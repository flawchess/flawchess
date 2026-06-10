---
phase: quick-260610-vru
plan: "01"
subsystem: library-ui
tags: [frontend, library, flaw-card, game-card, ui-polish]
dependency_graph:
  requires: []
  provides: [clock_seconds-on-FlawListItem, move_seconds-on-FlawListItem, opponent-only-flaw-header, clock-move-time-metadata, games-2col-grid, no-engine-analysis-message]
  affects: [FlawCard, LibraryGameCard, LibraryGameCardList, FlawsTab]
tech_stack:
  added: []
  patterns: [left-join-aliased-game-positions, css-grid-col-span]
key_files:
  created:
    - frontend/src/components/library/NoEngineAnalysisFlawsState.tsx
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - frontend/src/types/library.ts
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/results/LibraryGameCardList.tsx
    - frontend/src/pages/library/FlawsTab.tsx
decisions:
  - "Inlined _compute_move_seconds helper in repo (not importing private _move_time from flaws_service) per plan instructions"
  - "Removed formatTimeControl + SECONDS_PER_DAY from FlawCard as they became dead code after TC line removal"
  - "Single header span on FlawCard covers both desktop and mobile (no hidden/visible responsive pair needed for opponent-only text)"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-10"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 8
---

# Phase quick-260610-vru Plan 01: Library Card Layout Polish Summary

Polish the Library page card layout: clock context on flaw cards, opponent-only headers, 2-column Games grid, and an "engine analysis coming soon" message for the Flaws tab.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add clock_seconds + move_seconds to FlawListItem (backend + TS) | 8fcd34ce |
| 2 | FlawCard: opponent-only header, clock/move-time line, drop termination | a72d52cd |
| 3 | Games card move-count line, 2-col grid, Flaws no-analysis message | 938bb15e |

## What Was Built

**Task 1 — Backend data addition:**
- Added `clock_seconds: float | None` and `move_seconds: float | None` to `FlawListItem` Pydantic model in `app/schemas/library.py`
- Added a third aliased `GamePosition` join (`PositionTwoBefore`, ply=N-2) to `query_flaws` in `app/repositories/library_repository.py` to source the same-side previous clock (Pitfall 2: same-side is two plies back, not one)
- Added `_compute_move_seconds` helper mirroring `flaws_service._move_time` formula inline (import avoidance per plan)
- Mirrored both fields in `FlawListItem` TypeScript interface with matching nullability and brief JSDoc comments

**Task 2 — FlawCard frontend changes:**
- Header shows only the opponent: `vs <glyph><name> <rating>` on both desktop and mobile (single span, no responsive branches)
- TC + move count lines replaced by a `<Clock> mm:ss (Move Ns)` line; gracefully omits clock part when `clock_seconds` is null, move-time suffix when `move_seconds` is null, and the whole item when both are null
- Removed `terminationItem` and dead `RESULT_CLASSES`, `RESULT_ICONS`, `resultIndicator` code
- Removed dead imports: `cn`, `Hash`, `Plus`, `Equal`, `Minus`, `LucideIcon`, `UserResult`, `plysToFullMoves`, `formatTimeControl`, `SECONDS_PER_DAY`
- Added local `formatClock(seconds) -> "mm:ss"` helper (D-05 forbids shared import from EvalChart)

**Task 3 — Three independent UI changes:**
- `LibraryGameCard` metadata block: `timeControlItem` and `moveCountItem` now on separate lines (removed the shared `flex-wrap` row that grouped them)
- `LibraryGameCardList` card stack: switched from `flex flex-col` to `grid grid-cols-1 md:grid-cols-2 gap-2`; analyzed games get `md:col-span-2` (full width), unanalyzed get `md:col-span-1` (half width); each card wrapped in a div carrying the span class
- New `NoEngineAnalysisFlawsState` component: amber Cpu icon, "Engine analysis coming soon" h2, two muted `text-sm` paragraphs explaining Lichess-only availability and upcoming FlawChess support; `data-testid="flaws-no-engine-analysis"`; `FlawsTab` renders it instead of the generic `EmptyState` when `noMatchedFlaws` is true

## Deviations from Plan

None. Plan executed exactly as written.

## Known Stubs

None. All data is wired: `clock_seconds` / `move_seconds` are populated by the new `PositionTwoBefore` join in the flaw query and consumed by `FlawCard`.

## Threat Flags

No new threat surface introduced. The new LEFT JOIN on `game_positions` is user-scoped (`PositionTwoBefore.user_id == GameFlaw.user_id`) exactly like the existing position joins (T-112-02 pattern). No new endpoints or auth paths.

## Self-Check: PASSED

- NoEngineAnalysisFlawsState.tsx: FOUND
- app/schemas/library.py: FOUND
- frontend/src/types/library.ts: FOUND
- commit 8fcd34ce (task 1): FOUND
- commit a72d52cd (task 2): FOUND
- commit 938bb15e (task 3): FOUND
