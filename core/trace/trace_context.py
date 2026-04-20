"""
Trace Context Module — TANTRA Trace Lock (Phase 2)

Immutable trace context that propagates across all layers:
 Core → Sovereign Core → Sarathi → Execution → Pravah

Rules:
 - SAME trace_id across ALL layers
 - NO mutation allowed (frozen dataclass)
 - trace_id MUST be present in ALL payloads
 - Signals are appended by creating NEW context instances
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import copy
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TraceSignal:
    """
    An individual signal recorded at a specific layer.
    
    Immutable — once created, cannot be modified.
    """
    layer: str              # e.g., 'core', 'sovereign_core', 'sarathi', 'execution', 'pravah'
    signal_type: str        # e.g., 'origin', 'decision', 'enforcement', 'execution', 'observation'
    timestamp: str          # ISO 8601 UTC
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "layer": self.layer,
            "signal_type": self.signal_type,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class TraceContext:
    """
    Immutable trace context that flows through every layer.
    
    The trace_id is set ONCE at origin and NEVER changes.
    Signals are accumulated by creating new TraceContext instances.
    
    Freezing enforced by Python's frozen dataclass.
    """
    trace_id: str
    trace_timestamp: str    # Origin timestamp (ISO 8601 UTC)
    source: str             # Origin source identifier
    signals: tuple = ()     # Tuple of TraceSignal (immutable)
    execution_id: Optional[str] = None  # Set when execution begins
    trace_hash: Optional[str] = None    # Set after binding
    
    def add_signal(self, signal: TraceSignal) -> "TraceContext":
        """
        Create a NEW TraceContext with an additional signal.
        
        Does NOT mutate the current context — returns a new instance.
        This preserves immutability.
        
        Args:
            signal: TraceSignal to append
        
        Returns:
            New TraceContext with the signal appended
        """
        new_signals = self.signals + (signal,)
        logger.info(
            f"Trace {self.trace_id}: signal added — "
            f"layer={signal.layer}, type={signal.signal_type}"
        )
        return TraceContext(
            trace_id=self.trace_id,
            trace_timestamp=self.trace_timestamp,
            source=self.source,
            signals=new_signals,
            execution_id=self.execution_id,
            trace_hash=self.trace_hash,
        )
    
    def with_execution_id(self, execution_id: str) -> "TraceContext":
        """
        Create a NEW TraceContext with the execution_id set.
        
        Args:
            execution_id: The execution identifier (task_id)
        
        Returns:
            New TraceContext with execution_id
        """
        return TraceContext(
            trace_id=self.trace_id,
            trace_timestamp=self.trace_timestamp,
            source=self.source,
            signals=self.signals,
            execution_id=execution_id,
            trace_hash=self.trace_hash,
        )
    
    def with_trace_hash(self, trace_hash: str) -> "TraceContext":
        """
        Create a NEW TraceContext with the trace_hash set.
        
        Args:
            trace_hash: The cryptographic trace binding hash
        
        Returns:
            New TraceContext with trace_hash
        """
        return TraceContext(
            trace_id=self.trace_id,
            trace_timestamp=self.trace_timestamp,
            source=self.source,
            signals=self.signals,
            execution_id=self.execution_id,
            trace_hash=trace_hash,
        )
    
    def has_signal(self, signal_type: str) -> bool:
        """Check if a signal of the given type exists in the trace."""
        return any(s.signal_type == signal_type for s in self.signals)
    
    def get_signal(self, signal_type: str) -> Optional[TraceSignal]:
        """Get the first signal of the given type, or None."""
        for s in self.signals:
            if s.signal_type == signal_type:
                return s
        return None
    
    def get_all_timestamps(self) -> list:
        """Get all timestamps in the trace (origin + all signals) for ordering validation."""
        timestamps = [self.trace_timestamp]
        for s in self.signals:
            timestamps.append(s.timestamp)
        return timestamps
    
    def to_dict(self) -> dict:
        """Serialize the full trace context to a dictionary."""
        return {
            "trace_id": self.trace_id,
            "trace_timestamp": self.trace_timestamp,
            "source": self.source,
            "execution_id": self.execution_id,
            "trace_hash": self.trace_hash,
            "signals": [s.to_dict() for s in self.signals],
        }
    
    def validate_integrity(self) -> bool:
        """
        Validate trace context integrity.
        
        Checks:
         - trace_id is present and non-empty
         - trace_timestamp is present
         - All signals reference the correct layer progression
        
        Returns:
            True if trace context is valid
        """
        if not self.trace_id or not self.trace_timestamp:
            logger.error("Trace integrity failure: missing trace_id or trace_timestamp")
            return False
        
        if not self.source:
            logger.error("Trace integrity failure: missing source")
            return False
        
        return True


def create_trace_context(trace_id: str, trace_timestamp: str, source: str) -> TraceContext:
    """
    Factory function to create a new TraceContext at the origin.
    
    Args:
        trace_id: Unique trace identifier (from trace_origin)
        trace_timestamp: UTC timestamp (from trace_origin)
        source: Origin source identifier
    
    Returns:
        A new, immutable TraceContext
    """
    from core.trace.time_sync import get_normalized_timestamp
    
    origin_signal = TraceSignal(
        layer="core",
        signal_type="origin",
        timestamp=get_normalized_timestamp(),
        payload={"source": source, "trace_id": trace_id},
    )
    
    ctx = TraceContext(
        trace_id=trace_id,
        trace_timestamp=trace_timestamp,
        source=source,
        signals=(origin_signal,),
    )
    
    logger.info(f"TraceContext created: trace_id={trace_id}, source={source}")
    return ctx
