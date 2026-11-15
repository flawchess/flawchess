"""Tests for app/services/facepalm_score.py, the D-04 constants and reply_spread (Phase 250, 254).

Coverage:
- formula   : facepalm_score equals the logistic of the linear predictor
- nulls     : a missing played probability, spread or (unsettled) loss gives None; a mate
              settles a missing depth-3 loss
- loss      : the cap at LOSS_CAP, MATE_LOSS inside LINE_DEPTH only, the optional loss floor
- missed    : the D-05 table, the D-18 unknown best line, the mate value, floor and cap
- pre-refit : the shipped model reproduces a frozen copy of the Phase 250 formula for every
              lambda (D-12)
- lambda    : lam 0 is the loss-only score, the missed term rises with lam, lam is range-checked
- sql twin  : facepalm_score_sql agrees with the Python function on a grid with NULL in every
              input, for both material forms and every lambda
- expr      : facepalm_expr over stored game_flaws facts equals the Python twin (D-01)
- shape CHECK: the two stored-array CHECKs reject an empty, 3-slot, [0:8] and 2-D array (D-09)
- spread    : reply_spread of a uniform policy over k moves is k and equals the Phase 247
              effective-moves value on a real position's fake policy
- constants : the known D-04 values and LINE_DEPTH being a stored depth
"""

from __future__ import annotations

import csv
import itertools
import math
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import chess
import pytest
from sqlalchemy import Float, SmallInteger, column, select, text, values
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.game_flaw import GameFlaw

from app.services.blunder_check_rules import (
    FACEPALM_BEST_PROB_COEF,
    FACEPALM_DRILL_LAMBDA,
    FACEPALM_INTERCEPT,
    FACEPALM_LAMBDA_MAX,
    FACEPALM_LAMBDA_MIN,
    FACEPALM_LIBRARY_LAMBDA,
    FACEPALM_LOSS_COEF,
    FACEPALM_LOSS_FLOOR,
    FACEPALM_MATERIAL_FORM,
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_COEF,
    FACEPALM_MISSED_FLOOR,
    FACEPALM_MISSED_MATE,
    FACEPALM_PLAYED_COEF,
    FACEPALM_PRE_SPREAD_COEF,
    FACEPALM_SCORE_MIN,
    FACEPALM_SPREAD_COEF,
    FACEPALM_SPREAD_FORM,
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    PLAYED_PROB_OFFSET,
)
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmColumns,
    FacepalmFacts,
    FacepalmModel,
    facepalm_expr,
    facepalm_score,
    facepalm_score_sql,
    loss_feature,
    missed_feature,
)
from app.services.line_material import LINE_LOSS_DEPTHS, material_at_depth
from app.services.maia_flaw_stats import _effective_moves, reply_spread
from tests.facepalm_models import PHASE_250_MODEL
from tests.facepalm_seed import seed_flaw_rows
from tests.services.maia_fakes import fake_full_policy

FORMULA_TOLERANCE = 1e-12
PARITY_TOLERANCE = 1e-9
UNIFORM_MOVE_COUNTS = (1, 2, 5, 30)
LAMBDAS = (0.0, 0.5, 1.0)
# asyncpg allows 32767 bind parameters per statement; a VALUES row of the parity grid binds 8.
GRID_CHUNK_ROWS = 2000
MISSED_MATE_VALUE = 7
STORED_FACTS_USER_ID = 925402
STORED_ARRAY_SLOTS = 9

_MODEL = FacepalmModel(
    intercept=1.0, played_coef=-0.7, spread_coef=-0.7, loss_coef=0.3, loss_floor=None
)
_FLOORED_MODEL = FacepalmModel(
    intercept=1.0, played_coef=-0.7, spread_coef=-0.7, loss_coef=0.3, loss_floor=0
)
_SPLIT_MODEL = FacepalmModel(
    intercept=1.0,
    played_coef=-0.7,
    spread_coef=-0.7,
    loss_coef=0.3,
    loss_floor=0,
    material_form="split",
    missed_coef=0.5,
    missed_mate=MISSED_MATE_VALUE,
)
_COMBINED_MODEL = FacepalmModel(
    intercept=1.0,
    played_coef=-0.7,
    spread_coef=-0.7,
    loss_coef=0.3,
    loss_floor=0,
    material_form="combined",
    missed_floor=None,
    missed_mate=MISSED_MATE_VALUE,
)
_LOSS_ONLY_MODEL = replace(_SPLIT_MODEL, spread_form="loss_only")
_BEST_PROB_MISSES_MODEL = replace(
    _SPLIT_MODEL, spread_form="best_prob_for_misses", best_prob_coef=0.4
)
_ADDITIVE_BEST_PROB_MODEL = replace(_SPLIT_MODEL, best_prob_coef=0.4)
_ADDITIVE_PRE_SPREAD_MODEL = replace(_SPLIT_MODEL, pre_spread_coef=-0.2)
_MATERIAL_MODELS = (
    pytest.param(PHASE_250_MODEL, id="pre_refit"),
    pytest.param(FACEPALM_MODEL, id="shipped"),
    pytest.param(_FLOORED_MODEL, id="floor_0"),
    pytest.param(_SPLIT_MODEL, id="split_missed"),
    pytest.param(_COMBINED_MODEL, id="combined"),
)
# Every shape of the D-06 / D-07 / D-08 model space, for the parity test over NULL-laden rows.
_SHAPE_MODELS = (
    *_MATERIAL_MODELS,
    pytest.param(_LOSS_ONLY_MODEL, id="loss_only"),
    pytest.param(_BEST_PROB_MISSES_MODEL, id="best_prob_for_misses"),
    pytest.param(_ADDITIVE_BEST_PROB_MODEL, id="additive_best_prob"),
    pytest.param(_ADDITIVE_PRE_SPREAD_MODEL, id="additive_pre_spread"),
)

# Window 14 (game 2099808, ply 23), copied from the extra row of the committed features file
# reports/blunder-check/facepalm-features-2026-11-15.tsv (facts schema). Its stored refutation
# line is one ply long (pv_plies 1), so the depth-3 played material and the mate ply are NULL.
WINDOW_14_GAME_ID = 2099808
WINDOW_14_PLY = 23
WINDOW_14_PLAYED_PROB = 0.0949175
WINDOW_14_REPLY_SPREAD = 7.75985
WINDOW_14_BEST_PROB = 0.331294
WINDOW_14_BEST_3 = 0
WINDOW_14_PLAYED_3: int | None = None
WINDOW_14_MATE_PLY: int | None = None
_FEATURES_TSV = (
    Path(__file__).resolve().parents[2]
    / "reports"
    / "blunder-check"
    / "facepalm-features-2026-11-15.tsv"
)

# Parity grid of the SQL twin: NULL in every input. A stored array is None (no array), short
# (fewer than LINE_DEPTH slots) or a full 9-slot array whose slot 3 (depth 3) varies.
_GRID_PLAYED_PROB = (0.02, None)
_GRID_SPREAD = (1.5, None)
_GRID_MATE = (None, 1, LINE_DEPTH + 1)
_GRID_BEST_MATE = (None, 0, LINE_DEPTH + 1)
_GRID_PLAYED_SLOT3 = (None, -9, -3, 0, 2)
_GRID_BEST_SLOT3 = (None, -2, 3, 10)


def _material_array(slot3: int | None) -> list[int | None]:
    """A full 9-slot signed array whose depth-3 slot is `slot3` (other slots are filler)."""
    array: list[int | None] = [0] * 9
    array[LINE_DEPTH - 1] = slot3
    return array


_GRID_PLAYED_ARRAYS: tuple[list[int | None] | None, ...] = (
    None,
    [1, 1],
    *(_material_array(slot3) for slot3 in _GRID_PLAYED_SLOT3),
)
_GRID_BEST_ARRAYS: tuple[list[int | None] | None, ...] = (
    None,
    [1],
    *(_material_array(slot3) for slot3 in _GRID_BEST_SLOT3),
)

type GridRow = tuple[
    float | None,
    float | None,
    list[int | None] | None,
    int | None,
    list[int | None] | None,
    int | None,
    float | None,
    float | None,
]


def _facts(
    *,
    played_prob: float | None = 0.1,
    reply_spread: float | None = 2.0,
    played_3: int | None = -3,
    mate_ply: int | None = None,
    best_3: int | None = None,
    best_mate_ply: int | None = None,
    best_prob: float | None = None,
    pre_spread: float | None = None,
) -> FacepalmFacts:
    return FacepalmFacts(
        played_prob=played_prob,
        reply_spread=reply_spread,
        played_3=played_3,
        mate_ply=mate_ply,
        best_3=best_3,
        best_mate_ply=best_mate_ply,
        best_prob=best_prob,
        pre_spread=pre_spread,
    )


def _score(*, lam: float = 1.0, model: FacepalmModel = _MODEL, **facts: Any) -> float | None:
    return facepalm_score(_facts(**facts), lam=lam, model=model)


def _phase_250_score(
    played_prob: float | None,
    spread: float | None,
    loss_3: int | None,
    mate_ply: int | None,
) -> float | None:
    """A frozen private copy of the Phase 250 formula under the frozen Phase 250 constants."""
    if played_prob is None or spread is None:
        return None
    if mate_ply is not None and mate_ply <= LINE_DEPTH:
        loss = float(MATE_LOSS)
    elif loss_3 is None:
        return None
    else:
        loss = float(max(min(loss_3, LOSS_CAP), PHASE_250_MODEL.loss_floor or 0))
    z = (
        PHASE_250_MODEL.intercept
        + PHASE_250_MODEL.played_coef * math.log(played_prob + PLAYED_PROB_OFFSET)
        + PHASE_250_MODEL.spread_coef * spread
        + PHASE_250_MODEL.loss_coef * loss
    )
    return 1.0 / (1.0 + math.exp(-z))


def _facts_of(row: GridRow) -> FacepalmFacts:
    """The Python twin's scalar facts of one parity-grid row (the arrays read at LINE_DEPTH)."""
    played_prob, spread, played_array, mate, best_array, best_mate, best_prob, pre_spread = row
    return FacepalmFacts(
        played_prob=played_prob,
        reply_spread=spread,
        played_3=material_at_depth(played_array, LINE_DEPTH),
        mate_ply=mate,
        best_3=material_at_depth(best_array, LINE_DEPTH),
        best_mate_ply=best_mate,
        best_prob=best_prob,
        pre_spread=pre_spread,
    )


def _grid() -> list[GridRow]:
    grid: list[GridRow] = list(
        itertools.product(
            _GRID_PLAYED_PROB,
            _GRID_SPREAD,
            _GRID_PLAYED_ARRAYS,
            _GRID_MATE,
            _GRID_BEST_ARRAYS,
            _GRID_BEST_MATE,
            (None, 0.2),
            (None, 3.0),
        )
    )
    return grid


_TYPING_ROW: GridRow = (0.5, 1.0, [0] * 9, 1, [0] * 9, 1, 0.5, 1.0)


async def _sql_scores(
    engine: AsyncEngine, grid: Sequence[GridRow], model: FacepalmModel, lam: float
) -> list[float | None]:
    """The SQL twin's score of every grid row, in grid order (chunked for the bind limit)."""
    scores: list[float | None] = []
    async with engine.connect() as conn:
        for start in range(0, len(grid), GRID_CHUNK_ROWS):
            # The typing row (dropped below) keeps every VALUES column non-NULL: PostgreSQL would
            # type a column of bare NULLs as text.
            chunk = [_TYPING_ROW, *grid[start : start + GRID_CHUNK_ROWS]]
            rows = values(
                column("idx", SmallInteger),
                column("played", Float),
                column("spread", Float),
                column("played_mat", ARRAY(SmallInteger)),
                column("mate", SmallInteger),
                column("best_mat", ARRAY(SmallInteger)),
                column("best_mate", SmallInteger),
                column("best_prob", Float),
                column("pre_spread", Float),
                name="grid",
            ).data([(i, *row) for i, row in enumerate(chunk)])
            expression = facepalm_score_sql(
                FacepalmColumns(
                    played_prob=rows.c.played,
                    reply_spread=rows.c.spread,
                    played_material=rows.c.played_mat,
                    mate_ply=rows.c.mate,
                    best_material=rows.c.best_mat,
                    best_mate_ply=rows.c.best_mate,
                    best_prob=rows.c.best_prob,
                    pre_spread=rows.c.pre_spread,
                ),
                lam=lam,
                model=model,
            )
            result = await conn.execute(select(rows.c.idx, expression).order_by(rows.c.idx))
            scores.extend(score for _, score in result.all()[1:])
    return scores


def _assert_parity(
    grid: Sequence[GridRow], sql_scores: Sequence[float | None], model: FacepalmModel, lam: float
) -> None:
    assert len(sql_scores) == len(grid)
    saw_none = saw_value = False
    for row, sql_score in zip(grid, sql_scores, strict=True):
        expected = facepalm_score(_facts_of(row), lam=lam, model=model)
        if expected is None:
            assert sql_score is None, row
            saw_none = True
        else:
            assert sql_score == pytest.approx(expected, abs=PARITY_TOLERANCE), row
            saw_value = True
    assert saw_none and saw_value


def test_formula_is_the_logistic_of_the_linear_predictor() -> None:
    z = 1.0 - 0.7 * math.log(0.1 + PLAYED_PROB_OFFSET) - 0.7 * 2.0 + 0.3 * 3
    assert _score() == pytest.approx(1 / (1 + math.exp(-z)), abs=FORMULA_TOLERANCE)


def test_missing_input_gives_none() -> None:
    assert _score(played_prob=None) is None
    assert _score(reply_spread=None) is None
    assert _score(played_3=None) is None
    assert _score(played_3=None, mate_ply=LINE_DEPTH + 1) is None


def test_mate_within_depth_settles_a_missing_loss() -> None:
    assert _score(played_3=None, mate_ply=2) is not None


def test_loss_is_capped() -> None:
    assert _score(played_3=-9) == _score(played_3=-LOSS_CAP)


def test_mate_loss_applies_within_line_depth_only() -> None:
    assert _score(played_3=0, mate_ply=LINE_DEPTH) == _score(played_3=-MATE_LOSS)
    assert _score(played_3=0, mate_ply=LINE_DEPTH + 1) == _score(played_3=0)


def test_loss_floor_clips_negative_losses_only_when_set() -> None:
    assert _score(played_3=3, model=_FLOORED_MODEL) == _score(played_3=0, model=_FLOORED_MODEL)
    assert _score(played_3=3) != _score(played_3=0)


def test_loss_feature_values() -> None:
    assert loss_feature(None, None, loss_floor=None) is None
    assert loss_feature(None, LINE_DEPTH + 1, loss_floor=None) is None
    assert loss_feature(None, 1, loss_floor=None) == MATE_LOSS
    assert loss_feature(-2, None, loss_floor=0) == 0
    assert loss_feature(-2, None, loss_floor=None) == -2


@pytest.mark.parametrize(
    ("played_3", "best_3", "expected"),
    [(-5, 0, 0.0), (5, 10, 5.0), (-5, 3, 3.0)],
    ids=["5_0_loss_only", "0_5_pure_miss", "5_3_mixed"],
)
def test_missed_feature_d05_table(played_3: int, best_3: int, expected: float) -> None:
    # D-05 table rows (loss / missed): 5/0, 0/5 and 5/3 for (played, best) = (-5, 0), (5, 10), (-5, 3).
    missed = missed_feature(
        played_3,
        best_3,
        None,
        missed_floor=None,
        missed_cap=LOSS_CAP,
        missed_mate=MISSED_MATE_VALUE,
    )
    assert missed == expected


def test_missed_feature_floor_cap_unknown_and_mate() -> None:
    kwargs: dict[str, Any] = {"missed_cap": LOSS_CAP, "missed_mate": MISSED_MATE_VALUE}
    # A negative raw gain (best line behind) is kept without a floor and raised to 0 with floor 0.
    assert missed_feature(5, 2, None, missed_floor=None, **kwargs) == -3.0
    assert missed_feature(5, 2, None, missed_floor=0, **kwargs) == 0.0
    # The cap applies to a big gain.
    assert missed_feature(0, 9, None, missed_floor=0, **kwargs) == float(LOSS_CAP)
    # D-18: an unknown best line contributes 0 (and so does an unknown played line).
    assert missed_feature(0, None, None, missed_floor=0, **kwargs) == 0.0
    assert missed_feature(None, 4, None, missed_floor=0, **kwargs) == 0.0
    # A best mate within LINE_DEPTH (ply 0 = the best move itself mates) counts the mate value,
    # even when the best line's material is unknown; a later mate does not.
    for mate_ply in (0, 2):
        assert missed_feature(0, None, mate_ply, missed_floor=0, **kwargs) == MISSED_MATE_VALUE
    assert missed_feature(0, 1, LINE_DEPTH + 1, missed_floor=0, **kwargs) == 1.0


def test_new_twin_reproduces_phase_250_score() -> None:
    # D-12: the frozen Phase 250 model equals the frozen Phase 250 formula for every lambda,
    # whatever the best-line facts say, because the missed term is not in that model. Pinned
    # explicitly: FACEPALM_MODEL is the Phase 254 refit now.
    grid = itertools.product(
        (0.0, 0.05, 0.3, None), (1.0, 4.4, None), (None, -3, 0, 2, 9), (None, 1, 3, 4)
    )
    compared = 0
    for played_prob, spread, loss_3, mate_ply in grid:
        expected = _phase_250_score(played_prob, spread, loss_3, mate_ply)
        for lam in LAMBDAS:
            facts = FacepalmFacts(
                played_prob=played_prob,
                reply_spread=spread,
                played_3=None if loss_3 is None else -loss_3,
                mate_ply=mate_ply,
                best_3=10,
                best_mate_ply=0,
            )
            actual = facepalm_score(facts, lam=lam, model=PHASE_250_MODEL)
            if expected is None:
                assert actual is None
            else:
                assert actual == pytest.approx(expected, abs=FORMULA_TOLERANCE)
                compared += 1
    assert compared > 0


@pytest.mark.parametrize("model", [_SPLIT_MODEL, _COMBINED_MODEL], ids=["split", "combined"])
def test_missed_term_lambda(model: FacepalmModel) -> None:
    loss_only = FacepalmModel(
        intercept=model.intercept,
        played_coef=model.played_coef,
        spread_coef=model.spread_coef,
        loss_coef=model.loss_coef,
        loss_floor=model.loss_floor,
    )
    pure_miss = {"played_3": 5, "best_3": 10}
    expected_loss_only = _score(model=loss_only, lam=1.0, **pure_miss)
    assert expected_loss_only is not None
    # lam 0 reproduces the loss-only score; the pure miss rises with lam.
    assert _score(model=model, lam=0.0, **pure_miss) == pytest.approx(
        expected_loss_only, abs=FORMULA_TOLERANCE
    )
    low = _score(model=model, lam=0.5, **pure_miss)
    high = _score(model=model, lam=1.0, **pure_miss)
    assert low is not None and high is not None
    assert expected_loss_only < low < high


def test_missed_term_is_unknown_best_line_neutral() -> None:
    # D-18: an unknown best line keeps the loss-only score, in both material forms.
    for model in (_SPLIT_MODEL, _COMBINED_MODEL):
        unknown = _score(model=model, lam=1.0, played_3=-3, best_3=None)
        known_zero = _score(model=model, lam=0.0, played_3=-3, best_3=None)
        assert unknown is not None
        assert unknown == known_zero


def test_lambda_out_of_range_raises() -> None:
    for bad in (FACEPALM_LAMBDA_MIN - 0.1, FACEPALM_LAMBDA_MAX + 0.1):
        with pytest.raises(ValueError):
            facepalm_score(_facts(), lam=bad)


def test_combined_form_requires_loss_floor_zero() -> None:
    with pytest.raises(ValueError):
        FacepalmModel(
            intercept=0.0,
            played_coef=0.0,
            spread_coef=0.0,
            loss_coef=1.0,
            loss_floor=None,
            material_form="combined",
        )
    with pytest.raises(ValueError):
        FacepalmModel(
            intercept=0.0,
            played_coef=0.0,
            spread_coef=0.0,
            loss_coef=1.0,
            loss_floor=None,
            missed_coef=0.5,
        )


# Extreme but realistic rows (a 200-move spread, mate in 1, a probability of 0) with the shipped
# model: PostgreSQL exp() errors on overflow, so a future refit with large coefficients that
# overflows here fails before deploy (T-254-03).
_EXTREME_ROWS: list[GridRow] = [
    (0.0, 200.0, _material_array(-9), 1, _material_array(10), 0, 0.0, 200.0),
    (1.0, 1.0, _material_array(9), None, _material_array(-9), None, 1.0, 1.0),
]


@pytest.mark.parametrize("model", _SHAPE_MODELS)
@pytest.mark.parametrize("lam", LAMBDAS)
async def test_sql_twin_parity_every_shape(
    test_engine: AsyncEngine, model: FacepalmModel, lam: float
) -> None:
    grid = [*_grid(), *_EXTREME_ROWS]
    _assert_parity(grid, await _sql_scores(test_engine, grid, model, lam), model, lam)


@pytest.mark.parametrize("model", [PHASE_250_MODEL, FACEPALM_MODEL, _SPLIT_MODEL, _COMBINED_MODEL])
async def test_zero_coefficient_input_never_unscores(
    test_engine: AsyncEngine, model: FacepalmModel
) -> None:
    # best_prob, pre_spread and the whole best line are NULL while their coefficients are 0.0
    # (or the best line is unknown, D-18): the row keeps a score in both twins.
    row: GridRow = (0.1, 2.0, _material_array(-3), None, None, None, None, None)
    python_score = facepalm_score(_facts_of(row), lam=1.0, model=model)
    assert python_score is not None
    (sql_score,) = await _sql_scores(test_engine, [row], model, 1.0)
    assert sql_score == pytest.approx(python_score, abs=PARITY_TOLERANCE)


@pytest.mark.parametrize("model", [_LOSS_ONLY_MODEL, _BEST_PROB_MISSES_MODEL])
async def test_gated_spread_null_with_zero_loss(
    test_engine: AsyncEngine, model: FacepalmModel
) -> None:
    # A pure miss (loss 0) never reads the spread, so a NULL spread must not unscore the row.
    row: GridRow = (0.1, None, _material_array(5), None, _material_array(10), None, 0.3, None)
    python_score = facepalm_score(_facts_of(row), lam=1.0, model=model)
    assert python_score is not None
    (sql_score,) = await _sql_scores(test_engine, [row], model, 1.0)
    assert sql_score == pytest.approx(python_score, abs=PARITY_TOLERANCE)
    # With a loss the gated spread is read, so a NULL spread unscores the row in both twins.
    lossy: GridRow = (0.1, None, _material_array(-3), None, _material_array(10), None, 0.3, None)
    assert facepalm_score(_facts_of(lossy), lam=1.0, model=model) is None
    assert (await _sql_scores(test_engine, [lossy], model, 1.0)) == [None]


def test_gated_spread_forms_value() -> None:
    # loss_only: spread only on a loss row; best_prob_for_misses: best-prob term on a pure miss.
    miss: dict[str, Any] = {"played_3": 5, "best_3": 10, "best_prob": 0.3}
    no_spread: dict[str, Any] = {**miss, "reply_spread": None}
    base = _score(model=_SPLIT_MODEL, **miss)
    gated = _score(model=_LOSS_ONLY_MODEL, **no_spread)
    with_best = _score(model=_BEST_PROB_MISSES_MODEL, **no_spread)
    plain = _score(model=replace(_BEST_PROB_MISSES_MODEL, best_prob_coef=0.0), **no_spread)
    assert base is not None and gated is not None and with_best is not None and plain is not None
    assert gated == plain
    z_gap = math.log(with_best / (1 - with_best)) - math.log(plain / (1 - plain))
    assert z_gap == pytest.approx(0.4 * math.log(0.3 + PLAYED_PROB_OFFSET), abs=FORMULA_TOLERANCE)


def test_unknown_best_prob_contributes_zero() -> None:
    # D-18 consistency: an unknown best-move probability adds nothing, whatever the coefficient.
    for model in (_ADDITIVE_BEST_PROB_MODEL, _BEST_PROB_MISSES_MODEL):
        zero_coef = replace(model, best_prob_coef=0.0)
        for played_3 in (-3, 5):
            with_coef = _score(model=model, played_3=played_3, best_3=10, best_prob=None)
            assert with_coef is not None
            assert with_coef == _score(
                model=zero_coef, played_3=played_3, best_3=10, best_prob=None
            )


def test_additive_optional_inputs_enter_the_linear_predictor() -> None:
    facts: dict[str, Any] = {"played_3": -3, "best_3": 4, "best_prob": 0.3, "pre_spread": 5.0}
    base = _score(model=_SPLIT_MODEL, **facts)
    best_prob = _score(model=_ADDITIVE_BEST_PROB_MODEL, **facts)
    pre_spread = _score(model=_ADDITIVE_PRE_SPREAD_MODEL, **facts)
    assert base is not None and best_prob is not None and pre_spread is not None

    def z_gap(score: float) -> float:
        return math.log(score / (1 - score)) - math.log(base / (1 - base))

    assert z_gap(best_prob) == pytest.approx(
        0.4 * math.log(0.3 + PLAYED_PROB_OFFSET), abs=FORMULA_TOLERANCE
    )
    assert z_gap(pre_spread) == pytest.approx(-0.2 * 5.0, abs=FORMULA_TOLERANCE)


def test_sql_lambda_out_of_range_raises() -> None:
    columns = FacepalmColumns(*([column("x")] * len(FacepalmColumns._fields)))
    for bad in (FACEPALM_LAMBDA_MIN - 0.1, FACEPALM_LAMBDA_MAX + 0.1):
        with pytest.raises(ValueError):
            facepalm_score_sql(columns, lam=bad)


@pytest.mark.parametrize("model", _MATERIAL_MODELS)
@pytest.mark.parametrize("lam", LAMBDAS)
async def test_sql_twin_parity_material_forms(
    test_engine: AsyncEngine, model: FacepalmModel, lam: float
) -> None:
    grid = _grid()
    _assert_parity(grid, await _sql_scores(test_engine, grid, model, lam), model, lam)


@pytest.mark.parametrize("move_count", UNIFORM_MOVE_COUNTS)
def test_reply_spread_of_uniform_policy_is_the_move_count(move_count: int) -> None:
    policy = {f"m{i}": 1.0 / move_count for i in range(move_count)}
    assert reply_spread(policy) == pytest.approx(move_count, abs=PARITY_TOLERANCE)


def test_reply_spread_equals_phase_247_effective_moves() -> None:
    policy = fake_full_policy(chess.STARTING_FEN, 1500.0)
    assert reply_spread(policy) == _effective_moves(policy)


def test_known_d04_constants() -> None:
    assert (FACEPALM_SCORE_MIN, PLAYED_PROB_OFFSET, LINE_DEPTH, LOSS_CAP, MATE_LOSS) == (
        0.5,
        0.01,
        3,
        5,
        5,
    )
    assert LINE_DEPTH in LINE_LOSS_DEPTHS


def test_lambda_constants_are_separate_and_in_range() -> None:
    # D-03 / D-04: two named constants (equal today, free to diverge), both inside the range.
    assert FACEPALM_DRILL_LAMBDA == 1.0
    assert FACEPALM_LIBRARY_LAMBDA == 1.0
    assert FACEPALM_LAMBDA_MIN <= FACEPALM_DRILL_LAMBDA <= FACEPALM_LAMBDA_MAX
    assert FACEPALM_LAMBDA_MIN <= FACEPALM_LIBRARY_LAMBDA <= FACEPALM_LAMBDA_MAX


def test_default_model_is_built_from_the_fitted_constants() -> None:
    assert FACEPALM_MODEL == FacepalmModel(
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
    facts = _facts(played_3=-3)
    default = facepalm_score(facts, lam=FACEPALM_DRILL_LAMBDA)
    explicit = facepalm_score(facts, lam=FACEPALM_DRILL_LAMBDA, model=FACEPALM_MODEL)
    assert default is not None
    assert default == explicit


def test_window_14_constants_match_the_committed_features_row() -> None:
    with _FEATURES_TSV.open() as handle:
        rows = [
            row
            for row in csv.DictReader(handle, delimiter="\t")
            if row["game_id"] == str(WINDOW_14_GAME_ID) and row["ply"] == str(WINDOW_14_PLY)
        ]
    assert len(rows) == 1
    row = rows[0]
    assert row["n"] == "extra"
    assert float(row["played_prob"]) == WINDOW_14_PLAYED_PROB
    assert float(row["reply_spread"]) == WINDOW_14_REPLY_SPREAD
    assert float(row["best_prob"]) == WINDOW_14_BEST_PROB
    assert int(row["best_mat_3"]) == WINDOW_14_BEST_3
    assert (row["played_mat_3"] or None) == WINDOW_14_PLAYED_3
    assert (row["line_mate_ply"] or None) == WINDOW_14_MATE_PLY


def test_window_14_is_not_selected_by_the_shipped_model() -> None:
    # CONTEXT specifics: Window 14 must not pass FACEPALM_SCORE_MIN. Its stored line is only one
    # ply long, so the played depth-3 material is unknown and the score is None: a NULL score
    # fails the `score >= FACEPALM_SCORE_MIN` filter in SQL and in the pure judge, so an unscored
    # row never qualifies. Deliberately no numeric "below the cut" claim: the score cannot be
    # computed from the recorded inputs.
    score = facepalm_score(
        _facts(
            played_prob=WINDOW_14_PLAYED_PROB,
            reply_spread=WINDOW_14_REPLY_SPREAD,
            played_3=WINDOW_14_PLAYED_3,
            mate_ply=WINDOW_14_MATE_PLY,
            best_3=WINDOW_14_BEST_3,
            best_prob=WINDOW_14_BEST_PROB,
        ),
        lam=FACEPALM_DRILL_LAMBDA,
    )
    assert score is None


# ---------------------------------------------------------------------------
# facepalm_expr over stored game_flaws facts and the stored-array shape CHECKs (D-01, D-09)
# ---------------------------------------------------------------------------

_BEST_MATE_AT_PLY_0 = 0
# One row of facts per seeded flaw: arrays with NULL even slots (D-17), a NULL best array (D-18),
# a best line that mates at ply 0, a played-line mate, a NULL played probability.
_STORED_FACT_ROWS: tuple[dict[str, Any], ...] = (
    {
        "maia_played_prob": 0.05,
        "maia_reply_spread": 3.0,
        "played_line_material": [0, None, -5, None, -5, None, -5, None, -5],
        "best_line_material": [0, None, 4, None, 4, None, 4, None, 4],
    },
    {
        "maia_played_prob": 0.4,
        "maia_reply_spread": 1.5,
        "played_line_material": [0, None, 2, None, 2, None, 2, None, 2],
        "best_line_material": None,
    },
    {
        "maia_played_prob": 0.02,
        "maia_reply_spread": 8.0,
        "played_line_material": [0, 0, 0, 0, 0, 0, 0, 0, 0],
        "best_line_material": [0, 0, 1, 0, 0, 0, 0, 0, 0],
        "best_line_mate_ply": _BEST_MATE_AT_PLY_0,
        "maia_best_prob": 0.3,
        "maia_pre_spread": 6.0,
    },
    {
        "maia_played_prob": 0.1,
        "maia_reply_spread": 2.0,
        "played_line_material": [-1, -3, -9, -9, -9, -9, -9, -9, -9],
        "line_mate_ply": 2,
        "best_line_material": [0, 0, 3, 0, 3, 0, 3, 0, 3],
    },
    {
        "maia_played_prob": None,
        "maia_reply_spread": 2.0,
        "played_line_material": [0, 0, -3, 0, -3, 0, -3, 0, -3],
    },
    {
        "maia_played_prob": 0.3,
        "maia_reply_spread": 4.0,
        "played_line_material": None,
    },
)


async def _seed_stored_facts(session: AsyncSession, fact_rows: Sequence[dict[str, Any]]) -> int:
    return await seed_flaw_rows(session, fact_rows, user_id=STORED_FACTS_USER_ID)


def _facts_of_flaw(flaw: GameFlaw) -> FacepalmFacts:
    return FacepalmFacts(
        played_prob=flaw.maia_played_prob,
        reply_spread=flaw.maia_reply_spread,
        played_3=material_at_depth(flaw.played_line_material, LINE_DEPTH),
        mate_ply=flaw.line_mate_ply,
        best_3=material_at_depth(flaw.best_line_material, LINE_DEPTH),
        best_mate_ply=flaw.best_line_mate_ply,
        best_prob=flaw.maia_best_prob,
        pre_spread=flaw.maia_pre_spread,
    )


@pytest.mark.parametrize("lam", (0.0, 1.0))
@pytest.mark.parametrize(
    "model",
    [PHASE_250_MODEL, FACEPALM_MODEL, _SPLIT_MODEL, _COMBINED_MODEL, _BEST_PROB_MISSES_MODEL],
    ids=["pre_refit", "shipped", "split_missed", "combined", "best_prob_misses"],
)
async def test_expr_matches_python_twin_over_stored_facts(
    db_session: AsyncSession, model: FacepalmModel, lam: float
) -> None:
    game_id = await _seed_stored_facts(db_session, _STORED_FACT_ROWS)
    flaws = (
        (await db_session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
        .scalars()
        .all()
    )
    score_rows = await db_session.execute(
        select(GameFlaw.ply, facepalm_expr(lam, model)).where(GameFlaw.game_id == game_id)
    )
    scores: dict[int, float | None] = {ply: score for ply, score in score_rows.all()}
    assert len(flaws) == len(_STORED_FACT_ROWS)
    saw_none = saw_value = False
    for flaw in flaws:
        expected = facepalm_score(_facts_of_flaw(flaw), lam=lam, model=model)
        if expected is None:
            assert scores[flaw.ply] is None, flaw.ply
            saw_none = True
        else:
            assert scores[flaw.ply] == pytest.approx(expected, abs=PARITY_TOLERANCE), flaw.ply
            saw_value = True
    assert saw_none and saw_value


async def test_expr_reads_the_missed_term_from_the_stored_best_array(
    db_session: AsyncSession,
) -> None:
    # Row 0 misses a +4 gain: the split model scores it higher at lam 1 than at lam 0; a row
    # with no best array (row 1) is unchanged by lam (D-18).
    game_id = await _seed_stored_facts(db_session, _STORED_FACT_ROWS)

    async def _scores(lam: float) -> dict[int, float | None]:
        result = await db_session.execute(
            select(GameFlaw.ply, facepalm_expr(lam, _SPLIT_MODEL)).where(
                GameFlaw.game_id == game_id
            )
        )
        return {ply: score for ply, score in result.all()}

    at_zero, at_one = await _scores(0.0), await _scores(1.0)
    assert at_zero[0] is not None and at_one[0] is not None and at_one[0] > at_zero[0]
    assert at_zero[1] == pytest.approx(at_one[1], abs=PARITY_TOLERANCE)


_NINE_SLOTS = "{0,0,0,0,0,0,0,0,0}"
_BAD_ARRAY_LITERALS = {
    "empty": "'{}'::smallint[]",
    "three_slots": "'{1,2,3}'::smallint[]",
    "offset_lower_bound": f"'[0:8]={_NINE_SLOTS}'::smallint[]",
    "two_dimensional": "'{{1,2,3},{4,5,6},{7,8,9}}'::smallint[]",
}
_GOOD_ARRAY_LITERALS = {
    "null": "NULL::smallint[]",
    "nine_slots": f"'{_NINE_SLOTS}'::smallint[]",
    "null_even_slots": "'{0,NULL,1,NULL,1,NULL,1,NULL,1}'::smallint[]",
}
_SHAPE_COLUMNS = ("played_line_material", "best_line_material")


async def _set_array(session: AsyncSession, game_id: int, column_name: str, literal: str) -> None:
    # column_name and literal come from the constants above, never from input.
    await session.execute(
        text(f"UPDATE game_flaws SET {column_name} = {literal} WHERE game_id = :g AND ply = 0"),
        {"g": game_id},
    )


@pytest.mark.parametrize("column_name", _SHAPE_COLUMNS)
@pytest.mark.parametrize("shape", list(_BAD_ARRAY_LITERALS))
async def test_shape_check_rejects_malformed_arrays(
    db_session: AsyncSession, column_name: str, shape: str
) -> None:
    game_id = await _seed_stored_facts(db_session, _STORED_FACT_ROWS[:1])
    with pytest.raises(IntegrityError, match=f"ck_game_flaws_{column_name}_shape"):
        async with db_session.begin_nested():
            await _set_array(db_session, game_id, column_name, _BAD_ARRAY_LITERALS[shape])


@pytest.mark.parametrize("column_name", _SHAPE_COLUMNS)
@pytest.mark.parametrize("shape", list(_GOOD_ARRAY_LITERALS))
async def test_shape_check_accepts_null_and_nine_slot_arrays(
    db_session: AsyncSession, column_name: str, shape: str
) -> None:
    game_id = await _seed_stored_facts(db_session, _STORED_FACT_ROWS[:1])
    await _set_array(db_session, game_id, column_name, _GOOD_ARRAY_LITERALS[shape])
