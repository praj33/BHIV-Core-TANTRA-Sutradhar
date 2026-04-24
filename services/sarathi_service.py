"""
External Sarathi Service -- Phase 3

Standalone HTTP service that receives enforcement requests from BHIV Core
and returns CLEARED/BLOCKED with execution_token.

Run:
    python services/sarathi_service.py

Endpoint:
    POST /sarathi/enforce

Verifies decision_hash before clearing execution.
No execution without token. Strict ALLOW/DENY only.
"""

import hashlib
import json
import uuid
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = int(os.environ.get("SARATHI_PORT", 9002))

# Track issued tokens to prevent replay
_issued_tokens = set()
_used_decision_hashes = set()


def get_timestamp():
    return datetime.now(timezone.utc).isoformat()


def generate_execution_token(trace_id: str, decision_hash: str) -> str:
    """Generate a unique, non-replayable execution token."""
    token_input = f"{trace_id}:{decision_hash}:{uuid.uuid4()}"
    return hashlib.sha256(token_input.encode("utf-8")).hexdigest()


class SarathiHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[SARATHI] {args[0]}")

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "healthy", "service": "sarathi_enforcer"})
        elif self.path.startswith("/sarathi/validate-token"):
            self._handle_validate_token()
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/sarathi/enforce":
            self._handle_enforce()
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_enforce(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            trace_id = data.get("trace_id")
            decision = data.get("decision")
            execution_payload = data.get("execution_payload", {})
            decision_hash = data.get("decision_hash", "")

            if not trace_id:
                self._send_json(400, {"error": "trace_id is required"})
                return

            if not decision:
                self._send_json(400, {"error": "decision is required"})
                return

            timestamp = get_timestamp()

            # Check for replay attack
            if decision_hash and decision_hash in _used_decision_hashes:
                print(f"[SARATHI] REPLAY REJECTED: trace_id={trace_id}")
                self._send_json(403, {
                    "trace_id": trace_id,
                    "status": "BLOCKED",
                    "validation_result": "Replay attack detected -- decision_hash already used",
                    "failure_reason": "Decision hash replay rejected",
                    "timestamp": timestamp,
                })
                return

            # Evaluate decision
            if decision == "ALLOW":
                # Verify decision_hash is present
                if not decision_hash:
                    self._send_json(400, {
                        "trace_id": trace_id,
                        "status": "BLOCKED",
                        "validation_result": "Missing decision_hash",
                        "failure_reason": "Cannot clear without decision integrity proof",
                        "timestamp": timestamp,
                    })
                    return

                # Generate execution token
                execution_token = generate_execution_token(trace_id, decision_hash)
                _issued_tokens.add(execution_token)
                _used_decision_hashes.add(decision_hash)

                print(f"[SARATHI] CLEARED: trace_id={trace_id} token={execution_token[:16]}...")
                self._send_json(200, {
                    "trace_id": trace_id,
                    "status": "CLEARED",
                    "validation_result": "Decision ALLOW validated -- execution permitted",
                    "execution_token": execution_token,
                    "timestamp": timestamp,
                })

            elif decision == "DENY":
                print(f"[SARATHI] BLOCKED: trace_id={trace_id} decision=DENY")
                self._send_json(200, {
                    "trace_id": trace_id,
                    "status": "BLOCKED",
                    "validation_result": "Decision DENY enforced -- execution blocked",
                    "failure_reason": "Sovereign Core denied execution",
                    "timestamp": timestamp,
                })

            else:
                print(f"[SARATHI] BLOCKED: trace_id={trace_id} unknown decision={decision}")
                self._send_json(200, {
                    "trace_id": trace_id,
                    "status": "BLOCKED",
                    "validation_result": f"Unknown decision value: {decision}",
                    "failure_reason": "Invalid decision from Sovereign Core",
                    "timestamp": timestamp,
                })

        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_validate_token(self):
        """Validate an execution token."""
        from urllib.parse import urlparse, parse_qs
        query = parse_qs(urlparse(self.path).query)
        token = query.get("token", [""])[0]

        if token in _issued_tokens:
            self._send_json(200, {"valid": True, "token": token[:16] + "..."})
        else:
            self._send_json(200, {"valid": False, "reason": "Token not found or already expired"})

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def main():
    server = HTTPServer(("0.0.0.0", PORT), SarathiHandler)
    print(f"[SARATHI] External Sarathi Enforcer running on port {PORT}")
    print(f"[SARATHI] POST /sarathi/enforce")
    print(f"[SARATHI] GET  /sarathi/validate-token?token=...")
    print(f"[SARATHI] GET  /health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SARATHI] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
