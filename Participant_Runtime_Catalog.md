# Participant Runtime Catalog — Phase IV Production

Version: 1.0.0
Date: 2026-06-19
Classification: PRODUCTION RUNTIME REGISTRY

---

## BHIV Core

| Field | Value |
|---|---|
| **Product Name** | BHIV Core |
| **Module** | core_api.py, core/authority/*, core/trace/* |
| **Owner** | Raj Prajapati |
| **Ecosystem Layer(s)** | Orchestration, Governance |
| **Runtime Role** | Central orchestrator — trace origin, execution gate, authority router |
| **Upstream Dependencies** | Products (Gurukul, UniGuru, etc.) |
| **Downstream Dependencies** | Sovereign, CET, Sarathi, Bridge, Bucket, InsightFlow |
| **API Endpoints** | POST /execute_task, POST /execute_sequence, GET /trace/{id}, GET /traces, GET /health, GET / |
| **Authentication** | execution_token (from Sarathi) + trace_id required on all execute calls |
| **Trace Participation** | ORIGIN — generates trace_id (uuid4), propagates X-Trace-Id on all outbound calls |
| **Replay Participation** | FULL — GET /trace/{id} reconstructs lineage from Bucket + InsightFlow + local logs |
| **Health Endpoint** | GET /health → {"status": "healthy", "service": "BHIV Core API", "version": "1.0.0"} |
| **Failure Behaviour** | FAIL-CLOSED on all authority calls. BucketWriteError = execution FAILED. Only InsightFlow is non-blocking. |
| **Authority Owned** | trace_id generation, execution gating, token validation, agent routing, replay reconstruction |
| **Authority NOT Owned** | Decision making (Sovereign), enforcement policy (Sarathi), contract compilation (CET), validation rules (Bridge), truth storage schema (Bucket), telemetry schema (InsightFlow) |
| **Current Status** | OPERATIONAL — 142/142 tests, full chain proven |
| **Canonical Version** | 1.0.0 |

---

## Sovereign Core

| Field | Value |
|---|---|
| **Product Name** | Sovereign Core |
| **Module** | External service (Aakanksha, hosted on Rajaryan gateway) |
| **Owner** | Aakanksha |
| **Ecosystem Layer(s)** | Governance |
| **Runtime Role** | Decision authority — evaluates input risk, issues ALLOW/DENY verdict |
| **Upstream Dependencies** | None |
| **Downstream Dependencies** | None (produces decisions consumed by Core) |
| **API Endpoints** | POST /analyze |
| **Authentication** | None (open endpoint) |
| **Trace Participation** | PASSIVE — receives X-Trace-Id header from Core |
| **Replay Participation** | INDIRECT — decision recorded in Bucket by Core |
| **Health Endpoint** | GET / (returns service info) |
| **Failure Behaviour** | Core FAIL-CLOSED — if Sovereign unreachable, no execution occurs |
| **Authority Owned** | Risk scoring, risk categorization (LOW/MEDIUM/HIGH/CRITICAL), confidence assessment |
| **Authority NOT Owned** | Execution, enforcement, contract compilation, truth storage |
| **Current Status** | OPERATIONAL — real ALLOW decision proven (risk=LOW, confidence=0.5) |
| **Canonical Version** | 1.0 |

---

## CET (Contract Execution Template)

| Field | Value |
|---|---|
| **Product Name** | CET |
| **Module** | External service (Tanvi) |
| **Owner** | Tanvi |
| **Ecosystem Layer(s)** | Governance |
| **Runtime Role** | Contract compiler — generates cryptographic contract from decision + input |
| **Upstream Dependencies** | Sovereign (needs decision_hash) |
| **Downstream Dependencies** | Bridge (consumes contract_hash) |
| **API Endpoints** | POST /cet/compile, GET /health |
| **Authentication** | None |
| **Trace Participation** | PASSIVE — receives trace_id in payload and X-Trace-Id header |
| **Replay Participation** | INDIRECT — contract_hash recorded in Bucket by Core |
| **Health Endpoint** | GET /health → {"status": "ok"} |
| **Failure Behaviour** | Core FAIL-CLOSED (USE_FULL_TANTRA=true) or GRACEFUL-FALLBACK (internal hash) |
| **Authority Owned** | Contract compilation, contract schema, validation rules for compile inputs |
| **Authority NOT Owned** | Decision making, enforcement, execution, truth storage |
| **Current Status** | PARTIAL — health OK, /cet/compile returns 502 (Render timeout) |
| **Canonical Version** | 1.0 |

---

## Sarathi (Enforcement Gateway)

| Field | Value |
|---|---|
| **Product Name** | Sarathi |
| **Module** | External service (Rajaryan) |
| **Owner** | Rajaryan |
| **Ecosystem Layer(s)** | Governance, Control Plane |
| **Runtime Role** | Enforcement — validates decisions, issues execution tokens, governs execution |
| **Upstream Dependencies** | Sovereign (needs decision), Sutradhara (Layer 2), DGIC (epistemic state) |
| **Downstream Dependencies** | Bridge (consumes execution_token) |
| **API Endpoints** | POST /sarathi/enforce, GET /sarathi/validate-token, POST /api/v1/sutradhara/invoke, POST /api/v1/dgic/ingest |
| **Authentication** | Ed25519 signing — Core's fingerprint registered |
| **Trace Participation** | ACTIVE — generates trace_hash, validates decision_hash |
| **Replay Participation** | INDIRECT — enforcement signal recorded in Bucket by Core |
| **Health Endpoint** | GET / (returns service info) |
| **Failure Behaviour** | Core FAIL-CLOSED — no token = no execution |
| **Authority Owned** | Enforcement policy, token issuance, token validation, execution_token TTL |
| **Authority NOT Owned** | Decision making (Sovereign), contract compilation (CET), truth storage (Bucket) |
| **Current Status** | PARTIAL — service alive, 422 on /sarathi/enforce (token schema mismatch) |
| **Canonical Version** | 1.0 |

---

## Bridge (Gated Validation)

| Field | Value |
|---|---|
| **Product Name** | Gated Bridge |
| **Module** | External service (Ranjit) |
| **Owner** | Ranjit |
| **Ecosystem Layer(s)** | Governance |
| **Runtime Role** | Final validation gate — last checkpoint before execution proceeds |
| **Upstream Dependencies** | Sarathi (needs execution_token), CET (needs contract_hash) |
| **Downstream Dependencies** | None (gate pass = execution proceeds) |
| **API Endpoints** | POST /execute |
| **Authentication** | Token-based (returns 401 without valid token) |
| **Trace Participation** | PASSIVE — receives X-Trace-Id header and trace_id in payload |
| **Replay Participation** | INDIRECT — validation status recorded in Bucket by Core |
| **Health Endpoint** | None discovered |
| **Failure Behaviour** | Core FAIL-CLOSED (USE_FULL_TANTRA=true) or GRACEFUL-FALLBACK (internal validation) |
| **Authority Owned** | Validation rules, gate logic, execution approval/rejection |
| **Authority NOT Owned** | Decision, enforcement, contract, truth storage, telemetry |
| **Current Status** | PARTIAL — service alive, auth enforced (HTTP 401), ngrok intermittent |
| **Canonical Version** | 1.0 |

---

## Bucket (Truth Store)

| Field | Value |
|---|---|
| **Product Name** | Bucket |
| **Module** | External service (Siddhesh) |
| **Owner** | Siddhesh |
| **Ecosystem Layer(s)** | Infrastructure, Observability |
| **Runtime Role** | Append-only truth store — immutable execution records with hash chain |
| **Upstream Dependencies** | None |
| **Downstream Dependencies** | None (consumed by replay reconstruction) |
| **API Endpoints** | POST /bucket/artifact, GET /bucket/artifact/{id}, GET /bucket/artifacts, POST /bucket/validate-replay, GET /bucket/chain-state, GET /bucket/certification, GET /bucket/schema-info |
| **Authentication** | Schema validation (envelope must match: artifact_id, artifact_type, timestamp_utc, schema_version, source_module_id, payload) |
| **Trace Participation** | PASSIVE — receives trace_id inside payload. Domain-agnostic (validates structure, NOT content). |
| **Replay Participation** | PRIMARY SOURCE — all replay reconstruction queries Bucket first |
| **Health Endpoint** | GET /health |
| **Failure Behaviour** | Core FAIL-CLOSED — BucketWriteError = execution marked FAILED |
| **Authority Owned** | Truth storage schema, hash chain integrity, append-only invariant, artifact validation |
| **Authority NOT Owned** | Payload content, decision logic, enforcement, execution |
| **Current Status** | OPERATIONAL — real write proven (hash c1b89f0e, storage_type=append_only) |
| **Canonical Version** | 1.0.0 (schema_version) |

---

## InsightFlow (Data Universe Registry)

| Field | Value |
|---|---|
| **Product Name** | InsightFlow |
| **Module** | External service (Vijay) |
| **Owner** | Vijay |
| **Ecosystem Layer(s)** | Observability |
| **Runtime Role** | Telemetry, dataset registration, ecosystem-wide observability |
| **Upstream Dependencies** | None |
| **Downstream Dependencies** | None (consumed by operations dashboard) |
| **API Endpoints** | POST /api/v1/datasets/, GET /health |
| **Authentication** | X-API-Key header required |
| **Trace Participation** | PASSIVE — receives trace_id in metadata |
| **Replay Participation** | SECONDARY SOURCE — replay checks InsightFlow after Bucket |
| **Health Endpoint** | GET /health → {"status": "healthy", "version": "1.0.0"} |
| **Failure Behaviour** | Core GRACEFUL-FALLBACK — only non-blocking participant. Falls back to local JSONL. |
| **Authority Owned** | Dataset registration schema, canonical_id format (BHIV-DS-DOMAIN-NAME-XXX), telemetry classification |
| **Authority NOT Owned** | Execution, decision, enforcement, truth storage |
| **Current Status** | OPERATIONAL — HTTP 201, dataset BHIV-DS-TANTRA-CHAIN-DC3F760F registered |
| **Canonical Version** | 1.0.0 |

---

## Registry Extension Model

To add a new participant, populate the following fields in TANTRA_INTEGRATION_REGISTRY.json:

```json
{
  "new_participant_id": {
    "system_name": "...",
    "owner": "...",
    "purpose": "...",
    "ecosystem_layers": ["Governance|Infrastructure|Observability|Product"],
    "runtime_role": "...",
    "upstream_dependencies": [],
    "downstream_dependencies": [],
    "api_endpoints": [],
    "authentication": "...",
    "trace_participation": "ORIGIN|ACTIVE|PASSIVE",
    "replay_participation": "PRIMARY|SECONDARY|INDIRECT|NONE",
    "health_endpoint": "...",
    "failure_behaviour": "FAIL-CLOSED|GRACEFUL-FALLBACK",
    "authority_owned": [],
    "authority_not_owned": [],
    "current_status": "ARCHITECTURAL|CONNECTED|INTEGRATED|OPERATIONAL",
    "canonical_version": "1.0.0"
  }
}
```

No code changes required. Registry-driven participant discovery.
