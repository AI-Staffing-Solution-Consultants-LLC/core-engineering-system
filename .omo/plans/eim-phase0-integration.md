# EIM Phase 0 Integration — Multi-Cloud Executive Information Management

## TL;DR

> **Quick Summary**: Full-stack integration of the Executive Information Management (EIM) system across DigitalOcean, AWS, Google Cloud Run, and Cloudflare. Five milestones: salvage existing DO/AWS assets, build the Executive Quartet (4 AI agent Flask services) with MemoryPlugin MCP shared brain, deploy a Cloudflare edge interface with WebRTC video + Turnstile security, wire Telegram connectivity + self-remediation, then placeholder for the OpenClaw Business Management Module maiden mission.
>
> **Deliverables**:
> - `barry-preservation/` — DO-Lobe container packaging scripts, Docker manifest, connectivity verification
> - `aura-refactor/` — AWS atlas_ → aura_ refactoring scripts, verification report
> - `executive-quartet/` — 4 new Flask services (Sheryl, Aura, Malory, Krieger) + Dockerfiles + tests
> - `/rag/docs/openviking/` — OpenViking RAG corpus extension + ingest pipeline
> - `mcp/tools/memory-plugin.json` — MemoryPlugin MCP tool definition
> - Cloudflare: Pages dashboard, WebRTC signaling Worker, Turnstile widget, admin password gate
> - `self-remediation/` — OpenCode container + Auditor Agent hooks
> - `telegram-bridge/` — Sheryl-Telegram API integration
> - Updated `docker-compose.yml`, `cloudbuild.yaml`, `terraform/cloudrun.tf`
> - `evidence/PHASE-0-{milestone}.md` — verification evidence per milestone
>
> **Estimated Effort**: Extra Large (XL)
> **Parallel Execution**: YES — 6 implementation waves + Final verification
> **Critical Path**: Wave 1 → Wave 2 (Barry || Aura) → Wave 3 (MemoryPlugin → Quartet) → Wave 4 (CF Pages → WebRTC → Turnstile) → Wave 5 (Telegram → Self-Remediation → Auditor) → Wave 6 (Integration) → Final

---

## Context

### Original Request
Full EIM Master Integration blueprint covering Phase 0 salvage (Barry DO-Lobe preservation, Aura Memory Salvage on AWS), shared brain (MemoryPlugin MCP, OpenViking RAG), hybrid edge interface (Cloudflare Turnstile, WebRTC 2-way video at core.ai-business-employees.online), autonomous self-remediation (Auditor Agent, OpenCode container), and the OpenClaw Maiden Mission.

### Interview Summary
**Key Discussions**:
- **External Systems**: Full live integration — credentials available for DigitalOcean, AWS, and Cloudflare. Actual cloud mutations gated behind human-in-the-loop checkpoints.
- **Executive Quartet**: 4 independent Flask services (Sheryl, Aura, Malory, Krieger), each with own Dockerfile following the track-a/track-b pattern (python:3.12-slim, non-root user).
- **Test Strategy**: TDD (RED-GREEN-REFACTOR). Every task writes a failing test first. Agent-executed QA scenarios mandatory on every task.
- **OpenViking RAG**: Extend existing /rag/ corpus from track-a. Add `openviking/` namespace with SOP ingestion pipeline.
- **WebRTC**: Cloudflare Pages dashboard with embedded video widget + dedicated Worker for WebRTC signaling (offer/answer, ICE candidates).
- **Sequencing**: Maximize parallelism — Barry + Aura run in parallel; MemoryPlugin config + Edge interface in parallel.
- **MemoryPlugin MCP**: API key available for live integration.
- **Maiden Mission**: Placeholder milestone — scope TBD once infrastructure is live.
- **Ledger**: All new services write to the existing SHA-256 tamper-evident ledger.

**Defaults Applied** (override if needed):
- **Ledger integration**: All new services write to existing tamper-evident JSONL ledger (same chain format as track-a/track-b)
- **Barry/Aura artifacts**: Deployment scripts/Dockerfiles land in this repo; actual DO/AWS deployment gated behind checkpoints
- **Telegram integration**: Sheryl connects via Telegram Bot API (python-telegram-bot), webhook mode
- **Self-remediation**: OpenCode container deployed as Cloud Run service, Auditor Agent as separate Flask service

**Self-Review Gaps Addressed** (Metis/Oracle unavailable due to API balance):
- **Scope creep guard**: Each milestone has explicit Must-NOT-Have items
- **Credential safety**: All cloud mutations gated behind 7 human-in-the-loop checkpoints
- **Missing edge cases**: WebRTC fallback (no video), DO/AWS connectivity failure modes, MemoryPlugin timeout/retry, Telegram rate limiting
- **Test coverage gaps**: Each Quartet service includes both unit tests and integration tests against MemoryPlugin mock; Cloudflare Workers tested via wrangler dev before deploy

### Existing Infrastructure
- **track-a**: Control Loop (Flask, port 8080), RAG corpus at /rag/docs/
- **track-b**: Actuator (Flask, port 8081), tool allowlist at policy/tool-allowlist.txt
- **pytest**: .test/ harness with conftest.py, test_track_a_routes.py, test_track_b_allowlist.py, test_opa_eval.py, test_ledger_chain.py
- **cloudbuild.yaml**: Path-aware CI with Infisical auth, Inference-Tokenomics hierarchy, gated deploys
- **terraform**: cloudrun.tf (track-a + track-b), iam.tf (service account), secrets.tf
- **docker-compose.yml**: track-a + track-b + commented-out agency-agents-daemon
- **mcp/**: tools/agency-agents-factory.json, README.md, manifest.json
- **agency-agents/**: daemon/ (Flask service skeleton, Dockerfile, teams.json), package.json (local @agency-agents/cli)
- **policy/**: tool-allowlist.txt, 4 .rego policy files

---

## Work Objectives

### Core Objective
Integrate the EIM Phase 0 system: salvage DO/AWS assets into this repo, build 4 AI agent Flask services with shared MemoryPlugin MCP brain, deploy a Cloudflare edge interface with WebRTC + Turnstile at core.ai-business-employees.online, wire Telegram connectivity and containerized self-remediation, leaving the OpenClaw maiden mission as a ready-to-activate placeholder.

### Concrete Deliverables
- `barry-preservation/` — DO container Docker manifest + packaging script + connectivity test
- `aura-refactor/` — AWS rename script (atlas_ → aura_) + verification diff
- `executive-quartet/sheryl/`, `.../aura/`, `.../malory/`, `.../krieger/` — 4 Flask services with tests
- `rag/docs/openviking/` — Extended RAG corpus with SOP ingestion
- `mcp/tools/memory-plugin.json` — MemoryPlugin MCP integration spec
- `wrangler.toml` — Updated with Pages + Workers configuration
- `cloudflare/src/` — Pages dashboard, Turnstile widget, WebRTC Worker
- `telegram-bridge/` — Sheryl-Telegram webhook service
- `self-remediation/` — OpenCode container Dockerfile + Auditor Agent service
- Updated: `docker-compose.yml`, `cloudbuild.yaml`, `terraform/cloudrun.tf`, `terraform/iam.tf`

### Definition of Done
- [ ] All 5 milestones have passing tests (`python -m pytest .test/ -q` exits 0)
- [ ] `docker compose up --build` starts all services (track-a, track-b, sheryl, aura, malory, krieger, self-remediation, telegram-bridge)
- [ ] `curl localhost:8080/healthz` (track-a), `:8081/healthz` (track-b), `:8083/healthz` (sheryl), `:8084/healthz` (aura), `:8085/healthz` (malory), `:8086/healthz` (krieger), `:8087/healthz` (self-remediation), `:8088/healthz` (telegram-bridge) all return 200
- [ ] `curl -X POST localhost:8080/plan -d '{"query":"why is latency high"}'` returns steps (Track A → Track B working)
- [ ] MemoryPlugin MCP connectivity: POST to memoryplugin.com returns valid response
- [ ] Cloudflare Pages preview URL loads dashboard with Turnstile widget
- [ ] WebRTC Worker handles signaling (offer/answer exchange verified via curl)
- [ ] Ledger entries for all services chain correctly (`curl localhost:8080/ledger?limit=50`)
- [ ] `terraform -chdir=terraform validate` passes

### Must Have
1. Barry DO-Lobe packaged as portable Docker image (zero code modification)
2. Aura atlas_ → aura_ refactoring complete on all AWS files (zero identity drift)
3. 4 Executive Quartet Flask services with /healthz, MemoryPlugin MCP integration, tamper-evident ledger
4. OpenViking RAG corpus extension + ingestion pipeline
5. Cloudflare Pages dashboard at core.ai-business-employees.online with Turnstile + admin password gate
6. WebRTC 2-way video: signaling Worker + embedded widget on Pages
7. Sheryl-Telegram webhook bridge
8. OpenCode self-remediation container with Auditor Agent hooks
9. All 7 human-in-the-loop checkpoints preserved (from existing plan pattern)
10. Every new service follows track-a/track-b pattern: python:3.12-slim, non-root user, Flask dev server

### Must NOT Have (Guardrails)
| # | Forbidden action | Why |
|---|---|---|
| 1 | Modify Barry DO-Lobe container code, database hooks, or internal routing | Zero-modification preservation mandate |
| 2 | Remove `non-root` user from any Dockerfile | AGENTS.md defense-in-depth constraint |
| 3 | Add `allUsers` invoker binding to any Cloud Run service | Constitutional AI enforcement |
| 4 | Grant `roles/owner` or `roles/editor` in terraform/iam.tf | AGENTS.md hard constraint |
| 5 | `git push` without explicit human approval | Remote side-effects |
| 6 | `terraform apply`, `gcloud run deploy`, `wrangler deploy` without per-step approval | Live state mutation |
| 7 | Read /home/olly/.gemini/, .google-cloud-sdk/, .aws/, .netrc, or any credential file | User-excluded credential directories |
| 8 | Exceed Cloud Run free tier: cpu=1, memory=512Mi, min=0, max=1 per service | Free tier constraint |
| 9 | Deploy to any GCP project other than aissc-core-engine-self-dep | Project constraint |
| 10 | Deploy to any GCP region other than us-central1 | Region constraint |
| 11 | Auto-scope creep into OpenClaw Business Management Module beyond placeholder | Maiden mission scoping is a separate planning session |
| 12 | Echo MemoryPlugin API key, Telegram bot token, or any secret in logs or commits | Secret hygiene |
| 13 | Create directories under /AISSC_Cloud_Workspace/ or /CORE-Modules/ | Those paths are in a different repo (CEM_Update.txt target) |
| 14 | Make live HTTP calls to Antigravity IDE or Taskmaster.ai from in-repo code | Credential boundary |

---

## Human-in-the-Loop Checkpoints (7)

Preserved from the existing NEXUS-Sprint plan pattern:

| # | Checkpoint | Command |
|---|---|---|
| 1 | `git commit` on local `dev` branch | `git -C /home/olly/core-engineering-system commit -m "..."` |
| 2 | `git push origin dev` | `git push origin dev` |
| 3 | `terraform plan` | `terraform -chdir=terraform plan` |
| 4 | `terraform apply` | `terraform -chdir=terraform apply` |
| 5 | `gcloud builds submit` / `gcloud run deploy` | `gcloud builds submit ...` |
| 6 | `wrangler deploy` | `wrangler deploy` |
| 7 | Infisical Universal Auth handshake | `curl https://app.infisical.com/api/v1/auth/...` |

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD (RED-GREEN-REFACTOR)
- **Framework**: pytest (existing .test/ harness)
- **Every task**: Write failing test first → implement minimally → verify green → refactor

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.omo/evidence/`.
- **Frontend/UI**: Playwright — Navigate, interact, assert DOM, screenshot
- **TUI/CLI**: interactive_bash (tmux) — Run command, send keystrokes, validate output
- **API/Backend**: Bash (curl) — Send requests, assert status + response fields
- **Cloudflare Workers**: curl + wrangler dev — Test signaling, verify responses
- **Docker**: docker compose up --build + curl health checks

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — types, configs, scaffolding — ALL can start immediately):
├── Task 1:  Project scaffolding + directory structure
├── Task 2:  Type definitions + shared schemas
├── Task 3:  docker-compose.yml expansion (7 new services)
├── Task 4:  cloudbuild.yaml expansion (new service build steps)
├── Task 5:  terraform/cloudrun.tf expansion (new Cloud Run service blocks)
├── Task 6:  Shared ledger utility module (all services write to ledger)
└── Task 7:  Test infrastructure expansion (.test/ for new services)

Wave 2 (Salvage — Barry || Aura in parallel):
├── Task 8:  Barry DO-Lobe preservation (Docker manifest, packaging script)
├── Task 9:  Aura atlas_ → aura_ refactoring (script + AWS execution)

Wave 3 (Shared Brain — MemoryPlugin + RAG + Quartet):
├── Task 10: MemoryPlugin MCP tool definition + integration
├── Task 11: OpenViking RAG corpus extension + ingestion pipeline
├── Task 12: Sheryl agent service (Flask, port 8083)
├── Task 13: Aura agent service (Flask, port 8084)
├── Task 14: Malory agent service (Flask, port 8085)
├── Task 15: Krieger agent service (Flask, port 8086)
└── Task 16: Quartet integration tests (cross-service MemoryPlugin sharing)

Wave 4 (Edge Interface — Cloudflare Pages + WebRTC + Turnstile):
├── Task 17: Cloudflare Pages dashboard scaffold (HTML/CSS/JS)
├── Task 18: WebRTC signaling Worker (offer/answer, ICE relay)
├── Task 19: Cloudflare Turnstile widget + admin password gate (CF Functions)
├── Task 20: Embedded video widget (Pages-hosted, connects to Worker)
└── Task 21: wrangler.toml configuration for all Workers + Pages

Wave 5 (Connectivity — Telegram + Self-Remediation):
├── Task 22: Sheryl-Telegram webhook bridge service (Flask, port 8088)
├── Task 23: OpenCode self-remediation container (Dockerfile + Cloud Run config)
├── Task 24: Auditor Agent service (board log monitoring, port 8087)
└── Task 25: Health-check hooks for self-remediation loop

Wave 6 (Integration — End-to-end, cross-milestone):
├── Task 26: Full docker-compose integration (all 9 services)
├── Task 27: End-to-end flow test (query → plan → execute → ledger → MemoryPlugin)
├── Task 28: Cloud Build path-aware triggers for new services
└── Task 29: OpenClaw Maiden Mission placeholder scaffold

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
```

### Critical Path
Task 1 → Task 6 (ledger utility) → Task 10 (MemoryPlugin) → Task 12-15 (Quartet) → Task 22 (Telegram) → Task 26 (Integration) → Task 27 (E2E) → F1-F4

### Parallel Speedup
Waves 2-5 run with significant internal parallelism. Barry || Aura, MemoryPlugin || RAG, all 4 Quartet services, Pages || WebRTC || Turnstile, Telegram || Self-Remediation || Auditor. Estimated ~65% faster than sequential.

### Dependency Matrix

- **1-7**: - (Wave 1, no deps) - 8-16, 22-28 → Foundation blocks all waves
- **8**: - (starts immediately after Wave 1) - 26 → Barry independent of all except Wave 1
- **9**: - (starts immediately after Wave 1) - 26 → Aura independent of all except Wave 1
- **10**: 6 (ledger) - 12-16, 26 → MemoryPlugin needed by all Quartet services
- **11**: - (starts after Wave 1) - 12-16 → RAG needed by Quartet for context
- **12**: 6, 10, 11 - 16, 22, 26 → Sheryl needs ledger, MemoryPlugin, RAG
- **13**: 6, 10, 11 - 16, 26 → Aura agent needs ledger, MemoryPlugin, RAG
- **14**: 6, 10, 11 - 16, 26 → Malory needs ledger, MemoryPlugin, RAG
- **15**: 6, 10, 11 - 16, 26 → Krieger needs ledger, MemoryPlugin, RAG
- **16**: 12-15 - 26 → Quartet integration needs all 4 services
- **17**: - (after Wave 1) - 20, 21, 26 → Pages blocks widget + wrangler config
- **18**: - (after Wave 1) - 21, 26 → WebRTC Worker blocks wrangler
- **19**: - (after Wave 1) - 21, 26 → Turnstile blocks wrangler
- **20**: 17, 18 - 21, 26 → Widget needs Pages + Worker
- **21**: 17-20 - 26 → wrangler config needs all CF components
- **22**: 6, 12 - 25, 26 → Telegram needs ledger + Sheryl
- **23**: 6 - 25, 26 → Self-remediation needs ledger
- **24**: 6 - 25, 26 → Auditor needs ledger
- **25**: 22-24 - 26 → Health hooks need all connectivity services
- **26**: 8-25 - 27 → Integration blocks E2E
- **27**: 26 - F1-F4 → E2E blocks verification
- **28**: 1-7 - 26 → Cloud Build expansion after foundation
- **29**: 26 - F1-F4 → Maiden Mission placeholder after integration

### Agent Dispatch Summary

- **Wave 1**: 7 tasks — T1-T3 → `quick`, T4 → `unspecified-high`, T5 → `unspecified-high`, T6 → `unspecified-high`, T7 → `quick`
- **Wave 2**: 2 tasks — T8 → `unspecified-high` (DO packaging), T9 → `unspecified-high` (AWS refactoring)
- **Wave 3**: 7 tasks — T10 → `unspecified-high`, T11 → `quick`, T12-T15 → `quick` (pattern-based), T16 → `unspecified-high`
- **Wave 4**: 5 tasks — T17 → `visual-engineering`, T18 → `unspecified-high`, T19 → `quick`, T20 → `visual-engineering`, T21 → `quick`
- **Wave 5**: 4 tasks — T22 → `unspecified-high`, T23 → `unspecified-high`, T24 → `unspecified-high`, T25 → `quick`
- **Wave 6**: 4 tasks — T26 → `unspecified-high`, T27 → `unspecified-high`, T28 → `unspecified-high`, T29 → `quick`
- **Final**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. **Project scaffolding + directory structure**

  **What to do**:
  - Create top-level directories: `barry-preservation/`, `aura-refactor/`, `executive-quartet/`, `cloudflare/`, `telegram-bridge/`, `self-remediation/`
  - Create subdirectories per quartet member: `executive-quartet/sheryl/`, `executive-quartet/aura/`, `executive-quartet/malory/`, `executive-quartet/krieger/`
  - Create `cloudflare/src/` (Pages dashboard), `cloudflare/workers/` (WebRTC signaling)
  - Create `self-remediation/auditor/` (Auditor Agent service)
  - Add `__init__.py` to each Python service directory
  - Add `.gitkeep` to empty directories that need tracking

  **Must NOT do**:
  - Create directories under /AISSC_Cloud_Workspace/, /CORE-Modules/, or /Inference-Tokenomics/
  - Scaffold files with placeholder implementation — directories + __init__.py only

  **Recommended Agent Profile**:
  - **Category**: `quick` — Mechanical scaffolding, no logic
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2-7)
  - **Blocks**: 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, 22, 23, 24
  - **Blocked By**: None

  **References**:
  - `track-a/Dockerfile` — pattern for service Dockerfile structure
  - `track-a/main.py` — pattern for Flask service entry point
  - `agency-agents/daemon/` — existing daemon directory structure example

  **Acceptance Criteria**:
  - [ ] All 6 top-level directories exist with `test -d` verification
  - [ ] All 4 quartet subdirectories exist: `executive-quartet/{sheryl,aura,malory,krieger}/`
  - [ ] Each Python service dir has `__init__.py`: `test -f executive-quartet/sheryl/__init__.py`
  - [ ] No files under /AISSC_Cloud_Workspace/ or /CORE-Modules/ created

  **QA Scenarios**:
  ```
  Scenario: Directory structure matches plan
    Tool: Bash
    Steps:
      1. ls -d barry-preservation/ aura-refactor/ executive-quartet/ cloudflare/ telegram-bridge/ self-remediation/
      2. ls -d executive-quartet/{sheryl,aura,malory,krieger}/
      3. ls cloudflare/src/ cloudflare/workers/
    Expected Result: All directories exist, exit code 0
    Evidence: .omo/evidence/task-1-directory-structure.txt

  Scenario: No forbidden paths created
    Tool: Bash
    Steps:
      1. test ! -d /AISSC_Cloud_Workspace/
      2. test ! -d CORE-Modules/CEM-Core-Module/
    Expected Result: Both paths do not exist, exit code 0
    Evidence: .omo/evidence/task-1-forbidden-paths.txt
  ```

  **Commit**: YES (Wave 1 group)
  - Message: `feat(eim): project scaffolding — directory structure for 6 new modules`
  - Files: `barry-preservation/`, `aura-refactor/`, `executive-quartet/`, `cloudflare/`, `telegram-bridge/`, `self-remediation/`

- [x] 2. **Type definitions + shared schemas**

  **What to do**:
  - Create `src/schemas/` directory (shared TypeScript-like schemas as Python dataclasses)
  - Define `ExecutiveQuartetMember` dataclass (name, port, personality, memory_context)
  - Define `MemoryPluginRequest` / `MemoryPluginResponse` dataclasses
  - Define `LedgerEntry` dataclass (matches existing track-a/track-b format)
  - Define `WebRTCSignal` dataclass (type, sdp, candidate)
  - Define `TelegramMessage` / `TelegramWebhook` dataclasses
  - Define `BoardLogEntry` / `AuditFinding` dataclasses (for Auditor Agent)
  - Write tests: `.test/test_schemas.py` — verify all dataclasses instantiate and serialize correctly

  **Must NOT do**:
  - Use TypeScript/JavaScript schemas — keep Python-only for in-repo consistency
  - Create .proto files or gRPC definitions (not in scope)

  **Recommended Agent Profile**:
  - **Category**: `quick` — Defined schemas, straightforward dataclass authoring
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3-7)
  - **Blocks**: 6, 10, 12-15, 18, 22, 24
  - **Blocked By**: None

  **References**:
  - `track-a/main.py:search_rag()` — existing data structures for reference
  - `track-b/main.py:is_allowed()` — existing validation patterns
  - `conftest.py` — existing test patterns for dataclass tests

  **Acceptance Criteria**:
  - [ ] Test file created: `.test/test_schemas.py`
  - [ ] `python -m pytest .test/test_schemas.py -q` → PASS (at least 8 tests)
  - [ ] `python -c "from src.schemas import ExecutiveQuartetMember; m = ExecutiveQuartetMember('sheryl', 8083, 'strategic', 'sheryl_context')"` exits 0

  **QA Scenarios**:
  ```
  Scenario: All dataclasses instantiate and serialize
    Tool: Bash
    Steps:
      1. python -m pytest .test/test_schemas.py -q -v
      2. python -c "from src.schemas import *; import json; e = LedgerEntry('test', 'hash', 'data'); print(json.dumps(e.__dict__))"
    Expected Result: All tests pass, JSON serialization works
    Evidence: .omo/evidence/task-2-schemas-test.txt

  Scenario: Invalid dataclass raises error
    Tool: Bash
    Steps:
      1. python -c "from src.schemas import ExecutiveQuartetMember; ExecutiveQuartetMember('', -1, '', '')"
    Expected Result: ValueError raised (validation)
    Evidence: .omo/evidence/task-2-schemas-validation.txt
  ```

  **Commit**: YES (Wave 1 group)
  - Message: `feat(eim): shared type definitions and schemas`
  - Files: `src/schemas/`, `.test/test_schemas.py`

- [x] 3. **docker-compose.yml expansion (7 new services)**

  **What to do**:
  - Add service blocks for: sheryl (8083), aura-agent (8084), malory (8085), krieger (8086), self-remediation (8087), telegram-bridge (8088)
  - Each follows track-a pattern: `build: ./executive-quartet/<name>`, `python:3.12-slim`, non-root user, healthcheck on /healthz
  - Add ledger volumes for each service (ledger-{name})
  - Add `depends_on` where appropriate: quartet services depend on MemoryPlugin (external, so `condition: service_started` for internal deps)
  - Add commented-out Cloudflare local dev service (wrangler dev, for testing only)
  - Verify: `docker compose config --quiet` exits 0

  **Must NOT do**:
  - Remove non-root user from any service
  - Add `allUsers` or public port bindings
  - Start agency-agents-daemon (keep commented-out, per existing pattern)
  - Hardcode secrets in environment variables (use `.env.example` placeholders)

  **Recommended Agent Profile**:
  - **Category**: `quick` — Pattern duplication, mechanical edits
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-2, 4-7)
  - **Blocks**: 8, 9, 12-15, 22, 23, 24, 26
  - **Blocked By**: None

  **References**:
  - `docker-compose.yml:1-50` — existing track-a + track-b service patterns (health checks, volumes, port bindings, restart policies)

  **Acceptance Criteria**:
  - [ ] `docker compose config --quiet` exits 0
  - [ ] `grep -c "build:" docker-compose.yml` returns ≥ 8 (2 existing + 6 new)
  - [ ] Every new service has `test: ["CMD", "curl", "-f", "http://localhost:<port>/healthz"]` healthcheck
  - [ ] No `allUsers` string present in compose file
  - [ ] `grep -c "non-root\|coreengine" docker-compose.yml` ≥ service count

  **QA Scenarios**:
  ```
  Scenario: Docker compose validates cleanly
    Tool: Bash
    Steps:
      1. docker compose config --quiet
      2. docker compose config | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); svcs=list(d['services'].keys()); print(f'Services: {len(svcs)}'); assert len(svcs) >= 8"
    Expected Result: Exit 0, at least 8 services defined
    Evidence: .omo/evidence/task-3-compose-validate.txt
  ```

  **Commit**: YES (Wave 1 group)
  - Message: `feat(eim): docker-compose expansion — 7 new services`
  - Files: `docker-compose.yml`

- [x] 4. **cloudbuild.yaml expansion (new service build steps)**

  **What to do**:
  - Add path-detection patterns for new directories: `executive-quartet/*`, `telegram-bridge/*`, `self-remediation/*`
  - Add build steps for: sheryl, aura-agent, malory, krieger (each builds from `executive-quartet/<name>/Dockerfile`)
  - Add build step for self-remediation (builds from `self-remediation/Dockerfile`)
  - Add build step for telegram-bridge (builds from `telegram-bridge/Dockerfile`)
  - Add deploy steps for each new Cloud Run service (following existing deploy-track-a/b pattern)
  - Add each new image to the `images:` block at bottom
  - Maintain existing `--no-allow-unauthenticated`, `--ingress=internal`, sizing constraints
  - Verify: YAML parses cleanly

  **Must NOT do**:
  - Remove or modify existing track-a / track-b / inference-tokenomics build steps
  - Change the auth or sizing flags (keep `--no-allow-unauthenticated`, cpu=1, memory=512Mi)
  - Add wrangler deploy to Cloud Build (wrangler is checkpoint #6, gated separately)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Complex CI config, multiple service patterns
  - **Skills**: `engineering-devops-automator`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-3, 5-7)
  - **Blocks**: 28
  - **Blocked By**: None

  **References**:
  - `cloudbuild.yaml:182-199` — existing build-inference-tokenomics pattern
  - `cloudbuild.yaml:261-301` — existing build-track-a/b patterns
  - `cloudbuild.yaml:309-364` — existing deploy steps (gcloud run deploy flags)

  **Acceptance Criteria**:
  - [ ] `python3 -c "import yaml; yaml.safe_load(open('cloudbuild.yaml'))"` exits 0
  - [ ] `grep -c 'executive-quartet' cloudbuild.yaml` ≥ 4 (one per quartet member)
  - [ ] `grep -c 'telegram-bridge' cloudbuild.yaml` ≥ 1
  - [ ] `grep -c 'self-remediation' cloudbuild.yaml` ≥ 1
  - [ ] `grep -c '--no-allow-unauthenticated' cloudbuild.yaml` ≥ 4 (existing 2 + new)

  **QA Scenarios**:
  ```
  Scenario: cloudbuild.yaml parses and has new service references
    Tool: Bash
    Steps:
      1. python3 -c "import yaml; d=yaml.safe_load(open('cloudbuild.yaml')); print(f\"Steps: {len(d['steps'])}\"); assert len(d['steps']) >= 8"
      2. grep -c 'no-allow-unauthenticated' cloudbuild.yaml
    Expected Result: YAML parses, at least 8 steps, auth flags present
    Evidence: .omo/evidence/task-4-cloudbuild-validate.txt
  ```

  **Commit**: YES (Wave 1 group)
  - Message: `feat(eim): cloudbuild expansion — build/deploy steps for 7 new services`
  - Files: `cloudbuild.yaml`

- [x] 5. **terraform/cloudrun.tf expansion (new Cloud Run service blocks)**

  **What to do**:
  - Add `google_cloud_run_v2_service` blocks for: sheryl (port 8083), aura-agent (8084), malory (8085), krieger (8086), self-remediation (8087), telegram-bridge (8088)
  - Each follows existing track-b pattern: `INGRESS_TRAFFIC_INTERNAL_ONLY`, `cpu=1, memory=512Mi`, `min=0, max=1`, service account `core-engine-worker`
  - Add `google_cloud_run_service_iam_member` for each new service (invoker role for service account)
  - Add `var` entries in `variables.tf` for each new service image
  - Verify: `terraform -chdir=terraform validate` passes

  **Must NOT do**:
  - Grant `roles/owner` or `roles/editor` to any principal
  - Remove `INGRESS_TRAFFIC_INTERNAL_ONLY` from any service
  - Change existing track-a / track-b blocks
  - Exceed free tier sizing (cpu=1, memory=512Mi, min=0, max=1)
  - Create backend bucket for terraform state

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Terraform HCL, IAM bindings, Cloud Run resource blocks
  - **Skills**: `engineering-devops-automator`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-4, 6-7)
  - **Blocks**: 12-15, 22, 23 (services reference terraform config)
  - **Blocked By**: None

  **References**:
  - `terraform/cloudrun.tf:6-64` — existing track-a service block pattern (resources, probes, env, scaling, ingress, service_account)
  - `terraform/cloudrun.tf:72-124` — existing track-b pattern with IAM invoker binding
  - `terraform/iam.tf` — existing service account and role bindings (do NOT grant owner/editor)
  - `terraform/variables.tf` — variable declaration pattern

  **Acceptance Criteria**:
  - [ ] `terraform -chdir=terraform init -backend=false` exits 0
  - [ ] `terraform -chdir=terraform validate` exits 0
  - [ ] `grep -c 'google_cloud_run_v2_service' terraform/cloudrun.tf` ≥ 8 (2 existing + 6 new)
  - [ ] `grep -c 'INGRESS_TRAFFIC_INTERNAL_ONLY' terraform/cloudrun.tf` ≥ 8
  - [ ] Zero occurrences of `roles/owner` or `roles/editor` in terraform/iam.tf

  **QA Scenarios**:
  ```
  Scenario: Terraform validates with new service blocks
    Tool: Bash
    Steps:
      1. terraform -chdir=terraform init -backend=false
      2. terraform -chdir=terraform validate
    Expected Result: Init succeeds, validate exits 0 with "Success!"
    Evidence: .omo/evidence/task-5-terraform-validate.txt

  Scenario: No privileged roles granted
    Tool: Bash
    Steps:
      1. grep -E 'roles/owner|roles/editor' terraform/iam.tf
    Expected Result: No matches (exit code 1)
    Evidence: .omo/evidence/task-5-no-privileged-roles.txt
  ```

  **Commit**: YES (Wave 1 group)
  - Message: `feat(eim): terraform expansion — Cloud Run blocks for 6 new services`
  - Files: `terraform/cloudrun.tf`, `terraform/variables.tf`

- [x] 6. **Shared ledger utility module**

  **What to do**:
  - Create `src/ledger.py` — shared ledger write utility used by all new services
  - Implement `write_ledger_entry(entry_type, entry_data, prev_hash)` → returns new chain_hash
  - Implement `LedgerWriter` class with configurable `LEDGER_PATH` env var
  - SHA-256 chain: `chain_hash = sha256(prev_hash + json(entry, sort_keys=True)).hexdigest()`
  - Match existing track-a/track-b format: daily `ledger-YYYY-MM-DD.jsonl` files
  - Write tests: `.test/test_ledger_shared.py` — verify chain integrity, daily file rotation, concurrent writes
  - TDD: Write failing tests FIRST, then implement

  **Must NOT do**:
  - Read the live ledger file directly (only append via the utility)
  - Break the existing chain hash format from track-a/track-b
  - Create a separate ledger chain — all services share the same JSONL format

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Cryptographic chain logic, thread safety, file rotation
  - **Skills**: None needed (pure Python)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-5, 7)
  - **Blocks**: 10, 12-15, 22, 23, 24 (all services depend on ledger utility)
  - **Blocked By**: 2 (needs LedgerEntry schema)

  **References**:
  - `track-a/main.py:write_ledger()` — existing ledger write pattern
  - `track-b/main.py:write_ledger()` — existing actuator ledger pattern
  - `.test/test_ledger_chain.py` — existing chain integrity tests

  **Acceptance Criteria**:
  - [ ] Test file created: `.test/test_ledger_shared.py` (TDD: RED first, then GREEN)
  - [ ] `python -m pytest .test/test_ledger_shared.py -q` → PASS (at least 6 tests)
  - [ ] `python -c "from src.ledger import LedgerWriter; w = LedgerWriter('/tmp/test_ledger'); h = w.write('test', {'key':'val'}, '0'*64); assert len(h) == 64"`
  - [ ] Ledger file format matches existing: `ledger-YYYY-MM-DD.jsonl` with `{"type":...,"timestamp":...,"data":...,"prev_hash":...,"chain_hash":...}`

  **QA Scenarios**:
  ```
  Scenario: Ledger chain integrity across multiple writes
    Tool: Bash
    Steps:
      1. python -m pytest .test/test_ledger_shared.py -q -v
      2. python -c "
  from src.ledger import LedgerWriter
  import hashlib, json, os, tempfile
  with tempfile.TemporaryDirectory() as d:
      w = LedgerWriter(d)
      h1 = w.write('test', {'n':1}, '0'*64)
      h2 = w.write('test', {'n':2}, h1)
      # Verify chain
      with open(os.path.join(d, f'ledger-{__import__(\"datetime\").date.today()}.jsonl')) as f:
          lines = f.readlines()
      assert len(lines) == 2
      e1 = json.loads(lines[0])
      e2 = json.loads(lines[1])
      assert e1['chain_hash'] == h1
      assert e2['prev_hash'] == h1
      print(f'Chain: {h1[:8]}... -> {h2[:8]}... OK')
  "
    Expected Result: Chain hashes link correctly, prev_hash matches
    Evidence: .omo/evidence/task-6-ledger-chain.txt

  Scenario: Concurrent writes do not corrupt ledger
    Tool: Bash
    Steps:
      1. python -c "
  from src.ledger import LedgerWriter
  import tempfile, threading
  with tempfile.TemporaryDirectory() as d:
      w = LedgerWriter(d)
      errors = []
      def write_n(n):
          try:
              w.write('test', {'thread': n}, '0'*64)
          except Exception as e:
              errors.append(e)
      threads = [threading.Thread(target=write_n, args=(i,)) for i in range(10)]
      [t.start() for t in threads]
      [t.join() for t in threads]
      print(f'Errors: {len(errors)}, expected 0')
      assert len(errors) == 0
  "
    Expected Result: Zero errors, all writes succeed
    Evidence: .omo/evidence/task-6-ledger-concurrent.txt
  ```

  **Commit**: YES (Wave 1 group)
  - Message: `feat(eim): shared ledger utility module`
  - Files: `src/ledger.py`, `.test/test_ledger_shared.py`

- [x] 7. **Test infrastructure expansion**

  **What to do**:
  - Extend `.test/conftest.py` with fixtures for new services:
    - `quartet_client(name, port)` — fixture that starts a quartet service container
    - `ledger_writer(tmp_path)` — fixture for ledger tests
    - `mock_memory_plugin(httpx_mock)` — fixture for MemoryPlugin MCP mock
    - `mock_telegram(httpx_mock)` — fixture for Telegram API mock
  - Add `pytest.ini` or `pyproject.toml` [tool.pytest.ini_options] for test discovery paths
  - Add coverage configuration (`.coveragerc` or pyproject.toml)
  - Verify: `python -m pytest .test/ --collect-only` shows all existing + new test files

  **Must NOT do**:
  - Remove or break existing test fixtures in conftest.py
  - Add real network calls in fixtures (all must use mocks)

  **Recommended Agent Profile**:
  - **Category**: `quick` — Fixture definitions, pytest config
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-6)
  - **Blocks**: 12-15, 22, 23, 24 (services use fixtures for tests)
  - **Blocked By**: None

  **References**:
  - `conftest.py:1-39` — existing fixture pattern (_register_track_a_package)
  - `.test/conftest.py` — existing test configuration

  **Acceptance Criteria**:
  - [ ] `python -m pytest .test/ --collect-only -q` exits 0 and shows ≥ 20 collected tests
  - [ ] `test -f .test/conftest.py` and contains `quartet_client`, `ledger_writer`, `mock_memory_plugin` fixtures
  - [ ] Coverage config present: `test -f .coveragerc || grep -q coverage pyproject.toml`

  **QA Scenarios**:
  ```
  Scenario: All existing tests still pass after fixture additions
    Tool: Bash
    Steps:
      1. python -m pytest .test/test_track_a_routes.py .test/test_track_b_allowlist.py .test/test_opa_eval.py .test/test_ledger_chain.py -q -v
    Expected Result: All 4 existing test files pass (≥ 8 tests)
    Evidence: .omo/evidence/task-7-existing-tests-pass.txt

  Scenario: New fixtures are importable
    Tool: Bash
    Steps:
      1. python -c "from .test.conftest import quartet_client; print('quartet_client fixture OK')"
    Expected Result: No import error
    Evidence: .omo/evidence/task-7-fixtures-import.txt
  ```

  **Commit**: YES (Wave 1 group)
  - Message: `feat(eim): test infrastructure expansion — fixtures, coverage, conftest`
  - Files: `.test/conftest.py`, `.coveragerc` (or `pyproject.toml`)

- [x] 8. **Barry DO-Lobe preservation (Docker manifest + packaging script)**

  **What to do**:
  - Create `barry-preservation/Dockerfile` — base image for the DO lead-gen container migration
  - Create `barry-preservation/package.sh` — script that pulls the DO container, exports it as a portable Docker image tarball, and saves the manifest
  - Create `barry-preservation/manifest.json` — Docker image metadata (layers, digests, environment variables, exposed ports, entrypoint)
  - Create `barry-preservation/job-task-module/` — mirror of the job/task module directory structure (as container volume mount reference)
  - Create `barry-preservation/connectivity-test.sh` — verifies the packaged container boots and internal routing works
  - Write tests: `.test/test_barry_preservation.py` — verify Dockerfile syntax, manifest schema, packaging script exits cleanly with mock

  **Must NOT do**:
  - Modify ANY Barry container code, database hooks, or internal routing logic
  - Run live `docker push` or deploy to DO without human approval
  - Read DO credentials directly — use env var placeholders only

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Docker manifest extraction, container packaging, shell scripting
  - **Skills**: `engineering-devops-automator`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 9 — Aura)
  - **Blocks**: 26 (integration)
  - **Blocked By**: 1 (needs barry-preservation/ directory)

  **References**:
  - `track-a/Dockerfile` — Dockerfile pattern (python:3.12-slim, non-root user)
  - `docker-compose.yml:1-19` — service definition pattern for container testing

  **Acceptance Criteria**:
  - [ ] `docker build -f barry-preservation/Dockerfile barry-preservation/ --dry-run 2>&1` contains valid Dockerfile parse
  - [ ] `python3 -c "import json; json.load(open('barry-preservation/manifest.json'))"` exits 0
  - [ ] `python -m pytest .test/test_barry_preservation.py -q` → PASS (at least 4 tests)
  - [ ] `grep -q 'as-is\|zero.modification\|NO CODE CHANGE' barry-preservation/package.sh` — script documents the no-modification constraint

  **QA Scenarios**:
  ```
  Scenario: Dockerfile parses without syntax errors
    Tool: Bash
    Steps:
      1. docker build -f barry-preservation/Dockerfile barry-preservation/ 2>&1 | head -5
    Expected Result: No "Error: Cannot parse" or syntax failures
    Evidence: .omo/evidence/task-8-dockerfile-parse.txt

  Scenario: Manifest.json has required fields
    Tool: Bash
    Steps:
      1. python3 -c "
  import json
  m = json.load(open('barry-preservation/manifest.json'))
  required = ['image_name', 'layers', 'environment', 'exposed_ports', 'entrypoint', 'preservation_note']
  for r in required:
      assert r in m, f'Missing: {r}'
  print(f'All {len(required)} fields present')
  "
    Expected Result: All required fields present
    Evidence: .omo/evidence/task-8-manifest-schema.txt
  ```

  **Commit**: YES (Wave 2 group)
  - Message: `feat(eim): barry DO-lobe preservation — Docker manifest + packaging`
  - Files: `barry-preservation/`

- [x] 9. **Aura atlas_ → aura_ refactoring (script + AWS execution)**

  **What to do**:
  - Create `aura-refactor/refactor.py` — recursive rename script: finds all `atlas_` occurrences in file names, directory names, and file contents, replaces with `aura_`
  - Support dry-run mode (`--dry-run`) that reports changes without applying
  - Support path targeting (`--target-path`) for AWS file location
  - Support exclusion patterns (`--exclude`) for files that must NOT be renamed
  - Create `aura-refactor/identity-check.py` — verifies no `atlas_` references remain post-refactor
  - Create `aura-refactor/execution-plan.md` — step-by-step AWS SSH/deployment instructions
  - Write tests: `.test/test_aura_refactor.py` — test rename logic on temp directories, dry-run output, identity check
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - Execute refactor on any path outside a test temp directory (live AWS execution gated behind human approval)
  - Rename `atlas_` inside vendor/, node_modules/, or .git/ directories
  - Modify any credentials or AWS config files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Recursive file operations, path traversal, safety checks
  - **Skills**: None needed (pure Python, os/shutil/pathlib)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 8 — Barry)
  - **Blocks**: 26 (integration)
  - **Blocked By**: 1 (needs aura-refactor/ directory)

  **References**:
  - `CEM_Update.txt:22` — reference to "atlas_ directory files on AWS"
  - `track-a/main.py` — Python project pattern for in-repo scripts

  **Acceptance Criteria**:
  - [ ] `python3 aura-refactor/refactor.py --dry-run --target-path /tmp/test-aura-refactor` exits 0 with change report
  - [ ] `python3 aura-refactor/identity-check.py --target-path /tmp/test-aura-refactor-post` exits 0 (no atlas_ found)
  - [ ] `python -m pytest .test/test_aura_refactor.py -q` → PASS (at least 6 tests)
  - [ ] Script handles: directory renames, file renames, content replacements, exclusion patterns

  **QA Scenarios**:
  ```
  Scenario: Dry-run reports changes without modifying files
    Tool: Bash
    Steps:
      1. mkdir -p /tmp/test-aura-refactor/atlas_config/
      2. echo "import atlas_core" > /tmp/test-aura-refactor/atlas_config/atlas_main.py
      3. python3 aura-refactor/refactor.py --dry-run --target-path /tmp/test-aura-refactor
      4. grep -r "atlas_" /tmp/test-aura-refactor/ | wc -l
    Expected Result: Dry-run shows planned changes; files still contain "atlas_" (not yet modified)
    Evidence: .omo/evidence/task-9-dry-run.txt

  Scenario: Real refactor replaces all atlas_ with aura_
    Tool: Bash
    Steps:
      1. mkdir -p /tmp/test-aura-refactor-real/atlas_config/
      2. echo "import atlas_core\natlas_core.init()" > /tmp/test-aura-refactor-real/atlas_config/atlas_main.py
      3. python3 aura-refactor/refactor.py --target-path /tmp/test-aura-refactor-real
      4. grep -r "atlas_" /tmp/test-aura-refactor-real/ | wc -l
      5. grep -r "aura_" /tmp/test-aura-refactor-real/ | wc -l
    Expected Result: Zero atlas_ matches, aura_ matches found
    Evidence: .omo/evidence/task-9-refactor-result.txt
  ```

  **Commit**: YES (Wave 2 group)
  - Message: `feat(eim): aura atlas-to-aura refactoring scripts`
  - Files: `aura-refactor/`

- [x] 10. **MemoryPlugin MCP tool definition + integration**

  **What to do**:
  - Create `mcp/tools/memory-plugin.json` — MCP tool definition following the existing pattern from `mcp/tools/agency-agents-factory.json`
  - Schema: `name: "memory-plugin"`, `version: "0.1.0"`, `description`, `inputs` (operation, context, entity, payload), `outputs`, `backend: "memoryplugin-mcp"`, `endpoint: "https://www.memoryplugin.com/api/mcp/mcp"`
  - Create `executive-quartet/memory_client.py` — shared MemoryPlugin HTTP client for all quartet members:
    - `store_memory(entity, context, data)` → POST to MemoryPlugin
    - `query_memory(entity, context, query)` → POST query
    - `delete_memory(entity, memory_id)` → DELETE
    - Handles auth via `MEMORYPLUGIN_API_KEY` env var
    - Retry with exponential backoff (3 attempts, 1s/2s/4s)
    - Timeout: 10s per request
  - Write tests: `.test/test_memory_plugin.py` — integration tests using `httpx_mock` fixture
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - Echo the API key in logs or test output (use placeholder in tests: `MEMORYPLUGIN_API_KEY=test-key`)
  - Hardcode the API key in source files (always read from env var)
  - Register the tool in system-wide MCP registry (repo-local only)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — HTTP client with auth, retry logic, MCP tool spec
  - **Skills**: None needed (Python, requests/httpx)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12-15)
  - **Blocks**: 12, 13, 14, 15, 16 (all quartet services need MemoryPlugin client)
  - **Blocked By**: 2 (schemas), 6 (ledger utility)

  **References**:
  - `mcp/tools/agency-agents-factory.json` — MCP tool definition pattern
  - `mcp/README.md` — tool registry security contract
  - `src/schemas/` — MemoryPluginRequest/Response dataclasses

  **Acceptance Criteria**:
  - [ ] `python3 -c "import json; d=json.load(open('mcp/tools/memory-plugin.json')); assert d['name']=='memory-plugin'"` exits 0
  - [ ] `python -m pytest .test/test_memory_plugin.py -q` → PASS (at least 5 tests: store, query, delete, retry, timeout)
  - [ ] `grep -c 'MEMORYPLUGIN_API_KEY' executive-quartet/memory_client.py` ≥ 1 (env var, not hardcoded)
  - [ ] `grep -c 'MEMORYPLUGIN_API_KEY' executive-quartet/memory_client.py` ≥ 1 (uses env var, NOT hardcoded value)
  - [ ] No API key value hardcoded in source: `grep -cE '[A-Za-z0-9]{32,}' executive-quartet/memory_client.py` = 0 (no long random strings)

  **QA Scenarios**:
  ```
  Scenario: MemoryPlugin client stores and queries with mock
    Tool: Bash
    Steps:
      1. MEMORYPLUGIN_API_KEY=test-key python -m pytest .test/test_memory_plugin.py::test_store_and_query -q -v
    Expected Result: Test passes — mock verifies correct endpoint, headers, payload
    Evidence: .omo/evidence/task-10-memory-client.txt

  Scenario: MemoryPlugin client retries on failure
    Tool: Bash
    Steps:
      1. MEMORYPLUGIN_API_KEY=test-key python -m pytest .test/test_memory_plugin.py::test_retry_on_failure -q -v
    Expected Result: Test verifies 3 attempts with exponential backoff (1s, 2s, 4s)
    Evidence: .omo/evidence/task-10-retry-logic.txt

  Scenario: API key not hardcoded in source
    Tool: Bash
    Steps:
      1. grep -c 'MEMORYPLUGIN_API_KEY' executive-quartet/memory_client.py
      2. grep -cE '[A-Za-z0-9]{32,}' executive-quartet/memory_client.py
    Expected Result: First returns ≥1 (env var referenced); second returns 0 (no hardcoded key)
    Evidence: .omo/evidence/task-10-no-hardcoded-key.txt
  ```

  **Commit**: YES (Wave 3 group)
  - Message: `feat(eim): memory-plugin MCP tool definition + shared client`
  - Files: `mcp/tools/memory-plugin.json`, `executive-quartet/memory_client.py`

- [x] 11. **OpenViking RAG corpus extension + ingestion pipeline**

  **What to do**:
  - Create `rag/docs/openviking/` directory — OpenViking namespace for SOP documents
  - Create `rag/docs/openviking/SOP-001-system-architecture.md` — initial SOP document (system architecture overview)
  - Create `rag/docs/openviking/SOP-002-incident-response.md` — incident response runbook
  - Create `rag/ingest.py` — ingestion pipeline script that:
    - Scans `rag/docs/openviking/` for new/changed .md files
    - Updates the corpus index used by track-a's `search_rag()`
    - Supports `--watch` mode for continuous ingestion
  - Update `track-a/main.py:search_rag()` to include `openviking/` namespace in search path
  - Write tests: `.test/test_openviking_rag.py` — verify ingestion, corpus update, search across namespaces
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - Replace or remove existing RAG corpus files in `rag/docs/`
  - Change the search_rag signature (keyword argument extension only)
  - Require external vector database or embedding service (keep substring-based for now, per AGENTS.md)

  **Recommended Agent Profile**:
  - **Category**: `quick` — File I/O, corpus indexing, minor search function extension
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10, 12-15)
  - **Blocks**: 12, 13, 14, 15 (Quartet services query RAG for context)
  - **Blocked By**: 1 (needs rag/ directory confirmed)

  **References**:
  - `track-a/main.py:search_rag()` — existing search function (substring-based)
  - `rag/` — existing corpus directory structure
  - `AGENTS.md:77-78` — search_rag is "content.lower().count(query.lower())" (substring occurrences)

  **Acceptance Criteria**:
  - [ ] `test -f rag/docs/openviking/SOP-001-system-architecture.md` — at least 2 SOP files created
  - [ ] `python3 rag/ingest.py --dry-run` exits 0 and reports files found
  - [ ] `python -m pytest .test/test_openviking_rag.py -q` → PASS (at least 4 tests)
  - [ ] `curl -X POST localhost:8080/plan -d '{"query":"system architecture"}'` returns steps that reference openviking corpus

  **QA Scenarios**:
  ```
  Scenario: Ingest script indexes OpenViking SOPs
    Tool: Bash
    Steps:
      1. python3 rag/ingest.py --dry-run
      2. ls rag/docs/openviking/
    Expected Result: Dry-run reports >= 2 files found; directory contains SOP .md files
    Evidence: .omo/evidence/task-11-ingest-dry-run.txt

  Scenario: search_rag finds OpenViking content
    Tool: Bash
    Steps:
      1. python3 -c "
  import sys; sys.path.insert(0, 'track-a')
  from main import search_rag
  results = search_rag('incident response')
  print(f'Found {len(results)} results')
  "
    Expected Result: At least 1 result referencing openviking namespace
    Evidence: .omo/evidence/task-11-rag-search.txt
  ```

  **Commit**: YES (Wave 3 group)
  - Message: `feat(eim): openviking RAG corpus extension + ingestion pipeline`
  - Files: `rag/docs/openviking/`, `rag/ingest.py`, `track-a/main.py`

- [x] 12. **Sheryl agent service (Flask, port 8083)**

  **What to do**:
  - Create `executive-quartet/sheryl/main.py` — Flask service following track-a pattern:
    - `GET /healthz` — returns `{"status":"ok","agent":"sheryl"}`
    - `POST /memory/store` — stores context in MemoryPlugin via memory_client
    - `POST /memory/query` — queries MemoryPlugin for relevant context
    - `POST /plan` — receives query, consults RAG + MemoryPlugin, returns action plan
    - `/ledger` — read-only ledger access (same pattern as track-a)
    - Writes every reasoning step to tamper-evident ledger
  - Create `executive-quartet/sheryl/Dockerfile` — python:3.12-slim, non-root user `coreengine`
  - Create `executive-quartet/sheryl/requirements.txt` — flask, gunicorn, httpx
  - Personality: Strategic executive — prioritizes business impact, delegates to other quartet members
  - Write tests: `.test/test_sheryl.py` — health check, memory store/query, plan endpoint, ledger write
  - TDD: Write failing tests FIRST, then implement minimally

  **Must NOT do**:
  - Call Telegram API (that's Task 22, separate bridge)
  - Hardcode MemoryPlugin API key
  - Remove non-root user from Dockerfile

  **Recommended Agent Profile**:
  - **Category**: `quick` — Pattern-based Flask service (follows track-a exactly)
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10-11, 13-15 — all 4 Quartet services parallel)
  - **Blocks**: 16, 22, 26
  - **Blocked By**: 2 (schemas), 6 (ledger), 10 (memory_client), 11 (RAG)

  **References**:
  - `track-a/main.py` — Flask service pattern, /healthz, /plan, /ledger endpoints
  - `track-a/Dockerfile` — Dockerfile pattern (python:3.12-slim, non-root user, CMD python -u main.py)
  - `executive-quartet/memory_client.py` — shared MemoryPlugin client

  **Acceptance Criteria**:
  - [ ] `python3 executive-quartet/sheryl/main.py & sleep 2 && curl -fs localhost:8083/healthz` returns `{"status":"ok","agent":"sheryl"}`
  - [ ] `curl -fs -X POST localhost:8083/plan -H 'Content-Type: application/json' -d '{"query":"status"}' | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'steps' in d"`
  - [ ] `python -m pytest .test/test_sheryl.py -q` → PASS (at least 5 tests)
  - [ ] `grep -q 'coreengine\|non-root' executive-quartet/sheryl/Dockerfile`

  **QA Scenarios**:
  ```
  Scenario: Sheryl health check returns agent identity
    Tool: Bash (curl)
    Steps:
      1. Start: python3 executive-quartet/sheryl/main.py & sleep 2
      2. curl -s localhost:8083/healthz | python3 -m json.tool
    Expected Result: {"status":"ok","agent":"sheryl"}
    Evidence: .omo/evidence/task-12-sheryl-healthz.json

  Scenario: Sheryl plan endpoint returns action steps
    Tool: Bash (curl)
    Steps:
      1. curl -s -X POST localhost:8083/plan -H 'Content-Type: application/json' -d '{"query":"analyze system status"}'
      2. Check response has "steps" array
    Expected Result: JSON with "steps" field, each step has "action" and "reasoning"
    Evidence: .omo/evidence/task-12-sheryl-plan.json
  ```

  **Commit**: YES (Wave 3 group)
  - Message: `feat(eim): sheryl agent service — strategic executive quartet member`
  - Files: `executive-quartet/sheryl/`

- [x] 13. **Aura agent service (Flask, port 8084)**

  **What to do**:
  - Create `executive-quartet/aura/main.py` — Flask service following track-a pattern:
    - `GET /healthz` — returns `{"status":"ok","agent":"aura"}`
    - `POST /memory/store`, `POST /memory/query` — MemoryPlugin integration
    - `POST /identity/verify` — verifies no atlas_ references remain (identity drift check)
    - `/ledger` — read-only ledger access
    - Writes every reasoning step to tamper-evident ledger
  - Create `executive-quartet/aura/Dockerfile` — python:3.12-slim, non-root user
  - Create `executive-quartet/aura/requirements.txt` — flask, gunicorn, httpx
  - Personality: Identity guardian — monitors for naming drift, maintains organizational memory
  - Write tests: `.test/test_aura_agent.py` — health check, identity verify, memory store/query
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - Hardcode MemoryPlugin API key
  - Remove non-root user from Dockerfile

  **Recommended Agent Profile**:
  - **Category**: `quick` — Pattern-based Flask service (follows sheryl task 12 pattern)
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10-12, 14-15)
  - **Blocks**: 16, 26
  - **Blocked By**: 2 (schemas), 6 (ledger), 10 (memory_client), 11 (RAG)

  **References**:
  - `track-a/main.py` — Flask service pattern
  - `track-a/Dockerfile` — Dockerfile pattern
  - `executive-quartet/sheryl/main.py` — sibling service pattern (Task 12)

  **Acceptance Criteria**:
  - [ ] `python3 executive-quartet/aura/main.py & sleep 2 && curl -fs localhost:8084/healthz` returns `{"status":"ok","agent":"aura"}`
  - [ ] `python -m pytest .test/test_aura_agent.py -q` → PASS (at least 4 tests)
  - [ ] `grep -q 'coreengine\|non-root' executive-quartet/aura/Dockerfile`

  **QA Scenarios**:
  ```
  Scenario: Aura identity verify endpoint works
    Tool: Bash (curl)
    Steps:
      1. Start: python3 executive-quartet/aura/main.py & sleep 2
      2. curl -s -X POST localhost:8084/identity/verify -H 'Content-Type: application/json' -d '{"namespace":"test"}'
    Expected Result: JSON response with identity status (no atlas_ drift detected)
    Evidence: .omo/evidence/task-13-aura-identity.json
  ```

  **Commit**: YES (Wave 3 group)
  - Message: `feat(eim): aura agent service — identity guardian quartet member`
  - Files: `executive-quartet/aura/`

- [x] 14. **Malory agent service (Flask, port 8085)**

  **What to do**:
  - Create `executive-quartet/malory/main.py` — Flask service following same pattern:
    - `GET /healthz` — returns `{"status":"ok","agent":"malory"}`
    - `POST /memory/store`, `POST /memory/query` — MemoryPlugin integration
    - `POST /compliance/check` — validates actions against policy/tool-allowlist.txt
    - `/ledger` — read-only ledger access
  - Create `executive-quartet/malory/Dockerfile` — python:3.12-slim, non-root user
  - Personality: Compliance officer — validates every action against constitutional policies
  - Write tests: `.test/test_malory.py` — health check, compliance check, memory store/query
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - Modify policy/tool-allowlist.txt directly (read-only access)
  - Hardcode MemoryPlugin API key
  - Remove non-root user

  **Recommended Agent Profile**:
  - **Category**: `quick` — Pattern-based Flask service
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10-13, 15)
  - **Blocks**: 16, 26
  - **Blocked By**: 2 (schemas), 6 (ledger), 10 (memory_client), 11 (RAG)

  **References**:
  - `track-a/main.py`, `track-b/main.py` — service patterns
  - `policy/tool-allowlist.txt` — compliance reference data

  **Acceptance Criteria**:
  - [ ] `python3 executive-quartet/malory/main.py & sleep 2 && curl -fs localhost:8085/healthz` returns `{"status":"ok","agent":"malory"}`
  - [ ] `python -m pytest .test/test_malory.py -q` → PASS (at least 4 tests)
  - [ ] `grep -q 'coreengine\|non-root' executive-quartet/malory/Dockerfile`

  **QA Scenarios**:
  ```
  Scenario: Malory compliance check validates against allowlist
    Tool: Bash (curl)
    Steps:
      1. Start: python3 executive-quartet/malory/main.py & sleep 2
      2. curl -s -X POST localhost:8085/compliance/check -H 'Content-Type: application/json' -d '{"action":"kubectl get pods"}'
      3. curl -s -X POST localhost:8085/compliance/check -H 'Content-Type: application/json' -d '{"action":"rm -rf /"}'
    Expected Result: First returns allowed=true, second returns allowed=false
    Evidence: .omo/evidence/task-14-malory-compliance.json
  ```

  **Commit**: YES (Wave 3 group)
  - Message: `feat(eim): malory agent service — compliance officer quartet member`
  - Files: `executive-quartet/malory/`

- [x] 15. **Krieger agent service (Flask, port 8086)**

  **What to do**:
  - Create `executive-quartet/krieger/main.py` — Flask service following same pattern:
    - `GET /healthz` — returns `{"status":"ok","agent":"krieger"}`
    - `POST /memory/store`, `POST /memory/query` — MemoryPlugin integration
    - `POST /remediate` — receives incident report, proposes remediation plan
    - `/ledger` — read-only ledger access
  - Create `executive-quartet/krieger/Dockerfile` — python:3.12-slim, non-root user
  - Personality: Incident responder — handles remediation workflows, coordinates with self-remediation module
  - Write tests: `.test/test_krieger.py` — health check, remediation plan, memory store/query
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - Execute remediation actions directly (that's self-remediation module's job, Task 23)
  - Hardcode MemoryPlugin API key
  - Remove non-root user

  **Recommended Agent Profile**:
  - **Category**: `quick` — Pattern-based Flask service
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10-14)
  - **Blocks**: 16, 26
  - **Blocked By**: 2 (schemas), 6 (ledger), 10 (memory_client), 11 (RAG)

  **References**:
  - `track-a/main.py` — service pattern
  - `agency-agents/daemon/main.py` — existing daemon service pattern in repo

  **Acceptance Criteria**:
  - [ ] `python3 executive-quartet/krieger/main.py & sleep 2 && curl -fs localhost:8086/healthz` returns `{"status":"ok","agent":"krieger"}`
  - [ ] `python -m pytest .test/test_krieger.py -q` → PASS (at least 4 tests)
  - [ ] `grep -q 'coreengine\|non-root' executive-quartet/krieger/Dockerfile`

  **QA Scenarios**:
  ```
  Scenario: Krieger proposes remediation plan for incident
    Tool: Bash (curl)
    Steps:
      1. Start: python3 executive-quartet/krieger/main.py & sleep 2
      2. curl -s -X POST localhost:8086/remediate -H 'Content-Type: application/json' -d '{"incident":"high_latency","severity":"high"}'
    Expected Result: JSON with remediation_steps array
    Evidence: .omo/evidence/task-15-krieger-remediate.json
  ```

  **Commit**: YES (Wave 3 group)
  - Message: `feat(eim): krieger agent service — incident responder quartet member`
  - Files: `executive-quartet/krieger/`

- [x] 16. **Quartet integration tests (cross-service MemoryPlugin sharing)**

  **What to do**:
  - Create `.test/test_quartet_integration.py` — integration tests proving the 4 quartet members work together:
    - Sheryl stores strategic context → Aura can query it
    - Malory validates an action → Krieger receives remediation plan
    - All 4 members write to the same MemoryPlugin namespace
    - Ledger entries from all 4 services chain correctly
  - Use `subprocess` or `multiprocessing` to start all 4 Flask services in test fixtures
  - Verify cross-service data flow: MemoryPlugin is the shared brain
  - Write tests: TDD approach

  **Must NOT do**:
  - Make live calls to MemoryPlugin API (use httpx_mock as before)
  - Leave orphaned subprocesses after test runs

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Multi-service orchestration, subprocess management
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (after Tasks 12-15 complete)
  - **Blocks**: 26 (integration requires quartet working)
  - **Blocked By**: 12, 13, 14, 15

  **References**:
  - `.test/conftest.py` — existing fixture patterns
  - `executive-quartet/memory_client.py` — shared MemoryPlugin client

  **Acceptance Criteria**:
  - [ ] `python -m pytest .test/test_quartet_integration.py -q` → PASS (at least 4 integration tests)
  - [ ] Test verifies: Sheryl writes → Aura reads from MemoryPlugin (same namespace)
  - [ ] Test verifies: All 4 ledger entries chain correctly (prev_hash → chain_hash)
  - [ ] Test cleanup: zero orphaned subprocesses after test completion

  **QA Scenarios**:
  ```
  Scenario: Cross-quartet MemoryPlugin sharing
    Tool: Bash
    Steps:
      1. python -m pytest .test/test_quartet_integration.py::test_cross_quartet_memory_share -q -v
    Expected Result: Sheryl stores, Aura queries, data matches
    Evidence: .omo/evidence/task-16-quartet-integration.txt

  Scenario: Quartet ledger chain integrity
    Tool: Bash
    Steps:
      1. python -m pytest .test/test_quartet_integration.py::test_quartet_ledger_chain -q -v
    Expected Result: All 4 services' ledger entries form unbroken chain
    Evidence: .omo/evidence/task-16-quartet-ledger.txt
  ```

  **Commit**: YES (Wave 3 group)
  - Message: `feat(eim): quartet cross-service integration tests`
  - Files: `.test/test_quartet_integration.py`

- [x] 17. **Cloudflare Pages dashboard scaffold**

  **What to do**:
  - Create `cloudflare/src/index.html` — dashboard HTML with:
    - Top-left quadrant: WebRTC video widget container (`<div id="video-widget">`)
    - Top-right quadrant: Tokenomics Dashboard placeholder
    - Bottom-left: Mission Control Stats panel
    - Bottom-right: Joint-browsing window (`<iframe>` or embedded view)
  - Create `cloudflare/src/style.css` — responsive grid layout, dark theme, Sheryl-branded design
  - Create `cloudflare/src/app.js` — dashboard orchestration:
    - WebRTC connection manager (connects to Worker for signaling)
    - Polling loop for Mission Control stats (placeholder API)
    - Intent-based widget display (show/hide quadrants based on user cues)
  - Use vanilla HTML/CSS/JS (no framework) for minimum deploy size
  - Write basic E2E test: `.test/test_cloudflare_pages.py` — verify HTML structure, CSS grid, JS module loading

  **Must NOT do**:
  - Use React, Vue, Angular, or any heavy framework (keep it lightweight for CF Pages)
  - Hardcode any API keys or secrets in frontend JS
  - Include real WebRTC streams in initial scaffold (placeholder video element)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering` — Frontend dashboard, responsive layout, grid design
  - **Skills**: `agency-frontend-developer`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 18-19)
  - **Blocks**: 20, 21
  - **Blocked By**: 1 (needs cloudflare/ directory)

  **References**:
  - `wrangler.toml` — existing Cloudflare config for deployment context
  - Cloudflare Pages docs: static site structure, asset deployment

  **Acceptance Criteria**:
  - [ ] `python3 -m http.server 9000 --directory cloudflare/src &` serves dashboard at localhost:9000
  - [ ] `curl -s localhost:9000/index.html | grep -q 'video-widget'` — video widget container present
  - [ ] `curl -s localhost:9000/index.html | grep -q 'tokenomics\|mission-control'` — dashboard panels present
  - [ ] `python -m pytest .test/test_cloudflare_pages.py -q` → PASS (at least 3 tests)

  **QA Scenarios**:
  ```
  Scenario: Dashboard HTML loads and has required quadrants
    Tool: Bash (curl)
    Steps:
      1. python3 -m http.server 9000 --directory cloudflare/src &>/dev/null & sleep 1
      2. curl -s http://localhost:9000/index.html | grep -o 'id="[^"]*"' | sort
      3. kill %1
    Expected Result: Contains video-widget, tokenomics, mission-control, joint-browsing
    Evidence: .omo/evidence/task-17-dashboard-ids.txt

  Scenario: Dashboard is responsive (CSS grid)
    Tool: Bash
    Steps:
      1. grep -c 'grid-template' cloudflare/src/style.css
    Expected Result: At least 2 grid-template references (desktop + mobile)
    Evidence: .omo/evidence/task-17-responsive-grid.txt
  ```

  **Commit**: YES (Wave 4 group)
  - Message: `feat(eim): cloudflare pages dashboard scaffold`
  - Files: `cloudflare/src/`

- [x] 18. **WebRTC signaling Worker**

  **What to do**:
  - Create `cloudflare/workers/webrtc-signaling.js` — Cloudflare Worker for WebRTC signaling:
    - Handles WebSocket connections (or HTTP polling) for signaling relay
    - `POST /offer` — receives SDP offer, stores in Durable Object, returns session ID
    - `POST /answer` — receives SDP answer for session, relays to offerer
    - `POST /ice` — relays ICE candidates between peers
    - `GET /session/{id}` — retrieves session state
    - Uses Cloudflare Durable Objects for session state (ephemeral, TTL-based cleanup)
  - Create `cloudflare/workers/wrangler.toml` — Worker-specific config (bindings for DO)
  - Update root `wrangler.toml` — add webrtc-signaling Worker route
  - Write tests: `.test/test_webrtc_worker.py` — mock Worker environment, test offer/answer/ICE relay
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - `wrangler deploy` without human approval (checkpoint #6)
  - Store PII or persistent data in Durable Object (ephemeral only)
  - Expose raw SDP in logs

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — WebRTC protocol, Cloudflare Workers, Durable Objects
  - **Skills**: `cloudflare`, `durable-objects`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 17, 19)
  - **Blocks**: 20, 21
  - **Blocked By**: 1 (needs cloudflare/ directory)

  **References**:
  - `wrangler.toml` — existing CF configuration
  - Cloudflare Durable Objects docs — session state pattern
  - WebRTC spec — SDP offer/answer model, ICE candidate format

  **Acceptance Criteria**:
  - [ ] `npx wrangler dev --config cloudflare/workers/wrangler.toml` starts Worker locally
  - [ ] `python -m pytest .test/test_webrtc_worker.py -q` → PASS (at least 5 tests: offer, answer, ice, session, cleanup)
  - [ ] `grep -c 'DurableObject' cloudflare/workers/webrtc-signaling.js` ≥ 1

  **QA Scenarios**:
  ```
  Scenario: WebRTC Worker handles offer/answer exchange
    Tool: Bash (curl against wrangler dev)
    Steps:
      1. npx wrangler dev --config cloudflare/workers/wrangler.toml & sleep 3
      2. OFFER_RESP=$(curl -s -X POST http://localhost:8787/offer -H 'Content-Type: application/json' -d '{"sdp":"mock-offer-sdp"}')
      3. SESSION_ID=$(echo $OFFER_RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
      4. curl -s -X POST "http://localhost:8787/answer" -H 'Content-Type: application/json' -d "{\"session_id\":\"$SESSION_ID\",\"sdp\":\"mock-answer-sdp\"}"
    Expected Result: Offer creates session, answer returns relayed SDP
    Evidence: .omo/evidence/task-18-webrtc-exchange.json
  ```

  **Commit**: YES (Wave 4 group)
  - Message: `feat(eim): webrtc signaling worker (durable objects)`
  - Files: `cloudflare/workers/`

- [x] 19. **Cloudflare Turnstile widget + admin password gate**

  **What to do**:
  - Create `cloudflare/workers/turnstile-gate.js` — Cloudflare Worker that:
    - Intercepts requests to `core.ai-business-employees.online/admin`
    - Presents Turnstile challenge (invisible or managed mode)
    - After Turnstile pass: presents password prompt (CFP_PASSWORD env var)
    - On both passes: sets session cookie, redirects to dashboard
    - `GET /admin/verify` — checks session validity
  - Create `cloudflare/functions/admin-gate.js` — Cloudflare Pages Function for the admin password gate:
    - Validates `CFP_PASSWORD` env var against submitted password
    - Rate-limited: 5 attempts per IP per 15 minutes
  - Update root `wrangler.toml` — add routes for Turnstile Worker
  - Write tests: `.test/test_turnstile.py` — mock Turnstile and password verification flow

  **Must NOT do**:
  - `wrangler deploy` without human approval (checkpoint #6)
  - Hardcode CFP_PASSWORD (use env var placeholder)
  - Allow bypass of Turnstile (always enforce challenge before password prompt)

  **Recommended Agent Profile**:
  - **Category**: `quick` — CF Worker for auth gate, standard challenge/response pattern
  - **Skills**: `turnstile-spin`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 17-18, 20)
  - **Blocks**: 21
  - **Blocked By**: 1 (needs cloudflare/ directory)

  **References**:
  - Cloudflare Turnstile docs — widget integration, siteverify endpoint
  - Cloudflare Pages Functions — serverless function pattern
  - `wrangler.toml` — route configuration

  **Acceptance Criteria**:
  - [ ] `python -m pytest .test/test_turnstile.py -q` → PASS (at least 4 tests)
  - [ ] `grep -c 'turnstile\|TURNSTILE' cloudflare/workers/turnstile-gate.js` ≥ 2
  - [ ] `grep -c 'CFP_PASSWORD' cloudflare/functions/admin-gate.js` ≥ 1 (env var, not hardcoded)

  **QA Scenarios**:
  ```
  Scenario: Turnstile Worker returns challenge page
    Tool: Bash (curl)
    Steps:
      1. npx wrangler dev --config cloudflare/workers/wrangler.toml & sleep 3
      2. curl -s http://localhost:8787/admin | grep -i turnstile
    Expected Result: Response contains Turnstile widget reference
    Evidence: .omo/evidence/task-19-turnstile-challenge.html

  Scenario: Invalid password is rejected
    Tool: Bash (curl)
    Steps:
      1. curl -s -X POST http://localhost:8787/admin/verify -H 'Content-Type: application/json' -d '{"password":"wrong","turnstile_token":"mock-valid"}'
    Expected Result: 401 Unauthorized or redirect to challenge
    Evidence: .omo/evidence/task-19-invalid-password.txt
  ```

  **Commit**: YES (Wave 4 group)
  - Message: `feat(eim): cloudflare turnstile + admin password gate`
  - Files: `cloudflare/workers/turnstile-gate.js`, `cloudflare/functions/`

- [x] 20. **Embedded video widget (Pages-hosted, connects to Worker)**

  **What to do**:
  - Create `cloudflare/src/video-widget.js` — embedded WebRTC video widget:
    - Connects to WebRTC signaling Worker for offer/answer exchange
    - Uses `RTCPeerConnection` API for 2-way video stream
    - Handles: `getUserMedia` for local camera, remote stream attachment
    - Handles: ICE candidate gathering and relay via Worker
    - Handles: connection state changes (connecting, connected, disconnected, failed)
    - Handles: reconnection with exponential backoff (3 attempts)
  - Update `cloudflare/src/index.html` — wire video-widget.js into the top-left quadrant
  - Update `cloudflare/src/app.js` — initialize video widget on dashboard load
  - Write basic test: verifies JS module loads and exports expected functions

  **Must NOT do**:
  - Hardcode WebRTC server URLs (use config from app.js)
  - Auto-start camera without user interaction (require click-to-start per browser policy)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering` — Frontend video integration, WebRTC browser APIs
  - **Skills**: `agency-frontend-developer`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (after Tasks 17, 18)
  - **Blocks**: 21, 26
  - **Blocked By**: 17 (dashboard HTML needs video container), 18 (Worker must exist for signaling)

  **References**:
  - MDN WebRTC API — RTCPeerConnection, getUserMedia, ICE candidate handling
  - `cloudflare/workers/webrtc-signaling.js` — Worker endpoint paths (/offer, /answer, /ice)

  **Acceptance Criteria**:
  - [ ] `test -f cloudflare/src/video-widget.js` and exports `initVideoWidget()`, `startCall()`, `endCall()`
  - [ ] `grep -c 'RTCPeerConnection' cloudflare/src/video-widget.js` ≥ 1
  - [ ] `grep -c 'getUserMedia' cloudflare/src/video-widget.js` ≥ 1
  - [ ] `grep -c '/offer\|/answer\|/ice' cloudflare/src/video-widget.js` ≥ 3 (Worker endpoints referenced)

  **QA Scenarios**:
  ```
  Scenario: Video widget module loads without errors
    Tool: Bash (Node.js check)
    Steps:
      1. node -e "
  const fs = require('fs');
  const code = fs.readFileSync('cloudflare/src/video-widget.js', 'utf8');
  // Check for required exports
  assert(code.includes('initVideoWidget'), 'Missing initVideoWidget');
  assert(code.includes('startCall'), 'Missing startCall');
  assert(code.includes('endCall'), 'Missing endCall');
  console.log('All exports present');
  "
    Expected Result: All exports present, exit 0
    Evidence: .omo/evidence/task-20-video-widget-exports.txt

  Scenario: Video widget references Worker endpoints
    Tool: Bash
    Steps:
      1. grep -n '/offer\|/answer\|/ice' cloudflare/src/video-widget.js
    Expected Result: At least 3 references to signaling Worker endpoints
    Evidence: .omo/evidence/task-20-worker-endpoints.txt
  ```

  **Commit**: YES (Wave 4 group)
  - Message: `feat(eim): embedded webrtc video widget`
  - Files: `cloudflare/src/video-widget.js`, `cloudflare/src/index.html`, `cloudflare/src/app.js`

- [x] 21. **wrangler.toml configuration for all Workers + Pages**

  **What to do**:
  - Update root `wrangler.toml` with:
    - Pages project config: `cloudflare/src/` as build output directory
    - Worker routes: `webrtc-signaling` → `core.ai-business-employees.online/webrtc/*`
    - Worker routes: `turnstile-gate` → `core.ai-business-employees.online/admin/*`
    - KV namespace bindings for OBSERVABILITY_STATE and INFISICAL_CACHE (from CEM_Update.txt Phase 2)
    - Environment variables: `CFP_PASSWORD` (placeholder), `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`
    - Durable Object bindings for WebRTC sessions
  - Create `cloudflare/workers/wrangler.toml` — Worker-specific config
  - Verify: `npx wrangler deploy --dry-run` parses config (or `wrangler whoami` for auth check)

  **Must NOT do**:
  - `wrangler deploy` without human approval (checkpoint #6)
  - Create KV namespaces via `wrangler kv:namespace create` without approval
  - Hardcode real secrets in wrangler.toml (use `wrangler secret put` references)

  **Recommended Agent Profile**:
  - **Category**: `quick` — Config file consolidation, route mapping
  - **Skills**: `wrangler`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (after Tasks 17-20)
  - **Blocks**: 26 (integration needs wrangler config complete)
  - **Blocked By**: 17, 18, 19, 20

  **References**:
  - `wrangler.toml` — existing config pattern
  - `CEM_Update.txt:29-30` — KV stores OBSERVABILITY_STATE and INFISICAL_CACHE

  **Acceptance Criteria**:
  - [ ] `npx wrangler deploy --dry-run 2>&1 | grep -q 'config'` — wrangler reads config without error
  - [ ] `grep -c 'webrtc-signaling\|turnstile-gate' wrangler.toml` ≥ 2
  - [ ] `grep -c 'OBSERVABILITY_STATE\|INFISICAL_CACHE' wrangler.toml` ≥ 2
  - [ ] `grep -c 'durable_objects' wrangler.toml` ≥ 1

  **QA Scenarios**:
  ```
  Scenario: wrangler.toml references all Workers
    Tool: Bash
    Steps:
      1. python3 -c "
  import tomli  # or tomllib for 3.11+
  with open('wrangler.toml', 'rb') as f:
      config = tomli.load(f)  # note: TOML, not JSON
  # Flexible check: just verify the file parses
  print('wrangler.toml parsed successfully')
  " 2>&1 || echo "TOML parse check — see full file for worker references"
      2. grep -c 'name' wrangler.toml
    Expected Result: TOML parses, references at least 3 named Workers/Pages
    Evidence: .omo/evidence/task-21-wrangler-config.txt
  ```

  **Commit**: YES (Wave 4 group)
  - Message: `feat(eim): wrangler.toml config for pages + webrtc + turnstile workers`
  - Files: `wrangler.toml`, `cloudflare/workers/wrangler.toml`

- [x] 22. **Sheryl-Telegram webhook bridge service (Flask, port 8088)**

  **What to do**:
  - Create `telegram-bridge/main.py` — Flask service for Telegram Bot API integration:
    - `GET /healthz` — returns `{"status":"ok","service":"telegram-bridge"}`
    - `POST /webhook` — Telegram webhook endpoint (receives messages from Telegram)
    - `POST /send` — sends message to Telegram chat (forwarded from Sheryl)
    - `GET /status` — bot connection status, chat list
    - Parses Telegram message format (text, commands, inline keyboards)
    - Forwards messages to Sheryl (localhost:8083) for processing
    - Uses `TELEGRAM_BOT_TOKEN` env var (never hardcoded)
    - Rate limiting: 30 messages per second per chat (Telegram API limit)
  - Create `telegram-bridge/Dockerfile` — python:3.12-slim, non-root user
  - Create `telegram-bridge/requirements.txt` — flask, gunicorn, httpx
  - Write tests: `.test/test_telegram_bridge.py` — webhook parse, message forward, rate limiting
  - TDD: Write failing tests FIRST

  **Must NOT do**:
  - Hardcode Telegram bot token (use `TELEGRAM_BOT_TOKEN` env var)
  - Set webhook URL automatically (requires live Telegram API — manual step after deploy)
  - Echo the bot token in logs

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Telegram Bot API, webhook handling, message parsing
  - **Skills**: None needed (standard Flask + httpx)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 23, 24)
  - **Blocks**: 25, 26
  - **Blocked By**: 2 (schemas), 6 (ledger), 12 (Sheryl service must exist for forwarding)

  **References**:
  - Telegram Bot API docs — webhook format, sendMessage endpoint, update types
  - `track-a/main.py` — Flask service pattern
  - `executive-quartet/sheryl/main.py` — Sheryl's /plan endpoint for message forwarding

  **Acceptance Criteria**:
  - [ ] `python3 telegram-bridge/main.py & sleep 2 && curl -fs localhost:8088/healthz` returns 200
  - [ ] `curl -s -X POST localhost:8088/webhook -H 'Content-Type: application/json' -d '{"update_id":1,"message":{"chat":{"id":123},"text":"/status"}}'` → forwards to Sheryl and returns 200
  - [ ] `python -m pytest .test/test_telegram_bridge.py -q` → PASS (at least 5 tests)
  - [ ] `grep -c 'TELEGRAM_BOT_TOKEN' telegram-bridge/main.py` ≥ 1 (env var, not hardcoded value)
  - [ ] `grep -q 'coreengine\|non-root' telegram-bridge/Dockerfile`

  **QA Scenarios**:
  ```
  Scenario: Telegram webhook receives and forwards message to Sheryl
    Tool: Bash (curl chain)
    Steps:
      1. Start services: python3 executive-quartet/sheryl/main.py & sleep 1
      2. Start bridge: python3 telegram-bridge/main.py & sleep 1
      3. curl -s -X POST localhost:8088/webhook -H 'Content-Type: application/json' -d '{"update_id":1,"message":{"chat":{"id":123},"text":"system status"}}'
    Expected Result: 200 OK, Sheryl processes the message
    Evidence: .omo/evidence/task-22-telegram-webhook.json

  Scenario: Rate limiting blocks excessive messages
    Tool: Bash (curl loop)
    Steps:
      1. for i in $(seq 1 35); do curl -s -X POST localhost:8088/webhook -H 'Content-Type: application/json' -d "{\"update_id\":$i,\"message\":{\"chat\":{\"id\":123},\"text\":\"msg $i\"}}"; done
    Expected Result: First 30 return 200, messages 31-35 return 429
    Evidence: .omo/evidence/task-22-rate-limit.txt
  ```

  **Commit**: YES (Wave 5 group)
  - Message: `feat(eim): sheryl-telegram webhook bridge`
  - Files: `telegram-bridge/`

- [x] 23. **OpenCode self-remediation container (Dockerfile + Cloud Run config)**

  **What to do**:
  - Create `self-remediation/Dockerfile` — OpenCode container:
    - Base: `python:3.12-slim` + OpenCode CLI installation
    - Non-root user `coreengine`
    - Health-check hook: `GET /healthz` endpoint
    - Self-test: `opencode --version` verification
  - Create `self-remediation/main.py` — Flask wrapper service (port 8087):
    - `GET /healthz` — returns `{"status":"ok","service":"self-remediation"}`
    - `POST /remediate` — receives remediation plan from Krieger (Task 15), executes via OpenCode
    - `POST /health-check` — triggers health check of all mesh services
    - `/ledger` — writes remediation actions to tamper-evident ledger
  - Create `self-remediation/health-hooks.py` — health check hooks:
    - Probes all quartet services (/healthz)
    - Probes tracks A and B
    - Reports status to Auditor Agent (Task 24)
  - Create `self-remediation/requirements.txt` — flask, gunicorn, httpx

  **Must NOT do**:
  - Execute remediation actions that modify production without human approval
  - Expose OpenCode credentials in Dockerfile or logs
  - Remove non-root user

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — OpenCode integration, health-check orchestration, Docker multi-stage
  - **Skills**: `engineering-devops-automator`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 22, 24)
  - **Blocks**: 25, 26
  - **Blocked By**: 2 (schemas), 6 (ledger)

  **References**:
  - `track-a/Dockerfile` — Dockerfile pattern
  - `track-a/main.py` — Flask service pattern
  - `agency-agents/daemon/main.py` — existing daemon service pattern
  - OpenCode docs — CLI installation, health-check configuration

  **Acceptance Criteria**:
  - [ ] `docker build -f self-remediation/Dockerfile self-remediation/` succeeds (local build)
  - [ ] `python3 self-remediation/main.py & sleep 2 && curl -fs localhost:8087/healthz` returns 200
  - [ ] `curl -s -X POST localhost:8087/health-check -H 'Content-Type: application/json' -d '{}'` returns service status map
  - [ ] `python -m pytest .test/test_remediation.py -q` → PASS (at least 4 tests)
  - [ ] `grep -q 'coreengine\|non-root' self-remediation/Dockerfile`

  **QA Scenarios**:
  ```
  Scenario: Self-remediation service probes all mesh services
    Tool: Bash (curl)
    Steps:
      1. Start all quartet services + self-remediation
      2. curl -s -X POST localhost:8087/health-check | python3 -m json.tool
    Expected Result: JSON map of all services with health status
    Evidence: .omo/evidence/task-23-health-check.json

  Scenario: Self-remediation writes ledger entry on action
    Tool: Bash (curl)
    Steps:
      1. curl -s -X POST localhost:8087/remediate -H 'Content-Type: application/json' -d '{"plan_id":"test-1","target":"sheryl","action":"restart"}'
      2. curl -s localhost:8087/ledger?limit=1 | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d['entries'])==1"
    Expected Result: Ledger has 1 entry for remediation action
    Evidence: .omo/evidence/task-23-remediation-ledger.json
  ```

  **Commit**: YES (Wave 5 group)
  - Message: `feat(eim): opencode self-remediation container + health-check hooks`
  - Files: `self-remediation/`

- [x] 24. **Auditor Agent service (board log monitoring, port 8087)**

  **What to do**:
  - The Auditor Agent is co-located with the self-remediation service (same port 8087, separate endpoint paths):
    - `POST /audit/check` — receives board log entry, validates against MemoryPlugin context
    - `POST /audit/report` — generates audit finding if discrepancy found
    - `GET /audit/findings` — lists recent audit findings
    - Compares execution logs against expected policies from MemoryPlugin memory vault
  - Extend `self-remediation/main.py` with audit endpoints
  - Create `self-remediation/auditor.py` — Auditor Agent logic:
    - `validate_board_log(log_entry, memory_context)` → AuditFinding or None
    - `check_vcp(vcp_entry)` — validates VCP (Verified Completion Protocol) entries
    - Stores findings in memory (for now; future: persistent audit database)
  - Write tests: `.test/test_auditor.py` — board log validation, VCP checking, finding generation

  **Must NOT do**:
  - Block execution based on audit findings (report-only for now)
  - Access live board logs from production (test with mock data)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Audit logic, policy validation, data comparison
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 22-23)
  - **Blocks**: 25, 26
  - **Blocked By**: 2 (schemas), 6 (ledger), 10 (MemoryPlugin client for context)

  **References**:
  - `self-remediation/main.py` — shared Flask service (co-located)
  - `executive-quartet/memory_client.py` — MemoryPlugin for context validation
  - `policy/tool-allowlist.txt` — policy reference for audit validation

  **Acceptance Criteria**:
  - [ ] `python -m pytest .test/test_auditor.py -q` → PASS (at least 4 tests)
  - [ ] `curl -s -X POST localhost:8087/audit/check -H 'Content-Type: application/json' -d '{"log_entry":{"action":"kubectl get pods","result":"success"},"vcp":{"status":"completed"}}'` returns finding or null
  - [ ] Auditor detects: tool not in allowlist, missing reasoning ref, metacharacter in command

  **QA Scenarios**:
  ```
  Scenario: Auditor detects allowlist violation
    Tool: Bash (curl)
    Steps:
      1. curl -s -X POST localhost:8087/audit/check -H 'Content-Type: application/json' -d '{"log_entry":{"action":"rm -rf /","result":"blocked"}}'
    Expected Result: AuditFinding with severity "high", reason contains "allowlist"
    Evidence: .omo/evidence/task-24-audit-violation.json

  Scenario: Auditor validates clean log entry
    Tool: Bash (curl)
    Steps:
      1. curl -s -X POST localhost:8087/audit/check -H 'Content-Type: application/json' -d '{"log_entry":{"action":"kubectl get pods","reasoning_ref":"sha256:abc123"},"vcp":{"status":"completed"}}'
    Expected Result: No finding (null or {"finding":null})
    Evidence: .omo/evidence/task-24-audit-clean.json
  ```

  **Commit**: YES (Wave 5 group)
  - Message: `feat(eim): auditor agent — board log + VCP validation`
  - Files: `self-remediation/auditor.py`, `self-remediation/main.py`

- [x] 25. **Health-check hooks for self-remediation loop**

  **What to do**:
  - Extend `self-remediation/health-hooks.py` with the full remediation loop:
    - `probe_all_services()` → returns `{service_name: {healthy: bool, latency_ms: int, error: str|null}}`
    - `trigger_remediation(service_name, failure_type)` → calls Krieger for remediation plan
    - `execute_remediation_plan(plan)` → executes steps via OpenCode container
    - `verify_remediation(service_name)` → re-probes after remediation
    - Loop: probe → detect failure → trigger remediation → execute → verify → log
  - Integrate with Cloud Build health-check triggers (add to cloudbuild.yaml post-deploy verification step)
  - Write tests: `.test/test_health_hooks.py` — probe, detect, trigger, execute (mock), verify

  **Must NOT do**:
  - Automatically remediate without human approval for critical services (track-a, track-b)
  - Execute shell commands outside the OpenCode sandbox

  **Recommended Agent Profile**:
  - **Category**: `quick` — Health check orchestration, loop logic (extends existing self-remediation code)
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 5 (after Tasks 22-24)
  - **Blocks**: 26
  - **Blocked By**: 22 (Telegram bridge), 23 (self-remediation), 24 (Auditor)

  **References**:
  - `self-remediation/health-hooks.py` — existing hooks from Task 23
  - `self-remediation/main.py` — remediation endpoint
  - `executive-quartet/krieger/main.py` — Krieger's /remediate endpoint

  **Acceptance Criteria**:
  - [ ] `python3 -c "from self_remediation.health_hooks import probe_all_services; print(probe_all_services())"` returns service map
  - [ ] `python -m pytest .test/test_health_hooks.py -q` → PASS (at least 4 tests)
  - [ ] Health hook loop: probe → detect failure → trigger → execute → verify → log (all steps testable via mock)

  **QA Scenarios**:
  ```
  Scenario: Health probe detects unhealthy service
    Tool: Bash (Python)
    Steps:
      1. python3 -c "
  from self_remediation.health_hooks import probe_all_services
  # This probes actual running services — some will be down in test
  results = probe_all_services()
  assert isinstance(results, dict)
  print(f'Probed {len(results)} services')
  "
    Expected Result: Returns dict mapping service names to health status
    Evidence: .omo/evidence/task-25-health-probe.json

  Scenario: Remediation loop trigger → execute → verify
    Tool: Bash
    Steps:
      1. python -m pytest .test/test_health_hooks.py::test_remediation_loop -q -v
    Expected Result: Mock loop executes all 5 phases (probe, detect, trigger, execute, verify)
    Evidence: .omo/evidence/task-25-remediation-loop.txt
  ```

  **Commit**: YES (Wave 5 group)
  - Message: `feat(eim): self-remediation health-check loop hooks`
  - Files: `self-remediation/health-hooks.py`

- [x] 26. **Full docker-compose integration (all 9 services)**

  **What to do**:
  - Verify all 9 services start together: `docker compose up --build`
  - Fix any port conflicts, dependency ordering, volume mount issues
  - Ensure all healthchecks pass: track-a (8080), track-b (8081), sheryl (8083), aura (8084), malory (8085), krieger (8086), self-remediation (8087), telegram-bridge (8088)
  - Verify inter-service networking: quartet services can reach MemoryPlugin (external, tested via mock)
  - Verify ledger volumes are correctly mounted and writable for all services
  - Add compose service dependency chains where appropriate
  - Write integration smoke test: `.test/test_compose_integration.py` — starts all services, checks health, verifies cross-service communication

  **Must NOT do**:
  - Remove non-root user from any service
  - Expose any new ports beyond the planned 8080-8088 range
  - Add `allUsers` or public ingress bindings

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Multi-service Docker orchestration, networking, volume management
  - **Skills**: `engineering-devops-automator`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 6 (after Tasks 8-25)
  - **Blocks**: 27, 28, 29
  - **Blocked By**: 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25

  **References**:
  - `docker-compose.yml` — current service definitions
  - `track-a/Dockerfile`, `track-b/Dockerfile` — existing Docker patterns

  **Acceptance Criteria**:
  - [ ] `docker compose up --build -d && sleep 15` starts all services without errors
  - [ ] All health checks pass: `for port in 8080 8081 8083 8084 8085 8086 8087 8088; do curl -fs localhost:$port/healthz && echo ":$port OK" || echo ":$port FAIL"; done` → all OK
  - [ ] `docker compose down` cleans up all containers
  - [ ] `python -m pytest .test/test_compose_integration.py -q` → PASS

  **QA Scenarios**:
  ```
  Scenario: All 9 services start and respond to health checks
    Tool: Bash (docker compose + curl loop)
    Steps:
      1. docker compose up --build -d
      2. sleep 20
      3. for port in 8080 8081 8083 8084 8085 8086 8087 8088; do
           STATUS=$(curl -s -o /dev/null -w '%{http_code}' localhost:$port/healthz)
           echo "Port $port: HTTP $STATUS"
         done
      4. docker compose down
    Expected Result: All 8 ports return HTTP 200
    Evidence: .omo/evidence/task-26-all-healthz.txt

  Scenario: Cross-service communication works
    Tool: Bash (curl chain)
    Steps:
      1. docker compose up --build -d && sleep 15
      2. curl -s -X POST localhost:8083/plan -H 'Content-Type: application/json' -d '{"query":"test cross service"}' | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'steps' in d"
      3. curl -s -X POST localhost:8087/health-check | python3 -c "import sys,json; d=json.load(sys.stdin); assert isinstance(d, dict)"
    Expected Result: Sheryl plan returns steps; Self-remediation health-check returns service map
    Evidence: .omo/evidence/task-26-cross-service.json
  ```

  **Commit**: YES (Wave 6 group)
  - Message: `feat(eim): full docker-compose integration — 9 services`
  - Files: `docker-compose.yml`, `.test/test_compose_integration.py`

- [x] 27. **End-to-end flow test (query → plan → execute → ledger → MemoryPlugin)**

  **What to do**:
  - Create `.test/test_e2e_flow.py` — comprehensive end-to-end test:
    - User submits query to Track A via `/plan`
    - Track A consults OpenViking RAG (extended corpus)
    - Track A generates action plan with reasoning
    - Track B executes an allowlisted action (or mock)
    - Sheryl stores strategic context in MemoryPlugin
    - Malory validates the action against compliance policies
    - Krieger receives any incident reports
    - All ledger entries chain correctly across all services
    - Auditor Agent validates the execution log
  - Test both happy path (allowed action) and blocked path (disallowed action)
  - Test with mock MemoryPlugin (no live API call needed)
  - Verify ledger chain integrity end-to-end

  **Must NOT do**:
  - Execute destructive commands (use `echo "test"` or similar safe commands)
  - Call live external APIs (MemoryPlugin, Telegram) — all must be mocked

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — Multi-service E2E orchestration, complex test scenario
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 6 (after Task 26)
  - **Blocks**: F1-F4 (verification needs E2E passing)
  - **Blocked By**: 26

  **References**:
  - `.test/test_compose_integration.py` — integration test pattern from Task 26
  - `track-a/main.py:/plan` — entry point for query
  - `executive-quartet/memory_client.py` — MemoryPlugin mock pattern

  **Acceptance Criteria**:
  - [ ] `python -m pytest .test/test_e2e_flow.py -q` → PASS (at least 3 scenarios: happy path, blocked action, ledger chain)
  - [ ] E2E test covers: Track A → Track B → MemoryPlugin → Malory compliance → Auditor validation
  - [ ] Ledger chain verified: all entries across all services have valid prev_hash → chain_hash links

  **QA Scenarios**:
  ```
  Scenario: Full E2E happy path
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest .test/test_e2e_flow.py::test_e2e_happy_path -q -v
    Expected Result: All services participate, query returns steps, ledger chain intact
    Evidence: .omo/evidence/task-27-e2e-happy.txt

  Scenario: E2E blocked action path
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest .test/test_e2e_flow.py::test_e2e_blocked_action -q -v
    Expected Result: Disallowed action blocked by Track B, Malory reports compliance violation, Auditor logs finding
    Evidence: .omo/evidence/task-27-e2e-blocked.txt
  ```

  **Commit**: YES (Wave 6 group)
  - Message: `feat(eim): end-to-end flow test — full C-P-A + quartet + audit chain`
  - Files: `.test/test_e2e_flow.py`

- [x] 28. **Cloud Build path-aware triggers for new services**

  **What to do**:
  - Extend `cloudbuild.yaml` path-detection step with new directory patterns:
    - `executive-quartet/*` → BUILD_QUARTET=true (reuse existing flags or add new)
    - `telegram-bridge/*` → BUILD_TELEGRAM=true
    - `self-remediation/*` → BUILD_REMEDIATION=true
    - `cloudflare/*` → BUILD_CLOUDFLARE=true (wrangler deploy gated, build only)
    - `barry-preservation/*` → BUILD_BARRY=true
    - `aura-refactor/*` → BUILD_AURA=true
  - Add conditional build steps for each new service group
  - Verify: `python3 -c "import yaml; d=yaml.safe_load(open('cloudbuild.yaml')); print(f'Steps: {len(d[\"steps\"])}')"` shows expanded step count

  **Must NOT do**:
  - Add wrangler deploy to Cloud Build (gated behind checkpoint #6)
  - Add gcloud run deploy for new services without human approval
  - Change existing track-a/track-b path detection

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — CI config, path-aware triggers, conditional builds
  - **Skills**: `engineering-devops-automator`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 6 (with Task 29)
  - **Blocks**: None (final task before verification)
  - **Blocked By**: 4 (initial cloudbuild expansion), 26 (integration confirms service dirs)

  **References**:
  - `cloudbuild.yaml:102-174` — existing detect-changed-paths step
  - `cloudbuild.yaml:182-199` — existing conditional build step pattern

  **Acceptance Criteria**:
  - [ ] `python3 -c "import yaml; d=yaml.safe_load(open('cloudbuild.yaml')); print(len(d['steps']))"` shows ≥ 12 steps
  - [ ] `grep -c 'executive-quartet\|telegram-bridge\|self-remediation\|cloudflare\|barry-preservation\|aura-refactor' cloudbuild.yaml` ≥ 6
  - [ ] All new build steps use `--no-allow-unauthenticated` and sizing constraints

  **QA Scenarios**:
  ```
  Scenario: Cloud Build detects changes in new directories
    Tool: Bash (simulation)
    Steps:
      1. python3 -c "
  import yaml
  with open('cloudbuild.yaml') as f:
      config = yaml.safe_load(f)
  detect_step = [s for s in config['steps'] if s['id'] == 'detect-changed-paths'][0]
  args = detect_step['args'][2]  # the bash script
  print(f'Path detection patterns found: {args.count(\"case\")} case statements')
  "
    Expected Result: At least 6 case statements for new directories
    Evidence: .omo/evidence/task-28-cloudbuild-paths.txt
  ```

  **Commit**: YES (Wave 6 group)
  - Message: `feat(eim): cloud build path-aware triggers for all new services`
  - Files: `cloudbuild.yaml`

- [x] 29. **OpenClaw Maiden Mission placeholder scaffold**

  **What to do**:
  - Create `openclaw-business-module/` directory — placeholder for future OpenClaw development
  - Create `openclaw-business-module/README.md` — describes the maiden mission:
    - Goal: Build the OpenClaw Business Management Module using the deployed EIM infrastructure
    - Current status: PLACEHOLDER — awaiting infrastructure completion (Milestones 1-5)
    - Prerequisites: All 5 EIM milestones operational, Executive Quartet live, MemoryPlugin active, Telegram bridge connected
    - Activation trigger: Sheryl initiates via Telegram command `/initiate-openclaw`
    - Scope placeholder: Business management features (TBD in dedicated planning session)
  - Create `openclaw-business-module/INITIATION.md` — activation protocol:
    - Sheryl receives `/initiate-openclaw` command via Telegram
    - Sheryl validates infrastructure readiness (all health checks green)
    - Sheryl spawns a NEXUS-Sprint verification team via agency-agents-factory
    - Team produces initial OpenClaw sprint plan
  - This is a DOCUMENTATION-ONLY task — no implementation code for OpenClaw

  **Must NOT do**:
  - Start implementing OpenClaw features (out of scope — separate planning session)
  - Create Dockerfiles, services, or code for OpenClaw
  - Pre-define OpenClaw architecture (that's future Prometheus's job)

  **Recommended Agent Profile**:
  - **Category**: `quick` — Documentation-only, no code
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 6 (with Task 28)
  - **Blocks**: None
  - **Blocked By**: 26 (integration confirms infrastructure is ready)

  **References**:
  - `CEM_Update.txt` — reference to OpenClaw as target module
  - EIM Master Integration Blueprint Section IV, Prompt 7 — Maiden Mission activation

  **Acceptance Criteria**:
  - [ ] `test -f openclaw-business-module/README.md` — placeholder README exists
  - [ ] `test -f openclaw-business-module/INITIATION.md` — activation protocol exists
  - [ ] `grep -q 'PLACEHOLDER\|TBD\|future planning' openclaw-business-module/README.md`
  - [ ] `grep -q '/initiate-openclaw' openclaw-business-module/INITIATION.md`

  **QA Scenarios**:
  ```
  Scenario: OpenClaw placeholder documents exist and are clearly marked
    Tool: Bash
    Steps:
      1. ls -la openclaw-business-module/
      2. head -5 openclaw-business-module/README.md
      3. grep -c 'PLACEHOLDER\|placeholder\|TBD' openclaw-business-module/README.md openclaw-business-module/INITIATION.md
    Expected Result: Both files exist, clearly marked as placeholder, no implementation code
    Evidence: .omo/evidence/task-29-openclaw-placeholder.txt
  ```

  **Commit**: YES (Wave 6 group)
  - Message: `feat(eim): openclaw maiden mission placeholder scaffold`
  - Files: `openclaw-business-module/`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .omo/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest .test/ -q` + linter. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify every Dockerfile has non-root user.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start from clean state. `docker compose up --build` — verify all 9 health checks. Execute EVERY QA scenario from EVERY task. Test cross-service integration: query → plan → MemoryPlugin → execute → ledger chain. Test Cloudflare Pages via wrangler dev. Test WebRTC Worker signaling via curl.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything spec'd was built, nothing beyond spec was built. Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(eim): foundation scaffolding — types, configs, terraform, docker-compose` — multiple files
- **Wave 2**: `feat(eim): barry DO-lobe preservation + aura atlas refactor` — barry-preservation/, aura-refactor/
- **Wave 3**: `feat(eim): executive quartet services + memory-plugin MCP + openviking RAG` — executive-quartet/, mcp/tools/, rag/
- **Wave 4**: `feat(eim): cloudflare edge interface — pages, webrtc worker, turnstile` — cloudflare/, wrangler.toml
- **Wave 5**: `feat(eim): telegram bridge + self-remediation + auditor agent` — telegram-bridge/, self-remediation/
- **Wave 6**: `feat(eim): integration — docker-compose, cloud build, e2e tests, openclaw placeholder` — multiple files

All commits: local only. NO push without human approval (checkpoint #2).

---

## Success Criteria

### Verification Commands
```bash
# All health checks (9 services)
for port in 8080 8081 8083 8084 8085 8086 8087 8088; do
  curl -fs localhost:$port/healthz && echo ":$port OK" || echo ":$port FAIL"
done

# Pytest suite passes
python -m pytest .test/ -q

# ReAct loop works end-to-end
curl -fs -X POST localhost:8080/plan \
  -H 'Content-Type: application/json' \
  -d '{"query":"why is latency high"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'steps' in d, 'Missing steps'"

# Ledger chain intact
curl -fs 'localhost:8080/ledger?limit=5' | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d['entries']) > 0"

# MemoryPlugin MCP reachable
curl -fs -X POST https://www.memoryplugin.com/api/mcp/mcp \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${MEMORYPLUGIN_API_KEY}" \
  -d '{"operation":"ping"}' 2>/dev/null || echo "SKIP (external)"

# Terraform validates
terraform -chdir=terraform validate

# Docker compose parses
docker compose config --quiet
```

### Final Checklist
- [ ] All "Must Have" (10 items) present
- [ ] All "Must NOT Have" (14 items) absent
- [ ] All 29 implementation tasks complete with passing tests
- [ ] 7 human-in-the-loop checkpoints documented
- [ ] All evidence files in .omo/evidence/
- [ ] OpenClaw placeholder ready for future planning session

---

## What This Plan Does NOT Do

- Does NOT modify Barry DO-Lobe container internals
- Does NOT remove non-root user from any Dockerfile
- Does NOT add allUsers bindings or public ingress
- Does NOT grant roles/owner or roles/editor
- Does NOT push to remote, deploy to GCP, or wrangler deploy without human approval
- Does NOT read credential directories (.gemini, .google-cloud-sdk, .aws)
- Does NOT create directories under /AISSC_Cloud_Workspace/
- Does NOT exceed Cloud Run free tier (cpu=1, memory=512Mi, min=0, max=1)
- Does NOT implement the OpenClaw Business Management Module (placeholder only)
- Does NOT echo secrets (MemoryPlugin key, Telegram token) to logs or commits
