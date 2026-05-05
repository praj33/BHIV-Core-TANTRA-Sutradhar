# BUCKET TRUTH INVARIANT — Phase 3

## INVARIANT: Execution success = Bucket write success

---

## Rule

```
IF bucket_write != success → execution = FAILED

No exceptions. No async bypass. No silent failure.
No response is returned before Bucket write is confirmed AND verified.
```

---

## Execution Finalization Layer

```python
from core.authority.bucket_writer import finalize_execution

result = finalize_execution(
    trace_id=trace_id,
    execution_id=task_id,
    token=execution_token,
    decision="ALLOW",
    payload=payload,
    execution_result=execution_result,
)
# Returns ONLY if:
# 1. Bucket write succeeded
# 2. Post-write verification passed (record exists + correct)

# If either fails:
# → ExecutionFinalizationError raised
# → Execution is NOT complete
```

---

## Flow

```
execution = gated_execute(action, token, trace_id)
  |
  +-- action() runs → result
  |
  +-- finalize_execution(trace_id, ...)
      |
      +-- append_to_bucket(event)
      |     +-- Success → continue
      |     +-- Failure → ExecutionFinalizationError (STOP)
      |
      +-- verify_bucket_record(trace_id)
      |     +-- Found + correct → continue
      |     +-- Not found → ExecutionFinalizationError (STOP)
      |
      +-- Return {status: "finalized", verified: true}
```

---

## Zero Scenarios Without Truth

| Scenario | Bucket Write? | Verification? | Execution Status |
|----------|--------------|---------------|-----------------|
| Everything works | ✅ | ✅ | FINALIZED |
| Bucket service down, local works | ✅ (local) | ✅ | FINALIZED |
| Both stores down | ❌ | N/A | FAILED |
| Write succeeds, verify fails | ✅ | ❌ | FAILED |
| Missing required field | ❌ | N/A | FAILED |

---

## Test Proof

```
[PASS] Bucket write success
[PASS] Bucket missing field -> FAIL
[PASS] Bucket record verification
[PASS] Execution finalization (write + verify)
[PASS] Finalization missing field -> FAIL
```
