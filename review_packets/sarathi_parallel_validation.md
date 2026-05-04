# REVIEW PACKET — Sarathi Parallel Validation

**Date:** 2026-05-04
**Owner:** Raj Prajapati
**Module:** Core ↔ Sarathi Parallel Validation Enablement

---

## 1. ENTRY POINT

```python
from core.authority.parallel_validator import run_core_enforcement, compare_outputs

# Run Core enforcement on any input
result = run_core_enforcement("user login from Mumbai IP")

# Compare with Sarathi output
comparison = compare_outputs(result["core_output"], sarathi_output)
```

No API changes needed. This hooks into existing enforcement.

---

## 2. CORE EXECUTION FLOW (3 files)

### `core/authority/canonical_output.py`
- `produce_canonical_output()` — builds exact 6-field OrderedDict
- `produce_from_trace_context()` — extracts from TraceContext after Sovereign+Sarathi
- `validate_canonical_output()` — ensures no extra/missing fields
- `canonical_to_json()` — deterministic serialization

### `core/authority/parallel_validator.py`
- `log_raw_input()` — Phase 2: logs input BEFORE processing (no mutation)
- `run_core_enforcement()` — Phase 3: runs full enforcement, prints to console
- `compare_outputs()` — Phase 4: field-by-field comparison
- `_log_mismatch()` — Phase 5: MISMATCH DETECTED alert

### `tests/test_vc_dry_run.py`
- Phase 6: 15 test executions + mismatch detection + determinism check

---

## 3. LIVE FLOW (REAL JSON)

### Request:
```json
{
    "input": "deploy web1-blue service"
}
```

### Core Output (Canonical):
```json
{
    "trace_id": "19220895-9aa8-4fec-82ed-4721c338d1c7",
    "decision_id": "94036ea1bceb236f",
    "decision_hash": "b2c4780f2ca329e09615f016089d5371...",
    "verdict": "ALLOW",
    "enforcement_binding": "CLEARED:Decision ALLOW validated — execution permitted",
    "timestamp": "2026-05-04T11:52:17.268351+00:00"
}
```

### Comparison (Core vs Sarathi):
```json
{
    "match": true,
    "fields_compared": 6,
    "mismatches": []
}
```

### Mismatch Example:
```json
{
    "match": false,
    "fields_compared": 6,
    "mismatches": [
        {
            "field": "verdict",
            "core": "ALLOW",
            "sarathi": "DENY"
        },
        {
            "field": "decision_hash",
            "core": "b0ca041a1180dcbd...",
            "sarathi": "TAMPERED_HASH_VALUE"
        }
    ]
}
```

---

## 4. WHAT WAS BUILT

| Deliverable | File | Purpose |
|-------------|------|---------|
| Canonical Output | `core/authority/canonical_output.py` | 6-field deterministic output |
| Parallel Validator | `core/authority/parallel_validator.py` | Input integrity + comparison + mismatch |
| VC Dry Run | `tests/test_vc_dry_run.py` | 15 executions + validation tests |
| Output Schema doc | `docs/contracts/CORE_OUTPUT_SCHEMA.md` | Phase 1 |
| Input Integrity doc | `docs/contracts/CORE_INPUT_INTEGRITY.md` | Phase 2 |
| Parallel Logging doc | `docs/contracts/PARALLEL_EXECUTION_LOGGING.md` | Phase 3 |
| Comparison Map doc | `docs/contracts/CORE_SARATHI_COMPARISON_MAP.md` | Phase 4 |
| Mismatch Handling doc | `docs/contracts/MISMATCH_HANDLING.md` | Phase 5 |
| VC Dry Run Logs doc | `docs/contracts/VC_DRY_RUN_LOGS.md` | Phase 6 |

---

## 5. FAILURE CASES

| Case | Behavior |
|------|----------|
| Mismatch detected | Console: `!! MISMATCH DETECTED !!` with field-level diff |
| Missing field in output | `validate_canonical_output()` returns False |
| Invalid verdict | `ValueError: Must be ALLOW or DENY` |
| Input mutation between Core and Sarathi | `verify_input_integrity()` detects hash mismatch |
| Schema violation | Logged + flagged |

---

## 6. PROOF

### VC Dry Run Results
```
Total executions:    15
Successful:          15
Crashes:             0
Schema violations:   0
Missing fields:      0
Mismatch detection:  working (2 field mismatches caught)
Input integrity:     working
Determinism:         PASS
VC readiness:        READY
```

### Reproduce
```bash
python tests/test_vc_dry_run.py
```
