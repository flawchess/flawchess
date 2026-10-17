---
id: SEED-201
status: closed. Resolved by quick 261017-986 (2026-10-17); the report's §3.3.3 "14/20" cap count is left as an owner flag.
planted: 2026-10-17
planted_during: Phase 241 execution (13 parallel executors in wave 4 exposed the DB collision; the rest surfaced in executor reports and the pytest output)
trigger_when: next time two worktrees or agents run pytest at the same time, or any test-infra / flake cleanup pass; item 1 is worth doing before the next parallel GSD phase
scope: small (one conftest change plus three mechanical fixes; a single quick task)
---

# SEED-201: Test-infra hardening found during Phase 241

Four independent follow-ups, all small. Item 1 is the one that matters.

## 1. Concurrent pytest sessions drop each other's test databases

**Observed:** with 13 executors in parallel worktrees, several `pytest -n 4` / `-n auto` runs failed in
fixture setup with `database "flawchess_test_gw0" does not exist`, asyncpg
`ConnectionDoesNotExistError` and "another operation is in progress". Every one passed on a serial
retry, so the failures were collisions, not test bugs.

**Cause (verified in code):** `tests/conftest.py` `_get_run_db_name()` (~line 88-114) names the
per-run DB after the xdist worker only (`flawchess_test_{PYTEST_XDIST_WORKER}`, e.g. `flawchess_test_gw0`),
not after the session. `_create_run_db()` (~line 243) starts with `DROP DATABASE IF EXISTS <run_db>`
as its stale-DB reaper. So a second `pytest -n auto` session (another worktree, another agent) drops
the first session's live `gw0..gwN` databases mid-run. Serial runs use the PID, so they are safe.

**Doc drift:** root `CLAUDE.md` ("Test isolation") says parallel runs are "fully isolated". That holds
within one session only.

**Fix direction:**
- Add a session-unique token to the xdist name. pytest-xdist sets `PYTEST_XDIST_TESTRUNUID` in every
  worker of one run (same value across workers, different per run). Keep the name a valid identifier
  within 63 chars (`_DB_NAME_RE` is `^[a-z_][a-z0-9_]{0,62}$`, so lowercase and truncate the uid).
- The DROP-before-CREATE reaper then no longer cleans killed runs (names are unique). Replace it with
  a sweep of `flawchess_test_%` DBs that have no connections and are older than some threshold,
  or drop the run DB in session teardown and sweep orphans under the existing advisory lock.
  Never drop `flawchess_test_template` in the sweep.
- Prove it: two concurrent `uv run pytest -n auto` from two worktrees, both green. Then correct the
  CLAUDE.md "Test isolation" paragraph.
- Related memory: serial CI does not catch this (CI never runs two sessions at once).

## 2. TrainStreakCard animation flake under load

`frontend/src/components/train/__tests__/TrainStreakCard.test.tsx`, test "streak up: the flame
ignites..." failed once in each of two executors (241-57, 241-59) during the heavy parallel wave,
and passed 24/24 when rerun alone. It fails on an animation-counter assertion, not a timeout, so it
is not the 2026-09-04 timeout flake (fixed project-wide in vite.config.ts + src/vitest.setup.ts; do
not add per-file timeouts). Likely a real-timer or rAF timing dependency; fake timers or awaiting the
animation end should make it deterministic. Reproduce under CPU contention before changing anything.

## 3. Pytest warnings that will turn into breakage

- `HTTP_422_UNPROCESSABLE_ENTITY` is deprecated in Starlette (installed 1.6.0); the replacement is
  `HTTP_422_UNPROCESSABLE_CONTENT`. 9 uses: `app/routers/eval_remote.py` (8) and
  `app/services/eval_apply.py` (1). Same status code, pure rename.
- `tests/scripts/test_opening_cache_repair.py` has module-level `pytestmark = pytest.mark.asyncio`
  (line 117) but `class TestConfirm` (line 1572) holds sync tests, producing 6 PytestWarnings
  ("marked with '@pytest.mark.asyncio' but it is not an async function"). Move the sync tests out
  from under the module mark or mark only the async classes.

## 4. Comment vs benchmark report mismatch (INV-L1012)

`frontend/src/components/charts/ScoreGapByTimePressureChart.tsx` ~line 63 says "all 20 (TC, quintile)
cells cap at ±0.06", but `reports/benchmark/benchmarks-latest.md` §3.3.3 recommendation (~line 619)
says "The cap activates at 14/20 cells (extreme quintiles)". Phase 241 (plan 43) fixed the source
pointer and left the claim alone as an owner flag. Check which is true against the report's table
(benchmarks are the source of truth for "typical"), then fix the comment, or re-run the §3.3.3
chapter if the report is the stale one. Do not touch `PRESSURE_SCORE_GAP_NEUTRAL_MIN/MAX` without
owner sign-off.
