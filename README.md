# Core Engineering System

Two Cloud Run services implementing the **C-P-A (Context-Planning-Action) cognitive loop** defined in AIdevops.txt. This system is the operational brain for agentic DevOps — it transforms an LLM from a text generator into a decision engine.

Architecture: **Horizon 1/2 boundary** (Augmented Operator → Agent Swarms). Human-on-the-loop; the agent drives the plan, the human approves critical actions.

---

## The C-P-A Transform

```
                    ┌──────────────────────────┐
                    │     Operator (Human)      │
                    │  "Why is latency high?"   │
                    └────────────┬─────────────┘
                                 │ query
                                 ▼
              ┌──────────────────────────────────┐
              │        Track A: Control Loop     │
              │                                  │
              │  Context: RAG corpus search      │
              │           → finds similar past   │
              │             incidents            │
              │                                  │
              │  Planning: ReAct loop            │
              │   1. Form hypothesis             │
              │   2. Generate action plan        │
              │   3. Emit tool calls             │
              │                                  │
              │  Every step → tamper-evident     │
              │  ledger entry                    │
              └──────────────┬───────────────────┘
                             │ action request
                             ▼
              ┌──────────────────────────────────┐
              │      Track B: Actuator           │
              │                                  │
              │  Action: Constitutional AI gate  │
              │   1. Allowlist check             │
              │   2. Reasoning ref required      │
              │   3. No metacharacters           │
              │                                  │
              │  Sandboxed subprocess execution  │
              │  Result → back to Track A        │
              │                                  │
              │  Every execution → ledger entry  │
              └──────────────────────────────────┘
```

| C-P-A Layer | Track | Responsibility |
|---|---|---|
| **Context** | Track A | Loads RAG corpus, retrieves historical runbooks, forms situational awareness |
| **Planning** | Track A | ReAct loop: hypothesis → action plan → emit requests |
| **Action** | Track B | Allowlist validation → sandboxed execution → result return |
| **Perception** | Both | Track A ingests logs/metrics via RAG; Track B reads runtime sensor data |

---

## Project Structure

```
core-engineering-system/
├── docker-compose.yml          # Local dev: two containers + ledger volumes
├── .gitignore
├── README.md
├── track-a/
│   ├── Dockerfile              # python:3.12-slim, non-root user
│   ├── requirements.txt        # flask, gunicorn, requests
│   └── main.py                 # Control loop (Flask, port 8080)
├── track-b/
│   ├── Dockerfile              # python:3.12-slim, non-root user
│   ├── requirements.txt        # flask, gunicorn, requests
│   └── main.py                 # Actuator (Flask, port 8081)
├── terraform/
│   ├── provider.tf             # google provider, project, region
│   ├── project.tf              # API enablement
│   ├── iam.tf                  # Service account + least-privilege roles
│   ├── cloudrun.tf             # Two Cloud Run v2 services
│   ├── secrets.tf              # Secret Manager + per-secret IAM
│   ├── monitoring.tf           # Alerting policies (request_count, latency)
│   └── variables.tf            # Input variables
└── policy/
    ├── deny-destroy-prod.rego  # Block terraform destroy on prod
    ├── deny-broad-write.rego   # Reject Write("*") scope
    ├── require-namespace-scope.rego  # Remediation agents need namespace
    ├── log-reasoning-steps.rego      # Tool calls must reference reasoning
    └── tool-allowlist.txt      # Allowlisted CLI commands (one per line)
```

---

## Constitutional AI Enforcement

Every action passes through a **deterministic policy gate** before execution. The LLM's intent is irrelevant — the policy engine kills non-compliant commands hard.

### Enforcement Points

| Layer | Mechanism |
|---|---|
| **Infrastructure** | `--no-allow-unauthenticated` on both Cloud Run services. Only the service account can invoke. |
| **IAM** | Least-privilege roles: `roles/run.invoker`, `roles/secretmanager.secretAccessor`, `roles/logging.logWriter`. No `roles/owner`. |
| **Application** | Track B validates every tool call against `policy/tool-allowlist.txt` — exact match only, no wildcards , no metacharacters. |
| **Policy-as-Code** | 4 OPA/Rego rules in `policy/`. Evaluated before any action. |
| **Ledger** | Every reasoning step and every tool execution is written to a SHA-256 chained JSONL ledger. Tamper-evident. Replayable in post-mortem. |

### Tool Allowlist

Track B reads `policy/tool-allowlist.txt` at startup. Only commands on this list can be executed. No wildcards. No shell metacharacters. Track B refuses any tool call not matching a prefix in the list.

---

## Deployment

### Prerequisites

- `gcloud` CLI authenticated with `aissc-core-engine-self-dep` project access
- `gh` CLI authenticated with `Tizzle716` org access
- Docker installed for local testing

### 1. Local Dev (Docker Compose)

```bash
docker compose up --build
# Track A: http://localhost:8080
# Track B: http://localhost:8081
```

### 2. Cloud Run Deploy

```bash
PROJECT=aissc-core-engine-self-dep
REGION=us-central1

# Track A
gcloud run deploy track-a-control-loop \
    --source ./track-a \
    --region $REGION \
    --project $PROJECT \
    --no-allow-unauthenticated \
    --cpu=1 \
    --memory=512Mi \
    --min-instances=0 \
    --max-instances=1 \
    --service-account core-engine-worker@${PROJECT}.iam.gserviceaccount.com

# Track B
gcloud run deploy track-b-actuator \
    --source ./track-b \
    --region $REGION \
    --project $PROJECT \
    --no-allow-unauthenticated \
    --cpu=1 \
    --memory=512Mi \
    --min-instances=0 \
    --max-instances=1 \
    --service-account core-engine-worker@${PROJECT}.iam.gserviceaccount.com
```

If quota errors occur, reduce memory to `256Mi` and retry. Never exceed free tier limits.

### 3. Terraform (Infrastructure-as-Code)

```bash
cd terraform
terraform init
terraform validate
terraform plan   # review before apply
terraform apply
```

---

## Verification

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. GitHub repo exists ==="
gh repo view Tizzle716/core-engineering-system --json name

echo "=== 2. Cloud Run services deployed ==="
gcloud run services list --project=aissc-core-engine-self-dep --region=us-central1

echo "=== 3. Terraform validates ==="
terraform -chdir=terraform validate

echo "=== 4. Docker Compose parses ==="
docker compose config --quiet

echo "=== 5. Dev branch has the scaffold ==="
gh api repos/Tizzle716/core-engineering-system/branches/dev --jq '.name'
gh api repos/Tizzle716/core-engineering-system/contents/?ref=dev --jq '.[].name'

echo "=== 6. Policy directory is non-empty ==="
gh api repos/Tizzle716/core-engineering-system/contents/policy?ref=dev --jq '.[].name'

echo "=== ALL CHECKS PASSED ==="
```

---

## API Reference

### Track A (port 8080)

| Endpoint | Method | Description |
|---|---|---|
| `/healthz` | GET | Health check |
| `/plan` | POST | Submit query for ReAct planning. Body: `{"query": "Why is latency high?"}` |
| `/ledger` | GET | Retrieve tamper-evident ledger entries. Query: `?limit=50` |

### Track B (port 8081)

| Endpoint | Method | Description |
|---|---|---|
| `/healthz` | GET | Health check |
| `/execute` | POST | Execute an allowlisted tool. Body: `{"tool": "kubectl get pods", "args": [], "reasoning_log_ref": "hash..."}` |
| `/allowlist` | GET | View current tool allowlist |

---

## Constraints

- **Project**: `aissc-core-engine-self-dep` only. Do not deploy elsewhere.
- **Region**: `us-central1` only.
- **Branch**: `dev` on `Tizzle716/core-engineering-system` only.
- **Sizing**: `cpu=1, memory=512Mi, min_instances=0, max_instances=1` — fits GCP free tier.
- **Auth**: `--no-allow-unauthenticated` on both services. No public access.
- **Secrets**: Never echo tokens. Use Infisical for secret retrieval. Scrub logs before persisting.
