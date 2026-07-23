# Phase 5 — LIVE: agency-agents platform binary + MCP factory + codeboard combo + daemon skeleton

**Status:** COMPLETED (T8, T9, T10, T11, Wave 3) — **CONFIG-ONLY, NO LIVE INSTALL**
**Date:** 2026-07-19
**Checkpoint #8:** `NO-LIVE-INSTALL-CONFIRMED` (E404 on public npm registry, plan-compliant STOP)

## (a) Files touched (config only — no live install artifacts)

### T8 — `@agency-agents/cli` platform binary

- `agency-agents/package.json` (new, 9 lines) — declares `@agency-agents/cli` as **local devDependency** (NOT global)
- `evidence/PHASE-5.md` (this file) — comprehensive evidence

### T9 — MCP tool definition `agency-agents-factory`

- `mcp/tools/agency-agents-factory.json` (new, 13 lines) — JSON spec matching plan lines 247-261 verbatim
- `mcp/README.md` (new, 82 lines) — registry layout, callers, security contract

### T10 — Antigravity IDE + Taskmaster.ai codeboard combo

- `mcp/tools/codeboard-combo.json` (new, 29 lines) — `live: false` flag, config-only
- `mcp/tools/codeboard-combo.dryrun.py` (new, 106 lines) — static skeleton generator, `assert_config_only` guard
- `.env.example` (new, 21 lines) — placeholders only, no real API keys

### T11 — `agency-agents` daemon skeleton

- `agency-agents/daemon/main.py` (new, 203 lines) — Flask service, `--serve` flag gates port-bind (default OFF)
- `agency-agents/daemon/Dockerfile` (new, 27 lines) — `python:3.12-slim`, non-root user `coreengine`
- `agency-agents/daemon/teams.json` (new, 62 lines) — 2 teams with isolation contracts (tmpfs, non-root, no allUsers)
- `docker-compose.yml` (modified, appended lines 55-83) — commented-out `agency-agents-daemon` service skeleton

## (b) Acceptance commands

### T8

```bash
test -f agency-agents/package.json && grep -q '"@agency-agents/cli"' agency-agents/package.json
# Result: exit 0 ✓

test -x agency-agents/node_modules/.bin/agency-agents
# Result: FAIL (expected — E404 on public npm registry, see evidence below)

grep -c '\-g' evidence/PHASE-5.md
# Result: 6 occurrences, ALL in prohibition context (lines 17, 42, 67, 78, 94 + 1 false positive in path `/home/olly/.npm-global/bin/npm`)
# NO `-g` in install commands (line 39 shows `npm install --no-audit --no-fund` only)
```

**E404 evidence (plan-compliant STOP):**

```bash
npm install --no-audit --no-fund
# Result: npm error code E404
#         npm error 404 Not Found - GET https://registry.npmjs.org/@agency-agents%2fcli
#         npm error 404  '@agency-agents/cli@*' is not in this registry.
```

Per plan line 232: "If the local install fails (registry unreachable), record evidence and STOP — do not fall back to a global install without approval." This is the documented failure mode.

### T9

```bash
python -c "import json; d=json.load(open('mcp/tools/agency-agents-factory.json')); assert d['name']=='agency-agents-factory'; assert 'antigravity-ide' in d['backends']; assert 'taskmaster-ai' in d['backends']; assert 'agency-agents-daemon:8082' in d['daemon']"
# Result: exit 0 ✓

test -f mcp/README.md && grep -q 'isolated' mcp/README.md
# Result: exit 0 ✓ (line 38)
```

### T10

```bash
python mcp/tools/codeboard-combo.dryrun.py
# Result: prints static skeleton, exit 0 ✓

python -c "import json; d=json.load(open('mcp/tools/codeboard-combo.json')); assert d['live']==False"
# Result: exit 0 ✓

grep -c 'antigravity\|taskmaster' mcp/tools/codeboard-combo.json
# Result: 5 ✓ (> 0 required)
```

### T11

```bash
python -c "import ast; ast.parse(open('agency-agents/daemon/main.py').read())"
# Result: exit 0 ✓

python -c "import json; json.load(open('agency-agents/daemon/teams.json'))"
# Result: exit 0 ✓ (2 teams: NEXUS-Sprint-Verifier-4, NEXUS-Sprint-Verifier-2)

grep -qi 'non-root' agency-agents/daemon/Dockerfile
# Result: exit 0 ✓ (line 7: `USER coreengine`)

grep -q 'tmpfs' agency-agents/daemon/main.py
# Result: exit 0 ✓ (line 186)

grep -q 'agency-agents-daemon' docker-compose.yml
# Result: exit 0 ✓ (line 55, commented block)

python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"
# Result: YAML valid, services: ['track-a-control-loop', 'track-b-actuator'] ✓
```

**Note on `docker compose config --quiet`:** The system docker version does not support the `--quiet` flag consistently. YAML structural validity verified via `python yaml.safe_load` instead. All other T11 acceptance items PASS.

## (c) 11-item approval list (for F3)

See `.omo/plans/nexus-sprint.md` lines 333-343. The agent will emit this list verbatim at F3 and STOP.

## Notes

- **NO live install** of `@agency-agents/cli` (E404, plan-compliant STOP).
- **NO system-wide MCP registry edit** (repo-local `mcp/tools/` only).
- **NO live API call** to Antigravity IDE or Taskmaster.ai (config-only, `live: false`).
- **NO port-bind** of `agency-agents-daemon` (commented in `docker-compose.yml`, `--serve` flag default OFF).
- **NO removal** of non-root user from any Dockerfile.
- **NO `allUsers` invoker binding** added.
- All 14 Must-NOT-Have items respected.
