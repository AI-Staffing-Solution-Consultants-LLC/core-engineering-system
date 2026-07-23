"""SHA-256 chained JSONL ledger — tamper-evident write-ahead log.

Usage::

    from src.ledger import LedgerWriter

    writer = LedgerWriter()                    # /tmp/ledger (or $LEDGER_PATH)
    h1 = writer.write("deploy", {"env": "prod"}, "")
    h2 = writer.write("verify", {"ok": True}, h1)

Each entry is appended to a daily-rotated file ``ledger-YYYY-MM-DD.jsonl``.
Every entry carries a SHA-256 chain hash linking it to the previous entry,
making tampering detectable.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_LEDGER_PATH = Path("/tmp/ledger")


class LedgerWriter:
    """Thread-safe, SHA-256 chained JSONL ledger writer."""

    def __init__(self, ledger_path: str | Path | None = None) -> None:
        if ledger_path is not None:
            self.ledger_path = Path(ledger_path)
        else:
            self.ledger_path = Path(
                os.environ.get("LEDGER_PATH", str(_DEFAULT_LEDGER_PATH))
            )
        self.ledger_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ── public API ──────────────────────────────────────────────────────

    def write(self, entry_type: str, entry_data: dict, prev_hash: str) -> str:
        """Append a single chained entry to the ledger.

        Returns the 64-character lowercase hex chain_hash of the new entry.
        """
        entry: dict[str, object] = {
            "type": entry_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": entry_data,
            "prev_hash": prev_hash,
        }

        # Hash everything EXCEPT chain_hash (chicken-and-egg: chain_hash
        # cannot be part of the payload it authenticates).
        chain_hash = hashlib.sha256(
            (prev_hash + json.dumps(entry, sort_keys=True)).encode("utf-8")
        ).hexdigest()

        entry["chain_hash"] = chain_hash

        # Daily-rotated, thread-safe append
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ledger_file = self.ledger_path / f"ledger-{date_str}.jsonl"
        with self._lock:
            with open(ledger_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")

        return chain_hash
