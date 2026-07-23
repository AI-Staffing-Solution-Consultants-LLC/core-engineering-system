# PHASE-5 Evidence — Task 8: Install `@agency-agents/cli`

**Date:** 2026-07-19
**Task:** Task 8 from `.omo/plans/nexus-sprint.md` (lines 225-241)
**Status:** **FAILED — local install did not complete. STOPPED per spec. No global fallback attempted.**

---

## 1. Environment

| Item | Value |
|---|---|
| Working directory | `/home/olly/core-engineering-system/agency-agents/` |
| Node | `v24.14.0` (`/usr/bin/node`) |
| npm | `11.11.0` (`/home/olly/.npm-global/bin/npm`) |
| Registry | `https://registry.npmjs.org/` (default) |
| Install scope | **LOCAL** (no `-g` flag) |

## 2. package.json created

```json
{
  "name": "agency-agents",
  "version": "0.1.0",
  "private": true,
  "description": "Local devDependency container for @agency-agents/cli (NEXUS-Sprint Phase-5)",
  "devDependencies": {
    "@agency-agents/cli": "latest"
  }
}
```

`grep -q '"@agency-agents/cli"' agency-agents/package.json` → exit 0 (PASS).

## 3. Install command (LOCAL ONLY)

```bash
cd /home/olly/core-engineering-system/agency-agents
npm install --no-audit --no-fund
```

**No `-g` flag used.** No global install attempted.

## 4. Failure evidence

```
npm error code E404
npm error 404 Not Found - GET https://registry.npmjs.org/@agency-agents%2fcli - Not found
npm error 404
npm error 404  The requested resource '@agency-agents/cli@latest' could not be found or you do not have permission to access it.
npm error 404
npm error 404 Note that you can also install from a
npm error 404 tarball, folder, http url, or git url.
npm error A complete log of this run can be found in: /home/olly/.npm/_logs/2026-07-19T22_00_16_695Z-debug-0.log
EXIT_CODE=1
```

**Root cause:** The package `@agency-agents/cli` does not exist on the public npm registry. The 404 response from `registry.npmjs.org` confirms the package is not published (or is published under a different scope/name).

## 5. Acceptance criteria status

| Criterion | Status |
|---|---|
| `agency-agents/package.json` created with `@agency-agents/cli` as local devDependency | **PASS** |
| `npm install --no-audit --no-fund` run from `agency-agents/` directory | **PASS** (command executed) |
| `agency-agents/node_modules/.bin/agency-agents --version` exits 0 and prints a version string | **FAIL** — `node_modules/.bin/agency-agents` does not exist (install failed) |
| NO occurrence of `-g` in any install command | **PASS** — only `npm install --no-audit --no-fund` was run |
| Verification commands all pass | **FAIL** — binary verification cannot pass because install failed |

## 6. Action taken per spec

Per `.omo/plans/nexus-sprint.md` line 232:

> If the local install fails (registry unreachable), record evidence and STOP — do **not** fall back to a global install without approval.

- Evidence recorded in this file (`evidence/PHASE-5.md`).
- **STOPPED.** No global install attempted.
- No fallback to `npm install -g @agency-agents/cli`.
- No modification of files outside `agency-agents/` (except this evidence file and the learnings notepad).

## 7. Checkpoint #8 status

**`checkpoint #8 = NO-LIVE-INSTALL-CONFIRMED`** (per plan line 241).

The local install path was attempted and failed due to the package not being published to the public npm registry. Human approval is required before any alternative install scope (global, private registry, tarball, git URL) is attempted.

## 8. Next steps (require human approval)

Possible paths forward, each requiring explicit human approval:

1. **Publish `@agency-agents/cli` to npm** — requires the package source to exist and be published under the `@agency-agents` scope.
2. **Install from a private registry** — requires a registry URL and credentials.
3. **Install from a tarball or git URL** — requires the artifact to exist somewhere reachable.
4. **Approve global install** — would require `npm install -g @agency-agents/cli` and would mark checkpoint #8 = APPROVED.

Until one of these is approved, Task 8 remains incomplete and downstream tasks (T9-T11) that depend on the CLI being available cannot proceed.
