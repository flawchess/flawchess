"""Endgame findings service: transforms `EndgameOverviewResponse` composites into
deterministic findings for the LLM prompt assembly in Phase 65.

Scope (Phase 63):

- `compute_findings(filter_context, session, user_id)` is the sole public entry
  point. It issues TWO sequential calls to
  `endgame_service.get_endgame_overview` (one per time window) on the same
  `AsyncSession` and composes the per-subsection `SubsectionFinding` list.
- All data access goes through `endgame_service.get_endgame_overview` (FIND-01):
  this module MUST NOT import from `app.repositories`.
- Zones, trend gates, and flag thresholds are sourced from named constants in
  `app.services.endgame_zones` (FIND-02): no inline magic numbers.
- The four cross-section flags are computed deterministically from all_time
  findings (FIND-03).
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

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import (
    ClockStatsRow,
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameOverviewResponse,
    MaterialBucket,
    MaterialRow,
    ScoreGapTimelinePoint,
)
from app.schemas.insights import (
    EndgameTabFindings,
    FilterContext,
    FlagId,
    SubsectionFinding,
)
from app.services.endgame_service import get_endgame_overview
from app.services.endgame_zones import (
    NEUTRAL_PCT_THRESHOLD,
    NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD,
    TREND_MIN_SLOPE_VOL_RATIO,
    TREND_MIN_WEEKLY_POINTS,
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
        sentry_sdk.set_context("insights", {"user_id": user_id, "filter_context": filter_context.model_dump()})
        sentry_sdk.capture_exception(exc)
        raise

    all_time_findings = _compute_subsection_findings(all_time_resp, window="all_time")
    last_3mo_findings = _compute_subsection_findings(last_3mo_resp, window="last_3mo")
    all_findings = all_time_findings + last_3mo_findings

    flags = _compute_flags(all_findings)

    findings = EndgameTabFindings(
        as_of=datetime.datetime.now(datetime.UTC),
        filters=filter_context,
        findings=all_findings,
        flags=flags,
        findings_hash="",  # placeholder; replaced below
    )
    findings_hash = _compute_hash(findings)
    return findings.model_copy(update={"findings_hash": findings_hash})


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
        response.performance.endgame_wdl.total
        + response.performance.non_endgame_wdl.total
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

    series = [p.score_difference for p in timeline]
    trend, weekly_points = _compute_trend(series)
    last_value = series[-1]
    sample_size = len(series)
    quality = sample_quality("score_gap_timeline", sample_size)
    # Timeline headline-eligibility hinges on the trend gate (D-13).
    is_headline = trend != "n_a"
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
    )


def _findings_endgame_metrics(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_metrics -> 1 endgame_skill + 9 bucket×metric findings.

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

    # 2. Nine bucket×metric findings. Bucket identity goes in dimension.
    # Values follow RESEARCH.md §Subsection Mapping:
    #   conversion_win_pct = win_pct / 100
    #   parity_score_pct   = score (already 0.0-1.0)
    #   recovery_save_pct  = (win_pct + draw_pct) / 100
    for row in rows:
        bucket: MaterialBucket = row.bucket
        # Explicit dict[str, str] annotation so ty widens the MaterialBucket
        # Literal value to str — dict value types are invariant otherwise.
        bucket_dim: dict[str, str] = {"bucket": bucket}
        bucket_games = row.games
        bucket_quality = sample_quality("endgame_metrics", bucket_games)
        bucket_headline = bucket_quality != "thin"

        if bucket_games == 0:
            findings.append(
                _empty_finding(
                    "endgame_metrics", window, "conversion_win_pct",
                    dimension=bucket_dim,
                )
            )
            findings.append(
                _empty_finding(
                    "endgame_metrics", window, "parity_score_pct",
                    dimension=bucket_dim,
                )
            )
            findings.append(
                _empty_finding(
                    "endgame_metrics", window, "recovery_save_pct",
                    dimension=bucket_dim,
                )
            )
            continue

        conv_value = row.win_pct / 100.0
        parity_value = row.score
        recov_value = (row.win_pct + row.draw_pct) / 100.0

        findings.append(
            SubsectionFinding(
                subsection_id="endgame_metrics",
                parent_subsection_id=None,
                window=window,
                metric="conversion_win_pct",
                value=conv_value,
                zone=assign_bucketed_zone("conversion_win_pct", bucket, conv_value),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=bucket_games,
                sample_quality=bucket_quality,
                is_headline_eligible=bucket_headline,
                dimension=bucket_dim,
            )
        )
        findings.append(
            SubsectionFinding(
                subsection_id="endgame_metrics",
                parent_subsection_id=None,
                window=window,
                metric="parity_score_pct",
                value=parity_value,
                zone=assign_bucketed_zone("parity_score_pct", bucket, parity_value),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=bucket_games,
                sample_quality=bucket_quality,
                is_headline_eligible=bucket_headline,
                dimension=bucket_dim,
            )
        )
        findings.append(
            SubsectionFinding(
                subsection_id="endgame_metrics",
                parent_subsection_id=None,
                window=window,
                metric="recovery_save_pct",
                value=recov_value,
                zone=assign_bucketed_zone("recovery_save_pct", bucket, recov_value),
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
                    "endgame_elo_timeline", window, "endgame_elo_gap",
                    dimension=dim,
                )
            )
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
            )
        )

    return findings


def _findings_time_pressure_at_entry(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """time_pressure_at_entry -> avg_clock_diff_pct + net_timeout_rate.

    Values are game-weighted means across ClockStatsRow rows (one per time
    control). `net_timeout_rate` is passed to `assign_zone` with its sign
    flipped to match the registry's `lower_is_better` direction (D-06 A1
    resolution) — the raw value is preserved in the SubsectionFinding so
    Phase 65 prompt-assembly sees the real formula output.
    """
    rows: list[ClockStatsRow] = response.clock_pressure.rows
    total_clock_games = response.clock_pressure.total_clock_games

    clock_diff_quality = sample_quality("time_pressure_at_entry", total_clock_games)
    is_headline = clock_diff_quality != "thin"

    findings: list[SubsectionFinding] = []

    if not rows or total_clock_games == 0:
        findings.append(
            _empty_finding("time_pressure_at_entry", window, "avg_clock_diff_pct")
        )
        findings.append(
            _empty_finding("time_pressure_at_entry", window, "net_timeout_rate")
        )
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

    # D-06 resolution: the registry declares net_timeout_rate as
    # `lower_is_better`, but ClockStatsRow.net_timeout_rate is
    # (timeout_wins - timeout_losses) / total * 100 — positive when the user
    # wins flag battles. We flip the sign before calling assign_zone so the
    # zone matches the user's actual advantage under the locked
    # lower_is_better semantic. Do NOT store the negated value — emit the
    # original formula output in the finding so Phase 65 prompt-assembly
    # sees the actual number, not its sign-flipped proxy.
    net_timeout_zone_input = (
        -net_timeout_value if not math.isnan(net_timeout_value) else net_timeout_value
    )
    findings.append(
        SubsectionFinding(
            subsection_id="time_pressure_at_entry",
            parent_subsection_id=None,
            window=window,
            metric="net_timeout_rate",
            value=net_timeout_value,
            zone=assign_zone("net_timeout_rate", net_timeout_zone_input),
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

    series = [p.avg_clock_diff_pct for p in timeline]
    trend, weekly_points = _compute_trend(series)
    last_value = series[-1]
    sample_size = len(series)
    quality = sample_quality("clock_diff_timeline", sample_size)
    is_headline = trend != "n_a"
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
        return _empty_finding(
            "time_pressure_vs_performance", window, "avg_clock_diff_pct"
        )

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
    """results_by_endgame_type -> per-category endgame_skill finding.

    Value = category win rate (0.0-1.0), derived from EndgameCategoryStats.
    """
    categories: list[EndgameCategoryStats] = response.stats.categories
    findings: list[SubsectionFinding] = []

    if not categories:
        findings.append(
            _empty_finding("results_by_endgame_type", window, "endgame_skill")
        )
        return findings

    for cat in categories:
        # Explicit dict[str, str] annotation so ty widens the EndgameClass
        # Literal to str — dict value types are invariant otherwise.
        dim: dict[str, str] = {"endgame_class": cat.endgame_class}
        if cat.total == 0:
            findings.append(
                _empty_finding(
                    "results_by_endgame_type", window, "endgame_skill",
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
                metric="endgame_skill",
                value=value,
                zone=assign_zone("endgame_skill", value),
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
        findings.append(
            _empty_finding(
                "conversion_recovery_by_type", window, "conversion_win_pct"
            )
        )
        findings.append(
            _empty_finding(
                "conversion_recovery_by_type", window, "recovery_save_pct"
            )
        )
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
                    "conversion_recovery_by_type", window, "conversion_win_pct",
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
                    zone=assign_bucketed_zone(
                        "conversion_win_pct", "conversion", conv_value
                    ),
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
                    "conversion_recovery_by_type", window, "recovery_save_pct",
                    dimension=recov_dim,
                )
            )
        else:
            recov_value = cat.conversion.recovery_pct / 100.0
            recov_quality = sample_quality(
                "conversion_recovery_by_type", recov_games
            )
            findings.append(
                SubsectionFinding(
                    subsection_id="conversion_recovery_by_type",
                    parent_subsection_id=None,
                    window=window,
                    metric="recovery_save_pct",
                    value=recov_value,
                    zone=assign_bucketed_zone(
                        "recovery_save_pct", "recovery", recov_value
                    ),
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
                "type_win_rate_timeline", window, "endgame_skill",
                parent="results_by_endgame_type",
            )
        )
        return findings

    for endgame_class, points in per_type.items():
        dim = {"endgame_class": endgame_class}
        if not points:
            findings.append(
                _empty_finding(
                    "type_win_rate_timeline", window, "endgame_skill",
                    parent="results_by_endgame_type",
                    dimension=dim,
                )
            )
            continue
        series = [p.win_rate for p in points]
        trend, weekly_points = _compute_trend(series)
        last_value = series[-1]
        sample_size = len(series)
        quality = sample_quality("type_win_rate_timeline", sample_size)
        findings.append(
            SubsectionFinding(
                subsection_id="type_win_rate_timeline",
                parent_subsection_id="results_by_endgame_type",
                window=window,
                metric="endgame_skill",
                value=last_value,
                zone=assign_zone("endgame_skill", last_value),
                trend=trend,
                weekly_points_in_window=weekly_points,
                sample_size=sample_size,
                sample_quality=quality,
                # D-13: type_win_rate_timeline is never headline-eligible.
                is_headline_eligible=False,
                dimension=dim,
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


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


def _compute_flags(findings: list[SubsectionFinding]) -> list[FlagId]:
    """Compute four cross-section flags from all_time findings (FIND-03).

    All thresholds reference named constants from
    `app.services.endgame_zones` — no inline magic numbers. Flags fire
    only when the underlying findings exist with non-NaN values; missing
    data produces an absent flag, not a false positive.
    """
    by_key: dict[tuple[SubsectionId, Window, MetricId], SubsectionFinding] = {}
    for f in findings:
        if f.window != "all_time":
            continue
        # Top-level lookups only (no dimensioned bucket rows). The four
        # flags read the aggregate endgame_skill / score_gap findings and
        # the weighted-mean clock metric — all of which have dimension=None.
        if f.dimension is not None and f.subsection_id != "endgame_elo_timeline":
            continue
        by_key[(f.subsection_id, f.window, f.metric)] = f

    flags: list[FlagId] = []

    # Flag 1 — baseline_lift_mutes_score_gap
    skill_f = by_key.get(("endgame_metrics", "all_time", "endgame_skill"))
    sg_f = by_key.get(("overall", "all_time", "score_gap"))
    if (
        skill_f is not None
        and sg_f is not None
        and skill_f.zone == "strong"
        and sg_f.zone in ("typical", "weak")
    ):
        flags.append("baseline_lift_mutes_score_gap")

    # Flag 2 — clock_entry_advantage
    clock_f = by_key.get(
        ("time_pressure_at_entry", "all_time", "avg_clock_diff_pct")
    )
    if (
        clock_f is not None
        and not math.isnan(clock_f.value)
        and clock_f.value > NEUTRAL_PCT_THRESHOLD
    ):
        flags.append("clock_entry_advantage")

    # Flag 3 — no_clock_entry_advantage
    if (
        clock_f is not None
        and not math.isnan(clock_f.value)
        and abs(clock_f.value) <= NEUTRAL_PCT_THRESHOLD
    ):
        flags.append("no_clock_entry_advantage")

    # Flag 4 — notable_endgame_elo_divergence
    elo_findings = [
        f for f in findings
        if f.subsection_id == "endgame_elo_timeline"
        and f.window == "all_time"
        and f.metric == "endgame_elo_gap"
        and not math.isnan(f.value)
    ]
    if any(
        abs(f.value) > NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD
        for f in elo_findings
    ):
        flags.append("notable_endgame_elo_divergence")

    return flags


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
