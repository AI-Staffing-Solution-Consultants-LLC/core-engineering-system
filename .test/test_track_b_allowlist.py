"""Tests for Track B tool allowlist and Constitutional AI gate.

Covers the three gates in `constitutional_gate()`:
  1. Allowlist check (exact match OR prefix match with trailing space)
  2. Reasoning log reference required
  3. No shell metacharacters

The allowlist semantics from AGENTS.md:
  - `kubectl get pods` matches `kubectl get pods` and `kubectl get pods -A`
  - `kubectl get  pods` (double space) fails closed
  - `kubectl get podz` (typo) fails closed
"""

import pytest


# ---------------------------------------------------------------------------
# Gate 1 — Allowlist check
# ---------------------------------------------------------------------------


def test_exact_match_allowed(track_b_client):
    """Exact match against allowlist passes the gate."""
    resp = track_b_client.post(
        "/execute",
        json={
            "tool": "kubectl get pods",
            "args": [],
            "reasoning_log_ref": "test-ref-abc123",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["allowed"] is True
    assert data["tool"] == "kubectl get pods"


def test_prefix_match_allowed(track_b_client):
    """Prefix match (allowed + ' ') passes the gate."""
    resp = track_b_client.post(
        "/execute",
        json={
            "tool": "kubectl get pods -A",
            "args": [],
            "reasoning_log_ref": "test-ref-abc123",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["allowed"] is True


def test_typo_fails_closed(track_b_client):
    """Typo in tool name fails closed (HTTP 403)."""
    resp = track_b_client.post(
        "/execute",
        json={
            "tool": "kubectl get podz",  # typo: 'podz' instead of 'pods'
            "args": [],
            "reasoning_log_ref": "test-ref-abc123",
        },
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["allowed"] is False
    assert "allowlist" in data["error"].lower()


def test_double_space_fails_closed(track_b_client):
    """Double space between tokens fails closed (prefix match requires single space)."""
    resp = track_b_client.post(
        "/execute",
        json={
            "tool": "kubectl get  pods",  # double space
            "args": [],
            "reasoning_log_ref": "test-ref-abc123",
        },
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["allowed"] is False


# ---------------------------------------------------------------------------
# Gate 2 — Reasoning log reference required
# ---------------------------------------------------------------------------


def test_missing_reasoning_ref_blocked(track_b_client):
    """Missing reasoning_log_ref fails the gate (HTTP 403)."""
    resp = track_b_client.post(
        "/execute",
        json={
            "tool": "kubectl get pods",
            "args": [],
            "reasoning_log_ref": None,
        },
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["allowed"] is False
    assert "reasoning" in data["error"].lower()


# ---------------------------------------------------------------------------
# Gate 3 — No shell metacharacters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "metachar",
    ["|", ";", "&", "$(", "`", ">", "<", "${", "&&", "||"],
)
def test_metachar_blocked(track_b_client, metachar):
    """Each prohibited metacharacter fails the gate (HTTP 403)."""
    resp = track_b_client.post(
        "/execute",
        json={
            "tool": f"kubectl get pods {metachar} grep foo",
            "args": [],
            "reasoning_log_ref": "test-ref-abc123",
        },
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["allowed"] is False
    assert "metacharacter" in data["error"].lower()


# ---------------------------------------------------------------------------
# Audit endpoint
# ---------------------------------------------------------------------------


def test_allowlist_endpoint_returns_loaded_tools(track_b_client):
    """GET /allowlist returns the loaded allowlist."""
    resp = track_b_client.get("/allowlist")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "allowlist" in data
    assert isinstance(data["allowlist"], list)
    assert "kubectl get pods" in data["allowlist"]
    assert data["count"] == len(data["allowlist"])
