---
phase: quick-260519-lu0
plan: 01
status: incomplete
subsystem: openings+endgames+frontend
tags: [score-eval-charts, games-subtab, shared-component, stats-alignment, tdd]
tech-stack:
  added: []
  patterns:
    - shared PositionResultsPanel component (WDL + Score + Eval three-row panel)
    - _build_wdl_stats cross-module import (openings_service -> endgame_service)
    - compute_eval_confidence_bucket reuse for endgame per-category eval aggregation
key-files:
  created:
    - frontend/src/components/charts/PositionResultsPanel.tsx
  modified:
    - frontend/src/pages/openings/ExplorerTab.tsx
    - frontend/src/pages/openings/GamesTab.tsx
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - app/schemas/endgames.py
    - frontend/src/types/endgames.ts
    - frontend/src/pages/Endgames.tsx
    - tests/test_endgame_service.py
    - tests/test_endgames_router.py
decisions:
  - _build_wdl_stats imported cross-module (no circular import needed a shared module)
  - eval_baseline_pawns = EVAL_BASELINE_PAWNS_WHITE (0.25) for color-agnostic endgame stats
  - score_p_value backward compat preserved (gated to None below PVALUE_RELIABILITY_MIN_N=10)
metrics:
  duration: ~25 minutes
  completed: 2026-05-19T14:10:00Z
  tasks_completed: 5
  tasks_total: 6
  files_changed: 9
---

# Phase quick-260519-lu0 Plan 01: Score/Eval Charts in Games Subtabs Summary

**One-liner:** Score + Eval bullet panel extracted into shared PositionResultsPanel; Openings GamesTab and Endgames gamesContent now show WDL + Score + Eval matching the move explorer; endgame stats backend extended with Wilson score + MG-entry eval per category via shared helpers.

## Status: Awaiting Human Verification

All 5 auto tasks completed and committed. The plan has a blocking `checkpoint:human-verify` task (Task 6) requiring visual verification in the browser. See "Manual Verification Required" section below.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Extract shared PositionResultsPanel component | a8e6c286 | frontend/src/components/charts/PositionResultsPanel.tsx (created) |
| 2 | Render panel in ExplorerTab and Openings GamesTab | 1d314e94 | ExplorerTab.tsx, GamesTab.tsx |
| 3 | Backend: Wilson score + MG-entry eval per endgame category | 6d7eb100 | endgame_repository.py, endgame_service.py, endgames.py |
| 4 | Backend tests | 7251ce33 | tests/test_endgame_service.py, tests/test_endgames_router.py |
| 5 | Frontend: Endgames type alignment + PositionResultsPanel in gamesContent | 458021e8 | endgames.ts, Endgames.tsx |

## Manual Verification Required

The plan requires browser visual inspection before it can be marked complete. Steps:

1. Run the backend (`uv run uvicorn app.main:app --reload`, dev DB up) and frontend dev server (`npm run dev` in `frontend/`).
2. **Openings > Explorer (Moves tab):** Navigate to a position with games. The move-explorer "Results played as White/Black" panel must look identical to before (WDL bar, Score %, Eval rows).
3. **Openings > Games tab:** The same WDL + Score bullet + Eval bullet panel must appear above the game list. Score and Eval popovers open. "Games:" count is plain text (not a self-link).
4. Pick an Openings position/filter with no MG-entry eval data: confirm the Eval row shows an em-dash (not a broken chart).
5. **Endgames > Games tab:** Pick an endgame category with games. Confirm WDL + Score bullet + Eval bullet panel renders below. Score and Eval popovers open. Values look sane.
6. Pick an endgame category with no usable eval: confirm Eval row shows em-dash.
7. Resize to mobile width: both Games-subtab panels (Openings and Endgames) render correctly.
8. **Regression:** Endgames Stats subtab cards (EndgameTypeCard) still render their Score bullet correctly.

Type "approved" or describe visual/behavioral issues to continue.

## Implementation Notes

### No eval backfill needed
The endgame span-entry rows already carry `eval_cp`/`eval_mate` via `query_endgame_entry_rows` (repository projection, lines 251-252). No data migration was required.

### _build_wdl_stats import decision
The function was imported directly from `app.services.openings_service` into `app.services.endgame_service`. There is no circular import (openings_service does not import from endgame_service). A shared module (`app/services/wdl_stats.py`) was not needed. The import is documented as a deliberate cross-module reuse.

### Eval baseline decision (color-agnostic)
`eval_baseline_pawns = EVAL_BASELINE_PAWNS_WHITE` (0.25) is always used for endgame stats because endgame stats apply no color filter (D-02, both colors mixed per category). There is no single "color" to pick the baseline from. This matches the existing `color is None -> white baseline` convention in `openings_service.analyze`. The Eval bullet tick will always sit at +0.25 on the Endgames Games subtab. Documented in the plan risk section.

### score_p_value backward compatibility
`score_p_value` retains its existing gated semantics (`None when total < PVALUE_RELIABILITY_MIN_N=10`) for `EndgameTypeCard` Stats subtab. The new ungated `p_value` field (from `_build_wdl_stats`) is additive and separate. Both are serialized to the API response. Tests assert both independently.

### Endgame eval coverage
The eval cohort is per-span at endgame entry (user-perspective cp; mate excluded, NULL excluded, `|cp| >= 2000` trimmed). If a category's spans lack eval_cp (e.g., engine not yet backfilled, or all mate positions), `eval_n = 0` and the Eval row in `PositionResultsPanel` shows an em-dash. The panel already handles this gracefully.

### Mobile coverage
- **Openings:** `gamesTabEl` is a single shared element rendered at desktop (Openings.tsx line 865) and mobile (line 1176) — one change covers both.
- **Endgames:** `gamesContent` is a single shared element rendered at desktop (Endgames.tsx line 759) and mobile (line 846) — one change covers both.

## Automated Gates (All Passing)

- `uv run ruff check app/` — passed
- `uv run ty check app/ tests/` — zero errors
- `uv run pytest tests/test_endgame_service.py tests/test_endgames_router.py` — 318 passed
- `npx tsc --noEmit` — clean
- `npm run knip` — clean
- `npm run lint` — clean
- `npm test` — 576 passed (49 test files)

## Deviations from Plan

None during the plan tasks. One post-checkpoint fix during human UAT (commit `a7e99a7a`):
the shared `EvalConfidenceTooltip` was hardcoded with the openings phrasing
("average Stockfish eval at the *end* of your openings"), which mislabeled the
Endgames Games-subtab Eval bullet (the underlying math was already correct —
endgame span-entry `eval_cp` via `compute_eval_confidence_bucket`; this was a copy
bug, not a math bug). Added an `evalContext: 'opening-end' | 'endgame-entry'` prop
threaded `PositionResultsPanel → BulletConfidencePopover → EvalConfidenceTooltip`.
In `endgame-entry` mode the copy now reads "average Stockfish eval at the position
where the endgame begins" and the opening-only per-color +0.25 baseline tick (and
its legend line) is dropped, matching the Stats-tab "Endgame Entry Eval" framing.
Openings/move-explorer unchanged (default `opening-end`). Gates re-run green:
tsc/lint/knip clean, frontend 576 passed.

## Known Stubs

None. All data flows are wired; no placeholder values.

## Threat Flags

None. This plan adds no new network endpoints, auth paths, or file access patterns.

## Self-Check: PASSED

- frontend/src/components/charts/PositionResultsPanel.tsx — FOUND
- frontend/src/pages/openings/ExplorerTab.tsx — FOUND (updated)
- frontend/src/pages/openings/GamesTab.tsx — FOUND (updated)
- app/repositories/endgame_repository.py — FOUND (updated)
- app/services/endgame_service.py — FOUND (updated)
- app/schemas/endgames.py — FOUND (updated)
- frontend/src/types/endgames.ts — FOUND (updated)
- frontend/src/pages/Endgames.tsx — FOUND (updated)
- tests/test_endgame_service.py — FOUND (updated)
- tests/test_endgames_router.py — FOUND (updated)
- Commits a8e6c286, 1d314e94, 6d7eb100, 7251ce33, 458021e8 — all in git log
