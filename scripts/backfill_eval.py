"""Backfill Stockfish eval into endgame span-entry rows (Phase 78 FILL-01/02/03).

Row-level idempotency only (skip rows where eval_cp OR eval_mate is already
populated). No cross-row hash dedup — endgame span entries are effectively
unique across games and a hash cache lookup costs more than re-evaluating
the rare collision (FILL-02 relaxed, locked per CONTEXT.md D-10).

Three-round runbook (D-07, executed by Plan 78-06):
    Round 1 (dev):       --db dev --user-id <test-user-id> --limit 50  # smoke
    Round 2 (benchmark): --db benchmark                                  # full
                         then operator runs /conv-recov-validation (VAL-01 gate)
    Round 3 (prod):      --db prod                                       # via bin/prod_db_tunnel.sh
                         must complete BEFORE phase merge + deploy

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

DB URL is derived from settings.DATABASE_URL by swapping the port.  To override,
set BACKFILL_DEV_DB_URL, BACKFILL_BENCHMARK_DB_URL, or BACKFILL_PROD_DB_URL.

Stockfish binary:
    The script invokes app.services.engine, which reads STOCKFISH_PATH (default
    /usr/local/bin/stockfish — the path baked into the prod Docker image).
    Locally that binary does not exist; bin/run_local.sh exports
    STOCKFISH_PATH=$HOME/.local/stockfish/sf, but standalone script runs do not
    inherit that, so you must set it yourself:

        export STOCKFISH_PATH=$HOME/.local/stockfish/sf
        uv run python scripts/backfill_eval.py --db dev --user-id 13

    See .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-06-SUMMARY.md
    for install steps if the binary is missing.

Usage:
    uv run python scripts/backfill_eval.py --db dev --limit 50
    uv run python scripts/backfill_eval.py --db benchmark
    uv run python scripts/backfill_eval.py --db prod --user-id 1
    uv run python scripts/backfill_eval.py --db prod --dry-run

Parallelism (--workers, default 1):
    The eval phase runs N independent Stockfish processes via EnginePool.
    Default 1 = byte-identical to the legacy singleton path. On a 16 vCPU
    workstation, 10–12 workers is a good upper bound (leave headroom for
    Postgres + the SSH tunnel + OS). Each worker is configured with
    Threads=1, so N×1 scales much better than 1×N for independent positions.

        uv run python scripts/backfill_eval.py --db prod --workers 10

    Do NOT raise --workers on the prod server (4 vCPU / 8 GB) — the import
    path uses the engine module's singleton, and a multi-engine pool there
    would starve the API and Postgres.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence
from urllib.parse import urlparse, urlunparse

import chess
import chess.pgn
import sentry_sdk
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import Select

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.repositories.endgame_repository import ENDGAME_PIECE_COUNT_THRESHOLD  # noqa: E402
from app.services import engine as _engine_module  # noqa: E402
from app.services.engine import EnginePool  # noqa: E402
from app.services.position_classifier import (  # noqa: E402
    MIDGAME_MAJORS_AND_MINORS_THRESHOLD,
    MIDGAME_MIXEDNESS_THRESHOLD,
)

# D-09: COMMIT every 500 evals — at 10 workers × ~70ms/eval that's ~3.5s of work
# per chunk. Each chunk now collapses to one batched UPDATE … FROM (VALUES …)
# round-trip instead of EVAL_BATCH_SIZE individual UPDATEs, so the SSH tunnel to
# prod sees ~1/500th the round-trip overhead. Resume semantics are unchanged: a
# mid-run kill loses at most one chunk's worth of evaluated rows.
EVAL_BATCH_SIZE = 500

# Default to single-worker mode = byte-identical legacy behavior. CLI --workers
# overrides; a 16 vCPU workstation can comfortably run 10–12.
DEFAULT_WORKERS = 1

# Phase 79 PHASE-FILL-01: chunk size (in game_id units) for phase-column UPDATE pass.
# Phase assignment is now per-game (Lichess Divider semantics — monotonic),
# so chunking is by game_id range, not row id. 10_000 games keeps lock duration
# bounded while amortizing transaction overhead.
PHASE_BACKFILL_CHUNK_SIZE = 10_000

# Port map for --db targets per CLAUDE.md.
_TARGET_PORT: dict[str, int] = {
    "dev": 5432,
    "benchmark": 5433,
    "prod": 15432,
}


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _db_url(target: str) -> str:
    """Build the asyncpg URL for the chosen --db target.

    Derives the URL from settings.DATABASE_URL by replacing the host:port
    with localhost:<target-port>.  The target-specific BACKFILL_{TARGET}_DB_URL
    env var overrides this for operators who use non-default credentials —
    typically only needed for prod, whose password differs from the dev DB.

    All targets are reached via localhost (dev/benchmark via Docker, prod via
    the SSH tunnel from bin/prod_db_tunnel.sh).  Overrides MUST therefore use
    a localhost host; a non-local host (e.g. the docker-internal `db`) will
    fail to resolve from a developer workstation.  This is enforced below.

    Ports:
        dev:       localhost:5432  (flawchess-dev Docker compose)
        benchmark: localhost:5433  (flawchess-benchmark Docker compose)
        prod:      localhost:15432 (SSH tunnel via bin/prod_db_tunnel.sh)
    """
    if target not in _TARGET_PORT:
        raise ValueError(f"Unknown --db target: {target!r}. Must be one of: {list(_TARGET_PORT)}")

    override_var = f"BACKFILL_{target.upper()}_DB_URL"
    override = os.environ.get(override_var)
    if override:
        host = urlparse(override).hostname
        if host not in _LOCAL_HOSTS:
            raise ValueError(
                f"{override_var} host is {host!r}, but this script always reaches "
                f"the database via localhost (dev/benchmark via Docker, prod via "
                f"the SSH tunnel from bin/prod_db_tunnel.sh). Update the override "
                f"to use localhost:{_TARGET_PORT[target]} (keeping the credentials)."
            )
        return override

    port = _TARGET_PORT[target]
    parsed = urlparse(settings.DATABASE_URL)
    # Replace host and port; keep scheme, path (DB name), user, password.
    new_netloc = f"{parsed.username}:{parsed.password}@localhost:{port}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
    """Replay PGN to target_ply (0-indexed, pre-push).

    Returns the board state BEFORE the move at that ply — this is the
    state that was classified as the endgame span entry.  Mirrors the
    replay loop in scripts/reclassify_positions.py.

    Returns None if the PGN cannot be parsed or if target_ply is out of range.
    """
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
    # target_ply >= number of moves → return final position
    return board


def _boards_at_plies(pgn_text: str, plies: Sequence[int]) -> dict[int, chess.Board]:
    """Replay PGN once, return {ply: board} for all requested plies.

    Same per-ply semantics as _board_at_ply: board state BEFORE the move at
    that ply; ply >= mainline length → final position. Returns an empty dict
    if the PGN cannot be parsed; callers treat missing keys as a skip.

    Used by the backfill eval loop to amortize PGN parsing across all rows
    that share a game_id (a game with one middlegame entry plus several
    endgame span entries used to re-parse its PGN N times).
    """
    if not plies:
        return {}
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return {}
    if game is None:
        return {}

    plies_set = set(plies)
    captured: dict[int, chess.Board] = {}
    board = game.board()
    for i, node in enumerate(game.mainline()):
        if i in plies_set:
            captured[i] = board.copy()
        board.push(node.move)
    # Any requested ply >= mainline length → final position (after last push).
    for ply in plies_set:
        captured.setdefault(ply, board)
    return captured


def _build_span_entry_stmt(
    user_id: int | None,
    limit: int | None,
) -> Select[tuple[int, int, int, str]]:
    """Build the span-entry SELECT statement.

    Selects GamePosition rows where:
    1. eval_cp IS NULL AND eval_mate IS NULL  (row-level idempotency, FILL-02)
    2. endgame_class IS NOT NULL              (endgame row)
    3. ply == MIN(ply) for its contiguous-run group (user_id, game_id,
       endgame_class, island_id)

    Each contiguous run of the same endgame_class within a game is treated as
    its own span. If a game enters class=1, switches to class=2, then
    re-enters class=1, both class=1 stretches get an entry eval — not just
    the earliest. Spans of any length (including 1-ply) are included; the
    repository's ENDGAME_PLY_THRESHOLD is intentionally not enforced here.

    Island detection uses the gaps-and-islands trick: within a partition of
    (user_id, game_id, endgame_class), `ply - row_number()` is constant for
    consecutive plies and changes whenever a non-class row breaks the run,
    so it serves as a stable per-run group key.

    Optional filters:
    - user_id: scopes to a single user (--user-id flag)
    - limit: caps result set (--limit flag)
    """
    # Per-class row number, ordered by ply. ply - rn is constant within a
    # contiguous run of the same endgame_class in the same game.
    island_rn = func.row_number().over(
        partition_by=(
            GamePosition.user_id,
            GamePosition.game_id,
            GamePosition.endgame_class,
        ),
        order_by=GamePosition.ply,
    )

    classified = (
        select(
            GamePosition.user_id.label("uid"),
            GamePosition.game_id.label("gid"),
            GamePosition.endgame_class.label("ec"),
            GamePosition.ply.label("ply"),
            (GamePosition.ply - island_rn).label("island_id"),
        )
        .where(GamePosition.endgame_class.isnot(None))
        .subquery("classified")
    )

    span_min = (
        select(
            classified.c.uid,
            classified.c.gid,
            classified.c.ec,
            func.min(classified.c.ply).label("min_ply"),
        )
        .group_by(
            classified.c.uid,
            classified.c.gid,
            classified.c.ec,
            classified.c.island_id,
        )
        .subquery("span_min")
    )

    stmt = (
        select(
            GamePosition.id,
            GamePosition.game_id,
            GamePosition.ply,
            Game.pgn,
        )
        .join(Game, Game.id == GamePosition.game_id)
        .join(
            span_min,
            (GamePosition.user_id == span_min.c.uid)
            & (GamePosition.game_id == span_min.c.gid)
            & (GamePosition.endgame_class == span_min.c.ec)
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


def _build_middlegame_entry_stmt(
    user_id: int | None,
    limit: int | None,
) -> Select[tuple[int, int, int, str]]:
    """Build the middlegame entry SELECT statement (Phase 79 PHASE-FILL-02).

    Selects GamePosition rows where:
    1. eval_cp IS NULL AND eval_mate IS NULL  (row-level idempotency, T-78-17 lichess preserve)
    2. phase = 1                               (middlegame row)
    3. ply == MIN(ply) of phase=1 rows in the same game

    At most one middlegame entry per game. Later phase=1 stretches after an
    endgame are NOT re-evaluated (D-79-08 — mirrors lichess Divider's single
    Division(midGame, endGame) return).

    Returns rows with the same (id, game_id, ply, pgn) shape as
    _build_span_entry_stmt so the shared eval+write loop processes both
    row sets uniformly.
    """
    midgame_min = (
        select(
            GamePosition.game_id.label("gid"),
            func.min(GamePosition.ply).label("min_ply"),
        )
        .where(GamePosition.phase == 1)
        .group_by(GamePosition.game_id)
        .subquery("midgame_min")
    )

    stmt = (
        select(
            GamePosition.id,
            GamePosition.game_id,
            GamePosition.ply,
            Game.pgn,
        )
        .join(Game, Game.id == GamePosition.game_id)
        .join(
            midgame_min,
            (GamePosition.game_id == midgame_min.c.gid)
            & (GamePosition.ply == midgame_min.c.min_ply),
        )
        .where(
            GamePosition.eval_cp.is_(None),
            GamePosition.eval_mate.is_(None),
            GamePosition.phase == 1,
        )
    )

    if user_id is not None:
        stmt = stmt.where(GamePosition.user_id == user_id)

    stmt = stmt.order_by(GamePosition.game_id, GamePosition.ply)

    if limit is not None:
        stmt = stmt.limit(limit)

    return stmt


def _resolve_boards_grouped(
    rows: Sequence[Any],
) -> list[tuple[Any, chess.Board | None]]:
    """Replay each game's PGN once across all of its rows.

    Rows arrive ordered by (game_id, ply); itertools.groupby gives us one
    contiguous block per game so we can hand all of that game's plies to
    `_boards_at_plies` and walk the mainline a single time. A game with one
    middlegame entry plus several endgame span entries used to re-parse its
    PGN N times — now it parses once.

    Returns a list of (row, board_or_None) preserving the input order. None
    means the PGN failed to parse; callers count that as `skipped_no_board`.
    """
    from itertools import groupby

    out: list[tuple[Any, chess.Board | None]] = []
    for _gid, group_iter in groupby(rows, key=lambda r: r.game_id):
        group = list(group_iter)
        plies = [r.ply for r in group]
        boards = _boards_at_plies(group[0].pgn, plies)
        for r in group:
            out.append((r, boards.get(r.ply)))
    return out


def _build_batch_update_sql(batch_size: int) -> str:
    """Render the batched UPDATE … FROM (VALUES …) template for `batch_size` rows.

    One round-trip writes the whole chunk instead of one UPDATE per row.

    The explicit ::integer casts on every VALUES tuple are required because
    asyncpg binds Python ints as untyped parameters and Postgres infers `text`
    for the resulting columns ("operator does not exist: integer = text" on
    the JOIN). Casting every tuple (not just the first) is safe and avoids a
    NULL-on-the-first-row gotcha: eval_cp may be NULL on mate positions and
    eval_mate may be NULL on non-mate positions, so neither column has a
    reliable type-anchor row. Postgres coerces integer to the SMALLINT
    column types on the SET assignment.
    """
    values = ", ".join(
        f"((:id_{i})::integer, (:cp_{i})::integer, (:mate_{i})::integer)"
        for i in range(batch_size)
    )
    return (
        "UPDATE game_positions gp "
        "SET eval_cp = v.cp, eval_mate = v.mate "
        f"FROM (VALUES {values}) AS v(id, cp, mate) "
        "WHERE gp.id = v.id "
        "AND gp.eval_cp IS NULL AND gp.eval_mate IS NULL"
    )


async def _flush_writes(
    session: AsyncSession,
    writes: list[tuple[int, int | None, int | None]],
) -> None:
    """Apply pending (id, eval_cp, eval_mate) writes as one batched UPDATE."""
    if not writes:
        return
    sql = _build_batch_update_sql(len(writes))
    params: dict[str, int | None] = {}
    for i, (rid, cp, mate) in enumerate(writes):
        params[f"id_{i}"] = rid
        params[f"cp_{i}"] = cp
        params[f"mate_{i}"] = mate
    # The CAST happens via the column types on game_positions; psycopg/asyncpg
    # binds None as SQL NULL natively, and the UPDATE's column types coerce.
    await session.execute(text(sql), params)


async def _evaluate_and_write_rows(
    rows: Sequence[Any],
    session: AsyncSession,
    *,
    db: str,
    eval_kind: Literal["endgame_span_entry", "middlegame_entry"],
    pool: EnginePool,
) -> tuple[int, int, int]:
    """Evaluate and write eval_cp / eval_mate for a batch of rows.

    Shared between the endgame-span and middlegame-entry eval passes.
    eval_kind is set on Sentry as a tag so the two row sets are filterable.

    Concurrency: each chunk fan-outs `EVAL_BATCH_SIZE` evaluate() calls via
    asyncio.gather; the EnginePool's internal queue caps in-flight analyses
    at `pool.size`, so a 1-worker pool serializes (legacy behavior) while a
    10-worker pool gets ~10× throughput. Writes are deferred to a single
    batched UPDATE per chunk → one round-trip instead of EVAL_BATCH_SIZE.

    Returns (evaluated_count, skipped_no_board, skipped_engine_err).
    """
    resolved = _resolve_boards_grouped(rows)
    skipped_no_board = 0
    eval_targets: list[tuple[Any, chess.Board]] = []
    for row, board in resolved:
        if board is None:
            skipped_no_board += 1
            _log(f"WARNING: could not replay PGN for game_id={row.game_id} ply={row.ply}; skipping")
            continue
        eval_targets.append((row, board))

    evaluated = 0
    skipped_engine_err = 0
    total = len(eval_targets)

    for chunk_start in range(0, total, EVAL_BATCH_SIZE):
        chunk = eval_targets[chunk_start : chunk_start + EVAL_BATCH_SIZE]
        results = await asyncio.gather(*(pool.evaluate(b) for _, b in chunk))

        writes: list[tuple[int, int | None, int | None]] = []
        for (row, _board), (eval_cp, eval_mate) in zip(chunk, results):
            if eval_cp is None and eval_mate is None:
                skipped_engine_err += 1
                sentry_sdk.set_context(
                    "backfill_eval",
                    {
                        "game_position_id": row.id,
                        "game_id": row.game_id,
                        "ply": row.ply,
                        "db_target": db,
                    },
                )
                sentry_sdk.set_tag("source", "backfill")
                sentry_sdk.set_tag("eval_kind", eval_kind)
                sentry_sdk.capture_message(
                    "backfill engine returned (None, None) tuple", level="warning"
                )
                continue
            writes.append((row.id, eval_cp, eval_mate))
            evaluated += 1

        await _flush_writes(session, writes)
        await session.commit()
        _log(
            f"  [{eval_kind}] committed {min(chunk_start + len(chunk), total)}/{total} rows "
            f"(evaluated={evaluated}, "
            f"skipped_no_board={skipped_no_board}, "
            f"skipped_engine_err={skipped_engine_err})"
        )

    return evaluated, skipped_no_board, skipped_engine_err


async def run_backfill(
    *,
    db: str,
    user_id: int | None,
    dry_run: bool,
    limit: int | None,
    workers: int = DEFAULT_WORKERS,
    timeout: float | None = None,
    _session_maker: async_sessionmaker[AsyncSession] | None = None,
    _pool: EnginePool | None = None,
) -> None:
    """FILL-01/02/03 backfill driver. Public callable for testability.

    Idempotency (FILL-02 relaxed per D-10): row-level WHERE eval_cp IS NULL
    AND eval_mate IS NULL.  No cross-row hash dedup.

    Resume: same WHERE clause naturally picks up uncommitted rows on the
    next run after a mid-run kill (D-09 COMMIT-every-100 bounds data loss).

    main() parses argv and calls this function with keyword-only args.

    workers: size of the Stockfish EnginePool. Default 1 = legacy serial
    behavior. Raise on hosts with spare CPU/RAM (e.g. 10 on a 16 vCPU box).
    Do NOT raise on the prod server — the live import path uses the engine
    module's singleton and would compete for CPU.

    timeout: per-eval timeout in seconds. None = use engine module default
    (_TIMEOUT_S = 2.0). Raise to recover positions that consistently time out
    at depth 15 (typically dense early-endgame positions with queens + rooks
    + minor pieces + many pawns). The override mutates the engine module's
    _TIMEOUT_S global before the pool is started; pool workers read the
    global at every evaluate() call so the override applies to all workers.

    _session_maker / _pool: internal test hooks. Production callers omit both;
    the production path builds its own engine from _db_url(db) and starts an
    EnginePool of `workers` Stockfish processes.
    """
    if timeout is not None:
        _engine_module._TIMEOUT_S = timeout
        _log(f"Engine per-eval timeout overridden: {timeout}s (default 2.0s)")

    dispose_engine = _session_maker is None
    if _session_maker is None:
        url = _db_url(db)
        async_engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    else:
        async_engine = None  # type: ignore[assignment]  # not created here; nothing to dispose
        session_maker = _session_maker

    # Phase 79 PHASE-FILL-01: per-game phase backfill matching Lichess Divider.scala.
    # Phase is monotonic across the game's ply timeline (opening → middlegame → endgame,
    # never backwards), so it must be computed at game level — a per-row CASE would
    # let phase oscillate on positions where pieces re-occupy the back rank.
    # Chunked by game_id range to bound lock duration. Idempotent on re-run because
    # the affected_games CTE only includes games where at least one ply has phase IS NULL.
    # Threshold constants are interpolated from position_classifier.py so SQL and Python
    # share one source of truth (D-79-01).
    phase_update_sql = text(
        f"""
        WITH affected_games AS (
            SELECT DISTINCT game_id
            FROM game_positions
            WHERE phase IS NULL
              AND game_id BETWEEN :lo AND :hi
        ),
        per_game AS (
            SELECT
                gp.game_id,
                MIN(gp.ply) FILTER (
                    WHERE gp.piece_count <= {MIDGAME_MAJORS_AND_MINORS_THRESHOLD}
                       OR gp.backrank_sparse
                       OR gp.mixedness > {MIDGAME_MIXEDNESS_THRESHOLD}
                ) AS mid_ply_raw,
                MIN(gp.ply) FILTER (
                    WHERE gp.piece_count <= {ENDGAME_PIECE_COUNT_THRESHOLD}
                ) AS end_ply
            FROM game_positions gp
            JOIN affected_games ag ON gp.game_id = ag.game_id
            GROUP BY gp.game_id
        ),
        adjusted AS (
            SELECT
                game_id,
                CASE
                    WHEN end_ply IS NOT NULL AND mid_ply_raw >= end_ply THEN NULL
                    ELSE mid_ply_raw
                END AS mid_ply,
                end_ply
            FROM per_game
        )
        UPDATE game_positions gp
        SET phase = CASE
            WHEN a.end_ply IS NOT NULL AND gp.ply >= a.end_ply THEN 2
            WHEN a.mid_ply IS NOT NULL AND gp.ply >= a.mid_ply THEN 1
            ELSE 0
        END
        FROM adjusted a
        WHERE gp.game_id = a.game_id
          AND gp.phase IS NULL
        """
    )

    async with session_maker() as phase_session:
        bounds_row = (
            await phase_session.execute(
                text(
                    "SELECT COALESCE(MIN(game_id), 0), COALESCE(MAX(game_id), 0) "
                    "FROM game_positions WHERE phase IS NULL"
                )
            )
        ).one()
        lo_total, hi_total = bounds_row
        if hi_total > 0:
            _log(
                f"Phase-column backfill: game_id range [{lo_total}, {hi_total}], "
                f"chunk size {PHASE_BACKFILL_CHUNK_SIZE} games"
            )
            if dry_run:
                null_count = (
                    await phase_session.execute(
                        text("SELECT COUNT(*) FROM game_positions WHERE phase IS NULL")
                    )
                ).scalar_one()
                _log(f"--dry-run: would update {null_count} rows with NULL phase")
            else:
                cursor = lo_total
                updated_total = 0
                while cursor <= hi_total:
                    chunk_hi = cursor + PHASE_BACKFILL_CHUNK_SIZE - 1
                    result = await phase_session.execute(
                        phase_update_sql, {"lo": cursor, "hi": chunk_hi}
                    )
                    updated_total += result.rowcount or 0  # ty: ignore[unresolved-attribute]  # CursorResult from DML execute
                    await phase_session.commit()
                    cursor = chunk_hi + 1
                _log(f"Phase-column backfill complete: {updated_total} rows updated")
        else:
            _log("Phase-column backfill: zero rows with NULL phase (no-op)")

    # Phase 78: endgame span-entry eval pass.
    async with session_maker() as endgame_count_session:
        span_stmt = _build_span_entry_stmt(user_id, limit)
        span_rows = (await endgame_count_session.execute(span_stmt)).all()

    _log(f"Endgame span-entry eval: {len(span_rows)} rows queued")

    # Phase 79 PHASE-FILL-02: middlegame entry eval pass — count rows for dry-run reporting.
    async with session_maker() as midgame_count_session:
        midgame_stmt = _build_middlegame_entry_stmt(user_id, limit)
        midgame_rows = (await midgame_count_session.execute(midgame_stmt)).all()

    _log(f"Middlegame entry eval: {len(midgame_rows)} rows queued")

    if dry_run:
        _log(f"--dry-run: would evaluate {len(span_rows)} endgame span-entry rows")
        _log(f"--dry-run: would evaluate {len(midgame_rows)} middlegame entry rows")
        _log("--dry-run: exiting without starting engine or writing")
        if dispose_engine and async_engine is not None:
            await async_engine.dispose()
        return

    if not span_rows and not midgame_rows:
        _log("Nothing to do.")
        if dispose_engine and async_engine is not None:
            await async_engine.dispose()
        return

    # Eval + write phase: spin up an EnginePool of `workers` Stockfish processes.
    # _pool is a test hook; production builds its own from `workers`.
    dispose_pool = _pool is None
    if _pool is None:
        pool = EnginePool(workers)
        await pool.start()
        _log(f"EnginePool started with {workers} worker(s).")
    else:
        pool = _pool

    try:
        if span_rows:
            async with session_maker() as endgame_session:
                (
                    endgame_evaluated,
                    endgame_no_board,
                    endgame_engine_err,
                ) = await _evaluate_and_write_rows(
                    span_rows,
                    endgame_session,
                    db=db,
                    eval_kind="endgame_span_entry",
                    pool=pool,
                )
            _log(
                f"Endgame span-entry eval complete: "
                f"evaluated={endgame_evaluated}, "
                f"skipped_no_board={endgame_no_board}, "
                f"skipped_engine_err={endgame_engine_err}"
            )
        else:
            _log("No endgame span-entry rows to evaluate.")

        # Phase 79 PHASE-FILL-02: middlegame entry eval pass.
        if midgame_rows:
            async with session_maker() as midgame_session:
                mid_evaluated, mid_no_board, mid_engine_err = await _evaluate_and_write_rows(
                    midgame_rows,
                    midgame_session,
                    db=db,
                    eval_kind="middlegame_entry",
                    pool=pool,
                )
            _log(
                f"Middlegame entry eval complete: "
                f"evaluated={mid_evaluated}, "
                f"skipped_no_board={mid_no_board}, "
                f"skipped_engine_err={mid_engine_err}"
            )
        else:
            _log("No middlegame entry rows to evaluate.")
    finally:
        if dispose_pool:
            await pool.stop()

    # VACUUM ANALYZE outside a transaction (cannot run inside transaction block).
    # Skipped when using an injected session maker (test mode: VACUUM not meaningful
    # inside a rolled-back transaction and the engine reference is not available).
    if dispose_engine and async_engine is not None:
        _log("Running VACUUM ANALYZE game_positions...")
        async with async_engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("VACUUM ANALYZE game_positions"))
        _log("VACUUM ANALYZE complete.")
        await async_engine.dispose()


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments (D-08)."""
    parser = argparse.ArgumentParser(
        description="Backfill Stockfish eval into endgame span-entry rows (Phase 78 FILL-01/02/03)."
    )
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help=(
            "Database target.  dev=localhost:5432, benchmark=localhost:5433, "
            "prod=localhost:15432 (via bin/prod_db_tunnel.sh).  REQUIRED (T-78-12)."
        ),
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        dest="user_id",
        metavar="N",
        help="Limit backfill to a single user ID.  Default: all users.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Count rows and print count; do not start engine or write anything.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap evaluations at N rows.  Useful for smoke checks and staging rounds.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="N",
        help=(
            f"Number of parallel Stockfish workers (default {DEFAULT_WORKERS}). "
            "Each worker is its own UCI process configured Threads=1, so N×1 "
            "scales much better than 1×N for independent positions. On a 16 vCPU "
            "workstation, 10–12 is a good upper bound. Do NOT raise this on the "
            "prod server (4 vCPU / 8 GB) — the live import path uses the engine "
            "module's singleton."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "Override the engine's per-eval timeout (default 2.0s in "
            "app/services/engine.py:_TIMEOUT_S). Raise to recover positions "
            "that time out at depth 15 — typically dense early-endgame "
            "positions with queens + rooks + minor pieces + many pawns. "
            "Applies to every pool worker."
        ),
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error(f"--workers must be >= 1, got {args.workers}")
    if args.timeout is not None and args.timeout <= 0:
        parser.error(f"--timeout must be > 0, got {args.timeout}")
    return args


async def main() -> None:
    """Entry point: parse CLI args, init Sentry, run backfill."""
    args = parse_args()

    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    _log(
        f"Starting backfill: db={args.db} user_id={args.user_id} "
        f"dry_run={args.dry_run} limit={args.limit} workers={args.workers} "
        f"timeout={args.timeout}"
    )
    await run_backfill(
        db=args.db,
        user_id=args.user_id,
        dry_run=args.dry_run,
        limit=args.limit,
        workers=args.workers,
        timeout=args.timeout,
    )
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
