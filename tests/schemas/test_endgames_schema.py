"""Wave 0 schema tests for Phase 87.4 — Conversion ELO Timeline + Skill removal.

Verify the Pydantic contract after:
- EndgameEloTimelinePoint.endgame_elo → conversion_elo (D-06).
- EndgameOverviewResponse.endgame_elo_timeline → conversion_elo_timeline.
- ScoreGapMaterialResponse loses all Skill composite fields.

Tests are written BEFORE the implementation (RED gate). They will pass once Task 3
renames the field + drops the Skill fields.
"""

from __future__ import annotations

import pydantic
import pytest

from app.schemas.endgames import (
    EndgameEloTimelinePoint,
    EndgameOverviewResponse,
    ScoreGapMaterialResponse,
)


class TestEndgameEloTimelinePoint:
    """SC#3: timeline-point field rename endgame_elo → conversion_elo."""

    def test_endgame_elo_timeline_point_has_conversion_elo(self) -> None:
        pt = EndgameEloTimelinePoint(
            date="2026-05-10",
            conversion_elo=1500,
            actual_elo=1500,
            endgame_games_in_window=10,
            per_week_endgame_games=10,
        )
        assert pt.conversion_elo == 1500

    def test_endgame_elo_timeline_point_rejects_legacy_endgame_elo(self) -> None:
        # The old field name must no longer satisfy validation. Pydantic raises
        # ValidationError because `conversion_elo` is required and `endgame_elo`
        # is an unknown extra (strict by default — endgame.py uses BaseModel).
        with pytest.raises(pydantic.ValidationError):
            EndgameEloTimelinePoint.model_validate(
                {
                    "date": "2026-05-10",
                    "endgame_elo": 1500,
                    "actual_elo": 1500,
                    "endgame_games_in_window": 10,
                    "per_week_endgame_games": 10,
                }
            )


class TestScoreGapMaterialResponseSkillDropped:
    """SC#1 (backend): Skill composite fields removed from the wire."""

    def test_score_gap_response_drops_skill_fields(self) -> None:
        keys = set(ScoreGapMaterialResponse.model_fields.keys())
        forbidden = {
            "section2_score_gap_skill_mean",
            "section2_score_gap_skill_n",
            "section2_score_gap_skill_p_value",
            "section2_score_gap_skill_ci_low",
            "section2_score_gap_skill_ci_high",
            "endgame_skill_rate_mean",
        }
        leaked = forbidden & keys
        assert leaked == set(), f"Skill fields still present on wire: {leaked}"


class TestEndgameOverviewResponseConversionTimeline:
    """SC#3: EndgameOverviewResponse renames endgame_elo_timeline."""

    def test_overview_response_uses_conversion_elo_timeline(self) -> None:
        keys = set(EndgameOverviewResponse.model_fields.keys())
        assert "conversion_elo_timeline" in keys
        assert "endgame_elo_timeline" not in keys
