"""
Core API for BHIV System

This module provides API endpoints for the core orchestration layer,
allowing external systems to interact with the BHIV agent system.

ENFORCEMENT: All execution requires execution_token from Sarathi.
No token = 403. No bypass. No fallback.
"""

import hashlib
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from orchestration.core_orchestrator import execute_task, execute_sequence
from utils.logger import get_logger
from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.trace.time_sync import get_normalized_timestamp
from core.authority import callSovereign, callSarathi
from core.authority.execution_gate import (
    register_token, gated_execute, get_execution_record,
    ExecutionBlockedError,
)
from core.authority.bucket_writer import append_to_bucket, BucketWriteError
from core.trace.middleware import TraceMiddleware

logger = get_logger(__name__)

app = FastAPI(
    title="BHIV Core API",
    description="API for the BHIV Core Orchestration Layer",
    version="1.0.0"
)

# X-Trace-Id propagation middleware
app.add_middleware(TraceMiddleware)

class TaskPayload(BaseModel):
    """Payload for executing a single task."""
    input: str
    agent: Optional[str] = None
    task_id: Optional[str] = None
    input_type: Optional[str] = "text"
    tags: Optional[List[str]] = []
    retries: Optional[int] = 3
    fallback_agent: Optional[str] = "edumentor_agent"
    execution_token: Optional[str] = None  # REQUIRED for execution
    trace_id: Optional[str] = None  # REQUIRED for execution

class TaskSequencePayload(BaseModel):
    """Payload for executing a sequence of tasks."""
    tasks: List[TaskPayload]
    execution_token: Optional[str] = None  # REQUIRED for execution
    trace_id: Optional[str] = None  # REQUIRED for execution

class TaskResponse(BaseModel):
    """Response model for task execution."""
    task_id: str
    agent_output: Dict[str, Any]
    status: str
    trace_id: Optional[str] = None
    bucket_write: Optional[str] = None

class SequenceResponse(BaseModel):
    """Response model for sequence execution."""
    results: List[TaskResponse]
    trace_id: Optional[str] = None

@app.post("/execute_task", response_model=TaskResponse)
async def execute_single_task(payload: TaskPayload):
    """
    Execute a single task using the core orchestrator.
    REQUIRES execution_token and trace_id. No token = 403.
    """
    # ENFORCEMENT: token and trace_id are mandatory
    if not payload.execution_token or not payload.trace_id:
        raise HTTPException(
            status_code=403,
            detail="EXECUTION BLOCKED: execution_token and trace_id are required. "
                   "Obtain token via Sarathi enforcement."
        )

    try:
        logger.info(f"Received task execution request: trace_id={payload.trace_id}")

        # GATED EXECUTION: validate token, then execute
        register_token(payload.execution_token, payload.trace_id)
        result = gated_execute(
            execute_task,
            payload.execution_token,
            payload.trace_id,
            payload.dict(),
        )

        # BUCKET WRITE: record truth (fail-closed)
        task_id = result.get("task_id", str(uuid.uuid4()))
        event = get_execution_record(
            trace_id=payload.trace_id,
            execution_id=task_id,
            token=payload.execution_token,
            decision="ALLOW",
            payload=payload.dict(),
        )
        bucket_result = append_to_bucket(event)

        return TaskResponse(
            task_id=task_id,
            agent_output=result.get("agent_output", result),
            status=result.get("status", "success"),
            trace_id=payload.trace_id,
            bucket_write=bucket_result.get("status", "unknown"),
        )

    except ExecutionBlockedError as e:
        logger.error(f"EXECUTION BLOCKED: {str(e)}")
        raise HTTPException(status_code=403, detail=str(e))
    except BucketWriteError as e:
        logger.error(f"BUCKET WRITE FAILED: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Execution incomplete: {str(e)}")
    except Exception as e:
        logger.error(f"Error executing task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute_sequence", response_model=SequenceResponse)
async def execute_task_sequence(payload: TaskSequencePayload):
    """
    Execute a sequence of tasks using the core orchestrator.
    REQUIRES execution_token and trace_id. No token = 403.
    """
    # ENFORCEMENT: token and trace_id are mandatory
    if not payload.execution_token or not payload.trace_id:
        raise HTTPException(
            status_code=403,
            detail="EXECUTION BLOCKED: execution_token and trace_id are required."
        )

    try:
        logger.info(f"Received sequence request: trace_id={payload.trace_id}")

        register_token(payload.execution_token, payload.trace_id)
        task_list = [task.dict() for task in payload.tasks]
        results = gated_execute(
            execute_sequence,
            payload.execution_token,
            payload.trace_id,
            task_list,
        )

        # BUCKET WRITE for sequence
        event = get_execution_record(
            trace_id=payload.trace_id,
            execution_id=f"seq-{payload.trace_id[:8]}",
            token=payload.execution_token,
            decision="ALLOW",
            payload={"task_count": len(task_list)},
        )
        bucket_result = append_to_bucket(event)

        return SequenceResponse(
            results=[TaskResponse(**r) for r in results],
            trace_id=payload.trace_id,
        )

    except ExecutionBlockedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except BucketWriteError as e:
        raise HTTPException(status_code=500, detail=f"Execution incomplete: {str(e)}")
    except Exception as e:
        logger.error(f"Error executing sequence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "BHIV Core API",
        "version": "1.0.0"
    }

@app.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """
    Reconstruct full execution lineage from a single trace_id.
    Searches Bucket, InsightFlow, and replay logs.
    """
    from core.trace.trace_replay import reconstruct_trace
    result = reconstruct_trace(trace_id)
    if result["status"] == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    return result

@app.get("/traces")
async def list_traces():
    """List all known trace_ids and their summary."""
    from core.trace.trace_replay import reconstruct_all_traces
    return {"traces": reconstruct_all_traces()}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "BHIV Core API",
        "version": "1.0.0",
        "endpoints": {
            "execute_task": "POST /execute_task - Execute a single task",
            "execute_sequence": "POST /execute_sequence - Execute a sequence of tasks",
            "health": "GET /health - Health check",
            "trace": "GET /trace/{trace_id} - Reconstruct execution lineage",
            "traces": "GET /traces - List all known traces",
        },
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="BHIV Core API")
    parser.add_argument("--port", type=int, default=8003, help="Port to run the server on (default: 8003)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  BHIV CORE API")
    print("="*60)
    print(f" Server URL: http://{args.host}:{args.port}")
    print(f" API Documentation: http://{args.host}:{args.port}/docs")
    print("\n Endpoints:")
    print("   POST /execute_task - Execute a single task")
    print("   POST /execute_sequence - Execute a sequence of tasks")
    print("   GET /health - Health check")
    print("="*60)
    
    uvicorn.run(app, host=args.host, port=args.port)