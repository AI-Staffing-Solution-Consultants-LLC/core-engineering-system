"use client";

import { useEffect, useRef, useState } from "react";

/* ── Debounce constants ──────────────────────────────────────────────────── */

const MUTE_DEBOUNCE_MS = 300;
const UNMUTE_DEBOUNCE_MS = 500;
const MUTE_THRESHOLD = 0.5;
const UNMUTE_THRESHOLD = 0.3;

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const SESSION_KEY = "core_engine_session_token";

/* ── Types ──────────────────────────────────────────────────────────────── */

interface UseInterruptionParams {
  jawOpen: number | null;
  iframeContainerRef: React.RefObject<HTMLDivElement | null>;
  conversationId: string | null;
}

/* ── Hook ───────────────────────────────────────────────────────────────── */

export function useInterruption({
  jawOpen,
  iframeContainerRef,
  conversationId,
}: UseInterruptionParams): { isInterrupted: boolean } {
  const [isInterrupted, setIsInterrupted] = useState(false);
  const muteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmuteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMutedRef = useRef(false);

  /* ── Cleanup ────────────────────────────────────────────────────────── */

  useEffect(() => {
    return () => {
      if (muteTimerRef.current !== null) {
        clearTimeout(muteTimerRef.current);
        muteTimerRef.current = null;
      }
      if (unmuteTimerRef.current !== null) {
        clearTimeout(unmuteTimerRef.current);
        unmuteTimerRef.current = null;
      }
    };
  }, []);

  /* ── postMessage helper ─────────────────────────────────────────────── */

  function postToIframe(message: { type: "mute" | "unmute" }): void {
    const iframe = iframeContainerRef.current?.querySelector(
      "iframe"
    ) as HTMLIFrameElement | null;

    try {
      iframe?.contentWindow?.postMessage(message, "*");
    } catch {
      // Non-fatal: iframe may not be ready or cross-origin restricted
    }
  }

  /* ── Context event publisher ────────────────────────────────────────── */

  function sendInterruptionEvent(active: boolean): void {
    if (!conversationId) return;

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
        contextData: {
          interruption: {
            active,
            jawOpen: jawOpen ?? 0,
            timestamp: Date.now(),
          },
        },
      }),
    }).catch(() => {
      // Fire-and-forget — failure is non-fatal
    });
  }

  /* ── JawOpen monitoring ──────────────────────────────────────────────── */

  useEffect(() => {
    if (jawOpen === null) return;

    // ── Jaw open wide → consider muting ──────────────────────────────
    if (jawOpen > MUTE_THRESHOLD && !isMutedRef.current) {
      // Cancel any pending unmute
      if (unmuteTimerRef.current !== null) {
        clearTimeout(unmuteTimerRef.current);
        unmuteTimerRef.current = null;
      }
      // Start mute timer if not already counting down
      if (muteTimerRef.current === null) {
        muteTimerRef.current = setTimeout(() => {
          muteTimerRef.current = null;
          if (jawOpen > MUTE_THRESHOLD) {
            isMutedRef.current = true;
            setIsInterrupted(true);
            postToIframe({ type: "mute" });
            sendInterruptionEvent(true);
          }
        }, MUTE_DEBOUNCE_MS);
      }
      return;
    }

    // ── Jaw closed → consider unmuting ───────────────────────────────
    if (jawOpen < UNMUTE_THRESHOLD && isMutedRef.current) {
      // Cancel any pending mute
      if (muteTimerRef.current !== null) {
        clearTimeout(muteTimerRef.current);
        muteTimerRef.current = null;
      }
      // Start unmute timer if not already counting down
      if (unmuteTimerRef.current === null) {
        unmuteTimerRef.current = setTimeout(() => {
          unmuteTimerRef.current = null;
          if (jawOpen < UNMUTE_THRESHOLD) {
            isMutedRef.current = false;
            setIsInterrupted(false);
            postToIframe({ type: "unmute" });
            sendInterruptionEvent(false);
          }
        }, UNMUTE_DEBOUNCE_MS);
      }
      return;
    }

    // ── In-between zone (0.3 ≤ jawOpen ≤ 0.5) — cancel all timers ──
    if (muteTimerRef.current !== null) {
      clearTimeout(muteTimerRef.current);
      muteTimerRef.current = null;
    }
    if (unmuteTimerRef.current !== null) {
      clearTimeout(unmuteTimerRef.current);
      unmuteTimerRef.current = null;
    }
  }, [jawOpen, iframeContainerRef, conversationId]);

  return { isInterrupted };
}
