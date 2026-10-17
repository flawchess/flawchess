"""Schema tests for the endgame API contract.

EndgameEloTimelinePoint exposes endgame_elo, not conversion_elo.
The filtered overview and its aggregated cross-TC chip fields are
gone from the wire; the ranked payload carries per-TC percentiles only.
"""

from __future__ import annotations

import pydantic
import pytest

from app.schemas import endgames as endgames_schemas
from app.schemas.endgames import (
    EndgameEloTimelinePoint,
    RankedMetricOut,
    RankedTcStats,
)

# Aggregated cross-TC fields (and the per-TC chip value fields) retired.
RETIRED_AGGREGATED_FIELDS = {
    "score_gap_percentile",
    "achievable_score_gap_percentile",
    "score_gap_per_tc",
    "achievable_score_gap_per_tc",
    "percentile_value",
    "rate_percentile_value",
}


class TestOverviewSchemasRetired:
    """The overview response, its per-TC breakdown and the cards payloads are gone."""

    # Substrings of the retired class names (kept partial so this guard does not
    # reintroduce the full retired identifiers into the codebase).
    RETIRED_NAME_PARTS = (
        "EndgameOverview",
        "PerTcBreakdown",
        "ScoreGapMaterial",
        "EndgamePerformance",
        "EndgameTimelineResponse",
        "TimePressureTcCard",
        "EndgameMetricsTcCard",
    )

    def test_overview_only_schemas_removed(self) -> None:
        public = [n for n in dir(endgames_schemas) if not n.startswith("_")]
        leaked = [n for n in public if any(part in n for part in self.RETIRED_NAME_PARTS)]
        assert leaked == [], f"Retired overview schemas still exported: {leaked}"


class TestAggregatedChipFieldsRetired:
    """No aggregated cross-TC percentile field on the ranked payload."""

    def test_ranked_tc_stats_has_no_aggregated_fields(self) -> None:
        leaked = RETIRED_AGGREGATED_FIELDS & set(RankedTcStats.model_fields.keys())
        assert leaked == set(), f"Retired fields still on RankedTcStats: {leaked}"

    def test_ranked_metric_out_has_no_aggregated_fields(self) -> None:
        leaked = RETIRED_AGGREGATED_FIELDS & set(RankedMetricOut.model_fields.keys())
        assert leaked == set(), f"Retired fields still on RankedMetricOut: {leaked}"


class TestEndgameEloTimelinePointFieldRename:
    """SC#6: EndgameEloTimelinePoint exposes endgame_elo, not conversion_elo."""

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
        # The legacy field name must no longer satisfy validation. Pydantic
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
