# TRACE CROSS-SERVICE PROOF — Phase 5

## Trace Continuity Across Authority Services

This document proves that trace_id flows unchanged across:

```
Core --> Sovereign Core --> Sarathi --> Execution --> Pravah
```

Whether authority runs internally or externally.

---

## Verification Results (12/12 PASS)

### Phase 5 Tests — Trace Continuity

| Test | Result |
|------|--------|
| trace_id unchanged through Sovereign + Sarathi | PASS |
| decision_hash (input_hash) integrity | PASS |
| Execution requires Sarathi clearance | PASS |
| No trace_id regeneration at any layer | PASS |
| trace_hash verifies after full authority flow | PASS |
| Timestamp ordering monotonic across authority | PASS |

---

## What Is Proven

| Assertion | Proof |
|-----------|-------|
| **No mutation** | trace_id identical at origin, after Sovereign, after Sarathi, after execution, after Pravah |
| **No regeneration** | No layer generates a new trace_id -- all propagate the original |
| **decision_hash integrity** | SHA-256(input) matches across pipeline |
| **trace_hash integrity** | SHA-256(trace_id + execution_id + timestamp) verifiable after full flow |
| **execution_token required** | External Sarathi issues token only after ALLOW + valid decision_hash |
| **Timestamp ordering** | All timestamps monotonically non-decreasing |

---

## Cross-Service Flow (External Mode)

```
Core                 External Sovereign          External Sarathi
  |                       |                           |
  |-- POST /decide ------>|                           |
  |    trace_id: abc-123  |                           |
  |<-- decision: ALLOW ---|                           |
  |    decision_hash: x1  |                           |
  |                       |                           |
  |-- POST /enforce ------|-------------------------->|
  |    trace_id: abc-123  |    decision_hash: x1      |
  |<-- status: CLEARED ---|---------------------------|
  |    execution_token: t1|                           |
  |                       |                           |
  SAME trace_id at every step: abc-123
```

---

## Run Tests

```bash
python tests/test_authority_extraction.py
```

## File

[`tests/test_authority_extraction.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/tests/test_authority_extraction.py)
