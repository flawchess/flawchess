---
phase: 78
plan: 03
type: execute
wave: 2
depends_on: [78-02]
files_modified:
  - scripts/backfill_eval.py
  - tests/scripts/test_backfill_eval.py
autonomous: true
requirements: [FILL-01, FILL-02, FILL-03]
tags: [backfill, script, scripts, idempotent, resumable, fill-02-drift]

must_haves:
  truths:
    - "Backfill identifies endgame span-entry rows with `eval_cp IS NULL AND eval_mate IS NULL` and replays SAN to the entry ply, evaluates via the shared wrapper, and writes back (FILL-01)."
    - "**FILL-02 hash-dedup is intentionally relaxed per CONTEXT.md D-10: row-level idempotency only (skip rows where `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`). Cross-row hash cache lookup costs more than re-evaluating the rare collision; endgame span entries are effectively unique across games. Plan-checker should NOT BLOCKER on the missing hash dedup — this drift is locked.**"
    - "Re-running the script over a populated dataset performs zero engine calls (idempotency by row-level NULL check)."
    - "Mid-run kill leaves committed work intact; resume picks up from the next NULL-eval span-entry row (COMMIT every 100 evals per D-09)."
    - "CLI shape per D-08: `--db {dev|benchmark|prod}`, `--user-id <int>` (optional), `--dry-run`, `--limit <int>`. DB target is REQUIRED; default user filter is all users."
    - "Engine is started once at script entry (`start_engine()` from `app.services.engine`), stopped on exit. Standalone asyncio script, NOT a FastAPI app."
    - "All DB writes are sequential within the same `AsyncSession`; no `asyncio.gather` (CLAUDE.md hard constraint)."
    - "FILL-03 sequencing: this plan delivers the script. Plan 78-06 executes it in three rounds (dev → benchmark → prod) with VAL-01 as a hard gate between benchmark and prod."
  artifacts:
    - path: "scripts/backfill_eval.py"
      provides: "FILL-01/02/03 backfill executor (SAN replay + engine.evaluate + COMMIT-100)"
      min_lines: 200
    - path: "tests/scripts/test_backfill_eval.py"
      provides: "Idempotency + dry-run + resume tests on tiny seeded fixture"
      min_lines: 80
  key_links:
    - from: "scripts/backfill_eval.py"
      to: "app/services/engine.py (evaluate, start_engine, stop_engine)"
      via: "import"
      pattern: "from app.services.engine import"
    - from: "scripts/backfill_eval.py"
      to: "GamePosition table (UPDATE)"
      via: "sa.update(GamePosition).where(id=...).values(eval_cp=..., eval_mate=...)"
      pattern: "update\\(GamePosition\\)"
---

<objective>
Implement `scripts/backfill_eval.py` — the standalone asyncio CLI script that walks endgame span-entry rows where both `eval_cp` and `eval_mate` are NULL, replays SAN from the game's PGN to the entry ply, evaluates via `app.services.engine.evaluate()`, and writes results back. Targets dev / benchmark / prod via `--db` flag (D-07/D-08). Provides Wave 0 idempotency + resume tests on a tiny seeded fixture.

Purpose: FILL-01, FILL-02 (relaxed per D-10), FILL-03. The script is the operator's tool for the three-round cutover ordering in Plan 78-06: dev → benchmark → prod. Without this script, the prod backfill cannot happen before the deploy and there is a broken-classification window post-deploy.

Output: Idempotent, resumable, dry-run-capable backfill script under `scripts/`, plus a small Wave 0 test suite proving idempotency and dry-run behavior.

**FILL-02 SPEC drift acknowledgement (REQUIRED for plan-checker):** SPEC.md FILL-02 says "dedupes evaluations by `full_hash` so identical positions are not re-evaluated." This is intentionally relaxed per CONTEXT.md D-10 — row-level idempotency only (skip rows where `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`). Endgame span-entry positions are effectively unique across games (each game arrives at its endgame through a distinct path), so cross-row cache hits are astronomically rare and the dedup lookup costs more than re-evaluating. Plan-checker should NOT flag this as a BLOCKER — the drift is locked.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-02-engine-wrapper-PLAN.md
@CLAUDE.md
@scripts/reclassify_positions.py
@app/repositories/endgame_repository.py

<interfaces>
<!-- Wrapper API from Plan 78-02 (already shipped in Wave 1) -->
```python
from app.services.engine import start_engine, stop_engine, evaluate
# evaluate(board: chess.Board) -> tuple[int | None, int | None]
# Returns (None, None) on engine timeout/crash (engine self-restarts).
```

<!-- DB session pattern from app/core/database (existing) -->
```python
from app.core.database import async_session_maker, engine
# async_session_maker is a sessionmaker bound to the default DB. For per-target
# DB selection, build a fresh engine + sessionmaker from the URL chosen via --db.
```

<!-- ENDGAME_PLY_THRESHOLD constant — existing in app/repositories/endgame_repository.py -->
```python
# app/repositories/endgame_repository.py defines the threshold; reuse, do not redeclare.
ENDGAME_PLY_THRESHOLD = 6  # confirmed in code; verify via grep before locking
```

<!-- Span-entry SQL pattern (RESEARCH.md "Span-Entry Row Definition") -->
```sql
SELECT gp.id, gp.game_id, gp.ply, g.pgn
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.eval_cp IS NULL
  AND gp.eval_mate IS NULL
  AND gp.endgame_class IS NOT NULL
  AND gp.ply = (
      SELECT MIN(inner_gp.ply)
      FROM game_positions inner_gp
      WHERE inner_gp.game_id = gp.game_id
        AND inner_gp.endgame_class = gp.endgame_class
        AND inner_gp.user_id = gp.user_id
      GROUP BY inner_gp.game_id, inner_gp.endgame_class
      HAVING COUNT(inner_gp.ply) >= ENDGAME_PLY_THRESHOLD
  )
ORDER BY gp.game_id, gp.ply
```

<!-- SAN replay helper (mirrors scripts/reclassify_positions.py:136-176) -->
```python
def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
    """Replay PGN to target_ply (0-indexed, pre-push). Returns board BEFORE the move at that ply."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None
    if game is None:
        return None
    board = game.board()
    for i, node in enumerate(game.mainline()):
        if i == target_ply:
            return board
        board.push(node.move)
    return board  # ply == final position
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave 0 — backfill script idempotency + dry-run + resume tests</name>
  <files>tests/scripts/test_backfill_eval.py</files>
  <read_first>
    - tests/conftest.py (existing DB fixtures — `db_session`, `seed_user`, `seed_game`, etc.; reuse don't redefine)
    - tests/test_endgame_repository.py:_seed_game_position helper (lines 95-128)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md "Wave 0 Requirements"
    - scripts/reclassify_positions.py (CLI / batch shape to mirror)
  </read_first>
  <behavior>
    - Test 1 (dry-run): seed 3 span-entry rows with NULL eval; running with `--dry-run` prints a count of 3 and writes nothing (rows still have NULL eval_cp / eval_mate).
    - Test 2 (idempotency): seed 3 span-entry rows; first run populates them; second run performs zero engine calls (mock evaluate to count invocations).
    - Test 3 (resume): seed 6 span-entry rows; mock evaluate to crash after 3 invocations; first run commits 3, second run completes the remaining 3.
    - Test 4 (NULL preservation for lichess rows): seed 1 span-entry row with `eval_cp = -42` (lichess-populated); running the script does NOT update that row (FILL-04 invariant: lichess values byte-for-byte unchanged).
    - Test 5 (--limit): seed 5 span-entry rows; `--limit 2` evaluates only 2.
    - Test 6 (--user-id): seed rows for user A and user B; `--user-id <A>` only affects user A's rows.
  </behavior>
  <action>
    Create `tests/scripts/__init__.py` empty file. Create `tests/scripts/test_backfill_eval.py` with the test scenarios above. Use a mock for `app.services.engine.evaluate` so tests do not depend on Stockfish presence and run fast.

    Test skeleton (executor MUST adapt to existing fixture names in `tests/conftest.py`):

    ```python
    """Backfill script tests (FILL-01, FILL-02 relaxed). Phase 78 Wave 0."""
    from __future__ import annotations

    from unittest.mock import AsyncMock, patch

    import pytest

    # Public API of the script — the executor exposes a callable `run_backfill`
    # for testability. CLI is parsed in main(); run_backfill takes parsed args.
    from scripts.backfill_eval import run_backfill


    pytestmark = pytest.mark.asyncio


    async def _seed_span_entry_row(session, *, user, game, ply, eval_cp=None, eval_mate=None,
                                    endgame_class=1, ply_count=6):
        """Seed a span-entry row plus enough sibling rows to satisfy ENDGAME_PLY_THRESHOLD.

        Reuses existing _seed_game_position from tests.test_endgame_repository if available;
        otherwise inline GamePosition() construction.
        """
        ...  # executor uses existing fixture / helper


    class TestDryRun:
        async def test_dry_run_writes_nothing(self, db_session, seeded_user, seeded_game):
            for ply in (10, 11, 12, 13, 14, 15):  # 6 plies → satisfies threshold; ply 10 = span entry
                await _seed_span_entry_row(db_session, user=seeded_user, game=seeded_game, ply=ply)
            with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(150, None))) as mock_eval:
                await run_backfill(db="dev", user_id=None, dry_run=True, limit=None)
            assert mock_eval.call_count == 0
            # All rows still NULL
            ...


    class TestIdempotency:
        async def test_second_run_zero_engine_calls(self, db_session, seeded_user, seeded_game):
            for ply in (10, 11, 12, 13, 14, 15):
                await _seed_span_entry_row(db_session, user=seeded_user, game=seeded_game, ply=ply)
            with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(150, None))) as mock_eval:
                await run_backfill(db="dev", user_id=None, dry_run=False, limit=None)
                first_call_count = mock_eval.call_count
                assert first_call_count == 1  # only ply=10 is the span entry

                mock_eval.reset_mock()
                await run_backfill(db="dev", user_id=None, dry_run=False, limit=None)
                assert mock_eval.call_count == 0  # idempotent: nothing left to do


    class TestLichessPreservation:
        async def test_lichess_eval_not_overwritten(self, db_session, seeded_user, seeded_game):
            for ply in (10, 11, 12, 13, 14, 15):
                eval_cp = -42 if ply == 10 else None  # span entry has lichess eval
                await _seed_span_entry_row(db_session, user=seeded_user, game=seeded_game, ply=ply, eval_cp=eval_cp)
            with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(999, None))) as mock_eval:
                await run_backfill(db="dev", user_id=None, dry_run=False, limit=None)
            assert mock_eval.call_count == 0  # row had eval_cp set → skipped
            # Verify -42 still in DB
            ...


    class TestLimit:
        async def test_limit_caps_evaluations(self, db_session, ...):
            ...


    class TestUserFilter:
        async def test_user_id_scopes_rows(self, db_session, ...):
            ...
    ```

    Tests will FAIL until Task 2 creates `scripts/backfill_eval.py` with `run_backfill`. RED phase.

    **Implementation note for executor:** The script must expose a callable `run_backfill(db: str, user_id: int | None, dry_run: bool, limit: int | None) -> None` that does NOT itself parse argv — `main()` parses argv and calls `run_backfill`. This separation is what makes the tests possible. If the executor cannot find suitable fixtures in `tests/conftest.py` for seeded_user / seeded_game / db_session, fall back to inline construction in the test file (use the patterns from `tests/test_endgame_repository.py`).
  </action>
  <verify>
    <automated>
      uv run pytest tests/scripts/test_backfill_eval.py -x 2>&1 | tail -30
      # Expected RED: ImportError on `scripts.backfill_eval` until Task 2 lands.
    </automated>
  </verify>
  <acceptance_criteria>
    - File `tests/scripts/__init__.py` exists.
    - File `tests/scripts/test_backfill_eval.py` exists.
    - `grep -n "TestDryRun\|TestIdempotency\|TestLichessPreservation\|TestLimit\|TestUserFilter" tests/scripts/test_backfill_eval.py` returns at least 5 matches.
    - Pytest fails with `ModuleNotFoundError: scripts.backfill_eval` (RED phase confirmed).
  </acceptance_criteria>
  <done>Wave 0 test file present (RED); pytest output names the missing module.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement scripts/backfill_eval.py (GREEN)</name>
  <files>scripts/backfill_eval.py</files>
  <read_first>
    - scripts/reclassify_positions.py (full file — CLI shape, Sentry init, VACUUM, COMMIT batching, async_session_maker usage)
    - app/services/engine.py (the wrapper from Plan 78-02 — start_engine, stop_engine, evaluate)
    - app/repositories/endgame_repository.py:1-50 (ENDGAME_PLY_THRESHOLD constant location and value)
    - app/core/config.py / app/core/database.py (settings + async_session_maker construction)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "Backfill Script Patterns" (lines 313-449)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md "scripts/backfill_eval.py" section
    - tests/scripts/test_backfill_eval.py (the contract from Task 1)
    - CLAUDE.md "Database Access (MCP)" (DB ports: dev=5432, benchmark=5433, prod=15432)
  </read_first>
  <action>
    Create `scripts/backfill_eval.py`. Mirror `scripts/reclassify_positions.py`'s structural skeleton: docstring with three-round runbook, sys.path bootstrap, `_log` helper, argparse, Sentry init, async session maker per `--db` target, span-entry SELECT, COMMIT-every-100, `VACUUM ANALYZE` at completion, `if __name__ == "__main__": asyncio.run(main())`.

    Required CLI (D-08):
    - `--db {dev|benchmark|prod}` REQUIRED. Selects DB host/port from CLAUDE.md (dev=5432, benchmark=5433, prod=15432).
    - `--user-id <int>` OPTIONAL. Default = all users.
    - `--dry-run` OPTIONAL flag. Counts rows, exits without writing or starting engine.
    - `--limit <int>` OPTIONAL. Caps evaluations at N rows.

    Concrete signature exposed for testability:
    ```python
    async def run_backfill(
        *,
        db: str,
        user_id: int | None,
        dry_run: bool,
        limit: int | None,
    ) -> None:
        """Public callable for tests. main() parses argv and calls this."""
        ...
    ```

    Module structure:

    ```python
    """Backfill Stockfish eval into endgame span-entry rows (Phase 78 FILL-01/02/03).

    SPEC drift: FILL-02 hash-dedup is RELAXED per CONTEXT.md D-10. Row-level
    idempotency only (skip rows where eval_cp OR eval_mate is already populated).
    Cross-row hash cache lookup costs more than re-evaluating the rare collision.

    Three-round runbook (D-07, executed by Plan 78-06):
        Round 1 (dev):       --db dev --limit 50          # smoke check
        Round 2 (benchmark): --db benchmark               # full benchmark
                             then operator runs /conv-recov-validation (VAL-01 gate)
        Round 3 (prod):      --db prod                    # via bin/prod_db_tunnel.sh
                             must complete BEFORE phase merge + deploy

    Usage:
        # Local dev / benchmark / prod-via-tunnel — runs from operator's machine
        uv run python scripts/backfill_eval.py --db dev --limit 50
        uv run python scripts/backfill_eval.py --db benchmark
        uv run python scripts/backfill_eval.py --db prod --user-id 1
        uv run python scripts/backfill_eval.py --db prod --dry-run
    """
    from __future__ import annotations

    import argparse
    import asyncio
    import io
    import os
    import sys
    from datetime import datetime, timezone
    from pathlib import Path

    import chess
    import chess.pgn
    import sentry_sdk
    from sqlalchemy import func, select, text, update
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from app.core.config import settings  # noqa: E402
    from app.models.game import Game  # noqa: E402
    from app.models.game_position import GamePosition  # noqa: E402
    from app.repositories.endgame_repository import ENDGAME_PLY_THRESHOLD  # noqa: E402
    from app.services.engine import evaluate, start_engine, stop_engine  # noqa: E402


    EVAL_BATCH_SIZE = 100  # D-09 COMMIT every 100 evals


    def _log(msg: str = "") -> None:
        """Print a message prefixed with a UTC timestamp."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] {msg}")


    def _db_url(target: str) -> str:
        """Build the asyncpg URL for the chosen --db target.

        - dev:       localhost:5432  (Docker compose flawchess-dev)
        - benchmark: localhost:5433  (Docker compose flawchess-benchmark)
        - prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

        Credentials and DB names come from settings (env). Operator must have
        the appropriate DB-specific creds in their local .env or in env vars.
        """
        # Executor: confirm exact env-var names from app/core/config.py.
        # Pattern below matches the project's settings shape; adjust if settings
        # uses different attribute names.
        host_map = {"dev": ("localhost", 5432), "benchmark": ("localhost", 5433), "prod": ("localhost", 15432)}
        if target not in host_map:
            raise ValueError(f"Unknown --db target: {target!r}")
        host, port = host_map[target]
        # Reuse the user/password/dbname from settings; fall back to env-specific overrides
        # if the operator has set BACKFILL_<TARGET>_DB_URL.
        override = os.environ.get(f"BACKFILL_{target.upper()}_DB_URL")
        if override:
            return override
        # else build from settings — executor finalizes once they read app/core/config.py
        return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{host}:{port}/{settings.POSTGRES_DB}"


    def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
        """Replay PGN to target_ply (0-indexed, pre-push). Mirrors reclassify_positions.py."""
        try:
            game = chess.pgn.read_game(io.StringIO(pgn_text))
        except Exception:
            return None
        if game is None:
            return None
        board = game.board()
        for i, node in enumerate(game.mainline()):
            if i == target_ply:
                return board
            board.push(node.move)
        return board


    def _build_span_entry_stmt(user_id: int | None, limit: int | None):
        """Span-entry SELECT: NULL-eval rows where ply == MIN(ply) and COUNT(ply) >= threshold."""
        # Subquery: per (user_id, game_id, endgame_class), the MIN(ply) where group has >= threshold rows
        span_min = (
            select(
                GamePosition.user_id.label("user_id"),
                GamePosition.game_id.label("game_id"),
                GamePosition.endgame_class.label("endgame_class"),
                func.min(GamePosition.ply).label("min_ply"),
            )
            .where(GamePosition.endgame_class.isnot(None))
            .group_by(GamePosition.user_id, GamePosition.game_id, GamePosition.endgame_class)
            .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
            .subquery("span_min")
        )
        stmt = (
            select(GamePosition.id, GamePosition.game_id, GamePosition.ply, Game.pgn)
            .join(Game, Game.id == GamePosition.game_id)
            .join(
                span_min,
                (GamePosition.user_id == span_min.c.user_id)
                & (GamePosition.game_id == span_min.c.game_id)
                & (GamePosition.endgame_class == span_min.c.endgame_class)
                & (GamePosition.ply == span_min.c.min_ply),
            )
            .where(
                GamePosition.eval_cp.is_(None),
                GamePosition.eval_mate.is_(None),
            )
        )
        if user_id is not None:
            stmt = stmt.where(GamePosition.user_id == user_id)
        stmt = stmt.order_by(GamePosition.game_id, GamePosition.ply)
        if limit is not None:
            stmt = stmt.limit(limit)
        return stmt


    async def run_backfill(*, db: str, user_id: int | None, dry_run: bool, limit: int | None) -> None:
        """FILL-01/02/03 backfill driver. Public for testability.

        Idempotency (FILL-02 relaxed per D-10): row-level WHERE eval_cp IS NULL AND eval_mate IS NULL.
        Resume: same WHERE clause picks up uncommitted rows on the next run.
        """
        url = _db_url(db)
        async_engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

        # Count phase (always runs; cheap)
        async with session_maker() as session:
            stmt = _build_span_entry_stmt(user_id, limit)
            rows = (await session.execute(stmt)).all()
        _log(f"Found {len(rows)} span-entry rows with NULL eval (db={db}, user_id={user_id}, limit={limit})")

        if dry_run:
            _log("--dry-run: exiting without writing")
            await async_engine.dispose()
            return

        if not rows:
            _log("Nothing to do")
            await async_engine.dispose()
            return

        # Eval phase — engine + COMMIT every 100
        await start_engine()
        try:
            async with session_maker() as session:
                evaluated = 0
                skipped_no_board = 0
                skipped_engine_err = 0
                for i, row in enumerate(rows):
                    board = _board_at_ply(row.pgn, row.ply)
                    if board is None:
                        skipped_no_board += 1
                        continue
                    eval_cp, eval_mate = await evaluate(board)
                    if eval_cp is None and eval_mate is None:
                        skipped_engine_err += 1
                        # Sentry capture: bounded context only (no PGN, no user_id)
                        sentry_sdk.set_context("backfill_eval", {
                            "game_position_id": row.id,
                            "game_id": row.game_id,
                            "ply": row.ply,
                            "db_target": db,
                        })
                        sentry_sdk.set_tag("source", "backfill")
                        sentry_sdk.capture_message("backfill engine returned None tuple", level="warning")
                        continue
                    await session.execute(
                        update(GamePosition)
                        .where(GamePosition.id == row.id)
                        .values(eval_cp=eval_cp, eval_mate=eval_mate)
                    )
                    evaluated += 1
                    if (i + 1) % EVAL_BATCH_SIZE == 0:
                        await session.commit()
                        _log(f"Committed {i + 1}/{len(rows)} rows (evaluated={evaluated}, skipped_no_board={skipped_no_board}, skipped_engine_err={skipped_engine_err})")
                await session.commit()
                _log(f"Final commit. Total evaluated={evaluated}, skipped_no_board={skipped_no_board}, skipped_engine_err={skipped_engine_err}")
        finally:
            await stop_engine()

        # VACUUM ANALYZE per RESEARCH.md open question #4 + reclassify_positions.py:179-188
        async with async_engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("VACUUM ANALYZE game_positions"))
        _log("VACUUM ANALYZE complete")
        await async_engine.dispose()


    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Backfill Stockfish eval into endgame span-entry rows (Phase 78)")
        parser.add_argument("--db", choices=["dev", "benchmark", "prod"], required=True)
        parser.add_argument("--user-id", type=int, default=None, help="Limit to a single user (default: all users)")
        parser.add_argument("--dry-run", action="store_true", help="Count rows and exit; no engine spin-up, no writes")
        parser.add_argument("--limit", type=int, default=None, help="Cap evaluations at N rows (testing/staging)")
        return parser.parse_args()


    async def main() -> None:
        args = parse_args()
        if settings.SENTRY_DSN:
            sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
        _log(f"Starting backfill: db={args.db} user_id={args.user_id} dry_run={args.dry_run} limit={args.limit}")
        await run_backfill(db=args.db, user_id=args.user_id, dry_run=args.dry_run, limit=args.limit)
        _log("Done")


    if __name__ == "__main__":
        asyncio.run(main())
    ```

    **Executor adjustments:**
    - Confirm `settings.POSTGRES_USER`, `settings.POSTGRES_PASSWORD`, `settings.POSTGRES_DB`, `settings.SENTRY_DSN`, `settings.ENVIRONMENT` exist in `app/core/config.py`. Adjust attribute names if the project uses different ones.
    - Confirm `ENDGAME_PLY_THRESHOLD` is importable from `app/repositories/endgame_repository.py`. If it's underscore-private, either lift it to module-public or define a sibling public constant `ENDGAME_PLY_THRESHOLD` in the same module and re-import.
    - The `BACKFILL_{TARGET}_DB_URL` env-var override is for cases where operator wants to use a non-default user/password/dbname per-target (e.g. dev DB has different creds than prod). This is documented in the docstring.
    - Resume semantics are inherent to the SELECT WHERE clause — no extra checkpoint file needed.
    - Per CLAUDE.md: no `asyncio.gather` over the same session; no `requests`. Both honored.
  </action>
  <verify>
    <automated>
      uv run ruff check scripts/backfill_eval.py
      uv run ty check scripts/backfill_eval.py
      uv run pytest tests/scripts/test_backfill_eval.py -x
      uv run python scripts/backfill_eval.py --help
      grep -c "asyncio.gather" scripts/backfill_eval.py  # MUST be 0
      grep -c "import requests\|import berserk" scripts/backfill_eval.py  # MUST be 0
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "async def run_backfill" scripts/backfill_eval.py` returns a match.
    - `grep -n "EVAL_BATCH_SIZE = 100" scripts/backfill_eval.py` returns a match (D-09).
    - `grep -n "VACUUM ANALYZE" scripts/backfill_eval.py` returns a match.
    - `grep -n "from app.services.engine import" scripts/backfill_eval.py` returns a match (uses Plan 78-02 wrapper, not duplicate engine setup).
    - `grep -c "asyncio.gather" scripts/backfill_eval.py` returns 0.
    - `grep -c "import requests\|import berserk" scripts/backfill_eval.py` returns 0.
    - `grep -n "eval_cp.is_(None)\|eval_mate.is_(None)" scripts/backfill_eval.py` shows the row-level idempotency check (FILL-02 relaxed).
    - CLI parser has `--db`, `--user-id`, `--dry-run`, `--limit` (D-08).
    - `uv run ruff check scripts/backfill_eval.py` exits 0.
    - `uv run ty check scripts/backfill_eval.py` exits 0.
    - `uv run pytest tests/scripts/test_backfill_eval.py -x` exits 0 (GREEN — Task 1 contract satisfied).
    - `uv run python scripts/backfill_eval.py --help` prints usage with all four flags.
  </acceptance_criteria>
  <done>Backfill script exists, type-checks clean, Wave 0 tests pass, CLI matches D-08, no `asyncio.gather` over the same session, no synchronous HTTP imports.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator's machine → DB targets | Script connects to dev (5432), benchmark (5433), prod-via-tunnel (15432). All three are explicitly chosen via `--db`. |
| Engine timeout / crash → DB write | Wrapper returns `(None, None)` on engine error; script SKIPS the row, logs to Sentry, continues. No partial writes. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-78-11 | Tampering | Backfill overwrites lichess `%eval` annotations | mitigate | SELECT WHERE `eval_cp IS NULL AND eval_mate IS NULL` excludes rows with any existing eval. Wave 0 test `test_lichess_eval_not_overwritten` asserts this invariant. FILL-04 byte-for-byte preservation. |
| T-78-12 | Tampering | Wrong DB target (e.g. running prod backfill against dev creds by mistake) | mitigate | `--db` is REQUIRED with explicit `{dev|benchmark|prod}` choices; no default. `_log()` echoes the target on every commit boundary so operator sees `db=prod` in logs. |
| T-78-13 | Information disclosure | Sentry context leaks user-identifying PGN | mitigate | Sentry context is bounded fields only (`game_position_id`, `game_id`, `ply`, `db_target`). NO PGN, NO user_id, NO board FEN. |
| T-78-14 | DoS | Wedged engine consumes the entire backfill | mitigate | Wrapper's 2s timeout (D-05) bounds per-eval wall-clock. Engine self-restarts on timeout. Script logs and skips, does not retry. |
| T-78-15 | Denial of service | Prod tunnel drops mid-backfill | accept | COMMIT-every-100 ensures no data loss; resume via SELECT NULL re-runs the script. Operator restarts. Documented in docstring runbook. |
| T-78-16 | Repudiation | No audit log of what was written | accept | Script logs at COMMIT boundaries with row counts. Sentry captures errors. No formal audit trail beyond `_log()` stdout — acceptable for an operator-only one-shot tool. |
</threat_model>

<verification>
- `uv run pytest tests/scripts/test_backfill_eval.py -x` GREEN.
- `uv run ty check scripts/backfill_eval.py` exits 0.
- `uv run python scripts/backfill_eval.py --db dev --dry-run` against the dev Docker DB runs without errors and reports a row count (operator-only sanity check; not a CI gate).
- ENG-03 grep gate clean: `grep -rn "stockfish\|popen_uci\|setoption" scripts/backfill_eval.py` shows only the `from app.services.engine import` import line.
</verification>

<success_criteria>
- `scripts/backfill_eval.py` walks span-entry rows with NULL eval, SAN-replays to entry ply, evaluates via shared wrapper, writes results.
- Re-run on populated dataset performs zero engine calls (idempotency).
- Mid-run kill resumes via the SELECT NULL clause (no checkpoint file).
- CLI shape matches D-08.
- Wave 0 tests cover dry-run, idempotency, lichess preservation, limit, user filter.
- FILL-02 drift acknowledgement is explicit (in PLAN truths and module docstring).
</success_criteria>

<output>
After completion, create `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-03-SUMMARY.md` recording: span-entry SELECT shape used, row count observed against dev DB during smoke check, FILL-02 drift acknowledgement.
</output>
