"""
Health Hooks — Self-Remediation Probe/Detect/Trigger/Execute/Verify Loop.

Provides a complete automated remediation pipeline:
  1. probe_all_services()    — health-check all configured services
  2. detect_failure()        — identify failing services
  3. trigger_remediation()   — call Krieger /remediate to get a plan
  4. execute_remediation_plan() — run plan steps via self-remediation
  5. verify_remediation()    — re-probe to confirm health
  6. full_remediation_loop() — orchestrates the complete loop with logging
"""

import datetime
import json
import logging
import uuid
from pathlib import Path

import requests

logger = logging.getLogger("health_hooks")


# ── Probe ──────────────────────────────────────────────────────────────


def probe_all_services(services):
    """Health-check every configured service.

    Args:
        services: dict of {name: {url, timeout}}

    Returns:
        dict of {name: {healthy: bool, latency_ms: int|None, error: str|None}}
    """
    results = {}
    for name, config in services.items():
        try:
            resp = requests.get(config["url"], timeout=config.get("timeout", 5))
            latency_ms = int(resp.elapsed.total_seconds() * 1000)
            if resp.status_code == 200:
                results[name] = {
                    "healthy": True,
                    "latency_ms": latency_ms,
                    "error": None,
                }
            else:
                results[name] = {
                    "healthy": False,
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}",
                }
        except requests.exceptions.Timeout as exc:
            results[name] = {
                "healthy": False,
                "latency_ms": None,
                "error": str(exc),
            }
        except requests.exceptions.ConnectionError as exc:
            results[name] = {
                "healthy": False,
                "latency_ms": None,
                "error": str(exc),
            }
        except Exception as exc:
            results[name] = {
                "healthy": False,
                "latency_ms": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
    return results


# ── Detect ─────────────────────────────────────────────────────────────


def detect_failure(probe_results):
    """Identify failing services from probe results.

    Args:
        probe_results: dict from probe_all_services()

    Returns:
        list of {service: str, failure_reason: str, probe_result: dict}
    """
    failures = []
    for service, result in probe_results.items():
        if not result.get("healthy", False):
            failures.append(
                {
                    "service": service,
                    "failure_reason": result.get("error", "unknown"),
                    "probe_result": result,
                }
            )
    return failures


# ── Trigger ────────────────────────────────────────────────────────────


def trigger_remediation(failure, krieger_url="http://localhost:8086"):
    """Call Krieger /remediate to generate a remediation plan for a failing service.

    Args:
        failure: dict with {service, failure_reason, probe_result}
        krieger_url: base URL of the Krieger service

    Returns:
        dict: the remediation plan from Krieger (plan_id, steps, etc.)

    Raises:
        RuntimeError: if Krieger is unreachable or returns a non-200 status
    """
    incident_id = f"health-probe-{uuid.uuid4().hex[:8]}"
    title = f"Health probe failure: {failure['service']} ({failure['failure_reason']})"

    payload = {
        "incident_id": incident_id,
        "title": title,
        "severity": "high",
    }

    try:
        resp = requests.post(
            f"{krieger_url}/remediate",
            json=payload,
            timeout=10,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Krieger returned HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Krieger unreachable at {krieger_url}") from None
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Krieger timed out at {krieger_url}") from None


# ── Execute ────────────────────────────────────────────────────────────


def execute_remediation_plan(plan, execute_step_fn):
    """Execute each step in a remediation plan via the provided callback.

    Args:
        plan: dict with {plan_id, steps: [{action, priority}]}
        execute_step_fn: callable(step_dict) → None (or raises on failure)

    Returns:
        list of {action: str, success: bool, error: str|None}
    """
    results = []
    for step in plan.get("steps", []):
        try:
            execute_step_fn(step)
            results.append(
                {
                    "action": step["action"],
                    "success": True,
                    "error": None,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "action": step["action"],
                    "success": False,
                    "error": str(exc),
                }
            )
    return results


# ── Verify ─────────────────────────────────────────────────────────────


def verify_remediation(service_name, probe_fn):
    """Re-probe a service to confirm it is healthy after remediation.

    Args:
        service_name: name of the service to verify
        probe_fn: callable(service_name) → {healthy, latency_ms, error}

    Returns:
        {verified: bool, service: str, probe_result: dict}
    """
    probe_result = probe_fn(service_name)
    return {
        "verified": probe_result.get("healthy", False),
        "service": service_name,
        "probe_result": probe_result,
    }


# ── Helpers for full loop ─────────────────────────────────────────────


def _single_service_probe(services, service_name):
    """Probe a single service from the services config."""
    config = services.get(service_name)
    if not config:
        return {"healthy": False, "latency_ms": None, "error": "Service not in config"}
    return probe_all_services({service_name: config}).get(service_name)


def _write_remediation_log(log_dir, entry_type, payload):
    """Write a JSONL log entry for the remediation loop."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    log_file = log_path / f"remediation-{today}.jsonl"

    entry = {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "type": entry_type,
        "payload": payload,
    }
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _noop_execute(step):
    """Default no-op executor — logs but performs no real action.

    In production this is replaced by a function that actually
    executes remediation actions. Intentionally a no-op to prevent
    automatic remediation of critical services without approval.
    """
    logger.info("Remediation step (no-op): %s", step.get("action"))


# ── Full Loop ──────────────────────────────────────────────────────────


def full_remediation_loop(
    services, krieger_url="http://localhost:8086", log_dir=None, execute_step_fn=None
):
    """Run the complete remediation loop.

    pipeline: probe → detect → trigger → execute → verify → log

    Args:
        services: dict of {name: {url, timeout}} — services to monitor
        krieger_url: base URL of the Krieger incident remediation service
        log_dir: directory for remediation JSONL logs
        execute_step_fn: callable(step) to actually execute steps
                         (default is a safe no-op)

    Returns:
        dict summary: {
            status: "all_healthy" | "remediated" | "degraded",
            probe_count, failures_detected, remediations, errors
        }
    """
    if log_dir is None:
        log_dir = "./remediation-logs"
    if execute_step_fn is None:
        execute_step_fn = _noop_execute

    errors = []
    remediations = []

    # 1. Probe
    probe_results = probe_all_services(services)
    _write_remediation_log(
        log_dir,
        "probe_complete",
        {
            "results": {
                svc: {"healthy": r["healthy"], "latency_ms": r["latency_ms"]}
                for svc, r in probe_results.items()
            }
        },
    )

    # 2. Detect
    failures = detect_failure(probe_results)
    _write_remediation_log(
        log_dir,
        "failure_detect",
        {
            "count": len(failures),
            "services": [f["service"] for f in failures],
        },
    )

    if not failures:
        _write_remediation_log(
            log_dir,
            "loop_complete",
            {
                "status": "all_healthy",
                "probe_count": len(probe_results),
            },
        )
        return {
            "status": "all_healthy",
            "probe_count": len(probe_results),
            "failures_detected": 0,
            "remediations": [],
            "errors": [],
        }

    # 3-5. For each failure: trigger → execute → verify
    for failure in failures:
        service_name = failure["service"]
        try:
            # 3. Trigger
            plan = trigger_remediation(failure, krieger_url=krieger_url)
            _write_remediation_log(
                log_dir,
                "trigger_remediation",
                {
                    "service": service_name,
                    "plan_id": plan["plan_id"],
                    "steps": len(plan.get("steps", [])),
                },
            )

            # 4. Execute
            step_results = execute_remediation_plan(plan, execute_step_fn)
            _write_remediation_log(
                log_dir,
                "execute_complete",
                {
                    "service": service_name,
                    "plan_id": plan["plan_id"],
                    "step_results": step_results,
                },
            )

            # 5. Verify
            verification = verify_remediation(
                service_name,
                probe_fn=lambda svc: _single_service_probe(services, svc),
            )
            _write_remediation_log(
                log_dir,
                "verify_complete",
                {
                    "service": service_name,
                    "verified": verification["verified"],
                },
            )

            remediations.append(
                {
                    "service": service_name,
                    "plan_id": plan["plan_id"],
                    "plan": plan,
                    "step_results": step_results,
                    "verification": verification,
                }
            )
        except Exception as exc:
            errors.append(f"{service_name}: {exc}")
            _write_remediation_log(
                log_dir,
                "remediation_error",
                {
                    "service": service_name,
                    "error": str(exc),
                },
            )

    # Determine final status
    if errors and not remediations:
        final_status = "degraded"
    elif errors:
        final_status = "remediated"
    else:
        final_status = "remediated"

    _write_remediation_log(
        log_dir,
        "loop_complete",
        {
            "status": final_status,
            "probe_count": len(probe_results),
            "failures_detected": len(failures),
            "remediations": len(remediations),
            "errors": len(errors),
        },
    )

    return {
        "status": final_status,
        "probe_count": len(probe_results),
        "failures_detected": len(failures),
        "remediations": remediations,
        "errors": errors,
    }
