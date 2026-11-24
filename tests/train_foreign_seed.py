"""Shared seed helpers for the Phase 263 foreign-blunder-filler tests.

No test functions live here. The foreign draw is global across users (it samples other users'
games), so a caller that COMMITS seeded rows must delete them in `finally`
(`tests.blunder_check_seed.delete_games` for games, plus the stranger user), or the rows leak
into every other test that draws foreign material. A caller that seeds through the rolled-back
`db_session` fixture needs no cleanup.

Eval convention (see `tests.blunder_check_seed`): the eval stored on row P is the white-POV eval
AFTER the move played FROM position P. A blunder flaw at ply P therefore reads its "before"
eval from row P - 1, which `add_foreign_blunder_game` seeds as `prior_eval_cp`.
"""

from __future__ import annotations

import datetime
import itertools
import uuid

import chess
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from tests.blunder_check_seed import SEED_PGN, _replay_boards

# White's second move of SEED_PGN (ply 2, 0-based, white even), so the flaw is the owner's move
# for user_color white.
FOREIGN_SEED_PLY: int = 2
# Clears WINNABILITY_FLOOR_ES for White.
FOREIGN_PRIOR_EVAL_CP: int = 300

# Two distinct legal moves in the position before ply 2 of SEED_PGN (after 1. d3 b5), neither
# equal to the move the game plays there (a3).
FOREIGN_KEY_UCI: str = "e2e4"
FOREIGN_RUNNER_UP_UCI: str = "c2c4"

# Below the dead band (gap ~0.009 < INACCURACY_DROP) so dead_band_admissible passes; the second
# best (30 cp) is nowhere near winning so second_best_not_winning_admissible passes; the gap is
# below SHARP_GAP_ES so the puzzle classifies as soft.
FOREIGN_SOFT_PV_LINES: list[dict[str, object]] = [
    {"b": 40, "bm": None, "s": 30, "sm": None, "su": FOREIGN_RUNNER_UP_UCI}
]
# Gap ~0.5 ES (200 vs -200 cp) is above BLUNDER_DROP so the dead band does not exclude it; the
# runner-up is -200 cp for White so second_best_not_winning_admissible passes; the gap is above
# SHARP_GAP_ES so the puzzle classifies as sharp.
FOREIGN_SHARP_PV_LINES: list[dict[str, object]] = [
    {"b": 200, "bm": None, "s": -200, "sm": None, "su": FOREIGN_RUNNER_UP_UCI}
]

_FULL_EVALS_AT = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
_PLAYED_AT = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)
_BLUNDER_SEVERITY = 2
_PHASE_MIDDLEGAME = 1
_PLY_COUNT = 60
# Per-call counter so hash columns of different seeded games never collide.
_HASH_COUNTER = itertools.count(1)
_HASH_STRIDE = 1000
_HASH_BASE = 50_000_000


def _assert_seed_moves_legal() -> None:
    """Import-time guard: the key and runner-up are legal and differ from the played move."""
    boards, moves = _replay_boards(SEED_PGN)
    board = boards[FOREIGN_SEED_PLY]
    legal = {move.uci() for move in board.legal_moves}
    played = moves[FOREIGN_SEED_PLY].uci()
    for uci in (FOREIGN_KEY_UCI, FOREIGN_RUNNER_UP_UCI):
        assert uci in legal, f"{uci} is not legal before ply {FOREIGN_SEED_PLY}"
        assert uci != played, f"{uci} equals the move the game plays"
    assert FOREIGN_KEY_UCI != FOREIGN_RUNNER_UP_UCI
    assert chess.Move.from_uci(FOREIGN_KEY_UCI) in board.legal_moves


_assert_seed_moves_legal()


async def add_stranger(session: AsyncSession, *, label: str, is_guest: bool = False) -> int:
    """Add a `User` with a unique email and flush; returns the user id."""
    user = User(
        email=f"{label}-{uuid.uuid4().hex[:10]}@example.com",
        hashed_password="fakehash",
        is_guest=is_guest,
    )
    session.add(user)
    await session.flush()
    user_id: int = user.id
    return user_id


async def add_rated_games(
    session: AsyncSession,
    *,
    user_id: int,
    rating: int,
    count: int,
    platform: str = "lichess",
    time_control_bucket: str = "blitz",
) -> list[int]:
    """Rated, human-opponent games for `user_id` with that user-side rating and no flaws.

    Sets a solver's level through `user_level_elo` (the median pinned Elo of recent rated games).
    """
    game_ids: list[int] = []
    for _ in range(count):
        game = Game(
            user_id=user_id,
            platform=platform,
            platform_game_id=str(uuid.uuid4()),
            platform_url="https://lichess.org/test",
            pgn=SEED_PGN,
            result="1-0",
            user_color="white",
            time_control_str="300+0",
            time_control_bucket=time_control_bucket,
            time_control_seconds=300,
            base_time_seconds=300,
            increment_seconds=0.0,
            white_rating=rating,
            black_rating=rating,
            rated=True,
            is_computer_game=False,
            ply_count=_PLY_COUNT,
            played_at=_PLAYED_AT,
        )
        session.add(game)
        await session.flush()
        game_ids.append(game.id)
    return game_ids


async def add_foreign_blunder_game(
    session: AsyncSession,
    *,
    owner_id: int,
    owner_rating: int,
    missed_pv_lines: list[dict[str, object]] | None = FOREIGN_SOFT_PV_LINES,
    ply: int = FOREIGN_SEED_PLY,
    prior_eval_cp: int | None = FOREIGN_PRIOR_EVAL_CP,
    severity: int = _BLUNDER_SEVERITY,
    platform: str = "lichess",
    time_control_bucket: str = "blitz",
    time_control_str: str = "300+0",
) -> int:
    """One game owned by `owner_id` carrying one blunder flaw; returns the game id.

    The owner plays white, both ratings equal `owner_rating`. The flaw's `best_move` lives on the
    `GamePosition` at `ply` (= `FOREIGN_KEY_UCI`), its prior eval on the position at `ply - 1`.
    Never commits; a router-level caller commits itself.
    """
    boards, moves = _replay_boards(SEED_PGN)
    offset = _HASH_BASE + next(_HASH_COUNTER) * _HASH_STRIDE * 10
    game = Game(
        user_id=owner_id,
        platform=platform,
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn=SEED_PGN,
        result="1-0",
        user_color="white",
        time_control_str=time_control_str,
        time_control_bucket=time_control_bucket,
        time_control_seconds=300,
        base_time_seconds=300,
        increment_seconds=0.0,
        white_rating=owner_rating,
        black_rating=owner_rating,
        rated=True,
        is_computer_game=False,
        ply_count=_PLY_COUNT,
        played_at=_PLAYED_AT,
        full_evals_completed_at=_FULL_EVALS_AT,
    )
    session.add(game)
    await session.flush()
    game_id: int = game.id

    flaw_kwargs: dict[str, object] = dict(
        user_id=owner_id,
        game_id=game_id,
        ply=ply,
        severity=severity,
        phase=_PHASE_MIDDLEGAME,
        is_miss=False,
        is_lucky=False,
        is_reversed=False,
        is_squandered=False,
        fen=boards[ply].board_fen(),
    )
    if missed_pv_lines is not None:
        # JSONB gotcha (project_asyncpg_jsonb_null_vs_sql_null): omit the column entirely for a
        # true SQL NULL rather than passing None explicitly.
        flaw_kwargs["missed_pv_lines"] = missed_pv_lines
    session.add(GameFlaw(**flaw_kwargs))

    if prior_eval_cp is not None:
        session.add(
            GamePosition(
                user_id=owner_id,
                game_id=game_id,
                ply=ply - 1,
                full_hash=offset + ply - 1,
                white_hash=offset + _HASH_STRIDE + ply - 1,
                black_hash=offset + 2 * _HASH_STRIDE + ply - 1,
                eval_cp=prior_eval_cp,
                eval_mate=None,
            )
        )
    session.add(
        GamePosition(
            user_id=owner_id,
            game_id=game_id,
            ply=ply,
            full_hash=offset + ply,
            white_hash=offset + _HASH_STRIDE + ply,
            black_hash=offset + 2 * _HASH_STRIDE + ply,
            move_san=boards[ply].san(moves[ply]),
            eval_cp=None,
            eval_mate=None,
            best_move=FOREIGN_KEY_UCI,
        )
    )
    await session.flush()
    return game_id


async def delete_flaw_row(
    session: AsyncSession, *, game_id: int, ply: int = FOREIGN_SEED_PLY
) -> None:
    """Delete one owner `game_flaws` row (the reclassification a lazy eviction reacts to)."""
    await session.execute(delete(GameFlaw).where(GameFlaw.game_id == game_id, GameFlaw.ply == ply))
    await session.flush()


async def delete_game_row(session: AsyncSession, *, game_id: int) -> None:
    """Delete one game (its flaw and position rows cascade, `drill_solves.game_id` goes NULL)."""
    await session.execute(delete(Game).where(Game.id == game_id))
    await session.flush()
