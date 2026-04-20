"""
Webhook Handler for BHIV Core System

This module handles webhook callbacks for orchestrated outcomes
and provides monitoring endpoints for failed event deliveries.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BHIV Core Webhooks",
    description="Webhook endpoints for orchestrated outcomes",
    version="1.0.0"
)

class WebhookPayload(BaseModel):
    """Payload for webhook callbacks"""
    outcomeId: str
    caseId: str
    eventType: str
    result: Dict[str, Any]
    timestamp: str

class WebhookResponse(BaseModel):
    """Response model for webhook acceptance"""
    status: str = "received"
    messageId: str

class MonitoringEvent(BaseModel):
    """Model for monitoring events"""
    eventId: str
    eventType: str
    status: str
    timestamp: str
    details: Optional[str] = None

# In-memory storage for webhook events and monitoring (in production, this would be a database)
webhook_events = []
monitoring_events = []

@app.post("/callbacks/escalation-result", response_model=WebhookResponse)
async def handle_escalation_result(payload: WebhookPayload):
    """
    Handle escalation result callbacks from orchestration.
    """
    try:
        # Generate message ID
        message_id = str(uuid.uuid4())
        
        # Store the webhook event
        event_data = {
            "messageId": message_id,
            "payload": payload.dict(),
            "receivedAt": datetime.now().isoformat()
        }
        webhook_events.append(event_data)
        
        logger.info(f"Received escalation result webhook: {payload}")
        
        # In a real implementation, process the escalation result here
        # For example, update case status, notify stakeholders, etc.
        
        return WebhookResponse(messageId=message_id)
    except Exception as e:
        logger.error(f"Error handling escalation result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )

@app.post("/callbacks/{callback_type}", response_model=WebhookResponse)
async def handle_generic_callback(callback_type: str, payload: WebhookPayload):
    """
    Handle generic callback events.
    """
    try:
        # Generate message ID
        message_id = str(uuid.uuid4())
        
        # Store the webhook event
        event_data = {
            "messageId": message_id,
            "callbackType": callback_type,
            "payload": payload.dict(),
            "receivedAt": datetime.now().isoformat()
        }
        webhook_events.append(event_data)
        
        logger.info(f"Received {callback_type} webhook: {payload}")
        
        return WebhookResponse(messageId=message_id)
    except Exception as e:
        logger.error(f"Error handling {callback_type} callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )

@app.get("/monitoring/events")
async def get_monitoring_events(event_type: Optional[str] = None):
    """
    Get monitoring events, optionally filtered by event type.
    """
    if event_type:
        filtered_events = [event for event in monitoring_events if event.get("eventType") == event_type]
        return filtered_events
    return monitoring_events

@app.post("/monitoring/events")
async def log_monitoring_event(event: MonitoringEvent):
    """
    Log a monitoring event.
    """
    monitoring_events.append(event.dict())
    logger.info(f"Logged monitoring event: {event}")
    return {"status": "logged"}

@app.post("/monitoring/replay/{event_id}")
async def replay_failed_event(event_id: str):
    """
    Replay a failed event delivery.
    """
    # Find the event in webhook events
    event_to_replay = None
    for event in webhook_events:
        if event.get("messageId") == event_id:
            event_to_replay = event
            break
    
    if not event_to_replay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # In a real implementation, we would replay the event to the original destination
    # For now, we'll just log that a replay was requested
    logger.info(f"Replay requested for event {event_id}")
    
    # Log this as a monitoring event
    monitoring_event = {
        "eventId": str(uuid.uuid4()),
        "eventType": "replay",
        "status": "initiated",
        "timestamp": datetime.now().isoformat(),
        "details": f"Replay initiated for event {event_id}"
    }
    monitoring_events.append(monitoring_event)
    
    return {
        "status": "replay_initiated",
        "eventId": event_id,
        "monitoringEventId": monitoring_event["eventId"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "BHIV Core Webhooks",
        "version": "1.0.0",
        "webhook_events_count": len(webhook_events),
        "monitoring_events_count": len(monitoring_events)
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="BHIV Core Webhooks")
    parser.add_argument("--port", type=int, default=8005, help="Port to run the server on (default: 8005)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  BHIV CORE WEBHOOKS")
    print("="*60)
    print(f" Server URL: http://{args.host}:{args.port}")
    print(f" API Documentation: http://{args.host}:{args.port}/docs")
    print("\n Endpoints:")
    print("   POST /callbacks/escalation-result - Handle escalation results")
    print("   POST /callbacks/{callback_type} - Handle generic callbacks")
    print("   GET /monitoring/events - Get monitoring events")
    print("   POST /monitoring/events - Log monitoring events")
    print("   POST /monitoring/replay/{event_id} - Replay failed events")
    print("   GET /health - Health check")
    print("="*60)
    
    uvicorn.run(app, host=args.host, port=args.port)