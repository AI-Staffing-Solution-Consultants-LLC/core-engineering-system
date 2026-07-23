"""TDD tests for Sheryl agent Flask service.

Sheryl runs on port 8083 and acts as the memory/context specialist
in the executive quartet. Tests follow the conftest.py importlib pattern.

Must be run from repo root:
    python -m pytest executive-quartet/sheryl/test_sheryl.py -v
"""

import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "executive-quartet"))


# --------------------------------------------------------------------------
# Fixtures — isolate ledger, memory_client, and RAG path
# --------------------------------------------------------------------------


@pytest.fixture
def sheryl_module(tmp_path, monkeypatch):
    """Load Sheryl with isolated LEDGER_PATH, empty RAG dir, and mocked memory_client."""
    import importlib.util

    ledger_dir = tmp_path / "ledger-sheryl"
    ledger_dir.mkdir()
    rag_dir = tmp_path / "rag"
    rag_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("RAG_CORPUS_PATH", str(rag_dir))

    spec = importlib.util.spec_from_file_location(
        "sheryl_main", REPO_ROOT / "executive-quartet" / "sheryl" / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["sheryl_main"] = module
    spec.loader.exec_module(module)

    # Reset module-level state set during startup
    module.LEDGER_PATH = ledger_dir
    module.RAG_CORPUS_PATH = rag_dir
    if hasattr(module, "_last_hash"):
        module._last_hash = None

    # Mock memory_client.store_memory and query_memory so we don't hit actual API
    monkeypatch.setattr(
        module,
        "store_memory",
        MagicMock(return_value={"success": True, "data": {"id": "mock-mem-1"}}),
    )
    monkeypatch.setattr(
        module,
        "query_memory",
        MagicMock(
            return_value={
                "success": True,
                "data": [{"id": "mock-mem-1", "content": "mock result"}],
            }
        ),
    )

    return module


@pytest.fixture
def sheryl_client(sheryl_module):
    """Flask test client for Sheryl on port 8083."""
    sheryl_module.app.config["TESTING"] = True
    return sheryl_module.app.test_client()


# --------------------------------------------------------------------------
# Test 1: GET /healthz — agent identity
# --------------------------------------------------------------------------


def test_healthz_returns_200(sheryl_client):
    """GET /healthz returns HTTP 200 with sheryl agent identity."""
    resp = sheryl_client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["agent"] == "sheryl"


# --------------------------------------------------------------------------
# Test 2: POST /memory/store — store context
# --------------------------------------------------------------------------


def test_memory_store_stores_context(sheryl_client):
    """POST /memory/store stores context via memory_client.store_memory."""
    resp = sheryl_client.post(
        "/memory/store",
        json={"entity": "user-1", "context": "prefs", "data": {"theme": "dark"}},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["memory_id"] == "mock-mem-1"


def test_memory_store_missing_fields_returns_400(sheryl_client):
    """POST /memory/store with missing entity returns 400."""
    resp = sheryl_client.post(
        "/memory/store",
        json={"context": "prefs", "data": {}},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# --------------------------------------------------------------------------
# Test 3: POST /memory/query — query MemoryPlugin
# --------------------------------------------------------------------------


def test_memory_query_returns_results(sheryl_client):
    """POST /memory/query queries MemoryPlugin and returns results."""
    resp = sheryl_client.post(
        "/memory/query",
        json={"entity": "user-1", "context": "prefs", "query": "theme"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "data" in data
    assert isinstance(data["data"], list)


def test_memory_query_missing_query_returns_400(sheryl_client):
    """POST /memory/query with missing query field returns 400."""
    resp = sheryl_client.post(
        "/memory/query",
        json={"entity": "user-1", "context": "prefs"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# --------------------------------------------------------------------------
# Test 4: POST /plan — consult RAG + MemoryPlugin
# --------------------------------------------------------------------------


def test_plan_returns_plan_structure(sheryl_client):
    """POST /plan returns a plan with plan_id, hypothesis, and steps."""
    resp = sheryl_client.post(
        "/plan",
        json={"query": "why is latency high"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "plan_id" in data
    assert isinstance(data["plan_id"], str)
    assert "hypothesis" in data
    assert isinstance(data["hypothesis"], str)
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0
    assert data["source"] == "sheryl"


def test_plan_missing_query_returns_400(sheryl_client):
    """POST /plan with missing query returns 400."""
    resp = sheryl_client.post("/plan", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# --------------------------------------------------------------------------
# Test 5: GET /ledger — read entries
# --------------------------------------------------------------------------


def test_ledger_returns_entries(sheryl_client):
    """GET /ledger returns ledger entries list."""
    # Write a plan to produce at least one ledger entry
    sheryl_client.post("/plan", json={"query": "crash"})

    resp = sheryl_client.get("/ledger")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) > 0
    assert "count" in data


# --------------------------------------------------------------------------
# Test 6: Dockerfile has non-root user
# --------------------------------------------------------------------------


def test_dockerfile_has_non_root_user():
    """Sheryl Dockerfile must define a non-root 'coreengine' user."""
    dockerfile = REPO_ROOT / "executive-quartet" / "sheryl" / "Dockerfile"
    assert dockerfile.is_file(), f"Dockerfile missing at {dockerfile}"
    content = dockerfile.read_text()
    assert "useradd" in content.lower() or "user add" in content.lower(), (
        "Dockerfile must create a non-root user"
    )
    assert re.search(r"USER\s+coreengine", content), (
        "Dockerfile must switch to 'coreengine' user via USER directive"
    )
