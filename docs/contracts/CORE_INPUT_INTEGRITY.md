# CORE INPUT INTEGRITY — Phase 2

## Rule: Core processes EXACT same input as Sarathi. No mutation.

---

## Guarantees

| Guarantee | How |
|-----------|-----|
| No transformation before evaluation | `log_raw_input()` called BEFORE processing |
| No enrichment | Input string is hashed as-is |
| No hidden defaults | Context dict is separate, never merged into input |
| Raw input logged before processing | SHA-256 hash computed and logged |

---

## Verification

```python
from core.authority.parallel_validator import verify_input_integrity

# Same input to both systems
result = verify_input_integrity("user login from Mumbai", "user login from Mumbai")
# result: {"input_match": True, "core_input_hash": "abc...", "sarathi_input_hash": "abc..."}

# Different input (mutation detected)
result = verify_input_integrity("user login", "user login enriched")
# result: {"input_match": False, "mismatch_detail": {...}}
```

---

## How It Works

```
Request arrives at Core
  |
  +-- log_raw_input(input_data)  ← logs BEFORE any processing
  |     records: input string + SHA-256 hash + timestamp
  |
  +-- create_trace_origin(source)
  |
  +-- callSovereign(ctx, input_data)  ← input_data passed as-is
  |
  +-- callSarathi(ctx)
  |
  +-- produce_canonical_output()
```

Input string is NEVER modified between receipt and evaluation.

---

## Validation (Tested)

```
[Test 4] Same input to both: match=True  [OK]
[Test 5] Different input: match=False     [OK] Mismatch detected
```

---

## File

[`core/authority/parallel_validator.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/parallel_validator.py)
