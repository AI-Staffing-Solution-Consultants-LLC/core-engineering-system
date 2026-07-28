"""
Sheryl-Telegram Bridge — Webhook bridge service.

Receives Telegram webhook updates, parses messages, forwards to Sheryl,
and provides a /send endpoint for outbound Telegram messaging.

Port 8088. Token ONLY from env var (TELEGRAM_BOT_TOKEN).
Rate-limited: 30 messages per second per chat.
"""

import logging
import os
import threading
import time
from collections import defaultdict

import requests
from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Configuration — token from env ONLY, never hardcoded
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SHERYL_URL = os.environ.get("SHERYL_URL", "http://sheryl:8083/ingest")
TELEGRAM_API_BASE = "https://api.telegram.org"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("telegram-bridge")


# ---------------------------------------------------------------------------
# Rate limiter — 30 msg/sec/chat (in-memory, per-process)
# ---------------------------------------------------------------------------
RATE_LIMIT = 30  # messages per second per chat
_rate_buckets: dict[int, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()


def _check_rate(chat_id: int) -> bool:
    """Return True if the message is within the rate limit for this chat."""
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets[chat_id]
        # Prune timestamps older than 1 second
        cutoff = now - 1.0
        _rate_buckets[chat_id] = [t for t in bucket if t > cutoff]
        if len(_rate_buckets[chat_id]) >= RATE_LIMIT:
            return False
        _rate_buckets[chat_id].append(now)
        return True


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------


@app.route("/healthz")
def healthz():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "telegram-bridge"})


@app.route("/status")
def status():
    """Bot connection status — checks whether the token is configured."""
    token_configured = bool(TELEGRAM_BOT_TOKEN)
    if not token_configured:
        return jsonify(
            {
                "status": "disconnected",
                "reason": "TELEGRAM_BOT_TOKEN not set",
                "service": "telegram-bridge",
            }
        ), 503

    # Lightweight connectivity check — getMe
    try:
        resp = requests.get(
            f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/getMe",
            timeout=10,
        )
        if resp.status_code == 200:
            bot_info = resp.json()
            return jsonify(
                {
                    "status": "connected",
                    "service": "telegram-bridge",
                    "bot": bot_info.get("result", {}),
                }
            )
        else:
            return jsonify(
                {
                    "status": "error",
                    "service": "telegram-bridge",
                    "telegram_error": resp.text[:200],
                }
            ), 502
    except requests.RequestException as exc:
        return jsonify(
            {
                "status": "error",
                "service": "telegram-bridge",
                "reason": str(exc)[:200],
            }
        ), 502


@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive a Telegram Update, parse it, forward to Sheryl.

    Expects the standard Telegram Bot API Update JSON:
      https://core.telegram.org/bots/api#update
    """
    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"error": "empty or invalid JSON body"}), 400

    # Extract message (Telegram updates can be various types)
    message = body.get("message") or body.get("edited_message")
    if not message:
        return jsonify(
            {"error": "update contains no message", "update_id": body.get("update_id")}
        ), 200

    chat = message.get("chat", {})
    sender = message.get("from", {})
    chat_id = chat.get("id")
    from_id = sender.get("id")
    text = message.get("text", "")
    caption = message.get("caption", "")

    if chat_id is None:
        return jsonify(
            {"error": "missing chat_id", "update_id": body.get("update_id")}
        ), 400

    # Rate-limit: 30 msg/sec per chat
    if not _check_rate(chat_id):
        logger.warning("Rate limit exceeded for chat %s", chat_id)
        return jsonify({"error": "rate limit exceeded", "chat_id": chat_id}), 429

    parsed = {
        "update_id": body.get("update_id"),
        "chat_id": chat_id,
        "chat_type": chat.get("type"),
        "from_id": from_id,
        "from_name": sender.get("first_name", ""),
        "text": text,
        "caption": caption,
        "message_id": message.get("message_id"),
    }
    logger.info(
        "Parsed update %s — chat=%s from=%s text_preview=%s",
        parsed["update_id"],
        chat_id,
        from_id,
        (text or caption)[:60],
    )

    # Forward to Sheryl
    sheryl_ok = True
    sheryl_error = None
    try:
        resp = requests.post(
            SHERYL_URL,
            json=parsed,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Sheryl forward failed: %s", exc)
        sheryl_ok = False
        sheryl_error = str(exc)

    return jsonify(
        {
            "status": "ok",
            "chat_id": chat_id,
            "from_id": from_id,
            "text": text or caption,
            "sheryl_forwarded": sheryl_ok,
            "sheryl_error": sheryl_error,
        }
    )


@app.route("/send", methods=["POST"])
def send_message():
    """Send a message to a Telegram chat via the Bot API.

    Body: {"chat_id": <int>, "text": "<message>"}
    """
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({"error": "TELEGRAM_BOT_TOKEN not configured"}), 503

    body = request.get_json(silent=True) or {}
    chat_id = body.get("chat_id")
    text = body.get("text", "")

    if chat_id is None or not text:
        return jsonify({"error": "chat_id and text are required"}), 400

    try:
        resp = requests.post(
            f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as exc:
        logger.error("sendMessage failed: %s", exc)
        return jsonify({"error": str(exc)}), 502


@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "service": "telegram-bridge",
            "version": "0.1.0",
            "endpoints": {
                "/healthz": "GET — health check",
                "/status": "GET — bot connection status",
                "/webhook": "POST — receive Telegram update",
                "/send": "POST — send message to Telegram chat",
            },
        }
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    token_state = "configured" if TELEGRAM_BOT_TOKEN else "MISSING"
    logger.info(
        "Telegram Bridge starting on :8088 — token=%s sheryl=%s",
        token_state,
        SHERYL_URL,
    )
    # NOTE: never log the token value itself
    app.run(host="0.0.0.0", port=8088, debug=False)
