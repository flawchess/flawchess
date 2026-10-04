"""Unit tests for app.services.train_leaderboard (Phase 230, plans 01 and 02). DB-free.

Every test builds WeeklyAggregate / SolveTotals values directly. Test names carry a
rule token (window, display_name, accuracy_percent, qualify, rank, slice,
pass_target, hidden, guest, without_session, totals_without, tier) so the VALIDATION map can select them with pytest -k.
"""

from __future__ import annotations

import datetime

import pytest

from app.repositories.train_leaderboard_repository import SolveTotals, WeeklyAggregate
from app.services.train_leaderboard import (
    ACCURACY_QUALIFY_MIN_PUZZLES,
    ANONYMOUS_DISPLAY_NAME,
    LEADERBOARD_TOP_N,
    Board,
    BoardRow,
    accuracy_percent,
    build_board,
    build_leaderboard,
    display_name,
    puzzles_to_qualify,
    totals_without,
    resolve_viewer_visibility,
    week_window,
)

UTC = datetime.UTC


def _agg(
    user_id: int,
    *,
    points: int = 0,
    puzzles: int = 1,
    nf_points: int | None = None,
    nf_puzzles: int | None = None,
    name: str | None = None,
    chess_com: str | None = None,
    is_guest: bool = False,
    hidden: bool = False,
) -> WeeklyAggregate:
    """A weekly aggregate; the non-filler totals default to the all-solves totals."""
    return WeeklyAggregate(
        user_id=user_id,
        totals=SolveTotals(
            points=points,
            puzzles=puzzles,
            nf_points=points if nf_points is None else nf_points,
            nf_puzzles=puzzles if nf_puzzles is None else nf_puzzles,
        ),
        lichess_username=name if name is not None else f"user{user_id:02d}",
        chess_com_username=chess_com,
        is_guest=is_guest,
        leaderboard_hidden=hidden,
    )


def _rk(row: BoardRow) -> int:
    """A row's rank, asserted numeric (Points rows are always ranked)."""
    assert row.rank is not None
    return row.rank


def _points(aggs: list[WeeklyAggregate], viewer_id: int) -> Board:
    return build_board("points", aggs, viewer_id=viewer_id, viewer_visibility="public")


def _accuracy(aggs: list[WeeklyAggregate], viewer_id: int) -> Board:
    return build_board("accuracy", aggs, viewer_id=viewer_id, viewer_visibility="public")


# --- window -----------------------------------------------------------------


def test_window_midweek_is_monday_to_next_monday_utc() -> None:
    start, end = week_window(datetime.datetime(2031, 1, 8, 12, 0, tzinfo=UTC))
    assert start == datetime.datetime(2031, 1, 6, tzinfo=UTC)
    assert end == datetime.datetime(2031, 1, 13, tzinfo=UTC)


def test_window_monday_midnight_belongs_to_the_new_week() -> None:
    start, _ = week_window(datetime.datetime(2031, 1, 13, 0, 0, 0, tzinfo=UTC))
    assert start == datetime.datetime(2031, 1, 13, tzinfo=UTC)


def test_window_sunday_last_microsecond_belongs_to_the_ending_week() -> None:
    start, end = week_window(datetime.datetime(2031, 1, 12, 23, 59, 59, 999999, tzinfo=UTC))
    assert start == datetime.datetime(2031, 1, 6, tzinfo=UTC)
    assert end == datetime.datetime(2031, 1, 13, tzinfo=UTC)


def test_window_deadline_splits_adjacent_weeks_without_overlap() -> None:
    """A session spanning the deadline splits by timestamp: [start, end) is half-open."""
    _, ending_week_end = week_window(datetime.datetime(2031, 1, 12, 23, 59, 59, 999999, tzinfo=UTC))
    new_week_start, _ = week_window(datetime.datetime(2031, 1, 13, 0, 0, 0, tzinfo=UTC))
    assert ending_week_end == new_week_start


def test_window_converts_aware_non_utc_input_to_utc_first() -> None:
    # Monday 01:00 at +14:00 is Sunday 11:00 UTC, so it is still the previous week.
    plus_14 = datetime.timezone(datetime.timedelta(hours=14))
    start, _ = week_window(datetime.datetime(2031, 1, 13, 1, 0, tzinfo=plus_14))
    assert start == datetime.datetime(2031, 1, 6, tzinfo=UTC)


def test_window_seconds_remaining_counts_down_to_the_deadline() -> None:
    now = datetime.datetime(2031, 1, 12, 23, 0, tzinfo=UTC)
    start, end = week_window(now)
    board = build_leaderboard(
        [],
        viewer_id=1,
        viewer_visibility="public",
        week_start=start,
        week_end=end,
        now_utc=now,
    )
    assert board.seconds_remaining == 3600


def test_window_seconds_remaining_rounds_up_inside_the_last_second() -> None:
    # WR-03: truncating to 0 here let the client roll over before the server's reset.
    now = datetime.datetime(2031, 1, 12, 23, 59, 59, 500_000, tzinfo=UTC)
    start, end = week_window(now)
    board = build_leaderboard(
        [],
        viewer_id=1,
        viewer_visibility="public",
        week_start=start,
        week_end=end,
        now_utc=now,
    )
    assert board.seconds_remaining == 1


# --- display_name -----------------------------------------------------------


@pytest.mark.parametrize(
    ("lichess", "chess_com", "expected"),
    [
        ("magnus", None, "magnus"),
        (None, "hikaru", "hikaru"),
        ("magnus", "hikaru", "magnus"),
        (None, None, ANONYMOUS_DISPLAY_NAME),
        ("", None, ANONYMOUS_DISPLAY_NAME),
        ("   ", "   ", ANONYMOUS_DISPLAY_NAME),
        ("   ", "hikaru", "hikaru"),
        ("  magnus ", None, "magnus"),
    ],
)
def test_display_name_precedence_and_blank_handling(
    lichess: str | None, chess_com: str | None, expected: str
) -> None:
    assert display_name(lichess, chess_com) == expected


# --- accuracy_percent -------------------------------------------------------


@pytest.mark.parametrize(
    ("nf_points", "nf_puzzles", "expected"),
    [(20, 9, 74), (27, 9, 100), (0, 5, 0), (5, 0, None)],
)
def test_accuracy_percent_is_a_floored_integer(
    nf_points: int, nf_puzzles: int, expected: int | None
) -> None:
    assert accuracy_percent(nf_points, nf_puzzles) == expected


# --- qualify ----------------------------------------------------------------


def test_qualify_below_the_minimum_is_tentative_with_puzzles_to_go() -> None:
    board = _accuracy([_agg(1, points=57, puzzles=19)], viewer_id=1)
    assert board.viewer is not None
    assert board.viewer.tentative is True
    assert board.viewer.puzzles_to_qualify == 1
    assert board.rows[0].tentative is True
    assert board.viewer.rank is None
    assert board.rows[0].rank is None


def test_qualify_at_the_minimum_is_no_longer_tentative() -> None:
    board = _accuracy([_agg(1, points=60, puzzles=ACCURACY_QUALIFY_MIN_PUZZLES)], viewer_id=1)
    assert board.viewer is not None
    assert board.viewer.tentative is False
    assert board.viewer.puzzles_to_qualify == 0
    assert board.rows[0].tentative is False


def test_qualify_filler_only_user_has_no_accuracy_entry_but_a_points_row() -> None:
    filler_only = _agg(1, points=9, puzzles=3, nf_points=0, nf_puzzles=0)
    accuracy = _accuracy([filler_only], viewer_id=1)
    points = _points([filler_only], viewer_id=1)
    assert accuracy.viewer is None
    assert accuracy.rows == ()
    assert points.viewer is not None
    assert points.viewer.rank == 1
    assert points.viewer.puzzles_to_qualify == 0


def test_qualify_counts_only_non_filler_puzzles_on_the_accuracy_board() -> None:
    mixed = _agg(1, points=30, puzzles=10, nf_points=6, nf_puzzles=2)
    row = _accuracy([mixed], viewer_id=1).rows[0]
    assert (row.value, row.puzzles) == (100, 2)
    assert _points([mixed], viewer_id=1).rows[0].puzzles == 10


@pytest.mark.parametrize(("done", "left"), [(0, 20), (19, 1), (20, 0), (35, 0)])
def test_qualify_puzzles_to_qualify_never_goes_negative(done: int, left: int) -> None:
    assert puzzles_to_qualify(done) == left


# --- rank -------------------------------------------------------------------


def test_rank_ties_share_a_competition_rank() -> None:
    aggs = [
        _agg(1, points=10),
        _agg(2, points=10),
        _agg(3, points=10),
        _agg(4, points=7),
    ]
    board = _points(aggs, viewer_id=4)
    assert [r.rank for r in board.rows] == [1, 1, 1, 4]
    assert board.viewer is not None
    assert board.viewer.rank == 4


def test_rank_within_a_tie_lists_the_row_with_more_puzzles_first() -> None:
    aggs = [
        _agg(1, points=10, puzzles=2, name="few"),
        _agg(2, points=10, puzzles=6, name="many"),
        _agg(3, points=10, puzzles=4, name="mid"),
    ]
    assert [r.name for r in _points(aggs, viewer_id=1).rows] == ["many", "mid", "few"]


def test_rank_equal_value_and_puzzles_fall_back_to_casefolded_name() -> None:
    aggs = [
        _agg(1, points=10, puzzles=3, name="bravo"),
        _agg(2, points=10, puzzles=3, name="Alpha"),
        _agg(3, points=10, puzzles=3, name="charlie"),
    ]
    assert [r.name for r in _points(aggs, viewer_id=1).rows] == ["Alpha", "bravo", "charlie"]


def test_rank_accuracy_ties_are_visible_ties_on_the_floored_percent() -> None:
    # 56/63 = 88.9% and 64/72 = 88.9% both floor to 88, so they tie; puzzles breaks the order.
    # All three are qualified (20+ puzzles), so all are ranked.
    aggs = [
        _agg(1, points=56, puzzles=21),  # 56/63 -> 88
        _agg(2, points=64, puzzles=24),  # 64/72 -> 88
        _agg(3, points=60, puzzles=20),  # 100
    ]
    board = _accuracy(aggs, viewer_id=1)
    assert [(r.rank, r.value, r.puzzles) for r in board.rows] == [
        (1, 100, 20),
        (2, 88, 24),
        (2, 88, 21),
    ]


# --- slice ------------------------------------------------------------------

_SLICE_SIZE = 12


def _ladder(size: int) -> list[WeeklyAggregate]:
    """`size` users with strictly descending points: user j holds rank j + 1."""
    return [_agg(j + 1, points=(size - j) * 10) for j in range(size)]


@pytest.mark.parametrize(
    ("viewer_index", "shown", "gap_position"),
    [
        (0, list(range(0, 5)), None),
        (4, list(range(0, 7)), None),
        (5, list(range(0, 8)), None),
        (6, list(range(0, 9)), None),
        (7, list(range(0, 10)), None),
        (8, [0, 1, 2, 3, 4, 6, 7, 8, 9, 10], 6),
        (11, [0, 1, 2, 3, 4, 9, 10, 11], 9),
    ],
)
def test_slice_top_n_plus_viewer_neighbours_with_single_gap(
    viewer_index: int, shown: list[int], gap_position: int | None
) -> None:
    board = _points(_ladder(_SLICE_SIZE), viewer_id=viewer_index + 1)
    assert [_rk(r) - 1 for r in board.rows] == shown
    gap_positions = [_rk(r) - 1 for r in board.rows if r.gap_before]
    assert gap_positions == ([] if gap_position is None else [gap_position])
    viewer_rows = [r for r in board.rows if r.is_viewer]
    assert [_rk(r) - 1 for r in viewer_rows] == [viewer_index]


def test_slice_short_board_returns_every_row() -> None:
    for viewer_id in (1, 2, 3):
        board = _points(_ladder(3), viewer_id=viewer_id)
        assert len(board.rows) == 3
        assert not any(r.gap_before for r in board.rows)


def test_slice_without_a_viewer_entry_returns_only_the_top_n() -> None:
    aggs = _ladder(_SLICE_SIZE)
    board = _points(aggs, viewer_id=999)
    assert len(board.rows) == LEADERBOARD_TOP_N
    assert board.viewer is None
    assert not any(r.is_viewer for r in board.rows)


# --- pass_target ------------------------------------------------------------


def test_pass_target_is_the_nearest_strictly_better_row_skipping_ties() -> None:
    aggs = [
        _agg(1, points=20, name="leader"),
        _agg(2, points=10, puzzles=5, name="tied"),
        _agg(3, points=10, puzzles=3, name="viewer"),
    ]
    target = _points(aggs, viewer_id=3).pass_target
    assert target is not None
    assert (target.name, target.points_needed) == ("leader", 11)


def test_pass_target_is_the_row_directly_above_when_strictly_better() -> None:
    aggs = [
        _agg(1, points=30, name="top"),
        _agg(2, points=14, name="next"),
        _agg(3, points=10, name="viewer"),
    ]
    target = _points(aggs, viewer_id=3).pass_target
    assert target is not None
    assert (target.name, target.points_needed) == ("next", 5)


def test_pass_target_is_none_at_rank_one() -> None:
    aggs = [_agg(1, points=20), _agg(2, points=10)]
    assert _points(aggs, viewer_id=1).pass_target is None


def test_pass_target_is_none_when_the_viewer_has_no_entry() -> None:
    assert _points([_agg(1, points=20)], viewer_id=999).pass_target is None


def test_pass_target_is_never_set_on_the_accuracy_board() -> None:
    aggs = [_agg(1, points=3, puzzles=1), _agg(2, points=1, puzzles=1)]
    assert _accuracy(aggs, viewer_id=2).pass_target is None


# --- hidden -----------------------------------------------------------------


def test_hidden_user_is_absent_from_a_public_viewers_board_and_rank() -> None:
    aggs = [
        _agg(1, points=100, name="hiddenleader", hidden=True),
        _agg(2, points=20, name="visible"),
        _agg(3, points=10, name="viewer"),
    ]
    board = _points(aggs, viewer_id=3)
    assert [r.name for r in board.rows] == ["visible", "viewer"]
    assert board.viewer is not None
    assert board.viewer.rank == 2
    assert board.pass_target is not None
    assert board.pass_target.name == "visible"


def test_hidden_viewer_gets_a_private_would_be_row_among_visible_users() -> None:
    aggs = [
        _agg(1, points=10, name="alpha"),
        _agg(2, points=6, name="bravo"),
        _agg(3, points=8, name="me", hidden=True),
    ]
    board = build_board("points", aggs, viewer_id=3, viewer_visibility="hidden")
    assert [(r.rank, r.name, r.visibility, r.is_viewer) for r in board.rows] == [
        (1, "alpha", "public", False),
        (2, "me", "hidden", True),
        (3, "bravo", "public", False),
    ]
    assert board.viewer is not None
    assert (board.viewer.rank, board.viewer.visibility) == (2, "hidden")
    # A different public viewer never sees the hidden user and ranks without them.
    other_view = _points(aggs, viewer_id=2)
    assert [(r.rank, r.name) for r in other_view.rows] == [(1, "alpha"), (2, "bravo")]


# --- guest ------------------------------------------------------------------


def test_guest_never_appears_on_or_shifts_a_registered_viewers_board() -> None:
    aggs = [
        _agg(1, points=50, puzzles=20, name="ghost", is_guest=True),
        _agg(2, points=20, puzzles=20, name="registered"),
        _agg(3, points=10, puzzles=20, name="viewer"),
    ]
    for kind in ("points", "accuracy"):
        board = build_board(kind, aggs, viewer_id=3, viewer_visibility="public")
        assert "ghost" not in [r.name for r in board.rows]
        assert board.viewer is not None
        assert board.viewer.rank == 2


def test_guest_viewer_gets_a_ghost_row_at_the_would_be_rank() -> None:
    aggs = [
        _agg(1, points=30, name="alpha"),
        _agg(2, points=10, name="bravo"),
        _agg(3, points=20, name="me", is_guest=True),
    ]
    visibility = resolve_viewer_visibility(is_guest=True, leaderboard_hidden=False)
    assert visibility == "guest"
    board = build_board("points", aggs, viewer_id=3, viewer_visibility=visibility)
    assert [(r.rank, r.name, r.visibility) for r in board.rows] == [
        (1, "alpha", "public"),
        (2, "me", "guest"),
        (3, "bravo", "public"),
    ]
    assert board.viewer is not None
    assert board.viewer.visibility == "guest"


def test_guest_visibility_wins_over_hidden_and_public_is_the_default() -> None:
    assert resolve_viewer_visibility(is_guest=True, leaderboard_hidden=True) == "guest"
    assert resolve_viewer_visibility(is_guest=False, leaderboard_hidden=True) == "hidden"
    assert resolve_viewer_visibility(is_guest=False, leaderboard_hidden=False) == "public"


# --- without_session (D-12 / D-18) -------------------------------------------


def _contribution(
    points: int, puzzles: int, nf_points: int | None = None, nf_puzzles: int | None = None
) -> SolveTotals:
    return SolveTotals(
        points=points,
        puzzles=puzzles,
        nf_points=points if nf_points is None else nf_points,
        nf_puzzles=puzzles if nf_puzzles is None else nf_puzzles,
    )


def test_without_session_points_ranks_the_remaining_total_against_unchanged_others() -> None:
    aggs = [
        _agg(1, points=25, puzzles=10, name="alpha"),
        _agg(2, points=20, puzzles=10, name="bravo"),
        _agg(3, points=15, puzzles=10, name="charlie"),
        _agg(9, points=30, puzzles=10, name="viewer"),
    ]
    board = build_board(
        "points",
        aggs,
        viewer_id=9,
        viewer_visibility="public",
        session_contribution=_contribution(points=12, puzzles=4),
    )
    assert board.viewer is not None
    assert board.viewer.rank == 1
    # 30 - 12 = 18: behind 25 and 20, ahead of 15.
    assert board.viewer.rank_without_session == 3


def test_without_session_is_none_when_the_session_was_everything_or_absent() -> None:
    aggs = [_agg(1, points=20, puzzles=5, name="alpha"), _agg(2, points=9, puzzles=3, name="me")]
    everything = build_board(
        "points",
        aggs,
        viewer_id=2,
        viewer_visibility="public",
        session_contribution=_contribution(points=9, puzzles=3),
    )
    absent = build_board("points", aggs, viewer_id=2, viewer_visibility="public")
    assert everything.viewer is not None and absent.viewer is not None
    assert everything.viewer.rank_without_session is None
    assert absent.viewer.rank_without_session is None
    accuracy = build_board(
        "accuracy",
        aggs,
        viewer_id=2,
        viewer_visibility="public",
        session_contribution=_contribution(points=9, puzzles=3),
    )
    assert accuracy.viewer is not None
    assert accuracy.viewer.rank_without_session is None


def test_without_session_viewer_without_an_entry_has_no_standing() -> None:
    # A filler-only viewer has a Points entry but no Accuracy entry (D-19).
    aggs = [
        _agg(1, points=20, puzzles=5, name="alpha"),
        _agg(2, points=6, puzzles=2, nf_points=0, nf_puzzles=0, name="me"),
    ]
    board = build_board(
        "accuracy",
        aggs,
        viewer_id=2,
        viewer_visibility="public",
        session_contribution=_contribution(points=6, puzzles=2, nf_points=0, nf_puzzles=0),
    )
    assert board.viewer is None


def test_without_session_accuracy_can_improve_and_is_returned_unclamped() -> None:
    # Strong earlier solves (20 puzzles at 100 percent) plus a weak session (10 puzzles
    # at 0 percent): 66 percent with the session, 100 percent without it. The 20 remaining
    # puzzles keep the viewer qualified, so the delta is still computed.
    aggs = [
        _agg(1, points=60, puzzles=20, name="rival"),  # 100 percent
        _agg(2, points=45, puzzles=20, name="mid"),  # 75 percent
        _agg(9, points=60, puzzles=30, name="viewer"),  # 66 percent
    ]
    board = build_board(
        "accuracy",
        aggs,
        viewer_id=9,
        viewer_visibility="public",
        session_contribution=_contribution(points=0, puzzles=10),
    )
    assert board.viewer is not None
    assert board.viewer.rank == 3
    # Without the weak session the viewer is at 100 percent and ties for first.
    assert board.viewer.rank_without_session == 1
    assert board.viewer.rank_without_session < board.viewer.rank


def test_without_session_hidden_viewer_counts_only_visible_others() -> None:
    aggs = [
        _agg(1, points=50, puzzles=10, name="hiddenleader", hidden=True),
        _agg(2, points=45, puzzles=10, name="ghost", is_guest=True),
        _agg(3, points=20, puzzles=10, name="visible"),
        _agg(9, points=40, puzzles=10, name="me", hidden=True),
    ]
    board = build_board(
        "points",
        aggs,
        viewer_id=9,
        viewer_visibility="hidden",
        session_contribution=_contribution(points=15, puzzles=3),
    )
    assert board.viewer is not None
    # 40 beats the only visible other (20) for rank 1; 25 still does.
    assert board.viewer.rank == 1
    assert board.viewer.rank_without_session == 1


def test_totals_without_subtracts_each_field_and_clamps_at_zero() -> None:
    total = SolveTotals(points=10, puzzles=4, nf_points=8, nf_puzzles=3)
    assert totals_without(total, SolveTotals(3, 1, 2, 1)) == SolveTotals(7, 3, 6, 2)
    assert totals_without(total, SolveTotals(99, 99, 99, 99)) == SolveTotals(0, 0, 0, 0)


# --- tier (quick 261004-8rt: qualified first, tentative unranked below) -------


def test_tier_qualified_user_outranks_tentative_users_at_a_higher_percent() -> None:
    aggs = [
        _agg(1, points=30, puzzles=20, name="steady"),  # 50 percent, qualified
        _agg(2, points=3, puzzles=1, name="lucky"),  # 100 percent, 1 puzzle
        _agg(3, points=57, puzzles=19, name="almost"),  # 100 percent, 19 puzzles
    ]
    board = _accuracy(aggs, viewer_id=1)
    assert [(r.name, r.rank, r.tentative) for r in board.rows] == [
        ("steady", 1, False),
        ("almost", None, True),
        ("lucky", None, True),
    ]


def test_tier_tentative_rows_order_by_puzzles_then_value_then_name() -> None:
    aggs = [
        _agg(1, points=3 * 2, puzzles=2, name="bravo"),  # 2 puzzles, 100
        _agg(2, points=3 * 2, puzzles=2, name="Alpha"),  # 2 puzzles, 100
        _agg(3, points=15, puzzles=10, name="fifty"),  # 10 puzzles, 50
        _agg(4, points=27, puzzles=10, name="ninety"),  # 10 puzzles, 90
    ]
    board = _accuracy(aggs, viewer_id=1)
    assert [r.name for r in board.rows] == ["ninety", "fifty", "Alpha", "bravo"]
    assert all(r.rank is None and r.tentative for r in board.rows)


def test_tier_competition_ranks_among_qualified_ignore_tentative_rows() -> None:
    aggs = [
        _agg(1, points=60, puzzles=20, name="top"),  # 100
        _agg(2, points=56, puzzles=21, name="tie_a"),  # 88
        _agg(3, points=64, puzzles=24, name="tie_b"),  # 88
        _agg(4, points=3, puzzles=1, name="tentative"),
    ]
    board = _accuracy(aggs, viewer_id=1)
    assert [r.rank for r in board.rows] == [1, 2, 2, None]


def test_tier_all_tentative_week_shows_the_five_most_active() -> None:
    aggs = [_agg(i, points=3 * (i + 1), puzzles=i + 1) for i in range(1, 9)]
    board = _accuracy(aggs, viewer_id=999)
    assert [r.puzzles for r in board.rows] == [9, 8, 7, 6, 5]
    assert all(r.rank is None for r in board.rows)


def test_tier_slice_windows_over_the_combined_qualified_then_tentative_list() -> None:
    qualified = [_agg(i, points=60 - i, puzzles=20, name=f"q{i}") for i in (1, 2, 3)]
    tentative = [_agg(i, points=3 * (23 - i), puzzles=23 - i, name=f"t{i}") for i in range(4, 14)]
    # Tentative puzzles are 19..10 in id order; id 12 (11 puzzles) is the 9th tentative.
    board = _accuracy([*qualified, *tentative], viewer_id=12)
    assert [r.name for r in board.rows] == [
        "q1",
        "q2",
        "q3",
        "t4",
        "t5",
        "t10",
        "t11",
        "t12",
        "t13",
    ]
    assert [r.rank for r in board.rows] == [1, 2, 3, None, None, None, None, None, None]
    assert [r.gap_before for r in board.rows].count(True) == 1
    assert board.rows[5].gap_before is True
    assert board.rows[7].is_viewer is True
    assert board.viewer is not None
    assert board.viewer.rank is None


def test_tier_tentative_viewer_is_unranked_and_gets_no_rank_without_delta() -> None:
    aggs = [
        _agg(1, points=60, puzzles=20, name="qualified"),
        _agg(9, points=15, puzzles=5, name="viewer"),
    ]
    board = build_board(
        "accuracy",
        aggs,
        viewer_id=9,
        viewer_visibility="public",
        session_contribution=_contribution(points=6, puzzles=2),
    )
    assert board.viewer is not None
    assert board.viewer.rank is None
    assert board.viewer.tentative is True
    assert board.viewer.puzzles_to_qualify == 15
    assert board.viewer.rank_without_session is None


def test_tier_session_that_crossed_the_cutoff_has_no_rank_without_delta() -> None:
    # 22 puzzles with the session, 17 without: ranked now, tentative without the session.
    aggs = [
        _agg(1, points=60, puzzles=20, name="qualified"),
        _agg(9, points=66, puzzles=22, name="viewer"),
    ]
    board = build_board(
        "accuracy",
        aggs,
        viewer_id=9,
        viewer_visibility="public",
        session_contribution=_contribution(points=15, puzzles=5),
    )
    assert board.viewer is not None
    assert board.viewer.rank is not None
    assert board.viewer.rank_without_session is None


def test_tier_rank_without_compares_against_qualified_visible_others_only() -> None:
    aggs = [
        _agg(1, points=54, puzzles=20, name="rival"),  # 90
        _agg(2, points=36, puzzles=20, name="low"),  # 60
        _agg(3, points=3, puzzles=1, name="flash"),  # 100, tentative
        _agg(9, points=48, puzzles=30, name="viewer"),  # 53 with, 80 without
    ]
    board = build_board(
        "accuracy",
        aggs,
        viewer_id=9,
        viewer_visibility="public",
        session_contribution=_contribution(points=0, puzzles=10),
    )
    assert board.viewer is not None
    assert board.viewer.rank == 3
    # The tentative 100 percent "flash" does not count ahead of the viewer.
    assert board.viewer.rank_without_session == 2


@pytest.mark.parametrize("visibility", ["guest", "hidden"])
def test_tier_guest_and_hidden_viewers_sit_in_the_tentative_section(visibility: str) -> None:
    aggs = [
        _agg(1, points=30, puzzles=20, name="qualified"),
        _agg(2, points=15, puzzles=5, name="public_tentative"),
        _agg(
            9,
            points=9,
            puzzles=3,
            name="me",
            is_guest=visibility == "guest",
            hidden=visibility == "hidden",
        ),
    ]
    viewer_visibility = resolve_viewer_visibility(
        is_guest=visibility == "guest", leaderboard_hidden=visibility == "hidden"
    )
    board = build_board("accuracy", aggs, viewer_id=9, viewer_visibility=viewer_visibility)
    assert [(r.name, r.rank, r.visibility) for r in board.rows] == [
        ("qualified", 1, "public"),
        ("public_tentative", None, "public"),
        ("me", None, visibility),
    ]
    # A different public viewer sees neither the guest nor the hidden user in any tier.
    other = _accuracy(aggs, viewer_id=2)
    assert [r.name for r in other.rows] == ["qualified", "public_tentative"]
