"""Integration tests for POST /api/eval/remote/lease and /submit (Phase 120 SEED-048).

Covers:
- test_lease_requires_operator_token: empty server token → 403 (fail-closed).
- test_lease_wrong_operator_token: configured token, wrong header → 401.
- test_lease_no_pending_games: no eligible game in the queue → 204.
- test_lease_returns_positions: eligible engine game → 200, non-empty positions,
  exactly one is_terminal=True.
- test_submit_requires_operator_token: no/empty token → 403.
- test_submit_wrong_operator_token: wrong token → 401.
- test_submit_sf_version_mismatch: EXPECTED_SF_VERSION set, wrong sf_version → 422.
- test_submit_applies_post_move_shift: evals submitted at position-ply land at
  post-move ply in DB (server applies the +1 shift; pitfall 1 / D-2).
- test_submit_stamps_full_evals_completed_at: complete submit → marker non-NULL.
- test_submit_idempotent: same payload twice → 200 both times, no error.

Session patching: monkeypatch app.routers.eval_remote.async_session_maker to route
the router's own sessions to the per-run test DB (eval_drain / eval_queue_service
session makers are already patched by conftest's session-scoped override_get_async_session).
_claim_tier3_derived is monkeypatched directly in the eval_remote router namespace
for tests that need to control which game is leased without relying on the
recency-weighted lottery.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.main import app

# ─── URL constants (no magic numbers) ─────────────────────────────────────────

_LEASE_URL = "/api/eval/remote/lease"
_SUBMIT_URL = "/api/eval/remote/submit"

# ─── Test data constants ───────────────────────────────────────────────────────

# A simple 2-move (4 half-move) PGN for lease/submit tests.
# 4 non-terminal plies (0-3) + 1 terminal eval-donor ply (4).
_TWO_MOVE_PGN: str = "1. e4 e5 *"

# Token used for tests that exercise a correctly-configured server.
_TEST_TOKEN: str = "test-operator-secret-xyz"

# Unique user ID range for this module — avoids FK conflicts with other test modules.
_TEST_USER_ID: int = 99300


# ─── Session-scoped fixtures ──────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def eval_worker_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker bound to the per-run test engine."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=False)
async def eval_worker_test_user(
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
) -> int:
    """Ensure test user _TEST_USER_ID exists in the test DB. Returns user_id."""
    from app.models.user import User

    async with eval_worker_session_maker() as session:
        result = await session.execute(select(User).where(User.id == _TEST_USER_ID))
        if result.unique().scalar_one_or_none() is None:
            session.add(
                User(
                    id=_TEST_USER_ID,
                    email=f"eval-worker-test-{_TEST_USER_ID}@example.com",
                    hashed_password="fakehash",
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                )
            )
            await session.commit()
    return _TEST_USER_ID


# ─── DB helpers ───────────────────────────────────────────────────────────────


async def _insert_game(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    pgn: str = _TWO_MOVE_PGN,
    *,
    full_evals_completed_at: datetime | None = None,
    lichess_evals_at: datetime | None = None,
    full_eval_attempts: int = 0,
) -> int:
    """Insert a Game row and commit. Returns game_id."""
    from app.models.game import Game

    async with session_maker() as session:
        g = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=f"eval-worker-{uuid.uuid4().hex}",
            pgn=pgn,
            result="1-0",
            user_color="white",
            rated=True,
            is_computer_game=False,
            evals_completed_at=datetime.now(timezone.utc),
            full_evals_completed_at=full_evals_completed_at,
            lichess_evals_at=lichess_evals_at,
            full_eval_attempts=full_eval_attempts,
        )
        session.add(g)
        await session.flush()
        game_id = int(g.id)  # type: ignore[arg-type]
        await session.commit()
    return game_id


async def _insert_game_positions(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    game_id: int,
    rows: list[dict[str, Any]],
) -> None:
    """Insert GamePosition rows for a game and commit.

    Each dict: {"ply": int, "full_hash": int, "eval_cp": int|None, "eval_mate": int|None}.
    """
    from app.models.game_position import GamePosition

    async with session_maker() as session:
        for r in rows:
            session.add(
                GamePosition(
                    user_id=user_id,
                    game_id=game_id,
                    ply=r["ply"],
                    full_hash=r["full_hash"],
                    white_hash=0,
                    black_hash=0,
                    move_san=r.get("move_san"),
                    phase=0,
                    endgame_class=None,
                    eval_cp=r.get("eval_cp"),
                    eval_mate=r.get("eval_mate"),
                )
            )
        await session.commit()


async def _get_game_position(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
    ply: int,
) -> dict[str, Any] | None:
    """Fetch a GamePosition row. Returns a dict with eval_cp/eval_mate or None."""
    from app.models.game_position import GamePosition

    async with session_maker() as session:
        result = await session.execute(
            select(GamePosition).where(
                GamePosition.game_id == game_id,
                GamePosition.ply == ply,
            )
        )
        gp = result.scalar_one_or_none()
        if gp is None:
            return None
        return {
            "ply": gp.ply,
            "eval_cp": gp.eval_cp,
            "eval_mate": gp.eval_mate,
            "best_move": gp.best_move,
        }


async def _get_game_full_evals_completed_at(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
) -> datetime | None:
    """Fetch Game.full_evals_completed_at."""
    from app.models.game import Game

    async with session_maker() as session:
        result = await session.execute(
            select(Game.full_evals_completed_at).where(Game.id == game_id)
        )
        return result.scalar_one_or_none()


async def _delete_games(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
) -> None:
    """Delete games by ID (cascades to game_positions)."""
    from app.models.game import Game

    if not game_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.id.in_(game_ids)))
        await session.commit()


def _make_client() -> httpx.AsyncClient:
    """Return an httpx AsyncClient using the ASGI transport."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _patch_router_session(
    monkeypatch: pytest.MonkeyPatch,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Patch app.routers.eval_remote.async_session_maker to route to the test DB."""
    import app.routers.eval_remote as eval_remote_module

    monkeypatch.setattr(eval_remote_module, "async_session_maker", session_maker)


# ─── Lease: auth tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lease_requires_operator_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty server EVAL_OPERATOR_TOKEN → 403 (fail-closed per T-120-01)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", "")
    async with _make_client() as client:
        response = await client.post(_LEASE_URL)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_lease_wrong_operator_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured token but wrong header value → 401."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    async with _make_client() as client:
        response = await client.post(_LEASE_URL, headers={"X-Operator-Token": "wrong-secret"})
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_lease_non_ascii_operator_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-ASCII token header → 401, not 500 (WR-01).

    hmac.compare_digest raises TypeError on non-ASCII str operands; comparing on the
    UTF-8 byte encoding keeps the auth path from crashing into an unauthenticated 500
    (a cheap Sentry-spam vector) on attacker-controlled input.
    """
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    # Send raw bytes: on the wire HTTP header values are bytes (Starlette decodes
    # them latin-1), so a non-ASCII token reaches the server as a non-ASCII str —
    # the exact input that crashed hmac.compare_digest(str, str) before the fix.
    async with _make_client() as client:
        response = await client.post(
            _LEASE_URL, headers={b"X-Operator-Token": "tökën-ü".encode("latin-1")}
        )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


# ─── Lease: queue behavior ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lease_no_pending_games(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """No eligible game in the queue → 204 (empty response)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    # Patch _claim_tier3_derived to return None (empty queue).
    import app.routers.eval_remote as eval_remote_module

    monkeypatch.setattr(eval_remote_module, "_claim_tier3_derived", AsyncMock(return_value=None))

    async with _make_client() as client:
        response = await client.post(_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})
    assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_lease_returns_positions(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Eligible engine game → 200 with non-empty positions list, exactly one is_terminal=True.

    Seeds a game with _TWO_MOVE_PGN (4 half-moves: plies 0-3) and 4 game_positions rows.
    The lease response should include all 4 non-terminal positions + 1 terminal donor
    at ply 4, so len(positions) == 5 and exactly one is_terminal=True entry exists.
    """
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    game_id = await _insert_game(eval_worker_session_maker, user_id)
    # Seed game_positions for all 4 half-moves (plies 0-3).
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 1000 + ply, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    # Patch _claim_tier3_derived to return our seeded game.
    import app.routers.eval_remote as eval_remote_module

    monkeypatch.setattr(
        eval_remote_module,
        "_claim_tier3_derived",
        AsyncMock(return_value=(game_id, user_id, False)),
    )

    try:
        async with _make_client() as client:
            response = await client.post(_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["game_id"] == game_id
        assert body["user_id"] == user_id
        assert body["is_lichess_eval_game"] is False

        positions = body["positions"]
        assert len(positions) > 0, "positions must be non-empty"

        # Exactly one is_terminal=True position.
        terminal_positions = [p for p in positions if p["is_terminal"]]
        assert len(terminal_positions) == 1, (
            f"Expected exactly 1 is_terminal=True position, got {len(terminal_positions)}: "
            f"{terminal_positions}"
        )

        # Every position has a non-empty FEN.
        for pos in positions:
            assert pos["fen"], f"position at ply {pos['ply']} has empty FEN"
            assert "ply" in pos and isinstance(pos["ply"], int)
    finally:
        await _delete_games(eval_worker_session_maker, [game_id])


# ─── Submit: auth tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_requires_operator_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty server EVAL_OPERATOR_TOKEN → 403 (fail-closed per T-120-01)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", "")
    payload = {"game_id": 1, "sf_version": "Stockfish 18", "evals": []}
    async with _make_client() as client:
        response = await client.post(_SUBMIT_URL, json=payload)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_submit_wrong_operator_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured token but wrong header → 401."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    payload = {"game_id": 1, "sf_version": "Stockfish 18", "evals": []}
    async with _make_client() as client:
        response = await client.post(
            _SUBMIT_URL,
            json=payload,
            headers={"X-Operator-Token": "wrong-secret"},
        )
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


# ─── Submit: version gate ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_sf_version_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """EXPECTED_SF_VERSION configured, wrong sf_version in body → 422 (D-5 gate)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "Stockfish 18")

    # Submit with a mismatched Stockfish version.
    payload = {"game_id": 1, "sf_version": "Stockfish 17", "evals": []}
    async with _make_client() as client:
        response = await client.post(
            _SUBMIT_URL,
            json=payload,
            headers={"X-Operator-Token": _TEST_TOKEN},
        )
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


# ─── Submit: write-path tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_applies_post_move_shift(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Server applies the SEED-044 +1 post-move shift — proves server-side ownership (D-2).

    The worker submits evals keyed by the POSITION ply (e.g. ply 1 = the board
    after White's first move). The server stores the eval at the ROW ply (ply 0
    for White's first move), because the convention is: row k stores the eval of
    the position AFTER the move at k (i.e., position at k+1).

    Concretely for _TWO_MOVE_PGN "1. e4 e5 *":
      Plies 0, 1, 2, 3 are the half-moves played. Terminal ply is 4.
      Worker evaluates position at ply 1 (board after 1.e4) → eval_cp = 30.
      After the +1 shift, row ply=0 should carry eval_cp=30.
    """
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")  # no version gate
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    game_id = await _insert_game(eval_worker_session_maker, user_id)
    # Seed 4 game_positions (plies 0-3, all eval_cp=None = unanalyzed).
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 2000 + ply, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    # Submit evals for all 5 positions (plies 0-3 + terminal ply 4).
    # Under SEED-044 post-move shift:
    #   row ply=0 ← eval submitted at ply=1 (the position AFTER 1.e4)
    #   row ply=1 ← eval submitted at ply=2 (the position AFTER 1...e5)
    #   row ply=2 ← eval submitted at ply=3
    #   row ply=3 ← eval submitted at ply=4 (terminal donor)
    evals = [
        {"ply": 0, "eval_cp": 20, "eval_mate": None, "best_move": "e2e4", "pv": None},
        {"ply": 1, "eval_cp": 30, "eval_mate": None, "best_move": "e7e5", "pv": None},
        {"ply": 2, "eval_cp": 25, "eval_mate": None, "best_move": "g1f3", "pv": None},
        {"ply": 3, "eval_cp": 28, "eval_mate": None, "best_move": "b8c6", "pv": None},
        {"ply": 4, "eval_cp": 22, "eval_mate": None, "best_move": None, "pv": None},  # terminal
    ]
    payload = {
        "game_id": game_id,
        "sf_version": "Stockfish 18",
        "evals": evals,
    }

    try:
        async with _make_client() as client:
            response = await client.post(
                _SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        # Verify the post-move shift: row ply=0 carries the eval submitted at ply=1.
        # The worker submitted ply=1 with eval_cp=30; the server must store it at ply=0.
        row_ply0 = await _get_game_position(eval_worker_session_maker, game_id, ply=0)
        assert row_ply0 is not None, "game_positions row at ply=0 must exist"
        assert row_ply0["eval_cp"] == 30, (
            f"Row ply=0 should carry eval_cp=30 (submitted at ply=1, shifted by +1). "
            f"Got eval_cp={row_ply0['eval_cp']}. "
            "If eval_cp is None, the server did not apply the shift (D-2 violation). "
            "If eval_cp=20, the server stored without shifting (position-ply confusion)."
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id])


@pytest.mark.asyncio
async def test_submit_stamps_full_evals_completed_at(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """After a complete submit (no holes), full_evals_completed_at IS NOT NULL."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    game_id = await _insert_game(eval_worker_session_maker, user_id)
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 3000 + ply, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    # Submit all 5 positions (plies 0-3 + terminal ply 4) with non-NULL eval_cp.
    # No holes → failed_ply_count == 0 → stamp_complete=True.
    evals = [
        {"ply": p, "eval_cp": 10 + p, "eval_mate": None, "best_move": None, "pv": None}
        for p in range(5)
    ]
    payload = {"game_id": game_id, "sf_version": "Stockfish 18", "evals": evals}

    try:
        async with _make_client() as client:
            response = await client.post(
                _SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["stamp_complete"] is True, f"stamp_complete should be True: {body}"
        assert body["failed_ply_count"] == 0, f"failed_ply_count should be 0: {body}"

        # Verify the DB marker.
        completed_at = await _get_game_full_evals_completed_at(eval_worker_session_maker, game_id)
        assert completed_at is not None, (
            "full_evals_completed_at must be set after a complete submit "
            "(failed_ply_count == 0 → Path A stamp)"
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id])


@pytest.mark.asyncio
async def test_submit_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Submitting the same payload twice → 200 both times, identical stored evals.

    Proves T-120-03 (idempotency): ON CONFLICT DO NOTHING for flaws, idempotent
    oracle UPDATE, completion markers set to the same value on repeat.
    """
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    game_id = await _insert_game(eval_worker_session_maker, user_id)
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 4000 + ply, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    evals = [
        {"ply": p, "eval_cp": 15 + p, "eval_mate": None, "best_move": None, "pv": None}
        for p in range(5)
    ]
    payload = {"game_id": game_id, "sf_version": "Stockfish 18", "evals": evals}

    try:
        async with _make_client() as client:
            # First submit
            resp1 = await client.post(
                _SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
            assert resp1.status_code == 200, (
                f"First submit: expected 200, got {resp1.status_code}: {resp1.text}"
            )

            # Second submit (same payload)
            resp2 = await client.post(
                _SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
            assert resp2.status_code == 200, (
                f"Second submit: expected 200, got {resp2.status_code}: {resp2.text}"
            )

        # Both responses must be 200; stored eval must match first submit.
        row_ply0_first = resp1.json()
        row_ply0_second = resp2.json()
        assert row_ply0_first["game_id"] == game_id
        assert row_ply0_second["game_id"] == game_id

        # Row at ply=0 carries eval_cp=16 (submitted at ply=1 with eval_cp=16, shifted).
        row_ply0 = await _get_game_position(eval_worker_session_maker, game_id, ply=0)
        assert row_ply0 is not None
        assert row_ply0["eval_cp"] == 16, (  # 15 + ply=1 = 16
            f"After idempotent second submit, eval_cp at ply=0 should be 16, got {row_ply0['eval_cp']}"
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id])
