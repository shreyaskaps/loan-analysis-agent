"""Simple HTTP server that bridges the frontend to the LoanAnalysisAgent.

Run with:
    cd <repo_root>
    python frontend/server.py

Then open http://localhost:5000 in your browser.
"""

import json
import os
import sys
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import cgi
import io

# Add repo root to path so we can import the agent
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from agent import LoanAnalysisAgent

# Global agent instance
agent = LoanAnalysisAgent()

# Temp directory for uploaded files
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "loan_agent_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))


class LoanAgentHandler(SimpleHTTPRequestHandler):
    """Serves static files from frontend/ and handles API routes."""

    def __init__(self, *args, **kwargs):
        # Serve files from the frontend directory
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/chat":
            self._handle_chat()
        elif parsed.path == "/api/upload":
            self._handle_upload()
        elif parsed.path == "/api/reset":
            self._handle_reset()
        else:
            self._send_json({"error": "Not found"}, 404)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_chat(self):
        try:
            body = json.loads(self._read_body())
            message = body.get("message", "")
            file_paths = body.get("file_paths", [])

            if not message and not file_paths:
                self._send_json({"error": "No message provided"}, 400)
                return

            # Build message with file references
            full_message = message
            if file_paths:
                file_refs = " ".join(file_paths)
                if full_message:
                    full_message = f"{full_message}\n\n{file_refs}"
                else:
                    full_message = file_refs

            # Call the agent
            result = agent.respond(full_message)

            self._send_json({
                "text": result.get("text", ""),
                "tool_calls": result.get("tool_calls", []),
            })

        except Exception as e:
            print(f"Chat error: {e}")
            import traceback
            traceback.print_exc()
            self._send_json({"error": str(e)}, 500)

    def _handle_upload(self):
        try:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send_json({"error": "Expected multipart/form-data"}, 400)
                return

            # Parse multipart form data
            boundary = content_type.split("boundary=")[-1].encode()
            body = self._read_body()

            saved_paths = []
            # Simple multipart parser
            parts = body.split(b"--" + boundary)
            for part in parts:
                if b"filename=" not in part:
                    continue

                # Extract filename
                header_end = part.find(b"\r\n\r\n")
                if header_end < 0:
                    continue
                headers_raw = part[:header_end].decode("utf-8", errors="replace")
                file_data = part[header_end + 4:]
                # Remove trailing \r\n
                if file_data.endswith(b"\r\n"):
                    file_data = file_data[:-2]

                # Extract filename from Content-Disposition
                filename = None
                for line in headers_raw.split("\r\n"):
                    if "filename=" in line:
                        # Handle both quoted and unquoted filenames
                        parts2 = line.split("filename=")
                        if len(parts2) > 1:
                            filename = parts2[1].strip().strip('"').strip("'")
                            break

                if not filename or not file_data:
                    continue

                # Save to upload directory
                safe_name = os.path.basename(filename)
                save_path = os.path.join(UPLOAD_DIR, safe_name)
                with open(save_path, "wb") as f:
                    f.write(file_data)

                saved_paths.append(save_path)
                print(f"Saved upload: {save_path} ({len(file_data)} bytes)")

            self._send_json({"paths": saved_paths})

        except Exception as e:
            print(f"Upload error: {e}")
            import traceback
            traceback.print_exc()
            self._send_json({"error": str(e)}, 500)

    def _handle_reset(self):
        try:
            agent.reset()
            self._send_json({"status": "ok"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log formatting."""
        print(f"[server] {args[0]}")


def main():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), LoanAgentHandler)
    print(f"╔══════════════════════════════════════════╗")
    print(f"║   🏦 Loan Analysis Agent Frontend       ║")
    print(f"║                                          ║")
    print(f"║   http://localhost:{port:<5}                ║")
    print(f"║                                          ║")
    print(f"║   Upload dir: {UPLOAD_DIR:<25} ║" if len(UPLOAD_DIR) <= 25 else f"║   Upload dir: ...{UPLOAD_DIR[-22:]:<22} ║")
    print(f"╚══════════════════════════════════════════╝")
    print(f"\nPress Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
