# Intent Diff: Cloudflare AI Gateway provider secrets overwrite + Workers webhook verification

## Core question
What is the exact REST API endpoint, auth method, request body schema, and HTTP method required to update/overwrite provider credentials (API keys/secrets) on a Cloudflare AI Gateway gateway alias, and how do you target specific aliases such as 'default' and a custom one like 'Lockinlabs'? Also: how do you verify webhook signatures inside a Cloudflare Worker?

## Axes (4 orthogonal)

### Axis A — AI Gateway gateway management endpoints (CRUD)
- REST path for creating, listing, getting, updating, deleting a Cloudflare AI Gateway "gateway"
- Path shape: `/accounts/{account_id}/ai-gateway/gateways` and `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}`
- Method: PUT for create-or-replace, PATCH for partial update, GET for read, DELETE
- Request body fields, response shape, account_id source

### Axis B — AI Gateway provider credentials (the secret-overwrite target)
- Whether provider credentials live on the gateway resource itself (e.g., `providers`, `auth` fields) or as separate resources
- Path shape: `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/providers` and per-provider sub-resources
- Whether the secret-overwrite endpoint is `PUT /accounts/{account_id}/ai-gateway/gateways/{gateway_id}/providers/{provider_name}` or the secret is part of a bigger body
- Aliases: how custom URL slugs (e.g., 'Lockinlabs') are created/updated — separate alias endpoints vs. `cf_id` vs. `slug`

### Axis C — Authentication and headers
- Required header: `Authorization: Bearer <token>` (or `X-Auth-Email` + `X-Auth-Key` legacy)
- Required: `Content-Type: application/json`
- Account ID in path; how to get account ID
- Token scopes (Cloudflare API token with `AI Gateway: Edit` permission)

### Axis D — Cloudflare Workers webhook signature verification
- The general `crypto.subtle.verify` pattern with HMAC-SHA256
- Webhook signature header conventions: `Stripe-Signature`, `GitHub-Hub-Signature-256`, `svix-*` etc.
- `crypto.subtle.importKey` + `verify` for constant-time comparison
- Timestamp tolerance / replay protection
- Polyfill caveats: subtle.crypto is available on Workers runtime

## Codebase relevant
- No (this is a pure documentation/API research task — no source code to grep)

## External sources
- YES: developers.cloudflare.com/ai-gateway/ (official docs)
- YES: developers.cloudflare.com/api/operations/ai-gateway-* (API reference)
- YES: GitHub.com/cloudflare/cloudflare-docs (canonical doc source)
- YES: openapi.cf-data.org or Cloudflare's published OpenAPI spec
- YES: developers.cloudflare.com/workers/runtime/apis/web-crypto/ (subtle crypto reference)

## Verification likely
- YES — Phase 3: spin up a Worker that calls the AI Gateway PUT endpoint against a sandbox and verify it accepts the body. Run the subtle.crypto verify example against a known fixture.

## Final material format
- Markdown only (user asked for a "deliverable" with concrete spec — concise Markdown report with permalinks and code samples)
