"""
BHIV Core Trace Spine — TANTRA Trace Lock

This package implements the unbroken trace line across all system layers:
Core → Sovereign Core → Sarathi → Execution → Pravah

Modules:
    trace_origin     — trace_id generation at entry points (Core ownership)
    trace_context    — immutable trace context propagation
    trace_binding    — cryptographic trace hash binding
    time_sync        — UTC timestamp normalization
    sovereign_core   — decision layer (ALLOW/DENY signals)
    sarathi_enforcer — enforcement gate (non-bypassable)
    pravah_emitter   — passive observer signal dispatch
"""

from core.trace.trace_origin import generate_trace_id, generate_trace_timestamp
from core.trace.trace_context import TraceContext, TraceSignal
from core.trace.trace_binding import create_trace_binding, verify_trace_binding
from core.trace.time_sync import get_normalized_timestamp, compare_timestamps
from core.trace.sovereign_core import SovereignCore
from core.trace.sarathi_enforcer import SarathiEnforcer
from core.trace.pravah_emitter import PravahEmitter

__all__ = [
    "generate_trace_id",
    "generate_trace_timestamp",
    "TraceContext",
    "TraceSignal",
    "create_trace_binding",
    "verify_trace_binding",
    "get_normalized_timestamp",
    "compare_timestamps",
    "SovereignCore",
    "SarathiEnforcer",
    "PravahEmitter",
]
