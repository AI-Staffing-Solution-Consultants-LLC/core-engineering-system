/**
 * EIM — Executive Interface Module
 * Application logic for password gate, viewport switching,
 * tab system, and responsive sidebar navigation.
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
};

/* ── State ──────────────────────────────────────────────────────────────── */

let activeSection = 'dashboard';
let isMobileOpen = false;

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
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */

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

/* ── Initialization ─────────────────────────────────────────────────────── */

function init() {
  bindEvents();

  // Check existing session
  const hasSession = checkSession();

  if (hasSession) {
    // Dashboard is already visible; restore sidebar state
    restoreSidebarState();
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
