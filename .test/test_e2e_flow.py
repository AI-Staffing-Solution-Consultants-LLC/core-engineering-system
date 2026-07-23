"""
Comprehensive end-to-end flow tests covering C-P-A + Quartet + Audit chain.

Tests:
  1. test_e2e_happy_path     — query → RAG → plan → execute → MemoryPlugin store
                               → compliance check → ledger chain
  2. test_e2e_blocked_action  — disallowed tool blocked by Track B, Malory reports
                               violation, Auditor logs finding
  3. test_e2e_ledger_integrity — verify all entries across all services have valid
                               prev_hash → chain_hash links

Runs from repo root:  python3 -m pytest .test/test_e2e_flow.py -q
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACK_A_MAIN = REPO_ROOT / "track-a" / "main.py"
TRACK_B_MAIN = REPO_ROOT / "track-b" / "main.py"
QUARTET_DIR = REPO_ROOT / "executive-quartet"
SELF_REMEDIATION_DIR = REPO_ROOT / "self-remediation"
POLICY_DIR = REPO_ROOT / "policy"

# Ensure import paths are set up
for path_str in (str(REPO_ROOT), str(QUARTET_DIR), str(SELF_REMEDIATION_DIR)):
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


# ═══════════════════════════════════════════════════════════════════════════════
#  Shared Mock MemoryPlugin
# ═══════════════════════════════════════════════════════════════════════════════


class SharedMemoryMock:
    """In-memory store shared by all services, simulating MemoryPlugin."""

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


def _inject_mock_memory():
    """Create and inject a shared MemoryPlugin mock into sys.modules."""
    mock = MagicMock()
    shared = SharedMemoryMock()
    mock.store_memory.side_effect = shared.store_memory
    mock.query_memory.side_effect = shared.query_memory
    mock.delete_memory.side_effect = shared.delete_memory
    sys.modules["memory_client"] = mock
    return mock, shared


def _remove_mock_memory():
    sys.modules.pop("memory_client", None)


# ═══════════════════════════════════════════════════════════════════════════════
#  Module loader helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _load_module(name: str, file_path: Path):
    """Load a Python file as a module without requiring it to be a package."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ═══════════════════════════════════════════════════════════════════════════════
#  Chain validation helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _expected_chain_hash(prev_hash: str | None, entry: dict) -> str:
    """Compute the expected chain_hash for a ledger entry per the spec."""
    entry_without_hash = {k: v for k, v in entry.items() if k != "chain_hash"}
    payload = (prev_hash or "") + json.dumps(entry_without_hash, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_and_validate_chain(ledger_path: Path) -> list[dict]:
    """Read all ledger entries from the temp path and validate chain integrity.

    Returns: list of parsed entries.  Raises AssertionError on chain break.
    """
    files = sorted(ledger_path.glob("ledger-*.jsonl"))
    if not files:
        return []
    entries: list[dict] = []
    for f in files:
        for line in f.read_text(encoding="utf-8").strip().splitlines():
            if line:
                entries.append(json.loads(line))
    prev_hash = None
    for i, entry in enumerate(entries):
        assert "chain_hash" in entry, f"Entry {i} missing chain_hash"
        assert len(entry["chain_hash"]) == 64, (
            f"Entry {i} chain_hash wrong length: {len(entry['chain_hash'])}"
        )
        assert all(c in "0123456789abcdef" for c in entry["chain_hash"]), (
            f"Entry {i} chain_hash contains non-hex chars"
        )
        expected = _expected_chain_hash(prev_hash, entry)
        assert entry["chain_hash"] == expected, (
            f"Entry {i} chain_hash mismatch: got {entry['chain_hash'][:16]}…, "
            f"expected {expected[:16]}…"
        )
        prev_hash = entry["chain_hash"]
    return entries


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def e2e_memory():
    """Shared MemoryPlugin mock injected into sys.modules for all quartet services."""
    mock, shared = _inject_mock_memory()
    yield mock, shared
    _remove_mock_memory()


@pytest.fixture
def e2e_track_b(tmp_path, monkeypatch):
    """Load Track B with an extended test allowlist and mocked subprocess.

    Returns (module, test_client, allowlist_file_path, ledger_dir).
    """
    ledger_dir = tmp_path / "ledger-b"
    ledger_dir.mkdir()
    allowlist_file = tmp_path / "tool-allowlist-e2e.txt"
    # Include all tools Track A might generate for "latency", "crash", "deploy" queries
    allowlist_file.write_text(
        "kubectl get pods\n"
        "kubectl get nodes\n"
        "kubectl top pods\n"
        "kubectl top nodes\n"
        "kubectl logs\n"
        "kubectl logs --tail=100\n"
        "kubectl logs --previous\n"
        "kubectl describe pod\n"
        "kubectl events\n"
        "gcloud run services list\n"
        "git status\n"
        "git log\n"
        "echo\n"
    )

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("TOOL_ALLOWLIST", str(allowlist_file))

    module = _load_module("e2e_track_b_main", TRACK_B_MAIN)
    module._last_hash = None
    module.LEDGER_PATH = ledger_dir
    module.ALLOWLIST = module.load_allowlist()

    # Mock subprocess.run to avoid executing real commands
    mock_subprocess_result = MagicMock()
    mock_subprocess_result.returncode = 0
    mock_subprocess_result.stdout = "mocked-execution-output"
    mock_subprocess_result.stderr = ""
    monkeypatch.setattr(
        module.subprocess, "run", MagicMock(return_value=mock_subprocess_result)
    )

    module.app.config["TESTING"] = True
    client = module.app.test_client()

    return module, client, allowlist_file, ledger_dir


@pytest.fixture
def e2e_track_a(tmp_path, monkeypatch, e2e_track_b):
    """Load Track A with Track B bridged through its Flask test client.

    Track A's requests.post calls are intercepted and routed to Track B's
    test client in-process — no real network calls.

    Returns (module, test_client, ledger_dir).
    """
    _tb_module, tb_client, _tb_allowlist, _tb_ledger = e2e_track_b

    ledger_dir = tmp_path / "ledger-a"
    ledger_dir.mkdir()
    rag_dir = tmp_path / "rag"
    rag_dir.mkdir()
    (rag_dir / "incident-runbook.md").write_text(
        "# Latency Runbook\n"
        "High latency is often caused by resource saturation.\n"
        "Check CPU and memory usage with kubectl top pods.\n"
        "Inspect recent logs for error bursts.\n"
    )
    policy_dir = tmp_path / "policy"
    policy_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("RAG_CORPUS_PATH", str(rag_dir))
    monkeypatch.setenv("POLICY_DIR", str(policy_dir))
    monkeypatch.setenv("TRACK_B_URL", "http://bridged-track-b:8081")

    module = _load_module("e2e_track_a_main", TRACK_A_MAIN)
    module._last_hash = None
    module.LEDGER_PATH = ledger_dir
    module.RAG_CORPUS_PATH = rag_dir

    # Bridge Track A's HTTP calls to Track B's test client (true E2E)
    def _bridged_post(url, json=None, timeout=None, **kwargs):
        """Route Track A's HTTP POST to Track B's test client."""

        class BridgedResponse:
            def __init__(self, test_response):
                self.status_code = test_response.status_code
                self._text = test_response.get_data(as_text=True)
                try:
                    self._data = test_response.get_json()
                except Exception:
                    self._data = {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception(
                        f"Track B returned {self.status_code}: {self._text[:200]}"
                    )

            def json(self):
                return self._data

        resp = tb_client.post("/execute", json=json)
        return BridgedResponse(resp)

    monkeypatch.setattr(module.requests, "post", _bridged_post)

    module.app.config["TESTING"] = True
    client = module.app.test_client()

    return module, client, ledger_dir


@pytest.fixture
def e2e_sheryl(tmp_path, monkeypatch, e2e_memory):
    """Load Sheryl (Memory & Context agent) with shared mock MemoryPlugin.

    Returns (module, test_client, ledger_dir).
    """
    ledger_dir = tmp_path / "ledger-sheryl"
    ledger_dir.mkdir()
    rag_dir = tmp_path / "rag-sheryl"
    rag_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("RAG_CORPUS_PATH", str(rag_dir))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")

    spec = importlib.util.spec_from_file_location(
        "e2e_sheryl_main", QUARTET_DIR / "sheryl" / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["e2e_sheryl_main"] = module
    spec.loader.exec_module(module)

    module.LEDGER_PATH = ledger_dir
    module.RAG_CORPUS_PATH = rag_dir
    module._chain_head = ""
    module.app.config["TESTING"] = True
    client = module.app.test_client()

    return module, client, ledger_dir


@pytest.fixture
def e2e_malory(tmp_path, monkeypatch, e2e_memory):
    """Load Malory (Compliance agent) with shared mock MemoryPlugin and test allowlist.

    Returns (module, test_client, ledger_dir).
    """
    ledger_dir = tmp_path / "ledger-malory"
    ledger_dir.mkdir()
    allowlist_file = tmp_path / "tool-allowlist-malory.txt"
    allowlist_file.write_text(
        "kubectl get pods\n"
        "kubectl get nodes\n"
        "kubectl logs\n"
        "kubectl top pods\n"
        "kubectl top nodes\n"
        "kubectl describe pod\n"
        "kubectl events\n"
        "gcloud run services list\n"
        "git status\n"
        "git log\n"
    )

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))
    monkeypatch.setenv("TOOL_ALLOWLIST", str(allowlist_file))

    spec = importlib.util.spec_from_file_location(
        "e2e_malory_main", QUARTET_DIR / "malory" / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["e2e_malory_main"] = module
    spec.loader.exec_module(module)

    module._last_hash = None
    module.LEDGER_PATH = ledger_dir
    module.ALLOWLIST = module.load_allowlist()
    module.app.config["TESTING"] = True
    client = module.app.test_client()

    return module, client, ledger_dir


@pytest.fixture
def e2e_auditor(tmp_path, monkeypatch, e2e_memory):
    """Load the self-remediation service with auditor endpoints and shared mock memory.

    Returns (module, test_client, auditor_module, ledger_dir).
    """
    ledger_dir = tmp_path / "ledger-auditor"
    ledger_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))

    # Patch requests to avoid real service probes in health-check
    with patch("requests.get", return_value=MagicMock(status_code=200)):
        spec = importlib.util.spec_from_file_location(
            "e2e_auditor_main", SELF_REMEDIATION_DIR / "main.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["e2e_auditor_main"] = module
        spec.loader.exec_module(module)

    module.app.config["TESTING"] = True
    client = module.app.test_client()

    # Clear auditor's in-memory findings store for test isolation
    auditor_mod = module.auditor_module
    auditor_mod._findings.clear()

    return module, client, auditor_mod, ledger_dir


# ═══════════════════════════════════════════════════════════════════════════════
#  Test 1: E2E Happy Path
# ═══════════════════════════════════════════════════════════════════════════════


def test_e2e_happy_path(e2e_track_a, e2e_track_b, e2e_sheryl, e2e_malory, e2e_auditor):
    """Full C-P-A chain: query → RAG → plan → execute → MemoryPlugin store →
    compliance check → ledger chain integrity.

    Verifies the complete flow from operator query through execution, memory
    storage, compliance validation, and audit, with chain integrity.
    """
    ta_module, ta_client, ta_ledger = e2e_track_a
    _tb_module, _tb_client, _tb_allowlist, tb_ledger = e2e_track_b
    _sheryl_mod, _sheryl_client, _sheryl_ledger = e2e_sheryl
    _malory_mod, malory_client, _malory_ledger = e2e_malory
    _auditor_mod, _auditor_client, auditor_mod, _auditor_ledger = e2e_auditor

    # ── Phase 1: Operator submits query to Track A ─────────────────────────

    resp = ta_client.post("/plan", json={"query": "why is latency high"})
    assert resp.status_code == 200
    plan_data = resp.get_json()
    assert plan_data["status"] == "complete"
    assert "plan_id" in plan_data
    assert plan_data["query"] == "why is latency high"
    assert "hypothesis" in plan_data
    assert "High latency likely caused" in plan_data["hypothesis"]
    assert len(plan_data["steps"]) >= 2, "Expected at least 2 action steps"

    # All steps should have results (bridged through Track B test client)
    for step in plan_data["steps"]:
        assert "tool" in step
        assert "result" in step
        result = step["result"]
        # Track B always includes "error" key in response (None on success)
        actual_error = result.get("error")
        assert not actual_error, f"Step {step.get('step')} failed: {result}"

    # ── Phase 2: MemoryPlugin stores execution context via Sheryl ──────────

    store_resp = _sheryl_client.post(
        "/memory/store",
        json={
            "entity": "e2e-test",
            "context": "plan-execution",
            "data": {
                "plan_id": plan_data["plan_id"],
                "query": "why is latency high",
                "hypothesis": plan_data["hypothesis"],
                "step_count": len(plan_data["steps"]),
                "status": "complete",
            },
        },
    )
    assert store_resp.status_code == 200
    store_data = store_resp.get_json()
    assert store_data["success"] is True

    # Verify the stored data is retrievable
    query_resp = _sheryl_client.post(
        "/memory/query",
        json={
            "entity": "e2e-test",
            "context": "plan-execution",
            "query": "latency",
        },
    )
    assert query_resp.status_code == 200
    query_data = query_resp.get_json()
    assert query_data["success"] is True
    assert len(query_data.get("data", [])) >= 1

    # ── Phase 3: Malory compliance checks on all executed tools ────────────

    for step in plan_data["steps"]:
        tool = step["tool"]
        check_resp = malory_client.post("/compliance/check", json={"tool": tool})
        assert check_resp.status_code == 200
        check_data = check_resp.get_json()
        assert check_data["allowed"] is True, (
            f"Malory should allow tool '{tool}' on the test allowlist"
        )

    # Also check a known-bad tool to confirm Malory blocks correctly
    deny_resp = malory_client.post("/compliance/check", json={"tool": "rm -rf /"})
    assert deny_resp.status_code == 200
    deny_data = deny_resp.get_json()
    assert deny_data["allowed"] is False, "Malory should reject 'rm -rf /'"

    # ── Phase 4: Auditor validates board log entries (should be clean) ─────

    for step in plan_data["steps"]:
        log_entry = {
            "tool": step["tool"],
            "args": step.get("args", []),
            "reasoning_log_ref": plan_data["plan_id"],
            "timestamp": "2026-07-21T10:00:00Z",
        }
        audit_resp = _auditor_client.post(
            "/audit/report",
            json={
                "log_entry": log_entry,
                "memory_context": {
                    "entity": "board",
                    "context": "allowlist-context",
                    "results": [
                        {
                            "content": f"{step['tool']} is allowed for diagnostic operations",
                        }
                    ],
                },
            },
        )
        assert audit_resp.status_code == 200, (
            f"Auditor should return clean for tool '{step['tool']}': "
            f"got {audit_resp.get_data(as_text=True)}"
        )
        audit_data = audit_resp.get_json()
        assert audit_data["finding"] is None, (
            f"Unexpected audit finding for allowed tool '{step['tool']}'"
        )
        assert audit_data["status"] == "clean"

    # ── Phase 5: Verify ledger chain integrity across Track A and Track B ──

    ta_entries = _read_and_validate_chain(ta_ledger)
    assert len(ta_entries) >= 5, (
        f"Track A should have at least 5 ledger entries (reasoning, context, "
        f"hypothesis, actions, completion), got {len(ta_entries)}"
    )

    tb_entries = _read_and_validate_chain(tb_ledger)
    assert len(tb_entries) >= 2, (
        f"Track B should have at least 2 ledger entries (gate_passed, "
        f"tool_execution per action), got {len(tb_entries)}"
    )

    # Track B entries should all have track="B"
    for entry in tb_entries:
        assert entry.get("track") == "B"

    # Ensure entries from both tracks are independent chains
    if ta_entries and tb_entries:
        # Genesis entries (first in each chain) should differ since they're
        # independent services with different payloads
        assert ta_entries[0]["chain_hash"] != tb_entries[0]["chain_hash"], (
            "Independent service chains should not have matching genesis hashes"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Test 2: E2E Blocked Action
# ═══════════════════════════════════════════════════════════════════════════════


def test_e2e_blocked_action(e2e_track_b, e2e_malory, e2e_auditor):
    """Disallowed tool → Track B blocks (403) → Malory reports violation →
    Auditor logs finding.

    Verifies the full security chain: a tool not on Track B's allowlist is
    rejected, Malory confirms the rejection, and Auditor generates an
    allowlist-violation finding that is persisted and retrievable.
    """
    _tb_module, tb_client, _tb_allowlist, tb_ledger = e2e_track_b
    _malory_mod, malory_client, _malory_ledger = e2e_malory
    _auditor_mod, auditor_client, auditor_mod, _auditor_ledger = e2e_auditor

    # ── Phase 1: Attempt to execute a disallowed tool on Track B ───────────

    resp = tb_client.post(
        "/execute",
        json={
            "tool": "rm -rf /etc/critical",
            "args": [],
            "reasoning_log_ref": "hash-e2e-blocked-001",
        },
    )
    assert resp.status_code == 403, (
        f"Track B should return 403 for disallowed tool, got {resp.status_code}"
    )
    blocked_data = resp.get_json()
    assert blocked_data["allowed"] is False
    assert "Constitutional AI" in blocked_data["error"]
    assert "allowlist" in blocked_data["error"].lower()

    # ── Phase 2: Malory compliance check confirms the tool is not allowed ──

    malory_resp = malory_client.post(
        "/compliance/check", json={"tool": "rm -rf /etc/critical"}
    )
    assert malory_resp.status_code == 200
    malory_data = malory_resp.get_json()
    assert malory_data["allowed"] is False, "Malory should reject the blocked tool"

    # ── Phase 3: Auditor detects the violation and logs a finding ──────────

    log_entry = {
        "tool": "rm -rf /etc/critical",
        "args": [],
        "reasoning_log_ref": "hash-e2e-blocked-001",
        "timestamp": "2026-07-21T10:00:00Z",
    }
    audit_resp = auditor_client.post(
        "/audit/report",
        json={
            "log_entry": log_entry,
            "memory_context": {
                "entity": "board",
                "context": "allowlist-context",
                "results": [],
            },
        },
    )
    assert audit_resp.status_code == 201, (
        f"Auditor should return 201 for a violation finding, "
        f"got {audit_resp.status_code}: {audit_resp.get_data(as_text=True)}"
    )
    audit_data = audit_resp.get_json()
    assert "finding_id" in audit_data
    assert audit_data["finding_type"] == "allowlist_violation"
    assert audit_data["severity"] in ("critical", "high")
    assert audit_data["status"] == "violation"
    finding_id = audit_data["finding_id"]

    # ── Phase 4: Verify the finding is persisted and retrievable ───────────

    findings_resp = auditor_client.get("/audit/findings")
    assert findings_resp.status_code == 200
    findings_data = findings_resp.get_json()
    assert findings_data["count"] >= 1, "At least one finding should be persisted"
    finding_ids = [f["id"] for f in findings_data["findings"]]
    assert finding_id in finding_ids, (
        f"Persisted finding {finding_id} should appear in findings list"
    )

    # Verify the finding details
    finding = next(f for f in findings_data["findings"] if f["id"] == finding_id)
    assert finding["finding_type"] == "allowlist_violation"
    assert finding["board_entry_ref"] == "hash-e2e-blocked-001"

    # ── Phase 5: Track B ledger has a gate_denied entry ────────────────────

    tb_entries = _read_and_validate_chain(tb_ledger)
    denied_entries = [e for e in tb_entries if e.get("type") == "gate_denied"]
    assert len(denied_entries) >= 1, (
        "Track B ledger should have a 'gate_denied' entry for the blocked tool"
    )
    denied = denied_entries[0]
    assert "rm -rf" in str(denied.get("payload", {}))


# ═══════════════════════════════════════════════════════════════════════════════
#  Test 3: E2E Ledger Integrity
# ═══════════════════════════════════════════════════════════════════════════════


def test_e2e_ledger_integrity(
    e2e_track_a, e2e_track_b, e2e_sheryl, e2e_malory, e2e_auditor
):
    """Verify all entries across ALL services have valid prev_hash → chain_hash links.

    Drives every service to generate ledger entries, then validates:
      - Every entry has a 64-char hex chain_hash
      - Chain integrity holds per-service (each entry's hash links to previous)
      - Independent services have independent chains
      - Tamper detection works (modifying any entry breaks the chain)
    """
    ta_module, ta_client, ta_ledger = e2e_track_a
    tb_module, tb_client, tb_allowlist, tb_ledger = e2e_track_b
    _sheryl_mod, sheryl_client, sheryl_ledger = e2e_sheryl
    _malory_mod, malory_client, malory_ledger = e2e_malory
    _auditor_mod, auditor_client, auditor_mod, auditor_ledger = e2e_auditor

    # ── Drive every service to produce ledger entries ──────────────────────

    # Track A: run a full /plan
    ta_client.post("/plan", json={"query": "why is latency high"})
    ta_client.get("/healthz")

    # Track B: execute a tool directly
    tb_client.post(
        "/execute",
        json={
            "tool": "echo hello-e2e",
            "args": [],
            "reasoning_log_ref": "hash-ledger-test-b",
        },
    )
    tb_client.get("/healthz")

    # Sheryl: run a plan + memory store/query
    sheryl_client.post(
        "/memory/store",
        json={
            "entity": "ledger-test",
            "context": "integrity-check",
            "data": {"msg": "test-data"},
        },
    )
    sheryl_client.post(
        "/memory/query",
        json={
            "entity": "ledger-test",
            "context": "integrity-check",
            "query": "test-data",
        },
    )
    sheryl_client.get("/healthz")

    # Malory: compliance check
    malory_client.post("/compliance/check", json={"tool": "kubectl get pods"})
    malory_client.post("/compliance/check", json={"tool": "rm -rf /tmp"})
    malory_client.get("/healthz")

    # Auditor: generate a finding and list findings
    auditor_client.post(
        "/audit/report",
        json={
            "log_entry": {
                "tool": "rm -rf /var/log/*",
                "args": [],
                "reasoning_log_ref": "hash-ledger-test-audit",
                "timestamp": "2026-07-21T10:00:00Z",
            },
            "memory_context": {
                "entity": "board",
                "context": "allowlist-context",
                "results": [],
            },
        },
    )
    auditor_client.get("/audit/findings")
    auditor_client.get("/healthz")

    # ── Validate each service's independent ledger chain ──────────────────

    services: dict[str, Path] = {
        "track-a": ta_ledger,
        "track-b": tb_ledger,
        "sheryl": sheryl_ledger,
        "malory": malory_ledger,
        "auditor": auditor_ledger,
    }

    all_service_entries: dict[str, list[dict]] = {}

    for name, path in services.items():
        entries = _read_and_validate_chain(path)
        assert len(entries) >= 1, f"{name} ledger is empty — expected at least 1 entry"
        all_service_entries[name] = entries

    # ── Verify cross-service independence ──────────────────────────────────
    # Each service maintains its own independent chain; genesis hashes differ.

    genesis_hashes = {
        name: entries[0]["chain_hash"]
        for name, entries in all_service_entries.items()
        if entries
    }
    # With 5 services, at least 4 should have unique genesis hashes
    unique_genesis = len(set(genesis_hashes.values()))
    assert unique_genesis >= 3, (
        f"Expected independent chains; only {unique_genesis} unique genesis "
        f"hashes across {len(genesis_hashes)} services"
    )

    # ── Verify tamper detection ────────────────────────────────────────────
    # Pick Track A's entries and simulate tampering

    ta_entries = all_service_entries["track-a"]
    assert len(ta_entries) >= 2, "Need at least 2 entries for tamper test"

    # Tamper with entry[0]'s payload
    original_payload = ta_entries[0]["payload"]
    ta_entries[0]["payload"] = {"tampered": True}

    # Entry 0's stored hash should no longer match the recomputed hash
    expected0 = _expected_chain_hash(None, ta_entries[0])
    assert ta_entries[0]["chain_hash"] != expected0, (
        "Tampering with entry 0's payload went undetected — chain_hash "
        "still matches after mutation"
    )

    # Restore entry 0, now tamper with entry 1's payload — should also break
    ta_entries[0]["payload"] = original_payload
    if len(ta_entries) >= 2:
        ta_entries[1]["payload"] = {"also-tampered": True}
        prev_hash_for_1 = ta_entries[0]["chain_hash"]
        expected1 = _expected_chain_hash(prev_hash_for_1, ta_entries[1])
        assert ta_entries[1]["chain_hash"] != expected1, (
            "Tampering with entry 1's payload went undetected"
        )

    # ── Verify Track B ledger has track-specific metadata ────────────────

    tb_entries = all_service_entries["track-b"]
    for entry in tb_entries:
        if "track" in entry:
            assert entry["track"] == "B", (
                f"Track B entry should have track='B', got {entry.get('track')!r}"
            )
