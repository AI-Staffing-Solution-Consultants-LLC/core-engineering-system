"""
Gemini Knowledge Steward — AI-powered anomaly diagnosis and remediation advice.

Integrates with Google Gemini (via ``google.generativeai``) to analyse
telemetry anomaly reports and produce structured diagnostic output:
``{diagnosis, recommended_action, confidence}``.

Usage::

    from knowledge_steward import GeminiKnowledgeSteward

    steward = GeminiKnowledgeSteward()
    result = steward.analyze(
        {
            "service_name": "track-a-control-loop",
            "condition_type": "Ready",
            "condition_message": "Revision 'v3' has failed to start.",
        },
        rag_context=["SOP-001: System Architecture — control loop..."]
    )

Graceful degradation:
    - If ``GEMINI_API_KEY`` is missing or the API call fails, returns a stub
      response instead of crashing::

          {
              "diagnosis": "Knowledge Steward unavailable",
              "recommended_action": "Review logs manually",
              "confidence": 0.0,
          }

    - API keys and full prompts are NEVER echoed to logs.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger("self-remediation.knowledge_steward")

# ── Prompt template for Gemini ───────────────────────────────────────────
_SYSTEM_PROMPT: str = (
    "You are a root-cause analysis engine for a production observability "
    "platform called OpenViking. Given an anomaly report from telemetry "
    "data (GCP Cloud Run conditions, service health failures, etc.) and "
    "optionally relevant documentation context, produce a structured "
    "diagnosis with a recommended remediation action and a confidence "
    "score (0.0–1.0).\n\n"
    "Return ONLY a JSON object with keys: diagnosis (string describing "
    "the likely root cause), recommended_action (specific, actionable "
    "remediation step), and confidence (float 0.0–1.0, where 1.0 is "
    "high confidence)."
)


class GeminiKnowledgeSteward:
    """Encapsulates Gemini API integration for anomaly root-cause analysis.

    Requires ``google-generativeai`` package and ``GEMINI_API_KEY``
    environment variable. Falls back to a stub response if either is
    missing or the API is unreachable.
    """

    # Default model — flash variant for low-latency diagnosis
    DEFAULT_MODEL: str = "gemini-2.0-flash"

    def __init__(self) -> None:
        self._api_key: Optional[str] = os.environ.get("GEMINI_API_KEY")
        self._model: Optional[Any] = None  # genai.GenerativeModel instance
        self._api_available: bool = False

        if not self._api_key:
            logger.warning(
                "GeminiKnowledgeSteward: GEMINI_API_KEY not set — "
                "AI-powered diagnosis disabled (will return stub responses)"
            )
            return

        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self.DEFAULT_MODEL)
            self._api_available = True
            logger.info("GeminiKnowledgeSteward: Gemini API configured")
        except ImportError:
            logger.warning("GeminiKnowledgeSteward: google.generativeai not installed")
        except Exception:
            logger.exception("GeminiKnowledgeSteward: failed to initialise Gemini API")

    # ── Public API ───────────────────────────────────────────────────────

    def analyze(
        self,
        anomaly_report: dict,
        rag_context: Optional[list[str]] = None,
    ) -> dict:
        """Analyse an anomaly report and return a diagnostic.

        Args:
            anomaly_report: Dictionary with anomaly metadata, e.g.::

                {
                    "source": "gcp_cloud_run",
                    "service_name": "track-a-control-loop",
                    "condition_type": "Ready",
                    "condition_message": "Revision has failed.",
                }

            rag_context: Optional list of string snippets from the RAG
                corpus (OpenViking SOPs, incident runbooks, etc.) to
                provide domain context to the model.

        Returns:
            Dictionary with:
                - ``diagnosis`` (str): likely root cause
                - ``recommended_action`` (str): actionable remediation step
                - ``confidence`` (float): 0.0–1.0
        """
        # Build the user prompt from the anomaly + RAG context
        prompt = self._build_prompt(anomaly_report, rag_context)

        # Try Gemini; fall back to stub on failure
        if self._api_available and self._model is not None:
            try:
                response = self._model.generate_content(prompt)
                parsed = self._parse_response(response)
                if parsed:
                    return parsed
            except Exception:
                logger.exception(
                    "GeminiKnowledgeSteward: API call failed — returning stub response"
                )

        return self._stub_response()

    # ── Prompt construction ──────────────────────────────────────────────

    def _build_prompt(
        self,
        anomaly_report: dict,
        rag_context: Optional[list[str]],
    ) -> str:
        """Construct the full prompt sent to Gemini."""
        parts: list[str] = [_SYSTEM_PROMPT, ""]

        # Anomaly data (redacted — never log API keys)
        anomaly_str = json.dumps(anomaly_report, indent=2, default=str)
        parts.append("ANOMALY REPORT:")
        parts.append(anomaly_str)

        # RAG context (OpenViking documentation)
        if rag_context:
            parts.append("")
            parts.append("RELEVANT DOCUMENTATION CONTEXT:")
            for i, snippet in enumerate(rag_context, start=1):
                # Truncate each snippet to avoid blowing context window
                truncated = snippet[:2000]
                parts.append(f"--- Context {i} ---")
                parts.append(truncated)
        else:
            parts.append("")
            parts.append("RELEVANT DOCUMENTATION: (none provided)")

        parts.append("")
        parts.append(
            "Return ONLY a JSON object with keys diagnosis, "
            "recommended_action, and confidence. No other text."
        )

        return "\n".join(parts)

    # ── Response parsing ─────────────────────────────────────────────────

    def _parse_response(self, response: Any) -> Optional[dict]:
        """Attempt to parse the Gemini response as a JSON diagnostic.

        Returns ``None`` if parsing fails (caller should fall back to
        the stub response).
        """
        try:
            text = response.text
        except (AttributeError, ValueError):
            logger.warning("GeminiKnowledgeSteward: empty response from API")
            return None

        if not text:
            return None

        # Strip any markdown code fences the model might have added
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence
            lines = cleaned.split("\n")
            if len(lines) > 1:
                lines = lines[1:]  # skip opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # strip closing fence
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "GeminiKnowledgeSteward: non-JSON response — raw=%s",
                cleaned[:200],
            )
            return None

        # Validate required keys
        required = {"diagnosis", "recommended_action", "confidence"}
        if not required.issubset(parsed.keys()):
            logger.warning(
                "GeminiKnowledgeSteward: response missing required keys — got %s",
                list(parsed.keys()),
            )
            return None

        return {
            "diagnosis": str(parsed.get("diagnosis", "")),
            "recommended_action": str(parsed.get("recommended_action", "")),
            "confidence": float(parsed.get("confidence", 0.0)),
        }

    # ── Stub / fallback ──────────────────────────────────────────────────

    def _stub_response(self) -> dict:
        """Return a safe stub response when Gemini is unavailable."""
        return {
            "diagnosis": "Knowledge Steward unavailable",
            "recommended_action": "Review logs manually",
            "confidence": 0.0,
        }
