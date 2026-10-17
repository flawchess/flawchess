---
phase: 241-codebase-cleanup
plan: 19
subsystem: services
tags: [cleanup, comments, percentiles, canonical-slice-sql, activity]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/diff/ledger and the source-scan test runner"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "Canonical slice SQL, cohort CDF, user percentile, activity and current-strength services free of planning tags, with ledgers/241-19.txt covering all 26 INVENTORY rows"
affects: [241-70]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 689a1b071ef8ce59692f1625b96ae13ed187f695
plan_head_after: e205116d881584375b14e0e42b4230a765a5bcfe

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-19.txt
  modified:
    - app/services/canonical_slice_sql.py
    - app/services/global_percentile_cdf.py
    - app/services/user_benchmark_percentiles_service.py
    - app/services/activity_queries.py
    - app/services/activity_stats.py
    - app/services/current_strength_service.py

key-decisions:
  - "SQL-string comments inside canonical_slice_sql.py f-strings (`-- user_id widened per Phase 94.4 Pitfall 1` x9, `quick-260529-js1` in the chesscom_conversion_lookup CTE) are runtime SQL text and stay, per the plan prohibition on touching builder output"
  - "Single-digit tags the scan regex does not match (D-1, D-5, D-6, D-8, D-9, D-10, D3, V5, SC-2, `94.1 Plan 09`, `T-99-SQLi`) were removed by hand along with the scanned ones, using a broader grep"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: ~75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 19: Benchmark, Percentile and Activity Services Comment Cleanup Summary

**All planning tags and the stale claims in the canonical slice SQL, cohort CDF, user percentile, activity and current-strength services are gone; the token diff against PHASE_BASE is empty, so SQL builders, CdfMetricId values and the activity payload are unchanged.**

## Accomplishments

- Scope scan before: 60 matches in the Task 2 files plus about 80 in the Task 1 files; `scan --gate --scope scopes/241-19.txt` now reports 0 matches over all 8 files. `app/services/__init__.py` and `percentile_compute_registry.py` were already clean and are untouched.
- Ledger: 26 rows, all APPLIED, each re-verified against the code first (`cleanup.py ledger` exit 0).
- Codemod vs hand edits: the codemod rewrote 23 lines in Task 1 and 27 in Task 2 (50 total); the 98 flagged lines were hand-edited through exact-string batches (63 edits in Task 1, 56 in Task 2), including full rewrites of the two largest docstrings (canonical_slice_sql module docstring, user_benchmark_percentiles_service module docstring).

## Stale content fixed beyond tag removal (STYLE-GUIDE 2.2)

- canonical_slice_sql.py module docstring claimed the builders pool "across all time controls" and emit `(metric_value, n_games)`. Every builder takes a `TimeControlBucket` and `per_user_values` projects `user_id`; both corrected. The `elo_bucket_expr` / `sparse_exclusion_sql` docstrings cited `_build_per_bucket_sanity_query`, which no longer exists in `scripts/`; they now say the helpers are test-only (they stay, as the plan requires).
- user_benchmark_percentiles_service.py said Stage B owns "the other 7" families (it is 10), that chess.com games convert via `CHESSCOM_BLITZ_TO_LICHESS` / a ChessGoals snapshot (they use the composed native-TC grid), and cited "cold-drain" (glossary row 33 retires it; reworded to "eval drain").
- activity_queries.py fetch_activity docstring listed the row without the dense user index it really emits; fetch_funnel's "linked stage" paragraph rewritten from the verifier text after confirming `start_import` writes the username and creates the `import_jobs` row in one request (INV-L635 / T-241-35: the docstring states the dense-index rule, checked against the loop that builds `out`).
- activity_stats.py, current_strength_service.py: history narration ("no longer four preset keys", "used to", "the helper this module replaces") rewritten in present tense.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-19.txt` | exit 0 (8 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-19.txt` | exit 0 (8 selected, 6 changed, no residue) |
| `cleanup.py ledger --scope ... --ledger ledgers/241-19.txt` | exit 0 |
| `ruff check app/services`, `ruff format --check app/services` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean before edits) |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed |
| source_scan_tests.sh python half, run serially (no `-n 4`) | 95 passed + 5 passed |
| `tests/services/test_canonical_slice_sql.py` | 261 passed |
| current_strength, global_percentile_cdf, percentile gate/registry, user_benchmark_percentiles_service, admin_activity_stats tests | 79 passed, 1 skipped |

The Python half of `source_scan_tests.sh` was run serially because sibling executors share the dev Postgres; this is environmental, not a plan failure.

## Task Commits

1. **Task 1: canonical_slice_sql.py and global_percentile_cdf.py (12 rows)** - `fe4e314af`
2. **Task 2: percentiles, activity, current strength (14 rows) and plan gates** - `e205116d8`

`commits: 2` is measured with `git rev-list --count 689a1b071..HEAD` before the SUMMARY commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages) before the baseline gates; no tracked files changed. Baseline `ty check` passed before any edit.

**2. [Rule 2 - stale content] Single-digit planning tags the scan misses**
- The scan regex needs two or more digits (`D-\d{2,3}`), so tags such as `D-1`, `D-6`, `D3`, `V5`, `SC-2`, `94.1 Plan 09` stayed invisible to `scan --gate`. A broader grep over the scope removed them from comments and docstrings too.

**3. [Plan note] Ledger comment line**
- One `#` comment line at the end of ledgers/241-19.txt records the SQL-string comments left unchanged. No secondary-clause notes for rows owned by other plans were needed.

**Total deviations:** 1 blocking environment prep, 2 notes. No code token, SQL text, CdfMetricId value or runtime string changed.

## Known Stubs

None.

## Threat Flags

None. Comments and docstrings only; T-241-34 mitigated by the empty token diff, T-241-35 by the dense-index re-verification above.

## Notes for downstream plans

- The scan regex does not catch single-digit `D-N` tags, `V5`, `SC-2`, or `94.x Plan NN`; grep broadly (`\bD-[0-9]`, `Plan [0-9]`, `Pitfall`, `quick-`) before declaring a scope clean.
- Runtime SQL strings in canonical_slice_sql.py still carry nine `-- user_id widened per Phase 94.4 Pitfall 1` comments and one `quick-260529-js1` mention; removing them would change SQL text and needs its own decision (possibly with a test update), not a comment-only plan.

## Self-Check: PASSED

Files verified present: ledgers/241-19.txt, the six modified service files. Commits `fe4e314af` and `e205116d8` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
