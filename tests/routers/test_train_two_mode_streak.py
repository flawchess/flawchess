"""HTTP tests for the both-modes streak rule (Phase 251, D-02).

The streak ticks on a scheduled day only when every mode with a session size above 0 has a
completed session dated that day. These tests drive the rule through the real routes: compose
and solve today's puzzle session, then read `GET /train/progress`.

Covers:
  - test_day_completion_puzzles_only_waits_for_blunder_check: a streak holder who completes
    today's puzzles while blunder check (size 6) is pending keeps the same streak_count.
  - test_day_completion_blunder_check_off_ticks_on_puzzles: the same flow with blunder check at
    0 ticks the streak by exactly one.

Every non-guest Game insert is deleted in `finally` (the eval lottery is global).
"""

from __future__ import annotations

import datetime

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.drill_session import DrillSession
from app.models.train_settings import TrainSettings
from app.repositories import train_repository
from app.services import sharp_filler
from app.services.sharp_filler import SharpPuzzle
from app.services.train_scheduler import (
    ALL_WEEKDAYS_MASK,
    DEFAULT_BLUNDER_CHECK_PER_SESSION,
    DEFAULT_PUZZLES_PER_SESSION,
    DEFAULT_TIMEZONE,
)
from tests.blunder_check_seed import register_user

_SESSIONS = "/api/train/sessions"
_PROGRESS = "/api/train/progress"

_STARTING_STREAK = 3
_STARTING_SHIELD = 2

# A small deterministic sharp-filler fixture (sibling to tests/routers/test_train.py's), so a
# user with no games composes a real warm-up session of DEFAULT_PUZZLES_PER_SESSION puzzles.
_SHARP_PUZZLES: tuple[SharpPuzzle, ...] = tuple(
    SharpPuzzle(
        puzzle_id=f"sharp-two-mode-{i:02d}",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        first_move_uci="e2e4",
        solution_uci="d2d4",
        ply=0,
        side_to_move="white",
        motif="Fork",
        rating=1200,
        themes="fork short",
    )
    for i in range(10)
)


@pytest.fixture(autouse=True)
def _sharp_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install the deterministic sharp fixture (both bindings, see test_train.py)."""
    ordered = tuple(sorted(_SHARP_PUZZLES, key=lambda p: p.puzzle_id))
    by_id = {p.puzzle_id: p for p in ordered}
    monkeypatch.setattr(sharp_filler, "SHARP_SET", ordered)
    monkeypatch.setattr(sharp_filler, "SHARP_SET_BY_ID", by_id)
    monkeypatch.setattr(train_repository, "SHARP_SET_BY_ID", by_id)


async def _seed_streak_holder(test_engine, user_id: int, *, bc_size: int) -> None:
    """A streak holder settled through yesterday with the given blunder-check size.

    `blunder_check_streak_from` is NULL (the both-modes rule applies on every day) and the
    eligibility watermark sits at yesterday so today's day is judged normally.
    """
    today = datetime.datetime.now(datetime.timezone.utc).date()
    yesterday = today - datetime.timedelta(days=1)
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        stmt = pg_insert(TrainSettings).values(
            user_id=user_id,
            timezone=DEFAULT_TIMEZONE,
            weekday_mask=ALL_WEEKDAYS_MASK,
            puzzles_per_session=DEFAULT_PUZZLES_PER_SESSION,
            streak_count=_STARTING_STREAK,
            shield_level=_STARTING_SHIELD,
            streak_settled_through=yesterday,
            pool_eligible_since=yesterday,
            blunder_check_per_session=bc_size,
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "streak_count": _STARTING_STREAK,
                    "shield_level": _STARTING_SHIELD,
                    "streak_settled_through": yesterday,
                    "pool_eligible_since": yesterday,
                    "blunder_check_per_session": bc_size,
                },
            )
        )


async def _compose_and_solve_puzzles(token: str, test_engine) -> int:
    """Compose today's puzzle session over HTTP and solve every puzzle. Returns the session id."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        compose = await client.post(_SESSIONS, headers=headers)
        assert compose.status_code == 200, compose.text
        body = compose.json()
        session_id = int(body["session_id"])
        last: dict[str, object] = {}
        for position in range(body["puzzle_count"]):
            solve = await client.post(
                f"{_SESSIONS}/{session_id}/solve",
                headers=headers,
                json={
                    "position": position,
                    "guess": "critical",
                    "played_move": "e2e4",
                    "move_quality": "good",
                },
            )
            assert solve.status_code == 200, solve.text
            last = solve.json()
        assert last["session_complete"] is True
    return session_id


async def _progress(token: str) -> dict[str, object]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(_PROGRESS, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


async def _delete_drill_sessions(test_engine, session_ids: list[int]) -> None:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        await session.execute(delete(DrillSession).where(DrillSession.id.in_(session_ids)))


@pytest.mark.asyncio
async def test_day_completion_puzzles_only_waits_for_blunder_check(test_engine) -> None:
    """Tracer: completing today's puzzles with blunder check pending leaves the streak alone."""
    user_id, token = await register_user("two-mode-wait", beta=False, test_engine=test_engine)
    await _seed_streak_holder(test_engine, user_id, bc_size=DEFAULT_BLUNDER_CHECK_PER_SESSION)
    session_ids: list[int] = []
    try:
        session_ids.append(await _compose_and_solve_puzzles(token, test_engine))
        progress = await _progress(token)
        assert progress["session_streak_count"] == _STARTING_STREAK
        assert progress["shield_level"] == _STARTING_SHIELD
    finally:
        await _delete_drill_sessions(test_engine, session_ids)


@pytest.mark.asyncio
async def test_day_completion_blunder_check_off_ticks_on_puzzles(test_engine) -> None:
    """With blunder check at 0 the puzzle-only completion ticks the streak by exactly one."""
    user_id, token = await register_user("two-mode-off", beta=False, test_engine=test_engine)
    await _seed_streak_holder(test_engine, user_id, bc_size=0)
    session_ids: list[int] = []
    try:
        session_ids.append(await _compose_and_solve_puzzles(token, test_engine))
        progress = await _progress(token)
        assert progress["session_streak_count"] == _STARTING_STREAK + 1
        assert progress["shield_level"] == _STARTING_SHIELD + 1
    finally:
        await _delete_drill_sessions(test_engine, session_ids)
