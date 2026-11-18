"""Tests for the phase 255 feature-discovery route state.

Endpoint cases go through HTTP with ``dev_now_utc`` pinned to a day before the real
date and delete their users in a ``finally`` block (committed rows, so they cannot use
the rolled-back ``db_session``).

Service-level cases run on the ``db_session`` fixture (a transaction that is rolled
back after each test, so no cleanup). The stored value is read back with a SELECT on
the same session, because a second session cannot see the uncommitted row.
"""

import asyncio
import json
import datetime
import uuid
from collections.abc import Callable, Iterator, Sequence
from typing import Any, get_args

import httpx
import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database as db_module
from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.user import User
from app.models.user_activity import UserActivity
from app.repositories import game_repository
from app.schemas.feature_route import (
    FEATURE_ROUTE_KEY,
    FEATURE_ROUTE_SKIP_ACTIVE_DAYS,
    FeatureRouteActionRequest,
    FeatureRouteState,
    FeatureRouteStepId,
    FeatureRouteStepRecord,
)
from app.services import feature_route_service

# Before the real date; the route stores the UTC day taken from this instant.
NOW = datetime.datetime(2026, 3, 10, 12, 0, tzinfo=datetime.UTC)
TODAY = NOW.date()
_PASSWORD = "testpassword123"

# D-06 order, pinned so adding a step is a deliberate edit here too (D-09).
EXPECTED_STEP_IDS = (
    "import",
    "train",
    "bots",
    "openings",
    "openings-played-as",
    "openings-filters",
    "openings-stats",
    "endgames",
    "library-stats",
    "blunder-check",
)


async def _make_user(session: AsyncSession) -> User:
    """Insert a user inside the rolled-back test transaction."""
    user = User(email=f"route-{uuid.uuid4()}@example.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)  # picks up the prompt_state server default
    return user


async def _stored_prompt_state(session: AsyncSession, user_id: int) -> dict[str, Any]:
    result = await session.execute(select(User.prompt_state).where(User.id == user_id))
    return dict(result.scalar_one())


def _done(step: FeatureRouteStepId) -> FeatureRouteActionRequest:
    return FeatureRouteActionRequest(action="done", step=step)


def test_step_ids_are_pinned_in_d06_order() -> None:
    """D-09: the backend Literal lists the ten route steps in order, blunder-check appended last."""
    assert get_args(FeatureRouteStepId) == EXPECTED_STEP_IDS


def test_build_view_new_user_is_empty_state() -> None:
    """A transient user with an empty prompt_state gets an empty route (no I/O)."""
    view = feature_route_service.build_feature_route_view(User(prompt_state={}))
    assert view == FeatureRouteState()
    assert view is not None
    assert view.steps == {}
    assert view.current is None


def test_build_view_corrupt_state_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A step record with an unknown status gives None and exactly one Sentry capture."""
    captured: list[BaseException] = []
    monkeypatch.setattr(
        feature_route_service.sentry_sdk, "capture_exception", lambda exc: captured.append(exc)
    )
    user = User(
        prompt_state={
            FEATURE_ROUTE_KEY: {
                "steps": {"import": {"status": "bogus", "date": "2026-03-10", "with_dot": False}}
            }
        }
    )
    assert feature_route_service.build_feature_route_view(user) is None
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_done_without_current_step_stores_with_dot_false(db_session: AsyncSession) -> None:
    """D-15: done is accepted with no current step; with_dot records that it was not current."""
    user = await _make_user(db_session)
    state = await feature_route_service.apply_feature_route_action(
        db_session, user, _done("import"), now_utc=NOW, impersonated=False
    )
    assert state is not None
    expected = FeatureRouteStepRecord(status="done", date=NOW.date(), with_dot=False)
    assert state.steps["import"] == expected
    stored = await _stored_prompt_state(db_session, user.id)
    assert stored[FEATURE_ROUTE_KEY]["steps"]["import"] == {
        "status": "done",
        "date": NOW.date().isoformat(),
        "with_dot": False,
    }


@pytest.mark.asyncio
async def test_second_step_keeps_first_and_repeat_is_noop(db_session: AsyncSession) -> None:
    """Nested merge keeps earlier steps; a repeated done keeps the first record."""
    user = await _make_user(db_session)
    first = await feature_route_service.apply_feature_route_action(
        db_session, user, _done("import"), now_utc=NOW, impersonated=False
    )
    assert first is not None
    later = NOW + datetime.timedelta(days=3)
    both = await feature_route_service.apply_feature_route_action(
        db_session, user, _done("train"), now_utc=later, impersonated=False
    )
    assert both is not None
    assert set(both.steps) == {"import", "train"}
    assert both.steps["train"].date == later.date()

    # Repeat done import on a later day: the guarded UPDATE matches no row, the
    # service re-reads, and the first record (NOW's date) is kept.
    repeat = await feature_route_service.apply_feature_route_action(
        db_session, user, _done("import"), now_utc=later, impersonated=False
    )
    assert repeat is not None
    assert repeat.steps["import"].date == NOW.date()
    assert set(repeat.steps) == {"import", "train"}


@pytest.mark.asyncio
async def test_done_keeps_feedback_state(db_session: AsyncSession) -> None:
    """Only the feature_route key is replaced, so feedback_v1 survives."""
    user = await _make_user(db_session)
    user.prompt_state = {"feedback_v1": {"status": "done"}}
    await db_session.flush()
    await feature_route_service.apply_feature_route_action(
        db_session, user, _done("bots"), now_utc=NOW, impersonated=False
    )
    stored = await _stored_prompt_state(db_session, user.id)
    assert stored["feedback_v1"] == {"status": "done"}
    assert set(stored[FEATURE_ROUTE_KEY]["steps"]) == {"bots"}


@pytest.mark.asyncio
async def test_impersonated_session_never_writes(db_session: AsyncSession) -> None:
    """Impersonation returns the read-only view and leaves prompt_state untouched."""
    user = await _make_user(db_session)
    state = await feature_route_service.apply_feature_route_action(
        db_session, user, _done("import"), now_utc=NOW, impersonated=True
    )
    assert state == FeatureRouteState()
    assert await _stored_prompt_state(db_session, user.id) == {}


# --- HTTP endpoint cases (profile field, POST endpoint, guests) -----------------

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
    email = f"feature_route_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post("/api/auth/register", json={"email": email, "password": _PASSWORD})
    login = await client.post(
        "/api/auth/jwt/login", data={"username": email, "password": _PASSWORD}
    )
    return int(reg.json()["id"]), {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _prompt_state(user_id: int) -> dict[str, Any]:
    async with db_module.async_session_maker() as session:
        result = await session.execute(select(User.prompt_state).where(User.id == user_id))
        return dict(result.scalar_one())


async def _delete_user(user_id: int) -> None:
    async with db_module.async_session_maker() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def _post_route(
    client: httpx.AsyncClient, headers: dict[str, str], action: str, step: str
) -> httpx.Response:
    return await client.post(
        "/api/users/me/feature-route", json={"action": action, "step": step}, headers=headers
    )


async def _profile(client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    resp = await client.get("/api/users/me/profile", headers=headers)
    assert resp.status_code == 200
    return dict(resp.json())


@pytest.mark.asyncio
async def test_profile_feature_route_is_empty_and_reads_never_write(pin_now: PinNow) -> None:
    """D-11: a new user's profile carries an empty route, and GETs leave prompt_state alone."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            for _ in range(2):
                body = await _profile(client, headers)
                assert body["feature_route"] == {"steps": {}, "current": None}
            assert await _prompt_state(user_id) == {}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_post_done_is_stored_returned_and_idempotent(pin_now: PinNow) -> None:
    """POST done stores the step, the profile shows it, and a repeat returns the same record."""
    pin_now(NOW)
    record = {"status": "done", "date": TODAY.isoformat(), "with_dot": False}
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            first = await _post_route(client, headers, "done", "import")
            assert first.status_code == 200
            assert first.json()["steps"]["import"] == record
            assert (await _profile(client, headers))["feature_route"]["steps"]["import"] == record
            assert (await _prompt_state(user_id))[FEATURE_ROUTE_KEY]["steps"]["import"] == record
            repeat = await _post_route(client, headers, "done", "import")
            assert repeat.status_code == 200
            assert repeat.json()["steps"]["import"] == record
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_guest_route_is_stored_and_survives_email_promotion(pin_now: PinNow) -> None:
    """D-19: a guest records a step, and a promoted account keeps it."""
    pin_now(NOW)
    new_email = f"feature_route_promo_{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        created = await client.post("/api/auth/guest/create")
        assert created.status_code == 201
        headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
        guest_email = str((await _profile(client, headers))["email"])
        async with db_module.async_session_maker() as session:
            guest_id = (
                (
                    await session.execute(
                        select(User.id).where(User.email == guest_email)  # ty: ignore[invalid-argument-type]  # FastAPI-Users types email as plain str
                    )
                )
                .unique()
                .scalar_one()
            )
        try:
            assert (await _post_route(client, headers, "done", "import")).status_code == 200
            stored = (await _prompt_state(guest_id))[FEATURE_ROUTE_KEY]["steps"]
            assert stored["import"]["status"] == "done"
            promo = await client.post(
                "/api/auth/guest/promote/email",
                json={"email": new_email, "password": "TestPass123!"},
                headers=headers,
            )
            assert promo.status_code == 200
            new_headers = {"Authorization": f"Bearer {promo.json()['access_token']}"}
            body = await _profile(client, new_headers)
            assert body["is_guest"] is False
            assert body["feature_route"]["steps"]["import"]["status"] == "done"
        finally:
            await _delete_user(guest_id)


# --- current and skip: the clock (D-10, D-11), D-23, guards ----------------------


def _prior_days(count: int) -> list[datetime.date]:
    """`count` distinct days strictly before TODAY."""
    return [TODAY - datetime.timedelta(days=offset) for offset in range(1, count + 1)]


def _day(offset: int) -> datetime.datetime:
    """Pinned instant `offset` days after NOW."""
    return NOW + datetime.timedelta(days=offset)


async def _seed_activity(user_id: int, days: Sequence[datetime.date]) -> None:
    async with db_module.async_session_maker() as session:
        session.add_all([UserActivity(user_id=user_id, activity_date=day) for day in days])
        await session.commit()


async def _set_prompt_state(user_id: int, value: dict[str, Any]) -> None:
    async with db_module.async_session_maker() as session:
        await session.execute(
            text("UPDATE users SET prompt_state = CAST(:v AS jsonb) WHERE id = :uid"),
            {"v": json.dumps(value), "uid": user_id},
        )
        await session.commit()


def _record(status: str, day: datetime.date, with_dot: bool) -> dict[str, Any]:
    return {"status": status, "date": day.isoformat(), "with_dot": with_dot}


@pytest.mark.asyncio
async def test_skip_timeline_applies_exactly_at_since_days_plus_three(pin_now: PinNow) -> None:
    """D-10: current stamped at active day 2 skips on active day 5, not on days 3 or 4."""
    assert FEATURE_ROUTE_SKIP_ACTIVE_DAYS == 3
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            # One prior day, then one activity row per pinned day, so the count at
            # day N is the rows before it plus today.
            await _seed_activity(user_id, [*_prior_days(1), *(_day(i).date() for i in range(3))])
            pin_now(_day(0))
            body = await _profile(client, headers)
            assert body["active_days"] == 2
            stamped = await _post_route(client, headers, "current", "train")
            assert stamped.status_code == 200
            assert stamped.json()["current"] == {"step": "train", "since_days": 2}

            for offset, active in ((1, 3), (2, 4)):
                pin_now(_day(offset))
                assert (await _profile(client, headers))["active_days"] == active
                early = await _post_route(client, headers, "skip", "train")
                assert early.status_code == 200
                assert early.json()["steps"] == {}
                assert early.json()["current"] == {"step": "train", "since_days": 2}

            pin_now(_day(3))
            assert (await _profile(client, headers))["active_days"] == 5
            due = await _post_route(client, headers, "skip", "train")
            assert due.status_code == 200
            assert due.json()["steps"]["train"] == _record("skipped", _day(3).date(), True)
            stored = (await _prompt_state(user_id))[FEATURE_ROUTE_KEY]
            assert stored["steps"]["train"] == _record("skipped", _day(3).date(), True)
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_current_repost_keeps_since_days_and_reads_never_write(pin_now: PinNow) -> None:
    """D-11: re-posting current for the current step keeps since_days; a GET writes nothing."""
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, [*_prior_days(1), *(_day(i).date() for i in range(2))])
            pin_now(_day(0))
            first = await _post_route(client, headers, "current", "train")
            assert first.json()["current"] == {"step": "train", "since_days": 2}
            before = await _prompt_state(user_id)
            # Same day again, and a later day: since_days must not move.
            again = await _post_route(client, headers, "current", "train")
            assert again.status_code == 200
            pin_now(_day(1))
            later = await _post_route(client, headers, "current", "train")
            assert later.json()["current"] == {"step": "train", "since_days": 2}
            for _ in range(2):
                await _profile(client, headers)
            assert await _prompt_state(user_id) == before
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_current_and_skip_transition_rules(pin_now: PinNow) -> None:
    """current on a resolved step is a no-op; current on another step replaces; skip needs current."""
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(8))
            pin_now(NOW)
            assert (await _post_route(client, headers, "done", "import")).status_code == 200
            resolved = await _post_route(client, headers, "current", "import")
            assert resolved.json()["current"] is None

            # skip for a step that is not current is a no-op even when plenty of days passed
            pin_now(_day(10))
            not_current = await _post_route(client, headers, "skip", "bots")
            assert not_current.json()["steps"].keys() == {"import"}

            pin_now(NOW)
            await _post_route(client, headers, "current", "train")
            replaced = await _post_route(client, headers, "current", "bots")
            assert replaced.json()["current"] == {"step": "bots", "since_days": 9}
            assert replaced.json()["steps"].keys() == {"import"}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_done_with_dot_follows_current_and_upgrades_skip(pin_now: PinNow) -> None:
    """D-15: with_dot true only for the current step; a skipped step becomes done on a visit."""
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(1))
            pin_now(NOW)
            await _post_route(client, headers, "current", "train")
            off = await _post_route(client, headers, "done", "import")
            assert off.json()["steps"]["import"]["with_dot"] is False
            on = await _post_route(client, headers, "done", "train")
            assert on.json()["steps"]["train"]["with_dot"] is True

            await _post_route(client, headers, "current", "bots")
            await _seed_activity(user_id, [_day(i).date() for i in range(5)])
            pin_now(_day(4))
            skipped = await _post_route(client, headers, "skip", "bots")
            assert skipped.json()["steps"]["bots"]["status"] == "skipped"
            upgraded = await _post_route(client, headers, "done", "bots")
            assert upgraded.json()["steps"]["bots"]["status"] == "done"
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_guest_stamps_current_and_skips(pin_now: PinNow) -> None:
    """D-19: a guest's current stamp and skip are written like a registered user's."""
    async with _client() as client:
        created = await client.post("/api/auth/guest/create")
        assert created.status_code == 201
        headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
        guest_email = str((await _profile(client, headers))["email"])
        async with db_module.async_session_maker() as session:
            guest_id = (
                (
                    await session.execute(
                        select(User.id).where(User.email == guest_email)  # ty: ignore[invalid-argument-type]  # FastAPI-Users types email as plain str
                    )
                )
                .unique()
                .scalar_one()
            )
        try:
            await _seed_activity(guest_id, [*_prior_days(1), *(_day(i).date() for i in range(4))])
            pin_now(_day(0))
            stamped = await _post_route(client, headers, "current", "train")
            assert stamped.json()["current"] == {"step": "train", "since_days": 2}
            pin_now(_day(3))
            skipped = await _post_route(client, headers, "skip", "train")
            assert skipped.json()["steps"]["train"]["status"] == "skipped"
            stored = (await _prompt_state(guest_id))[FEATURE_ROUTE_KEY]
            assert stored["steps"]["train"]["status"] == "skipped"
        finally:
            await _delete_user(guest_id)


@pytest.mark.asyncio
async def test_impersonation_never_writes_current_done_or_skip(pin_now: PinNow) -> None:
    """Guards: an impersonation token returns the target's view and writes nothing."""
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
            await _seed_activity(target_id, _prior_days(8))
            imp = await client.post(f"/api/admin/impersonate/{target_id}", headers=admin_headers)
            assert imp.status_code == 200
            imp_headers = {"Authorization": f"Bearer {imp.json()['access_token']}"}
            for action in ("current", "done", "skip"):
                resp = await _post_route(client, imp_headers, action, "train")
                assert resp.status_code == 200
                assert resp.json() == {"steps": {}, "current": None}
            assert await _prompt_state(target_id) == {}
        finally:
            await _delete_user(admin_id)
            await _delete_user(target_id)


@pytest.mark.asyncio
async def test_post_validation_and_auth(pin_now: PinNow) -> None:
    """Guards: unknown step, unknown action and an extra body key are 422; no token is 401."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            assert (await _post_route(client, headers, "done", "analysis")).status_code == 422
            assert (await _post_route(client, headers, "reset", "train")).status_code == 422
            extra = await client.post(
                "/api/users/me/feature-route",
                json={"action": "done", "step": "train", "user_id": 1},
                headers=headers,
            )
            assert extra.status_code == 422
            anonymous = await client.post(
                "/api/users/me/feature-route", json={"action": "done", "step": "train"}
            )
            assert anonymous.status_code == 401
            assert await _prompt_state(user_id) == {}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_feedback_state_survives_every_transition(pin_now: PinNow) -> None:
    """Guards: feedback_v1 is byte-identical after done, current and skip."""
    feedback = {"status": "done", "views": 3, "snoozed_until": None}
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, [*_prior_days(1), *(_day(i).date() for i in range(4))])
            await _set_prompt_state(user_id, {"feedback_v1": feedback})
            pin_now(_day(0))
            await _post_route(client, headers, "current", "train")
            assert (await _prompt_state(user_id))["feedback_v1"] == feedback
            await _post_route(client, headers, "done", "import")
            assert (await _prompt_state(user_id))["feedback_v1"] == feedback
            pin_now(_day(3))
            await _post_route(client, headers, "skip", "train")
            assert (await _prompt_state(user_id))["feedback_v1"] == feedback
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_concurrent_posts_are_idempotent(pin_now: PinNow) -> None:
    """Two simultaneous done posts store one record; two current posts store one since_days."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(2))
            # Separate requests, each with its own DB session (never one AsyncSession).
            first, second = await asyncio.gather(
                _post_route(client, headers, "done", "import"),
                _post_route(client, headers, "done", "import"),
            )
            assert first.status_code == second.status_code == 200
            steps = (await _prompt_state(user_id))[FEATURE_ROUTE_KEY]["steps"]
            assert steps == {"import": _record("done", TODAY, False)}

            cur_a, cur_b = await asyncio.gather(
                _post_route(client, headers, "current", "train"),
                _post_route(client, headers, "current", "train"),
            )
            assert cur_a.status_code == cur_b.status_code == 200
            current = (await _prompt_state(user_id))[FEATURE_ROUTE_KEY]["current"]
            assert current == {"step": "train", "since_days": 3}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_corrupt_stored_state_fails_closed(
    pin_now: PinNow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guards: a corrupt stored state gives null on GET and POST, one capture, value unchanged."""
    pin_now(NOW)
    captured: list[BaseException] = []
    monkeypatch.setattr(
        feature_route_service.sentry_sdk, "capture_exception", lambda exc: captured.append(exc)
    )
    corrupt = {
        FEATURE_ROUTE_KEY: {
            "steps": {"import": {"status": "bogus", "date": TODAY.isoformat(), "with_dot": False}}
        }
    }
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _set_prompt_state(user_id, corrupt)
            assert (await _profile(client, headers))["feature_route"] is None
            assert len(captured) == 1
            resp = await _post_route(client, headers, "done", "train")
            assert resp.status_code == 200
            assert resp.json() is None
            assert len(captured) == 2
            assert await _prompt_state(user_id) == corrupt
        finally:
            await _delete_user(user_id)


# --- D-23: deleting all games removes the current stamp ---------------------------

_RELOCK_STATE: dict[str, Any] = {
    FEATURE_ROUTE_KEY: {
        "steps": {
            "import": _record("done", TODAY, False),
            "train": _record("done", TODAY, True),
            "bots": _record("done", TODAY, False),
        },
        "current": {"step": "openings", "since_days": 2},
    },
    "feedback_v1": {"status": "done", "views": 1},
}


@pytest.mark.asyncio
async def test_delete_all_games_removes_current_stamp_and_restarts_the_clock(
    pin_now: PinNow,
) -> None:
    """D-23: DELETE /imports/games drops `current`; a skip is refused, a fresh stamp restarts."""
    pin_now(NOW)
    async with _client() as client:
        user_id, headers = await _register(client)
        try:
            await _seed_activity(user_id, _prior_days(1))
            await _set_prompt_state(user_id, _RELOCK_STATE)
            assert (await client.delete("/api/imports/games", headers=headers)).status_code == 200

            stored = await _prompt_state(user_id)
            route = stored[FEATURE_ROUTE_KEY]
            assert "current" not in route
            assert route["steps"] == _RELOCK_STATE[FEATURE_ROUTE_KEY]["steps"]
            assert stored["feedback_v1"] == _RELOCK_STATE["feedback_v1"]

            # Days later the old stamp (since_days 2) would be long expired (active_days 6).
            await _seed_activity(user_id, [_day(i).date() for i in range(5)])
            pin_now(_day(5))
            assert (await _profile(client, headers))["active_days"] == 7
            refused = await _post_route(client, headers, "skip", "openings")
            assert refused.status_code == 200
            assert "openings" not in refused.json()["steps"]
            assert (await _prompt_state(user_id))[FEATURE_ROUTE_KEY]["steps"].keys() == {
                "import",
                "train",
                "bots",
            }

            # On unlock the client stamps afresh: the clock restarts at today's count.
            fresh = await _post_route(client, headers, "current", "openings")
            assert fresh.json()["current"] == {"step": "openings", "since_days": 7}
        finally:
            await _delete_user(user_id)


@pytest.mark.asyncio
async def test_delete_all_games_leaves_rows_without_a_stamp_untouched(pin_now: PinNow) -> None:
    """D-23: no feature_route key stays absent (no JSON null); no current key stays unchanged."""
    pin_now(NOW)
    async with _client() as client:
        no_route_id, no_route_headers = await _register(client)
        no_stamp_id, no_stamp_headers = await _register(client)
        try:
            await _set_prompt_state(no_route_id, {"feedback_v1": {"status": "done"}})
            no_stamp = {FEATURE_ROUTE_KEY: {"steps": {"import": _record("done", TODAY, False)}}}
            await _set_prompt_state(no_stamp_id, no_stamp)
            for headers in (no_route_headers, no_stamp_headers):
                assert (
                    await client.delete("/api/imports/games", headers=headers)
                ).status_code == 200
            assert await _prompt_state(no_route_id) == {"feedback_v1": {"status": "done"}}
            assert await _prompt_state(no_stamp_id) == no_stamp
        finally:
            await _delete_user(no_route_id)
            await _delete_user(no_stamp_id)


@pytest.mark.asyncio
async def test_delete_all_games_for_user_clears_the_stamp_for_every_caller(
    db_session: AsyncSession,
) -> None:
    """D-23: the repository function itself clears it (guest purge and reimport script path)."""
    user = await _make_user(db_session)
    user.prompt_state = {
        FEATURE_ROUTE_KEY: {"steps": {}, "current": {"step": "openings", "since_days": 4}}
    }
    await db_session.flush()
    await game_repository.delete_all_games_for_user(db_session, user.id)
    stored = await _stored_prompt_state(db_session, user.id)
    assert stored == {FEATURE_ROUTE_KEY: {"steps": {}}}
