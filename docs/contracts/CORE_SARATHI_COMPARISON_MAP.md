# CORE ↔ SARATHI COMPARISON MAP — Phase 4

## Field-Level Alignment for 1:1 Comparison

---

## Field Mapping

| Core Field | Sarathi Field | Comparable? | Notes |
|-----------|---------------|-------------|-------|
| `trace_id` | `trace_id` | YES | Same trace propagated to both |
| `decision_id` | `decision_id` | YES | Derived from trace + input |
| `decision_hash` | `decision_hash` | YES | SHA-256 of input — deterministic |
| `verdict` | `verdict` | YES | ALLOW or DENY — exact string match |
| `enforcement_binding` | `enforcement_binding` | YES | Format: `STATUS:description` |
| `timestamp` | `timestamp` | PARTIAL | Timing may differ slightly |

---

## Comparison Rules

| Rule | Enforcement |
|------|-------------|
| No derived values | Fields are raw, not computed from other fields |
| No hidden mappings | 1:1 field names, no renaming |
| String comparison | All fields compared as strings |
| Same input → same hash | `decision_hash` is deterministic |

---

## How to Compare

```python
from core.authority.parallel_validator import compare_outputs

core_output = {...}    # From Core
sarathi_output = {...} # From Sarathi

result = compare_outputs(core_output, sarathi_output)

# result:
# {
#     "match": True/False,
#     "fields_compared": 6,
#     "mismatches": [
#         {"field": "verdict", "core": "ALLOW", "sarathi": "DENY"}
#     ]
# }
```

---

## Expected Results

| Scenario | Expected |
|----------|----------|
| Same input, both systems healthy | ALL fields match (except timestamp) |
| Different input | `decision_hash` will differ |
| Sarathi has different policy | `verdict` may differ |
| Enforcement mismatch | `enforcement_binding` will differ |

---

## File

[`core/authority/parallel_validator.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/parallel_validator.py)
