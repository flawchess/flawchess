"""LLM insights orchestration service for the endgame insights endpoint.

Scope (Phase 65):
- get_insights_agent(): singleton pydantic-ai Agent per CONTEXT.md D-21.
- generate_insights(filter_context, user_id, session): sole orchestration
  entry point called by app/routers/insights.py. Handles tier-1 cache,
  rate limit, tier-2 soft-fail, fresh LLM call, and log-row write.
- Custom exceptions map to HTTP status codes at the router layer (Plan 06).

Critical invariants:
- Sequential awaits on `session`; never asyncio.gather (CLAUDE.md constraint).
- _SYSTEM_PROMPT loaded at module import — module cannot import if the
  prompt file is missing. This is intentional: Phase 65 must fail to start
  if the system prompt is missing (CONTEXT.md D-27).
- Sentry set_context uses structured data (user_id, findings_hash, model,
  endpoint); NEVER f-string interpolation in exception messages (CLAUDE.md
  §Sentry / D-37).
- Latency captured around `await agent.run(user_prompt)` only (D-25).
"""

import datetime
import functools
import math
import time
from pathlib import Path
from typing import Literal, cast

import sentry_sdk
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm_log import LlmLog
from app.repositories.import_job_repository import get_latest_completed_import_with_games_at
from app.repositories.llm_log_repository import (
    count_recent_successful_misses,
    create_llm_log,
    get_latest_report_for_user,
    get_latest_successful_log_for_user,
    get_oldest_recent_miss_timestamp,
)
from app.schemas.endgames import TimePressureChartResponse
from app.schemas.insights import (
    EndgameInsightsReport,
    EndgameInsightsResponse,
    EndgameTabFindings,
    FilterContext,
    PlayerProfileEntry,
    SubsectionFinding,
    TimePoint,
)
from app.schemas.llm_log import LlmLogCreate, LlmLogEndpoint, LlmLogFilterContext
from app.services.endgame_zones import BUCKETED_ZONE_REGISTRY, ZONE_REGISTRY, ZoneSpec
from app.services.insights_service import compute_findings

# -- Module-level constants (CLAUDE.md: no magic numbers) --

INSIGHTS_MISSES_PER_HOUR = 3  # CONTEXT.md D-09
_PROMPT_VERSION = "endgame_v15"  # v15 (v1.11 cleanup pass): dropped stale "check the `Filters:` header" parenthetical from the avg_clock_diff_pct glossary entry — the `Filters:` header was removed in v9 and the insights router rejects non-default time_control filters, so the instruction pointed at nothing. Cache invalidation is automatic via prompt_version cache key. See `app/prompts/endgame_insights.md`. v14 (260424-pc6 UAT pass) introduced the three-metric score_timeline emitter (endgame_score / non_endgame_score / score_gap) plus constant-N disclosure and no-op zone bands for per-part absolute scores.
_OUTPUT_RETRIES = 2  # CONTEXT.md D-24, RESEARCH.md §2
_RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)
_ENDPOINT: LlmLogEndpoint = "insights.endgame"

# Structural cache TTL safety net (260425-dxh): bounds the sliding 3-month
# window narrative drift on cache hits. Lower to 14 if users complain about
# stale narratives.
INSIGHTS_CACHE_MAX_AGE_DAYS = 30
INSIGHTS_CACHE_MAX_AGE = datetime.timedelta(days=INSIGHTS_CACHE_MAX_AGE_DAYS)

# Series / prompt-assembly filter constants (260422-tnb A4/C3/A5/C2/C4/C5/C6).
MIN_BUCKET_N: int = 3  # A4: drop timeline points with n<3
_ACTIVITY_GAP_DAYS: int = 90  # C3: insert gap markers between >90-day-apart points
_ALL_TIME_CUTOFF_DAYS: int = 90  # C2: trim last 90d from all_time series when last_3mo exists
# C6 (v5): cap all_time series at the most-recent N monthly points. Older
# history rarely adds narrative value — Series interpretation rule already
# tells the LLM to focus on multi-bucket direction, not long history.
# v11: raised from 12 → 36 so the LLM can speak about multi-year trajectories
# without overclaiming a 12-month window as a long-term arc.
_ALL_TIME_MAX_POINTS: int = 36
# time_pressure_vs_performance produces a single weighted-mean finding that is
# not useful on its own; the 10-bucket chart is rendered separately by
# `_format_time_pressure_chart_block`.
_SKIPPED_SUBSECTIONS: frozenset[str] = frozenset({"time_pressure_vs_performance"})
# Mirror frontend MIN_GAMES_FOR_RELIABLE_STATS (frontend/src/lib/theme.ts) so
# the LLM sees the same bucket gating as the rendered chart.
_MIN_GAMES_FOR_RELIABLE_BUCKET: int = 10

# Metrics already emitted on a non-fractional scale (Elo points or percentage points).
# Everything else is a fraction in [0, 1] (or signed [-1, +1] for score_gap) at the
# service layer and gets multiplied by 100 here so the LLM payload matches the UI's
# 0-100 percentage scale (v6 shape). Keeping the registry/service layer fractional
# keeps the frontend gauge codegen unchanged; the scale flip lives at the formatter only.
_NON_FRACTIONAL_METRICS: frozenset[str] = frozenset(
    {"endgame_elo_gap", "avg_clock_diff_pct", "net_timeout_rate"}
)


def _scale_for_metric(metric_id: str) -> float:
    """Multiplier applied to a raw metric value before rendering in the prompt."""
    return 1.0 if metric_id in _NON_FRACTIONAL_METRICS else 100.0


# Batch 2 enrichment thresholds (v6).
_STALE_SERIES_THRESHOLD_DAYS: int = 183  # ~6 months: a combo whose last bucket is this far behind the newest bucket across any series is flagged STALE.
_TREND_MIN_POINTS: int = 4  # minimum retained buckets before we emit trend fields in [summary]
_TREND_FLAT_THRESHOLD: float = (
    3.0  # on the 0-100 scale; |latest - mean(prior 3)| below this reads as flat
)
_LOW_TIME_BUCKETS: tuple[int, ...] = (0, 1, 2)  # 0-10%, 10-20%, 20-30%
_LOW_TIME_GAP_DECISIVE: float = (
    5.0  # on 0-100 scale; user vs opp gap below this reads as near-parity
)
_DELTA_WITHIN_NOISE_SHIFT: float = (
    5.0  # |all_time → last_3mo| shift on 0-100 scale below this reads as within-noise
)
_DELTA_WITHIN_NOISE_ELO: float = (
    50.0  # |Elo delta| below this reads as within-noise for endgame_elo_gap
)
# v11: trend flat threshold for derived [summary endgame_elo] (absolute Elo
# scale). Roughly half the within-noise cap — bucket-to-bucket Elo drift below
# this reads as flat. Separate from _TREND_FLAT_THRESHOLD which is on the 0-100
# percent scale.
_TREND_FLAT_THRESHOLD_ELO: float = 25.0
_DELTA_SMALL_SAMPLE_RATIO: float = 0.20  # last_3mo_n / all_time_n below this → within-noise flag only fires with this much size mismatch

# v7 proximity hint thresholds: inline `[near edge]` marker on bullets whose
# value sits within this many points of a zone boundary. Different scales for
# percent-scale metrics (0-100) and Elo-scale metrics.
_PROXIMITY_PCT_THRESHOLD: float = 2.0
_PROXIMITY_ELO_THRESHOLD: float = 20.0

# v7 weakest-type tag: requires the lowest score_pct to be clearly separated
# from the next-lowest AND to have a meaningful sample (avoids noise calls).
_WEAKEST_TYPE_MIN_GAMES: int = 100
_WEAKEST_TYPE_MIN_SEPARATION: float = 2.0  # on 0-100 score_pct scale

# v7 recovery pattern tag: fires when Recovery sits weak across at least this
# many endgame types.
_RECOVERY_PATTERN_MIN_WEAK_TYPES: int = 4


_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _build_zone_threshold_appendix() -> str:
    """Render ZONE_REGISTRY + BUCKETED_ZONE_REGISTRY as a markdown appendix.

    Auto-generated at module load so the LLM always sees the current numeric
    bands. Kept separate from the hand-authored system-prompt markdown so
    prompt-version bumps aren't required when thresholds change (the cache
    key is findings_hash + prompt_version + model — threshold changes
    propagate via findings_hash since zones are baked into findings).
    """
    lines: list[str] = ["", "## Zone thresholds", ""]
    lines.append(
        "Numeric bands for each metric (auto-generated — do not contradict). "
        "These same bands are also inlined next to every finding bullet as "
        "`(typical LO to UP[, lower is better])`; this appendix is the full "
        "reference, the inline fragment is the per-bullet shorthand."
    )
    lines.append("")
    for metric_id, spec in ZONE_REGISTRY.items():
        scale = _scale_for_metric(metric_id)
        lo = spec.typical_lower * scale
        hi = spec.typical_upper * scale
        if spec.direction == "higher_is_better":
            lines.append(
                f"- `{metric_id}`: weak<{lo:.0f}, typical [{lo:.0f}, {hi:.0f}], strong>{hi:.0f}"
            )
        else:
            lines.append(
                f"- `{metric_id}` (lower_is_better): strong<={lo:.0f}, "
                f"typical [{lo:.0f}, {hi:.0f}], "
                f"weak>{hi:.0f}"
            )
    lines.append("")
    lines.append("Bucketed metrics (one band per MaterialBucket):")
    for metric_id, buckets in BUCKETED_ZONE_REGISTRY.items():
        scale = _scale_for_metric(metric_id)
        lines.append(f"- `{metric_id}`:")
        for bucket, spec in buckets.items():
            lo = spec.typical_lower * scale
            hi = spec.typical_upper * scale
            lines.append(
                f"  - {bucket}: weak<{lo:.0f}, typical [{lo:.0f}, {hi:.0f}], strong>{hi:.0f}"
            )
    return "\n".join(lines) + "\n"


_SYSTEM_PROMPT = (_PROMPTS_DIR / "endgame_insights.md").read_text(
    encoding="utf-8"
) + _build_zone_threshold_appendix()


# -- Custom exceptions (router maps to HTTP status per Plan 06) --


class InsightsRateLimitExceeded(Exception):
    """Rate limit exhausted AND no tier-2 fallback available. Router -> 429."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("rate_limit_exceeded")
        self.retry_after_seconds = retry_after_seconds


class InsightsProviderError(Exception):
    """pydantic-ai ModelAPIError or unknown exception. Router -> 502."""

    def __init__(self, error_marker: str) -> None:
        super().__init__(error_marker)
        self.error_marker = error_marker


class InsightsValidationFailure(Exception):
    """Structured-output validation exhausted output_retries. Router -> 502."""

    def __init__(self, error_marker: str) -> None:
        super().__init__(error_marker)
        self.error_marker = error_marker


# -- Agent singleton (CONTEXT.md D-21, D-22) --

_GOOGLE_PREFIXES = ("google-gla:", "google-vertex:")
_GEMINI3_MODEL_MARKER = "gemini-3"  # Gemini 3+ uses thinking_level; older uses thinking_budget


def _build_google_thinking_config(model_name: str) -> dict[str, object]:
    """Return the google_thinking_config dict appropriate for this model.

    Gemini 3+ models use `thinking_level: 'low' | 'high'`. Older Gemini
    models (e.g. gemini-2.5-flash) use `thinking_budget: int` where 0 disables
    thinking entirely. `include_thoughts=True` makes the provider return
    `usage_metadata.thoughts_token_count` so the service can persist it.
    """
    config: dict[str, object] = {"include_thoughts": settings.GEMINI_INCLUDE_THOUGHTS}
    if _GEMINI3_MODEL_MARKER in model_name:
        config["thinking_level"] = settings.GEMINI_THINKING_LEVEL
    else:
        config["thinking_budget"] = settings.GEMINI_THINKING_BUDGET
    return config


@functools.lru_cache(maxsize=1)
def get_insights_agent() -> Agent[None, EndgameInsightsReport]:
    """Return the singleton pydantic-ai Agent, constructing on first call.

    For Google-provider models ("google-gla:" / "google-vertex:" prefix) the
    Agent is constructed from an explicit `GoogleModel` plus a
    `GoogleModelSettings` carrying `google_thinking_config`. This lets us cap
    thinking cost (thinking_level=low on Gemini 3; thinking_budget=0 on 2.5)
    and ask the provider to surface `thoughts_token_count` so the insights
    service can persist it to `llm_logs.thinking_tokens`.

    For all other providers (Anthropic, OpenAI, test) we keep the plain
    string-form Agent constructor — no thinking control surface, and
    pydantic-ai silently ignores the Google-specific settings anyway.

    Raises:
        UserError: empty PYDANTIC_AI_MODEL_INSIGHTS or unknown model suffix.
        ValueError: unknown provider prefix (e.g., "bogus-provider:foo").

    Called from (a) main.py lifespan for startup validation (Plan 06), and
    (b) generate_insights() at request time. lru_cache ensures one Agent
    instance across the app lifetime; pydantic-ai Agents are async-safe
    (RESEARCH.md §6).
    """
    model_str = settings.PYDANTIC_AI_MODEL_INSIGHTS
    if model_str.startswith(_GOOGLE_PREFIXES):
        provider_prefix, _, model_name = model_str.partition(":")
        # provider_prefix is "google-gla" or "google-vertex" — both are valid
        # pydantic-ai GoogleProvider names (see pydantic_ai.providers.google).
        # cast to satisfy pydantic-ai's Literal param — the startswith check
        # above guarantees provider_prefix is one of the two accepted values.
        provider_literal = cast(Literal["google-gla", "google-vertex"], provider_prefix)
        google_model = GoogleModel(model_name, provider=provider_literal)
        google_settings = GoogleModelSettings(
            google_thinking_config=_build_google_thinking_config(model_name),  # ty: ignore[invalid-argument-type]
        )
        return Agent(  # ty: ignore[invalid-return-type]
            google_model,
            output_type=EndgameInsightsReport,
            system_prompt=_SYSTEM_PROMPT,
            output_retries=_OUTPUT_RETRIES,
            model_settings=google_settings,
        )
    return Agent(  # ty: ignore[invalid-return-type] — pydantic-ai Agent generic params depend on runtime model string; ty cannot infer Agent[None, EndgameInsightsReport] from a str variable
        model_str,
        output_type=EndgameInsightsReport,
        system_prompt=_SYSTEM_PROMPT,
        output_retries=_OUTPUT_RETRIES,
    )


# -- User-prompt assembly (CONTEXT.md D-28, D-29) --

# Subsections that produce Series blocks in the prompt (MUST match Plan 03's _TIMELINE_SUBSECTION_IDS).
_TIMELINE_SUBSECTION_IDS: frozenset[str] = frozenset(
    {
        "score_timeline",
        "clock_diff_timeline",
        "endgame_elo_timeline",
        "type_win_rate_timeline",
    }
)


def _format_zone_bounds(metric_id: str, dimension: dict[str, str] | None) -> str:
    """Render '(typical LO to UP[, lower is better])' for a finding bullet.

    v5 (260422-tnb pass2): inline shorthand of the zone band for each finding,
    so the LLM can judge proximity to a zone edge without consulting the
    global appendix. Bucketed metrics (conversion_win_pct / parity_score_pct /
    recovery_save_pct) dispatch via `dimension['bucket']`; all other scalar
    metrics use ZONE_REGISTRY directly. Returns '' for unknown metric_ids
    (defensive — shouldn't fire for valid findings since MetricId is enumerated).

    Phase 68 (260424-pc6): endgame_score / non_endgame_score have no
    calibrated zone band — their registry entries span [0, 1] only so
    assign_zone does not raise. Skip the bounds render for those two so
    the prompt does not show a meaningless `(typical +0 to +100)` tag.
    """
    if metric_id in ("endgame_score", "non_endgame_score"):
        return ""
    spec: ZoneSpec | None = None
    bucket = dimension.get("bucket") if dimension else None
    bucketed = cast("dict[str, dict[str, ZoneSpec]]", dict(BUCKETED_ZONE_REGISTRY))
    scalar = cast("dict[str, ZoneSpec]", dict(ZONE_REGISTRY))
    if metric_id in bucketed and bucket is not None:
        spec = bucketed[metric_id].get(bucket)
    elif metric_id in scalar:
        spec = scalar[metric_id]
    if spec is None:
        return ""
    scale = _scale_for_metric(metric_id)
    lo = spec.typical_lower * scale
    hi = spec.typical_upper * scale
    direction_note = ", lower is better" if spec.direction == "lower_is_better" else ""
    return f"(typical {lo:+.0f} to {hi:+.0f}{direction_note})"


def _format_filters_for_prompt(filters: FilterContext) -> list[str]:
    """Emit only the `## Scoping caveat` line when opponent_strength is set.

    v9: dropped the always-on `Filters:` header. The router enforces defaults
    for `recency`, `time_controls`, `platforms`, `rated_only`, and `color`
    (INS-03 / D-31), so the only filter that can be non-default is
    `opponent_strength`. When it's `any`, no filter context is relevant to
    the LLM and we emit nothing. When it's `stronger` / `similar` / `weaker`,
    we emit the scoping caveat the system prompt tells the LLM to lead the
    overview with.
    """
    if filters.opponent_strength == "any":
        return []
    return [
        f"## Scoping caveat: opponent strength filter is active "
        f"({filters.opponent_strength}) — all findings reflect performance "
        f"vs {filters.opponent_strength} opponents only; lead the overview "
        f"with this scoping."
    ]


def _format_player_profile_block(
    profile: list[PlayerProfileEntry] | None,
) -> list[str]:
    """Render the `## Player profile` block as per-combo [summary actual_elo] blocks.

    Each qualifying (platform, time_control) combo emits one [summary] block
    whose format mirrors every other windowed metric: an all_time line with
    current / min / max / mean / n / buckets / window / trend / std (plus
    `stale: ...` when the combo hasn't been played in >183 days) and a
    last_3mo line with mean / n / buckets / trend / std (or `no data` when
    the combo has no calendar-recent activity). Combos are already sorted by
    game count desc upstream in compute_player_profile.
    """
    if not profile:
        return []
    lines: list[str] = ["## Player profile"]
    # v12: emit an [anchor-combo] tag pointing at the most-played live combo
    # (no stale marker). When every combo is stale, emit `all-stale` so the
    # LLM frames the whole profile in past tense instead of fabricating a
    # current-Elo read from a 27-month-old rating.
    anchor: PlayerProfileEntry | None = next(
        (e for e in profile if e.stale_last_bucket is None),
        None,
    )
    if anchor is not None:
        lines.append(
            f"[anchor-combo platform={anchor.platform}, time_control={anchor.time_control}]"
        )
    else:
        lines.append("[anchor-combo] all-stale — narrate in past tense")
    for entry in profile:
        header = (
            f"[summary actual_elo | platform={entry.platform}, time_control={entry.time_control}]"
        )
        lines.append(header)

        at_parts = [
            f"current={entry.current_elo}",
            f"mean={entry.all_time_mean}",
            f"min={entry.min_elo}",
            f"max={entry.max_elo}",
            f"n={entry.all_time_n}",
            f"buckets={entry.all_time_buckets} (weekly)",
            f"window={entry.window_days}d",
            f"trend={entry.all_time_trend}",
            f"std={entry.all_time_std}",
        ]
        if entry.stale_last_bucket and entry.stale_months is not None:
            at_parts.append(f"stale: last {entry.stale_last_bucket} ({entry.stale_months} mo ago)")
        lines.append("  all_time: " + ", ".join(at_parts))

        if entry.last_3mo_mean is None:
            lines.append("  last_3mo: no data")
        else:
            lm_parts = [
                f"mean={entry.last_3mo_mean}",
                f"n={entry.last_3mo_n}",
                f"buckets={entry.last_3mo_buckets} (weekly)",
            ]
            if entry.last_3mo_trend is not None:
                lm_parts.append(f"trend={entry.last_3mo_trend}")
            if entry.last_3mo_std is not None:
                lm_parts.append(f"std={entry.last_3mo_std}")
            lines.append("  last_3mo: " + ", ".join(lm_parts))
    lines.append("")
    return lines


def _format_time_pressure_chart_block(findings: EndgameTabFindings) -> list[str]:
    """Render the 10-bucket time_pressure_vs_performance chart as a table.

    Emits one `## Chart` header followed by a markdown table with one row per
    bucket (0-10% ... 90-100%), each showing user Score %, user game count,
    opponent Score %, opponent game count. Buckets where BOTH sides have
    fewer than _MIN_GAMES_FOR_RELIABLE_BUCKET games are dropped (mirrors
    the frontend's visual suppression). Returns [] if the chart is missing
    or empty. Rendered separately from SubsectionFinding rows because the
    20 data points do not fit the single-value finding shape.
    """
    chart = findings.time_pressure_chart
    if chart is None or chart.total_endgame_games == 0:
        return []

    user_by_idx = {p.bucket_index: p for p in chart.user_series}
    opp_by_idx = {p.bucket_index: p for p in chart.opp_series}

    rows: list[str] = []
    for idx in range(10):
        u = user_by_idx.get(idx)
        o = opp_by_idx.get(idx)
        u_n = u.game_count if u else 0
        o_n = o.game_count if o else 0
        if u_n < _MIN_GAMES_FOR_RELIABLE_BUCKET and o_n < _MIN_GAMES_FOR_RELIABLE_BUCKET:
            continue
        label = u.bucket_label if u else (o.bucket_label if o else f"{idx * 10}-{(idx + 1) * 10}%")
        u_score = (
            f"{u.score * 100:.0f}"
            if u is not None and u.score is not None and u_n >= _MIN_GAMES_FOR_RELIABLE_BUCKET
            else "—"
        )
        o_score = (
            f"{o.score * 100:.0f}"
            if o is not None and o.score is not None and o_n >= _MIN_GAMES_FOR_RELIABLE_BUCKET
            else "—"
        )
        rows.append(f"| {label:<7} | {u_score:<10} | {u_n:<6} | {o_score:<10} | {o_n:<6} |")

    if not rows:
        return []

    lines: list[str] = [
        "### Chart: time_pressure_vs_performance (all_time)",
        f"Total endgame games: {chart.total_endgame_games}. "
        "Rows show Score % conditional on time remaining at endgame entry, "
        "for the user and the opponent separately (each side binned by their own clock). "
        "user_score / opp_score are whole-number Score % values (wins=100, draws=50).",
    ]
    low_time_line = _low_time_gap_line(chart)
    if low_time_line:
        lines.append(low_time_line)
    lines.append("| time_left | user_score | user_n | opp_score | opp_n |")
    lines.append("| --------- | ---------- | ------ | ---------- | ------ |")
    lines.extend(rows)
    lines.append("")
    return lines


def _format_overall_wdl_chart_block(findings: EndgameTabFindings) -> list[str]:
    """Render the endgame-vs-non-endgame WDL + Score % comparison as a table.

    Emits a `## Chart: overall_wdl` header followed by a 2-row markdown table
    (endgame, non_endgame) with win_pct / draw_pct / loss_pct / score_pct
    columns. score_pct = (wins + 0.5*draws) / total (matches the UI's
    Endgame Performance section). Rows with fewer than
    _MIN_GAMES_FOR_RELIABLE_BUCKET games are skipped. Returns [] when the
    performance payload is absent or both rows are empty.
    """
    perf = findings.overall_performance
    if perf is None:
        return []

    rows: list[str] = []
    for label, summary in (("endgame", perf.endgame_wdl), ("non_endgame", perf.non_endgame_wdl)):
        total = summary.total
        if total < _MIN_GAMES_FOR_RELIABLE_BUCKET:
            continue
        score_pct = (summary.wins + 0.5 * summary.draws) / total * 100.0
        rows.append(
            f"| {label:<11} | {total:<5} | {summary.win_pct:.0f}     | {summary.draw_pct:.0f}      | "
            f"{summary.loss_pct:.0f}      | {score_pct:.0f}       |"
        )

    if not rows:
        return []

    lines: list[str] = [
        "### Chart: overall_wdl (all_time)",
        "Two-row WDL comparison for games that reached an endgame phase vs games that did not. "
        "All columns are whole-number percentages; score_pct uses wins=100, draws=50, losses=0.",
        "| series      | games | win_pct | draw_pct | loss_pct | score_pct |",
        "| ----------- | ----- | ------- | -------- | -------- | --------- |",
    ]
    lines.extend(rows)
    lines.append("")
    return lines


def _format_type_wdl_chart_block(findings: EndgameTabFindings) -> list[str]:
    """Render per-endgame-type WDL + Score % as a table.

    Emits `## Chart: results_by_endgame_type_wdl` followed by one row per
    endgame category (rook, minor_piece, pawn, queen, mixed) sorted by total
    descending (matches `EndgameStatsResponse` D-05). score_pct = (wins +
    0.5*draws) / total. Opponent Score % is the algebraic complement
    (1 - score_pct) for these samples since both sides played the same games,
    documented in the caption; not emitted as a separate column. Rows with
    fewer than _MIN_GAMES_FOR_RELIABLE_BUCKET games are skipped.
    """
    categories = findings.type_categories
    if not categories:
        return []

    # Drop pawnless: hidden in the UI, so the LLM should not narrate it either.
    sorted_cats = sorted(
        (c for c in categories if c.endgame_class != "pawnless"),
        key=lambda c: c.total,
        reverse=True,
    )

    rows: list[str] = []
    weakest_tag = _weakest_type_tag(sorted_cats)

    for cat in sorted_cats:
        if cat.total < _MIN_GAMES_FOR_RELIABLE_BUCKET:
            continue
        score_pct = (cat.wins + 0.5 * cat.draws) / cat.total * 100.0
        rows.append(
            f"| {cat.endgame_class:<13} | {cat.total:<5} | {cat.win_pct:.0f}     | "
            f"{cat.draw_pct:.0f}      | {cat.loss_pct:.0f}      | {score_pct:.0f}       |"
        )

    if not rows:
        return []

    lines: list[str] = [
        "### Chart: results_by_endgame_type_wdl (all_time)",
        "Per-endgame-type W/D/L and Score % for the user. All columns are whole-number "
        "percentages. opp_score_pct = 100 - score_pct (both sides played the same "
        "games), so a score_pct above 50 means the user outscores their opponents in that type.",
    ]
    if weakest_tag:
        lines.append(weakest_tag)
    lines.append("| endgame_class | games | win_pct | draw_pct | loss_pct | score_pct |")
    lines.append("| ------------- | ----- | ------- | -------- | -------- | --------- |")
    lines.extend(rows)
    lines.append("")
    return lines


# -- Batch 2 enrichments (v6): mechanical signals precomputed for the LLM --


def _newest_bucket_date(findings: list[SubsectionFinding]) -> datetime.date | None:
    """Return the most recent bucket date across every series in the payload."""
    newest: datetime.date | None = None
    for f in findings:
        if f.series is None:
            continue
        for pt in f.series:
            try:
                d = datetime.date.fromisoformat(pt.bucket_start)
            except ValueError:
                continue
            if newest is None or d > newest:
                newest = d
    return newest


def _all_time_window_bounds(
    findings: list[SubsectionFinding],
) -> tuple[datetime.date, datetime.date] | None:
    """Return (oldest, newest) bucket dates for all_time series after the C6 cap.

    Walks every all_time series, applies the same MIN_BUCKET_N filter and
    _ALL_TIME_MAX_POINTS tail-cap that `_retained_series_for_summary` applies,
    and tracks the min/max bucket dates across the retained set. Used by the
    `## Payload summary` block to spell out the effective time window the LLM
    is reading.
    """
    oldest: datetime.date | None = None
    newest: datetime.date | None = None
    for f in findings:
        if f.series is None or f.window != "all_time":
            continue
        retained = [pt for pt in f.series if pt.n >= MIN_BUCKET_N][-_ALL_TIME_MAX_POINTS:]
        for pt in retained:
            try:
                d = datetime.date.fromisoformat(pt.bucket_start)
            except ValueError:
                continue
            if oldest is None or d < oldest:
                oldest = d
            if newest is None or d > newest:
                newest = d
    if oldest is None or newest is None:
        return None
    return oldest, newest


def _stale_marker(series: list[TimePoint] | None, newest_payload_date: datetime.date | None) -> str:
    """Return 'stale: last YYYY-MM (N mo ago)' or '' if the series is live.

    Consumed inline in [summary] window lines — a short, bracket-compatible
    form. The threshold (_STALE_SERIES_THRESHOLD_DAYS) is unchanged; only the
    rendered string format changed alongside the v10 tag unification.
    """
    if not series or newest_payload_date is None:
        return ""
    try:
        last_date = datetime.date.fromisoformat(series[-1].bucket_start)
    except ValueError:
        return ""
    delta_days = (newest_payload_date - last_date).days
    if delta_days < _STALE_SERIES_THRESHOLD_DAYS:
        return ""
    months = delta_days // 30
    return f"stale: last {last_date.strftime('%Y-%m')} ({months} mo ago)"


def _trend_info(
    metric_id: str, points: list[TimePoint]
) -> tuple[str, float, float, int, bool] | None:
    """Return (direction, mean_scaled, std_scaled, n_total, within_noise) or None.

    Uses the full retained series (post A4/C2/C6 filtering). direction is
    computed over the last 4 buckets (latest vs mean of prior 3) — flat when
    |latest - prior-mean| < _TREND_FLAT_THRESHOLD, otherwise improving /
    regressing. std is the stddev across all retained points (0.0 when fewer
    than 2 points). within_noise mirrors the v7 rule: the last-4 shift is
    below the metric's noise cap even if direction is not flat. Returns None
    when fewer than _TREND_MIN_POINTS buckets remain — caller renders no
    trend field.
    """
    if len(points) < _TREND_MIN_POINTS:
        return None
    scale = _scale_for_metric(metric_id)
    values = [pt.value * scale for pt in points]
    latest = values[-1]
    prior_values = values[-4:-1]
    prior_mean = sum(prior_values) / len(prior_values)
    diff = latest - prior_mean
    if abs(diff) < _TREND_FLAT_THRESHOLD:
        direction = "flat"
    elif diff > 0:
        direction = "improving"
    else:
        direction = "regressing"
    series_mean = sum(values) / len(values)
    series_std = (
        (sum((v - series_mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5
        if len(values) >= 2
        else 0.0
    )
    n_total = sum(pt.n for pt in points)
    noise_cap = (
        _DELTA_WITHIN_NOISE_ELO if metric_id == "endgame_elo_gap" else _DELTA_WITHIN_NOISE_SHIFT
    )
    within_noise = direction != "flat" and abs(diff) < noise_cap
    return direction, series_mean, series_std, n_total, within_noise


def _proximity_hint(metric_id: str, value_scaled: float, dimension: dict[str, str] | None) -> str:
    """Return ' [near edge]' when the value sits within a proximity threshold of a zone boundary.

    Percent-scale metrics use _PROXIMITY_PCT_THRESHOLD; endgame_elo_gap uses
    _PROXIMITY_ELO_THRESHOLD. Returns '' for unknown metrics or when the value
    is comfortably inside one zone.
    """
    spec: ZoneSpec | None = None
    bucket = dimension.get("bucket") if dimension else None
    bucketed = cast("dict[str, dict[str, ZoneSpec]]", dict(BUCKETED_ZONE_REGISTRY))
    scalar = cast("dict[str, ZoneSpec]", dict(ZONE_REGISTRY))
    if metric_id in bucketed and bucket is not None:
        spec = bucketed[metric_id].get(bucket)
    elif metric_id in scalar:
        spec = scalar[metric_id]
    if spec is None:
        return ""
    scale = _scale_for_metric(metric_id)
    lo = spec.typical_lower * scale
    hi = spec.typical_upper * scale
    threshold = (
        _PROXIMITY_ELO_THRESHOLD if metric_id == "endgame_elo_gap" else _PROXIMITY_PCT_THRESHOLD
    )
    if abs(value_scaled - lo) <= threshold or abs(value_scaled - hi) <= threshold:
        return " [near edge]"
    return ""


def _weakest_type_tag(sorted_cats: list[object]) -> str:
    """Emit a weakest-type tag across the per-type WDL chart.

    Three outcomes across the eligible types (>= _WEAKEST_TYPE_MIN_GAMES):

    1. Clear single winner — the lowest score_pct is separated from #2 by
       >= _WEAKEST_TYPE_MIN_SEPARATION. Emits `[weakest-type] <class> ...`.
    2. Tied-weakest pair — top 2 are within the separation threshold BUT
       the #3 type (when present) is separated from #2 by >= the threshold,
       so the two lowest stand out together. Emits
       `[weakest-types-tied] <a>, <b> score_pct=X, Y — next=<c> score_pct=Z`
       (v12). Releases pawn-ending recommendations the same way a clear
       `[weakest-type] pawn` would.
    3. No clear bottom — no tag emitted.
    """
    # EndgameCategoryStats is imported lazily to keep the helper cheap when no
    # type chart is emitted. Using `object` in the signature and casting here
    # keeps ty happy without a top-level import.
    from app.schemas.endgames import EndgameCategoryStats

    eligible: list[tuple[float, str]] = []
    for cat in sorted_cats:
        c = cast(EndgameCategoryStats, cat)
        if c.total < _WEAKEST_TYPE_MIN_GAMES:
            continue
        score_pct = (c.wins + 0.5 * c.draws) / c.total * 100.0
        eligible.append((score_pct, c.endgame_class))
    if len(eligible) < 2:
        return ""
    eligible.sort(key=lambda t: t[0])
    weakest_score, weakest_class = eligible[0]
    next_score, next_class = eligible[1]
    if next_score - weakest_score >= _WEAKEST_TYPE_MIN_SEPARATION:
        return (
            f"[weakest-type] {weakest_class} score_pct={weakest_score:.0f}, "
            f"next={next_class} score_pct={next_score:.0f}"
        )
    # Tied-weakest: require a #3 type that is clearly separated from #2,
    # else the whole field is bunched and no "weakest" story is defensible.
    if len(eligible) < 3:
        return ""
    third_score, third_class = eligible[2]
    if third_score - next_score < _WEAKEST_TYPE_MIN_SEPARATION:
        return ""
    return (
        f"[weakest-types-tied] {weakest_class}, {next_class} "
        f"score_pct={weakest_score:.0f}, {next_score:.0f} — "
        f"next={third_class} score_pct={third_score:.0f}"
    )


def _recovery_pattern_tag(findings: list[SubsectionFinding]) -> str:
    """Emit '# recovery pattern: ...' when Recovery is weak across many endgame types.

    Scans all_time `conversion_recovery_by_type` findings for
    `recovery_save_pct` with zone=weak. When ≥ _RECOVERY_PATTERN_MIN_WEAK_TYPES
    types qualify, emits a hint so the LLM frames Recovery as a consistent
    pattern rather than a per-type crisis in each bullet.
    """
    weak_types: list[str] = []
    for f in findings:
        if f.subsection_id != "conversion_recovery_by_type" or f.window != "all_time":
            continue
        if f.metric != "recovery_save_pct" or f.dimension is None:
            continue
        klass = f.dimension.get("endgame_class")
        if klass is None or klass == "pawnless":
            continue
        if f.zone == "weak":
            weak_types.append(klass)
    if len(weak_types) < _RECOVERY_PATTERN_MIN_WEAK_TYPES:
        return ""
    return (
        f"[recovery-pattern] weak across {len(weak_types)} of 5 types — "
        "consistent defensive pattern, frame as one story not per-type crisis"
    )


def _asymmetry_lines(findings: list[SubsectionFinding]) -> list[str]:
    """Detect per-type Conversion/Recovery zone splits (one strong + one weak).

    Scans all_time `conversion_recovery_by_type` findings grouped by endgame
    class. When the two metrics sit in opposing zones, emits a comment the LLM
    should lead with for that type — the "you close winning pawn endgames but
    bleed losing ones" story is easy to miss if both bullets are narrated flat.
    Pawnless is skipped to stay consistent with the hidden-UI filter.
    """
    conv: dict[str, SubsectionFinding] = {}
    rec: dict[str, SubsectionFinding] = {}
    for f in findings:
        if f.subsection_id != "conversion_recovery_by_type" or f.window != "all_time":
            continue
        if f.dimension is None:
            continue
        klass = f.dimension.get("endgame_class")
        if klass is None or klass == "pawnless":
            continue
        if f.metric == "conversion_win_pct":
            conv[klass] = f
        elif f.metric == "recovery_save_pct":
            rec[klass] = f
    lines: list[str] = []
    for klass in sorted(conv):
        c = conv.get(klass)
        r = rec.get(klass)
        if c is None or r is None:
            continue
        if {c.zone, r.zone} != {"strong", "weak"}:
            continue
        c_val = c.value * 100.0
        r_val = r.value * 100.0
        # v11: pawn endgames amplify material imbalance by their nature (K+P vs K
        # is mechanical to convert, K vs K+P is often forced loss). Until we have
        # per-type cohort bands, a strong-Conversion / weak-Recovery split for
        # pawn endgames should be narrated neutrally, not as a defensive weakness.
        if klass == "pawn":
            story = (
                "expected asymmetry — pawn endgames amplify material imbalance "
                "(terminal phase); narrate neutrally, do not frame as defensive weakness"
            )
        elif c.zone == "strong":
            story = "closes winning endgames but bleeds losing ones"
        else:
            story = "defends losing endgames but mishandles winning ones"
        lines.append(
            f"[asymmetry type={klass}] conversion={c_val:.0f} {c.zone}, "
            f"recovery={r_val:.0f} {r.zone} — {story}"
        )
    return lines


def _low_time_gap_line(chart: TimePressureChartResponse | None) -> str:
    """Weighted user-vs-opp Score % over the low-time buckets (0-30%)."""
    if chart is None:
        return ""
    user_by_idx = {p.bucket_index: p for p in chart.user_series}
    opp_by_idx = {p.bucket_index: p for p in chart.opp_series}
    user_num = user_den = opp_num = opp_den = 0.0
    for idx in _LOW_TIME_BUCKETS:
        u = user_by_idx.get(idx)
        o = opp_by_idx.get(idx)
        if u is not None and u.score is not None and u.game_count >= _MIN_GAMES_FOR_RELIABLE_BUCKET:
            user_num += u.score * u.game_count
            user_den += u.game_count
        if o is not None and o.score is not None and o.game_count >= _MIN_GAMES_FOR_RELIABLE_BUCKET:
            opp_num += o.score * o.game_count
            opp_den += o.game_count
    if user_den == 0 or opp_den == 0:
        return ""
    user_avg = user_num / user_den * 100.0
    opp_avg = opp_num / opp_den * 100.0
    gap = user_avg - opp_avg
    if gap < -_LOW_TIME_GAP_DECISIVE:
        verdict = "user cracks under time pressure"
    elif gap > _LOW_TIME_GAP_DECISIVE:
        verdict = "user cooler under time pressure"
    else:
        verdict = "near parity"
    return (
        f"[low-time-gap] 0-30% buckets, weighted: user={user_avg:.0f}, opp={opp_avg:.0f}, "
        f"gap={gap:+.0f} — {verdict}"
    )


def _dim_key_for_finding(f: SubsectionFinding) -> str:
    """Return the canonical dim-key string used to group findings across windows."""
    if f.dimension is None:
        return ""
    return ", ".join(f"{k}={v}" for k, v in sorted(f.dimension.items()))


def _within_noise_shift(
    metric: str,
    all_time: SubsectionFinding,
    last_3mo: SubsectionFinding,
    shift: float,
) -> bool:
    """Shift is within-noise when it's below the metric cap AND the last_3mo window is much smaller."""
    noise_cap = (
        _DELTA_WITHIN_NOISE_ELO if metric == "endgame_elo_gap" else _DELTA_WITHIN_NOISE_SHIFT
    )
    sample_mismatch = (
        all_time.sample_size > 0
        and (last_3mo.sample_size / all_time.sample_size) < _DELTA_SMALL_SAMPLE_RATIO
    )
    return abs(shift) < noise_cap and sample_mismatch


def _series_granularity(finding: SubsectionFinding) -> str:
    """Weekly for last_3mo; monthly for all_time.

    Exceptions:
    - type_win_rate_timeline: always monthly (5-way split makes weekly noise).
    - score_timeline (Phase 68): always weekly (ISO-week is the natural grain
      of the underlying `_compute_score_gap_timeline`; the two-line chart
      reads weekly points directly and the insights series is built without
      monthly resampling — see `_findings_score_timeline`).
    """
    if finding.subsection_id == "type_win_rate_timeline":
        return "monthly"
    if finding.subsection_id == "score_timeline":
        return "weekly"
    return "weekly" if finding.window == "last_3mo" else "monthly"


def _summary_window_line(
    *,
    window: str,
    finding: SubsectionFinding,
    series_points: list[TimePoint] | None,
    stale_suffix: str,
) -> str:
    """Render one `  <window>: ...` line inside a [summary] block.

    Pulls mean / zone / quality from the scalar finding, and (when series
    points are provided and qualifying) buckets / granularity / trend / std
    from the series. Appends `stale: ...` and `[near edge]` suffixes when
    applicable. All numbers on the UI 0-100 scale (or Elo points).
    """
    scale = _scale_for_metric(finding.metric)
    value_scaled = finding.value * scale
    bounds = _format_zone_bounds(finding.metric, finding.dimension)
    zone_part = f"zone={finding.zone}"
    if bounds:
        zone_part += f" {bounds}"

    parts: list[str] = [f"mean={value_scaled:+.0f}", f"n={finding.sample_size}"]
    if series_points and len(series_points) >= _TREND_MIN_POINTS:
        info = _trend_info(finding.metric, series_points)
        if info is not None:
            direction, _series_mean, series_std, _n_total, within_noise = info
            granularity = _series_granularity(finding)
            parts.append(f"buckets={len(series_points)} ({granularity})")
            parts.append(zone_part)
            parts.append(f"quality={finding.sample_quality}")
            parts.append(f"trend={direction}")
            parts.append(f"std={series_std:.0f}")
            if within_noise:
                parts.append("within-noise")
            if stale_suffix:
                parts.append(stale_suffix)
            near = _proximity_hint(finding.metric, value_scaled, finding.dimension).strip()
            suffix = f" {near}" if near else ""
            return f"  {window}: " + ", ".join(parts) + suffix

    # Scalar (or too-short series) fallback.
    parts.append(zone_part)
    parts.append(f"quality={finding.sample_quality}")
    if stale_suffix:
        parts.append(stale_suffix)
    near = _proximity_hint(finding.metric, value_scaled, finding.dimension).strip()
    suffix = f" {near}" if near else ""
    return f"  {window}: " + ", ".join(parts) + suffix


def _summary_shift_line(
    metric: str,
    all_time: SubsectionFinding,
    last_3mo: SubsectionFinding,
) -> str:
    """Render `  shift=<Z>[, within-noise]` closing a [summary] block with paired windows."""
    scale = _scale_for_metric(metric)
    shift = (last_3mo.value - all_time.value) * scale
    line = f"  shift={shift:+.0f}"
    if _within_noise_shift(metric, all_time, last_3mo, shift):
        line += ", within-noise"
    return line


def _endgame_elo_per_bucket(points: list[TimePoint] | None) -> list[tuple[float, int]]:
    """Return [(endgame_elo_value, n), ...] derived from endgame_elo_gap series points.

    endgame_elo per bucket = actual_elo + gap. The gap metric is non-fractional
    (scale=1.0), so `pt.value` is already in Elo units. Points missing
    `actual_elo` are skipped — the gap series carries it for endgame_elo_gap
    only (see _render_series_block).
    """
    out: list[tuple[float, int]] = []
    if not points:
        return out
    for pt in points:
        if pt.actual_elo is None:
            continue
        out.append((pt.actual_elo + pt.value, pt.n))
    return out


def _render_endgame_elo_summary_block(
    *,
    dim_key: str,
    all_time_finding: SubsectionFinding | None,
    last_3mo_finding: SubsectionFinding | None,
    all_time_series: list[TimePoint] | None,
    last_3mo_series: list[TimePoint] | None,
    stale_markers: dict[int, str],
) -> list[str]:
    """Emit `[summary endgame_elo | dim]` derived from the endgame_elo_gap series.

    v11: the chart's headline value is Endgame ELO (absolute Elo, skill-adjusted)
    not the gap. We derive a per-window aggregate from the same retained series
    points used by the gap summary so the LLM can cite the chart number directly
    without doing arithmetic. No zone / quality fields — endgame_elo has no
    calibrated band; the paired `[summary endgame_elo_gap]` block (rendered
    immediately after this one) carries the zone interpretation.
    """

    def window_line(
        window_label: str, finding: SubsectionFinding | None, series: list[TimePoint] | None
    ) -> tuple[str | None, float | None]:
        """Return (rendered_line, weighted_mean) or (None, None) if no usable data."""
        values = _endgame_elo_per_bucket(series)
        if not values:
            return None, None
        total_n = sum(n for _, n in values)
        if total_n == 0:
            return None, None
        weighted_mean = sum(v * n for v, n in values) / total_n
        elos = [v for v, _ in values]
        elo_mean = sum(elos) / len(elos)
        std = (
            (sum((v - elo_mean) ** 2 for v in elos) / (len(elos) - 1)) ** 0.5
            if len(elos) >= 2
            else 0.0
        )
        granularity = "weekly" if window_label == "last_3mo" else "monthly"
        parts: list[str] = [
            f"mean={weighted_mean:+.0f} Elo",
            f"n={finding.sample_size if finding is not None else total_n}",
            f"buckets={len(values)} ({granularity})",
        ]
        within_noise = False
        if len(elos) >= _TREND_MIN_POINTS:
            latest = elos[-1]
            prior_mean = sum(elos[-4:-1]) / 3
            diff = latest - prior_mean
            if abs(diff) < _TREND_FLAT_THRESHOLD_ELO:
                direction = "flat"
            elif diff > 0:
                direction = "improving"
            else:
                direction = "regressing"
            parts.append(f"trend={direction}")
            within_noise = direction != "flat" and abs(diff) < _DELTA_WITHIN_NOISE_ELO
        parts.append(f"std={std:.0f}")
        if within_noise:
            parts.append("within-noise")
        if finding is not None:
            stale = stale_markers.get(id(finding), "")
            if stale:
                parts.append(stale)
        return f"  {window_label}: " + ", ".join(parts), weighted_mean

    header = "[summary endgame_elo"
    if dim_key:
        header += f" | {dim_key}"
    header += "]"

    at_line, at_mean = window_line("all_time", all_time_finding, all_time_series)
    lm_line, lm_mean = window_line("last_3mo", last_3mo_finding, last_3mo_series)

    if at_line is None and lm_line is None:
        return []

    lines: list[str] = [header]
    if at_line is not None:
        lines.append(at_line)
    if lm_line is not None:
        lines.append(lm_line)
    elif at_line is not None:
        lines.append("  last_3mo: no data")

    if (
        at_line is not None
        and lm_line is not None
        and at_mean is not None
        and lm_mean is not None
        and all_time_finding is not None
        and last_3mo_finding is not None
    ):
        shift = lm_mean - at_mean
        sample_mismatch = (
            all_time_finding.sample_size > 0
            and (last_3mo_finding.sample_size / all_time_finding.sample_size)
            < _DELTA_SMALL_SAMPLE_RATIO
        )
        shift_line = f"  shift={shift:+.0f} Elo"
        if abs(shift) < _DELTA_WITHIN_NOISE_ELO and sample_mismatch:
            shift_line += ", within-noise"
        lines.append(shift_line)

    return lines


def _render_summary_block(
    metric: str,
    dim_key: str,
    *,
    all_time: SubsectionFinding | None,
    last_3mo: SubsectionFinding | None,
    all_time_series: list[TimePoint] | None,
    last_3mo_series: list[TimePoint] | None,
    stale_markers: dict[int, str],
) -> list[str]:
    """Emit `[summary <metric>[ | dim]]` with all_time / last_3mo / shift lines.

    The block's format is intentionally consistent across scalar, timeseries,
    and per-dim metrics so the system prompt only needs to document one
    shape. `no data` stands in on the last_3mo line when only the all_time
    window has a finding (keeps the paired-line visual consistent).
    """
    header = f"[summary {metric}"
    if dim_key:
        header += f" | {dim_key}"
    header += "]"
    lines: list[str] = [header]

    if all_time is not None:
        stale = stale_markers.get(id(all_time), "")
        lines.append(
            _summary_window_line(
                window="all_time",
                finding=all_time,
                series_points=all_time_series,
                stale_suffix=stale,
            )
        )
    if last_3mo is not None:
        stale = stale_markers.get(id(last_3mo), "")
        lines.append(
            _summary_window_line(
                window="last_3mo",
                finding=last_3mo,
                series_points=last_3mo_series,
                stale_suffix=stale,
            )
        )
    elif all_time is not None:
        lines.append("  last_3mo: no data")

    if all_time is not None and last_3mo is not None:
        lines.append(_summary_shift_line(metric, all_time, last_3mo))
    return lines


def _count_activity_gaps(findings: list[SubsectionFinding]) -> int:
    """Count >90-day gaps between consecutive retained bucket pairs across all series."""
    count = 0
    for f in findings:
        if f.series is None:
            continue
        prev: datetime.date | None = None
        for pt in f.series:
            if pt.n < MIN_BUCKET_N:
                continue
            try:
                d = datetime.date.fromisoformat(pt.bucket_start)
            except ValueError:
                continue
            if prev is not None and (d - prev).days > _ACTIVITY_GAP_DAYS:
                count += 1
            prev = d
    return count


def _payload_summary_lines(
    findings: EndgameTabFindings,
    *,
    newest_date: datetime.date | None,
    stale_series_count: int,
    activity_gap_count: int,
    all_time_window: tuple[datetime.date, datetime.date] | None,
) -> list[str]:
    """Compact summary prepended to the prompt so macro context is always visible.

    v9: dropped the `Conversion/Recovery asymmetries detected: N` count — the
    per-type `# asymmetry (<type>): ...` tags surfaced inside the
    `conversion_recovery_by_type` subsection carry the actionable detail.
    v11: added `All-time series window: ... → ...` line so the LLM cannot
    overclaim a long-term trajectory beyond the actual cap.
    """
    lines: list[str] = ["## Payload summary"]
    if findings.overall_performance is not None:
        total_games = (
            findings.overall_performance.endgame_wdl.total
            + findings.overall_performance.non_endgame_wdl.total
        )
        if total_games > 0:
            lines.append(f"- Total games in scope: {total_games}")
    if newest_date is not None:
        lines.append(f"- Newest bucket across all series: {newest_date.isoformat()}")
    if all_time_window is not None:
        oldest, newest = all_time_window
        lines.append(
            f"- All-time series window: {oldest.strftime('%Y-%m')} → "
            f"{newest.strftime('%Y-%m')} (capped at {_ALL_TIME_MAX_POINTS} "
            "monthly buckets per series)"
        )
    if activity_gap_count > 0:
        lines.append(
            f"- Activity gaps (>{_ACTIVITY_GAP_DAYS}d) across all series: {activity_gap_count}"
        )
    if stale_series_count > 0:
        lines.append(
            f"- Stale series (>{_STALE_SERIES_THRESHOLD_DAYS}d behind newest): {stale_series_count}"
        )
    if len(lines) == 1:  # only the header line
        return []
    lines.append("")
    return lines


# v8: UI-ordered section layout. Each entry is (section_id, ordered blocks
# in UI top-to-bottom order). A block is ("subsection", id) or ("chart", id).
# The `section_id` strings match the `SectionId` enum on EndgameInsightsReport
# so the LLM can treat each `## Section:` header as the cue for which
# SectionInsight it is writing.
_SECTION_LAYOUT: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "overall",
        [
            ("chart", "overall_wdl"),
            # Scalar `overall` subsection emits only when the overall_wdl chart
            # does NOT (C4 gate below suppresses it when both exist).
            ("subsection", "overall"),
            ("subsection", "score_timeline"),
        ],
    ),
    (
        "metrics_elo",
        [
            ("subsection", "endgame_metrics"),
            ("subsection", "endgame_elo_timeline"),
        ],
    ),
    (
        "time_pressure",
        [
            ("subsection", "time_pressure_at_entry"),
            ("subsection", "clock_diff_timeline"),
            ("chart", "time_pressure_vs_performance"),
        ],
    ),
    (
        "type_breakdown",
        [
            ("chart", "results_by_endgame_type_wdl"),
            ("subsection", "conversion_recovery_by_type"),
            ("subsection", "type_win_rate_timeline"),
            ("subsection", "results_by_endgame_type"),
        ],
    ),
]


def _retained_series_for_summary(
    finding: SubsectionFinding,
    *,
    last_3mo_pairs: set[tuple[str, str]],
    all_time_cutoff: str,
) -> list[TimePoint] | None:
    """Return the retained series points for a timeline finding, or None.

    Applies the same A4/C2/C6 filter chain used for series emission, so the
    [summary] block's buckets / trend / std all describe the exact window
    the LLM sees in the [series ...] block below it. Returns None for
    non-timeline subsections (scalar findings carry no series semantics).
    """
    if finding.series is None or finding.subsection_id not in _TIMELINE_SUBSECTION_IDS:
        return None
    points = [pt for pt in finding.series if pt.n >= MIN_BUCKET_N]
    if (
        finding.window == "all_time"
        and (
            finding.metric,
            finding.subsection_id,
        )
        in last_3mo_pairs
    ):
        points = [pt for pt in points if pt.bucket_start < all_time_cutoff]
    if finding.window == "all_time":
        points = points[-_ALL_TIME_MAX_POINTS:]
    return points


def _render_series_block(finding: SubsectionFinding, points: list[TimePoint]) -> list[str]:
    """Render `[series metric, window, granularity[, dim_key]]` + raw points + `[activity-gap]` markers.

    Phase 68: when a finding carries a dimension (e.g. `{"part": "endgame"}`
    or `{"platform": "chess.com", "time_control": "blitz"}`), the series
    header gets a trailing dim_key suffix so two findings that share the
    same (metric, window, granularity) but different dims each get their
    own uniquely-labelled series block. This matches the grouping the
    `_dim_key_for_finding` helper already produces for summary blocks.

    Phase 68 (260424-pc6, UAT pass): when every point carries the same
    `n` — as happens for trailing-window series (e.g. score_timeline's
    rolling 100-game window) — the repetitive `(n=<N>)` suffix is noise.
    Emit a single `[n=<N> for every point]` disclosure line right after
    the series header and omit the suffix from each bucket line. The
    endgame_elo_gap variant (which also carries per-point `elo=`) always
    keeps the per-point `(n=<N>)` suffix because its `elo=` field can
    still vary per bucket — the disclosure shortcut would lose signal.
    """
    granularity = _series_granularity(finding)
    header = f"[series {finding.metric}, {finding.window}, {granularity}"
    dim_key = _dim_key_for_finding(finding)
    if dim_key:
        header += f", {dim_key}"
    header += "]"
    lines = [header]
    series_scale = _scale_for_metric(finding.metric)
    emit_elo = finding.metric == "endgame_elo_gap"
    # Constant-n suppression (260424-pc6 C): only applies when every point
    # shares the same `n` AND this is NOT the endgame_elo_gap variant (whose
    # per-point `elo=` field is the reason the full per-point line exists).
    ns = [pt.n for pt in points]
    n_is_constant = bool(ns) and not emit_elo and len(set(ns)) == 1
    if n_is_constant:
        lines.append(f"[n={ns[0]} for every point]")
    prev_date: datetime.date | None = None
    prev_bucket_start: str | None = None
    for pt in points:
        try:
            curr_date = datetime.date.fromisoformat(pt.bucket_start)
        except ValueError:
            continue
        if (
            prev_date is not None
            and prev_bucket_start is not None
            and (curr_date - prev_date).days > _ACTIVITY_GAP_DAYS
        ):
            lines.append(f"[activity-gap] {prev_bucket_start} → {pt.bucket_start}")
        pt_value = pt.value * series_scale
        if emit_elo and pt.actual_elo is not None:
            lines.append(f"{pt.bucket_start}: gap={pt_value:+.0f}, elo={pt.actual_elo} (n={pt.n})")
        elif n_is_constant:
            lines.append(f"{pt.bucket_start}: {pt_value:+.0f}")
        else:
            lines.append(f"{pt.bucket_start}: {pt_value:+.0f} (n={pt.n})")
        prev_date = curr_date
        prev_bucket_start = pt.bucket_start
    return lines


def _render_subsection_block(
    *,
    subsection_id: str,
    members: list[SubsectionFinding],
    stale_markers: dict[int, str],
    live_series_metrics: set[tuple[str, str]],
    last_3mo_pairs: set[tuple[str, str]],
    all_time_series_pairs: set[tuple[str, str]],
    all_time_cutoff: str,
    asymmetry_lines: list[str],
    recovery_pattern: str,
) -> list[str]:
    """Render one subsection: header + inline tags + [summary] blocks + [series] raw data.

    Findings are grouped by (metric, dim_key) so each pair produces exactly
    one [summary] block carrying both windows plus optional shift. Timeline
    findings also emit a `[series ...]` raw-data block below the summary.
    Phase 68 (B4 option c): `score_timeline` emits TWO findings per window
    (one per `part`) so the subsection naturally renders two summary blocks
    + two series blocks via the existing per-dimension grouping — no special
    suppression carve-out.
    """
    lines: list[str] = []
    header = f"### Subsection: {subsection_id}"
    parent = next(
        (m.parent_subsection_id for m in members if m.parent_subsection_id),
        None,
    )
    if parent:
        header += f" (parent: {parent})"
    lines.append(header)

    if subsection_id == "conversion_recovery_by_type":
        if recovery_pattern:
            lines.append(recovery_pattern)
        if asymmetry_lines:
            lines.extend(asymmetry_lines)

    # Group findings by (metric, dim_key) → {window: finding}. Preserves the
    # order in which metric/dim pairs first appear so the LLM sees them in
    # the original payload order (matches the old bullet ordering).
    groups: dict[tuple[str, str], dict[str, SubsectionFinding]] = {}
    order: list[tuple[str, str]] = []
    for f in members:
        key = (f.metric, _dim_key_for_finding(f))
        if key not in groups:
            groups[key] = {}
            order.append(key)
        groups[key][f.window] = f

    recovery_note_emitted = False
    for key in order:
        metric, dim_key = key
        windows = groups[key]
        all_time = windows.get("all_time")
        last_3mo = windows.get("last_3mo")

        all_time_series = (
            _retained_series_for_summary(
                all_time,
                last_3mo_pairs=last_3mo_pairs,
                all_time_cutoff=all_time_cutoff,
            )
            if all_time is not None
            else None
        )
        last_3mo_series = (
            _retained_series_for_summary(
                last_3mo,
                last_3mo_pairs=last_3mo_pairs,
                all_time_cutoff=all_time_cutoff,
            )
            if last_3mo is not None
            else None
        )

        # v11: in endgame_elo_timeline, lead each combo with the derived
        # absolute Endgame ELO summary (the chart's headline value), then
        # the gap summary (which carries the zone interpretation).
        if subsection_id == "endgame_elo_timeline" and metric == "endgame_elo_gap":
            lines.extend(
                _render_endgame_elo_summary_block(
                    dim_key=dim_key,
                    all_time_finding=all_time,
                    last_3mo_finding=last_3mo,
                    all_time_series=all_time_series,
                    last_3mo_series=last_3mo_series,
                    stale_markers=stale_markers,
                )
            )
        lines.extend(
            _render_summary_block(
                metric,
                dim_key,
                all_time=all_time,
                last_3mo=last_3mo,
                all_time_series=all_time_series,
                last_3mo_series=last_3mo_series,
                stale_markers=stale_markers,
            )
        )
        if (
            not recovery_note_emitted
            and metric == "recovery_save_pct"
            and subsection_id == "conversion_recovery_by_type"
        ):
            lines.append(
                "  [typical band 25-35 is cohort-wide; weak here means at/below "
                "population average, not absolute crisis]"
            )
            recovery_note_emitted = True

        # Raw [series ...] block below the summary. Same C5 / stale-live-twin
        # gates as before: skip last_3mo series when an all_time series exists
        # for the same (metric, subsection); skip stale combos when a live
        # combo exists.
        for candidate_finding, candidate_series in (
            (all_time, all_time_series),
            (last_3mo, last_3mo_series),
        ):
            if candidate_finding is None or not candidate_series:
                continue
            if (
                candidate_finding.window == "last_3mo"
                and (
                    candidate_finding.metric,
                    candidate_finding.subsection_id,
                )
                in all_time_series_pairs
            ):
                continue
            if (
                id(candidate_finding) in stale_markers
                and (candidate_finding.metric, candidate_finding.subsection_id)
                in live_series_metrics
            ):
                continue
            lines.extend(_render_series_block(candidate_finding, candidate_series))

    lines.append("")
    return lines


def _assemble_user_prompt(findings: EndgameTabFindings) -> str:
    """Render EndgameTabFindings as structured text for the LLM (D-29 format).

    v8 layout: payload summary + filters (+ scoping caveat) + player profile,
    then one `## Section:` block per UI section with subsection and chart
    blocks interleaved in UI order. Each section maps 1:1 to one `section_id`
    in the LLM output. Empty sections (no qualifying blocks) are omitted.

    Filters applied:
    - A5: skip findings in _SKIPPED_SUBSECTIONS (time_pressure_vs_performance
      single-value placeholder; the 10-bucket chart is rendered instead).
    - A2: skip findings where value is NaN or (sample_size=0 AND thin quality).
    - A4: drop series points with n < MIN_BUCKET_N.
    - C2: for `all_time` series, drop points within last 90 days if a matching
      `last_3mo` series exists for the same (metric, subsection) pair.
    - C3: insert `[activity-gap] ...` markers when consecutive retained
      series points are > _ACTIVITY_GAP_DAYS apart.
    - C4: drop the scalar `overall` subsection when the overall_wdl chart
      renders — the 2-row chart already carries the framing.
    - C5: skip the `last_3mo` Series block when an `all_time` Series for
      the same (metric, subsection) is emitted. The last_3mo scalar stays.
    - C6: cap `all_time` series at the last _ALL_TIME_MAX_POINTS buckets.
    - Inline zone bounds: every finding bullet includes a
      `(typical LO to UP[, lower is better])` fragment next to the zone token.
    """
    # Pre-render chart blocks so we can gate the scalar `overall` subsection
    # (C4) on whether the overall_wdl chart will emit.
    overall_wdl_block = _format_overall_wdl_chart_block(findings)
    time_pressure_block = _format_time_pressure_chart_block(findings)
    type_wdl_block = _format_type_wdl_chart_block(findings)
    chart_blocks: dict[str, list[str]] = {
        "overall_wdl": overall_wdl_block,
        "time_pressure_vs_performance": time_pressure_block,
        "results_by_endgame_type_wdl": type_wdl_block,
    }

    # A5 + A2: drop hidden subsections, NaN values, and thin empty findings.
    # v6: also drop any finding dimensioned on endgame_class=pawnless — the UI
    # hides pawnless rows (ENDGAME_CLASS_LABELS, Endgames.tsx) so the LLM must
    # not narrate a type the user cannot see.
    visible: list[SubsectionFinding] = [
        f
        for f in findings.findings
        if f.subsection_id not in _SKIPPED_SUBSECTIONS
        and not math.isnan(f.value)
        and not (f.sample_size == 0 and f.sample_quality == "thin")
        and not (f.dimension is not None and f.dimension.get("endgame_class") == "pawnless")
    ]

    # v9/Phase 68: the `overall` subsection carries the authoritative
    # aggregate `[summary score_gap]` alongside the overall_wdl chart
    # (matches chart row math: endgame.score_pct - non_endgame.score_pct).
    # The renamed `score_timeline` subsection emits TWO findings per window
    # (one per `part`: endgame, non_endgame), each with its own absolute
    # rolling-window series — the prompt reads two lines instead of
    # narrating the signed difference as a scalar.

    last_3mo_pairs: set[tuple[str, str]] = {
        (f.metric, f.subsection_id) for f in visible if f.window == "last_3mo"
    }
    all_time_series_pairs: set[tuple[str, str]] = {
        (f.metric, f.subsection_id)
        for f in visible
        if f.window == "all_time" and f.series is not None
    }
    today = datetime.date.today()
    all_time_cutoff = (today - datetime.timedelta(days=_ALL_TIME_CUTOFF_DAYS)).isoformat()

    newest_date = _newest_bucket_date(visible)
    stale_markers: dict[int, str] = {}
    stale_count = 0
    live_series_metrics: set[tuple[str, str]] = set()
    for f in visible:
        if f.series is None:
            continue
        marker = _stale_marker(f.series, newest_date)
        if marker:
            stale_markers[id(f)] = marker
            stale_count += 1
        else:
            live_series_metrics.add((f.metric, f.subsection_id))
    asymmetry_lines = _asymmetry_lines(visible)
    activity_gap_count = _count_activity_gaps(visible)
    recovery_pattern = _recovery_pattern_tag(visible)
    all_time_window = _all_time_window_bounds(visible)

    # Group findings by subsection_id for per-block rendering.
    groups: dict[str, list[SubsectionFinding]] = {}
    for f in visible:
        groups.setdefault(f.subsection_id, []).append(f)

    lines: list[str] = []
    lines.extend(
        _payload_summary_lines(
            findings,
            newest_date=newest_date,
            stale_series_count=stale_count,
            activity_gap_count=activity_gap_count,
            all_time_window=all_time_window,
        )
    )
    lines.extend(_format_filters_for_prompt(findings.filters))
    lines.append("")
    lines.extend(_format_player_profile_block(findings.player_profile))

    # v8: emit one `## Section:` block per UI section, with subsections and
    # charts interleaved in UI order. Skip a whole section when none of its
    # blocks produce content.
    for section_id, layout in _SECTION_LAYOUT:
        section_body: list[str] = []
        for kind, block_id in layout:
            if kind == "chart":
                block = chart_blocks.get(block_id, [])
                if block:
                    section_body.extend(block)
            else:  # subsection
                members = groups.get(block_id)
                if not members:
                    continue
                section_body.extend(
                    _render_subsection_block(
                        subsection_id=block_id,
                        members=members,
                        stale_markers=stale_markers,
                        live_series_metrics=live_series_metrics,
                        last_3mo_pairs=last_3mo_pairs,
                        all_time_series_pairs=all_time_series_pairs,
                        all_time_cutoff=all_time_cutoff,
                        asymmetry_lines=asymmetry_lines,
                        recovery_pattern=recovery_pattern,
                    )
                )
        if not section_body:
            continue
        lines.append(f"## Section: {section_id}")
        lines.append("")
        lines.extend(section_body)

    return "\n".join(lines).rstrip() + "\n"


# -- Overview gate (CONTEXT.md D-18) --


def _maybe_strip_overview(report: EndgameInsightsReport) -> EndgameInsightsReport:
    """If INSIGHTS_HIDE_OVERVIEW is True, return a copy with overview=''.

    Full overview is still present in the llm_logs.response_json source of truth;
    only the client-facing copy is stripped. Frontend treats '' as 'hide section'.
    """
    if not settings.INSIGHTS_HIDE_OVERVIEW:
        return report
    return report.model_copy(update={"overview": ""})


# -- Stale-filter detection for soft-fail banner (CONTEXT.md D-14) --


def _maybe_stale_filters(
    fallback_log: LlmLog,
    current: FilterContext,
) -> FilterContext | None:
    """Compare fallback's opponent_strength to current; return fallback-scoped
    FilterContext if they differ.

    Log rows only persist `opponent_strength` (router enforces all other
    filters to defaults, so they never vary across logs). The banner only
    fires when that single field differs — all other FilterContext fields
    are guaranteed to match.

    Returns None when filters match (banner not shown).
    """
    fallback_os = fallback_log.filter_context["opponent_strength"]
    if fallback_os == current.opponent_strength:
        return None
    return current.model_copy(update={"opponent_strength": fallback_os})


# -- Rate-limit retry-after computation (CONTEXT.md D-11, RESEARCH.md §4) --


async def _compute_retry_after(session: AsyncSession, user_id: int) -> int:
    """Seconds until oldest successful miss in the 1h window expires."""
    oldest = await get_oldest_recent_miss_timestamp(session, user_id, _RATE_LIMIT_WINDOW)
    if oldest is None:
        return 1
    expires_at = oldest + _RATE_LIMIT_WINDOW
    delta = (expires_at - datetime.datetime.now(datetime.UTC)).total_seconds()
    return max(1, int(delta))


# -- Agent invocation wrapper: exception -> (None, marker), success -> (report, ...) --

_THOUGHTS_DETAIL_KEY = "thoughts_tokens"  # pydantic-ai Google adapter key (models/google.py:1454)


async def _run_agent(
    user_prompt: str,
    user_id: int,
    findings_hash: str,
) -> tuple[EndgameInsightsReport | None, int, int, int | None, int, str | None]:
    """Run the Agent; return (report, input_tokens, output_tokens, thinking_tokens, latency_ms, error_marker).

    On success: (report, in_toks, out_toks, thinking_toks_or_None, latency_ms, None).
    On failure: (None, 0, 0, None, latency_ms, "<marker>") and Sentry capture.

    thinking_tokens is None for providers that don't surface a separate thought
    count (Anthropic, OpenAI, test). For Google models with include_thoughts=True
    it comes from `usage.details["thoughts_tokens"]` (populated by pydantic-ai's
    Google adapter from usage_metadata.thoughts_token_count).

    Latency is measured ONLY around agent.run() per D-25.
    """
    agent = get_insights_agent()
    try:
        # WR-02 (phase 68 review): start the timer inside the try so latency
        # measures only the agent.run() call itself, not the small gap
        # between timer-start and the await.
        t0 = time.monotonic()
        result = await agent.run(user_prompt)
    except UnexpectedModelBehavior as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context(
            "insights",
            {
                "user_id": user_id,
                "findings_hash": findings_hash,
                "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
                "endpoint": _ENDPOINT,
            },
        )
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, None, latency_ms, "validation_failure_after_retries"
    except ModelAPIError as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context(
            "insights",
            {
                "user_id": user_id,
                "findings_hash": findings_hash,
                "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
                "endpoint": _ENDPOINT,
            },
        )
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, None, latency_ms, "provider_error"
    except Exception as exc:
        # Defensive catch-all for unexpected exceptions (e.g. httpx connect errors
        # not wrapped as ModelAPIError). Map to provider_error marker per
        # RESEARCH.md §2 "Any other unexpected Exception -> 502 / provider_error".
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context(
            "insights",
            {
                "user_id": user_id,
                "findings_hash": findings_hash,
                "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
                "endpoint": _ENDPOINT,
            },
        )
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, None, latency_ms, "provider_error"
    latency_ms = int((time.monotonic() - t0) * 1000)
    usage = result.usage()
    thinking = usage.details.get(_THOUGHTS_DETAIL_KEY) or None
    return result.output, usage.input_tokens, usage.output_tokens, thinking, latency_ms, None


# -- Orchestration entry point (CONTEXT.md D-33) --


async def generate_insights(
    filter_context: FilterContext,
    user_id: int,
    session: AsyncSession,
) -> EndgameInsightsResponse:
    """Tier-1 structural cache -> rate-limit -> tier-2 soft-fail -> fresh LLM call.

    Cache key (260425-dxh): (user_id, prompt_version, model, opponent_strength).
    Validity rule: row.created_at >= MAX(import_jobs.completed_at WHERE
    games_imported > 0) for this user, AND row younger than
    INSIGHTS_CACHE_MAX_AGE. Reordered so compute_findings only runs on miss.

    Returns EndgameInsightsResponse with status in {fresh, cache_hit,
    stale_rate_limited}. Raises InsightsRateLimitExceeded (router -> 429),
    InsightsProviderError (router -> 502), or InsightsValidationFailure
    (router -> 502) on the respective failure paths.

    All DB work runs on the caller-supplied session (sequential awaits).
    create_llm_log opens its OWN session (Phase 64 D-02) so log rows
    persist even if the caller's session rolls back.
    """
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS

    # Tier-1 STRUCTURAL cache lookup (260425-dxh): cheap query on
    # (user_id, prompt_version, model, opponent_strength) + freshness checks.
    # Runs BEFORE compute_findings so cache hits skip the heavy DB pipeline.
    # Bug-fix note: the previous findings_hash-based lookup was unstable across
    # days because EndgameTabFindings includes time-relative fields (sliding
    # 3-month window stats and stale_months markers), so the hash drifted even
    # with a frozen game corpus. The hash also wasn't user-scoped — a latent
    # cross-user collision risk that the new helper closes by filtering on
    # user_id directly.
    cached = await get_latest_successful_log_for_user(
        session,
        user_id=user_id,
        prompt_version=_PROMPT_VERSION,
        model=model,
        opponent_strength=filter_context.opponent_strength,
        max_age=INSIGHTS_CACHE_MAX_AGE,
    )
    if cached is not None:
        last_import_at = await get_latest_completed_import_with_games_at(session, user_id)
        # Cache row valid only if no qualifying import has happened since it
        # was written. games_imported=0 imports were intentionally excluded
        # in the helper, so no-op resyncs do not invalidate the cache.
        if last_import_at is None or last_import_at <= cached.created_at:
            report = EndgameInsightsReport.model_validate(cached.response_json)
            return EndgameInsightsResponse(
                report=_maybe_strip_overview(report),
                status="cache_hit",
            )

    # Cache miss path: now we pay for compute_findings.
    findings = await compute_findings(filter_context, session, user_id)

    # Rate-limit check (CONTEXT.md D-09, D-10).
    misses = await count_recent_successful_misses(session, user_id, _RATE_LIMIT_WINDOW)
    if misses >= INSIGHTS_MISSES_PER_HOUR:
        fallback = await get_latest_report_for_user(session, user_id, _PROMPT_VERSION, model)
        if fallback is not None:
            stale_report = EndgameInsightsReport.model_validate(fallback.response_json)
            stale = _maybe_stale_filters(fallback, filter_context)
            return EndgameInsightsResponse(
                report=_maybe_strip_overview(stale_report),
                status="stale_rate_limited",
                stale_filters=stale,
            )
        retry_after = await _compute_retry_after(session, user_id)
        raise InsightsRateLimitExceeded(retry_after_seconds=retry_after)

    # Fresh call.
    user_prompt = _assemble_user_prompt(findings)
    report, in_tokens, out_tokens, thinking_tokens, latency_ms, marker = await _run_agent(
        user_prompt, user_id, findings.findings_hash
    )
    # A3 (260422-tnb): server-side override of model_used and prompt_version.
    # Previously the system prompt asked the LLM to echo these back, which
    # produced fabricated strings ("gpt-4o" in Gemini outputs). Overriding
    # here — before create_llm_log — ensures both the response AND the
    # persisted log row store the authoritative values.
    if report is not None:
        report = report.model_copy(
            update={
                "model_used": model,
                "prompt_version": _PROMPT_VERSION,
            }
        )
    await create_llm_log(
        LlmLogCreate(
            user_id=user_id,
            endpoint=_ENDPOINT,
            model=model,
            prompt_version=_PROMPT_VERSION,
            findings_hash=findings.findings_hash,
            filter_context=LlmLogFilterContext(opponent_strength=filter_context.opponent_strength),
            user_prompt=user_prompt,
            response_json=report.model_dump() if report is not None else None,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            thinking_tokens=thinking_tokens,
            latency_ms=latency_ms,
            cache_hit=False,
            error=marker,
        )
    )
    if marker == "validation_failure_after_retries":
        raise InsightsValidationFailure(marker)
    if marker is not None or report is None:
        raise InsightsProviderError(marker or "provider_error")
    return EndgameInsightsResponse(
        report=_maybe_strip_overview(report),
        status="fresh",
    )
