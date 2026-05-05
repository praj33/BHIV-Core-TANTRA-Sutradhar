# FAILURE MATRIX — FINAL LOCK (Phase 4)

## Every failure mode. FAIL CLOSED in ALL cases.

---

## Token Failures

| Failure | Behavior | Execution? | Bucket Write? |
|---------|----------|------------|---------------|
| Token missing | `ExecutionBlockedError` | **NO** | **NO** |
| Token tampered | `ExecutionBlockedError` | **NO** | **NO** |
| Token replayed | `ExecutionBlockedError: replay` | **NO** | **NO** |
| Token expired (TTL) | `ExecutionBlockedError: expired` | **NO** | **NO** |
| Token/trace mismatch | `ExecutionBlockedError: mismatch` | **NO** | **NO** |
| Crypto binding fail | `ExecutionBlockedError: binding` | **NO** | **NO** |
| Token validation service down | `ExecutionBlockedError: fail closed` | **NO** | **NO** |

---

## Authority Failures

| Failure | Behavior | Execution? | Bucket Write? |
|---------|----------|------------|---------------|
| Sovereign down | `ConnectionError` | **NO** | **NO** |
| Sovereign DENY | `SarathiEnforcementError` | **NO** | **NO** |
| Sarathi down | `ConnectionError` | **NO** | **NO** |
| No decision signal | `SarathiEnforcementError` | **NO** | **NO** |

---

## Bucket Failures

| Failure | Behavior | Execution? | Bucket Write? | Finalized? |
|---------|----------|------------|---------------|------------|
| External Bucket down, local OK | Falls back to local | YES | LOCAL | YES |
| External + local BOTH down | `BucketWriteError` | YES | **NO** | **NO** |
| Missing required field | `BucketWriteError` | YES | **NO** | **NO** |
| Post-write verify fails | `ExecutionFinalizationError` | YES | YES | **NO** |

---

## Bypass Attempts

| Attempt | Behavior | Execution? |
|---------|----------|------------|
| Direct function call (no gate) | `ExecutionBlockedError` via `@require_gate` | **NO** |
| Ungated execution detected | `RuntimeError: SECURITY PANIC` via assertion | **PANIC** |
| Partial execution (no Bucket) | Execution runs but NOT finalized | **INCOMPLETE** |

---

## Full Chain Failures

| Scenario | What Happens |
|----------|-------------|
| Everything works | trace → decision(ALLOW) → enforcement(CLEARED) → token → gate → execute → bucket → verify → FINALIZED |
| Sovereign down | trace → ConnectionError → STOP |
| Sovereign DENY | trace → decision(DENY) → SarathiEnforcementError → STOP |
| Sarathi down | trace → decision(ALLOW) → ConnectionError → STOP |
| No token | trace → decision → enforcement → ExecutionBlockedError → STOP |
| Token replay | trace → decision → enforcement → token(used) → ExecutionBlockedError → STOP |
| Token expired | trace → decision → enforcement → token(expired) → ExecutionBlockedError → STOP |
| Bucket down | trace → decision → enforcement → token → execute → BucketWriteError → INCOMPLETE |
| Verify fails | trace → decision → enforcement → token → execute → bucket → verify fail → INCOMPLETE |

---

## Guarantees

| Guarantee | Status |
|-----------|--------|
| No execution without token | **ENFORCED** |
| No execution with expired token | **ENFORCED** |
| No replay execution | **ENFORCED** (persistent store) |
| No execution with wrong trace | **ENFORCED** |
| No bypass via direct call | **ENFORCED** (`@require_gate`) |
| Bypass detection post-hoc | **ENFORCED** (`assert_execution_gated()`) |
| No success without Bucket truth | **ENFORCED** (`finalize_execution()`) |
| All failures → FAIL CLOSED | **ENFORCED** |
