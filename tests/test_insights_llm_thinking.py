"""Tests for the Gemini thinking-config + thinking_tokens wiring in insights_llm.

Covers:
- `_build_google_thinking_config` selects thinking_level for Gemini 3+ and
  thinking_budget for older models.
- `get_insights_agent` constructs a Google-backed Agent with GoogleModelSettings
  when the model string uses a `google-*` prefix, and a plain-string Agent
  otherwise.
- `_run_agent` extracts `thoughts_tokens` from `usage.details` and returns it
  as the new `thinking_tokens` tuple slot. None when the key is absent.
- `generate_insights` persists `thinking_tokens` to `llm_logs.thinking_tokens`
  on a fresh miss.

These tests operate at the service boundary — they do NOT hit Google. The agent
singleton is bypassed via monkeypatch where a real network call would otherwise
fire; the column-persistence test uses the `test` pydantic-ai provider.
"""

import datetime
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.config import settings
from app.schemas.insights import (
    EndgameInsightsReport,
    SectionInsight,
    EndgameTabFindings,
    FilterContext,
)
from app.services import insights_llm


def _sample_report() -> EndgameInsightsReport:
    return EndgameInsightsReport(
        overview="thinking-tokens coverage",
        sections=[
            SectionInsight(
                section_id="overall",
                headline="h",
                bullets=[],
            )
        ],
        model_used="test",
        prompt_version="endgame_v1",
    )


# ---------------------------------------------------------------------------
# _build_google_thinking_config
# ---------------------------------------------------------------------------


class TestBuildGoogleThinkingConfig:
    def test_gemini_3_uses_thinking_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "GEMINI_THINKING_LEVEL", "low")
        monkeypatch.setattr(settings, "GEMINI_INCLUDE_THOUGHTS", True)
        cfg = insights_llm._build_google_thinking_config("gemini-3-flash-preview")
        assert cfg == {"include_thoughts": True, "thinking_level": "low"}

    def test_gemini_25_uses_thinking_budget(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "GEMINI_THINKING_BUDGET", 0)
        monkeypatch.setattr(settings, "GEMINI_INCLUDE_THOUGHTS", False)
        cfg = insights_llm._build_google_thinking_config("gemini-2.5-flash")
        assert cfg == {"include_thoughts": False, "thinking_budget": 0}


# ---------------------------------------------------------------------------
# get_insights_agent — provider branching
# ---------------------------------------------------------------------------


class TestGetInsightsAgentGoogleBranch:
    def test_google_gla_model_builds_google_backed_agent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            settings,
            "PYDANTIC_AI_MODEL_INSIGHTS",
            "google-gla:gemini-3-flash-preview",
        )
        insights_llm.get_insights_agent.cache_clear()
        try:
            agent = insights_llm.get_insights_agent()
            assert isinstance(agent, Agent)
            assert isinstance(agent.model, GoogleModel)
            # Presence of model_settings (populated only by the Google branch of
            # get_insights_agent) is the behavioural signal we care about here.
            # The actual thinking_config contents are covered by the unit tests
            # on `_build_google_thinking_config` above — no need to re-assert.
            assert agent.model_settings is not None
        finally:
            insights_llm.get_insights_agent.cache_clear()

    def test_non_google_model_does_not_use_google_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "PYDANTIC_AI_MODEL_INSIGHTS", "test")
        insights_llm.get_insights_agent.cache_clear()
        try:
            agent = insights_llm.get_insights_agent()
            # For non-google providers we keep the plain-string Agent constructor,
            # so the underlying model must NOT be a GoogleModel instance.
            assert not isinstance(agent.model, GoogleModel)
        finally:
            insights_llm.get_insights_agent.cache_clear()


# ---------------------------------------------------------------------------
# _run_agent — thinking-token extraction
# ---------------------------------------------------------------------------


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int
    details: dict[str, int]


@dataclass
class _FakeResult:
    output: EndgameInsightsReport
    _usage: _FakeUsage

    def usage(self) -> _FakeUsage:  # pragma: no cover - trivial
        return self._usage


class _FakeAgent:
    """Stand-in for a pydantic-ai Agent that records the prompt and returns a fake run result."""

    def __init__(self, result: _FakeResult) -> None:
        self._result = result
        self.last_prompt: str | None = None

    async def run(self, prompt: str) -> _FakeResult:
        self.last_prompt = prompt
        return self._result


class TestRunAgentThinkingTokens:
    @pytest.mark.asyncio
    async def test_returns_thinking_tokens_when_details_has_thoughts_tokens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeAgent(
            _FakeResult(
                output=_sample_report(),
                _usage=_FakeUsage(
                    input_tokens=100,
                    output_tokens=50,
                    details={"thoughts_tokens": 17},
                ),
            )
        )
        monkeypatch.setattr(insights_llm, "get_insights_agent", lambda: fake)
        report, in_t, out_t, thinking, _latency, marker = await insights_llm._run_agent(
            "prompt", user_id=1, findings_hash="x" * 64
        )
        assert marker is None
        assert report is not None
        assert in_t == 100
        assert out_t == 50
        assert thinking == 17

    @pytest.mark.asyncio
    async def test_thinking_tokens_none_when_details_missing_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeAgent(
            _FakeResult(
                output=_sample_report(),
                _usage=_FakeUsage(input_tokens=1, output_tokens=1, details={}),
            )
        )
        monkeypatch.setattr(insights_llm, "get_insights_agent", lambda: fake)
        _r, _i, _o, thinking, _l, marker = await insights_llm._run_agent(
            "prompt", user_id=1, findings_hash="y" * 64
        )
        assert marker is None
        assert thinking is None

    @pytest.mark.asyncio
    async def test_thinking_tokens_none_when_thoughts_tokens_is_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Zero thought tokens = no thinking happened. Normalize to None so callers
        # can persist NULL rather than storing a misleading 0.
        fake = _FakeAgent(
            _FakeResult(
                output=_sample_report(),
                _usage=_FakeUsage(
                    input_tokens=1,
                    output_tokens=1,
                    details={"thoughts_tokens": 0},
                ),
            )
        )
        monkeypatch.setattr(insights_llm, "get_insights_agent", lambda: fake)
        _r, _i, _o, thinking, _l, marker = await insights_llm._run_agent(
            "prompt", user_id=1, findings_hash="z" * 64
        )
        assert marker is None
        assert thinking is None


# ---------------------------------------------------------------------------
# Integration: generate_insights persists thinking_tokens into llm_logs
# ---------------------------------------------------------------------------


class TestGenerateInsightsPersistsThinkingTokens:
    @pytest.mark.asyncio
    async def test_fresh_miss_persists_thinking_tokens_to_llm_logs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        seeded_user: Any,
        test_engine: AsyncEngine,
    ) -> None:
        """A fresh miss with thoughts_tokens in usage.details lands in llm_logs.thinking_tokens."""
        from sqlalchemy import select

        from app.models.llm_log import LlmLog

        user = seeded_user

        async def _fake_compute_findings(
            fc: FilterContext, session: Any, uid: int
        ) -> EndgameTabFindings:
            return EndgameTabFindings(
                as_of=datetime.datetime.now(datetime.UTC),
                filters=fc,
                findings=[],
                                findings_hash="t" * 64,
            )

        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings", _fake_compute_findings
        )

        fake_agent = _FakeAgent(
            _FakeResult(
                output=_sample_report(),
                _usage=_FakeUsage(
                    input_tokens=42,
                    output_tokens=24,
                    details={"thoughts_tokens": 99},
                ),
            )
        )
        monkeypatch.setattr(insights_llm, "get_insights_agent", lambda: fake_agent)

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            response = await insights_llm.generate_insights(
                filter_context=FilterContext(),
                user_id=user.id,
                session=session,
            )

        assert response.status == "fresh"

        async with session_maker() as session:
            row = (
                await session.execute(
                    select(LlmLog)
                    .where(LlmLog.user_id == user.id)
                    .order_by(LlmLog.created_at.desc())
                    .limit(1)
                )
            ).scalar_one()

        assert row.thinking_tokens == 99
        assert row.input_tokens == 42
        assert row.output_tokens == 24
