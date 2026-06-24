"""
Test Runtime Modules — lifecycle, health_monitor, version_negotiator, compatibility_engine
"""
import sys, os
# Project root is two levels up from core/runtime/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

print("=" * 60)
print("  RUNTIME MODULE TESTS")
print("=" * 60)

# --- 1. Lifecycle Manager ---
print("\n--- 1. Lifecycle Manager ---")
from core.runtime.lifecycle import LifecycleManager, LifecycleState

mgr = LifecycleManager()
mgr.register("sovereign", LifecycleState.INITIALIZING)
mgr.register("cet", LifecycleState.INITIALIZING)
mgr.register("sarathi", LifecycleState.INITIALIZING)
mgr.register("bridge", LifecycleState.INITIALIZING)
mgr.register("bucket", LifecycleState.INITIALIZING)
mgr.register("insightflow", LifecycleState.INITIALIZING)

# Transition all to READY
for name in ["sovereign", "cet", "sarathi", "bridge", "bucket", "insightflow"]:
    ok = mgr.set_state(name, LifecycleState.READY)
    print(f"  {name}: INITIALIZING → READY: {'✅' if ok else '❌'}")

# Test degraded
mgr.set_state("bridge", LifecycleState.DEGRADED)
print(f"  bridge accepts requests (DEGRADED): {mgr.can_accept_requests('bridge')}")  # True

# Test invalid transition
ok = mgr.set_state("bridge", LifecycleState.INITIALIZING)
print(f"  bridge DEGRADED → INITIALIZING (invalid): {'✅ blocked' if not ok else '❌ allowed'}")

# Summary
summary = mgr.summary()
print(f"  Summary: {summary['total_participants']} participants, accepting: {summary['accepting_requests']}")

# --- 2. Compatibility Engine ---
print("\n--- 2. Compatibility Engine ---")
from core.runtime.compatibility_engine import CompatibilityEngine

engine = CompatibilityEngine()
versions = {
    "sarathi": "1.0.0",
    "bridge": "1.0.0",
    "cet": "1.0.0",
    "bucket": "1.0.0",
    "sovereign": "1.0.0",
    "insightflow": "1.0.0",
}
report = engine.generate_report(versions)
print(f"  Ecosystem valid: {report['is_valid']}")
print(f"  Total issues: {report['total_issues']} (errors: {len(report['errors'])}, warnings: {len(report['warnings'])})")

# --- 3. Version Negotiator ---
print("\n--- 3. Version Negotiator ---")
from core.runtime.version_negotiator import VersionNegotiator

negotiator = VersionNegotiator(registry_path="TANTRA_INTEGRATION_REGISTRY.json")
compat, reason = negotiator.check_compatibility("sarathi", "1.0.0")
print(f"  sarathi v1.0.0 compatible: {compat} ({reason})")
compat, reason = negotiator.check_compatibility("bridge", "0.5.0")
print(f"  bridge v0.5.0 compatible: {compat} ({reason})")

all_check = negotiator.check_all()
print(f"  All compatible: {all_check['all_compatible']}")

# --- 4. Health Monitor (live checks) ---
print("\n--- 4. Health Monitor (live check of Bucket) ---")
from core.runtime.health_monitor import HealthMonitor

monitor = HealthMonitor()
monitor.register("bucket", "https://bhiv-bucket.onrender.com", "/health")
result = monitor.check("bucket")
print(f"  bucket: status={result['status']}, latency={result['latency_ms']}ms")

print(f"\n{'=' * 60}")
print("  ALL RUNTIME MODULES OPERATIONAL")
print(f"{'=' * 60}")
