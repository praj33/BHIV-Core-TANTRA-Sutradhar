"""
Generate Trace ID — All 3 Methods
Run: python generate_traceid.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.trace.trace_origin import generate_trace_id, generate_trace_timestamp, create_trace_origin

print("=" * 55)
print("  TRACE ID GENERATION — 3 METHODS")
print("=" * 55)

# METHOD 1: Full origin record (recommended)
print("\n--- Method 1: Full Origin Record (recommended) ---")
origin = create_trace_origin("my_app")
print(f"  trace_id      : {origin['trace_id']}")
print(f"  trace_timestamp: {origin['trace_timestamp']}")
print(f"  source         : {origin['source']}")

# METHOD 2: Just the trace_id
print("\n--- Method 2: Just the trace_id ---")
tid = generate_trace_id()
print(f"  trace_id: {tid}")

# METHOD 3: trace_id + timestamp separately
print("\n--- Method 3: trace_id + timestamp separately ---")
tid2 = generate_trace_id()
ts2 = generate_trace_timestamp()
print(f"  trace_id : {tid2}")
print(f"  timestamp: {ts2}")

print("\n" + "=" * 55)
print(f"  3 unique trace_ids generated successfully")
print("=" * 55)
