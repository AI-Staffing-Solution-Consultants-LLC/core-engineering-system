# Phase 2 — Rego evaluator hook + Cloud Build + allowlist/ledger tests

**Status:** COMPLETED (T2, T5, T6, T7, Wave 2)
**Date:** 2026-07-19

## Files touched

- `track-a/opa_eval.py` (new, 134 lines, stdlib `re` parser)
- `track_a/__init__.py` (new, package alias for hyphen-named `track-a/`)
- `conftest.py` (new, idempotent fallback for `track_a` registration)
- `.test/test_opa_eval.py` (new, 5 tests)
- `cloudbuild.yaml` (new, 101 lines, 4 deploy steps with `--no-allow-unauthenticated`)
- `tests/allowlist-mutation-test.py` (new, 355 lines, 4/4 PASS)
- `tests/ledger-chain-test.py` (new, 235 lines, 6/6 PASS)

## Acceptance commands

```bash
.venv/bin/python -m pytest .test/test_opa_eval.py -q
# Result: 5 passed in 0.13s (exit 0)

.venv/bin/python -c "from track_a.opa_eval import eval_package; print(eval_package('policy/log-reasoning-steps.rego'))"
# Result: {'package': 'core.constitutional', 'imports': [], 'rules': [{'name': 'deny', 'key': 'msg', 'body': '...'}]}

.venv/bin/python tests/allowlist-mutation-test.py
# Result: 4/4 PASS

.venv/bin/python tests/ledger-chain-test.py
# Result: 6/6 PASS
```

## Verification

- All 4 Rego files parse with `package='core.constitutional'`, `rules=['deny']`, `imports=[]`.
- `cloudbuild.yaml` has 4 deploy steps, all with `--no-allow-unauthenticated`.
- Allowlist mutation test verifies exact-match + prefix-match semantics.
- Ledger chain test verifies SHA-256 chain integrity.

## Notes

- `opa_eval.py` is a structural stub — does NOT evaluate Rego rules. Wire-up to real OPA engine is a future task.
- `track_a/` package alias bridges hyphen-vs-underscore naming gap.
