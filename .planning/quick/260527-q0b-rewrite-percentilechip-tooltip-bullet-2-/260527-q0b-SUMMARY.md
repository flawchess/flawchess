---
phase: quick-260527-q0b
plan: 01
type: execute
completed: 2026-05-27
status: complete
commits:
  - 9cbf8830: "feat(quick-260527-q0b): add PerTcBreakdownOut + thread per-TC breakdowns"
  - d3b18642: "feat(quick-260527-q0b): rewrite PercentileChip tooltip bullet 2 with per-TC breakdown"
key-files:
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/PercentileChip.tsx
    - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
    - frontend/src/components/charts/EndgameMetricCard.tsx
    - frontend/src/components/charts/EndgameMetricsSection.tsx
    - frontend/src/components/charts/EndgameTimePressureCard.tsx
    - frontend/src/components/charts/__tests__/PercentileChip.test.tsx
metrics:
  duration_minutes: ~25
  tasks_completed: 3
  files_changed: 9
  diff_lines: "+512 / -10"
---

# Quick Task 260527-q0b: PercentileChip Tooltip Per-TC Breakdown — Summary

Rewrote the `PercentileChipPopoverBody` bullet 2 so it discloses concrete
per-TC game counts, values, and percentiles instead of the misleading
"3000 rated games per time control" copy that suggested users had 3000
games in every TC. Bullets 1, 3, 4 and the Test 9 flame-icon regression
guard remain byte-identical.

## Files Changed

### Backend

- **`app/schemas/endgames.py`** — added `PerTcBreakdownOut` Pydantic model
  (`tc`, `value`, `n_games`, `percentile`). Added 4 `*_per_tc` list fields
  on `ScoreGapMaterialResponse` (score_gap, score_gap_conv, score_gap_parity,
  recovery_score_gap), one `achievable_score_gap_per_tc` on
  `EndgamePerformanceResponse`, and 6 scalar fields on `TimePressureTcCard`
  (3 chips × `_n_games` / `_value`). All new fields default to `[]` / `None`
  to preserve back-compat with existing constructor call sites.

- **`app/services/endgame_service.py`** — added `_build_per_tc_breakdown`
  + `_per_tc_game_counts` helpers next to `_aggregate_per_tc_percentile`.
  Threaded a single per-TC game-count dict through the orchestrator (one
  source of truth) into both `_compute_score_gap_material` and
  `_get_endgame_performance_from_rows`. Wired the 6 new scalar fields on
  `TimePressureTcCard` from the chip-cohort `PercentileRow.value` /
  `PercentileRow.n_games` at the existing per-TC lookup.

### Frontend

- **`frontend/src/types/endgames.ts`** — mirrored backend with
  `PerTcBreakdownOut`, the 5 new aggregated-chip list fields, and 6 new
  optional per-TC card scalar fields.

- **`frontend/src/components/charts/PercentileChip.tsx`** — extended
  `PercentileChipProps` with `perTcBreakdown?`, `nGames?`, `value?`. Added
  `formatChipValue` dispatcher (signed 2-decimal for the score family;
  signed integer percent for `clock-gap` + `net-flag-rate`) and a small
  `clampPercentInt` helper matching the chip-face floor/ceiling. Rewrote
  bullet 2 with two code paths:
    - **Aggregated (`tc === undefined`)**: leading "weighted average of
      `<metric>` percentiles" line followed by a per-TC `<ul>` with one
      `<li>` per entry. Per CONTEXT D-locked branches: above-floor with
      percentile → full line; above-floor with null percentile → DROP
      entry; below-floor with games > 0 → "insufficient games"; zero-
      games → defensive drop. Falls back to the legacy single-line copy
      when `perTcBreakdown` is undefined or filters to empty.
    - **Per-TC (`tc !== undefined`)**: single line "Based on `<n>` of your
      recent `<tc>` games over the last 36 months, vs opponents within
      +/-100 Elo. Your value: `<value>`." Falls back to the legacy copy
      when `nGames` / `value` are missing.
  Bullet 2 is rendered inside `<div>` (not `<p>`) so the `<ul>` is valid
  HTML.

- **`frontend/src/components/charts/EndgameOverallPerformanceSection.tsx`** —
  passes `perTcBreakdown` to the Achievable Score Gap and Endgame Score
  Gap chips.

- **`frontend/src/components/charts/EndgameMetricCard.tsx`** — added
  `scoreGapPerTc?: PerTcBreakdownOut[]` prop, threaded into the
  Conversion / Parity / Recovery chip.

- **`frontend/src/components/charts/EndgameMetricsSection.tsx`** — passes
  `data.score_gap_conv_per_tc` / `score_gap_parity_per_tc` /
  `recovery_score_gap_per_tc` down to the 3 metric cards.

- **`frontend/src/components/charts/EndgameTimePressureCard.tsx`** —
  passes `nGames` + `value` to the 3 per-TC chips
  (`time-pressure-score-gap`, `clock-gap`, `net-flag-rate`).

- **`frontend/src/components/charts/__tests__/PercentileChip.test.tsx`** —
  replaced the 2 legacy bullet-2 tests with 8 new tests covering all 4
  aggregated branch semantics, the per-TC simplified framing for all 3
  per-TC flavors, per-flavor coverage of the 5 aggregated flavors, and
  fallback paths for missing-fields legacy fixtures. Test 9 (no-flame
  regression guard) preserved byte-identical.

## Bullets 1, 3, 4 Untouched

Verified: `git diff 0436525444 HEAD -- frontend/src/components/charts/PercentileChip.tsx`
shows changes only inside the `bullet2` block, the popover-body interface,
the outer prop interface, and the imports. Bullet 1 (direct percentile
statement), bullet 3 (`COPY_FILTER_INDEPENDENCE`), and bullet 4 (4-branch
blended-anchor disclosure) are byte-identical.

## Test 9 Flame Regression Guard

Verified: `git diff` for the test file shows no lines mentioning
`flame` / `Flame`. The `describe('PercentileChip — NO flame icon ...')`
block at lines 273-298 (post-edit) is byte-identical.

## Pre-PR Checklist (Task 3) — All Green

| Step                                       | Result        |
| ------------------------------------------ | ------------- |
| `uv run ruff format app/ tests/`           | no changes    |
| `uv run ruff check app/ tests/ --fix`      | All checks passed! |
| `uv run ty check app/ tests/`              | zero errors   |
| `uv run pytest -x`                         | 2187 passed, 16 skipped |
| `cd frontend && npm run lint`              | clean         |
| `cd frontend && npm run knip`              | clean         |
| `cd frontend && npm test -- --run`         | 691 / 691 pass (56 files) |

## Deviations from Plan

None. The plan was executed exactly as written. Two minor process notes:

1. **Worktree path confusion (recovered):** the first round of Task 1
   edits resolved absolute paths to the main repo working tree (not the
   worktree). Recovered by copying the modified files into the worktree
   and `git checkout --`-reverting the main repo. Both task commits live
   in the worktree on `worktree-agent-aa86c648418833998`. No data lost.
2. **Bullet 2 wrapper:** changed the wrapping element from `<p>` to
   `<div>` so the new `<ul>` inside bullet 2's aggregated path is valid
   HTML. Bullets 1 and 3 still use `<p>`.

## Self-Check: PASSED

- `app/schemas/endgames.py` — FOUND (`PerTcBreakdownOut` defined, 5 aggregated
  list fields + 6 per-TC scalar fields verified via `grep`).
- `app/services/endgame_service.py` — FOUND (`_build_per_tc_breakdown`,
  `_per_tc_game_counts` helpers, threading in orchestrator verified).
- `frontend/src/types/endgames.ts` — FOUND (mirror interface + new fields).
- `frontend/src/components/charts/PercentileChip.tsx` — FOUND (rewritten
  bullet 2, 4 callers plumbed).
- `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` —
  FOUND (8 new bullet-2 tests; Test 9 untouched).
- Commit `9cbf8830` — FOUND in `git log`.
- Commit `d3b18642` — FOUND in `git log`.
