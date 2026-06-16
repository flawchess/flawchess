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
- TestTier1Claiming: tier-1 claim returns job_id; submit stamps eval_jobs; late submit
  guard; tier-3 submit with job_id=None does NOT touch eval_jobs; DEFAULT_IDLE_SLEEP=1.0.

Session patching: monkeypatch app.routers.eval_remote.async_session_maker to route
the router's own sessions to the per-run test DB (eval_drain / eval_queue_service
session makers are already patched by conftest's session-scoped override_get_async_session).
claim_eval_job is monkeypatched directly in the eval_remote router namespace for tests
that need to control which game is leased without relying on the recency-weighted lottery.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.main import app
from app.services.eval_queue_service import ClaimedJob

# ─── URL constants (no magic numbers) ─────────────────────────────────────────

_LEASE_URL = "/api/eval/remote/lease"
_SUBMIT_URL = "/api/eval/remote/submit"
_ENTRY_LEASE_URL = "/api/eval/remote/entry-lease"
_ENTRY_SUBMIT_URL = "/api/eval/remote/entry-submit"

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


_EVALS_NOW: datetime = datetime.now(timezone.utc)
"""Default evals_completed_at value — module-load-time now(), matching legacy behavior."""


async def _insert_game(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    pgn: str = _TWO_MOVE_PGN,
    *,
    evals_completed_at: datetime | None = _EVALS_NOW,
    full_evals_completed_at: datetime | None = None,
    lichess_evals_at: datetime | None = None,
    full_eval_attempts: int = 0,
) -> int:
    """Insert a Game row and commit. Returns game_id.

    By default evals_completed_at is set to now() so the game is NOT in the
    entry-ply pending queue (preserves pre-Phase-123 test behavior).
    Pass evals_completed_at=None to insert a pending entry-ply game
    (evals_completed_at IS NULL = unclaimed by the entry-eval drain).
    """
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
            evals_completed_at=evals_completed_at,
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

    Each dict: {"ply": int, "full_hash": int, "eval_cp": int|None, "eval_mate": int|None,
                "phase": int (optional, default 0)}.

    For entry-ply target collection, at least one row needs phase=1 (midgame) to produce
    a middlegame_entry target. Pass phase=1 in the row dict when needed.
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
                    phase=r.get("phase", 0),
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


async def _get_game_evals_completed_at(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
) -> datetime | None:
    """Fetch Game.evals_completed_at (entry-ply completion stamp)."""
    from app.models.game import Game

    async with session_maker() as session:
        result = await session.execute(select(Game.evals_completed_at).where(Game.id == game_id))
        return result.scalar_one_or_none()


async def _get_game_entry_eval_leased_by(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
) -> str | None:
    """Fetch Game.entry_eval_leased_by."""
    from app.models.game import Game

    async with session_maker() as session:
        result = await session.execute(select(Game.entry_eval_leased_by).where(Game.id == game_id))
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
    """Patch session makers for the eval remote router and the eval drain service.

    The router's own sessions (probe, claim, read) use async_session_maker imported
    into the router module. The entry-ply endpoints also call _load_pgns_for_games and
    _collect_eval_targets_from_db which open sessions via eval_drain.async_session_maker,
    so that module binding must also be redirected to the test DB.
    """
    import app.routers.eval_remote as eval_remote_module
    import app.services.eval_drain as eval_drain_module

    monkeypatch.setattr(eval_remote_module, "async_session_maker", session_maker)
    monkeypatch.setattr(eval_drain_module, "async_session_maker", session_maker)


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

    # Patch claim_eval_job to return None (empty queue).
    import app.routers.eval_remote as eval_remote_module

    monkeypatch.setattr(eval_remote_module, "claim_eval_job", AsyncMock(return_value=None))

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

    # Patch claim_eval_job to return our seeded game as a tier-3 ClaimedJob.
    import app.routers.eval_remote as eval_remote_module

    monkeypatch.setattr(
        eval_remote_module,
        "claim_eval_job",
        AsyncMock(
            return_value=ClaimedJob(
                game_id=game_id,
                user_id=user_id,
                tier=3,
                is_lichess_eval_game=False,
                job_id=None,
            )
        ),
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
        # Tier-3 claim: job_id must be None (no eval_jobs row for derived picks).
        assert body["job_id"] is None

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


# ─── Tier-1 claiming: helpers ─────────────────────────────────────────────────


async def _get_eval_job(
    session_maker: async_sessionmaker[AsyncSession],
    job_id: int,
) -> dict[str, Any] | None:
    """Fetch an eval_jobs row by id. Returns a dict with status/completed_at or None."""
    from app.models.eval_jobs import EvalJob

    async with session_maker() as session:
        result = await session.execute(select(EvalJob).where(EvalJob.id == job_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "id": row.id,
            "status": row.status,
            "completed_at": row.completed_at,
            "leased_by": row.leased_by,
        }


async def _seed_eval_job(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
    user_id: int,
    *,
    status: str = "leased",
) -> int:
    """Insert an eval_jobs row with the given status. Returns the new job_id."""
    from app.models.eval_jobs import EvalJob, TIER_EXPLICIT

    async with session_maker() as session:
        job = EvalJob(
            tier=TIER_EXPLICIT,
            user_id=user_id,
            game_id=game_id,
            status=status,
        )
        session.add(job)
        await session.flush()
        job_id = int(job.id)  # type: ignore[arg-type]
        await session.commit()
    return job_id


# ─── Tier-1 claiming: tests ───────────────────────────────────────────────────


class TestTier1Claiming:
    """Tier-1 claim path: job_id round-trip, eval_jobs stamp, late-submit guard.

    Tests R1, R3, R4, R5, R6 from the Phase 121 validation matrix.
    """

    @pytest.mark.asyncio
    async def test_tier1_lease_returns_job_id(
        self,
        monkeypatch: pytest.MonkeyPatch,
        eval_worker_session_maker: async_sessionmaker[AsyncSession],
        eval_worker_test_user: int,
    ) -> None:
        """R1: a tier-1 claim returns job_id equal to the leased eval_jobs.id.

        Mocks claim_eval_job to return a ClaimedJob with tier=1 and a non-None
        job_id. Asserts the lease response body carries that exact job_id.
        """
        monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
        _patch_router_session(monkeypatch, eval_worker_session_maker)

        user_id = eval_worker_test_user
        game_id = await _insert_game(eval_worker_session_maker, user_id)
        await _insert_game_positions(
            eval_worker_session_maker,
            user_id,
            game_id,
            [
                {"ply": ply, "full_hash": 5000 + ply, "eval_cp": None, "eval_mate": None}
                for ply in range(4)
            ],
        )

        seeded_job_id = 42  # opaque token — arbitrary non-None int for the mock

        import app.routers.eval_remote as eval_remote_module

        monkeypatch.setattr(
            eval_remote_module,
            "claim_eval_job",
            AsyncMock(
                return_value=ClaimedJob(
                    game_id=game_id,
                    user_id=user_id,
                    tier=1,
                    is_lichess_eval_game=False,
                    job_id=seeded_job_id,
                )
            ),
        )

        try:
            async with _make_client() as client:
                response = await client.post(_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            body = response.json()
            assert body["game_id"] == game_id
            # R1 key assertion: job_id echoed from ClaimedJob.job_id.
            assert body["job_id"] == seeded_job_id, (
                f"Expected job_id={seeded_job_id}, got {body.get('job_id')}"
            )
        finally:
            await _delete_games(eval_worker_session_maker, [game_id])

    @pytest.mark.asyncio
    async def test_submit_with_job_id_stamps_eval_jobs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        eval_worker_session_maker: async_sessionmaker[AsyncSession],
        eval_worker_test_user: int,
    ) -> None:
        """R3: submit WITH job_id stamps eval_jobs.status='completed' with completed_at set.

        Seeds a game, an eval_jobs row (status='leased'), and game_positions.
        Submits a complete payload with job_id. Queries the eval_jobs row back and
        asserts status='completed' and completed_at IS NOT NULL.
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
                {"ply": ply, "full_hash": 6000 + ply, "eval_cp": None, "eval_mate": None}
                for ply in range(4)
            ],
        )

        # Seed an eval_jobs row with status='leased' to simulate a claimed tier-1 job.
        job_id = await _seed_eval_job(eval_worker_session_maker, game_id, user_id, status="leased")

        evals = [
            {"ply": p, "eval_cp": 10 + p, "eval_mate": None, "best_move": None, "pv": None}
            for p in range(5)
        ]
        payload = {
            "game_id": game_id,
            "sf_version": "Stockfish 18",
            "evals": evals,
            "job_id": job_id,
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
            body = response.json()
            assert body["stamp_complete"] is True, f"stamp_complete should be True: {body}"

            # R3 key assertion: eval_jobs row is now 'completed' with completed_at set.
            job_row = await _get_eval_job(eval_worker_session_maker, job_id)
            assert job_row is not None, f"eval_jobs row {job_id} must exist"
            assert job_row["status"] == "completed", (
                f"eval_jobs status should be 'completed', got {job_row['status']!r}"
            )
            assert job_row["completed_at"] is not None, (
                "eval_jobs.completed_at must be set after stamping"
            )
        finally:
            await _delete_games(eval_worker_session_maker, [game_id])

    @pytest.mark.asyncio
    async def test_submit_without_job_id_does_not_touch_eval_jobs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        eval_worker_session_maker: async_sessionmaker[AsyncSession],
        eval_worker_test_user: int,
    ) -> None:
        """R4: submit with job_id=None (tier-3 path) leaves eval_jobs row untouched.

        Seeds a separate eval_jobs row (status='leased') unrelated to the game being
        submitted. Submits with job_id=None. Verifies the seeded row is unchanged.
        """
        monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
        monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")
        _patch_router_session(monkeypatch, eval_worker_session_maker)

        user_id = eval_worker_test_user

        # Game that will be submitted.
        game_id = await _insert_game(eval_worker_session_maker, user_id)
        await _insert_game_positions(
            eval_worker_session_maker,
            user_id,
            game_id,
            [
                {"ply": ply, "full_hash": 7000 + ply, "eval_cp": None, "eval_mate": None}
                for ply in range(4)
            ],
        )

        # A second game/job to verify eval_jobs is not touched.
        sentinel_game_id = await _insert_game(eval_worker_session_maker, user_id)
        sentinel_job_id = await _seed_eval_job(
            eval_worker_session_maker, sentinel_game_id, user_id, status="leased"
        )

        evals = [
            {"ply": p, "eval_cp": 10 + p, "eval_mate": None, "best_move": None, "pv": None}
            for p in range(5)
        ]
        # job_id=None → tier-3 path, no eval_jobs write expected.
        payload = {
            "game_id": game_id,
            "sf_version": "Stockfish 18",
            "evals": evals,
            "job_id": None,
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

            # R4 key assertion: sentinel eval_jobs row is still 'leased', not completed.
            sentinel_row = await _get_eval_job(eval_worker_session_maker, sentinel_job_id)
            assert sentinel_row is not None
            assert sentinel_row["status"] == "leased", (
                f"Sentinel eval_jobs status must remain 'leased' after tier-3 submit "
                f"(job_id=None); got {sentinel_row['status']!r}"
            )
            assert sentinel_row["completed_at"] is None, (
                "Sentinel eval_jobs.completed_at must stay NULL after tier-3 submit"
            )
        finally:
            await _delete_games(eval_worker_session_maker, [game_id, sentinel_game_id])

    @pytest.mark.asyncio
    async def test_late_submit_does_not_corrupt_eval_jobs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        eval_worker_session_maker: async_sessionmaker[AsyncSession],
        eval_worker_test_user: int,
    ) -> None:
        """R5: late-submit guard — submitting against a non-'leased' job is a no-op.

        Seeds an eval_jobs row with status='completed' (simulates a race where the
        lease expired and another worker already completed the job). Submits with
        that job_id. Asserts the row is unchanged (WHERE status='leased' makes the
        UPDATE miss). Proves T-121-01 blast-radius bound.
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
                {"ply": ply, "full_hash": 8000 + ply, "eval_cp": None, "eval_mate": None}
                for ply in range(4)
            ],
        )

        # Seed an eval_jobs row with status='completed' — not 'leased'.
        # The WHERE status='leased' guard must make the stamp UPDATE a no-op.
        job_id = await _seed_eval_job(
            eval_worker_session_maker, game_id, user_id, status="completed"
        )

        evals = [
            {"ply": p, "eval_cp": 10 + p, "eval_mate": None, "best_move": None, "pv": None}
            for p in range(5)
        ]
        payload = {
            "game_id": game_id,
            "sf_version": "Stockfish 18",
            "evals": evals,
            "job_id": job_id,
        }

        # Record state before submit.
        job_before = await _get_eval_job(eval_worker_session_maker, job_id)
        assert job_before is not None
        assert job_before["status"] == "completed"

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

            # R5 key assertion: the non-'leased' row is unchanged.
            job_after = await _get_eval_job(eval_worker_session_maker, job_id)
            assert job_after is not None
            assert job_after["status"] == "completed", (
                f"Status must remain 'completed' after a late submit; got {job_after['status']!r}"
            )
            # completed_at should be unchanged (was None when status='completed' with no
            # prior stamp — stays None because the UPDATE was a no-op).
            assert job_after["completed_at"] == job_before["completed_at"], (
                "completed_at must be unchanged after a late submit no-op"
            )
        finally:
            await _delete_games(eval_worker_session_maker, [game_id])

    @pytest.mark.asyncio
    async def test_lichess_eval_game_claim_releases_lease(
        self,
        monkeypatch: pytest.MonkeyPatch,
        eval_worker_session_maker: async_sessionmaker[AsyncSession],
        eval_worker_test_user: int,
    ) -> None:
        """WR-01: a deferred lichess-eval tier-1 claim releases its eval_jobs lease.

        claim_eval_job leases the eval_jobs row before the handler discovers it's a
        lichess-eval game it defers (D-4). Without the release fix the row would sit
        'leased' for the full lease TTL, stalling the server pool (which DOES do the
        flaw-PV backfill). Asserts the lease returns 204 AND the row is reset to
        'pending' with leased_by cleared so the server can claim it immediately.
        """
        monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
        _patch_router_session(monkeypatch, eval_worker_session_maker)

        user_id = eval_worker_test_user
        game_id = await _insert_game(eval_worker_session_maker, user_id)

        # A real 'leased' eval_jobs row — the state claim_eval_job would have left.
        job_id = await _seed_eval_job(eval_worker_session_maker, game_id, user_id, status="leased")

        import app.routers.eval_remote as eval_remote_module

        monkeypatch.setattr(
            eval_remote_module,
            "claim_eval_job",
            AsyncMock(
                return_value=ClaimedJob(
                    game_id=game_id,
                    user_id=user_id,
                    tier=1,
                    is_lichess_eval_game=True,
                    job_id=job_id,
                )
            ),
        )

        try:
            async with _make_client() as client:
                response = await client.post(_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})

            assert response.status_code == 204, (
                f"Lichess-eval game must be deferred with 204, got {response.status_code}"
            )

            # WR-01 key assertion: lease released back to 'pending', not stranded 'leased'.
            job_row = await _get_eval_job(eval_worker_session_maker, job_id)
            assert job_row is not None, f"eval_jobs row {job_id} must still exist"
            assert job_row["status"] == "pending", (
                f"Deferred lichess claim must release lease to 'pending'; got {job_row['status']!r}"
            )
            assert job_row["leased_by"] is None, (
                "leased_by must be cleared when the lease is released"
            )
            assert job_row["completed_at"] is None, (
                "A released (not completed) job must keep completed_at NULL"
            )
        finally:
            await _delete_games(eval_worker_session_maker, [game_id])

    def test_default_idle_sleep_is_one_second(self) -> None:
        """R6: DEFAULT_IDLE_SLEEP constant must be 1.0 (lowered from 5.0 in Phase 121).

        Only the empty-queue / 204 path sleeps; the busy path is a tight loop.
        This constant directly controls idle-pickup latency for tier-1 jobs.
        """
        import scripts.remote_eval_worker as remote_eval_worker

        assert remote_eval_worker.DEFAULT_IDLE_SLEEP == 1.0, (
            f"DEFAULT_IDLE_SLEEP must be 1.0, got {remote_eval_worker.DEFAULT_IDLE_SLEEP}"
        )


# ─── Phase 123 lease-claim tests ─────────────────────────────────────────────
# SEED-051 D-3/D-4: _claim_entry_eval_games SKIP-LOCKED LIFO correctness.
# Tests: partition (disjoint), LIFO ordering, TTL reclaim + future-lease exclusion,
# leased_by population.  All four drive the helper directly (no HTTP needed).


@pytest.mark.asyncio
async def test_lease_partition(
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Two sequential claims with different worker IDs return disjoint game ID sets.

    Inserts ENTRY_LEASE_BATCH_SIZE + 5 pending games (evals_completed_at=None) so
    both claims get a non-empty result, then asserts no overlap.  Sequential calls
    suffice because the first claim stamps entry_eval_lease_expiry in the future,
    making those rows invisible to the second claim's predicate — same partition
    guarantee as concurrent SKIP LOCKED.

    SEED-051 D-3 / validation matrix row 123-02-02.
    """
    from app.services.eval_drain import ENTRY_LEASE_BATCH_SIZE, _claim_entry_eval_games

    n_games = ENTRY_LEASE_BATCH_SIZE + 5
    game_ids: list[int] = []
    for _ in range(n_games):
        gid = await _insert_game(
            eval_worker_session_maker, eval_worker_test_user, evals_completed_at=None
        )
        game_ids.append(gid)

    try:
        async with eval_worker_session_maker() as session:
            first_batch = await _claim_entry_eval_games(
                session, "worker-A", ENTRY_LEASE_BATCH_SIZE, 60
            )
            await session.commit()

        async with eval_worker_session_maker() as session:
            second_batch = await _claim_entry_eval_games(
                session, "worker-B", ENTRY_LEASE_BATCH_SIZE, 60
            )
            await session.commit()

        assert len(first_batch) > 0, "first claim must return at least one game"
        assert len(second_batch) > 0, "second claim must return at least one game"
        overlap = set(first_batch) & set(second_batch)
        assert overlap == set(), (
            f"Claims must be disjoint (SKIP LOCKED partition), but overlap={overlap}"
        )
    finally:
        await _delete_games(eval_worker_session_maker, game_ids)


@pytest.mark.asyncio
async def test_lease_lifo(
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """The claim returns the highest IDs first (LIFO: newest import first, ORDER BY id DESC).

    Inserts 5 pending games sequentially (auto-increment IDs are monotonically
    increasing), then claims 3 of them.  The returned IDs must be the 3 largest
    (most recently inserted), confirming ORDER BY id DESC.

    SEED-051 D-3 (LIFO ordering) / RESEARCH §Architecture Diagram.
    """
    from app.services.eval_drain import _claim_entry_eval_games

    game_ids: list[int] = []
    for _ in range(5):
        gid = await _insert_game(
            eval_worker_session_maker, eval_worker_test_user, evals_completed_at=None
        )
        game_ids.append(gid)

    try:
        async with eval_worker_session_maker() as session:
            claimed = await _claim_entry_eval_games(session, "worker-lifo", 3, 60)
            await session.commit()

        assert len(claimed) == 3, f"Expected 3 claimed games, got {len(claimed)}"
        # The 3 highest IDs from the 5 inserted must be the ones claimed.
        top3 = sorted(game_ids)[-3:]
        assert sorted(claimed) == sorted(top3), (
            f"LIFO claim must return the 3 newest games (ids {top3}), got {sorted(claimed)}"
        )
    finally:
        await _delete_games(eval_worker_session_maker, game_ids)


@pytest.mark.asyncio
async def test_lease_reclaim(
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Past-expiry lease is reclaimable; future-expiry lease is NOT returned.

    1. Insert two pending games.
    2. Manually set game A's lease to the past (expired) and game B's to the future.
    3. Assert only game A is returned by a new claim (TTL reclaim); game B is skipped.

    SEED-051 D-4 (TTL reclaim) / PATTERNS.md lease_reclaim shape.
    """
    from app.services.eval_drain import _claim_entry_eval_games

    # Expired lease: entry_eval_lease_expiry 10 minutes in the past.
    game_expired = await _insert_game(
        eval_worker_session_maker, eval_worker_test_user, evals_completed_at=None
    )
    # Active (future) lease: entry_eval_lease_expiry 60 seconds from now.
    game_active = await _insert_game(
        eval_worker_session_maker, eval_worker_test_user, evals_completed_at=None
    )

    try:
        now = datetime.now(timezone.utc)
        async with eval_worker_session_maker() as session:
            await session.execute(
                sa.text("""
                    UPDATE games
                    SET entry_eval_lease_expiry = :past_ts,
                        entry_eval_leased_by = 'old-worker'
                    WHERE id = :gid
                """),
                {"past_ts": now - timedelta(minutes=10), "gid": game_expired},
            )
            await session.execute(
                sa.text("""
                    UPDATE games
                    SET entry_eval_lease_expiry = :future_ts,
                        entry_eval_leased_by = 'active-worker'
                    WHERE id = :gid
                """),
                {"future_ts": now + timedelta(seconds=60), "gid": game_active},
            )
            await session.commit()

        async with eval_worker_session_maker() as session:
            claimed = await _claim_entry_eval_games(session, "reclaimer", 10, 30)
            await session.commit()

        assert game_expired in claimed, f"Expired lease (game {game_expired}) must be reclaimable"
        assert game_active not in claimed, (
            f"Active future lease (game {game_active}) must NOT be reclaimable"
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_expired, game_active])


@pytest.mark.asyncio
async def test_leased_by_set(
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """After a claim, the leased games' entry_eval_leased_by equals the worker_id passed.

    SEED-051 D-9 / CONTEXT D-09 (observability column).
    """
    from app.services.eval_drain import _claim_entry_eval_games

    game_id = await _insert_game(
        eval_worker_session_maker, eval_worker_test_user, evals_completed_at=None
    )
    worker_id = "tst-worker"

    try:
        async with eval_worker_session_maker() as session:
            claimed = await _claim_entry_eval_games(session, worker_id, 10, 30)
            await session.commit()

        assert game_id in claimed, f"Game {game_id} must appear in the claimed set"

        async with eval_worker_session_maker() as session:
            from app.models.game import Game

            result = await session.execute(
                select(Game.entry_eval_leased_by).where(Game.id == game_id)
            )
            leased_by = result.scalar_one()

        assert leased_by == worker_id, (
            f"entry_eval_leased_by must equal worker_id '{worker_id}', got {leased_by!r}"
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id])


# ─── Phase 123 entry-lease HTTP endpoint tests ────────────────────────────────
# Tests for POST /eval/remote/entry-lease and /entry-submit (SEED-051 D-07).


@pytest.mark.asyncio
async def test_entry_lease_auth_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing operator token → 403 (fail-closed, T-123-01 / T-123-auth)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", "")
    async with _make_client() as client:
        response = await client.post(_ENTRY_LEASE_URL)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_entry_lease_auth_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong operator token → 401 (T-123-auth)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    async with _make_client() as client:
        response = await client.post(_ENTRY_LEASE_URL, headers={"X-Operator-Token": "wrong-token"})
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_entry_lease_gate_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Backlog exactly THRESHOLD-1 pending games → 204 (D-5 gate, Pitfall 6).

    The existence probe fires at OFFSET = THRESHOLD - 1 (0-indexed). With exactly
    THRESHOLD-1 games, the probe returns no row → 204 (too shallow for remote workers).
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    # Insert exactly THRESHOLD-1 pending games.
    n_games = ENTRY_LEASE_BACKLOG_THRESHOLD - 1
    game_ids: list[int] = []
    for _ in range(n_games):
        gid = await _insert_game(
            eval_worker_session_maker, eval_worker_test_user, evals_completed_at=None
        )
        game_ids.append(gid)

    try:
        async with _make_client() as client:
            response = await client.post(
                _ENTRY_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN}
            )
        assert response.status_code == 204, (
            f"Expected 204 (backlog below threshold), got {response.status_code}: {response.text}"
        )
    finally:
        await _delete_games(eval_worker_session_maker, game_ids)


@pytest.mark.asyncio
async def test_entry_lease_gate_at_threshold(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Backlog exactly THRESHOLD pending games → 200 (D-5 gate boundary, Pitfall 6).

    The 300th row is at OFFSET 299 (0-indexed). With exactly THRESHOLD games,
    the probe finds a row → gate passes → workers get a batch.
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    # Insert exactly THRESHOLD pending games.
    n_games = ENTRY_LEASE_BACKLOG_THRESHOLD
    game_ids: list[int] = []
    for _ in range(n_games):
        gid = await _insert_game(
            eval_worker_session_maker, eval_worker_test_user, evals_completed_at=None
        )
        game_ids.append(gid)

    try:
        async with _make_client() as client:
            response = await client.post(
                _ENTRY_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN}
            )
        # 200 = gate passed (batch leased); 204 would mean gate blocked (off-by-one bug).
        assert response.status_code == 200, (
            f"Expected 200 (backlog at threshold), got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert "positions" in body, f"Response must have 'positions' key: {body}"
        # The response may have 0 positions if games have no entry targets (no game_positions).
        # The key assertion is that the gate passed (200), not that positions is non-empty.
    finally:
        await _delete_games(eval_worker_session_maker, game_ids)


@pytest.mark.asyncio
async def test_entry_lease_returns_positions(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """With ≥ threshold pending games (with game_positions), entry-lease returns positions.

    Seeds THRESHOLD pending games + game_positions rows to produce real entry targets.
    Asserts the response has non-empty positions with {game_id, ply, fen} structure.
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    game_ids: list[int] = []

    # Pad to reach threshold first (these get lower IDs, so LIFO skips them in first batch).
    for _ in range(ENTRY_LEASE_BACKLOG_THRESHOLD - 1):
        gid = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
        game_ids.append(gid)

    # Insert our game with game_positions LAST so it gets the highest ID and
    # is picked first by the LIFO (id DESC) claim.
    game_with_positions = await _insert_game(
        eval_worker_session_maker, user_id, evals_completed_at=None
    )
    game_ids.append(game_with_positions)
    # phase=1 (midgame) on ply 0 produces a middlegame_entry target for _collect_target_specs.
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_with_positions,
        [
            {"ply": ply, "full_hash": 9000 + ply, "phase": 1, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    try:
        async with _make_client() as client:
            response = await client.post(
                _ENTRY_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN}
            )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert "positions" in body
        assert "leased_at" in body
        positions = body["positions"]
        assert len(positions) > 0, "positions must be non-empty (game has game_positions rows)"
        for pos in positions:
            assert "game_id" in pos and isinstance(pos["game_id"], int)
            assert "ply" in pos and isinstance(pos["ply"], int) and pos["ply"] >= 0
            assert "fen" in pos and pos["fen"], f"position at ply {pos['ply']} has empty FEN"
            # Entry-ply schema: NO is_terminal field (unlike full-ply LeasePosition)
            assert "is_terminal" not in pos, (
                "Entry-ply positions must not have is_terminal (depth-15, no best_move/pv)"
            )
    finally:
        await _delete_games(eval_worker_session_maker, game_ids)


@pytest.mark.asyncio
async def test_entry_submit_auth_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing operator token → 403 (T-123-01)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", "")
    payload = {"sf_version": "Stockfish 18", "evals": []}
    async with _make_client() as client:
        response = await client.post(_ENTRY_SUBMIT_URL, json=payload)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_entry_submit_sf_version_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """EXPECTED_SF_VERSION set, wrong version in body → 422 (T-123-07)."""
    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "Stockfish 18")
    payload = {"sf_version": "Stockfish 17", "evals": []}
    async with _make_client() as client:
        response = await client.post(
            _ENTRY_SUBMIT_URL,
            json=payload,
            headers={"X-Operator-Token": _TEST_TOKEN},
        )
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_entry_submit_no_shift(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Entry-submit writes eval at the EXACT submitted ply — NO +1 post-move shift.

    The inverse of test_submit_applies_post_move_shift (which verifies the +1 shift
    for full-ply /submit). Entry-ply uses _apply_eval_results (no shift); the worker
    submits at ply N and the server must store at row ply=N (Pitfall 1).

    For _TWO_MOVE_PGN "1. e4 e5 *": ply 0 is the middlegame entry (first half-move).
    Submit eval_cp=77 at ply=0 → row ply=0 must store eval_cp=77 (not shifted to ply=-1).
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user

    # Insert padding FIRST (lowest IDs) so the LIFO claim picks our game last.
    # The game with positions is inserted LAST to get the highest ID — LIFO picks it first.
    pad_ids: list[int] = []
    for _ in range(ENTRY_LEASE_BACKLOG_THRESHOLD - 1):
        gid = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
        pad_ids.append(gid)

    # Game with game_positions inserted LAST (highest ID → LIFO picks it in first batch).
    game_id = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 10000 + ply, "phase": 1, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    # First lease to discover what plies the server assigned.
    async with _make_client() as client:
        lease_resp = await client.post(_ENTRY_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})
    assert lease_resp.status_code == 200, (
        f"Expected 200 on entry-lease, got {lease_resp.status_code}: {lease_resp.text}"
    )
    positions = lease_resp.json()["positions"]
    # Find the position for our game.
    our_positions = [p for p in positions if p["game_id"] == game_id]
    assert our_positions, (
        f"Game {game_id} must appear in the leased positions. All positions: {positions}"
    )

    # Submit an eval for the first assigned ply of our game.
    target_ply = our_positions[0]["ply"]
    eval_cp_value = 77
    payload = {
        "sf_version": "Stockfish 18",
        "evals": [
            {"game_id": game_id, "ply": target_ply, "eval_cp": eval_cp_value, "eval_mate": None}
        ],
    }

    try:
        async with _make_client() as client:
            resp = await client.post(
                _ENTRY_SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
        assert resp.status_code == 200, (
            f"Expected 200 on entry-submit, got {resp.status_code}: {resp.text}"
        )

        # No-shift assertion: eval must be at the EXACT submitted ply (not shifted).
        row = await _get_game_position(eval_worker_session_maker, game_id, ply=target_ply)
        assert row is not None, f"game_positions row at ply={target_ply} must exist"
        assert row["eval_cp"] == eval_cp_value, (
            f"Entry-ply must write eval_cp={eval_cp_value} at ply={target_ply} (no +1 shift). "
            f"Got eval_cp={row['eval_cp']}. "
            "If the value landed at a different ply, the +1 shift was accidentally applied."
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id, *pad_ids])


@pytest.mark.asyncio
async def test_entry_submit_stamps_evals_completed_at(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """After entry-submit, evals_completed_at IS NOT NULL for the submitted game.

    The completion stamp is the permanent lease release (D-01): once stamped,
    the game exits the queue (evals_completed_at IS NULL predicate no longer matches).
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    # Padding inserted FIRST (lower IDs); game with positions LAST (highest ID → LIFO).
    pad_ids: list[int] = []
    for _ in range(ENTRY_LEASE_BACKLOG_THRESHOLD - 1):
        gid = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
        pad_ids.append(gid)

    game_id = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 11000 + ply, "phase": 1, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    # Lease to get the assigned plies.
    async with _make_client() as client:
        lease_resp = await client.post(_ENTRY_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})
    assert lease_resp.status_code == 200
    our_positions = [p for p in lease_resp.json()["positions"] if p["game_id"] == game_id]

    evals = [
        {"game_id": game_id, "ply": p["ply"], "eval_cp": 50, "eval_mate": None}
        for p in our_positions
    ]
    payload = {"sf_version": "Stockfish 18", "evals": evals}

    try:
        async with _make_client() as client:
            resp = await client.post(
                _ENTRY_SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert game_id in body["game_ids"], f"game_id must be in game_ids: {body}"
        assert body["stamped_count"] >= 1, f"stamped_count must be ≥1: {body}"

        # Key assertion: evals_completed_at is now set.
        completed_at = await _get_game_evals_completed_at(eval_worker_session_maker, game_id)
        assert completed_at is not None, (
            "evals_completed_at must be stamped after entry-submit "
            "(permanent lease release per D-01)"
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id, *pad_ids])


@pytest.mark.asyncio
async def test_entry_submit_stamps_full_leased_set_including_zero_target_games(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """CR-01 regression: a leased game that yields ZERO eval targets is still stamped.

    Before the fix, entry-submit stamped evals_completed_at ONLY for games present in
    the worker's submission body. A leased game with no derivable targets (e.g. an
    unreachable target ply, or — as here — a game with no game_positions rows) never
    appeared in body.evals, so it was never stamped and got re-leased every TTL cycle
    forever (re-lease livelock). The fix stamps the FULL set of games leased to this
    worker, mirroring the in-process server pool's "no permanent retry" invariant.

    Setup: BACKLOG_THRESHOLD-1 padding games with NO game_positions (zero targets) plus
    one game WITH positions. The LIFO claim leases a batch spanning padding games. We
    submit ONLY the target game's evals, then assert that a leased zero-target padding
    game also ends up stamped evals_completed_at.
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    # Padding games have NO game_positions → zero eval targets at drain time.
    pad_ids: list[int] = []
    for _ in range(ENTRY_LEASE_BACKLOG_THRESHOLD - 1):
        gid = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
        pad_ids.append(gid)

    # Highest ID → LIFO picks it first; it carries the only real eval targets.
    game_id = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 13000 + ply, "phase": 1, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    async with _make_client() as client:
        lease_resp = await client.post(_ENTRY_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})
    assert lease_resp.status_code == 200, lease_resp.text

    # Find a padding game that was actually leased to this (default) worker but produced
    # no positions in the lease response — that is the zero-target game CR-01 is about.
    leased_position_game_ids = {p["game_id"] for p in lease_resp.json()["positions"]}
    leased_zero_target_pad_id: int | None = None
    for pid in pad_ids:
        leased_by = await _get_game_entry_eval_leased_by(eval_worker_session_maker, pid)
        if leased_by is not None and pid not in leased_position_game_ids:
            leased_zero_target_pad_id = pid
            break
    assert leased_zero_target_pad_id is not None, (
        "Expected at least one padding game to be leased with zero target positions "
        "(LIFO claims a batch wider than the single game-with-positions)."
    )

    # Submit ONLY the target game's evals — the zero-target padding game is absent.
    our_positions = [p for p in lease_resp.json()["positions"] if p["game_id"] == game_id]
    evals = [
        {"game_id": game_id, "ply": p["ply"], "eval_cp": 42, "eval_mate": None}
        for p in our_positions
    ]
    payload = {"sf_version": "Stockfish 18", "evals": evals}

    try:
        async with _make_client() as client:
            resp = await client.post(
                _ENTRY_SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # CR-01 key assertion: the leased zero-target padding game (never submitted) is
        # stamped complete, so it cannot be re-leased — the livelock is broken.
        pad_completed_at = await _get_game_evals_completed_at(
            eval_worker_session_maker, leased_zero_target_pad_id
        )
        assert pad_completed_at is not None, (
            "A zero-target game leased to this worker must be stamped evals_completed_at "
            "on entry-submit even though it never appeared in the submission body "
            "(CR-01: full-leased-set stamping prevents the re-lease livelock)."
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id, *pad_ids])


@pytest.mark.asyncio
async def test_entry_submit_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Double entry-submit is safe: no error, no duplicate flaws.

    ON CONFLICT DO NOTHING for flaws; re-stamping evals_completed_at is a no-op.
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    monkeypatch.setattr(settings, "EXPECTED_SF_VERSION", "")
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    # Padding inserted FIRST (lower IDs); game with positions LAST (highest ID → LIFO).
    pad_ids: list[int] = []
    for _ in range(ENTRY_LEASE_BACKLOG_THRESHOLD - 1):
        gid = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
        pad_ids.append(gid)

    game_id = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
    await _insert_game_positions(
        eval_worker_session_maker,
        user_id,
        game_id,
        [
            {"ply": ply, "full_hash": 12000 + ply, "phase": 1, "eval_cp": None, "eval_mate": None}
            for ply in range(4)
        ],
    )

    # Lease to get assigned plies.
    async with _make_client() as client:
        lease_resp = await client.post(_ENTRY_LEASE_URL, headers={"X-Operator-Token": _TEST_TOKEN})
    assert lease_resp.status_code == 200
    our_positions = [p for p in lease_resp.json()["positions"] if p["game_id"] == game_id]

    evals = [
        {"game_id": game_id, "ply": p["ply"], "eval_cp": 42, "eval_mate": None}
        for p in our_positions
    ]
    payload = {"sf_version": "Stockfish 18", "evals": evals}

    try:
        async with _make_client() as client:
            resp1 = await client.post(
                _ENTRY_SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
            resp2 = await client.post(
                _ENTRY_SUBMIT_URL,
                json=payload,
                headers={"X-Operator-Token": _TEST_TOKEN},
            )
        assert resp1.status_code == 200, (
            f"First submit: expected 200, got {resp1.status_code}: {resp1.text}"
        )
        assert resp2.status_code == 200, (
            f"Second submit: expected 200, got {resp2.status_code}: {resp2.text}"
        )
    finally:
        await _delete_games(eval_worker_session_maker, [game_id, *pad_ids])


# ─── Phase 123 scope param tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scope_explicit_returns_only_tier1_2(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """scope=explicit → claim_eval_job returns tier-1/2 only; tier-3 is NOT attempted.

    Mocks claim_eval_job to verify it was called with scope='explicit'.
    When claim returns None (no tier-1/2 work) → /lease returns 204.
    """
    from unittest.mock import AsyncMock

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    import app.routers.eval_remote as eval_remote_module

    mock_claim = AsyncMock(return_value=None)
    monkeypatch.setattr(eval_remote_module, "claim_eval_job", mock_claim)

    async with _make_client() as client:
        response = await client.post(
            _LEASE_URL,
            params={"scope": "explicit"},
            headers={"X-Operator-Token": _TEST_TOKEN},
        )

    assert response.status_code == 204, (
        f"scope=explicit with no tier-1/2 work must return 204, got {response.status_code}"
    )
    # Key assertion: claim_eval_job was called with scope="explicit".
    mock_claim.assert_called_once()
    _, call_kwargs = mock_claim.call_args
    assert call_kwargs.get("scope") == "explicit", (
        f"claim_eval_job must receive scope='explicit', got {call_kwargs!r}"
    )


@pytest.mark.asyncio
async def test_scope_idle_skips_tier1_2(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """scope=idle → claim_eval_job receives scope='idle' and skips tier-1/2."""
    from unittest.mock import AsyncMock

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    import app.routers.eval_remote as eval_remote_module

    mock_claim = AsyncMock(return_value=None)
    monkeypatch.setattr(eval_remote_module, "claim_eval_job", mock_claim)

    async with _make_client() as client:
        response = await client.post(
            _LEASE_URL,
            params={"scope": "idle"},
            headers={"X-Operator-Token": _TEST_TOKEN},
        )

    assert response.status_code == 204
    mock_claim.assert_called_once()
    _, call_kwargs = mock_claim.call_args
    assert call_kwargs.get("scope") == "idle", (
        f"claim_eval_job must receive scope='idle', got {call_kwargs!r}"
    )


@pytest.mark.asyncio
async def test_scope_absent_is_bundled(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Absent scope → claim_eval_job is called with scope=None (bundled behavior, D-05).

    Backward-compat: an un-updated worker that sends no scope must get the exact
    pre-phase behavior (tier-1>2>3 bundled).
    """
    from unittest.mock import AsyncMock

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    import app.routers.eval_remote as eval_remote_module

    mock_claim = AsyncMock(return_value=None)
    monkeypatch.setattr(eval_remote_module, "claim_eval_job", mock_claim)

    async with _make_client() as client:
        response = await client.post(
            _LEASE_URL,
            headers={"X-Operator-Token": _TEST_TOKEN},
            # No scope param.
        )

    assert response.status_code == 204
    mock_claim.assert_called_once()
    _, call_kwargs = mock_claim.call_args
    assert call_kwargs.get("scope") is None, (
        f"claim_eval_job must receive scope=None when absent, got {call_kwargs!r}"
    )


# ─── Phase 123 X-Worker-Id header tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_worker_id_header_populates_leased_by_on_entry_lease(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """X-Worker-Id header on /entry-lease populates games.entry_eval_leased_by.

    Sends X-Worker-Id: box1 on the /entry-lease call. After the claim, asserts
    that the leased games carry entry_eval_leased_by='box1'.
    """
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    game_ids: list[int] = []
    for _ in range(ENTRY_LEASE_BACKLOG_THRESHOLD):
        gid = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
        game_ids.append(gid)

    try:
        async with _make_client() as client:
            response = await client.post(
                _ENTRY_LEASE_URL,
                headers={"X-Operator-Token": _TEST_TOKEN, "X-Worker-Id": "box1"},
            )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        # The claim stamped entry_eval_leased_by='box1' on the leased games.
        # Read back from DB to verify — games without entry targets still get the lease.
        found_any = False
        for gid in game_ids:
            leased_by = await _get_game_entry_eval_leased_by(eval_worker_session_maker, gid)
            if leased_by is not None:
                assert leased_by == "box1", (
                    f"Game {gid}: entry_eval_leased_by must be 'box1', got {leased_by!r}"
                )
                found_any = True
        assert found_any, "At least one game must have been leased with entry_eval_leased_by='box1'"
    finally:
        await _delete_games(eval_worker_session_maker, game_ids)


@pytest.mark.asyncio
async def test_worker_id_absent_falls_back_to_remote_worker_on_entry_lease(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """Absent X-Worker-Id header → entry_eval_leased_by = 'remote-worker' (D-10 fallback)."""
    from app.services.eval_drain import ENTRY_LEASE_BACKLOG_THRESHOLD

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    user_id = eval_worker_test_user
    game_ids: list[int] = []
    for _ in range(ENTRY_LEASE_BACKLOG_THRESHOLD):
        gid = await _insert_game(eval_worker_session_maker, user_id, evals_completed_at=None)
        game_ids.append(gid)

    try:
        async with _make_client() as client:
            response = await client.post(
                _ENTRY_LEASE_URL,
                headers={"X-Operator-Token": _TEST_TOKEN},
                # No X-Worker-Id header.
            )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        found_any = False
        for gid in game_ids:
            leased_by = await _get_game_entry_eval_leased_by(eval_worker_session_maker, gid)
            if leased_by is not None:
                assert leased_by == "remote-worker", (
                    f"Game {gid}: absent X-Worker-Id must fall back to 'remote-worker', "
                    f"got {leased_by!r}"
                )
                found_any = True
        assert found_any, (
            "At least one game must have been leased with entry_eval_leased_by='remote-worker'"
        )
    finally:
        await _delete_games(eval_worker_session_maker, game_ids)


@pytest.mark.asyncio
async def test_worker_id_header_populates_leased_by_on_full_lease(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
    eval_worker_test_user: int,
) -> None:
    """X-Worker-Id on /lease is passed to claim_eval_job as the worker_id label (D-10).

    Asserts claim_eval_job is called with worker_id='mybox' when the header is set.
    """
    from unittest.mock import AsyncMock

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)
    _patch_router_session(monkeypatch, eval_worker_session_maker)

    import app.routers.eval_remote as eval_remote_module

    mock_claim = AsyncMock(return_value=None)
    monkeypatch.setattr(eval_remote_module, "claim_eval_job", mock_claim)

    async with _make_client() as client:
        response = await client.post(
            _LEASE_URL,
            headers={"X-Operator-Token": _TEST_TOKEN, "X-Worker-Id": "mybox"},
        )

    assert response.status_code == 204
    mock_claim.assert_called_once()
    _, call_kwargs = mock_claim.call_args
    assert call_kwargs.get("worker_id") == "mybox", (
        f"claim_eval_job must receive worker_id='mybox', got {call_kwargs!r}"
    )


@pytest.mark.asyncio
async def test_worker_id_absent_falls_back_to_remote_worker_on_full_lease(
    monkeypatch: pytest.MonkeyPatch,
    eval_worker_session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Absent X-Worker-Id on /lease → claim_eval_job receives worker_id='remote-worker'."""
    from unittest.mock import AsyncMock

    monkeypatch.setattr(settings, "EVAL_OPERATOR_TOKEN", _TEST_TOKEN)

    import app.routers.eval_remote as eval_remote_module

    mock_claim = AsyncMock(return_value=None)
    monkeypatch.setattr(eval_remote_module, "claim_eval_job", mock_claim)

    async with _make_client() as client:
        response = await client.post(
            _LEASE_URL,
            headers={"X-Operator-Token": _TEST_TOKEN},
            # No X-Worker-Id.
        )

    assert response.status_code == 204
    mock_claim.assert_called_once()
    _, call_kwargs = mock_claim.call_args
    assert call_kwargs.get("worker_id") == "remote-worker", (
        f"Absent X-Worker-Id must fall back to 'remote-worker', got {call_kwargs!r}"
    )
