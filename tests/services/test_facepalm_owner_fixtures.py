"""The two owner miss fixtures carry every score input (Phase 254 plan 04, D-14, D-18)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA, FACEPALM_SCORE_MIN
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmFacts,
    facepalm_expr,
    facepalm_score,
    missed_feature,
)
from tests.facepalm_models import PHASE_250_MODEL
from tests.facepalm_seed import seed_flaw_rows
from tests.services.facepalm_owner_fixtures import OWNER_FIXTURE_FACTS, OwnerFixtureFacts
from tests.services.line_material_fixtures import OWNER_MISS_FIXTURES

# D-05 table: missed = best_3 - max(0, played_3) of the two owner fixtures.
EXPECTED_MISSED: dict[tuple[int, int], float] = {(817357, 24): 3.0, (820181, 65): 5.0}
OWNER_FIXTURES_USER_ID = 925403
ARRAY_SLOTS = 9
# The probabilities and spreads are stored as 4-byte floats, so the SQL value is the twin's to 1e-6.
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

    # Neither fixture line mates within LINE_DEPTH, every other input was measured on dev.
    assert facts.mate_ply is None and facts.best_mate_ply is None
    for value in (
        facts.played_prob,
        facts.reply_spread,
        facts.played_3,
        facts.best_3,
        facts.best_prob,
        facts.pre_spread,
    ):
        assert value is not None


@pytest.mark.parametrize("fixture", OWNER_FIXTURE_FACTS, ids=_id)
def test_depth_3_facts_agree_with_the_line_fixtures_and_d05(fixture: OwnerFixtureFacts) -> None:
    line = next(
        f for f in OWNER_MISS_FIXTURES if (f.game_id, f.ply) == (fixture.game_id, fixture.ply)
    )

    assert fixture.facts.played_3 == line.expected_played_3
    assert fixture.facts.best_3 == line.expected_best_3
    missed = missed_feature(
        fixture.facts.played_3,
        fixture.facts.best_3,
        fixture.facts.best_mate_ply,
        missed_floor=FACEPALM_MODEL.missed_floor,
        missed_cap=FACEPALM_MODEL.missed_cap,
        missed_mate=FACEPALM_MODEL.missed_mate,
    )
    assert missed == EXPECTED_MISSED[(fixture.game_id, fixture.ply)]


def _material_array(depth_3: int) -> list[int | None]:
    """A stored 9-slot signed array: `depth_3` at the odd depths (1, 3, ...), NULL at the even (D-17)."""
    return [depth_3 if index % 2 == 0 else None for index in range(ARRAY_SLOTS)]


def _fact_row(facts: FacepalmFacts) -> dict[str, Any]:
    """The stored GameFlaw facts of one fixture (every input present, no line mates)."""
    assert facts.played_3 is not None and facts.best_3 is not None
    return {
        "maia_played_prob": facts.played_prob,
        "maia_reply_spread": facts.reply_spread,
        "played_line_material": _material_array(facts.played_3),
        "line_mate_ply": facts.mate_ply,
        "best_line_material": _material_array(facts.best_3),
        "best_line_mate_ply": facts.best_mate_ply,
        "maia_best_prob": facts.best_prob,
        "maia_pre_spread": facts.pre_spread,
    }


# KNOWN SHORTFALL of the 2026-11-15 refit, recorded here on purpose and not hidden. The owner's
# two missed gains should qualify, but under the shipped model both still score about 0.15 (0.02
# under the frozen Phase 250 model): they improve a lot yet stay below FACEPALM_SCORE_MIN. The
# fit gave the size of the missed gain a coefficient of only 0.0891 (the best-move probability
# carries the pure misses instead), so a missed +3 or +5 barely moves the score. Revisit when a
# better input for misses exists. Owner accepted this outcome on 2026-11-15.
@pytest.mark.parametrize("fixture", OWNER_FIXTURE_FACTS, ids=_id)
def test_owner_fixtures_improve_under_the_refit_but_stay_below_the_cut(
    fixture: OwnerFixtureFacts,
) -> None:
    frozen = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA, model=PHASE_250_MODEL)
    shipped = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA, model=FACEPALM_MODEL)

    assert frozen is not None and shipped is not None
    assert shipped > frozen
    assert shipped < FACEPALM_SCORE_MIN


async def test_owner_fixtures_through_the_sql_expression_match_the_twin(
    db_session: AsyncSession,
) -> None:
    # The same known shortfall as above, read back through facepalm_expr over seeded facts: both
    # models agree with the Python twin, the refit is strictly higher and still below the cut.
    game_id = await seed_flaw_rows(
        db_session,
        [_fact_row(fixture.facts) for fixture in OWNER_FIXTURE_FACTS],
        user_id=OWNER_FIXTURES_USER_ID,
    )

    async def _scores(model: Any) -> dict[int, float | None]:
        result = await db_session.execute(
            select(GameFlaw.ply, facepalm_expr(FACEPALM_DRILL_LAMBDA, model)).where(
                GameFlaw.game_id == game_id
            )
        )
        return {ply: score for ply, score in result.all()}

    frozen_scores = await _scores(PHASE_250_MODEL)
    shipped_scores = await _scores(FACEPALM_MODEL)
    for ply, fixture in enumerate(OWNER_FIXTURE_FACTS):
        frozen, shipped = frozen_scores[ply], shipped_scores[ply]
        assert frozen is not None and shipped is not None
        assert shipped > frozen
        assert shipped < FACEPALM_SCORE_MIN
        for sql_score, model in ((frozen, PHASE_250_MODEL), (shipped, FACEPALM_MODEL)):
            python_score = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA, model=model)
            assert python_score == pytest.approx(sql_score, abs=STORED_FLOAT_TOLERANCE)
