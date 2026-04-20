# DECISION & ENFORCEMENT TRACE — Phase 4

## Sovereign Core Decision Signal

File: [`core/trace/sovereign_core.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/trace/sovereign_core.py)

### Decision Signal Format

```json
{
    "signal_type": "decision",
    "layer": "sovereign_core",
    "timestamp": "2026-04-20T09:02:51.123456+00:00",
    "payload": {
        "decision": "ALLOW",
        "policy_reference": "bhiv.core.default_allow_policy",
        "input_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
}
```

### Decision Values

| Decision | Meaning |
|----------|---------|
| `ALLOW` | Input evaluated, policy permits execution |
| `DENY` | Input evaluated, policy blocks execution |

### input_hash

SHA-256 hash of the raw input data. Proves the decision was made against specific input — tamper-evident.

---

## Sarathi Enforcement Signal

File: [`core/trace/sarathi_enforcer.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/trace/sarathi_enforcer.py)

### Enforcement Signal Format

```json
{
    "signal_type": "enforcement",
    "layer": "sarathi",
    "timestamp": "2026-04-20T09:02:51.234567+00:00",
    "payload": {
        "enforcement_status": "CLEARED",
        "validation_result": "Decision ALLOW validated -- execution permitted",
        "failure_reason": null
    }
}
```

### Enforcement Statuses

| Status | Meaning |
|--------|---------|
| `CLEARED` | Decision was ALLOW — execution proceeds |
| `BLOCKED` | Decision was DENY, missing, or invalid — execution halted |

### Failure Reasons (when BLOCKED)

- "Missing Sovereign Core decision — Sarathi cannot clear execution"
- "Sovereign Core denied execution. Policy: {policy_reference}"
- "Invalid decision signal from Sovereign Core"

### Test Coverage

- `test_sovereign_core_allow` — ALLOW + input_hash verified
- `test_sovereign_core_deny` — DENY on policy match
- `test_sarathi_clears_on_allow` — CLEARED status
- `test_sarathi_blocks_on_deny` — BLOCKED with SarathiEnforcementError

**Decision + enforcement is proven: signals exist, payload complete, trace unbroken.**
