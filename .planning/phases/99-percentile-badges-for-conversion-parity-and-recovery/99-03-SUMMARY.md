---
phase: 99-percentile-badges-for-conversion-parity-and-recovery
plan: "03"
subsystem: backend
tags:
  - percentile
  - endgame
  - dispatch
  - schema
  - wave-2a

dependency_graph:
  requires:
    - phase: 99-02
      provides: per_user_cte_conv_rate_tc, per_user_cte_parity_rate_tc, per_user_cte_recovery_rate_tc builders + ENUM widening
  provides:
    - app/services/user_benchmark_percentiles_service.py (STAGE_B_METRIC_FAMILIES extended to 10-tuple; dispatch arms for 3 rate families)
    - scripts/gen_global_percentile_cdf.py (IN_SCOPE_METRICS extended to 11; regen dispatch arms + _METRIC_DISPLAY entries for 3 rate families)
    - app/schemas/endgames.py (rate_percentile, rate_percentile_n_games, rate_percentile_value fields on PerTcBucketStats)
    - app/services/endgame_service.py (_build_per_tc_bucket_stats rate_percentile_row param; conv_rate_row/parity_rate_row/recov_rate_row lookups)
    - tests/scripts/fixtures/global_percentile_cdf/ (12 new golden fixtures for 3 rate metrics × 4 TCs)
  affects:
    - Plan 04 (frontend chip wiring — consumes rate_percentile from PerTcBucketStats)
    - Plan 05 (CDF regen + backfill — IN_SCOPE_METRICS now includes rate families; regen dispatch is ready)

tech-stack:
  added: []
  patterns:
    - "SC-2 drift-proof: same per_user_cte_*_rate_tc builders dispatched in both user_benchmark_percentiles_service (per-user) and gen_global_percentile_cdf (cohort regen)"
    - "D-01 coexistence: rate_percentile fields named distinctly from percentile* so both chip signals coexist on the same PerTcBucketStats block"
    - "Rule 1 pattern: stale Wave-0 ty:ignore annotations removed after symbols exist; golden fixtures and test count guards updated after STAGE_B_METRIC_FAMILIES widening"

key-files:
  created:
    - tests/scripts/fixtures/global_percentile_cdf/conversion_rate__bullet.sql
    - tests/scripts/fixtures/global_percentile_cdf/conversion_rate__blitz.sql
    - tests/scripts/fixtures/global_percentile_cdf/conversion_rate__rapid.sql
    - tests/scripts/fixtures/global_percentile_cdf/conversion_rate__classical.sql
    - tests/scripts/fixtures/global_percentile_cdf/parity_rate__bullet.sql
    - tests/scripts/fixtures/global_percentile_cdf/parity_rate__blitz.sql
    - tests/scripts/fixtures/global_percentile_cdf/parity_rate__rapid.sql
    - tests/scripts/fixtures/global_percentile_cdf/parity_rate__classical.sql
    - tests/scripts/fixtures/global_percentile_cdf/recovery_rate__bullet.sql
    - tests/scripts/fixtures/global_percentile_cdf/recovery_rate__blitz.sql
    - tests/scripts/fixtures/global_percentile_cdf/recovery_rate__rapid.sql
    - tests/scripts/fixtures/global_percentile_cdf/recovery_rate__classical.sql
  modified:
    - app/services/user_benchmark_percentiles_service.py
    - scripts/gen_global_percentile_cdf.py
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/services/test_endgame_service.py
    - tests/services/test_user_benchmark_percentiles_service.py

key-decisions:
  - "rate_percentile field trio named distinctly from percentile* — D-01 both coexist; no field name collision"
  - "rate_percentile_row added as 5th parameter with default None to _build_per_tc_bucket_stats — preserves backward compat with all existing tests"
  - "Regen run deferred to Plan 05 — this plan only wires dispatch so the script is syntactically correct; Plan 05 runs the actual benchmark regen"
  - "IN_SCOPE_METRICS extended to 11 values (not regenerated) — _METRIC_DISPLAY also extended to cover all 11 so regen report won't KeyError"

requirements-completed: []

duration: ~15min
completed: "2026-05-30"
---

# Phase 99 Plan 03: Stage B + Regen Dispatch + Schema Field Trio Summary

**Wave 2A backend wiring: both compute paths (per-user Stage B + cohort-CDF regen) route the 3 rate families to the shared Plan-02 builders; PerTcBucketStats carries the distinct rate_percentile trio; endgame_service threads the rate rows onto per-TC blocks.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-30T21:05:00Z
- **Completed:** 2026-05-30T21:18:14Z
- **Tasks:** 2
- **Files modified:** 6 (+ 12 created)

## Accomplishments

- Extended `STAGE_B_METRIC_FAMILIES` from 7 to 10 families: appended `conversion_rate`, `parity_rate`, `recovery_rate` — auto-propagates to `backfill_user_percentiles._ALL_METRICS` (Pitfall 7 compliance, no backfill edit needed)
- Added 3 dispatch arms in `_per_user_cte_for_family_and_tc` routing to the Plan-02 builders with `source="single_user"`
- Extended `IN_SCOPE_METRICS` from 8 to 11 families in `gen_global_percentile_cdf.py`; added 3 dispatch arms to `_per_user_cte_for_metric_and_tc` with `source="benchmark"`; added 3 entries to `_METRIC_DISPLAY` for the regen report
- Added `rate_percentile`, `rate_percentile_n_games`, `rate_percentile_value` fields to `PerTcBucketStats` (Phase 99, all optional/None — backward compat). Fields are named distinctly from `percentile*` (D-01: gap chip and rate chip coexist)
- Added `rate_percentile_row: PercentileRow | None = None` as 5th parameter to `_build_per_tc_bucket_stats`; added `conv_rate_row`, `parity_rate_row`, `recov_rate_row` lookups in `_compute_per_tc_metric_cards` via the same `_effective_rows.get("conversion_rate", {}).get(tc_bucket)` path as gap rows
- All 2191 tests passing; ty clean; ruff clean

## Task Commits

1. **Task 1: Stage B + regen dispatch arms for 3 rate families** - `78d3d956` (feat)
2. **Task 2: PerTcBucketStats rate field trio + endgame_service threading** - `7f123cc7` (feat)
3. **Rule 1 auto-fixes: golden fixtures + test guards** - `c8614a35` (fix)

## Files Created/Modified

- `app/services/user_benchmark_percentiles_service.py` — imports + STAGE_B_METRIC_FAMILIES extended to 10; 3 dispatch arms added to `_per_user_cte_for_family_and_tc`
- `scripts/gen_global_percentile_cdf.py` — imports + IN_SCOPE_METRICS extended to 11; 3 dispatch arms added to `_per_user_cte_for_metric_and_tc`; 3 `_METRIC_DISPLAY` entries added
- `app/schemas/endgames.py` — `rate_percentile`, `rate_percentile_n_games`, `rate_percentile_value` fields on `PerTcBucketStats`; docstring extended
- `app/services/endgame_service.py` — `_build_per_tc_bucket_stats` signature + return widened; 3 rate-row lookups in `_compute_per_tc_metric_cards`
- `tests/services/test_endgame_service.py` — stale Wave-0 `ty: ignore` annotations removed (Rule 1); block comment updated from RED to GREEN
- `tests/services/test_user_benchmark_percentiles_service.py` — `test_stage_b_metric_families_is_7_tuple` → `is_10_tuple`; T6 count updated 14 → 20 (Rule 1)
- `tests/scripts/fixtures/global_percentile_cdf/` — 12 new SQL golden fixtures: `{conversion_rate,parity_rate,recovery_rate}__{bullet,blitz,rapid,classical}.sql` (Rule 1)

## Key Contract Values (for downstream plans)

**PerTcBucketStats final rate fields:**
```python
rate_percentile: float | None = None
rate_percentile_n_games: int | None = None
rate_percentile_value: float | None = None
```

**endgame_service lookup pattern:**
```python
conv_rate_row = _effective_rows.get("conversion_rate", {}).get(tc_bucket)
parity_rate_row = _effective_rows.get("parity_rate", {}).get(tc_bucket)
recov_rate_row = _effective_rows.get("recovery_rate", {}).get(tc_bucket)
```

**Regen deferred:** `gen_global_percentile_cdf.py` now has correct dispatch for all 11 families; the actual `--target benchmark` regen run is Plan 05's responsibility. Until then, the 3 rate families return `None` for all per-TC blocks (no cohort CDF rows in `user_benchmark_percentiles` yet).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Golden fixture canary test failed after IN_SCOPE_METRICS widening**
- **Found during:** Full pytest run after Task 1
- **Issue:** `test_gen_global_percentile_cdf_unchanged.py` parametrizes over `IN_SCOPE_METRICS × ALL_TIME_CONTROLS`. After adding 3 new families, it required 12 new SQL golden fixtures that did not exist yet — `FileNotFoundError` on all 12 new cells.
- **Fix:** Ran the fixture regen snippet from the test module docstring for the 3 new metric families only (existing goldens unchanged). Generated 12 `{metric}__{tc}.sql` files.
- **Files modified:** 12 new files under `tests/scripts/fixtures/global_percentile_cdf/`
- **Commit:** `c8614a35`

**2. [Rule 1 - Bug] `test_stage_b_metric_families_is_7_tuple` failed after STAGE_B_METRIC_FAMILIES widening**
- **Found during:** Full pytest run after Task 1
- **Issue:** The test asserted `len == 7` and exact tuple equality. After widening to 10, both assertions failed.
- **Fix:** Renamed test to `is_10_tuple`, updated `len == 10`, added 3 new rate family names to the tuple assertion. Updated T6 docstring comment and `== 14` count to `== 20` (10 × 2 anchored TCs).
- **Files modified:** `tests/services/test_user_benchmark_percentiles_service.py`
- **Commit:** `c8614a35`

**3. [Rule 1 - Bug] Stale Wave-0 ty:ignore annotations in test_endgame_service.py**
- **Found during:** Task 2 `ty check`
- **Issue:** Wave-0 added `# ty: ignore[unresolved-attribute]` and `# ty: ignore[unknown-argument]` on `rate_percentile*` accesses. Once the fields exist (Plan 03), ty reports `warning[unused-ignore-comment]` on each one.
- **Fix:** Removed all 7 stale suppression comments; updated block comment from "INTENDED RED" to GREEN.
- **Files modified:** `tests/services/test_endgame_service.py`
- **Commit:** `7f123cc7`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — test guards and wave-0 cleanup that blocked CI or ty compliance)

## Self-Check

**Files verified:**
- `app/services/user_benchmark_percentiles_service.py` — contains `per_user_cte_conv_rate_tc` (import + dispatch arm), `STAGE_B_METRIC_FAMILIES` has 10 members
- `scripts/gen_global_percentile_cdf.py` — `IN_SCOPE_METRICS` verified via `python -c "from scripts.gen_global_percentile_cdf import IN_SCOPE_METRICS; assert {'conversion_rate','parity_rate','recovery_rate'} <= set(IN_SCOPE_METRICS)"`
- `app/schemas/endgames.py` — `grep -c "rate_percentile"` = 7
- `app/services/endgame_service.py` — `grep -c '_effective_rows.get("conversion_rate"...'` = 3

**Commits verified:**
- `78d3d956` — Task 1 commit
- `7f123cc7` — Task 2 commit
- `c8614a35` — Rule 1 auto-fixes commit

**Test suite:** 2191 passed, 16 skipped (pre-existing integration skips), 3 warnings (pre-existing)

**ty check:** `uv run ty check app/ tests/` → All checks passed!

**regen deferred:** Plan 05 runs `gen_global_percentile_cdf.py --target benchmark`; this plan only wires the dispatch.

## Self-Check: PASSED

---
*Phase: 99-percentile-badges-for-conversion-parity-and-recovery*
*Completed: 2026-05-30*
