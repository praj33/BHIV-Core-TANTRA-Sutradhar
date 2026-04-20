"""
Trace Origin Module — TANTRA Trace Lock (Phase 1)

Core MUST generate trace_id at the FIRST entry point.
No downstream system may generate or modify trace_id.

Entry points:
 - User request (web interface / CLI)
 - API call (MCP Bridge / Simple API)
 - System trigger (core events)

Rules:
 - trace_id MUST originate in Core
 - trace_id MUST be unique
 - trace_timestamp MUST be UTC-normalized
"""

import uuid
import threading
import logging
from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

# Thread-safe set to track issued trace_ids for uniqueness enforcement
_issued_trace_ids = set()
_trace_lock = threading.Lock()

# Maximum size before clearing old trace IDs (memory bound)
_MAX_TRACE_HISTORY = 100_000


def generate_trace_id() -> str:
    """
    Generate a globally unique trace_id.
    
    Uses UUID v4 for cryptographic randomness.
    Enforces uniqueness by checking against all previously issued IDs.
    
    Returns:
        A unique trace_id string (UUID v4 format)
    
    Raises:
        RuntimeError: If a duplicate trace_id is generated (statistically impossible)
    """
    with _trace_lock:
        # Bound memory usage
        if len(_issued_trace_ids) >= _MAX_TRACE_HISTORY:
            _issued_trace_ids.clear()
            logger.info("Trace ID history cleared (memory bound reached)")
        
        trace_id = str(uuid.uuid4())
        
        # Uniqueness enforcement — statistically impossible to collide, but verified
        if trace_id in _issued_trace_ids:
            # Regenerate on collision (essentially never happens)
            trace_id = str(uuid.uuid4())
            if trace_id in _issued_trace_ids:
                raise RuntimeError("Trace ID collision detected — critical system error")
        
        _issued_trace_ids.add(trace_id)
        logger.info(f"Trace origin generated: {trace_id}")
        return trace_id


def generate_trace_timestamp() -> str:
    """
    Generate a UTC-normalized trace timestamp.
    
    Delegates to time_sync module for standardization.
    
    Returns:
        ISO 8601 UTC timestamp string
    """
    return get_normalized_timestamp()


def create_trace_origin(source: str) -> dict:
    """
    Create a complete trace origin record.
    
    This is the canonical entry point for trace creation.
    Should be called ONCE at the very first system entry point.
    
    Args:
        source: Origin source identifier (e.g., 'mcp_bridge', 'core_events', 'simple_api')
    
    Returns:
        dict with trace_id, trace_timestamp, and source
    """
    trace_id = generate_trace_id()
    trace_timestamp = generate_trace_timestamp()
    
    origin = {
        "trace_id": trace_id,
        "trace_timestamp": trace_timestamp,
        "source": source,
    }
    
    logger.info(f"Trace origin created: source={source}, trace_id={trace_id}")
    return origin
