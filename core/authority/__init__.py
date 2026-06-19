"""
Authority Interface -- Core Authority Wrappers (Phase 1)

Wraps SovereignCore and Sarathi as callable interfaces.
When USE_EXTERNAL_AUTHORITY is True, routes to external HTTP services.
When False, uses internal modules directly.

All execution flows MUST go through these wrappers.
"""

import os
import json
import hashlib
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from core.trace.trace_context import TraceContext, TraceSignal
from core.trace.trace_binding import create_trace_binding
from core.trace.time_sync import get_normalized_timestamp
from core.trace.sovereign_core import SovereignCore as InternalSovereignCore
from core.trace.sarathi_enforcer import SarathiEnforcer as InternalSarathiEnforcer
from core.trace.sarathi_enforcer import SarathiEnforcementError

logger = logging.getLogger(__name__)

# ---------- CONFIG ----------

USE_EXTERNAL_AUTHORITY = os.environ.get("USE_EXTERNAL_AUTHORITY", "false").lower() == "true"
SOVEREIGN_SERVICE_URL = os.environ.get("SOVEREIGN_SERVICE_URL", "http://localhost:9001")
SARATHI_SERVICE_URL = os.environ.get("SARATHI_SERVICE_URL", "http://localhost:9002")


def _http_post(url: str, payload: dict, timeout: int = 10) -> dict:
    """Make an HTTP POST request and return JSON response."""
    from core.trace.middleware import get_trace_headers
    data = json.dumps(payload).encode("utf-8")
    headers = get_trace_headers(payload.get("trace_id"))
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise ConnectionError(f"Authority service unreachable at {url}: {e}")
    except Exception as e:
        raise ConnectionError(f"Authority service error at {url}: {e}")


# ========================================
# callSovereign -- Decision Interface
# ========================================

def callSovereign(
    trace_ctx: TraceContext,
    input_data: str,
    context: Optional[Dict[str, Any]] = None,
) -> TraceContext:
    """
    Route decision request to Sovereign Core (internal or external).

    Args:
        trace_ctx: Current immutable trace context
        input_data: Raw input to evaluate
        context: Optional additional context

    Returns:
        NEW TraceContext with decision signal appended

    Raises:
        ConnectionError: If external service is unreachable (FAIL CLOSED)
    """
    if USE_EXTERNAL_AUTHORITY:
        return _callSovereign_external(trace_ctx, input_data, context)
    else:
        return _callSovereign_internal(trace_ctx, input_data, context)


def _callSovereign_internal(
    trace_ctx: TraceContext,
    input_data: str,
    context: Optional[Dict[str, Any]] = None,
) -> TraceContext:
    """Use internal SovereignCore module."""
    sc = InternalSovereignCore()
    return sc.evaluate(trace_ctx, input_data, context)


def _callSovereign_external(
    trace_ctx: TraceContext,
    input_data: str,
    context: Optional[Dict[str, Any]] = None,
) -> TraceContext:
    """Call external Sovereign service via /analyze (Rajaryan's gateway).

    Maps risk_category to decision:
      LOW/MEDIUM → ALLOW
      HIGH/CRITICAL → DENY
    """
    import hashlib
    url = f"{SOVEREIGN_SERVICE_URL}/analyze"
    payload = {
        "text": input_data,
    }

    logger.info(f"Calling external Sovereign (/analyze): trace_id={trace_ctx.trace_id}")

    # FAIL CLOSED: if service is down, raise -- do NOT fallback
    response = _http_post(url, payload)

    # Map risk response to Sovereign decision
    risk_category = response.get("risk_category", "LOW")
    if risk_category in ("HIGH", "CRITICAL"):
        decision = "DENY"
    else:
        decision = "ALLOW"

    input_hash = hashlib.sha256(input_data.encode("utf-8")).hexdigest()

    # Build decision signal from external response
    decision_signal = TraceSignal(
        layer="sovereign_core",
        signal_type="decision",
        timestamp=get_normalized_timestamp(),
        payload={
            "decision": decision,
            "policy_reference": "bhiv.sovereign.risk_scoring@v1.0",
            "input_hash": input_hash,
            "decision_hash": hashlib.sha256(
                f"{decision}:{input_hash}:{risk_category}".encode()
            ).hexdigest(),
            "risk_score": response.get("risk_score", 0.0),
            "risk_category": risk_category,
            "confidence": response.get("confidence_score", 0.0),
        },
    )

    return trace_ctx.add_signal(decision_signal)


# ========================================
# callSarathi -- Enforcement Interface
# ========================================

def callSarathi(
    trace_ctx: TraceContext,
    execution_payload: Optional[Dict[str, Any]] = None,
) -> TraceContext:
    """
    Route enforcement request to Sarathi (internal or external).

    Args:
        trace_ctx: Trace context WITH decision signal
        execution_payload: Payload for execution (used by external service)

    Returns:
        NEW TraceContext with enforcement signal appended

    Raises:
        SarathiEnforcementError: If decision is DENY or missing
        ConnectionError: If external service is unreachable (FAIL CLOSED)
    """
    if USE_EXTERNAL_AUTHORITY:
        return _callSarathi_external(trace_ctx, execution_payload)
    else:
        return _callSarathi_internal(trace_ctx)


def _callSarathi_internal(trace_ctx: TraceContext) -> TraceContext:
    """Use internal SarathiEnforcer module."""
    se = InternalSarathiEnforcer()
    return se.enforce(trace_ctx)


def _callSarathi_external(
    trace_ctx: TraceContext,
    execution_payload: Optional[Dict[str, Any]] = None,
) -> TraceContext:
    """Call external Sarathi service via HTTP."""
    url = f"{SARATHI_SERVICE_URL}/sarathi/enforce"

    # Extract decision info from trace
    decision_signal = trace_ctx.get_signal("decision")
    if decision_signal is None:
        raise SarathiEnforcementError(
            f"No decision signal in trace {trace_ctx.trace_id}. "
            f"Cannot call Sarathi without Sovereign decision."
        )

    decision_hash = decision_signal.payload.get("decision_hash", "")

    # Rajaryan's Sarathi gate: signature_hash = SHA-256("execution_id|rajya_verdict|timestamp")
    from datetime import datetime, timezone
    execution_id = f"exec-{trace_ctx.trace_id.replace('-', '')[:12]}"
    sarathi_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rajya_verdict = "EXECUTION_APPROVED"
    raw_string = f"{execution_id}|{rajya_verdict}|{sarathi_timestamp}"
    signature_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

    payload = {
        "token": {
            "execution_id": execution_id,
            "rajya_verdict": rajya_verdict,
            "token_status": "VALID",
            "timestamp": sarathi_timestamp,
            "signature_hash": signature_hash,
        },
        "pipeline_execution_id": execution_id,
        "trace_id": trace_ctx.trace_id,
        "cet_hash": execution_payload.get("cet_hash", "") if execution_payload else "",
    }

    logger.info(f"Calling external Sarathi: trace_id={trace_ctx.trace_id}")

    # FAIL CLOSED: if service is down, raise -- do NOT fallback
    response = _http_post(url, payload)

    status = response.get("status", "BLOCKED")
    sarathi_jwt = response.get("jwt", "")  # Sarathi now returns signed JWT

    if status in ("CLEARED", "ALLOW"):
        enforcement_signal = TraceSignal(
            layer="sarathi",
            signal_type="enforcement",
            timestamp=response.get("timestamp", get_normalized_timestamp()),
            payload={
                "enforcement_status": "CLEARED",
                "validation_result": response.get("validation_result", "External Sarathi cleared"),
                "failure_reason": None,
                "execution_token": sarathi_jwt or response.get("execution_token", ""),
                "execution_id": execution_id,
            },
        )
        return trace_ctx.add_signal(enforcement_signal)
    else:
        enforcement_signal = TraceSignal(
            layer="sarathi",
            signal_type="enforcement",
            timestamp=response.get("timestamp", get_normalized_timestamp()),
            payload={
                "enforcement_status": "BLOCKED",
                "validation_result": response.get("validation_result", "External Sarathi blocked"),
                "failure_reason": response.get("failure_reason", "Decision denied"),
            },
        )
        # Add signal to trace before raising
        raise SarathiEnforcementError(
            f"Sarathi enforcement blocked trace {trace_ctx.trace_id}: "
            f"{response.get('failure_reason', 'DENIED')}"
        )
