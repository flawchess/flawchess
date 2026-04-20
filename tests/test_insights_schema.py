"""Tests for the Phase 63 findings-pipeline Pydantic schemas (app/schemas/insights.py).

Covers:
- FilterContext: defaults, Literal validation, field set matches INS-03 spec
- SubsectionFinding: required + optional fields, NaN value round-trip, Literal validation
- EndgameTabFindings: composition, required fields, FlagId validation
- FlagId / SectionId Literal alias contents match CONTEXT.md D-09 / specifics
- Re-exports: Zone, Trend, SampleQuality, Window, MetricId, SubsectionId all come from endgame_zones
"""

import datetime
import json
import math

import pytest
from pydantic import ValidationError

from app.schemas.insights import (
    EndgameTabFindings,
    FilterContext,
    FlagId,
    MetricId,
    SampleQuality,
    SectionId,
    SubsectionFinding,
    SubsectionId,
    Trend,
    Window,
    Zone,
)


class TestFilterContext:
    """FilterContext mirrors the endgame router's filter surface."""

    def test_defaults_all_optional(self) -> None:
        """FilterContext() instantiates cleanly — every field has a default."""
        fc = FilterContext()
        assert fc.recency == "all_time"
        assert fc.opponent_strength == "any"
        assert fc.color == "all"
        assert fc.time_controls == []
        assert fc.platforms == []
        assert fc.rated_only is False

    def test_populated(self) -> None:
        """Caller-provided values round-trip through model_dump."""
        fc = FilterContext(
            recency="3months",
            opponent_strength="stronger",
            color="white",
            time_controls=["blitz", "rapid"],
            platforms=["chess.com"],
            rated_only=True,
        )
        dumped = fc.model_dump()
        assert dumped == {
            "recency": "3months",
            "opponent_strength": "stronger",
            "color": "white",
            "time_controls": ["blitz", "rapid"],
            "platforms": ["chess.com"],
            "rated_only": True,
        }

    def test_recency_rejects_unknown_literal(self) -> None:
        """Pydantic v2 rejects unknown Literal values for recency."""
        with pytest.raises(ValidationError):
            FilterContext(recency="invalid")  # ty: ignore[invalid-argument-type]

    def test_opponent_strength_rejects_unknown_literal(self) -> None:
        with pytest.raises(ValidationError):
            FilterContext(opponent_strength="bogus")  # ty: ignore[invalid-argument-type]

    def test_color_rejects_unknown_literal(self) -> None:
        with pytest.raises(ValidationError):
            FilterContext(color="purple")  # ty: ignore[invalid-argument-type]

    def test_field_order_locked(self) -> None:
        """Field order is load-bearing for findings_hash determinism (FIND-05).

        Pydantic v2 model_dump_json emits fields in declaration order; the
        service post-processes with json.dumps(sort_keys=True) but the raw
        declaration order is asserted here so Plan 04's hash computation has
        a stable input shape to reason about.
        """
        assert list(FilterContext.model_fields.keys()) == [
            "recency",
            "opponent_strength",
            "color",
            "time_controls",
            "platforms",
            "rated_only",
        ]


class TestSubsectionFinding:
    """SubsectionFinding: per-subsection-per-window measurement unit."""

    def _valid_kwargs(self) -> dict:
        return {
            "subsection_id": "overall",
            "window": "all_time",
            "metric": "score_gap",
            "value": 0.05,
            "zone": "typical",
            "trend": "stable",
            "weekly_points_in_window": 30,
            "sample_size": 120,
            "sample_quality": "adequate",
            "is_headline_eligible": True,
        }

    def test_required_fields_only(self) -> None:
        """Only required fields; parent_subsection_id and dimension default to None."""
        f = SubsectionFinding(**self._valid_kwargs())
        assert f.parent_subsection_id is None
        assert f.dimension is None

    def test_populated_with_optional(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["parent_subsection_id"] = "results_by_endgame_type"
        kwargs["dimension"] = {"bucket": "conversion"}
        f = SubsectionFinding(**kwargs)
        assert f.parent_subsection_id == "results_by_endgame_type"
        assert f.dimension == {"bucket": "conversion"}

    def test_nan_value_serializes_to_json_null(self) -> None:
        """Empty-window convention: NaN value round-trips through model_dump_json as null."""
        kwargs = self._valid_kwargs()
        kwargs["value"] = float("nan")
        kwargs["zone"] = "typical"
        kwargs["trend"] = "n_a"
        kwargs["sample_size"] = 0
        kwargs["sample_quality"] = "thin"
        kwargs["is_headline_eligible"] = False
        f = SubsectionFinding(**kwargs)
        payload = json.loads(f.model_dump_json())
        assert payload["value"] is None

    def test_zone_rejects_unknown_literal(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["zone"] = "neutral"  # not a valid Zone
        with pytest.raises(ValidationError):
            SubsectionFinding(**kwargs)

    def test_trend_rejects_unknown_literal(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["trend"] = "unknown"
        with pytest.raises(ValidationError):
            SubsectionFinding(**kwargs)

    def test_subsection_id_rejects_unknown_literal(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["subsection_id"] = "made_up"
        with pytest.raises(ValidationError):
            SubsectionFinding(**kwargs)

    def test_field_order_locked(self) -> None:
        """Field order is locked per the plan action (load-bearing for hash stability)."""
        assert list(SubsectionFinding.model_fields.keys()) == [
            "subsection_id",
            "parent_subsection_id",
            "window",
            "metric",
            "value",
            "zone",
            "trend",
            "weekly_points_in_window",
            "sample_size",
            "sample_quality",
            "is_headline_eligible",
            "dimension",
        ]


class TestEndgameTabFindings:
    """EndgameTabFindings composes filters + findings + flags + hash."""

    def _valid_finding(self) -> SubsectionFinding:
        return SubsectionFinding(
            subsection_id="overall",
            window="all_time",
            metric="score_gap",
            value=0.05,
            zone="typical",
            trend="stable",
            weekly_points_in_window=30,
            sample_size=120,
            sample_quality="adequate",
            is_headline_eligible=True,
        )

    def test_minimal_instantiation(self) -> None:
        findings = EndgameTabFindings(
            as_of=datetime.datetime(2026, 4, 20, 12, 0, 0, tzinfo=datetime.timezone.utc),
            filters=FilterContext(),
            findings=[],
            flags=[],
            findings_hash="",
        )
        assert findings.findings == []
        assert findings.flags == []
        assert findings.findings_hash == ""

    def test_populated(self) -> None:
        fc = FilterContext(recency="3months")
        f = self._valid_finding()
        findings = EndgameTabFindings(
            as_of=datetime.datetime(2026, 4, 20, tzinfo=datetime.timezone.utc),
            filters=fc,
            findings=[f],
            flags=["clock_entry_advantage"],
            findings_hash="0" * 64,
        )
        assert len(findings.findings) == 1
        assert findings.flags == ["clock_entry_advantage"]
        # JSON round-trip works
        payload = json.loads(findings.model_dump_json())
        assert payload["flags"] == ["clock_entry_advantage"]
        assert payload["findings"][0]["subsection_id"] == "overall"

    def test_flag_rejects_unknown_value(self) -> None:
        """An unknown flag string in the flags list triggers ValidationError."""
        with pytest.raises(ValidationError):
            EndgameTabFindings(
                as_of=datetime.datetime(2026, 4, 20, tzinfo=datetime.timezone.utc),
                filters=FilterContext(),
                findings=[],
                flags=["not_a_real_flag"],  # ty: ignore[invalid-argument-type]
                findings_hash="",
            )

    def test_field_order_locked(self) -> None:
        assert list(EndgameTabFindings.model_fields.keys()) == [
            "as_of",
            "filters",
            "findings",
            "flags",
            "findings_hash",
        ]


class TestFlagIdAndSectionId:
    """FlagId and SectionId Literal aliases match CONTEXT.md D-09 and specifics."""

    def test_flag_id_has_exactly_four_values(self) -> None:
        """D-09 locks four cross-section flag IDs."""
        from typing import get_args

        expected = {
            "baseline_lift_mutes_score_gap",
            "clock_entry_advantage",
            "no_clock_entry_advantage",
            "notable_endgame_elo_divergence",
        }
        assert set(get_args(FlagId)) == expected

    def test_section_id_has_exactly_four_values(self) -> None:
        """SectionId enumerates the four Phase 65 prompt sections."""
        from typing import get_args

        expected = {"overall", "metrics_elo", "time_pressure", "type_breakdown"}
        assert set(get_args(SectionId)) == expected


class TestReExportsFromEndgameZones:
    """Zone / Trend / SampleQuality / Window / MetricId / SubsectionId come from endgame_zones."""

    def test_zone_is_endgame_zones_alias(self) -> None:
        from app.services.endgame_zones import Zone as ZoneSource

        assert Zone is ZoneSource

    def test_trend_is_endgame_zones_alias(self) -> None:
        from app.services.endgame_zones import Trend as TrendSource

        assert Trend is TrendSource

    def test_sample_quality_is_endgame_zones_alias(self) -> None:
        from app.services.endgame_zones import SampleQuality as SampleQualitySource

        assert SampleQuality is SampleQualitySource

    def test_window_is_endgame_zones_alias(self) -> None:
        from app.services.endgame_zones import Window as WindowSource

        assert Window is WindowSource

    def test_metric_id_is_endgame_zones_alias(self) -> None:
        from app.services.endgame_zones import MetricId as MetricIdSource

        assert MetricId is MetricIdSource

    def test_subsection_id_is_endgame_zones_alias(self) -> None:
        from app.services.endgame_zones import SubsectionId as SubsectionIdSource

        assert SubsectionId is SubsectionIdSource


class TestModuleAll:
    """__all__ export list covers every public name."""

    def test_all_contains_expected_names(self) -> None:
        from app.schemas import insights

        expected = {
            "EndgameTabFindings",
            "FilterContext",
            "FlagId",
            "MetricId",
            "SampleQuality",
            "SectionId",
            "SubsectionFinding",
            "SubsectionId",
            "Trend",
            "Window",
            "Zone",
        }
        assert set(insights.__all__) == expected


def test_nan_constant_available_for_callers() -> None:
    """Sanity: math.nan is what the service will emit for empty windows."""
    assert math.isnan(float("nan"))
