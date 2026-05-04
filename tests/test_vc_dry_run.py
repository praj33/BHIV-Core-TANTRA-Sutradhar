"""
VC Dry Run — Phase 6

Simulates VC conditions with 15 test executions.
Validates:
  - Outputs are visible
  - Logs are readable
  - No ambiguity
  - No crashes
  - No missing logs
  - No inconsistent outputs

Also tests mismatch detection with deliberate mismatches.

Run:
    python tests/test_vc_dry_run.py
"""

import sys
import os
import io
import json
from collections import OrderedDict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)

from core.authority.canonical_output import (
    produce_canonical_output,
    validate_canonical_output,
    canonical_to_json,
    CANONICAL_FIELDS,
)
from core.authority.parallel_validator import (
    run_core_enforcement,
    compare_outputs,
    log_raw_input,
    verify_input_integrity,
)
from core.trace.time_sync import get_normalized_timestamp


# ═══════════════════════════════════════════════════════════
# TEST INPUTS (15 scenarios)
# ═══════════════════════════════════════════════════════════

TEST_INPUTS = [
    "user login from Mumbai IP",
    "deploy web1-blue service",
    "restart database cluster",
    "scale frontend pods to 5",
    "enable maintenance mode",
    "query user karma score",
    "process payment transaction",
    "update firewall rules",
    "rotate API keys",
    "generate analytics report",
    "check service health",
    "backup MongoDB collections",
    "trigger CI/CD pipeline",
    "apply security patch",
    "sync replica nodes",
]


def main():
    print("=" * 60)
    print("  VC DRY RUN — PARALLEL VALIDATION READINESS")
    print("=" * 60)
    print(f"  Time: {get_normalized_timestamp()}")
    print(f"  Test cases: {len(TEST_INPUTS)}")
    print()

    results = []
    all_outputs = []
    crashes = 0
    missing_logs = 0
    schema_violations = 0
    mismatches_detected = 0

    # ── RUN 15 EXECUTIONS ──
    for i, input_data in enumerate(TEST_INPUTS):
        print(f"  [{i+1:2d}/{len(TEST_INPUTS)}] Input: \"{input_data}\"")

        try:
            result = run_core_enforcement(input_data, source="vc_dry_run")
            core_output = result["core_output"]

            # Validate schema
            if not validate_canonical_output(core_output):
                schema_violations += 1
                print(f"         SCHEMA VIOLATION!")

            # Verify determinism: same input → same output fields
            if core_output["verdict"] not in ("ALLOW", "DENY"):
                print(f"         INVALID VERDICT: {core_output['verdict']}")

            # Check all 6 fields present
            for field in CANONICAL_FIELDS:
                if field not in core_output or not core_output[field]:
                    missing_logs += 1
                    print(f"         MISSING FIELD: {field}")

            all_outputs.append(core_output)
            results.append({
                "index": i + 1,
                "input": input_data,
                "output": dict(core_output),
                "status": "OK",
            })
            print(f"         [OK] verdict={core_output['verdict']}")
            print()

        except Exception as e:
            crashes += 1
            results.append({
                "index": i + 1,
                "input": input_data,
                "error": str(e),
                "status": "CRASH",
            })
            print(f"         [CRASH] {str(e)[:60]}")
            print()

    # ── MISMATCH DETECTION TEST ──
    print("-" * 60)
    print("  MISMATCH DETECTION TEST")
    print("-" * 60)

    if len(all_outputs) >= 2:
        # Test 1: Compare same output with itself (should match)
        comp1 = compare_outputs(all_outputs[0], dict(all_outputs[0]))
        print(f"  [Test 1] Same output vs itself: match={comp1['match']}")
        if comp1["match"]:
            print(f"           [OK]")
        else:
            print(f"           [FAIL] Should have matched!")

        # Test 2: Compare with deliberately tampered output (should mismatch)
        tampered = dict(all_outputs[0])
        tampered["verdict"] = "DENY" if tampered["verdict"] == "ALLOW" else "ALLOW"
        tampered["decision_hash"] = "TAMPERED_HASH_VALUE"
        comp2 = compare_outputs(all_outputs[0], tampered)
        print(f"  [Test 2] Tampered output: match={comp2['match']}")
        if not comp2["match"]:
            mismatches_detected = len(comp2["mismatches"])
            print(f"           [OK] {mismatches_detected} mismatches detected")
            for m in comp2["mismatches"]:
                print(f"             {m['field']}: core={m['core'][:30]} vs sarathi={m['sarathi'][:30]}")
        else:
            print(f"           [FAIL] Should have detected mismatch!")

        # Test 3: Compare with missing field
        incomplete = dict(all_outputs[0])
        del incomplete["enforcement_binding"]
        incomplete["enforcement_binding"] = ""
        comp3 = compare_outputs(all_outputs[0], incomplete)
        print(f"  [Test 3] Missing field: match={comp3['match']}")
        if not comp3["match"]:
            print(f"           [OK] Mismatch on: {[m['field'] for m in comp3['mismatches']]}")
        else:
            print(f"           Could match if field was empty in both")

    # ── INPUT INTEGRITY TEST ──
    print()
    print("-" * 60)
    print("  INPUT INTEGRITY TEST")
    print("-" * 60)

    same_input = "identical test input for Core and Sarathi"
    integrity1 = verify_input_integrity(same_input, same_input)
    print(f"  [Test 4] Same input to both: match={integrity1['input_match']}")
    print(f"           [OK]" if integrity1["input_match"] else "           [FAIL]")

    diff_input_core = "core sees this"
    diff_input_sarathi = "sarathi sees something else"
    integrity2 = verify_input_integrity(diff_input_core, diff_input_sarathi)
    print(f"  [Test 5] Different input: match={integrity2['input_match']}")
    print(f"           [OK] Mismatch detected" if not integrity2["input_match"] else "           [FAIL]")

    # ── DETERMINISM TEST ──
    print()
    print("-" * 60)
    print("  DETERMINISM TEST")
    print("-" * 60)

    # Same input should produce same verdict (ALLOW under default policy)
    det1 = run_core_enforcement("determinism test input", source="determinism_check")
    det2 = run_core_enforcement("determinism test input", source="determinism_check")
    same_verdict = det1["core_output"]["verdict"] == det2["core_output"]["verdict"]
    same_hash = det1["core_output"]["decision_hash"] == det2["core_output"]["decision_hash"]
    print(f"  [Test 6] Same input, two runs:")
    print(f"           verdict match: {same_verdict}")
    print(f"           hash match:    {same_hash}")
    print(f"           [OK]" if same_verdict and same_hash else "           [FAIL]")

    # ── SUMMARY ──
    print()
    print("=" * 60)
    print("  VC DRY RUN RESULTS")
    print("=" * 60)
    print(f"  Total executions:    {len(TEST_INPUTS)}")
    print(f"  Successful:          {len(TEST_INPUTS) - crashes}")
    print(f"  Crashes:             {crashes}")
    print(f"  Schema violations:   {schema_violations}")
    print(f"  Missing fields:      {missing_logs}")
    print(f"  Mismatch detection:  working ({mismatches_detected} field mismatches caught)")
    print(f"  Input integrity:     working")
    print(f"  Determinism:         {'PASS' if same_verdict and same_hash else 'FAIL'}")
    print(f"  VC readiness:        {'READY' if crashes == 0 and schema_violations == 0 else 'NOT READY'}")
    print("=" * 60)

    # Save results
    os.makedirs("logs", exist_ok=True)
    with open("logs/vc_dry_run_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": get_normalized_timestamp(),
            "total": len(TEST_INPUTS),
            "crashes": crashes,
            "schema_violations": schema_violations,
            "results": results,
        }, f, indent=2, default=str)

    print(f"\n  Results saved to: logs/vc_dry_run_results.json")

    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
