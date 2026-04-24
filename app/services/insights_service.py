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
- Phase 59 removed the aggregate `endgame_skill` field from
  `EndgamePerformanceResponse`; this service recomputes it from
  `score_gap_material.material_rows` via `_endgame_skill_from_material_rows`
  (RESEARCH.md §Pitfall 7).
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
    ClockStatsRow,
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameEloTimelinePoint,
    EndgameOverviewResponse,
    MaterialBucket,
    MaterialRow,
    ScoreGapTimelinePoint,
)
from app.schemas.insights import (
    EndgameTabFindings,
    FilterContext,
    PlayerProfileEntry,
    SubsectionFinding,
    TimePoint,
)
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

# The 4 timeline SubsectionIds that receive a populated `series` field (D-02).
_TIMELINE_SUBSECTION_IDS: frozenset[str] = frozenset(
    {
        "score_gap_timeline",
        "clock_diff_timeline",
        "endgame_elo_timeline",
        "type_win_rate_timeline",
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
# Public entry point.
# ---------------------------------------------------------------------------


async def compute_findings(
    filter_context: FilterContext,
    session: AsyncSession,
    user_id: int,
) -> EndgameTabFindings:
    """Compute deterministic findings for the Endgame tab (Phase 63 FIND-01..05).

    Makes two sequential calls to `endgame_service.get_endgame_overview`
    (all_time window with `recency=None`, then last_3mo window with
    `recency="3months"`) on the same `AsyncSession` — never concurrent
    gather, per CLAUDE.md §Critical Constraints. The two-window shape is
    independent of `filter_context.recency`: the user's dashboard recency
    filter is a separate concept (RESEARCH.md §Pitfall 4).

    Returns an `EndgameTabFindings` whose `findings_hash` excludes `as_of` so
    the cache does not churn daily (FIND-05). `color` from `filter_context`
    is carried in the output but NOT forwarded to `get_endgame_overview` —
    that service has no color filter (per INS-03).
    """
    try:
        all_time_resp = await get_endgame_overview(
            session=session,
            user_id=user_id,
            time_control=filter_context.time_controls or None,
            platform=filter_context.platforms or None,
            rated=True if filter_context.rated_only else None,
            opponent_type=_OPPONENT_TYPE,
            recency=None,
            opponent_strength=filter_context.opponent_strength,
        )
        last_3mo_resp = await get_endgame_overview(
            session=session,
            user_id=user_id,
            time_control=filter_context.time_controls or None,
            platform=filter_context.platforms or None,
            rated=True if filter_context.rated_only else None,
            opponent_type=_OPPONENT_TYPE,
            recency="3months",
            opponent_strength=filter_context.opponent_strength,
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

    findings = EndgameTabFindings(
        as_of=datetime.datetime.now(datetime.UTC),
        filters=filter_context,
        findings=all_findings,
        # Pass the raw 10-bucket all_time chart through to the LLM prompt
        # assembler. The single-value _finding_time_pressure_vs_performance
        # placeholder stays in `all_findings` (still filtered out of the
        # prompt) so the findings list shape is unchanged — bucket rendering
        # is additive, not a replacement.
        time_pressure_chart=all_time_resp.time_pressure_chart,
        # Pass the all_time WDL detail (endgame vs non-endgame, plus per-type
        # categories) through so the LLM prompt can render the `overall_wdl`
        # and `results_by_endgame_type_wdl` chart blocks. The corresponding
        # SubsectionFinding rows (`overall` -> score_gap, `results_by_endgame_type`
        # -> win_rate) stay in `all_findings`; the chart blocks add the W/D/L
        # and Score % detail the single-value findings cannot carry.
        overall_performance=all_time_resp.performance,
        type_categories=all_time_resp.stats.categories,
        player_profile=player_profile,
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
    work. Each qualifying combo (>= _PLAYER_PROFILE_MIN_POINTS weekly points)
    yields one entry with current Elo, historical range, window length, and
    paired all_time / last_3mo window stats (mean, n, buckets, trend, std).
    Combos are sorted by total game count desc so the LLM sees the
    most-played combo first (the default anchor for tone).

    When a combo has no weekly points in the calendar-last-90d window, the
    last_3mo fields stay None and the prompt emits "last_3mo : no data".
    When the combo's last weekly point is >_PLAYER_PROFILE_STALE_DAYS old,
    `stale_last_bucket` / `stale_months` are populated so the summary line
    carries a STALE marker.

    Returns None when no combo qualifies — the caller renders no
    `## Player profile` block in the prompt.
    """
    today = datetime.date.today()
    cutoff_last_3mo = today - datetime.timedelta(days=_PLAYER_PROFILE_LAST_3MO_DAYS)

    entries: list[PlayerProfileEntry] = []
    for combo in combos:
        points = combo.points
        if len(points) < _PLAYER_PROFILE_MIN_POINTS:
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
    findings.append(_finding_score_gap_timeline(response, window))
    findings.extend(_findings_endgame_metrics(response, window))
    findings.extend(_findings_endgame_elo_timeline(response, window))
    findings.extend(_findings_time_pressure_at_entry(response, window))
    findings.append(_finding_clock_diff_timeline(response, window))
    findings.append(_finding_time_pressure_vs_performance(response, window))
    findings.extend(_findings_results_by_endgame_type(response, window))
    findings.extend(_findings_conversion_recovery_by_type(response, window))
    findings.extend(_findings_type_win_rate_timeline(response, window))

    return findings


# ---------------------------------------------------------------------------
# Per-subsection builders. Kept small so each subsection's mapping from
# EndgameOverviewResponse fields to SubsectionFinding is easy to audit.
# ---------------------------------------------------------------------------


def _finding_overall(
    response: EndgameOverviewResponse,
    window: Window,
) -> SubsectionFinding:
    """overall -> score_gap from score_gap_material.score_difference."""
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


def _finding_score_gap_timeline(
    response: EndgameOverviewResponse,
    window: Window,
) -> SubsectionFinding:
    """score_gap_timeline -> trend over score_gap_material.timeline series."""
    timeline: list[ScoreGapTimelinePoint] = response.score_gap_material.timeline
    if not timeline:
        return _empty_finding("score_gap_timeline", window, "score_gap")

    values = [p.score_difference for p in timeline]
    trend, weekly_points = _compute_trend(values)
    last_value = values[-1]
    sample_size = len(values)
    quality = sample_quality("score_gap_timeline", sample_size)
    # Timeline headline-eligibility hinges on the trend gate (D-13).
    is_headline = trend != "n_a"
    # D-02/D-03: populate resampled series for LLM prompt assembly.
    weekly: list[tuple[str, float, int]] = [
        (p.date, p.score_difference, p.per_week_total_games) for p in timeline
    ]
    return SubsectionFinding(
        subsection_id="score_gap_timeline",
        parent_subsection_id=None,
        window=window,
        metric="score_gap",
        value=last_value,
        zone=assign_zone("score_gap", last_value),
        trend=trend,
        weekly_points_in_window=weekly_points,
        sample_size=sample_size,
        sample_quality=quality,
        is_headline_eligible=is_headline,
        dimension=None,
        series=_weekly_points_to_time_points(weekly, window),
    )


def _findings_endgame_metrics(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_metrics -> 1 endgame_skill + 1 per-bucket matching metric.

    Per CONTEXT.md A1: each bucketed metric is tied to exactly ONE bucket
    (conversion_win_pct -> conversion, parity_score_pct -> parity,
    recovery_save_pct -> recovery). The previous 3×3 fan-out emitted
    self-contradictory findings like `parity_score_pct | [bucket=conversion]`
    which caused the LLM to hallucinate "parity score rates are strong across
    several categories" from conversion-bucket data. Fix: dispatch on
    `row.bucket` via _BUCKET_TO_METRIC and emit only the matching metric.

    endgame_skill is recomputed from material_rows (Phase 59 removed the
    aggregate field per RESEARCH.md §Pitfall 7).
    """
    rows: list[MaterialRow] = response.score_gap_material.material_rows
    total_games = sum(r.games for r in rows)
    quality = sample_quality("endgame_metrics", total_games)
    is_headline = quality != "thin"

    findings: list[SubsectionFinding] = []

    # 1. endgame_skill — recomputed from material_rows because
    # EndgamePerformanceResponse no longer exposes an aggregate endgame_skill
    # field (Phase 59 trimmed it; see RESEARCH.md §Pitfall 7). Mirrors the
    # logic of _endgame_skill_from_bucket_rows in endgame_service.py.
    skill_value = _endgame_skill_from_material_rows(rows)
    findings.append(
        SubsectionFinding(
            subsection_id="endgame_metrics",
            parent_subsection_id=None,
            window=window,
            metric="endgame_skill",
            value=skill_value,
            zone=assign_zone("endgame_skill", skill_value),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=total_games,
            sample_quality=quality,
            is_headline_eligible=is_headline and not math.isnan(skill_value),
            dimension=None,
        )
    )

    # 2. One finding per MaterialRow using the bucket's matching metric (A1 fix).
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

    Values are game-weighted means across ClockStatsRow rows (one per time
    control). Both metrics are zoned as higher_is_better, so zones are read
    directly from the raw formula output — no sign flip.
    """
    rows: list[ClockStatsRow] = response.clock_pressure.rows
    total_clock_games = response.clock_pressure.total_clock_games

    clock_diff_quality = sample_quality("time_pressure_at_entry", total_clock_games)
    is_headline = clock_diff_quality != "thin"

    findings: list[SubsectionFinding] = []

    if not rows or total_clock_games == 0:
        findings.append(_empty_finding("time_pressure_at_entry", window, "avg_clock_diff_pct"))
        findings.append(_empty_finding("time_pressure_at_entry", window, "net_timeout_rate"))
        return findings

    # avg_clock_diff_pct: mean of (user_avg_pct - opp_avg_pct) across rows,
    # weighted by clock_games. Rows without clock data (user_avg_pct is
    # None) are excluded from the weighted mean.
    diff_num = 0.0
    diff_den = 0
    for r in rows:
        if r.user_avg_pct is None or r.opp_avg_pct is None or r.clock_games <= 0:
            continue
        diff_num += (r.user_avg_pct - r.opp_avg_pct) * r.clock_games
        diff_den += r.clock_games
    if diff_den > 0:
        clock_diff_value = diff_num / diff_den
    else:
        clock_diff_value = float("nan")

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

    # net_timeout_rate: mean weighted by total_endgame_games (net_timeout_rate
    # is defined per that denominator in ClockStatsRow).
    nt_num = 0.0
    nt_den = 0
    for r in rows:
        if r.total_endgame_games <= 0:
            continue
        nt_num += r.net_timeout_rate * r.total_endgame_games
        nt_den += r.total_endgame_games
    if nt_den > 0:
        net_timeout_value = nt_num / nt_den
    else:
        net_timeout_value = float("nan")

    findings.append(
        SubsectionFinding(
            subsection_id="time_pressure_at_entry",
            parent_subsection_id=None,
            window=window,
            metric="net_timeout_rate",
            value=net_timeout_value,
            zone=assign_zone("net_timeout_rate", net_timeout_value),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=nt_den,
            sample_quality=sample_quality("time_pressure_at_entry", nt_den),
            is_headline_eligible=is_headline and not math.isnan(net_timeout_value),
            dimension=None,
        )
    )

    return findings


def _finding_clock_diff_timeline(
    response: EndgameOverviewResponse,
    window: Window,
) -> SubsectionFinding:
    """clock_diff_timeline -> trend over clock_pressure.timeline series."""
    timeline = response.clock_pressure.timeline
    if not timeline:
        return _empty_finding("clock_diff_timeline", window, "avg_clock_diff_pct")

    values = [p.avg_clock_diff_pct for p in timeline]
    trend, weekly_points = _compute_trend(values)
    last_value = values[-1]
    sample_size = len(values)
    quality = sample_quality("clock_diff_timeline", sample_size)
    is_headline = trend != "n_a"
    # D-02/D-03: populate resampled series for LLM prompt assembly.
    weekly: list[tuple[str, float, int]] = [
        (p.date, p.avg_clock_diff_pct, p.per_week_game_count) for p in timeline
    ]
    return SubsectionFinding(
        subsection_id="clock_diff_timeline",
        parent_subsection_id=None,
        window=window,
        metric="avg_clock_diff_pct",
        value=last_value,
        zone=assign_zone("avg_clock_diff_pct", last_value),
        trend=trend,
        weekly_points_in_window=weekly_points,
        sample_size=sample_size,
        sample_quality=quality,
        is_headline_eligible=is_headline,
        dimension=None,
        series=_weekly_points_to_time_points(weekly, window),
    )


def _finding_time_pressure_vs_performance(
    response: EndgameOverviewResponse,
    window: Window,
) -> SubsectionFinding:
    """time_pressure_vs_performance -> weighted mean score across user_series.

    MVP simplification (planner discretion per RESEARCH.md): emit one
    finding using `avg_clock_diff_pct` as the metric with the weighted-mean
    user score reinterpreted. The value is NOT a clock-diff percentage in
    the registry sense — it is the user's weighted mean score (0.0-1.0)
    across time-pressure buckets. We set `is_headline_eligible=False` until
    a dedicated metric lands in a follow-up phase; the finding still tracks
    sample size so Phase 65 prompt-assembly can skip it when thin.
    """
    chart = response.time_pressure_chart
    total = chart.total_endgame_games
    quality = sample_quality("time_pressure_vs_performance", total)

    score_num = 0.0
    score_den = 0
    for p in chart.user_series:
        if p.score is None or p.game_count <= 0:
            continue
        score_num += p.score * p.game_count
        score_den += p.game_count
    if score_den > 0:
        value = score_num / score_den
    else:
        value = float("nan")

    if total == 0 or math.isnan(value):
        return _empty_finding("time_pressure_vs_performance", window, "avg_clock_diff_pct")

    return SubsectionFinding(
        subsection_id="time_pressure_vs_performance",
        parent_subsection_id=None,
        window=window,
        metric="avg_clock_diff_pct",
        value=value,
        zone=assign_zone("avg_clock_diff_pct", value),
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=total,
        sample_quality=quality,
        # Conservative headline policy until a dedicated slope metric lands
        # (planner note in RESEARCH.md §Subsection Mapping).
        is_headline_eligible=False,
        dimension=None,
    )


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
                    zone=assign_bucketed_zone("conversion_win_pct", "conversion", conv_value),
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
                    zone=assign_bucketed_zone("recovery_save_pct", "recovery", recov_value),
                    trend="n_a",
                    weekly_points_in_window=0,
                    sample_size=recov_games,
                    sample_quality=recov_quality,
                    is_headline_eligible=recov_quality != "thin",
                    dimension=recov_dim,
                )
            )

    return findings


def _findings_type_win_rate_timeline(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """type_win_rate_timeline -> per-class trend over timeline.per_type series.

    parent_subsection_id = "results_by_endgame_type" per D-13. These
    findings are NEVER headline-eligible — they are supporting only.
    """
    per_type = response.timeline.per_type
    findings: list[SubsectionFinding] = []

    if not per_type:
        findings.append(
            _empty_finding(
                "type_win_rate_timeline",
                window,
                "win_rate",
                parent="results_by_endgame_type",
            )
        )
        return findings

    for endgame_class, points in per_type.items():
        dim = {"endgame_class": endgame_class}
        if not points:
            findings.append(
                _empty_finding(
                    "type_win_rate_timeline",
                    window,
                    "win_rate",
                    parent="results_by_endgame_type",
                    dimension=dim,
                )
            )
            continue
        values = [p.win_rate for p in points]
        trend, weekly_points = _compute_trend(values)
        last_value = values[-1]
        sample_size = len(values)
        quality = sample_quality("type_win_rate_timeline", sample_size)
        # D-02/D-05: populate resampled series. type_win_rate uses monthly for
        # BOTH windows (5-way split makes weekly noise).
        weekly: list[tuple[str, float, int]] = [
            (p.date, p.win_rate, p.per_week_game_count) for p in points
        ]
        findings.append(
            SubsectionFinding(
                subsection_id="type_win_rate_timeline",
                parent_subsection_id="results_by_endgame_type",
                window=window,
                metric="win_rate",
                value=last_value,
                zone=assign_zone("win_rate", last_value),
                trend=trend,
                weekly_points_in_window=weekly_points,
                sample_size=sample_size,
                sample_quality=quality,
                # D-13: type_win_rate_timeline is never headline-eligible.
                is_headline_eligible=False,
                dimension=dim,
                # D-05: type_win_rate uses monthly for both windows (5-way split makes weekly noise).
                series=_weekly_points_to_time_points(weekly, "all_time"),
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
    render `gap=<v>, elo=<r>` per row and distinguish skill regression from
    rating growth outpacing skill.
    """
    if len(combo.points) < SPARSE_COMBO_FLOOR:
        return None
    weekly: list[tuple[str, float, int, int]] = [
        (p.date, float(p.endgame_elo - p.actual_elo), p.per_week_endgame_games, p.actual_elo)
        for p in combo.points
    ]
    return _weekly_points_to_time_points_with_elo(weekly, window)


def _weekly_points_to_time_points_with_elo(
    weekly: list[tuple[str, float, int, int]],
    window: Window,
) -> list[TimePoint]:
    """Endgame-elo variant of `_weekly_points_to_time_points` that also
    carries `actual_elo` through. Weighted by game count (same convention as
    the gap value) so the monthly aggregate satisfies the invariant
    `value ≈ endgame_elo - actual_elo` for the aggregated `actual_elo`.
    """
    if not weekly:
        return []
    if window == "last_3mo":
        return [
            TimePoint(bucket_start=d, value=v, n=n, actual_elo=elo)
            for d, v, n, elo in sorted(weekly, key=lambda t: t[0])
        ]
    # all_time -> monthly
    buckets: dict[str, list[tuple[float, int, int]]] = defaultdict(list)
    for date_iso, value, n, elo in weekly:
        ym = date_iso[:7]
        buckets[ym].append((value, n, elo))
    points: list[TimePoint] = []
    for ym in sorted(buckets.keys()):
        weeks = buckets[ym]
        total_n = sum(n for _, n, _ in weeks)
        if total_n > 0:
            weighted_sum = sum(v * n for v, n, _ in weeks)
            mean_value = weighted_sum / total_n
            elo_weighted_sum = sum(elo * n for _, n, elo in weeks)
            mean_elo = round(elo_weighted_sum / total_n)
        else:
            mean_value = statistics.mean(v for v, _, _ in weeks)
            mean_elo = round(statistics.mean(elo for _, _, elo in weeks))
        points.append(
            TimePoint(
                bucket_start=f"{ym}-01",
                value=mean_value,
                n=total_n,
                actual_elo=mean_elo,
            )
        )
    return points


def _endgame_skill_from_material_rows(rows: list[MaterialRow]) -> float:
    """Arithmetic mean of non-empty bucket-level rates (Phase 59 restored).

    Mirrors the frontend `endgameSkill()` helper and the backend
    `_endgame_skill_from_bucket_rows` pattern in endgame_service.py, but
    consumes the already-aggregated MaterialRow values from the response
    (not raw per-game rows). Per-bucket rate:

      conversion: win_pct / 100
      parity:     score (already 0.0-1.0)
      recovery:   (win_pct + draw_pct) / 100

    Returns `float("nan")` when no bucket has any games — the caller maps
    NaN to `is_headline_eligible=False`.
    """
    rates: list[float] = []
    for r in rows:
        if r.games <= 0:
            continue
        if r.bucket == "conversion":
            rates.append(r.win_pct / 100.0)
        elif r.bucket == "parity":
            rates.append(r.score)
        else:  # recovery
            rates.append((r.win_pct + r.draw_pct) / 100.0)
    if not rates:
        return float("nan")
    return sum(rates) / len(rates)


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
