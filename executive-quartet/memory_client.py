"""
MemoryPlugin HTTP client — shared library for the executive quartet.

Provides store/query/delete operations against the MemoryPlugin MCP API.
Auth via MEMORYPLUGIN_API_KEY env var (never hardcoded).
Retries: 3 attempts, exponential backoff (1s / 2s / 4s), timeout 10s.

Usage:
    from executive_quartet.memory_client import store_memory, query_memory, delete_memory

    store_memory(entity="user-42", context="preferences", data={"theme": "dark"})
    results = query_memory(entity="user-42", context="preferences", query="theme")
    delete_memory(entity="user-42", memory_id="mem-abc123")
"""

import os
import time

import requests  # Project-wide HTTP library (track-a/requirements.txt)

# ── Configuration ──────────────────────────────────────────────────────

BASE_URL = "https://www.memoryplugin.com/api/mcp"
_DEFAULT_TIMEOUT = 10  # seconds
_MAX_RETRIES = 3
_RETRY_BACKOFF = [1.0, 2.0, 4.0]  # seconds per attempt (1-indexed)
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class MemoryPluginError(Exception):
    """Raised when a MemoryPlugin API call fails after all retries, or on auth/timeout."""


# ── Internal helpers ───────────────────────────────────────────────────


def _get_api_key() -> str:
    """Read the API key from MEMORYPLUGIN_API_KEY env var — never hardcoded."""
    key = os.getenv("MEMORYPLUGIN_API_KEY")
    if not key:
        raise MemoryPluginError("MEMORYPLUGIN_API_KEY environment variable is not set")
    return key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


def _should_retry(response: requests.Response) -> bool:
    """Retry on server errors (5xx) and rate-limit (429), not on client errors (4xx)."""
    return response.status_code in _RETRYABLE_STATUSES


# ── Public API ─────────────────────────────────────────────────────────


def store_memory(entity: str, context: str, data: dict) -> dict:
    """Store a structured memory for an entity within a context.

    Args:
        entity: Identifier (e.g. user ID, session ID).
        context: Namespace or category (e.g. "preferences", "session_state").
        data: Arbitrary JSON-serializable payload.

    Returns:
        dict: {"success": True, "data": {"id": "mem-..."}}

    Raises:
        MemoryPluginError: On auth failure, timeout, or non-retryable HTTP error.
    """
    url = f"{BASE_URL}/memory"
    payload = {"entity": entity, "context": context, "data": data}

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=_headers(),
                timeout=_DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            last_error = MemoryPluginError("Request timed out after 10 seconds")
        except requests.HTTPError as exc:
            if _should_retry(exc.response):
                last_error = MemoryPluginError(
                    f"HTTP {exc.response.status_code}: {exc}"
                )
            else:
                raise MemoryPluginError(
                    f"HTTP {exc.response.status_code}: {exc}"
                ) from exc
        except requests.RequestException as exc:
            last_error = MemoryPluginError(f"Request failed: {exc}")

        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_BACKOFF[attempt - 1])

    raise last_error  # type: ignore[misc]


def query_memory(entity: str, context: str, query: str) -> dict:
    """Query memories for an entity within a context.

    Args:
        entity: Identifier.
        context: Namespace to search within.
        query: Search string or filter.

    Returns:
        dict: {"success": True, "data": [...]}

    Raises:
        MemoryPluginError: On auth failure, timeout, or non-retryable HTTP error.
    """
    url = f"{BASE_URL}/memory/query"
    payload = {"entity": entity, "context": context, "query": query}

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=_headers(),
                timeout=_DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            last_error = MemoryPluginError("Request timed out after 10 seconds")
        except requests.HTTPError as exc:
            if _should_retry(exc.response):
                last_error = MemoryPluginError(
                    f"HTTP {exc.response.status_code}: {exc}"
                )
            else:
                raise MemoryPluginError(
                    f"HTTP {exc.response.status_code}: {exc}"
                ) from exc
        except requests.RequestException as exc:
            last_error = MemoryPluginError(f"Request failed: {exc}")

        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_BACKOFF[attempt - 1])

    raise last_error  # type: ignore[misc]


def delete_memory(entity: str, memory_id: str) -> dict:
    """Delete a stored memory by ID.

    Args:
        entity: Identifier for ownership check.
        memory_id: The memory entry ID to delete.

    Returns:
        dict: {"success": True, "data": None}

    Raises:
        MemoryPluginError: On auth failure, timeout, or non-retryable HTTP error.
    """
    url = f"{BASE_URL}/memory/{memory_id}"
    params = {"entity": entity}

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.delete(
                url,
                params=params,
                headers=_headers(),
                timeout=_DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            last_error = MemoryPluginError("Request timed out after 10 seconds")
        except requests.HTTPError as exc:
            if _should_retry(exc.response):
                last_error = MemoryPluginError(
                    f"HTTP {exc.response.status_code}: {exc}"
                )
            else:
                raise MemoryPluginError(
                    f"HTTP {exc.response.status_code}: {exc}"
                ) from exc
        except requests.RequestException as exc:
            last_error = MemoryPluginError(f"Request failed: {exc}")

        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_BACKOFF[attempt - 1])

    raise last_error  # type: ignore[misc]
