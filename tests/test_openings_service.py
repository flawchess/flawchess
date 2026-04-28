"""Unit and integration tests for the openings service.

Coverage:
- ANL-03: derive_user_result for all 6 result × color combinations
- recency_cutoff: None passthrough, "all", "week", "year" mappings
- ANL-03: W/D/L stats computed correctly from seeded data
- RES-01, RES-02: GameRecord includes opponent, result, date, time_control, platform_url
- RES-03: matched_count reflects total before pagination
- Zero-match edge case: all-zero stats, empty list, no error
- MEXP-04, MEXP-05, MEXP-10: get_next_moves W/D/L aggregation, sorting, result_fen
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.schemas.openings import OpeningsRequest, NextMovesRequest
from app.services.openings_service import (
    analyze,
    derive_user_result,
    get_next_moves,
    recency_cutoff,
)


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user
    for uid in [1]:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Seed helper (local — avoids coupling to repository test module)
# ---------------------------------------------------------------------------


def _unique_id() -> str:
    return str(uuid.uuid4())


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 1,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    rated: bool = True,
    time_control_bucket: str = "blitz",
    played_at: datetime.datetime | None = None,
    white_username: str = "testuser",
    black_username: str = "opponent",
    platform_url: str | None = "https://www.chess.com/game/live/12345",
    full_hash: int = 11111111,
    white_hash: int = 22222222,
    black_hash: int = 33333333,
) -> Game:
    """Insert one Game + one GamePosition and return the Game."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_id(),
        platform_url=platform_url,
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        white_username=white_username,
        black_username=black_username,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()

    pos = GamePosition(
        game_id=game.id,
        user_id=user_id,
        ply=1,
        full_hash=full_hash,
        white_hash=white_hash,
        black_hash=black_hash,
    )
    session.add(pos)
    await session.flush()

    return game


# ---------------------------------------------------------------------------
# TestDeriveUserResult — ANL-03 support
# ---------------------------------------------------------------------------


class TestDeriveUserResult:
    """Verify derive_user_result for all 6 result × color combinations."""

    def test_white_wins(self) -> None:
        assert derive_user_result("1-0", "white") == "win"

    def test_white_loses(self) -> None:
        assert derive_user_result("0-1", "white") == "loss"

    def test_black_wins(self) -> None:
        assert derive_user_result("0-1", "black") == "win"

    def test_black_loses(self) -> None:
        assert derive_user_result("1-0", "black") == "loss"

    def test_draw_white(self) -> None:
        assert derive_user_result("1/2-1/2", "white") == "draw"

    def test_draw_black(self) -> None:
        assert derive_user_result("1/2-1/2", "black") == "draw"


# ---------------------------------------------------------------------------
# TestRecencyCutoff
# ---------------------------------------------------------------------------


class TestRecencyCutoff:
    """Verify recency_cutoff returns correct datetime offsets."""

    def test_none_returns_none(self) -> None:
        assert recency_cutoff(None) is None

    def test_all_returns_none(self) -> None:
        assert recency_cutoff("all") is None

    def test_week_returns_recent(self) -> None:
        before = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=7)
        result = recency_cutoff("week")
        after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=7)

        assert result is not None
        assert before <= result <= after

    def test_year_returns_past(self) -> None:
        before = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=365)
        result = recency_cutoff("year")
        after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=365)

        assert result is not None
        assert before <= result <= after


# ---------------------------------------------------------------------------
# TestWDLStats — ANL-03
# ---------------------------------------------------------------------------

WDL_HASH = 44444444


class TestWDLStats:
    """Verify W/D/L stats computed correctly via analyze()."""

    @pytest.mark.asyncio
    async def test_wdl_computation(self, db_session: AsyncSession) -> None:
        """1 win + 1 draw + 1 loss yields correct counts and percentages."""
        await _seed_game(db_session, result="1-0", user_color="white", full_hash=WDL_HASH)
        await _seed_game(db_session, result="1/2-1/2", user_color="white", full_hash=WDL_HASH)
        await _seed_game(db_session, result="0-1", user_color="white", full_hash=WDL_HASH)

        request = OpeningsRequest(target_hash=WDL_HASH, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        assert response.stats.wins == 1
        assert response.stats.draws == 1
        assert response.stats.losses == 1
        assert response.stats.total == 3
        assert response.stats.win_pct == pytest.approx(33.3, abs=0.1)
        assert response.stats.draw_pct == pytest.approx(33.3, abs=0.1)
        assert response.stats.loss_pct == pytest.approx(33.3, abs=0.1)

    @pytest.mark.asyncio
    async def test_zero_matches(self, db_session: AsyncSession) -> None:
        """Hash that matches no games returns all-zero stats and empty list."""
        request = OpeningsRequest(target_hash=999999999, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        assert response.stats.wins == 0
        assert response.stats.draws == 0
        assert response.stats.losses == 0
        assert response.stats.total == 0
        assert response.stats.win_pct == 0.0
        assert response.stats.draw_pct == 0.0
        assert response.stats.loss_pct == 0.0
        assert response.games == []
        assert response.matched_count == 0


# ---------------------------------------------------------------------------
# TestGameRecord — RES-01, RES-02
# ---------------------------------------------------------------------------

RECORD_HASH = 55555555


class TestGameRecord:
    """Verify GameRecord contains all required display fields."""

    @pytest.mark.asyncio
    async def test_game_record_fields(self, db_session: AsyncSession) -> None:
        """GameRecord exposes players, result, date, time_control, platform_url."""
        played = datetime.datetime(2024, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        await _seed_game(
            db_session,
            result="1-0",
            user_color="white",
            white_username="testuser",
            black_username="grandmaster_bot",
            played_at=played,
            time_control_bucket="rapid",
            platform="chess.com",
            platform_url="https://www.chess.com/game/live/99999",
            full_hash=RECORD_HASH,
        )

        request = OpeningsRequest(target_hash=RECORD_HASH, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        assert len(response.games) == 1
        rec = response.games[0]

        # User is white, opponent is black
        assert rec.white_username == "testuser"
        assert rec.black_username == "grandmaster_bot"
        assert rec.user_color == "white"
        assert rec.user_result == "win"
        assert rec.played_at == played
        assert rec.time_control_bucket == "rapid"
        assert rec.platform == "chess.com"
        assert rec.platform_url == "https://www.chess.com/game/live/99999"

    @pytest.mark.asyncio
    async def test_platform_url_present(self, db_session: AsyncSession) -> None:
        """RES-02: platform_url is populated on every GameRecord."""
        url = "https://www.chess.com/game/live/77777"
        await _seed_game(db_session, platform_url=url, full_hash=RECORD_HASH)

        request = OpeningsRequest(target_hash=RECORD_HASH, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        for rec in response.games:
            assert rec.platform_url is not None


# ---------------------------------------------------------------------------
# TestPaginationResponse — RES-03
# ---------------------------------------------------------------------------

PAGINATION_HASH = 66666666


class TestPaginationResponse:
    """Verify matched_count reflects total before pagination."""

    @pytest.mark.asyncio
    async def test_matched_count_reflects_total(self, db_session: AsyncSession) -> None:
        """Seed 10 games, request limit=3 — matched_count=10, len(games)=3."""
        for _ in range(10):
            await _seed_game(db_session, full_hash=PAGINATION_HASH)

        request = OpeningsRequest(target_hash=PAGINATION_HASH, match_side="full", limit=3, offset=0)
        response = await analyze(db_session, user_id=1, request=request)

        assert response.matched_count == 10
        assert len(response.games) == 3
        assert response.limit == 3
        assert response.offset == 0


# ---------------------------------------------------------------------------
# _seed_game_with_positions — multi-position seed helper
# ---------------------------------------------------------------------------


async def _seed_game_with_positions(
    session: AsyncSession,
    *,
    user_id: int = 1,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    rated: bool = True,
    time_control_bucket: str = "blitz",
    played_at: datetime.datetime | None = None,
    white_username: str = "testuser",
    black_username: str = "opponent",
    platform_url: str | None = "https://www.chess.com/game/live/12345",
    pgn: str = "1. e4 e5 *",
    positions: list[dict] | None = None,
) -> Game:
    """Insert one Game + multiple GamePosition rows and return the Game."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_id(),
        platform_url=platform_url,
        pgn=pgn,
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        white_username=white_username,
        black_username=black_username,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()

    if positions:
        for pos_data in positions:
            pos = GamePosition(
                game_id=game.id,
                user_id=user_id,
                ply=pos_data["ply"],
                full_hash=pos_data["full_hash"],
                white_hash=pos_data.get("white_hash", 0),
                black_hash=pos_data.get("black_hash", 0),
                move_san=pos_data.get("move_san"),
            )
            session.add(pos)
        await session.flush()

    return game


# ---------------------------------------------------------------------------
# TestGetNextMoves — MEXP-04, MEXP-05, MEXP-10
# ---------------------------------------------------------------------------


class TestGetNextMoves:
    """Verify get_next_moves returns correct NextMovesResponse."""

    @pytest.mark.asyncio
    async def test_basic_next_moves(self, db_session: AsyncSession) -> None:
        """2 games at position, different moves -> 2 move entries with correct W/D/L."""
        SOURCE_HASH = 88888888
        RESULT_HASH_E4 = 88888801
        RESULT_HASH_D4 = 88888802

        # Game 1: user wins as white, plays e4 from source position
        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": RESULT_HASH_E4, "move_san": None},
            ],
        )
        # Game 2: user loses as white, plays d4 from source position
        await _seed_game_with_positions(
            db_session,
            result="0-1",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "d4"},
                {"ply": 1, "full_hash": RESULT_HASH_D4, "move_san": None},
            ],
        )

        request = NextMovesRequest(target_hash=SOURCE_HASH)
        response = await get_next_moves(db_session, user_id=1, request=request)

        assert response.position_stats.total == 2
        assert response.position_stats.wins == 1
        assert response.position_stats.losses == 1
        assert len(response.moves) == 2

        move_map = {m.move_san: m for m in response.moves}
        assert "e4" in move_map
        assert "d4" in move_map
        assert move_map["e4"].game_count == 1
        assert move_map["e4"].wins == 1
        assert move_map["d4"].game_count == 1
        assert move_map["d4"].losses == 1

    @pytest.mark.asyncio
    async def test_result_fen_uses_board_fen(self, db_session: AsyncSession) -> None:
        """result_fen is a piece-placement-only FEN (board_fen, not full fen)."""
        SOURCE_HASH = 77777777
        RESULT_HASH = 77777701

        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            pgn="1. e4 *",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": RESULT_HASH, "move_san": None},
            ],
        )

        request = NextMovesRequest(target_hash=SOURCE_HASH)
        response = await get_next_moves(db_session, user_id=1, request=request)

        assert len(response.moves) == 1
        fen = response.moves[0].result_fen
        # board_fen has no spaces (just piece placement with slashes)
        assert " " not in fen
        assert "/" in fen

    @pytest.mark.asyncio
    async def test_empty_position(self, db_session: AsyncSession) -> None:
        """Position with no games returns zeros and empty moves."""
        request = NextMovesRequest(target_hash=99999999)
        response = await get_next_moves(db_session, user_id=1, request=request)

        assert response.position_stats.total == 0
        assert response.moves == []

    @pytest.mark.asyncio
    async def test_transposition_count_gte_game_count(self, db_session: AsyncSession) -> None:
        """transposition_count >= game_count for every move entry."""
        SOURCE_HASH = 66666601
        RESULT_HASH = 66666611

        # 2 games that both play e4 from source, reaching same result
        for _ in range(2):
            await _seed_game_with_positions(
                db_session,
                result="1-0",
                user_color="white",
                positions=[
                    {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                    {"ply": 1, "full_hash": RESULT_HASH, "move_san": None},
                ],
            )

        request = NextMovesRequest(target_hash=SOURCE_HASH)
        response = await get_next_moves(db_session, user_id=1, request=request)

        for move in response.moves:
            assert move.transposition_count >= move.game_count


# ---------------------------------------------------------------------------
# TestNextMovesSorting — MEXP-04
# ---------------------------------------------------------------------------


class TestNextMovesSorting:
    """Verify sort_by parameter changes move ordering."""

    @pytest.mark.asyncio
    async def test_sort_by_frequency(self, db_session: AsyncSession) -> None:
        """Default sort: moves ordered by game_count descending."""
        SOURCE_HASH = 55555556
        RESULT_A = 55555501
        RESULT_B = 55555502

        # 3 games play "e4", 1 game plays "d4"
        for _ in range(3):
            await _seed_game_with_positions(
                db_session,
                result="1-0",
                user_color="white",
                positions=[
                    {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                    {"ply": 1, "full_hash": RESULT_A, "move_san": None},
                ],
            )
        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "d4"},
                {"ply": 1, "full_hash": RESULT_B, "move_san": None},
            ],
        )

        request = NextMovesRequest(target_hash=SOURCE_HASH, sort_by="frequency")
        response = await get_next_moves(db_session, user_id=1, request=request)

        assert response.moves[0].move_san == "e4"
        assert response.moves[0].game_count == 3

    @pytest.mark.asyncio
    async def test_sort_by_win_rate(self, db_session: AsyncSession) -> None:
        """sort_by=win_rate orders by win_pct descending."""
        SOURCE_HASH = 44444445
        RESULT_A = 44444401
        RESULT_B = 44444402

        # e4: 1 win out of 3 (33.3% win rate)
        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": RESULT_A, "move_san": None},
            ],
        )
        await _seed_game_with_positions(
            db_session,
            result="0-1",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": RESULT_A, "move_san": None},
            ],
        )
        await _seed_game_with_positions(
            db_session,
            result="0-1",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": RESULT_A, "move_san": None},
            ],
        )

        # d4: 1 win out of 1 (100% win rate)
        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "d4"},
                {"ply": 1, "full_hash": RESULT_B, "move_san": None},
            ],
        )

        request = NextMovesRequest(target_hash=SOURCE_HASH, sort_by="win_rate")
        response = await get_next_moves(db_session, user_id=1, request=request)

        # d4 (100% win rate) should come before e4 (33.3%)
        assert response.moves[0].move_san == "d4"
        assert response.moves[0].win_pct == 100.0
        assert response.moves[1].move_san == "e4"


# ---------------------------------------------------------------------------
# TestNextMovesScoreConfidence — Phase 76 D-05/D-13
# ---------------------------------------------------------------------------


class TestNextMovesScoreConfidence:
    """Phase 76 D-05/D-13: each NextMoveEntry carries score, confidence, p_value
    computed via the shared score_confidence.compute_confidence_bucket helper.
    """

    @pytest.mark.asyncio
    async def test_get_next_moves_populates_score_confidence_p_value(
        self, db_session: AsyncSession
    ) -> None:
        """NextMoveEntry.score/confidence/p_value match compute_confidence_bucket output."""
        from app.services.score_confidence import compute_confidence_bucket

        SOURCE_HASH = 33333302
        RESULT_HASH = 33333303

        # Seed 2 wins and 1 loss so we have deterministic W/D/L counts.
        for _ in range(2):
            await _seed_game_with_positions(
                db_session,
                result="1-0",
                user_color="white",
                positions=[
                    {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                    {"ply": 1, "full_hash": RESULT_HASH, "move_san": None},
                ],
            )
        await _seed_game_with_positions(
            db_session,
            result="0-1",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": RESULT_HASH, "move_san": None},
            ],
        )

        request = NextMovesRequest(target_hash=SOURCE_HASH)
        response = await get_next_moves(db_session, user_id=1, request=request)
        assert response.moves, "expected at least one move from seeded games"

        entry = response.moves[0]
        assert 0.0 <= entry.score <= 1.0
        assert entry.confidence in ("low", "medium", "high")
        assert 0.0 <= entry.p_value <= 1.0

        # Cross-check: same value as the helper would return directly for (w, d, l, n).
        expected_confidence, expected_p, _expected_se = compute_confidence_bucket(
            entry.wins, entry.draws, entry.losses, entry.game_count
        )
        expected_score = (entry.wins + 0.5 * entry.draws) / entry.game_count
        assert entry.score == pytest.approx(expected_score, abs=1e-9)
        assert entry.confidence == expected_confidence
        assert entry.p_value == pytest.approx(expected_p, abs=1e-9)
