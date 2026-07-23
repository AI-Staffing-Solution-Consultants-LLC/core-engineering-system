#!/usr/bin/env python3
"""
Standalone test for Track B allowlist mutation behavior.

Verifies that Track B's allowlist behaves correctly when the allowlist file
is mutated between process restarts. Since Track B loads the allowlist once
at module startup (via `load_allowlist()`), mutations to the file are only
picked up by a fresh process — not by the running process.

Scenarios tested:
  1. Adding an entry to the allowlist makes a previously-denied tool allowed.
  2. Removing an entry from the allowlist makes a previously-allowed tool denied.
  3. An empty allowlist denies all tools.
  4. The allowlist is loaded fresh per process (mutations between processes
     are picked up; mutations within a process are ignored — current behavior).

Usage:
    python tests/allowlist-mutation-test.py

Exit code:
    0 if all tests pass, 1 if any test fails.

This script does NOT use pytest. It is a standalone runner that spawns fresh
Python subprocesses for each allowlist state, because Track B's ALLOWLIST
global is populated once at module import time and is not re-read on mutation.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
TRACK_B_MAIN = REPO_ROOT / "track-b" / "main.py"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


# ---------------------------------------------------------------------------
# Subprocess harness
# ---------------------------------------------------------------------------
def _build_check_script(allowlist_path: str, tools: list[str]) -> str:
    """
    Build a Python one-liner that:
      1. Sets TOOL_ALLOWLIST env var to the given path.
      2. Loads track-b/main.py via importlib (hyphen in dir name).
      3. Calls load_allowlist() to populate the module's ALLOWLIST.
      4. Calls is_allowed() for each tool in `tools`.
      5. Prints results as JSON to stdout.
    """
    return (
        "import importlib.util, json, os, sys\n"
        f"os.environ['TOOL_ALLOWLIST'] = {allowlist_path!r}\n"
        f"os.environ['LEDGER_PATH'] = '/tmp/allowlist-mutation-test-ledger'\n"
        f"spec = importlib.util.spec_from_file_location('track_b_mut_test', {str(TRACK_B_MAIN)!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "sys.modules['track_b_mut_test'] = module\n"
        "spec.loader.exec_module(module)\n"
        "module.ALLOWLIST = module.load_allowlist()\n"
        f"tools = {tools!r}\n"
        "results = {tool: module.is_allowed(tool) for tool in tools}\n"
        "print(json.dumps({'allowlist_size': len(module.ALLOWLIST), 'results': results}))\n"
    )


def _run_subprocess(script: str) -> dict:
    """
    Run `script` in a fresh Python subprocess and return parsed JSON output.
    Uses the repo's .venv Python so Flask/requests are importable.
    """
    python_exe = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable
    proc = subprocess.run(
        [python_exe, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Subprocess failed (exit {proc.returncode}):\n"
            f"  stdout: {proc.stdout!r}\n"
            f"  stderr: {proc.stderr!r}"
        )
    return json.loads(proc.stdout.strip())


def check_allowlist(allowlist_content: str, tools: list[str]) -> dict:
    """
    Write `allowlist_content` to a temp file, spawn a fresh Python process
    that loads Track B with that allowlist, and return the is_allowed()
    results for each tool in `tools`.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(allowlist_content)
        allowlist_path = fh.name
    try:
        script = _build_check_script(allowlist_path, tools)
        return _run_subprocess(script)
    finally:
        os.unlink(allowlist_path)


def check_allowlist_at_path(allowlist_path: str, tools: list[str]) -> dict:
    """
    Like check_allowlist but uses an existing file path (for testing that
    a mutated file is picked up by a fresh process).
    """
    script = _build_check_script(allowlist_path, tools)
    return _run_subprocess(script)


# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------
def test_add_entry_makes_tool_allowed() -> bool:
    """
    Scenario 1: Adding an entry to the allowlist makes a previously-denied
    tool allowed.

    Process A: allowlist contains 'kubectl get pods' but NOT 'kubectl get nodes'.
      → 'kubectl get pods' should be allowed.
      → 'kubectl get nodes' should be denied.

    Process B: allowlist now also contains 'kubectl get nodes'.
      → 'kubectl get nodes' should be allowed.
    """
    print("\n=== Test 1: Add entry → previously-denied tool now allowed ===")

    tools = ["kubectl get pods", "kubectl get nodes", "kubectl get pods -A"]

    # Process A: no kubectl get nodes in allowlist
    content_a = "kubectl get pods\nkubectl logs\n"
    print(f"  Process A allowlist: {content_a.strip()!r}")
    result_a = check_allowlist(content_a, tools)
    print(f"  Process A results:   {result_a['results']}")

    if not result_a["results"]["kubectl get pods"]:
        print("  FAIL: 'kubectl get pods' should be allowed in Process A")
        return False
    if result_a["results"]["kubectl get nodes"]:
        print("  FAIL: 'kubectl get nodes' should be denied in Process A")
        return False
    # Prefix-match sanity check: 'kubectl get pods -A' should match 'kubectl get pods'
    if not result_a["results"]["kubectl get pods -A"]:
        print("  FAIL: 'kubectl get pods -A' should be allowed (prefix match)")
        return False

    # Process B: kubectl get nodes added to allowlist
    content_b = content_a + "kubectl get nodes\n"
    print(f"  Process B allowlist: {content_b.strip()!r}")
    result_b = check_allowlist(content_b, tools)
    print(f"  Process B results:   {result_b['results']}")

    if not result_b["results"]["kubectl get nodes"]:
        print("  FAIL: 'kubectl get nodes' should be allowed in Process B after add")
        return False

    print("  PASS: Adding entry made previously-denied tool allowed")
    return True


def test_remove_entry_makes_tool_denied() -> bool:
    """
    Scenario 2: Removing an entry from the allowlist makes a previously-allowed
    tool denied.

    Process A: allowlist contains both 'kubectl get pods' and 'kubectl get nodes'.
      → both should be allowed.

    Process B: 'kubectl get nodes' removed from allowlist.
      → 'kubectl get nodes' should now be denied.
    """
    print("\n=== Test 2: Remove entry → previously-allowed tool now denied ===")

    tools = ["kubectl get pods", "kubectl get nodes"]

    # Process A: both entries present
    content_a = "kubectl get pods\nkubectl get nodes\nkubectl logs\n"
    print(f"  Process A allowlist: {content_a.strip()!r}")
    result_a = check_allowlist(content_a, tools)
    print(f"  Process A results:   {result_a['results']}")

    if not result_a["results"]["kubectl get pods"]:
        print("  FAIL: 'kubectl get pods' should be allowed in Process A")
        return False
    if not result_a["results"]["kubectl get nodes"]:
        print("  FAIL: 'kubectl get nodes' should be allowed in Process A")
        return False

    # Process B: kubectl get nodes removed
    content_b = "kubectl get pods\nkubectl logs\n"
    print(f"  Process B allowlist: {content_b.strip()!r}")
    result_b = check_allowlist(content_b, tools)
    print(f"  Process B results:   {result_b['results']}")

    if result_b["results"]["kubectl get nodes"]:
        print("  FAIL: 'kubectl get nodes' should be denied in Process B after removal")
        return False
    if not result_b["results"]["kubectl get pods"]:
        print("  FAIL: 'kubectl get pods' should still be allowed in Process B")
        return False

    print("  PASS: Removing entry made previously-allowed tool denied")
    return True


def test_empty_allowlist_denies_all() -> bool:
    """
    Scenario 3: An empty allowlist denies all tools.

    Process with empty allowlist file:
      → allowlist_size should be 0.
      → every tool check should return False.
    """
    print("\n=== Test 3: Empty allowlist → all tools denied ===")

    tools = ["kubectl get pods", "git status", "docker ps", "anything-at-all"]
    print(f"  Allowlist: (empty)")
    result = check_allowlist("", tools)
    print(f"  Results: {result['results']}")

    if result["allowlist_size"] != 0:
        print(f"  FAIL: allowlist_size should be 0, got {result['allowlist_size']}")
        return False

    for tool in tools:
        if result["results"][tool]:
            print(f"  FAIL: '{tool}' should be denied with empty allowlist")
            return False

    print("  PASS: Empty allowlist denies all tools")
    return True


def test_allowlist_loaded_fresh_per_process() -> bool:
    """
    Scenario 4: The allowlist is loaded fresh per process.

    Uses a single persistent file path. Process A reads it with content X,
    then we mutate the file to content Y, then Process B reads it.
    Process B should see content Y (proving fresh load per process).

    This is the current behavior per AGENTS.md: "Track B loads allowlist once
    at startup via load_allowlist() — mutations to the file after startup
    are NOT picked up until restart."
    """
    print("\n=== Test 4: Allowlist loaded fresh per process ===")

    tools = ["kubectl get pods", "kubectl get nodes"]

    # Create a persistent file with initial content
    fd, persistent_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("kubectl get pods\n")
        print(f"  Persistent file: {persistent_path}")
        print(f"  Initial content: 'kubectl get pods'")

        # Process A: reads file with content 'kubectl get pods'
        result_a = check_allowlist_at_path(persistent_path, tools)
        print(f"  Process A results: {result_a['results']}")

        if not result_a["results"]["kubectl get pods"]:
            print("  FAIL: Process A should allow 'kubectl get pods'")
            return False
        if result_a["results"]["kubectl get nodes"]:
            print("  FAIL: Process A should deny 'kubectl get nodes'")
            return False

        # Mutate the file in-place
        with open(persistent_path, "w", encoding="utf-8") as fh:
            fh.write("kubectl get nodes\n")
        print(f"  Mutated content: 'kubectl get nodes'")

        # Process B: reads same file path, now with content 'kubectl get nodes'
        result_b = check_allowlist_at_path(persistent_path, tools)
        print(f"  Process B results: {result_b['results']}")

        if not result_b["results"]["kubectl get nodes"]:
            print("  FAIL: Process B should allow 'kubectl get nodes' (fresh load)")
            return False
        if result_b["results"]["kubectl get pods"]:
            print("  FAIL: Process B should deny 'kubectl get pods' (fresh load)")
            return False

        print(
            "  PASS: Allowlist is loaded fresh per process (no cross-process caching)"
        )
        return True
    finally:
        os.unlink(persistent_path)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 70)
    print("Track B Allowlist Mutation Test")
    print("=" * 70)
    print(f"Repo root:    {REPO_ROOT}")
    print(f"Track B main: {TRACK_B_MAIN}")
    print(f"Python:       {VENV_PYTHON if VENV_PYTHON.is_file() else sys.executable}")

    tests = [
        (
            "Add entry → previously-denied tool now allowed",
            test_add_entry_makes_tool_allowed,
        ),
        (
            "Remove entry → previously-allowed tool now denied",
            test_remove_entry_makes_tool_denied,
        ),
        ("Empty allowlist → all tools denied", test_empty_allowlist_denies_all),
        ("Allowlist loaded fresh per process", test_allowlist_loaded_fresh_per_process),
    ]

    results: list[tuple[str, bool]] = []
    for name, test_func in tests:
        try:
            passed = test_func()
        except Exception as exc:
            print(f"  ERROR: {type(exc).__name__}: {exc}")
            passed = False
        results.append((name, passed))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed_count = sum(1 for _, ok in results if ok)
    total_count = len(results)

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\n  {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n  ALL TESTS PASSED")
        return 0
    print(f"\n  {total_count - passed_count} TEST(S) FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
