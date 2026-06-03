# REVIEW PACKET — Sovereign Signer (Authority Hardening)

Date: 2026-06-03
Owner: Raj Prajapati
Module: BHIV Core — ED25519 Cryptographic Authority Signing

---

## 1. WHAT WAS BUILT

core/authority/sovereign_signer.py:
- Canonical Sovereign Decision Schema (bhiv.sovereign.decide/v1.0)
- Deterministic SHA-256 decision hashing (fixed field order, excludes signature)
- ED25519 signing utility (private key signs decision_hash only)
- ED25519 verification helper (recomputes hash, checks signature, detects tamper)
- Evaluator Identity Registry (AUTHORIZED_EVALUATORS set)
- Key management (auto-generate + persist PEM keys to config/keys/)

tests/test_sovereign_signer.py:
- 29 tests across 8 phases (all pass)

docs/contracts/AUTHORIZED_EVALUATORS.md:
- Registry of approved evaluator identities

---

## 2. CANONICAL SCHEMA

```json
{
  "schema_version": "bhiv.sovereign.decide/v1.0",
  "trace_id": "<UUID>",
  "decision": "ALLOW | DENY | ESCALATE",
  "decision_hash": "<sha256>",
  "policy_reference": "<policy_pack_id@version>",
  "input_hash": "<sha256>",
  "timestamp": "<RFC3339 UTC>",
  "evaluator_id": "sovereign_bhiv_core",
  "ed25519_signature": "<hex signature>"
}
```

Rules:
- No extra fields
- No mutation post-signing
- Deterministic serialization only (fixed field order, no spaces)
- api_key NEVER in external payloads

---

## 3. SIGNING FLOW

Step 1: build_canonical_decision() — constructs unsigned payload
Step 2: compute_decision_hash() — SHA-256 of canonical JSON (excludes signature + decision_hash)
Step 3: sign_decision() — ED25519 signs the decision_hash bytes
Step 4: verify_signature() — recomputes hash, verifies signature, detects any mutation

Private key:
- Stored in config/keys/sovereign_ed25519.pem
- NEVER included in payloads
- NEVER transmitted externally

Public key:
- Stored in config/keys/sovereign_ed25519_pub.pem
- Shareable with Sarathi/Hemanth for verification
- Exportable via get_public_key_hex()

---

## 4. REAL E2E PROOF (Phase 8)

trace_id: 26446947-3b13-4531-97d5-9f3511170da7

Signed decision:
```json
{
  "decision": "ALLOW",
  "decision_hash": "ab490d910cd6c04b953872764fd6dc2894fccb280a29d7039284bb42331b7ae2",
  "signature": "8420f73ade82b351422172bd9424ad73...",
  "signature_verified": true
}
```

Flow:
- Core origin → trace_id generated
- Sovereign decision → signed with ED25519
- Signature verified → using public key
- Sarathi enforcement → CLEARED
- Execution → gated, token-protected
- Bucket → finalized, verified=true
- InsightFlow → trace emitted

Same trace_id at every layer: VERIFIED
Same decision_hash at every layer: VERIFIED
Signature verification: PASSED

Public key: ca087b33d011dadfef89c2df05301c420766f29ba369d12ff2c601ab637171dc

---

## 5. TAMPER-FAILURE PROOF (Phase 6)

Mutation: decision changed after signing → TAMPER DETECTED
Mutation: trace_id changed after signing → TAMPER DETECTED
Mutation: timestamp changed after signing → TAMPER DETECTED
Mutation: input_hash changed after signing → TAMPER DETECTED
Wrong signing key → SIGNATURE INVALID
Missing signature → REJECTED
All tamper attempts: DETECTED AND BLOCKED

---

## 6. REPLAY-FAILURE PROOF

Reused signed payload:
- Signature itself is still valid (it doesn't expire)
- Replay blocked at execution_gate level via token + trace_id uniqueness
- Same token reuse → ExecutionBlockedError("replay detected")

---

## 7. SARATHI COMPATIBILITY (Phase 5)

Sarathi can:
- Ingest the canonical schema (all required fields present)
- Verify ED25519 signature using Core's public key
- Reject tampered decisions (modified fields → hash mismatch)
- Handle DENY decisions correctly

Hemanth (Sarathi) needs:
- Core's public key hex: ca087b33d011dadfef89c2df05301c420766f29ba369d12ff2c601ab637171dc
- verify_signature() function or equivalent ED25519 verification

---

## 8. BUCKET + INSIGHTFLOW COMPATIBILITY (Phase 7)

Bucket:
- Signed decision stored as part of execution payload
- decision_hash retrievable post-write
- Record integrity verified via finalize_execution()

InsightFlow:
- Signed authority payload included in trace chain
- Signature verification status observable
- Full chain: origin → sovereign (signed) → sarathi → execution → bucket

---

## 9. EVALUATOR IDENTITY (Phase 4)

Authorized evaluators:
- sovereign_bhiv_core (internal)
- sovereign_bhiv_core_v2 (reserved)
- sovereign_external_primary (Aakanksha)

Unauthorized evaluator → EvaluatorIdentityError
No fallback. No ad-hoc values.

---

## 10. PROOF

Test Suites (ALL PASS):
- Trace Spine: 24 passed, 0 failed
- Authority Extraction: 12 passed, 0 failed
- Execution Token Lock: 12 passed, 0 failed
- Adversarial Seal: 24 passed, 0 failed
- TANTRA Convergence: 21 passed, 0 failed
- Live Integration: 17 passed, 0 failed
- Sovereign Signer: 29 passed, 0 failed
- TOTAL: 139 passed, 0 failed

Proof artifact: logs/sovereign_signer_proof.json
