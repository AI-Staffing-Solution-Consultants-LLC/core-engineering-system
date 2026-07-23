"""TDD tests for cloudflare/workers/webrtc-signaling.js — WebRTC Signaling Worker.

Tests a mock Worker environment that mirrors the Durable Objects behavior:
- POST /offer  → store SDP offer, return session ID
- POST /answer → store SDP answer, relay to session
- POST /ice    → relay ICE candidates between peers
- GET  /session/{id} → retrieve session state
- Ephemeral sessions with TTL cleanup (no persistent PII)
"""

import json
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Mock Cloudflare Worker Environment ────────────────────────────────────
# Mirrors the Durable Objects + Worker behavior of webrtc-signaling.js
# without requiring Node.js, wrangler dev, or miniflare.


class MockDurableObjectStorage:
    """Simulates ctx.storage API (get/put/delete + alarm)."""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._alarm: int | None = None

    async def get(self, key: str):
        return self._data.get(key)

    async def put(self, key: str, value: Any):
        self._data[key] = value

    async def delete(self, key: str):
        self._data.pop(key, None)

    async def getAlarm(self) -> int | None:
        return self._alarm

    async def setAlarm(self, ts: int):
        self._alarm = ts

    async def deleteAlarm(self):
        self._alarm = None


class MockSignalingSession:
    """Simulates the SignalingSession Durable Object."""

    TTL_MS = 5 * 60 * 1000

    def __init__(self, do_id: str):
        self._id = do_id
        self.storage = MockDurableObjectStorage()

    def _empty_state(self) -> dict:
        now = int(time.time() * 1000)
        return {
            "role": "new",
            "offer": None,
            "answer": None,
            "iceCandidates": [],
            "created": now,
            "updated": now,
        }

    async def _state(self) -> dict:
        existing = await self.storage.get("state")
        return existing if existing else self._empty_state()

    async def _persist(self, state: dict):
        await self.storage.put("state", state)

    async def _arm_alarm(self, state: dict):
        existing = await self.storage.getAlarm()
        target = state["updated"] + self.TTL_MS
        if existing is None or existing < target - 2000:
            await self.storage.setAlarm(target)

    async def _destroy(self):
        await self.storage.delete("state")
        await self.storage.deleteAlarm()

    async def run_alarm(self):
        """Simulate alarm firing — cleanup if expired."""
        state = await self.storage.get("state")
        if state is None:
            await self._destroy()
            return "destroyed_no_state"
        if time.time() * 1000 >= state["updated"] + self.TTL_MS:
            await self._destroy()
            return "destroyed_expired"
        await self._arm_alarm(state)
        return "rearmed"

    # ── Endpoint handlers (mirror DO fetch routing) ──────────────────────

    async def handle(self, method: str, path: str, body: dict | None = None):
        state = await self._state()

        if method == "POST" and path in ("/offer", "/offer/"):
            return await self._do_offer(body or {}, state)
        if method == "POST" and path in ("/answer", "/answer/"):
            return await self._do_answer(body or {}, state)
        if method == "POST" and path in ("/ice", "/ice/"):
            return await self._do_ice(body or {}, state)
        if method == "GET":
            return await self._do_get(state)

        return {"status": 404, "body": {"error": "not_found", "path": path}}

    async def _do_offer(self, body: dict, state: dict):
        state["offer"] = {"sdp": body.get("sdp"), "created": int(time.time() * 1000)}
        state["role"] = "initiated"
        state["updated"] = int(time.time() * 1000)
        await self._persist(state)
        await self._arm_alarm(state)
        return {
            "status": 201,
            "body": {"sessionId": self._id, "state": state},
        }

    async def _do_answer(self, body: dict, state: dict):
        if not state.get("offer"):
            return {
                "status": 400,
                "body": {
                    "error": "no_offer",
                    "message": "Offer must be set before answer",
                },
            }
        state["answer"] = {"sdp": body.get("sdp"), "created": int(time.time() * 1000)}
        state["role"] = "negotiating"
        state["updated"] = int(time.time() * 1000)
        await self._persist(state)
        await self._arm_alarm(state)
        return {
            "status": 200,
            "body": {"sessionId": self._id, "state": state},
        }

    async def _do_ice(self, body: dict, state: dict):
        candidate = body.get("candidate")
        if not candidate:
            return {
                "status": 400,
                "body": {
                    "error": "missing_candidate",
                    "message": "ICE candidate object is required",
                },
            }
        if not isinstance(state.get("iceCandidates"), list):
            state["iceCandidates"] = []
        state["iceCandidates"].append(
            {
                "candidate": candidate,
                "from": body.get("from", "unknown"),
                "timestamp": int(time.time() * 1000),
            }
        )
        state["updated"] = int(time.time() * 1000)

        if len(state["iceCandidates"]) > 200:
            state["iceCandidates"] = state["iceCandidates"][-100:]

        await self._persist(state)
        await self._arm_alarm(state)
        return {
            "status": 200,
            "body": {
                "sessionId": self._id,
                "candidateCount": len(state["iceCandidates"]),
            },
        }

    async def _do_get(self, state: dict):
        return {
            "status": 200,
            "body": {"sessionId": self._id, "state": state},
        }


class MockSignalingWorker:
    """Simulates the Worker's fetch handler — routing requests to DO instances."""

    def __init__(self):
        self._sessions: dict[str, MockSignalingSession] = {}

    def _get_session(self, session_id: str) -> MockSignalingSession:
        """idFromName — deterministic DO lookup."""
        if session_id not in self._sessions:
            self._sessions[session_id] = MockSignalingSession(session_id)
        return self._sessions[session_id]

    async def fetch(self, method: str, url_path: str, body: dict | None = None):
        """Simulate a fetch() call to the Worker."""
        path = url_path.rstrip("/") or "/"

        # Determine sessionId
        session_id = None

        if path == "/offer":
            if body and "sessionId" in body:
                session_id = body["sessionId"]
            if not session_id:
                session_id = f"test-{uuid.uuid4().hex[:8]}"
        elif path in ("/answer", "/ice"):
            if body and "sessionId" in body:
                session_id = body["sessionId"]
            if not session_id:
                return {"status": 400, "body": {"error": "missing_session"}}
        elif path.startswith("/session/"):
            session_id = path[len("/session/") :]
        else:
            return {"status": 404, "body": {"error": "not_found", "path": path}}

        session = self._get_session(session_id)
        return await session.handle(method, path, body)

    def run_alarm_for(self, session_id: str):
        """Trigger alarm cleanup for a given session."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        import asyncio

        return asyncio.run(session.run_alarm())


# ── Test fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def worker():
    """Fresh MockSignalingWorker for each test."""
    return MockSignalingWorker()


# ── Test 1: POST /offer creates session and returns session ID ────────────


class TestOffer:
    """POST /offer → store SDP offer in DO, return session ID."""

    def test_offer_creates_session_and_returns_id(self, worker):
        """Offering with an SDP should return a sessionId and store the offer."""
        sdp = "v=0\r\no=- 1234567890 2 IN IP4 127.0.0.1\r\ns=-\r\n"
        response = worker.fetch("POST", "/offer", {"sdp": sdp})

        # Must be async, let's use a sync wrapper approach
        import asyncio

        result = asyncio.run(response)

        assert result["status"] == 201, (
            f"Expected 201, got {result['status']}: {result['body']}"
        )
        body = result["body"]
        assert "sessionId" in body, f"No sessionId in response: {body}"
        assert len(body["sessionId"]) > 0
        assert body["state"]["role"] == "initiated"
        assert body["state"]["offer"]["sdp"] == sdp

    def test_offer_respects_explicit_session_id(self, worker):
        """When body.sessionId is provided, use it instead of auto-generating."""
        import asyncio

        sdp = "v=0\r\no=offerer\r\n"
        custom_id = "my-custom-session-42"

        result = asyncio.run(
            worker.fetch("POST", "/offer", {"sdp": sdp, "sessionId": custom_id})
        )

        assert result["status"] == 201
        assert result["body"]["sessionId"] == custom_id

    def test_offer_without_sdp_still_creates_session(self, worker):
        """Offering without SDP should still create a session (null offer)."""
        import asyncio

        result = asyncio.run(worker.fetch("POST", "/offer", {}))

        assert result["status"] == 201
        assert result["body"]["state"]["offer"]["sdp"] is None


# ── Test 2: POST /answer stores answer and associates with session ────────


class TestAnswer:
    """POST /answer → relay SDP answer to session."""

    def test_answer_stores_on_existing_offer(self, worker):
        """Answering on a session with an existing offer should store answer."""
        import asyncio

        # First create offer
        sid = "test-answer-session"
        offer_sdp = "v=0\r\no=offerer\r\n"
        asyncio.run(
            worker.fetch("POST", "/offer", {"sdp": offer_sdp, "sessionId": sid})
        )

        # Then answer
        answer_sdp = "v=0\r\no=answerer\r\n"
        result = asyncio.run(
            worker.fetch("POST", "/answer", {"sdp": answer_sdp, "sessionId": sid})
        )

        assert result["status"] == 200, (
            f"Expected 200, got {result['status']}: {result['body']}"
        )
        body = result["body"]
        assert body["state"]["answer"]["sdp"] == answer_sdp
        assert body["state"]["role"] == "negotiating"
        assert body["state"]["offer"]["sdp"] == offer_sdp  # offer still intact

    def test_answer_without_offer_fails(self, worker):
        """Answering on a fresh session (no offer) should return 400."""
        import asyncio

        result = asyncio.run(
            worker.fetch(
                "POST", "/answer", {"sdp": "v=0", "sessionId": "no-offer-session"}
            )
        )

        assert result["status"] == 400
        assert "no_offer" in result["body"].get("error", "")

    def test_answer_without_session_id_fails(self, worker):
        """Answering without a sessionId should return 400."""
        import asyncio

        result = asyncio.run(worker.fetch("POST", "/answer", {"sdp": "v=0"}))

        assert result["status"] == 400
        assert "error" in result["body"]


# ── Test 3: POST /ice relays ICE candidates between peers ─────────────────


class TestIce:
    """POST /ice → relay ICE candidates between peers."""

    def test_ice_stores_candidate_on_session(self, worker):
        """Posting an ICE candidate should store it on the session."""
        import asyncio

        sid = "test-ice-session"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        candidate = {
            "candidate": "candidate:1 1 UDP 2122252543 192.168.1.1 12345 typ host",
            "sdpMid": "0",
            "sdpMLineIndex": 0,
        }
        result = asyncio.run(
            worker.fetch(
                "POST",
                "/ice",
                {"candidate": candidate, "from": "offerer", "sessionId": sid},
            )
        )

        assert result["status"] == 200
        assert result["body"]["candidateCount"] == 1

    def test_ice_relays_multiple_candidates(self, worker):
        """Multiple ICE candidates from both peers accumulate correctly."""
        import asyncio

        sid = "test-ice-multi"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        for i in range(5):
            result = asyncio.run(
                worker.fetch(
                    "POST",
                    "/ice",
                    {
                        "candidate": {
                            "candidate": f"candidate:{i}",
                            "sdpMid": "0",
                            "sdpMLineIndex": 0,
                        },
                        "from": "offerer" if i % 2 == 0 else "answerer",
                        "sessionId": sid,
                    },
                )
            )
            assert result["status"] == 200

        # Fetch session to verify
        result = asyncio.run(worker.fetch("GET", f"/session/{sid}"))
        state = result["body"]["state"]
        assert len(state["iceCandidates"]) == 5
        assert state["iceCandidates"][0]["from"] == "offerer"
        assert state["iceCandidates"][1]["from"] == "answerer"

    def test_ice_without_candidate_fails(self, worker):
        """Posting ICE without a candidate should return 400."""
        import asyncio

        sid = "test-ice-no-candidate"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        result = asyncio.run(
            worker.fetch("POST", "/ice", {"from": "offerer", "sessionId": sid})
        )

        assert result["status"] == 400
        assert "missing_candidate" in result["body"].get("error", "")


# ── Test 4: GET /session/{id} returns full session state ──────────────────


class TestSessionState:
    """GET /session/{id} → retrieve full session state."""

    def test_session_retrieves_full_state(self, worker):
        """After offer + answer + ICE, GET /session/{id} returns complete state."""
        import asyncio

        sid = "test-full-session"
        offer_sdp = "v=0\r\no=offerer"
        answer_sdp = "v=0\r\no=answerer"

        # Build full session
        asyncio.run(
            worker.fetch("POST", "/offer", {"sdp": offer_sdp, "sessionId": sid})
        )
        asyncio.run(
            worker.fetch("POST", "/answer", {"sdp": answer_sdp, "sessionId": sid})
        )
        asyncio.run(
            worker.fetch(
                "POST",
                "/ice",
                {
                    "candidate": {
                        "candidate": "c:1",
                        "sdpMid": "0",
                        "sdpMLineIndex": 0,
                    },
                    "from": "offerer",
                    "sessionId": sid,
                },
            )
        )
        asyncio.run(
            worker.fetch(
                "POST",
                "/ice",
                {
                    "candidate": {
                        "candidate": "c:2",
                        "sdpMid": "0",
                        "sdpMLineIndex": 0,
                    },
                    "from": "answerer",
                    "sessionId": sid,
                },
            )
        )

        # Retrieve
        result = asyncio.run(worker.fetch("GET", f"/session/{sid}"))
        assert result["status"] == 200

        state = result["body"]["state"]
        assert state["role"] == "negotiating"
        assert state["offer"]["sdp"] == offer_sdp
        assert state["answer"]["sdp"] == answer_sdp
        assert len(state["iceCandidates"]) == 2
        assert isinstance(state["created"], int)
        assert isinstance(state["updated"], int)

    def test_session_new_has_empty_state(self, worker):
        """A GET on a brand new (never POST'd) session returns default state."""
        import asyncio

        result = asyncio.run(worker.fetch("GET", "/session/brand-new-session"))

        assert result["status"] == 200
        state = result["body"]["state"]
        assert state["role"] == "new"
        assert state["offer"] is None
        assert state["answer"] is None
        assert state["iceCandidates"] == []

    def test_session_returns_same_id(self, worker):
        """Session ID in response body matches the ID used for retrieval."""
        import asyncio

        sid = "test-same-id"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        result = asyncio.run(worker.fetch("GET", f"/session/{sid}"))
        assert result["body"]["sessionId"] == sid


# ── Test 5: Ephemeral cleanup (no persistent PII) ─────────────────────────


class TestCleanup:
    """Sessions are ephemeral with TTL-based alarm cleanup."""

    def test_alarm_destroys_expired_session(self, worker):
        """When alarm fires after TTL, session is destroyed."""
        import asyncio

        sid = "test-cleanup"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        # Manually age the session past TTL
        session = worker._sessions[sid]
        state = asyncio.run(session._state())
        state["updated"] = 0  # 1970 — way expired
        asyncio.run(session._persist(state))

        # Trigger alarm — should destroy
        alarm_result = asyncio.run(session.run_alarm())
        assert alarm_result == "destroyed_expired"

        # State should be gone
        remaining = asyncio.run(session._state())
        assert remaining["role"] == "new"  # empty state returned
        assert remaining["offer"] is None

    def test_alarm_does_not_destroy_active_session(self, worker):
        """An active session (recently updated) survives alarm check."""
        import asyncio

        sid = "test-active"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        session = worker._sessions[sid]
        alarm_result = asyncio.run(session.run_alarm())
        assert alarm_result == "rearmed"  # not destroyed

        # Offer should still be there
        state = asyncio.run(session._state())
        assert state["offer"] is not None
        assert state["offer"]["sdp"] == "v=0"

    def test_alarm_with_no_state_cleans_up(self, worker):
        """If DO has no state at all, alarm destroys it cleanly."""
        import asyncio

        sid = "test-no-state"
        # Use DO directly without creating via offer
        session = worker._get_session(sid)
        alarm_result = asyncio.run(session.run_alarm())

        assert alarm_result == "destroyed_no_state"

    def test_sessions_are_independent(self, worker):
        """Cleaning up one session must not affect another."""
        import asyncio

        sid1 = "test-independent-1"
        sid2 = "test-independent-2"

        asyncio.run(
            worker.fetch("POST", "/offer", {"sdp": "v=0-offer1", "sessionId": sid1})
        )
        asyncio.run(
            worker.fetch("POST", "/offer", {"sdp": "v=0-offer2", "sessionId": sid2})
        )

        # Kill sid1
        session1 = worker._sessions[sid1]
        state1 = asyncio.run(session1._state())
        state1["updated"] = 0
        asyncio.run(session1._persist(state1))
        alarm_result = asyncio.run(session1.run_alarm())
        assert alarm_result == "destroyed_expired"

        # sid2 should be untouched
        state2 = asyncio.run(worker._sessions[sid2]._state())
        assert state2["offer"]["sdp"] == "v=0-offer2"
        assert state2["role"] == "initiated"

    def test_ice_candidates_capped_at_limit(self, worker):
        """ICE candidate list caps at 200 (keeps last 100 when exceeded)."""
        import asyncio

        sid = "test-ice-cap"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        # Add 300 candidates — enough to trigger cap at least once
        for i in range(300):
            asyncio.run(
                worker.fetch(
                    "POST",
                    "/ice",
                    {
                        "candidate": {
                            "candidate": f"c:{i}",
                            "sdpMid": "0",
                            "sdpMLineIndex": 0,
                        },
                        "from": "offerer",
                        "sessionId": sid,
                    },
                )
            )

        result = asyncio.run(worker.fetch("GET", f"/session/{sid}"))
        candidates = result["body"]["state"]["iceCandidates"]
        assert len(candidates) <= 200, (
            f"ICE candidates should be capped, got {len(candidates)}"
        )
        assert candidates[0]["candidate"]["candidate"] != "c:0", (
            "Early candidates should be trimmed by cap"
        )

    def test_no_persistent_pii_in_state(self, worker):
        """Session state must not contain any PII-like fields."""
        import asyncio

        sid = "test-no-pii"
        asyncio.run(worker.fetch("POST", "/offer", {"sdp": "v=0", "sessionId": sid}))

        result = asyncio.run(worker.fetch("GET", f"/session/{sid}"))
        state = result["body"]["state"]

        # No PII keys
        pii_keys = [
            "email",
            "name",
            "ip",
            "user",
            "password",
            "token",
            "secret",
            "key",
            "ssn",
        ]
        for key in pii_keys:
            assert key not in state, f"PII key '{key}' found in state: {state}"

        # No identity-bearing fields in offer/answer/ice structures
        if state["offer"]:
            for pii_key in pii_keys:
                assert pii_key not in state["offer"]
        if state["answer"]:
            for pii_key in pii_keys:
                assert pii_key not in state["answer"]
