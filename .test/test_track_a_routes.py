"""Tests for Track A HTTP routes (control loop).

Covers:
  - GET /healthz returns 200 with healthy status
  - POST /plan returns expected response shape
  - POST /plan with missing query returns 400
  - POST /plan latency query triggers latency hypothesis

The 4 xfail tests below are placeholders for ReAct loop features that are
not yet implemented. They document the desired behavior and will flip to
passing once the ReAct loop gains those capabilities.
"""

import pytest


# ---------------------------------------------------------------------------
# Passing tests — current behavior
# ---------------------------------------------------------------------------


def test_healthz_returns_200(track_a_client):
    """GET /healthz returns HTTP 200."""
    resp = track_a_client.get("/healthz")
    assert resp.status_code == 200


def test_healthz_returns_track_a_identity(track_a_client):
    """GET /healthz identifies the service as Track A."""
    resp = track_a_client.get("/healthz")
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["track"] == "A"
    assert data["service"] == "control-loop"


def test_plan_returns_plan_structure(track_a_client):
    """POST /plan returns a plan with plan_id, steps, hypothesis, status."""
    resp = track_a_client.post(
        "/plan",
        json={"query": "why is latency high"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "plan_id" in data
    assert isinstance(data["plan_id"], str)
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0
    assert "hypothesis" in data
    assert isinstance(data["hypothesis"], str)
    assert data["status"] == "complete"


def test_plan_missing_query_returns_400(track_a_client):
    """POST /plan with missing query returns HTTP 400."""
    resp = track_a_client.post("/plan", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_plan_latency_hypothesis(track_a_client):
    """POST /plan with latency query returns a latency-related hypothesis."""
    resp = track_a_client.post(
        "/plan",
        json={"query": "why is latency high"},
    )
    data = resp.get_json()
    assert "latency" in data["hypothesis"].lower()


# ---------------------------------------------------------------------------
# xfail placeholders — ReAct loop features not yet implemented
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="ReAct loop does not include a pre-validation step before emitting tools to Track B",
    strict=True,
)
def test_plan_pre_validates_tools_against_allowlist(track_a_client):
    """Track A should include a pre-validation step before executing tools."""
    resp = track_a_client.post(
        "/plan",
        json={"query": "why is latency high"},
    )
    data = resp.get_json()
    # Plan should include a step whose reason mentions validation (not implemented today)
    assert any("validat" in step.get("reason", "").lower() for step in data["steps"]), (
        "Plan has no pre-validation step"
    )


@pytest.mark.xfail(
    reason="ReAct loop does not retry failed steps",
    strict=True,
)
def test_plan_retries_failed_steps(track_a_client):
    """Track A should retry steps that fail on Track B."""
    resp = track_a_client.post(
        "/plan",
        json={"query": "why is latency high"},
    )
    data = resp.get_json()
    # Steps should carry a retry_count field (not implemented today)
    for step in data["steps"]:
        assert "retry_count" in step
        assert step["retry_count"] >= 0


@pytest.mark.xfail(
    reason="ReAct loop writes plan_adjustment ledger entries but does not mutate the hypothesis",
    strict=True,
)
def test_plan_adjusts_hypothesis_on_step_failure(track_a_client):
    """Track A should revise the hypothesis when a step fails."""
    resp = track_a_client.post(
        "/plan",
        json={"query": "why is latency high"},
    )
    data = resp.get_json()
    # Plan should expose hypothesis revisions (not implemented today)
    assert "hypothesis_revisions" in data
    assert isinstance(data["hypothesis_revisions"], list)


@pytest.mark.xfail(
    reason="Plan response does not include the full reasoning chain (only steps)",
    strict=True,
)
def test_plan_includes_full_reasoning_chain(track_a_client):
    """Plan response should include the full reasoning chain, not just steps."""
    resp = track_a_client.post(
        "/plan",
        json={"query": "why is latency high"},
    )
    data = resp.get_json()
    # Plan should expose the reasoning chain (not implemented today)
    assert "reasoning_chain" in data
    assert isinstance(data["reasoning_chain"], list)
    assert len(data["reasoning_chain"]) > 0
