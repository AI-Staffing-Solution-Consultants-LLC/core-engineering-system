# OpenClaw Business Module — Department Roster

## Overview

The OpenClaw Business Module operates as a 12-department enterprise composed entirely of specialized AI agents. Each department is a self-contained operational unit with a defined roster of agents, explicit dependencies on other departments, and documented communication channels. Departments are organized into four sequential deployment phases, from foundation infrastructure (Phase 1) through intelligence and governance (Phase 2), revenue and innovation (Phase 3), to customer-facing operations (Phase 4).

Departments communicate via the Hermes message bus, with each department publishing to and subscribing from specific named queues. Agent assignments are drawn from the available skill definitions in `.agents/skills/`, and each agent exists in exactly one department. The governance hub (Department 06, Executive Strategy PMO) receives reports from every department and issues directives across the entire enterprise.

### Phase Deployment Order

| Phase | Departments | Description |
|-------|-------------|-------------|
| Phase 1 | 01, 02, 03 | Foundation — infrastructure, software, and QA |
| Phase 2 | 04, 05, 06 | Intelligence — AI/data, security, and executive governance |
| Phase 3 | 07, 08, 09, 10 | Revenue — product innovation, sales, growth, and brand |
| Phase 4 | 11, 12 | Operations — customer success and back-office |

---

## 01-infrastructure-devops-sre

**Phase:** 1 — Foundation

**Description:** Foundation infrastructure team managing CI/CD pipelines, cloud operations, site reliability, networking, and database administration across the enterprise.

**Agents:**
- `devops-automator` — Infrastructure automation, CI/CD pipeline development, and cloud operations
- `sre-site-reliability-engineer` — SLOs, error budgets, observability, chaos engineering, and toil reduction
- `ci-cd-specialist` — GitHub Actions, GitLab CI, and automated deployment pipelines
- `finops-engineer` — Cloud cost allocation, tagging, rightsizing, and commitment planning
- `network-engineer` — Routing, switching, firewalling, and troubleshooting across Cisco, Juniper, and Palo Alto
- `engineering-database-administrator` — Schema migrations, indexing, and performance tuning

**Dependencies:** None — foundation layer; all other departments depend on this one.

**Communicates with:**
- 02-software-engineering-architecture (provides infrastructure for software systems)
- 04-ai-data-multi-agent (hosts compute and storage for AI/ML workloads)
- 05-security-privacy-compliance (collaborates on network security and access controls)
- 12-finance-legal-hr-operations (reports cloud spend and infrastructure costs)

---

## 02-software-engineering-architecture

**Phase:** 1 — Foundation

**Description:** Software architecture and engineering team responsible for system design, backend architecture, code quality, git workflows, and rapid prototyping standards.

**Agents:**
- `software-architect` — System design, domain-driven design, and architectural patterns
- `backend-architect` — Scalable systems, database architecture, API development, and cloud infrastructure
- `code-reviewer` — Constructive feedback focused on correctness, maintainability, security, and performance
- `git-workflow-master` — Branching strategies, conventional commits, rebasing, and worktrees
- `minimal-change-engineer` — Minimum-viable diffs with strict scope discipline
- `rapid-prototyper` — Ultra-fast proof-of-concept and MVP creation
- `senior-developer` — Laravel/Livewire/FluxUI, advanced CSS, and Three.js integration

**Dependencies:** None — foundation layer.

**Communicates with:**
- 01-infrastructure-devops-sre (deploys to infrastructure managed by department 01)
- 03-quality-assurance-testing (hands off builds for testing and receives quality reports)
- 04-ai-data-multi-agent (integrates AI/ML services into software systems)
- 07-product-research-innovation (receives product requirements and design specifications)

---

## 03-quality-assurance-testing

**Phase:** 1 — Foundation

**Description:** Quality assurance and testing team handling integration testing, performance profiling, incident response, and IT service management.

**Agents:**
- `qa-automation-engineer` — Integration tests and end-to-end regression suites
- `performance-engineer` — Load testing, profiling, and memory leak analysis
- `code-reviewer` — Constructive feedback focused on correctness, maintainability, security, and performance
- `incident-response-commander` — Structured incident management, post-mortems, and SLO tracking
- `it-service-manager` — ITIL 4 service catalog, change control, and SLA governance

**Dependencies:** None — foundation layer.

**Communicates with:**
- 02-software-engineering-architecture (receives builds, returns test results and quality reports)
- 04-ai-data-multi-agent (validates AI/ML model performance and data pipeline integrity)
- 05-security-privacy-compliance (collaborates on security testing and compliance audits)

---

## 04-ai-data-multi-agent

**Phase:** 2 — Intelligence

**Description:** AI, ML, data engineering, and multi-agent systems architecture — the intelligence core of the enterprise.

**Agents:**
- `ai-engineer` — ML model development, deployment, and integration into production systems
- `multi-agent-systems-architect` — Agent topology selection, context management, inter-agent trust, and failure recovery
- `data-engineer` — ETL/ELT pipelines, Apache Spark, dbt, streaming systems, and data platforms
- `ml-engineer` — Model training, fine-tuning, and inference latency optimization
- `vector-store-manager` — Vector index optimization, RAG retrieval quality, and embeddings management
- `prompt-engineer` — Crafting, testing, and optimizing prompts for production-grade AI behavior
- `ai-data-remediation-engineer` — Self-healing data pipelines with air-gapped SLMs and semantic clustering

**Dependencies:**
- 01-infrastructure-devops-sre (requires compute, storage, and networking)
- 02-software-engineering-architecture (requires API and service integration patterns)

**Communicates with:**
- 01-infrastructure-devops-sre (reports resource utilization and scaling needs)
- 02-software-engineering-architecture (provides AI/ML APIs and data services)
- 03-quality-assurance-testing (provides models for validation and receives quality metrics)
- 05-security-privacy-compliance (collaborates on AI governance and data privacy)
- 07-product-research-innovation (provides AI capabilities for product features)
- 09-search-growth-paid-media (provides embedding infrastructure and retrieval pipelines)

---

## 05-security-privacy-compliance

**Phase:** 2 — Intelligence

**Description:** Security, identity, accessibility compliance, and privacy — the enterprise security perimeter.

**Agents:**
- `identity-access-engineer` — OAuth 2.0/OIDC, enterprise SSO, passkeys/WebAuthn, and RBAC/ABAC
- `section-508-accessibility-specialist` — WCAG 2.1 AA compliance, screen reader testing, and VPAT authoring
- `it-service-manager` — ITIL 4 service catalog, change control, and SLA governance
- `network-engineer` — Routing, switching, firewalling, and troubleshooting
- `payments-billing-engineer` — PCI scope reduction and secure payment flow design

**Dependencies:**
- 01-infrastructure-devops-sre (requires network access and infrastructure security controls)

**Communicates with:**
- 01-infrastructure-devops-sre (enforces security policies on infrastructure)
- 03-quality-assurance-testing (collaborates on security testing and compliance verification)
- 06-executive-strategy-pmo (reports security posture and compliance status)
- 11-customer-success-support (provides security guidance for customer-facing operations)
- 12-finance-legal-hr-operations (coordinates on legal compliance and financial security)

---

## 06-executive-strategy-pmo

**Phase:** 2 — Intelligence

**Description:** Executive strategy, project management, resource allocation, and business product ownership — the governance hub of the enterprise.

**Agents:**
- `business-strategist` — Competitive analysis, market entry strategy, and growth planning
- `business-project-manager` — Sprint velocity tracking, blocker management, and project timelines
- `business-resource-allocator` — Developer bandwidth management, task assignment, and priority resolution
- `business-product-owner` — Technical output validation against business roadmap and feature requirements
- `business-finops-analyst` — Cloud spend analysis, utilization forecasting, and cost-cutting recommendations

**Dependencies:** None — governance layer; operates standalone as the command-and-control hub.

**Communicates with:** ALL departments — receives status reports, metrics, and escalations from every department; issues directives, priorities, and resource allocations across the entire enterprise.

---

## 07-product-research-innovation

**Phase:** 3 — Revenue

**Description:** Product management, UX research, rapid prototyping, interaction design, and UX architecture — the innovation engine.

**Agents:**
- `business-product-owner` — Technical output validation against business roadmap and feature requirements
- `ux-researcher` — User behavior analysis, usability testing, and data-driven design insights
- `rapid-prototyper` — Ultra-fast proof-of-concept and MVP creation
- `design-interaction-designer` — Micro-interactions, state transitions, and user flow ergonomics
- `design-ux-architect` — Technical architecture for UX, CSS systems, and implementation guidance

**Dependencies:**
- 02-software-engineering-architecture (requires engineering feasibility assessments)
- 04-ai-data-multi-agent (requires AI/ML capabilities for product features)

**Communicates with:**
- 02-software-engineering-architecture (delivers product specs and design handoffs)
- 04-ai-data-multi-agent (specifies AI feature requirements)
- 06-executive-strategy-pmo (reports product roadmap progress and innovation metrics)
- 08-sales-revenue-operations (provides product capabilities for sales enablement)
- 10-marketing-content-brand (delivers product positioning and UX specifications)

---

## 08-sales-revenue-operations

**Phase:** 3 — Revenue

**Description:** Sales strategy, payments/billing, CMS development, and email intelligence — the revenue engine.

**Agents:**
- `payments-billing-engineer` — PSP integrations, idempotent payment flows, webhook processing, and subscription billing
- `business-strategist` — Competitive analysis, market entry strategy, and growth planning
- `cms-developer` — Drupal and WordPress theme development, custom plugins, and content architecture
- `email-intelligence-engineer` — Extracting structured, reasoning-ready data from raw email threads

**Dependencies:**
- 01-infrastructure-devops-sre (requires production infrastructure for revenue systems)
- 05-security-privacy-compliance (requires PCI compliance and secure payment handling)

**Communicates with:**
- 06-executive-strategy-pmo (reports revenue metrics and sales pipeline)
- 07-product-research-innovation (provides customer feedback for product development)
- 09-search-growth-paid-media (coordinates on paid acquisition and conversion optimization)
- 10-marketing-content-brand (aligns on campaign execution and lead generation)
- 11-customer-success-support (hands off closed deals for onboarding)
- 12-finance-legal-hr-operations (reports revenue and processes payments reconciliation)

---

## 09-search-growth-paid-media

**Phase:** 3 — Revenue

**Description:** Search relevance, vector store management, and data engineering for growth and paid media optimization.

**Agents:**
- `search-relevance-engineer` — Elasticsearch/OpenSearch index design, BM25 tuning, and hybrid retrieval
- `vector-store-manager` — Vector index optimization, RAG retrieval quality, and embeddings management
- `data-engineer` — ETL/ELT pipelines, Apache Spark, dbt, streaming systems, and data platforms

**Dependencies:**
- 01-infrastructure-devops-sre (requires compute and storage for search and analytics workloads)
- 04-ai-data-multi-agent (requires embedding models and retrieval infrastructure)

**Communicates with:**
- 04-ai-data-multi-agent (coordinates on embedding pipelines and retrieval quality)
- 06-executive-strategy-pmo (reports growth metrics and acquisition costs)
- 08-sales-revenue-operations (provides lead scoring and conversion data)
- 10-marketing-content-brand (collaborates on SEO strategy and content optimization)

---

## 10-marketing-content-brand

**Phase:** 3 — Revenue

**Description:** Brand strategy, visual storytelling, UI design, technical writing, frontend development, and CMS performance — the brand and content engine.

**Agents:**
- `brand-guardian` — Brand identity development, consistency maintenance, and strategic positioning
- `visual-storyteller` — Visual narratives, multimedia content, and brand storytelling through design
- `ui-designer` — Visual design systems, component libraries, and pixel-perfect interface creation
- `technical-writer` — Developer documentation, API references, README files, and tutorials
- `frontend-developer` — Modern web technologies, React/Vue/Angular, UI implementation, and performance optimization
- `wordpress-performance-engineer` — Core Web Vitals, object caching, page caching, and CDN integration for WordPress
- `drupal-performance-engineer` — Core Web Vitals, render caching, BigPipe, and Views optimization for Drupal

**Dependencies:**
- 01-infrastructure-devops-sre (requires hosting and CDN infrastructure)
- 07-product-research-innovation (requires brand guidelines and UX specifications)

**Communicates with:**
- 06-executive-strategy-pmo (reports brand performance and content engagement metrics)
- 07-product-research-innovation (receives product positioning and visual design direction)
- 08-sales-revenue-operations (collaborates on campaign assets and lead generation content)
- 09-search-growth-paid-media (collaborates on SEO content and paid media creative)

---

## 11-customer-success-support

**Phase:** 4 — Operations

**Description:** Customer support, incident management, IT service management, Feishu/WeChat integrations, email intelligence, and voice AI — the customer-facing operations.

**Agents:**
- `incident-response-commander` — Structured incident management, post-mortems, and SLO tracking
- `it-service-manager` — ITIL 4 service catalog, change control, and SLA governance
- `feishu-integration-developer` — Feishu bots, mini programs, approval workflows, and interactive message cards
- `wechat-mini-program-developer` — WeChat mini program development, payment integration, and subscription messaging
- `email-intelligence-engineer` — Extracting structured, reasoning-ready data from raw email threads
- `voice-ai-integration-engineer` — Speech transcription pipelines, subtitle generation, and speaker diarization

**Dependencies:**
- 01-infrastructure-devops-sre (requires production infrastructure for customer-facing services)
- 05-security-privacy-compliance (requires data privacy and access control policies)

**Communicates with:**
- 05-security-privacy-compliance (escalates security incidents and compliance issues)
- 06-executive-strategy-pmo (reports customer satisfaction metrics and support SLAs)
- 08-sales-revenue-operations (receives closed deals for customer onboarding)
- 12-finance-legal-hr-operations (coordinates on billing disputes and service credits)

---

## 12-finance-legal-hr-operations

**Phase:** 4 — Operations

**Description:** Cloud financial operations, payments reconciliation, IT service governance, legal compliance checking, and finance tracking — the back-office operations.

**Agents:**
- `business-finops-analyst` — Cloud spend analysis, utilization forecasting, and cost-cutting recommendations
- `payments-billing-engineer` — PSP integrations, idempotent payment flows, and financial reconciliation
- `it-service-manager` — ITIL 4 service catalog, change control, and SLA governance
- `support-legal-compliance-checker` — Regulatory compliance verification and legal risk assessment
- `support-finance-tracker` — Financial tracking, budget monitoring, and expense reconciliation

**Dependencies:**
- 01-infrastructure-devops-sre (requires cost data and infrastructure usage reports)
- 05-security-privacy-compliance (requires compliance status and legal frameworks)
- 06-executive-strategy-pmo (requires budget directives and strategic priorities)

**Communicates with:**
- 01-infrastructure-devops-sre (receives cloud spend and infrastructure cost reports)
- 05-security-privacy-compliance (coordinates on regulatory compliance auditing)
- 06-executive-strategy-pmo (reports financial performance and legal risk assessments)
- 08-sales-revenue-operations (processes revenue reconciliation and payments settlement)
- 11-customer-success-support (processes billing adjustments and service credits)

---

## Communication Matrix

The table below maps which departments send messages to (rows) and receive messages from (columns) each other. An `X` indicates a documented communication channel. Department 06 (Executive Strategy PMO) communicates with all departments and is therefore marked in every applicable cell.

| Dept | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 |
|------|----|----|----|----|----|----|----|----|----|----|----|----|
| **01** inf-devops-sre | — | X |   | X | X | X |   |   |   |   |   | X |
| **02** sw-eng-arch | X | — | X | X |   | X | X |   |   |   |   |   |
| **03** qa-testing |   | X | — | X | X | X |   |   |   |   |   |   |
| **04** ai-data | X | X | X | — | X | X | X |   | X |   |   |   |
| **05** security | X |   | X | X | — | X |   |   |   |   | X | X |
| **06** exec-strategy | X | X | X | X | X | — | X | X | X | X | X | X |
| **07** product |   | X |   | X |   | X | — | X |   | X |   |   |
| **08** sales-revenue |   |   |   |   |   | X | X | — | X | X | X | X |
| **09** search-growth |   |   |   | X |   | X |   | X | — | X |   |   |
| **10** marketing |   |   |   |   |   | X | X | X | X | — |   |   |
| **11** customer-success |   |   |   |   | X | X |   | X |   |   | — | X |
| **12** finance-legal | X |   |   |   | X | X |   | X |   |   | X | — |

**Legend:**
- `X` — Documented communication channel (publisher or subscriber on Hermes bus)
- `—` — Same department (diagonal)
- Blank cell — No direct communication channel documented

---

## Phase Summary

| Phase | Department IDs | Department Count | Total Agents |
|-------|---------------|-----------------|--------------|
| Phase 1 (Foundation) | 01, 02, 03 | 3 | 18 |
| Phase 2 (Intelligence) | 04, 05, 06 | 3 | 17 |
| Phase 3 (Revenue) | 07, 08, 09, 10 | 4 | 19 |
| Phase 4 (Operations) | 11, 12 | 2 | 11 |
| **Total** | **All 12 departments** | **12** | **65** |

### Agent Count by Department

| Department | Slug | Phase | Agent Count |
|------------|------|-------|-------------|
| Infrastructure, DevOps, SRE | 01-infrastructure-devops-sre | Phase 1 | 6 |
| Software Engineering & Architecture | 02-software-engineering-architecture | Phase 1 | 7 |
| Quality Assurance & Testing | 03-quality-assurance-testing | Phase 1 | 5 |
| AI, Data & Multi-Agent | 04-ai-data-multi-agent | Phase 2 | 7 |
| Security, Privacy & Compliance | 05-security-privacy-compliance | Phase 2 | 5 |
| Executive Strategy & PMO | 06-executive-strategy-pmo | Phase 2 | 5 |
| Product, Research & Innovation | 07-product-research-innovation | Phase 3 | 5 |
| Sales & Revenue Operations | 08-sales-revenue-operations | Phase 3 | 4 |
| Search, Growth & Paid Media | 09-search-growth-paid-media | Phase 3 | 3 |
| Marketing, Content & Brand | 10-marketing-content-brand | Phase 3 | 7 |
| Customer Success & Support | 11-customer-success-support | Phase 4 | 6 |
| Finance, Legal & HR Operations | 12-finance-legal-hr-operations | Phase 4 | 5 |

---

## Enterprise Architecture Diagram

```
                             ┌──────────────────────────────────────┐
                             │       06-executive-strategy-pmo       │
                             │   (Governance Hub — communicates      │
                             │        with ALL departments)          │
                             └────┬────┬────┬────┬────┬────┬────┬────┘
                                  │    │    │    │    │    │    │
         ┌────────────────────────┘    │    │    │    │    │    └────────────────────────┐
         │                             │    │    │    │    │                             │
         ▼                             ▼    │    ▼    │    ▼                             ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ 07-product-research │   │ 08-sales-revenue    │   │ 09-search-growth    │   │ 10-marketing-content│
│ -innovation (Phase 3)│   │ -operations (Phase 3)│  │ -paid-media (Phase 3)│   │ -brand (Phase 3)     │
└──────────┬──────────┘   └──────────┬──────────┘   └──────────┬──────────┘   └──────────┬──────────┘
           │                         │                         │                         │
           └─────────────────────────┼─────────────────────────┼─────────────────────────┘
                                     │                         │
                            ┌────────┴────────┐       ┌────────┴────────┐
                            │ 04-ai-data      │       │ 05-security     │
                            │ multi-agent     │       │ privacy-comp    │
                            │ (Phase 2)       │       │ (Phase 2)       │
                            └────────┬────────┘       └────────┬────────┘
                                     │                         │
                            ┌────────┴────────┐                │
                            │                 │                │
                            ▼                 ▼                ▼
                     ┌──────────┐    ┌──────────┐    ┌──────────┐
                     │ 02-sw-eng│    │ 03-qa    │    │ 01-infra │
                     │ -arch    │    │ -testing │    │ -devops  │
                     │ (Phase 1)│    │ (Phase 1)│    │ (Phase 1)│
                     └──────────┘    └──────────┘    └────┬─────┘
                                                          │
                                            ┌─────────────┼─────────────┐
                                            │             │             │
                                            ▼             ▼             ▼
                                     ┌──────────┐  ┌──────────┐  ┌──────────┐
                                     │ 11-cust  │  │ 12-fin   │  │ 01-infra │
                                     │ -success │  │ -legal-hr│  │ (to all) │
                                     │ (Phase 4)│  │ (Phase 4)│  │          │
                                     └──────────┘  └──────────┘  └──────────┘
```

**Reading the diagram:**
- Phase 1 departments (01, 02, 03) form the foundation — all other layers depend on them.
- Phase 2 departments (04, 05, 06) sit atop the foundation, adding intelligence and governance.
- Phase 3 departments (07, 08, 09, 10) depend on Phase 1 infrastructure and Phase 2 intelligence services.
- Phase 4 departments (11, 12) are customer-facing and back-office operations that depend on the full stack.
- Department 06 (Executive Strategy PMO) spans all layers as the governance hub.
