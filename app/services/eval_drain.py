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
    """

    game_id: int
    ply: int
    full_hash: int
    board: chess.Board
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None = None


def _collect_full_ply_targets(
    game_id: int,
    pgn_text: str,
    game_positions_rows: Sequence[tuple[int, int, int | None, int | None]],
) -> list[_FullPlyEvalTarget]:
    """Collect one target per non-terminal ply (EVAL-01).

    game_positions_rows: (ply, full_hash, eval_cp, eval_mate) loaded from DB.

    Terminal exclusion: mainline iterator yields positions BEFORE each push.
    The post-last-move board (game-over) is never visited — no is_game_over()
    guard needed during the walk. Simply skip adding a snapshot after the loop.

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
    for ply, node in enumerate(game.mainline()):
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
    # board is now the terminal position — NOT added.
    return targets


async def _fetch_dedup_evals(
    session: AsyncSession,
    full_hashes: Sequence[int],
) -> dict[int, tuple[int | None, int | None, str | None]]:
    """Batch-fetch parity evals + best_move for opening-region hashes (EVAL-03, D-116-02).

    Marker gate: source games must have full_evals_completed_at IS NOT NULL
    (parity by construction). Do NOT use evals_completed_at here — that gate
    includes depth-15 source rows (Pitfall 4, RESEARCH.md).

    Engine-source-only gate (WR-02, D-117-07 repointed): source games must have
    lichess_evals_at IS NULL. Lichess %eval values are post-move evals — a row
    at ply k stores the eval of the position AFTER its move (zobrist.py:182),
    while the row's full_hash is the position BEFORE the move. Engine-written
    rows (this drain) evaluate the pre-push position, so only those are
    position-keyed by construction and safe to transplant cross-game by
    full_hash. Previously gated on white_blunders IS NULL (changed by D-117-07:
    after oracle counts are filled for engine games, white_blunders IS NOT NULL
    for engine games too — using it would wrongly exclude engine-written sources).

    Also returns best_move (D-117-01): transplant alongside eval_cp so
    dedup'd opening-region plies carry the engine's best-move suggestion.

    Returns {full_hash: (eval_cp, eval_mate, best_move)} for hashes with at
    least one hit.
    """
    if not full_hashes:
        return {}
    result = await session.execute(
        select(
            GamePosition.full_hash,
            GamePosition.eval_cp,
            GamePosition.eval_mate,
            GamePosition.best_move,
        )
        .join(Game, GamePosition.game_id == Game.id)
        .where(
            GamePosition.full_hash.in_(full_hashes),
            GamePosition.ply <= _DEDUP_MAX_PLY,
            Game.full_evals_completed_at.isnot(None),
            # WR-02 repointed (D-117-07): lichess_evals_at IS NULL = engine-written source.
            Game.lichess_evals_at.is_(None),
            sa.or_(GamePosition.eval_cp.isnot(None), GamePosition.eval_mate.isnot(None)),
        )
        .distinct(GamePosition.full_hash)
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
    """Resolve the eval + best_move + pv_string to write for one ply (pure; WR-04).

    Priority: dedup hit (EVAL-03, opening region only) > engine result >
    (None, None, None, None) hole (D-116-07).

    Dedup transplants (eval_cp, eval_mate, best_move) from the source row.
    pv_string is always None for dedup'd positions (the per-flaw PV is only
    written at flaw-adjacent plies N+1, not here — D-117-02).
    """
    if target.ply <= _DEDUP_MAX_PLY and target.full_hash in dedup_map:
        eval_cp, eval_mate, best_move = dedup_map[target.full_hash]
        return eval_cp, eval_mate, best_move, None
    return engine_result_map.get(target.ply, (None, None, None, None))


async def _apply_full_eval_results(
    session: AsyncSession,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    is_analyzed: bool,
) -> int:
    """Write resolved full-ply evals + best_move to GamePosition rows (WR-04 extraction).

    Mirrors _apply_eval_results for the entry-ply drain: UPDATEs run
    sequentially against the caller-owned session (CLAUDE.md hard rule:
    AsyncSession is not safe under asyncio.gather); the caller commits.

    D-116-04 is_analyzed gate (repointed to lichess_evals_at by D-117-07):
    - is_analyzed=True: lichess %evals present; preserve existing non-NULL
      eval_cp/eval_mate rows (T-78-17). best_move is always written since it is
      a new column — lichess games never had best_move set.
    - is_analyzed=False: legacy depth-15 evals; overwrite all (D-116-03).

    Returns the number of failed (NULL-hole) plies. Sentry reporting is the
    caller's responsibility — ONE aggregated event per game, never per ply
    (WR-05: a full game can have 60-600 plies; per-ply messages would flood
    Sentry whenever the engine pool degrades).
    """
    failed_ply_count = 0
    for target in targets:
        eval_cp, eval_mate, best_move, _pv_string = _resolve_full_eval(
            target, dedup_map, engine_result_map
        )
        # _pv_string intentionally discarded here: pv is written ONLY at flaw-adjacent
        # plies (ply = flaw_ply + 1) in _classify_and_fill_oracle below (D-117-02).
        # Do NOT add a general pv write here — that would overwrite flaw-PV selectivity.

        if eval_cp is None and eval_mate is None:
            # D-116-07: engine failure — leave NULL hole; counted for the
            # caller's per-game aggregated Sentry event (WR-05).
            failed_ply_count += 1
            continue

        # D-116-04 preservation (repointed by D-117-07: is_analyzed = lichess_evals_at IS NOT NULL).
        # Preserve lichess %evals for is_analyzed games (T-78-17). Belt-and-braces — covered
        # plies are already filtered out before the gather (WR-01). best_move is always written
        # (new column, not part of the lichess eval set).
        if is_analyzed and (target.eval_cp is not None or target.eval_mate is not None):
            # Preserve lichess evals; only write best_move if we have it.
            if best_move is not None:
                stmt = update(GamePosition).where(
                    GamePosition.game_id == target.game_id,
                    GamePosition.ply == target.ply,
                )
                await session.execute(stmt.values(best_move=best_move))
            continue

        stmt = update(GamePosition).where(
            GamePosition.game_id == target.game_id,
            GamePosition.ply == target.ply,
        )
        await session.execute(
            stmt.values(eval_cp=eval_cp, eval_mate=eval_mate, best_move=best_move)
        )
    return failed_ply_count


async def _mark_full_evals_completed(session: AsyncSession, game_id: int) -> None:
    """Mark one game as fully analyzed (EVAL-05, D-116-07).

    Sets full_evals_completed_at unconditionally — even when some plies are NULL
    holes (engine failure). One UPDATE per game (single tick), not batch.
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
    is_analyzed: bool = claimed.is_analyzed
    job_id: int | None = claimed.job_id

    # Step 2: load PGN + game_positions rows for this game.
    # Build targets via _collect_full_ply_targets; partition dedup candidates.
    # Short read session, then close.
    async with async_session_maker() as load_session:
        pgn_result = await load_session.execute(select(Game.pgn).where(Game.id == game_id))
        pgn_text_scalar = pgn_result.scalar_one_or_none()
        if pgn_text_scalar is None:
            # Game deleted between claim and load — nothing to do.
            return False
        pgn_text: str = pgn_text_scalar

        pos_result = await load_session.execute(
            select(
                GamePosition.ply,
                GamePosition.full_hash,
                GamePosition.eval_cp,
                GamePosition.eval_mate,
            ).where(GamePosition.game_id == game_id)
        )
        gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]

        # Collect one target per non-terminal ply (EVAL-01).
        targets = _collect_full_ply_targets(game_id, pgn_text, gp_rows)

        # WR-01: for is_analyzed (lichess %eval) games, plies whose row already
        # carries a non-NULL eval are preserved at write time (D-116-04 / T-78-17).
        # Filtering here avoids burning 1M-node calls whose results are discarded.
        if is_analyzed:
            targets = [t for t in targets if t.eval_cp is None and t.eval_mate is None]

        # Partition opening-region hashes for dedup (EVAL-03).
        dedup_hashes = [t.full_hash for t in targets if t.ply <= _DEDUP_MAX_PLY]
        dedup_map = await _fetch_dedup_evals(load_session, dedup_hashes)
    # load_session is now closed.

    # Step 3: asyncio.gather — NO session open.
    # CLAUDE.md hard rule: gather must never run inside an AsyncSession scope.
    # Targets with a dedup hit skip the engine call (EVAL-03).
    # Phase 117 EVAL-04: use evaluate_nodes_with_pv to capture best_move + PV string.
    # Tier-1 (QUEUE-03): fan ALL of one game's plies across the pool simultaneously.
    # Tiers 2/3: same gather — the distinction is how the game was claimed, not how it's analyzed.
    engine_targets = [t for t in targets if t.ply > _DEDUP_MAX_PLY or t.full_hash not in dedup_map]
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
    async with async_session_maker() as write_session:
        failed_ply_count = await _apply_full_eval_results(
            write_session, targets, dedup_map, engine_result_map, is_analyzed
        )
        if failed_ply_count:
            # WR-05: ONE aggregated Sentry event per game (never per ply).
            sentry_sdk.set_context(
                "eval", {"game_id": game_id, "failed_ply_count": failed_ply_count}
            )
            sentry_sdk.set_tag("source", "full_eval_drain")
            sentry_sdk.capture_message("full-drain engine returned None tuple", level="warning")

        # EVAL-06 / D-117-08: classify game_flaws + fill oracle columns + write flaw PVs.
        # Runs AFTER _apply_full_eval_results so eval_cp is visible for classification.
        # Runs BEFORE the completion markers so evals + flaws commit atomically (T-117-11).
        await _classify_and_fill_oracle(write_session, game_id, engine_result_map)

        # D-116-07: mark eval-complete even with partial NULL holes (the all-fail
        # case is intercepted by the circuit breaker above).
        await _mark_full_evals_completed(write_session, game_id)

        # D-117-12: mark best_move/PV-complete in the same transaction.
        await _mark_full_pv_completed(write_session, game_id)

        # QUEUE-06: report the leased job as complete (tier-3 has no job row — job_id is None).
        if job_id is not None:
            from app.models.eval_jobs import EvalJob

            jobs_table = EvalJob.__table__
            now_ts = datetime.now(timezone.utc)
            await write_session.execute(
                update(jobs_table)  # ty: ignore[invalid-argument-type]
                .where(
                    jobs_table.c.id == job_id,
                    jobs_table.c.status == "leased",
                )
                .values(status="completed", completed_at=now_ts)
            )

        await write_session.commit()

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
