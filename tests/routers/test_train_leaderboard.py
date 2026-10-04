"""Router tests for GET /api/train/leaderboard (Phase 230, plans 01 and 02).

Cases:
- test_points_and_accuracy_boards_rank_this_week: tracer, both boards end to end
  with a guest and an opted-out user that must stay invisible to a public viewer
- test_response_key_set_has_no_user_ids: exact key sets, no id/email anywhere
- test_leaderboard_requires_auth: 401 without a token
- test_solves_outside_the_pinned_week_are_ignored: half-open week boundaries,
  keyed on solved_at and not on drill_sessions.session_date (D-02)

Isolation rule: leaderboard data is global and router tests commit, so every test
in this module pins `dev_now_utc` into its own ISO week (the Monday 2032-01-05 plus
k weeks) and deletes the users it registered in `finally` (deleting a user cascades
its sessions and solves). A k is never reused anywhere in the phase.

k table (this plan holds k 0-9; Plan 02 holds k 10-29; Plan 04 holds k 30-39):
- k=0  test_points_and_accuracy_boards_rank_this_week
- k=1  owned by test_solves_outside_the_pinned_week_are_ignored (its previous-week row)
- k=2  test_solves_outside_the_pinned_week_are_ignored
- k=3  owned by test_solves_outside_the_pinned_week_are_ignored (its next-week row)
- k=4  test_response_key_set_has_no_user_ids
- k=5  test_leaderboard_requires_auth
- k=10 test_rank_without_session_follows_the_viewer_across_two_sessions
- k=11 test_foreign_session_id_ignored
- k=12 test_session_id_validation_rejects_bad_values
- k=13 test_hidden_viewer_sees_private_row
- k=14 test_guest_viewer_sees_ghost_row
- k=30 test_profile_opt_out_hides_user_from_other_viewers
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.user import User

ENDPOINT = "/api/train/leaderboard"

# Monday of the k=0 week; every test adds its own k weeks.
BASE_MONDAY = datetime.datetime(2032, 1, 5, tzinfo=datetime.UTC)

Outcome = tuple[bool, DrillMoveQuality, DrillSource]

_GOOD_SR: Outcome = (True, DrillMoveQuality.GOOD, DrillSource.SR_ITEM)
_GOOD_FILLER: Outcome = (True, DrillMoveQuality.GOOD, DrillSource.SHARP_FILLER)


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
    *,
    session_date: datetime.date | None = None,
) -> int:
    """Insert one completed session with one solved row per outcome; return its id.

    `session_date` defaults to the solve's UTC date. A test can override it to prove
    the window keys on solved_at, not on the session date (D-02).
    """
    day = session_date or solved_at.astimezone(datetime.UTC).date()
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
                        sharp_puzzle_id=(
                            f"lb{position}" if source == DrillSource.SHARP_FILLER else None
                        ),
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


async def _get_leaderboard(token: str, session_id: int | str | None = None) -> httpx.Response:
    params = {} if session_id is None else {"session_id": session_id}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(
            ENDPOINT, params=params, headers={"Authorization": f"Bearer {token}"}
        )


def _rows(board: dict[str, Any]) -> list[tuple[int | None, str, int, int, bool]]:
    return [(r["rank"], r["name"], r["value"], r["puzzles"], r["is_viewer"]) for r in board["rows"]]


@pytest.mark.asyncio
async def test_points_and_accuracy_boards_rank_this_week(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Tracer (k=0): both boards computed from drill_solves, guests/opted-out hidden."""
    now = _wednesday_noon(0)
    pin_now(now)
    solved_at = _week_monday(0) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    try:
        a_id, _ = await _register_and_login(f"lb-a-{tag}@example.com")
        b_id, _ = await _register_and_login(f"lb-b-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"lb-v-{tag}@example.com")
        g_id, _ = await _register_and_login(f"lb-g-{tag}@example.com")
        h_id, _ = await _register_and_login(f"lb-h-{tag}@example.com")
        user_ids = [a_id, b_id, v_id, g_id, h_id]
        a_name = f"lb_alpha_{tag}"
        b_name = f"lb_bravo_{tag}"
        await _set_user_fields(test_engine, a_id, lichess_username=a_name)
        await _set_user_fields(test_engine, b_id, chess_com_username=b_name)
        await _set_user_fields(test_engine, g_id, is_guest=True, lichess_username="lb_guest")
        await _set_user_fields(
            test_engine, h_id, leaderboard_hidden=True, lichess_username="lb_hidden"
        )

        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 4)
        await _seed_solves(
            test_engine,
            b_id,
            solved_at,
            [
                _GOOD_SR,
                (True, DrillMoveQuality.INACCURACY, DrillSource.RED_HERRING),
                (False, DrillMoveQuality.WRONG, DrillSource.SR_ITEM),
                _GOOD_FILLER,
            ],
        )
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR] * 2)
        await _seed_solves(test_engine, g_id, solved_at, [_GOOD_SR] * 10)
        await _seed_solves(test_engine, h_id, solved_at, [_GOOD_SR] * 10)

        resp = await _get_leaderboard(v_token)

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert _rows(body["points"]) == [
            (1, a_name, 12, 4, False),
            (2, b_name, 8, 4, False),
            (3, "Anonymous", 6, 2, True),
        ]
        assert _rows(body["accuracy"]) == [
            (None, a_name, 100, 4, False),
            (None, b_name, 55, 3, False),
            (None, "Anonymous", 100, 2, True),
        ]
        assert body["accuracy"]["viewer"]["rank"] is None
        assert all(r["tentative"] for r in body["accuracy"]["rows"])
        assert body["accuracy"]["viewer"]["puzzles_to_qualify"] == 18
        assert body["points"]["viewer"]["rank"] == 3
        assert body["points"]["viewer"]["visibility"] == "public"
        assert body["points"]["viewer"]["rank_without_session"] is None
        all_names = {r["name"] for b in ("points", "accuracy") for r in body[b]["rows"]}
        assert "lb_guest" not in all_names
        assert "lb_hidden" not in all_names
        assert datetime.datetime.fromisoformat(body["week_start"]) == _week_monday(0)
        assert datetime.datetime.fromisoformat(body["week_end"]) == _week_monday(1)
        assert body["seconds_remaining"] == 388800
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_response_key_set_has_no_user_ids(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Key set (k=4): every key pinned, no id or email anywhere in the payload."""
    pin_now(_wednesday_noon(4))
    solved_at = _week_monday(4) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    a_email = f"lb-keyset-a-{tag}@example.com"
    v_email = f"lb-keyset-v-{tag}@example.com"
    user_ids: list[int] = []
    try:
        a_id, _ = await _register_and_login(a_email)
        v_id, v_token = await _register_and_login(v_email)
        user_ids = [a_id, v_id]
        await _set_user_fields(test_engine, a_id, lichess_username=f"lb_keyset_a_{tag}")
        await _set_user_fields(test_engine, v_id, lichess_username=f"lb_keyset_v_{tag}")
        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 2)
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR])

        resp = await _get_leaderboard(v_token)

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body) == {"week_start", "week_end", "seconds_remaining", "points", "accuracy"}
        for board_name in ("points", "accuracy"):
            board = body[board_name]
            assert set(board) == {"rows", "viewer", "pass_target"}
            assert len(board["rows"]) == 2
            for row in board["rows"]:
                assert set(row) == {
                    "rank",
                    "name",
                    "value",
                    "puzzles",
                    "tentative",
                    "is_viewer",
                    "visibility",
                    "gap_before",
                }
            assert set(board["viewer"]) == {
                "rank",
                "rank_without_session",
                "tentative",
                "puzzles_to_qualify",
                "visibility",
            }

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    assert key not in {"user_id", "id", "email"}, key
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        # V is behind A on points (3 vs 6), so the Points board carries a pass target
        # naming A; the Accuracy board never does.
        assert set(body["points"]["pass_target"]) == {"name", "points_needed"}
        assert body["points"]["pass_target"]["name"] == f"lb_keyset_a_{tag}"
        assert body["points"]["pass_target"]["points_needed"] == 4
        assert body["accuracy"]["pass_target"] is None

        walk(body)
        assert a_email not in resp.text
        assert v_email not in resp.text
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_leaderboard_requires_auth(pin_now: Callable[[datetime.datetime], None]) -> None:
    """Auth (k=5): no token gives 401. Seeds nothing but pins its declared week."""
    pin_now(_wednesday_noon(5))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(ENDPOINT)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_solves_outside_the_pinned_week_are_ignored(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Window (k=2, owning k=1 and k=3): half-open [Monday, next Monday) on solved_at."""
    pin_now(_wednesday_noon(2))
    tag = uuid.uuid4().hex[:8]
    last_instant_of_week_1 = _week_monday(2) - datetime.timedelta(microseconds=1)
    first_instant_of_week_3 = _week_monday(3)
    in_week_session_date = _week_monday(2).date()
    user_ids: list[int] = []
    try:
        u_id, u_token = await _register_and_login(f"lb-window-{tag}@example.com")
        user_ids = [u_id]
        # The out-of-week rows carry a session_date INSIDE the pinned week, so a window
        # keyed on drill_sessions.session_date would wrongly count them (D-02).
        await _seed_solves(
            test_engine,
            u_id,
            last_instant_of_week_1,
            [_GOOD_SR],
            session_date=in_week_session_date,
        )
        await _seed_solves(
            test_engine,
            u_id,
            first_instant_of_week_3,
            [_GOOD_SR],
            session_date=in_week_session_date,
        )
        await _seed_solves(test_engine, u_id, _week_monday(2), [_GOOD_SR])

        resp = await _get_leaderboard(u_token)

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Only the Monday 00:00:00 solve that starts the week counts: 3 points, 1 puzzle.
        assert _rows(body["points"]) == [(1, "Anonymous", 3, 1, True)]
        assert _rows(body["accuracy"]) == [(None, "Anonymous", 100, 1, True)]
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_rank_without_session_follows_the_viewer_across_two_sessions(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Tracer (k=10): rank_without_session per board, first session null, no id null."""
    pin_now(_week_monday(10) + datetime.timedelta(days=5, hours=12))  # Saturday 12:00 UTC
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    try:
        a_id, _ = await _register_and_login(f"lb-delta-a-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"lb-delta-v-{tag}@example.com")
        user_ids = [a_id, v_id]
        await _set_user_fields(test_engine, a_id, lichess_username=f"lb_delta_a_{uuid.uuid4().hex}")
        await _set_user_fields(test_engine, v_id, lichess_username=f"lb_delta_v_{uuid.uuid4().hex}")
        await _seed_solves(test_engine, a_id, _week_monday(10), [_GOOD_SR] * 2)
        s1 = await _seed_solves(
            test_engine, v_id, _week_monday(10) + datetime.timedelta(days=1), [_GOOD_SR]
        )

        first = (await _get_leaderboard(v_token, s1)).json()

        # Nothing remains without the first session of the week.
        assert first["points"]["viewer"]["rank"] == 2
        assert first["points"]["viewer"]["rank_without_session"] is None
        assert first["accuracy"]["viewer"]["rank_without_session"] is None

        s2 = await _seed_solves(
            test_engine, v_id, _week_monday(10) + datetime.timedelta(days=2), [_GOOD_SR] * 2
        )

        second = (await _get_leaderboard(v_token, s2)).json()

        # V now has 9 points to A's 6; without S2 V is back to 3 and behind A.
        assert second["points"]["viewer"]["rank"] == 1
        assert second["points"]["viewer"]["rank_without_session"] == 2
        # Both users are under 20 puzzles, so the viewer is unranked on Accuracy and
        # gets no delta (no comparison across the qualification cutoff).
        assert second["accuracy"]["viewer"]["rank"] is None
        assert second["accuracy"]["viewer"]["rank_without_session"] is None

        plain = (await _get_leaderboard(v_token)).json()

        assert plain["points"]["viewer"]["rank_without_session"] is None
        assert plain["accuracy"]["viewer"]["rank_without_session"] is None
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_foreign_session_id_ignored(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Foreign session id (k=11): another user's session subtracts nothing (T-230-04)."""
    pin_now(_wednesday_noon(11))
    solved_at = _week_monday(11) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    try:
        a_id, _ = await _register_and_login(f"lb-foreign-a-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"lb-foreign-v-{tag}@example.com")
        user_ids = [a_id, v_id]
        await _set_user_fields(test_engine, a_id, lichess_username=f"lb_foreign_a_{tag}")
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR])
        foreign = await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 5)

        body = (await _get_leaderboard(v_token, foreign)).json()

        assert body["points"]["viewer"]["rank"] == 2
        assert body["points"]["viewer"]["rank_without_session"] == 2
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["abc", "0", "-1", "2147483648"])
async def test_session_id_validation_rejects_bad_values(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None], bad: str
) -> None:
    """Validation (k=12): junk, zero and int4 overflow are 422s before any SQL."""
    pin_now(_wednesday_noon(12))
    tag = uuid.uuid4().hex[:8]
    user_ids: list[int] = []
    try:
        u_id, u_token = await _register_and_login(f"lb-valid-{tag}@example.com")
        user_ids = [u_id]

        resp = await _get_leaderboard(u_token, bad)

        assert resp.status_code == 422, resp.text
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_hidden_viewer_sees_private_row(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Hidden viewer (k=13): own row visibility 'hidden'; nobody else sees it or ranks past it."""
    pin_now(_wednesday_noon(13))
    solved_at = _week_monday(13) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    h_name = f"lb_hid_h_{tag}"
    user_ids: list[int] = []
    try:
        a_id, _ = await _register_and_login(f"lb-hid-a-{tag}@example.com")
        h_id, h_token = await _register_and_login(f"lb-hid-h-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"lb-hid-v-{tag}@example.com")
        user_ids = [a_id, h_id, v_id]
        await _set_user_fields(test_engine, a_id, lichess_username=f"lb_hid_a_{tag}")
        await _set_user_fields(test_engine, h_id, leaderboard_hidden=True, lichess_username=h_name)
        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 2)
        await _seed_solves(test_engine, h_id, solved_at, [_GOOD_SR] * 5)
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR])

        hidden_body = (await _get_leaderboard(h_token)).json()
        other_body = (await _get_leaderboard(v_token)).json()

        own_rows = [r for r in hidden_body["points"]["rows"] if r["name"] == h_name]
        assert len(own_rows) == 1
        assert own_rows[0]["is_viewer"] is True
        assert own_rows[0]["visibility"] == "hidden"
        assert hidden_body["points"]["viewer"]["visibility"] == "hidden"
        assert hidden_body["points"]["viewer"]["rank"] == 1
        # The other viewer never sees H on either board and ranks as if H were absent.
        for board in ("points", "accuracy"):
            assert h_name not in {r["name"] for r in other_body[board]["rows"]}
        assert other_body["points"]["viewer"]["rank"] == 2
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_guest_viewer_sees_ghost_row(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Guest viewer (k=14): own ghost row visibility 'guest'; registered viewers never see it."""
    pin_now(_wednesday_noon(14))
    solved_at = _week_monday(14) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    g_name = f"lb_ghost_g_{tag}"
    user_ids: list[int] = []
    try:
        a_id, _ = await _register_and_login(f"lb-ghost-a-{tag}@example.com")
        g_id, g_token = await _register_and_login(f"lb-ghost-g-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"lb-ghost-v-{tag}@example.com")
        user_ids = [a_id, g_id, v_id]
        await _set_user_fields(test_engine, a_id, lichess_username=f"lb_ghost_a_{tag}")
        await _set_user_fields(test_engine, g_id, is_guest=True, lichess_username=g_name)
        await _seed_solves(test_engine, a_id, solved_at, [_GOOD_SR] * 2)
        await _seed_solves(test_engine, g_id, solved_at, [_GOOD_SR] * 5)
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR])

        guest_body = (await _get_leaderboard(g_token)).json()
        other_body = (await _get_leaderboard(v_token)).json()

        own_rows = [r for r in guest_body["points"]["rows"] if r["name"] == g_name]
        assert len(own_rows) == 1
        assert own_rows[0]["is_viewer"] is True
        assert own_rows[0]["visibility"] == "guest"
        assert guest_body["points"]["viewer"]["visibility"] == "guest"
        for board in ("points", "accuracy"):
            assert g_name not in {r["name"] for r in other_body[board]["rows"]}
        assert other_body["points"]["viewer"]["rank"] == 2
    finally:
        await _delete_users(test_engine, user_ids)


@pytest.mark.asyncio
async def test_profile_opt_out_hides_user_from_other_viewers(
    test_engine: Any, pin_now: Callable[[datetime.datetime], None]
) -> None:
    """Opt-out end to end (k=30): PUT /users/me/profile hides X from V's boards, X keeps a private row.

    Exercises the real write path (the profile PUT) rather than seeding the column,
    so the schema, router, repository and both leaderboard reads are covered together.
    """
    pin_now(_wednesday_noon(30))
    solved_at = _week_monday(30) + datetime.timedelta(days=1)
    tag = uuid.uuid4().hex[:8]
    x_name = f"lb_optout_{tag}"
    user_ids: list[int] = []
    try:
        x_id, x_token = await _register_and_login(f"lb-optout-x-{tag}@example.com")
        v_id, v_token = await _register_and_login(f"lb-optout-v-{tag}@example.com")
        user_ids = [x_id, v_id]
        await _set_user_fields(test_engine, x_id, lichess_username=x_name)
        await _seed_solves(test_engine, x_id, solved_at, [_GOOD_SR] * 5)
        await _seed_solves(test_engine, v_id, solved_at, [_GOOD_SR] * 2)

        def names(body: dict[str, Any]) -> set[str]:
            return {r["name"] for board in ("points", "accuracy") for r in body[board]["rows"]}

        before = (await _get_leaderboard(v_token)).json()
        assert x_name in names(before)
        assert before["points"]["viewer"]["rank"] == 2

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            put = await client.put(
                "/api/users/me/profile",
                json={"leaderboard_hidden": True},
                headers={"Authorization": f"Bearer {x_token}"},
            )
        assert put.status_code == 200, put.text
        assert put.json()["leaderboard_hidden"] is True

        v_hidden = (await _get_leaderboard(v_token)).json()
        assert x_name not in names(v_hidden)
        assert v_hidden["points"]["viewer"]["rank"] == 1

        x_body = (await _get_leaderboard(x_token)).json()
        for board in ("points", "accuracy"):
            viewer_rows = [r for r in x_body[board]["rows"] if r["is_viewer"]]
            if board == "points":
                assert len(viewer_rows) == 1
            assert all(r["visibility"] == "hidden" for r in viewer_rows)
        assert x_body["points"]["viewer"]["visibility"] == "hidden"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            unhide = await client.put(
                "/api/users/me/profile",
                json={"leaderboard_hidden": False},
                headers={"Authorization": f"Bearer {x_token}"},
            )
        assert unhide.status_code == 200, unhide.text

        v_after = (await _get_leaderboard(v_token)).json()
        assert x_name in names(v_after)
        assert v_after["points"]["viewer"]["rank"] == 2
    finally:
        await _delete_users(test_engine, user_ids)
