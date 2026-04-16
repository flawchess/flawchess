"""Shared seeded-user fixture for router integration tests (Phase 61).

Provides a single authoritative test user with a deterministic portfolio of
games and positions, committed to flawchess_test so HTTP endpoints can observe
the data through the patched async_session_maker. The seeded_user fixture is
module-scoped: register+seed cost is paid once per test module, not once per
test function.

Expected aggregates are computed once and returned alongside the user data so
test assertions can reference them by name rather than hand-counting.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest_asyncio

from app.main import app
from app.repositories.endgame_repository import ENDGAME_PLY_THRESHOLD

# Deterministic Zobrist hash used for every game's ply=0 position so
# /api/openings/next-moves queries at the starting position match all games.
STARTING_POSITION_HASH: int = 0x0123456789ABCDEF


@dataclass
class SeededUser:
    """Test user with a committed portfolio and derived expected aggregates."""

    id: int
    email: str
    auth_headers: dict[str, str]
    expected: dict[str, Any] = field(default_factory=dict)


# Portfolio spec: 15 games across platforms, time controls, colors, results.
# Hand-counted aggregates live in EXPECTED below and must be kept in sync with
# this list — Plan 61-02's router tests assert against EXPECTED directly.
_GAMES_SPEC: list[dict[str, Any]] = [
    # platform,       bucket,       color,    result,    rated, endgame
    {
        "platform": "chess.com",
        "bucket": "blitz",
        "color": "white",
        "result": "1-0",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "chess.com",
        "bucket": "blitz",
        "color": "white",
        "result": "1-0",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "chess.com",
        "bucket": "blitz",
        "color": "white",
        "result": "1/2-1/2",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "chess.com",
        "bucket": "blitz",
        "color": "black",
        "result": "0-1",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "chess.com",
        "bucket": "blitz",
        "color": "black",
        "result": "1-0",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "chess.com",
        "bucket": "rapid",
        "color": "white",
        "result": "0-1",
        "rated": True,
        "endgame": [1],
    },
    {
        "platform": "chess.com",
        "bucket": "rapid",
        "color": "white",
        "result": "0-1",
        "rated": True,
        "endgame": [1],
    },
    {
        "platform": "lichess",
        "bucket": "blitz",
        "color": "white",
        "result": "1-0",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "lichess",
        "bucket": "blitz",
        "color": "white",
        "result": "1-0",
        "rated": True,
        "endgame": [1],
    },
    {
        "platform": "lichess",
        "bucket": "bullet",
        "color": "black",
        "result": "1/2-1/2",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "lichess",
        "bucket": "bullet",
        "color": "black",
        "result": "1/2-1/2",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "lichess",
        "bucket": "classical",
        "color": "white",
        "result": "1-0",
        "rated": True,
        "endgame": [3],
    },
    {
        "platform": "lichess",
        "bucket": "classical",
        "color": "white",
        "result": "0-1",
        "rated": True,
        "endgame": None,
    },
    {
        "platform": "lichess",
        "bucket": "rapid",
        "color": "white",
        "result": "1-0",
        "rated": False,
        "endgame": None,
    },
    {
        "platform": "lichess",
        "bucket": "rapid",
        "color": "white",
        "result": "1/2-1/2",
        "rated": True,
        "endgame": [1, 3],
    },  # transition
]

# Expected aggregates derived from _GAMES_SPEC. Kept explicit so the router
# tests read as "portfolio → known numbers" rather than recomputing from spec.
EXPECTED: dict[str, Any] = {
    "total_games": 15,
    "global_wdl": {"wins": 7, "draws": 4, "losses": 4},
    "by_platform": {"chess.com": 7, "lichess": 8},
    "by_time_control": {"bullet": 2, "blitz": 7, "rapid": 4, "classical": 2},
    "by_color": {
        "white": {"total": 11, "wins": 6, "draws": 2, "losses": 3},
        "black": {"total": 4, "wins": 1, "draws": 2, "losses": 1},
    },
    "rated_total": 14,
    "endgame_games_distinct": 5,  # games 6,7,9,12,15 — game 15 has two classes but counts once
    "endgame_rook_games": 4,  # games 6,7,9,15
    "endgame_pawn_games": 2,  # games 12,15
    "starting_position_game_count": 15,
}


async def _register_and_login(
    client: httpx.AsyncClient,
) -> tuple[int, str, dict[str, str]]:
    email = f"seed_{uuid.uuid4().hex[:10]}@example.com"
    password = "seededuserpw123"
    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    reg.raise_for_status()
    user_id = int(reg.json()["id"])

    login = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    return user_id, email, {"Authorization": f"Bearer {token}"}


async def _seed_portfolio(user_id: int) -> None:
    """Commit 15 games + their positions for the registered user.

    Uses the patched async_session_maker (bound to flawchess_test by
    tests/conftest.py override_get_async_session) directly, so the writes
    land in the test DB and are visible to HTTP endpoints in the same run.
    """
    from app.core.database import async_session_maker
    from app.models.game import Game
    from app.models.game_position import GamePosition

    base_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)

    async with async_session_maker() as session:
        for idx, spec in enumerate(_GAMES_SPEC, start=1):
            color = spec["color"]
            game = Game(
                user_id=user_id,
                platform=spec["platform"],
                platform_game_id=f"seed-{idx:02d}",
                platform_url=f"https://example.com/game/{idx}",
                pgn="1. e4 e5 *",
                result=spec["result"],
                user_color=color,
                time_control_str="600+0",
                time_control_bucket=spec["bucket"],
                time_control_seconds=600,
                rated=spec["rated"],
                is_computer_game=False,
                white_username="seededuser" if color == "white" else "opponent",
                black_username="opponent" if color == "white" else "seededuser",
                white_rating=1500,
                black_rating=1510,
            )
            game.played_at = base_dt + datetime.timedelta(days=idx)
            session.add(game)
            await session.flush()

            # Starting position (ply=0, shared hash across all 15 games)
            session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=user_id,
                    ply=0,
                    full_hash=STARTING_POSITION_HASH,
                    white_hash=STARTING_POSITION_HASH + 1,
                    black_hash=STARTING_POSITION_HASH + 2,
                    move_san="e4",
                )
            )
            # Game-specific ply=1 position (deterministic per-game hashes)
            session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=user_id,
                    ply=1,
                    full_hash=STARTING_POSITION_HASH + 1000 + idx,
                    white_hash=STARTING_POSITION_HASH + 2000 + idx,
                    black_hash=STARTING_POSITION_HASH + 3000 + idx,
                    move_san="e5",
                )
            )

            # Endgame spans (if specified). Each class span covers
            # ENDGAME_PLY_THRESHOLD consecutive plies starting at ply=30.
            if spec["endgame"] is not None:
                span_start_ply = 30
                for class_int in spec["endgame"]:
                    if class_int == 1:
                        sig, imbalance = "KR_KR", 0
                    elif class_int == 3:
                        sig, imbalance = "KPP_KP", 100
                    else:
                        sig, imbalance = "KR_K", 0
                    for offset in range(ENDGAME_PLY_THRESHOLD):
                        session.add(
                            GamePosition(
                                game_id=game.id,
                                user_id=user_id,
                                ply=span_start_ply + offset,
                                full_hash=STARTING_POSITION_HASH + 10_000 + idx * 100 + offset,
                                white_hash=STARTING_POSITION_HASH + 20_000 + idx * 100 + offset,
                                black_hash=STARTING_POSITION_HASH + 30_000 + idx * 100 + offset,
                                piece_count=2,
                                material_count=1000,
                                material_signature=sig,
                                material_imbalance=imbalance,
                                endgame_class=class_int,
                            )
                        )
                    span_start_ply += ENDGAME_PLY_THRESHOLD

        await session.commit()


@pytest_asyncio.fixture(scope="module")
async def seeded_user() -> SeededUser:
    """Register one user + commit the deterministic portfolio; return handle."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, email, auth_headers = await _register_and_login(client)
    await _seed_portfolio(user_id)
    return SeededUser(
        id=user_id,
        email=email,
        auth_headers=auth_headers,
        expected=dict(EXPECTED),
    )
