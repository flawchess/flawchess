---
phase: 63-findings-pipeline-zone-wiring
plan: 01
subsystem: backend/registry
tags: [python, pydantic, literal-types, dataclass, zones, thresholds, endgame, tdd]

# Dependency graph
requires: []
provides:
  - "app/services/endgame_zones.py — Python source of truth for endgame gauge thresholds (D-01, FIND-02)"
  - "ZONE_REGISTRY: Mapping[MetricId, ZoneSpec] with 5 scalar metrics"
  - "BUCKETED_ZONE_REGISTRY: Mapping[BucketedMetricId, Mapping[MaterialBucket, ZoneSpec]] with D-10 recovery band [0.25, 0.35]"
  - "SAMPLE_QUALITY_BANDS: Mapping[SubsectionId, tuple[int, int]] for 10 subsections"
  - "Literal type aliases: Zone, Trend, SampleQuality, Window, MetricId, SubsectionId, BucketedMetricId"
  - "Named threshold constants: TREND_MIN_WEEKLY_POINTS, TREND_MIN_SLOPE_VOL_RATIO, NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD, NEUTRAL_PCT_THRESHOLD, NEUTRAL_TIMEOUT_THRESHOLD"
  - "assign_zone / assign_bucketed_zone / sample_quality helpers with NaN guard"
  - "22 unit tests in tests/services/test_endgame_zones.py"
  - "Recovery gauge re-centered to [0.25, 0.35] in frontend EndgameScoreGapSection.tsx (D-10)"
affects:
  - "63-02 (codegen + consistency): will import ZONE_REGISTRY, BUCKETED_ZONE_REGISTRY, threshold constants and emit frontend/src/generated/endgameZones.ts"
  - "63-03 (schemas): will re-import Zone/Trend/SampleQuality/Window/MetricId/SubsectionId Literal aliases"
  - "63-04, 63-05 (service): will call assign_zone / assign_bucketed_zone / sample_quality"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen dataclass as boundary value object (@dataclass(frozen=True))"
    - "Mapping[K, V] over dict[K, V] for module-level registry exports (covariant + read-only signal)"
    - "Literal type alias at module top, then constants, then dataclass, then registry, then helpers — order used by Plans 02-05"

key-files:
  created:
    - "app/services/endgame_zones.py (271 lines)"
    - "tests/services/__init__.py (7 lines — subpackage marker)"
    - "tests/services/test_endgame_zones.py (149 lines, 22 tests)"
  modified:
    - "frontend/src/components/charts/EndgameScoreGapSection.tsx (3 +/3 - — FIXED_GAUGE_ZONES.recovery only)"

key-decisions:
  - "D-06 honored verbatim: net_timeout_rate direction is lower_is_better with an inline comment explaining that if future review determines the formula produces positive-when-good values, the findings service (Plan 04) flips the sign before calling assign_zone rather than changing the registry."
  - "D-10 applied simultaneously in Python registry and TSX source so Plan 02 consistency test stays green from day one."
  - "Introduced BucketedMetricId Literal alias (tighter type than the raw Literal[...] in the registry signature) so call sites get a named type to document intent."
  - "NaN guard returns \"typical\" (not raising, not \"weak\"). Empty-window findings distinguish missing data via is_headline_eligible=False per D-13; this decouples the zone contract from the missing-data contract."

patterns-established:
  - "Every threshold is a named constant — registry entries reference NEUTRAL_TIMEOUT_THRESHOLD for net_timeout_rate bounds and NEUTRAL_PCT_THRESHOLD for avg_clock_diff_pct bounds (no duplicated literals)."
  - "Docstring-above-constant pattern from app/services/openings_service.py carried into the new module."
  - "Module-scope fixture isolation pattern: tests/services/__init__.py marks the subpackage, avoiding module-scope fixture state leakage across sibling service test files."

requirements-completed:
  - FIND-02

# Metrics
duration: 4min
completed: 2026-04-20
---

# Phase 63 Plan 01: Zone Registry + Recovery Band Re-center Summary

**Python authoritative zone registry with frozen ZoneSpec dataclass, 22 unit tests, and D-10 Recovery band [0.25, 0.35] applied simultaneously in Python source and FE gauge.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-20T18:40:07Z
- **Completed:** 2026-04-20T18:43:10Z
- **Tasks:** 3
- **Files created:** 3 (app/services/endgame_zones.py, tests/services/__init__.py, tests/services/test_endgame_zones.py)
- **Files modified:** 1 (frontend/src/components/charts/EndgameScoreGapSection.tsx)

## Accomplishments

- `app/services/endgame_zones.py` exports the full surface listed in RESEARCH.md: Zone / Trend / SampleQuality / Window / MetricId / SubsectionId / BucketedMetricId Literals, ZoneSpec frozen dataclass, ZONE_REGISTRY (5 scalar metrics), BUCKETED_ZONE_REGISTRY (3 bucketed metrics × 3 MaterialBuckets), SAMPLE_QUALITY_BANDS (10 subsections), five named thresholds (TREND_MIN_WEEKLY_POINTS, TREND_MIN_SLOPE_VOL_RATIO, NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD, NEUTRAL_PCT_THRESHOLD, NEUTRAL_TIMEOUT_THRESHOLD), and three helpers (`assign_zone`, `assign_bucketed_zone`, `sample_quality`).
- D-10 Recovery band re-center [0.25, 0.35] applied atomically to Python registry and `frontend/src/components/charts/EndgameScoreGapSection.tsx` `FIXED_GAUGE_ZONES.recovery` — both sides agree so the forthcoming Plan 02 consistency test is green by construction.
- 22 unit tests (above the 15+ target) cover higher_is_better / lower_is_better direction handling, typical-band boundary semantics (typical_lower inclusive on the typical side, typical_upper inclusive on the strong side), centered-band score_gap handling, NaN guard, the D-10 recovery band proof, per-bucket consistency across all three MaterialBuckets, sample quality band lookups including the D-16 smaller-per-type rationale, and registry sanity (all five scalar metrics covered, net_timeout_rate references NEUTRAL_TIMEOUT_THRESHOLD). All tests synchronous, no DB fixtures needed.
- `uv run ty check app/ tests/`, `uv run ruff check .`, and `npx tsc --noEmit` (in frontend/) all exit 0. No ty regressions project-wide.

## Task Commits

1. **Task 1: Create endgame_zones.py registry module** — `de735ea` (feat)
2. **Task 2: Recovery band re-center in EndgameScoreGapSection.tsx (D-10)** — `c6da043` (feat)
3. **Task 3: Unit tests for assign_zone and assign_bucketed_zone** — `a32e895` (test)

## Files Created/Modified

- `app/services/endgame_zones.py` — new module, 271 lines. Python source of truth for endgame gauge thresholds; all constants named, NaN-safe helpers, frozen ZoneSpec dataclass, separate scalar and bucketed registries.
- `tests/services/__init__.py` — new file, 7 lines. Subpackage marker so module-scope fixtures (seeded_user in Phase 61) stay isolated across sibling service tests.
- `tests/services/test_endgame_zones.py` — new file, 149 lines. 22 tests across 4 classes (TestAssignZone, TestAssignBucketedZone, TestSampleQuality, TestRegistrySanity).
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — 6 numeric changes in `FIXED_GAUGE_ZONES.recovery`: neutral band moved from [0.30, 0.40] to [0.25, 0.35], with the adjacent danger-upper (0.30→0.25) and success-lower (0.40→0.35) boundaries following. Conversion and parity blocks unchanged per D-11. `ENDGAME_SKILL_ZONES` unchanged.

## Decisions Made

- **A1 (RESEARCH.md open question — net_timeout_rate direction):** Resolved per plan instructions by honoring CONTEXT.md D-06 `lower_is_better` verbatim. The registry entry carries an inline comment stating that if Phase 63 review ever determines the formula produces positive-when-good values, the findings service (Plan 04) should flip the sign before calling `assign_zone` rather than mutate the registry entry. This keeps the registry aligned with the locked CONTEXT.md decision and centralizes any future adjustment at the call site.
- **NaN guard semantics:** Returns `"typical"` for both scalar and bucketed metrics. The is_headline_eligible=False signal on the emitted SubsectionFinding (Plan 03) is what distinguishes missing data from typical data — the zone contract stays pure.
- **Introduced `BucketedMetricId = Literal["conversion_win_pct", "parity_score_pct", "recovery_save_pct"]`** as a named alias. Plan 1 Task 1 action specced an inline `Literal[...]` on `assign_bucketed_zone`; promoting it to a module-level alias tightens the registry type (`Mapping[BucketedMetricId, Mapping[MaterialBucket, ZoneSpec]]`) and documents intent at call sites.

## Deviations from Plan

None — plan executed exactly as written.

The `BucketedMetricId` named alias promotion is a minor documentation refinement within the planned action (the plan itself used inline Literal[...] in two places; promoting it to a single module-level name avoids duplication). No behaviour difference.

## Issues Encountered

None. TDD task ordering: Task 1 (module) ran before Task 3 (tests) intentionally — the plan specifies Task 3 creates test file after module exists, which matches the RED-then-GREEN pattern collapsed into a single "GREEN first, test second" ordering since the module is a pure constants/helpers file where the tests are documentation of the contract rather than a driving design tool. All 22 tests pass on first run; no iteration needed.

## User Setup Required

None — no external service configuration required. Phase 63 is backend-only Python + one numeric edit to a TSX file.

## Next Phase Readiness

Plan 02 (codegen + FE-drift consistency test) can start immediately:
- `ZONE_REGISTRY`, `BUCKETED_ZONE_REGISTRY`, `SAMPLE_QUALITY_BANDS`, and the five named thresholds are importable from `app.services.endgame_zones`.
- Frontend source-of-truth values (FIXED_GAUGE_ZONES in EndgameScoreGapSection.tsx, NEUTRAL_PCT_THRESHOLD / NEUTRAL_TIMEOUT_THRESHOLD in EndgameClockPressureSection.tsx, SCORE_GAP_NEUTRAL_MIN/MAX in EndgamePerformanceSection.tsx) already match the Python registry (D-10 applied to the FE too), so the consistency test will pass on first run.

No blockers or concerns.

## Self-Check

Verifying every claim in this SUMMARY:

- ✅ `app/services/endgame_zones.py` exists (271 lines verified via wc -l)
- ✅ `tests/services/__init__.py` exists (7 lines)
- ✅ `tests/services/test_endgame_zones.py` exists (149 lines)
- ✅ `frontend/src/components/charts/EndgameScoreGapSection.tsx` modified (3 +/3 - via git diff)
- ✅ Commit `de735ea` in git log (Task 1)
- ✅ Commit `c6da043` in git log (Task 2)
- ✅ Commit `a32e895` in git log (Task 3)
- ✅ `uv run pytest tests/services/test_endgame_zones.py -x` → 22 passed in 0.12s
- ✅ `uv run ty check app/ tests/` → All checks passed
- ✅ `uv run ruff check .` → All checks passed
- ✅ `grep -c "from: 0.25, to: 0.35" frontend/.../EndgameScoreGapSection.tsx` → 1
- ✅ Python round-trip: `BUCKETED_ZONE_REGISTRY['recovery_save_pct']['recovery']` has `typical_lower=0.25, typical_upper=0.35`

## Self-Check: PASSED

---
*Phase: 63-findings-pipeline-zone-wiring*
*Completed: 2026-04-20*
