/**
 * Turnstile Gate Worker - intercepts /admin, presents Turnstile + password prompt,
 * validates via admin-gate Pages Function, sets session cookie on success.
 *
 * Deploy as a Cloudflare Worker with a route matching */admin*
 * Bindings:
 *   - ADMIN_GATE_URL: the Pages Function URL for password validation
 *   - SITE_VERIFY_URL: https://challenges.cloudflare.com/turnstile/v0/siteverify
 *   - TURNSTILE_SECRET_KEY: set via wrangler secret
 *   - SESSION_SECRET: set via wrangler secret (for signing cookies)
 */

const TURNSTILE_SITEKEY = typeof TURNSTILE_SITEKEY !== 'undefined' ? TURNSTILE_SITEKEY : '1x00000000000000000000AA'; // test key
const SESSION_TTL = 24 * 60 * 60; // 24 hours
const COOKIE_NAME = 'cf_admin_session';

/**
 * Simple HMAC-like cookie signing using Web Crypto.
 * In production, use a proper JWT or signed cookie library.
 */
async function signCookie(payload) {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(SESSION_SECRET);
  const key = await crypto.subtle.importKey(
    'raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const data = encoder.encode(JSON.stringify(payload));
  const signature = await crypto.subtle.sign('HMAC', key, data);
  const sigHex = Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0')).join('');
  return `${btoa(JSON.stringify(payload))}.${sigHex}`;
}

async function verifyCookie(cookieValue) {
  try {
    const [payloadB64, sigHex] = cookieValue.split('.');
    const payload = JSON.parse(atob(payloadB64));

    const encoder = new TextEncoder();
    const keyData = encoder.encode(SESSION_SECRET);
    const key = await crypto.subtle.importKey(
      'raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
    );
    const data = encoder.encode(JSON.stringify(payload));
    const expectedSig = await crypto.subtle.sign('HMAC', key, data);
    const expectedHex = Array.from(new Uint8Array(expectedSig))
      .map(b => b.toString(16).padStart(2, '0')).join('');

    if (expectedHex !== sigHex) return null;
    if (Date.now() > payload.exp) return null;
    return payload;
  } catch {
    return null;
  }
}

function getChallengeHTML(sitekey, error) {
  const errorHTML = error
    ? `<div style="color:#dc2626;margin-bottom:1rem;padding:0.5rem;background:#fef2f2;border-radius:4px;">${error}</div>`
    : '';
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Access — Verification Required</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #0f172a; color: #e2e8f0; display: flex; justify-content: center;
           align-items: center; min-height: 100vh; }
    .gate { background: #1e293b; padding: 2.5rem; border-radius: 12px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.4); max-width: 420px; width: 100%; }
    .gate h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #f8fafc; }
    .gate p { color: #94a3b8; margin-bottom: 1.5rem; font-size: 0.9rem; }
    .field { margin-bottom: 1.25rem; }
    .field label { display: block; margin-bottom: 0.4rem; font-size: 0.85rem;
                   color: #cbd5e1; font-weight: 500; }
    .field input { width: 100%; padding: 0.65rem 0.85rem; border: 1px solid #334155;
                   border-radius: 6px; background: #0f172a; color: #e2e8f0; font-size: 1rem; }
    .field input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.2); }
    button { width: 100%; padding: 0.75rem; background: #3b82f6; color: #fff; border: none;
             border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer;
             transition: background 0.2s; margin-top: 0.5rem; }
    button:hover { background: #2563eb; }
    button:disabled { background: #475569; cursor: not-allowed; }
    .cf-turnstile { margin-bottom: 1.25rem; display: flex; justify-content: center; }
  </style>
  <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
</head>
<body>
  <div class="gate">
    <h1>Admin Access</h1>
    <p>Complete the verification below to continue.</p>
    ${errorHTML}
    <form id="gate-form" method="POST" action="/admin">
      <div class="cf-turnstile" data-sitekey="${sitekey}" data-action="turnstile-spin-v1"></div>
      <div class="field">
        <label for="password">Admin Password</label>
        <input type="password" id="password" name="password" required
               placeholder="Enter admin password" autocomplete="current-password">
      </div>
      <button type="submit" id="submit-btn">Verify &amp; Continue</button>
    </form>
  </div>
  <script>
    const form = document.getElementById('gate-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('submit-btn');
      btn.disabled = true;
      btn.textContent = 'Verifying...';
      try {
        const token = document.querySelector('[name="cf-turnstile-response"]')?.value;
        if (!token) { alert('Please complete the CAPTCHA.'); btn.disabled = false; btn.textContent = 'Verify & Continue'; return; }
        const resp = await fetch('/admin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, password: document.getElementById('password').value })
        });
        const data = await resp.json();
        if (data.success) { window.location.href = data.redirect || '/admin'; }
        else { location.reload(); }
      } catch(err) { alert('Network error. Please try again.'); location.reload(); }
      btn.disabled = false;
      btn.textContent = 'Verify & Continue';
    });
  </script>
</body>
</html>`;
}

async function verifyTurnstile(token, ip) {
  const formData = new FormData();
  formData.append('secret', TURNSTILE_SECRET_KEY);
  formData.append('response', token);
  if (ip) formData.append('remoteip', ip);

  const resp = await fetch(SITE_VERIFY_URL, {
    method: 'POST',
    body: formData
  });
  return resp.json();
}

async function verifyPassword(token, password, ip) {
  const resp = await fetch(ADMIN_GATE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password, ip })
  });
  return resp.json();
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Only intercept /admin paths
    if (!url.pathname.startsWith('/admin')) {
      return fetch(request);
    }

    // Check for existing session
    const cookieHeader = request.headers.get('Cookie') || '';
    const sessionCookie = cookieHeader.split(';')
      .map(c => c.trim())
      .find(c => c.startsWith(`${COOKIE_NAME}=`));

    if (sessionCookie) {
      const cookieValue = sessionCookie.slice(COOKIE_NAME.length + 1);
      const session = await verifyCookie(cookieValue);
      if (session) {
        // Pass through to origin with session info
        const modifiedRequest = new Request(request);
        modifiedRequest.headers.set('X-Admin-Session', 'valid');
        modifiedRequest.headers.set('X-Admin-IP', session.ip);
        return fetch(modifiedRequest);
      }
    }

    // POST: validate Turnstile token + password
    if (request.method === 'POST') {
      try {
        const body = await request.json();
        const ip = request.headers.get('CF-Connecting-IP') || '127.0.0.1';

        // Verify Turnstile
        const turnstileResult = await verifyTurnstile(body.token, ip);
        if (!turnstileResult.success) {
          return new Response(JSON.stringify({
            success: false,
            error: 'turnstile_failed',
            details: turnstileResult['error-codes'] || ['invalid-input']
          }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' }
          });
        }

        // Verify password via admin-gate
        const gateResult = await verifyPassword(body.token, body.password, ip);
        if (!gateResult.success) {
          const status = gateResult.rate_limited ? 429 : 401;
          return new Response(JSON.stringify(gateResult), {
            status,
            headers: { 'Content-Type': 'application/json' }
          });
        }

        // Create signed session cookie
        const session = {
          ip,
          created: Date.now(),
          exp: Date.now() + SESSION_TTL * 1000
        };
        const signedCookie = await signCookie(session);

        return new Response(JSON.stringify({
          success: true,
          redirect: '/admin'
        }), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Set-Cookie': `${COOKIE_NAME}=${signedCookie}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${SESSION_TTL}`
          }
        });
      } catch (err) {
        return new Response(JSON.stringify({
          success: false,
          error: 'invalid_request'
        }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // GET: return challenge page
    const error = url.searchParams.get('error') || '';
    return new Response(getChallengeHTML(TURNSTILE_SITEKEY, error ? decodeURIComponent(error) : ''), {
      status: 200,
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
};
