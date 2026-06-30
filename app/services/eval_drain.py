"""Cold-lane eval drain coroutine for Phase 91 / SEED-023.

This module owns the in-process background coroutine that evaluates entry plies
for games whose `evals_completed_at IS NULL`. It is the structural fix for the
OOM-kill failure mode described in SEED-022/023 — by moving Stockfish work out
of the hot import lane (which caused 20-40 s held transactions) into this
dedicated background loop with short, well-bounded transactions.

Key architectural invariant:
    asyncio.gather() over engine_service.evaluate() MUST run OUTSIDE any open
    AsyncSession scope. Per CLAUDE.md hard rule: AsyncSession is not safe for
    concurrent use from multiple coroutines, and holding a session open during
    multi-position fan-out is the structural OOM driver.

Session discipline per tick:
    1. _pick_pending_game_ids: short read tx, then CLOSE.
    2. _load_pgns_for_games: short read tx, then CLOSE.
    3. asyncio.gather (no session open).
    4. Write session: open LATE, UPDATEs + commit, CLOSE.

Phase 91 / SEED-023 locks:
    D-09: engine (None, None) marks game complete — no permanent retry loop.
    D-11: LIFO id-DESC pick, batch size 10.
    D-12: no per-user fairness at current scale.
    D-13: idle sleep 5s when queue empty.

Quick 260521-d6o follow-up:
    Target collection is single-walk per game — one chess.pgn.read_game + one
    mainline traversal yields board snapshots at every target ply, instead of
    one parse-and-walk per target ply. Public wrappers
    (_collect_midgame_eval_targets, _collect_endgame_span_eval_targets) keep
    their original signatures for the hot-lane Stage 5c covered-game gate in
    import_service.py:_collect_covered_game_ids.
"""

import asyncio
import io
import json
import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import asyncpg
import chess
import chess.pgn
import sentry_sdk
import sqlalchemy as sa
from sqlalchemy import TextClause, bindparam, select, text, update
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import DEDUP_MAX_PLY, GamePosition
from app.models.import_job import ImportJob
from app.models.opening_position_eval import OpeningPositionEval
from app.repositories.game_flaws_repository import (
    bulk_insert_game_flaws,
    delete_flaws_for_game,
    flaw_record_to_row,
)
from app.repositories.game_repository import users_with_zero_pending
from app.services import engine as engine_service
from app.services import percentile_compute_registry
from app.services.eval_queue_service import WORKER_ID_SERVER_POOL, claim_eval_job
from app.services.flaws_service import classify_game_flaws, count_game_severities
from app.services.forcing_line_gate import PvNode
from app.services.user_benchmark_percentiles_service import compute_stage_b
from app.services.zobrist import PlyData

logger = logging.getLogger(__name__)

# UAT 2026-05-20 — same broad exception tuple as import_service.py to catch
# all connection-class errors raised by the asyncpg dialect during a
# Postgres restart. Copied verbatim (modulo module context).
_RETRIABLE_DB_OUTAGE_ERRORS: tuple[type[BaseException], ...] = (
    OperationalError,
    InterfaceError,
    DBAPIError,
    asyncpg.exceptions.CannotConnectNowError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.InterfaceError,
    asyncpg.exceptions.PostgresConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    OSError,
)

_DRAIN_BATCH_SIZE = 10  # D-11 (LIFO id-DESC pick size)
_DRAIN_IDLE_SLEEP_SECONDS = 5  # D-13 (poll interval when queue empty)

# Phase 119 WR-04: chunk the resweep_holed_games re-arm UPDATE so the documented
# unbounded "sweep all" prod path can't re-arm the entire holed backlog (~558k
# games) in one IN(...) statement/transaction — that would materialize the full
# id list as bind params (risking the parameter limit) and flip every game back
# into the tier-3 candidate pool simultaneously. Each chunk commits independently;
# the small-N path (count <= this size) is a single statement + single commit,
# behaviorally identical to the pre-batching code.
_RESWEEP_UPDATE_CHUNK_SIZE = 1000

# Phase 119 SEED-045: max drain ticks that may leave a non-terminal hole before
# the game is stamped complete anyway (with one aggregated Sentry warning).
# D-116-07 intent: a deterministically-unevaluable ply cannot loop forever.
# Pool outages (all-fail circuit breaker WR-05) do NOT consume attempts, so a
# transient outage cannot exhaust the budget and silently drop coverage.
MAX_EVAL_ATTEMPTS: int = 3

# Phase 116 EVAL-03 / D-116-02: dedup only in the opening region.
# WR-08: aliased from the model constant (single source of truth) so this
# boundary can never drift from the ply <= N predicate of the
# ix_gp_full_hash_opening partial index — drifting above it would silently
# stop dedup lookups from using the index.
_DEDUP_MAX_PLY: int = DEDUP_MAX_PLY

# SEED-049: under post-move storage, the game-ending move row (ply = max_ply - 1) stores
# the eval of the terminal game-over position, which is legitimately unevaluable. This
# offset defines "the game-ending move sits 1 ply before the maximum stored ply", used
# in the resweep predicate to exclude it from the hole definition (ply < max_ply - 1).
_GAME_ENDING_PLY_OFFSET: int = 1

# ─── Phase 123.1 SEED-053: opening eval cache population gate (single source of truth) ───

# OPENING_CACHE_BACKFILL_SQL is the canonical INSERT…SELECT that populates
# opening_position_eval from our-engine game_positions evals.  It is the single
# source of the cache-population gate, shared by:
#   - scripts/backfill_opening_eval_cache.py  (one-time idempotent backfill), and
#   - tests/services/test_full_eval_drain.py  (gate-equivalence tests for
#     _fetch_dedup_evals — run this SQL before calling _fetch_dedup_evals so the
#     gate is exercised at its actual enforcement site).
#
# Gate predicates:
#   full_evals_completed_at IS NOT NULL — our-engine evals only (D-123.1-03)
#   lichess_evals_at IS NULL            — exclude lichess %eval sources (WR-02 / D-117-07)
#   eval_cp IS NOT NULL OR eval_mate IS NOT NULL — donor row must have an eval
#   nxt.ply <= :dedup_max_ply           — opening region only (D-116-02 / EVAL-03)
# Idempotent: ON CONFLICT (full_hash) DO NOTHING.
OPENING_CACHE_BACKFILL_SQL: TextClause = text(
    """
    INSERT INTO opening_position_eval (full_hash, eval_cp, eval_mate, best_move)
    SELECT DISTINCT ON (nxt.full_hash)
           nxt.full_hash,
           cur.eval_cp,
           cur.eval_mate,
           nxt.best_move
    FROM   game_positions cur
    JOIN   game_positions nxt
           ON  nxt.game_id = cur.game_id
           AND nxt.ply     = cur.ply + 1
    JOIN   games g
           ON  g.id = cur.game_id
    WHERE  nxt.ply <= :dedup_max_ply
      AND  g.full_evals_completed_at IS NOT NULL
      AND  g.lichess_evals_at IS NULL
      AND  (cur.eval_cp IS NOT NULL OR cur.eval_mate IS NOT NULL)
    ON CONFLICT (full_hash) DO NOTHING
    """
)

# ─── Phase 123 SEED-051: entry-ply remote-fan-out lease constants (D-03/D-04/D-05) ───

# D-04: short TTL — entry-ply batches are only seconds of work (50 games × 2-3 plies
# × ~90ms ÷ N cores). Must be well under the 120s full-ply LEASE_TTL_SECONDS.
# RESEARCH Pitfall 3 recommends 15–30s; 20s is the midpoint with comfortable margin.
ENTRY_LEASE_TTL_SECONDS: int = 20

# D-5 starting knob: how many games to hand to one remote worker per batch.
# Tune once the worker is live and throughput is measured.
ENTRY_LEASE_BATCH_SIZE: int = 50

# D-5 starting knob: minimum backlog depth before /entry-lease invites remote workers.
# The existence probe uses OFFSET = THRESHOLD - 1 (Pitfall 6: 0-indexed OFFSET).
# Below this depth the server pool handles the tail solo (D-02).
ENTRY_LEASE_BACKLOG_THRESHOLD: int = 300


# ---------------------------------------------------------------------------
# Phase 116 full-ply drain: dataclass + helpers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _FullPlyEvalTarget:
    """One position scheduled for full-ply eval (Phase 116 EVAL-01).

    ply: game_positions.ply (0-indexed; 0 = initial position before first move)
    full_hash: for dedup batch-lookup at ply <= _DEDUP_MAX_PLY (EVAL-03)
    board: board snapshot for the engine call (if not dedup'd)
    eval_cp / eval_mate: the row's CURRENT stored values from the DB. Carried so
        the drain can skip engine calls for plies whose result would be
        discarded by the D-116-04 preservation gate anyway (WR-01), and so the
        write path's belt-and-braces preservation check needs no row re-scan.
    best_move: Phase 117 EVAL-04 — populated from engine result or dedup transplant.
    is_terminal: SEED-044 — True for the post-game terminal-position target. Under
        the post-move convention the eval stored at the LAST played move's row is
        the eval of the position AFTER that move (the terminal position), so the
        terminal board is evaluated as an eval-only donor. A terminal target has
        NO game_positions row of its own (no move was played from it): it is never
        written, never dedup'd, and contributes only its position eval as the
        pos_eval[k+1] donor for the last real row.
    """

    game_id: int
    ply: int
    full_hash: int
    board: chess.Board
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None = None
    is_terminal: bool = False
    ends_game: bool = False
    """SEED-049 — True for the single real (non-terminal) row whose move ENDS the game
    (resulting position is_game_over()). Under post-move storage its after-eval is the
    game-over terminal, which is deliberately unevaluable and never gets a donor, so its
    NULL post-move eval is legitimate — never counted as a hole."""


def _collect_full_ply_targets(
    game_id: int,
    pgn_text: str,
    game_positions_rows: Sequence[tuple[int, int, int | None, int | None]],
    include_terminal: bool = False,
) -> list[_FullPlyEvalTarget]:
    """Collect one target per ply, with an optional terminal eval-donor (EVAL-01, SEED-044).

    game_positions_rows: (ply, full_hash, eval_cp, eval_mate) loaded from DB.

    Per-ply targets snapshot the PRE-PUSH board (the position BEFORE the move at
    that ply), so the engine's eval is the eval OF that position and its best_move
    is the best move FROM it — both position-/decision-keyed. The POST-MOVE storage
    shift (eval stored at row k = eval of the position AFTER move k) is applied
    later, at write time, in `_post_move_eval`.

    include_terminal (SEED-044): when True, append ONE extra terminal target for
    the post-game board (the position after the final push). Under the post-move
    convention the last played move's stored eval is the eval of that terminal
    position, so it must be evaluated. The terminal target has `is_terminal=True`,
    `ply = <number of plies played>` (one past the last real row), and no DB row of
    its own — it is an eval-only donor (never written, never dedup'd). Engine games
    pass include_terminal=True; lichess `%eval` games pass False (their evals are
    preserved, never shifted, so no terminal donor is needed).

    Returns [] on PGN parse failure or None game.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []
    if game is None:
        return []

    # Build ply -> (full_hash, eval_cp, eval_mate) lookup from DB rows
    ply_meta: dict[int, tuple[int, int | None, int | None]] = {
        ply: (fh, cp, mt) for ply, fh, cp, mt in game_positions_rows
    }

    board = game.board()
    targets: list[_FullPlyEvalTarget] = []
    ply_count = 0
    for ply, node in enumerate(game.mainline()):
        ply_count = ply + 1
        meta = ply_meta.get(ply)
        if meta is not None:
            fh, cp, mt = meta
            targets.append(
                _FullPlyEvalTarget(
                    game_id=game_id,
                    ply=ply,
                    full_hash=fh,
                    board=board.copy(),
                    eval_cp=cp,
                    eval_mate=mt,
                )
            )
        board.push(node.move)
    # board is now the terminal position. Under post-move storage it is the
    # after-eval donor for the last played move (SEED-044). full_hash is 0 (unused:
    # terminal targets are excluded from dedup and never written by full_hash).
    #
    # Skip a GAME-OVER terminal (checkmate/stalemate/insufficient material): the
    # engine cannot search a finished position (evaluate_nodes_multipv2 would error
    # or return a degenerate result), and a mating/stalemating final move is the
    # best move, never a flaw to assess. Games that ended by resignation/timeout
    # leave a normal (not game-over) final board, so the last move IS assessable
    # (a pre-resignation blunder gets its after-eval).
    if include_terminal and ply_count > 0 and not board.is_game_over():
        targets.append(
            _FullPlyEvalTarget(
                game_id=game_id,
                ply=ply_count,
                full_hash=0,
                board=board.copy(),
                eval_cp=None,
                eval_mate=None,
                is_terminal=True,
            )
        )
    elif include_terminal and ply_count > 0 and board.is_game_over():
        # SEED-049: the final board is game-over (checkmate/stalemate/insufficient
        # material), which means the last real move was the game-ending move. Its
        # post-move eval is the unevaluable terminal position — legitimately NULL,
        # not a hole. Mark ends_game=True on the last real target (ply = ply_count - 1)
        # so _apply_full_eval_results skips it in the failed_ply_count counter.
        game_ending_ply = ply_count - 1
        for target in reversed(targets):
            if target.ply == game_ending_ply:
                target.ends_game = True
                break
    return targets


async def _fetch_dedup_evals(
    session: AsyncSession,
    full_hashes: Sequence[int],
) -> dict[int, tuple[int | None, int | None, str | None]]:
    """Batch-fetch a position's OWN eval + best_move for opening-region hashes (EVAL-03, D-116-02).

    SEED-053 / D-123.1-05: reads the position-keyed opening_position_eval cache instead
    of the former self-join on game_positions. The cache is a hash-unique relation keyed by
    full_hash, so the lookup collapses to a PK index scan (~1-5 ms) versus the ~8.4 s
    DISTINCT-ON self-join (see CONTEXT.md for EXPLAIN evidence). Column semantics are
    identical to the self-join result: eval_cp/eval_mate are the eval OF the requested
    position and best_move is the engine's decision FROM it.

    Read-side guards (ply <= DEDUP_MAX_PLY, not in flaw_engine_plies, not is_terminal)
    remain entirely in the caller at ~line 1640 — UNCHANGED. This function only changes
    which table backs the lookup.

    Returns {full_hash: (eval_cp, eval_mate, best_move)} for hashes present in the cache.
    """
    if not full_hashes:
        return {}
    result = await session.execute(
        select(
            OpeningPositionEval.full_hash,
            OpeningPositionEval.eval_cp,
            OpeningPositionEval.eval_mate,
            OpeningPositionEval.best_move,
        ).where(OpeningPositionEval.full_hash.in_(full_hashes))
    )
    return {row[0]: (row[1], row[2], row[3]) for row in result.all()}


async def _any_active_import_or_entry_ply_pending(session: AsyncSession) -> bool:
    """True if the full drain should yield to higher-priority work (D-116-11).

    Returns True when:
    (a) any import_job with status IN ('pending', 'in_progress') exists, OR
    (b) any game with evals_completed_at IS NULL exists (entry-ply drain backlog).
    Both checks use existing partial indexes and are sub-millisecond.
    """
    active_import = await session.scalar(
        select(sa.func.count())
        .select_from(ImportJob)
        .where(ImportJob.status.in_(["pending", "in_progress"]))
    )
    if active_import:
        return True
    entry_ply_pending = await session.scalar(
        select(sa.func.count()).select_from(Game).where(Game.evals_completed_at.is_(None)).limit(1)
    )
    return bool(entry_ply_pending)


def _resolve_full_eval(
    target: _FullPlyEvalTarget,
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> tuple[int | None, int | None, str | None, str | None]:
    """Resolve a target's POSITION-keyed eval + decision best_move/pv (pure; WR-04).

    Returns (eval_cp, eval_mate, best_move, pv_string) where eval_cp/eval_mate are
    the eval OF this target's own position (the engine evaluated the pre-push
    board, or the dedup map supplies the same position-keyed value) and
    best_move/pv are the engine's best move + PV FROM this position. This function
    does NOT apply the post-move storage shift — that is done at write time in
    `_post_move_eval` (SEED-044), so the same +1 lives in exactly one place.

    Priority: dedup hit (EVAL-03, opening region only) > engine result >
    (None, None, None, None) hole (D-116-07). pv_string is always None for dedup'd
    positions (the per-flaw PV is only written at flaw-adjacent plies N+1 — D-117-02).
    """
    if not target.is_terminal and target.ply <= _DEDUP_MAX_PLY and target.full_hash in dedup_map:
        eval_cp, eval_mate, best_move = dedup_map[target.full_hash]
        return eval_cp, eval_mate, best_move, None
    return engine_result_map.get(target.ply, (None, None, None, None))


def _post_move_eval(
    pos_eval: dict[int, tuple[int | None, int | None]],
    ply: int,
) -> tuple[int | None, int | None]:
    """Post-move storage shift — the SINGLE site of the +1 (SEED-044).

    Under the post-move convention the eval stored at row `ply` is the eval of
    the position AFTER the move at `ply`, i.e. the eval of the NEXT position
    (`ply + 1`). `pos_eval` is the position-keyed eval map (eval OF each ply's
    position, including the terminal ply that follows the last move). For the
    last real row, `ply + 1` is the terminal position. A missing next-ply eval
    (engine hole at ply+1, or no terminal donor) yields a (None, None) NULL hole.
    """
    return pos_eval.get(ply + 1, (None, None))


async def _batch_update_best_move_rows(
    session: AsyncSession,
    game_id: int,
    bm_rows: list[tuple[int, str]],
) -> None:
    """Emit ONE batched UPDATE for best_move-only rows (FLAWCHESS-6B).

    Used by _apply_full_eval_results for:
    - lichess-eval game plies (best_move only; evals preserved untouched)
    - engine-game plies that have a best_move but a NULL post-move eval (hole rows
      where best_move is still available — written independently of eval, per SEED-044)

    Uses CAST() instead of :: cast syntax: asyncpg's named-param rewrite (`$N`)
    occurs before the server parses the SQL, so `::` adjacent to a `$N` placeholder
    raises a syntax error. CAST() is the portable equivalent.

    Guard: empty input is a no-op (no zero-row VALUES UPDATE is emitted).
    Sequential execute on caller-owned session — no asyncio.gather (CLAUDE.md).
    """
    if not bm_rows:
        return
    params: dict[str, int | str] = {"game_id": game_id}
    values_parts: list[str] = []
    for i, (ply, bm) in enumerate(bm_rows):
        params[f"ply_{i}"] = ply
        params[f"bm_{i}"] = bm
        values_parts.append(f"(CAST(:ply_{i} AS smallint), CAST(:bm_{i} AS varchar))")
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        f"UPDATE game_positions"  # noqa: S608 — no user input; params are bound
        f" SET best_move = v.best_move"
        f" FROM (VALUES {values_sql}) AS v(ply, best_move)"
        f" WHERE game_positions.game_id = :game_id"
        f" AND game_positions.ply = v.ply"
    )
    await session.execute(sql, params)


async def _batch_update_pv_rows(
    session: AsyncSession,
    game_id: int,
    pv_rows: list[tuple[int, str]],
) -> None:
    """Emit ONE batched UPDATE writing pv (principal variation) for the given plies.

    Shared by the live drain (_classify_and_fill_oracle) and the SEED-054 backfill
    (scripts/backfill_best_move_pv.py) so the (game_id, ply) keying is identical by
    construction. pv is unbounded Text (PostgreSQL won't reject it at the column
    level).

    Does NOT catch exceptions — callers decide fault tolerance. The drain wraps the
    call in its own try/except so a PV write failure never aborts the flaw rows +
    oracle counts already written in the same transaction (T-108-04 / WR-01).

    Uses CAST() rather than :: cast syntax for asyncpg compatibility (same reason
    as _batch_update_best_move_rows). Guard: empty input is a no-op (no zero-row
    VALUES UPDATE). Sequential execute on caller-owned session — no asyncio.gather
    (CLAUDE.md).
    """
    if not pv_rows:
        return
    params: dict[str, int | str] = {"game_id": game_id}
    values_parts: list[str] = []
    for i, (ply, pv) in enumerate(pv_rows):
        params[f"ply_{i}"] = ply
        params[f"pv_{i}"] = pv
        values_parts.append(f"(CAST(:ply_{i} AS smallint), CAST(:pv_{i} AS text))")
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        f"UPDATE game_positions"  # noqa: S608 — no user input; params are bound
        f" SET pv = v.pv"
        f" FROM (VALUES {values_sql}) AS v(ply, pv)"
        f" WHERE game_positions.game_id = :game_id"
        f" AND game_positions.ply = v.ply"
    )
    await session.execute(sql, params)


async def _batch_update_eval_rows(
    session: AsyncSession,
    game_id: int,
    eval_rows: list[tuple[int, int | None, int | None, str | None]],
) -> None:
    """Emit ONE batched UPDATE for eval-bearing engine rows (FLAWCHESS-6B).

    Each row carries (ply, eval_cp, eval_mate, best_move). eval_cp/eval_mate are
    always non-NULL (at least one is set) and overwrite unconditionally. best_move
    may be NULL: it is sourced from THIS ply's resolution while the eval is the
    post-move eval of ply+1 (a different resolution), so an eval-bearing row can
    legitimately carry best_move=None. We must NOT clobber a previously-written
    best_move in that case (re-submit / retry path), so best_move is written via
    COALESCE(v.best_move, existing) — exactly matching the pre-batch semantics
    where best_move was only ever written when present (FLAWCHESS-6B).

    Uses CAST() instead of :: cast syntax for asyncpg compatibility (same reason
    as _batch_update_best_move_rows).

    Guard: empty input is a no-op (no zero-row VALUES UPDATE is emitted).
    Sequential execute on caller-owned session — no asyncio.gather (CLAUDE.md).
    """
    if not eval_rows:
        return
    params: dict[str, int | str | None] = {"game_id": game_id}
    values_parts: list[str] = []
    for i, (ply, eval_cp, eval_mate, bm) in enumerate(eval_rows):
        params[f"ply_{i}"] = ply
        params[f"ecp_{i}"] = eval_cp
        params[f"emt_{i}"] = eval_mate
        params[f"bm_{i}"] = bm
        values_parts.append(
            f"(CAST(:ply_{i} AS smallint),"
            f" CAST(:ecp_{i} AS smallint),"
            f" CAST(:emt_{i} AS smallint),"
            f" CAST(:bm_{i} AS varchar))"
        )
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        f"UPDATE game_positions"  # noqa: S608 — no user input; params are bound
        f" SET eval_cp = v.eval_cp, eval_mate = v.eval_mate,"
        f" best_move = COALESCE(v.best_move, game_positions.best_move)"
        f" FROM (VALUES {values_sql}) AS v(ply, eval_cp, eval_mate, best_move)"
        f" WHERE game_positions.game_id = :game_id"
        f" AND game_positions.ply = v.ply"
    )
    await session.execute(sql, params)


async def _apply_full_eval_results(
    session: AsyncSession,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    is_lichess_eval_game: bool,
) -> int:
    """Write POST-MOVE evals + best_move to GamePosition rows (WR-04; SEED-044).

    Batched single-round-trip writes replace the former per-row UPDATE loop
    (FLAWCHESS-6B N+1 fix). UPDATEs run sequentially against the caller-owned
    session (CLAUDE.md hard rule: AsyncSession is not safe under asyncio.gather);
    the caller commits.

    Convention (SEED-044): a row stores the eval of the position AFTER its move
    (post-move), matching lichess `%eval` and the flaw classifier. We resolve a
    position-keyed eval for every target (incl. the terminal eval-donor), then
    write row k's eval from `pos_eval[k + 1]` via `_post_move_eval` — the single
    +1 shift site. best_move stays decision-ply-keyed (best move FROM row k's
    position), so it is NOT shifted.

    is_lichess_eval_game gate (lichess_evals_at IS NOT NULL, D-117-07):
    - is_lichess_eval_game=True: lichess %evals are already post-move and
      authoritative — NEVER shifted or overwritten. Only best_move
      (engine-supplied; lichess lacks it) is written, at the flaw-adjacent plies
      that reached the write phase (WR-01 / D-117-13). SEED-044: un-annotated
      lichess plies are left NULL rather than filled with a pre-push engine eval
      (which mixed conventions in-game).
    - is_lichess_eval_game=False: engine games get the full post-move eval written.

    Returns the number of failed (NULL-hole) engine-game plies. Sentry reporting
    is the caller's responsibility — ONE aggregated event per game, never per ply
    (WR-05).
    """
    # Position-keyed resolve for every target (incl. the terminal eval-donor),
    # then the post-move +1 shift at write time (SEED-044).
    pos_eval: dict[int, tuple[int | None, int | None]] = {}
    best_move_by_ply: dict[int, str | None] = {}
    for target in targets:
        eval_cp, eval_mate, best_move, _pv_string = _resolve_full_eval(
            target, dedup_map, engine_result_map
        )
        # _pv_string intentionally discarded here: pv is written ONLY at flaw-adjacent
        # plies (ply = flaw_ply + 1) in _classify_and_fill_oracle below (D-117-02).
        pos_eval[target.ply] = (eval_cp, eval_mate)
        if not target.is_terminal:
            best_move_by_ply[target.ply] = best_move

    # Collect write-rows in one pass; emit batched UPDATEs after the loop.
    # Two groups (FLAWCHESS-6B):
    #   bm_only_rows  — lichess plies (best_move-only) + engine hole-rows w/ best_move
    #   eval_rows     — engine plies with a resolved eval (eval_cp/eval_mate + best_move)
    # failed_ply_count is accumulated in the same pass (pure Python; no DB I/O here).
    game_id = next((t.game_id for t in targets if not t.is_terminal), 0)
    bm_only_rows: list[tuple[int, str]] = []
    eval_rows: list[tuple[int, int | None, int | None, str | None]] = []
    failed_ply_count = 0

    for target in targets:
        if target.is_terminal:
            # Eval-only donor: its eval already lives in pos_eval as the last
            # real row's after-eval. It has no game_positions row to write.
            continue

        ply = target.ply
        best_move = best_move_by_ply.get(ply)

        if is_lichess_eval_game:
            # Preserve lichess %evals (post-move, authoritative); write best_move only.
            if best_move is not None:
                bm_only_rows.append((ply, best_move))
            continue

        # Engine game: store the POST-MOVE eval (eval of the position AFTER this
        # move = pos_eval[ply + 1]); best_move stays decision-ply-keyed. best_move is
        # written whenever available, INDEPENDENT of the eval — an engine hole at the
        # after-position (ply + 1) must not drop this row's own best_move (SEED-044).
        eval_cp, eval_mate = _post_move_eval(pos_eval, ply)

        if eval_cp is None and eval_mate is None:
            if target.ends_game:
                # SEED-049: the after-position is the game-over terminal — deliberately
                # unevaluable (no legal moves; engine skip in _collect_full_ply_targets
                # already omits the terminal donor when is_game_over()). This NULL is
                # legitimate, not a transient Stockfish timeout. Do NOT count it as a
                # hole; the row is written normally (eval stays NULL, best_move if set).
                if best_move is not None:
                    bm_only_rows.append((ply, best_move))
            else:
                # D-116-07: engine hole at the after-position — leave the eval NULL;
                # counted for the caller's per-game aggregated Sentry event (WR-05).
                failed_ply_count += 1
                if best_move is not None:
                    bm_only_rows.append((ply, best_move))
        else:
            # Eval resolved: include best_move in the eval group (may be None — writing
            # NULL over NULL is safe; both values come from the same target pass so no
            # in-flight best_move is discarded).
            eval_rows.append((ply, eval_cp, eval_mate, best_move))

    # Emit batched UPDATEs — O(1) round-trips per game (FLAWCHESS-6B).
    # Empty lists are guarded inside each helper (no zero-row VALUES statement).
    await _batch_update_best_move_rows(session, game_id, bm_only_rows)
    await _batch_update_eval_rows(session, game_id, eval_rows)

    return failed_ply_count


async def _mark_full_evals_completed(session: AsyncSession, game_id: int) -> None:
    """Mark one game as fully analyzed (EVAL-05, Phase 119 SEED-045).

    Called only when no non-terminal holes remain (failed_ply_count == 0) OR when
    full_eval_attempts reaches MAX_EVAL_ATTEMPTS (cap path). D-116-07 invariant
    preserved: a deterministically-unevaluable ply cannot loop forever — the cap
    stamps anyway after MAX_EVAL_ATTEMPTS ticks. One UPDATE per game (single tick).
    """
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == game_id)
        .values(full_evals_completed_at=now_ts)
    )
    await session.execute(stmt)


async def _mark_full_pv_completed(session: AsyncSession, game_id: int) -> None:
    """Mark one game's best_move/PV as written (D-117-12 second completion dimension).

    Mirrors _mark_full_evals_completed. Set after best_move is written for all
    plies and flaw PVs are written at flaw-adjacent positions.
    """
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == game_id)
        .values(full_pv_completed_at=now_ts)
    )
    await session.execute(stmt)


async def _classify_and_fill_oracle(
    session: AsyncSession,
    game_id: int,
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> None:
    """Classify game_flaws and fill oracle count columns for one engine-analyzed game (EVAL-06).

    Runs inside the Step 4 write session (same transaction as _apply_full_eval_results)
    so flaw rows, oracle counts, and flaw PVs commit atomically with the evals (T-117-11).

    Steps:
    1. Load game + ordered positions from the write session.
    2. classify_game_flaws — emits FlawRecord for M+B across both players.
    3. delete_flaws_for_game + bulk_insert_game_flaws — the full/oracle pass is
       authoritative and fully REPLACES any entry-pass rows (see tactic-tagging
       note below).
    4. count_game_severities × 2 (white then black) to get inaccuracy counts.
    5. UPDATE games oracle columns (white/black inaccuracies/mistakes/blunders).
    6. For each FlawRecord at ply N, write game_positions.pv at ply N+1 (D-117-02,
       Pitfall 4 off-by-one: pv belongs to the position AFTER the flaw was played).

    Errors in bulk_insert_game_flaws and the oracle-count UPDATE are intentionally
    NOT caught here — they must propagate to the caller so the write-session
    transaction is aborted and the completion markers (_mark_full_evals_completed /
    _mark_full_pv_completed) are NOT committed.  Only the per-flaw PV writes are
    individually fault-tolerant (a single bad PV row must not abort the whole game).

    T-108-04 still applies at the drain-tick level: _full_drain_tick wraps the entire
    write phase in its own exception boundary so one bad game never aborts the drain.
    """
    game_result = await session.execute(select(Game).where(Game.id == game_id))
    game = game_result.scalar_one_or_none()
    if game is None:
        return

    positions_result = await session.execute(
        select(GamePosition)
        .where(
            GamePosition.game_id == game.id,
            GamePosition.user_id == game.user_id,
        )
        .order_by(GamePosition.ply)
    )
    positions = list(positions_result.scalars().all())

    # Live tactic tagging (260618-aiq): the freshly-computed PVs in
    # engine_result_map are NOT yet written to game_positions at this point (the
    # batched PV UPDATE below runs after classify). _detect_tactic_for_flaw reads
    # the PV at flaw_ply+1, so without this override every live classify would see
    # pv=NULL and tag tactic_motif=NULL until a later backfill_flaws.py run. Pass
    # the in-memory PVs (ply -> pv_string) so the drain tags tactics on the fly.
    pv_by_ply: dict[int, str] = {
        ply: entry[3] for ply, entry in engine_result_map.items() if entry[3] is not None
    }

    flaw_result = classify_game_flaws(game, positions, pv_by_ply=pv_by_ply)
    if "reason" in flaw_result:
        # GameNotAnalyzed: insufficient eval coverage — skip.
        return

    flaw_list = flaw_result  # list[FlawRecord]

    # Delete-then-insert (not ON CONFLICT DO NOTHING): the full/oracle pass is
    # authoritative and must REPLACE any rows written by the entry pass. Lichess
    # "covered" games (full %eval at import) get flaw rows from
    # _classify_and_insert_flaws (import_service.py / entry-submit) BEFORE this
    # runs — those rows carry NULL tactic columns because the entry pass has no
    # PVs. A plain ON CONFLICT DO NOTHING would silently drop these fresh
    # tactic-bearing rows, so the live PVs above would never reach game_flaws
    # (tactic_motif stayed NULL until a backfill_flaws.py run). Deleting first
    # also lets our deeper Stockfish evals reclassify the flaw SET (lichess %eval
    # can disagree on severity / which plies are flaws) instead of leaving stale
    # entry-pass rows behind. Same write transaction → atomic with the evals.
    await delete_flaws_for_game(session, game_id=game.id, user_id=game.user_id)

    # Insert M+B flaw rows.
    # Bug fix (WR-01): DB errors here MUST propagate — a failure at this point
    # means no flaw rows were inserted; catching it would let the caller commit
    # the completion markers and permanently mark the game done with no flaws.
    rows = [
        flaw_record_to_row(user_id=game.user_id, game_id=game.id, flaw=flaw) for flaw in flaw_list
    ]
    await bulk_insert_game_flaws(session, rows)

    # Oracle count columns: count_game_severities reads only game.user_color.
    # Call twice with a swapped-color view (no DB I/O in count_game_severities —
    # it's pure Python over already-loaded positions).
    counts_white = count_game_severities(
        _GameColorView(game, "white"),  # ty: ignore[invalid-argument-type]  # reads only user_color
        positions,
    )
    counts_black = count_game_severities(
        _GameColorView(game, "black"),  # ty: ignore[invalid-argument-type]  # reads only user_color
        positions,
    )

    # Use "reason" key as the TypedDict discriminator (isinstance on TypedDict raises TypeError).
    if "reason" in counts_white or "reason" in counts_black:
        # Shouldn't happen (same coverage gate as classify_game_flaws), but be defensive.
        return

    games_table = Game.__table__
    # Bug fix (WR-01): DB errors here MUST propagate — if the oracle-count UPDATE
    # fails the game must be retried, not silently marked complete with NULL counts.
    await session.execute(
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == game_id)
        .values(
            white_inaccuracies=counts_white["inaccuracy"],
            white_mistakes=counts_white["mistake"],
            white_blunders=counts_white["blunder"],
            black_inaccuracies=counts_black["inaccuracy"],
            black_mistakes=counts_black["mistake"],
            black_blunders=counts_black["blunder"],
        )
    )

    # Flaw PV write (D-117-02 / SEED-054): for each FlawRecord at ply N, write pv at
    # BOTH ply N and ply N+1:
    #   - ply N    = the ideal-continuation line from the pre-blunder decision board
    #                (latent until a frontend surface renders it — SEED-054 Part 2).
    #   - ply N+1  = the refutation line from the post-blunder board (D-117-02, the
    #                SEED-039 tactic-motif input).
    # Each pv_string comes from engine_result_map at its OWN ply. For lichess games
    # ply N is engine-evaluated thanks to _flaw_engine_plies (SEED-054 Part 1); for
    # chess.com every ply already ran. Opening dedup-transplanted plies are absent
    # from engine_result_map → pv stays NULL there (acceptable per SEED-054). Deduped
    # by ply: consecutive flaws can make one flaw's ply N collide with another's N+1.
    #
    # FLAWCHESS-6B: collect surviving (ply, pv_string) pairs, then ONE batched UPDATE
    # via _batch_update_pv_rows.
    #
    # Fault tolerance rationale: batching trades per-row isolation for one round-trip —
    # acceptable because pv is unbounded Text (PostgreSQL won't reject it at the column
    # level), so the realistic failure mode is a DB connection error that would have
    # invalidated the whole session anyway, not a single bad row. The surviving rows
    # commit atomically with the flaw rows and oracle counts above (T-117-11). If the
    # batched execute fails, flaw rows + oracle counts are NOT rolled back — both the
    # old code and this block are inside the write_session transaction; asyncpg-level
    # errors invalidate the whole session regardless.
    flaw_pv_by_ply: dict[int, str] = {}
    for flaw in flaw_list:
        flaw_ply_val: int = flaw["ply"]
        for cand_ply in (flaw_ply_val, flaw_ply_val + 1):
            if cand_ply in flaw_pv_by_ply:
                continue
            engine_entry = engine_result_map.get(cand_ply)
            if engine_entry is None:
                continue
            _cp, _mt, _bm, pv_string = engine_entry
            if pv_string is None:
                continue
            flaw_pv_by_ply[cand_ply] = pv_string

    if flaw_pv_by_ply:
        try:
            await _batch_update_pv_rows(session, game_id, list(flaw_pv_by_ply.items()))
        except Exception as exc:
            # T-108-04 / WR-01: PV write failure must not abort flaw rows + oracle
            # counts already written above. Capture for visibility without embedding
            # variables in the message string (CLAUDE.md Sentry grouping rule).
            sentry_sdk.set_context(
                "classify_oracle",
                {"game_id": game_id},
            )
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_exception(exc)


async def _flaw_engine_plies(session: AsyncSession, game_id: int) -> set[int]:
    """Pre-classify a lichess-eval game's flaws to find plies needing an engine pass (D-117-13 / SEED-054).

    Lichess-eval games (is_lichess_eval_game=True) carry a lichess %eval on
    (nearly) every ply, so the is_lichess_eval_game target filter in
    _full_drain_tick would otherwise drop every flaw ply before the engine
    gather — and lichess supplies %eval but NO principal variation and NO
    best_move. The observed result (prod sanity check ~1 h after the Phase 117
    deploy) was 0% flaw-PV coverage for analyzed lichess games: every flaw's
    refutation line (the SEED-039 input) was missing.

    Fix: classify flaws up front from the already-stored %evals — the SAME inputs
    the write-time classify in _classify_and_fill_oracle uses — and return the set
    of {flaw_ply, flaw_ply + 1} plies. The caller exempts these from the
    eval-preservation filter and from the opening dedup so the engine evaluates
    exactly those positions, while the write path still preserves the lichess
    %eval (D-116-04). Covers BOTH players' flaws (classify_game_flaws is two-sided
    per D-06), matching the write-time PV loop.

    Two plies per flaw (SEED-054):
    - flaw_ply: the pre-blunder decision board → best_move (the better alternative
      the Flaw/Library arrow renders, read at game_positions[flaw_ply].best_move) +
      the ideal-continuation pv at the decision ply. This was NULL for lichess
      games before SEED-054 because the engine only ran at flaw_ply + 1.
    - flaw_ply + 1: the post-blunder board → the refutation pv (D-117-02, the
      SEED-039 tactic-motif input).

    Returns an empty set when the game is missing or classification reports
    insufficient coverage (GameNotAnalyzed) — the caller then falls back to the
    prior filter behavior (no extra engine calls). Engine-source (non-analyzed)
    games never call this: their evals aren't computed at load time, and they
    already get full-game PV coverage from the unfiltered engine pass.
    """
    game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
    if game is None:
        return set()
    positions_result = await session.execute(
        select(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.user_id == game.user_id)
        .order_by(GamePosition.ply)
    )
    positions = list(positions_result.scalars().all())
    flaw_result = classify_game_flaws(game, positions)
    if "reason" in flaw_result:
        # GameNotAnalyzed: insufficient eval coverage — fall back to prior filter.
        return set()
    plies: set[int] = set()
    for flaw in flaw_result:
        plies.add(flaw["ply"])
        plies.add(flaw["ply"] + 1)
    return plies


def _reconstruct_pos_eval(
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> dict[int, tuple[int | None, int | None]]:
    """Position-keyed eval map (eval OF each ply's position) assembled in-memory from
    the just-completed gather + the dedup transplants (SEED-056).

    Mirrors what _apply_full_eval_results will write, but with no DB round-trip, so the
    drain can pre-classify an engine game's flaws BEFORE the write session. Opening
    plies are mutually exclusive across the two maps by construction (engine_targets in
    _full_drain_tick excludes any opening ply with a dedup hit), so source precedence
    never matters here.
    """
    pos_eval: dict[int, tuple[int | None, int | None]] = {}
    for t in targets:
        engine_entry = engine_result_map.get(t.ply)
        if engine_entry is not None:
            pos_eval[t.ply] = (engine_entry[0], engine_entry[1])
        elif not t.is_terminal and t.ply <= _DEDUP_MAX_PLY and t.full_hash in dedup_map:
            cp, mate, _bm = dedup_map[t.full_hash]
            pos_eval[t.ply] = (cp, mate)
    return pos_eval


async def _missing_flaw_pv_targets(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> list[_FullPlyEvalTarget]:
    """SEED-056: find engine-game flaw plies that took a pv-less opening dedup transplant.

    The lichess path pre-classifies flaws from stored %evals up front (_flaw_engine_plies)
    and exempts {flaw_ply, flaw_ply + 1} from dedup so they always get a real engine pass
    (PV + best_move). Fresh engine games can't do that — they have no evals until AFTER
    the gather — so an opening-region flaw ply whose full_hash matched a dedup donor gets
    an eval-only transplant with NO pv. The flaw is registered but un-taggable (no
    refutation line for the SEED-039 motif classifier), and the better-alternative PV at
    flaw_ply is lost too.

    Fix: once the gather is done we DO know every ply's eval (engine_result_map for
    engine plies, dedup_map for transplanted ones). Reconstruct the post-move evals
    in-memory, classify, and return the dedup-transplanted {flaw_ply, flaw_ply + 1}
    targets that still lack a pv. The caller runs a tiny second engine gather on these
    boards and merges the results back into engine_result_map before the write session,
    so classify + the PV write pick the pv up exactly as for any engine-evaluated ply.

    Returns [] when the game has no flaws, no eval coverage, or no pv-less opening flaw
    plies — the common case (the prod gap is ~0.3% of opening-region engine-game flaws).
    """
    pos_eval = _reconstruct_pos_eval(targets, dedup_map, engine_result_map)
    async with async_session_maker() as session:
        game_result = await session.execute(select(Game).where(Game.id == game_id))
        game = game_result.scalar_one_or_none()
        if game is None:
            return []
        positions_result = await session.execute(
            select(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.user_id == game.user_id)
            .order_by(GamePosition.ply)
        )
        positions = list(positions_result.scalars().all())
    # Overlay the reconstructed post-move evals (engine games have NULL evals in the DB
    # until the write session runs). _post_move_eval is the single source of the +1 shift.
    for pos in positions:
        cp, mate = _post_move_eval(pos_eval, pos.ply)
        pos.eval_cp = cp
        pos.eval_mate = mate

    flaw_result = classify_game_flaws(game, positions)
    if "reason" in flaw_result:
        return []

    targets_by_ply = {t.ply: t for t in targets}
    need: dict[int, _FullPlyEvalTarget] = {}
    for flaw in flaw_result:
        flaw_ply_val: int = flaw["ply"]
        for cand_ply in (flaw_ply_val, flaw_ply_val + 1):
            if cand_ply in need:
                continue
            engine_entry = engine_result_map.get(cand_ply)
            if engine_entry is not None and engine_entry[3] is not None:
                continue  # already engine-evaluated with a pv
            target = targets_by_ply.get(cand_ply)
            if target is None or target.is_terminal:
                continue
            # Only the opening dedup region is in scope: a transplanted ply has its eval
            # but no pv. Engine-region flaw plies always get a real pass already, and an
            # engine HOLE (eval failed) would just fail the re-pass too — out of scope.
            if cand_ply <= _DEDUP_MAX_PLY and target.full_hash in dedup_map:
                need[cand_ply] = target
    return list(need.values())


async def _fill_engine_game_flaw_pvs(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    is_lichess_eval_game: bool,
) -> None:
    """SEED-056: targeted second engine pass for pv-less opening flaw plies (engine games).

    Engine games can't pre-know their flaws (no evals until after the gather), so an
    opening-region flaw ply that matched a dedup donor took an eval-only transplant with
    NO pv — registered but un-taggable. This classifies from the in-memory gather results,
    finds those pv-less flaw plies, runs ONE more gather over just their boards, and merges
    the pv back into engine_result_map (mutated in place) so the write-session classify
    (tactic tagging) and the pv write pick it up like any engine-evaluated ply.

    No-op for lichess games (they pre-classify up front via _flaw_engine_plies) and when
    there were no opening dedup hits (no possible gap). MUST be called with NO session open
    — it runs asyncio.gather (CLAUDE.md hard rule).
    """
    if is_lichess_eval_game:
        return
    has_opening_dedup = any(
        not t.is_terminal and t.ply <= _DEDUP_MAX_PLY and t.full_hash in dedup_map for t in targets
    )
    if not has_opening_dedup:
        return
    pv_gap_targets = await _missing_flaw_pv_targets(game_id, targets, dedup_map, engine_result_map)
    if not pv_gap_targets:
        return
    # Phase 142: switch to evaluate_nodes_multipv2 so the PV-recovery pass also returns
    # multipv=2 data. Slice to 4-tuple before writing to engine_result_map (which is keyed
    # as dict[int, tuple[...*4]] to avoid blast radius on _apply_full_eval_results).
    pv_gap_results: Sequence[
        tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None]
    ] = await asyncio.gather(
        *(engine_service.evaluate_nodes_multipv2(t.board) for t in pv_gap_targets)
    )
    for t, res in zip(pv_gap_targets, pv_gap_results, strict=True):
        # Only merge a real pv — a failed re-pass (pv None) leaves the status quo (eval
        # still served from the dedup transplant; pv stays NULL).
        if res[3] is not None:
            engine_result_map[t.ply] = (res[0], res[1], res[2], res[3])


async def _fill_engine_game_flaw_second_best(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    second_best_map: dict[int, tuple[int | None, int | None, str | None]],
    is_lichess_eval_game: bool,
) -> None:
    """D-05 / Phase 142 MPV-02: recover node-0 second-best for flaw plies that used
    the opening dedup cache (no engine second-best in second_best_map for those plies).

    Mirrors _fill_engine_game_flaw_pvs (SEED-056): no-op for lichess games and when
    there is no opening dedup. Reuses _missing_flaw_pv_targets to find the same
    dedup-transplanted flaw plies. Mutates second_best_map in place. MUST be called
    with NO session open — runs asyncio.gather (CLAUDE.md hard rule).
    """
    if is_lichess_eval_game:
        return
    has_opening_dedup = any(
        not t.is_terminal and t.ply <= _DEDUP_MAX_PLY and t.full_hash in dedup_map for t in targets
    )
    if not has_opening_dedup:
        return
    # Find flaw-ply targets in the dedup region — the same set as pv-less gap targets.
    gap_targets = await _missing_flaw_pv_targets(game_id, targets, dedup_map, engine_result_map)
    if not gap_targets:
        return
    # Only recover plies still absent from second_best_map (avoid redundant engine calls).
    missing = [t for t in gap_targets if t.ply not in second_best_map]
    if not missing:
        return
    gap_results: Sequence[
        tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None]
    ] = await asyncio.gather(*(engine_service.evaluate_nodes_multipv2(t.board) for t in missing))
    for t, res in zip(missing, gap_results, strict=True):
        second_cp, second_mate, second_uci = res[4], res[5], res[6]
        # Include valid second-best data only (not engine failure). second_uci is str
        # when the engine ran: "" = single-legal-move sentinel, non-empty = real second move.
        if second_cp is not None or second_uci is not None:
            second_best_map[t.ply] = (second_cp, second_mate, second_uci)


def _walk_pv_boards(
    start_board: chess.Board,
    pv_string: str | None,
    cap: int,
) -> list[chess.Board]:
    """Phase 142 MPV-02: return boards at each PV node (Option B server-side walk).

    Yields independent board copies: node 0 = copy of start_board, node k = position
    after k PV moves. Stops when a move is illegal, a UCI is malformed, or cap nodes
    are reached (cap limits nodes 1..N, so the list has at most cap+1 entries).
    """
    boards: list[chess.Board] = [start_board.copy()]
    if not pv_string:
        return boards
    for move_uci in pv_string.split()[:cap]:
        try:
            move = chess.Move.from_uci(move_uci)
            if not boards[-1].is_legal(move):
                break
            next_board = boards[-1].copy()
            next_board.push(move)
            boards.append(next_board)
        except (ValueError, AssertionError):
            break
    return boards


def _build_line_blobs(
    flaw_ply: int,
    line: str,
    walk: list[chess.Board],
    pos_eval: dict[int, tuple[int | None, int | None]],
    second_best_map: dict[int, tuple[int | None, int | None, str | None]],
    node_eval: dict[
        tuple[int, str, int],
        tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None],
    ],
) -> list[PvNode]:
    """Phase 142 MPV-02: assemble PvNode list for one line (allowed or missed) of a flaw.

    Node 0 evals come from pos_eval + second_best_map (no engine call needed).
    Nodes 1..N come from node_eval (batch-gathered in _build_flaw_multipv2_blobs).
    su='' is the no-second-move sentinel (Pitfall 3: never None in PvNode).
    """
    if not walk:
        return []
    nodes: list[PvNode] = []
    node0_ply = flaw_ply if line == "missed" else flaw_ply + 1
    best_cp, best_mate = pos_eval.get(node0_ply, (None, None))
    second = second_best_map.get(node0_ply)
    scp, smt, su_raw = second if second else (None, None, "")
    su: str = su_raw if su_raw is not None else ""
    nodes.append(PvNode(b=best_cp, bm=best_mate, s=scp, sm=smt, su=su))
    for k in range(1, len(walk)):
        res = node_eval.get((flaw_ply, line, k))
        if res is None:
            break
        # su must be str (Pitfall 3): engine failure yields (None,)*7 → res[6]=None → "".
        su_k: str = res[6] if res[6] is not None else ""
        nodes.append(PvNode(b=res[0], bm=res[1], s=res[4], sm=res[5], su=su_k))
    return nodes


async def _build_flaw_multipv2_blobs(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    second_best_map: dict[int, tuple[int | None, int | None, str | None]],
) -> dict[int, tuple[list[PvNode], list[PvNode]]]:
    """Phase 142 MPV-02: build PvNode blobs for the allowed/missed lines of each flaw.

    Loads game + positions (own read session, closed before gather), overlays in-memory
    evals (same pattern as _missing_flaw_pv_targets), classifies flaws, walks each
    flaw's PV using _walk_pv_boards, then evaluates ALL continuation nodes (1..N) across
    all flaws and both lines in ONE asyncio.gather. MUST be called with NO session open
    (CLAUDE.md hard rule). Returns {} on DB miss or no flaws.

    Return type: dict[flaw_ply -> (allowed_blobs, missed_blobs)].
    Node 0 of missed = position at flaw_ply; node 0 of allowed = position at flaw_ply + 1.
    """
    pos_eval = _reconstruct_pos_eval(targets, dedup_map, engine_result_map)
    targets_by_ply = {t.ply: t for t in targets}

    async with async_session_maker() as session:
        game = await session.scalar(select(Game).where(Game.id == game_id))
        if game is None:
            return {}
        positions_result = await session.execute(
            select(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.user_id == game.user_id)
            .order_by(GamePosition.ply)
        )
        positions = list(positions_result.scalars().all())

    # Overlay in-memory evals (same as _missing_flaw_pv_targets) so classify_game_flaws
    # sees the newly-computed evals (not the NULLs still in the DB at this point).
    for pos in positions:
        cp, mate = _post_move_eval(pos_eval, pos.ply)
        pos.eval_cp = cp
        pos.eval_mate = mate

    flaw_result = classify_game_flaws(game, positions)
    if "reason" in flaw_result:
        return {}

    cap = engine_service.PV_CAP_PLIES

    # Collect boards for continuation nodes (k >= 1) across all flaws and both lines.
    # Batching into one gather avoids repeated session opens (CLAUDE.md).
    gather_boards: list[chess.Board] = []
    gather_keys: list[tuple[int, str, int]] = []  # (flaw_ply, "allowed"|"missed", node_k)
    walks: dict[tuple[int, str], list[chess.Board]] = {}

    for flaw in flaw_result:
        flaw_ply: int = flaw["ply"]
        if flaw_ply not in targets_by_ply:
            continue

        # Missed line: PV walk from the flaw position (board at flaw_ply).
        board_missed = targets_by_ply[flaw_ply].board.copy()
        pv_missed = engine_result_map.get(flaw_ply, (None, None, None, None))[3]
        missed_walk = _walk_pv_boards(board_missed, pv_missed, cap)
        walks[(flaw_ply, "missed")] = missed_walk
        for k, b in enumerate(missed_walk[1:], 1):
            gather_boards.append(b)
            gather_keys.append((flaw_ply, "missed", k))

        # Allowed line: PV walk from the position after the flaw move (board at flaw_ply + 1).
        allowed_start = flaw_ply + 1
        if allowed_start not in targets_by_ply:
            walks[(flaw_ply, "allowed")] = []
            continue
        board_allowed = targets_by_ply[allowed_start].board.copy()
        pv_allowed = engine_result_map.get(allowed_start, (None, None, None, None))[3]
        allowed_walk = _walk_pv_boards(board_allowed, pv_allowed, cap)
        walks[(flaw_ply, "allowed")] = allowed_walk
        for k, b in enumerate(allowed_walk[1:], 1):
            gather_boards.append(b)
            gather_keys.append((flaw_ply, "allowed", k))

    # Evaluate all continuation boards in one gather (NO session open — CLAUDE.md hard rule).
    continuation_results: Sequence[
        tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None]
    ]
    if gather_boards:
        continuation_results = await asyncio.gather(
            *(engine_service.evaluate_nodes_multipv2(b) for b in gather_boards)
        )
    else:
        continuation_results = []

    node_eval: dict[
        tuple[int, str, int],
        tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None],
    ] = {}
    for key, res in zip(gather_keys, continuation_results, strict=True):
        node_eval[key] = res

    # Assemble PvNode blobs for each flaw.
    blobs: dict[int, tuple[list[PvNode], list[PvNode]]] = {}
    for flaw in flaw_result:
        flaw_ply = flaw["ply"]
        allowed = _build_line_blobs(
            flaw_ply,
            "allowed",
            walks.get((flaw_ply, "allowed"), []),
            pos_eval,
            second_best_map,
            node_eval,
        )
        missed = _build_line_blobs(
            flaw_ply,
            "missed",
            walks.get((flaw_ply, "missed"), []),
            pos_eval,
            second_best_map,
            node_eval,
        )
        if allowed or missed:
            blobs[flaw_ply] = (allowed, missed)
    return blobs


async def _batch_update_flaw_pv_lines(
    session: AsyncSession,
    game_id: int,
    blob_map: dict[int, tuple[list[PvNode], list[PvNode]]],
) -> None:
    """Phase 142 MPV-02: write allowed_pv_lines + missed_pv_lines for each flaw ply.

    One batched UPDATE mirroring _batch_update_pv_rows: CAST(:param AS jsonb) syntax for
    asyncpg compatibility (not :: cast). Does NOT catch exceptions — caller decides fault
    tolerance. Guard: empty blob_map is a no-op.
    """
    if not blob_map:
        return
    params: dict[str, Any] = {"game_id": game_id}
    values_parts: list[str] = []
    for i, (ply, (allowed_blobs, missed_blobs)) in enumerate(blob_map.items()):
        params[f"ply_{i}"] = ply
        params[f"allowed_{i}"] = json.dumps(allowed_blobs)
        params[f"missed_{i}"] = json.dumps(missed_blobs)
        values_parts.append(
            f"(CAST(:ply_{i} AS smallint), CAST(:allowed_{i} AS jsonb), CAST(:missed_{i} AS jsonb))"
        )
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        f"UPDATE game_flaws"  # noqa: S608 — no user input; params are bound
        f" SET allowed_pv_lines = v.allowed_pv_lines,"
        f"     missed_pv_lines = v.missed_pv_lines"
        f" FROM (VALUES {values_sql}) AS v(ply, allowed_pv_lines, missed_pv_lines)"
        f" WHERE game_flaws.game_id = :game_id"
        f" AND game_flaws.ply = v.ply"
    )
    await session.execute(sql, params)


async def _run_multipv2_pass(
    session: AsyncSession,
    game_id: int,
    flaw_pv_blobs: dict[int, tuple[list[PvNode], list[PvNode]]],
) -> None:
    """Phase 142 MPV-02: write PvNode blobs to game_flaws inside the write session.

    Wrapper around _batch_update_flaw_pv_lines that enforces write-session discipline
    (Pitfall 5: must run in the same transaction as _classify_and_fill_oracle so flaw rows
    exist before the UPDATE). No-op when flaw_pv_blobs is empty.
    """
    if not flaw_pv_blobs:
        return
    await _batch_update_flaw_pv_lines(session, game_id, flaw_pv_blobs)


# Minimal duck-typed view so count_game_severities can be called with a
# synthetic user_color without mutating the ORM Game object.
class _GameColorView:
    """Provides the user_color attribute for count_game_severities (D-117-08).

    count_game_severities reads only game.user_color; this thin wrapper avoids
    mutating the ORM object and avoids deepcopy overhead. Named with a leading
    underscore — internal to eval_drain, not exported.
    """

    def __init__(self, game: Game, user_color: str) -> None:
        self._game = game
        self.user_color = user_color

    def __getattr__(self, name: str) -> object:
        return getattr(self._game, name)


# Module-level set for per-user flaw completion signals (D-117-11).
# Phase 118 wires real cache invalidation against this set. For Phase 117,
# it is a lightweight append-only set that future cache middleware can poll.
_recently_flaw_completed_users: set[int] = set()


def _signal_flaw_completion(user_id: int) -> None:
    """Mark a user as having newly-completed flaw analysis (D-117-11 hook).

    Phase 117: no-op beyond a set insert. Phase 118 will wire cache
    invalidation here (debounced per-user asyncio.Task pattern).
    The set is intentionally not bounded — at 8.4k games/day and ~few hundred
    users, it stays small in practice.
    """
    _recently_flaw_completed_users.add(user_id)


# ---------------------------------------------------------------------------
# Lifted eval helpers — Phase 91: lifted from import_service.py for the
# cold-drain lane. The originals in import_service.py are removed in Plan 91-03.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _EvalTarget:
    """One row scheduled for engine evaluation in the cold-drain eval pass.

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

    Collected up-front across all games in a drain batch so the per-eval
    asyncio.gather() can fan out to every Stockfish worker in the module-level
    pool. Without batching the gather, a multi-worker pool would still serve
    only one in-flight evaluation at a time.
    """

    game_id: int
    ply: int
    eval_kind: Literal["middlegame_entry", "endgame_span_entry"]
    endgame_class: int | None  # None for middlegame; int for endgame span entry
    board: chess.Board


# A "target spec" describes one entry ply that needs a Stockfish eval. The
# per-game helper builds these from PlyData first (no PGN parsing), then in a
# single mainline walk snapshots board state at each target's ply.
@dataclass(slots=True, frozen=True)
class _TargetSpec:
    ply: int
    eval_kind: Literal["middlegame_entry", "endgame_span_entry"]
    endgame_class: int | None


def _collect_target_specs(plies_list: Sequence[PlyData]) -> list[_TargetSpec]:
    """Pure: derive the (ply, eval_kind, endgame_class) tuples that need eval.

    Skips plies where lichess %eval already populated eval_cp or eval_mate
    (T-78-17). At most one middlegame entry per game (D-79-08). Endgame spans
    are split into contiguous-ply islands per class; each island contributes
    one entry ply.
    """
    specs: list[_TargetSpec] = []

    # Midgame entry: MIN(ply) where phase == 1, unless already covered.
    midgame_entries = [pd for pd in plies_list if pd["phase"] == 1]
    if midgame_entries:
        mid_pd = min(midgame_entries, key=lambda p: p["ply"])
        if mid_pd["eval_cp"] is None and mid_pd["eval_mate"] is None:
            specs.append(
                _TargetSpec(
                    ply=mid_pd["ply"],
                    eval_kind="middlegame_entry",
                    endgame_class=None,
                )
            )

    # Endgame spans: contiguous-ply islands per endgame_class.
    class_plies: dict[int, list[PlyData]] = defaultdict(list)
    for pd in plies_list:
        ec = pd["endgame_class"]
        if ec is not None:
            class_plies[ec].append(pd)

    for ec, pds in class_plies.items():
        for island in _split_into_contiguous_islands(pds):
            span_pd = island[0]
            if span_pd["eval_cp"] is not None or span_pd["eval_mate"] is not None:
                # T-78-17 lichess preservation: do not overwrite.
                continue
            specs.append(
                _TargetSpec(
                    ply=span_pd["ply"],
                    eval_kind="endgame_span_entry",
                    endgame_class=ec,
                )
            )

    return specs


def _snapshot_boards(pgn_text: str, target_plies: set[int]) -> dict[int, chess.Board]:
    """Parse PGN once and return board snapshots keyed by ply (0-indexed, pre-push).

    Plies not reached before the mainline ends are silently omitted — no
    Sentry (parse errors and short games are rare and not urgent).
    Unparseable PGNs return an empty dict.
    """
    if not target_plies:
        return {}
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return {}
    if game is None:
        return {}

    board = game.board()
    snapshots: dict[int, chess.Board] = {}
    remaining = set(target_plies)
    for i, node in enumerate(game.mainline()):
        if i in remaining:
            snapshots[i] = board.copy()
            remaining.discard(i)
            if not remaining:
                break
        board.push(node.move)
    return snapshots


def _collect_eval_targets_per_game(
    g_id: int,
    pgn_text: str,
    plies_list: Sequence[PlyData],
) -> list[_EvalTarget]:
    """Per-game single-walk target builder (Quick 260521-d6o).

    Replaces the previous N-parse pattern where each midgame + endgame span
    entry triggered its own PGN parse and mainline walk per target ply.
    The new path:

      1. Derive every target ply up front from PlyData alone (no parsing).
      2. If no targets, return [] WITHOUT touching the PGN — cold drain
         covered-game gate goes through zero parses.
      3. Otherwise parse the PGN once and walk the mainline once, snapshotting
         `board.copy()` at each target ply (early-break when all targets are
         filled).
      4. Assemble _EvalTarget rows. Midgame entry first (matches the previous
         collector ordering — midgame helper output, then endgame helper
         output), then endgame targets in ply-ascending order.

    Targets whose ply was unreachable (game ended early) are silently dropped
    — no Sentry, matching the previous best-effort semantics for short games.
    """
    specs = _collect_target_specs(plies_list)
    if not specs:
        return []

    snapshots = _snapshot_boards(pgn_text, {s.ply for s in specs})
    if not snapshots:
        return []

    midgame_targets: list[_EvalTarget] = []
    endgame_targets: list[_EvalTarget] = []
    for spec in specs:
        board = snapshots.get(spec.ply)
        if board is None:
            # Mainline ended before this target ply — silently skip (no Sentry).
            continue
        target = _EvalTarget(
            game_id=g_id,
            ply=spec.ply,
            eval_kind=spec.eval_kind,
            endgame_class=spec.endgame_class,
            board=board,
        )
        if spec.eval_kind == "middlegame_entry":
            midgame_targets.append(target)
        else:
            endgame_targets.append(target)

    endgame_targets.sort(key=lambda t: t.ply)
    return midgame_targets + endgame_targets


def _collect_midgame_eval_targets(
    game_eval_data: Sequence[tuple[int, str, list[PlyData]]],
) -> list[_EvalTarget]:
    """Phase 79 PHASE-IMP-01: middlegame entry eval — MIN(ply) where phase == 1.

    Phase 91: lifted from import_service.py for the cold-drain lane.

    Quick 260521-d6o: now a thin filter over the single-walk per-game helper.
    The hot-lane Stage 5c covered-game gate in import_service.py still imports
    and calls this with single-game tuples; the signature is preserved. When
    both collectors are called back-to-back on the same `game_eval_data`, each
    invocation does its own single mainline walk per game — the production
    cold-drain path in `_collect_eval_targets_from_db` therefore calls
    `_collect_eval_targets_per_game` directly to avoid the double walk.

    Skips plies where lichess %eval already populated the row (T-78-17).
    At most one middlegame entry per game (D-79-08).
    """
    targets: list[_EvalTarget] = []
    for g_id, pgn_text, plies_list in game_eval_data:
        all_targets = _collect_eval_targets_per_game(g_id, pgn_text, plies_list)
        targets.extend(t for t in all_targets if t.eval_kind == "middlegame_entry")
    return targets


def _collect_endgame_span_eval_targets(
    game_eval_data: Sequence[tuple[int, str, list[PlyData]]],
) -> list[_EvalTarget]:
    """Phase 78 per-class endgame span entry collection.

    Phase 91: lifted from import_service.py for the cold-drain lane.

    Quick 260521-d6o: now a thin filter over the single-walk per-game helper.
    Same signature-preservation note as `_collect_midgame_eval_targets`.
    Each contiguous run of the same endgame_class within a game is its own
    span; a class=1 → class=2 → class=1 sequence yields two class=1 entry
    evals, not one. Skips plies where lichess %eval already populated the
    row (T-78-17).
    """
    targets: list[_EvalTarget] = []
    for g_id, pgn_text, plies_list in game_eval_data:
        all_targets = _collect_eval_targets_per_game(g_id, pgn_text, plies_list)
        targets.extend(t for t in all_targets if t.eval_kind == "endgame_span_entry")
    return targets


def _split_into_contiguous_islands(pds: Sequence[PlyData]) -> list[list[PlyData]]:
    """Split per-class plies into contiguous runs ("islands").

    Phase 91: lifted from import_service.py for the cold-drain lane.

    A new island starts whenever the ply gap to the previous entry is > 1
    — i.e. the class was interrupted by a non-class ply. plies_list is
    already in ply order, so pds is too; sort defensively.
    """
    pds_sorted = sorted(pds, key=lambda p: p["ply"])
    islands: list[list[PlyData]] = []
    current: list[PlyData] = []
    for pd in pds_sorted:
        if current and pd["ply"] != current[-1]["ply"] + 1:
            islands.append(current)
            current = []
        current.append(pd)
    if current:
        islands.append(current)
    return islands


async def _batch_update_entry_eval_rows(
    session: AsyncSession,
    rows: list[tuple[int, int, int | None, int | None, int | None]],
) -> None:
    """Emit ONE batched UPDATE for entry-ply / cold-drain eval rows (SEED-052).

    Each row carries (game_id, ply, eval_cp, eval_mate, endgame_class). Mirrors the
    full-ply batched-write helpers (_batch_update_eval_rows) but for the entry-ply
    lane (_apply_eval_results), which differs in three ways:
    - rows span MULTIPLE games in a drain batch, so game_id lives in the VALUES tuple
      (not a single :game_id param) and the WHERE matches on v.game_id;
    - only eval_cp/eval_mate are written (no best_move);
    - the optional endgame_class disambiguation is preserved per-row via
      (v.endgame_class IS NULL OR game_positions.endgame_class = v.endgame_class) —
      exactly the pre-batch semantics where the endgame_class predicate was only added
      when target.endgame_class was not None (defensive: current schema has at most one
      row per (game_id, ply)).

    Uses CAST() instead of :: cast syntax: asyncpg rewrites named params to $N before
    the server parses the SQL, so `::` adjacent to a $N placeholder is a syntax error.
    CAST() is the portable equivalent.

    Guard: empty input is a no-op (no zero-row VALUES UPDATE is emitted).
    Sequential execute on caller-owned session — no asyncio.gather (CLAUDE.md).
    """
    if not rows:
        return
    params: dict[str, int | None] = {}
    values_parts: list[str] = []
    for i, (game_id, ply, eval_cp, eval_mate, endgame_class) in enumerate(rows):
        params[f"gid_{i}"] = game_id
        params[f"ply_{i}"] = ply
        params[f"ecp_{i}"] = eval_cp
        params[f"emt_{i}"] = eval_mate
        params[f"ec_{i}"] = endgame_class
        values_parts.append(
            f"(CAST(:gid_{i} AS integer),"
            f" CAST(:ply_{i} AS smallint),"
            f" CAST(:ecp_{i} AS smallint),"
            f" CAST(:emt_{i} AS smallint),"
            f" CAST(:ec_{i} AS smallint))"
        )
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        f"UPDATE game_positions"  # noqa: S608 — no user input; params are bound
        f" SET eval_cp = v.eval_cp, eval_mate = v.eval_mate"
        f" FROM (VALUES {values_sql}) AS v(game_id, ply, eval_cp, eval_mate, endgame_class)"
        f" WHERE game_positions.game_id = v.game_id"
        f" AND game_positions.ply = v.ply"
        f" AND (v.endgame_class IS NULL OR game_positions.endgame_class = v.endgame_class)"
    )
    await session.execute(sql, params)


async def _apply_eval_results(
    session: AsyncSession,
    eval_targets: Sequence[_EvalTarget],
    eval_results: Sequence[tuple[int | None, int | None]],
) -> tuple[int, int]:
    """Apply engine eval results to GamePosition rows via one batched UPDATE.

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

    SEED-052: the per-row update(GamePosition) loop became a single batched
    UPDATE … FROM (VALUES …) round-trip (mirrors the full-ply lane's 260616-jq1 /
    FLAWCHESS-6B fix). One Python pass classifies rows (counting + Sentry on the
    (None, None) skips, collecting write-rows); _batch_update_entry_eval_rows then
    emits the single UPDATE. The batched UPDATE runs sequentially against the
    shared, caller-owned session (CLAUDE.md hard rule: AsyncSession is not safe
    under asyncio.gather) and lands in its transaction.

    When engine returns (None, None), the row is skipped (eval_cp/eval_mate
    stays NULL permanently per D-09). The game is still marked
    evals_completed_at = NOW() by _mark_evals_completed so it is never
    re-picked (D-09 / R-02 — no permanent retry loop).

    Returns (eval_calls_made, eval_calls_failed).
    """
    eval_calls_made = 0
    eval_calls_failed = 0
    write_rows: list[tuple[int, int, int | None, int | None, int | None]] = []
    for target, (eval_cp, eval_mate) in zip(eval_targets, eval_results, strict=True):
        eval_calls_made += 1
        if eval_cp is None and eval_mate is None:
            # D-09: engine error / timeout — skip row, capture to Sentry, continue drain.
            eval_calls_failed += 1
            # Bounded Sentry context (D-79-04, T-78-18: no PGN/FEN/user_id).
            ctx: dict[str, Any] = {"game_id": target.game_id, "ply": target.ply}
            if target.endgame_class is not None:
                ctx["endgame_class"] = target.endgame_class
            sentry_sdk.set_context("eval", ctx)
            sentry_sdk.set_tag("source", "eval_drain")
            sentry_sdk.set_tag("eval_kind", target.eval_kind)
            sentry_sdk.capture_message("cold-drain engine returned None tuple", level="warning")
            continue

        # Endgame span entries carry endgame_class to disambiguate when the same
        # ply could in principle belong to multiple class spans; middlegame entries
        # carry None (no predicate). The per-row WHERE semantics are preserved inside
        # _batch_update_entry_eval_rows via the (v.endgame_class IS NULL OR …) clause.
        write_rows.append((target.game_id, target.ply, eval_cp, eval_mate, target.endgame_class))

    await _batch_update_entry_eval_rows(session, write_rows)
    return eval_calls_made, eval_calls_failed


# ---------------------------------------------------------------------------
# Cold-drain helpers: pick / load / mark
# ---------------------------------------------------------------------------


async def _claim_entry_eval_games(
    session: AsyncSession, worker_id: str, batch_size: int, ttl_seconds: int
) -> list[int]:
    """Atomically claim up to batch_size pending entry-ply games (LIFO id DESC) and
    stamp their lease. Returns the list of claimed game IDs.

    Shared by _pick_pending_game_ids (server pool, D-01) and /entry-lease (remote
    workers, D-05/D-07). This is the ONE canonical claim — do not write a second copy.

    SEED-051 D-3 shape: UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING.
    Mirrors _claim_queued_job (eval_queue_service.py) in both bound-param discipline
    (every value bound as :param, never f-string-interpolated — project Security rule)
    and TTL idiom (:ttl || ' seconds')::interval / str(ttl_seconds).

    Lease ends naturally: _mark_evals_completed stamps evals_completed_at = now() which
    removes the game from the predicate permanently. A crashed claimer's batch is
    reclaimed when entry_eval_lease_expiry < now() (TTL reclaim, D-04).
    """
    result = await session.execute(
        sa.text("""
            UPDATE games
            SET entry_eval_lease_expiry = now() + (:ttl || ' seconds')::interval,
                entry_eval_leased_by = :worker_id
            WHERE id IN (
                SELECT id FROM games
                WHERE evals_completed_at IS NULL
                  AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())
                ORDER BY id DESC
                LIMIT :batch
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
        """),
        {"ttl": str(ttl_seconds), "worker_id": worker_id, "batch": batch_size},
    )
    return [row[0] for row in result.all()]


async def _pick_pending_game_ids(limit: int) -> list[int]:
    """Open a short read-then-commit session, claim up to *limit* pending game IDs,
    stamp their entry-eval lease, and close.

    D-01 (Phase 123 SEED-051): now a lease claim via _claim_entry_eval_games so the
    server pool and remote workers strictly partition the same import (no double-eval).
    D-11: LIFO by id DESC (newest import first) — unchanged.

    The lease is committed before drain work begins so it is durable before the engine
    gather runs (mirror of claim_eval_job's commit-then-release discipline in
    eval_queue_service.py). The lease ends naturally when _mark_evals_completed stamps
    evals_completed_at; a crash is reclaimed by ENTRY_LEASE_TTL_SECONDS expiry.

    Note: UPDATE … RETURNING does not guarantee row order, so we sort DESC to preserve
    the D-11 LIFO contract for callers (the set of claimed games is correct by SKIP LOCKED;
    only the list ordering needs an explicit sort here).
    """
    async with async_session_maker() as session:
        game_ids = await _claim_entry_eval_games(
            session, WORKER_ID_SERVER_POOL, limit, ENTRY_LEASE_TTL_SECONDS
        )
        await session.commit()
    return sorted(game_ids, reverse=True)


async def _load_pgns_for_games(game_ids: Sequence[int]) -> list[tuple[int, str]]:
    """Open a short session, load (id, pgn) rows for the given game IDs, close."""
    async with async_session_maker() as session:
        result = await session.execute(select(Game.id, Game.pgn).where(Game.id.in_(game_ids)))
        return [(row[0], row[1]) for row in result.all()]


async def _mark_evals_completed(session: AsyncSession, game_ids: Sequence[int]) -> None:
    """Mark all picked games as eval-complete in one executemany UPDATE.

    Uses Game.__table__ + bindparam discipline (same as Stage 5 executemany in
    import_service.py) to emit invariant SQL (no unique-SQL cache growth).

    Idempotent: calling twice simply re-stamps evals_completed_at with a newer
    timestamp. All *limit* games are marked regardless of whether they had any
    eval targets — engine (None, None) counts as "evaluated" per D-09 / R-02.
    """
    now_ts = datetime.now(timezone.utc)
    # ty: __table__ is typed as FromClause on declarative base, but is a Table at runtime.
    games_table = Game.__table__
    stmt = (
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == bindparam("b_id"))
        .values(evals_completed_at=now_ts)
    )
    await session.execute(stmt, [{"b_id": gid} for gid in game_ids])


# ---------------------------------------------------------------------------
# Cold-drain coroutine + DB-backed target collection
# ---------------------------------------------------------------------------


async def _collect_eval_targets_from_db(
    session: AsyncSession,
    game_ids: Sequence[int],
    pgn_map: dict[int, str],
) -> list[_EvalTarget]:
    """Load GamePosition metadata for game_ids and derive eval targets.

    Loads (game_id, ply, phase, endgame_class, eval_cp, eval_mate) from
    GamePosition rows, then calls the single-walk per-game target builder.

    This is the correct cold-drain path: it avoids re-running process_game_pgn
    and uses the stored phase/endgame_class from the DB.

    Quick 260521-d6o: calls `_collect_eval_targets_per_game` directly (one
    PGN parse + one mainline walk per game) instead of routing through the
    two public wrappers (which would walk the mainline twice).
    """
    from app.services.zobrist import PlyData

    result = await session.execute(
        select(
            GamePosition.game_id,
            GamePosition.ply,
            GamePosition.phase,
            GamePosition.endgame_class,
            GamePosition.eval_cp,
            GamePosition.eval_mate,
        ).where(GamePosition.game_id.in_(game_ids))
    )
    rows = result.all()

    # Build game_eval_data: list of (game_id, pgn_text, plies_list)
    game_plies: dict[int, list[PlyData]] = defaultdict(list)
    for row in rows:
        gid, ply, phase, endgame_class, eval_cp, eval_mate = row
        if gid not in pgn_map:
            continue
        ply_data: PlyData = {
            "ply": ply,
            "phase": phase if phase is not None else 0,
            "endgame_class": endgame_class,
            "eval_cp": eval_cp,
            "eval_mate": eval_mate,
            # Fields not needed by eval target collection — provide defaults
            "white_hash": 0,
            "black_hash": 0,
            "full_hash": 0,
            "move_san": None,
            "clock_seconds": None,
            "piece_count": 0,
            "backrank_sparse": False,
            "mixedness": 0,
        }
        game_plies[gid].append(ply_data)

    targets: list[_EvalTarget] = []
    for gid, plies in game_plies.items():
        if gid not in pgn_map:
            continue
        targets.extend(_collect_eval_targets_per_game(gid, pgn_map[gid], plies))
    return targets


async def _classify_and_insert_flaws(
    session: AsyncSession,
    game_ids: Sequence[int],
) -> None:
    """Classify game_flaws for a batch of just-evaluated games and bulk-insert.

    Called in the cold-lane write session AFTER _apply_eval_results and BEFORE
    _mark_evals_completed — so eval_cp is committed before classification reads
    it, and flaw rows commit atomically with the eval results (Pitfall 2 guard).

    SEQUENTIAL loop — AsyncSession is not safe for concurrent use from multiple
    coroutines (CLAUDE.md hard rule). The drain batch size is _DRAIN_BATCH_SIZE
    (10 games), producing ~1-5 M+B flaw rows each (~50 rows max) — well within
    the memory envelope. No asyncio.gather on this session.

    Skips GameNotAnalyzed games silently (chess.com / low eval coverage).
    Per-game classify errors are Sentry-captured and the loop continues (T-108-04:
    one bad game must not abort the whole drain batch).

    D-10: reuses classify_game_flaws (the single classification kernel) and
    flaw_record_to_row (the single FlawRecord→row mapping) so the materialized
    table never drifts from the live kernel.
    """
    games_result = await session.execute(select(Game).where(Game.id.in_(game_ids)))
    games = games_result.scalars().all()

    # N+1 fix (FLAWCHESS-6G): load ALL positions for the batch in ONE query instead of
    # one SELECT per game inside the loop (Sentry flagged the per-game query as N+1 on
    # /api/eval/remote/entry-submit). Group by game_id in Python. The composite FK
    # (game_id, user_id) -> games(id, user_id) guarantees a position's user_id matches
    # its owning game, so filtering on game_id alone preserves the T-108-05 user-scope
    # guard. ORDER BY game_id, ply keeps each game's positions in ply-ASC order, which
    # classify_game_flaws requires.
    positions_by_game: dict[int, list[GamePosition]] = defaultdict(list)
    if games:
        positions_result = await session.execute(
            select(GamePosition)
            .where(GamePosition.game_id.in_([game.id for game in games]))
            .order_by(GamePosition.game_id, GamePosition.ply)
        )
        for pos in positions_result.scalars().all():
            positions_by_game[pos.game_id].append(pos)

    for game in games:
        try:
            positions = positions_by_game.get(game.id, [])

            result = classify_game_flaws(game, positions)
            if "reason" in result:
                # GameNotAnalyzed = chess.com / insufficient eval coverage — no rows.
                # TypedDict is a plain dict at runtime; discriminate on "reason" key.
                continue

            rows = [
                flaw_record_to_row(
                    user_id=game.user_id,
                    game_id=game.id,
                    flaw=flaw,
                )
                for flaw in result
            ]
            await bulk_insert_game_flaws(session, rows)

        except Exception as exc:
            # T-108-04: per-game errors must not abort the whole drain batch.
            # Never embed variables in the message (CLAUDE.md Sentry rule).
            sentry_sdk.set_context(
                "game_flaws",
                {"game_id": game.id, "user_id": game.user_id},
            )
            sentry_sdk.capture_exception(exc)
            continue


async def run_eval_drain() -> None:
    """Continuously evaluate entry plies for games with evals_completed_at IS NULL.

    Phase 91 / SEED-023: cold-lane drain coroutine.

    Picks _DRAIN_BATCH_SIZE game IDs (LIFO by id DESC, D-11), loads PGNs from DB,
    derives entry-ply targets via GamePosition metadata, fans out asyncio.gather
    OUTSIDE any session scope (CLAUDE.md: AsyncSession not safe for concurrent use),
    then opens a short write-window session for the combined UPDATEs.

    Crash-safe: if the process dies before commit, all picked games remain
    evals_completed_at IS NULL and are re-picked on the next tick. At most a
    few seconds of eval CPU is repeated (idempotent).

    Exception handling (three-tier):
    - asyncio.CancelledError: propagates (lifespan shutdown contract, WR-07).
    - _RETRIABLE_DB_OUTAGE_ERRORS: sleep + continue (Postgres restart mid-tick).
    - Exception: log + capture + continue.

    Wired in app/main.py lifespan alongside run_periodic_reaper.
    """
    while True:
        try:
            # Step 1: pick batch (short read tx, then close session).
            # D-11: LIFO id-DESC, batch size = _DRAIN_BATCH_SIZE.
            game_ids = await _pick_pending_game_ids(limit=_DRAIN_BATCH_SIZE)
            if not game_ids:
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
                continue

            # Step 2: load PGNs (short read tx, then close session).
            game_pgn_rows = await _load_pgns_for_games(game_ids)
            pgn_map = {gid: pgn for gid, pgn in game_pgn_rows}

            # Step 3: load GamePosition metadata and derive eval targets
            # (separate short read session, then close).
            async with async_session_maker() as read_session:
                eval_targets = await _collect_eval_targets_from_db(read_session, game_ids, pgn_map)

            # Step 4: fan out engine evaluations.
            # CLAUDE.md hard rule: asyncio.gather must NEVER run inside an AsyncSession scope
            if eval_targets:
                eval_results: Sequence[tuple[int | None, int | None]] = await asyncio.gather(
                    *(engine_service.evaluate(t.board) for t in eval_targets)
                )
            else:
                eval_results = []

            # Step 5: open session LATE, write all UPDATEs in one short tx.
            # Session opens only AFTER gather completes — write window is <100 ms.
            async with async_session_maker() as session:
                if eval_targets:
                    await _apply_eval_results(session, eval_targets, list(eval_results))
                # Phase 108-02 D-10: classify + bulk-insert game_flaws for all
                # just-evaluated games. Runs AFTER _apply_eval_results so eval_cp
                # is available for classification, and BEFORE _mark_evals_completed
                # so flaw rows commit atomically with the eval results (Pitfall 2).
                # Sequential, no asyncio.gather (CLAUDE.md hard rule).
                await _classify_and_insert_flaws(session, game_ids)
                # Mark all picked games done regardless of eval success/failure.
                # engine.evaluate() returning (None, None) is treated as
                # "evaluated — engine failed for this position, leave row NULL"
                # per D-09 / R-02 — no permanent retry loop.
                await _mark_evals_completed(session, game_ids)
                await session.commit()

            # Phase 94.1 D-01 / Pitfall 1: Stage B fires for users whose pending-eval
            # count just transitioned to zero. Group just-drained game_ids by user_id,
            # then in ONE aggregated query (WR-01 fix, 94.1-12) filter to users whose
            # pending-eval count is now zero AND no active import_job exists (Plan 13
            # Stage B gate). Without the active-import guard, Stage B fires multiple
            # times as eval batches drain mid-import, producing transient intermediate
            # values on the chip (user 28 case — see 94.1-13-PLAN.md gap_source).
            # Fresh read session: never share the eval-write session across coroutines.
            async with async_session_maker() as read_session:
                user_id_rows = await read_session.execute(
                    select(Game.user_id).distinct().where(Game.id.in_(game_ids))
                )
                affected_user_ids = [row[0] for row in user_id_rows.all()]
                if affected_user_ids:
                    zero_pending = await users_with_zero_pending(read_session, affected_user_ids)
                    for uid in zero_pending:
                        # Quick 260529-015: mark BEFORE scheduling so the 3s
                        # readiness poll can't observe pending==0 and unlock Tier 2
                        # in the window before compute_stage_b starts writing rows.
                        percentile_compute_registry.mark(uid)
                        asyncio.create_task(compute_stage_b(uid))

        except asyncio.CancelledError:
            # Lifespan shutdown — propagate without retry (cancellation contract
            # mirrors WR-07 in import_service.py: CancelledError is BaseException,
            # neither except clause below catches it).
            raise
        except _RETRIABLE_DB_OUTAGE_ERRORS as exc:
            # Postgres restart mid-tick: log + short sleep, then re-poll.
            # Games remain evals_completed_at IS NULL and will be re-picked.
            logger.warning("eval_drain: DB outage, retrying in %ds", _DRAIN_IDLE_SLEEP_SECONDS)
            sentry_sdk.set_tag("source", "eval_drain")
            sentry_sdk.capture_exception(exc)
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
        except Exception:
            logger.exception("eval_drain: unexpected error — continuing")
            sentry_sdk.set_tag("source", "eval_drain")
            sentry_sdk.capture_exception()
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)


async def _upsert_opening_cache(
    session: AsyncSession,
    engine_targets: list[_FullPlyEvalTarget],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> None:
    """Batch-insert freshly-computed opening-region engine evals into the dedup cache (D-123.1-04).

    Populates opening_position_eval with results from this tick's engine evaluations,
    restricted to the opening region (ply <= _DEDUP_MAX_PLY), non-terminal targets, and
    rows that have a real eval (at least one of eval_cp/eval_mate is non-NULL).

    Excludes:
    - Dedup transplants (already in the cache; only engine_targets are passed in)
    - Terminal donors (is_terminal=True; no game_positions row, eval is post-move only)
    - Null-eval holes (engine failure — nothing to cache)

    Uses ON CONFLICT (full_hash) DO NOTHING (first-write-wins per D-123.1-04). Insert
    volume is self-limiting: as the cache fills, fewer misses reach here each tick.

    The INSERT is inside the existing Step-4 write transaction. If it fails the whole txn
    rolls back and the game is re-picked next tick — acceptable, as the eval writes have
    not committed either. No outer try/except is added (we do not swallow cache errors).

    Uses CAST() instead of :: cast syntax for asyncpg compatibility (same reason as
    _batch_update_eval_rows).

    Guard: empty cache_rows is a no-op — no SQL emitted.
    """
    cache_rows = [
        (t.full_hash, cp, mate, bm)
        for t in engine_targets
        if t.ply <= _DEDUP_MAX_PLY and not t.is_terminal
        for cp, mate, bm, _pv in (engine_result_map.get(t.ply, (None, None, None, None)),)
        if cp is not None or mate is not None
    ]
    if not cache_rows:
        return
    params: dict[str, int | str | None] = {}
    values_parts: list[str] = []
    for i, (fh, cp, mate, bm) in enumerate(cache_rows):
        params[f"fh_{i}"] = fh
        params[f"cp_{i}"] = cp
        params[f"mt_{i}"] = mate
        params[f"bm_{i}"] = bm
        values_parts.append(
            f"(CAST(:fh_{i} AS bigint),"
            f" CAST(:cp_{i} AS smallint),"
            f" CAST(:mt_{i} AS smallint),"
            f" CAST(:bm_{i} AS varchar))"
        )
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        f"INSERT INTO opening_position_eval (full_hash, eval_cp, eval_mate, best_move)"  # noqa: S608
        f" VALUES {values_sql}"
        f" ON CONFLICT (full_hash) DO NOTHING"
    )
    await session.execute(sql, params)


async def _full_drain_tick() -> bool:
    """Run ONE full-drain tick: yield gate, queue claim, collect, dedup, gather, write.

    Returns True when a game was processed and marked complete; False when the
    tick did nothing (yield gate active, or no pending non-guest game) or the
    all-fail circuit breaker tripped (WR-05 — game stays pending for retry).

    Extracted from run_full_eval_drain (WR-07) so tests can drive exactly one
    tick deterministically — no wall-clock sleeps, no loop cancellation.

    Session discipline (CLAUDE.md hard rule: AsyncSession not safe for concurrent use):
      Step 0: yield gate — short read tx, close.
      Step 1: claim_eval_job — tier-1 > tier-2 > tier-3 derived (queue service owns sessions).
      Step 2: load PGN + game_positions rows — short read tx, close.
      Step 3: asyncio.gather(evaluate_nodes_multipv2) with NO session open.
      Step 4: write session (open LATE): UPDATEs + classify + oracle + markers + commit, close.
      Step 5: _signal_flaw_completion — lightweight hook (no session, Phase 117 stub).
    """
    # Step 0: yield gate (D-116-11).
    # Short read session to check active import or entry-ply backlog.
    async with async_session_maker() as gate_session:
        should_yield = await _any_active_import_or_entry_ply_pending(gate_session)
    if should_yield:
        return False

    # Step 1: claim ONE game via the tiered priority queue (Phase 117 QUEUE-01/02/05).
    # Replaces the LIFO id-DESC interim pick (D-116-09). claim_eval_job owns its
    # sessions internally and commits before returning — the SKIP LOCKED lease is
    # released on that commit (Pitfall 1 in RESEARCH §Common Pitfalls).
    claimed = await claim_eval_job(worker_id=WORKER_ID_SERVER_POOL)
    if claimed is None:
        return False

    game_id: int = claimed.game_id
    user_id: int = claimed.user_id
    tier: int = claimed.tier
    is_lichess_eval_game: bool = claimed.is_lichess_eval_game
    job_id: int | None = claimed.job_id

    # Step 2: load PGN + game_positions rows for this game.
    # Build targets via _collect_full_ply_targets; partition dedup candidates.
    # Also load full_eval_attempts (SEED-045: threaded here to avoid an extra
    # round-trip inside the write session).
    # Short read session, then close.
    async with async_session_maker() as load_session:
        pgn_result = await load_session.execute(
            select(Game.pgn, Game.full_eval_attempts).where(Game.id == game_id)
        )
        pgn_row = pgn_result.one_or_none()
        if pgn_row is None:
            # Game deleted between claim and load — nothing to do.
            return False
        pgn_text: str = pgn_row[0]
        current_attempts: int = pgn_row[1]

        pos_result = await load_session.execute(
            select(
                GamePosition.ply,
                GamePosition.full_hash,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
            ).where(GamePosition.game_id == game_id)
        )
        gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]

        # Collect one target per ply (EVAL-01). Engine games also get a terminal
        # eval-donor (SEED-044): under post-move storage the last move's stored
        # eval is the eval of the post-game position. Lichess games preserve their
        # %evals (never shifted), so they need no terminal donor.
        targets = _collect_full_ply_targets(
            game_id, pgn_text, gp_rows, include_terminal=not is_lichess_eval_game
        )

        # WR-01: for is_lichess_eval_game (lichess %eval) games, plies whose row
        # already carries a non-NULL eval are preserved at write time (D-116-04 /
        # T-78-17). Filtering here avoids burning 1M-node calls whose results are
        # discarded.
        #
        # D-117-13 / SEED-054 EXCEPTION: flaw plies (flaw_ply AND flaw_ply + 1) must
        # still be engine-evaluated. flaw_ply + 1 captures the refutation PV; flaw_ply
        # captures the better-alternative best_move + ideal-continuation PV. Lichess
        # supplies %eval but NO PV and NO best_move, so without this exemption every
        # flaw in an analyzed lichess game got 0 PV (verified in prod post-Phase-117)
        # and a NULL best_move arrow (SEED-054). Pre-classify from the stored %evals
        # to find {flaw_ply, flaw_ply + 1}, then exempt those plies from the filter.
        flaw_engine_plies: set[int] = set()
        if is_lichess_eval_game:
            flaw_engine_plies = await _flaw_engine_plies(load_session, game_id)
            targets = [
                t
                for t in targets
                if (t.eval_cp is None and t.eval_mate is None) or t.ply in flaw_engine_plies
            ]

        # Partition opening-region hashes for dedup (EVAL-03). Flaw plies are
        # excluded so they always get a real engine eval + best_move + PV instead of
        # an eval-only dedup transplant (which carries no pv_string — D-117-13).
        dedup_hashes = [
            t.full_hash
            for t in targets
            if t.ply <= _DEDUP_MAX_PLY and t.ply not in flaw_engine_plies and not t.is_terminal
        ]
        dedup_map = await _fetch_dedup_evals(load_session, dedup_hashes)
    # load_session is now closed.

    # Step 3: asyncio.gather — NO session open.
    # CLAUDE.md hard rule: gather must never run inside an AsyncSession scope.
    # Targets with a dedup hit skip the engine call (EVAL-03).
    # Phase 117 EVAL-04 / Phase 142 D-01: use evaluate_nodes_multipv2 so the
    # whole-game per-ply pass becomes multipv=2 (capturing second-best per ply).
    # Tier-1 (QUEUE-03): fan ALL of one game's plies across the pool simultaneously.
    # Tiers 2/3: same gather — the distinction is how the game was claimed, not how it's analyzed.
    # D-117-13 / SEED-054: flaw plies (flaw_ply and flaw_ply + 1) always go to the
    # engine (best_move + PV capture), even if a sibling target with the same
    # full_hash seeded the dedup map.
    # The terminal eval-donor (SEED-044) is always engine-evaluated: it has no
    # full_hash in the dedup map and supplies the last move's after-eval.
    engine_targets = [
        t
        for t in targets
        if t.is_terminal
        or t.ply in flaw_engine_plies
        or t.ply > _DEDUP_MAX_PLY
        or t.full_hash not in dedup_map
    ]
    if engine_targets:
        engine_results_raw: Sequence[
            tuple[
                int | None,
                int | None,
                str | None,
                str | None,
                int | None,
                int | None,
                str | None,
            ]
        ] = await asyncio.gather(
            *(engine_service.evaluate_nodes_multipv2(t.board) for t in engine_targets)
        )
    else:
        engine_results_raw = []

    # WR-05 circuit breaker: when EVERY engine call for the game failed, the
    # cause is overwhelmingly an engine-pool problem (e.g. all workers
    # permanently dead after failed restarts), not a position problem. Marking
    # the game complete would convert a transient outage into permanent,
    # silent loss of full-eval coverage across the whole backlog at maximum
    # loop speed. Leave the game pending (re-picked next tick) and report ONE
    # Sentry event. Per-position holes remain mark-and-continue per D-116-07.
    if engine_targets and all(
        cp is None and mt is None for cp, mt, _bm, _pv, _scp, _smt, _suci in engine_results_raw
    ):
        sentry_sdk.set_context(
            "eval", {"game_id": game_id, "failed_ply_count": len(engine_targets)}
        )
        sentry_sdk.set_tag("source", "full_eval_drain")
        sentry_sdk.capture_message(
            "full-drain: all engine evals failed for game — leaving pending", level="warning"
        )
        return False

    # Build engine_result_map (4-tuple, unchanged downstream signature) and a parallel
    # second_best_map from the 7-tuple gather results. engine_result_map keeps its existing
    # 4-tuple shape so _apply_full_eval_results / _classify_and_fill_oracle are UNCHANGED
    # (minimal blast radius, Open Question #2 resolution). second_best_map carries the
    # second-best data and is passed only to _build_flaw_multipv2_blobs.
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]] = {}
    second_best_map: dict[int, tuple[int | None, int | None, str | None]] = {}
    for t, res in zip(engine_targets, engine_results_raw, strict=True):
        engine_result_map[t.ply] = (res[0], res[1], res[2], res[3])
        second_cp, second_mate, second_uci = res[4], res[5], res[6]
        # Include valid second-best data only (not engine failure). second_uci is str
        # when the engine ran: "" = single-legal-move sentinel (Pitfall 3), non-empty = second move.
        if second_cp is not None or second_uci is not None:
            second_best_map[t.ply] = (second_cp, second_mate, second_uci)

    # Step 3b (SEED-056): recover pv for engine-game opening flaw plies that took a
    # pv-less dedup transplant. Runs another gather internally — still NO session open
    # (CLAUDE.md hard rule). Mutates engine_result_map in place; no-op for lichess games.
    await _fill_engine_game_flaw_pvs(
        game_id, targets, dedup_map, engine_result_map, is_lichess_eval_game
    )

    # Step 3c (D-05 / Phase 142 MPV-02): recover node-0 second-best for flaw plies that
    # used the opening dedup cache (their evals came from the dedup transplant and thus
    # have no entry in second_best_map). Mutates second_best_map in place. Still NO
    # session open (CLAUDE.md hard rule).
    await _fill_engine_game_flaw_second_best(
        game_id, targets, dedup_map, engine_result_map, second_best_map, is_lichess_eval_game
    )

    # Step 3d (Phase 142 MPV-02): build PvNode blobs for each flaw's allowed/missed lines.
    # Opens its own read session (closes before gather), then runs ONE asyncio.gather for
    # all continuation nodes — all before the write session opens (CLAUDE.md hard rule).
    flaw_pv_blobs = await _build_flaw_multipv2_blobs(
        game_id, targets, dedup_map, engine_result_map, second_best_map
    )

    # Step 4: write session — open LATE, after gather completes.
    # All UPDATEs, classify hook, oracle counts, markers, and job report in one transaction.
    #
    # Phase 119 SEED-045 hole-aware completion logic:
    #   failed_ply_count from _apply_full_eval_results = count of non-terminal engine-game
    #   plies where BOTH eval_cp IS NULL AND eval_mate IS NULL after the tick (holes).
    #   Mate-scored plies (eval_mate IS NOT NULL) and terminal donors are NOT counted.
    #
    # Decision tree (applied inside the write session so all UPDATEs commit atomically):
    #   A. failed_ply_count == 0 → no holes: stamp both markers, classify, report job.
    #      full_eval_attempts unchanged.
    #   B. failed_ply_count > 0 AND current_attempts + 1 < MAX_EVAL_ATTEMPTS → under cap:
    #      Do NOT stamp full_evals_completed_at / full_pv_completed_at. Still run classify
    #      so partial flaws materialize (and evals that DID resolve are already written by
    #      _apply_full_eval_results). Increment full_eval_attempts, commit, return False so
    #      the game is re-picked next tick. Do NOT report the job complete (tier-1/2 lease
    #      sweep re-queues it; tier-3 has no job_id so it is naturally re-derived).
    #   C. failed_ply_count > 0 AND current_attempts + 1 >= MAX_EVAL_ATTEMPTS → cap:
    #      Stamp complete anyway (preserves D-116-07 no-infinite-loop invariant), classify,
    #      report job, emit ONE aggregated Sentry warning. Never emit the cap event unless
    #      holes actually persist — this replaces the former per-tick Sentry call at the
    #      failed_ply_count > 0 branch (which would have fired even on retried games).
    async with async_session_maker() as write_session:
        failed_ply_count = await _apply_full_eval_results(
            write_session, targets, dedup_map, engine_result_map, is_lichess_eval_game
        )

        # EVAL-06 / D-117-08: classify game_flaws + fill oracle columns + write flaw PVs.
        # Runs AFTER _apply_full_eval_results so eval_cp is visible for classification.
        # Runs BEFORE the completion markers so evals + flaws commit atomically (T-117-11).
        # Always runs — partial flaws should materialize even when holes remain.
        await _classify_and_fill_oracle(write_session, game_id, engine_result_map)

        # Phase 142 MPV-02: write PvNode blobs (allowed/missed lines) to game_flaws.
        # Runs in the same transaction as _classify_and_fill_oracle so flaw rows exist
        # before the UPDATE (Pitfall 5: write-session discipline).
        await _run_multipv2_pass(write_session, game_id, flaw_pv_blobs)

        # SEED-053 / D-123.1-04: fill the opening-eval cache with freshly-computed misses.
        # Runs inside the same write txn — cache write + eval write commit atomically.
        # Skipped for lichess-eval games (no engine_targets generated for them).
        await _upsert_opening_cache(write_session, engine_targets, engine_result_map)

        new_attempts = current_attempts + 1
        games_table = Game.__table__

        if failed_ply_count == 0:
            # Path A: no holes — stamp complete and report job.
            await _mark_full_evals_completed(write_session, game_id)
            await _mark_full_pv_completed(write_session, game_id)
            stamp_complete = True

        elif new_attempts < MAX_EVAL_ATTEMPTS:
            # Path B: holes remain, under cap — increment attempts, leave pending.
            # Do NOT stamp full_evals_completed_at or full_pv_completed_at.
            await write_session.execute(
                update(games_table)  # ty: ignore[invalid-argument-type]
                .where(games_table.c.id == game_id)
                .values(full_eval_attempts=new_attempts)
            )
            stamp_complete = False

        else:
            # Path C: holes remain AND cap reached — stamp anyway (D-116-07 no-loop
            # invariant) + ONE aggregated Sentry event (T-119-03: variables via
            # set_context, never interpolated into the message string per CLAUDE.md).
            await _mark_full_evals_completed(write_session, game_id)
            await _mark_full_pv_completed(write_session, game_id)
            sentry_sdk.set_context(
                "eval",
                {"game_id": game_id, "hole_count": failed_ply_count, "attempts": new_attempts},
            )
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_message(
                "full-drain: stamping complete after MAX_EVAL_ATTEMPTS with residual holes",
                level="warning",
            )
            stamp_complete = True

        if stamp_complete:
            # QUEUE-06: report the leased job as complete (tier-3 has no job row — job_id
            # is None, so this block is skipped for tier-3 and the game is re-derived next tick).
            if job_id is not None:
                from app.models.eval_jobs import EvalJob

                jobs_table_jobs = EvalJob.__table__
                now_ts = datetime.now(timezone.utc)
                await write_session.execute(
                    update(jobs_table_jobs)  # ty: ignore[invalid-argument-type]
                    .where(
                        jobs_table_jobs.c.id == job_id,
                        jobs_table_jobs.c.status == "leased",
                    )
                    .values(status="completed", completed_at=now_ts)
                )

        await write_session.commit()

    if not stamp_complete:
        # Path B: game is left pending — not a processed game by the WR-07 contract.
        return False

    # Step 5: per-user cache-completion signal (D-117-11 — no-op stub in Phase 117).
    # Runs AFTER commit so the signal never fires for a partially-committed game.
    _signal_flaw_completion(user_id)
    _ = tier  # tier is available for Phase 118 tier-aware cache logic

    return True


async def run_full_eval_drain() -> None:
    """Continuously evaluate all non-terminal plies for games with full_evals_completed_at IS NULL.

    Phase 116 EVAL-01/EVAL-02/EVAL-03/EVAL-05 / D-116-08.

    Thin loop over _full_drain_tick (WR-07): sleeps _DRAIN_IDLE_SLEEP_SECONDS
    whenever the tick processed nothing (yield gate active or queue empty),
    loops immediately after a processed game.

    D-116-09: LIFO id-DESC interim pick (replaced by queue in Phase 117).
    D-116-10: guest filter — WHERE NOT users.is_guest.
    D-116-11: yield gate — sleep if active import OR entry-ply drain has backlog.

    Exception handling (three-tier mirrors run_eval_drain):
    - asyncio.CancelledError: propagates (lifespan shutdown contract).
    - _RETRIABLE_DB_OUTAGE_ERRORS: sleep + continue (Postgres restart mid-tick).
    - Exception: log + capture + continue.

    Wired in app/main.py lifespan as full-eval-drain alongside the entry-ply drain.
    """
    while True:
        try:
            processed = await _full_drain_tick()
            if not processed:
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)

        except asyncio.CancelledError:
            raise
        except _RETRIABLE_DB_OUTAGE_ERRORS as exc:
            logger.warning("full_eval_drain: DB outage, retrying in %ds", _DRAIN_IDLE_SLEEP_SECONDS)
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_exception(exc)
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
        except Exception:
            logger.exception("full_eval_drain: unexpected error — continuing")
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_exception()
            await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)


async def resweep_holed_games(
    limit: int | None = None,
    dry_run: bool = False,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """Re-arm already-stamped engine games that still carry non-terminal holes (SEED-045).

    Before Phase 119, the drain stamped full_evals_completed_at unconditionally (D-116-07),
    so games with transient mid-game engine holes were permanently marked "fully analyzed"
    with gaps. This sweep finds those games and clears their completion markers so the
    bounded-retry drain re-picks them with a fresh MAX_EVAL_ATTEMPTS budget.

    A "hole" is a non-terminal, non-game-ending-move, non-mate ply:
        eval_cp IS NULL AND eval_mate IS NULL AND ply < MAX(ply) - 1 for that game.
    The MAX(ply) exclusion skips the terminal game-over ply (which has no DB row of its
    own in most games but may appear as the last row in some PGNs). The additional
    `- 1` (SEED-049) further excludes the game-ending move ply (ply = max_ply - 1):
    under post-move storage, that row stores the eval of the game-over terminal
    position, which is legitimately unevaluable (no legal moves; the engine skips it in
    _collect_full_ply_targets). Resignation/timeout endings whose last move has a real
    eval are unaffected — their last move is not NULL. Only the genuinely unevaluable
    terminal-move NULLs (checkmate, stalemate, insufficient material) are excluded.
    The 2 genuine mid-game holes observed in prod are at ply < max_ply - 1, so this
    exclusion is precise and safe.

    Scope: engine games only (lichess_evals_at IS NULL). Lichess %eval games are already
    excluded from the full-drain and need no re-arming.

    Args:
        limit: cap the candidate scan at this many games (None = all).
        dry_run: count candidates without performing the UPDATE. Useful for prod inspection
            before running for real.
        session_maker: optional sessionmaker override (e.g. a prod-tunnel-bound maker from
            scripts/resweep_holed_games.py --db prod). Defaults to the app's
            async_session_maker (bound to DATABASE_URL — the dev DB locally).

    Returns:
        Count of games swept (cleared) or that would be swept (dry_run=True).

    Prod usage (via the SSH tunnel from bin/prod_db_tunnel.sh):
        uv run python scripts/resweep_holed_games.py --db prod --dry-run   # count only
        uv run python scripts/resweep_holed_games.py --db prod             # sweep
    """
    from app.models.game_position import GamePosition

    maker = session_maker or async_session_maker
    games_table = Game.__table__
    gp_table = GamePosition.__table__

    # Sub-query: find game_ids of engine games whose full_evals_completed_at IS NOT NULL
    # AND that have at least one genuine (non-terminal, non-game-ending-move, non-mate) hole.
    # "Non-terminal" = ply < MAX(ply) for that game (excludes the last game-over ply).
    # "Non-game-ending-move" = ply < MAX(ply) - _GAME_ENDING_PLY_OFFSET (SEED-049:
    #     excludes the move that ended the game; under post-move storage its after-eval is
    #     the unevaluable terminal position — legitimately NULL, not a transient hole).
    # "Non-mate" = eval_mate IS NULL (mate-scored plies are not holes).
    max_ply_per_game = (
        sa.select(GamePosition.game_id, sa.func.max(GamePosition.ply).label("max_ply"))
        .group_by(GamePosition.game_id)
        .subquery("max_ply_per_game")
    )

    holed_game_ids_q = (
        sa.select(gp_table.c.game_id)
        .distinct()
        .join(
            games_table,
            sa.and_(
                gp_table.c.game_id == games_table.c.id,
                games_table.c.full_evals_completed_at.isnot(None),
                games_table.c.lichess_evals_at.is_(None),  # engine games only
            ),
        )
        .join(
            max_ply_per_game,
            gp_table.c.game_id == max_ply_per_game.c.game_id,
        )
        .where(
            gp_table.c.eval_cp.is_(None),
            gp_table.c.eval_mate.is_(None),
            # SEED-049: ply < max_ply - 1 excludes both the terminal ply AND the
            # game-ending move ply (whose NULL after-eval is legitimately unevaluable).
            gp_table.c.ply < max_ply_per_game.c.max_ply - _GAME_ENDING_PLY_OFFSET,
        )
    )
    if limit is not None:
        holed_game_ids_q = holed_game_ids_q.limit(limit)

    async with maker() as session:
        # Initialize before the try so the except handler can report game_count
        # without a fragile `dir()` scope probe (WR-03). If session.execute raises
        # before the assignment below, game_count is correctly 0.
        game_ids: list[int] = []
        try:
            result = await session.execute(holed_game_ids_q)
            game_ids = [row[0] for row in result.all()]
            count = len(game_ids)

            if dry_run or count == 0:
                logger.info(
                    "resweep_holed_games: %s=%d games%s",
                    "would sweep" if dry_run else "swept",
                    count,
                    " (dry run)" if dry_run else "",
                )
                return count

            # Clear the completion markers and reset the attempt counter.
            # Clearing full_evals_completed_at makes needs_engine_full_evals True again
            # → tier-3 re-picks the game. The ix_games_needs_engine_full_evals partial
            # index (SEED-046, migration 20260614150000) covers this predicate.
            #
            # WR-04: chunk the UPDATE in _RESWEEP_UPDATE_CHUNK_SIZE batches so the
            # unbounded prod path can't re-arm the whole holed backlog in one
            # statement/transaction (bind-param blowup + simultaneous re-queue).
            # For count <= chunk size this is one statement + one commit, identical
            # to the pre-batching behavior.
            for chunk_start in range(0, count, _RESWEEP_UPDATE_CHUNK_SIZE):
                chunk_ids = game_ids[chunk_start : chunk_start + _RESWEEP_UPDATE_CHUNK_SIZE]
                await session.execute(
                    update(games_table)  # ty: ignore[invalid-argument-type]
                    .where(games_table.c.id.in_(chunk_ids))
                    .values(
                        full_evals_completed_at=None,
                        full_pv_completed_at=None,
                        full_eval_attempts=0,
                    )
                )
                await session.commit()
            logger.info("resweep_holed_games: swept %d games", count)
            return count

        except Exception as exc:
            sentry_sdk.set_context("resweep", {"game_count": len(game_ids)})
            sentry_sdk.set_tag("source", "resweep_holed_games")
            sentry_sdk.capture_exception(exc)
            raise
