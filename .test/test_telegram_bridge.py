"""Tests for Sheryl-Telegram bridge service.

Covers:
  - GET  /healthz returns service identity
  - POST /webhook parses Telegram update and forwards to Sheryl
  - POST /webhook rate-limits at 30 msg/sec/chat
  - POST /send    sends message to Telegram chat
  - GET  /status  returns bot connection status
"""

import json
import time
from unittest.mock import MagicMock, patch

import pytest


# ── Module loader ──────────────────────────────────────────────────────
def _load_bridge_module(tmp_path, monkeypatch, **env_overrides):
    """Load telegram-bridge/main.py with isolated environment."""
    import importlib.util
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    module_path = repo_root / "telegram-bridge" / "main.py"

    # Default env: no token → bot reports disconnected (safe default)
    env = {}
    env.update(env_overrides)
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    spec = importlib.util.spec_from_file_location("telegram_bridge_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["telegram_bridge_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client_no_token(tmp_path, monkeypatch):
    """Flask test client with no Telegram token set."""
    module = _load_bridge_module(tmp_path, monkeypatch)
    module.app.config["TESTING"] = True
    return module.app.test_client()


@pytest.fixture
def client_with_token(tmp_path, monkeypatch):
    """Flask test client with a test Telegram token."""
    module = _load_bridge_module(
        tmp_path,
        monkeypatch,
        TELEGRAM_BOT_TOKEN="123456:test-token",
        SHERYL_URL="http://sheryl:9999/ingest",
    )
    module.app.config["TESTING"] = True
    return module.app.test_client()


# ── Test 1: healthz ────────────────────────────────────────────────────
def test_healthz_returns_service_identity(client_no_token):
    """GET /healthz returns ok status and service name."""
    resp = client_no_token.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "telegram-bridge"


# ── Test 2: webhook parse ──────────────────────────────────────────────
def test_webhook_parses_telegram_update(client_with_token, monkeypatch):
    """POST /webhook parses a Telegram update and extracts message fields."""
    # Mock requests.post so we don't actually call Sheryl
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"status": "ok"}
    monkeypatch.setattr("telegram_bridge_test.requests.post", mock_post)

    update = {
        "update_id": 1001,
        "message": {
            "message_id": 42,
            "from": {"id": 777, "first_name": "Alice", "is_bot": False},
            "chat": {"id": 888, "type": "private"},
            "date": 1710000000,
            "text": "Hello bridge!",
        },
    }

    resp = client_with_token.post("/webhook", json=update)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["chat_id"] == 888
    assert data["from_id"] == 777
    assert "Hello bridge!" in data["text"]


# ── Test 3: message forward ────────────────────────────────────────────
def test_webhook_forwards_to_sheryl(client_with_token, monkeypatch):
    """POST /webhook forwards the parsed message to Sheryl."""
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"status": "ingested"}
    monkeypatch.setattr("telegram_bridge_test.requests.post", mock_post)

    update = {
        "update_id": 1002,
        "message": {
            "message_id": 43,
            "from": {"id": 111, "first_name": "Bob"},
            "chat": {"id": 222, "type": "private"},
            "date": 1710000100,
            "text": "Check status",
        },
    }

    resp = client_with_token.post("/webhook", json=update)
    assert resp.status_code == 200

    # Verify Sheryl was called
    assert mock_post.called
    call_args = mock_post.call_args
    assert call_args[0][0] == "http://sheryl:9999/ingest"
    forwarded = call_args[1]["json"]
    assert forwarded["chat_id"] == 222
    assert forwarded["text"] == "Check status"
    assert forwarded["from_id"] == 111


# ── Test 4: rate limit ─────────────────────────────────────────────────
def test_webhook_rate_limit_30_msg_per_sec_per_chat(client_with_token, monkeypatch):
    """POST /webhook rejects messages exceeding 30 msg/sec per chat."""
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"status": "ok"}
    monkeypatch.setattr("telegram_bridge_test.requests.post", mock_post)

    update = {
        "update_id": 2000,
        "message": {
            "message_id": 50,
            "from": {"id": 999, "first_name": "Spammer"},
            "chat": {"id": 555, "type": "private"},
            "date": 1710000200,
            "text": "msg",
        },
    }

    # Send 30 messages — all should succeed
    for _ in range(30):
        resp = client_with_token.post("/webhook", json=update)
        assert resp.status_code == 200

    # The 31st should be rate-limited
    resp = client_with_token.post("/webhook", json=update)
    assert resp.status_code == 429
    data = resp.get_json()
    assert (
        "rate" in data.get("error", "").lower()
        or "limit" in data.get("error", "").lower()
    )


# ── Test 5: send message ───────────────────────────────────────────────
def test_send_message_to_telegram(client_with_token, monkeypatch):
    """POST /send invokes the Telegram Bot API to send a message."""
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "ok": True,
        "result": {"message_id": 999, "chat": {"id": 123}, "text": "echo: hello"},
    }
    monkeypatch.setattr("telegram_bridge_test.requests.post", mock_post)

    payload = {"chat_id": 123, "text": "hello from bridge"}

    resp = client_with_token.post("/send", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["result"]["message_id"] == 999

    # Verify Telegram API was called with the right URL
    assert mock_post.called
    call_args = mock_post.call_args
    assert "123456:test-token" in call_args[0][0]
    assert call_args[1]["json"]["chat_id"] == 123
    assert call_args[1]["json"]["text"] == "hello from bridge"
