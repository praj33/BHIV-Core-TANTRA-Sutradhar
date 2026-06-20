# Production Runtime Integration Registry — Phase IV Final

Version: 3.0.0
Date: 2026-06-20
Status: ✅ **8/8 SUCCESS**

---

## Overview

This is the authoritative runtime map for the TANTRA ecosystem. It defines what plugs into BHIV Core, why, when, which layer it belongs to, which authority it owns (and does NOT own), and what trace it produces.

---

## Registry Architecture

All participants are registered in `TANTRA_INTEGRATION_REGISTRY.json`. New participants are added by updating the JSON file — no hardcoded logic changes required.

### Registration Requirements

1. **System Name** — Unique identifier
2. **Owner** — Responsible person
3. **Layer** — Which runtime layer (Origin, Governance, Enforcement, Execution, Truth)
4. **URL** — Production endpoint
5. **Protocol** — HTTP method + path
6. **Schema** — Exact input/output format
7. **Auth** — Authentication method
8. **Failure Mode** — FAIL-CLOSED or GRACEFUL-FALLBACK
9. **Trace Requirements** — What trace fields are produced/consumed

---

## Registered Participants

| # | System | Owner | Layer | URL | Status |
|---|---|---|---|---|---|
| 1 | BHIV Core | Raj Prajapati | Origin | localhost:8003 | ✅ Operational |
| 2 | Sovereign | Aakanksha | Governance | text-risk-scoring-service.onrender.com | ✅ Operational |
| 3 | CET | Tanvi | Governance | sl-validator-parity.onrender.com | ✅ Operational |
| 4 | Sarathi | Rajaryan | Enforcement | text-risk-scoring-service.onrender.com | ✅ Operational |
| 5 | Bridge | Ranjit | Enforcement | evoke-oboe-stilt.ngrok-free.dev | ✅ Operational |
| 6 | Bucket | Siddhesh | Truth | bhiv-bucket.onrender.com | ✅ Operational |
| 7 | InsightFlow | Vijay | Truth | 04d1-152-59-6-179.ngrok-free.app | ✅ Operational |

---

## Authority Boundaries

Each participant owns specific authority. Core MUST NOT replicate or override these authorities.

| Participant | OWNS | DOES NOT OWN |
|---|---|---|
| **Core** | Trace generation, orchestration, agent execution | Risk decisions, contract compilation, enforcement |
| **Sovereign** | Risk assessment, ALLOW/DENY decisions | Contract compilation, enforcement, truth storage |
| **CET** | KSML compilation, SUM-SCRIPT generation | Risk decisions, enforcement, execution |
| **Sarathi** | Cryptographic enforcement, JWT issuance | Risk decisions, contract compilation, execution |
| **Bridge** | JWT validation, continuity enforcement | JWT issuance, risk decisions, execution |
| **Bucket** | Immutable truth storage, hash chain | Risk decisions, enforcement, execution |
| **InsightFlow** | Dataset registry, telemetry, provenance | Risk decisions, enforcement, truth storage |

---

## Integration Protocols

### Authentication Methods

| Participant | Auth Type | Details |
|---|---|---|
| Sovereign | None | Open endpoint |
| CET | None | Open endpoint |
| Sarathi | SHA-256 Hash | signature_hash = SHA-256(execution_id\|rajya_verdict\|timestamp) |
| Bridge | JWT Bearer | RS256 via JWKS, iss/aud validation, continuity check |
| Bucket | Schema validation | Field-level validation, parent_hash chain |
| InsightFlow | API Key | X-API-Key header |

### JWT Chain

```
Sarathi (Issues JWT)
    │ RS256 signed
    │ Claims: iss=tantra-sarathi, aud=tantra-bridge
    │         execution_id, trace_id, cet_hash, jti
    ▼
Core (Passes JWT)
    │ Authorization: Bearer <JWT>
    │ X-Sarathi-Execution-Id, X-Sarathi-Trace-Id, X-Sarathi-Cet-Hash
    ▼
Bridge (Validates JWT)
    │ Fetches JWKS from Sarathi /.well-known/jwks.json
    │ Verifies RS256 signature, iss, aud, kid
    │ Cross-validates execution_id, trace_id, cet_hash
    ▼
Execution proceeds
```

---

## How Products Attach

Products attach to BHIV Core by:

1. Registering in `TANTRA_INTEGRATION_REGISTRY.json`
2. Implementing the required protocol (HTTP endpoint)
3. Accepting `X-Trace-Id` header for trace continuity
4. Returning structured JSON responses
5. Declaring failure mode (FAIL-CLOSED or GRACEFUL-FALLBACK)

No hardcoded logic changes required. Configuration-driven integration.

---

## Verification

All 7 participants verified with live HTTP on 2026-06-20:
- **Proof trace_id:** `2a1556b2-1c5a-41f4-9c19-4e9399be5443`
- **Result:** 8/8 SUCCESS
- **Proof file:** `logs/full_tantra_v4_final_proof.json`
