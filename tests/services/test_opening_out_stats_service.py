"""Pure-builder tests for the "out of the opening" stats (Phase 243, no DB).

Pin D-06 (per-TC status), D-07 (game-weighted headline), D-08 (95% gate against the
game-weighted peer median, direction guard), the favourable orientation and the card
states when no TC contributes. Inputs are constructed ``OpeningOutInputs``; every count,
percentile and band is a named constant.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import pytest

from app.repositories.opening_out_repository import OpeningOutCounts
from app.repositories.user_benchmark_percentiles_repository import PercentileRow
from app.repositories.user_rating_anchors_repository import RatingAnchorRow
from app.schemas.normalization import Color
from app.schemas.opening_out import OpeningOutRateOut, OpeningOutTcOut
from app.services.canonical_slice_sql import (
    MEDIAN_ANCHOR_MIN_GAMES,
    OPENING_OUT_MIN_GAMES_PER_COLOR,
    TimeControlBucket,
)
from app.services.opening_insights_constants import OPENING_INSIGHTS_CI_Z_95
from app.services.opening_out_stats_service import (
    OpeningOutInputs,
    PeerBand,
    build_out_of_opening_stats,
)
import math

from app.services.score_confidence import (
    VERDICT_CI_Z_99,
    ci_excludes,
    wilson_bounds,
    wilson_score_test_p_value,
)

_SNAPSHOT = datetime.date(2026, 10, 31)
_ANCHOR_RATING = 1500
_PLENTY_OF_GAMES = 500

# D-07 weights case: 300 blitz and 100 rapid qualifying games -> weights 0.75 / 0.25.
_BLITZ_N = 300
_RAPID_N = 100
_BLITZ_RAW_PCT = 40.0
_RAPID_RAW_PCT = 80.0
_WEIGHTED_RAW_PCT = 0.75 * _BLITZ_RAW_PCT + 0.25 * _RAPID_RAW_PCT  # 50.0
_BELOW_FLOOR_N = 20
_ANCHOR_SHORT_GAMES = 18

# Default peer band (fractions) and a second one for the footer test.
_BAND = PeerBand(p25=0.20, p50=0.30, p75=0.40)
_BAND_RAPID = PeerBand(p25=0.10, p50=0.20, p75=0.60)

# 95-vs-99 case: 108 of 300 worse (rate 0.36) against a peer median of 0.30.
_GATE_N = 300
_GATE_K = 108
_GATE_BAND = PeerBand(p25=0.25, p50=0.30, p75=0.35)
_RAW_ABOVE_MEDIAN = 60.0
_RAW_BELOW_MEDIAN = 40.0
_RAW_HIGH_WORSE = 80.0
_RAW_LOW = 20.0

_ABS_TOL = 1e-9


@dataclass(frozen=True)
class _Tc:
    """One (colour, TC) fixture; ``None`` percentile / band = no row / no CDF cell."""

    n: int
    worse: int = 0
    better: int = 0
    worse_pct: float | None = None
    better_pct: float | None = None
    worse_band: PeerBand | None = _BAND
    better_band: PeerBand | None = _BAND
    anchored: bool = True
    anchor_games: int = _PLENTY_OF_GAMES
    eval_pending: int = 0


def _row(percentile: float, n: int) -> PercentileRow:
    return PercentileRow(value=0.0, percentile=percentile, cdf_snapshot=_SNAPSHOT, n_games=n)


def _inputs(by_color: dict[Color, dict[TimeControlBucket, _Tc]]) -> OpeningOutInputs:
    counts: dict[TimeControlBucket, dict[Color, OpeningOutCounts]] = {}
    anchors: dict[TimeControlBucket, RatingAnchorRow] = {}
    anchor_games: dict[TimeControlBucket, int] = {}
    eval_pending: dict[TimeControlBucket, int] = {}
    rows: dict = {}
    bands: dict = {}
    for color, tcs in by_color.items():
        for tc, spec in tcs.items():
            counts.setdefault(tc, {})[color] = OpeningOutCounts(
                n_games=spec.n, worse_n=spec.worse, better_n=spec.better
            )
            anchor_games[tc] = spec.anchor_games
            eval_pending[tc] = spec.eval_pending
            if spec.anchored:
                anchors[tc] = RatingAnchorRow(_ANCHOR_RATING, 0, spec.n, None, _ANCHOR_RATING)
            if spec.worse_pct is not None:
                rows[("opening_worse_rate", tc, color)] = _row(spec.worse_pct, spec.n)
            if spec.better_pct is not None:
                rows[("opening_better_rate", tc, color)] = _row(spec.better_pct, spec.n)
            if spec.worse_band is not None:
                bands[("opening_worse_rate", tc)] = spec.worse_band
            if spec.better_band is not None:
                bands[("opening_better_rate", tc)] = spec.better_band
    return OpeningOutInputs(
        counts=counts,
        anchor_games=anchor_games,
        eval_pending=eval_pending,
        anchors=anchors,
        percentile_rows=rows,
        peer_bands=bands,
    )


def _worse(tcs: dict[TimeControlBucket, _Tc], color: Color = "white") -> OpeningOutRateOut:
    result = build_out_of_opening_stats(_inputs({color: tcs}))
    return result.white.worse if color == "white" else result.black.worse


def _tc_by_name(card: OpeningOutRateOut, tc: TimeControlBucket) -> OpeningOutTcOut:
    return next(entry for entry in card.tcs if entry.tc == tc)


# --- D-07 weights and exclusions --------------------------------------------


def test_headline_is_game_weighted_over_contributing_tcs() -> None:
    card = _worse(
        {
            "blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_BLITZ_RAW_PCT),
            "rapid": _Tc(n=_RAPID_N, worse=30, worse_pct=_RAPID_RAW_PCT),
        }
    )
    assert card.status == "ranked"
    assert _WEIGHTED_RAW_PCT == pytest.approx(50.0)
    assert card.percentile_favorable == pytest.approx(100.0 - _WEIGHTED_RAW_PCT, abs=_ABS_TOL)
    assert (card.k, card.n) == (120, _BLITZ_N + _RAPID_N)


def test_below_floor_tc_is_excluded_but_listed() -> None:
    base: dict[TimeControlBucket, _Tc] = {
        "blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_BLITZ_RAW_PCT),
        "rapid": _Tc(n=_RAPID_N, worse=30, worse_pct=_RAPID_RAW_PCT),
    }
    without = _worse(base)
    with_bullet = _worse({**base, "bullet": _Tc(n=_BELOW_FLOOR_N, worse=10)})
    assert with_bullet.percentile_favorable == pytest.approx(without.percentile_favorable or 0.0)
    assert (with_bullet.k, with_bullet.n) == (without.k, without.n)
    bullet = _tc_by_name(with_bullet, "bullet")
    assert bullet.status == "below_floor"
    assert (bullet.floor_n, bullet.floor_required) == (
        _BELOW_FLOOR_N,
        OPENING_OUT_MIN_GAMES_PER_COLOR,
    )
    assert [e.tc for e in with_bullet.tcs] == ["bullet", "blitz", "rapid"]


def test_ranked_tc_without_cdf_cell_is_excluded_from_headline_and_gate() -> None:
    """A3: a TC that passes the floor but has no CDF cell is listed, not pooled."""
    card = _worse(
        {
            "blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_BLITZ_RAW_PCT),
            "rapid": _Tc(n=_RAPID_N, worse=30, worse_pct=_RAPID_RAW_PCT, worse_band=None),
        }
    )
    assert card.percentile_favorable == pytest.approx(100.0 - _BLITZ_RAW_PCT)
    assert (card.k, card.n) == (90, _BLITZ_N)
    assert _tc_by_name(card, "rapid").status == "ranked"


def test_anchor_floor_applies_before_the_games_floor() -> None:
    card = _worse(
        {"blitz": _Tc(n=_PLENTY_OF_GAMES, anchored=False, anchor_games=_ANCHOR_SHORT_GAMES)}
    )
    blitz = _tc_by_name(card, "blitz")
    assert blitz.status == "below_floor"
    assert (blitz.floor_n, blitz.floor_required) == (_ANCHOR_SHORT_GAMES, MEDIAN_ANCHOR_MIN_GAMES)


def test_tc_without_qualifying_games_but_pending_evals_is_pending() -> None:
    card = _worse({"blitz": _Tc(n=0, eval_pending=5)})
    assert _tc_by_name(card, "blitz").status == "pending"
    assert card.status == "pending"


# --- card states when nothing contributes -----------------------------------


def test_card_is_pending_when_any_tc_is_pending() -> None:
    card = _worse(
        {
            "bullet": _Tc(n=0, eval_pending=3),
            "blitz": _Tc(n=_BLITZ_N, worse=90),  # enough games, no Stage B row -> unranked
            "rapid": _Tc(n=_BELOW_FLOOR_N),
        }
    )
    assert card.status == "pending"
    assert card.percentile_favorable is None and card.ci_low is None and not card.significant


def test_card_is_unranked_when_a_tc_awaits_stage_b_and_none_is_pending() -> None:
    card = _worse(
        {
            "blitz": _Tc(n=_BLITZ_N, worse=90),
            "rapid": _Tc(n=_BELOW_FLOOR_N),
        }
    )
    assert card.status == "unranked"
    assert card.rate == pytest.approx(90 / (_BLITZ_N + _BELOW_FLOOR_N))


def test_card_is_unranked_not_below_floor_when_every_ranked_tc_lacks_a_peer_band() -> None:
    """Regression: ranked rows but no CDF cell at the current anchor must not read "0 of 30"."""
    card = _worse({"blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_BLITZ_RAW_PCT, worse_band=None)})
    assert _tc_by_name(card, "blitz").status == "ranked"
    assert card.status == "unranked"
    assert card.percentile_favorable is None and not card.significant
    assert (card.k, card.n) == (90, _BLITZ_N)


def test_card_is_below_floor_with_largest_floor_n() -> None:
    card = _worse({"bullet": _Tc(n=_BELOW_FLOOR_N, worse=4), "rapid": _Tc(n=_BELOW_FLOOR_N // 2)})
    assert card.status == "below_floor"
    assert (card.floor_n, card.floor_required) == (_BELOW_FLOOR_N, OPENING_OUT_MIN_GAMES_PER_COLOR)
    assert card.rate == pytest.approx(4 / (_BELOW_FLOOR_N + _BELOW_FLOOR_N // 2))
    assert card.peer_p50 is None


def test_card_with_no_listed_tc_is_below_floor_zero_of_thirty() -> None:
    card = _worse({})
    assert card.status == "below_floor"
    assert (card.floor_n, card.floor_required, card.rate, card.tcs) == (
        0,
        OPENING_OUT_MIN_GAMES_PER_COLOR,
        None,
        [],
    )


def test_colours_are_independent() -> None:
    result = build_out_of_opening_stats(
        _inputs(
            {
                "white": {"blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_BLITZ_RAW_PCT)},
                "black": {"blitz": _Tc(n=_BELOW_FLOOR_N, worse=5)},
            }
        )
    )
    assert result.white.worse.status == "ranked"
    assert result.black.worse.status == "below_floor"
    assert result.black.worse.floor_n == _BELOW_FLOOR_N
    assert result.white.better.status == "unranked"  # white has no better percentile row


# --- D-08: 95% gate and direction guard -------------------------------------


def _gate_card(raw_pct: float, k: int = _GATE_K) -> OpeningOutRateOut:
    return _worse({"blitz": _Tc(n=_GATE_N, worse=k, worse_pct=raw_pct, worse_band=_GATE_BAND)})


def test_gate_uses_95_percent_not_99() -> None:
    rate = _GATE_K / _GATE_N
    lo95, hi95 = wilson_bounds(rate, _GATE_N, z=OPENING_INSIGHTS_CI_Z_95)
    lo99, hi99 = wilson_bounds(rate, _GATE_N, z=VERDICT_CI_Z_99)
    # Premise first: significant at 95%, not at 99%.
    assert ci_excludes(_GATE_BAND.p50, lo95, hi95)
    assert not ci_excludes(_GATE_BAND.p50, lo99, hi99)
    card = _gate_card(_RAW_ABOVE_MEDIAN)
    assert card.significant is True
    assert (card.ci_low, card.ci_high) == pytest.approx((lo95, hi95))


def test_gate_direction_guard_blocks_ci_on_the_opposite_side_of_the_percentile() -> None:
    """The CI sits above the peer median but the raw headline is below 50: not significant."""
    card = _gate_card(_RAW_BELOW_MEDIAN)
    assert card.ci_low is not None and card.ci_low > _GATE_BAND.p50
    assert card.significant is False


def test_gate_is_false_when_the_ci_contains_the_peer_median() -> None:
    card = _gate_card(_RAW_ABOVE_MEDIAN, k=int(_GATE_BAND.p50 * _GATE_N))
    assert card.significant is False


def test_p_value_is_the_score_test_against_the_peer_median() -> None:
    """p is the two-sided score test of the pooled rate vs peer_p50, the inversion of the CI."""
    card = _gate_card(_RAW_ABOVE_MEDIAN)
    rate = _GATE_K / _GATE_N
    p0 = _GATE_BAND.p50
    z = (rate - p0) / math.sqrt(p0 * (1 - p0) / _GATE_N)
    assert card.p_value == pytest.approx(math.erfc(abs(z) / math.sqrt(2)))
    assert card.p_value is not None and card.p_value < 0.05  # agrees with the 95% CI gate
    contained = _gate_card(_RAW_ABOVE_MEDIAN, k=int(p0 * _GATE_N))
    assert contained.p_value is not None and contained.p_value >= 0.05


def test_p_value_is_none_unless_ranked() -> None:
    card = _worse({"blitz": _Tc(n=_GATE_N, worse=_GATE_K, worse_pct=None, worse_band=_GATE_BAND)})
    assert card.status != "ranked" and card.p_value is None


def test_score_test_p_value_is_none_for_a_degenerate_null() -> None:
    assert wilson_score_test_p_value(0.3, 100, 0.0) is None
    assert wilson_score_test_p_value(0.3, 100, 1.0) is None
    assert wilson_score_test_p_value(0.3, 0, 0.3) is None


def test_gate_null_is_the_game_weighted_peer_median() -> None:
    """Pooled over two TCs the null is sum(w * p50), not the first TC's median."""
    card = _worse(
        {
            "blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_RAW_ABOVE_MEDIAN, worse_band=_BAND),
            "rapid": _Tc(n=_RAPID_N, worse=30, worse_pct=_RAW_ABOVE_MEDIAN, worse_band=_BAND_RAPID),
        }
    )
    weighted_p50 = 0.75 * _BAND.p50 + 0.25 * _BAND_RAPID.p50
    assert card.peer_p50 == pytest.approx(weighted_p50)


# --- orientation ------------------------------------------------------------


def test_worse_is_inverted_and_better_is_not() -> None:
    result = build_out_of_opening_stats(
        _inputs(
            {
                "white": {
                    "blitz": _Tc(
                        n=_BLITZ_N,
                        worse=90,
                        better=60,
                        worse_pct=_RAW_HIGH_WORSE,
                        better_pct=_RAW_HIGH_WORSE,
                    )
                }
            }
        )
    )
    worse, better = result.white.worse, result.white.better
    # Many worse games (raw percentile high) never reads favourable.
    assert worse.percentile_favorable == pytest.approx(100.0 - _RAW_HIGH_WORSE)
    assert worse.percentile_favorable is not None and worse.percentile_favorable < 50.0
    assert worse.tcs[0].percentile_favorable == pytest.approx(100.0 - _RAW_HIGH_WORSE)
    assert better.percentile_favorable == pytest.approx(_RAW_HIGH_WORSE)
    assert better.tcs[0].percentile_favorable == pytest.approx(_RAW_HIGH_WORSE)


def test_orientation_applies_to_every_listed_tc() -> None:
    card = _worse(
        {
            "blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_RAW_LOW),
            "rapid": _Tc(n=_RAPID_N, worse=30, worse_pct=_RAW_HIGH_WORSE),
        }
    )
    assert _tc_by_name(card, "blitz").percentile_favorable == pytest.approx(100.0 - _RAW_LOW)
    assert _tc_by_name(card, "rapid").percentile_favorable == pytest.approx(100.0 - _RAW_HIGH_WORSE)


# --- footer data ------------------------------------------------------------


def test_footer_band_is_weighted_over_contributing_tcs_only() -> None:
    card = _worse(
        {
            "bullet": _Tc(n=_BELOW_FLOOR_N, worse=7, worse_band=PeerBand(0.9, 0.9, 0.9)),
            "blitz": _Tc(n=_BLITZ_N, worse=90, worse_pct=_BLITZ_RAW_PCT, worse_band=_BAND),
            "rapid": _Tc(n=_RAPID_N, worse=30, worse_pct=_RAPID_RAW_PCT, worse_band=_BAND_RAPID),
        }
    )
    w_blitz = _BLITZ_N / (_BLITZ_N + _RAPID_N)
    w_rapid = _RAPID_N / (_BLITZ_N + _RAPID_N)
    assert card.peer_p25 == pytest.approx(w_blitz * _BAND.p25 + w_rapid * _BAND_RAPID.p25)
    assert card.peer_p50 == pytest.approx(w_blitz * _BAND.p50 + w_rapid * _BAND_RAPID.p50)
    assert card.peer_p75 == pytest.approx(w_blitz * _BAND.p75 + w_rapid * _BAND_RAPID.p75)
    assert (card.k, card.n) == (120, _BLITZ_N + _RAPID_N)  # bullet's 7 of 20 excluded
    assert card.rate == pytest.approx(120 / (_BLITZ_N + _RAPID_N))
