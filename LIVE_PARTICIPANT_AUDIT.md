# LIVE PARTICIPANT AUDIT — BHIV Core TANTRA Convergence

Date: 2026-06-15
Lead: Raj Prajapati
Sprint: TANTRA Live Convergence

---

## Participant Matrix

### BHIV Core (Raj Prajapati)
- Repo: github.com/praj33/BHIV-Core-TANTRA-Sutradhar
- Running: YES (local, port 8003)
- Deployable: YES (FastAPI + uvicorn)
- Endpoint Available: YES (POST /execute_task, POST /execute_sequence, GET /health)
- Auth Available: YES (Ed25519 signing, API key, X-Trace-Id middleware)
- Test Health: 142/142 tests passing
- Classification: LIVE

### Sovereign Core (Aakanksha)
- Repo: UNKNOWN
- Running: UNKNOWN
- Deployable: UNKNOWN
- Endpoint Available: NO — no URL received
- Auth Available: N/A
- Current Status: Core has internal Sovereign fallback (InternalSovereignCore). External routing implemented but no endpoint to connect to.
- Classification: BLOCKED
- Action Required: Aakanksha must provide live URL for POST /sovereign/decide

### CET — Contract Engine (Tanvi)
- Repo: UNKNOWN
- Running: UNKNOWN
- Deployable: UNKNOWN
- Endpoint Available: NO — no URL received
- Auth Available: N/A
- Current Status: Core has cet_client.py ready. Falls back to internal contract hash generation when USE_FULL_TANTRA=false.
- Classification: BLOCKED
- Action Required: Tanvi must provide live URL for POST /cet/compile

### Sarathi — Enforcer (Rajaryan)
- Repo: UNKNOWN
- Running: PARTIAL — user mentioned ngrok URL exists (June 3)
- Deployable: UNKNOWN
- Endpoint Available: PARTIAL — URL exists but was never shared with Core
- Auth Available: YES — Hemanth confirmed Core's Ed25519 key is registered in Sarathi. Schema alignment verified byte-for-byte (decision_hash, decision_id, signing bytes all match).
- Current Status: Core has sovereign_signer.py aligned with Sarathi CORE_INTEGRATION spec. 32 signing tests pass. API key fingerprint generated. Post-execution receipt builder ready.
- Classification: PARTIAL
- Action Required: Rajaryan must share the ngrok/live URL

### Gated Bridge (Ranjit)
- Repo: UNKNOWN
- Running: PARTIAL — user mentioned URL exists (June 3)
- Deployable: UNKNOWN
- Endpoint Available: PARTIAL — URL exists but was never shared with Core
- Auth Available: UNKNOWN
- Current Status: Core has bridge_client.py ready with X-Trace-Id propagation.
- Classification: PARTIAL
- Action Required: Ranjit must share the live URL

### Bucket — Truth Store (Siddhesh)
- Repo: UNKNOWN
- Running: PARTIAL — user mentioned Render URL exists (June 3)
- Deployable: YES (on Render)
- Endpoint Available: PARTIAL — URL exists but was never shared with Core
- Auth Available: UNKNOWN
- Current Status: Core has bucket_writer.py with append-only writes, post-write verification, and local JSONL fallback. 12 bucket-related tests pass.
- Classification: PARTIAL
- Action Required: Siddhesh must share the Render URL

### InsightFlow — Telemetry (Vijay)
- Repo: UNKNOWN
- Running: UNKNOWN
- Deployable: UNKNOWN
- Endpoint Available: NO — no URL received
- Auth Available: N/A
- Current Status: Core has insightflow_client.py with local JSONL fallback. Trace emission works locally.
- Classification: BLOCKED
- Action Required: Vijay must provide live URL for POST /insightflow/trace

---

## Summary

LIVE: 1 (Core)
PARTIAL: 3 (Sarathi, Bridge, Bucket — URLs exist but not shared)
BLOCKED: 3 (Sovereign, CET, InsightFlow — no URLs at all)
UNKNOWN: 0

---

## Core Readiness Proof

Tests passing: 142/142 across 7 suites
- Trace Spine: 24/24
- Authority Extraction: 12/12
- Execution Token Lock: 12/12
- Adversarial Seal: 24/24
- TANTRA Convergence: 21/21
- Live Integration: 17/17
- Sovereign Signer: 32/32

Code ready for integration:
- core/authority/sovereign_signer.py — Ed25519 signing (Sarathi-aligned)
- core/authority/tantra_flow.py — 8-step TANTRA pipeline
- core/authority/cet_client.py — CET HTTP client
- core/authority/bridge_client.py — Bridge HTTP client
- core/authority/bucket_writer.py — Bucket truth writer
- core/authority/insightflow_client.py — InsightFlow telemetry
- core/trace/middleware.py — X-Trace-Id propagation
- .env.live — configuration (all localhost, awaiting URLs)

Auth ready:
- Ed25519 public key: ca087b33d011dadfef89c2df05301c420766f29ba369d12ff2c601ab637171dc
- API key fingerprint: b4aa300a850421dd883a1cc2333fac5ca5922e4246aca6ba932058e6585de569
- Evaluator ID: bhiv.sovereign.decision.prod.v1
- Schema: tantra.decision.v1

---

## Dependencies That Must Resolve

1. Rajaryan → share Sarathi ngrok URL
2. Ranjit → share Bridge URL
3. Siddhesh → share Bucket Render URL
4. Aakanksha → deploy Sovereign + share URL
5. Tanvi → deploy CET + share URL
6. Vijay → deploy InsightFlow + share URL

Without at least participants 1-3, no real trace can be produced.
Without all 6, full TANTRA convergence is impossible.
