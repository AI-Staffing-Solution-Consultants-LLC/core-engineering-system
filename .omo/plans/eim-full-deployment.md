# eim-full-deployment - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** A fully deployed multi-service mesh on Google Cloud Run with an interactive Web UI on Cloudflare Pages featuring live video avatar conversations, Telegram bot integration with safety checks, automated self-healing infrastructure, and a vector memory system that learns from every incident.

**Why this approach:** The codebase already has 9 working services with Dockerfiles, a comprehensive CI/CD pipeline, and 247 passing tests. We build the 3 missing pieces (.gcloudignore, deploy script, Web UI), add 2 safety integrations (Aura consistency check, self-remediation telemetry), populate the empty OpenViking memory plane, then deploy everything from a production branch.

**What it will NOT do:** It will not deploy to any project other than aissc-core-engine-self-dep, will not expose core services publicly, will not create directories under /AISSC_Cloud_Workspace/, and will not implement the OpenClaw business module beyond its placeholder scaffold.

**Effort:** XL
**Risk:** Medium — all credentials available, all services already have Dockerfiles, main work is integration and frontend assembly
**Decisions to sanity-check:** EIM Web UI is on Cloudflare Pages (not Cloud Run), telegram-bridge is the only public Cloud Run endpoint, production branch on AI-Staffing-Solution-Consultants-LLC (not Tizzle716, not dev).

Your next move: `$start-work eim-full-deployment`. Full execution detail follows below.

---

> TL;DR (machine): XL, Medium risk, 8 components in 5 waves — EIM Web UI on Cloudflare Pages, Telegram + Aura protocol, self-remediation telemetry, OpenViking RAG, deploy from production branch via deploy-gcr.sh

## Scope
### Must have
1. `.gcloudignore` at repo root — exclude node_modules, .git, .env*, terraform state, secrets
2. `deploy-gcr.sh` — master deploy script: enable APIs, deploy all 8 services (telegram public, rest internal)
3. `production` branch on `AI-Staffing-Solution-Consultants-LLC/core-engineering-system`
4. EIM Web UI on Cloudflare Pages at `cem.ai-staffing-solutions-consultants.online`: MediaPipe FaceLandmarker WASM, Tavus WebRTC avatar, secondary dashboard viewport, password-only access
5. Aura Consistency Protocol: Aura monitors Sheryl Telegram outputs, appends 🔴✔️ on ambiguity
6. Sheryl-Telegram 2-way bridge operational with live webhook
7. Inference smoketests: Aura, Malory, Krieger — structured routing, taskmaster list/add, tool execution
8. Self-remediation wired to Cloudflare/GCP telemetry + OpenViking RAG + Gemini Knowledge Steward
9. OpenViking memory plane populated with vector store configuration
10. All changes committed, pushed, deployed, with endpoint verification log

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Deploy to any GCP project other than `aissc-core-engine-self-dep`
- Deploy to any region other than `us-central1`
- Exceed free tier: `cpu=1, memory=512Mi, min-instances=0, max-instances=1`
- Add `allUsers` IAM binding to any internal service
- Grant `roles/owner` or `roles/editor`
- Echo secrets (Tavus key, Telegram token, Infisical creds) in logs or commits
- Deploy to `Tizzle716/core-engineering-system`
- Create directories under `/AISSC_Cloud_Workspace/` or `/CORE-Modules/`
- Implement OpenClaw business module beyond placeholder scaffold
- Modify Barry DO-Lobe container code

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after (existing 247 tests as baseline) + TDD for new Python code
- Framework: pytest (`.test/` harness), `wrangler dev` for Cloudflare Workers, `docker compose up --build` for integration
- Evidence: `.omo/evidence/eim-full-deployment/task-<N>-<slug>.<ext>`

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

```
Wave 1 (Foundation — all start immediately, no dependencies):
├── Task 1:  .gcloudignore creation
├── Task 2:  deploy-gcr.sh master deploy script
├── Task 3:  Production branch creation + remote setup
└── Task 4:  Aura Consistency Protocol (Sheryl + Aura + telegram-bridge)

Wave 2 (EIM Web UI — Cloudflare Pages):
├── Task 5:  Cloudflare Pages scaffold + password gate
├── Task 6:  MediaPipe FaceLandmarker WASM integration
├── Task 7:  Tavus WebRTC CVI avatar window
└── Task 8:  Secondary dashboard viewport (iframes for tokenomics, master-control)

Wave 3 (Integration & Smoketests):
├── Task 9:  Inference smoketests — Aura, Malory, Krieger
├── Task 10: Self-remediation → Cloudflare/GCP telemetry wiring
└── Task 11: OpenViking RAG memory plane + Gemini Knowledge Steward

Wave 4 (Deploy):
├── Task 12: Telegram webhook registration + live test
├── Task 13: Execute deploy-gcr.sh — full Cloud Run mesh deploy
└── Task 14: Endpoint verification log (all 8 services health-checked)

Wave FINAL (After ALL tasks — parallel reviews):
├── Task F1: Plan compliance audit
├── Task F2: Code quality review
├── Task F3: Real manual QA
└── Task F4: Scope fidelity check
```

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | None | None | 2, 3, 4 |
| 2 | None | 13 | 1, 3, 4 |
| 3 | None | 13 | 1, 2, 4 |
| 4 | None | 12 | 1, 2, 3 |
| 5 | None (design concepts from PC Interface) | 6, 7, 8 | None (Wave 2 serial) |
| 6 | 5 | 7, 8 | None |
| 7 | 5, 6 | 8 | None |
| 8 | 5, 6, 7 | None | None |
| 9 | 4 (Aura/Malory/Krieger must exist) | None | 10, 11 |
| 10 | None (self-remediation exists) | None | 9, 11 |
| 11 | None (openviking-memory/ is empty) | None | 9, 10 |
| 12 | 4 (Aura protocol), 13 (deploy must complete) | None | None |
| 13 | 2 (deploy-gcr.sh), 3 (production branch), 1-11 | 12, 14 | None |
| 14 | 13 | None | None |
| F1-F4 | 1-14 | None | All four in parallel |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. **Create `.gcloudignore` at repo root**
  What to do: Write `.gcloudignore` file at `/home/olly/core-engineering-system/.gcloudignore` with entries:
  ```
  node_modules/
  .git/
  .gitignore
  .env
  .env.*
  terraform/.terraform/
  terraform/*.tfstate
  terraform/*.tfstate.*
  terraform/.terraform.lock.hcl
  __pycache__/
  *.py[cod]
  *.pyc
  .venv/
  *.pem
  *.key
  service-account.json
  .DS_Store
  ledger-*/
  .omo/
  .wrangler/
  .pytest_cache/
  .ruff_cache/
  .test/
  tests/
  rag/
  policy/
  public/
  docs/
  ```
  Must NOT do: Include any file that is actually needed for deployment (track-a/, track-b/, executive-quartet/, self-remediation/, telegram-bridge/, agency-agents/, cloudflare/, src/, terraform/, cloudbuild.yaml, docker-compose.yml, README.md, wrangler.toml). Do not exclude .gcloudignore itself.
  Parallelization: Wave 1 | Blocked by: None | Blocks: None
  References: `.gitignore:1-40` (existing patterns), GCP docs: `https://cloud.google.com/sdk/gcloud/reference/topic/gcloudignore`
  Acceptance criteria: `test -f .gcloudignore`, `grep -q "node_modules" .gcloudignore`, file is valid (gcloud does not error on dry-run: `gcloud meta list-files-for-upload 2>&1 | head -5` does not show excluded dirs)
  QA: happy — `wc -l .gcloudignore` returns ≥ 15 lines; `grep -c "track-a" .gcloudignore` returns 0 (service dirs NOT excluded). failure — `grep ".env" .gcloudignore` returns ≥ 1 (env files excluded). Evidence: `.omo/evidence/eim-full-deployment/task-1-gcloudignore.txt`
  Commit: YES | `chore(deploy): add .gcloudignore — exclude dev artifacts from Cloud Run source deploy`

- [x] 2. **Create `deploy-gcr.sh` — master Cloud Run deploy script**
  What to do: Write executable `deploy-gcr.sh` at repo root that:
  1. `set -euo pipefail`
  2. Define: `PROJECT="aissc-core-engine-self-dep"`, `REGION="us-central1"`, `SERVICE_ACCOUNT="core-engine-worker@${PROJECT}.iam.gserviceaccount.com"`
  3. Enable APIs: `gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project=$PROJECT`
  4. Deploy Track A: `gcloud run deploy track-a-control-loop --source ./track-a --region=$REGION --project=$PROJECT --no-allow-unauthenticated --cpu=1 --memory=512Mi --min-instances=0 --max-instances=1 --ingress=internal --port=8080 --service-account=$SERVICE_ACCOUNT`
  5. Deploy Track B: same pattern, `--source ./track-b`, `--port=8081`
  6. Deploy Sheryl: `--source ./executive-quartet/sheryl`, `--port=8083`, internal-only
  7. Deploy Aura: `--source ./executive-quartet/aura`, `--port=8084`, internal-only
  8. Deploy Malory: `--source ./executive-quartet/malory`, `--port=8085`, internal-only
  9. Deploy Krieger: `--source ./executive-quartet/krieger`, `--port=8086`, internal-only
  10. Deploy Self-Remediation: `--source ./self-remediation`, `--port=8087`, internal-only
  11. Deploy Telegram Bridge: `--source ./telegram-bridge`, `--port=8088`, `--allow-unauthenticated` (ONLY public service)
  12. Print summary of all deployed service URLs: `gcloud run services list --project=$PROJECT --region=$REGION --format='table(name, status.address.url)'`
  Must NOT do: Add `--allow-unauthenticated` to any service except telegram-bridge. Do not hardcode secrets or tokens in the script. Do not deploy agency-agents-daemon.
  Parallelization: Wave 1 | Blocked by: None | Blocks: 13 (deploy execution)
  References: `README.md:1013-1047` (existing deploy commands), `cloudbuild.yaml:330-385` (Track A/B deploy patterns), `AGENTS.md` constraints section
  Acceptance criteria: `test -f deploy-gcr.sh && test -x deploy-gcr.sh`, `bash -n deploy-gcr.sh` exits 0 (syntax check), `grep -c "allow-unauthenticated" deploy-gcr.sh` returns exactly 1
  QA: happy — `grep "track-a-control-loop" deploy-gcr.sh` returns a line; `grep "telegram-bridge" deploy-gcr.sh` returns a line with `--allow-unauthenticated`. failure — dry-run validation: `grep -c "aissc-core-engine-self-dep" deploy-gcr.sh` returns ≥ 8 (every deploy targets correct project). Evidence: `.omo/evidence/eim-full-deployment/task-2-deploy-gcr.sh`
  Commit: YES | `feat(deploy): add deploy-gcr.sh — multi-service Cloud Run deploy script`

- [x] 3. **Create `production` branch and configure remote**
  What to do:
  1. Verify current branch is `dev`: `git branch --show-current`
  2. Fetch latest from origin: `git fetch origin`
  3. Verify remote exists: `git remote -v` shows `AI-Staffing-Solution-Consultants-LLC/core-engineering-system`
  4. If remote URL is still `Tizzle716/core-engineering-system`, update it: `git remote set-url origin https://github.com/AI-Staffing-Solution-Consultants-LLC/core-engineering-system.git`
  5. Create production branch from current dev: `git checkout -b production`
  6. Push to remote: `git push -u origin production`
  7. Verify branch exists on remote: `git ls-remote --heads origin production`
  Must NOT do: Delete or modify the `dev` branch. Force-push. Push to Tizzle716 remote.
  Parallelization: Wave 1 | Blocked by: None | Blocks: 13 (deploy from production)
  References: `.git/HEAD` (currently `ref: refs/heads/dev`)
  Acceptance criteria: `git branch --show-current` returns `production`, `git branch -r | grep origin/production` exits 0
  QA: happy — `git log --oneline -1` shows the same commit as dev. failure — `git remote get-url origin` contains `AI-Staffing-Solution-Consultants-LLC` (not Tizzle716). Evidence: `.omo/evidence/eim-full-deployment/task-3-production-branch.txt`
  Commit: N/A (branch creation, not a file commit) | Record branch SHA in evidence

- [x] 4. **Implement Aura Consistency Protocol — Sheryl Telegram output monitoring**
  What to do:
  1. Add `/ingest` endpoint to Sheryl (`executive-quartet/sheryl/main.py`) that accepts Telegram-parsed messages from telegram-bridge. Current gap: telegram-bridge forwards to `http://sheryl:8082/ingest` but Sheryl only has `/memory/store`, `/memory/query`, `/plan` — needs an `/ingest` route.
  2. Add Aura client to Sheryl: when Sheryl prepares a Telegram response, send the response text + context to Aura at `http://aura-agent:8084/consistency-check` for ambiguity analysis.
  3. Add `/consistency-check` endpoint to Aura (`executive-quartet/aura/main.py`): receives `{"response_text": "...", "context": {...}}`, performs keyword+semantic analysis for potential ambiguity (vague language, conflicting instructions, missing critical info), returns `{"ambiguous": true/false, "reason": "..."}`.
  4. In Sheryl's `/ingest` handler, after generating the Telegram response and receiving Aura's verdict: if `ambiguous: true`, append `🔴✔️` to the message text before sending via telegram-bridge `/send`.
  5. Add `/dashboard/last-responses` endpoint to Sheryl that returns the last 5 agent responses (for the master control dashboard referenced by the 🔴✔️ flag).
  6. Update telegram-bridge (`telegram-bridge/main.py`) to use correct Sheryl URL: `SHERYL_URL = os.environ.get("SHERYL_URL", "http://sheryl:8083/ingest")` (currently hardcoded to port 8082).
  Must NOT do: Break existing `/plan` or memory endpoints. Hard-code Telegram token in any file (use env var TELEGRAM_BOT_TOKEN only). Make Aura call blocking — use timeout=5s with graceful degradation.
  Parallelization: Wave 1 | Blocked by: None | Blocks: 9 (smoketests), 12 (telegram webhook)
  References: `executive-quartet/sheryl/main.py:1-356` (full Sheryl source), `executive-quartet/aura/main.py` (needs reading), `telegram-bridge/main.py:24` (SHERYL_URL default), `openclaw-business-module/INITIATION.md:75` (documents the /ingest gap), `eim-telegram-bridge.js:1-77` (Cloudflare Worker reference for Telegram routing)
  Acceptance criteria: `curl -X POST http://localhost:8083/ingest -H 'Content-Type: application/json' -d '{"chat_id": 123, "text": "deploy the new module", "from_id": 456}'` returns 200; `curl http://localhost:8083/dashboard/last-responses` returns JSON array with ≤ 5 entries; `curl -X POST http://localhost:8084/consistency-check -H 'Content-Type: application/json' -d '{"response_text": "I think maybe we could possibly consider deploying perhaps", "context": {}}'` returns `{"ambiguous": true, ...}`
  QA: happy — end-to-end: POST to telegram-bridge `/webhook` with a test message → Sheryl `/ingest` receives → Aura `/consistency-check` returns ambiguity verdict → if ambiguous, `🔴✔️` appended. failure — Aura unavailable: Sheryl `/ingest` still returns 200 (graceful degradation, no crash). Evidence: `.omo/evidence/eim-full-deployment/task-4-aura-consistency.txt`
  Commit: YES | `feat(quartet): Aura Consistency Protocol — Sheryl output monitored for ambiguity with 🔴✔️ flag`

- [x] 5. **Cloudflare Pages scaffold — EIM Web UI with password gate**
  What to do:
  1. Read design concepts from `/home/olly/Documents/Claw Components/Concepts/PC Interface` for visual direction.
  2. Create Cloudflare Pages project structure under `cloudflare/pages/eim/` (or extend existing `cloudflare/src/`):
     - `index.html` — main layout: left navigation menu, upper canvas (for avatar), lower management frame (multi-tab: tokenomics, master-control, analytics)
     - `app.js` — application logic, viewport switching, password gate
     - `style.css` — responsive design, dark theme, professional/executive aesthetic
  3. Implement password-only access: on page load, show password prompt. On correct entry, store session token in localStorage. All API calls include `Authorization: Bearer <password_hash>`.
  4. Password configured via Cloudflare Pages environment variable `ACCESS_PASSWORD_HASH` (SHA-256 of password, never stored in plaintext).
  5. Configure `wrangler.toml` or Cloudflare dashboard for Pages deployment at `cem.ai-staffing-solutions-consultants.online`.
  Must NOT do: Hard-code the password in HTML/JS (use env var + hash comparison). Deploy to Cloud Run (Pages only). Skip the responsive layout (executive-grade UI required).
  Parallelization: Wave 2 | Blocked by: None (design docs exist) | Blocks: 6, 7, 8
  References: Design concepts at `/home/olly/Documents/Claw Components/Concepts/PC Interface`, `cloudflare/src/index.html:1-186` (existing dashboard), `cloudflare/src/app.js:1-180` (existing app logic), `cloudflare/src/style.css:1-780` (existing styles), `wrangler.toml:1-86` (Cloudflare config)
  Acceptance criteria: `wrangler pages dev cloudflare/pages/eim/` starts local dev server; opening it shows password prompt; correct password loads dashboard layout with nav menu, upper canvas, lower frame.
  QA: happy — `curl -i http://localhost:8788/` returns HTML with password form; `curl -X POST http://localhost:8788/ -d 'password=wrong'` returns 401; correct password returns dashboard HTML with session. Evidence: `.omo/evidence/eim-full-deployment/task-5-pages-scaffold.txt`
  Commit: YES | `feat(eim): Cloudflare Pages scaffold — password-gated executive dashboard`

- [x] 6. **Integrate MediaPipe FaceLandmarker WASM — client-side emotion tracking**
  What to do:
  1. Add `@mediapipe/tasks-vision` dependency to the Pages project (via CDN or npm in the Pages build).
  2. Create `cloudflare/pages/eim/mediapipe-face-tracker.js`: loads FaceLandmarker WASM in VIDEO mode, captures webcam stream via `navigator.mediaDevices.getUserMedia({video: true})`, runs real-time face mesh detection, extracts 478 face landmarks + 52 blendshape scores.
  3. Emit blendshape scores as events on a custom EventTarget: `faceTracker.addEventListener('blendshape', (e) => { /* e.detail: { browDownLeft: 0.12, mouthSmileLeft: 0.87, ... } */ })`.
  4. Connect to the avatar canvas: blendshape scores drive subtle visual indicators (expression readout text overlay, confidence meter) in the upper canvas.
  5. Worker script loads WASM from CDN or local `public/wasm/` directory: `FaceLandmarker.createFromOptions(vision, { baseOptions: { modelAssetPath: '/wasm/face_landmarker.task', delegate: 'GPU' }, runningMode: 'VIDEO', ... })`.
  Must NOT do: Send raw video frames to any server (zero-latency, local-only processing). Load WASM synchronously (must be async/await with loading indicator). Block the main thread during detection (use `requestVideoFrameCallback` or `setInterval` with `performance.now()` drift compensation).
  Parallelization: Wave 2 | Blocked by: 5 (Pages scaffold) | Blocks: 7, 8
  References: `@mediapipe/tasks-vision` npm package (FaceLandmarker API), MediaPipe docs: `https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/web_js`, `cloudflare/pages/eim/app.js` (for integration point)
  Acceptance criteria: Opening the EIM page with webcam permission shows the face tracker canvas with 478 face mesh points drawn in real-time; `faceTracker.getBlendshapes()` returns 52 scores; CPU usage < 15% on modern hardware.
  QA: happy — browser console: `await faceTracker.detectOnce()` returns results array with faceLandmarks. failure — no webcam: tracker enters "no camera" state with user-visible message, does not crash. Evidence: screenshot of face mesh overlay + `.omo/evidence/eim-full-deployment/task-6-mediapipe.txt`
  Commit: YES | `feat(eim): MediaPipe FaceLandmarker WASM — client-side emotion/blendshape tracking`

- [x] 7. **Integrate Tavus WebRTC CVI — 2-way AI avatar video window**
  What to do:
  1. Read Tavus API key from `/home/olly/Documents/Keys2/Tavus/Tavus api key.txt`.
  2. Create Cloudflare Pages Function `cloudflare/pages/eim/functions/api/tavus/conversation.js` (or equivalent route handler): accepts POST with `{persona_id, replica_id}`, calls Tavus REST API `POST https://tavusapi.com/v2/conversations` with `x-api-key` header, returns `{conversation_url, conversation_id}`.
  3. Install `@tavus/cvi-ui` and `@daily-co/daily-js` in the Pages project for the client-side WebRTC transport.
  4. Create `cloudflare/pages/eim/tavus-avatar.js`: uses `CVIConversation` component (or Daily IFrame) to embed the 2-way video avatar in the upper canvas. Accepts conversation URL from step 2.
  5. Wire MediaPipe blendshape events into the Tavus conversation context: face expression data sent as custom events to the Tavus PAL for adaptive responses.
  6. Configure Tavus PAL (persona) and Face (replica) — use stock face initially, configurable via environment variables `TAVUS_PERSONA_ID` and `TAVUS_REPLICA_ID`.
  Must NOT do: Expose Tavus API key in client-side code (key stays in server-side Page Function only). Hard-code the API key in source files (use env var `TAVUS_API_KEY`). Deploy with the key readable in wrangler.toml (use `wrangler secret put`).
  Parallelization: Wave 2 | Blocked by: 5 (Pages scaffold), 6 (MediaPipe) | Blocks: 8
  References: Tavus CVI docs: `https://docs.tavus.io/sections/conversational-video-interface/overview-cvi`, `@tavus/cvi-ui` npm package, Tavus API key at `/home/olly/Documents/Keys2/Tavus/Tavus api key.txt`, `cloudflare/pages/eim/app.js` (integration point)
  Acceptance criteria: `curl -X POST https://cem.ai-staffing-solutions-consultants.online/api/tavus/conversation -H 'Content-Type: application/json' -d '{}'` returns `{conversation_url: "https://..."}`; opening the EIM page shows the avatar video window loading and connecting to a Tavus conversation.
  QA: happy — E2E: user opens EIM page → password gate → avatar window loads → user speaks → avatar responds (Tavus STT→LLM→TTS→Phoenix face render). failure — Tavus API unreachable: avatar window shows "Avatar service connecting..." spinner, no crash. Evidence: `.omo/evidence/eim-full-deployment/task-7-tavus.txt`
  Commit: YES | `feat(eim): Tavus WebRTC CVI — 2-way AI avatar video conversation window`

- [x] 8. **Secondary dashboard viewport — iframes for tokenomics and master-control**
  What to do:
  1. In `cloudflare/pages/eim/index.html`: below the upper avatar canvas, add a tabbed iframe/view panel with tabs: "Tokenomics Dashboard", "Master Control", "System Telemetry", "Ledger Audit".
  2. Each tab loads an iframe or embedded view pointing to the relevant Cloud Run endpoint or Cloudflare Pages-hosted dashboard:
     - Tokenomics: iframe to `https://track-a-control-loop-xxxxx-uc.a.run.app/ledger?limit=20` (or dedicated tokenomics dashboard URL)
     - Master Control: iframe showing a static/reactive control panel (or link to `https://cem.ai-staffing-solutions-consultants.online/master-control` sub-page)
     - Last 5 Agent Responses: embedded view calling Sheryl's `/dashboard/last-responses` endpoint (from Task 4), displayed as cards with agent name + timestamp + response preview + 🔴✔️ flags
  3. Implement cross-origin handling: if iframes are blocked, show a "Dashboard requires popup" fallback with a direct link.
  4. Add responsive breakpoints: on mobile (< 768px), iframes stack vertically instead of tabs.
  Must NOT do: Use `X-Frame-Options: DENY` on any dashboard endpoint (must allow framing from `cem.ai-staffing-solutions-consultants.online`). Load iframes synchronously blocking the avatar render.
  Parallelization: Wave 2 | Blocked by: 5, 6, 7 | Blocks: None
  References: `cloudflare/pages/eim/index.html` (Task 5 output), `cloudflare/pages/eim/style.css` (Task 5 output), Sheryl `/dashboard/last-responses` endpoint (Task 4)
  Acceptance criteria: Tab switching works smoothly (CSS transition ≤ 300ms); "Last 5 Agent Responses" tab shows data from Sheryl endpoint; iframe tabs show valid content or graceful "requires popup" fallback.
  QA: happy — playwright: navigate to EIM page, click "Master Control" tab, verify iframe loads or fallback shown; click "Last 5 Responses" tab, verify JSON-driven card list renders. failure — Sheryl endpoint down: "Last 5 Responses" tab shows "Dashboard data unavailable — check system health" message. Evidence: `.omo/evidence/eim-full-deployment/task-8-dashboard-viewport.txt`
  Commit: YES | `feat(eim): secondary dashboard viewport — tabbed iframes for tokenomics, master-control, agent responses`

- [ ] 9. **Inference smoketests — Aura, Malory, Krieger structured response verification**
  What to do:
  1. Read existing test files: `.test/test_aura_agent.py`, `.test/test_malory.py`, `.test/test_krieger.py` to understand current coverage.
  2. Create or extend `.test/test_hermes_smoketests.py` with:
     - `test_aura_responds_to_query`: POST to aura `/plan` with query "what is my schedule today", verify response contains `plan_id`, `steps` array, `source: "aura"`.
     - `test_malory_taskmaster_integration`: POST to malory `/plan` with business query "create a task for lead generation", verify response references taskmaster concepts (board, column, task).
     - `test_krieger_tool_execution`: POST to krieger `/plan` with engineering query "why is latency high", verify response `steps` contains allowlisted tools from `policy/tool-allowlist.txt`.
     - `test_hermes_routing_consistency`: Verify each agent returns `source` field matching its identity (aura/malory/krieger).
     - `test_hermes_ledger_writes`: Verify each agent's `/plan` call produces a ledger entry (call `/ledger?limit=1` after, check for `plan_id` match).
  3. Run: `python -m pytest .test/test_hermes_smoketests.py -q -v`.
  Must NOT do: Mock external API calls that should be tested live (use real docker-compose services). Skip ledger verification.
  Parallelization: Wave 3 | Blocked by: 4 (Aura protocol must exist, quartet services functional) | Blocks: None
  References: `executive-quartet/aura/main.py` (full source), `executive-quartet/malory/main.py`, `executive-quartet/krieger/main.py`, `policy/tool-allowlist.txt`, `.test/test_aura_agent.py:1-223`, `.test/test_malory.py:1-209`, `.test/test_krieger.py:1-187`
  Acceptance criteria: `python -m pytest .test/test_hermes_smoketests.py -q` exits 0 with ≥ 5 tests passing. Each test verifies agent identity (`source` field), structured response format, and ledger write.
  QA: happy — full run: `docker compose up --build aura-agent malory krieger sheryl` then `python -m pytest .test/test_hermes_smoketests.py -v` shows all green. failure — one agent down: test skips with `pytest.skip("service unavailable")`, does not crash. Evidence: `.omo/evidence/eim-full-deployment/task-9-smoketests.txt`
  Commit: YES | `test(quartet): Hermes inference smoketests — Aura, Malory, Krieger structured routing + taskmaster + ledger`

- [ ] 10. **Wire self-remediation to Cloudflare/GCP telemetry + OpenViking RAG**
  What to do:
  1. Read current self-remediation code: `self-remediation/main.py:1-406`, `self-remediation/health-hooks.py:1-395`, `self-remediation/auditor.py:1-216`.
  2. Add telemetry listener to self-remediation: create `self-remediation/telemetry.py` that:
     - Polls Cloud Run service health via `gcloud run services list --filter="status.latestReadyRevisionName!=''"` (or GCP Monitoring API) every 60s.
     - Reads Cloudflare Workers telemetry from the `remediation-events` Cloudflare Queue (referenced in `CEM_Update.txt:30`).
     - Writes anomalies to ledger as `type: "telemetry_anomaly"`.
  3. Connect self-remediation to OpenViking RAG: when an anomaly is detected, query the OpenViking vector store for matching historical incidents and known fixes. Stub the vector query interface (real vector search is future work; use keyword-match against `rag/docs/openviking/` SOP files for now).
  4. Add Gemini Knowledge Steward integration: create `self-remediation/knowledge_steward.py` — accepts anomaly report, queries Gemini API for root-cause analysis, stores result in MemoryPlugin (via Sheryl `/memory/store`). API key from `GEMINI_API_KEY` env var.
  5. Update `self-remediation/main.py` to import and initialize telemetry listener on startup.
  6. Update `self-remediation/requirements.txt` to include `google-cloud-monitoring`, `google-cloud-run`, `google-generativeai`.
  Must NOT do: Auto-execute fixes without human approval (existing `_execute_step` is stubbed — keep it stubbed). Echo any API keys in logs.
  Parallelization: Wave 3 | Blocked by: None (self-remediation exists) | Blocks: None
  References: `self-remediation/main.py:1-406`, `self-remediation/health-hooks.py:1-395`, `self-remediation/auditor.py:1-216`, `self-remediation/Dockerfile:1-33`, `rag/docs/openviking/SOP-001-system-architecture.md`, `rag/docs/openviking/SOP-002-incident-response.md`, `CEM_Update.txt:30` (remediation-events queue), `openviking-memory/` (empty — will be populated in Task 11)
  Acceptance criteria: `self-remediation/telemetry.py` imports without errors; `python -c "from self_remediation.telemetry import TelemetryListener"` succeeds (after adjusting imports); `curl -X POST http://localhost:8087/health-check` returns probe results for all mesh services (existing endpoint, verify still works).
  QA: happy — `python -m pytest .test/test_health_hooks.py -q` still passes (existing tests not broken). failure — GCP API unreachable: telemetry listener logs warning, does not crash self-remediation service. Evidence: `.omo/evidence/eim-full-deployment/task-10-telemetry.txt`
  Commit: YES | `feat(remediation): telemetry listener — GCP Cloud Run + Cloudflare Queue monitoring, OpenViking RAG integration, Gemini Knowledge Steward`

- [ ] 11. **Populate OpenViking RAG memory plane + Gemini Knowledge Steward configuration**
  What to do:
  1. Populate `openviking-memory/` directory (currently empty):
     - `openviking-memory/vector-store-config.json` — configuration for the vector store (embedding model, dimension, index type, namespace). Namespace: `core-engineering-system`.
     - `openviking-memory/knowledge-steward-config.json` — Gemini Knowledge Steward configuration: model (`gemini-2.5-flash` or `gemini-2.5-pro`), prompt template for root-cause analysis, allowed actions (query RAG, search logs, propose fix).
     - `openviking-memory/README.md` — setup instructions, dependency list, connection string format.
     - `openviking-memory/seed-data/` — seed knowledge entries (SOP documents from `rag/docs/openviking/` indexed into vector format).
  2. Create `openviking-memory/ingest-pipeline.py` — script that reads `rag/docs/openviking/*.md`, chunks by section heading, generates embeddings placeholder, writes to vector store (stubbed — real embedding generation requires API key).
  3. Wire Gemini Knowledge Steward to self-remediation: create `openviking-memory/gemini-steward.py` — receives `{"anomaly": {...}, "rag_context": [...]}` from self-remediation, crafts prompt, calls Gemini API, returns `{"diagnosis": "...", "recommended_action": "...", "confidence": 0.85}`.
  4. Update `self-remediation/main.py` to call Gemini Steward as part of remediation plan construction.
  Must NOT do: Hard-code API keys in openviking-memory/ files (use env vars). Implement actual vector database (this is configuration + stubs — real deployment is a separate Milestone).
  Parallelization: Wave 3 | Blocked by: None (directory exists, is empty) | Blocks: None
  References: `openviking-memory/` (empty directory), `rag/docs/openviking/SOP-001-system-architecture.md`, `rag/docs/openviking/SOP-002-incident-response.md`, `self-remediation/main.py:1-406`
  Acceptance criteria: `test -f openviking-memory/vector-store-config.json`, `test -f openviking-memory/gemini-steward.py`, `python openviking-memory/gemini-steward.py --help` exits 0, `python openviking-memory/ingest-pipeline.py --dry-run` exits 0
  QA: happy — `ls openviking-memory/` shows ≥ 4 files; `python -c "import json; json.load(open('openviking-memory/vector-store-config.json'))"` exits 0. failure — Gemini API key missing: steward module logs warning, returns "unavailable" status without crashing. Evidence: `.omo/evidence/eim-full-deployment/task-11-openviking.txt`
  Commit: YES | `feat(openviking): vector memory plane — store config, Gemini Knowledge Steward, ingest pipeline`

- [ ] 12. **Register Telegram webhook + live end-to-end test**
  What to do:
  1. After deploy-gcr.sh runs (Task 13), get the telegram-bridge Cloud Run URL: `gcloud run services describe telegram-bridge --region=us-central1 --project=aissc-core-engine-self-dep --format='value(status.url)'`
  2. Register webhook with Telegram Bot API: `curl -F "url=https://<TELEGRAM_BRIDGE_URL>/webhook" -F "secret_token=<randomly_generated_32_char_secret>" "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook"`
  3. Store the `secret_token` as a Cloud Run secret: `gcloud run services update telegram-bridge --set-env-vars="TELEGRAM_WEBHOOK_SECRET=<secret>"` (or use Secret Manager).
  4. Verify webhook registration: `curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"` returns `{"ok": true, "result": {"url": "...", "has_custom_certificate": false, "pending_update_count": 0}}`
  5. Send test message via Telegram to the bot: verify it appears in telegram-bridge logs and Sheryl's ledger.
  6. Verify Aura Consistency Protocol: send an ambiguous message ("maybe we could think about possibly deploying something") → bot response includes `🔴✔️`.
  Must NOT do: Echo the bot token in any log output. Register webhook against internal-only services (only telegram-bridge has public access).
  Parallelization: Wave 4 | Blocked by: 4 (Aura protocol), 13 (deploy) | Blocks: None
  References: Telegram Bot API docs: `https://core.telegram.org/bots/webhooks`, `https://core.telegram.org/bots/api#setwebhook`, `telegram-bridge/main.py:117-194` (webhook handler), Telegram research from librarian (Cloud Run webhook patterns)
  Acceptance criteria: `getWebhookInfo` returns URL pointing to telegram-bridge; test Telegram message appears in Sheryl ledger via `curl http://localhost:8083/ledger?limit=5` (or Cloud Run ledger endpoint); ambiguous message test returns response with `🔴✔️`
  QA: happy — full E2E: send "deploy the marketing module" via Telegram → message routes through telegram-bridge → Sheryl `/ingest` → Aura checks consistency → response back via Telegram with or without `🔴✔️`. failure — webhook not set: `getWebhookInfo` shows empty URL (manual intervention needed before proceeding). Evidence: `.omo/evidence/eim-full-deployment/task-12-telegram-webhook.txt`
  Commit: N/A (runtime configuration, no code change) | Record webhook URL + verification in evidence

- [ ] 13. **Execute `deploy-gcr.sh` — full Cloud Run mesh deploy**
  What to do:
  1. Verify all preconditions:
     - `gcloud auth list` shows active account with `aissc-core-engine-self-dep` access
     - `gcloud config set project aissc-core-engine-self-dep && gcloud config set run/region us-central1`
     - Docker daemon running (for local validation, not required for source deploy)
     - All 5 Wave 1-3 tasks committed and pushed to `production` branch
  2. Run: `bash deploy-gcr.sh 2>&1 | tee deploy-output.log`
  3. Monitor output for errors. Expected services deployed (8 total):
     - track-a-control-loop (internal, :8080)
     - track-b-actuator (internal, :8081)
     - sheryl-agent (internal, :8083)
     - aura-agent (internal, :8084)
     - malory-agent (internal, :8085)
     - krieger-agent (internal, :8086)
     - self-remediation (internal, :8087)
     - telegram-bridge (public, :8088)
  4. If any service deploy fails with quota error, retry with `--memory=256Mi`.
  5. Print final service list with URLs: `gcloud run services list --project=$PROJECT --region=$REGION --format='table(name, status.address.url, metadata.annotations.serving.knative.dev/ingress)'`
  Must NOT do: Deploy with `--allow-unauthenticated` on any service except telegram-bridge. Exceed free tier sizing. Deploy to wrong project or region.
  Parallelization: Wave 4 | Blocked by: 12 (deploy-gcr.sh exists), 3 (production branch), Tasks 1-11 (all code changes) | Blocks: 12 (webhook), 14 (verification)
  References: `deploy-gcr.sh` (Task 2 output), `cloudbuild.yaml:330-385` (existing deploy patterns), `terraform/cloudrun.tf` (IAC reference)
  Acceptance criteria: `gcloud run services list --project=aissc-core-engine-self-dep --region=us-central1` shows 8 services all with status "OK"; `gcloud run services describe telegram-bridge --format='value(metadata.annotations.serving.knative.dev/ingress)'` returns `all` (public); all other services return `internal` (empty or `internal`).
  QA: happy — `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <TRACK_A_URL>/healthz` returns 200 for each internal service; `curl <TELEGRAM_BRIDGE_URL>/healthz` returns 200 with no auth. failure — deploy failed mid-way: script output saved to `deploy-output.log`, identify which service failed, fix, re-run only that service. Evidence: `.omo/evidence/eim-full-deployment/task-13-deploy-output.log`
  Commit: N/A (deployment execution) | Commit `deploy-output.log` as deployment evidence

- [ ] 14. **Endpoint verification log — health-check all 8 services**
  What to do:
  1. For each deployed service, run health check and record result:
     - Track A: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/healthz`
     - Track B: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/healthz`
     - Sheryl: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/healthz`
     - Aura: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/healthz`
     - Malory: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/healthz`
     - Krieger: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/healthz`
     - Self-Remediation: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <URL>/healthz`
     - Telegram Bridge: `curl -si <URL>/healthz` (public, no auth needed)
  2. Verify EIM Web UI: `curl -si https://cem.ai-staffing-solutions-consultants.online/` returns 200 with HTML containing password form.
  3. Verify Tavus API connectivity: `curl -si https://cem.ai-staffing-solutions-consultants.online/api/tavus/conversation` returns valid response (or at least 401 if auth required, proving endpoint is live).
  4. Verify Telegram webhook: `curl -si "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"` shows `url` field populated.
  5. Verify self-remediation mesh health: `curl -si -H "Authorization: Bearer $(gcloud auth print-identity-token)" <SELF_REMEDIATION_URL>/health-check` returns probe results for all 8 services.
  6. Produce `deployment-verification.log` with all results formatted as a table: service name, URL, status code, response time, health status.
  Must NOT do: Claim success if any health check returns non-200. Skip any service.
  Parallelization: Wave 4 | Blocked by: 13 (deploy) | Blocks: None
  References: All service URLs from `gcloud run services list` output (Task 13), `README.md:1092-1110` (API reference)
  Acceptance criteria: All 8 health checks return HTTP 200; EIM Web UI returns 200; Telegram getWebhookInfo returns valid URL; self-remediation /health-check returns all 8 services as "healthy". Verification log written to `.omo/evidence/eim-full-deployment/task-14-verification.log`.
  QA: happy — `grep "200" .omo/evidence/eim-full-deployment/task-14-verification.log | wc -l` returns ≥ 10 (8 services + web UI + self-remediation probe). failure — any service returns non-200: log the error, file as known issue, proceed (deployment verification documents status, not blocks). Evidence: `.omo/evidence/eim-full-deployment/task-14-verification.log`
  Commit: YES | `docs(deploy): endpoint verification log — all 8 services health-checked post-deploy`

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit
- [ ] F2. Code quality review
- [ ] F3. Real manual QA
- [ ] F4. Scope fidelity

## Commit strategy
- Tasks 1-11, 14: individual commits per task as specified
- All commits on `production` branch
- Push to `AI-Staffing-Solution-Consultants-LLC/core-engineering-system` (remote `origin`)
- Task 13 (deploy): no commit; deploy-output.log committed as evidence in Task 14
- Message format: conventional commits (`feat(scope):`, `chore(scope):`, `test(scope):`, `docs(scope):`)

## Success criteria
1. `.gcloudignore` exists and excludes all dev artifacts from Cloud Run source deploy
2. `deploy-gcr.sh` is executable and deploys all 8 services to `aissc-core-engine-self-dep` in `us-central1`
3. `production` branch exists on `AI-Staffing-Solution-Consultants-LLC/core-engineering-system`
4. EIM Web UI loads at `cem.ai-staffing-solutions-consultants.online` with password gate, MediaPipe face tracker, and Tavus avatar window
5. Telegram bot responds to messages; ambiguous responses include `🔴✔️` flag
6. All 3 Hermes agents pass inference smoketests (structured routing, taskmaster integration, ledger writes)
7. Self-remediation telemetry listener polls GCP/Cloudflare and writes anomalies to ledger
8. OpenViking memory plane populated with config, steward, and ingest pipeline
9. All 8 Cloud Run services return healthy status from health-check probe
10. Deployment verification log present with all endpoints confirmed
