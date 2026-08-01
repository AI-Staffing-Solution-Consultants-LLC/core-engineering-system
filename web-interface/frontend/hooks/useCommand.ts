"use client";

import { useState, useCallback, useRef } from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const COMMAND_URL = `${API_BASE}/api/command`;
const SESSION_KEY = "core_engine_session_token";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface CommandStep {
  action: string;
  tool?: string;
  args?: string[];
  result?: {
    output?: string;
    exit_code?: number;
    error?: string;
  };
  status?: string;
  [key: string]: unknown;
}

export interface CommandResponse {
  plan_id: string;
  query?: string;
  hypothesis?: string;
  steps: CommandStep[];
  status?: string;
}

// ---------------------------------------------------------------------------
// Error mapping
// ---------------------------------------------------------------------------
function mapError(status: number): string {
  switch (status) {
    case 400:
      return "Missing or invalid query";
    case 401:
      return "Authentication required";
    case 502:
      return "Sheryl unreachable";
    case 504:
      return "Request timed out";
    default:
      return `Unexpected error (${status})`;
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useCommand() {
  const [response, setResponse] = useState<CommandResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(async (query: string) => {
    // Abort any in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const trimmed = query.trim();
    if (!trimmed) {
      setError("Query cannot be empty");
      return;
    }

    // Clear previous
    setResponse(null);
    setError(null);
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const token = localStorage.getItem(SESSION_KEY);
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(COMMAND_URL, {
        method: "POST",
        headers,
        body: JSON.stringify({ query: trimmed }),
        signal: controller.signal,
      });

      if (!res.ok) {
        let detail = "";
        try {
          const body = await res.json();
          detail = typeof body.detail === "string" ? body.detail : "";
        } catch {
          // no response body
        }
        const msg = mapError(res.status);
        setError(detail ? `${msg} — ${detail}` : msg);
        setLoading(false);
        return;
      }

      const data: CommandResponse = await res.json();
      setResponse(data);
      setLoading(false);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(
        err instanceof TypeError
          ? "Connection failed — check network and API URL"
          : "Connection failed"
      );
      setLoading(false);
    }
  }, []);

  return { send, response, loading, error };
}
