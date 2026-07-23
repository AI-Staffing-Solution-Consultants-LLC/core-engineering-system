"""TDD tests for Malory agent — executive-quartet/malory/main.py.

Malory is the compliance-focused agent in the executive quartet.
Tests must pass before implementation is considered complete.

Covers:
  - GET /healthz returns {"status":"ok","agent":"malory"}
  - POST /memory/store proxies to MemoryPlugin
  - POST /memory/query proxies to MemoryPlugin
  - POST /compliance/check validates tools against policy/tool-allowlist.txt
  - GET /ledger returns tamper-evident ledger entries
"""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MALORY_MAIN = REPO_ROOT / "executive-quartet" / "malory" / "main.py"
EQ_DIR = REPO_ROOT / "executive-quartet"


def _load_malory_module(monkeypatch, tmp_path, allowlist_lines=None, mock_memory=None):
    """Load the Malory Flask app with isolated ledger/allowlist paths.

    Args:
        mock_memory: If provided, a mock MemoryPlugin module to inject
                     into sys.modules before loading Malory's main.py.
                     Should have .store_memory and .query_memory attributes.
    """
    ledger_dir = tmp_path / "ledger-malory"
    ledger_dir.mkdir()

    if allowlist_lines is None:
        allowlist_lines = [
            "kubectl get pods\n",
            "kubectl get nodes\n",
            "kubectl logs\n",
            "git status\n",
            "git log\n",
        ]
    allowlist_file = tmp_path / "tool-allowlist-test.txt"
    allowlist_file.write_text("".join(allowlist_lines))

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("TOOL_ALLOWLIST", str(allowlist_file))

    # Ensure executive-quartet is on sys.path so memory_client can be imported
    if str(EQ_DIR) not in sys.path:
        sys.path.insert(0, str(EQ_DIR))

    # Inject mock memory_client before loading the module
    if mock_memory:
        sys.modules["memory_client"] = mock_memory

    spec = importlib.util.spec_from_file_location("malory_test_main", MALORY_MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["malory_test_main"] = module
    spec.loader.exec_module(module)
    module._last_hash = None
    module.LEDGER_PATH = ledger_dir
    module.ALLOWLIST = getattr(module, "load_allowlist", lambda: [])()
    return module


@pytest.fixture
def mock_memory():
    """Mock MemoryPlugin module with store_memory and query_memory functions."""
    mc = MagicMock()
    mc.store_memory = MagicMock(
        return_value={"success": True, "data": {"id": "mem-test-1"}}
    )
    mc.query_memory = MagicMock(
        return_value={"success": True, "data": [{"id": "mem-1", "content": "test"}]}
    )
    return mc


@pytest.fixture
def malory_client(tmp_path, monkeypatch, mock_memory):
    """Flask test client for Malory agent with mocked memory_client."""
    module = _load_malory_module(monkeypatch, tmp_path, mock_memory=mock_memory)
    module._mock_memory = mock_memory
    module.app.config["TESTING"] = True
    client = module.app.test_client()
    # Store module reference for test inspections
    client._mod = module
    yield client


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_healthz_returns_ok(malory_client):
    """GET /healthz returns HTTP 200 with Malory identity."""
    resp = malory_client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["agent"] == "malory"


# ---------------------------------------------------------------------------
# Memory endpoints
# ---------------------------------------------------------------------------


def test_memory_store_proxies_to_memoryplugin(malory_client):
    """POST /memory/store forwards the payload to store_memory and returns result."""
    resp = malory_client.post(
        "/memory/store",
        json={
            "entity": "agent-malory",
            "context": "compliance",
            "data": {"rule": "no-rm-rf"},
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["id"] == "mem-test-1"


def test_memory_query_proxies_to_memoryplugin(malory_client):
    """POST /memory/query forwards the payload to query_memory and returns result."""
    resp = malory_client.post(
        "/memory/query",
        json={
            "entity": "agent-malory",
            "context": "compliance",
            "query": "rm-rf",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_memory_store_missing_entity_returns_400(malory_client):
    """POST /memory/store without 'entity' returns HTTP 400."""
    resp = malory_client.post(
        "/memory/store",
        json={"context": "test", "data": {"key": "val"}},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Compliance check
# ---------------------------------------------------------------------------


def test_compliance_check_allows_valid_tool(malory_client):
    """POST /compliance/check with an allowed tool returns allowed=true."""
    resp = malory_client.post(
        "/compliance/check",
        json={"tool": "kubectl get pods"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["allowed"] is True
    assert "kubectl get pods" in data["matched"]


def test_compliance_check_rejects_unknown_tool(malory_client):
    """POST /compliance/check with a tool NOT in the allowlist returns allowed=false."""
    resp = malory_client.post(
        "/compliance/check",
        json={"tool": "rm -rf /"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["allowed"] is False


def test_compliance_check_missing_tool_returns_400(malory_client):
    """POST /compliance/check without 'tool' field returns HTTP 400."""
    resp = malory_client.post("/compliance/check", json={})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_ledger_returns_entries_array(malory_client):
    """GET /ledger returns a JSON object with an 'entries' key (list)."""
    resp = malory_client.get("/ledger")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_ledger_chain_hashes_are_present(malory_client):
    """GET /ledger entries include chain_hash fields for tamper-evidence."""
    resp = malory_client.get("/ledger")
    data = resp.get_json()
    if len(data["entries"]) > 0:
        for entry in data["entries"]:
            assert "chain_hash" in entry, f"Entry missing chain_hash: {entry}"
