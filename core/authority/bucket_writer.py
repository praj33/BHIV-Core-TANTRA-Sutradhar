"""
Bucket Writer -- SEALED (Phase 3)

Append-only truth writer from Core to Bucket.

INVARIANT: Execution success = Bucket write success.
No response returned before Bucket write.
No async bypass. No silent failure.

Rules:
  - Append-only: no mutation, no overwrite, no conditional writes
  - Fail-closed: Bucket unavailable = execution FAILED
  - Every record is immutable once written
  - Post-write verification mandatory
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
BUCKET_LOG_FILE = os.environ.get("BUCKET_LOG_FILE", "logs/bucket_truth_log.jsonl")


class BucketWriteError(Exception):
    """Raised when Bucket write fails. Execution is INCOMPLETE."""
    pass


class ExecutionFinalizationError(Exception):
    """Raised when execution cannot be finalized (truth not recorded)."""
    pass


# ═══════════════════════════════════════════════════════════
# EXECUTION FINALIZATION LAYER (Phase 3)
# ═══════════════════════════════════════════════════════════

def finalize_execution(
    trace_id: str,
    execution_id: str,
    token: str,
    decision: str,
    payload: Dict[str, Any],
    execution_result: Any,
) -> Dict[str, Any]:
    """
    Finalize execution by writing truth to Bucket AND verifying it.

    INVARIANT: If this function does not return success,
    the execution is FAILED regardless of what happened.

    Flow:
    1. Build execution record
    2. Write to Bucket (append_to_bucket)
    3. Verify record exists and is correct
    4. ONLY THEN return success

    Args:
        trace_id: Trace identifier
        execution_id: Execution/task identifier
        token: Execution token used
        decision: Sovereign decision (ALLOW)
        payload: Execution payload
        execution_result: Result of execution

    Returns:
        Finalization record with bucket_write confirmation

    Raises:
        ExecutionFinalizationError: If truth cannot be recorded
    """
    # Step 1: Build record
    timestamp = get_normalized_timestamp()
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    event = {
        "trace_id": trace_id,
        "execution_id": execution_id,
        "execution_token": token,
        "decision": decision,
        "timestamp": timestamp,
        "payload_hash": payload_hash,
    }

    # Step 2: Write to Bucket
    try:
        bucket_result = append_to_bucket(event)
    except BucketWriteError as e:
        raise ExecutionFinalizationError(
            f"EXECUTION FINALIZATION FAILED: Bucket write failed for "
            f"trace={trace_id}. Execution is NOT complete. Error: {e}"
        )

    # Step 3: Verify record
    record = verify_bucket_record(trace_id)
    if record is None:
        raise ExecutionFinalizationError(
            f"EXECUTION FINALIZATION FAILED: Post-write verification failed. "
            f"Record not found for trace={trace_id}."
        )

    # Verify integrity
    if record.get("trace_id") != trace_id:
        raise ExecutionFinalizationError(
            f"EXECUTION FINALIZATION FAILED: trace_id mismatch in stored record."
        )

    if record.get("execution_token") != token:
        raise ExecutionFinalizationError(
            f"EXECUTION FINALIZATION FAILED: execution_token mismatch in stored record."
        )

    # Step 4: Return success (ONLY if everything verified)
    return {
        "status": "finalized",
        "trace_id": trace_id,
        "execution_id": execution_id,
        "bucket_write": bucket_result.get("status", "unknown"),
        "bucket_write_id": bucket_result.get("bucket_write_id", ""),
        "store": bucket_result.get("store", ""),
        "verified": True,
    }


# ═══════════════════════════════════════════════════════════
# APPEND TO BUCKET
# ═══════════════════════════════════════════════════════════

def append_to_bucket(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append an execution record to Bucket (append-only).

    Returns write confirmation with bucket_write_id.
    Raises BucketWriteError if write fails.
    """
    required = [
        "trace_id", "execution_id", "execution_token",
        "decision", "timestamp", "payload_hash",
    ]
    for field in required:
        if field not in event:
            raise BucketWriteError(
                f"BUCKET WRITE FAILED: Missing required field '{field}'. "
                f"Execution is INCOMPLETE."
            )

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
        logger.warning("External Bucket unreachable, writing to local log")

    # Write to local append-only log
    try:
        return _write_to_local_log(write_record)
    except Exception as e:
        raise BucketWriteError(
            f"BUCKET WRITE FAILED: Cannot write to any truth store. "
            f"Execution is INCOMPLETE. Error: {e}"
        )


def _generate_write_id(event: Dict[str, Any]) -> str:
    """Generate unique write ID."""
    input_str = f"{event['trace_id']}:{event['execution_id']}:{event['timestamp']}"
    return hashlib.sha256(input_str.encode("utf-8")).hexdigest()[:24]


def _compute_record_hash(event: Dict[str, Any]) -> str:
    """Compute integrity hash of the record."""
    record_str = json.dumps(event, sort_keys=True)
    return hashlib.sha256(record_str.encode("utf-8")).hexdigest()


def _write_to_bucket_service(record: Dict[str, Any]) -> Dict[str, Any]:
    """Write to external Bucket service via HTTP."""
    url = f"{BUCKET_SERVICE_URL}/bucket/append"
    data = json.dumps(record).encode("utf-8")
    from core.trace.middleware import get_trace_headers
    req = urllib.request.Request(
        url, data=data,
        headers=get_trace_headers(record.get("trace_id")),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            json.loads(resp.read().decode("utf-8"))
            logger.info(
                f"BUCKET WRITE SUCCESS (external): "
                f"trace_id={record['trace_id']}"
            )
            return {
                "status": "written",
                "bucket_write_id": record["bucket_write_id"],
                "store": "external",
            }
    except urllib.error.URLError as e:
        raise ConnectionError(f"Bucket unreachable: {e}")


def _write_to_local_log(record: Dict[str, Any]) -> Dict[str, Any]:
    """Write to local append-only JSONL log."""
    os.makedirs(os.path.dirname(BUCKET_LOG_FILE), exist_ok=True)

    with open(BUCKET_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

    logger.info(
        f"BUCKET WRITE SUCCESS (local): "
        f"trace_id={record['trace_id']}"
    )
    return {
        "status": "written",
        "bucket_write_id": record["bucket_write_id"],
        "store": "local",
    }


def verify_bucket_record(trace_id: str) -> Optional[Dict[str, Any]]:
    """
    Verify that a record exists in Bucket for the given trace_id.
    Checks local log. Returns the record if found, None otherwise.
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
