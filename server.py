"""Flask API server for the Loan Analysis Agent frontend.

Bridges the frontend chat interface to the LoanAnalysisAgent class.

Usage:
    python server.py
    # Then open http://localhost:5000 in your browser
"""

import os
import json
import tempfile
import traceback

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from agent import LoanAnalysisAgent

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

# Global agent instance (single-user for simplicity)
agent = LoanAnalysisAgent()

# Temp directory for uploaded files
UPLOAD_DIR = tempfile.mkdtemp(prefix="loan_agent_uploads_")


@app.route("/")
def serve_index():
    """Serve the frontend index.html."""
    return send_from_directory("frontend", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    """Serve static frontend files."""
    return send_from_directory("frontend", path)


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "agent": "LoanAnalysisAgent"})


@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a message to the agent and get a response.

    Accepts multipart/form-data with:
      - message: text message from the user
      - files: optional file uploads (PDFs, images, spreadsheets)

    Returns JSON with:
      - text: agent's text response
      - tool_calls: list of tool calls made
    """
    try:
        message = request.form.get("message", "").strip()
        uploaded_files = request.files.getlist("files")

        if not message and not uploaded_files:
            return jsonify({"error": "No message or files provided"}), 400

        # Save uploaded files and build file path references
        file_descriptions = []
        for f in uploaded_files:
            if f.filename:
                # Save to temp directory
                safe_name = f.filename.replace("/", "_").replace("\\", "_")
                file_path = os.path.join(UPLOAD_DIR, safe_name)
                f.save(file_path)
                file_descriptions.append(file_path)

        # Build the full message with file paths embedded
        full_message = message
        if file_descriptions:
            file_refs = " ".join(file_descriptions)
            if full_message:
                full_message = f"{full_message}\n\n{file_refs}"
            else:
                full_message = f"Please analyze these documents: {file_refs}"

        # Get agent response
        result = agent.respond(full_message)

        # Parse tool calls into structured data for the results panel
        parsed_tools = []
        for tc in result.get("tool_calls", []):
            tool_data = {
                "name": tc["name"],
                "arguments": tc["arguments"],
            }
            # Extract structured data from tool results if present (for qualification decision)
            if tc["name"] == "generate_qualification_decision":
                # Arguments already contain all the data needed
                pass
            parsed_tools.append(tool_data)

        return jsonify({
            "text": result.get("text", ""),
            "tool_calls": parsed_tools,
            "files_uploaded": [os.path.basename(fp) for fp in file_descriptions],
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset the agent conversation state."""
    try:
        agent.reset()
        return jsonify({"status": "ok", "message": "Conversation reset"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("Loan Analysis Agent - Web Interface")
    print("=" * 50)
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"Open http://localhost:5000 in your browser")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
