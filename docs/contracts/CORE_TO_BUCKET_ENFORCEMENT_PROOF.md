# CORE TO BUCKET ENFORCEMENT PROOF — Phase 3

## Proof: Bucket is the ONLY source of truth for execution success

---

## Code Path

```python
# In core_api.py /execute_task:

# 1. Validate token
register_token(payload.execution_token, payload.trace_id)

# 2. Execute through gate
result = gated_execute(execute_task, token, trace_id, payload)

# 3. Finalize (Bucket write + verify)
# If this fails → HTTP 500, execution is INCOMPLETE
bucket_result = append_to_bucket(event)
```

---

## Integrity Validation

Every Bucket record contains:

| Field | Source | Verification |
|-------|--------|-------------|
| `trace_id` | Core trace_origin | Matches request |
| `execution_id` | Task ID | Unique per execution |
| `execution_token` | Sarathi | Matches used token |
| `payload_hash` | SHA-256 of payload | Tamper detection |
| `record_hash` | SHA-256 of entire record | Integrity proof |
| `bucket_write_id` | SHA-256 derived | Unique write ID |
| `bucket_write_timestamp` | Write time | Audit trail |

---

## Post-Write Verification

```python
record = verify_bucket_record(trace_id)
assert record is not None  # Record exists
assert record["trace_id"] == trace_id  # Correct trace
assert record["execution_token"] == token  # Correct token
assert "record_hash" in record  # Integrity hash present
```

---

## Test Proof

```
[PASS] Bucket write success
[PASS] Bucket record verification (post-write)
[PASS] Execution finalization (write + verify + integrity)
```
