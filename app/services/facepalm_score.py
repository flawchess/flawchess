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
- ``played_material`` / ``best_material``: the signed 9-slot material arrays of the played and
  the best line (positive = the blunderer is ahead; Python index N - 1 = depth N, SQL index N);
  ``played_3`` / ``best_3`` are their depth-3 slots;
- ``mate_ply``: the ply of the opponent's mate in the played line, ``best_mate_ply``: the ply of
  the mate in the best line (254 D-05);
- ``best_prob``, ``pre_spread``: optional D-08 inputs (the best move's Maia probability and
  the reply spread of the position before the blunder).

Term rules (identical in both twins):
- loss (``material_loss``), in three stages. Coverage (256 D-03, every input): a mate within
  LINE_DEPTH plies gives MATE_LOSS; otherwise an unknown depth-3 slot leaves the row unscored
  (None). Then the model's ``material_input`` (256 D-06): "depth_3" is ``loss_feature(-played_3)``,
  the net loss after LINE_DEPTH plies capped at LOSS_CAP and raised to the model's loss floor;
  "decaying_mean" is the weighted mean of that loss over the odd depths 1, 3, 5, 7, 9 (a mate
  beyond LINE_DEPTH counts MATE_LOSS from its ply on); "first_stable" is the first odd-depth loss
  that the next odd depth repeats, discounted by MATERIAL_DECAY_RATIO to the power of its onset
  index (no repeated pair: the last known loss, discounted by its own index). A missing played
  probability also leaves the row unscored.
- missed (``material_missed``), in the same three stages: a best-line mate within LINE_DEPTH gives
  the model's missed-mate value; an unknown played depth-3 slot gives 0 for every input; then
  "depth_3" is ``missed_feature`` (``best_3 - max(0, played_3)``, swing minus loss, 254 D-05,
  raised to the model's missed floor when it has one and capped at its missed cap) and
  "decaying_mean" is the weighted mean of that gain over the odd depths and "first_stable" its
  first confirmed value (same rule as the loss). An unknown best line
  contributes 0 (D-18: an unknown gain contributes nothing, the row keeps its loss-only score).
  Loss and missed always read the same material input (no mixed inputs).
- material (D-06): "combined" adds ``loss_coef * (loss + lam * missed)``; "split" adds
  ``loss_coef * loss`` plus ``missed_coef * lam * missed``. Lambda (D-03, D-04) multiplies the
  missed term only, so lam 0 is the loss-only score.
- spread (D-07): "always" adds ``spread_coef * reply_spread`` on every row (a missing spread
  leaves the row unscored); "loss_only" adds it only when the row loses material (else 0, even
  with a missing spread); "best_prob_for_misses" does the same and, when the row does not lose
  material, adds the best-prob term instead. "Loses material" is ``loses(loss, model.loss_gate)``
  (256 D-11): loss > 0 for gate None, loss >= gate for a number. A pure miss under
  "best_prob_for_misses" with a non-zero best-prob coefficient and an unknown best-move
  probability is unscored, like a NULL spread under "always" (256 D-04, 254 WR-01).
- optional (D-08): on the additive path (every spread form but "best_prob_for_misses"),
  ``best_prob_coef * ln(best_prob + PLAYED_PROB_OFFSET)`` (0 when best_prob is None, consistent
  with D-18) and ``pre_spread_coef * pre_spread`` (0 when None).
- Every coefficient of an optional term that is exactly 0.0 (and a zero lambda weight) omits
  its term at build time in both twins, so a NULL unused input never unscores a row.
- There is no forcing-flag input (254 D-10).

Facepalm type (257 D-02): every scored blunder is either a missed win or an allowed loss, decided
on the same ``loss`` and ``missed`` inputs the score reads (material units, after the model's
floors, caps and depth aggregation): allowed loss when ``loss > 0 and loss >= missed`` (a tie is
an allowed loss), missed win otherwise (a row with no material in either line is a missed win).
The type is NULL / None exactly when the loss input is unknown. It takes no lambda and no fitted
coefficient: the model weights lost material about three times as much as a missed gain, so the
types are only ever compared with the same type of the opponents (257 D-04). Twins:
``facepalm_type`` (Python) and ``facepalm_type_sql`` / ``facepalm_type_expr`` (SQL).

The formula exists twice: ``facepalm_score`` (Python) and ``facepalm_score_sql`` (SQLAlchemy
expression, so selection stays a plain SQL filter on game_flaws). If either side changes,
update the other; ``tests/services/test_facepalm_score.py`` pins them together. The default
model is ``FACEPALM_MODEL``, built from the FACEPALM_* constants in ``blunder_check_rules``
(its pre-refit values reproduce the Phase 250 score exactly, D-12); tests and the fit script
pass an explicit model. Pure, no I/O.
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
    FACEPALM_LOSS_FLOOR,
    FACEPALM_LOSS_GATE,
    FACEPALM_MATERIAL_FORM,
    FACEPALM_MATERIAL_INPUT,
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
    MaterialInput,
    SpreadForm,
)
from app.services.facepalm_material import (
    aggregate,
    aggregate_sql,
    gain_by_depth,
    gain_by_depth_sql,
    loses,
    loses_sql,
    loss_by_depth,
    loss_by_depth_sql,
)
from app.services.line_material import material_at_depth

__all__ = [
    "FACEPALM_MODEL",
    "FACEPALM_TYPES",
    "FacepalmColumns",
    "FacepalmFacts",
    "FacepalmModel",
    "FacepalmType",
    "MaterialForm",
    "MaterialInput",
    "SpreadForm",
    "facepalm_expr",
    "facepalm_score",
    "facepalm_score_sql",
    "facepalm_type",
    "facepalm_type_expr",
    "facepalm_type_from_sql",
    "facepalm_type_of",
    "facepalm_type_sql",
    "loss_feature",
    "material_loss",
    "material_missed",
    "missed_feature",
]

# 257 D-02: the type of a scored blunder. The strings travel through the library payloads and the
# frontend mirror (frontend/src/types/library.ts), so renaming them touches every reader.
FacepalmType = Literal["missed_win", "allowed_loss"]
FACEPALM_TYPES: Final[tuple[FacepalmType, ...]] = ("missed_win", "allowed_loss")

# The loss-term floor a model must carry when the D-05 missed term is active: D-05 fixes
# loss = max(0, -played_3), so a combined or missed-coefficient model reads loss >= 0 only.
_MISSED_REQUIRED_LOSS_FLOOR: Final[int] = 0


@dataclass(frozen=True, slots=True)
class FacepalmModel:
    """Fitted logistic model; the defaults of the shape fields are the pre-refit values (D-12).

    `loss_floor` lower-clips the loss input when not None. `material_form`, `spread_form` and
    the three optional coefficients select the D-06 / D-07 / D-08 shapes (module docstring);
    `material_input` selects the depths the loss and the missed gain read (256 D-06) and
    `loss_gate` the "loses material" threshold of the gated spread forms (256 D-11).
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
    material_input: MaterialInput = "depth_3"
    loss_gate: float | None = None

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
    material_input=FACEPALM_MATERIAL_INPUT,
    loss_gate=FACEPALM_LOSS_GATE,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FacepalmFacts:
    """The stored facts of one blunder (the Python twin's input); all optional.

    `played_material` and `best_material` are the stored signed 9-slot arrays, 0-based in
    Python (slot N - 1 = depth N). `played_3` and `best_3` are their depth-3 slots.
    """

    played_prob: float | None
    reply_spread: float | None
    played_material: Sequence[int | None] | None
    mate_ply: int | None
    best_material: Sequence[int | None] | None = None
    best_mate_ply: int | None = None
    best_prob: float | None = None
    pre_spread: float | None = None

    @property
    def played_3(self) -> int | None:
        """Signed material of the played line at LINE_DEPTH (reports and tests)."""
        return material_at_depth(self.played_material, LINE_DEPTH)

    @property
    def best_3(self) -> int | None:
        """Signed material of the best line at LINE_DEPTH (reports and tests)."""
        return material_at_depth(self.best_material, LINE_DEPTH)


class FacepalmColumns(NamedTuple):
    """The stored facts of one blunder as SQL column expressions (the SQL twin's input).

    `played_material` and `best_material` are the signed 9-slot arrays; the twin reads the
    slots of the model's material input (one-based indexing: slot N = depth N).
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


def material_loss(
    played_material: Sequence[int | None] | None,
    mate_ply: int | None,
    *,
    material_input: MaterialInput,
    loss_floor: int | None,
) -> float | None:
    """The loss input of the score under `material_input`, or None when the row is unscored.

    Coverage gate shared by every input (256 D-03): a mate within LINE_DEPTH plies gives
    MATE_LOSS (the short-circuit, so a mate at ply 3 is never averaged down), an unknown depth-3
    slot gives None. Then "depth_3" is `loss_feature` and an aggregate input ("decaying_mean",
    "first_stable") aggregates the per-depth loss.
    """
    if mate_ply is not None and mate_ply <= LINE_DEPTH:
        return float(MATE_LOSS)
    played_3 = material_at_depth(played_material, LINE_DEPTH)
    if played_3 is None:
        return None
    if material_input == "depth_3":
        return loss_feature(-played_3, mate_ply, loss_floor=loss_floor)
    return aggregate(
        material_input, loss_by_depth(played_material, mate_ply, loss_floor=loss_floor)
    )


def material_missed(
    played_material: Sequence[int | None] | None,
    best_material: Sequence[int | None] | None,
    best_mate_ply: int | None,
    *,
    material_input: MaterialInput,
    missed_floor: int | None,
    missed_cap: int,
    missed_mate: int,
) -> float:
    """The missed input of the score under `material_input` (never None).

    A best-line mate within LINE_DEPTH plies gives `missed_mate`; an unknown played depth-3 slot
    gives 0.0 for every input (so all inputs treat the same rows the same way). Then "depth_3" is
    `missed_feature` and an aggregate input aggregates the per-depth gain, 0.0 when no depth is
    known (D-18: an unknown best line contributes nothing).
    """
    if best_mate_ply is not None and best_mate_ply <= LINE_DEPTH:
        return float(missed_mate)
    played_3 = material_at_depth(played_material, LINE_DEPTH)
    if played_3 is None:
        return 0.0
    if material_input == "depth_3":
        return missed_feature(
            played_3,
            material_at_depth(best_material, LINE_DEPTH),
            best_mate_ply,
            missed_floor=missed_floor,
            missed_cap=missed_cap,
            missed_mate=missed_mate,
        )
    settled = aggregate(
        material_input,
        gain_by_depth(
            played_material,
            best_material,
            best_mate_ply,
            missed_floor=missed_floor,
            missed_cap=missed_cap,
            missed_mate=missed_mate,
        ),
    )
    return 0.0 if settled is None else settled


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


def _pure_miss_term(model: FacepalmModel, best_prob: float | None) -> float | None:
    """The best_prob_for_misses term of a row that does not lose material (256 D-04, 254 WR-01).

    Fix of 254 WR-01: a pure miss with an unknown best-move probability used to read the best-move
    term as 0 (`_best_prob_term`), which ranked it as if the best move were likely. Such a row
    cannot be scored, like a NULL spread under "always": None here leaves it unscored. A zero
    coefficient omits the term, so it never unscores a row.
    """
    if model.best_prob_coef == 0.0:
        return 0.0
    if best_prob is None:
        return None
    return model.best_prob_coef * math.log(best_prob + PLAYED_PROB_OFFSET)


def _spread_term(model: FacepalmModel, facts: FacepalmFacts, loss: float) -> float | None:
    """The D-07 spread term, or None when the form reads an input the row does not have."""
    if model.spread_form != "always" and not loses(loss, model.loss_gate):
        # A pure miss: no reply spread; best_prob_for_misses swaps in the best-move term.
        if model.spread_form == "best_prob_for_misses":
            return _pure_miss_term(model, facts.best_prob)
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
    loss = material_loss(
        facts.played_material,
        facts.mate_ply,
        material_input=model.material_input,
        loss_floor=model.loss_floor,
    )
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
        missed = material_missed(
            facts.played_material,
            facts.best_material,
            facts.best_mate_ply,
            material_input=model.material_input,
            missed_floor=model.missed_floor,
            missed_cap=model.missed_cap,
            missed_mate=model.missed_mate,
        )
        z += weight * missed
    return 1.0 / (1.0 + math.exp(-z))


def _loss_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    """SQL twin of `material_loss`: NULL when the played line is unknown and no mate settles it."""
    played_3 = columns.played_material[LINE_DEPTH]
    if model.material_input == "depth_3":
        capped = func.least(-played_3, LOSS_CAP)
        if model.loss_floor is not None:
            capped = func.greatest(capped, model.loss_floor)
        settled = capped
    else:
        settled = aggregate_sql(
            model.material_input,
            loss_by_depth_sql(
                columns.played_material, columns.mate_ply, loss_floor=model.loss_floor
            ),
        )
    return case(
        (columns.mate_ply <= LINE_DEPTH, literal(float(MATE_LOSS))),
        (played_3.is_(None), null()),
        else_=settled,
    )


def _missed_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    """SQL twin of `material_missed`; explicit CASE guards, never GREATEST/LEAST over a NULL."""
    played_3 = columns.played_material[LINE_DEPTH]
    if model.material_input != "depth_3":
        settled = func.coalesce(
            aggregate_sql(
                model.material_input,
                gain_by_depth_sql(
                    columns.played_material,
                    columns.best_material,
                    columns.best_mate_ply,
                    missed_floor=model.missed_floor,
                    missed_cap=model.missed_cap,
                    missed_mate=model.missed_mate,
                ),
            ),
            literal(0.0),
        )
        return case(
            (columns.best_mate_ply <= LINE_DEPTH, literal(float(model.missed_mate))),
            (played_3.is_(None), literal(0.0)),
            else_=settled,
        )
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


def _pure_miss_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    """SQL twin of `_pure_miss_term`: NULL (row unscored) for a NULL best-move probability.

    Fix of 254 WR-01: the pure-miss branch used `_best_prob_sql`, whose NULL arm reads 0.0, so a
    no-loss row with an unknown best-move probability scored as if the best move were likely.
    """
    if model.best_prob_coef == 0.0:
        return literal(0.0)
    return case(
        (columns.best_prob.is_(None), null()),
        else_=model.best_prob_coef * func.ln(columns.best_prob + PLAYED_PROB_OFFSET),
    )


def _spread_sql(
    columns: FacepalmColumns, model: FacepalmModel, loss: ColumnElement[Any]
) -> ColumnElement[Any]:
    """SQL twin of `_spread_term`: a gated form is an explicit CASE on `loses` (never NULL-gated)."""
    spread = model.spread_coef * columns.reply_spread
    if model.spread_form == "always":
        return spread
    pure_miss = (
        _pure_miss_sql(columns, model)
        if model.spread_form == "best_prob_for_misses"
        else literal(0.0)
    )
    return case((loses_sql(loss, model.loss_gate), spread), else_=pure_miss)


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


def _game_flaw_columns() -> FacepalmColumns:
    """The ``game_flaws`` column map every query-time expression of a row reads."""
    return FacepalmColumns(
        played_prob=GameFlaw.maia_played_prob,
        reply_spread=GameFlaw.maia_reply_spread,
        played_material=GameFlaw.played_line_material,
        mate_ply=GameFlaw.line_mate_ply,
        best_material=GameFlaw.best_line_material,
        best_mate_ply=GameFlaw.best_line_mate_ply,
        best_prob=GameFlaw.maia_best_prob,
        pre_spread=GameFlaw.maia_pre_spread,
    )


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


def facepalm_type(
    facts: FacepalmFacts, *, model: FacepalmModel = FACEPALM_MODEL
) -> FacepalmType | None:
    """Python twin of `facepalm_type_sql`: None exactly when the loss input is unknown.

    Reads the same `material_loss` / `material_missed` calls `facepalm_score` makes. It always
    computes `missed`, also where the score's missed weight is 0, so it deliberately does not
    route through `_missed_weight`. If either twin changes, update the other.
    """
    loss = material_loss(
        facts.played_material,
        facts.mate_ply,
        material_input=model.material_input,
        loss_floor=model.loss_floor,
    )
    missed = material_missed(
        facts.played_material,
        facts.best_material,
        facts.best_mate_ply,
        material_input=model.material_input,
        missed_floor=model.missed_floor,
        missed_cap=model.missed_cap,
        missed_mate=model.missed_mate,
    )
    return facepalm_type_of(loss, missed)


def facepalm_type_sql(
    columns: FacepalmColumns, *, model: FacepalmModel = FACEPALM_MODEL
) -> ColumnElement[str]:
    """SQL twin of `facepalm_type` (257 D-02): NULL when the loss input is unknown.

    Allowed loss when loss > 0 and loss >= missed, missed win otherwise; the same rule as
    `facepalm_type_of`. Its Python twin is `facepalm_type`: if either side changes, update the other.
    """
    loss = _loss_sql(columns, model)
    missed = _missed_sql(columns, model)
    # type_coerce only retypes the CASE for the checker (its branches are string literals).
    return type_coerce(
        case(
            (loss.is_(None), null()),
            (and_(loss > 0, loss >= missed), literal("allowed_loss")),
            else_=literal("missed_win"),
        ),
        String(),
    )


def facepalm_type_expr(model: FacepalmModel = FACEPALM_MODEL) -> ColumnElement[str]:
    """The facepalm type of a ``game_flaws`` row as one SQL expression (257 D-02).

    The single query-time type every reader uses, over the same column map as `facepalm_expr`.
    Lambda-free and coefficient-free: it does not move with the library or the drill lambda.
    Readers null the type wherever the score is NULL (the type is NULL only for an unknown loss,
    the score is also NULL for a missing played probability, spread or best-move probability).
    """
    return facepalm_type_sql(_game_flaw_columns(), model=model)


def facepalm_type_from_sql(value: str | None) -> FacepalmType | None:
    """Narrow the string a `facepalm_type_expr` column returns to the `FacepalmType` literal."""
    if value is None:
        return None
    for member in FACEPALM_TYPES:
        if value == member:
            return member
    raise ValueError("unexpected facepalm type")
