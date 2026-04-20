# TANTRA Trace Spine — Documentation

Phase proofs for the Core - Pravah Trace Lock integration.

| Phase | Document | Description |
|-------|----------|-------------|
| 1 | [TRACE_ORIGIN_PROOF.md](TRACE_ORIGIN_PROOF.md) | trace_id generation — Core ownership, UUID v4, uniqueness |
| 2 | [TRACE_PROPAGATION_MAP.md](TRACE_PROPAGATION_MAP.md) | Immutable propagation — frozen dataclass, same trace_id everywhere |
| 3 | [TRACE_BINDING_SPEC.md](TRACE_BINDING_SPEC.md) | SHA-256 crypto binding — deterministic, tamper-evident |
| 4 | [DECISION_ENFORCEMENT_TRACE.md](DECISION_ENFORCEMENT_TRACE.md) | Sovereign Core + Sarathi signals — ALLOW/DENY + CLEARED/BLOCKED |
| 5 | [SARATHI_ENFORCEMENT_ASSERTION.md](SARATHI_ENFORCEMENT_ASSERTION.md) | Sarathi lock — non-bypassable enforcement gate |
| 6 | [CORE_TO_PRAVAH_SIGNAL.md](CORE_TO_PRAVAH_SIGNAL.md) | Pravah contract — strict 6-field schema, passive only |
| 7 | [PRAVAH_NON_BLOCKING_PROOF.md](PRAVAH_NON_BLOCKING_PROOF.md) | Non-blocking guarantee — system unaffected if Pravah fails |
| 8 | [TIME_SYNC_SPEC.md](TIME_SYNC_SPEC.md) | UTC normalization — ISO 8601, monotonic ordering |
| 9 | [FULL_TRACE_PROOF.md](FULL_TRACE_PROOF.md) | End-to-end trace — all 5 layers verified |
| 10 | [FAILURE_TRACE_PROOF.md](FAILURE_TRACE_PROOF.md) | Failure persistence — trace survives denial |

## Related

- **Review Packet**: [`review_packets/core_pravah_trace_lock.md`](../../review_packets/core_pravah_trace_lock.md)
- **Test Suite**: [`tests/test_trace_spine.py`](../../tests/test_trace_spine.py)
- **Source Code**: [`core/trace/`](../../core/trace/)
