# TANTRA FAILURE MATRIX — Phase 3

## Predictable failure under ALL conditions. FAIL CLOSED always.

---

## Full Pipeline Failure Scenarios

| # | Failure | Layer | Error Type | Trace-Linked? | Deterministic? | Result |
|---|---------|-------|-----------|--------------|----------------|--------|
| 1 | Sovereign unavailable | Authority | `ConnectionError` | YES | YES | FAIL CLOSED |
| 2 | Sarathi unavailable | Authority | `ConnectionError` | YES | YES | FAIL CLOSED |
| 3 | Sovereign DENY | Decision | `SarathiEnforcementError` | YES | YES | FAIL CLOSED |
| 4 | Token missing | Gate | `ExecutionBlockedError` | YES | YES | FAIL CLOSED |
| 5 | Token tampered | Gate | `ExecutionBlockedError` | YES | YES | FAIL CLOSED |
| 6 | Token replayed | Gate | `ExecutionBlockedError` | YES | YES | FAIL CLOSED |
| 7 | Token expired | Gate | `ExecutionBlockedError` | YES | YES | FAIL CLOSED |
| 8 | Bucket down | Truth | `BucketWriteError` | YES | YES | FAIL CLOSED |
| 9 | Schema invalid | Contract | `ContractValidationError` | YES | YES | FAIL CLOSED |
| 10 | Trace_id mutated | Contract | `ContractValidationError` | YES | YES | FAIL CLOSED |

---

## Error Structure

All errors are:
- **Structured**: Exception class with descriptive message
- **Trace-linked**: Error message includes trace_id
- **Reproducible**: Same input → same error string

```python
# Example structured error:
ExecutionBlockedError(
    "EXECUTION BLOCKED: No execution_token provided for trace trace-linked-error-test. "
    "Execution requires a valid token from Sarathi."
)
```

---

## Determinism Proof

Same invalid input run 3 times → identical error string all 3 times:
```
[PASS] Failure is deterministic
```

---

## Test Proof

```
[PASS] Sovereign down -> fail closed
[PASS] Token invalid -> structured error
[PASS] Bucket schema violation
[PASS] Contract schema invalid
[PASS] Failure is deterministic
[PASS] Error is trace-linked
```
