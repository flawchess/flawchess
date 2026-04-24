"""Tests for the Phase 63 findings-pipeline Pydantic schemas (app/schemas/insights.py).

Covers:
- FilterContext: defaults, Literal validation, field set matches INS-03 spec
- SubsectionFinding: required + optional fields, NaN value round-trip, Literal validation
- EndgameTabFindings: composition, required fields
- SectionId Literal alias matches the Phase 65 prompt sections
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
        """Field order is locked per the plan action (load-bearing for hash stability).

        Phase 65 appended `series` as the final field (D-02). The ordering of
        the first 12 fields is unchanged — only `series` was appended after
        `dimension`.
        """
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
            "series",  # Phase 65 D-02: appended last for findings_hash stability
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
            findings_hash="",
        )
        assert findings.findings == []
        assert findings.findings_hash == ""

    def test_populated(self) -> None:
        fc = FilterContext(recency="3months")
        f = self._valid_finding()
        findings = EndgameTabFindings(
            as_of=datetime.datetime(2026, 4, 20, tzinfo=datetime.timezone.utc),
            filters=fc,
            findings=[f],
            findings_hash="0" * 64,
        )
        assert len(findings.findings) == 1
        payload = json.loads(findings.model_dump_json())
        assert payload["findings"][0]["subsection_id"] == "overall"

    def test_field_order_locked(self) -> None:
        assert list(EndgameTabFindings.model_fields.keys()) == [
            "as_of",
            "filters",
            "findings",
            "time_pressure_chart",
            "overall_performance",
            "type_categories",
            "player_profile",
            "findings_hash",
        ]


class TestSectionIdLiteral:
    """SectionId Literal alias matches the four Phase 65 prompt sections."""

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
            "EndgameInsightsReport",
            "EndgameInsightsResponse",
            "EndgameTabFindings",
            "FilterContext",
            "InsightsError",
            "InsightsErrorResponse",
            "InsightsStatus",
            "MetricId",
            "PlayerProfileEntry",
            "SampleQuality",
            "SectionId",
            "SectionInsight",
            "SubsectionFinding",
            "SubsectionId",
            "TimePoint",
            "Trend",
            "Window",
            "Zone",
        }
        assert set(insights.__all__) == expected


def test_nan_constant_available_for_callers() -> None:
    """Sanity: math.nan is what the service will emit for empty windows."""
    assert math.isnan(float("nan"))


# ---------------------------------------------------------------------------
# Phase 65 schema extension tests
# ---------------------------------------------------------------------------

from typing import Any  # noqa: E402

from app.schemas.insights import (  # noqa: E402
    EndgameInsightsReport,
    EndgameInsightsResponse,
    InsightsErrorResponse,
    SectionInsight,
    TimePoint,
)


class TestTimePoint:
    """Phase 65 D-02: TimePoint schema."""

    def test_round_trip(self) -> None:
        tp = TimePoint(bucket_start="2026-02-03", value=0.42, n=12)
        reloaded = TimePoint.model_validate_json(tp.model_dump_json())
        assert reloaded == tp

    def test_all_fields_required(self) -> None:
        with pytest.raises(ValidationError):
            TimePoint(bucket_start="2026-02-03", value=0.42)  # ty: ignore[missing-argument]


class TestSectionInsight:
    """Phase 65 D-19: SectionInsight shape + length bounds."""

    def test_bullets_default_empty(self) -> None:
        s = SectionInsight(section_id="overall", headline="ok")
        assert s.bullets == []

    def test_bullets_accepts_up_to_5(self) -> None:
        s = SectionInsight(section_id="overall", headline="ok", bullets=["a", "b", "c", "d", "e"])
        assert len(s.bullets) == 5

    def test_bullets_rejects_more_than_5(self) -> None:
        with pytest.raises(ValidationError):
            SectionInsight(
                section_id="overall", headline="ok", bullets=["a", "b", "c", "d", "e", "f"]
            )

    def test_headline_max_length_120(self) -> None:
        with pytest.raises(ValidationError):
            SectionInsight(section_id="overall", headline="x" * 121, bullets=[])

    def test_section_id_literal_enforced(self) -> None:
        with pytest.raises(ValidationError):
            SectionInsight(section_id="invalid", headline="ok")  # ty: ignore[invalid-argument-type]


class TestEndgameInsightsReport:
    """Phase 65 D-17/D-19/D-20 + INS-06: core LLM output schema."""

    def _build_section(self, section_id: SectionId) -> SectionInsight:
        return SectionInsight(section_id=section_id, headline="h", bullets=[])

    _DEFAULT_PROFILE = "Player at 1500 rapid, range 1100-1600 over 2 years, recently stable."
    _DEFAULT_RECS = ["Try drilling pawn endings.", "Review recent losses on time."]

    def test_happy_path(self) -> None:
        r = EndgameInsightsReport(
            player_profile=self._DEFAULT_PROFILE,
            overview="Summary of endgame signals.",
            recommendations=self._DEFAULT_RECS,
            sections=[self._build_section("overall")],
            model_used="test",
            prompt_version="endgame_v1",
        )
        assert r.overview == "Summary of endgame signals."
        assert r.player_profile == self._DEFAULT_PROFILE
        assert r.recommendations == self._DEFAULT_RECS

    def test_sections_min_length_1(self) -> None:
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=self._DEFAULT_RECS,
                sections=[],
                model_used="test",
                prompt_version="endgame_v1",
            )

    def test_sections_max_length_4(self) -> None:
        # "overall" repeated beyond 4 would also fail model_validator; use
        # distinct valid section_ids, then add one invalid 5th via cast.
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=self._DEFAULT_RECS,
                sections=[
                    SectionInsight(section_id="overall", headline="h"),
                    SectionInsight(section_id="metrics_elo", headline="h"),
                    SectionInsight(section_id="time_pressure", headline="h"),
                    SectionInsight(section_id="type_breakdown", headline="h"),
                    SectionInsight(section_id="overall", headline="h"),  # 5th entry
                ],
                model_used="test",
                prompt_version="endgame_v1",
            )

    def test_unique_section_ids_validator(self) -> None:
        """D-20: duplicate section_id raises → pydantic-ai retries upstream."""
        with pytest.raises(ValidationError) as exc_info:
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=self._DEFAULT_RECS,
                sections=[
                    SectionInsight(section_id="overall", headline="h"),
                    SectionInsight(section_id="overall", headline="h"),
                ],
                model_used="test",
                prompt_version="endgame_v1",
            )
        assert "duplicate section_id" in str(exc_info.value)

    def test_overview_empty_string_allowed(self) -> None:
        """INS-06 contract: backend may set overview='' when INSIGHTS_HIDE_OVERVIEW=true (D-18).
        Schema ALLOWS empty string — the always-populate rule is enforced by
        the system prompt, not the schema. Pydantic rejects only NULL.
        """
        r = EndgameInsightsReport(
            player_profile=self._DEFAULT_PROFILE,
            overview="",
            recommendations=self._DEFAULT_RECS,
            sections=[self._build_section("overall")],
            model_used="test",
            prompt_version="endgame_v1",
        )
        assert r.overview == ""

    def test_overview_none_rejected(self) -> None:
        """INS-06: overview is `str`, not `str | None`."""
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview=None,  # ty: ignore[invalid-argument-type]
                recommendations=self._DEFAULT_RECS,
                sections=[self._build_section("overall")],
                model_used="test",
                prompt_version="endgame_v1",
            )

    def test_player_profile_required_non_empty(self) -> None:
        """v9: player_profile is required and must not be empty (min_length=1)."""
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile="",
                overview="x",
                recommendations=self._DEFAULT_RECS,
                sections=[self._build_section("overall")],
                model_used="test",
                prompt_version="endgame_v1",
            )

    def test_recommendations_min_2(self) -> None:
        """v9: recommendations must have at least 2 items."""
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=["only one"],
                sections=[self._build_section("overall")],
                model_used="test",
                prompt_version="endgame_v1",
            )

    def test_recommendations_max_4(self) -> None:
        """v9: recommendations cap at 4 items."""
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=["a", "b", "c", "d", "e"],
                sections=[self._build_section("overall")],
                model_used="test",
                prompt_version="endgame_v1",
            )

    def test_recommendation_empty_string_rejected(self) -> None:
        """v9: each recommendation must be non-empty (validator)."""
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=["valid", "  "],
                sections=[self._build_section("overall")],
                model_used="test",
                prompt_version="endgame_v1",
            )

    def test_recommendation_too_long_rejected(self) -> None:
        """v9: each recommendation must be <= 200 chars."""
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=["valid", "x" * 201],
                sections=[self._build_section("overall")],
                model_used="test",
                prompt_version="endgame_v1",
            )


class TestEndgameInsightsResponse:
    """Phase 65 D-14: HTTP 200 success envelope."""

    def _report(self) -> EndgameInsightsReport:
        return EndgameInsightsReport(
            player_profile="profile",
            overview="x",
            recommendations=["one", "two"],
            sections=[SectionInsight(section_id="overall", headline="h")],
            model_used="test",
            prompt_version="endgame_v1",
        )

    def test_fresh_status(self) -> None:
        resp = EndgameInsightsResponse(report=self._report(), status="fresh")
        assert resp.stale_filters is None
        assert resp.status == "fresh"

    def test_stale_rate_limited_with_filters(self) -> None:
        # Use an actually-valid recency literal:
        filters = FilterContext(recency="3months", opponent_strength="any")
        resp = EndgameInsightsResponse(
            report=self._report(),
            status="stale_rate_limited",
            stale_filters=filters,
        )
        assert resp.stale_filters is not None
        assert resp.stale_filters.recency == "3months"

    def test_status_literal_enforced(self) -> None:
        with pytest.raises(ValidationError):
            EndgameInsightsResponse(report=self._report(), status="bogus")  # ty: ignore[invalid-argument-type]


class TestInsightsErrorResponse:
    """Phase 65 D-15: HTTP 4xx/5xx error envelope."""

    def test_rate_limit_with_retry_after(self) -> None:
        resp = InsightsErrorResponse(error="rate_limit_exceeded", retry_after_seconds=3600)
        assert resp.retry_after_seconds == 3600

    def test_provider_error_no_retry_after(self) -> None:
        resp = InsightsErrorResponse(error="provider_error")
        assert resp.retry_after_seconds is None

    def test_error_literal_enforced(self) -> None:
        with pytest.raises(ValidationError):
            InsightsErrorResponse(error="bogus")  # ty: ignore[invalid-argument-type]


class TestSubsectionFindingSeries:
    """Phase 65 D-02: append-only extension to Phase 63 SubsectionFinding."""

    def _minimal_kwargs(self) -> dict[str, Any]:
        return dict(
            subsection_id="score_timeline",
            window="last_3mo",
            metric="score_gap",
            value=4.2,
            zone="typical",
            trend="stable",
            weekly_points_in_window=12,
            sample_size=487,
            sample_quality="rich",
            is_headline_eligible=True,
        )

    def test_series_default_none(self) -> None:
        f = SubsectionFinding(**self._minimal_kwargs())
        assert f.series is None

    def test_series_populated(self) -> None:
        f = SubsectionFinding(
            **self._minimal_kwargs(),
            series=[TimePoint(bucket_start="2026-02-03", value=4.2, n=12)],
        )
        assert f.series is not None
        assert len(f.series) == 1

    def test_series_declaration_is_last_field(self) -> None:
        """Declaration order is load-bearing for findings_hash stability.

        `series` was APPENDED after `dimension` in Phase 65 — it MUST be the
        last declared field so pre-Phase-65 rows (with no `series` emitted)
        hash identically whether decoded by old or new code.
        """
        fields = list(SubsectionFinding.model_fields.keys())
        assert fields[-1] == "series", (
            f"Expected 'series' as last field for hash stability; got {fields}"
        )
