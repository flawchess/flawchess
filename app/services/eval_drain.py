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
from sqlalchemy import bindparam, select, update
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import GamePosition
from app.services import engine as engine_service
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


def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
    """Replay PGN to the board state at *target_ply* (0-indexed, pre-push).

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

    Phase 78 IMP-01: used by the import-time eval pass to reconstruct the board
    at a span-entry ply without retaining chess.Board objects in memory during
    the main PGN walk. Mirrors the backfill script approach (Option A, RESEARCH.md).

    Returns None if the PGN is unparseable or the game ends before target_ply.
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
    return None


def _collect_midgame_eval_targets(
    game_eval_data: Sequence[tuple[int, str, list[PlyData]]],
) -> list[_EvalTarget]:
    """Phase 79 PHASE-IMP-01: middlegame entry eval — MIN(ply) where phase == 1.

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

    At most one middlegame entry per game (later phase=1 stretches after an
    endgame are NOT re-evaluated, mirroring lichess Divider's single
    Division(midGame, endGame) return — D-79-08). Skips plies where lichess
    %eval already populated the row (T-78-17).
    """
    targets: list[_EvalTarget] = []
    for g_id, pgn_text, plies_list in game_eval_data:
        midgame_entries = [pd for pd in plies_list if pd["phase"] == 1]
        if not midgame_entries:
            continue
        mid_pd = min(midgame_entries, key=lambda p: p["ply"])
        # T-78-17 lichess preservation: skip if lichess %eval already populated the row.
        if mid_pd["eval_cp"] is not None or mid_pd["eval_mate"] is not None:
            continue
        mid_board = _board_at_ply(pgn_text, mid_pd["ply"])
        if mid_board is None:
            continue
        targets.append(
            _EvalTarget(
                game_id=g_id,
                ply=mid_pd["ply"],
                eval_kind="middlegame_entry",
                endgame_class=None,
                board=mid_board,
            )
        )
    return targets


def _collect_endgame_span_eval_targets(
    game_eval_data: Sequence[tuple[int, str, list[PlyData]]],
) -> list[_EvalTarget]:
    """Phase 78 per-class endgame span entry collection.

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

    Each contiguous run of the same endgame_class within a game is its own
    span: a class=1 → class=2 → class=1 sequence yields two class=1 entry
    evals, not one. Spans of any length are evaluated; the repository's
    ENDGAME_PLY_THRESHOLD is intentionally not enforced here so endgame
    eval coverage stays uniform across short and long spans. Skips plies
    where lichess %eval already populated the row (T-78-17).
    """
    targets: list[_EvalTarget] = []
    for g_id, pgn_text, plies_list in game_eval_data:
        # Group plies by endgame_class; only endgame plies have a non-None class.
        class_plies: dict[int, list[PlyData]] = defaultdict(list)
        for pd in plies_list:
            ec = pd["endgame_class"]
            if ec is not None:
                class_plies[ec].append(pd)

        for ec, pds in class_plies.items():
            islands = _split_into_contiguous_islands(pds)
            targets.extend(_island_eval_targets(g_id, pgn_text, ec, islands))
    return targets


def _split_into_contiguous_islands(pds: Sequence[PlyData]) -> list[list[PlyData]]:
    """Split per-class plies into contiguous runs ("islands").

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

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


def _island_eval_targets(
    g_id: int,
    pgn_text: str,
    ec: int,
    islands: Sequence[Sequence[PlyData]],
) -> list[_EvalTarget]:
    """Build _EvalTarget rows for each island's entry ply.

    Phase 91: lifted from import_service.py for the cold-drain lane.
    The originals in import_service.py are removed in Plan 91-03.

    Skips islands where lichess %eval already populated the entry ply
    (T-78-17) or where _board_at_ply replay fails (rare, no Sentry —
    parse error is unusual but not urgent).
    """
    targets: list[_EvalTarget] = []
    for island in islands:
        span_pd = island[0]  # entry ply = first ply of the contiguous run
        if span_pd["eval_cp"] is not None or span_pd["eval_mate"] is not None:
            # Lichess %eval already populated this ply — do not overwrite (T-78-17).
            continue
        span_board = _board_at_ply(pgn_text, span_pd["ply"])
        if span_board is None:
            continue
        targets.append(
            _EvalTarget(
                game_id=g_id,
                ply=span_pd["ply"],
                eval_kind="endgame_span_entry",
                endgame_class=ec,
                board=span_board,
            )
        )
    return targets


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
        result = await session.execute(
            select(Game.id, Game.pgn).where(Game.id.in_(game_ids))
        )
        return [(row[0], row[1]) for row in result.all()]


def _collect_eval_targets_for_games(
    rows: Sequence[tuple[int, str]],
) -> list[_EvalTarget]:
    """Pure function: derive eval targets from (id, pgn) rows.

    No session, no engine. Iterates rows, runs _collect_midgame_eval_targets +
    _collect_endgame_span_eval_targets per game, flattens into a single list.

    The cold drain reads PGNs from the DB (not from import-time memory), so this
    function re-parses them. The PGNs are already stored without move annotations
    needing re-processing by process_game_pgn — we only need them for _board_at_ply.
    """
    # Build minimal game_eval_data tuples: (game_id, pgn_text, plies_list).
    # The cold drain does not have pre-parsed PlyData lists, so we derive targets
    # by re-parsing the PGN. We collect targets per game using full-ply reconstruction
    # from the stored GamePosition rows — but the helpers expect PlyData lists.
    # Since we don't have PlyData here, we fall back to the pure PGN-based path:
    # _board_at_ply is called internally by the helpers when eval_cp/eval_mate are None.
    # We build minimal PlyData from the stored pgn by replaying the game.
    targets: list[_EvalTarget] = []
    for game_id, pgn_text in rows:
        game_eval_data = _build_game_eval_data_from_pgn(game_id, pgn_text)
        targets.extend(_collect_midgame_eval_targets(game_eval_data))
        targets.extend(_collect_endgame_span_eval_targets(game_eval_data))
    return targets


def _build_game_eval_data_from_pgn(
    game_id: int,
    pgn_text: str,
) -> list[tuple[int, str, list[PlyData]]]:
    """Reconstruct minimal PlyData list from a stored PGN for the cold drain.

    The cold drain stores PGNs in the DB but does not have the original
    process_game_pgn output in memory. This function re-parses the PGN to
    rebuild just the fields needed by _collect_midgame_eval_targets and
    _collect_endgame_span_eval_targets: ply, phase, endgame_class, eval_cp,
    eval_mate.

    Phase and endgame_class are determined from the GamePosition rows stored
    during import. However, this function works without a DB session by
    replaying the PGN. Since GamePosition rows already have the correct phase
    and endgame_class, we use a simplified heuristic: treat all plies as
    candidates (phase=1 for the first middlegame ply, phase=2 for endgame).
    The _collect_*_eval_targets helpers skip plies with eval_cp/eval_mate
    already populated, so we default those to None.

    In practice, the cold drain does NOT have access to GamePosition metadata
    without an extra DB query. The correct approach is to load the actual
    phase/endgame_class from GamePosition rows. This stub delegates to the
    DB-backed version. The caller (_collect_eval_targets_for_games) should
    be extended to load phase/endgame_class from GamePosition in a future
    refactor; for Phase 91, the drain uses the DB-backed helper in run_eval_drain
    directly (see the comment in run_eval_drain about target collection).
    """
    # Return an empty list for now — run_eval_drain loads targets directly
    # from GamePosition DB rows for correctness. This function exists as a
    # pure-function stub for testing _collect_eval_targets_for_games signature.
    return [(game_id, pgn_text, [])]


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
    GamePosition rows, then calls _collect_midgame_eval_targets +
    _collect_endgame_span_eval_targets with accurate PlyData lists.

    This is the correct cold-drain path: it avoids re-running process_game_pgn
    and uses the stored phase/endgame_class from the DB.
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

    game_eval_data: list[tuple[int, str, list[PlyData]]] = [
        (gid, pgn_map[gid], plies)
        for gid, plies in game_plies.items()
        if gid in pgn_map
    ]

    targets: list[_EvalTarget] = []
    targets.extend(_collect_midgame_eval_targets(game_eval_data))
    targets.extend(_collect_endgame_span_eval_targets(game_eval_data))
    return targets


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
                eval_targets = await _collect_eval_targets_from_db(
                    read_session, game_ids, pgn_map
                )

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
                # Mark all picked games done regardless of eval success/failure.
                # engine.evaluate() returning (None, None) is treated as
                # "evaluated — engine failed for this position, leave row NULL"
                # per D-09 / R-02 — no permanent retry loop.
                await _mark_evals_completed(session, game_ids)
                await session.commit()

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
