"""Integration tests for app.repositories.library_repository (Phase 106-01).

Uses a real PostgreSQL database via the db_session fixture (rolled-back per test).
Covers the Wave-0 seam guards from 106-VALIDATION.md:

- `-k exists_filter` — the user-color-scoped EXISTS severity filter selects games
  with >=1 USER ply of the requested severity, excludes clean games, and EXCLUDES
  a game where only the OPPONENT blundered (B1 guard).
- `-k analyzed_denominator` — placeholder, implemented in 106-03.

Note: The SQL<->kernel cross-check (B2, `TestCrossCheck`) was retired in Phase 108
Plan 03 (D-02 migration). The `game_flaws` table IS the materialized kernel output,
so there is no longer a separate SQL path that could drift from the kernel. The new
invariant is tested in `tests/test_flaw_predicate.py`.

Reuses _seed_game / _seed_position helpers patterned on tests/test_flaws_repository.py.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import bulk_insert_game_flaws
from app.repositories.library_repository import (
    analyzed_game_ids,
    count_filtered_and_analyzed,
    query_filtered_games,
)
from app.repositories.query_utils import apply_game_filters


# ---------------------------------------------------------------------------
# Seed helpers (mirror tests/test_flaws_repository.py)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [99999, 99998]:
        await ensure_test_user(db_session, uid)


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 99999,
    user_color: str = "white",
) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
    )
    session.add(game)
    await session.flush()
    return game


async def _seed_position(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    """Insert a GamePosition row and flush."""
    pos = GamePosition(
        game_id=game.id,
        user_id=game.user_id,
        ply=ply,
        full_hash=hash(f"{game.id}-{ply}"),
        white_hash=hash(f"w-{game.id}-{ply}"),
        black_hash=hash(f"b-{game.id}-{ply}"),
        move_san=move_san,
        clock_seconds=clock_seconds,
        phase=phase,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
        piece_count=2,
        material_count=1000,
        material_signature="KP_KP",
        material_imbalance=0,
        endgame_class=None,
    )
    session.add(pos)
    await session.flush()
    return pos


async def _seed_game_flaw(
    session: AsyncSession,
    *,
    game: Game,
    ply: int = 2,
    severity: int = 2,  # 2=blunder (see _SEVERITY_INT in game_flaws_repository)
) -> None:
    """Insert a game_flaws row directly (bypasses classifier).

    D-02 migration: EXISTS filter now reads game_flaws rows, not positions.
    """
    await bulk_insert_game_flaws(
        session,
        [
            {
                "user_id": game.user_id,
                "game_id": game.id,
                "ply": ply,
                "severity": severity,
                "tempo": None,
                "phase": 1,  # middlegame
                "is_miss": False,
                "is_lucky_escape": False,
                "is_while_ahead": False,
                "is_result_changing": False,
                "es_before": 0.7,
                "es_after": 0.2,
                "move_san": "Nf3",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            }
        ],
    )


async def _matching_game_ids(
    session: AsyncSession, *, user_id: int, severities: list[str]
) -> set[int]:
    """Run apply_game_filters with the flaw_severity EXISTS and return matched ids."""
    stmt = select(Game.id).where(Game.user_id == user_id)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="all",
        from_date=None,
        to_date=None,
        flaw_severity=severities,
        user_id=user_id,
    )
    rows = (await session.execute(stmt)).scalars().all()
    return set(rows)


# ---------------------------------------------------------------------------
# TestExistsFilter (-k exists_filter)
# ---------------------------------------------------------------------------


class TestExistsFilter:
    """The user-scoped EXISTS flaw-severity filter reads game_flaws table (D-02)."""

    @pytest.mark.asyncio
    async def test_exists_filter_selects_game_with_flaw_excludes_clean(
        self, db_session: AsyncSession
    ) -> None:
        """A game with a game_flaws blunder row is selected; a clean game is not.

        D-02 migration: the EXISTS filter reads game_flaws directly (not the
        window-scan). The user-scoping is enforced via game_flaws.user_id.
        """
        # Game A: has a game_flaws blunder row.
        game_a = await _seed_game(db_session, user_color="white")
        await _seed_game_flaw(db_session, game=game_a, ply=2, severity=2)  # blunder

        # Game B: no game_flaws rows (clean).
        game_b = await _seed_game(db_session, user_color="white")

        matched = await _matching_game_ids(db_session, user_id=99999, severities=["blunder"])
        assert game_a.id in matched, "game with a blunder flaw row must match severity=blunder"
        assert game_b.id not in matched, "game with no flaw rows must not match"

    @pytest.mark.asyncio
    async def test_exists_filter_user_scoped_excludes_other_users_flaws(
        self, db_session: AsyncSession
    ) -> None:
        """EXISTS is user-scoped: another user's game_flaws rows do not satisfy the filter.

        The game belongs to user 99999; user 99998 has no flaw row for it. The EXISTS
        predicate is always scoped to game_flaws.user_id == the querying user_id (T-108-07).
        """
        game = await _seed_game(db_session, user_id=99999, user_color="white")
        # Seed a blunder row for user 99999 only.
        await _seed_game_flaw(db_session, game=game, ply=2, severity=2)

        # Querying as user 99998 must find no matching games.
        matched = await _matching_game_ids(db_session, user_id=99998, severities=["blunder"])
        assert game.id not in matched, (
            "EXISTS bound to user 99998 must not match game_flaws rows owned by user 99999"
        )

    @pytest.mark.asyncio
    async def test_exists_filter_mistake_matches_only_mistake_not_blunder(
        self, db_session: AsyncSession
    ) -> None:
        """severity=["mistake"] matches games with mistake rows only (set-membership).

        Phase 108 changed severity filtering from a "mistake or worse" MIN threshold to
        exact set-membership: severity=["mistake"] selects mistakes only, NOT blunders.
        """
        # Game A: mistake row (severity=1).
        game_a = await _seed_game(db_session, user_color="white")
        await _seed_game_flaw(db_session, game=game_a, ply=2, severity=1)  # mistake

        # Game B: blunder row (severity=2). Must NOT match ["mistake"] under set-membership.
        game_b = await _seed_game(db_session, user_color="white")
        await _seed_game_flaw(db_session, game=game_b, ply=4, severity=2)  # blunder

        # Game C: no flaw rows.
        game_c = await _seed_game(db_session, user_color="white")

        matched = await _matching_game_ids(db_session, user_id=99999, severities=["mistake"])
        assert game_a.id in matched, "game with a mistake must match severity=mistake"
        assert game_b.id not in matched, "game with only a blunder must NOT match severity=mistake"
        assert game_c.id not in matched, "game with no flaw rows must not match"


# ---------------------------------------------------------------------------
# TestQueryFilteredGames (-k query_filtered_games) — paginated archive (106-02)
# ---------------------------------------------------------------------------


class TestQueryFilteredGames:
    """query_filtered_games: paginated user archive + boolean severity filter."""

    @pytest.mark.asyncio
    async def test_severity_filter_narrows_to_blunder_games(self, db_session: AsyncSession) -> None:
        """severity=["blunder"] returns only games with a game_flaws blunder row (D-02)."""
        # Game A: has a blunder flaw row in game_flaws.
        game_a = await _seed_game(db_session, user_color="white")
        await _seed_game_flaw(db_session, game=game_a, ply=2, severity=2)  # blunder

        # Game B: no flaw rows (clean).
        game_b = await _seed_game(db_session, user_color="white")

        # Unfiltered: both games present.
        all_games, all_count = await query_filtered_games(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
            offset=0,
            limit=20,
        )
        all_ids = {g.id for g in all_games}
        assert {game_a.id, game_b.id} <= all_ids
        assert all_count >= 2

        # Filtered: only the blunder game.
        flt_games, flt_count = await query_filtered_games(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=["blunder"],
            offset=0,
            limit=20,
        )
        flt_ids = {g.id for g in flt_games}
        assert game_a.id in flt_ids
        assert game_b.id not in flt_ids
        assert flt_count == len(flt_ids)

    @pytest.mark.asyncio
    async def test_pagination_and_matched_count(self, db_session: AsyncSession) -> None:
        """matched_count reflects all matching games; offset/limit page the result."""
        seeded: set[int] = set()
        for _ in range(3):
            g = await _seed_game(db_session, user_id=99998, user_color="white")
            await _seed_position(db_session, game=g, ply=0, eval_cp=0)
            seeded.add(g.id)

        page1, count = await query_filtered_games(
            db_session,
            user_id=99998,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
            offset=0,
            limit=2,
        )
        assert count >= 3
        assert len(page1) == 2

        page2, _ = await query_filtered_games(
            db_session,
            user_id=99998,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
            offset=2,
            limit=2,
        )
        page1_ids = {g.id for g in page1}
        page2_ids = {g.id for g in page2}
        assert page1_ids.isdisjoint(page2_ids)
        assert seeded <= (page1_ids | page2_ids | {g.id for g in page1})

    @pytest.mark.asyncio
    async def test_empty_returns_zero(self, db_session: AsyncSession) -> None:
        """A user with no games returns ([], 0)."""
        games, count = await query_filtered_games(
            db_session,
            user_id=99998,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=["blunder"],
            offset=0,
            limit=20,
        )
        assert games == []
        assert count == 0


# ---------------------------------------------------------------------------
# TestAnalyzedDenominator (-k analyzed_denominator) — the >=90% coverage gate
# ---------------------------------------------------------------------------


class TestAnalyzedDenominator:
    """count_filtered_and_analyzed + analyzed_game_ids over the filtered set."""

    @pytest.mark.asyncio
    async def test_analyzed_denominator_counts_only_covered_games(
        self, db_session: AsyncSession
    ) -> None:
        """One fully-analyzed game + one all-null game: total_n==2, analyzed_n==1."""
        # Analyzed game: 5 plies, only the final ply has null eval -> 4/5 = 0.80?
        # The kernel coverage gate is >= 0.90, so we need (N-1)/N >= 0.90 -> N >= 10.
        # Seed 10 plies with eval on the first 9 (final ply null is the realistic shape).
        analyzed = await _seed_game(db_session, user_id=99999, user_color="white")
        for ply in range(9):
            await _seed_position(db_session, game=analyzed, ply=ply, eval_cp=0)
        await _seed_position(db_session, game=analyzed, ply=9, eval_cp=None)  # final null

        # chess.com-style game: all-null eval -> coverage 0.0 -> NOT analyzed.
        chesscom = await _seed_game(db_session, user_id=99999, user_color="white")
        for ply in range(10):
            await _seed_position(db_session, game=chesscom, ply=ply, eval_cp=None)

        total_n, analyzed_n = await count_filtered_and_analyzed(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert total_n == 2, "both games are in the filtered set"
        assert analyzed_n == 1, "only the >=90%-coverage game counts as analyzed"

        ids = await analyzed_game_ids(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert analyzed.id in ids
        assert chesscom.id not in ids

    @pytest.mark.asyncio
    async def test_analyzed_denominator_user_scoped(self, db_session: AsyncSession) -> None:
        """A different user's analyzed game is not counted/listed."""
        game = await _seed_game(db_session, user_id=99999, user_color="white")
        for ply in range(9):
            await _seed_position(db_session, game=game, ply=ply, eval_cp=0)
        await _seed_position(db_session, game=game, ply=9, eval_cp=None)

        total_n, analyzed_n = await count_filtered_and_analyzed(
            db_session,
            user_id=99998,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert total_n == 0
        assert analyzed_n == 0
        ids = await analyzed_game_ids(
            db_session,
            user_id=99998,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert ids == []


# Keep `func` import referenced (used by downstream count-aggregate scaffolds).
_ = func
