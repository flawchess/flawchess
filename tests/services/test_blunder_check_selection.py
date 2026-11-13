"""DB tests for the blunder-check session composer (Phase 249 plan 03).

Coverage:
- own_first      : D-09, own supply fills every slot and the foreign pick is never queried
- foreign        : D-09, a user without own supply gets rating-banded, non-guest strangers' games
- fit            : D-03, a blunder only anchors a drawn position it fits
- repeat         : D-10, prompted blunders and overlapping herrings are never composed again
- miss           : D-07, a pure miss at position 1 carries the opponent's blunder as last lead-in
- short          : a user whose supply fits fewer windows gets a gap-free short session
- helpers        : snapshot, key-ply legality and reference Elo

Every seeded game is deleted in `finally` (leaked non-guest full-eval games poison other tests).
"""

from __future__ import annotations

import datetime
import io
import random
from collections.abc import Sequence

import chess
import chess.pgn
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.blunder_check import (
    BlunderCheckAnswer,
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
)
from app.models.game import Game
from app.models.user import User
from app.repositories.blunder_check_repository import EloSourceRow, NewWindow
from app.services import blunder_check_selection
from app.services.blunder_check_rules import (
    BLUNDER_CHECK_SESSION_WINDOWS,
    BLUNDER_MAX_PRE_EVAL_CP,
    LEAD_IN_PLIES,
    WindowShape,
)
from app.services.blunder_check_selection import (
    FOREIGN_ELO_BANDS,
    build_snapshot,
    compose_windows,
    reference_elo,
)
from tests.blunder_check_seed import (
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

_ROWS = 61  # positions of SEED_PGN (60 plies + the final position)
_USER_BLUNDER_PLY = 40  # white user; 20 clean user moves precede it
_BLUNDER_DROP_CP = 600
_RATING = 1500
_SEEDS = (0, 1, 2, 3, 4)
_START_FEN = "rnbqkbnr/pppqpppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_TS = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
# Inside the raw-rating prefilter (band + FOREIGN_RAW_PREFILTER_MARGIN) but outside the widest
# pinned-Elo band, so only the exact post-load band check can exclude it.
_FOREIGN_RATING_FAR = _RATING + FOREIGN_ELO_BANDS[-1] + 200


def _maker(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _user(test_engine, prefix: str, *, guest: bool = False) -> int:
    user_id, _ = await register_user(prefix, beta=True, test_engine=test_engine, guest=guest)
    return user_id


async def _seed_games(
    test_engine,
    user_id: int,
    count: int,
    *,
    blunder_ply: int = _USER_BLUNDER_PLY,
    rating: int = _RATING,
    full_evals: bool = True,
) -> list[int]:
    """`count` games: a clean stretch, then one findable blunder by the (white) user."""
    evals = with_user_blunder(flat_evals(_ROWS, 0), blunder_ply, _BLUNDER_DROP_CP)
    return [
        await seed_judged_game(
            test_engine,
            user_id=user_id,
            evals_cp=evals,
            blunders=[SeedBlunder(ply=blunder_ply)],
            white_rating=rating,
            black_rating=rating,
            full_evals=full_evals,
        )
        for _ in range(count)
    ]


async def _compose(test_engine, user_id: int, seed: int = 0) -> list[NewWindow]:
    async with _maker(test_engine)() as session:
        return await compose_windows(session, user_id=user_id, rng=random.Random(seed))


def _last_judged_ply(window: NewWindow) -> int:
    if window.blunder_ply is not None:
        return window.blunder_ply
    return window.first_ply + 2 * (window.window_length - 1)


async def _insert_prior_window(
    test_engine,
    *,
    user_id: int,
    game_id: int,
    first_ply: int,
    blunder_ply: int | None,
    window_length: int,
    answer_plies: Sequence[int],
) -> int:
    """A completed session with one served window and an answer row per prompted ply."""
    blunder_position = None if blunder_ply is None else (blunder_ply - first_ply) // 2 + 1
    async with _maker(test_engine)() as session:
        async with session.begin():
            header = BlunderCheckSession(
                user_id=user_id,
                status="completed",
                window_count=1,
                started_at=_TS,
                completed_at=_TS,
            )
            session.add(header)
            await session.flush()
            window = BlunderCheckWindow(
                session_id=header.id,
                position=0,
                user_id=user_id,
                game_id=game_id,
                is_own=True,
                window_length=window_length,
                blunder_position=blunder_position,
                first_ply=first_ply,
                blunder_ply=blunder_ply,
                window_case=int(WindowCase.HERRING if blunder_ply is None else WindowCase.ALLOWED),
                start_fen=_START_FEN,
                move_ucis="e2e4",
                lead_in_plies=0,
                points_possible=3,
            )
            session.add(window)
            await session.flush()
            for index, ply in enumerate(answer_plies, start=1):
                session.add(
                    BlunderCheckAnswer(
                        window_id=window.id, move_index=index, ply=ply, prompted_at=_TS
                    )
                )
            return header.id


def _force_shape(monkeypatch, shape: WindowShape) -> None:
    monkeypatch.setattr(blunder_check_selection, "draw_window_shape", lambda rng: shape)


# ---------------------------------------------------------------------------
# D-09 own first / foreign fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_own_first_never_queries_foreign(test_engine, monkeypatch) -> None:
    caller = await _user(test_engine, "bcs-own")
    stranger = await _user(test_engine, "bcs-own-stranger")
    own_ids = await _seed_games(test_engine, caller, 7)
    foreign_ids = await _seed_games(test_engine, stranger, 8)

    async def _boom(*args: object, **kwargs: object) -> list[int]:
        raise AssertionError("the foreign pick must not run while own supply fills every slot")

    monkeypatch.setattr(blunder_check_selection.repo, "pick_foreign_game_ids", _boom)
    try:
        windows = await _compose(test_engine, caller, seed=3)
    finally:
        await delete_games(test_engine, own_ids + foreign_ids)
    assert len(windows) == BLUNDER_CHECK_SESSION_WINDOWS
    assert all(w.is_own for w in windows)
    assert {w.game_id for w in windows} <= set(own_ids)


@pytest.mark.asyncio
async def test_foreign_fallback_bands_by_elo_and_skips_guests(test_engine, monkeypatch) -> None:
    monkeypatch.setattr(blunder_check_selection, "FOREIGN_SAMPLE_PERCENT", 100.0)
    caller = await _user(test_engine, "bcs-fb")
    stranger = await _user(test_engine, "bcs-fb-stranger")
    guest = await _user(test_engine, "bcs-fb-guest", guest=True)
    # The caller has recent rated games but nothing fully evaluated: reference Elo, no own supply.
    own_ids = await _seed_games(test_engine, caller, 3, full_evals=False)
    in_band = await _seed_games(test_engine, stranger, 2)
    too_strong = await _seed_games(test_engine, stranger, 6, rating=_FOREIGN_RATING_FAR)
    guest_ids = await _seed_games(test_engine, guest, 2)
    all_ids = own_ids + in_band + too_strong + guest_ids
    try:
        windows = await _compose(test_engine, caller, seed=5)
        async with _maker(test_engine)() as session:
            owners = (
                await session.execute(
                    select(Game.id, Game.user_id, User.is_guest)
                    .join(User, User.id == Game.user_id)
                    .where(Game.id.in_([w.game_id for w in windows]))
                )
            ).all()
    finally:
        await delete_games(test_engine, all_ids)
    # Only two games are in band; the six too-strong ones must not top the session up.
    assert {w.game_id for w in windows} == set(in_band)
    assert all(not w.is_own for w in windows)
    assert all(owner.user_id != caller and not owner.is_guest for owner in owners)
    assert not {w.game_id for w in windows} & set(guest_ids + too_strong + own_ids)
    for window in windows:
        assert window.mover_elo is not None
        assert abs(window.mover_elo - _RATING) <= FOREIGN_ELO_BANDS[-1]


# ---------------------------------------------------------------------------
# D-03 shape and fit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fit_blunder_only_anchors_positions_it_fits(test_engine, monkeypatch) -> None:
    _force_shape(monkeypatch, WindowShape(5, 3))
    caller = await _user(test_engine, "bcs-fit")
    fitting = await _seed_games(test_engine, caller, 3)
    # Only one user move precedes this blunder, so it can anchor position 1 or 2, never 3.
    too_early = await _seed_games(test_engine, caller, 1, blunder_ply=2)
    try:
        windows = await _compose(test_engine, caller, seed=1)
    finally:
        await delete_games(test_engine, fitting + too_early)
    assert {w.game_id for w in windows} == set(fitting)
    for window in windows:
        assert window.blunder_position == 3
        assert window.blunder_ply == _USER_BLUNDER_PLY
        # Two clean user moves precede it, judged plies step by 2.
        assert window.first_ply == _USER_BLUNDER_PLY - 4


# ---------------------------------------------------------------------------
# D-10 no repeats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeat_prompted_blunder_is_never_composed_again(test_engine, monkeypatch) -> None:
    _force_shape(monkeypatch, WindowShape(3, 1))
    caller = await _user(test_engine, "bcs-rep-prompted")
    (game_id,) = await _seed_games(test_engine, caller, 1)
    prior = await _insert_prior_window(
        test_engine,
        user_id=caller,
        game_id=game_id,
        first_ply=36,
        blunder_ply=_USER_BLUNDER_PLY,
        window_length=3,
        answer_plies=[36, 38, _USER_BLUNDER_PLY],
    )
    try:
        windows = await _compose(test_engine, caller)
    finally:
        await delete_blunder_check_sessions(test_engine, [prior])
        await delete_games(test_engine, [game_id])
    assert windows == []


@pytest.mark.asyncio
async def test_repeat_false_alarm_before_blunder_leaves_it_eligible(
    test_engine, monkeypatch
) -> None:
    _force_shape(monkeypatch, WindowShape(3, 1))
    caller = await _user(test_engine, "bcs-rep-alarm")
    (game_id,) = await _seed_games(test_engine, caller, 1)
    # The prior window ended on a false alarm at its first move: the blunder was never prompted.
    prior = await _insert_prior_window(
        test_engine,
        user_id=caller,
        game_id=game_id,
        first_ply=34,
        blunder_ply=_USER_BLUNDER_PLY,
        window_length=4,
        answer_plies=[34],
    )
    try:
        windows = await _compose(test_engine, caller)
    finally:
        await delete_blunder_check_sessions(test_engine, [prior])
        await delete_games(test_engine, [game_id])
    assert [w.blunder_ply for w in windows] == [_USER_BLUNDER_PLY]


@pytest.mark.asyncio
async def test_repeat_herring_never_overlaps_a_served_range(test_engine, monkeypatch) -> None:
    _force_shape(monkeypatch, WindowShape(3, None))
    caller = await _user(test_engine, "bcs-rep-herring")
    (game_id,) = await _seed_games(test_engine, caller, 1)
    served_first, served_last = 20, 24
    prior = await _insert_prior_window(
        test_engine,
        user_id=caller,
        game_id=game_id,
        first_ply=served_first,
        blunder_ply=None,
        window_length=3,
        answer_plies=[20, 22, 24],
    )
    try:
        composed = [await _compose(test_engine, caller, seed=seed) for seed in _SEEDS]
    finally:
        await delete_blunder_check_sessions(test_engine, [prior])
        await delete_games(test_engine, [game_id])
    windows = [window for batch in composed for window in batch]
    assert windows, "the game still supplies herring runs outside the served range"
    for window in windows:
        last = _last_judged_ply(window)
        assert last < served_first or window.first_ply > served_last


# ---------------------------------------------------------------------------
# D-07 miss lead-in and short sessions
# ---------------------------------------------------------------------------

_GIFT_PLY = 33  # black (opponent) blunders and hands the white user an advantage
_MISS_PLY = 34  # the user fails to use it


@pytest.mark.asyncio
async def test_miss_lead_in_ends_with_the_opponents_blunder(test_engine, monkeypatch) -> None:
    _force_shape(monkeypatch, WindowShape(3, 1))
    caller = await _user(test_engine, "bcs-miss")
    # The gift stays inside the undecided band (+/- 300), or the miss would not be served.
    evals = with_opponent_gift(flat_evals(_ROWS, 0), _GIFT_PLY, BLUNDER_MAX_PRE_EVAL_CP)
    evals = with_user_blunder(evals, _MISS_PLY, BLUNDER_MAX_PRE_EVAL_CP)
    game_id = await seed_judged_game(
        test_engine,
        user_id=caller,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=_MISS_PLY, is_miss=True)],
    )
    try:
        windows = await _compose(test_engine, caller)
    finally:
        await delete_games(test_engine, [game_id])
    assert len(windows) == 1
    window = windows[0]
    assert window.window_case == WindowCase.PURE_MISS
    assert (window.blunder_ply, window.first_ply) == (_MISS_PLY, _MISS_PLY)
    pgn_game = chess.pgn.read_game(io.StringIO(SEED_PGN))
    assert pgn_game is not None
    opponent_blunder = list(pgn_game.mainline_moves())[_GIFT_PLY].uci()
    assert window.lead_in_plies == LEAD_IN_PLIES
    assert window.move_ucis.split()[window.lead_in_plies - 1] == opponent_blunder


@pytest.mark.asyncio
async def test_short_session_keeps_gap_free_positions(test_engine) -> None:
    caller = await _user(test_engine, "bcs-short")
    game_ids = await _seed_games(test_engine, caller, 2)
    try:
        windows = await _compose(test_engine, caller, seed=2)
    finally:
        await delete_games(test_engine, game_ids)
    assert [w.position for w in windows] == [0, 1]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_build_snapshot_includes_lead_in_and_reply() -> None:
    snapshot = build_snapshot(SEED_PGN, first_ply=10, last_ply=14)
    assert snapshot is not None
    assert snapshot.lead_in_plies == LEAD_IN_PLIES == 1
    # Plies 9..15: lead-in (1) + judged span 10..14 (5 plies) + the reply at 15.
    assert len(snapshot.move_ucis.split()) == 7
    board = chess.Board(snapshot.start_fen)
    for uci in snapshot.move_ucis.split():
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)


def test_build_snapshot_clamps_at_game_start_and_rejects_past_end() -> None:
    early = build_snapshot(SEED_PGN, first_ply=0, last_ply=4)
    assert early is not None
    assert early.lead_in_plies == 0
    assert early.start_fen == chess.STARTING_FEN
    assert build_snapshot(SEED_PGN, first_ply=58, last_ply=70) is None
    assert build_snapshot("not a pgn at all (", first_ply=4, last_ply=6) is None


def test_reference_elo_is_the_median_pinned_elo() -> None:
    rows = [
        EloSourceRow(
            platform="lichess", time_control_bucket="blitz", time_control_str="300+0", rating=r
        )
        for r in (1400, 1500, 1800)
    ]
    assert reference_elo(rows) == 1500
    assert reference_elo([]) is None
