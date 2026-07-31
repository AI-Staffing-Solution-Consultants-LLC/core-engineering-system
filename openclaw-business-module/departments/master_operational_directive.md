# Master Operational Directive
## Enterprise OpenClaw Business Module Deployment

**Classification**: ORD-001 | **Authority**: Prometheus/OpenCode Executive Layer | **Status**: Active

This directive authorizes and governs the autonomous enterprise deployment of 12 departmental OpenClaw Business Modules. It is the single source of truth for architectural standards, execution sequencing, engineering workflow, and compliance gates. All subordinate module specifications, bootstrap protocols, and architecture documents derive their authority from this directive.

The Core Engineering System serves as the operational foundation. Its C-P-A (Context-Planning-Action) cognitive loop, tamper-evident ledger, and constitutional enforcement gates provide the runtime substrate on which every departmental module depends. This directive does not replace or modify the Core Engineering System. It extends it laterally, provisioning 12 standardized containers that operate as peers within the enterprise fabric.

No module is deployed to production by this directive. Scaffolding, configuration, and local validation are authorized. Production deployment requires explicit human approval through the engineering workflow gates defined herein.

---

## Section 1: Context and Operational Authority

This directive is the Prometheus/OpenCode enterprise authorization for full autonomous engineering across 12 business departments. It is the executable mandate for the following:

1. **Enterprise scaffolding**: Instantiate 12 standardized OpenClaw Business Module containers, one per department, under `openclaw-business-module/departments/<slug>/`.
2. **Agent provisioning**: Populate each container with a department-specific agent roster derived from the 85 available agent skill definitions in the repository.
3. **Configuration completeness**: Every module ships with AgentOS, Paperclip EIM, Hermes gateway, Redis client, and OpenViking RAG configuration files. No module is considered provisioned until all six configuration artifacts pass structural validation.
4. **Branch discipline**: All work occurs on `dev`. No work occurs on `main` or `production`. Feature branches follow the naming convention `feature/deploy-<department-slug>`. Merges require human approval.
5. **Compliance gating**: Every module must satisfy the Core Requirements enumerated in Section 5 before proceeding to the next phase. No partial scaffolding, no skipped validations, no bypassed gates.

This directive is not a suggestion, a guideline, or a starting point for discussion. It is an executable order. Engineering autonomy is granted within these boundaries. Beyond these boundaries, autonomy is withdrawn.

---

## Section 2: Technical Stack Mandate

Every department module inherits a standardized technology stack. Deviations require explicit authorization through an amendment to this directive. The mandatory stack comprises the following components:

**Container Runtime**: Docker, with `python:3.12-slim` as the base image. The non-root user `coreengine` is mandatory. Container isolation is enforced at the Docker level with no shared volumes between departments.

**AgentOS**: Agent lifecycle management, state persistence, and memory. Each container ships an `agents.json` roster enumerating the department's assigned agents, their roles, and their startup configuration. AgentOS governs agent birth, sleep, wake, and termination cycles.

**Paperclip EIM**: Enterprise Integration Middleware executing the 4-agent workflow orchestration pattern. Each container ships a `paperclip-config.json` that defines the department's EIM pipeline: intake agent, processing agent, validation agent, and delivery agent. Paperclip is the workflow execution engine for every department.

**Hermes Client**: Message bus subscriber. Each container ships a `hermes-gateway.json` that binds the department to its designated queue channel: `queue.<department-slug>`. Hermes is the inter-department communication fabric. No department communicates directly with another; all cross-department traffic routes through Hermes queues.

**Redis**: Persistent state backend with mandatory `REDIS_URL` environment variable. The Redis client configuration lives in `redis-client.json`. Redis stores agent state snapshots, workflow checkpoints, and cross-session context.

**OpenViking**: Hierarchical RAG context provider with mandatory `OPENVIKING_URL` environment variable. The RAG configuration lives in `viking-rag.json`. OpenViking provides contextual retrieval across the enterprise knowledge graph, organized hierarchically by department, domain, and cross-cutting concern.

**Protocol A (Redis startup validation)**: Every container must validate Redis connectivity at startup. A failed Redis ping constitutes a hard startup failure. The container must not begin agent initialization until Redis responds. This is not optional.

**Protocol B (OpenViking default binding)**: All agents connect to OpenViking by default for hierarchical RAG context. An agent may declare explicit RAG exclusions in its AgentOS configuration, but the default behavior is connection. Agents that operate without RAG context are the exception, not the norm.

---

## Section 3: Phased Execution Sequence

Enterprise deployment proceeds in four sequential phases. Within each phase, department modules may be scaffolded in parallel. No phase begins until all modules in the preceding phase pass Core Requirements validation. This gating is non-negotiable.

### Phase 1: Foundation

The operational backbone. These departments provide the infrastructure, architectural governance, and quality enforcement on which all subsequent phases depend.

| Order | Department | Slug |
|---|---|---|
| 01 | Infrastructure, DevOps, and SRE | `01-infrastructure-devops-sre` |
| 02 | Software Engineering and Architecture | `02-software-engineering-architecture` |
| 03 | Quality Assurance and Testing | `03-quality-assurance-testing` |

Validation gate: All three Foundation modules must pass Section 5 Core Requirements validation before Phase 2 begins.

### Phase 2: Core Intelligence

The analytical and protective layer. These departments provide AI capabilities, security enforcement, and strategic coordination.

| Order | Department | Slug |
|---|---|---|
| 04 | AI, Data, and Multi-Agent Systems | `04-ai-data-multi-agent` |
| 05 | Security, Privacy, and Compliance | `05-security-privacy-compliance` |
| 06 | Executive Strategy and PMO | `06-executive-strategy-pmo` |

Validation gate: All three Core Intelligence modules must pass Section 5 Core Requirements validation before Phase 3 begins.

### Phase 3: Revenue and Growth

The market-facing layer. These departments drive product development, revenue operations, and external presence.

| Order | Department | Slug |
|---|---|---|
| 07 | Product, Research, and Innovation | `07-product-research-innovation` |
| 08 | Sales and Revenue Operations | `08-sales-revenue-operations` |
| 09 | Search, Growth, and Paid Media | `09-search-growth-paid-media` |
| 10 | Marketing, Content, and Brand | `10-marketing-content-brand` |

Validation gate: All four Revenue and Growth modules must pass Section 5 Core Requirements validation before Phase 4 begins.

### Phase 4: Back Office

The support and governance layer. These departments handle customer relationships, financial operations, legal compliance, and human resources.

| Order | Department | Slug |
|---|---|---|
| 11 | Customer Success and Support | `11-customer-success-support` |
| 12 | Finance, Legal, and HR Operations | `12-finance-legal-hr-operations` |

Validation gate: All Phase 4 modules must pass Section 5 Core Requirements validation to complete enterprise deployment. The full 12-department roster is then considered provisioned and verification-ready.

---

## Section 4: Engineering Workflow Loop

Every department module follows an identical engineering workflow. Sequential execution is required per department; parallel execution is authorized across departments within the same phase.

### Per-Department Workflow

1. **Checkout**: Create a feature branch from `dev` named `feature/deploy-<department-slug>`. The slug matches the canonical name in Section 3.
2. **Scaffold**: Instantiate the department module template into `openclaw-business-module/departments/<slug>/`. All seven Core Requirement artifacts (Section 5) must be present.
3. **Verify**: Run structural validation. JSON configuration files must parse without error. Docker Compose configuration must pass `docker compose config --quiet`. Every configuration field marked required in the template must contain a substantive value.
4. **Merge**: Submit the feature branch for human review. Merge to `dev` only after approval. No auto-merge, no auto-push. The human-in-the-loop gate is a hard requirement.
5. **Advance**: Proceed to the next department in the same phase, or signal phase completion if this was the last department in the phase.

### Workflow Constraints

- Branch target is `dev` on `Tizzle716/core-engineering-system`. No other branch, no other repository.
- No auto-push. Every push requires explicit human confirmation at the merge gate.
- Feature branches follow the exact naming convention `feature/deploy-<department-slug>`. Branch names that deviate from this pattern are rejected.
- Verification failures block merge. A department that fails structural validation returns to Step 2 for remediation.
- Workflow state is documented in `.omo/evidence/enterprise-openclaw-deployment/task-<N>-<slug>.txt` for auditability.

---

## Section 5: Core Requirements Per Department

Every department module must satisfy all seven core requirements before it is considered provisioned. No exceptions. No waivers. A module missing any single requirement fails the validation gate and blocks phase progression.

1. **Container isolation**: A Dockerfile using `python:3.12-slim` with the non-root user `coreengine`. Container isolation is enforced per department with no shared filesystem volumes between departments. Port mapping follows the `8<phase><order>` convention.

2. **AgentOS agent roster**: `agents.json` enumerating the department's assigned agents. Each agent entry specifies a name, role identifier, skill reference path within the repository, startup priority, and RAG binding preference. The roster must contain at minimum one agent. AgentOS governs lifecycle operations for every listed agent.

3. **Paperclip EIM workflow**: `paperclip-config.json` defining the 4-agent workflow pipeline: intake agent, processing agent, validation agent, and delivery agent. Each pipeline stage specifies the assigned agent, input schema, output schema, retry policy, and timeout threshold.

4. **Hermes queue subscription**: `hermes-gateway.json` binding the department to `queue.<department-slug>`. This artifact specifies subscription mode, message format, acknowledgment policy, and the department's published event types. No cross-department direct communication is permitted.

5. **Redis persistent state**: `redis-client.json` with connection parameters, key namespace prefix, session TTL defaults, and retry strategy. The `REDIS_URL` environment variable is mandatory and must be documented in `.env.example`.

6. **OpenViking RAG context**: `viking-rag.json` with the OpenViking endpoint, department namespace, default retrieval settings, and index scope. The `OPENVIKING_URL` environment variable is mandatory and must be documented in `.env.example`.

7. **Department documentation**: `README.md` covering department purpose, agent roster summary, queue subscriptions, configuration variable reference, and startup instructions. Documentation quality is part of the validation gate; a one-line README fails.

### Mandatory Environment Variables

Every department module ships with `.env.example` containing at minimum:

- `REDIS_URL`: Redis connection string for persistent state storage.
- `OPENVIKING_URL`: OpenViking endpoint for hierarchical RAG context.

No defaults are provided for these variables. Each must be configured at deployment time with environment-appropriate values. The `.env.example` file documents the expected format but contains no real credentials.

### Hard Constraints from Core Engineering System

All department modules inherit the following constraints from `AGENTS.md`. These are non-negotiable and apply to every container without exception:

- **GCP project**: `aissc-core-engine-self-dep` only. No other project.
- **Region**: `us-central1` only. No other region.
- **Branch**: `dev` on `Tizzle716/core-engineering-system` only. No other branch.
- **Sizing**: `cpu=1`, `memory=512Mi`, `min_instances=0`, `max_instances=1`. This fits the GCP free tier. On quota errors, drop to `256Mi`. Never exceed these limits.
- **Authentication**: No `allUsers` invoker binding. Internal ingress only. Service account `core-engine-worker@aissc-core-engine-self-dep.iam.gserviceaccount.com` with least-privilege roles: `roles/run.invoker`, `roles/secretmanager.secretAccessor`, `roles/logging.logWriter`, `roles/iam.serviceAccountTokenCreator`. Never `roles/owner` or `roles/editor`.
- **Secrets**: Never in logs. Never in commits. Managed through Infisical or Secret Manager. `.gitignore` blocks `.env*`, `*.key`, `*.pem`, `service-account.json`.
- **Non-root user**: Every Dockerfile runs as `coreengine`. Root execution is prohibited.

---

*End of Master Operational Directive ORD-001. This document supersedes all prior verbal or informal deployment guidance. Amendments require an updated directive revision with explicit authorization.*
