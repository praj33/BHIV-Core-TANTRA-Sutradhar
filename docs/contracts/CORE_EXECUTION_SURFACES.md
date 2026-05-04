# CORE EXECUTION SURFACES — All Entry Points Locked

## All Execution Entry Points in BHIV Core

| # | File | Function/Endpoint | Port | Enforcement | Status |
|---|------|-------------------|------|-------------|--------|
| 1 | `core_api.py` | `POST /execute_task` | 8003 | HTTP 403 if no token | **LOCKED** |
| 2 | `core_api.py` | `POST /execute_sequence` | 8003 | HTTP 403 if no token | **LOCKED** |
| 3 | `orchestration/core_orchestrator.py` | `execute_task()` | — | Returns BLOCKED if no token | **LOCKED** |
| 4 | `orchestration/core_orchestrator.py` | `execute_sequence()` | — | Calls execute_task() which blocks | **LOCKED** |
| 5 | `mcp_bridge.py` | `POST /handle_task` | 8000 | Must go through authority first | **LOCKED** |

---

## Enforcement Rule

```
ALL execution surfaces REQUIRE:
  1. execution_token (from Sarathi, non-empty)
  2. trace_id (from Core trace_origin, non-empty)

Without BOTH → execution is IMPOSSIBLE.
```

---

## What Happens Without Token

```bash
# This request WILL BE REJECTED with 403:
curl -X POST http://localhost:8003/execute_task \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "agent": "edumentor_agent"}'

# Response:
# 403 {"detail": "EXECUTION BLOCKED: execution_token and trace_id are required."}
```

```bash
# This request WILL SUCCEED:
curl -X POST http://localhost:8003/execute_task \
  -H "Content-Type: application/json" \
  -d '{
    "input": "test",
    "agent": "edumentor_agent",
    "execution_token": "<VALID_TOKEN_FROM_SARATHI>",
    "trace_id": "<CORE_GENERATED_TRACE_ID>"
  }'
```

---

## No Optional Paths

| Path | Exists? |
|------|---------|
| Execute without token | **NO** |
| Execute without trace_id | **NO** |
| Execute with replayed token | **NO** |
| Execute without Bucket write | **NO** (fail-closed) |
| Silent execution | **NO** |
| Fallback execution | **NO** |
