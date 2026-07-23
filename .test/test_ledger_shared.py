"""Tests for src/ledger.py: LedgerWriter class — SHA-256 chained JSONL ledger.

Tests verify:
  1. single_write — one entry, 64-char hex chain_hash, file present
  2. chain_integrity — 3-entry chain, each hash links to previous
  3. daily_rotation — entries on different dates → separate daily files
  4. concurrent_writes — 10 threads, all entries preserved, no corruption
  5. default_path — LEDGER_PATH unset → /tmp/ledger
  6. format_matches_existing — entry keys: type, timestamp, data, prev_hash, chain_hash
"""

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────


def _expected_chain_hash(prev_hash: str, entry: dict) -> str:
    """Compute expected chain_hash per the spec:
    sha256((prev_hash + json.dumps(entry_without_chain_hash, sort_keys=True)).encode()).hexdigest()
    """
    entry_without_hash = {k: v for k, v in entry.items() if k != "chain_hash"}
    payload = prev_hash + json.dumps(entry_without_hash, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_entries(ledger_path: Path) -> list[dict]:
    """Read all JSONL entries from all daily ledger files, sorted by filename."""
    entries: list[dict] = []
    for f in sorted(ledger_path.glob("ledger-*.jsonl")):
        for line in f.read_text("utf-8").strip().splitlines():
            if line:
                entries.append(json.loads(line))
    return entries


# ── tests ────────────────────────────────────────────────────────────────────


def test_single_write(tmp_path):
    """A single write() returns a 64-char hex chain_hash and writes one JSONL line."""
    from src.ledger import LedgerWriter

    writer = LedgerWriter(ledger_path=tmp_path)
    h = writer.write("test_event", {"key": "value"}, "seed00")

    # 64 hex chars
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)

    entries = _read_entries(tmp_path)
    assert len(entries) == 1

    e = entries[0]
    assert e["type"] == "test_event"
    assert e["data"] == {"key": "value"}
    assert e["prev_hash"] == "seed00"
    assert e["chain_hash"] == h
    assert isinstance(e["timestamp"], str)

    # Hash must match the spec
    assert _expected_chain_hash("seed00", e) == h


def test_chain_integrity(tmp_path):
    """Three sequential writes produce a linked chain where each hash depends on the previous."""
    from src.ledger import LedgerWriter

    writer = LedgerWriter(ledger_path=tmp_path)

    h1 = writer.write("e1", {"n": 1}, "")
    h2 = writer.write("e2", {"n": 2}, h1)
    h3 = writer.write("e3", {"n": 3}, h2)

    # Hashes must differ
    assert len({h1, h2, h3}) == 3

    entries = _read_entries(tmp_path)
    assert len(entries) == 3

    prev_hash = ""
    for i, e in enumerate(entries):
        assert e["prev_hash"] == prev_hash, (
            f"Entry {i}: expected prev_hash={prev_hash!r}, got {e['prev_hash']!r}"
        )
        expected = _expected_chain_hash(prev_hash, e)
        assert e["chain_hash"] == expected, f"Entry {i} chain_hash mismatch"
        prev_hash = e["chain_hash"]


def test_daily_rotation(tmp_path, monkeypatch):
    """Entries on different calendar dates land in different daily files."""
    from src.ledger import LedgerWriter

    # Two datetime.now() calls per write() (timestamp + file date-string).
    # Provide enough calls for 5 writes on 3 different days.
    dates = iter(
        [
            datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),  # w0 ts
            datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),  # w0 file
            datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc),  # w1 ts
            datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc),  # w1 file
            datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc),  # w2 ts
            datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc),  # w2 file
            datetime(2026, 1, 2, 13, 0, 0, tzinfo=timezone.utc),  # w3 ts
            datetime(2026, 1, 2, 13, 0, 0, tzinfo=timezone.utc),  # w3 file
            datetime(2026, 1, 3, 12, 0, 0, tzinfo=timezone.utc),  # w4 ts
            datetime(2026, 1, 3, 12, 0, 0, tzinfo=timezone.utc),  # w4 file
        ]
    )

    class _MockDatetime(datetime):
        @staticmethod
        def now(tz=None):
            return next(dates)

    monkeypatch.setattr("src.ledger.datetime", _MockDatetime)

    writer = LedgerWriter(ledger_path=tmp_path)
    prev = ""
    for i in range(5):
        prev = writer.write(f"e{i}", {"i": i}, prev)

    files = sorted(tmp_path.glob("ledger-*.jsonl"))
    assert len(files) == 3
    assert files[0].name == "ledger-2026-01-01.jsonl"
    assert files[1].name == "ledger-2026-01-02.jsonl"
    assert files[2].name == "ledger-2026-01-03.jsonl"

    # Verify entry counts per file
    assert len(files[0].read_text().strip().splitlines()) == 2
    assert len(files[1].read_text().strip().splitlines()) == 2
    assert len(files[2].read_text().strip().splitlines()) == 1


def test_concurrent_writes(tmp_path):
    """Ten threads writing simultaneously: all entries appear, no corruption."""
    from src.ledger import LedgerWriter

    writer = LedgerWriter(ledger_path=tmp_path)
    errors: list[Exception] = []
    barrier = threading.Barrier(10)

    def _write_one(i: int) -> None:
        try:
            barrier.wait()  # all threads start together
            writer.write(f"thread_event_{i}", {"thread_id": i}, "")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_write_one, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"

    entries = _read_entries(tmp_path)
    assert len(entries) == 10, f"Expected 10 entries, got {len(entries)}"

    # All event types present (order may differ)
    types_seen = sorted(e["type"] for e in entries)
    assert types_seen == [f"thread_event_{i}" for i in range(10)]


def test_default_path(monkeypatch):
    """When LEDGER_PATH is not set, the default path is /tmp/ledger."""
    from src.ledger import LedgerWriter

    monkeypatch.delenv("LEDGER_PATH", raising=False)
    writer = LedgerWriter()
    assert writer.ledger_path == Path("/tmp/ledger")


def test_format_matches_existing(tmp_path):
    """Entry dict has exactly the five expected keys with correct types."""
    from src.ledger import LedgerWriter

    writer = LedgerWriter(ledger_path=tmp_path)
    writer.write("fmt_test", {"a": 1}, "abc123prev")

    entries = _read_entries(tmp_path)
    assert len(entries) == 1
    e = entries[0]

    assert set(e.keys()) == {"type", "timestamp", "data", "prev_hash", "chain_hash"}
    assert isinstance(e["type"], str)
    assert isinstance(e["timestamp"], str)
    assert isinstance(e["data"], dict)
    assert isinstance(e["prev_hash"], str)
    assert isinstance(e["chain_hash"], str)
    assert len(e["chain_hash"]) == 64
