"""Tests for tests/facepalm_seed.py: seeded facts read back the requested target score (D-01).

The seed helper is the only way reader tests put a facepalm score on a flaw row from R2 on, so
its round trip (facts -> game_flaws row -> facepalm_expr) is pinned here, including the band
edges the selection thresholds sit on (FACEPALM_SCORE_MIN, the library bands).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import (
    FACEPALM_DRILL_LAMBDA,
    FACEPALM_LIBRARY_LAMBDA,
)
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmModel,
    FacepalmType,
    facepalm_expr,
    facepalm_type_expr,
)
from tests.facepalm_seed import (
    SEED_FACEPALM_MARGIN,
    SEED_FACEPALM_TOLERANCE,
    facepalm_fact_columns,
    seed_flaw_rows,
)

SEED_USER_ID = 925403
BAND_EDGES = (0.3, 0.7)
TARGETS = (
    0.05,
    BAND_EDGES[0] - SEED_FACEPALM_MARGIN,
    BAND_EDGES[0] + SEED_FACEPALM_MARGIN,
    BAND_EDGES[1] - SEED_FACEPALM_MARGIN,
    BAND_EDGES[1] + SEED_FACEPALM_MARGIN,
    0.95,
)
_COMBINED_MODEL = FacepalmModel(
    intercept=-1.4193,
    played_coef=-0.6629,
    spread_coef=-0.3304,
    loss_coef=1.157,
    loss_floor=0,
    material_form="combined",
    missed_floor=None,
)
_MODELS = (
    pytest.param(FACEPALM_MODEL, id="shipped"),
    pytest.param(_COMBINED_MODEL, id="combined"),
)


@pytest.mark.parametrize("model", _MODELS)
@pytest.mark.parametrize("lam", (FACEPALM_DRILL_LAMBDA, FACEPALM_LIBRARY_LAMBDA))
async def test_seeded_facts_hit_the_target(
    db_session: AsyncSession, model: FacepalmModel, lam: float
) -> None:
    fact_rows = [facepalm_fact_columns(target, lam=lam, model=model) for target in TARGETS]
    game_id = await seed_flaw_rows(db_session, fact_rows, user_id=SEED_USER_ID)
    result = await db_session.execute(
        select(GameFlaw.ply, facepalm_expr(lam, model)).where(GameFlaw.game_id == game_id)
    )
    scores = {ply: score for ply, score in result.all()}
    assert len(scores) == len(TARGETS)
    for ply, target in enumerate(TARGETS):
        assert scores[ply] == pytest.approx(target, abs=SEED_FACEPALM_TOLERANCE), target


async def test_none_target_is_unscored(db_session: AsyncSession) -> None:
    facts = facepalm_fact_columns(None, lam=FACEPALM_DRILL_LAMBDA)
    game_id = await seed_flaw_rows(db_session, [facts], user_id=SEED_USER_ID)
    result = await db_session.execute(
        select(facepalm_expr(FACEPALM_DRILL_LAMBDA)).where(GameFlaw.game_id == game_id)
    )
    assert result.scalar_one() is None


def test_unreachable_target_raises() -> None:
    with pytest.raises(ValueError):
        facepalm_fact_columns(1.0 - 1e-12, lam=FACEPALM_DRILL_LAMBDA)


@pytest.mark.parametrize(
    ("facepalm_type", "target"),
    [("missed_win", 0.8), ("allowed_loss", 0.8), ("missed_win", 0.72)],
)
async def test_seeded_type_and_target(
    db_session: AsyncSession, facepalm_type: FacepalmType, target: float
) -> None:
    """257 D-02: a typed seed reads back both its target score and its facepalm type."""
    facts = facepalm_fact_columns(target, lam=FACEPALM_LIBRARY_LAMBDA, facepalm_type=facepalm_type)
    game_id = await seed_flaw_rows(db_session, [facts], user_id=SEED_USER_ID)
    result = await db_session.execute(
        select(facepalm_expr(FACEPALM_LIBRARY_LAMBDA), facepalm_type_expr()).where(
            GameFlaw.game_id == game_id
        )
    )
    score, seeded_type = result.one()
    assert score == pytest.approx(target, abs=SEED_FACEPALM_TOLERANCE)
    assert seeded_type == facepalm_type
