# CONTRACT VALIDATION PROOF — Phase 2

## Proof: No system accepts loosely structured input

---

## Rejection Test Results (12/12 PASS)

| # | Test | What Was Rejected | Result |
|---|------|-------------------|--------|
| 1 | Valid sovereign request | Nothing (passed) | ✅ |
| 2 | Missing required field | `input`, `context` | ✅ |
| 3 | Unknown extra field | `extra_field` | ✅ |
| 4 | Invalid enum value | `decision: "MAYBE"` | ✅ |
| 5 | Valid sarathi response | Nothing (passed) | ✅ |
| 6 | Invalid sarathi status | `status: "MAYBE"` | ✅ |
| 7 | Valid bucket record | Nothing (passed) | ✅ |
| 8 | Missing bucket fields | `execution_id`, etc. | ✅ |
| 9 | Valid pravah signal | Nothing (passed) | ✅ |
| 10 | Type mismatch | `trace_id: 12345` (int) | ✅ |
| 11 | Trace continuity pass | All same | ✅ |
| 12 | Trace continuity fail | Different trace_ids | ✅ |

---

## Error Examples (Real)

### Missing Field
```
ContractValidationError: Contract 'sovereign_request' validation failed:
  - Missing required field: 'input'
  - Missing required field: 'context'
```

### Unknown Field
```
ContractValidationError: Contract 'sovereign_request' validation failed:
  - Unknown field: 'extra_field' (not in contract)
```

### Invalid Enum
```
ContractValidationError: Contract 'sovereign_response' validation failed:
  - Invalid value: 'decision' = 'MAYBE', expected one of {'ALLOW', 'DENY'}
```

### Type Mismatch
```
ContractValidationError: Contract 'sovereign_request' validation failed:
  - Type mismatch: 'trace_id' expected str, got int
```

### Trace Continuity Broken
```
ContractValidationError: Trace continuity BROKEN at step 1:
  expected='x', got='y'
```

---

## Reproduce

```bash
python tests/test_tantra_convergence.py
```
