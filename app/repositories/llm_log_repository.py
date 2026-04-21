"""LLM log repository: async write + read surface for the llm_logs table.

UNLIKE other repositories in this package, `create_llm_log` opens its OWN
async session via `async_session_maker()` and commits independently so log
rows survive caller rollbacks. This is intentional: `llm_logs` captures LLM
failures, and if the caller's request-scoped session rolls back (HTTPException,
validation error, pydantic-ai crash), the log row must still persist. See
Phase 64 CONTEXT.md D-02.

`create_llm_log` also computes `cost_usd` internally via
`genai_prices.calc_price` (D-03). On LookupError (unknown model), cost falls
back to Decimal("0") and a `cost_unknown:<model>` marker is appended to the
row's `error` column per SC #4. This is the ONLY variable interpolation in
this module. It is a stable enum-like prefix, not a dynamic error message,
and conforms to the SC #4 contract rather than CLAUDE.md's no-interpolation
error-reporting rule (D-08).

`get_latest_log_by_hash` is the Phase 65 tier-1 cache-lookup. It takes a
caller-supplied session because the read path has no durability-vs-rollback
concern — the caller already has a session.

Phase 65 extends the read surface with two additional helpers per CONTEXT.md
D-34: `count_recent_successful_misses` (rate-limit count query, D-09) and
`get_latest_report_for_user` (tier-2 soft-fail fallback, D-11). Both take
caller-supplied sessions matching the read-path convention. `create_llm_log`
remains the sole own-session entry point (write-path, D-02).
"""

import datetime
from decimal import Decimal

from genai_prices import Usage, calc_price
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.llm_log import LlmLog
from app.schemas.llm_log import LlmLogCreate

_COST_UNKNOWN_PREFIX = "cost_unknown:"  # kept stable + LIKE-queryable
_ERROR_JOIN_SEP = "; "  # concatenates caller-supplied error with cost_unknown marker
_MODEL_SEP = ":"  # pydantic-ai "provider:model" format separator


async def create_llm_log(data: LlmLogCreate) -> LlmLog:
    """Persist one llm_logs row. Computes cost_usd via genai-prices.

    On LookupError from genai-prices (unknown model), sets cost_usd=0 and
    appends `cost_unknown:<model>` to data.error. Never swallows DB errors —
    caller captures at the router/service layer (D-08).

    Args:
        data: Validated LlmLogCreate DTO with all 15 caller-supplied fields.

    Returns:
        The committed LlmLog with id, created_at, cost_usd populated.

    Raises:
        sqlalchemy.exc.IntegrityError / sqlalchemy.exc.DBAPIError: propagated
            verbatim from the underlying asyncpg driver on DB-side failures
            (FK violations, serialization errors, connection issues). Callers
            capture at the router/service layer.
    """
    cost_usd, error_with_cost_marker = _finalize_cost_and_error(data)

    async with async_session_maker() as session:
        row = LlmLog(
            **data.model_dump(exclude={"error"}),
            error=error_with_cost_marker,
            cost_usd=cost_usd,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


def _finalize_cost_and_error(data: LlmLogCreate) -> tuple[Decimal, str | None]:
    """Compute cost_usd and compose the final error string.

    Returns (cost, error) where cost is a non-negative Decimal and error is
    either None, the caller's original error, the cost_unknown marker alone,
    or caller_error + `; ` + cost_unknown marker.
    """
    price = _compute_cost(data.model, data.input_tokens, data.output_tokens)
    if price is not None:
        return price, data.error
    # genai-prices LookupError path — model unknown.
    # This is the ONLY variable interpolation in this module; the prefix is
    # a stable enum-like marker (SC #4), NOT a dynamic error-report string.
    marker = f"{_COST_UNKNOWN_PREFIX}{data.model}"
    combined = f"{data.error}{_ERROR_JOIN_SEP}{marker}" if data.error else marker
    return Decimal("0"), combined


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal | None:
    """Return cost in USD as Decimal, or None if genai-prices can't match the model.

    Splits the pydantic-ai `provider:model` string on the FIRST `:` into
    provider_id + model_ref before calling genai-prices.calc_price. The split
    form is required — Plan 01's Wave 0 smoke test confirmed the combined
    "anthropic:claude-..." string raises LookupError inside genai-prices
    (see Phase 64 Plan 01 SUMMARY and commit e345d36). If `model` contains
    no colon, treats the whole string as model_ref with no provider_id, which
    will raise LookupError and fall through to the cost_unknown path.
    """
    provider_id, _, model_ref = model.partition(_MODEL_SEP)
    if not model_ref:
        # No colon in the model string — nothing to match on. Let genai-prices
        # raise LookupError naturally by passing the whole string as model_ref.
        model_ref = provider_id
        provider_id = ""
    try:
        price = calc_price(
            Usage(input_tokens=input_tokens, output_tokens=output_tokens),
            model_ref=model_ref,
            provider_id=provider_id or None,
        )
    except LookupError:
        return None
    # genai-prices returns Decimal already; Decimal(str(...)) is defensive normalization.
    return Decimal(str(price.total_price))


async def get_latest_log_by_hash(
    session: AsyncSession,
    findings_hash: str,
    prompt_version: str,
    model: str,
) -> LlmLog | None:
    """Phase 65 cache-lookup stub. Returns most recent successful log for the key.

    UNLIKE create_llm_log, this read helper takes a caller-supplied session —
    Phase 65's cache-lookup path already has one, and reads don't have the
    durability-across-rollback motivation that writes do.

    "Successful" means response_json IS NOT NULL and error IS NULL — a row
    written with error set (e.g., provider error, cost_unknown) is NOT a
    cache hit.

    Args:
        session: caller's AsyncSession.
        findings_hash: 64-char sha256 hex from insights_service.compute_findings.
        prompt_version: semver-ish string matching llm_logs.prompt_version.
        model: pydantic-ai `provider:model` string matching llm_logs.model.

    Returns:
        The most recent matching LlmLog or None.
    """
    result = await session.execute(
        select(LlmLog)
        .where(
            LlmLog.findings_hash == findings_hash,
            LlmLog.prompt_version == prompt_version,
            LlmLog.model == model,
            LlmLog.response_json.is_not(None),
            LlmLog.error.is_(None),
        )
        .order_by(LlmLog.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def count_recent_successful_misses(
    session: AsyncSession,
    user_id: int,
    window: datetime.timedelta,
) -> int:
    """Count successful cache-miss LLM calls for user within the time window.

    "Successful miss" per CONTEXT.md D-09 / D-10:
      - cache_hit IS FALSE
      - error IS NULL
      - response_json IS NOT NULL

    Only these rows consume rate-limit quota. A provider-error row (error
    populated, response_json NULL) does NOT count — pydantic-ai already
    retries internally on structured-output failures, so logged failures
    are "real" failures and shouldn't lock the user out.

    Uses Phase 64's composite index ix_llm_logs_user_id_created_at (DESC)
    for the equality-on-user_id + range-on-created_at filter. The
    cache_hit / error / response_json filters apply post-index-scan on the
    small per-user-per-hour slice.

    Args:
        session: caller-supplied AsyncSession (read path — no durability concern).
        user_id: authenticated user scoping the query (mandatory — never call without).
        window: timedelta defining the look-back window (e.g. timedelta(hours=1)).

    Returns:
        Integer count of successful-miss rows in the window. Zero when no rows match.
    """
    cutoff = datetime.datetime.now(datetime.UTC) - window
    result = await session.execute(
        select(func.count())
        .select_from(LlmLog)
        .where(
            LlmLog.user_id == user_id,
            LlmLog.created_at > cutoff,
            LlmLog.cache_hit.is_(False),
            LlmLog.error.is_(None),
            LlmLog.response_json.is_not(None),
        )
    )
    return result.scalar_one()


async def get_oldest_recent_miss_timestamp(
    session: AsyncSession,
    user_id: int,
    window: datetime.timedelta,
) -> datetime.datetime | None:
    """Return created_at of the oldest successful miss within the window, or None.

    Used by the rate-limit retry-after computation in the service layer to
    calculate when the oldest miss in the current window expires. Factored out
    of the service so DB access stays exclusively in the repository (CLAUDE.md
    §Architecture: "no SQL in services").

    "Successful miss" definition mirrors count_recent_successful_misses:
      - cache_hit IS FALSE
      - error IS NULL
      - response_json IS NOT NULL

    Args:
        session: caller-supplied AsyncSession.
        user_id: authenticated user scoping the query.
        window: timedelta defining the look-back window (e.g. timedelta(hours=1)).

    Returns:
        The created_at timestamp of the oldest qualifying row, or None if no
        rows exist in the window (caller defaults retry_after to 1 second).
    """
    cutoff = datetime.datetime.now(datetime.UTC) - window
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
    return result.scalar_one_or_none()


async def get_latest_report_for_user(
    session: AsyncSession,
    user_id: int,
    prompt_version: str,
    model: str,
) -> LlmLog | None:
    """Tier-2 soft-fail lookup per CONTEXT.md D-11.

    Returns the user's most recent successful report under the current
    prompt_version / model era. Called when rate-limit is exhausted and
    tier-1 exact cache lookup (get_latest_log_by_hash) returned None.

    Rationale for the era filter (prompt_version + model): serving a stale
    report from a prior prompt/model era would mix narratives from
    inconsistent prompts, confusing the user. Limiting to current era
    ensures stale content is still stylistically / semantically coherent
    with what a fresh call would have produced.

    "Successful" per same rule as tier-1: response_json IS NOT NULL AND
    error IS NULL — a cost_unknown row or provider-error row is NOT a
    valid stale-serve source.

    Index coverage: ix_llm_logs_user_id_created_at (user_id equality +
    created_at DESC ordering). prompt_version / model / response_json /
    error filters apply on the small per-user-per-era slice.

    Args:
        session: caller-supplied AsyncSession.
        user_id: authenticated user scoping the query.
        prompt_version: current prompt version (e.g. "endgame_v1") — era key.
        model: current pydantic-ai model string (e.g. "anthropic:claude-...") — era key.

    Returns:
        The most recent matching LlmLog, or None if no row matches.
    """
    result = await session.execute(
        select(LlmLog)
        .where(
            LlmLog.user_id == user_id,
            LlmLog.prompt_version == prompt_version,
            LlmLog.model == model,
            LlmLog.response_json.is_not(None),
            LlmLog.error.is_(None),
        )
        .order_by(LlmLog.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
