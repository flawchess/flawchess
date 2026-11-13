"""facepalm_score.py - the facepalm score of a user blunder (Phase 250 D-01, D-04).

A logistic score in [0, 1] at the mover's level: 0 = basically no chance the player could
have seen the blunder, 1 = a very careless blunder the player should absolutely have
avoided. It is a RANKING fitted on the owner's labels, not a probability: the label sets are
mostly rule passers, so the values are not calibrated to all blunders and no copy may
present the score as a share of peers.

    z     = intercept + played_coef * ln(played_prob + PLAYED_PROB_OFFSET)
                      + spread_coef * reply_spread + loss_coef * loss_feature
    score = 1 / (1 + exp(-z))

Inputs, all stored on game_flaws (no engine at scoring time):
- ``played_prob``: Maia's probability for the played move (``maia_played_prob``);
- ``reply_spread``: effective number of opponent replies one ply later (``maia_reply_spread``);
- ``loss_feature``: net material down after LINE_DEPTH plies of the stored line, capped at
  LOSS_CAP, or MATE_LOSS when the blunderer is mated within LINE_DEPTH plies.

The formula exists twice: ``facepalm_score`` (Python) and ``facepalm_score_sql`` (SQLAlchemy
expression, so selection stays a plain SQL filter on game_flaws). If either side changes,
update the other; ``tests/services/test_facepalm_score.py`` pins them together. The default
model is ``FACEPALM_MODEL``, built from the fitted FACEPALM_* constants in
``blunder_check_rules``; tests and the fit script pass an explicit model. Pure, no I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import ColumnElement, Float, case, func, literal, null, type_coerce

from app.services.blunder_check_rules import (
    FACEPALM_INTERCEPT,
    FACEPALM_LOSS_COEF,
    FACEPALM_LOSS_FLOOR,
    FACEPALM_PLAYED_COEF,
    FACEPALM_SPREAD_COEF,
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    PLAYED_PROB_OFFSET,
)


@dataclass(frozen=True, slots=True)
class FacepalmModel:
    """Fitted logistic coefficients; `loss_floor` lower-clips the loss input when not None."""

    intercept: float
    played_coef: float
    spread_coef: float
    loss_coef: float
    loss_floor: int | None


# The shipped model, built from the fitted D-04 constants; the default of both score twins.
FACEPALM_MODEL: Final[FacepalmModel] = FacepalmModel(
    intercept=FACEPALM_INTERCEPT,
    played_coef=FACEPALM_PLAYED_COEF,
    spread_coef=FACEPALM_SPREAD_COEF,
    loss_coef=FACEPALM_LOSS_COEF,
    loss_floor=FACEPALM_LOSS_FLOOR,
)


def loss_feature(
    loss_3: int | None, mate_ply: int | None, *, loss_floor: int | None
) -> float | None:
    """The loss input of the score, or None when the line is too short to tell.

    A mate within LINE_DEPTH plies counts MATE_LOSS. Otherwise the depth-3 net loss capped at
    LOSS_CAP, raised to `loss_floor` when the model has one; None when `loss_3` is None.
    """
    if mate_ply is not None and mate_ply <= LINE_DEPTH:
        return float(MATE_LOSS)
    if loss_3 is None:
        return None
    capped = min(loss_3, LOSS_CAP)
    if loss_floor is not None:
        capped = max(capped, loss_floor)
    return float(capped)


def facepalm_score(
    *,
    played_prob: float | None,
    reply_spread: float | None,
    loss_3: int | None,
    mate_ply: int | None,
    model: FacepalmModel = FACEPALM_MODEL,
) -> float | None:
    """Facepalm score in (0, 1), or None when any input is missing.

    Python twin of `facepalm_score_sql`: if either side changes, update the other.
    """
    if played_prob is None or reply_spread is None:
        return None
    loss = loss_feature(loss_3, mate_ply, loss_floor=model.loss_floor)
    if loss is None:
        return None
    z = (
        model.intercept
        + model.played_coef * math.log(played_prob + PLAYED_PROB_OFFSET)
        + model.spread_coef * reply_spread
        + model.loss_coef * loss
    )
    return 1.0 / (1.0 + math.exp(-z))


def facepalm_score_sql(
    played_col: Any,
    spread_col: Any,
    loss3_col: Any,
    mate_col: Any,
    *,
    model: FacepalmModel = FACEPALM_MODEL,
) -> ColumnElement[float]:
    """SQL twin of `facepalm_score` as a SQLAlchemy expression (NULL when any input is missing).

    The loss feature is MATE_LOSS when `mate_col` <= LINE_DEPTH, NULL when `loss3_col` is NULL
    otherwise (PostgreSQL LEAST/GREATEST skip NULLs, so the explicit CASE branch is what keeps
    a short line unscored), else LEAST(loss3, LOSS_CAP), raised to the model's floor when it
    has one. A NULL played probability or spread propagates through LN and the arithmetic.

    Its Python twin is `facepalm_score`: if either side changes, update the other.
    """
    capped = func.least(loss3_col, LOSS_CAP)
    if model.loss_floor is not None:
        capped = func.greatest(capped, model.loss_floor)
    loss = case(
        (mate_col <= LINE_DEPTH, literal(float(MATE_LOSS))),
        (loss3_col.is_(None), null()),
        else_=capped,
    )
    z = (
        model.intercept
        + model.played_coef * func.ln(played_col + PLAYED_PROB_OFFSET)
        + model.spread_coef * spread_col
        + model.loss_coef * loss
    )
    # type_coerce only retypes the expression for the checker (PostgreSQL exp() is double precision).
    return type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))
