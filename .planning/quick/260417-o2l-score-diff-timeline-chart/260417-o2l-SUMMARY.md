---
id: 260417-o2l
type: quick
title: Score % Difference timeline chart in Games with vs without Endgame
status: complete
---

# Quick Task 260417-o2l — Summary

Added a weekly rolling-window timeline chart showing Score % Difference
(endgame Score % minus non-endgame Score %) directly below the
"Games with vs without Endgame" table.

## Backend

- `app/schemas/endgames.py`
  - New `ScoreGapTimelinePoint` model (`date`, `score_difference`,
    `endgame_game_count`, `non_endgame_game_count`).
  - `ScoreGapMaterialResponse` extended with `timeline` and
    `timeline_window` fields.

- `app/services/endgame_service.py`
  - New constant `SCORE_GAP_TIMELINE_WINDOW = 100`.
  - New `_compute_score_gap_timeline(endgame_rows, non_endgame_rows, window)`:
    tags each row by side, merges chronologically, maintains separate trailing
    100-game windows for endgame and non-endgame games, emits one point per
    ISO week with the rolling `endgame_score - non_endgame_score`. Drops weeks
    where either side has fewer than `MIN_GAMES_FOR_TIMELINE` (=10) games.
  - `_compute_score_gap_material` extended with optional `endgame_rows` and
    `non_endgame_rows` params; populates the new timeline fields.
  - `get_endgame_overview` now passes the existing performance rows (no
    additional DB query) into `_compute_score_gap_material`.

- `tests/test_endgame_service.py`
  - New `TestComputeScoreGapTimeline` (6 tests):
    empty inputs, MIN_GAMES filter, two-week rolling diff math, window cap,
    null-played-at filter, end-to-end exposure via
    `_compute_score_gap_material`, and a backward-compat case when rows are
    omitted.

## Frontend

- `frontend/src/types/endgames.ts`
  - New `ScoreGapTimelinePoint` interface; extended `ScoreGapMaterialResponse`
    with `timeline` and `timeline_window`.

- `frontend/src/components/charts/EndgamePerformanceSection.tsx`
  - New `ScoreDiffTimelineChart` component rendered below the desktop table
    and mobile cards. Single Recharts `LineChart`:
    - X-axis: weekly date ticks via `createDateTickFormatter`.
    - Y-axis: fixed ±20 pp domain with ticks at -20/-10/0/10/20, signed
      `+N%` / `-N%` formatter, vertical "Score diff %" label outside the
      chart on desktop.
    - Three `ReferenceArea` zones at ±5 pp (matches the table's parity
      neutral threshold) with red/blue/green backgrounds at 0.15 opacity.
    - Dashed `ReferenceLine` at y=0.
    - Dots colored by zone; tooltip shows "Week of {full date}", signed
      diff %, and per-side game counts.
    - Empty state: chart hidden when `timeline.length === 0`.
  - data-testids: `score-diff-timeline-section`, `score-diff-timeline-chart`,
    `score-diff-timeline-info`.

## Verification

- `uv run ruff check app/ tests/` — clean
- `uv run ty check app/ tests/` — clean
- `uv run pytest` — 782 passed
- `cd frontend && npm run lint` — clean (pre-existing coverage warnings only)
- `cd frontend && npm run knip` — clean
- `cd frontend && npm run build` — built successfully
- `cd frontend && npm test -- --run` — 73 passed

## Notes

- Working on `main` branch — per project policy, changes are NOT committed
  by `/gsd-quick`. The user can stage + commit when ready.
- Browser smoke test deferred to user (no dev server started in this run).
