---
phase: quick-260529-l1i
plan: 01
subsystem: endgames-percentile-chip
tags: [frontend, backend, tooltip, percentile-chip, rating-anchor]
requires:
  - PerTcBreakdownOut (backend schema + frontend type)
  - user_rating_anchors / fetch_anchors_for_user
provides:
  - PerTcBreakdownOut.anchor (int | None) populated per aggregated metric
  - two-line per-TC tooltip rows with "anchored at ~{anchor} Lichess Elo"
affects:
  - PercentileChip tooltip surface (aggregated chips)
tech-stack:
  added: []
  patterns:
    - additive backend field (back-compat default None)
    - per-row inline disclosure replaces standalone composition paragraph
key-files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/services/test_endgame_service_chip_decoupling.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/PercentileChip.tsx
    - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
    - frontend/src/components/charts/EndgameMetricCard.tsx
    - frontend/src/components/charts/EndgameMetricsSection.tsx
    - frontend/src/components/charts/EndgameTimePressureCard.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/lib/percentileAnchor.ts
    - frontend/src/components/charts/__tests__/PercentileChip.test.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx
    - frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx
    - CHANGELOG.md
decisions:
  - Aggregated chip no longer needs a single anchor; per-TC anchors live inline on each breakdown row.
  - pickDominantTcAnchor deleted (dead after gate change); RatingAnchorsByTc kept (Time Pressure path still uses it).
metrics:
  duration: ~50m
  completed: 2026-05-29
  tasks: 3
  files: 15
---

# Phase quick-260529-l1i Plan 01: Per-TC Rating Anchor in PercentileChip Summary

Moved the per-time-control rating anchor inline into each per-TC breakdown row of the aggregated PercentileChip tooltip (two-line layout) and removed the standalone bottom platform-blend anchor paragraph entirely.

## What Was Built

- **Backend** (`PerTcBreakdownOut.anchor: int | None`): a new additive field defaulting to `None`. `_build_per_tc_breakdown` gained a keyword-only `anchors_by_tc: Mapping[TimeControlBucket, RatingAnchorRow] | None` and sets `anchor` from `RatingAnchorRow.anchor_rating` on both the percentile-row branch and the insufficient-games branch. The arg is threaded through `_compute_score_gap_material` (4 builder calls) and `_get_endgame_performance_from_rows` (1 call). `compute_endgame_overview` now fetches `anchors` once, before building performance + score_gap_material, and reuses the same dict for the existing top-level `rating_anchors` block (single fetch, no duplicate query).
- **Frontend** (`PercentileChip.tsx`): aggregated chip tooltip renders two stacked lines per renderable TC — line 1 `{tc} — anchored at ~{anchor} Lichess Elo` (omitted when `anchor` is null, with a `data-testid="percentile-chip-anchor-{tc}"`), line 2 `{value} over {n} games -> {percentile} percentile`. Bullet 4 (the platform-blend IIFE + its render line) removed entirely. Aggregated bullet 1 reworded to "of similarly-rated players, aggregated across the time controls you play." (no rating number); per-TC bullet 1 unchanged ("of ~{anchor}-rated players in {tc}"). `anchorRating` is now optional; the 4 platform-composition props (`nChesscomGames`, `nLichessGames`, `chesscomMedianNative`, `lichessMedianNative`) removed from props and all call sites.
- **Call-site cleanup**: the two aggregated sections (`EndgameOverallPerformanceSection`, `EndgameMetricCard` via `EndgameMetricsSection`) dropped the `dominantAnchor !== undefined` chip gate (now gate on `percentile != null` only), the `ratingAnchors` prop, and the now-dead `pickDominantTcAnchor`/`RatingAnchorsByTc` import. `Endgames.tsx` stopped threading `ratingAnchors` to those two sections (kept for `EndgameTimePressureSection`). `EndgameTimePressureCard` (3 per-TC chips) kept `anchorRating` and dropped only the 4 platform props. `pickDominantTcAnchor` deleted from `percentileAnchor.ts`; `RatingAnchorsByTc` retained (Time Pressure path still imports it — confirmed by knip).

## Verification

- Backend: `uv run ruff format` (no diff), `uv run ruff check --fix` (clean), `uv run ty check app/ tests/` (zero errors). `uv run pytest -q` = 2109 passed / 16 skipped / 1 failed.
  - The single failure is `tests/scripts/test_backfill_user_percentiles.py::test_backfill_target_prod_refuses_when_tunnel_down` — a documented pre-existing environment failure (the test asserts the prod tunnel on localhost:15432 is DOWN; the user's local prod tunnel is open). It touches `backfill_user_percentiles.py`, untouched by this plan, and is out of scope per the executor scope boundary. STATE.md records the same artifact across recent quick tasks.
- Frontend: `npm run lint` (eslint clean), `npm run knip` (clean — confirms `pickDominantTcAnchor` + 4 props fully removed with no orphans), `npm test -- --run` = 720/720 passed, `npx tsc -b` clean.
- New backend test `test_per_tc_breakdown_carries_anchor` asserts the seeded TC's breakdown entry carries `anchor == 1525`.
- New frontend tests assert: two-line anchor row + `data-testid` for an above-floor entry, single "insufficient games" line (no anchor) for below-floor, stats-line-only for a renderable entry with `anchor: null`, and absence of "blending"/"Anchored at"/"converted" prose for any chip.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] C4 no-flame guard used a deleted prop**
- **Found during:** Task 2 (frontend test rewrite).
- **Issue:** The plan said keep the C4 no-flame regression guard "verbatim", but the existing C4 popover test passed `nLichessGames: 300` (and `anchorRating`) — props the plan deliberately removes. Keeping it verbatim would break compilation.
- **Fix:** Removed the deleted prop from the `renderChip` call in C4. The test's purpose (no flame icon at any percentile/flavor) is unchanged.
- **Files modified:** `frontend/src/components/charts/__tests__/PercentileChip.test.tsx`
- **Commit:** `29d7c237`

**2. [Rule 3 - Blocking] Two affected component test suites passed `ratingAnchors` + stale fixtures**
- **Found during:** Task 2.
- **Issue:** `EndgameMetricCard.test.tsx` and `EndgameOverallPerformanceSection.test.tsx` imported `RatingAnchorsByTc`, defined a `DEFAULT_RATING_ANCHORS` fixture (using out-of-date `RatingAnchorOut` fields), and passed `ratingAnchors=` to the now-prop-less components. One `EndgameMetricCard` test also asserted the chip does NOT render when `ratingAnchors` is omitted — directly contradicting the new gate-drop behavior.
- **Fix:** Removed the imports/fixtures and `ratingAnchors` props; rewrote the contradicting test to assert the chip renders on a non-null percentile alone (no anchor prop). Renamed three test titles that said "+ anchors non-null".
- **Files modified:** the two test files above.
- **Commit:** `29d7c237`

### Notes

- The new sync backend test inherits the module-level `pytestmark = pytest.mark.asyncio`, producing a benign "marked asyncio but not async" warning. This matches existing sync tests in the codebase (e.g. `test_backfill_target_prod_refuses_when_tunnel_down`, `test_gather_outside_session`) and does not fail any gate. Left as-is for consistency with project convention.
- `npx prettier` was run exploratorily and flagged the touched frontend files, but the project does NOT use prettier (no dep, no config; formatting is enforced by eslint, which passed). The prettier signal was disregarded.

## Known Stubs

None. The anchor field is wired end to end (backend fetch → schema → frontend type → tooltip render). Displayed anchors may be stale until the separate 260529-js1 anchor-recompute human step runs — that follow-up is explicitly NOT in scope for this plan and completion is not gated on it.

## Self-Check: PASSED
