# Claim Graph: Cloudflare AI Gateway + Workers webhook verification (FINAL)

## Verified claims (Phase 3b gate cleared)

| claim_id | statement | risk | independent source domains | observation groups | counter-search | primary source | status |
|---|---|---|---|---|---|---|---|
| C1 | `PUT /accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}` is the canonical endpoint to update a Cloudflare AI Gateway provider config (overwriting the secret) | high | cloudflare.com (api docs), hexdocs.pm, github.com (Elixir SDK) | 3 | Yes — Alchemy claims "no update API" but multiple independent sources confirm it | Cloudflare OpenAPI spec | supported |
| C2 | The PUT body accepts `alias`, `default_config`, `provider_slug` (required) plus `rate_limit`, `rate_limit_period`, `secret`, `secret_id` (optional). The response returns only `secret_id` + `secret_preview` (last 4 chars), never the secret itself | high | cloudflare.com (api docs), hexdocs.pm, v2.alchemy.run | 3 | Yes | Cloudflare /api/ docs page + hexdocs schema | supported |
| C3 | Auth is `Authorization: Bearer $CLOUDFLARE_API_TOKEN` with `Content-Type: application/json`. Required token scope for write operations: `AI Gateway - Edit` | normal | cloudflare.com (api docs, manage-gateway doc, custom-providers doc) | 3 | Yes | Cloudflare auth doc | supported |
| C4 | `alias` is the per-(gateway, provider) discriminator. `default` is the implicit fallback; any other string (`Lockinlabs`, `production`, `testing`, ...) is a custom alias. Selected at request time via `cf-aig-byok-alias` request header | high | cloudflare.com (BYOK doc, REST API doc) | 2 | Yes | Cloudflare BYOK doc | supported |
| C5 | Workers can verify webhook signatures with `crypto.subtle.importKey("raw", bytes, {name:"HMAC", hash:"SHA-256"}, false, ["verify"])` then `await crypto.subtle.verify("HMAC", key, sig, data)`. `subtle.verify` is timing-safe by spec — no extra constant-time compare needed | high | cloudflare.com (Workers examples), bree-sharp.com, gethook.to, flaviocopes.com, jross.me, gethookmesh.io, stackoverflow | 7 | Yes | Cloudflare Workers "Sign requests" example | supported |
| C6 | The signed-payload format is vendor-specific. Stripe: `t=<ts>,v1=<hex>` over `<ts>.<rawBody>`. GitHub: `X-Hub-Signature-256: sha256=<hex>` over `<rawBody>`. Svix: `svix-id`, `svix-timestamp`, `svix-signature` over `<id>.<ts>.<rawBody>` (base64 sig) | normal | stripe.com (implied), docs.github.com, docs.svix.com, bree-sharp.com | 4 | Yes | Vendor webhook docs + Worker example | supported |

## Unresolved / refuted
(none)
