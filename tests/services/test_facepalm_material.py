"""Tests for app/services/facepalm_material.py and the material inputs of the score (Phase 256).

Coverage:
- weights   : the decay weights derive from MATERIAL_DECAY_RATIO over the odd depths
- series    : loss_by_depth / gain_by_depth read odd slots only, cap, floor and handle short arrays
- mean      : decaying_mean renormalises over the known depths (the CONTEXT early-swing row)
- stable    : first_stable (256 D-06, A1): the first confirmed odd-depth value, discounted by its onset
- mates     : a mate within LINE_DEPTH short-circuits both inputs (A2), a later mate enters per depth
- coverage  : D-03, every material input leaves a row without a depth-3 slot unscored
- gate      : D-11, `loses` and its SQL twin at gate None and 1.0
- single    : single_depth_material scores like the depth-3 scalar under every input
The SQL builders are pinned against these functions in tests/services/test_facepalm_score.py.
"""

from __future__ import annotations

from typing import get_args

import pytest
from sqlalchemy import SmallInteger, column
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY

from app.services.blunder_check_rules import (
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    MATERIAL_DECAY_RATIO,
    MaterialInput,
)
from app.services.facepalm_material import (
    MATERIAL_DECAY_WEIGHTS,
    MATERIAL_DEPTHS,
    decaying_mean,
    decaying_mean_sql,
    first_stable,
    first_stable_sql,
    gain_by_depth,
    gain_by_depth_sql,
    loses,
    loses_sql,
    loss_by_depth,
    loss_by_depth_sql,
    single_depth_material,
)
from app.services.facepalm_score import material_loss, material_missed

MISSED_MATE_VALUE = 7
DECAY_WEIGHT_SUM = 1.9375  # 1 + 1/2 + 1/4 + 1/8 + 1/16
GARBAGE = 99  # filler for the even slots: they must never change a result
ALL_INPUTS = get_args(MaterialInput)


def array(*odd: int | None) -> list[int | None]:
    """A 9-slot material array from the five odd-depth values; even slots hold garbage."""
    slots: list[int | None] = []
    for index, value in enumerate(odd):
        slots.append(value)
        if index < len(odd) - 1:
            slots.append(GARBAGE)
    return slots


def _loss(
    played: list[int | None] | None,
    mate_ply: int | None,
    material_input: MaterialInput,
    loss_floor: int | None = 0,
) -> float | None:
    return material_loss(played, mate_ply, material_input=material_input, loss_floor=loss_floor)


def _missed(
    played: list[int | None] | None,
    best: list[int | None] | None,
    best_mate_ply: int | None,
    material_input: MaterialInput,
    missed_floor: int | None = 0,
) -> float:
    return material_missed(
        played,
        best,
        best_mate_ply,
        material_input=material_input,
        missed_floor=missed_floor,
        missed_cap=LOSS_CAP,
        missed_mate=MISSED_MATE_VALUE,
    )


def test_weights_derive_from_the_ratio() -> None:
    assert MATERIAL_DEPTHS == (1, 3, 5, 7, 9)
    assert MATERIAL_DECAY_RATIO == 0.5
    assert MATERIAL_DECAY_WEIGHTS == (1.0, 0.5, 0.25, 0.125, 0.0625)


def test_decaying_mean_normalises_over_known_depths() -> None:
    # The CONTEXT early-swing row: a loss of 3 at depths 1 and 3, then level.
    assert decaying_mean((3, 3, 0, 0, 0)) == (3 + 1.5) / DECAY_WEIGHT_SUM
    assert decaying_mean((4, 4, 4, 4, 4)) == 4.0
    assert decaying_mean((2, 4, None, None, None)) == (2 + 0.5 * 4) / 1.5
    assert decaying_mean((None, None, None, None, None)) is None


def test_first_stable_values() -> None:
    # A1: the first odd-depth pair with equal known values, discounted by its onset index.
    assert first_stable((3, 3, 0, 0, 0)) == 3.0
    assert first_stable((0, 3, 3, 3, 3)) == 3 * 0.5
    # No stable pair: the last known value, discounted by its own index.
    assert first_stable((1, 2, 3, 4, 5)) == 5 * 0.0625
    assert first_stable((None, None, 2, None, None)) == 2 * 0.25
    assert first_stable((None, None, None, None, None)) is None
    # A None next to a value never forms a stable pair.
    assert first_stable((2, None, 2, 2, None)) == 2 * 0.25
    assert first_stable((2, None, 2, None, None)) == 2 * 0.25


def test_first_stable_sql_is_one_scalar_expression() -> None:
    played = column("played", ARRAY(SmallInteger))
    mate = column("mate", SmallInteger)
    expression = first_stable_sql(loss_by_depth_sql(played, mate, loss_floor=0))
    compiled = str(expression.compile(dialect=postgresql.dialect())).lower()
    assert "unnest" not in compiled
    assert "select" not in compiled


def test_loss_series_reads_odd_slots_caps_and_floors() -> None:
    assert loss_by_depth(array(-3, 0, 0, 0, 0), None, loss_floor=0) == (3.0, 0.0, 0.0, 0.0, 0.0)
    assert loss_by_depth(array(-9, -9, -9, -9, -9), None, loss_floor=0) == (float(LOSS_CAP),) * 5
    # Without a floor a gain of the blunderer is a negative loss; with floor 0 it is raised to 0.
    assert loss_by_depth(array(2, 2, 2, 2, 2), None, loss_floor=None) == (-2.0,) * 5
    assert loss_by_depth(array(2, 2, 2, 2, 2), None, loss_floor=0) == (0.0,) * 5


def test_loss_series_of_a_short_array_knows_only_the_first_depths() -> None:
    # A 3-slot array settles depths 1 and 3; the garbage in slot 2 is never read.
    short: list[int | None] = [-1, GARBAGE, -2]
    series = loss_by_depth(short, None, loss_floor=0)
    assert series == (1.0, 2.0, None, None, None)
    assert decaying_mean(series) == (1 + 0.5 * 2) / 1.5
    assert loss_by_depth(None, None, loss_floor=0) == (None,) * 5


def test_gain_series_of_the_seed_queen_trade() -> None:
    # The seed example: the best line is level but for a transient queen at depth 5 (the gain is
    # capped at 5), the played line is level throughout.
    best: list[int | None] = [1, 1, 1, 1, 10, 10, 1, 1, 1]
    played: list[int | None] = [0] * 9
    series = gain_by_depth(
        played, best, None, missed_floor=0, missed_cap=LOSS_CAP, missed_mate=MISSED_MATE_VALUE
    )
    assert series == (1.0, 1.0, 5.0, 1.0, 1.0)
    assert decaying_mean(series) == (1 + 0.5 + 0.25 * 5 + 0.125 + 0.0625) / DECAY_WEIGHT_SUM


def test_gain_series_floor_and_unknown_slots() -> None:
    kwargs = {"missed_cap": LOSS_CAP, "missed_mate": MISSED_MATE_VALUE}
    played = array(5, 5, 5, 5, 5)
    best = array(2, 2, 2, 2, 2)
    # The best line is behind: negative raw gain without a floor, 0 with floor 0.
    assert gain_by_depth(played, best, None, missed_floor=None, **kwargs) == (-3.0,) * 5
    assert gain_by_depth(played, best, None, missed_floor=0, **kwargs) == (0.0,) * 5
    # An unknown slot on either side leaves that depth unknown.
    short_best: list[int | None] = [4]
    series = gain_by_depth(played, short_best, None, missed_floor=0, **kwargs)
    assert series == (0.0, None, None, None, None)
    assert gain_by_depth(None, best, None, missed_floor=0, **kwargs) == (None,) * 5


def test_played_mate_short_circuits_within_line_depth() -> None:
    level = array(0, 0, 0, 0, 0)
    for material_input in ALL_INPUTS:
        # Mate at ply 3 settles the loss at MATE_LOSS, not an average of the arrays (A2).
        assert _loss(level, LINE_DEPTH, material_input) == float(MATE_LOSS)
        assert _loss(level, 1, material_input) == float(MATE_LOSS)
        # ... even when the array is unknown.
        assert _loss(None, LINE_DEPTH, material_input) == float(MATE_LOSS)


def test_played_mate_beyond_line_depth_enters_per_depth() -> None:
    level = array(0, 0, 0, 0, 0)
    series = loss_by_depth(level, 5, loss_floor=0)
    assert series == (0.0, 0.0, float(MATE_LOSS), float(MATE_LOSS), float(MATE_LOSS))
    assert _loss(level, 5, "decaying_mean") == (5 * (0.25 + 0.125 + 0.0625)) / DECAY_WEIGHT_SUM
    # depth_3 does not look beyond LINE_DEPTH.
    assert _loss(level, 5, "depth_3") == 0.0


def test_best_mate_short_circuits_within_line_depth() -> None:
    level = array(0, 0, 0, 0, 0)
    best = array(1, 1, 1, 1, 1)
    for material_input in ALL_INPUTS:
        for mate_ply in (0, 2):
            assert _missed(level, best, mate_ply, material_input) == MISSED_MATE_VALUE
            # even with no best line at all
            assert _missed(level, None, mate_ply, material_input) == MISSED_MATE_VALUE


def test_best_mate_beyond_line_depth_enters_per_depth() -> None:
    level = array(0, 0, 0, 0, 0)
    best = array(1, 1, 1, 1, 1)
    kwargs = {"missed_cap": LOSS_CAP, "missed_mate": MISSED_MATE_VALUE}
    series = gain_by_depth(level, best, 4, missed_floor=0, **kwargs)
    assert series == (1.0, 1.0, 7.0, 7.0, 7.0)
    expected = (1 + 0.5 + 7 * (0.25 + 0.125 + 0.0625)) / DECAY_WEIGHT_SUM
    assert _missed(level, best, 4, "decaying_mean") == expected
    assert _missed(level, best, 4, "depth_3") == 1.0


@pytest.mark.parametrize("material_input", ALL_INPUTS)
def test_coverage_requires_depth_3_for_every_input(material_input: MaterialInput) -> None:
    # D-03: no depth-3 slot and no mate within LINE_DEPTH leaves the row unscored, whatever the
    # other depths know; a mate within LINE_DEPTH settles it.
    no_depth_3: list[int | None] = [0, GARBAGE, None, GARBAGE, -3, GARBAGE, -3, GARBAGE, -3]
    short: list[int | None] = [0, GARBAGE]
    for played in (None, short, no_depth_3):
        assert _loss(played, None, material_input) is None
        assert _loss(played, LINE_DEPTH + 1, material_input) is None
        assert _loss(played, LINE_DEPTH, material_input) == float(MATE_LOSS)
    # The missed term of such a row is 0 (D-18), under every input.
    best = array(4, 4, 4, 4, 4)
    for played in (None, short, no_depth_3):
        assert _missed(played, best, None, material_input) == 0.0


@pytest.mark.parametrize("material_input", ALL_INPUTS)
def test_single_depth_material_scores_like_the_depth_3_scalar(
    material_input: MaterialInput,
) -> None:
    played = single_depth_material(-3)
    best = single_depth_material(4)
    assert played == (None, None, -3, None, None, None, None, None, None)
    # first_stable has no stable pair on a lone depth-3 slot, so it discounts that slot by its
    # onset index (depth 3 is index 1, weight 1/2); the other inputs read it as it is.
    discount = MATERIAL_DECAY_WEIGHTS[1] if material_input == "first_stable" else 1.0
    assert _loss(list(played), None, material_input) == 3.0 * discount
    assert _missed(list(played), list(best), None, material_input) == 4.0 * discount
    assert _loss(list(single_depth_material(None)), None, material_input) is None
    assert single_depth_material(5, depth=1)[0] == 5


def test_loses_is_the_gate_function() -> None:
    assert loses(0.5, None) is True
    assert loses(0.0, None) is False
    assert loses(-1.0, None) is False
    assert loses(0.5, 1.0) is False
    assert loses(1.0, 1.0) is True
    assert loses(2.0, 1.0) is True


def test_loss_gate_none_counts_any_positive_loss() -> None:
    # A decaying-mean loss of about 0.52 (one pawn at depth 1 only) loses under gate None.
    half = _loss(array(-1, 0, 0, 0, 0), None, "decaying_mean")
    assert half is not None and 0.0 < half < 1.0
    assert loses(half, None) is True


def test_loss_gate_one_needs_a_loss_of_at_least_one() -> None:
    half = _loss(array(-1, 0, 0, 0, 0), None, "decaying_mean")
    assert half is not None
    assert loses(half, 1.0) is False
    # A constant one-pawn loss averages exactly 1.0 and is losing under both gates (A4: `>=`).
    constant = _loss(array(-1, -1, -1, -1, -1), None, "decaying_mean")
    assert constant is not None and constant == 1.0
    assert loses(constant, None) is True
    assert loses(constant, 1.0) is True


def test_loss_gate_sql_twin_compiles_both_comparisons() -> None:
    mate = column("mate", SmallInteger)
    assert " > " in str(loses_sql(mate, None).compile(dialect=postgresql.dialect()))
    assert " >= " in str(loses_sql(mate, 1.0).compile(dialect=postgresql.dialect()))


def test_sql_builders_are_unrolled_scalar_expressions() -> None:
    # T-256-03: no unnest and no subquery, so readers bind the expression once per query.
    played = column("played", ARRAY(SmallInteger))
    best = column("best", ARRAY(SmallInteger))
    mate = column("mate", SmallInteger)
    series = loss_by_depth_sql(played, mate, loss_floor=0)
    gains = gain_by_depth_sql(
        played, best, mate, missed_floor=0, missed_cap=LOSS_CAP, missed_mate=MISSED_MATE_VALUE
    )
    assert len(series) == len(gains) == len(MATERIAL_DEPTHS)
    expressions = (
        decaying_mean_sql(series),
        decaying_mean_sql(gains),
        loses_sql(series[0], None),
        loses_sql(series[0], 1.0),
    )
    for expression in expressions:
        compiled = str(expression.compile(dialect=postgresql.dialect())).lower()
        assert "unnest" not in compiled
        assert "select" not in compiled
