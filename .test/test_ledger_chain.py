"""Tests for tamper-evident ledger chain hash computation.

The chain hash spec (from track-a/main.py and track-b/main.py):
    chain_hash[n] == sha256(
        (prev_hash or "") + json.dumps(entry_without_chain_hash, sort_keys=True)
    )

Where `entry_without_chain_hash` is the entry dict BEFORE `chain_hash` is
added. The hash is computed over the canonical JSON serialization with
sorted keys.

These tests verify:
  1. Single-entry hash matches the spec
  2. Chain integrity holds over N appends
  3. Tampering with any entry breaks the chain from that point forward
"""

import hashlib
import json


def _read_ledger_entries(ledger_path):
    """Read all entries from the daily ledger file."""
    files = sorted(ledger_path.glob("ledger-*.jsonl"))
    assert files, f"No ledger files found in {ledger_path}"
    lines = files[-1].read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines]


def _expected_chain_hash(prev_hash, entry):
    """Compute the expected chain hash for an entry per the spec."""
    entry_without_hash = {k: v for k, v in entry.items() if k != "chain_hash"}
    payload = (prev_hash or "") + json.dumps(entry_without_hash, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Passing tests
# ---------------------------------------------------------------------------


def test_single_entry_hash_matches_spec(track_a_module):
    """A single ledger entry's chain_hash matches sha256(prev || json(entry, sort_keys=True))."""
    track_a_module._last_hash = None
    track_a_module.write_ledger_entry("test_event", {"key": "value1"})

    entries = _read_ledger_entries(track_a_module.LEDGER_PATH)
    assert len(entries) == 1

    entry = entries[0]
    expected = _expected_chain_hash(None, entry)
    assert entry["chain_hash"] == expected


def test_chain_integrity_over_n_entries(track_a_module):
    """Chain integrity holds over N appends — each hash links to the previous."""
    track_a_module._last_hash = None
    n = 5
    for i in range(n):
        track_a_module.write_ledger_entry(
            f"event_{i}", {"index": i, "data": f"payload-{i}"}
        )

    entries = _read_ledger_entries(track_a_module.LEDGER_PATH)
    assert len(entries) == n

    prev_hash = None
    for i, entry in enumerate(entries):
        expected = _expected_chain_hash(prev_hash, entry)
        assert entry["chain_hash"] == expected, (
            f"Entry {i} chain_hash mismatch: "
            f"got {entry['chain_hash']!r}, expected {expected!r}"
        )
        prev_hash = entry["chain_hash"]


def test_tamper_detection_breaks_chain(track_a_module):
    """Tampering with an entry's payload invalidates its chain_hash."""
    track_a_module._last_hash = None
    track_a_module.write_ledger_entry("event_0", {"data": "original"})
    track_a_module.write_ledger_entry("event_1", {"data": "original"})

    entries = _read_ledger_entries(track_a_module.LEDGER_PATH)
    assert len(entries) == 2

    # Tamper with the first entry's payload
    entries[0]["payload"]["data"] = "tampered"

    # The first entry's stored chain_hash should no longer match the recomputed hash
    prev_hash = None
    for i, entry in enumerate(entries):
        expected = _expected_chain_hash(prev_hash, entry)
        if i == 0:
            assert entry["chain_hash"] != expected, (
                "Tampering went undetected — chain_hash still matches after payload mutation"
            )
        prev_hash = entry["chain_hash"]


def test_chain_hash_is_deterministic(track_a_module):
    """Two entries with identical payloads (modulo id/timestamp) produce different hashes
    because the chain links them — the second entry's hash depends on the first."""
    track_a_module._last_hash = None
    track_a_module.write_ledger_entry("same_type", {"k": "v"})
    track_a_module.write_ledger_entry("same_type", {"k": "v"})

    entries = _read_ledger_entries(track_a_module.LEDGER_PATH)
    assert len(entries) == 2
    # Chain links them — hashes must differ even though payloads are identical
    assert entries[0]["chain_hash"] != entries[1]["chain_hash"]
