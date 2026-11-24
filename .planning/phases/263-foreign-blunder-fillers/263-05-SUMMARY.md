---
phase: 263-foreign-blunder-fillers
plan: 05
subsystem: api
tags: [leaderboard, activity-dashboard, sqlalchemy, tdd]

requires:
  - phase: 263-foreign-blunder-fillers
    provides: plan 01 DrillSource.FOREIGN_BLUNDER = 3 and the drill_solves source CHECK (0, 1, 2, 3)
provides:
  - _ACCURACY_SOURCES, a positive source list (SR item, red herring) for the Accuracy board totals
  - Activity source breakdown row for source 3 and the retired source 2 row
affects: [263-10]

plan_head_before: fc17f0c9e02d6c0456566a8d279b41e081a17d1d
plan_head_after: afe4c416ddc64339efccdb30c9e9535b9aaef36b

actuals:
  tokens: 9000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Accuracy totals are a positive source list, so a new DrillSource stays off the Accuracy board until added on purpose"

key-files:
  created: []
  modified:
    - app/repositories/train_leaderboard_repository.py
    - tests/repositories/test_train_leaderboard_repository.py
    - app/services/activity_queries.py
    - frontend/src/pages/activity/render.js
    - frontend/src/pages/activity/ActivityPage.tsx
    - frontend/scripts/check-activity-layout.mjs
    - frontend/src/types/activity.ts
    - docs/activity-dashboard.md

key-decisions:
  - "The retired filler row is labelled 'Sharp filler (retired)', not 'Sharp filler · lichess (retired)': the longer label overlapped the value text at 320 and 360 px in the layout harness (D-19 gave the longer copy as an example only)"
  - "non_filler_* field names kept (frozen weekly standings use them); only the filter and comments changed"

requirements-completed: [D-18, D-19]

coverage:
  - id: D1
    description: "A solved foreign blunder and a legacy filler count on points and puzzles but not in the Accuracy totals; own puzzles and herrings count on both"
    requirement: "D-18"
    verification:
      - kind: unit
        ref: "tests/repositories/test_train_leaderboard_repository.py#test_foreign_and_legacy_filler_solves_count_on_points_but_not_on_accuracy"
        status: pass
    human_judgment: false
  - id: D2
    description: "The admin Activity breakdown has its own row for source 3 and keeps the relabelled retired source 2 row, never merged"
    requirement: "D-19"
    verification:
      - kind: unit
        ref: "tests/test_admin_activity_stats.py#test_fetch_puzzle_difficulty_splits_by_source"
        status: pass
      - kind: command
        ref: "npm --prefix frontend run check:activity-layout"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-11-23
status: complete
---

# Phase 263 Plan 05: Boards and Activity for the Foreign Source Summary

**The Accuracy board totals come from a positive list of own puzzles and red herrings, so foreign blunders earn points but not accuracy, and the admin Activity breakdown shows foreign blunders as their own row beside a retired lichess filler row.**

## Accomplishments

- `_NON_FILLER` (`source != SHARP_FILLER`) replaced by `_ACCURACY_SOURCES` (`source IN (SR_ITEM, RED_HERRING)`) at both aggregate sites (weekly aggregate and session contribution). `SolveTotals` comment updated; the `non_filler_*` names stay.
- New test `test_foreign_and_legacy_filler_solves_count_on_points_but_not_on_accuracy` seeds one good solve per source: points 12, puzzles 4, non_filler_points 6, non_filler_puzzles 2.
- `PZ_DIFF_ROWS` is own flaw (0), herring (1), "Similar player's blunder" (3), "Sharp filler (retired)" (2). Card note, `types/activity.ts` comment, `docs/activity-dashboard.md`, the `fetch_puzzle_difficulty` docstring and the layout harness fixture (now four rows) are in step. The SQL needed no change.

## Task Commits

1. RED test - `142b5a18a`
2. GREEN, accuracy filter - `05e08e5f3`
3. Task 2, Activity rows, note, harness, docs - `afe4c416d`

## Mutation check

With the old not-a-filler filter the new test fails: `non_filler_puzzles` is 3 instead of 2 and `non_filler_points` 9 instead of 6 (observed at the RED commit, before the filter change).
`test_fetch_puzzle_difficulty_splits_by_source` already carried a source 3 row from plan 263-01 and asserts it comes back as its own row with source 2 separate, so no test edit was needed there.

## Verification (observed)

- `uv run pytest -n auto`: 7094 passed, 9 skipped
- `uv run ruff format --check` and `ruff check .`: clean
- `uv run ty check app/ tests/ scripts/`: clean
- `check_function_size.py app/ --fail-over-depth 4`: no breaches
- Frontend: `npm run lint` exit 0, `npm run build` exit 0, `npm test -- --run` 382 files / 6862 tests passed, `npm run knip` exit 0, `check:activity-layout` OK at 320/360/390/414 px
- Acceptance: `_ACCURACY_SOURCES` 6 occurrences, `_NON_FILLER` 0; "Similar player's blunder" and "(retired)" present in `render.js`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retired-filler label overflowed the chart row**
- **Found during:** Task 2, layout harness
- **Issue:** "Sharp filler · lichess (retired)" overlapped the "100% good" value text at 320 and 360 px (harness FAIL).
- **Fix:** label shortened to "Sharp filler (retired)" in `render.js` and the harness fixture. The card note still explains that the filler is a lichess puzzle.
- **Files modified:** `frontend/src/pages/activity/render.js`, `frontend/scripts/check-activity-layout.mjs`
- **Commit:** afe4c416d

**2. [Plan-literal tweak]** `tests/test_admin_activity_stats.py` was listed as modified, but it already held the source 3 row and assertions, so it is unchanged. The plan's "module docstring lines that say source != SHARP_FILLER" did not exist in the repository file; only the `SolveTotals` field comment was rewritten. `npm run build` was run (the plan skipped it for concurrency; plans run sequentially here).

**Total deviations:** 1 auto-fixed (label length), 1 plan-literal note. **Impact:** none on behavior.

## Issues Encountered

None. The `MissingGreenlet` connection-close message in the teardown log of the DB tests is pre-existing noise, not a failure.

## Known Stubs

None.

## Threat Flags

None. T-263-14 is mitigated (positive list plus four-source test).

## Self-Check: PASSED

- Commits `142b5a18a`, `05e08e5f3`, `afe4c416d` are ancestors of HEAD.
- All modified files exist; working tree clean before this SUMMARY.
