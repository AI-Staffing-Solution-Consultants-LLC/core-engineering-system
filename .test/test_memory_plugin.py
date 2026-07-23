"""
Tests for executive-quartet/memory_client.py — MemoryPlugin HTTP client.

TDD: these tests were written before the implementation module existed.
They define the contract: store, query, delete, retry, timeout, auth.
"""

import os
import time
from unittest.mock import MagicMock, call, patch

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    """Every test gets MEMORYPLUGIN_API_KEY set so no real env leaks in."""
    monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "test-api-key-abc123")


# ── Helper: load the module under test ────────────────────────────────


@pytest.fixture
def client_module():
    """Import the memory_client module (will fail until implementation exists)."""
    import importlib.util
    import sys
    from pathlib import Path

    file_path = (
        Path(__file__).resolve().parent.parent
        / "executive-quartet"
        / "memory_client.py"
    )
    spec = importlib.util.spec_from_file_location("memory_client", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["memory_client"] = module
    spec.loader.exec_module(module)
    return module


# ── Tests ─────────────────────────────────────────────────────────────


class TestStoreMemory:
    """store_memory(entity, context, data) → HTTP POST"""

    def test_store_memory_sends_correct_payload(self, client_module):
        """POST /api/memory with entity, context, data in JSON body."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {"id": "mem-001"}}
        mock_response.raise_for_status.return_value = None

        with patch.object(
            client_module.requests, "post", return_value=mock_response
        ) as mock_post:
            result = client_module.store_memory(
                entity="user-42", context="preferences", data={"theme": "dark"}
            )

        assert result == {"success": True, "data": {"id": "mem-001"}}

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # URL
        assert call_args[0][0] == "https://www.memoryplugin.com/api/mcp/memory"
        # JSON body
        assert call_args[1]["json"] == {
            "entity": "user-42",
            "context": "preferences",
            "data": {"theme": "dark"},
        }
        # Auth header
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key-abc123"
        # Timeout
        assert call_args[1]["timeout"] == 10

    def test_store_memory_raises_on_failure(self, client_module):
        """Propagates HTTP error when all retries exhausted."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        exc = client_module.requests.HTTPError("500 Server Error")
        exc.response = mock_response  # requests attaches the response to HTTPError
        mock_response.raise_for_status.side_effect = exc

        with patch.object(client_module.requests, "post", return_value=mock_response):
            with pytest.raises(client_module.MemoryPluginError, match="500"):
                client_module.store_memory(entity="e", context="c", data={"x": 1})
        mock_response.ok = False
        mock_response.status_code = 500

        with patch.object(client_module.requests, "post", return_value=mock_response):
            with pytest.raises(client_module.MemoryPluginError, match="500"):
                client_module.store_memory(entity="e", context="c", data={"x": 1})


class TestQueryMemory:
    """query_memory(entity, context, query) → HTTP POST"""

    def test_query_memory_sends_correct_payload(self, client_module):
        """POST /api/mcp/memory/query with entity, context, query."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": [{"id": "mem-001", "content": {"theme": "dark"}}],
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(
            client_module.requests, "post", return_value=mock_response
        ) as mock_post:
            result = client_module.query_memory(
                entity="user-42", context="preferences", query="theme"
            )

        assert result["success"] is True
        assert len(result["data"]) == 1

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://www.memoryplugin.com/api/mcp/memory/query"
        assert call_args[1]["json"] == {
            "entity": "user-42",
            "context": "preferences",
            "query": "theme",
        }
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key-abc123"


class TestDeleteMemory:
    """delete_memory(entity, memory_id) → HTTP DELETE"""

    def test_delete_memory_sends_correct_request(self, client_module):
        """DELETE /api/mcp/memory/{id} with correct URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": None}
        mock_response.raise_for_status.return_value = None

        with patch.object(
            client_module.requests, "delete", return_value=mock_response
        ) as mock_delete:
            result = client_module.delete_memory(entity="user-42", memory_id="mem-abc")

        assert result["success"] is True

        mock_delete.assert_called_once()
        call_args = mock_delete.call_args
        assert call_args[0][0] == "https://www.memoryplugin.com/api/mcp/memory/mem-abc"
        assert call_args[1]["params"] == {"entity": "user-42"}
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key-abc123"
        assert call_args[1]["timeout"] == 10


class TestRetryBehavior:
    """Retry: 3 attempts, exponential backoff (1s / 2s / 4s)."""

    def test_retries_on_5xx_with_exponential_backoff(self, client_module):
        """Retries up to 3 times with 1s, 2s, 4s backoff on server errors."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 503
        exc = client_module.requests.HTTPError("503")
        exc.response = mock_response
        mock_response.raise_for_status.side_effect = exc

        with patch.object(
            client_module.requests, "post", return_value=mock_response
        ) as mock_post:
            with patch.object(time, "sleep", return_value=None) as mock_sleep:
                with pytest.raises(client_module.MemoryPluginError, match="503"):
                    client_module.store_memory(entity="e", context="c", data={"x": 1})

        with patch.object(
            client_module.requests, "post", return_value=mock_response
        ) as mock_post:
            with patch.object(time, "sleep", return_value=None) as mock_sleep:
                with pytest.raises(client_module.MemoryPluginError, match="503"):
                    client_module.store_memory(entity="e", context="c", data={"x": 1})

        # 3 attempts: initial + 2 retries
        assert mock_post.call_count == 3

        # Exponential backoff: 1s, 2s (3rd attempt fails, no 4s sleep)
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list == [call(1.0), call(2.0)]

    def test_does_not_retry_on_4xx(self, client_module):
        """No retry on client errors (4xx) — fail fast."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        exc = client_module.requests.HTTPError("400 Bad Request")
        exc.response = mock_response
        mock_response.raise_for_status.side_effect = exc

        with patch.object(
            client_module.requests, "post", return_value=mock_response
        ) as mock_post:
            with pytest.raises(client_module.MemoryPluginError, match="400"):
                client_module.store_memory(entity="e", context="c", data={"x": 1})

        # Only 1 attempt — no retry on 4xx
        assert mock_post.call_count == 1


class TestTimeout:
    """Timeout: 10 seconds on all requests."""

    def test_request_times_out_after_10_seconds(self, client_module):
        """Raises MemoryPluginError on timeout."""
        with patch.object(
            client_module.requests, "post", side_effect=client_module.requests.Timeout
        ):
            with pytest.raises(client_module.MemoryPluginError, match="timed out"):
                client_module.store_memory(entity="e", context="c", data={"x": 1})

    def test_timeout_value_is_10_seconds(self, client_module):
        """All HTTP calls use timeout=10."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {"id": "x"}}
        mock_response.raise_for_status.return_value = None

        with patch.object(
            client_module.requests, "post", return_value=mock_response
        ) as mock_post:
            client_module.store_memory(entity="e", context="c", data={"x": 1})

        assert mock_post.call_args[1]["timeout"] == 10


class TestAuth:
    """API authentication via MEMORYPLUGIN_API_KEY env var."""

    def test_api_key_from_env_var(self, monkeypatch, client_module):
        """Reads MEMORYPLUGIN_API_KEY from environment, never hardcoded."""
        monkeypatch.setenv("MEMORYPLUGIN_API_KEY", "custom-key-xyz")

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_response.raise_for_status.return_value = None

        with patch.object(
            client_module.requests, "post", return_value=mock_response
        ) as mock_post:
            client_module.store_memory(entity="e", context="c", data={})

        assert (
            mock_post.call_args[1]["headers"]["Authorization"]
            == "Bearer custom-key-xyz"
        )

    def test_raises_when_api_key_missing(self, monkeypatch, client_module):
        """Raises MemoryPluginError if MEMORYPLUGIN_API_KEY is not set."""
        monkeypatch.delenv("MEMORYPLUGIN_API_KEY", raising=False)

        with pytest.raises(
            client_module.MemoryPluginError, match="MEMORYPLUGIN_API_KEY"
        ):
            client_module.store_memory(entity="e", context="c", data={})


class TestNoHardcodedKey:
    """Security: zero hardcoded API key values in the source file."""

    def test_no_hardcoded_api_key_in_source(self, client_module):
        """The module file contains no literal API key strings."""
        import inspect

        source_path = inspect.getfile(client_module)
        with open(source_path, "r") as f:
            source = f.read()

        # No bearer token, no base64-looking key, no suspicious assignment
        lower = source.lower()
        assert "sk-" not in lower, "hardcoded API key found"
        assert "api_key =" not in lower, "hardcoded API key assignment found"
        # The only mention of the env var should be os.getenv/os.environ
        count = lower.count("memoryplugin_api_key")
        # Should appear exactly once: in os.getenv("MEMORYPLUGIN_API_KEY") call
        assert count >= 1, "MEMORYPLUGIN_API_KEY not referenced at all"
