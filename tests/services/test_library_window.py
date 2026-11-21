"""Decision tests for the Library Stats recent window (258).

The window is the newest RECENT_GAMES_PER_TC_CAP games per time control within
RECENCY_WINDOW_MONTHS of now_utc (or within the selected period). These tests pin the decisions
before the facepalm and tactic endpoints reuse the window:

- test_months_before_*          : calendar-month subtraction with clamping, tzinfo kept
- test_summarize_window_*       : per-TC counts, oldest date, cap flag, id sets
- test_cap_per_tc               : D-03 per-TC cap and cap_reached
- test_real_cap                 : D-03 at the real 1000 games
- test_bound_36_months          : the 36-month bound on a fixed now_utc
- test_recency_from_date        : D-04 an explicit date replaces the bound, the cap stays
- test_cap_counts_unanalyzed    : D-05 unanalyzed games take cap slots
- test_filter_first_color       : D-11 filters (colour) apply before the cap
- test_tiebreak_equal_played_at : the game id breaks played_at ties deterministically
- test_excluded_rows            : NULL played_at / ply_count 0 / NULL / NULL TC never appear
- test_two_user_isolation       : another user's games never enter the window
- test_window_counts            : D-06 windowed analyzed_n / total_n equal the window summary
- test_gate_on_window           : D-10 the flaw gate reads the windowed analyzed count
- test_quiet_tc                 : D-15 a TC with no window game stays on the switch

The db_session fixture rolls back every test, so no committed game leaks into the eval lotteries.
"""

import datetime
import uuid
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.repositories.library_repository import RecentWindowRow, fetch_recent_window_rows
from app.services.canonical_slice_sql import RECENT_GAMES_PER_TC_CAP, RECENCY_WINDOW_MONTHS
from app.services.library_service import (
    FLAW_COMPARISON_GATE,
    get_flaw_comparison,
    months_before,
    recent_window_start,
    summarize_window,
)
from tests.conftest import ensure_test_user

_NOW = datetime.datetime(2026, 11, 21, 12, 0, tzinfo=datetime.timezone.utc)
_UTC = datetime.timezone.utc

# User ids reserved for this module (free at planning time).
_USER = 88250
_OTHER_USER = 88251

_SEVERITY_BLUNDER = 2

_FILTERS: dict[str, Any] = dict(
    time_control=None,
    platform=None,
    rated=None,
    opponent_type="all",
    from_date=None,
    to_date=None,
    flaw_severity=None,
    opponent_gap_min=None,
    opponent_gap_max=None,
    color=None,
)


@pytest_asyncio.fixture(autouse=True)
async def _create_users(db_session: AsyncSession) -> None:
    await ensure_test_user(db_session, _USER)
    await ensure_test_user(db_session, _OTHER_USER)


def _make_game(
    *,
    user_id: int = _USER,
    played_at: datetime.datetime | None,
    time_control_bucket: str | None = "blitz",
    user_color: str = "white",
    ply_count: int | None = 40,
    analyzed: bool = False,
    blobs_done: bool = False,
) -> Game:
    return Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
        ply_count=ply_count,
        played_at=played_at,
        white_blunders=0 if analyzed else None,
        full_evals_completed_at=_NOW if analyzed else None,
        blobs_completed_at=_NOW if blobs_done else None,
    )


async def _seed(session: AsyncSession, **kwargs: Any) -> Game:
    game = _make_game(**kwargs)
    session.add(game)
    await session.flush()
    return game


async def _seed_flaw(session: AsyncSession, game: Game, *, severity: int) -> None:
    from app.repositories.game_flaws_repository import bulk_insert_game_flaws

    await bulk_insert_game_flaws(
        session,
        [
            {
                "user_id": game.user_id,
                "game_id": game.id,
                "ply": 2,
                "severity": severity,
                "tempo": None,
                "phase": 1,
                "is_miss": False,
                "is_lucky": False,
                "is_reversed": False,
                "is_squandered": False,
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            }
        ],
    )


def _filters(**overrides: Any) -> dict[str, Any]:
    return {**_FILTERS, **overrides}


def _days_ago(days: int, *, minutes: int = 0) -> datetime.datetime:
    return _NOW - datetime.timedelta(days=days, minutes=minutes)


async def _window(
    session: AsyncSession,
    *,
    user_id: int = _USER,
    cap: int = RECENT_GAMES_PER_TC_CAP,
    window_start: datetime.datetime | None = None,
    **overrides: Any,
) -> list[RecentWindowRow]:
    """fetch_recent_window_rows with the 36-month bound unless a test replaces it."""
    filters = _filters(**overrides)
    if window_start is None and filters["from_date"] is None and filters["to_date"] is None:
        window_start = recent_window_start(_NOW, None, None)
    return await fetch_recent_window_rows(
        session, user_id, window_start=window_start, cap=cap, **filters
    )


def _ids_by_tc(rows: list[RecentWindowRow], tc: str) -> set[int]:
    return {r.game_id for r in rows if r.tc == tc}


# ---------------------------------------------------------------------------
# months_before / recent_window_start (pure)
# ---------------------------------------------------------------------------


def test_months_before_clamps_feb_29() -> None:
    moment = datetime.datetime(2028, 2, 29, 10, 0, tzinfo=_UTC)
    assert months_before(moment, 36) == datetime.datetime(2025, 2, 28, 10, 0, tzinfo=_UTC)


def test_months_before_plain_and_tzinfo_kept() -> None:
    moment = datetime.datetime(2026, 3, 31, 9, 30, tzinfo=_UTC)
    result = months_before(moment, 36)
    assert result == datetime.datetime(2023, 3, 31, 9, 30, tzinfo=_UTC)
    assert result.tzinfo is _UTC


def test_months_before_crosses_year_boundary() -> None:
    moment = datetime.datetime(2026, 1, 31, tzinfo=_UTC)
    assert months_before(moment, 2) == datetime.datetime(2025, 11, 30, tzinfo=_UTC)


def test_recent_window_start_none_for_any_explicit_bound() -> None:
    today = _NOW.date()
    assert recent_window_start(_NOW, None, None) == months_before(_NOW, RECENCY_WINDOW_MONTHS)
    assert recent_window_start(_NOW, today, None) is None
    assert recent_window_start(_NOW, None, today) is None
    assert recent_window_start(_NOW, today, today) is None


# ---------------------------------------------------------------------------
# summarize_window (pure)
# ---------------------------------------------------------------------------


def _row(
    game_id: int,
    tc: str,
    played_at: datetime.datetime,
    *,
    analyzed: bool = False,
    tactic_ready: bool = False,
) -> RecentWindowRow:
    return RecentWindowRow(
        game_id=game_id,
        tc=tc,  # ty: ignore[invalid-argument-type]  # plain str stands in for the TC Literal
        played_at=played_at,
        analyzed=analyzed,
        tactic_ready=tactic_ready,
    )


def test_summarize_window_counts_and_ids() -> None:
    rows = [
        _row(1, "blitz", _days_ago(1), analyzed=True, tactic_ready=True),
        _row(2, "blitz", _days_ago(30), analyzed=True),
        _row(3, "blitz", _days_ago(60)),
        _row(4, "rapid", _days_ago(2)),
    ]
    summary = summarize_window(rows, cap=1000)
    blitz, rapid = summary["blitz"], summary["rapid"]
    assert (blitz.total_n, blitz.analyzed_n, blitz.tactic_analyzed_n) == (3, 2, 1)
    assert blitz.analyzed_ids == (1, 2)
    assert blitz.tactic_ids == (1,)
    assert blitz.sample_since == _days_ago(60).date()
    assert (rapid.total_n, rapid.analyzed_n, rapid.tactic_analyzed_n) == (1, 0, 0)
    assert rapid.analyzed_ids == () and rapid.tactic_ids == ()


def test_summarize_window_cap_reached_exactly_at_cap() -> None:
    rows = [_row(i, "blitz", _days_ago(i)) for i in range(3)]
    assert summarize_window(rows, cap=3)["blitz"].cap_reached is True
    assert summarize_window(rows, cap=4)["blitz"].cap_reached is False


def test_summarize_window_empty() -> None:
    assert summarize_window([], cap=1000) == {}


# ---------------------------------------------------------------------------
# fetch_recent_window_rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cap_per_tc(db_session: AsyncSession) -> None:
    """D-03: 5 blitz + 2 rapid with cap 3 gives the 3 newest blitz and both rapid."""
    blitz = [await _seed(db_session, played_at=_days_ago(i + 1)) for i in range(5)]
    rapid = [
        await _seed(db_session, played_at=_days_ago(i + 1), time_control_bucket="rapid")
        for i in range(2)
    ]
    rows = await _window(db_session, cap=3)
    assert _ids_by_tc(rows, "blitz") == {g.id for g in blitz[:3]}
    assert _ids_by_tc(rows, "rapid") == {g.id for g in rapid}
    summary = summarize_window(rows, cap=3)
    assert summary["blitz"].cap_reached is True
    assert summary["rapid"].cap_reached is False


@pytest.mark.asyncio
async def test_real_cap(db_session: AsyncSession) -> None:
    """D-03 at the real 1000: 1001 blitz games give 1000 rows and the oldest is outside."""
    games = [
        _make_game(played_at=_NOW - datetime.timedelta(minutes=i + 1))
        for i in range(RECENT_GAMES_PER_TC_CAP + 1)
    ]
    db_session.add_all(games)
    await db_session.flush()
    rows = await _window(db_session)
    assert len(rows) == RECENT_GAMES_PER_TC_CAP
    assert games[-1].id not in {r.game_id for r in rows}
    assert summarize_window(rows, RECENT_GAMES_PER_TC_CAP)["blitz"].cap_reached is True


@pytest.mark.asyncio
async def test_bound_36_months(db_session: AsyncSession) -> None:
    """A game 35 months old is in the window, one 37 months old is out."""
    inside = await _seed(db_session, played_at=months_before(_NOW, 35))
    await _seed(db_session, played_at=months_before(_NOW, 37))
    rows = await _window(db_session)
    assert {r.game_id for r in rows} == {inside.id}


@pytest.mark.asyncio
async def test_recency_from_date(db_session: AsyncSession) -> None:
    """D-04: an explicit from_date or to_date replaces the bound; the cap stays."""
    old = await _seed(db_session, played_at=months_before(_NOW, 37))
    recent = [await _seed(db_session, played_at=_days_ago(i + 1)) for i in range(3)]
    from_date = months_before(_NOW, 60).date()

    rows = await _window(db_session, from_date=from_date)
    assert {r.game_id for r in rows} == {old.id, *(g.id for g in recent)}

    capped = await _window(db_session, from_date=from_date, cap=3)
    assert {r.game_id for r in capped} == {g.id for g in recent}

    # A to_date alone is an explicit recency filter too (258 research A4).
    to_only = await _window(db_session, to_date=_NOW.date())
    assert old.id in {r.game_id for r in to_only}
    assert recent_window_start(_NOW, None, _NOW.date()) is None

    for analyzed_game in (old, *recent):
        analyzed_game.full_evals_completed_at = _NOW
    await db_session.flush()
    response = await get_flaw_comparison(
        db_session, _USER, now_utc=_NOW, **_filters(from_date=from_date)
    )
    assert response.recency_filtered is True
    default_response = await get_flaw_comparison(db_session, _USER, now_utc=_NOW, **_FILTERS)
    assert default_response.recency_filtered is False


@pytest.mark.asyncio
async def test_cap_counts_unanalyzed(db_session: AsyncSession) -> None:
    """D-05: unanalyzed newest games take the cap slots; older analyzed games are not pulled in."""
    for i in range(3):
        await _seed(db_session, played_at=_days_ago(i + 1), analyzed=False)
    for i in range(2):
        await _seed(db_session, played_at=_days_ago(i + 10), analyzed=True)
    rows = await _window(db_session, cap=3)
    summary = summarize_window(rows, cap=3)["blitz"]
    assert summary.total_n == 3
    assert summary.analyzed_n == 0
    assert summary.analyzed_ids == ()


@pytest.mark.asyncio
async def test_filter_first_color(db_session: AsyncSession) -> None:
    """D-11: the sidebar filters apply before the cap, so colour white gives the 3 newest white."""
    for i in range(3):
        await _seed(db_session, played_at=_days_ago(i + 1), user_color="black")
    white = [
        await _seed(db_session, played_at=_days_ago(i + 10), user_color="white") for i in range(4)
    ]
    rows = await _window(db_session, cap=3, color="white")
    assert {r.game_id for r in rows} == {g.id for g in white[:3]}


@pytest.mark.asyncio
async def test_tiebreak_equal_played_at(db_session: AsyncSession) -> None:
    """Equal played_at at the cap boundary keeps the higher ids, identically on a re-run."""
    moment = _days_ago(5)
    games = [await _seed(db_session, played_at=moment) for _ in range(4)]
    expected = {g.id for g in sorted(games, key=lambda g: g.id, reverse=True)[:2]}
    first = {r.game_id for r in await _window(db_session, cap=2)}
    second = {r.game_id for r in await _window(db_session, cap=2)}
    assert first == expected
    assert second == expected


@pytest.mark.asyncio
async def test_excluded_rows(db_session: AsyncSession) -> None:
    """NULL played_at, ply_count 0 / NULL and a NULL TC never appear, also with cap 1."""
    valid = await _seed(db_session, played_at=_days_ago(30))
    await _seed(db_session, played_at=None)
    await _seed(db_session, played_at=_days_ago(1), ply_count=0)
    await _seed(db_session, played_at=_days_ago(1), ply_count=None)
    await _seed(db_session, played_at=_days_ago(1), time_control_bucket=None)
    for cap in (1, RECENT_GAMES_PER_TC_CAP):
        rows = await _window(db_session, cap=cap)
        assert [r.game_id for r in rows] == [valid.id]
    # No lower bound at all: the NULL played_at game must still never take a slot (PostgreSQL
    # sorts DESC with NULLS FIRST, so it would otherwise rank first).
    unbounded = await fetch_recent_window_rows(
        db_session, _USER, window_start=None, cap=1, **_FILTERS
    )
    assert [r.game_id for r in unbounded] == [valid.id]


@pytest.mark.asyncio
async def test_two_user_isolation(db_session: AsyncSession) -> None:
    """Another user's newer games never enter this user's window."""
    mine = await _seed(db_session, user_id=_USER, played_at=_days_ago(20), analyzed=True)
    for i in range(3):
        await _seed(db_session, user_id=_OTHER_USER, played_at=_days_ago(i + 1), analyzed=True)
    rows = await _window(db_session, cap=3)
    assert [r.game_id for r in rows] == [mine.id]
    other_rows = await _window(db_session, user_id=_OTHER_USER, cap=3)
    assert len(other_rows) == 3 and mine.id not in {r.game_id for r in other_rows}
    response = await get_flaw_comparison(db_session, _USER, now_utc=_NOW, **_FILTERS)
    assert [(t.tc, t.total_n, t.analyzed_n) for t in response.tcs] == [("blitz", 1, 1)]


# ---------------------------------------------------------------------------
# get_flaw_comparison on the window
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_window_counts(db_session: AsyncSession) -> None:
    """D-06: windowed analyzed_n / total_n equal the window summary; old events stay out."""
    for i in range(22):
        await _seed(db_session, played_at=_days_ago(i + 1), analyzed=True)
    await _seed(db_session, played_at=_days_ago(40), analyzed=False)
    old = await _seed(db_session, played_at=months_before(_NOW, 40), analyzed=True)
    await _seed_flaw(db_session, old, severity=_SEVERITY_BLUNDER)

    response = await get_flaw_comparison(db_session, _USER, now_utc=_NOW, **_FILTERS)
    rows = await _window(db_session)
    summary = summarize_window(rows, RECENT_GAMES_PER_TC_CAP)["blitz"]

    (tc_entry,) = response.tcs
    assert tc_entry.analyzed_n == summary.analyzed_n == 22
    assert tc_entry.total_n == summary.total_n == 23
    assert tc_entry.sample_since == summary.sample_since
    assert tc_entry.cap_reached == summary.cap_reached is False
    assert tc_entry.history_analyzed_n == 23
    blunder = next(b for b in tc_entry.bullets if b.tag == "blunder")
    assert blunder.player_events == 0


@pytest.mark.asyncio
async def test_gate_on_window(db_session: AsyncSession) -> None:
    """D-10: 25 analyzed games, 10 older than 36 months: analyzed_n 15, below the gate."""
    for i in range(15):
        await _seed(db_session, played_at=_days_ago(i + 1), analyzed=True)
    for i in range(10):
        await _seed(db_session, played_at=months_before(_NOW, 40 + i), analyzed=True)
    response = await get_flaw_comparison(db_session, _USER, now_utc=_NOW, **_FILTERS)
    (tc_entry,) = response.tcs
    assert tc_entry.analyzed_n == 15
    assert tc_entry.history_analyzed_n == 25
    assert 15 < FLAW_COMPARISON_GATE
    assert tc_entry.below_gate is True


@pytest.mark.asyncio
async def test_quiet_tc(db_session: AsyncSession) -> None:
    """D-15: a TC whose analyzed games are all old stays in tcs with zero window numbers."""
    await _seed(db_session, played_at=_days_ago(2), analyzed=True)
    old_rapid = [
        await _seed(
            db_session,
            played_at=months_before(_NOW, 48 + i),
            analyzed=True,
            time_control_bucket="rapid",
        )
        for i in range(3)
    ]
    response = await get_flaw_comparison(db_session, _USER, now_utc=_NOW, **_FILTERS)
    by_tc = {t.tc: t for t in response.tcs}
    quiet = by_tc["rapid"]
    assert (quiet.total_n, quiet.analyzed_n) == (0, 0)
    assert quiet.sample_since is None
    assert quiet.cap_reached is False
    assert quiet.history_analyzed_n == len(old_rapid)
    assert by_tc["blitz"].total_n == 1

    # With a selected period reaching back five years the same TC is no longer quiet.
    from_date = months_before(_NOW, 60).date()
    wide = await get_flaw_comparison(
        db_session, _USER, now_utc=_NOW, **_filters(from_date=from_date)
    )
    wide_rapid = next(t for t in wide.tcs if t.tc == "rapid")
    assert wide_rapid.total_n == len(old_rapid)
    assert wide_rapid.analyzed_n == len(old_rapid)
