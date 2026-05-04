# CORE FAILURE MATRIX — FINAL (Phase 5)

## Every Failure Mode Explicitly Defined

No assumptions. Every case documented.

---

## Sovereign Core Failures

| Failure | Behavior | Execution? | Bucket Write? |
|---------|----------|------------|---------------|
| Sovereign service DOWN | `ConnectionError` raised | **NO** | **NO** |
| Sovereign returns DENY | `SarathiEnforcementError` at Sarathi | **NO** | **NO** |
| Sovereign returns invalid response | `ConnectionError` / parse error | **NO** | **NO** |
| Sovereign timeout | `ConnectionError` | **NO** | **NO** |

**Result: FAIL CLOSED. No decision → no enforcement → no execution.**

---

## Sarathi Failures

| Failure | Behavior | Execution? | Bucket Write? |
|---------|----------|------------|---------------|
| Sarathi service DOWN | `ConnectionError` raised | **NO** | **NO** |
| Sarathi returns BLOCKED | `SarathiEnforcementError` raised | **NO** | **NO** |
| No decision signal in trace | `SarathiEnforcementError` raised | **NO** | **NO** |
| Sarathi timeout | `ConnectionError` | **NO** | **NO** |

**Result: FAIL CLOSED. No enforcement → no token → no execution.**

---

## Execution Token Failures

| Failure | Behavior | Execution? | Bucket Write? |
|---------|----------|------------|---------------|
| No token provided | `ExecutionBlockedError` | **NO** | **NO** |
| Invalid/tampered token | `ExecutionBlockedError` | **NO** | **NO** |
| Token/trace_id mismatch | `ExecutionBlockedError` | **NO** | **NO** |
| Replay attempt (same token twice) | `ExecutionBlockedError` | **NO** | **NO** |
| Token validation service DOWN | `ExecutionBlockedError` (fail closed) | **NO** | **NO** |

**Result: FAIL CLOSED. Invalid token → execution impossible.**

---

## Bucket Failures

| Failure | Behavior | Execution? | Bucket Write? |
|---------|----------|------------|---------------|
| External Bucket service DOWN | Falls back to local log | YES | **LOCAL** |
| External Bucket + local log BOTH fail | `BucketWriteError` | YES but **INCOMPLETE** | **NO** |
| Missing required field in event | `BucketWriteError` | YES but **INCOMPLETE** | **NO** |

**Result: FAIL CLOSED. If no truth store available, execution is INCOMPLETE.**

---

## Full Chain Failure Scenarios

| Scenario | What Happens |
|----------|-------------|
| Everything works | trace → decision(ALLOW) → enforcement(CLEARED) → token → execute → Bucket write → COMPLETE |
| Sovereign down | trace → ConnectionError → STOP |
| Sovereign DENY | trace → decision(DENY) → SarathiEnforcementError → STOP |
| Sarathi down | trace → decision(ALLOW) → ConnectionError → STOP |
| No token after Sarathi | trace → decision → enforcement → ExecutionBlockedError → STOP |
| Token replay | trace → decision → enforcement → token(used) → ExecutionBlockedError → STOP |
| Bucket down | trace → decision → enforcement → token → execute → BucketWriteError → INCOMPLETE |

---

## Guarantees

| Guarantee | Status |
|-----------|--------|
| No execution without Sovereign ALLOW | ENFORCED |
| No execution without Sarathi CLEARED | ENFORCED |
| No execution without valid token | ENFORCED |
| No replay execution | ENFORCED |
| No silent success without Bucket | ENFORCED |
| Trace survives all failures | ENFORCED |
| System fails CLOSED on any service down | ENFORCED |

---

## Run Tests

```bash
python tests/test_execution_token_lock.py
```

12/12 tests covering all failure modes.
