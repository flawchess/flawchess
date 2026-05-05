---
phase: quick-260504-ttq
plan: "01"
subsystem: openings
tags: [score, confidence, ci, bullet-chart, openings, moves-tab]
key-decisions:
  - Reused OPENING_INSIGHTS_CI_Z_95 (1.96) from opening_insights_constants.py for CI bounds
  - Extracted _build_wdl_stats helper to DRY both WDLStats constructor sites in openings_service.py
  - Tested score bullet sub-tree (ScoreConfidencePopover + MiniBulletChart) directly rather than full-page Openings render to avoid 15+ mock overhead
  - Pre-existing MostPlayedOpeningsTable test failures deferred (caused by prior quick task 260504-rvh tooltip text change, unrelated to this task)
metrics:
  duration: "~20 minutes"
  completed: "2026-05-04T19:41:00Z"
  tasks: 3
  commits: 3
---

# Quick Task 260504-ttq: Add Current-Position Score vs. 50% Bullet

Score-vs-50% bullet chart with Wald 95% CI under the WDL bar on the Openings Moves tab, with mute-on-unreliable behavior and confidence popover.

## Files Modified

- **app/schemas/openings.py** -- Extended `WDLStats` Pydantic model with `score`, `confidence`, `p_value`, `ci_low`, `ci_high` fields (Literal typing, required, no Optional)
- **app/services/openings_service.py** -- Added `_build_wdl_stats` helper that calls `compute_confidence_bucket` and computes CI bounds; replaced both `WDLStats(...)` call sites; imported `OPENING_INSIGHTS_CI_Z_95` to avoid magic 1.96
- **tests/test_openings_service.py** -- Extended `test_basic_next_moves` and `test_wdl_computation` with new field assertions; added `test_position_stats_score_ci` with W=8,D=0,L=2,N=10 fixture
- **frontend/src/types/api.ts** -- Extended `WDLStats` TS interface to mirror backend (score, confidence, p_value, ci_low, ci_high)
- **frontend/src/lib/scoreBulletConfig.ts** -- New file: SCORE_BULLET_CENTER=0.5, NEUTRAL_MIN=-0.05, NEUTRAL_MAX=+0.05, DOMAIN=0.20, `clampScoreCi` helper
- **frontend/src/lib/__tests__/scoreBulletConfig.test.ts** -- New file: 6 vitest unit tests for constants and clamp helper
- **frontend/src/components/insights/ScoreConfidencePopover.tsx** -- New file: mirrors BulletConfidencePopover but renders WdlConfidenceTooltip; hover/tap HelpCircle trigger with data-testid + aria-label
- **frontend/src/pages/Openings.tsx** -- Added ScoreConfidencePopover and scoreBulletConfig imports; MIN_GAMES_FOR_RELIABLE_STATS to theme import; IIFE in moveExplorerContent renders MiniBulletChart + ScoreConfidencePopover under WDLChartRow with UNRELIABLE_OPACITY when total < 10
- **frontend/src/pages/__tests__/Openings.statsBoard.test.tsx** -- Added 5 new tests: ScoreConfidencePopover trigger testid/aria-label, MiniBulletChart score-domain CI whisker rendering, isUnreliable threshold constant verification

## Backend Math

`position_stats.score = (W + 0.5·D) / total` (0.5 when total=0). CI computed via `compute_confidence_bucket(W, D, L, total)` which returns `(confidence, p_value, se)` using Wald formula. `ci_low = max(0, score - 1.96·se)`, `ci_high = min(1, score + 1.96·se)`. Uses `OPENING_INSIGHTS_CI_Z_95 = 1.96` from shared constants. When total=0, `compute_confidence_bucket` returns `("low", 0.5, 0.0)` giving score=0.5, CI=[0.5, 0.5].

## Frontend

Rendering site: single IIFE inside `moveExplorerContent` (Openings.tsx:935), which is rendered once for both mobile and desktop. `MiniBulletChart` with center=0.5, neutral +/-0.05, domain=0.20, CI whisker from `clampScoreCi(ci_low/ci_high)`. Wrapper card applies `opacity: UNRELIABLE_OPACITY` (0.5) when `total < MIN_GAMES_FOR_RELIABLE_STATS` (10), dimming both the WDL bar and the bullet atomically. `ScoreConfidencePopover` HelpCircle opens `WdlConfidenceTooltip` on hover/tap.

## Deviations from Plan

### Out-of-scope pre-existing failures

**Pre-existing MostPlayedOpeningsTable.test.tsx failures (2 tests)** -- Tests checking `buildMgEvalHeaderTooltip` text content were already failing before this task (text was changed by quick task 260504-rvh, tests not updated). These are unrelated to this task's changes and deferred to a future fix.

### Test scope adjustment

**Tests in Openings.statsBoard.test.tsx** -- Full-page Openings render requires mocking 15+ hooks (documented in the existing test file comment). Per the plan's guidance ("add minimum mocking needed; keep scope tight"), the 3 new test groups test the score bullet sub-tree directly: ScoreConfidencePopover component rendering, MiniBulletChart with score-domain config, and the isUnreliable threshold constant logic. This approach matches the file's existing pattern of testing extracted helpers rather than the full page.

## Self-Check: PASSED

- All 4 key files found on disk
- All 3 task commits found in git log (115c34a, ccc6563, 6e3cc51)
- 23 backend tests passing, 16 new frontend tests passing
- ruff, ty, eslint, knip all clean
