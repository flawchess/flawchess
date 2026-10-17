---
phase: 238-endgame-stats-percentile-first
plan: 06
subsystem: ui
tags: [react, typescript, cleanup, knip, endgames]

requires:
  - phase: 238-04
    provides: insights files already rewritten for the ranked sample (remaining retired-name comments fixed here)
  - phase: 238-05
    provides: new Metrics, Time Pressure and Type sections mounted; old components unmounted but on disk
provides:
  - "Retired endgame component tree deleted (31 files: old Overall/Metrics/Time Pressure/Type sections and cards, EndgameGauge, PercentileChip, MetricStatPopover/Tooltip, AchievableScorePopover, EndgameOverallScoreGapRow, EndgameOverallShared, lib/percentileAnchor.ts, plus their tests)"
  - "Dead exports pruned: BUCKET_DISPLAY_LABELS, ENDGAME_TYPE_DESCRIPTIONS, SHOW_WDL_BAR_IN_TYPE_CARDS (endgameMetrics.ts); DEFAULT_GAUGE_ZONES, colorizeGaugeZones, GAUGE_ZONE_COLORS, GaugeZone, private GAUGE_DANGER/GAUGE_SUCCESS (theme.ts)"
  - "No surviving file under frontend/src, app/ or tests/ names a retired component outside the five files 238-07/238-08 own"
affects: [238-07, 238-08]

plan_head_before: 34c3bd2e8
plan_head_after: 0ab685601
actuals:
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Retirement sweep: importer grep first, one git rm, then knip until clean (second-order orphans surface on the re-run)"

key-files:
  created: []
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/lib/endgameMetrics.ts
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/lib/pressureBulletConfig.ts
    - frontend/src/lib/__tests__/sounds.test.ts
    - frontend/src/components/popovers/FlawBulletPopover.tsx
    - frontend/src/components/bots/PersonaEloDisclosurePopover.tsx
    - frontend/src/components/charts/EndgameEloTimelineSection.tsx
    - app/schemas/insights.py
    - app/services/insights_service.py
    - app/services/insights_llm.py
    - app/services/endgame_zones.py
    - app/services/user_benchmark_percentiles_service.py
    - tests/services/test_endgame_zones.py
  deleted:
    - "31 files in the plan's retirement inventory"

key-decisions:
  - "GAUGE_NEUTRAL survives (PercentileBar dot via rankedMetrics.ts); its stale 'Endgame gauge zone colors' comment was rewritten to describe the typical-middle blue"

requirements-completed: [D-00c, D-00d, D-00h]

duration: ~15min
completed: 2026-10-11
---

# Phase 238 Plan 06: Retire the replaced endgame component tree

**Executed inline from the orchestrating session (plan frontmatter `execution: inline`).**

## Performance

- **Tasks:** 2/2
- **Files:** 31 deleted, 14 modified
- **Execution:** inline (orchestrator), no subagent

## Accomplishments

- The importer check found that every importer of a retired module was itself on the deletion list, so nothing outside the inventory needed patching.
- Deleted all 31 inventory files with one `git rm --ignore-unmatch`. The old time-pressure pair was still on disk, because the 238-05 fallback had not removed it.
- Ran knip three times until it was clean:
  - First run: `BUCKET_DISPLAY_LABELS`, `ENDGAME_TYPE_DESCRIPTIONS`, `SHOW_WDL_BAR_IN_TYPE_CARDS`, `DEFAULT_GAUGE_ZONES` and `colorizeGaugeZones`, all removed.
  - Second run: `GAUGE_ZONE_COLORS` and the `GaugeZone` type, removed together with the now-unused private `GAUGE_DANGER` and `GAUGE_SUCCESS`.
  - Third run: clean. `EndgameOverallShared.ts` was never reported as an unused file because it was already in the deletion set.
- Comment sweep: 18 hits in 13 surviving files were rewritten to name RankedMetricPopover, TypeTable or ScoreGapByTimePressureChart, or to describe the concept. Backend and test edits are docstring and comment text only.

## Task Commits

1. **Task 1: Delete the retired tree, prune dead exports** – `4b1ea61c2` (refactor)
2. **Task 2: Stale-reference comment sweep** – `0ab685601` (docs). T1_SHA = `4b1ea61c2`.

## Verification

- Inventory `find` prints nothing. MiniBulletChart, pressureBulletConfig.ts, ScoreGapByTimePressureChart and EndgameClockDiffOverTimeChart are still present.
- `npm run knip` reports nothing. Lint and build (tsc -b) exit 0. The full vitest run passed 318 files and 5331 tests after Task 1.
- The stale-reference grep prints nothing outside `frontend/src/types/endgames.ts`, `app/schemas/endgames.py`, `app/services/endgame_service.py`, `tests/test_endgame_service.py` and `tests/test_endgames_router.py`, which 238-07 and 238-08 own.
- `git diff 4b1ea61c2 -- app/ tests/ frontend/src/components/charts/EndgameEloTimelineSection.tsx` touches comment and docstring lines only. I read the diff and found no statement, JSX or prompt-string changes. The EndgameEloTimelineSection and sounds tests pass unmodified (2 files, 49 tests).
- `ruff check` and `ruff format --check` on app/ and tests/ are clean.

## Deviations from Plan

None beyond the plan's own allowance:
- knip produced second-order orphans, as the plan anticipated: `GAUGE_ZONE_COLORS`, `GaugeZone`, and the private `GAUGE_DANGER` and `GAUGE_SUCCESS` that tsc would otherwise flag as unused.
- No comment hits turned up in files created by 238-03 or 238-05.

## Issues Encountered

None.

## Known Stubs

None.

## Next Phase Readiness

238-07 and 238-08 own the remaining retired-name references in the overview types and the backend overview path.

## Self-Check: PASSED
