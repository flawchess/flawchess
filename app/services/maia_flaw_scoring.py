"""maia_flaw_scoring.py — shared post-commit Maia scorer for game_flaws rows (Phase 247, D-13).

Every lane that writes ``game_flaws`` (local drain, atomic remote submit, tier-4 blob
submit, backfill script) calls into this one module AFTER its own write transaction has
committed, so the ~1 s of CPU per game never runs inside an eval write transaction.

Pipeline for one game, with no AsyncSession open during inference:

1. ``load_game_maia_inputs``: short read session (game rating metadata plus every flaw's
   fen, ``game_positions.best_move`` and the raw ``missed_pv_lines[0].su``).
2. ``score_game`` (sync, CPU, run in ``asyncio.to_thread``): one ``full_policy`` call per
   scorable flaw (D-04), the eight D-01 values derived by ``compute_maia_flaw_stats``.
3. ``write_game_maia_scores``: short write session that takes
   ``pg_advisory_xact_lock`` per game (ascending key order), re-reads the inputs
   fingerprint and writes the eight columns plus the stamp only when the fingerprint is
   unchanged. A mismatch means a concurrent apply reshaped the flaws; the game is left
   unstamped for the next pass.

The stamp ``games.maia_flaws_completed_at`` is only ever set when a Maia session was
loaded AND the pass completed without an exception (D-05 guardrail, decided from
``is_maia_available()``, never from row counts).
"""

from __future__ import annotations

import asyncio
import io
import logging
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast

import chess
import chess.pgn
import sentry_sdk
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import (
    bulk_update_flaw_maia_stats,
    mark_maia_flaws_completed,
)
from app.schemas.normalization import Platform, TimeControlBucket
from app.services import maia_engine
from app.services.best_move_candidates import pinned_elo_for_mover
from app.services.eval_apply import _FullPlyEvalTarget, _game_write_lock_key
from app.services.maia_engine import full_policy
from app.services.maia_flaw_stats import (
    MaiaReason,
    compute_maia_flaw_stats,
    null_maia_stats,
)
from app.services.normalization import is_correspondence_time_control

logger = logging.getLogger(__name__)

ScoringSource = Literal["full_eval_drain", "remote_eval_worker", "flaw_blob_submit", "backfill"]
GameOutcome = Literal["stamped", "fingerprint_changed", "already_stamped", "game_missing"]

# (ply, game_flaws.fen, game_positions.best_move, raw missed_pv_lines[0].su)
FlawFingerprint = tuple[int, str, str | None, str | None]

# ply -> (pre-push board, played UCI)
BoardsByPly = Mapping[int, tuple[chess.Board, str]]

# One write transaction holds one advisory lock per game; cap it so a batch caller can
# never exhaust the lock table.
MAX_GAMES_PER_WRITE_TXN: int = 50

# game_flaws.missed_pv_lines[0].su, i.e. Stockfish's second-best move at the flaw ply,
# extracted raw (no cleanup) so plan-01's D-15 rule decides what is usable.
_MISSED_PV_FIRST_NODE_PATH: str = "0"
_MISSED_PV_SECOND_UCI_KEY: str = "su"


class MaiaInferenceUnavailableError(RuntimeError):
    """full_policy returned None although a Maia session was reported available."""


@dataclass(frozen=True, slots=True)
class FlawMaiaInput:
    ply: int
    fen: str
    best_uci: str | None
    second_uci: str | None


def fingerprint_of(flaws: Sequence[FlawMaiaInput]) -> frozenset[FlawFingerprint]:
    return frozenset((f.ply, f.fen, f.best_uci, f.second_uci) for f in flaws)


@dataclass(frozen=True, slots=True)
class GameMaiaInputs:
    game_id: int
    user_id: int
    pgn: str
    white_rating: int | None
    black_rating: int | None
    platform: Platform
    time_control_bucket: TimeControlBucket | None
    is_correspondence: bool
    flaws: tuple[FlawMaiaInput, ...]

    def fingerprint(self) -> frozenset[FlawFingerprint]:
        return fingerprint_of(self.flaws)


@dataclass(slots=True)
class GameMaiaScore:
    game_id: int
    user_id: int
    fingerprint: frozenset[FlawFingerprint]
    rows: list[dict[str, Any]]
    reasons: Counter[MaiaReason]


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def _flaw_fingerprint_select(game_ids: Sequence[int]) -> sa.Select[Any]:
    """One flaw SELECT shared by the load and the in-lock re-read (same columns, so the
    fingerprints are comparable)."""
    second_uci = sa.func.jsonb_extract_path_text(
        GameFlaw.missed_pv_lines,
        sa.literal(_MISSED_PV_FIRST_NODE_PATH, type_=sa.String),
        sa.literal(_MISSED_PV_SECOND_UCI_KEY, type_=sa.String),
    )
    return (
        sa.select(
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.fen,
            GamePosition.best_move,
            second_uci,
        )
        .select_from(GameFlaw)
        .outerjoin(
            GamePosition,
            sa.and_(
                GamePosition.game_id == GameFlaw.game_id,
                GamePosition.user_id == GameFlaw.user_id,
                GamePosition.ply == GameFlaw.ply,
            ),
        )
        .where(GameFlaw.game_id.in_(list(game_ids)))
        .order_by(GameFlaw.game_id, GameFlaw.ply)
    )


async def _read_flaw_inputs(
    session: AsyncSession, game_ids: Sequence[int]
) -> dict[int, list[FlawMaiaInput]]:
    result = await session.execute(_flaw_fingerprint_select(game_ids))
    by_game: dict[int, list[FlawMaiaInput]] = {}
    for game_id, ply, fen, best_move, second_uci in result.all():
        by_game.setdefault(game_id, []).append(
            FlawMaiaInput(ply=ply, fen=fen, best_uci=best_move, second_uci=second_uci)
        )
    return by_game


async def load_game_maia_inputs(
    session: AsyncSession, game_ids: Sequence[int]
) -> dict[int, GameMaiaInputs]:
    """Load scoring inputs for the given games. Games that do not exist are absent."""
    if not game_ids:
        return {}
    game_rows = (
        await session.execute(
            sa.select(
                Game.id,
                Game.user_id,
                Game.pgn,
                Game.white_rating,
                Game.black_rating,
                Game.platform,
                Game.time_control_bucket,
                Game.time_control_str,
            ).where(Game.id.in_(list(game_ids)))
        )
    ).all()
    flaws_by_game = await _read_flaw_inputs(session, [row[0] for row in game_rows])
    inputs: dict[int, GameMaiaInputs] = {}
    for gid, uid, pgn, white, black, platform, bucket, tc_str in game_rows:
        inputs[gid] = GameMaiaInputs(
            game_id=gid,
            user_id=uid,
            pgn=pgn,
            white_rating=white,
            black_rating=black,
            platform=cast(Platform, platform),
            time_control_bucket=cast("TimeControlBucket | None", bucket),
            is_correspondence=is_correspondence_time_control(tc_str),
            flaws=tuple(flaws_by_game.get(gid, [])),
        )
    return inputs


# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------


def boards_from_targets(
    targets: Sequence[_FullPlyEvalTarget],
) -> dict[int, tuple[chess.Board, str]]:
    """ply -> (pre-push board, played UCI) from the drain's in-memory targets.

    Terminal eval-donor targets have no played move and are skipped.
    """
    return {
        t.ply: (t.board, t.move_uci)
        for t in targets
        if not t.is_terminal and t.move_uci is not None
    }


def replay_flaw_boards(
    pgn_text: str, plies: Collection[int]
) -> tuple[dict[int, tuple[chess.Board, str]], MaiaReason | None]:
    """Rebuild the pre-push board and played UCI for each wanted ply from the PGN (D-06).

    Used by callers without in-memory targets (tier-4 blob submit, backfill). The board
    is a full board (castling and en-passant state intact), so the FEN handed to
    full_policy is exact. Returns ({}, reason) when the whole game is unusable: an
    unparseable PGN or an invalid custom root (same guard as _collect_full_ply_targets).
    Plies never reached are simply absent; score_game counts them as ply_beyond_mainline.
    Counted buckets, not Sentry events: the drain already reports parse failures at its
    own choke point.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return {}, "pgn_unparseable"
    if game is None:
        return {}, "pgn_unparseable"
    board = game.board()
    if not board.is_valid():
        return {}, "invalid_root"
    wanted = set(plies)
    found: dict[int, tuple[chess.Board, str]] = {}
    for ply, node in enumerate(game.mainline()):
        if len(found) == len(wanted):
            break
        if ply in wanted:
            # Snapshot BEFORE the push: the flaw's decision position.
            found[ply] = (board.copy(stack=False), node.move.uci())
        board.push(node.move)
    return found, None


# ---------------------------------------------------------------------------
# Score (sync, CPU)
# ---------------------------------------------------------------------------


def _derive_flaw_stats(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
) -> tuple[dict[str, Any] | None, list[MaiaReason]]:
    """Derive the eight values for one flaw, or (None, [reason]) when it is unscorable.

    Exactly one full_policy call per scorable flaw (D-04): the guards that make a flaw
    unscorable all run before it.
    """
    entry = boards.get(flaw.ply)
    if entry is None:
        return None, ["ply_beyond_mainline"]
    board, played_uci = entry
    if board.board_fen() != flaw.fen:
        return None, ["fen_mismatch"]
    # board.turn, not ply parity: a custom-FEN game may start with Black to move.
    raw_rating = inputs.white_rating if board.turn == chess.WHITE else inputs.black_rating
    if raw_rating is None:
        return None, ["no_rating"]
    elo = pinned_elo_for_mover(
        raw_rating=raw_rating,
        platform=inputs.platform,
        time_control_bucket=inputs.time_control_bucket,
        is_correspondence=inputs.is_correspondence,
    )
    probs = full_policy(board.fen(), elo)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
    stats, reasons = compute_maia_flaw_stats(
        probs,
        played_uci=played_uci,
        best_uci=flaw.best_uci,
        second_uci=flaw.second_uci,
    )
    return (dict(stats) if stats is not None else None), reasons


def _flaw_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One write row (PK plus all eight keys) for a flaw; counts its reasons."""
    stats: dict[str, Any] | None = None
    if game_reason is not None:
        reasons[game_reason] += 1
    else:
        stats, flaw_reasons = _derive_flaw_stats(inputs, flaw, boards)
        reasons.update(flaw_reasons)
    row: dict[str, Any] = {
        "user_id": inputs.user_id,
        "game_id": inputs.game_id,
        "ply": flaw.ply,
    }
    row.update(stats if stats is not None else null_maia_stats())
    return row


def score_game(inputs: GameMaiaInputs, boards: BoardsByPly | None) -> GameMaiaScore:
    """Score every flaw of one game (sync, CPU, no I/O).

    boards None means "replay from the PGN" (callers without in-memory targets). Every
    flaw yields a row carrying all eight keys (None for an unscorable flaw), so a
    re-score never leaves a stale value (D-08).
    """
    game_reason: MaiaReason | None = None
    if boards is None:
        boards, game_reason = replay_flaw_boards(inputs.pgn, {f.ply for f in inputs.flaws})
    reasons: Counter[MaiaReason] = Counter()
    rows = [_flaw_row(inputs, flaw, boards, game_reason, reasons) for flaw in inputs.flaws]
    return GameMaiaScore(
        game_id=inputs.game_id,
        user_id=inputs.user_id,
        fingerprint=inputs.fingerprint(),
        rows=rows,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

_LOCK_GAMES_SQL = sa.text(
    "SELECT pg_advisory_xact_lock(k) FROM ("
    " SELECT k FROM unnest(CAST(:keys AS bigint[])) WITH ORDINALITY AS t(k, ord)"
    " ORDER BY ord OFFSET 0) AS ordered_keys"
)


async def _lock_games_ascending(session: AsyncSession, game_ids: Sequence[int]) -> None:
    """Take the per-game write advisory lock for every game in ascending key order.

    One statement over the Python-sorted key array; unnest WITH ORDINALITY preserves the
    array order and the key is monotonic in game_id, so concurrent batch writers can
    never deadlock against each other.
    """
    keys = sorted(_game_write_lock_key(gid) for gid in game_ids)
    await session.execute(_LOCK_GAMES_SQL, {"keys": keys})


def _outcome_for(
    score: GameMaiaScore,
    current_fingerprint: frozenset[FlawFingerprint] | None,
    stamp_state: tuple[bool, bool],
    require_unstamped: bool,
) -> GameOutcome:
    """Decide one game's write outcome. stamp_state is (game exists, already stamped)."""
    exists, already_stamped = stamp_state
    if not exists:
        return "game_missing"
    if require_unstamped and already_stamped:
        return "already_stamped"
    if (current_fingerprint or frozenset()) != score.fingerprint:
        return "fingerprint_changed"
    return "stamped"


async def write_game_maia_scores(
    session: AsyncSession,
    scores: Sequence[GameMaiaScore],
    *,
    require_unstamped: bool,
) -> dict[int, GameOutcome]:
    """Write the eight columns plus the stamp for every game whose inputs are unchanged.

    The caller commits. All games are advisory-locked (ascending order) before the
    fingerprint re-read, so the fingerprint cannot change between the check and the
    write.
    """
    if len(scores) > MAX_GAMES_PER_WRITE_TXN:
        raise ValueError("too many games for one write transaction")
    if not scores:
        return {}
    ordered = sorted(scores, key=lambda s: s.game_id)
    game_ids = [s.game_id for s in ordered]
    await _lock_games_ascending(session, game_ids)

    current_flaws = await _read_flaw_inputs(session, game_ids)
    stamp_rows = (
        await session.execute(
            sa.select(Game.id, Game.maia_flaws_completed_at).where(Game.id.in_(game_ids))
        )
    ).all()
    stamp_by_game = {gid: stamp for gid, stamp in stamp_rows}

    outcomes: dict[int, GameOutcome] = {}
    rows_to_write: list[dict[str, Any]] = []
    for score in ordered:
        current = current_flaws.get(score.game_id)
        current_fp = fingerprint_of(current) if current is not None else None
        exists = score.game_id in stamp_by_game
        already = stamp_by_game.get(score.game_id) is not None
        outcome = _outcome_for(score, current_fp, (exists, already), require_unstamped)
        outcomes[score.game_id] = outcome
        if outcome == "stamped":
            rows_to_write.extend(score.rows)

    stamped_ids = [gid for gid, outcome in outcomes.items() if outcome == "stamped"]
    await bulk_update_flaw_maia_stats(session, rows_to_write)
    await mark_maia_flaws_completed(session, stamped_ids)
    return outcomes


# ---------------------------------------------------------------------------
# Entry point for the post-commit lanes
# ---------------------------------------------------------------------------


async def score_game_flaws_after_apply(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
    *,
    targets: Sequence[_FullPlyEvalTarget] | None,
    source: ScoringSource,
) -> bool:
    """Score one game's flaws and stamp it, AFTER the lane's own write has committed.

    Returns True when the game was stamped. Never raises: a failure is reported to
    Sentry and leaves the game unstamped (the backfill picks it up later).

    D-05: with Maia unavailable nothing is written and nothing is stamped.
    D-13: short read session (closed), inference in a worker thread with no session
    open, then a short write session that locks, re-checks the fingerprint and commits.
    """
    if not maia_engine.is_maia_available():
        return False
    try:
        async with session_maker() as read_session:
            inputs = (await load_game_maia_inputs(read_session, [game_id])).get(game_id)
        if inputs is None:
            return False
        boards = boards_from_targets(targets) if targets else None
        score = await asyncio.to_thread(score_game, inputs, boards)
        async with session_maker() as write_session:
            outcomes = await write_game_maia_scores(write_session, [score], require_unstamped=False)
            await write_session.commit()
        return outcomes.get(game_id) == "stamped"
    except StaleDataError:
        # The game was deleted between the in-lock re-read and the UPDATE (same race
        # class as FLAWCHESS-8D). Expected; not a bug.
        logger.info("maia_flaw_scoring: game deleted mid-write, skipping stamp")
        return False
    except Exception:
        # Maia stats are secondary: never abort the lane, never stamp after a failure.
        sentry_sdk.set_context("maia_flaws", {"game_id": game_id, "lane": source})
        sentry_sdk.set_tag("source", "maia_flaws")
        sentry_sdk.capture_exception()
        return False


def format_maia_backfill_reminder(unstamped_games: int, db: str) -> str | None:
    """One-line reminder printed by reclassification scripts that cleared Maia stamps (D-11).

    None when no game was unstamped.
    """
    if unstamped_games <= 0:
        return None
    return (
        f"{unstamped_games} games lost their Maia flaw stats stamp; re-score them with: "
        f"uv run python scripts/backfill_maia_flaws.py --db {db}"
    )


__all__ = [
    "BoardsByPly",
    "FlawFingerprint",
    "FlawMaiaInput",
    "GameMaiaInputs",
    "GameMaiaScore",
    "GameOutcome",
    "MAX_GAMES_PER_WRITE_TXN",
    "MaiaInferenceUnavailableError",
    "ScoringSource",
    "boards_from_targets",
    "format_maia_backfill_reminder",
    "load_game_maia_inputs",
    "replay_flaw_boards",
    "score_game",
    "score_game_flaws_after_apply",
    "write_game_maia_scores",
]
