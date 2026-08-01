"use client";

import { useState, useEffect, useRef, type FormEvent } from "react";

interface AuthResponse {
  authenticated: boolean;
  token?: string;
  error?: string;
}

interface TokenPayload {
  exp: number;
}

const SESSION_KEY = "core_engine_session_token";

function decodeToken(token: string): TokenPayload | null {
  try {
    const json = atob(token);
    return JSON.parse(json) as TokenPayload;
  } catch {
    return null;
  }
}

function isTokenValid(token: string): boolean {
  const payload = decodeToken(token);
  if (!payload || typeof payload.exp !== "number") return false;
  return payload.exp > Date.now();
}

export default function PasswordGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check for existing valid token on mount
  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored && isTokenValid(stored)) {
      setAuthenticated(true);
    }
    setChecking(false);
  }, []);

  // Focus input when gate is shown
  useEffect(() => {
    if (!authenticated && !checking && inputRef.current) {
      inputRef.current.focus();
    }
  }, [authenticated, checking]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    const trimmed = password.trim();
    if (!trimmed) {
      setError(true);
      return;
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
      const response = await fetch(`${apiUrl}/api/auth`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: trimmed }),
      });

      if (!response.ok) {
        setError(true);
        setPassword("");
        return;
      }

      const data: AuthResponse = await response.json();

      if (data.authenticated && data.token) {
        localStorage.setItem(SESSION_KEY, data.token);
        setAuthenticated(true);
        setPassword("");
      } else {
        setError(true);
        setPassword("");
      }
    } catch {
      setError(true);
      setPassword("");
    }
  }

  // Still checking local storage — render nothing
  if (checking) return null;

  // Authenticated — show children
  if (authenticated) return <>{children}</>;

  // Show password gate
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-app-bg">
      <div className="w-full max-w-sm rounded-xl border border-app-border bg-app-panel p-10 text-center shadow-lg">
        {/* Icon */}
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-800 to-app-accent text-lg font-bold text-app-bg shadow-[0_0_24px_rgba(34,211,238,0.13)]">
          &#x25C6;
        </div>

        <h1 className="mb-1 text-xl font-semibold text-app-text">
          Core Engineering System
        </h1>
        <p className="mb-6 text-sm text-app-text-muted">
          Enter access password to continue
        </p>

        <form onSubmit={handleSubmit}>
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (error) setError(false);
              }}
              placeholder="Password"
              className="flex-1 rounded-md border border-app-border bg-app-bg px-4 py-3 text-base text-app-text transition-colors placeholder:text-gray-500 focus:border-app-accent focus:shadow-[0_0_0_3px_rgba(34,211,238,0.13)]"
            />
            <button
              type="submit"
              className="rounded-md bg-app-accent px-6 py-3 font-semibold text-app-bg transition-colors hover:bg-app-accent-hover"
            >
              Unlock
            </button>
          </div>

          <div
            className={`mt-3 min-h-[20px] text-sm text-red-400 transition-opacity ${
              error ? "opacity-100" : "opacity-0"
            }`}
          >
            Access denied
          </div>
        </form>
      </div>
    </div>
  );
}
