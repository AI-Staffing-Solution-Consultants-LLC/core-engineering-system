#!/usr/bin/env python3
"""
Standalone test for tamper-evident ledger chain hash computation.

Verifies the chain hash spec across both Track A and Track B:
    chain_hash[n] == sha256(
        (prev_hash or "") + json.dumps(entry_without_chain_hash, sort_keys=True)
    )

Tests:
  1. Single entry hash matches spec (Track A and Track B)
  2. Chain integrity over N entries (Track A and Track B)
  3. Tamper detection breaks chain
  4. Track A and Track B chains are independent

Usage: python tests/ledger-chain-test.py
Exit 0 if all pass, non-zero if any fail.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helper script (written to a temp file, invoked via subprocess)
# ---------------------------------------------------------------------------
# Each subprocess gets a fresh Python interpreter, so `_last_hash` (module-
# level state in track-a/main.py and track-b/main.py) starts at None. This
# mirrors the real-world behavior where each Cloud Run instance has its own
# in-memory chain head.
HELPER_SCRIPT = (
    "import importlib.util\n"
    "import os\n"
    "import sys\n"
    "from pathlib import Path\n"
    "\n"
    "REPO_ROOT = Path(os.environ['REPO_ROOT'])\n"
    "track = sys.argv[1]\n"
    "ledger_path = Path(sys.argv[2])\n"
    "n = int(sys.argv[3])\n"
    "\n"
    "# Set LEDGER_PATH BEFORE importing the track module — the module calls\n"
    "# LEDGER_PATH.mkdir(parents=True, exist_ok=True) at import time.\n"
    "os.environ['LEDGER_PATH'] = str(ledger_path)\n"
    "\n"
    "module_name = f'track_{track}_helper'\n"
    "file_path = REPO_ROOT / f'track-{track}' / 'main.py'\n"
    "spec = importlib.util.spec_from_file_location(module_name, file_path)\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "sys.modules[module_name] = module\n"
    "spec.loader.exec_module(module)\n"
    "\n"
    "module.LEDGER_PATH = ledger_path\n"
    "module._last_hash = None\n"
    "\n"
    "for i in range(n):\n"
    "    module.write_ledger_entry(f'event_{i}', {'index': i, 'data': f'payload-{i}'})\n"
)


def write_helper_script(tmp_dir: Path) -> Path:
    """Write the helper script to a temp file. Returns the path."""
    helper = tmp_dir / "ledger_helper.py"
    helper.write_text(HELPER_SCRIPT)
    return helper


def run_track(track: str, ledger_path: Path, n: int, helper_path: Path) -> None:
    """Spawn a fresh Python process to write N entries for the given track."""
    env = os.environ.copy()
    env["REPO_ROOT"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, str(helper_path), track, str(ledger_path), str(n)],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  [ERROR] Helper failed for track {track} (exit {result.returncode}):")
        print(f"    stdout: {result.stdout.strip()}")
        print(f"    stderr: {result.stderr.strip()}")
        raise RuntimeError(f"Helper failed for track {track}")


# ---------------------------------------------------------------------------
# Chain hash spec (mirrors track-a/main.py and track-b/main.py)
# ---------------------------------------------------------------------------
def expected_chain_hash(prev_hash: str | None, entry: dict) -> str:
    """Compute the expected chain hash for an entry per the spec."""
    entry_without_hash = {k: v for k, v in entry.items() if k != "chain_hash"}
    payload = (prev_hash or "") + json.dumps(entry_without_hash, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_ledger(ledger_path: Path) -> list[dict]:
    """Read all entries from the most recent daily ledger file."""
    files = sorted(ledger_path.glob("ledger-*.jsonl"))
    if not files:
        return []
    lines = files[-1].read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines]


def verify_chain(entries: list[dict], label: str) -> bool:
    """Walk the chain and verify each entry's hash matches the spec."""
    if not entries:
        print(f"  FAIL [{label}]: No entries found in ledger")
        return False
    prev_hash = None
    for i, entry in enumerate(entries):
        expected = expected_chain_hash(prev_hash, entry)
        if entry["chain_hash"] != expected:
            print(f"  FAIL [{label}]: Entry {i} chain_hash mismatch")
            print(f"    got:      {entry['chain_hash']}")
            print(f"    expected: {expected}")
            return False
        prev_hash = entry["chain_hash"]
    print(f"  PASS [{label}]: {len(entries)} entries verified")
    return True


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------
def scenario_1_single_entry(tmp_path: Path, helper: Path) -> list[bool]:
    """Scenario 1: A single entry's chain_hash matches sha256(prev || json(entry, sort_keys))."""
    print("\n[Scenario 1] Single entry hash matches spec")
    results = []
    for track, label in [("a", "Track A"), ("b", "Track B")]:
        ledger = tmp_path / f"s1-{track}"
        ledger.mkdir()
        run_track(track, ledger, 1, helper)
        results.append(verify_chain(read_ledger(ledger), label))
    return results


def scenario_2_chain_integrity(tmp_path: Path, helper: Path) -> list[bool]:
    """Scenario 2: Chain integrity holds over N appends."""
    print("\n[Scenario 2] Chain integrity over N entries (N=5)")
    results = []
    for track, label in [("a", "Track A"), ("b", "Track B")]:
        ledger = tmp_path / f"s2-{track}"
        ledger.mkdir()
        run_track(track, ledger, 5, helper)
        results.append(verify_chain(read_ledger(ledger), label))
    return results


def scenario_3_tamper_detection(tmp_path: Path, helper: Path) -> bool:
    """Scenario 3: Tampering with an entry's payload invalidates its chain_hash."""
    print("\n[Scenario 3] Tamper detection breaks chain")
    ledger = tmp_path / "s3"
    ledger.mkdir()
    run_track("a", ledger, 3, helper)
    entries = read_ledger(ledger)
    if len(entries) < 2:
        print("  FAIL: Need at least 2 entries to test tamper detection")
        return False

    # Simulate tampering: mutate the first entry's payload in memory.
    entries[0]["payload"]["data"] = "tampered"

    # Walk the chain. The first entry's stored hash must no longer match.
    prev_hash = None
    for i, entry in enumerate(entries):
        expected = expected_chain_hash(prev_hash, entry)
        if i == 0:
            if entry["chain_hash"] == expected:
                print("  FAIL: Tampering went undetected — chain_hash still matches")
                return False
            print(f"  PASS: Tampering detected at entry 0 (hash mismatch)")
            return True
        prev_hash = entry["chain_hash"]
    return False


def scenario_4_independent_chains(tmp_path: Path, helper: Path) -> bool:
    """Scenario 4: Track A and Track B maintain independent chains."""
    print("\n[Scenario 4] Track A and Track B chains are independent")
    ledger_a = tmp_path / "s4-a"
    ledger_a.mkdir()
    ledger_b = tmp_path / "s4-b"
    ledger_b.mkdir()
    run_track("a", ledger_a, 1, helper)
    run_track("b", ledger_b, 1, helper)
    entries_a = read_ledger(ledger_a)
    entries_b = read_ledger(ledger_b)
    if not entries_a or not entries_b:
        print("  FAIL: Missing entries from one or both tracks")
        return False
    # Track B's entry includes a "track": "B" field that Track A's doesn't.
    # Even with identical payloads, the chain hashes must differ.
    if entries_a[0]["chain_hash"] == entries_b[0]["chain_hash"]:
        print("  FAIL: Track A and Track B produced identical chain hashes")
        return False
    print("  PASS: Track A and Track B produce different chain hashes")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    results: list[bool] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        helper_path = write_helper_script(tmp_path)

        results.extend(scenario_1_single_entry(tmp_path, helper_path))
        results.extend(scenario_2_chain_integrity(tmp_path, helper_path))
        results.append(scenario_3_tamper_detection(tmp_path, helper_path))
        results.append(scenario_4_independent_chains(tmp_path, helper_path))

    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")
    if passed == total:
        print("ALL TESTS PASSED")
        return 0
    print("SOME TESTS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
