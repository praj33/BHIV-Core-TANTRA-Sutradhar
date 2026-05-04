"""
Parallel Validator — Phase 2-5

Handles:
  Phase 2: Input integrity (no mutation, log raw input)
  Phase 3: Parallel execution logging (real-time, readable)
  Phase 4: Comparison readiness (field-level alignment)
  Phase 5: Mismatch detection (obvious, field-level)

This module enables side-by-side execution visibility
between Core and Sarathi during live VC sessions.
"""

import hashlib
import json
import logging
import os
import sys
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from datetime import datetime, timezone

from core.trace.trace_origin import create_trace_origin
from core.trace.trace_context import create_trace_context
from core.trace.time_sync import get_normalized_timestamp
from core.authority import callSovereign, callSarathi
from core.authority.canonical_output import (
    produce_from_trace_context,
    validate_canonical_output,
    canonical_to_json,
    CANONICAL_FIELDS,
)

logger = logging.getLogger(__name__)

PARALLEL_LOG_FILE = os.environ.get(
    "PARALLEL_LOG_FILE", "logs/parallel_execution.jsonl"
)


# ═══════════════════════════════════════════════════════════
# PHASE 2 — INPUT INTEGRITY
# ═══════════════════════════════════════════════════════════


def log_raw_input(input_data: str, context: Dict[str, Any] = None) -> str:
    """
    Log raw input BEFORE any processing.
    Returns input hash for integrity verification.

    Rules:
      - No transformation before logging
      - No enrichment
      - No hidden defaults
      - Raw input is preserved exactly as received
    """
    input_hash = hashlib.sha256(input_data.encode("utf-8")).hexdigest()
    log_entry = {
        "type": "RAW_INPUT",
        "timestamp": get_normalized_timestamp(),
        "input": input_data,
        "input_hash": input_hash,
        "context": context or {},
    }
    _write_log(log_entry)
    return input_hash


def verify_input_integrity(
    core_input: str, sarathi_input: str
) -> Dict[str, Any]:
    """
    Verify that Core received EXACT same input as Sarathi.
    No mutation, no transformation.
    """
    core_hash = hashlib.sha256(core_input.encode("utf-8")).hexdigest()
    sarathi_hash = hashlib.sha256(sarathi_input.encode("utf-8")).hexdigest()
    match = core_hash == sarathi_hash

    result = {
        "input_match": match,
        "core_input_hash": core_hash,
        "sarathi_input_hash": sarathi_hash,
    }

    if not match:
        result["mismatch_detail"] = {
            "core_input": core_input,
            "sarathi_input": sarathi_input,
        }

    return result


# ═══════════════════════════════════════════════════════════
# PHASE 3 — PARALLEL EXECUTION LOGGING
# ═══════════════════════════════════════════════════════════


def run_core_enforcement(
    input_data: str, context: Dict[str, Any] = None, source: str = "parallel_validator"
) -> Dict[str, Any]:
    """
    Run Core enforcement and produce canonical output.
    Captures input, runs enforcement, captures output.
    Emits real-time log.

    Returns dict with:
      - input: raw input
      - core_output: canonical OrderedDict
      - trace_id: trace identifier
      - timing_ms: processing time
    """
    import time

    # Log raw input FIRST (Phase 2)
    input_hash = log_raw_input(input_data, context)

    start = time.time()

    # Create trace
    origin = create_trace_origin(source)
    ctx = create_trace_context(
        origin["trace_id"], origin["trace_timestamp"], source
    )

    # Sovereign decision
    ctx = callSovereign(ctx, input_data, context or {})

    # Sarathi enforcement
    ctx = callSarathi(ctx)

    # Produce canonical output (Phase 1)
    core_output = produce_from_trace_context(ctx, input_data)

    elapsed_ms = round((time.time() - start) * 1000, 2)

    # Build parallel log entry
    log_entry = {
        "type": "PARALLEL_EXECUTION",
        "timestamp": get_normalized_timestamp(),
        "input": input_data,
        "input_hash": input_hash,
        "core_output": dict(core_output),
        "timing_ms": elapsed_ms,
        "trace_id": origin["trace_id"],
    }
    _write_log(log_entry)

    # Print to console (real-time, readable during VC)
    _print_execution(input_data, core_output, origin["trace_id"], elapsed_ms)

    return {
        "input": input_data,
        "core_output": core_output,
        "trace_id": origin["trace_id"],
        "timing_ms": elapsed_ms,
    }


def _print_execution(
    input_data: str, output: OrderedDict, trace_id: str, timing_ms: float
):
    """Print execution to console in readable format."""
    print(f"  trace_id:             {trace_id}")
    print(f"  input:                {input_data[:60]}")
    print(f"  verdict:              {output['verdict']}")
    print(f"  decision_id:          {output['decision_id']}")
    print(f"  decision_hash:        {output['decision_hash'][:32]}...")
    print(f"  enforcement_binding:  {output['enforcement_binding'][:50]}")
    print(f"  timing:               {timing_ms}ms")


# ═══════════════════════════════════════════════════════════
# PHASE 4-5 — COMPARISON + MISMATCH DETECTION
# ═══════════════════════════════════════════════════════════


def compare_outputs(
    core_output: OrderedDict,
    sarathi_output: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare Core output with Sarathi output field-by-field.

    Rules:
      - Compare every canonical field
      - No derived values
      - No hidden mappings
      - Mismatch must be obvious immediately

    Returns:
      {
        "match": True/False,
        "fields_compared": 6,
        "mismatches": [{"field": ..., "core": ..., "sarathi": ...}]
      }
    """
    mismatches = []

    for field in CANONICAL_FIELDS:
        core_val = str(core_output.get(field, ""))
        sarathi_val = str(sarathi_output.get(field, ""))

        if core_val != sarathi_val:
            mismatches.append({
                "field": field,
                "core": core_val,
                "sarathi": sarathi_val,
            })

    result = {
        "match": len(mismatches) == 0,
        "fields_compared": len(CANONICAL_FIELDS),
        "mismatches": mismatches,
    }

    if mismatches:
        _log_mismatch(core_output, sarathi_output, mismatches)

    return result


def _log_mismatch(
    core_output: OrderedDict,
    sarathi_output: Dict[str, Any],
    mismatches: List[Dict],
):
    """
    Log mismatch clearly and obviously.
    Phase 5: Mismatch must be obvious immediately.
    """
    log_entry = {
        "type": "MISMATCH_DETECTED",
        "timestamp": get_normalized_timestamp(),
        "core_output": dict(core_output),
        "sarathi_output": sarathi_output,
        "mismatches": mismatches,
        "mismatch_count": len(mismatches),
    }
    _write_log(log_entry)

    # Print CLEARLY to console
    print("")
    print("  " + "!" * 50)
    print("  !! MISMATCH DETECTED !!")
    print("  " + "!" * 50)
    for m in mismatches:
        print(f"    Field: {m['field']}")
        print(f"      Core:    {m['core']}")
        print(f"      Sarathi: {m['sarathi']}")
    print("  " + "!" * 50)
    print("")


# ═══════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════


def _write_log(entry: Dict[str, Any]):
    """Write to parallel execution log file (append-only)."""
    os.makedirs(os.path.dirname(PARALLEL_LOG_FILE), exist_ok=True)
    with open(PARALLEL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
