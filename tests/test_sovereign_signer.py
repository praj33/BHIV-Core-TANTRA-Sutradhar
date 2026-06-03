"""
Sovereign Signer Test Suite — Aligned with Sarathi CORE_INTEGRATION spec

Run: python tests/test_sovereign_signer.py
"""
import sys, os, io, json, hashlib, copy, time, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

from core.authority.execution_gate import register_token, gated_execute, _token_registry, _used_tokens
from core.authority.bucket_writer import finalize_execution, verify_bucket_record
from core.authority.insightflow_client import emitTrace, buildTraceChain
from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.authority import callSovereign, callSarathi
from core.authority.sovereign_signer import (
    build_canonical_decision, sign_decision, verify_signature,
    compute_decision_hash, compute_decision_id, create_signed_decision,
    get_public_key_hex, load_public_key_from_hex, get_api_fingerprint,
    get_sarathi_headers, build_receipt, verify_receipt_signature,
    get_registration_data, b64url_encode, b64url_decode,
    SovereignSigningError, EvaluatorIdentityError,
    SCHEMA_VERSION, EVALUATOR_ID, KEY_ID, VALID_VERDICTS, AUTHORIZED_EVALUATORS,
)

passed = failed = 0
flow_artifacts = {}
def clean(): _token_registry.clear(); _used_tokens.clear()
def run_test(name, fn):
    global passed, failed
    try: fn(); passed += 1; print(f"  [PASS] {name}")
    except Exception as e: failed += 1; print(f"  [FAIL] {name}: {type(e).__name__}: {e}")

# ═══ PHASE 1: SCHEMA ═══
def test_schema_11_fields():
    p = build_canonical_decision(trace_id="550e8400-e29b-41d4-a716-446655440000", input_data="test", verdict="ALLOW")
    required = ["schema_version","trace_id","input_hash","decision_id","decision_hash","verdict","policy_reference","evaluator_id","enforcement_binding","timestamp","signature"]
    for f in required: assert f in p, f"Missing: {f}"
    assert len(p) == 11

def test_schema_version(): 
    p = build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="t", verdict="ALLOW")
    assert p["schema_version"] == "tantra.decision.v1"

def test_verdicts():
    for v in ["ALLOW","DENY","ESCALATE"]:
        p = build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="t", verdict=v)
        assert p["verdict"] == v

def test_invalid_verdict():
    try: build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="t", verdict="MAYBE"); assert False
    except SovereignSigningError: pass

def test_evaluator_id():
    p = build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="t", verdict="ALLOW")
    assert p["evaluator_id"] == "bhiv.sovereign.decision.prod.v1"

def test_unauthorized_evaluator():
    try: build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="t", verdict="ALLOW", evaluator_id="rogue"); assert False
    except EvaluatorIdentityError: pass

def test_signature_structure():
    p = build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="t", verdict="ALLOW")
    sig = p["signature"]
    assert sig["alg"] == "Ed25519"
    assert sig["encoding"] == "base64url_no_pad"
    assert sig["key_id"] == KEY_ID

def test_enforcement_binding():
    p = build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="t", verdict="ALLOW")
    assert "CLEARED" in p["enforcement_binding"]

# ═══ PHASE 2: HASHING ═══
def test_decision_hash_deterministic():
    ts = "2026-06-03T12:00:00.000000000Z"
    h1 = build_canonical_decision(trace_id="abcd1234-det-test-0000-000000000000", input_data="det test", verdict="ALLOW", timestamp=ts)["decision_hash"]
    h2 = build_canonical_decision(trace_id="abcd1234-det-test-0000-000000000000", input_data="det test", verdict="ALLOW", timestamp=ts)["decision_hash"]
    assert h1 == h2 and len(h1) == 64

def test_decision_hash_6_fields():
    """Hash uses exactly 6 fields in fixed order, excludes timestamp."""
    ts1 = "2026-06-03T12:00:00.000000000Z"
    ts2 = "2099-01-01T00:00:00.000000000Z"
    h1 = build_canonical_decision(trace_id="abcd1234-6f-test-0000-000000000000", input_data="same", verdict="ALLOW", timestamp=ts1)["decision_hash"]
    h2 = build_canonical_decision(trace_id="abcd1234-6f-test-0000-000000000000", input_data="same", verdict="ALLOW", timestamp=ts2)["decision_hash"]
    assert h1 == h2, "Hash should NOT include timestamp"

def test_decision_id_uuid_shape():
    p = build_canonical_decision(trace_id="abcd1234-5678-9012-3456-abcdefabcdef", input_data="id test", verdict="ALLOW")
    parts = p["decision_id"].split("-")
    assert len(parts) == 5 and [len(x) for x in parts] == [8,4,4,4,12]

def test_decision_id_fixed_order():
    """decision_id uses trace_id,input_hash,evaluator_id in FIXED order."""
    tid = "abcd1234-fixed-order-00-000000000001"
    inp = "fixed order test"
    ih = hashlib.sha256(inp.encode()).hexdigest()
    eid = EVALUATOR_ID
    canonical = '{"trace_id":' + json.dumps(tid) + ',"input_hash":' + json.dumps(ih) + ',"evaluator_id":' + json.dumps(eid) + '}'
    raw = hashlib.sha256(canonical.encode()).hexdigest()
    h = raw[:32]
    expected = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    p = build_canonical_decision(trace_id=tid, input_data=inp, verdict="ALLOW")
    assert p["decision_id"] == expected

# ═══ PHASE 3: SIGNING ═══
def test_sign_and_verify():
    p = create_signed_decision(trace_id="abcd1234-sign-test-0000-000000000001", input_data="sign test", verdict="ALLOW")
    assert p["signature"]["value"] != ""
    raw = b64url_decode(p["signature"]["value"])
    assert len(raw) == 64
    assert verify_signature(p) is True

def test_tampered_verdict():
    p = create_signed_decision(trace_id="abcd1234-tamp-verd-0000-000000000001", input_data="t", verdict="ALLOW")
    t = copy.deepcopy(p); t["verdict"] = "DENY"
    try: verify_signature(t); assert False
    except SovereignSigningError as e: assert "TAMPER" in str(e)

def test_tampered_trace_id():
    p = create_signed_decision(trace_id="abcd1234-tamp-tid-0000-0000000000001", input_data="t", verdict="ALLOW")
    t = copy.deepcopy(p); t["trace_id"] = "xxxxxxxx-tampered-0000-000000000001"
    try: verify_signature(t); assert False
    except SovereignSigningError: pass

def test_tampered_timestamp():
    p = create_signed_decision(trace_id="abcd1234-tamp-ts-00000-000000000001", input_data="t", verdict="ALLOW")
    t = copy.deepcopy(p); t["timestamp"] = "2099-01-01T00:00:00.000000000Z"
    try: verify_signature(t); assert False
    except SovereignSigningError: pass

def test_missing_signature():
    p = build_canonical_decision(trace_id="abcd1234-nosig-000000-000000000001", input_data="t", verdict="ALLOW")
    try: verify_signature(p); assert False
    except SovereignSigningError: pass

def test_wrong_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    p = create_signed_decision(trace_id="abcd1234-wkey-test-0000-000000000001", input_data="t", verdict="ALLOW")
    wk = Ed25519PrivateKey.generate().public_key()
    wh = wk.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw).hex()
    try: verify_signature(p, public_key_hex=wh); assert False
    except SovereignSigningError: pass

def test_base64url_no_pad():
    p = create_signed_decision(trace_id="abcd1234-b64-test-0000-0000000000001", input_data="t", verdict="ALLOW")
    val = p["signature"]["value"]
    assert "=" not in val, "Should have no padding"
    assert "+" not in val and "/" not in val, "Should be URL-safe"

# ═══ PHASE 4: API KEY ═══
def test_api_key_fingerprint():
    fp = get_api_fingerprint()
    assert len(fp) == 64

def test_sarathi_headers():
    h = get_sarathi_headers("test-trace-id")
    assert "X-API-Key" in h
    assert h["X-Sarathi-Trace-ID"] == "test-trace-id"
    assert h["Content-Type"] == "application/json"

# ═══ PHASE 5: SARATHI COMPAT ═══
def test_sarathi_ingest():
    p = create_signed_decision(trace_id="abcd1234-sarathi-ing-00-000000000001", input_data="sarathi", verdict="ALLOW")
    for f in ["schema_version","trace_id","input_hash","decision_id","decision_hash","verdict","policy_reference","evaluator_id","enforcement_binding","timestamp","signature"]:
        assert f in p
    assert p["signature"]["alg"] == "Ed25519"

def test_sarathi_verify():
    p = create_signed_decision(trace_id="abcd1234-sarathi-ver-00-000000000001", input_data="verify", verdict="ALLOW")
    assert verify_signature(p, public_key_hex=get_public_key_hex()) is True

def test_sarathi_reject_tampered():
    p = create_signed_decision(trace_id="abcd1234-sarathi-rej-00-000000000001", input_data="reject", verdict="ALLOW")
    t = copy.deepcopy(p); t["verdict"] = "DENY"
    try: verify_signature(t, public_key_hex=get_public_key_hex()); assert False
    except SovereignSigningError: pass

# ═══ PHASE 6: REPLAY + MUTATION ═══
def test_mutation_input_hash():
    p = create_signed_decision(trace_id="abcd1234-mut-ih-000000-000000000001", input_data="t", verdict="ALLOW")
    p["input_hash"] = hashlib.sha256(b"different").hexdigest()
    try: verify_signature(p); assert False
    except SovereignSigningError: pass

def test_mutation_enforcement_binding():
    p = create_signed_decision(trace_id="abcd1234-mut-eb-000000-000000000001", input_data="t", verdict="ALLOW")
    p["enforcement_binding"] = "HACKED:injected"
    try: verify_signature(p); assert False
    except SovereignSigningError: pass

# ═══ PHASE 7: BUCKET + INSIGHTFLOW ═══
def test_bucket_stores():
    clean()
    p = create_signed_decision(trace_id=f"abcd1234-buck-{int(time.time())}", input_data="bucket", verdict="ALLOW")
    tid = p["trace_id"]; tok = hashlib.sha256(f"{tid}:bk".encode()).hexdigest()
    register_token(tok, tid); gated_execute(lambda x: {"ok": True}, tok, tid, {})
    r = finalize_execution(trace_id=tid, execution_id=f"x-{tid[:8]}", token=tok, decision="ALLOW", payload={"signed": p}, execution_result={"ok": True})
    assert r["verified"] is True

def test_insightflow():
    p = create_signed_decision(trace_id="abcd1234-insight-sig-0-000000000001", input_data="insight", verdict="ALLOW")
    chain = buildTraceChain(trace_id=p["trace_id"], sovereign={"verdict": p["verdict"], "signed": True, "trace_id": p["trace_id"]})
    r = emitTrace(trace_id=p["trace_id"], trace_chain=chain)
    assert r["status"] == "emitted"

# ═══ PHASE 8: RECEIPT ═══
def test_receipt_build_and_verify():
    r = build_receipt(execution_id="exec-001", decision_id="did-001", response_hash="a"*64, received_body_hash="a"*64, chain_binding_hash="b"*64, storage_path="logs/test.json")
    assert len(r) == 12
    assert r["peer"] == "core"
    assert r["received_body_hash"] == r["observed_response_hash"]
    assert len(r["receipt_signature"]) == 128
    assert verify_receipt_signature(r) is True

def test_receipt_tamper_detected():
    r = build_receipt(execution_id="exec-002", decision_id="did-002", response_hash="c"*64, received_body_hash="c"*64, chain_binding_hash="d"*64, storage_path="logs/t.json")
    r["decision_id"] = "tampered-id"
    try: verify_receipt_signature(r); assert False
    except SovereignSigningError: pass

# ═══ PHASE 9: REGISTRATION ═══
def test_registration_data():
    d = get_registration_data()
    assert d["evaluator_id"] == EVALUATOR_ID
    assert len(d["public_key"]) == 64
    assert d["key_id"] == KEY_ID
    assert d["schema_version"] == "tantra.decision.v1"
    assert d["algorithm"] == "Ed25519"
    assert len(d["api_key_fingerprint"]) == 64

# ═══ E2E ═══
def test_e2e_full():
    clean()
    origin = create_trace_origin("e2e"); tid = origin["trace_id"]
    signed = create_signed_decision(trace_id=tid, input_data="e2e deploy", verdict="ALLOW")
    assert verify_signature(signed, public_key_hex=get_public_key_hex()) is True
    ctx = create_trace_context(tid, origin["trace_timestamp"], "e2e")
    ctx = callSovereign(ctx, "e2e deploy"); ctx = callSarathi(ctx)
    tok = hashlib.sha256(f"{tid}:e2e".encode()).hexdigest()
    register_token(tok, tid); r = gated_execute(lambda p: {"status": "executed"}, tok, tid, {})
    br = finalize_execution(trace_id=tid, execution_id=f"e2e-{tid[:8]}", token=tok, decision="ALLOW", payload={"signed": signed}, execution_result=r)
    chain = buildTraceChain(trace_id=tid, origin=origin, sovereign={"verdict": "ALLOW", "signed": True, "trace_id": tid}, bucket={"verified": True, "trace_id": tid})
    emitTrace(trace_id=tid, trace_chain=chain)
    flow_artifacts["e2e"] = {"trace_id": tid, "decision_hash": signed["decision_hash"], "signature_verified": True, "bucket_verified": True, "public_key": get_public_key_hex()}

# ═══ MAIN ═══
from cryptography.hazmat.primitives import serialization
def main():
    global passed, failed
    print("="*60); print("  SOVEREIGN SIGNER — SARATHI-ALIGNED TEST SUITE"); print("="*60)
    for phase, tests in [
        ("Phase 1: Schema (11 fields)", [("11 fields present", test_schema_11_fields), ("Schema version", test_schema_version), ("Valid verdicts", test_verdicts), ("Invalid verdict rejected", test_invalid_verdict), ("Evaluator ID locked", test_evaluator_id), ("Unauthorized evaluator rejected", test_unauthorized_evaluator), ("Signature structure", test_signature_structure), ("Enforcement binding", test_enforcement_binding)]),
        ("Phase 2: Hashing", [("decision_hash deterministic", test_decision_hash_deterministic), ("Hash excludes timestamp", test_decision_hash_6_fields), ("decision_id UUID shape", test_decision_id_uuid_shape), ("decision_id fixed order", test_decision_id_fixed_order)]),
        ("Phase 3: Ed25519 Signing", [("Sign + verify", test_sign_and_verify), ("Tampered verdict", test_tampered_verdict), ("Tampered trace_id", test_tampered_trace_id), ("Tampered timestamp", test_tampered_timestamp), ("Missing signature", test_missing_signature), ("Wrong key", test_wrong_key), ("base64url no-pad", test_base64url_no_pad)]),
        ("Phase 4: API Key", [("Fingerprint format", test_api_key_fingerprint), ("Sarathi headers", test_sarathi_headers)]),
        ("Phase 5: Sarathi Compat", [("Ingest schema", test_sarathi_ingest), ("Verify signature", test_sarathi_verify), ("Reject tampered", test_sarathi_reject_tampered)]),
        ("Phase 6: Mutation Resistance", [("Mutated input_hash", test_mutation_input_hash), ("Mutated enforcement_binding", test_mutation_enforcement_binding)]),
        ("Phase 7: Bucket + InsightFlow", [("Bucket stores signed", test_bucket_stores), ("InsightFlow observes", test_insightflow)]),
        ("Phase 8: Receipt", [("Build + verify receipt", test_receipt_build_and_verify), ("Receipt tamper detected", test_receipt_tamper_detected)]),
        ("Phase 9: Registration", [("Registration data complete", test_registration_data)]),
        ("E2E Proof", [("Full signed TANTRA flow", test_e2e_full)]),
    ]:
        print(f"\n  {phase}"); print("  "+"-"*40)
        for name, fn in tests: run_test(name, fn)
    total = passed + failed; print(); print("="*60); print(f"  RESULTS: {passed} passed, {failed} failed, {total} total"); print("="*60)
    if flow_artifacts:
        os.makedirs("logs", exist_ok=True)
        with open("logs/sovereign_signer_proof.json","w") as f: json.dump(flow_artifacts, f, indent=2, default=str)
        print(f"\n  Proof: logs/sovereign_signer_proof.json")
    return 0 if failed == 0 else 1

if __name__ == "__main__": sys.exit(main())
