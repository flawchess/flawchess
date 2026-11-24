"""Retired lichess filler rows (`DrillSource.LEGACY_SHARP_FILLER`, value 2) stay inert history.

Phase 263 D-03 deleted the static lichess puzzle set, so nothing can serve a source-2 row any
more. Prod still holds open sessions whose unsolved rows are such fillers (the pre-263
completion clause counted them as remaining), plus ~795 solved ones that must keep counting.
Each test seeds those rows directly through the rolled-back `db_session`. The rows no longer
carry a puzzle id: migration c4e6a8b0d375 dropped that column.
"""

import datetime

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.train_settings import TrainSettings
from app.repositories import train_repository
from tests.conftest import ensure_test_user
from tests.repositories.test_train_repository import (
    _PUZZLES_ONLY_BC_SIZE,
    _seed_open_session_with_sr_item,
    _set_blunder_check_size,
)

_USER_ID = 93110
_NOW = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc)
_TODAY = datetime.date(2026, 1, 15)


async def _open_session(db_session: AsyncSession, puzzle_count: int) -> DrillSession:
    drill_session = DrillSession(
        user_id=_USER_ID,
        session_date=_TODAY,
        status="open",
        puzzle_count=puzzle_count,
        expires_on=_TODAY + datetime.timedelta(days=1),
    )
    db_session.add(drill_session)
    await db_session.flush()
    return drill_session


def _legacy_row(
    session_id: int, position: int, *, solved: bool, move_quality: int | None = None
) -> DrillSolve:
    return DrillSolve(
        session_id=session_id,
        position=position,
        user_id=_USER_ID,
        game_id=None,
        herring_pool_id=None,
        ply=0,
        source=int(DrillSource.LEGACY_SHARP_FILLER),
        solved_at=_NOW if solved else None,
        correct_guess=True if solved else None,
        correct_move=True if solved else None,
        move_quality=move_quality,
    )


async def _session_with_sr_and_legacy(db_session: AsyncSession) -> tuple[DrillSession, int]:
    """An open 2-position session: an unsolved SR row (with its drill item) at 0, an unsolved
    legacy filler at 1."""
    await ensure_test_user(db_session, _USER_ID)
    drill_session = await _seed_open_session_with_sr_item(db_session, _USER_ID, "legacy-sr")
    sr_game_id = (
        await db_session.execute(
            select(DrillSolve.game_id).where(
                DrillSolve.session_id == drill_session.id, DrillSolve.position == 0
            )
        )
    ).scalar_one()
    assert sr_game_id is not None
    drill_session.puzzle_count = 2
    db_session.add(_legacy_row(drill_session.id, 1, solved=False))
    await db_session.flush()
    return drill_session, sr_game_id


@pytest.mark.asyncio
async def test_unsolved_legacy_filler_skipped_on_resume(db_session: AsyncSession) -> None:
    """The lichess set is gone, so an unsolved legacy row cannot be served: resume lists only the
    SR puzzle."""
    drill_session, sr_game_id = await _session_with_sr_and_legacy(db_session)

    resumed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert resumed.session_id == drill_session.id
    assert [(p.position, p.game_id) for p in resumed.puzzles] == [(0, sr_game_id)]


@pytest.mark.asyncio
async def test_unsolved_legacy_filler_never_pins_session_open(db_session: AsyncSession) -> None:
    """Solving the only servable row completes the session although an unsolved legacy row is
    still in it (prod: 14 sessions had only such fillers left).

    Mutation check: restoring the old completion clause that counted a legacy row with a
    non-NULL puzzle id as remaining, `session_complete` stays False and the session
    stays open, so this test fails (recorded in the 263-08 SUMMARY)."""
    drill_session, _ = await _session_with_sr_and_legacy(db_session)

    recorded = await train_repository.record_solve(
        db_session,
        user_id=_USER_ID,
        session_id=drill_session.id,
        position=0,
        guess="several",
        played_move="e2e4",
        move_quality="good",
        now_utc=_NOW,
    )

    assert recorded is not None
    assert recorded.session_complete is True
    status = (
        await db_session.execute(
            select(DrillSession.status).where(DrillSession.id == drill_session.id)
        )
    ).scalar_one()
    assert status == "completed"


@pytest.mark.asyncio
async def test_resume_completes_session_whose_remaining_rows_are_unservable(
    db_session: AsyncSession,
) -> None:
    """An open session with one solved SR row and one unsolved legacy filler row has nothing
    servable left: the next compose call completes it and credits its day (lazy completion in
    `_resume_session`; completion used to run only inside `record_solve`).

    Mutation check: removing the lazy branch leaves the session 'open' and
    `streak_credited_on` NULL, so this test fails (recorded in the 263-09 SUMMARY)."""
    drill_session, _ = await _session_with_sr_and_legacy(db_session)
    # Blunder check off, so the puzzle-only completion completes the day (two-mode days need both).
    await _set_blunder_check_size(db_session, _USER_ID, _PUZZLES_ONLY_BC_SIZE)
    await db_session.execute(
        update(DrillSolve)
        .where(DrillSolve.session_id == drill_session.id, DrillSolve.position == 0)
        .values(
            solved_at=_NOW,
            correct_guess=True,
            correct_move=True,
            move_quality=int(DrillMoveQuality.GOOD),
        )
    )
    await db_session.flush()

    resumed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert resumed.session_id == drill_session.id
    assert resumed.puzzles == []
    status = (
        await db_session.execute(
            select(DrillSession.status).where(DrillSession.id == drill_session.id)
        )
    ).scalar_one()
    assert status == "completed"
    credited_on = (
        await db_session.execute(
            select(TrainSettings.streak_credited_on).where(TrainSettings.user_id == _USER_ID)
        )
    ).scalar_one()
    assert credited_on == drill_session.session_date


@pytest.mark.asyncio
async def test_resume_leaves_untouched_session_with_nothing_servable_open(
    db_session: AsyncSession,
) -> None:
    """The negative of the lazy completion above (security T-263-25): an open session nobody
    solved anything in, whose only row is an unservable legacy filler, is NOT completed by a
    compose call and credits no streak day. Without the "at least one solve" guard a user
    would get a completed day for merely opening Train.

    Mutation check: dropping `and solved_results` from the lazy branch in `_resume_session`
    completes the session and sets `streak_credited_on`, so this test fails."""
    await ensure_test_user(db_session, _USER_ID)
    # Blunder check off, so nothing but the puzzle session stands between the user and a
    # completed day (the same setup as the positive test above).
    await _set_blunder_check_size(db_session, _USER_ID, _PUZZLES_ONLY_BC_SIZE)
    drill_session = await _open_session(db_session, puzzle_count=1)
    db_session.add(_legacy_row(drill_session.id, 0, solved=False))
    await db_session.flush()

    resumed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert resumed.session_id == drill_session.id
    assert resumed.puzzles == []
    assert resumed.solved_results == []
    row = (
        await db_session.execute(
            select(DrillSession.status, DrillSession.completed_at).where(
                DrillSession.id == drill_session.id
            )
        )
    ).one()
    assert row.status == "open"
    assert row.completed_at is None
    credited_on = (
        await db_session.execute(
            select(TrainSettings.streak_credited_on).where(TrainSettings.user_id == _USER_ID)
        )
    ).scalar_one()
    assert credited_on is None


@pytest.mark.asyncio
async def test_resume_serializes_solved_legacy_filler_as_sharp_filler(
    db_session: AsyncSession,
) -> None:
    """A solved legacy row keeps its "sharp_filler" wire value in `solved_results`: losing the
    `_wire_source` arm would raise on the Today mount. It carries no SR bookkeeping."""
    await ensure_test_user(db_session, _USER_ID)
    drill_session = await _open_session(db_session, puzzle_count=1)
    db_session.add(
        _legacy_row(drill_session.id, 0, solved=True, move_quality=int(DrillMoveQuality.GOOD))
    )
    await db_session.flush()

    resumed = await train_repository.compose_and_materialize_session(
        db_session, user_id=_USER_ID, now_utc=_NOW
    )

    assert [(r.source, r.item_status, r.due_date) for r in resumed.solved_results] == [
        ("sharp_filler", None, None)
    ]
    assert resumed.puzzles == []


@pytest.mark.asyncio
async def test_record_solve_on_legacy_filler_records_client_tier(
    db_session: AsyncSession,
) -> None:
    """A browser that composed before the deploy still holds the filler and posts its solve. The
    solve is recorded as a sharp puzzle with no key and no vetted set, so the client's asserted
    tier is stored verbatim (no 404 that would strand the client)."""
    await ensure_test_user(db_session, _USER_ID)
    drill_session = await _open_session(db_session, puzzle_count=1)
    db_session.add(_legacy_row(drill_session.id, 0, solved=False))
    await db_session.flush()

    recorded = await train_repository.record_solve(
        db_session,
        user_id=_USER_ID,
        session_id=drill_session.id,
        position=0,
        guess="critical",
        played_move="d2d4",
        move_quality="inaccuracy",
        now_utc=_NOW,
    )

    assert recorded is not None
    assert recorded.puzzle_type == "sharp"
    assert recorded.source == "sharp_filler"
    assert recorded.vetted_moves == []
    assert recorded.graded_es_before is None
    assert recorded.graded_es_after is None
    assert recorded.move_quality == "inaccuracy"  # the client's tier, verbatim
    stored = (
        await db_session.execute(
            select(DrillSolve.move_quality).where(DrillSolve.session_id == drill_session.id)
        )
    ).scalar_one()
    assert stored == int(DrillMoveQuality.INACCURACY)


@pytest.mark.asyncio
async def test_reveal_legacy_filler_not_found(db_session: AsyncSession) -> None:
    """The set that held a filler's FEN is gone, so a solved legacy row cannot be revealed."""
    await ensure_test_user(db_session, _USER_ID)
    drill_session = await _open_session(db_session, puzzle_count=1)
    db_session.add(
        _legacy_row(drill_session.id, 0, solved=True, move_quality=int(DrillMoveQuality.GOOD))
    )
    await db_session.flush()

    result = await train_repository.reveal_for_puzzle(
        db_session, user_id=_USER_ID, session_id=drill_session.id, position=0
    )

    assert result == "not_found"
