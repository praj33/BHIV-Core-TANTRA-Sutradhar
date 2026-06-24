"""
Version Negotiator

Discovers and negotiates protocol versions with TANTRA participants.
Ensures schema compatibility before execution begins.

Usage:
    negotiator = VersionNegotiator(registry_path="TANTRA_INTEGRATION_REGISTRY.json")
    compatible = negotiator.check_compatibility("cet")
    if not compatible:
        raise IncompatibleVersionError(...)
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Optional, Tuple
from packaging.version import Version, InvalidVersion

logger = logging.getLogger(__name__)


class VersionInfo:
    """Version information for a participant."""

    def __init__(self, name: str, canonical_version: str, min_compatible: str):
        self.name = name
        self.canonical_version = canonical_version
        self.min_compatible_version = min_compatible
        self.detected_version: Optional[str] = None
        self.compatible: Optional[bool] = None
        self.check_error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "canonical_version": self.canonical_version,
            "min_compatible_version": self.min_compatible_version,
            "detected_version": self.detected_version,
            "compatible": self.compatible,
            "check_error": self.check_error,
        }


def _parse_version(v: str) -> Optional[Version]:
    """Parse a version string, returning None on failure."""
    try:
        return Version(v)
    except (InvalidVersion, TypeError):
        return None


class VersionNegotiator:
    """Negotiates version compatibility with TANTRA participants."""

    CORE_VERSION = "1.0.0"

    def __init__(self, registry_path: str = None):
        self._participants: Dict[str, VersionInfo] = {}

        if registry_path:
            self._load_from_registry(registry_path)

    def _load_from_registry(self, path: str):
        """Load version info from TANTRA_INTEGRATION_REGISTRY.json."""
        try:
            with open(path, "r") as f:
                registry = json.load(f)

            for key, participant in registry.get("participants", {}).items():
                canonical = participant.get("canonical_version", "1.0.0")
                min_compat = participant.get("min_compatible_version", "1.0.0")
                self._participants[key] = VersionInfo(key, canonical, min_compat)

            logger.info(f"[version] Loaded {len(self._participants)} participants")
        except Exception as e:
            logger.error(f"[version] Failed to load registry: {e}")

    def register(self, name: str, canonical_version: str, min_compatible: str = "1.0.0"):
        """Register version info for a participant."""
        self._participants[name] = VersionInfo(name, canonical_version, min_compatible)

    def detect_version(self, name: str, url: str, health_endpoint: str = "/health") -> Optional[str]:
        """Detect version from participant's health endpoint."""
        try:
            full_url = f"{url.rstrip('/')}{health_endpoint}"
            req = urllib.request.Request(full_url, headers={
                "ngrok-skip-browser-warning": "true",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                body = json.loads(r.read().decode())
                # Try common version fields
                version = (
                    body.get("version")
                    or body.get("api_version")
                    or body.get("schema_version")
                )
                if version and name in self._participants:
                    self._participants[name].detected_version = str(version)
                return str(version) if version else None

        except Exception as e:
            if name in self._participants:
                self._participants[name].check_error = str(e)[:200]
            return None

    def check_compatibility(self, name: str, detected_version: str = None) -> Tuple[bool, str]:
        """
        Check if a participant's version is compatible with Core.
        Returns (is_compatible, reason).
        """
        info = self._participants.get(name)
        if not info:
            return True, f"Unknown participant '{name}', assuming compatible"

        version_str = detected_version or info.detected_version or info.canonical_version
        version = _parse_version(version_str)
        min_version = _parse_version(info.min_compatible_version)

        if version is None:
            info.compatible = None
            return True, f"Cannot parse version '{version_str}', assuming compatible"

        if min_version is None:
            info.compatible = True
            return True, f"Cannot parse min_compatible '{info.min_compatible_version}', assuming compatible"

        is_compat = version >= min_version
        info.compatible = is_compat

        if is_compat:
            reason = f"{name} v{version_str} >= min v{info.min_compatible_version}"
        else:
            reason = f"{name} v{version_str} < min v{info.min_compatible_version} — INCOMPATIBLE"

        return is_compat, reason

    def check_all(self) -> dict:
        """Check compatibility of all participants."""
        results = {}
        all_compatible = True

        for name, info in self._participants.items():
            is_compat, reason = self.check_compatibility(name)
            results[name] = {
                **info.to_dict(),
                "reason": reason,
            }
            if is_compat is False:
                all_compatible = False

        return {
            "core_version": self.CORE_VERSION,
            "all_compatible": all_compatible,
            "participants": results,
        }

    def reject_incompatible(self) -> list:
        """Return list of incompatible participants that should be rejected."""
        rejected = []
        for name, info in self._participants.items():
            is_compat, reason = self.check_compatibility(name)
            if is_compat is False:
                rejected.append({"name": name, "reason": reason})
        return rejected
