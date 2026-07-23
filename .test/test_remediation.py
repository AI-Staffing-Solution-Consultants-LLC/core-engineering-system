"""Tests for self-remediation service (port 8087).

Covers:
  - GET /healthz returns {"status":"ok","service":"self-remediation"}
  - POST /remediate accepts a plan from Krieger, executes via OpenCode stub
  - POST /health-check probes all mesh services and returns status map
  - GET /ledger returns tamper-evident entries with chain_hash field
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


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def remediation_module(tmp_path, monkeypatch):
    """Load self-remediation with isolated LEDGER_PATH and mocked mesh services."""
    ledger_dir = tmp_path / "ledger-remediation"
    ledger_dir.mkdir()

    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))

    # self-remediation/main.py uses bare `import auditor` — the module needs
    # its own directory on sys.path for local imports
    sr_dir = str(REPO_ROOT / "self-remediation")
    if sr_dir not in sys.path:
        sys.path.insert(0, sr_dir)

    module = _load_module(
        "remediation_test_main",
        REPO_ROOT / "self-remediation" / "main.py",
    )
    module.LEDGER_PATH = ledger_dir

    # Inject a mock requests module so health-check never hits real mesh services
    from unittest.mock import MagicMock

    mock_requests = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "healthy"}
    mock_requests.get.return_value = mock_response
    mock_requests.post.return_value = mock_response
    monkeypatch.setattr(module, "requests", mock_requests)
    module.mock_requests = mock_requests

    # Pre-load health-hooks with the mocked requests so probe_all_services works
    module._health_hooks_requests = mock_requests

    return module


@pytest.fixture
def remediation_client(remediation_module):
    """Flask test client for self-remediation service."""
    remediation_module.app.config["TESTING"] = True
    return remediation_module.app.test_client()


# ═══════════════════════════════════════════════════════════════════════
# Test 1 — Health Check
# ═══════════════════════════════════════════════════════════════════════


def test_healthz_returns_ok(remediation_client):
    """GET /healthz returns HTTP 200 with the expected identity."""
    resp = remediation_client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "self-remediation"


# ═══════════════════════════════════════════════════════════════════════
# Test 2 — Remediate Endpoint
# ═══════════════════════════════════════════════════════════════════════


def test_remediate_endpoint_accepts_plan(remediation_client):
    """POST /remediate receives a plan from Krieger and returns execution result."""
    payload = {
        "plan_id": "plan-abc123",
        "steps": [
            {"action": "kubectl get pods", "priority": "immediate"},
            {"action": "kubectl logs --tail=100", "priority": "high"},
        ],
        "reasoning_log_ref": "hash-abc123",
    }
    resp = remediation_client.post("/remediate", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["plan_id"] == "plan-abc123"
    assert data["status"] == "executed"
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 2


def test_remediate_missing_plan_id_returns_400(remediation_client):
    """POST /remediate with missing plan_id returns HTTP 400."""
    resp = remediation_client.post("/remediate", json={"steps": []})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


# ═══════════════════════════════════════════════════════════════════════
# Test 3 — Health Check Mesh Probe
# ═══════════════════════════════════════════════════════════════════════


def test_health_check_probes_mesh(remediation_client, remediation_module):
    """POST /health-check probes all mesh services and returns status map."""
    resp = remediation_client.post("/health-check")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "probe_complete"
    assert "services" in data
    assert isinstance(data["services"], dict)

    # All standard mesh services should be probed
    expected_services = [
        "track-a",
        "track-b",
        "sheryl",
        "aura",
        "malory",
        "krieger",
    ]
    for svc in expected_services:
        assert svc in data["services"], f"Missing service: {svc}"
        assert data["services"][svc] in ("healthy", "unreachable")

    # Verify the mock was called for each service
    assert remediation_module.mock_requests.get.call_count >= len(expected_services)


# ═══════════════════════════════════════════════════════════════════════
# Test 4 — Ledger
# ═══════════════════════════════════════════════════════════════════════


def test_ledger_returns_chain_hash(remediation_client):
    """GET /ledger returns entries with chain_hash field (tamper-evidence)."""
    # First do a /remediate to generate ledger entries
    remediation_client.post(
        "/remediate",
        json={
            "plan_id": "plan-ledger-test",
            "steps": [{"action": "echo hello", "priority": "low"}],
            "reasoning_log_ref": "hash-ledger",
        },
    )

    resp = remediation_client.get("/ledger?limit=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) > 0

    # Every entry must carry a chain_hash for tamper-evidence
    for entry in data["entries"]:
        assert "chain_hash" in entry, f"Entry missing chain_hash: {entry}"
        assert isinstance(entry["chain_hash"], str)
        assert len(entry["chain_hash"]) == 64
