"""Tests for Phase 65 read helpers added to llm_log_repository.py.

Covers:
- count_recent_successful_misses (CONTEXT.md D-09 / D-10): rate-limit count query.
- get_latest_report_for_user (CONTEXT.md D-11): tier-2 soft-fail lookup.

Both helpers take caller-supplied AsyncSession. Tests open a session via
async_sessionmaker(test_engine, ...) for seeding and querying — the same
pattern used in test_llm_log_repository.py's cache-lookup test (the
conftest-level async_session_maker patch only updates the module-level
name in app.core.database, not a fresh local sessionmaker bound to
test_engine). Uses fresh_test_user fixture (Phase 64) for user lifecycle
+ CASCADE cleanup.
"""

import datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.llm_log import LlmLog
from app.models.user import User
from app.repositories.llm_log_repository import (
    count_recent_successful_misses,
    get_latest_report_for_user,
)


def _make_row(
    user_id: int,
    *,
    created_at: datetime.datetime | None = None,
    error: str | None = None,
    response_json: dict[str, Any] | None = None,
    cache_hit: bool = False,
    prompt_version: str = "endgame_v1",
    model: str = "anthropic:claude-haiku-4-5-20251001",
    findings_hash: str = "a" * 64,
) -> LlmLog:
    """Build a minimal-valid LlmLog row for seeding."""
    kwargs: dict[str, Any] = dict(
        user_id=user_id,
        endpoint="insights.endgame",
        model=model,
        prompt_version=prompt_version,
        findings_hash=findings_hash,
        filter_context={"recency": "last_3mo"},
        flags=[],
        system_prompt="You are FlawChess's endgame analyst.",
        user_prompt="Filters: recency=last_3mo...",
        response_json=response_json,
        input_tokens=1200,
        output_tokens=180,
        latency_ms=2345,
        cache_hit=cache_hit,
        error=error,
        cost_usd=Decimal("0.001"),
    )
    # created_at has server_default=func.now() — override only when needed.
    # Passing it explicitly at ORM construction time wins over server_default
    # because SQLAlchemy sends the value in the INSERT rather than relying on
    # the DB default.
    if created_at is not None:
        kwargs["created_at"] = created_at
    return LlmLog(**kwargs)


async def _seed(session: AsyncSession, *rows: LlmLog) -> None:
    for row in rows:
        session.add(row)
    await session.commit()


@pytest.fixture
def now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


@pytest.fixture
def session_maker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Local sessionmaker bound to the test engine.

    Cannot reuse app.core.database.async_session_maker here — the conftest
    patches the module-level name in app.core.database, but a direct import
    of that name into this module would bind to the original object. Constructing
    a fresh sessionmaker from test_engine is the correct pattern (mirrors
    test_llm_log_repository.py line 122-123).
    """
    return async_sessionmaker(test_engine, expire_on_commit=False)


class TestCountRecentMisses:
    @pytest.mark.asyncio
    async def test_zero_when_no_rows(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            count = await count_recent_successful_misses(
                session, fresh_test_user.id, datetime.timedelta(hours=1)
            )
        assert count == 0

    @pytest.mark.asyncio
    async def test_counts_successful_misses_only(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        # Note: JSONB columns in PostgreSQL store Python None as JSON null
        # (not SQL NULL) via asyncpg. Rows with response_json=None in practice
        # ALWAYS have error set (pydantic-ai failure path), so the error IS NULL
        # filter correctly excludes them. Seeding realistic states here.
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(fresh_test_user.id, response_json={"ok": True}),  # success
                _make_row(fresh_test_user.id, response_json={"ok": True}),  # success
                # Provider error — excluded by error IS NULL filter
                _make_row(fresh_test_user.id, error="provider_error", response_json=None),
                # Cost-unknown failure — excluded by error IS NULL filter
                _make_row(
                    fresh_test_user.id,
                    error="cost_unknown:a:b",
                    response_json=None,
                ),
                # Cache hit — excluded by cache_hit IS FALSE filter
                _make_row(
                    fresh_test_user.id,
                    response_json={"ok": True},
                    cache_hit=True,
                ),
            )
            count = await count_recent_successful_misses(
                session, fresh_test_user.id, datetime.timedelta(hours=1)
            )
        assert count == 2

    @pytest.mark.asyncio
    async def test_respects_time_window(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
        now_utc: datetime.datetime,
    ) -> None:
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    fresh_test_user.id,
                    created_at=now_utc - datetime.timedelta(minutes=30),
                    response_json={"ok": True},
                ),
                _make_row(
                    fresh_test_user.id,
                    created_at=now_utc - datetime.timedelta(minutes=90),
                    response_json={"ok": True},
                ),
                _make_row(
                    fresh_test_user.id,
                    created_at=now_utc - datetime.timedelta(minutes=180),
                    response_json={"ok": True},
                ),
            )
            count = await count_recent_successful_misses(
                session, fresh_test_user.id, datetime.timedelta(hours=1)
            )
        assert count == 1

    @pytest.mark.asyncio
    async def test_excludes_other_users(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        # Seed rows under fresh_test_user.id, then query using a different
        # user_id that has no rows. Cannot seed under a non-existent user_id
        # (FK violation), so we validate scoping by querying for a non-existent
        # user_id and asserting the count is zero.
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(fresh_test_user.id, response_json={"ok": True}),
            )
            count = await count_recent_successful_misses(
                session,
                fresh_test_user.id + 999_999,
                datetime.timedelta(hours=1),
            )
        assert count == 0


class TestLatestReportForUser:
    @pytest.mark.asyncio
    async def test_returns_most_recent_matching(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
        now_utc: datetime.datetime,
    ) -> None:
        async with session_maker() as session:
            oldest = _make_row(
                fresh_test_user.id,
                created_at=now_utc - datetime.timedelta(days=2),
                response_json={"v": "old"},
            )
            middle = _make_row(
                fresh_test_user.id,
                created_at=now_utc - datetime.timedelta(days=1),
                response_json={"v": "mid"},
            )
            newest = _make_row(
                fresh_test_user.id,
                created_at=now_utc - datetime.timedelta(minutes=5),
                response_json={"v": "new"},
            )
            await _seed(session, oldest, middle, newest)
            result = await get_latest_report_for_user(
                session,
                fresh_test_user.id,
                "endgame_v1",
                "anthropic:claude-haiku-4-5-20251001",
            )
        assert result is not None
        assert result.response_json == {"v": "new"}

    @pytest.mark.asyncio
    async def test_filters_by_prompt_version(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    fresh_test_user.id,
                    prompt_version="endgame_v0",
                    response_json={"v": "old"},
                ),
                _make_row(
                    fresh_test_user.id,
                    prompt_version="endgame_v1",
                    response_json={"v": "new"},
                ),
            )
            result = await get_latest_report_for_user(
                session,
                fresh_test_user.id,
                "endgame_v1",
                "anthropic:claude-haiku-4-5-20251001",
            )
        assert result is not None
        assert result.response_json == {"v": "new"}

    @pytest.mark.asyncio
    async def test_filters_by_model(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    fresh_test_user.id,
                    model="google-gla:gemini-2.5-flash",
                    response_json={"v": "g"},
                ),
                _make_row(
                    fresh_test_user.id,
                    model="anthropic:claude-haiku-4-5-20251001",
                    response_json={"v": "a"},
                ),
            )
            result = await get_latest_report_for_user(
                session,
                fresh_test_user.id,
                "endgame_v1",
                "anthropic:claude-haiku-4-5-20251001",
            )
        assert result is not None
        assert result.response_json == {"v": "a"}

    @pytest.mark.asyncio
    async def test_none_when_no_match(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            result = await get_latest_report_for_user(
                session,
                fresh_test_user.id,
                "endgame_v1",
                "anthropic:claude-haiku-4-5-20251001",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_excludes_error_rows(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    fresh_test_user.id,
                    error="provider_error",
                    response_json=None,
                ),
            )
            result = await get_latest_report_for_user(
                session,
                fresh_test_user.id,
                "endgame_v1",
                "anthropic:claude-haiku-4-5-20251001",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_excludes_other_users(
        self,
        fresh_test_user: User,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        # Seed a successful row under fresh_test_user; query for a
        # non-existent user_id — should return None (user scoping enforced).
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    fresh_test_user.id,
                    response_json={"ok": True},
                ),
            )
            result = await get_latest_report_for_user(
                session,
                fresh_test_user.id + 999_999,
                "endgame_v1",
                "anthropic:claude-haiku-4-5-20251001",
            )
        assert result is None
