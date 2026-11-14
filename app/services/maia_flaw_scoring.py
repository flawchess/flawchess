"""maia_flaw_scoring.py — shared post-commit Maia scorer for game_flaws rows (Phase 247, D-13).

Every lane that writes ``game_flaws`` (local drain, atomic remote submit, tier-4 blob
submit, backfill script) calls into this one module AFTER its own write transaction has
committed, so the ~1 s of CPU per game never runs inside an eval write transaction.

Pipeline for one game, with no AsyncSession open during inference:

1. ``load_game_maia_inputs``: short read session (game rating metadata plus every flaw's
   fen, severity, the stored line ``game_positions.pv`` at ply + 1 and, from a second join at the
   flaw ply, the best line ``game_positions.pv`` and ``game_positions.best_move``).
2. ``score_game`` (sync, CPU, run in ``asyncio.to_thread``): one ``full_policy`` call per
   scorable flaw (the base value ``maia_played_prob``, via ``compute_maia_flaw_stats``) plus one
   per scorable user-side blunder (the post-blunder position at the blunderer's Elo, which
   yields the Phase 250 reply spread). The line facts (``line_facts`` on the stored line at ply + 1,
   ``best_line_facts`` on the best line at the flaw ply, Phase 254 D-09) and the facepalm score are
   derived from those plus the base value. The same flaw-position policy also yields the two
   pre-blunder inputs (Phase 254 D-08): ``maia_best_prob`` (the probability of the best move) and
   ``maia_pre_spread`` (the effective number of moves there), so the inference count per game is
   unchanged.
3. ``write_game_maia_scores``: short write session that takes
   ``pg_advisory_xact_lock`` per game (ascending key order), re-reads the inputs
   fingerprint and writes the scored columns plus the four stamps only when the
   fingerprint is unchanged. A mismatch means a concurrent apply reshaped the flaws (or
   changed a severity, the stored ply+1 line, the best line or the stored best move); the game is
   left unstamped for the next pass (254 T-254-05).

The stamps ``games.maia_flaws_completed_at``, ``games.facepalm_spread_completed_at``,
``games.facepalm_line_completed_at`` and ``games.facepalm_pre_completed_at`` are only ever set
together in full mode, when a Maia
session was loaded AND the pass completed without an exception (D-05 / D-09 guardrail, decided
from ``is_maia_available()``, never from row counts). Games with zero user-side blunders are
stamped too.

Phase 250 adds two backfill-only modes (D-08, D-18) that touch user-side blunders only: spread
mode (one post-blunder inference per blunder; writes the facepalm keys from the STORED
``maia_played_prob``) and line mode (no Maia at all; recomputes the line keys and the score
from the stored lines, ``maia_played_prob`` and ``maia_reply_spread``). The facepalm keys are the
Phase 250 eight plus the Phase 254 material arrays and best-line mate ply (``FACEPALM_COLUMNS``).

Phase 254 adds a third backfill-only mode, pre (D-08): one inference at the PRE-blunder position per
user-side blunder fills the two pre-blunder keys (``FACEPALM_PRE_COLUMNS``) on rows the hook wrote
before R1, and stamps only ``facepalm_pre_completed_at``. It never touches the played probability,
the reply spread, the line facts or the stored score.
"""

from __future__ import annotations

import asyncio
import io
import logging
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, NamedTuple, cast

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
    mark_facepalm_pre_completed,
    mark_facepalm_spread_completed,
    mark_maia_flaws_completed,
)
from app.repositories.query_utils import mover_is_white_at_ply
from app.schemas.normalization import Platform, TimeControlBucket
from app.services import maia_engine
from app.services.best_move_candidates import pinned_elo_for_mover
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA, LINE_DEPTH
from app.services.eval_apply import _FullPlyEvalTarget, _game_write_lock_key
from app.services.facepalm_score import FacepalmFacts, facepalm_score
from app.services.line_material import LineFacts, best_line_facts, line_facts
from app.services.maia_engine import full_policy
from app.services.maia_flaw_stats import (
    FacepalmStats,
    MaiaFlawStats,
    MaiaPreStats,
    MaiaReason,
    compute_maia_flaw_stats,
    null_facepalm_stats,
    null_maia_pre_stats,
    null_maia_stats,
    pre_blunder_spread,
    reply_spread,
)
from app.services.normalization import is_correspondence_time_control

logger = logging.getLogger(__name__)

# Separator of the stored line game_positions.pv (space-joined UCI).
_PV_SEPARATOR: str = " "

ScoringSource = Literal["full_eval_drain", "remote_eval_worker", "flaw_blob_submit", "backfill"]
GameOutcome = Literal["stamped", "fingerprint_changed", "already_stamped", "game_missing"]
# "full": the base value, the facepalm keys and the two pre-blunder keys per flaw, plus the four
# stamps. "spread" (Phase 250 D-08): the facepalm keys of user-side blunders from one post-blunder
# inference each, reading the stored maia_played_prob; stamps the spread and line stamps.
# "line" (Phase 250 D-18): the line keys plus facepalm_score of user-side blunders from the
# stored lines, played prob and spread; no Maia, stamps only the line stamp (cutoff-aware).
# "pre" (Phase 254 D-08): the two pre-blunder Maia keys of user-side blunders from one inference at
# the pre-blunder position; stamps only the pre stamp. Neither spread nor line writes the pre keys.
ScoringMode = Literal["full", "spread", "line", "pre"]

# (ply, game_flaws.fen, game_flaws.severity, the stored line game_positions.pv at ply + 1, the best
# line game_positions.pv at ply, game_positions.best_move at ply).
# The lines and the best move are part of the fingerprint because a Phase 252 repair can rewrite
# them, and the line facts and the facepalm score are derived from them (250 D-07, 254 T-254-05):
# stale line facts must never be written over a repaired line.
FlawFingerprint = tuple[int, str, int, str | None, str | None, str | None]

# ply -> (pre-push board, played UCI)
BoardsByPly = Mapping[int, tuple[chess.Board, str]]

# One write transaction holds one advisory lock per game; cap it so a batch caller can
# never exhaust the lock table.
MAX_GAMES_PER_WRITE_TXN: int = 50


class MaiaInferenceUnavailableError(RuntimeError):
    """full_policy returned None although a Maia session was reported available."""


@dataclass(frozen=True, slots=True)
class FlawMaiaInput:
    ply: int
    fen: str
    severity: int
    # The stored line game_positions.pv at ply + 1 (space-separated UCI starting with the
    # opponent's reply), None when absent. Input of the Phase 250 line facts.
    refutation_pv: str | None
    # The best line game_positions.pv at the flaw ply (the best move first, then its line) and
    # game_positions.best_move at the same ply (254 D-09, Pitfall 7). Inputs of the best-line
    # facts and the best-move probability; part of the fingerprint.
    best_pv: str | None
    best_move: str | None
    # The already stored game_flaws.maia_played_prob / maia_reply_spread. Inputs of the spread
    # and line modes (which must not re-run the base inference), required so a new construction
    # site cannot forget them. Deliberately NOT part of the fingerprint: they are derived values,
    # deterministic from the fingerprinted inputs, and including them would make every hook write
    # look like a concurrent reshape.
    stored_played_prob: float | None
    stored_reply_spread: float | None
    # The already stored game_flaws.maia_best_prob / maia_pre_spread (254 D-08): the pre-blunder
    # inputs of the dual-written stored score in spread and line modes. Not fingerprinted, same
    # reason as the two above.
    stored_best_prob: float | None
    stored_pre_spread: float | None


def fingerprint_of(flaws: Sequence[FlawMaiaInput]) -> frozenset[FlawFingerprint]:
    return frozenset(
        (f.ply, f.fen, f.severity, f.refutation_pv, f.best_pv, f.best_move) for f in flaws
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
    # Rows that carry a reply spread / a facepalm score (spread, line and full modes).
    spreads_scored: int = 0
    scores_set: int = 0
    # Rows that carry a pre-blunder spread (254 D-08; full and pre modes).
    pre_scored: int = 0
    # Decides which keys `rows` carry and which stamps the write sets.
    mode: ScoringMode = "full"


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def _flaw_fingerprint_select(game_ids: Sequence[int]) -> sa.Select[Any]:
    """One flaw SELECT shared by the load and the in-lock re-read (same columns, so the
    fingerprints are comparable).

    The stored line sits at ply + 1 (game_positions.pv of the position AFTER the flaw move); the
    best line and the best move sit at the flaw ply itself (the decision position).
    """
    gp_next = aliased(GamePosition)
    gp_flaw = aliased(GamePosition)
    return (
        sa.select(
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.fen,
            GameFlaw.severity,
            gp_next.pv,
            gp_flaw.pv,
            gp_flaw.best_move,
            GameFlaw.maia_played_prob,
            GameFlaw.maia_reply_spread,
            GameFlaw.maia_best_prob,
            GameFlaw.maia_pre_spread,
        )
        .select_from(GameFlaw)
        .outerjoin(
            gp_next,
            sa.and_(
                gp_next.game_id == GameFlaw.game_id,
                gp_next.user_id == GameFlaw.user_id,
                gp_next.ply == GameFlaw.ply + 1,
            ),
        )
        .outerjoin(
            gp_flaw,
            sa.and_(
                gp_flaw.game_id == GameFlaw.game_id,
                gp_flaw.user_id == GameFlaw.user_id,
                gp_flaw.ply == GameFlaw.ply,
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
        next_pv,
        best_pv,
        best_move,
        stored_played_prob,
        stored_reply_spread,
        stored_best_prob,
        stored_pre_spread,
    ) in result.all():
        by_game.setdefault(game_id, []).append(
            FlawMaiaInput(
                ply=ply,
                fen=fen,
                severity=severity,
                refutation_pv=next_pv,
                best_pv=best_pv,
                best_move=best_move,
                stored_played_prob=stored_played_prob,
                stored_reply_spread=stored_reply_spread,
                stored_best_prob=stored_best_prob,
                stored_pre_spread=stored_pre_spread,
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


def _derive_reply_spread(
    pre_board: chess.Board, played_uci: str, elo: float
) -> tuple[float | None, list[MaiaReason]]:
    """Maia's reply spread in the position after the blunder (one inference).

    `pre_board` is the position before the blunder (blunderer to move) and `elo` the
    blunderer's pinned Elo, taken from THAT board's mover: the question is "would a player
    of your level find a reply", so the opponent's rating never enters (248 D-04).
    The post-blunder board is a copy with the played move pushed (248 D-05): the drain's own
    target boards are never mutated and castling / en-passant rights stay exact.

    An illegal played move or a blunder that leaves the opponent no legal move spends no
    inference and returns a None spread plus the reason.
    """
    post = pre_board.copy(stack=False)
    played = chess.Move.from_uci(played_uci)
    if played not in post.legal_moves:
        return None, ["played_not_legal"]
    post.push(played)
    if not any(post.legal_moves):
        return None, ["no_legal_reply"]
    probs = full_policy(post.fen(), elo)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
    return (reply_spread(probs) if probs else None), []


def best_move_uci(best_pv: str | None, best_move: str | None) -> str | None:
    """The best move (UCI) at a flaw ply: the first token of the best pv, else best_move, else None.

    The pv wins so the best-move probability and the best-line facts describe the same move:
    `pv@ply` and `best_move` disagree on a few rows until the Phase 252 repair settles them
    (254 Pitfall 7).
    """
    if best_pv:
        return best_pv.split(_PV_SEPARATOR)[0]
    return best_move or None


def _material_or_none(facts: LineFacts) -> list[int | None] | None:
    """The signed 9-slot material array of a line, None when every slot is unsettled."""
    material = facts.material_array()
    return None if all(slot is None for slot in material) else material


def _facepalm_values(
    board: chess.Board,
    played_uci: str,
    flaw: FlawMaiaInput,
    played_prob: float | None,
    spread: float | None,
    pre: MaiaPreStats,
) -> FacepalmStats:
    """The facepalm columns of one user blunder (250 D-05, 254 D-09).

    Line facts come from the pre-blunder board and the stored lines alone (no rating, no
    inference), so they are set whenever a line is usable: the played line (`line_facts` on the
    stored line at ply + 1) and the best line (`best_line_facts` on the pv at the flaw ply, else
    the stored best move alone). The legacy `line_loss_*` columns are dual-written until the drop.
    The score additionally needs the played probability and the spread and is None when either is
    missing, or when the line is too short to tell (the shipped model's own rule,
    `facepalm_score`). `pre` carries the pre-blunder Maia inputs of the score (the model terms that
    read them are off until the refit).
    """
    facts = line_facts(board, played_uci, flaw.refutation_pv)
    best = best_line_facts(board, flaw.best_pv or flaw.best_move)
    columns = facts.as_columns()
    return FacepalmStats(
        maia_reply_spread=spread,
        line_loss_1=columns["line_loss_1"],
        line_loss_3=columns["line_loss_3"],
        line_loss_5=columns["line_loss_5"],
        line_loss_7=columns["line_loss_7"],
        line_loss_9=columns["line_loss_9"],
        line_mate_ply=columns["line_mate_ply"],
        # The stored column feeds the drill, so it is scored with the drill's lambda. The unused
        # model terms are off, so the score is the Phase 250 score (D-12).
        facepalm_score=facepalm_score(
            FacepalmFacts(
                played_prob=played_prob,
                reply_spread=spread,
                played_3=facts.material_at(LINE_DEPTH),
                mate_ply=facts.mate_ply,
                best_3=best.material_at(LINE_DEPTH),
                best_mate_ply=best.opponent_mate_ply,
                best_prob=pre["maia_best_prob"],
                pre_spread=pre["maia_pre_spread"],
            ),
            lam=FACEPALM_DRILL_LAMBDA,
        ),
        played_line_material=_material_or_none(facts),
        best_line_material=_material_or_none(best),
        best_line_mate_ply=best.opponent_mate_ply,
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


def _scope_facepalm(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    board: chess.Board,
    played_uci: str,
    played_prob: float | None,
    spread: float | None,
) -> FacepalmStats:
    """D-06: facepalm values for a user-side blunder, all-None for every other flaw.

    Used where the Maia pass produced nothing (no rating, no base stats), so the pre-blunder
    inputs are NULL as well.
    """
    if not _is_user_blunder(inputs, flaw):
        return null_facepalm_stats()
    return _facepalm_values(board, played_uci, flaw, played_prob, spread, null_maia_pre_stats())


class _FlawValues(NamedTuple):
    """Everything one flaw contributes to a full-mode row, plus the reasons it counts."""

    stats: MaiaFlawStats | None
    facepalm: FacepalmStats
    pre: MaiaPreStats
    reasons: list[MaiaReason]


def _pre_inputs(
    flaw: FlawMaiaInput, probs: Mapping[str, float]
) -> tuple[MaiaPreStats, list[MaiaReason]]:
    """The two pre-blunder inputs from the policy already computed at the flaw position (D-08).

    No inference: `probs` is the full policy that yields maia_played_prob. The best move is the
    first token of the best pv, else the stored best_move (Pitfall 7); one that is unknown or not
    in the policy leaves the best-move probability NULL and counts best_move_missing, while the
    pre-blunder spread is still stored.
    """
    best_uci = best_move_uci(flaw.best_pv, flaw.best_move)
    best_prob = float(probs[best_uci]) if best_uci is not None and best_uci in probs else None
    pre = MaiaPreStats(maia_best_prob=best_prob, maia_pre_spread=pre_blunder_spread(probs))
    return pre, ([] if best_prob is not None else ["best_move_missing"])


def _stored_pre(flaw: FlawMaiaInput) -> MaiaPreStats:
    """The stored pre-blunder inputs of a flaw (spread and line modes read, never write, them)."""
    return MaiaPreStats(
        maia_best_prob=flaw.stored_best_prob, maia_pre_spread=flaw.stored_pre_spread
    )


def _derive_flaw_values(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
) -> _FlawValues:
    """Derive the base value plus, for a user-side blunder, the facepalm and pre-blunder values.

    Exactly one full_policy call per scorable flaw (D-04) plus one per scorable user-side
    blunder (the post-blunder position): the guards that make a flaw unscorable all run
    before any inference. The board / fen guards run once and feed every output. The pre-blunder
    Maia inputs (254 D-08) come from the policy of the first call, so they cost no inference. A
    user blunder with a board but no rating or no base stats still gets its line facts (they need
    neither); the spread, the pre inputs and the score need the Maia pass.
    """
    entry = _flaw_board(flaw, boards)
    if isinstance(entry, str):
        return _FlawValues(None, null_facepalm_stats(), null_maia_pre_stats(), [entry])
    board, played_uci = entry
    elo = _mover_elo(inputs, board)
    if elo is None:
        facepalm = _scope_facepalm(inputs, flaw, board, played_uci, None, None)
        return _FlawValues(None, facepalm, null_maia_pre_stats(), ["no_rating"])
    probs = full_policy(board.fen(), elo)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
    stats, reasons = compute_maia_flaw_stats(probs, played_uci=played_uci)
    if stats is None or not _is_user_blunder(inputs, flaw):
        facepalm = _scope_facepalm(inputs, flaw, board, played_uci, None, None)
        return _FlawValues(stats, facepalm, null_maia_pre_stats(), reasons)
    spread, post_reasons = _derive_reply_spread(board, played_uci, elo)
    pre, pre_reasons = _pre_inputs(flaw, probs)
    facepalm = _facepalm_values(board, played_uci, flaw, stats["maia_played_prob"], spread, pre)
    return _FlawValues(stats, facepalm, pre, reasons + post_reasons + pre_reasons)


def _pk_row(inputs: GameMaiaInputs, flaw: FlawMaiaInput) -> dict[str, Any]:
    return {"user_id": inputs.user_id, "game_id": inputs.game_id, "ply": flaw.ply}


def _flaw_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One write row (PK plus the base value, the facepalm keys and the pre keys) for a flaw; counts
    its reasons.

    Out-of-scope and unscorable flaws carry NULL facepalm and pre values, so a full re-score also
    clears stale values on a row since downgraded from blunder (D-08 precedent, 250 D-06).
    """
    values = _FlawValues(None, null_facepalm_stats(), null_maia_pre_stats(), [])
    if game_reason is not None:
        reasons[game_reason] += 1
    else:
        values = _derive_flaw_values(inputs, flaw, boards)
        reasons.update(values.reasons)
    row = _pk_row(inputs, flaw)
    row.update(values.stats if values.stats is not None else null_maia_stats())
    row.update(values.facepalm)
    row.update(values.pre)
    return row


def _spread_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One spread-mode row for a user-side blunder: PK plus ONLY the facepalm keys (D-08).

    The same values the hook writes (`_facepalm_values`), but the base inference is not re-run:
    the played probability is the stored `maia_played_prob`. One post-blunder inference yields
    the spread. The line facts need no rating, so a missing rating keeps them and leaves the
    spread and score NULL, exactly as the hook does. The base value is never touched.
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
            spread, post_reasons = _derive_reply_spread(board, played_uci, elo)
            reasons.update(post_reasons)
        values = _facepalm_values(
            board, played_uci, flaw, flaw.stored_played_prob, spread, _stored_pre(flaw)
        )
    row = _pk_row(inputs, flaw)
    row.update(values)
    return row


def _pre_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One pre-mode row for a user-side blunder: PK plus ONLY the two pre-blunder keys (254 D-08).

    One inference at the pre-blunder board at the mover's pinned Elo, the same policy the hook
    reads `maia_played_prob` from, so the two values are exactly the hook's (`_pre_inputs`). The
    same guards run first (board / fen, rating, played move in the policy) and an unscorable
    blunder gets NULL pre keys with the reason counted. The played probability, the reply spread,
    the line facts and the stored score are never written (the row has no such key).
    """
    values = null_maia_pre_stats()
    entry: tuple[chess.Board, str] | MaiaReason
    entry = game_reason if game_reason is not None else _flaw_board(flaw, boards)
    if isinstance(entry, str):
        reasons[entry] += 1
    else:
        values, new_reasons = _pre_values(inputs, flaw, *entry)
        reasons.update(new_reasons)
    row = _pk_row(inputs, flaw)
    row.update(values)
    return row


def _pre_values(
    inputs: GameMaiaInputs, flaw: FlawMaiaInput, board: chess.Board, played_uci: str
) -> tuple[MaiaPreStats, list[MaiaReason]]:
    """The pre-blunder inputs of one blunder on a rebuilt board, plus the reasons to count."""
    elo = _mover_elo(inputs, board)
    if elo is None:
        return null_maia_pre_stats(), ["no_rating"]
    probs = full_policy(board.fen(), elo)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
    # The hook writes the pre inputs only when the played move is in the policy; keep that rule.
    stats, reasons = compute_maia_flaw_stats(probs, played_uci=played_uci)
    if stats is None:
        return null_maia_pre_stats(), reasons
    return _pre_inputs(flaw, probs)


# The keys a line-mode row carries: the facepalm columns minus the reply spread, which line mode
# reads but never writes (the spread needs Maia). They include the 254 material arrays and the
# best line's mate ply, recomputed from the stored lines.
LINE_ROW_COLUMNS: tuple[str, ...] = tuple(c for c in FACEPALM_COLUMNS if c != "maia_reply_spread")


def _line_row(
    inputs: GameMaiaInputs,
    flaw: FlawMaiaInput,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    reasons: Counter[MaiaReason],
) -> dict[str, Any]:
    """One line-mode row for a user-side blunder: PK plus the line keys and facepalm_score (D-18).

    No Maia, no rating: the line facts come from the replayed board and the stored line, the
    score from the stored `maia_played_prob` and `maia_reply_spread` plus those facts. A flaw
    whose board cannot be rebuilt gets NULL line keys (the stored values would describe a
    different position). `maia_reply_spread` and the base value are never written.
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
            flaw,
            flaw.stored_played_prob,
            flaw.stored_reply_spread,
            _stored_pre(flaw),
        )
    row = _pk_row(inputs, flaw)
    row.update({column: values[column] for column in LINE_ROW_COLUMNS})  # ty: ignore[invalid-key]
    return row


# Row builders of the user-blunder-only modes (full mode scores every flaw via `_flaw_row`).
_USER_BLUNDER_ROW_BUILDERS = {
    "spread": _spread_row,
    "line": _line_row,
    "pre": _pre_row,
}


def _score_rows(
    inputs: GameMaiaInputs,
    boards: BoardsByPly,
    game_reason: MaiaReason | None,
    mode: ScoringMode,
    reasons: Counter[MaiaReason],
) -> tuple[list[FlawMaiaInput], list[dict[str, Any]]]:
    """(flaws in scope, one row per in-scope flaw): every flaw in full mode, user blunders only
    in the spread and line modes."""
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

    Full mode: every flaw yields a row carrying every key (the base value, the facepalm keys and
    the two pre keys; None for an unscorable or out-of-scope value), so a re-score never leaves
    a stale value (D-08).
    Spread mode (250 D-08): user-side blunders only, rows carry the facepalm keys; one
    post-blunder inference each (a game with none replays nothing and runs no inference, and
    the PGN replay covers only the blunder plies). Line mode (250 D-18): user-side blunders
    only, rows carry the line keys plus facepalm_score; never calls Maia. Pre mode (254 D-08):
    user-side blunders only, rows carry the two pre-blunder keys; one pre-blunder inference each.
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
        spreads_scored=sum(1 for row in rows if row.get("maia_reply_spread") is not None),
        scores_set=sum(1 for row in rows if row.get("facepalm_score") is not None),
        pre_scored=sum(1 for row in rows if row.get("maia_pre_spread") is not None),
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
    "spread": Game.facepalm_spread_completed_at,
    "line": Game.facepalm_line_completed_at,
    "pre": Game.facepalm_pre_completed_at,
}


async def _mark_stamps(session: AsyncSession, mode: ScoringMode, game_ids: Sequence[int]) -> None:
    """Set the mode's stamps (see the per-mode table in `write_game_maia_scores`)."""
    if mode == "full":
        await mark_maia_flaws_completed(session, game_ids)
        await mark_facepalm_spread_completed(session, game_ids)
        await mark_facepalm_line_completed(session, game_ids)
        await mark_facepalm_pre_completed(session, game_ids)
    if mode == "spread":
        # The spread pass writes the line facts and the score too, so it settles both stamps.
        await mark_facepalm_spread_completed(session, game_ids)
    if mode in ("spread", "line"):
        await mark_facepalm_line_completed(session, game_ids)
    if mode == "pre":
        # The pre pass writes only the two pre-blunder inputs, so it settles only its own stamp.
        await mark_facepalm_pre_completed(session, game_ids)


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

    - full: checks maia_flaws_completed_at; sets all four stamps (the Maia stamp, the spread and
      line stamps and the 254 pre stamp).
    - spread (250 D-08): checks facepalm_spread_completed_at; sets it and
      facepalm_line_completed_at (the pass wrote the line facts too).
    - line (250 D-18): checks facepalm_line_completed_at against `line_cutoff` (a stamp at or
      after the cutoff means already stamped); sets only facepalm_line_completed_at.
    - pre (254 D-08): checks facepalm_pre_completed_at; sets only it (the pass wrote only the two
      pre-blunder keys).
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
    "ScoringMode",
    "ScoringSource",
    "best_move_uci",
    "boards_from_targets",
    "format_maia_backfill_reminder",
    "load_game_maia_inputs",
    "replay_flaw_boards",
    "score_game",
    "score_game_flaws_after_apply",
    "write_game_maia_scores",
]
