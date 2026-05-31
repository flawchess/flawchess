"""Unit tests for the shared benchmark SQL building blocks (no DB).

The ELO bucketing is the one stat the SKILL.md SQL hand-rolls in every chapter; the
acceptance gate (`test_chapter1_diff.py`) only exercises it indirectly via the live
DB, so these tests pin the pure Python mirror and prove it stays aligned with the
generated SQL CASE.
"""

from __future__ import annotations

import pytest

from scripts.benchmarks import sql


@pytest.mark.parametrize(
    ("rating", "expected"),
    [
        (None, None),
        (799, None),  # sub-floor dropped
        (800, 800),  # lower edge of first bucket
        (1199, 800),  # upper edge of first bucket
        (1200, 1200),
        (1599, 1200),
        (1600, 1600),
        (1999, 1600),
        (2000, 2000),
        (2399, 2000),
        (2400, 2400),  # open-ended top bucket
        (3200, 2400),
    ],
)
def test_elo_bucket(rating: int | None, expected: int | None) -> None:
    assert sql.elo_bucket(rating) == expected


def test_elo_bucket_case_sql_mirrors_anchors() -> None:
    """The generated CASE must reference every anchor + a sub-floor NULL branch."""
    case = sql.elo_bucket_case_sql("r")
    assert case.startswith(f"CASE WHEN r < {sql.ELO_FLOOR} THEN NULL")
    for anchor in sql.ELO_ANCHORS:
        assert str(anchor) in case
    assert case.rstrip().endswith(f"ELSE {sql.ELO_ANCHORS[-1]} END")


def test_equal_footing_filter_uses_tolerance() -> None:
    assert f"<= {sql.EQUAL_FOOTING_TOLERANCE}" in sql.EQUAL_FOOTING_FILTER


def test_selected_users_cte_enforces_completed_checkpoint() -> None:
    """Canonical cohort join is non-optional: completed checkpoints only."""
    assert "bic.status = 'completed'" in sql.SELECTED_USERS_CTE
    assert "benchmark_ingest_checkpoints" in sql.SELECTED_USERS_CTE
