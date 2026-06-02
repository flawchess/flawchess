"""Tests for series resampling helpers in app/services/insights_service.py (Phase 65 Plan 03).

Coverage:
- D-02: SubsectionFinding.series populated for the 3 timeline subsections only
  (type_win_rate_timeline removed in 260501-s0u).
- D-03: last_3mo → weekly pass-through; all_time → monthly weighted-by-n mean.
- D-04: Endgame ELO gap-only + sparse-combo filter (SPARSE_COMBO_FLOOR = 10).

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
    """Build a synthetic EndgameEloTimelineCombo with n_points weekly points.

    Phase 87.5 (D-06): parameter name restored to endgame_elo in lockstep
    with the renamed Pydantic field.
    """
    points: list[EndgameEloTimelinePoint] = [
        EndgameEloTimelinePoint(
            date=f"2026-01-{i + 1:02d}",
            endgame_elo=endgame_elo,
            non_endgame_elo=actual_elo,
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
# TestSeriesForEndgameEloComboPRFields — Phase 87.6 PR field threading.
# ---------------------------------------------------------------------------


def _make_elo_combo_with_pr(
    points_data: list[tuple[int, int, int]],
    platform: "Literal['chess.com', 'lichess']" = "chess.com",
    time_control: "Literal['bullet', 'blitz', 'rapid', 'classical']" = "blitz",
) -> EndgameEloTimelineCombo:
    """Build an EndgameEloTimelineCombo from (endgame_elo, non_endgame_elo, actual_elo) tuples.

    Phase 87.6: local fixture builder for PR-field threading tests. Each tuple
    represents one weekly bucket with distinct endgame_elo / non_endgame_elo /
    actual_elo values so tests can assert per-field pass-through independence.
    """
    points: list[EndgameEloTimelinePoint] = [
        EndgameEloTimelinePoint(
            date=f"2026-01-{i + 1:02d}",
            endgame_elo=endgame_elo,
            non_endgame_elo=non_endgame_elo,
            actual_elo=actual_elo,
            endgame_games_in_window=100,
            per_week_endgame_games=10,
        )
        for i, (endgame_elo, non_endgame_elo, actual_elo) in enumerate(points_data)
    ]
    return EndgameEloTimelineCombo(
        combo_key=f"{platform.replace('.', '_')}_{time_control}",
        platform=platform,
        time_control=time_control,
        points=points,
    )


class TestSeriesForEndgameEloComboPRFields:
    """Phase 87.6: asserts endgame_elo + non_endgame_elo thread through to TimePoints.

    RED gate: tests fail until Task 2 adds the two optional fields to TimePoint
    and extends the 4-tuple wiring to a 6-tuple in the service layer.
    """

    def test_emits_endgame_and_non_endgame_elo_per_timepoint(self) -> None:
        """last_3mo window passes both PR fields through per-point.

        10-point combo (SPARSE_COMBO_FLOOR boundary) with distinct
        (endgame_elo, non_endgame_elo, actual_elo) values per point.
        Asserts exact pass-through: no rounding, no cross-field bleed.
        """
        # 10 points: alternating lifting / lagging pattern
        points_data = [
            (1700, 1650, 1675),  # endgame lifts: 1700 > 1650
            (1700, 1750, 1725),  # endgame lags: 1700 < 1750
            (1750, 1700, 1725),  # endgame lifts: 1750 > 1700
            (1720, 1680, 1700),  # endgame lifts
            (1680, 1720, 1700),  # endgame lags
            (1760, 1740, 1750),  # endgame lifts slightly
            (1730, 1770, 1750),  # endgame lags slightly
            (1800, 1780, 1790),  # endgame lifts
            (1780, 1800, 1790),  # endgame lags
            (1790, 1790, 1790),  # endgame neutral
        ]
        combo = _make_elo_combo_with_pr(points_data)
        result = _series_for_endgame_elo_combo(combo, "last_3mo")
        assert result is not None
        assert len(result) == 10
        for tp, (eg_elo, neg_elo, act_elo) in zip(result, points_data, strict=True):
            assert tp.endgame_elo == eg_elo, (
                f"endgame_elo mismatch at bucket {tp.bucket_start}: "
                f"expected {eg_elo}, got {tp.endgame_elo}"
            )
            assert tp.non_endgame_elo == neg_elo, (
                f"non_endgame_elo mismatch at bucket {tp.bucket_start}: "
                f"expected {neg_elo}, got {tp.non_endgame_elo}"
            )
            assert tp.actual_elo == act_elo, (
                f"actual_elo mismatch at bucket {tp.bucket_start}: "
                f"expected {act_elo}, got {tp.actual_elo}"
            )

    def test_all_time_window_aggregates_both_pr_fields(self) -> None:
        """all_time window computes weighted mean for endgame_elo and non_endgame_elo.

        10-point combo (SPARSE_COMBO_FLOOR boundary) spanning 2 months (Jan
        2026 and Feb 2026). The 4 data-bearing points carry per_week_endgame_games
        > 0; 6 filler points carry per_week_endgame_games=0 so they do not
        affect weighted means but do satisfy the SPARSE_COMBO_FLOOR=10 gate.
        Asserts weighted mean of both PR fields per month bucket.
        """
        points: list[EndgameEloTimelinePoint] = [
            EndgameEloTimelinePoint(
                date="2026-01-05",
                endgame_elo=1700,
                non_endgame_elo=1660,
                actual_elo=1680,
                endgame_games_in_window=100,
                per_week_endgame_games=10,
            ),
            EndgameEloTimelinePoint(
                date="2026-01-12",
                endgame_elo=1720,
                non_endgame_elo=1680,
                actual_elo=1700,
                endgame_games_in_window=100,
                per_week_endgame_games=10,
            ),
            EndgameEloTimelinePoint(
                date="2026-02-02",
                endgame_elo=1730,
                non_endgame_elo=1690,
                actual_elo=1710,
                endgame_games_in_window=100,
                per_week_endgame_games=5,
            ),
            EndgameEloTimelinePoint(
                date="2026-02-09",
                endgame_elo=1750,
                non_endgame_elo=1710,
                actual_elo=1730,
                endgame_games_in_window=100,
                per_week_endgame_games=15,
            ),
            # 6 filler points to satisfy SPARSE_COMBO_FLOOR=10; n=0 so they
            # do not contribute to weighted means (statistics.mean path is
            # guarded by total_n == 0, which cannot happen here since the 4
            # data points already contribute positive weights).
            *[
                EndgameEloTimelinePoint(
                    date=f"2026-01-{19 + i}",
                    endgame_elo=1710,
                    non_endgame_elo=1670,
                    actual_elo=1690,
                    endgame_games_in_window=0,
                    per_week_endgame_games=0,
                )
                for i in range(6)
            ],
        ]
        combo = EndgameEloTimelineCombo(
            combo_key="chess_com_blitz",
            platform="chess.com",
            time_control="blitz",
            points=points,
        )
        result = _series_for_endgame_elo_combo(combo, "all_time")
        assert result is not None
        assert len(result) == 2  # Jan and Feb monthly buckets

        jan_point, feb_point = result
        assert jan_point.bucket_start == "2026-01-01"
        assert feb_point.bucket_start == "2026-02-01"

        # Jan: equal weights (n=10, n=10); simple mean
        expected_jan_eg = round((1700 * 10 + 1720 * 10) / 20)
        expected_jan_neg = round((1660 * 10 + 1680 * 10) / 20)
        assert jan_point.endgame_elo == expected_jan_eg, (
            f"Jan endgame_elo: expected {expected_jan_eg}, got {jan_point.endgame_elo}"
        )
        assert jan_point.non_endgame_elo == expected_jan_neg, (
            f"Jan non_endgame_elo: expected {expected_jan_neg}, got {jan_point.non_endgame_elo}"
        )

        # Feb: n=5 and n=15 (total=20); weighted mean
        expected_feb_eg = round((1730 * 5 + 1750 * 15) / 20)
        expected_feb_neg = round((1690 * 5 + 1710 * 15) / 20)
        assert feb_point.endgame_elo == expected_feb_eg, (
            f"Feb endgame_elo: expected {expected_feb_eg}, got {feb_point.endgame_elo}"
        )
        assert feb_point.non_endgame_elo == expected_feb_neg, (
            f"Feb non_endgame_elo: expected {expected_feb_neg}, got {feb_point.non_endgame_elo}"
        )

    def test_other_timeline_series_have_none_for_pr_fields(self) -> None:
        """Gating contract: only endgame_elo_timeline populates PR fields.

        TimePoint instances constructed directly (not via _series_for_endgame_elo_combo)
        default both PR fields to None. Any other timeline series (score, clock, etc.)
        that constructs TimePoints without the PR fields must have None for both.
        """
        from app.schemas.insights import TimePoint

        # Direct construction without PR fields mirrors what every other series helper does.
        tp = TimePoint(bucket_start="2026-04-06", value=0.05, n=50)
        assert tp.endgame_elo is None, (
            "TimePoint.endgame_elo must default to None for non-endgame_elo_timeline series"
        )
        assert tp.non_endgame_elo is None, (
            "TimePoint.non_endgame_elo must default to None for non-endgame_elo_timeline series"
        )

    def test_endgame_elo_combo_all_timepoints_have_non_endgame_elo(self) -> None:
        """Every TimePoint emitted by _series_for_endgame_elo_combo carries non_endgame_elo.

        Gating contract (Phase 87.6): the payload extension must be non-None for
        every point in the series (no silent None-propagation through the 6-tuple
        threading).
        """
        points_data = [(1700 + i * 10, 1650 + i * 10, 1675 + i * 10) for i in range(10)]
        combo = _make_elo_combo_with_pr(points_data)
        result = _series_for_endgame_elo_combo(combo, "last_3mo")
        assert result is not None
        for tp in result:
            assert tp.non_endgame_elo is not None, (
                f"non_endgame_elo must not be None for endgame_elo_timeline point "
                f"at {tp.bucket_start}"
            )


# ---------------------------------------------------------------------------
# TestTimelineHelpers — weekly vs monthly resampling.
# ---------------------------------------------------------------------------


class TestTimelineHelpers:
    """Unit tests for _weekly_points_to_time_points resampling."""

    def test_monthly_all_time(self) -> None:
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
        ClockDiffTimelineResponse,
        EndgameCategoryStats,
        EndgameEloTimelineResponse,
        EndgamePerformanceResponse,
        EndgameStatsResponse,
        EndgameTimelineResponse,
        EndgameWDLSummary,
        ScoreGapMaterialResponse,
        ScoreGapTimelinePoint,
        TimePressureCardsResponse,
    )

    wdl = EndgameWDLSummary(
        wins=50,
        draws=10,
        losses=40,
        total=100,
        win_pct=50.0,
        draw_pct=10.0,
        loss_pct=40.0,
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
                wins=20,
                draws=5,
                losses=15,
                total=40,
                win_pct=50.0,
                draw_pct=12.5,
                loss_pct=37.5,
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
    # ELO timeline with >=10 points per combo
    elo_combo = EndgameEloTimelineCombo(
        combo_key="chess_com_blitz",
        platform="chess.com",
        time_control="blitz",
        points=[
            EndgameEloTimelinePoint(
                date=f"2026-01-{i + 4:02d}",
                endgame_elo=1500,
                non_endgame_elo=1400,
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
        time_pressure_cards=TimePressureCardsResponse(cards=[]),
        clock_diff_timeline=ClockDiffTimelineResponse(points=[]),
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
        # Phase 84 fields — not exercised by these series tests; mirror identity values.
        opponent_conversion_pct=60.0,  # recovery_losses(12)/recovery_games(20)*100
        opponent_conversion_games=20,
        opponent_recovery_pct=40.0,  # (conversion_losses(6)+conversion_draws(2))/conversion_games(20)*100
        opponent_recovery_games=20,
    )


# ---------------------------------------------------------------------------
# TestIntegration — D-02 end-to-end: compute_findings populates series only
# for the 3 timeline subsections (type_win_rate_timeline removed 260501-s0u).
# ---------------------------------------------------------------------------

# Phase 88: clock_diff_timeline removed from active timeline subsections — the
# ClockPressureResponse.timeline field was replaced by TimePressureCardsResponse.
# _finding_clock_diff_timeline now returns an empty finding (series=None).
_TIMELINE_SUBSECTION_IDS: frozenset[str] = frozenset(
    {
        "score_timeline",
        "endgame_elo_timeline",
    }
)


class TestIntegration:
    """Integration tests for compute_findings series population (D-02)."""

    @pytest.mark.asyncio
    async def test_compute_findings_populates_series_only_for_timelines(self) -> None:
        """series is not None exactly for the active timeline subsection_ids (D-02).

        Phase 88: clock_diff_timeline no longer populates series (timeline removed
        from EndgameOverviewResponse with ClockPressureResponse migration).
        """
        mock_response = _make_minimal_response()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await compute_findings(
                FilterContext(),
                session=AsyncMock(),
                user_id=1,
            )

        timeline_with_series = {f.subsection_id for f in result.findings if f.series is not None}
        non_timeline_with_series = [
            f
            for f in result.findings
            if f.subsection_id not in _TIMELINE_SUBSECTION_IDS and f.series is not None
        ]

        # Active timeline subsections must have series populated (Phase 88: 2 of 3 remain)
        assert "score_timeline" in timeline_with_series, (
            "score_timeline should have series populated"
        )
        assert "endgame_elo_timeline" in timeline_with_series, (
            "endgame_elo_timeline should have series populated"
        )
        # Phase 88: clock_diff_timeline returns empty finding (series=None); verify it doesn't
        # appear in timeline_with_series (its timeline was removed with ClockPressureResponse).
        assert "clock_diff_timeline" not in timeline_with_series, (
            "clock_diff_timeline should NOT have series in Phase 88 (timeline removed)"
        )
        # Non-timeline findings must NOT have series
        assert non_timeline_with_series == [], (
            f"Non-timeline findings with series: "
            f"{[f.subsection_id for f in non_timeline_with_series]}"
        )

    @pytest.mark.asyncio
    async def test_score_timeline_emits_three_findings_per_window(self) -> None:
        """Phase 68 v14 (260424-pc6): score_timeline emits THREE findings per window.
        Phase 82 D-01/D-02: MetricId renamed to endgame_score_timeline /
        non_endgame_score_timeline.

        One finding per distinct metric (endgame_score_timeline,
        non_endgame_score_timeline, score_gap). No `part` dim tag — each
        metric id is the unique key.
        Deterministic order: endgame_score_timeline, non_endgame_score_timeline, score_gap.
        Only the endgame_score_timeline finding is headline-eligible when the
        trend gate passes; non_endgame_score_timeline and score_gap are never
        headlines (score_gap's headline already lives on the `overall` subsection).
        """
        mock_response = _make_minimal_response()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await compute_findings(
                FilterContext(),
                session=AsyncMock(),
                user_id=1,
            )

        for window in ("all_time", "last_3mo"):
            st_findings = [
                f
                for f in result.findings
                if f.subsection_id == "score_timeline" and f.window == window
            ]
            assert len(st_findings) == 3, (
                f"Expected exactly 3 score_timeline findings for window={window}, "
                f"got {len(st_findings)}"
            )
            # Order: endgame_score_timeline, non_endgame_score_timeline, score_gap.
            assert st_findings[0].metric == "endgame_score_timeline"
            assert st_findings[1].metric == "non_endgame_score_timeline"
            assert st_findings[2].metric == "score_gap"
            # No findings carry a `part` dim.
            for f in st_findings:
                assert f.dimension is None, (
                    f"score_timeline findings must not carry a dim tag; "
                    f"got dimension={f.dimension} on metric={f.metric}"
                )
                assert f.series is not None
                assert len(f.series) > 0
            # Headline eligibility: only the endgame_score row is eligible
            # (and only when the trend gate passes — may still be False in
            # the test fixture if the synthetic series is too short).
            assert st_findings[1].is_headline_eligible is False
            assert st_findings[2].is_headline_eligible is False

    @pytest.mark.asyncio
    async def test_score_timeline_series_uses_absolute_per_side_values(self) -> None:
        """Phase 68 v14 (260424-pc6): per-metric series values come from the
        matching source fields — endgame_score, non_endgame_score, and the
        signed difference respectively.

        Identity invariant: for matching buckets,
        abs((endgame_value - non_endgame_value) - gap_value) < 1e-9.
        """
        mock_response = _make_minimal_response()
        timeline = mock_response.score_gap_material.timeline
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await compute_findings(
                FilterContext(),
                session=AsyncMock(),
                user_id=1,
            )

        st_last_3mo = [
            f
            for f in result.findings
            if f.subsection_id == "score_timeline" and f.window == "last_3mo"
        ]
        assert len(st_last_3mo) == 3
        endgame_f, non_endgame_f, gap_f = st_last_3mo
        assert endgame_f.metric == "endgame_score_timeline"
        assert non_endgame_f.metric == "non_endgame_score_timeline"
        assert gap_f.metric == "score_gap"
        assert endgame_f.series is not None
        assert non_endgame_f.series is not None
        assert gap_f.series is not None
        # Series length matches the source timeline (weekly pass-through).
        assert len(endgame_f.series) == len(timeline)
        assert len(non_endgame_f.series) == len(timeline)
        assert len(gap_f.series) == len(timeline)
        # Values come directly from endgame_score / non_endgame_score; gap
        # series is the per-bucket signed difference.
        for pt, src in zip(endgame_f.series, timeline, strict=True):
            assert pt.value == pytest.approx(src.endgame_score)
        for pt, src in zip(non_endgame_f.series, timeline, strict=True):
            assert pt.value == pytest.approx(src.non_endgame_score)
        for pt, src in zip(gap_f.series, timeline, strict=True):
            assert pt.value == pytest.approx(src.endgame_score - src.non_endgame_score)
        # Identity invariant per bucket across the three series.
        for eg_pt, neg_pt, gap_pt, src in zip(
            endgame_f.series,
            non_endgame_f.series,
            gap_f.series,
            timeline,
            strict=True,
        ):
            assert abs((eg_pt.value - neg_pt.value) - gap_pt.value) < 1e-9
            assert abs((eg_pt.value - neg_pt.value) - src.score_difference) < 1e-9


# ---------------------------------------------------------------------------
# TestScoreTimelineIntegration — Phase 68 Plan 04 end-to-end payload guard.
# Spans compute_findings → _assemble_user_prompt so a cross-plan regression
# (e.g. backend rename landed but prompt-rendered text still references the
# old id) surfaces here even when per-plan unit tests pass.
# ---------------------------------------------------------------------------


class TestScoreTimelineIntegration:
    """Phase 68 v14 (260424-pc6): findings → prompt assembly end-to-end payload shape."""

    @pytest.mark.asyncio
    async def test_score_timeline_end_to_end_payload(self) -> None:
        """v14 UAT-pass shape: rendered prompt has THREE summary + THREE
        series blocks per window (one per metric), no `score_gap_timeline`,
        no `Framing rule`, no `part=` dim tags.

        The score_timeline subsection emits one finding per distinct metric
        (endgame_score, non_endgame_score, score_gap). Weekly granularity
        is pinned in both windows via `_series_granularity`. Constant-n
        series (trailing-window sampling produces identical N per bucket)
        emit a single `[n=<N> for every point]` disclosure line.
        """
        # _assemble_user_prompt is module-private; ruff/ty are OK with
        # intra-package relative imports in tests. The prompt body is the
        # load-bearing artifact, so we reach for the private helper rather
        # than spinning up the whole `generate_insights` machinery (which
        # would pull in a live pydantic-ai Agent + LLM call).
        from app.services.insights_llm import _assemble_user_prompt

        mock_response = _make_minimal_response()
        # Sanity: _make_minimal_response ships 13 weekly points with a mixed
        # endgame-leads-vs-trails pattern (score_difference = 0.05*(i+1) over
        # i=0..12, all positive). The guard is shape-level, not sign-level —
        # the pattern's only role is producing a realistic non-trivial
        # series in both all_time (resampled to monthly for other
        # subsections) and last_3mo (weekly pass-through).
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ):
            findings = await compute_findings(
                FilterContext(),
                session=AsyncMock(),
                user_id=1,
            )

        # --- Finding-level assertions (cross-check compute_findings output) ---
        windows = ("all_time", "last_3mo")
        for window in windows:
            st_findings = [
                f
                for f in findings.findings
                if f.subsection_id == "score_timeline" and f.window == window
            ]
            assert len(st_findings) == 3, (
                f"Expected exactly 3 score_timeline findings for window={window}"
            )
            assert st_findings[0].metric == "endgame_score_timeline"
            assert st_findings[1].metric == "non_endgame_score_timeline"
            assert st_findings[2].metric == "score_gap"
            for f in st_findings:
                assert f.dimension is None

        # --- Prompt-level assertions (v14 emitter shape) ---
        rendered = _assemble_user_prompt(findings)

        # One subsection header (shared across both windows — not one-per-window).
        assert rendered.count("### Subsection: score_timeline") == 1, (
            "### Subsection: score_timeline must appear exactly once "
            "(both windows render inline under one header)"
        )

        # Extract the score_timeline slice so assertions don't accidentally
        # count summary blocks that live under other subsections (notably
        # the dedicated `score_gap` subsection also emits `[summary score_gap]`).
        timeline_start = rendered.index("### Subsection: score_timeline")
        # Find the next "### " boundary (or end of string) to scope the slice.
        next_header_search = rendered.find("### ", timeline_start + 1)
        timeline_slice = (
            rendered[timeline_start:next_header_search]
            if next_header_search != -1
            else rendered[timeline_start:]
        )

        # v14 (Phase 82 D-01/D-02 rename): THREE summary blocks under score_timeline,
        # one per metric — now endgame_score_timeline / non_endgame_score_timeline.
        assert timeline_slice.count("[summary endgame_score_timeline]") == 1
        assert timeline_slice.count("[summary non_endgame_score_timeline]") == 1
        assert timeline_slice.count("[summary score_gap]") == 1

        # No part-dim-tagged summaries leak through anywhere.
        assert "part=endgame" not in rendered
        assert "part=non_endgame" not in rendered

        # Series blocks: one per metric. Weekly granularity pinned regardless
        # of window. C5 dedupe (drop last_3mo series when all_time exists for
        # same (metric, subsection)) still applies — only the all_time series
        # is emitted for each metric here.
        assert "[series endgame_score_timeline, all_time, weekly]" in rendered
        assert "[series non_endgame_score_timeline, all_time, weekly]" in rendered
        assert "[series score_gap, all_time, weekly]" in rendered

        # Never monthly for score_timeline — granularity pin regression guard.
        for metric in ("endgame_score_timeline", "non_endgame_score_timeline", "score_gap"):
            assert f"[series {metric}, all_time, monthly" not in rendered
            assert f"[series {metric}, last_3mo, monthly" not in rendered

        # Constant-n disclosure fires for score_timeline series (sample sizes
        # per point are derived directly from the per-bucket game counts; in
        # the synthetic fixture they are constant).
        assert "[n=" in timeline_slice
        assert "for every point]" in timeline_slice

        # Old subsection-id must not leak into the user prompt anywhere.
        assert "score_gap_timeline" not in rendered
        # The dropped framing rule from Plan 03 must not leak through.
        assert "Framing rule" not in rendered

        # Regression guard: the aggregate [summary score_gap] is preserved in
        # the dedicated `score_gap` subsection (Phase 102 UAT relocated it from
        # the retired `overall` subsection) so the LLM can still quote the
        # authoritative signed-difference number.
        assert "### Subsection: score_gap" in rendered
        score_gap_idx = rendered.index("### Subsection: score_gap")
        score_gap_slice = rendered[score_gap_idx:timeline_start]
        assert "[summary score_gap]" in score_gap_slice, (
            "score_gap subsection missing the bare [summary score_gap] aggregate"
        )
