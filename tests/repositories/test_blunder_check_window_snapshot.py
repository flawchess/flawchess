"""Phase 261 snapshot CHECKs on blunder_check_windows (CONTEXT "Claude's Discretion" record).

Coverage:
- round trip : a window carrying a full WindowSelectionRecord stores every snapshot column
- CHECKs     : the database refuses a herring with an arm, an arm without a snapshot, an arm
               probability outside (0, 1], a score outside [0, 1], a score without its inputs or
               without the type-mate flag, an unknown arm and a negative swing

Rejected rows roll back with their transaction, so only the round trip cleans up (session and game
in `finally`, eval lottery isolation).
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.blunder_check import (
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowArm,
    WindowCase,
)
from app.repositories import blunder_check_repository as repo
from app.repositories.blunder_check_repository import NewWindow, WindowSelectionRecord
from tests.blunder_check_seed import (
    SeedBlunder,
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    register_user,
    seed_judged_game,
    with_user_blunder,
)

_NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_ROWS = 61
_BLUNDER_PLY = 40
_BLUNDER_DROP_CP = 600
_WINDOW_LENGTH = 3
_BLUNDER_POSITION = 2

_EXPLORATION_PROBABILITY = 0.2
_SCORE = 0.3
_PLAYED_PROB = 0.1
_LOSS = 3.0
_MISSED = 0.0
_SWING = 2

# A valid snapshot of one blunder window; each rejection case overrides what it breaks.
_VALID_SNAPSHOT: dict[str, Any] = {
    "selection_arm": int(WindowArm.EXPLORATION),
    "arm_probability": _EXPLORATION_PROBABILITY,
    "facepalm_score": _SCORE,
    "facepalm_played_prob": _PLAYED_PROB,
    "facepalm_loss": _LOSS,
    "facepalm_missed": _MISSED,
    "facepalm_best_prob": None,
    "facepalm_reply_prob": 0.4,
    "type_swing": _SWING,
    "type_mate": False,
}


def _maker(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


def _record() -> WindowSelectionRecord:
    return WindowSelectionRecord(
        arm=WindowArm.EXPLORATION,
        arm_probability=_EXPLORATION_PROBABILITY,
        facepalm_score=_SCORE,
        played_prob=_PLAYED_PROB,
        loss=_LOSS,
        missed=_MISSED,
        best_prob=None,
        reply_prob=0.4,
        type_swing=_SWING,
        type_mate=False,
    )


def _new_window(game_id: int, *, herring: bool, selection: WindowSelectionRecord) -> NewWindow:
    return NewWindow(
        position=0,
        game_id=game_id,
        is_own=True,
        window_length=_WINDOW_LENGTH,
        blunder_position=None if herring else _BLUNDER_POSITION,
        first_ply=_BLUNDER_PLY - 2,
        blunder_ply=None if herring else _BLUNDER_PLY,
        window_case=WindowCase.HERRING if herring else WindowCase.ALLOWED,
        mover_elo=1500,
        start_fen=_START_FEN,
        move_ucis="e2e4 e7e5 g1f3",
        lead_in_plies=0,
        key_uci=None if herring else "d2d4",
        refutation_uci=None if herring else "e7e5",
        points_possible=3,
        selection=selection,
    )


async def _insert(test_engine, user_id: int, windows: list[NewWindow]) -> int:
    async with _maker(test_engine)() as session:
        async with session.begin():
            session_id = await repo.insert_session(
                session,
                user_id=user_id,
                windows=windows,
                now_utc=_NOW,
                session_date=_NOW.date(),
                expires_on=_NOW.date() + datetime.timedelta(days=1),
            )
    assert session_id is not None
    return session_id


async def _flush_raw_window(test_engine, user_id: int, **overrides: Any) -> None:
    """Add a header and one raw window row (snapshot overrides applied) and flush."""
    columns: dict[str, Any] = {**_VALID_SNAPSHOT, **overrides}
    async with _maker(test_engine)() as session:
        async with session.begin():
            header = BlunderCheckSession(
                user_id=user_id,
                status="open",
                window_count=1,
                started_at=_NOW,
                session_date=_NOW.date(),
                expires_on=_NOW.date() + datetime.timedelta(days=1),
            )
            session.add(header)
            await session.flush()
            session.add(
                BlunderCheckWindow(
                    session_id=header.id,
                    position=0,
                    user_id=user_id,
                    game_id=None,
                    is_own=True,
                    window_length=_WINDOW_LENGTH,
                    blunder_position=_BLUNDER_POSITION,
                    first_ply=_BLUNDER_PLY - 2,
                    blunder_ply=_BLUNDER_PLY,
                    window_case=int(WindowCase.ALLOWED),
                    start_fen=_START_FEN,
                    move_ucis="e2e4 e7e5 g1f3",
                    lead_in_plies=0,
                    points_possible=3,
                    **columns,
                )
            )
            await session.flush()


async def _user_and_game(test_engine, prefix: str) -> tuple[int, int]:
    user_id, _ = await register_user(prefix, beta=True, test_engine=test_engine)
    evals = with_user_blunder(flat_evals(_ROWS, 0), _BLUNDER_PLY, _BLUNDER_DROP_CP)
    game_id = await seed_judged_game(
        test_engine, user_id=user_id, evals_cp=evals, blunders=[SeedBlunder(ply=_BLUNDER_PLY)]
    )
    return user_id, game_id


@pytest.mark.asyncio
async def test_valid_snapshot_round_trips(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bcw-snap-ok")
    session_id: int | None = None
    try:
        session_id = await _insert(
            test_engine, user_id, [_new_window(game_id, herring=False, selection=_record())]
        )
        async with _maker(test_engine)() as session:
            row = (
                await session.execute(
                    select(BlunderCheckWindow).where(BlunderCheckWindow.session_id == session_id)
                )
            ).scalar_one()
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, [game_id])
    assert row.selection_arm == int(WindowArm.EXPLORATION)
    assert row.arm_probability == pytest.approx(_EXPLORATION_PROBABILITY)
    assert row.facepalm_score == pytest.approx(_SCORE)
    assert row.facepalm_played_prob == pytest.approx(_PLAYED_PROB)
    assert row.facepalm_loss == pytest.approx(_LOSS)
    assert row.facepalm_missed == pytest.approx(_MISSED)
    assert row.facepalm_best_prob is None
    assert row.facepalm_reply_prob == pytest.approx(0.4)
    assert row.type_swing == _SWING
    assert row.type_mate is False


@pytest.mark.asyncio
async def test_herring_with_an_arm_is_rejected(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bcw-snap-herring")
    try:
        with pytest.raises(IntegrityError, match="ck_blunder_check_windows_arm_herring"):
            await _insert(
                test_engine, user_id, [_new_window(game_id, herring=True, selection=_record())]
            )
    finally:
        await delete_games(test_engine, [game_id])


_REJECTIONS: list[tuple[str, dict[str, Any]]] = [
    ("ck_blunder_check_windows_selection_arm", {"selection_arm": 2}),
    (
        "ck_blunder_check_windows_arm_snapshot",
        {
            "facepalm_score": None,
            "facepalm_played_prob": None,
            "facepalm_loss": None,
            "facepalm_missed": None,
            "type_mate": None,
        },
    ),
    ("ck_blunder_check_windows_arm_probability", {"arm_probability": 0.0}),
    ("ck_blunder_check_windows_arm_probability", {"arm_probability": 1.5}),
    ("ck_blunder_check_windows_facepalm_score", {"facepalm_score": 1.5}),
    ("ck_blunder_check_windows_snapshot_inputs", {"facepalm_loss": None}),
    ("ck_blunder_check_windows_type_mate", {"type_mate": None}),
    ("ck_blunder_check_windows_type_swing", {"type_swing": -1}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("constraint", "overrides"),
    _REJECTIONS,
    ids=[
        f"{name.removeprefix('ck_blunder_check_windows_')}-{i}"
        for i, (name, _) in enumerate(_REJECTIONS)
    ],
)
async def test_malformed_snapshot_is_rejected(
    test_engine, constraint: str, overrides: dict[str, Any]
) -> None:
    user_id, _ = await register_user("bcw-snap-bad", beta=True, test_engine=test_engine)
    with pytest.raises(IntegrityError, match=constraint):
        await _flush_raw_window(test_engine, user_id, **overrides)
