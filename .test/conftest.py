"""
Pytest configuration and fixtures for core-engineering-system tests.

Provides isolated Flask test clients for Track A (control loop) and Track B (actuator).
Each test gets its own temporary LEDGER_PATH and TOOL_ALLOWLIST to avoid cross-test pollution.

Track A and Track B are loaded via importlib (not as packages) because their directory
names contain hyphens (`track-a/`, `track-b/`) which are not valid Python identifiers.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, file_path: Path):
    """Load a Python file as a module without requiring it to be a package."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _mock_track_b_post(url, json=None, timeout=None, **kwargs):
    """Mock Track B HTTP response so Track A tests don't need a live Track B."""

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "allowed": True,
                "exit_code": 0,
                "stdout": "mocked-output",
                "stderr": "",
            }

    return MockResponse()


@pytest.fixture
def track_a_module(tmp_path, monkeypatch):
    """Load Track A with isolated LEDGER_PATH, empty RAG/POLICY dirs, and mocked Track B calls."""
    ledger_dir = tmp_path / "ledger-a"
    ledger_dir.mkdir()
    rag_dir = tmp_path / "rag"
    rag_dir.mkdir()
    policy_dir = tmp_path / "policy"
    policy_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("RAG_CORPUS_PATH", str(rag_dir))
    monkeypatch.setenv("POLICY_DIR", str(policy_dir))

    module = _load_module("track_a_test_main", REPO_ROOT / "track-a" / "main.py")
    module._last_hash = None
    module.LEDGER_PATH = ledger_dir

    # Mock Track B HTTP calls so /plan tests don't need a live Track B service.
    monkeypatch.setattr(module.requests, "post", _mock_track_b_post)

    return module


@pytest.fixture
def track_b_module(tmp_path, monkeypatch):
    """Load Track B with isolated LEDGER_PATH and a minimal test allowlist."""
    ledger_dir = tmp_path / "ledger-b"
    ledger_dir.mkdir()
    allowlist_file = tmp_path / "tool-allowlist.txt"
    allowlist_file.write_text(
        "kubectl get pods\nkubectl get nodes\nkubectl logs\ngit status\ngit log\n"
    )

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("TOOL_ALLOWLIST", str(allowlist_file))

    module = _load_module("track_b_test_main", REPO_ROOT / "track-b" / "main.py")
    module._last_hash = None
    module.LEDGER_PATH = ledger_dir
    module.ALLOWLIST = module.load_allowlist()
    return module


@pytest.fixture
def track_a_client(track_a_module):
    """Flask test client for Track A."""
    track_a_module.app.config["TESTING"] = True
    return track_a_module.app.test_client()


@pytest.fixture
def track_b_client(track_b_module):
    """Flask test client for Track B."""
    track_b_module.app.config["TESTING"] = True
    return track_b_module.app.test_client()


# ── Service fixtures ────────────────────────────────────────────────


class LedgerWriter:
    """Minimal ledger writer backed by a temp directory (JSONL, SHA-256 chained)."""

    def __init__(self, ledger_path: Path):
        self.ledger_path = ledger_path
        self._last_hash = None

    def write(self, entry_type: str, payload: dict) -> str:
        import hashlib
        import json
        from datetime import datetime, timezone

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = self.ledger_path / f"ledger-{date_str}.jsonl"

        entry = {
            "type": entry_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        payload_str = (self._last_hash or "") + json.dumps(entry, sort_keys=True)
        chain_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        entry["chain_hash"] = chain_hash

        with open(file_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

        self._last_hash = chain_hash
        return chain_hash


@pytest.fixture
def ledger_writer(tmp_path) -> LedgerWriter:
    """Returns a LedgerWriter backed by a temporary directory."""
    ledger_dir = tmp_path / "ledger-test"
    ledger_dir.mkdir()
    return LedgerWriter(ledger_dir)


@pytest.fixture
def mock_memory_plugin():
    """Returns a mock MemoryPlugin that records store/recall calls."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.store.return_value = {"success": True, "data": {"id": "mock-mem-1"}}
    mock.recall.return_value = {"success": True, "data": []}
    return mock


@pytest.fixture
def mock_telegram():
    """Returns a mock Telegram API that records sent messages."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.send_message.return_value = {"ok": True, "result": {"message_id": 999}}
    return mock
