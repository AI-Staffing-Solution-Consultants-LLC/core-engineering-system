"""TDD tests for health-hooks — self-remediation probe/detect/trigger/execute/verify loop.

Tests verify:
  1. probe_all_services — returns health status for each service
  2. detect_failure — identifies failing services from probe results
  3. trigger_remediation — calls Krieger /remediate and returns plan
  4. execute_remediation_plan — executes plan steps via self-remediation
  5. verify_remediation — re-probes after remediation
  6. full_remediation_loop — end-to-end: probe → detect → trigger → execute → verify → log
"""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HEALTH_HOOKS_PATH = REPO_ROOT / "self-remediation" / "health-hooks.py"


def _load_health_hooks():
    """Load the health-hooks module via importlib (directory name has hyphen)."""
    module_name = "health_hooks_test"
    spec = importlib.util.spec_from_file_location(module_name, HEALTH_HOOKS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hh():
    """Provide the loaded health-hooks module."""
    mod = _load_health_hooks()
    yield mod
    sys.modules.pop("health_hooks_test", None)


# ── Test 1: probe_all_services ────────────────────────────────────────


class TestProbeAllServices:
    """Verify probe_all_services returns health status for each configured service."""

    def test_probe_returns_healthy_service(self, hh):
        """A healthy service returns {healthy: True, latency_ms, error: None}."""
        services = {
            "api-gateway": {"url": "http://api-gw:8080/healthz", "timeout": 5},
        }

        with patch.object(hh.requests, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.elapsed.total_seconds.return_value = 0.042
            mock_get.return_value = mock_resp

            results = hh.probe_all_services(services)

        assert "api-gateway" in results
        assert results["api-gateway"]["healthy"] is True
        assert results["api-gateway"]["latency_ms"] == 42
        assert results["api-gateway"]["error"] is None

    def test_probe_returns_unhealthy_service_on_timeout(self, hh):
        """A timed-out service returns {healthy: False, latency_ms: None, error: str}."""
        services = {
            "db-service": {"url": "http://db:8080/healthz", "timeout": 3},
        }

        import requests as real_requests

        with patch.object(hh.requests, "get") as mock_get:
            mock_get.side_effect = real_requests.exceptions.Timeout("timed out")
            results = hh.probe_all_services(services)

        assert "db-service" in results
        assert results["db-service"]["healthy"] is False
        assert results["db-service"]["latency_ms"] is None
        assert "timed out" in results["db-service"]["error"]

    def test_probe_returns_unhealthy_service_on_connection_error(self, hh):
        """A connection-refused service returns {healthy: False, error: str}."""
        services = {
            "cache": {"url": "http://cache:8080/healthz", "timeout": 5},
        }

        import requests as real_requests

        with patch.object(hh.requests, "get") as mock_get:
            mock_get.side_effect = real_requests.exceptions.ConnectionError(
                "Connection refused"
            )
            results = hh.probe_all_services(services)

        assert results["cache"]["healthy"] is False
        assert "Connection refused" in results["cache"]["error"]

    def test_probe_returns_unhealthy_on_non_200_status(self, hh):
        """A 503 response returns {healthy: False, latency_ms, error: 'HTTP 503'}."""
        services = {
            "worker": {"url": "http://worker:8080/healthz", "timeout": 5},
        }

        with patch.object(hh.requests, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_resp.elapsed.total_seconds.return_value = 0.15
            mock_get.return_value = mock_resp

            results = hh.probe_all_services(services)

        assert results["worker"]["healthy"] is False
        assert results["worker"]["latency_ms"] == 150
        assert "503" in results["worker"]["error"]

    def test_probe_multiple_services_mixed(self, hh):
        """Mixed results: one healthy, one unhealthy."""
        services = {
            "track-a": {"url": "http://track-a:8080/healthz", "timeout": 5},
            "track-b": {"url": "http://track-b:8081/healthz", "timeout": 5},
        }

        import requests as real_requests

        with patch.object(hh.requests, "get") as mock_get:

            def side_effect(url, timeout):
                if "track-b" in url:
                    raise real_requests.exceptions.Timeout("timed out")
                mock = MagicMock()
                mock.status_code = 200
                mock.elapsed.total_seconds.return_value = 0.01
                return mock

            mock_get.side_effect = side_effect
            results = hh.probe_all_services(services)

        assert results["track-a"]["healthy"] is True
        assert results["track-b"]["healthy"] is False
        assert len(results) == 2


# ── Test 2: detect_failure ────────────────────────────────────────────


class TestDetectFailure:
    """Verify detect_failure identifies failing services from probe results."""

    def test_detect_returns_empty_when_all_healthy(self, hh):
        """All healthy → empty list."""
        probe_results = {
            "svc-a": {"healthy": True, "latency_ms": 10, "error": None},
            "svc-b": {"healthy": True, "latency_ms": 20, "error": None},
        }

        failures = hh.detect_failure(probe_results)
        assert failures == []

    def test_detect_returns_failing_services(self, hh):
        """Some unhealthy → list of {service, failure_reason, probe_result}."""
        probe_results = {
            "svc-a": {"healthy": True, "latency_ms": 10, "error": None},
            "svc-b": {"healthy": False, "latency_ms": None, "error": "timeout"},
            "svc-c": {"healthy": False, "latency_ms": 500, "error": "HTTP 503"},
        }

        failures = hh.detect_failure(probe_results)

        assert len(failures) == 2
        failure_names = {f["service"] for f in failures}
        assert failure_names == {"svc-b", "svc-c"}

        svc_b = next(f for f in failures if f["service"] == "svc-b")
        assert svc_b["failure_reason"] == "timeout"
        assert svc_b["probe_result"]["healthy"] is False

        svc_c = next(f for f in failures if f["service"] == "svc-c")
        assert svc_c["failure_reason"] == "HTTP 503"

    def test_detect_handles_empty_probe_results(self, hh):
        """Empty probe results → empty list."""
        failures = hh.detect_failure({})
        assert failures == []


# ── Test 3: trigger_remediation ───────────────────────────────────────


class TestTriggerRemediation:
    """Verify trigger_remediation calls Krieger /remediate and returns plan."""

    def test_trigger_calls_krieger_and_returns_plan(self, hh):
        """Calls Krieger /remediate with correct payload, returns plan_id + steps."""
        failure = {
            "service": "api-gateway",
            "failure_reason": "timeout",
            "probe_result": {"healthy": False, "latency_ms": None, "error": "timeout"},
        }

        with patch.object(hh.requests, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "plan_id": "plan-abc123",
                "incident_id": "inc-001",
                "steps": [
                    {"action": "Acknowledge incident", "priority": "immediate"},
                    {"action": "Restart service", "priority": "high"},
                ],
                "status": "proposed",
            }
            mock_post.return_value = mock_resp

            plan = hh.trigger_remediation(failure, krieger_url="http://krieger:8086")

        assert plan["plan_id"] == "plan-abc123"
        assert len(plan["steps"]) == 2
        assert plan["steps"][0]["action"] == "Acknowledge incident"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://krieger:8086/remediate"
        payload = call_args[1]["json"]
        assert "incident_id" in payload
        assert payload["title"] == "Health probe failure: api-gateway (timeout)"
        assert payload["severity"] == "high"

    def test_trigger_raises_on_krieger_http_error(self, hh):
        """Raises RuntimeError when Krieger returns non-200."""
        failure = {
            "service": "db",
            "failure_reason": "HTTP 503",
            "probe_result": {"healthy": False, "latency_ms": 0, "error": "HTTP 503"},
        }

        with patch.object(hh.requests, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_post.return_value = mock_resp

            with pytest.raises(RuntimeError, match="Krieger returned HTTP 503"):
                hh.trigger_remediation(failure, krieger_url="http://krieger:8086")

    def test_trigger_raises_on_krieger_unreachable(self, hh):
        """Raises RuntimeError when Krieger is unreachable."""
        import requests as real_requests

        failure = {
            "service": "cache",
            "failure_reason": "timeout",
            "probe_result": {"healthy": False, "latency_ms": None, "error": "timeout"},
        }

        with patch.object(hh.requests, "post") as mock_post:
            mock_post.side_effect = real_requests.exceptions.ConnectionError(
                "Connection refused"
            )

            with pytest.raises(RuntimeError, match="Krieger unreachable"):
                hh.trigger_remediation(failure, krieger_url="http://krieger:8086")


# ── Test 4: execute_remediation_plan ──────────────────────────────────


class TestExecuteRemediationPlan:
    """Verify execute_remediation_plan executes each step via a callback."""

    def test_execute_runs_each_step_via_callback(self, hh):
        """Each step in the plan is passed to execute_step_fn."""
        plan = {
            "plan_id": "plan-xyz",
            "steps": [
                {"action": "Step 1", "priority": "high"},
                {"action": "Step 2", "priority": "medium"},
                {"action": "Step 3", "priority": "low"},
            ],
        }

        executed = []
        execute_step_fn = MagicMock(side_effect=lambda s: executed.append(s))

        results = hh.execute_remediation_plan(plan, execute_step_fn)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert results[0]["action"] == "Step 1"
        assert results[2]["action"] == "Step 3"
        assert execute_step_fn.call_count == 3

    def test_execute_handles_step_failure_gracefully(self, hh):
        """A failing step records success=False but continues."""
        plan = {
            "plan_id": "plan-xyz",
            "steps": [
                {"action": "Step 1", "priority": "high"},
                {"action": "Step 2", "priority": "medium"},
            ],
        }

        execute_step_fn = MagicMock(side_effect=[None, RuntimeError("step 2 failed")])

        results = hh.execute_remediation_plan(plan, execute_step_fn)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "step 2 failed" in results[1]["error"]

    def test_execute_empty_plan_returns_empty_list(self, hh):
        """An empty plan yields empty results."""
        plan = {"plan_id": "empty-plan", "steps": []}
        results = hh.execute_remediation_plan(plan, lambda s: None)
        assert results == []


# ── Test 5: verify_remediation ────────────────────────────────────────


class TestVerifyRemediation:
    """Verify verify_remediation re-probes a service and confirms health."""

    def test_verify_returns_true_when_service_healthy(self, hh):
        """Re-probe returns healthy → verification passes."""

        def mock_probe(service_name):
            return {"healthy": True, "latency_ms": 15, "error": None}

        result = hh.verify_remediation("api-gateway", probe_fn=mock_probe)
        assert result["verified"] is True
        assert result["service"] == "api-gateway"
        assert result["probe_result"]["healthy"] is True

    def test_verify_returns_false_when_service_still_unhealthy(self, hh):
        """Re-probe returns unhealthy → verification fails."""

        def mock_probe(service_name):
            return {"healthy": False, "latency_ms": None, "error": "still down"}

        result = hh.verify_remediation("db-service", probe_fn=mock_probe)
        assert result["verified"] is False
        assert result["probe_result"]["healthy"] is False
        assert "still down" == result["probe_result"]["error"]


# ── Test 6: full_remediation_loop ─────────────────────────────────────


class TestFullRemediationLoop:
    """End-to-end test: probe → detect → trigger → execute → verify → log."""

    def test_full_loop_all_healthy_skips_remediation(self, hh, tmp_path):
        """If all services are healthy, the loop logs success and returns."""
        services = {
            "svc-a": {"url": "http://a:8080/healthz", "timeout": 5},
            "svc-b": {"url": "http://b:8080/healthz", "timeout": 5},
        }

        log_path = tmp_path / "remediation.log"

        with patch.object(hh.requests, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.elapsed.total_seconds.return_value = 0.01
            mock_get.return_value = mock_resp

            result = hh.full_remediation_loop(
                services,
                krieger_url="http://krieger:8086",
                log_dir=str(log_path),
            )

        assert result["status"] == "all_healthy"
        assert result["probe_count"] == 2
        assert result["failures_detected"] == 0
        assert result["remediations"] == []

    def test_full_loop_detects_and_remediates_failing_service(self, hh, tmp_path):
        """One unhealthy service → detect → trigger → execute → verify."""
        services = {
            "track-a": {"url": "http://track-a:8080/healthz", "timeout": 5},
        }

        log_path = tmp_path / "remediation.log"

        import requests as real_requests

        with (
            patch.object(hh.requests, "get") as mock_probe_get,
            patch.object(hh.requests, "post") as mock_krieger_post,
        ):
            # First probe: unhealthy (timeout)
            mock_probe_get.side_effect = real_requests.exceptions.Timeout("timed out")

            # Krieger /remediate: returns a plan
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "plan_id": "plan-fix-001",
                "incident_id": "inc-001",
                "steps": [
                    {"action": "Restart pod", "priority": "high"},
                ],
                "status": "proposed",
            }
            mock_krieger_post.return_value = mock_resp

            result = hh.full_remediation_loop(
                services,
                krieger_url="http://krieger:8086",
                log_dir=str(log_path),
            )

        assert result["status"] == "remediated"
        assert result["failures_detected"] == 1
        assert len(result["remediations"]) == 1
        rem = result["remediations"][0]
        assert rem["service"] == "track-a"
        assert rem["plan_id"] == "plan-fix-001"

        # Verify log was written
        log_files = list(log_path.glob("remediation-*.jsonl"))
        assert len(log_files) == 1

        log_lines = log_files[0].read_text().strip().splitlines()
        assert len(log_lines) >= 3
        parsed = [json.loads(e) for e in log_lines]
        types = [e["type"] for e in parsed]
        assert "probe_complete" in types
        assert "trigger_remediation" in types
        assert "loop_complete" in types

    def test_full_loop_no_krieger_available_returns_error_status(self, hh, tmp_path):
        """When Krieger is unreachable, loop returns degraded status."""
        services = {
            "track-b": {"url": "http://track-b:8081/healthz", "timeout": 5},
        }

        log_path = tmp_path / "remediation.log"

        import requests as real_requests

        with (
            patch.object(hh.requests, "get") as mock_get,
            patch.object(hh.requests, "post") as mock_post,
        ):
            mock_get.side_effect = real_requests.exceptions.Timeout("timed out")
            mock_post.side_effect = real_requests.exceptions.ConnectionError(
                "Connection refused"
            )

            result = hh.full_remediation_loop(
                services,
                krieger_url="http://krieger:8086",
                log_dir=str(log_path),
            )

        assert result["status"] == "degraded"
        assert result["failures_detected"] == 1
        assert len(result["errors"]) > 0
