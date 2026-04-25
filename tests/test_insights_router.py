"""End-to-end router tests for POST /api/insights/endgame (Phase 65).

Tests the HTTP layer using httpx AsyncClient with ASGITransport. All LLM calls
are mocked via the fake_insights_agent fixture (TestModel) or monkeypatched
FunctionModel. No real provider calls are made (D-42).

URL: POST /api/insights/endgame
     (insights_router prefix="/insights" + @router.post("/endgame"), mounted under /api)
"""

import datetime
import uuid
from decimal import Decimal
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.main import app
from app.models.llm_log import LlmLog
from app.models.user import User
from app.schemas.insights import (
    EndgameInsightsReport,
    EndgameTabFindings,
    FilterContext,
    SectionInsight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INSIGHTS_ENDPOINT = "/api/insights/endgame"


def _sample_report(overview: str = "FlawChess played solidly overall.") -> EndgameInsightsReport:
    return EndgameInsightsReport(
        player_profile="Player around 1500 rapid, range 1200-1600 over 2 years.",
        overview=overview,
        recommendations=["Try drilling pawn endings.", "Review losses on time."],
        sections=[
            SectionInsight(
                section_id="overall",
                headline="Score Gap typical",
                bullets=["+4.2pp last 3mo"],
            )
        ],
        model_used="test",
        prompt_version="endgame_v15",
    )


async def _fake_compute_findings(
    filter_context: FilterContext,
    session: AsyncSession,
    user_id: int,
    findings_hash: str = "b" * 64,
) -> EndgameTabFindings:
    """Stub for compute_findings — returns minimal valid findings without hitting the DB."""
    return EndgameTabFindings(
        as_of=datetime.datetime.now(datetime.UTC),
        filters=filter_context,
        findings=[],
        findings_hash=findings_hash,
    )


def _make_row(
    user_id: int,
    *,
    created_at: datetime.datetime | None = None,
    error: str | None = None,
    response_json: dict[str, Any] | None = None,
    cache_hit: bool = False,
    prompt_version: str = "endgame_v1",
    model: str = "test",
    findings_hash: str = "a" * 64,
    opponent_strength: str = "any",
) -> LlmLog:
    """Build a minimal-valid LlmLog row for seeding rate-limit tests."""
    kwargs: dict[str, Any] = dict(
        user_id=user_id,
        endpoint="insights.endgame",
        model=model,
        prompt_version=prompt_version,
        findings_hash=findings_hash,
        filter_context={"opponent_strength": opponent_strength},
        user_prompt="user",
        response_json=response_json,
        input_tokens=100,
        output_tokens=50,
        latency_ms=500,
        cache_hit=cache_hit,
        error=error,
        cost_usd=Decimal("0"),
    )
    if created_at is not None:
        kwargs["created_at"] = created_at
    return LlmLog(**kwargs)


async def _seed(session: AsyncSession, *rows: LlmLog) -> None:
    for row in rows:
        session.add(row)
    await session.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def auth_headers(test_engine: AsyncEngine) -> dict[str, str]:
    """Register a fresh user and return auth headers for the test."""
    email = f"insights_router_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/auth/register", json={"email": email, "password": password})
        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login_resp.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def authed_user_with_session(
    test_engine: AsyncEngine,
) -> tuple[dict[str, str], User]:
    """Register a user, return (auth_headers, User ORM object) for seeding rows."""
    email = f"insights_ratelimit_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/auth/register", json={"email": email, "password": password})
        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login_resp.json()["access_token"]

    # Fetch the user from the DB so we can seed rows against their real ID.
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == email)  # ty: ignore[invalid-argument-type]
        )
        user = result.unique().scalar_one()

    headers = {"Authorization": f"Bearer {token}"}
    return headers, user


# ---------------------------------------------------------------------------
# TestAuth
# ---------------------------------------------------------------------------


class TestAuth:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestHappyPath
# ---------------------------------------------------------------------------


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_fresh_miss_returns_200(
        self,
        auth_headers: dict[str, str],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fresh cache miss with TestModel returns 200 with status='fresh'."""
        fake_insights_agent(_sample_report())
        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_findings)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "fresh"
        assert body["report"]["overview"] == "FlawChess played solidly overall."
        assert body["report"]["sections"][0]["section_id"] == "overall"

    @pytest.mark.asyncio
    async def test_cache_hit_returns_200(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
        test_engine: AsyncEngine,
    ) -> None:
        """Pre-seeded cache row with matching findings_hash returns status='cache_hit'.

        create_llm_log appends '; cost_unknown:test' to the error column for the
        'test' provider, so get_latest_log_by_hash (which filters error IS NULL) cannot
        find the fresh-miss row written by the first HTTP call. We therefore seed a
        pre-existing row with error=None directly — same pattern used in Plan 05 tests
        (deviation #3 documented in 65-05-SUMMARY.md).
        """
        headers, user = authed_user_with_session
        fake_insights_agent(_sample_report())

        # Stub compute_findings with a known hash so our seeded row matches
        async def _compute_with_known_hash(
            fc: FilterContext, session: AsyncSession, uid: int
        ) -> EndgameTabFindings:
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                filters=fc,
                findings=[],
                findings_hash="m" * 64,
            )

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _compute_with_known_hash)

        # Seed a row that get_latest_log_by_hash will find (error=None, matching hash)
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        valid_report = _sample_report()
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    user.id,
                    response_json=valid_report.model_dump(),
                    findings_hash="m" * 64,
                    error=None,
                    model="test",
                    prompt_version="endgame_v15",
                ),
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "cache_hit"


# ---------------------------------------------------------------------------
# TestRateLimit
# ---------------------------------------------------------------------------


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_429_when_rate_limited_without_tier2(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
        test_engine: AsyncEngine,
    ) -> None:
        """After 3 misses with no tier-2 fallback, returns 429 + error envelope."""
        headers, user = authed_user_with_session
        fake_insights_agent(_sample_report())

        # Stub compute_findings with a distinct hash (not in DB) so tier-1 always misses
        async def _fake_compute_new_hash(
            fc: FilterContext, session: AsyncSession, uid: int
        ) -> EndgameTabFindings:
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                filters=fc,
                findings=[],
                findings_hash="c" * 64,  # distinct from seeded rows
            )

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_new_hash)

        # Seed 3 successful misses using an old prompt_version so that
        # count_recent_successful_misses counts them (no prompt_version filter)
        # but get_latest_report_for_user excludes them (has prompt_version filter).
        # This creates the "rate limited without tier-2" scenario.
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    user.id,
                    response_json=_sample_report().model_dump(),
                    prompt_version="endgame_v0",  # excluded by get_latest_report_for_user
                    findings_hash="d" * 64,
                ),
                _make_row(
                    user.id,
                    response_json=_sample_report().model_dump(),
                    prompt_version="endgame_v0",
                    findings_hash="e" * 64,
                ),
                _make_row(
                    user.id,
                    response_json=_sample_report().model_dump(),
                    prompt_version="endgame_v0",
                    findings_hash="f" * 64,
                ),
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=headers)

        assert response.status_code == 429
        body = response.json()
        assert body["error"] == "rate_limit_exceeded"
        assert body["retry_after_seconds"] is not None
        assert body["retry_after_seconds"] > 0

    @pytest.mark.asyncio
    async def test_200_stale_when_rate_limited_with_tier2(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
        test_engine: AsyncEngine,
    ) -> None:
        """Rate-limited with a matching tier-2 row returns 200 + status='stale_rate_limited'."""
        headers, user = authed_user_with_session
        fake_insights_agent(_sample_report())

        async def _fake_compute_new_hash(
            fc: FilterContext, session: AsyncSession, uid: int
        ) -> EndgameTabFindings:
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                filters=fc,
                findings=[],
                findings_hash="g" * 64,  # distinct from seeded rows
            )

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_new_hash)

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        valid_report = _sample_report()
        async with session_maker() as session:
            # 3 old-version misses — fill the rate-limit bucket
            await _seed(
                session,
                _make_row(
                    user.id,
                    response_json=valid_report.model_dump(),
                    prompt_version="endgame_v0",
                    findings_hash="h" * 64,
                ),
                _make_row(
                    user.id,
                    response_json=valid_report.model_dump(),
                    prompt_version="endgame_v0",
                    findings_hash="i" * 64,
                ),
                _make_row(
                    user.id,
                    response_json=valid_report.model_dump(),
                    prompt_version="endgame_v0",
                    findings_hash="j" * 64,
                ),
                # Tier-2 fallback: current prompt_version row.
                # 260425-dxh: use opponent_strength="stronger" so the structural
                # cache lookup misses (the request uses default "any") — but
                # tier-2 fallback (get_latest_report_for_user) does NOT filter
                # by opponent_strength, so this row is still the served fallback.
                _make_row(
                    user.id,
                    response_json=valid_report.model_dump(),
                    prompt_version="endgame_v15",  # matches get_latest_report_for_user filter
                    findings_hash="k" * 64,
                    opponent_strength="stronger",
                ),
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "stale_rate_limited"
        assert body["report"]["overview"] == "FlawChess played solidly overall."


# ---------------------------------------------------------------------------
# TestErrors
# ---------------------------------------------------------------------------


class TestErrors:
    @pytest.mark.asyncio
    async def test_provider_error_returns_502(
        self,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When _run_agent returns a provider_error marker, router returns 502."""
        from pydantic_ai import Agent
        from pydantic_ai.exceptions import ModelHTTPError
        from pydantic_ai.models.function import FunctionModel
        from app.schemas.insights import EndgameInsightsReport

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_findings)

        async def _failing_model(messages: Any, info: Any) -> Any:
            raise ModelHTTPError(
                status_code=500, model_name="test", body="simulated provider error"
            )

        monkeypatch.setattr(
            "app.services.insights_llm.get_insights_agent",
            lambda: Agent(FunctionModel(_failing_model), output_type=EndgameInsightsReport),
        )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=auth_headers)

        assert response.status_code == 502
        body = response.json()
        assert body["error"] == "provider_error"
        assert body["retry_after_seconds"] is None

    @pytest.mark.asyncio
    async def test_validation_failure_returns_502(
        self,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When structured-output validation fails after retries, router returns 502."""
        from pydantic_ai import Agent
        from pydantic_ai.exceptions import UnexpectedModelBehavior
        from pydantic_ai.models.function import FunctionModel
        from app.schemas.insights import EndgameInsightsReport

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_findings)

        async def _validation_fail_model(messages: Any, info: Any) -> Any:
            raise UnexpectedModelBehavior("forced validation failure")

        monkeypatch.setattr(
            "app.services.insights_llm.get_insights_agent",
            lambda: Agent(FunctionModel(_validation_fail_model), output_type=EndgameInsightsReport),
        )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=auth_headers)

        assert response.status_code == 502
        body = response.json()
        assert body["error"] == "validation_failure"
        assert body["retry_after_seconds"] is None


# ---------------------------------------------------------------------------
# TestHideOverview
# ---------------------------------------------------------------------------


class TestHideOverview:
    @pytest.mark.asyncio
    async def test_hide_overview_strips_overview(
        self,
        auth_headers: dict[str, str],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When INSIGHTS_HIDE_OVERVIEW=True, overview is empty string in response."""
        fake_insights_agent(_sample_report())
        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_findings)

        from app.services import insights_llm

        monkeypatch.setattr(insights_llm.settings, "INSIGHTS_HIDE_OVERVIEW", True)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["report"]["overview"] == ""


# ---------------------------------------------------------------------------
# TestFilterPassing
# ---------------------------------------------------------------------------


class TestFilterPassing:
    @pytest.mark.asyncio
    async def test_query_params_flow_through(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
        test_engine: AsyncEngine,
    ) -> None:
        """opponent_strength is forwarded as FilterContext (v8: the only
        non-default filter the router accepts)."""
        headers, user = authed_user_with_session
        fake_insights_agent(_sample_report())

        captured_filter: dict[str, Any] = {}

        async def _capture_compute_findings(
            fc: FilterContext, session: AsyncSession, uid: int
        ) -> EndgameTabFindings:
            captured_filter.update(fc.model_dump())
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                filters=fc,
                findings=[],
                findings_hash="z" * 64,
            )

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _capture_compute_findings)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                INSIGHTS_ENDPOINT,
                params={"opponent_strength": "stronger"},
                headers=headers,
            )

        assert response.status_code == 200
        assert captured_filter["opponent_strength"] == "stronger"
        assert captured_filter["time_controls"] == []
        assert captured_filter["platforms"] == []

    @pytest.mark.asyncio
    async def test_rejects_non_default_filters(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        test_engine: AsyncEngine,
    ) -> None:
        """v8: router returns 400 when any filter other than opponent_strength
        is non-default. Frontend already gates the button; the server check is
        the defensive safety net."""
        headers, _user = authed_user_with_session

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            cases = [
                ({"time_control": "blitz"}, "Time control"),
                ({"platform": "chess.com"}, "Platform"),
                ({"recency": "3months"}, "Recency"),
                ({"rated": "true"}, "Rated"),
            ]
            for params, _label in cases:
                response = await client.post(INSIGHTS_ENDPOINT, params=params, headers=headers)
                assert response.status_code == 400, f"expected 400 for params={params}"
                body = response.json()
                assert body["detail"]["error"] == "filters_not_supported"
