# AUTHORIZED EVALUATORS — Phase 4

## Purpose

Only these evaluator_id values are accepted by Core when building Sovereign decisions. No arbitrary values. Each maps to an approved authority identity.

## Registry

sovereign_bhiv_core
- Owner: BHIV Core internal Sovereign engine
- Used when: USE_EXTERNAL_AUTHORITY=false
- Status: ACTIVE

sovereign_bhiv_core_v2
- Owner: BHIV Core Sovereign v2 (planned upgrade)
- Used when: Core v2 rollout
- Status: RESERVED

sovereign_external_primary
- Owner: Aakanksha (Sovereign Systems)
- Used when: USE_EXTERNAL_AUTHORITY=true
- Status: ACTIVE

## Rules

- Any evaluator_id NOT in this list is REJECTED
- EvaluatorIdentityError is raised immediately
- No fallback evaluators
- No ad-hoc identity assignment
- Adding new evaluators requires code change + review

## Enforcement

File: core/authority/sovereign_signer.py
Set: AUTHORIZED_EVALUATORS
Exception: EvaluatorIdentityError
