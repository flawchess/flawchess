---
phase: 78-stockfish-eval-cutover-for-endgame-classification
plan: "03"
subsystem: scripts
tags: [backfill, script, stockfish, eval, idempotent, resumable, endgame, tdd]

requires:
  - phase: 78-02
    provides: app.services.engine (evaluate, start_engine, stop_engine)

provides:
  - scripts/backfill_eval.py (FILL-01/02/03 backfill executor)
  - tests/scripts/test_backfill_eval.py (Wave 0 idempotency + dry-run + resume tests)

affects:
  - 78-06 (cutover plan that executes this script in three rounds: dev → benchmark → prod)

tech-stack:
  added: []
  patterns:
    - "_session_maker test hook: inject pre-configured session maker for scripts that build their own DB engine"
    - "Committed-data test isolation: seed data via test_engine with explicit commit/teardown (vs rolled-back db_session)"
    - "COMMIT-every-100 resume pattern: WHERE NULL re-runs naturally pick up uncommitted rows"

key-files:
  created:
    - scripts/backfill_eval.py
    - tests/scripts/__init__.py
    - tests/scripts/test_backfill_eval.py
  modified: []

key-decisions:
  - "Row-level idempotency only (skip WHERE eval_cp IS NULL AND eval_mate IS NULL) — no cross-row hash dedup per D-10 and FILL-02 relaxed"
  - "_session_maker optional test hook added to run_backfill signature so Wave 0 tests can inject the test DB session maker without changing the public production API"
  - "Tests use committed data via test_engine (not rolled-back db_session) because run_backfill creates independent DB connections that cannot see unpublished transactions"
  - "start_engine/stop_engine mocked in all non-dry-run tests since Stockfish binary is absent on this dev machine"

patterns-established:
  - "BACKFILL_<TARGET>_DB_URL env override pattern for per-target DB credential customization"
  - "_log() UTC timestamp prefix — mirrors reclassify_positions.py pattern for operator-visible progress"

requirements-completed: [FILL-01, FILL-02, FILL-03]

duration: ~12min
completed: "2026-05-02"
---

# Phase 78 Plan 03: Backfill Script Summary

**Standalone asyncio CLI script (`scripts/backfill_eval.py`) that evaluates endgame span-entry rows via Stockfish depth-15, writes eval_cp/eval_mate back, commits every 100 rows, and resumes from NULL via the WHERE clause — tested with 5 Wave 0 tests covering dry-run, idempotency, lichess preservation, limit, and user filter.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-02T13:00:00Z
- **Completed:** 2026-05-02T13:11:46Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments

- Idempotent backfill script targeting dev/benchmark/prod via `--db` (required), with `--user-id`, `--dry-run`, `--limit` flags matching D-08
- Span-entry SELECT uses subquery to find MIN(ply) per (user_id, game_id, endgame_class) where COUNT(ply) >= ENDGAME_PLY_THRESHOLD, filtered by eval_cp IS NULL AND eval_mate IS NULL (row-level idempotency, FILL-02 relaxed)
- COMMIT-every-100 pattern (D-09) + VACUUM ANALYZE on completion + Sentry bounded context (T-78-13: no PGN/user_id in context)
- Wave 0 TDD tests pass (5/5): dry-run, idempotency, lichess preservation (FILL-04), limit, user filter

## Task Commits

1. **Task 1: Wave 0 tests (RED)** - `9064029` (test)
2. **Task 2: backfill_eval.py implementation (GREEN)** - `d4c8b4a` (feat)

## Files Created/Modified

- `scripts/backfill_eval.py` — 320-line idempotent/resumable backfill script with FILL-01/02/03 logic
- `tests/scripts/__init__.py` — package init
- `tests/scripts/test_backfill_eval.py` — 5 Wave 0 tests using committed-data isolation pattern

## Span-Entry SELECT Shape

```sql
-- Subquery: per (user_id, game_id, endgame_class), MIN(ply) where COUNT >= ENDGAME_PLY_THRESHOLD
WITH span_min AS (
    SELECT user_id, game_id, endgame_class, MIN(ply) as min_ply
    FROM game_positions
    WHERE endgame_class IS NOT NULL
    GROUP BY user_id, game_id, endgame_class
    HAVING COUNT(ply) >= 6
)
SELECT gp.id, gp.game_id, gp.ply, g.pgn
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
JOIN span_min sm ON (gp.user_id = sm.user_id AND gp.game_id = sm.game_id
                     AND gp.endgame_class = sm.endgame_class AND gp.ply = sm.min_ply)
WHERE gp.eval_cp IS NULL AND gp.eval_mate IS NULL
ORDER BY gp.game_id, gp.ply
[LIMIT N]
```

## Decisions Made

- **Row-level idempotency only**: No cross-row hash dedup per D-10/FILL-02. Endgame span entries are effectively unique across games; hash cache lookup costs more than re-evaluating rare collisions.
- **`_session_maker` test hook**: Added optional `_session_maker` kwarg to `run_backfill` so tests can inject the test DB without changing the public production signature. Production callers omit it; the script builds its own engine from `_db_url(db)`.
- **Committed-data test isolation**: Tests that call `run_backfill` (non-dry-run) must commit their seed data first, because the script creates independent DB connections that cannot see rolled-back transaction data.
- **DB URL derivation**: Settings has a single `DATABASE_URL` (not separate POSTGRES_USER/PASSWORD/DB fields). `_db_url()` parses the URL and replaces host:port with `localhost:<target-port>`. `BACKFILL_<TARGET>_DB_URL` env override available for non-default credentials.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `_session_maker` test hook to `run_backfill`**

- **Found during:** Task 2 (GREEN implementation)
- **Issue:** The plan's `run_backfill(db, user_id, dry_run, limit)` signature builds its own DB engine from `_db_url(db)`. Test data seeded via `db_session` (rolled-back transaction) is not visible to new independent connections. Without a test hook, all Wave 0 tests would fail because the script connects to the dev DB and finds 0 rows.
- **Fix:** Added `_session_maker: async_sessionmaker[AsyncSession] | None = None` as a keyword-only parameter. Production code path unchanged. Tests inject `_make_session_maker(test_engine)` and seed committed data with explicit commit/teardown.
- **Files modified:** `scripts/backfill_eval.py`, `tests/scripts/test_backfill_eval.py`
- **Committed in:** d4c8b4a (Task 2 commit)

**2. [Rule 3 - Blocking] Used `settings.DATABASE_URL` URL-parsing instead of missing POSTGRES_* fields**

- **Found during:** Task 2 (GREEN implementation)
- **Issue:** Plan template referenced `settings.POSTGRES_USER`, `settings.POSTGRES_PASSWORD`, `settings.POSTGRES_DB` which do not exist in `app/core/config.py`. The settings only exposes `DATABASE_URL`.
- **Fix:** `_db_url()` uses `urlparse(settings.DATABASE_URL)` to extract user/password/dbname, replaces only the host:port for each target.
- **Files modified:** `scripts/backfill_eval.py`
- **Committed in:** d4c8b4a (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 blocking issue)
**Impact on plan:** Both fixes required for testability and correctness. No scope creep.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED  | 9064029 | `test(78-03): add failing Wave 0 backfill script tests (RED)` |
| GREEN | d4c8b4a | `feat(78-03): implement backfill_eval.py script (FILL-01/02/03 GREEN)` |

## Issues Encountered

None beyond the deviations documented above.

## Known Stubs

None. This plan creates a standalone CLI script with no UI or data-rendering paths.

## Threat Coverage

| Threat | Mitigation | Where |
|--------|-----------|-------|
| T-78-11 (lichess overwrite) | WHERE eval_cp IS NULL AND eval_mate IS NULL; TestLichessPreservation asserts -42 unchanged | backfill_eval.py:173-174, test:178-209 |
| T-78-12 (wrong DB target) | `--db` REQUIRED, explicit choices; _log() echoes db=target on every commit | backfill_eval.py:353-360, _log calls |
| T-78-13 (Sentry PGN leak) | sentry context: game_position_id, game_id, ply, db_target — NO PGN, NO user_id | backfill_eval.py:262-275 |
| T-78-14 (wedged engine DoS) | Wrapper's 2s timeout bounds per-eval wall-clock; script skips on (None, None) | engine.py handles; backfill_eval.py:258-276 |
| T-78-15 (prod tunnel drop) | COMMIT-every-100; resume via SELECT NULL re-run | backfill_eval.py:58, 289-295 |
| T-78-16 (no audit log) | Accepted; _log() at COMMIT boundaries with row counts | backfill_eval.py:297-303 |

## Next Phase Readiness

- `scripts/backfill_eval.py` is ready for use in Plan 78-06 three-round cutover (dev → benchmark → prod)
- Wave 0 gate tests pass, confirming idempotency and dry-run behavior
- VAL-01 gate (benchmark backfill + `/conv-recov-validation` re-run) is the hard gate before prod round

## Self-Check: PASSED

| Item | Status |
|------|--------|
| scripts/backfill_eval.py | FOUND |
| tests/scripts/__init__.py | FOUND |
| tests/scripts/test_backfill_eval.py | FOUND |
| commit 9064029 (RED) | FOUND |
| commit d4c8b4a (GREEN) | FOUND |
