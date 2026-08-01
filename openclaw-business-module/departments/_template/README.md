# <DEPARTMENT_NAME> — OpenClaw Business Module

**Department Slug:** `<SLUG>`
**Phase:** <PHASE_NUMBER> — <PHASE_DESCRIPTION>
**Port:** `81<NN>`
**Model:** `opencode-go/deepseek-v4-pro`

## Description

<ONE_PARAGRAPH_DEPARTMENT_DESCRIPTION>

## Agent Roster

Agents are defined in `agents.json`. Each agent references a skill definition from the canonical [Agent ID → skill_ref Path Mapping Table](../ops_architecture.md#11-agent-id--skill_ref-path-mapping-table).

| Agent ID | skill_ref | Role |
|---|---|---|
| `<PLACEHOLDER_AGENT_ID>` | `<PLACEHOLDER_SKILL_REF>` | `<one-line role>` |

## Dependencies

- **01-infrastructure-devops-sre** — compute, storage, networking infrastructure
- **06-executive-strategy-pmo** — governance directives and resource allocation

## Communication Map

| Publishes to | Subscribes from |
|---|---|
| `queue.<SLUG>` | `<LIST_OF_QUEUE_NAMES>` |

Messages are exchanged via the Hermes message bus (AMQP). Department 06 (Executive Strategy PMO) receives reports from and issues directives to all departments.

## Configuration

All configuration is supplied via environment variables. Copy `.env.example` to `.env` and replace placeholder values before deployment.

| Variable | Description | Example |
|---|---|---|
| `DEPARTMENT_NAME` | Human-readable department name | `<Name>` |
| `DEPARTMENT_SLUG` | URL-safe department identifier | `<slug>` |
| `PORT` | Container listen port | `81<NN>` |
| `HERMES_QUEUE_URL` | Hermes AMQP broker URL | `amqp://hermes:5672` |
| `AGENTOS_CONFIG_PATH` | Path to agent roster JSON | `/app/agents.json` |
| `PAPERCLIP_CONFIG_PATH` | Path to EIM workflow JSON | `/app/paperclip-config.json` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `OPENVIKING_URL` | OpenViking RAG mount URL | `viking://openviking:9000` |

## Protocols

| Protocol | File | Description |
|---|---|---|
| Protocol A | `redis-client.json` | Redis ping gate before container ONLINE |
| Protocol B | `viking-rag.json` | Agents connect to OpenViking by default for hierarchical RAG context |

## Build & Run

```bash
# Build the image
docker build -t <SLUG> .

# Run with env file
docker run --env-file .env -p 81<NN>:81<NN> <SLUG>
```

## Verification

```bash
# Health check
curl -fs http://localhost:81<NN>/healthz
# Expected: {"department":"<Name>","slug":"<slug>","status":"ok"}

# Validate JSON configs
python -c "import json; json.load(open('agents.json'))"
python -c "import json; json.load(open('paperclip-config.json'))"
python -c "import json; json.load(open('hermes-gateway.json'))"
python -c "import json; json.load(open('redis-client.json'))"
python -c "import json; json.load(open('viking-rag.json'))"
```
