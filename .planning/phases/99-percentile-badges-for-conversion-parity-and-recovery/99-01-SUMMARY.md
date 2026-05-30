---
phase: 99-percentile-badges-for-conversion-parity-and-recovery
plan: "01"
subsystem: testing
tags:
  - wave-0
  - tdd
  - percentile
  - endgame
dependency_graph:
  requires: []
  provides:
    - tests/services/test_canonical_slice_sql.py (rate builder tests — RED until Plan 02)
    - tests/models/test_user_benchmark_percentile.py (ENUM membership tests — RED until Plan 02)
    - tests/services/test_endgame_service.py (rate_percentile field tests — RED until Plan 03)
    - frontend/src/components/charts/EndgameMetricsByTcCard.test.tsx (chip behavior tests — render RED until Plan 04)
  affects:
    - Plans 02-05 (each plan turns specific tests green)
tech_stack:
  added: []
  patterns:
    - Deferred imports inside test methods for Wave-1 symbols (prevents collection failure during RED state)
    - ty: ignore[unresolved-import/attribute/unknown-argument] suppression for non-existent symbols
key_files:
  created:
    - tests/models/test_user_benchmark_percentile.py
    - frontend/src/components/charts/EndgameMetricsByTcCard.test.tsx
  modified:
    - tests/services/test_canonical_slice_sql.py
    - tests/services/test_endgame_service.py
decisions:
  - "Deferred imports (inside method body, not module level) allow pytest to collect the full existing test module while Wave-1 symbols are absent"
  - "ty: ignore suppressions used on each import line individually (not the from...import( line) — ty reports errors at member lines, not the from line"
metrics:
  duration: "~20 minutes"
  completed_date: "2026-05-30"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 99 Plan 01: Wave 0 Test Scaffolds Summary

Wave 0 test scaffolding for Phase 99 percentile badges. All four test surfaces named in 99-VALIDATION.md are created or extended so every Phase 99 Success Criterion has an automated home before implementation lands.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Backend rate-builder + ENUM + schema test scaffolds | 4d35d454 | Done |
| 2 | Frontend rate-chip test scaffold | 4d35d454 | Done |

## Intentionally RED Tests (Wave 0 State)

The following tests are expected to fail until the named Wave lands.

### RED until Plan 02 (rate builders + ENUM widening)

| Test | Why RED |
|------|---------|
| `TestConvRateTcBuilder::test_per_user_cte_conv_rate_tc_floor` | `per_user_cte_conv_rate_tc` and `MINIMUM_RATE_BUCKET_SPANS` not yet exported |
| `TestConvRateTcBuilder::test_per_user_cte_conv_rate_tc_source_parity` | same |
| `TestConvRateTcBuilder::test_per_user_cte_conv_rate_tc_metric_value_formula` | same |
| `TestParityRateTcBuilder::test_per_user_cte_parity_rate_tc_floor` | `per_user_cte_parity_rate_tc` not yet exported |
| `TestParityRateTcBuilder::test_per_user_cte_parity_rate_tc_source_parity` | same |
| `TestParityRateTcBuilder::test_per_user_cte_parity_rate_tc_metric_value_formula` | same |
| `TestRecoveryRateTcBuilder::test_per_user_cte_recovery_rate_tc_floor` | `per_user_cte_recovery_rate_tc` not yet exported |
| `TestRecoveryRateTcBuilder::test_per_user_cte_recovery_rate_tc_source_parity` | same |
| `TestRecoveryRateTcBuilder::test_per_user_cte_recovery_rate_tc_metric_value_formula` | same |
| `test_rate_enum_member_present[conversion_rate_{bullet,blitz,rapid,classical}]` | 12 ENUM members absent from `benchmark_metric_enum` |
| `test_rate_enum_member_present[parity_rate_{bullet,blitz,rapid,classical}]` | same |
| `test_rate_enum_member_present[recovery_rate_{bullet,blitz,rapid,classical}]` | same |

### RED until Plan 03 (PerTcBucketStats field widening)

| Test | Why RED |
|------|---------|
| `TestPerTcBucketStatsRatePercentileFields::test_rate_percentile_defaults_none` | `rate_percentile` field absent from Pydantic model |
| `TestPerTcBucketStatsRatePercentileFields::test_rate_percentile_n_games_defaults_none` | same |
| `TestPerTcBucketStatsRatePercentileFields::test_rate_percentile_value_defaults_none` | same |
| `TestPerTcBucketStatsRatePercentileFields::test_rate_percentile_distinct_from_gap_percentile` | same |

### RED until Plan 04 (EndgameMetricsByTcCard chip wiring)

| Test | Why RED |
|------|---------|
| `EndgameMetricsByTcCard — rate chip RENDER` (1 test) | Rate chip not yet wired in `MetricBlock` |
| `EndgameMetricsByTcCard — rate chip TC-SCOPED tooltip` (3 tests) | same |
| `EndgameMetricsByTcCard — COEXISTENCE of gap chip and rate chip` (1 test) | same |

### Already GREEN

| Test | Status |
|------|--------|
| `EndgameMetricsByTcCard — rate chip SUPPRESS when rate_percentile null` | GREEN — null check naturally prevents chip render |
| `EndgameMetricsByTcCard — rate chip SUPPRESS when anchorRating absent` | GREEN — undefined anchor check naturally prevents chip render |

## Deviations from Plan

**1. [Rule 1 - Bug] Module-level imports cause collection failure**
- **Found during:** Task 1 implementation
- **Issue:** The plan specified importing Wave-1 symbols from `canonical_slice_sql`. A module-level import of non-existent symbols causes pytest to fail collection of the entire 1040-line test file, not just the new tests.
- **Fix:** Used deferred imports (inside each test method body) instead of module-level imports. Each test individually imports the symbols it needs; the collection failure is scoped to that one test, not the entire module.
- **Files modified:** `tests/services/test_canonical_slice_sql.py`
- **Commit:** 4d35d454

**2. [Rule 2 - Compliance] ty: ignore comments required for Wave-1 symbols**
- **Found during:** Task 1 implementation
- **Issue:** `uv run ty check` reports errors on imports of non-existent symbols and attribute access on non-existent fields (CLAUDE.md requires zero ty errors).
- **Fix:** Added `# ty: ignore[unresolved-import]` on each deferred import line and `# ty: ignore[unresolved-attribute]` / `# ty: ignore[unknown-argument]` on each attribute access / constructor call. The ignore rule name must match ty's actual error code (`unknown-argument`, not `call-arg`).
- **Files modified:** `tests/services/test_canonical_slice_sql.py`, `tests/services/test_endgame_service.py`
- **Commit:** 4d35d454

## Verification Results

```
uv run pytest tests/services/test_canonical_slice_sql.py tests/models/test_user_benchmark_percentile.py tests/services/test_endgame_service.py --collect-only -q
→ 295 tests collected in 0.03s (no collection errors)

grep -c "source_parity" tests/services/test_canonical_slice_sql.py
→ 3

cd frontend && npx tsc --noEmit
→ (clean, no output)

cd frontend && npx vitest run EndgameMetricsByTcCard --reporter=dot
→ 5 failed (intended RED) | 20 passed
```

## Self-Check: PASSED

All files created/verified:
- `tests/models/test_user_benchmark_percentile.py` — exists, contains "conversion_rate_bullet"
- `frontend/src/components/charts/EndgameMetricsByTcCard.test.tsx` — exists, contains "rate_percentile" (18 occurrences) and "rate-percentile-chip" (13 occurrences)
- `tests/services/test_canonical_slice_sql.py` — extended, 3 source_parity tests present
- `tests/services/test_endgame_service.py` — extended, TestPerTcBucketStatsRatePercentileFields class present

Commit 4d35d454 verified in git log.
