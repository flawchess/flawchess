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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

import chess

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
    side = facepalm_type_of(loss, 0.0 if missed is None else missed)
    type_line: TypeLine | None = None
    if side is not None and type_mate:
        type_line = _TYPE_LINE[(side, True)]
    elif side is not None and type_swing is not None and type_swing >= TYPE_LINE_MIN_SWING:
        type_line = _TYPE_LINE[(side, False)]
    return BlunderFeedbackData(
        score=score, type_line=type_line, hard_to_catch=score < HARD_TO_CATCH_SCORE_BELOW
    )
