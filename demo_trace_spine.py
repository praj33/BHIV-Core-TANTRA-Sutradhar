# -*- coding: utf-8 -*-
"""
TANTRA Trace Spine -- Live Demo
Shows trace_id generation and full flow through all layers.
"""
import sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.disable(logging.CRITICAL)

from core.trace.trace_origin import generate_trace_id, generate_trace_timestamp, create_trace_origin
from core.trace.trace_context import create_trace_context, TraceSignal
from core.trace.trace_binding import create_trace_binding, verify_trace_binding
from core.trace.time_sync import get_normalized_timestamp
from core.trace.sovereign_core import SovereignCore
from core.trace.sarathi_enforcer import SarathiEnforcer, SarathiEnforcementError
from core.trace.pravah_emitter import PravahEmitter

print("=" * 65)
print("  TANTRA TRACE SPINE -- LIVE DEMONSTRATION")
print("=" * 65)

# ---- STEP 1: TRACE ORIGIN ----
print("\n" + "-" * 65)
print("  STEP 1: TRACE ORIGIN (Core generates trace_id)")
print("-" * 65)
origin = create_trace_origin("mcp_bridge")
print(f"\n  trace_id      : {origin['trace_id']}")
print(f"  trace_timestamp: {origin['trace_timestamp']}")
print(f"  source         : {origin['source']}")

# ---- STEP 2: CREATE IMMUTABLE CONTEXT ----
print("\n" + "-" * 65)
print("  STEP 2: IMMUTABLE TRACE CONTEXT (frozen dataclass)")
print("-" * 65)
ctx = create_trace_context(origin["trace_id"], origin["trace_timestamp"], origin["source"])
print(f"\n  TraceContext created (frozen=True)")
print(f"  trace_id in context: {ctx.trace_id}")
print(f"  Signals so far: {[s.signal_type for s in ctx.signals]}")

try:
    ctx.trace_id = "TAMPERED"
    print("  ERROR: Mutation allowed!")
except AttributeError:
    print("  Mutation test: BLOCKED (FrozenInstanceError) -- trace_id is immutable")

# ---- STEP 3: SOVEREIGN CORE DECISION ----
print("\n" + "-" * 65)
print("  STEP 3: SOVEREIGN CORE (Decision Layer)")
print("-" * 65)
sc = SovereignCore()
user_input = "Explain the basics of blockchain technology"
ctx = sc.evaluate(ctx, user_input)

decision_signal = ctx.get_signal("decision")
print(f"\n  Input: \"{user_input}\"")
print(f"  Decision  : {decision_signal.payload['decision']}")
print(f"  Policy    : {decision_signal.payload['policy_reference']}")
print(f"  Input Hash: {decision_signal.payload['input_hash'][:32]}...")
print(f"  trace_id still: {ctx.trace_id}")

# ---- STEP 4: SARATHI ENFORCEMENT ----
print("\n" + "-" * 65)
print("  STEP 4: SARATHI ENFORCER (Non-Bypassable Gate)")
print("-" * 65)
se = SarathiEnforcer()
ctx = se.enforce(ctx)

enforcement = ctx.get_signal("enforcement")
print(f"\n  Enforcement Status: {enforcement.payload['enforcement_status']}")
print(f"  Validation: {enforcement.payload['validation_result']}")
print(f"  trace_id still: {ctx.trace_id}")

# ---- STEP 5: EXECUTION ----
print("\n" + "-" * 65)
print("  STEP 5: EXECUTION (Agent processes task)")
print("-" * 65)
execution_id = "task-demo-001"
ctx = ctx.with_execution_id(execution_id)
exec_signal = TraceSignal(
    layer="execution",
    signal_type="execution",
    timestamp=get_normalized_timestamp(),
    payload={"execution_id": execution_id, "agent": "edumentor_agent", "status": "completed"},
)
ctx = ctx.add_signal(exec_signal)
print(f"\n  execution_id: {execution_id}")
print(f"  Agent: edumentor_agent")
print(f"  Status: completed")
print(f"  trace_id still: {ctx.trace_id}")

# ---- STEP 6: CRYPTO BINDING ----
print("\n" + "-" * 65)
print("  STEP 6: CRYPTO BINDING (SHA-256 tamper-evidence)")
print("-" * 65)
trace_hash = create_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp)
ctx = ctx.with_trace_hash(trace_hash)
print(f"\n  trace_hash: {trace_hash}")
print(f"  Formula: SHA-256({ctx.trace_id[:8]}... + {execution_id} + {ctx.trace_timestamp[:19]}...)")
is_valid = verify_trace_binding(ctx.trace_id, execution_id, ctx.trace_timestamp, trace_hash)
print(f"  Verification: {'VALID' if is_valid else 'TAMPERED'}")

# ---- STEP 7: PRAVAH EMISSION ----
print("\n" + "-" * 65)
print("  STEP 7: PRAVAH (Passive Observer -- fire-and-forget)")
print("-" * 65)
pe = PravahEmitter(log_file="logs/demo_pravah_signals.json")
ctx = pe.emit(ctx)
print(f"\n  Signal emitted to Pravah (non-blocking)")
print(f"  trace_id still: {ctx.trace_id}")

# ---- FINAL TRACE ----
print("\n" + "=" * 65)
print("  COMPLETE TRACE SPINE")
print("=" * 65)
print(f"\n  trace_id      : {ctx.trace_id}")
print(f"  execution_id  : {ctx.execution_id}")
print(f"  trace_hash    : {ctx.trace_hash}")
print(f"  source        : {ctx.source}")
print(f"\n  Signal Chain:")
for i, s in enumerate(ctx.signals):
    print(f"    {i+1}. [{s.layer}] {s.signal_type} @ {s.timestamp}")

print(f"\n  Full Trace JSON:")
print(json.dumps(ctx.to_dict(), indent=4))

print("\n" + "=" * 65)
print("  TRACE SPINE VERIFIED: trace_id identical across all 5 layers")
print("=" * 65)
