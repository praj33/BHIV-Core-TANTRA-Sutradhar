# Participant Runtime Catalog — Phase IV Final

Version: 3.0.0
Date: 2026-06-20
Status: ✅ All 7 participants verified operational

---

## 1. BHIV Core

| Field | Value |
|---|---|
| **Product Name** | BHIV Core |
| **Module** | core/ (authority, trace, execution, bucket, insightflow clients) |
| **Owner** | Raj Prajapati |
| **Ecosystem Layer(s)** | Origin, Execution |
| **Runtime Role** | Runtime backbone — orchestrates the 8-step TANTRA execution chain |
| **Upstream Dependencies** | None (origin point) |
| **Downstream Dependencies** | Sovereign, CET, Sarathi, Bridge, Bucket, InsightFlow |
| **API Endpoints** | POST /execute, GET /health, GET /trace/{id} |
| **Authentication** | Accepts Sarathi JWT, forwards to Bridge as Bearer token |
| **Trace Participation** | GENERATOR — creates uuid4 trace_id, propagates via X-Trace-Id header |
| **Replay Participation** | FULL — GET /trace/{id}, reconstruct_trace from Bucket+InsightFlow+local logs |
| **Health Endpoint** | GET /health → structured JSON with version, status, uptime |
| **Failure Behaviour** | FAIL-CLOSED on governance (Sovereign, Sarathi, Bucket). GRACEFUL-FALLBACK on InsightFlow. |
| **Authority Owned** | Trace generation, chain orchestration, agent execution, replay reconstruction |
| **Authority NOT Owned** | Risk decisions (Sovereign), contract compilation (CET), enforcement (Sarathi), JWT validation (Bridge), truth storage (Bucket), dataset registry (InsightFlow) |
| **Current Status** | ✅ OPERATIONAL — 8/8 chain SUCCESS |
| **Canonical Version** | 1.0.0 |

---

## 2. Sovereign

| Field | Value |
|---|---|
| **Product Name** | Sovereign (Risk Assessment Service) |
| **Module** | External — Aakanksha's text-risk-scoring-service |
| **Owner** | Aakanksha |
| **Ecosystem Layer(s)** | Governance |
| **Runtime Role** | Risk assessment — determines ALLOW/DENY based on content analysis |
| **Upstream Dependencies** | BHIV Core (receives text input + X-Trace-Id) |
| **Downstream Dependencies** | None (returns decision to Core) |
| **API Endpoints** | POST /analyze |
| **Authentication** | None (open endpoint) |
| **Trace Participation** | RECEIVER — accepts X-Trace-Id header, decision recorded by Core in Bucket |
| **Replay Participation** | INDIRECT — decision hash stored in Bucket by Core, retrievable via replay |
| **Health Endpoint** | GET / → service info |
| **Failure Behaviour** | Core FAIL-CLOSED — unreachable Sovereign = execution blocked |
| **Authority Owned** | Risk assessment, ALLOW/DENY decisions, risk scoring |
| **Authority NOT Owned** | Contract compilation, enforcement, JWT issuance, execution, truth storage |
| **Current Status** | ✅ OPERATIONAL (HTTP 200, ALLOW, risk=LOW) |
| **Canonical Version** | Render deployment (text-risk-scoring-service.onrender.com) |

---

## 3. CET (Compliance Execution Transpiler)

| Field | Value |
|---|---|
| **Product Name** | CET (Compliance Execution Transpiler) |
| **Module** | External — Tanvi's sl-validator-parity |
| **Owner** | Tanvi |
| **Ecosystem Layer(s)** | Governance |
| **Runtime Role** | Compiles KSML decision objects into executable SUM-SCRIPTs with constraint validation |
| **Upstream Dependencies** | BHIV Core (receives KSML payload + X-Trace-Id) |
| **Downstream Dependencies** | None (returns contract_hash to Core) |
| **API Endpoints** | POST /cet/compile, GET /health |
| **Authentication** | None (open endpoint) |
| **Trace Participation** | RECEIVER — trace_id in payload, contract_hash linked to trace |
| **Replay Participation** | INDIRECT — contract_hash stored in Bucket by Core, retrievable via replay |
| **Health Endpoint** | GET /health → `{"status": "ok"}` |
| **Failure Behaviour** | Core FAIL-CLOSED or internal fallback hash generation |
| **Authority Owned** | KSML compilation, SUM-SCRIPT generation, constraint validation |
| **Authority NOT Owned** | Risk decisions, enforcement, JWT issuance, execution, truth storage |
| **Current Status** | ✅ OPERATIONAL (HTTP 200, contract_hash + SUM-SCRIPT) |
| **Canonical Version** | Render deployment (sl-validator-parity.onrender.com) |

---

## 4. Sarathi (Enforcement Gate)

| Field | Value |
|---|---|
| **Product Name** | Sarathi (Enforcement Gate) |
| **Module** | External — Rajaryan's enforcement service |
| **Owner** | Rajaryan |
| **Ecosystem Layer(s)** | Enforcement |
| **Runtime Role** | Cryptographic enforcement gate — validates execution approval, issues JWT tokens |
| **Upstream Dependencies** | BHIV Core (receives token + trace_id + cet_hash) |
| **Downstream Dependencies** | Bridge (consumes JWT via Core passthrough) |
| **API Endpoints** | POST /sarathi/enforce, GET /.well-known/jwks.json |
| **Authentication** | SHA-256 cryptographic binding (signature_hash = SHA-256 of `execution_id\|rajya_verdict\|timestamp`) |
| **Trace Participation** | ENRICHER — adds execution_id, embeds trace_id + cet_hash in JWT claims |
| **Replay Participation** | INDIRECT — enforcement signal + JWT recorded by Core in Bucket, jti prevents replay |
| **Health Endpoint** | GET / → service info |
| **Failure Behaviour** | Core FAIL-CLOSED — no enforcement = SarathiEnforcementError = execution blocked |
| **Authority Owned** | Cryptographic enforcement, JWT issuance (RS256), execution approval |
| **Authority NOT Owned** | Risk decisions (Sovereign), contract compilation (CET), JWT validation (Bridge), truth storage (Bucket) |
| **Current Status** | ✅ OPERATIONAL (HTTP 200, status=ALLOW, JWT RS256 issued) |
| **Canonical Version** | Render deployment with JWT (iss=tantra-sarathi, aud=tantra-bridge) |

---

## 5. Bridge (Execution Gate)

| Field | Value |
|---|---|
| **Product Name** | Bridge (Execution Gate) |
| **Module** | External — Ranjit's bridge-validator |
| **Owner** | Ranjit |
| **Ecosystem Layer(s)** | Enforcement |
| **Runtime Role** | JWT validation gate — verifies Sarathi-issued tokens, enforces continuity |
| **Upstream Dependencies** | BHIV Core (receives JWT + bridge_signature + X-Sarathi-* headers), Sarathi (JWKS for key verification) |
| **Downstream Dependencies** | Execution service (downstream of Bridge) |
| **API Endpoints** | POST /execute, GET /health |
| **Authentication** | JWT Bearer token (RS256 or EdDSA) with iss/aud validation |
| **Trace Participation** | VALIDATOR — cross-validates execution_id + trace_id + cet_hash from JWT, body, headers |
| **Replay Participation** | INDIRECT — validation status recorded by Core in Bucket |
| **Health Endpoint** | GET /health → `{"service":"bridge","status":"healthy","algorithms":["RS256","EdDSA"]}` |
| **Failure Behaviour** | Core FAIL-CLOSED — 401/403 = execution blocked |
| **Authority Owned** | JWT validation, continuity enforcement, execution gate |
| **Authority NOT Owned** | JWT issuance (Sarathi), risk decisions (Sovereign), truth storage (Bucket) |
| **Current Status** | ✅ OPERATIONAL (HTTP 200, status=completed) |
| **Canonical Version** | ngrok deployment (evoke-oboe-stilt.ngrok-free.dev) |

---

## 6. Bucket (Immutable Truth Store)

| Field | Value |
|---|---|
| **Product Name** | Bucket (Immutable Truth Store) |
| **Module** | External — Siddhesh's bhiv-bucket |
| **Owner** | Siddhesh |
| **Ecosystem Layer(s)** | Truth |
| **Runtime Role** | Append-only artifact storage with hash chain integrity |
| **Upstream Dependencies** | BHIV Core (receives execution artifacts) |
| **Downstream Dependencies** | None (terminal truth store) |
| **API Endpoints** | POST /bucket/artifact, GET /bucket/chain-state, GET /bucket/schema-info, POST /bucket/validate-replay, GET /bucket/certification |
| **Authentication** | Schema validation enforced (field-level) |
| **Trace Participation** | RECORDER — stores trace_id in payload, hash chain preserves execution order |
| **Replay Participation** | PRIMARY — POST /bucket/validate-replay, full artifact query, hash chain reconstruction |
| **Health Endpoint** | GET /health → health status |
| **Failure Behaviour** | Core FAIL-CLOSED — BucketWriteError = execution FAILED |
| **Authority Owned** | Immutable truth storage, hash chain integrity, append-only invariant, replay validation |
| **Authority NOT Owned** | Risk decisions, enforcement, JWT, execution, telemetry |
| **Current Status** | ✅ OPERATIONAL (HTTP 200, hash chain write, parent_hash linked) |
| **Canonical Version** | schema_version 1.0.0, Render (bhiv-bucket.onrender.com) |

---

## 7. InsightFlow (Telemetry & Dataset Registry)

| Field | Value |
|---|---|
| **Product Name** | InsightFlow (BHIV Intelligence Data Universe Registry) |
| **Module** | External — Vijay's dataset registry |
| **Owner** | Vijay |
| **Ecosystem Layer(s)** | Truth |
| **Runtime Role** | Federated dataset metadata registry — telemetry, provenance, discovery |
| **Upstream Dependencies** | BHIV Core (receives dataset metadata) |
| **Downstream Dependencies** | None (terminal telemetry store) |
| **API Endpoints** | POST /api/v1/datasets/, GET /api/v1/datasets/, GET /api/v1/datasets/{id}, PATCH /api/v1/datasets/{id}, POST /api/v1/schemas/, POST /api/v1/relationships/, GET /api/v1/discovery/summary, POST /api/v1/onboarding/submit, GET /api/v1/audit/logs |
| **Authentication** | X-API-Key header required |
| **Trace Participation** | RECORDER — trace_id stored in extended_metadata |
| **Replay Participation** | SECONDARY — metadata stored but not primary replay source |
| **Health Endpoint** | GET /health → `{"status":"healthy","version":"1.0.0"}` |
| **Failure Behaviour** | Core GRACEFUL-FALLBACK — local JSONL on failure (non-blocking) |
| **Authority Owned** | Dataset registry, telemetry, provenance tracking, discovery, onboarding, audit |
| **Authority NOT Owned** | Risk decisions, enforcement, JWT, execution, truth storage (Bucket) |
| **Current Status** | ✅ OPERATIONAL (HTTP 201, dataset ACTIVE) |
| **Canonical Version** | version 1.0.0, ngrok deployment |

---

## Future Participant Registration

New participants are added by:
1. Creating an entry in `TANTRA_INTEGRATION_REGISTRY.json` with all fields above
2. Implementing the required HTTP protocol (endpoint + schema)
3. Accepting `X-Trace-Id` header for trace continuity
4. Declaring failure mode (FAIL-CLOSED or GRACEFUL-FALLBACK)
5. No architectural redesign required — configuration-driven integration
