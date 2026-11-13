"""Repository tests for the blunder check (Phase 249).

Coverage:
- schema CHECK constraints (herring/blunder_ply coupling, blunder_position bound, outcome
  range, answer result/answered_at coupling) and FK delete semantics (game SET NULL,
  session CASCADE)
- insert_session under the one-open-session race
- pick_own_game_ids / pick_foreign_game_ids filters (D-09)
- load_positions / load_blunder_flaws
- served_for_games (D-10)

Every seeded game is deleted in `finally` (tier-3 lottery isolation).
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.blunder_check import (
    AnswerResult,
    BlunderCheckAnswer,
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
)
from app.models.game_flaw import GameFlaw
from app.repositories import blunder_check_repository as repo
from app.repositories.blunder_check_repository import NewWindow
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
_ROWS = 60
_BLUNDER_PLY = 20
_BLUNDER_DROP_CP = 500


def _blunder_evals() -> list[int]:
    return with_user_blunder(flat_evals(_ROWS, 0), _BLUNDER_PLY, _BLUNDER_DROP_CP)


def _window(game_id: int, position: int = 0, **overrides: object) -> NewWindow:
    """A valid blunder window (ALLOWED case, blunder at the 2nd judged move)."""
    fields: dict[str, object] = dict(
        position=position,
        game_id=game_id,
        is_own=True,
        window_length=3,
        blunder_position=2,
        first_ply=_BLUNDER_PLY - 2,
        blunder_ply=_BLUNDER_PLY,
        window_case=WindowCase.ALLOWED,
        mover_elo=1500,
        start_fen=_START_FEN,
        move_ucis="e2e4 e7e5 g1f3",
        lead_in_plies=0,
        key_uci="d2d4",
        refutation_uci="e7e5",
        points_possible=3,
    )
    fields.update(overrides)
    return NewWindow(**fields)  # ty: ignore[invalid-argument-type]  # dict of mixed kwargs


def _herring_window(game_id: int, position: int, first_ply: int, length: int) -> NewWindow:
    return _window(
        game_id,
        position,
        window_length=length,
        blunder_position=None,
        first_ply=first_ply,
        blunder_ply=None,
        window_case=WindowCase.HERRING,
        key_uci=None,
        refutation_uci=None,
    )


async def _insert(test_engine, user_id: int, windows: list[NewWindow]) -> int:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            session_id = await repo.insert_session(
                session, user_id=user_id, windows=windows, now_utc=_NOW
            )
    assert session_id is not None
    return session_id


async def _window_id(test_engine, session_id: int, position: int) -> int:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        return (
            await session.execute(
                select(BlunderCheckWindow.id).where(
                    BlunderCheckWindow.session_id == session_id,
                    BlunderCheckWindow.position == position,
                )
            )
        ).scalar_one()


async def _add_answer(test_engine, window_id: int, move_index: int, ply: int) -> None:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            session.add(
                BlunderCheckAnswer(
                    window_id=window_id,
                    move_index=move_index,
                    ply=ply,
                    prompted_at=_NOW,
                    answer=0,
                    result=int(AnswerResult.CORRECT_SAFE),
                    answered_at=_NOW,
                )
            )


async def _user_and_game(test_engine, prefix: str, **game_kwargs: object) -> tuple[int, int]:
    user_id, _ = await register_user(prefix, beta=True, test_engine=test_engine)
    game_id = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=_blunder_evals(),
        blunders=[SeedBlunder(ply=_BLUNDER_PLY)],
        **game_kwargs,  # ty: ignore[invalid-argument-type]  # forwarded test overrides
    )
    return user_id, game_id


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


async def _add_raw_window(test_engine, session_id: int, user_id: int, **overrides: object) -> None:
    """Direct ORM insert of a window row so CHECKs fire (bypasses the NewWindow dataclass)."""
    fields: dict[str, object] = dict(
        session_id=session_id,
        position=5,
        user_id=user_id,
        game_id=None,
        is_own=True,
        window_length=3,
        blunder_position=2,
        first_ply=10,
        blunder_ply=12,
        window_case=int(WindowCase.ALLOWED),
        start_fen=_START_FEN,
        move_ucis="e2e4",
        lead_in_plies=0,
        points_possible=3,
    )
    fields.update(overrides)
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            session.add(BlunderCheckWindow(**fields))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"window_case": int(WindowCase.HERRING)},  # herring case but a blunder_ply is set
        {"blunder_position": 6},  # beyond window_length
        {"outcome": 7},  # outside the outcome enum
    ],
    ids=["herring_with_blunder_ply", "blunder_position_6", "outcome_7"],
)
async def test_schema_window_check_rejects(test_engine, overrides: dict[str, object]) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-schema")
    session_id = await _insert(test_engine, user_id, [_window(game_id, 0)])
    try:
        with pytest.raises(IntegrityError):
            await _add_raw_window(test_engine, session_id, user_id, **overrides)
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_schema_answer_result_without_answered_at_rejected(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-answer-check")
    session_id = await _insert(test_engine, user_id, [_window(game_id)])
    try:
        window_id = await _window_id(test_engine, session_id, 0)
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        with pytest.raises(IntegrityError):
            async with maker() as session:
                async with session.begin():
                    session.add(
                        BlunderCheckAnswer(
                            window_id=window_id,
                            move_index=1,
                            ply=18,
                            prompted_at=_NOW,
                            result=int(AnswerResult.CAUGHT),
                            answered_at=None,
                        )
                    )
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_schema_game_delete_nulls_window_game_id(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-game-delete")
    session_id = await _insert(test_engine, user_id, [_window(game_id)])
    try:
        await delete_games(test_engine, [game_id])
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            row = (
                await session.execute(
                    select(BlunderCheckWindow.game_id, BlunderCheckWindow.start_fen).where(
                        BlunderCheckWindow.session_id == session_id
                    )
                )
            ).one()
        assert row.game_id is None
        assert row.start_fen == _START_FEN  # the snapshot keeps the window servable
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_schema_session_delete_cascades_windows_and_answers(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-cascade")
    session_id = await _insert(test_engine, user_id, [_window(game_id)])
    try:
        window_id = await _window_id(test_engine, session_id, 0)
        await _add_answer(test_engine, window_id, 1, _BLUNDER_PLY - 2)
        await delete_blunder_check_sessions(test_engine, [session_id])
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            windows = (
                await session.execute(
                    select(func.count()).where(BlunderCheckWindow.session_id == session_id)
                )
            ).scalar_one()
            answers = (
                await session.execute(
                    select(func.count()).where(BlunderCheckAnswer.window_id == window_id)
                )
            ).scalar_one()
        assert (windows, answers) == (0, 0)
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, [game_id])


# ---------------------------------------------------------------------------
# insert_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_session_second_open_returns_none(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-insert-race")
    first_id = await _insert(test_engine, user_id, [_window(game_id)])
    try:
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            async with session.begin():
                second = await repo.insert_session(
                    session, user_id=user_id, windows=[_window(game_id)], now_utc=_NOW
                )
        assert second is None
        async with maker() as session:
            open_rows = (
                await session.execute(
                    select(func.count()).where(
                        BlunderCheckSession.user_id == user_id,
                        BlunderCheckSession.status == "open",
                    )
                )
            ).scalar_one()
        assert open_rows == 1
    finally:
        await delete_blunder_check_sessions(test_engine, [first_id])
        await delete_games(test_engine, [game_id])


# ---------------------------------------------------------------------------
# Picks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pick_own_game_ids_filters_and_excludes(test_engine) -> None:
    user_id, evaluated_a = await _user_and_game(test_engine, "bc-pick-own")
    evaluated_b = await seed_judged_game(
        test_engine, user_id=user_id, evals_cp=_blunder_evals(), blunders=[]
    )
    unevaluated = await seed_judged_game(
        test_engine, user_id=user_id, evals_cp=_blunder_evals(), blunders=[], full_evals=False
    )
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            picked = await repo.pick_own_game_ids(
                session, user_id=user_id, limit=10, exclude_ids=[]
            )
            excluded = await repo.pick_own_game_ids(
                session, user_id=user_id, limit=10, exclude_ids=[evaluated_a]
            )
        assert set(picked) == {evaluated_a, evaluated_b}
        assert set(excluded) == {evaluated_b}
    finally:
        await delete_games(test_engine, [evaluated_a, evaluated_b, unevaluated])


@pytest.mark.asyncio
async def test_pick_foreign_game_ids_applies_every_filter(test_engine) -> None:
    caller_id, caller_game = await _user_and_game(test_engine, "bc-foreign-caller")
    owner_id, _ = await register_user("bc-foreign-owner", beta=False, test_engine=test_engine)
    guest_id, _ = await register_user(
        "bc-foreign-guest", beta=False, test_engine=test_engine, guest=True
    )
    evals = _blunder_evals()
    eligible = await seed_judged_game(test_engine, user_id=owner_id, evals_cp=evals, blunders=[])
    unevaluated = await seed_judged_game(
        test_engine, user_id=owner_id, evals_cp=evals, blunders=[], full_evals=False
    )
    out_of_range = await seed_judged_game(
        test_engine, user_id=owner_id, evals_cp=evals, blunders=[], white_rating=900
    )
    guest_game = await seed_judged_game(test_engine, user_id=guest_id, evals_cp=evals, blunders=[])
    seeded = [caller_game, eligible, unevaluated, out_of_range, guest_game]
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            picked = await repo.pick_foreign_game_ids(
                session,
                user_id=caller_id,
                raw_low=1400,
                raw_high=1600,
                limit=100_000,
                exclude_ids=[],
                sample_percent=100,
            )
            excluding = await repo.pick_foreign_game_ids(
                session,
                user_id=caller_id,
                raw_low=1400,
                raw_high=1600,
                limit=100_000,
                exclude_ids=[eligible],
                sample_percent=100,
            )
        # Other tests' leaked games may exist; only the seeded ids are asserted on.
        assert set(picked) & set(seeded) == {eligible}
        assert eligible not in excluding
    finally:
        await delete_games(test_engine, seeded)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_positions_contiguous_with_best_move(test_engine) -> None:
    _, game_id = await _user_and_game(test_engine, "bc-load-pos")
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            by_game = await repo.load_positions(session, [game_id])
        rows = by_game[game_id]
        assert [r.ply for r in rows] == list(range(len(rows)))
        by_ply = {r.ply: r for r in rows}
        assert by_ply[_BLUNDER_PLY].best_move is not None
        assert by_ply[_BLUNDER_PLY + 1].best_move is not None
        assert by_ply[3].best_move is None
        assert by_ply[_BLUNDER_PLY].eval_cp == -_BLUNDER_DROP_CP
    finally:
        await delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_load_blunder_flaws_only_blunders_with_maia_values(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-load-flaws")
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            # A mistake-severity row must not come back.
            async with session.begin():
                session.add(
                    GameFlaw(
                        user_id=user_id,
                        game_id=game_id,
                        ply=30,
                        severity=1,
                        phase=1,
                        is_miss=False,
                        is_lucky=False,
                        is_reversed=False,
                        is_squandered=False,
                        fen="8/8/8/8/8/8/8/8",
                    )
                )
        async with maker() as session:
            flaws = await repo.load_blunder_flaws(session, [game_id])
        assert [(f.ply, f.severity) for f in flaws[game_id]] == [(_BLUNDER_PLY, 2)]
        flaw = flaws[game_id][0]
        assert (flaw.maia_refutation_prob, flaw.maia_refutation_rank) == (0.5, 1)
        assert (flaw.maia_best_prob, flaw.maia_best_rank) == (0.5, 1)
    finally:
        await delete_games(test_engine, [game_id])


# ---------------------------------------------------------------------------
# Served sets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_served_blunder_unserved_until_its_ply_was_prompted(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-served")
    session_id = await _insert(test_engine, user_id, [_window(game_id)])
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        window_id = await _window_id(test_engine, session_id, 0)
        # A false alarm at move 1 ends the window before the blunder ply is prompted.
        await _add_answer(test_engine, window_id, 1, _BLUNDER_PLY - 2)
        async with maker() as session:
            served = await repo.served_for_games(session, user_id=user_id, game_ids=[game_id])
        assert served.prompted.get(game_id, set()) == set()
        # The window's judged range is (first_ply, blunder_ply) either way.
        assert served.judged_ranges[game_id] == [(_BLUNDER_PLY - 2, _BLUNDER_PLY)]

        await _add_answer(test_engine, window_id, 2, _BLUNDER_PLY)
        async with maker() as session:
            served = await repo.served_for_games(session, user_id=user_id, game_ids=[game_id])
        assert served.prompted[game_id] == {_BLUNDER_PLY}
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_served_judged_ranges_for_herring_and_blunder_windows(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-ranges")
    herring_first, herring_len = 30, 4
    session_id = await _insert(
        test_engine,
        user_id,
        [_window(game_id, 0), _herring_window(game_id, 1, herring_first, herring_len)],
    )
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            served = await repo.served_for_games(session, user_id=user_id, game_ids=[game_id])
            other = await repo.served_for_games(
                session, user_id=user_id + 10**6, game_ids=[game_id]
            )
        # Herring: first_ply + 2 * (window_length - 1) = 30 + 6.
        assert sorted(served.judged_ranges[game_id]) == [
            (_BLUNDER_PLY - 2, _BLUNDER_PLY),
            (herring_first, herring_first + 2 * (herring_len - 1)),
        ]
        # Another solver sees nothing (user-scoped).
        assert other.judged_ranges.get(game_id, []) == []
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, [game_id])
