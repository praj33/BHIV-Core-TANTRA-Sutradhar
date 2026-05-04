# CORE EXECUTION SURFACES

## All Execution Entry Points in BHIV Core

| # | File | Function/Endpoint | Port | Token Gated? |
|---|------|-------------------|------|-------------|
| 1 | `core_api.py` | `POST /execute_task` | 8003 | MUST USE `gated_execute()` |
| 2 | `core_api.py` | `POST /execute_sequence` | 8003 | MUST USE `gated_execute()` |
| 3 | `orchestration/core_orchestrator.py` | `execute_task()` | — | MUST USE `gated_execute()` |
| 4 | `orchestration/core_orchestrator.py` | `execute_sequence()` | — | MUST USE `gated_execute()` |
| 5 | `mcp_bridge.py` | `POST /handle_task` | 8000 | MUST USE `gated_execute()` |

---

## Enforcement Rule

```
ALL execution surfaces MUST call:
    gated_execute(action_fn, token, trace_id)

Direct execution without gated_execute() is PROHIBITED.
```

---

## Gate Module

[`core/authority/execution_gate.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/execution_gate.py)
