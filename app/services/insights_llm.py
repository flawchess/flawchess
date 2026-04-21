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
import time
from pathlib import Path

import sentry_sdk
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm_log import LlmLog
from app.repositories.llm_log_repository import (
    count_recent_successful_misses,
    create_llm_log,
    get_latest_log_by_hash,
    get_latest_report_for_user,
)
from app.schemas.insights import (
    EndgameInsightsReport,
    EndgameInsightsResponse,
    EndgameTabFindings,
    FilterContext,
)
from app.schemas.llm_log import LlmLogCreate, LlmLogEndpoint
from app.services.insights_service import compute_findings

# -- Module-level constants (CLAUDE.md: no magic numbers) --

INSIGHTS_MISSES_PER_HOUR = 3             # CONTEXT.md D-09
_PROMPT_VERSION = "endgame_v1"           # CONTEXT.md D-08, bump to "endgame_v2" on prompt edit
_OUTPUT_RETRIES = 2                      # CONTEXT.md D-24, RESEARCH.md §2
_RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)
_ENDPOINT: LlmLogEndpoint = "insights.endgame"

_PROMPTS_DIR = Path(__file__).parent / "insights_prompts"
_SYSTEM_PROMPT = (_PROMPTS_DIR / "endgame_v1.md").read_text(encoding="utf-8")


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

@functools.lru_cache(maxsize=1)
def get_insights_agent() -> Agent[None, EndgameInsightsReport]:
    """Return the singleton pydantic-ai Agent, constructing on first call.

    Raises:
        UserError: empty PYDANTIC_AI_MODEL_INSIGHTS or unknown model suffix.
        ValueError: unknown provider prefix (e.g., "bogus-provider:foo").

    Called from (a) main.py lifespan for startup validation (Plan 06), and
    (b) generate_insights() at request time. lru_cache ensures one Agent
    instance across the app lifetime; pydantic-ai Agents are async-safe
    (RESEARCH.md §6).
    """
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS
    return Agent(  # ty: ignore[invalid-return-type] — pydantic-ai Agent generic params depend on runtime model string; ty cannot infer Agent[None, EndgameInsightsReport] from a str variable
        model,
        output_type=EndgameInsightsReport,
        system_prompt=_SYSTEM_PROMPT,
        output_retries=_OUTPUT_RETRIES,
    )


# -- User-prompt assembly (CONTEXT.md D-28, D-29) --

# Subsections that produce Series blocks in the prompt (MUST match Plan 03's _TIMELINE_SUBSECTION_IDS).
_TIMELINE_SUBSECTION_IDS: frozenset[str] = frozenset({
    "score_gap_timeline",
    "clock_diff_timeline",
    "endgame_elo_timeline",
    "type_win_rate_timeline",
})


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


def _assemble_user_prompt(findings: EndgameTabFindings) -> str:
    """Render EndgameTabFindings as structured text for the LLM (D-29 format)."""
    lines: list[str] = [
        _format_filters_for_prompt(findings.filters),
        f"Flags: {', '.join(findings.flags) if findings.flags else 'none'}",
        "",
    ]
    for f in findings.findings:
        header = f"## Subsection: {f.subsection_id}"
        if f.parent_subsection_id:
            header += f" (parent: {f.parent_subsection_id})"
        lines.append(header)
        dim = ""
        if f.dimension:
            dim = " [" + ", ".join(f"{k}={v}" for k, v in f.dimension.items()) + "]"
        lines.append(
            f"- {f.metric} ({f.window}): {f.value:+.2f} | {f.zone} | "
            f"{f.sample_size} games | {f.sample_quality}{dim}"
        )
        if f.series is not None and f.subsection_id in _TIMELINE_SUBSECTION_IDS:
            # Determine resolution for the series header.
            # type_win_rate_timeline always uses monthly (D-05).
            # score_gap_timeline / clock_diff_timeline use weekly for last_3mo.
            if f.subsection_id == "type_win_rate_timeline":
                resolution = "monthly"
            elif f.window == "last_3mo":
                resolution = "weekly"
            else:
                resolution = "monthly"
            lines.append(f"### Series ({f.metric}, {f.window}, {resolution})")
            for pt in f.series:
                lines.append(f"{pt.bucket_start}: {pt.value:+.3f} (n={pt.n})")
        lines.append("")
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
    cutoff = datetime.datetime.now(datetime.UTC) - _RATE_LIMIT_WINDOW
    result = await session.execute(
        select(LlmLog.created_at)
        .where(
            LlmLog.user_id == user_id,
            LlmLog.created_at > cutoff,
            LlmLog.cache_hit.is_(False),
            LlmLog.error.is_(None),
            LlmLog.response_json.is_not(None),
        )
        .order_by(LlmLog.created_at.asc())
        .limit(1)
    )
    oldest = result.scalar_one_or_none()
    if oldest is None:
        return 1
    expires_at = oldest + _RATE_LIMIT_WINDOW
    delta = (expires_at - datetime.datetime.now(datetime.UTC)).total_seconds()
    return max(1, int(delta))


# -- Agent invocation wrapper: exception -> (None, marker), success -> (report, ...) --

async def _run_agent(
    user_prompt: str,
    user_id: int,
    findings_hash: str,
) -> tuple[EndgameInsightsReport | None, int, int, int, str | None]:
    """Run the Agent; return (report, input_tokens, output_tokens, latency_ms, error_marker).

    On success: (report, in_toks, out_toks, latency_ms, None).
    On failure: (None, 0, 0, latency_ms, "<marker>") and Sentry capture.

    Latency is measured ONLY around agent.run() per D-25.
    """
    agent = get_insights_agent()
    t0 = time.monotonic()
    try:
        result = await agent.run(user_prompt)
    except UnexpectedModelBehavior as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context("insights", {
            "user_id": user_id,
            "findings_hash": findings_hash,
            "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
            "endpoint": _ENDPOINT,
        })
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, latency_ms, "validation_failure_after_retries"
    except ModelAPIError as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context("insights", {
            "user_id": user_id,
            "findings_hash": findings_hash,
            "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
            "endpoint": _ENDPOINT,
        })
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, latency_ms, "provider_error"
    except Exception as exc:
        # Defensive catch-all for unexpected exceptions (e.g. httpx connect errors
        # not wrapped as ModelAPIError). Map to provider_error marker per
        # RESEARCH.md §2 "Any other unexpected Exception -> 502 / provider_error".
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context("insights", {
            "user_id": user_id,
            "findings_hash": findings_hash,
            "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
            "endpoint": _ENDPOINT,
        })
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, latency_ms, "provider_error"
    latency_ms = int((time.monotonic() - t0) * 1000)
    usage = result.usage()
    return result.output, usage.input_tokens, usage.output_tokens, latency_ms, None


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
    cached = await get_latest_log_by_hash(
        session, findings.findings_hash, _PROMPT_VERSION, model
    )
    if cached is not None:
        report = EndgameInsightsReport.model_validate(cached.response_json)
        return EndgameInsightsResponse(
            report=_maybe_strip_overview(report),
            status="cache_hit",
        )

    # Rate-limit check (CONTEXT.md D-09, D-10).
    misses = await count_recent_successful_misses(
        session, user_id, _RATE_LIMIT_WINDOW
    )
    if misses >= INSIGHTS_MISSES_PER_HOUR:
        fallback = await get_latest_report_for_user(
            session, user_id, _PROMPT_VERSION, model
        )
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
    report, in_tokens, out_tokens, latency_ms, marker = await _run_agent(
        user_prompt, user_id, findings.findings_hash
    )
    await create_llm_log(LlmLogCreate(
        user_id=user_id,
        endpoint=_ENDPOINT,
        model=model,
        prompt_version=_PROMPT_VERSION,
        findings_hash=findings.findings_hash,
        filter_context=filter_context.model_dump(),
        flags=list(findings.flags),
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_json=report.model_dump() if report is not None else None,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        latency_ms=latency_ms,
        cache_hit=False,
        error=marker,
    ))
    if marker == "validation_failure_after_retries":
        raise InsightsValidationFailure(marker)
    if marker is not None or report is None:
        raise InsightsProviderError(marker or "provider_error")
    return EndgameInsightsResponse(
        report=_maybe_strip_overview(report),
        status="fresh",
    )
