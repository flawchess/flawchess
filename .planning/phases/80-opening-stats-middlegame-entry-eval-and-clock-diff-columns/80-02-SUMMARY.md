---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
plan: 02
subsystem: api
tags: [backend, repository, service, sql, aggregation, sqlalchemy, postgresql, eval, clock-diff]

# Dependency graph
requires:
  - phase: 80-01
    provides: OpeningWDL schema fields (MG + EG eval + clock-diff), compute_eval_confidence_bucket helper

provides:
  - query_opening_phase_entry_metrics_batch: batch SQL aggregation for phase-entry metrics (MG + EG eval + clock-diff) per opening in a single SQL pass with FILTER partitioning
  - OpeningPhaseEntryMetrics dataclass with 15 fields (6 MG eval, 3 clock, 6 EG eval) and four-bucket partition invariant
  - get_most_played_openings populated with all 15 new OpeningWDL fields via sequential awaits

affects:
  - 80-03 (schema response model used by frontend renderer)
  - 80-05 (frontend cells read from these response fields)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GROUP BY + JOIN SQL shape (not IN(subquery)) to avoid planner Nested Loop hangs on heavy users"
    - "Single SQL pass with phase IN (1, 2) + FILTER (WHERE phase = 1/2) for parallel MG + EG aggregation"
    - "ROW_NUMBER() OVER (PARTITION BY game_id, phase ORDER BY ply) to find phase-entry row per game"
    - "Sign convention applied at SQL level via case((user_color == 'white', 1), else_=-1)"
    - "Four-bucket partition invariant: eval_n + mate_n + null_eval_n + outlier_n == phase_entry_total"
    - "compute_eval_confidence_bucket called twice per opening (once for MG, once for EG)"

key-files:
  created:
    - tests/test_stats_repository_phase_entry.py
    - tests/services/test_stats_service_phase_entry.py
  modified:
    - app/repositories/stats_repository.py
    - app/services/stats_service.py

key-decisions:
  - "D-09: single SQL pass with phase IN (1, 2) + FILTER partitioning — avoids second DB round-trip"
  - "D-08: outlier trim |eval_cp| >= EVAL_OUTLIER_TRIM_CP=2000 classified as outlier_n, not null_eval_n, to keep partition invariant testable"
  - "GROUP BY + JOIN shape (not IN(subquery)) — mirrors endgame_repository.py:687-692 historical-bug fix"
  - "Sign convention at SQL level (not Python) so aggregates are already user-perspective by the time they're summed"
  - "Mate rows excluded from eval mean via FILTER predicate; counted as mate_n per phase"
  - "Clock diff only at MG entry (phase=1) — no EG-entry clock parallel per plan spec"

patterns-established:
  - "Phase-entry metrics query: GROUP BY full_hash with ROW_NUMBER + FILTER partitioning"
  - "Sequential await pattern: query_position_wdl_batch then query_opening_phase_entry_metrics_batch (no asyncio.gather)"

requirements-completed: [D-01, D-04, D-05, D-08, D-09]

# Metrics
duration: 13min
completed: 2026-05-03
---

# Phase 80 Plan 02: Opening Phase-Entry Metrics Batch Query Summary

**Batch SQL aggregation for MG-entry and EG-entry eval + clock-diff per opening using single-pass FILTER partitioning, wired into get_most_played_openings with compute_eval_confidence_bucket called twice per opening**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-05-03T20:22:11+02:00
- **Completed:** 2026-05-03T20:35:06+02:00
- **Tasks:** 2 (TDD: 4 commits — 2 RED + 1 GREEN + 1 fix)
- **Files modified:** 4

## Accomplishments

- Added `OpeningPhaseEntryMetrics` dataclass with 15 fields (6 MG eval buckets, 3 clock-diff, 6 EG eval buckets) and four-bucket partition invariant
- Implemented `query_opening_phase_entry_metrics_batch` using GROUP BY + JOIN shape with single SQL pass over `phase IN (1, 2)` and FILTER partitioning — no IN(subquery) antipattern, no asyncio.gather
- Extended `get_most_played_openings` to populate all 15 new `OpeningWDL` fields via sequential awaits and a finalizer invoking `compute_eval_confidence_bucket` twice per opening (once for MG, once for EG)
- 12 repository integration tests + 8 service integration tests all passing; full suite 1240 passed

## TDD Gate Compliance

| Gate | Commit | Description |
|------|--------|-------------|
| RED (repo) | `e95872f` | test(80-02): failing tests for query_opening_phase_entry_metrics_batch |
| GREEN (repo) | `d3c5070` | feat(80-02): add OpeningPhaseEntryMetrics + batch query |
| RED (service) | `738a7af` | test(80-02): failing service tests for phase-entry wiring |
| GREEN (service) | `0e71662` | feat(80-02): wire phase-entry metrics into get_most_played_openings |

## Task Commits

1. **Task 1 RED: failing repository tests** - `e95872f` (test)
2. **Task 1 GREEN: OpeningPhaseEntryMetrics + query_opening_phase_entry_metrics_batch** - `d3c5070` (feat)
3. **Task 2 RED: failing service tests** - `738a7af` (test)
4. **Task 2 GREEN: wire phase-entry metrics into service** - `0e71662` (feat)
5. **Fix: rephrase repository docstring** - `d3b849c` (fix)

## Files Created/Modified

- `app/repositories/stats_repository.py` - Added `EVAL_OUTLIER_TRIM_CP = 2000`, `OpeningPhaseEntryMetrics` dataclass (15 fields), `query_opening_phase_entry_metrics_batch` function
- `app/services/stats_service.py` - Extended `get_most_played_openings` with sequential awaits for phase-entry metrics, extended `rows_to_openings` finalizer with MG + EG eval CI computation and clock-diff calculation
- `tests/test_stats_repository_phase_entry.py` - 12 integration tests covering eval aggregation, color-flip symmetry, mate exclusion, outlier trim, partition invariant, clock diff, filter threading, empty hashes, recency filter
- `tests/services/test_stats_service_phase_entry.py` - 8 service-level integration tests covering MG eval fields, EG eval fields, zero-eval openings, clock diff percentage, filter threading, no-gather guard, color-flip symmetry, outlier trim propagation

## Decisions Made

- Single SQL pass with `phase IN (1, 2)` + `FILTER (WHERE phase = 1/2)` (D-09): avoids a second round-trip, roughly doubles the phase-scan row count but keeps latency proportional to one query
- GROUP BY + JOIN shape (not IN(subquery)): mirrors the fix at `endgame_repository.py:687-692` which resolved planner Nested Loop hangs on heavy users; same risk applies here
- Sign convention at SQL level via `case((user_color == "white", 1), else_=-1)`: sums are already user-perspective when aggregated, so no Python-side sign flip needed
- `EVAL_OUTLIER_TRIM_CP = 2000` (D-08): rows with `|eval_cp| >= 2000` classified as `outlier_n` (not `null_eval_n`) so the partition invariant `eval_n + mate_n + null_eval_n + outlier_n == phase_entry_total` remains testable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed literal "asyncio.gather" from docstrings and comments**
- **Found during:** Task 2 GREEN (service test `test_no_asyncio_gather_in_stats_service`)
- **Issue:** The test scans source code for `\basyncio\.gather\b` using `inspect.getsource`, stripping only lines starting with `#`. Docstring lines (not prefixed with `#`) in `stats_service.py` and `stats_repository.py` contained the literal string as negative examples ("never use asyncio.gather"). The acceptance criteria also requires `grep -c "asyncio.gather" stats_repository.py == 0`.
- **Fix:** Rephrased docstrings and comments to convey the same constraint without using the literal string (e.g., "AsyncSession not safe for concurrent use" instead of "never asyncio.gather")
- **Files modified:** `app/services/stats_service.py`, `app/repositories/stats_repository.py`
- **Verification:** All 20 tests pass, `grep -c "asyncio.gather" ... == 0` confirmed
- **Committed in:** `0e71662` (service), `d3b849c` (repository)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug — false-positive in static source guard)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Performance Considerations

Pre-merge EXPLAIN ANALYZE on Adrian's user (~30k games) is recommended before deploying to production (RESEARCH lines 467-471). The single-pass `phase IN (1, 2)` design scans roughly twice the rows vs the prior `phase = 1` scan, but keeps it as one query instead of two. The GROUP BY + JOIN shape avoids the Nested Loop hang risk. Flag if total query time > 1.5x the existing `/api/stats/most-played-openings` baseline.

## Known Stubs

None — all 15 `OpeningWDL` fields are populated from real query data.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced. The new SQL follows the same `user_id` + parameterized `IN(hashes)` pattern as `query_position_wdl_batch` (T-80-03, T-80-04 mitigated). No new STRIDE surface.

## Issues Encountered

- Test `test_no_asyncio_gather_in_stats_service` caught an unexpected issue: docstring lines (unlike comment lines starting with `#`) are not stripped by the source scanner, so negative examples in docstrings triggered the pattern. Fixed by rephrasing.
- Test 1 initially failed equality assertion (`eval_ci_low_pawns < avg_eval_pawns`) because all 12 games had identical eval_cp=30, giving zero variance and zero CI half-width. Fixed by using varied eval values.
- Service tests initially found no white openings passing the `MIN_PLY_WHITE=3` filter because the test was picking the King's Pawn Game (ply_count=1). Fixed by querying `openings_dedup` for openings with `ply_count >= 3` and odd ply_count.

## Next Phase Readiness

- Plan 03 (response model + router wiring) can now read all 15 new fields from `OpeningWDL` instances returned by `get_most_played_openings`
- Plan 05 (frontend rendering) has the data shape it needs: signed pawns, CI bounds, clock-diff pct + seconds, confidence buckets for both phases
- Pre-merge perf check on Adrian's account is the only outstanding manual step before deploy

---
*Phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns*
*Completed: 2026-05-03*
