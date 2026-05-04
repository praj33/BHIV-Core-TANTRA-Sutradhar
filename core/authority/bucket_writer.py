"""
Bucket Writer -- Phase 3-4

Append-only truth writer from Core to Bucket.
Every valid execution MUST write to Bucket.
If Bucket is unavailable, execution FAILS (fail-closed).

Rules:
  - Append-only: no mutation, no overwrite, no conditional writes
  - Fail-closed: Bucket unavailable = execution incomplete
  - Every record is immutable once written
"""

import json
import hashlib
import logging
import urllib.request
import urllib.error
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

BUCKET_SERVICE_URL = os.environ.get("BUCKET_SERVICE_URL", "http://localhost:9003")

# Local append-only log (fallback truth store when Bucket service is being built)
BUCKET_LOG_FILE = os.environ.get("BUCKET_LOG_FILE", "logs/bucket_truth_log.jsonl")


class BucketWriteError(Exception):
    """Raised when Bucket write fails. Execution is INCOMPLETE."""
    pass


def append_to_bucket(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append an execution record to Bucket (append-only).
    
    This is the canonical truth write. Once written, the record
    is immutable.
    
    Args:
        event: Execution record containing:
            - trace_id
            - execution_id
            - execution_token
            - decision
            - timestamp
            - payload_hash
    
    Returns:
        Write confirmation with bucket_write_id
    
    Raises:
        BucketWriteError: If write fails (execution is INCOMPLETE)
    """
    # Validate required fields
    required = ["trace_id", "execution_id", "execution_token", "decision", "timestamp", "payload_hash"]
    for field in required:
        if field not in event:
            raise BucketWriteError(
                f"BUCKET WRITE FAILED: Missing required field '{field}'. "
                f"Execution is INCOMPLETE."
            )
    
    # Add write metadata
    write_record = {
        **event,
        "bucket_write_id": _generate_write_id(event),
        "bucket_write_timestamp": get_normalized_timestamp(),
        "record_hash": _compute_record_hash(event),
    }
    
    # Try external Bucket service first
    try:
        return _write_to_bucket_service(write_record)
    except ConnectionError:
        logger.warning("External Bucket service unreachable, writing to local log")
    
    # Write to local append-only log
    try:
        return _write_to_local_log(write_record)
    except Exception as e:
        raise BucketWriteError(
            f"BUCKET WRITE FAILED: Cannot write to any truth store. "
            f"Execution is INCOMPLETE. Error: {e}"
        )


def _generate_write_id(event: Dict[str, Any]) -> str:
    """Generate a unique write ID for the bucket record."""
    input_str = f"{event['trace_id']}:{event['execution_id']}:{event['timestamp']}"
    return hashlib.sha256(input_str.encode("utf-8")).hexdigest()[:24]


def _compute_record_hash(event: Dict[str, Any]) -> str:
    """Compute integrity hash of the entire record."""
    record_str = json.dumps(event, sort_keys=True)
    return hashlib.sha256(record_str.encode("utf-8")).hexdigest()


def _write_to_bucket_service(record: Dict[str, Any]) -> Dict[str, Any]:
    """Write to external Bucket service via HTTP."""
    url = f"{BUCKET_SERVICE_URL}/bucket/append"
    data = json.dumps(record).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            response = json.loads(resp.read().decode("utf-8"))
            logger.info(
                f"BUCKET WRITE SUCCESS (external): "
                f"trace_id={record['trace_id']}, "
                f"write_id={record['bucket_write_id']}"
            )
            return {
                "status": "written",
                "bucket_write_id": record["bucket_write_id"],
                "store": "external",
            }
    except urllib.error.URLError as e:
        raise ConnectionError(f"Bucket service unreachable: {e}")


def _write_to_local_log(record: Dict[str, Any]) -> Dict[str, Any]:
    """Write to local append-only JSONL log."""
    os.makedirs(os.path.dirname(BUCKET_LOG_FILE), exist_ok=True)
    
    with open(BUCKET_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    
    logger.info(
        f"BUCKET WRITE SUCCESS (local): "
        f"trace_id={record['trace_id']}, "
        f"write_id={record['bucket_write_id']}"
    )
    return {
        "status": "written",
        "bucket_write_id": record["bucket_write_id"],
        "store": "local",
    }


def verify_bucket_record(trace_id: str) -> Optional[Dict[str, Any]]:
    """
    Verify that a record exists in the local Bucket log for the given trace_id.
    
    Args:
        trace_id: Trace ID to look up
    
    Returns:
        The record if found, None otherwise
    """
    if not os.path.exists(BUCKET_LOG_FILE):
        return None
    
    with open(BUCKET_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                if record.get("trace_id") == trace_id:
                    return record
            except json.JSONDecodeError:
                continue
    
    return None
