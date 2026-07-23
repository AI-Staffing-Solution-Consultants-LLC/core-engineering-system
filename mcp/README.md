# MCP Tool Registry (Repo-Local)

This directory holds **repo-local** MCP tool definitions for the
`core-engineering-system`. It is **not** a system-wide registry and is
**not** registered with any external MCP server.

## Layout

```
mcp/
├── README.md                       # this file
└── tools/
    └── agency-agents-factory.json  # NEXUS-Sprint team-spawn tool
```

Each `mcp/tools/*.json` file is a self-contained tool spec consumed by
the Atlas orchestrator and its subagents. Adding a new tool means
dropping a new JSON file in `mcp/tools/` — no daemon restart, no
network call, no system config edit.

## Expected Callers

| Caller | Role |
|---|---|
| **Atlas orchestrator** | Reads `mcp/tools/*.json` to discover available tools and dispatches calls to the appropriate backend. |
| **Subagents** (verification, security, code-quality) | May invoke tools directly when the orchestrator delegates a task. |
| **agency-agents daemon** (`agency-agents-daemon:8082`) | Receives `agency-agents-factory` calls and spawns the requested verification team. |

The registry is **read-only at runtime** — callers never mutate
`mcp/tools/*.json` files.

## Security Contract

Every tool spec in this registry MUST satisfy the following contract.
This mirrors the Constitutional AI guarantees enforced by Track A and
Track B in the core-engineering-system.

1. **Isolated execution.** Each spawned team runs in its own
   per-team docker compose namespace. No shared network namespace,
   no shared PID namespace, no shared filesystem outside the
   explicitly mounted volumes. Teams are fully isolated from each
   other and from the host.
2. **Ephemeral ledger.** `/var/ledger` is mounted as **tmpfs** inside
   each team container. The ledger is destroyed when the team
   container exits — there is no persistent on-host ledger written
   by verification teams.
3. **Non-root user.** Every container runs as a dedicated
   non-root user (UID ≥ 1000). No `USER root` in any Dockerfile
   referenced by a tool spec.
4. **No public ingress.** No `allUsers` invoker binding on any
   Cloud Run service spawned by a tool. Internal-only ingress
   (`INGRESS_TRAFFIC_INTERNAL_ONLY`) is mandatory.
5. **Allowlist subset.** Any shell command a team executes MUST be
   a subset of `policy/tool-allowlist.txt` in the parent repo.
   Tools that require commands outside the allowlist MUST be
   rejected at spec-validation time.
6. **Repo-local registration only.** Tool specs in `mcp/tools/` are
   consumed by repo-local callers. They are **not** registered with
   any system-wide MCP registry (`~/.config/mcp/`, `~/.opencode/`,
   `~/.claude/`, `~/.codex/`) without explicit human approval.

## Adding a New Tool

1. Create `mcp/tools/<tool-name>.json` with the required schema
   (`name`, `version`, `description`, `inputs`, `outputs`,
   `backends`, `daemon`, `isolation_contract`).
2. Validate the JSON parses and contains the required keys.
3. Update this README's **Expected Callers** table if a new
   backend or daemon is introduced.
4. Confirm the new tool's `isolation_contract` satisfies all six
   items in the **Security Contract** above.

## What This Registry Is NOT

- It is **not** a substitute for `policy/tool-allowlist.txt`. The
  allowlist governs what shell commands may run; this registry
  governs what tools may be invoked.
- It is **not** a deployment manifest. Tool specs describe
  capabilities, not infrastructure. Cloud Run / docker compose
  deployment is handled by `terraform/` and `docker-compose.yml`.
- It is **not** auto-registered. Adding a JSON file here does not
  publish the tool to any external system.
