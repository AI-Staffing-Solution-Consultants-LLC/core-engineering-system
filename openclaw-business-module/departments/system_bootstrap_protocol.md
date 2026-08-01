# System Bootstrap Protocol — Department Scaffold Loop

The creation loop specification for scaffolding each of the 12 departmental OpenClaw Business Modules. This protocol is executed once per department across 4 sequential phases (Phase 1: departments 01-03, Phase 2: 04-06, Phase 3: 07-10, Phase 4: 11-12). Every scaffold run follows the same 7-stage pipeline: verify pre-conditions, branch, scaffold, verify gates, merge, advance, and recover on failure.

---

## Section 1: Pre-flight Checks

Before starting scaffolding for ANY department, the following must all return clean. If any check fails, abort and resolve the issue before retrying.

| # | Check | Command | Expected Result |
|---|-------|---------|-----------------|
| 1 | Current branch is `dev` | `git branch --show-current` | Output must be exactly `dev` |
| 2 | Working tree is clean | `git status --porcelain` | Must be empty (zero lines of output) |
| 3 | Docker daemon is running | `docker compose config --quiet` | Exit code 0 (validates compose syntax only; no containers are started) |
| 4 | Target directory does not exist | `test ! -d openclaw-business-module/departments/<dept-slug>` | Exit code 0 (directory must not already exist; scaffolding is a create operation, not an update) |
| 5 | Template directory exists | `test -d openclaw-business-module/departments/_template` | Exit code 0 (template directory created by Task 5 in Wave 2 before any scaffold runs) |
| 6 | Agent skills exist on disk | Verify each agent's `skill_ref` path from `ops_architecture.md` Section 11 mapping table resolves to a file using `test -f` | Every path must exist. If a skill file is missing, abort this department and document the gap. |
| 7 | Required spec files exist | `test -f openclaw-business-module/departments/openclaw_departments.md && test -f openclaw-business-module/departments/ops_architecture.md && test -f openclaw-business-module/departments/master_operational_directive.md` | Exit code 0 (all three specification documents must be present before scaffolding begins) |

If any check in rows 1-5 or 7 fails, stop. The protocol does not proceed with a dirty state. Row 6 (agent skill verification) generates a report: missing skills are documented but the department can still proceed if and only if the missing agent is non-critical (the department roster in `openclaw_departments.md` includes a note that the agent is optional). Critical agents must have their skill files on disk.

---

## Section 2: Git Workflow

Every department scaffold begins from a fresh `feature/deploy-` branch cut from the tip of `dev`.

```bash
git checkout dev
git pull origin dev
git checkout -b feature/deploy-<department-slug>
```

**Branch naming convention:** The prefix is always `feature/deploy-`. The suffix is the department slug exactly as it appears in `openclaw_departments.md`. Examples:

| Department Slug | Branch Name |
|---|---|
| 01-infrastructure-devops-sre | `feature/deploy-01-infrastructure-devops-sre` |
| 02-software-engineering-architecture | `feature/deploy-02-software-engineering-architecture` |
| 03-quality-assurance-testing | `feature/deploy-03-quality-assurance-testing` |
| ... | ... |
| 12-finance-legal-hr-operations | `feature/deploy-12-finance-legal-hr-operations` |

After creating the branch, validate it exists and you are on it:

```bash
git branch --show-current
# Must output: feature/deploy-<department-slug>
```

If the branch creation fails (e.g., a branch by that name already exists), delete the stale branch first:

```bash
git branch -D feature/deploy-<department-slug>
git checkout -b feature/deploy-<department-slug>
```

Only proceed to scaffold once the branch is confirmed and you are checked out on it.

---

## Section 3: Scaffold Steps

Execute these 10 steps in order. Do not skip or reorder. Each step is atomic: if a step fails, stop, diagnose, fix, then re-run from that step. Steps 1-9 are performed by the agent; Step 10 is a verification checkpoint.

### Step 1: Create Department Directory

```bash
mkdir -p openclaw-business-module/departments/<dept-slug>
```

### Step 2: Copy Template Files

```bash
cp openclaw-business-module/departments/_template/* openclaw-business-module/departments/<dept-slug>/
```

The template directory (`_template/`) is the reusable department module skeleton created by Task 5. It contains exactly 10 files: `Dockerfile`, `requirements.txt`, `main.py`, `agents.json`, `paperclip-config.json`, `hermes-gateway.json`, `redis-client.json`, `viking-rag.json`, `.env.example`, `README.md`.

### Step 3: Populate `.env.example`

Replace these placeholders with department-specific values:

| Token | Replacement | Source |
|-------|-------------|--------|
| `<Name>` | Full department name (e.g., `"Infrastructure DevOps SRE"`) | `openclaw_departments.md` department heading |
| `<slug>` | Department slug (e.g., `01-infrastructure-devops-sre`) | `openclaw_departments.md` department heading |
| `81<NN>` | Assigned port number | Port assignment table in `ops_architecture.md` Section 8. Ports are 8101 through 8112, one per department. Department 01 gets 8101, department 02 gets 8102, and so on through department 12 at 8112. |

### Step 4: Populate `agents.json`

Replace the placeholder `agents` array (`[{...}]`) with the actual agent roster for this department from `openclaw_departments.md`. Each agent entry must include:

- `id`: The agent identifier (from the department's agent list in `openclaw_departments.md`)
- `skill_ref`: The filesystem path to the agent's skill definition file. **Do not derive paths from agent IDs.** Use the exact path from the mapping table in `ops_architecture.md` Section 11. Example: an agent `devops-automator` maps to skill_ref `.agents/skills/engineering-devops-automator/SKILL.md`.

### Step 5: Populate `paperclip-config.json`

Replace stage agent placeholders with the appropriate agents for each EIM (Enterprise Interface Module) stage:

| Stage | Agent to Assign | Selection Rule |
|-------|-----------------|----------------|
| `ingest` | Primary intake agent | The agent best suited to receive inbound messages or triggers for this department. For most departments, this is the agent whose domain most closely matches the department's core function. |
| `process` | Core processing agent(s) | One or more agents responsible for the department's main work. This is typically the largest agent group in the department roster. |
| `validate` | Quality/verification agent | An agent with reviewing, testing, or compliance responsibilities. Departments with a `code-reviewer`, `qa-automation-engineer`, or `it-service-manager` should assign one here. |
| `output` | Outbound/delivery agent | The agent that communicates results to other departments via Hermes queues. |

Selections are documented per department in `openclaw_departments.md` under each department's "Communicates with" section.

### Step 6: Populate `hermes-gateway.json`

Replace the queue name with the department-prefixed queue:

```json
"queue_name": "queue.<dept-slug>"
```

Example: for department `01-infrastructure-devops-sre`, the queue name is `queue.01-infrastructure-devops-sre`.

### Step 7: Populate `redis-client.json`

Replace `<dept-slug>` in the `state_keys` block with the actual department slug. The key pattern is:

```
state:<dept-slug>:*
```

Example: `state:01-infrastructure-devops-sre:*`

### Step 8: Populate `viking-rag.json`

No slug-specific changes are required. The viking-rag configuration uses environment variables for path resolution. Verify that the `viking://` paths in the file match the template defaults. If any path contains `<dept-slug>`, commit the file with the placeholder replaced. If none contain it, the file is correct as-is from the template.

### Step 9: Populate `README.md`

Replace all placeholders in the template README with department-specific values drawn from `openclaw_departments.md`:

| Placeholder | Source |
|-------------|--------|
| Department name | `openclaw_departments.md` heading |
| Phase number and name | Phase table in `openclaw_departments.md` Overview section |
| Department description | One-paragraph description under the department heading |
| Agent roster (list) | Agent list with roles from `openclaw_departments.md` |
| Dependencies | Dependencies section in `openclaw_departments.md` |
| Communication map | "Communicates with" section in `openclaw_departments.md` |

### Step 10: Verify No Placeholders Remain

```bash
grep -r "PLACEHOLDER" openclaw-business-module/departments/<dept-slug>/
```

This command must return zero matches (exit code 1, not 0). If any `PLACEHOLDER` strings are found, go back and populate the file where it appears, then re-run until clean.

---

## Section 4: Verification Gates

Before the department branch can be merged, all 8 gates must pass. Run these inside the department directory (`openclaw-business-module/departments/<dept-slug>/`).

### Gate 1: JSON Validation

Every `.json` file must parse cleanly:

```bash
for f in agents.json paperclip-config.json hermes-gateway.json redis-client.json viking-rag.json; do
    python -c "import json; json.load(open('$f'))" || echo "FAILED: $f"
done
```

If any file fails, inspect it. Common causes: trailing commas in the agents array, unescaped double quotes inside string values, or incorrect key names. Fix the scaffolded file directly (do not modify the `_template/` source).

### Gate 2: Dockerfile Structure

```bash
grep -q "FROM python:3.12-slim" Dockerfile \
  && grep -q "coreengine" Dockerfile \
  && grep -q "EXPOSE" Dockerfile \
  && grep -q "CMD python -u main.py" Dockerfile
```

All four conditions must pass. This ensures the Dockerfile follows the established pattern: Python 3.12 slim base image, non-root `coreengine` user, exposed port declaration, and dev-server entrypoint matching the track-a/track-b convention.

### Gate 3: File Count

```bash
ls -1 | wc -l
```

Must return exactly `10`. The ten required files are: `Dockerfile`, `requirements.txt`, `main.py`, `agents.json`, `paperclip-config.json`, `hermes-gateway.json`, `redis-client.json`, `viking-rag.json`, `.env.example`, `README.md`.

### Gate 4: No Placeholders or Incomplete Markers

```bash
grep -r "PLACEHOLDER\|TODO\|TBD" .
```

Must return zero matches. Any of these strings indicates unfinished work. Complete the file where the marker appears, then re-run.

### Gate 5: Agent Roster Match

```bash
# Count agents in agents.json
python -c "import json; print(len(json.load(open('agents.json'))['agents']))"

# Count agents in openclaw_departments.md for this department
# (manual cross-reference — the agent list is in the department's section)
```

The agent count in `agents.json` must match the agent count listed for this department in `openclaw_departments.md`. If counts differ, a skill_ref path may be missing an agent, or an extra agent may have been added. Reconcile by checking the department roster in the spec file.

### Gate 6: Queue Name

```bash
python -c "import json; d=json.load(open('hermes-gateway.json')); assert d['queue_name'] == 'queue.<dept-slug>', f'Expected queue.<dept-slug>, got {d[\"queue_name\"]}'; print('OK')"
```

The queue name must be exactly `queue.<dept-slug>` with no extra spaces, hyphens in the wrong place, or character substitutions.

### Gate 7: Port Assignment

```bash
grep -q "PORT=<expected-port>" .env.example
```

The port must match the assignment from `ops_architecture.md` Section 8. Ports are unique per department (8101-8112). Department 01 gets 8101, 02 gets 8102, and so on. Verify no two departments share the same port.

### Gate 8: Container Foundation

```bash
docker compose config --quiet
```

This validates that the `docker-compose.yml` at the repository root still parses correctly with the new department directory present, and that future compose entries (Task 18) will not conflict with existing configuration. No containers are started.

If all 8 gates pass, the department scaffold is complete and ready for merge. Record the result as an evidence file:

```bash
echo "ALL 8 VERIFICATION GATES PASSED for <dept-slug> at $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > ../../.omo/evidence/enterprise-openclaw-deployment/task-<N>-<dept-slug>.txt
```

---

## Section 5: Merge Criteria

Beyond the verification gates in Section 4, the following criteria must also be satisfied before merging:

1. **All 8 verification gates passed** (Section 4) with evidence recorded.
2. **No TODO/TBD in any file** in the department directory. Confirmed by Gate 4.
3. **Agent roster matches `openclaw_departments.md`** exactly. Confirmed by Gate 5.
4. **All `skill_ref` paths resolve to existing files on disk.** Each path in the `agents.json` skill_ref field must point to a file that exists. Verify with: `python -c "import json, os; agents=json.load(open('agents.json'))['agents']; [assert os.path.exists(a['skill_ref']), f'Missing: {a[\"skill_ref\"]}' for a in agents]; print('All skill_ref paths exist')"`
5. **`REDIS_URL` and `OPENVIKING_URL` present in `.env.example`.** These are Protocol A (Hermes bus via Redis) and Protocol B (knowledge retrieval via OpenViking RAG) compliance requirements. Verify with:
   ```bash
   grep -q "REDIS_URL" .env.example && grep -q "OPENVIKING_URL" .env.example
   ```

If ANY criterion fails, the department branch does not merge. Return to Section 3 (Scaffold Steps) for the failing file, fix it, then re-run Section 4 verification gates.

---

## Section 6: Merge and Advance

Once all verification gates pass and all merge criteria are satisfied:

```bash
git add openclaw-business-module/departments/<dept-slug>/
git commit -m "feat(enterprise): scaffold <dept-slug> department module"
git checkout dev
git merge feature/deploy-<dept-slug>
```

After a successful merge, advance to the next department in sequence:

| Current Department | Next Department |
|---|---|
| 01-infrastructure-devops-sre | 02-software-engineering-architecture |
| 02-software-engineering-architecture | 03-quality-assurance-testing |
| 03-quality-assurance-testing | 04-ai-data-multi-agent |
| 04-ai-data-multi-agent | 05-security-privacy-compliance |
| 05-security-privacy-compliance | 06-executive-strategy-pmo |
| 06-executive-strategy-pmo | 07-product-research-innovation |
| 07-product-research-innovation | 08-sales-revenue-operations |
| 08-sales-revenue-operations | 09-search-growth-paid-media |
| 09-search-growth-paid-media | 10-marketing-content-brand |
| 10-marketing-content-brand | 11-customer-success-support |
| 11-customer-success-support | 12-finance-legal-hr-operations |
| 12-finance-legal-hr-operations | (end of scaffold — proceed to Task 18) |

Feature branches can accumulate locally. Merge them one at a time in numeric order. Do not merge branches out of sequence: each department's dependencies must be satisfied before it enters the merge queue.

### Push Control

**`git push` is a gated operation.** Every push command must be annotated with `[HUMAN-APPROVAL-REQUIRED]` on the preceding line. The annotation serves as an explicit signaling mechanism that human confirmation is required before the push executes. No push proceeds without this annotation in the commit log or task output.

```
# [HUMAN-APPROVAL-REQUIRED]
# git push origin dev
```

The push command itself must remain commented out until approval is given. This mechanism ensures that no code reaches the remote repository without human review, regardless of how many departments have been scaffolded or verified.

---

## Section 7: Error Recovery

When a verification gate (Section 4) or merge criterion (Section 5) fails, follow the recovery path for the specific failure mode.

### Recovery: JSON Parse Error

**Symptom:** `python -c "import json; json.load(open('<file>'))"` fails with a `JSONDecodeError`.

**Diagnosis:** Open the failing file. Look for:
- Trailing commas in arrays or objects (e.g., `{"name": "agent",}` or `["a", "b",]`)
- Unescaped double quotes inside string values (e.g., `"description": "He said "hello""`)
- Incorrect key names (check against the template for the expected JSON structure)

**Fix:** Edit the scaffolded file directly. Never modify the `_template/` source. Re-run the JSON validation gate.

### Recovery: Missing File

**Symptom:** File count gate (Gate 3) returns fewer than 10.

**Diagnosis:** List the directory contents: `ls openclaw-business-module/departments/<dept-slug>/`. Compare against the required file list in Gate 3.

**Fix:** Re-copy the missing file from the template:
```bash
cp openclaw-business-module/departments/_template/<missing-file> openclaw-business-module/departments/<dept-slug>/
```
Then re-populate all placeholders in the copied file (refer to Section 3, the step corresponding to that file).

### Recovery: Agent Count Mismatch

**Symptom:** Gate 5 fails: agent count in `agents.json` does not match `openclaw_departments.md`.

**Diagnosis:** Cross-reference the agent list in `openclaw_departments.md` for this department against the `agents` array in `agents.json`. Check for:
- Missing agent entries (agents listed in the spec but absent from JSON)
- Extra agent entries (agents in JSON that don't belong to this department)
- Typographical errors in agent IDs (e.g., `devops-automater` instead of `devops-automator`)

**Fix:** Edit `agents.json` to match the spec roster exactly. If an agent appears in the spec but has no skill file on disk, document the gap and either mark the agent as optional in the roster or abort the department.

### Recovery: Queue Name Mismatch

**Symptom:** Gate 6 fails: `hermes-gateway.json` queue_name does not match `queue.<dept-slug>`.

**Diagnosis:** Open `hermes-gateway.json` and inspect the `queue_name` field. Compare against the expected value.

**Fix:** Correct the `queue_name` field to exactly `queue.<dept-slug>`. The pattern is rigid: `queue.` prefix, department slug, no extra characters.

### Recovery: docker compose config Failure

**Symptom:** Gate 8 fails: `docker compose config --quiet` exits non-zero.

**Diagnosis:** Run the command without `--quiet` to see the error output:
```bash
docker compose config
```
Common causes:
- YAML syntax error in the main `docker-compose.yml` (Task 18 entries)
- Duplicate port assignment for the department's service
- Uncommented service entry referencing a non-existent build context

**Fix:** If the error is in the main `docker-compose.yml`, fix it there. If port assignment is duplicated, check which department has the conflicting port and reassign. If a build context is wrong, verify the directory path matches the scaffolded department slug.

### Recovery: Dockerd Not Running

**Symptom:** Gate 8 fails with "Cannot connect to the Docker daemon."

**Fix:** Start the Docker daemon (`sudo systemctl start docker` or equivalent) and re-run. If Docker cannot be started (e.g., in a restricted CI environment), skip Gate 8 and document that the skip occurred, with the reason. The gate must be run before the final merge.

### Recovery: Blocking Failure (3-Attempt Rule)

If any gate cannot be resolved after 3 fix-and-retry cycles:

1. **Abort the merge** for this department.
2. **Document the failure:** write a file at `.omo/evidence/enterprise-openclaw-deployment/task-<N>-<dept-slug>-BLOCKED.txt` containing the gate that failed, the attempts made, and the unresolved error message.
3. **Advance to the next department** in the sequence.
4. **Revisit the blocked department** after all other departments in the current phase have been scaffolded and merged. A fresh retry from a clean dev branch often resolves issues caused by accumulated state.

### Recovery: Full Rollback

If the department branch must be abandoned entirely (e.g., the scaffold is corrupted beyond repair, or the department spec changes mid-scaffold):

```bash
git checkout dev
git branch -D feature/deploy-<dept-slug>
```

Then restart the protocol from Section 1 (Pre-flight Checks) with a fresh branch. Delete any partial scaffold directory before re-branching:

```bash
rm -rf openclaw-business-module/departments/<dept-slug>
```

---

## Execution Sequence Summary

```
Section 1: Pre-flight Checks  →  PASS  →  Section 2: Git Workflow
                                    ↘  FAIL  →  Fix, then retry from Section 1

Section 2: Git Workflow  →  Section 3: Scaffold Steps (10 steps in order)

Section 3: Scaffold Steps  →  Section 4: Verification Gates (8 gates)

Section 4: Verification Gates  →  ALL PASS  →  Section 5: Merge Criteria
                              →  ANY FAIL  →  Section 7: Error Recovery → retry

Section 5: Merge Criteria  →  ALL PASS  →  Section 6: Merge and Advance
                          →  ANY FAIL  →  Section 7: Error Recovery → retry

Section 6: Merge and Advance  →  Next department (repeat from Section 1)
                             →  After department 12: proceed to Task 18 (docker-compose entries)
```

This protocol is executed once per department. All 12 departments follow the same loop. The protocol does not skip steps, does not merge early, and does not proceed with a failing gate.
