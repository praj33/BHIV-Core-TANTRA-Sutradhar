# CORE AUTHORITY INTERFACE — Phase 1

## Purpose

All decision and enforcement calls in BHIV Core now go through unified wrappers. No direct access to SovereignCore or SarathiEnforcer is permitted from orchestration code.

---

## Wrappers

### `callSovereign(trace_ctx, input_data, context)`

Routes decision requests to Sovereign Core.

```python
from core.authority import callSovereign

ctx = callSovereign(trace_ctx, "user input here", {"agent": "edumentor"})
# ctx now has decision signal (ALLOW/DENY)
```

**Behavior:**
- `USE_EXTERNAL_AUTHORITY=false` → calls `SovereignCore.evaluate()` internally
- `USE_EXTERNAL_AUTHORITY=true` → calls `POST /sovereign/decide` externally
- Service down → **FAIL CLOSED** (raises `ConnectionError`, no fallback)

---

### `callSarathi(trace_ctx, execution_payload)`

Routes enforcement requests to Sarathi.

```python
from core.authority import callSarathi

ctx = callSarathi(trace_ctx, {"task": "process"})
# ctx now has enforcement signal (CLEARED/BLOCKED)
```

**Behavior:**
- `USE_EXTERNAL_AUTHORITY=false` → calls `SarathiEnforcer.enforce()` internally
- `USE_EXTERNAL_AUTHORITY=true` → calls `POST /sarathi/enforce` externally
- Service down → **FAIL CLOSED** (raises `ConnectionError`, no fallback)
- No decision signal → raises `SarathiEnforcementError`

---

## Config

| Env Variable | Values | Effect |
|---|---|---|
| `USE_EXTERNAL_AUTHORITY` | `true` / `false` | Routes to external APIs or internal modules |
| `SOVEREIGN_SERVICE_URL` | URL (default: `http://localhost:9001`) | External Sovereign endpoint |
| `SARATHI_SERVICE_URL` | URL (default: `http://localhost:9002`) | External Sarathi endpoint |

---

## Rules Enforced

| Rule | Status |
|------|--------|
| ALL execution flows go through wrappers | ENFORCED |
| No direct SovereignCore/Sarathi access from orchestration | ENFORCED |
| No fallback execution on service failure | ENFORCED (FAIL CLOSED) |
| trace_id preserved across calls | ENFORCED |
| Identical behavior internal vs external | ENFORCED |

---

## File

[`core/authority/__init__.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/__init__.py)
