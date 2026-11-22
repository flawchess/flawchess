"""facepalm_score.py - the facepalm score of a user blunder (Phase 250 D-01, D-04; Phase 259 D-05, D-08).

A logistic score in [0, 1] at the mover's level: 0 = basically no chance the player could
have seen the blunder, 1 = a very careless blunder the player should absolutely have
avoided. It is a RANKING fitted on the owner's labels, not a probability: the label sets are
mostly rule passers, so the values are not calibrated to all blunders and no copy may
present the score as a share of peers.

    z     = intercept + played_coef * ln(played_prob + PLAYED_PROB_OFFSET)
                      + loss_coef * loss + missed_coef * lam * missed + key-move term
    score = 1 / (1 + exp(-z))

The key-move term reads the opponent's reply on a losing row and the best move on a row that
loses nothing:

    key-move term = reply_prob_coef * ln(reply_prob + PLAYED_PROB_OFFSET)   when loss > 0
                  = best_prob_coef  * ln(best_prob  + PLAYED_PROB_OFFSET)   otherwise

Inputs, all stored scalars on game_flaws (no engine and no line arrays at scoring time):
- ``played_prob``: Maia's probability for the played move (``maia_played_prob``);
- ``loss`` / ``missed``: the decaying-mean material the blunderer loses along the played line and
  leaves on the table along the best line (``material_loss`` / ``material_missed``, written by
  ``facepalm_inputs`` under the quiet rule);
- ``best_prob``: Maia's probability for the best move (``maia_best_prob``);
- ``reply_prob``: Maia's probability of the opponent's refutation reply (``maia_best_reply_prob``).

Term rules (identical in both twins):
- A NULL played probability or a NULL loss leaves the row unscored (the SQL twin has an explicit
  first CASE branch for it, so a NULL loss never reaches the ELSE branch).
- A losing row (loss > 0) with a NULL reply probability, and a row that loses nothing with a
  NULL best-move probability, are unscored (256 D-04, mirrored for the reply).
- Lambda (D-03, D-04) multiplies the missed term only, so lam 0 is the loss-only score. The
  stored pair is NULL together (ck_game_flaws_material_pair), so a scored row has a missed value.
- A coefficient that is exactly 0.0 (and a zero lambda weight) omits its term at build time in both
  twins, so its NULL input never unscores a row.

Facepalm type (257 D-02): every scored blunder is either a missed win or an allowed loss, decided
on the same ``loss`` and ``missed`` inputs the score reads: allowed loss when
``loss > 0 and loss >= missed`` (a tie is an allowed loss), missed win otherwise (a row with no
material in either line is a missed win). The type is NULL / None exactly when the loss is
unknown. It takes no lambda and no fitted coefficient: the model weights lost material about twice
as much as a missed gain, so the types are only ever compared with the same type of the opponents
(257 D-04). Twins: ``facepalm_type`` (Python) and ``facepalm_type_sql`` / ``facepalm_type_expr`` (SQL).

The formula exists twice: ``facepalm_score`` (Python) and ``facepalm_score_sql`` (SQLAlchemy
expression, so selection stays a plain SQL filter on game_flaws). If either side changes,
update the other; ``tests/services/test_facepalm_score.py`` pins them together. The default
model is ``FACEPALM_MODEL``, built from the FACEPALM_* constants in ``blunder_check_rules``;
tests and the fit script pass an explicit model. Pure, no I/O.

The write-time half of this module (``material_loss``, ``material_missed``) turns the played and
best lines into the two stored material numbers (the decaying mean over the odd depths); the
score itself never calls it. ``facepalm_inputs`` is its caller.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal, NamedTuple

from sqlalchemy import ColumnElement, Float, String, and_, case, func, literal, null, type_coerce

from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import (
    FACEPALM_BEST_PROB_COEF,
    FACEPALM_INTERCEPT,
    FACEPALM_LAMBDA_MAX,
    FACEPALM_LAMBDA_MIN,
    FACEPALM_LOSS_COEF,
    FACEPALM_MISSED_COEF,
    FACEPALM_PLAYED_COEF,
    FACEPALM_REPLY_PROB_COEF,
    LINE_DEPTH,
    MATE_LOSS,
    PLAYED_PROB_OFFSET,
)
from app.services.facepalm_material import decaying_mean, gain_by_depth, loss_by_depth
from app.services.line_material import material_at_depth

__all__ = [
    "FACEPALM_MODEL",
    "FACEPALM_TYPES",
    "FacepalmColumns",
    "FacepalmFacts",
    "FacepalmModel",
    "FacepalmType",
    "facepalm_expr",
    "facepalm_score",
    "facepalm_score_sql",
    "facepalm_type",
    "facepalm_type_expr",
    "facepalm_type_from_sql",
    "facepalm_type_of",
    "facepalm_type_sql",
    "material_loss",
    "material_missed",
]

# 257 D-02: the type of a scored blunder. The strings travel through the library payloads and the
# frontend mirror (frontend/src/types/library.ts), so renaming them touches every reader.
FacepalmType = Literal["missed_win", "allowed_loss"]
FACEPALM_TYPES: Final[tuple[FacepalmType, ...]] = ("missed_win", "allowed_loss")


@dataclass(frozen=True, slots=True)
class FacepalmModel:
    """The six fitted coefficients of the score (module docstring)."""

    intercept: float
    played_coef: float
    loss_coef: float
    missed_coef: float
    best_prob_coef: float
    reply_prob_coef: float


# The shipped model, built from the FACEPALM_* constants; the default of both score twins.
FACEPALM_MODEL: Final[FacepalmModel] = FacepalmModel(
    intercept=FACEPALM_INTERCEPT,
    played_coef=FACEPALM_PLAYED_COEF,
    loss_coef=FACEPALM_LOSS_COEF,
    missed_coef=FACEPALM_MISSED_COEF,
    best_prob_coef=FACEPALM_BEST_PROB_COEF,
    reply_prob_coef=FACEPALM_REPLY_PROB_COEF,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FacepalmFacts:
    """The stored scalar facts of one blunder (the Python twin's input); all but the first two optional."""

    played_prob: float | None
    loss: float | None
    missed: float | None = None
    best_prob: float | None = None
    reply_prob: float | None = None


class FacepalmColumns(NamedTuple):
    """The stored scalar facts of one blunder as SQL column expressions (the SQL twin's input)."""

    played_prob: Any
    loss: Any
    missed: Any
    best_prob: Any
    reply_prob: Any


def material_loss(
    played_material: Sequence[int | None] | None,
    mate_ply: int | None,
    *,
    loss_floor: int | None,
) -> float | None:
    """The stored loss input: the decaying mean of the per-depth loss, or None when unscored.

    Coverage gate (256 D-03): a mate within LINE_DEPTH plies gives MATE_LOSS (the short-circuit,
    so a mate at ply 3 is never averaged down), an unknown depth-3 slot gives None. Otherwise the
    decaying mean over the odd depths 1, 3, 5, 7, 9 (259 D-03).
    """
    if mate_ply is not None and mate_ply <= LINE_DEPTH:
        return float(MATE_LOSS)
    played_3 = material_at_depth(played_material, LINE_DEPTH)
    if played_3 is None:
        return None
    return decaying_mean(loss_by_depth(played_material, mate_ply, loss_floor=loss_floor))


def material_missed(
    played_material: Sequence[int | None] | None,
    best_material: Sequence[int | None] | None,
    best_mate_ply: int | None,
    *,
    missed_floor: int | None,
    missed_cap: int,
    missed_mate: int,
) -> float:
    """The stored missed input: the decaying mean of the per-depth gain (never None).

    A best-line mate within LINE_DEPTH plies gives `missed_mate`; an unknown played depth-3 slot
    gives 0.0. Otherwise the decaying mean over the odd depths, 0.0 when no depth is known
    (D-18: an unknown best line contributes nothing).
    """
    if best_mate_ply is not None and best_mate_ply <= LINE_DEPTH:
        return float(missed_mate)
    played_3 = material_at_depth(played_material, LINE_DEPTH)
    if played_3 is None:
        return 0.0
    settled = decaying_mean(
        gain_by_depth(
            played_material,
            best_material,
            best_mate_ply,
            missed_floor=missed_floor,
            missed_cap=missed_cap,
            missed_mate=missed_mate,
        )
    )
    return 0.0 if settled is None else settled


def _check_lambda(lam: float) -> None:
    if not FACEPALM_LAMBDA_MIN <= lam <= FACEPALM_LAMBDA_MAX:
        raise ValueError("lam must lie within [FACEPALM_LAMBDA_MIN, FACEPALM_LAMBDA_MAX]")


def _log_term(coef: float, prob: float | None) -> float | None:
    """`coef * ln(prob + PLAYED_PROB_OFFSET)`; 0.0 for a zero coefficient, None for an unknown probability."""
    if coef == 0.0:
        return 0.0
    if prob is None:
        return None
    return coef * math.log(prob + PLAYED_PROB_OFFSET)


def _key_move_term(model: FacepalmModel, facts: FacepalmFacts, loss: float) -> float | None:
    """The key-move term: the reply on a losing row, the best move otherwise (None = unscored)."""
    if loss > 0:
        return _log_term(model.reply_prob_coef, facts.reply_prob)
    return _log_term(model.best_prob_coef, facts.best_prob)


def facepalm_score(
    facts: FacepalmFacts, *, lam: float, model: FacepalmModel = FACEPALM_MODEL
) -> float | None:
    """Facepalm score in (0, 1), or None when a required input is missing.

    `lam` is the loss-aversion weight of the missed term (D-03 / D-04; there is no default so
    every caller names its consumer's constant). Python twin of `facepalm_score_sql`: if either
    side changes, update the other.
    """
    _check_lambda(lam)
    if facts.played_prob is None or facts.loss is None:
        return None
    key_move = _key_move_term(model, facts, facts.loss)
    if key_move is None:
        return None
    z = (
        model.intercept
        + model.played_coef * math.log(facts.played_prob + PLAYED_PROB_OFFSET)
        + model.loss_coef * facts.loss
        + key_move
    )
    weight = model.missed_coef * lam
    if weight != 0.0:
        if facts.missed is None:
            return None
        z += weight * facts.missed
    return 1.0 / (1.0 + math.exp(-z))


def _log_term_sql(coef: float, prob: Any) -> ColumnElement[Any]:
    """SQL twin of `_log_term`: a literal 0.0 for a zero coefficient (the column is not named), NULL for a NULL probability."""
    if coef == 0.0:
        return literal(0.0)
    return case((prob.is_(None), null()), else_=coef * func.ln(prob + PLAYED_PROB_OFFSET))


def _key_move_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    """SQL twin of `_key_move_term` as an explicit CASE.

    The first branch is the NULL guard: without it a NULL loss makes `loss > 0` NULL and falls
    through to the best-move ELSE branch, which scores a row the Python twin leaves unscored.
    """
    return case(
        (columns.played_prob.is_(None) | columns.loss.is_(None), null()),
        (columns.loss > 0, _log_term_sql(model.reply_prob_coef, columns.reply_prob)),
        else_=_log_term_sql(model.best_prob_coef, columns.best_prob),
    )


def facepalm_score_sql(
    columns: FacepalmColumns, *, lam: float, model: FacepalmModel = FACEPALM_MODEL
) -> ColumnElement[float]:
    """SQL twin of `facepalm_score` as a SQLAlchemy expression (NULL when an input is missing).

    The term rules are in the module docstring. A NULL played probability or loss propagates
    through LN and the arithmetic (and through the key-move CASE); terms with a zero coefficient
    are omitted so their NULL inputs never unscore a row.

    Its Python twin is `facepalm_score`: if either side changes, update the other.
    """
    _check_lambda(lam)
    z = (
        model.intercept
        + model.played_coef * func.ln(columns.played_prob + PLAYED_PROB_OFFSET)
        + model.loss_coef * columns.loss
        + _key_move_sql(columns, model)
    )
    weight = model.missed_coef * lam
    if weight != 0.0:
        z = z + weight * columns.missed
    # type_coerce only retypes the expression for the checker (PostgreSQL exp() is double precision).
    return type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))


def _game_flaw_columns() -> FacepalmColumns:
    """The ``game_flaws`` column map every query-time expression of a row reads."""
    return FacepalmColumns(
        played_prob=GameFlaw.maia_played_prob,
        loss=GameFlaw.material_loss,
        missed=GameFlaw.material_missed,
        best_prob=GameFlaw.maia_best_prob,
        reply_prob=GameFlaw.maia_best_reply_prob,
    )


def facepalm_expr(lam: float, model: FacepalmModel = FACEPALM_MODEL) -> ColumnElement[float]:
    """The facepalm score of a ``game_flaws`` row as one SQL expression over its stored facts (D-01).

    This is the single query-time expression every reader uses: it reads the stored scalars
    (``maia_played_prob``, ``material_loss``, ``material_missed``, ``maia_best_prob``,
    ``maia_best_reply_prob``) and is NULL for a row that is not scored. Each reader passes its own
    lambda constant (``FACEPALM_DRILL_LAMBDA`` or ``FACEPALM_LIBRARY_LAMBDA``), binds the
    expression once per query and uses the same object in the SELECT and the WHERE, so the
    chip a user sees and the filter that selected the row can never disagree.
    """
    return facepalm_score_sql(_game_flaw_columns(), lam=lam, model=model)


def facepalm_type_of(loss: float | None, missed: float) -> FacepalmType | None:
    """257 D-02: the type of a blunder from its material inputs, None when the loss is unknown.

    Allowed loss when ``loss > 0 and loss >= missed`` (a tie is an allowed loss), missed win
    otherwise, so a row with no material in either line is a missed win. The fitted coefficients
    are never used. Shared rule of both type twins.
    """
    if loss is None:
        return None
    return "allowed_loss" if loss > 0 and loss >= missed else "missed_win"


def facepalm_type(facts: FacepalmFacts) -> FacepalmType | None:
    """Python twin of `facepalm_type_sql`: None exactly when the loss is unknown.

    A NULL missed reads as 0.0, like the SQL twin's coalesce. If either twin changes, update the other.
    """
    return facepalm_type_of(facts.loss, 0.0 if facts.missed is None else facts.missed)


def facepalm_type_sql(columns: FacepalmColumns) -> ColumnElement[str]:
    """SQL twin of `facepalm_type` (257 D-02): NULL when the loss is unknown.

    Allowed loss when loss > 0 and loss >= missed, missed win otherwise; the same rule as
    `facepalm_type_of`. Its Python twin is `facepalm_type`: if either side changes, update the other.
    """
    missed = func.coalesce(columns.missed, literal(0.0))
    # type_coerce only retypes the CASE for the checker (its branches are string literals).
    return type_coerce(
        case(
            (columns.loss.is_(None), null()),
            (and_(columns.loss > 0, columns.loss >= missed), literal("allowed_loss")),
            else_=literal("missed_win"),
        ),
        String(),
    )


def facepalm_type_expr() -> ColumnElement[str]:
    """The facepalm type of a ``game_flaws`` row as one SQL expression (257 D-02).

    The single query-time type every reader uses, over the same column map as `facepalm_expr`.
    Lambda-free and coefficient-free: it does not move with the library or the drill lambda.
    Readers null the type wherever the score is NULL (the type is NULL only for an unknown loss,
    the score is also NULL for a missing played, best-move or reply probability).
    """
    return facepalm_type_sql(_game_flaw_columns())


def facepalm_type_from_sql(value: str | None) -> FacepalmType | None:
    """Narrow the string a `facepalm_type_expr` column returns to the `FacepalmType` literal."""
    if value is None:
        return None
    for member in FACEPALM_TYPES:
        if value == member:
            return member
    raise ValueError("unexpected facepalm type")
