"""Type-line facts and the read-time feedback decision for the blunder-check drill (Phase 261).

Pure module, no I/O. The module has two halves sharing one vocabulary:

- `type_line_facts` runs at serve time (window composition) for the one blunder a window serves.
  It walks the stored engine lines with the Phase 259 functions only (`quiet_line_facts`,
  `quiet_best_line_facts`, `loss_by_depth`, `gain_by_depth`) and reads the swing at the deepest
  settled odd depth (D-08) on the facepalm-type side alone (seed "type line side", 257 D-02): the
  played line for an allowed loss, the best line for a missed win. The other side's swing or mate
  is never stored or used, and `window_case` is not read. A mate counts only when the stored line
  reaches it (D-09), and a best line that is only `best_move` and does not mate gives no missed
  swing (D-12), mirroring `missed = 0` for an unknown best line.
- `blunder_feedback` runs at read time on the stored snapshot. It applies the seed "type line
  floor" (`TYPE_LINE_MIN_SWING`, never applied to the stored `material_loss` / `material_missed`)
  and the D-06 "hard to catch" cut (`HARD_TO_CATCH_SCORE_BELOW`, tied to the score, never the arm).

Phase 264 shares both halves with the personalized puzzle reveal, which has no snapshot and
computes the line for its one row: `stored_type_line_facts` is the replay step for one blunder of
one PGN (blunder check's composer calls it per window), `type_line_of` the decision without a
facepalm score, and `stored_type_line` the two chained.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Final, Literal

import chess
import chess.pgn

from app.services.blunder_check_rules import (
    FACEPALM_LOSS_FLOOR,
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_FLOOR,
    FACEPALM_MISSED_MATE,
    HARD_TO_CATCH_SCORE_BELOW,
    TYPE_LINE_MIN_SWING,
)
from app.services.facepalm_material import MaterialSeries, gain_by_depth, loss_by_depth
from app.services.facepalm_score import FacepalmType, facepalm_type_of
from app.services.line_material import quiet_best_line_facts, quiet_line_facts

TypeLine = Literal["allowed_material", "allowed_mate", "missed_material", "missed_mate"]


# (facepalm type, is a mate) -> the type line the feedback shows.
_TYPE_LINE: Final[dict[tuple[FacepalmType, bool], TypeLine]] = {
    ("allowed_loss", False): "allowed_material",
    ("allowed_loss", True): "allowed_mate",
    ("missed_win", False): "missed_material",
    ("missed_win", True): "missed_mate",
}


@dataclass(frozen=True)
class TypeLineFacts:
    """The serve-time type-line facts of one blunder: the swing at the deepest settled depth
    (None = nothing settled) and whether the stored line reaches a mate on the type side."""

    swing: int | None
    mate: bool


@dataclass(frozen=True)
class BlunderFeedbackData:
    """What the solution feedback shows for one snapshotted blunder window."""

    score: float
    # 264 D-23: with the score, the solution line's "??" / "???" badge opens the facepalm
    # popover. From the snapshotted inputs, like the score; None only for an unknown loss,
    # which the snapshot's CHECK rules out whenever a score exists.
    facepalm_type: FacepalmType | None
    type_line: TypeLine | None
    hard_to_catch: bool


def _deepest_settled(series: MaterialSeries) -> int | None:
    """The last non-None element of a per-depth series (settledness is monotone in depth)."""
    settled = [value for value in series if value is not None]
    return round(settled[-1]) if settled else None


def type_line_facts(
    pre_board: chess.Board,
    played_uci: str,
    refutation_pv: str | None,
    best_line: str | None,
    facepalm_type: FacepalmType,
) -> TypeLineFacts:
    """Swing and mate on the facepalm-type side of one blunder (D-08, D-09, D-12).

    `pre_board` is the position before the blunder, `played_uci` the blunder, `refutation_pv` the
    stored line at ply + 1 and `best_line` the stored line at the flaw ply (else its `best_move`),
    the same inputs the write-time hook uses.
    """
    played = quiet_line_facts(pre_board, played_uci, refutation_pv)
    if facepalm_type == "allowed_loss":
        series = loss_by_depth(
            played.material_array(), played.mate_ply, loss_floor=FACEPALM_LOSS_FLOOR
        )
        return TypeLineFacts(swing=_deepest_settled(series), mate=played.mate_ply is not None)
    best = quiet_best_line_facts(pre_board, best_line)
    series = gain_by_depth(
        played.material_array(),
        best.material_array(),
        best.opponent_mate_ply,
        missed_floor=FACEPALM_MISSED_FLOOR,
        missed_cap=FACEPALM_MISSED_CAP,
        missed_mate=FACEPALM_MISSED_MATE,
    )
    return TypeLineFacts(swing=_deepest_settled(series), mate=best.opponent_mate_ply is not None)


def mainline(pgn: str) -> tuple[chess.Board, list[chess.Move]] | None:
    """Start board and mainline moves, None for an unparseable PGN."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            return None
        return game.board(), list(game.mainline_moves())
    except ValueError, IndexError, AttributeError, UnicodeDecodeError:
        return None


def board_before_ply(pgn: str, ply: int) -> tuple[chess.Board, chess.Move] | None:
    """The board before `ply` and the move played there; None for a bad PGN or a short mainline."""
    parsed = mainline(pgn)
    if parsed is None:
        return None
    board, moves = parsed
    if ply >= len(moves):
        return None
    for move in moves[:ply]:
        board.push(move)
    return board, moves[ply]


def stored_type_line_facts(
    pgn: str,
    blunder_ply: int,
    *,
    refutation_pv: str | None,
    best_line: str | None,
    facepalm_type: FacepalmType,
) -> TypeLineFacts:
    """Type-line facts of the blunder at `blunder_ply` of `pgn` from its stored lines.

    `refutation_pv` is `game_positions.pv` at ply + 1, `best_line` the pv at the flaw ply, else
    its best_move (the write-time hook's convention). No usable replay gives no facts. The one
    replay step of both surfaces: blunder check at serve time, the puzzle reveal at read time.
    """
    replay = board_before_ply(pgn, blunder_ply)
    if replay is None:
        return TypeLineFacts(None, False)
    board, played = replay
    return type_line_facts(board, played.uci(), refutation_pv, best_line, facepalm_type)


def _type_line_for(
    side: FacepalmType | None, type_swing: int | None, type_mate: bool | None
) -> TypeLine | None:
    """A mate beats material (D-09), material needs TYPE_LINE_MIN_SWING, anything less: None."""
    if side is None:
        return None
    if type_mate:
        return _TYPE_LINE[(side, True)]
    if type_swing is not None and type_swing >= TYPE_LINE_MIN_SWING:
        return _TYPE_LINE[(side, False)]
    return None


def type_line_of(
    *,
    loss: float | None,
    missed: float | None,
    type_swing: int | None,
    type_mate: bool | None,
) -> TypeLine | None:
    """The type line of a blunder from its material inputs and type-line facts (Phase 264 D-01).

    Needs no facepalm score: an unscored row with a known `loss` still gets its line. The side
    follows the facepalm type of the inputs (257 D-02); an unknown loss has no side and no line.
    """
    side = facepalm_type_of(loss, 0.0 if missed is None else missed)
    return _type_line_for(side, type_swing, type_mate)


def stored_type_line(
    pgn: str,
    blunder_ply: int,
    *,
    loss: float | None,
    missed: float | None,
    refutation_pv: str | None,
    best_line: str | None,
) -> TypeLine | None:
    """The type line of one stored blunder, replayed now (the puzzle reveal, Phase 264 D-01).

    The same two steps blunder check splits over serve time (`stored_type_line_facts`, stored on
    the window) and read time (`type_line_of`), so both surfaces give the same line for the same
    blunder.
    """
    side = facepalm_type_of(loss, 0.0 if missed is None else missed)
    if side is None:
        return None
    facts = stored_type_line_facts(
        pgn, blunder_ply, refutation_pv=refutation_pv, best_line=best_line, facepalm_type=side
    )
    return _type_line_for(side, facts.swing, facts.mate)


def blunder_feedback(
    *,
    score: float | None,
    loss: float | None,
    missed: float | None,
    type_swing: int | None,
    type_mate: bool | None,
) -> BlunderFeedbackData | None:
    """The read-time feedback of a window snapshot; None for a window without one (D-04).

    The type line follows the facepalm type of the snapshotted inputs (257 D-02): a mate beats
    material (D-09), material needs a swing of at least TYPE_LINE_MIN_SWING, anything less gives
    no line. "Hard to catch" is a snapshotted score below HARD_TO_CATCH_SCORE_BELOW (D-06).
    """
    if score is None:
        return None
    type_line = type_line_of(loss=loss, missed=missed, type_swing=type_swing, type_mate=type_mate)
    return BlunderFeedbackData(
        score=score,
        # A NULL missed reads as 0.0, as in the type's Python twin `facepalm_type`.
        facepalm_type=facepalm_type_of(loss, 0.0 if missed is None else missed),
        type_line=type_line,
        hard_to_catch=score < HARD_TO_CATCH_SCORE_BELOW,
    )
