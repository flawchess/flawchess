---
phase: 241-codebase-cleanup
plan: 68
subsystem: naming
tags: [rename, cross-layer, eval-entry, opponent-strength]
requires: ["241-67"]
provides:
  - "_EntryPlyEvalTarget / _apply_entry_eval_results (entry-lane names)"
  - "SIMILAR_THRESHOLD (backend + frontend)"
key-files:
  modified:
    - app/services/eval_entry.py
    - app/services/eval_drain.py
    - app/routers/eval_remote.py
    - tests/services/test_eval_drain.py
    - tests/test_eval_worker_endpoints.py
    - app/core/opponent_strength.py
    - frontend/src/lib/opponentStrength.ts
    - frontend/src/components/filters/OpponentStrengthFilter.tsx
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-68.tsv
decisions: []
metrics:
  tasks: 2
status: complete
commits: 2
plan_head_before: 615da7f14616650d0f67a2952e99e2a78e06198e
plan_head_after: a0775180b
actuals:
  tasks: 2
  commits: 2
---

# Phase 241 Plan 68: X8/X9/X2 cross-layer renames Summary

Entry-lane eval target and writer renamed to mirror their full-lane twins, and the Similar-preset bound renamed on both stacks, with no behavior change.

## Renames

| ID | Old -> New | Commit | Files |
|----|-----------|--------|-------|
| X8 | `_EvalTarget` -> `_EntryPlyEvalTarget` | d6819d14e | eval_entry.py, eval_drain.py (re-export, `# noqa: F401` kept), eval_remote.py, test_eval_drain.py, test_eval_worker_endpoints.py |
| X9 | `_apply_eval_results` -> `_apply_entry_eval_results` | d6819d14e | same files |
| X2 | `PRESET_THRESHOLD` -> `SIMILAR_THRESHOLD` | a0775180b | app/core/opponent_strength.py, frontend/src/lib/opponentStrength.ts, OpponentStrengthFilter.tsx |

Rename map: `.planning/phases/241-codebase-cleanup/rename-maps/241-68.tsv` (3 rows; committed with each task).

## Verification

- ruff check/format, ty (app/ tests/ scripts/): clean.
- pytest test_eval_drain, test_full_eval_drain, test_eval_worker_endpoints: 214 passed.
- `import app.core.opponent_strength` smoke check, `npm run build`, `npm run lint`, filter/lib vitest: pass.
- `cleanup.py absent` (3 rows, 0 hits) and `cleanup.py diff` pass for both tasks; no ruff isort reorder occurred, so no allow row was needed.
- `_FullPlyEvalTarget` / `_apply_full_eval_results` untouched.

## Deviations from Plan

None. app/services/import_service.py contained no matching token at execution time (the plan listed it from planning-time assumptions), so it was not modified.

## Known Stubs

None.

## Self-Check: PASSED

Both commits (d6819d14e, a0775180b) exist on the branch; rename map present.
