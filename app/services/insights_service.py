"""Endgame findings service: transforms the ranked Endgame Stats payload into
deterministic findings for the LLM prompt assembly in Phase 65.

Scope (Phase 63, re-based on the ranked payload in Phase 238 / D-04):

- `compute_findings(session, user_id)` is the sole public entry point. It awaits
  `fetch_ranked_inputs` ONCE, then builds two windows from the same inputs with the
  pure `build_ranked_stats`: `all_time` (the ranked sample the Stats tab shows) and
  `last_3mo` (the ranked games played in the last 90 days). No second DB pass.
- All data access goes through `endgame_ranked_service` (FIND-01): this module MUST
  NOT import from `app.repositories` and never calls the filtered overview.
- Findings are filter-independent (D-04): one report per user over the ranked sample.
  Overall-section findings are per time control (`dimension={"time_control": tc}`),
  mirroring the per-TC UI (D-00h); no pooled or page-level weighted number is emitted.
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

- One sequential `fetch_ranked_inputs` await on the caller's `AsyncSession`, never
  concurrent gather (CLAUDE.md §Critical Constraints).
- Phase 87.4 (D-05): the aggregate `endgame_skill` concept was retired
  end-to-end (no composite definition survived scrutiny).
- Percentiles exist only on the all_time window: the stored percentile ranks the full
  ranked sample, so `build_ranked_stats(since=...)` drops them (D-04) and
  `per_tc_metric_percentiles` is built from the all_time payload alone.
- Non-trivial except blocks call `sentry_sdk.set_context` with structured
  data, not variable-in-message strings (CLAUDE.md §Sentry).
"""

import datetime
import hashlib
import json
import statistics
from collections import defaultdict
from collections.abc import Sequence
from typing import Final, Literal

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import (
    EndgameCategoryStats,
    EndgameEloTimelineCombo,
    EndgameEloTimelinePoint,
    RankedMetricOut,
    RankedTcStats,
    ScoreGapTimelinePoint,
)
from app.schemas.insights import (
    EndgameTabFindings,
    MetricPercentileRecord,
    PlayerProfileEntry,
    RatingAnchorContext,
    SubsectionFinding,
    TimePoint,
)
from app.services.endgame_ranked_service import (
    build_ranked_stats,
    fetch_ranked_inputs,
)
from app.services.endgame_zones import (
    MIN_GAMES_PER_TC_CARD,
    TREND_MIN_SLOPE_VOL_RATIO,
    TREND_MIN_WEEKLY_POINTS,
    BucketedMetricId,
    MetricId,
    SubsectionId,
    TcBandMetricId,
    TcBucket,
    Trend,
    Window,
    assign_per_class_tc_zone,
    assign_tc_metric_zone,
    assign_zone,
    sample_quality,
)
from app.services.global_percentile_cdf import CdfMetricId

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

# Calendar window of the `last_3mo` findings: ranked games played in the last 90 days
# (planner assumption A9, Phase 238).
LAST_3MO_WINDOW_DAYS: Final[int] = 90

# Minimum sample for a single-aggregate tile (entry eval, scores, Eval Score Gap) to
# emit a real finding rather than the empty placeholder (Phase 82 D-17 / Phase 83 D-19).
_MIN_TILE_SAMPLE: Final[int] = 10

# ---------------------------------------------------------------------------
# Percentile helpers.
# ---------------------------------------------------------------------------

# Finding-side metric ids each ranked CdfMetricId is keyed under in
# `per_tc_metric_percentiles` ("{metric}:{tc}"). The DB / ranked id and the finding id
# differ for the rates (conversion_rate <-> conversion_win_pct, ...) and for recovery's
# score gap (recovery_score_gap <-> score_gap_recov); both recovery names are written so
# a renderer looking up either finds the record.
_PCTL_KEYS: Final[dict[CdfMetricId, tuple[str, ...]]] = {
    "score_gap": ("score_gap",),
    "achievable_score_gap": ("achievable_score_gap",),
    "score_gap_conv": ("score_gap_conv",),
    "score_gap_parity": ("score_gap_parity",),
    "recovery_score_gap": ("score_gap_recov", "recovery_score_gap"),
    "time_pressure_score_gap": ("time_pressure_score_gap",),
    "clock_gap": ("clock_gap",),
    "net_flag_rate": ("net_flag_rate",),
    "conversion_rate": ("conversion_win_pct",),
    "parity_rate": ("parity_score_pct",),
    "recovery_rate": ("recovery_save_pct",),
}

# Percentile record values are rendered on the UI's 0-100 scale.
_PCT_SCALE: Final[float] = 100.0


def _cohort_anchors(tcs: Sequence[RankedTcStats]) -> dict[str, RatingAnchorContext]:
    """Per-TC rating-anchor context for the `[rating basis]` block (TCs with an anchor)."""
    return {
        t.tc: RatingAnchorContext(
            anchor_rating=t.anchor.anchor_rating,
            n_chesscom_games=t.anchor.n_chesscom_games,
            n_lichess_games=t.anchor.n_lichess_games,
            chesscom_median_native=t.anchor.chesscom_median_native,
            lichess_median_native=t.anchor.lichess_median_native,
        )
        for t in tcs
        if t.anchor is not None
    }


def _per_tc_metric_percentiles(tcs: Sequence[RankedTcStats]) -> dict[str, MetricPercentileRecord]:
    """Percentile records keyed "{metric}:{tc}" for every metric whose status is 'ranked'.

    Every record is per TC (D-04): there is no page-level game-count-weighted record.
    `value` is scaled x100 (UI scale), `n_games` is the metric's own n, `anchor` the TC's
    blended Lichess-equivalent rating. Cells that are below their floor, pending or not
    yet ranked carry no percentile and therefore no record.
    """
    records: dict[str, MetricPercentileRecord] = {}
    for tc_stats in tcs:
        anchor = tc_stats.anchor.anchor_rating if tc_stats.anchor is not None else None
        for metric_id, metric in tc_stats.metrics.items():
            if metric.status != "ranked" or metric.percentile is None:
                continue
            record = MetricPercentileRecord(
                percentile=metric.percentile,
                value=metric.value * _PCT_SCALE if metric.value is not None else None,
                n_games=metric.n,
                anchor=anchor,
                tc=tc_stats.tc,
            )
            for finding_metric in _PCTL_KEYS[metric_id]:
                records[f"{finding_metric}:{tc_stats.tc}"] = record
    return records


def _type_categories_by_tc(
    tcs: Sequence[RankedTcStats],
) -> dict[TcBucket, list[EndgameCategoryStats]]:
    """TC -> Endgame Type rows (rook / minor piece / pawn / queen) from the ranked payload."""
    return {t.tc: t.type_categories for t in tcs if t.type_categories}


def _elo_combos(tcs: Sequence[RankedTcStats]) -> list[EndgameEloTimelineCombo]:
    """Every TC's Endgame ELO combos (already per (platform, TC)), in TC order."""
    return [combo for t in tcs for combo in t.elo_timeline]


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


async def compute_findings(session: AsyncSession, user_id: int) -> EndgameTabFindings:
    """Compute deterministic findings for the Endgame tab (Phase 63 FIND-01..05; D-04).

    One `fetch_ranked_inputs` await (sequential on the caller's `AsyncSession`, never
    concurrent gather per CLAUDE.md §Critical Constraints), then two pure builds from
    the same inputs: `all_time` = the ranked sample, `last_3mo` = the ranked games played
    in the last `LAST_3MO_WINDOW_DAYS` days. There is no filter input: the report is one
    per user over the sample the Stats tab shows.

    Returns an `EndgameTabFindings` whose `findings_hash` excludes `as_of` so the cache
    does not churn daily (FIND-05).
    """
    try:
        inputs = await fetch_ranked_inputs(session, user_id=user_id)
    except Exception as exc:
        # CLAUDE.md §Sentry: pass variable data via set_context; never embed
        # user_id in the error message (grouping).
        sentry_sdk.set_context("insights", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise

    as_of = datetime.datetime.now(datetime.UTC)
    all_time = build_ranked_stats(inputs).tcs
    last_3mo = build_ranked_stats(
        inputs, since=as_of - datetime.timedelta(days=LAST_3MO_WINDOW_DAYS)
    ).tcs
    return build_findings(all_time, last_3mo, as_of=as_of)


def build_findings(
    all_time: Sequence[RankedTcStats],
    last_3mo: Sequence[RankedTcStats],
    *,
    as_of: datetime.datetime,
) -> EndgameTabFindings:
    """Pure assembly of `EndgameTabFindings` from the two ranked windows (no DB)."""
    all_findings = _compute_subsection_findings(all_time, window="all_time") + (
        _compute_subsection_findings(last_3mo, window="last_3mo")
    )
    per_tc_pctls = _per_tc_metric_percentiles(all_time)
    cohort_anchors = _cohort_anchors(all_time)
    type_categories_by_tc = _type_categories_by_tc(all_time)
    findings = EndgameTabFindings(
        as_of=as_of,
        findings=all_findings,
        player_profile=compute_player_profile(_elo_combos(all_time)),
        ranked_tcs=list(all_time),
        per_tc_metric_percentiles=per_tc_pctls if per_tc_pctls else None,
        cohort_anchors=cohort_anchors if cohort_anchors else None,
        type_categories_by_tc=type_categories_by_tc if type_categories_by_tc else None,
        findings_hash="",  # placeholder; replaced below
    )
    return findings.model_copy(update={"findings_hash": _compute_hash(findings)})


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
    today = datetime.datetime.now(datetime.UTC).date()
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
# Subsection extraction — transforms the ranked TCs of ONE window into the
# list of SubsectionFinding for that window.
# ---------------------------------------------------------------------------


def _compute_subsection_findings(
    tcs: Sequence[RankedTcStats],
    window: Window,
) -> list[SubsectionFinding]:
    """Extract all per-subsection findings for one window.

    Empty subsections emit the standard empty-window placeholder (`_empty_finding`).
    Trend is computed over the timeline subsections only; non-timeline subsections
    carry `trend="n_a"` and `weekly_points_in_window=0`.

    Phase 238 (D-04): every builder reads the ranked per-TC payload. The Overall and
    Score-timeline subsections are emitted per time control (never pooled); the
    Endgame Metrics, Endgame Type and Endgame ELO subsections were already per TC.
    A TC absent from `tcs` (no ranked games in this window) emits nothing, which the
    renderer shows as `last_3mo: no data`.
    """
    findings: list[SubsectionFinding] = []
    for tc_stats in tcs:
        findings.extend(_findings_endgame_start_vs_end(tc_stats, window))  # Phase 82 D-16
        findings.extend(_findings_score_gap(tc_stats, window))  # Phase 102 UAT
        findings.extend(_findings_score_timeline(tc_stats, window))
        findings.extend(_findings_endgame_metrics(tc_stats, window))
    findings.extend(_findings_endgame_elo_timeline(tcs, window))
    # Phase 102 UAT (2026-06-02): _findings_time_pressure_at_entry removed — the
    # time_pressure LLM section is driven by the per-TC chart block (Clock Gap +
    # Net Flag Rate percentile aggregates), not blended page-level scalars.
    # Phase 102 UAT (2026-06-02): each eligible time control becomes its own
    # `endgame_type_<tc>` subsection mirroring the UI's per-TC collapsible Endgame
    # Type cards.
    findings.extend(_findings_endgame_type_by_tc(tcs, window))
    return findings


# ---------------------------------------------------------------------------
# Per-subsection builders. Kept small so each subsection's mapping from the
# ranked payload fields to SubsectionFinding is easy to audit.
# ---------------------------------------------------------------------------


def _tc_dimension(tc: TcBucket) -> dict[str, str]:
    """`{"time_control": tc}` dimension; explicit dict[str, str] widens the Literal (invariance)."""
    return {"time_control": tc}


def _scalar_finding(
    *,
    subsection_id: SubsectionId,
    window: Window,
    metric: MetricId,
    value: float,
    sample_size: int,
    dimension: dict[str, str] | None,
) -> SubsectionFinding:
    """Single-aggregate finding: zone from the global registry, trend n_a, headline iff not thin."""
    quality = sample_quality(subsection_id, sample_size)
    return SubsectionFinding(
        subsection_id=subsection_id,
        parent_subsection_id=None,
        window=window,
        metric=metric,
        value=value,
        zone=assign_zone(metric, value),
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=sample_size,
        sample_quality=quality,
        is_headline_eligible=quality != "thin",
        dimension=dimension,
    )


def _findings_score_gap(
    tc_stats: RankedTcStats,
    window: Window,
) -> list[SubsectionFinding]:
    """score_gap subsection (one time control) -> TWO findings, mirroring the UI
    "Endgame Score Differences" card order: achievable_score_gap ("Eval Score Gap")
    first, then score_gap ("Endgame Score Gap").

    Phase 238 (D-04, D-00h): built from the TC's ranked metrics and emitted per time
    control with `dimension={"time_control": tc}`, so the narrated value is exactly the
    ranked value the Stats tab shows for that TC.
    """
    dim = _tc_dimension(tc_stats.tc)
    findings: list[SubsectionFinding] = []

    # Eval Score Gap (achievable_score_gap): paired over endgame games with a non-null
    # entry eval. Gate on the same cohort size as the entry_expected_score tile.
    asg = tc_stats.metrics["achievable_score_gap"]
    if asg.value is None or asg.n < _MIN_TILE_SAMPLE:
        findings.append(_empty_finding("score_gap", window, "achievable_score_gap", dimension=dim))
    else:
        findings.append(
            _scalar_finding(
                subsection_id="score_gap",
                window=window,
                metric="achievable_score_gap",
                value=asg.value,
                sample_size=asg.n,
                dimension=dim,
            )
        )

    # Endgame Score Gap (score_gap): endgame - non_endgame. The empty-window gate
    # intentionally diverges from the `< 10` floor above: the denominator is endgame +
    # non_endgame games, so a `>= 1` payload is informationally meaningful. The
    # downstream `_assemble_user_prompt` filter (sample_size == 0 AND quality == "thin")
    # still drops sub-`SAMPLE_QUALITY_BANDS["score_gap"][0]` payloads from the rendered
    # prompt via the per-finding sample-quality classifier.
    overall = tc_stats.overall
    sample_size = overall.endgame_wdl.total + overall.non_endgame_wdl.total
    sg = tc_stats.metrics["score_gap"]
    if sample_size == 0 or sg.value is None:
        findings.append(_empty_finding("score_gap", window, "score_gap", dimension=dim))
    else:
        findings.append(
            _scalar_finding(
                subsection_id="score_gap",
                window=window,
                metric="score_gap",
                value=sg.value,
                sample_size=sample_size,
                dimension=dim,
            )
        )
    return findings


def _wdl_score(wins: int, draws: int, total: int) -> float:
    """Score fraction (win = 1, draw = 0.5) of a W/D/L summary."""
    return (wins + 0.5 * draws) / total


def _findings_endgame_start_vs_end(
    tc_stats: RankedTcStats,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_start_vs_end (one time control) -> FOUR findings, in UI-card order:
    endgame_score, non_endgame_score, entry_eval_pawns, entry_expected_score.

    Phase 82 (D-16): wire entry_eval_mean_pawns and endgame Score-vs-50% into the LLM
    payload. All findings are single-aggregate, no series. Empty-window convention:
    entry_eval_n < 10 OR endgame_wdl.total < 10 OR non_endgame_wdl.total < 10 OR
    entry_expected_score_n < 10 -> _empty_finding for the affected tile (gated
    independently per Phase 82 D-17 / Phase 83 D-19). is_headline_eligible =
    sample_quality != "thin" (D-18).

    Phase 83 (D-17 / D-19): entry_expected_score is the Stockfish-baseline achievable
    score via the Lichess sigmoid. No `verdict` field: the LLM narrates strictly by
    zone (memory feedback_llm_significance_signal.md).

    Phase 102 UAT: non_endgame_score ("Games without Endgame" card) shares
    endgame_score's 0.45-0.55 vs-50% band; the two score cards lead the subsection.

    Phase 238 (D-04, D-00h): built from the TC's ranked overall block
    (endgame_wdl / non_endgame_wdl / entry_flow) and emitted per time control with
    `dimension={"time_control": tc}`.
    """
    sid: SubsectionId = "endgame_start_vs_end"
    dim = _tc_dimension(tc_stats.tc)
    overall = tc_stats.overall
    flow = overall.entry_flow

    # Tile 1 - entry eval (gate on entry_eval_n >= 10)
    if flow.entry_eval_n < _MIN_TILE_SAMPLE or flow.entry_eval_mean_pawns is None:
        tile1 = _empty_finding(sid, window, "entry_eval_pawns", dimension=dim)
    else:
        tile1 = _scalar_finding(
            subsection_id=sid,
            window=window,
            metric="entry_eval_pawns",
            value=flow.entry_eval_mean_pawns,
            sample_size=flow.entry_eval_n,
            dimension=dim,
        )

    # Tile 2 - endgame score vs 50% (gate on endgame_wdl.total >= 10)
    eg = overall.endgame_wdl
    if eg.total < _MIN_TILE_SAMPLE:
        tile2 = _empty_finding(sid, window, "endgame_score", dimension=dim)
    else:
        tile2 = _scalar_finding(
            subsection_id=sid,
            window=window,
            metric="endgame_score",
            value=_wdl_score(eg.wins, eg.draws, eg.total),
            sample_size=eg.total,
            dimension=dim,
        )

    # Tile 2b - non-endgame score vs 50% (Phase 102 UAT: gate on non_endgame_wdl.total >= 10).
    ne = overall.non_endgame_wdl
    if ne.total < _MIN_TILE_SAMPLE:
        tile2b = _empty_finding(sid, window, "non_endgame_score", dimension=dim)
    else:
        tile2b = _scalar_finding(
            subsection_id=sid,
            window=window,
            metric="non_endgame_score",
            value=_wdl_score(ne.wins, ne.draws, ne.total),
            sample_size=ne.total,
            dimension=dim,
        )

    # Tile 3 - achievable score (Phase 83 D-19: gate on the expected-score cohort n >= 10)
    if flow.n < _MIN_TILE_SAMPLE or flow.expected_score is None:
        tile3 = _empty_finding(sid, window, "entry_expected_score", dimension=dim)
    else:
        tile3 = _scalar_finding(
            subsection_id=sid,
            window=window,
            metric="entry_expected_score",
            value=flow.expected_score,
            sample_size=flow.n,
            dimension=dim,
        )

    # UI-card order (Phase 102 UAT): the two score cards lead, then the two entry-eval
    # tiles. tile1 = entry_eval_pawns, tile2 = endgame_score, tile2b = non_endgame_score,
    # tile3 = entry_expected_score.
    return [tile2, tile2b, tile1, tile3]


def _findings_score_timeline(
    tc_stats: RankedTcStats,
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
    Phase 238 (D-04, D-00h): built from one TC's ranked `score_gap_timeline` and emitted
    per time control with `dimension={"time_control": tc}` (never pooled across TCs).

    Granularity stays WEEKLY in both windows (unlike other timelines that
    resample all_time to monthly) — the ISO-week bucketing is the natural
    grain of `compute_score_gap_timeline` and the two-line chart reads
    weekly points directly. `_series_granularity` in insights_llm.py pins
    this explicitly for subsection_id == "score_timeline".
    """
    dim = _tc_dimension(tc_stats.tc)
    timeline: list[ScoreGapTimelinePoint] = tc_stats.score_gap_timeline
    if not timeline:
        return [
            _empty_finding("score_timeline", window, "endgame_score_timeline", dimension=dim),
            _empty_finding("score_timeline", window, "non_endgame_score_timeline", dimension=dim),
            _empty_finding("score_timeline", window, "score_gap", dimension=dim),
        ]

    sample_size = len(timeline)
    quality = sample_quality("score_timeline", sample_size)

    # Per-part scalar means (authoritative values for each summary's
    # `mean=` field). The TC's ranked `score_gap` metric stays the aggregate for the
    # score_gap finding so both the score_gap and score_timeline summaries quote the
    # same source of truth; the series mean is only the fallback when the metric has
    # no value (e.g. one side of the endgame / non-endgame split is empty).
    endgame_mean = statistics.mean(p.endgame_score for p in timeline)
    non_endgame_mean = statistics.mean(p.non_endgame_score for p in timeline)
    ranked_gap = tc_stats.metrics["score_gap"].value
    gap_mean = (
        ranked_gap
        if ranked_gap is not None
        else statistics.mean(p.score_difference for p in timeline)
    )

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
            dimension=dim,
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
            dimension=dim,
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
            dimension=dim,
            series=gap_series,
        ),
    ]


# Phase 102 UAT (2026-06-02): per-TC Endgame Metrics rows. Each tuple is
# (ranked rate metric, finding rate metric, ranked ΔES-gap metric, finding ΔES-gap
# metric, per-TC-band gap metric). tc_gap_metric is None for parity: its ΔES-gap
# neutral band stays global (score_gap_parity is NOT a TcBandMetricId — see
# endgame_zones.TC_METRIC_BANDS), so the parity gap zone routes through assign_zone,
# not assign_tc_metric_zone. The recovery gap is `recovery_score_gap` on the ranked
# payload but `score_gap_recov` on the finding (naming bridge, same as _PCTL_KEYS).
_METRICS_ELO_BUCKETS: tuple[
    tuple[CdfMetricId, BucketedMetricId, CdfMetricId, MetricId, TcBandMetricId | None], ...
] = (
    ("conversion_rate", "conversion_win_pct", "score_gap_conv", "score_gap_conv", "score_gap_conv"),
    ("parity_rate", "parity_score_pct", "score_gap_parity", "score_gap_parity", None),
    (
        "recovery_rate",
        "recovery_save_pct",
        "recovery_score_gap",
        "score_gap_recov",
        "score_gap_recov",
    ),
)

# Phase 102 UAT: each eligible time control becomes its own subsection,
# mirroring the UI's per-TC Endgame Metrics cards. The aggregate-over-TC
# `endgame_metrics` subsection is retired.
_TC_TO_METRICS_SUBSECTION: dict[TcBucket, SubsectionId] = {
    "bullet": "endgame_metrics_bullet",
    "blitz": "endgame_metrics_blitz",
    "rapid": "endgame_metrics_rapid",
    "classical": "endgame_metrics_classical",
}


def _findings_endgame_metrics(
    tc_stats: RankedTcStats,
    window: Window,
) -> list[SubsectionFinding]:
    """metrics_elo -> one subsection for this time control, 6 findings.

    Phase 102 UAT (2026-06-02): each eligible time control becomes its own
    ``endgame_metrics_<tc>`` subsection mirroring the UI, carrying the three rate
    findings (conversion_win_pct / parity_score_pct / recovery_save_pct) and the three
    ΔES-gap findings (score_gap_conv / score_gap_parity / score_gap_recov). Rate + gap
    are interleaved per bucket to mirror the UI's Conv | Parity | Recov columns. Zones
    use per-TC bands so the payload's ``zone=`` label and inline ``(typical …)`` bound
    match the page's per-TC gauges; per-TC percentiles are attached at render time via
    the finding's ``time_control`` dimension (see _lookup_pctl_record).

    Phase 238 (D-04): values and sample sizes come straight from the TC's ranked
    ``metrics`` (value and n), so the narrated number is the ranked value the Stats tab
    shows. The TC is eligible when its ranked endgame game count reaches
    MIN_GAMES_PER_TC_CARD (the gate that used to filter the per-TC cards).

    Per CONTEXT.md A1: each rate metric is still tied to exactly ONE bucket, so
    no cross-bucket fan-out occurs.
    """
    if tc_stats.overall.endgame_wdl.total < MIN_GAMES_PER_TC_CARD:
        return []
    tc: TcBucket = tc_stats.tc
    subsection_id = _TC_TO_METRICS_SUBSECTION[tc]
    findings: list[SubsectionFinding] = []
    for rate_key, rate_metric, gap_key, gap_metric, tc_gap_metric in _METRICS_ELO_BUCKETS:
        findings.append(
            _tc_rate_finding(subsection_id, tc, rate_metric, tc_stats.metrics[rate_key], window)
        )
        findings.append(
            _tc_score_gap_finding(
                subsection_id, tc, gap_metric, tc_gap_metric, tc_stats.metrics[gap_key], window
            )
        )
    return findings


def _tc_rate_finding(
    subsection_id: SubsectionId,
    tc: TcBucket,
    rate_metric: BucketedMetricId,
    stats: RankedMetricOut,
    window: Window,
) -> SubsectionFinding:
    """Emit one per-TC rate finding (conversion / parity / recovery)."""
    dim = _tc_dimension(tc)
    if stats.n == 0 or stats.value is None:
        return _empty_finding(subsection_id, window, rate_metric, dimension=dim)
    quality = sample_quality(subsection_id, stats.n)
    return SubsectionFinding(
        subsection_id=subsection_id,
        parent_subsection_id=None,
        window=window,
        metric=rate_metric,
        value=stats.value,
        zone=assign_tc_metric_zone(rate_metric, tc, stats.value),
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=stats.n,
        sample_quality=quality,
        is_headline_eligible=quality != "thin",
        dimension=dim,
    )


def _tc_score_gap_finding(
    subsection_id: SubsectionId,
    tc: TcBucket,
    gap_metric: MetricId,
    tc_gap_metric: TcBandMetricId | None,
    stats: RankedMetricOut,
    window: Window,
) -> SubsectionFinding:
    """Emit one per-TC ΔES Score Gap finding.

    Wire shape per finding: (mean, n, zone). No p_value / verdict — the band IS
    the significance signal (memory feedback_llm_significance_signal.md). The
    conv/recov gaps use per-TC bands (tc_gap_metric); parity's gap (tc_gap_metric
    is None) uses the global neutral band via assign_zone.
    """
    mean_raw = stats.value
    n_raw = stats.n
    value = mean_raw if mean_raw is not None else float("nan")
    zone = (
        assign_zone(gap_metric, value)
        if tc_gap_metric is None
        else assign_tc_metric_zone(tc_gap_metric, tc, value)
    )
    return SubsectionFinding(
        subsection_id=subsection_id,
        parent_subsection_id=None,
        window=window,
        metric=gap_metric,
        value=value,
        zone=zone,
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=n_raw,
        sample_quality=sample_quality(subsection_id, n_raw),
        is_headline_eligible=(n_raw >= _MIN_TILE_SAMPLE and mean_raw is not None),
        dimension=_tc_dimension(tc),
    )


def _findings_endgame_elo_timeline(
    tcs: Sequence[RankedTcStats],
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_elo_timeline -> one finding per (platform, time_control) combo.

    Phase 238 (D-03): combos are the concatenation of every ranked TC's
    `elo_timeline` (already per (platform, time_control), built from that TC's ranked
    games only).

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
    combos: list[EndgameEloTimelineCombo] = _elo_combos(tcs)
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


# Phase 102 UAT (2026-06-02): _findings_time_pressure_at_entry was removed. The
# blended-across-TC avg_clock_diff_pct + net_timeout_rate page-level findings it
# produced are superseded by the per-TC Clock Gap + Net Flag Rate percentile
# aggregates the LLM chart block now renders (insights_llm._time_pressure_aggregate_lines),
# which carry percentiles the blended pair never had. The `time_pressure` section
# of the LLM payload is now driven entirely by the per-TC chart block.

# Phase 88.1 (Plan 09, REVIEW.md WR-06): _finding_clock_diff_timeline and
# _finding_time_pressure_vs_performance were removed. Both helpers had returned
# permanent empty findings since Phase 88 retired the underlying ClockPressureResponse
# and TimePressureChartResponse fields; emitting them on every call was a silent
# LLM-prompt regression because downstream consumers could not distinguish
# "feature deprecated" from "no user data". The full WR-06 orphan cleanup
# (insights_llm.py _SKIPPED_SUBSECTIONS, _format_time_pressure_chart_block, etc.)
# lives in app/services/insights_llm.py.


# Phase 102 UAT (2026-06-02): each eligible time control becomes its own
# `endgame_type_<tc>` subsection, mirroring the UI's per-TC collapsible Endgame
# Type breakdown (TypeTable). The aggregate-over-TC
# `results_by_endgame_type` + `conversion_recovery_by_type` subsections are retired.
_TC_TO_TYPE_SUBSECTION: dict[TcBucket, SubsectionId] = {
    "bullet": "endgame_type_bullet",
    "blitz": "endgame_type_blitz",
    "rapid": "endgame_type_rapid",
    "classical": "endgame_type_classical",
}

# Fixed TC order so the per-TC subsections render bullet → blitz → rapid →
# classical (matches the UI accordion order and _SECTION_LAYOUT).
_TYPE_TC_ORDER: tuple[TcBucket, ...] = ("bullet", "blitz", "rapid", "classical")


def _sorted_type_categories(
    cats: list[EndgameCategoryStats],
) -> list[EndgameCategoryStats]:
    """Sort per-TC categories by total desc (endgame_class tiebreak).

    Shared by the findings producer and the renderer's WDL table so the bullet
    order matches the table row order deterministically.
    """
    return sorted(cats, key=lambda c: (-c.total, c.endgame_class))


def _findings_endgame_type_by_tc(
    tcs: Sequence[RankedTcStats],
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_type_<tc> -> per-(class × TC) Conversion / Recovery / Score-Gap findings.

    Phase 102 UAT (2026-06-02): mirrors the UI's per-TC collapsible Endgame Type
    breakdown (TypeTable). For each eligible time control in
    each ranked TC's ``type_categories`` (already excluding mixed/pawnless upstream
    and gated to TCs with >= MIN_GAMES_PER_TC_CARD endgame games across the four
    visible classes) emits up to three findings per endgame class:

      - ``conversion_win_pct`` (win rate when entered with eval >= +1.0)
      - ``recovery_save_pct`` (draw+win rate when entered with eval <= -1.0)
      - ``endgame_type_achievable_score_gap`` (per-span ΔES vs the Stockfish baseline)

    Each carries a ``{endgame_class, time_control}`` dimension and dispatches its
    zone via ``assign_per_class_tc_zone`` so the payload's ``zone=`` label and the
    inline ``(typical …)`` bound match the per-TC tile gauges. ``win_rate`` is NOT
    emitted as a finding — the renderer's per-TC WDL table (built from
    ``type_categories_by_tc``) carries the W/D/L + Score% framing, mirroring the
    tile's WDL bar + score bullet. TCs below the game gate emit no findings, so the
    assembly loop omits their subsection entirely.
    """
    categories_by_tc = _type_categories_by_tc(tcs)
    if not categories_by_tc:
        return []
    findings: list[SubsectionFinding] = []
    for tc in _TYPE_TC_ORDER:
        cats = categories_by_tc.get(tc)
        if not cats or sum(c.total for c in cats) < MIN_GAMES_PER_TC_CARD:
            continue
        subsection_id = _TC_TO_TYPE_SUBSECTION[tc]
        for cat in _sorted_type_categories(cats):
            findings.extend(_endgame_type_class_findings(subsection_id, tc, cat, window))
    return findings


def _endgame_type_class_findings(
    subsection_id: SubsectionId,
    tc: TcBucket,
    cat: EndgameCategoryStats,
    window: Window,
) -> list[SubsectionFinding]:
    """Build the Conversion / Recovery / Score-Gap findings for one (class, TC) tile."""
    findings: list[SubsectionFinding] = []
    # Explicit dict[str, str] annotations so ty widens the EndgameClass / TcBucket
    # Literals to str — dict value types are invariant otherwise.
    conv_dim: dict[str, str] = {"endgame_class": cat.endgame_class, "time_control": tc}
    conv_games = cat.conversion.conversion_games
    if conv_games == 0:
        findings.append(
            _empty_finding(subsection_id, window, "conversion_win_pct", dimension=conv_dim)
        )
    else:
        conv_value = cat.conversion.conversion_pct / 100.0
        conv_quality = sample_quality(subsection_id, conv_games)
        findings.append(
            SubsectionFinding(
                subsection_id=subsection_id,
                parent_subsection_id=None,
                window=window,
                metric="conversion_win_pct",
                value=conv_value,
                zone=assign_per_class_tc_zone(
                    "conversion_win_pct", cat.endgame_class, tc, conv_value
                ),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=conv_games,
                sample_quality=conv_quality,
                is_headline_eligible=conv_quality != "thin",
                dimension=conv_dim,
            )
        )

    recov_dim: dict[str, str] = {"endgame_class": cat.endgame_class, "time_control": tc}
    recov_games = cat.conversion.recovery_games
    if recov_games == 0:
        findings.append(
            _empty_finding(subsection_id, window, "recovery_save_pct", dimension=recov_dim)
        )
    else:
        recov_value = cat.conversion.recovery_pct / 100.0
        recov_quality = sample_quality(subsection_id, recov_games)
        findings.append(
            SubsectionFinding(
                subsection_id=subsection_id,
                parent_subsection_id=None,
                window=window,
                metric="recovery_save_pct",
                value=recov_value,
                zone=assign_per_class_tc_zone(
                    "recovery_save_pct", cat.endgame_class, tc, recov_value
                ),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=recov_games,
                sample_quality=recov_quality,
                is_headline_eligible=recov_quality != "thin",
                dimension=recov_dim,
            )
        )

    # Per-span Score Gap — moved here from insights_llm._synthesize_* and now banded
    # per-(class × TC). n-gates follow compute_paired_difference_test (n == 0 → no
    # finding). Skipped (no finding) when the class has no eligible spans in this TC.
    gap_mean = cat.type_achievable_score_gap_mean
    gap_n = cat.type_achievable_score_gap_n or 0
    if gap_mean is not None and gap_n > 0:
        gap_dim: dict[str, str] = {"endgame_class": cat.endgame_class, "time_control": tc}
        gap_quality = sample_quality(subsection_id, gap_n)
        findings.append(
            SubsectionFinding(
                subsection_id=subsection_id,
                parent_subsection_id=None,
                window=window,
                metric="endgame_type_achievable_score_gap",
                value=gap_mean,
                zone=assign_per_class_tc_zone(
                    "endgame_type_achievable_score_gap", cat.endgame_class, tc, gap_mean
                ),
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=gap_n,
                sample_quality=gap_quality,
                is_headline_eligible=gap_quality != "thin",
                dimension=gap_dim,
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
