# CORE INTAKE BEHAVIOR

## Purpose

This document defines **what Core does** and **what Core does NOT do** when it receives an inbound flow from Sutradhar.

---

## What Core Does

### 1. Accept Flow

Core receives a structured flow payload from Sutradhar (see `SUTRADHAR_TO_CORE_CONTRACT.md`).

```
Sutradhar --[flow payload]--> Core Intake
```

### 2. Structural Validation

Core validates only that the payload is well-formed:
- All required fields present (`flow_id`, `source`, `intent`, `context_payload`, `trace_id`, `timestamp`)
- Types are correct (strings are strings, objects are objects)
- `trace_id` is a valid UUID

**Core does NOT validate business logic, intent correctness, or routing.**

### 3. Context Assembly

Core assembles a processing context from the flow:

```
Assembled Context = {
    flow_id          <-- from Sutradhar (passed through)
    trace_id         <-- from Sutradhar (passed through)
    intent           <-- from Sutradhar (passed through)
    source           <-- from Sutradhar (passed through)
    context_payload  <-- from Sutradhar (passed through)
    core_received_at <-- Core's UTC timestamp (when Core received it)
}
```

### 4. Build ActionProposal

Core transforms the assembled context into an ActionProposal and sends it to Sovereign Core (see `CORE_TO_SOVEREIGN_CONTRACT.md`).

```
Core --[ActionProposal]--> Sovereign Core
```

### 5. Receive Decision

Core receives a decision response from Sovereign Core (see `SOVEREIGN_TO_CORE_RESPONSE.md`) and acts accordingly:
- **ALLOW**: Forward execution context downstream (to Sarathi)
- **DENY**: Record denial in trace, stop processing

---

## What Core Does NOT Do

| Core does NOT... | Who does it? |
|----------------|-------------|
| Make decisions (ALLOW/DENY) | Sovereign Core |
| Execute actions | Execution Layer / Products |
| Route flows | Sutradhar |
| Enforce decisions | Sarathi |
| Validate intent correctness | Sutradhar |
| Validate authority/policy | Sovereign Core |
| Mutate `flow_id` | Nobody (immutable) |
| Mutate `trace_id` | Nobody (immutable) |
| Mutate flow origin data | Nobody (immutable) |
| Retry failed decisions | Nobody (decision is final) |
| Override decisions | Nobody (decision is sovereign) |

---

## Core's Identity

Core is a **pure coordination layer**:

```
INPUT:  Structured flow from Sutradhar
OUTPUT: ActionProposal to Sovereign Core
ROLE:   Receive, assemble, propose — nothing more
```

Core absorbs **neither** the router role (Sutradhar) **nor** the authority role (Sovereign Core).
