"""
Self-Remediation Service — OpenCode execution wrapper (port 8087)

Receives remediation plans from Krieger, executes them via OpenCode CLI
(stubbed — requires human approval for production), and maintains a
tamper-evident ledger of all actions.

Endpoints:
  GET  /healthz       — service health check
  POST /remediate      — receive plan from Krieger, execute via OpenCode
  POST /health-check   — probe all mesh services
  GET  /ledger         — tamper-evident ledger entries
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request

# ── Load sibling health-hooks module (filename contains hyphen) ───────
_HH_PATH = Path(__file__).parent / "health-hooks.py"
_hh_spec = importlib.util.spec_from_file_location("health_hooks", _HH_PATH)
_health_hooks = importlib.util.module_from_spec(_hh_spec)
sys.modules["health_hooks"] = _health_hooks
_hh_spec.loader.exec_module(_health_hooks)

# ── Shared ledger writer (src/ledger.py) ──────────────────────────────
from src.ledger import LedgerWriter

# ── Auditor module (local) ─────────────────────────────────────────────
import auditor as auditor_module

# ── MemoryPlugin client (shared across executive quartet) ──────────────
_eq_path = str(Path(__file__).resolve().parent.parent / "executive-quartet")
if _eq_path not in sys.path:
    sys.path.insert(0, _eq_path)

try:
    from memory_client import query_memory
except ImportError:
    query_memory = None  # type: ignore[assignment]

# ── Configuration ──────────────────────────────────────────────────────
LEDGER_PATH = Path(os.environ.get("LEDGER_PATH", "/var/log/ledger"))
LEDGER_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("self-remediation")

# ── Ledger writer instance ─────────────────────────────────────────────
_ledger = LedgerWriter(ledger_path=LEDGER_PATH)
_CHAIN_HEAD: str = ""  # last chain_hash, restored on startup


def _write_ledger(entry_type: str, payload: dict) -> str:
    """Append an entry to the tamper-evident ledger using src/ledger.py."""
    global _CHAIN_HEAD
    chain_hash = _ledger.write(entry_type, payload, _CHAIN_HEAD)
    _CHAIN_HEAD = chain_hash
    return chain_hash


# ── HTTP API ────────────────────────────────────────────────────────────


@app.route("/healthz")
def healthz():
    """Service health check."""
    return jsonify({"status": "ok", "service": "self-remediation"})


@app.route("/remediate", methods=["POST"])
def remediate():
    """Receive a remediation plan from Krieger and execute via OpenCode.

    Request body::

        {
            "plan_id": "plan-abc123",
            "steps": [
                {"action": "kubectl get pods", "priority": "immediate"},
                ...
            ],
            "reasoning_log_ref": "hash-abc123"
        }
    """
    body = request.get_json(silent=True) or {}

    # Validate plan via health-hooks
    try:
        plan = _health_hooks.trigger_remediation(body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    plan_id = plan["plan_id"]
    steps = plan["steps"]
    reasoning_ref = plan["reasoning_log_ref"]

    _write_ledger(
        "remediation_received",
        {
            "plan_id": plan_id,
            "step_count": len(steps),
            "reasoning_log_ref": reasoning_ref,
        },
    )
    logger.info("Received remediation plan %s with %d steps", plan_id, len(steps))

    # Execute steps via OpenCode (stubbed — human approval required)
    results = _health_hooks.execute_remediation_plan(steps)

    # Ledger each step result
    for i, res in enumerate(results):
        _write_ledger(
            "remediation_step_executed",
            {
                "plan_id": plan_id,
                "step_index": i,
                "action": res["action"],
                "status": res["status"],
                "output": res["output"],
            },
        )

    _write_ledger(
        "remediation_complete",
        {"plan_id": plan_id, "total_steps": len(results)},
    )

    return jsonify(
        {
            "plan_id": plan_id,
            "status": "executed",
            "results": results,
        }
    )


# ── Mesh service map for /health-check probing ──────────────────────────
# Internal docker-compose container names → healthz URLs
_SERVICE_MAP: dict[str, dict] = {
    "track-a": {"url": "http://track-a-control-loop:8080/healthz", "timeout": 5},
    "track-b": {"url": "http://track-b-actuator:8081/healthz", "timeout": 5},
    "sheryl": {"url": "http://sheryl:8083/healthz", "timeout": 5},
    "aura": {"url": "http://aura-agent:8084/healthz", "timeout": 5},
    "malory": {"url": "http://malory:8085/healthz", "timeout": 5},
    "krieger": {"url": "http://krieger:8086/healthz", "timeout": 5},
    "self-remediation": {"url": "http://localhost:8087/healthz", "timeout": 5},
    "telegram-bridge": {"url": "http://telegram-bridge:8088/healthz", "timeout": 5},
}


@app.route("/health-check", methods=["POST"])
def health_check():
    """Probe all mesh services and return their health status."""
    _write_ledger("health_check_start", {})

    probe_results = _health_hooks.probe_all_services(_SERVICE_MAP)

    # Convert boolean healthy to string status
    services: dict[str, str] = {}
    for svc_name, result in probe_results.items():
        services[svc_name] = "healthy" if result.get("healthy") else "unreachable"

    healthy = sum(1 for s in services.values() if s == "healthy")
    unhealthy = sum(1 for s in services.values() if s == "unreachable")

    _write_ledger(
        "health_check_complete",
        {
            "total": len(services),
            "healthy": healthy,
            "unreachable": unhealthy,
        },
    )

    return jsonify(
        {
            "status": "probe_complete",
            "services": services,
        }
    )


@app.route("/ledger", methods=["GET"])
def ledger():
    """Return recent tamper-evident ledger entries."""
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


@app.route("/audit/check", methods=["POST"])
def audit_check():
    """Validate a board log entry against MemoryPlugin context."""
    body = request.get_json(silent=True) or {}
    log_entry = body.get("log_entry")
    entity = body.get("entity", "board")
    context = body.get("context", "allowlist-context")

    if not log_entry:
        return jsonify({"error": "Missing required field: log_entry"}), 400

    memory_context = {"entity": entity, "context": context, "results": []}
    if query_memory is not None:
        try:
            result = query_memory(
                entity=entity,
                context=context,
                query=log_entry.get("tool", ""),
            )
            if result.get("success"):
                memory_context["results"] = result.get("data", [])
        except Exception as exc:
            logger.warning("MemoryPlugin query failed for audit/check: %s", exc)

    finding = auditor_module.validate_board_log(log_entry, memory_context)

    _write_ledger(
        "audit_check",
        {
            "tool": log_entry.get("tool"),
            "has_finding": finding is not None,
            "finding_type": finding.finding_type if finding else None,
        },
    )

    return jsonify(
        {
            "finding": {
                "id": finding.id,
                "finding_type": finding.finding_type,
                "severity": finding.severity,
                "description": finding.description,
            }
            if finding
            else None,
            "status": "violation" if finding else "clean",
        }
    )


@app.route("/audit/report", methods=["POST"])
def audit_report():
    """Generate and persist an audit finding from a log entry or VCP entry."""
    body = request.get_json(silent=True) or {}

    vcp_entry = body.get("vcp_entry")
    if vcp_entry is not None:
        finding = auditor_module.check_vcp(vcp_entry)
        if finding:
            auditor_module._add_finding(finding)
            _write_ledger(
                "audit_report",
                {
                    "finding_id": finding.id,
                    "finding_type": finding.finding_type,
                    "via": "vcp",
                },
            )
            return (
                jsonify(
                    {
                        "finding_id": finding.id,
                        "finding_type": finding.finding_type,
                        "severity": finding.severity,
                        "description": finding.description,
                        "status": "violation",
                    }
                ),
                201,
            )
        _write_ledger("audit_report", {"via": "vcp", "status": "clean"})
        return jsonify({"finding": None, "status": "clean"})

    log_entry = body.get("log_entry")
    if not log_entry:
        return jsonify({"error": "Missing required field: log_entry or vcp_entry"}), 400

    memory_context = body.get("memory_context")
    if memory_context is None:
        entity = body.get("entity", "board")
        context = body.get("context", "allowlist-context")
        memory_context = {"entity": entity, "context": context, "results": []}
        if query_memory is not None:
            try:
                result = query_memory(
                    entity=entity,
                    context=context,
                    query=log_entry.get("tool", ""),
                )
                if result.get("success"):
                    memory_context["results"] = result.get("data", [])
            except Exception as exc:
                logger.warning("MemoryPlugin query failed for audit/report: %s", exc)

    finding = auditor_module.validate_board_log(log_entry, memory_context)

    if finding:
        auditor_module._add_finding(finding)
        _write_ledger(
            "audit_report",
            {
                "finding_id": finding.id,
                "finding_type": finding.finding_type,
                "tool": log_entry.get("tool"),
            },
        )
        return (
            jsonify(
                {
                    "finding_id": finding.id,
                    "finding_type": finding.finding_type,
                    "severity": finding.severity,
                    "description": finding.description,
                    "status": "violation",
                }
            ),
            201,
        )

    _write_ledger("audit_report", {"tool": log_entry.get("tool"), "status": "clean"})
    return jsonify({"finding": None, "status": "clean"})


@app.route("/audit/findings", methods=["GET"])
def audit_findings():
    """List all persisted audit findings."""
    findings = auditor_module._get_findings()
    serialized = [
        {
            "id": f.id,
            "timestamp": f.timestamp,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "board_entry_ref": f.board_entry_ref,
            "vcp_entry": f.vcp_entry,
            "description": f.description,
        }
        for f in findings
    ]

    _write_ledger("audit_findings_listed", {"count": len(serialized)})
    return jsonify({"findings": serialized, "count": len(serialized)})


@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "service": "self-remediation",
            "version": "0.1.0",
            "model": "OpenCode Self-Remediation",
            "endpoints": {
                "/healthz": "GET — health check",
                "/remediate": "POST — receive remediation plan, execute via OpenCode",
                "/health-check": "POST — probe all mesh services",
                "/audit/check": "POST — validate board log against MemoryPlugin context",
                "/audit/report": "POST — generate and persist an audit finding",
                "/audit/findings": "GET — list all persisted audit findings",
                "/ledger": "GET — tamper-evident ledger entries",
            },
        }
    )


# ── Startup ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Restore ledger chain head from last entry on disk
    ledger_files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"))
    if ledger_files:
        last_lines = ledger_files[-1].read_text(encoding="utf-8").strip().splitlines()
        if last_lines:
            try:
                last_entry = json.loads(last_lines[-1])
                _CHAIN_HEAD = last_entry.get("chain_hash", "")
            except json.JSONDecodeError:
                pass

    logger.info(
        "Self-remediation starting — port 8087, chain_head=%s…",
        _CHAIN_HEAD[:12] if _CHAIN_HEAD else "(genesis)",
    )
    app.run(host="0.0.0.0", port=8087, debug=False)
