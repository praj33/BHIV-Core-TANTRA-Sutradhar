# SOVEREIGN SERVICE SETUP — Phase 2

## External Sovereign Decision Service

### Run

```bash
python services/sovereign_service.py
```

Starts on port **9001** (configurable via `SOVEREIGN_PORT` env var).

---

## API

### `POST /sovereign/decide`

**Request:**
```json
{
    "trace_id": "eb823ecc-0188-4097-95c1-57667c6a9693",
    "input": "Explain blockchain technology",
    "context": {}
}
```

**Response (ALLOW):**
```json
{
    "trace_id": "eb823ecc-0188-4097-95c1-57667c6a9693",
    "decision": "ALLOW",
    "policy_reference": "bhiv.core.default_allow_policy",
    "input_hash": "c2340b9c75aa754fffc10bc951fb64ec...",
    "decision_hash": "7a8f3b2e1d4c5a6b9e8f7a6b5c4d3e2f...",
    "timestamp": "2026-04-24T10:30:00.000000+00:00"
}
```

**Response (DENY):**
```json
{
    "trace_id": "eb823ecc-...",
    "decision": "DENY",
    "policy_reference": "block_policy_name",
    "input_hash": "...",
    "decision_hash": "...",
    "timestamp": "..."
}
```

### `GET /health`

Returns `{"status": "healthy", "service": "sovereign_core"}`

---

## Proof (curl)

```bash
# Test ALLOW
curl -X POST http://localhost:9001/sovereign/decide \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"test-123","input":"hello world","context":{}}'

# Test health
curl http://localhost:9001/health
```

---

## Properties

| Property | Guarantee |
|----------|-----------|
| Same logic as internal | Uses identical policy evaluation |
| Deterministic output | Same inputs always produce same decision + hash |
| decision_hash | SHA-256(trace_id:decision:input_hash:timestamp) |
| No dependencies | stdlib only (http.server, hashlib, json) |

---

## File

[`services/sovereign_service.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/services/sovereign_service.py)
