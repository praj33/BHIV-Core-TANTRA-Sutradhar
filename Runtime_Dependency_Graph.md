# Runtime Dependency Graph — Phase IV Final

Version: 3.0.0
Date: 2026-06-20
Status: ✅ All dependencies verified with live HTTP

---

## Overview

This document maps every Producer → Consumer relationship in the TANTRA runtime chain. All dependencies are verified with live HTTP evidence from the 8/8 SUCCESS chain.

---

## Dependency Graph

```mermaid
graph TD
    User["User Request"] --> Core["BHIV Core"]
    Core --> Sov["Sovereign"]
    Core --> CET["CET Compiler"]
    Core --> Sar["Sarathi Gate"]
    Core --> Brg["Bridge"]
    Core --> Bkt["Bucket"]
    Core --> Ins["InsightFlow"]

    Sov -->|"decision + risk"| Core
    CET -->|"contract_hash + sum_script"| Core
    Sar -->|"status=ALLOW + JWT"| Core
    Brg -->|"status=completed"| Core
    Bkt -->|"hash + storage_type"| Core
    Ins -->|"dataset_id + status"| Core

    Sar -->|"JWKS public key"| Brg
    Core -->|"JWT Bearer token"| Brg

    style Core fill:#4CAF50,color:#fff
    style Sov fill:#2196F3,color:#fff
    style CET fill:#FF9800,color:#fff
    style Sar fill:#9C27B0,color:#fff
    style Brg fill:#F44336,color:#fff
    style Bkt fill:#009688,color:#fff
    style Ins fill:#795548,color:#fff
```

---

## Producer → Consumer Mappings

### Core Produces → Others Consume

| Producer | Artifact | Consumer | Protocol |
|---|---|---|---|
| Core | text input | Sovereign | POST /analyze |
| Core | KSML decision object | CET | POST /cet/compile |
| Core | SarathiTokenInput + trace_id + cet_hash | Sarathi | POST /sarathi/enforce |
| Core | JWT + bridge_signature + X-Sarathi-* | Bridge | POST /execute |
| Core | Execution artifact + parent_hash | Bucket | POST /bucket/artifact |
| Core | Dataset metadata | InsightFlow | POST /api/v1/datasets/ |
| Core | trace_id | All participants | X-Trace-Id header |

### Others Produce → Core Consumes

| Producer | Artifact | Consumer | Evidence |
|---|---|---|---|
| Sovereign | decision (ALLOW/DENY), risk_category | Core | HTTP 200 |
| CET | contract_hash, sum_script | Core | HTTP 200 |
| Sarathi | status (ALLOW), JWT token | Core | HTTP 200 |
| Bridge | status (completed), result | Core | HTTP 200 |
| Bucket | artifact hash, storage_type | Core | HTTP 200 |
| InsightFlow | dataset_id, status (ACTIVE) | Core | HTTP 201 |

### Cross-Service Dependencies

| Producer | Artifact | Consumer | Notes |
|---|---|---|---|
| Sarathi | JWKS (/.well-known/jwks.json) | Bridge | RSA public key for JWT verification |
| Sarathi | JWT (RS256 signed) | Bridge (via Core) | Core forwards as Bearer token |
| CET | contract_hash | Sarathi (via Core) | Embedded in Sarathi token as cet_hash |
| CET | contract_hash | Bridge (via Core) | Validated as cet_hash continuity |
| Bucket | chain_state (last_hash) | Core | Pre-fetched as parent_hash for chain integrity |

---

## Data Flow Summary

```
User Request
    │
    ▼
┌──────────────┐
│  BHIV Core   │ ── trace_id generated
└──────┬───────┘
       │
       ├──► Sovereign ──► decision_hash
       │
       ├──► CET ──► contract_hash
       │
       ├──► Sarathi ──► JWT (RS256)
       │        │
       │        └──► JWKS ──► Bridge (key verification)
       │
       ├──► Bridge ──► status=completed
       │    (Bearer JWT + X-Sarathi-* + bridge_signature)
       │
       ├──► [Agent Execution]
       │
       ├──► Bucket ──► artifact_hash (chain-linked)
       │
       └──► InsightFlow ──► dataset_id (ACTIVE)
```

---

## Failure Propagation

| Failing Service | Impact on Chain | Recovery |
|---|---|---|
| Sovereign unreachable | Chain BLOCKED at Step 2 | FAIL-CLOSED |
| CET unreachable | Chain BLOCKED at Step 3 | Internal fallback hash |
| Sarathi unreachable | Chain BLOCKED at Step 4 | FAIL-CLOSED (SarathiEnforcementError) |
| Sarathi rejects | Chain BLOCKED at Step 4 | FAIL-CLOSED |
| Bridge rejects JWT | Chain BLOCKED at Step 5 | FAIL-CLOSED |
| Bridge unreachable | Chain BLOCKED at Step 5 | FAIL-CLOSED |
| Bucket unreachable | Chain BLOCKED at Step 7 | FAIL-CLOSED (BucketWriteError) |
| InsightFlow unreachable | Chain CONTINUES | GRACEFUL-FALLBACK (local JSONL) |

---

## Dependency Classification

| Participant | Type | Blocking? | Fallback? |
|---|---|---|---|
| Sovereign | CRITICAL | YES | No — FAIL-CLOSED |
| CET | CRITICAL | YES | YES — internal fallback hash |
| Sarathi | CRITICAL | YES | No — FAIL-CLOSED |
| Bridge | CRITICAL | YES | No — FAIL-CLOSED |
| Bucket | CRITICAL | YES | No — FAIL-CLOSED |
| InsightFlow | OPTIONAL | NO | YES — local JSONL |

---

## Service Startup Order

Services must be available in this order before Core can execute the full chain:

| Order | Service | Reason |
|---|---|---|
| 1 | Bucket | Truth store must be available for chain-state fetch |
| 2 | Sovereign | Risk assessment must be reachable |
| 3 | CET | Contract compilation must be reachable |
| 4 | Sarathi | Enforcement + JWT issuance must be reachable |
| 5 | Bridge | JWT validation gate must be reachable |
| 6 | InsightFlow | Optional — Core starts without it (GRACEFUL-FALLBACK) |
| 7 | **BHIV Core** | Starts last — all dependencies verified via health checks |

---

## Safe Shutdown Order

Services should be shut down in reverse dependency order:

| Order | Service | Pre-shutdown Action |
|---|---|---|
| 1 | **BHIV Core** | Stop accepting new requests, drain in-flight executions |
| 2 | InsightFlow | Flush pending dataset registrations |
| 3 | Bridge | Drain pending JWT validations |
| 4 | Sarathi | Drain pending enforcement requests |
| 5 | CET | No state — safe to stop immediately |
| 6 | Sovereign | No state — safe to stop immediately |
| 7 | Bucket | Verify all pending writes committed, flush hash chain |

---

## Replay Reconstruction Order

To reconstruct a trace from evidence:

| Order | Source | Data Retrieved |
|---|---|---|
| 1 | Bucket | Primary truth — artifact payload, hash chain, timestamps |
| 2 | InsightFlow | Secondary — dataset metadata, canonical_id |
| 3 | Core local logs | Tertiary — JSONL fallback, trace_origin details |
| 4 | Sovereign | Verify — re-run risk assessment for comparison |
| 5 | CET | Verify — re-compile contract for hash comparison |

Replay command: `GET /trace/{trace_id}` on Core reconstructs from all sources.

