# Canonical Runtime Sequence — Phase IV

Version: 1.0.0
Date: 2026-06-19

---

## Full TANTRA Runtime Execution Sequence

```
User
  ↓
Application (Product Layer)
  ↓
BHIV Core (Orchestration Layer)
  ↓
Sovereign (Governance — Decision)
  ↓
CET (Governance — Contract)
  ↓
Sarathi (Governance — Enforcement)
  ↓
Bridge (Governance — Validation)
  ↓
Execution (Agent Layer)
  ↓
Bucket (Infrastructure — Truth)
  ↓
InsightFlow (Observability — Telemetry)
  ↓
Replay (Reconstruction)
  ↓
Operations Dashboard (Monitoring)
  ↓
Human Review (Governance)
```

---

## Transition Details

### Transition 1: User → Application

| Field | Value |
|---|---|
| **Input** | User query, action, or request |
| **Output** | Structured request payload |
| **Protocol** | HTTP / WebSocket / Event |
| **Validation** | Product-level input validation |
| **Failure Handling** | Product returns user-facing error |
| **Trace Continuation** | No trace_id yet — product may create session_id |
| **Authority Boundary** | Product owns UX and input formatting |

### Transition 2: Application → BHIV Core

| Field | Value |
|---|---|
| **Input** | `{agent, input, input_type, tags, execution_token, trace_id}` |
| **Output** | `{task_id, agent_output, status, trace_id, bucket_write}` |
| **Protocol** | HTTP POST /execute_task |
| **Validation** | execution_token and trace_id MUST be present → 403 if missing |
| **Failure Handling** | Core returns HTTP 403/500 with structured error |
| **Trace Continuation** | trace_id GENERATED here (uuid4). This is the trace origin. |
| **Authority Boundary** | Core owns trace_id generation, agent routing, execution gating |

### Transition 3: BHIV Core → Sovereign

| Field | Value |
|---|---|
| **Input** | `{text: "input to evaluate"}` |
| **Output** | `{risk_score, risk_category, confidence_score}` |
| **Protocol** | HTTP POST /analyze with X-Trace-Id header |
| **Validation** | Response must contain risk_category. Core maps: LOW/MEDIUM→ALLOW, HIGH/CRITICAL→DENY |
| **Failure Handling** | FAIL-CLOSED — ConnectionError raised, execution aborted |
| **Trace Continuation** | X-Trace-Id header propagated. decision_hash computed from response. |
| **Authority Boundary** | Sovereign owns risk scoring. Core owns decision mapping. |

### Transition 4: BHIV Core → CET

| Field | Value |
|---|---|
| **Input** | `{trace_id, input, decision_hash, timestamp}` |
| **Output** | `{contract_hash, compiled_contract}` |
| **Protocol** | HTTP POST /cet/compile with X-Trace-Id header |
| **Validation** | Response must contain contract_hash |
| **Failure Handling** | FAIL-CLOSED (USE_FULL_TANTRA=true) or internal hash fallback |
| **Trace Continuation** | trace_id in payload and X-Trace-Id header |
| **Authority Boundary** | CET owns contract compilation. Core provides inputs. |

### Transition 5: BHIV Core → Sarathi

| Field | Value |
|---|---|
| **Input** | `{trace_id, decision, execution_payload, decision_hash}` |
| **Output** | `{status: CLEARED/BLOCKED, execution_token, validation_result}` |
| **Protocol** | HTTP POST /sarathi/enforce with X-Trace-Id header |
| **Validation** | status must be CLEARED. BLOCKED = SarathiEnforcementError |
| **Failure Handling** | FAIL-CLOSED — no token = no execution |
| **Trace Continuation** | X-Trace-Id header. decision_hash verified. execution_token issued. |
| **Authority Boundary** | Sarathi owns enforcement policy and token issuance. Core cannot issue tokens. |

### Transition 6: BHIV Core → Bridge

| Field | Value |
|---|---|
| **Input** | `{trace_id, execution_token, contract_hash, timestamp}` |
| **Output** | `{validation_status: VALIDATED/REJECTED}` |
| **Protocol** | HTTP POST /execute with X-Trace-Id + ngrok-skip-browser-warning headers |
| **Validation** | VALIDATED = proceed. REJECTED = BridgeError |
| **Failure Handling** | FAIL-CLOSED (USE_FULL_TANTRA=true) or internal validation |
| **Trace Continuation** | X-Trace-Id header and trace_id in payload |
| **Authority Boundary** | Bridge owns validation gate logic. Core provides credentials. |

### Transition 7: BHIV Core → Execution

| Field | Value |
|---|---|
| **Input** | `{agent, input, input_type, tags}` via gated_execute |
| **Output** | `{task_id, agent_output, status}` |
| **Protocol** | Internal Python call (execute_task) |
| **Validation** | Token validated by gated_execute. Replay prevention checked. |
| **Failure Handling** | ExecutionBlockedError if token invalid/replayed |
| **Trace Continuation** | trace_id passed through to agent context |
| **Authority Boundary** | Agent owns domain execution. Core owns gating. |

### Transition 8: BHIV Core → Bucket

| Field | Value |
|---|---|
| **Input** | `{artifact_id, artifact_type, timestamp_utc, schema_version, source_module_id, payload}` |
| **Output** | `{hash, parent_hash, storage_type, artifact_id, timestamp}` |
| **Protocol** | HTTP POST /bucket/artifact |
| **Validation** | Bucket validates envelope structure (not content). Missing fields = 400. |
| **Failure Handling** | FAIL-CLOSED — BucketWriteError = execution marked FAILED |
| **Trace Continuation** | trace_id inside payload. Hash chain extends. |
| **Authority Boundary** | Bucket owns truth storage schema. Core provides payload. |

### Transition 9: BHIV Core → InsightFlow

| Field | Value |
|---|---|
| **Input** | `{canonical_id, dataset_name, owner_name, domain_primary, source_system, tags, metadata}` |
| **Output** | `{id, canonical_id, status, registered_at}` |
| **Protocol** | HTTP POST /api/v1/datasets/ with X-API-Key header |
| **Validation** | canonical_id must follow BHIV-DS-DOMAIN-NAME-XXX pattern |
| **Failure Handling** | GRACEFUL-FALLBACK — only non-blocking participant. Falls back to local JSONL. |
| **Trace Continuation** | trace_id inside metadata |
| **Authority Boundary** | InsightFlow owns dataset registration schema. Core provides trace data. |

### Transition 10: InsightFlow → Replay

| Field | Value |
|---|---|
| **Input** | `trace_id` |
| **Output** | Reconstructed execution lineage (all signals, all writes) |
| **Protocol** | HTTP GET /trace/{trace_id} on Core |
| **Validation** | Aggregates from Bucket, InsightFlow, local logs |
| **Failure Handling** | 404 if trace_id not found in any source |
| **Trace Continuation** | Final reconstruction — all trace signals aggregated |
| **Authority Boundary** | Core owns replay reconstruction. Bucket is primary source. InsightFlow is secondary. |

### Transition 11: Replay → Operations Dashboard

| Field | Value |
|---|---|
| **Input** | Reconstructed trace data |
| **Output** | Visual dashboard, alerts, SLA metrics |
| **Protocol** | HTTP / WebSocket (future) |
| **Validation** | Dashboard validates trace completeness |
| **Failure Handling** | Dashboard offline = no user impact (data preserved in Bucket) |
| **Trace Continuation** | Read-only — no trace modification |
| **Authority Boundary** | Dashboard owns visualization. Core owns data. |

### Transition 12: Operations Dashboard → Human Review

| Field | Value |
|---|---|
| **Input** | Dashboard alerts, trace anomalies, governance flags |
| **Output** | Human decision (approve, investigate, escalate) |
| **Protocol** | UI interaction |
| **Validation** | Human judgment |
| **Failure Handling** | Escalation to governance team |
| **Trace Continuation** | Human review decision recorded in Bucket (future) |
| **Authority Boundary** | Human owns final judgment. System provides evidence. |
