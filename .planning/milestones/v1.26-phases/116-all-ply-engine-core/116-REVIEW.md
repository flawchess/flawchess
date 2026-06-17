---
phase: 116-all-ply-engine-core
reviewed: 2026-06-12T12:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - alembic/versions/20260612_120000_add_full_evals_completed_at.py
  - app/main.py
  - app/models/game_position.py
  - app/models/game.py
  - app/services/engine.py
  - app/services/eval_drain.py
  - tests/services/test_engine_nodes.py
  - tests/services/test_full_eval_drain.py
  - tests/test_migration_116_full_evals.py
findings:
  critical: 1
  warning: 8
  info: 6
  total: 15
status: issues_found
---

# Phase 116: Code Review Report

**Reviewed:** 2026-06-12T12:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the Phase 116 all-ply engine core: the `evaluate_nodes` 1M-node entry point, the `run_full_eval_drain` background coroutine, the `full_evals_completed_at` migration with in-migration backfill, model changes, and three test files. The drain's session discipline is correct (gather runs outside all session scopes, verified by reading and by the AST regression test), `ty check` passes, and the lifespan wiring/shutdown ordering in `app/main.py` is sound.

One critical defect: the D-116-06 "verified backfill" in the migration is a no-op against real data. Every imported game carries a terminal `game_positions` row that is hardcoded to `eval_cp=None, eval_mate=None` at import time (`app/services/zobrist.py:239-248`), so the backfill's `NOT EXISTS (... eval_cp IS NULL AND eval_mate IS NULL)` anti-join disqualifies every game with at least one move. The migration tests pass only because their synthetic fixtures omit the terminal row. Downstream, this compounds with a write-time-discard inefficiency (WR-01) into the full lichess-analyzed corpus being re-evaluated at 1M nodes for zero stored output.

Additionally, four of the nine files fail `ruff format --check`, which is the project's single most common preventable CI failure per CLAUDE.md.

## Critical Issues

### CR-01: Migration backfill marks zero games — terminal-position row always has NULL evals

**File:** `alembic/versions/20260612_120000_add_full_evals_completed_at.py:79-90`
**Issue:** The Step 4 backfill marks games where `NOT EXISTS (SELECT 1 FROM game_positions gp WHERE gp.game_id = g.id AND gp.eval_cp IS NULL AND gp.eval_mate IS NULL)`. But the import pipeline appends a final-position row for **every** game with `eval_cp=None, eval_mate=None` hardcoded (`app/services/zobrist.py:239-248`, `move_san=None`). Lichess `%eval` annotations never populate this row, and the full-ply drain itself deliberately never evaluates it (`_collect_full_ply_targets` excludes the terminal position). So the anti-join finds a NULL-eval row in every real game and the backfill marks **nothing** (except degenerate games with zero position rows, which it marks vacuously). The migration docstring even states the intended predicate — "every **non-terminal** ply already has eval_cp/eval_mate populated" — but the SQL has no non-terminal exclusion.

Consequences:
1. The EVAL-03 dedup source set is never seeded "from day one" as D-116-06 requires; dedup only starts paying off after the drain itself completes games.
2. Every fully-lichess-analyzed game (~the `is_analyzed` corpus) remains `full_evals_completed_at IS NULL` and will be picked by the drain, burning a full game's worth of 1M-node evals whose results are then all discarded at write time (see WR-01).
3. The EXPLAIN-verified "798ms on dev" claim measured a query that updates zero rows.

The migration tests (`tests/test_migration_116_full_evals.py:252-311`) did not catch this because they insert two synthetic position rows that both have evals and **no terminal row** — unrepresentative of every game the import pipeline produces. After fixing the SQL, those fixtures must gain a terminal NULL-eval row (with `move_san` populated on non-terminal rows) or they will mask regressions of the same shape.

**Fix:**
```sql
UPDATE games g
SET full_evals_completed_at = COALESCE(g.imported_at, NOW())
WHERE g.full_evals_completed_at IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM game_positions gp
      WHERE gp.game_id = g.id
        AND gp.move_san IS NOT NULL      -- exclude the terminal row (never evaluated by design)
        AND gp.eval_cp IS NULL
        AND gp.eval_mate IS NULL
  )
```
`move_san IS NOT NULL` is the existing per-row terminal marker (see `GamePosition.move_san` docstring). Note one residual caveat to verify against real lichess data before shipping: lichess typically emits no `%eval` on a game-ending mating move, so decisive analyzed games may still have a NULL at the last non-terminal ply and stay unmarked (conservative under-marking — the drain fills them — but it shrinks the seeded set; decide explicitly whether that is acceptable). Update both migration tests to include a terminal row so the fixture matches `process_game_pgn` output.

## Warnings

### WR-01: Drain evaluates plies whose results are deterministically discarded for `is_analyzed` games

**File:** `app/services/eval_drain.py:890-894, 925-934`
**Issue:** `engine_targets` excludes only dedup hits. For `is_analyzed=True` games, the write loop later drops every result for a ply whose row already has a non-NULL eval (D-116-04 preservation). The collector already loads each row's current `eval_cp`/`eval_mate` into the target tuple stream (`_collect_full_ply_targets` receives them and discards them as `_cp, _mt`), so the information needed to skip the engine call is in hand and thrown away. A fully analyzed lichess game gets ~60+ 1M-node evaluations (~1s each) computed and then 100% discarded. Combined with CR-01 (those games are never backfilled out of the queue), this is the dominant workload of the drain at launch producing zero written rows. This is a logic defect (work whose output is provably unused), not a perf-tuning nit.
**Fix:** When `is_analyzed` is true, exclude already-covered plies from `engine_targets` (and from the dedup candidate list), e.g. carry `eval_cp`/`eval_mate` on `_FullPlyEvalTarget` and filter `t.eval_cp is None and t.eval_mate is None` before the gather. Keep the write-time preservation check as a belt-and-braces guard.

### WR-02: Dedup transplants post-move lichess evals onto pre-move position hashes

**File:** `app/services/eval_drain.py:153-179, 911-912`
**Issue:** Per `app/services/zobrist.py:182` ("eval of position AFTER this move"), a lichess-sourced `eval_cp` at row ply *k* evaluates the position at ply *k+1*, while the row's `full_hash` is the position at ply *k* (pre-push). Engine-sourced evals (Phase 91 entry drain, this drain) instead evaluate the pre-push position at ply *k* — the two conventions already coexist within a game (pre-existing, not introduced here). What Phase 116 adds is **cross-game transplantation keyed by `full_hash`**: `_fetch_dedup_evals` returns rows from drain-completed `is_analyzed` games whose preserved values are lichess post-move evals. Copying such a value to another game's row with the same hash attaches the eval of "position after the *source game's* move" to a row whose game may have played a *different* move from that position. The error is usually small in the opening region, but it is a semantic mismatch that will skew flaw-delta computations around dedup'd plies, and it silently mixes conventions inside the target game.
**Fix:** Restrict the dedup source set to engine-written rows (position-keyed by construction). Simplest: for `is_analyzed` source games exclude preserved rows — e.g. add a join condition that the source game is `is_analyzed == False` (`Game.white_blunders.is_(None)`), or persist provenance. At minimum, document the accepted error explicitly in `_fetch_dedup_evals` if the team decides it is tolerable.

### WR-03: `ruff format --check` fails on 4 of 9 reviewed files

**File:** `app/services/eval_drain.py:890, 949-951`; `tests/services/test_engine_nodes.py`; `tests/services/test_full_eval_drain.py`; `tests/test_migration_116_full_evals.py`
**Issue:** `uv run ruff format --check` reports "Would reformat" for these four files (e.g. `eval_drain.py:890` exceeds line length; `949-951` over-wrapped). CLAUDE.md's pre-PR checklist mandates running the formatter before push and calls a CI "would reformat" failure "always avoidable locally". `ruff check` and `ty check` are clean.
**Fix:** Run `uv run ruff format app/ tests/` and commit with a `style(...)` prefix before integration.

### WR-04: `run_full_eval_drain` breaches the hard nesting limit (depth 6) and inlines the write stage

**File:** `app/services/eval_drain.py:824-944` (deepest at 925-934)
**Issue:** Inside the function body: `while` (1) → `try` (2) → `async with write_session` (3) → `for target` (4) → `if is_analyzed` (5) → `if original_row is not None and (...)` (6). CLAUDE.md sets nesting soft 3 / hard 4 inside any function body, and the ~120-line body mixes pick, load, dedup, gather, resolution, and write concerns. The sibling `run_eval_drain` keeps its write stage in helpers (`_apply_eval_results`, `_mark_evals_completed`); this function inlines the equivalent ~40-line write loop.
**Fix:** Extract Step 4 into an `_apply_full_eval_results(session, targets, dedup_map, engine_result_map, gp_rows, is_analyzed, game_id)`-style helper (mirroring `_apply_eval_results`), and hoist the per-ply resolution (`dedup vs engine vs hole`) into a small pure function. Both drops bring nesting back within limits and make the resolution priority unit-testable.

### WR-05: Per-ply Sentry messages + no circuit breaker — a dead engine pool floods Sentry and burns the backlog with NULL holes

**File:** `app/services/eval_drain.py:916-923, 942-943`
**Issue:** Each failed ply emits a `capture_message`. The entry-ply drain has the same pattern (D-09) but at ≤~3 targets/game; here it is one per non-terminal ply (~60-600/game). If the pool degrades to permanently-failed workers (restart failure path in `EnginePool._restart_worker` sets `_protocols[idx] = None`; every subsequent call returns `(None, None)` instantly), the drain will: emit hundreds of Sentry events per game, mark the game complete with all-NULL holes (D-116-07, no retry), and immediately pick the next game — converting a transient engine outage into permanent, silent loss of full-eval coverage across the entire backlog at maximum loop speed.
**Fix:** (a) Aggregate to one Sentry event per game with a `failed_ply_count` in context instead of per-ply messages. (b) Add a cheap circuit breaker: if **all** targets in a game returned `(None, None)`, do NOT set `full_evals_completed_at`; sleep and retry (an all-fail tick is overwhelmingly an engine problem, not a position problem). Per-position holes remain mark-and-continue per D-116-07.

### WR-06: `EnginePool.evaluate_nodes` duplicates `evaluate` wholesale, including the failure/restart path

**File:** `app/services/engine.py:342-401`
**Issue:** The two methods are byte-identical except for the `Limit` and timeout (the docstring says "Mirrors evaluate() exactly"). The duplicated portion includes the worker-acquisition, exception tuple, restart-on-failure, and slot-release logic — the exact code most likely to need a coordinated fix later (e.g. the FLAWCHESS-3Q era touched this area twice). A future patch to one copy that misses the other is a latent divergence bug, not just style.
**Fix:** Extract a private `async def _analyse(self, board, limit: chess.engine.Limit, timeout: float)` and make both public methods one-line wrappers: `return await self._analyse(board, chess.engine.Limit(depth=_DEPTH), _TIMEOUT_S)` / `Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S`.

### WR-07: Marker tests run the real drain loop against shared per-run DB state — ordering-dependent and mutate other tests' rows

**File:** `tests/services/test_full_eval_drain.py:389-400, 451-461`
**Issue:** `test_marker_set_after_drain` / `test_marker_set_with_holes` start the actual `run_full_eval_drain` loop for a fixed 3.0s wall-clock window against the worker's shared per-run database. Three reliability problems: (1) the Step 0 yield gate sleeps 5s whenever **any** game in the DB has `evals_completed_at IS NULL` — if a previously-run test in the same worker leaves such a row behind (committed, not cleaned), the gate blocks for the entire 3s window and the assertion fails: a classic ordering-dependent flake. (2) During the window the drain picks and processes **every** pending non-guest game in the DB LIFO, writing `full_evals_completed_at` (and mocked evals) onto rows owned by other tests' committed fixtures. (3) The two tests add ~6s of guaranteed wall-clock sleep per run (`wait_for` always times out by design).
**Fix:** Refactor the tick body of `run_full_eval_drain` into a `_full_drain_tick() -> bool` (processed-something flag) and have the loop call it; tests then call `_full_drain_tick()` directly — deterministic, scoped to one pick, no sleeps, and it also resolves the WR-04 extraction. If the loop must be exercised, gate the pick to the test's game_id via monkeypatch.

### WR-08: `ply <= 20` coupling invariant maintained by comments in three places

**File:** `app/models/game_position.py:103-107`; `alembic/versions/20260612_120000_add_full_evals_completed_at.py:68-74`; `app/services/eval_drain.py:89`
**Issue:** The dedup boundary appears as a literal `20` in the model's partial-index predicate, the migration, and as `_DEDUP_MAX_PLY` in the drain. If `_DEDUP_MAX_PLY` ever drifts above the index predicate, dedup lookups silently stop using `ix_gp_full_hash_opening` (the same failure mode the `MAX_EXPLORER_PLY` block in this very file documents and guards against by interpolating the constant into `text(f"ply <= {MAX_EXPLORER_PLY}")`). The new index does not follow the file's own established pattern.
**Fix:** Define `DEDUP_MAX_PLY: int = 20` next to `MAX_EXPLORER_PLY` in `app/models/game_position.py`, use `text(f"ply <= {DEDUP_MAX_PLY}")` in the index, and import it in `eval_drain.py` (`models` does not import `eval_drain`, so no cycle). The migration keeps its literal (migrations are frozen history).

## Info

### IN-01: Pick query selects `Game.user_id` but never reads it

**File:** `app/services/eval_drain.py:846, 861-863`
**Issue:** `row[3]` (`Game.user_id`) is selected and never consumed (`game_id`, `pgn_text`, `is_analyzed` are rows 0-2). Dead column in the SELECT.
**Fix:** Drop `Game.user_id` from the select (or use it — e.g. in the Sentry context at line 918, which currently omits it).

### IN-02: `.limit(1)` on a COUNT aggregate is dead code; use EXISTS for the gate

**File:** `app/services/eval_drain.py:197-199`
**Issue:** `select(func.count()).select_from(Game).where(...).limit(1)` — a count always returns exactly one row, so `limit(1)` does nothing, and the count itself scans every entry of the pending partial index rather than short-circuiting. Right after a large import (100k+ pending games) this counts the full backlog every 5s tick. The docstring's "sub-millisecond" claim holds only at steady state.
**Fix:** `await session.scalar(select(sa.exists().where(Game.evals_completed_at.is_(None))).select())` (and the same for the import-job check) for a true first-match short-circuit.

### IN-03: `from app.models.user import User` inside the drain loop body

**File:** `app/services/eval_drain.py:837`
**Issue:** The import executes on every loop iteration (cached, so harmless at runtime, but it is the only model imported mid-function while `Game`, `GamePosition`, `ImportJob` are module-level). No circular-import constraint forces this.
**Fix:** Move to the module-level import block.

### IN-04: Preservation check re-scans `gp_rows` linearly per target, duplicating a lookup the collector already builds

**File:** `app/services/eval_drain.py:929`
**Issue:** `next((r for r in gp_rows if r[0] == target.ply), None)` is an O(plies) scan inside the per-target loop, and it re-derives exactly the `ply_meta` dict that `_collect_full_ply_targets` already constructs and discards (line 135-137). Duplicated data-shaping, and the dataclass already has room to carry the original eval values.
**Fix:** Carry `orig_eval_cp` / `orig_eval_mate` on `_FullPlyEvalTarget` (or build one `{ply: (cp, mt)}` dict before the loop). This also feeds the WR-01 fix.

### IN-05: PGN parse failure is swallowed with no signal; unparseable games are marked complete with zero evals

**File:** `app/services/eval_drain.py:127-131, 942-943`
**Issue:** `_collect_full_ply_targets` returns `[]` on parse exception or `None` game; the tick then writes nothing and marks `full_evals_completed_at`. The game permanently exits the queue with zero coverage and no Sentry breadcrumb. The import-path equivalent (`process_game_pgn` in zobrist.py:157-160) does call `capture_exception` for the same condition; `_snapshot_boards` documents its no-Sentry choice — this function documents nothing.
**Fix:** Either capture once with `{"game_id": ...}` context, or document the silent-skip decision in the docstring as `_snapshot_boards` does.

### IN-06: Migration docstring carries an unfilled placeholder

**File:** `alembic/versions/20260612_120000_add_full_evals_completed_at.py:19`
**Issue:** `Revision ID: <autogenerated — see revision variable below>` — the placeholder was never replaced with `20260612120000`. Cosmetic, but it deviates from every sibling migration header.
**Fix:** Replace with the literal revision id.

---

_Reviewed: 2026-06-12T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
