"""Weekly Train leaderboards: week window, ranking, slicing, visibility (Phase 230).

The repository returns one aggregate per user for the ISO week; everything
viewer-specific happens here in pure Python so each rule is unit-testable
without a database:

- D-02: the week is a UTC ISO week, half-open [Monday 00:00, next Monday 00:00),
  keyed on `drill_solves.solved_at`. `week_window` is standalone so a later medals
  snapshot can reuse it. Time only ever arrives as the `now_utc` argument (the
  router injects it from the `dev_now_utc` dependency), never the wall clock.
- D-03 / D-19 (amended by quick 261004-8rt, which superseded D-03's interleaved
  ranking): the Accuracy board lists everyone with at least one non-filler solve.
  Users with 20+ non-filler solves are qualified and ranked first by accuracy; users
  under 20 are tentative, listed below every qualified user with no rank, ordered by
  puzzles desc, then accuracy desc, then name.
- D-04: competition ranks (1, 1, 1, 4) among qualified entries; display order within
  equal value is puzzles desc, then name, then an internal key. Top 5 plus the viewer
  with 2 neighbours.
- D-05 / D-15: display name is the lichess username, else chess.com, else
  "Anonymous". No verification (impersonation is an accepted risk).
- D-06 / D-13 / D-14: other users' rows and ranks are computed only from registered,
  non-hidden users. A hidden viewer sees a private would-be row, a guest viewer a
  ghost row, each ranked among the visible users.

Phase 231 adds the closed-week side: `final_standings` / `medal_for` freeze a week's
public standings with the SAME `_entry_for` / `_tiered_order` as the live board (no
second ranking implementation), and `build_last_week` turns the stored rows into the
previous week's podium.

The internal `_Entry.key` (the user id) is never copied onto a response dataclass.
"""

from __future__ import annotations

import datetime
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Final

from app.models.train_weekly_standing import Medal
from app.repositories.train_leaderboard_repository import (
    SolveTotals,
    WeeklyAggregate,
    fetch_session_contribution,
    fetch_week_aggregates,
)
from app.repositories.train_medals_repository import (
    StandingRow,
    TallyCount,
    fetch_last_week_rows,
    fetch_medal_tallies,
)
from app.schemas.train import LeaderboardBoardKind, LeaderboardVisibility, MedalKind
from app.services.train_score import TRAIN_POINTS_PER_PUZZLE
from sqlalchemy.ext.asyncio import AsyncSession

ACCURACY_QUALIFY_MIN_PUZZLES: Final = 20
LEADERBOARD_TOP_N: Final = 5
LEADERBOARD_NEIGHBOURS: Final = 2
DAYS_PER_WEEK: Final = 7
PERCENT_SCALE: Final = 100
ANONYMOUS_DISPLAY_NAME: Final = "Anonymous"
# Must stay equal to the literal in migration e3a8c5f17b20's erase-name trigger (pinned by tests).
DELETED_USER_DISPLAY_NAME: Final = "Deleted user"
# Olympic rule (D-02/D-06): the competition rank that earns each medal.
MEDAL_BY_RANK: Final[Mapping[int, Medal]] = MappingProxyType(
    {1: Medal.GOLD, 2: Medal.SILVER, 3: Medal.BRONZE}
)
MEDAL_KIND: Final[Mapping[Medal, MedalKind]] = MappingProxyType(
    {Medal.GOLD: "gold", Medal.SILVER: "silver", Medal.BRONZE: "bronze"}
)


@dataclass(frozen=True)
class MedalTally:
    """Lifetime medal counts shown on a board row. Counts only, never an id."""

    gold: int
    silver: int
    bronze: int


ZERO_TALLY: Final = MedalTally(gold=0, silver=0, bronze=0)


@dataclass(frozen=True)
class BoardRow:
    rank: int | None  # None marks a tentative Accuracy entry (unranked)
    name: str
    value: int
    puzzles: int
    tentative: bool
    is_viewer: bool
    visibility: LeaderboardVisibility
    gap_before: bool
    gap_after: bool
    medals: MedalTally


@dataclass(frozen=True)
class ViewerStanding:
    rank: int | None  # None while the viewer is a tentative Accuracy entry
    rank_without_session: int | None
    tentative: bool
    puzzles_to_qualify: int
    visibility: LeaderboardVisibility


@dataclass(frozen=True)
class PassTarget:
    name: str
    points_needed: int


@dataclass(frozen=True)
class PodiumEntry:
    medal: MedalKind
    name: str  # read-time masked, see _podium_name
    is_viewer: bool  # True only on the viewer's own entry


@dataclass(frozen=True)
class LastWeek:
    """The immediately previous week on one board (D-07): podium plus the viewer's own rank."""

    week_start: datetime.date
    podium: tuple[PodiumEntry, ...]
    viewer_final_rank: int | None  # only for a viewer row that carries no medal (D-03)


@dataclass(frozen=True)
class Board:
    rows: tuple[BoardRow, ...]
    viewer: ViewerStanding | None
    pass_target: PassTarget | None
    last_week: LastWeek | None = None


@dataclass(frozen=True)
class FinalStanding:
    """One snapshot row before persistence. `user_id` is persisted, never serialized."""

    user_id: int
    display_name: str
    final_rank: int
    value: int
    puzzles: int
    medal: Medal | None


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


def _tentative_order_key(entry: _Entry) -> tuple[int, int, str, int]:
    """Tentative entries are ordered by activity first: puzzles desc, then value desc."""
    return (-entry.puzzles, -entry.value, entry.name.casefold(), entry.key)


def _competition_ranks(ordered: Sequence[_Entry]) -> list[int]:
    """Competition ranks over an already ordered list: equal values share a rank."""
    ranks: list[int] = []
    for index, entry in enumerate(ordered):
        if index > 0 and entry.value == ordered[index - 1].value:
            ranks.append(ranks[index - 1])
        else:
            ranks.append(index + 1)
    return ranks


def _tiered_order(combined: Sequence[_Entry]) -> tuple[list[_Entry], list[int | None]]:
    """Qualified entries first (ranked), then tentative entries (rank None).

    Fix (quick 261004-8rt): tentative entries used to be ranked and interleaved with
    qualified ones by raw percentage, so a single 1/1 solve at 100% sat at #1 above every
    qualified player (prod 2026-10-04, top 5 rows all 100% on 1 puzzle). Qualified
    entries now rank first; tentative ones follow unranked.
    """
    qualified = sorted((e for e in combined if not e.tentative), key=_order_key)
    tentative = sorted((e for e in combined if e.tentative), key=_tentative_order_key)
    ranks: list[int | None] = [*_competition_ranks(qualified), *([None] * len(tentative))]
    return [*qualified, *tentative], ranks


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
    against (public, qualified and not the viewer), never the combined list, which
    holds the viewer's full entry. None when the viewer is tentative without the
    session, so the client never computes a delta across the qualification cutoff.
    Points can only worsen without a session; Accuracy can improve, and the value is
    returned as computed, never clamped to the real rank (D-18: the "(up N)" copy rule
    is the client's).
    """
    remaining = totals_without(viewer_aggregate.totals, contribution)
    if kind == "points" and remaining.puzzles == 0:
        return None
    viewer_entry = _entry_for(kind, replace(viewer_aggregate, totals=remaining))
    if viewer_entry is None or viewer_entry.tentative:
        return None
    others = (
        e for e in entries if e.is_public and not e.tentative and e.key != viewer_aggregate.user_id
    )
    return 1 + sum(1 for other in others if other.value > viewer_entry.value)


def medal_for(rank: int, value: int) -> Medal | None:
    """Olympic medal for a competition rank (D-02/D-06); none for a zero value (D-05).

    Deliberate refinement of "no participation floor": one point is enough, but a
    0-point or 0% entry keeps its rank and earns no medal.
    """
    if value <= 0:
        return None
    return MEDAL_BY_RANK.get(rank)


def final_standings(
    kind: LeaderboardBoardKind, aggregates: Sequence[WeeklyAggregate]
) -> list[FinalStanding]:
    """The public final standings of one closed week on one board (D-01, D-02).

    Equals the board every public viewer saw at the deadline: `build_board` ranks
    `combined = public entries (+ the viewer)`, which for a public viewer is exactly
    the public list built here by the same `_entry_for` and `_tiered_order`. Tentative
    Accuracy entries come back with rank None and get no row.
    """
    public = [e for e in (_entry_for(kind, a) for a in aggregates) if e is not None and e.is_public]
    ordered, ranks = _tiered_order(public)
    return [
        FinalStanding(
            user_id=entry.key,
            display_name=entry.name,
            final_rank=rank,
            value=entry.value,
            puzzles=entry.puzzles,
            medal=medal_for(rank, entry.value),
        )
        for entry, rank in zip(ordered, ranks, strict=True)
        if rank is not None
    ]


def _podium_order_key(row: StandingRow) -> tuple[int, int, str]:
    """Gold first, then the live board's tie order: puzzles desc, then name."""
    assert row.medal is not None  # callers pass medal rows only
    return (int(row.medal), -row.puzzles, row.display_name.casefold())


def _podium_name(row: StandingRow, viewer_id: int) -> str:
    """The name others may see for a stored row, decided at read time (D-04, D-09).

    Eligibility was decided at finalization; masking is only about who looks now.
    "Deleted user" for an erased account, "Anonymous" for a user hidden now unless the
    viewer is that user (their own data is never masked to themselves).
    """
    if row.user_id is None:
        return DELETED_USER_DISPLAY_NAME
    if row.leaderboard_hidden and row.user_id != viewer_id:
        return ANONYMOUS_DISPLAY_NAME
    return row.display_name


def build_last_week(
    kind: LeaderboardBoardKind,
    rows: Sequence[StandingRow],
    *,
    viewer_id: int,
    week_start: datetime.date,
) -> LastWeek | None:
    """The previous week's podium and the viewer's own non-medal rank on one board.

    None when there is nothing to show (D-08): no medal awarded and no non-medal
    viewer row. Every tied name is listed (D-06/D-09).
    """
    board_rows = [r for r in rows if r.board == kind]
    medal_rows = sorted((r for r in board_rows if r.medal is not None), key=_podium_order_key)
    podium = tuple(
        PodiumEntry(
            medal=MEDAL_KIND[r.medal],
            name=_podium_name(r, viewer_id),
            # A deleted user's row has user_id None, which never equals an int viewer_id.
            is_viewer=r.user_id == viewer_id,
        )
        for r in medal_rows
        if r.medal is not None  # narrowing for the type checker; medal_rows are medal rows
    )
    viewer_final_rank = next(
        (r.final_rank for r in board_rows if r.user_id == viewer_id and r.medal is None), None
    )
    if not podium and viewer_final_rank is None:
        return None
    return LastWeek(week_start=week_start, podium=podium, viewer_final_rank=viewer_final_rank)


@dataclass(frozen=True)
class _RankedBoard:
    """The shared ranking and slicing of one board for one viewer. Private: carries keys."""

    entries: list[_Entry]
    ordered: list[_Entry]
    ranks: list[int | None]
    viewer_index: int | None
    indices: list[int]
    gap_index: int | None


def _rank_board(
    kind: LeaderboardBoardKind, aggregates: Sequence[WeeklyAggregate], *, viewer_id: int
) -> _RankedBoard:
    """Rank one board and pick the rows to show; the one implementation `build_board` and
    `visible_keys` share, so the tally lookup can never drift from the rows displayed."""
    entries = [e for e in (_entry_for(kind, a) for a in aggregates) if e is not None]
    combined = [e for e in entries if e.is_public or e.key == viewer_id]
    ordered, ranks = _tiered_order(combined)
    viewer_index = next((i for i, e in enumerate(ordered) if e.key == viewer_id), None)
    indices, gap_index = _slice_indices(len(ordered), viewer_index)
    return _RankedBoard(entries, ordered, ranks, viewer_index, indices, gap_index)


def visible_keys(
    kind: LeaderboardBoardKind, aggregates: Sequence[WeeklyAggregate], *, viewer_id: int
) -> list[int]:
    """User ids behind the rows `build_board` shows for the same inputs (internal use only).

    Used to scope the one grouped tally COUNT to rows already visible to this viewer
    (T-231-12). The ids never leave the service layer.
    """
    ranked = _rank_board(kind, aggregates, viewer_id=viewer_id)
    return [ranked.ordered[i].key for i in ranked.indices]


def fold_medal_tallies(
    rows: Sequence[TallyCount],
) -> dict[LeaderboardBoardKind, dict[int, MedalTally]]:
    """Per-board, per-user lifetime tallies from grouped (board, user, medal, count) rows."""
    counts: dict[LeaderboardBoardKind, dict[int, dict[Medal, int]]] = {"points": {}, "accuracy": {}}
    for row in rows:
        per_user = counts[row.board].setdefault(row.user_id, {})
        per_user[row.medal] = per_user.get(row.medal, 0) + row.count
    return {
        board: {
            user_id: MedalTally(
                gold=by_medal.get(Medal.GOLD, 0),
                silver=by_medal.get(Medal.SILVER, 0),
                bronze=by_medal.get(Medal.BRONZE, 0),
            )
            for user_id, by_medal in per_user.items()
        }
        for board, per_user in counts.items()
    }


def build_board(
    kind: LeaderboardBoardKind,
    aggregates: Sequence[WeeklyAggregate],
    *,
    viewer_id: int,
    viewer_visibility: LeaderboardVisibility,
    session_contribution: SolveTotals | None = None,
    medal_tallies: Mapping[int, MedalTally] | None = None,
    last_week: LastWeek | None = None,
) -> Board:
    """Rank one board for one viewer.

    Others are only registered, non-hidden users, filtered before ranking so a hidden
    user or guest can surface in no row, rank or pass target (D-06/D-13/D-14). The
    viewer's own entry (any visibility) joins them to form the combined list.

    `medal_tallies` is keyed by the internal user key, read here to fill each row's
    `medals` and never copied onto the row itself.
    """
    tallies = medal_tallies or {}
    ranked = _rank_board(kind, aggregates, viewer_id=viewer_id)
    entries, ordered, ranks = ranked.entries, ranked.ordered, ranked.ranks
    viewer_index, indices, gap_index = ranked.viewer_index, ranked.indices, ranked.gap_index
    # Ranks below the last shown row are cut: without a trailing marker a top-ranked
    # viewer saw only top N plus neighbours and read it as the whole field.
    trailing_gap_index = indices[-1] if indices and indices[-1] < len(ordered) - 1 else None
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
            gap_after=i == trailing_gap_index,
            medals=tallies.get(ordered[i].key, ZERO_TALLY),
        )
        for i in indices
    )
    viewer: ViewerStanding | None = None
    if viewer_index is not None:
        viewer_entry = ordered[viewer_index]
        viewer_aggregate = next((a for a in aggregates if a.user_id == viewer_id), None)
        without = (
            _rank_without(kind, entries, viewer_aggregate, session_contribution)
            if session_contribution is not None
            and viewer_aggregate is not None
            and ranks[viewer_index] is not None
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
    return Board(
        rows=rows,
        viewer=viewer,
        pass_target=_pass_target(kind, ordered, viewer_index),
        last_week=last_week,
    )


def build_leaderboard(
    aggregates: Sequence[WeeklyAggregate],
    *,
    viewer_id: int,
    viewer_visibility: LeaderboardVisibility,
    week_start: datetime.datetime,
    week_end: datetime.datetime,
    now_utc: datetime.datetime,
    session_contribution: SolveTotals | None = None,
    medal_tallies: Mapping[LeaderboardBoardKind, Mapping[int, MedalTally]] | None = None,
    last_week: Mapping[LeaderboardBoardKind, LastWeek | None] | None = None,
) -> WeeklyLeaderboard:
    tallies = medal_tallies or {}
    last = last_week or {}
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
            medal_tallies=tallies.get("points"),
            last_week=last.get("points"),
        ),
        accuracy=build_board(
            "accuracy",
            aggregates,
            viewer_id=viewer_id,
            viewer_visibility=viewer_visibility,
            session_contribution=session_contribution,
            medal_tallies=tallies.get("accuracy"),
            last_week=last.get("accuracy"),
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
    # One grouped COUNT for the user ids behind every visible row of both boards
    # (Locked tally). Skipped when no row is visible. The ids stay in this service.
    visible_ids = {
        user_id
        for kind in ("points", "accuracy")
        for user_id in visible_keys(kind, aggregates, viewer_id=viewer_id)
    }
    tally_rows = (
        await fetch_medal_tallies(session, user_ids=sorted(visible_ids)) if visible_ids else []
    )
    # D-07: only the immediately previous ISO week. Before the first deadline (and
    # during the finalize grace window) no rows exist, so both blocks come back None.
    previous_week = (week_start - datetime.timedelta(days=DAYS_PER_WEEK)).date()
    standing_rows = await fetch_last_week_rows(
        session, week_start=previous_week, viewer_id=viewer_id
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
        medal_tallies=fold_medal_tallies(tally_rows),
        last_week={
            kind: build_last_week(
                kind, standing_rows, viewer_id=viewer_id, week_start=previous_week
            )
            for kind in ("points", "accuracy")
        },
    )
