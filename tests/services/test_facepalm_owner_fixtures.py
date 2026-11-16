"""The two owner miss fixtures carry every score input (Phase 254 plan 04, D-14, D-18)."""

from __future__ import annotations

from typing import Any, get_args

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import (
    FACEPALM_DRILL_LAMBDA,
    FACEPALM_SCORE_MIN,
    MaterialInput,
)
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmFacts,
    facepalm_expr,
    facepalm_score,
    material_loss,
    material_missed,
    missed_feature,
)
from tests.facepalm_models import PHASE_254_MODEL
from tests.facepalm_seed import seed_flaw_rows
from tests.services.facepalm_owner_fixtures import OWNER_FIXTURE_FACTS, OwnerFixtureFacts
from tests.services.line_material_fixtures import OWNER_MISS_FIXTURES

# D-05 table: missed = best_3 - max(0, played_3) of the two owner fixtures.
EXPECTED_MISSED: dict[tuple[int, int], float] = {(817357, 24): 3.0, (820181, 65): 5.0}
OWNER_FIXTURES_USER_ID = 925403
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


def test_constant_arrays_read_the_same_material_under_every_input() -> None:
    # The fixtures' arrays are constant, so every material input reads the same loss and missed
    # gain as depth 3 and only the coefficients move these scores (256 plan 01).
    for fixture in OWNER_FIXTURE_FACTS:
        facts = fixture.facts
        expected_missed = EXPECTED_MISSED[(fixture.game_id, fixture.ply)]
        for material_input in get_args(MaterialInput):
            loss = material_loss(
                facts.played_material,
                facts.mate_ply,
                material_input=material_input,
                loss_floor=FACEPALM_MODEL.loss_floor,
            )
            missed = material_missed(
                facts.played_material,
                facts.best_material,
                facts.best_mate_ply,
                material_input=material_input,
                missed_floor=FACEPALM_MODEL.missed_floor,
                missed_cap=FACEPALM_MODEL.missed_cap,
                missed_mate=FACEPALM_MODEL.missed_mate,
            )
            assert loss == 0.0, (fixture.game_id, material_input)
            assert missed == expected_missed, (fixture.game_id, material_input)


def _fact_row(facts: FacepalmFacts) -> dict[str, Any]:
    """The stored GameFlaw facts of one fixture (every input present, no line mates)."""
    assert facts.played_material is not None and facts.best_material is not None
    return {
        "maia_played_prob": facts.played_prob,
        "maia_reply_spread": facts.reply_spread,
        "played_line_material": list(facts.played_material),
        "line_mate_ply": facts.mate_ply,
        "best_line_material": list(facts.best_material),
        "best_line_mate_ply": facts.best_mate_ply,
        "maia_best_prob": facts.best_prob,
        "maia_pre_spread": facts.pre_spread,
    }


# Observed outcome of the Phase 256 refit (reports/blunder-check/facepalm-fit-2026-11-16.md, label
# sets 1-8, material input decaying_mean), recorded here on purpose and not hidden. The owner's two
# missed gains still do not qualify, and both now score LOWER than under the Phase 254 model
# (0.1458 and 0.1540): the new fit puts its weight on the best-move probability and the loss, and
# the two fixtures have a constant material line, so aggregating over depths cannot lift them. The
# owner saw these scores at the 256-07 checkpoint (D-13) and kept FACEPALM_SCORE_MIN = 0.5. This is
# information, not a fitting target; revisit when a better input for misses exists.
EXPECTED_SHIPPED_SCORE: dict[tuple[int, int], float] = {(817357, 24): 0.0632, (820181, 65): 0.1044}
SHIPPED_SCORE_TOLERANCE = 5e-5


@pytest.mark.parametrize("fixture", OWNER_FIXTURE_FACTS, ids=_id)
def test_owner_fixtures_score_lower_under_the_refit_and_stay_below_the_cut(
    fixture: OwnerFixtureFacts,
) -> None:
    previous = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA, model=PHASE_254_MODEL)
    shipped = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA, model=FACEPALM_MODEL)

    assert previous is not None and shipped is not None
    assert shipped < previous
    assert shipped < FACEPALM_SCORE_MIN
    assert shipped == pytest.approx(
        EXPECTED_SHIPPED_SCORE[(fixture.game_id, fixture.ply)], abs=SHIPPED_SCORE_TOLERANCE
    )


async def test_owner_fixtures_through_the_sql_expression_match_the_twin(
    db_session: AsyncSession,
) -> None:
    # The same observed outcome as above, read back through facepalm_expr over seeded facts: both
    # models agree with the Python twin, the refit is strictly lower and still below the cut.
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

    frozen_scores = await _scores(PHASE_254_MODEL)
    shipped_scores = await _scores(FACEPALM_MODEL)
    for ply, fixture in enumerate(OWNER_FIXTURE_FACTS):
        frozen, shipped = frozen_scores[ply], shipped_scores[ply]
        assert frozen is not None and shipped is not None
        assert shipped < frozen
        assert shipped < FACEPALM_SCORE_MIN
        for sql_score, model in ((frozen, PHASE_254_MODEL), (shipped, FACEPALM_MODEL)):
            python_score = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA, model=model)
            assert python_score == pytest.approx(sql_score, abs=STORED_FLOAT_TOLERANCE)
