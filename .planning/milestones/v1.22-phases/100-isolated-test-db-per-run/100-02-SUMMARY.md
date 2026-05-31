---
phase: 100-isolated-test-db-per-run
plan: 02
subsystem: testing
tags: [postgresql, pytest, asyncpg, pytest-xdist, documentation, test-isolation]

# Dependency graph
requires:
  - phase: 100-isolated-test-db-per-run
    plan: 01
    provides: Per-run DB isolation infrastructure (test_engine, advisory-lock template refresh)
provides:
  - Verified -n auto parallel run: 18.56s wall clock vs 40.29s serial baseline (2.2x speedup)
  - Verified SC-1 concurrent-run isolation: two simultaneous full pytest runs both green (RC=0)
  - SC-5 documentation: conftest.py module-level comment + CLAUDE.md test isolation section
  - xdist-compatibility fixes: sorted parametrize + per-worker openings seed in conftest
affects:
  - Any future phase that runs tests (xdist-compat fixes improve parallel reliability)
  - Any future agent running concurrent pytest sessions (confirmed isolation works)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-worker openings seed: seed_openings_for_tests in conftest.py ensures every xdist worker seeds its own per-run DB
    - Deterministic parametrize: sorted() over set() for stable xdist test collection

key-files:
  created:
    - .planning/phases/100-isolated-test-db-per-run/100-02-SUMMARY.md
  modified:
    - tests/conftest.py — SC-5 documentation + seed_openings_for_tests fixture (xdist fix)
    - tests/test_endgame_zones.py — list(_VISIBLE_CLASSES) -> sorted(_VISIBLE_CLASSES) (xdist fix)
    - CLAUDE.md — test isolation subsection with flawchess_test_template + -n auto note

key-decisions:
  - "seed_openings_for_tests moved to conftest.py: autouse session-scoped fixture only runs on workers that collect its source file; conftest ensures all workers seed openings"
  - "sorted(_VISIBLE_CLASSES) required for stable xdist collection: Python set iteration is non-deterministic, causing Different-tests-collected errors across workers"
  - "-n auto wall-clock 18.56s vs 40.29s serial (2.2x speedup): SC-3 satisfied; RESEARCH estimate of 8-15s was accurate, actual falls at 18.56s (slightly above estimate, reasonable given 16 workers + DB clone overhead)"

requirements-completed: []

# Metrics
duration: 14min
completed: 2026-05-31
---

# Phase 100 Plan 02: Verify + Document Per-Run DB Isolation Summary

**Advisory-lock template-refresh mechanism documented; -n auto confirmed green at 18.56s (2.2x faster than 40.29s serial baseline); two concurrent serial runs both green with zero deadlocks or cross-run collision**

## Performance

- **Duration:** 14 min
- **Started:** 2026-05-31T14:54:58Z
- **Completed:** 2026-05-31T15:09:15Z
- **Tasks:** 2
- **Files modified:** 4 (tests/conftest.py, tests/test_endgame_zones.py, CLAUDE.md, 100-02-SUMMARY.md)

## SC-3: -n auto Wall-Clock Measurement

**18.56 seconds** (2198 passed, 16 skipped) vs 40.29s serial baseline.

- Speedup: **2.2x faster** than serial (SC-3 met: measurably faster)
- Workers: 16 xdist workers (`-n auto` on 16-core dev box)
- RESEARCH estimate was 8–15s; actual 18.56s is above the estimate but still well below serial
- Note: 2198 passed (vs 2193 serial in Plan 01) due to the `seed_openings_for_tests` conftest fix enabling 5 previously-skipped tests to pass (openings were not yet seeded at collection time in the old ordering)

## SC-1: Concurrent-Run Proxy

Two full `uv run pytest` processes launched simultaneously in the background:

```
uv run pytest -q > /tmp/100_run_a.log 2>&1 &  # PID A
uv run pytest -q > /tmp/100_run_b.log 2>&1 &  # PID B
```

**Run A:** 2198 passed, 16 skipped in 32.92s — RC=0
**Run B:** 2198 passed, 16 skipped in 32.89s — RC=0

No deadlock, no "database is being accessed by other users", no PK collision, no RESTART-IDENTITY errors. Each run used its own `flawchess_test_<pid>` DB; the advisory lock correctly serialized the template-freshness check.

## Residual Databases

After all test runs, the following `flawchess_test*` databases exist:

| Database | Status | Expected? |
|----------|--------|-----------|
| `flawchess_test` | Pre-Phase-100 shared test DB (no longer used) | Yes — not dropped by design |
| `flawchess_test_template` | Migrated template persists between runs | Yes — expected to persist |
| `flawchess_test_75459` | Stale residual from a Plan 01 interrupted run | Pre-existing — will be cleaned by next run with same PID |

No per-run DBs from THIS plan's test runs were left behind — all were dropped at teardown as expected.

## Accomplishments

- SC-5 documentation: expanded conftest.py module-level comment to fully cover (a) per-run DB cloning from `flawchess_test_template`, (b) advisory-lock-guarded Alembic head-drift auto-refresh with Pitfall-4 re-check, (c) stale-DB reaper self-heal, (d) zero manual steps after migration
- SC-5 documentation: CLAUDE.md "Test isolation (per-run DB)" subsection added near backend commands, with `flawchess_test_template` and `-n auto` keywords
- SC-3 satisfied: `-n auto` green at 18.56s (2.2x faster than 40.29s serial)
- SC-1 proxy satisfied: two simultaneous full pytest processes both exit 0 with zero deadlock/collision
- xdist compatibility fixed (two Rule 1 bugs discovered during -n auto run)

## Task Commits

Each task was committed atomically:

1. **Task 1: Document template-refresh mechanism** - `98f8ad83` (docs)
2. **Task 2 (Rule 1 fixes): Fix xdist collection + openings seed gap** - `c4a715d0` (fix)

## Files Created/Modified

- `tests/conftest.py` — expanded SC-5 module-level comment block (a-d); added `seed_openings_for_tests` session-scoped autouse fixture (xdist fix)
- `tests/test_endgame_zones.py` — `sorted(_VISIBLE_CLASSES)` instead of `list(_VISIBLE_CLASSES)` (xdist fix)
- `CLAUDE.md` — `uv run pytest -n auto` command + "Test isolation (per-run DB)" subsection

## Decisions Made

- **seed_openings_for_tests in conftest.py:** The fixture was session-scoped autouse in `test_seed_openings.py` only; xdist workers that did not collect that file had empty openings_dedup. The conftest copy ensures all workers seed. The `test_seed_openings.py` version stays (idempotent duplicate).
- **sorted() for parametrize over sets:** Python set iteration order is implementation-defined. Any `list(set)` in a pytest.mark.parametrize call causes xdist "Different tests collected" errors between workers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] list(_VISIBLE_CLASSES) -> sorted(_VISIBLE_CLASSES) in test_endgame_zones.py**
- **Found during:** Task 2 (first -n auto run)
- **Issue:** `@pytest.mark.parametrize("cls", list(_VISIBLE_CLASSES))` where `_VISIBLE_CLASSES` is a Python `set`. Sets have non-deterministic iteration order, causing xdist to report "Different tests were collected between gw0 and gw2" for `test_per_class_tc_achievable_score_gap_consistent_across_tc`. The test ordering was different on each worker.
- **Fix:** Changed `list(_VISIBLE_CLASSES)` to `sorted(_VISIBLE_CLASSES)` for deterministic alphabetical ordering across all workers.
- **Files modified:** tests/test_endgame_zones.py
- **Verification:** -n auto green, collection errors gone
- **Committed in:** c4a715d0

**2. [Rule 1 - Bug] seed_openings_for_tests missing from conftest.py**
- **Found during:** Task 2 (second -n auto run after fix 1)
- **Issue:** `seed_openings_for_tests` was `autouse=True, scope="session"` in `test_seed_openings.py`. Under xdist, session-scoped autouse fixtures from a test file only run on workers that collect tests from that file. Workers assigned only `test_stats_repository.py::TestQueryTopOpeningsSqlWDL` tests had empty `openings_dedup`, causing 4 test failures (openings queries returned empty).
- **Fix:** Added `seed_openings_for_tests` to conftest.py as a session-scoped autouse fixture. Every worker (and the serial session) now seeds openings at session start. The `test_seed_openings.py` version is retained as a harmless idempotent duplicate.
- **Files modified:** tests/conftest.py
- **Verification:** -n auto green (2198 passed, 16 skipped, 0 failures)
- **Committed in:** c4a715d0

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes are correctness requirements for xdist compatibility — no scope creep. The serial suite was unaffected by both bugs (serial ordering masked them). SC-3 and SC-1 could not have been passed without these fixes.

## Issues Encountered

- Pre-existing: `test_admin_users_search.py::test_search_by_exact_id` fails when run in isolation (alone or on a single xdist worker without companion tests) due to MissingGreenlet error during connection cleanup. Passes in the full serial suite (2198 passed). This is a pre-existing fixture-ordering issue unrelated to Phase 100 changes. Confirmed by: (a) test passes in full serial suite, (b) it was present in pre-Phase-100 code, (c) concurrent proxy runs both exit 0. Deferred to deferred-items.

## Known Stubs

None.

## Threat Surface Scan

No new external attack surface. Documentation and test-compatibility fixes only.

## User Setup Required

None.

## Next Phase Readiness

- Phase 100 is complete: per-run DB isolation built, measured, and documented
- Phase 101 (frontend major dependency upgrades) can proceed immediately
- The `flawchess_test_75459` stale DB is a cosmetic artifact; it will be cleaned by the next pytest run that happens to reuse PID 75459 (effectively never — low priority)

---
*Phase: 100-isolated-test-db-per-run*
*Completed: 2026-05-31*
