# BHIV Core System

## Overview
The BHIV Core system is responsible for event ingestion, orchestration, and blockchain reconciliation. It accepts case events, applies orchestration rules, and coordinates with other system components.

## Components

### Core Events API
Handles event ingestion and status queries.
- **Port**: 8004
- **Main File**: `core/events/core_events.py`

### Webhooks API
Handles callback events and monitoring.
- **Port**: 8005
- **Main File**: `core/events/webhooks.py`

### Orchestration Engine
Applies business rules to events.
- **Main File**: `core/orchestration/core_orchestrator.py`
- **Rules**: `core/orchestration/rules.py`

## Key Features

1. **Event Ingestion**: Accepts case events via REST API
2. **Orchestration**: Applies rules for auto-escalation, duplicate detection, and multisig triggers
3. **Webhook Handling**: Receives and processes callback events
4. **Monitoring**: Tracks system health and event processing
5. **Reconciliation**: Verifies blockchain anchoring of evidence

## API Documentation

### Core Events Endpoints
- `POST /core/events` - Accept case events
- `GET /core/events/{core_event_id}` - Get event status
- `GET /core/case/{case_id}/status` - Get case reconciliation status
- `GET /health` - Health check

### Webhooks Endpoints
- `POST /callbacks/escalation-result` - Handle escalation results
- `POST /callbacks/{callback_type}` - Handle generic callbacks
- `GET /monitoring/events` - Get monitoring events
- `POST /monitoring/events` - Log monitoring events
- `POST /monitoring/replay/{event_id}` - Replay failed events
- `GET /health` - Health check

## Deployment

### Docker
```bash
docker-compose -f docker-compose.fullstack.yml up -d
```

### Manual
```bash
# Start Core Events API
python core/events/core_events.py --port 8004

# Start Webhooks API
python core/events/webhooks.py --port 8005
```

## Testing
Run the test script to verify functionality:
```bash
python core/test_core_functionality.py
```

## Configuration
The system can be configured using environment variables:
- `MONGO_URI` - MongoDB connection string
- `QDRANT_HOST` - Qdrant service host
- `AUTH_TOKEN` - Authentication token for API access
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Handover Artifacts
All handover artifacts are located in the `core/` directory:
- Schemas: `core/schemas/`
- Orchestration rules: `core/orchestration/sample_rules.json`
- API contracts: `core/openapi.yaml`
- Postman collection: `core/postman_collection.json`
- Docker configuration: `core/Dockerfile`
- RBAC permissions: `core/rbac-permissions.json`
- Data schemas: `core/*-schema.json`
- Smart contract: `core/contract-abi.json`
- Documentation: `core/integration-runbook.md`
- Checklist: `core/handover-checklist.md`