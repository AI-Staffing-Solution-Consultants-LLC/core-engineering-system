/**
 * EIM — Executive Interface Module
 * Application logic for password gate, viewport switching,
 * tab system, responsive sidebar navigation, face tracking,
 * Tavus avatar integration, and MediaPipe-Tavus bridging.
 *
 * No framework dependencies. Vanilla ES module.
 */

/* ── Storage Keys ──────────────────────────────────────────────────────── */

const SESSION_KEY = 'eim_session_hash';
const SIDEBAR_KEY = 'eim_sidebar_collapsed';

/* ── DOM References ─────────────────────────────────────────────────────── */

const dom = {
  passwordGate: document.getElementById('password-gate'),
  passwordGateCard: document.getElementById('password-gate-card'),
  passwordInput: document.getElementById('password-input'),
  passwordSubmit: document.getElementById('password-submit'),
  passwordError: document.getElementById('password-error'),

  appShell: document.getElementById('app-shell'),
  sidebar: document.getElementById('sidebar'),
  sidebarToggle: document.getElementById('sidebar-toggle'),
  sidebarOverlay: document.getElementById('sidebar-overlay'),
  mobileMenuBtn: document.getElementById('mobile-menu-btn'),

  navItems: document.querySelectorAll('.sidebar-nav-item[data-section]'),
  sections: document.querySelectorAll('.section-view'),

  managementFrame: document.getElementById('management-frame'),
  tabBtns: document.querySelectorAll('.tab-btn[data-tab]'),
  tabPanels: document.querySelectorAll('.tab-panel[role="tabpanel"]'),

  logoutBtn: document.getElementById('logout-btn'),

  // Face tracker
  faceTrackerOverlay: document.getElementById('face-tracker-overlay'),
  faceTrackerLoading: document.getElementById('face-tracker-loading'),
  faceTrackerStatus: document.getElementById('face-tracker-status'),
  faceTrackerStatusIcon: document.getElementById('face-tracker-status-icon'),
  faceTrackerStatusText: document.getElementById('face-tracker-status-text'),
  faceTrackerRetryBtn: document.getElementById('face-tracker-retry-btn'),
  faceBadge: document.getElementById('canvas-face-badge'),
  canvasPlaceholder: document.querySelector('.canvas-placeholder'),

  // Avatar
  avatarContainer: document.getElementById('avatar-container'),
  avatarLoading: document.getElementById('avatar-loading'),
  avatarPlaceholder: document.getElementById('avatar-placeholder'),
  avatarError: document.getElementById('avatar-error'),
  avatarErrorLabel: document.getElementById('avatar-error-label'),
  avatarRetryBtn: document.getElementById('avatar-retry-btn'),
};

/* ── State ──────────────────────────────────────────────────────────────── */

let activeSection = 'dashboard';
let isMobileOpen = false;
let faceTrackerInstance = null;
let faceTrackerInitialized = false;

// Dashboard viewport lazy-load state
const lazyLoadedTabs = new Set();
lazyLoadedTabs.add('tokenomics-tab'); // First tab is active on load

// Configurable dashboard URLs — override via env vars at deploy time
const EIM_CONFIG = {
  tokenomicsUrl: 'https://tokenomics-dashboard-xxxxx-uc.a.run.app',
  masterControlUrl: 'https://master-control-xxxxx-uc.a.run.app',
  sherylUrl: 'https://sheryl-agent-xxxxx-uc.a.run.app',
  selfRemediationUrl: 'https://self-remediation-xxxxx-uc.a.run.app',
};

// Expose blendshape data for downstream consumers (Tasks 7, 8)
let latestBlendshapes = null;

// Avatar state
let tavusAvatarInstance = null;
let mediapipeBridgeInstance = null;
let avatarConnected = false;
let avatarConnecting = false;

/* ── Utilities ──────────────────────────────────────────────────────────── */

/**
 * Hash a string with SHA-256, returns hex string.
 */
async function sha256(message) {
  const encoder = new TextEncoder();
  const data = encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Generate a random session identifier. Not a security token —
 * only stores that the user authenticated, not the password.
 */
function generateSessionId() {
  const arr = new Uint8Array(16);
  crypto.getRandomValues(arr);
  return Array.from(arr, (b) => b.toString(16).padStart(2, '0')).join('');
}

/* ── Password Gate ──────────────────────────────────────────────────────── */

/**
 * Attempt authentication via the Pages Function.
 * Sends the password to POST /api/auth; server verifies against
 * ACCESS_PASSWORD_HASH env var. Client never sees the hash.
 */
async function attemptAuth(password) {
  try {
    const response = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      return { authenticated: false };
    }

    const data = await response.json();
    return data;
  } catch (err) {
    console.error('Auth request failed:', err);
    return { authenticated: false, error: 'Network error' };
  }
}

/**
 * Handle password submission.
 */
async function handlePasswordSubmit() {
  const password = dom.passwordInput.value.trim();

  if (!password) {
    showPasswordError();
    return;
  }

  const result = await attemptAuth(password);

  if (result.authenticated) {
    // Store session identifier (not the password/hash)
    const sessionId = generateSessionId();
    localStorage.setItem(SESSION_KEY, sessionId);
    hidePasswordGate();
    initFaceTracker();
    initAvatar();
  } else {
    showPasswordError();
  }
}

function showPasswordError() {
  dom.passwordError.classList.add('visible');
  dom.passwordGateCard.classList.add('shake');
  dom.passwordInput.value = '';

  // Remove shake after animation completes
  setTimeout(() => {
    dom.passwordGateCard.classList.remove('shake');
  }, 500);

  // Hide error message after 2 seconds
  setTimeout(() => {
    dom.passwordError.classList.remove('visible');
  }, 2000);
}

function hidePasswordGate() {
  dom.passwordGate.classList.add('hidden');
}

/**
 * Check if a valid session exists. If so, skip the password gate.
 */
function checkSession() {
  const sessionId = localStorage.getItem(SESSION_KEY);
  if (sessionId) {
    dom.passwordGate.classList.add('hidden');
    return true;
  }
  return false;
}

/**
 * Clear session and show password gate again.
 */
function logout() {
  localStorage.removeItem(SESSION_KEY);

  if (faceTrackerInstance) {
    faceTrackerInstance.stop();
    faceTrackerInstance = null;
    faceTrackerInitialized = false;
    latestBlendshapes = null;
    handleFaceTrackerStatus('idle');
  }

  if (mediapipeBridgeInstance) {
    mediapipeBridgeInstance.detach();
    mediapipeBridgeInstance = null;
  }

  if (tavusAvatarInstance) {
    tavusAvatarInstance.disconnect();
    tavusAvatarInstance = null;
    avatarConnected = false;
    avatarConnecting = false;
    handleAvatarStatus('disconnected');
  }

  dom.passwordGate.classList.remove('hidden');
  dom.passwordInput.value = '';
  dom.passwordInput.focus();
}

/* ── Section / Viewport Switching ───────────────────────────────────────── */

/**
 * Activate a section view. Hides all other sections.
 */
function activateSection(sectionName) {
  activeSection = sectionName;

  // Update nav items
  dom.navItems.forEach((item) => {
    const isActive = item.dataset.section === sectionName;
    item.classList.toggle('active', isActive);
    if (isActive) {
      item.setAttribute('aria-current', 'page');
    } else {
      item.removeAttribute('aria-current');
    }
  });

  // Toggle section views
  dom.sections.forEach((section) => {
    const sectionId = section.id.replace('section-', '');
    section.classList.toggle('active', sectionId === sectionName);
  });

  // On mobile, close sidebar after navigation
  if (isMobileOpen && window.innerWidth <= 768) {
    closeMobileSidebar();
  }
}

/* ── Tab System ─────────────────────────────────────────────────────────── */

/**
 * Activate a tab panel within the management frame.
 */
function activateTab(tabName) {
  // Update tab buttons
  dom.tabBtns.forEach((btn) => {
    const isActive = btn.dataset.tab === tabName;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-selected', isActive);
  });

  // Update tab panels
  dom.tabPanels.forEach((panel) => {
    const isActive = panel.id === tabName;
    panel.classList.toggle('active', isActive);
  });

  // Lazy-load tab content on first click
  if (!lazyLoadedTabs.has(tabName)) {
    lazyLoadedTabs.add(tabName);
    switch (tabName) {
      case 'tokenomics-tab':
        loadIframeTab('tokenomics', EIM_CONFIG.tokenomicsUrl);
        break;
      case 'mastercontrol-tab':
        loadIframeTab('mastercontrol', EIM_CONFIG.masterControlUrl);
        break;
      case 'telemetry-tab':
        loadTelemetryTab();
        break;
      case 'responses-tab':
        loadResponsesTab();
        break;
    }
  }
}

/**
 * Load an iframe into a dashboard tab panel with cross-origin fallback handling.
 * @param {string} prefix — 'tokenomics' or 'mastercontrol'
 * @param {string} url — dashboard URL to embed
 */
function loadIframeTab(prefix, url) {
  const container = document.getElementById(`${prefix}-iframe-container`);
  if (!container) return;

  const iframe = document.createElement('iframe');
  iframe.className = 'dashboard-iframe';
  iframe.src = url;
  iframe.allow = 'clipboard-write';
  iframe.sandbox = 'allow-scripts allow-same-origin allow-popups allow-forms';
  iframe.title = `${prefix === 'tokenomics' ? 'Tokenomics' : 'Master Control'} Dashboard`;
  iframe.loading = 'lazy';

  const fallback = document.getElementById(`${prefix}-fallback`);
  const fallbackLink = document.getElementById(`${prefix}-fallback-link`);

  if (fallbackLink) {
    fallbackLink.href = url;
  }

  iframe.addEventListener('load', () => {
    // Test if iframe is accessible (not blocked by X-Frame-Options)
    try {
      const doc = iframe.contentDocument;
      if (!doc || !doc.body) {
        throw new Error('cross-origin blocked');
      }
    } catch {
      // X-Frame-Options or CSP blocked — show fallback
      iframe.remove();
      if (fallback) fallback.classList.remove('hidden');
    }
  });

  iframe.addEventListener('error', () => {
    iframe.remove();
    if (fallback) fallback.classList.remove('hidden');
  });

  container.appendChild(iframe);
}

/**
 * Load telemetry tab with Mesh service health status cards.
 * Displays status for all 8 Mesh services using local fallback data.
 * In production, fetches from SELF_REMEDIATION_URL/health-check.
 */
function loadTelemetryTab() {
  const grid = document.getElementById('service-grid');
  if (!grid) return;

  const services = [
    { name: 'Track A — Control Loop', port: 8080, status: 'healthy' },
    { name: 'Track B — Actuator', port: 8081, status: 'healthy' },
    { name: 'Sheryl — Strategy', port: 8082, status: 'healthy' },
    { name: 'Connie — Code Analysis', port: 8083, status: 'healthy' },
    { name: 'Roy — Predictions', port: 8084, status: 'healthy' },
    { name: 'Mary — Monitoring', port: 8085, status: 'warning' },
    { name: 'Data Remediation Engine', port: 8086, status: 'healthy' },
    { name: 'Self-Remediation', port: 8087, status: 'healthy' },
  ];

  grid.innerHTML = services
    .map(
      (svc) => `
    <div class="service-card service-card-${svc.status}">
      <div class="service-card-header">
        <span class="service-card-name">${svc.name}</span>
        <span class="service-status service-status-${svc.status}">${svc.status}</span>
      </div>
      <div class="service-card-body">
        <span class="service-card-port">Port ${svc.port}</span>
      </div>
    </div>`
    )
    .join('');

  // Attempt live health check in background
  if (EIM_CONFIG.selfRemediationUrl && !EIM_CONFIG.selfRemediationUrl.includes('xxxxx')) {
    fetch(`${EIM_CONFIG.selfRemediationUrl}/health-check`)
      .then((r) => r.json())
      .then((data) => {
        if (data && data.services) {
          updateServiceGrid(data.services);
        }
      })
      .catch(() => {});
  }
}

function updateServiceGrid(serviceData) {
  const grid = document.getElementById('service-grid');
  if (!grid) return;

  grid.innerHTML = serviceData
    .map(
      (svc) => `
    <div class="service-card service-card-${svc.status || 'healthy'}">
      <div class="service-card-header">
        <span class="service-card-name">${svc.name}</span>
        <span class="service-status service-status-${svc.status || 'healthy'}">${svc.status || 'healthy'}</span>
      </div>
      <div class="service-card-body">
        <span class="service-card-port">Port ${svc.port || '—'}</span>
      </div>
    </div>`
    )
    .join('');
}

/**
 * Load agent responses tab from Sheryl /dashboard/last-responses.
 * Fetches via Pages Function proxy (/api/sheryl/responses).
 * Renders cards with agent name, timestamp, query/response preview, and flag status.
 */
async function loadResponsesTab() {
  const container = document.getElementById('response-cards');
  if (!container) return;

  try {
    const response = await fetch('/api/sheryl/responses');

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();

    if (!Array.isArray(data) || data.length === 0) {
      container.innerHTML = `
        <div class="response-card response-card-empty">
          <div class="response-card-header">
            <span class="response-card-agent">No recent agent responses</span>
          </div>
          <div class="response-card-body">
            <p class="text-muted">Agents have not reported any responses yet.</p>
          </div>
        </div>`;
      return;
    }

    container.innerHTML = data
      .map(
        (entry) => `
      <div class="response-card">
        <div class="response-card-header">
          <span class="response-card-agent">${escapeHtml(entry.agent || 'Unknown Agent')}</span>
          <span class="response-card-timestamp text-mono">${escapeHtml(entry.timestamp || '—')}</span>
        </div>
        <div class="response-card-preview">
          <div class="response-card-query">${escapeHtml(truncateText(entry.query, 120))}</div>
          <div class="response-card-response">${escapeHtml(truncateText(entry.response, 160))}</div>
        </div>
        <div class="response-card-footer">
          <span class="response-card-flag ${entry.ambiguous ? 'response-flag-warn' : 'response-flag-ok'}">
            ${entry.ambiguous ? 'Ambiguous' : 'Clear'}
          </span>
        </div>
      </div>`
      )
      .join('');
  } catch (err) {
    console.error('[EIM] Failed to load agent responses:', err);
    container.innerHTML = `
      <div class="response-card response-card-error">
        <div class="response-card-header">
          <span class="response-card-agent">Dashboard data unavailable</span>
        </div>
        <div class="response-card-body">
          <p class="text-muted">Check system health — Sheryl endpoint may be offline.</p>
        </div>
      </div>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function truncateText(text, maxLen) {
  if (!text) return '—';
  return text.length > maxLen ? text.slice(0, maxLen) + '…' : text;
}

/**
 * Toggle sidebar collapsed state (desktop) or open/close (mobile).
 */
function toggleSidebar() {
  if (window.innerWidth <= 768) {
    // Mobile behavior: slide in/out
    if (isMobileOpen) {
      closeMobileSidebar();
    } else {
      openMobileSidebar();
    }
  } else {
    // Desktop behavior: collapse/expand width
    const isCollapsed = dom.appShell.classList.toggle('sidebar-collapsed');
    localStorage.setItem(SIDEBAR_KEY, isCollapsed ? '1' : '0');
  }
}

function openMobileSidebar() {
  isMobileOpen = true;
  dom.sidebar.classList.add('mobile-open');
  dom.sidebarOverlay.classList.add('visible');
  dom.sidebarOverlay.setAttribute('aria-hidden', 'false');
  dom.mobileMenuBtn.setAttribute('aria-expanded', 'true');
  document.body.style.overflow = 'hidden';
}

function closeMobileSidebar() {
  isMobileOpen = false;
  dom.sidebar.classList.remove('mobile-open');
  dom.sidebarOverlay.classList.remove('visible');
  dom.sidebarOverlay.setAttribute('aria-hidden', 'true');
  dom.mobileMenuBtn.setAttribute('aria-expanded', 'false');
  document.body.style.overflow = '';
}

/**
 * Restore sidebar state from localStorage on page load.
 */
function restoreSidebarState() {
  if (window.innerWidth > 768) {
    const saved = localStorage.getItem(SIDEBAR_KEY);
    if (saved === '1') {
      dom.appShell.classList.add('sidebar-collapsed');
    } else {
      dom.appShell.classList.remove('sidebar-collapsed');
    }
  }
}

/**
 * Handle window resize — ensures correct sidebar behavior
 * when transitioning between mobile and desktop breakpoints.
 */
function handleResize() {
  if (window.innerWidth > 768) {
    // Leaving mobile: clean up mobile overlay state
    if (isMobileOpen) {
      closeMobileSidebar();
    }
    dom.sidebar.classList.remove('mobile-open');
    restoreSidebarState();
  } else {
    // Entering mobile: remove desktop collapsed state
    dom.appShell.classList.remove('sidebar-collapsed');
  }
}

/* ── Event Binding ──────────────────────────────────────────────────────── */

function bindEvents() {
  // Password gate
  dom.passwordSubmit.addEventListener('click', handlePasswordSubmit);
  dom.passwordInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      handlePasswordSubmit();
    }
  });

  // Sidebar toggle
  dom.sidebarToggle.addEventListener('click', toggleSidebar);

  // Mobile menu button
  dom.mobileMenuBtn.addEventListener('click', toggleSidebar);

  // Sidebar overlay (close on click outside)
  dom.sidebarOverlay.addEventListener('click', closeMobileSidebar);

  // Close sidebar on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isMobileOpen) {
      closeMobileSidebar();
    }
  });

  // Navigation items
  dom.navItems.forEach((item) => {
    item.addEventListener('click', () => {
      const section = item.dataset.section;
      activateSection(section);
    });
  });

  // Tab buttons
  dom.tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      activateTab(tab);
    });
  });

  // Face tracker retry button
  if (dom.faceTrackerRetryBtn) {
    dom.faceTrackerRetryBtn.addEventListener('click', () => {
      initFaceTracker();
    });
  }

  // Avatar retry button
  if (dom.avatarRetryBtn) {
    dom.avatarRetryBtn.addEventListener('click', () => {
      initAvatar();
    });
  }

  // Logout
  if (dom.logoutBtn) {
    dom.logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      logout();
    });
  }

  // Window resize
  window.addEventListener('resize', handleResize);
}

/* ── Face Tracker Integration ──────────────────────────────────────────── */

async function initFaceTracker() {
  if (faceTrackerInitialized) return;
  faceTrackerInitialized = true;

  // Show overlay and loading spinner
  dom.faceTrackerOverlay?.classList.remove('hidden');
  dom.faceTrackerOverlay?.removeAttribute('aria-hidden');
  dom.faceTrackerLoading?.classList.remove('hidden');
  dom.faceTrackerStatus?.classList.add('hidden');

  try {
    const { default: FaceTracker } = await import('./mediapipe-face-tracker.js');

    faceTrackerInstance = new FaceTracker({
      canvasId: 'face-mesh-canvas',
      containerSelector: '.canvas-frame',
    });

    faceTrackerInstance.addEventListener('status', (e) => {
      const { status, message } = e.detail;
      handleFaceTrackerStatus(status, message);
    });

    faceTrackerInstance.addEventListener('blendshape', (e) => {
      latestBlendshapes = e.detail;
      // Downstream consumers (Tasks 7, 8) poll `getLatestBlendshapes()`
    });

    await faceTrackerInstance.start();
  } catch (err) {
    console.error('[EIM] Face tracker init failed:', err);
    handleFaceTrackerStatus('error', err.message || 'Unknown error');
    faceTrackerInitialized = false;
  }
}

function handleFaceTrackerStatus(status, message) {
  switch (status) {
    case 'initializing':
      dom.faceTrackerLoading?.classList.remove('hidden');
      dom.faceTrackerStatus?.classList.add('hidden');
      dom.faceBadge?.classList.remove('visible');
      break;

    case 'running':
      dom.faceTrackerLoading?.classList.add('hidden');
      dom.faceTrackerStatus?.classList.add('hidden');
      dom.faceBadge?.classList.add('visible');
      dom.canvasPlaceholder?.classList.add('hidden');
      break;

    case 'no-camera':
      dom.faceTrackerLoading?.classList.add('hidden');
      dom.faceTrackerStatus?.classList.remove('hidden');
      dom.faceBadge?.classList.remove('visible');
      faceTrackerInitialized = false;
      dom.faceTrackerStatusIcon.className = 'face-tracker-status-icon warning';
      dom.faceTrackerStatusIcon.innerHTML =
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/><line x1="5" y1="3" x2="5" y2="5"/></svg>';
      dom.faceTrackerStatusText.textContent =
        message || 'Camera access denied. Please enable camera permissions to use face tracking.';
      dom.faceTrackerRetryBtn.classList.remove('hidden');
      break;

    case 'error':
      dom.faceTrackerLoading?.classList.add('hidden');
      dom.faceTrackerStatus?.classList.remove('hidden');
      dom.faceBadge?.classList.remove('visible');
      dom.faceTrackerStatusIcon.className = 'face-tracker-status-icon error';
      dom.faceTrackerStatusIcon.innerHTML =
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
      dom.faceTrackerStatusText.textContent =
        message || 'Face tracker initialization failed. Try refreshing the page.';
      dom.faceTrackerRetryBtn.classList.remove('hidden');
      faceTrackerInitialized = false;
      break;

    case 'idle':
    default:
      dom.faceTrackerLoading?.classList.add('hidden');
      dom.faceTrackerStatus?.classList.add('hidden');
      dom.faceBadge?.classList.remove('visible');
      dom.faceTrackerOverlay?.classList.add('hidden');
      dom.faceTrackerOverlay?.setAttribute('aria-hidden', 'true');
      break;
  }
}

/**
 * Public getter for downstream consumers (Tasks 7, 8).
 * Returns the latest blendshape scores or null.
 */
export function getLatestBlendshapes() {
  return latestBlendshapes;
}

/* ── Avatar Integration ─────────────────────────────────────────────────── */

/**
 * Initialize the Tavus avatar and MediaPipe bridge.
 * Called after successful authentication and independent of face tracker.
 */
async function initAvatar() {
  if (avatarConnected || avatarConnecting) return;
  avatarConnecting = true;

  handleAvatarStatus('connecting');

  try {
    // Import modules dynamically
    const [{ default: TavusAvatar }, { default: MediapipeTavusBridge }] = await Promise.all([
      import('./tavus-avatar.js'),
      import('./mediapipe-tavus-bridge.js'),
    ]);

    // Create the bridge if face tracker is active
    if (faceTrackerInstance) {
      if (!mediapipeBridgeInstance) {
        mediapipeBridgeInstance = new MediapipeTavusBridge();
        mediapipeBridgeInstance.addEventListener('tavus-context', (e) => {
          console.log('[EIM] Tavus context updated:', e.detail.emotion);
        });
      }
      mediapipeBridgeInstance.attach(faceTrackerInstance);
    }

    // Fetch conversation URL from the server-side proxy
    const response = await fetch('/api/tavus/conversation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Proxy returned ${response.status}`);
    }

    const { conversation_url } = await response.json();
    if (!conversation_url) {
      throw new Error('No conversation_url returned from Tavus proxy');
    }

    // Create and connect the avatar
    tavusAvatarInstance = new TavusAvatar({ containerId: 'avatar-container' });

    tavusAvatarInstance.addEventListener('status', (e) => {
      const { status, message } = e.detail;
      handleAvatarStatus(status, message);
    });

    await tavusAvatarInstance.connect(conversation_url);
  } catch (err) {
    console.error('[EIM] Avatar init failed:', err);
    handleAvatarStatus('error', err.message || 'Avatar connection failed');
    avatarConnecting = false;
  }
}

/**
 * Handle avatar status changes — update UI states.
 * @param {string} status — "connecting" | "connected" | "disconnected" | "error"
 * @param {string} [message] — error message
 */
function handleAvatarStatus(status, message) {
  const avatarPlaceholder = dom.avatarPlaceholder;
  const avatarLoading = dom.avatarLoading;
  const avatarError = dom.avatarError;

  switch (status) {
    case 'connecting':
      avatarConnected = false;
      avatarConnecting = true;
      if (avatarPlaceholder) avatarPlaceholder.classList.add('hidden');
      if (avatarLoading) avatarLoading.classList.remove('hidden');
      if (avatarError) avatarError.classList.add('hidden');
      break;

    case 'connected':
      avatarConnected = true;
      avatarConnecting = false;
      if (avatarPlaceholder) avatarPlaceholder.classList.add('hidden');
      if (avatarLoading) avatarLoading.classList.add('hidden');
      if (avatarError) avatarError.classList.add('hidden');
      if (dom.faceBadge) {
        const badgeLabel = dom.faceBadge.querySelector('span:last-child');
        if (badgeLabel) badgeLabel.textContent = 'Avatar Active';
        dom.faceBadge.classList.add('visible');
      }
      break;

    case 'disconnected':
      avatarConnected = false;
      avatarConnecting = false;
      if (avatarPlaceholder) avatarPlaceholder.classList.remove('hidden');
      if (avatarLoading) avatarLoading.classList.add('hidden');
      if (avatarError) avatarError.classList.add('hidden');
      break;

    case 'error':
      avatarConnected = false;
      avatarConnecting = false;
      if (avatarPlaceholder) avatarPlaceholder.classList.add('hidden');
      if (avatarLoading) avatarLoading.classList.add('hidden');
      if (avatarError) avatarError.classList.remove('hidden');
      if (dom.avatarErrorLabel) {
        dom.avatarErrorLabel.textContent = message || 'Avatar connection failed';
      }
      break;
  }
}

/* ── Initialization ─────────────────────────────────────────────────────── */

function init() {
  bindEvents();

  // Attempt to fetch deployed config (env-var-driven URLs); non-blocking
  fetch('/api/config')
    .then((r) => r.json())
    .then((cfg) => Object.assign(EIM_CONFIG, cfg))
    .catch(() => {});

  // Check existing session
  const hasSession = checkSession();

  if (hasSession) {
    restoreSidebarState();
    initFaceTracker();
    initAvatar();
    loadIframeTab('tokenomics', EIM_CONFIG.tokenomicsUrl);
  } else {
    // Show password gate, focus input
    dom.passwordInput.focus();
    // Ensure sidebar starts expanded when first authenticating
    dom.appShell.classList.remove('sidebar-collapsed');
  }

  console.log('[EIM] Initialized. Session:', hasSession ? 'active' : 'expired');
}

// Boot
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
