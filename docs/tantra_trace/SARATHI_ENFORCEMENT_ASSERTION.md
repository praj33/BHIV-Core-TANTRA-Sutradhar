# SARATHI ENFORCEMENT ASSERTION — Phase 5

## Non-Bypassable Enforcement

File: [`core/trace/sarathi_enforcer.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/trace/sarathi_enforcer.py)

### Enforcement Path (MANDATORY)

```
Core --> Sarathi --> Execution
```

### Prohibited Paths

| Path | Status |
|------|--------|
| Core --> Execution (direct) | BLOCKED — raises `SarathiEnforcementError` |
| Core --> Pravah (skip Sarathi) | BLOCKED — no execution occurs |
| Any path skipping Sarathi | BLOCKED — `assert_cleared()` detects violation |

### Enforcement Mechanism

1. **`SarathiEnforcer.enforce(ctx)`** — validates decision signal exists and is ALLOW
2. **`SarathiEnforcer.assert_cleared(ctx)`** — static check at any point to verify Sarathi was not bypassed
3. **`SarathiEnforcementError`** — raised on any violation, halting execution

### Enforcement Scenarios

| Scenario | Result | Error |
|----------|--------|-------|
| Decision = ALLOW | CLEARED | None |
| Decision = DENY | BLOCKED | `SarathiEnforcementError` |
| No decision signal | BLOCKED | `SarathiEnforcementError` |
| Unknown decision value | BLOCKED | `SarathiEnforcementError` |

### Test Proof

- `test_sarathi_blocks_without_decision` — no decision = BLOCKED
- `test_sarathi_clears_on_allow` — ALLOW = CLEARED
- `test_sarathi_blocks_on_deny` — DENY = BLOCKED
- `test_sarathi_assert_cleared` — static assertion works
- `test_sarathi_assert_fails_without_enforcement` — bypass detected

**Sarathi lock is proven: non-bypassable, enforced at code level.**
