---
name: agency-ai-gateway
description: Cloudflare AI Gateway context — proxy for AI API traffic with analytics, logging, caching, rate limiting, request retries, model fallback, A/B testing, guardrails, and data loss prevention. Load for any task involving AI Gateway, gateway.ai.cloudflare.com endpoints, the /ai/run or /ai/v1/chat/completions or /ai/v1/responses REST API, cf-aig-gateway-id headers, Workers AI routing, or routing/fallback/rate-limiting of LLM API traffic through Cloudflare.
---

# AI Gateway Context (Project Wrapper)

Full Cloudflare AI Gateway context lives in the **user-level `ai-gateway` skill** (`~/.agents/skills/ai-gateway/`) — load it for anything AI Gateway related. It contains the distilled essentials plus the complete official docs snapshot (`references/ai-gateway-llms-full.txt`, ~665KB).

This project-level wrapper exists so the skill is discoverable inside this repo (versioned, shows up in repo exploration).

Quick orientation (full detail in the user-level skill):

- **Endpoint**: `https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/{provider}` or the Cloudflare REST API `.../ai/run`, `.../ai/v1/chat/completions`, `.../ai/v1/responses`.
- **Auth**: Account ID + API token (`AI Gateway - Read/Edit`, `Workers AI - Read`); provider keys via unified billing, BYOK, or request headers.
- **Workers AI requests require the `cf-aig-gateway-id: default` header**; third-party models auto-create the `default` gateway.
- **Features**: caching, rate limiting, retries/fallback/A-B (dynamic routing), guardrails, DLP, logging, analytics.
- **Freshness**: snapshot dated 2026-07-31 — re-fetch `https://developers.cloudflare.com/ai-gateway/llms-full.txt` before citing specific limits/pricing.
