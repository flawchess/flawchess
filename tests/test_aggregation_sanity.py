"""Aggregation sanity tests (Phase 61).

Encodes the audit gaps identified in the 2026-04-16 session. Each test seeds
the minimum games needed via db_session (transaction rolled back per test),
calls the service function directly, and asserts exact integers.

Coverage:
- TestWDLBlackPerspective: user plays black, WDL flips correctly from white perspective
- TestRollingWindowBoundaries: MIN_GAMES_FOR_TIMELINE cutoff, same-day bucketing
- TestFilterIntersection: platform AND time_control (intersection, not union)
- TestRecencyBoundary: played_at == cutoff is inclusive (>=)
- TestPositionDedup: same hash at multiple plies in one game counts once
- TestEndgameClassTransition: one game crossing two endgame classes counted in both categories
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.endgame_repository import ENDGAME_PLY_THRESHOLD
from app.repositories.query_utils import apply_game_filters
from app.schemas.openings import (
    OpeningsRequest,
    TimeSeriesBookmarkParam,
    TimeSeriesRequest,
)
from app.services.endgame_service import get_endgame_overview
from app.services.openings_service import analyze as openings_analyze
from app.services.openings_service import get_time_series
from app.services.stats_service import get_global_stats

# 700-series IDs (no other test module uses these)
_USER_BLACK = 701
_USER_BOTH_COLORS = 702
_USER_ROLLING = 703
_USER_ROLLING_SAMEDAY = 704
_USER_FILTER = 705
_USER_RECENCY = 706
_USER_DEDUP = 707
_USER_ENDGAME_TRANS = 708
_ALL_IDS = [
    _USER_BLACK,
    _USER_BOTH_COLORS,
    _USER_ROLLING,
    _USER_ROLLING_SAMEDAY,
    _USER_FILTER,
    _USER_RECENCY,
    _USER_DEDUP,
    _USER_ENDGAME_TRANS,
]


@pytest_asyncio.fixture(autouse=True)
async def _create_users(db_session: AsyncSession) -> None:
    from tests.conftest import ensure_test_user

    for uid in _ALL_IDS:
        await ensure_test_user(db_session, uid)


def _uid() -> str:
    return str(uuid.uuid4())


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int,
    result: str,
    user_color: str,
    platform: str = "chess.com",
    time_control_bucket: str = "blitz",
    played_at: datetime.datetime | None = None,
    rated: bool = True,
) -> Game:
    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_uid(),
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        is_computer_game=False,
        white_rating=1500,
        black_rating=1500,
    )
    game.played_at = played_at or datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    session.add(game)
    await session.flush()
    return game


async def _seed_position(
    session: AsyncSession,
    *,
    game_id: int,
    user_id: int,
    ply: int,
    full_hash: int,
    endgame_class: int | None = None,
    material_signature: str | None = None,
    material_imbalance: int | None = None,
) -> GamePosition:
    pos = GamePosition(
        game_id=game_id,
        user_id=user_id,
        ply=ply,
        full_hash=full_hash,
        white_hash=full_hash + 1,
        black_hash=full_hash + 2,
        piece_count=2 if endgame_class else None,
        material_count=1000 if endgame_class else None,
        material_signature=material_signature,
        material_imbalance=material_imbalance,
        endgame_class=endgame_class,
    )
    session.add(pos)
    await session.flush()
    return pos


def _by_category(categories: list, name: str) -> dict | None:
    """Find a WDLByCategory row by its label and return the count fields."""
    for c in categories:
        if c.label == name:
            return {
                "total": c.total,
                "wins": c.wins,
                "draws": c.draws,
                "losses": c.losses,
            }
    return None


# -----------------------------------------------------------------------------
# TestWDLBlackPerspective
# -----------------------------------------------------------------------------


class TestWDLBlackPerspective:
    """User plays black — results must flip from white's perspective."""

    @pytest.mark.asyncio
    async def test_black_win_is_user_win(self, db_session: AsyncSession) -> None:
        await _seed_game(db_session, user_id=_USER_BLACK, result="0-1", user_color="black")
        await db_session.commit()
        resp = await get_global_stats(db_session, user_id=_USER_BLACK, recency=None, platform=None)
        black = _by_category(resp.by_color, "Black")
        assert black == {"total": 1, "wins": 1, "draws": 0, "losses": 0}

    @pytest.mark.asyncio
    async def test_black_loss_is_user_loss(self, db_session: AsyncSession) -> None:
        await _seed_game(db_session, user_id=_USER_BLACK, result="1-0", user_color="black")
        await db_session.commit()
        resp = await get_global_stats(db_session, user_id=_USER_BLACK, recency=None, platform=None)
        black = _by_category(resp.by_color, "Black")
        assert black == {"total": 1, "wins": 0, "draws": 0, "losses": 1}

    @pytest.mark.asyncio
    async def test_mixed_black_portfolio(self, db_session: AsyncSession) -> None:
        """3 black games: user wins, loses, draws → (1, 1, 1)."""
        for result in ("0-1", "1-0", "1/2-1/2"):
            await _seed_game(db_session, user_id=_USER_BLACK, result=result, user_color="black")
        await db_session.commit()
        resp = await get_global_stats(db_session, user_id=_USER_BLACK, recency=None, platform=None)
        black = _by_category(resp.by_color, "Black")
        assert black == {"total": 3, "wins": 1, "draws": 1, "losses": 1}

    @pytest.mark.asyncio
    async def test_mixed_both_colors_does_not_cross_wires(self, db_session: AsyncSession) -> None:
        """Seed 2 white wins + 2 black wins. Ensures the per-color aggregator
        doesn't accidentally report white perspective for black games or vice versa.
        """
        for _ in range(2):
            await _seed_game(
                db_session,
                user_id=_USER_BOTH_COLORS,
                result="1-0",
                user_color="white",
            )
        for _ in range(2):
            await _seed_game(
                db_session,
                user_id=_USER_BOTH_COLORS,
                result="0-1",
                user_color="black",
            )
        await db_session.commit()
        resp = await get_global_stats(
            db_session, user_id=_USER_BOTH_COLORS, recency=None, platform=None
        )
        white = _by_category(resp.by_color, "White")
        black = _by_category(resp.by_color, "Black")
        assert white == {"total": 2, "wins": 2, "draws": 0, "losses": 0}
        assert black == {"total": 2, "wins": 2, "draws": 0, "losses": 0}


# -----------------------------------------------------------------------------
# TestRollingWindowBoundaries
# -----------------------------------------------------------------------------


class TestRollingWindowBoundaries:
    """get_time_series rolling-window edge cases."""

    @pytest.mark.asyncio
    async def test_fewer_games_than_min_games_returns_empty_series(
        self, db_session: AsyncSession
    ) -> None:
        """MIN_GAMES_FOR_TIMELINE=10, so 5 games must produce 0 timeline points."""
        hash_val = 99_701
        base_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        for i in range(5):
            g = await _seed_game(
                db_session,
                user_id=_USER_ROLLING,
                result="1-0",
                user_color="white",
                played_at=base_dt + datetime.timedelta(days=i),
            )
            await _seed_position(
                db_session,
                game_id=g.id,
                user_id=_USER_ROLLING,
                ply=1,
                full_hash=hash_val,
            )
        await db_session.commit()
        req = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(bookmark_id=1, target_hash=hash_val, match_side="full")
            ]
        )
        resp = await get_time_series(db_session, user_id=_USER_ROLLING, request=req)
        assert len(resp.series) == 1
        assert resp.series[0].data == []
        assert resp.series[0].total_games == 5

    @pytest.mark.asyncio
    async def test_exactly_min_games_emits_first_point(self, db_session: AsyncSession) -> None:
        """10 games on 10 distinct days → only the last day's window has game_count>=10."""
        hash_val = 99_702
        base_dt = datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc)
        for i in range(10):
            g = await _seed_game(
                db_session,
                user_id=_USER_ROLLING,
                result="1-0",
                user_color="white",
                played_at=base_dt + datetime.timedelta(days=i),
            )
            await _seed_position(
                db_session,
                game_id=g.id,
                user_id=_USER_ROLLING,
                ply=1,
                full_hash=hash_val,
            )
        await db_session.commit()
        req = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(bookmark_id=2, target_hash=hash_val, match_side="full")
            ]
        )
        resp = await get_time_series(db_session, user_id=_USER_ROLLING, request=req)
        assert len(resp.series[0].data) == 1
        assert resp.series[0].data[0].game_count == 10
        assert resp.series[0].data[0].win_rate == 1.0  # all wins

    @pytest.mark.asyncio
    async def test_same_day_games_collapse_to_one_point(self, db_session: AsyncSession) -> None:
        """12 games on the same calendar day keep only the last game's window per date."""
        hash_val = 99_703
        base_dt = datetime.datetime(2026, 3, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
        for i in range(12):
            g = await _seed_game(
                db_session,
                user_id=_USER_ROLLING_SAMEDAY,
                result="1-0",
                user_color="white",
                played_at=base_dt + datetime.timedelta(minutes=5 * i),
            )
            await _seed_position(
                db_session,
                game_id=g.id,
                user_id=_USER_ROLLING_SAMEDAY,
                ply=1,
                full_hash=hash_val,
            )
        await db_session.commit()
        req = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(bookmark_id=3, target_hash=hash_val, match_side="full")
            ]
        )
        resp = await get_time_series(db_session, user_id=_USER_ROLLING_SAMEDAY, request=req)
        # Single date → single point (the last game's rolling window)
        assert len(resp.series[0].data) == 1
        assert resp.series[0].data[0].game_count == 12


# -----------------------------------------------------------------------------
# TestFilterIntersection
# -----------------------------------------------------------------------------


class TestFilterIntersection:
    """platform AND time_control must intersect (not union)."""

    @pytest.mark.asyncio
    async def test_query_utils_intersects_platform_and_time_control(
        self, db_session: AsyncSession
    ) -> None:
        combos = [
            ("chess.com", "blitz"),
            ("chess.com", "rapid"),
            ("lichess", "blitz"),
            ("lichess", "rapid"),
        ]
        for platform, bucket in combos:
            await _seed_game(
                db_session,
                user_id=_USER_FILTER,
                result="1-0",
                user_color="white",
                platform=platform,
                time_control_bucket=bucket,
            )
        await db_session.commit()

        stmt = select(Game.id).where(Game.user_id == _USER_FILTER)
        stmt = apply_game_filters(
            stmt,
            time_control=["blitz"],
            platform=["chess.com"],
            rated=None,
            opponent_type="human",
            recency_cutoff=None,
        )
        rows = (await db_session.execute(stmt)).scalars().all()
        assert len(rows) == 1, (
            "platform ∩ time_control must intersect; got "
            f"{len(rows)} rows (expected exactly 1 for chess.com+blitz)"
        )


# -----------------------------------------------------------------------------
# TestRecencyBoundary
# -----------------------------------------------------------------------------


class TestRecencyBoundary:
    """apply_game_filters uses >= for recency_cutoff — boundary is inclusive."""

    @pytest.mark.asyncio
    async def test_cutoff_is_inclusive_at_boundary(self, db_session: AsyncSession) -> None:
        cutoff = datetime.datetime(2026, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        await _seed_game(
            db_session,
            user_id=_USER_RECENCY,
            result="1-0",
            user_color="white",
            played_at=cutoff,
        )
        await db_session.commit()
        stmt = apply_game_filters(
            select(Game.id).where(Game.user_id == _USER_RECENCY),
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="human",
            recency_cutoff=cutoff,
        )
        rows = (await db_session.execute(stmt)).scalars().all()
        assert len(rows) == 1, "played_at == recency_cutoff must be inclusive (>=)"

    @pytest.mark.asyncio
    async def test_cutoff_excludes_one_microsecond_earlier(self, db_session: AsyncSession) -> None:
        cutoff = datetime.datetime(2026, 2, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        await _seed_game(
            db_session,
            user_id=_USER_RECENCY,
            result="1-0",
            user_color="white",
            played_at=cutoff - datetime.timedelta(microseconds=1),
        )
        await db_session.commit()
        stmt = apply_game_filters(
            select(Game.id).where(Game.user_id == _USER_RECENCY),
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="human",
            recency_cutoff=cutoff,
        )
        rows = (await db_session.execute(stmt)).scalars().all()
        assert len(rows) == 0, "game played 1µs before cutoff must be excluded"


# -----------------------------------------------------------------------------
# TestPositionDedup
# -----------------------------------------------------------------------------


class TestPositionDedup:
    """Same full_hash at multiple plies within one game: count game once."""

    @pytest.mark.asyncio
    async def test_same_hash_multiple_plies_one_game_counted_once(
        self, db_session: AsyncSession
    ) -> None:
        hash_val = 99_801
        game = await _seed_game(db_session, user_id=_USER_DEDUP, result="1-0", user_color="white")
        for ply in (0, 2, 4):
            await _seed_position(
                db_session,
                game_id=game.id,
                user_id=_USER_DEDUP,
                ply=ply,
                full_hash=hash_val,
            )
        await db_session.commit()

        req = OpeningsRequest(target_hash=hash_val, match_side="full")
        resp = await openings_analyze(db_session, user_id=_USER_DEDUP, request=req)
        assert resp.stats.total == 1, (
            "one game with 3 positions sharing the same hash must count as 1 game, "
            f"got total={resp.stats.total}"
        )
        assert resp.stats.wins == 1
        assert resp.matched_count == 1


# -----------------------------------------------------------------------------
# TestEndgameClassTransition
# -----------------------------------------------------------------------------


class TestEndgameClassTransition:
    """One game with rook span then pawn span: both categories see +1 game."""

    @pytest.mark.asyncio
    async def test_game_with_rook_then_pawn_span_counted_in_both_classes(
        self, db_session: AsyncSession
    ) -> None:
        game = await _seed_game(
            db_session,
            user_id=_USER_ENDGAME_TRANS,
            result="1-0",
            user_color="white",
            time_control_bucket="rapid",
        )
        base_ply = 30
        # Rook span (endgame_class=1)
        for offset in range(ENDGAME_PLY_THRESHOLD):
            await _seed_position(
                db_session,
                game_id=game.id,
                user_id=_USER_ENDGAME_TRANS,
                ply=base_ply + offset,
                full_hash=100_000 + offset,
                endgame_class=1,
                material_signature="KR_KR",
                material_imbalance=0,
            )
        # Pawn span (endgame_class=3)
        for offset in range(ENDGAME_PLY_THRESHOLD):
            await _seed_position(
                db_session,
                game_id=game.id,
                user_id=_USER_ENDGAME_TRANS,
                ply=base_ply + ENDGAME_PLY_THRESHOLD + offset,
                full_hash=200_000 + offset,
                endgame_class=3,
                material_signature="KPP_KP",
                material_imbalance=100,
            )
        await db_session.commit()

        resp = await get_endgame_overview(
            db_session,
            user_id=_USER_ENDGAME_TRANS,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="human",
            recency=None,
        )
        # Distinct-game count (one game, regardless of multi-class)
        assert resp.performance.endgame_wdl.total == 1

        # Per-category breakdown: both rook and pawn see this game
        by_class = {c.endgame_class: c.total for c in resp.stats.categories}
        assert by_class.get("rook") == 1, f"categories={by_class}"
        assert by_class.get("pawn") == 1, f"categories={by_class}"
