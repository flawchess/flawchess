"""Router tests for the weekly medal snapshot on GET /api/train/leaderboard (Phase 231).

Cases:
- test_deadline_finalizes_last_week_and_shows_the_podium: tracer, the first request
  after a deadline freezes last week's public boards and returns the podium
- test_podium_masks_hidden_now_and_deleted_users: read-time "Anonymous" for a user
  hidden now (not to themself), trigger erasure + "Deleted user" after account deletion
- test_finalization_waits_for_the_grace_window: nothing finalizes before deadline + 5 min
- test_last_week_is_only_the_immediately_previous_week: no fallback to an older week
- test_finalization_failure_still_serves_the_board: finalizer error -> 200 + Sentry
- test_unclaimed_then_claim_round_trip: tracer for GET /medals/unclaimed + POST /medals/claim
- test_unclaimed_order_newest_week_first_points_before_accuracy: D-11 ordering
- test_claim_is_scoped_to_the_caller_and_idempotent: IDOR, replay, D-04 hidden, D-10 guest
- test_claim_validation_rejects_bad_bodies: 422 before any SQL, 401 without a token
- test_medal_tally_counts_lifetime_medals_per_board: lifetime tally on live rows, opt-out round trip

Isolation rule: snapshot data is global and permanent, and router tests commit. Every
test owns ISO weeks from Monday 2033-01-03 plus k (a week is never shared), monkeypatches
`app.services.train_medals.MEDALS_START_WEEK` to its first owned week so finalization
touches only its own weeks, deletes its owned weeks from `train_weekly_finalizations`
before seeding and in `finally` (the FK cascades their standings rows), and deletes the
users it registered in `finally`. A k is never reused. A test owns both its finalized
week and the week its request is pinned in.

k table (this plan holds k 0-19, Plan 02 holds k 20-49):
- k=0  test_deadline_finalizes_last_week_and_shows_the_podium (finalized week)
- k=1  test_deadline_finalizes_last_week_and_shows_the_podium (request week)
- k=2  test_podium_masks_hidden_now_and_deleted_users (finalized week)
- k=3  test_podium_masks_hidden_now_and_deleted_users (request week)
- k=4  test_finalization_waits_for_the_grace_window (finalized week)
- k=5  test_finalization_waits_for_the_grace_window (request week)
- k=6  test_last_week_is_only_the_immediately_previous_week (finalized week with data)
- k=7  test_last_week_is_only_the_immediately_previous_week (finalized empty week)
- k=8  test_last_week_is_only_the_immediately_previous_week (request week)
- k=9  unused
- k=10 test_finalization_failure_still_serves_the_board (would-be finalized week)
- k=11 test_finalization_failure_still_serves_the_board (request week)
- k=12-19 reserved for this plan's later additions
- k=20 test_unclaimed_then_claim_round_trip (finalized week)
- k=21 test_unclaimed_then_claim_round_trip (request week)
- k=22 test_unclaimed_order_newest_week_first_points_before_accuracy (finalized week)
- k=23 test_unclaimed_order_newest_week_first_points_before_accuracy (finalized week)
- k=24 test_unclaimed_order_newest_week_first_points_before_accuracy (request week)
- k=25 test_claim_is_scoped_to_the_caller_and_idempotent (finalized week)
- k=26 test_claim_is_scoped_to_the_caller_and_idempotent (request week)
- k=27 test_claim_validation_rejects_bad_bodies (pinned week, no data)
- k=28, 29 unused
- k=30 test_medal_tally_counts_lifetime_medals_per_board (finalized week)
- k=31 test_medal_tally_counts_lifetime_medals_per_board (finalized week)
- k=32 test_medal_tally_counts_lifetime_medals_per_board (request week)
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable, Iterator, Sequence
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.train_weekly_standing import TrainWeeklyFinalization, TrainWeeklyStanding
from app.models.user import User
from app.routers import train as train_router
from app.services import train_medals

ENDPOINT = "/api/train/leaderboard"
UNCLAIMED_ENDPOINT = "/api/train/medals/unclaimed"
CLAIM_ENDPOINT = "/api/train/medals/claim"

# Monday of the k=0 week; every test adds its own k weeks.
BASE_MONDAY = datetime.datetime(2033, 1, 3, tzinfo=datetime.UTC)

Outcome = tuple[bool, DrillMoveQuality, DrillSource]

_GOOD_SR: Outcome = (True, DrillMoveQuality.GOOD, DrillSource.SR_ITEM)


def _week_monday(k: int) -> datetime.datetime:
    return BASE_MONDAY + datetime.timedelta(weeks=k)


def _wednesday_noon(k: int) -> datetime.datetime:
    return _week_monday(k) + datetime.timedelta(days=2, hours=12)


@pytest.fixture
def pin_now() -> Iterator[Callable[[datetime.datetime], None]]:
    """Pin dev_now_utc for the test; the override is removed on teardown."""

    def _pin(now: datetime.datetime) -> None:
        app.dependency_overrides[dev_now_utc] = lambda: now

    yield _pin
    app.dependency_overrides.pop(dev_now_utc, None)


async def _register_and_login(email: str, password: str = "testpass123!") -> tuple[int, str]:
    """Register a user via HTTP and return (user_id, auth_token)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post("/api/auth/register", json={"email": email, "password": password})
        assert reg.status_code in (200, 201), f"register failed: {reg.text}"
        user_id = int(reg.json()["id"])
        login = await client.post(
            "/api/auth/jwt/login", data={"username": email, "password": password}
        )
        assert login.status_code == 200, f"login failed: {login.text}"
        token = str(login.json()["access_token"])
    return user_id, token


async def _set_user_fields(test_engine: Any, user_id: int, **values: Any) -> None:
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            await session.execute(update(User).where(User.id == user_id).values(**values))


async def _seed_solves(
    test_engine: Any,
    user_id: int,
    solved_at: datetime.datetime,
    outcomes: Sequence[Outcome],
) -> int:
    """Insert one completed session with one solved row per outcome; return its id."""
    day = solved_at.astimezone(datetime.UTC).date()
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            drill_session = DrillSession(
                user_id=user_id,
                session_date=day,
                status="completed",
                puzzle_count=len(outcomes),
                expires_on=day + datetime.timedelta(days=1),
            )
            session.add(drill_session)
            await session.flush()
            for position, (correct_guess, quality, source) in enumerate(outcomes):
                session.add(
                    DrillSolve(
                        session_id=drill_session.id,
                        position=position,
                        user_id=user_id,
                        game_id=None,
                        ply=0,
                        source=int(source),
                        sharp_puzzle_id=None,
                        correct_guess=correct_guess,
                        correct_move=quality != DrillMoveQuality.WRONG,
                        move_quality=int(quality),
                        solved_at=solved_at,
                    )
                )
            return drill_session.id


async def _delete_users(test_engine: Any, user_ids: Sequence[int]) -> None:
    """Delete registered users; their sessions and solves cascade."""
    if not user_ids:
        return
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            await session.execute(delete(User).where(User.id.in_(list(user_ids))))


async def _clear_weeks(test_engine: Any, mondays: Sequence[datetime.date]) -> None:
    """Delete the weeks' markers; the FK cascades their standings rows."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            await session.execute(
                delete(TrainWeeklyFinalization).where(
                    TrainWeeklyFinalization.week_start.in_(list(mondays))
                )
            )


async def _get_leaderboard(token: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(ENDPOINT, headers={"Authorization": f"Bearer {token}"})


async def _get_unclaimed(token: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(UNCLAIMED_ENDPOINT, headers={"Authorization": f"Bearer {token}"})


async def _post_claim(token: str, medals: list[dict[str, str]]) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(
            CLAIM_ENDPOINT, json={"medals": medals}, headers={"Authorization": f"Bearer {token}"}
        )


def _assert_no_ids(node: Any) -> None:
    """Recursively assert that no response key is a user id, row id or email."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in {"user_id", "id", "email"}, key
            _assert_no_ids(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_ids(item)


async def _standings(
    test_engine: Any, week: datetime.date, board: str
) -> list[tuple[int | None, str, int, int | None]]:
    """(user_id, display_name, final_rank, medal) of one week and board, by rank then name."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(
            select(
                TrainWeeklyStanding.user_id,
                TrainWeeklyStanding.display_name,
                TrainWeeklyStanding.final_rank,
                TrainWeeklyStanding.medal,
            )
            .where(TrainWeeklyStanding.week_start == week, TrainWeeklyStanding.board == board)
            .order_by(TrainWeeklyStanding.final_rank, TrainWeeklyStanding.display_name)
        )
        return [(r[0], r[1], r[2], r[3]) for r in result.all()]


async def _marker_count(test_engine: Any, week: datetime.date) -> int:
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(
            select(func.count()).where(TrainWeeklyFinalization.week_start == week)
        )
        return int(result.scalar_one())


@pytest.mark.asyncio
async def test_deadline_finalizes_last_week_and_shows_the_podium(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracer (k=0 finalized, k=1 request): the first GET after a deadline freezes the week."""
    week0 = _week_monday(0).date()
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", week0)
    pin_now(_wednesday_noon(1))
    solved_at = _week_monday(0) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    await _clear_weeks(test_engine, [week0])
    try:
        a_id, _ = await _register_and_login(f"md-a-{tag}@example.com")
        b_id, _ = await _register_and_login(f"md-b-{tag}@example.com")
        c_id, _ = await _register_and_login(f"md-c-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"md-v-{tag}@example.com")
        g_id, g_token = await _register_and_login(f"md-g-{tag}@example.com")
        h_id, _ = await _register_and_login(f"md-h-{tag}@example.com")
        user_ids = [a_id, b_id, c_id, v_id, g_id, h_id]
        a_name = f"md_alpha_{tag}"
        b_name = f"md_bravo_{tag}"
        c_name = f"md_charlie_{tag}"
        await _set_user_fields(test_engine, a_id, lichess_username=a_name)
        await _set_user_fields(test_engine, b_id, lichess_username=b_name)
        await _set_user_fields(test_engine, c_id, lichess_username=c_name)
        await _set_user_fields(test_engine, v_id, lichess_username=f"md_victor_{tag}")
        await _set_user_fields(test_engine, g_id, is_guest=True, lichess_username=f"md_guest_{tag}")
        await _set_user_fields(
            test_engine, h_id, leaderboard_hidden=True, lichess_username=f"md_hidden_{tag}"
        )
        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 20)
        await _seed_solves(test_engine, b_id, solved_at, [_GOOD_SR] * 3)
        await _seed_solves(test_engine, c_id, solved_at, [_GOOD_SR] * 3)
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR])
        await _seed_solves(test_engine, g_id, solved_at, [_GOOD_SR] * 30)
        await _seed_solves(test_engine, h_id, solved_at, [_GOOD_SR] * 30)

        resp = await _get_leaderboard(v_token)

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["points"]["last_week"] == {
            "week_start": week0.isoformat(),
            "podium": [
                {"medal": "gold", "name": a_name, "is_viewer": False},
                {"medal": "silver", "name": b_name, "is_viewer": False},
                {"medal": "silver", "name": c_name, "is_viewer": False},
            ],
            "viewer_final_rank": 4,
        }
        # B, C and V are tentative on Accuracy (under 20 puzzles): no row, so no line.
        assert body["accuracy"]["last_week"] == {
            "week_start": week0.isoformat(),
            "podium": [{"medal": "gold", "name": a_name, "is_viewer": False}],
            "viewer_final_rank": None,
        }
        podium_names = {
            e["name"] for b in ("points", "accuracy") for e in body[b]["last_week"]["podium"]
        }
        assert f"md_guest_{tag}" not in podium_names
        assert f"md_hidden_{tag}" not in podium_names

        points_rows = await _standings(test_engine, week0, "points")
        assert points_rows == [
            (a_id, a_name, 1, 1),
            (b_id, b_name, 2, 2),
            (c_id, c_name, 2, 2),
            (v_id, f"md_victor_{tag}", 4, None),
        ]
        assert await _standings(test_engine, week0, "accuracy") == [(a_id, a_name, 1, 1)]
        assert await _marker_count(test_engine, week0) == 1

        # A repeat request writes nothing more.
        again = await _get_leaderboard(v_token)
        assert again.status_code == 200
        assert len(await _standings(test_engine, week0, "points")) == 4
        assert len(await _standings(test_engine, week0, "accuracy")) == 1
        assert await _marker_count(test_engine, week0) == 1

        # Guests see the same podium (public data) and never get a "finished" rank.
        guest = (await _get_leaderboard(g_token)).json()
        assert guest["points"]["last_week"]["podium"] == body["points"]["last_week"]["podium"]
        assert guest["points"]["last_week"]["viewer_final_rank"] is None
    finally:
        await _clear_weeks(test_engine, [week0])
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_podium_masks_hidden_now_and_deleted_users(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Masking (k=2 finalized, k=3 request): "Anonymous" for hidden-now, erased on deletion."""
    week2 = _week_monday(2).date()
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", week2)
    pin_now(_wednesday_noon(3))
    solved_at = _week_monday(2) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    await _clear_weeks(test_engine, [week2])
    try:
        a_id, a_token = await _register_and_login(f"md-mask-a-{tag}@example.com")
        b_id, _ = await _register_and_login(f"md-mask-b-{tag}@example.com")
        c_id, _ = await _register_and_login(f"md-mask-c-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"md-mask-v-{tag}@example.com")
        user_ids = [a_id, b_id, v_id]  # C is deleted by the test itself
        a_name = f"md_mask_a_{tag}"
        b_name = f"md_mask_b_{tag}"
        await _set_user_fields(test_engine, a_id, lichess_username=a_name)
        await _set_user_fields(test_engine, b_id, lichess_username=b_name)
        await _set_user_fields(test_engine, c_id, lichess_username=f"md_mask_c_{tag}")
        await _set_user_fields(test_engine, v_id, lichess_username=f"md_mask_v_{tag}")
        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 4)
        await _seed_solves(test_engine, b_id, solved_at, [_GOOD_SR] * 3)
        await _seed_solves(test_engine, c_id, solved_at, [_GOOD_SR] * 2)
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR])
        assert (await _get_leaderboard(v_token)).status_code == 200  # finalizes week 2

        await _set_user_fields(test_engine, a_id, leaderboard_hidden=True)
        await _delete_users(test_engine, [c_id])

        as_viewer = (await _get_leaderboard(v_token)).json()
        as_a = (await _get_leaderboard(a_token)).json()

        assert [e["name"] for e in as_viewer["points"]["last_week"]["podium"]] == [
            "Anonymous",
            b_name,
            "Deleted user",
        ]
        # D-04: masking only applies to what others see; A still sees their own name.
        assert as_a["points"]["last_week"]["podium"][0] == {
            "medal": "gold",
            "name": a_name,
            "is_viewer": True,
        }
        assert not any(e["is_viewer"] for e in as_viewer["points"]["last_week"]["podium"])
        # The trigger, not only read-time masking, erased the stored name.
        bronze = [row for row in await _standings(test_engine, week2, "points") if row[2] == 3]
        assert bronze == [(None, "Deleted user", 3, 3)]
    finally:
        await _clear_weeks(test_engine, [week2])
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_finalization_waits_for_the_grace_window(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Grace (k=4 finalized, k=5 request): nothing finalizes before deadline + 5 minutes."""
    week4 = _week_monday(4).date()
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", week4)
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    await _clear_weeks(test_engine, [week4])
    try:
        a_id, a_token = await _register_and_login(f"md-grace-a-{tag}@example.com")
        user_ids = [a_id]
        a_name = f"md_grace_a_{tag}"
        await _set_user_fields(test_engine, a_id, lichess_username=a_name)
        await _seed_solves(
            test_engine, a_id, _week_monday(4) + datetime.timedelta(days=1), [_GOOD_SR]
        )

        pin_now(_week_monday(5) + datetime.timedelta(minutes=4, seconds=59))
        early = (await _get_leaderboard(a_token)).json()

        assert early["points"]["last_week"] is None
        assert await _marker_count(test_engine, week4) == 0

        pin_now(_week_monday(5) + datetime.timedelta(minutes=5))
        later = (await _get_leaderboard(a_token)).json()

        assert later["points"]["last_week"]["podium"] == [
            {"medal": "gold", "name": a_name, "is_viewer": True}
        ]
        # The viewer medalled, so the "You finished #N" line stays off (D-03).
        assert later["points"]["last_week"]["viewer_final_rank"] is None
        assert await _marker_count(test_engine, week4) == 1
    finally:
        await _clear_weeks(test_engine, [week4])
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_last_week_is_only_the_immediately_previous_week(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-07 (k=6, 7 finalized, k=8 request): no fallback to an older finalized week."""
    weeks = [_week_monday(k).date() for k in (6, 7)]
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", weeks[0])
    pin_now(_wednesday_noon(8))
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    await _clear_weeks(test_engine, weeks)
    try:
        a_id, a_token = await _register_and_login(f"md-prev-a-{tag}@example.com")
        user_ids = [a_id]
        a_name = f"md_prev_a_{tag}"
        await _set_user_fields(test_engine, a_id, lichess_username=a_name)
        await _seed_solves(
            test_engine, a_id, _week_monday(6) + datetime.timedelta(days=1), [_GOOD_SR]
        )

        body = (await _get_leaderboard(a_token)).json()

        # Week 7 had no entrants, so there is nothing to show, although week 6 holds a gold row.
        assert body["points"]["last_week"] is None
        assert body["accuracy"]["last_week"] is None
        assert await _standings(test_engine, weeks[0], "points") == [(a_id, a_name, 1, 1)]
        assert await _marker_count(test_engine, weeks[1]) == 1
    finally:
        await _clear_weeks(test_engine, weeks)
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_finalization_failure_still_serves_the_board(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Isolation (k=10, 11; k=9 unused): a finalizer error is reported and never fails the board."""
    week10 = _week_monday(10).date()
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", week10)
    pin_now(_wednesday_noon(11))
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    capture = MagicMock()

    async def _boom(*_args: Any, **_kwargs: Any) -> int:
        raise RuntimeError("finalization exploded")

    monkeypatch.setattr(train_router, "finalize_due_weeks", _boom)
    monkeypatch.setattr(train_router.sentry_sdk, "capture_exception", capture)
    await _clear_weeks(test_engine, [week10])
    try:
        v_id, v_token = await _register_and_login(f"md-fail-v-{tag}@example.com")
        user_ids = [v_id]
        await _seed_solves(
            test_engine, v_id, _week_monday(10) + datetime.timedelta(days=1), [_GOOD_SR]
        )
        await _seed_solves(
            test_engine, v_id, _week_monday(11) + datetime.timedelta(days=1), [_GOOD_SR]
        )

        resp = await _get_leaderboard(v_token)

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Reading the viewer's visibility after the rollback proves no expired User
        # attribute was touched (it would raise MissingGreenlet).
        assert body["points"]["viewer"]["rank"] == 1
        assert body["points"]["viewer"]["visibility"] == "public"
        assert capture.call_count == 1
        assert await _marker_count(test_engine, week10) == 0
    finally:
        await _clear_weeks(test_engine, [week10])
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_unclaimed_then_claim_round_trip(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracer (k=20 finalized, k=21 request): list the medal, claim it, it is gone for A only."""
    week20 = _week_monday(20).date()
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", week20)
    pin_now(_wednesday_noon(21))
    solved_at = _week_monday(20) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    await _clear_weeks(test_engine, [week20])
    try:
        a_id, a_token = await _register_and_login(f"md-claim-a-{tag}@example.com")
        b_id, b_token = await _register_and_login(f"md-claim-b-{tag}@example.com")
        user_ids = [a_id, b_id]
        await _set_user_fields(test_engine, a_id, lichess_username=f"md_claim_a_{tag}")
        await _set_user_fields(test_engine, b_id, lichess_username=f"md_claim_b_{tag}")
        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 3)
        await _seed_solves(test_engine, b_id, solved_at, [_GOOD_SR])

        # The GET itself finalizes the closed week: no leaderboard request came first.
        first = await _get_unclaimed(a_token)

        assert first.status_code == 200, first.text
        assert first.json() == {
            "medals": [
                {
                    "week_start": week20.isoformat(),
                    "board": "points",
                    "medal": "gold",
                    "value": 9,
                    "shared": False,
                }
            ]
        }
        _assert_no_ids(first.json())
        b_before = await _get_unclaimed(b_token)
        assert b_before.json()["medals"] == [
            {
                "week_start": week20.isoformat(),
                "board": "points",
                "medal": "silver",
                "value": 3,
                "shared": False,
            }
        ]

        claimed = await _post_claim(
            a_token, [{"week_start": week20.isoformat(), "board": "points"}]
        )

        assert claimed.status_code == 204, claimed.text
        assert (await _get_unclaimed(a_token)).json() == {"medals": []}
        b_after = await _get_unclaimed(b_token)
        assert [m["medal"] for m in b_after.json()["medals"]] == ["silver"]
        _assert_no_ids(b_after.json())
    finally:
        await _clear_weeks(test_engine, [week20])
        await _delete_users(test_engine, user_ids)


def _key(week: datetime.date, board: str) -> dict[str, str]:
    return {"week_start": week.isoformat(), "board": board}


async def _celebrated_at(
    test_engine: Any, week: datetime.date, board: str, user_id: int
) -> datetime.datetime | None:
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(
            select(TrainWeeklyStanding.celebrated_at).where(
                TrainWeeklyStanding.week_start == week,
                TrainWeeklyStanding.board == board,
                TrainWeeklyStanding.user_id == user_id,
            )
        )
        return result.scalar_one()


@pytest.mark.asyncio
async def test_unclaimed_order_newest_week_first_points_before_accuracy(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-11 (k=22, 23 finalized, k=24 request): newest week first, Points before Accuracy."""
    week22 = _week_monday(22).date()
    week23 = _week_monday(23).date()
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", week22)
    pin_now(_wednesday_noon(24))
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    await _clear_weeks(test_engine, [week22, week23])
    try:
        a_id, a_token = await _register_and_login(f"md-ord-a-{tag}@example.com")
        b_id, _ = await _register_and_login(f"md-ord-b-{tag}@example.com")
        user_ids = [a_id, b_id]
        await _set_user_fields(test_engine, a_id, lichess_username=f"md_ord_a_{tag}")
        await _set_user_fields(test_engine, b_id, lichess_username=f"md_ord_b_{tag}")
        # Week 22: A alone, 20 solves = 60 points and a qualified Accuracy entry.
        await _seed_solves(
            test_engine, a_id, _week_monday(22) + datetime.timedelta(days=1), [_GOOD_SR] * 20
        )
        # Week 23: B beats A on Points; neither qualifies on Accuracy.
        await _seed_solves(
            test_engine, a_id, _week_monday(23) + datetime.timedelta(days=1), [_GOOD_SR] * 2
        )
        await _seed_solves(
            test_engine, b_id, _week_monday(23) + datetime.timedelta(days=1), [_GOOD_SR] * 4
        )

        resp = await _get_unclaimed(a_token)

        assert resp.status_code == 200, resp.text
        assert [(m["week_start"], m["board"], m["medal"]) for m in resp.json()["medals"]] == [
            (week23.isoformat(), "points", "silver"),
            (week22.isoformat(), "points", "gold"),
            (week22.isoformat(), "accuracy", "gold"),
        ]
        assert [m["value"] for m in resp.json()["medals"]] == [6, 60, 100]
    finally:
        await _clear_weeks(test_engine, [week22, week23])
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_claim_is_scoped_to_the_caller_and_idempotent(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IDOR, replay, D-04 and D-10 (k=25 finalized, k=26 request)."""
    week25 = _week_monday(25).date()
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", week25)
    first_now = _wednesday_noon(26)
    pin_now(first_now)
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    await _clear_weeks(test_engine, [week25])
    try:
        a_id, a_token = await _register_and_login(f"md-scope-a-{tag}@example.com")
        b_id, b_token = await _register_and_login(f"md-scope-b-{tag}@example.com")
        c_id, c_token = await _register_and_login(f"md-scope-c-{tag}@example.com")
        g_id, g_token = await _register_and_login(f"md-scope-g-{tag}@example.com")
        user_ids = [a_id, b_id, c_id, g_id]
        for uid, name in ((a_id, "a"), (b_id, "b"), (c_id, "c")):
            await _set_user_fields(test_engine, uid, lichess_username=f"md_scope_{name}_{tag}")
        await _set_user_fields(test_engine, g_id, is_guest=True, lichess_username=f"md_sg_{tag}")
        solved_at = _week_monday(25) + datetime.timedelta(days=1)
        # A and B tie at 9 points (ranks 1, 1), C takes rank 3 with 3 points.
        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 3)
        await _seed_solves(test_engine, b_id, solved_at, [_GOOD_SR] * 3)
        await _seed_solves(test_engine, c_id, solved_at, [_GOOD_SR])
        b_list = await _get_unclaimed(b_token)  # finalizes week 25
        # D-04 is about opting out AFTER the week; a user hidden at finalization gets no row.
        await _set_user_fields(test_engine, a_id, leaderboard_hidden=True)

        a_list = (await _get_unclaimed(a_token)).json()["medals"]
        c_list = (await _get_unclaimed(c_token)).json()["medals"]
        assert [(m["medal"], m["shared"]) for m in b_list.json()["medals"]] == [("gold", True)]
        assert [(m["medal"], m["shared"]) for m in a_list] == [
            ("gold", True)
        ]  # hidden, still listed
        assert [(m["medal"], m["shared"]) for m in c_list] == [("bronze", False)]

        # B posts the key that also matches A's medal: only B's own row is claimed.
        assert (await _post_claim(b_token, [_key(week25, "points")])).status_code == 204
        assert (await _get_unclaimed(b_token)).json() == {"medals": []}
        assert len((await _get_unclaimed(a_token)).json()["medals"]) == 1
        assert await _celebrated_at(test_engine, week25, "points", a_id) is None

        # A claims twice (D-04: still hidden); the second POST, at a later pinned now, is a no-op.
        assert (await _post_claim(a_token, [_key(week25, "points")])).status_code == 204
        pin_now(first_now + datetime.timedelta(hours=3))
        assert (await _post_claim(a_token, [_key(week25, "points")])).status_code == 204
        assert await _celebrated_at(test_engine, week25, "points", a_id) == first_now
        assert (await _get_unclaimed(a_token)).json() == {"medals": []}
        assert len((await _get_unclaimed(c_token)).json()["medals"]) == 1  # C never claimed

        # D-10 (server side): a guest has no rows; GET is empty and POST is a harmless 204.
        assert (await _get_unclaimed(g_token)).json() == {"medals": []}
        assert (await _post_claim(g_token, [_key(week25, "points")])).status_code == 204
        assert await _celebrated_at(test_engine, week25, "points", c_id) is None
    finally:
        await _clear_weeks(test_engine, [week25])
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_claim_validation_rejects_bad_bodies(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Validation (k=27): bad bodies are 422 before any SQL; no token is 401 on both routes."""
    pin_now(_wednesday_noon(27))
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    try:
        u_id, token = await _register_and_login(f"md-val-{tag}@example.com")
        user_ids = [u_id]
        good = _key(_week_monday(27).date(), "points")

        assert (await _post_claim(token, [])).status_code == 422
        assert (await _post_claim(token, [good] * 101)).status_code == 422
        assert (
            await _post_claim(token, [_key(_week_monday(27).date(), "speed")])
        ).status_code == 422
        assert (
            await _post_claim(token, [{"week_start": "2033-13-40", "board": "points"}])
        ).status_code == 422
        # The boundary itself is valid: 100 keys, none of which match a row.
        assert (await _post_claim(token, [good] * 100)).status_code == 204

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get(UNCLAIMED_ENDPOINT)).status_code == 401
            assert (await client.post(CLAIM_ENDPOINT, json={"medals": [good]})).status_code == 401
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_medal_tally_counts_lifetime_medals_per_board(
    test_engine: Any,
    pin_now: Callable[[datetime.datetime], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tally (k=30, 31 finalized, k=32 request): per board, survives an opt-out round trip."""
    weeks = [_week_monday(k).date() for k in (30, 31, 32)]
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", weeks[0])
    pin_now(_wednesday_noon(32))
    tag = uuid.uuid4().hex[:8]
    a_name, b_name, v_name = (f"md_tally_{n}_{tag}" for n in ("a", "b", "v"))
    user_ids: list[int] = []
    await _clear_weeks(test_engine, weeks)
    try:
        a_id, a_token = await _register_and_login(f"md-tally-a-{tag}@example.com")
        b_id, _ = await _register_and_login(f"md-tally-b-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"md-tally-v-{tag}@example.com")
        user_ids = [a_id, b_id, v_id]
        for uid, name in ((a_id, a_name), (b_id, b_name), (v_id, v_name)):
            await _set_user_fields(test_engine, uid, lichess_username=name)
        for k in (30, 31):  # A wins Points twice, B is second twice
            solved_at = _week_monday(k) + datetime.timedelta(days=1)
            await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 4)
            await _seed_solves(test_engine, b_id, solved_at, [_GOOD_SR])
        live = _week_monday(32) + datetime.timedelta(days=1)
        for uid in (a_id, b_id, v_id):
            await _seed_solves(test_engine, uid, live, [_GOOD_SR])

        def tallies(body: dict[str, Any], board: str) -> dict[str, dict[str, int]]:
            return {r["name"]: r["medals"] for r in body[board]["rows"]}

        gold2 = {"gold": 2, "silver": 0, "bronze": 0}
        silver2 = {"gold": 0, "silver": 2, "bronze": 0}
        zero = {"gold": 0, "silver": 0, "bronze": 0}

        resp = await _get_leaderboard(v_token)
        assert resp.status_code == 200, resp.text
        as_v = resp.json()
        _assert_no_ids(as_v)
        assert tallies(as_v, "points") == {a_name: gold2, b_name: silver2, v_name: zero}
        # Nobody ever qualified on Accuracy, so every Accuracy row (tentative now) is zero.
        assert set(tallies(as_v, "accuracy")) == {a_name, b_name, v_name}
        assert all(t == zero for t in tallies(as_v, "accuracy").values())

        # Opt out: others no longer see A at all; A's own row keeps the tally.
        await _set_user_fields(test_engine, a_id, leaderboard_hidden=True)
        as_a = (await _get_leaderboard(a_token)).json()
        assert tallies(as_a, "points")[a_name] == gold2
        assert a_name not in tallies((await _get_leaderboard(v_token)).json(), "points")

        # Opt back in: the tally follows the user id and is still there.
        await _set_user_fields(test_engine, a_id, leaderboard_hidden=False)
        again = (await _get_leaderboard(v_token)).json()
        _assert_no_ids(again)
        assert tallies(again, "points")[a_name] == gold2
    finally:
        await _clear_weeks(test_engine, weeks)
        await _delete_users(test_engine, user_ids)
