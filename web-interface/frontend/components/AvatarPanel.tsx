"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { useFaceTracker, type Blendshapes } from "@/hooks/useFaceTracker";
import { useTavusBridge } from "@/hooks/useTavusBridge";
import { useInterruption } from "@/hooks/useInterruption";

/* ── Configuration ───────────────────────────────────────────────────────── */

const AVATAR_ROOM_URL =
  process.env.NEXT_PUBLIC_TAVUS_ROOM_URL ?? "";
const AVATAR_CONVERSATION_ID =
  process.env.NEXT_PUBLIC_TAVUS_CONVERSATION_ID ?? "";
const TAVUS_PERSONA_ID =
  process.env.NEXT_PUBLIC_TAVUS_PERSONA_ID ?? "";

/**
 * Dynamically import an ES module from a CDN URL at runtime.
 * Uses `new Function` to prevent webpack/Next.js from statically
 * analyzing the import and trying to bundle the remote module.
 */
function importFromCdn(url: string): Promise<unknown> {
  return new Function("url", "return import(url)")(url);
}

type AvatarStatus = "idle" | "connecting" | "connected" | "error";

/* ── Daily.co types (runtime CDN module — no npm types available) ────────── */

interface DailyCallObject {
  on(event: string, handler: (...args: unknown[]) => void): void;
  on(event: "error", handler: (e: DailyError) => void): void;
  on(event: "joined-meeting", handler: () => void): void;
  on(event: "left-meeting", handler: () => void): void;
  off(event: string, handler: (...args: unknown[]) => void): void;
  off(event: "error", handler: (e: DailyError) => void): void;
  off(event: "joined-meeting", handler: () => void): void;
  off(event: "left-meeting", handler: () => void): void;
  iframe(): HTMLIFrameElement | null;
  join(opts: { url: string }): Promise<void>;
  leave(): Promise<void>;
  destroy(): void;
  setLocalAudio(enabled: boolean): void;
}

interface DailyCallObjectInternal extends DailyCallObject {
  _handlers?: {
    onJoined: () => void;
    onLeft: () => void;
    onError: (e: unknown) => void;
  };
}

interface DailyError {
  errorMsg?: string;
  message?: string;
}

interface DailyIframeApi {
  createCallObject(config: { dailyConfig: Record<string, never> }): DailyCallObject;
  default: DailyIframeApi;
}

/* ── BlendshapeHUD sub-component ─────────────────────────────────────────── */

function BlendshapeHUD({ blendshapes }: { blendshapes: Blendshapes | null }) {
  if (!blendshapes) {
    return (
      <div className="flex flex-col gap-1.5 text-[11px] text-app-text-muted">
        <span className="font-mono uppercase tracking-wider text-[10px]">
          Perception idle
        </span>
      </div>
    );
  }

  const metrics: Array<{
    label: string;
    value: number;
    getter: (b: Blendshapes) => number;
  }> = [
    {
      label: "jawOpen",
      value: blendshapes.jawOpen ?? 0,
      getter: (b) => b.jawOpen ?? 0,
    },
    {
      label: "smile",
      value: Math.max(
        blendshapes.mouthSmileLeft ?? 0,
        blendshapes.mouthSmileRight ?? 0
      ),
      getter: (b) =>
        Math.max(b.mouthSmileLeft ?? 0, b.mouthSmileRight ?? 0),
    },
    {
      label: "brow",
      value:
        ((blendshapes.browDownLeft ?? 0) +
          (blendshapes.browDownRight ?? 0)) /
        2,
      getter: (b) =>
        ((b.browDownLeft ?? 0) + (b.browDownRight ?? 0)) / 2,
    },
    {
      label: "blink",
      value:
        ((blendshapes.eyeBlinkLeft ?? 0) +
          (blendshapes.eyeBlinkRight ?? 0)) /
        2,
      getter: (b) =>
        ((b.eyeBlinkLeft ?? 0) + (b.eyeBlinkRight ?? 0)) / 2,
    },
  ];

  return (
    <div className="flex flex-col gap-1.5">
      {metrics.map((m) => (
        <div key={m.label} className="flex items-center gap-2">
          <span className="w-10 font-mono text-[10px] uppercase tracking-wider text-app-text-muted">
            {m.label}
          </span>
          <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-app-bg">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-app-accent transition-all duration-150"
              style={{ width: `${Math.min(m.value * 100, 100)}%` }}
            />
          </div>
          <span className="w-8 text-right font-mono text-[10px] tabular-nums text-app-text-muted">
            {(m.value * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────────────────── */

export default function AvatarPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const iframeContainerRef = useRef<HTMLDivElement>(null);

  const [avatarStatus, setAvatarStatus] = useState<AvatarStatus>("idle");
  const [avatarError, setAvatarError] = useState<string | null>(null);

  // Face tracker
  const {
    blendshapes,
    isTracking,
    error: trackerError,
    start: startTracker,
    stop: stopTracker,
  } = useFaceTracker(canvasRef);

  // Tavus bridge
  const {
    isConnected: bridgeConnected,
    error: bridgeError,
    sendContext,
  } = useTavusBridge(AVATAR_CONVERSATION_ID || null);

  // Interruption: jawOpen-driven mute/unmute with debounce
  const jawOpen = blendshapes?.jawOpen ?? null;
  const { isInterrupted } = useInterruption({
    jawOpen,
    iframeContainerRef,
    conversationId: AVATAR_CONVERSATION_ID || null,
  });

  // Daily.co call object ref (for cleanup)
  const callObjectRef = useRef<DailyCallObjectInternal | null>(null);

  /* ── Bridge blendshapes to Tavus context ────────────────────────────── */

  useEffect(() => {
    if (blendshapes && isTracking) {
      sendContext(blendshapes);
    }
  }, [blendshapes, isTracking, sendContext]);

  /* ── Initialize Daily.co IFrame ─────────────────────────────────────── */

  const connectAvatar = useCallback(async () => {
    if (!AVATAR_ROOM_URL) {
      setAvatarStatus("error");
      setAvatarError("No avatar room URL configured");
      return;
    }

    setAvatarStatus("connecting");
    setAvatarError(null);

    try {
      const DailyModule = (await importFromCdn(
        "https://cdn.jsdelivr.net/npm/@daily-co/daily-js/+esm"
      )) as DailyIframeApi;
      const DailyIframe = DailyModule.default;

      const callObject = DailyIframe.createCallObject({
        dailyConfig: {},
      }) as DailyCallObjectInternal;
      callObjectRef.current = callObject;

      // Event handlers
      const onJoined = () => {
        setAvatarStatus("connected");
        setAvatarError(null);
      };

      const onLeft = () => {
        setAvatarStatus("idle");
      };

      const onError = (e: unknown) => {
        const err = e as DailyError;
        const msg =
          err?.errorMsg || err?.message || "Avatar connection lost";
        setAvatarStatus("error");
        setAvatarError(msg);
      };

      callObject.on("joined-meeting", onJoined);
      callObject.on("left-meeting", onLeft);
      callObject.on("error", onError);

      // Store handlers for cleanup
      callObject._handlers = { onJoined, onLeft, onError };

      // Share local audio for two-way communication
      callObject.setLocalAudio(true);

      // Create and insert iframe
      const iframe = callObject.iframe();
      if (iframe && iframeContainerRef.current) {
        iframe.setAttribute(
          "allow",
          "camera; microphone; autoplay; fullscreen"
        );
        iframe.setAttribute("allowfullscreen", "");
        iframe.style.width = "100%";
        iframe.style.height = "100%";
        iframe.style.border = "none";
        iframe.style.borderRadius = "inherit";
        iframe.style.backgroundColor = "#0f172a";

        // Clear any previous iframe
        iframeContainerRef.current.innerHTML = "";
        iframeContainerRef.current.appendChild(iframe);
      }

      // Join the room
      await callObject.join({ url: AVATAR_ROOM_URL });
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Avatar connection failed";
      setAvatarStatus("error");
      setAvatarError(message);
    }
  }, []);

  /* ── Disconnect Daily.co ────────────────────────────────────────────── */

  const disconnectAvatar = useCallback(async () => {
    const call = callObjectRef.current;
    if (!call) return;

    try {
      // Remove event handlers
      const handlers = call._handlers;
      if (handlers) {
        call.off("joined-meeting", handlers.onJoined);
        call.off("left-meeting", handlers.onLeft);
        call.off("error", handlers.onError);
      }

      await call.leave();
      call.destroy();
    } catch {
      // Best-effort cleanup
    }

    callObjectRef.current = null;

    // Clear iframe
    if (iframeContainerRef.current) {
      iframeContainerRef.current.innerHTML = "";
    }
  }, []);

  /* ── Lifecycle: connect on mount, disconnect on unmount ─────────────── */

  useEffect(() => {
    connectAvatar();
    return () => {
      disconnectAvatar();
    };
  }, [connectAvatar, disconnectAvatar]);

  /* ── Lifecycle: start face tracking on mount ────────────────────────── */

  useEffect(() => {
    startTracker();
    return () => {
      stopTracker();
    };
    // Only on mount/unmount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Combined error state ───────────────────────────────────────────── */

  const displayError = avatarError ?? trackerError ?? bridgeError;
  const errorLabel =
    (trackerError
      ? trackerError
      : avatarError
        ? avatarError
        : bridgeError)
    ?? null;

  const isConnecting = avatarStatus === "connecting";

  /* ── Render ─────────────────────────────────────────────────────────── */

  return (
    <div
      className={`relative flex h-full w-full flex-col bg-app-bg ${
        isInterrupted ? "ring-2 ring-red-500" : ""
      }`}
    >
      {/* ── Daily.co IFrame container (Tavus video) ──────────────────── */}
      <div
        ref={iframeContainerRef}
        className="absolute inset-0"
        aria-label="Tavus avatar video"
      />

      {/* ── Face mesh canvas overlay ─────────────────────────────────── */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 z-10"
        style={{ pointerEvents: "none" }}
        aria-hidden="true"
      />

      {/* ── Connecting spinner ───────────────────────────────────────── */}
      {isConnecting && !displayError && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-app-bg/60 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-app-border border-t-app-accent" />
            <span className="font-mono text-xs uppercase tracking-wider text-app-text-muted">
              Connecting avatar
            </span>
          </div>
        </div>
      )}

      {/* ── Error overlay ────────────────────────────────────────────── */}
      {displayError && !isConnecting && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-app-bg/80 backdrop-blur-sm">
          <div className="flex max-w-[240px] flex-col items-center gap-3 px-4 text-center">
            {/* X-circle icon */}
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#ef4444"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span className="text-sm font-medium text-red-400">
              {errorLabel}
            </span>
            <button
              onClick={() => {
                setAvatarError(null);
                connectAvatar();
              }}
              className="rounded-md border border-app-border px-4 py-2 font-mono text-xs uppercase tracking-wider text-app-accent transition-colors hover:border-app-accent hover:bg-app-accent/10"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* ── Tracking badge (top-right) ───────────────────────────────── */}
      {isTracking && !displayError && (
        <div className="absolute right-2 top-2 z-20 flex items-center gap-1.5 rounded-full border border-app-border bg-app-panel/90 px-2.5 py-1 backdrop-blur">
          <span
            className={`h-2 w-2 rounded-full ${
              bridgeConnected ? "bg-green-400" : "bg-app-accent"
            }`}
          />
          <span className="font-mono text-[10px] uppercase tracking-wider text-app-text-muted">
            {bridgeConnected ? "Live" : "Tracking"}
          </span>
        </div>
      )}

      {/* ── Blendshape HUD (bottom-left) ─────────────────────────────── */}
      <div className="absolute bottom-3 left-3 right-3 z-20 rounded-lg border border-app-border bg-app-panel/90 px-3 py-2.5 backdrop-blur">
        <BlendshapeHUD blendshapes={blendshapes} />
      </div>

      {/* ── Persona label (bottom-right) ──────────────────────────────── */}
      {TAVUS_PERSONA_ID && avatarStatus === "connected" && !displayError && (
        <div className="absolute bottom-3 right-3 z-20 rounded-full border border-app-border bg-app-panel/90 px-2.5 py-1 backdrop-blur">
          <span className="font-mono text-[10px] uppercase tracking-wider text-app-text-muted">
            {TAVUS_PERSONA_ID}
          </span>
        </div>
      )}
    </div>
  );
}
