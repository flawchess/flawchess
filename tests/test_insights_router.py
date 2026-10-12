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
    SectionInsight,
)
from app.services import insights_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INSIGHTS_ENDPOINT = "/api/insights/endgame"


def _sample_report(overview: str = "FlawChess played solidly overall.") -> EndgameInsightsReport:
    return EndgameInsightsReport(
        summary="Endgames lift your rating; rook endings need work.",
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
        prompt_version="endgame_v16",
    )


async def _fake_compute_findings(
    session: AsyncSession,
    user_id: int,
    findings_hash: str = "b" * 64,
) -> EndgameTabFindings:
    """Stub for compute_findings — returns minimal valid findings without hitting the DB."""
    return EndgameTabFindings(
        as_of=datetime.datetime.now(datetime.UTC),
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
        async def _compute_with_known_hash(session: AsyncSession, uid: int) -> EndgameTabFindings:
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
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
                    prompt_version=insights_llm._PROMPT_VERSION,
                ),
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "cache_hit"


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
        assert "retry_after_seconds" not in body

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
        assert "retry_after_seconds" not in body


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
# TestFilterFree: Phase 238 D-04, the endgame insights take no filters
# ---------------------------------------------------------------------------

# Every query string the pre-238 router either rejected (400 filters_not_supported) or
# keyed the cache on. The filter-free router declares no parameters, so all of them
# must behave exactly like no query string at all.
LEGACY_FILTER_PARAMS: list[dict[str, str]] = [
    {},
    {"time_control": "blitz"},
    {"platform": "chess.com"},
    {"from_date": "2026-01-01"},
    {"to_date": "2026-02-01"},
    {"rated": "false"},
    {"rated": "true"},
    {"opponent_gap_min": "50"},
    {"opponent_gap_min": "13", "opponent_gap_max": "27"},
    {"color": "white"},
    {"time_control": "blitz", "platform": "lichess", "from_date": "2026-01-01", "rated": "false"},
    {"unknown_param": "x"},
]
LEGACY_FILTER_PARAM_IDS = [
    "none",
    "time_control",
    "platform",
    "from_date",
    "to_date",
    "rated_false",
    "rated_true",
    "gap_stronger",
    "gap_custom",
    "color",
    "combined",
    "unknown",
]


class TestFilterFree:
    @pytest.mark.parametrize("params", LEGACY_FILTER_PARAMS, ids=LEGACY_FILTER_PARAM_IDS)
    @pytest.mark.asyncio
    async def test_query_strings_behave_like_no_query_string(
        self,
        params: dict[str, str],
        authed_user_with_session: tuple[dict[str, str], User],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """POST accepts any query string and answers 200 (never 400 filters_not_supported).

        compute_findings receives only (session, user_id): the removed filter plumbing
        cannot reach the service, so one report per user is served whatever the page
        filters were. The transient frontend (filters still sent until plan 238-07)
        therefore keeps working.
        """
        headers, user = authed_user_with_session
        fake_insights_agent(_sample_report())

        captured: dict[str, Any] = {}

        async def _capture_compute_findings(session: AsyncSession, uid: int) -> EndgameTabFindings:
            captured["user_id"] = uid
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                findings=[],
                findings_hash="z" * 64,
            )

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _capture_compute_findings)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(INSIGHTS_ENDPOINT, params=params, headers=headers)

        assert response.status_code == 200, f"expected 200 for params={params}: {response.text}"
        assert response.json()["status"] == "fresh"
        assert captured["user_id"] == user.id

    @pytest.mark.asyncio
    async def test_cache_lookup_uses_constant_opponent_strength(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The cache lookup keys on user, prompt version, model and the constant 'any'."""
        headers, user = authed_user_with_session
        fake_insights_agent(_sample_report())
        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_findings)

        lookups: list[dict[str, Any]] = []

        async def _spy_lookup(session: AsyncSession, **kwargs: Any) -> None:
            lookups.append(kwargs)
            return None

        monkeypatch.setattr(
            "app.services.insights_llm.get_latest_successful_log_for_user", _spy_lookup
        )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # opponent_gap_min=50 used to derive opponent_strength="stronger".
            response = await client.post(
                INSIGHTS_ENDPOINT, params={"opponent_gap_min": 50}, headers=headers
            )

        assert response.status_code == 200
        assert len(lookups) == 1
        assert lookups[0]["opponent_strength"] == "any"
        assert lookups[0]["opponent_strength"] == insights_llm.INSIGHTS_CACHE_OPPONENT_STRENGTH
        assert lookups[0]["user_id"] == user.id
        assert lookups[0]["prompt_version"] == insights_llm._PROMPT_VERSION

    @pytest.mark.asyncio
    async def test_log_row_written_with_constant_opponent_strength(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        fake_insights_agent: Any,
        monkeypatch: pytest.MonkeyPatch,
        test_engine: AsyncEngine,
    ) -> None:
        """A fresh report is logged with filter_context.opponent_strength == 'any'."""
        headers, user = authed_user_with_session
        fake_insights_agent(_sample_report())
        monkeypatch.setattr("app.services.insights_llm.compute_findings", _fake_compute_findings)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                INSIGHTS_ENDPOINT, params={"opponent_gap_min": 50}, headers=headers
            )
        assert response.status_code == 200

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            rows = (
                (await session.execute(select(LlmLog).where(LlmLog.user_id == user.id)))
                .scalars()
                .all()
            )
        assert len(rows) == 1
        assert rows[0].filter_context == {"opponent_strength": "any"}


# ---------------------------------------------------------------------------
# TestCachedEndpoint — GET /api/insights/endgame/cached (260508-q1z)
# ---------------------------------------------------------------------------


CACHED_ENDPOINT = "/api/insights/endgame/cached"


class TestCachedEndpoint:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(CACHED_ENDPOINT)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cache_hit_returns_200(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        monkeypatch: pytest.MonkeyPatch,
        test_engine: AsyncEngine,
    ) -> None:
        """Fresh cache row → 200 with status='cache_hit'. LLM never invoked."""
        headers, user = authed_user_with_session

        # Spy on compute_findings + LLM agent — they must NOT be called.
        compute_calls = {"n": 0}

        async def _spy_compute(session: AsyncSession, uid: int) -> EndgameTabFindings:
            compute_calls["n"] += 1
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                findings=[],
                findings_hash="x" * 64,
            )

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _spy_compute)

        # Seed a fresh cache row matching default opponent_strength="any".
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        valid_report = _sample_report()
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    user.id,
                    response_json=valid_report.model_dump(),
                    error=None,
                    model=insights_llm.settings.PYDANTIC_AI_MODEL_INSIGHTS,
                    prompt_version=insights_llm._PROMPT_VERSION,
                    opponent_strength="any",
                ),
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(CACHED_ENDPOINT, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "cache_hit"
        assert body["report"]["overview"] == "FlawChess played solidly overall."
        # Cache-only path must never run compute_findings or invoke the LLM.
        assert compute_calls["n"] == 0

    @pytest.mark.asyncio
    async def test_cache_miss_returns_404(
        self,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No cache row → 404. compute_findings not called."""
        compute_calls = {"n": 0}

        async def _spy_compute(session: AsyncSession, uid: int) -> EndgameTabFindings:
            compute_calls["n"] += 1
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                findings=[],
                findings_hash="x" * 64,
            )

        monkeypatch.setattr("app.services.insights_llm.compute_findings", _spy_compute)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(CACHED_ENDPOINT, headers=auth_headers)

        assert response.status_code == 404
        assert compute_calls["n"] == 0

    @pytest.mark.parametrize("params", LEGACY_FILTER_PARAMS, ids=LEGACY_FILTER_PARAM_IDS)
    @pytest.mark.asyncio
    async def test_query_strings_serve_the_same_cached_report(
        self,
        params: dict[str, str],
        authed_user_with_session: tuple[dict[str, str], User],
        test_engine: AsyncEngine,
    ) -> None:
        """Phase 238 D-04: filters no longer scope the cache. Any query string (the
        transient frontend still sends the page filters) returns the one per-user
        report, never a 404 caused by a filter or a custom opponent-gap range."""
        headers, user = authed_user_with_session
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    user.id,
                    response_json=_sample_report().model_dump(),
                    error=None,
                    model=insights_llm.settings.PYDANTIC_AI_MODEL_INSIGHTS,
                    prompt_version=insights_llm._PROMPT_VERSION,
                    opponent_strength="any",
                ),
            )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(CACHED_ENDPOINT, params=params, headers=headers)

        assert response.status_code == 200, f"expected 200 for params={params}"
        assert response.json()["status"] == "cache_hit"

    @pytest.mark.asyncio
    async def test_cache_lookup_uses_constant_opponent_strength(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The cached GET keys on user, prompt version, model and the constant 'any'."""
        headers, user = authed_user_with_session
        lookups: list[dict[str, Any]] = []

        async def _spy_lookup(session: AsyncSession, **kwargs: Any) -> None:
            lookups.append(kwargs)
            return None

        monkeypatch.setattr(
            "app.services.insights_llm.get_latest_successful_log_for_user", _spy_lookup
        )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                CACHED_ENDPOINT, params={"opponent_gap_min": 50}, headers=headers
            )

        assert response.status_code == 404
        assert len(lookups) == 1
        assert lookups[0]["opponent_strength"] == insights_llm.INSIGHTS_CACHE_OPPONENT_STRENGTH
        assert lookups[0]["opponent_strength"] == "any"
        assert lookups[0]["user_id"] == user.id

    @staticmethod
    async def _seed_row_and_import(
        test_engine: AsyncEngine, user: User, cache_age: datetime.timedelta
    ) -> str:
        """Seed a valid cache row `cache_age` old plus a games>0 import 1h ago; return job id."""
        from app.models.import_job import ImportJob

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        now = datetime.datetime.now(datetime.UTC)
        job_id = str(uuid.uuid4())
        async with session_maker() as session:
            await _seed(
                session,
                _make_row(
                    user.id,
                    created_at=now - cache_age,
                    response_json=_sample_report().model_dump(),
                    error=None,
                    model=insights_llm.settings.PYDANTIC_AI_MODEL_INSIGHTS,
                    prompt_version=insights_llm._PROMPT_VERSION,
                    opponent_strength="any",
                ),
            )
            session.add(
                ImportJob(
                    id=job_id,
                    user_id=user.id,
                    platform="lichess",
                    username="someone",
                    status="completed",
                    games_imported=5,
                    completed_at=now - datetime.timedelta(hours=1),
                )
            )
            await session.commit()
        return job_id

    @staticmethod
    async def _delete_import(test_engine: AsyncEngine, job_id: str) -> None:
        from sqlalchemy import delete

        from app.models.import_job import ImportJob

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            await session.execute(delete(ImportJob).where(ImportJob.id == job_id))
            await session.commit()

    async def _get_cached(self, headers: dict[str, str]) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get(CACHED_ENDPOINT, headers=headers)

    @pytest.mark.asyncio
    async def test_stale_report_still_served_after_import(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        test_engine: AsyncEngine,
    ) -> None:
        """Quick 261012-qiz: an import with games > 0 after the report does NOT
        404 the display lookup (a 404 would auto-generate a second report); the
        user refreshes explicitly via Update Insights."""
        headers, user = authed_user_with_session
        job_id = await self._seed_row_and_import(test_engine, user, datetime.timedelta(hours=2))
        try:
            response = await self._get_cached(headers)
        finally:
            await self._delete_import(test_engine, job_id)

        assert response.status_code == 200
        assert response.json()["status"] == "cache_hit"

    @pytest.mark.asyncio
    async def test_report_older_than_max_age_still_served(
        self,
        authed_user_with_session: tuple[dict[str, str], User],
        test_engine: AsyncEngine,
    ) -> None:
        """The 30-day regeneration max age does not apply to the display lookup."""
        headers, user = authed_user_with_session
        job_id = await self._seed_row_and_import(
            test_engine, user, insights_llm.INSIGHTS_CACHE_MAX_AGE + datetime.timedelta(days=1)
        )
        try:
            response = await self._get_cached(headers)
        finally:
            await self._delete_import(test_engine, job_id)

        assert response.status_code == 200
        assert response.json()["status"] == "cache_hit"
