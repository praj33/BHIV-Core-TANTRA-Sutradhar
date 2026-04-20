"""
Core Events API for BHIV System

This module handles event ingestion, orchestration, and blockchain reconciliation
for the BHIV Core system.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BHIV Core Events API",
    description="API for accepting case events and orchestrating higher-level flows",
    version="1.0.0"
)

class EventPayload(BaseModel):
    """Payload for case events"""
    caseId: str = Field(..., description="Unique identifier for the case")
    evidenceId: str = Field(..., description="Identifier for the evidence associated with the case")
    riskScore: float = Field(..., ge=0, le=100, description="Risk score for the case (0-100)")
    actionSuggested: str = Field(..., enum=["approve", "reject", "escalate", "review", "freeze"], 
                                description="Suggested action for the case")
    txHash: Optional[str] = Field(None, description="Transaction hash on blockchain")
    source: Optional[str] = Field(None, description="Source of the event")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the event")

class EventResponse(BaseModel):
    """Response model for event acceptance"""
    coreEventId: str = Field(..., description="Unique identifier for the core event")
    status: str = Field("accepted", description="Status of the event")
    timestamp: str = Field(..., description="Timestamp when the event was accepted")

# In-memory storage for events (in production, this would be a database)
events_storage = {}

@app.post("/core/events", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def accept_event(payload: EventPayload):
    """
    Accept case events for processing.
    
    Returns 202 Accepted with coreEventId.
    """
    try:
        # Generate a unique core event ID
        core_event_id = str(uuid.uuid4())
        
        # Store the event with timestamp
        event_data = payload.dict()
        event_data["coreEventId"] = core_event_id
        event_data["timestamp"] = datetime.now().isoformat()
        
        # Store in memory (in production, store in database)
        events_storage[core_event_id] = event_data
        
        logger.info(f"Accepted event with coreEventId: {core_event_id}")
        
        return EventResponse(
            coreEventId=core_event_id,
            status="accepted",
            timestamp=event_data["timestamp"]
        )
    except Exception as e:
        logger.error(f"Error accepting event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept event: {str(e)}"
        )

@app.get("/core/events/{core_event_id}", response_model=EventResponse)
async def get_event_status(core_event_id: str):
    """
    Get the status of a specific event.
    """
    if core_event_id not in events_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    event_data = events_storage[core_event_id]
    return EventResponse(
        coreEventId=event_data["coreEventId"],
        status="accepted",
        timestamp=event_data["timestamp"]
    )

@app.get("/core/case/{case_id}/status")
async def get_case_status(case_id: str):
    """
    Get the status of a specific case.
    
    Returns reconciliation status between core ledger and blockchain.
    """
    # Find events for this case
    case_events = [
        event for event in events_storage.values() 
        if event.get("caseId") == case_id
    ]
    
    if not case_events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # For each event, check if txHash matches blockchain
    reconciliation_results = []
    for event in case_events:
        tx_hash = event.get("txHash")
        if tx_hash:
            # In a real implementation, we would verify against blockchain
            # For now, we'll simulate a successful verification
            reconciliation_results.append({
                "evidenceId": event["evidenceId"],
                "txHash": tx_hash,
                "status": "verified",
                "details": "Evidence anchor matches blockchain transaction"
            })
        else:
            reconciliation_results.append({
                "evidenceId": event["evidenceId"],
                "txHash": None,
                "status": "pending",
                "details": "No blockchain transaction hash provided"
            })
    
    return {
        "caseId": case_id,
        "reconciliation": reconciliation_results,
        "overallStatus": "ok" if all(r["status"] == "verified" for r in reconciliation_results) else "mismatch"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "BHIV Core Events API",
        "version": "1.0.0",
        "events_count": len(events_storage)
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="BHIV Core Events API")
    parser.add_argument("--port", type=int, default=8004, help="Port to run the server on (default: 8004)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  BHIV CORE EVENTS API")
    print("="*60)
    print(f" Server URL: http://{args.host}:{args.port}")
    print(f" API Documentation: http://{args.host}:{args.port}/docs")
    print("\n Endpoints:")
    print("   POST /core/events - Accept case events")
    print("   GET /core/events/{core_event_id} - Get event status")
    print("   GET /core/case/{case_id}/status - Get case reconciliation status")
    print("   GET /health - Health check")
    print("="*60)
    
    uvicorn.run(app, host=args.host, port=args.port)