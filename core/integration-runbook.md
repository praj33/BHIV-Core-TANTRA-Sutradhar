# BHIV Core Integration Runbook

## Overview
This document provides instructions for integrating with the BHIV Core system, including API endpoints, authentication, and example requests.

## Prerequisites
- Python 3.9+
- FastAPI
- Docker (for containerized deployment)
- Access to MongoDB and Qdrant services

## API Endpoints

### Core Events API (Port 8004)
- `POST /core/events` - Accept case events
- `GET /core/events/{core_event_id}` - Get event status
- `GET /core/case/{case_id}/status` - Get case reconciliation status
- `GET /health` - Health check

### Webhooks API (Port 8005)
- `POST /callbacks/escalation-result` - Handle escalation results
- `POST /callbacks/{callback_type}` - Handle generic callbacks
- `GET /monitoring/events` - Get monitoring events
- `POST /monitoring/events` - Log monitoring events
- `POST /monitoring/replay/{event_id}` - Replay failed events
- `GET /health` - Health check

## Authentication
All API endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <your-auth-token>
```

## Example Requests

### Accept a Case Event
```bash
curl -X POST http://localhost:8004/core/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-auth-token" \
  -d '{
    "caseId": "case-12345",
    "evidenceId": "evidence-67890",
    "riskScore": 85.5,
    "actionSuggested": "escalate",
    "txHash": "0x123456789abcdef",
    "source": "backend-service",
    "metadata": {
      "walletAddress": "0xabcdef123456789",
      "amount": 15000,
      "currency": "USD"
    }
  }'
```

### Get Event Status
```bash
curl -X GET http://localhost:8004/core/events/event-12345 \
  -H "Authorization: Bearer your-auth-token"
```

### Get Case Status
```bash
curl -X GET http://localhost:8004/core/case/case-12345/status \
  -H "Authorization: Bearer your-auth-token"
```

### Send Escalation Result Callback
```bash
curl -X POST http://localhost:8005/callbacks/escalation-result \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-auth-token" \
  -d '{
    "outcomeId": "outcome-12345",
    "caseId": "case-67890",
    "eventType": "escalation_completed",
    "result": {
      "status": "approved",
      "decision": "Escalation approved by risk team",
      "assignedTo": "analyst-001",
      "nextSteps": ["investigate_further", "contact_customer"]
    },
    "timestamp": "2025-10-06T10:30:00Z"
  }'
```

## Health Checks
```bash
# Core Events API health check
curl -X GET http://localhost:8004/health

# Webhooks API health check
curl -X GET http://localhost:8005/health
```

## Docker Deployment
To deploy the full stack using Docker Compose:

```bash
docker-compose -f docker-compose.fullstack.yml up -d
```

## Environment Variables
The following environment variables can be configured:

- `MONGO_URI` - MongoDB connection string
- `QDRANT_HOST` - Qdrant service host
- `AUTH_TOKEN` - Authentication token for API access
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Monitoring and Logging
- Logs are written to the `logs/` directory
- Monitoring events can be viewed at `GET /monitoring/events`
- Failed event deliveries can be replayed using `POST /monitoring/replay/{event_id}`

## Troubleshooting
1. If endpoints return 401 errors, check your authentication token
2. If services fail to start, verify that MongoDB and Qdrant are running
3. For webhook delivery issues, check the monitoring events endpoint
4. For high-risk cases not escalating, verify the orchestration rules configuration