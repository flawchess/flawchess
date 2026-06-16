---
phase: 116-all-ply-engine-core
plan: "01"
subsystem: database
tags: [stockfish, engine, alembic, migration, postgresql, eval-drain, python-chess]

# Dependency graph
requires:
  - phase: 91-eval-drain
    provides: "evals_completed_at pattern, ix_games_evals_pending, EnginePool, eval_drain.py session discipline"
  - phase: 116-all-ply-engine-core
    provides: "116-CONTEXT.md locked decisions D-116-01..D-116-13, 116-RESEARCH.md patterns"

provides:
  - "evaluate_nodes() at module + EnginePool level — 1M-node Limit, 5.0s timeout (EVAL-02)"
  - "games.full_evals_completed_at nullable TIMESTAMPTZ column (EVAL-05 / D-116-05)"
  - "ix_games_full_evals_pending partial index ON games(id) WHERE NULL (migration-only)"
  - "ix_gp_full_hash_opening cross-user index ON game_positions(full_hash) WHERE ply<=20 (EVAL-03)"
  - "Alembic migration 20260612120000 with verified D-116-06 backfill"
  - "Wave-0 test scaffolds: tests/services/test_engine_nodes.py, tests/test_migration_116_full_evals.py"

affects: [116-02-full-eval-drain, 116-03-memory-docs, 117-eval-queue]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "evaluate_nodes() mirrors evaluate() exactly — same pool, same _score_to_cp_mate, only Limit + timeout differ"
    - "No multipv in Phase 116 engine calls — scalar InfoDict returned directly (PV capture deferred EVAL-04/Phase 117)"
    - "Cross-file xdist isolation: real-engine tests call start_engine() directly instead of relying on session-scoped engine_started fixture"
    - "Migration-only index pattern: ix_games_full_evals_pending follows ix_games_evals_pending convention (not in __table_args__)"

key-files:
  created:
    - alembic/versions/20260612_120000_add_full_evals_completed_at.py
    - tests/services/test_engine_nodes.py
    - tests/test_migration_116_full_evals.py
  modified:
    - app/services/engine.py
    - app/models/game.py
    - app/models/game_position.py

key-decisions:
  - "_NODES_TIMEOUT_S=5.0 chosen as ~4x prod p90 (1.277s from spike 002); _TIMEOUT_S=2.0 would timeout ~50% of 1M-node calls"
  - "In-migration backfill confirmed safe: EXPLAIN ANALYZE on dev (185k games, 14M positions) shows 798ms via nested loop anti-join on ix_game_positions_game_id — no full table scan; estimated ~2.6s on prod"
  - "ix_games_full_evals_pending is migration-only (not in Game.__table_args__), matching ix_games_evals_pending pattern (Critical Constraint 5)"
  - "ix_gp_full_hash_opening has no user_id column — cross-user dedup lookup by design (D-116-02)"
  - "Real-engine tests use start_engine() directly for xdist resilience (session-scoped engine_started fixture vulnerable to stop_engine() from other test files in same worker)"

patterns-established:
  - "evaluate_nodes() / EnginePool.evaluate_nodes(): new constants (_NODES_BUDGET, _NODES_TIMEOUT_S) + new functions mirroring depth-15 path; ENG-03 UCI centralization preserved"
  - "Backfill path decision: run EXPLAIN (ANALYZE, BUFFERS) on dev DB before committing to in-migration vs post-deploy script"

requirements-completed: [EVAL-02, EVAL-05, EVAL-03]

# Metrics
duration: 16min
completed: 2026-06-12
---

# Phase 116 Plan 01: All-Ply Engine Core Foundation Summary

**evaluate_nodes() at 1M-node Lichess-parity budget (EVAL-02), full_evals_completed_at marker column + two partial indexes (EVAL-05, EVAL-03), and a verified in-migration backfill seeding the dedup source set from day one (D-116-06)**

## Performance

- **Duration:** 16 min
- **Started:** 2026-06-12T17:47:43Z
- **Completed:** 2026-06-12T18:04:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `evaluate_nodes()` (module-level + `EnginePool` method) using `chess.engine.Limit(nodes=1_000_000)` and `_NODES_TIMEOUT_S=5.0s`; no multipv; scalar `InfoDict` via existing `_score_to_cp_mate()` unchanged
- Added `games.full_evals_completed_at` TIMESTAMPTZ column, `ix_games_full_evals_pending` partial index (migration-only), and `ix_gp_full_hash_opening` cross-user dedup index on `game_positions`
- Alembic migration with verified D-116-06 backfill confirmed safe via `EXPLAIN (ANALYZE, BUFFERS)`: 798ms on dev (nested loop anti-join on `ix_game_positions_game_id`, no full scan), estimated ~2.6s on prod
- Wave-0 test scaffolds pass: mock-based `Limit(nodes=...)` contract tests, pool-unset tests, and 4 migration tests (column/index presence + backfill coverage/skip semantics)

## Task Commits

1. **Task 1: evaluate_nodes() + Wave-0 test scaffold** — `597595b9` (feat)
2. **Task 2: Model column + dedup index** — `fd10a0fa` (feat)
3. **Task 3: Migration + backfill + migration test** — `0f1ce95e` (feat)
4. **[Rule 1] xdist isolation fix** — `f133f271` (fix)

## Backfill EXPLAIN Result

```
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
UPDATE games g SET full_evals_completed_at = ...
WHERE g.full_evals_completed_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM game_positions gp WHERE gp.game_id = g.id
                  AND gp.eval_cp IS NULL AND gp.eval_mate IS NULL)

Plan: Gather → Parallel Index Only Scan on uq_games_id_user_id + Nested Loop Anti Join
      → Index Scan on ix_game_positions_game_id
Dev execution time: 798ms (185k games, 14M game_positions)
Prod estimate: ~2.6s (600k games, ~30M positions, proportional scaling)
Decision: IN-MIGRATION backfill. No full table scan; cost acceptable.
```

## Files Created/Modified

- `app/services/engine.py` — Added `_NODES_BUDGET=1_000_000`, `_NODES_TIMEOUT_S=5.0`, module-level `evaluate_nodes()`, `EnginePool.evaluate_nodes()`
- `app/models/game.py` — Added `full_evals_completed_at` column with comment citing EVAL-05/D-116-05
- `app/models/game_position.py` — Added `ix_gp_full_hash_opening` index to `__table_args__`
- `alembic/versions/20260612_120000_add_full_evals_completed_at.py` — New migration (down_revision=07994baf3b15)
- `tests/services/test_engine_nodes.py` — Wave-0 EVAL-02 test scaffold (mock + pool-unset + real-engine)
- `tests/test_migration_116_full_evals.py` — Wave-0 EVAL-05 migration test (column/index + backfill coverage)

## Decisions Made

- `_NODES_TIMEOUT_S=5.0`: ~4x prod p90 (1.277s, spike 002). Current `_TIMEOUT_S=2.0` would timeout ~50% of 1M-node calls.
- In-migration backfill: EXPLAIN confirmed 798ms on dev via indexed nested loop (NOT a full table scan). Safe to run on prod startup.
- Migration-only index for `ix_games_full_evals_pending`: follows `ix_games_evals_pending` convention (Critical Constraint 5). No `__table_args__` entry.
- Cross-user `ix_gp_full_hash_opening`: no `user_id` column by design (D-116-02 marker-gated cross-user dedup).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed xdist test isolation for TestEvaluateNodesRealEngine**
- **Found during:** Full suite run (`uv run pytest -n auto -x`)
- **Issue:** `TestEngineNotStarted::test_evaluate_returns_none_tuple_if_engine_not_started` in `test_engine.py` calls `stop_engine()`, which destroys the module-level pool for all subsequent tests in the same xdist worker session. `TestEvaluateNodesRealEngine` ran after this and got `(None, None)` for every call.
- **Fix:** Changed `TestEvaluateNodesRealEngine` to call `start_engine()` directly before each test (idempotent, restarts if stopped). Changed `TestEvaluateNodesPoolUnset` to use `patch.object(engine_module, "_pool", None)` instead of `stop_engine()` to avoid destroying the session engine state.
- **Files modified:** `tests/services/test_engine_nodes.py`
- **Verification:** `uv run pytest -n auto -x` passes (2533 passed, 10 skipped)
- **Committed in:** `f133f271`

---

**Total deviations:** 1 auto-fixed (Rule 1 - test isolation bug)
**Impact on plan:** Necessary fix for CI reliability. No scope creep.

## Issues Encountered

None beyond the xdist test isolation bug documented in Deviations above.

## Known Stubs

None. This plan creates infrastructure (engine API, schema, migration) — no UI or data rendering involved.

## Threat Flags

No new threat surface beyond the items already in the plan's `<threat_model>`:
- T-116-01 (backfill cost) — mitigated: EXPLAIN confirmed safe, in-migration path chosen.
- T-116-02 (migration chaining) — mitigated: down_revision=07994baf3b15, single head verified.
- T-116-03 (cross-user index) — accepted: index on Zobrist integer (no PII), server-side drain only.

## Next Phase Readiness

Plan 02 (full-eval drain coroutine) can now build on:
- `evaluate_nodes()` contract (EVAL-02)
- `full_evals_completed_at` column + `ix_games_full_evals_pending` for the LIFO pick
- `ix_gp_full_hash_opening` for the opening-region dedup batch lookup
- `Game.full_evals_completed_at` column for marker-gate join in dedup query (D-116-02)

---
*Phase: 116-all-ply-engine-core*
*Completed: 2026-06-12*

## Self-Check: PASSED

Files verified present:
- app/services/engine.py: FOUND
- app/models/game.py: FOUND
- app/models/game_position.py: FOUND
- alembic/versions/20260612_120000_add_full_evals_completed_at.py: FOUND
- tests/services/test_engine_nodes.py: FOUND
- tests/test_migration_116_full_evals.py: FOUND

Commits verified:
- 597595b9: feat(116-01): evaluate_nodes() — FOUND
- fd10a0fa: feat(116-01): model column + dedup index — FOUND
- 0f1ce95e: feat(116-01): migration + backfill + test — FOUND
- f133f271: fix(116-01): xdist isolation — FOUND
