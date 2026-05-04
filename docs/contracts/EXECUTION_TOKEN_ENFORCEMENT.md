# EXECUTION TOKEN ENFORCEMENT — Phase 1

## Objective

Execution MUST require an `execution_token` from Sarathi. No exceptions.

---

## Gate Function

```python
from core.authority.execution_gate import gated_execute, register_token

# After Sarathi clears:
register_token(execution_token, trace_id)

# Before ANY execution:
result = gated_execute(action_fn, token, trace_id, *args, **kwargs)
```

---

## Validation Chain

```
gated_execute(action, token, trace_id)
  |
  +-- 1. Token empty? --> BLOCK (ExecutionBlockedError)
  |
  +-- 2. Token in _used_tokens? --> BLOCK (replay attack)
  |
  +-- 3. Token in _valid_tokens?
  |       +-- YES: trace_id matches? --> EXECUTE
  |       +-- YES: trace_id mismatch? --> BLOCK
  |       +-- NO: try external validation
  |
  +-- 4. External Sarathi validation
  |       +-- Valid --> EXECUTE
  |       +-- Invalid --> BLOCK
  |       +-- Unreachable --> BLOCK (fail closed)
  |
  +-- 5. Mark token as USED (before execution)
  |
  +-- 6. EXECUTE action_fn
```

---

## Failure Cases

| Scenario | Result |
|----------|--------|
| No token | BLOCKED |
| Invalid token | BLOCKED |
| Mismatched trace_id | BLOCKED |
| Replayed token | BLOCKED |
| Sarathi unreachable | BLOCKED (fail closed) |

---

## File

[`core/authority/execution_gate.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/execution_gate.py)
