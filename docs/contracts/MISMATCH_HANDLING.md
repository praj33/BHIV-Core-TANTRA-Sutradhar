# MISMATCH HANDLING — Phase 5

## Rule: Mismatch must be obvious immediately. Never suppressed.

---

## Behavior

When a mismatch is detected between Core and Sarathi output:

### 1. Console Alert (IMMEDIATE)

```
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  !! MISMATCH DETECTED !!
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    Field: decision_hash
      Core:    b0ca041a1180dcbdfae554c2f104f7d556b23806...
      Sarathi: TAMPERED_HASH_VALUE
    Field: verdict
      Core:    ALLOW
      Sarathi: DENY
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

### 2. Log Entry

```json
{
    "type": "MISMATCH_DETECTED",
    "timestamp": "2026-05-04T...",
    "core_output": {...},
    "sarathi_output": {...},
    "mismatches": [
        {"field": "verdict", "core": "ALLOW", "sarathi": "DENY"}
    ],
    "mismatch_count": 1
}
```

### 3. Field-Level Detail

Every mismatch shows:
- **Field name**: which field differs
- **Core value**: what Core produced
- **Sarathi value**: what Sarathi produced

---

## What Does NOT Happen

| Action | Happens? |
|--------|----------|
| Suppress mismatch | **NO** |
| Retry silently | **NO** |
| Override output | **NO** |
| Log without alerting | **NO** |
| Ignore field differences | **NO** |

---

## Mismatch Detection (Tested)

```
[Test 1] Same output vs itself: match=True   [OK]
[Test 2] Tampered output: match=False         [OK] 2 mismatches detected
             decision_hash: core=b0ca041a... vs sarathi=TAMPERED_HASH_VALUE
             verdict: core=ALLOW vs sarathi=DENY
[Test 3] Missing field: match=False           [OK] Mismatch on: ['enforcement_binding']
```

---

## Usage

```python
from core.authority.parallel_validator import compare_outputs

result = compare_outputs(core_output, sarathi_output)
if not result["match"]:
    # Mismatch is already printed to console and logged
    # result["mismatches"] contains field-level details
```

---

## File

[`core/authority/parallel_validator.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/parallel_validator.py)
