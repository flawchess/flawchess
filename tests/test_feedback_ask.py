"""Integration tests for the milestone feedback ask (SEED-191, Phase 234).

Requirement ids: FBASK-01 (prompt_state defaults), FBASK-02 (GET and PUT profile
carry active_days + feedback_ask), FBASK-03 (server-decided eligibility, today-inclusive
active days), FBASK-04 (view / snooze / done lifecycle, guards, concurrency).

Clock: the ``pin_now`` fixture pins ``dev_now_utc`` to a day before the real date.
LastActivityMiddleware writes user_activity rows with the REAL clock after each
authenticated 2xx response, so those rows are dated after the pinned day and fall
outside the ``activity_date < today`` count. Every test that seeds rows deletes its
user in a ``finally`` block (CASCADE removes activity and feedback rows) so seeded
past activity cannot leak into the global activity-stats tests.
"""

import asyncio
import datetime
import json
import uuid
from collections.abc import Callable, Iterator, Sequence

import httpx
import pytest
from sqlalchemy import delete, select, text

from app.core import database as db_module
from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.user import User
from app.models.user_activity import UserActivity
from app.schemas.feedback_ask import FEEDBACK_ASK_ID, FEEDBACK_ASK_MIN_ACTIVE_DAYS

_PASSWORD = "testpassword123"

# Before the real date (see module docstring).
NOW = datetime.datetime(2026, 3, 10, 12, 0, tzinfo=datetime.UTC)
TODAY = NOW.date()

PinNow = Callable[[datetime.datetime], None]


@pytest.fixture
def pin_now() -> Iterator[PinNow]:
    """Pin dev_now_utc for the test; the override is removed on teardown."""

    def _pin(now: datetime.datetime) -> None:
        app.dependency_overrides[dev_now_utc] = lambda: now

    yield _pin
    app.dependency_overrides.pop(dev_now_utc, None)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _register(client: httpx.AsyncClient) -> tuple[int, dict[str, str]]:
    """Register a fresh user; return (user_id, auth headers)."""
    email = f"feedback_ask_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post("/api/auth/register", json={"email": email, "password": _PASSWORD})
    login = await client.post(
        "/api/auth/jwt/login", data={"username": email, "password": _PASSWORD}
    )
    return int(reg.json()["id"]), {"Authorization": f"Bearer {login.json()['access_token']}"}


def _prior_days(count: int) -> list[datetime.date]:
    """`count` distinct days strictly before TODAY."""
    return [TODAY - datetime.timedelta(days=offset) for offset in range(1, count + 1)]


async def _seed_activity(user_id: int, days: Sequence[datetime.date]) -> None:
    async with db_module.async_session_maker() as session:
        session.add_all([UserActivity(user_id=user_id, activity_date=day) for day in days])
        await session.commit()


async def _prompt_state(user_id: int) -> dict[str, object]:
    async with db_module.async_session_maker() as session:
        result = await session.execute(select(User.prompt_state).where(User.id == user_id))
        return dict(result.scalar_one())


async def _delete_user(user_id: int) -> None:
    async with db_module.async_session_maker() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_feedback_ask_new_user_prompt_state_is_empty_object() -> None:
    """FBASK-01: a registered user's prompt_state is a JSON object, empty."""
    async with _client() as client:
        user_id, _ = await _register(client)
    try:
        assert await _prompt_state(user_id) == {}
        async with db_module.async_session_maker() as session:
            result = await session.execute(
                text("SELECT jsonb_typeof(prompt_state) FROM users WHERE id = :uid"),
                {"uid": user_id},
            )
            assert result.scalar_one() == "object"
    finally:
        await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_profile_inactive_below_threshold(pin_now: PinNow) -> None:
    """FBASK-03: 3 prior days + today = 4 active days, one short of the threshold."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 2))
            body = (await client.get("/api/users/me/profile", headers=headers)).json()
            assert body["active_days"] == FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1
            assert body["feedback_ask"] == {"active": False}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_profile_active_at_threshold(pin_now: PinNow) -> None:
    """FBASK-03: 4 prior days + today = 5 active days, the first fetch of day 5 shows the ask."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            body = (await client.get("/api/users/me/profile", headers=headers)).json()
            assert body["active_days"] == FEEDBACK_ASK_MIN_ACTIVE_DAYS
            assert body["feedback_ask"] == {"active": True}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_today_row_counts_once(pin_now: PinNow) -> None:
    """FBASK-03: a user_activity row dated today never counts twice (5, not 6)."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            days = [*_prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1), TODAY]
            await _seed_activity(user_id, days)
            body = (await client.get("/api/users/me/profile", headers=headers)).json()
            assert body["active_days"] == FEEDBACK_ASK_MIN_ACTIVE_DAYS
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_view_records_first_view(pin_now: PinNow) -> None:
    """FBASK-04: the first view of an eligible user lands in users.prompt_state."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            resp = await client.post(
                "/api/users/me/feedback-ask", json={"action": "view"}, headers=headers
            )
            assert resp.status_code == 200
            assert resp.json() == {"active": True}
            assert await _prompt_state(user_id) == {
                FEEDBACK_ASK_ID: {"round": 1, "views": 1, "last_view_date": TODAY.isoformat()}
            }
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_get_and_put_profile_agree(pin_now: PinNow) -> None:
    """FBASK-02: GET and PUT /me/profile return identical active_days and feedback_ask."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            got = (await client.get("/api/users/me/profile", headers=headers)).json()
            put = await client.put(
                "/api/users/me/profile", json={"leaderboard_hidden": False}, headers=headers
            )
            assert put.status_code == 200
            assert put.json()["active_days"] == got["active_days"]
            assert put.json()["feedback_ask"] == got["feedback_ask"] == {"active": True}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_any_feedback_ends_ask(pin_now: PinNow) -> None:
    """FBASK-03: a feedback row from any source (here the floating button) ends the ask."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            before = (await client.get("/api/users/me/profile", headers=headers)).json()
            assert before["feedback_ask"] == {"active": True}
            fb = await client.post(
                "/api/feedback",
                json={"text": "Nice app", "rating": 5, "page_url": "/openings"},
                headers=headers,
            )
            assert fb.status_code == 201
            after = (await client.get("/api/users/me/profile", headers=headers)).json()
            assert after["feedback_ask"] == {"active": False}
        finally:
            await _delete_user(user_id)


# ---------------------------------------------------------------------------
# Task 2: snooze / done / auto-snooze grace / round 2 / guards / concurrency
# ---------------------------------------------------------------------------


def _day(offset: int) -> datetime.datetime:
    """Pinned clock `offset` days after NOW."""
    return NOW + datetime.timedelta(days=offset)


async def _post(client: httpx.AsyncClient, headers: dict[str, str], action: str) -> httpx.Response:
    return await client.post("/api/users/me/feedback-ask", json={"action": action}, headers=headers)


async def _profile(client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, object]:
    resp = await client.get("/api/users/me/profile", headers=headers)
    assert resp.status_code == 200
    return dict(resp.json())


@pytest.mark.asyncio
async def test_feedback_ask_snooze_hides_until_reask_gap(pin_now: PinNow) -> None:
    """FBASK-04: snooze hides immediately; the ask returns after +10 active days (not +9)."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            resp = await _post(client, headers, "snooze")
            assert resp.status_code == 200
            assert resp.json() == {"active": False}
            stored = (await _prompt_state(user_id))[FEEDBACK_ASK_ID]
            assert stored == {
                "status": "snoozed",
                "snoozed_by": "click",
                "snoozed_at_days": FEEDBACK_ASK_MIN_ACTIVE_DAYS,
            }
            # Active days accumulate: TODAY..TODAY+9 each gained a row.
            await _seed_activity(user_id, [TODAY + datetime.timedelta(days=i) for i in range(10)])
            pin_now(_day(9))
            assert (await _profile(client, headers))["feedback_ask"] == {"active": False}
            pin_now(_day(10))
            body = await _profile(client, headers)
            assert body["active_days"] == FEEDBACK_ASK_MIN_ACTIVE_DAYS + 10
            assert body["feedback_ask"] == {"active": True}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_three_view_days_auto_snooze_with_grace(pin_now: PinNow) -> None:
    """FBASK-04: the 3rd view day keeps showing all day, then the ask is snoozed."""
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS + 1))
            for offset in range(3):
                pin_now(_day(offset))
                resp = await _post(client, headers, "view")
                assert resp.json() == {"active": True}
            stored = (await _prompt_state(user_id))[FEEDBACK_ASK_ID]
            assert isinstance(stored, dict)
            assert stored["status"] == "snoozed"
            assert stored["snoozed_by"] == "views"
            assert stored["views"] == 3
            # Same day: still active (grace), profile agrees.
            assert (await _profile(client, headers))["feedback_ask"] == {"active": True}
            # Next day: hidden.
            pin_now(_day(3))
            assert (await _profile(client, headers))["feedback_ask"] == {"active": False}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_done_ends_ask_forever(pin_now: PinNow) -> None:
    """FBASK-04: done hides the ask and later views never write again."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            assert (await _post(client, headers, "view")).json() == {"active": True}
            resp = await _post(client, headers, "done")
            assert resp.json() == {"active": False}
            before = await _prompt_state(user_id)
            pin_now(_day(40))
            assert (await _post(client, headers, "view")).json() == {"active": False}
            assert (await _profile(client, headers))["feedback_ask"] == {"active": False}
            assert await _prompt_state(user_id) == before
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_rejects_unknown_action_and_extra_key() -> None:
    """Guards: an unknown action and an extra body key both return 422."""
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            assert (await _post(client, headers, "bogus")).status_code == 422
            extra = await client.post(
                "/api/users/me/feedback-ask",
                json={"action": "view", "user_id": 1},
                headers=headers,
            )
            assert extra.status_code == 422
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_requires_auth() -> None:
    """Guards: an unauthenticated call returns 401."""
    async with _client() as client:
        resp = await client.post("/api/users/me/feedback-ask", json={"action": "view"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_feedback_ask_ineligible_view_writes_nothing(pin_now: PinNow) -> None:
    """Guards: a 4-active-day user's view is a no-op."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 2))
            resp = await _post(client, headers, "view")
            assert resp.json() == {"active": False}
            assert await _prompt_state(user_id) == {}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_guest_is_inactive_and_never_written(pin_now: PinNow) -> None:
    """Guards: a guest gets active false from every route and no write."""
    pin_now(NOW)
    async with _client() as client:
        created = await client.post("/api/auth/guest/create")
        assert created.status_code == 201
        headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
        email = str((await _profile(client, headers))["email"])
        async with db_module.async_session_maker() as session:
            guest_id = (
                (
                    await session.execute(
                        select(User.id).where(User.email == email)  # ty: ignore[invalid-argument-type]  # FastAPI-Users types email as plain str
                    )
                )
                .unique()
                .scalar_one()
            )
        try:
            await _seed_activity(guest_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS + 5))
            assert (await _profile(client, headers))["feedback_ask"] == {"active": False}
            for action in ("view", "snooze", "done"):
                assert (await _post(client, headers, action)).json() == {"active": False}
            assert await _prompt_state(guest_id) == {}
        finally:
            await _delete_user(guest_id)


@pytest.mark.asyncio
async def test_feedback_ask_impersonation_is_inactive_and_never_written(
    pin_now: PinNow,
) -> None:
    """Guards: an impersonation token sees no ask and cannot write the target's state."""
    pin_now(NOW)
    async with _client() as client:
        admin_id, admin_headers = await _register(client)
        target_id, target_headers = await _register(client)
        try:
            async with db_module.async_session_maker() as session:
                await session.execute(
                    text("UPDATE users SET is_superuser = true WHERE id = :uid"),
                    {"uid": admin_id},
                )
                await session.commit()
            await _seed_activity(target_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS + 1))
            # The target sees the ask normally.
            assert (await _profile(client, target_headers))["feedback_ask"] == {"active": True}
            imp = await client.post(f"/api/admin/impersonate/{target_id}", headers=admin_headers)
            assert imp.status_code == 200
            imp_headers = {"Authorization": f"Bearer {imp.json()['access_token']}"}
            body = await _profile(client, imp_headers)
            assert body["feedback_ask"] == {"active": False}
            for action in ("view", "snooze", "done"):
                assert (await _post(client, imp_headers, action)).json() == {"active": False}
            assert await _prompt_state(target_id) == {}
        finally:
            await _delete_user(admin_id)
            await _delete_user(target_id)


@pytest.mark.asyncio
async def test_feedback_ask_concurrent_same_day_views_count_once(pin_now: PinNow) -> None:
    """FBASK-04 / T-234-04: two simultaneous same-day views leave views == 1."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            # Separate requests, each with its own DB session (not one AsyncSession).
            first, second = await asyncio.gather(
                _post(client, headers, "view"), _post(client, headers, "view")
            )
            assert first.status_code == second.status_code == 200
            stored = (await _prompt_state(user_id))[FEEDBACK_ASK_ID]
            assert isinstance(stored, dict)
            assert stored["views"] == 1
        finally:
            await _delete_user(user_id)


async def _set_prompt_state(user_id: int, state: dict[str, object]) -> None:
    async with db_module.async_session_maker() as session:
        await session.execute(
            text("UPDATE users SET prompt_state = CAST(:state AS jsonb) WHERE id = :uid"),
            {"state": json.dumps(state), "uid": user_id},
        )
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["view", "snooze", "done"])
async def test_feedback_ask_corrupt_state_fails_closed_not_500(
    pin_now: PinNow, action: str
) -> None:
    """WR-01: a corrupt stored state (unknown key) returns 200 inactive, never a 500.

    Before the fix the UPDATE's RETURNING value failed validation and surfaced as a 500;
    the UPDATE must also be rolled back so the stored state is left untouched.
    """
    pin_now(NOW)
    corrupt: dict[str, object] = {FEEDBACK_ASK_ID: {"bogus_key": 1}}
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            await _set_prompt_state(user_id, corrupt)
            resp = await _post(client, headers, action)
            assert resp.status_code == 200
            assert resp.json() == {"active": False}
            assert await _prompt_state(user_id) == corrupt
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_ineligible_snooze_writes_nothing(pin_now: PinNow) -> None:
    """WR-02: a click-snooze from a below-threshold user must not write ask state.

    Before the fix snooze ran ungated and stored snoozed_at_days=2, pushing the re-ask
    out to 12 active days instead of one gap after the real milestone.
    """
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 3))
            resp = await _post(client, headers, "snooze")
            assert resp.json() == {"active": False}
            assert await _prompt_state(user_id) == {}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_snooze_after_feedback_writes_nothing(pin_now: PinNow) -> None:
    """WR-02: a user who already sent feedback (any source) cannot write snooze state."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 1))
            fb = await client.post(
                "/api/feedback",
                json={"text": "Nice app", "rating": 5, "page_url": "/openings"},
                headers=headers,
            )
            assert fb.status_code == 201
            resp = await _post(client, headers, "snooze")
            assert resp.json() == {"active": False}
            assert await _prompt_state(user_id) == {}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_ask_done_stays_ungated(pin_now: PinNow) -> None:
    """WR-02: done is deliberately unconditional (SEED-191 #5: it only shrinks exposure)."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(FEEDBACK_ASK_MIN_ACTIVE_DAYS - 3))
            resp = await _post(client, headers, "done")
            assert resp.json() == {"active": False}
            stored = (await _prompt_state(user_id))[FEEDBACK_ASK_ID]
            assert stored == {"status": "done"}
        finally:
            await _delete_user(user_id)
