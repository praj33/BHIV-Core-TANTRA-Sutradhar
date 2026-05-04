"""
Core Canonical Output — Phase 1

Produces deterministic, structured output with EXACT fields.
No extra fields. No missing fields. Deterministic field order.
Same input → same output ALWAYS.

Canonical output schema:
{
    "trace_id": "",
    "decision_id": "",
    "decision_hash": "",
    "verdict": "ALLOW | DENY",
    "enforcement_binding": "",
    "timestamp": ""
}
"""

import hashlib
import json
import logging
from typing import Dict, Any
from collections import OrderedDict

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

# Canonical field order — NEVER changes
CANONICAL_FIELDS = [
    "trace_id",
    "decision_id",
    "decision_hash",
    "verdict",
    "enforcement_binding",
    "timestamp",
]


def produce_canonical_output(
    trace_id: str,
    decision_id: str,
    decision_hash: str,
    verdict: str,
    enforcement_binding: str,
    timestamp: str,
) -> OrderedDict:
    """
    Produce a canonical output with EXACT fields in deterministic order.

    Rules:
      - No extra fields
      - No missing fields
      - Deterministic field order (always same)
      - No formatting drift
      - Same input → same output ALWAYS

    Args:
        trace_id: Trace identifier from Core origin
        decision_id: Unique decision identifier
        decision_hash: SHA-256 hash of decision
        verdict: "ALLOW" or "DENY" (nothing else)
        enforcement_binding: Binding reference from Sarathi
        timestamp: ISO 8601 UTC timestamp

    Returns:
        OrderedDict with exact canonical fields
    """
    # Validate verdict
    if verdict not in ("ALLOW", "DENY"):
        raise ValueError(f"Invalid verdict: {verdict}. Must be ALLOW or DENY.")

    output = OrderedDict()
    output["trace_id"] = str(trace_id)
    output["decision_id"] = str(decision_id)
    output["decision_hash"] = str(decision_hash)
    output["verdict"] = str(verdict)
    output["enforcement_binding"] = str(enforcement_binding)
    output["timestamp"] = str(timestamp)

    return output


def produce_from_trace_context(ctx, input_data: str = "") -> OrderedDict:
    """
    Produce canonical output from a TraceContext that has been
    through Sovereign + Sarathi.

    Args:
        ctx: TraceContext with decision and enforcement signals
        input_data: Raw input string (for decision_id generation)

    Returns:
        OrderedDict canonical output
    """
    # Extract decision signal
    decision_signal = ctx.get_signal("decision")
    if not decision_signal:
        raise ValueError("No decision signal in trace context")

    # Extract enforcement signal
    enforcement_signal = ctx.get_signal("enforcement")

    # Build canonical fields
    trace_id = ctx.trace_id
    verdict = decision_signal.payload.get("decision", "DENY")
    input_hash = decision_signal.payload.get("input_hash", "")
    decision_hash = decision_signal.payload.get(
        "decision_hash", input_hash
    )
    timestamp = decision_signal.timestamp

    # Decision ID: deterministic from trace + input
    decision_id = hashlib.sha256(
        f"{trace_id}:{input_hash}".encode("utf-8")
    ).hexdigest()[:16]

    # Enforcement binding
    if enforcement_signal:
        enforcement_binding = (
            f"{enforcement_signal.payload.get('enforcement_status', 'NONE')}"
            f":{enforcement_signal.payload.get('validation_result', '')[:40]}"
        )
    else:
        enforcement_binding = "NONE:no_enforcement_signal"

    return produce_canonical_output(
        trace_id=trace_id,
        decision_id=decision_id,
        decision_hash=decision_hash,
        verdict=verdict,
        enforcement_binding=enforcement_binding,
        timestamp=timestamp,
    )


def canonical_to_json(output: OrderedDict) -> str:
    """Serialize canonical output to deterministic JSON string."""
    return json.dumps(output, separators=(",", ":"))


def validate_canonical_output(output: Dict[str, Any]) -> bool:
    """
    Validate that an output dict has EXACTLY the canonical fields.
    No extra, no missing.
    """
    output_keys = set(output.keys())
    expected_keys = set(CANONICAL_FIELDS)

    if output_keys != expected_keys:
        extra = output_keys - expected_keys
        missing = expected_keys - output_keys
        logger.error(
            f"Schema violation: extra={extra}, missing={missing}"
        )
        return False

    return True
