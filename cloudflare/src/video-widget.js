/**
 * Video Widget — WebRTC client for Sheryl Dashboard
 *
 * Connects to the webrtc-signaling Cloudflare Worker for peer-to-peer
 * video via HTTP-based signaling (offer/answer/ICE relay).
 *
 * Endpoints (from cloudflare/workers/webrtc-signaling.js):
 *   POST /offer               → store SDP offer, returns { sessionId, state }
 *   POST /answer?session=X     → store SDP answer
 *   POST /ice?session=X        → relay ICE candidate
 *   GET  /session/{id}         → retrieve full session state
 *
 * No hardcoded URLs — signaling URL read from config.
 * No secrets stored in source.
 *
 * Exports:
 *   initVideoWidget(options)   → factory, returns { connect, disconnect }
 *   getVideoWidgetStatus()     → current connection status string
 */

// ── Configuration ──────────────────────────────────────────────────────────

const DEFAULT_ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
];

const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_BASE_DELAY = 1000;      // ms, doubled each attempt
const SESSION_POLL_INTERVAL = 1500;     // ms between /session polls
const SESSION_POLL_TIMEOUT = 120_000;   // max 2 min waiting for answer

// ── Module-level state ─────────────────────────────────────────────────────

const _state = {
  status: 'disconnected',       // connecting | connected | disconnected | failed
  sessionId: null,
  peerConnection: null,
  localStream: null,
  remoteStream: null,
  reconnectAttempts: 0,
  pollTimer: null,
  pollStartTime: 0,
  processedIceIdx: 0,           // track remote ICE candidates already applied
  hadRemoteAnswer: false,       // track whether we've consumed the answer
};

let _config = {
  signalingUrl: '',
};

// ── DOM helpers ────────────────────────────────────────────────────────────

function $(id) {
  return document.getElementById(id);
}

function _readConfig() {
  const bodyUrl = document.body?.dataset?.signalingUrl;
  if (bodyUrl) _config.signalingUrl = bodyUrl;
}

function _updateBadge(text, cls) {
  const badge = $('video-badge');
  if (!badge) return;
  badge.textContent = text;
  badge.classList.remove('badge-offline', 'badge-live', 'badge-idle');
  if (cls) badge.classList.add(cls);
}

function _updateStatusText(text) {
  const el = $('video-status');
  if (el) el.textContent = text;
}

function _showLocalVideo(stream) {
  const localVideo = $('video-local');
  const container = $('video-container');
  const placeholder = $('video-placeholder');

  if (localVideo) {
    localVideo.srcObject = stream;
    localVideo.classList.remove('hidden');
  }
  if (container) container.classList.remove('hidden');
  if (placeholder) placeholder.classList.add('hidden');
}

function _showRemoteVideo(stream) {
  const remoteVideo = $('video-remote');
  if (remoteVideo) {
    remoteVideo.srcObject = stream;
    remoteVideo.classList.remove('hidden');
  }
}

function _hideVideos() {
  const containers = [$('video-local'), $('video-remote'), $('video-container')];
  const placeholder = $('video-placeholder');

  for (const el of containers) {
    if (el) {
      el.classList.add('hidden');
      if (el.tagName === 'VIDEO') el.srcObject = null;
    }
  }
  if (placeholder) placeholder.classList.remove('hidden');
}

// ── Signaling (HTTP ↔ Worker) ─────────────────────────────────────────────

async function _postOffer(sdp) {
  if (!_config.signalingUrl) {
    throw new Error('signalingUrl not configured');
  }
  const resp = await fetch(`${_config.signalingUrl}/offer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sdp }),
  });
  if (!resp.ok) throw new Error(`POST /offer failed: ${resp.status}`);
  return resp.json();
}

async function _pollSession() {
  if (!_state.sessionId || !_config.signalingUrl) return null;
  const resp = await fetch(`${_config.signalingUrl}/session/${_state.sessionId}`);
  if (!resp.ok) return null;
  return resp.json();
}

async function _postIce(candidate) {
  if (!_state.sessionId || !_config.signalingUrl) return;
  try {
    await fetch(`${_config.signalingUrl}/ice?session=${_state.sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate, from: 'offerer' }),
    });
  } catch {
    // ICE failing is non-fatal
  }
}

async function _applyRemoteAnswer(state) {
  if (!state?.answer?.sdp) return false;
  if (_state.hadRemoteAnswer) return false;

  const answerDesc = new RTCSessionDescription({
    type: 'answer',
    sdp: state.answer.sdp,
  });
  await _state.peerConnection.setRemoteDescription(answerDesc);
  _state.hadRemoteAnswer = true;
  return true;
}

async function _applyRemoteIceCandidates(state) {
  if (!Array.isArray(state?.iceCandidates)) return;
  const candidates = state.iceCandidates;

  for (let i = _state.processedIceIdx; i < candidates.length; i++) {
    const entry = candidates[i];
    // Only consume candidates from the answerer (remote peer)
    if (entry.from !== 'answerer') continue;
    try {
      const ice = new RTCIceCandidate(entry.candidate);
      await _state.peerConnection.addIceCandidate(ice);
      _state.processedIceIdx = i + 1;
    } catch {
      // Malformed candidate — skip
      _state.processedIceIdx = i + 1;
    }
  }
}

// ── Session polling loop ──────────────────────────────────────────────────

function _startPolling() {
  _stopPolling();
  _state.pollStartTime = Date.now();

  _state.pollTimer = setInterval(async () => {
    // Timeout check
    if (Date.now() - _state.pollStartTime > SESSION_POLL_TIMEOUT) {
      _stopPolling();
      _setStatus('failed', 'Remote peer timeout — no answer received');
      return;
    }

    try {
      const data = await _pollSession();
      if (!data?.state) return;

      // Check for answer
      const gotAnswer = await _applyRemoteAnswer(data.state);
      if (gotAnswer) {
        _setStatus('connected', 'Connected');
      }

      // Check for remote ICE candidates
      await _applyRemoteIceCandidates(data.state);

    } catch {
      // Poll error — will retry next interval
    }
  }, SESSION_POLL_INTERVAL);
}

function _stopPolling() {
  if (_state.pollTimer) {
    clearInterval(_state.pollTimer);
    _state.pollTimer = null;
  }
}

// ── Reconnection ───────────────────────────────────────────────────────────

function _getReconnectDelay() {
  return RECONNECT_BASE_DELAY * Math.pow(2, _state.reconnectAttempts);
}

async function _attemptReconnect() {
  if (_state.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    _setStatus('failed', 'Max reconnection attempts reached');
    return;
  }

  const delay = _getReconnectDelay();
  _state.reconnectAttempts += 1;
  _updateStatusText(`Reconnecting (${_state.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}) in ${Math.round(delay / 1000)}s…`);

  await new Promise((r) => setTimeout(r, delay));

  if (_state.status !== 'disconnected') return; // user cancelled during wait

  try {
    await _fullConnect();
  } catch (err) {
    // Will retry via connectionstatechange handler or give up
  }
}

// ── Status management ──────────────────────────────────────────────────────

function _setStatus(status, label) {
  _state.status = status;
  const badgeMap = {
    connecting: ['badge-idle', 'Connecting…'],
    connected: ['badge-live', 'Connected'],
    disconnected: ['badge-offline', 'Disconnected'],
    failed: ['badge-offline', 'Failed'],
  };
  const [cls, text] = badgeMap[status] || ['badge-idle', status];
  _updateBadge(label || text, cls);
}

// ── PeerConnection lifecycle ───────────────────────────────────────────────

async function _createPeerConnection(stream) {
  const pc = new RTCPeerConnection({
    iceServers: DEFAULT_ICE_SERVERS,
  });

  // Add local tracks
  for (const track of stream.getTracks()) {
    pc.addTrack(track, stream);
  }

  // ICE candidate handler
  pc.onicecandidate = (event) => {
    if (event.candidate) {
      _postIce(event.candidate.toJSON());
    }
  };

  // Remote track handler (2-way video)
  pc.ontrack = (event) => {
    if (event.streams?.[0]) {
      _state.remoteStream = event.streams[0];
      _showRemoteVideo(event.streams[0]);
    }
  };

  // Connection state handler
  pc.onconnectionstatechange = () => {
    switch (pc.connectionState) {
      case 'connected':
        _setStatus('connected', 'Connected');
        _state.reconnectAttempts = 0;
        break;
      case 'connecting':
        _setStatus('connecting', 'Connecting…');
        break;
      case 'disconnected':
        _setStatus('disconnected', 'Disconnected');
        _stopPolling();
        _attemptReconnect();
        break;
      case 'failed':
        _setStatus('failed', 'Connection failed');
        _stopPolling();
        _attemptReconnect();
        break;
    }
  };

  return pc;
}

// ── Full connection flow ──────────────────────────────────────────────────

async function _fullConnect() {
  _readConfig();

  if (!_config.signalingUrl) {
    throw new Error('signalingUrl not configured — set data-signaling-url on <body>');
  }

  _setStatus('connecting', 'Connecting…');
  _updateStatusText('Requesting camera…');

  // 1. Get user media (requires user gesture)
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 640 }, height: { ideal: 360 } },
    audio: true,
  });
  _state.localStream = stream;
  _showLocalVideo(stream);

  _updateStatusText('Establishing peer connection…');

  // 2. Create PeerConnection
  const pc = await _createPeerConnection(stream);
  _state.peerConnection = pc;

  // 3. Create SDP offer
  const offer = await pc.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: true });
  await pc.setLocalDescription(offer);

  // 4. Post offer to signaling Worker
  _updateStatusText('Signaling…');
  const data = await _postOffer(offer.sdp);
  _state.sessionId = data.sessionId;

  // Reset polling state
  _state.processedIceIdx = 0;
  _state.hadRemoteAnswer = false;

  // 5. Start polling for answer + remote ICE
  _updateStatusText('Awaiting remote peer…');
  _startPolling();
}

// ── Teardown ───────────────────────────────────────────────────────────────

function _teardown() {
  _stopPolling();

  // Stop media tracks
  if (_state.localStream) {
    for (const track of _state.localStream.getTracks()) {
      track.stop();
    }
    _state.localStream = null;
  }

  // Close peer connection
  if (_state.peerConnection) {
    _state.peerConnection.close();
    _state.peerConnection = null;
  }

  _state.sessionId = null;
  _state.remoteStream = null;
  _state.processedIceIdx = 0;
  _state.hadRemoteAnswer = false;
  _state.reconnectAttempts = 0;
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Initialize the video widget. Returns control handle.
 *
 * @param {object} [options]
 * @param {string} [options.signalingUrl] — base URL of webrtc-signaling Worker
 * @returns {{ connect: () => Promise<void>, disconnect: () => void, getStatus: () => string }}
 */
export function initVideoWidget(options = {}) {
  if (options.signalingUrl) {
    _config.signalingUrl = options.signalingUrl;
  }

  return {
    /**
     * Connect to WebRTC signaling and establish a peer connection.
     * Must be called from a user-initiated event (e.g., button click)
     * to satisfy browser getUserMedia policy.
     */
    connect: async () => {
      try {
        await _fullConnect();
      } catch (err) {
        console.error('[video-widget] Connection error:', err);
        _setStatus('failed', err.message || 'Connection failed');
        _updateStatusText(err.message || 'Connection failed');
        _teardown();
      }
    },

    /**
     * Disconnect and tear down all WebRTC resources.
     */
    disconnect: () => {
      _teardown();
      _hideVideos();
      _setStatus('disconnected', 'Disconnected');
      _updateStatusText('WebRTC feed inactive');
    },

    /** @returns {string} Current connection status */
    getStatus: () => _state.status,
  };
}

/**
 * Return the current widget status without initializing.
 * @returns {string} — 'connecting' | 'connected' | 'disconnected' | 'failed'
 */
export function getVideoWidgetStatus() {
  return _state.status;
}

// ── Self-check (for basic module load verification) ───────────────────────

if (typeof globalThis !== 'undefined' && globalThis.__VIDEO_WIDGET_SELFTEST) {
  const exports = { initVideoWidget, getVideoWidgetStatus };
  const expected = ['initVideoWidget', 'getVideoWidgetStatus'];
  const missing = expected.filter((n) => typeof exports[n] !== 'function');
  if (missing.length) {
    throw new Error(`[video-widget] Missing exports: ${missing.join(', ')}`);
  }
}
