"""Tests for app/services/insights_llm.py — Phase 65 orchestration service.

Covers:
- LLM-01: Agent returns validated EndgameInsightsReport via TestModel.
- LLM-02: Startup validation (UserError on empty model, ValueError on bad provider).
- INS-04: Cache key = (findings_hash, prompt_version, model).
- INS-05: 3-miss rate-limit boundary, tier-2 soft-fail, window rollover.
- INS-06: Overview always populated in log; hidden only in response when flag set.

No real provider calls — all agent calls use TestModel or FunctionModel per D-38/D-39.
Rate-limit seeding uses fresh_test_user + own-session pattern (mirrors Plan 04 tests).
compute_findings is monkeypatched for all orchestration tests to avoid DB-heavy Phase 63.
"""

import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.llm_log import LlmLog
from app.models.user import User
from app.schemas.insights import (
    EndgameInsightsReport,
    EndgameTabFindings,
    FilterContext,
    SectionInsight,
    SubsectionFinding,
    TimePoint,
)
from app.services import insights_llm
from app.services.insights_llm import (
    INSIGHTS_MISSES_PER_HOUR,
    InsightsProviderError,
    InsightsRateLimitExceeded,
    InsightsValidationFailure,
    _SYSTEM_PROMPT,
    _assemble_user_prompt,
    _maybe_strip_overview,
    generate_insights,
    get_insights_agent,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _sample_report(overview: str = "FlawChess played well overall.") -> EndgameInsightsReport:
    return EndgameInsightsReport(
        overview=overview,
        sections=[
            SectionInsight(
                section_id="overall",
                headline="Score Gap is typical",
                bullets=["+4.2pp gap on last_3mo"],
            ),
        ],
        model_used="test",
        prompt_version="endgame_v6",
    )


def _sample_filter_context(**kwargs: Any) -> FilterContext:
    defaults: dict[str, Any] = {
        "recency": "all_time",
        "opponent_strength": "any",
        "color": "all",
        "time_controls": [],
        "platforms": [],
        "rated_only": False,
    }
    defaults.update(kwargs)
    return FilterContext(**defaults)


def _make_log_row(
    user_id: int,
    *,
    created_at: datetime.datetime | None = None,
    error: str | None = None,
    response_json: dict[str, Any] | None = None,
    cache_hit: bool = False,
    prompt_version: str = "endgame_v6",
    model: str = "test",
    findings_hash: str = "b" * 64,
) -> LlmLog:
    """Build a minimal LlmLog row for seeding rate-limit tests."""
    kwargs: dict[str, Any] = dict(
        user_id=user_id,
        endpoint="insights.endgame",
        model=model,
        prompt_version=prompt_version,
        findings_hash=findings_hash,
        filter_context={"recency": "all_time"},
        flags=[],
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


def _fake_findings(
    filter_context: FilterContext,
    findings_hash: str = "b" * 64,
    findings: list[SubsectionFinding] | None = None,
) -> EndgameTabFindings:
    return EndgameTabFindings(
        as_of=datetime.datetime.now(datetime.UTC),
        filters=filter_context,
        findings=findings or [],
        findings_hash=findings_hash,
    )


async def _fake_compute_findings(
    filter_context: FilterContext,
    session: AsyncSession,
    user_id: int,
    findings_hash: str = "b" * 64,
) -> EndgameTabFindings:
    return _fake_findings(filter_context, findings_hash=findings_hash)


# ---------------------------------------------------------------------------
# TestStartupValidation
# ---------------------------------------------------------------------------


class TestStartupValidation:
    def test_empty_model_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pydantic_ai.exceptions import UserError

        insights_llm.get_insights_agent.cache_clear()
        monkeypatch.setattr(insights_llm.settings, "PYDANTIC_AI_MODEL_INSIGHTS", "")
        with pytest.raises(UserError):
            insights_llm.get_insights_agent()
        insights_llm.get_insights_agent.cache_clear()

    def test_bad_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        insights_llm.get_insights_agent.cache_clear()
        monkeypatch.setattr(
            insights_llm.settings, "PYDANTIC_AI_MODEL_INSIGHTS", "bogus-provider:foo"
        )
        with pytest.raises(ValueError):
            insights_llm.get_insights_agent()
        insights_llm.get_insights_agent.cache_clear()

    def test_valid_test_model_constructs(self) -> None:
        # conftest sets PYDANTIC_AI_MODEL_INSIGHTS="test"; cache may hold it already.
        insights_llm.get_insights_agent.cache_clear()
        agent = get_insights_agent()
        assert agent is not None
        insights_llm.get_insights_agent.cache_clear()


# ---------------------------------------------------------------------------
# TestPromptAssembly
# ---------------------------------------------------------------------------


class TestPromptAssembly:
    def test_user_prompt_shape(self) -> None:
        filters = _sample_filter_context(
            recency="3months", time_controls=["blitz"], platforms=["chess.com"]
        )
        non_timeline = SubsectionFinding(
            subsection_id="overall",
            parent_subsection_id=None,
            window="all_time",
            metric="score_gap",
            value=4.2,
            zone="typical",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=487,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=None,
        )
        timeline = SubsectionFinding(
            subsection_id="score_gap_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="score_gap",
            value=3.5,
            zone="typical",
            trend="improving",
            weekly_points_in_window=8,
            sample_size=8,
            sample_quality="adequate",
            is_headline_eligible=True,
            dimension=None,
            series=[
                TimePoint(bucket_start="2026-01-06", value=2.1, n=12),
                TimePoint(bucket_start="2026-01-13", value=3.5, n=14),
            ],
        )
        tab_findings = _fake_findings(filters, findings=[non_timeline, timeline])
        prompt = _assemble_user_prompt(tab_findings)

        assert "Filters:" in prompt
        assert "Flags:" not in prompt
        assert "## Subsection: overall" in prompt
        assert "## Subsection: score_gap_timeline" in prompt
        assert "### Series (" in prompt
        assert "2026-01-06" in prompt
        assert "2026-01-13" in prompt

    def test_system_prompt_loaded_from_file(self) -> None:
        """_SYSTEM_PROMPT is the markdown file contents + auto-generated zone appendix.

        Per 260422-tnb B2: _SYSTEM_PROMPT at module load = file contents + a
        deterministic `## Zone thresholds` appendix sourced from ZONE_REGISTRY
        and BUCKETED_ZONE_REGISTRY. The appendix is appended so the file
        content must be a strict prefix.
        """
        from pathlib import Path

        import app.services.insights_llm as mod

        file_path = Path(mod.__file__).parent.parent / "prompts" / "endgame_insights.md"
        file_content = file_path.read_text(encoding="utf-8")
        assert _SYSTEM_PROMPT.startswith(file_content)
        assert "## Zone thresholds" in _SYSTEM_PROMPT
        assert len(_SYSTEM_PROMPT) > len(file_content)

    def test_filter_excludes_color_and_rated_only(self) -> None:
        filters = _sample_filter_context(color="white", rated_only=True)
        tab_findings = _fake_findings(filters)
        prompt = _assemble_user_prompt(tab_findings)

        assert "color=" not in prompt
        assert "rated_only=" not in prompt
        assert "white" not in prompt
        assert "rated" not in prompt

    def test_assemble_user_prompt_drops_nan_findings(self) -> None:
        """A2 (260422-tnb): NaN values and thin empty findings are filtered out."""
        filters = _sample_filter_context()
        normal = SubsectionFinding(
            subsection_id="overall",
            parent_subsection_id=None,
            window="all_time",
            metric="score_gap",
            value=0.05,
            zone="typical",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=120,
            sample_quality="adequate",
            is_headline_eligible=True,
            dimension=None,
            series=None,
        )
        # Empty finding mirrors _empty_finding output: NaN value, thin, n=0.
        empty = SubsectionFinding(
            subsection_id="endgame_metrics",
            parent_subsection_id=None,
            window="last_3mo",
            metric="recovery_save_pct",
            value=float("nan"),
            zone="typical",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=0,
            sample_quality="thin",
            is_headline_eligible=False,
            dimension={"bucket": "recovery"},
            series=None,
        )
        tab_findings = _fake_findings(filters, findings=[normal, empty])
        prompt = _assemble_user_prompt(tab_findings)

        # Must not leak NaN into the prompt (was: "+nan | typical | 0 games | thin").
        assert "nan" not in prompt.lower()
        # The only bullet line should be the normal finding.
        bullet_lines = [line for line in prompt.splitlines() if line.startswith("- ")]
        assert len(bullet_lines) == 1
        assert "score_gap" in bullet_lines[0]

    def test_assemble_user_prompt_groups_by_subsection(self) -> None:
        """C1 (260422-tnb): multiple findings under one subsection share a single header."""
        from typing import cast
        from app.schemas.insights import MetricId

        filters = _sample_filter_context()

        def _em(metric: str, bucket: str, value: float) -> SubsectionFinding:
            return SubsectionFinding(
                subsection_id="endgame_metrics",
                parent_subsection_id=None,
                window="all_time",
                metric=cast(MetricId, metric),
                value=value,
                zone="typical",
                trend="n_a",
                weekly_points_in_window=0,
                sample_size=120,
                sample_quality="adequate",
                is_headline_eligible=True,
                dimension={"bucket": bucket},
                series=None,
            )

        findings_list = [
            _em("conversion_win_pct", "conversion", 0.66),
            _em("parity_score_pct", "parity", 0.50),
            _em("recovery_save_pct", "recovery", 0.30),
        ]
        tab_findings = _fake_findings(filters, findings=findings_list)
        prompt = _assemble_user_prompt(tab_findings)

        assert prompt.count("## Subsection: endgame_metrics") == 1
        bullet_lines = [line for line in prompt.splitlines() if line.startswith("- ")]
        assert len(bullet_lines) == 3

    def test_assemble_user_prompt_filters_sparse_series_points(self) -> None:
        """A4 (260422-tnb): series points with n < MIN_BUCKET_N (=3) are dropped."""
        filters = _sample_filter_context()
        timeline = SubsectionFinding(
            subsection_id="score_gap_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="score_gap",
            value=0.08,
            zone="typical",
            trend="improving",
            weekly_points_in_window=4,
            sample_size=4,
            sample_quality="thin",
            is_headline_eligible=False,
            dimension=None,
            series=[
                TimePoint(bucket_start="2026-02-02", value=0.01, n=1),  # drop
                TimePoint(bucket_start="2026-02-09", value=0.04, n=5),  # keep
                TimePoint(bucket_start="2026-02-16", value=0.06, n=2),  # drop
                TimePoint(bucket_start="2026-02-23", value=0.08, n=10),  # keep
            ],
        )
        tab_findings = _fake_findings(filters, findings=[timeline])
        prompt = _assemble_user_prompt(tab_findings)

        # Retained points must appear.
        assert "2026-02-09" in prompt
        assert "(n=5)" in prompt
        assert "2026-02-23" in prompt
        assert "(n=10)" in prompt
        # Dropped points must NOT appear.
        assert "2026-02-02" not in prompt
        assert "(n=1)" not in prompt
        assert "2026-02-16" not in prompt
        assert "(n=2)" not in prompt

    def test_assemble_user_prompt_skips_time_pressure_vs_performance_subsection_finding(
        self,
    ) -> None:
        """The single-value time_pressure_vs_performance finding is dropped.

        The 10-bucket chart is rendered separately via
        `_format_time_pressure_chart_block`; the scalar placeholder finding
        must NOT appear as a `## Subsection` row (it would be a meaningless
        weighted-mean number labelled as `avg_clock_diff_pct`).
        """
        filters = _sample_filter_context()
        hidden = SubsectionFinding(
            subsection_id="time_pressure_vs_performance",
            parent_subsection_id=None,
            window="all_time",
            metric="avg_clock_diff_pct",
            value=0.46,
            zone="typical",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=2940,
            sample_quality="rich",
            is_headline_eligible=False,
            dimension=None,
            series=None,
        )
        tab_findings = _fake_findings(filters, findings=[hidden])
        prompt = _assemble_user_prompt(tab_findings)
        assert "## Subsection: time_pressure_vs_performance" not in prompt

    def test_assemble_user_prompt_renders_time_pressure_chart_block(self) -> None:
        """The 10-bucket chart is rendered as a `## Chart` table.

        Mirrors the frontend's MIN_GAMES_FOR_RELIABLE_STATS=10 gate: buckets
        where both sides have <10 games are dropped, and a side with <10
        games renders as "—".
        """
        from app.schemas.endgames import TimePressureBucketPoint, TimePressureChartResponse

        user_series = [
            TimePressureBucketPoint(
                bucket_index=i,
                bucket_label=f"{i * 10}-{(i + 1) * 10}%",
                score=0.30 + 0.05 * i,  # climbs from 0.30 to 0.75
                game_count=20 if i >= 2 else 3,  # first two buckets thin
            )
            for i in range(10)
        ]
        opp_series = [
            TimePressureBucketPoint(
                bucket_index=i,
                bucket_label=f"{i * 10}-{(i + 1) * 10}%",
                score=0.45 + 0.03 * i,
                game_count=20 if i >= 2 else 3,
            )
            for i in range(10)
        ]
        chart = TimePressureChartResponse(
            user_series=user_series,
            opp_series=opp_series,
            total_endgame_games=487,
        )
        filters = _sample_filter_context()
        tab_findings = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=filters,
            findings=[],
            time_pressure_chart=chart,
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab_findings)

        assert "## Chart: time_pressure_vs_performance" in prompt
        assert "Total endgame games: 487" in prompt
        assert "| time_left | user_score | user_n | opp_score | opp_n |" in prompt
        # Buckets with >=10 games on both sides render scores.
        assert "20-30%" in prompt
        assert "90-100%" in prompt
        # Buckets where both sides have <10 games are dropped entirely.
        assert "0-10%" not in prompt
        assert "10-20%" not in prompt

    def test_assemble_user_prompt_omits_chart_block_when_empty(self) -> None:
        """Chart block is omitted when total_endgame_games == 0 or chart is None."""
        from app.schemas.endgames import TimePressureChartResponse

        filters = _sample_filter_context()
        empty_chart = TimePressureChartResponse(
            user_series=[], opp_series=[], total_endgame_games=0
        )
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=filters,
            findings=[],
            time_pressure_chart=empty_chart,
            findings_hash="b" * 64,
        )
        assert "## Chart: time_pressure_vs_performance" not in _assemble_user_prompt(tab)

        tab_none = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=filters,
            findings=[],
            time_pressure_chart=None,
            findings_hash="b" * 64,
        )
        assert "## Chart: time_pressure_vs_performance" not in _assemble_user_prompt(tab_none)

    def test_assemble_user_prompt_renders_overall_wdl_chart_block(self) -> None:
        """The endgame-vs-non-endgame WDL block is rendered when performance is set."""
        from app.schemas.endgames import EndgamePerformanceResponse, EndgameWDLSummary

        perf = EndgamePerformanceResponse(
            endgame_wdl=EndgameWDLSummary(
                wins=120,
                draws=40,
                losses=80,
                total=240,
                win_pct=50.0,
                draw_pct=16.7,
                loss_pct=33.3,
            ),
            non_endgame_wdl=EndgameWDLSummary(
                wins=300,
                draws=50,
                losses=350,
                total=700,
                win_pct=42.9,
                draw_pct=7.1,
                loss_pct=50.0,
            ),
            endgame_win_rate=50.0,
        )
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[],
            overall_performance=perf,
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab)

        assert "## Chart: overall_wdl (all_time)" in prompt
        assert "| series      | games | win_pct | draw_pct | loss_pct | score_pct |" in prompt
        assert "| endgame     | 240" in prompt
        assert "| non_endgame | 700" in prompt
        # v6 0-100 scale: Score % = (W + 0.5*D)/total * 100.
        # endgame = 140/240*100 = 58.3, non-endgame = 325/700*100 = 46.4
        assert "58.3" in prompt
        assert "46.4" in prompt

    def test_assemble_user_prompt_omits_overall_wdl_when_thin(self) -> None:
        """Rows below the 10-game floor are dropped; block omitted if all dropped."""
        from app.schemas.endgames import EndgamePerformanceResponse, EndgameWDLSummary

        perf = EndgamePerformanceResponse(
            endgame_wdl=EndgameWDLSummary(
                wins=2,
                draws=1,
                losses=1,
                total=4,
                win_pct=50.0,
                draw_pct=25.0,
                loss_pct=25.0,
            ),
            non_endgame_wdl=EndgameWDLSummary(
                wins=0,
                draws=0,
                losses=0,
                total=0,
                win_pct=0.0,
                draw_pct=0.0,
                loss_pct=0.0,
            ),
            endgame_win_rate=50.0,
        )
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[],
            overall_performance=perf,
            findings_hash="b" * 64,
        )
        assert "## Chart: overall_wdl" not in _assemble_user_prompt(tab)

        # None case
        tab_none = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[],
            overall_performance=None,
            findings_hash="b" * 64,
        )
        assert "## Chart: overall_wdl" not in _assemble_user_prompt(tab_none)

    def test_assemble_user_prompt_renders_type_wdl_chart_block(self) -> None:
        """Per-endgame-type WDL block is rendered, sorted by total descending."""
        from app.schemas.endgames import ConversionRecoveryStats, EndgameCategoryStats

        # Helper conversion stub — values irrelevant for the WDL block.
        conv_stub = ConversionRecoveryStats.model_construct(
            conversion_games=0,
            conversion_wins=0,
            conversion_pct=0.0,
            recovery_games=0,
            recovery_saves=0,
            recovery_pct=0.0,
        )
        categories = [
            EndgameCategoryStats(
                endgame_class="rook",
                label="Rook",
                wins=50,
                draws=20,
                losses=30,
                total=100,
                win_pct=50.0,
                draw_pct=20.0,
                loss_pct=30.0,
                conversion=conv_stub,
            ),
            EndgameCategoryStats(
                endgame_class="pawn",
                label="Pawn",
                wins=15,
                draws=5,
                losses=10,
                total=30,
                win_pct=50.0,
                draw_pct=16.7,
                loss_pct=33.3,
                conversion=conv_stub,
            ),
            EndgameCategoryStats(
                endgame_class="queen",
                label="Queen",
                wins=2,
                draws=0,
                losses=1,
                total=3,  # below 10-game floor — dropped
                win_pct=66.7,
                draw_pct=0.0,
                loss_pct=33.3,
                conversion=conv_stub,
            ),
        ]
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[],
            type_categories=categories,
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab)

        assert "## Chart: results_by_endgame_type_wdl (all_time)" in prompt
        assert "| endgame_class | games | win_pct | draw_pct | loss_pct | score_pct |" in prompt
        # Sorted by total descending: rook (100) before pawn (30).
        rook_idx = prompt.index("| rook")
        pawn_idx = prompt.index("| pawn")
        assert rook_idx < pawn_idx
        # Queen (n=3) dropped by 10-game floor.
        assert "| queen" not in prompt

    def test_pawnless_findings_are_filtered(self) -> None:
        """v6: pawnless-dimensioned findings and chart rows are stripped.

        The UI hides pawnless in ENDGAME_CLASS_LABELS (Endgames.tsx); the LLM
        must not narrate a type the user cannot see. Applies to both per-type
        findings (dimension.endgame_class == "pawnless") and the
        results_by_endgame_type_wdl chart row.
        """
        from typing import cast

        from app.schemas.endgames import ConversionRecoveryStats, EndgameCategoryStats
        from app.schemas.insights import MetricId

        filters = _sample_filter_context()
        rook_finding = SubsectionFinding(
            subsection_id="results_by_endgame_type",
            parent_subsection_id=None,
            window="all_time",
            metric="win_rate",
            value=0.41,
            zone="weak",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=100,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension={"endgame_class": "rook"},
            series=None,
        )
        pawnless_finding = SubsectionFinding(
            subsection_id="results_by_endgame_type",
            parent_subsection_id=None,
            window="all_time",
            metric=cast(MetricId, "win_rate"),
            value=0.58,
            zone="strong",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=19,
            sample_quality="adequate",
            is_headline_eligible=True,
            dimension={"endgame_class": "pawnless"},
            series=None,
        )
        conv_stub = ConversionRecoveryStats.model_construct(
            conversion_games=0,
            conversion_wins=0,
            conversion_pct=0.0,
            recovery_games=0,
            recovery_saves=0,
            recovery_pct=0.0,
        )
        categories = [
            EndgameCategoryStats(
                endgame_class="rook",
                label="Rook",
                wins=41,
                draws=12,
                losses=47,
                total=100,
                win_pct=41.0,
                draw_pct=12.0,
                loss_pct=47.0,
                conversion=conv_stub,
            ),
            EndgameCategoryStats(
                endgame_class="pawnless",
                label="Pawnless",
                wins=11,
                draws=5,
                losses=3,
                total=19,
                win_pct=57.9,
                draw_pct=26.3,
                loss_pct=15.8,
                conversion=conv_stub,
            ),
        ]
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=filters,
            findings=[rook_finding, pawnless_finding],
            type_categories=categories,
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab)

        assert "endgame_class=rook" in prompt
        assert "endgame_class=pawnless" not in prompt
        assert "| rook" in prompt
        assert "| pawnless" not in prompt

    def test_bullet_includes_inline_zone_bounds(self) -> None:
        """v5: every finding bullet renders `(typical LO to UP)` next to its zone.

        Covers scalar (score_gap), bucketed (conversion_win_pct), and
        lower_is_better (net_timeout_rate) registry paths. The inline shorthand
        lets the LLM judge proximity to a zone edge without consulting the
        global appendix.
        """
        from typing import cast

        from app.schemas.insights import MetricId

        filters = _sample_filter_context()
        scalar = SubsectionFinding(
            subsection_id="overall",
            parent_subsection_id=None,
            window="all_time",
            metric="score_gap",
            value=-0.15,
            zone="weak",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=200,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=None,
        )
        bucketed = SubsectionFinding(
            subsection_id="endgame_metrics",
            parent_subsection_id=None,
            window="all_time",
            metric=cast(MetricId, "conversion_win_pct"),
            value=0.65,
            zone="weak",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=100,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension={"bucket": "conversion"},
            series=None,
        )
        timeout = SubsectionFinding(
            subsection_id="time_pressure_at_entry",
            parent_subsection_id=None,
            window="all_time",
            metric="net_timeout_rate",
            value=-12.82,
            zone="weak",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=2940,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=None,
        )
        tab = _fake_findings(filters, findings=[scalar, bucketed, timeout])
        prompt = _assemble_user_prompt(tab)

        # v6 0-100 scale: score_gap band is -10.0 to +10.0 pp.
        assert "weak (typical -10.0 to +10.0)" in prompt
        # v6 0-100 scale: conversion bucket band is +65.0 to +75.0.
        assert "weak (typical +65.0 to +75.0)" in prompt
        # lower_is_better metric: net_timeout_rate band (already pp) now rendered at .1f.
        assert "weak (typical -5.0 to +5.0, lower is better)" in prompt

    def test_overall_subsection_dropped_when_wdl_chart_present(self) -> None:
        """v5 C4: scalar `overall` subsection is omitted when overall_wdl renders.

        The 2-row chart already carries the endgame-vs-non-endgame framing;
        keeping the scalar `score_gap` bullet alongside invited the LLM to
        anchor on a misleading one-number narrative.
        """
        from app.schemas.endgames import EndgamePerformanceResponse, EndgameWDLSummary

        scalar = SubsectionFinding(
            subsection_id="overall",
            parent_subsection_id=None,
            window="all_time",
            metric="score_gap",
            value=-0.15,
            zone="weak",
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=200,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=None,
        )
        perf = EndgamePerformanceResponse(
            endgame_wdl=EndgameWDLSummary(
                wins=120,
                draws=40,
                losses=80,
                total=240,
                win_pct=50.0,
                draw_pct=16.7,
                loss_pct=33.3,
            ),
            non_endgame_wdl=EndgameWDLSummary(
                wins=300,
                draws=50,
                losses=350,
                total=700,
                win_pct=42.9,
                draw_pct=7.1,
                loss_pct=50.0,
            ),
            endgame_win_rate=50.0,
        )
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[scalar],
            overall_performance=perf,
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab)

        # Chart renders.
        assert "## Chart: overall_wdl" in prompt
        # Scalar `overall` subsection dropped — no subsection header, no bullet.
        assert "## Subsection: overall\n" not in prompt
        assert "- score_gap (all_time):" not in prompt

        # Control: when the chart is absent (no overall_performance), the
        # scalar overall subsection IS kept as a fallback.
        tab_no_chart = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[scalar],
            overall_performance=None,
            findings_hash="b" * 64,
        )
        prompt_no_chart = _assemble_user_prompt(tab_no_chart)
        assert "## Subsection: overall" in prompt_no_chart
        assert "- score_gap (all_time):" in prompt_no_chart

    def test_all_time_series_trimmed_to_last_12_points(self) -> None:
        """v5 C6: all_time Series block is capped at the most-recent 12 buckets.

        Older monthly history consumes tokens without narrative value — the
        Series interpretation rule already tells the LLM to focus on
        multi-bucket direction, not deep history.
        """
        filters = _sample_filter_context()
        # 20 consecutive monthly buckets ending 2025-10: 2024-03 .. 2025-10.
        bucket_starts: list[str] = []
        cursor = datetime.date(2024, 3, 1)
        while cursor <= datetime.date(2025, 10, 1):
            bucket_starts.append(cursor.isoformat())
            # next month (first-of-month arithmetic)
            year, month = cursor.year, cursor.month + 1
            if month > 12:
                year += 1
                month = 1
            cursor = datetime.date(year, month, 1)
        assert len(bucket_starts) == 20
        timeline = SubsectionFinding(
            subsection_id="score_gap_timeline",
            parent_subsection_id=None,
            window="all_time",
            metric="score_gap",
            value=-0.08,
            zone="typical",
            trend="stable",
            weekly_points_in_window=20,
            sample_size=20,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=[TimePoint(bucket_start=bs, value=-0.05, n=20) for bs in bucket_starts],
        )
        tab = _fake_findings(filters, findings=[timeline])
        prompt = _assemble_user_prompt(tab)

        # Most recent 12 buckets are retained: 2024-11 .. 2025-10.
        assert "2025-10-01" in prompt
        assert "2024-11-01" in prompt
        # Oldest 8 buckets are dropped: 2024-01 .. 2024-10.
        assert "2024-01-01" not in prompt
        assert "2024-10-01" not in prompt
        # Exactly 12 series value lines (bucket_start entries, not the header).
        series_lines = [ln for ln in prompt.splitlines() if ln.startswith(("2024-", "2025-"))]
        assert len(series_lines) == 12

    def test_last_3mo_series_block_skipped_when_all_time_series_present(self) -> None:
        """v5 C5: last_3mo Series block is skipped when all_time Series is emitted.

        The last_3mo scalar bullet stays (it's the current-state signal); only
        the weekly Series block is suppressed. The all_time series already
        rolls up those weeks at monthly resolution.
        """
        filters = _sample_filter_context()
        all_time_series = [
            TimePoint(bucket_start=f"2025-{month:02d}-01", value=-0.05, n=20)
            for month in range(1, 11)
        ]
        last_3mo_series = [
            TimePoint(bucket_start=f"2026-02-{day:02d}", value=-0.03, n=12)
            for day in (2, 9, 16, 23)
        ]
        all_time_finding = SubsectionFinding(
            subsection_id="score_gap_timeline",
            parent_subsection_id=None,
            window="all_time",
            metric="score_gap",
            value=-0.05,
            zone="typical",
            trend="stable",
            weekly_points_in_window=10,
            sample_size=200,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=all_time_series,
        )
        last_3mo_finding = SubsectionFinding(
            subsection_id="score_gap_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="score_gap",
            value=-0.03,
            zone="typical",
            trend="improving",
            weekly_points_in_window=4,
            sample_size=40,
            sample_quality="adequate",
            is_headline_eligible=True,
            dimension=None,
            series=last_3mo_series,
        )
        tab = _fake_findings(filters, findings=[all_time_finding, last_3mo_finding])
        prompt = _assemble_user_prompt(tab)

        # Both scalar bullets stay.
        assert "- score_gap (all_time):" in prompt
        assert "- score_gap (last_3mo):" in prompt
        # all_time Series header + points present.
        assert "### Series (score_gap, all_time, monthly)" in prompt
        assert "2025-10-01" in prompt
        # last_3mo Series header + points suppressed.
        assert "### Series (score_gap, last_3mo, weekly)" not in prompt
        assert "2026-02-09" not in prompt

        # Control: with only last_3mo (no all_time series), last_3mo Series
        # block is kept — suppression is conditional on the all_time twin.
        tab_solo = _fake_findings(filters, findings=[last_3mo_finding])
        prompt_solo = _assemble_user_prompt(tab_solo)
        assert "### Series (score_gap, last_3mo, weekly)" in prompt_solo
        assert "2026-02-09" in prompt_solo


class TestV6Enrichments:
    """Batch 2 (v6) payload enrichments: stale markers, trend tags, asymmetry
    flags, low-time gap scalar, all_time↔last_3mo delta, payload summary."""

    def _finding(
        self,
        *,
        subsection_id: str,
        metric: str,
        window: str,
        value: float,
        zone: str = "typical",
        sample_size: int = 100,
        sample_quality: str = "rich",
        dimension: dict[str, str] | None = None,
        series: list[TimePoint] | None = None,
    ) -> SubsectionFinding:
        from typing import cast

        from app.schemas.insights import MetricId, SampleQuality, SubsectionId, Window, Zone

        return SubsectionFinding(
            subsection_id=cast(SubsectionId, subsection_id),
            parent_subsection_id=None,
            window=cast(Window, window),
            metric=cast(MetricId, metric),
            value=value,
            zone=cast(Zone, zone),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=sample_size,
            sample_quality=cast(SampleQuality, sample_quality),
            is_headline_eligible=True,
            dimension=dimension,
            series=series,
        )

    def test_payload_summary_block_rendered(self) -> None:
        """`## Payload summary` prepends the prompt with macro context."""
        from app.schemas.endgames import EndgamePerformanceResponse, EndgameWDLSummary

        filters = _sample_filter_context()
        series_finding = self._finding(
            subsection_id="score_gap_timeline",
            metric="score_gap",
            window="all_time",
            value=-0.05,
            series=[
                TimePoint(bucket_start=f"2026-01-{week:02d}", value=-0.05, n=50)
                for week in (5, 12, 19, 26)
            ],
        )
        perf = EndgamePerformanceResponse(
            endgame_wdl=EndgameWDLSummary(
                wins=120, draws=40, losses=80, total=240, win_pct=50.0, draw_pct=16.7, loss_pct=33.3
            ),
            non_endgame_wdl=EndgameWDLSummary(
                wins=300, draws=50, losses=350, total=700, win_pct=42.9, draw_pct=7.1, loss_pct=50.0
            ),
            endgame_win_rate=50.0,
        )
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=filters,
            findings=[series_finding],
            overall_performance=perf,
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab)
        assert "## Payload summary" in prompt
        assert "Total games in scope: 940" in prompt
        assert "Newest bucket across all series: 2026-01-26" in prompt
        # Summary appears BEFORE the Filters line.
        assert prompt.index("## Payload summary") < prompt.index("Filters:")

    def test_stale_marker_on_old_endgame_elo_gap(self) -> None:
        """A combo whose series trails >6mo behind the newest bucket is STALE-tagged."""
        filters = _sample_filter_context()
        old_series = [
            TimePoint(bucket_start=f"2023-{month:02d}-01", value=0.6, n=15)
            for month in (9, 10, 11, 12)
        ]
        new_series = [
            TimePoint(bucket_start=f"2026-{month:02d}-01", value=-0.42, n=20) for month in (1, 2)
        ] + [
            TimePoint(bucket_start=f"2025-{month:02d}-01", value=-0.42, n=20) for month in (11, 12)
        ]
        new_series.sort(key=lambda pt: pt.bucket_start)
        blitz_old = self._finding(
            subsection_id="endgame_elo_timeline",
            metric="endgame_elo_gap",
            window="all_time",
            value=60.0,
            dimension={"platform": "chess.com", "time_control": "blitz"},
            series=old_series,
            sample_size=60,
        )
        rapid_new = self._finding(
            subsection_id="endgame_elo_timeline",
            metric="endgame_elo_gap",
            window="all_time",
            value=-42.0,
            dimension={"platform": "chess.com", "time_control": "rapid"},
            series=new_series,
            sample_size=70,
        )
        tab = _fake_findings(filters, findings=[blitz_old, rapid_new])
        prompt = _assemble_user_prompt(tab)

        # Stale blitz combo carries the marker, rapid combo does not.
        blitz_line = next(ln for ln in prompt.splitlines() if "time_control=blitz" in ln)
        rapid_line = next(ln for ln in prompt.splitlines() if "time_control=rapid" in ln)
        assert "STALE:" in blitz_line
        assert "STALE:" not in rapid_line
        # Summary counts the stale series.
        assert "Stale series" in prompt

    def test_trend_tag_emitted_under_series_header(self) -> None:
        """A `# trend: direction=...` line appears right after the Series header."""
        filters = _sample_filter_context()
        series = [
            TimePoint(bucket_start=f"2026-01-{day:02d}", value=v, n=30)
            for day, v in zip((5, 12, 19, 26), (-0.25, -0.20, -0.10, -0.02), strict=False)
        ]
        finding = self._finding(
            subsection_id="score_gap_timeline",
            metric="score_gap",
            window="last_3mo",
            value=-0.02,
            series=series,
        )
        tab = _fake_findings(filters, findings=[finding])
        prompt = _assemble_user_prompt(tab)

        lines = prompt.splitlines()
        series_idx = lines.index("### Series (score_gap, last_3mo, weekly)")
        trend_line = lines[series_idx + 1]
        assert trend_line.startswith("# trend: direction=")
        assert "latest=-2.0" in trend_line or "latest=+-" in trend_line or "latest=" in trend_line
        assert "improving" in trend_line  # latest -2 vs prior-mean -18.3 → improving

    def test_asymmetry_line_emitted_for_strong_weak_split(self) -> None:
        """Pawn with strong conversion + weak recovery emits `# asymmetry (pawn): ...`."""
        filters = _sample_filter_context()
        conv = self._finding(
            subsection_id="conversion_recovery_by_type",
            metric="conversion_win_pct",
            window="all_time",
            value=0.77,
            zone="strong",
            dimension={"endgame_class": "pawn", "bucket": "conversion"},
        )
        rec = self._finding(
            subsection_id="conversion_recovery_by_type",
            metric="recovery_save_pct",
            window="all_time",
            value=0.16,
            zone="weak",
            dimension={"endgame_class": "pawn", "bucket": "recovery"},
        )
        tab = _fake_findings(filters, findings=[conv, rec])
        prompt = _assemble_user_prompt(tab)

        assert "# asymmetry (pawn): conversion=77.0 strong, recovery=16.0 weak" in prompt
        assert "closes winning endgames but bleeds losing ones" in prompt

    def test_low_time_gap_line_emitted_in_time_pressure_chart(self) -> None:
        """`# low-time gap (0-30% buckets, weighted):` appears in the chart caption."""
        from app.schemas.endgames import TimePressureBucketPoint, TimePressureChartResponse

        user_series = [
            TimePressureBucketPoint(
                bucket_index=i,
                bucket_label=f"{i * 10}-{(i + 1) * 10}%",
                score=0.30 + 0.03 * i,
                game_count=100,
            )
            for i in range(10)
        ]
        opp_series = [
            TimePressureBucketPoint(
                bucket_index=i,
                bucket_label=f"{i * 10}-{(i + 1) * 10}%",
                score=0.50 + 0.01 * i,
                game_count=100,
            )
            for i in range(10)
        ]
        chart = TimePressureChartResponse(
            user_series=user_series, opp_series=opp_series, total_endgame_games=1000
        )
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[],
            time_pressure_chart=chart,
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab)

        assert "# low-time gap (0-30% buckets, weighted):" in prompt
        assert "user cracks under time pressure" in prompt

    def test_delta_line_emitted_for_paired_windows(self) -> None:
        """Paired all_time + last_3mo scalars emit a `# delta ... within-noise` line."""
        filters = _sample_filter_context()
        at = self._finding(
            subsection_id="endgame_metrics",
            metric="endgame_skill",
            window="all_time",
            value=0.45,
            sample_size=2948,
        )
        lm = self._finding(
            subsection_id="endgame_metrics",
            metric="endgame_skill",
            window="last_3mo",
            value=0.49,
            sample_size=195,
        )
        tab = _fake_findings(filters, findings=[at, lm])
        prompt = _assemble_user_prompt(tab)

        assert "# delta endgame_skill: all_time=+45.0 (n=2948) → last_3mo=+49.0 (n=195)" in prompt
        assert "within-noise" in prompt


# ---------------------------------------------------------------------------
# TestHappyPath
# ---------------------------------------------------------------------------


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_generate_insights_fresh_miss(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fresh miss: returns status='fresh', writes exactly one llm_logs row."""
        report = _sample_report()
        fake_insights_agent(report)

        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            response = await generate_insights(
                _sample_filter_context(), fresh_test_user.id, session
            )

        assert response.status == "fresh"
        assert response.report.overview == report.overview
        assert response.report.sections[0].section_id == "overall"

        # Verify exactly one llm_logs row written with cache_hit=False + response_json set.
        # Note: the "test" model is unknown to genai-prices so the row's error field
        # will contain "cost_unknown:test" (not NULL). We query directly by user_id +
        # findings_hash rather than via get_latest_log_by_hash which filters error IS NULL.
        from sqlalchemy import select as sa_select
        from app.models.llm_log import LlmLog as LlmLogModel

        async with session_maker() as session:
            result = await session.execute(
                sa_select(LlmLogModel)
                .where(
                    LlmLogModel.user_id == fresh_test_user.id,
                    LlmLogModel.findings_hash == "b" * 64,
                    LlmLogModel.cache_hit.is_(False),
                )
                .order_by(LlmLogModel.created_at.desc())
                .limit(1)
            )
            log = result.scalar_one_or_none()
        assert log is not None
        assert log.cache_hit is False
        assert log.response_json is not None


# ---------------------------------------------------------------------------
# TestCacheBehavior
# ---------------------------------------------------------------------------


class TestMetadataOverride:
    """260422-tnb A3: server-side override of model_used + prompt_version."""

    @pytest.mark.asyncio
    async def test_generate_insights_overrides_model_used_and_prompt_version(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fabricated LLM output for model_used/prompt_version is overwritten server-side.

        The LLM can (and has — see review of gemini-3-flash-preview run) return
        "gpt-4o-2024-05-13" as model_used. The service must override both
        fields after _run_agent returns so the user-facing response and the
        persisted llm_logs row both reflect the actual configured values.
        """
        # Simulate a fabricated report from the LLM.
        fabricated = EndgameInsightsReport(
            overview="Fabricated overview.",
            sections=[
                SectionInsight(
                    section_id="overall",
                    headline="A headline",
                    bullets=["a bullet"],
                ),
            ],
            model_used="FABRICATED",
            prompt_version="WRONG",
        )
        fake_insights_agent(fabricated)

        # Unique findings_hash — the cache-lookup is global (not per-user), so
        # we must not collide with any row left behind by the router tests which
        # seed rows with hashes like "m"*64 and do NOT tear them down.
        import uuid as _uuid

        findings_hash = _uuid.uuid4().hex + _uuid.uuid4().hex  # 64 lowercase hex
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(
                fc, sess, uid, findings_hash=findings_hash
            ),
        )

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            response = await generate_insights(
                _sample_filter_context(), fresh_test_user.id, session
            )

        # Response carries the overridden values — never "FABRICATED" or "WRONG".
        assert response.status == "fresh"
        assert response.report.model_used == insights_llm.settings.PYDANTIC_AI_MODEL_INSIGHTS
        assert response.report.prompt_version == "endgame_v6"

        # Log row's response_json also carries the overridden values (the override
        # happens BEFORE create_llm_log per A3). Query by findings_hash (unique
        # per-test) rather than filtering by error IS NULL — the "test" model is
        # unknown to genai-prices so the row's error column will contain
        # "cost_unknown:test". We query directly since we know our hash is unique.
        from sqlalchemy import select as sa_select
        from app.models.llm_log import LlmLog as LlmLogModel

        async with session_maker() as session:
            result = await session.execute(
                sa_select(LlmLogModel)
                .where(
                    LlmLogModel.user_id == fresh_test_user.id,
                    LlmLogModel.findings_hash == findings_hash,
                )
                .order_by(LlmLogModel.created_at.desc())
                .limit(1)
            )
            log = result.scalar_one_or_none()
        assert log is not None, f"no log row for findings_hash={findings_hash}"
        assert log.response_json is not None
        assert log.response_json["model_used"] == insights_llm.settings.PYDANTIC_AI_MODEL_INSIGHTS
        assert log.response_json["prompt_version"] == "endgame_v6"


class TestCacheBehavior:
    @pytest.mark.asyncio
    async def test_second_call_cache_hits(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A seeded cache row (error=None) causes the next call to return cache_hit.

        Note: the test provider "test" is unknown to genai-prices, so any row
        written by generate_insights itself gets error="cost_unknown:test" and
        would NOT be found by get_latest_log_by_hash (which filters error IS NULL).
        We seed a clean cache row manually to test the cache-hit branch directly.
        """
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Seed a cache-hit eligible row: error=None, response_json set,
        # matching (findings_hash, prompt_version="endgame_v6", model="test").
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    model="test",
                    findings_hash="b" * 64,
                    response_json=report.model_dump(),
                    error=None,
                ),
            )

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        # Call returns cache_hit because the seeded row matches (hash + prompt_version + model).
        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "cache_hit"

    @pytest.mark.asyncio
    async def test_prompt_version_bump_misses(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A row with an old prompt_version does not count as a cache hit."""
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Seed a row with old prompt version
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    prompt_version="endgame_v0",
                    model="test",
                    findings_hash="b" * 64,
                    response_json=report.model_dump(),
                ),
            )

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        # Should be fresh — old prompt_version doesn't match _PROMPT_VERSION
        assert r.status == "fresh"

    @pytest.mark.asyncio
    async def test_model_swap_misses(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A row with a different model does not count as a cache hit."""
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Seed a row with different model
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    model="google-gla:gemini-2.5-flash",
                    findings_hash="b" * 64,
                    response_json=report.model_dump(),
                ),
            )

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        # Should be fresh — model "test" != "google-gla:gemini-2.5-flash"
        assert r.status == "fresh"


# ---------------------------------------------------------------------------
# TestRateLimit
# ---------------------------------------------------------------------------


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_boundary_3_misses_allowed_4th_stale(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After 3 successful misses, 4th call returns stale_rate_limited with tier-2 fallback."""
        assert INSIGHTS_MISSES_PER_HOUR == 3  # confirm constant
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Seed 3 successful miss rows (consuming the quota) + 1 tier-2 fallback.
        # All rows use valid EndgameInsightsReport JSON (get_latest_report_for_user
        # returns the most recent one, which may be any of these — that's fine as
        # long as it parses). Use distinct findings_hashes != "b"*64 so tier-1
        # lookup for the current "b"*64 hash does not find them.
        now = datetime.datetime.now(datetime.UTC)
        valid_report_json = report.model_dump()
        async with session_maker() as session:
            for i in range(3):
                await _seed(
                    session,
                    _make_log_row(
                        fresh_test_user.id,
                        created_at=now - datetime.timedelta(minutes=10 + i),
                        findings_hash="c" * 64,
                        response_json=valid_report_json,
                    ),
                )
            # Tier-2 fallback: oldest successful row (get_latest returns newest,
            # which is one of the 3 above — all valid — so any serves as fallback).
            # This extra row ensures at least one valid fallback exists regardless
            # of query ordering.
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    created_at=now - datetime.timedelta(minutes=30),
                    findings_hash="d" * 64,
                    response_json=valid_report_json,
                ),
            )

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "stale_rate_limited"
        assert r.report.overview == report.overview

    @pytest.mark.asyncio
    async def test_429_when_no_tier2(
        self,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rate-limit exhausted with no tier-2 fallback raises InsightsRateLimitExceeded."""
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Seed 3 successful miss rows with an OLD prompt_version so they count
        # toward the rate-limit (count_recent_successful_misses does NOT filter
        # by prompt_version) but are NOT returned by get_latest_report_for_user
        # (which filters by prompt_version="endgame_v6"), producing "no tier-2".
        now = datetime.datetime.now(datetime.UTC)
        # Build a valid report JSON for rows (avoids ValidationError in case tier-2
        # is somehow reached — but with the prompt_version mismatch it should not be).
        valid_json = _sample_report().model_dump()
        async with session_maker() as session:
            for _ in range(3):
                await _seed(
                    session,
                    _make_log_row(
                        fresh_test_user.id,
                        created_at=now - datetime.timedelta(minutes=10),
                        prompt_version="endgame_v0",  # old era — excluded from tier-2
                        response_json=valid_json,
                        findings_hash="k" * 64,
                    ),
                )

        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            # Use a hash that differs from all seeded rows so tier-1 misses
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid, findings_hash="d" * 64),
        )

        async with session_maker() as session:
            with pytest.raises(InsightsRateLimitExceeded) as exc_info:
                await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert exc_info.value.retry_after_seconds > 0

    @pytest.mark.asyncio
    async def test_window_rollover(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Misses older than 1h are outside the window; 4th call is fresh (not rate-limited)."""
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Seed 3 misses with created_at >61 minutes ago (outside the 1h window)
        old_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=61)
        async with session_maker() as session:
            for _ in range(3):
                await _seed(
                    session,
                    _make_log_row(
                        fresh_test_user.id,
                        created_at=old_time,
                        response_json={"ok": True},
                        findings_hash="e" * 64,
                    ),
                )

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid, findings_hash="f" * 64),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        # Window rolled over — should be fresh, not rate-limited
        assert r.status == "fresh"


# ---------------------------------------------------------------------------
# TestErrors
# ---------------------------------------------------------------------------


class TestErrors:
    @pytest.mark.asyncio
    async def test_provider_error_logs_row_and_raises(
        self,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Provider error: raises InsightsProviderError + writes one row with error='provider_error'."""
        from pydantic_ai import Agent
        from pydantic_ai.exceptions import ModelHTTPError
        from pydantic_ai.models.function import FunctionModel

        async def _failing_model(messages: Any, info: Any) -> Any:
            raise ModelHTTPError(status_code=500, model_name="test", body="simulated")

        fake = Agent(FunctionModel(_failing_model), output_type=EndgameInsightsReport)
        monkeypatch.setattr("app.services.insights_llm.get_insights_agent", lambda: fake)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid, findings_hash="g" * 64),
        )
        # Silence Sentry in this test
        mock_sentry = MagicMock()
        monkeypatch.setattr("app.services.insights_llm.sentry_sdk", mock_sentry)

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            with pytest.raises(InsightsProviderError):
                await generate_insights(_sample_filter_context(), fresh_test_user.id, session)

        # Verify log row written with error marker and null response_json
        async with session_maker() as session:
            from sqlalchemy import select
            from app.models.llm_log import LlmLog as LlmLogModel

            result = await session.execute(
                select(LlmLogModel).where(
                    LlmLogModel.user_id == fresh_test_user.id,
                    LlmLogModel.findings_hash == "g" * 64,
                )
            )
            row = result.scalar_one_or_none()
        assert row is not None
        assert row.error is not None
        assert "provider_error" in row.error

    @pytest.mark.asyncio
    async def test_validation_failure_logs_row_and_raises(
        self,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validation failure: raises InsightsValidationFailure + writes row with error marker."""
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel

        # TestModel with sections=[] violates min_length=1, triggering UnexpectedModelBehavior
        # after output_retries are exhausted.
        bad_output: dict[str, Any] = {
            "overview": "ok",
            "sections": [],  # violates min_length=1
            "model_used": "test",
            "prompt_version": "endgame_v6",
        }
        fake = Agent(
            TestModel(custom_output_args=bad_output),
            output_type=EndgameInsightsReport,
            output_retries=0,  # no retries — fail immediately
        )
        monkeypatch.setattr("app.services.insights_llm.get_insights_agent", lambda: fake)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid, findings_hash="h" * 64),
        )
        mock_sentry = MagicMock()
        monkeypatch.setattr("app.services.insights_llm.sentry_sdk", mock_sentry)

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            with pytest.raises(InsightsValidationFailure):
                await generate_insights(_sample_filter_context(), fresh_test_user.id, session)

        async with session_maker() as session:
            from sqlalchemy import select
            from app.models.llm_log import LlmLog as LlmLogModel

            result = await session.execute(
                select(LlmLogModel).where(
                    LlmLogModel.user_id == fresh_test_user.id,
                    LlmLogModel.findings_hash == "h" * 64,
                )
            )
            row = result.scalar_one_or_none()
        assert row is not None
        # The "test" model is unknown to genai-prices so the repo appends
        # "; cost_unknown:test" to the error column. The marker we care about
        # (the pydantic-ai failure reason) must be the first part.
        assert row.error is not None
        assert row.error.startswith("validation_failure_after_retries")
        assert row.response_json is None


# ---------------------------------------------------------------------------
# TestSentryCapture
# ---------------------------------------------------------------------------


class TestSentryCapture:
    @pytest.mark.asyncio
    async def test_set_context_called_on_provider_error(
        self,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Provider error triggers sentry_sdk.set_context with structured data."""
        from pydantic_ai import Agent
        from pydantic_ai.exceptions import ModelHTTPError
        from pydantic_ai.models.function import FunctionModel

        async def _failing_model(messages: Any, info: Any) -> Any:
            raise ModelHTTPError(status_code=500, model_name="test", body="simulated")

        fake = Agent(FunctionModel(_failing_model), output_type=EndgameInsightsReport)
        monkeypatch.setattr("app.services.insights_llm.get_insights_agent", lambda: fake)
        findings_hash = "i" * 64
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(
                fc, sess, uid, findings_hash=findings_hash
            ),
        )
        mock_sentry = MagicMock()
        monkeypatch.setattr("app.services.insights_llm.sentry_sdk", mock_sentry)

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            with pytest.raises(InsightsProviderError):
                await generate_insights(_sample_filter_context(), fresh_test_user.id, session)

        mock_sentry.set_context.assert_called_with(
            "insights",
            {
                "user_id": fresh_test_user.id,
                "findings_hash": findings_hash,
                "model": "test",
                "endpoint": "insights.endgame",
            },
        )
        mock_sentry.capture_exception.assert_called_once()

    def test_no_variable_in_exception_message(self) -> None:
        """Exception messages use stable markers — no user_id or dynamic data."""
        exc = InsightsProviderError("provider_error")
        msg = str(exc)
        # Must not contain anything dynamic (user_id is an int, findings_hash is hex)
        assert "user_id" not in msg
        assert "findings_hash" not in msg
        # Must be the stable marker
        assert msg == "provider_error"


# ---------------------------------------------------------------------------
# TestHideOverview
# ---------------------------------------------------------------------------


class TestHideOverview:
    def test_maybe_strip_overview_strips_when_flag_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(insights_llm.settings, "INSIGHTS_HIDE_OVERVIEW", True)
        report = _sample_report(overview="Full overview text here.")
        stripped = _maybe_strip_overview(report)
        assert stripped.overview == ""
        # Original unchanged
        assert report.overview == "Full overview text here."

    def test_maybe_strip_overview_keeps_when_flag_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(insights_llm.settings, "INSIGHTS_HIDE_OVERVIEW", False)
        report = _sample_report(overview="Full overview text.")
        result = _maybe_strip_overview(report)
        assert result.overview == "Full overview text."

    @pytest.mark.asyncio
    async def test_hide_overview_strips_response_but_logs_full(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """INSIGHTS_HIDE_OVERVIEW=True: response has empty overview but log has full text."""
        full_overview = "Detailed analysis here."
        report = _sample_report(overview=full_overview)
        fake_insights_agent(report)

        monkeypatch.setattr(insights_llm.settings, "INSIGHTS_HIDE_OVERVIEW", True)
        findings_hash = "j" * 64
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(
                fc, sess, uid, findings_hash=findings_hash
            ),
        )

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            response = await generate_insights(
                _sample_filter_context(), fresh_test_user.id, session
            )

        # Response overview stripped
        assert response.status == "fresh"
        assert response.report.overview == ""

        # Log response_json still has the full overview.
        # Query directly (not via get_latest_log_by_hash which filters error IS NULL;
        # the "test" model yields cost_unknown:test in the error column).
        from sqlalchemy import select as sa_select
        from app.models.llm_log import LlmLog as LlmLogModel

        async with session_maker() as session:
            result = await session.execute(
                sa_select(LlmLogModel)
                .where(
                    LlmLogModel.user_id == fresh_test_user.id,
                    LlmLogModel.findings_hash == findings_hash,
                )
                .order_by(LlmLogModel.created_at.desc())
                .limit(1)
            )
            log = result.scalar_one_or_none()
        assert log is not None
        assert log.response_json is not None
        assert log.response_json.get("overview") == full_overview
