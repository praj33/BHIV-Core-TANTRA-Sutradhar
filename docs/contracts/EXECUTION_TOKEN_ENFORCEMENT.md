# EXECUTION TOKEN ENFORCEMENT — Phase 1

## Objective

Execution MUST require an `execution_token` from Sarathi. No exceptions. No bypass. No fallback.

---

## What Changed (Authority Made UNAVOIDABLE)

Previous state: Gate module existed but execution surfaces were NOT wired.
**Current state: ALL execution surfaces now REQUIRE token. No path exists without it.**

### Surfaces Locked

| # | Surface | File | Enforcement |
|---|---------|------|-------------|
| 1 | `POST /execute_task` | `core_api.py` | **403 if no token** |
| 2 | `POST /execute_sequence` | `core_api.py` | **403 if no token** |
| 3 | `execute_task()` | `orchestration/core_orchestrator.py` | **Returns BLOCKED if no token** |
| 4 | `execute_sequence()` | `orchestration/core_orchestrator.py` | **Calls execute_task() which blocks** |
| 5 | `POST /handle_task` | `mcp_bridge.py` | **Must go through authority** |

### Defense-in-Depth (2 layers)

```
Layer 1 — API (core_api.py):
  POST /execute_task
    → payload.execution_token missing? → HTTP 403
    → payload.trace_id missing? → HTTP 403

Layer 2 — Orchestrator (core_orchestrator.py):
  execute_task(payload)
    → payload['execution_token'] missing? → return {status: "blocked"}
    → payload['trace_id'] missing? → return {status: "blocked"}
```

Even if Layer 1 is somehow bypassed, Layer 2 blocks.

---

## Gate Function

```python
from core.authority.execution_gate import gated_execute, register_token

# In core_api.py:
register_token(payload.execution_token, payload.trace_id)
result = gated_execute(execute_task, token, trace_id, payload.dict())
```

---

## Validation Chain

```
POST /execute_task {execution_token, trace_id, input}
  |
  +-- 1. token empty? → HTTP 403 (BLOCKED)
  |
  +-- 2. register_token(token, trace_id)
  |
  +-- 3. gated_execute():
  |       +-- token in _used_tokens? → BLOCK (replay)
  |       +-- token in _valid_tokens, trace matches? → EXECUTE
  |       +-- token unknown? → try external Sarathi → BLOCK if fails
  |
  +-- 4. Mark token USED (before execution)
  |
  +-- 5. EXECUTE action_fn
  |
  +-- 6. append_to_bucket(event) → FAIL CLOSED if write fails
```

---

## Failure Cases

| Scenario | Layer | Result |
|----------|-------|--------|
| No token in request | API | HTTP 403 |
| No trace_id in request | API | HTTP 403 |
| No token in orchestrator | Orchestrator | `{status: "blocked"}` |
| Invalid/tampered token | Gate | ExecutionBlockedError |
| Mismatched trace_id | Gate | ExecutionBlockedError |
| Replayed token | Gate | ExecutionBlockedError |
| Sarathi unreachable | Gate | ExecutionBlockedError (fail closed) |
| Bucket write fails | Writer | BucketWriteError (execution incomplete) |

**There is NO path to execution without a valid token.**

---

## Files Modified

| File | Change |
|------|--------|
| `core_api.py` | Added token/trace_id enforcement to `/execute_task` and `/execute_sequence` |
| `orchestration/core_orchestrator.py` | Added defense-in-depth check in `execute_task()` |
| `core/authority/execution_gate.py` | Token validation + gated execution |
| `core/authority/bucket_writer.py` | Fail-closed truth write |
