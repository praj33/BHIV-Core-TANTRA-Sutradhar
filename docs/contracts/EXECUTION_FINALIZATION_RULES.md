# EXECUTION FINALIZATION RULES — Phase 3

## Rule: Execution is ONLY complete when truth is recorded AND verified.

---

## Finalization Requirements

| Requirement | Enforced By |
|-------------|------------|
| Bucket write succeeds | `append_to_bucket()` or `BucketWriteError` |
| Post-write verification | `verify_bucket_record()` confirms existence |
| trace_id matches | Verification check |
| execution_token matches | Verification check |
| record_hash present | Integrity check |

---

## What Does NOT Count as "Complete"

| Scenario | Status |
|----------|--------|
| Action ran but no Bucket write | **NOT COMPLETE** |
| Bucket write succeeded but not verified | **NOT COMPLETE** |
| Bucket write returned error | **NOT COMPLETE** |
| Post-write verify found wrong trace | **NOT COMPLETE** |
| Async Bucket write (fire-and-forget) | **PROHIBITED** |
| Best-effort write | **PROHIBITED** |

---

## API Behavior

```
POST /execute_task
  → gate passes → action executes → bucket write

  IF bucket write succeeds AND verified:
    → HTTP 200 {status: "success", bucket_write: "written"}

  IF bucket write fails:
    → HTTP 500 {detail: "Execution incomplete: bucket write failed"}

  IF verification fails:
    → HTTP 500 {detail: "Execution incomplete: verification failed"}
```

---

## File

[`core/authority/bucket_writer.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/bucket_writer.py)
