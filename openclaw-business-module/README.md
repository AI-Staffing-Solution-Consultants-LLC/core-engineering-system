# OpenClaw Business Module — Maiden Mission

**Status: PLACEHOLDER** — documentation-only scaffolding. No implementation code exists.

## Purpose

The OpenClaw Business Module is the future operational shell for a multi-channel AI agent gateway (OpenClaw), hosting business-facing chatbot, automation, and workflow services. This module documents the *intent* to integrate OpenClaw into the Core Engineering System, pending architectural design (Prometheus's job) and implementation.

## Maiden Mission

The maiden mission is the **first end-to-end activation** of OpenClaw within the C-P-A (Context-Planning-Action) architecture. It will:

1. Accept a business command via the Telegram bridge (`/initiate-openclaw`)
2. Route through Sheryl (Memory & Context Agent) for context retrieval
3. Spawn a NEXUS-Sprint verification team via `agency-agents-factory`
4. Execute a sandboxed action plan through Track B (Actuator), constrained by `policy/tool-allowlist.txt`
5. Write every reasoning step and execution to the tamper-evident SHA-256 ledger

## Prerequisites

All five EIM (Executive Interface Module) milestones must be operational before the maiden mission can proceed. Per `CEM_Update.txt` Phase 5, these are:

| # | Milestone | Status |
|---|---|---|
| EIM-1 | OpenCode container configured as temporary EIM with `opencode-controller` skill | **TBD** |
| EIM-2 | OpenViking RAG matrix populated and queryable from the control loop | **TBD** |
| EIM-3 | Cloud Build pipeline (`cloudbuild.yaml`) triggers per-directory deployments conditionally | **TBD** |
| EIM-4 | Track A (Control Loop) ported to CEM-Core-Module, Track B ported to Self-Remediation-Module | **TBD** |
| EIM-5 | Cloudflare Edge Intelligence Grid (router.js + scraper.js) deployed and bound to KV, Queue, Browser Rendering, AI Gateway | **TBD** |

## Activation Trigger

```
/initiate-openclaw   (sent via Telegram → telegram-bridge:8088 → sheryl:8083)
```

## Existing Infrastructure Referenced

| Component | Path | Port | Role in Maiden Mission |
|---|---|---|---|
| **Sheryl** | `executive-quartet/sheryl/` | 8083 | Validates command, consults RAG + MemoryPlugin, builds action plan |
| **Telegram Bridge** | `telegram-bridge/` | 8088 | Receives `/initiate-openclaw` webhook, forwards to Sheryl |
| **Agency-Agents Factory** | `mcp/tools/agency-agents-factory.json` | — | Spawns NEXUS-Sprint verification team via daemon |
| **Agency-Agents Daemon** | `agency-agents/daemon/` | 8082 | Executes factory requests in isolated Docker Compose namespaces |
| **Track A (Control Loop)** | `track-a/` | 8080 | C-P-A reasoning: RAG search → hypothesis → action plan |
| **Track B (Actuator)** | `track-b/` | 8081 | Constitutional AI gate: allowlist validation → sandboxed execution |
| **Cloudflare Edge Grid** | `src/router.js` + `src/scraper.js` | Workers | Observability ingestion, remediation queue, browser scraping |
| **Constitutional Policies** | `policy/` | — | Rego rules (documentation of intent) + `tool-allowlist.txt` |
| **Ledger** | Per-track daily JSONL | — | SHA-256 chained, tamper-evident audit trail |

## What Lives Here (Future)

The OpenClaw configuration, channel definitions, business logic, and gateway routing will live here once architected. This directory is a **document-only placeholder** until Prometheus completes the architectural design.

## What Does NOT Live Here

- ❌ No Dockerfiles for OpenClaw services
- ❌ No implementation code (Python, JS, Go, etc.)
- ❌ No architecture diagrams or design documents (future Prometheus task)
- ❌ No wrangler.toml or Cloud Run deployment manifests

## Verification

```bash
# Confirm placeholder status — no implementation files present
ls openclaw-business-module/
# Expected: README.md, INITIATION.md  (only)
```
