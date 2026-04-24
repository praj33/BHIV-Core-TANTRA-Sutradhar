# REVIEW PACKET — Authority Extraction

**Owner:** Raj Prajapati
**Module:** Core Authority Extraction (SovereignCore + Sarathi externalization)
**Date:** 2026-04-24

---

## Summary

BHIV Core's internal SovereignCore (decision) and Sarathi (enforcement) have been extracted into external, independently deployable services. Core now operates as a pure orchestration layer with all authority externalized.

---

## Architecture

```
                     USE_EXTERNAL_AUTHORITY
                            |
              false         |         true
              -----         |         ----
                            |
callSovereign() ----+-- internal ---> SovereignCore.evaluate()
                    |
                    +-- external ---> POST /sovereign/decide (port 9001)

callSarathi()   ----+-- internal ---> SarathiEnforcer.enforce()
                    |
                    +-- external ---> POST /sarathi/enforce  (port 9002)
```

---

## Phase Deliverables

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | `CORE_AUTHORITY_INTERFACE.md` | COMPLETE |
| 2 | `SOVEREIGN_SERVICE_SETUP.md` | COMPLETE |
| 3 | `SARATHI_SERVICE_SETUP.md` | COMPLETE |
| 4 | `CORE_AUTHORITY_SWITCH.md` | COMPLETE |
| 5 | `TRACE_CROSS_SERVICE_PROOF.md` | COMPLETE |
| 6 | `AUTHORITY_EXTRACTION_VALIDATION.md` | COMPLETE |

---

## Implementation Files

| File | Purpose |
|------|---------|
| `core/authority/__init__.py` | callSovereign + callSarathi wrappers |
| `services/sovereign_service.py` | External Sovereign (port 9001) |
| `services/sarathi_service.py` | External Sarathi (port 9002) |
| `tests/test_authority_extraction.py` | 12 validation tests |

---

## Test Results

**12/12 tests passing**

| Phase | Tests | Result |
|-------|-------|--------|
| Phase 5 — Trace Continuity | 6 | ALL PASS |
| Phase 6 — Security | 6 | ALL PASS |

---

## Integration Boundaries

| Team Member | Layer | Interface |
|-------------|-------|-----------|
| Ashmit Pandey | Bucket | Post-execution truth write (receives execution_token) |
| Vijay Dhawan | InsightBridge | Post-Sarathi enforcement gateway |
| Aakanksha | Sovereign Systems | Authority validation via /sovereign/decide |
| Rajaryan | Enforcement Layer | Sarathi service validation via /sarathi/enforce |
| Kanishk | Execution Systems | Execution token validation |
| Pritesh Patra | Sovereign Interfaces | Contract consistency |

---

## Constraints Enforced

| Constraint | Status |
|-----------|--------|
| No agent logic changed | ENFORCED |
| No execution flow modified | ENFORCED |
| trace_id continuity preserved | ENFORCED (12 tests) |
| No fallback execution paths | ENFORCED (fail closed) |
| No schema redesign | ENFORCED |
| Replay attack detection | ENFORCED (decision_hash tracking) |
| No new external dependencies | ENFORCED (stdlib only) |

---

**Outcome: BHIV Core operates as a pure orchestration layer with all authority externalized, trace-safe, and deterministic.**
