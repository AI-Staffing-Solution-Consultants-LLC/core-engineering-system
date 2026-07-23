"""TDD tests for executive-quartet/aura/main.py — Aura Flask service on port 8084.

Tests verify:
  1. GET /healthz → {"status":"ok","agent":"aura"}
  2. POST /memory/store → integrates memory_client.store_memory()
  3. POST /memory/query → integrates memory_client.query_memory()
  4. POST /identity/verify → detects atlas_ drift in source
  5. GET /ledger → returns ledger entries via LedgerWriter
"""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, file_path: Path):
    """Load a Python file as a module without requiring it to be a package."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def aura_module(tmp_path, monkeypatch):
    """Load Aura main.py with isolated LEDGER_PATH and mocked memory_client."""
    ledger_dir = tmp_path / "ledger-aura"
    ledger_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))

    # Patch memory_client in advance so we control its behavior
    mock_mem = MagicMock()
    mock_mem.store_memory.return_value = {
        "success": True,
        "data": {"id": "mock-mem-001"},
    }
    mock_mem.query_memory.return_value = {
        "success": True,
        "data": [
            {"id": "mem-001", "data": {"key": "value"}},
        ],
    }
    # Inject mock into sys.modules so aura's import gets our mock
    sys.modules["memory_client"] = mock_mem

    module = _load_module(
        "aura_main",
        REPO_ROOT / "executive-quartet" / "aura" / "main.py",
    )
    module._last_hash = None  # reset chain state per test
    return module


@pytest.fixture
def aura_client(aura_module):
    """Flask test client for Aura agent."""
    aura_module.app.config["TESTING"] = True
    return aura_module.app.test_client()


# ── Tests ─────────────────────────────────────────────────────────────────


class TestHealthz:
    """GET /healthz → {"status":"ok","agent":"aura"}"""

    def test_healthz_returns_ok_with_agent_aura(self, aura_client):
        response = aura_client.get("/healthz")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "ok"
        assert data["agent"] == "aura"


class TestMemoryStore:
    """POST /memory/store → integrates memory_client.store_memory()"""

    def test_memory_store_calls_store_memory_with_correct_params(self, aura_client):
        payload = {
            "entity": "user-42",
            "context": "preferences",
            "data": {"theme": "dark"},
        }
        response = aura_client.post(
            "/memory/store",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["memory_id"] == "mock-mem-001"

    def test_memory_store_returns_400_on_missing_fields(self, aura_client):
        response = aura_client.post(
            "/memory/store",
            data=json.dumps({"entity": "user-42"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestMemoryQuery:
    """POST /memory/query → integrates memory_client.query_memory()"""

    def test_memory_query_calls_query_memory_with_correct_params(self, aura_client):
        payload = {
            "entity": "user-42",
            "context": "preferences",
            "query": "theme",
        }
        response = aura_client.post(
            "/memory/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "mem-001"

    def test_memory_query_returns_400_on_missing_fields(self, aura_client):
        response = aura_client.post(
            "/memory/query",
            data=json.dumps({"entity": "user-42"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestIdentityVerify:
    """POST /identity/verify → checks for atlas_ drift in source tree"""

    def test_identity_verify_detects_atlas_in_content(self, aura_client):
        """Returns drift=true when atlas_ references found in provided content."""
        payload = {"content": "import atlas_config\natlas_init()"}
        response = aura_client.post(
            "/identity/verify",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["drift"] is True
        assert len(data["matches"]) > 0
        # Should have found atlas_config and atlas_init
        assert any("atlas_config" in m for m in data["matches"])
        assert any("atlas_init" in m for m in data["matches"])

    def test_identity_verify_passes_clean_content(self, aura_client):
        """Returns drift=false when no atlas_ references found."""
        payload = {"content": "import aura_config\naura_init()"}
        response = aura_client.post(
            "/identity/verify",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["drift"] is False
        assert len(data["matches"]) == 0

    def test_identity_verify_returns_400_on_missing_content(self, aura_client):
        response = aura_client.post(
            "/identity/verify",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestLedger:
    """GET /ledger → returns SHA-256 chained JSONL ledger entries"""

    def test_ledger_returns_empty_when_no_entries(self, aura_client):
        response = aura_client.get("/ledger")
        assert response.status_code == 200

        data = response.get_json()
        assert "entries" in data
        assert data["count"] == 0

    def test_ledger_returns_entries_after_writes(self, aura_client, aura_module):
        """After writing a ledger entry via the module, /ledger returns it."""
        # Write an entry using the module-level writer
        aura_module.write_ledger_entry(
            "identity_check",
            {"drift_detected": False, "matches": 0},
        )

        response = aura_client.get("/ledger")
        assert response.status_code == 200

        data = response.get_json()
        assert data["count"] == 1
        entry = data["entries"][0]
        assert entry["type"] == "identity_check"
        assert "chain_hash" in entry
        assert len(entry["chain_hash"]) == 64
