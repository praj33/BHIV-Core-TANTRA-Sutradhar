# EXECUTION PATH ASSERTIONS — Phase 1

## Hard Assertion Layer

### `assert_execution_gated()`

Verifies that ALL executions went through the gate. If any ungated execution is detected → **SECURITY PANIC**.

```python
from core.authority.execution_gate import assert_execution_gated

# Call in health checks, audit hooks, startup verification
assert_execution_gated()

# If ungated execution detected:
# RuntimeError: SECURITY PANIC: 2 execution(s) detected without gate!
#               Total=5, Gated=3. SYSTEM INTEGRITY COMPROMISED.
```

### `@require_gate` Decorator

Marks functions as requiring the gate. If called directly → **BLOCKED**.

```python
from core.authority.execution_gate import require_gate

@require_gate
def sensitive_action():
    return "must go through gate"

# Direct call → ExecutionBlockedError
sensitive_action()  # BLOCKED

# Through gate → ALLOWED
gated_execute(sensitive_action, token, trace_id)  # WORKS
```

---

## Defense-in-Depth Layers

```
Layer 1 — API (core_api.py):
  payload.execution_token empty? → HTTP 403
  payload.trace_id empty? → HTTP 403

Layer 2 — Orchestrator (core_orchestrator.py):
  task_payload['execution_token'] missing? → return BLOCKED
  task_payload['trace_id'] missing? → return BLOCKED

Layer 3 — Gate (execution_gate.py):
  validate_execution_token() → ExecutionBlockedError

Layer 4 — Assertion (post-execution):
  assert_execution_gated() → RuntimeError (PANIC)

Layer 5 — Decorator:
  @require_gate → ExecutionBlockedError if direct call
```

---

## Test Proof

```
[PASS] Assertion layer (normal) — counts match
[PASS] Assertion detects bypass — SECURITY PANIC raised
[PASS] @require_gate blocks direct call — ExecutionBlockedError
```
