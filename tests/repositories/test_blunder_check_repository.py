"""Repository tests for the blunder check (Phase 249).

Coverage:
- schema CHECK constraints (herring/blunder_ply coupling, blunder_position bound, outcome
  range, answer result/answered_at coupling) and FK delete semantics (game SET NULL,
  session CASCADE)
- insert_session under the one-open-session race
- pick_own_game_ids / pick_foreign_game_ids filters (D-09)
- load_positions / load_blunder_flaws (facepalm filter, 250 D-09)
- served_for_games (250 D-17), require_facepalm picks
- recent_rated_games (250 D-14): rated human games only, scoped to the user, newest first

Every seeded game is deleted in `finally` (tier-3 lottery isolation).
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.blunder_check import (
    AnswerResult,
    BlunderCheckAnswer,
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
)
from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.repositories import blunder_check_repository as repo
from app.repositories.blunder_check_repository import NewWindow
from app.services.blunder_check_rules import FACEPALM_SCORE_MIN
from app.services.blunder_check_candidates import judge_game
from app.services.blunder_check_selection import legal_key_plies
from tests.blunder_check_seed import (
    SEED_FACEPALM_SCORE,
    SEED_PGN,
    SeedBlunder,
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    register_user,
    seed_judged_game,
    with_opponent_gift,
    with_user_blunder,
)

_NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_ROWS = 60
_BLUNDER_PLY = 20
_BLUNDER_DROP_CP = 500
# Plies of the tracer game's three user blunders: below threshold, qualifying, unscored.
_TRACER_PLIES = (20, 30, 40)


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
async def test_recent_rated_games_keeps_rated_human_games_newest_first(test_engine) -> None:
    user_id, _ = await register_user("bc-level", beta=False, test_engine=test_engine)
    other_id, _ = await register_user("bc-level-other", beta=False, test_engine=test_engine)
    evals = _blunder_evals()
    # Distinct user-side ratings (the user plays white) identify each game in the result.
    ratings = {"newer": 1600, "older": 1400, "unrated": 1700, "bot": 1800, "other": 1900}
    ids = {
        name: await seed_judged_game(
            test_engine,
            user_id=other_id if name == "other" else user_id,
            evals_cp=evals,
            blunders=[],
            white_rating=rating,
        )
        for name, rating in ratings.items()
    }
    played = {"older": 1, "newer": 3, "unrated": 4, "bot": 5, "other": 6}
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            async with session.begin():
                for name, day in played.items():
                    values: dict[str, object] = {
                        "played_at": datetime.datetime(2026, 6, day, tzinfo=datetime.timezone.utc)
                    }
                    if name == "unrated":
                        values["rated"] = False
                    if name == "bot":
                        values["is_computer_game"] = True
                    await session.execute(update(Game).where(Game.id == ids[name]).values(**values))
        async with maker() as session:
            rows = await repo.recent_rated_games(session, user_id=user_id, limit=10)
            limited = await repo.recent_rated_games(session, user_id=user_id, limit=1)
    finally:
        await delete_games(test_engine, list(ids.values()))
    # The unrated game and the game against a computer are excluded even though they are newer
    # (the bot-rating echo), and the other user's game never leaks in (T-250-17).
    assert [row.rating for row in rows] == [ratings["newer"], ratings["older"]]
    assert [row.rating for row in limited] == [ratings["newer"]]


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


@pytest.mark.asyncio
async def test_pick_own_require_facepalm_skips_games_without_unserved_qualifying_blunder(
    test_engine,
) -> None:
    low_ply, qualifying_ply, _ = _TRACER_PLIES
    user_id, _ = await register_user("bc-pick-fp", beta=True, test_engine=test_engine)
    evals = _three_blunder_evals()
    qualifying = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=qualifying_ply)],
    )
    below = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=low_ply, facepalm_score=FACEPALM_SCORE_MIN - 0.2)],
    )
    unscored = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=low_ply, facepalm_score=None)],
    )
    served = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=qualifying_ply)],
    )
    session_id = await _insert(
        test_engine,
        user_id,
        [_window(served, 0, first_ply=qualifying_ply - 2, blunder_ply=qualifying_ply)],
    )
    seeded = [qualifying, below, unscored, served]
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            plain = await repo.pick_own_game_ids(session, user_id=user_id, limit=10, exclude_ids=[])
            required = await repo.pick_own_game_ids(
                session, user_id=user_id, limit=10, exclude_ids=[], require_facepalm=True
            )
        assert set(plain) == set(seeded)
        # Below-threshold, unscored and already-served blunders do not make a game eligible.
        assert set(required) == {qualifying}
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, seeded)


@pytest.mark.asyncio
async def test_pick_foreign_require_facepalm_skips_games_without_unserved_qualifying_blunder(
    test_engine,
) -> None:
    low_ply, qualifying_ply, _ = _TRACER_PLIES
    caller_id, caller_game = await _user_and_game(test_engine, "bc-fpf-caller")
    owner_id, _ = await register_user("bc-fpf-owner", beta=False, test_engine=test_engine)
    evals = _three_blunder_evals()
    qualifying = await seed_judged_game(
        test_engine,
        user_id=owner_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=qualifying_ply)],
    )
    below = await seed_judged_game(
        test_engine,
        user_id=owner_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=low_ply, facepalm_score=FACEPALM_SCORE_MIN - 0.2)],
    )
    served_to_caller = await seed_judged_game(
        test_engine,
        user_id=owner_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=qualifying_ply)],
    )
    served_to_other = await seed_judged_game(
        test_engine,
        user_id=owner_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=qualifying_ply)],
    )
    other_id, _ = await register_user("bc-fpf-other", beta=True, test_engine=test_engine)
    caller_session = await _insert(
        test_engine,
        caller_id,
        [_window(served_to_caller, 0, first_ply=qualifying_ply - 2, blunder_ply=qualifying_ply)],
    )
    other_session = await _insert(
        test_engine,
        other_id,
        [_window(served_to_other, 0, first_ply=qualifying_ply - 2, blunder_ply=qualifying_ply)],
    )
    seeded = [caller_game, qualifying, below, served_to_caller, served_to_other]
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
                sample_percent=100.0,
                require_facepalm=True,
            )
            unfiltered = await repo.pick_foreign_game_ids(
                session,
                user_id=caller_id,
                raw_low=1400,
                raw_high=1600,
                limit=100_000,
                exclude_ids=[],
                sample_percent=100.0,
            )
        # Other tests' leaked games may exist; only the seeded ids are asserted on. A window served
        # to ANOTHER user never hides a game from the caller (T-250-08).
        assert set(picked) & set(seeded) == {qualifying, served_to_other}
        assert set(unfiltered) & set(seeded) == {
            qualifying,
            below,
            served_to_caller,
            served_to_other,
        }
    finally:
        await delete_blunder_check_sessions(test_engine, [caller_session, other_session])
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
async def test_load_blunder_flaws_only_qualifying_blunders(test_engine) -> None:
    user_id, game_id = await _user_and_game(test_engine, "bc-load-flaws")
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            # A mistake-severity row must not come back, even with a qualifying score.
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
                        facepalm_score=SEED_FACEPALM_SCORE,
                    )
                )
        async with maker() as session:
            flaws = await repo.load_blunder_flaws(session, [game_id])
        assert [(f.ply, f.severity) for f in flaws[game_id]] == [(_BLUNDER_PLY, 2)]
        assert flaws[game_id][0].facepalm_score == pytest.approx(SEED_FACEPALM_SCORE)
    finally:
        await delete_games(test_engine, [game_id])


def _three_blunder_evals() -> list[int]:
    """White user blunders at plies 20, 30 and 40; black hands the balance back right after each."""
    evals = flat_evals(_ROWS, 0)
    for ply in _TRACER_PLIES:
        evals = with_user_blunder(evals, ply, _BLUNDER_DROP_CP)
        evals = with_opponent_gift(evals, ply + 1, _BLUNDER_DROP_CP)
    return evals


@pytest.mark.asyncio
async def test_facepalm_loader_and_judge_keep_only_qualifying(test_engine) -> None:
    """Tracer (250 D-09): the SQL filter and the pure judge both keep only the qualifying blunder."""
    low_ply, qualifying_ply, null_ply = _TRACER_PLIES
    user_id, _ = await register_user("bc-facepalm", beta=True, test_engine=test_engine)
    game_id = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=_three_blunder_evals(),
        blunders=[
            SeedBlunder(ply=low_ply, facepalm_score=FACEPALM_SCORE_MIN - 0.2),
            SeedBlunder(ply=qualifying_ply, facepalm_score=SEED_FACEPALM_SCORE),
            SeedBlunder(ply=null_ply, facepalm_score=None),
        ],
    )
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            flaws = (await repo.load_blunder_flaws(session, [game_id]))[game_id]
            positions = (await repo.load_positions(session, [game_id]))[game_id]
        assert [f.ply for f in flaws] == [qualifying_ply]
        key_plies = legal_key_plies(SEED_PGN, positions, {f.ply for f in flaws})
        candidates = judge_game(
            game_id=game_id,
            user_is_white=True,
            positions=positions,
            flaws=flaws,
            key_plies=key_plies,
            served_blunder_plies=set(),
            served_ply_ranges=[],
        )
        assert candidates is not None
        assert [c.ply for c in candidates.blunders] == [qualifying_ply]
    finally:
        await delete_games(test_engine, [game_id])


# ---------------------------------------------------------------------------
# Served sets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_served_blunder_counts_once_its_window_was_served(test_engine) -> None:
    """250 D-17: a false-alarm window still burns its blunder, answered at that ply or not."""
    user_id, game_id = await _user_and_game(test_engine, "bc-served")
    session_id = await _insert(test_engine, user_id, [_window(game_id)])
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        window_id = await _window_id(test_engine, session_id, 0)
        # A false alarm at move 1 ends the window before the blunder ply is prompted: no answer
        # row exists for the blunder ply, yet the blunder is served.
        await _add_answer(test_engine, window_id, 1, _BLUNDER_PLY - 2)
        async with maker() as session:
            served = await repo.served_for_games(session, user_id=user_id, game_ids=[game_id])
            other = await repo.served_for_games(
                session, user_id=user_id + 10**6, game_ids=[game_id]
            )
        assert served.served_blunder_plies[game_id] == {_BLUNDER_PLY}
        # The window's judged range is (first_ply, blunder_ply).
        assert served.judged_ranges[game_id] == [(_BLUNDER_PLY - 2, _BLUNDER_PLY)]
        # Another solver has been served nothing (user-scoped, T-250-08).
        assert other.served_blunder_plies.get(game_id, set()) == set()
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
