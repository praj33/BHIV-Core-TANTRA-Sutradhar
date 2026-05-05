# BHIV Core — TANTRA Sutradhar

An advanced AI processing pipeline with sovereign execution control, cryptographic enforcement, and deterministic system integrity. BHIV Core is a fully integrated, non-bypassable participant in the TANTRA execution chain.

---

## 🔒 Sovereign Execution Architecture

BHIV Core enforces a strict execution model where **no action can occur without cryptographic proof**:

```
Trigger → Core → Sovereign Core → Sarathi → Execution Gate → Bucket → Pravah
              ↓           ↓            ↓            ↓            ↓
          trace_id    decision     enforcement   gated_exec   truth_write
          (UUID v4)   (ALLOW/DENY)  (CLEARED)    (token req)  (verified)
```

**SAME `trace_id` flows across ALL layers. No regeneration. No mutation. No bypass.**

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ENTRY LAYER                                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │  Core API   │   │ MCP Bridge  │   │ Web Interface│               │
│  │  (8003)     │   │  (8002)     │   │  (8003)     │               │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘               │
│         │ 403 w/o token    │                  │                      │
└─────────┼──────────────────┼──────────────────┼──────────────────────┘
          └──────────────────┼──────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    AUTHORITY LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Trace Origin → Sovereign Core → Sarathi Enforcer            │    │
│  │   (UUID v4)     (ALLOW/DENY)     (CLEARED/BLOCKED)          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Contract Validator (7 strict schemas at all boundaries)      │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   EXECUTION LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Execution Gate (gated_execute)                               │    │
│  │   • Token lifecycle (CREATED → USED → EXPIRED → INVALID)    │    │
│  │   • TTL enforcement (300s default)                           │    │
│  │   • Scope binding (trace + agent + intent + decision_hash)   │    │
│  │   • Cryptographic binding proof (SHA-256)                    │    │
│  │   • Persistent replay protection                             │    │
│  │   • @require_gate decorator + assertion layer                │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     TRUTH LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Bucket Writer (append-only truth store)                      │    │
│  │   • finalize_execution() = write + post-write verify         │    │
│  │   • INVARIANT: execution success = Bucket write success      │    │
│  │   • record_hash + payload_hash for integrity                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Parallel Validator (Core ↔ Sarathi comparison)               │    │
│  │   • Canonical 6-field output + mismatch detection            │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │Text Agent │  │Archive    │  │Image Agent│  │Audio Agent│        │
│  │           │  │Agent      │  │(BLIP)     │  │(Wav2Vec2) │        │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Reinforcement Learning (UCB optimization + auto-retraining)  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Security Model

| Guarantee | Mechanism |
|-----------|-----------|
| No execution without token | `gated_execute()` → `ExecutionBlockedError` |
| No replay | Persistent replay store + in-memory `_used_tokens` |
| No expired token use | TTL enforcement (configurable) |
| No cross-trace misuse | Scope binding + cryptographic binding |
| No bypass via direct call | `@require_gate` decorator |
| Bypass detection | `assert_execution_gated()` → PANIC |
| No success without truth | `finalize_execution()` → Bucket write + verify |
| All failures → FAIL CLOSED | No fallback, no silent execution |

---

## 📊 Test Coverage

```
Trace Spine:            24/24 PASS
Authority Extraction:   12/12 PASS
Execution Token Lock:   12/12 PASS
Adversarial Seal:       24/24 PASS
TANTRA Convergence:     21/21 PASS
─────────────────────────────────
TOTAL:                  93/93 PASS
```

Run all tests:
```bash
python tests/test_trace_spine.py
python tests/test_authority_extraction.py
python tests/test_execution_token_lock.py
python tests/test_adversarial_seal.py
python tests/test_tantra_convergence.py
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MongoDB 5.0+ (for NLO storage)
- Groq API key
- 8GB+ RAM (16GB recommended)

### Installation

```bash
git clone https://github.com/praj33/BHIV-Core-TANTRA-Sutradhar.git
cd BHIV-Core
pip install -r requirements.txt
python -m spacy download en_core_web_sm

cp .env.example .env
# Edit .env with your API keys
```

### Running

```bash
# Start Core API (port 8003)
python core_api.py

# Start MCP Bridge (port 8002)
python mcp_bridge.py

# Start Web Interface
python integration/web_interface.py
```

### Access

- **Core API**: http://localhost:8003
- **MCP Bridge**: http://localhost:8002/docs
- **Health Check**: http://localhost:8002/health

---

## 📁 Project Structure

```
BHIV-Core/
├── core/
│   ├── authority/                    # Sovereign execution enforcement
│   │   ├── __init__.py               # Sovereign + Sarathi wrappers
│   │   ├── execution_gate.py         # Non-bypassable execution gate
│   │   ├── bucket_writer.py          # Append-only truth writer
│   │   ├── contract_validator.py     # Strict schema validation (7 contracts)
│   │   ├── canonical_output.py       # Deterministic 6-field output
│   │   └── parallel_validator.py     # Core ↔ Sarathi comparison engine
│   ├── trace/                        # Immutable trace system
│   │   ├── trace_origin.py           # UUID v4 trace generation
│   │   ├── trace_context.py          # Frozen dataclass trace propagation
│   │   ├── trace_binding.py          # Cryptographic trace binding
│   │   ├── sovereign_core.py         # Decision engine
│   │   ├── sarathi_enforcer.py       # Enforcement validator
│   │   └── time_sync.py              # UTC timestamp normalization
│   └── orchestration/                # Event processing
├── orchestration/
│   └── core_orchestrator.py          # Task execution (defense-in-depth)
├── core_api.py                       # FastAPI entry (403 without token)
├── mcp_bridge.py                     # MCP protocol bridge
├── integration/                      # Web + voice + LLM interfaces
├── reinforcement/                    # RL agent selection
├── tests/                            # 93 tests across 5 suites
│   ├── test_trace_spine.py           # Trace immutability (24 tests)
│   ├── test_authority_extraction.py  # Authority signals (12 tests)
│   ├── test_execution_token_lock.py  # Token enforcement (12 tests)
│   ├── test_adversarial_seal.py      # Attack scenarios (24 tests)
│   ├── test_tantra_convergence.py    # E2E TANTRA flow (21 tests)
│   └── test_vc_dry_run.py            # VC readiness (15 executions)
├── docs/contracts/                   # 41 enforcement contracts
├── review_packets/                   # 7 review packets
└── logs/                             # Execution + truth logs
    ├── bucket_truth_log.jsonl        # Append-only truth store
    ├── replay_protection.jsonl       # Persistent replay store
    ├── parallel_execution.jsonl      # Comparison logs
    └── tantra_flow_proof.json        # Real E2E flow JSON
```

---

## 📋 Contracts & Review Packets

### Key Contracts (`docs/contracts/`)

| Contract | Purpose |
|----------|---------|
| `FULL_TANTRA_FLOW_PROOF.md` | Real 7-layer E2E flow with JSON |
| `TANTRA_CONTRACT_SCHEMA.md` | 7 strict boundary schemas |
| `EXECUTION_SURFACE_SEAL_PROOF.md` | All surfaces enumerated + sealed |
| `TOKEN_LIFECYCLE_SPEC.md` | CREATED → USED → EXPIRED → INVALID |
| `BUCKET_TRUTH_INVARIANT.md` | Execution success = Bucket write |
| `FAILURE_MATRIX_FINAL_LOCK.md` | All failure modes → FAIL CLOSED |
| `CORE_SARATHI_COMPARISON_MAP.md` | 1:1 field alignment for VC |

### Review Packets (`review_packets/`)

| Packet | Sprint |
|--------|--------|
| `core_tantra_convergence.md` | TANTRA E2E + Contracts + Failure Determinism |
| `core_execution_seal_final.md` | System Seal + Token Lifecycle + Bucket Invariant |
| `sarathi_parallel_validation.md` | Core ↔ Sarathi Parallel Validation |
| `2026_execution_token_lock.md` | Execution Token Enforcement |

---

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EXECUTION_TOKEN_TTL` | `300` | Token time-to-live (seconds) |
| `USE_EXTERNAL_AUTHORITY` | `false` | Use external Sovereign/Sarathi services |
| `SOVEREIGN_SERVICE_URL` | `http://localhost:9001` | Sovereign service endpoint |
| `SARATHI_SERVICE_URL` | `http://localhost:9002` | Sarathi service endpoint |
| `BUCKET_SERVICE_URL` | `http://localhost:9003` | Bucket service endpoint |
| `REPLAY_STORE_FILE` | `logs/replay_protection.jsonl` | Persistent replay store |
| `BUCKET_LOG_FILE` | `logs/bucket_truth_log.jsonl` | Local truth store |

---

## 👥 Integration Block

| Owner | System | Role |
|-------|--------|------|
| Raj Prajapati | BHIV Core | Core execution + trace + enforcement |
| Siddhesh Narkar | Bucket | Append-only truth storage |
| Vijay Dhawan | InsightBridge | Enforcement + gateway alignment |
| Aakanksha | Sovereign Systems | Decision integrity |
| Rajaryan | Sarathi | Enforcement token validation |
| Kanishk | Execution Systems | Token consumption |
| Shivam/Ritesh | Pravah | Signal ingestion + observation |
| Pritesh Patra | Interfaces | Schema consistency |

---

## 📄 License

Proprietary — BHIV Systems
