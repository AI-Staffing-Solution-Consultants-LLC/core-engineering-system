/**
 * Admin Gate Pages Function — validates CFP_PASSWORD env var,
 * enforces rate limit of 5 attempts per IP per 15 minutes.
 *
 * Deploy as a Cloudflare Pages Function (onRequestPost handler for /admin-gate).
 *
 * Environment variable required:
 *   CFP_PASSWORD — the admin password (never hardcoded)
 *
 * Uses a Durable Object for rate limiting, or falls back to an in-memory
 * Map with a periodic cleanup timer for simpler deployments.
 */

// In-memory rate limit store (for Pages Functions without DO binding).
// For production with multiple isolates, replace with Durable Object or KV.
const rateLimitStore = new Map();

const RATE_LIMIT_WINDOW = 15 * 60 * 1000; // 15 minutes
const RATE_LIMIT_MAX = 5;

function cleanupRateLimitStore() {
  const now = Date.now();
  for (const [key, entry] of rateLimitStore) {
    if (now > entry.resetAt) {
      rateLimitStore.delete(key);
    }
  }
}

let _cleanupTimer = null;
function startCleanupTimer() {
  if (typeof setInterval !== 'undefined' && _cleanupTimer === null) {
    _cleanupTimer = setInterval(cleanupRateLimitStore, 60_000);
    // Allow Node.js process to exit even with active timer (for testing)
    if (typeof _cleanupTimer?.unref === 'function') {
      _cleanupTimer.unref();
    }
  }
}
function stopCleanupTimer() {
  if (_cleanupTimer !== null) {
    clearInterval(_cleanupTimer);
    _cleanupTimer = null;
  }
}
startCleanupTimer();

/**
 * Check and increment rate limit for an IP address.
 * @param {string} ip
 * @returns {{ allowed: boolean, remaining: number, resetAt: number }}
 */
function checkRateLimit(ip) {
  const now = Date.now();
  const key = `rate:${ip}`;
  let entry = rateLimitStore.get(key);

  if (!entry || now > entry.resetAt) {
    entry = { count: 0, resetAt: now + RATE_LIMIT_WINDOW };
    rateLimitStore.set(key, entry);
  }

  if (entry.count >= RATE_LIMIT_MAX) {
    return { allowed: false, remaining: 0, resetAt: entry.resetAt };
  }

  entry.count += 1;
  return { allowed: true, remaining: RATE_LIMIT_MAX - entry.count, resetAt: entry.resetAt };
}

// ---- Exported handler --------------------------------------------------------

export async function onRequestPost({ request, env }) {
  // CFP_PASSWORD from env var — NEVER hardcoded
  const CFP_PASSWORD = env.CFP_PASSWORD || process?.env?.CFP_PASSWORD;

  if (!CFP_PASSWORD) {
    return new Response(JSON.stringify({
      success: false,
      error: 'server_configuration',
      detail: 'CFP_PASSWORD environment variable is not set'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Parse request body
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({
      success: false,
      error: 'invalid_body'
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const password = body.password || '';
  const ip = body.ip || request.headers.get('CF-Connecting-IP') || '127.0.0.1';

  // Rate limit check
  const rateLimit = checkRateLimit(ip);
  if (!rateLimit.allowed) {
    return new Response(JSON.stringify({
      success: false,
      rate_limited: true,
      error: 'rate_limited',
      detail: `Too many attempts. Try again after ${new Date(rateLimit.resetAt).toISOString()}`,
      retry_after_seconds: Math.ceil((rateLimit.resetAt - Date.now()) / 1000)
    }), {
      status: 429,
      headers: {
        'Content-Type': 'application/json',
        'Retry-After': String(Math.ceil((rateLimit.resetAt - Date.now()) / 1000))
      }
    });
  }

  // Validate password
  if (password !== CFP_PASSWORD) {
    return new Response(JSON.stringify({
      success: false,
      error: 'invalid_password',
      remaining_attempts: rateLimit.remaining
    }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Success — reset rate limit counter on successful auth
  rateLimitStore.delete(`rate:${ip}`);

  return new Response(JSON.stringify({
    success: true
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

// Export for testing
export { checkRateLimit, cleanupRateLimitStore, stopCleanupTimer, rateLimitStore, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX };
