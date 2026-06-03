"""
TANTRA Live Integration Test Suite — Phases 3-9

Phase 3: Token discipline (missing/tampered → blocked)
Phase 4: Contract integrity (CET hash unchanged)
Phase 5: Replay protection
Phase 6: Bucket truth validation
Phase 7: InsightFlow trace verification
Phase 8: End-to-end proof (ONE real flow)
Phase 9: Failure visibility

Run:
    python tests/test_live_tantra_integration.py
"""

import sys
import os
import io
import json
import hashlib
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)

from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.trace.time_sync import get_normalized_timestamp
from core.authority import callSovereign, callSarathi
from core.trace.sarathi_enforcer import SarathiEnforcementError
from core.authority.execution_gate import (
    register_token, gated_execute, validate_execution_token,
    ExecutionBlockedError, _token_registry, _used_tokens,
)
from core.authority.bucket_writer import (
    append_to_bucket, verify_bucket_record, finalize_execution,
    BucketWriteError, ExecutionFinalizationError,
)
from core.authority.cet_client import verify_contract_integrity, CETError
from core.authority.insightflow_client import (
    emitTrace, buildTraceChain, INSIGHTFLOW_LOG_FILE,
)
from core.authority.tantra_flow import execute_tantra_flow, TANTRAFlowError

passed = 0
failed = 0
flow_artifacts = {}


def clean_state():
    _token_registry.clear()
    _used_tokens.clear()


def run_test(name, test_fn):
    global passed, failed
    try:
        test_fn()
        passed += 1
        print(f"  [PASS] {name}")
    except AssertionError as e:
        failed += 1
        print(f"  [FAIL] {name}: {e}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")


# ═══════════════════════════════════════════════════════════
# PHASE 3 — TOKEN DISCIPLINE
# ═══════════════════════════════════════════════════════════

def test_missing_token_blocked():
    clean_state()
    try:
        gated_execute(lambda p: "bad", "", "trace-missing")
        assert False, "Should block"
    except ExecutionBlockedError:
        pass


def test_tampered_token_blocked():
    clean_state()
    token = hashlib.sha256(b"real").hexdigest()
    register_token(token, "trace-tamper")
    try:
        gated_execute(lambda p: "bad", "FAKE-TOKEN", "trace-tamper")
        assert False, "Should block"
    except (ExecutionBlockedError, ConnectionError):
        pass


def test_token_from_sarathi_only():
    """Token must come from Sarathi flow, not self-generated."""
    clean_state()
    origin = create_trace_origin("token_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "test")
    ctx = callSovereign(ctx, "test token discipline")
    ctx = callSarathi(ctx)

    enforcement = ctx.get_signal("enforcement")
    assert enforcement is not None
    assert enforcement.payload["enforcement_status"] == "CLEARED"


def test_no_execution_without_token():
    clean_state()
    try:
        validate_execution_token("", "trace-no-token")
        assert False, "Should block"
    except ExecutionBlockedError as e:
        assert "BLOCKED" in str(e)


# ═══════════════════════════════════════════════════════════
# PHASE 4 — CONTRACT INTEGRITY
# ═══════════════════════════════════════════════════════════

def test_contract_hash_unchanged():
    """CET hash must be forwarded without mutation."""
    original = hashlib.sha256(b"contract-data").hexdigest()
    forwarded = original  # No mutation
    assert verify_contract_integrity(original, forwarded) is True


def test_contract_hash_mutation_detected():
    """If hash is mutated, Core rejects flow."""
    original = hashlib.sha256(b"contract-data").hexdigest()
    mutated = hashlib.sha256(b"tampered-data").hexdigest()
    try:
        verify_contract_integrity(original, mutated)
        assert False, "Should detect mutation"
    except CETError as e:
        assert "VIOLATED" in str(e)


# ═══════════════════════════════════════════════════════════
# PHASE 5 — REPLAY PROTECTION
# ═══════════════════════════════════════════════════════════

def test_replay_same_token_blocked():
    clean_state()
    token = hashlib.sha256(b"replay-test").hexdigest()
    trace_id = "trace-replay-live"
    register_token(token, trace_id)
    gated_execute(lambda p: "ok", token, trace_id, {})

    # Second attempt with same token
    register_token(token, trace_id)
    try:
        gated_execute(lambda p: "bad", token, trace_id, {})
        assert False, "Should block replay"
    except ExecutionBlockedError as e:
        assert "replay" in str(e).lower()


def test_same_request_different_tokens():
    """Same request with different tokens = different executions (not replay)."""
    clean_state()
    t1 = hashlib.sha256(b"token-1").hexdigest()
    t2 = hashlib.sha256(b"token-2").hexdigest()
    register_token(t1, "trace-multi-1")
    register_token(t2, "trace-multi-2")

    r1 = gated_execute(lambda p: {"run": 1}, t1, "trace-multi-1", {})
    r2 = gated_execute(lambda p: {"run": 2}, t2, "trace-multi-2", {})
    assert r1["run"] == 1
    assert r2["run"] == 2


# ═══════════════════════════════════════════════════════════
# PHASE 6 — BUCKET TRUTH VALIDATION
# ═══════════════════════════════════════════════════════════

def test_bucket_write_and_readback():
    clean_state()
    trace_id = f"trace-bucket-live-{int(time.time())}"
    result = finalize_execution(
        trace_id=trace_id,
        execution_id=f"exec-{trace_id[:8]}",
        token="token-bucket-test",
        decision="ALLOW",
        payload={"action": "test"},
        execution_result={"status": "ok"},
    )
    assert result["status"] == "finalized"
    assert result["verified"] is True

    record = verify_bucket_record(trace_id)
    assert record is not None
    assert record["trace_id"] == trace_id


def test_bucket_write_every_execution():
    """Every execution attempt must produce a Bucket write."""
    clean_state()
    token = hashlib.sha256(b"bucket-every").hexdigest()
    trace_id = f"trace-every-{int(time.time())}"
    register_token(token, trace_id)
    gated_execute(lambda p: {"ok": True}, token, trace_id, {})

    # Finalize
    result = finalize_execution(
        trace_id=trace_id,
        execution_id=f"exec-{trace_id[:8]}",
        token=token,
        decision="ALLOW",
        payload={"test": True},
        execution_result={"ok": True},
    )
    assert result["verified"] is True

    record = verify_bucket_record(trace_id)
    assert record is not None


# ═══════════════════════════════════════════════════════════
# PHASE 7 — INSIGHTFLOW TRACE
# ═══════════════════════════════════════════════════════════

def test_insightflow_trace_emission():
    trace_id = f"trace-insight-{int(time.time())}"
    chain = buildTraceChain(
        trace_id=trace_id,
        origin={"trace_id": trace_id, "source": "test"},
        sovereign={"decision": "ALLOW", "trace_id": trace_id},
        execution={"status": "executed", "trace_id": trace_id},
        bucket={"status": "finalized", "trace_id": trace_id},
    )

    assert len(chain) == 4
    assert all(c["trace_id"] == trace_id for c in chain)

    result = emitTrace(
        trace_id=trace_id,
        trace_chain=chain,
        execution_status="completed",
        bucket_verified=True,
    )
    assert result["status"] == "emitted"


def test_insightflow_no_trace_mutation():
    """Trace chain must have same trace_id at every layer."""
    trace_id = "trace-no-mutate"
    chain = buildTraceChain(
        trace_id=trace_id,
        origin={"trace_id": trace_id},
        sovereign={"trace_id": trace_id},
        sarathi={"trace_id": trace_id},
        bucket={"trace_id": trace_id},
    )
    for entry in chain:
        assert entry["trace_id"] == trace_id, f"Trace mutated at {entry['layer']}"


# ═══════════════════════════════════════════════════════════
# PHASE 8 — END-TO-END PROOF
# ═══════════════════════════════════════════════════════════

def test_full_tantra_flow_e2e():
    """ONE complete flow: Core → Sovereign → CET → Sarathi → Bridge → Exec → Bucket → InsightFlow"""
    clean_state()
    result = execute_tantra_flow(
        input_data="deploy edumentor service to production",
        agent="edumentor_agent",
        source="live_integration_test",
    )

    assert result["status"] == "completed"
    assert result["trace_id"] is not None

    trace_id = result["trace_id"]

    # Verify all 8 steps present
    steps = result["steps"]
    assert "1_origin" in steps
    assert "2_sovereign" in steps
    assert "3_cet" in steps
    assert "4_sarathi" in steps
    assert "5_bridge" in steps
    assert "6_execution" in steps
    assert "7_bucket" in steps
    assert "8_insightflow" in steps

    # Verify SAME trace_id at every step
    for step_name, step_data in steps.items():
        if isinstance(step_data, dict) and "trace_id" in step_data:
            assert step_data["trace_id"] == trace_id, \
                f"trace_id mismatch at {step_name}: {step_data['trace_id']} != {trace_id}"

    # Verify Bucket record exists
    record = verify_bucket_record(trace_id)
    assert record is not None

    # Store for report
    flow_artifacts["e2e_flow"] = result
    flow_artifacts["trace_id"] = trace_id


# ═══════════════════════════════════════════════════════════
# PHASE 9 — FAILURE VISIBILITY
# ═══════════════════════════════════════════════════════════

def test_failure_sovereign_down():
    """Sovereign down → execution stops, failure visible."""
    import core.authority as auth
    orig = auth.USE_EXTERNAL_AUTHORITY
    orig_url = auth.SOVEREIGN_SERVICE_URL
    auth.USE_EXTERNAL_AUTHORITY = True
    auth.SOVEREIGN_SERVICE_URL = "http://localhost:59999"

    clean_state()
    try:
        execute_tantra_flow(input_data="test sov down", source="fail_test")
        assert False, "Should fail"
    except TANTRAFlowError as e:
        assert "unreachable" in str(e).lower() or "Sovereign" in str(e)
    finally:
        auth.USE_EXTERNAL_AUTHORITY = orig
        auth.SOVEREIGN_SERVICE_URL = orig_url


def test_failure_token_missing():
    """Missing token → execution blocked, trace emitted."""
    clean_state()
    try:
        validate_execution_token("", "trace-fail-vis")
        assert False, "Should block"
    except ExecutionBlockedError as e:
        assert "BLOCKED" in str(e)
        assert "trace-fail-vis" in str(e)


def test_failure_bucket_schema():
    """Bucket schema violation → structured error."""
    try:
        append_to_bucket({"trace_id": "x"})
        assert False
    except BucketWriteError as e:
        assert "Missing required field" in str(e)


def test_failure_deterministic():
    """Same failure → same error every time."""
    clean_state()
    errors = []
    for _ in range(3):
        try:
            validate_execution_token("", "trace-det-fail")
        except ExecutionBlockedError as e:
            errors.append(str(e))
    assert len(set(errors)) == 1


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    global passed, failed

    print("=" * 60)
    print("  TANTRA LIVE INTEGRATION TEST SUITE")
    print("=" * 60)

    print("\n  Phase 3: Token Discipline")
    print("  " + "-" * 40)
    run_test("Missing token -> BLOCKED", test_missing_token_blocked)
    run_test("Tampered token -> BLOCKED", test_tampered_token_blocked)
    run_test("Token from Sarathi flow", test_token_from_sarathi_only)
    run_test("No execution without token", test_no_execution_without_token)

    print("\n  Phase 4: Contract Integrity")
    print("  " + "-" * 40)
    run_test("Contract hash unchanged", test_contract_hash_unchanged)
    run_test("Contract mutation detected", test_contract_hash_mutation_detected)

    print("\n  Phase 5: Replay Protection")
    print("  " + "-" * 40)
    run_test("Replay same token -> BLOCKED", test_replay_same_token_blocked)
    run_test("Same request, different tokens -> OK", test_same_request_different_tokens)

    print("\n  Phase 6: Bucket Truth Validation")
    print("  " + "-" * 40)
    run_test("Bucket write + readback", test_bucket_write_and_readback)
    run_test("Bucket write every execution", test_bucket_write_every_execution)

    print("\n  Phase 7: InsightFlow Trace")
    print("  " + "-" * 40)
    run_test("Trace emission", test_insightflow_trace_emission)
    run_test("No trace mutation", test_insightflow_no_trace_mutation)

    print("\n  Phase 8: End-to-End Proof")
    print("  " + "-" * 40)
    run_test("Full TANTRA flow (8 steps)", test_full_tantra_flow_e2e)

    print("\n  Phase 9: Failure Visibility")
    print("  " + "-" * 40)
    run_test("Sovereign down -> fail closed", test_failure_sovereign_down)
    run_test("Token missing -> visible error", test_failure_token_missing)
    run_test("Bucket schema violation", test_failure_bucket_schema)
    run_test("Failure is deterministic", test_failure_deterministic)

    total = passed + failed
    print()
    print("=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed, {total} total")
    print("=" * 60)

    if flow_artifacts:
        os.makedirs("logs", exist_ok=True)
        with open("logs/live_tantra_flow_proof.json", "w", encoding="utf-8") as f:
            json.dump(flow_artifacts, f, indent=2, default=str)
        print(f"\n  Flow proof: logs/live_tantra_flow_proof.json")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
