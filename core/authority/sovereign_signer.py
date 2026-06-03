"""
Sovereign Signer — ED25519 Cryptographic Authority Layer
Aligned with Sarathi CORE_INTEGRATION spec (Hemanth).

Wire contract:
  - Schema: tantra.decision.v1
  - 11 fields, FIXED order (NOT alphabetical)
  - Signature: Ed25519 (RFC 8032), base64url no-pad encoding
  - decision_hash: SHA-256 of 6-field canonical JSON (FIXED order)
  - decision_id: uuid_shape(SHA256(canonical({trace_id, input_hash, evaluator_id})))
  - API key: Core-generated, fingerprint shared with Sarathi

Rules:
  - Private key NEVER in payloads
  - Signature signs the FULL canonical payload (all 10 non-signature fields)
  - No fallback signing modes
  - No mutation post-signing
  - Field order is part of what gets signed
  - Pure Ed25519 only (NOT Ed25519ph, NOT Ed25519ctx)
"""

import base64
import hashlib
import json
import os
import secrets
import logging
from typing import Dict, Any, Optional, Set
from collections import OrderedDict
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from core.trace.time_sync import get_normalized_timestamp

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CONSTANTS — locked to Sarathi contract
# ═══════════════════════════════════════════════════════════

SCHEMA_VERSION = "tantra.decision.v1"
EVALUATOR_ID = "bhiv.sovereign.decision.prod.v1"
KEY_ID = f"{EVALUATOR_ID}#ed25519-2026-05"
VALID_VERDICTS = {"ALLOW", "DENY", "ESCALATE"}

# Evaluator registry
AUTHORIZED_EVALUATORS: Set[str] = {
    "bhiv.sovereign.decision.prod.v1",
}

# ═══════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════

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
    if os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE):
        with open(PRIVATE_KEY_FILE, "rb") as f:
            _signing_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(PUBLIC_KEY_FILE, "rb") as f:
            _verify_key = serialization.load_pem_public_key(f.read())
        logger.info("Loaded existing ED25519 key pair")
        return
    _signing_key = Ed25519PrivateKey.generate()
    _verify_key = _signing_key.public_key()
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
    """Get the public key as 64-char hex string."""
    _ensure_keys()
    raw = _verify_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex()


def load_public_key_from_hex(hex_key: str) -> Ed25519PublicKey:
    """Load a public key from hex string."""
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_key))


# ═══════════════════════════════════════════════════════════
# API KEY MANAGEMENT (§6)
# ═══════════════════════════════════════════════════════════

API_KEY_FILE = os.path.join(KEY_DIR, "api_key.secret")
API_FINGERPRINT_FILE = os.path.join(KEY_DIR, "api_key_fingerprint.txt")


def ensure_api_key() -> tuple:
    """
    Generate or load the API key.
    Returns (secret, fingerprint).
    Secret goes in X-API-Key header.
    Fingerprint goes to Sarathi out-of-band.
    """
    os.makedirs(KEY_DIR, exist_ok=True)
    if os.path.exists(API_KEY_FILE) and os.path.exists(API_FINGERPRINT_FILE):
        with open(API_KEY_FILE, "r") as f:
            secret = f.read().strip()
        with open(API_FINGERPRINT_FILE, "r") as f:
            fingerprint = f.read().strip()
        return secret, fingerprint

    secret = secrets.token_hex(32)  # 64-char hex string
    fingerprint = hashlib.sha256(secret.encode()).hexdigest()
    with open(API_KEY_FILE, "w") as f:
        f.write(secret)
    with open(API_FINGERPRINT_FILE, "w") as f:
        f.write(fingerprint)
    logger.info("Generated new API key")
    return secret, fingerprint


def get_api_key() -> str:
    """Get the raw API key secret (for X-API-Key header)."""
    secret, _ = ensure_api_key()
    return secret


def get_api_fingerprint() -> str:
    """Get the API key fingerprint (for Sarathi registration)."""
    _, fingerprint = ensure_api_key()
    return fingerprint


# ═══════════════════════════════════════════════════════════
# BASE64URL NO-PAD HELPERS
# ═══════════════════════════════════════════════════════════

def b64url_encode(data: bytes) -> str:
    """base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(s: str) -> bytes:
    """base64url decode without padding."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ═══════════════════════════════════════════════════════════
# RFC3339 NANO TIMESTAMP
# ═══════════════════════════════════════════════════════════

def get_rfc3339_nano() -> str:
    """RFC3339 with nanoseconds, UTC."""
    now = datetime.now(timezone.utc)
    # Python max precision is microseconds — pad to nanoseconds
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond:06d}000Z"


# ═══════════════════════════════════════════════════════════
# DECISION HASH (§3.1) — 6-field FIXED ORDER
# ═══════════════════════════════════════════════════════════

# The 6 fields in EXACT order for decision_hash computation
DECISION_HASH_FIELDS = [
    "schema_version", "trace_id", "input_hash",
    "verdict", "policy_reference", "evaluator_id",
]


def compute_decision_hash(
    schema_version: str,
    trace_id: str,
    input_hash: str,
    verdict: str,
    policy_reference: str,
    evaluator_id: str,
) -> str:
    """
    Compute decision_hash per §3.1.
    SHA-256 of canonical 6-field JSON in FIXED order (NOT alphabetical).
    Timestamp intentionally NOT in the material.
    """
    canonical = (
        '{"schema_version":' + json.dumps(schema_version) + ','
        '"trace_id":' + json.dumps(trace_id) + ','
        '"input_hash":' + json.dumps(input_hash) + ','
        '"verdict":' + json.dumps(verdict) + ','
        '"policy_reference":' + json.dumps(policy_reference) + ','
        '"evaluator_id":' + json.dumps(evaluator_id) + '}'
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════
# DECISION ID (§3.2) — deterministic UUID-shape
# ═══════════════════════════════════════════════════════════

def compute_decision_id(trace_id: str, input_hash: str, evaluator_id: str) -> str:
    """
    Compute decision_id per §3.2.
    canonical = '{"trace_id":"...","input_hash":"...","evaluator_id":"..."}'
    FIXED ORDER: trace_id, input_hash, evaluator_id (NOT alphabetical).
    UUID shape: 8-4-4-4-12 from first 32 hex chars of SHA-256.
    """
    canonical = (
        '{"trace_id":' + json.dumps(trace_id) + ','
        '"input_hash":' + json.dumps(input_hash) + ','
        '"evaluator_id":' + json.dumps(evaluator_id) + '}'
    )
    raw_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    h = raw_hash[:32]
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ═══════════════════════════════════════════════════════════
# CANONICAL PAYLOAD (§2.2) — 10 non-signature fields, FIXED ORDER
# ═══════════════════════════════════════════════════════════

def _build_canonical_bytes(payload_no_sig: OrderedDict) -> bytes:
    """
    Build canonical bytes for signing per §4.1.
    FIXED field order from §2.2 (NOT alphabetical).
    No whitespace. UTF-8. No trailing newline.
    """
    # Manual JSON construction to guarantee field order
    parts = []
    for key, value in payload_no_sig.items():
        parts.append(json.dumps(key) + ":" + json.dumps(value))
    canonical = "{" + ",".join(parts) + "}"
    return canonical.encode("utf-8")


# ═══════════════════════════════════════════════════════════
# BUILD + SIGN DECISION (§2 + §3 + §4)
# ═══════════════════════════════════════════════════════════

def build_canonical_decision(
    trace_id: str,
    input_data: str,
    verdict: str = "ALLOW",
    policy_reference: str = "bhiv.core.default_allow_policy@v1.0",
    evaluator_id: str = EVALUATOR_ID,
    enforcement_binding: str = None,
    timestamp: str = None,
) -> Dict[str, Any]:
    """
    Build a canonical Sovereign decision payload per §2.2.
    Returns the UNSIGNED payload (11 fields, signature empty).
    """
    if verdict not in VALID_VERDICTS:
        raise SovereignSigningError(f"Invalid verdict: '{verdict}'. Must be one of {VALID_VERDICTS}")
    if evaluator_id not in AUTHORIZED_EVALUATORS:
        raise EvaluatorIdentityError(f"Unauthorized evaluator: '{evaluator_id}'.")
    if not trace_id or len(trace_id) < 8:
        raise SovereignSigningError(f"Invalid trace_id: '{trace_id}'")

    ts = timestamp or get_rfc3339_nano()
    input_hash = hashlib.sha256(input_data.encode("utf-8")).hexdigest()
    decision_id = compute_decision_id(trace_id, input_hash, evaluator_id)
    decision_hash = compute_decision_hash(
        SCHEMA_VERSION, trace_id, input_hash, verdict, policy_reference, evaluator_id,
    )

    if enforcement_binding is None:
        enforcement_binding = f"CLEARED:Decision {verdict} validated"

    # 11 fields in §2.2 FIXED order
    payload = OrderedDict([
        ("schema_version", SCHEMA_VERSION),
        ("trace_id", trace_id),
        ("input_hash", input_hash),
        ("decision_id", decision_id),
        ("decision_hash", decision_hash),
        ("verdict", verdict),
        ("policy_reference", policy_reference),
        ("evaluator_id", evaluator_id),
        ("enforcement_binding", enforcement_binding),
        ("timestamp", ts),
        ("signature", {
            "alg": "Ed25519",
            "key_id": KEY_ID,
            "encoding": "base64url_no_pad",
            "value": "",
        }),
    ])
    return dict(payload)


def sign_decision(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sign a canonical decision payload per §4.2.
    1. Build JSON with all 10 NON-signature fields in §2.2 order.
    2. Canonicalize (fixed order, no whitespace, UTF-8).
    3. Ed25519.Sign(private_key, canonical_bytes).
    4. signature.value = base64url_no_pad(sig_bytes).
    """
    _ensure_keys()

    # Build the 10 non-signature fields in FIXED order
    payload_no_sig = OrderedDict([
        ("schema_version", payload["schema_version"]),
        ("trace_id", payload["trace_id"]),
        ("input_hash", payload["input_hash"]),
        ("decision_id", payload["decision_id"]),
        ("decision_hash", payload["decision_hash"]),
        ("verdict", payload["verdict"]),
        ("policy_reference", payload["policy_reference"]),
        ("evaluator_id", payload["evaluator_id"]),
        ("enforcement_binding", payload["enforcement_binding"]),
        ("timestamp", payload["timestamp"]),
    ])

    canonical_bytes = _build_canonical_bytes(payload_no_sig)
    sig_bytes = _signing_key.sign(canonical_bytes)  # 64 raw bytes
    sig_value = b64url_encode(sig_bytes)

    payload["signature"] = {
        "alg": "Ed25519",
        "key_id": KEY_ID,
        "encoding": "base64url_no_pad",
        "value": sig_value,
    }

    logger.info(f"Decision signed: trace_id={payload['trace_id']}, verdict={payload['verdict']}")
    return payload


def verify_signature(
    payload: Dict[str, Any],
    public_key_hex: str = None,
) -> bool:
    """
    Verify Ed25519 signature on a Sovereign decision per §5.
    Recomputes canonical bytes from 10 non-signature fields in FIXED order.
    """
    sig_obj = payload.get("signature", {})
    sig_value = sig_obj.get("value", "")
    if not sig_value:
        raise SovereignSigningError(f"No signature value for trace {payload.get('trace_id')}")

    # Verify decision_hash integrity (§5 step 9)
    recomputed_hash = compute_decision_hash(
        payload["schema_version"], payload["trace_id"], payload["input_hash"],
        payload["verdict"], payload["policy_reference"], payload["evaluator_id"],
    )
    if recomputed_hash != payload.get("decision_hash"):
        raise SovereignSigningError(
            f"TAMPER DETECTED: decision_hash mismatch for trace {payload.get('trace_id')}. "
            f"Expected={recomputed_hash}, got={payload.get('decision_hash')}"
        )

    # Verify decision_id integrity (§5 step 10)
    recomputed_id = compute_decision_id(
        payload["trace_id"], payload["input_hash"], payload["evaluator_id"],
    )
    if recomputed_id != payload.get("decision_id"):
        raise SovereignSigningError(
            f"TAMPER DETECTED: decision_id mismatch for trace {payload.get('trace_id')}."
        )

    # Recompute canonical bytes and verify signature
    payload_no_sig = OrderedDict([
        ("schema_version", payload["schema_version"]),
        ("trace_id", payload["trace_id"]),
        ("input_hash", payload["input_hash"]),
        ("decision_id", payload["decision_id"]),
        ("decision_hash", payload["decision_hash"]),
        ("verdict", payload["verdict"]),
        ("policy_reference", payload["policy_reference"]),
        ("evaluator_id", payload["evaluator_id"]),
        ("enforcement_binding", payload["enforcement_binding"]),
        ("timestamp", payload["timestamp"]),
    ])

    canonical_bytes = _build_canonical_bytes(payload_no_sig)
    sig_bytes = b64url_decode(sig_value)

    try:
        if public_key_hex:
            verify_key = load_public_key_from_hex(public_key_hex)
        else:
            _ensure_keys()
            verify_key = _verify_key
        verify_key.verify(sig_bytes, canonical_bytes)
        logger.info(f"Signature VERIFIED: trace_id={payload.get('trace_id')}")
        return True
    except InvalidSignature:
        raise SovereignSigningError(
            f"SIGNATURE INVALID for trace {payload.get('trace_id')}. "
            f"Payload tampered or signed with wrong key."
        )


def create_signed_decision(
    trace_id: str,
    input_data: str,
    verdict: str = "ALLOW",
    policy_reference: str = "bhiv.core.default_allow_policy@v1.0",
    evaluator_id: str = EVALUATOR_ID,
) -> Dict[str, Any]:
    """Build + sign a Sovereign decision. One-shot function."""
    payload = build_canonical_decision(
        trace_id=trace_id, input_data=input_data, verdict=verdict,
        policy_reference=policy_reference, evaluator_id=evaluator_id,
    )
    return sign_decision(payload)


# ═══════════════════════════════════════════════════════════
# HTTP HEADERS for /sarathi/enforce (§2.1)
# ═══════════════════════════════════════════════════════════

def get_sarathi_headers(trace_id: str) -> Dict[str, str]:
    """Get required HTTP headers for posting to /sarathi/enforce."""
    return {
        "Content-Type": "application/json",
        "X-API-Key": get_api_key(),
        "X-Sarathi-Trace-ID": trace_id,
    }


# ═══════════════════════════════════════════════════════════
# POST-EXECUTION RECEIPT (§8)
# ═══════════════════════════════════════════════════════════

def build_receipt(
    execution_id: str,
    decision_id: str,
    response_hash: str,
    received_body_hash: str,
    chain_binding_hash: str,
    storage_path: str,
) -> Dict[str, str]:
    """
    Build a post-execution receipt per §8.4.
    12 fields. Receipt signing uses ALPHABETICAL key ordering + hex signature.
    """
    _ensure_keys()
    pub_hex = get_public_key_hex()
    persisted_at = get_rfc3339_nano()

    # For Core, received_body_hash == observed_response_hash (§8.4 note)
    receipt = OrderedDict([
        ("schema_version", "sarathi.live.receipt/v1.0"),
        ("peer", "core"),
        ("execution_id", execution_id),
        ("decision_id", decision_id),
        ("response_hash", response_hash),
        ("received_body_hash", received_body_hash),
        ("observed_response_hash", received_body_hash),  # Same for Core (§8.4)
        ("chain_binding_hash", chain_binding_hash),
        ("persisted_at", persisted_at),
        ("storage_path", storage_path),
        ("peer_public_key_hex", pub_hex),
        ("receipt_signature", ""),  # Placeholder for signing
    ])

    # Sign per §8.5: RFC 8785 with ALPHABETICAL key ordering, hex signature
    canonical = json.dumps(dict(receipt), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    canonical_bytes = canonical.encode("utf-8")
    sig_bytes = _signing_key.sign(canonical_bytes)
    receipt["receipt_signature"] = sig_bytes.hex()  # 128 hex chars

    return dict(receipt)


def verify_receipt_signature(receipt: Dict[str, str], public_key_hex: str = None) -> bool:
    """Verify a receipt's Ed25519 signature (alphabetical canonical, hex sig)."""
    sig_hex = receipt.get("receipt_signature", "")
    if not sig_hex:
        raise SovereignSigningError("No receipt_signature")

    # Recompute canonical with empty signature
    receipt_copy = dict(receipt)
    receipt_copy["receipt_signature"] = ""
    canonical = json.dumps(receipt_copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    canonical_bytes = canonical.encode("utf-8")
    sig_bytes = bytes.fromhex(sig_hex)

    try:
        if public_key_hex:
            verify_key = load_public_key_from_hex(public_key_hex)
        else:
            _ensure_keys()
            verify_key = _verify_key
        verify_key.verify(sig_bytes, canonical_bytes)
        return True
    except InvalidSignature:
        raise SovereignSigningError("Receipt signature INVALID")


# ═══════════════════════════════════════════════════════════
# REGISTRATION DATA (§6.3) — what to send Sarathi out-of-band
# ═══════════════════════════════════════════════════════════

def get_registration_data() -> Dict[str, str]:
    """Get all data that must be sent to Sarathi for registration."""
    _ensure_keys()
    return {
        "evaluator_id": EVALUATOR_ID,
        "public_key": get_public_key_hex(),
        "key_id": KEY_ID,
        "schema_version": SCHEMA_VERSION,
        "algorithm": "Ed25519",
        "api_key_fingerprint": get_api_fingerprint(),
        "decision_id_formula": "uuid_shape(SHA256(canonical({trace_id, input_hash, evaluator_id})))",
        "peer_core_public_key": get_public_key_hex(),  # Same key for both
    }
