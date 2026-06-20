# Participant Runtime Catalog — Phase IV Final

Version: 3.0.0
Date: 2026-06-20
Status: ✅ All 7 participants verified operational

---

## 1. BHIV Core

| Field | Value |
|---|---|
| **Owner** | Raj Prajapati |
| **Purpose** | Runtime backbone — orchestrates the 8-step TANTRA execution chain |
| **URL** | localhost:8003 (cloud deployment pending) |
| **Inputs** | User requests, text input |
| **Outputs** | Trace signals, execution results, Bucket artifacts, InsightFlow datasets |
| **Current Status** | ✅ OPERATIONAL |
| **Integration Status** | ✅ 8/8 chain SUCCESS |
| **Trace Requirements** | Generates uuid4 trace_id, propagates via X-Trace-Id header |
| **Evidence Requirements** | Full chain proof in logs/full_tantra_v4_final_proof.json |
| **Auth** | Accepts Sarathi JWT, forwards to Bridge |
| **Failure Mode** | FAIL-CLOSED on governance (Sovereign, Sarathi, Bucket). GRACEFUL-FALLBACK on InsightFlow. |

---

## 2. Sovereign

| Field | Value |
|---|---|
| **Owner** | Aakanksha (via Rajaryan's service) |
| **Purpose** | Risk assessment — determines ALLOW/DENY based on content analysis |
| **URL** | https://text-risk-scoring-service.onrender.com/analyze |
| **Inputs** | `{"text": "..."}` + X-Trace-Id header |
| **Outputs** | `{"risk_category": "LOW", "risk_score": 0.0, "decision": "ALLOW"}` |
| **Current Status** | ✅ OPERATIONAL (HTTP 200) |
| **Integration Status** | ✅ VERIFIED |
| **Trace Requirements** | Receives X-Trace-Id, decision recorded in Bucket |
| **Evidence Requirements** | decision_hash = SHA-256 of response |
| **Auth** | None (open endpoint) |
| **Failure Mode** | Core FAIL-CLOSED — unreachable = execution blocked |

---

## 3. CET (Compliance Execution Transpiler)

| Field | Value |
|---|---|
| **Owner** | Tanvi |
| **Purpose** | Compiles KSML decision objects into executable SUM-SCRIPTs with constraint validation |
| **URL** | https://sl-validator-parity.onrender.com/cet/compile |
| **Inputs** | KSML object: `{trace_id, input: {decision_id, trace_id, intent, actors, constraints, context, timestamp}}` |
| **Outputs** | `{"contract_hash": "...", "sum_script": {...}}` |
| **Current Status** | ✅ OPERATIONAL (HTTP 200) |
| **Integration Status** | ✅ VERIFIED |
| **Schema** | actors = dict of named objects, constraints = [{left, operator, right}], intent = "TransferFunds" |
| **Trace Requirements** | trace_id in payload, contract_hash recorded in Bucket |
| **Evidence Requirements** | contract_hash (SHA-256 of compiled contract) |
| **Auth** | None |
| **Failure Mode** | Core FAIL-CLOSED or internal fallback hash |

---

## 4. Sarathi (Enforcement Gate)

| Field | Value |
|---|---|
| **Owner** | Rajaryan |
| **Purpose** | Cryptographic enforcement gate — validates execution approval and issues JWT tokens |
| **URL** | https://text-risk-scoring-service.onrender.com/sarathi/enforce |
| **Inputs** | `{token: {execution_id, rajya_verdict, token_status, timestamp, signature_hash}, pipeline_execution_id, trace_id, cet_hash}` |
| **Outputs** | `{"status": "ALLOW", "jwt": "eyJhbG..."}` |
| **Current Status** | ✅ OPERATIONAL (HTTP 200 + JWT) |
| **Integration Status** | ✅ VERIFIED |
| **Signature** | signature_hash = SHA-256 of `execution_id\|rajya_verdict\|timestamp` |
| **JWT** | RS256, kid=sarathi-key-001, iss=tantra-sarathi, aud=tantra-bridge |
| **JWKS** | https://text-risk-scoring-service.onrender.com/.well-known/jwks.json |
| **Trace Requirements** | execution_id + trace_id + cet_hash embedded in JWT claims |
| **Evidence Requirements** | JWT with jti for replay prevention |
| **Auth** | SHA-256 cryptographic binding |
| **Failure Mode** | Core FAIL-CLOSED — no token = no execution |

---

## 5. Bridge (Execution Gate)

| Field | Value |
|---|---|
| **Owner** | Ranjit |
| **Purpose** | JWT validation gate — verifies Sarathi-issued tokens and enforces continuity |
| **URL** | https://evoke-oboe-stilt.ngrok-free.dev/execute |
| **Inputs** | Body: `{trace_id, execution_id, execution_token, contract_hash, cet_hash, bridge_signature, timestamp}` Headers: `Authorization: Bearer <JWT>`, `X-Sarathi-*` |
| **Outputs** | `{"trace_id": "...", "execution_id": "...", "status": "completed", "result": {...}}` |
| **Current Status** | ✅ OPERATIONAL (HTTP 200) |
| **Integration Status** | ✅ VERIFIED |
| **JWT Validation** | RS256/EdDSA via JWKS, kid resolution, iss/aud enforcement |
| **Continuity** | execution_id + trace_id + cet_hash validated across JWT claims, body, and X-Sarathi-* headers |
| **bridge_signature** | SHA-256 of `trace_id\|execution_id\|contract_hash` |
| **Health** | GET /health → `{"service":"bridge","status":"healthy","algorithms":["RS256","EdDSA"]}` |
| **Auth** | JWT Bearer token (RS256 or EdDSA) |
| **Failure Mode** | Core FAIL-CLOSED — rejection = execution blocked |

---

## 6. Bucket (Immutable Truth Store)

| Field | Value |
|---|---|
| **Owner** | Siddhesh |
| **Purpose** | Append-only artifact storage with hash chain integrity |
| **URL** | https://bhiv-bucket.onrender.com/bucket/artifact |
| **Inputs** | `{artifact_id, artifact_type, timestamp_utc, schema_version, source_module_id, parent_hash, payload}` |
| **Outputs** | `{"hash": "...", "storage_type": "append_only"}` |
| **Current Status** | ✅ OPERATIONAL (HTTP 200) |
| **Integration Status** | ✅ VERIFIED |
| **Chain State** | GET /bucket/chain-state → `{last_hash, artifact_count}` |
| **Integrity** | parent_hash required (chain-linked), append-only invariant |
| **Trace Requirements** | trace_id stored in payload, hash chain preserves order |
| **Evidence Requirements** | Artifact hash (SHA-256) |
| **Auth** | Schema validation enforced |
| **Failure Mode** | Core FAIL-CLOSED — BucketWriteError = execution FAILED |

---

## 7. InsightFlow (Telemetry & Dataset Registry)

| Field | Value |
|---|---|
| **Owner** | Vijay |
| **Purpose** | Federated dataset metadata registry — telemetry, provenance, discovery |
| **URL** | https://04d1-152-59-6-179.ngrok-free.app/api/v1/datasets/ |
| **Inputs** | `{canonical_id, dataset_name, description, owner_name, owner_team, domain_primary, source_system, domain_tags, extended_metadata}` |
| **Outputs** | `{"id": "uuid", "status": "ACTIVE", "canonical_id": "..."}` |
| **Current Status** | ✅ OPERATIONAL (HTTP 201) |
| **Integration Status** | ✅ VERIFIED |
| **API Surface** | Datasets CRUD, Schemas, Relationships, Provenance, Discovery, Onboarding, Audit |
| **Trace Requirements** | trace_id in extended_metadata |
| **Evidence Requirements** | Dataset ID + canonical_id |
| **Auth** | X-API-Key header required |
| **Failure Mode** | Core GRACEFUL-FALLBACK — local JSONL on failure |
