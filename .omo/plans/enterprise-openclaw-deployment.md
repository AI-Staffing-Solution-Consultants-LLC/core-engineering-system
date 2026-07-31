# enterprise-openclaw-deployment - Work Plan

## TL;DR (For humans)

**What you'll get:** Four enterprise specification documents (department roster, architecture, bootstrap protocol, operational directive) plus 12 fully scaffolded OpenClaw Business Modules under `openclaw-business-module/departments/` — one per business department, each a standardized container with Dockerfile, AgentOS agent roster, Paperclip EIM 4-agent workflow orchestrator, and Hermes message bus hooks.

**Why this approach:** The repo already has ~85 agent skill definitions and a well-established Docker/Cloud Run pattern. Rather than inventing new infrastructure, we create specification files from the directive text, then instantiate a reusable template 12 times with department-specific agent rosters mapped from available skills. Everything is config-only — no runtime code, no live deployment. All 12 departments can be scaffolded in parallel within each phase.

**What it will NOT do:** It will not deploy anything — no `gcloud run deploy`, no `wrangler deploy`, no `terraform apply`. It will not modify existing C-P-A services (track-a, track-b, executive-quartet). It will not push to `main` or `production` branches. It will not implement business logic — each department gets only a Flask health-check skeleton plus configuration files.

**Effort:** XL — 19 implementation tasks + 4 review tasks across 6 waves
**Risk:** Low — all work is file creation in a new subdirectory, no existing code is modified
**Decisions to sanity-check:** Department file location (`openclaw-business-module/departments/`), agent-to-department mapping derived from skill names, deploy excluded from scope

## Scope

### Must have
1. Create four specification files: `openclaw_departments.md`, `ops_architecture.md`, `system_bootstrap_protocol.md`, `master_operational_directive.md` — the canonical source-of-truth for all 12 departmental OpenClaw modules
2. Define a reusable department module template (Dockerfile, agents.json, paperclip-config.json, hermes-gateway.json, .env.example, README.md)
3. Scaffold all 12 departmental modules under `openclaw-business-module/departments/<slug>/` across 4 phases, each instantiating the template with department-specific agent rosters and queue bindings
4. Add docker-compose.yml entries for all 12 department services (commented-out by default)
5. Agent-executed QA: config validation per department (JSON schema, YAML lint, docker compose config --quiet)
6. Git workflow: feature branches per department, merged to `dev`

### Must NOT have (guardrails)
- ❌ Do NOT deploy to GCP Cloud Run, Cloudflare Workers, or any live infrastructure
- ❌ Do NOT run `docker compose up`, `terraform apply`, `gcloud run deploy`, or `wrangler deploy`
- ❌ Do NOT modify existing C-P-A services (track-a/, track-b/, executive-quartet/, telegram-bridge/, self-remediation/)
- ❌ Do NOT modify existing cloudbuild.yaml triggers
- ❌ Do NOT push to `main` or `production` branches — merge to `dev` only
- ❌ Do NOT exceed free-tier sizing (cpu=1, memory=512Mi)
- ❌ Do NOT add `allUsers` IAM binding to any service
- ❌ Do NOT remove non-root user (`coreengine`) from any Dockerfile
- ❌ Do NOT create files outside `openclaw-business-module/departments/` (except docker-compose.yml entries)
- ❌ Do NOT implement runtime Python/JS code beyond the Flask health-check skeleton — this is scaffold/config only
- ❌ Do NOT overwrite `openclaw-business-module/README.md` or `INITIATION.md`
- ❌ Do NOT grant `roles/owner` or `roles/editor` to any principal
- ❌ Do NOT echo secrets in logs or commits

## Verification strategy
- Test decision: agent-executed QA (config-only — no runtime execution)
- Framework: JSON schema validation (Python `json.load` + manual schema checks), YAML lint (docker compose config --quiet), Dockerfile structural checks (grep for non-root, python:3.12-slim)
- Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-<N>-<slug>.txt`

## Execution strategy
### Parallel execution waves

```
Wave 1 (Specification files — Phase A, all parallel):
├── Task 1:  Create master_operational_directive.md
├── Task 2:  Create openclaw_departments.md
├── Task 3:  Create ops_architecture.md
└── Task 4:  Create system_bootstrap_protocol.md

Wave 2 (Template + Phase 1 — Foundation):
├── Task 5:  Define reusable department module template
├── Task 6:  Scaffold 01-infrastructure-devops-sre
├── Task 7:  Scaffold 02-software-engineering-architecture
└── Task 8:  Scaffold 03-quality-assurance-testing

Wave 3 (Phase 2 — Core Intelligence, parallel):
├── Task 9:  Scaffold 04-ai-data-multi-agent
├── Task 10: Scaffold 05-security-privacy-compliance
└── Task 11: Scaffold 06-executive-strategy-pmo

Wave 4 (Phase 3 — Revenue & Growth, parallel):
├── Task 12: Scaffold 07-product-research-innovation
├── Task 13: Scaffold 08-sales-revenue-operations
├── Task 14: Scaffold 09-search-growth-paid-media
└── Task 15: Scaffold 10-marketing-content-brand

Wave 5 (Phase 4 — Back Office, parallel):
├── Task 16: Scaffold 11-customer-success-support
└── Task 17: Scaffold 12-finance-legal-hr-operations

Wave 6 (Integration + QA):
├── Task 18: Add docker-compose.yml entries for all 12 departments
└── Task 19: Agent-executed QA — validate all configs

Wave FINAL (After ALL tasks — parallel reviews):
├── Task F1: Plan compliance audit
├── Task F2: Code quality review
├── Task F3: Real manual QA
└── Task F4: Scope fidelity check
```

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | None | 5 (template references ops_architecture) | 2, 3, 4 |
| 2 | None | 6-17 (all dept scaffolds reference it) | 1, 3, 4 |
| 3 | None | 5 (template references ops_architecture) | 1, 2, 4 |
| 4 | None | None (protocol doc, not config) | 1, 2, 3 |
| 5 | 1, 3 (specs define template content) | 6-17 | None (Wave 2, before dept scaffolds) |
| 6 | 2, 5 | None | 7, 8 |
| 7 | 2, 5 | None | 6, 8 |
| 8 | 2, 5 | None | 6, 7 |
| 9 | 2, 5 | None | 10, 11 |
| 10 | 2, 5 | None | 9, 11 |
| 11 | 2, 5 | None | 9, 10 |
| 12 | 2, 5 | None | 13, 14, 15 |
| 13 | 2, 5 | None | 12, 14, 15 |
| 14 | 2, 5 | None | 12, 13, 15 |
| 15 | 2, 5 | None | 12, 13, 14 |
| 16 | 2, 5 | None | 17 |
| 17 | 2, 5 | None | 16 |
| 18 | 6-17 (all depts must exist) | 19 | None |
| 19 | 18 | None | None |
| F1-F4 | 1-19 | None | All four in parallel |

## Todos

### Wave 1 — Specification Files (Phase A)

- [x] 1. **Create `master_operational_directive.md`**
  What to do: Write `openclaw-business-module/departments/master_operational_directive.md` containing the formalized operational directive from the user's mandate. Content sections:
  1. **Context & Operational Authority** — Authorization for autonomous enterprise deployment
  2. **Technical Stack Mandate** — OpenClaw + AgentOS + Paperclip + Hermes per department
  3. **Phased Execution Sequence** — 4 phases with department list
  4. **Engineering Workflow Loop** — Git branch → scaffold → verify → merge per department
  5. **Core Requirements Per Department** — Container isolation, AgentOS config, Paperclip integration, Hermes hooks
  This file serves as the single-page executive reference for the entire enterprise deployment.
  Must NOT do: Include any implementation details or code. This is a directive document, not a technical spec.
  Parallelization: Wave 1 | Blocked by: None | Blocks: None
  References: User's directive message (this session), `Blueprint_Core_Engineering_System.md:1-79` (existing architecture reference), `AGENTS.md:1-114` (hard constraints)
  Acceptance criteria: `test -f openclaw-business-module/departments/master_operational_directive.md`, `wc -l openclaw-business-module/departments/master_operational_directive.md` ≥ 60, file contains sections "Context & Operational Authority", "Technical Stack Mandate", "Phased Execution Sequence", "Engineering Workflow Loop", "Core Requirements Per Department"
  QA: happy — `grep -c "Phase" openclaw-business-module/departments/master_operational_directive.md` returns ≥ 4 (all four phases referenced). failure — `grep -c "TODO\|TBD\|PLACEHOLDER" openclaw-business-module/departments/master_operational_directive.md` returns 0. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-1-master-directive.txt`
  Commit: YES | `docs(enterprise): create master_operational_directive.md — autonomous enterprise deployment mandate`

- [x] 2. **Create `openclaw_departments.md`**
  What to do: Write `openclaw-business-module/departments/openclaw_departments.md` defining the complete 12-department roster with agent assignments. Content per department:
  - Department number, name, slug, phase
  - Description (one paragraph)
  - Agent roster: list of agent skill names from `.agents/skills/` and `.opencode/agents/` mapped by relevance
  - Communication map: which other departments this department sends/receives messages from
  - Dependencies: which departments must be operational first

  **Agent-to-department mapping (pre-defined):**

  **01-infrastructure-devops-sre** (Phase 1):
  - Agents: devops-automator, sre-site-reliability-engineer, ci-cd-specialist, finops-engineer, network-engineer, engineering-database-administrator
  - Dependencies: None (foundation layer)
  - Communicates with: 02, 04, 05, 12

  **02-software-engineering-architecture** (Phase 1):
  - Agents: software-architect, backend-architect, code-reviewer, git-workflow-master, minimal-change-engineer, rapid-prototyper, senior-developer
  - Dependencies: None (foundation layer)
  - Communicates with: 01, 03, 04, 07

  **03-quality-assurance-testing** (Phase 1):
  - Agents: qa-automation-engineer, performance-engineer, code-reviewer, incident-response-commander, it-service-manager
  - Dependencies: None (foundation layer)
  - Communicates with: 02, 04, 05

  **04-ai-data-multi-agent** (Phase 2):
  - Agents: ai-engineer, multi-agent-systems-architect, data-engineer, ml-engineer, vector-store-manager, prompt-engineer, ai-data-remediation-engineer
  - Dependencies: 01 (infrastructure), 02 (architecture)
  - Communicates with: 01, 02, 03, 05, 07, 09

  **05-security-privacy-compliance** (Phase 2):
  - Agents: identity-access-engineer, section-508-accessibility-specialist, it-service-manager, network-engineer, payments-billing-engineer
  - Dependencies: 01 (infrastructure)
  - Communicates with: 01, 03, 06, 11, 12

  **06-executive-strategy-pmo** (Phase 2):
  - Agents: business-strategist, business-project-manager, business-resource-allocator, business-product-owner, business-finops-analyst
  - Dependencies: None (governance layer, can operate standalone)
  - Communicates with: ALL departments (governance hub)

  **07-product-research-innovation** (Phase 3):
  - Agents: business-product-owner, ux-researcher, rapid-prototyper, design-interaction-designer, design-ux-architect
  - Dependencies: 02 (architecture), 04 (AI)
  - Communicates with: 02, 04, 06, 08, 10

  **08-sales-revenue-operations** (Phase 3):
  - Agents: payments-billing-engineer, business-strategist, cms-developer, email-intelligence-engineer
  - Dependencies: 01 (infrastructure), 05 (security)
  - Communicates with: 06, 07, 09, 10, 11, 12

  **09-search-growth-paid-media** (Phase 3):
  - Agents: search-relevance-engineer, vector-store-manager, data-engineer
  - Dependencies: 01 (infrastructure), 04 (AI/data)
  - Communicates with: 04, 06, 08, 10

  **10-marketing-content-brand** (Phase 3):
  - Agents: brand-guardian, visual-storyteller, ui-designer, technical-writer, frontend-developer, wordpress-performance-engineer, drupal-performance-engineer
  - Dependencies: 01 (infrastructure), 07 (product)
  - Communicates with: 06, 07, 08, 09

  **11-customer-success-support** (Phase 4):
  - Agents: incident-response-commander, it-service-manager, feishu-integration-developer, wechat-mini-program-developer, email-intelligence-engineer, voice-ai-integration-engineer
  - Dependencies: 01 (infrastructure), 05 (security)
  - Communicates with: 05, 06, 08, 12

  **12-finance-legal-hr-operations** (Phase 4):
  - Agents: business-finops-analyst, payments-billing-engineer, it-service-manager, support-legal-compliance-checker, support-finance-tracker
  - Dependencies: 01 (infrastructure), 05 (security), 06 (PMO)
  - Communicates with: 01, 05, 06, 08, 11

  Must NOT do: Invent agents not present in `.agents/skills/` or `.opencode/agents/`. Skip departments with no matching agents.
  Parallelization: Wave 1 | Blocked by: None | Blocks: 6-17
  References: `.agents/skills/` directory listing, `.opencode/agents/` directory listing, user directive (department list and phases)
  Acceptance criteria: `test -f openclaw-business-module/departments/openclaw_departments.md`, `grep -c "^## " openclaw-business-module/departments/openclaw_departments.md` returns ≥ 12 (one section per department), each department section contains "Agents:", "Dependencies:", "Communicates with:"
  QA: happy — `grep -c "Phase 1" openclaw-business-module/departments/openclaw_departments.md` ≥ 1 and `grep -c "Phase 4"` ≥ 1 (all phases present). failure — `grep "TODO\|TBD" openclaw-business-module/departments/openclaw_departments.md` returns 0. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-2-departments.txt`
  Commit: YES | `docs(enterprise): create openclaw_departments.md — 12-department agent roster and communication map`

- [x] 3. **Create `ops_architecture.md`**
  What to do: Write `openclaw-business-module/departments/ops_architecture.md` defining the standardized 6-tier OpenClaw module architecture. Content sections:
  1. **Node Perimeter** — OpenClaw Module Container structure diagram (ASCII art) showing all 6 tiers: Malory (EIM Global Control Plane) → OpenClaw Container → AgentOS → Paperclip → Hermes → Redis → OpenViking
  2. **Container Foundation** — Dockerfile spec: `python:3.12-slim`, non-root `coreengine` user, Flask dev server, port assignment (8101-8112), health check `/healthz`
  3. **AgentOS Configuration** — `agents.json` schema: JSON object with `name`, `version`, `agents` array; each agent has `id`, `name`, `skill_ref` (absolute path to skill file, either `.agents/skills/<dir>/SKILL.md` or `.opencode/agents/<name>.md` — see agent-to-path mapping table below), `model` (default `opencode-go/deepseek-v4-pro`), `role`, `context`
  4. **Paperclip Integration** — `paperclip-config.json` schema: EIM 4-agent workflow orchestrator config with `workflow_name`, `stages` array (ingest, process, validate, output), `routing_rules`, `timeout_ms`, `retry_policy`
  5. **Hermes Event Bus Hooks** — `hermes-gateway.json` schema: queue subscription config with `queue_name` (`queue.<department_slug>`), `inbound_routes`, `outbound_routes`, `message_schema`
  6. **Redis Persistent State** — `redis-client.json` schema: `{"redis_url": "${REDIS_URL}", "connection": {"timeout_ms": 5000, "retry": 3}, "state_keys": {"active_job": "job:active:{id}", "session": "sess:{dept}:{id}"}}`. Protocol A: every container MUST validate Redis ping response on startup before going ONLINE. Redis provides session locks, task queues, fast cache, and state sync across container restarts.
  7. **OpenViking RAG & Context** — `viking-rag.json` schema: `{"viking_url": "${OPENViking_URL}", "mount_point": "viking://", "tiers": {"L0": "abstract_summary", "L1": "overview", "L2": "full_content"}, "paths": {"resources": "viking://resources/", "memories": "viking://user/memories/", "sessions": "viking://user/sessions/", "skills": "viking://agent/skills/"}}`. Protocol B: all agents connect to OpenViking by default for hierarchical RAG context, cross-session memory, and self-evolving skill heuristics.
  8. **Environment Configuration** — `.env.example` template with required vars: `DEPARTMENT_NAME`, `DEPARTMENT_SLUG`, `PORT`, `HERMES_QUEUE_URL`, `AGENTOS_CONFIG_PATH`, `PAPERCLIP_CONFIG_PATH`, `REDIS_URL`, `OPENVIKING_URL`
  9. **Network & Security** — Traffic internal-only (`--no-allow-unauthenticated`), service account `core-engine-worker`, no `allUsers` binding, cpu=1 memory=512Mi
  10. **File Structure** — Standard directory layout per department (10 files)
  11. **Agent ID → skill_ref path mapping table** — Explicit mapping for each agent used in the plan:

  | Agent ID | skill_ref path |
  |---|---|
  | `devops-automator` | `.agents/skills/engineering-devops-automator/SKILL.md` |
  | `sre-site-reliability-engineer` | `.agents/skills/engineering-sre/SKILL.md` |
  | `ci-cd-specialist` | `.agents/skills/ci-cd-specialist/SKILL.md` |
  | `finops-engineer` | `.agents/skills/engineering-finops-engineer/SKILL.md` |
  | `network-engineer` | `.agents/skills/engineering-network-engineer/SKILL.md` |
  | `software-architect` | `.agents/skills/engineering-software-architect/SKILL.md` |
  | `backend-architect` | `.agents/skills/engineering-backend-architect/SKILL.md` |
  | `code-reviewer` | `.agents/skills/engineering-code-reviewer/SKILL.md` |
  | `git-workflow-master` | `.agents/skills/engineering-git-workflow-master/SKILL.md` |
  | `minimal-change-engineer` | `.agents/skills/engineering-minimal-change-engineer/SKILL.md` |
  | `rapid-prototyper` | `.agents/skills/engineering-rapid-prototyper/SKILL.md` |
  | `senior-developer` | `.agents/skills/engineering-senior-developer/SKILL.md` |
  | `qa-automation-engineer` | `.agents/skills/qa-automation-engineer/SKILL.md` |
  | `performance-engineer` | `.agents/skills/performance-engineer/SKILL.md` |
  | `incident-response-commander` | `.agents/skills/engineering-incident-response-commander/SKILL.md` |
  | `it-service-manager` | `.agents/skills/engineering-it-service-manager/SKILL.md` |
  | `ai-engineer` | `.agents/skills/engineering-ai-engineer/SKILL.md` |
  | `multi-agent-systems-architect` | `.agents/skills/engineering-multi-agent-systems-architect/SKILL.md` |
  | `data-engineer` | `.agents/skills/engineering-data-engineer/SKILL.md` |
  | `ml-engineer` | `.agents/skills/ml-engineer/SKILL.md` |
  | `vector-store-manager` | `.agents/skills/vector-store-manager/SKILL.md` |
  | `prompt-engineer` | `.agents/skills/engineering-prompt-engineer/SKILL.md` |
  | `ai-data-remediation-engineer` | `.agents/skills/engineering-ai-data-remediation-engineer/SKILL.md` |
  | `identity-access-engineer` | `.agents/skills/engineering-identity-access-engineer/SKILL.md` |
  | `section-508-accessibility-specialist` | `.agents/skills/engineering-section-508-specialist/SKILL.md` |
  | `payments-billing-engineer` | `.agents/skills/engineering-payments-billing-engineer/SKILL.md` |
  | `business-strategist` | `.agents/skills/business-strategist/SKILL.md` |
  | `business-project-manager` | `.agents/skills/project-manager/SKILL.md` |
  | `business-resource-allocator` | `.agents/skills/resource-allocator/SKILL.md` |
  | `business-product-owner` | `.agents/skills/product-owner/SKILL.md` |
  | `business-finops-analyst` | `.agents/skills/finops-analyst/SKILL.md` |
  | `ux-researcher` | `.agents/skills/design-ux-researcher/SKILL.md` |
  | `design-interaction-designer` | `.agents/skills/interaction-designer/SKILL.md` |
  | `design-ux-architect` | `.agents/skills/design-ux-architect/SKILL.md` |
  | `cms-developer` | `.agents/skills/engineering-cms-developer/SKILL.md` |
  | `email-intelligence-engineer` | `.agents/skills/engineering-email-intelligence-engineer/SKILL.md` |
  | `search-relevance-engineer` | `.agents/skills/engineering-search-relevance-engineer/SKILL.md` |
  | `brand-guardian` | `.agents/skills/design-brand-guardian/SKILL.md` |
  | `visual-storyteller` | `.agents/skills/design-visual-storyteller/SKILL.md` |
  | `ui-designer` | `.agents/skills/design-ui-designer/SKILL.md` |
  | `technical-writer` | `.agents/skills/engineering-technical-writer/SKILL.md` |
  | `frontend-developer` | `.agents/skills/engineering-frontend-developer/SKILL.md` |
  | `wordpress-performance-engineer` | `.agents/skills/engineering-wordpress-performance/SKILL.md` |
  | `drupal-performance-engineer` | `.agents/skills/engineering-drupal-performance/SKILL.md` |
  | `feishu-integration-developer` | `.agents/skills/engineering-feishu-integration-developer/SKILL.md` |
  | `wechat-mini-program-developer` | `.agents/skills/engineering-wechat-mini-program-developer/SKILL.md` |
  | `voice-ai-integration-engineer` | `.agents/skills/engineering-voice-ai-integration-engineer/SKILL.md` |
  | `engineering-database-administrator` | `.opencode/agents/database-administrator.md` |
  | `support-legal-compliance-checker` | `.opencode/agents/support-legal-compliance-checker.md` |
  | `support-finance-tracker` | `.opencode/agents/support-finance-tracker.md` |

  Must NOT do: Include deployment commands (no `gcloud run deploy`). Include hardcoded secrets or tokens. Omit the agent-to-path mapping table.
  Parallelization: Wave 1 | Blocked by: None | Blocks: 5
  References: `AGENTS.md:1-114` (hard constraints), `track-a/Dockerfile:1-20` (Dockerfile pattern), `track-b/main.py:1-50` (Flask skeleton pattern), `docker-compose.yml:200-240` (commented daemon pattern), `Blueprint_Core_Engineering_System.md:24-36` (Hermes architecture), `terraform/cloudrun.tf` (Cloud Run sizing constraints)
  Acceptance criteria: `test -f openclaw-business-module/departments/ops_architecture.md`, file contains sections "Node Perimeter", "Container Foundation", "AgentOS Configuration", "Paperclip Integration", "Hermes Event Bus Hooks", "Redis Persistent State", "OpenViking RAG & Context", "Environment Configuration", "Network & Security", "File Structure", "Agent ID → skill_ref path mapping table". Mapping table has ≥ 48 rows.
  QA: happy — `grep -c "python:3.12-slim"` ≥ 1, `grep -c "coreengine"` ≥ 1, `grep -c "queue\."` ≥ 1, `grep -c "REDIS_URL"` ≥ 1, `grep -c "OPENVIKING_URL"` ≥ 1, `grep -c "Protocol A"` ≥ 1, `grep -c "Protocol B"` ≥ 1. failure — `grep "allUsers\|roles/owner\|roles/editor"` returns 0. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-3-ops-architecture.txt`
  Commit: YES | `docs(enterprise): create ops_architecture.md — 6-tier OpenClaw module architecture with Redis + OpenViking`

- [x] 4. **Create `system_bootstrap_protocol.md`**
  What to do: Write `openclaw-business-module/departments/system_bootstrap_protocol.md` defining the creation loop per department. Content sections:
  1. **Pre-flight Checks** — Verify dev branch, clean working tree, docker compose config --quiet, available agent skills exist
  2. **Git Workflow** — `git checkout dev`, `git pull origin dev`, `git checkout -b feature/deploy-<department-slug>`
  3. **Scaffold Steps** — Create directory, copy template files, populate agents.json with roster, configure paperclip-config.json, bind hermes-gateway.json
  4. **Verification Gates** — JSON schema validation, Dockerfile structural checks, docker compose config --quiet, file count verification
  5. **Merge Criteria** — All verification gates pass, no TODO/TBD in any file, agent roster matches openclaw_departments.md
  6. **Merge & Next** — `git add`, `git commit`, `git checkout dev`, `git merge feature/deploy-<slug>`, advance to next department
  7. **Error Recovery** — What to do if a gate fails, when to abort, rollback procedure

  Must NOT do: Include `git push` without human-in-the-loop note. Include `terraform apply` or `gcloud run deploy`.
  Parallelization: Wave 1 | Blocked by: None | Blocks: None
  References: User directive (workflow loop section), `AGENTS.md:1-114` (branch and push constraints), `existing .omo/evidence/PHASE-*.md` (prior phase gate patterns)
  Acceptance criteria: `test -f openclaw-business-module/departments/system_bootstrap_protocol.md`, file contains sections "Pre-flight Checks", "Git Workflow", "Scaffold Steps", "Verification Gates", "Merge Criteria", "Merge & Next", "Error Recovery"
  QA: happy — `grep -c "feature/deploy-" openclaw-business-module/departments/system_bootstrap_protocol.md` ≥ 1 (branch naming convention). failure — `grep "git push" openclaw-business-module/departments/system_bootstrap_protocol.md` returns non-zero exit code (grep found no unannotated push) OR every occurrence is immediately followed by `[HUMAN-APPROVAL-REQUIRED]` within the same line. Verify with: `! grep "git push" openclaw-business-module/departments/system_bootstrap_protocol.md || grep -c "git push.*HUMAN-APPROVAL-REQUIRED" openclaw-business-module/departments/system_bootstrap_protocol.md` ≥ 1. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-4-bootstrap-protocol.txt`
  Commit: YES | `docs(enterprise): create system_bootstrap_protocol.md — department creation loop`

### Wave 2 — Template + Phase 1 (Foundation)

- [ ] 5. **Define reusable department module template**
  What to do: Create `openclaw-business-module/departments/_template/` with the following files (10 total):
  1. `Dockerfile` — Same pattern as `track-a/Dockerfile:1-20`: `FROM python:3.12-slim`, create non-root `coreengine` user, copy requirements.txt + main.py + *.json, expose `$PORT`, `CMD python -u main.py`
  2. `requirements.txt` — `flask==3.1.0` (only dependency for the health-check skeleton; no additional packages)
  3. `main.py` — Minimal Flask service: `/healthz` returns `{"status": "ok", "department": os.environ["DEPARTMENT_NAME"], "slug": os.environ["DEPARTMENT_SLUG"]}`, reads `agents.json` at startup, loads config from env vars. NO business logic — skeleton only.
  4. `agents.json` — Template with `name` and `agents` array placeholder. Schema: `{"name": "<DEPARTMENT_NAME>", "version": "0.1.0", "department_slug": "<SLUG>", "phase": <N>, "agents": [{"id": "<agent_id>", "skill_ref": "<SEE_OPS_ARCHITECTURE_MAPPING_TABLE>", "model": "opencode-go/deepseek-v4-pro", "role": "<one-line role>"}]}` — USE the explicit mapping table from `ops_architecture.md` Section 11; never derive from agent ID.
  5. `paperclip-config.json` — EIM 4-agent workflow template. Schema: `{"workflow_name": "<dept-slug>-workflow", "stages": [{"name": "ingest", "agent": "<primary-agent>", "timeout_ms": 30000}, {"name": "process", "agent": "<secondary-agent>", "timeout_ms": 60000}, {"name": "validate", "agent": "<qa-agent>", "timeout_ms": 30000}, {"name": "output", "agent": "<primary-agent>", "timeout_ms": 15000}], "routing_rules": [], "retry_policy": {"max_retries": 3, "backoff_ms": 1000}}`
  6. `hermes-gateway.json` — Queue subscription template. Schema: `{"queue_name": "queue.<dept-slug>", "inbound_routes": [{"event": "*", "handler": "process_message"}], "outbound_routes": [], "message_schema": {"event": "string", "payload": "object", "timestamp": "ISO8601"}}`
  7. **`redis-client.json`** — Redis persistent state & caching config. Schema: `{"redis_url": "${REDIS_URL}", "connection": {"timeout_ms": 5000, "retry": 3}, "state_keys": {"active_job": "job:active:{id}", "session": "sess:<dept-slug>:{id}"}}` — Protocol A: container startup MUST validate Redis ping before declaring ONLINE.
  8. **`viking-rag.json`** — OpenViking RAG & context database config. Schema: `{"viking_url": "${OPENVIKING_URL}", "mount_point": "viking://", "tiers": {"L0": "abstract_summary", "L1": "overview", "L2": "full_content"}, "paths": {"resources": "viking://resources/", "memories": "viking://user/memories/", "sessions": "viking://user/sessions/", "skills": "viking://agent/skills/"}}` — Protocol B: all agents connect to OpenViking by default for hierarchical RAG context.
  9. `.env.example` — `DEPARTMENT_NAME=<Name>`, `DEPARTMENT_SLUG=<slug>`, `PORT=81<NN>`, `HERMES_QUEUE_URL=amqp://hermes:5672`, `AGENTOS_CONFIG_PATH=/app/agents.json`, `PAPERCLIP_CONFIG_PATH=/app/paperclip-config.json`, **`REDIS_URL=redis://redis:6379/0`**, **`OPENVIKING_URL=viking://openviking:9000`**
  10. `README.md` — Template with department name, phase, description, agent roster (from openclaw_departments.md), dependencies, communication map

  Must NOT do: Hard-code department-specific values in the template (use `<PLACEHOLDER>` syntax). Include secrets or tokens.
  Parallelization: Wave 2 | Blocked by: 1, 2, 3 | Blocks: 6-17
  References: `track-a/Dockerfile:1-20`, `track-b/main.py:1-50`, `docker-compose.yml:200-240` (commented daemon pattern), `ops_architecture.md` (Task 3 output — USE the agent-to-path mapping table for skill_ref values), `openclaw_departments.md` (Task 2 output)
  Acceptance criteria: All 10 template files exist. `python -c "import json; json.load(open('openclaw-business-module/departments/_template/agents.json'))"` exits 0. Ditto for paperclip-config.json, hermes-gateway.json, redis-client.json, viking-rag.json. Dockerfile has `coreengine` user and `python:3.12-slim`.
  QA: happy — `grep -c "coreengine" openclaw-business-module/departments/_template/Dockerfile` ≥ 1. `grep -c "PLACEHOLDER" openclaw-business-module/departments/_template/agents.json` ≥ 1. `grep -c "REDIS_URL" openclaw-business-module/departments/_template/.env.example` ≥ 1. `grep -c "OPENVIKING_URL" openclaw-business-module/departments/_template/.env.example` ≥ 1. `grep -c "Protocol A" openclaw-business-module/departments/_template/redis-client.json` ≥ 1. `grep -c "Protocol B" openclaw-business-module/departments/_template/viking-rag.json` ≥ 1. failure — `grep "allUsers\|roles/owner" openclaw-business-module/departments/_template/Dockerfile` returns 0. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-5-template.txt`
  Commit: YES | `feat(enterprise): define reusable 10-file department module template with Redis + OpenViking`

- [ ] 6. **Scaffold 01-infrastructure-devops-sre**
  What to do: Create `openclaw-business-module/departments/01-infrastructure-devops-sre/` populated from `_template/`. Replace placeholders:
  - DEPARTMENT_NAME: "Infrastructure & DevOps & SRE"
  - DEPARTMENT_SLUG: "infrastructure-devops-sre"
  - PORT: 8101
  - PHASE: 1
  - agents.json roster: devops-automator, sre-site-reliability-engineer, ci-cd-specialist, finops-engineer, network-engineer, engineering-database-administrator
  - paperclip-config.json stages: ingest→devops-automator, process→sre-site-reliability-engineer, validate→ci-cd-specialist, output→devops-automator
  - hermes-gateway.json queue_name: "queue.infrastructure-devops-sre"
  - README.md: populated from openclaw_departments.md section for department 01

  Must NOT do: Modify template files. Add runtime code beyond the skeleton main.py.
  Parallelization: Wave 2 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Task 2 output, Section 01), `_template/` (Task 5 output), `.agents/skills/engineering-devops-automator/SKILL.md`, `.agents/skills/engineering-sre/SKILL.md`, `.agents/skills/ci-cd-specialist/SKILL.md`, `.agents/skills/engineering-finops-engineer/SKILL.md`, `.agents/skills/engineering-network-engineer/SKILL.md`, `.opencode/agents/database-administrator.md`
  Acceptance criteria: Directory exists with Dockerfile, requirements.txt, main.py, agents.json, paperclip-config.json, hermes-gateway.json, .env.example, README.md. `python -c "import json; d=json.load(open('openclaw-business-module/departments/01-infrastructure-devops-sre/agents.json')); assert len(d['agents'])==6"` exits 0. `grep "queue.infrastructure-devops-sre" openclaw-business-module/departments/01-infrastructure-devops-sre/hermes-gateway.json`. No PLACEHOLDER strings remain in any file.
  QA: happy — `python -c "import json; json.load(open('openclaw-business-module/departments/01-infrastructure-devops-sre/agents.json'))"` exits 0. `grep -c "PLACEHOLDER" openclaw-business-module/departments/01-infrastructure-devops-sre/agents.json` returns 0. failure — `grep "TODO\|TBD" openclaw-business-module/departments/01-infrastructure-devops-sre/*.md` returns 0. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-6-dept-01.txt`
  Commit: YES | `feat(enterprise): scaffold 01-infrastructure-devops-sre department module`

- [ ] 7. **Scaffold 02-software-engineering-architecture**
  What to do: Create `openclaw-business-module/departments/02-software-engineering-architecture/` from `_template/` with:
  - DEPARTMENT_NAME: "Software Engineering & Architecture"
  - DEPARTMENT_SLUG: "software-engineering-architecture"
  - PORT: 8102
  - PHASE: 1
  - agents: software-architect, backend-architect, code-reviewer, git-workflow-master, minimal-change-engineer, rapid-prototyper, senior-developer
  - paperclip stages: ingest→software-architect, process→backend-architect, validate→code-reviewer, output→senior-developer
  - queue: "queue.software-engineering-architecture"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 2 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 02), `_template/`, `.agents/skills/engineering-software-architect/SKILL.md`, `.agents/skills/engineering-backend-architect/SKILL.md`, `.agents/skills/engineering-code-reviewer/SKILL.md`, `.agents/skills/engineering-git-workflow-master/SKILL.md`, `.agents/skills/engineering-minimal-change-engineer/SKILL.md`, `.agents/skills/engineering-rapid-prototyper/SKILL.md`, `.agents/skills/engineering-senior-developer/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/02-software-engineering-architecture/agents.json')); assert len(d['agents'])==7"`. No PLACEHOLDER strings.
  QA: happy — JSON parse succeeds, agent count=7. `grep "queue.software-engineering-architecture" openclaw-business-module/departments/02-software-engineering-architecture/hermes-gateway.json`. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-7-dept-02.txt`
  Commit: YES | `feat(enterprise): scaffold 02-software-engineering-architecture department module`

- [ ] 8. **Scaffold 03-quality-assurance-testing**
  What to do: Create `openclaw-business-module/departments/03-quality-assurance-testing/` from `_template/` with:
  - DEPARTMENT_NAME: "Quality Assurance & Testing"
  - DEPARTMENT_SLUG: "quality-assurance-testing"
  - PORT: 8103
  - PHASE: 1
  - agents: qa-automation-engineer, performance-engineer, code-reviewer, incident-response-commander, it-service-manager
  - paperclip stages: ingest→qa-automation-engineer, process→performance-engineer, validate→code-reviewer, output→qa-automation-engineer
  - queue: "queue.quality-assurance-testing"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 2 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 03), `_template/`, `.agents/skills/qa-automation-engineer/SKILL.md`, `.agents/skills/performance-engineer/SKILL.md`, `.agents/skills/engineering-code-reviewer/SKILL.md`, `.agents/skills/engineering-incident-response-commander/SKILL.md`, `.agents/skills/engineering-it-service-manager/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/03-quality-assurance-testing/agents.json')); assert len(d['agents'])==5"`. No PLACEHOLDER strings.
  QA: happy — JSON parse succeeds, agent count=5. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-8-dept-03.txt`
  Commit: YES | `feat(enterprise): scaffold 03-quality-assurance-testing department module`

### Wave 3 — Phase 2 (Core Intelligence & Governance)

- [ ] 9. **Scaffold 04-ai-data-multi-agent**
  What to do: Create `openclaw-business-module/departments/04-ai-data-multi-agent/` from `_template/` with:
  - DEPARTMENT_NAME: "AI & Data & Multi-Agent Systems"
  - DEPARTMENT_SLUG: "ai-data-multi-agent"
  - PORT: 8104
  - PHASE: 2
  - agents: ai-engineer, multi-agent-systems-architect, data-engineer, ml-engineer, vector-store-manager, prompt-engineer, ai-data-remediation-engineer
  - paperclip stages: ingest→ai-engineer, process→multi-agent-systems-architect, validate→data-engineer, output→ai-engineer
  - queue: "queue.ai-data-multi-agent"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 3 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 04), `_template/`, `.agents/skills/engineering-ai-engineer/SKILL.md`, `.agents/skills/engineering-multi-agent-systems-architect/SKILL.md`, `.agents/skills/engineering-data-engineer/SKILL.md`, `.agents/skills/ml-engineer/SKILL.md`, `.agents/skills/vector-store-manager/SKILL.md`, `.agents/skills/engineering-prompt-engineer/SKILL.md`, `.agents/skills/engineering-ai-data-remediation-engineer/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/04-ai-data-multi-agent/agents.json')); assert len(d['agents'])==7"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=7. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-9-dept-04.txt`
  Commit: YES | `feat(enterprise): scaffold 04-ai-data-multi-agent department module`

- [ ] 10. **Scaffold 05-security-privacy-compliance**
  What to do: Create `openclaw-business-module/departments/05-security-privacy-compliance/` from `_template/` with:
  - DEPARTMENT_NAME: "Security & Privacy & Compliance"
  - DEPARTMENT_SLUG: "security-privacy-compliance"
  - PORT: 8105
  - PHASE: 2
  - agents: identity-access-engineer, section-508-accessibility-specialist, it-service-manager, network-engineer, payments-billing-engineer
  - paperclip stages: ingest→identity-access-engineer, process→it-service-manager, validate→section-508-accessibility-specialist, output→identity-access-engineer
  - queue: "queue.security-privacy-compliance"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 3 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 05), `_template/`, `.agents/skills/engineering-identity-access-engineer/SKILL.md`, `.agents/skills/engineering-section-508-specialist/SKILL.md`, `.agents/skills/engineering-it-service-manager/SKILL.md`, `.agents/skills/engineering-network-engineer/SKILL.md`, `.agents/skills/engineering-payments-billing-engineer/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/05-security-privacy-compliance/agents.json')); assert len(d['agents'])==5"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=5. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-10-dept-05.txt`
  Commit: YES | `feat(enterprise): scaffold 05-security-privacy-compliance department module`

- [ ] 11. **Scaffold 06-executive-strategy-pmo**
  What to do: Create `openclaw-business-module/departments/06-executive-strategy-pmo/` from `_template/` with:
  - DEPARTMENT_NAME: "Executive Strategy & PMO"
  - DEPARTMENT_SLUG: "executive-strategy-pmo"
  - PORT: 8106
  - PHASE: 2
  - agents: business-strategist, business-project-manager, business-resource-allocator, business-product-owner, business-finops-analyst
  - paperclip stages: ingest→business-strategist, process→business-project-manager, validate→business-product-owner, output→business-strategist
  - queue: "queue.executive-strategy-pmo"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 3 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 06), `_template/`, `.agents/skills/business-strategist/SKILL.md`, `.agents/skills/project-manager/SKILL.md`, `.agents/skills/resource-allocator/SKILL.md`, `.agents/skills/product-owner/SKILL.md`, `.agents/skills/finops-analyst/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/06-executive-strategy-pmo/agents.json')); assert len(d['agents'])==5"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=5. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-11-dept-06.txt`
  Commit: YES | `feat(enterprise): scaffold 06-executive-strategy-pmo department module`

### Wave 4 — Phase 3 (Revenue & Growth Engine)

- [ ] 12. **Scaffold 07-product-research-innovation**
  What to do: Create `openclaw-business-module/departments/07-product-research-innovation/` from `_template/` with:
  - DEPARTMENT_NAME: "Product & Research & Innovation"
  - DEPARTMENT_SLUG: "product-research-innovation"
  - PORT: 8107
  - PHASE: 3
  - agents: business-product-owner, ux-researcher, rapid-prototyper, design-interaction-designer, design-ux-architect
  - paperclip stages: ingest→business-product-owner, process→ux-researcher, validate→design-ux-architect, output→rapid-prototyper
  - queue: "queue.product-research-innovation"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 4 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 07), `_template/`, `.agents/skills/product-owner/SKILL.md`, `.agents/skills/design-ux-researcher/SKILL.md`, `.agents/skills/engineering-rapid-prototyper/SKILL.md`, `.agents/skills/interaction-designer/SKILL.md`, `.agents/skills/design-ux-architect/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/07-product-research-innovation/agents.json')); assert len(d['agents'])==5"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=5. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-12-dept-07.txt`
  Commit: YES | `feat(enterprise): scaffold 07-product-research-innovation department module`

- [ ] 13. **Scaffold 08-sales-revenue-operations**
  What to do: Create `openclaw-business-module/departments/08-sales-revenue-operations/` from `_template/` with:
  - DEPARTMENT_NAME: "Sales & Revenue Operations"
  - DEPARTMENT_SLUG: "sales-revenue-operations"
  - PORT: 8108
  - PHASE: 3
  - agents: payments-billing-engineer, business-strategist, cms-developer, email-intelligence-engineer
  - paperclip stages: ingest→business-strategist, process→payments-billing-engineer, validate→email-intelligence-engineer, output→business-strategist
  - queue: "queue.sales-revenue-operations"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 4 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 08), `_template/`, `.agents/skills/engineering-payments-billing-engineer/SKILL.md`, `.agents/skills/business-strategist/SKILL.md`, `.agents/skills/engineering-cms-developer/SKILL.md`, `.agents/skills/engineering-email-intelligence-engineer/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/08-sales-revenue-operations/agents.json')); assert len(d['agents'])==4"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=4. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-13-dept-08.txt`
  Commit: YES | `feat(enterprise): scaffold 08-sales-revenue-operations department module`

- [ ] 14. **Scaffold 09-search-growth-paid-media**
  What to do: Create `openclaw-business-module/departments/09-search-growth-paid-media/` from `_template/` with:
  - DEPARTMENT_NAME: "Search & Growth & Paid Media"
  - DEPARTMENT_SLUG: "search-growth-paid-media"
  - PORT: 8109
  - PHASE: 3
  - agents: search-relevance-engineer, vector-store-manager, data-engineer
  - paperclip stages: ingest→search-relevance-engineer, process→data-engineer, validate→vector-store-manager, output→search-relevance-engineer
  - queue: "queue.search-growth-paid-media"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 4 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 09), `_template/`, `.agents/skills/engineering-search-relevance-engineer/SKILL.md`, `.agents/skills/vector-store-manager/SKILL.md`, `.agents/skills/engineering-data-engineer/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/09-search-growth-paid-media/agents.json')); assert len(d['agents'])==3"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=3. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-14-dept-09.txt`
  Commit: YES | `feat(enterprise): scaffold 09-search-growth-paid-media department module`

- [ ] 15. **Scaffold 10-marketing-content-brand**
  What to do: Create `openclaw-business-module/departments/10-marketing-content-brand/` from `_template/` with:
  - DEPARTMENT_NAME: "Marketing & Content & Brand"
  - DEPARTMENT_SLUG: "marketing-content-brand"
  - PORT: 8110
  - PHASE: 3
  - agents: brand-guardian, visual-storyteller, ui-designer, technical-writer, frontend-developer, wordpress-performance-engineer, drupal-performance-engineer
  - paperclip stages: ingest→brand-guardian, process→ui-designer, validate→technical-writer, output→frontend-developer
  - queue: "queue.marketing-content-brand"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 4 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 10), `_template/`, `.agents/skills/design-brand-guardian/SKILL.md`, `.agents/skills/design-visual-storyteller/SKILL.md`, `.agents/skills/design-ui-designer/SKILL.md`, `.agents/skills/engineering-technical-writer/SKILL.md`, `.agents/skills/engineering-frontend-developer/SKILL.md`, `.agents/skills/engineering-wordpress-performance/SKILL.md`, `.agents/skills/engineering-drupal-performance/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/10-marketing-content-brand/agents.json')); assert len(d['agents'])==7"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=7. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-15-dept-10.txt`
  Commit: YES | `feat(enterprise): scaffold 10-marketing-content-brand department module`

### Wave 5 — Phase 4 (Back Office & Customer Operations)

- [ ] 16. **Scaffold 11-customer-success-support**
  What to do: Create `openclaw-business-module/departments/11-customer-success-support/` from `_template/` with:
  - DEPARTMENT_NAME: "Customer Success & Support"
  - DEPARTMENT_SLUG: "customer-success-support"
  - PORT: 8111
  - PHASE: 4
  - agents: incident-response-commander, it-service-manager, feishu-integration-developer, wechat-mini-program-developer, email-intelligence-engineer, voice-ai-integration-engineer
  - paperclip stages: ingest→incident-response-commander, process→it-service-manager, validate→email-intelligence-engineer, output→incident-response-commander
  - queue: "queue.customer-success-support"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 5 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 11), `_template/`, `.agents/skills/engineering-incident-response-commander/SKILL.md`, `.agents/skills/engineering-it-service-manager/SKILL.md`, `.agents/skills/engineering-feishu-integration-developer/SKILL.md`, `.agents/skills/engineering-wechat-mini-program-developer/SKILL.md`, `.agents/skills/engineering-email-intelligence-engineer/SKILL.md`, `.agents/skills/engineering-voice-ai-integration-engineer/SKILL.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/11-customer-success-support/agents.json')); assert len(d['agents'])==6"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=6. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-16-dept-11.txt`
  Commit: YES | `feat(enterprise): scaffold 11-customer-success-support department module`

- [ ] 17. **Scaffold 12-finance-legal-hr-operations**
  What to do: Create `openclaw-business-module/departments/12-finance-legal-hr-operations/` from `_template/` with:
  - DEPARTMENT_NAME: "Finance & Legal & HR Operations"
  - DEPARTMENT_SLUG: "finance-legal-hr-operations"
  - PORT: 8112
  - PHASE: 4
  - agents: business-finops-analyst, payments-billing-engineer, it-service-manager, support-legal-compliance-checker, support-finance-tracker
  - paperclip stages: ingest→business-finops-analyst, process→payments-billing-engineer, validate→support-legal-compliance-checker, output→support-finance-tracker
  - queue: "queue.finance-legal-hr-operations"

  Must NOT do: Same constraints as Task 6.
  Parallelization: Wave 5 | Blocked by: 2, 5 | Blocks: 18
  References: `openclaw_departments.md` (Section 12), `_template/`, `.agents/skills/finops-analyst/SKILL.md`, `.agents/skills/engineering-payments-billing-engineer/SKILL.md`, `.agents/skills/engineering-it-service-manager/SKILL.md`, `.opencode/agents/support-legal-compliance-checker.md`, `.opencode/agents/support-finance-tracker.md`
  Acceptance criteria: All 10 files present. `python -c "import json; d=json.load(open('openclaw-business-module/departments/12-finance-legal-hr-operations/agents.json')); assert len(d['agents'])==5"`. No PLACEHOLDER.
  QA: happy — JSON parse succeeds, agent count=5. failure — no TODO/TBD/PLACEHOLDER. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-17-dept-12.txt`
  Commit: YES | `feat(enterprise): scaffold 12-finance-legal-hr-operations department module`

### Wave 6 — Integration & QA

- [ ] 18. **Add docker-compose.yml entries for all 12 departments**
  What to do: Append 12 commented-out service definitions to `docker-compose.yml` following the existing `agency-agents-daemon` pattern. Each entry:
  ```yaml
  # service: <dept-slug> (default OFF — Phase <N> department module)
  # <dept-slug>:
  #   build:
  #     context: ./openclaw-business-module/departments/<dept-slug>
  #     dockerfile: Dockerfile
  #   ports:
  #     - "81<NN>:81<NN>"
  #   environment:
  #     - DEPARTMENT_NAME=<Name>
  #     - DEPARTMENT_SLUG=<slug>
  #     - PORT=81<NN>
  #     - HERMES_QUEUE_URL=${HERMES_QUEUE_URL:-amqp://hermes:5672}
  #     - REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
  #     - OPENVIKING_URL=${OPENVIKING_URL:-viking://openviking:9000}
  #   volumes:
  #     - ./openclaw-business-module/departments/<dept-slug>/agents.json:/app/agents.json:ro
  #     - ./openclaw-business-module/departments/<dept-slug>/paperclip-config.json:/app/paperclip-config.json:ro
  #     - ./openclaw-business-module/departments/<dept-slug>/redis-client.json:/app/redis-client.json:ro
  #     - ./openclaw-business-module/departments/<dept-slug>/viking-rag.json:/app/viking-rag.json:ro
  #   restart: "no"
  ```

  Do this for all 12 departments (ports 8101-8112). Append after the existing `agency-agents-daemon` commented block.
  Must NOT do: Uncomment any service. Add `allUsers` binding. Exceed memory limits. Remove non-root user.
  Parallelization: Wave 6 | Blocked by: 6-17 | Blocks: 19
  References: `docker-compose.yml:200-240` (existing commented daemon pattern), `AGENTS.md` constraints section, `ops_architecture.md` (Task 3 output)
  Acceptance criteria: `docker compose config --quiet` exits 0. `grep -c "# <dept-slug> (default OFF" docker-compose.yml` ≥ 12 (one comment per department). `grep "81<NN>" docker-compose.yml` returns 0 (no literal placeholder — all ports are real numbers 8101-8112).
  QA: happy — `docker compose config --quiet` succeeds with all 12 departments present (still commented, no runtime impact). `grep -c "openclaw-business-module/departments/" docker-compose.yml` ≥ 12. failure — `grep "allUsers\|--allow-unauthenticated" docker-compose.yml` returns 0. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-18-docker-compose.txt`
  Commit: YES | `feat(enterprise): add commented docker-compose entries for all 12 department modules`

- [ ] 19. **Agent-executed QA — validate all configs**
  What to do: Run a comprehensive validation sweep across all 12 department directories + spec files:
  1. JSON schema validation: parse every `agents.json`, `paperclip-config.json`, `hermes-gateway.json`, `redis-client.json`, `viking-rag.json` (60 files total: 5 per dept × 12) with `find openclaw-business-module/departments -name "*.json" -exec python -c "import json; json.load(open('{}'))" \;` — all must exit 0
  2. Check agent references: verify each agent `skill_ref` in agents.json points to an existing file under `.agents/skills/` or `.opencode/agents/`. Use: `for f in $(find openclaw-business-module/departments/0*-*/ -name agents.json); do python -c "import json,os; d=json.load(open('$f')); [os.path.exists(a['skill_ref']) or sys.exit(f'MISSING: {a[\"skill_ref\"]}') for a in d['agents']]" 2>&1 || echo "FAIL: $f"; done`
  3. Placeholder audit: `grep -r "PLACEHOLDER\|TODO\|TBD" openclaw-business-module/departments/` must return 0 (exit code 1 = no matches found = PASS)
  4. Dockerfile structural check: each Dockerfile has `FROM python:3.12-slim`, `coreengine` user, `EXPOSE`, `CMD python -u main.py`. Use: `for f in $(find openclaw-business-module/departments/0*-*/ -name Dockerfile); do grep -q "FROM python:3.12-slim" "$f" && grep -q "coreengine" "$f" && grep -q "EXPOSE" "$f" && grep -q "CMD python -u main.py" "$f" || echo "FAIL: $f"; done`
  5. `docker compose config --quiet` succeeds (requires Docker daemon running — no containers started)
  6. File count: each department directory has at least the 10 required template files (Dockerfile, requirements.txt, main.py, agents.json, paperclip-config.json, hermes-gateway.json, redis-client.json, viking-rag.json, .env.example, README.md). Use: `for d in openclaw-business-module/departments/0*-*/; do for f in Dockerfile requirements.txt main.py agents.json paperclip-config.json hermes-gateway.json redis-client.json viking-rag.json .env.example README.md; do test -f "$d$f" || echo "MISSING: $d$f"; done; done`
  7. Port uniqueness: ports 8101-8112 are assigned exactly once across all `.env.example` files. Use: `grep -h "^PORT=" openclaw-business-module/departments/0*-*/.env.example | sort | uniq -c | awk '$1 > 1 {print "DUPLICATE: "$0}'`
  8. Queue name consistency: each `hermes-gateway.json` queue_name matches the department slug pattern `queue.<slug>`. Use: `for f in $(find openclaw-business-module/departments/0*-*/ -name hermes-gateway.json); do python -c "import json,os; d=json.load(open('$f')); slug=os.path.basename(os.path.dirname('$f')); assert d['queue_name']==f'queue.{slug}', f'{d[\"queue_name\"]} != queue.{slug}'" || echo "FAIL: $f"; done`
  9. Redis & OpenViking protocol presence: `grep -rl "REDIS_URL" openclaw-business-module/departments/0*-*/.env.example | wc -l` returns 12, `grep -rl "OPENVIKING_URL" openclaw-business-module/departments/0*-*/.env.example | wc -l` returns 12
  10. Agent roster cross-reference: each department's agent count in agents.json matches its entry in `openclaw_departments.md` — use the per-task acceptance criteria counts (6, 7, 5, 7, 5, 5, 5, 4, 3, 7, 6, 5)

  Must NOT do: Run `docker compose up`. Make live network calls. Modify any files — validation only.
  Parallelization: Wave 6 | Blocked by: 18 | Blocks: F1-F4
  References: All department directories (Tasks 6-17 outputs), `_template/` (Task 5 output), `docker-compose.yml` (Task 18 output), `.agents/skills/` directory, `.opencode/agents/` directory, `ops_architecture.md` (Task 3, agent mapping table)
  Acceptance criteria: All 10 validation checks pass. Zero errors. Evidence written to `.omo/evidence/enterprise-openclaw-deployment/task-19-qa.txt` with per-check pass/fail counts.
  QA: happy — `find openclaw-business-module/departments -name "*.json" -exec python -c "import json; json.load(open('{}'))" \; 2>&1 | grep -c Traceback` returns 0 (zero JSON parse errors). failure — any check fails: evidence file captures exact check number + failure message. Evidence: `.omo/evidence/enterprise-openclaw-deployment/task-19-qa.txt`
  Commit: NO (validation only, no code changes — evidence recorded) | Record QA results in evidence file

### Wave FINAL — Parallel Reviewers

- [ ] F1. **Plan compliance audit**
  Verify: Every Must-Have item (#1-6 in Scope) is covered by at least one todo. Every Must-NOT-Have guardrail is referenced in at least one todo's "Must NOT do" section. All 12 departments are present in Tasks 6-17. Dependency matrix is internally consistent (no task blocked by itself, all "Blocks" entries have matching "Blocked by" entries). No circular dependencies.
  Commands:
  ```
  grep -c "Must have" .omo/plans/enterprise-openclaw-deployment.md  # ≥ 6 items
  grep -c "Must NOT have" .omo/plans/enterprise-openclaw-deployment.md  # ≥ 11 guardrails
  grep -o "0[1-9]\|1[0-2]-[a-z-]*" .omo/plans/enterprise-openclaw-deployment.md | sort -u | wc -l  # == 12 departments
  ```
  Evidence: `.omo/evidence/enterprise-openclaw-deployment/review-f1-compliance.txt`

- [ ] F2. **Code quality review**
  Verify: All JSON files parse (60 files: 5 per dept × 12). All Dockerfiles follow standard pattern (`FROM python:3.12-slim`, `coreengine`, no `allUsers`). All `.env.example` files have valid port assignments (8101-8112, no duplicates). No hardcoded secrets. No PLACEHOLDER/TODO/TBD in final output.
  Commands:
  ```
  find openclaw-business-module/departments -name "*.json" -exec python -c "import json; json.load(open('{}'))" \; 2>&1 | grep -c Traceback  # == 0
  grep -r "PLACEHOLDER\|TODO\|TBD" openclaw-business-module/departments/  # exit 1 = no matches = PASS
  grep -r "allUsers\|roles/owner" openclaw-business-module/departments/  # exit 1 = PASS
  ```
  Evidence: `.omo/evidence/enterprise-openclaw-deployment/review-f2-quality.txt`

- [ ] F3. **Real manual QA**
  Verify: `docker compose config --quiet` passes (requires Docker daemon). At least 60 JSON files parse successfully. `grep -r "PLACEHOLDER" openclaw-business-module/departments/` returns 0 matches. `grep -r "TODO\|TBD" openclaw-business-module/departments/` returns 0 matches. All `skill_ref` paths in agents.json resolve to existing files (use the success criteria script from L639). Dockerfile count config validation (`coreengine`, `python:3.12-slim`).
  Commands:
  ```
  docker compose config --quiet && echo "PASS" || echo "FAIL: compose config"
  find openclaw-business-module/departments -name "*.json" | wc -l  # ≥ 60 (5 per dept × 12 + 4 spec files)
  for d in openclaw-business-module/departments/0*-*/; do for f in Dockerfile requirements.txt main.py agents.json paperclip-config.json hermes-gateway.json redis-client.json viking-rag.json .env.example README.md; do test -f "$d$f" || echo "MISSING: $d$f"; done; done | grep -c MISSING  # == 0
  ```
  Evidence: `.omo/evidence/enterprise-openclaw-deployment/review-f3-qa.txt`

- [ ] F4. **Scope fidelity check**
  Verify: No files created outside `openclaw-business-module/departments/` (except `docker-compose.yml`). No modification to existing C-P-A services (track-a/, track-b/, executive-quartet/, telegram-bridge/, self-remediation/, agency-agents/). No deployment commands (`gcloud run deploy`, `terraform apply`, `wrangler deploy`) in any department file. No `allUsers` or `roles/owner` references. `openclaw-business-module/README.md` and `INITIATION.md` are unmodified.
  Commands:
  ```
  git diff --stat dev -- openclaw-business-module/README.md openclaw-business-module/INITIATION.md  # must be empty
  git diff --stat dev -- track-a/ track-b/ executive-quartet/ telegram-bridge/ self-remediation/ agency-agents/  # must be empty
  grep -r "gcloud run deploy\|terraform apply\|wrangler deploy" openclaw-business-module/departments/  # exit 1 = PASS
  grep -r "allUsers\|roles/owner" openclaw-business-module/departments/  # exit 1 = PASS
  ```
  Evidence: `.omo/evidence/enterprise-openclaw-deployment/review-f4-scope.txt`

## Final verification wave
All four F1-F4 reviewers run in parallel. ALL must APPROVE before plan is considered complete.

## Commit strategy
- One commit per task (Tasks 1-18), cumulative on `dev` branch
- Task 19 is validation-only — no commit, evidence recorded
- Feature branches: `feature/deploy-enterprise-specs` (Tasks 1-4), `feature/deploy-enterprise-template` (Task 5), then `feature/deploy-<dept-slug>` per department (Tasks 6-17)
- Merge order: Specs → Template → Phase 1 → Phase 2 → Phase 3 → Phase 4 → docker-compose → QA
- NO automatic push — human-in-the-loop required per AGENTS.md

## Success criteria
```bash
# 1. All 4 spec files exist
test -f openclaw-business-module/departments/master_operational_directive.md
test -f openclaw-business-module/departments/openclaw_departments.md
test -f openclaw-business-module/departments/ops_architecture.md
test -f openclaw-business-module/departments/system_bootstrap_protocol.md

# 2. Template directory has 10 files
ls openclaw-business-module/departments/_template/ | wc -l   # == 10

# 3. All 12 department directories exist
ls -d openclaw-business-module/departments/0*-*/ | wc -l   # == 12

# 4. Each department has at least the 10 required template files
for d in openclaw-business-module/departments/0*-*/; do
  for f in Dockerfile requirements.txt main.py agents.json paperclip-config.json hermes-gateway.json redis-client.json viking-rag.json .env.example README.md; do
    test -f "$d$f" || echo "MISSING: $d$f"
  done
done | grep -c MISSING   # == 0

# 5. All JSON files parse
find openclaw-business-module/departments -name "*.json" -exec python -c "import json; json.load(open('{}'))" \;

# 6. No placeholders
grep -r "PLACEHOLDER\|TODO\|TBD" openclaw-business-module/departments/   # must return 0 matches

# 7. docker compose parses
docker compose config --quiet   # exits 0

# 8. All agent skill_refs exist
for f in $(find openclaw-business-module/departments/0*-*/ -name agents.json); do
  python -c "
import json, os
d = json.load(open('$f'))
for a in d['agents']:
  skill_path = a['skill_ref'].replace('.agents/', '.agents/')
  assert os.path.exists(os.path.join('/home/olly/core-engineering-system', skill_path)), f'Missing: {skill_path}'
print('OK: $f')
"
done
```
