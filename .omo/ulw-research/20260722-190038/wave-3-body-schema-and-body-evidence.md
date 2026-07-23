# Wave 3 — Body schema, response shape, and independent library evidence

## 1. POST and PUT body parameters (from /api/resources/ai_gateway/subresources/provider_configs/)

POST `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs` body parameters:
- `alias: string` — required
- `default_config: boolean` — required
- `provider_slug: string` — required
- `rate_limit: optional number`
- `rate_limit_period: optional number`
- `secret: optional string` — plaintext API key (write-only)
- `secret_id: optional string` — reference to existing Secrets Store secret

PUT `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}` — same body shape (confirmed by hexdocs and Elixir lib; the canonical /api/ docs page only documents POST, but the OpenAPI spec includes the PUT).

## 2. Response shape (both POST and PUT)

```json
{
  "result": {
    "id": "string",
    "alias": "string",
    "default_config": true,
    "gateway_id": "my-gateway",
    "modified_at": "2019-12-27T18:11:19.117Z",
    "provider_slug": "string",
    "secret_id": "string",
    "secret_preview": "string",
    "rate_limit": 0,
    "rate_limit_period": 0
  },
  "success": true
}
```

**CRITICAL**: The response never includes the `secret` field. It returns only `secret_id` (Secrets Store reference) and `secret_preview` (last 4 chars of the secret for display). The `secret` field on the request body is write-only.

## 3. Independent corroboration

| Source | Evidence | Reliability |
|---|---|---|
| Cloudflare OpenAPI spec (canonical) | PUT endpoint exists at `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}` with summary "Update a Provider Configs" | HIGH |
| Cloudflare developers docs (`/api/resources/ai_gateway/subresources/provider_configs/`) | POST body schema with `secret` and `secret_id` fields | HIGH |
| `freedomben/cloudflare_api` (Elixir SDK) on GitHub | `update/5` function calls `Tesla.put(config_path(account_id, gateway_id, config_id), params)` — confirms path AND PUT method | HIGH (independent implementation) |
| `cloudflare` 0.5.0 hexdocs package | Documents PUT endpoint with same response shape | HIGH (independent client lib) |
| BYOK doc page | Confirms alias semantics and Secrets Store naming convention | HIGH |
| Cloudflare changelog (2026-06-12, 2026-05-21, 2026-04-02, 2025-06-03) | No specific changelog entry for "provider_configs Update" — the endpoint pre-dates BYOK renaming | MEDIUM |
| Alchemy docs | **Inaccurate** claim that "Cloudflare exposes no update API for provider configs" — the endpoint exists | LOW (counter-evidence only) |

## 4. The `default` vs custom-alias mechanism (CONFIRMED)

- "default" is the implicit alias used when no `cf-aig-byok-alias` header is set on a request.
- Any string is a valid custom alias (`production`, `testing`, `Lockinlabs`, etc.).
- A single (gateway, provider) tuple can have multiple provider configs with different aliases — runtime selects the right one via the request header.
- The `default_config: true` field on the config body marks which alias is the system default; only one config per (gateway, provider) should have `default_config: true`.

## 5. Authentication (CONFIRMED, multiple sources)

- Header: `Authorization: Bearer $CLOUDFLARE_API_TOKEN`
- Required token scope: `AI Gateway - Edit` (for write operations)
- Account ID obtained via `wrangler whoami` (Workers) or `GET /accounts` (API)
- Legacy `X-Auth-Email` + `X-Auth-Key` still works for some endpoints (Secrets Store Patch) but is deprecated.

## 6. Webhook verification pattern (CONFIRMED, multiple sources)

- Workers runtime exposes `crypto.subtle` (Web Crypto API).
- HMAC-SHA256: `await crypto.subtle.importKey("raw", keyBytes, {name: "HMAC", hash: "SHA-256"}, false, ["verify"])` then `await crypto.subtle.verify("HMAC", key, sigBytes, dataBytes)`.
- `subtle.verify` is timing-safe by spec — DO NOT roll your own constant-time compare.
- The body MUST be read as raw bytes (`request.text()` or `request.arrayBuffer()`) BEFORE parsing JSON — the stream is one-shot.
- Replay protection: include a timestamp in the signed payload, reject anything older than ~5 minutes.
- Vendor-specific header conventions:
  - Stripe: `Stripe-Signature: t=<ts>,v1=<hex>` — signed payload is `<ts>.<rawBody>`.
  - GitHub: `X-Hub-Signature-256: sha256=<hex>` — signed payload is `<rawBody>`.
  - Svix (Clerk, Resend, etc.): `svix-id`, `svix-timestamp`, `svix-signature` — signed payload is `<svix-id>.<svix-timestamp>.<rawBody>`, base64-encoded signature.
  - CloudConvert: `CloudConvert-Signature: <hex>` — signed payload is `<rawBody>`.
