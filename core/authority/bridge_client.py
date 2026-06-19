"""
Bridge Client — Gated Bridge (Ranjit)

Calls the Gated Bridge for execution validation.
Bridge validates execution_token + trace_id before allowing execution.

No execution without Bridge clearance when in live mode.
"""

import json
import logging
import urllib.request
import urllib.error
import os
from typing import Dict, Any

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

BRIDGE_SERVICE_URL = os.environ.get("BRIDGE_SERVICE_URL", "http://localhost:9005")


class BridgeError(Exception):
    """Raised when Bridge validation fails. Execution is BLOCKED."""
    pass


def callBridge(
    trace_id: str,
    execution_token: str,
    contract_hash: str = "",
) -> Dict[str, Any]:
    """
    Call Gated Bridge for execution validation.

    Args:
        trace_id: Core-generated trace_id
        execution_token: Token from Sarathi
        contract_hash: Hash from CET (forwarded unchanged)

    Returns:
        Bridge response: {status: "VALIDATED"/"REJECTED", ...}

    Raises:
        BridgeError: If Bridge rejects or is unreachable (FAIL CLOSED)
    """
    url = f"{BRIDGE_SERVICE_URL}/execute"
    payload = {
        "trace_id": trace_id,
        "execution_token": execution_token,
        "contract_hash": contract_hash,
        "timestamp": get_normalized_timestamp(),
    }

    logger.info(f"Calling Bridge: trace_id={trace_id}")

    try:
        from core.trace.middleware import get_trace_headers
        data = json.dumps(payload).encode("utf-8")
        headers = get_trace_headers(trace_id)
        headers["ngrok-skip-browser-warning"] = "true"
        req = urllib.request.Request(
            url, data=data,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            response = json.loads(resp.read().decode("utf-8"))

        status = response.get("status", "REJECTED")

        if status == "VALIDATED":
            logger.info(f"Bridge VALIDATED: trace_id={trace_id}")
            return response
        else:
            raise BridgeError(
                f"Bridge REJECTED execution for trace {trace_id}: "
                f"{response.get('reason', 'unknown')}"
            )

    except urllib.error.URLError as e:
        raise BridgeError(f"Bridge unreachable at {url}: {e}. FAIL CLOSED.")
    except json.JSONDecodeError as e:
        raise BridgeError(f"Bridge returned invalid JSON: {e}. FAIL CLOSED.")
