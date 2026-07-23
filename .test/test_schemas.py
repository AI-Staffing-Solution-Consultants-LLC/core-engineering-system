"""TDD tests for src/schemas/ dataclass modules."""

import json
from dataclasses import asdict
import pytest

from src.schemas import (
    ExecutiveQuartetMember,
    MemoryPluginRequest,
    MemoryPluginResponse,
    LedgerEntry,
    WebRTCSignal,
    TelegramMessage,
    TelegramWebhook,
    BoardLogEntry,
    AuditFinding,
)


# ── Executive Quartet ──────────────────────────────────────────────


def test_executive_quartet_valid():
    """Instantiate ExecutiveQuartetMember with valid data."""
    m = ExecutiveQuartetMember(
        name="Alpha", port=8800, personality="analyst", memory_context="ctx-1"
    )
    assert m.name == "Alpha"
    assert m.port == 8800
    assert m.personality == "analyst"
    assert m.memory_context == "ctx-1"


def test_executive_quartet_port_too_low():
    """Reject port below 1024."""
    with pytest.raises(ValueError, match="port"):
        ExecutiveQuartetMember(
            name="Beta", port=80, personality="critic", memory_context="ctx-2"
        )


def test_executive_quartet_port_too_high():
    """Reject port above 65535."""
    with pytest.raises(ValueError, match="port"):
        ExecutiveQuartetMember(
            name="Gamma", port=99999, personality="executor", memory_context="ctx-3"
        )


def test_executive_quartet_empty_name():
    """Reject empty name."""
    with pytest.raises(ValueError, match="name"):
        ExecutiveQuartetMember(
            name="", port=5000, personality="observer", memory_context="ctx-4"
        )


# ── Memory Plugin ──────────────────────────────────────────────────


def test_memory_plugin_request_serialize():
    """MemoryPluginRequest serializes to dict correctly."""
    req = MemoryPluginRequest(
        operation="store", context="session-1", entity="user-42", payload={"key": "val"}
    )
    d = asdict(req)
    assert d["operation"] == "store"
    assert d["payload"] == {"key": "val"}


def test_memory_plugin_response_defaults():
    """MemoryPluginResponse defaults error to empty string."""
    resp = MemoryPluginResponse(success=True, data={"id": 1})
    assert resp.error == ""
    assert resp.success is True


# ── Ledger Entry ───────────────────────────────────────────────────


def test_ledger_entry_serialize():
    """LedgerEntry serializes with all fields."""
    entry = LedgerEntry(
        type="exec",
        timestamp="2025-01-01T00:00:00Z",
        data={"cmd": "ls"},
        prev_hash="abc",
        chain_hash="def",
    )
    d = asdict(entry)
    assert d["type"] == "exec"
    assert d["prev_hash"] == "abc"
    assert d["chain_hash"] == "def"


# ── WebRTC Signal ──────────────────────────────────────────────────


def test_webrtc_signal_defaults():
    """WebRTCSignal uses provided defaults when fields omitted."""
    sig = WebRTCSignal(type="offer", session_id="s1")
    assert sig.sdp == ""
    assert sig.candidate == ""
    assert sig.type == "offer"


# ── Telegram ───────────────────────────────────────────────────────


def test_telegram_message_defaults():
    """TelegramMessage defaults command to empty string."""
    msg = TelegramMessage(chat_id=123, text="hello")
    assert msg.command == ""
    assert msg.chat_id == 123


def test_telegram_webhook_instantiate():
    """TelegramWebhook holds nested message dict."""
    wh = TelegramWebhook(update_id=1, message={"chat": {"id": 456}, "text": "ping"})
    assert wh.update_id == 1
    assert wh.message["text"] == "ping"


# ── Audit ──────────────────────────────────────────────────────────


def test_audit_board_log_entry_serialize():
    """BoardLogEntry serializes to dict."""
    entry = BoardLogEntry(
        action="approved",
        result="pass",
        reasoning_ref="ref-001",
        timestamp="2025-01-01T00:00:00Z",
    )
    d = asdict(entry)
    assert d["action"] == "approved"
    assert d["result"] == "pass"


def test_audit_finding_instantiate():
    """AuditFinding holds severity, reason, and evidence dict."""
    finding = AuditFinding(
        severity="HIGH", reason="unauthorized access", evidence={"log": "line 42"}
    )
    assert finding.severity == "HIGH"
    assert finding.evidence["log"] == "line 42"
