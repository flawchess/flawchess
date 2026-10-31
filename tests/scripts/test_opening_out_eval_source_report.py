"""Pure-function tests for the report-only per-eval-source comparison (Phase 243)."""

from __future__ import annotations

import math

import pytest

from scripts.opening_out_eval_source_report import (
    MIN_GAMES_PER_SOURCE,
    EvalSource,
    PairedDelta,
    SourceRow,
    paired_source_deltas,
    render_markdown,
    source_shares,
)


def _row(
    user_id: int,
    source: EvalSource,
    n: int,
    worse_n: int,
    better_n: int,
    *,
    user_color: str = "white",
) -> SourceRow:
    return SourceRow("blitz", user_id, user_color, source, n, worse_n, better_n)


def _delta(deltas: list[PairedDelta], a: EvalSource, b: EvalSource) -> PairedDelta:
    return next(d for d in deltas if d.source_a == a and d.source_b == b)


def test_pairs_need_the_floor_on_both_sources() -> None:
    rows = [
        _row(1, "lichess", MIN_GAMES_PER_SOURCE, 10, 4),
        _row(1, "local_full", MIN_GAMES_PER_SOURCE, 8, 4),
        # user 2: one game short on local_full -> excluded from the pair.
        _row(2, "lichess", 50, 25, 10),
        _row(2, "local_full", MIN_GAMES_PER_SOURCE - 1, 5, 5),
    ]
    delta = _delta(paired_source_deltas(rows), "lichess", "local_full")
    assert delta.n_pairs == 1
    assert delta.worse_mean_pp == pytest.approx((10 / 20 - 8 / 20) * 100)
    assert delta.better_mean_pp == pytest.approx(0.0)


def test_mean_and_se_in_percentage_points() -> None:
    # Two pairs with worse-rate differences of +10 pp and +20 pp.
    rows = [
        _row(1, "lichess", 20, 10, 0),
        _row(1, "entry_lane", 20, 8, 0),
        _row(2, "lichess", 20, 12, 0),
        _row(2, "entry_lane", 20, 8, 0),
    ]
    delta = _delta(paired_source_deltas(rows), "lichess", "entry_lane")
    assert delta.n_pairs == 2
    assert delta.worse_mean_pp == pytest.approx(15.0)
    # sd of [10, 20] = sqrt(50); SE = sd / sqrt(2) = 5.
    assert delta.worse_se_pp == pytest.approx(5.0)


def test_colours_pair_separately_and_missing_pairs_report_zero() -> None:
    rows = [
        _row(1, "lichess", 30, 15, 0, user_color="white"),
        _row(1, "local_full", 30, 15, 0, user_color="black"),
    ]
    deltas = paired_source_deltas(rows)
    # Same user, but the two sources are on different colours -> no pair.
    pair = _delta(deltas, "lichess", "local_full")
    assert pair.n_pairs == 0
    assert pair.worse_mean_pp is None
    assert pair.worse_se_pp is None


def test_single_pair_has_mean_but_no_se() -> None:
    rows = [_row(1, "lichess", 20, 10, 0), _row(1, "local_full", 20, 6, 0)]
    delta = _delta(paired_source_deltas(rows), "lichess", "local_full")
    assert delta.n_pairs == 1
    assert delta.worse_mean_pp == pytest.approx(20.0)
    assert delta.worse_se_pp is None


def test_source_shares_sum_to_one_per_tc() -> None:
    rows = [_row(1, "lichess", 30, 0, 0), _row(1, "entry_lane", 10, 0, 0)]
    shares = source_shares(rows)["blitz"]
    assert shares["lichess"] == pytest.approx(0.75)
    assert shares["entry_lane"] == pytest.approx(0.25)
    assert math.isclose(sum(shares.values()), 1.0)


def test_render_markdown_has_both_tables() -> None:
    md = render_markdown([_row(1, "lichess", 20, 10, 5), _row(1, "local_full", 20, 8, 5)])
    assert "## Eval-source shares" in md
    assert "| blitz | lichess | local_full | 1 |" in md
