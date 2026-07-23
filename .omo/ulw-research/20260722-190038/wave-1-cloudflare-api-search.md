# Wave 1 — Cloudflare OpenAPI spec dump (ai-gateway tag)

Source: `cloudflare-api_search` against the canonical Cloudflare OpenAPI spec.

## Endpoint inventory (ai-gateway tag)

Critical paths (filtered to provider-credential-relevant):

| Method | Path | Summary |
|---|---|---|
| GET | `/accounts/{account_id}/ai-gateway/gateways` | List Gateways |
| POST | `/accounts/{account_id}/ai-gateway/gateways` | Create a new Gateway |
| GET | `/accounts/{account_id}/ai-gateway/gateways/{id}` | Fetch a Gateway |
| **PUT** | **`/accounts/{account_id}/ai-gateway/gateways/{id}`** | **Update a Gateway** |
| DELETE | `/accounts/{account_id}/ai-gateway/gateways/{id}` | Delete a Gateway |
| GET | `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/url/{provider}` | Get Gateway URL |
| **GET** | **`/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs`** | **List Provider Configs** |
| **POST** | **`/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs`** | **Create a new Provider Configs** |
| GET | `/accounts/{account_id}/ai-gateway/custom-providers` | List Account Providers |
| POST | `/accounts/{account_id}/ai-gateway/custom-providers` | Create a new Account Provider |
| PATCH | `/accounts/{account_id}/ai-gateway/custom-providers/{id}` | Update a Account Provider |
| PATCH | `/accounts/{account_id}/ai-gateway/secrets_store` (assumed) | Secret rotation via Secrets Store |

## EXPAND leads surfaced

- **LEAD-1**: The official spec shows `POST .../provider_configs` for Create but I see a separate "Update a Provider Configs" entry on a sister reference page (cloudflare.hexdocs.pm) that uses `PUT .../provider_configs/{id}`. Need to confirm whether this is the canonical secret-rotation endpoint.
- **LEAD-2**: BYOK naming convention `{gateway_id}_{provider_slug}_{alias}` — the alias field IS the key the user is asking about. Need to confirm via primary doc how the runtime picks between `default` and a custom alias like `Lockinlabs`.
- **LEAD-3**: The Secrets Store is the underlying secret store — need to verify whether AI Gateway directly persists the secret, or whether API callers must pre-create a Secrets Store entry with the exact name.

## Source reliability
- Primary (Cloudflare canonical spec): HIGH
