"""
Tests for OpenViking RAG namespace integration.

Covers:
  - rag/ingest.py: scanning openviking/ .md files, --dry-run, index update
  - track-a/main.py: namespace-aware corpus loading and cross-namespace search
"""

import json
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Helpers ────────────────────────────────────────────────────────────
def _write_test_sop(directory: Path, name: str, content: str) -> Path:
    """Create a test SOP .md file and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _mock_track_b_post(url, json=None, timeout=None, **kwargs):
    """Mock Track B HTTP so module-level imports succeed."""

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"allowed": True, "exit_code": 0, "stdout": "mock", "stderr": ""}

    return MockResponse()


def _load_track_a_for_test(name: str, tmp_path, monkeypatch):
    """Load track-a/main.py with isolated LEDGER_PATH and RAG_CORPUS_PATH."""
    import importlib.util

    # Must set LEDGER_PATH before module-level LEDGER_PATH.mkdir() runs
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LEDGER_PATH", str(ledger_dir))

    spec = importlib.util.spec_from_file_location(
        name, REPO_ROOT / "track-a" / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    # Patch requests.post before exec_module so the import-time code doesn't
    # try to actually connect anywhere (requests is imported at module level)
    import requests as real_requests

    monkeypatch.setattr(real_requests, "post", _mock_track_b_post)
    spec.loader.exec_module(module)
    module._last_hash = None
    module.LEDGER_PATH = ledger_dir
    return module


# ── 1. Ingestion pipeline: scan and find new .md files ─────────────────
def test_ingestion_finds_new_markdown_files(tmp_path):
    """rag/ingest.py scans openviking/ and discovers .md files."""
    ov_dir = tmp_path / "openviking"
    _write_test_sop(
        ov_dir,
        "SOP-001-system-architecture.md",
        "# System Architecture\n\nOpenViking runs on GKE with Cloud Run sidecars.",
    )
    _write_test_sop(
        ov_dir,
        "SOP-002-incident-response.md",
        "# Incident Response\n\nP1: page on-call. P2: ticket within 15 min.",
    )

    from rag.ingest import scan_directory

    results = scan_directory(str(ov_dir))
    assert len(results) >= 2
    names = [r["name"] for r in results]
    assert "SOP-001-system-architecture.md" in names
    assert "SOP-002-incident-response.md" in names


# ── 2. Corpus update after ingestion ──────────────────────────────────
def test_corpus_includes_openviking_namespace(tmp_path, monkeypatch):
    """After copying .md into the RAG corpus path, load_rag_context finds them."""
    rag_dir = tmp_path / "rag"
    openviking_dir = rag_dir / "openviking"
    _write_test_sop(rag_dir, "README.md", "# Welcome\n\nCore Engineering System RAG.")
    _write_test_sop(
        openviking_dir,
        "SOP-001-system-architecture.md",
        "# OpenViking Architecture\n\nRuns on GKE with Cloud Run sidecars.",
    )
    _write_test_sop(
        openviking_dir,
        "SOP-002-incident-response.md",
        "# Incident Response\n\nP1: page on-call. P2: ticket within 15 min.",
    )

    monkeypatch.setenv("RAG_CORPUS_PATH", str(rag_dir))
    module = _load_track_a_for_test("track_a_ov", tmp_path, monkeypatch)

    corpus = module.load_rag_context()
    assert len(corpus) == 3

    # Root-level files keep filename as key
    assert "README.md" in corpus
    # openviking/ files use namespace-prefixed key
    assert "openviking/SOP-001-system-architecture.md" in corpus
    assert "openviking/SOP-002-incident-response.md" in corpus

    # Verify content
    assert "GKE with Cloud Run" in corpus["openviking/SOP-001-system-architecture.md"]


# ── 3. Search across namespaces ────────────────────────────────────────
def test_search_across_namespaces(tmp_path, monkeypatch):
    """search_rag() finds relevant chunks from both root and openviking namespaces."""
    rag_dir = tmp_path / "rag"
    openviking_dir = rag_dir / "openviking"
    _write_test_sop(
        rag_dir,
        "README.md",
        "# Core Engineering\n\nThis system monitors latency and crashes.",
    )
    _write_test_sop(
        openviking_dir,
        "SOP-001-system-architecture.md",
        "# OpenViking Architecture\n\nOpenViking runs on GKE with Cloud Run. "
        "Latency is measured via Cloud Monitoring.",
    )
    _write_test_sop(
        openviking_dir,
        "SOP-002-incident-response.md",
        "# Incident Response\n\nP1: page on-call. P2: ticket within 15 min.",
    )

    monkeypatch.setenv("RAG_CORPUS_PATH", str(rag_dir))
    module = _load_track_a_for_test("track_a_ov2", tmp_path, monkeypatch)

    corpus = module.load_rag_context()

    # Search for "latency" — should match both root README and openviking SOP-001
    results = module.search_rag(corpus, "latency", top_k=5)
    assert len(results) >= 2, f"Expected >=2 latency results, got {len(results)}"
    # At least one from openviking
    assert any("Cloud Monitoring" in r for r in results)

    # Search for "GKE" — only in openviking SOP-001
    results = module.search_rag(corpus, "GKE", top_k=5)
    assert len(results) >= 1
    assert any("GKE" in r for r in results)

    # Search for non-existent term
    results = module.search_rag(corpus, "dinosaur", top_k=5)
    assert len(results) == 0


# ── 4. Dry-run mode does not modify index ─────────────────────────────
def test_dry_run_does_not_modify(tmp_path):
    """--dry-run reports files but does not change the index on disk."""
    ov_dir = tmp_path / "openviking"
    _write_test_sop(
        ov_dir,
        "SOP-001-system-architecture.md",
        "# Architecture\n\nOpenViking runs on GKE.",
    )
    _write_test_sop(
        ov_dir,
        "SOP-002-incident-response.md",
        "# Incident Response\n\nP1: page on-call.",
    )

    index_path = tmp_path / "index.json"
    original_index = {
        "version": "1.0",
        "files": {"README.md": {"path": "README.md", "hash": "abc123"}},
    }
    index_path.write_text(json.dumps(original_index))

    from rag.ingest import run_ingestion

    result = run_ingestion(
        scan_dir=str(ov_dir),
        index_path=str(index_path),
        dry_run=True,
    )
    assert result["dry_run"] is True
    assert len(result["new_files"]) == 2

    # Index on disk should be unchanged
    on_disk = json.loads(index_path.read_text())
    assert on_disk == original_index
    assert "SOP-001-system-architecture.md" not in on_disk.get("files", {})


# ── 5. Existing corpus files are not removed ──────────────────────────
def test_ingestion_preserves_existing_corpus(tmp_path):
    """Running ingestion on openviking/ does not drop previously indexed files."""
    ov_dir = tmp_path / "openviking"
    _write_test_sop(ov_dir, "SOP-001-system-architecture.md", "# Arch\n\nGKE setup.")

    index_path = tmp_path / "index.json"
    original_index = {
        "version": "1.0",
        "files": {
            "README.md": {"path": "README.md", "hash": "abc123"},
            "DEPLOY.md": {"path": "DEPLOY.md", "hash": "def456"},
        },
    }
    index_path.write_text(json.dumps(original_index))

    from rag.ingest import run_ingestion

    run_ingestion(
        scan_dir=str(ov_dir),
        index_path=str(index_path),
        dry_run=False,
    )

    on_disk = json.loads(index_path.read_text())
    # Original entries still present
    assert "README.md" in on_disk["files"]
    assert "DEPLOY.md" in on_disk["files"]
    # New entry added with namespace prefix
    assert "openviking/SOP-001-system-architecture.md" in on_disk["files"]


# ── 6. Watch mode detects new files (basic polling test) ──────────────
def test_watch_mode_detects_new_files(tmp_path, monkeypatch):
    """--watch mode polls and detects newly added .md files."""
    ov_dir = tmp_path / "openviking"
    _write_test_sop(ov_dir, "SOP-001-system-architecture.md", "# Architecture\n\nGKE.")

    from rag.ingest import run_watch

    callbacks: list = []

    def fake_sleep(s):
        nonlocal callbacks
        files = list(ov_dir.rglob("*.md"))
        callbacks.append([f.name for f in files])
        # Stop the loop by raising StopIteration
        raise StopIteration()

    monkeypatch.setattr(time, "sleep", fake_sleep)

    try:
        run_watch(str(ov_dir), interval_seconds=0.5)
    except StopIteration:
        pass

    assert len(callbacks) >= 1
    assert "SOP-001-system-architecture.md" in callbacks[0]
