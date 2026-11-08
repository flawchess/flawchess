---
phase: 243-out-of-the-opening-worse-better-rates
plan: 02
subsystem: backend
tags: [percentiles, cohort-cdf, benchmark-db, regen, eval-source]

requires:
  - phase: 243-out-of-the-opening-worse-better-rates
    plan: 01
    provides: per_user_cte_opening_out_rate builder, opening CdfMetricId values, TEXT+CHECK metric column
provides:
  - opening_worse_rate / opening_better_rate colour-pooled CDFs (12474 rows each) merged into app/data/cohort_cdf.tsv
  - gen_global_percentile_cdf.py --metrics scoped merge regen (load_cells_from_tsv / merge_cells)
  - scripts/opening_out_eval_source_report.py (report-only paired per-eval-source comparison)
  - 8 golden SQL fixtures for the opening metrics
  - dev benchmark_cohort_cdf seeded with the opening rows
affects: [243-04 read path, 243-05, prod CDF seed on deploy]

actuals:
  tokens: 22000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Scoped regen: --metrics rewrites only the named metrics' TSV rows; all other rows stay byte-identical to main"
    - "Colour-pooled CDF: one point per (user, colour) passing the 30-game floor, ranked against one curve per (anchor, TC); MIN/MAX/n_users count distinct users"

key-files:
  created:
    - scripts/opening_out_eval_source_report.py
    - tests/scripts/test_opening_out_eval_source_report.py
    - tests/scripts/test_gen_global_percentile_cdf_opening_out.py
    - reports/percentile/cohort-percentile-cdf-opening-out-latest.md
    - tests/scripts/fixtures/global_percentile_cdf/opening_worse_rate__{bullet,blitz,rapid,classical}.sql
    - tests/scripts/fixtures/global_percentile_cdf/opening_better_rate__{bullet,blitz,rapid,classical}.sql
  modified:
    - scripts/gen_global_percentile_cdf.py
    - tests/scripts/test_cohort_cdf_seed_artifact.py
    - app/data/cohort_cdf.tsv

key-decisions:
  - "A2: cohort MIN (100), MAX (500) and n_users count DISTINCT users, not colour points, so both colour points of a user enter or leave a cell together (rated costly: changing it means a regen, a reseed and a prod Stage B backfill)"
  - "Regen pinned to --snapshot-date 2026-05-30 and its own report path so the Endgames report and CDFs are untouched"

patterns-established:
  - "Every in-scope CDF metric needs a _METRIC_DISPLAY entry; guarded by test_every_in_scope_metric_has_a_report_display_name"

requirements-completed: [D-04, D-05, D-06]

coverage:
  - id: D1
    description: "Opening worse/better CDFs are produced per TC through per_user_cte_opening_out_rate(source='benchmark'), colour-pooled, ranked against the per-TC anchor"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_global_percentile_cdf_opening_out.py"
        status: pass
      - kind: unit
        ref: "tests/scripts/fixtures/global_percentile_cdf (8 new opening goldens)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Scoped regen leaves every non-opening TSV row byte-identical to main and in order; 12474 rows each for the two opening metrics; n_users <= 500; snapshot_month 2026-05"
    requirement: "D-06"
    verification:
      - kind: other
        ref: "diff -q of main:app/data/cohort_cdf.tsv vs the TSV minus opening rows (clean); awk check n_users>500 = 0, bad snapshot = 0"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_cohort_cdf_seed_artifact.py, tests/scripts/test_gen_global_percentile_cdf_unchanged.py (57 passed with the other script tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dev benchmark_cohort_cdf holds 12474 rows for each opening metric after scripts.seed_cohort_cdf (147609 rows upserted, 0 errors)"
    requirement: "D-05"
    verification:
      - kind: other
        ref: "SELECT metric, count(*) FROM benchmark_cohort_cdf WHERE metric LIKE 'opening_%' -> opening_better_rate 12474, opening_worse_rate 12474"
        status: pass
    human_judgment: false
  - id: D4
    description: "Per-eval-source paired comparison produced from the benchmark DB (report-only, no gate)"
    verification:
      - kind: other
        ref: "temp/opening-out-regen/eval-source.md (table below)"
        status: pass
    human_judgment: false

duration: ~2h (incl. orchestrator regen runs)
completed: 2026-10-31
status: complete
plan_head_before: 944dc07e9aee51272091287c85e828dd2472be45
plan_head_after: 85159108e471ca2431222c573138e912bd92ebba
commits: 3
---

# Phase 243 Plan 02: Opening-out CDFs and eval-source check Summary

**The colour-pooled `opening_worse_rate` and `opening_better_rate` CDFs are regenerated from the benchmark DB, merged into `cohort_cdf.tsv` (12474 rows each) with every Endgames row byte-identical to main, and seeded into the dev table.**

## Accomplishments

- `gen_global_percentile_cdf.py` now carries the two opening ids in `IN_SCOPE_METRICS`, dispatches them to `per_user_cte_opening_out_rate(source="benchmark")`, ranks colour-pooled points against one curve per (anchor, TC), and supports `--metrics` for a scoped merge regen (`load_cells_from_tsv` / `merge_cells`).
- New `scripts/opening_out_eval_source_report.py` produces the paired per-eval-source table (report-only).
- 8 new golden SQL fixtures; the 44 existing ones are unchanged.
- Regen: `--target benchmark --snapshot-date 2026-05-30 --metrics opening_worse_rate,opening_better_rate`, 502.7 s runtime on the successful run.
- Task 3 gates: non-opening TSV rows equal main byte for byte (`diff -q` clean); 12474 rows per opening metric; no `n_users` above 500; all snapshot months 2026-05; round-trip/golden/seed-artifact tests pass (57 passed); dev seed upserted 147609 rows with 0 errors and the dev table holds 12474 rows for each opening metric.

## Non-suppressed cell counts (from regen.log / report)

| Metric | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| opening_worse_rate | 35/37 | 36/37 | 36/37 | 19/37 |
| opening_better_rate | 35/37 | 36/37 | 36/37 | 19/37 |

Classical is sparse as expected (126/148 cells non-suppressed per metric); the report's Option A/B discussion applies, chips for users in suppressed cells render nothing.

## Per-eval-source check (report-only)

Source shares of qualifying games:

| TC | lichess | local_full | entry_lane |
|---|---:|---:|---:|
| blitz | 20.6% | 10.9% | 68.5% |
| rapid | 30.6% | 10.7% | 58.8% |

Paired per-user x colour deltas, first minus second source (pp, mean +/- SE; at least 20 games per source):

| TC | source A | source B | pairs | worse delta (pp) | better delta (pp) |
|---|---|---|---:|---:|---:|
| blitz | lichess | local_full | 1345 | +1.97 +/- 0.28 | -0.97 +/- 0.28 |
| blitz | lichess | entry_lane | 1392 | +1.70 +/- 0.23 | -0.80 +/- 0.23 |
| blitz | local_full | entry_lane | 1656 | -0.12 +/- 0.18 | +0.09 +/- 0.18 |
| rapid | lichess | local_full | 1241 | +3.59 +/- 0.32 | -3.57 +/- 0.31 |
| rapid | lichess | entry_lane | 1638 | +3.18 +/- 0.25 | -3.53 +/- 0.23 |
| rapid | local_full | entry_lane | 1281 | -0.21 +/- 0.22 | +0.09 +/- 0.23 |

Comparison to SEED-206's finding of under ~1 pp: the lichess-vs-own-eval gaps are larger than that (about +1.7 to +2.0 pp worse in blitz, +3.2 to +3.6 pp worse and -3.5 pp better in rapid), while local_full and entry_lane agree within 0.2 pp. Reported only; no assertion or gate is placed on these numbers.

## Run history

1. Run 1 crashed at report render with a `KeyError` (the TSV had been written, the report had not); fixed in `a72b34fa0`.
2. Run 2 died with `DiskFullError` (benchmark container `/dev/shm` exhausted) because the eval-source report ran concurrently with the regen.
3. Run 3 completed alone (502.7 s) and produced the committed TSV and report.

## Task Commits

1. **Task 1:** `3a3428122` feat(243-02): colour-pooled opening CDFs, scoped --metrics merge regen, eval-source report
2. **Task 2:** no commit by design (orchestrator-run regen and eval-source report)
3. **Fix (orchestrator):** `a72b34fa0` fix(243-02): regen report display names for opening metrics, LF TSV writer
4. **Task 3:** `85159108e` feat(243-02): scoped regen of opening worse/better CDFs into cohort_cdf.tsv

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_METRIC_DISPLAY` lacked the opening ids; TSV writer emitted CRLF**
- **Found during:** Task 2 (first regen run)
- **Issue:** The first regen wrote the TSV and then crashed with `KeyError` at report render because `_METRIC_DISPLAY` had no entries for the opening metric ids. Separately, the csv writer emitted CRLF line endings while the committed TSV is LF, which would have rewritten every row.
- **Fix:** Added the display names; set `lineterminator="\n"` on the TSV writer; added guard test `test_every_in_scope_metric_has_a_report_display_name`.
- **Files modified:** scripts/gen_global_percentile_cdf.py, tests/scripts/test_gen_global_percentile_cdf_opening_out.py
- **Commit:** a72b34fa0

### Process note

The orchestrator ran the eval-source report concurrently with the regen in run 2, exhausting the benchmark container's shared memory. Heavy benchmark-DB scripts should run one at a time.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- FOUND: app/data/cohort_cdf.tsv, reports/percentile/cohort-percentile-cdf-opening-out-latest.md, scripts/opening_out_eval_source_report.py
- FOUND commits: 3a3428122, a72b34fa0, 85159108e
