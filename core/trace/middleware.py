"""
Trace Middleware — X-Trace-Id Header Propagation

FastAPI middleware that:
  1. Captures X-Trace-Id from incoming request headers
  2. If present (internal call) → preserves it, no regeneration
  3. If absent (gateway/external call) → generates new trace_id
  4. Stores trace_id in contextvars (async-safe, per-request)
  5. Adds X-Trace-Id to response headers

Any code can access the current trace_id via get_current_trace_id().
Outgoing HTTP calls use get_current_trace_id() to attach X-Trace-Id.

Header name: X-Trace-Id (standard across all TANTRA services)
"""

import uuid
import logging
from contextvars import ContextVar
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CONTEXT VAR — async-safe, per-request trace_id storage
# ═══════════════════════════════════════════════════════════

_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

TRACE_HEADER = "X-Trace-Id"


def get_current_trace_id() -> Optional[str]:
    """Get the trace_id for the current request context.
    Returns None if called outside a request context."""
    return _trace_id_var.get()


def set_current_trace_id(trace_id: str) -> None:
    """Set the trace_id for the current request context."""
    _trace_id_var.set(trace_id)


# ═══════════════════════════════════════════════════════════
# FASTAPI MIDDLEWARE
# ═══════════════════════════════════════════════════════════

class TraceMiddleware(BaseHTTPMiddleware):
    """
    Intercepts every request:
    - If X-Trace-Id header exists → use it (internal call, preserve)
    - If X-Trace-Id header missing → generate new trace_id (gateway call)
    - Sets trace_id in contextvars for downstream access
    - Adds X-Trace-Id to response headers
    """

    async def dispatch(self, request: Request, call_next):
        # Check incoming header
        incoming_trace_id = request.headers.get(TRACE_HEADER)

        if incoming_trace_id:
            # Internal call — preserve existing trace_id
            trace_id = incoming_trace_id
            logger.info(f"Trace propagated from upstream: {trace_id}")
        else:
            # Gateway/external call — generate new trace_id
            trace_id = str(uuid.uuid4())
            logger.info(f"Trace originated at gateway: {trace_id}")

        # Store in contextvars (accessible to all code in this request)
        set_current_trace_id(trace_id)

        # Process request
        response: Response = await call_next(request)

        # Add trace_id to response headers
        response.headers[TRACE_HEADER] = trace_id

        return response


# ═══════════════════════════════════════════════════════════
# OUTGOING HTTP HELPER
# ═══════════════════════════════════════════════════════════

def get_trace_headers(trace_id: str = None) -> dict:
    """
    Get headers with X-Trace-Id for outgoing HTTP calls.
    Uses provided trace_id, or falls back to current context.
    """
    tid = trace_id or get_current_trace_id()
    headers = {"Content-Type": "application/json"}
    if tid:
        headers[TRACE_HEADER] = tid
    return headers
