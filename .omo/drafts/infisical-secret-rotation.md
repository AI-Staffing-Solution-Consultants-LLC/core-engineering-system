---
slug: infisical-secret-rotation
status: awaiting-approval
intent: clear
review_required: false
pending-action: write .omo/plans/infisical-secret-rotation.md
approach: Three-deliverable framework: (1) Infisical rotation adapter configs as Python deployment scripts in CORE-Modules/Inference-Tokenomics/, (2) a Cloudflare Workers webhook receiver (src/rotation_sync.js) that authenticates Infisical webhooks and PUTs new keys to the AI Gateway API, (3) INFERENCE_README.md documenting the full rotation lifecycle, webhook schema, and rollback procedures. Push to dev branch of AI-Staffing-Solution-Consultants-LLC/core-engineering-system.
---

# Draft: infisical-secret-rotation

## Components (topology ledger)
| ID | Outcome | Status | Evidence |
|----|---------|--------|----------|
| C1 | Infisical rotation adapter configs (OpenRouter dual-phase + GCP SA single-phase) deployed to CORE-Modules/Inference-Tokenomics/ | active | existing: CORE-Modules/Inference-Tokenomics/ |
| C2 | Cloudflare Workers rotation_sync.js with HMAC-SHA256 webhook verification and AI Gateway PUT overwrites for 'default' and 'Lockinlabs' aliases | active | existing: src/router.js pattern |
| C3 | INFERENCE_README.md with full lifecycle docs, webhook schema, and disaster-recovery rollback | active | existing: README.md conventions |
| C4 | All files staged and pushed to dev branch of AI-Staffing-Solution-Consultants-LLC/core-engineering-system | active | existing: .gitignore, README.md |

## Open assumptions (announced defaults)
| Assumption | Adopted Default | Rationale | Reversible? |
|-----------|----------------|-----------|-------------|
| Infisical webhook secret stored as CF Worker secret `INFISICAL_WEBHOOK_SECRET` | Yes | Standard secret management pattern per existing wrangler.toml | Yes |
| GCP SA key rotation uses single-phase (not dual-phase) per Infisical docs | Yes | GCP IAM does not support two concurrent keys per SA | No |
| OpenRouter rotation interval = 30 days, rotateAt 00:00 UTC | Yes | Matches user spec | Yes |
| Gateway aliases target 'default' and 'Lockinlabs' only | Yes | Matches user spec exactly | N/A |
| Provider slug for OpenRouter = 'openrouter' in Cloudflare AI Gateway | Yes | Standard CF slug | Yes |
| Cloudflare Account ID referenced as env var CF_ACCOUNT_ID | Yes | Standard pattern from existing router.js | Yes |

## Findings (cited)
- Infisical OpenRouter adapter: POST /api/v2/secret-rotations/open-router-api-key, dual-phase, 30-day interval
- Infisical GCP SA adapter: POST /api/v2/secret-rotations/gcp-service-account-key, single-phase (old key revoked in-place)
- Cloudflare AI Gateway PUT: PUT /accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id} with alias, provider_slug, secret fields
- Webhook signature: x-infisical-signature: t=<unix_ms>;<hex_hmac_sha256>, signed payload = JSON.stringify(body) with embedded timestamp
- Existing pattern: src/router.js uses Cloudflare Worker fetch with KV bindings and tamper-evident ledger

## Decisions
- Rotation sync worker placed at src/rotation_sync.js (cloudflare edge directory, separate from router.js)
- Webhook handler is a standalone Cloudflare Worker (not a Pages Function) for secrets binding access
- GCP SA key rotation gets a 90-day interval (not 30) to reduce IAM key proliferation
- All secrets pushed via Infisical → no hardcoded values in any file

## Scope IN
- Infisical rotation adapter configs (OpenRouter + GCP SA key)
- Cloudflare Worker rotation_sync.js with webhook verification + AI Gateway PUT
- INFERENCE_README.md documentation
- Git staging and push to dev branch

## Scope OUT (Must NOT have)
- No mock/stub values — all configs reference env vars or secrets
- No changes to existing track-a/track-b services
- No modifications to existing wrangler.toml or router.js
- No actual secret values committed to git
- No CI/CD pipeline creation (out of scope)

## Open questions
None — all owner-decisions resolved via defaults above.

## Approval gate
status: awaiting-approval
