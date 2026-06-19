# Runtime Dependency Graph — Phase IV

Version: 1.0.0
Date: 2026-06-19

---

## Critical Dependencies (execution blocks if unavailable)

| Dependency | Consumer | Impact if Down | Classification |
|---|---|---|---|
| Sovereign | Core | No decision → no execution | CRITICAL |
| Sarathi | Core | No token → no execution | CRITICAL |
| Bucket | Core | No truth write → execution FAILED | CRITICAL |
| CET | Core (FULL_TANTRA) | No contract → no validation | CRITICAL (live mode) |
| Bridge | Core (FULL_TANTRA) | No validation → execution blocked | CRITICAL (live mode) |

## Optional Participants (execution continues if unavailable)

| Participant | Consumer | Impact if Down | Classification |
|---|---|---|---|
| InsightFlow | Core | Local JSONL fallback | OPTIONAL |
| CET | Core (non-FULL_TANTRA) | Internal hash fallback | OPTIONAL |
| Bridge | Core (non-FULL_TANTRA) | Internal validation (always VALIDATED) | OPTIONAL |
| KarmaChain | Core agents | Karma not updated, execution continues | OPTIONAL |

## Blocking Participants

| Participant | What it Blocks | Unblock Requirement |
|---|---|---|
| Sovereign | All execution | Sovereign must return risk_category |
| Sarathi | All execution | Sarathi must return status=CLEARED + execution_token |
| Bucket | Execution finalization | Bucket must return hash + artifact_id |
| CET (live) | Bridge validation | CET must return contract_hash |
| Bridge (live) | Agent execution | Bridge must return VALIDATED |

---

## Fallback Behaviour

| Participant Down | Fallback | Data Preserved? |
|---|---|---|
| Sovereign | NONE — execution aborted | No (fail-closed) |
| CET | Internal contract hash (if USE_FULL_TANTRA=false) | Yes (internal hash) |
| Sarathi | NONE — execution aborted | No (fail-closed) |
| Bridge | Internal validation (if USE_FULL_TANTRA=false) | Yes (always VALIDATED) |
| Bucket (external) | Local JSONL fallback | Yes (local log) |
| InsightFlow | Local JSONL fallback | Yes (local log) |
| KarmaChain | Karma update skipped | Execution result preserved |
| Agent service | Agent error → fallback_agent attempted | Partial |

---

## Fail-Closed Behaviour

Every FAIL-CLOSED scenario produces deterministic output:

| Failure | HTTP Code | Error Type | Trace Preserved? |
|---|---|---|---|
| Sovereign unreachable | 500 | ConnectionError → TANTRAFlowError | Partial (origin only) |
| Sarathi unreachable | 500 | ConnectionError → TANTRAFlowError | Partial (origin + decision) |
| Sarathi DENY | 500 | SarathiEnforcementError | Yes (decision + enforcement) |
| Bridge reject | 500 | BridgeError → TANTRAFlowError | Yes (up to bridge step) |
| Bucket write fail | 500 | BucketWriteError → ExecutionFinalizationError | Yes (local fallback) |
| Token replay | 403 | ExecutionBlockedError | Yes (attempt logged) |
| Token missing | 403 | HTTPException | No (rejected at gate) |
| Signature tamper | 500 | SovereignSigningError | Yes (tamper logged) |

---

## Recovery Order

When restarting after failure, services must come up in this order:

```
1. Bucket          (truth store must be available first)
2. Sovereign       (decision authority — no dependency)
3. InsightFlow     (telemetry — no dependency)
4. CET             (needs Sovereign available for compile)
5. Sarathi         (needs Sovereign + CET)
6. Bridge          (needs Sarathi + CET)
7. BHIV Core       (needs all governance + infrastructure)
8. Products        (need Core)
```

---

## Service Startup Order

```
Phase 1 — Infrastructure:  Bucket, InsightFlow
Phase 2 — Governance:      Sovereign, CET
Phase 3 — Enforcement:     Sarathi, Bridge
Phase 4 — Orchestration:   BHIV Core
Phase 5 — Products:        Gurukul, UniGuru, etc.
```

## Safe Shutdown Order (reverse)

```
Phase 1 — Products:        Stop accepting user requests
Phase 2 — Orchestration:   Core drains in-flight executions
Phase 3 — Enforcement:     Sarathi, Bridge stop accepting new tokens
Phase 4 — Governance:      Sovereign, CET stop accepting new decisions
Phase 5 — Infrastructure:  Bucket finalizes pending writes, InsightFlow flushes
```

---

## Replay Reconstruction Order

When reconstructing a trace:

```
1. Query Bucket           (primary source — immutable truth)
2. Query InsightFlow      (secondary — telemetry metadata)
3. Query local logs       (tertiary — replay_protection.jsonl, insightflow_traces.jsonl)
4. Aggregate signals      (merge by trace_id, sort by timestamp)
5. Validate hash chain    (verify Bucket hashes are consistent)
6. Produce lineage        (ordered list of signals from all sources)
```

---

## Dependency Diagram

```
                    ┌─────────────┐
                    │   Products  │
                    │  (Layer 1)  │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │  BHIV Core  │
                    │  (Layer 2)  │
                    └──┬──┬──┬──┬─┘
                       │  │  │  │
           ┌───────────┘  │  │  └───────────┐
           │              │  │              │
     ┌─────┴─────┐  ┌────┴──┴────┐  ┌──────┴──────┐
     │ Sovereign  │  │  CET       │  │   Sarathi   │
     │ (CRITICAL) │  │ (CRITICAL*)│  │ (CRITICAL)  │
     └────────────┘  └────────────┘  └──────┬──────┘
                                            │
                                     ┌──────┴──────┐
                                     │   Bridge    │
                                     │ (CRITICAL*) │
                                     └─────────────┘

     * CRITICAL only when USE_FULL_TANTRA=true

     ┌─────────────┐     ┌─────────────┐
     │   Bucket    │     │ InsightFlow │
     │ (CRITICAL)  │     │ (OPTIONAL)  │
     └─────────────┘     └─────────────┘
```
