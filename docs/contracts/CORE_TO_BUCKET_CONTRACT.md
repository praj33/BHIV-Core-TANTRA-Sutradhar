# CORE TO BUCKET CONTRACT — Phase 3

## Strict Contract: Core → Bucket (Siddhesh Narkar)

---

## Flow

```
Execution → Bucket.append(event)
```

Every valid execution MUST write to Bucket. No exceptions.

---

## Event Schema

```json
{
    "trace_id": "string (UUID v4, from Core trace_origin)",
    "execution_id": "string (UUID v4, from task_id)",
    "execution_token": "string (SHA-256, from Sarathi)",
    "decision": "string (ALLOW only — DENY never reaches Bucket)",
    "timestamp": "string (ISO 8601 UTC)",
    "payload_hash": "string (SHA-256 of execution payload)",
    "bucket_write_id": "string (SHA-256 derived, auto-generated)",
    "bucket_write_timestamp": "string (ISO 8601 UTC, auto-generated)",
    "record_hash": "string (SHA-256 of entire record, auto-generated)"
}
```

---

## Rules

| Rule | Enforcement |
|------|-------------|
| **Append-only** | New records only. No updates. |
| **No mutation** | Once written, a record CANNOT be changed |
| **No overwrite** | Same trace_id can have multiple records (but each is unique) |
| **No conditional writes** | Write always happens after valid execution |
| **No deletion** | Records are permanent |

---

## Bucket API (for Siddhesh to implement)

### `POST /bucket/append`

**Request:**
```json
{
    "trace_id": "eb823ecc-...",
    "execution_id": "task-001",
    "execution_token": "sha256...",
    "decision": "ALLOW",
    "timestamp": "2026-05-04T...",
    "payload_hash": "sha256...",
    "bucket_write_id": "abc123...",
    "bucket_write_timestamp": "2026-05-04T...",
    "record_hash": "sha256..."
}
```

**Response (Success):**
```json
{
    "status": "written",
    "bucket_write_id": "abc123..."
}
```

**Response (Failure):**
```json
{
    "status": "error",
    "error": "reason"
}
```

### `GET /bucket/verify?trace_id=...`

Returns the record for a given trace_id (read-only).

---

## What Core Does

Core calls:
```python
from core.authority.bucket_writer import append_to_bucket

event = {
    "trace_id": ctx.trace_id,
    "execution_id": task_id,
    "execution_token": token,
    "decision": "ALLOW",
    "timestamp": get_normalized_timestamp(),
    "payload_hash": sha256(payload),
}

result = append_to_bucket(event)
```

---

## What Siddhesh Must Implement

| Requirement | Details |
|-------------|---------|
| `POST /bucket/append` | Accept and store the event record |
| Append-only storage | MongoDB, PostgreSQL, or file-based |
| No mutation API | No PUT/PATCH/DELETE endpoints |
| Record integrity | Store `record_hash` for verification |
| Port | 9003 (configurable via `BUCKET_SERVICE_URL`) |

---

## File

[`core/authority/bucket_writer.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/bucket_writer.py)
