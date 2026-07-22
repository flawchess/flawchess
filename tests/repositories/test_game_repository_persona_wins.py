"""Tests for count_wins_by_persona / update_bot_game_persona_id (Phase 185 T-185-02).

Covers: count_wins_by_persona excludes draws, losses, persona_id-NULL rows, and
non-flawchess-platform rows; groups correctly per persona_id; scoped to
user_id. update_bot_game_persona_id writes the single column without
committing.

Data isolation: uses the rollback-scoped ``db_session`` fixture from
``tests/conftest.py`` — no committed rows leak between tests, following
tests/repositories/test_bot_game_settings_repository.py's precedent.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.repositories.game_repository import count_wins_by_persona, update_bot_game_persona_id
from tests.conftest import ensure_test_user

pytestmark = pytest.mark.asyncio

_TEST_USER_ID = 92401  # unique ID for this test module (distinct from other repo test modules)
_OTHER_USER_ID = 92402


def _make_game(
    *,
    user_id: int,
    platform_game_id: str,
    result: str,
    user_color: str,
    persona_id: str | None,
    platform: str = "flawchess",
) -> Game:
    return Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=platform_game_id,
        pgn="1. e4 e5 1-0",
        result=result,
        user_color=user_color,
        rated=False,
        is_computer_game=True,
        persona_id=persona_id,
    )


class TestCountWinsByPersona:
    async def test_counts_wins_only_excludes_draws_and_losses(
        self, db_session: AsyncSession
    ) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID)
        db_session.add_all(
            [
                # Win as white.
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-win-white",
                    result="1-0",
                    user_color="white",
                    persona_id="attacker-1200",
                ),
                # Win as black.
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-win-black",
                    result="0-1",
                    user_color="black",
                    persona_id="attacker-1200",
                ),
                # Draw — excluded.
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-draw",
                    result="1/2-1/2",
                    user_color="white",
                    persona_id="attacker-1200",
                ),
                # Loss as white — excluded.
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-loss",
                    result="0-1",
                    user_color="white",
                    persona_id="attacker-1200",
                ),
            ]
        )
        await db_session.flush()

        wins = await count_wins_by_persona(db_session, _TEST_USER_ID)
        assert wins == {"attacker-1200": 2}

    async def test_excludes_persona_id_null_rows(self, db_session: AsyncSession) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID)
        db_session.add_all(
            [
                # Custom-mode win — persona_id NULL, must not appear.
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-null-persona",
                    result="1-0",
                    user_color="white",
                    persona_id=None,
                ),
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-real-persona",
                    result="1-0",
                    user_color="white",
                    persona_id="grinder-1600",
                ),
            ]
        )
        await db_session.flush()

        wins = await count_wins_by_persona(db_session, _TEST_USER_ID)
        assert wins == {"grinder-1600": 1}

    async def test_groups_per_persona_id(self, db_session: AsyncSession) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID)
        db_session.add_all(
            [
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-group-a1",
                    result="1-0",
                    user_color="white",
                    persona_id="wall-800",
                ),
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-group-a2",
                    result="1-0",
                    user_color="white",
                    persona_id="wall-800",
                ),
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-group-b1",
                    result="1-0",
                    user_color="white",
                    persona_id="trickster-1400",
                ),
            ]
        )
        await db_session.flush()

        wins = await count_wins_by_persona(db_session, _TEST_USER_ID)
        assert wins == {"wall-800": 2, "trickster-1400": 1}

    async def test_scoped_to_user_id(self, db_session: AsyncSession) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID)
        await ensure_test_user(db_session, _OTHER_USER_ID)
        db_session.add_all(
            [
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-scope-mine",
                    result="1-0",
                    user_color="white",
                    persona_id="attacker-1200",
                ),
                _make_game(
                    user_id=_OTHER_USER_ID,
                    platform_game_id="cwp-scope-other",
                    result="1-0",
                    user_color="white",
                    persona_id="attacker-1200",
                ),
            ]
        )
        await db_session.flush()

        wins = await count_wins_by_persona(db_session, _TEST_USER_ID)
        assert wins == {"attacker-1200": 1}

    async def test_excludes_non_flawchess_platform(self, db_session: AsyncSession) -> None:
        """Defense-in-depth: persona_id set on a non-flawchess row (should never
        happen in practice) is still excluded by the platform predicate.
        """
        await ensure_test_user(db_session, _TEST_USER_ID)
        db_session.add(
            _make_game(
                user_id=_TEST_USER_ID,
                platform_game_id="cwp-wrong-platform",
                result="1-0",
                user_color="white",
                persona_id="attacker-1200",
                platform="lichess",
            )
        )
        await db_session.flush()

        wins = await count_wins_by_persona(db_session, _TEST_USER_ID)
        assert wins == {}

    async def test_no_rows_returns_empty_dict(self, db_session: AsyncSession) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID)
        wins = await count_wins_by_persona(db_session, _TEST_USER_ID)
        assert wins == {}

    async def test_persona_with_only_losses_is_absent_not_zero(
        self, db_session: AsyncSession
    ) -> None:
        """WR-01 regression: a persona played but never won must be absent from
        the dict entirely, matching the docstring's "absent means never played
        a winning game" contract — NOT present as a spurious {"persona": 0}
        entry (the previous GROUP BY with no HAVING produced exactly that).
        """
        await ensure_test_user(db_session, _TEST_USER_ID)
        db_session.add_all(
            [
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-only-loss",
                    result="0-1",
                    user_color="white",
                    persona_id="wall-800",
                ),
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-only-draw",
                    result="1/2-1/2",
                    user_color="white",
                    persona_id="wall-800",
                ),
                # A different persona WITH a win, to prove the HAVING filter is
                # per-group, not a query-wide short-circuit.
                _make_game(
                    user_id=_TEST_USER_ID,
                    platform_game_id="cwp-other-win",
                    result="1-0",
                    user_color="white",
                    persona_id="attacker-1200",
                ),
            ]
        )
        await db_session.flush()

        wins = await count_wins_by_persona(db_session, _TEST_USER_ID)
        assert "wall-800" not in wins
        assert wins == {"attacker-1200": 1}


class TestUpdateBotGamePersonaId:
    async def test_writes_persona_id_without_committing(self, db_session: AsyncSession) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID)
        game = _make_game(
            user_id=_TEST_USER_ID,
            platform_game_id="ubgpi-write",
            result="1-0",
            user_color="white",
            persona_id=None,
        )
        db_session.add(game)
        await db_session.flush()

        await update_bot_game_persona_id(db_session, game.id, "deep-1800")
        await db_session.flush()

        row = (await db_session.execute(select(Game).where(Game.id == game.id))).scalar_one()
        assert row.persona_id == "deep-1800"
