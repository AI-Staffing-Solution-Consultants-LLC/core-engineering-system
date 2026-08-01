# OpenClaw Business Module — Standardized Department Architecture

**Version**: 0.1.0
**Audience**: Platform engineers, agent scaffold generators, deployment pipeline owners
**Status**: Canonical reference — all department containers MUST conform to this spec

This document defines the 6-tier architecture for every department node in the OpenClaw business module. It is the single source of truth for container layout, agent roster, protocol compliance, and file structure. Downstream scaffold tasks (Tasks 5-17 in the enterprise deployment plan) consume the agent mapping table in Section 11 to auto-generate department configurations.

---

## 1. Node Perimeter

Each department runs as an isolated container within the OpenClaw module boundary. The stack layers from the executive control plane down through the runtime foundation.

```
[ Malory: Executive Business Manager / Paperclip Global Control Plane ]
                          │
                          ▼ (EIM Directives & Workflows)
┌──────────────────────────────────────────────────────────────────┐
│ Department Node Perimeter: OpenClaw Module Container             │
│  ├── Runtime Foundation: AgentOS                                 │
│  ├── Orchestration Engine: Paperclip (EIM 4-agent workflow)      │
│  ├── Communications Gateway: Hermes Client (queue.<dept_slug>)   │
│  ├── Fast State & Ephemeral Memory: Redis Client                 │
│  └── Knowledge & RAG Engine: OpenViking Client (viking://)       │
└──────────────────────────────────────────────────────────────────┘
```

Malory dispatches work items through the EIM directives layer. Each department container receives EIM workflows via Paperclip, communicates with sibling containers over Hermes queues, and pulls hierarchical context from OpenViking. Redis handles session locks and task state. AgentOS hosts the agent roster that executes each workflow stage.

---

## 2. Container Foundation

Every department ships as a slim Flask container with a predictable port range and health contract.

**Dockerfile specification:**

```dockerfile
FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash coreengine
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER coreengine
EXPOSE 8101
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8101/healthz || exit 1

CMD ["python", "-u", "main.py"]
```

**Port assignment scheme:** Each department gets a sequential port in the 8101-8112 range. The mapping is department-specific and declared in each department's `main.py` and `.env.example`.

**Health check endpoint:** Every container MUST expose `GET /healthz` returning:

```json
{"status": "ok", "department": "<Department Name>", "slug": "<dept_slug>"}
```

The health check is the signal that the container is ready to receive work. AgentOS must complete its startup sequence (Redis ping via Protocol A, OpenViking connection via Protocol B) before the health check returns `ok`.

**Runtime:** Flask dev server (`app.run()`), not gunicorn. This is intentional during scaffolding. Upgrading to a production WSGI server is a future optimization tracked separately.

**Requirements:** Each department's `requirements.txt` declares exactly `flask==3.1.0`. Additional dependencies are added per department as needed.

---

## 3. AgentOS Configuration

AgentOS is the runtime that loads, initializes, and hosts agents within the container. Each container has exactly one `agents.json` file at its root.

**Schema:**

```json
{
  "name": "<Department Name>",
  "version": "0.1.0",
  "department_slug": "<dept_slug>",
  "phase": 1,
  "agents": [
    {
      "id": "<agent_id>",
      "skill_ref": "<path>",
      "model": "opencode-go/deepseek-v4-pro",
      "role": "<short description of the agent's responsibility>"
    }
  ]
}
```

**Field definitions:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable department name |
| `version` | Yes | Semver string matching the container image tag |
| `department_slug` | Yes | URL-safe slug used in queue names, Redis keys, and file paths |
| `phase` | Yes | Startup order within the department (1 = first wave) |
| `agents` | Yes | Array of agent definitions |
| `agents[].id` | Yes | Unique agent identifier, must match a row in Section 11 |
| `agents[].skill_ref` | Yes | File path to the agent's SKILL.md or agents.md file |
| `agents[].model` | Yes | LLM model identifier |
| `agents[].role` | Yes | One-line description of what this agent does in production |

**Path conventions for `skill_ref`:**

- Agency skills (from the core engineering system): `.agents/skills/<category>/SKILL.md`
- OpenCode agents (custom or internal): `.opencode/agents/<name>.md`

The complete mapping of agent IDs to skill_ref paths is in Section 11. Every `agents.json` in every department MUST use the exact paths listed there. No aliases, no shortcuts.

---

## 4. Paperclip Integration

Paperclip is the EIM (Enterprise Integration Manager) orchestration engine. It receives work directives from Malory, decomposes them into 4-stage workflows, and routes each stage to the appropriate agent in the roster.

**Configuration file:** `paperclip-config.json` at the container root.

**Schema:**

```json
{
  "workflow_name": "<dept_slug>-workflow",
  "stages": [
    {
      "name": "ingest",
      "agent": "<agent_id>",
      "timeout_ms": 30000
    },
    {
      "name": "process",
      "agent": "<agent_id>",
      "timeout_ms": 60000
    },
    {
      "name": "validate",
      "agent": "<agent_id>",
      "timeout_ms": 30000
    },
    {
      "name": "output",
      "agent": "<agent_id>",
      "timeout_ms": 15000
    }
  ],
  "routing_rules": [],
  "retry_policy": {
    "max_retries": 3,
    "backoff_ms": 1000
  }
}
```

**Stage execution order:** ingest → process → validate → output. Each stage runs sequentially within a workflow. A stage failure triggers the retry policy. After `max_retries` failures, the workflow is marked `FAILED` and the failed payload is written to a dead-letter queue for manual inspection.

**Timeout semantics:** `timeout_ms` is a hard deadline per stage. If an agent exceeds it, the stage is cancelled and counted as a failure toward the retry budget.

**Routing rules:** The `routing_rules` array is reserved for future fan-out and conditional routing. It is empty in the initial scaffold.

---

## 5. Hermes Event Bus Hooks

Hermes provides inter-department communication via named queues. Every container subscribes to its department queue and can publish to any sibling queue.

**Configuration file:** `hermes-gateway.json` at the container root.

**Schema:**

```json
{
  "queue_name": "queue.<dept_slug>",
  "inbound_routes": [
    {
      "event": "*",
      "handler": "process_message"
    }
  ],
  "outbound_routes": [],
  "message_schema": {
    "event": "string",
    "payload": "object",
    "timestamp": "ISO8601"
  }
}
```

**Queue naming:** Every department queue follows the pattern `queue.<dept_slug>`. The department slug is the canonical slug declared in `agents.json` and `.env.example`.

**Inbound handling:** The wildcard `"*"` event route means the container processes all messages arriving on its queue. The `process_message` handler is implemented in `main.py` and dispatches to the appropriate Paperclip workflow based on the event type.

**Message envelope:** Every message on Hermes carries three fields:

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Event type identifier (e.g., `work_order.created`) |
| `payload` | object | Arbitrary JSON payload specific to the event |
| `timestamp` | ISO8601 | UTC timestamp of message creation |

**Outbound routes:** The `outbound_routes` array is populated per department based on which sibling queues it needs to publish to. It is empty in the scaffold and filled during department-specific wiring.

---

## 6. Redis Persistent State

Redis acts as the fast state layer for session management, task queues, and ephemeral caching across container restarts.

**Configuration file:** `redis-client.json` at the container root.

**Schema:**

```json
{
  "redis_url": "${REDIS_URL}",
  "connection": {
    "timeout_ms": 5000,
    "retry": 3
  },
  "state_keys": {
    "active_job": "job:active:{id}",
    "session": "sess:<dept_slug>:{id}"
  }
}
```

**Protocol A — Redis Startup Ping:**

> Every container MUST validate a Redis ping response on startup before declaring ONLINE. The health check endpoint SHALL NOT return `ok` until the Redis connection is confirmed.

This is a hard gate. If Redis is unreachable at startup, the container logs the error, retries up to the configured limit (3 attempts, 5-second timeout per attempt), and exits with code 1 if all retries fail.

**Purpose:**

- **Session locks:** Prevent concurrent processing of the same work item across container restarts
- **Task queues:** Hold pending EIM workflow items before Paperclip picks them up
- **Fast cache:** Store intermediate results that are expensive to recompute
- **State sync:** Survive container restarts without losing in-flight work state

**Environment variable:** `REDIS_URL` is set per environment. In local dev via docker-compose, it is `redis://redis:6379/0`. In GCP Cloud Run, it is the Redis instance connection string stored in Secret Manager.

**Key naming:** All Redis keys are namespaced by department slug to prevent collisions. The `{id}` placeholder is replaced at runtime with the specific work item or session identifier.

---

## 7. OpenViking RAG & Context

OpenViking provides hierarchical, tiered knowledge retrieval for agents. Every container connects to the OpenViking service at startup.

**Configuration file:** `viking-rag.json` at the container root.

**Schema:**

```json
{
  "viking_url": "${OPENVIKING_URL}",
  "mount_point": "viking://",
  "tiers": {
    "L0": "abstract_summary",
    "L1": "overview",
    "L2": "full_content"
  },
  "paths": {
    "resources": "viking://resources/",
    "memories": "viking://user/memories/",
    "sessions": "viking://user/sessions/",
    "skills": "viking://agent/skills/"
  }
}
```

**Protocol B — OpenViking Default Connection:**

> All agents connect to OpenViking by default for hierarchical RAG context. The container MUST establish a connection to `viking_url` during startup. Agent context windows pull from OpenViking tiers before processing any workflow stage.

**Tiered loading for token efficiency:**

| Tier | Name | Purpose | Typical size |
|------|------|---------|-------------|
| L0 | Abstract summary | One-paragraph summary of the resource. Loaded first for every query. | ~100 tokens |
| L1 | Overview | Section-level summaries and key metadata. Loaded when L0 indicates relevance. | ~500 tokens |
| L2 | Full content | The complete resource body. Loaded only when deep context is required. | Variable |

Agents request L0 context first, then escalate to L1 or L2 only if the abstract indicates the resource is relevant to the current task. This keeps context windows lean and token costs low.

**Four namespaces:**

| Namespace | Mount path | Contents |
|-----------|-----------|----------|
| Resources | `viking://resources/` | Department documents, policies, runbooks, reference material |
| User memories | `viking://user/memories/` | Per-user knowledge accumulated across sessions |
| User sessions | `viking://user/sessions/` | Historical session transcripts and context |
| Agent skills | `viking://agent/skills/` | Agent-authored heuristics, learned patterns, skill refinements |

**Self-evolving knowledge:** Agents write new heuristics and learnings back to `viking://agent/skills/` and `viking://user/memories/`. Over time, the knowledge base improves without manual curation. Each write is timestamped and attributed to the writing agent for auditability.

**Environment variable:** `OPENVIKING_URL` is set per environment. In local dev via docker-compose, it is `viking://openviking:9000`.

---

## 8. Environment Configuration

Each department ships a `.env.example` template that documents all required environment variables. The scaffold generates `.env` from this template (`.env` is `.gitignore`-blocked and never committed).

**Required variables:**

```bash
# Department identity
DEPARTMENT_NAME=Operations
DEPARTMENT_SLUG=ops
PORT=8101

# Hermes event bus
HERMES_QUEUE_URL=amqp://hermes:5672

# Configuration paths (mounted from container filesystem)
AGENTOS_CONFIG_PATH=/app/agents.json
PAPERCLIP_CONFIG_PATH=/app/paperclip-config.json

# Redis persistent state (Protocol A)
REDIS_URL=redis://redis:6379/0

# OpenViking RAG context (Protocol B)
OPENVIKING_URL=viking://openviking:9000
```

**Variable descriptions:**

| Variable | Required | Default (dev) | Purpose |
|----------|----------|---------------|---------|
| `DEPARTMENT_NAME` | Yes | (none) | Human-readable name, appears in health check response |
| `DEPARTMENT_SLUG` | Yes | (none) | URL-safe slug, used in queue names, Redis keys, file paths |
| `PORT` | Yes | (none) | Container port (8101-8112 range) |
| `HERMES_QUEUE_URL` | Yes | `amqp://hermes:5672` | Hermes message broker connection |
| `AGENTOS_CONFIG_PATH` | Yes | `/app/agents.json` | Path to AgentOS roster file |
| `PAPERCLIP_CONFIG_PATH` | Yes | `/app/paperclip-config.json` | Path to Paperclip workflow config |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection string (Protocol A) |
| `OPENVIKING_URL` | Yes | `viking://openviking:9000` | OpenViking service URL (Protocol B) |

Production values are injected via GCP Secret Manager or Cloud Run environment variables. No secrets are ever hardcoded in `.env.example` or any committed file.

---

## 9. Network & Security

All department containers run under strict security constraints. These are non-negotiable and enforced at the Terraform layer.

**Traffic:** Internal-only. All Cloud Run services are deployed with `--no-allow-unauthenticated`. The `INGRESS_TRAFFIC_INTERNAL_ONLY` setting blocks all public internet traffic. Communication between containers goes through Cloud Run's internal networking or Hermes queues.

**Service account:** All containers use the single service account `core-engine-worker@aissc-core-engine-self-dep.iam.gserviceaccount.com`.

**Allowed IAM roles (exhaustive list):**

| Role | Purpose |
|------|---------|
| `roles/run.invoker` | Allow one Cloud Run service to call another |
| `roles/secretmanager.secretAccessor` | Read secrets at startup (Redis URL, API keys) |
| `roles/logging.logWriter` | Write structured logs to Cloud Logging |
| `roles/iam.serviceAccountTokenCreator` | Generate OIDC tokens for service-to-service auth |

**Explicitly forbidden:**

- `allUsers` IAM binding (public access): never, under any circumstance.
- `roles/owner`: never.
- `roles/editor`: never.

**Resource sizing (Cloud Run free tier compliance):**

| Parameter | Value |
|-----------|-------|
| CPU | 1 |
| Memory | 512Mi |
| Min instances | 0 |
| Max instances | 1 |

If GCP quota errors occur, memory can be dropped to 256Mi. It must never be raised above 512Mi.

**Project and region:** All resources live in `aissc-core-engine-self-dep`, region `us-central1`. No other projects or regions are authorized for this module.

---

## 10. File Structure

Every department container has a standard directory layout. All 10 files are present at scaffold time (some as templates, some as functional code).

```
<dept_slug>/
├── Dockerfile
├── requirements.txt
├── main.py
├── agents.json
├── paperclip-config.json
├── hermes-gateway.json
├── redis-client.json
├── viking-rag.json
├── .env.example
└── README.md
```

**File purposes:**

| File | Type | Description |
|------|------|-------------|
| `Dockerfile` | Infrastructure | Container build spec (python:3.12-slim, coreengine user) |
| `requirements.txt` | Dependency | Python package manifest (starts with `flask==3.1.0`) |
| `main.py` | Application | Flask app with `/healthz` endpoint and queue listener skeleton |
| `agents.json` | Configuration | AgentOS roster with agent IDs and skill_ref paths |
| `paperclip-config.json` | Configuration | EIM 4-agent workflow (ingest, process, validate, output) |
| `hermes-gateway.json` | Configuration | Queue subscription and message schema |
| `redis-client.json` | Configuration | Redis connection and state key patterns (Protocol A) |
| `viking-rag.json` | Configuration | OpenViking tiered RAG context (Protocol B) |
| `.env.example` | Template | Environment variable documentation (no secrets) |
| `README.md` | Documentation | Department-specific onboarding and operational guide |

**File ordering by type:**

1. Infrastructure (Dockerfile) — defines the runtime
2. Application (main.py, requirements.txt) — the executable code
3. Configuration (agents.json, paperclip-config.json, hermes-gateway.json, redis-client.json, viking-rag.json) — the declarative state
4. Templates (.env.example) — the environment contract
5. Documentation (README.md) — the human-facing guide

---

## 11. Agent ID → skill_ref Path Mapping Table

This table is the canonical mapping between agent identifiers and their skill definition files. Every `agents.json` in every department MUST use the exact paths listed here. No aliases, no relative-path shortcuts, no alternative filenames.

Downstream scaffold tasks (Tasks 5-17) read this table to populate each department's agent roster.

| Agent ID | skill_ref path |
|---|---|
| devops-automator | .agents/skills/engineering-devops-automator/SKILL.md |
| sre-site-reliability-engineer | .agents/skills/engineering-sre/SKILL.md |
| ci-cd-specialist | .agents/skills/ci-cd-specialist/SKILL.md |
| finops-engineer | .agents/skills/engineering-finops-engineer/SKILL.md |
| network-engineer | .agents/skills/engineering-network-engineer/SKILL.md |
| software-architect | .agents/skills/engineering-software-architect/SKILL.md |
| backend-architect | .agents/skills/engineering-backend-architect/SKILL.md |
| code-reviewer | .agents/skills/engineering-code-reviewer/SKILL.md |
| git-workflow-master | .agents/skills/engineering-git-workflow-master/SKILL.md |
| minimal-change-engineer | .agents/skills/engineering-minimal-change-engineer/SKILL.md |
| rapid-prototyper | .agents/skills/engineering-rapid-prototyper/SKILL.md |
| senior-developer | .agents/skills/engineering-senior-developer/SKILL.md |
| qa-automation-engineer | .agents/skills/qa-automation-engineer/SKILL.md |
| performance-engineer | .agents/skills/performance-engineer/SKILL.md |
| incident-response-commander | .agents/skills/engineering-incident-response-commander/SKILL.md |
| it-service-manager | .agents/skills/engineering-it-service-manager/SKILL.md |
| ai-engineer | .agents/skills/engineering-ai-engineer/SKILL.md |
| multi-agent-systems-architect | .agents/skills/engineering-multi-agent-systems-architect/SKILL.md |
| data-engineer | .agents/skills/engineering-data-engineer/SKILL.md |
| ml-engineer | .agents/skills/ml-engineer/SKILL.md |
| vector-store-manager | .agents/skills/vector-store-manager/SKILL.md |
| prompt-engineer | .agents/skills/engineering-prompt-engineer/SKILL.md |
| ai-data-remediation-engineer | .agents/skills/engineering-ai-data-remediation-engineer/SKILL.md |
| identity-access-engineer | .agents/skills/engineering-identity-access-engineer/SKILL.md |
| section-508-accessibility-specialist | .agents/skills/engineering-section-508-specialist/SKILL.md |
| payments-billing-engineer | .agents/skills/engineering-payments-billing-engineer/SKILL.md |
| business-strategist | .agents/skills/business-strategist/SKILL.md |
| business-project-manager | .agents/skills/project-manager/SKILL.md |
| business-resource-allocator | .agents/skills/resource-allocator/SKILL.md |
| business-product-owner | .agents/skills/product-owner/SKILL.md |
| business-finops-analyst | .agents/skills/finops-analyst/SKILL.md |
| ux-researcher | .agents/skills/design-ux-researcher/SKILL.md |
| design-interaction-designer | .agents/skills/interaction-designer/SKILL.md |
| design-ux-architect | .agents/skills/design-ux-architect/SKILL.md |
| cms-developer | .agents/skills/engineering-cms-developer/SKILL.md |
| email-intelligence-engineer | .agents/skills/engineering-email-intelligence-engineer/SKILL.md |
| search-relevance-engineer | .agents/skills/engineering-search-relevance-engineer/SKILL.md |
| brand-guardian | .agents/skills/design-brand-guardian/SKILL.md |
| visual-storyteller | .agents/skills/design-visual-storyteller/SKILL.md |
| ui-designer | .agents/skills/design-ui-designer/SKILL.md |
| technical-writer | .agents/skills/engineering-technical-writer/SKILL.md |
| frontend-developer | .agents/skills/engineering-frontend-developer/SKILL.md |
| wordpress-performance-engineer | .agents/skills/engineering-wordpress-performance/SKILL.md |
| drupal-performance-engineer | .agents/skills/engineering-drupal-performance/SKILL.md |
| feishu-integration-developer | .agents/skills/engineering-feishu-integration-developer/SKILL.md |
| wechat-mini-program-developer | .agents/skills/engineering-wechat-mini-program-developer/SKILL.md |
| voice-ai-integration-engineer | .agents/skills/engineering-voice-ai-integration-engineer/SKILL.md |
| engineering-database-administrator | .opencode/agents/database-administrator.md |
| support-legal-compliance-checker | .opencode/agents/support-legal-compliance-checker.md |
| support-finance-tracker | .opencode/agents/support-finance-tracker.md |

**Row count:** 50 agent IDs. This table covers all known agents from the core engineering system's skill registry (`engineering-*`, `design-*`, `business-*`, `ml-*`, `qa-*`, `ci-cd-*`, `performance-*`) plus three support agents under the `.opencode/agents/` namespace.

**Path conventions reminder:**

- `.agents/skills/<category>/SKILL.md` — agency skills shipped with the core engineering system
- `.opencode/agents/<name>.md` — custom or internal agents specific to OpenCode

**Usage note for scaffold generators:** When iterating this table to produce `agents.json`, skip any agent ID that does not apply to the target department. The table is the universe. Each department's roster is a subset.
