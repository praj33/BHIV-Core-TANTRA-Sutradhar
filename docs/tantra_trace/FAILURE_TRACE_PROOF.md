# FAILURE TRACE PROOF — Phase 10

## Trace Persistence on Failure

This proof demonstrates that the trace spine persists even when execution is denied or fails.

### Failure Scenario

```
User Request (contains "forbidden" content)
  |
  v
[CORE] trace_id = "def67890-..." generated
  |  signal: origin
  v
[SOVEREIGN CORE] policy evaluated -- DENY triggered
  |  signal: decision (DENY, policy=deny_test, input_hash=abc123...)
  v
[SARATHI] enforcement rejects execution
  |  SarathiEnforcementError raised
  |  Execution BLOCKED
  v
[EXECUTION] records failure
  |  signal: execution_failed (reason="Blocked by Sarathi", status=denied)
  |  trace_hash = SHA-256(trace_id + task-denied-001 + timestamp)
  v
[PRAVAH] observes failure (passive, non-blocking)
     signal: observation (trace_failure, severity=error)
```

### Key Proof Points

| Assertion | Status |
|-----------|--------|
| Trace persists after denial | VERIFIED — trace_id unchanged |
| Decision DENY is recorded | VERIFIED — signal present with policy reference |
| Failure is captured in trace | VERIFIED — `execution_failed` signal exists |
| No break in lineage | VERIFIED — all signals present in context |
| trace_hash computed even on failure | VERIFIED — binding exists |
| Pravah receives failure signal | VERIFIED — observation signal with severity=error |
| Timestamp ordering maintained | VERIFIED — monotonically non-decreasing |

### Trace Integrity After Failure

```json
{
    "trace_id": "def67890-...",
    "signals": [
        {"signal_type": "origin",           "layer": "core"},
        {"signal_type": "decision",         "layer": "sovereign_core",  "payload": {"decision": "DENY"}},
        {"signal_type": "execution_failed", "layer": "execution",      "payload": {"status": "denied"}},
        {"signal_type": "observation",      "layer": "pravah",         "payload": {"signal_type": "trace_failure"}}
    ],
    "trace_hash": "computed and bound"
}
```

### Test Proof

Test `test_failure_trace_persists` validates all above assertions.

**Failure trace is proven: trace persists, failure captured, no break in lineage.**
