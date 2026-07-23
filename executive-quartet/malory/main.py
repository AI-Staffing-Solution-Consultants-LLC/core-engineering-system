"""
Malory — Compliance & Audit Agent (Executive Quartet)

Malory is the rule-keeper. Responsibilities:
  - MemoryPlugin integration (store / query cross-agent context)
  - Tool compliance checking against policy/tool-allowlist.txt
  - Tamper-evident ledger for audit trail
  - Read-only access to policy — never modifies allowlist

Follows the Sheryl agent pattern: minimal Flask service, single-responsibility,
shared memory_client for persistence.
"""

import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory_client import store_memory, query_memory  # noqa: E402

LEDGER_PATH = Path(os.environ.get("LEDGER_PATH", "/var/log/ledger"))
ALLOWLIST_PATH = Path(
    os.environ.get(
        "TOOL_ALLOWLIST",
        str(
            Path(__file__).resolve().parent.parent.parent
            / "policy"
            / "tool-allowlist.txt"
        ),
    )
)

LEDGER_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] malory/%(funcName)s %(message)s",
)
logger = logging.getLogger("malory")

_last_hash: str | None = None


def load_allowlist() -> list[str]:
    if not ALLOWLIST_PATH.is_file():
        logger.warning(
            "Allowlist file %s not found — rejecting all tools", ALLOWLIST_PATH
        )
        return []
    lines = ALLOWLIST_PATH.read_text(encoding="utf-8").strip().splitlines()
    allowlist = [
        line.strip() for line in lines if line.strip() and not line.startswith("#")
    ]
    logger.info("Loaded %d allowlisted tools", len(allowlist))
    return allowlist


ALLOWLIST: list[str] = load_allowlist()


def _build_chain_hash(prev_hash: str | None, entry_str: str) -> str:
    return hashlib.sha256(((prev_hash or "") + entry_str).encode("utf-8")).hexdigest()


def write_ledger_entry(event_type: str, payload: dict) -> str:
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


def _is_allowed(tool: str) -> tuple[bool, str]:
    for allowed in ALLOWLIST:
        if tool == allowed or tool.startswith(allowed + " "):
            return True, allowed
    return False, ""


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "agent": "malory"})


@app.route("/memory/store", methods=["POST"])
def memory_store():
    body = request.get_json(silent=True) or {}
    entity = body.get("entity", "").strip()
    context = body.get("context", "").strip()
    data = body.get("data")
    if not entity:
        return jsonify({"error": "Missing 'entity' field"}), 400
    if not context:
        return jsonify({"error": "Missing 'context' field"}), 400
    if data is None:
        return jsonify({"error": "Missing 'data' field"}), 400

    try:
        result = store_memory(entity=entity, context=context, data=data)
        write_ledger_entry(
            "memory_store", {"entity": entity, "context": context, "result": result}
        )
        return jsonify(result)
    except Exception as exc:
        logger.error("store_memory failed: %s", exc)
        write_ledger_entry(
            "memory_store_error",
            {"entity": entity, "context": context, "error": str(exc)},
        )
        return jsonify({"error": str(exc)}), 502


@app.route("/memory/query", methods=["POST"])
def memory_query():
    body = request.get_json(silent=True) or {}
    entity = body.get("entity", "").strip()
    context = body.get("context", "").strip()
    query_text = body.get("query", "").strip()
    if not entity:
        return jsonify({"error": "Missing 'entity' field"}), 400
    if not context:
        return jsonify({"error": "Missing 'context' field"}), 400
    if not query_text:
        return jsonify({"error": "Missing 'query' field"}), 400

    try:
        result = query_memory(entity=entity, context=context, query=query_text)
        write_ledger_entry(
            "memory_query",
            {
                "entity": entity,
                "context": context,
                "query": query_text,
                "result": result,
            },
        )
        return jsonify(result)
    except Exception as exc:
        logger.error("query_memory failed: %s", exc)
        write_ledger_entry(
            "memory_query_error",
            {
                "entity": entity,
                "context": context,
                "query": query_text,
                "error": str(exc),
            },
        )
        return jsonify({"error": str(exc)}), 502


@app.route("/compliance/check", methods=["POST"])
def compliance_check():
    body = request.get_json(silent=True) or {}
    tool = body.get("tool", "").strip()
    if not tool:
        return jsonify({"error": "Missing 'tool' field"}), 400

    allowed, matched = _is_allowed(tool)
    entry_payload = {
        "tool": tool,
        "allowed": allowed,
        "matched": matched if allowed else None,
    }
    write_ledger_entry("compliance_check", entry_payload)

    response = {"allowed": allowed}
    if allowed:
        response["matched"] = matched

    if not allowed:
        logger.info("Rejected non-allowlisted tool: %r", tool)

    return jsonify(response)


@app.route("/ledger", methods=["GET"])
def ledger():
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
    return jsonify(
        {
            "service": "malory-compliance-agent",
            "version": "0.1.0",
            "endpoints": {
                "/healthz": "GET — health check",
                "/memory/store": "POST — store memory entry",
                "/memory/query": "POST — query memories",
                "/compliance/check": "POST — check tool against allowlist",
                "/ledger": "GET — retrieve tamper-evident ledger",
            },
        }
    )


if __name__ == "__main__":
    ledger_files = sorted(LEDGER_PATH.glob("ledger-*.jsonl"))
    if ledger_files:
        last_lines = ledger_files[-1].read_text(encoding="utf-8").strip().splitlines()
        if last_lines:
            try:
                last_entry = json.loads(last_lines[-1])
                _last_hash = last_entry.get("chain_hash")
            except json.JSONDecodeError:
                pass

    logger.info(
        "Malory starting — allowlist: %d tools, ledger: %s", len(ALLOWLIST), LEDGER_PATH
    )
    app.run(host="0.0.0.0", port=8085, debug=False)
