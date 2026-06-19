# Runtime Layer Map — Phase IV

Version: 1.0.0
Date: 2026-06-19

---

## Layer 1 — Product Layer

| Field | Value |
|---|---|
| **Responsibilities** | User-facing applications, domain-specific logic, UX |
| **Capabilities** | Submit execution requests, receive results, display outcomes |
| **Interfaces** | HTTP API calls to Core /execute_task and /execute_sequence |
| **Participants** | Gurukul, UniGuru, HackaVerse, SETU, SUMSCRIPT, ERP, Fraud Detection, AI Video, Robotics, XR, Blockchain |
| **Authority Limits** | Products CANNOT bypass Core. Products CANNOT call Sovereign/Sarathi/Bucket directly. Products MUST use Core as the single entry point. |
| **Required Evidence** | trace_id logged per request, product /health endpoint, error handling for Core unavailability |
| **Current Maturity** | ARCHITECTURAL — no products deployed through Core yet |
| **Target Production Maturity** | Products attach via registry, no custom integration code |

---

## Layer 2 — Orchestration Layer

| Field | Value |
|---|---|
| **Responsibilities** | Trace origin, agent routing, execution gating, authority coordination |
| **Capabilities** | Generate trace_id, route to agents, enforce token-gated execution, record to Bucket, emit to InsightFlow |
| **Interfaces** | FastAPI endpoints (POST /execute_task, POST /execute_sequence, GET /trace/{id}, GET /health) |
| **Participants** | BHIV Core (sole participant) |
| **Authority Limits** | Core DOES NOT make decisions (Sovereign does). Core DOES NOT enforce policy (Sarathi does). Core DOES NOT compile contracts (CET does). Core DOES NOT validate gates (Bridge does). Core DOES NOT define truth schema (Bucket does). |
| **Required Evidence** | 142/142 tests, full chain proof, replay reconstruction, LIVE_TRACE_PACKET |
| **Current Maturity** | CONVERGED — production-ready |
| **Target Production Maturity** | Deployment to Render/cloud, TLS, rate limiting, monitoring |

---

## Layer 3 — Governance Layer

| Field | Value |
|---|---|
| **Responsibilities** | Decision making, contract compilation, enforcement, validation |
| **Capabilities** | Risk scoring (Sovereign), contract hashing (CET), token issuance (Sarathi), gate validation (Bridge) |
| **Interfaces** | POST /analyze, POST /cet/compile, POST /sarathi/enforce, POST /execute |
| **Participants** | Sovereign (Aakanksha), CET (Tanvi), Sarathi (Rajaryan), Bridge (Ranjit), Sutradhara (Rajaryan), DGIC (Rajaryan) |
| **Authority Limits** | Governance DOES NOT execute tasks. Governance DOES NOT store truth. Governance DOES NOT generate trace_id. Each governance participant owns ONLY its specific authority. |
| **Required Evidence** | Decision proof (Sovereign), contract hash (CET), enforcement signal (Sarathi), validation status (Bridge) |
| **Current Maturity** | CONNECTED — all services reachable, 3 need schema alignment |
| **Target Production Maturity** | All schema mismatches resolved, real enforcement chain proven end-to-end |

---

## Layer 4 — Infrastructure Layer

| Field | Value |
|---|---|
| **Responsibilities** | Truth storage, hash chain integrity, append-only audit trail |
| **Capabilities** | Immutable artifact storage, hash chain verification, replay validation, chain state certification |
| **Interfaces** | POST /bucket/artifact, GET /bucket/artifact/{id}, POST /bucket/validate-replay, GET /bucket/chain-state |
| **Participants** | Bucket (Siddhesh), KarmaChain (Siddhesh) |
| **Authority Limits** | Bucket validates STRUCTURE, not CONTENT (domain-agnostic). Bucket DOES NOT make decisions. Bucket DOES NOT enforce policy. |
| **Required Evidence** | Real write with hash chain, append-only invariant, schema validation |
| **Current Maturity** | INTEGRATED — real writes proven, hash chain working |
| **Target Production Maturity** | Bucket backup/replication, KarmaChain deployment, chain anchoring |

---

## Layer 5 — Observability Layer

| Field | Value |
|---|---|
| **Responsibilities** | Telemetry, dataset registration, execution monitoring, ecosystem-wide visibility |
| **Capabilities** | Dataset registration, trace metadata storage, health monitoring |
| **Interfaces** | POST /api/v1/datasets/, GET /health |
| **Participants** | InsightFlow (Vijay) |
| **Authority Limits** | InsightFlow DOES NOT block execution (only non-blocking participant). InsightFlow DOES NOT replace Bucket as source of truth. InsightFlow is BEST-EFFORT. |
| **Required Evidence** | Dataset registration proof, canonical_id format, metadata schema |
| **Current Maturity** | INTEGRATED — real dataset registration proven |
| **Target Production Maturity** | Dashboard visualization, alerting, SLA monitoring |

---

## Layer 6 — Agent Layer

| Field | Value |
|---|---|
| **Responsibilities** | Domain-specific task execution (education, wellness, audio, voice, etc.) |
| **Capabilities** | Text processing, knowledge retrieval, audio processing, voice synthesis, image processing |
| **Interfaces** | Internal Python calls via execute_task() |
| **Participants** | edumentor_agent, vedas_agent, wellness_agent, knowledge_agent, audio_agent, voice_persona_agent, image_agent, archive_agent, stream_transformer_agent |
| **Authority Limits** | Agents CANNOT bypass execution gate. Agents CANNOT write directly to Bucket. Agents CANNOT call Sovereign. All agent execution goes through Core's gated_execute. |
| **Required Evidence** | Agent registry, agent health, execution results |
| **Current Maturity** | PARTIAL — 9 agents registered, not all production-tested |
| **Target Production Maturity** | All agents testable, hot-pluggable, metrics-emitting |

---

## Layer Interaction Rules

1. **Products → Core ONLY.** No direct calls to governance or infrastructure.
2. **Core → Governance → Core.** Core calls governance services, receives signals, continues.
3. **Core → Infrastructure.** Core writes to Bucket and emits to InsightFlow after execution.
4. **Governance participants do NOT call each other through Core.** Sarathi may internally call Sutradhara/DGIC.
5. **Agents execute within Core's process.** No external agent calls (except configured HTTP agents).
6. **trace_id flows TOP-DOWN.** Generated at Layer 2 (Core), propagated to all lower layers.
