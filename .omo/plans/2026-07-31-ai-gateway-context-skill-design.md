# Design: AI Gateway Auto-Context Skill

Date: 2026-07-31
Status: Approved (user decisions via Q&A + continuation directive)
Scope: Non-code repo change — skill files only. No touch to track-a/track-b, docker-compose, terraform, or policy.

## Problem

The Cloudflare AI Gateway documentation (official `llms-full.txt` export, 665 KB) should be automatically available as context whenever Prometheus (planner) or the librarian (reference search agent) handles an AI Gateway-related task — without manual fetching or web searches.

## Decisions (user-confirmed)

1. **Placement: both levels.**
   - User-level skill at `~/.agents/skills/ai-gateway/` — applies to ALL projects on this machine, sits alongside the existing `cloudflare` / `wrangler` skills.
   - Thin project wrapper at `.agents/skills/engineering-ai-gateway/` (skill name `agency-ai-gateway`, matching the repo's 74-skill `agency-*` convention) — versioned in this repo, discoverable via repo exploration.
2. **Content: distilled summary + full-docs reference.**
   - `SKILL.md` carries distilled essentials (~80 lines): what AI Gateway is, integration paths, auth, gateway management, features, providers, freshness note.
   - `references/ai-gateway-llms-full.txt` holds the complete 665 KB official export for on-demand deep dives. Matches the existing `cloudflare` skill's summary-then-references pattern.
3. **Discoverability: AGENTS.md pointer.** One line added to the repo map table so always-loaded context (and therefore Prometheus during planning) points at the skill.

## Architecture

### A. User-level skill — `~/.agents/skills/ai-gateway/`

- `SKILL.md`
  - Frontmatter: `name: ai-gateway` + trigger description covering: AI Gateway, `gateway.ai.cloudflare.com` endpoints, `/ai/run` and `/ai/v1/chat/completions` REST API, `cf-aig-gateway-id` header, Workers AI routing, model routing/fallback/rate-limiting through Cloudflare.
  - Body: distilled essentials (see Content below) + pointer to `references/ai-gateway-llms-full.txt`.
  - Freshness: snapshot date noted; instructs agents to re-fetch `https://developers.cloudflare.com/ai-gateway/llms-full.txt` before citing specific limits or pricing.
- `references/ai-gateway-llms-full.txt` — complete export, fetched via `curl`.

### B. Project wrapper — `.agents/skills/engineering-ai-gateway/SKILL.md`

- Frontmatter: `name: agency-ai-gateway` + the same trigger description.
- Body: short pointer — "Full AI Gateway context lives in the user-level `ai-gateway` skill. Load it for anything AI Gateway related." Also lists the distilled essentials inline (short form) so the wrapper is not empty if the user-level skill is absent.

### C. AGENTS.md pointer

- One line in the repo map table: `ai-gateway skill` row: "Cloudflare AI Gateway context: load `ai-gateway` skill (user-level) / `agency-ai-gateway` (project). 665KB official docs snapshot + distilled essentials."

## Content of the distilled SKILL.md body (user-level)

1. What AI Gateway is: proxy for AI API traffic providing observability (analytics, logging) + control (caching, rate limiting, retries, model fallback, A/B tests, guardrails, data loss prevention). One line of config to start.
2. Integration paths:
   - Provider-specific endpoint: `https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/{provider}` (keeps provider's API schema).
   - Cloudflare REST API: `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run` (all modalities), `/ai/v1/chat/completions` (OpenAI SDK compat), `/ai/v1/responses` (agentic).
   - Workers binding: `env.AI.run()`.
   - WebSockets API (realtime + non-realtime).
3. Auth: Account ID + Cloudflare API token with `AI Gateway - Read`, `AI Gateway - Edit`, `Workers AI - Read`. Upstream provider auth: unified billing, BYOK (stored keys), or request headers.
4. Gateway management: gateway IDs ≤ 64 chars; `default` gateway auto-created on first authenticated request for third-party models; **Workers AI requests always require the `cf-aig-gateway-id: default` header**.
5. Features: caching (per-request override), rate limiting, dynamic routing (retries/fallback/A-B), guardrails, DLP, logging, analytics (request count, tokens, cost).
6. Providers: OpenAI, Anthropic, Google AI Studio, Gemini, Workers AI, AWS Bedrock, Azure OpenAI, plus Baseten, Cartesia, Cerebras, Cohere, Deepgram, DeepSeek, ElevenLabs, Fal AI, xAI (Grok), Groq, HuggingFace, Ideogram, Mistral, OpenRouter, Parallel, Perplexity, Replicate, Vertex AI, Moonshot/Kimi, ByteDance, Alibaba, MiniMax, etc. (214 models total in the catalog).
7. Freshness note + reference pointer.

## Data flow — how context auto-applies

1. An agent (orchestrator, librarian, Prometheus) receives an AI Gateway-related task.
2. Available-skills check matches the trigger description → skill loads → distilled essentials enter context immediately.
3. Deep detail: agent reads `references/ai-gateway-llms-full.txt` on demand.
4. Librarian dispatch: orchestrator passes `load_skills=["ai-gateway"]` so the librarian gets the docs locally instead of web-searching.
5. Prometheus planning: always-loaded AGENTS.md points at the skill → planner loads it before writing the plan.

## Failure / freshness handling

- Reference file missing/corrupt → SKILL.md stands alone (distilled body is complete for most tasks).
- Docs drift → dated snapshot + re-fetch instruction when citing limits/pricing; the `cloudflare` skill's "prefer retrieval over pre-training" principle applies to the reference file.

## Verification

1. `skill(name="ai-gateway")` returns the distilled content.
2. `agency-ai-gateway` appears in available-skills listing for this project.
3. `references/ai-gateway-llms-full.txt` exists, ~665 KB, valid markdown.
4. AGENTS.md renders correctly; docker-compose/terraform/policy untouched (git diff limited to new skill files + AGENTS.md + spec).
5. Existing repo smoke checks unaffected (no runtime code changed): `docker compose config --quiet` and `terraform -chdir=terraform validate` still pass.
