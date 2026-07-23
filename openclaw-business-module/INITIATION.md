# OpenClaw Maiden Mission — Initiation Protocol

**Status: PLACEHOLDER** — this protocol is not yet wired. All steps describe intent, not current behavior.

## Overview

The Initiation Protocol defines how the OpenClaw Maiden Mission is activated. When a human operator sends `/initiate-openclaw` via Telegram, Sheryl (the Memory & Context Agent) receives the command, validates that all prerequisite infrastructure is operational, and spawns a NEXUS-Sprint verification team via the agency-agents-factory daemon.

## Activation Flow

```
Human Operator
     │
     │  /initiate-openclaw
     ▼
┌─────────────────────┐
│  Telegram Bridge     │  :8088
│  (telegram-bridge/)  │
│                     │
│  Webhook receives   │
│  command, parses    │
│  chat_id + message  │
└─────────┬───────────┘
          │  POST /ingest {"command": "/initiate-openclaw", ...}
          ▼
┌─────────────────────┐
│  Sheryl              │  :8083
│  (executive-quartet/ │
│   sheryl/)           │
│                     │
│  1. Parse command   │
│  2. Validate infra  │──► Health probes to all dependencies
│  3. Build plan      │
│  4. Log to ledger   │
└─────────┬───────────┘
          │  POST /spawn-team
          ▼
┌─────────────────────┐
│  Agency-Agents       │  :8082
│  Daemon              │
│  (agency-agents/     │
│   daemon/)           │
│                     │
│  1. Create isolated  │
│     Docker namespace │
│  2. Spawn NEXUS-     │
│     Sprint team      │
│  3. Return team_id   │
└─────────┬───────────┘
          │  team_id + verification_plan
          ▼
┌─────────────────────┐
│  NEXUS-Sprint Team  │
│                     │
│  Verifies OpenClaw   │
│  module readiness,  │
│  reports back to    │
│  Sheryl via ledger   │
└─────────────────────┘
```

## Step 1: Command Reception (TBD)

Sheryl receives the command via the Telegram bridge webhook at `POST /ingest`. The payload format (TBD) will include:

```json
{
  "command": "/initiate-openclaw",
  "chat_id": "<telegram_chat_id>",
  "timestamp": "<ISO 8601>",
  "message_id": "<telegram_message_id>"
}
```

**Current state:** The Telegram bridge (`telegram-bridge/main.py`) routes messages to Sheryl at `/ingest`, but Sheryl's `main.py` does not yet expose an `/ingest` endpoint — it uses `/plan`. This gap must be resolved before activation.

## Step 2: Infrastructure Validation (TBD)

Sheryl probes all prerequisite components before proceeding:

| Component | Health Check | Expected Response | Status |
|---|---|---|---|
| Track A | `GET :8080/healthz` | `{"status": "ok", "service": "track-a-control-loop"}` | **TBD** |
| Track B | `GET :8081/healthz` | `{"status": "ok", "service": "track-b-actuator"}` | **TBD** |
| Agency-Agents Daemon | `GET :8082/healthz` | `{"status": "ok"}` | **TBD** |
| Tool Allowlist | `GET :8081/allowlist` | Non-empty list of allowlisted commands | **TBD** |
| RAG Corpus | `GET :8080/ledger?limit=1` | Functional control loop (proves RAG loaded) | **TBD** |
| Ledger Integrity | Chain hash continuity check across tracks | Sequential chain hashes verify | **TBD** |
| Cloudflare Edge Grid | `GET <worker-url>/healthz` | `{"status": "healthy", "bindings": {...}}` | **TBD** |
| EIM Milestones | All 5 EIM milestones confirmed operational | Per `openclaw-business-module/README.md` prerequisites | **TBD** |

If any component fails validation, Sheryl halts, logs the failure to the ledger with `type: "gate_denied"`, and responds to the Telegram chat with the specific failure reason.

## Step 3: Plan Construction (TBD)

Upon successful validation, Sheryl:

1. Queries the RAG corpus for relevant OpenClaw runbooks and business-module documentation
2. Queries MemoryPlugin for prior OpenClaw activation contexts
3. Constructs an action plan:
   - `team_size`: 4 (default for NEXUS-Sprint)
   - `module_request.name`: `"openclaw-business-module"`
   - `module_request.path`: `"/home/olly/core-engineering-system/openclaw-business-module/"`
   - `module_request.scope`: `"maiden-mission-activation"`
4. Writes the full reasoning chain to the SHA-256 tamper-evident ledger

## Step 4: NEXUS-Sprint Team Spawning (TBD)

Sheryl calls the agency-agents daemon:

```
POST :8082/spawn-team
Content-Type: application/json

{
  "module_request": {
    "name": "openclaw-business-module",
    "path": "/home/olly/core-engineering-system/openclaw-business-module/",
    "scope": "maiden-mission-activation"
  },
  "team_size": 4,
  "reasoning_log_ref": "<chain_hash_from_step_3>"
}
```

The daemon, per the `agency-agents-factory.json` isolation contract:

- Creates a per-team Docker Compose namespace (no shared network or PID namespace)
- Mounts `/var/ledger` as tmpfs (ephemeral, destroyed on exit)
- Runs containers as non-root user (UID ≥ 1000)
- Restricts shell commands to the subset in `policy/tool-allowlist.txt`
- Returns `team_id` and `verification_plan`

## Step 5: Response to Operator (TBD)

Sheryl responds to the Telegram chat:

```
OpenClaw Maiden Mission initiated.
  Team ID: <team_id>
  Ledger Ref: <chain_hash>
  Status: Verification team spawned. Awaiting results.
```

All subsequent NEXUS-Sprint team output is written to the ledger and retrievable via `GET :8080/ledger?limit=N`.

## Verification (Placeholder)

```bash
# When wired, the end-to-end test will look like:
curl -X POST http://localhost:8088/webhook \
  -H 'Content-Type: application/json' \
  -d '{"message": {"chat": {"id": 123}, "text": "/initiate-openclaw"}}'

# Expected: Sheryl returns team_id, ledger entries appear with type "maiden_mission_initiation"
```

**Current state:** This entire protocol is **TBD**. No code implements any of these steps. The flow above describes the *intended behavior* once infrastructure is wired.

## What This Is NOT

- ❌ Not a working implementation — every step is TBD
- ❌ Not an architecture design — that is Prometheus's future task
- ❌ Not a deployment manifest — no Dockerfiles, no wrangler.toml, no terraform
- ❌ No API contracts beyond the conceptual JSON payloads shown above
