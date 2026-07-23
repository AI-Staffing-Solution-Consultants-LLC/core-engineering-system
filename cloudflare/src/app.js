/**
 * Sheryl Dashboard — Orchestration Module
 *
 * Responsibilities:
 *   - Quadrant show/hide toggling
 *   - WebRTC video widget lifecycle
 *   - Live clock + status indicator
 *   - Mission Control telemetry fetcher placeholder
 *
 * No frameworks. No hardcoded secrets. Exported for testability.
 */

import { initVideoWidget } from './video-widget.js';

// ── Module-level video widget instance ─────────────────────────────────────

let _videoWidget = null;

// ── Public API (exported for tests) ────────────────────────────────────────

/**
 * Toggle visibility of a dashboard quadrant by its element id.
 * @param {string} quadrantId — DOM id of the quadrant section
 */
export function toggleQuadrant(quadrantId) {
  const el = document.getElementById(quadrantId);
  if (!el) return;
  el.classList.toggle("hidden");
}

/**
 * Init a WebRTC video connection via the real video widget.
 * Unified entry point — replaces the previous simulated placeholder.
 * @returns {{ status: string }} — current connection status
 */
export function initWebRTC() {
  if (!_videoWidget) {
    _videoWidget = initVideoWidget();
  }
  _videoWidget.connect();
  return { status: 'connecting' };
}

/**
 * Disconnect WebRTC and reset UI state.
 * @returns {{ status: string }}
 */
export function disconnectWebRTC() {
  if (_videoWidget) {
    _videoWidget.disconnect();
  }
  return { status: 'disconnected' };
}

/**
 * Update the header clock to current time.
 */
export function tickClock() {
  const el = document.getElementById("header-time");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

/**
 * Set system status indicator.
 * @param {"online"|"offline"} status
 */
export function setSystemStatus(status) {
  const dot = document.getElementById("status-dot");
  const label = document.getElementById("status-label");
  if (!dot || !label) return;

  if (status === "online") {
    dot.classList.remove("offline");
    label.textContent = "System Online";
  } else {
    dot.classList.add("offline");
    label.textContent = "Offline";
  }
}

/**
 * Update a mission-control stat card by its element id.
 * @param {string} statId — element id for the stat-delta span
 * @param {string} valueText — new .stat-value text
 * @param {string} deltaText — new .stat-delta text
 * @param {"up"|"down"|"neutral"} deltaClass — CSS class for delta indicator
 */
export function updateStat(statId, valueText, deltaText, deltaClass) {
  const deltaEl = document.getElementById(statId);
  if (!deltaEl) return;

  const card = deltaEl.closest(".stat-card");
  if (!card) return;

  const valueEl = card.querySelector(".stat-value");
  if (valueEl) valueEl.textContent = valueText;

  deltaEl.textContent = deltaText;
  deltaEl.classList.remove("delta-up", "delta-down", "delta-neutral");
  deltaEl.classList.add(`delta-${deltaClass}`);
}

// ── Bootstrap (runs after DOMContentLoaded) ───────────────────────────────

function bootstrap() {
  // Clock
  tickClock();
  setInterval(tickClock, 1000);

  // System status
  setSystemStatus("online");

  // Initialize video widget (lazy — connect on user click)
  _videoWidget = initVideoWidget();

  // WebRTC connect button
  const connectBtn = document.getElementById("btn-video-connect");
  if (connectBtn) {
    connectBtn.addEventListener("click", () => {
      _videoWidget.connect();
      connectBtn.disabled = true;
    });
  }

  // WebRTC disconnect button
  const disconnectBtn = document.getElementById("btn-video-disconnect");
  if (disconnectBtn) {
    disconnectBtn.addEventListener("click", () => {
      _videoWidget.disconnect();
      if (connectBtn) connectBtn.disabled = false;
    });
  }

  // Video hide button
  const hideVideoBtn = document.getElementById("btn-video-hide");
  if (hideVideoBtn) {
    hideVideoBtn.addEventListener("click", () => {
      toggleQuadrant("quadrant-video");
      hideVideoBtn.textContent =
        hideVideoBtn.textContent === "Hide Panel" ? "Show Panel" : "Hide Panel";
    });
  }

  // Mission hide button
  const hideMissionBtn = document.getElementById("btn-mission-hide");
  if (hideMissionBtn) {
    hideMissionBtn.addEventListener("click", () => {
      toggleQuadrant("quadrant-mission");
      hideMissionBtn.textContent =
        hideMissionBtn.textContent === "Hide Panel" ? "Show Panel" : "Hide Panel";
    });
  }

  // Browsing hide button
  const hideBrowsingBtn = document.getElementById("btn-browsing-hide");
  if (hideBrowsingBtn) {
    hideBrowsingBtn.addEventListener("click", () => {
      toggleQuadrant("quadrant-browsing");
      hideBrowsingBtn.textContent =
        hideBrowsingBtn.textContent === "Hide Panel" ? "Show Panel" : "Hide Panel";
    });
  }
}

// ── Entry point ────────────────────────────────────────────────────────────

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
}
