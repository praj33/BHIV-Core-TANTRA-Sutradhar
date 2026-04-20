"""
Sarathi Enforcer — Enforcement Gate — TANTRA Trace Lock (Phase 5)

Sarathi is the NON-BYPASSABLE enforcement gate between
decision and execution.

Enforcement flow:
    Core → Sovereign Core (decision) → Sarathi (enforcement) → Execution

Enforcement signal format:
    signal_type: "enforcement"
    payload:
        enforcement_status: "CLEARED" | "BLOCKED"
        validation_result: str
        failure_reason: str | None

Rules:
 - NO Core → Execution direct path
 - NO trace path skipping Sarathi
 - Execution MUST only occur AFTER Sarathi clearance
 - If no decision signal exists, Sarathi BLOCKS
"""

import logging
from typing import Optional
from core.trace.trace_context import TraceContext, TraceSignal
from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)


class SarathiEnforcementError(Exception):
    """Raised when execution is attempted without Sarathi clearance."""
    pass


class SarathiEnforcer:
    """
    Non-bypassable enforcement gate.
    
    Validates that:
    1. A Sovereign Core decision signal exists in the trace
    2. The decision is ALLOW
    3. Only then permits execution to proceed
    
    Without Sarathi clearance, execution is BLOCKED.
    """
    
    def __init__(self):
        logger.info("SarathiEnforcer initialized")
    
    def enforce(self, trace_ctx: TraceContext) -> TraceContext:
        """
        Enforce the Sarathi gate.
        
        Checks for a valid decision signal from Sovereign Core.
        If decision is ALLOW → CLEARED.
        If decision is DENY → BLOCKED.
        If no decision exists → BLOCKED (enforcement failure).
        
        Args:
            trace_ctx: Current trace context with decision signal
        
        Returns:
            NEW TraceContext with enforcement signal appended
        
        Raises:
            SarathiEnforcementError: If execution should be blocked
        """
        # Check for decision signal
        decision_signal = trace_ctx.get_signal("decision")
        
        if decision_signal is None:
            # NO DECISION — BLOCK
            enforcement_signal = TraceSignal(
                layer="sarathi",
                signal_type="enforcement",
                timestamp=get_normalized_timestamp(),
                payload={
                    "enforcement_status": "BLOCKED",
                    "validation_result": "No decision signal found in trace",
                    "failure_reason": "Missing Sovereign Core decision — Sarathi cannot clear execution",
                },
            )
            new_ctx = trace_ctx.add_signal(enforcement_signal)
            
            logger.error(
                f"SARATHI BLOCKED: trace_id={trace_ctx.trace_id} — "
                f"No decision signal found. Execution denied."
            )
            raise SarathiEnforcementError(
                f"Sarathi enforcement failed for trace {trace_ctx.trace_id}: "
                f"No Sovereign Core decision signal exists. "
                f"Execution CANNOT proceed without decision."
            )
        
        # Check decision value
        decision = decision_signal.payload.get("decision")
        
        if decision == "ALLOW":
            # CLEARED — execution may proceed
            enforcement_signal = TraceSignal(
                layer="sarathi",
                signal_type="enforcement",
                timestamp=get_normalized_timestamp(),
                payload={
                    "enforcement_status": "CLEARED",
                    "validation_result": "Decision ALLOW validated — execution permitted",
                    "failure_reason": None,
                },
            )
            new_ctx = trace_ctx.add_signal(enforcement_signal)
            
            logger.info(
                f"SARATHI CLEARED: trace_id={trace_ctx.trace_id} — "
                f"Execution permitted."
            )
            return new_ctx
        
        elif decision == "DENY":
            # BLOCKED — decision was DENY
            enforcement_signal = TraceSignal(
                layer="sarathi",
                signal_type="enforcement",
                timestamp=get_normalized_timestamp(),
                payload={
                    "enforcement_status": "BLOCKED",
                    "validation_result": "Decision DENY enforced — execution blocked",
                    "failure_reason": f"Sovereign Core denied execution. Policy: {decision_signal.payload.get('policy_reference', 'unknown')}",
                },
            )
            new_ctx = trace_ctx.add_signal(enforcement_signal)
            
            logger.warning(
                f"SARATHI BLOCKED: trace_id={trace_ctx.trace_id} — "
                f"Decision was DENY."
            )
            raise SarathiEnforcementError(
                f"Sarathi enforcement blocked trace {trace_ctx.trace_id}: "
                f"Sovereign Core decision was DENY."
            )
        
        else:
            # UNKNOWN DECISION — BLOCK
            enforcement_signal = TraceSignal(
                layer="sarathi",
                signal_type="enforcement",
                timestamp=get_normalized_timestamp(),
                payload={
                    "enforcement_status": "BLOCKED",
                    "validation_result": f"Unknown decision value: {decision}",
                    "failure_reason": "Invalid decision signal from Sovereign Core",
                },
            )
            new_ctx = trace_ctx.add_signal(enforcement_signal)
            
            logger.error(
                f"SARATHI BLOCKED: trace_id={trace_ctx.trace_id} — "
                f"Unknown decision value: {decision}"
            )
            raise SarathiEnforcementError(
                f"Sarathi enforcement failed for trace {trace_ctx.trace_id}: "
                f"Unknown decision value '{decision}'."
            )
    
    @staticmethod
    def assert_cleared(trace_ctx: TraceContext) -> bool:
        """
        Assert that Sarathi enforcement has cleared this trace.
        
        Can be called at any point to verify that the trace
        passed through Sarathi before reaching execution.
        
        Args:
            trace_ctx: Trace context to check
        
        Returns:
            True if Sarathi cleared the trace
        
        Raises:
            SarathiEnforcementError: If enforcement was not cleared
        """
        enforcement_signal = trace_ctx.get_signal("enforcement")
        
        if enforcement_signal is None:
            raise SarathiEnforcementError(
                f"Trace {trace_ctx.trace_id} has NO Sarathi enforcement signal. "
                f"Execution bypassed Sarathi — this is a VIOLATION."
            )
        
        status = enforcement_signal.payload.get("enforcement_status")
        if status != "CLEARED":
            raise SarathiEnforcementError(
                f"Trace {trace_ctx.trace_id} was not cleared by Sarathi. "
                f"Status: {status}"
            )
        
        return True
