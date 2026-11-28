"""Tests for app/services/facepalm_score.py, the D-04 constants and reply_spread (Phase 250, 254, 259).

Only the shipped shape is tested (259 owner trim): one scalar score twin, one type twin.

Coverage:
- formula    : facepalm_score equals the logistic of the linear predictor, the key-move term reads
               the reply on a losing row and the best move otherwise
- nulls      : a missing played probability or loss, a losing row without a reply probability and a
               non-losing row without a best-move probability give None
- lambda     : lam 0 is the loss-only score, the missed term rises with lam, lam is range-checked
- sql twin   : facepalm_score_sql / facepalm_type_sql agree with the Python twins on one grid with
               NULL in every input, at both lambda bounds
- omission   : a zero coefficient (or a zero lambda weight) omits its term and its column
- expr       : facepalm_expr / facepalm_type_expr over stored game_flaws facts equal the twins (D-01)
- size       : the compiled expressions stay under MAX_EXPRESSION_CHARS (D-18)
- write-time : material_loss / material_missed (the decaying mean) and the pinned rule
- shape CHECK: the two stored-array CHECKs (they stay until the arrays go)
- spread     : reply_spread of a uniform policy is the move count
- constants  : the known D-04 values and LINE_DEPTH being a stored depth
"""

from __future__ import annotations

import csv
import itertools
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import chess
import pytest
from sqlalchemy import ColumnElement, Float, SmallInteger, column, select, values
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.game_flaw import GameFlaw
from app.services import blunder_check_rules
from app.services.blunder_check_rules import (
    FACEPALM_BEST_PROB_COEF,
    FACEPALM_DRILL_LAMBDA,
    FACEPALM_INTERCEPT,
    FACEPALM_LAMBDA_MAX,
    FACEPALM_LAMBDA_MIN,
    FACEPALM_LIBRARY_LAMBDA,
    FACEPALM_LOSS_COEF,
    FACEPALM_LOSS_FLOOR,
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_COEF,
    FACEPALM_MISSED_FLOOR,
    FACEPALM_MISSED_MATE,
    FACEPALM_PLAYED_COEF,
    FACEPALM_REPLY_PROB_COEF,
    FACEPALM_SCORE_MIN,
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    MATERIAL_DECAY_RATIO,
    PLAYED_PROB_OFFSET,
)
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmColumns,
    FacepalmFacts,
    FacepalmModel,
    _game_flaw_columns,
    facepalm_expr,
    facepalm_score,
    facepalm_score_sql,
    facepalm_type,
    facepalm_type_expr,
    facepalm_type_of,
    facepalm_type_sql,
    is_allowed_loss,
    material_loss,
    material_missed,
)
from app.services.line_material import LINE_LOSS_DEPTHS
from app.services.maia_flaw_stats import _effective_moves, reply_spread
from tests.facepalm_seed import lone_depth_line, seed_flaw_rows
from tests.services.maia_fakes import fake_full_policy

FORMULA_TOLERANCE = 1e-12
PARITY_TOLERANCE = 1e-9
UNIFORM_MOVE_COUNTS = (1, 2, 5, 30)
# asyncpg allows 32767 bind parameters per statement; a VALUES row of the parity grid binds 6.
GRID_CHUNK_ROWS = 2000
MISSED_MATE_VALUE = 7
STORED_FACTS_USER_ID = 925402
# 258 D-18: a compiled score or type expression must stay a small statement fragment.
MAX_EXPRESSION_CHARS = 2000

# Every coefficient non-zero and distinct, so a swapped or dropped term moves the score.
_MODEL = FacepalmModel(
    intercept=1.0,
    played_coef=-0.7,
    loss_coef=0.3,
    missed_coef=0.5,
    best_prob_coef=0.4,
    reply_prob_coef=0.6,
)

# Window 14 (game 2099808, ply 23), copied from the extra row of the committed plan 11 features
# file reports/blunder-check/facepalm-features-2026-11-23.tsv (scalar schema). No loss and no
# missed gain under the quiet rule.
WINDOW_14_GAME_ID = 2099808
WINDOW_14_PLY = 23
WINDOW_14_PLAYED_PROB = 0.0949175
WINDOW_14_BEST_PROB = 0.331294
WINDOW_14_REPLY_PROB = 0.132603
WINDOW_14_LOSS = 0.0
WINDOW_14_MISSED = 0.0
_FEATURES_TSV = (
    Path(__file__).resolve().parents[2]
    / "reports"
    / "blunder-check"
    / "facepalm-features-2026-11-23.tsv"
)

# Parity grid of the SQL twin: NULL in every input, both key-move branches, a mate-valued loss
# (MATE_LOSS = 5.0), a missed gain of 0 and above 0.
_GRID_PLAYED_PROB = (0.02, None)
_GRID_LOSS = (None, 0.0, 2.0, float(MATE_LOSS))
_GRID_MISSED = (0.0, 3.0, None)
_GRID_BEST_PROB = (0.3, None)
_GRID_REPLY_PROB = (0.2, None)

type GridRow = tuple[float | None, float | None, float | None, float | None, float | None]


def _grid() -> list[GridRow]:
    return list(
        itertools.product(
            _GRID_PLAYED_PROB, _GRID_LOSS, _GRID_MISSED, _GRID_BEST_PROB, _GRID_REPLY_PROB
        )
    )


def _facts(
    *,
    played_prob: float | None = 0.1,
    loss: float | None = 3.0,
    missed: float | None = 0.0,
    best_prob: float | None = 0.4,
    reply_prob: float | None = 0.2,
) -> FacepalmFacts:
    return FacepalmFacts(
        played_prob=played_prob,
        loss=loss,
        missed=missed,
        best_prob=best_prob,
        reply_prob=reply_prob,
    )


def _score(*, lam: float = 1.0, model: FacepalmModel = _MODEL, **facts: Any) -> float | None:
    return facepalm_score(_facts(**facts), lam=lam, model=model)


def _facts_of(row: GridRow) -> FacepalmFacts:
    played_prob, loss, missed, best_prob, reply_prob = row
    return FacepalmFacts(
        played_prob=played_prob,
        loss=loss,
        missed=missed,
        best_prob=best_prob,
        reply_prob=reply_prob,
    )


async def _sql_values(
    engine: AsyncEngine,
    grid: Sequence[GridRow],
    expression_of: Callable[[FacepalmColumns], ColumnElement[Any]],
) -> list[Any]:
    """`expression_of(columns)` evaluated on every grid row, in grid order (chunked for the bind limit)."""
    results: list[Any] = []
    typing_row: GridRow = (0.5, 1.0, 1.0, 0.5, 0.5)
    async with engine.connect() as conn:
        for start in range(0, len(grid), GRID_CHUNK_ROWS):
            # The typing row (dropped below) keeps every VALUES column non-NULL: PostgreSQL would
            # type a column of bare NULLs as text.
            chunk = [typing_row, *grid[start : start + GRID_CHUNK_ROWS]]
            rows = values(
                column("idx", SmallInteger),
                column("played", Float),
                column("loss", Float),
                column("missed", Float),
                column("best_prob", Float),
                column("reply_prob", Float),
                name="grid",
            ).data([(i, *row) for i, row in enumerate(chunk)])
            expression = expression_of(
                FacepalmColumns(
                    played_prob=rows.c.played,
                    loss=rows.c.loss,
                    missed=rows.c.missed,
                    best_prob=rows.c.best_prob,
                    reply_prob=rows.c.reply_prob,
                )
            )
            result = await conn.execute(select(rows.c.idx, expression).order_by(rows.c.idx))
            results.extend(value for _, value in result.all()[1:])
    return results


# ---------------------------------------------------------------------------
# The Python twin
# ---------------------------------------------------------------------------


def test_formula_is_the_logistic_of_the_linear_predictor() -> None:
    # A losing row reads the reply term, a row that loses nothing reads the best-move term.
    losing = (
        1.0
        - 0.7 * math.log(0.1 + PLAYED_PROB_OFFSET)
        + 0.3 * 3.0
        + 0.5 * 2.0
        + 0.6 * math.log(0.2 + PLAYED_PROB_OFFSET)
    )
    assert _score(loss=3.0, missed=2.0) == pytest.approx(
        1 / (1 + math.exp(-losing)), abs=FORMULA_TOLERANCE
    )
    non_losing = (
        1.0
        - 0.7 * math.log(0.1 + PLAYED_PROB_OFFSET)
        + 0.5 * 2.0
        + 0.4 * math.log(0.4 + PLAYED_PROB_OFFSET)
    )
    assert _score(loss=0.0, missed=2.0) == pytest.approx(
        1 / (1 + math.exp(-non_losing)), abs=FORMULA_TOLERANCE
    )


def test_missing_input_gives_none() -> None:
    assert _score(played_prob=None) is None
    assert _score(loss=None) is None
    # A losing row needs the reply probability, a row that loses nothing the best-move probability.
    assert _score(loss=3.0, reply_prob=None) is None
    assert _score(loss=3.0, best_prob=None) is not None
    assert _score(loss=0.0, best_prob=None) is None
    assert _score(loss=0.0, reply_prob=None) is not None
    # A NULL missed with a non-zero weight is unscored; lam 0 drops the weight (and the term).
    assert _score(missed=None) is None
    assert _score(missed=None, lam=0.0) is not None


@pytest.mark.parametrize(
    ("loss", "missed", "expected"),
    [
        (2.0, 2.0, True),  # a tie is an allowed loss
        (3.0, 2.0, True),
        (1.0, 2.0, False),  # a mixed row: loses something, but misses more
        (0.0, 0.0, False),
        (1.0, None, True),  # a NULL missed reads as 0.0
    ],
)
def test_is_allowed_loss_rule(loss: float, missed: float | None, expected: bool) -> None:
    assert is_allowed_loss(loss, missed) is expected


def test_mixed_row_reads_the_best_move_term() -> None:
    # 262 D-04: loss 1.0 with missed 2.0 is a missed win, so the key-move term is the best move's,
    # not the reply's (the Phase 259 gate read the reply on any loss above zero).
    z = (
        1.0
        - 0.7 * math.log(0.1 + PLAYED_PROB_OFFSET)
        + 0.3 * 1.0
        + 0.5 * 2.0
        + 0.4 * math.log(0.4 + PLAYED_PROB_OFFSET)
    )
    assert _score(loss=1.0, missed=2.0) == pytest.approx(
        1 / (1 + math.exp(-z)), abs=FORMULA_TOLERANCE
    )
    # NULL rule: the best-move probability decides the mixed row, the reply probability does not.
    assert _score(loss=1.0, missed=2.0, best_prob=None) is None
    assert _score(loss=1.0, missed=2.0, reply_prob=None) is not None


def test_missed_term_is_unknown_best_line_neutral() -> None:
    # D-18: an unknown best line stores missed 0, so the row keeps its loss-only score at any lambda.
    assert _score(missed=0.0, lam=1.0) == _score(missed=0.0, lam=0.0)
    low = _score(missed=3.0, lam=0.5)
    high = _score(missed=3.0, lam=1.0)
    loss_only = _score(missed=3.0, lam=0.0)
    assert loss_only is not None and low is not None and high is not None
    assert loss_only < low < high


def test_lambda_out_of_range_raises() -> None:
    for bad in (FACEPALM_LAMBDA_MIN - 0.1, FACEPALM_LAMBDA_MAX + 0.1):
        with pytest.raises(ValueError):
            facepalm_score(_facts(), lam=bad)


def test_sql_lambda_out_of_range_raises() -> None:
    columns = FacepalmColumns(*([column("x")] * len(FacepalmColumns._fields)))
    for bad in (FACEPALM_LAMBDA_MIN - 0.1, FACEPALM_LAMBDA_MAX + 0.1):
        with pytest.raises(ValueError):
            facepalm_score_sql(columns, lam=bad)


# ---------------------------------------------------------------------------
# The SQL twins: one score grid and one type grid
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lam", (FACEPALM_LAMBDA_MIN, FACEPALM_LAMBDA_MAX))
async def test_sql_twin_parity_grid(test_engine: AsyncEngine, lam: float) -> None:
    grid = _grid()
    sql_scores = await _sql_values(
        test_engine, grid, lambda columns: facepalm_score_sql(columns, lam=lam, model=_MODEL)
    )
    assert len(sql_scores) == len(grid)
    saw_none = saw_value = False
    for row, sql_score in zip(grid, sql_scores, strict=True):
        expected = facepalm_score(_facts_of(row), lam=lam, model=_MODEL)
        if expected is None:
            assert sql_score is None, row
            saw_none = True
        else:
            assert sql_score == pytest.approx(expected, abs=PARITY_TOLERANCE), row
            saw_value = True
    assert saw_none and saw_value


async def test_sql_type_twin_parity_grid(test_engine: AsyncEngine) -> None:
    # The grid holds NULL loss, loss > missed > 0, the tie loss == missed > 0, loss 0 with missed > 0
    # and no material at all, so every branch of the type CASE has a row.
    grid: list[GridRow] = [
        *_grid(),
        (0.5, 2.0, 1.0, 0.5, 0.5),
        (0.5, 2.0, 2.0, 0.5, 0.5),
        (0.5, 0.0, 3.0, 0.5, 0.5),
        (0.5, 0.0, 0.0, 0.5, 0.5),
    ]
    sql_types = await _sql_values(test_engine, grid, facepalm_type_sql)
    assert len(sql_types) == len(grid)
    for row, sql_type in zip(grid, sql_types, strict=True):
        assert sql_type == facepalm_type(_facts_of(row)), row
    assert set(sql_types) == {None, "missed_win", "allowed_loss"}
    assert sql_types[-4:] == ["allowed_loss", "allowed_loss", "missed_win", "missed_win"]


def _compiled(expression: ColumnElement[Any]) -> str:
    return str(expression.compile(dialect=postgresql.dialect()))


def test_zero_coefficient_omits_its_term() -> None:
    # A zero coefficient builds a literal 0.0, so the expression does not even name its column.
    no_reply = replace(_MODEL, reply_prob_coef=0.0)
    no_best = replace(_MODEL, best_prob_coef=0.0)
    full = _compiled(facepalm_score_sql(_game_flaw_columns(), lam=1.0, model=_MODEL))
    assert "maia_best_reply_prob" in full and "maia_best_prob" in full and "material_missed" in full
    assert "maia_best_reply_prob" not in _compiled(
        facepalm_score_sql(_game_flaw_columns(), lam=1.0, model=no_reply)
    )
    assert "maia_best_prob" not in _compiled(
        facepalm_score_sql(_game_flaw_columns(), lam=1.0, model=no_best)
    )
    # lam 0 drops the missed term; the allowed-loss gate (262 D-04) still reads the column once
    # (NULL-safe through the coalesce), so a NULL missed never unscores a row at lam 0.
    assert (
        _compiled(facepalm_score_sql(_game_flaw_columns(), lam=0.0, model=_MODEL)).count(
            "game_flaws.material_missed"
        )
        == 1
    )
    assert (
        _compiled(facepalm_score_sql(_game_flaw_columns(), lam=1.0, model=_MODEL)).count(
            "game_flaws.material_missed"
        )
        == 2
    )
    # The Python twin agrees: the omitted term's NULL input no longer unscores the row.
    assert _score(loss=3.0, reply_prob=None, model=no_reply) is not None
    assert _score(loss=0.0, best_prob=None, model=no_best) is not None
    assert _score(missed=None, lam=0.0) is not None


async def test_zero_coefficient_scores_the_row_in_sql(test_engine: AsyncEngine) -> None:
    no_reply = replace(_MODEL, reply_prob_coef=0.0)
    row: GridRow = (0.2, 3.0, 0.0, 0.3, None)
    [sql_score] = await _sql_values(
        test_engine, [row], lambda columns: facepalm_score_sql(columns, lam=1.0, model=no_reply)
    )
    expected = facepalm_score(_facts_of(row), lam=1.0, model=no_reply)
    assert expected is not None
    assert sql_score == pytest.approx(expected, abs=PARITY_TOLERANCE)


def test_score_and_type_expressions_are_small() -> None:
    assert len(_compiled(facepalm_expr(FACEPALM_LIBRARY_LAMBDA))) < MAX_EXPRESSION_CHARS
    assert len(_compiled(facepalm_type_expr())) < MAX_EXPRESSION_CHARS


# ---------------------------------------------------------------------------
# facepalm_expr over stored game_flaws facts (D-01)
# ---------------------------------------------------------------------------

# One row of stored scalars per seeded flaw: a losing row, a non-losing miss, a losing row without a
# reply probability, a non-losing row without a best-move probability, a NULL played probability, an
# unscored row (the loss and missed pair is NULL together, ck_game_flaws_material_pair) and a mixed
# row (loss 1.0 below missed 3.0, a missed win typed row, scored on the best move even without a reply).
_STORED_FACT_ROWS: tuple[dict[str, Any], ...] = (
    {
        "maia_played_prob": 0.05,
        "material_loss": 4.0,
        "material_missed": 1.0,
        "maia_best_prob": 0.3,
        "maia_best_reply_prob": 0.6,
    },
    {
        "maia_played_prob": 0.4,
        "material_loss": 0.0,
        "material_missed": 3.0,
        "maia_best_prob": 0.25,
        "maia_best_reply_prob": 0.1,
    },
    {
        "maia_played_prob": 0.02,
        "material_loss": 2.0,
        "material_missed": 0.0,
        "maia_best_prob": 0.3,
        "maia_best_reply_prob": None,
    },
    {
        "maia_played_prob": 0.1,
        "material_loss": 0.0,
        "material_missed": 5.0,
        "maia_best_prob": None,
        "maia_best_reply_prob": 0.2,
    },
    {
        "maia_played_prob": None,
        "material_loss": 3.0,
        "material_missed": 0.0,
        "maia_best_prob": 0.3,
        "maia_best_reply_prob": 0.2,
    },
    {
        "maia_played_prob": 0.3,
        "material_loss": None,
        "material_missed": None,
        "maia_best_prob": 0.3,
        "maia_best_reply_prob": 0.2,
    },
    {
        "maia_played_prob": 0.08,
        "material_loss": 1.0,
        "material_missed": 3.0,
        "maia_best_prob": 0.3,
        "maia_best_reply_prob": None,
    },
)


async def _seed_stored_facts(session: AsyncSession, fact_rows: Sequence[dict[str, Any]]) -> int:
    return await seed_flaw_rows(session, fact_rows, user_id=STORED_FACTS_USER_ID)


def _facts_of_flaw(flaw: GameFlaw) -> FacepalmFacts:
    return FacepalmFacts(
        played_prob=flaw.maia_played_prob,
        loss=flaw.material_loss,
        missed=flaw.material_missed,
        best_prob=flaw.maia_best_prob,
        reply_prob=flaw.maia_best_reply_prob,
    )


async def _seeded_flaws(
    session: AsyncSession, fact_rows: Sequence[dict[str, Any]]
) -> list[GameFlaw]:
    game_id = await _seed_stored_facts(session, fact_rows)
    flaws = (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id))).scalars()
    return sorted(flaws, key=lambda flaw: flaw.ply)


@pytest.mark.parametrize("lam", (FACEPALM_LAMBDA_MIN, FACEPALM_LAMBDA_MAX))
@pytest.mark.parametrize("model", [_MODEL, FACEPALM_MODEL], ids=["synthetic", "shipped"])
async def test_expr_matches_python_twin_over_stored_facts(
    db_session: AsyncSession, model: FacepalmModel, lam: float
) -> None:
    flaws = await _seeded_flaws(db_session, _STORED_FACT_ROWS)
    score_rows = await db_session.execute(
        select(GameFlaw.ply, facepalm_expr(lam, model)).where(GameFlaw.game_id == flaws[0].game_id)
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
    # 262 D-04: the mixed row (loss 1.0, missed 3.0, reply NULL) is scored on its best-move term.
    mixed = flaws[-1]
    assert mixed.maia_best_reply_prob is None and scores[mixed.ply] is not None


async def test_expr_unscores_losing_row_without_reply_prob(db_session: AsyncSession) -> None:
    # 256 D-04 mirrored: a losing row with a NULL reply probability is NULL through the expression
    # (row 2 of the stored facts), while a zero reply coefficient scores it.
    flaws = await _seeded_flaws(db_session, _STORED_FACT_ROWS)
    losing_without_reply = flaws[2]
    assert losing_without_reply.maia_best_reply_prob is None
    unscored = (
        await db_session.execute(
            select(facepalm_expr(1.0, _MODEL)).where(
                GameFlaw.game_id == losing_without_reply.game_id,
                GameFlaw.ply == losing_without_reply.ply,
            )
        )
    ).scalar_one()
    assert unscored is None
    scored = (
        await db_session.execute(
            select(facepalm_expr(1.0, replace(_MODEL, reply_prob_coef=0.0))).where(
                GameFlaw.game_id == losing_without_reply.game_id,
                GameFlaw.ply == losing_without_reply.ply,
            )
        )
    ).scalar_one()
    expected = facepalm_score(
        _facts_of_flaw(losing_without_reply), lam=1.0, model=replace(_MODEL, reply_prob_coef=0.0)
    )
    assert expected is not None
    assert scored == pytest.approx(expected, abs=PARITY_TOLERANCE)


async def test_expr_unscores_pure_miss_without_best_prob(db_session: AsyncSession) -> None:
    # 256 D-04: no loss and a NULL maia_best_prob is NULL through the expression (row 3).
    flaws = await _seeded_flaws(db_session, _STORED_FACT_ROWS)
    pure_miss = flaws[3]
    assert pure_miss.material_loss == 0.0 and pure_miss.maia_best_prob is None
    value = (
        await db_session.execute(
            select(facepalm_expr(1.0, _MODEL)).where(
                GameFlaw.game_id == pure_miss.game_id, GameFlaw.ply == pure_miss.ply
            )
        )
    ).scalar_one()
    assert value is None
    assert facepalm_score(_facts_of_flaw(pure_miss), lam=1.0, model=_MODEL) is None


@pytest.mark.parametrize("model", [_MODEL, FACEPALM_MODEL], ids=["synthetic", "shipped"])
async def test_type_expr_matches_python_twin_over_stored_facts(
    db_session: AsyncSession, model: FacepalmModel
) -> None:
    flaws = await _seeded_flaws(db_session, _STORED_FACT_ROWS)
    type_rows = await db_session.execute(
        select(GameFlaw.ply, facepalm_type_expr()).where(GameFlaw.game_id == flaws[0].game_id)
    )
    types: dict[int, str | None] = {ply: ftype for ply, ftype in type_rows.all()}
    assert len(flaws) == len(_STORED_FACT_ROWS)
    seen: set[str | None] = set()
    for flaw in flaws:
        assert types[flaw.ply] == facepalm_type(_facts_of_flaw(flaw)), flaw.ply
        seen.add(types[flaw.ply])
    assert seen == {None, "missed_win", "allowed_loss"}


# ---------------------------------------------------------------------------
# The write-time half: the helpers that turn a stored line into loss and missed
# ---------------------------------------------------------------------------


def _loss(played_3: int | None, mate_ply: int | None = None, *, loss_floor: int | None = 0) -> Any:
    return material_loss(lone_depth_line(played_3), mate_ply, loss_floor=loss_floor)


def test_mate_within_depth_settles_a_missing_loss() -> None:
    assert _loss(None) is None
    assert _loss(None, LINE_DEPTH + 1) is None
    assert _loss(None, 2) == float(MATE_LOSS)


def test_loss_is_capped() -> None:
    assert _loss(-9) == _loss(-LOSS_CAP) == float(LOSS_CAP)


def test_mate_loss_short_circuits_within_line_depth_and_enters_per_depth_after() -> None:
    assert _loss(0, LINE_DEPTH) == float(MATE_LOSS)
    assert _loss(0) == 0.0
    # A mate at ply 4 is beyond LINE_DEPTH: the lone depth-3 line stays 0 at depth 3, and depths
    # 5, 7, 9 (weights 1/4, 1/8, 1/16) count MATE_LOSS. Depth 1 is unknown, so the weights
    # renormalise over 1/2 + 1/4 + 1/8 + 1/16 = 15/16: 5 * (7/16) / (15/16) = 7/3.
    assert _loss(0, LINE_DEPTH + 1) == pytest.approx(7 / 3)


def test_loss_floor_clips_negative_losses_only_when_set() -> None:
    assert _loss(3, loss_floor=0) == 0.0
    assert _loss(3, loss_floor=None) == -3.0


def _missed(
    played_3: int | None,
    best_3: int | None,
    best_mate_ply: int | None = None,
    *,
    missed_floor: int | None = 0,
) -> float:
    return material_missed(
        lone_depth_line(played_3),
        None if best_3 is None else lone_depth_line(best_3),
        best_mate_ply,
        missed_floor=missed_floor,
        missed_cap=LOSS_CAP,
        missed_mate=MISSED_MATE_VALUE,
    )


@pytest.mark.parametrize(
    ("played_3", "best_3", "expected"),
    [(-5, 0, 0.0), (5, 10, 5.0), (-5, 3, 3.0)],
    ids=["5_0_loss_only", "0_5_pure_miss", "5_3_mixed"],
)
def test_missed_d05_table(played_3: int, best_3: int, expected: float) -> None:
    # D-05 table rows (loss / missed): 5/0, 0/5 and 5/3 for (played, best) = (-5, 0), (5, 10), (-5, 3).
    # The gain is best - max(0, played) capped at LOSS_CAP; a lone depth-3 line gives it unchanged.
    assert _missed(played_3, best_3, missed_floor=None) == expected


def test_missed_floor_cap_unknown_and_mate() -> None:
    # A negative raw gain (best line behind) is kept without a floor and raised to 0 with floor 0.
    assert _missed(5, 2, missed_floor=None) == -3.0
    assert _missed(5, 2) == 0.0
    # The cap applies to a big gain.
    assert _missed(0, 9) == float(LOSS_CAP)
    # D-18: an unknown best line contributes 0 (and so does an unknown played line).
    assert _missed(0, None) == 0.0
    assert _missed(None, 4) == 0.0
    # A best mate within LINE_DEPTH (ply 0 = the best move itself mates) counts the mate value,
    # even when the best line's material is unknown.
    for mate_ply in (0, 2):
        assert _missed(0, None, mate_ply) == MISSED_MATE_VALUE
    # A mate at ply 4 is beyond LINE_DEPTH: depth 3 gains 1 (weight 1/2), depths 5, 7, 9 count the
    # mate value 7 (weights 1/4, 1/8, 1/16), depth 1 is unknown: (1/2 + 7 * 7/16) / (15/16) = 19/5.
    assert _missed(0, 1, LINE_DEPTH + 1) == pytest.approx(3.8)


def test_material_missed_reads_the_best_line_only_when_the_played_line_is_known() -> None:
    kwargs: dict[str, Any] = {
        "missed_floor": 0,
        "missed_cap": LOSS_CAP,
        "missed_mate": MISSED_MATE_VALUE,
    }
    best = lone_depth_line(4)
    assert material_missed(lone_depth_line(0), best, None, **kwargs) == 4.0
    assert material_missed(lone_depth_line(None), best, None, **kwargs) == 0.0


def test_write_time_material_rule_is_pinned() -> None:
    # These constants decide what the hook and the line pass STORE; changing one changes every
    # stored loss and missed value, so it needs a prod line pass with a new cutoff first.
    message = "changing the material rule needs a prod line pass (259 D-05)"
    assert LINE_DEPTH == 3, message
    assert LOSS_CAP == 5, message
    assert MATE_LOSS == 5, message
    assert FACEPALM_LOSS_FLOOR == 0, message
    assert FACEPALM_MISSED_FLOOR == 0, message
    assert FACEPALM_MISSED_CAP == 5, message
    assert FACEPALM_MISSED_MATE == 5, message
    assert MATERIAL_DECAY_RATIO == 0.5, message


# ---------------------------------------------------------------------------
# reply_spread and the constants
# ---------------------------------------------------------------------------


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
        loss_coef=FACEPALM_LOSS_COEF,
        missed_coef=FACEPALM_MISSED_COEF,
        best_prob_coef=FACEPALM_BEST_PROB_COEF,
        reply_prob_coef=FACEPALM_REPLY_PROB_COEF,
    )
    facts = _facts(loss=3.0)
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
    assert float(row["best_prob"]) == WINDOW_14_BEST_PROB
    assert float(row["reply_prob"]) == WINDOW_14_REPLY_PROB
    assert float(row["loss"]) == WINDOW_14_LOSS
    assert float(row["missed"]) == WINDOW_14_MISSED


def test_window_14_is_not_selected_by_the_shipped_model() -> None:
    """Window 14 (an even trade in the engine's line, the owner's false alarm) stays below the drill cut."""
    score = facepalm_score(
        FacepalmFacts(
            played_prob=WINDOW_14_PLAYED_PROB,
            loss=WINDOW_14_LOSS,
            missed=WINDOW_14_MISSED,
            best_prob=WINDOW_14_BEST_PROB,
            reply_prob=WINDOW_14_REPLY_PROB,
        ),
        lam=FACEPALM_DRILL_LAMBDA,
    )

    assert score is None or score < FACEPALM_SCORE_MIN


# ---------------------------------------------------------------------------
# 257 D-01: the stats cut. 257 D-02: the facepalm type rule
# ---------------------------------------------------------------------------

# The frontend's Facepalm tag cut in whole percents (frontend/src/lib/facepalm.ts
# FACEPALM_HIGH_CUTOFF), parsed from the file so the backend stats cut cannot drift from it
# unnoticed (parity-test precedent: tests/schemas/test_train_telemetry_parity.py).
_FACEPALM_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/facepalm.ts"
_HIGH_CUTOFF_PATTERN = re.compile(r"export const FACEPALM_HIGH_CUTOFF = (\d+);")
# The frontend states the cut in whole percents, the backend as a 0..1 score.
_PERCENT_SCALE = 100.0


def _frontend_facepalm_cutoff_pct() -> int:
    match = _HIGH_CUTOFF_PATTERN.search(_FACEPALM_TS.read_text())
    assert match is not None, (
        "FACEPALM_HIGH_CUTOFF declaration not found in frontend/src/lib/facepalm.ts"
    )
    return int(match.group(1))


_HARD_TO_SPOT_PATTERN = re.compile(r"export const FACEPALM_HARD_TO_SPOT_BELOW = (\d+);")


def test_hard_to_catch_cut_is_the_frontend_hard_to_spot_cut() -> None:
    """264 D-23: the game-move line's "hard to spot" band and blunder check's "hard to catch"
    line share one cut, so blunder check can drop the band word exactly when it shows the line."""
    match = _HARD_TO_SPOT_PATTERN.search(_FACEPALM_TS.read_text())
    assert match is not None, (
        "FACEPALM_HARD_TO_SPOT_BELOW declaration not found in frontend/src/lib/facepalm.ts"
    )
    hard_to_catch = getattr(blunder_check_rules, "HARD_TO_CATCH_SCORE_BELOW", None)
    assert hard_to_catch is not None
    assert hard_to_catch == int(match.group(1)) / _PERCENT_SCALE


def test_facepalm_stats_min_is_the_frontend_facepalm_cut() -> None:
    # Read through the module so a missing constant fails this assertion, not the file's import.
    stats_min = getattr(blunder_check_rules, "FACEPALM_STATS_MIN", None)
    assert stats_min is not None
    assert stats_min == _frontend_facepalm_cutoff_pct() / _PERCENT_SCALE
    # 259 D-15: the drill cut moved to 0.70 and now equals the stats cut in value; they stay two
    # constants (257 D-01) so either can move alone, hence no value inequality is asserted.
    assert "FACEPALM_STATS_MIN" in vars(blunder_check_rules)
    assert "FACEPALM_SCORE_MIN" in vars(blunder_check_rules)


@pytest.mark.parametrize(
    ("loss", "missed", "expected"),
    [
        (None, 0.0, None),
        (0.0, 0.0, "missed_win"),
        (0.0, 3.0, "missed_win"),
        (1.0, 2.0, "missed_win"),
        (1.0, 3.0, "missed_win"),  # the mixed row of 262 D-04
        (2.0, 0.0, "allowed_loss"),
        (2.0, 2.0, "allowed_loss"),
    ],
)
def test_facepalm_type_of_rule(loss: float | None, missed: float, expected: str | None) -> None:
    assert facepalm_type_of(loss, missed) == expected
