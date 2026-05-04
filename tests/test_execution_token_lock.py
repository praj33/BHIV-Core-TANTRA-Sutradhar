"""
Execution Token Lock -- Test Suite (Phase 2 + 4 + 5)

Tests:
  Phase 2: Token enforcement proof (no token, valid token, tampered token)
  Phase 4: Bucket write enforcement (write success, write fail = incomplete)
  Phase 5: Full failure matrix validation

Run:
    python tests/test_execution_token_lock.py
"""

import sys
import os
import io
import json
import hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)

from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.trace.time_sync import get_normalized_timestamp
from core.authority import callSovereign, callSarathi
from core.trace.sarathi_enforcer import SarathiEnforcementError
from core.authority.execution_gate import (
    register_token, validate_execution_token, gated_execute,
    mark_token_used, ExecutionBlockedError, _valid_tokens, _used_tokens,
)
from core.authority.bucket_writer import (
    append_to_bucket, verify_bucket_record, BucketWriteError,
    BUCKET_LOG_FILE,
)


def run_test(name, test_fn):
    try:
        test_fn()
        print(f"  [PASS] {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name} -- {str(e)[:100]}")
        return False


def _cleanup():
    """Reset state between tests."""
    _valid_tokens.clear()
    _used_tokens.clear()


# ============================================================
# PHASE 2 -- EXECUTION TOKEN PROOF
# ============================================================

def test_no_token_blocks_execution():
    """Case 1: Without token, execution MUST fail."""
    _cleanup()
    try:
        validate_execution_token("", "trace-123")
        assert False, "Should have been blocked"
    except ExecutionBlockedError as e:
        assert "No execution_token" in str(e)


def test_valid_token_allows_execution():
    """Case 2: With valid token, execution MUST succeed."""
    _cleanup()
    token = "valid-token-abc123"
    trace_id = "trace-valid-001"
    register_token(token, trace_id)

    executed = False
    def action():
        nonlocal executed
        executed = True
        return {"result": "success"}

    result = gated_execute(action, token, trace_id)
    assert executed, "Action was not executed"
    assert result["result"] == "success"


def test_tampered_token_blocks_execution():
    """Case 3: Tampered token MUST be rejected."""
    _cleanup()
    real_token = "real-token-xyz"
    trace_id = "trace-tamper-001"
    register_token(real_token, trace_id)

    tampered_token = "tampered-token-FAKE"
    try:
        validate_execution_token(tampered_token, trace_id)
        assert False, "Should have been blocked"
    except (ExecutionBlockedError, ConnectionError):
        pass  # Expected -- token not found


def test_mismatched_trace_blocks_execution():
    """Case 4: Token bound to wrong trace_id MUST be rejected."""
    _cleanup()
    token = "token-mismatch-001"
    register_token(token, "trace-A")

    try:
        validate_execution_token(token, "trace-B")
        assert False, "Should have been blocked"
    except ExecutionBlockedError as e:
        assert "mismatch" in str(e).lower()


def test_replay_token_blocked():
    """Case 5: Using the same token twice MUST be rejected."""
    _cleanup()
    token = "token-replay-001"
    trace_id = "trace-replay-001"
    register_token(token, trace_id)

    # First use: OK
    gated_execute(lambda: "ok", token, trace_id)

    # Second use: BLOCKED (replay)
    register_token(token, trace_id)  # re-register to test replay detection
    try:
        validate_execution_token(token, trace_id)
        assert False, "Should have been blocked (replay)"
    except ExecutionBlockedError as e:
        assert "replay" in str(e).lower()


def test_gated_execute_full_flow():
    """Full flow: trace -> Sovereign -> Sarathi -> gate -> execute."""
    _cleanup()
    origin = create_trace_origin("gate_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "gate_test")

    # Decision
    ctx = callSovereign(ctx, "execute gate test")
    assert ctx.get_signal("decision").payload["decision"] == "ALLOW"

    # Enforcement
    ctx = callSarathi(ctx)
    assert ctx.get_signal("enforcement").payload["enforcement_status"] == "CLEARED"

    # Generate a mock execution token
    token = hashlib.sha256(f"{origin['trace_id']}:mock".encode()).hexdigest()
    register_token(token, origin["trace_id"])

    # Gated execution
    executed = False
    def real_action():
        nonlocal executed
        executed = True
        return {"status": "completed"}

    result = gated_execute(real_action, token, origin["trace_id"])
    assert executed
    assert result["status"] == "completed"


# ============================================================
# PHASE 4 -- BUCKET WRITE ENFORCEMENT
# ============================================================

def test_bucket_write_success():
    """Valid execution record MUST write to Bucket."""
    # Clean log file
    if os.path.exists(BUCKET_LOG_FILE):
        os.remove(BUCKET_LOG_FILE)

    event = {
        "trace_id": "trace-bucket-001",
        "execution_id": "exec-bucket-001",
        "execution_token": "token-bucket-001",
        "decision": "ALLOW",
        "timestamp": get_normalized_timestamp(),
        "payload_hash": hashlib.sha256(b"test").hexdigest(),
    }

    result = append_to_bucket(event)
    assert result["status"] == "written"
    assert result["bucket_write_id"] is not None

    # Verify record exists
    record = verify_bucket_record("trace-bucket-001")
    assert record is not None
    assert record["trace_id"] == "trace-bucket-001"
    assert record["execution_id"] == "exec-bucket-001"


def test_bucket_missing_field_fails():
    """Missing required field MUST cause write failure."""
    event = {
        "trace_id": "trace-incomplete",
        # Missing execution_id, execution_token, etc.
    }
    try:
        append_to_bucket(event)
        assert False, "Should have raised BucketWriteError"
    except BucketWriteError as e:
        assert "Missing required field" in str(e)


def test_bucket_record_immutable():
    """Record must contain integrity hash (record_hash)."""
    if os.path.exists(BUCKET_LOG_FILE):
        os.remove(BUCKET_LOG_FILE)

    event = {
        "trace_id": "trace-immutable-001",
        "execution_id": "exec-immutable-001",
        "execution_token": "token-immutable-001",
        "decision": "ALLOW",
        "timestamp": get_normalized_timestamp(),
        "payload_hash": hashlib.sha256(b"immutable").hexdigest(),
    }
    append_to_bucket(event)

    record = verify_bucket_record("trace-immutable-001")
    assert record is not None
    assert "record_hash" in record
    assert "bucket_write_id" in record
    assert "bucket_write_timestamp" in record


# ============================================================
# PHASE 5 -- FAILURE MATRIX
# ============================================================

def test_sovereign_deny_blocks_everything():
    """Sovereign DENY -> no token -> no execution -> no Bucket write."""
    _cleanup()
    from core.trace.sovereign_core import SovereignCore
    sc = SovereignCore(policies={"block": {"type": "deny", "deny_keywords": ["forbidden"]}})

    origin = create_trace_origin("deny_full_test")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "deny_test")
    ctx = sc.evaluate(ctx, "this is forbidden")
    assert ctx.get_signal("decision").payload["decision"] == "DENY"

    # Sarathi blocks
    from core.trace.sarathi_enforcer import SarathiEnforcer
    try:
        SarathiEnforcer().enforce(ctx)
        assert False, "Should be blocked"
    except SarathiEnforcementError:
        pass

    # No token means no execution
    try:
        validate_execution_token("", origin["trace_id"])
        assert False, "Should be blocked"
    except ExecutionBlockedError:
        pass


def test_no_token_no_bucket_write():
    """Without valid execution, no Bucket write should happen."""
    _cleanup()
    # Attempt execution without token
    try:
        gated_execute(lambda: "bad", "", "trace-no-token")
        assert False, "Should be blocked"
    except ExecutionBlockedError:
        pass

    # Verify no Bucket record for this trace
    record = verify_bucket_record("trace-no-token")
    assert record is None, "Bucket should NOT have a record for blocked execution"


def test_external_sovereign_down_fail_closed():
    """External Sovereign down -> FAIL CLOSED."""
    import core.authority as auth
    original = auth.USE_EXTERNAL_AUTHORITY
    original_url = auth.SOVEREIGN_SERVICE_URL

    auth.USE_EXTERNAL_AUTHORITY = True
    auth.SOVEREIGN_SERVICE_URL = "http://localhost:59999"

    origin = create_trace_origin("sovereign_down")
    ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], "down_test")

    try:
        auth.callSovereign(ctx, "test")
        assert False, "Should fail closed"
    except ConnectionError:
        pass
    finally:
        auth.USE_EXTERNAL_AUTHORITY = original
        auth.SOVEREIGN_SERVICE_URL = original_url


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  EXECUTION TOKEN LOCK -- VALIDATION SUITE")
    print("=" * 60)

    tests = [
        # Phase 2 -- Token Proof
        ("Phase 2", "No token -> BLOCKED", test_no_token_blocks_execution),
        ("Phase 2", "Valid token -> ALLOWED", test_valid_token_allows_execution),
        ("Phase 2", "Tampered token -> BLOCKED", test_tampered_token_blocks_execution),
        ("Phase 2", "Mismatched trace_id -> BLOCKED", test_mismatched_trace_blocks_execution),
        ("Phase 2", "Replay token -> BLOCKED", test_replay_token_blocked),
        ("Phase 2", "Full gated flow (Sovereign->Sarathi->Gate)", test_gated_execute_full_flow),
        # Phase 4 -- Bucket
        ("Phase 4", "Bucket write success", test_bucket_write_success),
        ("Phase 4", "Bucket missing field -> FAIL", test_bucket_missing_field_fails),
        ("Phase 4", "Bucket record has integrity hash", test_bucket_record_immutable),
        # Phase 5 -- Failure Matrix
        ("Phase 5", "Sovereign DENY -> full block chain", test_sovereign_deny_blocks_everything),
        ("Phase 5", "No token -> no Bucket write", test_no_token_no_bucket_write),
        ("Phase 5", "External Sovereign down -> fail closed", test_external_sovereign_down_fail_closed),
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
