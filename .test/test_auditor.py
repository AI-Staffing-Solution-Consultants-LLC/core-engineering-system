"""TDD tests for Auditor Agent — co-located with self-remediation on port 8087.

Tests verify:
  1. validate_board_log — checks board log entries against MemoryPlugin context
  2. check_vcp — validates VCP entries for compliance
  3. POST /audit/report — generates audit findings and persists them
  4. GET /audit/findings — lists findings, including allowlist violation detection
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXECUTIVE_QUARTET = REPO_ROOT / "executive-quartet"
SELF_REMEDIATION = REPO_ROOT / "self-remediation"


# ---------------------------------------------------------------------------
#  Fixture: load self-remediation module with mocked memory_client
# ---------------------------------------------------------------------------


@pytest.fixture
def auditor_client(tmp_path):
    """Flask test client for self-remediation auditor with mocked MemoryPlugin and isolated ledger."""
    ledger_dir = tmp_path / "ledger-self-remediation"
    ledger_dir.mkdir()

    # Pre-mock the memory_client module so imports in auditor are intercepted.
    mock_store = MagicMock(
        return_value={"success": True, "data": {"id": "mock-mem-audit-1"}}
    )
    mock_query = MagicMock(
        return_value={
            "success": True,
            "data": [
                {
                    "id": "ctx-001",
                    "content": "kubectl get pods is allowed for namespace monitoring",
                    "entity": "board",
                    "context": "allowlist-context",
                    "created_at": "2026-07-21T00:00:00Z",
                }
            ],
        }
    )
    mock_delete = MagicMock(return_value={"success": True, "data": None})

    mock_mod = MagicMock()
    mock_mod.store_memory = mock_store
    mock_mod.query_memory = mock_query
    mock_mod.delete_memory = mock_delete
    sys.modules["memory_client"] = mock_mod

    # Ensure required directories are on sys.path:
    #   - repo root (for `from src.ledger import LedgerWriter`)
    #   - executive-quartet (for `from memory_client import ...`)
    #   - self-remediation (for `import auditor`)
    for path_str in (str(REPO_ROOT), str(EXECUTIVE_QUARTET), str(SELF_REMEDIATION)):
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    # Load self-remediation main module
    with patch.dict("os.environ", {"LEDGER_PATH": str(ledger_dir)}):
        spec = importlib.util.spec_from_file_location(
            "self_remediation_main",
            SELF_REMEDIATION / "main.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["self_remediation_main"] = module
        spec.loader.exec_module(module)

    module.app.config["TESTING"] = True
    client = module.app.test_client()

    yield client, mock_store, mock_query, module

    # Cleanup
    sys.modules.pop("memory_client", None)
    sys.modules.pop("self_remediation_main", None)
    for key in list(sys.modules):
        if key.startswith("auditor"):
            sys.modules.pop(key, None)


# ---------------------------------------------------------------------------
#  Test 1: Board log validation
# ---------------------------------------------------------------------------


class TestValidateBoardLog:
    """validate_board_log(log_entry, memory_context) → AuditFinding or None"""

    def test_clean_entry_returns_none(self, auditor_client):
        """A board log entry matching memory context returns None (no finding)."""
        _, _, mock_query, module = auditor_client

        memory_context = {
            "entity": "board",
            "context": "allowlist-context",
            "results": [
                {
                    "id": "ctx-001",
                    "content": "kubectl get pods is allowed for monitoring",
                    "entity": "board",
                    "context": "allowlist-context",
                }
            ],
        }
        log_entry = {
            "tool": "kubectl get pods",
            "args": ["-n", "monitoring"],
            "reasoning_log_ref": "hash-abc123",
            "timestamp": "2026-07-21T10:00:00Z",
        }

        result = module.auditor_module.validate_board_log(log_entry, memory_context)
        assert result is None

    def test_allowlist_violation_returns_finding(self, auditor_client):
        """A board log entry using a disallowed tool returns an AuditFinding."""
        _, _, _, module = auditor_client

        memory_context = {
            "entity": "board",
            "context": "allowlist-context",
            "results": [],
        }
        log_entry = {
            "tool": "rm -rf /tmp/*",
            "args": [],
            "reasoning_log_ref": "hash-dangerous",
            "timestamp": "2026-07-21T10:00:00Z",
        }

        result = module.auditor_module.validate_board_log(log_entry, memory_context)
        assert result is not None
        assert result.finding_type == "allowlist_violation"
        assert "rm -rf" in result.description

    def test_context_mismatch_returns_finding(self, auditor_client):
        """A board log entry that contradicts memory context returns an AuditFinding."""
        _, _, _, module = auditor_client

        memory_context = {
            "entity": "board",
            "context": "allowlist-context",
            "results": [
                {
                    "id": "ctx-002",
                    "content": "kubectl logs is restricted — requires human approval in production",
                    "entity": "board",
                    "context": "allowlist-context",
                }
            ],
        }
        log_entry = {
            "tool": "kubectl logs critical-app",
            "args": [],
            "reasoning_log_ref": "hash-logs",
            "timestamp": "2026-07-21T10:00:00Z",
        }

        result = module.auditor_module.validate_board_log(log_entry, memory_context)
        assert result is not None
        assert result.finding_type == "context_mismatch"


# ---------------------------------------------------------------------------
#  Test 2: VCP entry validation
# ---------------------------------------------------------------------------


class TestCheckVcp:
    """check_vcp(vcp_entry) → AuditFinding or None"""

    def test_valid_vcp_entry_returns_none(self, auditor_client):
        """A valid VCP entry with all required fields returns None."""
        _, _, _, module = auditor_client

        vcp_entry = {
            "vcp_id": "vcp-001",
            "action": "scale",
            "target": "deployment/nginx",
            "namespace": "production",
            "requested_by": "agent-krieger",
            "approved_by": "human-operator",
            "timestamp": "2026-07-21T10:00:00Z",
        }

        result = module.auditor_module.check_vcp(vcp_entry)
        assert result is None

    def test_missing_approved_by_returns_finding(self, auditor_client):
        """A VCP entry missing approved_by returns an AuditFinding."""
        _, _, _, module = auditor_client

        vcp_entry = {
            "vcp_id": "vcp-002",
            "action": "deploy",
            "target": "service/frontend",
            "namespace": "production",
            "requested_by": "agent-krieger",
            "approved_by": "",
            "timestamp": "2026-07-21T10:00:00Z",
        }

        result = module.auditor_module.check_vcp(vcp_entry)
        assert result is not None
        assert result.finding_type == "vcp_invalid"
        assert "approved_by" in result.description.lower()

    def test_missing_vcp_id_returns_finding(self, auditor_client):
        """A VCP entry missing vcp_id returns an AuditFinding."""
        _, _, _, module = auditor_client

        vcp_entry = {
            "vcp_id": "",
            "action": "restart",
            "target": "pod/app-1",
            "namespace": "staging",
            "requested_by": "agent-krieger",
            "approved_by": "human-operator",
            "timestamp": "2026-07-21T10:00:00Z",
        }

        result = module.auditor_module.check_vcp(vcp_entry)
        assert result is not None
        assert result.finding_type == "vcp_invalid"


# ---------------------------------------------------------------------------
#  Test 3: Audit report generation
# ---------------------------------------------------------------------------


class TestAuditReport:
    """POST /audit/report — generates and persists an audit finding."""

    def test_report_generates_finding(self, auditor_client):
        """POST /audit/report with a log entry and memory context returns a finding."""
        client, _, _, _ = auditor_client

        payload = {
            "log_entry": {
                "tool": "rm -rf /var/log/*",
                "args": [],
                "reasoning_log_ref": "hash-bad-1",
                "timestamp": "2026-07-21T10:00:00Z",
            },
            "memory_context": {
                "entity": "board",
                "context": "allowlist-context",
                "results": [],
            },
        }

        resp = client.post("/audit/report", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "finding_id" in data
        assert data["finding_type"] == "allowlist_violation"
        assert data["severity"] in ("low", "medium", "high", "critical")

    def test_report_clean_log_returns_no_finding(self, auditor_client):
        """POST /audit/report with a clean log entry returns 200 with no finding."""
        client, _, _, _ = auditor_client

        payload = {
            "log_entry": {
                "tool": "kubectl get pods",
                "args": ["-n", "monitoring"],
                "reasoning_log_ref": "hash-clean-1",
                "timestamp": "2026-07-21T10:00:00Z",
            },
            "memory_context": {
                "entity": "board",
                "context": "allowlist-context",
                "results": [
                    {
                        "id": "ctx-001",
                        "content": "kubectl get pods is allowed",
                    }
                ],
            },
        }

        resp = client.post("/audit/report", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["finding"] is None
        assert data["status"] == "clean"

    def test_report_vcp_entry_generates_finding(self, auditor_client):
        """POST /audit/report with a VCP entry validates and returns findings."""
        client, _, _, _ = auditor_client

        payload = {
            "vcp_entry": {
                "vcp_id": "",
                "action": "deploy",
                "target": "service/api",
                "namespace": "production",
                "requested_by": "agent-krieger",
                "approved_by": None,
                "timestamp": "2026-07-21T10:00:00Z",
            }
        }

        resp = client.post("/audit/report", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["finding_type"] == "vcp_invalid"

    def test_report_missing_payload_returns_400(self, auditor_client):
        """POST /audit/report with empty payload returns 400."""
        client, _, _, _ = auditor_client

        resp = client.post("/audit/report", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
#  Test 4: Findings listing and allowlist violation detection
# ---------------------------------------------------------------------------


class TestAuditFindings:
    """GET /audit/findings — lists all persisted audit findings."""

    def test_findings_endpoint_returns_list(self, auditor_client):
        """GET /audit/findings returns a list (empty for fresh state)."""
        client, _, _, _ = auditor_client

        resp = client.get("/audit/findings")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "findings" in data
        assert isinstance(data["findings"], list)
        assert "count" in data

    def test_findings_includes_reported_issues(self, auditor_client):
        """After submitting a report, GET /audit/findings includes it."""
        client, _, _, _ = auditor_client

        # Generate a finding first
        report_payload = {
            "log_entry": {
                "tool": "rm -rf /etc/*",
                "args": [],
                "reasoning_log_ref": "hash-finding-1",
                "timestamp": "2026-07-21T10:00:00Z",
            },
            "memory_context": {
                "entity": "board",
                "context": "allowlist-context",
                "results": [],
            },
        }
        report_resp = client.post("/audit/report", json=report_payload)
        assert report_resp.status_code == 201
        report_finding_id = report_resp.get_json()["finding_id"]

        # Retrieve findings
        findings_resp = client.get("/audit/findings")
        assert findings_resp.status_code == 200
        data = findings_resp.get_json()
        assert data["count"] >= 1
        finding_ids = [f["id"] for f in data["findings"]]
        assert report_finding_id in finding_ids

        # The finding should have allowlist_violation type
        finding = next(f for f in data["findings"] if f["id"] == report_finding_id)
        assert finding["finding_type"] == "allowlist_violation"

    def test_allowlist_violation_detection_in_board_log(self, auditor_client):
        """validate_board_log detects allowlist violations in a board log entry."""
        _, _, _, module = auditor_client

        # Simulate: the board log contains a tool NOT in the known-valid set
        memory_context = {
            "entity": "board",
            "context": "allowlist-context",
            "results": [
                {
                    "id": "ctx-003",
                    "content": "kubectl get pods, kubectl logs, git status are allowed",
                    "entity": "board",
                    "context": "allowlist-context",
                }
            ],
        }
        log_entry = {
            "tool": "rm -rf /tmp/critical",
            "args": [],
            "reasoning_log_ref": "hash-bad-2",
            "timestamp": "2026-07-21T10:00:00Z",
        }

        result = module.auditor_module.validate_board_log(log_entry, memory_context)
        assert result is not None
        assert result.finding_type == "allowlist_violation"
        assert result.severity == "critical"
        assert "allowlist" in result.description.lower()
