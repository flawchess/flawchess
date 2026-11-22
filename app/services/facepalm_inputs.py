"""facepalm_inputs.py - the one write-time function for the stored facepalm material inputs.

Phase 259 D-02 to D-05: the two stored numbers, ``loss`` and ``missed``, are the decaying mean over
the odd depths of the quiet-point material walk (``quiet_line_facts`` / ``quiet_best_line_facts``),
computed by ``material_loss`` / ``material_missed``. The write-time hook, the line
pass, the features pull and the review all call ``facepalm_material_inputs``, so the rule exists
once. No I/O.
"""

from __future__ import annotations

from typing import NamedTuple

import chess

from app.services.blunder_check_rules import (
    FACEPALM_LOSS_FLOOR,
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_FLOOR,
    FACEPALM_MISSED_MATE,
)
from app.services.facepalm_score import material_loss, material_missed
from app.services.line_material import LineFacts, quiet_best_line_facts, quiet_line_facts

# 259 D-03: the stored inputs are always the decaying mean over the odd depths, never chosen by a fit.


class MaterialInputs(NamedTuple):
    """The stored pair. `loss` is None when the line is too short to tell, and then `missed` is
    None too (256 D-03); a known loss with an unknown best line gives `missed` 0.0 (254 D-18)."""

    loss: float | None
    missed: float | None


def material_inputs_from_facts(played: LineFacts, best: LineFacts) -> MaterialInputs:
    """The stored pair from already-computed line facts (either rule's facts work)."""
    loss = material_loss(
        played.material_array(),
        played.mate_ply,
        loss_floor=FACEPALM_LOSS_FLOOR,
    )
    if loss is None:
        return MaterialInputs(loss=None, missed=None)
    missed = material_missed(
        played.material_array(),
        best.material_array(),
        best.opponent_mate_ply,
        missed_floor=FACEPALM_MISSED_FLOOR,
        missed_cap=FACEPALM_MISSED_CAP,
        missed_mate=FACEPALM_MISSED_MATE,
    )
    return MaterialInputs(loss=loss, missed=missed)


def facepalm_material_inputs(
    pre_board: chess.Board,
    played_uci: str,
    refutation_pv: str | None,
    best_pv: str | None,
) -> MaterialInputs:
    """The single writer function for the stored `loss` and `missed` (259 D-02 to D-04).

    `pre_board` is the position before the blunder, `refutation_pv` the stored line at ply + 1 and
    `best_pv` the stored line at the flaw ply (callers pass `best_pv or best_move`, the
    `quiet_best_line_facts` convention). `pre_board` is never mutated.
    """
    return material_inputs_from_facts(
        quiet_line_facts(pre_board, played_uci, refutation_pv),
        quiet_best_line_facts(pre_board, best_pv),
    )
