"""Integration tests for app.repositories.library_repository (Phase 106-01).

Uses a real PostgreSQL database via the db_session fixture (rolled-back per test).
Covers the Wave-0 seam guards from 106-VALIDATION.md:

- `-k exists_filter` — the user-color-scoped EXISTS severity filter selects games
  with >=1 USER ply of the requested severity, excludes clean games, and EXCLUDES
  a game where only the OPPONENT blundered (B1 guard).
- `-k cross_check` — the SQL window-scan flagged (ply, severity) set equals the
  user-color-filtered M+B subset of the Python kernel `_run_all_moves_pass`
  on the SAME fixture rows (B2, the load-bearing seam guard).
- `-k analyzed_denominator` — placeholder, implemented in 106-03.

Reuses _seed_game / _seed_position helpers patterned on tests/test_flaws_repository.py.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.library_repository import (
    analyzed_game_ids,
    count_filtered_and_analyzed,
    flaw_exists_subquery,
    query_filtered_games,
)
from app.repositories.query_utils import apply_game_filters
from app.services.eval_utils import eval_cp_to_expected_score
from app.services.flaws_service import BLUNDER_DROP, _run_all_moves_pass


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


def _cp_for_white_drop(drop_target: float) -> tuple[int, int]:
    """Return (prev_cp, curr_cp) so a WHITE-mover ES drop is >= drop_target."""
    prev_cp = 0
    es_before = eval_cp_to_expected_score(prev_cp, "white")
    curr_cp = -10
    while es_before - eval_cp_to_expected_score(curr_cp, "white") < drop_target:
        curr_cp -= 10
    return prev_cp, curr_cp


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
    """The user-color-scoped EXISTS flaw-severity filter (LIBG-08, B1)."""

    @pytest.mark.asyncio
    async def test_exists_filter_selects_user_blunder_excludes_clean(
        self, db_session: AsyncSession
    ) -> None:
        """A game with a USER blunder is selected; a clean game is not."""
        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)

        # Game A: white (user) blunders at ply 2.
        game_a = await _seed_game(db_session, user_color="white")
        await _seed_position(db_session, game=game_a, ply=0, eval_cp=prev_b)
        await _seed_position(db_session, game=game_a, ply=1, eval_cp=prev_b)  # black clean
        await _seed_position(db_session, game=game_a, ply=2, eval_cp=curr_b)  # white blunder
        await _seed_position(db_session, game=game_a, ply=3, eval_cp=curr_b)  # black clean

        # Game B: all even eval — nobody blunders.
        game_b = await _seed_game(db_session, user_color="white")
        for n in range(4):
            await _seed_position(db_session, game=game_b, ply=n, eval_cp=0)

        matched = await _matching_game_ids(db_session, user_id=99999, severities=["blunder"])
        assert game_a.id in matched, "game with a USER blunder must match severity=blunder"
        assert game_b.id not in matched, "clean game must not match"

    @pytest.mark.asyncio
    async def test_exists_filter_excludes_opponent_only_blunder(
        self, db_session: AsyncSession
    ) -> None:
        """B1 guard: a game where ONLY the opponent blundered is EXCLUDED.

        The user is BLACK and plays cleanly; the white (opponent) drop is a
        blunder. severity=["blunder"] must NOT match this game.
        """
        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)

        # user is BLACK; white (opponent) blunders at ply 2, black (user) is clean.
        game = await _seed_game(db_session, user_color="black")
        await _seed_position(db_session, game=game, ply=0, eval_cp=prev_b)
        await _seed_position(db_session, game=game, ply=1, eval_cp=prev_b)  # black (user) clean
        await _seed_position(db_session, game=game, ply=2, eval_cp=curr_b)  # white (opp) blunder
        await _seed_position(db_session, game=game, ply=3, eval_cp=curr_b)  # black (user) clean

        matched = await _matching_game_ids(db_session, user_id=99999, severities=["blunder"])
        assert game.id not in matched, (
            "opponent-only-blunder game must be EXCLUDED by severity=blunder (B1)"
        )

    @pytest.mark.asyncio
    async def test_exists_filter_subquery_scoped_to_user(self, db_session: AsyncSession) -> None:
        """flaw_exists_subquery is user-scoped: another user's positions don't match."""
        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)
        game = await _seed_game(db_session, user_id=99999, user_color="white")
        await _seed_position(db_session, game=game, ply=0, eval_cp=prev_b)
        await _seed_position(db_session, game=game, ply=1, eval_cp=prev_b)
        await _seed_position(db_session, game=game, ply=2, eval_cp=curr_b)

        # Querying as a DIFFERENT user must not see this game's plies.
        stmt = select(Game.id).where(
            Game.user_id == 99999,
            flaw_exists_subquery(user_id=99998, severities=["blunder"]),
        )
        rows = set((await db_session.execute(stmt)).scalars().all())
        assert game.id not in rows, "EXISTS bound to a different user_id must not match"


# ---------------------------------------------------------------------------
# TestCrossCheck (-k cross_check) — the load-bearing seam guard (B2)
# ---------------------------------------------------------------------------


class TestCrossCheck:
    """SQL flagged set == user-color-filtered M+B subset of the kernel (B2)."""

    @pytest.mark.asyncio
    async def test_cross_check_sql_equals_kernel_subset(self, db_session: AsyncSession) -> None:
        """Seed mixed evals on BOTH colors; SQL flagged (ply, sev) == kernel M+B user subset."""
        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)

        # Build an evals timeline that has flaws on BOTH colors at different plies.
        # ply: 0   1     2     3     4     5
        # cp : 0  +0  curr_b  0  curr_b  prev_b  (varied to spread severities)
        eval_by_ply: dict[int, int] = {
            0: 0,
            1: 0,  # black move N=1: drop 0 -> clean
            2: curr_b,  # white move N=2: 0 -> curr_b (white blunder)
            3: 0,  # black move N=3: curr_b -> 0 (black-POV: improves for white = drop for black)
            4: curr_b,  # white move N=4: 0 -> curr_b (white blunder)
            5: prev_b,  # black move N=5
        }
        game = await _seed_game(db_session, user_color="white")
        positions = []
        for ply, cp in eval_by_ply.items():
            pos = await _seed_position(db_session, game=game, ply=ply, eval_cp=cp)
            positions.append(pos)

        # Kernel reference set: user-color-filtered M+B subset.
        all_moves = _run_all_moves_pass(positions)
        kernel_set = {
            (ply, sev)
            for ply, (mover, sev, _, _) in all_moves.items()
            if mover == game.user_color and sev in ("mistake", "blunder")
        }

        # SQL set: for each severity tier, the plies the EXISTS-style drop math flags.
        sql_set = await _sql_flagged_set(db_session, game=game)

        assert sql_set == kernel_set, (
            f"SQL flagged set {sql_set} != kernel user-color M+B subset {kernel_set}"
        )
        # Sanity: the fixture actually produced at least one user flaw.
        assert kernel_set, "fixture must produce >=1 user M+B flaw for a meaningful cross-check"

    @pytest.mark.asyncio
    async def test_cross_check_mate_branch_matches_kernel(self, db_session: AsyncSession) -> None:
        """Mate Option-B parity incl. eval_mate == 0 (python-chess Mate(0)) — guards WR-01.

        sign(0) == 0 would map eval_mate == 0 to cp 0 -> ES 0.5; the kernel maps a
        non-positive mate to -MATE_CP_EQUIVALENT -> ES ~= 0.0. With ES_before = 0.5
        (eval_cp == 0 at ply 1) the kernel flags a white blunder at ply 2, while the
        buggy sign() SQL would compute drop 0 and flag nothing — so this fixture fails
        iff the SQL mate transcription diverges from the Python kernel. The prior
        cross-check used only eval_cp rows and never exercised the mate branch (WR-02).
        """
        game = await _seed_game(db_session, user_color="white")
        positions = [
            await _seed_position(db_session, game=game, ply=0, eval_cp=0),
            await _seed_position(db_session, game=game, ply=1, eval_cp=0),
            # White move N=2 lands in a Mate(0) position (non-positive mate ->
            # white-POV ES ~= 0.0): a blunder from the 0.5 prior.
            await _seed_position(db_session, game=game, ply=2, eval_mate=0),
            await _seed_position(db_session, game=game, ply=3, eval_cp=0),
        ]

        all_moves = _run_all_moves_pass(positions)
        kernel_set = {
            (ply, sev)
            for ply, (mover, sev, _, _) in all_moves.items()
            if mover == game.user_color and sev in ("mistake", "blunder")
        }
        sql_set = await _sql_flagged_set(db_session, game=game)

        assert (2, "blunder") in kernel_set, (
            "fixture must classify the Mate(0) white move as a blunder"
        )
        assert sql_set == kernel_set, (
            f"SQL mate-branch flagged set {sql_set} != kernel subset {kernel_set} "
            "(eval_mate == 0 must map to -MATE_CP_EQUIVALENT, not sign(0))"
        )


async def _sql_flagged_set(session: AsyncSession, *, game: Game) -> set[tuple[int, str]]:
    """Return {(ply, severity)} the SQL drop-math flags for the user's plies.

    Runs flaw_exists_subquery once per severity tier in isolation against a
    single-ply window so the per-ply flag is observable. We detect, per ply,
    the HIGHEST tier whose threshold the drop meets (mirroring _classify_severity).
    """
    from app.repositories.library_repository import flagged_plies_for_severity

    flagged: dict[int, str] = {}
    # Order matters: blunder (highest) wins, then mistake.
    for sev in ("mistake", "blunder"):
        plies = await flagged_plies_for_severity(
            session, game_id=game.id, user_id=game.user_id, severity=sev
        )
        for ply in plies:
            # Highest tier wins: only upgrade, never downgrade.
            if sev == "blunder" or ply not in flagged:
                flagged[ply] = sev
    return {(ply, sev) for ply, sev in flagged.items()}


# ---------------------------------------------------------------------------
# TestQueryFilteredGames (-k query_filtered_games) — paginated archive (106-02)
# ---------------------------------------------------------------------------


class TestQueryFilteredGames:
    """query_filtered_games: paginated user archive + boolean severity filter."""

    @pytest.mark.asyncio
    async def test_severity_filter_narrows_to_blunder_games(self, db_session: AsyncSession) -> None:
        """severity=["blunder"] returns only games with a USER blunder."""
        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)

        # Game A: white (user) blunders at ply 2.
        game_a = await _seed_game(db_session, user_color="white")
        await _seed_position(db_session, game=game_a, ply=0, eval_cp=prev_b)
        await _seed_position(db_session, game=game_a, ply=1, eval_cp=prev_b)
        await _seed_position(db_session, game=game_a, ply=2, eval_cp=curr_b)
        await _seed_position(db_session, game=game_a, ply=3, eval_cp=curr_b)

        # Game B: clean (all even eval).
        game_b = await _seed_game(db_session, user_color="white")
        for n in range(4):
            await _seed_position(db_session, game=game_b, ply=n, eval_cp=0)

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
