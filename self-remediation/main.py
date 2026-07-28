"""
Self-Remediation Service — OpenCode execution wrapper (port 8087)

Receives remediation plans from Krieger, executes them via OpenCode CLI
(stubbed — requires human approval for production), and maintains a
tamper-evident ledger of all actions.

Telemetry, knowledge stewardship, and RAG retrieval are wired in at startup
(gated by environment variables) to support autonomous anomaly diagnosis.

Endpoints:
  GET  /healthz         — service health check
  POST /remediate       — receive plan from Krieger, execute via OpenCode
  POST /health-check    — probe all mesh services
  POST /plan            — construct remediation plan with RAG + Gemini
  POST /diagnose        — diagnose an anomaly using Gemini Knowledge Steward
  GET  /ledger          — tamper-evident ledger entries
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

# ── Telemetry / Knowledge Steward / RAG ─────────────────────────────────
# Import sibling modules in the self-remediation package
try:
    from telemetry import TelemetryListener
except ImportError:
    TelemetryListener = None  # type: ignore[assignment]

try:
    from knowledge_steward import GeminiKnowledgeSteward
except ImportError:
    GeminiKnowledgeSteward = None  # type: ignore[assignment]

try:
    from rag_connector import OpenVikingRAG
except ImportError:
    OpenVikingRAG = None  # type: ignore[assignment]

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

PROJECT_NAME = os.environ.get("PROJECT_NAME", "aissc-core-engine-self-dep")
REGION = os.environ.get("REGION", "us-central1")
ENABLE_TELEMETRY = os.environ.get("ENABLE_TELEMETRY", "").lower() == "true"

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("self-remediation")

# ── Ledger writer instance ─────────────────────────────────────────────
_ledger = LedgerWriter(ledger_path=LEDGER_PATH)
_CHAIN_HEAD: str = ""  # last chain_hash, restored on startup

# ── Telemetry listener (gated by ENABLE_TELEMETRY env var) ──────────────
_telemetry_listener = None
if ENABLE_TELEMETRY and TelemetryListener is not None:
    _telemetry_listener = TelemetryListener(
        project=PROJECT_NAME,
        region=REGION,
        polling_interval=60,
        ledger_writer=_ledger,
    )
    logger.info(
        "Telemetry listener configured — project=%s region=%s",
        PROJECT_NAME,
        REGION,
    )
elif ENABLE_TELEMETRY:
    logger.warning("ENABLE_TELEMETRY=true but TelemetryListener import failed")

# ── Gemini Knowledge Steward ────────────────────────────────────────────
_knowledge_steward = None
if GeminiKnowledgeSteward is not None:
    _knowledge_steward = GeminiKnowledgeSteward()
else:
    logger.warning("GeminiKnowledgeSteward: import failed — AI diagnosis disabled")

# ── OpenViking RAG connector ────────────────────────────────────────────
_rag = None
if OpenVikingRAG is not None:
    _rag = OpenVikingRAG()
else:
    logger.warning("OpenVikingRAG: import failed — RAG context lookup disabled")


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

    plan_id = body.get("plan_id")
    if not plan_id:
        return jsonify({"error": "Missing required field: plan_id"}), 400

    steps = body.get("steps", [])
    reasoning_ref = body.get("reasoning_log_ref", "")

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
    def _execute_step(step):
        pass  # OpenCode execution stubbed — human approval required

    results = _health_hooks.execute_remediation_plan(
        {"plan_id": plan_id, "steps": steps}, _execute_step
    )

    # Ledger each step result
    for i, res in enumerate(results):
        _write_ledger(
            "remediation_step_executed",
            {
                "plan_id": plan_id,
                "step_index": i,
                "action": res["action"],
                "status": "success" if res.get("success") else "failed",
                "output": res.get("error", ""),
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


@app.route("/plan", methods=["POST"])
def construct_plan():
    """Construct a remediation plan using RAG context and Gemini diagnosis.

    Accepts an anomaly report and returns a diagnostic plan.  This
    integrates the OpenViking RAG connector for context lookups and the
    Gemini Knowledge Steward for AI-powered root-cause analysis.

    Request body::

        {
            "anomaly": {
                "source": "gcp_cloud_run",
                "service_name": "track-a-control-loop",
                "condition_type": "Ready",
                "condition_message": "Revision has failed."
            },
            "query": "why is latency high"   // optional free-text query
        }
    """
    body = request.get_json(silent=True) or {}

    anomaly = body.get("anomaly", {})
    user_query = body.get("query", "")

    if not anomaly and not user_query:
        return jsonify({"error": "Missing required field: anomaly or query"}), 400

    plan_id = uuid.uuid4().hex[:16]
    diagnostic: dict = {}

    # Step 1: Query RAG for relevant SOPs / runbooks
    rag_results: list[dict] = []
    search_text = user_query or str(anomaly)
    if _rag is not None:
        try:
            rag_results = _rag.query(search_text, top_k=3)
            logger.info(
                "RAG query returned %d docs for plan %s",
                len(rag_results),
                plan_id,
            )
        except Exception as exc:
            logger.warning("RAG query failed for plan %s: %s", plan_id, exc)

    # Step 2: Call Gemini Knowledge Steward for diagnosis
    if _knowledge_steward is not None:
        rag_snippets = [r.get("content", "") for r in rag_results]
        try:
            diagnostic = _knowledge_steward.analyze(
                anomaly_report=anomaly or {"query": user_query},
                rag_context=rag_snippets if rag_snippets else None,
            )
            logger.info(
                "Gemini diagnosis for plan %s: confidence=%.2f",
                plan_id,
                diagnostic.get("confidence", 0.0),
            )
        except Exception as exc:
            logger.warning("Gemini analysis failed for plan %s: %s", plan_id, exc)
            diagnostic = {
                "diagnosis": "Analysis error",
                "recommended_action": "Review logs manually",
                "confidence": 0.0,
            }

    # Step 3: Build plan from diagnosis + RAG
    steps: list[dict] = []
    if diagnostic.get("diagnosis"):
        steps.append(
            {
                "action": diagnostic["diagnosis"],
                "priority": "immediate",
                "source": "gemini-knowledge-steward",
            }
        )
    if diagnostic.get("recommended_action"):
        steps.append(
            {
                "action": diagnostic["recommended_action"],
                "priority": "immediate",
                "source": "gemini-knowledge-steward",
            }
        )

    # Attach RAG-referenced SOPs as informational steps
    for doc in rag_results[:3]:
        steps.append(
            {
                "action": f"Review {doc['title']}",
                "priority": "advisory",
                "source": "openviking-rag",
                "document_path": doc.get("path", ""),
            }
        )

    _write_ledger(
        "plan_constructed",
        {
            "plan_id": plan_id,
            "step_count": len(steps),
            "rag_doc_count": len(rag_results),
            "diagnosis_confidence": diagnostic.get("confidence", 0.0),
            "diagnosis": diagnostic.get("diagnosis", ""),
        },
    )

    return jsonify(
        {
            "plan_id": plan_id,
            "steps": steps,
            "diagnostic": diagnostic,
            "rag_context": [
                {"title": d["title"], "score": d["score"]} for d in rag_results
            ],
        }
    )


@app.route("/diagnose", methods=["POST"])
def diagnose():
    """Diagnose an anomaly using Gemini Knowledge Steward + RAG context.

    Simpler alternative to ``/plan`` — returns only the diagnostic
    without constructing a full remediation plan.

    Request body::

        {
            "anomaly": {
                "source": "gcp_cloud_run",
                "service_name": "track-a-control-loop",
                "condition_type": "Ready",
                "condition_message": "Revision has failed."
            }
        }
    """
    body = request.get_json(silent=True) or {}

    anomaly = body.get("anomaly")
    if not anomaly:
        return jsonify({"error": "Missing required field: anomaly"}), 400

    # Query RAG for context
    rag_snippets: list[str] = []
    if _rag is not None:
        try:
            rag_results = _rag.query(str(anomaly), top_k=3)
            rag_snippets = [r.get("content", "") for r in rag_results]
        except Exception as exc:
            logger.warning("RAG query failed for /diagnose: %s", exc)

    # Call Knowledge Steward
    if _knowledge_steward is not None:
        try:
            diagnostic = _knowledge_steward.analyze(
                anomaly_report=anomaly,
                rag_context=rag_snippets if rag_snippets else None,
            )
        except Exception as exc:
            logger.warning("Gemini analysis failed for /diagnose: %s", exc)
            diagnostic = _knowledge_steward._stub_response()
    else:
        diagnostic = {
            "diagnosis": "Knowledge Steward not available",
            "recommended_action": "Review logs manually",
            "confidence": 0.0,
        }

    _write_ledger(
        "diagnosis_complete",
        {
            "service": anomaly.get("service_name", "unknown"),
            "condition": anomaly.get("condition_type", "unknown"),
            "diagnosis": diagnostic.get("diagnosis", ""),
            "confidence": diagnostic.get("confidence", 0.0),
        },
    )

    return jsonify(
        {
            "diagnostic": diagnostic,
            "rag_sources": len(rag_snippets),
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
            "telemetry_enabled": _telemetry_listener is not None,
            "knowledge_steward_available": _knowledge_steward is not None
            and getattr(_knowledge_steward, "_api_available", False),
            "rag_available": _rag is not None and _rag.corpus_path is not None,
            "endpoints": {
                "/healthz": "GET — health check",
                "/remediate": "POST — receive remediation plan, execute via OpenCode",
                "/health-check": "POST — probe all mesh services",
                "/plan": "POST — construct remediation plan with RAG + Gemini",
                "/diagnose": "POST — diagnose anomaly using Gemini Knowledge Steward",
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

    # Start telemetry polling (only if ENABLE_TELEMETRY=true)
    if _telemetry_listener is not None:
        _telemetry_listener.start()

    logger.info(
        "Self-remediation starting — port 8087, chain_head=%s…, telemetry=%s",
        _CHAIN_HEAD[:12] if _CHAIN_HEAD else "(genesis)",
        _telemetry_listener is not None,
    )
    app.run(host="0.0.0.0", port=8087, debug=False)
