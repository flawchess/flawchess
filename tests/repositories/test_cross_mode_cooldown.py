"""Cross-mode cooldown tests (Phase 251 D-16, plan 03 task 2).

A flaw served in either Train mode is ineligible in the other for CROSS_MODE_COOLDOWN_DAYS local
days after its last serve, in both directions:

- puzzle side: a flaw in a blunder-check window dated inside the cooldown drops out of
  `_select_candidates` (due and pool statements) and out of `get_waiting_puzzle_count`, without any
  `drill_items.due_date` write (A7), so it resurfaces once the cooldown ends
- blunder-check side: a flaw in a drill SR row of a session dated inside the cooldown is not
  composed as an own blunder window

Puzzle-side tests run in the rollback-scoped `db_session`; blunder-check-side tests need a fully
judged game (committed rows, deleted in `finally`).
"""

from __future__ import annotations

import datetime
import itertools
import random

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.blunder_check import (
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
)
from app.models.drill_item import DrillItem, DrillStatus
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillSolve, DrillSource
from app.models.train_settings import TrainSettings
from app.repositories import train_repository
from app.services import blunder_check_selection, blunder_check_service, sharp_filler
from app.services.blunder_check_rules import SlotPlan, WindowShape
from app.services.train_scheduler import CROSS_MODE_COOLDOWN_DAYS
from tests.blunder_check_seed import (
    SeedBlunder,
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    register_user,
    seed_judged_game,
    with_user_blunder,
)
from tests.conftest import ensure_test_user
from tests.repositories.test_train_repository import _seed_flaw_game

_USER_ID = 93300
_NOW = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc)
_TODAY = datetime.date(2026, 1, 15)
_FLAW_PLY = 2
# Inside / outside the cooldown, derived from the production constant so a tuning change moves them.
_INSIDE_DAYS = CROSS_MODE_COOLDOWN_DAYS - 5
_OUTSIDE_DAYS = CROSS_MODE_COOLDOWN_DAYS + 1


@pytest.fixture(autouse=True)
def _empty_sharp_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """No sharp fillers: a composed session holds exactly the SR material seeded here."""
    monkeypatch.setattr(sharp_filler, "SHARP_SET", ())
    monkeypatch.setattr(sharp_filler, "SHARP_SET_BY_ID", {})
    monkeypatch.setattr(train_repository, "SHARP_SET_BY_ID", {})


# ---------------------------------------------------------------------------
# Puzzle side
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def puzzle_user(db_session: AsyncSession) -> int:
    await ensure_test_user(db_session, _USER_ID)
    await train_repository.upsert_settings(
        db_session,
        user_id=_USER_ID,
        timezone="UTC",
        weekday_mask=0,
        puzzles_per_session=6,
        reminder_enabled=False,
        reminder_hour=18,
        reminder_intent_at=None,
        now_utc=_NOW,
    )
    return _USER_ID


async def _seed_due_item(db_session: AsyncSession, label: str) -> int:
    """A game with one qualifying flaw and an ACTIVE drill item due today; returns the game id."""
    game_id = await _seed_flaw_game(db_session, _USER_ID, label, ply=_FLAW_PLY)
    db_session.add(
        DrillItem(
            user_id=_USER_ID,
            game_id=game_id,
            ply=_FLAW_PLY,
            status=DrillStatus.ACTIVE,
            streak=0,
            due_date=_TODAY,
            fail_count=0,
            ever_correct=False,
        )
    )
    await db_session.flush()
    return game_id


async def _seed_bc_serve(
    db_session: AsyncSession, *, game_id: int, ply: int, days_ago: int
) -> None:
    """A blunder-check session dated `days_ago` local days back with one window on (game, ply)."""
    session_date = _TODAY - datetime.timedelta(days=days_ago)
    header = BlunderCheckSession(
        user_id=_USER_ID,
        status="completed",
        window_count=1,
        session_date=session_date,
        expires_on=session_date + datetime.timedelta(days=1),
    )
    db_session.add(header)
    await db_session.flush()
    db_session.add(
        BlunderCheckWindow(
            session_id=header.id,
            position=0,
            user_id=_USER_ID,
            game_id=game_id,
            is_own=True,
            window_length=3,
            blunder_position=1,
            first_ply=ply,
            blunder_ply=ply,
            window_case=int(WindowCase.ALLOWED),
            start_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            move_ucis="e2e4",
            lead_in_plies=0,
            points_possible=3,
        )
    )
    await db_session.flush()


async def _composed_pairs(db_session: AsyncSession, session_id: int) -> set[tuple[int, int]]:
    rows = (
        await db_session.execute(
            select(DrillSolve.game_id, DrillSolve.ply).where(
                DrillSolve.session_id == session_id, DrillSolve.source == DrillSource.SR_ITEM
            )
        )
    ).all()
    return {(game_id, ply) for game_id, ply in rows}


async def _due_date(db_session: AsyncSession, game_id: int) -> datetime.date:
    return (
        await db_session.execute(
            select(DrillItem.due_date).where(
                DrillItem.user_id == _USER_ID,
                DrillItem.game_id == game_id,
                DrillItem.ply == _FLAW_PLY,
            )
        )
    ).scalar_one()


@pytest.mark.asyncio
async def test_cooldown_bc_serve_hides_due_puzzle(db_session: AsyncSession, puzzle_user) -> None:
    """A due item served in a recent blunder-check window leaves composition and the count."""
    cooled_game = await _seed_due_item(db_session, "cool-hidden")
    control_game = await _seed_due_item(db_session, "cool-control")
    await _seed_bc_serve(db_session, game_id=cooled_game, ply=_FLAW_PLY, days_ago=_INSIDE_DAYS)
    settings_row = await train_repository.get_or_create_settings(db_session, user_id=_USER_ID)

    waiting = await train_repository.get_waiting_puzzle_count(
        db_session, user_id=_USER_ID, settings_row=settings_row, today=_TODAY
    )
    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert composed.session_id is not None
    assert await _composed_pairs(db_session, composed.session_id) == {(control_game, _FLAW_PLY)}
    assert waiting == 1
    assert await _due_date(db_session, cooled_game) == _TODAY  # A7: never written


@pytest.mark.asyncio
async def test_cooldown_due_puzzle_resurfaces_after_window(
    db_session: AsyncSession, puzzle_user
) -> None:
    """The same item with the blunder-check serve outside the cooldown is composed again."""
    cooled_game = await _seed_due_item(db_session, "cool-resurface")
    control_game = await _seed_due_item(db_session, "cool-resurface-control")
    await _seed_bc_serve(db_session, game_id=cooled_game, ply=_FLAW_PLY, days_ago=_OUTSIDE_DAYS)

    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert composed.session_id is not None
    assert await _composed_pairs(db_session, composed.session_id) == {
        (cooled_game, _FLAW_PLY),
        (control_game, _FLAW_PLY),
    }
    assert await _due_date(db_session, cooled_game) == _TODAY


@pytest.mark.asyncio
async def test_cooldown_hides_untracked_pool_flaw(db_session: AsyncSession, puzzle_user) -> None:
    """A fresh pool flaw (no drill item yet) served in blunder check is hidden as well."""
    cooled_game = await _seed_flaw_game(db_session, _USER_ID, "cool-pool-hidden", ply=_FLAW_PLY)
    open_game = await _seed_flaw_game(db_session, _USER_ID, "cool-pool-open", ply=_FLAW_PLY)
    await _seed_bc_serve(db_session, game_id=cooled_game, ply=_FLAW_PLY, days_ago=_INSIDE_DAYS)
    settings_row = await train_repository.get_or_create_settings(db_session, user_id=_USER_ID)

    waiting = await train_repository.get_waiting_puzzle_count(
        db_session, user_id=_USER_ID, settings_row=settings_row, today=_TODAY
    )
    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert composed.session_id is not None
    assert await _composed_pairs(db_session, composed.session_id) == {(open_game, _FLAW_PLY)}
    assert waiting == 1


@pytest.mark.asyncio
async def test_cooldown_waiting_count_mirrors_composition(
    db_session: AsyncSession, puzzle_user
) -> None:
    """With cooled due and pool material present, the count equals what composition serves."""
    cooled_due = await _seed_due_item(db_session, "cool-mirror-due")
    await _seed_due_item(db_session, "cool-mirror-due-open")
    cooled_pool = await _seed_flaw_game(db_session, _USER_ID, "cool-mirror-pool", ply=_FLAW_PLY)
    await _seed_flaw_game(db_session, _USER_ID, "cool-mirror-pool-open", ply=_FLAW_PLY)
    await _seed_bc_serve(db_session, game_id=cooled_due, ply=_FLAW_PLY, days_ago=_INSIDE_DAYS)
    await _seed_bc_serve(db_session, game_id=cooled_pool, ply=_FLAW_PLY, days_ago=0)
    settings_row = await train_repository.get_or_create_settings(db_session, user_id=_USER_ID)

    waiting = await train_repository.get_waiting_puzzle_count(
        db_session, user_id=_USER_ID, settings_row=settings_row, today=_TODAY
    )
    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert composed.session_id is not None
    served = await _composed_pairs(db_session, composed.session_id)
    assert len(served) == 2
    assert waiting == len(served)


@pytest.mark.asyncio
async def test_cooldown_pool_flags_unaffected(db_session: AsyncSession, puzzle_user) -> None:
    """The cooldown is not part of pool eligibility: cooled-only material still counts as material."""
    cooled_game = await _seed_flaw_game(db_session, _USER_ID, "cool-flags", ply=_FLAW_PLY)
    before = await train_repository._material_flags(db_session, user_id=_USER_ID)
    await _seed_bc_serve(db_session, game_id=cooled_game, ply=_FLAW_PLY, days_ago=_INSIDE_DAYS)
    after = await train_repository._material_flags(db_session, user_id=_USER_ID)

    assert before == after == (False, True)


# ---------------------------------------------------------------------------
# Blunder-check side
# ---------------------------------------------------------------------------

_BC_BLUNDER_PLY = 40  # white user; 20 clean user moves precede it
_BC_DROP_CP = 600
_BC_ROWS = 61


def _force_own_blunder_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every slot is an own blunder window; the cooldown, not the shape mix, decides the result."""
    shape = WindowShape(3, 1)
    monkeypatch.setattr(
        blunder_check_selection, "draw_slot_plan", lambda rng: SlotPlan("own", shape)
    )
    monkeypatch.setattr(blunder_check_selection, "draw_blunder_shape", lambda rng: shape)
    monkeypatch.setattr(blunder_check_selection, "draw_herring_shape", lambda rng: shape)
    monkeypatch.setattr(blunder_check_selection, "new_session_rng", lambda: random.Random(1))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("days_ago", "expect_window"),
    [(_INSIDE_DAYS, False), (_OUTSIDE_DAYS, True)],
    ids=["served_as_puzzle_inside_cooldown", "served_as_puzzle_outside_cooldown"],
)
async def test_cooldown_puzzle_serve_hides_bc_own_blunder(
    test_engine, monkeypatch: pytest.MonkeyPatch, days_ago: int, expect_window: bool
) -> None:
    """An own blunder in a drill SR row of a recent puzzle session is not composed in blunder check."""
    _force_own_blunder_slots(monkeypatch)
    user_id, _ = await register_user("bc-cooldown", beta=False, test_engine=test_engine)
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    evals = with_user_blunder(flat_evals(_BC_ROWS, 0), _BC_BLUNDER_PLY, _BC_DROP_CP)
    game_id = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=_BC_BLUNDER_PLY)],
    )
    drill_session_id: int | None = None
    bc_session_id: int | None = None
    try:
        async with maker() as session:
            async with session.begin():
                session.add(TrainSettings(user_id=user_id, timezone="UTC"))
                served_on = _TODAY - datetime.timedelta(days=days_ago)
                header = DrillSession(
                    user_id=user_id,
                    session_date=served_on,
                    status="completed",
                    puzzle_count=1,
                    expires_on=served_on + datetime.timedelta(days=1),
                )
                session.add(header)
                await session.flush()
                drill_session_id = header.id
                session.add(
                    DrillSolve(
                        session_id=header.id,
                        position=0,
                        user_id=user_id,
                        game_id=game_id,
                        ply=_BC_BLUNDER_PLY,
                        source=DrillSource.SR_ITEM,
                    )
                )
        async with maker() as session:
            progress = await blunder_check_service.compose_or_resume(
                session, user_id=user_id, now_utc=_NOW
            )
            await session.commit()
        bc_session_id = None if progress is None else progress.session_id
    finally:
        await delete_blunder_check_sessions(test_engine, [bc_session_id] if bc_session_id else [])
        await delete_games(test_engine, [game_id])
        if drill_session_id is not None:
            async with maker() as session:
                async with session.begin():
                    await session.execute(
                        delete(DrillSession).where(DrillSession.id == drill_session_id)
                    )
    assert (progress is not None) is expect_window


@pytest.mark.asyncio
async def test_cooldown_cooled_blunder_not_composed_through_a_herring_round(
    test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After the blunder pick comes back empty, the plain herring pick reloads the game: the judge
    must still treat the cooled blunder as served, or it would fill the blunder slot with it."""
    blunder_shape, herring_shape = WindowShape(3, 1), WindowShape(3, None)
    plans = itertools.cycle([SlotPlan("own", blunder_shape), SlotPlan("own", herring_shape)])
    monkeypatch.setattr(blunder_check_selection, "draw_slot_plan", lambda rng: next(plans))
    monkeypatch.setattr(blunder_check_selection, "draw_blunder_shape", lambda rng: blunder_shape)
    monkeypatch.setattr(blunder_check_selection, "draw_herring_shape", lambda rng: herring_shape)
    user_id, _ = await register_user("bc-cooldown-herring", beta=False, test_engine=test_engine)
    evals = with_user_blunder(flat_evals(_BC_ROWS, 0), _BC_BLUNDER_PLY, _BC_DROP_CP)
    game_id = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=_BC_BLUNDER_PLY)],
    )
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            control = await blunder_check_selection.compose_windows(
                session, user_id=user_id, rng=random.Random(1), count=2
            )
            cooled = await blunder_check_selection.compose_windows(
                session,
                user_id=user_id,
                rng=random.Random(1),
                count=2,
                cooled_pairs=[(game_id, _BC_BLUNDER_PLY)],
            )
    finally:
        await delete_games(test_engine, [game_id])
    assert [w.blunder_ply for w in control] == [_BC_BLUNDER_PLY]
    assert all(w.blunder_ply != _BC_BLUNDER_PLY for w in cooled)
