# PARALLEL EXECUTION LOGGING — Phase 3

## Real-Time Side-by-Side Execution Visibility

---

## How It Works

For every request, Core:
1. Captures input (raw, unhashed)
2. Runs enforcement (Sovereign → Sarathi)
3. Captures output (canonical 6-field format)
4. Emits log to console + file

---

## Console Output (VC-Readable)

```
  trace_id:             9166d389-53c0-40e2-ab6c-bc064ce46f96
  input:                deploy web1-blue service
  verdict:              ALLOW
  decision_id:          d25764e62a469fd5
  decision_hash:        d25764e62a469fd5bf3a56e5e806a497...
  enforcement_binding:  CLEARED:Decision ALLOW validated — execution per
  timing:               0.0ms
```

Output is:
- Real-time (not buffered)
- Readable during VC
- Not delayed

---

## Log File

Logs are written to `logs/parallel_execution.jsonl`:

```json
{
    "type": "PARALLEL_EXECUTION",
    "timestamp": "2026-05-04T...",
    "input": "deploy web1-blue service",
    "input_hash": "sha256...",
    "core_output": {
        "trace_id": "...",
        "decision_id": "...",
        "decision_hash": "...",
        "verdict": "ALLOW",
        "enforcement_binding": "...",
        "timestamp": "..."
    },
    "timing_ms": 0.0,
    "trace_id": "..."
}
```

---

## Usage

```python
from core.authority.parallel_validator import run_core_enforcement

result = run_core_enforcement("user login from Mumbai IP")
# Prints to console immediately
# Writes to logs/parallel_execution.jsonl
# Returns: {"input": ..., "core_output": ..., "trace_id": ..., "timing_ms": ...}
```

---

## File

[`core/authority/parallel_validator.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/parallel_validator.py)
