"""Weekly Train leaderboards: week window, ranking, slicing, visibility (Phase 230).

The repository returns one aggregate per user for the ISO week; everything
viewer-specific happens here in pure Python so each rule is unit-testable
without a database:

- D-02: the week is a UTC ISO week, half-open [Monday 00:00, next Monday 00:00),
  keyed on `drill_solves.solved_at`. `week_window` is standalone so a later medals
  snapshot can reuse it. Time only ever arrives as the `now_utc` argument (the
  router injects it from the `dev_now_utc` dependency), never the wall clock.
- D-03 / D-19: the Accuracy board lists everyone with at least one non-filler solve,
  marking users under 20 non-filler solves as tentative.
- D-04: competition ranks (1, 1, 1, 4); display order within equal value is puzzles
  desc, then name, then an internal key. Top 5 plus the viewer with 2 neighbours.
- D-05 / D-15: display name is the lichess username, else chess.com, else
  "Anonymous". No verification (impersonation is an accepted risk).
- D-06 / D-13 / D-14: other users' rows and ranks are computed only from registered,
  non-hidden users. A hidden viewer sees a private would-be row, a guest viewer a
  ghost row, each ranked among the visible users.

The internal `_Entry.key` (the user id) is never copied onto a response dataclass.
"""

from __future__ import annotations

import datetime
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Final

from app.repositories.train_leaderboard_repository import (
    SolveTotals,
    WeeklyAggregate,
    fetch_session_contribution,
    fetch_week_aggregates,
)
from app.schemas.train import LeaderboardBoardKind, LeaderboardVisibility
from app.services.train_score import TRAIN_POINTS_PER_PUZZLE
from sqlalchemy.ext.asyncio import AsyncSession

ACCURACY_QUALIFY_MIN_PUZZLES: Final = 20
LEADERBOARD_TOP_N: Final = 5
LEADERBOARD_NEIGHBOURS: Final = 2
DAYS_PER_WEEK: Final = 7
PERCENT_SCALE: Final = 100
ANONYMOUS_DISPLAY_NAME: Final = "Anonymous"


@dataclass(frozen=True)
class BoardRow:
    rank: int
    name: str
    value: int
    puzzles: int
    tentative: bool
    is_viewer: bool
    visibility: LeaderboardVisibility
    gap_before: bool


@dataclass(frozen=True)
class ViewerStanding:
    rank: int
    rank_without_session: int | None
    tentative: bool
    puzzles_to_qualify: int
    visibility: LeaderboardVisibility


@dataclass(frozen=True)
class PassTarget:
    name: str
    points_needed: int


@dataclass(frozen=True)
class Board:
    rows: tuple[BoardRow, ...]
    viewer: ViewerStanding | None
    pass_target: PassTarget | None


@dataclass(frozen=True)
class WeeklyLeaderboard:
    week_start: datetime.datetime
    week_end: datetime.datetime
    seconds_remaining: int
    points: Board
    accuracy: Board


@dataclass(frozen=True)
class _Entry:
    """One user's private board entry. `key` is internal and never serialized."""

    key: int
    name: str
    value: int
    puzzles: int
    tentative: bool
    is_public: bool  # registered and not opted out


def week_window(now_utc: datetime.datetime) -> tuple[datetime.datetime, datetime.datetime]:
    """ISO week [Monday 00:00 UTC, next Monday 00:00 UTC) containing now_utc (D-02)."""
    today = now_utc.astimezone(datetime.UTC).date()
    monday = today - datetime.timedelta(days=today.weekday())  # Monday == 0
    start = datetime.datetime.combine(monday, datetime.time.min, tzinfo=datetime.UTC)
    return start, start + datetime.timedelta(days=DAYS_PER_WEEK)


def display_name(lichess_username: str | None, chess_com_username: str | None) -> str:
    """Lichess username, else chess.com, else "Anonymous"; blank counts as missing (D-05)."""
    for candidate in (lichess_username, chess_com_username):
        if candidate is not None and candidate.strip():
            return candidate.strip()
    return ANONYMOUS_DISPLAY_NAME


def accuracy_percent(nf_points: int, nf_puzzles: int) -> int | None:
    """Pooled non-filler accuracy as a floored integer percent, None with no puzzles.

    Same flooring as the client's displaySessionPercentage, so the ordering never
    contradicts the number shown and ties are visible ties (no float equality).
    """
    if nf_puzzles == 0:
        return None
    return (PERCENT_SCALE * nf_points) // (TRAIN_POINTS_PER_PUZZLE * nf_puzzles)


def puzzles_to_qualify(nf_puzzles: int) -> int:
    """Non-filler puzzles still needed to leave the tentative Accuracy state (D-03)."""
    return max(0, ACCURACY_QUALIFY_MIN_PUZZLES - nf_puzzles)


def resolve_viewer_visibility(*, is_guest: bool, leaderboard_hidden: bool) -> LeaderboardVisibility:
    if is_guest:
        return "guest"
    if leaderboard_hidden:
        return "hidden"
    return "public"


def _entry_for(kind: LeaderboardBoardKind, aggregate: WeeklyAggregate) -> _Entry | None:
    """The user's entry on one board, or None when they have no place on it (D-19)."""
    totals = aggregate.totals
    name = display_name(aggregate.lichess_username, aggregate.chess_com_username)
    is_public = not aggregate.is_guest and not aggregate.leaderboard_hidden
    if kind == "points":
        return _Entry(aggregate.user_id, name, totals.points, totals.puzzles, False, is_public)
    percent = accuracy_percent(totals.nf_points, totals.nf_puzzles)
    if percent is None:
        return None
    return _Entry(
        aggregate.user_id,
        name,
        percent,
        totals.nf_puzzles,
        totals.nf_puzzles < ACCURACY_QUALIFY_MIN_PUZZLES,
        is_public,
    )


def _order_key(entry: _Entry) -> tuple[int, int, str, int]:
    return (-entry.value, -entry.puzzles, entry.name.casefold(), entry.key)


def _competition_ranks(ordered: Sequence[_Entry]) -> list[int]:
    """Competition ranks over an already ordered list: equal values share a rank."""
    ranks: list[int] = []
    for index, entry in enumerate(ordered):
        if index > 0 and entry.value == ordered[index - 1].value:
            ranks.append(ranks[index - 1])
        else:
            ranks.append(index + 1)
    return ranks


def _slice_indices(size: int, viewer_index: int | None) -> tuple[list[int], int | None]:
    """Indices to show (top N plus the viewer with neighbours) and the gap_before index.

    The gap index is the first shown row after skipped ranks, None when the shown rows
    are contiguous from the top.
    """
    top_end = min(LEADERBOARD_TOP_N, size)
    if viewer_index is None:
        return list(range(top_end)), None
    window_start = max(0, viewer_index - LEADERBOARD_NEIGHBOURS)
    window_end = min(size, viewer_index + LEADERBOARD_NEIGHBOURS + 1)
    if window_start <= LEADERBOARD_TOP_N:
        return list(range(max(top_end, window_end))), None
    return list(range(top_end)) + list(range(window_start, window_end)), window_start


def _pass_target(
    kind: LeaderboardBoardKind, ordered: Sequence[_Entry], viewer_index: int | None
) -> PassTarget | None:
    """Nearest row above the viewer with a strictly greater value (Points board only)."""
    if kind != "points" or viewer_index is None:
        return None
    viewer_value = ordered[viewer_index].value
    for entry in reversed(ordered[:viewer_index]):
        if entry.value > viewer_value:
            return PassTarget(name=entry.name, points_needed=entry.value - viewer_value + 1)
    return None


def totals_without(total: SolveTotals, contribution: SolveTotals) -> SolveTotals:
    """`total` minus `contribution`, each field clamped at 0 (D-12)."""
    return SolveTotals(
        points=max(0, total.points - contribution.points),
        puzzles=max(0, total.puzzles - contribution.puzzles),
        nf_points=max(0, total.nf_points - contribution.nf_points),
        nf_puzzles=max(0, total.nf_puzzles - contribution.nf_puzzles),
    )


def _rank_without(
    kind: LeaderboardBoardKind,
    entries: Sequence[_Entry],
    viewer_aggregate: WeeklyAggregate,
    contribution: SolveTotals,
) -> int | None:
    """The viewer's rank with one session's solves removed (D-12), None if nothing remains.

    Counted against `entries` filtered to the same visible others `rank` is computed
    against (public and not the viewer), never the combined list, which holds the
    viewer's full entry. Points can only worsen without a session; Accuracy can
    improve, and the value is returned as computed, never clamped to the real rank
    (D-18: the "(up N)" copy rule is the client's).
    """
    remaining = totals_without(viewer_aggregate.totals, contribution)
    if kind == "points" and remaining.puzzles == 0:
        return None
    viewer_entry = _entry_for(kind, replace(viewer_aggregate, totals=remaining))
    if viewer_entry is None:
        return None
    others = (e for e in entries if e.is_public and e.key != viewer_aggregate.user_id)
    return 1 + sum(1 for other in others if other.value > viewer_entry.value)


def build_board(
    kind: LeaderboardBoardKind,
    aggregates: Sequence[WeeklyAggregate],
    *,
    viewer_id: int,
    viewer_visibility: LeaderboardVisibility,
    session_contribution: SolveTotals | None = None,
) -> Board:
    """Rank one board for one viewer.

    Others are only registered, non-hidden users, filtered before ranking so a hidden
    user or guest can surface in no row, rank or pass target (D-06/D-13/D-14). The
    viewer's own entry (any visibility) joins them to form the combined list.
    """
    entries = [e for e in (_entry_for(kind, a) for a in aggregates) if e is not None]
    combined = [e for e in entries if e.is_public or e.key == viewer_id]
    ordered = sorted(combined, key=_order_key)
    ranks = _competition_ranks(ordered)
    viewer_index = next((i for i, e in enumerate(ordered) if e.key == viewer_id), None)
    indices, gap_index = _slice_indices(len(ordered), viewer_index)
    rows = tuple(
        BoardRow(
            rank=ranks[i],
            name=ordered[i].name,
            value=ordered[i].value,
            puzzles=ordered[i].puzzles,
            tentative=ordered[i].tentative,
            is_viewer=i == viewer_index,
            visibility=viewer_visibility if i == viewer_index else "public",
            gap_before=i == gap_index,
        )
        for i in indices
    )
    viewer: ViewerStanding | None = None
    if viewer_index is not None:
        viewer_entry = ordered[viewer_index]
        viewer_aggregate = next((a for a in aggregates if a.user_id == viewer_id), None)
        without = (
            _rank_without(kind, entries, viewer_aggregate, session_contribution)
            if session_contribution is not None and viewer_aggregate is not None
            else None
        )
        viewer = ViewerStanding(
            rank=ranks[viewer_index],
            rank_without_session=without,
            tentative=viewer_entry.tentative,
            puzzles_to_qualify=puzzles_to_qualify(viewer_entry.puzzles)
            if kind == "accuracy"
            else 0,
            visibility=viewer_visibility,
        )
    return Board(rows=rows, viewer=viewer, pass_target=_pass_target(kind, ordered, viewer_index))


def build_leaderboard(
    aggregates: Sequence[WeeklyAggregate],
    *,
    viewer_id: int,
    viewer_visibility: LeaderboardVisibility,
    week_start: datetime.datetime,
    week_end: datetime.datetime,
    now_utc: datetime.datetime,
    session_contribution: SolveTotals | None = None,
) -> WeeklyLeaderboard:
    return WeeklyLeaderboard(
        week_start=week_start,
        week_end=week_end,
        # WR-03 (phase 230 review): round UP. Truncating let the client's countdown
        # reach 0 up to ~1 s before the real deadline, so its rollover refetch could
        # land while the old week was still current.
        seconds_remaining=max(0, math.ceil((week_end - now_utc).total_seconds())),
        points=build_board(
            "points",
            aggregates,
            viewer_id=viewer_id,
            viewer_visibility=viewer_visibility,
            session_contribution=session_contribution,
        ),
        accuracy=build_board(
            "accuracy",
            aggregates,
            viewer_id=viewer_id,
            viewer_visibility=viewer_visibility,
            session_contribution=session_contribution,
        ),
    )


async def get_weekly_leaderboard(
    session: AsyncSession,
    *,
    viewer_id: int,
    viewer_is_guest: bool,
    viewer_hidden: bool,
    now_utc: datetime.datetime,
    session_id: int | None = None,
) -> WeeklyLeaderboard:
    """Both weekly boards for the viewer. Sequential awaits, no concurrency on the session.

    With `session_id`, the viewer's own in-window solves of that session are fetched
    after the aggregate and passed on so each board also reports the viewer's rank
    without them (D-12). The fetch is scoped to the viewer, so a foreign id is inert.
    """
    week_start, week_end = week_window(now_utc)
    aggregates = await fetch_week_aggregates(session, week_start=week_start, week_end=week_end)
    contribution: SolveTotals | None = None
    if session_id is not None:
        contribution = await fetch_session_contribution(
            session,
            user_id=viewer_id,
            session_id=session_id,
            week_start=week_start,
            week_end=week_end,
        )
    return build_leaderboard(
        aggregates,
        viewer_id=viewer_id,
        viewer_visibility=resolve_viewer_visibility(
            is_guest=viewer_is_guest, leaderboard_hidden=viewer_hidden
        ),
        week_start=week_start,
        week_end=week_end,
        now_utc=now_utc,
        session_contribution=contribution,
    )
