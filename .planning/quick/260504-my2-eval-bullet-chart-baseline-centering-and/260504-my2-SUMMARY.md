---
quick_id: 260504-my2
phase: quick
type: quick
tags: [phase-80, opening-stats, eval-bullet-chart, baseline-centering, recalibration]
key-files:
  modified:
    - app/services/opening_insights_constants.py
    - app/services/stats_service.py
    - app/services/eval_confidence.py
    - app/schemas/stats.py
    - tests/services/test_eval_confidence.py
    - tests/test_stats_schemas.py
    - frontend/src/types/stats.ts
    - frontend/src/lib/openingStatsZones.ts
    - frontend/src/lib/__tests__/openingStatsZones.test.ts
    - frontend/src/components/charts/MiniBulletChart.tsx
    - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx
    - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
    - frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx
    - frontend/src/pages/Openings.tsx
decisions:
  - "buildMgEvalHeaderTooltip lives in openingStatsZones.ts (not MostPlayedOpeningsTable.tsx) to avoid the react-refresh/only-export-components lint error from co-locating non-component exports with the component."
  - "Neutral band widens from ±0.20 to ±0.25 pawns. With baseline-centering active, a quarter-pawn delta from the active baseline is treated as indistinguishable; the previous ±0.20 bound was calibrated when the chart centered on zero."
  - "Bookmark sections (chart bookmarks, no per-API baseline) fall back to EVAL_BASELINE_PAWNS_WHITE / BLACK lib constants when mostPlayedData is undefined; otherwise they prefer the API value so the visual stays consistent with the most-played sections."
metrics:
  tasks_completed: 3
  commits: 6
  files_modified: 14
---

# Quick Task 260504-my2: Eval Bullet Chart Baseline-Centering & Per-Game-Mean Recalibration Summary

Recalibrated the engine-asymmetry baselines from 2026-03 medians (28 / -20 cp) to 2026-05-04 per-game means (31.5 / -18.9 cp), surfaced them in MostPlayedOpeningsResponse, added a `center` prop to MiniBulletChart so the bullet visual matches the per-row z-test reference, centralized the zone-color helper in openingStatsZones.ts, and wired the centered chart through the desktop table, mobile renderer, and per-row tooltip.

## Tasks Completed

### Task 1 — Recalibrate backend baselines and surface eval_baseline_pawns_{white,black}

- `EVAL_BASELINE_CP_WHITE` is now `float = 31.5`; `EVAL_BASELINE_CP_BLACK` is `float = -18.9`.
- Comment block in `opening_insights_constants.py` cites `reports/benchmarks-2026-05-04.md` (per-game mean, n=1.25M trimmed games).
- `_baseline_cp_for_color` docstring refreshed to "per-game mean, 2026-05 Lichess benchmark" with new numbers.
- `eval_confidence.py` module docstring updated to cite +31.5 / -18.9.
- `MostPlayedOpeningsResponse` carries two new required `float` fields (`eval_baseline_pawns_white`, `eval_baseline_pawns_black`); populated in `get_most_played_openings` from `_baseline_cp_for_color('white'|'black') / 100.0`.
- New schema test in `tests/test_stats_schemas.py` asserts wrapper round-trips the eval baselines via `model_dump()`.
- Comments in `tests/services/test_eval_confidence.py` referencing the old `+28` / `-20` numbers updated to `+31.5` / `-18.9`. Existing assertions remain symbolic via `float(EVAL_BASELINE_CP_WHITE)` / `_BLACK` and continue to hold under the new constants (z=31.5/5=6.3 still gives p<<0.001 for the white-baseline test).

Commits: 5a468ba (RED) -> ce2670f (GREEN).

### Task 2 — `center` prop on MiniBulletChart, widened neutral zone, shared evalZoneColor

- `MiniBulletChart` accepts `center?: number` (default `0`). With `center=0` every existing call site renders identically (verified by the legacy zero-centered test).
- Reference line, neutral-band shading, bar-from-center fill, and zone-color test all shift to the active center. Neutral-band bounds are computed as `center + neutralMin/Max` in absolute eval space.
- Tick-suppression condition checks `Math.abs(absNeutralMin - center) > BOUNDARY_EPSILON` (collapses to legacy `Math.abs(neutralMin)` at center=0).
- `EVAL_NEUTRAL_MIN_PAWNS` widened to `-0.25`; `EVAL_NEUTRAL_MAX_PAWNS` widened to `+0.25`.
- New constants exported from `openingStatsZones.ts`: `EVAL_BASELINE_PAWNS_WHITE = 0.315`, `EVAL_BASELINE_PAWNS_BLACK = -0.189`.
- New shared helper `evalZoneColor(value, center)` exported from `openingStatsZones.ts` (uses `delta = value - center`).
- New tests cover white/black/zero centers, marker-at-center alignment, default-center regression, and non-zero center reference-line shift.

Commits: ac31d28 (RED) -> ded1808 (GREEN).

### Task 3 — Wire baseline-centered chart through MostPlayedOpeningsTable + mobile + tooltip

- `MostPlayedOpeningsResponse` (TypeScript) declares `eval_baseline_pawns_white` and `eval_baseline_pawns_black` (both required `number`).
- `MostPlayedOpeningsTableProps` adds required `evalBaselinePawns: number`. `OpeningRow` threads it to its `MiniBulletChart center={evalBaselinePawns}` and to `evalZoneColor(value, evalBaselinePawns)` for the text-cell color.
- `MobileMostPlayedRows` (in `Openings.tsx`) accepts `evalBaselinePawns` and uses it identically.
- Local `evalZoneColor` definitions in `MostPlayedOpeningsTable.tsx` and `Openings.tsx` deleted; both now import from `@/lib/openingStatsZones`.
- `MG_EVAL_HEADER_TOOLTIP` (string constant) replaced by `buildMgEvalHeaderTooltip(evalBaselinePawns)` (function). The tooltip text explains baseline-centering and surfaces the active baseline as a signed two-decimal number (no em-dashes per CLAUDE.md).
- Bookmark sections (chart bookmarks; no per-API baseline) fall back to `EVAL_BASELINE_PAWNS_WHITE` / `EVAL_BASELINE_PAWNS_BLACK` when `mostPlayedData` is undefined; otherwise they prefer the API value.
- Most-played sections use `mostPlayedData.eval_baseline_pawns_white` / `_black` for their respective color.
- Test `renderTable` helper takes optional `evalBaselinePawns` (default `0`); existing assertions continue to pass under the legacy zero-centered behavior.
- New tests assert text-cell color reflects baseline-centered zone (white-baseline row at avg=0.32 is neutral, at avg=0.65 is success, at avg=0.0 is danger).

Commits: 22da709 (RED) -> 147b883 (GREEN).

## Verification Results

### Backend gate

```
uv run ruff check .       -> All checks passed
uv run ty check app/ tests/ -> All checks passed
uv run pytest             -> 1238 passed, 6 skipped
```

### Frontend gate

```
npm run lint              -> 0 errors (3 pre-existing warnings in coverage/*.js, unrelated)
npm test -- --run         -> 271 passed (24 files)
npm run knip              -> clean (no dead exports / unused deps)
npm run build             -> built in 5.06s, PWA generated
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Pre-existing failing tests in `MostPlayedOpeningsTable.test.tsx`**

- **Found during:** Task 3 RED setup
- **Issue:** Two tests asserted `popover?.dataset.preface` and `MG_EVAL_HEADER_TOOLTIP` contain `'across analyzed games'`, but the live constant didn't include that phrase. The tests were already failing on HEAD before any of my changes.
- **Fix:** Replaced with assertions against the new tooltip text (`'Position relative to the center'`) and added a baseline-numeric assertion. Aligned with the plan's instruction to migrate every call site away from `MG_EVAL_HEADER_TOOLTIP` and assert against substrings of the new tooltip.
- **Files modified:** `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx`
- **Commit:** 22da709 (RED) / 147b883 (GREEN)

**2. [Rule 3 — Blocking issue] `buildMgEvalHeaderTooltip` placement**

- **Found during:** Task 3 lint gate
- **Issue:** The plan instructed exporting `buildMgEvalHeaderTooltip` from `MostPlayedOpeningsTable.tsx`. ESLint's `react-refresh/only-export-components` rule rejected this — Vite Fast Refresh requires component files to export only components.
- **Fix:** Moved the function to `frontend/src/lib/openingStatsZones.ts` (where the related baseline constants and `evalZoneColor` live). Updated the import in `MostPlayedOpeningsTable.tsx`, the test file, and `Openings.tsx`.
- **Rationale:** `openingStatsZones.ts` already houses every other piece of the baseline-centering API surface (constants + `evalZoneColor`), so the tooltip builder is a natural fit there. No change in behavior; only the import path differs from the plan's literal instruction.
- **Files modified:** `frontend/src/lib/openingStatsZones.ts`, `frontend/src/components/stats/MostPlayedOpeningsTable.tsx`, `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx`, `frontend/src/pages/Openings.tsx`
- **Commit:** 147b883

### Out-of-scope deferrals

**Pre-existing repo-wide ruff format drift.** `uv run ruff format --check .` reports 91 files would be reformatted on HEAD before any of my changes. Running `ruff format .` repo-wide was out of scope per the deviation scope boundary. I formatted only the files I modified — `app/services/stats_service.py` was the one file in my touchset that had pre-existing drift, which `ruff format` cleanly fixed (whitespace + line-wrapping nits, no behavioral change).

## Self-Check

**Files exist:**
- FOUND: `app/services/opening_insights_constants.py`
- FOUND: `app/services/stats_service.py`
- FOUND: `app/services/eval_confidence.py`
- FOUND: `app/schemas/stats.py`
- FOUND: `tests/services/test_eval_confidence.py`
- FOUND: `tests/test_stats_schemas.py`
- FOUND: `frontend/src/types/stats.ts`
- FOUND: `frontend/src/lib/openingStatsZones.ts`
- FOUND: `frontend/src/lib/__tests__/openingStatsZones.test.ts`
- FOUND: `frontend/src/components/charts/MiniBulletChart.tsx`
- FOUND: `frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx`
- FOUND: `frontend/src/components/stats/MostPlayedOpeningsTable.tsx`
- FOUND: `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx`
- FOUND: `frontend/src/pages/Openings.tsx`

**Commits exist (6 commits, oldest first):**
- FOUND: 5a468ba — test(260504-my2): add failing test for MostPlayedOpeningsResponse eval baselines
- FOUND: ce2670f — feat(260504-my2): recalibrate eval baselines to 31.5/-18.9 cp and surface them in MostPlayedOpeningsResponse
- FOUND: ac31d28 — test(260504-my2): add failing tests for evalZoneColor + MiniBulletChart center prop
- FOUND: ded1808 — feat(260504-my2): add center prop to MiniBulletChart and shared evalZoneColor helper
- FOUND: 22da709 — test(260504-my2): add failing tests for evalBaselinePawns prop and buildMgEvalHeaderTooltip
- FOUND: 147b883 — feat(260504-my2): wire baseline-centered chart through MPO table, mobile renderer, and tooltip

## Self-Check: PASSED
