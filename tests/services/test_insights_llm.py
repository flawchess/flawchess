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
        player_profile="Player around 1500 rapid, range 1200-1600 over 2 years.",
        overview=overview,
        recommendations=["Try drilling pawn endings.", "Review losses on time."],
        sections=[
            SectionInsight(
                section_id="overall",
                headline="Score Gap is typical",
                bullets=["+4.2pp gap on last_3mo"],
            ),
        ],
        model_used="test",
        prompt_version="endgame_v16",
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


_USE_CURRENT_PROMPT_VERSION = object()  # sentinel for _make_log_row default


def _make_log_row(
    user_id: int,
    *,
    created_at: datetime.datetime | None = None,
    error: str | None = None,
    response_json: dict[str, Any] | None = None,
    cache_hit: bool = False,
    prompt_version: Any = _USE_CURRENT_PROMPT_VERSION,
    model: str = "test",
    findings_hash: str = "b" * 64,
    opponent_strength: str = "any",
) -> LlmLog:
    """Build a minimal LlmLog row for seeding rate-limit tests.

    Default `prompt_version` is insights_llm._PROMPT_VERSION so cache-hit
    tests remain valid across version bumps without manual updates.
    """
    resolved_version = (
        insights_llm._PROMPT_VERSION
        if prompt_version is _USE_CURRENT_PROMPT_VERSION
        else prompt_version
    )
    kwargs: dict[str, Any] = dict(
        user_id=user_id,
        endpoint="insights.endgame",
        model=model,
        prompt_version=resolved_version,
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
# TestPromptVersionAndBody
# ---------------------------------------------------------------------------


class TestPromptVersionAndBody:
    """Phase 68 regression tests (Plan 03 + UAT-pass 260424-pc6).

    Guards:
    - _PROMPT_VERSION is bumped to endgame_v19 so prior cached LLM reports invalidate.
    - app/prompts/endgame_insights.md dropped the score_gap framing rule, the
      score_gap_timeline "only exception to summary-per-metric" carve-out, and
      renamed every `score_gap_timeline` reference to `score_timeline`.
    - The UAT-pass emitter-shape documentation describes the THREE-summary +
      THREE-series score_timeline shape keyed on distinct metrics
      (endgame_score, non_endgame_score, score_gap) with weekly granularity
      and the `[n=<N> for every point]` disclosure for constant-N series.
    """

    def test_prompt_version_is_v19(self) -> None:
        assert insights_llm._PROMPT_VERSION == "endgame_v19"

    def test_prompt_file_does_not_contain_removed_framing_rule(self) -> None:
        from pathlib import Path

        prompt_path = (
            Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
        )
        body = prompt_path.read_text(encoding="utf-8")

        # Negative invariants — all removed in v13, plus v14 drops the old
        # part-dim-tagged score_timeline emitter description.
        for forbidden in (
            "score_gap_timeline",
            "Framing rule (important)",
            "one exception to the summary-per-metric",
            "Score Gap over Time",
            "TWO standard `[summary score_timeline]` blocks",
            "part=endgame",
            "part=non_endgame",
        ):
            assert forbidden not in body, f"prompt still contains forbidden string: {forbidden!r}"

        # Positive invariants — renamed id + v14 emitter-shape documentation present.
        assert "score_timeline" in body
        assert "[summary endgame_score]" in body
        assert "[summary non_endgame_score]" in body
        assert "[summary score_gap]" in body
        assert "[n=<N> for every point]" in body
        assert "weekly" in body

    def test_subsection_mapping_table_renames_to_score_timeline(self) -> None:
        from pathlib import Path

        prompt_path = (
            Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
        )
        body = prompt_path.read_text(encoding="utf-8")

        # The `Subsection → section_id mapping` table row must map score_timeline → overall,
        # NOT score_gap_timeline → overall.
        mapping_row = None
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("| score_timeline") and "overall" in stripped:
                mapping_row = stripped
                break
        assert mapping_row is not None, (
            "missing `| score_timeline ... | overall |` row in mapping table"
        )

    def test_constant_n_series_emits_disclosure_and_drops_per_point_suffix(self) -> None:
        """v14 (260424-pc6 C): when every point's `n` is equal, the series block
        emits a single `[n=<N> for every point]` disclosure line after the
        header and drops the per-point `(n=N)` suffix from every bucket row.
        """
        from app.services.insights_llm import _render_series_block

        finding = SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="endgame_score",
            value=0.55,
            zone="typical",
            trend="improving",
            weekly_points_in_window=5,
            sample_size=100,
            sample_quality="adequate",
            is_headline_eligible=True,
            dimension=None,
            series=[
                TimePoint(bucket_start=f"2026-02-{day:02d}", value=0.55, n=42)
                for day in (2, 9, 16, 23)
            ],
        )
        assert finding.series is not None
        rendered = "\n".join(_render_series_block(finding, finding.series))

        # Disclosure line sits immediately after the header.
        assert "[n=42 for every point]" in rendered
        # Per-point (n=42) suffix must NOT appear on any bucket row.
        assert "(n=42)" not in rendered
        # Bucket rows still carry bucket_start + signed value.
        assert "2026-02-02: +55" in rendered

    def test_variable_n_series_keeps_per_point_suffix(self) -> None:
        """v14 (260424-pc6 C): when per-point `n` varies, the disclosure
        shortcut must NOT fire — every bucket keeps its own `(n=<N>)` tag
        so the LLM can still reason about per-bucket sample weight.
        """
        from app.services.insights_llm import _render_series_block

        finding = SubsectionFinding(
            subsection_id="clock_diff_timeline",
            parent_subsection_id=None,
            window="all_time",
            metric="avg_clock_diff_pct",
            value=-5.0,
            zone="typical",
            trend="stable",
            weekly_points_in_window=5,
            sample_size=200,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=[
                TimePoint(bucket_start=f"2026-02-{day:02d}", value=-5.0, n=n)
                for day, n in zip((2, 9, 16, 23), (40, 42, 44, 46), strict=True)
            ],
        )
        assert finding.series is not None
        rendered = "\n".join(_render_series_block(finding, finding.series))

        # Disclosure line must NOT appear — n is not constant.
        assert "for every point]" not in rendered
        # Per-point (n=<N>) suffix is retained on every bucket.
        for n in (40, 42, 44, 46):
            assert f"(n={n})" in rendered


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
        # Phase 68 (260424-pc6): score_timeline emits THREE findings per
        # window — one per metric (endgame_score, non_endgame_score,
        # score_gap). No `part` dim; each metric id is the unique key.
        timeline_endgame = SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="endgame_score",
            value=0.55,
            zone="typical",
            trend="improving",
            weekly_points_in_window=8,
            sample_size=8,
            sample_quality="adequate",
            is_headline_eligible=True,
            dimension=None,
            series=[
                TimePoint(bucket_start="2026-01-06", value=0.55, n=14),
                TimePoint(bucket_start="2026-01-13", value=0.57, n=14),
            ],
        )
        timeline_non_endgame = SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="non_endgame_score",
            value=0.52,
            zone="typical",
            trend="stable",
            weekly_points_in_window=8,
            sample_size=8,
            sample_quality="adequate",
            is_headline_eligible=False,
            dimension=None,
            series=[
                TimePoint(bucket_start="2026-01-06", value=0.52, n=14),
                TimePoint(bucket_start="2026-01-13", value=0.52, n=14),
            ],
        )
        timeline_gap = SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="score_gap",
            value=0.035,
            zone="typical",
            trend="improving",
            weekly_points_in_window=8,
            sample_size=8,
            sample_quality="adequate",
            is_headline_eligible=False,
            dimension=None,
            series=[
                TimePoint(bucket_start="2026-01-06", value=0.03, n=28),
                TimePoint(bucket_start="2026-01-13", value=0.05, n=28),
            ],
        )
        tab_findings = _fake_findings(
            filters,
            findings=[non_timeline, timeline_endgame, timeline_non_endgame, timeline_gap],
        )
        prompt = _assemble_user_prompt(tab_findings)

        # v9: Filters: header is no longer always emitted; only the
        # `## Scoping caveat` line appears when opponent_strength != "any".
        assert "Filters:" not in prompt
        assert "Flags:" not in prompt
        assert "### Subsection: overall" in prompt
        assert "### Subsection: score_timeline" in prompt
        # Phase 68 (v14): three series blocks (one per metric), all pinned to weekly.
        assert "[series endgame_score, last_3mo, weekly]" in prompt
        assert "[series non_endgame_score, last_3mo, weekly]" in prompt
        assert "[series score_gap, last_3mo, weekly]" in prompt
        # No `part=` dim on any score_timeline series block.
        assert "part=endgame" not in prompt
        assert "part=non_endgame" not in prompt
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
        # Only the normal finding produces a [summary] block; the NaN empty finding is dropped.
        assert prompt.count("[summary ") == 1
        assert "[summary score_gap]" in prompt
        # No bullet lines in v10 — findings render as indented all_time/last_3mo lines.
        assert not [line for line in prompt.splitlines() if line.startswith("- ")]

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

        assert prompt.count("### Subsection: endgame_metrics") == 1
        # Each of the 3 metrics emits exactly one [summary metric | dim] block.
        assert prompt.count("[summary conversion_win_pct | bucket=conversion]") == 1
        assert prompt.count("[summary parity_score_pct | bucket=parity]") == 1
        assert prompt.count("[summary recovery_save_pct | bucket=recovery]") == 1

    def test_assemble_user_prompt_filters_sparse_series_points(self) -> None:
        """A4 (260422-tnb): series points with n < MIN_BUCKET_N (=3) are dropped."""
        filters = _sample_filter_context()
        timeline = SubsectionFinding(
            subsection_id="score_timeline",
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
            dimension={"part": "endgame"},
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
        assert "### Subsection: time_pressure_vs_performance" not in prompt

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

        assert "### Chart: time_pressure_vs_performance" in prompt
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
        assert "### Chart: time_pressure_vs_performance" not in _assemble_user_prompt(tab)

        tab_none = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=filters,
            findings=[],
            time_pressure_chart=None,
            findings_hash="b" * 64,
        )
        assert "### Chart: time_pressure_vs_performance" not in _assemble_user_prompt(tab_none)

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

        assert "### Chart: overall_wdl (all_time)" in prompt
        assert "| series      | games | win_pct | draw_pct | loss_pct | score_pct |" in prompt
        assert "| endgame     | 240" in prompt
        assert "| non_endgame | 700" in prompt
        # v7 whole-number scale: Score % = (W + 0.5*D)/total * 100, rounded.
        # endgame = 140/240*100 = 58.3 → 58, non-endgame = 325/700*100 = 46.4 → 46
        assert "| 58 " in prompt or "| 58\n" in prompt or " 58 " in prompt
        assert "| 46 " in prompt or "| 46\n" in prompt or " 46 " in prompt

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
        assert "### Chart: overall_wdl" not in _assemble_user_prompt(tab)

        # None case
        tab_none = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=_sample_filter_context(),
            findings=[],
            overall_performance=None,
            findings_hash="b" * 64,
        )
        assert "### Chart: overall_wdl" not in _assemble_user_prompt(tab_none)

    def test_assemble_user_prompt_renders_type_wdl_chart_block(self) -> None:
        """Per-class Conversion & Recovery delta block is rendered, sorted by total descending.

        v18 (260501-s0u): chart now shows conv_pct, conv_baseline_mid, conv_delta,
        recov_pct, recov_baseline_mid, recov_delta, n_seq per class rather than
        win_pct/score_pct columns.
        """
        from app.schemas.endgames import ConversionRecoveryStats, EndgameCategoryStats

        def _conv(
            conv_pct: float, recov_pct: float, n_conv: int = 40, n_recov: int = 20
        ) -> ConversionRecoveryStats:
            return ConversionRecoveryStats(
                conversion_pct=conv_pct,
                conversion_games=n_conv,
                conversion_wins=int(n_conv * conv_pct / 100),
                conversion_draws=0,
                conversion_losses=n_conv - int(n_conv * conv_pct / 100),
                recovery_pct=recov_pct,
                recovery_games=n_recov,
                recovery_saves=int(n_recov * recov_pct / 100),
                recovery_wins=int(n_recov * recov_pct / 100 * 0.6),
                recovery_draws=int(n_recov * recov_pct / 100 * 0.4),
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
                conversion=_conv(conv_pct=68.0, recov_pct=32.0),
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
                conversion=_conv(conv_pct=70.0, recov_pct=28.0),
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
                conversion=_conv(conv_pct=75.0, recov_pct=25.0, n_conv=1, n_recov=1),
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

        assert "### Chart: results_by_endgame_type_wdl (all_time)" in prompt
        # v18 column headers (delta-from-baseline table).
        assert "conv_baseline_mid" in prompt
        assert "recov_baseline_mid" in prompt
        assert "conv_delta" in prompt
        assert "recov_delta" in prompt
        # Old win_pct/score_pct columns removed.
        assert "| endgame_class | games | win_pct | draw_pct | loss_pct | score_pct |" not in prompt
        # Sorted by total descending: rook (100) before pawn (30).
        rook_idx = prompt.index("| rook")
        pawn_idx = prompt.index("| pawn")
        assert rook_idx < pawn_idx
        # Queen (n_seq=2, below 10-game floor) dropped.
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
        # Rook: give realistic sequence counts so the delta table renders.
        rook_conv = ConversionRecoveryStats(
            conversion_pct=65.0,
            conversion_games=30,
            conversion_wins=20,
            conversion_draws=0,
            conversion_losses=10,
            recovery_pct=30.0,
            recovery_games=20,
            recovery_saves=6,
            recovery_wins=4,
            recovery_draws=2,
        )
        # Pawnless: zero sequences — keeps existing test intent (would be filtered anyway by
        # the pawnless endgame_class guard, but also dropped by n_seq < 10).
        pawnless_conv_stub = ConversionRecoveryStats.model_construct(
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
                conversion=rook_conv,
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
                conversion=pawnless_conv_stub,
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
        """v7: every finding bullet renders `(typical LO to UP)` next to its zone.

        Covers scalar (score_gap), bucketed (conversion_win_pct), and
        higher_is_better (net_timeout_rate) registry paths. The inline shorthand
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

        # v7 whole-number scale: score_gap band is -10 to +10.
        assert "weak (typical -10 to +10)" in prompt
        # conversion bucket band is +65 to +75.
        assert "weak (typical +65 to +75)" in prompt
        # net_timeout_rate band is now higher_is_better (positive is strong): typical -5 to +5.
        assert "weak (typical -5 to +5)" in prompt
        assert "lower is better" not in prompt  # v7: no lower_is_better metrics left.

    def test_overall_subsection_emitted_alongside_wdl_chart(self) -> None:
        """v9: scalar `overall` subsection is now emitted EVEN WHEN the chart fires.

        Previously (v5 C4) the scalar was dropped when the chart rendered, leaving
        only the score_timeline subsection's bullet — but that bullet's
        `value` is the latest weekly bucket of the rolling timeline, mislabeled
        as `(all_time)`. v9 keeps both: the chart shows the WDL decomposition,
        and the `overall` scalar reports the all-time aggregate that exactly
        matches the chart math (endgame.score_pct - non_endgame.score_pct).
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

        # Chart renders AND the overall [summary score_gap] block renders alongside it.
        assert "### Chart: overall_wdl" in prompt
        assert "### Subsection: overall" in prompt
        assert "[summary score_gap]" in prompt
        # The scalar value should be -15 (-0.15 * 100, rounded) — rendered as mean=-15 on the all_time line.
        assert "all_time: mean=-15" in prompt

    def test_all_time_series_trimmed_to_last_36_points(self) -> None:
        """v11: all_time Series block is capped at the most-recent 36 buckets.

        v5 originally capped at 12 to keep the payload short; v11 raised the
        cap to 36 so the LLM can speak about multi-year trajectories without
        overclaiming a 12-month window as "long-term". Older history beyond
        36 months is still trimmed to keep tokens bounded.
        """
        filters = _sample_filter_context()
        # Uses clock_diff_timeline (still monthly for all_time) since Phase 68
        # pinned score_timeline at weekly granularity across both windows.
        # 40 consecutive monthly buckets ending 2025-10: 2022-07 .. 2025-10.
        bucket_starts: list[str] = []
        cursor = datetime.date(2022, 7, 1)
        while cursor <= datetime.date(2025, 10, 1):
            bucket_starts.append(cursor.isoformat())
            # next month (first-of-month arithmetic)
            year, month = cursor.year, cursor.month + 1
            if month > 12:
                year += 1
                month = 1
            cursor = datetime.date(year, month, 1)
        assert len(bucket_starts) == 40
        # Values alternate between -5 and -15 so the flat-trend collapse
        # (v7 B4) doesn't trigger — the series must retain its per-bucket lines
        # for this test's date-presence assertions to make sense.
        timeline = SubsectionFinding(
            subsection_id="clock_diff_timeline",
            parent_subsection_id=None,
            window="all_time",
            metric="avg_clock_diff_pct",
            value=-8.0,
            zone="typical",
            trend="stable",
            weekly_points_in_window=40,
            sample_size=40,
            sample_quality="rich",
            is_headline_eligible=True,
            dimension=None,
            series=[
                TimePoint(bucket_start=bs, value=-5.0 if i % 2 == 0 else -15.0, n=20)
                for i, bs in enumerate(bucket_starts)
            ],
        )
        tab = _fake_findings(filters, findings=[timeline])
        prompt = _assemble_user_prompt(tab)

        # Most recent 36 buckets are retained: 2022-11 .. 2025-10.
        assert "2025-10-01" in prompt
        assert "2022-11-01" in prompt
        # Oldest 4 buckets are dropped: 2022-07 .. 2022-10.
        assert "2022-07-01" not in prompt
        assert "2022-10-01" not in prompt
        # Exactly 36 series value lines (bucket_start entries, not the header).
        series_lines = [
            ln for ln in prompt.splitlines() if ln.startswith(("2022-", "2023-", "2024-", "2025-"))
        ]
        assert len(series_lines) == 36

    def test_score_timeline_emits_three_summaries_three_series_deterministic_order(self) -> None:
        """Phase 68 v14 (260424-pc6): score_timeline subsection emits THREE [summary] + THREE [series] blocks.

        One finding per distinct metric (endgame_score, non_endgame_score,
        score_gap). No `part=` dim tag — each metric id is unique. Order:
        endgame_score → non_endgame_score → score_gap. All three series are
        pinned to weekly granularity regardless of window. When `n` is
        constant across all points (as here, n=12 on every row), the series
        block carries a single `[n=<N> for every point]` disclosure line and
        drops the `(n=N)` suffix from each bucket row.
        """
        filters = _sample_filter_context()
        endgame_series = [
            TimePoint(
                bucket_start=f"2026-02-{day:02d}",
                value=0.55 + 0.01 * i,
                n=12,
            )
            for i, day in enumerate((2, 9, 16, 23))
        ]
        non_endgame_series = [
            TimePoint(
                bucket_start=f"2026-02-{day:02d}",
                value=0.50 + 0.005 * i,
                n=12,
            )
            for i, day in enumerate((2, 9, 16, 23))
        ]
        gap_series = [
            TimePoint(
                bucket_start=f"2026-02-{day:02d}",
                value=0.05 + 0.005 * i,
                n=24,
            )
            for i, day in enumerate((2, 9, 16, 23))
        ]
        endgame_finding = SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="endgame_score",
            value=0.565,
            zone="typical",
            trend="improving",
            weekly_points_in_window=4,
            sample_size=40,
            sample_quality="adequate",
            is_headline_eligible=True,
            dimension=None,
            series=endgame_series,
        )
        non_endgame_finding = SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="non_endgame_score",
            value=0.5075,
            zone="typical",
            trend="stable",
            weekly_points_in_window=4,
            sample_size=40,
            sample_quality="adequate",
            is_headline_eligible=False,
            dimension=None,
            series=non_endgame_series,
        )
        gap_finding = SubsectionFinding(
            subsection_id="score_timeline",
            parent_subsection_id=None,
            window="last_3mo",
            metric="score_gap",
            value=0.0575,
            zone="typical",
            trend="improving",
            weekly_points_in_window=4,
            sample_size=40,
            sample_quality="adequate",
            is_headline_eligible=False,
            dimension=None,
            series=gap_series,
        )
        tab = _fake_findings(
            filters,
            findings=[endgame_finding, non_endgame_finding, gap_finding],
        )
        prompt = _assemble_user_prompt(tab)

        timeline_start = prompt.index("### Subsection: score_timeline")
        timeline_chunk = prompt[timeline_start:]

        # Exactly three [summary <metric>] blocks, one per metric, no dim tag.
        assert timeline_chunk.count("[summary endgame_score]") == 1
        assert timeline_chunk.count("[summary non_endgame_score]") == 1
        assert timeline_chunk.count("[summary score_gap]") == 1
        # No leftover part-dim-tagged summaries.
        assert "part=endgame" not in timeline_chunk
        assert "part=non_endgame" not in timeline_chunk
        # Exactly three [series ...] blocks, pinned weekly regardless of window.
        assert timeline_chunk.count("[series endgame_score, last_3mo, weekly]") == 1
        assert timeline_chunk.count("[series non_endgame_score, last_3mo, weekly]") == 1
        assert timeline_chunk.count("[series score_gap, last_3mo, weekly]") == 1
        # Deterministic order: endgame_score → non_endgame_score → score_gap.
        endgame_idx = timeline_chunk.index("[summary endgame_score]")
        non_endgame_idx = timeline_chunk.index("[summary non_endgame_score]")
        gap_idx = timeline_chunk.index("[summary score_gap]")
        assert endgame_idx < non_endgame_idx < gap_idx
        # Constant-n disclosure appears (n=12 for endgame/non_endgame, n=24 for gap)
        # and no per-point (n=12) / (n=24) suffix leaks through.
        assert "[n=12 for every point]" in timeline_chunk
        assert "[n=24 for every point]" in timeline_chunk
        assert "(n=12)" not in timeline_chunk
        assert "(n=24)" not in timeline_chunk
        # No suppression carve-out left behind in the module.
        from app.services.insights_llm import _render_subsection_block as _rsb  # noqa: F401
        import inspect

        source = inspect.getsource(_rsb)
        assert "suppress_summary" not in source


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
            subsection_id="score_timeline",
            metric="score_gap",
            window="all_time",
            value=-0.05,
            dimension={"part": "endgame"},
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
        # v9: Filters: line is no longer emitted at defaults.
        assert "Filters:" not in prompt

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

        # Stale blitz combo's all_time line carries the `stale:` marker;
        # rapid combo's all_time line does not.
        blitz_summary_idx = next(
            i
            for i, ln in enumerate(prompt.splitlines())
            if ln == "[summary endgame_elo_gap | platform=chess.com, time_control=blitz]"
        )
        rapid_summary_idx = next(
            i
            for i, ln in enumerate(prompt.splitlines())
            if ln == "[summary endgame_elo_gap | platform=chess.com, time_control=rapid]"
        )
        prompt_lines = prompt.splitlines()
        # The `all_time:` line sits immediately below its [summary] header.
        blitz_all_time_line = prompt_lines[blitz_summary_idx + 1]
        rapid_all_time_line = prompt_lines[rapid_summary_idx + 1]
        assert "stale:" in blitz_all_time_line
        assert "stale:" not in rapid_all_time_line
        # Summary counts the stale series.
        assert "Stale series" in prompt

    def test_trend_emitted_on_summary_window_line(self) -> None:
        """v10: `trend=improving` rides the [summary] window line, not a separate tag.

        Phase 68 dropped the score_gap_timeline suppression carve-out, so
        every timeline subsection emits a [summary] block now. This test
        uses clock_diff_timeline to verify that timeseries [summary] lines
        carry `trend=` / `std=` fields (the same format score_timeline
        now also emits for each per-part finding).
        """
        filters = _sample_filter_context()
        series = [
            TimePoint(bucket_start=f"2026-01-{day:02d}", value=v, n=30)
            for day, v in zip((5, 12, 19, 26), (-25.0, -20.0, -10.0, -2.0), strict=False)
        ]
        finding = self._finding(
            subsection_id="clock_diff_timeline",
            metric="avg_clock_diff_pct",
            window="last_3mo",
            value=-2.0,
            series=series,
        )
        tab = _fake_findings(filters, findings=[finding])
        prompt = _assemble_user_prompt(tab)

        # The summary block's last_3mo line carries trend= and std=.
        lines = prompt.splitlines()
        summary_idx = lines.index("[summary avg_clock_diff_pct]")
        last_3mo_line = lines[summary_idx + 1]
        assert last_3mo_line.startswith("  last_3mo: ")
        assert "trend=improving" in last_3mo_line  # latest -2 vs prior-mean -18.3 → improving
        assert "std=" in last_3mo_line
        # Raw [series ...] still emits for the timeline data.
        assert "[series avg_clock_diff_pct, last_3mo, weekly]" in prompt

    def test_asymmetry_line_emitted_for_strong_weak_split(self) -> None:
        """Pawn with strong conversion + weak recovery emits `[asymmetry type=pawn] ...`.

        v16: pawn now uses the standard "closes winning / defends losing"
        framing alongside every other endgame class. Section 6 benchmark
        data shows queen has the largest conversion/recovery asymmetry, not
        pawn — the v11 pawn special case was reasoned from chess theory, not
        from population data, and the data does not back it.
        """
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

        assert "[asymmetry type=pawn] conversion=77 strong, recovery=16 weak" in prompt
        assert "closes winning endgames but bleeds losing ones" in prompt
        # v16: the v11 "expected asymmetry — pawn endgames amplify material
        # imbalance" framing is gone. Pawn now uses the same story text as
        # every other class.
        assert "expected asymmetry" not in prompt
        assert "amplify material imbalance" not in prompt

    def test_asymmetry_line_uses_standard_story_for_non_pawn_types(self) -> None:
        """Rook with strong conversion + weak recovery uses the standard story text."""
        filters = _sample_filter_context()
        conv = self._finding(
            subsection_id="conversion_recovery_by_type",
            metric="conversion_win_pct",
            window="all_time",
            value=0.80,
            zone="strong",
            dimension={"endgame_class": "rook", "bucket": "conversion"},
        )
        rec = self._finding(
            subsection_id="conversion_recovery_by_type",
            metric="recovery_save_pct",
            window="all_time",
            value=0.18,
            zone="weak",
            dimension={"endgame_class": "rook", "bucket": "recovery"},
        )
        tab = _fake_findings(filters, findings=[conv, rec])
        prompt = _assemble_user_prompt(tab)

        assert "[asymmetry type=rook] conversion=80 strong, recovery=18 weak" in prompt
        assert "closes winning endgames but bleeds losing ones" in prompt

    def test_low_time_gap_line_emitted_in_time_pressure_chart(self) -> None:
        """`[low-time-gap] 0-30% buckets, weighted:` appears in the chart caption."""
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

        assert "[low-time-gap] 0-30% buckets, weighted:" in prompt
        assert "user cracks under time pressure" in prompt

    def test_summary_emitted_for_paired_windows(self) -> None:
        """Paired all_time + last_3mo scalars fold into one [summary] block with a within-noise shift."""
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

        assert "[summary endgame_skill]" in prompt
        assert "all_time: mean=+45, n=2948" in prompt
        assert "last_3mo: mean=+49, n=195" in prompt
        # Shift line closes the block with a within-noise flag.
        assert "shift=+4, within-noise" in prompt

    def test_player_profile_stale_combo_emits_no_recent_trajectory(self) -> None:
        """A stale combo carries `stale: ...` on all_time and `last_3mo: no data`.

        The old free-text trajectory ("+93 over 3 months") silently misled on
        stale combos because it was anchored to the combo's last game date,
        not calendar-now. v10 format replaces it with calendar-anchored
        last_3mo stats, so a stale combo structurally cannot imply recent
        activity.
        """
        from app.schemas.insights import PlayerProfileEntry

        filters = _sample_filter_context()
        stale_entry = PlayerProfileEntry(
            platform="chess.com",
            time_control="blitz",
            games=820,
            current_elo=1293,
            min_elo=819,
            max_elo=1300,
            window_days=1099,
            all_time_mean=1204,
            all_time_n=820,
            all_time_buckets=64,
            all_time_trend="flat",
            all_time_std=125,
            last_3mo_mean=None,
            last_3mo_n=None,
            last_3mo_buckets=None,
            last_3mo_trend=None,
            last_3mo_std=None,
            stale_last_bucket="2024-01",
            stale_months=27,
        )
        live_entry = PlayerProfileEntry(
            platform="lichess",
            time_control="rapid",
            games=450,
            current_elo=1782,
            min_elo=1655,
            max_elo=1839,
            window_days=161,
            all_time_mean=1750,
            all_time_n=450,
            all_time_buckets=23,
            all_time_trend="flat",
            all_time_std=45,
            last_3mo_mean=1775,
            last_3mo_n=210,
            last_3mo_buckets=12,
            last_3mo_trend="flat",
            last_3mo_std=30,
        )
        tab = EndgameTabFindings(
            as_of=datetime.datetime.now(datetime.UTC),
            filters=filters,
            findings=[],
            player_profile=[stale_entry, live_entry],
            findings_hash="b" * 64,
        )
        prompt = _assemble_user_prompt(tab)

        # Stale blitz combo: all_time carries `stale:`, last_3mo reads "no data".
        blitz_header = "[summary actual_elo | platform=chess.com, time_control=blitz]"
        assert blitz_header in prompt
        lines = prompt.splitlines()
        blitz_idx = lines.index(blitz_header)
        blitz_at_line = lines[blitz_idx + 1]
        blitz_lm_line = lines[blitz_idx + 2]
        assert blitz_at_line.startswith("  all_time: ")
        assert "stale: last 2024-01 (27 mo ago)" in blitz_at_line
        assert blitz_lm_line == "  last_3mo: no data"

        # Live lichess combo: no `stale:` marker, populated last_3mo line.
        live_header = "[summary actual_elo | platform=lichess, time_control=rapid]"
        live_idx = lines.index(live_header)
        live_at_line = lines[live_idx + 1]
        live_lm_line = lines[live_idx + 2]
        assert "stale:" not in live_at_line
        assert live_lm_line.startswith("  last_3mo: ")
        assert live_lm_line != "  last_3mo: no data"

        # The old free-text trajectory must NOT appear anywhere in the prompt.
        assert "over 3 months" not in prompt

    def test_endgame_elo_summary_emitted_before_gap_summary(self) -> None:
        """v11: `[summary endgame_elo | ...]` precedes `[summary endgame_elo_gap | ...]`.

        The Endgame ELO Timeline chart's headline value is the absolute
        skill-adjusted Endgame ELO (dashed line), not the gap. The derived
        endgame_elo summary is computed from the same retained series points
        as the gap summary (mean = weighted mean of actual_elo + gap), and
        rendered immediately above the gap summary so the LLM cites the
        chart's primary value, not the derived deviation.
        """
        filters = _sample_filter_context()
        # Series of 4 buckets so trend is computed: actual_elo rising 1450 →
        # 1500, gap holding around -40. Weighted mean endgame_elo per bucket
        # = actual_elo + gap.
        series = [
            TimePoint(bucket_start="2025-10-01", value=-40.0, n=10, actual_elo=1450),
            TimePoint(bucket_start="2025-11-01", value=-45.0, n=20, actual_elo=1470),
            TimePoint(bucket_start="2025-12-01", value=-40.0, n=15, actual_elo=1490),
            TimePoint(bucket_start="2026-01-01", value=-35.0, n=15, actual_elo=1500),
        ]
        finding = self._finding(
            subsection_id="endgame_elo_timeline",
            metric="endgame_elo_gap",
            window="all_time",
            value=-40.0,
            zone="typical",
            dimension={"platform": "chess.com", "time_control": "rapid"},
            series=series,
            sample_size=60,
        )
        tab = _fake_findings(filters, findings=[finding])
        prompt = _assemble_user_prompt(tab)

        elo_header = "[summary endgame_elo | platform=chess.com, time_control=rapid]"
        gap_header = "[summary endgame_elo_gap | platform=chess.com, time_control=rapid]"
        assert elo_header in prompt
        assert gap_header in prompt
        elo_idx = prompt.index(elo_header)
        gap_idx = prompt.index(gap_header)
        assert elo_idx < gap_idx, "endgame_elo summary must precede endgame_elo_gap summary"

        # Weighted mean endgame_elo: (1410*10 + 1425*20 + 1450*15 + 1465*15) / 60
        # = (14100 + 28500 + 21750 + 21975) / 60 = 86325 / 60 ≈ 1439.
        elo_block_lines = prompt[elo_idx:].splitlines()
        all_time_line = elo_block_lines[1]
        assert all_time_line.startswith("  all_time: ")
        assert "mean=+1439 Elo" in all_time_line
        assert "buckets=4 (monthly)" in all_time_line
        # endgame_elo summary has no zone/quality fields (no calibrated band).
        assert "zone=" not in all_time_line
        assert "quality=" not in all_time_line

    def test_endgame_elo_summary_skipped_when_actual_elo_missing(self) -> None:
        """No endgame_elo summary emitted if series points lack actual_elo.

        Defensive: actual_elo is only populated for endgame_elo_timeline series
        upstream. If the upstream pipeline regresses and stops setting it, the
        derived summary should silently fall back to gap-only rather than
        emitting a meaningless block.
        """
        filters = _sample_filter_context()
        series = [
            TimePoint(bucket_start=f"2026-01-{day:02d}", value=-40.0, n=15)
            for day in (5, 12, 19, 26)
        ]
        finding = self._finding(
            subsection_id="endgame_elo_timeline",
            metric="endgame_elo_gap",
            window="all_time",
            value=-40.0,
            dimension={"platform": "chess.com", "time_control": "rapid"},
            series=series,
        )
        tab = _fake_findings(filters, findings=[finding])
        prompt = _assemble_user_prompt(tab)

        assert "[summary endgame_elo |" not in prompt
        assert "[summary endgame_elo_gap |" in prompt

    def test_payload_summary_includes_all_time_window(self) -> None:
        """v11: payload summary spells out the all-time series window bounds.

        Uses clock_diff_timeline (still monthly for all_time) since Phase 68
        pinned score_timeline at weekly granularity across both windows.
        """
        filters = _sample_filter_context()
        series = [
            TimePoint(bucket_start=f"2024-{month:02d}-01", value=-5.0, n=20)
            for month in (1, 4, 7, 10)
        ] + [
            TimePoint(bucket_start=f"2026-{month:02d}-01", value=-5.0, n=20) for month in (1, 2, 3)
        ]
        finding = self._finding(
            subsection_id="clock_diff_timeline",
            metric="avg_clock_diff_pct",
            window="all_time",
            value=-5.0,
            series=series,
        )
        tab = _fake_findings(filters, findings=[finding])
        prompt = _assemble_user_prompt(tab)

        assert "All-time series window: 2024-01 → 2026-03" in prompt
        # Cap value is mentioned so the LLM knows the trim policy.
        assert "capped at 36 monthly buckets per series" in prompt


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
            player_profile="Fabricated player profile.",
            overview="Fabricated overview.",
            recommendations=["Fabricated rec one.", "Fabricated rec two."],
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
        assert response.report.prompt_version == "endgame_v19"

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
        assert log.response_json["prompt_version"] == "endgame_v19"


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

        Note: the cache key is now structural (260425-dxh): the lookup runs via
        get_latest_successful_log_for_user on (user_id, prompt_version, model,
        opponent_strength) — findings_hash is no longer part of the key. The
        test provider "test" is unknown to genai-prices, so any row written by
        generate_insights itself gets error="cost_unknown:test" and would NOT
        be returned by the lookup (which filters error IS NULL). We seed a
        clean cache row manually to test the cache-hit branch directly.
        """
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Seed a cache-hit eligible row: error=None, response_json set,
        # matching (user_id, prompt_version=current, model="test",
        # opponent_strength="any" via filter_context).
        # _make_log_row defaults prompt_version to insights_llm._PROMPT_VERSION.
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

        # Call returns cache_hit because the seeded row matches (prompt_version + model).
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


class TestStructuralCacheInvalidation:
    """Tests for the 260425-dxh structural cache:
    (user_id, prompt_version, model, opponent_strength) + import freshness + 30d TTL.
    """

    @pytest.mark.asyncio
    async def test_import_with_new_games_invalidates_cache(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A completed import with games_imported > 0 after the cached row
        was written invalidates the cache: next call must be fresh."""
        from sqlalchemy import delete

        from app.models.import_job import ImportJob

        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)
        newer = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    created_at=old,
                    response_json=report.model_dump(),
                ),
            )
            session.add(
                ImportJob(
                    id="job-with-games",
                    user_id=fresh_test_user.id,
                    platform="chess.com",
                    username="dxhuser",
                    status="completed",
                    games_fetched=42,
                    games_imported=42,
                    started_at=newer,
                    completed_at=newer,
                )
            )
            await session.commit()

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "fresh"

        # Cleanup the seeded ImportJob row.
        async with session_maker() as session:
            await session.execute(delete(ImportJob).where(ImportJob.id == "job-with-games"))
            await session.commit()

    @pytest.mark.asyncio
    async def test_no_op_import_does_not_invalidate(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A completed import with games_imported = 0 (daily resync that
        fetched nothing new) must NOT invalidate the cache."""
        from sqlalchemy import delete

        from app.models.import_job import ImportJob

        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)
        newer = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    created_at=old,
                    response_json=report.model_dump(),
                ),
            )
            session.add(
                ImportJob(
                    id="job-no-games",
                    user_id=fresh_test_user.id,
                    platform="chess.com",
                    username="dxhuser",
                    status="completed",
                    games_fetched=0,
                    games_imported=0,
                    started_at=newer,
                    completed_at=newer,
                )
            )
            await session.commit()

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "cache_hit"

        async with session_maker() as session:
            await session.execute(delete(ImportJob).where(ImportJob.id == "job-no-games"))
            await session.commit()

    @pytest.mark.asyncio
    async def test_ttl_expiry_misses(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A cached row older than INSIGHTS_CACHE_MAX_AGE_DAYS is treated as a miss."""
        from app.services.insights_llm import INSIGHTS_CACHE_MAX_AGE_DAYS

        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        too_old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            days=INSIGHTS_CACHE_MAX_AGE_DAYS + 1
        )
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    created_at=too_old,
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
        assert r.status == "fresh"

    @pytest.mark.asyncio
    async def test_other_users_log_not_returned(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A log row owned by a different user must not be served as cache hit
        (regression test for the missing user_id filter on the old hash-based lookup)."""
        import uuid as _uuid

        from sqlalchemy import delete

        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        # Create a real second user (FK constraint prevents fabricated ids).
        async with session_maker() as session:
            other_user = User(
                email=f"other-user-{_uuid.uuid4()}@example.com",
                hashed_password="x",
            )
            session.add(other_user)
            await session.commit()
            await session.refresh(other_user)
            other_user_id = other_user.id

        try:
            async with session_maker() as session:
                await _seed(
                    session,
                    _make_log_row(
                        other_user_id,
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
            assert r.status == "fresh"
        finally:
            async with session_maker() as session:
                # ON DELETE CASCADE on llm_logs.user_id removes the seeded log row.
                await session.execute(delete(User).where(User.id == other_user_id))
                await session.commit()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_compute_findings(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Cache hit must NOT invoke compute_findings (the whole point of the rewrite)."""
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    response_json=report.model_dump(),
                ),
            )

        called = {"count": 0}

        async def _raising_compute_findings(
            fc: FilterContext, sess: AsyncSession, uid: int
        ) -> EndgameTabFindings:
            called["count"] += 1
            raise AssertionError("compute_findings must not be called on cache hit")

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            _raising_compute_findings,
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "cache_hit"
        assert called["count"] == 0


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
        # long as it parses).
        # 260425-dxh: seed with opponent_strength="stronger" so the structural
        # cache lookup (which queries with the call's opp_strength="any") MISSES
        # — but rate-limit count and tier-2 fallback do NOT filter by
        # opp_strength, so they still pick up these rows.
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
                        opponent_strength="stronger",
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
                    opponent_strength="stronger",
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
        # (which filters by prompt_version="endgame_v16"), producing "no tier-2".
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

        # Seed 3 misses with created_at >61 minutes ago (outside the 1h window).
        # 260425-dxh: use opponent_strength="stronger" so the structural cache
        # lookup misses (the call uses default "any") — otherwise these rows
        # would serve as a cache hit before the rate-limit check ran.
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
                        opponent_strength="stronger",
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
            "prompt_version": "endgame_v16",
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
