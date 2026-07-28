/**
 * EIM Authentication — Pages Function
 *
 * POST /api/auth
 * Body: { "password": "..." }
 * Response: { "authenticated": true | false }
 *
 * Rate-limited: 5 attempts per minute per IP (in-memory).
 * The ACCESS_PASSWORD_HASH env var is NEVER returned to the client.
 */

// In-memory rate limiting store.
// Cleans up entries older than WINDOW_MS on each request.
// In production, use KV or Durable Objects for persistence across instances.
const rateLimitStore = new Map();
const MAX_ATTEMPTS = 5;
const WINDOW_MS = 60_000; // 1 minute

/**
 * Hash a string with SHA-256, returns hex string.
 * Uses the Web Crypto API available in Workers/Pages Functions runtime.
 */
async function sha256(message) {
  const encoder = new TextEncoder();
  const data = encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Check and update rate limit for a given IP.
 * @param {string} ip
 * @returns {{ allowed: boolean, remaining: number }}
 */
function checkRateLimit(ip) {
  const now = Date.now();

  // Clean up stale entries
  for (const [key, entry] of rateLimitStore.entries()) {
    if (now - entry.windowStart > WINDOW_MS) {
      rateLimitStore.delete(key);
    }
  }

  const entry = rateLimitStore.get(ip);

  if (!entry || now - entry.windowStart > WINDOW_MS) {
    // New window
    rateLimitStore.set(ip, { count: 1, windowStart: now });
    return { allowed: true, remaining: MAX_ATTEMPTS - 1 };
  }

  if (entry.count >= MAX_ATTEMPTS) {
    return { allowed: false, remaining: 0 };
  }

  entry.count += 1;
  return { allowed: true, remaining: MAX_ATTEMPTS - entry.count };
}

/**
 * Extract client IP from request headers.
 * Handles Cloudflare proxy forwarding.
 */
function getClientIP(request) {
  const cfIP = request.headers.get('CF-Connecting-IP');
  if (cfIP) return cfIP;

  const forwarded = request.headers.get('X-Forwarded-For');
  if (forwarded) return forwarded.split(',')[0].trim();

  return 'unknown';
}

/**
 * CORS headers for API responses.
 */
function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };
}

/**
 * Main request handler.
 */
export async function onRequest(context) {
  const { request, env } = context;

  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  // Only POST is allowed
  if (request.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: corsHeaders() }
    );
  }

  // Rate limiting
  const clientIP = getClientIP(request);
  const rateCheck = checkRateLimit(clientIP);

  if (!rateCheck.allowed) {
    return new Response(
      JSON.stringify({
        authenticated: false,
        error: 'Rate limit exceeded. Try again later.',
      }),
      {
        status: 429,
        headers: {
          ...corsHeaders(),
          'Retry-After': '60',
        },
      }
    );
  }

  // Parse request body
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(
      JSON.stringify({ authenticated: false, error: 'Invalid JSON' }),
      { status: 400, headers: corsHeaders() }
    );
  }

  const { password } = body;

  if (!password || typeof password !== 'string' || password.length === 0) {
    return new Response(
      JSON.stringify({ authenticated: false, error: 'Password required' }),
      { status: 400, headers: corsHeaders() }
    );
  }

  // Verify password against stored hash
  const expectedHash = env.ACCESS_PASSWORD_HASH;

  if (!expectedHash || expectedHash === 'placeholder-change-me-set-real-hash-before-deploy') {
    console.error('[EIM Auth] ACCESS_PASSWORD_HASH env var is not configured.');
    return new Response(
      JSON.stringify({ authenticated: false, error: 'Server configuration error' }),
      { status: 500, headers: corsHeaders() }
    );
  }

  const inputHash = await sha256(password);

  if (inputHash === expectedHash) {
    // Reset rate limit on successful authentication
    rateLimitStore.delete(clientIP);

    return new Response(
      JSON.stringify({ authenticated: true }),
      { status: 200, headers: corsHeaders() }
    );
  }

  // Authentication failed
  return new Response(
    JSON.stringify({
      authenticated: false,
      remaining: rateCheck.remaining,
    }),
    { status: 401, headers: corsHeaders() }
  );
}
