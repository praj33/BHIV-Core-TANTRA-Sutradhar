"""
Trace Binding Module — TANTRA Trace Lock (Phase 3)

Cryptographic trace binding ensures tamper-evidence.

Binding formula:
    trace_hash = SHA-256(trace_id + execution_id + timestamp)

Rules:
 - Binding MUST be deterministic (same inputs → same hash)
 - Binding MUST be tamper-evident (changed input → different hash)
 - No plain trace passing without binding
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


def create_trace_binding(trace_id: str, execution_id: str, timestamp: str) -> str:
    """
    Create a cryptographic trace binding hash.
    
    Formula: SHA-256(trace_id + execution_id + timestamp)
    
    This binding is deterministic: the same inputs always produce
    the same hash. Any change in any field produces a different hash,
    making the trace tamper-evident.
    
    Args:
        trace_id: The trace identifier (from trace_origin)
        execution_id: The execution identifier (task_id)
        timestamp: The binding timestamp (ISO 8601 UTC)
    
    Returns:
        Hex-encoded SHA-256 hash string
    """
    if not trace_id or not execution_id or not timestamp:
        raise ValueError("All binding fields (trace_id, execution_id, timestamp) are required")
    
    binding_input = f"{trace_id}{execution_id}{timestamp}"
    trace_hash = hashlib.sha256(binding_input.encode("utf-8")).hexdigest()
    
    logger.info(
        f"Trace binding created: trace_id={trace_id}, "
        f"execution_id={execution_id}, hash={trace_hash[:16]}..."
    )
    return trace_hash


def verify_trace_binding(
    trace_id: str,
    execution_id: str,
    timestamp: str,
    expected_hash: str,
) -> bool:
    """
    Verify a trace binding hash against expected values.
    
    Recomputes the hash from the raw inputs and compares
    against the expected hash. Any tampering will cause mismatch.
    
    Args:
        trace_id: The trace identifier
        execution_id: The execution identifier
        timestamp: The binding timestamp
        expected_hash: The hash to verify against
    
    Returns:
        True if binding is valid (hashes match), False if tampered
    """
    computed_hash = create_trace_binding(trace_id, execution_id, timestamp)
    is_valid = computed_hash == expected_hash
    
    if not is_valid:
        logger.error(
            f"TRACE BINDING VERIFICATION FAILED: "
            f"trace_id={trace_id}, execution_id={execution_id} — "
            f"expected={expected_hash[:16]}..., got={computed_hash[:16]}..."
        )
    else:
        logger.info(f"Trace binding verified: trace_id={trace_id}")
    
    return is_valid
