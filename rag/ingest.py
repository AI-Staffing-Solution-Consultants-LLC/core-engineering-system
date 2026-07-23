#!/usr/bin/env python3
"""
rag/ingest.py — OpenViking namespace ingestion pipeline.

Scans rag/docs/openviking/ for .md SOP files, maintains a corpus index
JSON file, and supports --dry-run and --watch modes for continuous ingestion.

Usage:
    python rag/ingest.py rag/docs/openviking/                          # interactive
    python rag/ingest.py rag/docs/openviking/ --dry-run                # preview only
    python rag/ingest.py rag/docs/openviking/ --watch                  # continuous polling
    python rag/ingest.py rag/docs/openviking/ --index rag/docs/index.json  # specific index
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


# ── Directory scanner ─────────────────────────────────────────────────
def scan_directory(path: str) -> list[dict[str, Any]]:
    """Scan a directory for .md files and return metadata for each.

    Returns a list of dicts with keys: name, path, hash, size_bytes.
    """
    results: list[dict[str, Any]] = []
    base = Path(path)
    if not base.is_dir():
        print(f"scan_directory: {path} is not a directory", file=sys.stderr)
        return results

    for md_file in sorted(base.rglob("*.md")):
        try:
            content = md_file.read_bytes()
            results.append(
                {
                    "name": md_file.name,
                    "path": str(md_file),
                    "hash": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                }
            )
        except Exception as exc:
            print(f"scan_directory: error reading {md_file}: {exc}", file=sys.stderr)

    return results


# ── Index management ──────────────────────────────────────────────────
def _load_index(index_path: str) -> dict[str, Any]:
    """Load existing index JSON, returning default structure if missing or corrupt."""
    path = Path(index_path)
    if not path.is_file():
        return {"version": "1.0", "files": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": "1.0", "files": {}}


def _save_index(index_path: str, index: dict[str, Any]) -> None:
    """Write index to disk atomically (write temp + rename)."""
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tmp_path.replace(path)


def _compute_namespace_key(scan_dir: str, file_entry: dict[str, Any]) -> str:
    """Compute the namespace-prefixed key for a file.

    If scan_dir is 'rag/docs/openviking', a file named 'SOP-001.md' gets
    key 'openviking/SOP-001.md'. This allows namespace-aware lookups.
    """
    scan_path = Path(scan_dir).resolve()
    file_path = Path(file_entry["path"]).resolve()

    try:
        rel = file_path.relative_to(scan_path)
    except ValueError:
        # File is not under scan_dir — use bare filename
        return file_entry["name"]

    parts = rel.parts
    if len(parts) == 1:
        # Direct child: prefix with parent directory name
        namespace = scan_path.name
        return f"{namespace}/{parts[0]}"
    else:
        # Nested: use relative path
        return str(rel)


# ── Core ingestion logic ──────────────────────────────────────────────
def run_ingestion(
    scan_dir: str,
    index_path: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scan for new .md files and update the corpus index.

    Args:
        scan_dir: Directory to scan for .md files.
        index_path: Path to the corpus index JSON file.
        dry_run: If True, report new files without modifying the index.

    Returns:
        Dict with keys: dry_run, total_scanned, new_files, skipped.
    """
    index = _load_index(index_path)
    scanned = scan_directory(scan_dir)

    existing_hashes: set[str] = set()
    for entry in index.get("files", {}).values():
        existing_hashes.add(entry.get("hash", ""))

    new_files: list[str] = []
    skipped: list[str] = []

    for entry in scanned:
        key = _compute_namespace_key(scan_dir, entry)
        if entry["hash"] in existing_hashes:
            skipped.append(key)
            continue
        index.setdefault("files", {})[key] = {
            "path": entry["path"],
            "hash": entry["hash"],
            "size_bytes": entry["size_bytes"],
        }
        new_files.append(key)

    if not dry_run and new_files:
        _save_index(index_path, index)

    return {
        "dry_run": dry_run,
        "total_scanned": len(scanned),
        "new_files": new_files,
        "skipped": skipped,
    }


# ── Watch mode ────────────────────────────────────────────────────────
def run_watch(
    scan_dir: str, index_path: str = "", interval_seconds: float = 5.0
) -> None:
    """Continuously poll scan_dir for new .md files.

    Args:
        scan_dir: Directory to watch for new .md files.
        index_path: Path to the corpus index JSON. Defaults to <scan_dir>/../index.json.
        interval_seconds: Polling interval in seconds.
    """
    if not index_path:
        index_path = str(Path(scan_dir).parent / "index.json")

    print(f"Watching {scan_dir} (interval={interval_seconds}s, index={index_path})")
    print("Press Ctrl+C to stop.")

    seen_hashes: set[str] = set()
    # Prime: load existing hashes
    index = _load_index(index_path)
    for entry in index.get("files", {}).values():
        seen_hashes.add(entry.get("hash", ""))

    try:
        while True:
            scanned = scan_directory(scan_dir)
            for entry in scanned:
                if entry["hash"] not in seen_hashes:
                    key = _compute_namespace_key(scan_dir, entry)
                    print(f"[NEW] {key} ({entry['size_bytes']} bytes)")
                    seen_hashes.add(entry["hash"])
                    # Auto-ingest: write to index immediately
                    index.setdefault("files", {})[key] = {
                        "path": entry["path"],
                        "hash": entry["hash"],
                        "size_bytes": entry["size_bytes"],
                    }
                    _save_index(index_path, index)

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nWatch stopped.")


# ── CLI ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenViking RAG ingestion pipeline — scan and index .md SOP files.",
    )
    parser.add_argument(
        "scan_dir",
        nargs="?",
        default="rag/docs/openviking",
        help="Directory to scan for .md files (default: rag/docs/openviking)",
    )
    parser.add_argument(
        "--index",
        default="rag/docs/index.json",
        help="Path to corpus index JSON file (default: rag/docs/index.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview new files without modifying the index",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously poll for new .md files",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Polling interval in seconds for --watch (default: 5.0)",
    )

    args = parser.parse_args()

    # Resolve paths relative to project root (script is in rag/)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    scan_dir = str(project_root / args.scan_dir)
    index_path = str(project_root / args.index)

    if args.watch:
        run_watch(scan_dir, index_path, args.interval)
    else:
        result = run_ingestion(scan_dir, index_path, dry_run=args.dry_run)
        mode = "[DRY-RUN] " if result["dry_run"] else ""
        print(f"{mode}Scanned {result['total_scanned']} files in {scan_dir}")
        if result["new_files"]:
            print(f"{mode}New files ({len(result['new_files'])}):")
            for f in result["new_files"]:
                print(f"  + {f}")
        else:
            print(f"{mode}No new files to ingest.")
        if result["skipped"]:
            print(f"Skipped {len(result['skipped'])} already-indexed files.")


if __name__ == "__main__":
    main()
