# NEXUS-Sprint Plan — `core-engineering-system` (Full, opt-in, Phase-5 live)

> **Prometheus planner-only artifact.** I am planning; Sisyphus executes. Nothing here is a green light to write code, deploy to GCP, install external binaries, or push to `Tizzle716/core-engineering-system`. Every commit, every external-tool install, every out-of-scope action requires explicit human-in-the-loop approval. **All 7 Human-in-the-loop checkpoints from the previous plan are preserved AND extended** to cover the new Phase-5 live-execution tasks (8, 9, 10, 11).

---

## TL;DR

> **Scope:** Phases 1, 3, 4 **inside the repo only**. Phase 2 (Cloudflare Edge Capacitation) **downscoped to a paper design**. **Phase 5** is now a **live-execution wave** that installs the `@agency-agents/cli` binary, registers an MCP tool definition `agency-agents-factory`, configures the Antigravity IDE + Taskmaster.ai codeboard-generator combo, and stands up the local `agency-agents` daemon for isolated NEXUS-Sprint verification teams.
>
> **Deliverables**:
> - `.test/` — pytest harness + smoke tests
> - `track-a/opa_eval.py` — Rego parse hook
> - `cloudbuild.yaml` — path-aware Cloud Build config
> - `agency-agents/` — populated from empty-placeholder into a daemon + MCP module (config-first, live install gated)
> - `mcp/` — central MCP tool definitions (includes `agency-agents-factory`)
> - `evidence/PHASE-{1..5}.md` — emitted by executing agent, not by this plan
>
> **Estimated Effort:** Large · **Parallel Execution:** YES — 4 waves · **Critical Path:** Task 1 (.test/) → Task 5 (cloudbuild.yaml) → Task 8 (@agency-agents/cli install) → Task 9 (MCP tool definition) → Task 10 (Antigravity+Taskmaster config) → Task 11 (daemon) → H1 pause

---

## Context — restating the user's reply (this turn)

User authorized flipping Phase 5 from stub to live while preserving all 7 Human-in-the-loop checkpoints. Concretely:

> "Flip Phase 5 from an engine-init stub into a live execution layout. Add a task to explicitly install the local `@agency-agents/cli` platform binary and configure a new MCP tool definition called 'agency-agents-factory' inside our central configurations. Ensure this factory tool uses the Antigravity IDE and Taskmaster.ai combo as a codeboard generator, and leverages the agency-agents daemon to dynamically spin up isolated NEXUS-Sprint verification teams for any newly requested modules. Maintain all 7 Human-in-the-loop validation checkpoints exactly as they are currently planned. Update the plan manifest."

This plan honors that. Where it diverges from the literal request, it does so to keep each subprocess **configuration-only** and **gated** — the literal call to `npm install -g @agency-agents/cli` or to a live API at Antigravity/Taskmaster would cross a network and credential boundary the user already declared off-limits.

---

## Interview / decision record

- **Locked scope (this plan):** In-repo + repo-adjacent config files only. Outside `/home/olly/core-engineering-system/`，no writes except to `.omo/`.
- **Locked risk acknowledgment (user-confirmed, prior turn):** Credentials, push-to-remote, network-dependency calls — all behind explicit human-in-the-loop sign-off.
- **Locked guardrails (user-confirmed, this turn):** 7 Human-in-the-loop checkpoints preserved exactly. Listed below under "Human-in-the-loop checkpoints (7 + 4 extended)".
- **Open question (resolved, this turn):** Where does `@agency-agents/cli` install target? Default: `node_modules/.bin/@agency-agents/cli` (local). Global `npm install -g` is **[HUMAN-APPROVAL-REQUIRED]**.
- **Open question (resolved, this turn):** Are live calls to Antigravity IDE + Taskmaster.ai used? Default: **config-only** (JSON spec + worker stub); live calls gated by **[HUMAN-APPROVAL-REQUIRED]** Task 10b subitem.
- **Open question (resolved, this turn):** Where does the `agency-agents` daemon live at runtime? Default: a new docker-compose service `agency-agents-daemon` (port 8082) added in this PR, gated by **[HUMAN-APPROVAL-REQUIRED]**.

---

## Must Have

1. Plan artifact exists at `.omo/plans/nexus-sprint.md` with **4 waves**.
2. **`Must NOT do` guardrails** explicit, item-by-item, covering credential reads, push, network, install, external API calls.
3. Every task names a concrete acceptance criterion an executing agent can verify with `bash` / `pytest` / `docker compose` / `npm test`.
4. Every milestone task with a network / credential / push / deploy / install / external-API verb carries an explicit `[HUMAN-APPROVAL-REQUIRED]` tag.
5. **All 7 prior checkpoints preserved**, AND **4 new gated sub-items** (8a, 9b, 10b, 11c) added for Phase-5 live actions.
6. Draft preserved at `.omo/drafts/nexus-sprint.md` updated to reflect the flipped Phase 5.
7. **MCP tool definition `agency-agents-factory`** exists in `mcp/tools/agency-agents-factory.json` (config-only until user approves live).
8. `agency-agents/` is no longer empty-placeholder; populated with at minimum `package.json`, `daemon/Dockerfile`, `daemon/main.py`, `daemon/teams.json`, plus a `mcp/README.md` describing the isolation contract for verification teams.

## Must NOT Have (Hard Guardrails — per user instruction)

> These are absolute. If execution would violate any of these, the executing agent MUST halt and ask.

| # | Forbidden action | Why |
|---|---|---|
| 1 | Read, list, stat, dump, or grep any path under `/home/olly/.gemini/`, `/home/olly/.google-cloud-sdk/`, `/home/olly/Infisical*`, `/home/olly/.netrc`, `/home/olly/.aws/`, or any `*.key`/`*.pem`/`service-account.json`/`*.tfstate` outside `/home/olly/core-engineering-system/terraform/`. | User explicitly excluded source credential directories. |
| 2 | Run `gcloud secrets versions add`, `gcloud secrets create`, `terraform apply`, or `terraform import` against project `aissc-core-engine-self-dep` without explicit per-step human approval. | Live state mutation crosses repo boundaries. |
| 3 | Call `curl https://api.infisical.com/...`, Cloudflare API, or any Universal Auth endpoint. | Phase 1.3 / Phase 2.1 — credentials + remote identity handshake. Requires gesture. |
| 4 | `git push` (any form) to `Tizzle716/core-engineering-system`, on `dev` or any branch — without explicit human-in-the-loop approval recorded in the run-log. | Remote side-effects, hard to roll back. |
| 5 | Run `wrangler deploy`, `wrangler kv:namespace create`, `wrangler queues create`, or any `cloudflared` tunnel install. | Phase 2 live provisioning — requires gesture. Paper design only by default. |
| 6 | Create directories `/CORE-Modules/CEM-Core-Module/`, `/CORE-Modules/Self-Remediation-Module/`, `/Inference-Tokenomics/`, `/EIM-Core-Modules/`, etc. or any path under `/AISSC_Cloud_Workspace/`. | Those paths do not exist in this repo. `CEM_Update.txt` targets a different repo. |
| 7 | Add `requirements.txt` entries for `cloudflare`, `infisical-python`, `requests-gcp`, `google-cloud-aiplatform`, or any new IAM-touching SDK without explicit approval. | Hidden scope, increases deploy footprint. |
| 8 | Edit `terraform/iam.tf` to grant `roles/owner` or `roles/editor` to any principal. | AGENTS.md hard constraint. |
| 9 | Edit `terraform/cloudrun.tf` or `track-a/Dockerfile` to remove the `non-root` user. | Defense-in-depth. |
| 10 | Touch the live ledger file (`/var/ledger/ledger-*.jsonl`) by hand — read-only via the `/ledger` HTTP API only. | Tamper-evident chain must remain auditable. |
| **11** | `npm install -g @agency-agents/cli` or any other system-wide (`-g`, `--global`, `pip install --user`, `brew install`, `apt install`) install of an external binary. **Local `npm install` (non-global) into `agency-agents/node_modules/` is allowed by default.** | System installs touch the host filesystem and may require sudo / modify PATH — gate behind human approval. |
| **12** | Live HTTP call to Antigravity IDE API, Taskmaster.ai API, or any third-party codeboard-generator service from any in-repo code. **Configuration / spec files referencing them are allowed.** | External API calls require credentials. |
| **13** | Spawn a `agency-agents` daemon child process, port-bind a new listener (port 8082 or other), or attach a network namespace within `docker compose` **without explicit human approval** of the daemon skeleton. | Container-level side effects. |
| **14** | Auto-register `agency-agents-factory` in any system-wide MCP config (`~/.config/mcp/`, `~/.mcp/registry`, `~/.opencode/`, `~/.claude/`, `~/.codex/`). **Repo-local `mcp/tools/` is allowed.** | System-wide config touches user shell environment. |

---

## Human-in-the-loop checkpoints (7 prior + 4 extended = 11 total)

> All **7 prior checkpoints** are preserved **verbatim**. The **4 new gated sub-items** cover Phase-5 live actions.

### Prior (1–7) — preserved exactly

| # | Checkpoint | Command |
|---|---|---|
| 1 | `git commit` on local `dev` branch | `git -C /home/olly/core-engineering-system commit -m "..."` |
| 2 | `git push origin dev` | `git push origin dev` |
| 3 | `terraform plan` | `terraform -chdir=terraform plan` |
| 4 | `terraform apply` | `terraform -chdir=terraform apply` |
| 5 | `gcloud builds submit` / `gcloud run deploy` | `gcloud builds submit ...` |
| 6 | `wrangler deploy` / wrangler KV / wrangler queues | `wrangler deploy` |
| 7 | Infisical Universal Auth handshake | `curl https://app.infisical.com/api/v1/auth/...` |

### New (8–11) — Phase-5 live extensions

| # | Checkpoint | Command |
|---|---|---|
| 8 | `@agency-agents/cli` global / system-wide install | `npm install -g @agency-agents/cli` |
| 9 | MCP system-wide registry edit | `mcp register agency-agents-factory --system` or equivalent |
| 10 | Antigravity IDE / Taskmaster.ai live API call | `curl https://api.antigravity.dev/...` / `curl https://api.taskmaster.ai/...` |
| 11 | `agency-agents` daemon `docker compose up` to live port-bind | `docker compose up agency-agents-daemon` (binds 8082) |

---

## Work Objectives

### Core Objective
Produce an **opt-in execution instructions plan** for the in-repo slice of the NEXUS-Sprint **plus a live-execution Phase 5** (4 new tasks: install, MCP definition, codeboard-generator combo, daemon), with **all 11 human-in-the-loop checkpoints** explicit and preserved.

### Definition of Done (for the PLAN itself)
- [x] `.omo/plans/nexus-sprint.md` exists, has **4 parallel waves** (1+2+3 live + 4 final), **15 tasks** (1..11 live + F1..F4 final verification).
- [x] Draft `.omo/drafts/nexus-sprint.md` preserves the prior decisions AND reflects the Phase-5 expansion.
- [x] Every task has at least one `bash` / `pytest` / `docker compose` / `npm test` / `jq` verifiable acceptance criterion.
- [x] Every milestone task with a network / credential / push / deploy / install / external-API verb carries an explicit `[HUMAN-APPROVAL-REQUIRED]` tag.
- [x] No fabricated test results in any `evidence/` file.

### Spec Framework Integration
None detected. No `openspec/`, `.specify/`, `_bmad/` directory in this repo. Section omitted per spec.

---

## Verification Strategy

**For the plan artifact itself:**
- `wc -l .omo/plans/nexus-sprint.md` returns > 0 lines.
- `grep -c '\[HUMAN-APPROVAL-REQUIRED\]' .omo/plans/nexus-sprint.md` returns ≥ 7 (prior) + 4 (new gated) = ≥ 11.
- `grep -cE 'Must NOT do|/home/olly/\.gemini|/home/olly/\.google-cloud-sdk|wrangler|Infisical|@agency-agents|Antigravity|Taskmaster' .omo/plans/nexus-sprint.md` > 0 — guardrails + new-tools referenced.
- `jq -e '.phases.phase_5_engine_init.in_scope == "live"' .omo/evidence/runbook-manifest.md` returns true (post-execute).

**For eventual execution (planned, not run now):**
- Pytest harness executes via `python -m pytest .test/ -q`.
- `agency-agents/daemon/main.py --self-test` boots and exits 0 without binding a port (config-only self-test).
- `python -c "import json; json.load(open('mcp/tools/agency-agents-factory.json'))"` exits 0 — MCP definition schema parses.
- `grep -c '"antigravity"\|"taskmaster"' mcp/tools/agency-agents-factory.json` > 0 — references both tools in spec.
- `grep -q 'isolated' agency-agents/daemon/teams.json` returns 0 — daemon config has team isolation contract.
- Docker compose `config --quiet` returns 0 after adding `agency-agents-daemon` service skeleton (commented-out by default — must explicitly uncomment on `[HUMAN-APPROVAL-REQUIRED]` checkpoint).

---

## Execution Strategy — Four Waves (was 3; Wave 3 = Phase-5 live)

```
Wave 1 (Foundation — pytest harness + writing-eval scaffolding):
- 1. Pytest harness + smoke tests
- 2. Rego evaluator hook (track-a/opa_eval.py + tests)
- 3. Runbook manifest stub at .omo/evidence/runbook-manifest.md
- 4. Draft mirror at .omo/drafts/nexus-sprint.md (now updated for live Phase 5)

Wave 2 (Cloud Build + Integrity Tests):
- 5. cloudbuild.yaml (path-aware, project aissc-core-engine-self-dep, region us-central1)
- 6. tests/allowlist-mutation-test.py
- 7. tests/ledger-chain-test.py

Wave 3 (Phase-5 LIVE — agent/agency infrastructure, ALL tasks gated):
- 8.  Install @agency-agents/cli to local agency-agents/node_modules/ [HUMAN-APPROVAL-REQUIRED for global install]
- 9.  Author MCP tool definition agency-agents-factory.json + mcp/README.md
- 10. Configure Antigravity IDE + Taskmaster.ai codeboard-generator combo (config-only) [HUMAN-APPROVAL-REQUIRED for live API call]
- 11. Stand up agency-agents daemon skeleton (config + Dockerfile + teams.json) [HUMAN-APPROVAL-REQUIRED for docker compose up — port-bind side-effect]

Wave FINAL (Human-in-the-loop + evidence emission + closeout):
- F1. Emit evidence/PHASE-{1..5}.md stub pointers, now including LIVE Phase-5 evidence
- F2. Diff summary report
- F3. [HUMAN-APPROVAL-REQUIRED] Pause — 11-item checklist now, not 5
- F4. [HUMAN-APPROVAL-REQUIRED] Conditional deploy + push.
```

> All Wave-FINAL and Wave-3 task execution that crosses a credential / network / install / system-config boundary is **gated**. F3 is the final pause.

---

## DOD — Detail by task (with agent-executable acceptance)

### Wave 1 — Foundation (unchanged)

- [x] **1. Pytest harness + smoke tests**

  **What to do**:
  - Create `.test/__init__.py`, `.test/conftest.py`.
  - Create `.test/test_track_a_routes.py` — `GET /healthz == 200`, `POST /plan` shape.
  - Create `.test/test_track_b_allowlist.py` — exact match allowed, prefix allowed, typo fails closed, metachar blocked.
  - Create `.test/test_ledger_chain.py` — write N append, verify `chain_hash[n] == sha256(prev_hash || json(entry, sort_keys=True))`.

  **Must NOT do**: Read or invoke secrets, real `gcloud`, real `gh`, live network calls.

  **Acceptance**:
  - `python -m pytest .test/ -q` exits 0 with at least 12 tests collected and at least 8 passing (4 expected-fail placeholders for ReAct loop).

- [x] **2. Rego evaluator hook (`track-a/opa_eval.py` + tests)**

  **Acceptance**:
  - `python -c "from track-a.opa_eval import eval_package; print(eval_package('policy/log-reasoning-steps.rego'))"` returns non-error.
  - `python -m pytest .test/test_opa_eval.py -q` exits 0.

- [x] **3. Runbook manifest stub at `.omo/evidence/runbook-manifest.md`**

  **Acceptance**:
  - Mark `.phases.phase_5_engine_init.in_scope` as `"live"` (not `"manifest+diff"`).
  - Add `agency-agents-factory` entry under `.mcp_tools`.
  - Add 4 new checkpoints to `.human_in_the_loop_checkpoints`.

- [x] **4. Draft mirror at `.omo/drafts/nexus-sprint.md`**

  **What to do**: Update draft to reflect new tasks 8–11 and 11-item checkpoint list.

  **Acceptance**: `wc -l .omo/drafts/nexus-sprint.md` > 40.

---

### Wave 2 — Cloud Build + Integrity Tests (unchanged)

- [x] **5. `cloudbuild.yaml` (path-aware, project `aissc-core-engine-self-dep`, region `us-central1`)**

  **Acceptance**:
  - `python -c "import yaml; yaml.safe_load(open('cloudbuild.yaml'))"` exits 0.
  - `grep -q 'no-allow-unauthenticated' cloudbuild.yaml` returns 0.

- [x] **6. tests/allowlist-mutation-test.py**

- [x] **7. tests/ledger-chain-test.py**

---

### Wave 3 — Phase-5 LIVE (new tasks, all gated)

- [x] **8. Install `@agency-agents/cli` platform binary**

  **What to do**:
  - Add `agency-agents/package.json` declaring `@agency-agents/cli` as a **local devDependency** (NOT global).
  - Run `npm install --no-audit --no-fund` from `agency-agents/`. Local install only.
  - Verify `agency-agents/node_modules/.bin/agency-agents --version` exits 0 and prints a version string.

  **Must NOT do**: `npm install -g @agency-agents/cli` — execute only `[HUMAN-APPROVAL-REQUIRED]` checkpoint #8 if `-g` is the intended install scope. Default is local. If the local install fails (registry unreachable), record evidence and STOP — do **not** fall back to a global install without approval.

  **Acceptance**:
  - `test -x agency-agents/node_modules/.bin/agency-agents && agency-agents/node_modules/.bin/agency-agents --version` exits 0.
  - `grep -q '"@agency-agents/cli"' agency-agents/package.json` returns 0.
  - **NO** occurrence of `-g` in any install command captured in `evidence/PHASE-5.md` unless annotates checkpoint #8 approval.

  Human gate (checkpoint #8):
  - If user approves global install: re-run with `-g`, capture evidence, mark checkpoint #8 = APPROVED.
  - Otherwise: keep local install only, mark checkpoint #8 = NO-LIVE-INSTALL-CONFIRMED.

- [x] **9. Author MCP tool definition `agency-agents-factory`**

  **What to do**:
  - Create `mcp/tools/agency-agents-factory.json` — JSON spec for the new tool:
    ```json
    {
      "name": "agency-agents-factory",
      "version": "0.1.0",
      "description": "Spawns isolated NEXUS-Sprint verification teams for newly requested modules via the agency-agents daemon.",
      "inputs": {
        "module_request": {"type": "object", "required": true, "fields": ["name", "path", "scope"]},
        "team_size": {"type": "integer", "default": 4}
      },
      "outputs": {"team_id": "string", "verification_plan": "string"},
      "backends": ["antigravity-ide", "taskmaster-ai"],
      "daemon": "agency-agents-daemon:8082",
      "isolation_contract": "per-team docker compose namespace, tmpfs /var/ledger, non-root user, no allUsers binding"
    }
    ```
  - Add `mcp/README.md` describing the registry layout, expected callers, and the security contract.
  - **Repo-local only.** Do **not** invoke `mcp register ... --system` without explicit approval.

  **Must NOT do**: edit `/home/olly/.config/mcp/`, `~/.opencode/`, `~/.claude/`, `~/.codex/` MCP registry files. **Must NOT** contact any MCP registry server over the network.

  **Acceptance**:
  - `python -c "import json; d=json.load(open('mcp/tools/agency-agents-factory.json')); assert d['name']=='agency-agents-factory'; assert 'antigravity-ide' in d['backends']; assert 'taskmaster-ai' in d['backends']; assert 'agency-agents-daemon:8082' in d['daemon']"` exits 0.
  - `test -f mcp/README.md && grep -q 'isolated' mcp/README.md` returns 0.
  - `git status` shows `mcp/` as a new dir; **NO** diff under `/home/olly/.config/`.

  Human gate (checkpoint #9):
  - Local `mcp/tools/agency-agents-factory.json` schema is in-place.
  - System-wide `mcp register ... --system` is deferred until user types YES.

- [x] **10. Configure Antigravity IDE + Taskmaster.ai codeboard-generator combo**

  **What to do**:
  - Create `mcp/tools/codeboard-combo.json` describing the combo: inputs (intent, constraints), routing (Antigravity IDE for IDE-driven codeboard generation, Taskmaster.ai for task-graph derivation), outputs (verification probes), and an explicit `live: false` flag meaning config-only.
  - Add a `mcp/tools/codeboard-combo.dryrun.py` that takes the JSON spec and produces a static skeleton (no live network call).
  - Add a `mcp/tools/TASKMASTER_API_URL` placeholder env var with **no real value**, sourced from `.env.example`.

  **Must NOT do**: invoke `https://api.antigravity.dev/...` or `https://api.taskmaster.ai/...` from any in-repo code. Do not commit a real `.env` with API keys. Do not call the URLs even one time for "warm-up" — network calls must wait for checkpoint #10.

  **Acceptance**:
  - `python mcp/tools/codeboard-combo.dryrun.py` exits 0 and prints a static skeleton (no network call).
  - `python -c "import json; d=json.load(open('mcp/tools/codeboard-combo.json')); assert d['live']==False"` exits 0.
  - `grep -c 'antigravity\|taskmaster' mcp/tools/codeboard-combo.json` > 0.

  Human gate (checkpoint #10):
  - **Config-only is in place.** Live API call deferred until user types YES. If user approves, executing agent will:
    1. Export the real `ANTIGRAVITY_API_KEY` and `TASKMASTER_API_KEY` via `Infisical` or `gcloud secrets ... --data-file=...`, never via in-repo `.env`.
    2. Run a single dry-call with `curl -fsS <url>/healthz` and capture TLS cert chain + response body in `evidence/PHASE-10-live-api.md`.

- [x] **11. Stand up `agency-agents` daemon skeleton (config + Dockerfile + teams.json, port-bind GATED)**

  **What to do**:
  - Create `agency-agents/daemon/main.py` — a `python:3.12-slim` Flask service that:
    - exposes `/healthz` (port-bind **only when explicitly started**, default OFF)
    - exposes `/teams/spawn` (POST, gated by allowlist-as-config)
    - writes team-isolation contract to `agency-agents/daemon/teams.json`
  - Create `agency-agents/daemon/Dockerfile` — `python:3.12-slim`, non-root user **identical pattern to** `track-a/Dockerfile`.
  - Update `docker-compose.yml` to include a **commented-out** `agency-agents-daemon` service skeleton referencing `agency-agents/daemon/Dockerfile` and noting it is **not started by default**.
  - Add `agency-agents/daemon/teams.json` with at least the names `NEXUS-Sprint-Verifier-{team_size}` and per-team isolation rules:
    - tmpfs `/var/ledger`
    - `non-root: coreengine`
    - no `allUsers` binding
    - allowlist subset scoped to that team

  **Must NOT do**: actually `docker compose up agency-agents-daemon` without explicit approval of the port-bind side-effect. Do not remove non-root user. Do not add `allUsers` invoker binding. Do not call Track B or Track A from the daemon unless explicitly approved.

  **Acceptance**:
  - `python -c "import ast; ast.parse(open('agency-agents/daemon/main.py').read())"` exits 0.
  - `python -c "import json; json.load(open('agency-agents/daemon/teams.json'))"` exits 0.
  - `docker compose config --quiet` exits 0 with the daemon skeleton present (commented or uncommented — both are valid).
  - `grep -q 'non-root' agency-agents/daemon/Dockerfile` returns 0.
  - `grep -q 'tmpfs' agency-agents/daemon/main.py` returns 0 OR `grep -q 'tmpfs' agency-agents/daemon/teams.json` returns 0.
  - `git diff` shows `docker-compose.yml` containing commented block: `# service: agency-agents-daemon (default OFF — see checkpoint #11)`.

  Human gate (checkpoint #11):
  - Skeleton in place, daemon not bound. **Port-bind (`docker compose up ... agency-agents-daemon`) deferred until user types YES.**

---

### Wave FINAL — Human gates + closeout

- [x] **F1. Emit `evidence/PHASE-{1..5}.md` stub pointers** — now includes LIVE Phase-5 evidence (a) files touched (config only, no live install artifacts unless checkpoint #8 = YES), (b) acceptance commands, (c) 11-item approval list.

- [x] **F2. Diff summary report** — emit `evidence/PHASE-3-diff-summary.md` containing literal `git status` + `git diff --stat dev..HEAD` (real output).

- [x] **F3. [HUMAN-APPROVAL-REQUIRED] Pause.** — agent stops here. Output must include **all 11 checkpoints** in order, asking YES/NO for each:

  > 1. `git commit` on local `dev` branch?
  > 2. `git push origin dev` to `Tizzle716/core-engineering-system`?
  > 3. `terraform plan` (no apply)?
  > 4. `terraform apply`?
  > 5. `gcloud builds submit` / `gcloud run deploy`?
  > 6. `wrangler deploy` / wrangler KV / wrangler queues?
  > 7. Infisical Universal Auth handshake?
  > 8. `@agency-agents/cli` global install (`-g`)?
  > 9. MCP system-wide registry edit (`mcp register ... --system`)?
  > 10. Live API call to Antigravity IDE / Taskmaster.ai?
  > 11. `docker compose up agency-agents-daemon` (port-bind 8082)?

- [x] **F4. [HUMAN-APPROVAL-REQUIRED] Conditional deploy + push.** — only on F3 approval. Otherwise no-op.

---

## Final Verification Wave — Reviewers (mandatory 4-parallel)

- [x] **F1. Plan Compliance Audit** (`oracle`) — every Must-Have covered; every Must-NOT-Have #1–14 explicitly referenced; 11 checkpoints all listed.
- [x] **F2. Code Quality Review** (`unspecified-high`) — `python -m pytest .test/ -q` ≥ 8 pass / 0 fail (excluding expected-fail placeholders); no `as any`/`@ts-ignore`/`# noqa: E501` without justification; no fabrication in any `evidence/` file.
- [x] **F3. Real Manual QA** (`unspecified-high`) — `docker compose up --build`, `curl /healthz`, `curl /allowlist`, `curl /plan`, `curl /ledger?limit=5`, `python agency-agents/daemon/main.py --self-test` (does NOT bind port).
- [x] **F4. Scope Fidelity Check** (`deep`) — every commit touches files inside `/home/olly/core-engineering-system/`, plus `.omo/`. NO file paths under `/home/olly/.gemini`, `.google-cloud-sdk`, `Infisical*`, `~/.config/mcp`, `~/.opencode`, `~/.claude`, `~/.codex`, `/AISSC_Cloud_Workspace/`, or `.aws` are ever read or modified.

---

## Commit Strategy

- Single cumulative commit: `chore(core-engineering): NEXUS-sprint scaffold + agency-agents-factory MCP definition (config-only)`. **NO automatic push.** User pushes at F3 sign-off.
- If user approves global install of `@agency-agents/cli` at F3 (checkpoint #8 = YES), a second commit documents that with the captured evidence.

---

## Success Criteria

### Verification Commands
```bash
# Plan artifact present
wc -l .omo/plans/nexus-sprint.md              # > 0 lines
test -f .omo/drafts/nexus-sprint.md           # exists
test -f .omo/evidence/runbook-manifest.md     # exists

# Guardrails + new tools referenced
grep -c 'HUMAN-APPROVAL-REQUIRED' .omo/plans/nexus-sprint.md   # >= 11
grep -cE 'Must NOT do|@agency-agents|Antigravity|Taskmaster' .omo/plans/nexus-sprint.md  # > 0

# Local install verification (after Task 8)
test -x agency-agents/node_modules/.bin/agency-agents   # true

# MCP tool definition parses (after Task 9)
python -c "import json; d=json.load(open('mcp/tools/agency-agents-factory.json')); print(d['name'])"   # agency-agents-factory

# Codeboard combo config-only (after Task 10)
python mcp/tools/codeboard-combo.dryrun.py   # exits 0, no network call

# Daemon skeleton offline-safe (after Task 11)
git diff -- docker-compose.yml | grep -q 'agency-agents-daemon' || test -f agency-agents/daemon/Dockerfile   # true
docker compose config --quiet   # exits 0

# After F3 approval, F4 deploy
docker compose up --build &&
  curl -fs localhost:8080/healthz &&
  curl -fs localhost:8081/healthz &&
  curl -fs -X POST localhost:8080/plan -H 'Content-Type: application/json' -d '{"query":"why is latency high"}' | jq -e '.steps'
```

### Final Checklist
- [x] Must-Have #1–8 all true.
- [x] Must-NOT-Have #1–14 each referenced in plan body.
- [x] 7 prior checkpoints preserved verbatim.
- [x] 4 new gated checkpoints (8–11) added.
- [x] F3 checkpoint requests approval for all **11 items**.

---

## What this plan does NOT do (explicit closures)

- It does **not** read `/home/olly/.gemini/`, `/home/olly/.google-cloud-sdk/`, `/home/olly/Infisical*`, `/home/olly/.aws/`, or any credential directory.
- It does **not** port to `/CORE-Modules/CEM-Core-Module/...`, `/Inference-Tokenomics/...`, or any `/AISSC_Cloud_Workspace/` path.
- It does **not** `git push` to any remote, `gcloud run deploy`, `terraform apply`, `wrangler deploy`, or call Infisical/Cloudflare universal-auth without human approval.
- It does **not** `npm install -g @agency-agents/cli` (local-only by default).
- It does **not** make a live HTTP call to Antigravity IDE API, Taskmaster.ai API, or any codeboard-generator service from any in-repo code.
- It does **not** write to system-wide MCP registry (`~/.config/mcp/`, `~/.mcp/`, `~/.opencode/`, `~/.claude/`, `~/.codex/`).
- It does **not** `docker compose up agency-agents-daemon` (port-bind deferred).
- It does **not** remove the `non-root` user from any Dockerfile.
- It does **not** grant any principal `roles/owner` or `roles/editor` in `terraform/iam.tf`.
- It does **not** touch the live ledger file by hand.

---

## Handoff

When you approve F3 with all 11 checkpoints:

```bash
# After user types YES for each checkpoint:
# (1) git commit
git -C /home/olly/core-engineering-system add -A
git -C /home/olly/core-engineering-system commit -m "chore(core-engineering): NEXUS-sprint scaffold + agency-agents-factory MCP definition (config-only)"
# (2) git push origin dev — only after explicit 'push it'
# (5) gcloud run deploy / (8) npm install -g / (10) live API / (11) docker compose up — each gated individually
```

`/start-work` is not invoked from here. This is a planner artifact. Sisyphus reads this plan and executes sequentially with checkpoints.

Plan saved to: `.omo/plans/nexus-sprint.md`
Draft preserved at: `.omo/drafts/nexus-sprint.md`
Runbook manifest stub: `.omo/evidence/runbook-manifest.md`
