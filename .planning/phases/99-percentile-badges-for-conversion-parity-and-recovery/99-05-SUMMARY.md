---
phase: 99-percentile-badges-for-conversion-parity-and-recovery
plan: "05"
subsystem: database
tags:
  - percentile
  - endgame
  - cdf-regen
  - backfill
  - wave-3

dependency_graph:
  requires:
    - phase: 99-03
      provides: IN_SCOPE_METRICS wired with 3 rate families in gen_global_percentile_cdf.py; STAGE_B_METRIC_FAMILIES extended
  provides:
    - app/services/global_percentile_cdf.py (COHORT_PERCENTILE_CDF regenerated with 12 new rate-percentile cells)
    - reports/percentile/cohort-percentile-cdf-latest.md (regen report for 11 metrics × 37 anchors × 4 TCs = 1,628 cells)
    - user_benchmark_percentiles (dev DB: 27 conv_rate rows, 27 parity_rate rows, 26 recovery_rate rows)
    - alembic/versions/20260530_220134_52c928794fe7 (bare family name ENUM fix, Rule 1)
  affects:
    - Plan 04 (frontend chip wiring — chips now have real CDF data to render with)
    - Prod DB (backfill deferred to deploy — Task 3 sign-off 2026-05-31)

tech-stack:
  added: []
  patterns:
    - "CDF regen: gen_global_percentile_cdf.py --target benchmark --snapshot-date 2026-05-30, 11 metrics in ~690s"
    - "Rule 1 bug fix: bare family names missing from benchmark_metric ENUM — upsert_percentile needs 'conversion_rate' not 'conversion_rate_blitz'"
    - "Dev backfill: backfill_user_percentiles.py --target dev --snapshot-date 2026-05-30, 18 users, 62s"

key-files:
  created:
    - reports/archive/cohort-percentile-cdf-latest-2026-05-30-phase-94.4.md
    - alembic/versions/20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py
  modified:
    - app/services/global_percentile_cdf.py (COHORT_PERCENTILE_CDF regenerated — 12 new rate cells added)
    - reports/percentile/cohort-percentile-cdf-latest.md (regen report updated)
    - app/models/user_benchmark_percentile.py (benchmark_metric_enum 20 → 23 values)
    - tests/integration/test_benchmark_metric_enum.py (EXPECTED_ENUM_LABELS 20 → 23)

key-decisions:
  - "Rule 1 auto-fix: benchmark_metric ENUM lacked bare family names — upsert path needs 'conversion_rate' not 'conversion_rate_blitz'; migration 52c928794fe7 added 3 bare family names"
  - "parity_rate|classical CDF is empty (0 non-suppressed anchors): 147 benchmark users qualify but max in-window=49 < 100 MIN floor; expected D-05 sparsity, not Pitfall 1"
  - "Dev DB classical rate rows: 0 rows (all 18 users below ≥30-span floor for classical); expected per D-05 validation"
  - "Prod backfill: DEFERRED to deploy per human sign-off 2026-05-31 (D-11 / Task 3); migrations auto-apply at deploy, per-user backfill runs post-deploy"

requirements-completed: []

duration: ~75min
completed: "2026-05-31"
---

# Phase 99 Plan 05: CDF Regen + Dev Backfill Summary

**Cohort CDFs regenerated into global_percentile_cdf.py for all 12 new rate-percentile cells (conversion_rate/parity_rate/recovery_rate × 4 TCs); dev DB backfilled after a Rule-1 ENUM fix; prod backfill deferred to deploy per human sign-off (D-11).**

## Performance

- **Duration:** ~75 min (includes 690s regen + 62s backfill + debugging Rule 1 bug)
- **Started:** 2026-05-30T21:28:39Z
- **Completed:** 2026-05-31 (Task 3 checkpoint resolved — prod backfill deferred to deploy)
- **Tasks completed:** 3 of 3 (Task 3 = human-action checkpoint, signed off: defer prod to deploy)
- **Files modified:** 6 (+ 2 created)

## Accomplishments

### Task 1: CDF Regen (f7e40b0e)

- Ran `gen_global_percentile_cdf.py --target benchmark --snapshot-date 2026-05-30` (~690s runtime)
- Regenerated `COHORT_PERCENTILE_CDF` in `global_percentile_cdf.py` covering all 11 metrics: the 8 existing Phase 94.4 metrics + 3 new rate families
- Prior report archived to `reports/archive/cohort-percentile-cdf-latest-2026-05-30-phase-94.4.md`
- New report at `reports/percentile/cohort-percentile-cdf-latest.md` (11 metrics × 37 anchors × 4 TCs = 1,628 cells)
- Format + lint + ty all clean after regen

**Per-cell CDF row counts (12 new cells):**

| Metric | TC | Rows returned | Non-suppressed anchors | Notes |
|--------|-----|--------------|------------------------|-------|
| conversion_rate | bullet | 944 | 34/37 | |
| conversion_rate | blitz | 934 | 35/37 | |
| conversion_rate | rapid | 955 | 33/37 | |
| conversion_rate | classical | 234 | 9/37 | Sparse — expected |
| parity_rate | bullet | 846 | 33/37 | |
| parity_rate | blitz | 855 | 33/37 | |
| parity_rate | rapid | 744 | 30/37 | |
| parity_rate | classical | 147 | 0/37 | All suppressed — max in-window 49 < 100 MIN |
| recovery_rate | bullet | 942 | 34/37 | |
| recovery_rate | blitz | 914 | 35/37 | |
| recovery_rate | rapid | 888 | 32/37 | |
| recovery_rate | classical | 226 | 4/37 | Sparse — expected |

**Pitfall 1 check:** None of the bullet/blitz/rapid cells are empty — users were returned for all three (944–955 for conv, 846–855 for parity, 888–942 for recovery). `parity_rate|classical` has 147 user rows but 0 non-suppressed anchors because the density never reaches the 100-user MIN floor per anchor. This is correct CDF suppression behavior (D-05), not Pitfall 1.

**Sanity check vs benchmarks-latest.md §3.2.1:**

| Metric | TC | CDF p50 (anchor 1400) | Benchmark §3.2.1 per-TC |
|--------|----|-----------------------|-------------------------|
| conversion_rate | bullet | 62.8% | 65.6% |
| conversion_rate | blitz | 71.7% | 71.9% |
| conversion_rate | rapid | 73.6% | 74.6% |
| parity_rate | bullet | 48.8% | ~50.0% |
| parity_rate | blitz | 49.3% | ~50.8% |
| recovery_rate | bullet | 35.9% | 35.3% |
| recovery_rate | blitz | 29.3% | 30.9% |
| recovery_rate | rapid | 25.8% | 28.1% |

All CDF medians are in the expected ballpark. The slight downward bias for conversion (62.8% vs 65.6% at bullet) reflects that the CDF is anchored at 1400 Elo users, while the benchmark §3.2.1 per-TC row pools all ELOs (pooled bullet mean = 65.2%).

### Task 2: Dev Backfill (f4295f16)

**Rule 1 Auto-fix found during backfill:** The `benchmark_metric` Postgres ENUM (migration 3981239fd391) contained TC-suffixed values (`conversion_rate_bullet`, etc.) but NOT bare family names (`conversion_rate`). `upsert_percentile` is called with `metric="conversion_rate"` (the CdfMetricId) and `time_control_bucket="blitz"` as separate args. The ENUM rejected the bare family name with `invalid input value for enum benchmark_metric: "conversion_rate"`. This error was silently swallowed by `compute_stage_b`'s inner `try/except` (which calls `sentry_sdk.capture_exception` — no Sentry configured in local dev). Result: zero rows written for all 3 new rate metrics despite the SQL CTE returning correct values.

Fix: added migration `52c928794fe7` adding `conversion_rate`, `parity_rate`, `recovery_rate` as bare ENUM values. Updated `benchmark_metric_enum` SAEnum from 20 to 23 values. Updated `test_benchmark_metric_enum.py` guard from 20 to 23 labels.

**Dev backfill results (after fix):**

| Metric | TC | included | floor_rej | suppressed |
|--------|-----|----------|-----------|------------|
| conversion_rate | bullet | 3 | 14 | 1 |
| conversion_rate | blitz | 10 | 7 | 1 |
| conversion_rate | rapid | 12 | 6 | 0 |
| conversion_rate | classical | 0 | 18 | 0 |
| parity_rate | bullet | 3 | 14 | 1 |
| parity_rate | blitz | 10 | 7 | 1 |
| parity_rate | rapid | 11 | 6 | 1 |
| parity_rate | classical | 0 | 18 | 0 |
| recovery_rate | bullet | 3 | 14 | 1 |
| recovery_rate | blitz | 10 | 7 | 1 |
| recovery_rate | rapid | 11 | 7 | 0 |
| recovery_rate | classical | 0 | 18 | 0 |

**MCP query verification:** `SELECT metric::text, count(*) FROM user_benchmark_percentiles WHERE metric::text IN ('conversion_rate','parity_rate','recovery_rate') GROUP BY metric`:
- `conversion_rate`: 27 rows
- `parity_rate`: 27 rows
- `recovery_rate`: 26 rows

Classical: 0 rows for all three rate metrics — expected per D-05 (dev DB classical users all fall below the ≥30 span floor).

`_ALL_METRICS` verify command exits 0 (all 3 families present).

### Task 3: Prod checkpoint resolved — DEFERRED to deploy (human sign-off, D-11)

Prod backfill NOT run on this branch. User signed off (2026-05-31) to **defer the prod backfill to deploy time**: the regenerated CDF artifact and both ENUM migrations (`3981239fd391`, `52c928794fe7`) ship with the code; alembic applies the migrations automatically on backend container startup. The per-user prod backfill (`scripts/backfill_user_percentiles.py --target prod`) runs once this milestone is deployed to production.

## Task Commits

1. **Task 1: CDF regen** - `f7e40b0e` (feat)
2. **Task 2: Dev backfill + Rule 1 ENUM fix** - `f4295f16` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] benchmark_metric ENUM missing bare family names for rate metrics**
- **Found during:** Task 2 (backfill ran but wrote 0 rows for all 3 rate metrics)
- **Issue:** Migration 3981239fd391 added only TC-suffixed ENUM values (`conversion_rate_bullet` etc.). `upsert_percentile` is called with `metric="conversion_rate"` (CdfMetricId family name), which the ENUM rejects. The error was silently swallowed by `compute_stage_b`'s inner `try/except`. All 18 dev users showed `floor_rej=18` even though `_compute_metric_for_user_per_tc` returned correct values.
- **Fix:** Created migration `52c928794fe7` adding bare family names (`conversion_rate`, `parity_rate`, `recovery_rate`) as ENUM values. Updated SAEnum in `user_benchmark_percentile.py` from 20 to 23 values. Updated `test_benchmark_metric_enum.py` guard.
- **Files modified:** `alembic/versions/20260530_220134_52c928794fe7_...py`, `app/models/user_benchmark_percentile.py`, `tests/integration/test_benchmark_metric_enum.py`
- **Commit:** `f4295f16`

### Verify Command Bug in Plan

The plan's Task 1 `<verify>` command contains a logic error:
```python
[m for m in (...) if not any(k[0]==m for k in C)]
```
`for k in C` iterates over string metric names (dict keys), so `k[0]` is a character (`'c'`, `'p'`, `'r'`), not a metric name tuple element. The command always reports missing metrics even when they're present. The correct check is `m not in C`. The acceptance criteria were verified manually — all 3 metrics are in `C` with non-empty entries.

## Prod Backfill Disposition

**DEFERRED TO DEPLOY** — User signed off on 2026-05-31 (Task 3 `checkpoint:human-action`, D-11) to defer the prod backfill to deploy time rather than running an ad-hoc prod write ahead of the production branch. The regenerated CDF artifact (`global_percentile_cdf.py`) and both ENUM migrations ship with the code deploy — prod reads the same static CDF; only the per-user rows need backfilling. Post-deploy step (after this milestone reaches production):

```bash
bin/prod_db_tunnel.sh                                      # open tunnel → localhost:15432
# (alembic upgrade head runs automatically on backend container startup at deploy)
uv run python scripts/backfill_user_percentiles.py --target prod --snapshot-date 2026-05-30
bin/prod_db_tunnel.sh stop
```

`_assert_target_safe` port-checks the prod target. Tracked as a deferred deploy-time obligation (see `.planning/todos/`).

## Known Stubs

None — the CDF is real data from the benchmark DB, and dev user rows are real computed percentiles (suppressed for classical where the data is sparse, as expected).

## Self-Check

**Files created/modified verified:**
- `app/services/global_percentile_cdf.py` — found: `conversion_rate`, `parity_rate`, `recovery_rate` keys in `COHORT_PERCENTILE_CDF` with 111, 96, 105 entries respectively
- `reports/percentile/cohort-percentile-cdf-latest.md` — exists, 116,220 bytes, 2026-05-30 23:40
- `reports/archive/cohort-percentile-cdf-latest-2026-05-30-phase-94.4.md` — exists, archived prior report
- `alembic/versions/20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py` — exists, down_revision=3981239fd391
- `app/models/user_benchmark_percentile.py` — benchmark_metric_enum has 23 values
- `tests/integration/test_benchmark_metric_enum.py` — EXPECTED_ENUM_LABELS has 23 entries
- Dev DB: 27 conversion_rate rows, 27 parity_rate rows, 26 recovery_rate rows

**Commits verified:**
- `f7e40b0e` — Task 1 CDF regen commit
- `f4295f16` — Task 2 dev backfill + Rule 1 fix commit

**Test suite:** 2191 passed, 16 skipped, 3 warnings
**ty check:** All checks passed
**ruff:** All checks passed

## Self-Check: PASSED

---
*Phase: 99-percentile-badges-for-conversion-parity-and-recovery*
*Completed: 2026-05-31 (paused at Task 3 prod checkpoint)*
