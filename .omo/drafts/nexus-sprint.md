# NEXUS-Sprint Draft — Phase-5 LIVE flip

> **Mirror of `.omo/plans/nexus-sprint.md` (summary, not duplicate).** Reflects the Phase-5 LIVE flip: 4 waves, 11 checkpoints, 14 Must-NOT-Have items, 4 new gated tasks (8–11).

---

## TL;DR

- **Scope:** Phases 1, 3, 4 in-repo only. Phase 2 = paper design. **Phase 5 = LIVE** (config-first, install gated).
- **Deliverables:** `.test/`, `track-a/opa_eval.py`, `cloudbuild.yaml`, `agency-agents/` (populated), `mcp/` (incl. `agency-agents-factory`), `evidence/PHASE-{1..5}.md`.
- **Critical path:** Task 1 → Task 5 → Task 8 → Task 9 → Task 10 → Task 11 → F3 pause.

---

## Four Waves

### Wave 1 — Foundation (tasks 1–4)
1. Pytest harness + smoke tests (`.test/`)
2. Rego evaluator hook (`track-a/opa_eval.py`)
3. Runbook manifest stub (`.omo/evidence/runbook-manifest.md`)
4. **Draft mirror** (this file)

### Wave 2 — Cloud Build + Integrity Tests (tasks 5–7)
5. `cloudbuild.yaml` (path-aware, `--no-allow-unauthenticated`)
6. `tests/allowlist-mutation-test.py`
7. `tests/ledger-chain-test.py`

### Wave 3 — Phase-5 LIVE (tasks 8–11, ALL gated)
8. **Install `@agency-agents/cli`** — local `agency-agents/node_modules/` (default). Global `-g` is `[HUMAN-APPROVAL-REQUIRED]` checkpoint #8.
9. **MCP tool definition `agency-agents-factory`** — `mcp/tools/agency-agents-factory.json` + `mcp/README.md`. Repo-local only. System-wide `mcp register ... --system` is checkpoint #9.
10. **Antigravity IDE + Taskmaster.ai codeboard-generator combo** — config-only (`live: false` flag). Live API call is checkpoint #10.
11. **`agency-agents` daemon skeleton** — `daemon/main.py`, `daemon/Dockerfile`, `daemon/teams.json`. Port-bind (`docker compose up`) is checkpoint #11.

### Wave FINAL — Human gates + closeout (F1–F4)
- F1. Emit `evidence/PHASE-{1..5}.md` stub pointers (now includes LIVE Phase-5 evidence)
- F2. Diff summary report
- F3. **[HUMAN-APPROVAL-REQUIRED]** Pause — 11-item checklist
- F4. **[HUMAN-APPROVAL-REQUIRED]** Conditional deploy + push

---

## 11 Human-in-the-loop Checkpoints (7 prior + 4 new)

### Prior (1–7) — preserved verbatim
| # | Checkpoint | Command |
|---|---|---|
| 1 | `git commit` on local `dev` | `git -C /home/olly/core-engineering-system commit -m "..."` |
| 2 | `git push origin dev` | `git push origin dev` |
| 3 | `terraform plan` | `terraform -chdir=terraform plan` |
| 4 | `terraform apply` | `terraform -chdir=terraform apply` |
| 5 | `gcloud builds submit` / `gcloud run deploy` | `gcloud builds submit ...` |
| 6 | `wrangler deploy` / KV / queues | `wrangler deploy` |
| 7 | Infisical Universal Auth handshake | `curl https://app.infisical.com/api/v1/auth/...` |

### New (8–11) — Phase-5 LIVE extensions
| # | Checkpoint | Command |
|---|---|---|
| 8 | `@agency-agents/cli` global install | `npm install -g @agency-agents/cli` |
| 9 | MCP system-wide registry edit | `mcp register agency-agents-factory --system` |
| 10 | Antigravity / Taskmaster live API call | `curl https://api.antigravity.dev/...` / `curl https://api.taskmaster.ai/...` |
| 11 | `agency-agents` daemon `docker compose up` | `docker compose up agency-agents-daemon` (binds 8082) |

---

## 14 Must-NOT-Have Items (Hard Guardrails)

| # | Forbidden action | Why |
|---|---|---|
| 1 | Read/list/stat/dump/grep any path under `/home/olly/.gemini/`, `/home/olly/.google-cloud-sdk/`, `/home/olly/Infisical*`, `/home/olly/.netrc`, `/home/olly/.aws/`, or any `*.key`/`*.pem`/`service-account.json`/`*.tfstate` outside `terraform/`. | User excluded source credential directories. |
| 2 | Run `gcloud secrets versions add`, `gcloud secrets create`, `terraform apply`, `terraform import` against `aissc-core-engine-self-dep` without per-step human approval. | Live state mutation crosses repo boundaries. |
| 3 | Call `curl https://api.infisical.com/...`, Cloudflare API, or any Universal Auth endpoint. | Credentials + remote identity handshake. |
| 4 | `git push` (any form) to `Tizzle716/core-engineering-system` without explicit human-in-the-loop approval. | Remote side-effects, hard to roll back. |
| 5 | Run `wrangler deploy`, `wrangler kv:namespace create`, `wrangler queues create`, or any `cloudflared` tunnel install. | Phase 2 live provisioning. |
| 6 | Create directories under `/CORE-Modules/`, `/Inference-Tokenomics/`, `/EIM-Core-Modules/`, or any `/AISSC_Cloud_Workspace/` path. | Those paths do not exist in this repo. |
| 7 | Add `requirements.txt` entries for `cloudflare`, `infisical-python`, `requests-gcp`, `google-cloud-aiplatform`, or any IAM-touching SDK without approval. | Hidden scope. |
| 8 | Edit `terraform/iam.tf` to grant `roles/owner` or `roles/editor` to any principal. | AGENTS.md hard constraint. |
| 9 | Edit `terraform/cloudrun.tf` or `track-a/Dockerfile` to remove the `non-root` user. | Defense-in-depth. |
| 10 | Touch the live ledger file (`/var/ledger/ledger-*.jsonl`) by hand — read-only via `/ledger` HTTP API only. | Tamper-evident chain must remain auditable. |
| **11** | `npm install -g @agency-agents/cli` or any system-wide install (`-g`, `--global`, `pip install --user`, `brew install`, `apt install`). **Local `npm install` into `agency-agents/node_modules/` is allowed by default.** | System installs touch host filesystem. |
| **12** | Live HTTP call to Antigravity IDE API, Taskmaster.ai API, or any third-party codeboard-generator service from any in-repo code. **Config/spec files referencing them are allowed.** | External API calls require credentials. |
| **13** | Spawn `agency-agents` daemon child process, port-bind a new listener (port 8082 or other), or attach a network namespace within `docker compose` **without explicit human approval** of the daemon skeleton. | Container-level side effects. |
| **14** | Auto-register `agency-agents-factory` in any system-wide MCP config (`~/.config/mcp/`, `~/.mcp/registry`, `~/.opencode/`, `~/.claude/`, `~/.codex/`). **Repo-local `mcp/tools/` is allowed.** | System-wide config touches user shell environment. |

---

## Phase-5 LIVE Tasks — Detail

### Task 8 — Install `@agency-agents/cli`
- Add `agency-agents/package.json` declaring `@agency-agents/cli` as **local devDependency** (NOT global).
- `npm install --no-audit --no-fund` from `agency-agents/`.
- Verify `agency-agents/node_modules/.bin/agency-agents --version` exits 0.
- **Default:** local install only. **Global `-g` requires checkpoint #8 approval.**

### Task 9 — MCP tool definition `agency-agents-factory`
- Create `mcp/tools/agency-agents-factory.json` — JSON spec with `name`, `version`, `description`, `inputs` (module_request, team_size), `outputs` (team_id, verification_plan), `backends` (antigravity-ide, taskmaster-ai), `daemon` (agency-agents-daemon:8082), `isolation_contract`.
- Add `mcp/README.md` describing registry layout + security contract.
- **Repo-local only.** System-wide `mcp register ... --system` is checkpoint #9.

### Task 10 — Antigravity IDE + Taskmaster.ai codeboard-generator combo
- Create `mcp/tools/codeboard-combo.json` with `live: false` flag (config-only).
- Add `mcp/tools/codeboard-combo.dryrun.py` — static skeleton, no network call.
- Add `TASKMASTER_API_URL` placeholder env var in `.env.example` (no real value).
- **Live API call deferred** until checkpoint #10 approval.

### Task 11 — `agency-agents` daemon skeleton
- `agency-agents/daemon/main.py` — Flask service, `/healthz` + `/teams/spawn` (port-bind **only when explicitly started**, default OFF).
- `agency-agents/daemon/Dockerfile` — `python:3.12-slim`, non-root user (same pattern as `track-a/Dockerfile`).
- `agency-agents/daemon/teams.json` — team isolation contract: tmpfs `/var/ledger`, non-root `coreengine`, no `allUsers` binding, allowlist subset per team.
- `docker-compose.yml` — **commented-out** `agency-agents-daemon` service skeleton (default OFF).
- **Port-bind (`docker compose up`) deferred** until checkpoint #11 approval.

---

## Verification (post-execution)

```bash
# Plan + draft + manifest present
wc -l .omo/plans/nexus-sprint.md .omo/drafts/nexus-sprint.md .omo/evidence/runbook-manifest.md

# Guardrails + new tools referenced
grep -c 'HUMAN-APPROVAL-REQUIRED' .omo/plans/nexus-sprint.md   # >= 11
grep -cE '@agency-agents|Antigravity|Taskmaster' .omo/plans/nexus-sprint.md  # > 0

# Local install verification (after Task 8)
test -x agency-agents/node_modules/.bin/agency-agents

# MCP tool definition parses (after Task 9)
python -c "import json; d=json.load(open('mcp/tools/agency-agents-factory.json')); print(d['name'])"

# Codeboard combo config-only (after Task 10)
python mcp/tools/codeboard-combo.dryrun.py   # exits 0, no network call

# Daemon skeleton offline-safe (after Task 11)
docker compose config --quiet   # exits 0
```

---

## F3 Pause — 11-item approval list

> Agent stops here. Output must include all 11 checkpoints in order, asking YES/NO for each.

1. `git commit` on local `dev` branch?
2. `git push origin dev` to `Tizzle716/core-engineering-system`?
3. `terraform plan` (no apply)?
4. `terraform apply`?
5. `gcloud builds submit` / `gcloud run deploy`?
6. `wrangler deploy` / wrangler KV / wrangler queues?
7. Infisical Universal Auth handshake?
8. `@agency-agents/cli` global install (`-g`)?
9. MCP system-wide registry edit (`mcp register ... --system`)?
10. Live API call to Antigravity IDE / Taskmaster.ai?
11. `docker compose up agency-agents-daemon` (port-bind 8082)?

---

## What this plan does NOT do

- Does **not** read credential directories (`.gemini`, `.google-cloud-sdk`, `Infisical*`, `.aws`, `.netrc`).
- Does **not** port to `/CORE-Modules/`, `/Inference-Tokenomics/`, or `/AISSC_Cloud_Workspace/`.
- Does **not** `git push`, `gcloud run deploy`, `terraform apply`, `wrangler deploy`, or call Infisical/Cloudflare without human approval.
- Does **not** `npm install -g @agency-agents/cli` (local-only by default).
- Does **not** make live HTTP calls to Antigravity/Taskmaster APIs from in-repo code.
- Does **not** write to system-wide MCP registry (`~/.config/mcp/`, `~/.opencode/`, `~/.claude/`, `~/.codex/`).
- Does **not** `docker compose up agency-agents-daemon` (port-bind deferred).
- Does **not** remove `non-root` user from any Dockerfile.
- Does **not** grant `roles/owner` or `roles/editor` in `terraform/iam.tf`.
- Does **not** touch the live ledger file by hand.

---

**Source of truth:** `.omo/plans/nexus-sprint.md` (439 lines). **Manifest:** `.omo/evidence/runbook-manifest.md` (129 lines).
