---
phase: quick-260529-gl0
plan: "01"
subsystem: percentile-cte
tags: [refactor, dead-code, canonical-slice-sql, percentile]
dependency_graph:
  requires: []
  provides: []
  affects:
    - app/services/canonical_slice_sql.py
    - tests/services/test_canonical_slice_sql.py
    - tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py
tech_stack:
  added: []
  patterns: []
key_files:
  modified:
    - app/services/canonical_slice_sql.py
    - tests/services/test_canonical_slice_sql.py
    - tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py
decisions:
  - "Retained docstring context in canonical_slice_sql.py module header (describes pooled methodology still relevant to surviving _tc builders)"
  - "Repointed negative regression guards (elo_bucket, tc_bucket, sparse-cell, old join predicate) to per_user_cte_score_gap_tc as representative live builder"
  - "Folded recent_capped prelude + per_user_values substring assertions into test_score_gap_tc_pooled_body_byte_identical_across_sources"
  - "Replaced per_user_cte_for dispatcher calls in TestPitfall1UserIdWideningExistingBuilders with inline builder dispatch dicts"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-29T10:17:05Z"
  tasks_completed: 3
  files_modified: 3
---

# Phase quick-260529-gl0 Plan 01: Delete Dead Non-Per-TC Percentile CTEs

Remove 5 dead non-per-TC pooled CTE builders from `canonical_slice_sql.py` and repoint/trim tests; zero loss of live-builder coverage.

## What Was Done

The percentile metric system was redesigned (Phase 94.3+) to compute per-time-control (`_tc`) lookups. The original pooled (non-`_tc`) CTE builders and their dispatcher `per_user_cte_for` had no production callers — only tests referenced them. This plan removes all 5 dead symbols and repoints the test suite to the live `_tc` builders.

**Symbols deleted from `app/services/canonical_slice_sql.py`:**

1. `_recent_capped_cte` (~L260 original) — non-per-TC recency helper, used only by the 3 dead builders below.
2. `per_user_cte_score_gap` (~L320) — pooled all-TC score gap builder.
3. `per_user_cte_achievable` (~L381) — pooled all-TC achievable score gap builder.
4. `per_user_cte_score_gap_bucket` (~L454) — pooled all-TC bucket builder (conversion/parity/recovery).
5. `per_user_cte_for` (~L1363) — dispatcher for the 4 dead builders + 12 live per-TC builders; stale (missing `recovery_score_gap` arm that the live dispatcher has).

**File reduced from 1431 to 1081 lines (-350 lines).**

## Tasks

### Task 1: Delete 5 dead symbols from canonical_slice_sql.py
- Commit: `cb944127`
- Files: `app/services/canonical_slice_sql.py`
- Dead-check re-confirmed: `per_user_cte_for` had zero prod/script callers; both live dispatchers (`_per_user_cte_for_family_and_tc`, `_per_user_cte_for_metric_and_tc`) only invoke `_tc` builders.
- Also cleaned docstring references in `_recent_capped_per_tc_cte` and the 3 `_tc` builder docstrings that mentioned dead symbol names.

### Task 2: Repoint parity tests to live _tc builders
- Commit: `8cc62d90`
- File: `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py`
- Removed `per_user_cte_for` import; added 6 live builder imports.
- Deleted 4 dead `_METRICS`-keyed tests; folded prelude/per_user_values substring assertions into `test_score_gap_tc_pooled_body_byte_identical_across_sources`.
- Replaced `_PER_TC_METRIC_IDS`-parametrised tests with `(family, tc)` parametrisation calling `_call_per_tc_builder` dispatcher.
- Repointed `test_existing_94_3_per_tc_pooled_body_byte_identical_after_pitfall_1` to live builders.
- 88 tests pass.

### Task 3: Repoint/trim structural tests, grep-clean, full gate
- Commit: `e1056e63`
- Files: `tests/services/test_canonical_slice_sql.py`, `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py`, `app/services/canonical_slice_sql.py`
- Replaced `TestPooledShape` with `TestPooledShapeNegativeGuards` repointed to `per_user_cte_score_gap_tc`.
- Deleted `TestRecencyWindow`; repointed `test_cap_appears_once_per_builder_output` to live builder.
- Deleted `TestInclusionFloor` (floor coverage exists in live `_tc` builder tests).
- Deleted `TestPerTcDispatcher` (dispatcher is gone; underlying builder properties covered by `TestPerTcBuilders`).
- Deleted `TestPerUserCteSection2RecoveryWidening` (entire class called dead `per_user_cte_score_gap_bucket`).
- Deleted `test_non_per_tc_builders_are_not_touched_by_pitfall_1` (scope guard moot).
- Repointed `TestPitfall1UserIdWideningExistingBuilders` methods to call live builders via inline dispatch dicts.
- 2212 tests pass.

## Verification

- Zero grep hits for all 5 deleted symbol names across `app/ scripts/ tests/` (excluding `_tc`/`_per_tc` names).
- `git diff --stat tests/scripts/fixtures/global_percentile_cdf/` shows zero changes (32 goldens byte-unchanged).
- `uv run ruff format app/ tests/` reports 187 files unchanged.
- `uv run ruff check app/ tests/ --fix` reports all checks passed.
- `uv run ty check app/ tests/` reports all checks passed.
- `uv run pytest -x --deselect tests/scripts/test_backfill_user_percentiles.py::test_backfill_target_prod_refuses_when_tunnel_down` reports 2212 passed, 16 skipped.
- Known unrelated failure: `test_backfill_target_prod_refuses_when_tunnel_down` fails locally because prod SSH tunnel is open on port 15432; passes in CI.

## Deviations from Plan

### Docstring cleanup added

**Found during:** Tasks 1 and 3
**Issue:** The live `_tc` builder docstrings referenced dead symbol names (`_recent_capped_cte`, `per_user_cte_score_gap`, etc.) as their "non-per-TC analogs". The plan's grep guard (`grep -rn ... | grep -v "_tc\|_per_tc"`) would flag these comment references as false positives.
**Fix:** Updated 4 docstrings in `canonical_slice_sql.py` to describe the properties directly without referencing the dead names. Also updated test comment references in both test files.
**Files modified:** `app/services/canonical_slice_sql.py`, `tests/services/test_canonical_slice_sql.py`, `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py`

None of these are behavior changes.

## Self-Check: PASSED

- `app/services/canonical_slice_sql.py` exists and contains `per_user_cte_score_gap_tc`
- `tests/services/test_canonical_slice_sql.py` exists
- `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py` exists
- Commits `cb944127`, `8cc62d90`, `e1056e63` verified in git log
