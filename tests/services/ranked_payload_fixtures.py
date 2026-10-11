"""Synthetic ranked-payload builders for the insights tests (Phase 238 plan 04, D-04).

The insights pipeline narrates the ranked Endgame Stats payload
(``RankedTcStats`` per time control). These builders construct that payload directly
with controllable values, so the findings builders, the prompt assembler and the golden
user prompt can be tested without a database.

Defaults describe a healthy, fully ranked blitz player: every metric is ``ranked`` with
a percentile, the Overall block clears every sample gate, and the timelines carry
enough points for the series logic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

from app.schemas.endgames import (
    ConversionRecoveryStats,
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameEloTimelinePoint,
    EndgameWDLSummary,
    PressureQuintileBullet,
    RankedBucketOut,
    RankedEntryFlowOut,
    RankedMetricOut,
    RankedOverallOut,
    RankedTcStats,
    RankedTimePressureOut,
    RankStatus,
    RatingAnchorOut,
    ScoreGapTimelinePoint,
    TimeControlBucket,
)
from app.services.global_percentile_cdf import CdfMetricId

# (value in fraction units, n) per metric; the defaults used by make_ranked_tc.
DEFAULT_METRIC_VALUES: Final[dict[CdfMetricId, tuple[float, int]]] = {
    "score_gap": (0.05, 240),
    "achievable_score_gap": (0.02, 50),
    "score_gap_conv": (-0.08, 100),
    "score_gap_parity": (-0.02, 80),
    "recovery_score_gap": (0.04, 60),
    "time_pressure_score_gap": (-0.03, 40),
    "clock_gap": (0.01, 90),
    "net_flag_rate": (0.005, 90),
    "conversion_rate": (0.68, 100),
    "parity_rate": (0.50, 80),
    "recovery_rate": (0.35, 60),
}

DEFAULT_ANCHOR: Final[RatingAnchorOut] = RatingAnchorOut(
    anchor_rating=1500,
    n_chesscom_games=0,
    n_lichess_games=300,
    chesscom_median_native=None,
    lichess_median_native=1500,
)


def make_wdl(wins: int, draws: int, losses: int) -> EndgameWDLSummary:
    """W/D/L summary with consistent percentages."""
    total = wins + draws + losses
    return EndgameWDLSummary(
        wins=wins,
        draws=draws,
        losses=losses,
        total=total,
        win_pct=wins / total * 100 if total else 0.0,
        draw_pct=draws / total * 100 if total else 0.0,
        loss_pct=losses / total * 100 if total else 0.0,
    )


def make_metric(
    metric: CdfMetricId,
    *,
    value: float | None = None,
    n: int | None = None,
    status: RankStatus = "ranked",
    percentile: float | None = None,
) -> RankedMetricOut:
    """One ranked metric; ``value`` / ``n`` default to DEFAULT_METRIC_VALUES.

    A ``ranked`` metric gets a deterministic percentile unless one is given; every other
    status carries none (the ranked service only exposes percentiles for ranked cells).
    """
    default_value, default_n = DEFAULT_METRIC_VALUES[metric]
    metric_value = default_value if value is None else value
    metric_n = default_n if n is None else n
    if status == "ranked" and percentile is None:
        percentile = 40.0 + 3.0 * list(DEFAULT_METRIC_VALUES).index(metric)
    return RankedMetricOut(
        metric=metric,
        value=metric_value,
        n=metric_n,
        floor_n=metric_n,
        floor_required=30,
        percentile=percentile if status == "ranked" else None,
        status=status,
    )


def make_score_timeline(n_points: int = 13) -> list[ScoreGapTimelinePoint]:
    """Weekly Score Gap timeline; endgame_score - non_endgame_score == score_difference."""
    return [
        ScoreGapTimelinePoint(
            date=f"2026-01-{i + 4:02d}",
            score_difference=round(0.05 * (i + 1), 4),
            endgame_game_count=10,
            non_endgame_game_count=10,
            per_week_total_games=20,
            endgame_score=round(0.50 + 0.05 * (i + 1), 4),
            non_endgame_score=0.50,
        )
        for i in range(n_points)
    ]


def make_elo_combo(
    n_points: int = 13,
    *,
    platform: str = "chess.com",
    time_control: TimeControlBucket = "blitz",
    endgame_elo: int = 1500,
    actual_elo: int = 1400,
) -> EndgameEloTimelineCombo:
    """Endgame ELO combo with ``n_points`` weekly points."""
    return EndgameEloTimelineCombo(
        combo_key=f"{platform.replace('.', '_')}_{time_control}",
        platform="chess.com" if platform == "chess.com" else "lichess",
        time_control=time_control,
        points=[
            EndgameEloTimelinePoint(
                date=f"2026-01-{i + 4:02d}",
                endgame_elo=endgame_elo,
                non_endgame_elo=actual_elo,
                actual_elo=actual_elo,
                endgame_games_in_window=50,
                per_week_endgame_games=5,
            )
            for i in range(n_points)
        ],
    )


def make_quintiles(*, n: int = 30) -> list[PressureQuintileBullet]:
    """Five pressure quintiles (Q0 = max pressure); each clears the opponent n-gate."""
    labels = ("0-20%", "20-40%", "40-60%", "60-80%", "80-100%")
    return [
        PressureQuintileBullet(
            quintile_index=i,
            quintile_label=label,
            n=n,
            n_opp=n,
            delta=-0.06 + 0.03 * i,
            p_value=None,
            ci_low=None,
            ci_high=None,
            opp_score=0.50,
        )
        for i, label in enumerate(labels)
    ]


def make_category(
    endgame_class: str,
    *,
    conv_games: int,
    conv_wins: int,
    recov_games: int,
    recov_wins: int,
) -> EndgameCategoryStats:
    """Minimal Endgame Type row (rook / minor_piece / pawn / queen)."""
    conv_losses = conv_games - conv_wins
    total = conv_games + recov_games
    return EndgameCategoryStats(
        endgame_class=endgame_class,  # ty: ignore[invalid-argument-type]
        label=endgame_class.capitalize(),  # ty: ignore[invalid-argument-type]
        wins=conv_wins,
        draws=0,
        losses=conv_losses,
        total=total,
        win_pct=round(conv_wins / total * 100, 1),
        draw_pct=0.0,
        loss_pct=round(conv_losses / total * 100, 1),
        conversion=ConversionRecoveryStats(
            conversion_pct=round(conv_wins / conv_games * 100, 1) if conv_games else 0.0,
            conversion_games=conv_games,
            conversion_wins=conv_wins,
            conversion_draws=0,
            conversion_losses=conv_losses,
            recovery_pct=round(recov_wins / recov_games * 100, 1) if recov_games else 0.0,
            recovery_games=recov_games,
            recovery_saves=recov_wins,
            recovery_wins=recov_wins,
            recovery_draws=0,
            opponent_conversion_pct=None,
            opponent_conversion_games=recov_games,
            opponent_recovery_pct=None,
            opponent_recovery_games=conv_games,
        ),
    )


def make_ranked_tc(
    tc: TimeControlBucket = "blitz",
    *,
    endgame: tuple[int, int, int] = (25, 10, 15),
    non_endgame: tuple[int, int, int] = (20, 10, 20),
    metrics: Mapping[CdfMetricId, RankedMetricOut] | None = None,
    entry_eval_mean_pawns: float | None = 0.30,
    entry_eval_n: int = 50,
    expected_score: float | None = 0.50,
    actual_score: float | None = 0.52,
    flow_n: int = 50,
    anchor: RatingAnchorOut | None = DEFAULT_ANCHOR,
    ranked_games: int | None = None,
    score_gap_timeline: Sequence[ScoreGapTimelinePoint] | None = None,
    elo_timeline: Sequence[EndgameEloTimelineCombo] | None = None,
    type_categories: Sequence[EndgameCategoryStats] | None = None,
    quintiles: Sequence[PressureQuintileBullet] | None = None,
) -> RankedTcStats:
    """A ranked TC payload; ``metrics`` overrides individual defaults by metric id."""
    eg = make_wdl(*endgame)
    ne = make_wdl(*non_endgame)
    all_metrics: dict[CdfMetricId, RankedMetricOut] = {
        metric: make_metric(metric) for metric in DEFAULT_METRIC_VALUES
    }
    all_metrics.update(metrics or {})
    games = eg.total + ne.total if ranked_games is None else ranked_games
    return RankedTcStats(
        tc=tc,
        ranked_games=games,
        anchor_games=games,
        anchor_min_games=30,
        anchor=anchor,
        eval_pending_games=0,
        metrics=all_metrics,
        overall=RankedOverallOut(
            endgame_wdl=eg,
            non_endgame_wdl=ne,
            entry_flow=RankedEntryFlowOut(
                entry_eval_mean_pawns=entry_eval_mean_pawns,
                entry_eval_n=entry_eval_n,
                expected_score=expected_score,
                actual_score=actual_score,
                n=flow_n,
            ),
        ),
        buckets=[
            RankedBucketOut(bucket="conversion", games=100, wins=68, draws=0, losses=32),
            RankedBucketOut(bucket="parity", games=80, wins=30, draws=20, losses=30),
            RankedBucketOut(bucket="recovery", games=60, wins=10, draws=22, losses=28),
        ],
        time_pressure=RankedTimePressureOut(
            quintiles=list(make_quintiles() if quintiles is None else quintiles)
        ),
        score_gap_timeline=list(
            make_score_timeline() if score_gap_timeline is None else score_gap_timeline
        ),
        score_gap_timeline_window=50,
        elo_timeline=list(
            [make_elo_combo(time_control=tc)] if elo_timeline is None else elo_timeline
        ),
        elo_timeline_window=100,
        type_categories=list(type_categories or []),
    )
