# CORE TO PRAVAH SIGNAL — Phase 6

## Pravah Contract (Passive Only)

File: [`core/trace/pravah_emitter.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/trace/pravah_emitter.py)

### Signal Schema (STRICT — NO EXTRA FIELDS)

```json
{
    "trace_id":    "string — the trace identifier from Core",
    "trace_hash":  "string — SHA-256 cryptographic binding",
    "source":      "string — origin source identifier",
    "signal_type": "string — e.g. 'trace_complete' or 'trace_failure'",
    "severity":    "string — 'info', 'warning', 'error', 'critical'",
    "timestamp":   "string — ISO 8601 UTC"
}
```

**Exactly 6 fields. No additions. No omissions.**

### Pravah Role

| Pravah IS | Pravah IS NOT |
|-----------|---------------|
| Observer only | Authority |
| Non-blocking | Blocking |
| Non-authoritative | Decision maker |
| Passive receiver | Active participant |

### Pravah Rules

| Rule | Enforcement |
|------|-------------|
| Pravah does NOT modify payload | Schema is built by Core, Pravah receives as-is |
| Pravah does NOT acknowledge truth | No acknowledgment in protocol |
| Pravah does NOT confirm execution | No confirmation callback |
| No extra fields beyond schema | `test_pravah_strict_schema` validates exactly 6 fields |

### Test Proof

- `test_pravah_strict_schema` — exactly 6 fields, no more

**Pravah contract is proven: passive, strict schema, non-authoritative.**
