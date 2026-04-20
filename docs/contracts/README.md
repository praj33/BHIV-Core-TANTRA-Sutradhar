# Interface Contracts — Documentation

Boundary contracts defining how BHIV Core sits between Sutradhar (flow) and Sovereign Core (authority).

| Document | Description |
|----------|-------------|
| [SUTRADHAR_TO_CORE_CONTRACT.md](SUTRADHAR_TO_CORE_CONTRACT.md) | Inbound flow schema — what Core receives from Sutradhar |
| [CORE_INTAKE_BEHAVIOR.md](CORE_INTAKE_BEHAVIOR.md) | Core intake rules — what Core does and does NOT do |
| [CORE_TO_SOVEREIGN_CONTRACT.md](CORE_TO_SOVEREIGN_CONTRACT.md) | ActionProposal output — what Core sends to Sovereign |
| [SOVEREIGN_TO_CORE_RESPONSE.md](SOVEREIGN_TO_CORE_RESPONSE.md) | Decision handling — ALLOW/DENY response contract |
| [CORE_POSITION_IN_FLOW.md](CORE_POSITION_IN_FLOW.md) | End-to-end flow map — Core's exact position and prohibited paths |
| [CORE_BOUNDARY_ASSERTIONS.md](CORE_BOUNDARY_ASSERTIONS.md) | Safety check — Core is NOT routing/authority/enforcement/execution |

## Flow Summary

```
Sutradhar --> BHIV Core --> Sovereign Core --> Sarathi --> Gated Bridge --> Execution
```

Core is a **pure coordination layer** — receives, assembles, proposes. Nothing more.
