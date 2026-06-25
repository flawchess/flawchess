"""Integration tests for GET /api/library/flaws/{game_id}/{ply}/tactic-lines (Phase 135, Plan 01).

Coverage:
- test_200_shape              : authenticated request for owned flaw returns 200 with TacticLinesResponse fields
- test_404_wrong_user         : requesting another user's flaw returns 404 (IDOR; not 403)
- test_404_missing            : game_id/ply with no game_flaws row returns 404
- test_401_unauthenticated    : no-auth returns 401
- test_no_hash_leak           : JSON body never exposes internal Zobrist hash field names
"""

from __future__ import annotations

import datetime
import uuid

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition


ENDPOINT_TMPL = "/api/library/flaws/{game_id}/{ply}/tactic-lines"

# A simple legal position: starting position FEN (piece-placement only)
_STARTING_BOARD_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
# A PV for white from the starting position (1. e4 e5 2. Nf3 Nc6 ...)
_MISSED_PV = "e2e4 e7e5 g1f3 b8c6"
_ALLOWED_PV = "e7e5 g1f3"

# Tactic motif ints used (from TacticMotifInt enum — FORK=1)
_FORK_INT = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(email: str, password: str = "testpass123!") -> tuple[int, str]:
    """Register a user via HTTP and return (user_id, auth_token)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post("/api/auth/register", json={"email": email, "password": password})
        assert reg.status_code in (200, 201), f"register failed: {reg.text}"
        user_id = int(reg.json()["id"])

        login = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200, f"login failed: {login.text}"
        token = str(login.json()["access_token"])
    return user_id, token


async def _seed_game_and_flaw(
    test_engine,
    user_id: int,
    *,
    ply: int = 10,
    missed_tactic_motif: int | None = _FORK_INT,
    missed_tactic_confidence: int | None = 85,
    missed_tactic_depth: int | None = 2,
    allowed_tactic_motif: int | None = _FORK_INT,
    allowed_tactic_confidence: int | None = 85,
    allowed_tactic_depth: int | None = 1,
    missed_pv: str | None = _MISSED_PV,
    allowed_pv: str | None = _ALLOWED_PV,
) -> tuple[int, int]:
    """Seed a game + flaw row + two game_position rows. Returns (game_id, ply)."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            game = Game(
                user_id=user_id,
                platform="lichess",
                platform_game_id=str(uuid.uuid4()),
                platform_url="https://lichess.org/test",
                pgn="1. e4 e5 *",
                result="1-0",
                user_color="white",
                time_control_str="600+0",
                time_control_bucket="blitz",
                time_control_seconds=600,
                base_time_seconds=600,
                increment_seconds=0.0,
                rated=True,
                is_computer_game=False,
                ply_count=40,
                full_evals_completed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            )
            session.add(game)
            await session.flush()
            game_id: int = game.id

            # GameFlaw row at the flaw ply
            flaw = GameFlaw(
                user_id=user_id,
                game_id=game_id,
                ply=ply,
                severity=2,
                phase=1,
                is_miss=False,
                is_lucky=False,
                is_reversed=False,
                is_squandered=False,
                fen=_STARTING_BOARD_FEN,  # board_fen() before the flaw
                missed_tactic_motif=missed_tactic_motif,
                missed_tactic_confidence=missed_tactic_confidence,
                missed_tactic_depth=missed_tactic_depth,
                allowed_tactic_motif=allowed_tactic_motif,
                allowed_tactic_confidence=allowed_tactic_confidence,
                allowed_tactic_depth=allowed_tactic_depth,
            )
            session.add(flaw)

            # game_position at flaw ply (missed PV source + move_san + best_move)
            pos_n = GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=ply,
                full_hash=1001,
                white_hash=2001,
                black_hash=3001,
                move_san="e4",
                best_move="e2e4",
                pv=missed_pv,
            )
            session.add(pos_n)

            # game_position at flaw ply+1 (allowed PV source)
            pos_n1 = GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=ply + 1,
                full_hash=1002,
                white_hash=2002,
                black_hash=3002,
                move_san="e5",
                pv=allowed_pv,
            )
            session.add(pos_n1)

    return game_id, ply


async def _delete_games(test_engine, game_ids: list[int]) -> None:
    """Delete seeded games (cleanup)."""
    if not game_ids:
        return
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            await session.execute(delete(Game).where(Game.id.in_(game_ids)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_200_shape(test_engine) -> None:
    """Authenticated request for owned tagged flaw returns 200 with TacticLinesResponse fields."""
    email = f"tac-lines-200-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    game_id, ply = await _seed_game_and_flaw(test_engine, user_id)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                ENDPOINT_TMPL.format(game_id=game_id, ply=ply),
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()

        # Core fields required by TacticLinesResponse
        assert "missed_moves" in body
        assert "missed_depth" in body
        assert "missed_tactic_ply_index" in body
        assert "missed_motif" in body
        assert "allowed_moves" in body
        assert "allowed_depth" in body
        assert "allowed_tactic_ply_index" in body
        assert "allowed_motif" in body
        assert "position_fen" in body
        assert "flaw_move_san" in body
        assert "best_move_uci" in body
        assert "flaw_ply" in body

        # position_fen is a full FEN (contains side-to-move)
        assert body["position_fen"] is not None
        assert isinstance(body["position_fen"], str)
        assert body["flaw_ply"] == ply
    finally:
        await _delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_404_wrong_user(test_engine) -> None:
    """Requesting a flaw belonging to another user returns 404 — not 403 (IDOR; T-135-01)."""
    # Seed flaw under user B
    email_b = f"tac-lines-idor-b-{uuid.uuid4().hex[:8]}@example.com"
    user_id_b, _token_b = await _register_and_login(email_b)
    game_id, ply = await _seed_game_and_flaw(test_engine, user_id_b)

    # Authenticate as user A
    email_a = f"tac-lines-idor-a-{uuid.uuid4().hex[:8]}@example.com"
    _user_id_a, token_a = await _register_and_login(email_a)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                ENDPOINT_TMPL.format(game_id=game_id, ply=ply),
                headers={"Authorization": f"Bearer {token_a}"},
            )

        assert resp.status_code == 404, f"Expected 404 for IDOR, got {resp.status_code}"
        assert resp.json().get("detail") == "Flaw not found"
    finally:
        await _delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_404_missing(test_engine) -> None:
    """Requesting a game_id/ply with no game_flaws row returns 404."""
    email = f"tac-lines-404-{uuid.uuid4().hex[:8]}@example.com"
    _user_id, token = await _register_and_login(email)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            ENDPOINT_TMPL.format(game_id=999999999, ply=1),
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404
    assert resp.json().get("detail") == "Flaw not found"


@pytest.mark.asyncio
async def test_401_unauthenticated() -> None:
    """Unauthenticated request returns 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(ENDPOINT_TMPL.format(game_id=1, ply=1))

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_no_hash_leak(test_engine) -> None:
    """JSON response body never exposes internal Zobrist hash field names (T-135-03).

    API responses must expose only FEN/SAN/depth/motif — never internal hashes
    (CLAUDE.md "API responses never expose internal hashes").
    """
    email = f"tac-lines-hash-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    game_id, ply = await _seed_game_and_flaw(test_engine, user_id)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                ENDPOINT_TMPL.format(game_id=game_id, ply=ply),
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body_text = resp.text
        assert "white_hash" not in body_text, "white_hash must not appear in response"
        assert "black_hash" not in body_text, "black_hash must not appear in response"
        assert "full_hash" not in body_text, "full_hash must not appear in response"
    finally:
        await _delete_games(test_engine, [game_id])
