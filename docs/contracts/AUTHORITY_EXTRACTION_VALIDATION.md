# AUTHORITY EXTRACTION VALIDATION — Phase 6

## Failure + Security Validation

This document proves all failure and security scenarios are handled correctly.

---

## Test Results (6/6 PASS)

| Scenario | Expected | Result |
|----------|----------|--------|
| Sovereign DENY decision | Execution BLOCKED | PASS |
| Missing decision signal | FAIL CLOSED (SarathiEnforcementError) | PASS |
| External service unreachable | FAIL CLOSED (ConnectionError) | PASS |
| Sarathi called without Sovereign | FAIL CLOSED (SarathiEnforcementError) | PASS |
| No fallback execution path | assert_cleared fails without enforcement | PASS |
| Trace survives authority failure | trace_id + signals intact after DENY | PASS |

---

## Failure Modes

### Sovereign Down --> FAIL CLOSED

```
Core calls external Sovereign at http://localhost:9001
  --> Service unreachable
  --> ConnectionError raised
  --> NO decision recorded
  --> NO execution possible
  --> System HALTS
```

**There is NO fallback to internal when external mode is selected.**

### Sarathi Down --> FAIL CLOSED

```
Core calls external Sarathi at http://localhost:9002
  --> Service unreachable
  --> ConnectionError raised
  --> NO enforcement signal
  --> NO execution token
  --> Execution BLOCKED
```

### Decision DENY --> Execution Blocked

```
Sovereign returns DENY
  --> Sarathi recognizes DENY
  --> SarathiEnforcementError raised
  --> Execution CANNOT proceed
```

### Replay Attempt --> Rejected

```
Same decision_hash submitted twice to Sarathi
  --> Second request detected as replay
  --> Status: BLOCKED
  --> Reason: "Decision hash replay rejected"
```

### Missing Execution Token --> Blocked

```
No Sarathi enforcement signal in trace
  --> SarathiEnforcer.assert_cleared() raises error
  --> Execution CANNOT proceed
```

---

## Run Tests

```bash
python tests/test_authority_extraction.py
```

## File

[`tests/test_authority_extraction.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/tests/test_authority_extraction.py)
