# OpenViking Memory Mesh — Ingest Portal v2

Cloudflare Pages deployment for submitting documentation URLs and raw text into the OpenViking RAG ingestion queue.

## Deployment

| Property | Value |
|---|---|
| **Live URL** | `https://openclaw-gateway.pages.dev` |
| **Project Name** | `openclaw-gateway` |
| **Cloudflare Account** | `197a5689d9c0df2855f017dcbfc59f4a` |
| **Runtime Mode** | `_worker.js` (Advanced Mode) |
| **Deployed** | 2026-07-23 |

## What's New in v2

- **Dual submission modes**: URL scrape OR raw text input
- **Text-to-Markdown conversion**: Plain text is auto-wrapped in structured .md with frontmatter
- **3 document categories**:
  - `Component Documentation` — system component docs, architecture, APIs
  - `OpenCode Transcripts` — session logs, agent conversations, tool outputs
  - `Planned Concepts` — design docs, RFCs, future architecture proposals
- **Removed confusing internal labels** (Barry_Lead_Gen, Track_A_Control, etc.)

## Architecture

```
Browser Form --POST--> /api/submit-scrape --> _worker.js (edge)
                                                  |
                    +-----------------------------+
                    |
              URL mode: forward target_url to AI Gateway
              Text mode: convert to Markdown, then forward
                    |
                    v
      Cloudflare AI Gateway (openclaw-gateway)
      gateway.ai.cloudflare.com/v1/.../openclaw-gateway/compat/chat/completions
                    |
                    v
      OpenClaw RAG Ingestion Pipeline
```

### Why `_worker.js` instead of `functions/`?

Pages direct-upload API does not compile file-based `functions/` during deployment.
The `_worker.js` approach (Advanced Mode) uses a single pre-compiled worker with
manual routing. Same Workers runtime, same performance — just a different bundling path.

**Do NOT connect GitHub to this Pages project.** Git integration causes build failures
with `_worker.js`. Use direct-upload deployments only.

## Files

```
Docs_Cf_Page/
├── public/
│   ├── index.html      # Frontend form (responsive, dark theme, dual mode)
│   └── _worker.js      # Edge function: AI Gateway proxy + markdown conversion
└── README.md           # This file
```

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

**Error Response (4xx/5xx):**
```json
{
  "success": false,
  "error": "Gateway rejected request (HTTP 401): Unauthorized",
  "context_label": "Component_Documentation"
}
```

### Outbound Headers (injected by edge function)

| Header | Value |
|---|---|
| `X-Agent-ID` | `openviking-web-ingest-portal` |
| `X-Task-Type` | `critical-engineering` |

### Text-to-Markdown Conversion

When `text_content` is submitted, the edge function wraps it in structured Markdown:

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

### Gateway Endpoint

```
https://gateway.ai.cloudflare.com/v1/197a5689d9c0df2855f017dcbfc59f4a/openclaw-gateway/compat/chat/completions
```

This is a Cloudflare AI Gateway proxy. It routes to the OpenClaw chat completions
endpoint. Authentication is handled at the gateway layer — the edge function does
not inject gateway auth tokens.

## Redeployment

### Direct upload (preferred)

```bash
# Ensure wrangler is authenticated
wrangler whoami

# IMPORTANT: The repo root has a wrangler.toml for a different project.
# Temporarily rename it before Pages deploy.
mv wrangler.toml wrangler.toml.bak

# Deploy from the public/ directory
CLOUDFLARE_API_TOKEN=<your-token> CLOUDFLARE_ACCOUNT_ID=197a5689d9c0df2855f017dcbfc59f4a \
  wrangler pages deploy ./public/ --project-name=openclaw-gateway --branch=main

# Restore the root config
mv wrangler.toml.bak wrangler.toml
```

### Why no Git integration?

Pages Git builds fail with `_worker.js` (Advanced Mode) because the build system
cannot properly compile the single-worker format. Direct upload bypasses this issue.

The repo (`Docs_Cf_Page/`) serves as the source of truth. After making changes:
1. Commit/push to the repo
2. Run the direct-upload wrangler command above
3. The live site updates immediately

## Custom Domain

To map a custom domain:

**Dashboard → Workers & Pages → `openclaw-gateway` → Custom domains → Connect domain**

Enter: `docs.ai-staffing-solutions-consultants.online`

SSL will auto-provision. The domain must have a CNAME pointing to `openclaw-gateway.pages.dev`.

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

- **Different Cloudflare project** (`openclaw-gateway` vs Sheryl Dashboard)
- **No shared state** — the ingest portal is stateless
- **Different domain** — `openclaw-gateway.pages.dev` vs the dashboard domain

To unify under one domain later:
1. Add a custom domain to the `openclaw-gateway` Pages project
2. Or use Cloudflare Workers to route paths to different backends

### OpenViking RAG Pipeline

The edge function forwards to the AI Gateway, which proxies to OpenClaw.
The gateway endpoint uses the OpenClaw chat completions format. The RAG ingestion
happens downstream — this portal is just the submission surface.

Text documents are converted to Markdown before forwarding so the RAG pipeline
can parse them as structured documents rather than raw text blobs.

## Secrets & Auth

| Secret | Where | Purpose |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` | Local env / CI | Wrangler deploy auth |
| AI Gateway auth | Gateway config (not in this code) | Gateway→OpenClaw auth |

**Never commit API tokens.** Store in Infisical or Cloudflare dashboard secrets.
