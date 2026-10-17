"""Tests for the findings-pipeline Pydantic schemas (app/schemas/insights.py).

Covers:
- FilterContext is GONE: the endgame insights take no filters
- SubsectionFinding: required + optional fields, NaN value round-trip, Literal validation
- EndgameTabFindings: composition, required fields
- SectionId Literal alias matches the prompt sections
- Re-exports: Zone, Trend, SampleQuality, Window, MetricId, SubsectionId all come from endgame_zones
"""

import datetime
import json
import math

import pytest
from pydantic import ValidationError

from app.schemas.insights import (
    EndgameTabFindings,
    MetricId,
    RatingAnchorContext,
    SampleQuality,
    SectionId,
    SubsectionFinding,
    SubsectionId,
    Trend,
    Window,
    Zone,
)


class TestFilterContextRemoved:
    """The insights are filter-independent; FilterContext no longer exists."""

    def test_filter_context_is_not_part_of_the_schema_module(self) -> None:
        from app.schemas import insights

        assert not hasattr(insights, "FilterContext")
        assert "FilterContext" not in insights.__all__

    def test_llm_log_filter_context_keeps_its_json_shape(self) -> None:
        """No migration: llm_logs.filter_context still holds {"opponent_strength": ...}."""
        from app.schemas.llm_log import LlmLogFilterContext
        from app.services.insights_llm import INSIGHTS_CACHE_OPPONENT_STRENGTH

        ctx = LlmLogFilterContext(opponent_strength=INSIGHTS_CACHE_OPPONENT_STRENGTH)
        assert ctx.model_dump() == {"opponent_strength": "any"}


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
        """Field order is locked (load-bearing for hash stability).

        `series` is the final field. The ordering of
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
            "series",  # Appended last for findings_hash stability
        ]


class TestEndgameTabFindings:
    """EndgameTabFindings composes findings + the ranked payload + percentile context + hash."""

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
            findings=[],
            findings_hash="",
        )
        assert findings.findings == []
        assert findings.findings_hash == ""

    def test_populated(self) -> None:
        f = self._valid_finding()
        findings = EndgameTabFindings(
            as_of=datetime.datetime(2026, 4, 20, tzinfo=datetime.timezone.utc),
            findings=[f],
            findings_hash="0" * 64,
        )
        assert len(findings.findings) == 1
        payload = json.loads(findings.model_dump_json())
        assert payload["findings"][0]["subsection_id"] == "overall"

    def test_field_order_locked(self) -> None:
        assert list(EndgameTabFindings.model_fields.keys()) == [
            "as_of",
            "findings",
            "player_profile",
            # The all_time ranked payload, appended after player_profile and
            # before findings_hash so the hash stays last (load-bearing for stability).
            "ranked_tcs",
            # Per-TC metric percentiles for Section 2 ΔES-gap +
            # raw-rate + time-pressure metrics, keyed "{metric}:{tc}".
            "per_tc_metric_percentiles",
            # cohort_anchors changed from dict[str, int] to
            # dict[str, RatingAnchorContext] — field position is unchanged.
            "cohort_anchors",
            # Per-(class × TC) type breakdown for the
            # per-TC endgame_type_<tc> subsections. Appended after cohort_anchors,
            # before findings_hash, to preserve findings_hash stability.
            "type_categories_by_tc",
            "findings_hash",
        ]

    def test_ranked_payload_replaces_the_filtered_overview_fields(self) -> None:
        """ranked_tcs is the data source; the filter-era fields are gone."""
        fields = EndgameTabFindings.model_fields
        assert "ranked_tcs" in fields
        for removed in (
            "filters",
            "metric_percentiles",
            "overall_performance",
            "type_categories",
            "time_pressure_chart",
            "time_pressure_cards",
        ):
            assert removed not in fields, f"{removed} must not exist on EndgameTabFindings"

    def test_ranked_tcs_defaults_to_empty_and_round_trips(self) -> None:
        from tests.services.ranked_payload_fixtures import make_ranked_tc

        empty = EndgameTabFindings(
            as_of=datetime.datetime(2026, 4, 20, tzinfo=datetime.timezone.utc),
            findings=[],
            findings_hash="",
        )
        assert empty.ranked_tcs == []

        populated = empty.model_copy(update={"ranked_tcs": [make_ranked_tc("blitz")]})
        restored = EndgameTabFindings.model_validate_json(populated.model_dump_json())
        assert [t.tc for t in restored.ranked_tcs] == ["blitz"]
        assert restored.ranked_tcs[0].metrics["score_gap"].value == pytest.approx(0.05)


class TestSectionIdLiteral:
    """SectionId Literal alias matches the four prompt sections."""

    def test_section_id_has_exactly_four_values(self) -> None:
        """SectionId enumerates the four prompt sections."""
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
            "InsightsError",
            "InsightsErrorResponse",
            "InsightsStatus",
            "MetricId",
            "MetricPercentileRecord",
            "PlayerProfileEntry",
            "RatingAnchorContext",
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


class TestRatingAnchorContext:
    """RatingAnchorContext carries platform-composition disclosure."""

    def test_basic_construction(self) -> None:
        ctx = RatingAnchorContext(
            anchor_rating=1550,
            n_chesscom_games=320,
            n_lichess_games=0,
            chesscom_median_native=1400,
        )
        assert ctx.anchor_rating == 1550
        assert ctx.n_chesscom_games == 320
        assert ctx.n_lichess_games == 0
        assert ctx.chesscom_median_native == 1400
        assert ctx.lichess_median_native is None

    def test_pure_lichess(self) -> None:
        ctx = RatingAnchorContext(
            anchor_rating=1620,
            n_chesscom_games=0,
            n_lichess_games=450,
            lichess_median_native=1620,
        )
        assert ctx.n_chesscom_games == 0
        assert ctx.n_lichess_games == 450
        assert ctx.chesscom_median_native is None

    def test_mixed_user(self) -> None:
        ctx = RatingAnchorContext(
            anchor_rating=1580,
            n_chesscom_games=200,
            n_lichess_games=300,
            chesscom_median_native=1410,
            lichess_median_native=1600,
        )
        assert ctx.chesscom_median_native == 1410
        assert ctx.lichess_median_native == 1600

    def test_cohort_anchors_in_findings_carries_rating_anchor_context(self) -> None:
        """EndgameTabFindings.cohort_anchors accepts dict[str, RatingAnchorContext]."""
        ctx = RatingAnchorContext(
            anchor_rating=1550,
            n_chesscom_games=320,
            n_lichess_games=0,
            chesscom_median_native=1400,
        )
        findings = EndgameTabFindings(
            as_of=datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc),
            findings=[],
            cohort_anchors={"blitz": ctx},
            findings_hash="",
        )
        assert findings.cohort_anchors is not None
        assert "blitz" in findings.cohort_anchors
        anchor = findings.cohort_anchors["blitz"]
        assert isinstance(anchor, RatingAnchorContext)
        assert anchor.anchor_rating == 1550
        assert anchor.chesscom_median_native == 1400


# ---------------------------------------------------------------------------
# Schema extension tests
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
    """TimePoint schema."""

    def test_round_trip(self) -> None:
        tp = TimePoint(bucket_start="2026-02-03", value=0.42, n=12)
        reloaded = TimePoint.model_validate_json(tp.model_dump_json())
        assert reloaded == tp

    def test_all_fields_required(self) -> None:
        with pytest.raises(ValidationError):
            TimePoint(bucket_start="2026-02-03", value=0.42)  # ty: ignore[missing-argument]


class TestSectionInsight:
    """SectionInsight shape + length bounds."""

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
    """Core LLM output schema."""

    def _build_section(self, section_id: SectionId) -> SectionInsight:
        return SectionInsight(section_id=section_id, headline="h", bullets=[])

    _DEFAULT_PROFILE = "Player at 1500 rapid, range 1100-1600 over 2 years, recently stable."
    _DEFAULT_RECS = ["Try drilling pawn endings.", "Review recent losses on time."]

    def test_happy_path(self) -> None:
        r = EndgameInsightsReport(
            summary="Endgames lift your rating; rook endings need work.",
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
                summary="Endgames lift your rating; rook endings need work.",
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
                summary="Endgames lift your rating; rook endings need work.",
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
        """Duplicate section_id raises → pydantic-ai retries upstream."""
        with pytest.raises(ValidationError) as exc_info:
            EndgameInsightsReport(
                summary="Endgames lift your rating; rook endings need work.",
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
        """Backend may set overview='' when INSIGHTS_HIDE_OVERVIEW=true.
        Schema ALLOWS empty string — the always-populate rule is enforced by
        the system prompt, not the schema. Pydantic rejects only NULL.
        """
        r = EndgameInsightsReport(
            summary="Endgames lift your rating; rook endings need work.",
            player_profile=self._DEFAULT_PROFILE,
            overview="",
            recommendations=self._DEFAULT_RECS,
            sections=[self._build_section("overall")],
            model_used="test",
            prompt_version="endgame_v1",
        )
        assert r.overview == ""

    def test_overview_none_rejected(self) -> None:
        """Overview is `str`, not `str | None`."""
        with pytest.raises(ValidationError):
            EndgameInsightsReport(
                summary="Endgames lift your rating; rook endings need work.",
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
                summary="Endgames lift your rating; rook endings need work.",
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
                summary="Endgames lift your rating; rook endings need work.",
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
                summary="Endgames lift your rating; rook endings need work.",
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
                summary="Endgames lift your rating; rook endings need work.",
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
                summary="Endgames lift your rating; rook endings need work.",
                player_profile=self._DEFAULT_PROFILE,
                overview="x",
                recommendations=["valid", "x" * 201],
                sections=[self._build_section("overall")],
                model_used="test",
                prompt_version="endgame_v1",
            )


class TestEndgameInsightsResponse:
    """HTTP 200 success envelope."""

    def _report(self) -> EndgameInsightsReport:
        return EndgameInsightsReport(
            summary="Endgames lift your rating; rook endings need work.",
            player_profile="profile",
            overview="x",
            recommendations=["one", "two"],
            sections=[SectionInsight(section_id="overall", headline="h")],
            model_used="test",
            prompt_version="endgame_v1",
        )

    def test_fresh_status(self) -> None:
        resp = EndgameInsightsResponse(report=self._report(), status="fresh")
        assert resp.status == "fresh"

    def test_cache_hit_status(self) -> None:
        resp = EndgameInsightsResponse(report=self._report(), status="cache_hit")
        assert resp.status == "cache_hit"

    def test_status_literal_enforced(self) -> None:
        with pytest.raises(ValidationError):
            EndgameInsightsResponse(report=self._report(), status="bogus")  # ty: ignore[invalid-argument-type]


class TestInsightsErrorResponse:
    """HTTP 502 error envelope."""

    def test_provider_error(self) -> None:
        resp = InsightsErrorResponse(error="provider_error")
        assert resp.error == "provider_error"

    def test_validation_failure(self) -> None:
        resp = InsightsErrorResponse(error="validation_failure")
        assert resp.error == "validation_failure"

    def test_error_literal_enforced(self) -> None:
        with pytest.raises(ValidationError):
            InsightsErrorResponse(error="bogus")  # ty: ignore[invalid-argument-type]


class TestSubsectionFindingSeries:
    """Append-only extension to SubsectionFinding."""

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

        `series` was APPENDED after `dimension` — it MUST be the
        last declared field so older rows (with no `series` emitted)
        hash identically whether decoded by old or new code.
        """
        fields = list(SubsectionFinding.model_fields.keys())
        assert fields[-1] == "series", (
            f"Expected 'series' as last field for hash stability; got {fields}"
        )
