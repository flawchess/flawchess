"""maia_flaw_scoring.py — shared post-commit Maia scorer for game_flaws rows (Phase 247, D-13).

Every lane that writes ``game_flaws`` (local drain, atomic remote submit, tier-4 blob
submit, backfill script) calls into this one module AFTER its own write transaction has
committed, so the ~1 s of CPU per game never runs inside an eval write transaction.

Pipeline for one game, with no AsyncSession open during inference:

1. ``load_game_maia_inputs``: short read session (game rating metadata plus every flaw's
   fen, ``game_positions.best_move`` and the raw ``missed_pv_lines[0].su``).
2. ``score_game`` (sync, CPU, run in ``asyncio.to_thread``): one ``full_policy`` call per
   scorable flaw plus one per scorable user-side blunder (the post-blunder position at the
   blunderer's Elo). The eight D-01 values come from ``compute_maia_flaw_stats``. The
   post-blunder policy feeds both the Phase 248 refutation pair (Maia's probability and rank
   for Stockfish's best reply, ``compute_refutation_stats``) and the Phase 250 reply spread
   (D-07: no extra inference). The Phase 250 line facts (``line_facts`` on the stored line at
   ply + 1) and the facepalm score are derived from those plus the base values.
3. ``write_game_maia_scores``: short write session that takes
   ``pg_advisory_xact_lock`` per game (ascending key order), re-reads the inputs
   fingerprint and writes the eighteen columns plus the four stamps only when the
   fingerprint is unchanged. A mismatch means a concurrent apply reshaped the flaws (or
   changed a severity, a ply+1 best move or the stored ply+1 line); the game is left
   unstamped for the next pass.

The stamps ``games.maia_flaws_completed_at``, ``games.maia_refutation_completed_at``,
``games.facepalm_spread_completed_at`` and ``games.facepalm_line_completed_at`` are only
ever set together in full mode, when a Maia session was loaded AND the pass completed
without an exception (D-05 / D-09 guardrail, decided from ``is_maia_available()``, never
from row counts). Games with zero user-side blunders are stamped too. Refutation mode
(Phase 248 D-10) stamps only ``maia_refutation_completed_at``.

Phase 250 adds two backfill-only modes (D-08, D-18) that touch user-side blunders only: spread
mode (one post-blunder inference per blunder; writes the eight facepalm keys from the STORED
``maia_played_prob``) and line mode (no Maia at all; recomputes the six line keys and the score
from the stored line, ``maia_played_prob`` and ``maia_reply_spread``).
"""

from __future__ import annotations

import asyncio
import io
import logging
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

import chess
import chess.pgn
import sentry_sdk
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import StaleDataError

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import (
    _SEVERITY_INT,
    FACEPALM_COLUMNS,
    bulk_update_flaw_maia_stats,
    mark_facepalm_line_completed,
    mark_facepalm_spread_completed,
    mark_maia_flaws_completed,
    mark_maia_refutation_completed,
)
from app.repositories.query_utils import mover_is_white_at_ply
from app.schemas.normalization import Platform, TimeControlBucket
from app.services import maia_engine
from app.services.best_move_candidates import pinned_elo_for_mover
from app.services.blunder_check_rules import LINE_DEPTH
from app.services.eval_apply import _FullPlyEvalTarget, _game_write_lock_key
from app.services.facepalm_score import facepalm_score
from app.services.line_material import line_facts
from app.services.maia_engine import full_policy
from app.services.maia_flaw_stats import (
    FacepalmStats,
    MaiaFlawStats,
    MaiaReason,
    MaiaRefutationStats,
    compute_maia_flaw_stats,
    compute_refutation_stats,
    null_facepalm_stats,
    null_maia_stats,
    null_refutation_stats,
    reply_spread,
)
from app.services.normalization import is_correspondence_time_control

logger = logging.getLogger(__name__)

ScoringSource = Literal["full_eval_drain", "remote_eval_worker", "flaw_blob_submit", "backfill"]
GameOutcome = Literal["stamped", "fingerprint_changed", "already_stamped", "game_missing"]
# "full": all eighteen values per flaw plus the four stamps. "refutation" (Phase 248 D-10): only
# the refutation pair of user-side blunders plus the refutation stamp (everything else untouched).
# "spread" (Phase 250 D-08): the eight facepalm keys of user-side blunders from one post-blunder
# inference each, reading the stored maia_played_prob; stamps the spread and line stamps.
# "line" (Phase 250 D-18): the six line keys plus facepalm_score of user-side blunders from the
# stored line, played prob and spread; no Maia, stamps only the line stamp (cutoff-aware).
ScoringMode = Literal["full", "refutation", "spread", "line"]

# (ply, game_flaws.fen, game_positions.best_move, raw missed_pv_lines[0].su,
#  game_flaws.severity, refutation UCI = COALESCE(best_move, first pv token) at ply + 1,
#  the stored line game_positions.pv at ply + 1). The line is part of the fingerprint
# because a Phase 252 repair can rewrite it while keeping its first token, so the
# refutation UCI alone would not notice the change (250 D-07): stale line facts must never
# be written.
FlawFingerprint = tuple[int, str, str | None, str | None, int, str | None, str | None]

# ply -> (pre-push board, played UCI)
BoardsByPly = Mapping[int, tuple[chess.Board, str]]

# One write transaction holds one advisory lock per game; cap it so a batch caller can
# never exhaust the lock table.
MAX_GAMES_PER_WRITE_TXN: int = 50

# game_flaws.missed_pv_lines[0].su, i.e. Stockfish's second-best move at the flaw ply,
# extracted raw (no cleanup) so plan-01's D-15 rule decides what is usable.
_MISSED_PV_FIRST_NODE_PATH: str = "0"
_MISSED_PV_SECOND_UCI_KEY: str = "su"

# game_positions.pv is a space-joined UCI line (game_position.py); its first token is the
# refutation fallback when best_move is NULL at ply + 1 (D-20).
REFUTATION_PV_SEPARATOR: str = " "


class MaiaInferenceUnavailableError(RuntimeError):
    """full_policy returned None although a Maia session was reported available."""


@dataclass(frozen=True, slots=True)
class FlawMaiaInput:
    ply: int
    fen: str
    best_uci: str | None
    second_uci: str | None
    severity: int
    # Stockfish's best reply after the flaw move (D-02/D-20), None when no row carries one.
    refutation_uci: str | None
    # True when best_move was NULL at ply + 1 and the first pv token stood in (report only).
    refutation_from_pv: bool
    # The stored line game_positions.pv at ply + 1 (space-separated UCI starting with the
    # opponent's reply), None when absent. Input of the Phase 250 line facts.
    refutation_pv: str | None
    # The already stored game_flaws.maia_played_prob / maia_reply_spread. Inputs of the spread
    # and line modes (which must not re-run the base inference), required so a new construction
    # site cannot forget them. Deliberately NOT part of the fingerprint: they are derived values,
    # deterministic from the fingerprinted inputs, and including them would make every hook write
    # look like a concurrent reshape.
    stored_played_prob: float | None
    stored_reply_spread: float | None


def fingerprint_of(flaws: Sequence[FlawMaiaInput]) -> frozenset[FlawFingerprint]:
    return frozenset(
        (f.ply, f.fen, f.best_uci, f.second_uci, f.severity, f.refutation_uci, f.refutation_pv)
        for f in flaws
    )


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
    user_color: Literal["white", "black"]
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
    # Counts over in-scope (user-side blunder) flaws, for the backfill report.
    user_blunders: int = 0
    refutations_from_pv: int = 0
    # Rows that carry a reply spread / a facepalm score (spread, line and full modes).
    spreads_scored: int = 0
    scores_set: int = 0
    # Decides which keys `rows` carry and which stamps the write sets.
    mode: ScoringMode = "full"


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
    # Phase 248 (D-02/D-20): the refutation is the engine's best reply in the position
    # AFTER the flaw move, stored at ply + 1 (best_move is decision-ply keyed, not shifted).
    # best_move is NULL on a terminal row, where the refutation PV's first token stands in.
    gp_next = aliased(GamePosition)
    refutation_uci = sa.func.coalesce(
        gp_next.best_move,
        sa.func.nullif(sa.func.split_part(gp_next.pv, REFUTATION_PV_SEPARATOR, 1), ""),
    )
    return (
        sa.select(
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.fen,
            GameFlaw.severity,
            GamePosition.best_move,
            second_uci,
            gp_next.best_move,
            refutation_uci,
            gp_next.pv,
            GameFlaw.maia_played_prob,
            GameFlaw.maia_reply_spread,
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
        .outerjoin(
            gp_next,
            sa.and_(
                gp_next.game_id == GameFlaw.game_id,
                gp_next.user_id == GameFlaw.user_id,
                gp_next.ply == GameFlaw.ply + 1,
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
    for (
        game_id,
        ply,
        fen,
        severity,
        best_move,
        second_uci,
        next_best,
        refutation,
        next_pv,
        stored_played_prob,
        stored_reply_spread,
    ) in result.all():
        by_game.setdefault(game_id, []).append(
            FlawMaiaInput(
                ply=ply,
                fen=fen,
                best_uci=best_move,
                second_uci=second_uci,
                severity=severity,
                refutation_uci=refutation,
                refutation_from_pv=next_best is None and refutation is not None,
                refutation_pv=next_pv,
                stored_played_prob=stored_played_prob,
                stored_reply_spread=stored_reply_spread,
            )
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
                Game.user_color,
            ).where(Game.id.in_(list(game_ids)))
        )
    ).all()
    flaws_by_game = await _read_flaw_inputs(session, [row[0] for row in game_rows])
    inputs: dict[int, GameMaiaInputs] = {}
    for gid, uid, pgn, white, black, platform, bucket, tc_str, user_color in game_rows:
        inputs[gid] = GameMaiaInputs(
            game_id=gid,
            user_id=uid,
            pgn=pgn,
            white_rating=white,
            black_rating=black,
            platform=cast(Platform, platform),
            time_control_bucket=cast("TimeControlBucket | None", bucket),
            is_correspondence=is_correspondence_time_control(tc_str),
            user_color=cast("Literal['white', 'black']", user_color),
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


def _mover_elo(inputs: GameMaiaInputs, board: chess.Board) -> float | None:
    """The pinned Elo of the side to move on `board`, or None when its rating is unknown."""
    # board.turn, not ply parity: a custom-FEN game may start with Black to move.
    raw_rating = inputs.white_rating if board.turn == chess.WHITE else inputs.black_rating
    if raw_rating is None:
        return None
    return pinned_elo_for_mover(
        raw_rating=raw_rating,
        platform=inputs.platform,
        time_control_bucket=inputs.time_control_bucket,
        is_correspondence=inputs.is_correspondence,
    )


def _is_user_blunder(inputs: GameMaiaInputs, flaw: FlawMaiaInput) -> bool:
    """D-03: a blunder (severity 2) played by the game's user, never an opponent or a mistake."""
    if flaw.severity != _SEVERITY_INT["blunder"]:
        return False
    return mover_is_white_at_ply(flaw.ply) == (inputs.user_color == "white")


def _refutation_reason(post: chess.Board, refutation_uci: str | None) -> MaiaReason | None:
    """Why `refutation_uci` is unusable as a reply on the post-blunder board, else None."""
    if refutation_uci is None:
        return "refutation_missing"
    try:
        refutation = chess.Move.from_uci(refutation_uci)
    except ValueError:
        # Worker-supplied strings land in game_positions (T-248-01): a malformed one
        # must leave the pair NULL, not fail the whole game.
        return "refutation_not_legal"
    if refutation not in post.legal_moves:
        return "refutation_not_legal"
    return None


def _derive_post_blunder(
    pre_board: chess.Board,
    played_uci: str,
    elo: float,
    refutation_uci: str | None,
) -> tuple[MaiaRefutationStats, float | None, list[MaiaReason]]:
    """Maia's view of the position after the blunder: refutation pair plus reply spread.

    `pre_board` is the position before the blunder (blunderer to move) and `elo` the
    blunderer's pinned Elo, taken from THAT board's mover: the question is "would a player
    of your level find this reply", so the opponent's rating never enters (248 D-04).
    The post-blunder board is a copy with the played move pushed (248 D-05): the drain's own
    target boards are never mutated and castling / en-passant rights stay exact.

    ONE full_policy call serves both outputs (250 D-07: no extra inference): the reply
    spread is `reply_spread(probs)`, and the refutation pair is Maia's probability and rank
    for Stockfish's best reply. The spread does not need that reply, so a missing, malformed
    or illegal reply leaves only the pair NULL (reason `refutation_missing` /
    `refutation_not_legal`) while the spread is still returned. An illegal played move or a
    blunder that leaves the opponent no legal move spends no inference and returns the null
    pair, a None spread and the reason.
    """
    post = pre_board.copy(stack=False)
    played = chess.Move.from_uci(played_uci)
    if played not in post.legal_moves:
        return null_refutation_stats(), None, ["played_not_legal"]
    post.push(played)
    if not any(post.legal_moves):
        return null_refutation_stats(), None, ["no_legal_reply"]
    probs = full_policy(post.fen(), elo)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
    spread = reply_spread(probs) if probs else None
    reason = _refutation_reason(post, refutation_uci)
    if reason is not None:
        return null_refutation_stats(), spread, [reason]
    refutation, pair_reason = compute_refutation_stats(probs, refutation_uci)
    return refutation, spread, [] if pair_reason is None else [pair_reason]


def _facepalm_values(
    board: chess.Board,
    played_uci: str,
    refutation_pv: str | None,
    played_prob: float | None,
    spread: float | None,
) -> FacepalmStats:
    """The eight facepalm columns of one user blunder (250 D-05).

    Line facts come from the pre-blunder board and the stored line alone (no rating, no
    inference), so they are set whenever the line is usable. The score additionally needs
    the played probability and the spread and is None when either is missing, or when the
    line is too short to tell (the shipped model's own rule, `facepalm_score`).
    """
    facts = line_facts(board, played_uci, refutation_pv)
    columns = facts.as_columns()
    return FacepalmStats(
        maia_reply_spread=spread,
        line_loss_1=columns["line_loss_1"],
        line_loss_3=columns["line_loss_3"],
        line_loss_5=columns["line_loss_5"],
        line_loss_7=columns["line_loss_7"],
        line_loss_9=columns["line_loss_9"],
        line_mate_ply=columns["line_mate_ply"],
        facepalm_score=facepalm_score(
            played_prob=played_prob,
            reply_spread=spread,
            loss_3=facts.loss_at(LINE_DEPTH),
            mate_ply=facts.mate_ply,
        ),
    )


def _flaw_board(flaw: FlawMaiaInput, boards: BoardsByPly) -> tuple[chess.Board, str] | MaiaReason:
    """The (pre-push board, played UCI) of a flaw, else the reason it has none.

    The ply / fen guards, all run before any inference. They need no rating, so the line
    facts of a user blunder can be derived from this alone.
    """
    entry = boards.get(flaw.ply)
    if entry is None:
        return "ply_beyond_mainline"
    board, played_uci = entry
    if board.board_fen() != flaw.fen:
        return "fen_mismatch"
    return board, played_uci


def _flaw_context(
    inputs: GameMaiaInputs, flaw: FlawMaiaInput, boards: BoardsByPly
) -> tuple[chess.Board, str, float] | MaiaReason:
    """The (pre-push board, played UCI, mover Elo) of a scorable flaw, else the reason it is not.

    The board / fen / rating guards shared by both modes; all run before any inference.
    """
    entry = _flaw_board(flaw, boards)
    if isinstance(entry, str):
        return entry
    board, played_uci = entry
    elo = _mover_elo(inputs, board)
    if elo is None:
        return "no_rating"
    return board, played_uci, elo


def _scope_facepalm(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    board: chess.Board,
    played_uci: str,
    played_prob: float | None,
    spread: float | None,
) -> FacepalmStats:
    """D-06: facepalm values for a user-side blunder, all-None for every other flaw."""
    if not _is_user_blunder(inputs, flaw):
        return null_facepalm_stats()
    return _facepalm_values(board, played_uci, flaw.refutation_pv, played_prob, spread)


def _derive_flaw_values(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
) -> tuple[MaiaFlawStats | None, MaiaRefutationStats, FacepalmStats, list[MaiaReason]]:
    """Derive the eight base values plus, for a user-side blunder, the refutation pair and
    the eight facepalm values.

    Exactly one full_policy call per scorable flaw (D-04) plus one per scorable user-side
    blunder (the post-blunder position, even when its reply is unusable): the guards that
    make a flaw unscorable all run before any inference. The board / fen guards run once and
    feed every output. A user blunder with a board but no rating or no base stats still gets
    its line facts (they need neither); the spread and the score need the Maia pass.
    """
    no_refutation = null_refutation_stats()
    entry = _flaw_board(flaw, boards)
    if isinstance(entry, str):
        return None, no_refutation, null_facepalm_stats(), [entry]
    board, played_uci = entry
    elo = _mover_elo(inputs, board)
    if elo is None:
        facepalm = _scope_facepalm(inputs, flaw, board, played_uci, None, None)
        return None, no_refutation, facepalm, ["no_rating"]
    probs = full_policy(board.fen(), elo)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
    stats, reasons = compute_maia_flaw_stats(
        probs,
        played_uci=played_uci,
        best_uci=flaw.best_uci,
        second_uci=flaw.second_uci,
    )
    if stats is None or not _is_user_blunder(inputs, flaw):
        facepalm = _scope_facepalm(inputs, flaw, board, played_uci, None, None)
        return stats, no_refutation, facepalm, reasons
    refutation, spread, post_reasons = _derive_post_blunder(
        board, played_uci, elo, flaw.refutation_uci
    )
    facepalm = _facepalm_values(
        board, played_uci, flaw.refutation_pv, stats["maia_played_prob"], spread
    )
    return stats, refutation, facepalm, reasons + post_reasons


def _pk_row(inputs: GameMaiaInputs, flaw: FlawMaiaInput) -> dict[str, Any]:
    return {"user_id": inputs.user_id, "game_id": inputs.game_id, "ply": flaw.ply}


def _flaw_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One write row (PK plus all eighteen keys) for a flaw; counts its reasons.

    Out-of-scope and unscorable flaws carry a NULL refutation pair and NULL facepalm values,
    so a full re-score also clears stale values on a row since downgraded from blunder
    (D-08 precedent, 250 D-06).
    """
    stats: MaiaFlawStats | None = None
    refutation = null_refutation_stats()
    facepalm = null_facepalm_stats()
    if game_reason is not None:
        reasons[game_reason] += 1
    else:
        stats, refutation, facepalm, flaw_reasons = _derive_flaw_values(inputs, flaw, boards)
        reasons.update(flaw_reasons)
    row = _pk_row(inputs, flaw)
    row.update(stats if stats is not None else null_maia_stats())
    row.update(refutation)
    row.update(facepalm)
    return row


def _refutation_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One refutation-mode row for a user-side blunder: PK plus ONLY the two refutation keys.

    The eight base values and the facepalm values are deliberately absent so the write
    leaves them untouched (D-10); the spread the shared inference also yields is dropped.
    """
    refutation = null_refutation_stats()
    context: tuple[chess.Board, str, float] | MaiaReason
    context = game_reason if game_reason is not None else _flaw_context(inputs, flaw, boards)
    if isinstance(context, str):
        reasons[context] += 1
    else:
        board, played_uci, elo = context
        refutation, _spread, post_reasons = _derive_post_blunder(
            board, played_uci, elo, flaw.refutation_uci
        )
        reasons.update(post_reasons)
    row = _pk_row(inputs, flaw)
    row.update(refutation)
    return row


def _spread_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One spread-mode row for a user-side blunder: PK plus ONLY the eight facepalm keys (D-08).

    The same values the hook writes (`_facepalm_values`), but the base inference is not re-run:
    the played probability is the stored `maia_played_prob`. One post-blunder inference yields
    the spread (its refutation pair is discarded: the pair columns are not written). The line
    facts need no rating, so a missing rating keeps them and leaves the spread and score NULL,
    exactly as the hook does. The base values and the refutation pair are never touched.
    """
    values = null_facepalm_stats()
    entry: tuple[chess.Board, str] | MaiaReason
    entry = game_reason if game_reason is not None else _flaw_board(flaw, boards)
    if isinstance(entry, str):
        reasons[entry] += 1
    else:
        board, played_uci = entry
        spread: float | None = None
        elo = _mover_elo(inputs, board)
        if elo is None:
            reasons["no_rating"] += 1
        else:
            _pair, spread, post_reasons = _derive_post_blunder(
                board, played_uci, elo, flaw.refutation_uci
            )
            reasons.update(post_reasons)
        values = _facepalm_values(
            board, played_uci, flaw.refutation_pv, flaw.stored_played_prob, spread
        )
    row = _pk_row(inputs, flaw)
    row.update(values)
    return row


# The keys a line-mode row carries: the facepalm columns minus the reply spread, which line mode
# reads but never writes (the spread needs Maia).
LINE_ROW_COLUMNS: tuple[str, ...] = tuple(c for c in FACEPALM_COLUMNS if c != "maia_reply_spread")


def _line_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One line-mode row for a user-side blunder: PK plus the six line keys and facepalm_score (D-18).

    No Maia, no rating: the line facts come from the replayed board and the stored line, the
    score from the stored `maia_played_prob` and `maia_reply_spread` plus those facts. A flaw
    whose board cannot be rebuilt gets NULL line keys (the stored values would describe a
    different position). `maia_reply_spread`, the base values and the refutation pair are never
    written.
    """
    values = null_facepalm_stats()
    entry: tuple[chess.Board, str] | MaiaReason
    entry = game_reason if game_reason is not None else _flaw_board(flaw, boards)
    if isinstance(entry, str):
        reasons[entry] += 1
    else:
        board, played_uci = entry
        values = _facepalm_values(
            board,
            played_uci,
            flaw.refutation_pv,
            flaw.stored_played_prob,
            flaw.stored_reply_spread,
        )
    row = _pk_row(inputs, flaw)
    row.update({column: values[column] for column in LINE_ROW_COLUMNS})  # ty: ignore[invalid-key]
    return row


# Row builders of the user-blunder-only modes (full mode scores every flaw via `_flaw_row`).
_USER_BLUNDER_ROW_BUILDERS = {
    "refutation": _refutation_row,
    "spread": _spread_row,
    "line": _line_row,
}


def _score_rows(
    inputs: GameMaiaInputs,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    mode: ScoringMode,
    reasons: Counter[MaiaReason],
) -> tuple[list[FlawMaiaInput], list[dict[str, Any]]]:
    """(flaws in scope, one row per in-scope flaw): every flaw in full mode, user blunders only
    in the refutation, spread and line modes."""
    if mode == "full":
        flaws = list(inputs.flaws)
        return flaws, [_flaw_row(inputs, f, boards, game_reason, reasons) for f in flaws]
    build = _USER_BLUNDER_ROW_BUILDERS[mode]
    flaws = [f for f in inputs.flaws if _is_user_blunder(inputs, f)]
    return flaws, [build(inputs, f, boards, game_reason, reasons) for f in flaws]


def score_game(
    inputs: GameMaiaInputs, boards: BoardsByPly | None, mode: ScoringMode = "full"
) -> GameMaiaScore:
    """Score one game's flaws (sync, CPU, no I/O).

    boards None means "replay from the PGN" (callers without in-memory targets).

    Full mode: every flaw yields a row carrying all eighteen keys (None for an unscorable or
    out-of-scope value), so a re-score never leaves a stale value (D-08).
    Refutation mode (D-10): only user-side blunders yield a row, carrying just the two
    refutation keys; a game with none replays nothing and runs no inference (D-09), and the
    PGN replay covers only the blunder plies (D-05).
    Spread mode (250 D-08): user-side blunders only, rows carry the eight facepalm keys; one
    post-blunder inference each. Line mode (250 D-18): user-side blunders only, rows carry the
    six line keys plus facepalm_score; never calls Maia.
    """
    scope_plies = (
        {f.ply for f in inputs.flaws}
        if mode == "full"
        else {f.ply for f in inputs.flaws if _is_user_blunder(inputs, f)}
    )
    game_reason: MaiaReason | None = None
    if boards is None:
        if scope_plies:
            boards, game_reason = replay_flaw_boards(inputs.pgn, scope_plies)
        else:
            boards = {}
    reasons: Counter[MaiaReason] = Counter()
    scope_flaws, rows = _score_rows(inputs, boards, game_reason, mode, reasons)
    return GameMaiaScore(
        game_id=inputs.game_id,
        user_id=inputs.user_id,
        fingerprint=inputs.fingerprint(),
        rows=rows,
        reasons=reasons,
        user_blunders=sum(1 for f in scope_flaws if _is_user_blunder(inputs, f)),
        # Only full and refutation rows carry the refutation key.
        refutations_from_pv=sum(
            1
            for f, row in zip(scope_flaws, rows, strict=True)
            if f.refutation_from_pv and row.get("maia_refutation_prob") is not None
        )
        if mode in ("full", "refutation")
        else 0,
        spreads_scored=sum(1 for row in rows if row.get("maia_reply_spread") is not None),
        scores_set=sum(1 for row in rows if row.get("facepalm_score") is not None),
        mode=mode,
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


# The game stamp each mode checks (require_unstamped) and, in `_STAMPS_BY_MODE`, the stamps it sets.
_STAMP_COLUMN_BY_MODE: dict[ScoringMode, Any] = {
    "full": Game.maia_flaws_completed_at,
    "refutation": Game.maia_refutation_completed_at,
    "spread": Game.facepalm_spread_completed_at,
    "line": Game.facepalm_line_completed_at,
}


async def _mark_stamps(session: AsyncSession, mode: ScoringMode, game_ids: Sequence[int]) -> None:
    """Set the mode's stamps (see the per-mode table in `write_game_maia_scores`)."""
    if mode == "full":
        await mark_maia_flaws_completed(session, game_ids)
        await mark_facepalm_spread_completed(session, game_ids)
        await mark_facepalm_line_completed(session, game_ids)
    if mode in ("full", "refutation"):
        await mark_maia_refutation_completed(session, game_ids)
    if mode == "spread":
        # The spread pass writes the line facts and the score too, so it settles both stamps.
        await mark_facepalm_spread_completed(session, game_ids)
    if mode in ("spread", "line"):
        await mark_facepalm_line_completed(session, game_ids)


def _is_already_stamped(
    stamp: datetime | None, mode: ScoringMode, line_cutoff: datetime | None
) -> bool:
    """True when the mode's stamp says the game needs no write.

    Line mode (D-18) is re-runnable: the stamp counts only when it is at or after the cutoff, so
    a game last line-scored before the cutoff is written again.
    """
    if stamp is None:
        return False
    if mode == "line" and line_cutoff is not None:
        return stamp >= line_cutoff
    return True


async def write_game_maia_scores(
    session: AsyncSession,
    scores: Sequence[GameMaiaScore],
    *,
    require_unstamped: bool,
    line_cutoff: datetime | None = None,
) -> dict[int, GameOutcome]:
    """Write the scored columns plus the mode's stamps for every game whose inputs are unchanged.

    The caller commits. All games are advisory-locked (ascending order) before the
    fingerprint re-read, so the fingerprint cannot change between the check and the
    write.

    All scores of one call share a mode (ValueError otherwise: the modes carry different key
    sets, so one executemany cannot take two). Stamps checked and set per mode:

    - full: checks maia_flaws_completed_at; sets all four stamps (the two Maia stamps and, since
      Phase 250, the two facepalm stamps).
    - refutation: checks and sets only maia_refutation_completed_at; never touches the base
      columns, the facepalm columns or the other stamps (D-10).
    - spread (250 D-08): checks facepalm_spread_completed_at; sets it and
      facepalm_line_completed_at (the pass wrote the line facts too).
    - line (250 D-18): checks facepalm_line_completed_at against `line_cutoff` (a stamp at or
      after the cutoff means already stamped); sets only facepalm_line_completed_at.
    """
    if len(scores) > MAX_GAMES_PER_WRITE_TXN:
        raise ValueError("too many games for one write transaction")
    if not scores:
        return {}
    modes = {s.mode for s in scores}
    if len(modes) > 1:
        raise ValueError("cannot write a batch mixing scoring modes")
    mode = next(iter(modes))
    if mode == "line" and require_unstamped and line_cutoff is None:
        raise ValueError("line mode with require_unstamped needs a cutoff")
    ordered = sorted(scores, key=lambda s: s.game_id)
    game_ids = [s.game_id for s in ordered]
    await _lock_games_ascending(session, game_ids)

    current_flaws = await _read_flaw_inputs(session, game_ids)
    stamp_rows = (
        await session.execute(
            sa.select(Game.id, _STAMP_COLUMN_BY_MODE[mode]).where(Game.id.in_(game_ids))
        )
    ).all()
    stamp_by_game = {gid: stamp for gid, stamp in stamp_rows}

    outcomes: dict[int, GameOutcome] = {}
    rows_to_write: list[dict[str, Any]] = []
    for score in ordered:
        current = current_flaws.get(score.game_id)
        current_fp = fingerprint_of(current) if current is not None else None
        exists = score.game_id in stamp_by_game
        already = _is_already_stamped(stamp_by_game.get(score.game_id), mode, line_cutoff)
        outcome = _outcome_for(score, current_fp, (exists, already), require_unstamped)
        outcomes[score.game_id] = outcome
        if outcome == "stamped":
            rows_to_write.extend(score.rows)

    stamped_ids = [gid for gid, outcome in outcomes.items() if outcome == "stamped"]
    await bulk_update_flaw_maia_stats(session, rows_to_write)
    await _mark_stamps(session, mode, stamped_ids)
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
    "REFUTATION_PV_SEPARATOR",
    "ScoringMode",
    "ScoringSource",
    "boards_from_targets",
    "format_maia_backfill_reminder",
    "load_game_maia_inputs",
    "replay_flaw_boards",
    "score_game",
    "score_game_flaws_after_apply",
    "write_game_maia_scores",
]
