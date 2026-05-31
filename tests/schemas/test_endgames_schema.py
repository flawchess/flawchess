"""Wave 0 schema tests for Phase 87.5 — Endgame ELO Timeline field rename.

Verify the Pydantic contract after Phase 87.5 D-06:
- EndgameEloTimelinePoint.conversion_elo → endgame_elo
- EndgameOverviewResponse.conversion_elo_timeline → endgame_elo_timeline
- ScoreGapMaterialResponse continues to drop the Phase 78 Skill composite fields.

Tests are written BEFORE the implementation (RED gate). They will pass once Task 3
in Plan 87.5-01 renames the fields end-to-end.
"""

from __future__ import annotations

import pydantic
import pytest

from app.schemas.endgames import (
    EndgameEloTimelinePoint,
    EndgameOverviewResponse,
    EndgamePerformanceResponse,
    ScoreGapMaterialResponse,
)


class TestScoreGapMaterialResponseSkillDropped:
    """SC#1 (backend, inherited from Phase 78): Skill composite fields stay off-wire."""

    def test_score_gap_response_drops_skill_fields(self) -> None:
        keys = set(ScoreGapMaterialResponse.model_fields.keys())
        forbidden = {
            "score_gap_skill_mean",
            "score_gap_skill_n",
            "score_gap_skill_p_value",
            "score_gap_skill_ci_low",
            "score_gap_skill_ci_high",
            "endgame_skill_rate_mean",
        }
        leaked = forbidden & keys
        assert leaked == set(), f"Skill fields still present on wire: {leaked}"


class TestEndgameOverviewResponseEndgameEloTimeline:
    """SC#6 (Phase 87.5): EndgameOverviewResponse uses endgame_elo_timeline."""

    def test_overview_response_uses_endgame_elo_timeline(self) -> None:
        keys = set(EndgameOverviewResponse.model_fields.keys())
        assert "endgame_elo_timeline" in keys
        assert "conversion_elo_timeline" not in keys


class TestEndgameEloTimelinePointFieldRename:
    """SC#6 (Phase 87.5): EndgameEloTimelinePoint exposes endgame_elo, not conversion_elo."""

    def test_point_has_endgame_elo_field(self) -> None:
        pt = EndgameEloTimelinePoint(
            date="2026-05-17",
            endgame_elo=1500,
            non_endgame_elo=1480,
            actual_elo=1500,
            endgame_games_in_window=10,
            per_week_endgame_games=10,
        )
        assert pt.endgame_elo == 1500
        assert pt.non_endgame_elo == 1480
        assert pt.actual_elo == 1500

    def test_point_rejects_legacy_conversion_elo(self) -> None:
        # The Phase 87.4 field name must no longer satisfy validation. Pydantic
        # raises ValidationError because endgame_elo is now required and
        # conversion_elo would be either missing-required or unknown-extra.
        with pytest.raises(pydantic.ValidationError):
            EndgameEloTimelinePoint.model_validate(
                {
                    "date": "2026-05-17",
                    "conversion_elo": 1500,
                    "actual_elo": 1500,
                    "endgame_games_in_window": 10,
                    "per_week_endgame_games": 10,
                }
            )


class TestPercentileFieldsPresent:
    """Phase 94 (PCTL-02) / Phase 97 D-10: percentile fields on the wire.

    Phase 94 added 4 nullable `_percentile` fields:
      - score_gap_percentile (Overall Performance chip — KEPT)
      - achievable_score_gap_percentile (Overall Performance chip — KEPT)
      - score_gap_conv_percentile (Metrics-section chip — REMOVED in Phase 97 D-10)
      - score_gap_parity_percentile (Metrics-section chip — REMOVED in Phase 97 D-10)

    Phase 97 D-10: score_gap_conv_percentile, score_gap_parity_percentile,
    and recovery_score_gap_percentile were Metrics-section-only and are removed
    now that the EndgameMetricsSection component is deleted (superseded by per-TC
    cards). Only the Overall-Performance chips survive.
    """

    def test_score_gap_response_has_overall_percentile_field(self) -> None:
        keys = set(ScoreGapMaterialResponse.model_fields.keys())
        assert "score_gap_percentile" in keys, (
            "score_gap_percentile missing — Overall Performance chip must remain"
        )
        # Metrics-section-only fields removed in Phase 97 D-10.
        removed = {
            "score_gap_conv_percentile",
            "score_gap_parity_percentile",
            "recovery_score_gap_percentile",
            "score_gap_conv_per_tc",
            "score_gap_parity_per_tc",
            "recovery_score_gap_per_tc",
        }
        leaked = removed & keys
        assert leaked == set(), f"Metrics-section-only fields still present: {leaked}"

    def test_performance_response_has_percentile_field(self) -> None:
        keys = set(EndgamePerformanceResponse.model_fields.keys())
        assert "achievable_score_gap_percentile" in keys, (
            "achievable_score_gap_percentile missing from EndgamePerformanceResponse.model_fields"
        )
