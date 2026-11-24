"""HTTP tests for the two-mode settings PUT (Phase 251, D-04, D-05, D-07, D-21).

Covers:
  - test_settings_bc_off_after_puzzles_done_ticks_streak: the tracer. A streak holder finishes
    today's puzzles (blunder check at 6, no tick), then sets blunder check to 0: the response
    echoes 0 and the streak ticks by exactly one.
  - test_settings_both_modes_off_422_row_unchanged: both sizes 0 answers 422 and writes nothing.
  - test_settings_resolved_both_off_422: puzzles 0 with the blunder-check key omitted while the
    stored size is 0 resolves to both-off and answers 422 (the service-level check).
  - test_settings_old_pwa_body_keeps_stored_values: a body without the two new keys answers 200
    and keeps the stored size and level.
  - test_settings_bc_amount_change_nulls_notice: changing the amount clears the launch notice;
    re-sending the same amount keeps it.
  - test_settings_bc_size_and_level_round_trip: PUT/GET round-trip both new fields.
  - test_settings_out_of_range_sizes_422: 51 puzzles and 31 blunder-check windows are rejected.

Every test registers its own user (non-beta: the settings routes are open to everyone).
"""

from __future__ import annotations

import datetime

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.train_settings import TrainSettings
from app.services.train_scheduler import DEFAULT_BLUNDER_CHECK_PER_SESSION
from tests.blunder_check_seed import register_user
from tests.routers.test_train_two_mode_streak import (
    _compose_and_solve_puzzles,
    _delete_drill_sessions,
    _progress,
    _seed_streak_holder,
)

_SETTINGS = "/api/train/settings"
_STARTING_STREAK = 3
_PUZZLES_SIZE = 6
_FAR_OUT_OF_RANGE_PUZZLES = 51
_FAR_OUT_OF_RANGE_BC = 31
_STORED_BC_SIZE = 4


@pytest.fixture(autouse=True)
def _filled_sessions(foreign_filler_pool: None) -> None:
    """A user with no games still composes a full puzzle session: the committed stranger pool
    (tests/conftest.py) is the only filler."""


def _body(**overrides: object) -> dict[str, object]:
    """A full old-style settings body; keyword overrides replace or add keys."""
    body: dict[str, object] = {
        "timezone": "UTC",
        "weekday_mask": 127,
        "puzzles_per_session": _PUZZLES_SIZE,
        "reminder_enabled": False,
        "reminder_hour": 18,
        "reminder_intent_at": None,
    }
    body.update(overrides)
    return body


async def _put(token: str, body: dict[str, object]) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.put(_SETTINGS, headers={"Authorization": f"Bearer {token}"}, json=body)


async def _get(token: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(_SETTINGS, headers={"Authorization": f"Bearer {token}"})


async def _stored_row(test_engine, user_id: int) -> TrainSettings:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        return (
            await session.execute(select(TrainSettings).where(TrainSettings.user_id == user_id))
        ).scalar_one()


async def _update_row(test_engine, user_id: int, **values: object) -> None:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        await session.execute(
            update(TrainSettings).where(TrainSettings.user_id == user_id).values(**values)
        )


@pytest.mark.asyncio
async def test_settings_bc_off_after_puzzles_done_ticks_streak(test_engine) -> None:
    """Tracer: puzzles done with blunder check pending, then blunder check -> 0 ticks once."""
    user_id, token = await register_user("settings-bc-off", beta=False, test_engine=test_engine)
    await _seed_streak_holder(test_engine, user_id, bc_size=DEFAULT_BLUNDER_CHECK_PER_SESSION)
    session_ids: list[int] = []
    try:
        session_ids.append(await _compose_and_solve_puzzles(token, test_engine))
        assert (await _progress(token))["session_streak_count"] == _STARTING_STREAK

        resp = await _put(token, _body(blunder_check_per_session=0))

        assert resp.status_code == 200, resp.text
        assert resp.json()["blunder_check_per_session"] == 0
        assert (await _progress(token))["session_streak_count"] == _STARTING_STREAK + 1

        # A second identical PUT must not credit again (apply_day_completion is idempotent).
        again = await _put(token, _body(blunder_check_per_session=0))
        assert again.status_code == 200, again.text
        assert (await _progress(token))["session_streak_count"] == _STARTING_STREAK + 1
    finally:
        await _delete_drill_sessions(test_engine, session_ids)


@pytest.mark.asyncio
async def test_settings_both_modes_off_422_row_unchanged(test_engine) -> None:
    """D-05: both sizes 0 answers 422, never a 500 from the DB CHECK, and the row is unchanged."""
    user_id, token = await register_user("settings-both-off", beta=False, test_engine=test_engine)
    await _seed_streak_holder(test_engine, user_id, bc_size=_STORED_BC_SIZE)

    resp = await _put(token, _body(puzzles_per_session=0, blunder_check_per_session=0))

    assert resp.status_code == 422, resp.text
    row = await _stored_row(test_engine, user_id)
    assert row.puzzles_per_session == _PUZZLES_SIZE
    assert row.blunder_check_per_session == _STORED_BC_SIZE


@pytest.mark.asyncio
async def test_settings_resolved_both_off_422(test_engine) -> None:
    """Puzzles 0 with the key omitted while the stored blunder-check size is 0 answers 422."""
    user_id, token = await register_user("settings-resolved", beta=False, test_engine=test_engine)
    await _seed_streak_holder(test_engine, user_id, bc_size=0)

    resp = await _put(token, _body(puzzles_per_session=0))

    assert resp.status_code == 422, resp.text
    row = await _stored_row(test_engine, user_id)
    assert row.puzzles_per_session == _PUZZLES_SIZE


@pytest.mark.asyncio
async def test_settings_old_pwa_body_keeps_stored_values(test_engine) -> None:
    """D-07: a body without the two new keys saves (200) and keeps the stored size and level."""
    user_id, token = await register_user("settings-old-pwa", beta=False, test_engine=test_engine)
    await _seed_streak_holder(test_engine, user_id, bc_size=_STORED_BC_SIZE)
    await _update_row(test_engine, user_id, blunder_check_level="advanced")

    resp = await _put(token, _body(puzzles_per_session=9))

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["puzzles_per_session"] == 9
    assert payload["blunder_check_per_session"] == _STORED_BC_SIZE
    assert payload["blunder_check_level"] == "advanced"
    row = await _stored_row(test_engine, user_id)
    assert row.blunder_check_per_session == _STORED_BC_SIZE
    assert row.blunder_check_level == "advanced"


@pytest.mark.asyncio
async def test_settings_bc_amount_change_nulls_notice(test_engine) -> None:
    """D-21: a changed blunder-check amount clears the launch notice; the same amount keeps it."""
    user_id, token = await register_user("settings-notice", beta=False, test_engine=test_engine)
    await _seed_streak_holder(test_engine, user_id, bc_size=_STORED_BC_SIZE)
    stamp = datetime.datetime(2026, 11, 18, 12, tzinfo=datetime.timezone.utc)
    await _update_row(test_engine, user_id, blunder_check_notice_from=stamp)

    same = await _put(token, _body(blunder_check_per_session=_STORED_BC_SIZE))
    assert same.status_code == 200, same.text
    assert (await _stored_row(test_engine, user_id)).blunder_check_notice_from == stamp

    changed = await _put(token, _body(blunder_check_per_session=_STORED_BC_SIZE + 1))
    assert changed.status_code == 200, changed.text
    assert (await _stored_row(test_engine, user_id)).blunder_check_notice_from is None


@pytest.mark.asyncio
async def test_settings_bc_size_and_level_round_trip(test_engine) -> None:
    """D-07: PUT then GET round-trip blunder_check_per_session and blunder_check_level."""
    _user_id, token = await register_user("settings-round", beta=False, test_engine=test_engine)

    put = await _put(token, _body(blunder_check_per_session=11, blunder_check_level="beginner"))

    assert put.status_code == 200, put.text
    assert put.json()["blunder_check_per_session"] == 11
    assert put.json()["blunder_check_level"] == "beginner"
    assert (await _get(token)).json() == put.json()


@pytest.mark.asyncio
async def test_settings_out_of_range_sizes_422(test_engine) -> None:
    """T-251-12: sizes beyond the documented caps are rejected at the schema."""
    _user_id, token = await register_user("settings-range", beta=False, test_engine=test_engine)

    too_many_puzzles = await _put(token, _body(puzzles_per_session=_FAR_OUT_OF_RANGE_PUZZLES))
    too_many_bc = await _put(token, _body(blunder_check_per_session=_FAR_OUT_OF_RANGE_BC))
    bad_level = await _put(token, _body(blunder_check_level="grandmaster"))

    assert too_many_puzzles.status_code == 422
    assert too_many_bc.status_code == 422
    assert bad_level.status_code == 422
