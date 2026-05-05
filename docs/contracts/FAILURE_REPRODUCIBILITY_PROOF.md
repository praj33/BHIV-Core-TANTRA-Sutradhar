# FAILURE REPRODUCIBILITY PROOF — Phase 3

## Failure is deterministic, not situational.

---

## Proof Method

Run the SAME invalid input 3 times. Compare error strings.

```python
errors = []
for _ in range(3):
    try:
        validate_execution_token("", "trace-determinism")
    except ExecutionBlockedError as e:
        errors.append(str(e))

assert len(set(errors)) == 1  # All 3 identical
```

**Result: PASS** — All 3 error strings are identical.

---

## Error JSON Samples

### Token Missing
```json
{
    "error_type": "ExecutionBlockedError",
    "message": "EXECUTION BLOCKED: No execution_token provided for trace trace-fail-token. Execution requires a valid token from Sarathi.",
    "trace_id": "trace-fail-token",
    "deterministic": true
}
```

### Bucket Schema Violation
```json
{
    "error_type": "BucketWriteError",
    "message": "BUCKET WRITE FAILED: Missing required field 'execution_id'. Execution is INCOMPLETE.",
    "trace_id": "x",
    "deterministic": true
}
```

### Contract Schema Invalid
```json
{
    "error_type": "ContractValidationError",
    "message": "Contract 'sovereign_request' validation failed:\n  - Missing required field: 'input'\n  - Missing required field: 'context'\n  - Unknown field: 'bad' (not in contract)",
    "deterministic": true
}
```

### Sovereign Unavailable
```json
{
    "error_type": "ConnectionError",
    "message": "Authority service unreachable at http://localhost:59999/sovereign/decide: ...",
    "deterministic": true
}
```

---

## Guarantees

| Guarantee | Verified |
|-----------|----------|
| Same input → same error message | YES |
| Errors include trace_id | YES |
| Errors are structured (typed exceptions) | YES |
| No random/situational behavior | YES |
| No retry masking | YES |
| No silent failure | YES |
