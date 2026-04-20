# SUTRADHAR TO CORE CONTRACT

## Purpose

This contract defines the **exact structure** of flow payloads that BHIV Core receives from Sutradhar (the routing system).

---

## Inbound Flow Schema

```json
{
    "flow_id":          "string  — Unique flow identifier (assigned by Sutradhar)",
    "source":           "string  — Origin system/channel (e.g., 'web', 'api', 'mobile')",
    "intent":           "string  — What the user/system is trying to do (e.g., 'query', 'analyze', 'process')",
    "context_payload":  "object  — Structured input data (intent-specific)",
    "trace_id":         "string  — TANTRA trace identifier (from trace_origin)",
    "timestamp":        "string  — ISO 8601 UTC timestamp"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `flow_id` | string (UUID) | YES | Unique identifier for this flow, assigned by Sutradhar. Core does NOT generate this. |
| `source` | string | YES | Where the flow originated. Core uses this for context assembly only. |
| `intent` | string | YES | The action intent. Core uses this to build an ActionProposal. |
| `context_payload` | object | YES | Structured data relevant to the intent. Core passes this through without modification. |
| `trace_id` | string (UUID) | YES | TANTRA trace identifier. Must be present for trace spine integrity. |
| `timestamp` | string (ISO 8601) | YES | When Sutradhar dispatched the flow. UTC only. |

### Example Payload

```json
{
    "flow_id": "f7a1b2c3-d4e5-6789-abcd-ef0123456789",
    "source": "web_dashboard",
    "intent": "analyze_transaction",
    "context_payload": {
        "transaction_id": "tx-9876",
        "wallet_address": "0xABCDEF...",
        "amount": 15000,
        "currency": "USD"
    },
    "trace_id": "eb823ecc-0188-4097-95c1-57667c6a9693",
    "timestamp": "2026-04-20T09:30:22.918492+00:00"
}
```

---

## Rules

| Rule | Rationale |
|------|-----------|
| Core does **NOT** validate routing logic | Routing is Sutradhar's responsibility |
| Core does **NOT** modify flow structure | Flow structure is owned by Sutradhar |
| Core does **NOT** generate `flow_id` | Flow identity is assigned by Sutradhar |
| Core does **NOT** reject flow based on intent | Core consumes all structured input |
| Core only consumes structured input | Core is a coordination layer, not a filter |

---

## Validation (Core-side)

Core performs **only structural validation**:
- All required fields present
- `flow_id` is non-empty string
- `trace_id` is non-empty string
- `timestamp` is valid ISO 8601
- `context_payload` is a valid object

Core does **NOT** perform:
- Intent validation (Sutradhar's job)
- Routing validation (Sutradhar's job)
- Business logic validation (Sovereign Core's job)
