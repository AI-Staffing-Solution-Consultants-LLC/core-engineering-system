"""
Sheryl — Memory & Context Agent (Executive Quartet)

Sheryl is the memory specialist. She:
  - Manages persistent context via MemoryPlugin
  - Consults RAG corpus for historical runbooks
  - Runs a lightweight planning loop combining both sources
  - Writes every reasoning step to a tamper-evident ledger

Conforms to the C-P-A model: Context (RAG + MemoryPlugin) → Planning → Action.
"""

import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add parent (executive-quartet/) and repo root to import path so we can
# reach memory_client and src.ledger at runtime.
_EXEC_DIR = Path(__file__).resolve().parent.parent  # executive-quartet/
_REPO_ROOT = _EXEC_DIR.parent  # core-engineering-system/
sys.path.insert(0, str(_EXEC_DIR))
sys.path.insert(0, str(_REPO_ROOT))

import requests  # noqa: E402

from flask import Flask, Response, jsonify, request  # noqa: E402
from memory_client import query_memory, store_memory  # noqa: E402
from src.ledger import LedgerWriter  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RAG_CORPUS_PATH = Path(os.environ.get("RAG_CORPUS_PATH", "/rag/docs"))
LEDGER_PATH = Path(os.environ.get("LEDGER_PATH", "/var/log/ledger"))

LEDGER_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sheryl")

# Shared ledger writer instance (thread-safe, per src/ledger.py)
ledger = LedgerWriter(str(LEDGER_PATH))
_chain_head: str = ""  # tracks the last chain_hash emitted

# Cross-service URLs (container-network hostnames)
AURA_URL = os.environ.get("AURA_URL", "http://aura-agent:8084")
TELEGRAM_BRIDGE_URL = os.environ.get(
    "TELEGRAM_BRIDGE_URL", "http://telegram-bridge:8088"
)

# In-memory store for dashboard (max 5 entries, oldest-eviction FIFO)
_last_responses: list[dict] = []


def _write_ledger(entry_type: str, data: dict) -> str:
    """Write a chained ledger entry and return the new chain hash."""
    global _chain_head
    h = ledger.write(entry_type, data, _chain_head)
    _chain_head = h
    return h


# ---------------------------------------------------------------------------
# RAG Context Loader
# ---------------------------------------------------------------------------
def load_rag_context() -> dict:
    """Load Markdown files from the RAG corpus into a name→content dict."""
    corpus: dict[str, str] = {}
    if not RAG_CORPUS_PATH.is_dir():
        logger.warning("RAG corpus path %s not found", RAG_CORPUS_PATH)
        return corpus
    for md_file in RAG_CORPUS_PATH.rglob("*.md"):
        try:
            try:
                rel = md_file.relative_to(RAG_CORPUS_PATH)
            except ValueError:
                rel = md_file.name
            corpus[str(rel)] = md_file.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to read RAG chunk %s: %s", md_file, exc)
    logger.info("Sheryl loaded %d RAG documents", len(corpus))
    return corpus


def search_rag(corpus: dict[str, str], query: str, top_k: int = 3) -> list[str]:
    """Simple keyword-match RAG search (placeholder for vector search)."""
    results: list[tuple[str, int]] = []
    q = query.lower()
    for content in corpus.values():
        score = content.lower().count(q)
        if score > 0:
            results.append((content, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in results[:top_k]]


# ---------------------------------------------------------------------------
# Planning helpers
# ---------------------------------------------------------------------------
def form_hypothesis(query: str, rag_chunks: list[str]) -> str:
    """Rule-based hypothesis from query keywords."""
    triggers = {
        "latency": "High latency likely caused by resource saturation or network congestion.",
        "crash": "Crash may be caused by memory exhaustion (OOM) or uncaught exception.",
        "error": "Error state detected; investigate logs for root cause.",
        "deploy": "Deployment issue; check container image and configuration drift.",
        "cpu": "CPU saturation detected; check for noisy neighbour or runaway process.",
        "memory": "Memory pressure detected; possible memory leak or under-provisioning.",
    }
    q = query.lower()
    for kw, h in triggers.items():
        if kw in q:
            return h
    return "Unknown anomaly; requires full diagnostic sweep."


def build_action_plan(query: str, hypothesis: str) -> list[dict]:
    """Generate a sequence of investigation steps based on the query."""
    actions = []
    q = query.lower()

    actions.append(
        {
            "tool": "kubectl get pods",
            "reason": "Establish baseline pod status",
        }
    )

    if "latency" in q:
        actions.append({"tool": "kubectl top pods", "reason": "Check resource usage"})
        actions.append(
            {"tool": "kubectl logs --tail=100", "reason": "Inspect recent log output"}
        )
    elif "crash" in q or "error" in q:
        actions.append(
            {
                "tool": "kubectl logs --previous",
                "reason": "Inspect previous container logs",
            }
        )
        actions.append({"tool": "kubectl describe pod", "reason": "Inspect pod events"})
    else:
        actions.append(
            {"tool": "kubectl top nodes", "reason": "Check node resource usage"}
        )
        actions.append(
            {"tool": "kubectl events", "reason": "Check recent cluster events"}
        )

    return actions


def generate_response(
    query: str, rag_chunks: list[str], memory_chunks: list[dict]
) -> str:
    """Synthesise a response from RAG context and memory, or fall back to
    a generic acknowledgment."""
    q = query.lower()

    keyword_responses = {
        "latency": (
            "High latency detected — check resource saturation and network "
            "conditions. Reviewing historical runbooks for similar incidents."
        ),
        "crash": (
            "Crash incident detected. Recommend inspecting pod logs and "
            "memory usage. Investigating previous crash patterns."
        ),
        "error": (
            "Error state identified. I'll analyse recent logs and system "
            "events to isolate the root cause."
        ),
        "deploy": (
            "Deploy request received. Verify container image and "
            "configuration drift, then proceed with rollout."
        ),
        "cpu": (
            "CPU saturation alert. Check for noisy neighbours or "
            "runaway processes on the affected node."
        ),
        "memory": (
            "Memory pressure detected. Possible memory leak or "
            "under-provisioning — checking resource allocation."
        ),
    }
    for kw, response in keyword_responses.items():
        if kw in q:
            return response

    if rag_chunks:
        snippet = rag_chunks[0][:120].strip().replace("\n", " ")
        return f"I found relevant context: {snippet}... Would you like me to investigate further?"

    if memory_chunks:
        return (
            "I have prior context related to this query. Let me review and "
            "provide a detailed assessment."
        )

    return "Acknowledged. I'll analyse this request and respond with an action plan shortly."


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------


@app.route("/healthz")
def healthz():
    """Health check identifying this agent."""
    return jsonify({"status": "ok", "agent": "sheryl"})


@app.route("/memory/store", methods=["POST"])
def memory_store():
    """Store a structured memory via MemoryPlugin.

    Expects JSON: {"entity": "...", "context": "...", "data": {...}}
    """
    body = request.get_json(silent=True) or {}
    entity = body.get("entity", "").strip()
    context = body.get("context", "").strip()
    data = body.get("data")

    if not entity or not context or data is None:
        return jsonify({"error": "Missing required fields: entity, context, data"}), 400

    try:
        result = store_memory(entity=entity, context=context, data=data)
    except Exception as exc:
        logger.error("store_memory failed: %s", exc)
        return jsonify({"error": str(exc)}), 502

    _write_ledger(
        "memory_store",
        {
            "entity": entity,
            "context": context,
            "memory_id": result.get("data", {}).get("id"),
        },
    )

    return jsonify(
        {
            "success": True,
            "memory_id": result.get("data", {}).get("id"),
        }
    )


@app.route("/memory/query", methods=["POST"])
def memory_query():
    """Query MemoryPlugin for stored context.

    Expects JSON: {"entity": "...", "context": "...", "query": "..."}
    """
    body = request.get_json(silent=True) or {}
    entity = body.get("entity", "").strip()
    context = body.get("context", "").strip()
    q = body.get("query", "").strip()

    if not entity or not context or not q:
        return jsonify(
            {"error": "Missing required fields: entity, context, query"}
        ), 400

    try:
        result = query_memory(entity=entity, context=context, query=q)
    except Exception as exc:
        logger.error("query_memory failed: %s", exc)
        return jsonify({"error": str(exc)}), 502

    _write_ledger(
        "memory_query",
        {
            "entity": entity,
            "context": context,
            "query": q,
            "results_count": len(result.get("data", [])),
        },
    )

    return jsonify(result)


@app.route("/plan", methods=["POST"])
def plan():
    """Accept a query, consult RAG + MemoryPlugin, return an action plan.

    Expects JSON: {"query": "why is latency high"}
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "Missing 'query' field"}), 400

    plan_id = str(uuid.uuid4())

    # 1. Log reasoning start
    reasoning_ref = _write_ledger(
        "reasoning_start",
        {
            "plan_id": plan_id,
            "query": query,
        },
    )
    logger.info("Sheryl plan %s: processing '%s'", plan_id, query)

    # 2. Consult RAG corpus
    rag_corpus = load_rag_context()
    rag_chunks = search_rag(rag_corpus, query, top_k=3)
    _write_ledger(
        "context_retrieval",
        {
            "plan_id": plan_id,
            "source": "rag",
            "chunks_found": len(rag_chunks),
            "query": query,
        },
    )

    # 3. Consult MemoryPlugin for relevant stored context
    try:
        memory_result = query_memory(
            entity="sheryl",
            context="plan_context",
            query=query,
        )
        memory_chunks = memory_result.get("data", [])
    except Exception as exc:
        logger.warning("MemoryPlugin query failed (non-fatal): %s", exc)
        memory_chunks = []

    _write_ledger(
        "memory_context",
        {
            "plan_id": plan_id,
            "source": "memory_plugin",
            "results_found": len(memory_chunks),
        },
    )

    # 4. Form hypothesis (RAG-weighted, rule-based)
    hypothesis = form_hypothesis(query, rag_chunks)
    _write_ledger(
        "hypothesis",
        {
            "plan_id": plan_id,
            "hypothesis": hypothesis,
            "reasoning_log_ref": reasoning_ref,
        },
    )

    # 5. Build action plan
    steps = build_action_plan(query, hypothesis)
    _write_ledger(
        "reasoning_complete",
        {
            "plan_id": plan_id,
            "total_steps": len(steps),
            "reasoning_log_ref": reasoning_ref,
        },
    )

    return jsonify(
        {
            "plan_id": plan_id,
            "query": query,
            "hypothesis": hypothesis,
            "steps": steps,
            "source": "sheryl",
        }
    )


@app.route("/ledger", methods=["GET"])
def ledger_route():
    """Return most recent ledger entries across daily files."""
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


@app.route("/ingest", methods=["POST"])
def ingest():
    """Accept a Telegram message, consult RAG + MemoryPlugin, generate a
    response, run it through Aura consistency check, and deliver via
    telegram-bridge.
    """
    body = request.get_json(silent=True) or {}
    chat_id = body.get("chat_id")
    text = (body.get("text") or body.get("caption") or "").strip()
    from_id = body.get("from_id")
    from_name = body.get("from_name", "unknown")

    if chat_id is None or not text:
        return jsonify({"error": "Missing required fields: chat_id, text"}), 400

    plan_id = str(uuid.uuid4())
    reasoning_ref = _write_ledger(
        "ingest_start",
        {"plan_id": plan_id, "chat_id": chat_id, "from_id": from_id, "query": text},
    )
    logger.info("Sheryl ingest %s: '%s' from chat=%s", plan_id, text, chat_id)

    # 1 ─ Consult RAG corpus
    rag_corpus = load_rag_context()
    rag_chunks = search_rag(rag_corpus, text, top_k=3)

    # 2 ─ Consult MemoryPlugin
    try:
        mem_result = query_memory(entity="sheryl", context="plan_context", query=text)
        memory_chunks = mem_result.get("data", [])
    except Exception as exc:
        logger.warning("MemoryPlugin query failed (non-fatal): %s", exc)
        memory_chunks = []

    # 3 ─ Generate response
    response_text = generate_response(text, rag_chunks, memory_chunks)

    # 4 ─ Aura consistency check
    aura_checked = False
    ambiguous = False
    try:
        aura_resp = requests.post(
            f"{AURA_URL}/consistency-check",
            json={"response_text": response_text, "context": {"chat_id": chat_id}},
            timeout=5,
        )
        if aura_resp.ok:
            aura_data = aura_resp.json()
            ambiguous = aura_data.get("ambiguous", False)
            aura_checked = True
            if ambiguous:
                response_text += " \N{LARGE RED CIRCLE}\N{HEAVY CHECK MARK}"
    except requests.RequestException as exc:
        logger.warning("Aura unreachable for consistency check: %s", exc)

    # 5 ─ Deliver via telegram-bridge
    try:
        requests.post(
            f"{TELEGRAM_BRIDGE_URL}/send",
            json={"chat_id": chat_id, "text": response_text},
            timeout=5,
        )
    except requests.RequestException as exc:
        logger.warning("telegram-bridge /send failed: %s", exc)

    # 6 ─ Ledger entry
    _write_ledger(
        "ingest_complete",
        {
            "plan_id": plan_id,
            "chat_id": chat_id,
            "aura_checked": aura_checked,
            "ambiguous": ambiguous,
            "response_preview": response_text[:200],
            "reasoning_log_ref": reasoning_ref,
        },
    )

    # 7 ─ Record for dashboard
    _last_responses.append(
        {
            "agent": "sheryl",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": text,
            "response": response_text,
            "ambiguous": ambiguous,
        }
    )
    if len(_last_responses) > 5:
        _last_responses.pop(0)

    logger.info(
        "Sheryl ingest %s complete — aura_checked=%s ambiguous=%s",
        plan_id,
        aura_checked,
        ambiguous,
    )
    return jsonify(
        {
            "response": response_text,
            "aura_checked": aura_checked,
            "ambiguous": ambiguous,
            "plan_id": plan_id,
        }
    )


@app.route("/dashboard/last-responses", methods=["GET"])
def dashboard_last_responses():
    """Return the last 5 agent responses stored in memory."""
    return jsonify(list(_last_responses))


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Restore chain head from the last ledger entry (if any)
    ledger_files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"))
    if ledger_files:
        last_lines = ledger_files[-1].read_text(encoding="utf-8").strip().splitlines()
        if last_lines:
            try:
                last_entry = json.loads(last_lines[-1])
                _chain_head = last_entry.get("chain_hash", "")
            except json.JSONDecodeError:
                pass

    rag = load_rag_context()
    logger.info("Sheryl starting on :8083 — %d RAG docs loaded", len(rag))
    app.run(host="0.0.0.0", port=8083, debug=False)
