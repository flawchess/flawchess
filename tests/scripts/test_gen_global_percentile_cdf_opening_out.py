"""Opening-out additions to the CDF script (Phase 243): colour-pooled ranking, merge, CLI.

Pure unit tests on synthetic rows; no database.
"""

from __future__ import annotations

import random
import sys
from datetime import date

import pytest

from app.services.global_percentile_cdf import CdfTable
from scripts.gen_global_percentile_cdf import (
    COHORT_MAX_USERS_PER_ANCHOR,
    COHORT_MIN_USERS_PER_ANCHOR,
    IN_SCOPE_METRICS,
    _METRIC_DISPLAY,
    CdfCells,
    _build_color_pooled_cohort_cdf_for,
    _build_per_user_with_anchor_query,
    _parse_metrics,
    _PerUserColorRow,
    merge_cells,
    parse_args,
)

_ANCHOR = 1500
_ROWS_PER_COLOR_GAMES = 40


def _users(
    n_users: int, *, base_id: int = 1, rating: int = _ANCHOR, colors: int = 2
) -> list[_PerUserColorRow]:
    """``n_users`` users at one rating, each with ``colors`` colour rows."""
    rows: list[_PerUserColorRow] = []
    for i in range(n_users):
        for c, color in enumerate(("white", "black")[:colors]):
            rows.append(
                _PerUserColorRow(
                    user_id=base_id + i,
                    user_color=color,
                    metric_value=(i + 0.25 * c) / max(n_users, 1),
                    n_games=_ROWS_PER_COLOR_GAMES,
                    anchor_rating=rating,
                )
            )
    return rows


def test_99_distinct_users_suppressed_with_users_not_points_counted() -> None:
    rows = _users(COHORT_MIN_USERS_PER_ANCHOR - 1)  # 198 colour rows, 99 users
    cdf, log = _build_color_pooled_cohort_cdf_for(rows, "opening_worse_rate", "blitz")
    entry = next(e for e in log if e["anchor"] == _ANCHOR)
    assert _ANCHOR not in cdf
    assert entry["suppressed"] is True
    assert entry["n_in_window"] == COHORT_MIN_USERS_PER_ANCHOR - 1


def test_100_distinct_users_qualify_with_n_users_100() -> None:
    cdf, log = _build_color_pooled_cohort_cdf_for(
        _users(COHORT_MIN_USERS_PER_ANCHOR), "opening_worse_rate", "blitz"
    )
    entry = next(e for e in log if e["anchor"] == _ANCHOR)
    assert entry["suppressed"] is False
    assert cdf[_ANCHOR].n_users == COHORT_MIN_USERS_PER_ANCHOR
    assert len(cdf[_ANCHOR].breakpoints) == 99


def test_cap_keeps_nearest_500_users_with_both_colour_rows() -> None:
    near = _users(COHORT_MAX_USERS_PER_ANCHOR, base_id=1, rating=_ANCHOR)
    # 100 farther users with a wildly different rate; they must not enter the cohort.
    far = [r._replace(metric_value=99.0) for r in _users(100, base_id=10_000, rating=_ANCHOR + 100)]
    cdf, log = _build_color_pooled_cohort_cdf_for(near + far, "opening_worse_rate", "blitz")
    entry = next(e for e in log if e["anchor"] == _ANCHOR)
    assert entry["n_in_window"] == COHORT_MAX_USERS_PER_ANCHOR + 100
    assert cdf[_ANCHOR].n_users == COHORT_MAX_USERS_PER_ANCHOR
    assert max(cdf[_ANCHOR].breakpoints) < 99.0
    # Breakpoints equal those of the near users alone (both colour rows each).
    only_near, _ = _build_color_pooled_cohort_cdf_for(near, "opening_worse_rate", "blitz")
    assert cdf[_ANCHOR].breakpoints == only_near[_ANCHOR].breakpoints


def test_tie_break_is_distance_then_user_id_and_input_order_free() -> None:
    # 600 users all at distance 0: the cap must keep the lowest 500 user ids.
    rows = _users(600)
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)
    a, _ = _build_color_pooled_cohort_cdf_for(rows, "opening_better_rate", "rapid")
    b, _ = _build_color_pooled_cohort_cdf_for(shuffled, "opening_better_rate", "rapid")
    assert a[_ANCHOR].breakpoints == b[_ANCHOR].breakpoints
    assert a[_ANCHOR].n_users == COHORT_MAX_USERS_PER_ANCHOR
    lowest = [r for r in rows if r.user_id <= COHORT_MAX_USERS_PER_ANCHOR]
    expected, _ = _build_color_pooled_cohort_cdf_for(lowest, "opening_better_rate", "rapid")
    assert a[_ANCHOR].breakpoints == expected[_ANCHOR].breakpoints


def test_single_colour_user_counts_as_one_user_with_one_point() -> None:
    both = _users(COHORT_MIN_USERS_PER_ANCHOR - 1)
    one_colour = [
        _PerUserColorRow(
            user_id=9_999,
            user_color="white",
            metric_value=0.5,
            n_games=_ROWS_PER_COLOR_GAMES,
            anchor_rating=_ANCHOR,
        )
    ]
    cdf, log = _build_color_pooled_cohort_cdf_for(both + one_colour, "opening_worse_rate", "blitz")
    entry = next(e for e in log if e["anchor"] == _ANCHOR)
    assert entry["n_in_window"] == COHORT_MIN_USERS_PER_ANCHOR
    assert cdf[_ANCHOR].n_users == COHORT_MIN_USERS_PER_ANCHOR


def _table(tag: float) -> CdfTable:
    return CdfTable(breakpoints=(tag,) * 99, n_users=100, snapshot_month="2026-05")


def test_merge_cells_replaces_only_selected_metrics() -> None:
    existing: CdfCells = {
        "score_gap": {(1500, "blitz"): _table(1.0)},
        "opening_worse_rate": {(1500, "blitz"): _table(2.0)},
    }
    fresh: CdfCells = {"opening_worse_rate": {(1600, "rapid"): _table(3.0)}}
    merged = merge_cells(existing, fresh, ["opening_worse_rate", "opening_better_rate"])
    assert merged["score_gap"] is existing["score_gap"]
    assert merged["opening_worse_rate"] == fresh["opening_worse_rate"]
    assert "opening_better_rate" not in merged


def test_opening_query_projects_color_and_composes_shared_builder() -> None:
    sql = _build_per_user_with_anchor_query(
        "opening_worse_rate", "blitz", snapshot_date=date(2026, 5, 26)
    )
    head = sql.split("FROM per_user_values puv")[0]
    assert "puv.user_id,\n  puv.user_color,\n  puv.metric_value," in head
    assert "pua.anchor_rating" in head
    assert "opening_out_classified" in sql
    assert "per_user_color_counts" in sql


def test_existing_metric_query_has_no_color_column() -> None:
    sql = _build_per_user_with_anchor_query("score_gap", "blitz", snapshot_date=date(2026, 5, 26))
    assert "puv.user_color" not in sql


def test_opening_metrics_are_appended_last() -> None:
    assert IN_SCOPE_METRICS[-2:] == ("opening_worse_rate", "opening_better_rate")


def test_every_in_scope_metric_has_a_report_display_name() -> None:
    # The first scoped opening regen wrote the TSV, then crashed at report render
    # with KeyError because _METRIC_DISPLAY lacked the opening ids.
    assert set(IN_SCOPE_METRICS) <= set(_METRIC_DISPLAY)


def test_metrics_flag_parses_and_rejects_unknown_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _parse_metrics("opening_worse_rate,opening_better_rate") == [
        "opening_worse_rate",
        "opening_better_rate",
    ]
    monkeypatch.setattr(
        sys,
        "argv",
        ["gen", "--target", "benchmark", "--metrics", "opening_worse_rate,opening_better_rate"],
    )
    assert parse_args().metrics == ["opening_worse_rate", "opening_better_rate"]

    monkeypatch.setattr(sys, "argv", ["gen", "--target", "benchmark", "--metrics", "not_a_metric"])
    with pytest.raises(SystemExit) as excinfo:
        parse_args()
    assert excinfo.value.code == 2
