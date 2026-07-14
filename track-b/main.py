"""
Track B — Actuator (C-P-A Model)

Implements the Action layer of the cognitive loop:
  - Receives tool-call requests from Track A
  - Validates each request against the tool allowlist
  - Executes commands in sandboxed subprocesses
  - Returns results to Track A
  - Writes every execution to a tamper-evident ledger

Conforms to AIdevops.txt: no tool executes without passing Constitutional AI gate first.
"""

import hashlib
import json
import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TOOL_ALLOWLIST_FILE = Path(os.environ.get("TOOL_ALLOWLIST", "/policy/tool-allowlist.txt"))
LEDGER_PATH         = Path(os.environ.get("LEDGER_PATH", "/var/log/ledger"))
TRACK_A_URL         = os.environ.get("TRACK_A_URL", "http://track-a-control-loop:8080")

LEDGER_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("track-b")

# ---------------------------------------------------------------------------
# Tool Allowlist
# ---------------------------------------------------------------------------
def load_allowlist() -> set[str]:
    """Load the tool allowlist from disk. One command per line."""
    if not TOOL_ALLOWLIST_FILE.is_file():
        logger.error("Tool allowlist not found at %s — refusing all tool calls", TOOL_ALLOWLIST_FILE)
        return set()
    lines = TOOL_ALLOWLIST_FILE.read_text(encoding="utf-8").strip().splitlines()
    allowed = {line.strip() for line in lines if line.strip() and not line.strip().startswith("#")}
    logger.info("Loaded %d allowed tools", len(allowed))
    return allowed


ALLOWLIST: set[str] = set()  # populated at startup


def is_allowed(tool: str) -> bool:
    """Check if a tool prefix is on the allowlist. No wildcards. No metacharacters."""
    tool_clean = tool.strip()
    for allowed in ALLOWLIST:
        if tool_clean == allowed or tool_clean.startswith(allowed + " "):
            return True
    return False


# ---------------------------------------------------------------------------
# Tamper-Evident Ledger
# ---------------------------------------------------------------------------
_last_hash: str | None = None


def _build_chain_hash(prev_entry: str | None, entry: str) -> str:
    payload = (prev_entry or "") + entry
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_ledger_entry(event_type: str, payload: dict) -> str:
    global _last_hash
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "track": "B",
        "payload": payload,
    }
    entry["chain_hash"] = _build_chain_hash(_last_hash, json.dumps(entry, sort_keys=True))
    _last_hash = entry["chain_hash"]

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ledger_file = LEDGER_PATH / f"ledger-{date_str}.jsonl"
    with open(ledger_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry["chain_hash"]


# ---------------------------------------------------------------------------
# Constitutional AI Gate
# ---------------------------------------------------------------------------
def constitutional_gate(tool: str, reasoning_log_ref: str | None) -> tuple[bool, str]:
    """
    Apply Constitutional AI checks before every tool execution.
    Returns (allowed: bool, reason: str).
    """
    # Gate 1: Allowlist check
    if not is_allowed(tool):
        return False, f"Constitutional AI: tool '{tool}' is not on the allowlist"

    # Gate 2: Reasoning log reference required
    if not reasoning_log_ref:
        return False, "Constitutional AI: every tool call must reference a reasoning log entry"

    # Gate 3: No shell metacharacters
    dangerous = {"|", ";", "&", "$(", "`", ">", "<", "${", "&&", "||"}
    for char in dangerous:
        if char in tool:
            return False, f"Constitutional AI: tool contains prohibited metacharacter '{char}'"

    return True, "ok"


# ---------------------------------------------------------------------------
# Sandboxed Execution
# ---------------------------------------------------------------------------
EXEC_TIMEOUT = 15  # seconds


def execute_sandboxed(tool: str) -> dict:
    """Execute a tool call in a sandboxed subprocess with a hard timeout."""
    try:
        result = subprocess.run(
            tool,
            shell=True,
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:8192],  # truncate large outputs
            "stderr": result.stderr[:8192],
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {EXEC_TIMEOUT}s", "exit_code": -1}
    except Exception as exc:
        return {"error": str(exc), "exit_code": -1}


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

@app.route("/healthz")
def healthz():
    return jsonify({"status": "healthy", "track": "B", "service": "actuator"})


@app.route("/execute", methods=["POST"])
def execute():
    """
    Execute a tool call. Request body:
      { "tool": "kubectl get pods", "args": [], "reasoning_log_ref": "hash..." }
    """
    body = request.get_json(silent=True) or {}
    tool = body.get("tool", "").strip()
    args = body.get("args", [])
    reasoning_ref = body.get("reasoning_log_ref")

    if not tool:
        return jsonify({"error": "Missing 'tool' field"}), 400

    # Constitutional AI gate
    allowed, reason = constitutional_gate(tool, reasoning_ref)
    if not allowed:
        write_ledger_entry("gate_denied", {
            "tool": tool,
            "reason": reason,
            "reasoning_log_ref": reasoning_ref,
        })
        logger.warning("Gate denied: %s — %s", tool, reason)
        return jsonify({"error": reason, "allowed": False}), 403

    write_ledger_entry("gate_passed", {
        "tool": tool,
        "args": args,
        "reasoning_log_ref": reasoning_ref,
    })

    # Execute
    full_command = tool
    if args:
        full_command += " " + " ".join(args)

    result = execute_sandboxed(full_command)

    write_ledger_entry("tool_execution", {
        "tool": tool,
        "args": args,
        "full_command": full_command,
        "exit_code": result.get("exit_code"),
        "reasoning_log_ref": reasoning_ref,
    })

    return jsonify({
        "tool": tool,
        "allowed": True,
        "exit_code": result.get("exit_code"),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "error": result.get("error"),
    })


@app.route("/allowlist", methods=["GET"])
def get_allowlist():
    """Return the current tool allowlist for audit purposes."""
    return jsonify({"allowlist": sorted(ALLOWLIST), "count": len(ALLOWLIST)})


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "track-b-actuator",
        "version": "0.1.0",
        "model": "C-P-A Actuator",
        "endpoints": {
            "/healthz": "GET — health check",
            "/execute": "POST — execute an allowlisted tool call",
            "/allowlist": "GET — view current tool allowlist",
        },
    })


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ALLOWLIST = load_allowlist()
    if not ALLOWLIST:
        logger.critical("EMPTY ALLOWLIST — Track B will reject ALL tool calls")

    # Restore ledger chain hash
    ledger_files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"))
    if ledger_files:
        last_lines = ledger_files[-1].read_text(encoding="utf-8").strip().splitlines()
        if last_lines:
            try:
                last_entry = json.loads(last_lines[-1])
                _last_hash = last_entry.get("chain_hash")
            except json.JSONDecodeError:
                pass

    logger.info("Track B starting — %d tools on allowlist", len(ALLOWLIST))
    app.run(host="0.0.0.0", port=8081, debug=False)
