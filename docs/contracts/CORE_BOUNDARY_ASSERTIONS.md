# CORE BOUNDARY ASSERTIONS

## Purpose

This is the **safety document** that explicitly declares what BHIV Core IS and IS NOT.

---

## Boundary Assertions

### Assertion 1: Core is NOT the routing system

```
ROUTING SYSTEM = SUTRADHAR

Sutradhar decides WHERE flows go.
Core does NOT route.
Core does NOT decide which system handles a request.
Core does NOT redirect flows.
Core ONLY receives what Sutradhar sends.
```

---

### Assertion 2: Core is NOT the authority system

```
AUTHORITY SYSTEM = SOVEREIGN CORE

Sovereign Core decides ALLOW / DENY.
Core does NOT make decisions.
Core does NOT approve actions.
Core does NOT deny actions.
Core ONLY proposes — Sovereign decides.
```

---

### Assertion 3: Core is NOT the enforcement system

```
ENFORCEMENT SYSTEM = SARATHI

Sarathi enforces decisions.
Core does NOT enforce.
Core does NOT gate execution.
Core does NOT block actions.
Core does NOT call Sarathi directly.
```

---

### Assertion 4: Core is NOT the execution system

```
EXECUTION SYSTEM = PRODUCTS / AGENTS

Products and agents execute actions.
Core does NOT execute.
Core does NOT run agents.
Core does NOT process tasks.
Core does NOT produce outputs.
```

---

## What Core IS

```
BHIV CORE = COORDINATION LAYER

Core RECEIVES structured flow     (from Sutradhar)
Core ASSEMBLES context            (from flow payload)
Core PROPOSES actions              (to Sovereign Core)
Core RECORDS decisions in trace   (from Sovereign Core)
Core PASSES context downstream    (on ALLOW)
Core HALTS processing             (on DENY)

That is ALL Core does. Nothing more.
```

---

## Summary Table

| Role | Owner | Core's Relationship |
|------|-------|-------------------|
| Routing | **Sutradhar** | Core receives from it |
| Decision | **Sovereign Core** | Core proposes to it |
| Enforcement | **Sarathi** | Core does NOT connect |
| Execution | **Products** | Core does NOT connect |
| Coordination | **BHIV Core** | THIS is Core's role |

---

## Violation Detection

If any of the following are observed, it is a **boundary violation**:

| Violation | What It Means |
|-----------|---------------|
| Core generates `flow_id` | Core is absorbing Sutradhar's role |
| Core makes ALLOW/DENY decisions | Core is absorbing Sovereign Core's role |
| Core calls Sarathi directly | Core is bypassing the flow hierarchy |
| Core invokes agents directly | Core is absorbing the execution role |
| Core retries a Sovereign decision | Core is overriding authority |
| Core modifies `trace_id` | Trace integrity is broken |

**Any of these violations invalidates the system architecture.**
