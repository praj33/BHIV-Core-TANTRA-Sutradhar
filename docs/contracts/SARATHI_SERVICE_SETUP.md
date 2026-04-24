# SARATHI SERVICE SETUP — Phase 3

## External Sarathi Enforcement Service

### Run

```bash
python services/sarathi_service.py
```

Starts on port **9002** (configurable via `SARATHI_PORT` env var).

---

## API

### `POST /sarathi/enforce`

**Request:**
```json
{
    "trace_id": "eb823ecc-0188-4097-95c1-57667c6a9693",
    "decision": "ALLOW",
    "execution_payload": {"task": "analyze"},
    "decision_hash": "7a8f3b2e1d4c5a6b9e8f7a6b5c4d3e2f..."
}
```

**Response (CLEARED):**
```json
{
    "trace_id": "eb823ecc-...",
    "status": "CLEARED",
    "validation_result": "Decision ALLOW validated -- execution permitted",
    "execution_token": "a1b2c3d4e5f6...",
    "timestamp": "2026-04-24T10:30:01.000000+00:00"
}
```

**Response (BLOCKED):**
```json
{
    "trace_id": "eb823ecc-...",
    "status": "BLOCKED",
    "validation_result": "Decision DENY enforced -- execution blocked",
    "failure_reason": "Sovereign Core denied execution",
    "timestamp": "..."
}
```

### `GET /sarathi/validate-token?token=...`

Validates an execution token. Returns `{"valid": true/false}`.

### `GET /health`

Returns `{"status": "healthy", "service": "sarathi_enforcer"}`

---

## Security Features

| Feature | Implementation |
|---------|---------------|
| **decision_hash verified** | Hash must be present for ALLOW clearance |
| **execution_token issued** | Unique SHA-256 token per cleared execution |
| **replay detection** | Same decision_hash cannot be used twice |
| **strict ALLOW/DENY** | Unknown values are BLOCKED |
| **no execution without token** | Token required for downstream execution |

---

## Proof (curl)

```bash
# Test CLEARED
curl -X POST http://localhost:9002/sarathi/enforce \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"test-123","decision":"ALLOW","decision_hash":"abc123","execution_payload":{}}'

# Test BLOCKED
curl -X POST http://localhost:9002/sarathi/enforce \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"test-123","decision":"DENY","decision_hash":"abc123","execution_payload":{}}'

# Test health
curl http://localhost:9002/health
```

---

## File

[`services/sarathi_service.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/services/sarathi_service.py)
