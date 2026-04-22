"""Integration tests for app/repositories/llm_log_repository.py.

Covers:
- LOG-02 happy path: create_llm_log writes one row with computed cost.
- SC #4 cost_unknown fallback: unknown model → cost_usd=0 + error marker.
- SC #4 cost_unknown append: unknown model + caller error → concatenated.
- Phase 65 cache-lookup stub: get_latest_log_by_hash filters error IS NULL
  AND response_json IS NOT NULL.

IMPORTANT: These tests use the Phase-64-added `fresh_test_user` fixture,
NOT the rollback-scoped `db_session` fixture. create_llm_log opens its own
async_session_maker() scope and commits independently (D-02); db_session
rolls back at end-of-test and cannot observe those commits. fresh_test_user
commits its User via its own session and deletes on teardown (ON DELETE
CASCADE removes any inserted log rows).
"""

from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.user import User
from app.repositories.llm_log_repository import (
    create_llm_log,
    get_latest_log_by_hash,
)
from app.schemas.llm_log import LlmLogCreate


def _build_payload(user_id: int, **overrides: Any) -> LlmLogCreate:
    """Build a minimal-valid LlmLogCreate, letting callers override one field."""
    defaults: dict[str, Any] = dict(
        user_id=user_id,
        endpoint="insights.endgame",
        model="anthropic:claude-haiku-4-5-20251001",  # known to genai-prices per Plan 01 smoke
        prompt_version="endgame_v1",
        findings_hash="a" * 64,
        filter_context={"recency": "last_3mo"},
        flags=[],
        system_prompt="You are FlawChess's endgame analyst...",
        user_prompt="Filters: recency=last_3mo...",
        response_json={"overview": "ok", "sections": []},
        input_tokens=1200,
        output_tokens=180,
        latency_ms=2345,
        cache_hit=False,
        error=None,
    )
    defaults.update(overrides)
    return LlmLogCreate(**defaults)


@pytest.mark.asyncio
async def test_create_llm_log_inserts_and_returns_row(fresh_test_user: User) -> None:
    """Happy path: known model → cost computed, error None, row persisted."""
    data = _build_payload(fresh_test_user.id)
    row = await create_llm_log(data)

    assert row.id is not None
    assert row.created_at is not None
    assert row.user_id == fresh_test_user.id
    assert row.cost_usd > 0, "expected positive cost for known model"
    assert row.error is None


@pytest.mark.asyncio
async def test_unknown_model_records_cost_unknown_and_zero_cost(
    fresh_test_user: User,
) -> None:
    """SC #4: genai-prices LookupError → cost_usd=0, error marker set."""
    data = _build_payload(
        fresh_test_user.id,
        model="fictional-vendor:fake-model-9000",
        findings_hash="b" * 64,
        error=None,
    )
    row = await create_llm_log(data)
    assert row.cost_usd == Decimal("0")
    assert row.error == "cost_unknown:fictional-vendor:fake-model-9000"


@pytest.mark.asyncio
async def test_unknown_model_appends_to_existing_error(fresh_test_user: User) -> None:
    """SC #4: unknown model + caller error → '<caller_error>; cost_unknown:<model>'."""
    data = _build_payload(
        fresh_test_user.id,
        model="fictional-vendor:fake-model-9000",
        findings_hash="c" * 64,
        error="provider_rate_limit",
    )
    row = await create_llm_log(data)
    assert row.cost_usd == Decimal("0")
    assert row.error == "provider_rate_limit; cost_unknown:fictional-vendor:fake-model-9000"


@pytest.mark.asyncio
async def test_get_latest_log_by_hash_returns_most_recent_successful(
    test_engine: Any, fresh_test_user: User
) -> None:
    """Phase 65 cache-lookup: error IS NULL + response_json IS NOT NULL filter."""
    hash_under_test = "d" * 64
    # Insert a failed row (error set) — should NOT be returned by cache lookup.
    failed = _build_payload(
        fresh_test_user.id,
        findings_hash=hash_under_test,
        error="provider_timeout",
        response_json=None,
    )
    await create_llm_log(failed)
    # Insert a successful row — SHOULD be returned.
    successful = _build_payload(
        fresh_test_user.id,
        findings_hash=hash_under_test,
        error=None,
        response_json={"overview": "ok", "sections": []},
    )
    success_row = await create_llm_log(successful)

    # Query via a caller-supplied session (matches Phase 65 usage).
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        hit = await get_latest_log_by_hash(
            session,
            findings_hash=hash_under_test,
            prompt_version="endgame_v1",
            model="anthropic:claude-haiku-4-5-20251001",
        )
        assert hit is not None
        assert hit.id == success_row.id
        assert hit.error is None
        assert hit.response_json is not None

        miss = await get_latest_log_by_hash(
            session,
            findings_hash="z" * 64,
            prompt_version="endgame_v1",
            model="anthropic:claude-haiku-4-5-20251001",
        )
        assert miss is None
