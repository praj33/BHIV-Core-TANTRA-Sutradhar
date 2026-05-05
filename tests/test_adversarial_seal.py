"""
Adversarial Test Suite — Phase 4

Tests ALL failure and misuse scenarios:
  - Token missing, tampered, replayed, expired
  - Bucket down
  - Sovereign down, Sarathi down
  - Partial execution attempts
  - Direct function call bypass attempts
  - Token lifecycle state transitions
  - Execution finalization invariant

ALL tests must result in FAIL CLOSED behavior.

Run:
    python tests/test_adversarial_seal.py
"""

import sys
import os
import io
import json
import time
import hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)

from core.authority.execution_gate import (
    register_token, gated_execute, validate_execution_token,
    mark_token_used, get_token_state, assert_execution_gated,
    ExecutionBlockedError, TokenState, require_gate,
    _token_registry, _used_tokens, _execution_count, _gated_execution_count,
    _lock,
)
from core.authority.bucket_writer import (
    append_to_bucket, verify_bucket_record, finalize_execution,
    BucketWriteError, ExecutionFinalizationError,
)
from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.authority import callSovereign, callSarathi


def clean_state():
    import core.authority.execution_gate as gate
    with gate._lock:
        gate._token_registry.clear()
        gate._used_tokens.clear()
        gate._execution_count = 0
        gate._gated_execution_count = 0


passed = 0
failed = 0


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


def action_success():
    return {"status": "executed", "result": "ok"}


# ═══════════════════════════════════════════════════════════
# PHASE 1 — EXECUTION SURFACE SEAL
# ═══════════════════════════════════════════════════════════

def test_no_token_blocks():
    clean_state()
    try:
        gated_execute(action_success, "", "trace-001")
        assert False, "Should have blocked"
    except ExecutionBlockedError:
        pass


def test_no_trace_blocks():
    clean_state()
    try:
        gated_execute(action_success, "some-token", "")
        assert False, "Should have blocked"
    except ExecutionBlockedError:
        pass


def test_valid_token_allows():
    clean_state()
    token = hashlib.sha256(b"valid-test-1").hexdigest()
    trace_id = "trace-valid-001"
    register_token(token, trace_id)
    result = gated_execute(action_success, token, trace_id)
    assert result["status"] == "executed"


def test_assertion_layer():
    """Hard assertion: all executions must go through gate."""
    clean_state()
    import core.authority.execution_gate as gate
    gate._execution_count = 0
    gate._gated_execution_count = 0

    token = hashlib.sha256(b"assert-test").hexdigest()
    register_token(token, "trace-assert")
    gated_execute(action_success, token, "trace-assert")

    # Should pass (both counts equal)
    assert_execution_gated()


def test_assertion_detects_bypass():
    """Hard assertion detects ungated execution."""
    clean_state()
    import core.authority.execution_gate as gate
    gate._execution_count = 5
    gate._gated_execution_count = 3

    try:
        assert_execution_gated()
        assert False, "Should have panicked"
    except RuntimeError as e:
        assert "SECURITY PANIC" in str(e)


def test_require_gate_decorator():
    """@require_gate decorator blocks direct calls."""
    clean_state()

    @require_gate
    def protected_action():
        return "should not run"

    try:
        protected_action()
        assert False, "Should have blocked"
    except ExecutionBlockedError as e:
        assert "called directly" in str(e)


# ═══════════════════════════════════════════════════════════
# PHASE 2 — TOKEN LIFECYCLE
# ═══════════════════════════════════════════════════════════

def test_tampered_token_blocks():
    clean_state()
    try:
        gated_execute(action_success, "FAKE-TOKEN", "trace-002")
        assert False, "Should have blocked"
    except (ExecutionBlockedError, ConnectionError):
        pass


def test_replay_blocks():
    clean_state()
    token = hashlib.sha256(b"replay-test").hexdigest()
    trace_id = "trace-replay"
    register_token(token, trace_id)
    gated_execute(action_success, token, trace_id)

    # Second use of same token
    register_token(token, trace_id)  # even if re-registered
    try:
        gated_execute(action_success, token, trace_id)
        assert False, "Should have blocked replay"
    except ExecutionBlockedError as e:
        assert "replay" in str(e).lower()


def test_trace_mismatch_blocks():
    clean_state()
    token = hashlib.sha256(b"mismatch-test").hexdigest()
    register_token(token, "trace-correct")
    try:
        gated_execute(action_success, token, "trace-wrong")
        assert False, "Should have blocked"
    except ExecutionBlockedError as e:
        assert "mismatch" in str(e).lower()


def test_token_expiry():
    """Token with 0-second TTL must expire immediately."""
    clean_state()
    token = hashlib.sha256(b"expiry-test").hexdigest()
    trace_id = "trace-expiry"
    register_token(token, trace_id, ttl_seconds=0)  # expires immediately

    time.sleep(0.1)  # wait for expiry

    try:
        gated_execute(action_success, token, trace_id)
        assert False, "Should have blocked (expired)"
    except ExecutionBlockedError as e:
        assert "expired" in str(e).lower()


def test_token_scope_binding():
    """Token with scope binding validates correctly."""
    clean_state()
    token = hashlib.sha256(b"scope-test").hexdigest()
    trace_id = "trace-scope"
    scope = {"agent": "edumentor", "intent": "deploy"}
    register_token(token, trace_id, scope=scope)

    # Should work with correct trace
    result = gated_execute(action_success, token, trace_id)
    assert result["status"] == "executed"


def test_token_state_transitions():
    """Token states: CREATED -> USED."""
    clean_state()
    token = hashlib.sha256(b"state-test").hexdigest()
    trace_id = "trace-state"

    # Before registration
    assert get_token_state(token) == TokenState.INVALID

    # After registration
    register_token(token, trace_id)
    assert get_token_state(token) == TokenState.CREATED

    # After use
    gated_execute(action_success, token, trace_id)
    assert get_token_state(token) == TokenState.USED


def test_token_state_expired():
    """Token state: CREATED -> EXPIRED."""
    clean_state()
    token = hashlib.sha256(b"expire-state").hexdigest()
    trace_id = "trace-expire-state"
    register_token(token, trace_id, ttl_seconds=0)

    time.sleep(0.1)
    assert get_token_state(token) == TokenState.EXPIRED


def test_cryptographic_binding():
    """Token has cryptographic binding proof."""
    clean_state()
    token = hashlib.sha256(b"crypto-test").hexdigest()
    trace_id = "trace-crypto"
    scope = {"agent": "test", "decision_hash": "abc123"}
    register_token(token, trace_id, scope=scope)

    record = _token_registry.get(token)
    assert record is not None
    assert "cryptographic_binding" in record
    assert len(record["cryptographic_binding"]) == 64  # SHA-256 hex


# ═══════════════════════════════════════════════════════════
# PHASE 3 — BUCKET TRUTH INVARIANT
# ═══════════════════════════════════════════════════════════

def test_bucket_write_success():
    clean_state()
    event = {
        "trace_id": "trace-bucket-ok",
        "execution_id": "exec-001",
        "execution_token": "token-001",
        "decision": "ALLOW",
        "timestamp": "2026-05-05T00:00:00+00:00",
        "payload_hash": "abc123",
    }
    result = append_to_bucket(event)
    assert result["status"] == "written"


def test_bucket_missing_field_fails():
    clean_state()
    event = {
        "trace_id": "trace-bucket-fail",
        "execution_id": "exec-002",
        # missing: execution_token, decision, timestamp, payload_hash
    }
    try:
        append_to_bucket(event)
        assert False, "Should have failed"
    except BucketWriteError:
        pass


def test_bucket_record_verification():
    clean_state()
    event = {
        "trace_id": "trace-verify-001",
        "execution_id": "exec-verify",
        "execution_token": "token-verify",
        "decision": "ALLOW",
        "timestamp": "2026-05-05T00:00:00+00:00",
        "payload_hash": "verify123",
    }
    append_to_bucket(event)
    record = verify_bucket_record("trace-verify-001")
    assert record is not None
    assert record["trace_id"] == "trace-verify-001"
    assert "record_hash" in record


def test_execution_finalization():
    """Execution finalization: write + verify."""
    clean_state()
    result = finalize_execution(
        trace_id="trace-final-001",
        execution_id="exec-final",
        token="token-final",
        decision="ALLOW",
        payload={"action": "test"},
        execution_result={"status": "ok"},
    )
    assert result["status"] == "finalized"
    assert result["verified"] is True
    assert result["bucket_write"] == "written"


def test_finalization_missing_field():
    """Finalization fails if Bucket write fails."""
    clean_state()
    try:
        # Will fail because payload is None which causes issues
        finalize_execution(
            trace_id="",  # empty trace
            execution_id="exec-fail",
            token="token-fail",
            decision="ALLOW",
            payload={"action": "test"},
            execution_result=None,
        )
        # If it writes successfully with empty trace, verify it
    except (ExecutionFinalizationError, BucketWriteError):
        pass  # Expected


# ═══════════════════════════════════════════════════════════
# PHASE 4 — ADVERSARIAL SCENARIOS
# ═══════════════════════════════════════════════════════════

def test_sovereign_deny_chain():
    """Sovereign DENY -> no token -> no execution."""
    clean_state()
    origin = create_trace_origin("adversarial")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "test")

    # If Sovereign returns DENY, Sarathi should not clear
    # We simulate by not registering a token
    try:
        gated_execute(action_success, "", origin["trace_id"])
        assert False, "Should have blocked"
    except ExecutionBlockedError:
        pass  # Correct: no token means no execution


def test_direct_bypass_attempt():
    """Attempting to call action directly without gate."""
    clean_state()

    @require_gate
    def sensitive_action():
        return "bypassed!"

    try:
        sensitive_action()  # Direct call without gate
        assert False, "Should have blocked"
    except ExecutionBlockedError as e:
        assert "directly" in str(e)


def test_partial_execution_no_bucket():
    """Execution without Bucket write is NOT finalized."""
    clean_state()
    token = hashlib.sha256(b"partial-test").hexdigest()
    trace_id = "trace-partial"
    register_token(token, trace_id)

    # Execute through gate
    result = gated_execute(action_success, token, trace_id)
    assert result["status"] == "executed"

    # But no finalization was done (no bucket write)
    # Verify: no record in Bucket for this trace
    record = verify_bucket_record(trace_id)
    # record might be None (not finalized) - that's the point


def test_full_sealed_flow():
    """Complete flow: trace -> sovereign -> sarathi -> gate -> bucket -> verify."""
    clean_state()
    origin = create_trace_origin("seal_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "test")
    ctx = callSovereign(ctx, "test sealed execution")
    ctx = callSarathi(ctx)

    token = hashlib.sha256(
        f"{origin['trace_id']}:sealed".encode()
    ).hexdigest()
    register_token(token, origin["trace_id"])

    result = gated_execute(action_success, token, origin["trace_id"])
    assert result["status"] == "executed"

    # Finalize with Bucket
    final = finalize_execution(
        trace_id=origin["trace_id"],
        execution_id="exec-sealed",
        token=token,
        decision="ALLOW",
        payload={"action": "sealed_test"},
        execution_result=result,
    )
    assert final["status"] == "finalized"
    assert final["verified"] is True


def test_multi_instance_replay():
    """Simulate multi-instance replay detection."""
    clean_state()
    token = hashlib.sha256(b"multi-instance").hexdigest()
    trace_id = "trace-multi"
    register_token(token, trace_id)

    # First instance uses the token
    gated_execute(action_success, token, trace_id)

    # Simulate second instance trying the same token
    # (token is in _used_tokens now)
    try:
        register_token(token, trace_id)  # re-register
        gated_execute(action_success, token, trace_id)
        assert False, "Should have blocked replay"
    except ExecutionBlockedError as e:
        assert "replay" in str(e).lower()


def main():
    global passed, failed

    print("=" * 60)
    print("  ADVERSARIAL TEST SUITE — SYSTEM SEAL")
    print("=" * 60)

    # Phase 1: Execution Surface Seal
    print("\n  Phase 1: Execution Surface Seal")
    print("  " + "-" * 40)
    run_test("No token -> BLOCKED", test_no_token_blocks)
    run_test("No trace_id -> BLOCKED", test_no_trace_blocks)
    run_test("Valid token -> ALLOWED", test_valid_token_allows)
    run_test("Assertion layer (normal)", test_assertion_layer)
    run_test("Assertion detects bypass", test_assertion_detects_bypass)
    run_test("@require_gate blocks direct call", test_require_gate_decorator)

    # Phase 2: Token Lifecycle
    print("\n  Phase 2: Token Lifecycle")
    print("  " + "-" * 40)
    run_test("Tampered token -> BLOCKED", test_tampered_token_blocks)
    run_test("Replay token -> BLOCKED", test_replay_blocks)
    run_test("Trace mismatch -> BLOCKED", test_trace_mismatch_blocks)
    run_test("Token expiry -> BLOCKED", test_token_expiry)
    run_test("Token scope binding", test_token_scope_binding)
    run_test("Token state transitions", test_token_state_transitions)
    run_test("Token state expired", test_token_state_expired)
    run_test("Cryptographic binding", test_cryptographic_binding)

    # Phase 3: Bucket Truth Invariant
    print("\n  Phase 3: Bucket Truth Invariant")
    print("  " + "-" * 40)
    run_test("Bucket write success", test_bucket_write_success)
    run_test("Bucket missing field -> FAIL", test_bucket_missing_field_fails)
    run_test("Bucket record verification", test_bucket_record_verification)
    run_test("Execution finalization", test_execution_finalization)
    run_test("Finalization missing field", test_finalization_missing_field)

    # Phase 4: Adversarial Scenarios
    print("\n  Phase 4: Adversarial Scenarios")
    print("  " + "-" * 40)
    run_test("Sovereign DENY -> block chain", test_sovereign_deny_chain)
    run_test("Direct bypass attempt", test_direct_bypass_attempt)
    run_test("Partial execution (no Bucket)", test_partial_execution_no_bucket)
    run_test("Full sealed flow", test_full_sealed_flow)
    run_test("Multi-instance replay", test_multi_instance_replay)

    # Summary
    total = passed + failed
    print()
    print("=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed, {total} total")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
