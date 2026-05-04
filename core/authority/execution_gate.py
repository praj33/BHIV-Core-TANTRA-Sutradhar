"""
Execution Gate -- Phase 1

Non-bypassable execution gate that requires a valid execution_token
from Sarathi before ANY execution can proceed.

Every execution surface MUST call:
    gated_execute(action_fn, token, trace_id, *args, **kwargs)

Without a valid token, execution is BLOCKED.
"""

import hashlib
import json
import logging
import urllib.request
import urllib.error
import os
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timezone

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

SARATHI_SERVICE_URL = os.environ.get("SARATHI_SERVICE_URL", "http://localhost:9002")

# In-memory token registry (for internal mode)
# In external mode, tokens are validated via Sarathi service
_valid_tokens: Dict[str, str] = {}  # token -> trace_id mapping
_used_tokens: set = set()  # prevent replay


class ExecutionBlockedError(Exception):
    """Raised when execution is blocked due to missing/invalid token."""
    pass


def register_token(token: str, trace_id: str):
    """
    Register a valid execution token (called after Sarathi CLEARED).
    
    Args:
        token: The execution_token from Sarathi
        trace_id: The trace_id this token is bound to
    """
    _valid_tokens[token] = trace_id
    logger.info(f"Execution token registered for trace_id={trace_id}")


def validate_execution_token(token: str, trace_id: str) -> bool:
    """
    Validate an execution token against a trace_id.
    
    Checks:
    1. Token is not empty
    2. Token exists in registry
    3. Token is bound to the correct trace_id
    4. Token has not been used before (replay prevention)
    
    Args:
        token: The execution_token to validate
        trace_id: The expected trace_id
    
    Returns:
        True if valid
    
    Raises:
        ExecutionBlockedError: If token is invalid
    """
    if not token:
        raise ExecutionBlockedError(
            f"EXECUTION BLOCKED: No execution_token provided for trace {trace_id}. "
            f"Execution requires a valid token from Sarathi."
        )
    
    if not trace_id:
        raise ExecutionBlockedError(
            f"EXECUTION BLOCKED: No trace_id provided. "
            f"Cannot validate token without trace_id."
        )
    
    # Check replay
    if token in _used_tokens:
        raise ExecutionBlockedError(
            f"EXECUTION BLOCKED: Token replay detected for trace {trace_id}. "
            f"This token has already been used. Replay attacks are rejected."
        )
    
    # Check token exists and matches trace_id
    if token in _valid_tokens:
        bound_trace = _valid_tokens[token]
        if bound_trace != trace_id:
            raise ExecutionBlockedError(
                f"EXECUTION BLOCKED: Token/trace_id mismatch. "
                f"Token is bound to trace {bound_trace}, not {trace_id}."
            )
        return True
    
    # Try external validation if token not in local registry
    try:
        return _validate_token_external(token, trace_id)
    except ConnectionError:
        raise ExecutionBlockedError(
            f"EXECUTION BLOCKED: Cannot validate token for trace {trace_id}. "
            f"Sarathi service unreachable. FAIL CLOSED."
        )


def _validate_token_external(token: str, trace_id: str) -> bool:
    """Validate token via external Sarathi service."""
    url = f"{SARATHI_SERVICE_URL}/sarathi/validate-token?token={token}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("valid"):
                return True
            else:
                raise ExecutionBlockedError(
                    f"EXECUTION BLOCKED: Token rejected by Sarathi for trace {trace_id}. "
                    f"Reason: {data.get('reason', 'unknown')}"
                )
    except urllib.error.URLError as e:
        raise ConnectionError(f"Sarathi unreachable: {e}")


def mark_token_used(token: str):
    """Mark a token as used (prevents replay)."""
    _used_tokens.add(token)
    if token in _valid_tokens:
        del _valid_tokens[token]
    logger.info(f"Execution token consumed (replay prevention)")


def gated_execute(
    action_fn: Callable,
    token: str,
    trace_id: str,
    *args,
    **kwargs,
) -> Any:
    """
    Execute an action ONLY if the execution_token is valid.
    
    This is the ONLY way execution should happen in the system.
    
    Args:
        action_fn: The function to execute
        token: execution_token from Sarathi
        trace_id: trace_id this execution belongs to
        *args, **kwargs: Arguments passed to action_fn
    
    Returns:
        Result of action_fn
    
    Raises:
        ExecutionBlockedError: If token is invalid/missing/replayed
    """
    # STEP 1: Validate token (blocks if invalid)
    validate_execution_token(token, trace_id)
    
    # STEP 2: Mark token as used BEFORE execution (prevents replay even if execution fails)
    mark_token_used(token)
    
    # STEP 3: Execute
    logger.info(f"EXECUTION GATE OPENED: trace_id={trace_id}")
    result = action_fn(*args, **kwargs)
    logger.info(f"EXECUTION COMPLETE: trace_id={trace_id}")
    
    return result


def get_execution_record(
    trace_id: str,
    execution_id: str,
    token: str,
    decision: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a canonical execution record for Bucket write.
    
    Args:
        trace_id: Trace identifier
        execution_id: Execution identifier (task_id)
        token: The execution_token used
        decision: The Sovereign decision (ALLOW)
        payload: The execution payload
    
    Returns:
        Canonical execution record dict
    """
    timestamp = get_normalized_timestamp()
    payload_str = json.dumps(payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    
    return {
        "trace_id": trace_id,
        "execution_id": execution_id,
        "execution_token": token,
        "decision": decision,
        "timestamp": timestamp,
        "payload_hash": payload_hash,
    }
