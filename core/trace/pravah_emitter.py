"""
Pravah Emitter — Passive Observer — TANTRA Trace Lock (Phase 6 & 7)

Pravah is the PASSIVE OBSERVER at the end of the trace spine.
It receives trace signals but does NOT:
 - Generate trace
 - Mutate trace
 - Acknowledge truth
 - Confirm execution
 - Block system operation

Pravah signal schema (strict, no extra fields):
    trace_id: str
    trace_hash: str
    source: str
    signal_type: str
    severity: str
    timestamp: str

Rules:
 - Strict schema — no extra fields
 - Core does NOT wait for Pravah
 - Execution does NOT depend on Pravah
 - System behavior unchanged if Pravah fails
 - Non-blocking with timeout
"""

import json
import logging
from typing import Optional, Dict, Any
from core.trace.trace_context import TraceContext, TraceSignal
from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

# Pravah emission timeout (seconds)
PRAVAH_TIMEOUT = 1.0

# Pravah signal log file
PRAVAH_LOG_FILE = "logs/pravah_signals.json"


class PravahEmitter:
    """
    Passive observer signal emitter.
    
    Emits trace signals to Pravah in a non-blocking, fire-and-forget manner.
    If Pravah is unavailable, system behavior is UNCHANGED.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize Pravah emitter.
        
        Args:
            log_file: Path to log Pravah signals (for demonstration).
                      In production, this would be a message queue / event stream.
        """
        self.log_file = log_file or PRAVAH_LOG_FILE
        logger.info("PravahEmitter initialized (passive observer)")
    
    def _build_signal_payload(
        self,
        trace_ctx: TraceContext,
        signal_type: str = "trace_complete",
        severity: str = "info",
    ) -> dict:
        """
        Build a strict-schema Pravah signal payload.
        
        ONLY the following fields are permitted:
            trace_id, trace_hash, source, signal_type, severity, timestamp
        
        Args:
            trace_ctx: The complete trace context
            signal_type: Type of signal (e.g., 'trace_complete', 'trace_failure')
            severity: Severity level ('info', 'warning', 'error', 'critical')
        
        Returns:
            Strict-schema signal dictionary
        """
        return {
            "trace_id": trace_ctx.trace_id,
            "trace_hash": trace_ctx.trace_hash or "unbound",
            "source": trace_ctx.source,
            "signal_type": signal_type,
            "severity": severity,
            "timestamp": get_normalized_timestamp(),
        }
    
    def emit(
        self,
        trace_ctx: TraceContext,
        signal_type: str = "trace_complete",
        severity: str = "info",
    ) -> TraceContext:
        """
        Emit a signal to Pravah (fire-and-forget, non-blocking).
        
        If emission fails, the error is logged but NOT propagated.
        System behavior is UNCHANGED regardless of Pravah status.
        
        Pravah does NOT:
         - Modify the payload
         - Acknowledge truth
         - Confirm execution
        
        Args:
            trace_ctx: Complete trace context to emit
            signal_type: Signal type for Pravah
            severity: Severity level
        
        Returns:
            NEW TraceContext with Pravah observation signal appended
        """
        payload = self._build_signal_payload(trace_ctx, signal_type, severity)
        
        # Add observation signal to trace context
        pravah_signal = TraceSignal(
            layer="pravah",
            signal_type="observation",
            timestamp=get_normalized_timestamp(),
            payload=payload,
        )
        new_ctx = trace_ctx.add_signal(pravah_signal)
        
        # Fire-and-forget emission — MUST NOT block
        try:
            self._dispatch_signal(payload)
            logger.info(
                f"Pravah signal emitted: trace_id={trace_ctx.trace_id}, "
                f"type={signal_type}"
            )
        except Exception as e:
            # NON-BLOCKING: log and continue, system unchanged
            logger.warning(
                f"Pravah emission failed (non-blocking, system unaffected): "
                f"trace_id={trace_ctx.trace_id}, error={str(e)}"
            )
        
        return new_ctx
    
    def _dispatch_signal(self, payload: dict) -> None:
        """
        Dispatch signal to Pravah backend.
        
        Current implementation: log to file.
        Production: send to message queue / event stream / Pravah API.
        
        Args:
            payload: Strict-schema signal payload
        """
        import os
        
        # Ensure logs directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Append signal to log file
        try:
            existing = []
            if os.path.exists(self.log_file):
                with open(self.log_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        existing = json.loads(content)
            
            existing.append(payload)
            
            with open(self.log_file, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            # Even file writing failure is non-blocking
            logger.warning(f"Pravah log write failed: {str(e)}")
    
    def emit_failure(
        self,
        trace_ctx: TraceContext,
        failure_reason: str,
    ) -> TraceContext:
        """
        Emit a failure signal to Pravah.
        
        Used when execution fails or is denied.
        The trace MUST still reach Pravah even on failure.
        
        Args:
            trace_ctx: Trace context at point of failure
            failure_reason: Reason for failure
        
        Returns:
            NEW TraceContext with failure observation signal appended
        """
        return self.emit(
            trace_ctx,
            signal_type="trace_failure",
            severity="error",
        )
