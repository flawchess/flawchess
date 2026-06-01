"""Endgame findings service: transforms `EndgameOverviewResponse` composites into
deterministic findings for the LLM prompt assembly in Phase 65.

Scope (Phase 63):

- `compute_findings(filter_context, session, user_id)` is the sole public entry
  point. It issues TWO sequential calls to
  `endgame_service.get_endgame_overview` (one per time window) on the same
  `AsyncSession` and composes the per-subsection `SubsectionFinding` list.
- All data access goes through `endgame_service.get_endgame_overview` (FIND-01):
  this module MUST NOT import from `app.repositories`.
- Zones and trend gates are sourced from named constants in
  `app.services.endgame_zones` (FIND-02): no inline magic numbers.
- Trend gate combines BOTH the weekly-points-in-window count and the
  slope-to-volatility ratio; either failure collapses the trend to `"n_a"`
  (FIND-04).
- `findings_hash` is a 64-char lowercase hex SHA256 of the canonical JSON of
  `EndgameTabFindings` with `as_of` and `findings_hash` excluded, produced via
  the NaN-safe `model_dump_json` -> `json.loads` -> `json.dumps(sort_keys=True,
  separators=(",", ":"))` recipe (FIND-05; RESEARCH.md §Pitfall 1).

Critical invariants:

- Two sequential awaits of `get_endgame_overview`, never concurrent gather
  — a single `AsyncSession` is not safe for concurrent coroutines (CLAUDE.md
  §Critical Constraints).
- Phase 87.4 (D-05): the aggregate `endgame_skill` concept was retired
  end-to-end (no composite definition survived scrutiny). The prior
  `_endgame_skill_from_material_rows` recompute path and its sole
  endgame_metrics emitter were deleted in the same change.
- `FilterContext.color` is not forwarded to `get_endgame_overview` (the
  endgame service has no color filter).
- Non-trivial except blocks call `sentry_sdk.set_context` with structured
  data, not variable-in-message strings (CLAUDE.md §Sentry).
"""

import datetime
import hashlib
import json
import math
import statistics
from collections import defaultdict
from typing import Literal

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import (
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameEloTimelinePoint,
    EndgameOverviewResponse,
    MaterialBucket,
    MaterialRow,
    PerTcBreakdownOut,
    ScoreGapTimelinePoint,
    TimePressureTcCard,
)
from app.schemas.insights import (
    EndgameTabFindings,
    FilterContext,
    MetricPercentileRecord,
    PlayerProfileEntry,
    RatingAnchorContext,
    SubsectionFinding,
    TimePoint,
)
from app.core.opponent_strength import preset_to_range
from app.services.endgame_service import get_endgame_overview
from app.services.endgame_zones import (
    TREND_MIN_SLOPE_VOL_RATIO,
    TREND_MIN_WEEKLY_POINTS,
    BucketedMetricId,
    MetricId,
    SubsectionId,
    Trend,
    Window,
    assign_bucketed_zone,
    assign_per_class_zone,
    assign_zone,
    sample_quality,
)

# ---------------------------------------------------------------------------
# Opponent type is hardcoded for the findings pipeline — FilterContext does
# not surface a bot toggle in v1.11 per INS-03.
# ---------------------------------------------------------------------------

_OPPONENT_TYPE: str = "human"

# ---------------------------------------------------------------------------
# Phase 65 series resampling constants.
# ---------------------------------------------------------------------------

# D-04: min weekly observations per (platform, time_control) combo for the
# endgame_elo_timeline series. Combos below this floor are silently skipped —
# no SubsectionFinding is emitted for them.
SPARSE_COMBO_FLOOR: int = 10

# The 3 timeline SubsectionIds that receive a populated `series` field (D-02).
# type_win_rate_timeline was removed in 260501-s0u: the per-type WDL timeline
# chart was deleted from the UI in favour of static Conversion/Recovery gauge cards.
_TIMELINE_SUBSECTION_IDS: frozenset[str] = frozenset(
    {
        "score_timeline",
        "clock_diff_timeline",
        "endgame_elo_timeline",  # Phase 87.5 D-06: restored from the Phase 87.4 subsection name.
    }
)

# Maps each MaterialBucket to the ONE bucketed metric whose glossary definition
# applies to that bucket. Used by _findings_endgame_metrics so each MaterialRow
# emits exactly one finding (not three). Fixes the A1 semantic-conflict bug:
# the prior 3×3 fan-out emitted e.g. `parity_score_pct | [bucket=conversion]`
# which contradicts the glossary.
_BUCKET_TO_METRIC: dict[MaterialBucket, BucketedMetricId] = {
    "conversion": "conversion_win_pct",
    "parity": "parity_score_pct",
    "recovery": "recovery_save_pct",
}


# ---------------------------------------------------------------------------
# Percentile helpers.
# ---------------------------------------------------------------------------


def _dominant_per_tc_row(
    rows: list[PerTcBreakdownOut],
) -> PerTcBreakdownOut | None:
    """Return the per-TC breakdown row with the highest n_games (dominant TC).

    Used to pick a representative anchor/value/n_games for page-level weighted
    percentile records (score_gap, achievable_score_gap) where the chip shows a
    single weighted number but we want to attribute it to the most-played TC.
    Returns None when the list is empty.
    """
    if not rows:
        return None
    return max(rows, key=lambda r: r.n_games)


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


async def compute_findings(
    filter_context: FilterContext,
    session: AsyncSession,
    user_id: int,
) -> EndgameTabFindings:
    """Compute deterministic findings for the Endgame tab (Phase 63 FIND-01..05).

    Makes two sequential calls to `endgame_service.get_endgame_overview`
    (all_time window with `from_date=None, to_date=None`, then last_3mo
    window with `from_date=date.today() - 90d, to_date=None`) on the same
    `AsyncSession` — never concurrent gather, per CLAUDE.md §Critical
    Constraints. The two-window shape is independent of the user's
    dashboard date filter (`filter_context.from_date` / `.to_date`): the
    user's range is forwarded only to the repositories, not the LLM-window
    split (RESEARCH.md §Pitfall 4).

    Returns an `EndgameTabFindings` whose `findings_hash` excludes `as_of` so
    the cache does not churn daily (FIND-05). `color` from `filter_context`
    is carried in the output but NOT forwarded to `get_endgame_overview` —
    that service has no color filter (per INS-03).
    """
    gap_min, gap_max = preset_to_range(filter_context.opponent_strength)
    try:
        all_time_resp = await get_endgame_overview(
            session=session,
            user_id=user_id,
            time_control=filter_context.time_controls or None,
            platform=filter_context.platforms or None,
            rated=True if filter_context.rated_only else None,
            opponent_type=_OPPONENT_TYPE,
            from_date=None,
            to_date=None,
            opponent_gap_min=gap_min,
            opponent_gap_max=gap_max,
        )
        last_3mo_resp = await get_endgame_overview(
            session=session,
            user_id=user_id,
            time_control=filter_context.time_controls or None,
            platform=filter_context.platforms or None,
            rated=True if filter_context.rated_only else None,
            opponent_type=_OPPONENT_TYPE,
            from_date=datetime.date.today() - datetime.timedelta(days=90),
            to_date=None,
            opponent_gap_min=gap_min,
            opponent_gap_max=gap_max,
        )
    except Exception as exc:
        # CLAUDE.md §Sentry: pass variable data via set_context; never embed
        # user_id or filter_context values in the error message (grouping).
        sentry_sdk.set_context(
            "insights", {"user_id": user_id, "filter_context": filter_context.model_dump()}
        )
        sentry_sdk.capture_exception(exc)
        raise

    all_time_findings = _compute_subsection_findings(all_time_resp, window="all_time")
    last_3mo_findings = _compute_subsection_findings(last_3mo_resp, window="last_3mo")
    all_findings = all_time_findings + last_3mo_findings

    player_profile = compute_player_profile(all_time_resp.endgame_elo_timeline.combos)

    # Phase 102 (Plan 01 + Plan 04): build enriched metric-percentile lookups and
    # cohort anchors from the all_time response so the LLM assembler can render
    # pctl= annotations with anchor/n_games/value context without re-reading
    # EndgameOverviewResponse. All new fields are optional — existing test fixtures
    # that construct EndgameTabFindings without them still work.
    # Phase 102 (Plan 05): changed from dict[str, int] to dict[str, RatingAnchorContext]
    # to carry full platform-composition disclosure (n_chesscom_games, n_lichess_games,
    # chesscom_median_native, lichess_median_native) alongside anchor_rating so the
    # [rating basis] block in insights_llm can teach the LLM about the Lichess-equivalent
    # framing for chess.com-heavy users.
    cohort_anchors: dict[str, RatingAnchorContext] = {
        tc: RatingAnchorContext(
            anchor_rating=anchor.anchor_rating,
            n_chesscom_games=anchor.n_chesscom_games,
            n_lichess_games=anchor.n_lichess_games,
            chesscom_median_native=anchor.chesscom_median_native,
            lichess_median_native=anchor.lichess_median_native,
        )
        for tc, anchor in all_time_resp.rating_anchors.items()
    }

    # --- Page-level (weighted) metric percentiles ---
    # score_gap and achievable_score_gap carry a game-count-weighted mean
    # across TCs (D-06). Per-TC breakdown rows carry anchor + n_games + value.
    metric_percentiles: dict[str, MetricPercentileRecord] = {}
    sgm = all_time_resp.score_gap_material
    if sgm.score_gap_percentile is not None:
        # Use the dominant-by-n_games TC breakdown row for anchor/value/n_games.
        dominant_sg = _dominant_per_tc_row(sgm.score_gap_per_tc)
        # Phase 102 (Plan 05): cohort_anchors[tc] is now a RatingAnchorContext; read .anchor_rating.
        _sg_ctx = cohort_anchors.get(dominant_sg.tc) if dominant_sg else None
        metric_percentiles["score_gap"] = MetricPercentileRecord(
            percentile=sgm.score_gap_percentile,
            value=dominant_sg.value * 100.0
            if dominant_sg and dominant_sg.value is not None
            else None,
            n_games=dominant_sg.n_games if dominant_sg else None,
            anchor=_sg_ctx.anchor_rating if _sg_ctx is not None else None,
            tc=None,  # page-level weighted metric
        )
    perf = all_time_resp.performance
    if perf is not None and perf.achievable_score_gap_percentile is not None:
        dominant_asg = _dominant_per_tc_row(perf.achievable_score_gap_per_tc)
        # Phase 102 (Plan 05): cohort_anchors[tc] is now a RatingAnchorContext; read .anchor_rating.
        _asg_ctx = cohort_anchors.get(dominant_asg.tc) if dominant_asg else None
        metric_percentiles["achievable_score_gap"] = MetricPercentileRecord(
            percentile=perf.achievable_score_gap_percentile,
            value=dominant_asg.value * 100.0
            if dominant_asg and dominant_asg.value is not None
            else None,
            n_games=dominant_asg.n_games if dominant_asg else None,
            anchor=_asg_ctx.anchor_rating if _asg_ctx is not None else None,
            tc=None,  # page-level weighted metric
        )

    # --- Per-TC metric percentiles for the Section 2 ΔES Score Gap family ---
    # Keyed as "{metric_id}:{tc}". Bridges the naming gap: DB metric is
    # "recovery_score_gap"; SubsectionFinding metric id is "score_gap_recov".
    # Both bridge keys are written so renderers can look up either name.
    per_tc_metric_percentiles: dict[str, MetricPercentileRecord] = {}
    for card in all_time_resp.endgame_metrics_cards.cards:
        tc = card.tc
        # Phase 102 (Plan 05): cohort_anchors[tc] is now a RatingAnchorContext; read .anchor_rating.
        _card_ctx = cohort_anchors.get(tc)
        anchor = _card_ctx.anchor_rating if _card_ctx is not None else None
        # Tuples: (bucket attr name, ΔES-gap finding metric id, rate finding metric id,
        #          DB metric id for the bridge alias — only differs for recovery)
        _BUCKET_ROWS: tuple[tuple[str, str, str, str], ...] = (
            ("conversion", "score_gap_conv", "conversion_win_pct", "score_gap_conv"),
            ("parity", "score_gap_parity", "parity_score_pct", "score_gap_parity"),
            # Bridge: DB stores "recovery_score_gap"; finding uses "score_gap_recov".
            ("recovery", "score_gap_recov", "recovery_save_pct", "recovery_score_gap"),
        )
        for bucket_attr, gap_finding_metric, rate_finding_metric, db_gap_metric in _BUCKET_ROWS:
            bucket_stats = getattr(card, bucket_attr)
            # ΔES-gap percentile
            pctl = bucket_stats.percentile
            if pctl is not None:
                rec = MetricPercentileRecord(
                    percentile=pctl,
                    value=bucket_stats.percentile_value * 100.0
                    if bucket_stats.percentile_value is not None
                    else None,
                    n_games=bucket_stats.percentile_n_games,
                    anchor=anchor,
                    tc=tc,
                )
                per_tc_metric_percentiles[f"{gap_finding_metric}:{tc}"] = rec
                # Write the bridge key for the recovery naming gap so renderers
                # looking up either "score_gap_recov:blitz" or
                # "recovery_score_gap:blitz" both find the record.
                if gap_finding_metric != db_gap_metric:
                    per_tc_metric_percentiles[f"{db_gap_metric}:{tc}"] = rec
            # Raw-rate percentile
            rate_pctl = bucket_stats.rate_percentile
            if rate_pctl is not None:
                per_tc_metric_percentiles[f"{rate_finding_metric}:{tc}"] = MetricPercentileRecord(
                    percentile=rate_pctl,
                    value=bucket_stats.rate_percentile_value * 100.0
                    if bucket_stats.rate_percentile_value is not None
                    else None,
                    n_games=bucket_stats.rate_percentile_n_games,
                    anchor=anchor,
                    tc=tc,
                )

    # --- Per-TC time-pressure metric percentiles ---
    # time_pressure_score_gap, clock_gap, net_flag_rate per TC card.
    for tp_card in all_time_resp.time_pressure_cards.cards:
        tc = tp_card.tc
        # Phase 102 (Plan 05): cohort_anchors[tc] is now a RatingAnchorContext; read .anchor_rating.
        _tp_ctx = cohort_anchors.get(tc)
        anchor = _tp_ctx.anchor_rating if _tp_ctx is not None else None
        for metric_id, pctl, n_games, value in (
            (
                "time_pressure_score_gap",
                tp_card.time_pressure_score_gap_percentile,
                tp_card.time_pressure_score_gap_n_games,
                tp_card.time_pressure_score_gap_value,
            ),
            (
                "clock_gap",
                tp_card.clock_gap_percentile,
                tp_card.clock_gap_n_games,
                tp_card.clock_gap_value,
            ),
            (
                "net_flag_rate",
                tp_card.net_flag_rate_percentile,
                tp_card.net_flag_rate_n_games,
                tp_card.net_flag_rate_value,
            ),
        ):
            if pctl is not None:
                per_tc_metric_percentiles[f"{metric_id}:{tc}"] = MetricPercentileRecord(
                    percentile=pctl,
                    value=value * 100.0 if value is not None else None,
                    n_games=n_games,
                    anchor=anchor,
                    tc=tc,
                )

    findings = EndgameTabFindings(
        as_of=datetime.datetime.now(datetime.UTC),
        filters=filter_context,
        findings=all_findings,
        # Phase 88: time_pressure_chart removed from EndgameOverviewResponse; LLM
        # prompt assembly now uses time_pressure_cards instead (Plan 88-07).
        time_pressure_chart=None,
        # Pass the all_time WDL detail (endgame vs non-endgame, plus per-type
        # categories) through so the LLM prompt can render the `overall_wdl`
        # and `results_by_endgame_type_wdl` chart blocks. The corresponding
        # SubsectionFinding rows (`overall` -> score_gap, `results_by_endgame_type`
        # -> win_rate) stay in `all_findings`; the chart blocks add the W/D/L
        # and Score % detail the single-value findings cannot carry.
        overall_performance=all_time_resp.performance,
        type_categories=all_time_resp.stats.categories,
        player_profile=player_profile,
        # Phase 102 (Plan 01 + Plan 04): new optional fields; defaults (None) apply
        # for existing test fixtures that construct EndgameTabFindings without them.
        time_pressure_cards=all_time_resp.time_pressure_cards,
        metric_percentiles=metric_percentiles if metric_percentiles else None,
        per_tc_metric_percentiles=per_tc_metric_percentiles if per_tc_metric_percentiles else None,
        cohort_anchors=cohort_anchors if cohort_anchors else None,
        findings_hash="",  # placeholder; replaced below
    )
    findings_hash = _compute_hash(findings)
    return findings.model_copy(update={"findings_hash": findings_hash})


# ---------------------------------------------------------------------------
# Player profile — per-(platform, time_control) Elo context for the LLM.
# ---------------------------------------------------------------------------

# Minimum qualifying points a combo needs before it gets an entry in the
# player profile. Below this, window stats are too noisy to be useful.
_PLAYER_PROFILE_MIN_POINTS: int = 20

# Calendar window for the last_3mo line of the player-profile summary.
_PLAYER_PROFILE_LAST_3MO_DAYS: int = 90

# Trend flat threshold for player-profile per-combo Elo series. Elo values
# typically move 10-30 points between weekly buckets; a latest-vs-prior-mean
# shift below this reads as flat.
_PLAYER_PROFILE_TREND_FLAT_ELO: float = 15.0

# Stale threshold: a combo whose last weekly point is more than this many
# days before `today` is flagged STALE on its all_time summary line.
_PLAYER_PROFILE_STALE_DAYS: int = 183

# Minimum retained points before a trend direction is reported. Below this
# the window emits no trend (caller renders no `trend=` field).
_PLAYER_PROFILE_MIN_TREND_POINTS: int = 4


def _elo_trend_direction(elos: list[int]) -> Literal["improving", "regressing", "flat"] | None:
    """Return trend direction across the last 4 Elo points, or None if <4.

    Uses the same last-4-buckets convention as `_trend_tag` in insights_llm:
    compare the latest value to the mean of the prior 3. Player-profile
    specific flat threshold (_PLAYER_PROFILE_TREND_FLAT_ELO) is looser than
    the percentage-scale threshold because Elo swings 10-20 points weekly
    are normal.
    """
    if len(elos) < _PLAYER_PROFILE_MIN_TREND_POINTS:
        return None
    latest = elos[-1]
    prior_mean = statistics.mean(elos[-4:-1])
    diff = latest - prior_mean
    if abs(diff) < _PLAYER_PROFILE_TREND_FLAT_ELO:
        return "flat"
    return "improving" if diff > 0 else "regressing"


def compute_player_profile(
    combos: list[EndgameEloTimelineCombo],
) -> list[PlayerProfileEntry] | None:
    """Produce per-combo Elo context for the LLM prompt.

    Uses the already-fetched `endgame_elo_timeline.combos` — no extra DB
    work. Each combo with >= _PLAYER_PROFILE_MIN_POINTS weekly points yields
    a `quality="full"` entry with paired all_time / last_3mo window stats
    (mean, n, buckets, trend, std). Combos are sorted by total game count
    desc so the LLM sees the most-played combo first (the default anchor
    for tone).

    Sparse-fallback (Fix B): when NO combo clears the full-quality floor,
    every combo with >= 1 weekly point is emitted as a `quality="sparse"`
    entry instead. Sparse entries carry the same field shape but the
    renderer suppresses trend/std and swaps the [anchor-combo] tag for a
    `sparse-history` variant — the goal is to keep the LLM anchored to
    real Elo numbers rather than letting it hallucinate the whole
    `player_profile` output field. See
    `.planning/debug/llm-prompt-missing-sections.md`.

    When a combo has no weekly points in the calendar-last-90d window, the
    last_3mo fields stay None and the prompt emits "last_3mo : no data".
    When the combo's last weekly point is >_PLAYER_PROFILE_STALE_DAYS old,
    `stale_last_bucket` / `stale_months` are populated so the summary line
    carries a STALE marker.

    Returns None only when no combo has any weekly points at all (the user
    has imported games but somehow has zero endgame_elo timeline rows).
    """
    today = datetime.date.today()
    cutoff_last_3mo = today - datetime.timedelta(days=_PLAYER_PROFILE_LAST_3MO_DAYS)

    sparse_mode = not any(len(c.points) >= _PLAYER_PROFILE_MIN_POINTS for c in combos)
    min_points = 1 if sparse_mode else _PLAYER_PROFILE_MIN_POINTS
    quality: Literal["full", "sparse"] = "sparse" if sparse_mode else "full"

    entries: list[PlayerProfileEntry] = []
    for combo in combos:
        points = combo.points
        if len(points) < min_points:
            continue
        # Sort by date ASC (the endgame service already returns ASC, but be
        # defensive — trend math depends on chronological order).
        ordered = sorted(points, key=lambda p: p.date)
        elos = [p.actual_elo for p in ordered]
        current_elo = elos[-1]
        min_elo = min(elos)
        max_elo = max(elos)
        try:
            first_date = datetime.date.fromisoformat(ordered[0].date)
            last_date = datetime.date.fromisoformat(ordered[-1].date)
            window_days = (last_date - first_date).days
        except ValueError:
            window_days = 0
            last_date = today  # Defensive: treat undated combos as current.

        # all_time window stats across every qualifying point.
        all_time_mean = int(round(statistics.mean(elos)))
        all_time_n = sum(p.per_week_endgame_games for p in ordered)
        all_time_buckets = len(ordered)
        all_time_std = int(round(statistics.stdev(elos))) if len(elos) >= 2 else 0
        all_time_trend = _elo_trend_direction(elos) or "flat"

        # last_3mo window: calendar-anchored. Empty when no weekly points
        # fall in the last 90 days (stale combos will hit this branch).
        recent_points: list[EndgameEloTimelinePoint] = []
        for p in ordered:
            try:
                d = datetime.date.fromisoformat(p.date)
            except ValueError:
                continue
            if d >= cutoff_last_3mo:
                recent_points.append(p)
        last_3mo_mean: int | None = None
        last_3mo_n: int | None = None
        last_3mo_buckets: int | None = None
        last_3mo_trend: Literal["improving", "regressing", "flat"] | None = None
        last_3mo_std: int | None = None
        if recent_points:
            recent_elos = [p.actual_elo for p in recent_points]
            last_3mo_mean = int(round(statistics.mean(recent_elos)))
            last_3mo_n = sum(p.per_week_endgame_games for p in recent_points)
            last_3mo_buckets = len(recent_points)
            last_3mo_std = int(round(statistics.stdev(recent_elos))) if len(recent_elos) >= 2 else 0
            last_3mo_trend = _elo_trend_direction(recent_elos)

        # Stale marker: combo's last weekly point sits far behind calendar-now.
        stale_last_bucket: str | None = None
        stale_months: int | None = None
        if window_days > 0:
            days_stale = (today - last_date).days
            if days_stale > _PLAYER_PROFILE_STALE_DAYS:
                stale_last_bucket = last_date.strftime("%Y-%m")
                stale_months = days_stale // 30

        games = sum(p.per_week_endgame_games for p in ordered)
        entries.append(
            PlayerProfileEntry(
                platform=combo.platform,
                time_control=combo.time_control,
                games=games,
                current_elo=current_elo,
                min_elo=min_elo,
                max_elo=max_elo,
                window_days=window_days,
                all_time_mean=all_time_mean,
                all_time_n=all_time_n,
                all_time_buckets=all_time_buckets,
                all_time_trend=all_time_trend,
                all_time_std=all_time_std,
                last_3mo_mean=last_3mo_mean,
                last_3mo_n=last_3mo_n,
                last_3mo_buckets=last_3mo_buckets,
                last_3mo_trend=last_3mo_trend,
                last_3mo_std=last_3mo_std,
                stale_last_bucket=stale_last_bucket,
                stale_months=stale_months,
                quality=quality,
            )
        )
    if not entries:
        return None
    entries.sort(key=lambda e: e.games, reverse=True)
    return entries


# ---------------------------------------------------------------------------
# Subsection extraction — transforms ONE EndgameOverviewResponse into the
# list of SubsectionFinding for ONE window.
# ---------------------------------------------------------------------------


def _compute_subsection_findings(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """Extract all per-subsection findings for one window.

    Covers the 10 SubsectionId values. Empty subsections emit the standard
    empty-window placeholder (`_empty_finding`). Trend is computed over the
    timeline subsections only; non-timeline subsections carry `trend="n_a"`
    and `weekly_points_in_window=0`.
    """
    findings: list[SubsectionFinding] = []

    findings.append(_finding_overall(response, window))
    findings.extend(_findings_endgame_start_vs_end(response, window))  # Phase 82 D-16
    findings.extend(_findings_score_timeline(response, window))
    findings.extend(_findings_endgame_metrics(response, window))
    findings.extend(_findings_endgame_elo_timeline(response, window))
    findings.extend(_findings_time_pressure_at_entry(response, window))
    # Phase 88.1: removed silent empty-finding regression (REVIEW.md WR-06).
    # The clock-diff and time-pressure-vs-performance subsection helpers used to
    # be appended here, both returning permanent empty findings since Phase 88
    # removed their backing fields from EndgameOverviewResponse.
    findings.extend(_findings_results_by_endgame_type(response, window))
    findings.extend(_findings_conversion_recovery_by_type(response, window))

    return findings


# ---------------------------------------------------------------------------
# Per-subsection builders. Kept small so each subsection's mapping from
# EndgameOverviewResponse fields to SubsectionFinding is easy to audit.
# ---------------------------------------------------------------------------


def _finding_overall(
    response: EndgameOverviewResponse,
    window: Window,
) -> SubsectionFinding:
    """overall -> score_gap from score_gap_material.score_difference.

    Empty-window gate intentionally diverges from `_findings_endgame_start_vs_end`'s
    `< 10` floor. The `score_gap` denominator is endgame + non_endgame games, so a
    `>= 1` payload is informationally meaningful even when each side alone would
    be thin. The downstream `_assemble_user_prompt` filter (sample_size == 0 AND
    quality == "thin") still drops sub-`SAMPLE_QUALITY_BANDS["overall"][0]` (50)
    payloads from the rendered prompt via the per-finding sample-quality classifier,
    so 1..9-game payloads are emitted but suppressed before the LLM sees them.
    Keep the `== 0` floor here; tighten the rendered-output filter only.
    """
    sample_size = (
        response.performance.endgame_wdl.total + response.performance.non_endgame_wdl.total
    )
    if sample_size == 0:
        return _empty_finding("overall", window, "score_gap")

    value = response.score_gap_material.score_difference
    quality = sample_quality("overall", sample_size)
    return SubsectionFinding(
        subsection_id="overall",
        parent_subsection_id=None,
        window=window,
        metric="score_gap",
        value=value,
        zone=assign_zone("score_gap", value),
        trend="n_a",  # non-timeline finding
        weekly_points_in_window=0,
        sample_size=sample_size,
        sample_quality=quality,
        is_headline_eligible=quality != "thin",
        dimension=None,
    )


def _findings_endgame_start_vs_end(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_start_vs_end -> THREE findings (entry_eval_pawns, endgame_score, entry_expected_score).

    Phase 82 (D-16): wire Phase 81 entry_eval_mean_pawns and endgame
    Score-vs-50% into the LLM payload. All findings are single-aggregate, no
    series, no dimension (D-19, D-20). Empty-window convention:
    entry_eval_n < 10 OR endgame_wdl.total < 10 OR
    entry_expected_score_n < 10 -> _empty_finding for the affected tile
    (gated independently per Phase 82 D-17 / Phase 83 D-19).
    is_headline_eligible = sample_quality != "thin" (D-18).

    Phase 83 (D-17 / D-19): adds a third finding for entry_expected_score
    (Stockfish-baseline achievable score via Lichess sigmoid). The LLM
    narrates the achievable-vs-achieved gap as the headline diagnostic with
    entry_eval_pawns as the explanatory unit (D-18). No `verdict` field —
    the LLM narrates strictly by zone (Phase 82 D-06; memory
    feedback_llm_significance_signal.md).
    """
    perf = response.performance

    # Tile 1 — entry eval (D-17: gate on entry_eval_n >= 10)
    n_eval = perf.entry_eval_n
    entry_eval = perf.entry_eval_mean_pawns
    if n_eval < 10:
        tile1 = _empty_finding("endgame_start_vs_end", window, "entry_eval_pawns")
    else:
        eval_quality = sample_quality("endgame_start_vs_end", n_eval)
        tile1 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="entry_eval_pawns",
            value=entry_eval,
            zone=assign_zone("entry_eval_pawns", entry_eval),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=n_eval,
            sample_quality=eval_quality,
            is_headline_eligible=eval_quality != "thin",
            dimension=None,
        )

    # Tile 2 — endgame score vs 50% (D-17: gate on endgame_wdl.total >= 10)
    total = perf.endgame_wdl.total
    if total < 10:
        tile2 = _empty_finding("endgame_start_vs_end", window, "endgame_score")
    else:
        score = (perf.endgame_wdl.wins + 0.5 * perf.endgame_wdl.draws) / total
        score_quality = sample_quality("endgame_start_vs_end", total)
        tile2 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="endgame_score",
            value=score,
            zone=assign_zone("endgame_score", score),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=total,
            sample_quality=score_quality,
            is_headline_eligible=score_quality != "thin",
            dimension=None,
        )

    # Tile 3 — achievable score (Phase 83 D-19: gate on entry_expected_score_n >= 10)
    n_ex = perf.entry_expected_score_n
    if n_ex < 10:
        tile3 = _empty_finding("endgame_start_vs_end", window, "entry_expected_score")
    else:
        ex = perf.entry_expected_score
        ex_quality = sample_quality("endgame_start_vs_end", n_ex)
        tile3 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="entry_expected_score",
            value=ex,
            zone=assign_zone("entry_expected_score", ex),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=n_ex,
            sample_quality=ex_quality,
            is_headline_eligible=ex_quality != "thin",
            dimension=None,
        )

    return [tile1, tile2, tile3]


def _findings_score_timeline(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """score_timeline -> THREE findings per window (endgame_score_timeline, non_endgame_score_timeline, score_gap).

    Phase 68 (260424-pc6, UAT pass): replaces the prior B4-option-c
    two-findings-with-part-dim shape. The old shape emitted two
    `[summary score_gap | part=endgame|non_endgame]` blocks where the
    series values were absolute per-part scores, not signed gaps — the
    `score_gap` label lied about its payload and misled the LLM. The new
    shape emits ONE finding per distinct metric, each with its own scalar
    value, zone, trend, and series:

    1. `metric="endgame_score_timeline"`: absolute endgame-side Score (0-1),
       series is each week's endgame_score. Headline-eligible when trend gate
       passes (this is the side that actually drives insight narration).
       Phase 82 D-01: renamed from "endgame_score" to free that slot for the
       new endgame_start_vs_end subsection.
    2. `metric="non_endgame_score_timeline"`: absolute non-endgame-side Score
       (0-1), series is each week's non_endgame_score. Never headline-eligible
       on its own — it is the partner context for the endgame side.
       Phase 82 D-02: renamed from "non_endgame_score".
    3. `metric="score_gap"`: signed aggregate gap (endgame - non_endgame),
       series is each week's per-bucket gap. Never headline-eligible —
       the `overall` subsection already emits the authoritative
       `[summary score_gap]`; this row gives the LLM the gap's own
       timeseries trajectory without forcing it to subtract two series.

    Deterministic order: endgame_score_timeline, non_endgame_score_timeline, score_gap.
    Findings carry no `dimension` — each metric id is unique, so no
    per-dim fan-out is needed to keep summary headers distinct.

    Granularity stays WEEKLY in both windows (unlike other timelines that
    resample all_time to monthly) — the ISO-week bucketing is the natural
    grain of `_compute_score_gap_timeline` and the two-line chart reads
    weekly points directly. `_series_granularity` in insights_llm.py pins
    this explicitly for subsection_id == "score_timeline".
    """
    timeline: list[ScoreGapTimelinePoint] = response.score_gap_material.timeline
    if not timeline:
        return [
            _empty_finding("score_timeline", window, "endgame_score_timeline"),
            _empty_finding("score_timeline", window, "non_endgame_score_timeline"),
            _empty_finding("score_timeline", window, "score_gap"),
        ]

    sample_size = len(timeline)
    quality = sample_quality("score_timeline", sample_size)

    # Per-part scalar means (authoritative values for each summary's
    # `mean=` field). response.score_gap_material.score_difference stays
    # the aggregate for score_gap so both the overall and score_timeline
    # summaries quote the same source of truth.
    endgame_mean = statistics.mean(p.endgame_score for p in timeline)
    non_endgame_mean = statistics.mean(p.non_endgame_score for p in timeline)
    gap_mean = response.score_gap_material.score_difference

    # Per-part weekly tuples (absolute rolling Scores) and per-point gap
    # tuples. Pass window="last_3mo" so `_weekly_points_to_time_points`
    # takes the pass-through branch and preserves weekly grain in both
    # windows — see docstring for rationale.
    endgame_weekly: list[tuple[str, float, int]] = [
        (p.date, p.endgame_score, p.endgame_game_count) for p in timeline
    ]
    non_endgame_weekly: list[tuple[str, float, int]] = [
        (p.date, p.non_endgame_score, p.non_endgame_game_count) for p in timeline
    ]
    gap_weekly: list[tuple[str, float, int]] = [
        (
            p.date,
            p.endgame_score - p.non_endgame_score,
            p.endgame_game_count + p.non_endgame_game_count,
        )
        for p in timeline
    ]

    endgame_series = _weekly_points_to_time_points(endgame_weekly, "last_3mo")
    non_endgame_series = _weekly_points_to_time_points(non_endgame_weekly, "last_3mo")
    gap_series = _weekly_points_to_time_points(gap_weekly, "last_3mo")

    # Trend per side: each finding carries its own trajectory.
    endgame_trend, endgame_weekly_points = _compute_trend([p.endgame_score for p in timeline])
    non_endgame_trend, non_endgame_weekly_points = _compute_trend(
        [p.non_endgame_score for p in timeline]
    )
    diffs = [p.score_difference for p in timeline]
    gap_trend, gap_weekly_points = _compute_trend(diffs)

    # Only the endgame_score_timeline finding is headline-eligible — the
    # narrative convention says "endgame side drives the insight".
    # non_endgame_score_timeline is the partner; score_gap's headline already
    # lives on `overall`. Phase 82 D-01/D-02: metric names renamed from
    # "endgame_score" / "non_endgame_score" to the _timeline variants.
    return [
        SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window=window,
            metric="endgame_score_timeline",
            value=endgame_mean,
            zone=assign_zone("endgame_score_timeline", endgame_mean),
            trend=endgame_trend,
            weekly_points_in_window=endgame_weekly_points,
            sample_size=sample_size,
            sample_quality=quality,
            is_headline_eligible=endgame_trend != "n_a",
            dimension=None,
            series=endgame_series,
        ),
        SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window=window,
            metric="non_endgame_score_timeline",
            value=non_endgame_mean,
            zone=assign_zone("non_endgame_score_timeline", non_endgame_mean),
            trend=non_endgame_trend,
            weekly_points_in_window=non_endgame_weekly_points,
            sample_size=sample_size,
            sample_quality=quality,
            is_headline_eligible=False,
            dimension=None,
            series=non_endgame_series,
        ),
        SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window=window,
            metric="score_gap",
            value=gap_mean,
            zone=assign_zone("score_gap", gap_mean),
            trend=gap_trend,
            weekly_points_in_window=gap_weekly_points,
            sample_size=sample_size,
            sample_quality=quality,
            is_headline_eligible=False,
            dimension=None,
            series=gap_series,
        ),
    ]


def _findings_endgame_metrics(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_metrics -> 1 finding per bucket (conversion / parity / recovery).

    Per CONTEXT.md A1: each bucketed metric is tied to exactly ONE bucket
    (conversion_win_pct -> conversion, parity_score_pct -> parity,
    recovery_save_pct -> recovery). The previous 3×3 fan-out emitted
    self-contradictory findings like `parity_score_pct | [bucket=conversion]`
    which caused the LLM to hallucinate "parity score rates are strong across
    several categories" from conversion-bucket data. Fix: dispatch on
    `row.bucket` via _BUCKET_TO_METRIC and emit only the matching metric.

    Phase 87.4 (D-05): the aggregate ``endgame_skill`` finding was dropped
    end-to-end alongside the Endgame Skill concept retirement.
    """
    rows: list[MaterialRow] = response.score_gap_material.material_rows

    findings: list[SubsectionFinding] = []

    # Phase 87.4 (D-05): the prior endgame_skill aggregate finding emitter was
    # removed along with _endgame_skill_from_material_rows. The per-bucket
    # findings below cover the same surface without the composite scalar.
    # The previous total_games / quality locals fed only that aggregate
    # finding; per-bucket findings compute their own bucket_quality.

    # One finding per MaterialRow using the bucket's matching metric (A1 fix).
    # Values follow RESEARCH.md §Subsection Mapping:
    #   conversion bucket -> conversion_win_pct = win_pct / 100
    #   parity bucket     -> parity_score_pct   = score (already 0.0-1.0)
    #   recovery bucket   -> recovery_save_pct  = (win_pct + draw_pct) / 100
    for row in rows:
        bucket: MaterialBucket = row.bucket
        # Explicit dict[str, str] annotation so ty widens the MaterialBucket
        # Literal value to str — dict value types are invariant otherwise.
        bucket_dim: dict[str, str] = {"bucket": bucket}
        bucket_games = row.games
        bucket_metric: BucketedMetricId = _BUCKET_TO_METRIC[bucket]

        if bucket_games == 0:
            findings.append(
                _empty_finding(
                    "endgame_metrics",
                    window,
                    bucket_metric,
                    dimension=bucket_dim,
                )
            )
            continue

        bucket_quality = sample_quality("endgame_metrics", bucket_games)
        bucket_headline = bucket_quality != "thin"

        # Dispatch on bucket to pick the ONE metric whose glossary entry
        # applies to that bucket — no cross-bucket fan-out.
        if bucket == "conversion":
            bucket_value = row.win_pct / 100.0
        elif bucket == "parity":
            bucket_value = row.score
        else:  # recovery
            bucket_value = (row.win_pct + row.draw_pct) / 100.0

        findings.append(
            SubsectionFinding(
                subsection_id="endgame_metrics",
                parent_subsection_id=None,
                window=window,
                metric=bucket_metric,
                value=bucket_value,
                zone=assign_bucketed_zone(bucket_metric, bucket, bucket_value),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=bucket_games,
                sample_quality=bucket_quality,
                is_headline_eligible=bucket_headline,
                dimension=bucket_dim,
            )
        )

    # Phase 87.2 (D-09 — ADDITIVE per RESEARCH §LLM Payload Critical Drift):
    # ΔES Score Gap findings alongside the existing rate findings above.
    # Wire shape per finding: (mean, n, zone, neutral_band). No p_value / verdict —
    # band IS the significance signal (memory feedback_llm_significance_signal.md).
    # Phase 87.4 (D-05): the "skill"/"score_gap_skill" tuple was
    # dropped — Endgame Skill composite retired end-to-end.
    _SCORE_GAP_BUCKETS: list[tuple[str, MetricId]] = [
        ("conv", "score_gap_conv"),
        ("parity", "score_gap_parity"),
        ("recov", "score_gap_recov"),
    ]
    for bucket_id, metric_id in _SCORE_GAP_BUCKETS:
        # Dynamic attribute access: score_gap_{bucket_id}_{mean,n} are
        # defined on ScoreGapMaterialResponse in endgames.py (Plan 02 fields).
        mean_raw: float | None = getattr(response.score_gap_material, f"score_gap_{bucket_id}_mean")
        n_raw_or_none: int | None = getattr(response.score_gap_material, f"score_gap_{bucket_id}_n")
        n_raw = n_raw_or_none if n_raw_or_none is not None else 0
        value_for_payload = mean_raw if mean_raw is not None else float("nan")
        findings.append(
            SubsectionFinding(
                subsection_id="endgame_metrics",
                parent_subsection_id=None,
                window=window,
                metric=metric_id,
                value=value_for_payload,
                zone=assign_zone(metric_id, value_for_payload),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=n_raw,
                sample_quality=sample_quality("endgame_metrics", n_raw),
                is_headline_eligible=(n_raw >= 10 and mean_raw is not None),
                dimension=None,
            )
        )

    return findings


def _findings_endgame_elo_timeline(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_elo_timeline -> one finding per (platform, time_control) combo.

    Value = most recent point's (endgame_elo - actual_elo). Combo identity
    lives in the `dimension` field (D-14). Combos with zero points are
    already dropped by the endgame service, but we defensively skip any
    empty `points` list.

    Phase 65 D-04: combos with fewer than SPARSE_COMBO_FLOOR weekly
    observations are skipped entirely — no SubsectionFinding is emitted.
    The gap-only series is populated via _series_for_endgame_elo_combo.

    Phase 87.5 (D-06): restored from the Phase 87.4 helper name. The
    subsection / metric Literal IDs are restored in lockstep with the
    Phase 87.5 backend rebuild on the additive K mapping; emission semantics
    are unchanged.
    """
    combos: list[EndgameEloTimelineCombo] = response.endgame_elo_timeline.combos
    findings: list[SubsectionFinding] = []

    if not combos:
        findings.append(_empty_finding("endgame_elo_timeline", window, "endgame_elo_gap"))
        return findings

    for combo in combos:
        # Explicit dict[str, str] annotation so ty widens the Literal combo
        # values (platform / time_control) to str — dict value types are
        # invariant otherwise.
        dim: dict[str, str] = {
            "platform": combo.platform,
            "time_control": combo.time_control,
        }
        if not combo.points:
            findings.append(
                _empty_finding(
                    "endgame_elo_timeline",
                    window,
                    "endgame_elo_gap",
                    dimension=dim,
                )
            )
            continue

        # D-04: build gap-only series; returns None if combo is too sparse
        # (< SPARSE_COMBO_FLOOR points). Skip the finding entirely in that case.
        combo_series = _series_for_endgame_elo_combo(combo, window)
        if combo_series is None:
            continue

        last = combo.points[-1]
        value = float(last.endgame_elo - last.actual_elo)
        sample_size = len(combo.points)
        quality = sample_quality("endgame_elo_timeline", sample_size)
        findings.append(
            SubsectionFinding(
                subsection_id="endgame_elo_timeline",
                parent_subsection_id=None,
                window=window,
                metric="endgame_elo_gap",
                value=value,
                zone=assign_zone("endgame_elo_gap", value),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=sample_size,
                sample_quality=quality,
                is_headline_eligible=quality != "thin",
                dimension=dim,
                series=combo_series,
            )
        )

    return findings


def _findings_time_pressure_at_entry(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """time_pressure_at_entry -> avg_clock_diff_pct + net_timeout_rate.

    Phase 88: source switched from ClockStatsRow.clock_pressure to TimePressureTcCard
    time_pressure_cards. avg_clock_diff_pct is the n-weighted mean of
    ClockGapBullet.mean_diff_pct * 100 across cards.

    Phase 102 (Plan 01): net_timeout_rate is now a real n-weighted scalar computed
    from card.net_timeout_rate (fraction → x100 to match avg_clock_diff_pct scale).
    Previously this was an always-empty stub since the Phase 88 ClockStatsRow
    migration.
    """
    cards: list[TimePressureTcCard] = response.time_pressure_cards.cards

    findings: list[SubsectionFinding] = []

    if not cards:
        findings.append(_empty_finding("time_pressure_at_entry", window, "avg_clock_diff_pct"))
        findings.append(_empty_finding("time_pressure_at_entry", window, "net_timeout_rate"))
        return findings

    # avg_clock_diff_pct: n-weighted mean of mean_diff_pct * 100 across TC cards.
    # mean_diff_pct is a fraction (0.0-1.0 scale); multiply by 100 to match the
    # avg_clock_diff_pct metric scale expected by assign_zone.
    diff_num = 0.0
    diff_den = 0
    for card in cards:
        n = card.clock_gap.n
        if n <= 0:
            continue
        diff_num += card.clock_gap.mean_diff_pct * 100.0 * n
        diff_den += n

    if diff_den > 0:
        clock_diff_value = diff_num / diff_den
    else:
        clock_diff_value = float("nan")

    clock_diff_quality = sample_quality("time_pressure_at_entry", diff_den)
    is_headline = clock_diff_quality != "thin"

    findings.append(
        SubsectionFinding(
            subsection_id="time_pressure_at_entry",
            parent_subsection_id=None,
            window=window,
            metric="avg_clock_diff_pct",
            value=clock_diff_value,
            zone=assign_zone("avg_clock_diff_pct", clock_diff_value),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=diff_den,
            sample_quality=sample_quality("time_pressure_at_entry", diff_den),
            is_headline_eligible=is_headline and not math.isnan(clock_diff_value),
            dimension=None,
        )
    )

    # Phase 102 (Plan 01): net_timeout_rate wired from card.net_timeout_rate
    # (fraction -> x100 to match avg_clock_diff_pct scale); was an always-empty
    # stub since the Phase 88 ClockStatsRow migration.
    # net_timeout_rate is in _NON_FRACTIONAL_METRICS in insights_llm.py so the
    # assembler does NOT re-scale it — the x100 happens here, exactly like
    # avg_clock_diff_pct.
    # Denominator uses card.total (total endgame games for this TC) to weight
    # the per-TC net timeout rate proportionally to each TC's game volume.
    timeout_num = 0.0
    timeout_den = 0
    for card in cards:
        n = card.total
        if n <= 0:
            continue
        timeout_num += card.net_timeout_rate * 100.0 * n
        timeout_den += n

    if timeout_den > 0:
        timeout_value = timeout_num / timeout_den
    else:
        timeout_value = float("nan")

    timeout_quality = sample_quality("time_pressure_at_entry", timeout_den)
    is_timeout_headline = timeout_quality != "thin"

    findings.append(
        SubsectionFinding(
            subsection_id="time_pressure_at_entry",
            parent_subsection_id=None,
            window=window,
            metric="net_timeout_rate",
            value=timeout_value,
            zone=assign_zone("net_timeout_rate", timeout_value),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=timeout_den,
            sample_quality=timeout_quality,
            is_headline_eligible=is_timeout_headline and not math.isnan(timeout_value),
            dimension=None,
        )
    )

    return findings


# Phase 88.1 (Plan 09, REVIEW.md WR-06): _finding_clock_diff_timeline and
# _finding_time_pressure_vs_performance were removed. Both helpers had returned
# permanent empty findings since Phase 88 retired the underlying ClockPressureResponse
# and TimePressureChartResponse fields; emitting them on every call was a silent
# LLM-prompt regression because downstream consumers could not distinguish
# "feature deprecated" from "no user data". The full WR-06 orphan cleanup
# (insights_llm.py _SKIPPED_SUBSECTIONS, _format_time_pressure_chart_block, etc.)
# lives in app/services/insights_llm.py.


def _findings_results_by_endgame_type(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """results_by_endgame_type -> per-category win_rate finding.

    Value = category win rate (0.0-1.0, W/total, draws excluded), derived from
    EndgameCategoryStats. Emitted as metric="win_rate" so the LLM prompt does
    not confuse it with endgame_skill (the Conv/Parity/Recov composite used
    only in subsection `endgame_metrics`).
    """
    categories: list[EndgameCategoryStats] = response.stats.categories
    findings: list[SubsectionFinding] = []

    if not categories:
        findings.append(_empty_finding("results_by_endgame_type", window, "win_rate"))
        return findings

    for cat in categories:
        # Explicit dict[str, str] annotation so ty widens the EndgameClass
        # Literal to str — dict value types are invariant otherwise.
        dim: dict[str, str] = {"endgame_class": cat.endgame_class}
        if cat.total == 0:
            findings.append(
                _empty_finding(
                    "results_by_endgame_type",
                    window,
                    "win_rate",
                    dimension=dim,
                )
            )
            continue
        value = cat.win_pct / 100.0
        quality = sample_quality("results_by_endgame_type", cat.total)
        findings.append(
            SubsectionFinding(
                subsection_id="results_by_endgame_type",
                parent_subsection_id=None,
                window=window,
                metric="win_rate",
                value=value,
                zone=assign_zone("win_rate", value),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=cat.total,
                sample_quality=quality,
                is_headline_eligible=quality != "thin",
                dimension=dim,
            )
        )
    return findings


def _findings_conversion_recovery_by_type(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """conversion_recovery_by_type -> per-category conversion/recovery findings.

    Emits two findings per category (conversion_win_pct + recovery_save_pct)
    using `assign_bucketed_zone` with the matching MaterialBucket. Parity
    is not emitted here — it already appears in `endgame_metrics` with
    bucket dimension (v1.11 MVP).
    """
    categories: list[EndgameCategoryStats] = response.stats.categories
    findings: list[SubsectionFinding] = []

    if not categories:
        findings.append(_empty_finding("conversion_recovery_by_type", window, "conversion_win_pct"))
        findings.append(_empty_finding("conversion_recovery_by_type", window, "recovery_save_pct"))
        return findings

    for cat in categories:
        # Conversion branch — bucket = "conversion"
        conv_games = cat.conversion.conversion_games
        # Explicit dict[str, str] annotation so ty widens the EndgameClass
        # Literal to str — dict value types are invariant otherwise.
        conv_dim: dict[str, str] = {
            "endgame_class": cat.endgame_class,
            "bucket": "conversion",
        }
        if conv_games == 0:
            findings.append(
                _empty_finding(
                    "conversion_recovery_by_type",
                    window,
                    "conversion_win_pct",
                    dimension=conv_dim,
                )
            )
        else:
            conv_value = cat.conversion.conversion_pct / 100.0
            conv_quality = sample_quality("conversion_recovery_by_type", conv_games)
            findings.append(
                SubsectionFinding(
                    subsection_id="conversion_recovery_by_type",
                    parent_subsection_id=None,
                    window=window,
                    metric="conversion_win_pct",
                    value=conv_value,
                    zone=assign_per_class_zone("conversion_win_pct", cat.endgame_class, conv_value),
                    trend="n_a",
                    weekly_points_in_window=0,
                    sample_size=conv_games,
                    sample_quality=conv_quality,
                    is_headline_eligible=conv_quality != "thin",
                    dimension=conv_dim,
                )
            )

        # Recovery branch — bucket = "recovery"
        recov_games = cat.conversion.recovery_games
        # Explicit dict[str, str] annotation — same rationale as conv_dim.
        recov_dim: dict[str, str] = {
            "endgame_class": cat.endgame_class,
            "bucket": "recovery",
        }
        if recov_games == 0:
            findings.append(
                _empty_finding(
                    "conversion_recovery_by_type",
                    window,
                    "recovery_save_pct",
                    dimension=recov_dim,
                )
            )
        else:
            recov_value = cat.conversion.recovery_pct / 100.0
            recov_quality = sample_quality("conversion_recovery_by_type", recov_games)
            findings.append(
                SubsectionFinding(
                    subsection_id="conversion_recovery_by_type",
                    parent_subsection_id=None,
                    window=window,
                    metric="recovery_save_pct",
                    value=recov_value,
                    zone=assign_per_class_zone("recovery_save_pct", cat.endgame_class, recov_value),
                    trend="n_a",
                    weekly_points_in_window=0,
                    sample_size=recov_games,
                    sample_quality=recov_quality,
                    is_headline_eligible=recov_quality != "thin",
                    dimension=recov_dim,
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _weekly_points_to_time_points(
    weekly: list[tuple[str, float, int]],
    window: Window,
) -> list[TimePoint]:
    """Convert weekly (date_iso, value, n) tuples to TimePoint list per D-03.

    last_3mo: pass-through (weekly resolution, sorted by date).
    all_time: resample to monthly, weighted-by-n mean, sample sizes summed.

    Weighted mean rationale (D-03 / RESEARCH.md §5): a 50-game week must
    dominate a 3-game week because the LLM also sees `n` on each TimePoint
    and would otherwise see inconsistent per-month numbers.

    Empty input returns []. All-zero-n month falls back to arithmetic mean
    with n=0 (emits the point rather than dropping — matches the LLM
    contract that a month with zero games is still a visible gap).
    """
    if not weekly:
        return []
    if window == "last_3mo":
        return [
            TimePoint(bucket_start=d, value=v, n=n)
            for d, v, n in sorted(weekly, key=lambda t: t[0])
        ]
    # all_time -> monthly
    buckets: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for date_iso, value, n in weekly:
        ym = date_iso[:7]  # "YYYY-MM" prefix of ISO date string
        buckets[ym].append((value, n))
    points: list[TimePoint] = []
    for ym in sorted(buckets.keys()):
        weeks = buckets[ym]
        total_n = sum(n for _, n in weeks)
        if total_n > 0:
            weighted_sum = sum(v * n for v, n in weeks)
            mean_value = weighted_sum / total_n
        else:
            mean_value = statistics.mean(v for v, _ in weeks)
        points.append(TimePoint(bucket_start=f"{ym}-01", value=mean_value, n=total_n))
    return points


def _series_for_endgame_elo_combo(
    combo: EndgameEloTimelineCombo,
    window: Window,
) -> list[TimePoint] | None:
    """Build gap+elo series for one (platform, time_control) combo per D-04.

    Returns None if combo has fewer than SPARSE_COMBO_FLOOR total weekly
    observations in the window (caller skips the subsection finding entirely).
    Each point carries both `value` (endgame_elo - actual_elo, the zoned gap)
    and `actual_elo` (the user's rating at that bucket) so the LLM prompt can
    render `gap=<v>, elo=<r>` per row and distinguish endgame regression from
    rating growth outpacing endgame.

    Phase 87.5 (D-06): per-point ``endgame_elo`` field on
    EndgameEloTimelinePoint is consumed directly (Plan 01 restored the field
    name); function name is `_series_for_endgame_elo_combo` (internal-only,
    no semantic load — kept stable across the rename).
    """
    if len(combo.points) < SPARSE_COMBO_FLOOR:
        return None
    weekly: list[tuple[str, float, int, int, int, int]] = [
        (
            p.date,
            float(p.endgame_elo - p.actual_elo),
            p.per_week_endgame_games,
            p.actual_elo,
            p.endgame_elo,
            p.non_endgame_elo,
        )
        for p in combo.points
    ]
    return _weekly_points_to_time_points_with_elo(weekly, window)


def _weekly_points_to_time_points_with_elo(
    weekly: list[tuple[str, float, int, int, int, int]],
    window: Window,
) -> list[TimePoint]:
    """Endgame-elo variant of `_weekly_points_to_time_points` that carries
    `actual_elo`, `endgame_elo`, and `non_endgame_elo` through. All three are
    weighted by game count so monthly aggregates satisfy the invariant
    `value ≈ endgame_elo - actual_elo`.

    Phase 87.5 D-06: post-rewire `per_week_endgame_games` carries the
    trailing-window count (≈ constant ≈ window size), so within a single
    TC × platform combo the weighting degenerates to ~unweighted. Acceptable
    for v1 since window size is stable across the series.

    Phase 87.6: extended tuple from 4-element to 6-element to thread
    `endgame_elo` and `non_endgame_elo` through (post-amendment 2026-05-17:
    these are derived from the logistic stretch around Actual ELO, not FIDE
    Performance Ratings).
    """
    if not weekly:
        return []
    if window == "last_3mo":
        return [
            TimePoint(
                bucket_start=d,
                value=v,
                n=n,
                actual_elo=elo,
                endgame_elo=e_elo,
                non_endgame_elo=ne_elo,
            )
            for d, v, n, elo, e_elo, ne_elo in sorted(weekly, key=lambda t: t[0])
        ]
    # all_time -> monthly
    buckets: dict[str, list[tuple[float, int, int, int, int]]] = defaultdict(list)
    for date_iso, value, n, elo, e_elo, ne_elo in weekly:
        ym = date_iso[:7]
        buckets[ym].append((value, n, elo, e_elo, ne_elo))
    points: list[TimePoint] = []
    for ym in sorted(buckets.keys()):
        weeks = buckets[ym]
        total_n = sum(n for _, n, _, _, _ in weeks)
        if total_n > 0:
            weighted_sum = sum(v * n for v, n, _, _, _ in weeks)
            mean_value = weighted_sum / total_n
            elo_weighted_sum = sum(elo * n for _, n, elo, _, _ in weeks)
            mean_elo = round(elo_weighted_sum / total_n)
            e_elo_weighted_sum = sum(e_elo * n for _, n, _, e_elo, _ in weeks)
            mean_e_elo = round(e_elo_weighted_sum / total_n)
            ne_elo_weighted_sum = sum(ne_elo * n for _, n, _, _, ne_elo in weeks)
            mean_ne_elo = round(ne_elo_weighted_sum / total_n)
        else:
            mean_value = statistics.mean(v for v, _, _, _, _ in weeks)
            mean_elo = round(statistics.mean(elo for _, _, elo, _, _ in weeks))
            mean_e_elo = round(statistics.mean(e_elo for _, _, _, e_elo, _ in weeks))
            mean_ne_elo = round(statistics.mean(ne_elo for _, _, _, _, ne_elo in weeks))
        points.append(
            TimePoint(
                bucket_start=f"{ym}-01",
                value=mean_value,
                n=total_n,
                actual_elo=mean_elo,
                endgame_elo=mean_e_elo,
                non_endgame_elo=mean_ne_elo,
            )
        )
    return points


# Phase 87.4 (D-05): _endgame_skill_from_material_rows deleted alongside the
# Endgame Skill concept retirement. Its sole caller (_findings_endgame_metrics'
# aggregate endgame_skill finding emitter) was removed in the same change.


def _compute_trend(
    points: list[float],
    min_weekly_points: int = TREND_MIN_WEEKLY_POINTS,
    min_slope_vol_ratio: float = TREND_MIN_SLOPE_VOL_RATIO,
) -> tuple[Trend, int]:
    """Trend + weekly-points-in-window from a time-ordered metric series.

    Returns `"n_a"` when:
    - `len(points) < min_weekly_points` (FIND-04 count gate), or
    - `abs(slope) / stdev < min_slope_vol_ratio` (FIND-04 ratio gate).

    All-identical series collapse to `"stable"` (stdev == 0). Otherwise
    returns `"improving"` (slope > 0) or `"declining"` (slope < 0).

    Uses stdlib `statistics.linear_regression` / `statistics.stdev` — no
    numpy dependency, fully deterministic per CLAUDE.md.
    """
    n = len(points)
    if n < min_weekly_points:
        return "n_a", n
    if n < 2:
        # Defensive guard — statistics.stdev requires n >= 2. Redundant
        # given the count gate above, but keeps the function safe if the
        # threshold is ever lowered.
        return "n_a", n

    xs = list(range(n))
    slope, _intercept = statistics.linear_regression(xs, points)
    stdev = statistics.stdev(points)
    if stdev == 0.0:
        return "stable", n
    ratio = abs(slope) / stdev
    if ratio < min_slope_vol_ratio:
        return "n_a", n
    return ("improving" if slope > 0 else "declining"), n


def _compute_hash(findings: EndgameTabFindings) -> str:
    """Deterministic SHA256 of the canonical JSON (FIND-05).

    Two-step recipe because Pydantic v2 `model_dump_json` emits fields in
    declaration order (not alphabetically), AND `model_dump(mode="json")`
    returns `float("nan")` unchanged which `json.dumps` would serialise as
    invalid `NaN`. The safe path (RESEARCH.md §Pitfall 1 + Pitfall 2):

      1. `model_dump_json(exclude=...)`  — NaN -> null
      2. `json.loads(...)`               — parse back to dict
      3. `json.dumps(..., sort_keys=True, separators=(",", ":"))`
      4. `hashlib.sha256(...).hexdigest()`

    Excludes `as_of` (so daily recomputes cache-hit) and `findings_hash`
    itself (so the field never hashes its own placeholder).
    """
    json_str = findings.model_dump_json(exclude={"findings_hash", "as_of"})
    parsed = json.loads(json_str)
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _empty_finding(
    subsection_id: SubsectionId,
    window: Window,
    metric: MetricId,
    parent: SubsectionId | None = None,
    dimension: dict[str, str] | None = None,
) -> SubsectionFinding:
    """Placeholder finding for empty / missing-data subsections.

    Per the convention documented on `SubsectionFinding` (Plan 03):
    value=NaN (Pydantic v2 serialises to JSON null), zone="typical",
    trend="n_a", sample_size=0, sample_quality="thin",
    is_headline_eligible=False. Phase 65 prompt-assembly skips findings
    where sample_quality == "thin" AND value is null.
    """
    return SubsectionFinding(
        subsection_id=subsection_id,
        parent_subsection_id=parent,
        window=window,
        metric=metric,
        value=float("nan"),
        zone="typical",
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=0,
        sample_quality="thin",
        is_headline_eligible=False,
        dimension=dimension,
    )
