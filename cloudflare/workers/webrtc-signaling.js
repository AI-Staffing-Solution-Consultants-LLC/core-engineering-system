/**
 * WebRTC Signaling Worker — Cloudflare Workers + Durable Objects
 *
 * Provides HTTP-based signaling for WebRTC peer connections.
 * Uses Durable Objects for session state (ephemeral, no persistent PII).
 *
 * Endpoints:
 *   POST /offer          — Store SDP offer, return session ID
 *   POST /answer         — Store SDP answer, associate with session
 *   POST /ice            — Relay ICE candidate between peers
 *   GET  /session/{id}   — Retrieve full session state
 *
 * Each session is a Durable Object instance identified by sessionId.
 * Sessions self-destruct after TTL_SESSION_MS of inactivity.
 */

import { DurableObject } from "cloudflare:workers";

// ── Constants ──────────────────────────────────────────────────────────────

/** Session expires 5 minutes after last activity. */
const TTL_SESSION_MS = 5 * 60 * 1000;

/** Tolerated clock skew for alarm re-arming (prevents tight loops). */
const ALARM_SKEW_MS = 2_000;

// ── Environment ────────────────────────────────────────────────────────────

export const SIGNALING_DO = "SIGNALING_DO";

// ── Durable Object: SignalingSession ──────────────────────────────────────

export class SignalingSession extends DurableObject {
  /** @param {DurableObjectState} ctx */
  /** @param {object} env */
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx = ctx;
  }

  /**
   * Main fetch handler — processes HTTP requests for this session.
   * @param {Request} request
   * @returns {Promise<Response>}
   */
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Standardize: strip leading/trailing slashes for routing
    const normalized = path.replace(/^\/+|\/+$/g, "");

    // Retrieve current session state from storage (ephemeral in-memory backed)
    let state = await this.ctx.storage.get("state") || this._emptyState();

    // ── Route by HTTP method + path ──────────────────────────────────

    if (request.method === "POST" && normalized.startsWith("offer")) {
      const body = await request.json().catch(() => ({}));
      return this._handleOffer(body, state);
    }

    if (request.method === "POST" && normalized.startsWith("answer")) {
      const body = await request.json().catch(() => ({}));
      return this._handleAnswer(body, state);
    }

    if (request.method === "POST" && normalized.startsWith("ice")) {
      const body = await request.json().catch(() => ({}));
      return this._handleIce(body, state);
    }

    if (request.method === "GET" && normalized.startsWith("session/")) {
      return this._handleGetSession(state);
    }

    // Also handle plain GET (no sub-path) for tests that call /session/{id}
    if (request.method === "GET") {
      return this._handleGetSession(state);
    }

    return new Response(
      JSON.stringify({ error: "not_found", path }),
      { status: 404, headers: { "Content-Type": "application/json" } }
    );
  }

  // ── Handlers ─────────────────────────────────────────────────────────

  /**
   * POST /offer — Store the offerer's SDP.
   */
  async _handleOffer(body, state) {
    state.offer = { sdp: body.sdp || null, created: Date.now() };
    state.role = "initiated";
    state.updated = Date.now();

    await this._persistState(state);
    this._armCleanupAlarm();

    return this._jsonResponse(201, {
      sessionId: this.ctx.id.toString(),
      state,
    });
  }

  /**
   * POST /answer — Store the answerer's SDP.
   */
  async _handleAnswer(body, state) {
    if (!state.offer) {
      return this._jsonResponse(400, {
        error: "no_offer",
        message: "Offer must be set before answer",
      });
    }

    state.answer = { sdp: body.sdp || null, created: Date.now() };
    state.role = "negotiating";
    state.updated = Date.now();

    await this._persistState(state);
    this._armCleanupAlarm();

    return this._jsonResponse(200, {
      sessionId: this.ctx.id.toString(),
      state,
    });
  }

  /**
   * POST /ice — Store an ICE candidate from either peer.
   * Body: { candidate: {...}, from: "offerer" | "answerer" }
   */
  async _handleIce(body, state) {
    const candidate = body.candidate;
    const from = body.from;

    if (!candidate) {
      return this._jsonResponse(400, {
        error: "missing_candidate",
        message: "ICE candidate object is required",
      });
    }

    if (!Array.isArray(state.iceCandidates)) {
      state.iceCandidates = [];
    }
    state.iceCandidates.push({
      candidate,
      from: from || "unknown",
      timestamp: Date.now(),
    });
    state.updated = Date.now();

    // Cap at 200 to prevent memory blow-up
    if (state.iceCandidates.length > 200) {
      state.iceCandidates = state.iceCandidates.slice(-100);
    }

    await this._persistState(state);
    this._armCleanupAlarm();

    return this._jsonResponse(200, {
      sessionId: this.ctx.id.toString(),
      candidateCount: state.iceCandidates.length,
    });
  }

  /**
   * GET /session/{id} — Return full session state.
   */
  async _handleGetSession(state) {
    return this._jsonResponse(200, {
      sessionId: this.ctx.id.toString(),
      state,
    });
  }

  // ── Alarm (TTL cleanup) ──────────────────────────────────────────────

  async alarm() {
    const state = await this.ctx.storage.get("state");
    if (!state || !state.updated) {
      await this._destroySession();
      return;
    }

    const deadline = state.updated + TTL_SESSION_MS;
    if (Date.now() >= deadline) {
      // Session expired — destroy
      await this._destroySession();
    } else {
      // Re-arm for the remaining time
      await this._armCleanupAlarm();
    }
  }

  // ── Internal helpers ─────────────────────────────────────────────────

  /**
   * Persist session state to DO storage.
   * Storage is ephemeral — data lives only while the DO is active.
   */
  async _persistState(state) {
    await this.ctx.storage.put("state", state);
  }

  /**
   * Arm the cleanup alarm for TTL_SESSION_MS from now.
   * Skews slightly to avoid tight loops.
   */
  async _armCleanupAlarm() {
    const existing = await this.ctx.storage.getAlarm();
    const target = Date.now() + TTL_SESSION_MS;

    if (existing === null || existing < target - ALARM_SKEW_MS) {
      await this.ctx.storage.setAlarm(target);
    }
  }

  /**
   * Wipe all session data and delete alarm.
   */
  async _destroySession() {
    await this.ctx.storage.delete("state");
    await this.ctx.storage.deleteAlarm();
  }

  /**
   * Return an empty session state object.
   */
  _emptyState() {
    return {
      role: "new",
      offer: null,
      answer: null,
      iceCandidates: [],
      created: Date.now(),
      updated: Date.now(),
    };
  }

  /**
   * Build a JSON response with proper headers.
   */
  _jsonResponse(status, body) {
    return new Response(JSON.stringify(body), {
      status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
}

// ── Worker entrypoint ─────────────────────────────────────────────────────

export default {
  /**
   * Fetch handler — routes incoming requests to the correct DO instance.
   *
   * URL patterns:
   *   POST /offer              → new DO (idFromName using random UUID)
   *   POST /answer?session=X   → route to DO by sessionId
   *   POST /ice?session=X      → route to DO by sessionId
   *   GET  /session/{id}       → route to DO by sessionId
   *
   * @param {Request} request
   * @param {object} env       — environment with SIGNALING_DO binding
   * @param {object} _ctx      — execution context
   * @returns {Promise<Response>}
   */
  async fetch(request, env, _ctx) {
    // Handle preflight CORS
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, ""); // strip trailing slash

    let sessionId = null;

    // Determine sessionId from path or query string
    if (path === "/offer") {
      // New session — generate unique ID
      sessionId = url.searchParams.get("session");
      if (!sessionId) {
        // Auto-generate — use timestamp + random for uniqueness
        sessionId = `${Date.now().toString(36)}-${crypto.randomUUID().slice(0, 8)}`;
      }
    } else if (path === "/answer" || path === "/ice") {
      sessionId = url.searchParams.get("session");
      if (!sessionId) {
        // Try reading from body for convenience
        try {
          const cloned = request.clone();
          const body = await cloned.json();
          sessionId = body.sessionId || null;
        } catch {
          // No body or invalid JSON — fall through
        }
      }
      if (!sessionId) {
        return new Response(
          JSON.stringify({ error: "missing_session", message: "session query param or body.sessionId required" }),
          { status: 400, headers: { "Content-Type": "application/json" } }
        );
      }
    } else if (path.startsWith("/session/")) {
      sessionId = path.slice("/session/".length);
    } else {
      return new Response(
        JSON.stringify({ error: "not_found", path }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    // Route to the DO
    const doId = env.SIGNALING_DO.idFromName(sessionId);
    const stub = env.SIGNALING_DO.get(doId);

    return stub.fetch(request);
  },
};
