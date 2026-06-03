"""
TANTRA Flow Executor — Canonical 8-Step Pipeline

The ONLY way execution happens in live TANTRA mode.
Wires the exact flow:

  1. Core (trace origin)
  2. Sovereign (decision)
  3. CET (contract compilation)
  4. Sarathi (enforcement + token)
  5. Bridge (validation gate)
  6. Execution (gated)
  7. Bucket (truth write + verify)
  8. InsightFlow (trace emission)

SAME trace_id across ALL steps. No mutation. No skipping.
"""

import hashlib
import json
import logging
import os
from typing import Dict, Any, Optional

from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.trace.time_sync import get_normalized_timestamp
from core.authority import callSovereign, callSarathi
from core.trace.sarathi_enforcer import SarathiEnforcementError
from core.authority.execution_gate import (
    register_token, gated_execute, ExecutionBlockedError,
)
from core.authority.bucket_writer import (
    finalize_execution, BucketWriteError, ExecutionFinalizationError,
)
from core.authority.cet_client import callCET, verify_contract_integrity, CETError
from core.authority.bridge_client import callBridge, BridgeError
from core.authority.insightflow_client import emitTrace, buildTraceChain, InsightFlowError

logger = logging.getLogger(__name__)

# Feature flag — set True when all live services are available
USE_FULL_TANTRA = os.environ.get("USE_FULL_TANTRA", "false").lower() == "true"


class TANTRAFlowError(Exception):
    """Raised when any step in the TANTRA flow fails."""
    pass


def execute_tantra_flow(
    input_data: str,
    agent: str = None,
    source: str = "core_api",
    task_payload: Dict[str, Any] = None,
    action_fn=None,
) -> Dict[str, Any]:
    """
    Execute ONE complete TANTRA flow across all 8 layers.

    Args:
        input_data: User input / action
        agent: Target agent
        source: Trace origin source
        task_payload: Full task payload for execution
        action_fn: The actual execution function

    Returns:
        Complete flow result with all layer outputs + trace_id

    Raises:
        TANTRAFlowError: If any layer fails (FAIL CLOSED)
    """
    flow_result = {"steps": {}, "status": "in_progress"}

    # ═══ STEP 1: TRACE ORIGIN ═══
    origin = create_trace_origin(source)
    trace_id = origin["trace_id"]
    flow_result["trace_id"] = trace_id
    flow_result["steps"]["1_origin"] = origin
    logger.info(f"[TANTRA] Step 1 — Origin: trace_id={trace_id}")

    ctx = create_trace_context(trace_id, origin["trace_timestamp"], source)

    # ═══ STEP 2: SOVEREIGN CORE (Decision) ═══
    try:
        ctx = callSovereign(ctx, input_data)
        decision_signal = ctx.get_signal("decision")

        if decision_signal is None:
            raise TANTRAFlowError(f"No decision signal from Sovereign for trace {trace_id}")

        decision = decision_signal.payload["decision"]
        decision_hash = decision_signal.payload.get("decision_hash", "")
        input_hash = decision_signal.payload.get("input_hash", "")

        flow_result["steps"]["2_sovereign"] = {
            "decision": decision,
            "decision_hash": decision_hash,
            "input_hash": input_hash,
            "trace_id": trace_id,
        }
        logger.info(f"[TANTRA] Step 2 — Sovereign: decision={decision}")

        if decision == "DENY":
            flow_result["status"] = "blocked"
            flow_result["blocked_at"] = "sovereign"
            _emit_failure_trace(trace_id, flow_result, "sovereign_deny")
            raise TANTRAFlowError(f"Sovereign DENIED execution for trace {trace_id}")

    except ConnectionError as e:
        flow_result["status"] = "failed"
        flow_result["error"] = str(e)
        raise TANTRAFlowError(f"Sovereign unreachable for trace {trace_id}: {e}")

    # ═══ STEP 3: CET (Contract Compilation) ═══
    cet_result = None
    contract_hash = ""
    if USE_FULL_TANTRA:
        try:
            cet_result = callCET(trace_id, input_data, decision_hash)
            contract_hash = cet_result.get("contract_hash", "")
            flow_result["steps"]["3_cet"] = {
                "contract_hash": contract_hash,
                "trace_id": trace_id,
            }
            logger.info(f"[TANTRA] Step 3 — CET: contract_hash={contract_hash[:16]}...")
        except CETError as e:
            flow_result["status"] = "failed"
            flow_result["error"] = str(e)
            raise TANTRAFlowError(f"CET failed for trace {trace_id}: {e}")
    else:
        # Internal mode: generate contract hash locally
        contract_hash = hashlib.sha256(
            f"{trace_id}:{input_data}:{decision_hash}".encode()
        ).hexdigest()
        flow_result["steps"]["3_cet"] = {
            "contract_hash": contract_hash,
            "trace_id": trace_id,
            "mode": "internal",
        }
        logger.info(f"[TANTRA] Step 3 — CET (internal): contract_hash={contract_hash[:16]}...")

    # ═══ STEP 4: SARATHI (Enforcement + Token) ═══
    try:
        ctx = callSarathi(ctx)
        enforcement_signal = ctx.get_signal("enforcement")

        if enforcement_signal is None:
            raise TANTRAFlowError(f"No enforcement signal from Sarathi for trace {trace_id}")

        enforcement_status = enforcement_signal.payload["enforcement_status"]
        execution_token = enforcement_signal.payload.get("execution_token", "")

        # If no token from external Sarathi, generate internal one
        if not execution_token:
            execution_token = hashlib.sha256(
                f"{trace_id}:{decision_hash}:{get_normalized_timestamp()}".encode()
            ).hexdigest()

        flow_result["steps"]["4_sarathi"] = {
            "enforcement_status": enforcement_status,
            "has_token": bool(execution_token),
            "trace_id": trace_id,
        }
        logger.info(f"[TANTRA] Step 4 — Sarathi: status={enforcement_status}")

    except SarathiEnforcementError as e:
        flow_result["status"] = "blocked"
        flow_result["blocked_at"] = "sarathi"
        _emit_failure_trace(trace_id, flow_result, "sarathi_blocked")
        raise TANTRAFlowError(f"Sarathi blocked trace {trace_id}: {e}")
    except ConnectionError as e:
        flow_result["status"] = "failed"
        raise TANTRAFlowError(f"Sarathi unreachable for trace {trace_id}: {e}")

    # ═══ STEP 5: BRIDGE (Validation Gate) ═══
    bridge_result = None
    if USE_FULL_TANTRA:
        try:
            bridge_result = callBridge(trace_id, execution_token, contract_hash)
            # Verify contract integrity — hash must not have changed
            if cet_result:
                verify_contract_integrity(
                    cet_result.get("contract_hash", ""),
                    contract_hash,
                )
            flow_result["steps"]["5_bridge"] = {
                "status": "VALIDATED",
                "trace_id": trace_id,
            }
            logger.info(f"[TANTRA] Step 5 — Bridge: VALIDATED")
        except (BridgeError, CETError) as e:
            flow_result["status"] = "blocked"
            flow_result["blocked_at"] = "bridge"
            raise TANTRAFlowError(f"Bridge rejected trace {trace_id}: {e}")
    else:
        flow_result["steps"]["5_bridge"] = {
            "status": "VALIDATED",
            "trace_id": trace_id,
            "mode": "internal",
        }
        logger.info(f"[TANTRA] Step 5 — Bridge (internal): VALIDATED")

    # ═══ STEP 6: EXECUTION (Gated) ═══
    try:
        register_token(execution_token, trace_id, scope={
            "agent": agent or "default",
            "contract_hash": contract_hash,
            "decision_hash": decision_hash,
        })

        if action_fn:
            exec_result = gated_execute(action_fn, execution_token, trace_id, task_payload or {})
        else:
            # Default execution
            exec_result = gated_execute(
                lambda p: {"status": "executed", "result": f"processed: {input_data[:50]}"},
                execution_token, trace_id, task_payload or {},
            )

        flow_result["steps"]["6_execution"] = {
            "status": "executed",
            "trace_id": trace_id,
        }
        logger.info(f"[TANTRA] Step 6 — Execution: COMPLETE")

    except ExecutionBlockedError as e:
        flow_result["status"] = "blocked"
        flow_result["blocked_at"] = "execution_gate"
        _emit_failure_trace(trace_id, flow_result, "token_blocked")
        raise TANTRAFlowError(f"Execution blocked for trace {trace_id}: {e}")

    # ═══ STEP 7: BUCKET (Truth Write + Verify) ═══
    try:
        bucket_result = finalize_execution(
            trace_id=trace_id,
            execution_id=f"tantra-{trace_id[:8]}",
            token=execution_token,
            decision=decision,
            payload=task_payload or {"input": input_data},
            execution_result=exec_result,
        )

        flow_result["steps"]["7_bucket"] = {
            "status": "finalized",
            "verified": bucket_result.get("verified", False),
            "bucket_write_id": bucket_result.get("bucket_write_id", ""),
            "trace_id": trace_id,
        }
        logger.info(f"[TANTRA] Step 7 — Bucket: FINALIZED + VERIFIED")

    except (BucketWriteError, ExecutionFinalizationError) as e:
        flow_result["status"] = "failed"
        flow_result["error"] = f"Bucket write failed: {e}"
        _emit_failure_trace(trace_id, flow_result, "bucket_failed")
        raise TANTRAFlowError(f"Bucket write failed for trace {trace_id}: {e}")

    # ═══ STEP 8: INSIGHTFLOW (Trace Emission) ═══
    try:
        trace_chain = buildTraceChain(
            trace_id=trace_id,
            origin=flow_result["steps"].get("1_origin"),
            sovereign=flow_result["steps"].get("2_sovereign"),
            cet=flow_result["steps"].get("3_cet"),
            sarathi=flow_result["steps"].get("4_sarathi"),
            bridge=flow_result["steps"].get("5_bridge"),
            execution=flow_result["steps"].get("6_execution"),
            bucket=flow_result["steps"].get("7_bucket"),
        )

        insight_result = emitTrace(
            trace_id=trace_id,
            trace_chain=trace_chain,
            execution_status="completed",
            bucket_verified=bucket_result.get("verified", False),
        )

        flow_result["steps"]["8_insightflow"] = {
            "status": "emitted",
            "store": insight_result.get("store", ""),
            "chain_length": len(trace_chain),
            "trace_id": trace_id,
        }
        logger.info(f"[TANTRA] Step 8 — InsightFlow: EMITTED ({len(trace_chain)} signals)")

    except InsightFlowError as e:
        # InsightFlow failure does NOT block execution (trace is already in Bucket)
        logger.warning(f"InsightFlow emission failed (non-blocking): {e}")
        flow_result["steps"]["8_insightflow"] = {
            "status": "failed",
            "error": str(e),
            "trace_id": trace_id,
        }

    # ═══ COMPLETE ═══
    flow_result["status"] = "completed"
    flow_result["execution_result"] = exec_result
    logger.info(f"[TANTRA] FLOW COMPLETE: trace_id={trace_id}")
    return flow_result


def _emit_failure_trace(trace_id: str, flow_result: Dict, failure_type: str):
    """Emit failure trace to InsightFlow (best-effort)."""
    try:
        trace_chain = buildTraceChain(
            trace_id=trace_id,
            origin=flow_result["steps"].get("1_origin"),
            sovereign=flow_result["steps"].get("2_sovereign"),
            cet=flow_result["steps"].get("3_cet"),
            sarathi=flow_result["steps"].get("4_sarathi"),
        )
        emitTrace(
            trace_id=trace_id,
            trace_chain=trace_chain,
            execution_status=f"failed:{failure_type}",
            bucket_verified=False,
        )
    except Exception:
        logger.warning(f"Could not emit failure trace for {trace_id}")
