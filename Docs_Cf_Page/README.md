# OpenViking Memory Mesh — Ingest Portal v2 (Cloudflare Worker)

Cloudflare Worker deployment for submitting documentation URLs and raw text into the OpenViking RAG ingestion queue.

## Migration from Pages to Worker

This project was migrated from Cloudflare Pages (v1) to Cloudflare Workers (v2) to support proper multi-environment deployments (dev/staging/prod).

**Why Workers instead of Pages?**
- Pages only supports 2 environments (Production + Preview)
- Workers support unlimited environments via `wrangler.toml`
- Each environment gets its own URL, secrets, and configuration
- Proper isolation for dev → staging → prod workflow

## Deployment

| Environment | Worker Name | URL |
|---|---|---|
| **Dev** | `openviking-ingest-dev` | `https://openviking-ingest-dev.automations-unstoppable.workers.dev` |
| **Staging** | `openviking-ingest-staging` | `https://openviking-ingest-staging.automations-unstoppable.workers.dev` |
| **Production** | `openviking-ingest-prod` | `https://openviking-ingest-prod.automations-unstoppable.workers.dev` |

| Property | Value |
|---|---|
| **Cloudflare Account** | `197a5689d9c0df2855f017dcbfc59f4a` |
| **Deployed** | 2026-07-23 |

## Files

```
Docs_Cf_Page/
├── src/
│   └── index.js          # Worker: serves HTML + API proxy + markdown conversion
├── wrangler.toml         # Multi-environment config (dev/staging/prod)
├── package.json          # Deploy scripts
└── README.md             # This file
```

## Deploy Commands

```bash
# Navigate to project
cd Docs_Cf_Page

# Deploy to dev (for testing)
npm run deploy:dev
# or: wrangler deploy --env dev

# Deploy to staging
npm run deploy:staging
# or: wrangler deploy --env staging

# Deploy to production
npm run deploy:prod
# or: wrangler deploy --env production

# View logs
npm run tail:dev
npm run tail:prod
```

## What's New in v2

- **Dual submission modes**: URL scrape OR raw text input
- **Text-to-Markdown conversion**: Plain text is auto-wrapped in structured .md with frontmatter
- **3 document categories**:
  - `Component Documentation` — system component docs, architecture, APIs
  - `OpenCode Transcripts` — session logs, agent conversations, tool outputs
  - `Planned Concepts` — design docs, RFCs, future architecture proposals
- **Removed confusing internal labels** (Barry_Lead_Gen, Track_A_Control, etc.)
- **Multi-environment support**: dev/staging/prod isolation

## API Reference

### POST /api/submit-scrape

**URL Mode Request:**
```json
{
  "target_url": "https://example.com/docs",
  "context_label": "Component_Documentation"
}
```

**Text Mode Request:**
```json
{
  "text_content": "Raw documentation text here...",
  "context_label": "Component_Documentation"
}
```

**Valid context_label values:**
- `Component_Documentation`
- `OpenCode_Transcripts`
- `Planned_Concepts`

**Success Response (200):**
```json
{
  "success": true,
  "message": "Text document accepted for ingestion. Context: Component_Documentation",
  "gateway_status": 200,
  "reference": "optional-gateway-id",
  "ingest_type": "text"
}
```

### Text-to-Markdown Conversion

When `text_content` is submitted, the Worker wraps it in structured Markdown:

```markdown
---
title: "Component Documentation"
category: Component_Documentation
ingested_at: 2026-07-23T16:00:00.000Z
source: openviking-web-ingest-portal
format: markdown
---

# Component Documentation

(escaped text content here)
```

### Outbound Headers

| Header | Value |
|---|---|
| `X-Agent-ID` | `openviking-web-ingest-portal` |
| `X-Task-Type` | `critical-engineering` |

## Integration Notes

### Browser-based Master Dashboard

The Sheryl Dashboard at `cloudflare/src/index.html` is the main operational console.
When integrating the ingest portal:

1. **Embed as iframe** or **route via path** in the existing dashboard
2. The ingest portal uses the same dark theme — visual consistency is intentional
3. The `POST /api/submit-scrape` endpoint is self-contained — no dashboard dependencies

### EIM 2-Way Streaming Video Chat

The existing WebRTC infrastructure (`cloudflare/workers/webrtc-signaling.js`) handles
video chat. The ingest portal is a separate concern:

- **Different Cloudflare project** (`openviking-ingest` Worker vs Sheryl Dashboard)
- **No shared state** — the ingest portal is stateless
- **Different domain** — `*.workers.dev` vs the dashboard domain

To unify under one domain later:
1. Add a custom domain to the Worker (via Cloudflare dashboard or API)
2. Or use Cloudflare Workers to route paths to different backends

### OpenViking RAG Pipeline

The Worker forwards to the AI Gateway, which proxies to OpenClaw.
The gateway endpoint uses the OpenClaw chat completions format. The RAG ingestion
happens downstream — this portal is just the submission surface.

Text documents are converted to Markdown before forwarding so the RAG pipeline
can parse them as structured documents rather than raw text blobs.

## Environment Variables

| Variable | Dev | Staging | Production |
|---|---|---|---|
| `APP_NAME` | `openviking-ingest-portal` | `openviking-ingest-portal` | `openviking-ingest-portal` |
| `ENVIRONMENT` | `dev` | `staging` | `production` |
| `LOG_LEVEL` | `debug` | `info` | `warn` |

## Secrets & Auth

| Secret | Where | Purpose |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` | Local env / CI | Wrangler deploy auth |
| AI Gateway auth | Gateway config (not in code) | Gateway→OpenClaw auth |

**Never commit API tokens.** Store in Infisical or use `wrangler secret put`.

## Custom Domain

To map a custom domain to a specific environment:

```bash
# Via Cloudflare dashboard:
# Workers & Pages → openviking-ingest-dev (or -staging / -prod) 
# → Triggers → Add Custom Domain
# Enter: docs-dev.ai-staffing-solutions-consultants.online
```

Or via API:
```bash
curl -X POST "https://api.cloudflare.com/client/v4/accounts/197a5689d9c0df2855f017dcbfc59f4a/workers/domains" \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"service":"openviking-ingest-prod","environment":"production","hostname":"docs.ai-staffing-solutions-consultants.online"}'
```

## Legacy Pages Deployment

The original Pages deployment at `openclaw-gateway.pages.dev` is deprecated.
The DNS CNAME for `docs.ai-staffing-solutions-consultants.online` should be updated
from `openclaw-gateway.pages.dev` to the new Worker custom domain once configured.
