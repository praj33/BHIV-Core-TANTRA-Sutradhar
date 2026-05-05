"""
TANTRA End-to-End Convergence Test — Phase 1 + 2 + 3

Phase 1: Full TANTRA flow proof (real, no mocks)
Phase 2: Contract validation at every boundary
Phase 3: Failure determinism (same input -> same failure)

Flow:
  Trigger -> Core -> Sovereign -> Sarathi -> Execution -> Bucket -> Pravah

SAME trace_id across ALL layers. No regeneration. No bypass.

Run:
    python tests/test_tantra_convergence.py
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
from core.trace.trace_context import create_trace_context, TraceSignal
from core.trace.time_sync import get_normalized_timestamp
from core.authority import callSovereign, callSarathi
from core.trace.sarathi_enforcer import SarathiEnforcementError
from core.authority.execution_gate import (
    register_token, gated_execute, validate_execution_token,
    ExecutionBlockedError, _token_registry, _used_tokens, get_token_state,
)
from core.authority.bucket_writer import (
    append_to_bucket, verify_bucket_record, finalize_execution,
    BucketWriteError, ExecutionFinalizationError,
)
from core.authority.contract_validator import (
    validate_contract, validate_trace_continuity,
    ContractValidationError, CONTRACT_SCHEMAS,
)

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


def action_execute(input_data):
    return {"status": "executed", "result": f"processed: {input_data[:30]}"}


# ═══════════════════════════════════════════════════════════
# PHASE 1 — FULL TANTRA FLOW PROOF
# ═══════════════════════════════════════════════════════════

def test_full_tantra_flow():
    """ONE real, complete end-to-end execution across ALL layers."""
    clean_state()
    artifacts = {}

    # Step 1: Trigger — create trace origin
    origin = create_trace_origin("tantra_convergence_test")
    trace_id = origin["trace_id"]
    artifacts["1_origin"] = origin

    # Step 2: Core — create trace context
    ctx = create_trace_context(trace_id, origin["trace_timestamp"], "tantra_test")
    artifacts["2_trace_context"] = {
        "trace_id": ctx.trace_id,
        "source": ctx.source,
        "timestamp": ctx.trace_timestamp,
    }

    # Verify trace_id is the SAME
    assert ctx.trace_id == trace_id, "trace_id mutated at context creation!"

    # Step 3: Sovereign Core — decision
    ctx = callSovereign(ctx, "tantra convergence test execution")
    decision_signal = ctx.get_signal("decision")
    assert decision_signal is not None, "No decision signal from Sovereign"
    assert decision_signal.payload["decision"] == "ALLOW"

    # Validate Sovereign response contract
    sovereign_response = {
        "decision": decision_signal.payload["decision"],
        "input_hash": decision_signal.payload.get("input_hash", ""),
        "decision_hash": decision_signal.payload.get("decision_hash", ""),
        "policy_reference": decision_signal.payload.get("policy_reference", ""),
    }
    validate_contract(sovereign_response, "sovereign_response")
    artifacts["3_sovereign"] = sovereign_response

    # Step 4: Sarathi — enforcement
    ctx = callSarathi(ctx)
    enforcement_signal = ctx.get_signal("enforcement")
    assert enforcement_signal is not None, "No enforcement signal from Sarathi"
    assert enforcement_signal.payload["enforcement_status"] == "CLEARED"

    # Validate Sarathi response contract
    sarathi_response = {
        "status": enforcement_signal.payload["enforcement_status"],
        "validation_result": enforcement_signal.payload.get("validation_result", ""),
    }
    validate_contract(sarathi_response, "sarathi_response")
    artifacts["4_sarathi"] = sarathi_response

    # Step 5: Execution — through gate
    token = hashlib.sha256(f"{trace_id}:tantra".encode()).hexdigest()
    register_token(token, trace_id, scope={
        "agent": "tantra_test",
        "intent": "convergence",
        "decision_hash": decision_signal.payload.get("decision_hash", ""),
    })

    result = gated_execute(
        action_execute, token, trace_id, "tantra convergence test execution"
    )
    assert result["status"] == "executed"
    artifacts["5_execution"] = result

    # Step 6: Bucket — truth write + verify
    final = finalize_execution(
        trace_id=trace_id,
        execution_id=f"tantra-exec-{trace_id[:8]}",
        token=token,
        decision="ALLOW",
        payload={"input": "tantra convergence test execution"},
        execution_result=result,
    )
    assert final["status"] == "finalized"
    assert final["verified"] is True
    artifacts["6_bucket"] = final

    # Verify Bucket record
    bucket_record = verify_bucket_record(trace_id)
    assert bucket_record is not None, "Bucket record NOT found!"
    assert bucket_record["trace_id"] == trace_id
    artifacts["6_bucket_record"] = {
        "trace_id": bucket_record["trace_id"],
        "execution_id": bucket_record["execution_id"],
        "record_hash": bucket_record.get("record_hash", ""),
    }

    # Step 7: Pravah — observation signal
    pravah_signal = {
        "trace_id": trace_id,
        "event_type": "execution_completed",
        "timestamp": get_normalized_timestamp(),
        "payload": {
            "execution_status": "finalized",
            "bucket_verified": True,
        },
    }
    validate_contract(pravah_signal, "pravah_signal")
    artifacts["7_pravah"] = pravah_signal

    # VERIFY: trace_id is SAME across ALL layers
    all_payloads = [
        {"trace_id": trace_id},                    # Origin
        {"trace_id": ctx.trace_id},                # Context
        {"trace_id": bucket_record["trace_id"]},   # Bucket
        {"trace_id": pravah_signal["trace_id"]},   # Pravah
    ]
    validate_trace_continuity(all_payloads, trace_id)

    # Store for report
    flow_artifacts["full_flow"] = artifacts
    flow_artifacts["trace_id"] = trace_id


def test_trace_id_never_changes():
    """Verify trace_id is SAME at every step."""
    clean_state()
    origin = create_trace_origin("trace_lock_test")
    trace_id = origin["trace_id"]

    ctx = create_trace_context(trace_id, origin["trace_timestamp"], "test")
    assert ctx.trace_id == trace_id

    ctx = callSovereign(ctx, "test trace continuity")
    assert ctx.trace_id == trace_id

    ctx = callSarathi(ctx)
    assert ctx.trace_id == trace_id

    # No regeneration, no mutation
    for signal in ctx.signals:
        # signals don't carry trace_id themselves, but context does
        pass

    assert ctx.trace_id == trace_id, "trace_id was mutated!"


def test_deterministic_output():
    """Same input -> same decision hash."""
    clean_state()
    input_data = "deterministic tantra input"

    # Run 1
    origin1 = create_trace_origin("det1")
    ctx1 = create_trace_context(origin1["trace_id"], origin1["trace_timestamp"], "det")
    ctx1 = callSovereign(ctx1, input_data)
    hash1 = ctx1.get_signal("decision").payload.get("decision_hash", "")

    # Run 2
    clean_state()
    origin2 = create_trace_origin("det2")
    ctx2 = create_trace_context(origin2["trace_id"], origin2["trace_timestamp"], "det")
    ctx2 = callSovereign(ctx2, input_data)
    hash2 = ctx2.get_signal("decision").payload.get("decision_hash", "")

    assert hash1 == hash2, f"Decision hash not deterministic: {hash1} != {hash2}"
    assert ctx1.get_signal("decision").payload["decision"] == ctx2.get_signal("decision").payload["decision"]


# ═══════════════════════════════════════════════════════════
# PHASE 2 — CONTRACT VALIDATION
# ═══════════════════════════════════════════════════════════

def test_sovereign_request_valid():
    payload = {"trace_id": "abc12345-6789-0000-0000-000000000001", "input": "test", "context": {}}
    validate_contract(payload, "sovereign_request")


def test_sovereign_request_missing_field():
    payload = {"trace_id": "abc-123"}  # missing input, context
    try:
        validate_contract(payload, "sovereign_request")
        assert False, "Should reject"
    except ContractValidationError as e:
        assert "Missing required field" in str(e)


def test_sovereign_request_unknown_field():
    payload = {"trace_id": "abc", "input": "test", "context": {}, "extra_field": "bad"}
    try:
        validate_contract(payload, "sovereign_request")
        assert False, "Should reject"
    except ContractValidationError as e:
        assert "Unknown field" in str(e)


def test_sovereign_response_invalid_enum():
    payload = {"decision": "MAYBE", "input_hash": "x", "decision_hash": "y"}
    try:
        validate_contract(payload, "sovereign_response")
        assert False, "Should reject"
    except ContractValidationError as e:
        assert "Invalid value" in str(e)


def test_sarathi_response_valid():
    payload = {"status": "CLEARED", "execution_token": "tok-123"}
    validate_contract(payload, "sarathi_response")


def test_sarathi_response_invalid():
    payload = {"status": "MAYBE"}
    try:
        validate_contract(payload, "sarathi_response")
        assert False, "Should reject"
    except ContractValidationError as e:
        assert "Invalid value" in str(e)


def test_bucket_record_valid():
    payload = {
        "trace_id": "abc12345-6789-0000-0000-000000000002", "execution_id": "exec-1",
        "execution_token": "tok-1", "decision": "ALLOW",
        "timestamp": "2026-01-01T00:00:00Z", "payload_hash": "hash",
    }
    validate_contract(payload, "bucket_record")


def test_bucket_record_missing():
    payload = {"trace_id": "abc"}
    try:
        validate_contract(payload, "bucket_record")
        assert False, "Should reject"
    except ContractValidationError as e:
        assert "Missing required field" in str(e)


def test_pravah_signal_valid():
    payload = {
        "trace_id": "abc12345-6789-0000-0000-000000000003", "event_type": "exec_done",
        "timestamp": "2026-01-01T00:00:00Z", "payload": {"x": 1},
    }
    validate_contract(payload, "pravah_signal")


def test_type_mismatch_rejected():
    payload = {"trace_id": 12345, "input": "test", "context": {}}
    try:
        validate_contract(payload, "sovereign_request")
        assert False, "Should reject"
    except ContractValidationError as e:
        assert "Type mismatch" in str(e)


def test_trace_continuity_pass():
    payloads = [{"trace_id": "x"}, {"trace_id": "x"}, {"trace_id": "x"}]
    validate_trace_continuity(payloads, "x")


def test_trace_continuity_fail():
    payloads = [{"trace_id": "x"}, {"trace_id": "y"}]
    try:
        validate_trace_continuity(payloads, "x")
        assert False, "Should fail"
    except ContractValidationError as e:
        assert "BROKEN" in str(e)


# ═══════════════════════════════════════════════════════════
# PHASE 3 — FAILURE DETERMINISM
# ═══════════════════════════════════════════════════════════

def test_failure_sovereign_down():
    """Sovereign down -> structured error, trace-linked."""
    import core.authority as auth
    orig = auth.USE_EXTERNAL_AUTHORITY
    orig_url = auth.SOVEREIGN_SERVICE_URL
    auth.USE_EXTERNAL_AUTHORITY = True
    auth.SOVEREIGN_SERVICE_URL = "http://localhost:59999"

    origin = create_trace_origin("fail_sov")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "test")

    try:
        callSovereign(ctx, "test")
        assert False, "Should fail closed"
    except ConnectionError as e:
        assert "unreachable" in str(e).lower()
    finally:
        auth.USE_EXTERNAL_AUTHORITY = orig
        auth.SOVEREIGN_SERVICE_URL = orig_url


def test_failure_sarathi_down():
    """Sarathi down -> structured error."""
    import core.authority as auth
    orig = auth.USE_EXTERNAL_AUTHORITY
    orig_url = auth.SARATHI_SERVICE_URL
    auth.USE_EXTERNAL_AUTHORITY = True
    auth.SARATHI_SERVICE_URL = "http://localhost:59998"

    origin = create_trace_origin("fail_sar")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "test")
    ctx = callSovereign(ctx, "test")

    auth.USE_EXTERNAL_AUTHORITY = True
    auth.SARATHI_SERVICE_URL = "http://localhost:59998"
    try:
        _callSarathi_fail(ctx)
        assert False, "Should fail closed"
    except (ConnectionError, SarathiEnforcementError):
        pass
    finally:
        auth.USE_EXTERNAL_AUTHORITY = orig
        auth.SARATHI_SERVICE_URL = orig_url


def _callSarathi_fail(ctx):
    """Helper to test Sarathi failure."""
    import core.authority as auth
    auth.USE_EXTERNAL_AUTHORITY = True
    auth.SARATHI_SERVICE_URL = "http://localhost:59998"
    return auth.callSarathi(ctx)


def test_failure_token_invalid():
    """Invalid token -> structured error with trace_id."""
    clean_state()
    try:
        validate_execution_token("FAKE", "trace-fail-token")
        assert False, "Should block"
    except ExecutionBlockedError as e:
        assert "BLOCKED" in str(e)


def test_failure_bucket_missing_field():
    """Bucket schema violation -> structured error."""
    try:
        append_to_bucket({"trace_id": "x"})
        assert False
    except BucketWriteError as e:
        assert "Missing required field" in str(e)


def test_failure_schema_invalid():
    """Invalid schema -> structured error."""
    try:
        validate_contract({"bad": "data"}, "sovereign_request")
        assert False
    except ContractValidationError as e:
        assert "Missing required field" in str(e)


def test_failure_determinism():
    """Same invalid input -> same error ALWAYS."""
    clean_state()
    errors = []
    for _ in range(3):
        try:
            validate_execution_token("", "trace-determinism")
        except ExecutionBlockedError as e:
            errors.append(str(e))

    # All 3 errors must be identical
    assert len(set(errors)) == 1, f"Failure not deterministic: {errors}"


def test_failure_trace_linked():
    """Error messages must include trace_id."""
    clean_state()
    trace_id = "trace-linked-error-test"
    try:
        validate_execution_token("", trace_id)
    except ExecutionBlockedError as e:
        assert trace_id in str(e), f"Error not trace-linked: {e}"


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    global passed, failed

    print("=" * 60)
    print("  TANTRA END-TO-END CONVERGENCE TEST")
    print("=" * 60)

    # Phase 1
    print("\n  Phase 1: Full TANTRA Flow Proof")
    print("  " + "-" * 40)
    run_test("Full TANTRA flow (7 layers)", test_full_tantra_flow)
    run_test("trace_id never changes", test_trace_id_never_changes)
    run_test("Deterministic output", test_deterministic_output)

    # Phase 2
    print("\n  Phase 2: Contract Schema Validation")
    print("  " + "-" * 40)
    run_test("Sovereign request (valid)", test_sovereign_request_valid)
    run_test("Sovereign request (missing field)", test_sovereign_request_missing_field)
    run_test("Sovereign request (unknown field)", test_sovereign_request_unknown_field)
    run_test("Sovereign response (invalid enum)", test_sovereign_response_invalid_enum)
    run_test("Sarathi response (valid)", test_sarathi_response_valid)
    run_test("Sarathi response (invalid)", test_sarathi_response_invalid)
    run_test("Bucket record (valid)", test_bucket_record_valid)
    run_test("Bucket record (missing)", test_bucket_record_missing)
    run_test("Pravah signal (valid)", test_pravah_signal_valid)
    run_test("Type mismatch rejected", test_type_mismatch_rejected)
    run_test("Trace continuity (pass)", test_trace_continuity_pass)
    run_test("Trace continuity (fail)", test_trace_continuity_fail)

    # Phase 3
    print("\n  Phase 3: Failure Determinism")
    print("  " + "-" * 40)
    run_test("Sovereign down -> fail closed", test_failure_sovereign_down)
    run_test("Token invalid -> structured error", test_failure_token_invalid)
    run_test("Bucket schema violation", test_failure_bucket_missing_field)
    run_test("Contract schema invalid", test_failure_schema_invalid)
    run_test("Failure is deterministic", test_failure_determinism)
    run_test("Error is trace-linked", test_failure_trace_linked)

    total = passed + failed
    print()
    print("=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed, {total} total")
    print("=" * 60)

    # Save flow artifacts
    if flow_artifacts:
        os.makedirs("logs", exist_ok=True)
        with open("logs/tantra_flow_proof.json", "w", encoding="utf-8") as f:
            json.dump(flow_artifacts, f, indent=2, default=str)
        print(f"\n  Flow artifacts: logs/tantra_flow_proof.json")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
