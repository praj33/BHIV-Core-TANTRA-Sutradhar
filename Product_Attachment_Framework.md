# Product Attachment Framework — Phase IV

Version: 1.0.0
Date: 2026-06-19
Classification: PRODUCTION ATTACHMENT SPECIFICATION

---

## Attachment Model

Every BHIV product connects to Core through a standardized attachment interface.
Products become **attachable modules** — not custom integrations.

### Attachment Contract

Every product must define:

```yaml
product:
  name: "..."
  purpose: "..."
  owner: "..."
  version: "1.0.0"

trigger:
  type: "http_api | event | schedule | webhook"
  endpoint: "POST /execute_task"
  payload_schema: "{agent, input, input_type, tags}"

execution_path:
  entry: "Core /execute_task"
  agent: "edumentor_agent | vedas_agent | wellness_agent | custom_agent"
  authority_chain: "Sovereign → CET → Sarathi → Bridge"

trace_path:
  origin: "Core (trace_id generated)"
  propagation: "X-Trace-Id header on all calls"
  persistence: "Bucket (payload.trace_id)"

replay_path:
  reconstruction: "GET /trace/{trace_id}"
  sources: ["Bucket", "InsightFlow", "local logs"]

observability_path:
  telemetry: "InsightFlow /api/v1/datasets/"
  canonical_id: "BHIV-DS-{DOMAIN}-{PRODUCT}-{SEQ}"

truth_persistence:
  store: "Bucket /bucket/artifact"
  schema: "artifact_id, artifact_type, timestamp_utc, schema_version, source_module_id, payload"

governance_dependencies:
  decision: "Sovereign /analyze"
  contract: "CET /cet/compile"
  enforcement: "Sarathi /sarathi/enforce"
  validation: "Bridge /execute"

runtime_health:
  product_health: "GET /health on product"
  core_health: "GET /health on Core"
  dependency_health: "All governance participants"

recovery_behaviour:
  sovereign_down: "FAIL-CLOSED — no execution"
  bucket_down: "FAIL-CLOSED — execution marked FAILED"
  insightflow_down: "GRACEFUL — local fallback"
  product_down: "Core unaffected — product responsibility"

version_compatibility:
  core_version: ">=1.0.0"
  bucket_schema: "1.0.0"
  trace_protocol: "X-Trace-Id (uuid4)"
```

---

## Product Attachments

### 1. UniGuru

| Field | Value |
|---|---|
| **Product** | UniGuru |
| **Purpose** | University mentoring AI — personalized academic guidance |
| **Owner** | BHIV Team |
| **Trigger** | HTTP API: Student submits guidance query |
| **Execution Path** | UniGuru → Core /execute_task → edumentor_agent |
| **Trace Path** | Core generates trace_id → propagated to Sovereign, Bucket, InsightFlow |
| **Replay Path** | GET /trace/{trace_id} → reconstructs full guidance session |
| **Observability** | BHIV-DS-UNIGURU-GUIDANCE-{SEQ} on InsightFlow |
| **Truth Persistence** | Bucket: guidance_record artifact_type |
| **Governance** | Sovereign (content safety) → Bucket (truth) → InsightFlow (telemetry) |
| **Runtime Health** | UniGuru /health + Core /health |
| **Recovery** | UniGuru down = Core unaffected. Core down = UniGuru cannot execute. |
| **Version** | Architecture only — no deployment |

### 2. HackaVerse

| Field | Value |
|---|---|
| **Product** | HackaVerse |
| **Purpose** | Hackathon platform with AI-assisted project evaluation |
| **Owner** | BHIV Team |
| **Trigger** | HTTP API: Project submission / evaluation request |
| **Execution Path** | HackaVerse → Core /execute_task → evaluation_agent |
| **Trace Path** | Core generates trace_id → full TANTRA chain |
| **Replay Path** | GET /trace/{trace_id} → reconstructs evaluation lineage |
| **Observability** | BHIV-DS-HACKAVERSE-EVAL-{SEQ} on InsightFlow |
| **Truth Persistence** | Bucket: evaluation_record artifact_type |
| **Governance** | Sovereign (fairness check) → CET (evaluation contract) → Sarathi → Bucket |
| **Runtime Health** | HackaVerse /health + Core /health |
| **Recovery** | HackaVerse down = Core unaffected |
| **Version** | Architecture only |

### 3. SETU

| Field | Value |
|---|---|
| **Product** | SETU |
| **Purpose** | Integration bridge for external APIs and third-party systems |
| **Owner** | BHIV Team |
| **Trigger** | Webhook / Event: External system triggers via SETU |
| **Execution Path** | External → SETU → Core /execute_task → appropriate_agent |
| **Trace Path** | Core generates trace_id → SETU passes upstream correlation_id in metadata |
| **Replay Path** | GET /trace/{trace_id} + external correlation mapping |
| **Observability** | BHIV-DS-SETU-INTEGRATION-{SEQ} on InsightFlow |
| **Truth Persistence** | Bucket: integration_record artifact_type |
| **Governance** | Sovereign (input validation) → Bucket (truth) |
| **Runtime Health** | SETU /health + Core /health + external system health |
| **Recovery** | External down = SETU handles retry. Core down = SETU queues. |
| **Version** | Architecture only |

### 4. SUMSCRIPT

| Field | Value |
|---|---|
| **Product** | SUMSCRIPT |
| **Purpose** | Summarization and transcription engine |
| **Owner** | BHIV Team |
| **Trigger** | HTTP API: Document/audio submitted for summarization |
| **Execution Path** | SUMSCRIPT → Core /execute_task → text_agent / audio_agent |
| **Trace Path** | Core generates trace_id → propagated through chain |
| **Replay Path** | GET /trace/{trace_id} → reconstructs summarization session |
| **Observability** | BHIV-DS-SUMSCRIPT-SUMMARY-{SEQ} on InsightFlow |
| **Truth Persistence** | Bucket: summary_record artifact_type |
| **Governance** | Sovereign (content safety) → Bucket (truth) |
| **Runtime Health** | SUMSCRIPT /health + Core /health |
| **Recovery** | SUMSCRIPT down = Core unaffected |
| **Version** | Architecture only |

### 5. ERP

| Field | Value |
|---|---|
| **Product** | BHIV ERP |
| **Purpose** | Enterprise resource planning with AI-assisted decision making |
| **Owner** | BHIV Team |
| **Trigger** | HTTP API / Schedule: Business process triggers |
| **Execution Path** | ERP → Core /execute_task → business_agent |
| **Trace Path** | Core generates trace_id → full TANTRA chain (financial compliance) |
| **Replay Path** | GET /trace/{trace_id} → complete audit trail |
| **Observability** | BHIV-DS-ERP-DECISION-{SEQ} on InsightFlow |
| **Truth Persistence** | Bucket: erp_decision artifact_type (LEGAL GRADE — immutable) |
| **Governance** | Full chain: Sovereign → CET → Sarathi → Bridge → Bucket |
| **Runtime Health** | ERP /health + full governance chain health |
| **Recovery** | FAIL-CLOSED — financial compliance requires all participants |
| **Version** | Architecture only |

### 6. Fraud Detection

| Field | Value |
|---|---|
| **Product** | Fraud Detection System |
| **Purpose** | Real-time fraud detection and evidence collection |
| **Owner** | BHIV Team |
| **Trigger** | Event / Webhook: Transaction alerts |
| **Execution Path** | Alert → FDS → Core /execute_task → fraud_analysis_agent |
| **Trace Path** | Core generates trace_id → full TANTRA chain (evidence grade) |
| **Replay Path** | GET /trace/{trace_id} → legal evidence reconstruction |
| **Observability** | BHIV-DS-FRAUD-EVIDENCE-{SEQ} on InsightFlow |
| **Truth Persistence** | Bucket: fraud_evidence artifact_type (LEGAL EVIDENCE GRADE) |
| **Governance** | Full chain: Sovereign → CET → Sarathi → Bridge → Bucket |
| **Runtime Health** | FDS /health + full chain health |
| **Recovery** | FAIL-CLOSED — evidence integrity requires all participants |
| **Version** | Architecture only |

### 7. AI Video

| Field | Value |
|---|---|
| **Product** | AI Video |
| **Purpose** | AI-powered video generation and processing |
| **Owner** | BHIV Team |
| **Trigger** | HTTP API: Video generation / processing request |
| **Execution Path** | AI Video → Core /execute_task → video_agent |
| **Trace Path** | Core generates trace_id → Sovereign + Bucket |
| **Replay Path** | GET /trace/{trace_id} → video generation lineage |
| **Observability** | BHIV-DS-AIVIDEO-GENERATION-{SEQ} on InsightFlow |
| **Truth Persistence** | Bucket: video_record artifact_type |
| **Governance** | Sovereign (content safety) → Bucket (truth) |
| **Recovery** | AI Video down = Core unaffected |
| **Version** | Architecture only |

### 8. Future Robotics

| Field | Value |
|---|---|
| **Product** | Robotics Interface |
| **Purpose** | AI-driven robotics control and decision making |
| **Trigger** | Event: Sensor data / control commands |
| **Execution Path** | Robot → Core /execute_task → robotics_agent |
| **Governance** | Full chain — safety-critical requires all participants |
| **Recovery** | FAIL-CLOSED — safety-critical operations |
| **Version** | Architecture only |

### 9. Future XR

| Field | Value |
|---|---|
| **Product** | XR (Extended Reality) |
| **Purpose** | AI-assisted XR experiences and spatial computing |
| **Trigger** | Event: User interaction in XR environment |
| **Execution Path** | XR App → Core /execute_task → xr_agent |
| **Governance** | Sovereign (content safety) → Bucket (session truth) |
| **Recovery** | XR down = Core unaffected |
| **Version** | Architecture only |

### 10. Future Blockchain

| Field | Value |
|---|---|
| **Product** | Blockchain Integration |
| **Purpose** | On-chain verification of Bucket truth records |
| **Trigger** | Schedule: Periodic hash anchoring |
| **Execution Path** | Scheduler → Core → Bucket (read chain-state) → Blockchain (anchor) |
| **Governance** | Full chain — immutability verification |
| **Truth Persistence** | Bucket hash chain → blockchain anchor |
| **Recovery** | Blockchain down = Bucket remains source of truth |
| **Version** | Architecture only |

---

## Attachment Validation Checklist

Before any product goes live, verify:

- [ ] Product calls Core /execute_task (not direct agent calls)
- [ ] trace_id propagated from Core response to product logs
- [ ] Execution token obtained (via Sarathi or Core-issued)
- [ ] Bucket write confirmed for every execution
- [ ] InsightFlow emission confirmed (or local fallback active)
- [ ] Product /health endpoint exists
- [ ] Failure behaviour documented (FAIL-CLOSED or GRACEFUL)
- [ ] Canonical_id format registered with InsightFlow
- [ ] artifact_type registered with Bucket schema
- [ ] Recovery behaviour tested
