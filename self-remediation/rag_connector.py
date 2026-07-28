"""
OpenViking RAG Connector — keyword-match document retrieval from the RAG corpus.

Provides a lightweight, zero-dependency retrieval interface over the
``rag/docs/openviking/`` knowledge base. Documents are matched by keyword
frequency — not embeddings. This is suitable for SOP lookups during incident
triage where embedding models are unnecessary overhead.

Usage::

    from rag_connector import OpenVikingRAG

    rag = OpenVikingRAG()
    docs = rag.query("Cloud Run service not Ready", top_k=3)
    for doc in docs:
        print(doc["title"], doc["score"])

Falls back to an empty list if ``rag/docs/openviking/`` does not exist.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("self-remediation.rag_connector")

# ── Default RAG corpus path ──────────────────────────────────────────────
# Resolution order:
#   1. RAG_CORPUS_PATH env var
#   2. ../rag/docs/openviking/ relative to this file
#   3. ./rag/docs/openviking/ relative to CWD
#   4. /app/rag/docs/openviking/ (container path)
_DEFAULT_RAG_PATHS: tuple[str, ...] = (
    "rag/docs/openviking/",
    "../rag/docs/openviking/",
    "/app/rag/docs/openviking/",
)


class OpenVikingRAG:
    """Keyword-frequency RAG retrieval over OpenViking knowledge base docs.

    Reads ``*.md`` files from the configured RAG corpus directory and
    ranks documents by the number of times query keywords appear.
    """

    def __init__(self, corpus_path: Optional[str | Path] = None) -> None:
        """Initialise the RAG connector.

        Args:
            corpus_path: Path to the RAG corpus directory. If ``None``,
                auto-discovers from environment or well-known locations.
        """
        self.corpus_path: Optional[Path] = self._resolve_path(corpus_path)
        self._cache: dict[str, str] = {}  # filename → content, lazily filled

        if self.corpus_path:
            logger.info("OpenVikingRAG: corpus path = %s", self.corpus_path)
        else:
            logger.warning(
                "OpenVikingRAG: corpus not found — queries will return empty"
            )

    # ── Public API ───────────────────────────────────────────────────────

    def query(
        self,
        anomaly_description: str,
        top_k: int = 3,
    ) -> list[dict]:
        """Search the RAG corpus for documents relevant to the anomaly.

        Args:
            anomaly_description: Free-text description of the anomaly
                (e.g. "Cloud Run service not Ready after deploy").
            top_k: Maximum number of documents to return (default 3).

        Returns:
            List of dicts, each with:
                - ``title`` (str): filename without ``.md`` extension
                - ``path`` (str): absolute path to the document
                - ``content`` (str): full document text
                - ``score`` (int): keyword frequency match score
        """
        if not self.corpus_path:
            return []

        # Extract meaningful keywords from the query
        keywords = self._tokenize(anomaly_description)

        # Load all documents (lazy — caches after first load)
        docs = self._load_docs()

        # Score each document by keyword frequency
        scored: list[dict] = []
        for filename, content in docs.items():
            if not keywords:
                # No meaningful keywords — no results
                break
            score = self._score(content, keywords)
            if score > 0:
                title = filename[:-3] if filename.endswith(".md") else filename
                scored.append(
                    {
                        "title": title,
                        "path": str(self.corpus_path / filename),
                        "content": content,
                        "score": score,
                    }
                )

        # Sort by score descending, limit to top_k
        scored.sort(key=lambda d: d["score"], reverse=True)
        return scored[:top_k]

    # ── Document loading ─────────────────────────────────────────────────

    def _load_docs(self) -> dict[str, str]:
        """Load all Markdown files from the corpus directory.

        Results are cached in ``self._cache`` after the first call.
        """
        if self._cache:
            return self._cache

        if not self.corpus_path or not self.corpus_path.is_dir():
            return {}

        for file_path in self.corpus_path.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                self._cache[file_path.name] = content
            except Exception:
                logger.warning("OpenVikingRAG: failed to read %s", file_path)

        logger.info(
            "OpenVikingRAG: loaded %d documents from corpus",
            len(self._cache),
        )
        return self._cache

    # ── Path resolution ──────────────────────────────────────────────────

    def _resolve_path(self, explicit: Optional[str | Path]) -> Optional[Path]:
        """Resolve the RAG corpus path from explicit argument, env var, or
        well-known locations."""
        import os

        if explicit:
            return Path(explicit)

        # Check RAG_CORPUS_PATH env var
        env_path = os.environ.get("RAG_CORPUS_PATH")
        if env_path:
            candidate = Path(env_path)
            # Append openviking subdirectory if the env var points to rag/docs/
            if candidate.name == "docs" and candidate.parent.name == "rag":
                candidate = candidate / "openviking"
            if candidate.is_dir():
                return candidate

        # Check well-known locations relative to this file's parent
        here = Path(__file__).resolve().parent
        for rel in _DEFAULT_RAG_PATHS:
            candidate = (here / rel).resolve()
            if candidate.is_dir():
                return candidate

        # Check relative to CWD
        cwd = Path.cwd()
        for rel in _DEFAULT_RAG_PATHS:
            candidate = (cwd / rel).resolve()
            if candidate.is_dir():
                return candidate

        return None

    # ── Scoring ──────────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Extract meaningful keywords from a free-text description.

        Splits on non-alphanumeric characters, lowercases, filters
        out very short words and common stop words.
        """
        _STOP_WORDS: frozenset[str] = frozenset(
            {
                "the",
                "a",
                "an",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "will",
                "would",
                "could",
                "should",
                "may",
                "might",
                "can",
                "shall",
                "not",
                "no",
                "nor",
                "but",
                "and",
                "or",
                "if",
                "then",
                "else",
                "when",
                "where",
                "why",
                "how",
                "all",
                "any",
                "both",
                "each",
                "few",
                "more",
                "most",
                "other",
                "some",
                "such",
                "only",
                "own",
                "same",
                "so",
                "than",
                "too",
                "very",
                "just",
                "this",
                "that",
                "these",
                "those",
                "it",
                "its",
                "for",
                "with",
                "from",
                "about",
                "into",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "between",
                "under",
                "over",
                "out",
                "off",
                "on",
                "at",
                "in",
                "by",
                "to",
                "of",
                "up",
                "down",
            }
        )

        tokens: list[str] = []
        for word in re.split(r"[^a-zA-Z0-9]+", text.lower()):
            word = word.strip()
            if len(word) > 2 and word not in _STOP_WORDS:
                tokens.append(word)
        return tokens

    @staticmethod
    def _score(content: str, keywords: list[str]) -> int:
        """Score a document by count of keyword occurrences.

        Each keyword match in the document content contributes 1 to the
        score. Matching is case-insensitive.
        """
        content_lower = content.lower()
        score = 0
        for kw in keywords:
            score += content_lower.count(kw)
        return score
