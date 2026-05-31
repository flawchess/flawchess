---
phase: 99-percentile-badges-for-conversion-parity-and-recovery
plan: "02"
subsystem: database
tags:
  - percentile
  - endgame
  - sql-builder
  - alembic
  - enum
  - wave-1

dependency_graph:
  requires:
    - phase: 99-01
      provides: Wave-0 test scaffolds (rate builder tests, ENUM membership tests) — RED until this plan
  provides:
    - app/services/canonical_slice_sql.py (per_user_cte_conv_rate_tc, per_user_cte_parity_rate_tc, per_user_cte_recovery_rate_tc, MINIMUM_RATE_BUCKET_SPANS)
    - app/services/global_percentile_cdf.py (CdfMetricId widened with conversion_rate, parity_rate, recovery_rate)
    - app/models/user_benchmark_percentile.py (benchmark_metric_enum widened with 12 TC-suffixed rate values)
    - alembic/versions/20260530_extend_benchmark_metric_for_rate_percentiles.py (migration 3981239fd391, ADD VALUE × 12)
  affects:
    - Plan 03 (PerTcBucketStats field widening + endgame_service dispatch — imports builders from canonical_slice_sql)
    - Plan 04 (frontend chip wiring — consumes rate_percentile field from Plan 03)
    - Plan 05 (CDF regen + backfill — uses all three builders for cohort construction)

tech-stack:
  added: []
  patterns:
    - "Three-builder pattern: one per_user_cte_*_rate_tc builder per rate family, each using _ = source idiom for drift-proof source parity (SC-2)"
    - "No lead()/spans_with_next in rate builders — outcome measured from game result, not ΔES delta"
    - "MINIMUM_RATE_BUCKET_SPANS named separately from SCORE_GAP_BUCKET_MIN_SPANS — same value, independent tuning"
    - "ADD VALUE IF NOT EXISTS migration loop from fd5b551f381c — forward-only, idempotent, no data rows in same transaction"

key-files:
  created:
    - alembic/versions/20260530_extend_benchmark_metric_for_rate_percentiles.py
  modified:
    - app/services/canonical_slice_sql.py
    - app/services/global_percentile_cdf.py
    - app/models/user_benchmark_percentile.py
    - tests/integration/test_benchmark_metric_enum.py
    - tests/services/test_canonical_slice_sql.py

key-decisions:
  - "Migration revision ID is 3981239fd391, down_revision=c70f5d94b243 — downstream plans reference this"
  - "Recovery builder bucket CASE: mate present and user not winning → recovery (since conversion already handled positive mate); cp <= -100 signed → recovery; else parity"
  - "Stale ty: ignore[unresolved-import] comments removed from Wave-0 tests after symbols exist (Rule 1)"
  - "test_benchmark_metric_enum.py EXPECTED_ENUM_LABELS updated from 8 to 20 values (Rule 1 — the guard was blocking after ENUM widening)"

patterns-established:
  - "Builder signatures: per_user_cte_{family}_rate_tc(tc: TimeControlBucket, *, source: Literal[...], snapshot_date: date | None = None) -> str"
  - "CdfMetricId: 11 family names — score_gap, achievable_score_gap, score_gap_conv, score_gap_parity, recovery_score_gap, time_pressure_score_gap, clock_gap, net_flag_rate, conversion_rate, parity_rate, recovery_rate"
  - "benchmark_metric SAEnum: 20 values (8 family-level + 12 TC-suffixed rate values)"

requirements-completed: []

duration: ~25min
completed: "2026-05-30"
---

# Phase 99 Plan 02: Rate Builders + ENUM Widening + Alembic Migration Summary

**Three per-TC raw-rate SQL builders (conversion/parity/recovery), MINIMUM_RATE_BUCKET_SPANS constant, CdfMetricId + SAEnum widened to 11 families / 20 ENUM values, and Alembic migration 3981239fd391 locking the backend contract layer for Plans 03/04/05.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-30T20:40:00Z
- **Completed:** 2026-05-30T21:04:09Z
- **Tasks:** 2
- **Files modified:** 5 (+ 1 created)

## Accomplishments

- Added `MINIMUM_RATE_BUCKET_SPANS: int = 30` to the constant block (separate from `SCORE_GAP_BUCKET_MIN_SPANS` per CLAUDE.md no-magic-numbers rule, same value but independent tuning)
- Added three rate builders to `canonical_slice_sql.py` — each uses `_ = source` idiom, no `lead()`/`spans_with_next`, HAVING floor ≥ `MINIMUM_RATE_BUCKET_SPANS`, and projects `(user_id, metric_value, n_games)` per Pitfall 1
- Widened `CdfMetricId` Literal with 3 new family names and `benchmark_metric_enum` SAEnum with 12 TC-suffixed values; created migration 3981239fd391 (applied to dev DB — 20 ENUM values confirmed in Postgres)
- All Wave-0 source-parity, floor, and ENUM membership tests are GREEN; ty clean, ruff clean, 532 tests passing

## Task Commits

1. **Task 1: Three rate builders + MINIMUM_RATE_BUCKET_SPANS** - `935d417e` (feat)
2. **Task 2: Widen CdfMetricId + SAEnum + Alembic migration** - `ef360e10` (feat)

## Files Created/Modified

- `app/services/canonical_slice_sql.py` — added `MINIMUM_RATE_BUCKET_SPANS` constant and three builders: `per_user_cte_conv_rate_tc`, `per_user_cte_parity_rate_tc`, `per_user_cte_recovery_rate_tc`
- `app/services/global_percentile_cdf.py` — `CdfMetricId` Literal widened: +`conversion_rate`, `parity_rate`, `recovery_rate` (3 family names, no TC suffixes)
- `app/models/user_benchmark_percentile.py` — `benchmark_metric_enum` SAEnum widened to 20 values; module docstring updated for Phase 99
- `alembic/versions/20260530_extend_benchmark_metric_for_rate_percentiles.py` — migration 3981239fd391 (revision), `down_revision=c70f5d94b243`, ADD VALUE IF NOT EXISTS × 12, no data rows
- `tests/integration/test_benchmark_metric_enum.py` — `EXPECTED_ENUM_LABELS` updated 8 → 20 values (Rule 1 auto-fix)
- `tests/services/test_canonical_slice_sql.py` — stale `ty: ignore[unresolved-import]` Wave-0 annotations removed (Rule 1 auto-fix)

## Key Contract Values (for downstream plans)

**Migration revision ID:** `3981239fd391` (down_revision: `c70f5d94b243`)

**Builder signatures:**
```python
per_user_cte_conv_rate_tc(tc, *, source, snapshot_date=None) -> str  # metric_value = wins/conv_n
per_user_cte_parity_rate_tc(tc, *, source, snapshot_date=None) -> str  # metric_value = (wins+0.5*draws)/parity_n
per_user_cte_recovery_rate_tc(tc, *, source, snapshot_date=None) -> str  # metric_value = (wins+draws)/recov_n
```

**CdfMetricId final list (11 families):**
`score_gap`, `achievable_score_gap`, `score_gap_conv`, `score_gap_parity`, `recovery_score_gap`, `time_pressure_score_gap`, `clock_gap`, `net_flag_rate`, `conversion_rate`, `parity_rate`, `recovery_rate`

**SAEnum final list (20 values):**
All 8 Phase-94.4 family-level values + `conversion_rate_{bullet,blitz,rapid,classical}` + `parity_rate_{bullet,blitz,rapid,classical}` + `recovery_rate_{bullet,blitz,rapid,classical}`

## Decisions Made

- Recovery builder's bucket classification: when `entry_eval_mate IS NOT NULL` and the user is not winning (mate is negative from user's perspective), classify as `recovery`; `entry_eval_cp <= -100` signed (user perspective) also maps to `recovery`. This mirrors the existing `per_user_cte_score_gap_bucket_tc` CASE logic.
- Removed stale `# ty: ignore[unresolved-import]` annotations from Wave-0 tests after symbols landed. Plan 01 added these for RED state; Plan 02 turning them GREEN requires removal for ty compliance.
- Updated `test_benchmark_metric_enum.py` EXPECTED_ENUM_LABELS from 8 to 20 values — the guard's exact-count assertion was blocking after the ENUM widening (correct behavior, needed update).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Integration test EXPECTED_ENUM_LABELS blocked after ENUM widening**
- **Found during:** Task 2 (full pytest suite run)
- **Issue:** `tests/integration/test_benchmark_metric_enum.py` had `EXPECTED_ENUM_LABELS` hard-coded to the 8 Phase-94.4 values. After the migration added 12 new values, the test failed with "Left contains 12 more items."
- **Fix:** Updated `EXPECTED_ENUM_LABELS` to include all 20 values in alphabetical order; updated docstring from "8 labels" to "20 labels."
- **Files modified:** `tests/integration/test_benchmark_metric_enum.py`
- **Verification:** Full pytest suite passes (532 passed, 1 expected-RED)
- **Committed in:** `ef360e10` (Task 2 commit)

**2. [Rule 1 - Bug] Stale ty: ignore[unresolved-import] annotations causing warnings**
- **Found during:** Task 2 (ty check after widening CdfMetricId)
- **Issue:** Wave-0 added `# ty: ignore[unresolved-import]` to each deferred import in the rate builder tests. Once the symbols exist (Wave 1), these annotations become stale — ty reports `warning[unused-ignore-comment]`.
- **Fix:** Removed the `# ty: ignore[unresolved-import]` comments and simplified class docstrings (removed Wave-0 RED state description).
- **Files modified:** `tests/services/test_canonical_slice_sql.py`
- **Verification:** `uv run ty check app/ tests/` exits 0 with "All checks passed!"
- **Committed in:** `ef360e10` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs that blocked CI or ty compliance)
**Impact on plan:** Both fixes required for correctness. No scope creep.

## Issues Encountered

- `uv run alembic check` reports a pre-existing drift for `ix_games_evals_pending` — this exists before this plan and is unrelated to the ENUM widening. Noted as out-of-scope; the ENUM values were confirmed via direct Postgres introspection (`SELECT enumlabel FROM pg_enum`).

## Next Phase Readiness

- Plan 03 contract: `per_user_cte_conv_rate_tc`, `per_user_cte_parity_rate_tc`, `per_user_cte_recovery_rate_tc` and `MINIMUM_RATE_BUCKET_SPANS` are all exported from `canonical_slice_sql.py` — Plan 03 can import them directly.
- Plan 05 contract: migration `3981239fd391` is at head on dev DB; `CdfMetricId` has 3 new family names; `gen_global_percentile_cdf.py` dispatch needs 3 new arms (Plan 05 task).
- Intentionally RED until Plan 03: `TestPerTcBucketStatsRatePercentileFields` tests — `rate_percentile` field absent from `PerTcBucketStats` Pydantic model.

## Self-Check

**Files created/modified verified:**
- `app/services/canonical_slice_sql.py` — found: `grep -c "def per_user_cte_conv_rate_tc\|def per_user_cte_parity_rate_tc\|def per_user_cte_recovery_rate_tc"` = 3, `MINIMUM_RATE_BUCKET_SPANS` count = 7 (1 def + 3 HAVING + 1 constant block + 2 docstring refs)
- `app/services/global_percentile_cdf.py` — found: `conversion_rate`, `parity_rate`, `recovery_rate` in `CdfMetricId`
- `app/models/user_benchmark_percentile.py` — found: `conversion_rate_bullet` in SAEnum
- `alembic/versions/20260530_extend_benchmark_metric_for_rate_percentiles.py` — exists, contains `down_revision = "c70f5d94b243"`, `_NEW_VALUES` tuple has 12 entries

**Commits verified:**
- `935d417e` — Task 1 commit
- `ef360e10` — Task 2 commit (includes migration file)

**Migration applied:** Postgres `benchmark_metric` ENUM confirmed at 20 values via `pg_enum` query.

## Self-Check: PASSED

---
*Phase: 99-percentile-badges-for-conversion-parity-and-recovery*
*Completed: 2026-05-30*
