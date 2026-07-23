"""TDD tests for Krieger agent — incident remediation service on port 8086.

Tests verify:
  1. healthz — correct agent identity response
  2. POST /memory/store — delegates to MemoryPlugin store_memory
  3. POST /memory/query — delegates to MemoryPlugin query_memory
  4. POST /remediate — receives incident, proposes remediation plan
  5. GET /ledger — returns ledger entries
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
KRIEGER_MAIN = REPO_ROOT / "executive-quartet" / "krieger" / "main.py"


@pytest.fixture
def krieger_client(tmp_path):
    """Flask test client for Krieger with isolated ledger and mocked MemoryPlugin."""
    ledger_dir = tmp_path / "ledger-krieger"
    ledger_dir.mkdir()

    # Pre-mock the memory_client module so Krieger's imports are intercepted.
    # Krieger adds parent dir to sys.path and does: from memory_client import ...
    # We inject a mock module into sys.modules before loading.
    mock_store = MagicMock(return_value={"success": True, "data": {"id": "mock-mem-1"}})
    mock_query = MagicMock(
        return_value={"success": True, "data": [{"id": "m1", "content": "test"}]}
    )

    mock_mod = MagicMock()
    mock_mod.store_memory = mock_store
    mock_mod.query_memory = mock_query
    sys.modules["memory_client"] = mock_mod

    # Load Krieger module with LEDGER_PATH set
    with patch.dict("os.environ", {"LEDGER_PATH": str(ledger_dir)}):
        spec = importlib.util.spec_from_file_location("krieger_main", KRIEGER_MAIN)
        module = importlib.util.module_from_spec(spec)
        sys.modules["krieger_main"] = module
        spec.loader.exec_module(module)

    module.app.config["TESTING"] = True
    client = module.app.test_client()

    yield client, mock_store, mock_query

    # Cleanup
    sys.modules.pop("memory_client", None)
    sys.modules.pop("krieger_main", None)


# ── Test 1: Health check ──────────────────────────────────────────────


class TestHealthz:
    """Verify /healthz returns correct agent identity."""

    def test_healthz_returns_ok_with_agent_krieger(self, krieger_client):
        """GET /healthz → {"status": "ok", "agent": "krieger"}"""
        client, _, _ = krieger_client
        resp = client.get("/healthz")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["agent"] == "krieger"


# ── Test 2: Memory store ──────────────────────────────────────────────


class TestMemoryStore:
    """Verify /memory/store delegates to MemoryPlugin."""

    def test_memory_store_delegates_to_store_memory(self, krieger_client):
        """POST /memory/store → calls store_memory with entity/context/data."""
        client, mock_store, _ = krieger_client
        payload = {
            "entity": "incident-42",
            "context": "remediation",
            "data": {"severity": "high", "cluster": "us-central1"},
        }
        resp = client.post("/memory/store", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["id"] == "mock-mem-1"
        mock_store.assert_called_once_with(
            entity="incident-42",
            context="remediation",
            data={"severity": "high", "cluster": "us-central1"},
        )

    def test_memory_store_returns_error_on_missing_fields(self, krieger_client):
        """POST /memory/store without entity returns 400."""
        client, _, _ = krieger_client
        resp = client.post("/memory/store", json={"context": "test", "data": {}})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data


# ── Test 3: Memory query ──────────────────────────────────────────────


class TestMemoryQuery:
    """Verify /memory/query delegates to MemoryPlugin."""

    def test_memory_query_delegates_to_query_memory(self, krieger_client):
        """POST /memory/query → calls query_memory with entity/context/query."""
        client, _, mock_query = krieger_client
        payload = {
            "entity": "incident-42",
            "context": "remediation",
            "query": "latency",
        }
        resp = client.post("/memory/query", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "data" in data
        mock_query.assert_called_once_with(
            entity="incident-42",
            context="remediation",
            query="latency",
        )

    def test_memory_query_returns_error_on_missing_fields(self, krieger_client):
        """POST /memory/query without query returns 400."""
        client, _, _ = krieger_client
        resp = client.post("/memory/query", json={"entity": "x", "context": "y"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data


# ── Test 4: Remediation endpoint ──────────────────────────────────────


class TestRemediate:
    """Verify /remediate proposes a remediation plan for an incident."""

    def test_remediate_returns_plan_for_incident(self, krieger_client):
        """POST /remediate → returns plan_id and remediation steps."""
        client, _, _ = krieger_client
        payload = {
            "incident_id": "inc-001",
            "title": "High latency in us-central1",
            "severity": "critical",
        }
        resp = client.post("/remediate", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "plan_id" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0

    def test_remediate_rejects_missing_incident_id(self, krieger_client):
        """POST /remediate without incident_id returns 400."""
        client, _, _ = krieger_client
        resp = client.post("/remediate", json={"title": "test"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data


# ── Test 5: Ledger endpoint ───────────────────────────────────────────


class TestLedger:
    """Verify /ledger returns ledger entries."""

    def test_ledger_returns_entries(self, krieger_client):
        """GET /ledger → returns entries list."""
        client, _, _ = krieger_client
        resp = client.get("/ledger")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert "count" in data
