---
phase: 244-train-sr-ladder-calculation-not-recall
plan: 02
subsystem: train
tags: [train, spaced-repetition, copy, changelog, pre-merge-gate]
requires: ["244-01"]
provides:
  - "User-facing Train copy (Home card, verdict tail, stats-card popovers, README) describing the new SR ladder"
  - "CHANGELOG [Unreleased] bullet for the SR ladder rework"
  - "STATE.md open-thread reminder for the SEED-207 post-ship re-check"
affects: [train frontend copy]
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - frontend/src/pages/Home.tsx
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/components/train/TrainStatsCard.tsx
    - frontend/src/components/train/TrainFlawFixedBanner.tsx
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/components/train/__tests__/TrainStatsCard.test.tsx
    - README.md
    - CHANGELOG.md
    - .planning/STATE.md
key-decisions:
  - "D-03 honoured: returnPhrase, NEXT_SESSION_TAIL and the 'Back in N days' tail are untouched"
  - "Explainers say 'a few days' for the miss delay so a later FAIL_RETRY_DAYS tweak needs no copy change; stats-card counts (2, 3, 4) stay numeric"
metrics:
  duration: "about 15 min"
  tasks: 2
  files: 9
status: complete
actuals:
  tokens: 3000
  tasks: 2
  commits: 2
plan_head_before: a7c498e97ca8d8d3a7cb70391f40ba958b8e524f
plan_head_after: 93e0c383caafbc6631b7693a416613cd3db79e56
---

# Phase 244 Plan 02: SR Ladder Copy and Pre-merge Gate Summary

Every user-facing description of Train's spaced repetition now matches the 244-01 ladder: a missed position returns a few days later, a solved one after ten days, mastery at two correct solves in a row, parked at 4 lifetime misses (or 3 without ever solving).

## What Was Built

- **Task 1 (tracer, `31d8322e6`)**: Home Train card sentence, `MASTERED_TAIL = 'Two in a row, so this one is retired.'` (only change in `trainBotCopy.ts`), `MASTERED_EXPLAINER` ("Solved correctly twice in a row."), `PARKED_EXPLAINER` ("Missed 4 times in total, or 3 times without ever solving it."), and the threshold comment (2 / 3 / 4). Tests: `toContain('Two in a row')` on the mastered-tail case, and a new `TrainStatsCard` case that opens both popovers and asserts the new thresholds.
- **Task 2 (`93e0c383c`)**: README feature bullet, CHANGELOG `[Unreleased]` / `### Changed` first bullet, STATE.md open-thread line for the SEED-207 post-ship re-check, and the `TrainFlawFixedBanner.tsx` header comment ("reaches mastery (two correct solves in a row)").

## Copy Grep (Task 1 step 6)

`grep -rniE "three times|3 times in a row|three solves|three days|6 times|six (misses|times)|(after|then) (three|3) days|3/3|three in a row"` over `frontend/src` and `README.md` (tests excluded) returned only unrelated prose hits (`trainBotCopy.ts:267,401`, `botLineTrigger.ts:75`, `maiaWorkerErrors.ts:89`). No remaining ladder copy names three solves, a three-day step or six misses.

## Pre-merge Gate (T-244-06)

| Step | Result |
| ---- | ------ |
| `ruff format app/ tests/ scripts/ analysis/` | 556 files unchanged |
| `ruff check . --fix` | All checks passed |
| `ty check app/ tests/ scripts/` | All checks passed |
| `ty check analysis/` (analysis project) | All checks passed |
| `check_function_size.py app/ --fail-over-depth 4` | OK, 1279 functions, no breaches |
| `pytest -n auto -x` | 5668 passed, 19 skipped |
| Serial run: migration 244, scheduler, routers/test_train, train_repository | 378 passed |
| Frontend `npm run lint` | clean |
| Frontend `npm run build` (tsc -b + vite) | success |
| Frontend `npm test -- --run` | 341 files, 5706 tests passed |
| Frontend `npm run knip` | exit 0 (config hints only) |

The formatter and `--fix` changed no files, so no `style(244)` commit was needed.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. Copy is compile-time string literals rendered as React text (T-244-05 accepted); T-244-06 mitigated by the gate above.

## Notes for Merge/Deploy

- The phase is ready to squash-merge to `main` (both plans applied, gate green).
- Deploy: compare the migration's logged "pushed due_date on N active drill_items" count with the ~436 sizing in 244-CONTEXT.
- The CHANGELOG bullet sits in `[Unreleased]` per CLAUDE.md.

## Self-Check: PASSED

- Commits `31d8322e6` and `93e0c383c` are on branch `gsd/phase-244-train-sr-ladder-calculation-not-recall`.
- Edited files verified by grep and by passing tests.
