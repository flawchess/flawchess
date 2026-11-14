"""The two owner miss fixtures carry every score input (Phase 254 plan 04, D-14, D-18)."""

from __future__ import annotations

import pytest

from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    facepalm_score,
    missed_feature,
)
from tests.services.facepalm_owner_fixtures import OWNER_FIXTURE_FACTS, OwnerFixtureFacts
from tests.services.line_material_fixtures import OWNER_MISS_FIXTURES

# D-05 table: missed = best_3 - max(0, played_3) of the two owner fixtures.
EXPECTED_MISSED: dict[tuple[int, int], float] = {(817357, 24): 3.0, (820181, 65): 5.0}
# Both fixtures score about 2% under the pre-refit model (CONTEXT specifics): the defect the
# refit must fix. Plan 12 replaces this ceiling with "at or above FACEPALM_SCORE_MIN".
PRE_REFIT_SCORE_CEILING: float = 0.1


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


@pytest.mark.parametrize("fixture", OWNER_FIXTURE_FACTS, ids=_id)
def test_pre_refit_model_scores_both_misses_below_the_ceiling(fixture: OwnerFixtureFacts) -> None:
    score = facepalm_score(fixture.facts, lam=FACEPALM_DRILL_LAMBDA, model=FACEPALM_MODEL)

    assert score is not None
    assert score < PRE_REFIT_SCORE_CEILING
