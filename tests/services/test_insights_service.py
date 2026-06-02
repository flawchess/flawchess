"""Tests for app/services/insights_service.py — Phase 63 Plan 05.

Coverage by requirement:

- FIND-01 (layering): TestComputeFindingsLayering asserts that
  `insights_service` imports no repositories and never calls
  `asyncio.gather`, and that `compute_findings` issues exactly two
  sequential calls to `endgame_service.get_endgame_overview`
  (from_date=None/to_date=None then from_date=today-90d/to_date=None).
- FIND-04 (trend gate): TestComputeTrend covers count-fail, ratio-fail,
  both-pass (improving / declining), and flat (stable).
- FIND-05 (hash stability): TestComputeHash covers the 64-char lowercase
  hex format, `as_of` / `findings_hash` exclusion, value-change
  discrimination, NaN safety, and dict-insertion-order invariance.

Additional coverage: TestEmptyFinding verifies the empty-window
convention (value=NaN, zone="typical", is_headline_eligible=False,
sample_quality="thin").

All tests run against synthetic Pydantic instances / helper-built
SubsectionFinding lists — zero DB access. Target runtime < 30s.
"""

from __future__ import annotations

import inspect
import math
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest

import app.services.insights_service as insights_module
from app.schemas.endgames import EndgameOverviewResponse
from app.schemas.insights import (
    EndgameTabFindings,
    FilterContext,
    MetricId,
    SampleQuality,
    SubsectionFinding,
    SubsectionId,
    Trend,
    Window,
    Zone,
)
from app.services.endgame_zones import (
    TREND_MIN_SLOPE_VOL_RATIO,
    TREND_MIN_WEEKLY_POINTS,
)
from app.services.insights_service import (
    _compute_hash,
    _compute_trend,
    _empty_finding,
    compute_findings,
)


# ---------------------------------------------------------------------------
# Helper factory for building synthetic SubsectionFinding instances.
# Keeps flag / hash tests terse by defaulting non-load-bearing fields.
# ---------------------------------------------------------------------------


def _make_finding(
    subsection_id: str,
    metric: str,
    value: float,
    zone: str,
    *,
    window: str = "all_time",
    dimension: dict[str, str] | None = None,
    trend: str = "n_a",
    sample_size: int = 100,
    sample_quality: str = "adequate",
    is_headline_eligible: bool = True,
    parent_subsection_id: str | None = None,
    weekly_points_in_window: int = 0,
) -> SubsectionFinding:
    """Build a SubsectionFinding with sensible test defaults.

    Accepts `str` for the Literal-typed fields for test brevity; the
    underlying Pydantic validator still enforces membership in each
    Literal alias, so an invalid value would raise ValidationError.
    """
    return SubsectionFinding(
        subsection_id=cast(SubsectionId, subsection_id),
        parent_subsection_id=cast("SubsectionId | None", parent_subsection_id),
        window=cast(Window, window),
        metric=cast(MetricId, metric),
        value=value,
        zone=cast(Zone, zone),
        trend=cast(Trend, trend),
        weekly_points_in_window=weekly_points_in_window,
        sample_size=sample_size,
        sample_quality=cast(SampleQuality, sample_quality),
        is_headline_eligible=is_headline_eligible,
        dimension=dimension,
    )


# ---------------------------------------------------------------------------
# TestComputeTrend — FIND-04 trend gate (count + slope/volatility ratio).
# ---------------------------------------------------------------------------


class TestComputeTrend:
    """Unit tests for _compute_trend: count gate + slope/volatility gate."""

    def test_count_fail_returns_n_a(self) -> None:
        """n < TREND_MIN_WEEKLY_POINTS collapses trend to n_a."""
        # Build n-1 points — guaranteed below the gate regardless of tuning.
        points = [float(i) for i in range(TREND_MIN_WEEKLY_POINTS - 1)]
        trend, n = _compute_trend(points)
        assert trend == "n_a"
        assert n == TREND_MIN_WEEKLY_POINTS - 1

    def test_empty_series_returns_n_a(self) -> None:
        """Empty list is a degenerate count-fail case."""
        trend, n = _compute_trend([])
        assert trend == "n_a"
        assert n == 0

    def test_both_pass_improving(self) -> None:
        """Strong positive slope at n >= count gate → improving.

        For a pure linear series of length n, `slope / stdev(points)` is a
        FIXED property (scale-invariant): `sqrt(12 / (n^2 - 1))` for the
        sample-stdev variant. At n=25 that's 0.136 — below the default 0.5
        gate by design (per 63-04 SUMMARY smoke-test note). To exercise the
        "improving" branch deterministically, we call `_compute_trend` with
        a permissive `min_slope_vol_ratio` override; the test still runs
        the REAL gate check using the same function, just with a threshold
        we know the linear series passes.
        """
        n = TREND_MIN_WEEKLY_POINTS + 5
        points = [float(i) for i in range(n)]
        trend, returned_n = _compute_trend(points, min_slope_vol_ratio=0.1)
        assert trend == "improving"
        assert returned_n == n

    def test_both_pass_declining(self) -> None:
        """Strong negative slope at n >= count gate → declining.

        Same rationale as test_both_pass_improving: pure linear series at
        n>=20 never passes the default 0.5 ratio gate, so we supply a
        permissive override to exercise the declining-slope branch.
        """
        n = TREND_MIN_WEEKLY_POINTS + 5
        points = [float(n - i) for i in range(n)]
        trend, returned_n = _compute_trend(points, min_slope_vol_ratio=0.1)
        assert trend == "declining"
        assert returned_n == n

    def test_flat_series_is_stable(self) -> None:
        """Zero-volatility series collapses to stable (not n_a)."""
        points = [0.5] * (TREND_MIN_WEEKLY_POINTS + 5)
        trend, n = _compute_trend(points)
        assert trend == "stable"
        assert n == TREND_MIN_WEEKLY_POINTS + 5

    def test_ratio_fail_returns_n_a(self) -> None:
        """Tiny slope relative to high volatility fails the ratio gate."""
        # Zero-slope noise around 0.5 — slope ~ 0, ratio ~ 0 < 0.5.
        import random

        random.seed(42)
        points = [random.gauss(0.5, 0.2) for _ in range(TREND_MIN_WEEKLY_POINTS + 5)]
        trend, _ = _compute_trend(points)
        assert trend == "n_a"

    def test_ratio_gate_references_registry_constant(self) -> None:
        """Default signature argument equals the registry constant (no magic)."""
        # Inspect the default argument; ensures no drift between the service
        # signature and the registry value.
        sig = inspect.signature(_compute_trend)
        default = sig.parameters["min_slope_vol_ratio"].default
        assert default == TREND_MIN_SLOPE_VOL_RATIO

    def test_count_gate_references_registry_constant(self) -> None:
        """Default count-gate argument equals the registry constant."""
        sig = inspect.signature(_compute_trend)
        default = sig.parameters["min_weekly_points"].default
        assert default == TREND_MIN_WEEKLY_POINTS


# ---------------------------------------------------------------------------
# TestComputeHash — FIND-05 hash format + stability + discrimination.
# ---------------------------------------------------------------------------


class TestComputeHash:
    """Unit tests for _compute_hash canonical-JSON + SHA256 recipe."""

    def _base_findings(self) -> EndgameTabFindings:
        """Minimal EndgameTabFindings seed — one ordinary finding."""
        import datetime

        return EndgameTabFindings(
            as_of=datetime.datetime(2026, 4, 20, tzinfo=datetime.UTC),
            filters=FilterContext(),
            findings=[_make_finding("overall", "score_gap", 0.05, "typical")],
            findings_hash="",
        )

    def test_hash_is_64_char_lowercase_hex(self) -> None:
        """Format: 64-char lowercase hex (SHA256 hexdigest)."""
        h = _compute_hash(self._base_findings())
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_excludes_as_of(self) -> None:
        """Two findings differing only in as_of produce the same hash."""
        import datetime

        a = self._base_findings()
        b = a.model_copy(update={"as_of": datetime.datetime(2099, 1, 1, tzinfo=datetime.UTC)})
        assert _compute_hash(a) == _compute_hash(b)

    def test_hash_excludes_findings_hash_itself(self) -> None:
        """findings_hash placeholder value does not influence the hash."""
        a = self._base_findings().model_copy(update={"findings_hash": "placeholder"})
        b = a.model_copy(update={"findings_hash": "otherstring"})
        assert _compute_hash(a) == _compute_hash(b)

    def test_hash_differs_on_finding_value_change(self) -> None:
        """Changing a finding's value produces a different hash."""
        a = self._base_findings()
        b = a.model_copy(
            update={
                "findings": [_make_finding("overall", "score_gap", 0.20, "strong")],
            }
        )
        assert _compute_hash(a) != _compute_hash(b)

    def test_hash_differs_on_filter_change(self) -> None:
        """Different FilterContext → different hash (cache discrimination)."""
        a = self._base_findings().model_copy(
            update={"filters": FilterContext(opponent_strength="stronger")},
        )
        b = a.model_copy(
            update={"filters": FilterContext(opponent_strength="weaker")},
        )
        assert _compute_hash(a) != _compute_hash(b)

    def test_hash_stable_with_nan_value(self) -> None:
        """NaN serialises to JSON null via model_dump_json — no JSONDecodeError."""
        a = self._base_findings().model_copy(
            update={
                "findings": [
                    _make_finding("overall", "score_gap", float("nan"), "typical"),
                ],
            }
        )
        h = _compute_hash(a)
        assert len(h) == 64

    def test_hash_stable_across_dict_insertion_order(self) -> None:
        """dict keys are sort_keys=True canonicalised → order invariance."""
        dim_ab = {"platform": "chess.com", "time_control": "blitz"}
        dim_ba = {"time_control": "blitz", "platform": "chess.com"}
        a = self._base_findings().model_copy(
            update={
                "findings": [
                    _make_finding(
                        "endgame_elo_timeline",
                        "endgame_elo_gap",
                        50.0,
                        "typical",
                        dimension=dim_ab,
                    ),
                ],
            }
        )
        b = self._base_findings().model_copy(
            update={
                "findings": [
                    _make_finding(
                        "endgame_elo_timeline",
                        "endgame_elo_gap",
                        50.0,
                        "typical",
                        dimension=dim_ba,
                    ),
                ],
            }
        )
        assert _compute_hash(a) == _compute_hash(b)

    def test_hash_stable_across_two_invocations(self) -> None:
        """Calling _compute_hash twice on the same inputs yields the same hash."""
        findings = self._base_findings()
        assert _compute_hash(findings) == _compute_hash(findings)


# ---------------------------------------------------------------------------
# TestEmptyFinding — empty-window convention (NaN / typical / not headline).
# ---------------------------------------------------------------------------


class TestEmptyFinding:
    """Unit tests for _empty_finding helper (empty-window contract)."""

    def test_empty_finding_sets_nan_value(self) -> None:
        f = _empty_finding("overall", "all_time", "score_gap")
        assert math.isnan(f.value)

    def test_empty_finding_sets_typical_zone(self) -> None:
        f = _empty_finding("overall", "all_time", "score_gap")
        assert f.zone == "typical"

    def test_empty_finding_sets_trend_n_a(self) -> None:
        f = _empty_finding("overall", "all_time", "score_gap")
        assert f.trend == "n_a"

    def test_empty_finding_not_headline_eligible(self) -> None:
        f = _empty_finding("overall", "all_time", "score_gap")
        assert f.is_headline_eligible is False

    def test_empty_finding_thin_quality(self) -> None:
        f = _empty_finding("overall", "all_time", "score_gap")
        assert f.sample_quality == "thin"

    def test_empty_finding_zero_sample_size(self) -> None:
        f = _empty_finding("overall", "all_time", "score_gap")
        assert f.sample_size == 0

    def test_empty_finding_carries_dimension(self) -> None:
        """Dimension passes through for per-combo / per-bucket empty findings."""
        dim = {"platform": "chess.com", "time_control": "blitz"}
        f = _empty_finding(
            "endgame_elo_timeline",
            "all_time",
            "endgame_elo_gap",
            dimension=dim,
        )
        assert f.dimension == dim

    def test_empty_finding_serialises_nan_as_null(self) -> None:
        """NaN must serialise to JSON null via Pydantic v2 — no JSONDecodeError
        when a downstream consumer rehydrates the finding."""
        import json

        f = _empty_finding("overall", "all_time", "score_gap")
        parsed = json.loads(f.model_dump_json())
        # JSON null round-trips to Python None (not NaN).
        assert parsed["value"] is None


# ---------------------------------------------------------------------------
# TestComputeFindingsLayering — FIND-01: service-only access, two sequential
# awaits of get_endgame_overview, no asyncio.gather, no repository imports.
# ---------------------------------------------------------------------------


class TestComputeFindingsLayering:
    """FIND-01: insights_service consumes only endgame_service.get_endgame_overview."""

    def test_no_repository_import_in_module_source(self) -> None:
        """Module source has no `from app.repositories` import (FIND-01)."""
        src = inspect.getsource(insights_module)
        assert "from app.repositories" not in src, (
            "FIND-01 violation: insights_service must not import from repositories"
        )
        assert "import app.repositories" not in src

    def test_no_asyncio_gather_in_module_source(self) -> None:
        """CLAUDE.md §Critical Constraints: no asyncio.gather on AsyncSession."""
        src = inspect.getsource(insights_module)
        assert "asyncio.gather" not in src, (
            "AsyncSession is not safe for concurrent gather; use sequential awaits."
        )

    @pytest.mark.asyncio
    async def test_calls_get_endgame_overview_twice(self) -> None:
        """compute_findings issues exactly 2 awaits of get_endgame_overview."""
        mock_response = EndgameOverviewResponse.model_construct()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            try:
                await compute_findings(
                    FilterContext(),
                    session=AsyncMock(),
                    user_id=1,
                )
            except Exception:
                # compute_findings may fail downstream because model_construct
                # skips required fields; we only care about the two-call
                # invariant on the mocked overview service here.
                pass
            assert mocked.await_count == 2

    @pytest.mark.asyncio
    async def test_first_call_uses_from_date_none(self) -> None:
        """First call passes from_date=None, to_date=None (all_time window)."""
        mock_response = EndgameOverviewResponse.model_construct()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            try:
                await compute_findings(
                    FilterContext(),
                    session=AsyncMock(),
                    user_id=1,
                )
            except Exception:
                pass
            first_kwargs = mocked.await_args_list[0].kwargs
            assert first_kwargs["from_date"] is None
            assert first_kwargs["to_date"] is None

    @pytest.mark.asyncio
    async def test_second_call_uses_last_3mo_window(self) -> None:
        """Second call passes from_date=today-90d, to_date=None (last_3mo window)."""
        import datetime

        mock_response = EndgameOverviewResponse.model_construct()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            try:
                await compute_findings(
                    FilterContext(),
                    session=AsyncMock(),
                    user_id=1,
                )
            except Exception:
                pass
            second_kwargs = mocked.await_args_list[1].kwargs
            expected_from_date = datetime.date.today() - datetime.timedelta(days=90)
            assert second_kwargs["from_date"] == expected_from_date
            assert second_kwargs["to_date"] is None

    @pytest.mark.asyncio
    async def test_color_is_not_forwarded_to_endgame_service(self) -> None:
        """FilterContext.color is carried by the schema but NOT threaded to
        get_endgame_overview (the endgame service has no color filter)."""
        mock_response = EndgameOverviewResponse.model_construct()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            try:
                await compute_findings(
                    FilterContext(color="white"),
                    session=AsyncMock(),
                    user_id=1,
                )
            except Exception:
                pass
            for call in mocked.await_args_list:
                assert "color" not in call.kwargs


# ---------------------------------------------------------------------------
# TestComputeFindingsReturnContract — REVIEW WR-03: end-to-end contract that
# compute_findings returns an EndgameTabFindings whose findings_hash is
# populated (64-char lowercase hex) so a refactor cannot silently drop the
# hash assignment. Subsection extraction is patched to [] so the test does
# not need a full EndgameOverviewResponse fixture — only the wiring from
# compute_findings' hash step to the returned model matters here.
# ---------------------------------------------------------------------------

import re  # noqa: E402


def _stub_endgame_overview_response() -> EndgameOverviewResponse:
    """Build a minimal EndgameOverviewResponse for compute_findings wiring tests.

    `model_construct` skips validation but does not set defaults, so any field
    `compute_findings` reads must be populated explicitly. Subsection extraction
    is patched to [] in the wiring tests, so per-subsection field accesses inside
    `_compute_subsection_findings` don't matter here — only the top-level fields
    read by `compute_findings` itself need stub values.

    Phase 102 (Plan 01): added score_gap_material (for score_gap_percentile),
    time_pressure_cards (passed through to EndgameTabFindings), and rating_anchors
    (for cohort_anchors) to the stub so compute_findings' new field population
    does not AttributeError on model_construct instances.
    """
    from app.schemas.endgames import (
        ScoreGapMaterialResponse,
        TimePressureCardsResponse,
    )

    stub_score_gap_material = ScoreGapMaterialResponse(
        endgame_score=0.5,
        non_endgame_score=0.5,
        score_difference=0.0,
        material_rows=[],
        timeline=[],
        timeline_window=50,
    )
    stub_time_pressure_cards = TimePressureCardsResponse(cards=[])

    return EndgameOverviewResponse.model_construct(
        time_pressure_chart=None,
        performance=None,
        stats=type("StatsStub", (), {"categories": []})(),
        endgame_elo_timeline=type("EloTimelineStub", (), {"combos": []})(),
        score_gap_material=stub_score_gap_material,
        time_pressure_cards=stub_time_pressure_cards,
        rating_anchors={},
    )


class TestComputeFindingsReturnContract:
    """End-to-end wiring of compute_findings → EndgameTabFindings."""

    @pytest.mark.asyncio
    async def test_returns_endgame_tab_findings_with_populated_hash(self) -> None:
        mock_response = _stub_endgame_overview_response()
        fc = FilterContext()
        with (
            patch.object(
                insights_module,
                "get_endgame_overview",
                new=AsyncMock(return_value=mock_response),
            ),
            patch.object(
                insights_module,
                "_compute_subsection_findings",
                return_value=[],
            ),
        ):
            result = await compute_findings(fc, session=AsyncMock(), user_id=1)

        assert isinstance(result, EndgameTabFindings)
        assert re.fullmatch(r"[0-9a-f]{64}", result.findings_hash), (
            f"findings_hash must be 64-char lowercase hex, got: {result.findings_hash!r}"
        )
        assert result.filters == fc
        assert result.findings == []

    @pytest.mark.asyncio
    async def test_hash_is_stable_across_two_invocations_end_to_end(self) -> None:
        """Calling compute_findings twice with the same inputs produces the
        same findings_hash (as_of differs between calls but is excluded)."""
        mock_response = _stub_endgame_overview_response()
        fc = FilterContext(opponent_strength="stronger")
        with (
            patch.object(
                insights_module,
                "get_endgame_overview",
                new=AsyncMock(return_value=mock_response),
            ),
            patch.object(
                insights_module,
                "_compute_subsection_findings",
                return_value=[],
            ),
        ):
            first = await compute_findings(fc, session=AsyncMock(), user_id=1)
            second = await compute_findings(fc, session=AsyncMock(), user_id=1)

        assert first.findings_hash == second.findings_hash


# ---------------------------------------------------------------------------
# TestFindingsEndgameMetrics — 260422-tnb A1: bucket-matched metric emission.
# Each MaterialRow maps to exactly ONE finding whose metric matches the
# bucket (conversion -> conversion_win_pct, parity -> parity_score_pct,
# recovery -> recovery_save_pct). Phase 87.4 (D-05): the aggregate
# ``endgame_skill`` finding was removed end-to-end. Total emitted = N bucket
# rate findings + 3 score_gap_* findings (Phase 87.2 D-09 minus the
# retired "skill" bucket).
# ---------------------------------------------------------------------------


class TestFindingsEndgameMetrics:
    """Unit tests for _findings_endgame_metrics A1 fix."""

    def _make_overview_with_material_rows(
        self,
        material_rows: list[Any],
    ) -> Any:
        """Build a minimal EndgameOverviewResponse with given material_rows."""
        from app.schemas.endgames import ScoreGapMaterialResponse

        score_gap_material = ScoreGapMaterialResponse(
            endgame_score=0.5,
            non_endgame_score=0.5,
            score_difference=0.0,
            material_rows=material_rows,
            timeline=[],
            timeline_window=50,
        )
        resp = EndgameOverviewResponse.model_construct(
            score_gap_material=score_gap_material,
        )
        return resp

    def _make_material_row(
        self,
        bucket: str,
        games: int,
        win_pct: float,
        draw_pct: float,
        score: float,
    ) -> Any:
        from app.schemas.endgames import MaterialRow

        return MaterialRow(
            bucket=cast(Any, bucket),
            label=bucket.capitalize(),
            games=games,
            win_pct=win_pct,
            draw_pct=draw_pct,
            loss_pct=100.0 - win_pct - draw_pct,
            score=score,
        )

    def test_emits_exactly_one_finding_per_non_empty_bucket(self) -> None:
        """3 non-zero MaterialRows -> 3 bucket rate findings + 3 score_gap_bucket
        findings (Phase 87.2 D-09 minus the retired Skill bucket per Phase 87.4 D-05)
        = 6 total. The aggregate ``endgame_skill`` finding was removed in 87.4."""
        from app.services.insights_service import _findings_endgame_metrics

        rows = [
            self._make_material_row(
                "conversion", games=100, win_pct=68.0, draw_pct=10.0, score=0.73
            ),
            self._make_material_row("parity", games=80, win_pct=40.0, draw_pct=20.0, score=0.50),
            self._make_material_row("recovery", games=60, win_pct=15.0, draw_pct=20.0, score=0.25),
        ]
        response = self._make_overview_with_material_rows(rows)
        findings = _findings_endgame_metrics(response, window="all_time")

        assert len(findings) == 6
        # Phase 87.4 (D-05): no aggregate endgame_skill finding any more.
        assert not any(f.metric == "endgame_skill" for f in findings)

        # Three rate bucket findings: one per bucket, metric matches the bucket.
        rate_findings = [
            f
            for f in findings
            if f.dimension is not None
            and f.metric in {"conversion_win_pct", "parity_score_pct", "recovery_save_pct"}
        ]
        by_bucket: dict[str, str] = {
            f.dimension["bucket"]: f.metric for f in rate_findings if f.dimension is not None
        }
        assert by_bucket == {
            "conversion": "conversion_win_pct",
            "parity": "parity_score_pct",
            "recovery": "recovery_save_pct",
        }

        # Three score_gap_* findings (Phase 87.2 D-09 minus retired skill).
        score_gap_bucket_metrics = sorted(
            f.metric for f in findings if f.metric.startswith("score_gap_")
        )
        assert score_gap_bucket_metrics == [
            "score_gap_conv",
            "score_gap_parity",
            "score_gap_recov",
        ]

    def test_no_cross_bucket_fan_out(self) -> None:
        """No finding has (bucket=conversion, metric=parity_score_pct) or similar.

        Regression guard for the A1 semantic conflict: before the fix, every
        bucket emitted all three metrics, producing self-contradictory rows
        like `parity_score_pct | [bucket=conversion]`.
        """
        from app.services.insights_service import _findings_endgame_metrics

        rows = [
            self._make_material_row(
                "conversion", games=100, win_pct=68.0, draw_pct=10.0, score=0.73
            ),
            self._make_material_row("parity", games=80, win_pct=40.0, draw_pct=20.0, score=0.50),
            self._make_material_row("recovery", games=60, win_pct=15.0, draw_pct=20.0, score=0.25),
        ]
        response = self._make_overview_with_material_rows(rows)
        findings = _findings_endgame_metrics(response, window="all_time")

        for f in findings:
            if f.dimension is None:
                # Phase 87.4 (D-05): score_gap_* findings have no
                # bucket dim (they live on the response as scalars, not
                # per-MaterialBucket). The aggregate endgame_skill finding
                # was retired so the dimension==None branch now covers only
                # those.
                continue
            bucket = f.dimension.get("bucket")
            if bucket == "conversion":
                assert f.metric == "conversion_win_pct"
            elif bucket == "parity":
                assert f.metric == "parity_score_pct"
            elif bucket == "recovery":
                assert f.metric == "recovery_save_pct"

    def test_empty_bucket_emits_one_empty_finding(self) -> None:
        """A MaterialRow with games=0 emits ONE empty finding for the matching metric.

        Phase 87.2 (D-09): 4 score_gap_* findings are always emitted alongside
        the rate findings, so the bucket-only assertions filter on dimension presence.
        """
        from app.services.insights_service import _findings_endgame_metrics

        rows = [
            self._make_material_row("conversion", games=0, win_pct=0.0, draw_pct=0.0, score=0.0),
            self._make_material_row("parity", games=50, win_pct=40.0, draw_pct=20.0, score=0.50),
            self._make_material_row("recovery", games=0, win_pct=0.0, draw_pct=0.0, score=0.0),
        ]
        response = self._make_overview_with_material_rows(rows)
        findings = _findings_endgame_metrics(response, window="all_time")

        # Phase 87.4 (D-05): no aggregate endgame_skill finding.
        # 3 rate bucket findings (2 empty + 1 normal) +
        # 3 score_gap_* findings (D-09 minus retired skill bucket).
        assert len(findings) == 6

        # Rate bucket findings only — filter by metric, not by dimension, because
        # score_gap_* findings have dimension=None.
        bucket_findings = [
            f
            for f in findings
            if f.dimension is not None
            and f.metric in {"conversion_win_pct", "parity_score_pct", "recovery_save_pct"}
        ]
        # Each bucket appears exactly once.
        buckets_seen = [f.dimension["bucket"] for f in bucket_findings if f.dimension]
        assert sorted(buckets_seen) == ["conversion", "parity", "recovery"]

        # Empty-bucket findings carry the matching metric with NaN value.
        conv = next(
            f for f in bucket_findings if f.dimension and f.dimension["bucket"] == "conversion"
        )
        assert conv.metric == "conversion_win_pct"
        assert math.isnan(conv.value)
        assert conv.sample_size == 0

        recov = next(
            f for f in bucket_findings if f.dimension and f.dimension["bucket"] == "recovery"
        )
        assert recov.metric == "recovery_save_pct"
        assert math.isnan(recov.value)

    def test_conversion_value_is_win_pct_over_100(self) -> None:
        """Value for the conversion bucket = win_pct / 100."""
        from app.services.insights_service import _findings_endgame_metrics

        rows = [
            self._make_material_row(
                "conversion", games=100, win_pct=68.0, draw_pct=10.0, score=0.73
            ),
        ]
        response = self._make_overview_with_material_rows(rows)
        findings = _findings_endgame_metrics(response, window="all_time")

        conv = next(
            f for f in findings if f.dimension and f.dimension.get("bucket") == "conversion"
        )
        assert conv.value == pytest.approx(0.68)

    def test_parity_value_is_score(self) -> None:
        """Value for the parity bucket = score (already 0.0-1.0)."""
        from app.services.insights_service import _findings_endgame_metrics

        rows = [
            self._make_material_row("parity", games=80, win_pct=40.0, draw_pct=20.0, score=0.50),
        ]
        response = self._make_overview_with_material_rows(rows)
        findings = _findings_endgame_metrics(response, window="all_time")

        parity = next(f for f in findings if f.dimension and f.dimension.get("bucket") == "parity")
        assert parity.value == pytest.approx(0.50)

    def test_recovery_value_is_win_plus_draw_over_100(self) -> None:
        """Value for the recovery bucket = (win_pct + draw_pct) / 100."""
        from app.services.insights_service import _findings_endgame_metrics

        rows = [
            self._make_material_row("recovery", games=60, win_pct=15.0, draw_pct=20.0, score=0.25),
        ]
        response = self._make_overview_with_material_rows(rows)
        findings = _findings_endgame_metrics(response, window="all_time")

        recov = next(f for f in findings if f.dimension and f.dimension.get("bucket") == "recovery")
        assert recov.value == pytest.approx(0.35)


class TestFindingsEndgameStartVsEnd:
    """Unit tests for _findings_endgame_start_vs_end (Phase 82 D-16/D-17/D-18/D-19/D-20).

    Phase 102 UAT: emitter now returns FOUR findings in UI-card order —
    endgame_score, non_endgame_score, entry_eval_pawns, entry_expected_score.
    Assertions are keyed by metric (via `_by_metric`) so they survive future
    reordering. Covers independent per-tile gates, zone boundary dispatch via
    assign_zone, and is_headline_eligible = (sample_quality != "thin").
    """

    @staticmethod
    def _by_metric(findings: list[Any]) -> dict[str, Any]:
        return {f.metric: f for f in findings}

    def _make_overview(
        self,
        *,
        entry_eval_mean_pawns: float = 0.0,
        entry_eval_n: int = 50,
        wins: int = 25,
        draws: int = 10,
        losses: int = 15,
        non_wins: int = 20,
        non_draws: int = 10,
        non_losses: int = 20,
        entry_expected_score: float = 0.50,
        entry_expected_score_n: int = 50,
    ) -> Any:
        """Build a minimal EndgameOverviewResponse for endgame_start_vs_end tests."""
        from app.schemas.endgames import (
            EndgameOverviewResponse,
            EndgamePerformanceResponse,
            EndgameWDLSummary,
        )

        total = wins + draws + losses
        non_total = non_wins + non_draws + non_losses
        perf = EndgamePerformanceResponse.model_construct(
            entry_eval_mean_pawns=entry_eval_mean_pawns,
            entry_eval_n=entry_eval_n,
            entry_expected_score=entry_expected_score,
            entry_expected_score_n=entry_expected_score_n,
            endgame_wdl=EndgameWDLSummary(
                wins=wins,
                draws=draws,
                losses=losses,
                total=total,
                win_pct=wins / total * 100 if total else 0.0,
                draw_pct=draws / total * 100 if total else 0.0,
                loss_pct=losses / total * 100 if total else 0.0,
            ),
            non_endgame_wdl=EndgameWDLSummary(
                wins=non_wins,
                draws=non_draws,
                losses=non_losses,
                total=non_total,
                win_pct=non_wins / non_total * 100 if non_total else 0.0,
                draw_pct=non_draws / non_total * 100 if non_total else 0.0,
                loss_pct=non_losses / non_total * 100 if non_total else 0.0,
            ),
            endgame_win_rate=wins / total * 100 if total else 0.0,
        )
        return EndgameOverviewResponse.model_construct(performance=perf)

    def test_returns_four_findings_in_canonical_ui_order(self) -> None:
        """Phase 102 UAT: all gates pass -> FOUR findings, score cards leading."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_mean_pawns=0.62)
        findings = _findings_endgame_start_vs_end(response, "all_time")

        assert [f.metric for f in findings] == [
            "endgame_score",
            "non_endgame_score",
            "entry_eval_pawns",
            "entry_expected_score",
        ]

    def test_empty_entry_eval_when_n_eval_lt_10(self) -> None:
        """entry_eval_n < 10 -> entry_eval_pawns empty; endgame_score still populated."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_n=5)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_eval_pawns"].sample_quality == "thin"
        assert tiles["entry_eval_pawns"].is_headline_eligible is False
        assert tiles["endgame_score"].sample_quality != "thin"

    def test_empty_endgame_score_when_total_lt_10(self) -> None:
        """endgame_wdl.total < 10 -> endgame_score empty; entry_eval_pawns populated."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_n=50, wins=3, draws=1, losses=1)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["endgame_score"].sample_quality == "thin"
        assert tiles["endgame_score"].is_headline_eligible is False
        assert tiles["entry_eval_pawns"].sample_quality != "thin"

    def test_empty_both_score_and_eval_when_both_lt_10(self) -> None:
        """Both pre-existing gates fail -> endgame_score and entry_eval_pawns empty."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_n=5, wins=2, draws=1, losses=2)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_eval_pawns"].sample_quality == "thin"
        assert tiles["endgame_score"].sample_quality == "thin"

    def test_entry_eval_at_n_10_is_populated_adequate(self) -> None:
        """Boundary: entry_eval_n == 10 (the strict-`<` floor) -> populated, adequate.

        Phase 82 D-17 gates on `n_eval < 10`. n=10 must NOT be empty. Pairs with
        SAMPLE_QUALITY_BANDS["endgame_start_vs_end"] = (10, 50) which classifies
        n=10 as `adequate` (`thin` is `< 10`).
        """
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_mean_pawns=0.30, entry_eval_n=10)
        eval_tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "entry_eval_pawns"
        ]

        assert eval_tile.sample_size == 10
        assert eval_tile.sample_quality == "adequate"
        assert eval_tile.is_headline_eligible is True

    def test_endgame_score_at_total_10_is_populated_adequate(self) -> None:
        """Boundary: endgame_wdl.total == 10 -> endgame_score populated, adequate."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_n=50, wins=5, draws=2, losses=3)
        score_tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "endgame_score"
        ]

        assert score_tile.sample_size == 10
        assert score_tile.sample_quality == "adequate"
        assert score_tile.is_headline_eligible is True

    def test_entry_eval_at_n_9_is_thin(self) -> None:
        """Boundary: entry_eval_n == 9 (just below the floor) -> empty/thin."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_n=9)
        eval_tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "entry_eval_pawns"
        ]

        assert eval_tile.sample_quality == "thin"
        assert eval_tile.is_headline_eligible is False

    def test_zone_strong_for_entry_eval_above_band(self) -> None:
        """entry_eval_mean_pawns = 1.00 -> zone = 'strong' (above typical_upper=0.75)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_mean_pawns=1.00)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_eval_pawns"].zone == "strong"

    def test_zone_weak_for_entry_eval_below_band(self) -> None:
        """entry_eval_mean_pawns = -1.00 -> zone = 'weak' (below typical_lower=-0.75)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_mean_pawns=-1.00)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_eval_pawns"].zone == "weak"

    def test_zone_typical_for_entry_eval_inside_band(self) -> None:
        """entry_eval_mean_pawns = 0.30 -> zone = 'typical' (inside [-0.75, 0.75])."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_mean_pawns=0.30)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_eval_pawns"].zone == "typical"

    def test_zone_strong_for_endgame_score_above_band(self) -> None:
        """wins=12, draws=4, losses=4 -> score=14/20=0.70 -> zone='strong'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(wins=12, draws=4, losses=4)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["endgame_score"].zone == "strong"

    def test_zone_weak_for_endgame_score_below_band(self) -> None:
        """wins=4, draws=4, losses=12 -> score=6/20=0.30 -> zone='weak'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(wins=4, draws=4, losses=12)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["endgame_score"].zone == "weak"

    # ------------------------------------------------------------------
    # Phase 102 UAT: non_endgame_score tile.
    # ------------------------------------------------------------------

    def test_non_endgame_score_value_and_band(self) -> None:
        """non_endgame_score = (w + 0.5d)/total over non_endgame_wdl, same band as endgame_score."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        # non: wins=12, draws=4, losses=4 -> score=14/20=0.70 -> strong (band [0.45, 0.55]).
        response = self._make_overview(non_wins=12, non_draws=4, non_losses=4)
        non_tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "non_endgame_score"
        ]

        assert non_tile.value == pytest.approx(0.70)
        assert non_tile.zone == "strong"
        assert non_tile.sample_size == 20
        assert non_tile.dimension is None
        assert non_tile.series is None

    def test_non_endgame_score_zone_weak_below_band(self) -> None:
        """non score = 6/20 = 0.30 -> zone='weak'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(non_wins=4, non_draws=4, non_losses=12)
        non_tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "non_endgame_score"
        ]

        assert non_tile.zone == "weak"

    def test_non_endgame_score_empty_when_total_lt_10(self) -> None:
        """non_endgame_wdl.total < 10 -> non_endgame_score empty (thin, not headline)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(non_wins=2, non_draws=1, non_losses=2)
        non_tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "non_endgame_score"
        ]

        assert math.isnan(non_tile.value)
        assert non_tile.sample_quality == "thin"
        assert non_tile.is_headline_eligible is False
        assert non_tile.sample_size == 0

    def test_dimension_and_series_are_none(self) -> None:
        """All findings must have dimension=None and series=None (D-19/D-20)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        findings = _findings_endgame_start_vs_end(self._make_overview(), "all_time")

        for f in findings:
            assert f.dimension is None
            assert f.series is None

    def test_subsection_and_window_propagate(self) -> None:
        """All findings carry correct subsection_id and window."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        findings = _findings_endgame_start_vs_end(self._make_overview(), "last_3mo")

        for f in findings:
            assert f.subsection_id == "endgame_start_vs_end"
            assert f.window == "last_3mo"
            assert f.parent_subsection_id is None

    # ------------------------------------------------------------------
    # Phase 83 D-17 / D-19: entry_expected_score tile.
    # ------------------------------------------------------------------

    def test_entry_expected_score_emitted_when_n_at_or_above_10(self) -> None:
        """entry_expected_score_n >= 10 -> tile populated with the correct shape."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_expected_score=0.58, entry_expected_score_n=50)
        tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "entry_expected_score"
        ]

        assert tile.value == pytest.approx(0.58)
        assert tile.zone in {"weak", "typical", "strong"}
        assert tile.dimension is None
        assert tile.trend == "n_a"
        assert tile.sample_size == 50
        assert tile.weekly_points_in_window == 0
        assert tile.parent_subsection_id is None
        assert tile.subsection_id == "endgame_start_vs_end"
        assert tile.is_headline_eligible is True

    def test_entry_expected_score_empty_when_n_below_10(self) -> None:
        """entry_expected_score_n < 10 -> tile empty (thin, NaN value, not headline)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_expected_score=0.62, entry_expected_score_n=9)
        tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "entry_expected_score"
        ]

        assert math.isnan(tile.value)
        assert tile.zone == "typical"
        assert tile.sample_quality == "thin"
        assert tile.is_headline_eligible is False
        assert tile.sample_size == 0

    def test_entry_expected_score_zone_strong_above_band(self) -> None:
        """entry_expected_score=0.60 (above typical_upper=0.55) -> zone='strong'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_expected_score=0.60, entry_expected_score_n=50)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_expected_score"].zone == "strong"

    def test_entry_expected_score_zone_weak_below_band(self) -> None:
        """entry_expected_score=0.40 (below typical_lower=0.45) -> zone='weak'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_expected_score=0.40, entry_expected_score_n=50)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_expected_score"].zone == "weak"

    def test_no_verdict_field(self) -> None:
        """Phase 82 D-06 / Phase 83 D-19: SubsectionFinding has NO `verdict` field.

        Guards against a future regression that re-adds a sig-test signal —
        per memory `feedback_llm_significance_signal.md`, the LLM narrates
        strictly by zone, never by p-value or sig-test outcome.
        """
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_expected_score=0.58, entry_expected_score_n=50)
        tile = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))[
            "entry_expected_score"
        ]

        assert not hasattr(tile, "verdict")
        assert "verdict" not in tile.model_dump()

    def test_entry_expected_score_independent_gate_from_other_tiles(self) -> None:
        """Phase 83 D-19: entry_expected_score gate is independent of the other tiles.

        The score / eval tiles may be populated while entry_expected_score is
        empty when only the expected-score backfill has not yet completed.
        """
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(
            entry_eval_mean_pawns=0.30,
            entry_eval_n=50,
            entry_expected_score=0.58,
            entry_expected_score_n=5,  # thin
        )
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_eval_pawns"].sample_quality != "thin"
        assert tiles["endgame_score"].sample_quality != "thin"
        assert tiles["entry_expected_score"].sample_quality == "thin"

    def test_existing_tiles_unchanged_by_new_findings(self) -> None:
        """Adding non_endgame_score must not regress entry_eval/endgame_score shape."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        response = self._make_overview(entry_eval_mean_pawns=0.30)
        tiles = self._by_metric(_findings_endgame_start_vs_end(response, "all_time"))

        assert tiles["entry_eval_pawns"].value == pytest.approx(0.30)
        assert tiles["entry_eval_pawns"].sample_size == 50
        # score = (25 + 0.5*10) / 50 = 0.60
        assert tiles["endgame_score"].value == pytest.approx(0.60)
        assert tiles["endgame_score"].sample_size == 50


class TestFindingsScoreGap:
    """Unit tests for _findings_score_gap (Phase 102 UAT).

    The dedicated `score_gap` subsection mirrors the UI "Endgame Score
    Differences" card: achievable_score_gap ("Eval Score Gap") first, then
    score_gap ("Endgame Score Gap"). Relocated from the retired `overall`
    subsection, with achievable_score_gap newly wired as a finding.
    """

    @staticmethod
    def _by_metric(findings: list[Any]) -> dict[str, Any]:
        return {f.metric: f for f in findings}

    def _make_overview(
        self,
        *,
        score_difference: float = -0.08,
        achievable_score_gap: float = -0.03,
        entry_expected_score_n: int = 60,
        endgame_total: int = 240,
        non_endgame_total: int = 700,
    ) -> Any:
        from app.schemas.endgames import (
            EndgameOverviewResponse,
            EndgamePerformanceResponse,
            EndgameWDLSummary,
            ScoreGapMaterialResponse,
        )

        def _wdl(total: int) -> Any:
            return EndgameWDLSummary(
                wins=total,
                draws=0,
                losses=0,
                total=total,
                win_pct=100.0 if total else 0.0,
                draw_pct=0.0,
                loss_pct=0.0,
            )

        perf = EndgamePerformanceResponse.model_construct(
            achievable_score_gap=achievable_score_gap,
            entry_expected_score_n=entry_expected_score_n,
            endgame_wdl=_wdl(endgame_total),
            non_endgame_wdl=_wdl(non_endgame_total),
        )
        return EndgameOverviewResponse.model_construct(
            performance=perf,
            score_gap_material=ScoreGapMaterialResponse.model_construct(
                score_difference=score_difference
            ),
        )

    def test_emits_two_findings_in_card_order(self) -> None:
        from app.services.insights_service import _findings_score_gap

        findings = _findings_score_gap(self._make_overview(), "all_time")

        assert [f.metric for f in findings] == ["achievable_score_gap", "score_gap"]
        for f in findings:
            assert f.subsection_id == "score_gap"
            assert f.dimension is None
            assert f.series is None
            assert f.parent_subsection_id is None

    def test_score_gap_value_and_zone(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tiles = self._by_metric(
            _findings_score_gap(self._make_overview(score_difference=-0.15), "all_time")
        )
        sg = tiles["score_gap"]
        assert sg.value == pytest.approx(-0.15)
        assert sg.zone == "weak"  # below score_gap band lower bound (-0.10)
        assert sg.sample_size == 940  # 240 + 700

    def test_achievable_score_gap_value_and_gate(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tiles = self._by_metric(
            _findings_score_gap(
                self._make_overview(achievable_score_gap=0.04, entry_expected_score_n=80),
                "all_time",
            )
        )
        asg = tiles["achievable_score_gap"]
        assert asg.value == pytest.approx(0.04)
        assert asg.sample_size == 80
        assert asg.zone in {"weak", "typical", "strong"}

    def test_achievable_score_gap_empty_when_n_below_10(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tiles = self._by_metric(
            _findings_score_gap(self._make_overview(entry_expected_score_n=5), "all_time")
        )
        asg = tiles["achievable_score_gap"]
        assert math.isnan(asg.value)
        assert asg.sample_quality == "thin"
        assert asg.is_headline_eligible is False

    def test_score_gap_empty_when_no_games(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tiles = self._by_metric(
            _findings_score_gap(
                self._make_overview(endgame_total=0, non_endgame_total=0), "all_time"
            )
        )
        assert math.isnan(tiles["score_gap"].value)
        assert tiles["score_gap"].sample_quality == "thin"


# ---------------------------------------------------------------------------
# TestComputePlayerProfile — v27 Fix B sparse-history fallback.
# ---------------------------------------------------------------------------


class TestComputePlayerProfile:
    """Tests for `compute_player_profile`, including v27 Fix B sparse fallback.

    See `.planning/debug/llm-prompt-missing-sections.md`.
    """

    @staticmethod
    def _combo(
        platform: str,
        time_control: str,
        n_points: int,
        *,
        start_date: str = "2026-03-01",
    ) -> Any:
        """Build a synthetic EndgameEloTimelineCombo with `n_points` weekly buckets."""
        import datetime as _dt

        from app.schemas.endgames import (
            EndgameEloTimelineCombo,
            EndgameEloTimelinePoint,
        )

        first = _dt.date.fromisoformat(start_date)
        points = [
            EndgameEloTimelinePoint(
                date=(first + _dt.timedelta(weeks=i)).isoformat(),
                endgame_elo=1400 + i,
                non_endgame_elo=1380 + i,
                actual_elo=1350 + i,
                endgame_games_in_window=50,
                per_week_endgame_games=10,
            )
            for i in range(n_points)
        ]
        return EndgameEloTimelineCombo(
            combo_key=f"{platform.replace('.', '_')}_{time_control}",
            platform=cast(Any, platform),
            time_control=cast(Any, time_control),
            points=points,
        )

    def test_returns_none_when_no_combo_has_any_points(self) -> None:
        from app.services.insights_service import compute_player_profile

        assert compute_player_profile([]) is None

    def test_full_quality_when_at_least_one_combo_clears_floor(self) -> None:
        """Both combos with >= 20 weekly points produce quality='full' entries."""
        from app.services.insights_service import (
            _PLAYER_PROFILE_MIN_POINTS,
            compute_player_profile,
        )

        combos = [
            self._combo("chess.com", "blitz", n_points=_PLAYER_PROFILE_MIN_POINTS + 5),
            self._combo("chess.com", "rapid", n_points=_PLAYER_PROFILE_MIN_POINTS + 1),
        ]
        result = compute_player_profile(combos)
        assert result is not None
        assert len(result) == 2
        assert all(e.quality == "full" for e in result)

    def test_full_entries_keep_subfloor_combos_out(self) -> None:
        """When at least one combo qualifies for full, sub-floor combos are dropped."""
        from app.services.insights_service import (
            _PLAYER_PROFILE_MIN_POINTS,
            compute_player_profile,
        )

        combos = [
            self._combo("chess.com", "blitz", n_points=_PLAYER_PROFILE_MIN_POINTS + 5),
            self._combo("chess.com", "rapid", n_points=3),  # below floor
        ]
        result = compute_player_profile(combos)
        assert result is not None
        # Only the full-quality blitz combo is emitted; rapid is silently skipped
        # because at least one combo cleared the floor (full mode).
        assert len(result) == 1
        assert result[0].time_control == "blitz"
        assert result[0].quality == "full"

    def test_sparse_fallback_when_no_combo_clears_floor(self) -> None:
        """v27 Fix B: when ALL combos are below the full floor, emit them all as sparse.

        This is the user-49 / user-89 case from the debug session — short-history
        users with only 5-9 weekly buckets per combo. Without this fallback the
        `## Player profile` block vanishes and the LLM hallucinates the schema-
        mandated `player_profile` output field from non-existent anchor data.
        """
        from app.services.insights_service import compute_player_profile

        combos = [
            self._combo("chess.com", "bullet", n_points=7),
            self._combo("chess.com", "blitz", n_points=5),
        ]
        result = compute_player_profile(combos)

        assert result is not None
        assert len(result) == 2
        assert all(e.quality == "sparse" for e in result)
        # Sort order is games desc — bullet (7 pts × 10 games = 70) before blitz (50).
        assert result[0].time_control == "bullet"
        assert result[0].all_time_buckets == 7
        assert result[1].time_control == "blitz"
        assert result[1].all_time_buckets == 5
        # current_elo is the most recent bucket's actual_elo (1350 + 7 - 1 = 1356
        # for bullet; 1350 + 5 - 1 = 1354 for blitz).
        assert result[0].current_elo == 1356
        assert result[1].current_elo == 1354


class TestD15LlmPathInvariant:
    """D-15 regression: _findings_conversion_recovery_by_type must read
    response.stats.categories (pooled) only — never categories_by_tc.

    Adding categories_by_tc to EndgameStatsResponse must NOT change the
    findings produced by the LLM insights path. This test asserts identical
    outputs with and without categories_by_tc populated, so any accidental
    coupling to the new field is caught immediately.
    """

    @staticmethod
    def _make_category(
        endgame_class: str,
        conv_games: int,
        conv_wins: int,
        recov_games: int,
        recov_wins: int,
    ) -> Any:
        """Build a minimal EndgameCategoryStats for insights path smoke testing."""
        from app.schemas.endgames import (
            ConversionRecoveryStats,
            EndgameCategoryStats,
        )

        conv_draws = 0
        conv_losses = conv_games - conv_wins - conv_draws
        recov_draws = 0
        recovery_saves = recov_wins + recov_draws
        return EndgameCategoryStats(
            endgame_class=cast(Any, endgame_class),
            label=cast(Any, endgame_class.capitalize()),
            wins=conv_wins,
            draws=recov_draws,
            losses=conv_losses,
            total=conv_games + recov_games,
            win_pct=round(conv_wins / (conv_games + recov_games) * 100, 1),
            draw_pct=0.0,
            loss_pct=round(conv_losses / (conv_games + recov_games) * 100, 1),
            conversion=ConversionRecoveryStats(
                conversion_pct=(round(conv_wins / conv_games * 100, 1) if conv_games else 0.0),
                conversion_games=conv_games,
                conversion_wins=conv_wins,
                conversion_draws=conv_draws,
                conversion_losses=conv_losses,
                recovery_pct=(round(recovery_saves / recov_games * 100, 1) if recov_games else 0.0),
                recovery_games=recov_games,
                recovery_saves=recovery_saves,
                recovery_wins=recov_wins,
                recovery_draws=recov_draws,
                opponent_conversion_pct=None,
                opponent_conversion_games=recov_games,
                opponent_recovery_pct=None,
                opponent_recovery_games=conv_games,
            ),
        )

    def _make_stats(
        self,
        categories: list[Any],
        categories_by_tc: Any = None,
    ) -> Any:
        """Build an EndgameStatsResponse with or without categories_by_tc."""
        from app.schemas.endgames import EndgameStatsResponse

        return EndgameStatsResponse(
            categories=categories,
            total_games=100,
            endgame_games=50,
            categories_by_tc=categories_by_tc,
        )

    def _make_response(self, stats: Any) -> Any:
        """Build a minimal EndgameOverviewResponse containing the given stats."""
        return EndgameOverviewResponse.model_construct(
            stats=stats,
            time_pressure_chart=None,
            performance=None,
        )

    def test_findings_identical_with_and_without_categories_by_tc(self) -> None:
        """D-15 invariant: adding categories_by_tc must NOT change LLM findings.

        The _findings_conversion_recovery_by_type function must continue to
        read response.stats.categories (pooled) and produce identical findings
        whether categories_by_tc is None or populated with data.
        """
        from app.services.insights_service import _findings_conversion_recovery_by_type

        categories = [
            self._make_category("rook", conv_games=20, conv_wins=16, recov_games=10, recov_wins=3),
            self._make_category("pawn", conv_games=15, conv_wins=12, recov_games=8, recov_wins=2),
        ]

        # Build a populated categories_by_tc (different data from pooled)
        tc_cats = {
            "blitz": [
                self._make_category("rook", conv_games=5, conv_wins=2, recov_games=3, recov_wins=1)
            ]
        }

        stats_without = self._make_stats(categories, categories_by_tc=None)
        stats_with = self._make_stats(categories, categories_by_tc=tc_cats)
        resp_without = self._make_response(stats_without)
        resp_with = self._make_response(stats_with)

        findings_without = _findings_conversion_recovery_by_type(resp_without, "all_time")
        findings_with = _findings_conversion_recovery_by_type(resp_with, "all_time")

        # Both must produce identical findings (same length, same values)
        assert len(findings_without) == len(findings_with), (
            "D-15 violated: findings count differs when categories_by_tc is set"
        )
        for f_without, f_with in zip(findings_without, findings_with, strict=True):
            assert f_without.value == f_with.value, (
                f"D-15 violated: finding value differs for metric={f_without.metric}, "
                f"dim={f_without.dimension}"
            )
            assert f_without.zone == f_with.zone, (
                f"D-15 violated: finding zone differs for metric={f_without.metric}"
            )

    def test_llm_path_does_not_reference_categories_by_tc(self) -> None:
        """Static assertion: _findings_conversion_recovery_by_type source must not
        reference categories_by_tc (prevents accidental coupling)."""
        import inspect

        from app.services import insights_service

        source = inspect.getsource(insights_service._findings_conversion_recovery_by_type)  # type: ignore[attr-defined]
        assert "categories_by_tc" not in source, (
            "D-15 violated: _findings_conversion_recovery_by_type references "
            "categories_by_tc — the LLM path must read only response.stats.categories"
        )


# ---------------------------------------------------------------------------
# TestNetTimeoutRateFinding — Phase 102 (Plan 01): net_timeout_rate is now a
# real n-weighted scalar finding derived from card.net_timeout_rate (fraction
# → x100 to match avg_clock_diff_pct scale). Previously an always-empty stub.
# ---------------------------------------------------------------------------


class TestNetTimeoutRateFinding:
    """net_timeout_rate is a real n-weighted (×100) scalar finding when cards exist."""

    def _make_time_pressure_cards_response(
        self,
        cards_data: list[dict[str, Any]],
    ) -> Any:
        """Build a minimal TimePressureCardsResponse with given card data."""
        from app.schemas.endgames import (
            ClockGapBullet,
            PressureQuintileBullet,
            TimePressureCardsResponse,
            TimePressureTcCard,
        )

        cards = []
        for cd in cards_data:
            card = TimePressureTcCard(
                tc=cd["tc"],
                total=cd["total"],
                net_timeout_rate=cd["net_timeout_rate"],
                clock_gap=ClockGapBullet(
                    n=cd.get("clock_gap_n", cd["total"]),
                    mean_diff_pct=cd.get("mean_diff_pct", 0.0),
                    p_value=None,
                    ci_low=None,
                    ci_high=None,
                ),
                quintiles=[
                    PressureQuintileBullet(
                        quintile_index=q,
                        quintile_label=f"{q * 20}-{q * 20 + 20}%",
                        n=0,
                        n_opp=0,
                        delta=0.0,
                        p_value=None,
                        ci_low=None,
                        ci_high=None,
                        opp_score=None,
                    )
                    for q in range(5)
                ],
            )
            cards.append(card)
        return TimePressureCardsResponse(cards=cards)

    def _make_overview_with_cards(self, cards_data: list[dict[str, Any]]) -> Any:
        """Build a minimal EndgameOverviewResponse containing TimePressureCardsResponse."""
        time_pressure_cards = self._make_time_pressure_cards_response(cards_data)
        return EndgameOverviewResponse.model_construct(
            time_pressure_cards=time_pressure_cards,
        )

    def test_net_timeout_rate_non_nan_when_cards_exist(self) -> None:
        """With ≥1 card carrying a non-zero net_timeout_rate and total>0, the
        emitted finding has a non-NaN value and a zone assigned (not thin/empty).

        Phase 102 (Plan 01): this was previously always NaN (empty stub).
        """
        from app.services.insights_service import _findings_time_pressure_at_entry

        response = self._make_overview_with_cards(
            [
                {"tc": "blitz", "total": 100, "net_timeout_rate": 0.02},
            ]
        )
        findings = _findings_time_pressure_at_entry(response, window="all_time")

        timeout_findings = [f for f in findings if f.metric == "net_timeout_rate"]
        assert len(timeout_findings) == 1
        f = timeout_findings[0]
        assert not math.isnan(f.value), "net_timeout_rate must not be NaN when cards exist"
        assert f.zone != "thin", "net_timeout_rate zone must be assigned when cards exist"
        assert f.sample_quality != "thin" or f.sample_size > 0, (
            "net_timeout_rate finding with >0 total games must not be thin"
        )

    def test_net_timeout_rate_scaled_by_100(self) -> None:
        """net_timeout_rate fraction is multiplied ×100 to match avg_clock_diff_pct scale.

        0.005 fraction should yield 0.5 (percentage-point scalar) in the finding.
        """
        from app.services.insights_service import _findings_time_pressure_at_entry

        response = self._make_overview_with_cards(
            [
                {"tc": "blitz", "total": 200, "net_timeout_rate": 0.005},
            ]
        )
        findings = _findings_time_pressure_at_entry(response, window="all_time")
        timeout_findings = [f for f in findings if f.metric == "net_timeout_rate"]
        assert len(timeout_findings) == 1
        # 0.005 fraction × 100 = 0.5 percentage points
        assert abs(timeout_findings[0].value - 0.5) < 1e-9

    def test_net_timeout_rate_n_weighted_across_cards(self) -> None:
        """n-weighted mean: two cards with different net_timeout_rate and total."""
        from app.services.insights_service import _findings_time_pressure_at_entry

        # blitz: 0.01 fraction × 100 = 1.0 pp, 100 games
        # rapid: 0.03 fraction × 100 = 3.0 pp, 300 games
        # expected weighted mean: (1.0 * 100 + 3.0 * 300) / 400 = 1000/400 = 2.5
        response = self._make_overview_with_cards(
            [
                {"tc": "blitz", "total": 100, "net_timeout_rate": 0.01},
                {"tc": "rapid", "total": 300, "net_timeout_rate": 0.03},
            ]
        )
        findings = _findings_time_pressure_at_entry(response, window="all_time")
        timeout_findings = [f for f in findings if f.metric == "net_timeout_rate"]
        assert len(timeout_findings) == 1
        assert abs(timeout_findings[0].value - 2.5) < 1e-9

    def test_net_timeout_rate_empty_stub_when_no_cards(self) -> None:
        """Empty cards list → empty finding (NaN, thin, not headline eligible)."""
        from app.services.insights_service import _findings_time_pressure_at_entry

        response = self._make_overview_with_cards([])
        findings = _findings_time_pressure_at_entry(response, window="all_time")
        timeout_findings = [f for f in findings if f.metric == "net_timeout_rate"]
        assert len(timeout_findings) == 1
        f = timeout_findings[0]
        assert math.isnan(f.value)
        assert f.sample_quality == "thin"
        assert f.is_headline_eligible is False

    def test_net_timeout_rate_is_headline_eligible_with_sufficient_games(self) -> None:
        """Sufficient total games makes net_timeout_rate headline eligible."""
        from app.services.insights_service import _findings_time_pressure_at_entry

        # Use a total large enough to produce "adequate" or "rich" quality
        response = self._make_overview_with_cards(
            [
                {"tc": "blitz", "total": 200, "net_timeout_rate": 0.01},
            ]
        )
        findings = _findings_time_pressure_at_entry(response, window="all_time")
        timeout_findings = [f for f in findings if f.metric == "net_timeout_rate"]
        assert len(timeout_findings) == 1
        assert timeout_findings[0].is_headline_eligible is True
