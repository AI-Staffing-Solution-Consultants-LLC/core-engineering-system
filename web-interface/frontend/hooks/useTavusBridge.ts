"use client";

import { useRef, useState, useCallback } from "react";
import type { Blendshapes } from "./useFaceTracker";

/* ── Configuration ───────────────────────────────────────────────────────── */

const THROTTLE_MS = 500;
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const SESSION_KEY = "core_engine_session_token";

/* ── Types ──────────────────────────────────────────────────────────────── */

export interface TavusBridgeState {
  /** Whether the bridge has sent at least one successful context update */
  isConnected: boolean;
  /** Timestamp (ms) of the last successful POST, or null */
  lastSent: number | null;
  /** Last POST error message, or null if healthy */
  error: string | null;
}

export interface TavusBridgeActions {
  /**
   * Send blendshape context data to the Tavus API via backend proxy.
   * Throttled to one call per 500ms. Identical calls (unchanged values)
   * within throttle window are dropped silently.
   */
  sendContext: (blendshapes: Blendshapes) => void;
}

/* ── Hook ───────────────────────────────────────────────────────────────── */

/**
 * React hook bridging MediaPipe blendshapes to the Tavus CVI context API.
 *
 * Ported from `cloudflare/pages/eim/mediapipe-tavus-bridge.js`.
 * Key changes:
 *   - CustomEvent dispatch → fetch() POST to backend proxy
 *   - EventTarget listener pattern → callback-based sendContext()
 *   - Emotion inference removed (backend handles that if needed);
 *     raw blendshapes sent as contextData for Tavus consumption.
 *
 * @param conversationId - The Tavus conversation ID to send context to
 */
export function useTavusBridge(
  conversationId: string | null
): TavusBridgeState & TavusBridgeActions {
  const [isConnected, setIsConnected] = useState(false);
  const [lastSent, setLastSent] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const lastSentTimeRef = useRef(0);
  const lastBlendshapesRef = useRef<Blendshapes | null>(null);

  const sendContext = useCallback(
    (blendshapes: Blendshapes) => {
      if (!conversationId) return;

      const now = performance.now();

      // Throttle: skip if within THROTTLE_MS window
      if (now - lastSentTimeRef.current < THROTTLE_MS) {
        lastBlendshapesRef.current = blendshapes;
        return;
      }

      // Skip if no significant change (avoid redundant API calls)
      if (lastBlendshapesRef.current) {
        const prev = lastBlendshapesRef.current;
        const keyExpressions = [
          "mouthSmileLeft",
          "mouthSmileRight",
          "mouthFrownLeft",
          "mouthFrownRight",
          "browInnerUp",
          "browDownLeft",
          "browDownRight",
          "jawOpen",
          "eyeWideLeft",
          "eyeWideRight",
        ];

        let changed = false;
        for (const key of keyExpressions) {
          if (
            Math.abs((blendshapes[key] || 0) - (prev[key] || 0)) > 0.05
          ) {
            changed = true;
            break;
          }
        }
        if (!changed) return;
      }

      lastSentTimeRef.current = now;
      lastBlendshapesRef.current = blendshapes;

      // Fire-and-forget POST (don't await — keep the bridge non-blocking)
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem(SESSION_KEY)
          : null;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      fetch(`${API_BASE}/api/tavus/context`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          conversationId,
          contextData: blendshapes,
        }),
      })
        .then((res) => {
          if (!res.ok) {
            return res.json().then((data) => {
              throw new Error(
                data.error || `Tavus context POST returned ${res.status}`
              );
            });
          }
          return res.json();
        })
        .then(() => {
          if (!isConnected) setIsConnected(true);
          setLastSent(Date.now());
          setError(null);
        })
        .catch((err) => {
          if (err instanceof Error) {
            setError(err.message);
          }
        });
    },
    [conversationId, isConnected]
  );

  return {
    isConnected,
    lastSent,
    error,
    sendContext,
  };
}
