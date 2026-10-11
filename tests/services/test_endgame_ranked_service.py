"""Pure (no DB) tests for the ranked Endgame Stats service (Phase 238).

Built on synthetic ``RankedInputs``: rank-status matrix (D-09 / D-10 / D-11),
bucket W/D/L vs rate consistency (D-00b), TC listing (D-14) and the popover
statistics shapes. Numeric parity with the Stage A/B CTEs lives in
``test_endgame_ranked_parity.py``.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import NamedTuple

import pytest

from app.repositories.endgame_ranked_repository import RankedGameRow
from app.repositories.query_utils import AnalyticsPlatform
from app.repositories.user_benchmark_percentiles_repository import PercentileRow
from app.repositories.user_rating_anchors_repository import RatingAnchorRow
from app.schemas.endgames import EndgameRankedStatsResponse, RankedMetricOut, RankedTcStats
from app.services.canonical_slice_sql import MEDIAN_ANCHOR_MIN_GAMES, TimeControlBucket
from app.services.endgame_ranked_service import (
    EVAL_DEPENDENT_METRICS,
    RankedInputs,
    _asof_by_platform,
    build_ranked_stats,
)
from app.services.endgame_service import (
    _ENDGAME_ELO_COMBO_ORDER,
    ENDGAME_ELO_TIMELINE_WINDOW,
    aggregate_endgame_stats_by_tc,
    build_quintile_bullets,
    compute_clock_diff_timeline,
    _compute_endgame_elo_weekly_series,
    compute_score_gap_timeline,
    iterate_clock_rows,
    build_endgame_elo_combos,
)
from app.services.global_percentile_cdf import CdfMetricId

_NOW = datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc)
_SNAPSHOT = datetime.date(2026, 10, 1)
_BASE_TIME_SECONDS = 180
_ENDGAME_GAMES = 100
_NON_ENDGAME_GAMES = 35
_BELOW_ANCHOR_GAMES = 18
_METRIC_FLOOR_SHORT_GAMES = 22
_PERCENTILE = 64.0
_ALL_METRICS: tuple[CdfMetricId, ...] = (
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
)
_CLOCK_METRICS: tuple[CdfMetricId, ...] = (
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)

_ANCHOR = RatingAnchorRow(
    anchor_rating=1500,
    n_chesscom_games=0,
    n_lichess_games=75,
    chesscom_median_native=None,
    lichess_median_native=1500,
)


# ── Synthetic row shapes (named like the repository rows) ────────────────────


class PerfRow(NamedTuple):
    played_at: datetime.datetime
    result: str
    user_color: str
    platform: str
    time_control_bucket: str


class BucketRow(NamedTuple):
    game_id: int
    endgame_class: int
    result: str
    user_color: str
    eval_cp: int | None
    eval_mate: int | None
    time_control_bucket: str
    next_entry_eval_cp: int | None
    next_entry_eval_mate: int | None


class EntryRow(NamedTuple):
    game_id: int
    endgame_class: int
    result: str
    user_color: str
    eval_cp: int | None
    eval_mate: int | None
    next_entry_eval_cp: int | None
    next_entry_eval_mate: int | None
    played_at: datetime.datetime
    time_control_bucket: str


class ClockRow(NamedTuple):
    game_id: int
    time_control_bucket: str
    base_time_seconds: int | None
    termination: str | None
    result: str
    user_color: str
    ply_array: list[int]
    clock_array: list[float | None]
    played_at: datetime.datetime


def _games(
    n: int,
    *,
    first_id: int = 1,
    platform: AnalyticsPlatform = "lichess",
    time_control_str: str | None = "180+0",
    eval_pending: bool = False,
) -> list[RankedGameRow]:
    return [
        RankedGameRow(
            game_id=first_id + i,
            played_at=_NOW - datetime.timedelta(days=i),
            platform=platform,
            time_control_str=time_control_str,
            user_elo=1500,
            eval_pending=eval_pending,
        )
        for i in range(n)
    ]


def _result(outcome: str, user_color: str) -> str:
    if outcome == "draw":
        return "1/2-1/2"
    return "1-0" if (user_color == "white") == (outcome == "win") else "0-1"


def _outcome(i: int) -> str:
    return ("win", "win", "draw", "loss")[i % 4]


def _color(i: int) -> str:
    return "white" if i % 2 == 0 else "black"


def _perf_rows(ids: range, tc: str = "blitz") -> list[PerfRow]:
    return [
        PerfRow(
            played_at=_NOW - datetime.timedelta(days=i),
            result=_result(_outcome(i), _color(i)),
            user_color=_color(i),
            platform="lichess",
            time_control_bucket=tc,
        )
        for i in ids
    ]


def _entry_cp(i: int) -> int:
    """User-perspective entry eval cycling conversion / parity / recovery."""
    return (250, 0, -250)[i % 3]


def _bucket_rows(ids: range, tc: str = "blitz") -> list[BucketRow]:
    rows = []
    for i in ids:
        color = _color(i)
        sign = 1 if color == "white" else -1
        rows.append(
            BucketRow(
                game_id=i + 1,
                endgame_class=1,
                result=_result(_outcome(i), color),
                user_color=color,
                eval_cp=_entry_cp(i) * sign,
                eval_mate=None,
                time_control_bucket=tc,
                next_entry_eval_cp=None,
                next_entry_eval_mate=None,
            )
        )
    return rows


def _entry_rows(ids: range, tc: str = "blitz") -> list[EntryRow]:
    return [
        EntryRow(
            game_id=b.game_id,
            endgame_class=b.endgame_class,
            result=b.result,
            user_color=b.user_color,
            eval_cp=b.eval_cp,
            eval_mate=b.eval_mate,
            next_entry_eval_cp=None,
            next_entry_eval_mate=None,
            played_at=_NOW,
            time_control_bucket=tc,
        )
        for b in _bucket_rows(ids, tc)
    ]


def _clock_rows(ids: range, tc: str = "blitz") -> list[ClockRow]:
    """Alternate pressured (40s) / comfortable (150s) clocks for user and opponent."""
    rows = []
    for i in ids:
        color = _color(i)
        user_clock = 40.0 if i % 2 == 0 else 150.0
        opp_clock = 40.0 if i % 3 == 0 else 150.0
        white, black = (user_clock, opp_clock) if color == "white" else (opp_clock, user_clock)
        rows.append(
            ClockRow(
                game_id=i + 1,
                time_control_bucket=tc,
                base_time_seconds=_BASE_TIME_SECONDS,
                termination="timeout" if i % 5 == 0 else "checkmate",
                result=_result(_outcome(i), color),
                user_color=color,
                ply_array=[30, 31],
                clock_array=[white, black],
                played_at=_NOW,
            )
        )
    return rows


def _full_inputs(
    *,
    tc: TimeControlBucket = "blitz",
    anchor: RatingAnchorRow | None = _ANCHOR,
    eval_pending: bool = False,
    with_evals: bool = True,
    with_clocks: bool = True,
    percentile_rows: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] | None = None,
    n_endgame: int = _ENDGAME_GAMES,
) -> RankedInputs:
    games = _games(n_endgame + _NON_ENDGAME_GAMES, eval_pending=eval_pending)
    ids = range(n_endgame)
    return RankedInputs(
        games_by_tc={tc: games},
        endgame_rows=_perf_rows(ids, tc),
        non_endgame_rows=_perf_rows(range(n_endgame, n_endgame + _NON_ENDGAME_GAMES), tc),
        entry_rows=_entry_rows(ids, tc) if with_evals else [],
        bucket_rows=_bucket_rows(ids, tc) if with_evals else [],
        clock_rows=_clock_rows(ids, tc) if with_clocks else [],
        percentile_rows=percentile_rows or {},
        anchors={tc: anchor} if anchor is not None else {},
    )


def _percentiles(
    metrics: tuple[CdfMetricId, ...] = _ALL_METRICS,
    *,
    tc: TimeControlBucket = "blitz",
    percentile: float | None = _PERCENTILE,
) -> dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]]:
    return {
        m: {tc: PercentileRow(value=0.1, percentile=percentile, cdf_snapshot=_SNAPSHOT, n_games=40)}
        for m in metrics
    }


def _tc(response: EndgameRankedStatsResponse, tc: TimeControlBucket = "blitz") -> RankedTcStats:
    return next(t for t in response.tcs if t.tc == tc)


def _metric(
    response: EndgameRankedStatsResponse, metric: CdfMetricId, tc: TimeControlBucket = "blitz"
) -> RankedMetricOut:
    return _tc(response, tc).metrics[metric]


# ── Rank status matrix (D-09 / D-10 / D-11) ──────────────────────────────────


def test_status_below_floor_anchor() -> None:
    """D-09: no anchor and 18 non-Daily games -> every metric below_floor, '18 of 30'."""
    inputs = RankedInputs(games_by_tc={"blitz": _games(_BELOW_ANCHOR_GAMES)})
    tc_stats = _tc(build_ranked_stats(inputs))
    assert tc_stats.anchor is None
    assert tc_stats.anchor_games == _BELOW_ANCHOR_GAMES
    assert set(tc_stats.metrics) == set(_ALL_METRICS)
    for metric in tc_stats.metrics.values():
        assert metric.status == "below_floor"
        assert metric.floor_n == _BELOW_ANCHOR_GAMES
        assert metric.floor_required == MEDIAN_ANCHOR_MIN_GAMES
        assert metric.percentile is None


def test_status_daily_excluded_from_anchor_count() -> None:
    """Chess.com Daily games count in ranked_games but not in anchor_games."""
    daily = _games(12, platform="chess.com", time_control_str="1/86400")
    live = _games(28, first_id=100, platform="chess.com", time_control_str="180+0")
    inputs = RankedInputs(games_by_tc={"blitz": daily + live})
    tc_stats = _tc(build_ranked_stats(inputs))
    assert tc_stats.ranked_games == 40
    assert tc_stats.anchor_games == 28
    assert tc_stats.metrics["score_gap"].status == "below_floor"
    assert tc_stats.metrics["score_gap"].floor_n == 28


def test_status_pending() -> None:
    """D-11: eval-dependent metric with no value while evals are pending -> pending."""
    inputs = _full_inputs(eval_pending=True, with_evals=False)
    response = build_ranked_stats(inputs)
    for metric_id in EVAL_DEPENDENT_METRICS:
        metric = _metric(response, metric_id)
        assert metric.value is None
        assert metric.status == "pending"
    # Stage A's score_gap needs no eval: it is not pending.
    assert _metric(response, "score_gap").status != "pending"


def test_status_clock_unranked() -> None:
    """D-11: eval-independent clock metric with a value and no persisted row -> unranked."""
    inputs = _full_inputs(eval_pending=True, with_evals=False)
    response = build_ranked_stats(inputs)
    for metric_id in _CLOCK_METRICS:
        metric = _metric(response, metric_id)
        assert metric.value is not None
        assert metric.status == "unranked"
        assert metric.percentile is None


def test_status_metric_floor() -> None:
    """Anchor present, metric floor_n 22 < 30 -> below_floor with that binding count."""
    inputs = _full_inputs(n_endgame=_METRIC_FLOOR_SHORT_GAMES)
    metric = _metric(build_ranked_stats(inputs), "clock_gap")
    assert metric.value is not None
    assert metric.status == "below_floor"
    assert metric.floor_n == _METRIC_FLOOR_SHORT_GAMES
    assert metric.floor_required == 30


def test_status_ranked() -> None:
    """A persisted row with a percentile and a met floor -> ranked, percentile passed through."""
    inputs = _full_inputs(percentile_rows=_percentiles(("clock_gap", "score_gap")))
    response = build_ranked_stats(inputs)
    for metric_id in ("clock_gap", "score_gap"):
        metric = _metric(response, metric_id)
        assert metric.status == "ranked"
        assert metric.percentile == _PERCENTILE


def test_status_row_without_percentile() -> None:
    """A persisted row whose percentile is None (no CDF cell) -> unranked, no percentile."""
    inputs = _full_inputs(percentile_rows=_percentiles(("clock_gap",), percentile=None))
    metric = _metric(build_ranked_stats(inputs), "clock_gap")
    assert metric.status == "unranked"
    assert metric.percentile is None


def test_status_since_window_never_ranked() -> None:
    """The insights window ignores persisted percentiles: percentile None everywhere."""
    inputs = _full_inputs(percentile_rows=_percentiles())
    since = _NOW - datetime.timedelta(days=60)
    response = build_ranked_stats(inputs, since=since)
    assert _tc(response).ranked_games < len(inputs.games_by_tc["blitz"])
    for metric in _tc(response).metrics.values():
        assert metric.percentile is None
        assert metric.status != "ranked"


# ── TC listing (D-14, D-10) ──────────────────────────────────────────────────


def test_tcs_listed_order_and_omission() -> None:
    """Zero-game TCs are omitted; the list is ordered bullet, blitz, rapid, classical."""
    inputs = RankedInputs(
        games_by_tc={
            "classical": _games(3),
            "bullet": _games(5),
            "blitz": [],
            "rapid": _games(2),
        }
    )
    assert [t.tc for t in build_ranked_stats(inputs).tcs] == ["bullet", "rapid", "classical"]


def test_tcs_listed_empty_sample() -> None:
    """D-10: an empty ranked sample returns tcs == []."""
    assert build_ranked_stats(RankedInputs(games_by_tc={})).tcs == []
    empty = RankedInputs(games_by_tc={"bullet": [], "blitz": [], "rapid": [], "classical": []})
    assert build_ranked_stats(empty).tcs == []


# ── Bucket WDL vs rate (D-00b) ───────────────────────────────────────────────


def test_bucket_rate_consistency() -> None:
    """Each rate equals the value derived from the SAME bucket's W/D/L counts."""
    tc_stats = _tc(build_ranked_stats(_full_inputs()))
    by_bucket = {b.bucket: b for b in tc_stats.buckets}
    assert list(by_bucket) == ["conversion", "parity", "recovery"]
    conv, parity, recov = by_bucket["conversion"], by_bucket["parity"], by_bucket["recovery"]
    assert conv.games > 0 and parity.games > 0 and recov.games > 0
    assert tc_stats.metrics["conversion_rate"].value == pytest.approx(conv.wins / conv.games)
    assert tc_stats.metrics["parity_rate"].value == pytest.approx(
        (parity.wins + parity.draws / 2) / parity.games
    )
    assert tc_stats.metrics["recovery_rate"].value == pytest.approx(
        (recov.wins + recov.draws) / recov.games
    )
    for bucket in by_bucket.values():
        assert bucket.wins + bucket.draws + bucket.losses == bucket.games
    assert tc_stats.metrics["conversion_rate"].n == conv.games


# ── Popover statistics shapes (assumption A3) ────────────────────────────────


def test_ci_p_shapes() -> None:
    """Rates: Wilson CI only; net_flag_rate: nothing; every other metric: CI and p (n >= 10)."""
    metrics = _tc(build_ranked_stats(_full_inputs())).metrics
    for metric_id in ("conversion_rate", "parity_rate", "recovery_rate"):
        metric = metrics[metric_id]
        assert metric.ci_low is not None and metric.ci_high is not None
        assert metric.ci_low <= (metric.value or 0.0) <= metric.ci_high
        assert metric.p_value is None
    net_flag = metrics["net_flag_rate"]
    assert (net_flag.ci_low, net_flag.ci_high, net_flag.p_value) == (None, None, None)
    for metric_id in (
        "score_gap",
        "achievable_score_gap",
        "score_gap_conv",
        "score_gap_parity",
        "recovery_score_gap",
        "time_pressure_score_gap",
        "clock_gap",
    ):
        metric = metrics[metric_id]
        assert metric.value is not None
        assert metric.n >= 10, metric_id
        assert metric.ci_low is not None, metric_id
        assert metric.ci_high is not None, metric_id
        assert metric.p_value is not None, metric_id


# ── Timelines (D-03) ─────────────────────────────────────────────────────────

_TIMELINE_GAMES_PER_SIDE = 80
_TIMELINE_START = datetime.datetime(2026, 1, 5, tzinfo=datetime.timezone.utc)
_TIMELINE_SINCE = datetime.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc)


def _timeline_inputs() -> RankedInputs:
    """One game per day on each side over 80 days: the windows fill across the range."""
    games: list[RankedGameRow] = []
    endgame: list[PerfRow] = []
    non_endgame: list[PerfRow] = []
    for i in range(_TIMELINE_GAMES_PER_SIDE):
        day = _TIMELINE_START + datetime.timedelta(days=i)
        color = _color(i)
        for offset, side in ((0, endgame), (_TIMELINE_GAMES_PER_SIDE, non_endgame)):
            games.append(
                RankedGameRow(
                    game_id=offset + i + 1,
                    played_at=day,
                    platform="lichess",
                    time_control_str="180+0",
                    user_elo=1500,
                    eval_pending=False,
                )
            )
            side.append(
                PerfRow(
                    played_at=day,
                    result=_result(_outcome(i), color),
                    user_color=color,
                    platform="lichess",
                    time_control_bucket="blitz",
                )
            )
    return RankedInputs(
        games_by_tc={"blitz": games},
        endgame_rows=endgame,
        non_endgame_rows=non_endgame,
        anchors={"blitz": _ANCHOR},
    )


def test_since_trims_timeline_points() -> None:
    """Points before ``since`` are dropped while older rows still pre-fill the windows."""
    inputs = _timeline_inputs()
    full = _tc(build_ranked_stats(inputs))
    trimmed = _tc(build_ranked_stats(inputs, since=_TIMELINE_SINCE))
    cutoff = _TIMELINE_SINCE.date().isoformat()
    assert full.score_gap_timeline
    assert min(p.date for p in full.score_gap_timeline) < cutoff
    assert trimmed.score_gap_timeline
    assert all(p.date >= cutoff for p in trimmed.score_gap_timeline)
    assert all(p.date >= cutoff for combo in trimmed.elo_timeline for p in combo.points)
    # Pre-fill: the first kept point's trailing window still holds pre-cutoff games, so it
    # is larger than the count of endgame games played on or after the cutoff up to then.
    first_kept = trimmed.score_gap_timeline[0]
    games_since_cutoff = sum(1 for r in inputs.endgame_rows if r.played_at >= _TIMELINE_SINCE)
    assert first_kept.endgame_game_count > games_since_cutoff - _TIMELINE_GAMES_PER_SIDE // 2
    # Scalar metrics use only rows on or after ``since``.
    assert trimmed.ranked_games < full.ranked_games


def test_build_endgame_elo_combos_matches_overview_path() -> None:
    """The extracted combo builder equals the previous inline loop shape for the same inputs."""
    inputs = _timeline_inputs()
    asof = _asof_by_platform("blitz", inputs.games_by_tc["blitz"])
    cutoff = _TIMELINE_SINCE.date().isoformat()
    combos = build_endgame_elo_combos(inputs.endgame_rows, inputs.non_endgame_rows, asof, cutoff)

    expected = []
    for platform_name, tc in _ENDGAME_ELO_COMBO_ORDER:
        dates, ratings = asof.get((platform_name, tc), ([], []))
        gap = compute_score_gap_timeline(
            [r for r in inputs.endgame_rows if (r[3], r[4]) == (platform_name, tc)],
            [r for r in inputs.non_endgame_rows if (r[3], r[4]) == (platform_name, tc)],
            ENDGAME_ELO_TIMELINE_WINDOW,
            cutoff_str=cutoff,
        )
        points = _compute_endgame_elo_weekly_series(gap, dates, ratings, cutoff_str=cutoff)
        if points:
            expected.append((f"{platform_name.replace('.', '_')}_{tc}", points))
    assert expected, "synthetic inputs must produce at least one combo"
    assert [(c.combo_key, c.points) for c in combos] == expected
    assert [c.time_control for c in combos] == ["blitz"]


# ── Time pressure curve, Clock Gap timeline, type categories (D-05 / D-06) ───

_QUINTILE_COUNT = 5
_TYPE_ROOK = 1
_TYPE_PAWN = 3
_TYPE_MIXED = 5
_TYPE_ROOK_GAMES = 7
_TYPE_PAWN_GAMES = 4
_TYPE_MIXED_GAMES = 3


def _two_tc_clock_inputs() -> RankedInputs:
    """Blitz carries clock rows; bullet is a listed TC with ranked games but no clock rows."""
    return RankedInputs(
        games_by_tc={"bullet": _games(40, first_id=1000), "blitz": _games(60)},
        clock_rows=_clock_rows(range(60), "blitz"),
        anchors={"bullet": _ANCHOR, "blitz": _ANCHOR},
    )


def test_quintile_curve_from_ranked_clock_rows() -> None:
    """Five bullets in Q0..Q4 order, equal to the shared builder over the same rows."""
    inputs = _two_tc_clock_inputs()
    curve = _tc(build_ranked_stats(inputs)).time_pressure.quintiles
    assert len(curve) == _QUINTILE_COUNT
    assert [b.quintile_index for b in curve] == list(range(_QUINTILE_COUNT))
    _, user_wdl, opp_wdl, shared = iterate_clock_rows(inputs.clock_rows)
    assert curve == build_quintile_bullets("blitz", user_wdl, opp_wdl, shared)


def test_clock_diff_timeline_per_tc() -> None:
    """Clock Gap points derive only from the TC's own rows; a TC without clock rows is empty."""
    inputs = _two_tc_clock_inputs()
    response = build_ranked_stats(inputs)
    blitz, bullet = _tc(response, "blitz"), _tc(response, "bullet")
    assert blitz.clock_diff_timeline
    assert blitz.clock_diff_timeline == compute_clock_diff_timeline(inputs.clock_rows).points
    assert bullet.clock_diff_timeline == []
    assert bullet.time_pressure.quintiles == []


def _entry_ns(game_id: int, endgame_class: int, tc: str) -> SimpleNamespace:
    """Attribute-style entry row (the production SA Row shape)."""
    return SimpleNamespace(
        game_id=game_id,
        endgame_class=endgame_class,
        result="1-0",
        user_color="white",
        eval_cp=0,
        eval_mate=None,
        next_entry_eval_cp=None,
        next_entry_eval_mate=None,
        played_at=_NOW,
        time_control_bucket=tc,
    )


def _type_inputs(*, with_endgames: bool = True) -> RankedInputs:
    entry_rows: list[SimpleNamespace] = []
    if with_endgames:
        game_id = 1
        for endgame_class, count in (
            (_TYPE_ROOK, _TYPE_ROOK_GAMES),
            (_TYPE_PAWN, _TYPE_PAWN_GAMES),
            (_TYPE_MIXED, _TYPE_MIXED_GAMES),
        ):
            for _ in range(count):
                entry_rows.append(_entry_ns(game_id, endgame_class, "blitz"))
                game_id += 1
        entry_rows.append(_entry_ns(game_id, _TYPE_ROOK, "bullet"))
    return RankedInputs(
        games_by_tc={"bullet": _games(40, first_id=1000), "blitz": _games(60)},
        entry_rows=entry_rows,
        anchors={"bullet": _ANCHOR, "blitz": _ANCHOR},
    )


def test_type_categories_per_tc() -> None:
    """Type rows equal the shared aggregator for the TC; mixed and pawnless are excluded."""
    inputs = _type_inputs()
    response = build_ranked_stats(inputs)
    blitz = _tc(response, "blitz")
    assert blitz.type_categories == aggregate_endgame_stats_by_tc(inputs.entry_rows)["blitz"]
    by_class = {c.endgame_class: c.total for c in blitz.type_categories}
    assert by_class == {"rook": _TYPE_ROOK_GAMES, "pawn": _TYPE_PAWN_GAMES}
    # The bullet rook span never leaks into blitz.
    assert [c.total for c in _tc(response, "bullet").type_categories] == [1]


def test_type_categories_empty_without_endgames() -> None:
    """A TC with ranked games but no endgame spans has no type rows."""
    response = build_ranked_stats(_type_inputs(with_endgames=False))
    assert _tc(response, "blitz").type_categories == []
