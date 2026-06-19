# Production Runtime Integration Registry — Phase IV

Version: 1.0.0
Date: 2026-06-19
Lead: Raj Prajapati
Classification: PRODUCTION RUNTIME REGISTRY

---

## Purpose

This registry is the **authoritative runtime map** for BHIV Core's TANTRA ecosystem.
Every participant, product, and integration point is documented here.

Future products integrate by following this registry — not by creating custom integrations.

---

## Registry Documents

| # | Document | Purpose |
|---|---|---|
| 1 | [Participant_Runtime_Catalog.md](Participant_Runtime_Catalog.md) | Full metadata for all 7 infrastructure participants |
| 2 | [Product_Attachment_Framework.md](Product_Attachment_Framework.md) | How 10 products attach to Core |
| 3 | [Runtime_Layer_Map.md](Runtime_Layer_Map.md) | 6-layer ecosystem with responsibilities and authority limits |
| 4 | [Production_Readiness_Matrix.md](Production_Readiness_Matrix.md) | 11-dimension readiness for all participants |
| 5 | [Canonical_Runtime_Sequence.md](Canonical_Runtime_Sequence.md) | 12-transition execution sequence with protocol details |
| 6 | [Runtime_Dependency_Graph.md](Runtime_Dependency_Graph.md) | Dependencies, recovery, startup, shutdown, replay order |

---

## Participant Summary

| Participant | Owner | Layer | Status | Authority Owned |
|---|---|---|---|---|
| BHIV Core | Raj | Orchestration | CONVERGED | trace_id, execution gate, agent routing, replay |
| Sovereign | Aakanksha | Governance | INTEGRATED | Risk scoring, decision |
| CET | Tanvi | Governance | CONNECTED | Contract compilation |
| Sarathi | Rajaryan | Governance | CONNECTED | Enforcement, token issuance |
| Bridge | Ranjit | Governance | CONNECTED | Validation gate |
| Bucket | Siddhesh | Infrastructure | INTEGRATED | Truth storage, hash chain |
| InsightFlow | Vijay | Observability | INTEGRATED | Telemetry, dataset registry |

---

## Authority Boundary Map

### Core OWNS:
- trace_id generation (uuid4)
- X-Trace-Id propagation
- Execution gating (token validation)
- Agent routing
- Replay reconstruction
- Bucket write orchestration
- InsightFlow emission orchestration

### Core DOES NOT OWN:
- Decision making → Sovereign
- Contract compilation → CET
- Enforcement policy → Sarathi
- Validation rules → Bridge
- Truth storage schema → Bucket
- Telemetry schema → InsightFlow
- Risk scoring → Sovereign
- Token issuance → Sarathi

---

## Adding a New Participant

1. Add entry to `TANTRA_INTEGRATION_REGISTRY.json` using the extension template
2. Document in `Participant_Runtime_Catalog.md`
3. Create HTTP client in `core/authority/` following existing patterns
4. Wire URL in `.env.live`
5. Add trace header propagation (X-Trace-Id)
6. Define failure behaviour (FAIL-CLOSED or GRACEFUL-FALLBACK)
7. Add health check to monitoring
8. Run integration test suite

**No architectural redesign required.**

---

## Adding a New Product

1. Define product attachment in `Product_Attachment_Framework.md`
2. Choose agent(s) for execution
3. Call Core POST /execute_task with execution_token and trace_id
4. Handle Core responses (200, 403, 500)
5. Log trace_id in product telemetry
6. Verify Bucket write appears for every execution
7. Register canonical_id format with InsightFlow

**No Core code changes required.**

---

## Integration Evidence

### Sample Participant Registration (Sovereign)

```json
{
  "sovereign": {
    "system_name": "Sovereign Core",
    "owner": "Aakanksha",
    "ecosystem_layers": ["Governance"],
    "runtime_role": "Decision authority",
    "api_endpoints": ["POST /analyze"],
    "trace_participation": "PASSIVE",
    "failure_behaviour": "FAIL-CLOSED",
    "authority_owned": ["risk_scoring", "risk_categorization"],
    "authority_not_owned": ["execution", "enforcement", "truth_storage"],
    "current_status": "OPERATIONAL",
    "canonical_version": "1.0"
  }
}
```

### Sample Product Attachment (UniGuru)

```yaml
product: UniGuru
trigger: HTTP API (student query)
execution_path: UniGuru → Core /execute_task → edumentor_agent
trace_path: Core generates trace_id → propagated to all downstream
replay_path: GET /trace/{trace_id}
observability: BHIV-DS-UNIGURU-GUIDANCE-{SEQ}
truth_persistence: Bucket (guidance_record)
governance: Sovereign → Bucket → InsightFlow
```

### Live Integration Evidence

| Call | Service | Result | Proof |
|---|---|---|---|
| POST /analyze | Sovereign | ALLOW, risk=LOW | logs/live_sovereign_proof.json |
| POST /bucket/artifact | Bucket | hash c1b89f0e stored | logs/full_tantra_live_chain_proof.json |
| POST /api/v1/datasets/ | InsightFlow | HTTP 201, ACTIVE | dataset BHIV-DS-TANTRA-CHAIN-DC3F760F |
| POST /execute | Bridge | HTTP 401 (auth enforced) | LIVE_TRACE_PACKET.md |
| GET /health | CET | HTTP 200 OK | LIVE_TRACE_PACKET.md |
| POST /sarathi/enforce | Sarathi | HTTP 422 (alive) | LIVE_TRACE_PACKET.md |
