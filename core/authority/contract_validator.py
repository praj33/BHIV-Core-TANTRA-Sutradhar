"""
TANTRA Contract Schema Validator — Phase 2

Strict schema validation at ALL system boundaries.
Rejects:
  - Unknown fields
  - Missing required fields
  - Type mismatches
  - Loosely structured payloads

Boundaries:
  Core <-> Sovereign
  Core <-> Sarathi
  Core <-> Execution
  Core <-> Bucket
  Core <-> Pravah
"""

import hashlib
import json
import logging
from typing import Dict, Any, List, Optional, Set
from collections import OrderedDict

logger = logging.getLogger(__name__)


class ContractValidationError(Exception):
    """Raised when a payload violates the strict contract schema."""
    pass


# ═══════════════════════════════════════════════════════════
# SCHEMA DEFINITIONS (STRICT)
# ═══════════════════════════════════════════════════════════

# Core -> Sovereign: Decision Request
SOVEREIGN_REQUEST_SCHEMA = {
    "required": {"trace_id", "input", "context"},
    "allowed": {"trace_id", "input", "context"},
    "types": {"trace_id": str, "input": str, "context": dict},
}

# Sovereign -> Core: Decision Response
SOVEREIGN_RESPONSE_SCHEMA = {
    "required": {"decision", "input_hash", "decision_hash"},
    "allowed": {"decision", "input_hash", "decision_hash", "policy_reference", "timestamp"},
    "types": {"decision": str, "input_hash": str, "decision_hash": str},
    "enum": {"decision": {"ALLOW", "DENY"}},
}

# Core -> Sarathi: Enforcement Request
SARATHI_REQUEST_SCHEMA = {
    "required": {"trace_id", "decision", "decision_hash"},
    "allowed": {"trace_id", "decision", "decision_hash", "execution_payload"},
    "types": {"trace_id": str, "decision": str, "decision_hash": str},
}

# Sarathi -> Core: Enforcement Response
SARATHI_RESPONSE_SCHEMA = {
    "required": {"status"},
    "allowed": {"status", "validation_result", "execution_token", "failure_reason", "timestamp"},
    "types": {"status": str},
    "enum": {"status": {"CLEARED", "BLOCKED"}},
}

# Core -> Execution: Execution Payload
EXECUTION_PAYLOAD_SCHEMA = {
    "required": {"trace_id", "execution_token", "task_payload"},
    "allowed": {"trace_id", "execution_token", "task_payload", "execution_id"},
    "types": {"trace_id": str, "execution_token": str},
}

# Core -> Bucket: Truth Record
BUCKET_RECORD_SCHEMA = {
    "required": {"trace_id", "execution_id", "execution_token", "decision", "timestamp", "payload_hash"},
    "allowed": {"trace_id", "execution_id", "execution_token", "decision", "timestamp", "payload_hash",
                "bucket_write_id", "bucket_write_timestamp", "record_hash"},
    "types": {"trace_id": str, "execution_id": str, "execution_token": str,
              "decision": str, "timestamp": str, "payload_hash": str},
}

# Core -> Pravah: Observation Signal
PRAVAH_SIGNAL_SCHEMA = {
    "required": {"trace_id", "event_type", "timestamp", "payload"},
    "allowed": {"trace_id", "event_type", "timestamp", "payload", "source"},
    "types": {"trace_id": str, "event_type": str, "timestamp": str, "payload": dict},
}

# Registry of all schemas
CONTRACT_SCHEMAS = {
    "sovereign_request": SOVEREIGN_REQUEST_SCHEMA,
    "sovereign_response": SOVEREIGN_RESPONSE_SCHEMA,
    "sarathi_request": SARATHI_REQUEST_SCHEMA,
    "sarathi_response": SARATHI_RESPONSE_SCHEMA,
    "execution_payload": EXECUTION_PAYLOAD_SCHEMA,
    "bucket_record": BUCKET_RECORD_SCHEMA,
    "pravah_signal": PRAVAH_SIGNAL_SCHEMA,
}


# ═══════════════════════════════════════════════════════════
# VALIDATION ENGINE
# ═══════════════════════════════════════════════════════════

def validate_contract(
    payload: Dict[str, Any],
    schema_name: str,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    Validate a payload against a strict contract schema.

    Args:
        payload: The data to validate
        schema_name: Name of the schema (from CONTRACT_SCHEMAS)
        strict: If True, reject unknown fields. Always True in production.

    Returns:
        Validated payload (unchanged if valid)

    Raises:
        ContractValidationError: If validation fails
    """
    if schema_name not in CONTRACT_SCHEMAS:
        raise ContractValidationError(
            f"Unknown schema: {schema_name}. "
            f"Valid schemas: {list(CONTRACT_SCHEMAS.keys())}"
        )

    schema = CONTRACT_SCHEMAS[schema_name]
    errors = []

    # Check required fields
    required = schema.get("required", set())
    for field in required:
        if field not in payload:
            errors.append(f"Missing required field: '{field}'")
        elif payload[field] is None:
            errors.append(f"Required field '{field}' is null")

    # Check for unknown fields (strict mode)
    if strict:
        allowed = schema.get("allowed", set())
        for field in payload:
            if field not in allowed:
                errors.append(f"Unknown field: '{field}' (not in contract)")

    # Check types
    types = schema.get("types", {})
    for field, expected_type in types.items():
        if field in payload and payload[field] is not None:
            if not isinstance(payload[field], expected_type):
                errors.append(
                    f"Type mismatch: '{field}' expected {expected_type.__name__}, "
                    f"got {type(payload[field]).__name__}"
                )

    # Check enums
    enums = schema.get("enum", {})
    for field, valid_values in enums.items():
        if field in payload and payload[field] not in valid_values:
            errors.append(
                f"Invalid value: '{field}' = '{payload[field]}', "
                f"expected one of {valid_values}"
            )

    # Check trace_id format (if present)
    if "trace_id" in payload and payload.get("trace_id"):
        trace_id = payload["trace_id"]
        if not isinstance(trace_id, str) or len(trace_id) < 8:
            errors.append(f"Invalid trace_id format: '{trace_id}'")

    if errors:
        raise ContractValidationError(
            f"Contract '{schema_name}' validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return payload


def validate_trace_continuity(
    payloads: List[Dict[str, Any]],
    expected_trace_id: str,
) -> bool:
    """
    Verify that ALL payloads in a chain carry the SAME trace_id.
    No regeneration, no mutation.

    Args:
        payloads: List of dicts with 'trace_id' field
        expected_trace_id: The trace_id that must be present everywhere

    Returns:
        True if all match

    Raises:
        ContractValidationError: If any trace_id differs
    """
    for i, payload in enumerate(payloads):
        actual = payload.get("trace_id", "")
        if actual != expected_trace_id:
            raise ContractValidationError(
                f"Trace continuity BROKEN at step {i}: "
                f"expected='{expected_trace_id}', got='{actual}'"
            )
    return True


def get_contract_summary() -> Dict[str, Any]:
    """Get summary of all registered contracts."""
    summary = {}
    for name, schema in CONTRACT_SCHEMAS.items():
        summary[name] = {
            "required_fields": sorted(schema.get("required", set())),
            "allowed_fields": sorted(schema.get("allowed", set())),
            "typed_fields": list(schema.get("types", {}).keys()),
            "enum_fields": list(schema.get("enum", {}).keys()),
        }
    return summary
