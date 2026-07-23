# infisical-secret-rotation - Work Plan

## TL;DR (For humans)

**What you'll get:** A fully automated secret rotation pipeline that rotates your OpenRouter API key every 30 days and GCP service account key every 90 days via Infisical, then instantly pushes fresh credentials into your Cloudflare AI Gateway aliases ('default' and 'Lockinlabs') through a webhook-triggered Workers edge function — zero downtime, zero manual key management.

**Why this approach:** OpenRouter supports true dual-phase rotation (old key stays valid during sync window), while GCP SA keys require single-phase rotation (old key revoked immediately). The Cloudflare Worker webhook receiver validates HMAC-SHA256 signatures from Infisical before touching any gateway config, ensuring only authenticated rotation events can modify your provider secrets.

**What it will NOT do:** Will not modify your existing Track A/Track B services, router.js, or wrangler.toml. Will not commit any secret values. Will not create CI/CD pipelines.

**Effort:** Medium
**Risk:** Medium — depends on Infisical App Connections being pre-configured for OpenRouter and GCP

**Decisions to sanity-check:** GCP SA key rotation set to 90-day interval (not 30) to reduce IAM key proliferation risk. Provider slug for OpenRouter in AI Gateway assumed to be 'openrouter'. Cloudflare Account ID referenced via CF_ACCOUNT_ID env var.

Your next move: Approve this plan, then run `/start-work` to execute. Full execution detail follows below.

---

> TL;DR (machine): Medium effort, Medium risk. 3 deliverables: Infisical rotation adapter configs, Cloudflare Worker webhook receiver for AI Gateway PUT overwrites, INFERENCE_README.md docs. All pushed to dev branch.

## Scope

### Must have
- Infisical rotation adapter deployment configs for OpenRouter (dual-phase, 30-day) and GCP SA key (single-phase, 90-day)
- Cloudflare Worker `src/rotation_sync.js` that receives Infisical webhooks, verifies HMAC-SHA256 signatures, and PUTs new keys to AI Gateway for 'default' and 'Lockinlabs' aliases
- INFERENCE_README.md documenting the full rotation lifecycle, webhook payload schema, and disaster-recovery rollback procedures
- All files staged and committed to `dev` branch of `AI-Staffing-Solution-Consultants-LLC/core-engineering-system`

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No mock/stub/placeholder secret values in any file — all secrets referenced via env vars or Infisical secret paths
- No modifications to track-a/, track-b/, existing wrangler.toml, or router.js
- No CI/CD pipeline creation
- No new Python dependencies beyond what already exists in requirements.txt
- No actual secret values committed to git (enforced by .gitignore .env* pattern)
- No emoji in any file

## Verification strategy

> Zero human intervention — all verification is agent-executed.

- Test decision: tests-after + manual verification via curl
- Evidence: `.omo/evidence/ulw/<session>/<goalId>/a<attempt>/task-<N>-infisical-secret-rotation.<ext>`

## Execution strategy

### Parallel execution waves

| Wave | Tasks | Rationale |
|------|-------|-----------|
| Wave 1 | Tasks 1-3 | Create all three deliverable files in parallel (no dependencies between them) |
| Wave 2 | Task 4 | Stage, commit, and push all files to dev branch |

### Dependency matrix

| Todo | Depends on | Blocks | Can parallelize with |
|------|-----------|--------|---------------------|
| 1 | None | 4 | 2, 3 |
| 2 | None | 4 | 1, 3 |
| 3 | None | 4 | 1, 2 |
| 4 | 1, 2, 3 | Final verification | None |

## Todos

- [ ] 1. Create Infisical rotation adapter deployment configs
  What to do / Must NOT do:
  Create `CORE-Modules/Inference-Tokenomics/infisical_rotation_config.py` — a Python module that defines the Infisical API request payloads for both rotation adapters. This is NOT a runnable script that calls the API; it is a configuration definition module that documents the exact JSON payloads the operator will use with the Infisical REST API or CLI to create the rotation adapters. Must include:
  - OPENROUTER_ROTATION_CONFIG dict: adapter type `open-router-api-key`, dual-phase, 30-day interval, `rotateAtUtc: {hours: 0, minutes: 0}`, `secretsMapping: {apiKey: "OPEN_ROUTER_API_KEY"}`, parameters with name `openrouter-core-key`, limit 100, limitReset monthly
  - GCP_SA_ROTATION_CONFIG dict: adapter type `gcp-service-account-key`, single-phase, 90-day interval, `rotateAtUtc: {hours: 0, minutes: 0}`, `secretsMapping: {privateKey: "GCP_SERVICE_ACCOUNT_KEY"}`, parameters with serviceAccountEmail placeholder
  - COMMON_FIELDS dict: shared fields including projectId, environment "dev", secretPath "/CORE-Modules/Inference-Tokenomics", isAutoRotationEnabled True
  - DUAL_PHASE_LIFECYCLE dict: documentation of the Active→Inactive→Revoked state machine with the 30-day cadence
  - Module docstring explaining this is a configuration reference, not a runtime script
  Must NOT hardcode any workspaceId, connectionId, or projectId values — use env var references or descriptive placeholders.
  Parallelization: Wave 1 | Blocked by: None | Blocks: 4
  References: CORE-Modules/Inference-Tokenomics/main.py (existing module pattern), CORE-Modules/Inference-Tokenomics/Dockerfile (existing container pattern), infisical_vault_sync.sh:1-51 (existing Infisical auth pattern)
  Acceptance criteria (agent-executed): `python -c "from COREModules.InferenceTokenomics.infisical_rotation_config import OPENROUTER_ROTATION_CONFIG, GCP_SA_ROTATION_CONFIG, DUAL_PHASE_LIFECYCLE; assert OPENROUTER_ROTATION_CONFIG['isAutoRotationEnabled'] is True; assert GCP_SA_ROTATION_CONFIG['rotationInterval'] == 90; assert DUAL_PHASE_LIFECYCLE['states'] == ['Active', 'Inactive', 'Revoked']"` from repo root
  QA scenarios (happy + failure): Happy: module imports cleanly, all three exports exist and have expected values. Failure: missing required keys in config dicts. Evidence: `.omo/evidence/ulw/infisical-secret-rotation/task-1-infisical-secret-rotation.txt`
  Commit: Y | feat(inference-tokenomics): add Infisical rotation adapter config definitions

- [ ] 2. Create Cloudflare Worker rotation_sync.js
  What to do / Must NOT do:
  Create `src/rotation_sync.js` — a standalone Cloudflare Workers script that receives encrypted webhooks from Infisical when a secret rotation occurs, authenticates the HMAC-SHA256 signature, reads the new secret value, and performs a server-side PUT to overwrite the provider key on the Cloudflare AI Gateway for both 'default' and 'Lockinlabs' aliases.
  
  MUST include these exact sections:
  
  **(a) HMAC-SHA256 signature verification:**
  - Parse header `x-infisical-signature: t=<unix_ms>;<hex_hmac_sha256>`
  - Extract timestamp `t` and hex signature
  - Reject if timestamp older than 5 minutes (replay protection)
  - Build signed payload: `JSON.stringify(body)` (body contains the event timestamp)
  - Use `crypto.subtle.importKey` with HMAC SHA-256 on `INFISICAL_WEBHOOK_SECRET` env var
  - Use `crypto.subtle.verify` (constant-time, never === comparison)
  - Cache imported CryptoKey at module scope (importKey is expensive)
  
  **(b) Webhook payload parsing:**
  - Parse the Infisical rotation webhook body (event type: `secrets.rotation-failed` for failures, or custom `secrets.rotation-succeeded` for our needs)
  - Extract: event, project.projectId, project.rotationName, project.secretPath, project.environment
  - Log the rotation event to console (structured JSON)
  
  **(c) Cloudflare AI Gateway PUT overwrite:**
  - For each target alias ('default' and 'Lockinlabs'), perform:
    `PUT https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/ai-gateway/gateways/${CF_AI_GATEWAY_ID}/provider_configs/${configId}`
  - Request body: `{ alias, default_config: false, provider_slug, secret: newKey }`
  - Auth header: `Authorization: Bearer ${CF_API_TOKEN}`
  - Read CF_ACCOUNT_ID, CF_AI_GATEWAY_ID, CF_API_TOKEN from env vars
  - Handle response: log success/failure, return appropriate HTTP status
  
  **(d) Export default handler:**
  - `export default { async fetch(request, env, ctx) { ... } }`
  - Handle CORS preflight OPTIONS
  - Only accept POST requests
  - Return 200 on success, 401 on bad signature, 500 on gateway API failure
  
  Must NOT:
  - Use Node.js crypto module (Workers use Web Crypto API exclusively)
  - Hardcode any secrets or API tokens
  - Import from external npm packages (Workers runtime only)
  - Include any route handlers beyond the webhook endpoint (this is a standalone worker, not a modification of router.js)
  
  Parallelization: Wave 1 | Blocked by: None | Blocks: 4
  References: src/router.js:1-554 (existing Worker pattern with CORS, error handling, ledger writes), cloudflare/functions/admin-gate.js:1-147 (existing Pages Function pattern), wrangler.toml:1-86 (existing bindings pattern)
  Acceptance criteria (agent-executed): `grep -c "crypto.subtle.verify" src/rotation_sync.js` returns at least 1; `grep -c "INFISICAL_WEBHOOK_SECRET" src/rotation_sync.js` returns at least 1; `grep -c "provider_configs" src/rotation_sync.js` returns at least 1; `grep -c "Lockinlabs" src/rotation_sync.js` returns at least 1; `grep -c "default" src/rotation_sync.js` returns at least 2; `node -c src/rotation_sync.js` passes syntax check
  QA scenarios: Happy: valid Infisical webhook with correct HMAC passes verification and triggers AI Gateway PUT. Failure: invalid signature returns 401; expired timestamp returns 401; non-POST returns 405; gateway API error returns 500. Evidence: `.omo/evidence/ulw/infisical-secret-rotation/task-2-infisical-secret-rotation.txt`
  Commit: Y | feat(rotation-sync): add Infisical webhook receiver for Cloudflare AI Gateway secret rotation

- [ ] 3. Create INFERENCE_README.md
  What to do / Must NOT do:
  Create `./INFERENCE_README.md` at repo root — a comprehensive operational document covering:
  
  **(a) System Architecture Overview:**
  - Diagram (ASCII) of the rotation flow: Infisical → Webhook → Cloudflare Worker → AI Gateway PUT
  - Component inventory with file paths
  
  **(b) Infisical Rotation Configuration:**
  - OpenRouter adapter: dual-phase lifecycle (Active→Inactive→Revoked), 30-day interval, rotateAt UTC 00:00
  - GCP SA key adapter: single-phase lifecycle, 90-day interval (note: GCP IAM does not support concurrent keys)
  - Required Infisical App Connections: OpenRouter (with Provisioning API Key), GCP (with service account)
  - Required Infisical project/workspace settings
  
  **(c) Webhook Validation Schema:**
  - Full JSON payload example for `secrets.rotation-failed` event
  - Header format: `x-infisical-signature: t=<unix_ms>;<hex_hmac_sha256>`
  - Signed payload construction: `JSON.stringify(body)`
  - Timestamp replay window: 5 minutes
  - HMAC algorithm: SHA-256 via Web Crypto API
  
  **(d) Cloudflare AI Gateway REST API:**
  - PUT endpoint: `/accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}`
  - Auth: Bearer token with AI Gateway Edit scope
  - Request body schema with alias, default_config, provider_slug, secret fields
  - How aliases work: 'default' (no header needed) vs 'Lockinlabs' (cf-aig-byok-alias header)
  
  **(e) Environment Variables:**
  - INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET (Infisical Machine Identity auth)
  - INFISICAL_PROJECT_ID (Infisical project UUID)
  - INFISICAL_WEBHOOK_SECRET (HMAC-SHA256 key for webhook verification)
  - CF_ACCOUNT_ID, CF_AI_GATEWAY_ID, CF_API_TOKEN (Cloudflare AI Gateway access)
  - GCP_SERVICE_ACCOUNT_EMAIL (for GCP SA key rotation target)
  
  **(f) Disaster Recovery Rollback:**
  - Manual rollback procedure: use Infisical API to revert to previous credential set
  - Cloudflare AI Gateway manual secret override via dashboard
  - Rollback verification steps
  
  **(g) Security Considerations:**
  - Never log secret values
  - HMAC-SHA256 signature verification prevents unauthorized rotation
  - Timestamp replay protection (5-minute window)
  - Least-privilege Cloudflare API token scope (AI Gateway Edit only)
  
  Must NOT include any actual secret values, API keys, or tokens. All values shown as placeholders.
  Parallelization: Wave 1 | Blocked by: None | Blocks: 4
  References: README.md:1-186 (existing doc conventions), CORE-Modules/Inference-Tokenomics/main.py:1-25 (existing module docstring pattern)
  Acceptance criteria (agent-executed): `test -f INFERENCE_README.md && wc -l INFERENCE_README.md | awk '{print $1}'` returns line count >= 150; `grep -c "Disaster Recovery" INFERENCE_README.md` returns at least 1; `grep -c "Webhook" INFERENCE_README.md` returns at least 3; `grep -c "Lockinlabs" INFERENCE_README.md` returns at least 1
  QA scenarios: Happy: file exists, contains all 7 sections, no placeholder values leaked as real secrets. Failure: missing sections, hardcoded secret values. Evidence: `.omo/evidence/ulw/infisical-secret-rotation/task-3-infisical-secret-rotation.txt`
  Commit: Y | docs: add INFERENCE_README.md with rotation lifecycle, webhook schema, and rollback procedures

- [ ] 4. Stage, commit, and push all files to dev branch
  What to do / Must NOT do:
  Stage all new/modified files, create a conventional commit, and push to the `dev` branch of `AI-Staffing-Solution-Consultants-LLC/core-engineering-system`. 
  - Git add: CORE-Modules/Inference-Tokenomics/infisical_rotation_config.py, src/rotation_sync.js, INFERENCE_README.md
  - Commit message: `feat(security): automated Infisical secret rotation for Cloudflare AI Gateway`
  - Push to: dev branch only (never main)
  - Verify push succeeded by checking remote HEAD
  Must NOT: modify any existing files, push to main branch, include any secrets in the commit.
  Parallelization: Wave 2 | Blocked by: 1, 2, 3 | Blocks: Final verification
  References: README.md (branch constraints: dev only), AGENTS.md (branch: dev on Tizzle716/core-engineering-system)
  Acceptance criteria (agent-executed): `git log --oneline -1 dev` shows the new commit; `git diff --name-only HEAD~1 dev` shows exactly the 3 new files
  QA scenarios: Happy: commit succeeds, push succeeds, remote HEAD matches. Failure: push rejected (wrong branch), merge conflict. Evidence: `.omo/evidence/ulw/infisical-secret-rotation/task-4-infisical-secret-rotation.txt`
  Commit: Y (this IS the commit task) | feat(security): automated Infisical secret rotation for Cloudflare AI Gateway

## Final verification wave

> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.

- [ ] F1. Plan compliance audit
  Verify every file from the plan exists, has no stub/mock values, and matches the specified paths.
  Check: CORE-Modules/Inference-Tokenomics/infisical_rotation_config.py exists and exports OPENROUTER_ROTATION_CONFIG, GCP_SA_ROTATION_CONFIG, DUAL_PHASE_LIFECYCLE. src/rotation_sync.js exists and contains crypto.subtle.verify, INFISICAL_WEBHOOK_SECRET, provider_configs, Lockinlabs. INFERENCE_README.md exists with >=150 lines covering all 7 sections.

- [ ] F2. Code quality review
  Review rotation_sync.js for: no Node.js crypto imports, no hardcoded secrets, proper error handling, CORS headers, structured logging. Review infisical_rotation_config.py for: clean module structure, no runtime API calls (config only), proper docstrings. Review INFERENCE_README.md for: no leaked secret values, accurate API schemas matching research findings.

- [ ] F3. Real manual QA
  Execute verification commands: `python -c "from COREModules.InferenceTokenomics.infisical_rotation_config import OPENROUTER_ROTATION_CONFIG, GCP_SA_ROTATION_CONFIG, DUAL_PHASE_LIFECYCLE"` (module imports), `node -c src/rotation_sync.js` (syntax check), `grep -c "Disaster Recovery" INFERENCE_README.md` (doc completeness). Verify git log shows the commit on dev branch.

- [ ] F4. Scope fidelity
  Confirm no modifications to track-a/, track-b/, existing wrangler.toml, or router.js. Confirm no secret values committed. Confirm all files are at the correct paths. Confirm commit is on dev branch only.

## Commit strategy

Single atomic commit on `dev` branch:
```
feat(security): automated Infisical secret rotation for Cloudflare AI Gateway
```
Files: 3 new files, 0 modified files.

## Success criteria

1. All 3 deliverable files exist at their specified paths with no stub/mock values
2. rotation_sync.js passes syntax check and contains all required components (HMAC verification, AI Gateway PUT, both aliases)
3. infisical_rotation_config.py exports all 3 config objects with correct rotation intervals (30-day OpenRouter, 90-day GCP SA)
4. INFERENCE_README.md documents the full lifecycle including rollback procedures
5. All files committed and pushed to dev branch of AI-Staffing-Solution-Consultants-LLC/core-engineering-system
6. No existing files modified, no secrets committed
