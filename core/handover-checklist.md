# BHIV Core Handover Checklist

## Overview
This document outlines the handover checklist for the BHIV Core system, detailing what has been delivered and what is expected from the receiving team.

## Completed Deliverables

### 1. Core Event Schema
- **File**: `core/schemas/core-event-spec.json`
- **Description**: JSON schema for case events
- **Status**: ✅ Completed
- **Validation**: Schema validates required fields (caseId, evidenceId, riskScore, actionSuggested)

### 2. Core Events API
- **File**: `core/events/core_events.py`
- **Endpoints**:
  - `POST /core/events` (accepts events with 202 response)
  - `GET /core/events/{core_event_id}` (gets event status)
  - `GET /core/case/{case_id}/status` (gets case reconciliation status)
- **Status**: ✅ Completed
- **Testing**: Unit tests included in `tests/test_core_events.py`

### 3. Orchestration Rules
- **File**: `core/orchestration/rules.py`
- **Rules Implemented**:
  - Auto-escalation for high risk scores (>= 80)
  - Auto-escalation for high-value transfers (>= $10,000)
  - Multisig trigger for freeze actions with high risk (>= 70)
  - Duplicate wallet detection across cases
- **Status**: ✅ Completed

### 4. Webhook Handler
- **File**: `core/events/webhooks.py`
- **Endpoints**:
  - `POST /callbacks/escalation-result` (handles escalation results)
  - `POST /callbacks/{callback_type}` (handles generic callbacks)
  - `GET /monitoring/events` (gets monitoring events)
  - `POST /monitoring/events` (logs monitoring events)
  - `POST /monitoring/replay/{event_id}` (replays failed events)
- **Status**: ✅ Completed

### 5. Main Orchestrator
- **File**: `core/orchestration/core_orchestrator.py`
- **Features**:
  - Event processing with rule application
  - Webhook callback handling
  - Event status retrieval
  - Monitoring event management
  - Failed event replay capability
- **Status**: ✅ Completed

## Handover Artifacts

### 1. Core Event Specification
- **File**: `core/schemas/core-event-spec.json`
- **Description**: Complete JSON schema for case events

### 2. Sample Orchestration Rules
- **File**: `core/orchestration/sample_rules.json`
- **Description**: Sample rules for auto-escalation, high-value transfers, freeze actions, and duplicate detection

### 3. Sample Webhook Callback
- **File**: `core/events/sample_callback.json`
- **Description**: Example webhook callback with authentication and payload structure

### 4. Monitoring Configuration
- **File**: `core/events/monitoring_config.json`
- **Description**: Monitoring endpoints and replay instructions

### 5. OpenAPI Specification
- **File**: `core/openapi.yaml`
- **Description**: Complete API contract for all core endpoints

### 6. Postman Collection
- **File**: `core/postman_collection.json`
- **Description**: Ready-to-use Postman collection for testing all endpoints

### 7. Docker Configuration
- **File**: `core/Dockerfile`
- **Description**: Dockerfile for containerizing the core service

### 8. Full Stack Docker Compose
- **File**: `docker-compose.fullstack.yml`
- **Description**: Docker Compose file for deploying the full BHIV stack

### 9. RBAC Permissions Matrix
- **File**: `core/rbac-permissions.json`
- **Description**: Role-based access control permissions for all core services

### 10. Data Schemas
- **Files**: 
  - `core/evidence-schema.json`
  - `core/case-schema.json`
  - `core/rl-outcome-schema.json`
  - `core/storage-metadataschema.json`
- **Description**: JSON schemas for all core data entities

### 11. Smart Contract Integration
- **Files**:
  - `core/contract-abi.json`
  - `core/contract-addresses.md`
- **Description**: Smart contract ABI and deployment addresses for all environments

### 12. Integration Runbook
- **File**: `core/integration-runbook.md`
- **Description**: Comprehensive guide for integrating with the BHIV Core system

## Integration/QA Plan

### Unit & Integration Testing
- Each module has 80%+ code coverage
- Tests are located in the `tests/` directory
- Run tests with: `python -m pytest tests/`

### Integration Smoke Tests
- Flag a wallet → create case → upload evidence → bucket returns pointer → anchor on chain → RL returns action → escalate → PDF generated
- Execute using the Postman collection

### E2E Acceptance
- QA team executes the Postman collection
- Pass = green, Fail = identified issues with clear reproduction steps

### Security Review
- Run Snyk/OWASP dependency checks
- Quick pentest checklist (auth, file upload size/type, rate limit bypass)

## Acceptance Checklist

### ✅ 1. OpenAPI validated
- `core/openapi.yaml` validates successfully
- Postman collection executes E2E in staging

### ✅ 2. Evidence flow works end-to-end
- Test with BHIV Bucket test credentials
- Upload → Store → Retrieve workflow verified

### ✅ 3. On-chain anchor writes
- Returns txHash and verify returns success on BHIV testnet

### ✅ 4. RL endpoints available
- RL endpoints functional
- RLLog shows admin feedback updates

### ✅ 5. RBAC enforced
- Middleware and UI enforce RBAC
- Tests show unauthorized access is denied

### ✅ 6. Kafka resilience
- Service stays up if Kafka is down
- Event processing continues with local queuing

### ✅ 7. Docker-compose up
- Staging deployment successful
- Health checks passing

### ✅ 8. Monitoring
- Logs, metrics, alerting implemented
- Basic CPU, error rate, queue depth monitoring

### ✅ 9. Documentation complete
- Runbook provided
- Monitoring dashboard links included
- Loom walkthrough created
- PDF sample for regulators generated

### ✅ 10. Humility/Gratitude/Honesty note
- Required note included in final PR

## Quick Handover Matrix

### Nisarg → Yashika
- **What**: Event topic format, sample events, required orchestration outcomes
- **Files**: `core/schemas/core-event-spec.json`, sample events in documentation

### Nisarg → Nikhil/Yash
- **What**: OpenAPI specification, Postman collection, mock tokens, sample RL responses
- **Files**: `core/openapi.yaml`, `core/postman_collection.json`

## Final Notes & Recommendations

### Integration Window
- Run a 2-hour "integration window" after Day 3
- Validate E2E and fix immediate contract mismatches
- Use mock server to unblock frontend if needed

### Source of Truth
- Keep `core/openapi.yaml` as the source of truth
- Any API change must update that file first

### PR Process
- Enforce PR humility/gratitude/honesty requirement
- Checks included in acceptance checklist