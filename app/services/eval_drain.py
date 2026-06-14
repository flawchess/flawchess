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
from sqlalchemy import bindparam, select, update
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import DEDUP_MAX_PLY, GamePosition
from app.models.import_job import ImportJob
from app.repositories.game_flaws_repository import bulk_insert_game_flaws, flaw_record_to_row
from app.repositories.game_repository import users_with_zero_pending
from app.services import engine as engine_service
from app.services import percentile_compute_registry
from app.services.eval_queue_service import WORKER_ID_SERVER_POOL, claim_eval_job
from app.services.flaws_service import classify_game_flaws, count_game_severities
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
    # engine cannot search a finished position (evaluate_nodes_with_pv would error
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
    return targets


async def _fetch_dedup_evals(
    session: AsyncSession,
    full_hashes: Sequence[int],
) -> dict[int, tuple[int | None, int | None, str | None]]:
    """Batch-fetch a position's OWN eval + best_move for opening-region hashes (EVAL-03, D-116-02).

    Returns, for each requested position hash Q, the eval OF position Q and the
    engine's best move FROM Q — i.e. position-/decision-keyed values, NOT the
    post-move stored convention. The post-move +1 shift that turns these into the
    written rows happens later in `_post_move_eval`. Keeping the dedup map
    position-keyed lets the same shift apply uniformly to engine results and
    dedup transplants.

    Post-move convention recovery (SEED-044): every source row now stores the
    POST-MOVE eval — row k holds the eval of the position AFTER move k, i.e. the
    eval of `full_hash[k+1]`, for ALL sources (engine and lichess `%eval` alike;
    zobrist.py stores lichess the same way). So a position's OWN eval is NOT in
    its own row — it is in the row whose move REACHED it (one ply earlier). We
    recover it with a one-ply self-join: for a requested position Q, read
    `cur.eval_cp` from the donor row `cur` whose successor `nxt` has
    `nxt.full_hash == Q` (`nxt.ply == cur.ply + 1`). `cur.eval_cp` is the eval
    AFTER cur's move = the eval OF Q. The best move FROM Q stays decision-keyed,
    so it is read directly from `nxt.best_move` (the row whose full_hash IS Q).

    Gates (unchanged): full_evals_completed_at IS NOT NULL (parity by
    construction; NOT evals_completed_at, which includes depth-15 rows — Pitfall
    4) and lichess_evals_at IS NULL (engine-written source only — WR-02 /
    D-117-07; transplanting requires our 1M-node best_move, which lichess sources
    lack). The opening-region gate is on the requested position `nxt.ply`.

    First-ply edge: the initial position (ply 0) has no predecessor move that
    reaches it, so it is never recoverable here and simply falls through to a
    fresh engine eval. That is harmless — under post-move storage no row ever
    stores the initial position's eval (row k stores the eval AFTER move k).

    Returns {full_hash: (eval_cp, eval_mate, best_move)} for hashes with at
    least one hit.
    """
    if not full_hashes:
        return {}
    cur = aliased(GamePosition)
    nxt = aliased(GamePosition)
    result = await session.execute(
        select(
            nxt.full_hash,
            cur.eval_cp,
            cur.eval_mate,
            nxt.best_move,
        )
        .join(nxt, sa.and_(nxt.game_id == cur.game_id, nxt.ply == cur.ply + 1))
        .join(Game, cur.game_id == Game.id)
        .where(
            nxt.full_hash.in_(full_hashes),
            nxt.ply <= _DEDUP_MAX_PLY,
            # full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL — engine-written
            # source only (WR-02 / D-117-07; transplanting requires our 1M-node best_move,
            # which lichess sources lack).
            Game.has_engine_full_evals,
            # cur.eval_cp/eval_mate = the post-move eval of cur = the eval OF nxt's position.
            sa.or_(cur.eval_cp.isnot(None), cur.eval_mate.isnot(None)),
        )
        .distinct(nxt.full_hash)
        .limit(len(full_hashes))
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


async def _apply_full_eval_results(
    session: AsyncSession,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    is_lichess_eval_game: bool,
) -> int:
    """Write POST-MOVE evals + best_move to GamePosition rows (WR-04; SEED-044).

    UPDATEs run sequentially against the caller-owned session (CLAUDE.md hard
    rule: AsyncSession is not safe under asyncio.gather); the caller commits.

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
                await session.execute(
                    update(GamePosition)
                    .where(
                        GamePosition.game_id == target.game_id,
                        GamePosition.ply == ply,
                    )
                    .values(best_move=best_move)
                )
            continue

        # Engine game: store the POST-MOVE eval (eval of the position AFTER this
        # move = pos_eval[ply + 1]); best_move stays decision-ply-keyed. best_move is
        # written whenever available, INDEPENDENT of the eval — an engine hole at the
        # after-position (ply + 1) must not drop this row's own best_move (SEED-044).
        eval_cp, eval_mate = _post_move_eval(pos_eval, ply)
        values: dict[str, int | str | None] = {}
        if best_move is not None:
            values["best_move"] = best_move
        if eval_cp is None and eval_mate is None:
            # D-116-07: engine hole at the after-position — leave the eval NULL; counted
            # for the caller's per-game aggregated Sentry event (WR-05).
            failed_ply_count += 1
        else:
            values["eval_cp"] = eval_cp
            values["eval_mate"] = eval_mate
        if values:
            await session.execute(
                update(GamePosition)
                .where(
                    GamePosition.game_id == target.game_id,
                    GamePosition.ply == ply,
                )
                .values(**values)
            )
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
    3. bulk_insert_game_flaws (ON CONFLICT DO NOTHING, idempotent).
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

    flaw_result = classify_game_flaws(game, positions)
    if "reason" in flaw_result:
        # GameNotAnalyzed: insufficient eval coverage — skip.
        return

    flaw_list = flaw_result  # list[FlawRecord]

    # Insert M+B flaw rows (ON CONFLICT DO NOTHING — idempotent).
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

    # Flaw PV write: for each FlawRecord at ply N, write pv at ply N+1.
    # The pv_string for ply N+1 comes from the engine_result_map entry at ply N+1
    # (the board AFTER the flawed move — D-117-02 / Pitfall 4).
    # PV writes are individually fault-tolerant: a single bad pv row (e.g. oversized
    # string) must NOT abort flaw rows + oracle counts already written above.
    for flaw in flaw_list:
        flaw_ply: int = flaw["ply"]
        pv_ply = flaw_ply + 1
        engine_entry = engine_result_map.get(pv_ply)
        if engine_entry is None:
            continue
        _cp, _mt, _bm, pv_string = engine_entry
        if pv_string is None:
            continue
        try:
            await session.execute(
                update(GamePosition)
                .where(
                    GamePosition.game_id == game_id,
                    GamePosition.ply == pv_ply,
                )
                .values(pv=pv_string)
            )
        except Exception as exc:
            # T-108-04 / WR-01: a single bad PV row must not abort the whole game.
            # Flaw rows and oracle counts are already written above (not rolled back
            # here — this try/except is inside the write_session transaction; the
            # session is invalidated on asyncpg-level errors, which will propagate
            # through the outer commit). Capture for visibility.
            sentry_sdk.set_context(
                "classify_oracle",
                {"game_id": game_id, "pv_ply": pv_ply},
            )
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_exception(exc)


async def _flaw_adjacent_plies(session: AsyncSession, game_id: int) -> set[int]:
    """Pre-classify a lichess-eval game's flaws to find plies needing engine PV capture (D-117-13).

    Lichess-eval games (is_lichess_eval_game=True) carry a lichess %eval on
    (nearly) every ply, so the is_lichess_eval_game target filter in
    _full_drain_tick would otherwise drop every flaw-adjacent ply before the
    engine gather — and lichess supplies %eval but NO principal variation. The observed result (prod sanity check ~1 h after the
    Phase 117 deploy) was 0% flaw-PV coverage for analyzed lichess games: every
    flaw's refutation line (the SEED-039 input) was missing.

    Fix: classify flaws up front from the already-stored %evals — the SAME inputs
    the write-time classify in _classify_and_fill_oracle uses — and return the set
    of {flaw_ply + 1} plies. The caller exempts these from the eval-preservation
    filter and from the opening dedup so the engine evaluates exactly those
    positions for PV capture, while the write path still preserves the lichess
    %eval (D-116-04). Covers BOTH players' flaws (classify_game_flaws is two-sided
    per D-06), matching the write-time PV loop.

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
    return {flaw["ply"] + 1 for flaw in flaw_result}


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


async def _apply_eval_results(
    session: AsyncSession,
    eval_targets: Sequence[_EvalTarget],
    eval_results: Sequence[tuple[int | None, int | None]],
) -> tuple[int, int]:
    """Apply engine eval results to GamePosition rows via per-row UPDATE.

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

    UPDATEs run sequentially against the shared session (CLAUDE.md hard
    rule: AsyncSession is not safe under asyncio.gather). The session is
    owned by the caller and the UPDATEs land in its transaction.

    When engine returns (None, None), the row is skipped (eval_cp/eval_mate
    stays NULL permanently per D-09). The game is still marked
    evals_completed_at = NOW() by _mark_evals_completed so it is never
    re-picked (D-09 / R-02 — no permanent retry loop).

    Returns (eval_calls_made, eval_calls_failed).
    """
    eval_calls_made = 0
    eval_calls_failed = 0
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

        # Build the WHERE clause for this eval kind. Endgame span entries
        # filter by endgame_class to disambiguate when the same ply could
        # in principle belong to multiple class spans (defensive — current
        # schema has at most one row per (game_id, ply)).
        stmt = update(GamePosition).where(
            GamePosition.game_id == target.game_id,
            GamePosition.ply == target.ply,
        )
        if target.endgame_class is not None:
            stmt = stmt.where(GamePosition.endgame_class == target.endgame_class)
        await session.execute(stmt.values(eval_cp=eval_cp, eval_mate=eval_mate))
    return eval_calls_made, eval_calls_failed


# ---------------------------------------------------------------------------
# Cold-drain helpers: pick / load / mark
# ---------------------------------------------------------------------------


async def _pick_pending_game_ids(limit: int) -> list[int]:
    """Open a short session, pick up to *limit* pending game IDs in LIFO order, close.

    D-11: LIFO by id DESC so the most recently imported games are evaluated first.
    Uses the partial index ix_games_evals_pending (WHERE evals_completed_at IS NULL)
    for an instant index scan.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Game.id)
            .where(Game.evals_completed_at.is_(None))
            .order_by(Game.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


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
            "material_count": 0,
            "material_signature": "",
            "material_imbalance": 0,
            "has_opposite_color_bishops": False,
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

    for game in games:
        try:
            # Load positions ordered by ply, scoped to game.user_id (T-108-05 guard)
            positions_result = await session.execute(
                select(GamePosition)
                .where(
                    GamePosition.game_id == game.id,
                    GamePosition.user_id == game.user_id,
                )
                .order_by(GamePosition.ply)
            )
            positions = list(positions_result.scalars().all())

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
      Step 3: asyncio.gather(evaluate_nodes_with_pv) with NO session open.
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
        # D-117-13 EXCEPTION: flaw-adjacent plies (flaw_ply + 1) must still be
        # engine-evaluated to capture the refutation PV. Lichess supplies %eval but
        # NO PV, so without this exemption every flaw in an analyzed lichess game
        # got 0 PV (verified in prod post-Phase-117). Pre-classify from the stored
        # %evals to find {flaw_ply + 1}, then exempt those plies from the filter.
        flaw_adjacent_plies: set[int] = set()
        if is_lichess_eval_game:
            flaw_adjacent_plies = await _flaw_adjacent_plies(load_session, game_id)
            targets = [
                t
                for t in targets
                if (t.eval_cp is None and t.eval_mate is None) or t.ply in flaw_adjacent_plies
            ]

        # Partition opening-region hashes for dedup (EVAL-03). Flaw-adjacent plies
        # are excluded so they always get a real engine eval + PV instead of an
        # eval-only dedup transplant (which carries no pv_string — D-117-13).
        dedup_hashes = [
            t.full_hash
            for t in targets
            if t.ply <= _DEDUP_MAX_PLY and t.ply not in flaw_adjacent_plies and not t.is_terminal
        ]
        dedup_map = await _fetch_dedup_evals(load_session, dedup_hashes)
    # load_session is now closed.

    # Step 3: asyncio.gather — NO session open.
    # CLAUDE.md hard rule: gather must never run inside an AsyncSession scope.
    # Targets with a dedup hit skip the engine call (EVAL-03).
    # Phase 117 EVAL-04: use evaluate_nodes_with_pv to capture best_move + PV string.
    # Tier-1 (QUEUE-03): fan ALL of one game's plies across the pool simultaneously.
    # Tiers 2/3: same gather — the distinction is how the game was claimed, not how it's analyzed.
    # D-117-13: flaw-adjacent plies always go to the engine (PV capture), even if a
    # sibling target with the same full_hash seeded the dedup map.
    # The terminal eval-donor (SEED-044) is always engine-evaluated: it has no
    # full_hash in the dedup map and supplies the last move's after-eval.
    engine_targets = [
        t
        for t in targets
        if t.is_terminal
        or t.ply in flaw_adjacent_plies
        or t.ply > _DEDUP_MAX_PLY
        or t.full_hash not in dedup_map
    ]
    if engine_targets:
        engine_results_raw: Sequence[
            tuple[int | None, int | None, str | None, str | None]
        ] = await asyncio.gather(
            *(engine_service.evaluate_nodes_with_pv(t.board) for t in engine_targets)
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
    if engine_targets and all(cp is None and mt is None for cp, mt, _bm, _pv in engine_results_raw):
        sentry_sdk.set_context(
            "eval", {"game_id": game_id, "failed_ply_count": len(engine_targets)}
        )
        sentry_sdk.set_tag("source", "full_eval_drain")
        sentry_sdk.capture_message(
            "full-drain: all engine evals failed for game — leaving pending", level="warning"
        )
        return False

    # Build a ply -> (eval_cp, eval_mate, best_move, pv_string) map from engine results.
    # Dedup hits take priority at write time via _resolve_full_eval.
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]] = {}
    for t, res in zip(engine_targets, engine_results_raw, strict=True):
        engine_result_map[t.ply] = res

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
) -> int:
    """Re-arm already-stamped engine games that still carry non-terminal holes (SEED-045).

    Before Phase 119, the drain stamped full_evals_completed_at unconditionally (D-116-07),
    so games with transient mid-game engine holes were permanently marked "fully analyzed"
    with gaps. This sweep finds those games and clears their completion markers so the
    bounded-retry drain re-picks them with a fresh MAX_EVAL_ATTEMPTS budget.

    A "hole" is a non-terminal, non-mate ply:
        eval_cp IS NULL AND eval_mate IS NULL AND ply < MAX(ply) for that game.
    The MAX(ply) exclusion skips the terminal game-over ply (which has no DB row
    of its own in most games but may appear as the last row in some PGNs).

    Scope: engine games only (lichess_evals_at IS NULL). Lichess %eval games are already
    excluded from the full-drain and need no re-arming.

    Args:
        limit: cap the candidate scan at this many games (None = all).
        dry_run: count candidates without performing the UPDATE. Useful for prod inspection
            before running for real.

    Returns:
        Count of games swept (cleared) or that would be swept (dry_run=True).

    Prod one-liner:
        uv run python -c "
        import asyncio
        from app.services.eval_drain import resweep_holed_games
        count = asyncio.run(resweep_holed_games(dry_run=True))
        print(f'Would sweep {count} games')
        "
    """
    from app.models.game_position import GamePosition

    games_table = Game.__table__
    gp_table = GamePosition.__table__

    # Sub-query: find game_ids of engine games whose full_evals_completed_at IS NOT NULL
    # AND that have at least one non-terminal, non-mate hole.
    # "Non-terminal" = ply < MAX(ply) for that game (excludes the last game-over ply).
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
            gp_table.c.ply < max_ply_per_game.c.max_ply,  # exclude terminal ply
        )
    )
    if limit is not None:
        holed_game_ids_q = holed_game_ids_q.limit(limit)

    async with async_session_maker() as session:
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
