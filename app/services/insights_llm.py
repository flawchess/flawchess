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
from collections import OrderedDict
from pathlib import Path
from typing import Literal, cast

import sentry_sdk
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm_log import LlmLog
from app.repositories.llm_log_repository import (
    count_recent_successful_misses,
    create_llm_log,
    get_latest_log_by_hash,
    get_latest_report_for_user,
    get_oldest_recent_miss_timestamp,
)
from app.schemas.insights import (
    EndgameInsightsReport,
    EndgameInsightsResponse,
    EndgameTabFindings,
    FilterContext,
    SubsectionFinding,
)
from app.schemas.llm_log import LlmLogCreate, LlmLogEndpoint
from app.services.endgame_zones import BUCKETED_ZONE_REGISTRY, ZONE_REGISTRY
from app.services.insights_service import compute_findings

# -- Module-level constants (CLAUDE.md: no magic numbers) --

INSIGHTS_MISSES_PER_HOUR = 3  # CONTEXT.md D-09
_PROMPT_VERSION = "endgame_v4"  # bumped from "endgame_v3" when score_gap_timeline section moved overall, statistics-concepts section added, and overall_wdl + results_by_endgame_type_wdl chart blocks added
_OUTPUT_RETRIES = 2  # CONTEXT.md D-24, RESEARCH.md §2
_RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)
_ENDPOINT: LlmLogEndpoint = "insights.endgame"

# Series / prompt-assembly filter constants (260422-tnb A4/C3/A5/C2).
MIN_BUCKET_N: int = 3  # A4: drop timeline points with n<3
_ACTIVITY_GAP_DAYS: int = 90  # C3: insert gap markers between >90-day-apart points
_ALL_TIME_CUTOFF_DAYS: int = 90  # C2: trim last 90d from all_time series when last_3mo exists
# time_pressure_vs_performance produces a single weighted-mean finding that is
# not useful on its own; the 10-bucket chart is rendered separately by
# `_format_time_pressure_chart_block`.
_SKIPPED_SUBSECTIONS: frozenset[str] = frozenset({"time_pressure_vs_performance"})
# Mirror frontend MIN_GAMES_FOR_RELIABLE_STATS (frontend/src/lib/theme.ts) so
# the LLM sees the same bucket gating as the rendered chart.
_MIN_GAMES_FOR_RELIABLE_BUCKET: int = 10

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
    lines.append("Numeric bands for each metric (auto-generated — do not contradict).")
    lines.append("")
    for metric_id, spec in ZONE_REGISTRY.items():
        if spec.direction == "higher_is_better":
            lines.append(
                f"- `{metric_id}`: weak<{spec.typical_lower:.2f}, "
                f"typical [{spec.typical_lower:.2f}, {spec.typical_upper:.2f}], "
                f"strong>{spec.typical_upper:.2f}"
            )
        else:
            lines.append(
                f"- `{metric_id}` (lower_is_better): strong<={spec.typical_lower:.2f}, "
                f"typical [{spec.typical_lower:.2f}, {spec.typical_upper:.2f}], "
                f"weak>{spec.typical_upper:.2f}"
            )
    lines.append("")
    lines.append("Bucketed metrics (one band per MaterialBucket):")
    for metric_id, buckets in BUCKETED_ZONE_REGISTRY.items():
        lines.append(f"- `{metric_id}`:")
        for bucket, spec in buckets.items():
            lines.append(
                f"  - {bucket}: weak<{spec.typical_lower:.2f}, "
                f"typical [{spec.typical_lower:.2f}, {spec.typical_upper:.2f}], "
                f"strong>{spec.typical_upper:.2f}"
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
        "score_gap_timeline",
        "clock_diff_timeline",
        "endgame_elo_timeline",
        "type_win_rate_timeline",
    }
)


def _format_filters_for_prompt(filters: FilterContext) -> str:
    """Render FilterContext as 'Filters: key=value, ...' string.

    Excludes `color` and `rated_only` per INS-03 / D-31 — they flow into the
    findings pipeline (affecting what games count) but must NOT appear in
    the LLM prompt (they don't materially reshape the cross-section story).
    """
    parts = [
        f"recency={filters.recency}",
        f"opponent={filters.opponent_strength}",
        f"tc=[{','.join(filters.time_controls) or 'all'}]",
        f"platform=[{','.join(filters.platforms) or 'all'}]",
    ]
    return "Filters: " + ", ".join(parts)


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
            f"{u.score:.2f}"
            if u is not None and u.score is not None and u_n >= _MIN_GAMES_FOR_RELIABLE_BUCKET
            else "—"
        )
        o_score = (
            f"{o.score:.2f}"
            if o is not None and o.score is not None and o_n >= _MIN_GAMES_FOR_RELIABLE_BUCKET
            else "—"
        )
        rows.append(f"| {label:<7} | {u_score:<10} | {u_n:<6} | {o_score:<10} | {o_n:<6} |")

    if not rows:
        return []

    lines: list[str] = [
        "## Chart: time_pressure_vs_performance (all_time)",
        f"Total endgame games: {chart.total_endgame_games}. "
        "Rows show Score % conditional on time remaining at endgame entry, "
        "for the user and the opponent separately (each side binned by their own clock).",
        "| time_left | user_score | user_n | opp_score | opp_n |",
        "| --------- | ---------- | ------ | ---------- | ------ |",
    ]
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
        win_frac = summary.win_pct / 100.0
        draw_frac = summary.draw_pct / 100.0
        loss_frac = summary.loss_pct / 100.0
        score_frac = (summary.wins + 0.5 * summary.draws) / total
        rows.append(
            f"| {label:<11} | {total:<5} | {win_frac:.2f}    | {draw_frac:.2f}     | "
            f"{loss_frac:.2f}     | {score_frac:.3f}     |"
        )

    if not rows:
        return []

    lines: list[str] = [
        "## Chart: overall_wdl (all_time)",
        "Two-row WDL comparison for games that reached an endgame phase vs games that did not. "
        "score_pct uses wins=1, draws=0.5, losses=0.",
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

    sorted_cats = sorted(categories, key=lambda c: c.total, reverse=True)

    rows: list[str] = []
    for cat in sorted_cats:
        if cat.total < _MIN_GAMES_FOR_RELIABLE_BUCKET:
            continue
        win_frac = cat.win_pct / 100.0
        draw_frac = cat.draw_pct / 100.0
        loss_frac = cat.loss_pct / 100.0
        score_frac = (cat.wins + 0.5 * cat.draws) / cat.total
        rows.append(
            f"| {cat.endgame_class:<13} | {cat.total:<5} | {win_frac:.2f}    | "
            f"{draw_frac:.2f}     | {loss_frac:.2f}     | {score_frac:.3f}     |"
        )

    if not rows:
        return []

    lines: list[str] = [
        "## Chart: results_by_endgame_type_wdl (all_time)",
        "Per-endgame-type W/D/L and Score % for the user. opp_score_pct = 1 - score_pct "
        "(both sides played the same games), so a score_pct above 0.50 means the user "
        "outscores their opponents in that type.",
        "| endgame_class | games | win_pct | draw_pct | loss_pct | score_pct |",
        "| ------------- | ----- | ------- | -------- | -------- | --------- |",
    ]
    lines.extend(rows)
    lines.append("")
    return lines


def _assemble_user_prompt(findings: EndgameTabFindings) -> str:
    """Render EndgameTabFindings as structured text for the LLM (D-29 format).

    Filters applied (260422-tnb):
    - A5: skip findings in _SKIPPED_SUBSECTIONS (time_pressure_vs_performance).
    - A2: skip findings where value is NaN or (sample_size=0 AND thin quality).
    - C1: group findings by subsection_id under one header (not one per finding).
    - A4: drop series points with n < MIN_BUCKET_N.
    - C2: for `all_time` series, drop points within last 90 days if a matching
      `last_3mo` series exists for the same (metric, subsection) pair.
    - C3: insert `# Activity gap: ...` markers when consecutive retained
      series points are > _ACTIVITY_GAP_DAYS apart.
    """
    # A5 + A2: drop hidden subsections, NaN values, and thin empty findings.
    visible: list[SubsectionFinding] = [
        f
        for f in findings.findings
        if f.subsection_id not in _SKIPPED_SUBSECTIONS
        and not math.isnan(f.value)
        and not (f.sample_size == 0 and f.sample_quality == "thin")
    ]

    # C2: identify (metric, subsection_id) pairs that have a `last_3mo` variant
    # so we can trim the last 90 days off the matching `all_time` series below.
    last_3mo_pairs: set[tuple[str, str]] = {
        (f.metric, f.subsection_id) for f in visible if f.window == "last_3mo"
    }
    today = datetime.date.today()
    all_time_cutoff = (today - datetime.timedelta(days=_ALL_TIME_CUTOFF_DAYS)).isoformat()

    # C1: group by subsection_id preserving first-seen order.
    groups: OrderedDict[str, list[SubsectionFinding]] = OrderedDict()
    for f in visible:
        groups.setdefault(f.subsection_id, []).append(f)

    lines: list[str] = [
        _format_filters_for_prompt(findings.filters),
        "",
    ]

    for subsection_id, members in groups.items():
        header = f"## Subsection: {subsection_id}"
        # Parent info on header if any finding in the group has one (take first).
        parent = next(
            (m.parent_subsection_id for m in members if m.parent_subsection_id),
            None,
        )
        if parent:
            header += f" (parent: {parent})"
        lines.append(header)

        for f in members:
            dim = ""
            if f.dimension:
                dim = " [" + ", ".join(f"{k}={v}" for k, v in f.dimension.items()) + "]"
            lines.append(
                f"- {f.metric} ({f.window}): {f.value:+.2f} | {f.zone} | "
                f"{f.sample_size} games | {f.sample_quality}{dim}"
            )

            # Series rendering with A4/C2/C3 filters applied.
            if f.series is not None and f.subsection_id in _TIMELINE_SUBSECTION_IDS:
                # A4: drop sparse points.
                points = [pt for pt in f.series if pt.n >= MIN_BUCKET_N]
                # C2: if an all_time series has a last_3mo twin for the same
                # (metric, subsection), trim the last 90 days off the all_time
                # series so the two don't duplicate coverage.
                if f.window == "all_time" and (f.metric, f.subsection_id) in last_3mo_pairs:
                    points = [pt for pt in points if pt.bucket_start < all_time_cutoff]

                if not points:
                    continue

                # Resolution header for LLM orientation.
                if f.subsection_id == "type_win_rate_timeline":
                    resolution = "monthly"
                elif f.window == "last_3mo":
                    resolution = "weekly"
                else:
                    resolution = "monthly"
                lines.append(f"### Series ({f.metric}, {f.window}, {resolution})")

                # C3: emit points with activity-gap markers between >90-day gaps.
                prev_date: datetime.date | None = None
                prev_bucket_start: str | None = None
                for pt in points:
                    curr_date = datetime.date.fromisoformat(pt.bucket_start)
                    if (
                        prev_date is not None
                        and prev_bucket_start is not None
                        and (curr_date - prev_date).days > _ACTIVITY_GAP_DAYS
                    ):
                        lines.append(f"# Activity gap: {prev_bucket_start} → {pt.bucket_start}")
                    lines.append(f"{pt.bucket_start}: {pt.value:+.3f} (n={pt.n})")
                    prev_date = curr_date
                    prev_bucket_start = pt.bucket_start

        lines.append("")

    lines.extend(_format_overall_wdl_chart_block(findings))
    lines.extend(_format_time_pressure_chart_block(findings))
    lines.extend(_format_type_wdl_chart_block(findings))

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
    """Compare fallback's filter_context to current; return fallback if they differ.

    Equality ignores `color` and `rated_only` (same exclusion as the prompt --
    those fields don't materially reshape findings for LLM purposes).
    Returns None when filters match (banner not shown).
    """
    fallback = FilterContext.model_validate(fallback_log.filter_context)
    # Normalize out the ignored fields before comparison.
    current_dict = current.model_dump(exclude={"color", "rated_only"})
    fallback_dict = fallback.model_dump(exclude={"color", "rated_only"})
    if current_dict == fallback_dict:
        return None
    return fallback


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
    t0 = time.monotonic()
    try:
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
    """Tier-1 cache -> rate-limit -> tier-2 soft-fail -> fresh LLM call.

    Returns EndgameInsightsResponse with status in {fresh, cache_hit,
    stale_rate_limited}. Raises InsightsRateLimitExceeded (router -> 429),
    InsightsProviderError (router -> 502), or InsightsValidationFailure
    (router -> 502) on the respective failure paths.

    All DB work runs on the caller-supplied session (sequential awaits).
    create_llm_log opens its OWN session (Phase 64 D-02) so log rows
    persist even if the caller's session rolls back.
    """
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS
    findings = await compute_findings(filter_context, session, user_id)

    # Tier-1 cache lookup (CONTEXT.md D-08).
    cached = await get_latest_log_by_hash(session, findings.findings_hash, _PROMPT_VERSION, model)
    if cached is not None:
        report = EndgameInsightsReport.model_validate(cached.response_json)
        return EndgameInsightsResponse(
            report=_maybe_strip_overview(report),
            status="cache_hit",
        )

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
            filter_context=filter_context.model_dump(),
            flags=[],
            system_prompt=_SYSTEM_PROMPT,
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
