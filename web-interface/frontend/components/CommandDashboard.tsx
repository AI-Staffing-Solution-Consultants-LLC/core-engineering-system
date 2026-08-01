"use client";

import { useState, type FormEvent } from "react";
import { useSSE } from "@/hooks/useSSE";
import { useCommand, type CommandStep } from "@/hooks/useCommand";

// ---------------------------------------------------------------------------
// Services — known agent/service names with ports
// ---------------------------------------------------------------------------
interface ServiceDef {
  name: string;
  port: number;
}

const SERVICES: ServiceDef[] = [
  { name: "sheryl", port: 8083 },
  { name: "aura", port: 8084 },
  { name: "malory", port: 8085 },
  { name: "krieger", port: 8086 },
  { name: "self-remediation", port: 8087 },
  { name: "telegram-bridge", port: 8088 },
  { name: "track-a", port: 8080 },
  { name: "track-b", port: 8081 },
  { name: "agency-agents", port: 8082 },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function statusDot(
  status: "ok" | "unreachable" | "unknown"
): string {
  if (status === "ok") return "bg-emerald-500";
  if (status === "unreachable") return "bg-red-500";
  return "bg-gray-600";
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function stepSummary(step: CommandStep, idx: number): string {
  const action = step.action ?? `Step ${idx + 1}`;
  const tool = step.tool ?? "";
  const status = step.status ?? "";
  const parts = [action];
  if (tool) parts.push(`(${tool})`);
  if (status) parts.push(`[${status}]`);
  return parts.join(" ");
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function CommandDashboard() {
  // --- Hooks ---
  const { telemetry, connected, error: sseError, reconnect: reconnectSSE } = useSSE();
  const { send, response, loading, error: cmdError } = useCommand();

  // --- Local state ---
  const [query, setQuery] = useState("");

  const canSend = query.trim().length > 0 && !loading;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSend) return;
    send(query);
  }

  // --- Derived data ---
  const serviceStatuses: Record<string, "ok" | "unreachable" | "unknown"> = {};
  for (const svc of SERVICES) {
    serviceStatuses[svc.name] = telemetry.services[svc.name] ?? "unknown";
  }

  // Ledger-like events — extract events with known types from the event stream
  const ledgerEvents = telemetry.events.filter(
    (e) =>
      typeof e.type === "string" &&
      typeof e.timestamp === "string"
  );
  const recentLedger = ledgerEvents.slice(-20).reverse();

  // === RENDER ===
  return (
    <div className="flex h-full w-full">
      {/* ── LEFT PANEL (40%) — Command Center ──────────────── */}
      <div className="flex-[4] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="shrink-0 border-b border-app-border px-4 py-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-app-accent">
            Command Center
          </h2>
        </div>

        {/* Command input */}
        <form onSubmit={handleSubmit} className="shrink-0 px-4 pt-3 pb-2 space-y-3">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder='Describe the problem — e.g. "why is latency high"'
            rows={3}
            className="w-full resize-none rounded-md border border-app-border
                       bg-app-bg px-3 py-2.5 text-sm text-app-text
                       font-mono placeholder:text-gray-500
                       focus:border-app-accent focus:shadow-[0_0_0_3px_rgba(34,211,238,0.13)]
                       disabled:opacity-50"
            disabled={loading}
          />

          <button
            type="submit"
            disabled={!canSend}
            className="w-full rounded-md bg-app-accent px-4 py-2.5 text-sm
                       font-semibold text-app-bg transition-colors
                       hover:bg-app-accent-hover
                       disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </form>

        {/* Response area — scrollable fill */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          {/* Command error */}
          {cmdError && (
            <div className="mt-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2.5">
              <p className="text-sm font-medium text-red-400">{cmdError}</p>
            </div>
          )}

          {/* Loading indicator */}
          {loading && !cmdError && (
            <div className="mt-4 flex items-center gap-2 text-sm text-app-text-muted">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-app-accent border-t-transparent" />
              Sending query to Sheryl...
            </div>
          )}

          {/* Response content */}
          {response && !loading && (
            <div className="mt-3 space-y-3">
              {/* plan_id */}
              <div className="rounded-md border border-app-border bg-app-bg/60 px-3 py-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-app-text-muted">
                  Plan
                </span>
                <p className="mt-0.5 font-mono text-sm text-app-accent break-all">
                  {response.plan_id}
                </p>
              </div>

              {/* Hypothesis */}
              {response.hypothesis && (
                <div className="rounded-md border border-app-border bg-app-bg/60 px-3 py-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-app-text-muted">
                    Hypothesis
                  </span>
                  <p className="mt-0.5 text-sm text-app-text">{response.hypothesis}</p>
                </div>
              )}

              {/* Steps */}
              {response.steps.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-app-text-muted">
                    Steps ({response.steps.length})
                  </span>

                  {response.steps.map((step, idx) => (
                    <details
                      key={`${response.plan_id}-${idx}`}
                      className="group rounded-md border border-app-border bg-app-bg/60"
                    >
                      <summary className="cursor-pointer px-3 py-2 text-sm text-app-text select-none">
                        <span className="font-mono text-xs text-app-text-muted mr-2">
                          #{idx + 1}
                        </span>
                        {stepSummary(step, idx)}
                      </summary>

                      <div className="border-t border-app-border px-3 py-2 space-y-1.5">
                        {step.tool && (
                          <div className="text-xs">
                            <span className="text-app-text-muted">Tool: </span>
                            <span className="font-mono text-app-accent">{step.tool}</span>
                          </div>
                        )}

                        {step.args && step.args.length > 0 && (
                          <div className="text-xs">
                            <span className="text-app-text-muted">Args: </span>
                            <span className="font-mono text-app-text">
                              {step.args.join(", ")}
                            </span>
                          </div>
                        )}

                        {step.result && (
                          <div className="mt-1 rounded bg-app-bg px-2 py-1.5">
                            {step.result.output && (
                              <pre className="whitespace-pre-wrap break-all font-mono text-xs text-app-text-muted">
                                {step.result.output}
                              </pre>
                            )}
                            {step.result.exit_code !== undefined && (
                              <div className="text-xs">
                                <span className="text-app-text-muted">Exit: </span>
                                <span
                                  className={
                                    step.result.exit_code === 0
                                      ? "text-emerald-400"
                                      : "text-red-400"
                                  }
                                >
                                  {step.result.exit_code}
                                </span>
                              </div>
                            )}
                            {step.result.error && (
                              <div className="text-xs text-red-400">
                                {step.result.error}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              )}

              {/* No steps */}
              {response.steps.length === 0 && (
                <p className="text-sm text-app-text-muted italic">No action steps returned.</p>
              )}
            </div>
          )}

          {/* Empty state — no response, no error, not loading */}
          {!response && !cmdError && !loading && (
            <p className="mt-4 text-xs text-app-text-muted italic">
              Enter a query and press Send to dispatch it to Sheryl.
            </p>
          )}
        </div>
      </div>

      {/* ── RIGHT PANEL (60%) — Monitoring ─────────────────── */}
      <div className="flex-[6] flex flex-col overflow-hidden border-l border-app-border">
        {/* Header */}
        <div className="shrink-0 border-b border-app-border px-4 py-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-app-accent">
            Monitoring
          </h2>

          {/* Connection status */}
          <div className="flex items-center gap-2">
            {sseError && (
              <button
                onClick={reconnectSSE}
                className="text-xs text-app-accent hover:text-app-accent-hover transition-colors"
              >
                Retry
              </button>
            )}
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                connected ? "bg-emerald-500" : "bg-gray-600"
              }`}
            />
            <span className="text-xs text-app-text-muted">
              {connected ? "Connected" : sseError ? "Disconnected" : "Connecting..."}
            </span>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
          {/* === SERVICE HEALTH GRID === */}
          <section>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-app-text-muted">
              Service Health
            </h3>

            <div className="grid grid-cols-3 gap-2">
              {SERVICES.map((svc) => {
                const status = serviceStatuses[svc.name] ?? "unknown";
                return (
                  <div
                    key={svc.name}
                    className="flex items-center gap-2 rounded-md border border-app-border
                               bg-app-bg/60 px-2.5 py-2"
                  >
                    {/* Dot */}
                    <span
                      className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${statusDot(status)}`}
                    />
                    {/* Name */}
                    <div className="min-w-0 flex-1">
                      <span className="block truncate text-xs text-app-text">
                        {svc.name}
                      </span>
                      <span className="block truncate text-[10px] text-app-text-muted font-mono">
                        :{svc.port}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* === AGENT STATUS === */}
          <section>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-app-text-muted">
              Agent Status
            </h3>

            <div className="space-y-2">
              {/* Sheryl */}
              <div className="flex items-center justify-between rounded-md border border-app-border bg-app-bg/60 px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2.5 w-2.5 rounded-full ${
                      statusDot(serviceStatuses.sheryl ?? "unknown")
                    }`}
                  />
                  <span className="text-sm text-app-text">Sheryl</span>
                </div>
                <span className="text-xs text-app-text-muted font-mono">
                  {serviceStatuses.sheryl ?? "unknown"}
                </span>
              </div>

              {/* Telegram Bridge */}
              <div className="flex items-center justify-between rounded-md border border-app-border bg-app-bg/60 px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2.5 w-2.5 rounded-full ${
                      statusDot(serviceStatuses["telegram-bridge"] ?? "unknown")
                    }`}
                  />
                  <span className="text-sm text-app-text">Telegram Bridge</span>
                </div>
                <span className="text-xs text-app-text-muted font-mono">
                  {serviceStatuses["telegram-bridge"] ?? "unknown"}
                </span>
              </div>
            </div>
          </section>

          {/* === LATEST EVENTS (LEDGER) === */}
          <section>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-app-text-muted">
              Latest Events
            </h3>

            {recentLedger.length === 0 ? (
              <p className="text-xs text-app-text-muted italic">
                No events received yet — waiting for telemetry stream.
              </p>
            ) : (
              <div className="max-h-40 overflow-y-auto space-y-1 rounded-md border border-app-border bg-app-bg/60 p-2">
                {recentLedger.map((event, i) => {
                  // Extract known fields safely despite index-signature unknowns
                  const rawType = String(event.type ?? "");
                  const rawTs = typeof event.timestamp === "string" ? event.timestamp : "";
                  const rawId = typeof event.id === "string" ? event.id : "";
                  const rawPayload =
                    event.payload && typeof event.payload === "object"
                      ? (event.payload as Record<string, unknown>)
                      : null;

                  return (
                    <div
                      key={rawId || `evt-${i}`}
                      className="flex items-center gap-2 rounded px-2 py-1.5 text-xs"
                    >
                      <span className="shrink-0 font-mono text-[10px] text-app-text-muted">
                        {rawTs ? formatTime(rawTs) : "--:--:--"}
                      </span>
                      <span className="shrink-0 rounded bg-app-accent/15 px-1.5 py-0.5 font-mono text-[10px] text-app-accent">
                        {rawType}
                      </span>
                      {rawPayload ? (
                        <span className="min-w-0 flex-1 truncate text-app-text-muted">
                          {JSON.stringify(rawPayload)}
                        </span>
                      ) : rawId ? (
                        <span className="min-w-0 flex-1 truncate text-app-text-muted">
                          #{rawId.slice(0, 8)}
                        </span>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Last telemetry timestamp */}
          {telemetry.timestamp && (
            <p className="text-[10px] text-app-text-muted text-right">
              Last poll: {formatTime(telemetry.timestamp)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
