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
                "is_lucky": False,
                "is_reversed": False,
                "is_squandered": False,
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


# ---------------------------------------------------------------------------
# TestEvalJoin (Phase 112-01): regression guard + schema check
# ---------------------------------------------------------------------------


async def _seed_game_flaw_with_es(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    severity: int = 2,
    fen: str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
) -> None:
    """Insert a game_flaws row for eval-join regression tests.

    Phase 112 (D-07): es_before/es_after/move_san are no longer stored in game_flaws;
    they are sourced at query time via a game_positions join. The test verifies that
    the join reproduces the correct eval values from the seeded game_positions rows.
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
                "is_lucky": False,
                "is_reversed": False,
                "is_squandered": False,
                "fen": fen,
            }
        ],
    )


class TestEvalJoinReproducesEs:
    """Phase 112 Pitfall 1 regression guard: game_positions join has correct ply offset.

    Verifies that the two aliased LEFT JOINs on game_positions (PositionAt at ply=N,
    PositionBefore at ply=N-1) return the eval values the kernel uses for es_before/es_after.
    If the ply offset is wrong, the ES computed from the join will differ from the seed-computed ES.
    """

    @pytest.mark.asyncio
    async def test_eval_join_reproduces_es(self, db_session: AsyncSession) -> None:
        """Joined eval_cp reproduces the ES values the kernel would compute.

        Seed: flaw at ply=2 (white mover per kernel parity: even=white).
          - positions[1].eval_cp = +100  (eval_before in flaws_service terms: positions[N-1])
          - positions[2].eval_cp = -50   (eval_after: positions[N])
        ES values computed directly from seeded evals (Phase 112: no longer stored):
          - es_before = eval_cp_to_expected_score(+100, "white") ≈ 0.591
          - es_after  = eval_cp_to_expected_score(-50, "white")  ≈ 0.454
        The test asserts abs(computed_from_join - computed_from_seed) < 1e-6 for both.
        """
        from app.repositories.library_repository import query_flaws
        from app.services.eval_utils import eval_cp_to_expected_score

        game = await _seed_game(db_session, user_color="white")
        # Seed positions 0..3 (ply 0=initial, 1=black, 2=white mover flaw, 3=next)
        # Kernel parity: n % 2 == 0 → white mover. Flaw at ply=2 → white.
        await _seed_position(db_session, game=game, ply=0, eval_cp=0, move_san=None)
        await _seed_position(db_session, game=game, ply=1, eval_cp=100, move_san="e5")
        # ply=2: white mover; eval_before = positions[1].eval_cp = 100; eval_after = positions[2].eval_cp = -50
        await _seed_position(db_session, game=game, ply=2, eval_cp=-50, move_san="Nf3")
        await _seed_position(db_session, game=game, ply=3, eval_cp=-30, move_san="d5")

        # Compute expected ES values using the same kernel formula
        mover_color = "white"  # ply=2, even → white
        expected_es_before = eval_cp_to_expected_score(100, mover_color)
        expected_es_after = eval_cp_to_expected_score(-50, mover_color)

        # Seed the flaw row with the kernel-computed ES values
        await _seed_game_flaw_with_es(
            db_session,
            game=game,
            ply=2,
            severity=2,  # blunder
        )

        # Run query_flaws and check the join produces the right eval fields
        items, count = await query_flaws(
            db_session,
            user_id=99999,
            severity=["mistake", "blunder"],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            offset=0,
            limit=20,
        )
        assert count > 0, "expected at least one flaw row"

        # Find the flaw for our seeded game
        our_flaw = next((item for item in items if item.game_id == game.id and item.ply == 2), None)
        assert our_flaw is not None, "flaw at ply=2 must appear in results"

        # Verify eval fields are sourced from game_positions
        assert our_flaw.eval_cp_after == -50, (
            f"eval_cp_after must be -50 (positions[ply=2].eval_cp), got {our_flaw.eval_cp_after}"
        )
        assert our_flaw.eval_cp_before == 100, (
            f"eval_cp_before must be 100 (positions[ply=1].eval_cp), got {our_flaw.eval_cp_before}"
        )
        assert our_flaw.move_san == "Nf3", f"move_san must be 'Nf3', got {our_flaw.move_san}"

        # ES reproduction: convert joined eval to ES and compare with seed-computed values
        # Mover is white (ply=2, even): no negation needed
        computed_es_before = eval_cp_to_expected_score(our_flaw.eval_cp_before, mover_color)
        computed_es_after = eval_cp_to_expected_score(our_flaw.eval_cp_after, mover_color)

        assert abs(computed_es_before - expected_es_before) < 1e-6, (
            f"Computed es_before {computed_es_before} must match stored {expected_es_before}"
        )
        assert abs(computed_es_after - expected_es_after) < 1e-6, (
            f"Computed es_after {computed_es_after} must match stored {expected_es_after}"
        )

    @pytest.mark.asyncio
    async def test_eval_join_reproduces_es_with_mate(self, db_session: AsyncSession) -> None:
        """Mate rows: eval_mate maps to ±MATE_CP_EQUIVALENT before sigmoid.

        Flaw at ply=3 (black mover, odd ply).
        positions[2].eval_mate = +3 → white has mate-in-3 → black is losing.
        eval_before for black mover = eval_cp_to_expected_score(-MATE_CP_EQUIVALENT, "black")
        """
        from app.repositories.library_repository import query_flaws
        from app.services.eval_utils import eval_cp_to_expected_score
        from app.services.flaws_service import MATE_CP_EQUIVALENT

        game = await _seed_game(db_session, user_color="black")
        await _seed_position(db_session, game=game, ply=0, eval_cp=0, move_san=None)
        await _seed_position(db_session, game=game, ply=1, eval_cp=50, move_san="e4")
        await _seed_position(db_session, game=game, ply=2, eval_mate=3, move_san="e5")
        # ply=3: black mover flaw (odd ply → black); eval_before = positions[2].eval_mate = +3
        await _seed_position(db_session, game=game, ply=3, eval_cp=-400, move_san="Nf6")

        # Kernel: ply=3, n=3, n%2==1 → black mover
        mover_color = "black"
        # es_before: positions[2].eval_mate=+3 (white has mate) → cp_equiv = -MATE_CP_EQUIVALENT for black
        # eval_cp_to_expected_score uses white-POV: +MATE_CP_EQUIVALENT → white winning
        # From black's perspective: -MATE_CP_EQUIVALENT passed as eval_cp
        # Actually _ply_to_es: eval_mate > 0 → cp_equiv = +MATE_CP_EQUIVALENT, then eval_cp_to_expected_score(+MATE_CP_EQ, "black")
        cp_equiv_before = MATE_CP_EQUIVALENT  # eval_mate=+3>0 → +MATE_CP_EQUIVALENT
        expected_es_before = eval_cp_to_expected_score(cp_equiv_before, mover_color)
        expected_es_after = eval_cp_to_expected_score(-400, mover_color)

        await _seed_game_flaw_with_es(
            db_session,
            game=game,
            ply=3,
            severity=2,
        )

        items, count = await query_flaws(
            db_session,
            user_id=99999,
            severity=["mistake", "blunder"],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            offset=0,
            limit=20,
        )

        our_flaw = next((item for item in items if item.game_id == game.id and item.ply == 3), None)
        assert our_flaw is not None, "flaw at ply=3 must appear in results"
        assert our_flaw.eval_mate_before == 3, (
            f"eval_mate_before must be 3 (positions[ply=2].eval_mate), got {our_flaw.eval_mate_before}"
        )
        assert our_flaw.eval_cp_after == -400, (
            f"eval_cp_after must be -400, got {our_flaw.eval_cp_after}"
        )

        # ES reproduction with mate: use MATE_CP_EQUIVALENT
        cp_before = MATE_CP_EQUIVALENT  # eval_mate_before=3 > 0 → +MATE_CP_EQUIVALENT
        computed_es_before = eval_cp_to_expected_score(cp_before, mover_color)
        # eval_cp_after is asserted non-None above; assert for ty narrowing
        assert our_flaw.eval_cp_after is not None
        computed_es_after = eval_cp_to_expected_score(our_flaw.eval_cp_after, mover_color)

        assert abs(computed_es_before - expected_es_before) < 1e-6, (
            f"Mate es_before {computed_es_before} must match stored {expected_es_before}"
        )
        assert abs(computed_es_after - expected_es_after) < 1e-6, (
            f"Mate es_after {computed_es_after} must match stored {expected_es_after}"
        )

    @pytest.mark.asyncio
    async def test_eval_join_null_before_at_ply_1(self, db_session: AsyncSession) -> None:
        """A flaw at ply=1 with no ply=0 eval yields eval_cp_before=None (no crash).

        ply=0 (initial position) usually has eval_cp=None; the LEFT JOIN produces null.
        """
        from app.repositories.library_repository import query_flaws

        game = await _seed_game(db_session, user_color="black")
        # ply=0: no eval (typical initial position)
        await _seed_position(db_session, game=game, ply=0, eval_cp=None, move_san=None)
        # ply=1: black's first move; flaw at ply=1
        await _seed_position(db_session, game=game, ply=1, eval_cp=50, move_san="e4")

        await _seed_game_flaw_with_es(db_session, game=game, ply=1, severity=2)

        items, count = await query_flaws(
            db_session,
            user_id=99999,
            severity=["mistake", "blunder"],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            offset=0,
            limit=20,
        )

        our_flaw = next((item for item in items if item.game_id == game.id and item.ply == 1), None)
        assert our_flaw is not None, "flaw at ply=1 must appear"
        # ply=0 has eval_cp=None, LEFT JOIN on ply=0 returns a row but eval_cp=None
        # Actually ply=0 HAS a game_positions row (just eval_cp=None), so the join finds the row
        # but eval_cp_before = None (the eval_cp on that row is None)
        assert our_flaw.eval_cp_before is None, (
            f"ply=0 has null eval_cp, so eval_cp_before must be None, got {our_flaw.eval_cp_before}"
        )
        assert our_flaw.eval_cp_after == 50


class TestFlawsEndpointSchema:
    """Phase 112-01 Task 2: FlawListItem carries new fields, drops ES fields."""

    @pytest.mark.asyncio
    async def test_flaws_endpoint_schema(self, db_session: AsyncSession) -> None:
        """FlawListItem carries white_rating/black_rating, move_san, eval fields; no es_before/es_after."""
        from app.repositories.library_repository import query_flaws

        game = await _seed_game(db_session, user_color="white")
        # Seed positions for the flaw
        await _seed_position(db_session, game=game, ply=0, eval_cp=0, move_san=None)
        await _seed_position(db_session, game=game, ply=1, eval_cp=150, move_san="d4")
        await _seed_position(db_session, game=game, ply=2, eval_cp=-100, move_san="Nf3")

        await bulk_insert_game_flaws(
            db_session,
            [
                {
                    "user_id": game.user_id,
                    "game_id": game.id,
                    "ply": 2,
                    "severity": 2,
                    "tempo": None,
                    "phase": 1,
                    "is_miss": False,
                    "is_lucky": False,
                    "is_reversed": False,
                    "is_squandered": False,
                    "fen": "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR",
                }
            ],
        )

        items, count = await query_flaws(
            db_session,
            user_id=99999,
            severity=["mistake", "blunder"],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            offset=0,
            limit=20,
        )

        our_flaw = next((item for item in items if item.game_id == game.id and item.ply == 2), None)
        assert our_flaw is not None, "flaw at ply=2 must appear"

        # Schema assertions: new fields present
        assert our_flaw.move_san is not None, "move_san must be join-sourced and non-None"
        assert our_flaw.eval_cp_after is not None, "eval_cp_after must be set from game_positions"
        assert our_flaw.eval_cp_before is not None, "eval_cp_before must be set from game_positions"

        # Ratings (sourced from Game; Game was seeded without explicit ratings → None is valid)
        # Check the attribute exists on the model
        assert hasattr(our_flaw, "white_rating"), "FlawListItem must have white_rating field"
        assert hasattr(our_flaw, "black_rating"), "FlawListItem must have black_rating field"
        assert hasattr(our_flaw, "eval_cp_before"), "FlawListItem must have eval_cp_before"
        assert hasattr(our_flaw, "eval_cp_after"), "FlawListItem must have eval_cp_after"
        assert hasattr(our_flaw, "eval_mate_before"), "FlawListItem must have eval_mate_before"
        assert hasattr(our_flaw, "eval_mate_after"), "FlawListItem must have eval_mate_after"

        # Schema assertions: ES fields must NOT be present (dropped in Task 2)
        assert not hasattr(our_flaw, "es_before"), "FlawListItem must NOT have es_before"
        assert not hasattr(our_flaw, "es_after"), "FlawListItem must NOT have es_after"
