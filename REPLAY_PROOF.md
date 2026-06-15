# REPLAY PROOF — Trace Reconstruction

Date: 2026-06-15
Sprint: TANTRA Live Convergence — Phase 4

---

## Capability

Core now exposes:
- GET /trace/{trace_id} — Reconstruct full execution lineage from a single trace_id
- GET /traces — List all known trace_ids with summary

Implementation: core/trace/trace_replay.py

Sources searched:
- logs/bucket_truth_log.jsonl (execution records)
- logs/insightflow_traces.jsonl (telemetry chains)
- logs/replay_protection.jsonl (token usage)

---

## Proof: Trace Reconstruction

Trace ID: 134124de-443f-417c-abc0-f39260b279c8
Status: RECONSTRUCTED

### Participant Sequence (7 layers)
1. core_origin
2. sovereign_core
3. cet
4. sarathi
5. bridge
6. execution
7. bucket

### Decision Path
- Verdict: ALLOW
- Trace ID: 134124de-443f-417c-abc0-f39260b279c8
- Timestamp: 2026-06-03T06:47:08.013646+00:00

### Lineage Events: 7
Each event has: source, layer, timestamp — all with same trace_id.

### Evidence
Full reconstruction output: logs/replay_reconstruction_proof.json

---

## Known Traces

Total reconstructable traces: 29
Traces with both bucket + insightflow records: multiple
Traces with full 7-layer participant sequence: confirmed

---

## Current Limitation

All 29 traces are from INTERNAL mode (localhost services).
No traces from real external participants yet (BLOCKED on URLs).

Once live URLs are wired, GET /trace/{trace_id} will reconstruct traces that span real participant systems.

---

## API Usage

### Reconstruct a single trace:
```
GET http://localhost:8003/trace/134124de-443f-417c-abc0-f39260b279c8
```

Response includes:
- bucket_records: execution truth records
- insightflow_traces: telemetry chains
- replay_records: token usage
- participant_sequence: ordered layer evidence
- decision_path: Sovereign verdict
- execution_path: execution details
- lineage: chronological events across all sources

### List all traces:
```
GET http://localhost:8003/traces
```
