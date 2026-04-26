"""Integration tests for the stats repository.

All tests use a real PostgreSQL database through the db_session fixture,
which wraps each test in a rolled-back transaction for isolation.

Coverage:
- query_rating_history: returns per-platform per-game rating data points
- query_rating_history: filters by recency_cutoff
- query_rating_history: excludes games with NULL user_rating
- query_results_by_time_control: returns SQL-aggregated (bucket, total, wins, draws, losses) tuples
- query_results_by_time_control: filters by recency_cutoff
- query_results_by_time_control: excludes games with NULL time_control_bucket
- query_results_by_color: returns SQL-aggregated (user_color, total, wins, draws, losses) tuples
- query_results_by_color: filters by recency_cutoff
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.repositories.stats_repository import (
    query_rating_history,
    query_results_by_color,
    query_results_by_time_control,
    query_top_openings_sql_wdl,
)


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


def _unique_game_id() -> str:
    """Return a unique platform_game_id for each call."""
    return str(uuid.uuid4())


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user
    for uid in [2, 99999]:
        await ensure_test_user(db_session, uid)


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 99999,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    time_control_bucket: str | None = "blitz",
    white_rating: int | None = None,
    black_rating: int | None = None,
    played_at: datetime.datetime | None = None,
    opening_eco: str | None = None,
    opening_name: str | None = None,
) -> Game:
    """Insert a Game row and flush to obtain IDs.

    Pass white_rating/black_rating to set the player ratings.
    The effective user_rating is derived by the repository via CASE WHEN user_color.
    """
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_game_id(),
        platform_url="https://chess.com/game/123",
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=True,
        white_rating=white_rating,
        black_rating=black_rating,
        opening_eco=opening_eco,
        opening_name=opening_name,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()

    # If the game is tagged with a named opening, seed a matching game_positions
    # row carrying that opening's full_hash. The top-openings query (post
    # PRE-01.1) ranks by COUNT(DISTINCT game) joined through game_positions —
    # without this row the JOIN would drop the game and the count would be 0.
    if opening_eco is not None and opening_name is not None:
        from sqlalchemy import select as _select
        from app.models.game_position import GamePosition
        from app.repositories.stats_repository import _openings_dedup
        opening_lookup = await session.execute(
            _select(_openings_dedup.c.full_hash, _openings_dedup.c.ply_count)
            .where(_openings_dedup.c.eco == opening_eco)
            .where(_openings_dedup.c.name == opening_name)
            .limit(1)
        )
        row = opening_lookup.first()
        if row is not None:
            full_hash, ply_count = row
            session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=user_id,
                    ply=ply_count,
                    full_hash=full_hash,
                    white_hash=0,
                    black_hash=0,
                )
            )
            await session.flush()
    return game


# ---------------------------------------------------------------------------
# TestQueryRatingHistory
# ---------------------------------------------------------------------------


class TestQueryRatingHistory:
    """Tests for query_rating_history repository function."""

    @pytest.mark.asyncio
    async def test_returns_game_with_rating(self, db_session: AsyncSession) -> None:
        """A game with white_rating (user is white) should appear in results."""
        await _seed_game(db_session, platform="chess.com", user_color="white", white_rating=1600)

        rows = await query_rating_history(
            db_session, user_id=99999, platform="chess.com", recency_cutoff=None
        )

        assert len(rows) == 1
        date_val, rating, tc_bucket = rows[0]
        assert rating == 1600
        assert tc_bucket == "blitz"

    @pytest.mark.asyncio
    async def test_excludes_null_rating(self, db_session: AsyncSession) -> None:
        """Games without white_rating when user is white should be excluded."""
        await _seed_game(db_session, platform="chess.com", user_color="white", white_rating=None)

        rows = await query_rating_history(
            db_session, user_id=99999, platform="chess.com", recency_cutoff=None
        )

        assert len(rows) == 0

    @pytest.mark.asyncio
    async def test_filters_by_platform(self, db_session: AsyncSession) -> None:
        """Only games from the specified platform are returned."""
        await _seed_game(db_session, platform="chess.com", user_color="white", white_rating=1500)
        await _seed_game(db_session, platform="lichess", user_color="white", white_rating=1600)

        chesscom_rows = await query_rating_history(
            db_session, user_id=99999, platform="chess.com", recency_cutoff=None
        )
        lichess_rows = await query_rating_history(
            db_session, user_id=99999, platform="lichess", recency_cutoff=None
        )

        assert len(chesscom_rows) == 1
        assert len(lichess_rows) == 1
        assert chesscom_rows[0][1] == 1500
        assert lichess_rows[0][1] == 1600

    @pytest.mark.asyncio
    async def test_filters_by_recency_cutoff(self, db_session: AsyncSession) -> None:
        """Games before the recency_cutoff should be excluded."""
        old_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=60)
        recent_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=5)
        cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)

        await _seed_game(db_session, platform="chess.com", user_color="white", white_rating=1400, played_at=old_date)
        await _seed_game(db_session, platform="chess.com", user_color="white", white_rating=1600, played_at=recent_date)

        rows = await query_rating_history(
            db_session, user_id=99999, platform="chess.com", recency_cutoff=cutoff
        )

        assert len(rows) == 1
        assert rows[0][1] == 1600

    @pytest.mark.asyncio
    async def test_ordered_by_played_at(self, db_session: AsyncSession) -> None:
        """Results should be ordered chronologically by played_at."""
        dates = [
            datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=i)
            for i in [10, 5, 1]
        ]
        ratings = [1400, 1500, 1600]

        # Insert in reverse order
        for dt, rating in zip(reversed(dates), reversed(ratings)):
            await _seed_game(db_session, platform="chess.com", user_color="white", white_rating=rating, played_at=dt)

        rows = await query_rating_history(
            db_session, user_id=99999, platform="chess.com", recency_cutoff=None
        )

        actual_ratings = [r[1] for r in rows]
        assert actual_ratings == sorted(actual_ratings)

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self, db_session: AsyncSession) -> None:
        """Only games for the specified user_id are returned."""
        await _seed_game(db_session, user_id=99999, platform="chess.com", user_color="white", white_rating=1500)
        await _seed_game(db_session, user_id=2, platform="chess.com", user_color="white", white_rating=1900)

        rows = await query_rating_history(
            db_session, user_id=99999, platform="chess.com", recency_cutoff=None
        )

        assert len(rows) == 1
        assert rows[0][1] == 1500


# ---------------------------------------------------------------------------
# TestQueryResultsByTimeControl
# ---------------------------------------------------------------------------


class TestQueryResultsByTimeControl:
    """Tests for query_results_by_time_control — SQL-aggregated WDL per bucket."""

    @pytest.mark.asyncio
    async def test_returns_aggregated_wdl(self, db_session: AsyncSession) -> None:
        """Should return (bucket, total, wins, draws, losses) aggregated in SQL."""
        # 2 wins + 1 draw as white in blitz
        await _seed_game(db_session, time_control_bucket="blitz", result="1-0", user_color="white")
        await _seed_game(db_session, time_control_bucket="blitz", result="1-0", user_color="white")
        await _seed_game(db_session, time_control_bucket="blitz", result="1/2-1/2", user_color="white")

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=None
        )

        assert len(rows) == 1
        bucket, total, wins, draws, losses = rows[0]
        assert bucket == "blitz"
        assert total == 3
        assert wins == 2
        assert draws == 1
        assert losses == 0

    @pytest.mark.asyncio
    async def test_excludes_null_time_control_bucket(self, db_session: AsyncSession) -> None:
        """Games without time_control_bucket should be excluded."""
        await _seed_game(db_session, time_control_bucket=None)

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=None
        )

        assert len(rows) == 0

    @pytest.mark.asyncio
    async def test_multiple_buckets(self, db_session: AsyncSession) -> None:
        """Returns one aggregated row per time control bucket."""
        await _seed_game(db_session, time_control_bucket="bullet", result="0-1", user_color="white")
        await _seed_game(db_session, time_control_bucket="blitz", result="1-0", user_color="white")
        await _seed_game(db_session, time_control_bucket="rapid", result="1/2-1/2", user_color="white")

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=None
        )

        assert len(rows) == 3
        buckets = {r[0] for r in rows}
        assert buckets == {"bullet", "blitz", "rapid"}

    @pytest.mark.asyncio
    async def test_filters_by_recency_cutoff(self, db_session: AsyncSession) -> None:
        """Games before the recency_cutoff should be excluded."""
        old_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=60)
        recent_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=5)
        cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)

        await _seed_game(db_session, time_control_bucket="bullet", played_at=old_date)
        await _seed_game(db_session, time_control_bucket="blitz", played_at=recent_date)

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=cutoff
        )

        assert len(rows) == 1
        assert rows[0][0] == "blitz"

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self, db_session: AsyncSession) -> None:
        """Only games for the specified user_id are returned."""
        await _seed_game(db_session, user_id=99999, time_control_bucket="blitz")
        await _seed_game(db_session, user_id=2, time_control_bucket="rapid")

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=None
        )

        assert len(rows) == 1
        assert rows[0][0] == "blitz"

    @pytest.mark.asyncio
    async def test_filters_by_platform_chess_com(self, db_session: AsyncSession) -> None:
        """Only chess.com games are returned when platform='chess.com'."""
        await _seed_game(db_session, platform="chess.com", time_control_bucket="blitz")
        await _seed_game(db_session, platform="lichess", time_control_bucket="rapid")

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=None, platform="chess.com"
        )

        assert len(rows) == 1
        assert rows[0][0] == "blitz"

    @pytest.mark.asyncio
    async def test_filters_by_platform_none_returns_all(self, db_session: AsyncSession) -> None:
        """All games are returned when platform=None (default behavior)."""
        await _seed_game(db_session, platform="chess.com", time_control_bucket="blitz")
        await _seed_game(db_session, platform="lichess", time_control_bucket="rapid")

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=None, platform=None
        )

        assert len(rows) == 2
        buckets = {r[0] for r in rows}
        assert buckets == {"blitz", "rapid"}

    @pytest.mark.asyncio
    async def test_wdl_counts_black_perspective(self, db_session: AsyncSession) -> None:
        """Wins/losses should be computed from the user's perspective (black)."""
        # Black wins when result is "0-1", loses when "1-0"
        await _seed_game(db_session, time_control_bucket="blitz", result="0-1", user_color="black")
        await _seed_game(db_session, time_control_bucket="blitz", result="1-0", user_color="black")

        rows = await query_results_by_time_control(
            db_session, user_id=99999, recency_cutoff=None
        )

        assert len(rows) == 1
        _, total, wins, draws, losses = rows[0]
        assert total == 2
        assert wins == 1
        assert losses == 1
        assert draws == 0


# ---------------------------------------------------------------------------
# TestQueryResultsByColor
# ---------------------------------------------------------------------------


class TestQueryResultsByColor:
    """Tests for query_results_by_color — SQL-aggregated WDL per color."""

    @pytest.mark.asyncio
    async def test_returns_aggregated_wdl(self, db_session: AsyncSession) -> None:
        """Should return (color, total, wins, draws, losses) aggregated in SQL."""
        # 2 wins + 1 loss as white
        await _seed_game(db_session, user_color="white", result="1-0")
        await _seed_game(db_session, user_color="white", result="1-0")
        await _seed_game(db_session, user_color="white", result="0-1")

        rows = await query_results_by_color(db_session, user_id=99999, recency_cutoff=None)

        assert len(rows) == 1
        color, total, wins, draws, losses = rows[0]
        assert color == "white"
        assert total == 3
        assert wins == 2
        assert draws == 0
        assert losses == 1

    @pytest.mark.asyncio
    async def test_both_colors_returned(self, db_session: AsyncSession) -> None:
        """Returns one aggregated row per color."""
        await _seed_game(db_session, user_color="white", result="1-0")
        await _seed_game(db_session, user_color="black", result="0-1")

        rows = await query_results_by_color(db_session, user_id=99999, recency_cutoff=None)

        assert len(rows) == 2
        colors = {r[0] for r in rows}
        assert colors == {"white", "black"}

    @pytest.mark.asyncio
    async def test_filters_by_recency_cutoff(self, db_session: AsyncSession) -> None:
        """Games before the recency_cutoff should be excluded."""
        old_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=60)
        recent_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=5)
        cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)

        await _seed_game(db_session, user_color="white", played_at=old_date)
        await _seed_game(db_session, user_color="black", played_at=recent_date)

        rows = await query_results_by_color(db_session, user_id=99999, recency_cutoff=cutoff)

        assert len(rows) == 1
        assert rows[0][0] == "black"

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self, db_session: AsyncSession) -> None:
        """Only games for the specified user_id are returned."""
        await _seed_game(db_session, user_id=99999, user_color="white")
        await _seed_game(db_session, user_id=2, user_color="black")

        rows = await query_results_by_color(db_session, user_id=99999, recency_cutoff=None)

        assert len(rows) == 1
        assert rows[0][0] == "white"

    @pytest.mark.asyncio
    async def test_filters_by_platform_lichess(self, db_session: AsyncSession) -> None:
        """Only lichess games are returned when platform='lichess'."""
        await _seed_game(db_session, platform="chess.com", user_color="white")
        await _seed_game(db_session, platform="lichess", user_color="black")

        rows = await query_results_by_color(db_session, user_id=99999, recency_cutoff=None, platform="lichess")

        assert len(rows) == 1
        assert rows[0][0] == "black"

    @pytest.mark.asyncio
    async def test_filters_by_platform_none_returns_all(self, db_session: AsyncSession) -> None:
        """All games are returned when platform=None (default behavior)."""
        await _seed_game(db_session, platform="chess.com", user_color="white")
        await _seed_game(db_session, platform="lichess", user_color="black")

        rows = await query_results_by_color(db_session, user_id=99999, recency_cutoff=None, platform=None)

        assert len(rows) == 2
        colors = {r[0] for r in rows}
        assert colors == {"white", "black"}

    @pytest.mark.asyncio
    async def test_wdl_counts_black_wins(self, db_session: AsyncSession) -> None:
        """Black wins (result 0-1) should be counted as wins for the black row."""
        await _seed_game(db_session, user_color="black", result="0-1")
        await _seed_game(db_session, user_color="black", result="1-0")
        await _seed_game(db_session, user_color="black", result="1/2-1/2")

        rows = await query_results_by_color(db_session, user_id=99999, recency_cutoff=None)

        assert len(rows) == 1
        _, total, wins, draws, losses = rows[0]
        assert total == 3
        assert wins == 1
        assert draws == 1
        assert losses == 1


# ---------------------------------------------------------------------------
# TestQueryTopOpeningsSqlWDL
# ---------------------------------------------------------------------------


class TestQueryTopOpeningsSqlWDL:
    """Tests for the SQL-side WDL aggregation query (Phase 37)."""

    @pytest.mark.asyncio
    async def test_sql_wdl_returns_correct_counts(self, db_session: AsyncSession) -> None:
        """SQL WDL should compute wins/draws/losses in SQL, not Python."""
        # Seed 3 wins + 2 draws for King's Pawn Game as white.
        # "King's Pawn Game" (B00, ply_count=1) exists in openings_dedup.
        for _ in range(3):
            await _seed_game(db_session, user_id=99999, result="1-0", user_color="white",
                             opening_eco="B00", opening_name="King's Pawn Game")
        for _ in range(2):
            await _seed_game(db_session, user_id=99999, result="1/2-1/2", user_color="white",
                             opening_eco="B00", opening_name="King's Pawn Game")

        rows = await query_top_openings_sql_wdl(
            db_session, user_id=99999, color="white", min_games=1, limit=10, min_ply=1)
        assert len(rows) >= 1
        # Find the King's Pawn Game row
        kpg = [r for r in rows if r[0] == "B00" and r[1] == "King's Pawn Game"]
        assert len(kpg) == 1
        eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses = kpg[0]
        assert wins == 3
        assert draws == 2
        assert losses == 0
        assert total == 5
        assert pgn  # non-empty PGN from openings_dedup
        assert fen  # non-empty FEN from openings_dedup
        assert "/" in fen  # FEN has rank separators
        assert full_hash is not None  # precomputed Zobrist hash from openings_dedup
        # King's Pawn Game has ply_count=1 (white-defined). For a white user this
        # is same-color, so display_name has no "vs. " prefix.
        assert display_name == "King's Pawn Game"

    @pytest.mark.asyncio
    async def test_sql_wdl_excludes_below_min_games(self, db_session: AsyncSession) -> None:
        """Openings below min_games threshold should not appear."""
        await _seed_game(db_session, user_id=99999, result="1-0", user_color="white",
                         opening_eco="B00", opening_name="King's Pawn Game")
        rows = await query_top_openings_sql_wdl(
            db_session, user_id=99999, color="white", min_games=100, limit=10, min_ply=1)
        assert len(rows) == 0

    @pytest.mark.asyncio
    async def test_sql_wdl_filters_by_time_control(self, db_session: AsyncSession) -> None:
        """time_control filter should restrict results."""
        for _ in range(10):
            await _seed_game(db_session, user_id=99999, result="1-0", user_color="white",
                             opening_eco="B00", opening_name="King's Pawn Game",
                             time_control_bucket="blitz")
        for _ in range(10):
            await _seed_game(db_session, user_id=99999, result="1-0", user_color="white",
                             opening_eco="B00", opening_name="King's Pawn Game",
                             time_control_bucket="rapid")

        # Filter to blitz only
        rows = await query_top_openings_sql_wdl(
            db_session, user_id=99999, color="white", min_games=1, limit=10, min_ply=1,
            time_control=["blitz"])
        kpg = [r for r in rows if r[0] == "B00" and r[1] == "King's Pawn Game"]
        assert len(kpg) == 1
        # Tuple shape: (eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)
        assert kpg[0][6] == 10  # total = 10 blitz games only

    @pytest.mark.asyncio
    async def test_sql_wdl_ply_threshold_excludes_short_openings(self, db_session: AsyncSession) -> None:
        """min_ply filter should exclude openings with ply_count below threshold."""
        # King's Pawn Game has ply_count=1 (1. e4)
        for _ in range(10):
            await _seed_game(db_session, user_id=99999, result="1-0", user_color="white",
                             opening_eco="B00", opening_name="King's Pawn Game")
        # With min_ply=5, King's Pawn Game (ply=1) should be excluded
        rows = await query_top_openings_sql_wdl(
            db_session, user_id=99999, color="white", min_games=1, limit=10, min_ply=5)
        kpg = [r for r in rows if r[0] == "B00" and r[1] == "King's Pawn Game"]
        assert len(kpg) == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("color", ["white", "black"])
    async def test_top_openings_includes_off_color_with_vs_prefix(
        self, db_session: AsyncSession, color: str
    ) -> None:
        """PRE-01: parity filter removed — off-color openings appear with `vs. ` prefix.

        Seeds two openings with known parity:
        - "King's Pawn Game" (B00, ply_count=1, odd) — white-defined
        - "Caro-Kann Defense" (B10, ply_count=2, even) — black-defined

        For each user color, both openings should appear in the result. The
        opening whose defining ply parity differs from the user's color must
        carry a `display_name` of `f"vs. {opening_name}"`; the same-color
        opening must keep its canonical name.
        """
        # Seed enough games for each opening to clear min_games. Use the same
        # user_color for both openings (the "user color" determines whose
        # perspective we're showing — the parity filter previously hid
        # off-color openings for that perspective).
        for _ in range(5):
            await _seed_game(
                db_session, user_id=99999, result="1-0", user_color=color,
                opening_eco="B00", opening_name="King's Pawn Game",
            )
            await _seed_game(
                db_session, user_id=99999, result="1-0", user_color=color,
                opening_eco="B10", opening_name="Caro-Kann Defense",
            )

        # min_ply=1 ensures both ply=1 (B00) and ply=2 (B10) qualify.
        rows = await query_top_openings_sql_wdl(
            db_session, user_id=99999,
            color="white" if color == "white" else "black",
            min_games=1, limit=10, min_ply=1,
        )

        by_eco = {r[0]: r for r in rows}
        assert "B00" in by_eco, "King's Pawn Game (white-defined) should appear"
        assert "B10" in by_eco, "Caro-Kann Defense (black-defined) should appear"

        # display_name is the 3rd column (index 2)
        kpg_display_name = by_eco["B00"][2]
        ckd_display_name = by_eco["B10"][2]

        if color == "white":
            # White user: B00 (white-defined) is same-color → no prefix
            #             B10 (black-defined) is off-color → "vs. " prefix
            assert kpg_display_name == "King's Pawn Game"
            assert ckd_display_name == "vs. Caro-Kann Defense"
        else:
            # Black user: B00 (white-defined) is off-color → "vs. " prefix
            #             B10 (black-defined) is same-color → no prefix
            assert kpg_display_name == "vs. King's Pawn Game"
            assert ckd_display_name == "Caro-Kann Defense"
