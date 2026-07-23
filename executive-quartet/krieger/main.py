"""
Krieger — Incident Remediation Agent (port 8086)

Endpoints:
  GET  /healthz        — health check
  POST /memory/store   — store memory via MemoryPlugin
  POST /memory/query   — query memory via MemoryPlugin
  POST /remediate      — receive incident, propose remediation plan
  GET  /ledger         — read tamper-evident ledger
"""

import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request

# ── Import shared memory_client from parent directory ────────────────
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from memory_client import query_memory, store_memory
except ImportError:
    store_memory = None
    query_memory = None

# ── Configuration ────────────────────────────────────────────────────
LEDGER_PATH = Path(os.environ.get("LEDGER_PATH", "/var/log/ledger"))
LEDGER_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("krieger")

# ── Tamper-Evident Ledger ─────────────────────────────────────────────
_last_hash = None


def _build_chain_hash(prev_hash, entry_str):
    return hashlib.sha256(((prev_hash or "") + entry_str).encode("utf-8")).hexdigest()


def _write_ledger(entry_type, payload):
    global _last_hash
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": entry_type,
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


# ── HTTP API ──────────────────────────────────────────────────────────


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "agent": "krieger"})


@app.route("/memory/store", methods=["POST"])
def memory_store():
    if store_memory is None:
        return jsonify({"error": "MemoryPlugin not available"}), 503

    body = request.get_json(silent=True) or {}
    entity = body.get("entity")
    context = body.get("context")
    data = body.get("data")

    if not entity or not context or data is None:
        return jsonify({"error": "Missing required fields: entity, context, data"}), 400

    try:
        result = store_memory(entity=entity, context=context, data=data)
        _write_ledger("memory_store", {"entity": entity, "context": context})
        return jsonify(result)
    except Exception as exc:
        logger.error("memory/store failed: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.route("/memory/query", methods=["POST"])
def memory_query():
    if query_memory is None:
        return jsonify({"error": "MemoryPlugin not available"}), 503

    body = request.get_json(silent=True) or {}
    entity = body.get("entity")
    context = body.get("context")
    query_text = body.get("query")

    if not entity or not context or not query_text:
        return jsonify(
            {"error": "Missing required fields: entity, context, query"}
        ), 400

    try:
        result = query_memory(entity=entity, context=context, query=query_text)
        _write_ledger(
            "memory_query", {"entity": entity, "context": context, "query": query_text}
        )
        return jsonify(result)
    except Exception as exc:
        logger.error("memory/query failed: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.route("/remediate", methods=["POST"])
def remediate():
    body = request.get_json(silent=True) or {}
    incident_id = body.get("incident_id")
    title = body.get("title", "Untitled incident")
    severity = body.get("severity", "unknown")

    if not incident_id:
        return jsonify({"error": "Missing required field: incident_id"}), 400

    plan_id = str(uuid.uuid4())

    _write_ledger(
        "remediation_start",
        {
            "plan_id": plan_id,
            "incident_id": incident_id,
            "title": title,
            "severity": severity,
        },
    )

    steps = _build_remediation_plan(title, severity)

    for i, step in enumerate(steps):
        _write_ledger(
            "remediation_step",
            {"plan_id": plan_id, "step": i, "action": step["action"]},
        )

    _write_ledger(
        "remediation_complete",
        {"plan_id": plan_id, "total_steps": len(steps)},
    )

    return jsonify(
        {
            "plan_id": plan_id,
            "incident_id": incident_id,
            "title": title,
            "severity": severity,
            "steps": steps,
            "status": "proposed",
        }
    )


def _build_remediation_plan(title, severity):
    """Generate a remediation plan based on incident title and severity."""
    title_lower = title.lower()
    steps = [
        {"action": "Acknowledge incident and notify on-call", "priority": "immediate"},
    ]

    if "latency" in title_lower:
        steps.append(
            {
                "action": "Check resource saturation: CPU, memory, network",
                "priority": "high",
            }
        )
        steps.append(
            {
                "action": "Inspect recent deployment for regressions",
                "priority": "high",
            }
        )
        steps.append(
            {"action": "Scale replicas if under-provisioned", "priority": "medium"}
        )
    elif "crash" in title_lower or "error" in title_lower:
        steps.append(
            {"action": "Collect crash logs and stack traces", "priority": "critical"}
        )
        steps.append(
            {"action": "Roll back to last known-good release", "priority": "high"}
        )
        steps.append(
            {"action": "Verify database and dependency health", "priority": "medium"}
        )
    elif "deploy" in title_lower:
        steps.append(
            {"action": "Verify container image integrity", "priority": "critical"}
        )
        steps.append(
            {
                "action": "Check configuration drift vs. Terraform state",
                "priority": "high",
            }
        )
        steps.append({"action": "Run smoke tests after rollback", "priority": "high"})
    else:
        steps.append({"action": "Run full diagnostic sweep", "priority": "high"})
        steps.append(
            {"action": "Check monitoring dashboards for anomalies", "priority": "high"}
        )
        steps.append(
            {
                "action": "Review recent changes in affected services",
                "priority": "medium",
            }
        )

    if severity == "critical":
        steps.insert(
            1, {"action": "Escalate to incident commander", "priority": "immediate"}
        )

    steps.append(
        {"action": "Document root cause and update runbook", "priority": "low"}
    )
    return steps


@app.route("/ledger", methods=["GET"])
def ledger():
    limit = request.args.get("limit", 50, type=int)
    entries = []
    files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"), reverse=True)
    for f in files:
        lines = f.read_text(encoding="utf-8").strip().splitlines()
        entries.extend(reversed(lines))
        if len(entries) >= limit:
            break
    entries = entries[:limit]
    parsed = [json.loads(e) for e in reversed(entries)]
    return jsonify({"entries": parsed, "count": len(parsed)})


@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "service": "krieger",
            "version": "0.1.0",
            "agent": "incident-remediation",
            "endpoints": {
                "/healthz": "GET — health check",
                "/memory/store": "POST — store memory via MemoryPlugin",
                "/memory/query": "POST — query memory via MemoryPlugin",
                "/remediate": "POST — receive incident, propose remediation plan",
                "/ledger": "GET — read tamper-evident ledger",
            },
        }
    )


# ── Startup ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Krieger starting on port 8086")
    app.run(host="0.0.0.0", port=8086, debug=False)
