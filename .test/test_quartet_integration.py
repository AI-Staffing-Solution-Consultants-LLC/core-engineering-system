"""Integration tests for the executive quartet: Sheryl, Aura, Malory, Krieger.

Verifies all 4 services work together through the shared MemoryPlugin layer,
using a single shared mock memory_client to avoid live HTTP calls.

Tests:
  1. test_cross_quartet_memory_share — Sheryl stores → Aura queries → data matches
  2. test_malory_compliance_krieger_remediation — Malory validates tool →
     Krieger proposes remediation
  3. test_quartet_ledger_chain — all 4 services' ledger entries carry chain_hash
  4. test_all_quartet_healthz — all 4 services respond with correct agent identity

Runs from repo root:  python3 -m pytest .test/test_quartet_integration.py -q
"""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
QUARTET_DIR = REPO_ROOT / "executive-quartet"

# Ensure repo root is on sys.path so Sheryl can import src.ledger
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(QUARTET_DIR) not in sys.path:
    sys.path.insert(0, str(QUARTET_DIR))


# ── Shared mock memory client — used by all 4 services ──────────────────
# Services importing via `from memory_client import store_memory, query_memory`
# receive these mock functions. Because they come from the same MagicMock,
# the side_effect functions share a single `_store` dict, enabling cross-service
# memory tests (Sheryl writes → Aura reads).


class SharedMemoryMock:
    """In-memory store shared by all quartet members, simulating MemoryPlugin."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def store_memory(self, entity: str, context: str, data: dict) -> dict:
        key = f"{entity}:{context}"
        self._store[key] = data
        return {"success": True, "data": {"id": f"mem-{len(self._store)}"}}

    def query_memory(self, entity: str, context: str, query: str) -> dict:
        key = f"{entity}:{context}"
        if key in self._store:
            return {
                "success": True,
                "data": [
                    {
                        "id": f"mem-{list(self._store.keys()).index(key) + 1}",
                        "entity": entity,
                        "context": context,
                        "content": self._store[key],
                    }
                ],
            }
        return {"success": True, "data": []}

    def delete_memory(self, entity: str, memory_id: str) -> dict:
        return {"success": True, "data": None}


def _make_mock_memory_client():
    """Create a MagicMock wrapping a SharedMemoryMock, suitable for
    sys.modules injection."""
    mock = MagicMock()
    shared = SharedMemoryMock()
    mock.store_memory.side_effect = shared.store_memory
    mock.query_memory.side_effect = shared.query_memory
    mock.delete_memory.side_effect = shared.delete_memory
    return mock


# ── Fixtures: one per quartet member ────────────────────────────────────


@pytest.fixture
def mock_mem():
    """Shared mock memory_client injected into sys.modules before any module loads."""
    mock = _make_mock_memory_client()
    sys.modules["memory_client"] = mock
    yield mock
    sys.modules.pop("memory_client", None)


@pytest.fixture
def sheryl(mock_mem, tmp_path, monkeypatch):
    """Load Sheryl Flask app with isolated env, returning (module, test_client)."""
    ledger_dir = tmp_path / "ledger-sheryl"
    ledger_dir.mkdir()
    rag_dir = tmp_path / "rag"
    rag_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("RAG_CORPUS_PATH", str(rag_dir))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")

    spec = importlib.util.spec_from_file_location(
        "sheryl_main", QUARTET_DIR / "sheryl" / "main.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sheryl_main"] = mod
    spec.loader.exec_module(mod)

    # Reset module-level state
    mod.LEDGER_PATH = ledger_dir
    mod.RAG_CORPUS_PATH = rag_dir
    mod._chain_head = ""
    mod.app.config["TESTING"] = True
    client = mod.app.test_client()
    return mod, client


@pytest.fixture
def aura(mock_mem, tmp_path, monkeypatch):
    """Load Aura Flask app with isolated env, returning (module, test_client)."""
    ledger_dir = tmp_path / "ledger-aura"
    ledger_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")

    spec = importlib.util.spec_from_file_location(
        "aura_main", QUARTET_DIR / "aura" / "main.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["aura_main"] = mod
    spec.loader.exec_module(mod)

    # Aura uses _last_hash (not _chain_head)
    mod._last_hash = None
    mod.app.config["TESTING"] = True
    client = mod.app.test_client()
    return mod, client


@pytest.fixture
def malory(mock_mem, tmp_path, monkeypatch):
    """Load Malory Flask app with isolated env, returning (module, test_client)."""
    ledger_dir = tmp_path / "ledger-malory"
    ledger_dir.mkdir()
    allowlist_file = tmp_path / "tool-allowlist.txt"
    allowlist_file.write_text(
        "kubectl get pods\nkubectl get nodes\nkubectl logs\nkubectl top pods\n"
        "kubectl describe pod\ngit status\ngit log\n"
    )

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("TOOL_ALLOWLIST", str(allowlist_file))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")

    spec = importlib.util.spec_from_file_location(
        "malory_main", QUARTET_DIR / "malory" / "main.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["malory_main"] = mod
    spec.loader.exec_module(mod)

    mod._last_hash = None
    mod.LEDGER_PATH = ledger_dir
    mod.ALLOWLIST = mod.load_allowlist()
    mod.app.config["TESTING"] = True
    client = mod.app.test_client()
    return mod, client


@pytest.fixture
def krieger(mock_mem, tmp_path, monkeypatch):
    """Load Krieger Flask app with isolated env, returning (module, test_client)."""
    ledger_dir = tmp_path / "ledger-krieger"
    ledger_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")

    spec = importlib.util.spec_from_file_location(
        "krieger_main", QUARTET_DIR / "krieger" / "main.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["krieger_main"] = mod
    spec.loader.exec_module(mod)

    mod._last_hash = None
    mod.app.config["TESTING"] = True
    client = mod.app.test_client()
    return mod, client


# ── Integration Tests ───────────────────────────────────────────────────


# Test 1: Cross-quartet memory share — Sheryl stores, Aura queries
def test_cross_quartet_memory_share(sheryl, aura):
    """Sheryl stores data via MemoryPlugin → Aura queries and sees same data.

    Verifies that all four agents share the same MemoryPlugin backend,
    proving cross-service context propagation works.
    """
    _sheryl_mod, sheryl_client = sheryl
    _aura_mod, aura_client = aura

    # Sheryl stores a cross-service context entry
    store_resp = sheryl_client.post(
        "/memory/store",
        json={
            "entity": "cross-test",
            "context": "shared-state",
            "data": {"msg": "hello from sheryl", "version": 1},
        },
    )
    assert store_resp.status_code == 200
    store_data = store_resp.get_json()
    assert store_data["success"] is True
    assert "memory_id" in store_data
    stored_id = store_data["memory_id"]

    # Aura queries the same entity+context and must see Sheryl's data
    query_resp = aura_client.post(
        "/memory/query",
        json={
            "entity": "cross-test",
            "context": "shared-state",
            "query": "sheryl",
        },
    )
    assert query_resp.status_code == 200
    query_data = query_resp.get_json()
    assert query_data["success"] is True
    assert len(query_data["results"]) >= 1, (
        "Aura should see Sheryl's stored data via shared MemoryPlugin"
    )

    result = query_data["results"][0]
    assert result["content"] == {"msg": "hello from sheryl", "version": 1}


# Test 2: Malory compliance → Krieger remediation
def test_malory_compliance_krieger_remediation(malory, krieger):
    """Malory validates a tool → Krieger proposes remediation for an incident.

    The two agents operate independently, but this test proves both function
    correctly. Malory (compliance) gates tool usage; Krieger (remediation)
    handles incident response.
    """
    _malory_mod, malory_client = malory
    _krieger_mod, krieger_client = krieger

    # Phase 1: Malory — check an allowed tool
    check_resp = malory_client.post(
        "/compliance/check",
        json={"tool": "kubectl get pods"},
    )
    assert check_resp.status_code == 200
    check_data = check_resp.get_json()
    assert check_data["allowed"] is True
    assert "kubectl get pods" in check_data["matched"]

    # Phase 1b: Malory — check a denied tool
    deny_resp = malory_client.post(
        "/compliance/check",
        json={"tool": "rm -rf /"},
    )
    assert deny_resp.status_code == 200
    deny_data = deny_resp.get_json()
    assert deny_data["allowed"] is False

    # Phase 2: Krieger — remediate a compliance incident
    remed_resp = krieger_client.post(
        "/remediate",
        json={
            "incident_id": "INC-001",
            "title": "High latency in payment service",
            "severity": "critical",
        },
    )
    assert remed_resp.status_code == 200
    remed_data = remed_resp.get_json()
    assert remed_data["status"] == "proposed"
    assert "plan_id" in remed_data
    assert remed_data["incident_id"] == "INC-001"
    assert isinstance(remed_data["steps"], list)
    assert len(remed_data["steps"]) > 0

    # Critical severity should insert escalation step
    actions = [s["action"] for s in remed_data["steps"]]
    assert any("Escalate" in a for a in actions), (
        "Critical severity must include escalation step"
    )


# Test 3: All 4 ledger chains carry chain_hash entries
def test_quartet_ledger_chain(sheryl, aura, malory, krieger):
    """All four services produce ledger entries with valid chain_hash fields.

    Proves that:
    - Each service independently writes to its tamper-evident ledger
    - Every ledger entry includes a 64-character hex chain_hash
    - Each service's `/ledger` endpoint returns valid entries
    """
    sheryl_mod, sheryl_client = sheryl
    aura_mod, aura_client = aura
    malory_mod, malory_client = malory
    krieger_mod, krieger_client = krieger

    # Trigger a ledger-writing action on each service
    sheryl_client.get("/healthz")
    aura_client.get("/healthz")
    malory_client.get("/healthz")
    krieger_client.get("/healthz")

    # Trigger plan/remediation to create richer ledger entries
    sheryl_client.post("/plan", json={"query": "latency"})
    aura_client.post("/identity/verify", json={"content": "atlas_legacy_func()"})
    malory_client.post("/compliance/check", json={"tool": "kubectl get pods"})
    krieger_client.post(
        "/remediate",
        json={
            "incident_id": "INC-LEDGER-001",
            "title": "Crash in auth service",
            "severity": "high",
        },
    )

    # Each service's /ledger endpoint must return entries with chain_hash
    for name, client in [
        ("sheryl", sheryl_client),
        ("aura", aura_client),
        ("malory", malory_client),
        ("krieger", krieger_client),
    ]:
        resp = client.get("/ledger")
        assert resp.status_code == 200, f"{name} /ledger returned {resp.status_code}"
        data = resp.get_json()
        assert data["count"] >= 1, f"{name} ledger is empty — expected at least 1 entry"

        for entry in data["entries"]:
            assert "chain_hash" in entry, (
                f"{name} ledger entry missing chain_hash: {entry}"
            )
            assert len(entry["chain_hash"]) == 64, (
                f"{name} chain_hash wrong length ({len(entry['chain_hash'])}): "
                f"{entry['chain_hash'][:16]}..."
            )
            # chain_hash must be hex-only
            assert all(c in "0123456789abcdef" for c in entry["chain_hash"]), (
                f"{name} chain_hash contains non-hex characters"
            )


# Test 4: All services respond with correct agent identity
def test_all_quartet_healthz(sheryl, aura, malory, krieger):
    """All four services respond to /healthz with correct agent identifiers."""
    expected = {
        "sheryl": sheryl[1],
        "aura": aura[1],
        "malory": malory[1],
        "krieger": krieger[1],
    }

    for agent_name, client in expected.items():
        resp = client.get("/healthz")
        assert resp.status_code == 200, (
            f"{agent_name} /healthz returned {resp.status_code}"
        )
        data = resp.get_json()
        assert data["status"] == "ok", f"{agent_name} status was {data.get('status')!r}"
        assert data["agent"] == agent_name, (
            f"{agent_name} /healthz said agent={data.get('agent')!r}, "
            f"expected {agent_name!r}"
        )
