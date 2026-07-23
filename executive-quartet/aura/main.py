"""
Aura — Identity Guardian Agent (Executive Quartet)

Flask service on port 8084. Responsibilities:
  - Memory integration: store/query via shared memory_client
  - Identity verification: detect atlas_ drift in codebase
  - Tamper-evident ledger: SHA-256 chained JSONL audit log

Pattern: follows track-a scaffolding (Flask dev server, inline ledger).
"""

import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests  # noqa: F401 — available for future cross-service calls
from flask import Flask, jsonify, request

# ── Load shared memory_client ──────────────────────────────────────────────
# In tests, memory_client is pre-injected into sys.modules as a mock.
# In production, we load it via importlib from the parent directory.
try:
    import memory_client  # type: ignore[import-not-found]
except ImportError:
    import importlib.util

    _mem_path = Path(__file__).resolve().parent.parent / "memory_client.py"
    spec = importlib.util.spec_from_file_location("memory_client", _mem_path)
    memory_client = importlib.util.module_from_spec(spec)
    sys.modules["memory_client"] = memory_client
    spec.loader.exec_module(memory_client)

# ── Configuration ──────────────────────────────────────────────────────────
LEDGER_PATH = Path(os.environ.get("LEDGER_PATH", "/var/log/ledger"))
LEDGER_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("aura")


# ── Tamper-Evident Ledger (inline, track-a pattern) ────────────────────────
_last_hash: str | None = None


def _build_chain_hash(prev: str | None, entry_str: str) -> str:
    """Build a SHA-256 chain hash linking ledger entries together."""
    payload = (prev or "") + entry_str
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_ledger_entry(event_type: str, payload: dict) -> str:
    """Append a tamper-evident entry to the daily-rotated JSONL ledger.

    Returns the 64-char hex chain_hash of the new entry.
    """
    global _last_hash
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "payload": payload,
    }
    entry["chain_hash"] = _build_chain_hash(
        _last_hash, json.dumps(entry, sort_keys=True)
    )
    _last_hash = entry["chain_hash"]

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ledger_file = LEDGER_PATH / f"ledger-{date_str}.jsonl"
    with open(ledger_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry["chain_hash"]


# ── HTTP API ───────────────────────────────────────────────────────────────


@app.route("/healthz")
def healthz():
    """Kubernetes / Cloud Run health check."""
    return jsonify({"status": "ok", "agent": "aura"})


@app.route("/memory/store", methods=["POST"])
def memory_store():
    """Store a structured memory via the shared MemoryPlugin client.

    Body: {"entity": ..., "context": ..., "data": {...}}
    Returns: {"success": ..., "memory_id": ...}
    """
    body = request.get_json(silent=True) or {}
    entity = body.get("entity", "").strip()
    context = body.get("context", "").strip()
    data = body.get("data")

    if not entity or not context or data is None:
        return jsonify({"error": "Missing required fields: entity, context, data"}), 400

    result = memory_client.store_memory(entity=entity, context=context, data=data)
    write_ledger_entry("memory_store", {"entity": entity, "context": context})

    return jsonify(
        {
            "success": result.get("success", False),
            "memory_id": result.get("data", {}).get("id"),
        }
    )


@app.route("/memory/query", methods=["POST"])
def memory_query():
    """Query memories via the shared MemoryPlugin client.

    Body: {"entity": ..., "context": ..., "query": ...}
    Returns: {"success": ..., "results": [...]}
    """
    body = request.get_json(silent=True) or {}
    entity = body.get("entity", "").strip()
    context = body.get("context", "").strip()
    query = body.get("query", "").strip()

    if not entity or not context or not query:
        return jsonify(
            {"error": "Missing required fields: entity, context, query"}
        ), 400

    result = memory_client.query_memory(entity=entity, context=context, query=query)
    write_ledger_entry("memory_query", {"entity": entity, "context": context})

    return jsonify(
        {
            "success": result.get("success", False),
            "results": result.get("data", []),
        }
    )


@app.route("/identity/verify", methods=["POST"])
def identity_verify():
    """Detect atlas_ drift in provided source content.

    Body: {"content": "<source code string>"}
    Returns: {"drift": bool, "matches": [...]}

    Guards against pre-refactor artifacts (atlas_ references) leaking
    into the codebase.  Used as a gate in CI and deployment pipelines.
    """
    body = request.get_json(silent=True) or {}
    content = body.get("content", "")

    if not content:
        return jsonify({"error": "Missing required field: content"}), 400

    matches: list[str] = []
    for line_no, line in enumerate(content.splitlines(), 1):
        if "atlas_" in line:
            matches.append(f"line {line_no}: {line.strip()}")

    drift = len(matches) > 0
    write_ledger_entry(
        "identity_check", {"drift_detected": drift, "matches": len(matches)}
    )

    return jsonify({"drift": drift, "matches": matches})


@app.route("/ledger")
def ledger():
    """Return the most recent ledger entries (last N lines)."""
    limit = request.args.get("limit", 50, type=int)
    entries: list[str] = []
    files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"), reverse=True)
    for f in files:
        lines = f.read_text(encoding="utf-8").strip().splitlines()
        entries.extend(reversed(lines))
        if len(entries) >= limit:
            break
    entries = entries[:limit]
    parsed = [json.loads(e) for e in reversed(entries)]
    return jsonify({"entries": parsed, "count": len(parsed)})


# ── Startup ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Restore ledger chain hash from last entry on disk
    ledger_files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"))
    if ledger_files:
        last_lines = ledger_files[-1].read_text(encoding="utf-8").strip().splitlines()
        if last_lines:
            try:
                last_entry = json.loads(last_lines[-1])
                _last_hash = last_entry.get("chain_hash")
            except json.JSONDecodeError:
                pass

    logger.info("Aura agent starting on port 8084 — identity guardian active")
    app.run(host="0.0.0.0", port=8084, debug=False)
