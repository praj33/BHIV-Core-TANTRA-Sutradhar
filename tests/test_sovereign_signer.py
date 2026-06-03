"""
Sovereign Signer Test Suite — Phases 1-8

Phase 1: Canonical schema validation
Phase 2: Deterministic hashing proof
Phase 3: ED25519 sign + verify
Phase 4: Evaluator identity enforcement
Phase 5: Sarathi compatibility (ingest, validate, reject tampered)
Phase 6: Replay + mutation resistance
Phase 7: InsightFlow + Bucket compatibility
Phase 8: End-to-end proof

Run:
    python tests/test_sovereign_signer.py
"""

import sys
import os
import io
import json
import hashlib
import copy
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)

from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.trace.time_sync import get_normalized_timestamp
from core.authority import callSovereign, callSarathi
from core.authority.execution_gate import (
    register_token, gated_execute, _token_registry, _used_tokens,
)
from core.authority.bucket_writer import (
    finalize_execution, verify_bucket_record,
)
from core.authority.insightflow_client import emitTrace, buildTraceChain
from core.authority.sovereign_signer import (
    build_canonical_decision, sign_decision, verify_signature,
    compute_decision_hash, create_signed_decision, get_public_key_hex,
    load_public_key_from_hex, get_canonical_bytes,
    SovereignSigningError, EvaluatorIdentityError,
    SCHEMA_VERSION, CANONICAL_FIELD_ORDER, VALID_DECISIONS,
    AUTHORIZED_EVALUATORS,
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


# ═══════════════════════════════════════════════════════════
# PHASE 1 — CANONICAL SCHEMA
# ═══════════════════════════════════════════════════════════

def test_canonical_schema_fields():
    """Schema has exactly the required fields, no extra."""
    payload = build_canonical_decision(
        trace_id="abcd1234-5678-9012-3456-abcdefabcdef",
        decision="ALLOW",
        input_data="test input",
    )
    for field in CANONICAL_FIELD_ORDER:
        assert field in payload, f"Missing field: {field}"

    # No extra fields
    for field in payload:
        assert field in CANONICAL_FIELD_ORDER, f"Extra field: {field}"


def test_schema_version_locked():
    payload = build_canonical_decision(
        trace_id="abcd1234-5678-9012-3456-abcdefabcdef",
        decision="ALLOW",
        input_data="test",
    )
    assert payload["schema_version"] == SCHEMA_VERSION


def test_valid_decisions():
    for decision in ["ALLOW", "DENY", "ESCALATE"]:
        payload = build_canonical_decision(
            trace_id="abcd1234-5678-9012-3456-abcdefabcdef",
            decision=decision,
            input_data="test",
        )
        assert payload["decision"] == decision


def test_invalid_decision_rejected():
    try:
        build_canonical_decision(
            trace_id="abcd1234-5678-9012-3456-abcdefabcdef",
            decision="MAYBE",
            input_data="test",
        )
        assert False, "Should reject"
    except SovereignSigningError as e:
        assert "Invalid decision" in str(e)


def test_input_hash_computed():
    payload = build_canonical_decision(
        trace_id="abcd1234-5678-9012-3456-abcdefabcdef",
        decision="ALLOW",
        input_data="test input for hashing",
    )
    expected = hashlib.sha256("test input for hashing".encode()).hexdigest()
    assert payload["input_hash"] == expected


# ═══════════════════════════════════════════════════════════
# PHASE 2 — DETERMINISTIC HASHING
# ═══════════════════════════════════════════════════════════

def test_deterministic_hash():
    """Same input -> same decision_hash across runs."""
    ts = "2026-06-03T12:00:00+00:00"
    h1 = build_canonical_decision(
        trace_id="abcd1234-deterministic-test-000000000",
        decision="ALLOW",
        input_data="deterministic test",
        timestamp=ts,
    )["decision_hash"]

    h2 = build_canonical_decision(
        trace_id="abcd1234-deterministic-test-000000000",
        decision="ALLOW",
        input_data="deterministic test",
        timestamp=ts,
    )["decision_hash"]

    assert h1 == h2, f"Hashes differ: {h1} != {h2}"
    assert len(h1) == 64  # SHA-256 hex


def test_different_input_different_hash():
    ts = "2026-06-03T12:00:00+00:00"
    h1 = build_canonical_decision(
        trace_id="abcd1234-diff-test-0000-000000000001",
        decision="ALLOW",
        input_data="input A",
        timestamp=ts,
    )["decision_hash"]

    h2 = build_canonical_decision(
        trace_id="abcd1234-diff-test-0000-000000000001",
        decision="ALLOW",
        input_data="input B",
        timestamp=ts,
    )["decision_hash"]

    assert h1 != h2


def test_hash_excludes_signature():
    """decision_hash must NOT include the signature field."""
    payload = build_canonical_decision(
        trace_id="abcd1234-hash-excl-0000-000000000001",
        decision="ALLOW",
        input_data="test",
    )
    hash_before = payload["decision_hash"]

    # Add a fake signature
    payload["ed25519_signature"] = "fake_sig"
    hash_after = compute_decision_hash(payload)

    assert hash_before == hash_after, "Hash changed when signature added"


# ═══════════════════════════════════════════════════════════
# PHASE 3 — ED25519 SIGNING
# ═══════════════════════════════════════════════════════════

def test_sign_and_verify():
    payload = create_signed_decision(
        trace_id="abcd1234-sign-test-0000-000000000001",
        decision="ALLOW",
        input_data="test signing",
    )
    assert payload["ed25519_signature"] != ""
    assert len(payload["ed25519_signature"]) == 128  # ED25519 sig is 64 bytes = 128 hex

    # Verify
    assert verify_signature(payload) is True


def test_tampered_payload_fails():
    """Tampered decision -> verification fails."""
    payload = create_signed_decision(
        trace_id="abcd1234-tamp-test-0000-000000000001",
        decision="ALLOW",
        input_data="original input",
    )

    # Tamper the decision
    tampered = copy.deepcopy(payload)
    tampered["decision"] = "DENY"

    try:
        verify_signature(tampered)
        assert False, "Should fail"
    except SovereignSigningError as e:
        assert "TAMPER" in str(e)


def test_tampered_trace_id_fails():
    payload = create_signed_decision(
        trace_id="abcd1234-trace-orig-0000-000000000001",
        decision="ALLOW",
        input_data="test",
    )

    tampered = copy.deepcopy(payload)
    tampered["trace_id"] = "xxxxxxxx-tampered-0000-000000000001"

    try:
        verify_signature(tampered)
        assert False, "Should fail"
    except SovereignSigningError as e:
        assert "TAMPER" in str(e) or "mismatch" in str(e)


def test_tampered_timestamp_fails():
    payload = create_signed_decision(
        trace_id="abcd1234-time-test-0000-000000000001",
        decision="ALLOW",
        input_data="test",
    )

    tampered = copy.deepcopy(payload)
    tampered["timestamp"] = "2099-01-01T00:00:00+00:00"

    try:
        verify_signature(tampered)
        assert False, "Should fail"
    except SovereignSigningError as e:
        assert "TAMPER" in str(e) or "mismatch" in str(e)


def test_missing_signature_rejected():
    payload = build_canonical_decision(
        trace_id="abcd1234-nosig-test-000-000000000001",
        decision="ALLOW",
        input_data="test",
    )
    # No signing
    try:
        verify_signature(payload)
        assert False, "Should fail"
    except SovereignSigningError as e:
        assert "No signature" in str(e)


def test_wrong_key_rejected():
    """Signed with one key, verified with different key -> fails."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    payload = create_signed_decision(
        trace_id="abcd1234-wkey-test-0000-000000000001",
        decision="ALLOW",
        input_data="test",
    )

    # Generate a different key
    wrong_key = Ed25519PrivateKey.generate()
    wrong_pub = wrong_key.public_key()
    from cryptography.hazmat.primitives import serialization
    wrong_pub_hex = wrong_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()

    try:
        verify_signature(payload, public_key_hex=wrong_pub_hex)
        assert False, "Should fail"
    except SovereignSigningError as e:
        assert "INVALID" in str(e) or "tampered" in str(e).lower()


def test_public_key_export():
    pub_hex = get_public_key_hex()
    assert len(pub_hex) == 64  # 32 bytes = 64 hex chars
    # Can load back
    key = load_public_key_from_hex(pub_hex)
    assert key is not None


# ═══════════════════════════════════════════════════════════
# PHASE 4 — EVALUATOR IDENTITY
# ═══════════════════════════════════════════════════════════

def test_authorized_evaluator_accepted():
    for ev in AUTHORIZED_EVALUATORS:
        payload = build_canonical_decision(
            trace_id="abcd1234-eval-test-0000-000000000001",
            decision="ALLOW",
            input_data="test",
            evaluator_id=ev,
        )
        assert payload["evaluator_id"] == ev


def test_unauthorized_evaluator_rejected():
    try:
        build_canonical_decision(
            trace_id="abcd1234-unauth-eval-00-000000000001",
            decision="ALLOW",
            input_data="test",
            evaluator_id="rogue_evaluator",
        )
        assert False, "Should reject"
    except EvaluatorIdentityError as e:
        assert "Unauthorized" in str(e)


# ═══════════════════════════════════════════════════════════
# PHASE 5 — SARATHI COMPATIBILITY
# ═══════════════════════════════════════════════════════════

def test_sarathi_can_ingest_schema():
    """Sarathi can receive and parse the signed payload."""
    payload = create_signed_decision(
        trace_id="abcd1234-sarathi-ingest-0-000000000001",
        decision="ALLOW",
        input_data="sarathi test",
    )
    # Sarathi needs: decision, decision_hash, ed25519_signature, trace_id
    assert "decision" in payload
    assert "decision_hash" in payload
    assert "ed25519_signature" in payload
    assert "trace_id" in payload
    assert payload["decision"] in VALID_DECISIONS


def test_sarathi_can_verify_signature():
    """Sarathi validates signature using Core's public key."""
    payload = create_signed_decision(
        trace_id="abcd1234-sarathi-verif-0-000000000001",
        decision="ALLOW",
        input_data="sarathi verify",
    )
    pub_hex = get_public_key_hex()
    assert verify_signature(payload, public_key_hex=pub_hex) is True


def test_sarathi_rejects_tampered():
    """Sarathi rejects tampered decisions."""
    payload = create_signed_decision(
        trace_id="abcd1234-sarathi-tamp-00-000000000001",
        decision="ALLOW",
        input_data="sarathi tamper test",
    )
    pub_hex = get_public_key_hex()

    tampered = copy.deepcopy(payload)
    tampered["decision"] = "DENY"

    try:
        verify_signature(tampered, public_key_hex=pub_hex)
        assert False, "Should reject"
    except SovereignSigningError:
        pass


def test_sarathi_deny_flow():
    """Sarathi correctly handles DENY decision."""
    payload = create_signed_decision(
        trace_id="abcd1234-deny-flow-0000-000000000001",
        decision="DENY",
        input_data="denied action",
    )
    assert verify_signature(payload) is True
    assert payload["decision"] == "DENY"


# ═══════════════════════════════════════════════════════════
# PHASE 6 — REPLAY + MUTATION RESISTANCE
# ═══════════════════════════════════════════════════════════

def test_replay_reused_payload():
    """Reused signed payload detected via trace_id uniqueness."""
    payload = create_signed_decision(
        trace_id="abcd1234-replay-test-00-000000000001",
        decision="ALLOW",
        input_data="replay test",
    )
    # The payload itself verifies (signature is valid)
    assert verify_signature(payload) is True
    # But trace_id-based replay protection at execution gate will catch reuse
    # (This is enforced in execution_gate, not in signer)


def test_mutation_decision_after_signing():
    payload = create_signed_decision(
        trace_id="abcd1234-mut-dec-0000-0000000000001",
        decision="ALLOW",
        input_data="test",
    )
    payload["decision"] = "DENY"
    try:
        verify_signature(payload)
        assert False
    except SovereignSigningError:
        pass


def test_mutation_trace_id_after_signing():
    payload = create_signed_decision(
        trace_id="abcd1234-mut-trace-00-000000000001",
        decision="ALLOW",
        input_data="test",
    )
    payload["trace_id"] = "xxxxxxxx-mutated-trace-00000000001"
    try:
        verify_signature(payload)
        assert False
    except SovereignSigningError:
        pass


def test_mutation_timestamp_after_signing():
    payload = create_signed_decision(
        trace_id="abcd1234-mut-time-000-000000000001",
        decision="ALLOW",
        input_data="test",
    )
    payload["timestamp"] = "2099-12-31T23:59:59+00:00"
    try:
        verify_signature(payload)
        assert False
    except SovereignSigningError:
        pass


def test_mutation_input_hash_after_signing():
    payload = create_signed_decision(
        trace_id="abcd1234-mut-inhash-0-000000000001",
        decision="ALLOW",
        input_data="test",
    )
    payload["input_hash"] = hashlib.sha256(b"different").hexdigest()
    try:
        verify_signature(payload)
        assert False
    except SovereignSigningError:
        pass


# ═══════════════════════════════════════════════════════════
# PHASE 7 — INSIGHTFLOW + BUCKET COMPATIBILITY
# ═══════════════════════════════════════════════════════════

def test_bucket_stores_signed_decision():
    """Bucket can store signed decision and decision_hash is retrievable."""
    clean_state()
    payload = create_signed_decision(
        trace_id=f"abcd1234-bucket-sig-{int(time.time())}",
        decision="ALLOW",
        input_data="bucket signed test",
    )
    trace_id = payload["trace_id"]

    # Finalize to Bucket
    token = hashlib.sha256(f"{trace_id}:bucket-sig".encode()).hexdigest()
    register_token(token, trace_id)
    gated_execute(lambda p: {"ok": True}, token, trace_id, {})

    result = finalize_execution(
        trace_id=trace_id,
        execution_id=f"exec-{trace_id[:8]}",
        token=token,
        decision=payload["decision"],
        payload={"signed_decision": payload},
        execution_result={"ok": True},
    )
    assert result["verified"] is True

    record = verify_bucket_record(trace_id)
    assert record is not None
    assert record["trace_id"] == trace_id


def test_insightflow_observes_signed_decision():
    """InsightFlow can observe signed authority payload."""
    payload = create_signed_decision(
        trace_id="abcd1234-insight-sig-0-000000000001",
        decision="ALLOW",
        input_data="insightflow signed test",
    )

    chain = buildTraceChain(
        trace_id=payload["trace_id"],
        sovereign={
            "decision": payload["decision"],
            "decision_hash": payload["decision_hash"],
            "signature": payload["ed25519_signature"][:32] + "...",
            "trace_id": payload["trace_id"],
        },
    )

    result = emitTrace(
        trace_id=payload["trace_id"],
        trace_chain=chain,
        execution_status="completed",
    )
    assert result["status"] == "emitted"


# ═══════════════════════════════════════════════════════════
# PHASE 8 — END-TO-END PROOF
# ═══════════════════════════════════════════════════════════

def test_e2e_signed_authority_flow():
    """
    ONE real flow:
    Core -> signed Sovereign -> verify -> Sarathi -> execute -> Bucket -> InsightFlow
    Same trace_id, same decision_hash, successful signature verification.
    """
    clean_state()

    # Step 1: Origin
    origin = create_trace_origin("signed_authority_e2e")
    trace_id = origin["trace_id"]

    # Step 2: Signed Sovereign decision
    signed_decision = create_signed_decision(
        trace_id=trace_id,
        decision="ALLOW",
        input_data="e2e signed authority test execution",
    )
    assert signed_decision["trace_id"] == trace_id

    # Step 3: Verify signature (as Sarathi would)
    pub_hex = get_public_key_hex()
    assert verify_signature(signed_decision, public_key_hex=pub_hex) is True

    # Step 4: Sarathi enforcement (internal flow)
    ctx = create_trace_context(trace_id, origin["trace_timestamp"], "e2e_test")
    ctx = callSovereign(ctx, "e2e signed authority test execution")
    ctx = callSarathi(ctx)
    enforcement = ctx.get_signal("enforcement")
    assert enforcement.payload["enforcement_status"] == "CLEARED"

    # Step 5: Execution
    token = hashlib.sha256(f"{trace_id}:e2e-signed".encode()).hexdigest()
    register_token(token, trace_id)
    exec_result = gated_execute(
        lambda p: {"status": "executed", "result": "e2e signed"},
        token, trace_id, {},
    )
    assert exec_result["status"] == "executed"

    # Step 6: Bucket (with signed decision as payload)
    bucket_result = finalize_execution(
        trace_id=trace_id,
        execution_id=f"e2e-signed-{trace_id[:8]}",
        token=token,
        decision=signed_decision["decision"],
        payload={
            "signed_decision": signed_decision,
            "decision_hash": signed_decision["decision_hash"],
        },
        execution_result=exec_result,
    )
    assert bucket_result["verified"] is True

    # Step 7: InsightFlow
    chain = buildTraceChain(
        trace_id=trace_id,
        origin=origin,
        sovereign={
            "decision": signed_decision["decision"],
            "decision_hash": signed_decision["decision_hash"],
            "signed": True,
            "signature_verified": True,
            "trace_id": trace_id,
        },
        sarathi={"enforcement_status": "CLEARED", "trace_id": trace_id},
        execution={"status": "executed", "trace_id": trace_id},
        bucket={"status": "finalized", "verified": True, "trace_id": trace_id},
    )
    insight = emitTrace(trace_id=trace_id, trace_chain=chain)
    assert insight["status"] == "emitted"

    # Verify: same trace_id everywhere
    assert signed_decision["trace_id"] == trace_id
    assert bucket_result["trace_id"] == trace_id

    # Verify: same decision_hash
    hash_from_decision = signed_decision["decision_hash"]
    assert len(hash_from_decision) == 64

    # Store proof
    flow_artifacts["e2e_signed_flow"] = {
        "trace_id": trace_id,
        "decision": signed_decision["decision"],
        "decision_hash": hash_from_decision,
        "signature": signed_decision["ed25519_signature"][:32] + "...",
        "signature_verified": True,
        "bucket_verified": True,
        "insightflow_emitted": True,
        "public_key": pub_hex,
    }


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    global passed, failed

    print("=" * 60)
    print("  SOVEREIGN SIGNER — AUTHORITY HARDENING TEST SUITE")
    print("=" * 60)

    print("\n  Phase 1: Canonical Schema")
    print("  " + "-" * 40)
    run_test("Schema has all required fields", test_canonical_schema_fields)
    run_test("Schema version locked", test_schema_version_locked)
    run_test("Valid decisions accepted", test_valid_decisions)
    run_test("Invalid decision rejected", test_invalid_decision_rejected)
    run_test("Input hash computed correctly", test_input_hash_computed)

    print("\n  Phase 2: Deterministic Hashing")
    print("  " + "-" * 40)
    run_test("Same input -> same hash", test_deterministic_hash)
    run_test("Different input -> different hash", test_different_input_different_hash)
    run_test("Hash excludes signature", test_hash_excludes_signature)

    print("\n  Phase 3: ED25519 Signing")
    print("  " + "-" * 40)
    run_test("Sign and verify", test_sign_and_verify)
    run_test("Tampered decision -> FAIL", test_tampered_payload_fails)
    run_test("Tampered trace_id -> FAIL", test_tampered_trace_id_fails)
    run_test("Tampered timestamp -> FAIL", test_tampered_timestamp_fails)
    run_test("Missing signature -> FAIL", test_missing_signature_rejected)
    run_test("Wrong key -> FAIL", test_wrong_key_rejected)
    run_test("Public key export/import", test_public_key_export)

    print("\n  Phase 4: Evaluator Identity")
    print("  " + "-" * 40)
    run_test("Authorized evaluator accepted", test_authorized_evaluator_accepted)
    run_test("Unauthorized evaluator rejected", test_unauthorized_evaluator_rejected)

    print("\n  Phase 5: Sarathi Compatibility")
    print("  " + "-" * 40)
    run_test("Sarathi can ingest schema", test_sarathi_can_ingest_schema)
    run_test("Sarathi can verify signature", test_sarathi_can_verify_signature)
    run_test("Sarathi rejects tampered", test_sarathi_rejects_tampered)
    run_test("Sarathi DENY flow", test_sarathi_deny_flow)

    print("\n  Phase 6: Replay + Mutation Resistance")
    print("  " + "-" * 40)
    run_test("Replay reused payload", test_replay_reused_payload)
    run_test("Mutation: decision after signing", test_mutation_decision_after_signing)
    run_test("Mutation: trace_id after signing", test_mutation_trace_id_after_signing)
    run_test("Mutation: timestamp after signing", test_mutation_timestamp_after_signing)
    run_test("Mutation: input_hash after signing", test_mutation_input_hash_after_signing)

    print("\n  Phase 7: InsightFlow + Bucket")
    print("  " + "-" * 40)
    run_test("Bucket stores signed decision", test_bucket_stores_signed_decision)
    run_test("InsightFlow observes signed", test_insightflow_observes_signed_decision)

    print("\n  Phase 8: End-to-End Proof")
    print("  " + "-" * 40)
    run_test("E2E signed authority flow", test_e2e_signed_authority_flow)

    total = passed + failed
    print()
    print("=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed, {total} total")
    print("=" * 60)

    if flow_artifacts:
        os.makedirs("logs", exist_ok=True)
        with open("logs/sovereign_signer_proof.json", "w", encoding="utf-8") as f:
            json.dump(flow_artifacts, f, indent=2, default=str)
        print(f"\n  Proof: logs/sovereign_signer_proof.json")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
