"""
Authority Extraction -- Trace Continuity + Security Tests (Phase 5-6)

Tests:
  Phase 5: Trace continuity across internal path
  Phase 6: Failure modes and security validation

Run:
    python tests/test_authority_extraction.py
"""

import sys
import os
import io
import json
import time
import hashlib
import threading
from http.server import HTTPServer

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)

from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context, TraceSignal
from core.trace.trace_binding import create_trace_binding, verify_trace_binding
from core.trace.time_sync import get_normalized_timestamp, validate_timestamp_ordering
from core.trace.sovereign_core import SovereignCore
from core.trace.sarathi_enforcer import SarathiEnforcer, SarathiEnforcementError
from core.trace.pravah_emitter import PravahEmitter


def run_test(name, test_fn):
    try:
        test_fn()
        print(f"  [PASS] {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name} -- {str(e)}")
        return False


# ============================================================
# PHASE 5 -- TRACE CONTINUITY (INTERNAL PATH)
# ============================================================

def test_trace_id_unchanged_through_authority():
    """trace_id must be SAME after Sovereign + Sarathi."""
    origin = create_trace_origin("authority_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])
    original_id = ctx.trace_id

    sc = SovereignCore()
    ctx = sc.evaluate(ctx, "test input")
    assert ctx.trace_id == original_id, "trace_id changed after Sovereign"

    se = SarathiEnforcer()
    ctx = se.enforce(ctx)
    assert ctx.trace_id == original_id, "trace_id changed after Sarathi"


def test_decision_hash_integrity():
    """decision_hash must be derivable from inputs."""
    input_data = "test input for hashing"
    input_hash = hashlib.sha256(input_data.encode("utf-8")).hexdigest()

    sc = SovereignCore()
    origin = create_trace_origin("hash_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])
    ctx = sc.evaluate(ctx, input_data)

    decision_signal = ctx.get_signal("decision")
    assert decision_signal is not None
    assert decision_signal.payload["input_hash"] == input_hash


def test_execution_token_required():
    """Execution must not proceed without Sarathi clearance."""
    origin = create_trace_origin("token_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    # Skip Sovereign, try enforcement directly
    se = SarathiEnforcer()
    try:
        se.enforce(ctx)
        assert False, "Should have been blocked"
    except SarathiEnforcementError:
        pass  # Expected


def test_no_trace_id_regeneration():
    """trace_id must NOT be regenerated at any layer."""
    origin = create_trace_origin("regen_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])
    original_id = ctx.trace_id

    # Full flow
    sc = SovereignCore()
    se = SarathiEnforcer()
    pe = PravahEmitter(log_file="logs/test_authority_pravah.json")

    ctx = sc.evaluate(ctx, "test")
    assert ctx.trace_id == original_id

    ctx = se.enforce(ctx)
    assert ctx.trace_id == original_id

    execution_id = "exec-auth-001"
    ctx = ctx.with_execution_id(execution_id)
    trace_hash = create_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp)
    ctx = ctx.with_trace_hash(trace_hash)
    assert ctx.trace_id == original_id

    ctx = pe.emit(ctx)
    assert ctx.trace_id == original_id

    # Verify all signals have consistent trace
    for s in ctx.signals:
        if "trace_id" in s.payload:
            assert s.payload["trace_id"] == original_id


def test_trace_hash_integrity_after_authority():
    """trace_hash must verify correctly after full authority flow."""
    origin = create_trace_origin("binding_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    sc = SovereignCore()
    se = SarathiEnforcer()

    ctx = sc.evaluate(ctx, "test binding")
    ctx = se.enforce(ctx)

    execution_id = "exec-bind-001"
    ctx = ctx.with_execution_id(execution_id)
    trace_hash = create_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp)
    ctx = ctx.with_trace_hash(trace_hash)

    assert verify_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp, ctx.trace_hash)


def test_timestamp_ordering_across_authority():
    """Timestamps must be monotonically non-decreasing across authority layers."""
    origin = create_trace_origin("time_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    sc = SovereignCore()
    se = SarathiEnforcer()

    ctx = sc.evaluate(ctx, "time test")
    ctx = se.enforce(ctx)

    timestamps = ctx.get_all_timestamps()
    assert validate_timestamp_ordering(timestamps), "Timestamps not monotonic"


# ============================================================
# PHASE 6 -- FAILURE + SECURITY VALIDATION
# ============================================================

def test_sovereign_deny_blocks_execution():
    """DENY decision must completely block execution."""
    sc = SovereignCore(policies={"block": {"type": "deny", "deny_keywords": ["forbidden"]}})
    se = SarathiEnforcer()

    origin = create_trace_origin("deny_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    ctx = sc.evaluate(ctx, "this is forbidden content")
    assert ctx.get_signal("decision").payload["decision"] == "DENY"

    try:
        se.enforce(ctx)
        assert False, "Should have been blocked"
    except SarathiEnforcementError:
        pass  # Expected


def test_missing_decision_blocks_execution():
    """Missing decision signal must block execution (fail closed)."""
    se = SarathiEnforcer()
    origin = create_trace_origin("missing_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    try:
        se.enforce(ctx)
        assert False, "Should have been blocked"
    except SarathiEnforcementError as e:
        assert "No Sovereign Core decision" in str(e)


def test_external_service_fail_closed():
    """If external service is unreachable, system must FAIL CLOSED."""
    # Import the authority interface
    import core.authority as auth

    # Force external mode with unreachable URL
    original_use_external = auth.USE_EXTERNAL_AUTHORITY
    original_url = auth.SOVEREIGN_SERVICE_URL

    auth.USE_EXTERNAL_AUTHORITY = True
    auth.SOVEREIGN_SERVICE_URL = "http://localhost:59999"  # Nothing running here

    origin = create_trace_origin("failclosed_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    try:
        auth.callSovereign(ctx, "test input")
        assert False, "Should have raised ConnectionError"
    except ConnectionError:
        pass  # Expected -- FAIL CLOSED
    finally:
        auth.USE_EXTERNAL_AUTHORITY = original_use_external
        auth.SOVEREIGN_SERVICE_URL = original_url


def test_sarathi_fail_closed_without_sovereign():
    """Sarathi must fail closed if called without decision."""
    import core.authority as auth

    origin = create_trace_origin("sarathi_fail_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    try:
        auth.callSarathi(ctx)
        assert False, "Should have been blocked"
    except SarathiEnforcementError:
        pass  # Expected


def test_no_fallback_execution_path():
    """There must be no way to execute without going through authority."""
    origin = create_trace_origin("nofallback_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])

    # Assert: no enforcement signal exists
    assert not ctx.has_signal("enforcement"), "Should not have enforcement without Sarathi"

    # Assert: assert_cleared fails
    try:
        SarathiEnforcer.assert_cleared(ctx)
        assert False, "Should have raised"
    except SarathiEnforcementError:
        pass  # Expected

    # Assert: after adding decision but NOT enforcement, assert_cleared still fails
    sc = SovereignCore()
    ctx = sc.evaluate(ctx, "test")
    try:
        SarathiEnforcer.assert_cleared(ctx)
        assert False, "Should have raised"
    except SarathiEnforcementError:
        pass  # Expected


def test_trace_survives_authority_failure():
    """Trace must persist even when authority blocks execution."""
    sc = SovereignCore(policies={"deny_all": {"type": "deny", "deny_keywords": ["blocked"]}})
    se = SarathiEnforcer()

    origin = create_trace_origin("survive_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])
    original_id = ctx.trace_id

    ctx = sc.evaluate(ctx, "this is blocked content")
    assert ctx.trace_id == original_id
    assert ctx.has_signal("decision")

    try:
        se.enforce(ctx)
    except SarathiEnforcementError:
        pass  # Expected

    # Trace survives
    assert ctx.trace_id == original_id
    assert ctx.get_signal("decision").payload["decision"] == "DENY"


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  AUTHORITY EXTRACTION -- VALIDATION SUITE")
    print("=" * 60)

    tests = [
        # Phase 5 -- Trace Continuity
        ("Phase 5", "trace_id unchanged through authority", test_trace_id_unchanged_through_authority),
        ("Phase 5", "decision_hash integrity", test_decision_hash_integrity),
        ("Phase 5", "execution requires Sarathi clearance", test_execution_token_required),
        ("Phase 5", "no trace_id regeneration at any layer", test_no_trace_id_regeneration),
        ("Phase 5", "trace_hash verifies after authority flow", test_trace_hash_integrity_after_authority),
        ("Phase 5", "timestamp ordering across authority", test_timestamp_ordering_across_authority),
        # Phase 6 -- Failure + Security
        ("Phase 6", "DENY decision blocks execution", test_sovereign_deny_blocks_execution),
        ("Phase 6", "missing decision blocks execution", test_missing_decision_blocks_execution),
        ("Phase 6", "external service fail closed", test_external_service_fail_closed),
        ("Phase 6", "Sarathi fail closed without Sovereign", test_sarathi_fail_closed_without_sovereign),
        ("Phase 6", "no fallback execution path", test_no_fallback_execution_path),
        ("Phase 6", "trace survives authority failure", test_trace_survives_authority_failure),
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
