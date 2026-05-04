# CORE OUTPUT SCHEMA — Phase 1

## Canonical Output Format

Every Core enforcement output MUST contain EXACTLY these 6 fields:

```json
{
    "trace_id": "string (UUID v4, Core-generated)",
    "decision_id": "string (SHA-256 derived from trace_id + input_hash, 16 chars)",
    "decision_hash": "string (SHA-256 of input, deterministic)",
    "verdict": "ALLOW | DENY (nothing else)",
    "enforcement_binding": "string (CLEARED:... or BLOCKED:... from Sarathi)",
    "timestamp": "string (ISO 8601 UTC)"
}
```

---

## Rules

| Rule | Enforcement |
|------|-------------|
| No extra fields | `validate_canonical_output()` rejects extras |
| No missing fields | `validate_canonical_output()` rejects missing |
| Deterministic field order | `OrderedDict` with fixed key order |
| No formatting drift | `canonical_to_json()` uses separators=(",",":") |
| Same input → same output | `decision_hash` is deterministic SHA-256 of input |

---

## Example (Real Output)

```json
{
    "trace_id": "9166d389-53c0-40e2-ab6c-bc064ce46f96",
    "decision_id": "d25764e62a469fd5",
    "decision_hash": "d25764e62a469fd5bf3a56e5e806a49700d058e7329b6b4752793645d665e060",
    "verdict": "ALLOW",
    "enforcement_binding": "CLEARED:Decision ALLOW validated — execution permitted",
    "timestamp": "2026-05-04T11:40:31.491603+00:00"
}
```

---

## Determinism Proof

Same input run twice produces:
- Same `verdict`: YES
- Same `decision_hash`: YES
- Different `trace_id`: YES (expected — each trace is unique)
- Different `decision_id`: YES (derived from trace_id)

---

## File

[`core/authority/canonical_output.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/canonical_output.py)
