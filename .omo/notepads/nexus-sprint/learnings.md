## 2026-07-19 — Draft mirror recreated (Task 4)

**Context:** The draft at `.omo/drafts/nexus-sprint.md` was deleted during the Prometheus cleanup step. Recreated to reflect the Phase-5 LIVE flip.

**What was done:**
- Created `.omo/drafts/nexus-sprint.md` (172 lines, > 40 required).
- Mirrored key decisions from `.omo/plans/nexus-sprint.md` (439 lines) into a summary draft.
- Included all 4 waves (Wave 1: tasks 1–4, Wave 2: tasks 5–7, Wave 3: tasks 8–11 LIVE, Wave FINAL: F1–F4).
- Included all 11 human-in-the-loop checkpoints (7 prior + 4 new for Phase-5).
- Included all 14 Must-NOT-Have items.
- Included Phase-5 LIVE task details: install `@agency-agents/cli`, MCP tool definition `agency-agents-factory`, Antigravity+Taskmaster combo, `agency-agents` daemon.

**Verification:**
- `wc -l .omo/drafts/nexus-sprint.md` → 172 (> 40 ✓)
- `grep -cE 'Wave|HUMAN-APPROVAL-REQUIRED|@agency-agents|Antigravity|Taskmaster|agency-agents-factory|14'` → 41 matches

**Notes:**
- Draft is a summary, not a duplicate of the plan.
- No commits made (per MUST NOT DO).
- Source of truth remains `.omo/plans/nexus-sprint.md`.
- Manifest at `.omo/evidence/runbook-manifest.md` (129 lines) confirms Phase-5 `in_scope: live`.

## 2026-07-19 — Pytest harness created (Task: pytest harness)

**Context:** First task in Wave 1. Created the test harness for the core-engineering-system repo. No production code was modified.

**What was done:**
- Created `.test/__init__.py` (empty package marker).
- Created `.test/conftest.py` with Flask test client fixtures for track-a and track-b. Each fixture loads the module via `importlib.util.spec_from_file_location` (because `track-a/` and `track-b/` have hyphens and aren't valid Python package names). Each test gets isolated `LEDGER_PATH` and `TOOL_ALLOWLIST` via `tmp_path` + `monkeypatch.setenv`.
- Created `.test/test_track_a_routes.py` — 5 passing tests (healthz, plan structure, missing query, latency hypothesis) + 4 `xfail(strict=True)` placeholders for ReAct loop features not yet implemented (pre-validation, retry, hypothesis adjustment, reasoning chain).
- Created `.test/test_track_b_allowlist.py` — 6 passing tests (exact match, prefix match, typo, double-space, missing reasoning ref, allowlist endpoint) + 10 parametrized metachar tests (one per prohibited character).
- Created `.test/test_ledger_chain.py` — 4 passing tests verifying the chain hash spec: `chain_hash[n] == sha256((prev_hash or "") + json.dumps(entry_without_chain_hash, sort_keys=True))`. Tests cover single-entry hash, N-entry integrity, tamper detection, and chain-link determinism.
- Added `.venv/` to `.gitignore`.

**Verification:**
- `.venv/bin/python -m pytest .test/ -q` → `30 passed, 4 xfailed in 1.91s` (exit 0).
- 34 tests collected (≥ 12 required ✓), 30 passing (≥ 8 required ✓).

**Key findings:**
- Track A's `react_plan()` calls `execute_action_via_track_b()` which makes HTTP requests to Track B. Without a live Track B, tests would hang on connection timeouts. Solution: mock `requests.post` in the `track_a_module` fixture so `/plan` tests run in <2s.
- The chain hash is computed BEFORE `chain_hash` is added to the entry dict (chicken-and-egg in the source). The test reconstructs `entry_without_chain_hash` by filtering out the `chain_hash` key, then verifies `sha256(prev + json(entry_without_hash, sort_keys=True))`.
- `xfail(strict=True)` flips to FAILED if the test unexpectedly passes. The first version of `test_plan_pre_validates_tools_against_allowlist` XPASSed because the mock made all tools valid. Fixed by changing the assertion to check for a validation step in the plan (which doesn't exist today).
- Pre-existing `.test/test_opa_eval.py` (5 tests) was already in the repo and now passes because `track-a/opa_eval.py` exists locally (untracked, not my responsibility).

**Notes:**
- No commits made (per MUST NOT DO).
- No production code modified (per MUST NOT DO).
- No new dependencies added (per MUST NOT DO).

## 2026-07-19 — Rego evaluator hook created (Task: opa_eval)

**Context:** Wave 1 task to create the Rego evaluator hook for the core-engineering-system. The `policy/*.rego` files are documentation-of-intent (not currently evaluated by either track). This task creates a structural parser stub that extracts `package`, `imports`, and `rules` from a Rego file without actually evaluating policy logic.

**What was done:**
- Created `track-a/opa_eval.py` — `eval_package(path)` function using stdlib `re` (no `opa-python` dependency). Parses `package <name>`, `import <path>`, and rule headers `<name>[<key>] { <body> }` via brace-balancing (Rego bodies can contain nested braces in expressions). Comments (`#`) are stripped before parsing.
- Created `.test/test_opa_eval.py` — 5 tests: required keys present, package name extracted, `deny` rule found, imports is a list, missing file raises `FileNotFoundError`.
- Created `track_a/__init__.py` — Python package alias for `track-a/`. Uses `importlib.util.spec_from_file_location` to register `track-a/opa_eval.py` as `track_a.opa_eval`. This bridges the hyphen-vs-underscore naming gap so both pytest and standalone Python can `from track_a.opa_eval import eval_package`.
- Created `conftest.py` — idempotent fallback that registers `track_a` if not already in `sys.modules` (safety net for pytest invocations that don't auto-load `track_a/__init__.py`).

**Verification:**
- `.venv/bin/python -m pytest .test/test_opa_eval.py -q` → `5 passed in 0.13s` (exit 0).
- `.venv/bin/python -c "from track_a.opa_eval import eval_package; print(eval_package('policy/log-reasoning-steps.rego'))"` → returns `{'package': 'core.constitutional', 'imports': [], 'rules': [{'name': 'deny', 'key': 'msg', 'body': '...'}}}`.
- Sanity check on all 4 Rego files: all parse with `package='core.constitutional'`, `rules=['deny']`, `imports=[]`.

**Key findings:**
- `re.finditer` with `^` requires `re.MULTILINE` flag to match line starts. First implementation missed this and returned empty rules list — caught by the failing test, not by manual inspection.
- The `track-a/` directory has a hyphen, which Python rejects as a module name. Two solutions work: (a) `track_a/__init__.py` with importlib loading (chosen — works for both pytest and standalone Python), or (b) `conftest.py` with sys.modules injection (works for pytest only). Option (a) is strictly better.
- Brace-balancing is necessary for rule body extraction because Rego expressions can contain nested braces (e.g., function calls, set literals). A simple regex `\{.*\}` would fail on multi-line bodies or nested structures.
- The parser is a structural stub — it does NOT evaluate Rego rules. Wire-up to a real OPA engine (e.g., `opa-python` or subprocess to `opa eval`) is a future task.

**Notes:**
- No commits made (per MUST NOT DO).
- `track-a/main.py` not modified (per MUST NOT DO).
- No new dependencies added (per MUST NOT DO — used stdlib `re` only).
- `track_a/` directory created at repo root as a package alias; does not duplicate `track-a/` source files.

## 2026-07-19 — Cloud Build pipeline created (Task 5)

**Context:** Wave 2 task to create a path-aware Cloud Build config that builds both `track-a/` and `track-b/` Docker images and deploys them to Cloud Run. The README had a `gcloud run deploy --source` pattern, but the task required explicit `docker build` + `gcloud run deploy` steps for CI/CD clarity.

**What was done:**
- Created `cloudbuild.yaml` (4 steps, 4 images, 6 substitutions).
- Step 1: `build-track-a` — `docker build -f track-a/Dockerfile -t ${_REPO}/${_SERVICE_A}:${SHORT_SHA} -t ...:latest track-a`. Build context is the `track-a/` directory so `COPY main.py .` in the Dockerfile resolves correctly.
- Step 2: `build-track-b` — same pattern with `track-b/Dockerfile` and `track-b/` context.
- Step 3: `deploy-track-a` — `gcloud run deploy track-a-control-loop` with `--no-allow-unauthenticated`, `--ingress=internal`, `--service-account=core-engine-worker@${_PROJECT}.iam.gserviceaccount.com`, free-tier sizing (`--cpu=1 --memory=512Mi --min-instances=0 --max-instances=1`), `--port=8080`.
- Step 4: `deploy-track-b` — same pattern, `--port=8081`.
- Substitutions block: `_PROJECT=aissc-core-engine-self-dep`, `_REGION=us-central1`, `_REPO=gcr.io/${_PROJECT}`, `_SERVICE_A=track-a-control-loop`, `_SERVICE_B=track-b-actuator`, `_SERVICE_ACCOUNT=core-engine-worker@${_PROJECT}.iam.gserviceaccount.com`.
- `options.logging: CLOUD_LOGGING_ONLY` — no GCS bucket required for build logs.
- `timeout: 600s` — 10 minutes for build + deploy.

**Verification:**
- `python3 -c "import yaml; yaml.safe_load(open('cloudbuild.yaml'))"` → exits 0, parses to 4 steps + 4 images + 6 substitutions.
- `grep -c 'no-allow-unauthenticated' cloudbuild.yaml` → 4 (2 deploy steps + 2 comments).
- `grep -q 'aissc-core-engine-self-dep'` → PRESENT.
- `grep -q 'us-central1'` → PRESENT.
- `grep -q 'core-engine-worker@'` → PRESENT.
- All sizing flags present: `cpu=1`, `memory=512Mi`, `min-instances=0`, `max-instances=1`.
- Path-aware: both `track-a/Dockerfile` and `track-b/Dockerfile` referenced.
- No `roles/owner` or `roles/editor` anywhere.
- No plaintext secrets (only Secret Manager references via env vars, which are set in terraform/cloudrun.tf, not in this file).

**Key findings:**
- Used `${_PROJECT}` (custom substitution) instead of `${PROJECT_ID}` (Cloud Build built-in) so the project name appears literally in the file. This satisfies the "Uses project `aissc-core-engine-self-dep`" requirement as a literal string AND keeps the config portable via `--substitutions=_PROJECT=other-project` at submit time.
- `--ingress=internal` maps to terraform's `INGRESS_TRAFFIC_INTERNAL_ONLY`. Without this flag, gcloud defaults to `--ingress=all` which would allow external traffic — a Constitutional AI violation.
- `--port=8080` and `--port=8081` are explicit to match the `container_port` settings in terraform/cloudrun.tf. The Dockerfiles `EXPOSE` these ports, so gcloud could infer them, but being explicit prevents drift.
- The README's deploy command uses `--source ./track-a` (gcloud builds + deploys in one step). The cloudbuild.yaml separates build and deploy for CI/CD clarity — each step is independently retryable and the build artifacts are tagged with `${SHORT_SHA}` for traceability.
- `images:` block lists all 4 pushed images (2 services × 2 tags) so Cloud Build tracks them for caching and cleanup.

**Notes:**
- No commits made (per MUST NOT DO).
- No existing files modified (per MUST NOT DO).
- No live deploy commands run (per MUST NOT DO).
- Config is ready for `gcloud builds submit --config=cloudbuild.yaml` but was not executed.

## 2026-07-19 — Allowlist mutation test created (Task 6)

**Context:** Wave 2 task to create a standalone Python test script (NOT pytest) that verifies Track B's allowlist behavior when the allowlist file is mutated. This complements the pytest-based `.test/test_track_b_allowlist.py` which tests within-process behavior; this script tests cross-process behavior (mutations between process restarts).

**What was done:**
- Created `tests/allowlist-mutation-test.py` — standalone runner, 4 scenarios, subprocess-based.
- Uses `importlib.util.spec_from_file_location` to load `track-b/main.py` (hyphen in dir name) inside each subprocess.
- Sets `TOOL_ALLOWLIST` env var before loading the module so `TOOL_ALLOWLIST_FILE` resolves to the test file.
- Calls `module.ALLOWLIST = module.load_allowlist()` then `module.is_allowed(tool)` for each test tool.
- Returns results as JSON via stdout, parsed by the parent process.
- Uses `.venv/bin/python` for subprocesses (system Python lacks Flask/requests).

**Scenarios tested:**
1. Add entry → previously-denied tool now allowed (Process A denies `kubectl get nodes`, Process B allows it after adding to allowlist).
2. Remove entry → previously-allowed tool now denied (Process A allows `kubectl get nodes`, Process B denies it after removal).
3. Empty allowlist → all tools denied (allowlist_size=0, every tool returns False).
4. Allowlist loaded fresh per process (persistent file mutated between Process A and Process B; Process B sees new content).

**Verification:**
- `python3 tests/allowlist-mutation-test.py` → `4/4 tests passed`, exit code 0.
- All 4 scenarios produce expected PASS output with clear before/after allowlist contents and per-tool results.

**Key findings:**
- `tempfile.mkstemp()` does NOT accept an `encoding` kwarg (unlike `NamedTemporaryFile`). Must use `os.fdopen(fd, "w", encoding="utf-8")` to write with encoding. First run failed on Test 4 with `TypeError: mkstemp() got an unexpected keyword argument 'encoding'` — caught by running the script, not by manual inspection.
- The `is_allowed()` prefix-match semantics work as documented: `kubectl get pods -A` matches `kubectl get pods` (exact + space-prefix). Verified explicitly in Test 1.
- Track B's `ALLOWLIST` global is populated at module import time (line 53: `ALLOWLIST: set[str] = set()`) and only re-populated in `if __name__ == "__main__":` (line 236). When loaded via importlib (not as `__main__`), the global stays empty until you explicitly call `module.ALLOWLIST = module.load_allowlist()`. This is the correct pattern for testing — it mirrors what production does at startup.
- The subprocess approach is necessary because the allowlist is loaded once per process. Within a single process, mutating the file has no effect on `is_allowed()` results (the ALLOWLIST set is frozen at load time). Cross-process, each fresh subprocess re-reads the file.

**Notes:**
- No commits made (per MUST NOT DO).
- `track-b/main.py` not modified (per MUST NOT DO).
- `policy/tool-allowlist.txt` not modified (per MUST NOT DO).
- No new dependencies added (per MUST NOT DO — used stdlib `subprocess`, `tempfile`, `importlib`, `json`, `os`, `sys` only).
- No live network calls (per MUST NOT DO — all subprocesses run locally).
- Script is standalone (no pytest import), exits 0 on success, non-zero on failure.

## 2026-07-19 — Standalone ledger chain test created (Task 7)

**Context:** Wave 2 task to create a standalone Python test script (NOT pytest) that verifies the tamper-evident ledger chain hash computation across both Track A and Track B. Complements the pytest-based `.test/test_ledger_chain.py` which tests within-process behavior; this script tests cross-process behavior (fresh `_last_hash` per subprocess).

**What was done:**
- Created `tests/ledger-chain-test.py` — standalone runner, 4 scenarios, subprocess-based.
- Uses `importlib.util.spec_from_file_location` to load `track-a/main.py` and `track-b/main.py` inside each subprocess (hyphen in dir names).
- Sets `LEDGER_PATH` env var BEFORE importing the track module — critical because `track-a/main.py:34` and `track-b/main.py:33` call `LEDGER_PATH.mkdir(parents=True, exist_ok=True)` at module load time using the default `/var/log/ledger` path. Without this, the helper fails with `PermissionError: [Errno 13] Permission denied: '/var/log/ledger'`.
- Helper script writes N entries via `module.write_ledger_entry()`, then exits. Each subprocess gets a fresh `_last_hash = None`.
- Main script reads the ledger file, walks the chain, and verifies each entry's `chain_hash` matches `sha256((prev_hash or "") + json.dumps(entry_without_chain_hash, sort_keys=True))`.
- Uses `.venv/bin/python` for subprocesses (system Python lacks Flask/requests).

**Scenarios tested:**
1. Single entry hash matches spec (Track A and Track B) — 2 checks.
2. Chain integrity over N=5 entries (Track A and Track B) — 2 checks.
3. Tamper detection breaks chain — write 3 entries, mutate entry 0's payload, verify stored hash no longer matches recomputed hash.
4. Track A and Track B chains are independent — write 1 entry to each, verify chain hashes differ (Track B has extra `"track": "B"` field).

**Verification:**
- `.venv/bin/python tests/ledger-chain-test.py` → `6/6 checks passed`, exit code 0.
- All 4 scenarios produce expected PASS output with clear per-check labels.

**Key findings:**
- `LEDGER_PATH` must be set via env var BEFORE `importlib.util.spec_from_file_location().exec_module()` — the module-level `LEDGER_PATH.mkdir()` call runs at import time, not at first use. First run failed with `PermissionError: '/var/log/ledger'` — caught by running the script.
- Each scenario uses its own temp ledger directory (`s1-a`, `s2-a`, `s3`, `s4-a`, etc.) to avoid cross-scenario chain contamination. If you reuse the same directory across scenarios, the chain breaks because each subprocess starts with `_last_hash = None` but the ledger already has entries from a previous subprocess.
- Track B's entry dict includes an extra `"track": "B"` field that Track A's doesn't. This is what makes the chains independent — even with identical payloads, the serialized JSON differs, so the chain hashes differ. The independence test verifies this directly.
- The tamper detection test mutates the entry in memory (not the file on disk). This is sufficient to prove the chain hash spec catches tampering — if the stored hash doesn't match the recomputed hash, the chain is broken.
- The pytest version (`.test/test_ledger_chain.py`) uses a fixture that loads the module once and resets `_last_hash` between tests. The standalone version uses subprocesses because `_last_hash` is module-level state that can't be reset across "tests" without a process boundary.

**Notes:**
- No commits made (per MUST NOT DO).
- `track-a/main.py` and `track-b/main.py` not modified (per MUST NOT DO).
- No new dependencies added (per MUST NOT DO — used stdlib `subprocess`, `tempfile`, `importlib`, `hashlib`, `json`, `os`, `sys` only).
- No live network calls (per MUST NOT DO — all subprocesses run locally).
- Script is standalone (no pytest import), exits 0 on success, non-zero on failure.
- Live ledger at `/var/log/ledger` never touched — all writes go to temp directories under `tempfile.TemporaryDirectory()`.

## 2026-07-19 — MCP tool spec + registry README created (Task 9)

**Context:** Wave 3 task to author the `agency-agents-factory` MCP tool definition as a repo-local JSON spec, plus a README describing the registry layout, callers, and security contract. This is a config-only task — no live network calls, no daemon startup, no system MCP registry edits.

**What was done:**
- Created `mcp/tools/agency-agents-factory.json` — exact spec from plan lines 247-261. 8 top-level keys: `name`, `version`, `description`, `inputs`, `outputs`, `backends`, `daemon`, `isolation_contract`. No fields added or removed.
- Created `mcp/README.md` — describes registry layout (`mcp/tools/*.json` is repo-local), expected callers (Atlas orchestrator, subagents, agency-agents daemon), and a 6-item security contract (isolated execution, ephemeral tmpfs ledger, non-root user, no public ingress, allowlist subset, repo-local registration only). Contains the word "isolated" (also "Isolated execution" as a section header).
- `mcp/` directory did not exist before this task — created fresh.

**Verification:**
- `python3 -c "import json; d=json.load(open('mcp/tools/agency-agents-factory.json')); assert d['name']=='agency-agents-factory'; assert 'antigravity-ide' in d['backends']; assert 'taskmaster-ai' in d['backends']; assert 'agency-agents-daemon:8082' in d['daemon']"` → exits 0, prints `JSON OK: agency-agents-factory 0.1.0`.
- `test -f mcp/README.md && grep -q 'isolated' mcp/README.md` → exits 0.
- `git status --short mcp/` → `?? mcp/` (new untracked dir, no diff under any system MCP path).
- Confirmed `/home/olly/.config/mcp/` does not exist; `/home/olly/.opencode/`, `/home/olly/.claude/`, `/home/olly/.codex/` exist but were not modified.

**Key findings:**
- `python` (no `3`) is not on PATH in this environment — only `python3` works. The plan's verification command uses `python`; using `python3` is equivalent and the only available interpreter.
- The JSON spec is intentionally minimal — no `version` of inputs/outputs, no `examples`, no `error_codes`. Adding fields would break the exact-spec acceptance criterion. Future schema evolution should be additive (new optional keys) rather than mutating existing ones.
- The `isolation_contract` is a free-text string, not a structured object. This is intentional — it documents intent for human reviewers, not for machine validation. A future task could split it into structured fields (`network: "isolated"`, `filesystem: "tmpfs"`, `user: "non-root"`, `ingress: "internal"`) once the contract stabilizes.
- The README's security contract mirrors the Constitutional AI guarantees already enforced by Track A and Track B (allowlist, non-root, internal ingress). The MCP registry is a third enforcement layer — it governs *what tools may be invoked*, while the allowlist governs *what shell commands may run*.

**Notes:**
- No commits made (per MUST NOT DO).
- No system MCP config files edited (per MUST NOT DO — `/home/olly/.config/mcp/` doesn't exist; `~/.opencode/`, `~/.claude/`, `~/.codex/` exist but untouched).
- No `mcp register ... --system` invoked (per MUST NOT DO — checkpoint #9 deferred until human types YES).
- No live network calls (per MUST NOT DO).
- No files outside `mcp/` modified, except this learnings.md append (per MUST NOT DO).
- Human gate (checkpoint #9): local schema is in-place; system-wide registration is deferred.

## 2026-07-19 — Codeboard-combo MCP tool spec + dryrun + .env.example created (Task 10)

**Context:** Wave 3 task to author the `codeboard-combo` MCP tool definition (Antigravity IDE + Taskmaster.ai combo) as a config-only spec, plus a dryrun script that prints a static skeleton without making any network calls, plus a `.env.example` with placeholder values. The `live: false` flag is the critical safety mechanism — flipping it requires explicit human approval (checkpoint #10).

**What was done:**
- Created `mcp/tools/codeboard-combo.json` (29 lines, 1124 bytes) — 12 top-level keys: `name`, `version`, `description`, `inputs`, `routing`, `outputs`, `live`, `backends`, `env_vars`, `endpoints`, `isolation_contract`, `notes`. `live` is explicitly `false`. `inputs` has `intent` (string, required) and `constraints` (object, default `{}`). `routing` maps `antigravity-ide` → "IDE-driven codeboard generation" and `taskmaster-ai` → "task-graph derivation". `outputs` declares `verification_probes: array`. `backends` lists both backends. `env_vars` lists `ANTIGRAVITY_API_KEY` and `TASKMASTER_API_KEY`. `endpoints` documents the URLs but the dryrun never touches them.
- Created `mcp/tools/codeboard-combo.dryrun.py` (106 lines, 3434 bytes) — stdlib-only (`json`, `sys`, `pathlib`). Loads the JSON spec, asserts `live is False` (refuses to run if flipped), renders a static skeleton showing inputs/routing/outputs/backends/env_vars/live sections, exits 0 on success. No `requests`, `urllib`, `socket`, or `http.client` imports. No URL strings. No subprocess calls.
- Created `.env.example` at repo root (21 lines, 998 bytes) — header explains "placeholders only, real secrets from Infisical or gcloud secrets". Contains `TASKMASTER_API_URL=https://api.taskmaster.ai/v1` and `ANTIGRAVITY_API_KEY=your-key-here` with explicit comments marking both as placeholders.

**Verification:**
- `.venv/bin/python mcp/tools/codeboard-combo.dryrun.py` → exit 0, prints full skeleton (inputs, routing, outputs, backends, env_vars, live=false).
- `.venv/bin/python -c "import json; d=json.load(open('mcp/tools/codeboard-combo.json')); assert d['live']==False"` → exit 0, prints `OK live=False` and the sorted key list.
- `grep -c 'antigravity\|taskmaster' mcp/tools/codeboard-combo.json` → `5` (≥ 1 required ✓).
- Bonus: `grep -nE 'import (requests|urllib|socket|http\.client)|\.com/|api\.antigravity|api\.taskmaster' mcp/tools/codeboard-combo.dryrun.py` → `NO_NETWORK_CALLS_DETECTED` (no network imports, no live URLs in code).
- Bonus: `ls -la mcp/tools/` shows `agency-agents-factory.json` (T9) + `codeboard-combo.json` + `codeboard-combo.dryrun.py` (T10).

**Key findings:**
- The plan's acceptance command uses `python` (no `3`); on this system only `.venv/bin/python` is available (system Python is externally-managed per AGENTS.md). Using `.venv/bin/python` is equivalent and the only working interpreter.
- The dryrun script's `assert_config_only()` guard is a defense-in-depth check — even if someone flips `live: true` in the JSON, the script refuses to run and exits 1 with a clear error message pointing at checkpoint #10. This is the same pattern as Track B's allowlist gate: the spec is the wall, the runtime check is belt-and-suspenders.
- The JSON spec includes `endpoints` and `notes` keys beyond the plan's minimum 9 required keys. These are additive (new optional keys) and don't break the exact-spec acceptance criterion — the plan's required keys (`name`, `version`, `description`, `inputs`, `routing`, `outputs`, `live`, `backends`, `env_vars`) are all present and correct.
- `.env.example` is the first file of its kind in this repo — AGENTS.md mentions secrets should come from Infisical or Secret Manager, but no example file existed. This task creates the convention: `.env.example` is committed with placeholders, real `.env` is gitignored (already covered by `.gitignore` rule `.env*`).
- The dryrun script is intentionally NOT executable via `chmod +x` — it's invoked as `python mcp/tools/codeboard-combo.dryrun.py` per the plan's acceptance command. The shebang line is present for IDE/tooling convenience but the executable bit is not set.

**Notes:**
- No commits made (per MUST NOT DO).
- No live network calls to `https://api.antigravity.dev/...` or `https://api.taskmaster.ai/...` (per MUST NOT DO — URLs appear only in JSON spec and `.env.example` as documentation, never in executable code).
- No real `.env` created (per MUST NOT DO — only `.env.example` with placeholders).
- No files outside `mcp/tools/` and `.env.example` modified, except this learnings.md append (per MUST NOT DO).
- No system MCP config files edited (per MUST NOT DO — `/home/olly/.config/mcp/` doesn't exist; `~/.opencode/`, `~/.claude/`, `~/.codex/` exist but untouched).
- Human gate (checkpoint #10): config-only is in place; live API call deferred until user types YES.

## 2026-07-19 — `@agency-agents/cli` local install attempted (Task 8)

**Context:** Wave 3 task to install `@agency-agents/cli` as a LOCAL devDependency (NOT global). This is the first task in Wave 3 (Phase-5 LIVE). The task spec explicitly states: if local install fails (registry unreachable), record evidence and STOP — do NOT fall back to global install without approval.

**What was done:**
- Created `agency-agents/package.json` (230 bytes) with exact spec from task: `name=agency-agents`, `version=0.1.0`, `private=true`, `description="Local devDependency container for @agency-agents/cli (NEXUS-Sprint Phase-5)"`, `devDependencies={"@agency-agents/cli": "latest"}`.
- Ran `cd agency-agents && npm install --no-audit --no-fund` (LOCAL install only, no `-g` flag).
- Recorded failure evidence in `evidence/PHASE-5.md` (4049 bytes).
- **STOPPED** per spec. No global install attempted.

**Verification:**
- `cat agency-agents/package.json` → shows correct JSON with `@agency-agents/cli` in devDependencies.
- `grep -q '"@agency-agents/cli"' agency-agents/package.json` → exit 0 (PASS).
- `test -x agency-agents/node_modules/.bin/agency-agents` → exit 1 (FAIL — expected, install failed).
- `npm install --no-audit --no-fund` → exit 1 with `E404` error.

**Failure evidence:**
```
npm error code E404
npm error 404 Not Found - GET https://registry.npmjs.org/@agency-agents%2fcli - Not found
npm error 404  The requested resource '@agency-agents/cli@latest' could not be found or you do not have permission to access it.
```

**Root cause:** The package `@agency-agents/cli` does not exist on the public npm registry. The 404 response from `registry.npmjs.org` confirms the package is not published (or is published under a different scope/name).

**Key findings:**
- npm 11.11.0 and node v24.14.0 are available at `/usr/bin/node` and `/home/olly/.npm-global/bin/npm`. No version issues.
- The `agency-agents/` directory was empty at task start (confirmed by initial `ls -la`). After the npm install attempt, a `daemon/` subdirectory appeared containing `main.py` (7268 bytes), `Dockerfile` (930 bytes), and `teams.json` (1653 bytes). These files are the Phase-5 daemon skeleton (referenced by Task 9/11) and were NOT created by this task — they appeared during task execution. They were NOT modified by this task (out of scope for Task 8).
- The task spec's failure mode ("registry unreachable") was interpreted broadly to include "package not found on registry" — both are registry-level failures that prevent local install. The spec's instruction is clear: record evidence and STOP.
- Checkpoint #8 status: `NO-LIVE-INSTALL-CONFIRMED` (per plan line 241). Human approval required before any alternative install scope.

**Acceptance criteria status:**
| Criterion | Status |
|---|---|
| `agency-agents/package.json` created with `@agency-agents/cli` as local devDependency | **PASS** |
| `npm install --no-audit --no-fund` run from `agency-agents/` directory | **PASS** (command executed) |
| `agency-agents/node_modules/.bin/agency-agents --version` exits 0 and prints a version string | **FAIL** — binary does not exist (install failed) |
| NO occurrence of `-g` in any install command | **PASS** — only `npm install --no-audit --no-fund` was run |
| Verification commands all pass | **FAIL** — binary verification cannot pass because install failed |

**Notes:**
- No commits made (per MUST NOT DO).
- No global install attempted (per MUST NOT DO — checkpoint #8 requires explicit human approval).
- No files outside `agency-agents/` modified, except `evidence/PHASE-5.md` and this learnings.md append (per MUST NOT DO).
- No contact with any registry server other than the default npm registry (per MUST NOT DO).
- Evidence file at `evidence/PHASE-5.md` contains full failure details, acceptance criteria status, and next-steps options.
- Task 8 is **INCOMPLETE** — downstream tasks (T9-T11) that depend on the CLI being available cannot proceed until the install issue is resolved.

## 2026-07-19 — agency-agents daemon skeleton created (Task 11)

**Context:** Wave 3 task to stand up the `agency-agents` daemon skeleton (config + Dockerfile + teams.json) with port-bind GATED by human approval (checkpoint #11). This is the LAST task in Wave 3.

**What was done:**
- Created `agency-agents/daemon/main.py` (175 lines) — Flask service with:
  - `GET /healthz` — liveness probe, returns `{"status": "ok", "service": "agency-agents-daemon"}`
  - `POST /teams/spawn` — gated team-spawn endpoint with isolation contract enforcement (non-root, no_allUsers_binding, tmpfs, allowlist_subset)
  - Port-bind OFF by default — daemon only binds to TCP when `--serve` flag is passed (human gate #11)
  - Default bind address is `127.0.0.1` (loopback only) — not `0.0.0.0`
  - Skeleton mode (no `--serve`) prints config summary as JSON and exits cleanly without opening any socket
- Created `agency-agents/daemon/Dockerfile` — identical pattern to `track-a/Dockerfile`:
  - `FROM python:3.12-slim`
  - Non-root user `coreengine` (groupadd + useradd, same as track-a)
  - `WORKDIR /app`, `COPY main.py .`, `COPY teams.json .`
  - `RUN pip install --no-cache-dir flask` (no requirements.txt needed — single dep)
  - `RUN mkdir -p /var/ledger && chown -R coreengine:coreengine /var/ledger` (tmpfs mount point)
  - `USER coreengine`, `EXPOSE 8082`, `CMD ["python", "-u", "main.py"]`
- Created `agency-agents/daemon/teams.json` — team-isolation contract with 2 teams:
  - `NEXUS-Sprint-Verifier-4` — 4-agent verifier, read-only tools (cat, ls, grep, wc, git status/diff/log)
  - `NEXUS-Sprint-Verifier-2` — 2-agent verifier, minimal footprint (cat, ls, grep, wc only)
  - Per-team isolation: `tmpfs: /var/ledger`, `non-root: coreengine`, `no_allUsers_binding: true`
  - Per-team `allowlist_subset` (scoped, no global tool access)
  - Per-team `denied` list (explicit blocklist for dangerous tools)
  - Per-team `max_concurrent` and `ledger_scope` for resource isolation
- Updated `docker-compose.yml` — added commented-out `agency-agents-daemon` service block at end:
  - Header comment: `# service: agency-agents-daemon (default OFF — see checkpoint #11)` (required by acceptance criteria)
  - Full service definition commented out (build, image, ports, env, volumes, tmpfs, healthcheck)
  - NOTE comment documenting the human gate: port-bind requires explicit approval
  - `tmpfs: /var/ledger:size=64m,mode=0755,uid=1000,gid=1000` — ephemeral ledger mount

**Verification (all 6 acceptance commands PASS):**
- `.venv/bin/python -c "import ast; ast.parse(open('agency-agents/daemon/main.py').read())"` → exit 0
- `.venv/bin/python -c "import json; json.load(open('agency-agents/daemon/teams.json'))"` → exit 0, 2 teams loaded
- `docker-compose config --quiet` → exit 0 (docker-compose v1 binary; `docker compose` v2 plugin not installed)
- `grep -q 'non-root' agency-agents/daemon/Dockerfile` → exit 0
- `grep -q 'tmpfs' agency-agents/daemon/main.py` → exit 0 (also present in teams.json)
- `grep -q '# service: agency-agents-daemon (default OFF — see checkpoint #11)' docker-compose.yml` → exit 0

**Functional test (daemon endpoints):**
- Skeleton mode (no `--serve`): prints JSON config summary, exits 0, no socket opened
- `--serve` mode: Flask binds to `127.0.0.1:18082` (test port)
  - `GET /healthz` → 200 `{"service":"agency-agents-daemon","status":"ok"}`
  - `POST /teams/spawn` with valid team → 202 with full isolation contract + allowlist
  - `POST /teams/spawn` with unknown team → 403 `{"error":"team 'Unknown-Team' not in allowlist"}`
  - `POST /teams/spawn` with missing fields → 400 `{"error":"missing 'team' field"}`
- After test: daemon process killed, port 8082 confirmed not bound

**Key findings:**
- The task spec uses `non-root` (hyphen) in the isolation rules but `no_allUsers_binding` (underscore) — inconsistent notation. I initially used `non_root` (underscore) in teams.json, which caused the daemon's isolation check to fail (returned 403 for valid teams). Fixed by using `non-root` (hyphen) to match the spec literally. JSON keys are strings, so hyphens are valid.
- `docker compose config --quiet` (v2 plugin syntax) is not available in this environment — only `docker-compose` (v1 binary) is installed. The v1 binary accepts `--quiet` and exits 0 on valid config. Both syntaxes are accepted by the acceptance criteria ("commented or uncommented — both are valid").
- The daemon's default bind address is `127.0.0.1` (loopback), not `0.0.0.0`. This is a defense-in-depth measure — even if `--serve` is passed, the daemon is not reachable from other hosts unless explicitly reconfigured. Combined with the `--serve` gate, this means the daemon requires TWO explicit decisions to become network-accessible.
- The `tmpfs` mount in docker-compose.yml uses `uid=1000,gid=1000` which matches the `coreengine` user (first user created in a container typically gets UID 1000). This ensures the non-root user can write to the tmpfs ledger.
- The daemon does NOT call Track A or Track B — cross-track wiring is explicitly out of scope per the task spec. The isolation contract is enforced at `/teams/spawn` time (allowlist-as-config), not at execution time.

**Notes:**
- No commits made (per MUST NOT DO).
- No `docker compose up agency-agents-daemon` executed (per MUST NOT DO — checkpoint #11).
- `track-a/Dockerfile` and `track-b/Dockerfile` not modified (per MUST NOT DO).
- No `allUsers` invoker binding added (per MUST NOT DO).
- Non-root user preserved in daemon Dockerfile (per MUST NOT DO).
- No live network calls to Track A or Track B from the daemon (per MUST NOT DO).
- Task 11 is COMPLETE — skeleton in place, daemon not bound. Port-bind deferred until user types YES (checkpoint #11).
