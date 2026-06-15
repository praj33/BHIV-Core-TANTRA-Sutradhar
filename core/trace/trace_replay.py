"""
Trace Replay — Reconstruction Endpoint

GET /trace/{trace_id}  → Reconstruct full execution lineage from a single trace_id

Sources:
  - logs/bucket_truth_log.jsonl (execution records)
  - logs/insightflow_traces.jsonl (telemetry chains)
  - logs/replay_protection.jsonl (token usage)

Produces a complete, reconstructable execution history.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

BUCKET_LOG = os.environ.get("BUCKET_LOG_FILE", "logs/bucket_truth_log.jsonl")
INSIGHT_LOG = os.environ.get("INSIGHTFLOW_LOG_FILE", "logs/insightflow_traces.jsonl")
REPLAY_LOG = os.environ.get("REPLAY_STORE_FILE", "logs/replay_protection.jsonl")


def _read_jsonl(filepath: str) -> List[Dict]:
    """Read a JSONL file and return list of parsed records."""
    records = []
    if not os.path.exists(filepath):
        return records
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.warning(f"Could not read {filepath}: {e}")
    return records


def reconstruct_trace(trace_id: str) -> Dict[str, Any]:
    """
    Reconstruct full execution lineage from a single trace_id.

    Searches across all log sources and assembles:
      - Execution record (from Bucket)
      - Trace chain (from InsightFlow)
      - Token usage (from Replay log)
      - Decision path
      - Timestamps
      - Participant evidence

    Returns:
        Complete reconstruction or NOT_FOUND status
    """
    result = {
        "trace_id": trace_id,
        "reconstruction_timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "NOT_FOUND",
        "bucket_records": [],
        "insightflow_traces": [],
        "replay_records": [],
        "participant_sequence": [],
        "decision_path": None,
        "execution_path": None,
        "lineage": [],
    }

    # 1. Search Bucket truth log
    bucket_records = _read_jsonl(BUCKET_LOG)
    matching_bucket = [r for r in bucket_records if r.get("trace_id") == trace_id]
    result["bucket_records"] = matching_bucket

    # 2. Search InsightFlow traces
    insight_records = _read_jsonl(INSIGHT_LOG)
    matching_insight = [r for r in insight_records if r.get("trace_id") == trace_id]
    result["insightflow_traces"] = matching_insight

    # 3. Search replay protection log
    replay_records = _read_jsonl(REPLAY_LOG)
    matching_replay = [r for r in replay_records if r.get("trace_id") == trace_id]
    result["replay_records"] = matching_replay

    # 4. Reconstruct participant sequence from InsightFlow chain
    if matching_insight:
        for trace_record in matching_insight:
            chain = trace_record.get("trace_chain", [])
            for signal in chain:
                layer = signal.get("layer", "unknown")
                result["participant_sequence"].append({
                    "layer": layer,
                    "trace_id": signal.get("trace_id", trace_id),
                    "timestamp": signal.get("timestamp", ""),
                    "data": signal.get("data", {}),
                })

    # 5. Extract decision path
    for signal in result["participant_sequence"]:
        if signal["layer"] == "sovereign_core":
            result["decision_path"] = {
                "verdict": signal["data"].get("decision", signal["data"].get("verdict", "")),
                "trace_id": signal["trace_id"],
                "timestamp": signal["timestamp"],
            }
            break

    # 6. Extract execution path from bucket
    if matching_bucket:
        record = matching_bucket[0]
        result["execution_path"] = {
            "execution_id": record.get("execution_id", ""),
            "decision": record.get("decision", ""),
            "execution_token": record.get("execution_token", "")[:16] + "..." if record.get("execution_token") else "",
            "timestamp": record.get("timestamp", ""),
            "payload_hash": record.get("payload_hash", ""),
        }

    # 7. Build full lineage (chronological)
    all_events = []
    for sig in result["participant_sequence"]:
        all_events.append({
            "source": "insightflow",
            "layer": sig["layer"],
            "timestamp": sig["timestamp"],
        })
    for rec in matching_bucket:
        all_events.append({
            "source": "bucket",
            "layer": "bucket_write",
            "timestamp": rec.get("timestamp", ""),
        })
    for rep in matching_replay:
        all_events.append({
            "source": "replay_protection",
            "layer": "token_use",
            "timestamp": rep.get("timestamp", rep.get("used_at", "")),
        })

    # Sort by timestamp
    all_events.sort(key=lambda x: x.get("timestamp", ""))
    result["lineage"] = all_events

    # 8. Determine status
    if matching_bucket or matching_insight or matching_replay:
        result["status"] = "RECONSTRUCTED"
        result["evidence_sources"] = {
            "bucket": len(matching_bucket),
            "insightflow": len(matching_insight),
            "replay": len(matching_replay),
        }
    else:
        result["status"] = "NOT_FOUND"

    return result


def reconstruct_all_traces() -> List[Dict[str, Any]]:
    """List all known trace_ids and their summary."""
    all_trace_ids = set()

    for record in _read_jsonl(BUCKET_LOG):
        if "trace_id" in record:
            all_trace_ids.add(record["trace_id"])
    for record in _read_jsonl(INSIGHT_LOG):
        if "trace_id" in record:
            all_trace_ids.add(record["trace_id"])

    summaries = []
    for tid in sorted(all_trace_ids):
        recon = reconstruct_trace(tid)
        summaries.append({
            "trace_id": tid,
            "status": recon["status"],
            "bucket_records": len(recon["bucket_records"]),
            "insightflow_traces": len(recon["insightflow_traces"]),
            "participant_count": len(recon["participant_sequence"]),
        })

    return summaries
