# TRACE PROPAGATION MAP — Phase 2

## Immutable Trace Flow

The trace_id propagates through the following layers without mutation:

```
Core (origin)
  |  trace_id generated (UUID v4)
  v
Sovereign Core (decision)
  |  SAME trace_id — decision signal appended
  v
Sarathi (enforcement)
  |  SAME trace_id — enforcement signal appended
  v
Execution (agent processing)
  |  SAME trace_id — execution signal appended
  v
Pravah (passive observer)
     SAME trace_id — observation signal emitted
```

## Immutability Enforcement

File: [`core/trace/trace_context.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/trace/trace_context.py)

`TraceContext` is a **frozen dataclass** (`@dataclass(frozen=True)`).

| Property | Enforcement |
|----------|-------------|
| trace_id cannot be modified | Python `FrozenInstanceError` on mutation attempt |
| Signals are accumulated by creating NEW context | `add_signal()` returns a new `TraceContext` |
| Original context is never mutated | Verified in test `test_signal_addition_creates_new_context` |
| trace_id is identical across all layers | Verified in test `test_trace_id_preserved_across_signals` |

## Signal Accumulation Pattern

```python
# Each layer creates a NEW context — never mutates
ctx = create_trace_context(trace_id, timestamp, source)     # origin signal
ctx = sovereign_core.evaluate(ctx, input_data)               # + decision signal
ctx = sarathi.enforce(ctx)                                   # + enforcement signal
ctx = ctx.add_signal(execution_signal)                       # + execution signal
ctx = pravah.emit(ctx)                                       # + observation signal
```

## Propagation Verification

Test `test_full_trace_end_to_end` verifies the complete signal chain:
```
["origin", "decision", "enforcement", "execution", "observation"]
```

**Propagation is proven: immutable, same trace_id at every layer.**
