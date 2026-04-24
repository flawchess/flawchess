"""Tests for series resampling helpers in app/services/insights_service.py (Phase 65 Plan 03).

Coverage:
- D-02: SubsectionFinding.series populated for the 4 timeline subsections only.
- D-03: last_3mo → weekly pass-through; all_time → monthly weighted-by-n mean.
- D-04: Endgame ELO gap-only + sparse-combo filter (SPARSE_COMBO_FLOOR = 10).
- D-05: type_win_rate_timeline uses monthly for BOTH all_time AND last_3mo windows.

All tests run against synthetic Pydantic instances — zero DB access.
"""

from __future__ import annotations

import re
from typing import Literal
from unittest.mock import AsyncMock, patch

import pytest

import app.services.insights_service as insights_module
from app.schemas.endgames import (
    ConversionRecoveryStats,
    EndgameEloTimelineCombo,
    EndgameEloTimelinePoint,
    EndgameOverviewResponse,
)
from app.schemas.insights import (
    FilterContext,
)
from app.services.insights_service import (
    SPARSE_COMBO_FLOOR,
    _series_for_endgame_elo_combo,
    _weekly_points_to_time_points,
    compute_findings,
)

# ---------------------------------------------------------------------------
# TestResample — D-03 resampling helper unit tests.
# ---------------------------------------------------------------------------


class TestResample:
    """Unit tests for _weekly_points_to_time_points."""

    def test_monthly_weighted_mean(self) -> None:
        """4 weekly points in Feb 2026 → 1 monthly TimePoint with weighted mean."""
        weekly: list[tuple[str, float, int]] = [
            ("2026-02-03", 0.5, 10),
            ("2026-02-10", 0.6, 20),
            ("2026-02-17", 0.4, 10),
            ("2026-02-24", 0.7, 10),
        ]
        result = _weekly_points_to_time_points(weekly, "all_time")
        assert len(result) == 1
        point = result[0]
        assert point.bucket_start == "2026-02-01"
        # weighted mean = (0.5*10 + 0.6*20 + 0.4*10 + 0.7*10) / 50
        #               = (5 + 12 + 4 + 7) / 50 = 28/50 = 0.56
        assert point.value == pytest.approx(0.56, rel=1e-3)
        assert point.n == 50

    def test_last_3mo_pass_through(self) -> None:
        """last_3mo window: weekly points are passed through as-is, sorted by date."""
        weekly: list[tuple[str, float, int]] = [
            ("2026-02-17", 0.4, 10),
            ("2026-02-03", 0.5, 5),
            ("2026-02-10", 0.6, 20),
            ("2026-02-24", 0.7, 8),
            ("2026-03-03", 0.3, 15),
        ]
        result = _weekly_points_to_time_points(weekly, "last_3mo")
        assert len(result) == 5
        # Should be sorted by date
        dates = [p.bucket_start for p in result]
        assert dates == sorted(dates)
        # Values preserved exactly
        result_values = {p.bucket_start: (p.value, p.n) for p in result}
        assert result_values["2026-02-03"] == (0.5, 5)
        assert result_values["2026-02-10"] == (0.6, 20)
        assert result_values["2026-02-17"] == (0.4, 10)
        assert result_values["2026-02-24"] == (0.7, 8)
        assert result_values["2026-03-03"] == (0.3, 15)

    def test_monthly_single_week(self) -> None:
        """Single weekly point in all_time → 1 monthly TimePoint with same value and n."""
        weekly: list[tuple[str, float, int]] = [("2025-06-16", 0.55, 30)]
        result = _weekly_points_to_time_points(weekly, "all_time")
        assert len(result) == 1
        assert result[0].bucket_start == "2025-06-01"
        assert result[0].value == pytest.approx(0.55)
        assert result[0].n == 30

    def test_monthly_key_format(self) -> None:
        """all_time bucket_start must match YYYY-MM-01 format."""
        weekly: list[tuple[str, float, int]] = [
            ("2026-01-05", 0.5, 10),
            ("2026-03-10", 0.6, 20),
        ]
        result = _weekly_points_to_time_points(weekly, "all_time")
        for point in result:
            assert re.match(r"^\d{4}-\d{2}-01$", point.bucket_start), (
                f"bucket_start {point.bucket_start!r} does not match YYYY-MM-01"
            )

    def test_empty_input_all_time(self) -> None:
        """Empty input returns empty list for all_time window."""
        result = _weekly_points_to_time_points([], "all_time")
        assert result == []

    def test_empty_input_last_3mo(self) -> None:
        """Empty input returns empty list for last_3mo window."""
        result = _weekly_points_to_time_points([], "last_3mo")
        assert result == []

    def test_all_zero_n_fallback(self) -> None:
        """All-zero-n weeks fall back to arithmetic mean with n=0, point still emitted."""
        weekly: list[tuple[str, float, int]] = [
            ("2026-02-03", 0.4, 0),
            ("2026-02-10", 0.6, 0),
        ]
        result = _weekly_points_to_time_points(weekly, "all_time")
        assert len(result) == 1
        assert result[0].n == 0
        # arithmetic mean of 0.4 and 0.6 = 0.5
        assert result[0].value == pytest.approx(0.5)
        # bucket key is still YYYY-MM-01
        assert result[0].bucket_start == "2026-02-01"

    def test_monthly_multiple_months(self) -> None:
        """Points spanning multiple months produce one TimePoint per month, sorted."""
        weekly: list[tuple[str, float, int]] = [
            ("2026-01-05", 0.3, 10),
            ("2026-02-02", 0.5, 20),
            ("2026-02-09", 0.7, 20),
        ]
        result = _weekly_points_to_time_points(weekly, "all_time")
        assert len(result) == 2
        assert result[0].bucket_start == "2026-01-01"
        assert result[0].n == 10
        assert result[1].bucket_start == "2026-02-01"
        # weighted mean for Feb: (0.5*20 + 0.7*20) / 40 = 0.6
        assert result[1].value == pytest.approx(0.6)
        assert result[1].n == 40


# ---------------------------------------------------------------------------
# TestEloCombo — D-04 gap-only + sparse-combo filter.
# ---------------------------------------------------------------------------


def _make_elo_combo(
    n_points: int,
    endgame_elo: int = 1500,
    actual_elo: int = 1400,
    platform: "Literal['chess.com', 'lichess']" = "chess.com",
    time_control: "Literal['bullet', 'blitz', 'rapid', 'classical']" = "blitz",
) -> EndgameEloTimelineCombo:
    """Build a synthetic EndgameEloTimelineCombo with n_points weekly points."""
    points: list[EndgameEloTimelinePoint] = [
        EndgameEloTimelinePoint(
            date=f"2026-01-{i + 1:02d}",
            endgame_elo=endgame_elo,
            actual_elo=actual_elo,
            endgame_games_in_window=50,
            per_week_endgame_games=5,
        )
        for i in range(n_points)
    ]
    return EndgameEloTimelineCombo(
        combo_key=f"{platform.replace('.', '_')}_{time_control}",
        platform=platform,
        time_control=time_control,
        points=points,
    )


class TestEloCombo:
    """Unit tests for _series_for_endgame_elo_combo."""

    def test_gap_only_series(self) -> None:
        """Gap value = endgame_elo - actual_elo for each point (D-04)."""
        combo = _make_elo_combo(10, endgame_elo=1500, actual_elo=1400)
        result = _series_for_endgame_elo_combo(combo, "last_3mo")
        assert result is not None
        for point in result:
            assert point.value == pytest.approx(100.0)  # 1500 - 1400 = 100

    def test_sparse_combo_skipped(self) -> None:
        """Combo with 9 points (< SPARSE_COMBO_FLOOR=10) returns None."""
        combo = _make_elo_combo(SPARSE_COMBO_FLOOR - 1)
        result = _series_for_endgame_elo_combo(combo, "last_3mo")
        assert result is None

    def test_threshold_boundary(self) -> None:
        """Combo with exactly SPARSE_COMBO_FLOOR=10 points returns a list, not None."""
        combo = _make_elo_combo(SPARSE_COMBO_FLOOR)
        result = _series_for_endgame_elo_combo(combo, "last_3mo")
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == SPARSE_COMBO_FLOOR

    def test_gap_negative_value(self) -> None:
        """Negative gap (actual_elo > endgame_elo) produces negative TimePoint value."""
        combo = _make_elo_combo(10, endgame_elo=1300, actual_elo=1400)
        result = _series_for_endgame_elo_combo(combo, "last_3mo")
        assert result is not None
        for point in result:
            assert point.value == pytest.approx(-100.0)

    def test_combo_n_field_uses_per_week_endgame_games(self) -> None:
        """TimePoint.n comes from per_week_endgame_games, not endgame_games_in_window."""
        combo = _make_elo_combo(10, endgame_elo=1500, actual_elo=1400)
        result = _series_for_endgame_elo_combo(combo, "last_3mo")
        assert result is not None
        for point in result:
            assert point.n == 5  # per_week_endgame_games from _make_elo_combo


# ---------------------------------------------------------------------------
# TestTypeTimeline — D-05: type_win_rate_timeline uses monthly for both windows.
# ---------------------------------------------------------------------------


class TestTypeTimeline:
    """Unit tests for D-05: type_win_rate monthly for both windows."""

    def test_monthly_both_windows(self) -> None:
        """Calling _weekly_points_to_time_points with 'all_time' always gives monthly."""
        # Multiple weeks within the same month
        weekly: list[tuple[str, float, int]] = [
            ("2026-02-03", 0.5, 10),
            ("2026-02-10", 0.6, 10),
        ]
        result_all_time = _weekly_points_to_time_points(weekly, "all_time")
        # Should collapse to 1 monthly bucket
        assert len(result_all_time) == 1
        assert result_all_time[0].bucket_start == "2026-02-01"

        # Calling with last_3mo gives weekly (pass-through)
        result_last_3mo = _weekly_points_to_time_points(weekly, "last_3mo")
        assert len(result_last_3mo) == 2


# ---------------------------------------------------------------------------
# Integration helpers — build a minimal EndgameOverviewResponse.
# ---------------------------------------------------------------------------


def _make_minimal_response() -> EndgameOverviewResponse:
    """Build a minimal valid EndgameOverviewResponse for integration tests.

    Uses model_construct to bypass field requirements for non-tested fields.
    Supplies the minimal fields that compute_findings reads.
    """
    from app.schemas.endgames import (
        ClockPressureResponse,
        ClockPressureTimelinePoint,
        EndgameCategoryStats,
        EndgameEloTimelineResponse,
        EndgamePerformanceResponse,
        EndgameStatsResponse,
        EndgameTimelineResponse,
        EndgameWDLSummary,
        ScoreGapMaterialResponse,
        ScoreGapTimelinePoint,
        TimePressureChartResponse,
    )

    wdl = EndgameWDLSummary(
        wins=50, draws=10, losses=40, total=100,
        win_pct=50.0, draw_pct=10.0, loss_pct=40.0,
    )
    performance = EndgamePerformanceResponse(
        endgame_wdl=wdl,
        non_endgame_wdl=wdl,
        endgame_win_rate=50.0,
    )
    stats = EndgameStatsResponse(
        categories=[
            EndgameCategoryStats(
                endgame_class="rook",
                label="Rook",
                wins=20, draws=5, losses=15, total=40,
                win_pct=50.0, draw_pct=12.5, loss_pct=37.5,
                conversion=_make_conv_stats(),
            ),
        ],
        total_games=200,
        endgame_games=100,
    )
    # Score gap timeline with enough weekly points to test resampling.
    # Phase 68: endgame_score / non_endgame_score satisfy
    # score_difference == endgame_score - non_endgame_score.
    score_gap_timeline = [
        ScoreGapTimelinePoint(
            date=f"2026-01-{i + 4:02d}",
            score_difference=0.05 * (i + 1),
            endgame_game_count=10,
            non_endgame_game_count=10,
            per_week_total_games=20,
            endgame_score=round(0.50 + 0.05 * (i + 1), 4),
            non_endgame_score=0.50,
        )
        for i in range(13)  # 13 weekly points for last_3mo
    ]
    score_gap_material = ScoreGapMaterialResponse(
        endgame_score=0.55,
        non_endgame_score=0.50,
        score_difference=0.05,
        material_rows=[],
        timeline=score_gap_timeline,
        timeline_window=50,
    )
    # Clock pressure timeline
    clock_timeline = [
        ClockPressureTimelinePoint(
            date=f"2026-01-{i + 4:02d}",
            avg_clock_diff_pct=float(i + 1),
            game_count=10,
            per_week_game_count=10,
        )
        for i in range(13)
    ]
    clock_pressure = ClockPressureResponse(
        rows=[],
        total_clock_games=130,
        total_endgame_games=130,
        timeline=clock_timeline,
        timeline_window=50,
    )
    time_pressure_chart = TimePressureChartResponse(
        user_series=[],
        opp_series=[],
        total_endgame_games=0,
    )
    # ELO timeline with >=10 points per combo
    elo_combo = EndgameEloTimelineCombo(
        combo_key="chess_com_blitz",
        platform="chess.com",
        time_control="blitz",
        points=[
            EndgameEloTimelinePoint(
                date=f"2026-01-{i + 4:02d}",
                endgame_elo=1500,
                actual_elo=1400,
                endgame_games_in_window=50,
                per_week_endgame_games=5,
            )
            for i in range(13)
        ],
    )
    elo_timeline = EndgameEloTimelineResponse(combos=[elo_combo], timeline_window=50)
    # Type timeline with per_type data
    from app.schemas.endgames import EndgameTimelinePoint

    type_timeline = EndgameTimelineResponse(
        overall=[],
        per_type={
            "rook": [
                EndgameTimelinePoint(
                    date=f"2026-01-{i + 4:02d}",
                    win_rate=0.5,
                    game_count=10,
                    per_week_game_count=10,
                )
                for i in range(13)
            ],
        },
        window=50,
    )
    return EndgameOverviewResponse(
        stats=stats,
        performance=performance,
        timeline=type_timeline,
        score_gap_material=score_gap_material,
        clock_pressure=clock_pressure,
        time_pressure_chart=time_pressure_chart,
        endgame_elo_timeline=elo_timeline,
    )


def _make_conv_stats() -> ConversionRecoveryStats:
    return ConversionRecoveryStats(
        conversion_pct=60.0,
        conversion_games=20,
        conversion_wins=12,
        conversion_draws=2,
        conversion_losses=6,
        recovery_pct=40.0,
        recovery_games=20,
        recovery_saves=8,
        recovery_wins=5,
        recovery_draws=3,
    )


# ---------------------------------------------------------------------------
# TestIntegration — D-02 end-to-end: compute_findings populates series only
# for the 4 timeline subsections.
# ---------------------------------------------------------------------------

_TIMELINE_SUBSECTION_IDS: frozenset[str] = frozenset({
    "score_timeline",
    "clock_diff_timeline",
    "endgame_elo_timeline",
    "type_win_rate_timeline",
})


class TestIntegration:
    """Integration tests for compute_findings series population (D-02)."""

    @pytest.mark.asyncio
    async def test_compute_findings_populates_series_only_for_timelines(self) -> None:
        """series is not None exactly for the 4 timeline subsection_ids (D-02)."""
        mock_response = _make_minimal_response()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await compute_findings(
                FilterContext(), session=AsyncMock(), user_id=1,
            )

        timeline_with_series = {
            f.subsection_id
            for f in result.findings
            if f.series is not None
        }
        non_timeline_with_series = [
            f for f in result.findings
            if f.subsection_id not in _TIMELINE_SUBSECTION_IDS and f.series is not None
        ]

        # All 4 timeline subsections must have series populated
        assert "score_timeline" in timeline_with_series, (
            "score_timeline should have series populated"
        )
        assert "clock_diff_timeline" in timeline_with_series, (
            "clock_diff_timeline should have series populated"
        )
        assert "endgame_elo_timeline" in timeline_with_series, (
            "endgame_elo_timeline should have series populated"
        )
        assert "type_win_rate_timeline" in timeline_with_series, (
            "type_win_rate_timeline should have series populated"
        )
        # Non-timeline findings must NOT have series
        assert non_timeline_with_series == [], (
            f"Non-timeline findings with series: "
            f"{[f.subsection_id for f in non_timeline_with_series]}"
        )

    @pytest.mark.asyncio
    async def test_type_win_rate_monthly_for_last_3mo(self) -> None:
        """D-05: type_win_rate_timeline series has monthly bucket_starts even for last_3mo."""
        mock_response = _make_minimal_response()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await compute_findings(
                FilterContext(), session=AsyncMock(), user_id=1,
            )

        # Find type_win_rate_timeline findings for last_3mo window
        type_timeline_findings = [
            f for f in result.findings
            if f.subsection_id == "type_win_rate_timeline"
            and f.window == "last_3mo"
            and f.series is not None
        ]

        assert len(type_timeline_findings) > 0, (
            "Expected at least one type_win_rate_timeline finding for last_3mo with series"
        )
        for finding in type_timeline_findings:
            assert finding.series is not None
            for point in finding.series:
                assert re.match(r"^\d{4}-\d{2}-01$", point.bucket_start), (
                    f"type_win_rate_timeline last_3mo bucket_start {point.bucket_start!r} "
                    f"should be monthly (YYYY-MM-01) per D-05"
                )

    @pytest.mark.asyncio
    async def test_score_timeline_emits_two_findings_per_window(self) -> None:
        """Phase 68 B4c: score_timeline emits TWO findings per window (one per `part`).

        Each finding carries its own per-side absolute-score series. Both
        findings share metric='score_gap' and value=aggregate score_difference;
        they're distinguished by dimension={'part': 'endgame'|'non_endgame'}.
        The endgame finding emits first (deterministic order).
        """
        mock_response = _make_minimal_response()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await compute_findings(
                FilterContext(), session=AsyncMock(), user_id=1,
            )

        for window in ("all_time", "last_3mo"):
            st_findings = [
                f for f in result.findings
                if f.subsection_id == "score_timeline" and f.window == window
            ]
            assert len(st_findings) == 2, (
                f"Expected exactly 2 score_timeline findings for window={window}, "
                f"got {len(st_findings)}"
            )
            # Order: endgame first, then non_endgame.
            assert st_findings[0].dimension == {"part": "endgame"}
            assert st_findings[1].dimension == {"part": "non_endgame"}
            # Both share metric=score_gap.
            for f in st_findings:
                assert f.metric == "score_gap"
                assert f.series is not None
                assert len(f.series) > 0
            # Non-endgame is NEVER headline-eligible on its own.
            assert st_findings[1].is_headline_eligible is False

    @pytest.mark.asyncio
    async def test_score_timeline_series_uses_absolute_per_side_values(self) -> None:
        """Phase 68: endgame finding series values come from endgame_score,
        non_endgame finding series values come from non_endgame_score.

        Identity invariant: for matching buckets,
        abs((endgame_value - non_endgame_value) - score_difference) < 1e-9.
        """
        mock_response = _make_minimal_response()
        timeline = mock_response.score_gap_material.timeline
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await compute_findings(
                FilterContext(), session=AsyncMock(), user_id=1,
            )

        st_last_3mo = [
            f for f in result.findings
            if f.subsection_id == "score_timeline" and f.window == "last_3mo"
        ]
        assert len(st_last_3mo) == 2
        endgame_f, non_endgame_f = st_last_3mo
        assert endgame_f.series is not None
        assert non_endgame_f.series is not None
        # Series length matches the source timeline (weekly pass-through).
        assert len(endgame_f.series) == len(timeline)
        assert len(non_endgame_f.series) == len(timeline)
        # Values come directly from endgame_score / non_endgame_score.
        for pt, src in zip(endgame_f.series, timeline, strict=True):
            assert pt.value == pytest.approx(src.endgame_score)
        for pt, src in zip(non_endgame_f.series, timeline, strict=True):
            assert pt.value == pytest.approx(src.non_endgame_score)
        # Identity invariant per bucket.
        for eg_pt, neg_pt, src in zip(
            endgame_f.series, non_endgame_f.series, timeline, strict=True,
        ):
            assert abs((eg_pt.value - neg_pt.value) - src.score_difference) < 1e-9
