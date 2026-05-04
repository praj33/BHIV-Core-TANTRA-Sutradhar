# VC DRY RUN LOGS — Phase 6

## 15 Test Executions Under Simulated VC Conditions

---

## Results Summary

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

---

## All 15 Executions

| # | Input | trace_id | verdict | decision_hash (first 16) | Status |
|---|-------|----------|---------|-------------------------|--------|
| 1 | user login from Mumbai IP | 1950b435-... | ALLOW | b0ca041a11... | OK |
| 2 | deploy web1-blue service | 19220895-... | ALLOW | b2c4780f2c... | OK |
| 3 | restart database cluster | 5244e7e7-... | ALLOW | 2a9feada72... | OK |
| 4 | scale frontend pods to 5 | 3d6a4bfb-... | ALLOW | ae4855a083... | OK |
| 5 | enable maintenance mode | c05dce6e-... | ALLOW | 3f7cc958df... | OK |
| 6 | query user karma score | cb6a7517-... | ALLOW | 4af91c09ed... | OK |
| 7 | process payment transaction | c17bbc59-... | ALLOW | db9149e621... | OK |
| 8 | update firewall rules | 7e552ffb-... | ALLOW | 595f1a4f7e... | OK |
| 9 | rotate API keys | 00c4c844-... | ALLOW | e95d36e8db... | OK |
| 10 | generate analytics report | 26845c89-... | ALLOW | a139febbc2... | OK |
| 11 | check service health | 69bbd867-... | ALLOW | 56235894bc... | OK |
| 12 | backup MongoDB collections | a790fb11-... | ALLOW | ce4b485947... | OK |
| 13 | trigger CI/CD pipeline | bbe7084d-... | ALLOW | 556d2067e8... | OK |
| 14 | apply security patch | fbe7b1f0-... | ALLOW | 8237e61d73... | OK |
| 15 | sync replica nodes | 8399b455-... | ALLOW | 052af1bc2d... | OK |

---

## Validation Tests

| Test | What | Result |
|------|------|--------|
| Test 1 | Same output vs itself | match=True ✅ |
| Test 2 | Tampered output (verdict+hash changed) | match=False, 2 mismatches ✅ |
| Test 3 | Missing field (enforcement_binding) | match=False, 1 mismatch ✅ |
| Test 4 | Same input to Core and Sarathi | match=True ✅ |
| Test 5 | Different input to Core and Sarathi | match=False ✅ |
| Test 6 | Determinism (same input, two runs) | verdict match + hash match ✅ |

---

## VC Readiness Checklist

| Item | Status |
|------|--------|
| Outputs visible on console | YES |
| Logs readable during VC | YES |
| No ambiguity in output | YES |
| No crashes | YES (0/15) |
| No missing logs | YES (0 missing fields) |
| No inconsistent outputs | YES (determinism PASS) |

---

## Reproduce

```bash
python tests/test_vc_dry_run.py
```

Full JSON results: `logs/vc_dry_run_results.json`
Full log stream: `logs/parallel_execution.jsonl`
