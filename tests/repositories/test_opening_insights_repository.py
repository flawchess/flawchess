"""Phase 70 repository SQL contract tests — INSIGHT-CORE-02, INSIGHT-CORE-03, INSIGHT-CORE-04.

Wave 0 scaffolding: tests collect under pytest and FAIL with NotImplementedError until
Plan 70-03 lands the query_opening_transitions function. Downstream plans flip them green.
"""

from __future__ import annotations


def test_entry_ply_lower_bound_3_inclusive() -> None:
    """D-32: entry_ply = 3 is included in transition results."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_entry_ply_upper_bound_16_inclusive() -> None:
    """D-32: entry_ply = 16 is included in transition results."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_entry_ply_2_excluded() -> None:
    """D-32: entry_ply = 2 is excluded (below MIN_ENTRY_PLY = 3)."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_entry_ply_17_excluded_as_entry_but_included_as_candidate() -> None:
    """D-32: ply 17 is a valid candidate ply but NOT a valid entry ply (entry max = 16).
    A transition where ply=17 (candidate) and entry_hash is ply=16 is included."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_lag_returns_null_for_first_ply_of_each_game() -> None:
    """RESEARCH.md Pitfall 2: LAG(full_hash) with PARTITION BY game_id returns NULL
    for the very first ply of each game, preventing cross-game phantom entries."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_min_games_per_candidate_floor_at_20() -> None:
    """D-33: n=19 is excluded, n=20 is included by the HAVING clause."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_having_strict_gt_055_drops_neutrals() -> None:
    """D-04: HAVING clause uses strict > 0.55; exactly 0.550 is dropped (neutral)."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_user_color_filter_routes_correct_games() -> None:
    """The color parameter restricts to games where game.user_color matches exactly."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_apply_game_filters_recency_narrows_results() -> None:
    """INSIGHT-CORE-01: apply_game_filters recency parameter correctly limits the
    game date window, reducing findings when older games are excluded."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")


def test_partial_index_predicate_alignment() -> None:
    """RESEARCH.md A6: smoke-check that EXPLAIN output shows ix_gp_user_game_ply
    (Index Only Scan on game_positions) is used by the transition query."""
    raise NotImplementedError("Wave 0 stub — Plan 70-03 (repository) implements")
