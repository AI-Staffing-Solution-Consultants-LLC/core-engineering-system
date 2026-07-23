# Phase 3 — Runbook manifest + draft mirror

**Status:** COMPLETED (T3, T4, Wave 1)
**Date:** 2026-07-19

## Files touched

- `.omo/evidence/runbook-manifest.md` (new, 129 lines)
- `.omo/drafts/nexus-sprint.md` (new, 172 lines)

## Acceptance commands

```bash
test -f .omo/evidence/runbook-manifest.md && wc -l .omo/evidence/runbook-manifest.md
# Result: 129 lines (≥ 40 required ✓)

test -f .omo/drafts/nexus-sprint.md && wc -l .omo/drafts/nexus-sprint.md
# Result: 172 lines (≥ 40 required ✓)

grep -cE 'Wave|HUMAN-APPROVAL-REQUIRED|@agency-agents|Antigravity|Taskmaster|agency-agents-factory|14' .omo/drafts/nexus-sprint.md
# Result: 31 matches
```

## Verification

- Manifest declares `Phase 5: live (config-first)`.
- Draft mirrors all 4 waves, 11 checkpoints, 14 Must-NOT-Have items.
- Source of truth remains `.omo/plans/nexus-sprint.md`.
