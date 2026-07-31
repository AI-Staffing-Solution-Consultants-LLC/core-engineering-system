"""
<DEPARTMENT_NAME> — <DEPARTMENT_SLUG>
Phase <PHASE_NUMBER> — <PHASE_DESCRIPTION>

Minimal Flask skeleton. Loads agent/service config at startup.
No business logic — skeleton only.
"""

import json
import logging
import os
from pathlib import Path

from flask import Flask, jsonify

# ---------------------------------------------------------------------------
# Configuration — all values from environment
# ---------------------------------------------------------------------------
DEPARTMENT_NAME = os.environ.get("DEPARTMENT_NAME", "<DEPARTMENT_NAME>")
DEPARTMENT_SLUG = os.environ.get("DEPARTMENT_SLUG", "<SLUG>")
PORT = int(os.environ.get("PORT", "8080"))

AGENTOS_CONFIG_PATH = Path(os.environ.get("AGENTOS_CONFIG_PATH", "/app/agents.json"))
PAPERCLIP_CONFIG_PATH = Path(
    os.environ.get("PAPERCLIP_CONFIG_PATH", "/app/paperclip-config.json")
)

# Phase 2+ departments load these optional configs
REDIS_CLIENT_PATH = Path("/app/redis-client.json")
VIKING_RAG_PATH = Path("/app/viking-rag.json")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(DEPARTMENT_SLUG)


# ---------------------------------------------------------------------------
# Config loading — skeletons only, no business logic
# ---------------------------------------------------------------------------
def load_agentos_config() -> dict:
    """Load agent roster from agents.json."""
    if not AGENTOS_CONFIG_PATH.is_file():
        logger.warning(
            "AgentOS config not found at %s — running headless", AGENTOS_CONFIG_PATH
        )
        return {}
    data = json.loads(AGENTOS_CONFIG_PATH.read_text(encoding="utf-8"))
    logger.info("AgentOS config loaded: %d agents defined", len(data.get("agents", [])))
    return data


def load_paperclip_config() -> dict:
    """Load EIM workflow config from paperclip-config.json."""
    if not PAPERCLIP_CONFIG_PATH.is_file():
        logger.warning("Paperclip config not found at %s", PAPERCLIP_CONFIG_PATH)
        return {}
    data = json.loads(PAPERCLIP_CONFIG_PATH.read_text(encoding="utf-8"))
    logger.info("Paperclip workflow loaded: %s", data.get("workflow_name", "unknown"))
    return data


def load_redis_config() -> dict:
    """Load Redis connection config — Protocol A skeleton."""
    if not REDIS_CLIENT_PATH.is_file():
        logger.info("redis-client.json not found — Redis disabled")
        return {}
    data = json.loads(REDIS_CLIENT_PATH.read_text(encoding="utf-8"))
    logger.info("Redis config loaded (Protocol A)")
    return data


def load_viking_config() -> dict:
    """Load OpenViking RAG config — Protocol B skeleton."""
    if not VIKING_RAG_PATH.is_file():
        logger.info("viking-rag.json not found — RAG disabled")
        return {}
    data = json.loads(VIKING_RAG_PATH.read_text(encoding="utf-8"))
    logger.info("Viking RAG config loaded (Protocol B)")
    return data


# Load configs at module startup
agentos_cfg = load_agentos_config()
paperclip_cfg = load_paperclip_config()
redis_cfg = load_redis_config()
viking_cfg = load_viking_config()


# ---------------------------------------------------------------------------
# Routes — health check only (skeleton)
# ---------------------------------------------------------------------------
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify(
        {
            "status": "ok",
            "department": DEPARTMENT_NAME,
            "slug": DEPARTMENT_SLUG,
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(
        "Starting %s (slug: %s) on port %d", DEPARTMENT_NAME, DEPARTMENT_SLUG, PORT
    )
    app.run(host="0.0.0.0", port=PORT)
