"""Tests for the phase 255 feature-route seed migration (data-only).

Regression suite for the migration that gives every users row existing at deploy the nine
launch step IDs as done (D-16, D-22) and leaves rows created afterwards at ``{}``.

Structure mirrors tests/test_migration_240_reveal_tour_stage.py: each test drives Alembic via
asyncio.to_thread against this run's private per-run database, downgrades to the previous
revision, asserts the data shape, then upgrades back to head. Assertions only touch the
dedicated user IDs 999_700-999_703, because the seed also rewrites other rows in the worker
database.
"""

import asyncio
import json
from typing import Any

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text

from app.schemas.feature_route import FeatureRouteState

TARGET_REVISION: str = "head"
BASE_REVISION: str = "a7d2c9e1b254"  # down_revision of the feature-route seed migration

_USER_REGISTERED: int = 999_700
_USER_GUEST: int = 999_701
_USER_FEEDBACK: int = 999_702
_USER_HAS_ROUTE: int = 999_703
_ALL_USERS: tuple[int, ...] = (_USER_REGISTERED, _USER_GUEST, _USER_FEEDBACK, _USER_HAS_ROUTE)

# Hard-coded twin of the migration's list; the test pins the D-06 order and count.
_LAUNCH_STEP_IDS: tuple[str, ...] = (
    "import",
    "train",
    "bots",
    "openings",
    "openings-played-as",
    "openings-filters",
    "openings-stats",
    "endgames",
    "library-stats",
)

_FEEDBACK: dict[str, Any] = {"status": "done", "views": 2}
_EXISTING_ROUTE: dict[str, Any] = {
    "steps": {"import": {"status": "done", "date": "2026-01-02", "with_dot": True}}
}

pytestmark = pytest.mark.asyncio


def _make_alembic_cfg() -> AlembicConfig:
    """Build an AlembicConfig for this run's per-run test database."""
    from app.core.config import settings

    cfg = AlembicConfig("alembic.ini")
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


async def _run_upgrade(revision: str = TARGET_REVISION) -> None:
    await asyncio.to_thread(alembic_command.upgrade, _make_alembic_cfg(), revision)


async def _run_downgrade(revision: str = BASE_REVISION) -> None:
    await asyncio.to_thread(alembic_command.downgrade, _make_alembic_cfg(), revision)


async def _insert_user(
    engine, user_id: int, *, is_guest: bool = False, prompt_state: dict[str, Any] | None = None
) -> None:
    """Insert a user; prompt_state None keeps the server default ({})."""
    async with engine.begin() as conn:
        if prompt_state is None:
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, "
                    "is_verified, is_guest) "
                    "VALUES (:id, :email, 'x', true, false, false, :guest)"
                ),
                {
                    "id": user_id,
                    "email": f"migration255-test-{user_id}@example.com",
                    "guest": is_guest,
                },
            )
            return
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, "
                "is_verified, is_guest, prompt_state) "
                "VALUES (:id, :email, 'x', true, false, false, :guest, CAST(:ps AS jsonb))"
            ),
            {
                "id": user_id,
                "email": f"migration255-test-{user_id}@example.com",
                "guest": is_guest,
                "ps": json.dumps(prompt_state),
            },
        )


async def _prompt_state(engine, user_id: int) -> dict[str, Any]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT prompt_state FROM users WHERE id = :uid"), {"uid": user_id}
        )
        return dict(result.scalar_one())


async def _cleanup(engine) -> None:
    async with engine.begin() as conn:
        for user_id in _ALL_USERS:
            await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})


async def _insert_all_at_base(engine) -> None:
    await _insert_user(engine, _USER_REGISTERED)
    await _insert_user(engine, _USER_GUEST, is_guest=True)
    await _insert_user(engine, _USER_FEEDBACK, prompt_state={"feedback_v1": _FEEDBACK})
    await _insert_user(engine, _USER_HAS_ROUTE, prompt_state={"feature_route": _EXISTING_ROUTE})


def _assert_seeded(stored: dict[str, Any]) -> None:
    route = stored["feature_route"]
    assert "current" not in route
    # jsonb does not keep key order, so compare as a set (and pin the count).
    assert len(route["steps"]) == len(_LAUNCH_STEP_IDS) == 9
    assert set(route["steps"]) == set(_LAUNCH_STEP_IDS)
    for record in route["steps"].values():
        assert record["status"] == "done"
        assert record["with_dot"] is False
    # The seeded object must be a valid stored route state.
    assert set(FeatureRouteState.model_validate(route).steps) == set(_LAUNCH_STEP_IDS)


async def test_seeds_every_existing_row_with_the_nine_launch_steps(test_engine) -> None:
    """Registered, guest and feedback-holding rows get exactly the nine IDs as done; a row that
    already holds a route is left alone and feedback_v1 survives."""
    await _run_downgrade(BASE_REVISION)
    try:
        await _insert_all_at_base(test_engine)
        await _run_upgrade(TARGET_REVISION)

        registered = await _prompt_state(test_engine, _USER_REGISTERED)
        guest = await _prompt_state(test_engine, _USER_GUEST)
        feedback = await _prompt_state(test_engine, _USER_FEEDBACK)
        _assert_seeded(registered)
        _assert_seeded(guest)
        _assert_seeded(feedback)
        assert feedback["feedback_v1"] == _FEEDBACK
        assert set(registered) == {"feature_route"}
        assert await _prompt_state(test_engine, _USER_HAS_ROUTE) == {
            "feature_route": _EXISTING_ROUTE
        }
    finally:
        await _run_upgrade(TARGET_REVISION)
        await _cleanup(test_engine)


async def test_upgrade_is_idempotent(test_engine) -> None:
    """Re-running the seed statement over seeded rows changes nothing."""
    await _run_downgrade(BASE_REVISION)
    try:
        await _insert_user(test_engine, _USER_REGISTERED)
        await _run_upgrade(TARGET_REVISION)
        first = await _prompt_state(test_engine, _USER_REGISTERED)
        await _run_downgrade(BASE_REVISION)
        # Put the seeded route back by hand, then upgrade again over a row that has it.
        async with test_engine.begin() as conn:
            await conn.execute(
                text("UPDATE users SET prompt_state = CAST(:ps AS jsonb) WHERE id = :uid"),
                {"ps": json.dumps(first), "uid": _USER_REGISTERED},
            )
        await _run_upgrade(TARGET_REVISION)
        assert await _prompt_state(test_engine, _USER_REGISTERED) == first
    finally:
        await _run_upgrade(TARGET_REVISION)
        await _cleanup(test_engine)


async def test_downgrade_removes_only_the_route_key(test_engine) -> None:
    """After a downgrade feedback_v1 stays, feature_route is gone, and an empty row is {}."""
    await _run_downgrade(BASE_REVISION)
    try:
        await _insert_all_at_base(test_engine)
        await _run_upgrade(TARGET_REVISION)
        await _run_downgrade(BASE_REVISION)

        assert await _prompt_state(test_engine, _USER_FEEDBACK) == {"feedback_v1": _FEEDBACK}
        assert await _prompt_state(test_engine, _USER_REGISTERED) == {}
        assert await _prompt_state(test_engine, _USER_HAS_ROUTE) == {}
    finally:
        await _run_upgrade(TARGET_REVISION)
        await _cleanup(test_engine)


async def test_row_created_after_the_seed_starts_empty(test_engine) -> None:
    """A user inserted at head holds {} and walks the route (a post-launch step is absent)."""
    await _run_upgrade(TARGET_REVISION)
    try:
        await _insert_user(test_engine, _USER_REGISTERED)
        assert await _prompt_state(test_engine, _USER_REGISTERED) == {}
    finally:
        await _cleanup(test_engine)
