# CORE AUTHORITY SWITCH — Phase 4

## Configuration Toggle

The `USE_EXTERNAL_AUTHORITY` environment variable controls whether BHIV Core uses internal modules or external services for decision and enforcement.

---

## Switch

| Variable | Value | Routing |
|---|---|---|
| `USE_EXTERNAL_AUTHORITY` | `false` (default) | Internal `SovereignCore` + `SarathiEnforcer` |
| `USE_EXTERNAL_AUTHORITY` | `true` | External `POST /sovereign/decide` + `POST /sarathi/enforce` |

### Set via environment

```bash
# Internal (default)
set USE_EXTERNAL_AUTHORITY=false

# External
set USE_EXTERNAL_AUTHORITY=true
set SOVEREIGN_SERVICE_URL=http://localhost:9001
set SARATHI_SERVICE_URL=http://localhost:9002
```

---

## Routing Logic

```
callSovereign(trace_ctx, input_data, context)
    |
    +-- USE_EXTERNAL_AUTHORITY=false --> SovereignCore.evaluate()  [internal]
    |
    +-- USE_EXTERNAL_AUTHORITY=true  --> POST /sovereign/decide    [external]

callSarathi(trace_ctx, execution_payload)
    |
    +-- USE_EXTERNAL_AUTHORITY=false --> SarathiEnforcer.enforce() [internal]
    |
    +-- USE_EXTERNAL_AUTHORITY=true  --> POST /sarathi/enforce     [external]
```

---

## Rules

| Rule | Enforcement |
|------|-------------|
| Identical behavior on both paths | Same decision logic, same enforcement logic |
| No fallback execution | If external is selected but down, system FAILS CLOSED |
| No bypass possible | Both paths go through same wrappers |
| No mixed mode | Cannot use external Sovereign with internal Sarathi |
| trace_id preserved | Same trace context flows through both paths |

---

## Fail-Closed Guarantee

```
External service down?
    --> ConnectionError raised
    --> No decision recorded
    --> No enforcement possible
    --> No execution token issued
    --> Execution BLOCKED

There is NO fallback to internal when external is selected.
```

---

## File

[`core/authority/__init__.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/authority/__init__.py)
