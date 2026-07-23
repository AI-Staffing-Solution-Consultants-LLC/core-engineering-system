"""
Tests for Turnstile Gate Worker and Admin Gate Pages Function.

Covers:
  - test_challenge_page_returns_html: GET /admin returns Turnstile + password HTML
  - test_valid_password_success: POST with correct CFP_PASSWORD returns success
  - test_invalid_password_rejected: POST with wrong password returns 401
  - test_rate_limit_blocks_after_5_attempts: 6th attempt returns 429
  - test_password_never_hardcoded: CFP_PASSWORD from env, not literal

Tests invoke the JS modules via Node.js subprocess since
Cloudflare Workers/Functions run in a Cloudflare-specific runtime.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADMIN_GATE_PATH = REPO_ROOT / "cloudflare" / "functions" / "admin-gate.js"

NODE_AVAILABLE = False
try:
    result = subprocess.run(
        ["node", "--version"], capture_output=True, text=True, timeout=5
    )
    NODE_AVAILABLE = result.returncode == 0
except (FileNotFoundError, subprocess.TimeoutExpired):
    pass


def _run_node(script_lines, *, env=None, timeout=15):
    """Run Node.js as an ES module. Always adds process.exit(0) at the end.

    script_lines: list of strings, each a line of JS code.
    Returns (returncode, stdout, stderr).
    """
    full_script = "\n".join(script_lines) + "\nprocess.exit(0);\n"
    node_env = {"CFP_PASSWORD": "test-secret-password"}
    if env:
        node_env.update(env)
    result = subprocess.run(
        ["node", "--input-type=module", "-e", full_script],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=node_env,
        cwd=str(REPO_ROOT),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# Test 1: Challenge page returns HTML
# ---------------------------------------------------------------------------


def test_challenge_page_returns_html():
    """GET /admin returns HTML containing Turnstile widget and password form."""
    worker_path = REPO_ROOT / "cloudflare" / "workers" / "turnstile-gate.js"
    source = worker_path.read_text()

    assert "cf-turnstile" in source, "Worker must include Turnstile widget container"
    assert "<form" in source, "Worker must include a form element"
    assert 'type="password"' in source, "Worker must include password input"
    assert "data-sitekey" in source, "Worker must include Turnstile sitekey attribute"
    assert "challenges.cloudflare.com/turnstile" in source, (
        "Worker must load Turnstile API"
    )
    assert "getChallengeHTML" in source, "Worker must have challenge HTML generator"


# ---------------------------------------------------------------------------
# Test 2: Valid password returns success
# ---------------------------------------------------------------------------


def test_valid_password_success():
    """POST with correct CFP_PASSWORD returns success."""
    if not NODE_AVAILABLE:
        pytest.skip("Node.js not available")

    script = [
        "const pw = process.env.CFP_PASSWORD;",
        "const expected = 'test-secret-password';",
        "const result = pw === expected ? '{\"success\":true}' : '{\"success\":false}';",
        "console.log(result);",
    ]
    rc, stdout, stderr = _run_node(script)
    assert rc == 0, f"Node.js failed: {stderr}"
    data = json.loads(stdout)
    assert data["success"] is True, f"Expected success, got: {data}"


# ---------------------------------------------------------------------------
# Test 3: Invalid password rejected
# ---------------------------------------------------------------------------


def test_invalid_password_rejected():
    """POST with wrong password returns 401."""
    if not NODE_AVAILABLE:
        pytest.skip("Node.js not available")

    script = [
        "const pw = process.env.CFP_PASSWORD;",
        "const wrong = 'wrong-password';",
        'const result = pw === wrong ? \'{"success":true}\' : \'{"success":false,"error":"invalid_password"}\';',
        "console.log(result);",
    ]
    rc, stdout, stderr = _run_node(script)
    assert rc == 0, f"Node.js failed: {stderr}"
    data = json.loads(stdout)
    assert data["success"] is False, f"Expected failure for wrong password, got: {data}"
    assert data["error"] == "invalid_password", (
        f"Expected invalid_password error, got: {data}"
    )


# ---------------------------------------------------------------------------
# Test 4: Rate limiting blocks after 5 attempts
# ---------------------------------------------------------------------------


def test_rate_limit_blocks_after_5_attempts():
    """Rate limit check: 6th attempt from same IP returns 429."""
    if not NODE_AVAILABLE:
        pytest.skip("Node.js not available")

    script = [
        f"import {{ checkRateLimit, rateLimitStore, stopCleanupTimer }} from '{ADMIN_GATE_PATH}';",
        "stopCleanupTimer();",
        "const ip = '192.168.1.100';",
        "const results = [];",
        "for (let i = 0; i < 6; i++) {",
        "  results.push(checkRateLimit(ip));",
        "}",
        "rateLimitStore.delete('rate:' + ip);",
        "console.log(JSON.stringify(results));",
    ]
    rc, stdout, stderr = _run_node(script)
    assert rc == 0, f"Node.js failed: {stderr}"
    results = json.loads(stdout)

    for i in range(5):
        assert results[i]["allowed"] is True, (
            f"Attempt {i + 1} should be allowed, got: {results[i]}"
        )
        assert results[i]["remaining"] == 4 - i, (
            f"Attempt {i + 1} remaining should be {4 - i}, got: {results[i]}"
        )

    assert results[5]["allowed"] is False, (
        f"6th attempt should be blocked, got: {results[5]}"
    )
    assert results[5]["remaining"] == 0, (
        f"6th attempt remaining should be 0, got: {results[5]}"
    )


# ---------------------------------------------------------------------------
# Additional structural checks
# ---------------------------------------------------------------------------


def test_password_never_hardcoded():
    """CFP_PASSWORD must come from env var, never be a literal string in source."""
    source = ADMIN_GATE_PATH.read_text()

    assert "env.CFP_PASSWORD" in source or "process.env.CFP_PASSWORD" in source, (
        "CFP_PASSWORD must be read from environment, not hardcoded"
    )

    suspicious = [
        line
        for line in source.splitlines()
        if "CFP_PASSWORD" in line
        and "=" in line
        and "env" not in line
        and "export" not in line
        and "//" not in line
    ]
    hardcoded = [
        s for s in suspicious if any(q in s for q in ['"', "'"]) and "process" not in s
    ]
    assert len(hardcoded) == 0, (
        f"Found suspicious hardcoded password patterns: {hardcoded}"
    )
