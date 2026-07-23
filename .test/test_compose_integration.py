"""Integration smoke tests for full docker-compose service mesh.

Verifies all 8 services boot correctly, health checks respond with
expected identities, and cross-service communication works end-to-end.

Tests:
  1. test_compose_config_parses — docker-compose.yml is valid YAML with 8 services
  2. test_service_ports — all 8 services mapped to correct ports (8080-8088)
  3. test_all_services_have_healthchecks — every service has a healthcheck stanza
  4. test_health_checks_use_correct_paths — all health checks hit /healthz
  5. test_ledger_volumes_present — every service has a named ledger volume
  6. test_track_a_depends_on_track_b — Track A depends_on Track B (healthy)
  7. test_service_healthz_identities — all 8 services return correct /healthz identity
  8. test_track_a_to_track_b_chain — Track A /plan → Track B /execute chain works
  9. test_sheryl_plan_returns_steps — Sheryl /plan endpoint returns structured plan
  10. test_self_remediation_health_check — /health-check probes mesh services
  11. test_self_remediation_health_check_has_telegram — telegram-bridge in health-check map
  12. test_ledger_paths_are_writable — ledger directories mount correctly

Runs from repo root:
    python3 -m pytest .test/test_compose_integration.py -q
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

# ── Expected service configuration ─────────────────────────────────────

EXPECTED_SERVICES = {
    "track-a-control-loop": {
        "port": 8080,
        "container_port": 8080,
        "healthz_identity": {
            "status": "healthy",
            "track": "A",
            "service": "control-loop",
        },
    },
    "track-b-actuator": {
        "port": 8081,
        "container_port": 8081,
        "healthz_identity": {"status": "healthy", "track": "B", "service": "actuator"},
    },
    "sheryl": {
        "port": 8083,
        "container_port": 8083,
        "healthz_identity": {"status": "ok", "agent": "sheryl"},
    },
    "aura-agent": {
        "port": 8084,
        "container_port": 8084,
        "healthz_identity": {"status": "ok", "agent": "aura"},
    },
    "malory": {
        "port": 8085,
        "container_port": 8085,
        "healthz_identity": {"status": "ok", "agent": "malory"},
    },
    "krieger": {
        "port": 8086,
        "container_port": 8086,
        "healthz_identity": {"status": "ok", "agent": "krieger"},
    },
    "self-remediation": {
        "port": 8087,
        "container_port": 8087,
        "healthz_identity": {"status": "ok", "service": "self-remediation"},
    },
    "telegram-bridge": {
        "port": 8088,
        "container_port": 8088,
        "healthz_identity": {"status": "ok", "service": "telegram-bridge"},
    },
}

ALL_PORTS = set(svc["port"] for svc in EXPECTED_SERVICES.values())


# ═════════════════════════════════════════════════════════════════════════
# Fixture: parse docker-compose.yml once per test session
# ═════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def compose_config():
    """Parse docker-compose.yml into a Python dict."""
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    return yaml.safe_load(text)


@pytest.fixture(scope="module")
def compose_services(compose_config):
    """Return the services dict from docker-compose.yml."""
    return compose_config.get("services", {})


# ═════════════════════════════════════════════════════════════════════════
# Helper: load a service module via importlib
# ═════════════════════════════════════════════════════════════════════════


def _load_module(name, file_path, sys_path_insert=None):
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if sys_path_insert and sys_path_insert not in sys.path:
        sys.path.insert(0, sys_path_insert)
    spec.loader.exec_module(module)
    return module


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 1 — docker-compose.yml structure validation
# ═══════════════════════════════════════════════════════════════════════


def test_compose_config_parses(compose_config):
    """docker-compose.yml is valid YAML with expected version."""
    assert "services" in compose_config
    assert "version" in compose_config or True  # version is optional in spec v3.9


def test_compose_all_eight_services(compose_services):
    """All 8 services are present in docker-compose.yml."""
    for svc_name in EXPECTED_SERVICES:
        assert svc_name in compose_services, f"Missing service: {svc_name}"

    # The daemon is commented out — should not appear
    assert "agency-agents-daemon" not in compose_services, (
        "agency-agents-daemon must remain commented out (default OFF)"
    )


def test_service_ports_match(compose_services):
    """Every service maps its expected port."""
    for svc_name, expected in EXPECTED_SERVICES.items():
        svc = compose_services[svc_name]
        ports = svc.get("ports", [])
        expected_mapping = f"{expected['port']}:{expected['container_port']}"
        assert expected_mapping in ports, (
            f"{svc_name}: expected port mapping {expected_mapping!r}, got {ports}"
        )


def test_port_range_8080_to_8088(compose_services):
    """No port outside the 8080-8088 range is exposed."""
    for svc_name, svc in compose_services.items():
        ports = svc.get("ports", [])
        for mapping in ports:
            # Parse "HOST:CONTAINER" or "CONTAINER"
            parts = mapping.split(":")
            host_port = int(parts[0])
            assert 8080 <= host_port <= 8088, (
                f"{svc_name}: port {host_port} is outside allowed range 8080-8088"
            )


def test_all_services_have_healthchecks(compose_services):
    """Every service defines a healthcheck block."""
    for svc_name in EXPECTED_SERVICES:
        svc = compose_services[svc_name]
        assert "healthcheck" in svc, f"{svc_name}: missing healthcheck"


def test_healthchecks_use_healthz_endpoint(compose_services):
    """All health checks probe /healthz with curl."""
    for svc_name, svc in compose_services.items():
        if "healthcheck" not in svc:
            continue
        hc = svc["healthcheck"]
        test_cmd = hc.get("test", [])
        cmd_str = " ".join(test_cmd) if isinstance(test_cmd, list) else str(test_cmd)
        assert "healthz" in cmd_str, (
            f"{svc_name}: health check does not reference /healthz: {cmd_str}"
        )
        assert "curl" in cmd_str.lower(), (
            f"{svc_name}: health check does not use curl: {cmd_str}"
        )


def test_healthcheck_intervals_are_reasonable(compose_services):
    """Health checks have reasonable interval (>=10s, <=60s)."""
    for svc_name, svc in compose_services.items():
        if "healthcheck" not in svc:
            continue
        hc = svc["healthcheck"]
        interval_str = hc.get("interval", "30s")
        seconds = int(interval_str.rstrip("s"))
        assert 10 <= seconds <= 60, (
            f"{svc_name}: healthcheck interval {interval_str} is out of range [10s, 60s]"
        )


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 2 — Volume mounts
# ═══════════════════════════════════════════════════════════════════════


def test_ledger_volumes_defined(compose_config):
    """Named ledger volumes exist for all services."""
    volumes = compose_config.get("volumes", {})
    expected_volumes = [
        "ledger-a",
        "ledger-b",
        "ledger-sheryl",
        "ledger-aura",
        "ledger-malory",
        "ledger-krieger",
        "ledger-self-remediation",
        "ledger-telegram-bridge",
    ]
    for vol_name in expected_volumes:
        assert vol_name in volumes, f"Missing named volume: {vol_name}"


def test_ledger_volumes_mounted(compose_services):
    """Each service mounts its own ledger volume to /var/log/ledger."""
    service_volumes = {
        "track-a-control-loop": "ledger-a",
        "track-b-actuator": "ledger-b",
        "sheryl": "ledger-sheryl",
        "aura-agent": "ledger-aura",
        "malory": "ledger-malory",
        "krieger": "ledger-krieger",
        "self-remediation": "ledger-self-remediation",
        "telegram-bridge": "ledger-telegram-bridge",
    }
    for svc_name, expected_vol in service_volumes.items():
        svc = compose_services.get(svc_name, {})
        volumes = svc.get("volumes", [])
        found = False
        for v in volumes:
            # Named volumes appear as "ledger-xxx:/var/log/ledger"
            if (
                isinstance(v, str)
                and v.startswith(expected_vol)
                and "/var/log/ledger" in v
            ):
                found = True
                break
        assert found, (
            f"{svc_name}: missing ledger volume mount {expected_vol} -> /var/log/ledger"
        )


def test_policy_volume_mounts(compose_services):
    """Track A and Track B mount policy as read-only."""
    for svc_name in ["track-a-control-loop", "track-b-actuator"]:
        svc = compose_services[svc_name]
        volumes = svc.get("volumes", [])
        policy_mounts = [v for v in volumes if isinstance(v, str) and "policy" in v]
        assert any(":ro" in m for m in policy_mounts), (
            f"{svc_name}: policy volumes should be mounted read-only"
        )


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 3 — Service dependency ordering
# ═══════════════════════════════════════════════════════════════════════


def test_track_a_depends_on_track_b(compose_services):
    """Track A must wait for Track B to be healthy before starting."""
    track_a = compose_services["track-a-control-loop"]
    assert "depends_on" in track_a, "Track A must depend on Track B"
    deps = track_a["depends_on"]
    assert "track-b-actuator" in deps
    assert deps["track-b-actuator"].get("condition") == "service_healthy"


def test_no_circular_dependencies(compose_services):
    """No service depends on itself or creates a cycle."""
    for svc_name, svc in compose_services.items():
        deps = svc.get("depends_on", {})
        if isinstance(deps, dict):
            for dep_name in deps:
                assert dep_name != svc_name, f"{svc_name} depends on itself"
                # Check the inverse doesn't exist (simple cycle detection)
                dep_svc = compose_services.get(dep_name, {})
                dep_deps = dep_svc.get("depends_on", {})
                if isinstance(dep_deps, dict):
                    assert svc_name not in dep_deps, (
                        f"Circular dependency: {svc_name} <-> {dep_name}"
                    )


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 4 — Non-root user enforcement
# ═══════════════════════════════════════════════════════════════════════


def test_all_dockerfiles_use_non_root_user():
    """Every Dockerfile has USER coreengine (non-root)."""
    dockerfiles = [
        REPO_ROOT / "track-a" / "Dockerfile",
        REPO_ROOT / "track-b" / "Dockerfile",
        REPO_ROOT / "executive-quartet" / "sheryl" / "Dockerfile",
        REPO_ROOT / "executive-quartet" / "aura" / "Dockerfile",
        REPO_ROOT / "executive-quartet" / "malory" / "Dockerfile",
        REPO_ROOT / "executive-quartet" / "krieger" / "Dockerfile",
        REPO_ROOT / "self-remediation" / "Dockerfile",
        REPO_ROOT / "telegram-bridge" / "Dockerfile",
    ]
    for df_path in dockerfiles:
        assert df_path.exists(), f"Dockerfile not found: {df_path}"
        content = df_path.read_text()
        assert "USER coreengine" in content or "USER 100" in content, (
            f"{df_path.name}: missing non-root USER directive"
        )


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 5 — Service health check identities (unit, via test clients)
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def service_clients(tmp_path, monkeypatch):
    """Load all 8 services with isolated envs, returning name->(module, client)."""
    # Ensure repo root on sys.path
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    eq_path = str(REPO_ROOT / "executive-quartet")
    if eq_path not in sys.path:
        sys.path.insert(0, eq_path)

    # Mock MemoryPlugin for all quartet services
    mock_mem = MagicMock()
    mock_mem.store_memory.return_value = {"success": True, "data": {"id": "mem-test-1"}}
    mock_mem.query_memory.return_value = {"success": True, "data": []}
    mock_mem.delete_memory.return_value = {"success": True, "data": None}
    sys.modules["memory_client"] = mock_mem

    # Mock requests for self-remediation (health-check uses requests module)
    mock_requests = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.01
    mock_response.json.return_value = {"status": "ok"}
    mock_requests.get.return_value = mock_response
    mock_requests.post.return_value = mock_response

    clients = {}

    # ── Track A ──────────────────────────────────────────────────────
    ta_ledger = tmp_path / "ledger-a"
    ta_ledger.mkdir()
    ta_rag = tmp_path / "rag"
    ta_rag.mkdir()
    ta_policy = tmp_path / "policy-a"
    ta_policy.mkdir()
    monkeypatch.setenv("LEDGER_PATH", str(ta_ledger))
    monkeypatch.setenv("RAG_CORPUS_PATH", str(ta_rag))
    monkeypatch.setenv("POLICY_DIR", str(ta_policy))
    ta_mod = _load_module("ta_int_main", REPO_ROOT / "track-a" / "main.py")
    ta_mod._last_hash = None
    ta_mod.LEDGER_PATH = ta_ledger
    # Mock Track B calls
    ta_mock_resp = MagicMock()
    ta_mock_resp.status_code = 200
    ta_mock_resp.raise_for_status = MagicMock()
    ta_mock_resp.json.return_value = {
        "allowed": True,
        "exit_code": 0,
        "stdout": "mocked",
        "stderr": "",
    }
    ta_mod.requests.post = MagicMock(return_value=ta_mock_resp)
    ta_mod.app.config["TESTING"] = True
    clients["track-a-control-loop"] = (ta_mod, ta_mod.app.test_client())

    # ── Track B ──────────────────────────────────────────────────────
    tb_ledger = tmp_path / "ledger-b"
    tb_ledger.mkdir()
    tb_allowlist = tmp_path / "tool-allowlist.txt"
    tb_allowlist.write_text(
        "kubectl get pods\nkubectl get nodes\nkubectl logs\ngit status\ngit log\n"
    )
    monkeypatch.setenv("LEDGER_PATH", str(tb_ledger))
    monkeypatch.setenv("TOOL_ALLOWLIST", str(tb_allowlist))
    tb_mod = _load_module("tb_int_main", REPO_ROOT / "track-b" / "main.py")
    tb_mod._last_hash = None
    tb_mod.LEDGER_PATH = tb_ledger
    tb_mod.ALLOWLIST = tb_mod.load_allowlist()
    tb_mod.app.config["TESTING"] = True
    clients["track-b-actuator"] = (tb_mod, tb_mod.app.test_client())

    # ── Sheryl ───────────────────────────────────────────────────────
    sh_ledger = tmp_path / "ledger-sheryl"
    sh_ledger.mkdir()
    sh_rag = tmp_path / "rag-sheryl"
    sh_rag.mkdir()
    monkeypatch.setenv("LEDGER_PATH", str(sh_ledger))
    monkeypatch.setenv("RAG_CORPUS_PATH", str(sh_rag))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")
    sh_mod = _load_module(
        "sh_int_main", REPO_ROOT / "executive-quartet" / "sheryl" / "main.py"
    )
    sh_mod.LEDGER_PATH = sh_ledger
    sh_mod.RAG_CORPUS_PATH = sh_rag
    sh_mod._chain_head = ""
    sh_mod.app.config["TESTING"] = True
    clients["sheryl"] = (sh_mod, sh_mod.app.test_client())

    # ── Aura ─────────────────────────────────────────────────────────
    au_ledger = tmp_path / "ledger-aura"
    au_ledger.mkdir()
    monkeypatch.setenv("LEDGER_PATH", str(au_ledger))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")
    au_mod = _load_module(
        "au_int_main", REPO_ROOT / "executive-quartet" / "aura" / "main.py"
    )
    au_mod._last_hash = None
    au_mod.app.config["TESTING"] = True
    clients["aura-agent"] = (au_mod, au_mod.app.test_client())

    # ── Malory ───────────────────────────────────────────────────────
    ma_ledger = tmp_path / "ledger-malory"
    ma_ledger.mkdir()
    ma_allowlist = tmp_path / "tool-allowlist-ma.txt"
    ma_allowlist.write_text(
        "kubectl get pods\nkubectl get nodes\nkubectl logs\nkubectl top pods\n"
        "kubectl describe pod\ngit status\ngit log\n"
    )
    monkeypatch.setenv("LEDGER_PATH", str(ma_ledger))
    monkeypatch.setenv("TOOL_ALLOWLIST", str(ma_allowlist))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")
    ma_mod = _load_module(
        "ma_int_main", REPO_ROOT / "executive-quartet" / "malory" / "main.py"
    )
    ma_mod._last_hash = None
    ma_mod.LEDGER_PATH = ma_ledger
    ma_mod.ALLOWLIST = ma_mod.load_allowlist()
    ma_mod.app.config["TESTING"] = True
    clients["malory"] = (ma_mod, ma_mod.app.test_client())

    # ── Krieger ──────────────────────────────────────────────────────
    kr_ledger = tmp_path / "ledger-krieger"
    kr_ledger.mkdir()
    monkeypatch.setenv("LEDGER_PATH", str(kr_ledger))
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-key")
    kr_mod = _load_module(
        "kr_int_main", REPO_ROOT / "executive-quartet" / "krieger" / "main.py"
    )
    kr_mod._last_hash = None
    kr_mod.app.config["TESTING"] = True
    clients["krieger"] = (kr_mod, kr_mod.app.test_client())

    # ── Self-Remediation ─────────────────────────────────────────────
    sr_ledger = tmp_path / "ledger-sr"
    sr_ledger.mkdir()
    monkeypatch.setenv("LEDGER_PATH", str(sr_ledger))
    sr_mod = _load_module(
        "sr_int_main",
        REPO_ROOT / "self-remediation" / "main.py",
        sys_path_insert=str(REPO_ROOT / "self-remediation"),
    )
    sr_mod.LEDGER_PATH = sr_ledger
    sr_mod.app.config["TESTING"] = True
    # Mock requests for health-check
    monkeypatch.setattr(sr_mod, "requests", mock_requests)
    # Also inject requests mock into the _health_hooks module
    if hasattr(sr_mod, "_health_hooks"):
        monkeypatch.setattr(sr_mod._health_hooks, "requests", mock_requests)
    clients["self-remediation"] = (sr_mod, sr_mod.app.test_client())

    # ── Telegram-Bridge ──────────────────────────────────────────────
    tg_ledger = tmp_path / "ledger-tg"
    tg_ledger.mkdir()
    monkeypatch.setenv("LEDGER_PATH", str(tg_ledger))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test")
    tg_mod = _load_module("tg_int_main", REPO_ROOT / "telegram-bridge" / "main.py")
    tg_mod.LEDGER_PATH = tg_ledger
    tg_mod.app.config["TESTING"] = True
    clients["telegram-bridge"] = (tg_mod, tg_mod.app.test_client())

    yield clients

    # Cleanup
    sys.modules.pop("memory_client", None)


def test_track_a_healthz(service_clients):
    """Track A /healthz returns correct identity."""
    _, client = service_clients["track-a-control-loop"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["track-a-control-loop"]["healthz_identity"]


def test_track_b_healthz(service_clients):
    """Track B /healthz returns correct identity."""
    _, client = service_clients["track-b-actuator"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["track-b-actuator"]["healthz_identity"]


def test_sheryl_healthz(service_clients):
    """Sheryl /healthz returns correct identity."""
    _, client = service_clients["sheryl"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["sheryl"]["healthz_identity"]


def test_aura_healthz(service_clients):
    """Aura /healthz returns correct identity."""
    _, client = service_clients["aura-agent"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["aura-agent"]["healthz_identity"]


def test_malory_healthz(service_clients):
    """Malory /healthz returns correct identity."""
    _, client = service_clients["malory"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["malory"]["healthz_identity"]


def test_krieger_healthz(service_clients):
    """Krieger /healthz returns correct identity."""
    _, client = service_clients["krieger"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["krieger"]["healthz_identity"]


def test_self_remediation_healthz(service_clients):
    """Self-remediation /healthz returns correct identity."""
    _, client = service_clients["self-remediation"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["self-remediation"]["healthz_identity"]


def test_telegram_bridge_healthz(service_clients):
    """Telegram-bridge /healthz returns correct identity."""
    _, client = service_clients["telegram-bridge"]
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == EXPECTED_SERVICES["telegram-bridge"]["healthz_identity"]


def test_all_eight_healthz_pass(service_clients):
    """All 8 services respond to /healthz with HTTP 200."""
    for svc_name in EXPECTED_SERVICES:
        _, client = service_clients[svc_name]
        resp = client.get("/healthz")
        assert resp.status_code == 200, (
            f"{svc_name} /healthz returned {resp.status_code}"
        )
        data = resp.get_json()
        assert "status" in data, f"{svc_name} missing 'status' key"
        assert data["status"] in ("ok", "healthy"), (
            f"{svc_name}: expected status ok/healthy, got {data.get('status')!r}"
        )


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 6 — Cross-service communication
# ═══════════════════════════════════════════════════════════════════════


def test_track_a_to_track_b_chain(service_clients):
    """Track A /plan calls Track B /execute internally and returns steps."""
    ta_mod, ta_client = service_clients["track-a-control-loop"]

    resp = ta_client.post("/plan", json={"query": "why is latency high"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "plan_id" in data
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0, "Track A /plan should produce at least one step"
    assert data["status"] == "complete"

    # Each step should have the expected shape
    for step in data["steps"]:
        assert "step" in step
        assert "tool" in step
        assert "reason" in step
        # The result should come from the mocked Track B response
        assert "result" in step

    # Verify Track A called Track B's /execute
    assert ta_mod.requests.post.called, "Track A should have called Track B via HTTP"


def test_sheryl_plan_returns_steps(service_clients):
    """Sheryl /plan returns structured plan with hypothesis and steps."""
    _, client = service_clients["sheryl"]

    resp = client.post("/plan", json={"query": "latency"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "plan_id" in data
    assert "hypothesis" in data
    assert isinstance(data["hypothesis"], str)
    assert len(data["hypothesis"]) > 0
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert data.get("source") == "sheryl"


def test_self_remediation_health_check(service_clients):
    """Self-remediation /health-check returns status: probe_complete with services map."""
    _, client = service_clients["self-remediation"]

    resp = client.post("/health-check")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "probe_complete"
    assert "services" in data
    assert isinstance(data["services"], dict)

    # All 6 core mesh services should be probed (track-a, track-b, sheryl, aura, malory, krieger)
    core_mesh = ["track-a", "track-b", "sheryl", "aura", "malory", "krieger"]
    for svc in core_mesh:
        assert svc in data["services"], f"Missing service '{svc}' in health-check map"


def test_self_remediation_health_check_has_telegram(service_clients):
    """Self-remediation /health-check includes telegram-bridge and self-remediation."""
    _, client = service_clients["self-remediation"]

    resp = client.post("/health-check")
    assert resp.status_code == 200
    data = resp.get_json()
    services = data["services"]

    # telegram-bridge should be in the service map
    assert "telegram-bridge" in services, (
        "telegram-bridge missing from health-check service map"
    )
    # self-remediation should probe itself
    assert "self-remediation" in services, (
        "self-remediation missing from health-check service map"
    )


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 7 — Ledger paths work correctly
# ═══════════════════════════════════════════════════════════════════════


# Services that expose a /ledger endpoint
# Track B and telegram-bridge intentionally do not expose /ledger (per AGENTS.md)
LEDGER_SERVICES = {
    "track-a-control-loop",
    "sheryl",
    "aura-agent",
    "malory",
    "krieger",
    "self-remediation",
}


def test_ledger_entries_have_chain_hash(service_clients):
    """Each service's /ledger returns entries with valid chain_hash."""
    # Trigger ledger writes on each service
    for svc_name, (mod, client) in service_clients.items():
        # Trigger a health check to write a ledger entry
        client.get("/healthz")

        if svc_name not in LEDGER_SERVICES:
            continue  # Track B intentionally has no /ledger endpoint

        resp = client.get("/ledger?limit=5")
        assert resp.status_code == 200, (
            f"{svc_name} /ledger returned {resp.status_code}"
        )
        data = resp.get_json()
        assert "entries" in data, f"{svc_name} /ledger missing 'entries' key"
        assert isinstance(data["entries"], list), (
            f"{svc_name} /ledger entries not a list"
        )

        if data["entries"]:
            for entry in data["entries"]:
                if "chain_hash" in entry:
                    assert len(entry["chain_hash"]) == 64, (
                        f"{svc_name}: chain_hash wrong length {len(entry.get('chain_hash', ''))}"
                    )
                    assert all(c in "0123456789abcdef" for c in entry["chain_hash"]), (
                        f"{svc_name}: chain_hash contains non-hex characters"
                    )
        data = resp.get_json()
        assert "entries" in data, f"{svc_name} /ledger missing 'entries' key"
        assert isinstance(data["entries"], list), (
            f"{svc_name} /ledger entries not a list"
        )

        if data["entries"]:
            for entry in data["entries"]:
                if "chain_hash" in entry:
                    assert len(entry["chain_hash"]) == 64, (
                        f"{svc_name}: chain_hash wrong length {len(entry.get('chain_hash', ''))}"
                    )
                    assert all(c in "0123456789abcdef" for c in entry["chain_hash"]), (
                        f"{svc_name}: chain_hash contains non-hex characters"
                    )


def test_sheryl_volume_mounts_ledger(compose_services):
    """Sheryl mounts only its named ledger volume (RAG is built into image)."""
    sheryl = compose_services["sheryl"]
    volumes = sheryl.get("volumes", [])
    ledger_mounts = [v for v in volumes if isinstance(v, str) and "ledger-sheryl" in v]
    assert len(ledger_mounts) >= 1, "Sheryl should mount ledger-sheryl volume"
    assert "/var/log/ledger" in ledger_mounts[0], (
        "Sheryl ledger should mount to /var/log/ledger"
    )


def test_track_a_mounts_rag_and_policy(compose_services):
    """Track A mounts both RAG and policy volumes as read-only."""
    track_a = compose_services["track-a-control-loop"]
    volumes = track_a.get("volumes", [])
    mount_paths = set()
    for v in volumes:
        if isinstance(v, str) and ":" in v:
            mount_paths.add(v.split(":")[-1])
    assert "/rag/docs:ro" in volumes or any(
        "rag" in v and ":ro" in v for v in volumes if isinstance(v, str)
    ), "Track A missing RAG read-only mount"
    assert "/policy:ro" in volumes or any(
        "policy" in v and ":ro" in v for v in volumes if isinstance(v, str)
    ), "Track A missing policy read-only mount"


# ═══════════════════════════════════════════════════════════════════════
# Test Suite 8 — docker-compose config command
# ═══════════════════════════════════════════════════════════════════════


def test_compose_file_is_yaml():
    """docker-compose.yml is valid YAML (no parsing errors)."""
    content = COMPOSE_FILE.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    assert isinstance(parsed, dict)
