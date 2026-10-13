"""On-read ranked Endgame Stats service (Phase 238, SEED-196).

``get_ranked_stats`` serves ``GET /api/endgames/ranked-stats``: for every time
control with at least one ranked-sample game it computes the 11 peer-ranked
metric values ON READ from the canonical ranked slice (rated, human, opponents
within 100 Elo, last 36 months, at most 3000 games per TC). The ranked games are
selected by ``ranked_games_sql`` which composes the unchanged Stage A/B prelude,
so every value describes the same games the persisted percentiles rank (D-00b,
D-07). Percentiles are read as Stage A/B wrote them (D-07, D-08).

Shape (pipeline seams, nesting depth <= 4):

* ``fetch_ranked_inputs``: sequential DB reads (one AsyncSession, no gather) into
  a ``RankedInputs`` bundle.
* ``build_ranked_stats``: pure, no DB. Per TC: canonical-mode metric helpers,
  rank status, response models.
* ``get_ranked_stats``: the two composed.

Definition drift is the real risk: the older Python aggregators in
``endgame_service`` differ from the Stage A/B CTEs (NULL-eval routing, sub-800
floor, 2x clock clamp, per-span vs per-game gaps). Every helper here mirrors its
CTE line for line, and ``tests/services/test_endgame_ranked_parity.py`` is the
numeric gate against ``_compute_metric_for_user_per_tc``.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Literal, TypedDict, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.endgame_ranked_repository import RankedGameRow, fetch_ranked_games
from app.repositories.endgame_repository import (
    query_clock_stats_rows,
    query_endgame_bucket_rows,
    query_endgame_entry_rows,
    query_endgame_performance_rows,
)
from app.repositories.user_benchmark_percentiles_repository import (
    PercentileRow,
    fetch_for_user,
)
from app.repositories.user_rating_anchors_repository import (
    RatingAnchorRow,
    fetch_anchors_for_user,
)
from app.schemas.endgames import (
    ClockDiffTimelinePoint,
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameRankedStatsResponse,
    MaterialBucket,
    RankedBucketOut,
    RankedEntryFlowOut,
    RankedMetricOut,
    RankedOverallOut,
    RankedTcStats,
    RankedTimePressureOut,
    RankStatus,
    RatingAnchorOut,
    ScoreGapTimelinePoint,
)
from app.repositories.stats_repository import EVAL_OUTLIER_TRIM_CP
from app.services.canonical_slice_sql import (
    ACHIEVABLE_MIN_GAMES,
    CLOCK_GAP_MIN_POOL_N,
    MEDIAN_ANCHOR_MIN_GAMES,
    MINIMUM_RATE_BUCKET_SPANS,
    NET_FLAG_RATE_MIN_POOL_N,
    SCORE_GAP_BUCKET_MIN_SPANS,
    SCORE_GAP_MIN_ENDGAME_N,
    SUB_800_FLOOR,
    TIME_PRESSURE_CLOCK_PCT_THRESHOLD,
    TIME_PRESSURE_MIN_PRESSURED_N,
    TimeControlBucket,
)
from app.services.endgame_service import (
    ENDGAME_ELO_TIMELINE_WINDOW,
    EVAL_ADVANTAGE_THRESHOLD,
    EVAL_CLIP_MAX_CP,
    SCORE_GAP_TIMELINE_WINDOW,
    aggregate_endgame_stats_by_tc,
    build_endgame_elo_combos,
    build_quintile_bullets,
    build_wdl_summary,
    compute_clock_diff_timeline,
    compute_score_gap_timeline,
    compute_span_gap,
    extract_entry_clocks,
    iterate_clock_rows,
)
from app.services.eval_utils import eval_cp_to_expected_score
from app.repositories.benchmark_cohort_cdf_repository import load_cohort_cells
from app.services.endgame_zones import PER_CLASS_TC_GAUGE_ZONES
from app.services.global_percentile_cdf import (
    BREAKPOINT_PERCENTILES,
    CdfMetricId,
    round_anchor_to_grid,
)
from app.services.openings_service import derive_user_result
from app.services.score_confidence import (
    VERDICT_CI_Z_99,
    ci_excludes,
    compute_paired_difference_test,
    compute_score_difference_test,
    wilson_bounds,
)

# Fixed display / iteration order for time controls (D-14): fastest to slowest.
RANKED_TC_ORDER: Final[tuple[TimeControlBucket, ...]] = ("bullet", "blitz", "rapid", "classical")

# Chess.com Daily games carry time_control_str "1/<seconds>"; the anchor CTE drops them
# (canonical_slice_sql.py median anchor: NOT (platform='chess.com' AND str LIKE '1/%')).
_CHESSCOM_PLATFORM: Final[str] = "chess.com"
_DAILY_TIME_CONTROL_PREFIX: Final[str] = "1/"

_OUTCOME_SCORE: Final[dict[Literal["win", "draw", "loss"], float]] = {
    "win": 1.0,
    "draw": 0.5,
    "loss": 0.0,
}


@dataclass(frozen=True)
class RankedInputs:
    """Everything the pure builder needs, fetched once per request.

    The row lists hold rows for ALL time controls (one query each, restricted to
    the union of the ranked ids); the builder groups them by ``time_control_bucket``.
    ``entry_rows`` / ``bucket_rows`` / ``clock_rows`` are empty until the canonical
    metric families that consume them are enabled.
    """

    games_by_tc: dict[TimeControlBucket, list[RankedGameRow]]
    endgame_rows: list[Any] = field(default_factory=list)
    non_endgame_rows: list[Any] = field(default_factory=list)
    entry_rows: list[Any] = field(default_factory=list)
    bucket_rows: list[Any] = field(default_factory=list)
    clock_rows: list[Any] = field(default_factory=list)
    percentile_rows: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = field(
        default_factory=dict
    )
    anchors: dict[TimeControlBucket, RatingAnchorRow] = field(default_factory=dict)
    # Phase 239 D-14: cohort p50 of each raw-rate metric at the user's anchor, the null
    # the rate's 99% CI is tested against. Missing key = no cohort cell, no verdict gate.
    cohort_medians: dict[tuple[CdfMetricId, TimeControlBucket], float] = field(default_factory=dict)


class _RowQueryKwargs(TypedDict):
    """Keyword arguments shared by the four ranked-id row queries (typed ``**`` unpacking)."""

    user_id: int
    time_control: Sequence[str] | None
    platform: Sequence[str] | None
    rated: bool | None
    opponent_type: Literal["human", "bot", "all"]
    from_date: datetime.date | None
    to_date: datetime.date | None
    game_ids: Sequence[int]


@dataclass(frozen=True)
class _MetricCore:
    """A metric's value, binding counts and footer statistics before rank status.

    ci_low / ci_high / p_value feed the popover footer (planner assumption A3): rates
    carry a Wilson CI only, score_gap and time_pressure a two-sample CI + p, the paired
    metrics (net_flag_rate included since Phase 239 D-14) a paired CI + p. Every CI is
    99% (D-14), the level the red/green verdict gate uses.
    """

    value: float | None
    n: int
    floor_n: int
    floor_required: int
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None


# ---------------------------------------------------------------------------
# Fetch (DB)
# ---------------------------------------------------------------------------


async def fetch_ranked_inputs(session: AsyncSession, *, user_id: int) -> RankedInputs:
    """Read the ranked sample and everything derived from it, sequentially.

    One AsyncSession means one connection: queries run one after another (CLAUDE.md,
    never ``asyncio.gather`` on a session). The row queries run ONCE with the union
    of the per-TC ranked ids (``game_ids``), then the builder groups by TC.
    """
    games_by_tc: dict[TimeControlBucket, list[RankedGameRow]] = {}
    for tc in RANKED_TC_ORDER:
        games_by_tc[tc] = await fetch_ranked_games(session, user_id=user_id, tc=tc)
    union_ids = [g.game_id for games in games_by_tc.values() for g in games]

    # Neutral filters: the id set alone defines the population (D-01, D-07). The ranked
    # games are rated and human by construction, so no filter is needed on those axes.
    row_kwargs = _RowQueryKwargs(
        user_id=user_id,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="all",
        from_date=None,
        to_date=None,
        game_ids=union_ids,
    )
    endgame_rows: list[Any] = []
    non_endgame_rows: list[Any] = []
    entry_rows: list[Any] = []
    bucket_rows: list[Any] = []
    clock_rows: list[Any] = []
    if union_ids:
        endgame_rows, non_endgame_rows = await query_endgame_performance_rows(session, **row_kwargs)
        entry_rows = await query_endgame_entry_rows(session, **row_kwargs)
        bucket_rows = await query_endgame_bucket_rows(session, **row_kwargs)
        clock_rows = await query_clock_stats_rows(session, **row_kwargs)
    percentile_rows = await fetch_for_user(session, user_id=user_id)
    anchors = await fetch_anchors_for_user(session, user_id=user_id)
    cohort_medians = await _fetch_rate_cohort_medians(session, anchors)
    return RankedInputs(
        games_by_tc=games_by_tc,
        endgame_rows=endgame_rows,
        non_endgame_rows=non_endgame_rows,
        entry_rows=entry_rows,
        bucket_rows=bucket_rows,
        clock_rows=clock_rows,
        percentile_rows=percentile_rows,
        anchors=anchors,
        cohort_medians=cohort_medians,
    )


# Raw-rate metrics: no natural 0 null, so the D-14 gate tests them against the cohort p50.
RATE_METRICS: Final[frozenset[CdfMetricId]] = frozenset(
    {"conversion_rate", "parity_rate", "recovery_rate"}
)
_MEDIAN_PERCENTILE: Final[float] = 50.0
_MEDIAN_BREAKPOINT_INDEX: Final[int] = BREAKPOINT_PERCENTILES.index(_MEDIAN_PERCENTILE)


async def _fetch_rate_cohort_medians(
    session: AsyncSession, anchors: dict[TimeControlBucket, RatingAnchorRow]
) -> dict[tuple[CdfMetricId, TimeControlBucket], float]:
    """Cohort p50 per (raw-rate metric, TC) at the user's anchor, in one batched read."""
    rounded = {tc: round_anchor_to_grid(a.anchor_rating) for tc, a in anchors.items()}
    cells = await load_cohort_cells(session, sorted(set(rounded.values())), list(rounded))
    medians: dict[tuple[CdfMetricId, TimeControlBucket], float] = {}
    for tc, anchor_elo in rounded.items():
        for metric in RATE_METRICS:
            table = cells.get((metric, anchor_elo, tc))
            if table is not None:
                medians[(metric, tc)] = table.breakpoints[_MEDIAN_BREAKPOINT_INDEX]
    return medians


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

_MATERIAL_BUCKETS: Final[tuple[MaterialBucket, ...]] = ("conversion", "parity", "recovery")

# Metric id carrying each entry-eval bucket's rate / per-span score gap.
_RATE_METRIC: Final[dict[MaterialBucket, CdfMetricId]] = {
    "conversion": "conversion_rate",
    "parity": "parity_rate",
    "recovery": "recovery_rate",
}
_GAP_METRIC: Final[dict[MaterialBucket, CdfMetricId]] = {
    "conversion": "score_gap_conv",
    "parity": "score_gap_parity",
    "recovery": "recovery_score_gap",
}

_PAWNS_PER_CP: Final[float] = 100.0

# Metrics that need entry evals (Stage B eval-dependent). While a TC still has evals
# pending, one of these without a value is "pending" (D-11), not "below the floor".
# The clock families are Stage B but eval-INDEPENDENT: their value is always computable,
# so before a percentile row exists they land in "unranked", never "pending".
EVAL_DEPENDENT_METRICS: Final[frozenset[CdfMetricId]] = frozenset(
    {
        "achievable_score_gap",
        "score_gap_conv",
        "score_gap_parity",
        "recovery_score_gap",
        "conversion_rate",
        "parity_rate",
        "recovery_rate",
    }
)


def _score_of(row: Any) -> float:
    """User score (1 / 0.5 / 0) of a row exposing ``result`` and ``user_color``."""
    return _OUTCOME_SCORE[derive_user_result(row.result, row.user_color)]


def _sign(user_color: Literal["white", "black"]) -> int:
    """+1 for white, -1 for black: turns a white-perspective eval into the user's."""
    return 1 if user_color == "white" else -1


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _paired_core(diffs: Sequence[float], floor_required: int) -> _MetricCore:
    """Mean of per-unit values with the paired one-sample CI + p against 0.

    n and the binding floor count are the unit count; no units means no value.
    """
    n = len(diffs)
    if n == 0:
        return _MetricCore(value=None, n=0, floor_n=0, floor_required=floor_required)
    mean_d, p_value, ci_low, ci_high = compute_paired_difference_test(diffs, z=VERDICT_CI_Z_99)
    return _MetricCore(
        value=mean_d,
        n=n,
        floor_n=n,
        floor_required=floor_required,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
    )


def _wdl_counts(scores: Sequence[float]) -> tuple[int, int, int]:
    """(wins, draws, losses) from 1 / 0.5 / 0 scores."""
    wins = sum(1 for score in scores if score == 1.0)
    draws = sum(1 for score in scores if score == 0.5)
    return wins, draws, len(scores) - wins - draws


def _rows_for_tc(rows: Sequence[Any], tc: TimeControlBucket) -> list[Any]:
    return [row for row in rows if row.time_control_bucket == tc]


def _restrict_to_since(inputs: RankedInputs, since: datetime.datetime) -> RankedInputs:
    """Keep only games / rows played at or after ``since`` (insights last_3mo window).

    The windowed sample never carries persisted percentiles (D-04): the stored
    percentile ranks the full ranked sample, not a sub-window.
    """
    games_by_tc = {
        tc: [g for g in games if g.played_at >= since] for tc, games in inputs.games_by_tc.items()
    }
    keep_ids = {g.game_id for games in games_by_tc.values() for g in games}
    return RankedInputs(
        games_by_tc=games_by_tc,
        endgame_rows=[r for r in inputs.endgame_rows if r.played_at >= since],
        non_endgame_rows=[r for r in inputs.non_endgame_rows if r.played_at >= since],
        entry_rows=[r for r in inputs.entry_rows if r.game_id in keep_ids],
        bucket_rows=[r for r in inputs.bucket_rows if r.game_id in keep_ids],
        clock_rows=[r for r in inputs.clock_rows if r.game_id in keep_ids],
        percentile_rows={},
        anchors=inputs.anchors,
        cohort_medians=inputs.cohort_medians,
    )


def _is_anchor_game(game: RankedGameRow) -> bool:
    """Mirror of the anchor CTE's Daily exclusion.

    The CTE keeps a game iff ``NOT (platform = 'chess.com' AND time_control_str LIKE
    '1/%')``. For a chess.com game with a NULL string the predicate is NULL, so the
    game is dropped as well; a non-chess.com game is always kept.
    """
    if game.platform != _CHESSCOM_PLATFORM:
        return True
    return game.time_control_str is not None and not game.time_control_str.startswith(
        _DAILY_TIME_CONTROL_PREFIX
    )


def _anchor_out(row: RatingAnchorRow | None) -> RatingAnchorOut | None:
    if row is None:
        return None
    return RatingAnchorOut(
        anchor_rating=row.anchor_rating,
        n_chesscom_games=row.n_chesscom_games,
        n_lichess_games=row.n_lichess_games,
        chesscom_median_native=row.chesscom_median_native,
        lichess_median_native=row.lichess_median_native,
    )


# ---------------------------------------------------------------------------
# Canonical-mode metric helpers. Each mirrors its Stage A/B CTE line for line
# (canonical_slice_sql.py); parity is gated by test_endgame_ranked_parity.py.
# ---------------------------------------------------------------------------


def _score_gap_core(endgame_rows: Sequence[Any], non_endgame_rows: Sequence[Any]) -> _MetricCore:
    """Endgame score minus non-endgame score (``per_user_cte_score_gap_tc``).

    n is the endgame game count; the binding floor count is the smaller of the two
    sides (the CTE requires both >= 30).
    """
    eg_scores = [_score_of(r) for r in endgame_rows]
    ne_scores = [_score_of(r) for r in non_endgame_rows]
    eg_n, ne_n = len(eg_scores), len(ne_scores)
    value: float | None = None
    p_value = ci_low = ci_high = None
    if eg_n > 0 and ne_n > 0:
        value = sum(eg_scores) / eg_n - sum(ne_scores) / ne_n
        p_value, ci_low, ci_high = compute_score_difference_test(
            *_wdl_counts(eg_scores), eg_n, *_wdl_counts(ne_scores), ne_n, z=VERDICT_CI_Z_99
        )
    return _MetricCore(
        value=value,
        n=eg_n,
        floor_n=min(eg_n, ne_n),
        floor_required=SCORE_GAP_MIN_ENDGAME_N,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
    )


def _classify_entry(eval_cp: int | None, eval_mate: int | None, sign: int) -> MaterialBucket:
    """Entry-eval bucket exactly as the CTEs' CASE: a mate decides first, then +-100 cp.

    Callers have already dropped rows with both evals NULL (the CTEs exclude them).
    """
    if eval_mate is not None:
        return "conversion" if eval_mate * sign > 0 else "recovery"
    signed_cp = cast(int, eval_cp) * sign
    if signed_cp >= EVAL_ADVANTAGE_THRESHOLD:
        return "conversion"
    if signed_cp <= -EVAL_ADVANTAGE_THRESHOLD:
        return "recovery"
    return "parity"


def _achievable_expected(row: Any) -> float | None:
    """Expected score at the first endgame ply (``per_user_cte_achievable_tc`` d_i term).

    Mate scores 1.0 / 0.0 for the user; a cp eval goes through the Lichess sigmoid only
    when |cp| < 2000, otherwise the game has no d_i. No 800 floor in this CTE.
    """
    sign = _sign(row.user_color)
    if row.eval_mate is not None and row.eval_mate * sign > 0:
        return 1.0
    if row.eval_mate is not None and row.eval_mate * sign < 0:
        return 0.0
    if row.eval_cp is not None and abs(row.eval_cp) < EVAL_CLIP_MAX_CP:
        return eval_cp_to_expected_score(row.eval_cp, row.user_color)
    return None


def _entry_eval_pawns(bucket_rows: Sequence[Any]) -> tuple[float | None, int]:
    """Mean user-perspective entry eval in pawns over cp-only rows, outliers trimmed."""
    pawns = [
        _sign(row.user_color) * row.eval_cp / _PAWNS_PER_CP
        for row in bucket_rows
        if row.eval_mate is None
        and row.eval_cp is not None
        and abs(row.eval_cp) < EVAL_OUTLIER_TRIM_CP
    ]
    return _mean(pawns), len(pawns)


def _achievable_metric(bucket_rows: Sequence[Any]) -> tuple[_MetricCore, RankedEntryFlowOut]:
    """``achievable_score_gap`` plus the entry flow, from one per-game cohort.

    d_i = game score minus expected score at the game's first endgame ply. The entry
    flow's expected / actual means run over the SAME non-null d_i cohort, so
    ``actual - expected == value`` and ``n`` agree exactly.
    """
    expected: list[float] = []
    actual: list[float] = []
    for row in bucket_rows:
        expected_score = _achievable_expected(row)
        if expected_score is None:
            continue
        expected.append(expected_score)
        actual.append(_score_of(row))
    core = _paired_core(
        [a - e for a, e in zip(actual, expected, strict=True)], ACHIEVABLE_MIN_GAMES
    )
    eval_mean, eval_n = _entry_eval_pawns(bucket_rows)
    flow = RankedEntryFlowOut(
        entry_eval_mean_pawns=eval_mean,
        entry_eval_n=eval_n,
        expected_score=_mean(expected),
        actual_score=_mean(actual),
        n=core.n,
    )
    return core, flow


def _eligible_for_eval_buckets(row: Any, elo_by_game: dict[int, int]) -> bool:
    """CTE gate shared by the rates and bucket gaps: an entry eval exists, user >= 800."""
    if row.eval_cp is None and row.eval_mate is None:
        return False
    return elo_by_game.get(row.game_id, 0) >= SUB_800_FLOOR


def _rate_of(bucket: MaterialBucket, wins: int, draws: int, n: int) -> float | None:
    """Conversion = wins/n, parity = (wins + draws/2)/n, recovery = (wins + draws)/n."""
    if n == 0:
        return None
    if bucket == "conversion":
        return wins / n
    if bucket == "parity":
        return (wins + 0.5 * draws) / n
    return (wins + draws) / n


def _wilson_interval(value: float | None, n: int) -> tuple[float | None, float | None]:
    """Wilson 99% bounds for a rate (D-14). No p-value: a rate has no natural null; the
    verdict gate tests the CI against the cohort median instead."""
    if value is None or n <= 0:
        return None, None
    return wilson_bounds(value, n, z=VERDICT_CI_Z_99)


def _rate_metrics(
    bucket_rows: Sequence[Any], elo_by_game: dict[int, int]
) -> tuple[dict[CdfMetricId, _MetricCore], list[RankedBucketOut]]:
    """Conversion / parity / recovery rates and their W/D/L counts from the same games.

    One row per endgame game at its first endgame ply; NULL-eval and sub-800 games are
    excluded (the CTEs do), unlike the legacy Python path that routed NULL to parity.
    """
    tallies: dict[MaterialBucket, dict[str, int]] = {
        b: {"win": 0, "draw": 0, "loss": 0} for b in _MATERIAL_BUCKETS
    }
    for row in bucket_rows:
        if not _eligible_for_eval_buckets(row, elo_by_game):
            continue
        bucket = _classify_entry(row.eval_cp, row.eval_mate, _sign(row.user_color))
        tallies[bucket][derive_user_result(row.result, row.user_color)] += 1
    cores: dict[CdfMetricId, _MetricCore] = {}
    buckets: list[RankedBucketOut] = []
    for bucket in _MATERIAL_BUCKETS:
        tally = tallies[bucket]
        n = sum(tally.values())
        rate = _rate_of(bucket, tally["win"], tally["draw"], n)
        ci_low, ci_high = _wilson_interval(rate, n)
        cores[_RATE_METRIC[bucket]] = _MetricCore(
            value=rate,
            n=n,
            floor_n=n,
            floor_required=MINIMUM_RATE_BUCKET_SPANS,
            ci_low=ci_low,
            ci_high=ci_high,
        )
        buckets.append(
            RankedBucketOut(
                bucket=bucket,
                games=n,
                wins=tally["win"],
                draws=tally["draw"],
                losses=tally["loss"],
            )
        )
    return cores, buckets


def _bucket_gap_metrics(
    entry_rows: Sequence[Any], elo_by_game: dict[int, int]
) -> dict[CdfMetricId, _MetricCore]:
    """Per-bucket mean span score gap (``per_user_cte_score_gap_bucket_tc``).

    One row per (game, endgame class) span; the exit eval is the NEXT span's entry eval
    (LEAD), or the game score for a terminal span. No 2000 cp clip, matching the CTE.
    """
    gaps: dict[MaterialBucket, list[float]] = {b: [] for b in _MATERIAL_BUCKETS}
    for row in entry_rows:
        if not _eligible_for_eval_buckets(row, elo_by_game):
            continue
        gap = compute_span_gap(
            row.eval_cp,
            row.eval_mate,
            row.next_entry_eval_cp,
            row.next_entry_eval_mate,
            row.result,
            row.user_color,
        )
        if gap is None:
            continue
        gaps[_classify_entry(row.eval_cp, row.eval_mate, _sign(row.user_color))].append(gap)
    return {
        _GAP_METRIC[bucket]: _paired_core(gaps[bucket], SCORE_GAP_BUCKET_MIN_SPANS)
        for bucket in _MATERIAL_BUCKETS
    }


@dataclass(frozen=True)
class _ClockEntry:
    """One endgame game with both entry clocks readable and a positive base clock."""

    score: float
    user_clock: float
    opp_clock: float
    base: float


def _clock_entries(clock_rows: Sequence[Any]) -> list[_ClockEntry]:
    """Games usable for clock_gap / time pressure: base > 0, both entry clocks non-null.

    NO clamp of clocks above 2x base (the legacy Python path clamped; the CTEs do not).
    """
    entries: list[_ClockEntry] = []
    for row in clock_rows:
        base = row.base_time_seconds
        if base is None or base <= 0:
            continue
        user_clock, opp_clock = extract_entry_clocks(
            list(row.ply_array), list(row.clock_array), row.user_color
        )
        if user_clock is None or opp_clock is None:
            continue
        entries.append(
            _ClockEntry(
                score=_score_of(row),
                user_clock=float(user_clock),
                opp_clock=float(opp_clock),
                base=float(base),
            )
        )
    return entries


def _clock_gap_metric(entries: Sequence[_ClockEntry]) -> _MetricCore:
    """Mean (user clock - opponent clock) / base clock at endgame entry."""
    return _paired_core(
        [(e.user_clock - e.opp_clock) / e.base for e in entries], CLOCK_GAP_MIN_POOL_N
    )


def _net_flag_per_game(row: Any) -> float:
    """+1 for a timeout win, -1 for a timeout loss, 0 for any other endgame game."""
    if row.termination != "timeout":
        return 0.0
    result = derive_user_result(row.result, row.user_color)
    if result == "win":
        return 1.0
    return -1.0 if result == "loss" else 0.0


def _net_flag_metric(clock_rows: Sequence[Any]) -> _MetricCore:
    """(timeout wins - timeout losses) / endgame games.

    The denominator is EVERY endgame game of the TC: the CTE has no base-clock check.
    Phase 239 D-14: the mean of the per-game +1 / 0 / -1 values is the same number, and
    the paired test on them gives the CI the verdict gate needs (it had none before).
    """
    return _paired_core([_net_flag_per_game(row) for row in clock_rows], NET_FLAG_RATE_MIN_POOL_N)


def _time_pressure_score_gap_metric(entries: Sequence[_ClockEntry]) -> _MetricCore:
    """User-pressured score minus opponent-pressured score (clock < 40% of base).

    The opponent side mirrors the user score (1 - score). Dual floor: n is the smaller
    of the two pressured counts. The footer test treats the two sides as samples that
    share the games where BOTH players were pressured (covariance correction).
    """
    user_flags = [e.user_clock / e.base < TIME_PRESSURE_CLOCK_PCT_THRESHOLD for e in entries]
    opp_flags = [e.opp_clock / e.base < TIME_PRESSURE_CLOCK_PCT_THRESHOLD for e in entries]
    user_pressured = [e.score for e, flag in zip(entries, user_flags, strict=True) if flag]
    opp_pressured = [1.0 - e.score for e, flag in zip(entries, opp_flags, strict=True) if flag]
    shared_n = sum(1 for u, o in zip(user_flags, opp_flags, strict=True) if u and o)
    user_mean, opp_mean = _mean(user_pressured), _mean(opp_pressured)
    value = user_mean - opp_mean if user_mean is not None and opp_mean is not None else None
    n = min(len(user_pressured), len(opp_pressured))
    p_value, ci_low, ci_high = compute_score_difference_test(
        *_wdl_counts(user_pressured),
        len(user_pressured),
        *_wdl_counts(opp_pressured),
        len(opp_pressured),
        shared_n=shared_n,
        z=VERDICT_CI_Z_99,
    )
    return _MetricCore(
        value=value,
        n=n,
        floor_n=n,
        floor_required=TIME_PRESSURE_MIN_PRESSURED_N,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
    )


# ---------------------------------------------------------------------------
# Timelines (D-03): the same pure helpers the filtered path uses, fed ranked rows.
# ---------------------------------------------------------------------------


def _cutoff_str(since: datetime.datetime | None) -> str | None:
    """YYYY-MM-DD cutoff for timeline output; ``None`` keeps every point."""
    return since.date().isoformat() if since is not None else None


def _asof_by_platform(
    tc: TimeControlBucket, games: Sequence[RankedGameRow]
) -> dict[tuple[str, str], tuple[list[datetime.datetime], list[int]]]:
    """Per-(platform, TC) parallel (dates, ratings) arrays for the Actual ELO asof-join.

    Built from the TC's ranked games only, so Actual ELO comes from the same games
    that feed the Endgame Score Gap series. Sorted chronologically (bisect needs it).
    """
    by_platform: dict[str, list[RankedGameRow]] = {}
    for game in games:
        by_platform.setdefault(game.platform, []).append(game)
    asof: dict[tuple[str, str], tuple[list[datetime.datetime], list[int]]] = {}
    for platform, platform_games in by_platform.items():
        ordered = sorted(platform_games, key=lambda g: g.played_at)
        asof[(platform, tc)] = ([g.played_at for g in ordered], [g.user_elo for g in ordered])
    return asof


def _score_gap_timeline_points(
    endgame_rows: Sequence[Any], non_endgame_rows: Sequence[Any], since: datetime.datetime | None
) -> list[ScoreGapTimelinePoint]:
    """Endgame Score Gap over Time for one TC from ranked rows (D-03).

    ``endgame_rows`` / ``non_endgame_rows`` are the TC's FULL ranked rows: rolling
    windows pre-fill from older ranked games and points before ``since`` are dropped,
    mirroring the overview cutoff semantics. The first points can fall under
    MIN_GAMES_FOR_TIMELINE because the ranked sample has no older pre-fill; expected.
    """
    return compute_score_gap_timeline(
        endgame_rows, non_endgame_rows, SCORE_GAP_TIMELINE_WINDOW, _cutoff_str(since)
    )


def _elo_timeline_combos(
    tc: TimeControlBucket,
    games: Sequence[RankedGameRow],
    endgame_rows: Sequence[Any],
    non_endgame_rows: Sequence[Any],
    since: datetime.datetime | None,
) -> list[EndgameEloTimelineCombo]:
    """Endgame ELO Timeline combos (chess.com / lichess) for one TC from ranked games (D-03)."""
    return build_endgame_elo_combos(
        endgame_rows, non_endgame_rows, _asof_by_platform(tc, games), _cutoff_str(since)
    )


# ---------------------------------------------------------------------------
# Time pressure curve, Clock Gap timeline, Endgame Type categories (D-06 / D-05).
# These three are NOT peer-ranked, so they keep the legacy Python semantics on
# purpose and must NOT be "fixed" toward the Stage A/B CTE definitions:
#   * clocks above MAX_CLOCK_PCT_OF_BASE x base are dropped (the CTE-mirroring
#     helpers above do not clamp);
#   * the type table classifies spans with the legacy NULL-eval-to-parity rule.
# ---------------------------------------------------------------------------


def _time_pressure_out(tc: TimeControlBucket, clock_rows: Sequence[Any]) -> RankedTimePressureOut:
    """Five-quintile time-pressure curve for one TC (existing clamp and covariance rules).

    A TC without any usable clock row gets no curve, rather than five empty bullets.
    """
    tc_total, user_wdl, opp_wdl, shared = iterate_clock_rows(clock_rows)
    if tc_total.get(tc, 0) == 0:
        return RankedTimePressureOut()
    return RankedTimePressureOut(quintiles=build_quintile_bullets(tc, user_wdl, opp_wdl, shared))


def _clock_diff_points(
    full_clock_rows: Sequence[Any], since: datetime.datetime | None
) -> list[ClockDiffTimelinePoint]:
    """Clock Gap timeline for one TC from its FULL ranked clock rows (same pre-fill rule)."""
    return compute_clock_diff_timeline(full_clock_rows, cutoff=since).points


def _band_mid(band: tuple[float, float]) -> float:
    return (band[0] + band[1]) / 2


def _rate_significant(successes: int, games: int, band: tuple[float, float]) -> bool:
    """D-14 gate for a per-class rate: the 99% Wilson CI excludes the band centre.

    The per-class bands are cohort p25/p75 per (class, TC); their centre stands in for
    the cohort median, which the per-class registry does not store.
    """
    if games <= 0:
        return False
    lo, hi = wilson_bounds(successes / games, games, z=VERDICT_CI_Z_99)
    return ci_excludes(_band_mid(band), lo, hi)


def _type_gap_significant(category: EndgameCategoryStats) -> bool:
    """D-14 gate for the per-class Score Gap: its 99% CI excludes 0.

    The shared category builder (endgame_service._build_category_stats) already emits
    the 99% CI, so the gate reads it directly; a missing CI (n < 2) never passes.
    """
    return ci_excludes(
        0.0,
        category.type_achievable_score_gap_ci_low,
        category.type_achievable_score_gap_ci_high,
    )


def _with_significance(
    category: EndgameCategoryStats, tc: TimeControlBucket
) -> EndgameCategoryStats:
    """Attach the D-14 verdict gates of one TypeTable row (zoneless classes get none)."""
    zones = PER_CLASS_TC_GAUGE_ZONES.get(category.endgame_class)
    if zones is None:
        return category
    bands = zones[tc]
    conv = category.conversion
    return category.model_copy(
        update={
            "conversion_significant": _rate_significant(
                conv.conversion_wins, conv.conversion_games, bands.conversion
            ),
            "recovery_significant": _rate_significant(
                conv.recovery_saves, conv.recovery_games, bands.recovery
            ),
            "type_achievable_score_gap_significant": _type_gap_significant(category),
        }
    )


def _type_categories(
    tc: TimeControlBucket, entry_rows: Sequence[Any]
) -> list[EndgameCategoryStats]:
    """Rook / minor piece / pawn / queen rows for one TC (mixed and pawnless excluded)."""
    return [
        _with_significance(category, tc)
        for category in aggregate_endgame_stats_by_tc(entry_rows).get(tc, [])
    ]


@dataclass(frozen=True)
class _TcCanonical:
    """Canonical-mode result for one TC: metric cores, bucket WDL and entry flow."""

    cores: dict[CdfMetricId, _MetricCore]
    buckets: list[RankedBucketOut]
    entry_flow: RankedEntryFlowOut


def _tc_canonical(
    tc: TimeControlBucket,
    games: Sequence[RankedGameRow],
    inputs: RankedInputs,
    endgame_rows: Sequence[Any],
    non_endgame_rows: Sequence[Any],
) -> _TcCanonical:
    elo_by_game = {g.game_id: g.user_elo for g in games}
    bucket_rows = _rows_for_tc(inputs.bucket_rows, tc)
    clock_rows = _rows_for_tc(inputs.clock_rows, tc)
    achievable, entry_flow = _achievable_metric(bucket_rows)
    rate_cores, buckets = _rate_metrics(bucket_rows, elo_by_game)
    gap_cores = _bucket_gap_metrics(_rows_for_tc(inputs.entry_rows, tc), elo_by_game)
    entries = _clock_entries(clock_rows)
    cores: dict[CdfMetricId, _MetricCore] = {
        "score_gap": _score_gap_core(endgame_rows, non_endgame_rows),
        "achievable_score_gap": achievable,
        "score_gap_conv": gap_cores["score_gap_conv"],
        "score_gap_parity": gap_cores["score_gap_parity"],
        "recovery_score_gap": gap_cores["recovery_score_gap"],
        "time_pressure_score_gap": _time_pressure_score_gap_metric(entries),
        "clock_gap": _clock_gap_metric(entries),
        "net_flag_rate": _net_flag_metric(clock_rows),
        "conversion_rate": rate_cores["conversion_rate"],
        "parity_rate": rate_cores["parity_rate"],
        "recovery_rate": rate_cores["recovery_rate"],
    }
    return _TcCanonical(cores=cores, buckets=buckets, entry_flow=entry_flow)


def _rank_status(
    *,
    has_anchor: bool,
    anchor_games: int,
    eval_dependent: bool,
    value: float | None,
    eval_pending: int,
    floor_n: int,
    floor_required: int,
    row: PercentileRow | None,
) -> tuple[RankStatus, int, int]:
    """Rank status of one (metric, TC) plus the (floor_n, floor_required) to display.

    Applied in this order (D-09 / D-11):
      1. no anchor and fewer than 30 anchor-eligible games -> below_floor, counting the
         ANCHOR games ("18 of 30"), for every metric of the TC
      2. eval-dependent metric without a value while evals are pending -> pending
      3. the metric's own binding count under its floor -> below_floor
      4. a persisted row with a percentile -> ranked
      5. otherwise -> unranked (Stage B row not written yet, or no CDF cell)
    No drift handling between a fresh value and the stored percentile (D-08).
    """
    if not has_anchor and anchor_games < MEDIAN_ANCHOR_MIN_GAMES:
        return "below_floor", anchor_games, MEDIAN_ANCHOR_MIN_GAMES
    if eval_dependent and value is None and eval_pending > 0:
        return "pending", floor_n, floor_required
    if floor_n < floor_required:
        return "below_floor", floor_n, floor_required
    if row is not None and row.percentile is not None:
        return "ranked", floor_n, floor_required
    return "unranked", floor_n, floor_required


@dataclass(frozen=True)
class _StatusContext:
    """TC-level facts every metric's rank status depends on."""

    has_anchor: bool
    anchor_games: int
    eval_pending: int


def _metric_significant(
    metric: CdfMetricId,
    core: _MetricCore,
    percentile: float | None,
    cohort_median: float | None,
) -> bool:
    """Phase 239 D-14 verdict gate for one ranked metric.

    The 99% CI must exclude the null (0 for a difference metric, the cohort p50 for a raw
    rate) on the same side as the percentile verdict, so a green "above typical" never
    rests on a value significantly below the null.
    """
    if percentile is None or core.value is None:
        return False
    null = cohort_median if metric in RATE_METRICS else 0.0
    if null is None or not ci_excludes(null, core.ci_low, core.ci_high):
        return False
    return (core.value > null) == (percentile > _MEDIAN_PERCENTILE)


def _metric_out(
    metric: CdfMetricId,
    core: _MetricCore,
    row: PercentileRow | None,
    ctx: _StatusContext,
    cohort_median: float | None,
) -> RankedMetricOut:
    status, floor_n, floor_required = _rank_status(
        has_anchor=ctx.has_anchor,
        anchor_games=ctx.anchor_games,
        eval_dependent=metric in EVAL_DEPENDENT_METRICS,
        value=core.value,
        eval_pending=ctx.eval_pending,
        floor_n=core.floor_n,
        floor_required=core.floor_required,
        row=row,
    )
    # The percentile is only meaningful (and only shown) for a ranked cell.
    percentile = row.percentile if status == "ranked" and row is not None else None
    return RankedMetricOut(
        metric=metric,
        value=core.value,
        n=core.n,
        floor_n=floor_n,
        floor_required=floor_required,
        percentile=percentile,
        status=status,
        ci_low=core.ci_low,
        ci_high=core.ci_high,
        p_value=core.p_value,
        significant=_metric_significant(metric, core, percentile, cohort_median),
    )


def _build_tc_stats(
    tc: TimeControlBucket,
    games: Sequence[RankedGameRow],
    inputs: RankedInputs,
    full: RankedInputs,
    since: datetime.datetime | None,
) -> RankedTcStats:
    """Assemble one TC's payload.

    ``inputs`` is the (possibly ``since``-restricted) sample driving every scalar metric;
    ``full`` is the unrestricted sample the timelines pre-fill from (``full is inputs``
    when ``since`` is None).
    """
    endgame_rows = _rows_for_tc(inputs.endgame_rows, tc)
    non_endgame_rows = _rows_for_tc(inputs.non_endgame_rows, tc)
    full_endgame = _rows_for_tc(full.endgame_rows, tc)
    full_non_endgame = _rows_for_tc(full.non_endgame_rows, tc)
    canonical = _tc_canonical(tc, games, inputs, endgame_rows, non_endgame_rows)
    anchor_games = sum(1 for g in games if _is_anchor_game(g))
    eval_pending_games = sum(1 for g in games if g.eval_pending)
    ctx = _StatusContext(
        has_anchor=tc in inputs.anchors,
        anchor_games=anchor_games,
        eval_pending=eval_pending_games,
    )
    metrics = {
        metric: _metric_out(
            metric,
            core,
            inputs.percentile_rows.get(metric, {}).get(tc),
            ctx,
            inputs.cohort_medians.get((metric, tc)),
        )
        for metric, core in canonical.cores.items()
    }
    return RankedTcStats(
        tc=tc,
        ranked_games=len(games),
        anchor_games=anchor_games,
        anchor_min_games=MEDIAN_ANCHOR_MIN_GAMES,
        anchor=_anchor_out(inputs.anchors.get(tc)),
        eval_pending_games=eval_pending_games,
        metrics=metrics,
        overall=RankedOverallOut(
            endgame_wdl=build_wdl_summary(endgame_rows),
            non_endgame_wdl=build_wdl_summary(non_endgame_rows),
            entry_flow=canonical.entry_flow,
        ),
        buckets=canonical.buckets,
        time_pressure=_time_pressure_out(tc, _rows_for_tc(inputs.clock_rows, tc)),
        score_gap_timeline=_score_gap_timeline_points(full_endgame, full_non_endgame, since),
        score_gap_timeline_window=SCORE_GAP_TIMELINE_WINDOW,
        clock_diff_timeline=_clock_diff_points(_rows_for_tc(full.clock_rows, tc), since),
        elo_timeline=_elo_timeline_combos(
            tc, full.games_by_tc.get(tc, []), full_endgame, full_non_endgame, since
        ),
        elo_timeline_window=ENDGAME_ELO_TIMELINE_WINDOW,
        type_categories=_type_categories(tc, _rows_for_tc(inputs.entry_rows, tc)),
    )


def build_ranked_stats(
    inputs: RankedInputs,
    *,
    since: datetime.datetime | None = None,
) -> EndgameRankedStatsResponse:
    """Assemble the response from fetched inputs (pure, no DB).

    Only time controls with at least one ranked game are listed, in
    bullet, blitz, rapid, classical order (D-14); an empty ranked sample yields
    ``tcs == []`` (D-10). ``since`` restricts the scalar metrics to games played at or
    after it and drops persisted percentiles (insights ``last_3mo`` window); the
    timelines still pre-fill their rolling windows from the full ranked rows and only
    trim emitted points before ``since``.
    """
    full = inputs
    if since is not None:
        inputs = _restrict_to_since(inputs, since)
    tcs = [
        _build_tc_stats(tc, inputs.games_by_tc[tc], inputs, full, since)
        for tc in RANKED_TC_ORDER
        if inputs.games_by_tc.get(tc)
    ]
    return EndgameRankedStatsResponse(tcs=tcs)


async def get_ranked_stats(session: AsyncSession, *, user_id: int) -> EndgameRankedStatsResponse:
    """Ranked-sample Endgame Stats for the authenticated user (no filters, D-01)."""
    return build_ranked_stats(await fetch_ranked_inputs(session, user_id=user_id))
