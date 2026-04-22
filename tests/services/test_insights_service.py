"""Tests for app/services/insights_service.py — Phase 63 Plan 05.

Coverage by requirement:

- FIND-01 (layering): TestComputeFindingsLayering asserts that
  `insights_service` imports no repositories and never calls
  `asyncio.gather`, and that `compute_findings` issues exactly two
  sequential calls to `endgame_service.get_endgame_overview`
  (recency=None then recency="3months").
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
from typing import cast
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
        b = a.model_copy(
            update={"as_of": datetime.datetime(2099, 1, 1, tzinfo=datetime.UTC)}
        )
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
            "endgame_elo_timeline", "all_time", "endgame_elo_gap", dimension=dim,
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
                    FilterContext(), session=AsyncMock(), user_id=1,
                )
            except Exception:
                # compute_findings may fail downstream because model_construct
                # skips required fields; we only care about the two-call
                # invariant on the mocked overview service here.
                pass
            assert mocked.await_count == 2

    @pytest.mark.asyncio
    async def test_first_call_uses_recency_none(self) -> None:
        """First call passes recency=None (all_time window)."""
        mock_response = EndgameOverviewResponse.model_construct()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            try:
                await compute_findings(
                    FilterContext(), session=AsyncMock(), user_id=1,
                )
            except Exception:
                pass
            first_kwargs = mocked.await_args_list[0].kwargs
            assert first_kwargs["recency"] is None

    @pytest.mark.asyncio
    async def test_second_call_uses_recency_3months(self) -> None:
        """Second call passes recency='3months' (last_3mo window)."""
        mock_response = EndgameOverviewResponse.model_construct()
        with patch.object(
            insights_module,
            "get_endgame_overview",
            new=AsyncMock(return_value=mock_response),
        ) as mocked:
            try:
                await compute_findings(
                    FilterContext(), session=AsyncMock(), user_id=1,
                )
            except Exception:
                pass
            second_kwargs = mocked.await_args_list[1].kwargs
            assert second_kwargs["recency"] == "3months"

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


class TestComputeFindingsReturnContract:
    """End-to-end wiring of compute_findings → EndgameTabFindings."""

    @pytest.mark.asyncio
    async def test_returns_endgame_tab_findings_with_populated_hash(self) -> None:
        mock_response = EndgameOverviewResponse.model_construct()
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
        mock_response = EndgameOverviewResponse.model_construct()
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
