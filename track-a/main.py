"""
Track A — Control & Planning Loop (C-P-A Model)

Implements the Context + Planning layers of the cognitive loop:
  - Loads RAG corpus from /rag/docs for historical context
  - Loads Constitutional AI policies from /policy
  - Runs a ReAct-style planning loop
  - Emits action requests to Track B (actuator)
  - Writes every reasoning step and action to a tamper-evident ledger

Conforms to AIdevops.txt H1/H2 boundary: human-on-the-loop, agent drives the plan.
"""

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, Response, jsonify, request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RAG_CORPUS_PATH = Path(os.environ.get("RAG_CORPUS_PATH", "/rag/docs"))
POLICY_DIR      = Path(os.environ.get("POLICY_DIR", "/policy"))
LEDGER_PATH     = Path(os.environ.get("LEDGER_PATH", "/var/log/ledger"))
TRACK_B_URL     = os.environ.get("TRACK_B_URL", "http://track-b-actuator:8081")

LEDGER_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("track-a")

# ---------------------------------------------------------------------------
# RAG Context Loader
# ---------------------------------------------------------------------------
def load_rag_context() -> dict[str, str]:
    """Load all Markdown files from the RAG corpus into an in-memory index."""
    corpus: dict[str, str] = {}
    if not RAG_CORPUS_PATH.is_dir():
        logger.warning("RAG corpus path %s not found or not a directory", RAG_CORPUS_PATH)
        return corpus
    for md_file in RAG_CORPUS_PATH.rglob("*.md"):
        try:
            corpus[md_file.name] = md_file.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to read RAG chunk %s: %s", md_file, exc)
    logger.info("Loaded %d RAG documents", len(corpus))
    return corpus


def search_rag(corpus: dict[str, str], query: str, top_k: int = 3) -> list[str]:
    """Simple keyword-match search over the RAG corpus (placeholder for vector search)."""
    results: list[tuple[str, int]] = []
    query_lower = query.lower()
    for name, content in corpus.items():
        score = content.lower().count(query_lower)
        if score > 0:
            results.append((content, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in results[:top_k]]

# ---------------------------------------------------------------------------
# Policy Loader
# ---------------------------------------------------------------------------
def load_policies() -> list[str]:
    """Load all .rego policy files from /policy (placeholder OPA evaluation)."""
    policies: list[str] = []
    if not POLICY_DIR.is_dir():
        return policies
    for rego_file in POLICY_DIR.glob("*.rego"):
        policies.append(rego_file.read_text(encoding="utf-8"))
    logger.info("Loaded %d policy files", len(policies))
    return policies

# ---------------------------------------------------------------------------
# Tamper-Evident Ledger
# ---------------------------------------------------------------------------
def _build_chain_hash(prev_entry: str | None, entry: str) -> str:
    """Build a SHA-256 chain hash linking ledger entries together."""
    payload = (prev_entry or "") + entry
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_last_hash: str | None = None  # in-memory chain head (restored from last file on startup)


def write_ledger_entry(event_type: str, payload: dict) -> str:
    """Append a tamper-evident entry to the ledger. Returns the entry hash."""
    global _last_hash
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "payload": payload,
    }
    entry["chain_hash"] = _build_chain_hash(_last_hash, json.dumps(entry, sort_keys=True))
    _last_hash = entry["chain_hash"]

    # Write to daily rotating ledger file
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ledger_file = LEDGER_PATH / f"ledger-{date_str}.jsonl"
    with open(ledger_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry["chain_hash"]


# ---------------------------------------------------------------------------
# ReAct Planning Loop
# ---------------------------------------------------------------------------
def react_plan(query: str, rag_corpus: dict[str, str]) -> dict:
    """
    ReAct-style planning loop (Reason + Act).
    For each problem, the agent:
      1. Retrieves relevant context from RAG
      2. Forms a hypothesis
      3. Creates a step-by-step investigation plan
      4. Emits action requests for Track B to execute
    """
    plan_id = str(uuid.uuid4())
    steps = []

    # Log the reasoning entry
    reasoning_ref = write_ledger_entry("reasoning_start", {
        "plan_id": plan_id,
        "query": query,
    })
    logger.info("Plan %s: beginning ReAct loop for '%s'", plan_id, query)

    # Step 1 — Context retrieval
    ctx_chunks = search_rag(rag_corpus, query, top_k=3)
    write_ledger_entry("context_retrieval", {
        "plan_id": plan_id,
        "chunks_found": len(ctx_chunks),
        "query": query,
    })

    # Step 2 — Hypothesis formation (rule-based placeholder)
    hypothesis = form_hypothesis(query, ctx_chunks)
    write_ledger_entry("hypothesis", {
        "plan_id": plan_id,
        "hypothesis": hypothesis,
        "reasoning_log_ref": reasoning_ref,
    })

    # Step 3 — Action plan generation
    action_requests = generate_action_plan(query, hypothesis)

    # Step 4 — Emit each action to Track B, collect results
    results = []
    for idx, action in enumerate(action_requests):
        step = execute_action_via_track_b(action, reasoning_ref, plan_id, idx)
        steps.append(step)
        results.append(step)

        # After each action, re-evaluate — does the result change the hypothesis?
        if step.get("result", {}).get("error"):
            write_ledger_entry("plan_adjustment", {
                "plan_id": plan_id,
                "step": idx,
                "reason": f"Action failed: {step['result']['error']}",
                "reasoning_log_ref": reasoning_ref,
            })

    write_ledger_entry("reasoning_complete", {
        "plan_id": plan_id,
        "total_steps": len(steps),
        "reasoning_log_ref": reasoning_ref,
    })

    return {
        "plan_id": plan_id,
        "query": query,
        "hypothesis": hypothesis,
        "steps": steps,
        "status": "complete",
    }


def form_hypothesis(query: str, context_chunks: list[str]) -> str:
    """Form a hypothesis based on query and retrieved context (rule-based placeholder)."""
    triggers = {
        "latency": "High latency likely caused by resource saturation or network congestion.",
        "crash": "Crash may be caused by memory exhaustion (OOM) or uncaught exception.",
        "error": "Error state detected; investigate logs for root cause.",
        "deploy": "Deployment issue; check container image and configuration drift.",
        "cpu": "CPU saturation detected; check for noisy neighbor or runaway process.",
        "memory": "Memory pressure detected; possible memory leak or under-provisioning.",
    }
    query_lower = query.lower()
    for keyword, hypothesis in triggers.items():
        if keyword in query_lower:
            return hypothesis
    return "Unknown anomaly; requires full diagnostic sweep."


def generate_action_plan(query: str, hypothesis: str) -> list[dict]:
    """Generate a sequence of tool-call actions (rule-based placeholder)."""
    actions = []
    query_lower = query.lower()

    # Always start with status check
    actions.append({
        "tool": "kubectl get pods",
        "args": [],
        "reason": "Establish baseline pod status",
    })

    if "latency" in query_lower:
        actions.append({"tool": "kubectl top pods", "args": [], "reason": "Check resource usage"})
        actions.append({"tool": "kubectl logs", "args": ["--tail=100"], "reason": "Inspect recent log output"})
    elif "crash" in query_lower or "error" in query_lower:
        actions.append({"tool": "kubectl logs", "args": ["--previous"], "reason": "Inspect logs from previous crashed container"})
        actions.append({"tool": "kubectl describe pod", "args": [], "reason": "Inspect pod events and status"})
    elif "deploy" in query_lower:
        actions.append({"tool": "gcloud run services list", "args": [], "reason": "List deployed services"})
        actions.append({"tool": "kubectl events", "args": [], "reason": "Check recent cluster events"})
    else:
        actions.append({"tool": "kubectl top nodes", "args": [], "reason": "Check node-level resource usage"})
        actions.append({"tool": "kubectl events", "args": [], "reason": "Check recent cluster events"})

    return actions


def execute_action_via_track_b(action: dict, reasoning_ref: str, plan_id: str, step_idx: int) -> dict:
    """Send an action request to Track B and record the result."""
    write_ledger_entry("action_request", {
        "plan_id": plan_id,
        "step": step_idx,
        "tool": action["tool"],
        "args": action.get("args", []),
        "reason": action.get("reason", ""),
        "reasoning_log_ref": reasoning_ref,
    })

    try:
        resp = requests.post(
            f"{TRACK_B_URL}/execute",
            json={
                "tool": action["tool"],
                "args": action.get("args", []),
                "reasoning_log_ref": reasoning_ref,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as exc:
        result = {"error": str(exc), "output": ""}
        logger.error("Track B call failed for step %d: %s", step_idx, exc)

    write_ledger_entry("action_result", {
        "plan_id": plan_id,
        "step": step_idx,
        "tool": action["tool"],
        "result": result,
        "reasoning_log_ref": reasoning_ref,
    })

    return {
        "step": step_idx,
        "tool": action["tool"],
        "args": action.get("args", []),
        "reason": action.get("reason", ""),
        "result": result,
    }


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

@app.route("/healthz")
def healthz():
    """Kubernetes / Cloud Run health check."""
    return jsonify({"status": "healthy", "track": "A", "service": "control-loop"})


@app.route("/plan", methods=["POST"])
def plan():
    """
    Accept a query from the operator, run the ReAct planning loop,
    and return the full investigation plan with results.
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "Missing 'query' field"}), 400

    rag_corpus = load_rag_context()
    result = react_plan(query, rag_corpus)
    return jsonify(result)


@app.route("/ledger", methods=["GET"])
def ledger():
    """Return the most recent ledger entries (last N lines across all daily files)."""
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


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "track-a-control-loop",
        "version": "0.1.0",
        "model": "C-P-A Control Loop",
        "endpoints": {
            "/healthz": "GET — health check",
            "/plan": "POST — submit query for ReAct planning",
            "/ledger": "GET — retrieve tamper-evident ledger entries",
        },
    })


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Pre-load RAG corpus and policies in background
    rag = load_rag_context()
    policies = load_policies()
    logger.info("Track A starting — %d RAG docs, %d policies loaded", len(rag), len(policies))

    # Restore ledger chain hash from last entry
    ledger_files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"))
    if ledger_files:
        last_lines = ledger_files[-1].read_text(encoding="utf-8").strip().splitlines()
        if last_lines:
            try:
                last_entry = json.loads(last_lines[-1])
                _last_hash = last_entry.get("chain_hash")
            except json.JSONDecodeError:
                pass

    app.run(host="0.0.0.0", port=8080, debug=False)
