# ACCESS CONTROL POLICY

**Effective Date:** 2026-04-24
**Owner:** BHIV Core Team
**Classification:** INTERNAL -- CONFIDENTIAL

---

## 1. Access Tiers

### Tier 1 -- RESTRICTED (Never Exposed)

These systems contain core truth, authority, and enforcement logic. They must **NEVER** be accessible to external developers.

| System | Contents | Who Can Access |
|--------|----------|---------------|
| **Core** | Orchestration, trace origin, context assembly | Raj, bh@blackholeinfiverse.com |
| **Bucket** | Final truth write layer (post-execution) | Ashmit (assigned), Raj, bh@ |
| **Sarathi** | Enforcement gate, execution tokens | Rajaryan (assigned), Raj, bh@ |
| **Trace Systems** | trace_id generation, crypto binding | Raj, bh@ |
| **Sovereign Core** | Decision authority (ALLOW/DENY) | Aakanksha (assigned), Raj, bh@ |

### Tier 2 -- LIMITED (Controlled Access)

These systems have defined, narrow interfaces. External developers see ONLY the API contract, never internals.

| System | What Is Visible | What Is Hidden |
|--------|----------------|---------------|
| **Pravah** | Signal stream (read-only) | Internal signal processing |
| **Execution** | Execution token validation endpoint | Token generation logic |
| **InsightBridge** | Enforcement gateway API | Sarathi integration details |

### Tier 3 -- OPEN (Documentation Only)

| Resource | Access |
|----------|--------|
| Interface contracts (docs/contracts/) | Team-wide (read-only) |
| Testing protocols | Assigned testers |
| API documentation | Assigned integrators |

---

## 2. Access Matrix

| Person | Role | Core | Bucket | Sarathi | Sovereign | Pravah | Execution |
|--------|------|------|--------|---------|-----------|--------|-----------|
| **bh@blackholeinfiverse.com** | Owner | FULL | FULL | FULL | FULL | FULL | FULL |
| **Raj Prajapati** | Core Lead | FULL | READ | READ | READ | READ | READ |
| **Ashmit Pandey** | Bucket | NO | FULL | NO | NO | NO | NO |
| **Rajaryan** | Enforcement | NO | NO | FULL | NO | NO | NO |
| **Aakanksha** | Sovereign | NO | NO | NO | FULL | NO | NO |
| **Vijay Dhawan** | InsightBridge | NO | NO | API ONLY | NO | NO | NO |
| **Kanishk** | Execution | NO | NO | NO | NO | NO | API ONLY |
| **Vinayak Tiwari** | Testing | READ | READ | READ | READ | READ | READ |
| **Rayyan Sheikh** | Pravah | NO | NO | NO | NO | SIGNAL ONLY | NO |
| **Pritesh Patra** | Interfaces | NO | NO | NO | NO | NO | NO |

---

## 3. Rules

### Repository Rules

| Rule | Enforcement |
|------|-------------|
| All repos MUST be private | GitHub settings |
| No repo sharing without explicit approval | Violation = immediate revocation |
| Core/Bucket/Sarathi repos: NO external dev access | Access matrix above |
| New collaborator requires written approval from bh@ | Email/written record |

### Code Rules

| Rule | Enforcement |
|------|-------------|
| No internal architecture exposed in public docs | Code review |
| External services expose ONLY defined APIs | Contract docs |
| No credentials in code | .gitignore + .env |
| No trace internals in client-facing responses | API design |

### Communication Rules

| Rule | Enforcement |
|------|-------------|
| Internal architecture discussed only on approved channels | Team policy |
| No screenshots of Core/Bucket/Sarathi code shared externally | Team policy |
| Integration details shared via contracts only | docs/contracts/ |

---

## 4. Violation Response

| Severity | Action |
|----------|--------|
| Unauthorized repo sharing | Immediate access revocation + written note |
| Credential exposure | Rotate keys immediately + audit |
| Architecture leak | Investigate scope + restrict access |
| Repeated violation | Removal from project |

---

**This policy is effective immediately and applies to all team members.**
