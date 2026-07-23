# Phase 1 — Pytest harness + smoke tests

**Status:** COMPLETED (T1, Wave 1)
**Date:** 2026-07-19

## Files touched

- `.test/__init__.py` (new, empty package marker)
- `.test/conftest.py` (new, Flask test client fixtures for track-a and track-b)
- `.test/test_track_a_routes.py` (new, 5 passing + 4 xfail)
- `.test/test_track_b_allowlist.py` (new, 6 passing + 10 parametrized metachar tests)
- `.test/test_ledger_chain.py` (new, 4 passing tests for chain hash spec)
- `.gitignore` (modified, added `.venv/`)

## Acceptance commands

```bash
.venv/bin/python -m pytest .test/ -q
# Result: 30 passed, 4 xfailed in 1.91s (exit 0)
```

## Verification

- 34 tests collected (≥ 12 required ✓)
- 30 passing (≥ 8 required ✓)
- 4 xfail placeholders for unimplemented ReAct loop features

## Notes

- Track A's `react_plan()` calls `execute_action_via_track_b()` which makes HTTP requests. Tests mock `requests.post` to avoid connection timeouts.
- Chain hash spec verified: `chain_hash[n] == sha256((prev_hash or "") + json.dumps(entry_without_chain_hash, sort_keys=True))`.
- No production code modified. No new dependencies added.
