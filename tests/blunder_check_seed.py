"""Shared seed helpers for the blunder-check tests (Phase 249, plans 02-05).

No test functions live here. Every caller must delete the games it seeds in `finally`
(`delete_games`): leaked non-guest fully evaluated games poison the global tier-3
lottery and the foreign-pick tests of other modules.

Eval convention (post-move, see `app.services.flaws_service._run_all_moves_pass`): the
eval_cp stored on row P is the white-POV eval AFTER the move played FROM position P. The
mover at row P is white when P is even. A blunder at ply P therefore shows up as a drop
of the mover's eval between row P-1 and row P.
"""

from __future__ import annotations

import datetime
import io
import itertools
import uuid
from dataclasses import dataclass

import chess
import chess.pgn
import httpx
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.blunder_check import BlunderCheckSession
from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.services.flaws_service import _run_all_moves_pass

# A fixed legal mainline of 60 plies (a seeded quiet playout; no check/capture drama so
# every ply has legal moves). Verified legal by `seed_judged_game`'s replay.
SEED_PGN = (
    "1. d3 b5 2. a3 f6 3. b3 a5 4. c3 c5 5. b4 h5 6. Qd2 Rh7 7. d4 h4 8. Ra2 Qc7 9. Nh3 Qb6 "
    "10. Qh6 Qa6 11. Nd2 Ra7 12. Rb2 Rb7 13. Qe3 Qb6 14. Qd3 Qc7 15. Kd1 Rh8 16. Qb1 Qf4 "
    "17. Qe4 e5 18. Kc2 Rh5 19. Kd3 Qh6 20. Nf4 c4+ 21. Kc2 d6 22. Ng6 Be7 23. Nf4 Bd7 "
    "24. g3 Rb6 25. Ne6 Nc6 26. a4 Rb8 27. Rb3 Bd8 28. Kb1 Rg5 29. Nc5 Rg4 30. Qc2 Qh8 *"
)

_FULL_EVALS_AT = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
_DEFAULT_PASSWORD = "testpass123!"
# Per-call counter so hash columns of different seeded games never collide.
_HASH_COUNTER = itertools.count(1)
_HASH_STRIDE = 1000
_PHASE_MIDDLEGAME = 1
_BLUNDER_SEVERITY = 2


# Comfortably above FACEPALM_SCORE_MIN, so a default seeded blunder always qualifies.
SEED_FACEPALM_SCORE: float = 0.95


@dataclass(frozen=True)
class SeedBlunder:
    """A blunder flaw row to seed (the facepalm score defaults to a qualifying value)."""

    ply: int
    is_miss: bool = False
    facepalm_score: float | None = SEED_FACEPALM_SCORE


def flat_evals(count: int, cp: int) -> list[int]:
    """`count` rows of the same white-POV eval (row P = eval after the move from P)."""
    return [cp] * count


def _shift_mover_eval(evals: list[int], ply: int, loss_cp: int) -> list[int]:
    """Copy of `evals` where the mover at `ply` loses `loss_cp` for good (sign follows parity).

    Row `ply` and every later row shift, so the opponent reply right after is not itself a drop.
    """
    out = list(evals)
    mover_is_white = ply % 2 == 0
    delta = -loss_cp if mover_is_white else loss_cp
    for row in range(ply, len(out)):
        out[row] += delta  # the swing persists: later moves keep the new balance
    return out


def with_user_blunder(evals: list[int], ply: int, drop_cp: int) -> list[int]:
    """Make the move played from row `ply` a blunder: the mover's eval drops by `drop_cp`.

    Post-move convention: row `ply`'s eval is the eval AFTER the move played from `ply`,
    so the drop is applied to that row. The mover is white when `ply` is even, so white
    loses by decreasing the white-POV eval and black by increasing it. Whether that mover
    is "the user" is decided by the game's user_color, not here.
    """
    return _shift_mover_eval(evals, ply, drop_cp)


def with_opponent_gift(evals: list[int], ply: int, gift_cp: int) -> list[int]:
    """Make the move played from row `ply` (an opponent move) hand over `gift_cp`.

    Same math as `with_user_blunder` (the mover at `ply` loses `gift_cp` under the post-move
    convention); the separate name documents the intent in a test: the opponent's blunder
    gifts the user an advantage.
    """
    return _shift_mover_eval(evals, ply, gift_cp)


async def register_user(
    email_prefix: str, *, beta: bool, test_engine, guest: bool = False
) -> tuple[int, str]:
    """Register + log in a user over HTTP; flip beta_enabled / is_guest by direct UPDATE."""
    email = f"{email_prefix}-{uuid.uuid4().hex[:10]}@example.com"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post(
            "/api/auth/register", json={"email": email, "password": _DEFAULT_PASSWORD}
        )
        assert reg.status_code in (200, 201), f"register failed: {reg.text}"
        user_id = int(reg.json()["id"])
        login = await client.post(
            "/api/auth/jwt/login", data={"username": email, "password": _DEFAULT_PASSWORD}
        )
        assert login.status_code == 200, f"login failed: {login.text}"
        token = str(login.json()["access_token"])
    values: dict[str, bool] = {}
    if beta:
        values["beta_enabled"] = True
    if guest:
        values["is_guest"] = True
    if values:
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            await session.execute(update(User).where(User.id == user_id).values(**values))
            await session.commit()
    return user_id, token


def _replay_boards(pgn: str) -> tuple[list[chess.Board], list[chess.Move]]:
    """Boards BEFORE each move (index = ply) plus a final board, and the played moves."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    board = game.board()
    boards: list[chess.Board] = []
    moves: list[chess.Move] = []
    for node in game.mainline():
        boards.append(board.copy())
        moves.append(node.move)
        board.push(node.move)
    boards.append(board.copy())  # final position (no move played from it)
    return boards, moves


def _first_alternative(board: chess.Board, played: chess.Move | None) -> str:
    """First legal move in sorted UCI order that differs from `played`."""
    ucis = sorted(m.uci() for m in board.legal_moves)
    for uci in ucis:
        if played is None or uci != played.uci():
            return uci
    return ucis[0]


def _best_moves_for_blunders(
    boards: list[chess.Board], moves: list[chess.Move], blunder_plies: list[int]
) -> dict[int, str]:
    """best_move per ply: at each blunder ply an alternative to the played move (the key),
    at ply + 1 a legal opponent reply (the refutation). Blunder keys win collisions."""
    best: dict[int, str] = {}
    for ply in blunder_plies:
        best[ply] = _first_alternative(boards[ply], moves[ply])
    for ply in blunder_plies:
        nxt = ply + 1
        if nxt < len(moves) and nxt not in best:
            best[nxt] = _first_alternative(boards[nxt], None)
    return best


def _self_check(evals_cp: list[int], n_rows: int, blunders: list[SeedBlunder]) -> None:
    """Fail loudly when a seeded blunder ply is not recomputed as a blunder."""
    rows = [
        GamePosition(
            game_id=0,
            user_id=0,
            ply=i,
            full_hash=0,
            white_hash=0,
            black_hash=0,
            eval_cp=evals_cp[i] if i < len(evals_cp) else None,
            eval_mate=None,
        )
        for i in range(n_rows)
    ]
    classified = _run_all_moves_pass(rows)
    for blunder in blunders:
        entry = classified.get(blunder.ply)
        severity = None if entry is None else entry[1]
        if severity != "blunder":
            raise ValueError(
                f"seed self-check: ply {blunder.ply} recomputes as {severity!r}, not 'blunder'"
            )


async def seed_judged_game(
    test_engine,
    *,
    user_id: int,
    user_color: str = "white",
    evals_cp: list[int],
    blunders: list[SeedBlunder],
    white_rating: int | None = 1500,
    black_rating: int | None = 1500,
    platform: str = "lichess",
    time_control_bucket: str = "blitz",
    full_evals: bool = True,
) -> int:
    """Seed one fully evaluated game with its positions and blunder flaw rows; return game_id.

    Replays SEED_PGN to build plies 0..n (move_san, eval_cp from `evals_cp[ply]`, unique
    hashes). best_move is set at each blunder ply (an alternative to the played move) and at
    ply + 1 (a legal opponent reply). Raises ValueError when a seeded blunder ply is not
    recomputed as a blunder by the production classifier (fixture self-check).
    """
    boards, moves = _replay_boards(SEED_PGN)
    n_rows = len(boards)
    _self_check(evals_cp, n_rows, blunders)
    best = _best_moves_for_blunders(boards, moves, [b.ply for b in blunders])
    offset = next(_HASH_COUNTER) * _HASH_STRIDE * 10
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            game = Game(
                user_id=user_id,
                platform=platform,
                platform_game_id=str(uuid.uuid4()),
                platform_url="https://lichess.org/test",
                pgn=SEED_PGN,
                result="1-0",
                user_color=user_color,
                time_control_str="300+0",
                time_control_bucket=time_control_bucket,
                time_control_seconds=300,
                base_time_seconds=300,
                increment_seconds=0.0,
                white_rating=white_rating,
                black_rating=black_rating,
                rated=True,
                is_computer_game=False,
                ply_count=n_rows - 1,
                played_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc),
                full_evals_completed_at=_FULL_EVALS_AT if full_evals else None,
            )
            session.add(game)
            await session.flush()
            game_id: int = game.id
            for ply in range(n_rows):
                session.add(
                    GamePosition(
                        user_id=user_id,
                        game_id=game_id,
                        ply=ply,
                        full_hash=offset + ply,
                        white_hash=offset + _HASH_STRIDE + ply,
                        black_hash=offset + 2 * _HASH_STRIDE + ply,
                        move_san=boards[ply].san(moves[ply]) if ply < len(moves) else None,
                        eval_cp=evals_cp[ply] if ply < len(evals_cp) else None,
                        eval_mate=None,
                        best_move=best.get(ply),
                    )
                )
            for blunder in blunders:
                session.add(
                    GameFlaw(
                        user_id=user_id,
                        game_id=game_id,
                        ply=blunder.ply,
                        severity=_BLUNDER_SEVERITY,
                        phase=_PHASE_MIDDLEGAME,
                        is_miss=blunder.is_miss,
                        is_lucky=False,
                        is_reversed=False,
                        is_squandered=False,
                        fen=boards[blunder.ply].board_fen(),
                        facepalm_score=blunder.facepalm_score,
                    )
                )
    return game_id


async def delete_games(test_engine, game_ids: list[int]) -> None:
    """Delete seeded games (positions and flaws cascade)."""
    if not game_ids:
        return
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            await session.execute(delete(Game).where(Game.id.in_(game_ids)))


async def delete_blunder_check_sessions(test_engine, session_ids: list[int]) -> None:
    """Delete blunder-check sessions (windows and answers cascade)."""
    if not session_ids:
        return
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            await session.execute(
                delete(BlunderCheckSession).where(BlunderCheckSession.id.in_(session_ids))
            )
