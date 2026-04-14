"""Integration tests for the endgame repository.

All tests use a real PostgreSQL database through the db_session fixture,
which wraps each test in a rolled-back transaction for isolation.

Coverage:
- query_endgame_entry_rows: returns empty list for user with no endgame positions
- query_endgame_entry_rows: returns one row per (game_id, endgame_class) span with >= 6 plies
- query_endgame_entry_rows: ply threshold filters short spans (< 6 plies)
- query_endgame_entry_rows: multi-class per game — game counts in both rook and pawn categories
- query_endgame_entry_rows: material_imbalance from first ply of each span
- query_endgame_entry_rows: time_control filter returns only matching games
- query_endgame_entry_rows: platform filter returns only matching games
- query_endgame_games: returns paginated GameRecord-shaped rows for a given endgame class
- query_endgame_games: returns empty list for unknown endgame class
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition

# Import the threshold constants and repository functions.
from app.repositories.endgame_repository import (
    ENDGAME_PIECE_COUNT_THRESHOLD,
    ENDGAME_PLY_THRESHOLD,
    query_endgame_bucket_rows,
    query_endgame_entry_rows,
    query_endgame_games,
    query_endgame_performance_rows,
    query_endgame_timeline_rows,
)


# ---------------------------------------------------------------------------
# Seed helpers
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
    played_at: datetime.datetime | None = None,
    rated: bool = True,
    is_computer_game: bool = False,
) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_game_id(),
        platform_url=f"https://{platform}/game/123",
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        is_computer_game=is_computer_game,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()
    return game


async def _seed_game_position(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    piece_count: int = 2,
    material_count: int = 1000,
    material_signature: str = "KR_KR",
    material_imbalance: int = 0,
    endgame_class: int | None = 1,  # Default 1 (rook) matching default material_signature KR_KR
) -> GamePosition:
    """Insert a GamePosition row with endgame-relevant metadata.

    piece_count defaults to 2 (KR_KR — rook endgame, safely below threshold of 6).
    endgame_class defaults to 1 (rook), matching the default material_signature KR_KR.
    Use endgame_class=None for non-endgame positions.
    """
    pos = GamePosition(
        game_id=game.id,
        user_id=game.user_id,
        ply=ply,
        full_hash=hash(f"{game.id}-{ply}"),  # deterministic unique hash
        white_hash=hash(f"w-{game.id}-{ply}"),
        black_hash=hash(f"b-{game.id}-{ply}"),
        move_san=None,
        piece_count=piece_count,
        material_count=material_count,
        material_signature=material_signature,
        material_imbalance=material_imbalance,
        endgame_class=endgame_class,
    )
    session.add(pos)
    await session.flush()
    return pos


# ---------------------------------------------------------------------------
# TestQueryEndgameEntryRows
# ---------------------------------------------------------------------------


class TestQueryEndgameEntryRows:
    """Tests for query_endgame_entry_rows repository function."""

    @pytest.mark.asyncio
    async def test_no_games_returns_empty(self, db_session: AsyncSession) -> None:
        """User with no games returns empty list."""
        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_no_endgame_positions_returns_empty(self, db_session: AsyncSession) -> None:
        """Game with no endgame_class positions returns empty (endgame_class=None filters out)."""
        game = await _seed_game(db_session)
        # Position with no endgame class — not counted
        await _seed_game_position(
            db_session,
            game=game,
            ply=10,
            piece_count=ENDGAME_PIECE_COUNT_THRESHOLD + 2,
            material_signature="KQRB_KQRB",
            endgame_class=None,
        )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_returns_one_row_per_game_class_span(self, db_session: AsyncSession) -> None:
        """A game with >= ENDGAME_PLY_THRESHOLD positions of one class returns exactly one row."""
        game = await _seed_game(db_session)
        # Seed exactly ENDGAME_PLY_THRESHOLD rook endgame positions
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        # Should return exactly one row for this (game, rook) span
        assert len(rows) == 1
        (
            game_id,
            endgame_class,
            result,
            user_color,
            user_material_imbalance,
            user_material_imbalance_after,
        ) = rows[0]
        assert game_id == game.id
        assert endgame_class == 1  # rook

    @pytest.mark.asyncio
    async def test_ply_threshold_filters_short_spans(self, db_session: AsyncSession) -> None:
        """A game with fewer than ENDGAME_PLY_THRESHOLD plies in a class is excluded."""
        game = await _seed_game(db_session)
        # Seed only ENDGAME_PLY_THRESHOLD - 2 rook positions (below threshold)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD - 2):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        # Short span filtered out by HAVING clause
        assert rows == []

    @pytest.mark.asyncio
    async def test_multi_class_per_game(self, db_session: AsyncSession) -> None:
        """A game with >= threshold plies in two classes returns TWO rows (one per class)."""
        game = await _seed_game(db_session)
        # 7 rook endgame positions (endgame_class=1)
        for ply in range(20, 27):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )
        # 6 pawn endgame positions (endgame_class=3)
        for ply in range(30, 36):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KPP_KP", endgame_class=3
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        # Should return two rows: one for rook span, one for pawn span
        assert len(rows) == 2
        classes = {r[1] for r in rows}  # endgame_class is index 1
        assert 1 in classes  # rook
        assert 3 in classes  # pawn
        # Both rows belong to the same game
        assert all(r[0] == game.id for r in rows)

    @pytest.mark.asyncio
    async def test_entry_imbalance_at_first_ply_of_span(self, db_session: AsyncSession) -> None:
        """material_imbalance at the first (MIN) ply of each span is used for conversion/recovery."""
        game = await _seed_game(db_session, user_color="white")
        # Seed 6 rook positions; first at ply=20 with imbalance=200, rest with different values
        await _seed_game_position(
            db_session,
            game=game,
            ply=20,
            material_signature="KR_KR",
            endgame_class=1,
            material_imbalance=200,
        )
        for ply in range(21, 26):
            await _seed_game_position(
                db_session,
                game=game,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=50,  # different from entry ply
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        (
            _game_id,
            _endgame_class,
            _result,
            user_color,
            user_material_imbalance,
            user_material_imbalance_after,
        ) = rows[0]
        # For white user, user_material_imbalance = material_imbalance at entry ply (ply=20)
        assert user_color == "white"
        assert user_material_imbalance == 200  # from first ply of span
        # user_material_imbalance_after = imbalance at ply=24 (entry+4 = ply 20+4)
        # All plies 21-25 have imbalance=50, so after-value is 50
        assert user_material_imbalance_after == 50

    @pytest.mark.asyncio
    async def test_time_control_filter(self, db_session: AsyncSession) -> None:
        """time_control filter returns only games with matching time_control_bucket."""
        blitz_game = await _seed_game(db_session, time_control_bucket="blitz")
        rapid_game = await _seed_game(db_session, time_control_bucket="rapid")

        for game in [blitz_game, rapid_game]:
            for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
                await _seed_game_position(
                    db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
                )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=["blitz"],
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        game_ids = [r[0] for r in rows]
        assert blitz_game.id in game_ids
        assert rapid_game.id not in game_ids

    @pytest.mark.asyncio
    async def test_platform_filter(self, db_session: AsyncSession) -> None:
        """platform filter returns only games from the specified platform."""
        chesscom_game = await _seed_game(db_session, platform="chess.com")
        lichess_game = await _seed_game(db_session, platform="lichess")

        for game in [chesscom_game, lichess_game]:
            for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
                await _seed_game_position(
                    db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
                )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=["lichess"],
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        game_ids = [r[0] for r in rows]
        assert lichess_game.id in game_ids
        assert chesscom_game.id not in game_ids


# ---------------------------------------------------------------------------
# TestQueryEndgameGames
# ---------------------------------------------------------------------------


class TestQueryEndgameGames:
    """Tests for query_endgame_games repository function."""

    @pytest.mark.asyncio
    async def test_returns_games_for_rook_endgame(self, db_session: AsyncSession) -> None:
        """query_endgame_games returns Game objects for games with >= threshold rook plies."""
        game = await _seed_game(db_session)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        games, matched_count = await query_endgame_games(
            db_session,
            user_id=99999,
            endgame_class="rook",
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            offset=0,
            limit=20,
        )
        assert matched_count == 1
        assert len(games) == 1
        # Verify it returns game objects with expected attributes
        returned_game = games[0]
        assert returned_game.id == game.id

    @pytest.mark.asyncio
    async def test_unknown_endgame_class_returns_empty(self, db_session: AsyncSession) -> None:
        """Unknown endgame class (not rook/minor_piece/pawn/queen/mixed/pawnless) returns empty."""
        game = await _seed_game(db_session)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        games, matched_count = await query_endgame_games(
            db_session,
            user_id=99999,
            endgame_class="nonexistent_class",  # ty: ignore[invalid-argument-type]  # intentionally testing invalid class
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            offset=0,
            limit=20,
        )
        assert matched_count == 0
        assert games == []


# ---------------------------------------------------------------------------
# TestQueryEndgameTimelineRows
# ---------------------------------------------------------------------------


class TestQueryEndgameTimelineRows:
    """Tests for the rewritten query_endgame_timeline_rows (2-query implementation)."""

    @pytest.mark.asyncio
    async def test_empty_user_returns_all_empty(self, db_session: AsyncSession) -> None:
        """User with no games returns empty endgame_rows, non_endgame_rows, and empty per_type dicts."""
        endgame_rows, non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert endgame_rows == []
        assert non_endgame_rows == []
        # All 6 class slots initialized to empty lists
        assert set(per_type_rows.keys()) == {1, 2, 3, 4, 5, 6}
        assert all(v == [] for v in per_type_rows.values())

    @pytest.mark.asyncio
    async def test_per_class_bucketing_selective_classes(self, db_session: AsyncSession) -> None:
        """Seeding classes 1, 3, 5 only: those slots are non-empty; 2, 4, 6 stay empty."""
        import datetime

        base_dt = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

        # Game with rook endgame (class 1)
        game1 = await _seed_game(db_session, played_at=base_dt)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game1, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        # Game with pawn endgame (class 3)
        game3 = await _seed_game(db_session, played_at=base_dt + datetime.timedelta(days=1))
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game3, ply=ply, material_signature="KPP_KP", endgame_class=3
            )

        # Game with mixed endgame (class 5)
        game5 = await _seed_game(db_session, played_at=base_dt + datetime.timedelta(days=2))
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game5, ply=ply, material_signature="KRBP_KRP", endgame_class=5
            )

        endgame_rows, non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        # All 6 class slots must be present
        assert set(per_type_rows.keys()) == {1, 2, 3, 4, 5, 6}

        # Classes 1, 3, 5 were seeded — must be non-empty
        assert len(per_type_rows[1]) == 1
        assert len(per_type_rows[3]) == 1
        assert len(per_type_rows[5]) == 1

        # Classes 2, 4, 6 were NOT seeded — must be empty
        assert per_type_rows[2] == []
        assert per_type_rows[4] == []
        assert per_type_rows[6] == []

        # Overall endgame series must have one entry per game (3 games = 3 rows)
        assert len(endgame_rows) == 3

        # No non-endgame games were seeded
        assert non_endgame_rows == []

    @pytest.mark.asyncio
    async def test_per_type_rows_have_three_tuple_shape(self, db_session: AsyncSession) -> None:
        """Each row in per_type_rows must be (played_at, result, user_color) — 3 elements."""
        import datetime

        game = await _seed_game(
            db_session, played_at=datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc)
        )
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        _endgame_rows, _non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        rook_rows = per_type_rows[1]
        assert len(rook_rows) == 1
        row = rook_rows[0]
        # Service layer expects exactly 3 columns: played_at, result, user_color
        assert len(row) == 3  # type: ignore[arg-type]
        played_at, result, user_color = row  # type: ignore[misc]
        assert isinstance(played_at, datetime.datetime)
        assert result in ("1-0", "0-1", "1/2-1/2")
        assert user_color in ("white", "black")

    @pytest.mark.asyncio
    async def test_non_endgame_games_bucketed_correctly(self, db_session: AsyncSession) -> None:
        """Games without any qualifying endgame span land in non_endgame_rows, not endgame_rows."""
        import datetime

        base_dt = datetime.datetime(2024, 3, 1, tzinfo=datetime.timezone.utc)

        # Game that reaches rook endgame
        endgame_game = await _seed_game(db_session, played_at=base_dt)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=endgame_game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        # Game that never reaches any endgame class (endgame_class=None for all positions)
        non_eg_game = await _seed_game(db_session, played_at=base_dt + datetime.timedelta(days=1))
        for ply in range(1, 10):
            await _seed_game_position(db_session, game=non_eg_game, ply=ply, endgame_class=None)

        endgame_rows, non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        assert len(endgame_rows) == 1
        assert len(non_endgame_rows) == 1
        assert len(per_type_rows[1]) == 1


# ---------------------------------------------------------------------------
# TestQueryEndgameBucketRows (Phase 59 gap-closure)
# ---------------------------------------------------------------------------


class TestQueryEndgameBucketRows:
    """Tests for query_endgame_bucket_rows — one row per endgame game meeting ENDGAME_PLY_THRESHOLD.

    Per quick-260414-ae4, this query applies the same 6-ply HAVING as
    `_any_endgame_ply_subquery`, so bucket_rows and endgame_rows (from
    `query_endgame_performance_rows`) count the same population — the
    material-bucket invariant sum(material_rows.games) == endgame_wdl.total
    holds by symmetric construction.
    """

    @pytest.mark.asyncio
    async def test_empty_user_returns_empty(self, db_session: AsyncSession) -> None:
        rows = await query_endgame_bucket_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_short_endgame_is_excluded(self, db_session: AsyncSession) -> None:
        """Game with fewer than ENDGAME_PLY_THRESHOLD endgame plies is EXCLUDED.

        Post quick-260414-ae4 the bucket query mirrors the binary "has endgame" split:
        both apply the uniform 6-ply threshold, so a game that only briefly touched an
        endgame class (tactical transition) is classified as "no endgame" for the
        entire tab.
        """
        game = await _seed_game(db_session, result="1-0", user_color="white")
        # Only 2 endgame plies — well under the 6-ply threshold
        for ply in range(30, 32):
            await _seed_game_position(
                db_session,
                game=game,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=0,
            )

        rows = await query_endgame_bucket_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        # Short-endgame games no longer appear in bucket_rows — they are routed to the
        # "no endgame" side of the split by both this query and
        # query_endgame_performance_rows.
        assert rows == []

    @pytest.mark.asyncio
    async def test_long_endgame_returns_imbalance_after(self, db_session: AsyncSession) -> None:
        """Game with endgame >= ENDGAME_PLY_THRESHOLD plies returns non-NULL user_material_imbalance_after."""
        game = await _seed_game(db_session, result="1-0", user_color="white")
        entry_ply = 30
        # Seed ENDGAME_PLY_THRESHOLD plies so the game qualifies under the uniform rule;
        # the first PERSISTENCE_PLIES+1 plies also cover the imbalance_after position.
        for offset in range(ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session,
                game=game,
                ply=entry_ply + offset,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=150,  # conversion-qualifying
            )

        rows = await query_endgame_bucket_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        assert len(rows) == 1
        _game_id, _endgame_class, _result, _user_color, imb, imb_after = rows[0]
        assert imb == 150
        assert imb_after == 150  # conversion-qualifying, persisted PERSISTENCE_PLIES plies

    @pytest.mark.asyncio
    async def test_black_user_sign_flip(self, db_session: AsyncSession) -> None:
        """material_imbalance is sign-flipped when user_color == black (user perspective)."""
        game = await _seed_game(db_session, result="0-1", user_color="black")
        entry_ply = 30
        for offset in range(ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session,
                game=game,
                ply=entry_ply + offset,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=-150,  # white is behind by 150 → black (user) is ahead by 150
            )

        rows = await query_endgame_bucket_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        assert len(rows) == 1
        _game_id, _endgame_class, _result, user_color, imb, imb_after = rows[0]
        assert user_color == "black"
        assert imb == 150  # sign-flipped: user is +150 from their perspective
        assert imb_after == 150

    @pytest.mark.asyncio
    async def test_invariant_matches_performance_rows_count(self, db_session: AsyncSession) -> None:
        """Core invariant: bucket_rows count == endgame_rows count (post quick-260414-ae4).

        Mix of games: one long-endgame game (qualifies), one short-endgame game (now
        EXCLUDED from both bucket_rows and endgame_rows — routed to non_endgame_rows),
        and one non-endgame game. Because the 6-ply rule is now uniform, bucket_rows
        and endgame_rows include exactly the same game_ids.
        """
        # Game A: endgame spans 7 plies (above threshold)
        game_a = await _seed_game(db_session, result="1-0", user_color="white")
        for ply in range(30, 37):
            await _seed_game_position(
                db_session,
                game=game_a,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=0,
            )

        # Game B: endgame only 2 plies — under the uniform 6-ply threshold.
        # Now classified as "no endgame" on both sides of the split.
        game_b = await _seed_game(db_session, result="1/2-1/2", user_color="black")
        for ply in range(30, 32):
            await _seed_game_position(
                db_session,
                game=game_b,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=0,
            )

        # Game C: never enters endgame (endgame_class=None)
        game_c = await _seed_game(db_session, result="0-1", user_color="white")
        await _seed_game_position(
            db_session,
            game=game_c,
            ply=10,
            piece_count=ENDGAME_PIECE_COUNT_THRESHOLD + 2,
            material_signature="KQRB_KQRB",
            endgame_class=None,
        )

        bucket_rows = await query_endgame_bucket_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        endgame_rows, non_endgame_rows = await query_endgame_performance_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        # Only game_a qualifies; game_b (short) and game_c (no endgame) are both "no endgame".
        assert len(bucket_rows) == len(endgame_rows) == 1
        assert len(non_endgame_rows) == 2
        bucket_game_ids = {r[0] for r in bucket_rows}
        assert bucket_game_ids == {game_a.id}

        # entry_rows (per-class 6-ply HAVING) and bucket_rows now agree — both drop game_b.
        entry_rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        entry_game_ids = {r[0] for r in entry_rows}
        assert entry_game_ids == bucket_game_ids == {game_a.id}

    @pytest.mark.asyncio
    async def test_time_control_filter(self, db_session: AsyncSession) -> None:
        game_blitz = await _seed_game(db_session, time_control_bucket="blitz")
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session,
                game=game_blitz,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
            )
        game_bullet = await _seed_game(db_session, time_control_bucket="bullet")
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session,
                game=game_bullet,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
            )

        rows = await query_endgame_bucket_rows(
            db_session,
            user_id=99999,
            time_control=["blitz"],
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        assert rows[0][0] == game_blitz.id

    @pytest.mark.asyncio
    async def test_binary_endgame_split_uses_6ply_threshold(self, db_session: AsyncSession) -> None:
        """quick-260414-ae4: binary split + bucket + per-class all respect ENDGAME_PLY_THRESHOLD.

        Game A spends exactly ENDGAME_PLY_THRESHOLD plies in KR_KR → qualifies.
        Game B spends ENDGAME_PLY_THRESHOLD - 1 plies in KR_KR → does NOT qualify on
        any endgame-tab analysis (count_endgame_games, performance_rows, bucket_rows).
        """
        game_a = await _seed_game(db_session, result="1-0", user_color="white")
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session,
                game=game_a,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=0,
            )

        game_b = await _seed_game(db_session, result="1/2-1/2", user_color="white")
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD - 1):
            await _seed_game_position(
                db_session,
                game=game_b,
                ply=ply,
                material_signature="KR_KR",
                endgame_class=1,
                material_imbalance=0,
            )

        bucket_rows = await query_endgame_bucket_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        endgame_rows, non_endgame_rows = await query_endgame_performance_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )

        # Game A in bucket + endgame, Game B only in non_endgame.
        assert {r.game_id for r in bucket_rows} == {game_a.id}
        assert len(endgame_rows) == 1
        assert len(non_endgame_rows) == 1
