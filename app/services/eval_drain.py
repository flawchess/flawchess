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
from sqlalchemy import bindparam, select, update
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.game_repository import count_pending_evals, users_with_zero_pending
from app.services import engine as engine_service
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
                # Mark all picked games done regardless of eval success/failure.
                # engine.evaluate() returning (None, None) is treated as
                # "evaluated — engine failed for this position, leave row NULL"
                # per D-09 / R-02 — no permanent retry loop.
                await _mark_evals_completed(session, game_ids)
                await session.commit()

            # Phase 94.1 D-01 / Pitfall 1: Stage B fires for users whose pending-eval
            # count just transitioned to zero. Group just-drained game_ids by user_id,
            # then in ONE aggregated query (WR-01 fix, 94.1-12) filter to users whose
            # pending-eval count is now zero, then fan-out Stage B.
            # Fresh read session: never share the eval-write session across coroutines.
            async with async_session_maker() as read_session:
                user_id_rows = await read_session.execute(
                    select(Game.user_id).distinct().where(Game.id.in_(game_ids))
                )
                affected_user_ids = [row[0] for row in user_id_rows.all()]
                if affected_user_ids:
                    zero_pending = await users_with_zero_pending(
                        read_session, affected_user_ids
                    )
                    for uid in zero_pending:
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
