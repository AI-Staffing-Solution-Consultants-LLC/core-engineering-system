# Wave 2 — Update endpoint confirmation

## Confirmed endpoint inventory (Cloudflare canonical OpenAPI spec)

| Method | Path | Summary |
|---|---|---|
| GET | `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs` | List Provider Configs |
| POST | `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs` | Create a new Provider Configs |
| **PUT** | **`/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}`** | **Update a Provider Configs** ← the secret-overwrite endpoint |
| DELETE | `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}` | Delete a Provider Configs |

Tags: `ai-gateway`, `AI Gateway Provider Configs`.

## BYOK alias semantics (from canonical doc)

- Each provider key has an `alias` string; `default` is the fallback.
- Per-alias request header: `cf-aig-byok-alias: <alias>` selects which key to use at request time.
- Multi-alias support: a single (gateway, provider) can have many aliases — `default`, `production`, `testing` are all valid.
- Secrets Store naming convention for API-created keys: `{gateway_id}_{provider_slug}_{alias}` (e.g. `my-gateway_anthropic_default`).
- The dashboard auto-creates the Secrets Store secret; the API caller must pre-create it with the exact name.

## Source reliability
- Cloudflare canonical OpenAPI spec: HIGH (this is the source of truth that powers the docs site)
- developers.cloudflare.com BYOK page: HIGH (first-party)
