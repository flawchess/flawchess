"""Repository unit tests for fetch_tactic_lines() (Phase 135, Plan 01).

Uses the rollback-scoped db_session fixture so tests are isolated and fast.

Coverage:
- test_missed_from_pos_n_allowed_from_pos_n_plus_1  : n vs n+1 anchoring + flaw-move prepend
- test_allowed_decision_depth_offset                 : allowed_depth returned as raw 0-based (no offset)
- test_short_pv_no_crash                             : PV shorter than tactic_depth → no crash, no negative
- test_null_pv_returns_none                          : pos[n].pv = None → missed_moves is None
- test_full_pv_no_truncation                         : full engine PV returned untruncated (Phase 135 UAT)
- test_eval_fields_populated                          : missed eval from pos[ply-1] (decision), allowed eval from pos[ply] (post-flaw) — eval_cp is post-move
- test_missed_eval_none_at_game_start                 : ply 0 → no pos[ply-1] → missed eval is None
"""

from __future__ import annotations

import datetime
import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game as GameModel
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.library_repository import (
    fetch_tactic_lines,
)

# A legal starting position board_fen() (piece-placement only) — used as flaw.fen.
# White to move at this position (ply % 2 == 0 for white).
_START_BOARD_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

# Legal UCI PV strings from the starting position (white to move at ply 0/2/...).
# 4 moves (indices 0-3): e4, e5, Nf3, Nc6
_PV_4 = "e2e4 e7e5 g1f3 b8c6"
# 2 moves (shorter)
_PV_2 = "e2e4 e7e5"
# Long PV for truncation test (8 moves)
_PV_8 = "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6"

# After white plays e4 (move_san="e4") the board is: rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR
# Black to move — PV from there (PV at pos[n+1], which starts after the flaw move):
_ALLOWED_PV_FROM_AFTER_E4 = "e7e5 g1f3 b8c6"

# FORK motif int = 1
_FORK_INT = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_user(session: AsyncSession, user_id: int) -> None:
    """Insert a minimal user row via ensure_test_user."""
    from tests.conftest import ensure_test_user

    await ensure_test_user(session, user_id)


async def _seed_game(session: AsyncSession, user_id: int) -> int:
    """Seed a minimal analyzed game and return game_id."""
    game = GameModel(
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
        ply_count=20,
        full_evals_completed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )
    session.add(game)
    await session.flush()
    return int(game.id)


async def _seed_flaw(
    session: AsyncSession,
    user_id: int,
    game_id: int,
    ply: int,
    *,
    fen: str = _START_BOARD_FEN,
    missed_tactic_motif: int | None = _FORK_INT,
    missed_tactic_confidence: int | None = 85,
    missed_tactic_depth: int | None = 2,
    allowed_tactic_motif: int | None = _FORK_INT,
    allowed_tactic_confidence: int | None = 85,
    allowed_tactic_depth: int | None = 1,
) -> None:
    """Insert a GameFlaw row for testing."""
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
        fen=fen,
        missed_tactic_motif=missed_tactic_motif,
        missed_tactic_confidence=missed_tactic_confidence,
        missed_tactic_depth=missed_tactic_depth,
        allowed_tactic_motif=allowed_tactic_motif,
        allowed_tactic_confidence=allowed_tactic_confidence,
        allowed_tactic_depth=allowed_tactic_depth,
    )
    session.add(flaw)
    await session.flush()


async def _seed_position(
    session: AsyncSession,
    user_id: int,
    game_id: int,
    ply: int,
    *,
    pv: str | None = None,
    move_san: str | None = None,
    best_move: str | None = None,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
) -> None:
    """Insert a GamePosition row for testing."""
    pos = GamePosition(
        user_id=user_id,
        game_id=game_id,
        ply=ply,
        full_hash=1000 + ply,
        white_hash=2000 + ply,
        black_hash=3000 + ply,
        move_san=move_san,
        best_move=best_move,
        pv=pv,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
    )
    session.add(pos)
    await session.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFetchTacticLines:
    """Unit tests for fetch_tactic_lines() repository function."""

    @pytest.mark.asyncio
    async def test_missed_from_pos_n_allowed_from_pos_n_plus_1(self, db_session: object) -> None:
        """missed_moves derives from pos[n].pv; allowed_moves[0] == flaw move, then pos[n+1].pv.

        PV anchoring:
        - Missed: uses board_before (decision position at flaw ply, white to move for ply 0).
        - Allowed: uses board_after_flaw (flaw move pushed), PV from pos[n+1].pv;
                   flaw_move_san is prepended as allowed_moves[0] (Pitfall 3).
        """
        session = cast(AsyncSession, db_session)
        uid = 13501
        await _seed_user(session, uid)
        game_id = await _seed_game(session, uid)
        ply = 0  # white to move at ply 0

        # The flaw move from the starting position: e4 (SAN)
        flaw_move_san = "e4"
        best_move = "e2e4"
        # PV at pos[n] (missed — from decision position, white to move):
        missed_pv = _PV_4  # e4, e5, Nf3, Nc6
        # PV at pos[n+1] (allowed — from board_after_flaw, black to move after e4):
        allowed_pv = _ALLOWED_PV_FROM_AFTER_E4  # e5, Nf3, Nc6

        await _seed_flaw(session, uid, game_id, ply)
        await _seed_position(
            session, uid, game_id, ply, pv=missed_pv, move_san=flaw_move_san, best_move=best_move
        )
        await _seed_position(session, uid, game_id, ply + 1, pv=allowed_pv)

        result = await fetch_tactic_lines(session, game_id=game_id, ply=ply)

        assert result is not None
        # Missed PV from decision position
        assert result.missed_moves is not None
        assert isinstance(result.missed_moves, list)
        assert len(result.missed_moves) > 0
        # The first missed move should be "e4" (best move from starting position)
        assert result.missed_moves[0] == "e4"

        # Allowed: first move is the flaw move itself (prepended), then opponent PV
        assert result.allowed_moves is not None
        assert isinstance(result.allowed_moves, list)
        assert len(result.allowed_moves) >= 1
        assert result.allowed_moves[0] == flaw_move_san, (
            f"allowed_moves[0] should be flaw move '{flaw_move_san}', got '{result.allowed_moves[0]}'"
        )

        # flaw metadata
        assert result.flaw_move_san == flaw_move_san
        assert result.best_move_uci == best_move
        assert result.flaw_ply == ply

        # position_fen is a full FEN (includes side-to-move, not just board_fen)
        assert " " in result.position_fen, "position_fen should be a full FEN with side-to-move"

    @pytest.mark.asyncio
    async def test_allowed_decision_depth_offset(self, db_session: object) -> None:
        """allowed_depth in response is the raw 0-based DB value (no offset applied server-side).

        The +1 display offset is applied client-side via toDisplayDepthForOrientation().
        The endpoint returns RAW depths (Research Finding 2).
        """
        session = cast(AsyncSession, db_session)
        uid = 13502
        await _seed_user(session, uid)
        game_id = await _seed_game(session, uid)
        ply = 0

        raw_allowed_depth = 3
        raw_missed_depth = 2

        await _seed_flaw(
            session,
            uid,
            game_id,
            ply,
            missed_tactic_depth=raw_missed_depth,
            allowed_tactic_depth=raw_allowed_depth,
        )
        await _seed_position(session, uid, game_id, ply, pv=_PV_4, move_san="e4", best_move="e2e4")
        await _seed_position(session, uid, game_id, ply + 1, pv=_ALLOWED_PV_FROM_AFTER_E4)

        result = await fetch_tactic_lines(session, game_id=game_id, ply=ply)

        assert result is not None
        # Raw 0-based depths returned as-is (no offset applied in repository)
        assert result.allowed_depth == raw_allowed_depth, (
            f"allowed_depth should be raw {raw_allowed_depth}, got {result.allowed_depth}"
        )
        assert result.missed_depth == raw_missed_depth, (
            f"missed_depth should be raw {raw_missed_depth}, got {result.missed_depth}"
        )
        # missed has no prepend → ply_index == raw depth.
        assert result.missed_tactic_ply_index == raw_missed_depth
        # allowed_moves prepends the flaw move at index 0, so the refutation punchline
        # sits one index deeper → ply_index == raw depth + 1 (Phase 135 UAT).
        assert result.allowed_tactic_ply_index == raw_allowed_depth + 1

    @pytest.mark.asyncio
    async def test_short_pv_no_crash(self, db_session: object) -> None:
        """PV shorter than missed_tactic_depth: no crash, returns the full short list.

        Pitfall 1: tactic_depth >= pv_length. The slice handles this gracefully
        (slicing past end is safe in Python). No negative counters, no None corruption.
        """
        session = cast(AsyncSession, db_session)
        uid = 13503
        await _seed_user(session, uid)
        game_id = await _seed_game(session, uid)
        ply = 0

        # PV has only 2 moves, but tactic_depth is 5 (depth > PV length)
        short_pv = _PV_2  # 2 moves
        raw_missed_depth = 5  # exceeds PV length

        await _seed_flaw(session, uid, game_id, ply, missed_tactic_depth=raw_missed_depth)
        await _seed_position(session, uid, game_id, ply, pv=short_pv, move_san="e4")
        await _seed_position(session, uid, game_id, ply + 1, pv=_ALLOWED_PV_FROM_AFTER_E4)

        # Must not raise an exception
        result = await fetch_tactic_lines(session, game_id=game_id, ply=ply)

        assert result is not None
        # missed_moves should be the full (short) list — no negative slice corruption
        assert result.missed_moves is not None
        assert len(result.missed_moves) == 2  # full PV, not truncated to negative

    @pytest.mark.asyncio
    async def test_null_pv_returns_none(self, db_session: object) -> None:
        """pos[n].pv = None → missed_moves is None; allowed_moves still resolves from pos[n+1].

        Pitfall 4: pv can be NULL for certain positions; the endpoint handles gracefully.
        """
        session = cast(AsyncSession, db_session)
        uid = 13504
        await _seed_user(session, uid)
        game_id = await _seed_game(session, uid)
        ply = 0

        await _seed_flaw(session, uid, game_id, ply)
        # pos[n].pv is NULL
        await _seed_position(session, uid, game_id, ply, pv=None, move_san="e4", best_move="e2e4")
        await _seed_position(session, uid, game_id, ply + 1, pv=_ALLOWED_PV_FROM_AFTER_E4)

        result = await fetch_tactic_lines(session, game_id=game_id, ply=ply)

        assert result is not None
        assert result.missed_moves is None, "missed_moves should be None when pv is NULL"
        # allowed_moves can still resolve (starts from flaw move prepend + pos[n+1].pv)
        # Note: allowed_moves requires pos[n].move_san for the prepended flaw move AND pos[n+1].pv
        # Both are provided → allowed_moves may resolve
        assert result.flaw_ply == ply

    @pytest.mark.asyncio
    async def test_full_pv_no_truncation(self, db_session: object) -> None:
        """The full engine PV is returned untruncated (Phase 135 UAT).

        Previously the PV was capped at tactic_depth + 1 + payoff plies; now every
        move the engine returned is shown so the user can walk the whole line.
        """
        session = cast(AsyncSession, db_session)
        uid = 13505
        await _seed_user(session, uid)
        game_id = await _seed_game(session, uid)
        ply = 0

        # Long PV: 8 moves. tactic_depth = 2 — the depth no longer caps the list length.
        raw_missed_depth = 2
        long_pv = _PV_8  # 8 moves

        await _seed_flaw(session, uid, game_id, ply, missed_tactic_depth=raw_missed_depth)
        await _seed_position(session, uid, game_id, ply, pv=long_pv, move_san="e4")
        await _seed_position(session, uid, game_id, ply + 1, pv=_ALLOWED_PV_FROM_AFTER_E4)

        result = await fetch_tactic_lines(session, game_id=game_id, ply=ply)

        assert result is not None
        assert result.missed_moves is not None
        # All 8 PV plies present — no truncation regardless of tactic_depth.
        assert len(result.missed_moves) == 8, (
            f"Expected the full 8-move PV, got {len(result.missed_moves)}"
        )

    @pytest.mark.asyncio
    async def test_eval_fields_populated(self, db_session: object) -> None:
        """missed eval comes from pos[ply-1] (decision position), allowed eval from pos[ply].

        game_positions.eval_cp is the POST-MOVE eval (eval of the position AFTER that
        ply's move), so the decision-position eval lives on ply-1 and the post-flaw
        eval lives on ply. White-POV (Phase 135 UAT). Uses ply=10 (even → white to
        move, starting position) so a real ply-1 row exists.
        """
        session = cast(AsyncSession, db_session)
        uid = 13506
        await _seed_user(session, uid)
        game_id = await _seed_game(session, uid)
        ply = 10  # even → white to move from the starting board_fen

        await _seed_flaw(session, uid, game_id, ply)
        # Decision-position eval (board_before) lives on ply-1's post-move row.
        await _seed_position(session, uid, game_id, ply - 1, eval_cp=120)
        # Post-flaw eval (after the flaw move e4) is the post-move eval on ply's row.
        await _seed_position(session, uid, game_id, ply, pv=_PV_4, move_san="e4", eval_mate=-3)
        # pos[ply+1] carries the refutation PV; its eval must NOT be read for either line.
        await _seed_position(
            session, uid, game_id, ply + 1, pv=_ALLOWED_PV_FROM_AFTER_E4, eval_cp=999
        )

        result = await fetch_tactic_lines(session, game_id=game_id, ply=ply)

        assert result is not None
        # Missed (decision) eval from pos[ply-1], NOT the post-flaw pos[ply].
        assert result.missed_eval_cp == 120
        assert result.missed_eval_mate is None
        # Allowed (post-flaw) eval from pos[ply], NOT the deeper pos[ply+1] (999).
        assert result.allowed_eval_cp is None
        assert result.allowed_eval_mate == -3

    @pytest.mark.asyncio
    async def test_missed_eval_none_at_game_start(self, db_session: object) -> None:
        """ply 0 has no pos[ply-1], so the decision-position eval is None (game start)."""
        session = cast(AsyncSession, db_session)
        uid = 13507
        await _seed_user(session, uid)
        game_id = await _seed_game(session, uid)
        ply = 0

        await _seed_flaw(session, uid, game_id, ply)
        await _seed_position(session, uid, game_id, ply, pv=_PV_4, move_san="e4", eval_cp=120)
        await _seed_position(
            session, uid, game_id, ply + 1, pv=_ALLOWED_PV_FROM_AFTER_E4, eval_mate=-3
        )

        result = await fetch_tactic_lines(session, game_id=game_id, ply=ply)

        assert result is not None
        # No pos[-1] → decision eval unavailable.
        assert result.missed_eval_cp is None
        assert result.missed_eval_mate is None
        # Allowed (post-flaw) eval still comes from pos[ply].
        assert result.allowed_eval_cp == 120
        assert result.allowed_eval_mate is None
