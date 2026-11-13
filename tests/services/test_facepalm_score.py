"""Tests for app/services/facepalm_score.py, the D-04 constants and reply_spread (Phase 250).

Coverage:
- formula   : facepalm_score equals the logistic of the linear predictor
- nulls     : a missing played probability, spread or (unsettled) loss gives None; a mate
              settles a missing depth-3 loss
- loss      : the cap at LOSS_CAP, MATE_LOSS inside LINE_DEPTH only, the optional loss floor
- sql twin  : facepalm_score_sql agrees with the Python function on a grid that includes
              NULLs in every input position, for both floor variants
- spread    : reply_spread of a uniform policy over k moves is k and equals the Phase 247
              effective-moves value on a real position's fake policy
- constants : the known D-04 values and LINE_DEPTH being a stored depth
"""

from __future__ import annotations

import csv
import itertools
import math
from pathlib import Path

import chess
import pytest
from sqlalchemy import Float, SmallInteger, column, select, values
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services.blunder_check_rules import (
    FACEPALM_INTERCEPT,
    FACEPALM_LOSS_COEF,
    FACEPALM_LOSS_FLOOR,
    FACEPALM_PLAYED_COEF,
    FACEPALM_SCORE_MIN,
    FACEPALM_SPREAD_COEF,
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    PLAYED_PROB_OFFSET,
)
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmModel,
    facepalm_score,
    facepalm_score_sql,
    loss_feature,
)
from app.services.line_material import LINE_LOSS_DEPTHS
from app.services.maia_flaw_stats import _effective_moves, reply_spread
from tests.services.maia_fakes import fake_full_policy

FORMULA_TOLERANCE = 1e-12
PARITY_TOLERANCE = 1e-9
UNIFORM_MOVE_COUNTS = (1, 2, 5, 30)

_MODEL = FacepalmModel(
    intercept=1.0, played_coef=-0.7, spread_coef=-0.7, loss_coef=0.3, loss_floor=None
)
_FLOORED_MODEL = FacepalmModel(
    intercept=1.0, played_coef=-0.7, spread_coef=-0.7, loss_coef=0.3, loss_floor=0
)

# Window 14 (game 2099808, ply 23), copied from the extra row of the committed features file
# reports/blunder-check/facepalm-features-2026-11-13.tsv. Its stored refutation line is one ply
# long (pv_plies 1, line_loss_1 -1), so the depth-3 loss and the mate ply are NULL there.
WINDOW_14_GAME_ID = 2099808
WINDOW_14_PLY = 23
WINDOW_14_PLAYED_PROB = 0.0949175
WINDOW_14_REPLY_SPREAD = 7.75985
WINDOW_14_LINE_LOSS_3: int | None = None
WINDOW_14_MATE_PLY: int | None = None
_FEATURES_TSV = (
    Path(__file__).resolve().parents[2]
    / "reports"
    / "blunder-check"
    / "facepalm-features-2026-11-13.tsv"
)

_GRID_PLAYED = (0.0, 0.05, 0.3, None)
_GRID_SPREAD = (1.0, 4.4, None)
_GRID_LOSS_3 = (None, -3, 0, 2, 9)
_GRID_MATE = (None, 1, 3, 4)


def _score(
    *,
    played_prob: float | None = 0.1,
    reply_spread: float | None = 2.0,
    loss_3: int | None = 3,
    mate_ply: int | None = None,
    model: FacepalmModel = _MODEL,
) -> float | None:
    return facepalm_score(
        played_prob=played_prob,
        reply_spread=reply_spread,
        loss_3=loss_3,
        mate_ply=mate_ply,
        model=model,
    )


def test_formula_is_the_logistic_of_the_linear_predictor() -> None:
    z = 1.0 - 0.7 * math.log(0.1 + PLAYED_PROB_OFFSET) - 0.7 * 2.0 + 0.3 * 3
    assert _score() == pytest.approx(1 / (1 + math.exp(-z)), abs=FORMULA_TOLERANCE)


def test_missing_input_gives_none() -> None:
    assert _score(played_prob=None) is None
    assert _score(reply_spread=None) is None
    assert _score(loss_3=None) is None
    assert _score(loss_3=None, mate_ply=LINE_DEPTH + 1) is None


def test_mate_within_depth_settles_a_missing_loss() -> None:
    assert _score(loss_3=None, mate_ply=2) is not None


def test_loss_is_capped() -> None:
    assert _score(loss_3=9) == _score(loss_3=LOSS_CAP)


def test_mate_loss_applies_within_line_depth_only() -> None:
    assert _score(loss_3=0, mate_ply=LINE_DEPTH) == _score(loss_3=MATE_LOSS)
    assert _score(loss_3=0, mate_ply=LINE_DEPTH + 1) == _score(loss_3=0)


def test_loss_floor_clips_negative_losses_only_when_set() -> None:
    assert _score(loss_3=-3, model=_FLOORED_MODEL) == _score(loss_3=0, model=_FLOORED_MODEL)
    assert _score(loss_3=-3) != _score(loss_3=0)


def test_loss_feature_values() -> None:
    assert loss_feature(None, None, loss_floor=None) is None
    assert loss_feature(None, LINE_DEPTH + 1, loss_floor=None) is None
    assert loss_feature(None, 1, loss_floor=None) == MATE_LOSS
    assert loss_feature(-2, None, loss_floor=0) == 0
    assert loss_feature(-2, None, loss_floor=None) == -2


@pytest.mark.parametrize(
    "model", [_MODEL, _FLOORED_MODEL, None], ids=["no_floor", "floor_0", "default_model"]
)
async def test_sql_twin_matches_python(
    test_engine: AsyncEngine, model: FacepalmModel | None
) -> None:
    # model=None exercises the default of both twins (FACEPALM_MODEL), the shipped fit.
    kwargs = {} if model is None else {"model": model}
    grid = list(itertools.product(_GRID_PLAYED, _GRID_SPREAD, _GRID_LOSS_3, _GRID_MATE))
    rows = values(
        column("played", Float),
        column("spread", Float),
        column("loss3", SmallInteger),
        column("mate", SmallInteger),
        name="grid",
    ).data(grid)
    expression = facepalm_score_sql(
        rows.c.played, rows.c.spread, rows.c.loss3, rows.c.mate, **kwargs
    )
    async with test_engine.connect() as conn:
        result = await conn.execute(
            select(rows.c.played, rows.c.spread, rows.c.loss3, rows.c.mate, expression)
        )
        fetched = result.all()
    assert len(fetched) == len(grid)
    saw_none = saw_value = False
    for played, spread, loss3, mate, sql_score in fetched:
        expected = facepalm_score(
            played_prob=played, reply_spread=spread, loss_3=loss3, mate_ply=mate, **kwargs
        )
        if expected is None:
            assert sql_score is None, (played, spread, loss3, mate)
            saw_none = True
        else:
            assert sql_score == pytest.approx(expected, abs=PARITY_TOLERANCE), (
                played,
                spread,
                loss3,
                mate,
            )
            saw_value = True
    assert saw_none and saw_value


@pytest.mark.parametrize("move_count", UNIFORM_MOVE_COUNTS)
def test_reply_spread_of_uniform_policy_is_the_move_count(move_count: int) -> None:
    policy = {f"m{i}": 1.0 / move_count for i in range(move_count)}
    assert reply_spread(policy) == pytest.approx(move_count, abs=PARITY_TOLERANCE)


def test_reply_spread_equals_phase_247_effective_moves() -> None:
    policy = fake_full_policy(chess.STARTING_FEN, 1500.0)
    assert reply_spread(policy) == _effective_moves(policy)


def test_known_d04_constants() -> None:
    assert (FACEPALM_SCORE_MIN, PLAYED_PROB_OFFSET, LINE_DEPTH, LOSS_CAP, MATE_LOSS) == (
        0.7,
        0.01,
        3,
        5,
        5,
    )
    assert LINE_DEPTH in LINE_LOSS_DEPTHS


def test_default_model_is_built_from_the_fitted_constants() -> None:
    assert FACEPALM_MODEL == FacepalmModel(
        intercept=FACEPALM_INTERCEPT,
        played_coef=FACEPALM_PLAYED_COEF,
        spread_coef=FACEPALM_SPREAD_COEF,
        loss_coef=FACEPALM_LOSS_COEF,
        loss_floor=FACEPALM_LOSS_FLOOR,
    )
    default = facepalm_score(played_prob=0.1, reply_spread=2.0, loss_3=3, mate_ply=None)
    explicit = facepalm_score(
        played_prob=0.1, reply_spread=2.0, loss_3=3, mate_ply=None, model=FACEPALM_MODEL
    )
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
    assert float(row["played_prob"]) == WINDOW_14_PLAYED_PROB
    assert float(row["reply_spread"]) == WINDOW_14_REPLY_SPREAD
    assert (row["line_loss_3"] or None) == WINDOW_14_LINE_LOSS_3
    assert (row["line_mate_ply"] or None) == WINDOW_14_MATE_PLY


def test_window_14_is_not_selected_by_the_shipped_model() -> None:
    # CONTEXT specifics: Window 14 must not pass FACEPALM_SCORE_MIN. Its stored line is only one
    # ply long, so the loss input is unknown and the score is None: a NULL score fails the
    # `score >= FACEPALM_SCORE_MIN` filter in SQL and in the pure judge, so it is not selected,
    # but the score itself cannot be computed from the recorded inputs (see the plan 04 summary).
    score = facepalm_score(
        played_prob=WINDOW_14_PLAYED_PROB,
        reply_spread=WINDOW_14_REPLY_SPREAD,
        loss_3=WINDOW_14_LINE_LOSS_3,
        mate_ply=WINDOW_14_MATE_PLY,
    )
    assert score is None
