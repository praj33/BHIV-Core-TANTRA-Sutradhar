# TOKEN LIFECYCLE SPEC — Phase 2

## Token State Machine

```
CREATED → USED → (terminal)
CREATED → EXPIRED → (terminal)
CREATED → INVALID → (terminal)
* → INVALID (if tampered or binding fails)
```

---

## Token Record Structure

```json
{
    "token": "sha256:...",
    "trace_id": "uuid-v4",
    "state": "CREATED | USED | EXPIRED | INVALID",
    "created_at": 1714905600.0,
    "expires_at": 1714905900.0,
    "ttl_seconds": 300,
    "scope": {
        "agent": "edumentor",
        "intent": "deploy",
        "decision_hash": "sha256:..."
    },
    "cryptographic_binding": "sha256(token:trace_id:scope)"
}
```

---

## TTL Enforcement

| Config | Default | Env Var |
|--------|---------|---------|
| Token TTL | 300 seconds (5 min) | `EXECUTION_TOKEN_TTL` |

```python
register_token(token, trace_id, ttl_seconds=300)
# After 300 seconds:
# gated_execute() → ExecutionBlockedError: Token expired
```

---

## Scope Binding

Token is bound to:
1. `trace_id` — cannot be used with different trace
2. `agent` — intended agent target
3. `intent` — execution intent
4. `decision_hash` — Sovereign decision it validates

```python
register_token(token, trace_id, scope={
    "agent": "edumentor",
    "intent": "deploy",
    "decision_hash": "abc123..."
})
```

---

## Cryptographic Binding Proof

```
binding = SHA-256(token + ":" + trace_id + ":" + sorted_json(scope))
```

If binding verification fails → token state → INVALID.

---

## Test Proof

```
[PASS] Token state transitions (INVALID → CREATED → USED)
[PASS] Token state expired (CREATED → EXPIRED)
[PASS] Token scope binding
[PASS] Cryptographic binding (64-char SHA-256)
[PASS] Token expiry -> BLOCKED
```
