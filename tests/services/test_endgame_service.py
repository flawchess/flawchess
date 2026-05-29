"""Service-level tests for _compute_per_tc_metric_cards (Phase 97, Plan 02).

Tests cover:
- Per-TC rate values (conversion win%, parity score%, recovery save%)
- WDL percentages per bucket
- ΔES score-gap stats per bucket
- Per-TC percentile lookup (direct, non-blended)
- TC card ordering (bullet -> blitz -> rapid -> classical)
- MIN_GAMES_PER_TC_CARD suppression (below threshold -> no card)
- Empty input -> cards == []
- Multi-TC fixture in get_endgame_overview produces non-empty cards
"""

import datetime
from typing import Any, NamedTuple
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.endgame_service import (
    MIN_GAMES_PER_TC_CARD,
    _compute_per_tc_metric_cards,
)


# ---------------------------------------------------------------------------
# Row type and builder
# ---------------------------------------------------------------------------


class _BucketRow(NamedTuple):
    """Minimal stand-in for an extended query_endgame_bucket_rows Row.

    Mirrors the labeled columns produced by the Phase 97 extended query so
    _compute_per_tc_metric_cards (positional indexing) and _get_endgame_performance_from_rows
    (named attribute access on eval_cp, eval_mate) both work correctly.
    """

    game_id: int
    endgame_class: int
    result: str
    user_color: str
    eval_cp: Any
    eval_mate: Any
    time_control_bucket: str
    next_entry_eval_cp: Any
    next_entry_eval_mate: Any


def _make_bucket_row(
    tc: str,
    result: str = "1-0",
    user_color: str = "white",
    eval_cp: int | None = 200,
    eval_mate: int | None = None,
    game_id: int = 1,
    next_entry_eval_cp: int | None = None,
    next_entry_eval_mate: int | None = None,
    endgame_class: int = 1,
) -> _BucketRow:
    """Build a minimal bucket row matching the extended query_endgame_bucket_rows shape.

    Column indices (and named attributes for NamedTuple access):
        [0] game_id
        [1] endgame_class
        [2] result
        [3] user_color
        [4] eval_cp
        [5] eval_mate
        [6] time_control_bucket
        [7] next_entry_eval_cp
        [8] next_entry_eval_mate
    """
    return _BucketRow(
        game_id=game_id,
        endgame_class=endgame_class,
        result=result,
        user_color=user_color,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
        time_control_bucket=tc,
        next_entry_eval_cp=next_entry_eval_cp,
        next_entry_eval_mate=next_entry_eval_mate,
    )


def _make_conversion_row(
    tc: str, result: str, user_color: str = "white", game_id: int = 1
) -> _BucketRow:
    """Build a conversion bucket row: eval_cp=200 (user up, white perspective)."""
    # eval_cp=200 centipawns, user_color=white => +2.0 from user's perspective => conversion
    return _make_bucket_row(
        tc=tc, result=result, user_color=user_color, eval_cp=200, game_id=game_id
    )


def _make_recovery_row(
    tc: str, result: str, user_color: str = "white", game_id: int = 1
) -> _BucketRow:
    """Build a recovery bucket row: eval_cp=-200 (user down, white perspective)."""
    # eval_cp=-200 centipawns, user_color=white => -2.0 from user's perspective => recovery
    return _make_bucket_row(
        tc=tc, result=result, user_color=user_color, eval_cp=-200, game_id=game_id
    )


def _make_parity_row(
    tc: str, result: str, user_color: str = "white", game_id: int = 1
) -> _BucketRow:
    """Build a parity bucket row: eval_cp=0 (even position)."""
    return _make_bucket_row(tc=tc, result=result, user_color=user_color, eval_cp=0, game_id=game_id)


# ---------------------------------------------------------------------------
# Core behavior tests
# ---------------------------------------------------------------------------


class TestComputePerTcMetricCardsEmpty:
    def test_empty_input_returns_empty_cards(self) -> None:
        """Empty bucket_rows produces EndgameMetricsCardsResponse with cards == []."""
        result = _compute_per_tc_metric_cards([])
        assert result.cards == []

    def test_below_threshold_suppressed(self) -> None:
        """TC with total < MIN_GAMES_PER_TC_CARD produces no card."""
        rows = [
            _make_conversion_row("blitz", "1-0", game_id=i)
            for i in range(MIN_GAMES_PER_TC_CARD - 1)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert result.cards == []

    def test_at_threshold_card_emitted(self) -> None:
        """TC with total == MIN_GAMES_PER_TC_CARD emits one card."""
        rows = [
            _make_conversion_row("blitz", "1-0", game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        assert result.cards[0].tc == "blitz"


class TestComputePerTcMetricCardsOrder:
    def test_card_order_bullet_blitz_rapid_classical(self) -> None:
        """When all four TCs pass the threshold, cards are ordered bullet->blitz->rapid->classical."""
        rows: list[tuple[Any, ...]] = []
        for tc_offset, tc in enumerate(["classical", "rapid", "blitz", "bullet"]):  # reversed
            for i in range(MIN_GAMES_PER_TC_CARD):
                rows.append(_make_parity_row(tc, "1/2-1/2", game_id=1000 * (tc_offset + 1) + i))
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 4
        assert [c.tc for c in result.cards] == ["bullet", "blitz", "rapid", "classical"]

    def test_only_qualifying_tcs_in_cards(self) -> None:
        """Only TCs that pass MIN_GAMES_PER_TC_CARD appear in cards."""
        rows = [
            _make_parity_row("bullet", "1/2-1/2", game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        # Add 5 rapid rows (below threshold)
        rows += [_make_parity_row("rapid", "1/2-1/2", game_id=1000 + i) for i in range(5)]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        assert result.cards[0].tc == "bullet"


class TestComputePerTcMetricCardsRates:
    def test_conversion_rate_all_wins(self) -> None:
        """All conversion games are wins -> conversion.rate == 1.0."""
        rows = [
            _make_conversion_row("blitz", "1-0", "white", game_id=i)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        assert card.conversion.rate == pytest.approx(1.0)

    def test_conversion_rate_half_wins(self) -> None:
        """Half wins, half losses -> conversion.rate == 0.5."""
        rows = []
        half = MIN_GAMES_PER_TC_CARD // 2
        for i in range(half):
            rows.append(_make_conversion_row("blitz", "1-0", "white", game_id=i))
        for i in range(half):
            rows.append(_make_conversion_row("blitz", "0-1", "white", game_id=100 + i))
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        assert result.cards[0].conversion.rate == pytest.approx(0.5)

    def test_recovery_rate_all_saves(self) -> None:
        """All recovery games are wins+draws -> recovery.rate == 1.0."""
        rows = []
        half = MIN_GAMES_PER_TC_CARD // 2
        for i in range(half):
            rows.append(_make_recovery_row("rapid", "1-0", "white", game_id=i))
        for i in range(half):
            rows.append(_make_recovery_row("rapid", "1/2-1/2", "white", game_id=100 + i))
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        # recovery save = (wins + draws) / total
        assert result.cards[0].recovery.rate == pytest.approx(1.0)

    def test_recovery_rate_zero_saves(self) -> None:
        """All recovery games are losses -> recovery.rate == 0.0."""
        rows = [
            _make_recovery_row("rapid", "0-1", "white", game_id=i)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        assert result.cards[0].recovery.rate == pytest.approx(0.0)

    def test_parity_score_pct_all_draws(self) -> None:
        """All parity games are draws -> parity.rate == 0.5 (chess score)."""
        rows = [
            _make_parity_row("bullet", "1/2-1/2", "white", game_id=i)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        # parity rate = (wins + 0.5*draws) / total = (0 + 0.5*N) / N = 0.5
        assert result.cards[0].parity.rate == pytest.approx(0.5)

    def test_rate_none_when_bucket_empty(self) -> None:
        """When a bucket has zero games, its rate is None."""
        # All parity games -> conversion and recovery buckets are empty
        rows = [
            _make_parity_row("blitz", "1/2-1/2", "white", game_id=i)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        assert card.conversion.rate is None
        assert card.recovery.rate is None

    def test_rates_within_unit_interval(self) -> None:
        """All rates are in [0.0, 1.0] or None for a mixed fixture."""
        rows = []
        # Blend of all three buckets across two TCs
        for i in range(8):
            rows.append(_make_conversion_row("bullet", "1-0", game_id=i))
        for i in range(6):
            rows.append(_make_parity_row("bullet", "1/2-1/2", game_id=100 + i))
        for i in range(MIN_GAMES_PER_TC_CARD - 14):
            rows.append(_make_recovery_row("bullet", "0-1", game_id=200 + i))
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        for bucket_stats in [card.conversion, card.parity, card.recovery]:
            if bucket_stats.rate is not None:
                assert 0.0 <= bucket_stats.rate <= 1.0


class TestComputePerTcMetricCardsWDL:
    def test_wdl_pcts_all_wins(self) -> None:
        """All wins in conversion bucket -> win_pct=100, draw_pct=0, loss_pct=0."""
        rows = [
            _make_conversion_row("blitz", "1-0", "white", game_id=i)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        conv = result.cards[0].conversion
        assert conv.win_pct == pytest.approx(100.0)
        assert conv.draw_pct == pytest.approx(0.0)
        assert conv.loss_pct == pytest.approx(0.0)
        assert conv.games == MIN_GAMES_PER_TC_CARD

    def test_wdl_pcts_mixed(self) -> None:
        """5 wins, 3 draws, 2 losses -> win_pct=50, draw_pct=30, loss_pct=20."""
        rows = []
        for i in range(5):
            rows.append(_make_conversion_row("blitz", "1-0", game_id=i))
        for i in range(3):
            rows.append(_make_conversion_row("blitz", "1/2-1/2", game_id=100 + i))
        for i in range(2):
            rows.append(_make_conversion_row("blitz", "0-1", game_id=200 + i))
        # Pad with parity rows to clear MIN_GAMES_PER_TC_CARD
        for i in range(MIN_GAMES_PER_TC_CARD - 10):
            rows.append(_make_parity_row("blitz", "1/2-1/2", game_id=300 + i))

        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        conv = result.cards[0].conversion
        assert conv.games == 10
        assert conv.win_pct == pytest.approx(50.0)
        assert conv.draw_pct == pytest.approx(30.0)
        assert conv.loss_pct == pytest.approx(20.0)


class TestComputePerTcMetricCardsPercentile:
    def test_percentile_rows_omitted_defaults_to_none(self) -> None:
        """Calling without percentile_rows gives None on all three buckets' percentile."""
        rows = [
            _make_parity_row("blitz", "1/2-1/2", game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        assert card.conversion.percentile is None
        assert card.parity.percentile is None
        assert card.recovery.percentile is None

    def test_percentile_rows_direct_lookup(self) -> None:
        """Per-TC percentile is read directly from percentile_rows[metric][tc]."""
        import datetime

        from app.models.user_rating_anchors import TimeControlBucket
        from app.repositories.user_benchmark_percentiles_repository import PercentileRow
        from app.services.global_percentile_cdf import CdfMetricId

        rows = [
            _make_parity_row("blitz", "1/2-1/2", game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        percentile_rows: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = {
            "score_gap_conv": {
                "blitz": PercentileRow(
                    value=0.05,
                    percentile=72.0,
                    cdf_snapshot=datetime.date(2026, 5, 29),
                    n_games=50,
                ),
            },
            "score_gap_parity": {
                "blitz": PercentileRow(
                    value=-0.01,
                    percentile=48.0,
                    cdf_snapshot=datetime.date(2026, 5, 29),
                    n_games=50,
                ),
            },
            "recovery_score_gap": {
                "blitz": PercentileRow(
                    value=0.10,
                    percentile=65.0,
                    cdf_snapshot=datetime.date(2026, 5, 29),
                    n_games=50,
                ),
            },
        }
        result = _compute_per_tc_metric_cards(rows, percentile_rows=percentile_rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        assert card.conversion.percentile == pytest.approx(72.0)
        assert card.parity.percentile == pytest.approx(48.0)
        assert card.recovery.percentile == pytest.approx(65.0)

    def test_percentile_rows_missing_tc_is_none(self) -> None:
        """If the TC is absent from a metric's percentile dict, percentile is None."""
        import datetime

        from app.models.user_rating_anchors import TimeControlBucket
        from app.repositories.user_benchmark_percentiles_repository import PercentileRow
        from app.services.global_percentile_cdf import CdfMetricId

        rows = [
            _make_parity_row("bullet", "1/2-1/2", game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        # score_gap_conv has blitz but NOT bullet; others not provided
        percentile_rows: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = {
            "score_gap_conv": {
                "blitz": PercentileRow(
                    value=0.05,
                    percentile=72.0,
                    cdf_snapshot=datetime.date(2026, 5, 29),
                    n_games=50,
                ),
            },
        }
        result = _compute_per_tc_metric_cards(rows, percentile_rows=percentile_rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        # bullet not in score_gap_conv dict -> None
        assert card.conversion.percentile is None
        assert card.parity.percentile is None
        assert card.recovery.percentile is None

    def test_percentile_no_blended_aggregation(self) -> None:
        """Percentile lookup is per-TC direct; two TCs get their own independent values."""
        import datetime

        from app.models.user_rating_anchors import TimeControlBucket
        from app.repositories.user_benchmark_percentiles_repository import PercentileRow
        from app.services.global_percentile_cdf import CdfMetricId

        rows: list[tuple[Any, ...]] = []
        for i in range(MIN_GAMES_PER_TC_CARD):
            rows.append(_make_parity_row("bullet", "1/2-1/2", game_id=i))
        for i in range(MIN_GAMES_PER_TC_CARD):
            rows.append(_make_parity_row("blitz", "1/2-1/2", game_id=1000 + i))

        percentile_rows: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = {
            "score_gap_parity": {
                "bullet": PercentileRow(
                    value=-0.02,
                    percentile=30.0,
                    cdf_snapshot=datetime.date(2026, 5, 29),
                    n_games=40,
                ),
                "blitz": PercentileRow(
                    value=0.03,
                    percentile=70.0,
                    cdf_snapshot=datetime.date(2026, 5, 29),
                    n_games=60,
                ),
            },
        }
        result = _compute_per_tc_metric_cards(rows, percentile_rows=percentile_rows)
        assert len(result.cards) == 2
        cards_by_tc = {c.tc: c for c in result.cards}
        # Each TC gets its own percentile, not a blended value
        assert cards_by_tc["bullet"].parity.percentile == pytest.approx(30.0)
        assert cards_by_tc["blitz"].parity.percentile == pytest.approx(70.0)


class TestComputePerTcMetricCardsBucketPriority:
    def test_conversion_priority_over_recovery(self) -> None:
        """When a game has both conv and recov (impossible for one game, but priority test).

        Conversion has priority over recovery — a game with eval >= +1.0 user perspective
        always lands in conversion bucket, never recovery.
        """
        # A conversion game (white up 2 pawns, user is white) must land in conversion
        row = _make_conversion_row("rapid", "1-0", "white", game_id=1)
        # Pad to threshold
        rows = [row] + [
            _make_parity_row("rapid", "1/2-1/2", game_id=i)
            for i in range(2, MIN_GAMES_PER_TC_CARD + 1)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        assert card.conversion.games == 1
        assert card.recovery.games == 0

    def test_user_color_black_classification(self) -> None:
        """user_color=black flips the eval sign: eval_cp=-200 from white's view means +2 for black => conversion."""
        # eval_cp=-200 means white is down 2 pawns => black (user) is up => conversion
        row = _make_bucket_row(
            tc="blitz",
            result="0-1",  # black wins
            user_color="black",
            eval_cp=-200,  # white-perspective: white is down -> black (user) is up
            game_id=1,
        )
        rows = [row] + [
            _make_parity_row("blitz", "1/2-1/2", game_id=i)
            for i in range(2, MIN_GAMES_PER_TC_CARD + 1)
        ]
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        # With user_color=black and eval_cp=-200, the user sees +2 => conversion
        assert result.cards[0].conversion.games == 1


class TestComputePerTcMetricCardsTotal:
    def test_total_equals_sum_of_bucket_games(self) -> None:
        """card.total equals sum of conv + parity + recovery games."""
        rows = []
        for i in range(5):
            rows.append(_make_conversion_row("bullet", "1-0", game_id=i))
        for i in range(8):
            rows.append(_make_parity_row("bullet", "1/2-1/2", game_id=100 + i))
        for i in range(MIN_GAMES_PER_TC_CARD - 13):
            rows.append(_make_recovery_row("bullet", "0-1", game_id=200 + i))
        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        assert card.total == MIN_GAMES_PER_TC_CARD
        assert card.conversion.games + card.parity.games + card.recovery.games == card.total


class TestComputePerTcMetricCardsMultiTc:
    def test_multi_tc_independent_rates(self) -> None:
        """Two TCs with different win rates compute independent rate values."""
        rows = []
        # Bullet: all conversion wins
        for i in range(MIN_GAMES_PER_TC_CARD):
            rows.append(_make_conversion_row("bullet", "1-0", game_id=i))
        # Blitz: all conversion losses
        for i in range(MIN_GAMES_PER_TC_CARD):
            rows.append(_make_conversion_row("blitz", "0-1", game_id=1000 + i))

        result = _compute_per_tc_metric_cards(rows)
        assert len(result.cards) == 2
        cards_by_tc = {c.tc: c for c in result.cards}
        assert cards_by_tc["bullet"].conversion.rate == pytest.approx(1.0)
        assert cards_by_tc["blitz"].conversion.rate == pytest.approx(0.0)


class TestGetEndgameOverviewMetricsCards:
    """Test that get_endgame_overview threads endgame_metrics_cards into the response."""

    @pytest.mark.asyncio
    async def test_endgame_metrics_cards_populated_multi_tc(self) -> None:
        """get_endgame_overview returns a non-empty endgame_metrics_cards for a multi-TC fixture."""
        from app.schemas.endgames import EndgameEloTimelineResponse, EndgameTimelineResponse
        from app.services.endgame_service import get_endgame_overview

        # Build bucket rows that will produce two TC cards (bullet + blitz)
        bucket_rows = []
        for i in range(MIN_GAMES_PER_TC_CARD):
            bucket_rows.append(_make_conversion_row("bullet", "1-0", game_id=i))
        for i in range(MIN_GAMES_PER_TC_CARD):
            bucket_rows.append(_make_parity_row("blitz", "1/2-1/2", game_id=1000 + i))

        with (
            patch(
                "app.services.endgame_service.query_endgame_bucket_rows",
                new_callable=AsyncMock,
                return_value=bucket_rows,
            ),
            patch(
                "app.services.endgame_service.query_endgame_entry_rows",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.endgame_service.query_endgame_performance_rows",
                new_callable=AsyncMock,
                return_value=([], []),
            ),
            patch(
                "app.services.endgame_service.count_filtered_games",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "app.services.endgame_service.count_endgame_games",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "app.services.endgame_service.query_clock_stats_rows",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.endgame_service.get_endgame_timeline",
                new_callable=AsyncMock,
                return_value=EndgameTimelineResponse(overall=[], per_type={}, window=100),
            ),
            patch(
                "app.services.endgame_service.get_endgame_elo_timeline",
                new_callable=AsyncMock,
                return_value=EndgameEloTimelineResponse(combos=[], timeline_window=100),
            ),
            patch(
                "app.services.endgame_service.user_benchmark_percentiles_repository.fetch_for_user",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.endgame_service.fetch_anchors_for_user",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await get_endgame_overview(
                AsyncMock(spec=AsyncSession),
                user_id=1,
                time_control=None,
                platform=None,
                rated=None,
                opponent_type="human",
                from_date=None,
                to_date=None,
                window=100,
            )

        # endgame_metrics_cards should be populated with 2 cards (bullet + blitz)
        assert result.endgame_metrics_cards is not None
        assert len(result.endgame_metrics_cards.cards) == 2
        cards_by_tc = {c.tc: c for c in result.endgame_metrics_cards.cards}
        assert "bullet" in cards_by_tc
        assert "blitz" in cards_by_tc
        # Rates are within [0, 1] or None
        for card in result.endgame_metrics_cards.cards:
            for bucket_stats in [card.conversion, card.parity, card.recovery]:
                if bucket_stats.rate is not None:
                    assert 0.0 <= bucket_stats.rate <= 1.0
