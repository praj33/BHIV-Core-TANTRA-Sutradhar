# TANTRA CONTRACT SCHEMA — Phase 2

## Strict Schema Enforcement Across ALL System Boundaries

---

## Contracts

### 1. Core → Sovereign (Decision Request)
```json
{
    "trace_id": "string (UUID, required)",
    "input": "string (required)",
    "context": "dict (required)"
}
```
**Rejects:** unknown fields, missing fields, non-string trace_id

### 2. Sovereign → Core (Decision Response)
```json
{
    "decision": "ALLOW | DENY (enum, required)",
    "input_hash": "string (required)",
    "decision_hash": "string (required)",
    "policy_reference": "string (optional)",
    "timestamp": "string (optional)"
}
```
**Rejects:** decision != ALLOW|DENY, missing hash fields

### 3. Core → Sarathi (Enforcement Request)
```json
{
    "trace_id": "string (required)",
    "decision": "string (required)",
    "decision_hash": "string (required)",
    "execution_payload": "dict (optional)"
}
```

### 4. Sarathi → Core (Enforcement Response)
```json
{
    "status": "CLEARED | BLOCKED (enum, required)",
    "validation_result": "string (optional)",
    "execution_token": "string (optional)",
    "failure_reason": "string (optional)",
    "timestamp": "string (optional)"
}
```
**Rejects:** status != CLEARED|BLOCKED

### 5. Core → Execution (Execution Payload)
```json
{
    "trace_id": "string (required)",
    "execution_token": "string (required)",
    "task_payload": "any (required)",
    "execution_id": "string (optional)"
}
```

### 6. Core → Bucket (Truth Record)
```json
{
    "trace_id": "string (required)",
    "execution_id": "string (required)",
    "execution_token": "string (required)",
    "decision": "string (required)",
    "timestamp": "string (required)",
    "payload_hash": "string (required)"
}
```
**Extended fields (auto-added):** bucket_write_id, bucket_write_timestamp, record_hash

### 7. Core → Pravah (Observation Signal)
```json
{
    "trace_id": "string (required)",
    "event_type": "string (required)",
    "timestamp": "string (required)",
    "payload": "dict (required)",
    "source": "string (optional)"
}
```

---

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| Unknown fields → REJECT | `strict=True` in `validate_contract()` |
| Missing required fields → REJECT | Checked against `required` set |
| Type mismatch → REJECT | Checked against `types` dict |
| Invalid enum → REJECT | Checked against `enum` dict |
| trace_id < 8 chars → REJECT | Format validation |
| Null required field → REJECT | Explicit null check |

---

## File

[`core/authority/contract_validator.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/contract_validator.py)
