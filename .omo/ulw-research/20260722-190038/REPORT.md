# Cloudflare AI Gateway — Overwriting Provider Secrets + Workers Webhook Verification

**Researched:** 2026-07-22 · **Status:** Verified · **Format:** Markdown deliverable

This is the answer. Every claim below is backed by a primary Cloudflare source and (where it could be tested) by executed code in `verify/`.

---

## Part 1 — The API endpoint for overwriting provider credentials

### The exact endpoint

```
PUT https://api.cloudflare.com/client/v4/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}
```

| Field | Value |
|---|---|
| Method | `PUT` |
| Auth header | `Authorization: Bearer $CLOUDFLARE_API_TOKEN` |
| Content-Type | `application/json` |
| Required token scope | `AI Gateway - Edit` |
| Path params | `account_id`, `gateway_id`, `id` (the provider-config ID returned from create) |
| Source | [Cloudflare API reference](https://developers.cloudflare.com/api/resources/ai_gateway/subresources/provider_configs/) (confirmed in the canonical OpenAPI spec) |

### Request body

```json
{
  "alias": "Lockinlabs",
  "default_config": false,
  "provider_slug": "openai",
  "rate_limit": 100,
  "rate_limit_period": 60,
  "secret": "sk-NEW-rotated-key-value-here"
}
```

| Field | Required | Notes |
|---|---|---|
| `alias` | yes | The alias the user asked about — `"default"` is the implicit fallback, any other string (e.g. `"Lockinlabs"`) is a custom alias |
| `default_config` | yes | Boolean — mark `true` only on the system-default config for a given (gateway, provider) |
| `provider_slug` | yes | `"openai"`, `"anthropic"`, `"workers-ai"`, `"google-ai-studio"`, etc. |
| `rate_limit` | no | Per-config rate limit |
| `rate_limit_period` | no | Window in seconds for the rate limit |
| `secret` | no (one of these) | **Plaintext API key** — write-only, never returned in the response |
| `secret_id` | no (one of these) | Reference to an existing Secrets Store secret (mutually exclusive with `secret`) |

### Response (write-only secret)

```json
{
  "result": {
    "id": "00000000-0000-0000-0000-000000000000",
    "alias": "Lockinlabs",
    "default_config": false,
    "gateway_id": "my-gateway",
    "modified_at": "2026-07-22T19:00:38.000Z",
    "provider_slug": "openai",
    "secret_id": "abcd1234-...",
    "secret_preview": "wxyz",
    "rate_limit": 100,
    "rate_limit_period": 60
  },
  "success": true
}
```

The `secret` value you sent is **never echoed back**. The response returns `secret_id` (a Secrets Store reference) and `secret_preview` (last 4 characters of the secret) for display.

### cURL

```bash
curl -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/ai-gateway/gateways/my-gateway/provider_configs/$PROVIDER_CONFIG_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "alias": "Lockinlabs",
        "default_config": false,
        "provider_slug": "openai",
        "secret": "sk-NEW-rotated-key-value-here"
      }'
```

### From a Cloudflare Worker

```ts
const res = await fetch(
  `https://api.cloudflare.com/client/v4/accounts/${env.ACCOUNT_ID}/ai-gateway/gateways/${gatewayId}/provider_configs/${configId}`,
  {
    method: "PUT",
    headers: {
      "Authorization": `Bearer ${env.CF_API_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      alias: "Lockinlabs",
      default_config: false,
      provider_slug: "openai",
      secret: newKey,
    }),
  }
);
const data = await res.json();
```

---

## Part 2 — How to target specific aliases (the `default` vs `Lockinlabs` question)

The `alias` field on the body is the **per-(gateway, provider) discriminator**. You can create as many provider configs per provider as you want, each with a different alias.

| Alias value | What it means |
|---|---|
| `"default"` | The implicit fallback. Request clients don't need to set any header to use it. |
| `"Lockinlabs"` (or any other string) | A custom alias. Request clients select it via the `cf-aig-byok-alias: Lockinlabs` request header. |

### Runtime request routing (how a caller picks the alias)

```bash
# Uses the "default" alias (no header needed)
curl https://gateway.ai.cloudflare.com/v1/$ACCOUNT_ID/$GATEWAY_ID/openai/chat/completions \
  -H "cf-aig-authorization: Bearer $CF_AIG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [...]}'

# Uses the "Lockinlabs" alias
curl https://gateway.ai.cloudflare.com/v1/$ACCOUNT_ID/$GATEWAY_ID/openai/chat/completions \
  -H "cf-aig-authorization: Bearer $CF_AIG_TOKEN" \
  -H "cf-aig-byok-alias: Lockinlabs" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [...]}'
```

### To **rotate** the secret for an existing alias

1. `GET /accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs` — find the config with the alias you want (e.g. `alias = "Lockinlabs"`). Copy its `id`.
2. `PUT` to the same `/provider_configs/{id}` with a new `secret` value. The alias, provider, and rate limits stay the same.

### To **create** a brand-new alias

Use `POST /accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs` with the same body shape. The Secrets Store entry is auto-created from the `secret` value.

> **Note**: If you call the API (instead of the dashboard), Cloudflare's underlying Secrets Store entry is named `{gateway_id}_{provider_slug}_{alias}` and must exist with scope `["ai_gateway"]` before the provider-config call. Passing `secret: <plaintext>` on the body takes care of this for you. ([BYOK doc](https://developers.cloudflare.com/ai-gateway/configuration/bring-your-own-keys/))

---

## Part 3 — Webhook signature verification in Cloudflare Workers

### The pattern (HMAC-SHA256, generic)

```ts
async function verifyWebhook(
  request: Request,
  secret: string
): Promise<{ ok: true; body: string } | { ok: false; status: number; reason: string }> {
  const sig = request.headers.get("webhook-signature");
  if (!sig) return { ok: false, status: 401, reason: "missing signature" };

  // CRITICAL: read the raw body BEFORE any JSON.parse — the stream is one-shot.
  const rawBody = await request.text();

  // Import the secret as a CryptoKey (do this once at module scope and cache it)
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,                 // not extractable
    ["verify"]             // only need verify, not sign
  );

  // Build the signed payload — format is vendor-specific (see below)
  const signedPayload = new TextEncoder().encode(/* ... */);

  // Decode the signature (vendor-specific: hex or base64)
  const sigBytes = /* ... */;

  // subtle.verify is timing-safe by spec — do NOT compare with ===.
  const ok = await crypto.subtle.verify("HMAC", key, sigBytes, signedPayload);
  if (!ok) return { ok: false, status: 401, reason: "invalid signature" };

  return { ok: true, body: rawBody };
}
```

### Vendor-specific signed-payload formats

| Provider | Headers | Signed payload | Signature encoding |
|---|---|---|---|
| **Stripe** | `Stripe-Signature: t=<ts>,v1=<hex>[,v1=<hex>...]` | `<ts>.<rawBody>` | hex (HMAC-SHA256) |
| **GitHub** | `X-Hub-Signature-256: sha256=<hex>` | `<rawBody>` | hex (HMAC-SHA256) |
| **Svix** (Clerk, Resend, Lob) | `svix-id`, `svix-timestamp`, `svix-signature: <b64>[, <b64>...]` | `<id>.<ts>.<rawBody>` | base64 (HMAC-SHA256) |
| **CloudConvert** | `CloudConvert-Signature: <hex>` | `<rawBody>` | hex (HMAC-SHA256) |

### Stripe-specific example (verified by execution — see `verify/webhook-verify.md`)

```ts
async function verifyStripeWebhook(request: Request, env: { STRIPE_WEBHOOK_SECRET: string }) {
  const rawBody = await request.text();
  const sigHeader = request.headers.get("stripe-signature");
  if (!sigHeader) return new Response("missing sig", { status: 400 });

  // Parse "t=...,v1=...,v1=..."
  const parts = Object.fromEntries(
    sigHeader.split(",").map(p => p.split("=", 2))
  );
  const t = parts.t;
  const v1s = sigHeader.split(",").filter(p => p.startsWith("v1=")).map(p => p.slice(3));
  if (!t || v1s.length === 0) return new Response("malformed sig", { status: 400 });

  // Replay window: reject if older than 5 minutes
  const age = Math.abs(Math.floor(Date.now() / 1000) - Number(t));
  if (age > 300) return new Response("stale", { status: 401 });

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(env.STRIPE_WEBHOOK_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );

  // Signed payload is "<t>.<rawBody>"
  const signedPayload = new TextEncoder().encode(`${t}.${rawBody}`);

  // Accept if ANY v1 signature matches (key rotation)
  for (const hex of v1s) {
    const sigBytes = Uint8Array.from(hex.match(/.{2}/g)!.map(h => parseInt(h, 16)));
    const ok = await crypto.subtle.verify("HMAC", key, sigBytes, signedPayload);
    if (ok) {
      // Valid! Now safe to JSON.parse(rawBody)
      const event = JSON.parse(rawBody);
      return new Response(JSON.stringify({ received: true }), { status: 200 });
    }
  }
  return new Response("invalid signature", { status: 401 });
}
```

### Hard rules for webhook verification on Workers

1. **Use `crypto.subtle.verify`, not `===` byte comparison** — `verify` is constant-time by the Web Crypto spec. A manual `===` short-circuits on first mismatch and leaks timing information.
2. **Read the body as raw bytes first** — call `request.text()` or `request.arrayBuffer()` BEFORE `request.json()`. The body stream is one-shot in V8/Workers; once consumed by `.json()` you cannot get the bytes back to verify the HMAC.
3. **Always check a timestamp** — include a `t` or `svix-timestamp` in the signed payload and reject anything older than 5 minutes. Otherwise an attacker who once captured a valid payload can replay it forever.
4. **Cache the imported `CryptoKey`** — `importKey` is expensive. Do it once at module scope, not per-request.
5. **Never use Node's `crypto.createHmac` or `crypto.timingSafeEqual`** — these are Node-only. Use the Web Crypto API exclusively.

---

## Verification artifacts

Two verification scripts were executed and passed:

- `verify/webhook-verify.mjs` — verifies that `crypto.subtle.verify` accepts legitimate signatures and rejects tampered bodies, wrong secrets, and replay attacks. **Result: 4/4 paths CONFIRMED.**
- `verify/aigateway-body-build.mjs` — constructs two valid PUT request bodies (`alias=Lockinlabs` and `alias=default`) and validates them against the documented schema. **Result: VALID.**

Run them yourself with `node verify/webhook-verify.mjs` and `node verify/aigateway-body-build.mjs`.

## Sources

1. Cloudflare /api/ — `developer.cloudflare.com/api/resources/ai_gateway/subresources/provider_configs/` (primary)
2. Cloudflare BYOK doc — `developers.cloudflare.com/ai-gateway/configuration/bring-your-own-keys/`
3. Cloudflare hexdocs — `hexdocs.pm/cloudflare/ai_gateway_provider_configs.html` (independent SDK docs)
4. FreedomBen/cloudflare_api (Elixir SDK source) — `github.com/freedomben/cloudflare_api`
5. Cloudflare "Sign requests" Worker example — `developers.cloudflare.com/workers/examples/signing-requests/`
6. bree-sharp.com — Stripe webhook in a Worker, no SDK
7. gethook.to — Webhook signature verification in edge runtimes
8. Cloudflare Secrets Store Patch a secret — `developers.cloudflare.com/api/resources/secrets_store/.../secrets/methods/edit/`
9. Cloudflare Authenticated Gateway doc — `developers.cloudflare.com/ai-gateway/configuration/authentication/`
10. Cloudflare Manage gateways doc — `developers.cloudflare.com/ai-gateway/configuration/manage-gateway/`
