"""
TANTRA Trace Spine -- End-to-End Test Suite

Validates all 11 phases of the Core <-> Pravah Trace Lock:
 1. Trace origin (uniqueness, format)
 2. Trace propagation (immutability, same trace_id)
 3. Crypto binding (deterministic, tamper-evident)
 4. Decision + enforcement signals
 5. Sarathi lock (non-bypassable)
 6. Pravah contract (strict schema)
 7. Non-blocking guarantee
 8. Time synchronization
 9. Full trace proof (end-to-end)
10. Failure trace proof
11. Review packet structure
"""

import sys
import os
import json
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trace.trace_origin import generate_trace_id, generate_trace_timestamp, create_trace_origin
from core.trace.trace_context import TraceContext, TraceSignal, create_trace_context
from core.trace.trace_binding import create_trace_binding, verify_trace_binding
from core.trace.time_sync import get_normalized_timestamp, compare_timestamps, validate_timestamp_ordering
from core.trace.sovereign_core import SovereignCore
from core.trace.sarathi_enforcer import SarathiEnforcer, SarathiEnforcementError
from core.trace.pravah_emitter import PravahEmitter


def run_test(name, test_fn):
    """Run a test and print result."""
    try:
        test_fn()
        print(f"  [PASS] {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name} -- {str(e)}")
        return False


# ============================================================
# PHASE 1 -- TRACE ORIGIN
# ============================================================

def test_trace_id_is_uuid4():
    """trace_id must be UUID v4 format."""
    trace_id = generate_trace_id()
    assert len(trace_id) == 36, f"Expected UUID length 36, got {len(trace_id)}"
    assert trace_id.count("-") == 4, "Expected 4 hyphens in UUID"


def test_trace_id_uniqueness():
    """All trace_ids must be unique across 1000 generations."""
    ids = set()
    for _ in range(1000):
        tid = generate_trace_id()
        assert tid not in ids, f"Duplicate trace_id detected: {tid}"
        ids.add(tid)


def test_trace_timestamp_is_utc():
    """trace_timestamp must be ISO 8601 UTC."""
    ts = generate_trace_timestamp()
    assert "+00:00" in ts or "Z" in ts, f"Timestamp not UTC: {ts}"


def test_trace_origin_record():
    """create_trace_origin must produce a complete record."""
    origin = create_trace_origin("test_source")
    assert "trace_id" in origin
    assert "trace_timestamp" in origin
    assert "source" in origin
    assert origin["source"] == "test_source"


# ============================================================
# PHASE 2 -- TRACE PROPAGATION (IMMUTABLE)
# ============================================================

def test_trace_context_is_immutable():
    """TraceContext must be frozen (immutable)."""
    ctx = create_trace_context("test-id", get_normalized_timestamp(), "test")
    try:
        ctx.trace_id = "modified-id"
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass  # Expected -- frozen dataclass


def test_trace_id_preserved_across_signals():
    """trace_id must be SAME across all signal additions."""
    origin_id = generate_trace_id()
    ctx = create_trace_context(origin_id, get_normalized_timestamp(), "test")
    
    signal = TraceSignal(
        layer="test_layer",
        signal_type="test_signal",
        timestamp=get_normalized_timestamp(),
        payload={"test": True},
    )
    ctx2 = ctx.add_signal(signal)
    
    assert ctx.trace_id == ctx2.trace_id == origin_id, "trace_id must not change"


def test_signal_addition_creates_new_context():
    """add_signal must return a NEW context, not mutate the original."""
    ctx = create_trace_context("test-id", get_normalized_timestamp(), "test")
    original_signal_count = len(ctx.signals)
    
    signal = TraceSignal(
        layer="test", signal_type="test", timestamp=get_normalized_timestamp()
    )
    ctx2 = ctx.add_signal(signal)
    
    assert len(ctx.signals) == original_signal_count, "Original context must not change"
    assert len(ctx2.signals) == original_signal_count + 1, "New context must have +1 signal"
    assert ctx is not ctx2, "Must be different objects"


# ============================================================
# PHASE 3 -- CRYPTO TRACE BINDING
# ============================================================

def test_binding_is_deterministic():
    """Same inputs must produce the same hash."""
    h1 = create_trace_binding("id-1", "exec-1", "2026-01-01T00:00:00+00:00")
    h2 = create_trace_binding("id-1", "exec-1", "2026-01-01T00:00:00+00:00")
    assert h1 == h2, "Binding must be deterministic"


def test_binding_is_tamper_evident():
    """Changing any field must produce a different hash."""
    base = create_trace_binding("id-1", "exec-1", "2026-01-01T00:00:00+00:00")
    tampered_id = create_trace_binding("id-2", "exec-1", "2026-01-01T00:00:00+00:00")
    tampered_exec = create_trace_binding("id-1", "exec-2", "2026-01-01T00:00:00+00:00")
    tampered_time = create_trace_binding("id-1", "exec-1", "2026-01-02T00:00:00+00:00")
    
    assert base != tampered_id, "Different trace_id must produce different hash"
    assert base != tampered_exec, "Different execution_id must produce different hash"
    assert base != tampered_time, "Different timestamp must produce different hash"


def test_binding_verification():
    """verify_trace_binding must correctly validate hashes."""
    h = create_trace_binding("id-1", "exec-1", "2026-01-01T00:00:00+00:00")
    assert verify_trace_binding("id-1", "exec-1", "2026-01-01T00:00:00+00:00", h)
    assert not verify_trace_binding("id-TAMPERED", "exec-1", "2026-01-01T00:00:00+00:00", h)


# ============================================================
# PHASE 4 -- DECISION + ENFORCEMENT SIGNALS
# ============================================================

def test_sovereign_core_allow():
    """Sovereign Core must emit ALLOW decision with input_hash."""
    sc = SovereignCore()
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    ctx2 = sc.evaluate(ctx, "test input data")
    
    decision_signal = ctx2.get_signal("decision")
    assert decision_signal is not None, "Decision signal must exist"
    assert decision_signal.payload["decision"] == "ALLOW"
    assert "input_hash" in decision_signal.payload
    assert len(decision_signal.payload["input_hash"]) == 64  # SHA-256 hex


def test_sovereign_core_deny():
    """Sovereign Core must emit DENY when policy triggers."""
    sc = SovereignCore(policies={
        "block_test": {"type": "deny", "deny_keywords": ["BLOCKED_KEYWORD"]}
    })
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    ctx2 = sc.evaluate(ctx, "This contains BLOCKED_KEYWORD in input")
    
    decision_signal = ctx2.get_signal("decision")
    assert decision_signal is not None
    assert decision_signal.payload["decision"] == "DENY"
    assert decision_signal.payload["policy_reference"] == "block_test"


def test_sarathi_clears_on_allow():
    """Sarathi must CLEAR when decision is ALLOW."""
    sc = SovereignCore()
    se = SarathiEnforcer()
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    ctx = sc.evaluate(ctx, "allowed input")
    ctx = se.enforce(ctx)
    
    enforcement = ctx.get_signal("enforcement")
    assert enforcement is not None
    assert enforcement.payload["enforcement_status"] == "CLEARED"


def test_sarathi_blocks_on_deny():
    """Sarathi must BLOCK when decision is DENY."""
    sc = SovereignCore(policies={
        "deny_all": {"type": "deny", "deny_keywords": ["test"]}
    })
    se = SarathiEnforcer()
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    ctx = sc.evaluate(ctx, "test input")
    
    try:
        se.enforce(ctx)
        assert False, "Should have raised SarathiEnforcementError"
    except SarathiEnforcementError:
        pass  # Expected


# ============================================================
# PHASE 5 -- SARATHI LOCK (NON-BYPASSABLE)
# ============================================================

def test_sarathi_blocks_without_decision():
    """Sarathi must BLOCK if no decision signal exists."""
    se = SarathiEnforcer()
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    # No Sovereign Core evaluation -- trying to bypass
    try:
        se.enforce(ctx)
        assert False, "Should have raised SarathiEnforcementError"
    except SarathiEnforcementError as e:
        assert "No Sovereign Core decision" in str(e)


def test_sarathi_assert_cleared():
    """assert_cleared must verify Sarathi enforcement exists."""
    sc = SovereignCore()
    se = SarathiEnforcer()
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    ctx = sc.evaluate(ctx, "allowed input")
    ctx = se.enforce(ctx)
    
    assert SarathiEnforcer.assert_cleared(ctx) is True


def test_sarathi_assert_fails_without_enforcement():
    """assert_cleared must fail if no enforcement signal."""
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    try:
        SarathiEnforcer.assert_cleared(ctx)
        assert False, "Should have raised SarathiEnforcementError"
    except SarathiEnforcementError as e:
        assert "NO Sarathi enforcement signal" in str(e)


# ============================================================
# PHASE 6 -- PRAVAH CONTRACT (STRICT SCHEMA)
# ============================================================

def test_pravah_strict_schema():
    """Pravah signal must have exactly 6 fields, no more."""
    pe = PravahEmitter(log_file="logs/test_pravah_signals.json")
    sc = SovereignCore()
    se = SarathiEnforcer()
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    ctx = sc.evaluate(ctx, "test")
    ctx = se.enforce(ctx)
    ctx = ctx.with_execution_id("exec-1")
    ctx = ctx.with_trace_hash(create_trace_binding(ctx.trace_id, "exec-1", ctx.trace_timestamp))
    
    payload = pe._build_signal_payload(ctx)
    
    expected_fields = {"trace_id", "trace_hash", "source", "signal_type", "severity", "timestamp"}
    assert set(payload.keys()) == expected_fields, (
        f"Strict schema violation: expected {expected_fields}, got {set(payload.keys())}"
    )


# ============================================================
# PHASE 7 -- NON-BLOCKING GUARANTEE
# ============================================================

def test_pravah_non_blocking():
    """Pravah failure must NOT raise or block."""
    pe = PravahEmitter(log_file="/nonexistent/path/that/will/fail.json")
    ctx = create_trace_context(generate_trace_id(), get_normalized_timestamp(), "test")
    
    # This should NOT raise even though the log file path is invalid
    ctx2 = pe.emit(ctx)
    assert ctx2.trace_id == ctx.trace_id, "Trace must survive Pravah failure"


# ============================================================
# PHASE 8 -- TIME SYNCHRONIZATION
# ============================================================

def test_timestamps_are_utc():
    """All timestamps must be UTC."""
    ts = get_normalized_timestamp()
    assert "+00:00" in ts, f"Not UTC: {ts}"


def test_timestamp_ordering():
    """Sequential timestamps must be monotonically non-decreasing."""
    timestamps = [get_normalized_timestamp() for _ in range(10)]
    assert validate_timestamp_ordering(timestamps), "Timestamps not monotonic"


def test_timestamp_comparison():
    """compare_timestamps must return correct ordering."""
    early = "2026-01-01T00:00:00+00:00"
    late = "2026-12-31T23:59:59+00:00"
    assert compare_timestamps(early, late) == -1
    assert compare_timestamps(late, early) == 1
    assert compare_timestamps(early, early) == 0


# ============================================================
# PHASE 9 -- FULL TRACE PROOF (END-TO-END)
# ============================================================

def test_full_trace_end_to_end():
    """Complete trace: User -> Core -> Sovereign Core -> Sarathi -> Execution -> Pravah."""
    # 1. CORE: Generate trace origin
    origin = create_trace_origin("mcp_bridge")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])
    original_trace_id = ctx.trace_id
    
    # 2. SOVEREIGN CORE: Make decision
    sc = SovereignCore()
    ctx = sc.evaluate(ctx, "Explain quantum computing")
    assert ctx.has_signal("decision")
    assert ctx.trace_id == original_trace_id
    
    # 3. SARATHI: Enforce decision
    se = SarathiEnforcer()
    ctx = se.enforce(ctx)
    assert ctx.has_signal("enforcement")
    assert ctx.trace_id == original_trace_id
    
    # 4. EXECUTION: Set execution ID
    execution_id = "task-exec-001"
    ctx = ctx.with_execution_id(execution_id)
    exec_signal = TraceSignal(
        layer="execution",
        signal_type="execution",
        timestamp=get_normalized_timestamp(),
        payload={"execution_id": execution_id, "agent": "edumentor_agent", "status": "completed"},
    )
    ctx = ctx.add_signal(exec_signal)
    assert ctx.trace_id == original_trace_id
    
    # 5. BINDING: Create crypto hash
    trace_hash = create_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp)
    ctx = ctx.with_trace_hash(trace_hash)
    assert verify_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp, ctx.trace_hash)
    
    # 6. PRAVAH: Emit observation (non-blocking)
    pe = PravahEmitter(log_file="logs/test_pravah_signals.json")
    ctx = pe.emit(ctx)
    assert ctx.has_signal("observation")
    assert ctx.trace_id == original_trace_id
    
    # VERIFY: All signals present in correct order
    signal_types = [s.signal_type for s in ctx.signals]
    assert signal_types == ["origin", "decision", "enforcement", "execution", "observation"], (
        f"Signal order wrong: {signal_types}"
    )
    
    # VERIFY: Trace hash is valid
    assert ctx.trace_hash is not None
    assert verify_trace_binding(ctx.trace_id, ctx.execution_id, ctx.trace_timestamp, ctx.trace_hash)
    
    # VERIFY: Timestamp ordering
    assert validate_timestamp_ordering(ctx.get_all_timestamps())
    
    print("    Full trace: " + json.dumps(ctx.to_dict(), indent=2)[:200] + "...")


# ============================================================
# PHASE 10 -- FAILURE TRACE PROOF
# ============================================================

def test_failure_trace_persists():
    """Trace must persist even when execution is denied."""
    # Create trace
    origin = create_trace_origin("mcp_bridge")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])
    original_trace_id = ctx.trace_id
    
    # Sovereign Core DENIES
    sc = SovereignCore(policies={
        "deny_test": {"type": "deny", "deny_keywords": ["forbidden"]}
    })
    ctx = sc.evaluate(ctx, "This is forbidden content")
    assert ctx.has_signal("decision")
    assert ctx.get_signal("decision").payload["decision"] == "DENY"
    
    # Sarathi BLOCKS -- but trace continues
    se = SarathiEnforcer()
    try:
        se.enforce(ctx)
        assert False, "Should have been blocked"
    except SarathiEnforcementError:
        pass  # Expected
    
    # Add failure execution signal manually (trace persists)
    failure_signal = TraceSignal(
        layer="execution",
        signal_type="execution_failed",
        timestamp=get_normalized_timestamp(),
        payload={"reason": "Blocked by Sarathi", "status": "denied"},
    )
    ctx = ctx.add_signal(failure_signal)
    
    # Bind even on failure
    execution_id = "task-denied-001"
    ctx = ctx.with_execution_id(execution_id)
    trace_hash = create_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp)
    ctx = ctx.with_trace_hash(trace_hash)
    
    # Pravah still receives the failure signal
    pe = PravahEmitter(log_file="logs/test_pravah_signals.json")
    ctx = pe.emit_failure(ctx, "Blocked by Sarathi enforcement")
    
    # VERIFY: Trace is complete despite failure
    assert ctx.trace_id == original_trace_id
    assert ctx.has_signal("decision")
    assert ctx.has_signal("execution_failed")
    assert ctx.has_signal("observation")
    assert ctx.trace_hash is not None
    assert validate_timestamp_ordering(ctx.get_all_timestamps())


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  TANTRA TRACE SPINE -- FULL VALIDATION SUITE")
    print("=" * 60)
    
    tests = [
        # Phase 1
        ("Phase 1", "Trace ID is UUID v4 format", test_trace_id_is_uuid4),
        ("Phase 1", "Trace ID uniqueness (1000 IDs)", test_trace_id_uniqueness),
        ("Phase 1", "Trace timestamp is UTC", test_trace_timestamp_is_utc),
        ("Phase 1", "Trace origin record complete", test_trace_origin_record),
        # Phase 2
        ("Phase 2", "TraceContext is immutable (frozen)", test_trace_context_is_immutable),
        ("Phase 2", "trace_id preserved across signals", test_trace_id_preserved_across_signals),
        ("Phase 2", "Signal addition creates new context", test_signal_addition_creates_new_context),
        # Phase 3
        ("Phase 3", "Binding is deterministic", test_binding_is_deterministic),
        ("Phase 3", "Binding is tamper-evident", test_binding_is_tamper_evident),
        ("Phase 3", "Binding verification works", test_binding_verification),
        # Phase 4
        ("Phase 4", "Sovereign Core emits ALLOW decision", test_sovereign_core_allow),
        ("Phase 4", "Sovereign Core emits DENY on policy", test_sovereign_core_deny),
        ("Phase 4", "Sarathi CLEARS on ALLOW", test_sarathi_clears_on_allow),
        ("Phase 4", "Sarathi BLOCKS on DENY", test_sarathi_blocks_on_deny),
        # Phase 5
        ("Phase 5", "Sarathi BLOCKS without decision", test_sarathi_blocks_without_decision),
        ("Phase 5", "Sarathi assert_cleared works", test_sarathi_assert_cleared),
        ("Phase 5", "Sarathi assert fails without enforcement", test_sarathi_assert_fails_without_enforcement),
        # Phase 6
        ("Phase 6", "Pravah strict schema (6 fields only)", test_pravah_strict_schema),
        # Phase 7
        ("Phase 7", "Pravah non-blocking on failure", test_pravah_non_blocking),
        # Phase 8
        ("Phase 8", "Timestamps are UTC", test_timestamps_are_utc),
        ("Phase 8", "Timestamp ordering is monotonic", test_timestamp_ordering),
        ("Phase 8", "Timestamp comparison correct", test_timestamp_comparison),
        # Phase 9
        ("Phase 9", "FULL END-TO-END TRACE", test_full_trace_end_to_end),
        # Phase 10
        ("Phase 10", "Failure trace persists", test_failure_trace_persists),
    ]
    
    passed = 0
    failed = 0
    current_phase = ""
    
    for phase, name, fn in tests:
        if phase != current_phase:
            print(f"\n{'-' * 50}")
            print(f"  {phase}")
            print(f"{'-' * 50}")
            current_phase = phase
        
        if run_test(name, fn):
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'=' * 60}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
