"""Tests for app/services/insights_service.py — Phase 63 Plan 05, re-based on the
ranked payload in Phase 238 plan 04 (D-04).

Coverage by requirement:

- FIND-01 (layering): TestComputeFindingsLayering asserts that
  `insights_service` imports no repositories and never calls
  `asyncio.gather`, and that `compute_findings` awaits `fetch_ranked_inputs`
  exactly once, then builds the all_time window (`since=None`) and the last_3mo
  window (`since=now-90d`) from the same inputs with `build_ranked_stats`.
- FIND-04 (trend gate): TestComputeTrend covers count-fail, ratio-fail,
  both-pass (improving / declining), and flat (stable).
- FIND-05 (hash stability): TestComputeHash covers the 64-char lowercase
  hex format, `as_of` / `findings_hash` exclusion, value-change
  discrimination, NaN safety, and dict-insertion-order invariance.
- D-04 / D-00b (ranked alignment): TestRankedPayloadAlignment pins that every
  narrated number equals the ranked per-TC value, that last_3mo is the ranked
  subset played in the last 90 days, and that percentile records exist exactly
  for ranked metrics (all per TC).

Additional coverage: TestEmptyFinding verifies the empty-window
convention (value=NaN, zone="typical", is_headline_eligible=False,
sample_quality="thin").

All tests run against synthetic Pydantic instances / helper-built
SubsectionFinding lists — zero DB access. Target runtime < 30s.
"""

from __future__ import annotations

import datetime
import inspect
import math
import re
from typing import Any, NamedTuple, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.insights_service as insights_module
from app.repositories.endgame_ranked_repository import RankedGameRow
from app.schemas.endgames import EndgameRankedStatsResponse, RankedTcStats
from app.schemas.insights import (
    EndgameTabFindings,
    MetricId,
    SampleQuality,
    SubsectionFinding,
    SubsectionId,
    Trend,
    Window,
    Zone,
)
from app.services.endgame_ranked_service import RankedInputs
from app.services.endgame_zones import (
    TREND_MIN_SLOPE_VOL_RATIO,
    TREND_MIN_WEEKLY_POINTS,
)
from app.services.insights_service import (
    LAST_3MO_WINDOW_DAYS,
    _compute_hash,
    _compute_trend,
    _empty_finding,
    build_findings,
    compute_findings,
)
from tests.services.ranked_payload_fixtures import (
    make_category,
    make_elo_combo,
    make_metric,
    make_ranked_tc,
    make_score_timeline,
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

    def test_hash_differs_on_ranked_payload_change(self) -> None:
        """A different ranked payload (Phase 238) -> different hash (cache discrimination)."""
        a = self._base_findings().model_copy(update={"ranked_tcs": [make_ranked_tc("blitz")]})
        b = a.model_copy(
            update={
                "ranked_tcs": [
                    make_ranked_tc(
                        "blitz", metrics={"score_gap": make_metric("score_gap", value=0.31)}
                    )
                ]
            }
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
# TestComputeFindingsLayering — FIND-01: service-only access, ONE sequential
# fetch of the ranked inputs, no asyncio.gather, no repository imports.
# ---------------------------------------------------------------------------


def _ranked_response(*tcs: RankedTcStats) -> EndgameRankedStatsResponse:
    return EndgameRankedStatsResponse(tcs=list(tcs))


class TestComputeFindingsLayering:
    """FIND-01: insights_service consumes only the ranked service (Phase 238, D-04)."""

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

    def test_compute_findings_takes_no_filter_argument(self) -> None:
        """D-04: the only inputs are the session and the user id."""
        assert list(inspect.signature(compute_findings).parameters) == ["session", "user_id"]

    @pytest.mark.asyncio
    async def test_fetches_ranked_inputs_once_and_builds_both_windows(self) -> None:
        """One fetch, two pure builds: all_time (since=None) then last_3mo (since=now-90d)."""
        sentinel = RankedInputs(games_by_tc={})
        fetch = AsyncMock(return_value=sentinel)
        build = MagicMock(return_value=_ranked_response(make_ranked_tc("blitz")))
        session = AsyncMock()
        before = datetime.datetime.now(datetime.UTC)
        with (
            patch.object(insights_module, "fetch_ranked_inputs", new=fetch),
            patch.object(insights_module, "build_ranked_stats", new=build),
        ):
            await compute_findings(session, 7)
        after = datetime.datetime.now(datetime.UTC)

        assert fetch.await_count == 1
        assert fetch.await_args is not None
        assert fetch.await_args.args == (session,)
        assert fetch.await_args.kwargs == {"user_id": 7}

        assert build.call_count == 2
        all_time_call, last_3mo_call = build.call_args_list
        assert all_time_call.args == (sentinel,)
        assert all_time_call.kwargs == {}  # since=None: the full ranked sample
        assert last_3mo_call.args == (sentinel,)
        since = last_3mo_call.kwargs["since"]
        window = datetime.timedelta(days=LAST_3MO_WINDOW_DAYS)
        assert before - window <= since <= after - window

    @pytest.mark.asyncio
    async def test_fetch_failure_is_captured_and_reraised(self) -> None:
        """A failing fetch reaches Sentry once and propagates (CLAUDE.md §Sentry)."""
        boom = RuntimeError("db down")
        with (
            patch.object(insights_module, "fetch_ranked_inputs", new=AsyncMock(side_effect=boom)),
            patch.object(insights_module.sentry_sdk, "capture_exception") as capture,
            patch.object(insights_module.sentry_sdk, "set_context") as set_context,
            pytest.raises(RuntimeError),
        ):
            await compute_findings(AsyncMock(), 7)
        capture.assert_called_once_with(boom)
        set_context.assert_called_once_with("insights", {"user_id": 7})


# ---------------------------------------------------------------------------
# TestComputeFindingsReturnContract — REVIEW WR-03: end-to-end contract that
# compute_findings returns an EndgameTabFindings whose findings_hash is
# populated (64-char lowercase hex) so a refactor cannot silently drop the
# hash assignment.
# ---------------------------------------------------------------------------


class TestComputeFindingsReturnContract:
    """End-to-end wiring of compute_findings → EndgameTabFindings."""

    @staticmethod
    def _patches(*tcs: RankedTcStats) -> Any:
        return (
            patch.object(
                insights_module,
                "fetch_ranked_inputs",
                new=AsyncMock(return_value=RankedInputs(games_by_tc={})),
            ),
            patch.object(
                insights_module,
                "build_ranked_stats",
                new=MagicMock(return_value=_ranked_response(*tcs)),
            ),
        )

    @pytest.mark.asyncio
    async def test_returns_endgame_tab_findings_with_populated_hash(self) -> None:
        fetch_patch, build_patch = self._patches(make_ranked_tc("blitz"))
        with fetch_patch, build_patch:
            result = await compute_findings(AsyncMock(), 1)

        assert isinstance(result, EndgameTabFindings)
        assert re.fullmatch(r"[0-9a-f]{64}", result.findings_hash), (
            f"findings_hash must be 64-char lowercase hex, got: {result.findings_hash!r}"
        )
        assert result.findings, "ranked TC must yield findings"
        assert [t.tc for t in result.ranked_tcs] == ["blitz"]
        assert not hasattr(result, "filters")

    @pytest.mark.asyncio
    async def test_hash_is_stable_across_two_invocations_end_to_end(self) -> None:
        """Calling compute_findings twice with the same inputs produces the
        same findings_hash (as_of differs between calls but is excluded)."""
        fetch_patch, build_patch = self._patches(make_ranked_tc("blitz"), make_ranked_tc("rapid"))
        with fetch_patch, build_patch:
            first = await compute_findings(AsyncMock(), 1)
            second = await compute_findings(AsyncMock(), 1)

        assert first.findings_hash == second.findings_hash

    @pytest.mark.asyncio
    async def test_empty_ranked_sample_yields_empty_findings(self) -> None:
        """D-10: an empty ranked sample is a valid (empty) payload, not an error."""
        fetch_patch, build_patch = self._patches()
        with fetch_patch, build_patch:
            result = await compute_findings(AsyncMock(), 1)

        # Only the standing empty ELO placeholders remain (NaN value, dropped when rendered).
        assert all(math.isnan(f.value) and f.sample_size == 0 for f in result.findings)
        assert result.ranked_tcs == []
        assert result.player_profile is None
        assert result.per_tc_metric_percentiles is None
        assert result.cohort_anchors is None
        assert re.fullmatch(r"[0-9a-f]{64}", result.findings_hash)


# ---------------------------------------------------------------------------
# TestRankedPayloadAlignment — D-04 / D-00b: every narrated number is the ranked
# value the Stats tab shows; last_3mo is the ranked subset; percentile records
# exist exactly for ranked metrics.
# ---------------------------------------------------------------------------


class _PerfRow(NamedTuple):
    """Shape of the repository's performance rows (indexed by the WDL summary helper)."""

    played_at: datetime.datetime
    result: str
    user_color: str
    platform: str
    time_control_bucket: str


_NOW = datetime.datetime.now(datetime.UTC)
_RECENT_DAYS = 10  # inside the last-90-day window
_OLD_DAYS = 200  # outside it


def _expected_value(tc_stats: RankedTcStats, f: SubsectionFinding) -> float | None:
    """The ranked value a finding must narrate (None for metrics checked elsewhere)."""
    m = tc_stats.metrics
    overall = tc_stats.overall
    flow = overall.entry_flow
    eg, ne = overall.endgame_wdl, overall.non_endgame_wdl
    by_metric: dict[str, float | None] = {
        "score_gap": m["score_gap"].value,
        "achievable_score_gap": m["achievable_score_gap"].value,
        "conversion_win_pct": m["conversion_rate"].value,
        "parity_score_pct": m["parity_rate"].value,
        "recovery_save_pct": m["recovery_rate"].value,
        "score_gap_conv": m["score_gap_conv"].value,
        "score_gap_parity": m["score_gap_parity"].value,
        "score_gap_recov": m["recovery_score_gap"].value,
        "endgame_score": (eg.wins + 0.5 * eg.draws) / eg.total,
        "non_endgame_score": (ne.wins + 0.5 * ne.draws) / ne.total,
        "entry_eval_pawns": flow.entry_eval_mean_pawns,
        "entry_expected_score": flow.expected_score,
    }
    return by_metric.get(f.metric)


class TestRankedPayloadAlignment:
    def test_findings_values_equal_ranked_payload(self) -> None:
        """Every all_time finding with a time_control dimension (and no series) carries
        the ranked value of THAT TC: rates and gaps from metrics, scores from the overall
        WDL, entry metrics from entry_flow. Two TCs with different values catch any
        cross-TC mixing or pooling."""
        blitz = make_ranked_tc("blitz")
        rapid = make_ranked_tc(
            "rapid",
            endgame=(40, 5, 15),
            non_endgame=(10, 10, 30),
            entry_eval_mean_pawns=-0.4,
            expected_score=0.42,
            metrics={
                "score_gap": make_metric("score_gap", value=0.17),
                "achievable_score_gap": make_metric("achievable_score_gap", value=-0.06),
                "conversion_rate": make_metric("conversion_rate", value=0.81),
                "parity_rate": make_metric("parity_rate", value=0.44),
                "recovery_rate": make_metric("recovery_rate", value=0.22),
                "score_gap_conv": make_metric("score_gap_conv", value=0.09),
                "score_gap_parity": make_metric("score_gap_parity", value=-0.11),
                "recovery_score_gap": make_metric("recovery_score_gap", value=-0.07),
            },
        )
        result = build_findings([blitz, rapid], [], as_of=_NOW)
        by_tc = {t.tc: t for t in (blitz, rapid)}

        checked = 0
        for f in result.findings:
            if f.window != "all_time" or f.series is not None:
                continue
            assert f.dimension is not None and "endgame_class" not in f.dimension
            tc_stats = by_tc[cast(Any, f.dimension["time_control"])]
            expected = _expected_value(tc_stats, f)
            assert expected is not None, f"unmapped finding metric {f.metric}"
            assert f.value == pytest.approx(expected), (f.subsection_id, f.metric, tc_stats.tc)
            checked += 1
        # 4 start_vs_end + 2 score_gap + 6 metrics, for both TCs.
        assert checked == 2 * (4 + 2 + 6)
        # The two TCs really narrate different numbers (no pooling).
        sg = {
            f.dimension["time_control"]: f.value
            for f in result.findings
            if f.subsection_id == "score_gap" and f.metric == "score_gap" and f.dimension
        }
        assert sg["blitz"] != sg["rapid"]

    def test_overall_findings_are_per_tc_never_pooled(self) -> None:
        result = build_findings([make_ranked_tc("bullet"), make_ranked_tc("rapid")], [], as_of=_NOW)
        for subsection in ("endgame_start_vs_end", "score_gap", "score_timeline"):
            members = [f for f in result.findings if f.subsection_id == subsection]
            assert members, subsection
            assert all(f.dimension and "time_control" in f.dimension for f in members), subsection
            assert {f.dimension["time_control"] for f in members if f.dimension} == {
                "bullet",
                "rapid",
            }

    @staticmethod
    def _game(game_id: int, days_ago: int) -> RankedGameRow:
        return RankedGameRow(
            game_id=game_id,
            played_at=_NOW - datetime.timedelta(days=days_ago),
            platform="lichess",
            time_control_str="180+0",
            user_elo=1500,
            eval_pending=False,
        )

    @staticmethod
    def _row(days_ago: int, outcome: str, *, color: str = "white") -> Any:
        result = {"win": "1-0", "draw": "1/2-1/2", "loss": "0-1"}[outcome]
        return _PerfRow(
            played_at=_NOW - datetime.timedelta(days=days_ago),
            result=result,
            user_color=color,
            platform="lichess",
            time_control_bucket="blitz",
        )

    def _inputs(self, *, old_outcome: str) -> RankedInputs:
        """12 recent endgame wins + 12 recent non-endgame draws; plus 30 OLD games per side
        whose endgame outcome is ``old_outcome`` (non-endgame old games are draws)."""
        recent_eg = [self._row(_RECENT_DAYS + i % 5, "win") for i in range(12)]
        recent_ne = [self._row(_RECENT_DAYS + i % 5, "draw") for i in range(12)]
        old_eg = [self._row(_OLD_DAYS + i, old_outcome) for i in range(30)]
        old_ne = [self._row(_OLD_DAYS + i, "draw") for i in range(30)]
        games = [self._game(i + 1, _RECENT_DAYS + i % 5) for i in range(24)] + [
            self._game(100 + i, _OLD_DAYS + i) for i in range(60)
        ]
        return RankedInputs(
            games_by_tc={"blitz": games},
            endgame_rows=recent_eg + old_eg,
            non_endgame_rows=recent_ne + old_ne,
        )

    @staticmethod
    def _last_3mo(result: EndgameTabFindings, subsection: str, metric: str) -> SubsectionFinding:
        return next(
            f
            for f in result.findings
            if f.window == "last_3mo" and f.subsection_id == subsection and f.metric == metric
        )

    @pytest.mark.asyncio
    async def test_last_3mo_uses_ranked_subset(self) -> None:
        """last_3mo = build_ranked_stats(since=now-90d): games older than 90 days do not
        move it, while the all_time window (the full ranked sample) does."""
        results = {}
        for old_outcome in ("loss", "win"):
            with patch.object(
                insights_module,
                "fetch_ranked_inputs",
                new=AsyncMock(return_value=self._inputs(old_outcome=old_outcome)),
            ):
                results[old_outcome] = await compute_findings(AsyncMock(), 1)

        for result in results.values():
            sg = self._last_3mo(result, "score_gap", "score_gap")
            assert sg.value == pytest.approx(0.5)  # endgame score 1.0 minus non-endgame 0.5
            es = self._last_3mo(result, "endgame_start_vs_end", "endgame_score")
            assert es.value == pytest.approx(1.0)
            assert es.sample_size == 12  # only the recent games

        lost, won = results["loss"], results["win"]
        # Identical last_3mo whatever the old games did ...
        assert self._last_3mo(lost, "score_gap", "score_gap").value == pytest.approx(
            self._last_3mo(won, "score_gap", "score_gap").value
        )

        # ... while all_time moves with them.
        def all_time_gap(r: EndgameTabFindings) -> float:
            return next(
                f.value
                for f in r.findings
                if f.window == "all_time"
                and f.subsection_id == "score_gap"
                and f.metric == "score_gap"
            )

        assert all_time_gap(lost) != pytest.approx(all_time_gap(won))

    def test_pctl_records_only_for_ranked_status(self) -> None:
        """per_tc_metric_percentiles has "{metric}:{tc}" exactly when the metric is
        'ranked'; every record is per TC and there is no page-level weighted record."""
        tc_stats = make_ranked_tc(
            "blitz",
            metrics={
                "score_gap": make_metric("score_gap", status="ranked", percentile=71.0),
                "achievable_score_gap": make_metric("achievable_score_gap", status="below_floor"),
                "score_gap_conv": make_metric("score_gap_conv", status="pending"),
                "score_gap_parity": make_metric("score_gap_parity", status="unranked"),
                "recovery_score_gap": make_metric(
                    "recovery_score_gap", status="ranked", percentile=33.0
                ),
                "clock_gap": make_metric("clock_gap", status="ranked", percentile=58.0),
                "net_flag_rate": make_metric("net_flag_rate", status="below_floor"),
                "time_pressure_score_gap": make_metric(
                    "time_pressure_score_gap", status="unranked"
                ),
                "conversion_rate": make_metric("conversion_rate", status="ranked", percentile=64.0),
                "parity_rate": make_metric("parity_rate", status="below_floor"),
                "recovery_rate": make_metric("recovery_rate", status="pending"),
            },
        )
        result = build_findings([tc_stats], [], as_of=_NOW)
        records = result.per_tc_metric_percentiles
        assert records is not None
        assert set(records) == {
            "score_gap:blitz",
            "score_gap_recov:blitz",  # recovery bridge: both names are written
            "recovery_score_gap:blitz",
            "clock_gap:blitz",
            "conversion_win_pct:blitz",
        }
        assert not any(":" not in key for key in records), "no page-level record"
        sg = records["score_gap:blitz"]
        assert sg.percentile == 71.0
        assert sg.tc == "blitz"
        assert sg.anchor == 1500
        assert sg.n_games == tc_stats.metrics["score_gap"].n
        assert sg.value == pytest.approx(0.05 * 100.0)  # DEFAULT_METRIC_VALUES["score_gap"] x100
        assert records["score_gap_recov:blitz"] is records["recovery_score_gap:blitz"]

    def test_pctl_records_are_not_built_from_the_last_3mo_window(self) -> None:
        """The windowed sample never carries persisted percentiles (D-04): only the
        all_time payload feeds per_tc_metric_percentiles."""
        ranked = make_ranked_tc("blitz")
        windowed = make_ranked_tc(
            "blitz", metrics={"score_gap": make_metric("score_gap", status="unranked")}
        )
        result = build_findings([ranked], [windowed], as_of=_NOW)
        assert result.per_tc_metric_percentiles is not None
        assert "score_gap:blitz" in result.per_tc_metric_percentiles

    def test_elo_and_score_timeline_from_ranked_series(self) -> None:
        """endgame_elo_timeline and score_timeline series come from each TC's own ranked
        elo_timeline / score_gap_timeline."""
        blitz_elo = make_elo_combo(13, time_control="blitz", endgame_elo=1500, actual_elo=1400)
        rapid_elo = make_elo_combo(
            12, platform="lichess", time_control="rapid", endgame_elo=1650, actual_elo=1700
        )
        blitz = make_ranked_tc(
            "blitz", elo_timeline=[blitz_elo], score_gap_timeline=make_score_timeline(13)
        )
        rapid = make_ranked_tc(
            "rapid", elo_timeline=[rapid_elo], score_gap_timeline=make_score_timeline(14)
        )
        result = build_findings([blitz, rapid], [], as_of=_NOW)

        elo = [f for f in result.findings if f.subsection_id == "endgame_elo_timeline"]
        assert [
            (f.dimension["platform"], f.dimension["time_control"]) for f in elo if f.dimension
        ] == [("chess.com", "blitz"), ("lichess", "rapid")]
        by_tc = {f.dimension["time_control"]: f for f in elo if f.dimension}
        assert by_tc["blitz"].value == pytest.approx(100.0)  # 1500 - 1400
        assert by_tc["rapid"].value == pytest.approx(-50.0)  # 1650 - 1700
        # all_time series are resampled monthly; the Actual ELO on the points identifies
        # which TC's ranked combo each series came from.
        blitz_series, rapid_series = by_tc["blitz"].series, by_tc["rapid"].series
        assert blitz_series is not None and {p.actual_elo for p in blitz_series} == {1400}
        assert rapid_series is not None and {p.actual_elo for p in rapid_series} == {1700}

        st = [
            f
            for f in result.findings
            if f.subsection_id == "score_timeline" and f.metric == "endgame_score_timeline"
        ]
        lengths = {f.dimension["time_control"]: len(f.series or []) for f in st if f.dimension}
        assert lengths == {"blitz": 13, "rapid": 14}

        # The player profile is built from the concatenation of every TC's combos.
        assert result.player_profile is not None
        assert {(e.platform, e.time_control) for e in result.player_profile} == {
            ("chess.com", "blitz"),
            ("lichess", "rapid"),
        }

    def test_type_categories_by_tc_filled_from_ranked_lists(self) -> None:
        cats = [make_category("rook", conv_games=20, conv_wins=16, recov_games=10, recov_wins=3)]
        result = build_findings(
            [make_ranked_tc("blitz", type_categories=cats), make_ranked_tc("rapid")], [], as_of=_NOW
        )
        assert result.type_categories_by_tc is not None
        assert set(result.type_categories_by_tc) == {"blitz"}
        assert result.type_categories_by_tc["blitz"] == cats

    def test_cohort_anchors_come_from_each_tc_anchor(self) -> None:
        result = build_findings(
            [make_ranked_tc("blitz"), make_ranked_tc("rapid", anchor=None)], [], as_of=_NOW
        )
        assert result.cohort_anchors is not None
        assert set(result.cohort_anchors) == {"blitz"}
        assert result.cohort_anchors["blitz"].anchor_rating == 1500


# ---------------------------------------------------------------------------
# TestFindingsEndgameMetrics — 260422-tnb A1: bucket-matched metric emission.
# Each bucket maps to exactly ONE rate finding whose metric matches the bucket
# (conversion -> conversion_win_pct, parity -> parity_score_pct, recovery ->
# recovery_save_pct). Phase 87.4 (D-05): the aggregate ``endgame_skill`` finding
# was removed end-to-end. Total emitted per TC = 3 rate + 3 score_gap_* findings.
# ---------------------------------------------------------------------------


class TestFindingsEndgameMetrics:
    """Unit tests for _findings_endgame_metrics (one ranked TC at a time).

    Phase 102 UAT (2026-06-02): one ``endgame_metrics_<tc>`` subsection per time
    control. Phase 238: sourced from ``RankedTcStats.metrics`` (value and n). Each TC
    emits 6 findings — 3 rate (conversion/parity/recovery) + 3 ΔES gap
    (score_gap_conv/parity/recov) — all carrying ``dimension={"time_control": tc}``.
    """

    def test_tc_emits_six_findings_three_rate_three_gap(self) -> None:
        """One fully-populated TC -> 3 rate findings + 3 ΔES-gap findings = 6,
        all under endgame_metrics_<tc> with dimension time_control=<tc>."""
        from app.services.insights_service import _findings_endgame_metrics

        findings = _findings_endgame_metrics(make_ranked_tc("blitz"), window="all_time")

        assert len(findings) == 6
        assert all(f.subsection_id == "endgame_metrics_blitz" for f in findings)
        assert all(f.dimension == {"time_control": "blitz"} for f in findings)
        # Phase 87.4 (D-05): no aggregate endgame_skill finding any more.
        assert not any(f.metric == "endgame_skill" for f in findings)

        rate_metrics = {
            f.metric
            for f in findings
            if f.metric in {"conversion_win_pct", "parity_score_pct", "recovery_save_pct"}
        }
        assert rate_metrics == {"conversion_win_pct", "parity_score_pct", "recovery_save_pct"}

        gap_metrics = sorted(f.metric for f in findings if f.metric.startswith("score_gap_"))
        assert gap_metrics == ["score_gap_conv", "score_gap_parity", "score_gap_recov"]

    def test_one_subsection_per_time_control(self) -> None:
        """Two TCs -> one endgame_metrics_<tc> subsection each, 6 findings per TC."""
        findings = build_findings(
            [make_ranked_tc("bullet"), make_ranked_tc("rapid")], [], as_of=_NOW
        ).findings
        metrics = [f for f in findings if f.subsection_id.startswith("endgame_metrics_")]

        assert len(metrics) == 12
        assert {f.subsection_id for f in metrics} == {
            "endgame_metrics_bullet",
            "endgame_metrics_rapid",
        }
        bullet = [f for f in metrics if f.subsection_id == "endgame_metrics_bullet"]
        rapid = [f for f in metrics if f.subsection_id == "endgame_metrics_rapid"]
        assert len(bullet) == 6
        assert len(rapid) == 6
        assert all(f.dimension == {"time_control": "bullet"} for f in bullet)
        assert all(f.dimension == {"time_control": "rapid"} for f in rapid)

    def test_tc_below_game_gate_emits_no_findings(self) -> None:
        """A TC under MIN_GAMES_PER_TC_CARD ranked endgame games shows no Metrics card."""
        from app.services.endgame_zones import MIN_GAMES_PER_TC_CARD
        from app.services.insights_service import _findings_endgame_metrics

        assert 8 < MIN_GAMES_PER_TC_CARD
        tc_stats = make_ranked_tc("blitz", endgame=(5, 1, 2))
        assert _findings_endgame_metrics(tc_stats, window="all_time") == []

    def test_empty_bucket_emits_empty_rate_and_nan_gap(self) -> None:
        """A bucket with n=0 / value=None emits an empty rate finding (NaN, n=0,
        not headline-eligible); its ΔES gap finding (n=0, value=None) is NaN too."""
        from app.services.insights_service import _findings_endgame_metrics

        tc_stats = make_ranked_tc(
            "blitz",
            metrics={
                "conversion_rate": make_metric("conversion_rate", n=0),
                "score_gap_conv": make_metric("score_gap_conv", n=0),
                "recovery_rate": make_metric("recovery_rate", n=0),
                "recovery_score_gap": make_metric("recovery_score_gap", n=0),
            },
        )
        # make_metric substitutes the default value for None, so null the values explicitly.
        for key in ("conversion_rate", "score_gap_conv", "recovery_rate", "recovery_score_gap"):
            tc_stats.metrics[key] = tc_stats.metrics[key].model_copy(update={"value": None})
        findings = _findings_endgame_metrics(tc_stats, window="all_time")

        assert len(findings) == 6

        conv_rate = next(f for f in findings if f.metric == "conversion_win_pct")
        assert math.isnan(conv_rate.value)
        assert conv_rate.sample_size == 0
        assert conv_rate.is_headline_eligible is False

        conv_gap = next(f for f in findings if f.metric == "score_gap_conv")
        assert math.isnan(conv_gap.value)
        assert conv_gap.sample_size == 0
        assert conv_gap.is_headline_eligible is False

        # The populated parity bucket still emits a real rate finding.
        parity_rate = next(f for f in findings if f.metric == "parity_score_pct")
        assert parity_rate.value == pytest.approx(0.50)

    def test_rate_value_is_metric_value(self) -> None:
        """Each rate finding's value is the ranked metric's value."""
        from app.services.insights_service import _findings_endgame_metrics

        findings = _findings_endgame_metrics(make_ranked_tc("blitz"), window="all_time")

        conv = next(f for f in findings if f.metric == "conversion_win_pct")
        parity = next(f for f in findings if f.metric == "parity_score_pct")
        recov = next(f for f in findings if f.metric == "recovery_save_pct")
        assert conv.value == pytest.approx(0.68)
        assert parity.value == pytest.approx(0.50)
        assert recov.value == pytest.approx(0.35)
        assert (conv.sample_size, parity.sample_size, recov.sample_size) == (100, 80, 60)

    def test_gap_value_is_metric_value_with_recovery_bridge(self) -> None:
        """Each ΔES-gap finding's value is the ranked gap metric; the finding id
        score_gap_recov maps to the ranked recovery_score_gap metric."""
        from app.services.insights_service import _findings_endgame_metrics

        findings = _findings_endgame_metrics(make_ranked_tc("blitz"), window="all_time")

        conv = next(f for f in findings if f.metric == "score_gap_conv")
        parity = next(f for f in findings if f.metric == "score_gap_parity")
        recov = next(f for f in findings if f.metric == "score_gap_recov")
        assert conv.value == pytest.approx(-0.08)
        assert parity.value == pytest.approx(-0.02)
        assert recov.value == pytest.approx(0.04)


def _by_metric(findings: list[SubsectionFinding]) -> dict[str, SubsectionFinding]:
    return {f.metric: f for f in findings}


class TestFindingsEndgameStartVsEnd:
    """Unit tests for _findings_endgame_start_vs_end (Phase 82 D-16/D-17/D-18/D-19/D-20).

    Phase 102 UAT: emitter returns FOUR findings in UI-card order —
    endgame_score, non_endgame_score, entry_eval_pawns, entry_expected_score.
    Phase 238 (D-04, D-00h): one ranked TC at a time, each finding carries
    ``dimension={"time_control": tc}``. Assertions are keyed by metric (via
    `_by_metric`) so they survive future reordering. Covers independent per-tile gates,
    zone boundary dispatch via assign_zone, and is_headline_eligible =
    (sample_quality != "thin").
    """

    @staticmethod
    def _make_tc(
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
    ) -> RankedTcStats:
        return make_ranked_tc(
            "blitz",
            endgame=(wins, draws, losses),
            non_endgame=(non_wins, non_draws, non_losses),
            entry_eval_mean_pawns=entry_eval_mean_pawns,
            entry_eval_n=entry_eval_n,
            expected_score=entry_expected_score,
            flow_n=entry_expected_score_n,
        )

    def test_returns_four_findings_in_canonical_ui_order(self) -> None:
        """Phase 102 UAT: all gates pass -> FOUR findings, score cards leading."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        findings = _findings_endgame_start_vs_end(
            self._make_tc(entry_eval_mean_pawns=0.62), "all_time"
        )

        assert [f.metric for f in findings] == [
            "endgame_score",
            "non_endgame_score",
            "entry_eval_pawns",
            "entry_expected_score",
        ]

    def test_empty_entry_eval_when_n_eval_lt_10(self) -> None:
        """entry_eval_n < 10 -> entry_eval_pawns empty; endgame_score still populated."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(entry_eval_n=5), "all_time")
        )

        assert tiles["entry_eval_pawns"].sample_quality == "thin"
        assert tiles["entry_eval_pawns"].is_headline_eligible is False
        assert tiles["endgame_score"].sample_quality != "thin"

    def test_empty_endgame_score_when_total_lt_10(self) -> None:
        """endgame_wdl.total < 10 -> endgame_score empty; entry_eval_pawns populated."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_eval_n=50, wins=3, draws=1, losses=1), "all_time"
            )
        )

        assert tiles["endgame_score"].sample_quality == "thin"
        assert tiles["endgame_score"].is_headline_eligible is False
        assert tiles["entry_eval_pawns"].sample_quality != "thin"

    def test_empty_both_score_and_eval_when_both_lt_10(self) -> None:
        """Both pre-existing gates fail -> endgame_score and entry_eval_pawns empty."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_eval_n=5, wins=2, draws=1, losses=2), "all_time"
            )
        )

        assert tiles["entry_eval_pawns"].sample_quality == "thin"
        assert tiles["endgame_score"].sample_quality == "thin"

    def test_entry_eval_at_n_10_is_populated_adequate(self) -> None:
        """Boundary: entry_eval_n == 10 (the strict-`<` floor) -> populated, adequate.

        Phase 82 D-17 gates on `n_eval < 10`. n=10 must NOT be empty. Pairs with
        SAMPLE_QUALITY_BANDS["endgame_start_vs_end"] = (10, 50) which classifies
        n=10 as `adequate` (`thin` is `< 10`).
        """
        from app.services.insights_service import _findings_endgame_start_vs_end

        eval_tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_eval_mean_pawns=0.30, entry_eval_n=10), "all_time"
            )
        )["entry_eval_pawns"]

        assert eval_tile.sample_size == 10
        assert eval_tile.sample_quality == "adequate"
        assert eval_tile.is_headline_eligible is True

    def test_endgame_score_at_total_10_is_populated_adequate(self) -> None:
        """Boundary: endgame_wdl.total == 10 -> endgame_score populated, adequate."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        score_tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_eval_n=50, wins=5, draws=2, losses=3), "all_time"
            )
        )["endgame_score"]

        assert score_tile.sample_size == 10
        assert score_tile.sample_quality == "adequate"
        assert score_tile.is_headline_eligible is True

    def test_entry_eval_at_n_9_is_thin(self) -> None:
        """Boundary: entry_eval_n == 9 (just below the floor) -> empty/thin."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        eval_tile = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(entry_eval_n=9), "all_time")
        )["entry_eval_pawns"]

        assert eval_tile.sample_quality == "thin"
        assert eval_tile.is_headline_eligible is False

    def test_entry_eval_none_is_empty_even_with_sample(self) -> None:
        """A ranked TC with no mean entry eval (pending evals) emits the empty tile."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tc_stats = make_ranked_tc("blitz", entry_eval_mean_pawns=None, entry_eval_n=50)
        eval_tile = _by_metric(_findings_endgame_start_vs_end(tc_stats, "all_time"))[
            "entry_eval_pawns"
        ]
        assert math.isnan(eval_tile.value)
        assert eval_tile.sample_quality == "thin"

    def test_zone_strong_for_entry_eval_above_band(self) -> None:
        """entry_eval_mean_pawns = 1.00 -> zone = 'strong' (above typical_upper=0.75)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(entry_eval_mean_pawns=1.00), "all_time")
        )

        assert tiles["entry_eval_pawns"].zone == "strong"

    def test_zone_weak_for_entry_eval_below_band(self) -> None:
        """entry_eval_mean_pawns = -1.00 -> zone = 'weak' (below typical_lower=-0.75)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(entry_eval_mean_pawns=-1.00), "all_time")
        )

        assert tiles["entry_eval_pawns"].zone == "weak"

    def test_zone_typical_for_entry_eval_inside_band(self) -> None:
        """entry_eval_mean_pawns = 0.30 -> zone = 'typical' (inside [-0.75, 0.75])."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(entry_eval_mean_pawns=0.30), "all_time")
        )

        assert tiles["entry_eval_pawns"].zone == "typical"

    def test_zone_strong_for_endgame_score_above_band(self) -> None:
        """wins=12, draws=4, losses=4 -> score=14/20=0.70 -> zone='strong'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(wins=12, draws=4, losses=4), "all_time")
        )

        assert tiles["endgame_score"].zone == "strong"

    def test_zone_weak_for_endgame_score_below_band(self) -> None:
        """wins=4, draws=4, losses=12 -> score=6/20=0.30 -> zone='weak'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(wins=4, draws=4, losses=12), "all_time")
        )

        assert tiles["endgame_score"].zone == "weak"

    # ------------------------------------------------------------------
    # Phase 102 UAT: non_endgame_score tile.
    # ------------------------------------------------------------------

    def test_non_endgame_score_value_and_band(self) -> None:
        """non_endgame_score = (w + 0.5d)/total over non_endgame_wdl, same band as endgame_score."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        # non: wins=12, draws=4, losses=4 -> score=14/20=0.70 -> strong (band [0.45, 0.55]).
        non_tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(non_wins=12, non_draws=4, non_losses=4), "all_time"
            )
        )["non_endgame_score"]

        assert non_tile.value == pytest.approx(0.70)
        assert non_tile.zone == "strong"
        assert non_tile.sample_size == 20
        assert non_tile.dimension == {"time_control": "blitz"}
        assert non_tile.series is None

    def test_non_endgame_score_zone_weak_below_band(self) -> None:
        """non score = 6/20 = 0.30 -> zone='weak'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        non_tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(non_wins=4, non_draws=4, non_losses=12), "all_time"
            )
        )["non_endgame_score"]

        assert non_tile.zone == "weak"

    def test_non_endgame_score_empty_when_total_lt_10(self) -> None:
        """non_endgame_wdl.total < 10 -> non_endgame_score empty (thin, not headline)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        non_tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(non_wins=2, non_draws=1, non_losses=2), "all_time"
            )
        )["non_endgame_score"]

        assert math.isnan(non_tile.value)
        assert non_tile.sample_quality == "thin"
        assert non_tile.is_headline_eligible is False
        assert non_tile.sample_size == 0

    def test_dimension_is_time_control_and_series_none(self) -> None:
        """All findings carry the TC dimension (D-00h) and no series (D-19/D-20)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        findings = _findings_endgame_start_vs_end(self._make_tc(), "all_time")

        for f in findings:
            assert f.dimension == {"time_control": "blitz"}
            assert f.series is None

    def test_subsection_and_window_propagate(self) -> None:
        """All findings carry correct subsection_id and window."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        findings = _findings_endgame_start_vs_end(self._make_tc(), "last_3mo")

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

        tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_expected_score=0.58, entry_expected_score_n=50), "all_time"
            )
        )["entry_expected_score"]

        assert tile.value == pytest.approx(0.58)
        assert tile.zone in {"weak", "typical", "strong"}
        assert tile.dimension == {"time_control": "blitz"}
        assert tile.trend == "n_a"
        assert tile.sample_size == 50
        assert tile.weekly_points_in_window == 0
        assert tile.parent_subsection_id is None
        assert tile.subsection_id == "endgame_start_vs_end"
        assert tile.is_headline_eligible is True

    def test_entry_expected_score_empty_when_n_below_10(self) -> None:
        """entry_expected_score_n < 10 -> tile empty (thin, NaN value, not headline)."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_expected_score=0.62, entry_expected_score_n=9), "all_time"
            )
        )["entry_expected_score"]

        assert math.isnan(tile.value)
        assert tile.zone == "typical"
        assert tile.sample_quality == "thin"
        assert tile.is_headline_eligible is False
        assert tile.sample_size == 0

    def test_entry_expected_score_zone_strong_above_band(self) -> None:
        """entry_expected_score=0.60 (above typical_upper=0.55) -> zone='strong'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_expected_score=0.60, entry_expected_score_n=50), "all_time"
            )
        )

        assert tiles["entry_expected_score"].zone == "strong"

    def test_entry_expected_score_zone_weak_below_band(self) -> None:
        """entry_expected_score=0.40 (below typical_lower=0.45) -> zone='weak'."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_expected_score=0.40, entry_expected_score_n=50), "all_time"
            )
        )

        assert tiles["entry_expected_score"].zone == "weak"

    def test_no_verdict_field(self) -> None:
        """Phase 82 D-06 / Phase 83 D-19: SubsectionFinding has NO `verdict` field.

        Guards against a future regression that re-adds a sig-test signal —
        per memory `feedback_llm_significance_signal.md`, the LLM narrates
        strictly by zone, never by p-value or sig-test outcome.
        """
        from app.services.insights_service import _findings_endgame_start_vs_end

        tile = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(entry_expected_score=0.58, entry_expected_score_n=50), "all_time"
            )
        )["entry_expected_score"]

        assert not hasattr(tile, "verdict")
        assert "verdict" not in tile.model_dump()

    def test_entry_expected_score_independent_gate_from_other_tiles(self) -> None:
        """Phase 83 D-19: entry_expected_score gate is independent of the other tiles.

        The score / eval tiles may be populated while entry_expected_score is
        empty when only the expected-score backfill has not yet completed.
        """
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(
                self._make_tc(
                    entry_eval_mean_pawns=0.30,
                    entry_eval_n=50,
                    entry_expected_score=0.58,
                    entry_expected_score_n=5,  # thin
                ),
                "all_time",
            )
        )

        assert tiles["entry_eval_pawns"].sample_quality != "thin"
        assert tiles["endgame_score"].sample_quality != "thin"
        assert tiles["entry_expected_score"].sample_quality == "thin"

    def test_existing_tiles_unchanged_by_new_findings(self) -> None:
        """Adding non_endgame_score must not regress entry_eval/endgame_score shape."""
        from app.services.insights_service import _findings_endgame_start_vs_end

        tiles = _by_metric(
            _findings_endgame_start_vs_end(self._make_tc(entry_eval_mean_pawns=0.30), "all_time")
        )

        assert tiles["entry_eval_pawns"].value == pytest.approx(0.30)
        assert tiles["entry_eval_pawns"].sample_size == 50
        # score = (25 + 0.5*10) / 50 = 0.60
        assert tiles["endgame_score"].value == pytest.approx(0.60)
        assert tiles["endgame_score"].sample_size == 50


class TestFindingsScoreGap:
    """Unit tests for _findings_score_gap (Phase 102 UAT; ranked per-TC since Phase 238).

    The dedicated `score_gap` subsection mirrors the UI "Endgame Score
    Differences" card: achievable_score_gap ("Eval Score Gap") first, then
    score_gap ("Endgame Score Gap"), each per time control.
    """

    @staticmethod
    def _make_tc(
        *,
        score_difference: float = -0.08,
        achievable_score_gap: float = -0.03,
        entry_expected_score_n: int = 60,
        endgame_total: int = 240,
        non_endgame_total: int = 700,
    ) -> RankedTcStats:
        return make_ranked_tc(
            "blitz",
            endgame=(endgame_total, 0, 0),
            non_endgame=(non_endgame_total, 0, 0),
            metrics={
                "score_gap": make_metric("score_gap", value=score_difference),
                "achievable_score_gap": make_metric(
                    "achievable_score_gap", value=achievable_score_gap, n=entry_expected_score_n
                ),
            },
        )

    def test_emits_two_findings_in_card_order(self) -> None:
        from app.services.insights_service import _findings_score_gap

        findings = _findings_score_gap(self._make_tc(), "all_time")

        assert [f.metric for f in findings] == ["achievable_score_gap", "score_gap"]
        for f in findings:
            assert f.subsection_id == "score_gap"
            assert f.dimension == {"time_control": "blitz"}
            assert f.series is None
            assert f.parent_subsection_id is None

    def test_score_gap_value_and_zone(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tiles = _by_metric(_findings_score_gap(self._make_tc(score_difference=-0.15), "all_time"))
        sg = tiles["score_gap"]
        assert sg.value == pytest.approx(-0.15)
        assert sg.zone == "weak"  # below score_gap band lower bound (-0.10)
        assert sg.sample_size == 940  # 240 + 700

    def test_achievable_score_gap_value_and_gate(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tiles = _by_metric(
            _findings_score_gap(
                self._make_tc(achievable_score_gap=0.04, entry_expected_score_n=80), "all_time"
            )
        )
        asg = tiles["achievable_score_gap"]
        assert asg.value == pytest.approx(0.04)
        assert asg.sample_size == 80
        assert asg.zone in {"weak", "typical", "strong"}

    def test_achievable_score_gap_empty_when_n_below_10(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tiles = _by_metric(_findings_score_gap(self._make_tc(entry_expected_score_n=5), "all_time"))
        asg = tiles["achievable_score_gap"]
        assert math.isnan(asg.value)
        assert asg.sample_quality == "thin"
        assert asg.is_headline_eligible is False

    def test_score_gap_empty_when_no_games(self) -> None:
        from app.services.insights_service import _findings_score_gap

        tc_stats = make_ranked_tc(
            "blitz",
            endgame=(0, 0, 0),
            non_endgame=(0, 0, 0),
            metrics={"score_gap": make_metric("score_gap", n=0)},
        )
        tc_stats.metrics["score_gap"] = tc_stats.metrics["score_gap"].model_copy(
            update={"value": None}
        )
        tiles = _by_metric(_findings_score_gap(tc_stats, "all_time"))
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
    """Phase 102 UAT (2026-06-02): D-15 is REVERSED. The LLM type_breakdown path
    reads the per-(class × TC) type rows and emits one `endgame_type_<tc>`
    subsection per eligible time control, mirroring the UI's per-TC collapsible
    cards. Phase 238: the rows come from each ranked TC's ``type_categories``.
    """

    def test_per_tc_producer_emits_endgame_type_subsections(self) -> None:
        """The per-TC producer reads type_categories and emits endgame_type_<tc>
        findings (Conv/Recov per class) carrying a {endgame_class, time_control} dim."""
        from app.services.insights_service import _findings_endgame_type_by_tc

        # blitz clears the per-TC games gate (totals 30 + 23 = 53 >= 20).
        blitz = make_ranked_tc(
            "blitz",
            type_categories=[
                make_category("rook", conv_games=20, conv_wins=16, recov_games=10, recov_wins=3),
                make_category("pawn", conv_games=15, conv_wins=12, recov_games=8, recov_wins=2),
            ],
        )

        findings = _findings_endgame_type_by_tc([blitz], "all_time")

        assert findings, "expected per-TC Endgame Type findings"
        assert all(f.subsection_id == "endgame_type_blitz" for f in findings)
        assert all(f.dimension and f.dimension.get("time_control") == "blitz" for f in findings)
        assert all(
            f.dimension and f.dimension.get("endgame_class") in {"rook", "pawn"} for f in findings
        )
        metrics = {f.metric for f in findings}
        assert "conversion_win_pct" in metrics
        assert "recovery_save_pct" in metrics
        # win_rate is NOT emitted — the renderer's per-TC WDL table carries that framing.
        assert "win_rate" not in metrics

    def test_one_subsection_per_ranked_tc(self) -> None:
        from app.services.insights_service import _findings_endgame_type_by_tc

        cats = [make_category("rook", conv_games=20, conv_wins=16, recov_games=10, recov_wins=3)]
        findings = _findings_endgame_type_by_tc(
            [
                make_ranked_tc("bullet", type_categories=cats),
                make_ranked_tc("rapid", type_categories=cats),
            ],
            "all_time",
        )
        assert {f.subsection_id for f in findings} == {
            "endgame_type_bullet",
            "endgame_type_rapid",
        }

    def test_no_findings_when_type_categories_absent(self) -> None:
        """A ranked TC without type rows (no endgames) emits nothing (section omitted)."""
        from app.services.insights_service import _findings_endgame_type_by_tc

        assert _findings_endgame_type_by_tc([make_ranked_tc("blitz")], "all_time") == []
        assert _findings_endgame_type_by_tc([], "all_time") == []

    def test_tc_below_game_gate_is_omitted(self) -> None:
        """A TC whose summed endgame games fall below MIN_GAMES_PER_TC_CARD emits no findings."""
        from app.services.endgame_zones import MIN_GAMES_PER_TC_CARD
        from app.services.insights_service import _findings_endgame_type_by_tc

        # rapid total = 5 + 3 = 8, below the gate.
        assert 8 < MIN_GAMES_PER_TC_CARD
        rapid = make_ranked_tc(
            "rapid",
            type_categories=[
                make_category("rook", conv_games=5, conv_wins=2, recov_games=3, recov_wins=1)
            ],
        )

        assert _findings_endgame_type_by_tc([rapid], "all_time") == []
