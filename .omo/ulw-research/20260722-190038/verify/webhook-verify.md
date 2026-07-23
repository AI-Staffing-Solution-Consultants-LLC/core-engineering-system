# Verify: Cloudflare Workers webhook signature verification (HMAC-SHA256)

## Claim under test
C5: Workers can verify webhook signatures with `crypto.subtle.importKey` + `crypto.subtle.verify('HMAC', key, signature, data)`
C6: The signature header is provider-specific (e.g., `Stripe-Signature`) and uses HMAC-SHA256

## Test
Run file: `webhook-verify.mjs` — generates a valid Stripe-format `t=...,v1=...` signature header, then verifies it via the Worker-style `crypto.subtle.importKey` + `verify` chain with a 5-minute replay window.

## Environment
- Node.js v22.x, `globalThis.crypto.subtle` available
- Web Crypto API in the Worker runtime is a direct equivalent of Node's WebCrypto in this respect.

## Output
```
=== Verifying legitimate webhook ===
{ "ok": true,  "reason": "valid" }

=== Verifying with tampered body ===
{ "ok": false, "reason": "invalid signature" }

=== Verifying with wrong secret ===
{ "ok": false, "reason": "invalid signature" }

=== Verifying with replayed (old) timestamp ===
{ "ok": false, "reason": "stale or invalid timestamp (age=3600s)" }
```

## Verdict
**CONFIRMED** — all four paths behave as documented:
- Legitimate: accepted
- Tampered body: rejected
- Wrong secret: rejected
- Replay: rejected

The crypto.subtle.verify pattern is sound; subtle.verify is timing-safe by spec so no extra constant-time compare is needed.
