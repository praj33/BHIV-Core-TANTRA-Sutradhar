# DISTRIBUTED REPLAY PROTECTION — Phase 2

## Problem

In-memory replay stores are lost on restart and don't work across multiple instances.

## Solution

### Persistent Replay Store

Used tokens are persisted to `logs/replay_protection.jsonl`:

```json
{"token_hash": "sha256(token)", "consumed_at": "2026-05-05T..."}
```

- Written synchronously after token consumption
- Loaded on module import
- Append-only (no deletion)

### Thread Safety

All token operations use `threading.Lock`:

```python
with _lock:
    _token_registry[token] = record
    _used_tokens.add(token)
```

### Multi-Instance Safety

| Scenario | Behavior |
|----------|----------|
| Same instance, replay attempt | Blocked (in-memory `_used_tokens`) |
| Instance restart, replay attempt | Blocked (persistent store loaded) |
| Different instance, same token | Blocked if shared persistent store |

### Configuration

| Config | Default | Env Var |
|--------|---------|---------|
| Replay store file | `logs/replay_protection.jsonl` | `REPLAY_STORE_FILE` |

---

## Test Proof

```
[PASS] Replay token -> BLOCKED
[PASS] Multi-instance replay -> BLOCKED
```
