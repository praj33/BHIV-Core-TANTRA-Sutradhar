"""
Compatibility Engine

Validates that specific versions of participants are compatible with each other.
Uses a compatibility matrix to prevent known-incompatible combinations.

Usage:
    engine = CompatibilityEngine()
    issues = engine.validate_ecosystem({
        "sarathi": "1.0.0",
        "bridge": "1.0.0",
        "cet": "1.0.0",
    })
    if issues:
        for issue in issues:
            print(f"INCOMPATIBLE: {issue}")
"""

import json
import logging
from typing import Dict, List, Optional
from packaging.version import Version, InvalidVersion

logger = logging.getLogger(__name__)

# Compatibility matrix: defines which versions of each service work together.
# Format: service -> version -> { compatible_with: { other_service: [compatible_versions] } }
COMPATIBILITY_MATRIX = {
    "sarathi": {
        "1.0.0": {
            "bridge": ["1.0.0", "1.1.0"],
            "cet": ["1.0.0"],
            "bhiv_core": ["1.0.0"],
        }
    },
    "bridge": {
        "1.0.0": {
            "sarathi": ["1.0.0"],
            "bhiv_core": ["1.0.0"],
        }
    },
    "cet": {
        "1.0.0": {
            "sarathi": ["1.0.0"],
            "bhiv_core": ["1.0.0"],
        }
    },
    "bucket": {
        "1.0.0": {
            "bhiv_core": ["1.0.0"],
        }
    },
    "sovereign": {
        "1.0.0": {
            "bhiv_core": ["1.0.0"],
        }
    },
    "insightflow": {
        "1.0.0": {
            "bhiv_core": ["1.0.0"],
        }
    },
}


class CompatibilityIssue:
    """Represents a compatibility issue between two participants."""

    def __init__(self, service_a: str, version_a: str, service_b: str, version_b: str, severity: str, message: str):
        self.service_a = service_a
        self.version_a = version_a
        self.service_b = service_b
        self.version_b = version_b
        self.severity = severity  # "error", "warning", "info"
        self.message = message

    def to_dict(self) -> dict:
        return {
            "service_a": self.service_a,
            "version_a": self.version_a,
            "service_b": self.service_b,
            "version_b": self.version_b,
            "severity": self.severity,
            "message": self.message,
        }

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.service_a} v{self.version_a} ↔ {self.service_b} v{self.version_b}: {self.message}"


class CompatibilityEngine:
    """Validates cross-service version compatibility."""

    def __init__(self, matrix: dict = None):
        self._matrix = matrix or COMPATIBILITY_MATRIX

    def validate_pair(self, service_a: str, version_a: str, service_b: str, version_b: str) -> Optional[CompatibilityIssue]:
        """Check if two specific service versions are compatible."""
        service_compat = self._matrix.get(service_a, {}).get(version_a, {})

        if service_b not in service_compat:
            # No compatibility data — untested combination
            return CompatibilityIssue(
                service_a, version_a, service_b, version_b,
                "warning",
                f"No compatibility data for {service_a} v{version_a} with {service_b}. Untested combination."
            )

        compatible_versions = service_compat[service_b]
        if version_b in compatible_versions:
            return None  # Compatible, no issue

        return CompatibilityIssue(
            service_a, version_a, service_b, version_b,
            "error",
            f"{service_a} v{version_a} is NOT compatible with {service_b} v{version_b}. "
            f"Compatible versions: {compatible_versions}"
        )

    def validate_ecosystem(self, versions: Dict[str, str]) -> List[CompatibilityIssue]:
        """
        Validate all pair-wise compatibility in the ecosystem.

        Args:
            versions: dict of {service_name: version_string}

        Returns:
            List of CompatibilityIssue objects (empty = all compatible)
        """
        issues = []
        services = list(versions.keys())

        for i, service_a in enumerate(services):
            for service_b in services[i + 1:]:
                issue = self.validate_pair(
                    service_a, versions[service_a],
                    service_b, versions[service_b],
                )
                if issue:
                    issues.append(issue)

        if issues:
            errors = [i for i in issues if i.severity == "error"]
            warnings = [i for i in issues if i.severity == "warning"]
            logger.info(
                f"[compat] Ecosystem check: {len(errors)} errors, {len(warnings)} warnings"
            )
        else:
            logger.info("[compat] Ecosystem check: all compatible")

        return issues

    def get_compatible_versions(self, service: str, version: str) -> dict:
        """Get all compatible versions for a given service version."""
        return self._matrix.get(service, {}).get(version, {})

    def is_ecosystem_valid(self, versions: Dict[str, str]) -> bool:
        """Quick check: are there any blocking (error-level) incompatibilities?"""
        issues = self.validate_ecosystem(versions)
        return not any(i.severity == "error" for i in issues)

    def generate_report(self, versions: Dict[str, str]) -> dict:
        """Generate full compatibility report."""
        issues = self.validate_ecosystem(versions)
        return {
            "ecosystem_versions": versions,
            "is_valid": not any(i.severity == "error" for i in issues),
            "total_issues": len(issues),
            "errors": [i.to_dict() for i in issues if i.severity == "error"],
            "warnings": [i.to_dict() for i in issues if i.severity == "warning"],
            "info": [i.to_dict() for i in issues if i.severity == "info"],
        }
