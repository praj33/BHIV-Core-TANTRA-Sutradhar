"""
Sovereign Core — Decision Layer — TANTRA Trace Lock (Phase 4)

The Sovereign Core is the decision gate in the trace spine.
It observes input and emits ALLOW/DENY decision signals
based on policy evaluation.

Decision signal format:
    signal_type: "decision"
    payload:
        decision: "ALLOW" | "DENY"
        policy_reference: str
        input_hash: SHA-256(input_data)

Rules:
 - Does NOT modify execution logic
 - Does NOT introduce new authority
 - Only observes, evaluates, and records decisions
 - Decision signal MUST be present before Sarathi enforcement
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from core.trace.trace_context import TraceContext, TraceSignal
from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)


class SovereignCore:
    """
    Decision layer that evaluates input against policies
    and emits ALLOW/DENY signals into the trace context.
    
    This is NOT an execution authority — it is a truth recorder.
    """
    
    # Default policy — ALLOW all (can be extended with real policy logic)
    DEFAULT_POLICY = "bhiv.core.default_allow_policy"
    
    def __init__(self, policies: Optional[Dict[str, Any]] = None):
        """
        Initialize Sovereign Core with optional policy configuration.
        
        Args:
            policies: Dictionary of policy rules. If None, uses default allow policy.
        """
        self.policies = policies or {}
        logger.info("SovereignCore initialized")
    
    def _compute_input_hash(self, input_data: str) -> str:
        """
        Compute SHA-256 hash of the input data for tamper evidence.
        
        Args:
            input_data: Raw input string
        
        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(input_data.encode("utf-8")).hexdigest()
    
    def _evaluate_policy(self, input_data: str, context: Dict[str, Any]) -> tuple:
        """
        Evaluate input against policies.
        
        Args:
            input_data: The raw input to evaluate
            context: Additional context (agent, tags, etc.)
        
        Returns:
            Tuple of (decision: str, policy_reference: str)
            decision is "ALLOW" or "DENY"
        """
        # Check for explicit deny policies
        for policy_name, policy_rule in self.policies.items():
            if policy_rule.get("type") == "deny":
                deny_keywords = policy_rule.get("deny_keywords", [])
                if any(kw.lower() in input_data.lower() for kw in deny_keywords):
                    logger.info(f"Policy DENY triggered: {policy_name}")
                    return "DENY", policy_name
        
        # Default: ALLOW
        return "ALLOW", self.DEFAULT_POLICY
    
    def evaluate(
        self,
        trace_ctx: TraceContext,
        input_data: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TraceContext:
        """
        Evaluate input and emit a decision signal into the trace.
        
        This is the primary entry point for the Sovereign Core.
        
        Args:
            trace_ctx: Current trace context (immutable)
            input_data: The raw input being processed
            context: Additional context for policy evaluation
        
        Returns:
            NEW TraceContext with the decision signal appended
        """
        context = context or {}
        
        # Compute input hash for tamper evidence
        input_hash = self._compute_input_hash(input_data)
        
        # Evaluate policy
        decision, policy_reference = self._evaluate_policy(input_data, context)
        
        # Create decision signal
        decision_signal = TraceSignal(
            layer="sovereign_core",
            signal_type="decision",
            timestamp=get_normalized_timestamp(),
            payload={
                "decision": decision,
                "policy_reference": policy_reference,
                "input_hash": input_hash,
            },
        )
        
        logger.info(
            f"Sovereign Core decision: trace_id={trace_ctx.trace_id}, "
            f"decision={decision}, policy={policy_reference}"
        )
        
        # Return NEW context with signal (immutability preserved)
        return trace_ctx.add_signal(decision_signal)
