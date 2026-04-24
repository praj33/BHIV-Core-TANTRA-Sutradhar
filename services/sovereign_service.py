"""
External Sovereign Service -- Phase 2

Standalone HTTP service that receives decision requests from BHIV Core
and returns ALLOW/DENY decisions with decision_hash.

Run:
    python services/sovereign_service.py

Endpoint:
    POST /sovereign/decide

Uses the SAME logic as internal SovereignCore -- deterministic output.
"""

import hashlib
import json
import uuid
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = int(os.environ.get("SOVEREIGN_PORT", 9001))


def get_timestamp():
    return datetime.now(timezone.utc).isoformat()


def compute_input_hash(input_data: str) -> str:
    return hashlib.sha256(input_data.encode("utf-8")).hexdigest()


def compute_decision_hash(trace_id: str, decision: str, input_hash: str, timestamp: str) -> str:
    """Deterministic hash binding decision to trace."""
    binding = f"{trace_id}:{decision}:{input_hash}:{timestamp}"
    return hashlib.sha256(binding.encode("utf-8")).hexdigest()


# Default policies (same as internal SovereignCore)
POLICIES = {}


def evaluate_policy(input_data: str, context: dict) -> tuple:
    """Evaluate input against policies. Returns (decision, policy_reference)."""
    for policy_name, policy_rule in POLICIES.items():
        if policy_rule.get("type") == "deny":
            deny_keywords = policy_rule.get("deny_keywords", [])
            if any(kw.lower() in input_data.lower() for kw in deny_keywords):
                return "DENY", policy_name
    return "ALLOW", "bhiv.core.default_allow_policy"


class SovereignHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[SOVEREIGN] {args[0]}")

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "healthy", "service": "sovereign_core"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/sovereign/decide":
            self._handle_decide()
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_decide(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            trace_id = data.get("trace_id")
            input_data = data.get("input", "")
            context = data.get("context", {})

            if not trace_id:
                self._send_json(400, {"error": "trace_id is required"})
                return

            # Compute input hash
            input_hash = compute_input_hash(input_data)

            # Evaluate policy (same logic as internal)
            decision, policy_reference = evaluate_policy(input_data, context)

            # Generate deterministic decision hash
            timestamp = get_timestamp()
            decision_hash = compute_decision_hash(trace_id, decision, input_hash, timestamp)

            response = {
                "trace_id": trace_id,
                "decision": decision,
                "policy_reference": policy_reference,
                "input_hash": input_hash,
                "decision_hash": decision_hash,
                "timestamp": timestamp,
            }

            print(f"[SOVEREIGN] trace_id={trace_id} decision={decision} policy={policy_reference}")
            self._send_json(200, response)

        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def main():
    # Load policies from env if available
    policy_env = os.environ.get("SOVEREIGN_POLICIES", "")
    if policy_env:
        try:
            global POLICIES
            POLICIES = json.loads(policy_env)
        except json.JSONDecodeError:
            pass

    server = HTTPServer(("0.0.0.0", PORT), SovereignHandler)
    print(f"[SOVEREIGN] External Sovereign Core running on port {PORT}")
    print(f"[SOVEREIGN] POST /sovereign/decide")
    print(f"[SOVEREIGN] GET  /health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SOVEREIGN] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
