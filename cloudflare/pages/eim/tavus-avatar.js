/**
 * Tavus Avatar — Client-Side WebRTC Video Module
 * ==================================================
 * Creates an embedded Daily.co IFrame for Tavus CVI 2-way video.
 * Uses the Daily IFrame API (@daily-co/daily-js) via CDN.
 * No framework dependencies. Vanilla ES module.
 *
 * @module tavus-avatar
 * @exports TavusAvatar (default)
 *
 * Usage:
 *   import TavusAvatar from './tavus-avatar.js';
 *   const avatar = new TavusAvatar({ containerId: 'avatar-container' });
 *   avatar.addEventListener('status', (e) => console.log(e.detail));
 *   await avatar.connect(conversationUrl);
 *   // ... later ...
 *   avatar.disconnect();
 */

/* ── Events dispatched by TavusAvatar ──────────────────────────────────── */

const STATUS_EVENT = 'status';
const STATUS_CONNECTING = 'connecting';
const STATUS_CONNECTED = 'connected';
const STATUS_DISCONNECTED = 'disconnected';
const STATUS_ERROR = 'error';

/* ── TavusAvatar Class ──────────────────────────────────────────────────── */

export default class TavusAvatar extends EventTarget {
  /**
   * @param {Object} config
   * @param {string} config.containerId — DOM element id where the iframe is inserted
   */
  constructor(config = {}) {
    super();

    this.containerId = config.containerId || 'avatar-container';
    this._callObject = null;
    this._iframeEl = null;
    this._status = STATUS_DISCONNECTED;
    this._boundHandlers = null;
  }

  /* ── Public API ──────────────────────────────────────────────────────── */

  /**
   * Connect to a Tavus conversation room via Daily.co IFrame.
   * Creates the iframe, loads Daily API, joins the room.
   *
   * @param {string} conversationUrl — Daily.co room URL from Tavus API
   * @returns {Promise<void>}
   */
  async connect(conversationUrl) {
    if (this._callObject) {
      console.warn('[TavusAvatar] Already connected — disconnecting first.');
      await this.disconnect();
    }

    if (!conversationUrl) {
      this._dispatchStatus(STATUS_ERROR, { message: 'No conversation URL provided' });
      return;
    }

    this._dispatchStatus(STATUS_CONNECTING);

    try {
      // Dynamically import Daily IFrame API from CDN
      const DailyModule = await import(
        'https://cdn.jsdelivr.net/npm/@daily-co/daily-js/+esm'
      );
      const DailyIframe = DailyModule.default;

      // Create the Daily call object
      this._callObject = DailyIframe.createCallObject({
        dailyConfig: {},
      });

      // Bind event handlers
      this._boundHandlers = {
        'joined-meeting': () => {
          console.log('[TavusAvatar] Joined meeting');
          this._status = STATUS_CONNECTED;
          this._dispatchStatus(STATUS_CONNECTED, { conversationUrl });
        },
        'left-meeting': () => {
          console.log('[TavusAvatar] Left meeting');
          this._status = STATUS_DISCONNECTED;
          this._cleanupIframe();
          this._dispatchStatus(STATUS_DISCONNECTED);
        },
        error: (e) => {
          console.error('[TavusAvatar] Daily error:', e);
          this._dispatchStatus(STATUS_ERROR, {
            message: e.errorMsg || e.message || 'Daily.co connection error',
            detail: e,
          });
        },
      };

      Object.entries(this._boundHandlers).forEach(([event, handler]) => {
        this._callObject.on(event, handler);
      });

      // Share local audio for two-way communication
      this._callObject.setLocalAudio(true);

      // Insert the iframe into the container
      this._createIframe();

      // Join the Tavus conversation room
      await this._callObject.join({ url: conversationUrl });
    } catch (err) {
      console.error('[TavusAvatar] Connection failed:', err);
      this._dispatchStatus(STATUS_ERROR, {
        message: err.message || 'Failed to connect to Tavus conversation',
      });
      this._cleanupIframe();
    }
  }

  /**
   * Disconnect from the conversation and clean up.
   * @returns {Promise<void>}
   */
  async disconnect() {
    if (this._callObject) {
      try {
        // Remove event listeners
        if (this._boundHandlers) {
          Object.entries(this._boundHandlers).forEach(([event, handler]) => {
            this._callObject.off(event, handler);
          });
          this._boundHandlers = null;
        }

        // Leave the meeting
        await this._callObject.leave();
        this._callObject.destroy();
      } catch (err) {
        console.warn('[TavusAvatar] Error during disconnect:', err.message);
      }
      this._callObject = null;
    }

    this._status = STATUS_DISCONNECTED;
    this._cleanupIframe();
    this._dispatchStatus(STATUS_DISCONNECTED);
  }

  /**
   * Returns the current connection state.
   * @returns {string} — "connecting" | "connected" | "disconnected" | "error"
   */
  getStatus() {
    return this._status;
  }

  /* ── Iframe Management ───────────────────────────────────────────────── */

  _createIframe() {
    const container = document.getElementById(this.containerId);
    if (!container) {
      console.error('[TavusAvatar] Container not found:', this.containerId);
      return;
    }

    // If an iframe from a previous call still exists, remove it
    this._cleanupIframe();

    // Create the iframe for the Daily call object
    this._iframeEl = this._callObject.iframe();
    if (this._iframeEl) {
      this._iframeEl.setAttribute('allow', 'camera; microphone; autoplay; fullscreen');
      this._iframeEl.setAttribute('allowfullscreen', '');
      this._iframeEl.style.width = '100%';
      this._iframeEl.style.height = '100%';
      this._iframeEl.style.border = 'none';
      this._iframeEl.style.borderRadius = 'inherit';
      this._iframeEl.style.backgroundColor = 'var(--color-bg, #0f131c)';

      container.appendChild(this._iframeEl);
    }
  }

  _cleanupIframe() {
    if (this._iframeEl && this._iframeEl.parentNode) {
      this._iframeEl.parentNode.removeChild(this._iframeEl);
    }
    this._iframeEl = null;
  }

  /* ── Event Helpers ───────────────────────────────────────────────────── */

  _dispatchStatus(status, detail = {}) {
    this.dispatchEvent(
      new CustomEvent(STATUS_EVENT, {
        detail: { status, ...detail },
      })
    );
  }
}
