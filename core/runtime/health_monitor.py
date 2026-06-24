"""
Rich Health Monitor

Monitors participant health with latency tracking, error rates,
dependency health, and cold start detection.

Usage:
    monitor = HealthMonitor(registry_path="TANTRA_INTEGRATION_REGISTRY.json")
    report = await monitor.check_all()
    print(report)  # Rich health data for all participants
"""

import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ParticipantHealth:
    """Tracks health metrics for a single participant."""

    def __init__(self, name: str, url: str, health_endpoint: str = "/health"):
        self.name = name
        self.url = url
        self.health_endpoint = health_endpoint
        self.status = "unknown"
        self.latency_ms: Optional[float] = None
        self.last_check: Optional[str] = None
        self.last_success: Optional[str] = None
        self.error_count = 0
        self.success_count = 0
        self.consecutive_failures = 0
        self.last_error: Optional[str] = None
        self.cold_start_detected = False
        self._latency_history: list = []

    def check(self) -> dict:
        """Perform health check and return result."""
        url = f"{self.url.rstrip('/')}{self.health_endpoint}"
        start = time.time()
        self.last_check = datetime.now(timezone.utc).isoformat()

        try:
            req = urllib.request.Request(url, headers={
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "BHIV-Core-HealthMonitor/1.0",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                latency = (time.time() - start) * 1000
                body = json.loads(r.read().decode())

                self.latency_ms = round(latency, 1)
                self._latency_history.append(self.latency_ms)
                if len(self._latency_history) > 100:
                    self._latency_history = self._latency_history[-100:]

                self.success_count += 1
                self.consecutive_failures = 0
                self.last_success = self.last_check
                self.last_error = None

                # Cold start detection: latency > 5000ms suggests Render cold start
                self.cold_start_detected = latency > 5000

                # Determine status based on latency
                if latency < 2000:
                    self.status = "healthy"
                elif latency < 5000:
                    self.status = "degraded"
                else:
                    self.status = "slow"

                return self.to_dict(extra={"response": body})

        except urllib.error.HTTPError as e:
            latency = (time.time() - start) * 1000
            self.latency_ms = round(latency, 1)
            self.error_count += 1
            self.consecutive_failures += 1
            self.last_error = f"HTTP {e.code}"
            self.status = "error"
            return self.to_dict()

        except Exception as e:
            latency = (time.time() - start) * 1000
            self.latency_ms = round(latency, 1)
            self.error_count += 1
            self.consecutive_failures += 1
            self.last_error = str(e)[:200]
            self.status = "unreachable"
            return self.to_dict()

    @property
    def error_rate(self) -> float:
        """Error rate as fraction (0.0 to 1.0)."""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return round(self.error_count / total, 4)

    @property
    def avg_latency_ms(self) -> Optional[float]:
        """Average latency over recent checks."""
        if not self._latency_history:
            return None
        return round(sum(self._latency_history) / len(self._latency_history), 1)

    @property
    def p95_latency_ms(self) -> Optional[float]:
        """95th percentile latency."""
        if not self._latency_history:
            return None
        sorted_latencies = sorted(self._latency_history)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def to_dict(self, extra: dict = None) -> dict:
        result = {
            "name": self.name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "error_rate": self.error_rate,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "last_check": self.last_check,
            "last_success": self.last_success,
            "last_error": self.last_error,
            "cold_start_detected": self.cold_start_detected,
        }
        if extra:
            result.update(extra)
        return result


class HealthMonitor:
    """Monitors health of all TANTRA participants."""

    def __init__(self, registry_path: str = None):
        self._participants: Dict[str, ParticipantHealth] = {}
        self._check_count = 0
        self._start_time = datetime.now(timezone.utc)

        if registry_path:
            self._load_from_registry(registry_path)

    def _load_from_registry(self, path: str):
        """Load participants from TANTRA_INTEGRATION_REGISTRY.json."""
        try:
            with open(path, "r") as f:
                registry = json.load(f)

            for key, participant in registry.get("participants", {}).items():
                url = participant.get("url", "")
                health_ep = participant.get("health_endpoint", "/health")
                if url and key != "bhiv_core":  # Skip self
                    self.register(key, url, health_ep)

            logger.info(f"[health] Loaded {len(self._participants)} participants from registry")
        except Exception as e:
            logger.error(f"[health] Failed to load registry: {e}")

    def register(self, name: str, url: str, health_endpoint: str = "/health"):
        """Register a participant for monitoring."""
        self._participants[name] = ParticipantHealth(name, url, health_endpoint)

    def check(self, name: str) -> Optional[dict]:
        """Check health of a specific participant."""
        p = self._participants.get(name)
        if not p:
            return None
        return p.check()

    def check_all(self) -> dict:
        """Check health of all participants."""
        self._check_count += 1
        results = {}
        healthy = 0
        degraded = 0
        unreachable = 0

        for name, participant in self._participants.items():
            result = participant.check()
            results[name] = result
            if result["status"] in ("healthy",):
                healthy += 1
            elif result["status"] in ("degraded", "slow"):
                degraded += 1
            else:
                unreachable += 1

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "check_number": self._check_count,
            "monitor_uptime_seconds": (datetime.now(timezone.utc) - self._start_time).total_seconds(),
            "summary": {
                "total": len(self._participants),
                "healthy": healthy,
                "degraded": degraded,
                "unreachable": unreachable,
            },
            "participants": results,
        }

    def get_core_health_response(self) -> dict:
        """Generate rich health response for Core's /health endpoint."""
        report = self.check_all()
        dependencies = {}
        for name, data in report["participants"].items():
            dependencies[name] = {
                "status": data["status"],
                "latency_ms": data["latency_ms"],
                "error_rate": data["error_rate"],
                "last_check": data["last_check"],
            }

        return {
            "service": "bhiv-core",
            "status": "healthy" if report["summary"]["unreachable"] == 0 else "degraded",
            "version": "1.0.0",
            "uptime_seconds": report["monitor_uptime_seconds"],
            "dependencies": dependencies,
            "chain_health": {
                "total_participants": report["summary"]["total"],
                "healthy": report["summary"]["healthy"],
                "degraded": report["summary"]["degraded"],
                "unreachable": report["summary"]["unreachable"],
            },
        }
