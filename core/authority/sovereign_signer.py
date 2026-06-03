"""
Sovereign Signer — ED25519 Cryptographic Authority Layer

Phase 1: Canonical Sovereign Decision Schema
Phase 2: Deterministic Decision Hashing
Phase 3: ED25519 Signing + Verification
Phase 4: Evaluator Identity Registry

Rules:
  - Private key NEVER in payloads
  - Signature signs ONLY canonical decision_hash
  - No fallback signing modes
  - No mutation post-signing
  - Deterministic serialization only
  - Field ordering fixed
"""

import hashlib
import json
import os
import logging
from typing import Dict, Any, Optional, Set
from collections import OrderedDict

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

# Schema version — locked
SCHEMA_VERSION = "bhiv.sovereign.decide/v1.0"

# ═══════════════════════════════════════════════════════════
# PHASE 4 — EVALUATOR IDENTITY REGISTRY
# ═══════════════════════════════════════════════════════════

# Only these evaluator IDs are accepted system-wide.
# No arbitrary values. Must map to approved authority identity.
AUTHORIZED_EVALUATORS: Set[str] = {
    "sovereign_bhiv_core",
    "sovereign_bhiv_core_v2",
    "sovereign_external_primary",
}


class SovereignSigningError(Exception):
    """Raised when signing or verification fails."""
    pass


class EvaluatorIdentityError(Exception):
    """Raised when evaluator_id is not in the authorized registry."""
    pass


# ═══════════════════════════════════════════════════════════
# KEY MANAGEMENT
# ═══════════════════════════════════════════════════════════

_signing_key: Optional[Ed25519PrivateKey] = None
_verify_key: Optional[Ed25519PublicKey] = None

KEY_DIR = os.environ.get("SOVEREIGN_KEY_DIR", "config/keys")
PRIVATE_KEY_FILE = os.path.join(KEY_DIR, "sovereign_ed25519.pem")
PUBLIC_KEY_FILE = os.path.join(KEY_DIR, "sovereign_ed25519_pub.pem")


def _ensure_keys():
    """Load or generate ED25519 key pair."""
    global _signing_key, _verify_key

    if _signing_key is not None and _verify_key is not None:
        return

    os.makedirs(KEY_DIR, exist_ok=True)

    # Try loading existing keys
    if os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE):
        with open(PRIVATE_KEY_FILE, "rb") as f:
            _signing_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(PUBLIC_KEY_FILE, "rb") as f:
            _verify_key = serialization.load_pem_public_key(f.read())
        logger.info("Loaded existing ED25519 key pair")
        return

    # Generate new key pair
    _signing_key = Ed25519PrivateKey.generate()
    _verify_key = _signing_key.public_key()

    # Save keys
    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(_signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(_verify_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    logger.info("Generated new ED25519 key pair")


def get_public_key_hex() -> str:
    """Get the public key as hex string (for sharing with Sarathi/verification)."""
    _ensure_keys()
    raw = _verify_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex()


def load_public_key_from_hex(hex_key: str) -> Ed25519PublicKey:
    """Load a public key from hex string (for verification by external systems)."""
    raw = bytes.fromhex(hex_key)
    return Ed25519PublicKey.from_public_bytes(raw)


# ═══════════════════════════════════════════════════════════
# PHASE 1 — CANONICAL DECISION SCHEMA
# ═══════════════════════════════════════════════════════════

# Required fields in EXACT order (for deterministic serialization)
CANONICAL_FIELD_ORDER = [
    "schema_version",
    "trace_id",
    "decision",
    "decision_id",
    "decision_hash",
    "policy_reference",
    "input_hash",
    "timestamp",
    "evaluator_id",
    "ed25519_signature",
]

VALID_DECISIONS = {"ALLOW", "DENY", "ESCALATE"}


def build_canonical_decision(
    trace_id: str,
    decision: str,
    input_data: str,
    policy_reference: str = "bhiv.core.default_allow_policy",
    evaluator_id: str = "sovereign_bhiv_core",
    timestamp: str = None,
) -> Dict[str, str]:
    """
    Build a canonical Sovereign decision payload.
    This is the UNSIGNED version — decision_hash is computed, signature is empty.

    Args:
        trace_id: Trace ID from Core (MUST NOT change)
        decision: ALLOW / DENY / ESCALATE
        input_data: Raw input being evaluated
        policy_reference: Policy pack ID@version
        evaluator_id: Must be in AUTHORIZED_EVALUATORS
        timestamp: RFC3339 UTC (auto-generated if None)

    Returns:
        Canonical decision dict (unsigned)

    Raises:
        EvaluatorIdentityError: If evaluator_id not authorized
        SovereignSigningError: If decision invalid
    """
    # Validate decision
    if decision not in VALID_DECISIONS:
        raise SovereignSigningError(
            f"Invalid decision: '{decision}'. Must be one of {VALID_DECISIONS}"
        )

    # Validate evaluator identity (Phase 4)
    if evaluator_id not in AUTHORIZED_EVALUATORS:
        raise EvaluatorIdentityError(
            f"Unauthorized evaluator: '{evaluator_id}'. "
            f"Must be one of {AUTHORIZED_EVALUATORS}"
        )

    # Validate trace_id
    if not trace_id or not isinstance(trace_id, str) or len(trace_id) < 8:
        raise SovereignSigningError(f"Invalid trace_id: '{trace_id}'")

    ts = timestamp or get_normalized_timestamp()
    input_hash = hashlib.sha256(input_data.encode("utf-8")).hexdigest()

    # Compute decision_id: uuid_shape(SHA256(canonical({trace_id, input_hash, evaluator_id})))
    decision_id = compute_decision_id(trace_id, input_hash, evaluator_id)

    # Build unsigned payload (signature empty for hash computation)
    payload = OrderedDict([
        ("schema_version", SCHEMA_VERSION),
        ("trace_id", trace_id),
        ("decision", decision),
        ("decision_id", decision_id),
        ("decision_hash", ""),  # Computed below
        ("policy_reference", policy_reference),
        ("input_hash", input_hash),
        ("timestamp", ts),
        ("evaluator_id", evaluator_id),
        ("ed25519_signature", ""),  # Computed in sign step
    ])

    # Phase 2: Compute decision_hash
    payload["decision_hash"] = compute_decision_hash(payload)

    return dict(payload)


# ═══════════════════════════════════════════════════════════
# DECISION ID COMPUTATION
# ═══════════════════════════════════════════════════════════

def compute_decision_id(trace_id: str, input_hash: str, evaluator_id: str) -> str:
    """
    Compute decision_id matching Sarathi's formula:
      decision_id = uuid_shape( SHA256( canonical({ trace_id, input_hash, evaluator_id }) ) )

    Canonical JSON: deterministic, sorted keys, no spaces.
    UUID shape: first 32 hex chars formatted as 8-4-4-4-12.

    Args:
        trace_id: Trace ID from Core
        input_hash: SHA-256 of the input data
        evaluator_id: Authorized evaluator identity

    Returns:
        UUID-shaped decision_id string
    """
    canonical = json.dumps(
        {"evaluator_id": evaluator_id, "input_hash": input_hash, "trace_id": trace_id},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    raw_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # UUID shape: 8-4-4-4-12 from first 32 hex chars
    h = raw_hash[:32]
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ═══════════════════════════════════════════════════════════
# PHASE 2 — DETERMINISTIC DECISION HASHING
# ═══════════════════════════════════════════════════════════

def compute_decision_hash(payload: Dict[str, str]) -> str:
    """
    Compute SHA-256 hash of the canonical decision payload.

    Serialization: RFC 8785 (JSON Canonicalization Scheme)
      - Keys sorted lexicographically (sort_keys=True)
      - No whitespace (separators=(",",":"))
      - UTF-8 encoding
    Signing: RFC 8032 (Ed25519) — applied in sign_decision()

    EXCLUDES: ed25519_signature, decision_hash, decision_id
    (signature is computed FROM this hash; decision_id and decision_hash are derived)

    Args:
        payload: Decision payload (with or without signature)

    Returns:
        SHA-256 hex digest
    """
    # Build canonical JSON — exclude derived/computed fields
    canonical = {}
    for field in CANONICAL_FIELD_ORDER:
        if field in ("ed25519_signature", "decision_hash", "decision_id"):
            continue  # Exclude from hash computation
        canonical[field] = payload.get(field, "")

    # RFC 8785: sorted keys, no whitespace, UTF-8
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def get_canonical_bytes(payload: Dict[str, str]) -> bytes:
    """Get the canonical bytes that are signed (for verification)."""
    decision_hash = payload.get("decision_hash", "")
    if not decision_hash:
        decision_hash = compute_decision_hash(payload)
    return decision_hash.encode("utf-8")


# ═══════════════════════════════════════════════════════════
# PHASE 3 — ED25519 SIGNING
# ═══════════════════════════════════════════════════════════

def sign_decision(payload: Dict[str, str]) -> Dict[str, str]:
    """
    Sign a canonical decision payload with ED25519.

    Args:
        payload: Unsigned canonical decision (from build_canonical_decision)

    Returns:
        Signed payload (with ed25519_signature filled)

    Raises:
        SovereignSigningError: If signing fails
    """
    _ensure_keys()

    # Ensure decision_hash is computed
    decision_hash = payload.get("decision_hash", "")
    if not decision_hash:
        decision_hash = compute_decision_hash(payload)
        payload["decision_hash"] = decision_hash

    # Sign the decision_hash (NOT the full payload)
    try:
        message = decision_hash.encode("utf-8")
        signature = _signing_key.sign(message)
        payload["ed25519_signature"] = signature.hex()
        logger.info(
            f"Decision signed: trace_id={payload.get('trace_id')}, "
            f"decision={payload.get('decision')}"
        )
        return payload
    except Exception as e:
        raise SovereignSigningError(f"ED25519 signing failed: {e}")


def verify_signature(
    payload: Dict[str, str],
    public_key_hex: str = None,
) -> bool:
    """
    Verify ED25519 signature on a Sovereign decision.

    Args:
        payload: Signed decision payload
        public_key_hex: Public key hex string (uses local key if None)

    Returns:
        True if signature is valid

    Raises:
        SovereignSigningError: If verification fails (tampered or invalid)
    """
    signature_hex = payload.get("ed25519_signature", "")
    if not signature_hex:
        raise SovereignSigningError(
            f"No signature in payload for trace {payload.get('trace_id')}"
        )

    decision_hash = payload.get("decision_hash", "")
    if not decision_hash:
        raise SovereignSigningError(
            f"No decision_hash in payload for trace {payload.get('trace_id')}"
        )

    # Recompute hash to detect mutation
    recomputed_hash = compute_decision_hash(payload)
    if recomputed_hash != decision_hash:
        raise SovereignSigningError(
            f"TAMPER DETECTED: decision_hash mismatch for trace {payload.get('trace_id')}. "
            f"Expected={recomputed_hash}, got={decision_hash}"
        )

    # Verify signature
    try:
        if public_key_hex:
            verify_key = load_public_key_from_hex(public_key_hex)
        else:
            _ensure_keys()
            verify_key = _verify_key

        signature = bytes.fromhex(signature_hex)
        message = decision_hash.encode("utf-8")
        verify_key.verify(signature, message)

        logger.info(f"Signature VERIFIED: trace_id={payload.get('trace_id')}")
        return True

    except InvalidSignature:
        raise SovereignSigningError(
            f"SIGNATURE INVALID for trace {payload.get('trace_id')}. "
            f"Payload has been tampered or signed with wrong key."
        )
    except Exception as e:
        raise SovereignSigningError(
            f"Signature verification error for trace {payload.get('trace_id')}: {e}"
        )


# ═══════════════════════════════════════════════════════════
# CONVENIENCE: Sign + Verify in one call
# ═══════════════════════════════════════════════════════════

def create_signed_decision(
    trace_id: str,
    decision: str,
    input_data: str,
    policy_reference: str = "bhiv.core.default_allow_policy",
    evaluator_id: str = "sovereign_bhiv_core",
) -> Dict[str, str]:
    """
    Build + hash + sign a Sovereign decision. One-shot function.

    Returns:
        Fully signed, verifiable decision payload
    """
    payload = build_canonical_decision(
        trace_id=trace_id,
        decision=decision,
        input_data=input_data,
        policy_reference=policy_reference,
        evaluator_id=evaluator_id,
    )
    return sign_decision(payload)
