"""facepalm_score.py - the facepalm score of a user blunder (Phase 250 D-01, D-04; Phase 254).

A logistic score in [0, 1] at the mover's level: 0 = basically no chance the player could
have seen the blunder, 1 = a very careless blunder the player should absolutely have
avoided. It is a RANKING fitted on the owner's labels, not a probability: the label sets are
mostly rule passers, so the values are not calibrated to all blunders and no copy may
present the score as a share of peers.

    z     = intercept + played_coef * ln(played_prob + PLAYED_PROB_OFFSET)
                      + spread term + material term + optional terms
    score = 1 / (1 + exp(-z))

Inputs, all stored on game_flaws (no engine at scoring time):
- ``played_prob``: Maia's probability for the played move (``maia_played_prob``);
- ``reply_spread``: effective number of opponent replies one ply later (``maia_reply_spread``);
- ``played_3``: signed material after LINE_DEPTH plies of the played line (positive = the
  blunderer is ahead), ``mate_ply``: the ply of the opponent's mate in that line;
- ``best_3`` / ``best_mate_ply``: the same two facts for the best line (254 D-05);
- ``best_prob``, ``pre_spread``: optional D-08 inputs (the best move's Maia probability and
  the reply spread of the position before the blunder).

Term rules (identical in both twins):
- loss = ``loss_feature(-played_3, mate_ply)``: net material down after LINE_DEPTH plies,
  capped at LOSS_CAP, raised to the model's loss floor, MATE_LOSS when the blunderer is mated
  within LINE_DEPTH plies; None (row unscored) when ``played_3`` is None and no mate settles it.
  A missing played probability also leaves the row unscored.
- missed = ``missed_feature``: ``best_3 - max(0, played_3)`` (swing minus loss, 254 D-05),
  raised to the model's missed floor when it has one and capped at its missed cap; the model's
  missed-mate value when the best line mates within LINE_DEPTH; 0 when the best line is
  unknown (D-18: an unknown gain contributes nothing, the row keeps its loss-only score).
- material (D-06): "combined" adds ``loss_coef * (loss + lam * missed)``; "split" adds
  ``loss_coef * loss`` plus ``missed_coef * lam * missed``. Lambda (D-03, D-04) multiplies the
  missed term only, so lam 0 is the loss-only score.
- spread (D-07): "always" adds ``spread_coef * reply_spread`` on every row (a missing spread
  leaves the row unscored); "loss_only" adds it only when loss > 0 (else 0, even with a missing
  spread); "best_prob_for_misses" does the same and, when loss is not > 0, adds the best-prob
  term instead.
- optional (D-08): ``best_prob_coef * ln(best_prob + PLAYED_PROB_OFFSET)`` (0 when best_prob is
  None, consistent with D-18) and ``pre_spread_coef * pre_spread`` (0 when None).
- Every coefficient of an optional term that is exactly 0.0 (and a zero lambda weight) omits
  its term at build time in both twins, so a NULL unused input never unscores a row.
- There is no forcing-flag input (254 D-10).

The formula exists twice: ``facepalm_score`` (Python) and ``facepalm_score_sql`` (SQLAlchemy
expression, so selection stays a plain SQL filter on game_flaws). If either side changes,
update the other; ``tests/services/test_facepalm_score.py`` pins them together. The default
model is ``FACEPALM_MODEL``, built from the FACEPALM_* constants in ``blunder_check_rules``
(its pre-refit values reproduce the Phase 250 score exactly, D-12); tests and the fit script
pass an explicit model. Pure, no I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final, NamedTuple

from sqlalchemy import ColumnElement, Float, case, func, literal, null, type_coerce

from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import (
    FACEPALM_BEST_PROB_COEF,
    FACEPALM_INTERCEPT,
    FACEPALM_LAMBDA_MAX,
    FACEPALM_LAMBDA_MIN,
    FACEPALM_LOSS_COEF,
    FACEPALM_LOSS_FLOOR,
    FACEPALM_MATERIAL_FORM,
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_COEF,
    FACEPALM_MISSED_FLOOR,
    FACEPALM_MISSED_MATE,
    FACEPALM_PLAYED_COEF,
    FACEPALM_PRE_SPREAD_COEF,
    FACEPALM_SPREAD_COEF,
    FACEPALM_SPREAD_FORM,
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    PLAYED_PROB_OFFSET,
    MaterialForm,
    SpreadForm,
)

__all__ = [
    "FACEPALM_MODEL",
    "FacepalmColumns",
    "FacepalmFacts",
    "FacepalmModel",
    "MaterialForm",
    "SpreadForm",
    "facepalm_expr",
    "facepalm_score",
    "facepalm_score_sql",
    "loss_feature",
    "missed_feature",
]

# The loss-term floor a model must carry when the D-05 missed term is active: D-05 fixes
# loss = max(0, -played_3), so a combined or missed-coefficient model reads loss >= 0 only.
_MISSED_REQUIRED_LOSS_FLOOR: Final[int] = 0


@dataclass(frozen=True, slots=True)
class FacepalmModel:
    """Fitted logistic model; the defaults of the shape fields are the pre-refit values (D-12).

    `loss_floor` lower-clips the loss input when not None. `material_form`, `spread_form` and
    the three optional coefficients select the D-06 / D-07 / D-08 shapes (module docstring).
    """

    intercept: float
    played_coef: float
    spread_coef: float
    loss_coef: float
    loss_floor: int | None
    material_form: MaterialForm = "split"
    missed_coef: float = 0.0
    missed_floor: int | None = 0
    missed_cap: int = LOSS_CAP
    missed_mate: int = MATE_LOSS
    spread_form: SpreadForm = "always"
    best_prob_coef: float = 0.0
    pre_spread_coef: float = 0.0

    def __post_init__(self) -> None:
        missed_active = self.material_form == "combined" or self.missed_coef != 0.0
        if missed_active and self.loss_floor != _MISSED_REQUIRED_LOSS_FLOOR:
            raise ValueError("an active missed term requires loss_floor == 0 (D-05)")


# The shipped model, built from the FACEPALM_* constants; the default of both score twins.
FACEPALM_MODEL: Final[FacepalmModel] = FacepalmModel(
    intercept=FACEPALM_INTERCEPT,
    played_coef=FACEPALM_PLAYED_COEF,
    spread_coef=FACEPALM_SPREAD_COEF,
    loss_coef=FACEPALM_LOSS_COEF,
    loss_floor=FACEPALM_LOSS_FLOOR,
    material_form=FACEPALM_MATERIAL_FORM,
    missed_coef=FACEPALM_MISSED_COEF,
    missed_floor=FACEPALM_MISSED_FLOOR,
    missed_cap=FACEPALM_MISSED_CAP,
    missed_mate=FACEPALM_MISSED_MATE,
    spread_form=FACEPALM_SPREAD_FORM,
    best_prob_coef=FACEPALM_BEST_PROB_COEF,
    pre_spread_coef=FACEPALM_PRE_SPREAD_COEF,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FacepalmFacts:
    """The stored facts of one blunder, as scalars (the Python twin's input); all optional."""

    played_prob: float | None
    reply_spread: float | None
    played_3: int | None
    mate_ply: int | None
    best_3: int | None = None
    best_mate_ply: int | None = None
    best_prob: float | None = None
    pre_spread: float | None = None


class FacepalmColumns(NamedTuple):
    """The stored facts of one blunder as SQL column expressions (the SQL twin's input).

    `played_material` and `best_material` are the signed 9-slot arrays; the twin reads slot
    LINE_DEPTH (one-based indexing).
    """

    played_prob: Any
    reply_spread: Any
    played_material: Any
    mate_ply: Any
    best_material: Any
    best_mate_ply: Any
    best_prob: Any
    pre_spread: Any


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


def missed_feature(
    played_3: int | None,
    best_3: int | None,
    best_mate_ply: int | None,
    *,
    missed_floor: int | None,
    missed_cap: int,
    missed_mate: int,
) -> float:
    """The missed input of the score (254 D-05): the gain the blunderer left on the table.

    `best_3 - max(0, played_3)`, i.e. the swing minus the loss. A best line that mates within
    LINE_DEPTH plies counts `missed_mate`. An unknown best line (or played line) contributes 0
    (D-18), so the row keeps its loss-only score. Raised to `missed_floor` when it is not None
    (the raw value is negative when the best line is behind at depth 3), then capped.
    """
    if best_mate_ply is not None and best_mate_ply <= LINE_DEPTH:
        return float(missed_mate)
    if best_3 is None or played_3 is None:
        return 0.0
    raw = best_3 - max(0, played_3)
    if missed_floor is not None:
        raw = max(raw, missed_floor)
    return float(min(raw, missed_cap))


def _check_lambda(lam: float) -> None:
    if not FACEPALM_LAMBDA_MIN <= lam <= FACEPALM_LAMBDA_MAX:
        raise ValueError("lam must lie within [FACEPALM_LAMBDA_MIN, FACEPALM_LAMBDA_MAX]")


def _missed_weight(model: FacepalmModel, lam: float) -> float:
    """Coefficient of the missed term in z: the combined form scales loss_coef, split its own."""
    if model.material_form == "combined":
        return model.loss_coef * lam
    return model.missed_coef * lam


def _best_prob_term(model: FacepalmModel, best_prob: float | None) -> float:
    """The D-08 best-move term; 0 when the coefficient is 0 or the best move's probability is unknown."""
    if model.best_prob_coef == 0.0 or best_prob is None:
        return 0.0
    return model.best_prob_coef * math.log(best_prob + PLAYED_PROB_OFFSET)


def _spread_term(model: FacepalmModel, facts: FacepalmFacts, loss: float) -> float | None:
    """The D-07 spread term, or None when the form reads a spread the row does not have."""
    if model.spread_form != "always" and loss <= 0:
        # A pure miss: no reply spread; best_prob_for_misses swaps in the best-move term.
        if model.spread_form == "best_prob_for_misses":
            return _best_prob_term(model, facts.best_prob)
        return 0.0
    if facts.reply_spread is None:
        return None
    return model.spread_coef * facts.reply_spread


def _optional_terms(model: FacepalmModel, facts: FacepalmFacts) -> float:
    """The D-08 additive terms outside the spread slot (each 0 when its input is unknown)."""
    total = 0.0
    if model.spread_form != "best_prob_for_misses":
        total += _best_prob_term(model, facts.best_prob)
    if model.pre_spread_coef != 0.0 and facts.pre_spread is not None:
        total += model.pre_spread_coef * facts.pre_spread
    return total


def facepalm_score(
    facts: FacepalmFacts, *, lam: float, model: FacepalmModel = FACEPALM_MODEL
) -> float | None:
    """Facepalm score in (0, 1), or None when a required input is missing.

    `lam` is the loss-aversion weight of the missed term (D-03 / D-04; there is no default so
    every caller names its consumer's constant). Python twin of `facepalm_score_sql`: if either
    side changes, update the other.
    """
    _check_lambda(lam)
    if facts.played_prob is None:
        return None
    loss_3 = None if facts.played_3 is None else -facts.played_3
    loss = loss_feature(loss_3, facts.mate_ply, loss_floor=model.loss_floor)
    spread = None if loss is None else _spread_term(model, facts, loss)
    if loss is None or spread is None:
        return None
    z = (
        model.intercept
        + model.played_coef * math.log(facts.played_prob + PLAYED_PROB_OFFSET)
        + spread
        + model.loss_coef * loss
        + _optional_terms(model, facts)
    )
    weight = _missed_weight(model, lam)
    if weight != 0.0:
        missed = missed_feature(
            facts.played_3,
            facts.best_3,
            facts.best_mate_ply,
            missed_floor=model.missed_floor,
            missed_cap=model.missed_cap,
            missed_mate=model.missed_mate,
        )
        z += weight * missed
    return 1.0 / (1.0 + math.exp(-z))


def _loss_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    """SQL twin of the loss input: NULL when the played line is unknown and no mate settles it."""
    played_3 = columns.played_material[LINE_DEPTH]
    capped = func.least(-played_3, LOSS_CAP)
    if model.loss_floor is not None:
        capped = func.greatest(capped, model.loss_floor)
    return case(
        (columns.mate_ply <= LINE_DEPTH, literal(float(MATE_LOSS))),
        (played_3.is_(None), null()),
        else_=capped,
    )


def _missed_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    """SQL twin of `missed_feature`; explicit CASE guards, never GREATEST/LEAST over a NULL."""
    played_3 = columns.played_material[LINE_DEPTH]
    best_3 = columns.best_material[LINE_DEPTH]
    played_positive = case((played_3 > 0, played_3), else_=literal(0))
    raw = best_3 - played_positive
    if model.missed_floor is not None:
        raw = func.greatest(raw, model.missed_floor)
    return case(
        (columns.best_mate_ply <= LINE_DEPTH, literal(float(model.missed_mate))),
        (best_3.is_(None), literal(0.0)),
        (played_3.is_(None), literal(0.0)),
        else_=func.least(raw, model.missed_cap),
    )


def _best_prob_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    """SQL twin of `_best_prob_term`: 0.0 for a zero coefficient or a NULL best-move probability."""
    if model.best_prob_coef == 0.0:
        return literal(0.0)
    return case(
        (columns.best_prob.is_(None), literal(0.0)),
        else_=model.best_prob_coef * func.ln(columns.best_prob + PLAYED_PROB_OFFSET),
    )


def _spread_sql(
    columns: FacepalmColumns, model: FacepalmModel, loss: ColumnElement[Any]
) -> ColumnElement[Any]:
    """SQL twin of `_spread_term`: a gated form is an explicit CASE on loss > 0 (never NULL-gated)."""
    spread = model.spread_coef * columns.reply_spread
    if model.spread_form == "always":
        return spread
    pure_miss = (
        _best_prob_sql(columns, model)
        if model.spread_form == "best_prob_for_misses"
        else literal(0.0)
    )
    return case((loss > 0, spread), else_=pure_miss)


def _optional_sql(columns: FacepalmColumns, model: FacepalmModel) -> list[ColumnElement[Any]]:
    """SQL twin of `_optional_terms`: only the terms whose coefficient is not 0.0."""
    terms: list[ColumnElement[Any]] = []
    if model.spread_form != "best_prob_for_misses" and model.best_prob_coef != 0.0:
        terms.append(_best_prob_sql(columns, model))
    if model.pre_spread_coef != 0.0:
        terms.append(
            case(
                (columns.pre_spread.is_(None), literal(0.0)),
                else_=model.pre_spread_coef * columns.pre_spread,
            )
        )
    return terms


def facepalm_score_sql(
    columns: FacepalmColumns, *, lam: float, model: FacepalmModel = FACEPALM_MODEL
) -> ColumnElement[float]:
    """SQL twin of `facepalm_score` as a SQLAlchemy expression (NULL when an input is missing).

    The term rules are in the module docstring. A NULL played probability or spread propagates
    through LN and the arithmetic; the loss, missed and gated terms use explicit CASE branches
    because PostgreSQL LEAST/GREATEST skip NULLs. Terms with a zero coefficient are omitted so
    their NULL inputs never unscore a row.

    Its Python twin is `facepalm_score`: if either side changes, update the other.
    """
    _check_lambda(lam)
    loss = _loss_sql(columns, model)
    z = (
        model.intercept
        + model.played_coef * func.ln(columns.played_prob + PLAYED_PROB_OFFSET)
        + _spread_sql(columns, model, loss)
        + model.loss_coef * loss
    )
    for term in _optional_sql(columns, model):
        z = z + term
    weight = _missed_weight(model, lam)
    if weight != 0.0:
        z = z + weight * _missed_sql(columns, model)
    # type_coerce only retypes the expression for the checker (PostgreSQL exp() is double precision).
    return type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))


def facepalm_expr(lam: float, model: FacepalmModel = FACEPALM_MODEL) -> ColumnElement[float]:
    """The facepalm score of a ``game_flaws`` row as one SQL expression over its stored facts (D-01).

    This is the single query-time expression every reader uses from release R2 on: it reads the
    fact columns (``maia_played_prob``, ``maia_reply_spread``, ``played_line_material``,
    ``line_mate_ply``, ``best_line_material``, ``best_line_mate_ply``, ``maia_best_prob``,
    ``maia_pre_spread``) and is NULL for a row that is not scored. Each reader passes its own
    lambda constant (``FACEPALM_DRILL_LAMBDA`` or ``FACEPALM_LIBRARY_LAMBDA``), binds the
    expression once per query and uses the same object in the SELECT and the WHERE, so the
    chip a user sees and the filter that selected the row can never disagree.
    """
    return facepalm_score_sql(
        FacepalmColumns(
            played_prob=GameFlaw.maia_played_prob,
            reply_spread=GameFlaw.maia_reply_spread,
            played_material=GameFlaw.played_line_material,
            mate_ply=GameFlaw.line_mate_ply,
            best_material=GameFlaw.best_line_material,
            best_mate_ply=GameFlaw.best_line_mate_ply,
            best_prob=GameFlaw.maia_best_prob,
            pre_spread=GameFlaw.maia_pre_spread,
        ),
        lam=lam,
        model=model,
    )
