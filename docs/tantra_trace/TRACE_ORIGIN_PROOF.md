# TRACE ORIGIN PROOF — Phase 1

## Trace Origin Ownership

**Core is the SOLE origin of all trace_ids in the TANTRA system.**

### Implementation

File: [`core/trace/trace_origin.py`](file:///c:/Users/Microsoft/Downloads/BHIV-Core/BHIV-Core/core/trace/trace_origin.py)

### Rules Enforced

| Rule | Implementation |
|------|---------------|
| trace_id MUST originate in Core | `generate_trace_id()` is the only trace_id generator |
| trace_id MUST be unique | Thread-safe `_issued_trace_ids` set with collision detection |
| trace_timestamp MUST be UTC | Delegates to `time_sync.get_normalized_timestamp()` |
| No downstream system may generate trace_id | Only `core/trace/trace_origin.py` contains generation logic |

### Entry Points Covered

| Entry Point | File | Function |
|-------------|------|----------|
| MCP Bridge API | `mcp_bridge.py` | `handle_task()`, `query_knowledge_base()` |
| Core Events API | `core/events/core_events.py` | `accept_event()` |
| Simple API | `simple_api.py` | All endpoints |

### Trace Origin Record Format

```json
{
    "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "trace_timestamp": "2026-04-20T09:02:51.123456+00:00",
    "source": "mcp_bridge"
}
```

### Proof of Uniqueness

Test `test_trace_id_uniqueness` generates 1000 trace_ids and verifies zero collisions.

**Trace origin is proven: Core-owned, unique, UTC-normalized.**
