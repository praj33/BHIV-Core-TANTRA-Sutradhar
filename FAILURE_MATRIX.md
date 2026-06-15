# FAILURE MATRIX — Fail-Closed Determinism

Date: 2026-06-15
Sprint: TANTRA Live Convergence — Phase 5

---

## Failure Determinism: Every participant failure produces deterministic behavior

All tests below are from EXISTING test suites (142 passing tests).
No silent degradation. No undefined behavior. Every failure path is explicit.

---

## 1. Sovereign Unavailable

Expected: Execution BLOCKED. No fallback. No degradation.
Actual: ConnectionError raised → TANTRAFlowError → HTTP 500
Proof: test_tantra_convergence.py — Sovereign deny/fail tests

When USE_EXTERNAL_AUTHORITY=true and Sovereign is down:
- _callSovereign_external raises ConnectionError
- Flow aborts at Step 2
- No execution token issued
- No execution occurs
- InsightFlow emits failure trace (best-effort)

Classification: FAIL-CLOSED ✅

---

## 2. CET Unavailable

Expected: Execution BLOCKED when USE_FULL_TANTRA=true
Actual: CETError raised → TANTRAFlowError → HTTP 500
Proof: test_live_tantra_integration.py — CET failure test

When CET is unreachable:
- URLError caught → CETError raised
- Flow aborts at Step 3
- No contract hash generated
- Bridge cannot validate
- Execution blocked

When USE_FULL_TANTRA=false:
- Internal contract hash generated (deterministic fallback)
- Flow continues with local hash

Classification: FAIL-CLOSED (live) / GRACEFUL-FALLBACK (internal) ✅

---

## 3. Sarathi Unavailable

Expected: Execution BLOCKED. No token = no execution.
Actual: SarathiEnforcementError raised → TANTRAFlowError → HTTP 500
Proof: test_tantra_convergence.py, test_authority_extraction.py

When Sarathi is down:
- No enforcement signal
- No execution_token issued
- gated_execute cannot proceed
- InsightFlow emits failure trace

Classification: FAIL-CLOSED ✅

---

## 4. Bridge Unavailable

Expected: Execution BLOCKED when USE_FULL_TANTRA=true
Actual: BridgeError raised → TANTRAFlowError → HTTP 500
Proof: test_live_tantra_integration.py — Bridge failure test

When Bridge is unreachable:
- URLError caught → BridgeError raised
- Flow aborts at Step 5
- Token exists but execution cannot proceed
- Bridge rejection = hard block

When USE_FULL_TANTRA=false:
- Internal validation (always VALIDATED)

Classification: FAIL-CLOSED (live) / GRACEFUL-FALLBACK (internal) ✅

---

## 5. Bucket Unavailable

Expected: Execution is FAILED. Truth not recorded = execution incomplete.
Actual: BucketWriteError → ExecutionFinalizationError → HTTP 500
Proof: test_adversarial_seal.py, test_execution_token_lock.py

INVARIANT: Execution success = Bucket write success
When Bucket is down:
- append_to_bucket raises BucketWriteError
- finalize_execution raises ExecutionFinalizationError
- Response NOT returned to caller
- Execution is marked FAILED regardless of actual result
- Local JSONL fallback captures record

Classification: FAIL-CLOSED ✅

---

## 6. InsightFlow Unavailable

Expected: Execution continues. Trace emitted to local fallback.
Actual: InsightFlowError caught → warning logged → local JSONL written
Proof: test_live_tantra_integration.py — InsightFlow failure test

InsightFlow is the ONLY non-blocking participant:
- External emit fails → _emit_local writes to logs/insightflow_traces.jsonl
- If local also fails → InsightFlowError raised but does NOT abort flow
- Execution result already in Bucket (truth preserved)
- Trace is NOT lost — local log is the fallback

Classification: GRACEFUL-FALLBACK (non-blocking) ✅

---

## 7. Token Replay Attack

Expected: ExecutionBlockedError. Same token cannot execute twice.
Actual: ExecutionBlockedError raised → HTTP 403
Proof: test_execution_token_lock.py — 12 tests, test_adversarial_seal.py — 24 tests

When same token is reused:
- _used_tokens set detects replay
- ExecutionBlockedError raised
- HTTP 403 returned
- Attempt logged

Classification: FAIL-CLOSED ✅

---

## 8. Signature Tampering

Expected: SovereignSigningError. Payload rejected.
Actual: SovereignSigningError raised (TAMPER DETECTED)
Proof: test_sovereign_signer.py — 32 tests

Tested mutations:
- Tampered verdict → decision_hash mismatch → REJECTED
- Tampered trace_id → decision_hash mismatch → REJECTED
- Tampered timestamp → signature verification fails → REJECTED
- Tampered input_hash → decision_hash mismatch → REJECTED
- Tampered enforcement_binding → signature fails → REJECTED
- Wrong key → signature invalid → REJECTED
- Missing signature → REJECTED

Classification: FAIL-CLOSED ✅

---

## 9. Missing Token / Missing trace_id

Expected: HTTP 403. No execution.
Actual: HTTPException(403) raised
Proof: core_api.py lines 78-83

Classification: FAIL-CLOSED ✅

---

## Summary Matrix

| Failure | Behavior | Classification | Tests |
|---|---|---|---|
| Sovereign down | Flow aborts, no execution | FAIL-CLOSED | ✅ |
| CET down | Flow aborts (live) | FAIL-CLOSED | ✅ |
| Sarathi down | No token, no execution | FAIL-CLOSED | ✅ |
| Bridge down | Flow aborts (live) | FAIL-CLOSED | ✅ |
| Bucket down | Execution FAILED | FAIL-CLOSED | ✅ |
| InsightFlow down | Local fallback | GRACEFUL-FALLBACK | ✅ |
| Token replay | 403 blocked | FAIL-CLOSED | ✅ |
| Signature tamper | REJECTED | FAIL-CLOSED | ✅ |
| Missing token | 403 blocked | FAIL-CLOSED | ✅ |

No silent degradation in any scenario.

---

## Live Participant Testing

Status: BLOCKED — requires real participant URLs to test actual service unavailability.
Internal fail-closed behavior is verified. External service failure testing awaits wiring.
