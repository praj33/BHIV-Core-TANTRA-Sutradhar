"""
InsightFlow Client — Telemetry + Trace Observability (Vijay)

Emits full trace chains to InsightFlow after execution completes.
Every execution MUST emit a trace. Missing trace = audit gap.

The trace includes ALL signals from every layer:
  Core → Sovereign → CET → Sarathi → Bridge → Execution → Bucket
"""

import json
import logging
import urllib.request
import urllib.error
import os
from typing import Dict, Any, List

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

INSIGHTFLOW_SERVICE_URL = os.environ.get("INSIGHTFLOW_SERVICE_URL", "http://localhost:9006")

# Local fallback log for InsightFlow traces
INSIGHTFLOW_LOG_FILE = os.environ.get("INSIGHTFLOW_LOG_FILE", "logs/insightflow_traces.jsonl")


class InsightFlowError(Exception):
    """Raised when InsightFlow emission fails."""
    pass


def emitTrace(
    trace_id: str,
    trace_chain: List[Dict[str, Any]],
    execution_status: str = "completed",
    bucket_verified: bool = False,
) -> Dict[str, Any]:
    """
    Emit full trace chain to InsightFlow.

    Args:
        trace_id: Core-generated trace_id (SAME across all layers)
        trace_chain: List of signal dicts from each layer
        execution_status: Final status (completed/failed/blocked)
        bucket_verified: Whether Bucket write was verified

    Returns:
        Emission result

    Raises:
        InsightFlowError: If emission fails (logged but does NOT block execution)
    """
    payload = {
        "trace_id": trace_id,
        "timestamp": get_normalized_timestamp(),
        "execution_status": execution_status,
        "bucket_verified": bucket_verified,
        "trace_chain": trace_chain,
        "chain_length": len(trace_chain),
        "source": "bhiv_core",
    }

    logger.info(f"Emitting trace to InsightFlow: trace_id={trace_id}, signals={len(trace_chain)}")

    # Try external InsightFlow service
    try:
        return _emit_external(payload)
    except Exception as e:
        logger.warning(f"InsightFlow external emit failed: {e}. Writing to local log.")

    # Fallback: local log (trace must NOT be lost)
    try:
        return _emit_local(payload)
    except Exception as e:
        logger.error(f"InsightFlow local emit also failed: {e}")
        raise InsightFlowError(f"Cannot emit trace for {trace_id}: {e}")


def _emit_external(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Emit to external InsightFlow (Vijay's Data Universe Registry).

    Maps trace data to dataset registration format:
      POST /api/v1/datasets/
    Schema: canonical_id (BHIV-DS-TANTRA-TRACE-XXX), dataset_name,
            owner_name, owner_team, domain_primary, source_system
    """
    url = f"{INSIGHTFLOW_SERVICE_URL}/api/v1/datasets/"
    trace_id = payload.get("trace_id", "unknown")
    short_id = trace_id[:8].replace("-", "").upper()

    # Map trace payload to Vijay's dataset registration schema
    dataset_payload = {
        "canonical_id": f"BHIV-DS-TANTRA-TRACE-{short_id}",
        "dataset_name": f"TANTRA Trace {trace_id[:8]}",
        "description": (
            f"Execution trace from BHIV Core. "
            f"Status: {payload.get('execution_status', 'unknown')}. "
            f"Chain length: {payload.get('chain_length', 0)}."
        ),
        "owner_name": "Raj Prajapati",
        "owner_team": "bhiv-core",
        "domain_primary": "tantra",
        "source_system": "bhiv-core-v1",
        "tags": ["tantra", "trace", "execution", payload.get("execution_status", "unknown")],
        "metadata": payload,
    }

    data = json.dumps(dataset_payload, default=str).encode("utf-8")
    from core.trace.middleware import get_trace_headers
    headers = get_trace_headers(trace_id)
    headers["ngrok-skip-browser-warning"] = "true"
    api_key = os.environ.get("INSIGHTFLOW_API_KEY", "")
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(
        url, data=data,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            response = json.loads(resp.read().decode("utf-8"))
            logger.info(f"InsightFlow trace emitted (external): trace_id={trace_id}")
            return {"status": "emitted", "store": "external", "trace_id": trace_id}
    except urllib.error.URLError as e:
        raise ConnectionError(f"InsightFlow unreachable: {e}")


def _emit_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Write trace to local JSONL log."""
    os.makedirs(os.path.dirname(INSIGHTFLOW_LOG_FILE), exist_ok=True)
    with open(INSIGHTFLOW_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
    logger.info(f"InsightFlow trace emitted (local): trace_id={payload['trace_id']}")
    return {"status": "emitted", "store": "local", "trace_id": payload["trace_id"]}


def buildTraceChain(
    trace_id: str,
    origin: Dict = None,
    sovereign: Dict = None,
    cet: Dict = None,
    sarathi: Dict = None,
    bridge: Dict = None,
    execution: Dict = None,
    bucket: Dict = None,
) -> List[Dict[str, Any]]:
    """
    Build a full trace chain from individual layer outputs.
    Each entry has: layer, trace_id, timestamp, data.
    """
    chain = []
    timestamp = get_normalized_timestamp()

    layers = [
        ("core_origin", origin),
        ("sovereign_core", sovereign),
        ("cet", cet),
        ("sarathi", sarathi),
        ("bridge", bridge),
        ("execution", execution),
        ("bucket", bucket),
    ]

    for layer_name, data in layers:
        if data is not None:
            chain.append({
                "layer": layer_name,
                "trace_id": trace_id,
                "timestamp": data.get("timestamp", timestamp),
                "data": data,
            })

    return chain
