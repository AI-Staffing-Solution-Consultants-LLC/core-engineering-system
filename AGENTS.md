# AGENTS.md — Core Engineering System

Compact orientation for future OpenCode sessions.
For the full C-P-A design rationale, architecture diagram, and deployment walkthroughs, read `README.md`.

## Repo map (load-bearing files only)

| Path | What it actually is |
|---|---|
| `track-a/main.py` | Flask **Control Loop**, port 8080. Loads RAG corpus from `/rag/docs/*.md`, runs a ReAct loop, emits action requests to Track B. |
| `track-a/Dockerfile` | `python:3.12-slim`, non-root user `coreengine`. `CMD python -u main.py` (Flask dev server). |
| `track-b/main.py` | Flask **Actuator**, port 8081. Loads allowlist at startup, validates each tool call, executes in `subprocess.run(shell=True)` with a 15s timeout, output truncated to 8192 bytes. |
| `policy/tool-allowlist.txt` | One command per line. Empty/missing file causes Track B to reject every request. |
| `policy/*.rego` | `package core.constitutional` OPA rules. **Neither track evaluates Rego today** — these are documentation of intent. |
| `terraform/` | Cloud Run v2 + IAM + Secrets Manager + Monitoring. **No backend** configured; state lives locally in `terraform.tfstate`. |
| `docker-compose.yml` | Spins up both services, mounts `./policy` (ro) and ledger Docker volumes. References `./rag` (host dir), which **does not exist in this repo** and must be created locally — otherwise Track A logs a warning and runs with empty corpus. |
| `CEM_Update.txt` | One-shot reconciliation manifest (phases of porting into a larger `/AISSC_Cloud_Workspace/`). Treat as a roadmap document, not config. |
| `agency-agents/` | **Empty placeholder directory.** If a task references files inside it, the user has not populated it yet — don't author files there without asking. |

## Hard constraints — do not negotiate

These come from the project owner (`README.md` "Constraints" section + `terraform/*.tf`):

- **GCP project:** `aissc-core-engine-self-dep` only. Do not deploy anywhere else.
- **Region:** `us-central1` only.
- **Branch:** `dev` on `Tizzle716/core-engineering-system` only.
- **Cloud Run sizing:** `cpu=1 memory=512Mi min_instances=0 max_instances=1` (free tier). On quota errors drop to `256Mi`. Never go higher.
- **Auth:** Terraform sets `INGRESS_TRAFFIC_INTERNAL_ONLY` on both services. The gcloud deploy branch in `README.md` uses `--no-allow-unauthenticated`. **Never** add an `allUsers` invoker binding.
- **Service account** `core-engine-worker@<project>.iam.gserviceaccount.com`. Allowed roles: `roles/run.invoker`, `roles/secretmanager.secretAccessor`, `roles/logging.logWriter`, `roles/iam.serviceAccountTokenCreator`. Never `roles/owner` or `roles/editor`.
- **Secrets** must never be echoed in logs or commits. `.gitignore` blocks `.env*`, `*.key`, `*.pem`, `service-account.json`. Use Infisical or Secret Manager (`terraform/secrets.tf`) — not `gcloud secrets ... --data-file=...` without thinking.

## Day-to-day commands

```bash
# Local dev (from repo root)
docker compose up --build      # Track A → :8080, Track B → :8081

# Smoke checks
curl localhost:8080/healthz
curl localhost:8081/healthz
curl localhost:8081/allowlist  # what Track B will let through

# Drive the ReAct loop end-to-end
curl -X POST localhost:8080/plan \
  -H 'Content-Type: application/json' \
  -d '{"query":"why is latency high"}'
# Returns {"plan_id":..., "steps":[...]} — each step is a Track-B execution

# Read the tamper-evident ledger (per-day JSONL, SHA-256 chained)
curl 'localhost:8080/ledger?limit=20'
curl 'localhost:8081/healthz'  # B does not currently expose its own ledger

# Terraform (always run from repo root, not inside terraform/)
cd /home/olly/core-engineering-system
terraform -chdir=terraform init
terraform -chdir=terraform validate
terraform -chdir=terraform plan    # review before apply
```

## Things that will bite you

- **The Flask services run the dev server, not gunicorn.** `requirements.txt` lists `gunicorn==23.0.0` but the Dockerfile `CMD` is `python -u main.py` (which calls `app.run()`). Don't "fix" this without also wiring a proper WSGI entry — it is intentional during scaffolding.
- **`search_rag()` and `form_hypothesis()` are rule-based placeholders.** `search_rag` is `content.lower().count(query.lower())` (substring occurrences, not embeddings). `form_hypothesis` keys on substrings `latency / crash / error / deploy / cpu / memory`; everything else returns `"Unknown anomaly; requires full diagnostic sweep."` Replacing either requires loading a vector store or LLM and is out of scope for trivial edits.
- **`policy/*.rego` is documentation, not enforcement.** Both Python tracks read these files (`load_policies()` in Track A) but never evaluate them. Wire-up is a future task.
- **Tool allowlist semantics in `track-b/main.py:is_allowed()`**: exact match OR `' '.startswith(allowed + ' ')`. So `kubectl get pods` matches `kubectl get pods` and `kubectl get pods -A`, but `kubectl get  pods` (double space) fails closed. Plain `kubectl get` (no second word) also fails — the allowlist currently has no `kubectl get` entry, only the specific subcommands.
- **Metacharacter blocklist:** `|`, `;`, `&`, `$(`, backtick, `>`, `<`, `${`, `&&`, `||`. Note this is not exhaustive — `subprocess.run(shell=True)` still interprets the rest of bash. The allowlist is the actual wall; metacharacters are belt-and-suspenders.
- **Ledger chains are independent per track.** Both tracks write to daily `ledger-YYYY-MM-DD.jsonl` files inside their own Docker volume. `_last_hash` reload on startup is per-process — verify chain integrity by reading `chain_hash` per entry; don't assume a single global chain across tracks.
- **`EXEC_TIMEOUT = 15` seconds** (Track B). Long-running commands will fail closed.
- **`terraform/variables.tf` defaults to literal `"placeholder-change-me"`** for both secret vars. `terraform apply` with defaults succeeds and stores that string into Secret Manager. Always pass real values via `-var` or `TF_VAR_*` env vars.
- **`TRACK_A_URL` env var** is set in `docker-compose.yml` for Track B but **not used by the Python code** (Track B does not currently call Track A back). It was removed from Terraform earlier; the compose entry is dead but harmless.
- **Type-info mismatch with terraform.tf:** `terraform/cloudrun.tf` comments say "Start the Flask app via gunicorn" — that's the plan, not the current reality (see first bite above).

## When you change code

- **Env var rename** (`LEDGER_PATH`, `TRACK_B_URL`, `RAG_CORPUS_PATH`, `POLICY_DIR`, `TOOL_ALLOWLIST`): update the Python file *and* the matching `docker-compose.yml` env block *and* the `env {}` block in `terraform/cloudrun.tf`. They all three must agree.
- **Adding an allowlisted tool:** append one line to `policy/tool-allowlist.txt`, then restart Track B (the allowlist is loaded once via `load_allowlist()` at module startup, not per request).
- **Adding an OPA rule:** drop a `*.rego` file in `policy/` with `package core.constitutional`. It will be loaded by Track A but **not executed** unless you wire a real OPA engine into `track-a/main.py`.
- **No test harness, no linter config, no CI workflows.** Truthfulness gate: don't invent `pytest`, `ruff`, or GitHub Actions files unless the user asks — keep edits scoped.

## Verification (run before claiming done)

```bash
# 1. Compose parses
docker compose config --quiet

# 2. Terraform is valid
terraform -chdir=terraform validate

# 3. Services booted and reachable
docker compose up --build &
curl -fs localhost:8080/healthz
curl -fs localhost:8081/healthz

# 4. ReAct loop delivers steps end-to-end (proves Track A → Track B works)
curl -fs -X POST localhost:8080/plan \
  -H 'Content-Type: application/json' \
  -d '{"query":"why is latency high"}' \
  | jq '.steps | length'

# 5. Ledger evolved (chain hash field present)
curl -fs 'localhost:8080/ledger?limit=5' | jq '.entries[].chain_hash' | head -5

# Stop services
docker compose down
```

## What "blocked by mistake" looks like

- Deploy fails with `PERMISSION_DENIED` → service account lacks one of the roles in `iam.tf`. Re-verify; do not escalate to `roles/owner`.
- `docker compose up` exits with `Bind for 0.0.0.0:8080 failed` → previous run still bound. `docker compose down` first.
- `POST /plan` returns `{"error": "..."}` from Track B with HTTP 403 → one of Track B's three gates failed: tool not in allowlist, missing `reasoning_log_ref`, or prohibited metacharacter. The ledger entry under `type: "gate_denied"` has the exact reason.
- `Track A starting — 0 RAG docs` → `RAG_CORPUS_PATH` is empty/missing. Expected if `./rag/` doesn't exist locally. The service still serves requests.
</content>
</invoke>