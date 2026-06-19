"""
CET Client — Contract Engine (Tanvi)

Calls the CET (Contract Execution Tracker) service for contract compilation.
CET receives trace_id + input and returns SUM-SCRIPT + contract_hash.

Core treats CET output as OPAQUE — no mutation allowed.
Hash before CET == hash forwarded to Sarathi/Bridge.
"""

import json
import hashlib
import logging
import urllib.request
import urllib.error
import os
from typing import Dict, Any

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

CET_SERVICE_URL = os.environ.get("CET_SERVICE_URL", "http://localhost:9004")


class CETError(Exception):
    """Raised when CET service fails. Execution is BLOCKED."""
    pass


def callCET(trace_id: str, input_data: str, decision_hash: str) -> Dict[str, Any]:
    """
    Call CET service for contract compilation.

    Args:
        trace_id: Core-generated trace_id (MUST NOT change)
        input_data: The input being processed
        decision_hash: Hash from Sovereign decision

    Returns:
        CET response: {contract_hash, sum_script, trace_id, ...}

    Raises:
        CETError: If CET is unreachable or returns error (FAIL CLOSED)
    """
    url = f"{CET_SERVICE_URL}/cet/compile"
    # Tanvi's KSML schema: input must contain exactly these 7 keys in canonical order
    payload = {
        "trace_id": trace_id,
        "input": {
            "decision_id": f"dec-{trace_id[:8]}",
            "trace_id": trace_id,
            "intent": input_data,
            "actors": ["bhiv-core", "sovereign"],
            "constraints": ["fail-closed", "append-only"],
            "context": {
                "source": "bhiv-core",
                "type": "execution_request",
                "decision_hash": decision_hash,
            },
            "timestamp": get_normalized_timestamp(),
        },
        "decision_hash": decision_hash,
        "timestamp": get_normalized_timestamp(),
    }

    logger.info(f"Calling CET: trace_id={trace_id}")

    try:
        from core.trace.middleware import get_trace_headers
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers=get_trace_headers(trace_id),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            response = json.loads(resp.read().decode("utf-8"))

        # Verify trace_id was not mutated by CET
        if response.get("trace_id") and response["trace_id"] != trace_id:
            raise CETError(
                f"CET mutated trace_id: sent={trace_id}, "
                f"received={response['trace_id']}. REJECTED."
            )

        logger.info(f"CET response: contract_hash={response.get('contract_hash', 'N/A')}")
        return response

    except urllib.error.URLError as e:
        raise CETError(f"CET service unreachable at {url}: {e}. FAIL CLOSED.")
    except json.JSONDecodeError as e:
        raise CETError(f"CET returned invalid JSON: {e}. FAIL CLOSED.")


def verify_contract_integrity(
    original_hash: str,
    forwarded_hash: str,
) -> bool:
    """
    Verify that the contract hash from CET was not mutated in transit.

    Args:
        original_hash: Hash received from CET
        forwarded_hash: Hash being forwarded downstream

    Returns:
        True if identical

    Raises:
        CETError: If hashes differ (contract integrity violated)
    """
    if original_hash != forwarded_hash:
        raise CETError(
            f"CONTRACT INTEGRITY VIOLATED: "
            f"CET hash={original_hash}, forwarded={forwarded_hash}. "
            f"Payload was mutated. Execution BLOCKED."
        )
    return True
