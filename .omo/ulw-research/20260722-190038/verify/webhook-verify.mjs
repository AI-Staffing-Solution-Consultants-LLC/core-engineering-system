// Verification: Cloudflare Workers crypto.subtle.verify against a Stripe-format webhook
// This proves the importKey + verify chain works exactly as the docs describe.

const encoder = new TextEncoder();
const decoder = new TextDecoder();

// The Webhook Secret that would be stored in env.STRIPE_WEBHOOK_SECRET
const WEBHOOK_SECRET = 'whsec_test_supersecretkey_1234567890abcdef';

// Raw body as it arrived on the request
const rawBody = JSON.stringify({
  id: 'evt_test_123',
  type: 'payment.succeeded',
  data: { amount: 4200 },
});

// Signature header as Stripe would have sent it
// t = unix timestamp, v1 = hex(HMAC-SHA256("whsec_..." ,  `${t}.${rawBody}`))
async function sign(secret, payload) {
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(payload));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

const t = Math.floor(Date.now() / 1000);
const signedPayload = `${t}.${rawBody}`;
const v1 = await sign(WEBHOOK_SECRET, signedPayload);
const signatureHeader = `t=${t},v1=${v1}`;

console.log('=== Generated signature header ===');
console.log(signatureHeader);
console.log();

// Simulate the Worker verifier
async function verifyStripeWebhook(rawBody, signatureHeader, endpointSecret, toleranceSec = 300) {
  if (!signatureHeader) return { ok: false, reason: 'missing header' };

  const parts = signatureHeader.split(',').reduce((acc, p) => {
    const [k, v] = p.split('=', 2);
    if (k === 't') acc.t = v;
    if (k === 'v1') acc.v1.push(v);
    return acc;
  }, { t: null, v1: [] });

  if (!parts.t || parts.v1.length === 0) return { ok: false, reason: 'malformed' };

  const age = Math.abs(Math.floor(Date.now() / 1000) - Number(parts.t));
  if (!Number.isFinite(Number(parts.t)) || age > toleranceSec) {
    return { ok: false, reason: `stale or invalid timestamp (age=${age}s)` };
  }

  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(endpointSecret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['verify']
  );

  const signedPayload = encoder.encode(`${parts.t}.${rawBody}`);
  const sigBytes = Uint8Array.from(
    parts.v1[0].match(/.{2}/g).map(h => parseInt(h, 16))
  );

  const ok = await crypto.subtle.verify('HMAC', key, sigBytes, signedPayload);
  return { ok, reason: ok ? 'valid' : 'invalid signature' };
}

console.log('=== Verifying legitimate webhook ===');
const good = await verifyStripeWebhook(rawBody, signatureHeader, WEBHOOK_SECRET);
console.log(JSON.stringify(good, null, 2));
console.log();

console.log('=== Verifying with tampered body ===');
const tampered = await verifyStripeWebhook(rawBody + 'x', signatureHeader, WEBHOOK_SECRET);
console.log(JSON.stringify(tampered, null, 2));
console.log();

console.log('=== Verifying with wrong secret ===');
const wrongSecret = await verifyStripeWebhook(rawBody, signatureHeader, 'whsec_WrongSecretValue');
console.log(JSON.stringify(wrongSecret, null, 2));
console.log();

console.log('=== Verifying with replayed (old) timestamp ===');
const oldSig = `t=${t - 3600},v1=${await sign(WEBHOOK_SECRET, `${t - 3600}.${rawBody}`)}`;
const replay = await verifyStripeWebhook(rawBody, oldSig, WEBHOOK_SECRET);
console.log(JSON.stringify(replay, null, 2));
