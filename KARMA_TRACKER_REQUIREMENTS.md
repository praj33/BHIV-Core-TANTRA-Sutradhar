# Karma Tracker Service Requirements

This document outlines the requirements for the Karma Tracker service that BHIV Core will integrate with.

## API Endpoints

### 1. Update Karma
```
POST /update_karma
```

**Request Body:**
```json
{
  "user_id": "string",
  "action_type": "string",
  "value": "number"
}
```

**Response:**
```json
{
  "user_id": "string",
  "karma_score": "number",
  "last_update": "ISO timestamp",
  "source_action": "string"
}
```

### 2. Get Karma
```
GET /get_karma?user_id={user_id}
```

**Response:**
```json
{
  "user_id": "string",
  "karma_score": "number",
  "last_update": "ISO timestamp",
  "source_action": "string"
}
```

## Expected Action Types

1. `learning_task_completed` - User completes a learning task
2. `suggestion_provided` - Agent provides a suggestion
3. `task_skipped` - User skips a task (negative karma)
4. `voice_interaction` - User interacts via voice interface
5. `agent_suggestion_provided` - Agent provides personalized suggestion

## Response Format

All responses should follow this format:
```json
{
  "user_id": "string",
  "karma_score": "number",
  "last_update": "ISO timestamp",
  "source_action": "string"
}
```

## Event Propagation

The Karma Tracker should emit events for consumption by the Bucket service:

**Event Format:**
```json
{
  "event_id": "uuid",
  "event_type": "karma_updated",
  "timestamp": "ISO timestamp",
  "payload": {
    "user_id": "string",
    "karma_score": "number",
    "source_action": "string",
    "updated_at": "ISO timestamp"
  }
}
```

## Error Handling

The API should return appropriate HTTP status codes:
- 200: Success
- 400: Bad Request (invalid input)
- 404: User not found
- 500: Internal server error

## Validation Requirements

1. User ID must be a non-empty string
2. Action type must be one of the predefined types
3. Value must be a number (can be negative)
4. All required fields must be present

## Sample Test Users

For integration testing, seed the following users:
1. `test_user_001`
2. `workflow_user_001`
3. `default_user`

## Technology Recommendations

The Karma Tracker service can be implemented using:
- FastAPI (Python) - for consistency with BHIV Core
- MongoDB - for storing karma data
- Redis/RabbitMQ - for event propagation to Bucket service

## Environment Configuration

The service should listen on:
- Host: localhost
- Port: 8005

## Integration Validation

To validate the integration, the Karma Tracker should:
1. Accept requests from BHIV Core
2. Update karma scores correctly
3. Return proper response formats
4. Emit events for Bucket consumption
5. Handle errors gracefully

This specification should be sufficient for Siddhesh to implement the Karma Tracker service.