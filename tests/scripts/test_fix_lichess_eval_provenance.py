"""Tests for scripts/fix_lichess_eval_provenance.py (SEED-202 item 1 provenance fix).

Runs inside the rolled-back db_session, so nothing is committed.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from scripts.fix_lichess_eval_provenance import FlaggedGame, apply_fix, restore, scan
from tests.conftest import ensure_test_user

pytestmark = pytest.mark.asyncio

_USER_ID = 99660  # reserved for this module
_N_EVALS = 12
_EVALS_CP = [17, 22, 18, 25, 30, 12, -5, -20, 40, 55, 61, 80]
_OVERWRITE_OFFSET_CP = 37  # engine values close to, but never equal to, lichess's
_LICHESS_AT = datetime.datetime(2026, 10, 1, 12, 0, tzinfo=datetime.timezone.utc)

Layout = Literal["intact", "overwritten", "shifted"]


def _pgn_with_evals() -> str:
    moves = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7", "Re1", "b5"]
    parts = []
    for i, (san, cp) in enumerate(zip(moves, _EVALS_CP)):
        prefix = f"{i // 2 + 1}. " if i % 2 == 0 else ""
        parts.append(f"{prefix}{san} {{ [%eval {cp / 100:.2f}] }}")
    return '[Event "Rated Blitz game"]\n\n' + " ".join(parts) + " *"


def _stored_eval(layout: Layout, ply: int) -> int | None:
    """eval_cp for game_positions row `ply`; the n-th %eval belongs at ply n-1."""
    if layout == "intact":
        return _EVALS_CP[ply] if ply < _N_EVALS else None
    if layout == "overwritten":
        return _EVALS_CP[ply] + _OVERWRITE_OFFSET_CP if ply < _N_EVALS else None
    return _EVALS_CP[ply - 1] if 1 <= ply <= _N_EVALS else None


async def _seed(session: AsyncSession, layout: Layout) -> int:
    game = Game(
        user_id=_USER_ID,
        platform="lichess",
        platform_game_id=f"prov-{uuid.uuid4().hex[:12]}",
        pgn=_pgn_with_evals(),
        result="1-0",
        user_color="white",
        rated=True,
        is_computer_game=False,
        lichess_evals_at=_LICHESS_AT,
        full_evals_completed_at=_LICHESS_AT,
    )
    session.add(game)
    await session.flush()
    for ply in range(_N_EVALS + 1):
        session.add(
            GamePosition(
                game_id=game.id,
                user_id=_USER_ID,
                ply=ply,
                full_hash=ply,
                white_hash=ply,
                black_hash=ply,
                eval_cp=_stored_eval(layout, ply),
            )
        )
    await session.flush()
    return game.id


async def _lichess_at(session: AsyncSession, game_id: int) -> datetime.datetime | None:
    return await session.scalar(select(Game.lichess_evals_at).where(Game.id == game_id))


async def test_scan_flags_only_overwritten_games(db_session: AsyncSession) -> None:
    await ensure_test_user(db_session, _USER_ID)
    intact = await _seed(db_session, "intact")
    overwritten = await _seed(db_session, "overwritten")
    shifted = await _seed(db_session, "shifted")

    flagged = {g["id"]: g for g in await scan(db_session)}

    assert overwritten in flagged
    assert flagged[overwritten]["n_evals"] == _N_EVALS
    assert flagged[overwritten]["post_matches"] == 0
    assert intact not in flagged
    # The one-ply-shift defect still holds lichess values: must not be relabelled.
    assert shifted not in flagged


async def test_apply_rechecks_and_restore_round_trips(db_session: AsyncSession) -> None:
    await ensure_test_user(db_session, _USER_ID)
    intact = await _seed(db_session, "intact")
    overwritten = await _seed(db_session, "overwritten")
    flagged = [g for g in await scan(db_session) if g["id"] == overwritten]
    # A doctored list entry for an intact game must be skipped by the re-check.
    doctored_entry: FlaggedGame = {**flagged[0], "id": intact}
    doctored = [*flagged, doctored_entry]

    changed = await apply_fix(db_session, doctored)

    assert changed == [overwritten]
    assert await _lichess_at(db_session, overwritten) is None
    assert await _lichess_at(db_session, intact) == _LICHESS_AT

    restored = await restore(db_session, flagged)

    assert restored == [overwritten]
    assert await _lichess_at(db_session, overwritten) == _LICHESS_AT
