"""The two owner miss fixtures carry every scalar score input (Phase 254 plan 04, Phase 259 D-05)."""

from __future__ import annotations

from typing import Any

import chess
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA, FACEPALM_SCORE_MIN
from app.services.facepalm_inputs import facepalm_material_inputs
from app.services.facepalm_score import (
    FacepalmFacts,
    facepalm_expr,
    facepalm_score,
    facepalm_type_expr,
)
from tests.facepalm_seed import seed_flaw_rows
from tests.services.facepalm_owner_fixtures import OWNER_FIXTURE_FACTS, OwnerFixtureFacts
from tests.services.line_material_fixtures import OWNER_MISS_FIXTURES

# D-05 table: the missed gain of the two owner fixtures.
EXPECTED_MISSED: dict[tuple[int, int], float] = {(817357, 24): 3.0, (820181, 65): 5.0}
OWNER_FIXTURES_USER_ID = 925403
# The probabilities are stored as 4-byte floats, so the SQL value is the twin's to 1e-6.
STORED_FLOAT_TOLERANCE = 1e-6


def _id(fixture: OwnerFixtureFacts) -> str:
    return f"game{fixture.game_id}-ply{fixture.ply}"


def test_fixtures_cover_both_owner_games() -> None:
    assert {(f.game_id, f.ply) for f in OWNER_FIXTURE_FACTS} == set(EXPECTED_MISSED)
    assert {(f.game_id, f.ply) for f in OWNER_FIXTURE_FACTS} == {
        (f.game_id, f.ply) for f in OWNER_MISS_FIXTURES
    }


@pytest.mark.parametrize("fixture", OWNER_FIXTURE_FACTS, ids=_id)
def test_every_score_input_is_present(fixture: OwnerFixtureFacts) -> None:
    facts = fixture.facts

    for value in (facts.played_prob, facts.loss, facts.missed, facts.best_prob, facts.reply_prob):
        assert value is not None


@pytest.mark.parametrize("fixture", OWNER_FIXTURE_FACTS, ids=_id)
def test_stored_inputs_agree_with_the_line_fixtures(fixture: OwnerFixtureFacts) -> None:
    line = next(
        f for f in OWNER_MISS_FIXTURES if (f.game_id, f.ply) == (fixture.game_id, fixture.ply)
    )

    inputs = facepalm_material_inputs(
        chess.Board(line.pre_fen), line.played_uci, line.refutation_line, line.best_line
    )

    assert inputs.loss == fixture.facts.loss
    assert inputs.missed == fixture.facts.missed
    assert inputs.missed == EXPECTED_MISSED[(fixture.game_id, fixture.ply)]


@pytest.mark.parametrize("fixture", OWNER_FIXTURE_FACTS, ids=_id)
def test_owner_fixtures_stay_on_the_accepted_side_of_the_cut(fixture: OwnerFixtureFacts) -> None:
    # 259 D-15 (2026-11-22): the owner accepted both fixtures below the drill cut (259-11-SUMMARY:
    # 0.0654 and 0.1389 against FACEPALM_SCORE_MIN 0.7), so neither is served as a facepalm.
    score = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA)

    assert score is not None
    assert score < FACEPALM_SCORE_MIN


def _fact_row(facts: FacepalmFacts) -> dict[str, Any]:
    """The stored GameFlaw facts of one fixture (every input present)."""
    return {
        "maia_played_prob": facts.played_prob,
        "material_loss": facts.loss,
        "material_missed": facts.missed,
        "maia_best_prob": facts.best_prob,
        "maia_best_reply_prob": facts.reply_prob,
    }


async def test_owner_fixtures_through_the_sql_expression_match_the_twin(
    db_session: AsyncSession,
) -> None:
    # Read back through facepalm_expr over seeded facts: the SQL value equals the Python twin, and
    # both fixtures are missed wins (no loss, a missed gain).
    game_id = await seed_flaw_rows(
        db_session,
        [_fact_row(fixture.facts) for fixture in OWNER_FIXTURE_FACTS],
        user_id=OWNER_FIXTURES_USER_ID,
    )
    result = await db_session.execute(
        select(GameFlaw.ply, facepalm_expr(FACEPALM_DRILL_LAMBDA), facepalm_type_expr()).where(
            GameFlaw.game_id == game_id
        )
    )
    by_ply = {ply: (score, ftype) for ply, score, ftype in result.all()}
    for ply, fixture in enumerate(OWNER_FIXTURE_FACTS):
        sql_score, ftype = by_ply[ply]
        python_score = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA)
        assert sql_score is not None and python_score is not None
        assert python_score == pytest.approx(sql_score, abs=STORED_FLOAT_TOLERANCE)
        assert ftype == "missed_win"
