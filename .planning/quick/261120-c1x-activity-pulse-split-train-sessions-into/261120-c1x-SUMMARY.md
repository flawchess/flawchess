---
phase: quick-261120-c1x
plan: 01
subsystem: activity-dashboard
tags: [activity-pulse, train, blunder-check, sql, render.js]
status: complete
requirements: [QUICK-261120-c1x]
key-files:
  modified:
    - app/services/activity_queries.py
    - app/services/activity_stats.py
    - tests/test_admin_activity_stats.py
    - frontend/src/types/activity.ts
    - frontend/src/pages/activity/ActivityPage.tsx
    - frontend/src/pages/activity/render.js
    - frontend/src/pages/activity/styles.css
    - frontend/scripts/check-activity-layout.mjs
    - docs/activity-dashboard.md
    - CHANGELOG.md
  created:
    - frontend/src/pages/activity/__tests__/domIds.test.ts
actuals:
  tokens: 60000
  tasks: 3
  commits: 3
plan_head_before: 185554aa173c006f1468b02e5534dd7f38791c4a
plan_head_after: 3b383db9432060f6832c2b8aad2abc0a45545135
---

# Phase quick-261120-c1x Plan 01: Activity Pulse Train split Summary

The Train sessions section is now two sub-headed blocks (Personalized Puzzles, Blunder Check), both using query-time Completed / Open / Abandoned outcomes, with never-started puzzle sessions excluded and the guest Train note removed.

## Commits

- 14ee713e8 feat: backend queries, payload, tests (Task 1)
- 1d7411a72 feat: page shell, render.js, types, styles (Task 2)
- 3b383db94 test: layout fixtures, DOM-id seam test, docs, changelog (Task 3)

## What changed

- `activity_queries.py`: shared SQL fragments `_SESSION_OPEN_NOW`, `_SESSION_ABANDONED`, `_PUZZLE_SESSION_STARTED`; `fetch_train` reworked (takes `today`); new `fetch_blunder_check_sessions` and `fetch_blunder_check_windows`; `fetch_guest_train` and the `guest_train` payload key deleted. The lazy-expiry root cause is commented at the fragments.
- `activity_stats.py`: `today = now_utc.date()` bound into both session fetches; 19 awaited fetch calls / 21 SQL statements documented in the cache comment.
- Frontend: shared `renderSessionOutcomeCard`, `renderBlunderCheckWindowCards` (7-day rolling score from the lead-in, trimmed before plotting), mode-named card titles, `.mode-head` style, tile relabelled "Puzzle sessions".
- Docs: new "Train session outcomes" and "Blunder Check metrics" sections, funnel marked puzzle-only, exact query count.

## Mutation checks (tests bite)

- Open-now `>` changed to `>=`: `test_fetch_train_derives_outcomes_and_skips_unstarted` and `test_fetch_blunder_check_sessions_derives_outcomes` both failed on the boundary row. Restored.
- Solve fallback removed from the started predicate: the puzzle test failed (abandoned 2 instead of 3, row F). Restored.
- `id="c-bc-score"` renamed in ActivityPage.tsx: `domIds.test.ts` failed listing `c-bc-score` as missing. Restored.

## Deviations from Plan

None. One small correction: `fetch_blunder_check_windows` counts users from `blunder_check_windows.user_id` directly instead of joining sessions (the column is denormalized on the window), which is simpler and equivalent.

## Known Stubs

None.

## Threat Flags

None. Only per-day aggregates leave the database; all parameters are bound.

## Verification run

- `uv run pytest tests/test_admin_activity_stats.py`: 44 passed.
- Pre-merge gate: ruff format (no changes), ruff check, ty (app/tests/scripts and analysis/), check_function_size depth 4: all clean. `uv run pytest -n auto -x`: 7197 passed, 19 skipped. Frontend lint clean, `npm run build` ok, `npm run knip` ok, `npm test -- --run`: 375 files / 6619 tests passed, `check:activity-layout` ok at 320/360/390/414.
- Plan grep assertions all met (no guest_train in app/ or frontend/src, no "Still open", c-bc ids >= 4, test ids >= 3, `~16` gone, changelog 2 bullets).
- Not run: browser UAT of /activity.

## Self-Check: PASSED
