# CORE POSITION IN FLOW

## Purpose

This document maps BHIV Core's **exact position** in the system flow and explicitly defines what Core does and does not connect to.

---

## End-to-End Flow

```
  SUTRADHAR (Router)
      |
      |  flow_id, source, intent, context_payload, trace_id, timestamp
      |
      v
  BHIV CORE (Coordinator)
      |
      |  ActionProposal: proposal_id, intent, target, payload, risk_level
      |
      v
  SOVEREIGN CORE (Authority)
      |
      |  Decision: ALLOW / DENY, reason, policy_reference
      |
      v
  SARATHI (Enforcer)
      |
      |  Enforcement: CLEARED / BLOCKED
      |
      v
  GATED BRIDGE (Gateway)
      |
      |  Validated execution context
      |
      v
  EXECUTION (Products / Agents)
```

---

## Core's Connections

| Direction | Connects To | What Flows |
|-----------|-------------|-----------|
| **INBOUND** | Sutradhar | Structured flow payload |
| **OUTBOUND** | Sovereign Core | ActionProposal |
| **INBOUND** | Sovereign Core | Decision response |

---

## Core Does NOT Connect To

| System | Why Not |
|--------|---------|
| **Sarathi** | Core does NOT call Sarathi. Sovereign Core's decision flows to Sarathi independently. |
| **Gated Bridge** | Core has no direct path to the gateway. |
| **Execution** | Core does NOT talk to execution. Ever. No direct path. |
| **Products/Agents** | Agents are invoked by the execution layer, not Core. |

---

## Explicit Flow Rules

| Rule | Status |
|------|--------|
| Sutradhar -> Core | PERMITTED (only inbound source) |
| Core -> Sovereign Core | PERMITTED (ActionProposal only) |
| Sovereign Core -> Core | PERMITTED (Decision response only) |
| Core -> Sarathi | **PROHIBITED** |
| Core -> Execution | **PROHIBITED** |
| Core -> Gated Bridge | **PROHIBITED** |
| Core -> Products | **PROHIBITED** |
| Core skips Sovereign | **PROHIBITED** |

---

## Flow Identity Preservation

Throughout the entire flow, these identifiers are **never mutated**:

| Identifier | Created By | Modified By |
|------------|-----------|-------------|
| `trace_id` | Core (trace_origin) | Nobody |
| `flow_id` | Sutradhar | Nobody |
| `proposal_id` | Core | Nobody |
| `correlation_id` | Sovereign Core (= proposal_id) | Nobody |

Every system adds signals/decisions but **never changes** the originating identifiers.
