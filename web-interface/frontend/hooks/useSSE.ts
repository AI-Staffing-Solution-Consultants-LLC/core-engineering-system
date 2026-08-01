"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const SSE_URL = `${API_BASE}/api/telemetry`;
const POLL_URL = `${API_BASE}/api/telemetry/poll`;
const SSE_CONNECT_TIMEOUT = 10_000; // 10 s before fallback
const POLL_INTERVAL = 3_000; // 3 s
const RECONNECT_DELAY = 3_000; // 3 s

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface TelemetryEvent {
  type: string;
  healthy?: boolean;
  services?: Record<string, "ok" | "unreachable">;
  timestamp?: string;
  [key: string]: unknown;
}

export interface TelemetryState {
  healthy: boolean;
  services: Record<string, "ok" | "unreachable" | "unknown">;
  timestamp: string;
  events: TelemetryEvent[];
  lastHeartbeat: string | null;
}

const EMPTY_TELEMETRY: TelemetryState = {
  healthy: false,
  services: {},
  timestamp: "",
  events: [],
  lastHeartbeat: null,
};

// ---------------------------------------------------------------------------
// Poll service-name mapping: backend keys → dashboard names
// ---------------------------------------------------------------------------
const POLL_SERVICE_MAP: Record<string, string> = {
  sheryl: "sheryl",
  aura: "aura",
  malory: "malory",
  krieger: "krieger",
  selfRemediation: "self-remediation",
  telegram: "telegram-bridge",
  trackA: "track-a",
  trackB: "track-b",
  agencyAgents: "agency-agents",
};

function mergePollServices(
  backend: Record<string, "ok" | "unreachable">
): Record<string, "ok" | "unreachable" | "unknown"> {
  const out: Record<string, "ok" | "unreachable" | "unknown"> = {};
  for (const [key, label] of Object.entries(POLL_SERVICE_MAP)) {
    out[label] = (backend[key] as "ok" | "unreachable") ?? "unknown";
  }
  return out;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useSSE() {
  const [telemetry, setTelemetry] = useState<TelemetryState>(EMPTY_TELEMETRY);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mountedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- Polling fallback ---
  const startPolling = useCallback(() => {
    if (!mountedRef.current) return;

    setError("SSE unavailable — using polling fallback");

    const poll = () => {
      const token = localStorage.getItem("core_engine_session_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      fetch(POLL_URL, { headers })
        .then((res) => res.json())
        .then((data) => {
          if (!mountedRef.current) return;
          setConnected(true);
          setTelemetry((prev) => ({
            ...prev,
            healthy: data.healthy ?? prev.healthy,
            services: {
              ...prev.services,
              ...(data.services
                ? mergePollServices(data.services as Record<string, "ok" | "unreachable">)
                : {}),
            },
            timestamp: data.timestamp ?? prev.timestamp,
          }));
        })
        .catch(() => {
          // retry next interval
        });
    };

    poll(); // immediate first poll
    pollRef.current = setInterval(poll, POLL_INTERVAL);
  }, []);

  // --- Cleanup helpers ---
  const cleanUpConnections = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // --- Fetch-based SSE connection ---
  const connectSSE = useCallback(() => {
    if (!mountedRef.current) return;
    cleanUpConnections();

    const controller = new AbortController();
    abortRef.current = controller;

    const token = localStorage.getItem("core_engine_session_token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let didConnect = false;

    // Fallback timer — if no data within SSE_CONNECT_TIMEOUT, switch to polling
    connectTimeoutRef.current = setTimeout(() => {
      if (!didConnect && mountedRef.current) {
        controller.abort();
        startPolling();
      }
    }, SSE_CONNECT_TIMEOUT);

    fetch(SSE_URL, { signal: controller.signal, headers })
      .then(async (response) => {
        if (!response.ok) throw new Error(`SSE HTTP ${response.status}`);
        if (!response.body) throw new Error("SSE response has no body");

        didConnect = true;
        setConnected(true);
        setError(null);
        if (connectTimeoutRef.current) {
          clearTimeout(connectTimeoutRef.current);
          connectTimeoutRef.current = null;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (mountedRef.current) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data: ")) continue;

            const raw = trimmed.slice(6);
            try {
              const parsed: TelemetryEvent = JSON.parse(raw);

              // Flatten ledger batch events into individual entries for the dashboard
              let eventsToPush: TelemetryEvent[];
              if (
                parsed.type === "ledger" &&
                Array.isArray(parsed.entries) &&
                parsed.entries.length > 0
              ) {
                eventsToPush = (parsed.entries as TelemetryEvent[]).map(
                  (entry) => ({
                    type: "ledger",
                    id: typeof entry.id === "string" ? entry.id : "",
                    timestamp:
                      typeof entry.timestamp === "string"
                        ? entry.timestamp
                        : parsed.timestamp ?? new Date().toISOString(),
                    payload:
                      entry.payload ??
                      (entry as unknown as Record<string, unknown>),
                    chain_hash:
                      typeof entry.chain_hash === "string"
                        ? entry.chain_hash
                        : "",
                  })
                );
              } else {
                eventsToPush = [parsed];
              }

              setTelemetry((prev) => {
                const nextEvents = [...prev.events, ...eventsToPush].slice(
                  -200
                );
                const updates: Partial<TelemetryState> = { events: nextEvents };

                if (parsed.type === "heartbeat") {
                  updates.lastHeartbeat = new Date().toISOString();
                }

                if (typeof parsed.healthy === "boolean") {
                  updates.healthy = parsed.healthy;
                }

                if (parsed.services && typeof parsed.services === "object") {
                  updates.services = {
                    ...prev.services,
                    ...mergePollServices(
                      parsed.services as Record<string, "ok" | "unreachable">
                    ),
                  };
                }

                if (typeof parsed.timestamp === "string") {
                  updates.timestamp = parsed.timestamp;
                }

                return { ...prev, ...updates };
              });
            } catch {
              // Malformed JSON — skip line silently
            }
          }
        }
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        if (!mountedRef.current) return;

        setConnected(false);
        setError("Telemetry disconnected — reconnecting...");

        reconnectTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current) connectSSE();
        }, RECONNECT_DELAY);
      });
  }, [startPolling, cleanUpConnections]);

  // --- Manual reconnect (exposed) ---
  const reconnect = useCallback(() => {
    setError(null);
    connectSSE();
  }, [connectSSE]);

  // --- Mount / unmount ---
  useEffect(() => {
    mountedRef.current = true;
    connectSSE();

    return () => {
      mountedRef.current = false;
      cleanUpConnections();
    };
  }, [connectSSE, cleanUpConnections]);

  return { telemetry, connected, error, reconnect };
}
