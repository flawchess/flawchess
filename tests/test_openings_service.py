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
        # score / confidence / CI regression check (quick task 260504-ttq)
        # W=1, D=1, L=1, N=3 → score = (1 + 0.5) / 3 ≈ 0.5
        assert 0.0 <= response.stats.score <= 1.0
        assert response.stats.confidence in {"low", "medium", "high"}
        assert 0.0 <= response.stats.ci_low <= response.stats.score
        assert response.stats.score <= response.stats.ci_high <= 1.0

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
# TestEvalFields — quick task 260508-f9o
# ---------------------------------------------------------------------------


EVAL_HASH = 77777777


async def _seed_game_with_mg_eval(
    session: AsyncSession,
    *,
    user_id: int = 1,
    user_color: str = "white",
    full_hash: int = EVAL_HASH,
    eval_cp: int | None = 30,
    result: str = "1-0",
) -> Game:
    """Seed a Game + opening anchor row + MG-entry (phase=1) row carrying eval_cp."""
    game = Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=_unique_id(),
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        white_username="testuser",
        black_username="opponent",
    )
    game.played_at = datetime.datetime.now(tz=datetime.timezone.utc)
    session.add(game)
    await session.flush()

    # Opening anchor row (phase=None) — feeds query_wdl_counts.
    session.add(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=10,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
            phase=None,
        )
    )
    # MG-entry row (phase=1) carrying eval_cp — feeds the new eval pillar.
    session.add(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=20,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
            phase=1,
            eval_cp=eval_cp,
        )
    )
    await session.flush()
    return game


class TestAnalyzeEvalFields:
    """Quick task 260508-f9o: analyze() populates MG-entry eval fields and
    OpeningsResponse.eval_baseline_pawns from the position's phase=1 rows."""

    @pytest.mark.asyncio
    async def test_eval_fields_populated_when_mg_data_exists(
        self, db_session: AsyncSession
    ) -> None:
        """Position with eval data → response.stats.avg_eval_pawns is not None,
        eval_n > 0, eval_baseline_pawns matches the request's color."""
        # Seed 12 white games with varying MG eval (need variance for CI bounds).
        for cp in [20, 25, 25, 28, 30, 30, 30, 32, 35, 35, 38, 42]:
            await _seed_game_with_mg_eval(
                db_session, full_hash=EVAL_HASH, user_color="white", eval_cp=cp
            )

        request = OpeningsRequest(target_hash=EVAL_HASH, match_side="full", color="white")
        response = await analyze(db_session, user_id=1, request=request)

        assert response.stats.eval_n == 12
        assert response.stats.avg_eval_pawns is not None
        # Mean of eval_cp values is 30.83, in pawns ≈ 0.31.
        assert response.stats.avg_eval_pawns == pytest.approx(0.3083, abs=0.005)
        assert response.stats.eval_ci_low_pawns is not None
        assert response.stats.eval_ci_high_pawns is not None
        assert (
            response.stats.eval_ci_low_pawns
            < response.stats.avg_eval_pawns
            < response.stats.eval_ci_high_pawns
        )
        assert response.stats.eval_confidence in {"low", "medium", "high"}
        # White color → +0.25 baseline (EVAL_BASELINE_PAWNS_WHITE).
        assert response.stats.eval_p_value is not None
        assert response.eval_baseline_pawns == pytest.approx(0.25)

    @pytest.mark.asyncio
    async def test_eval_fields_default_when_no_mg_data(self, db_session: AsyncSession) -> None:
        """Position with no MG-entry eval → eval_n == 0, avg_eval_pawns is None,
        eval_confidence == 'low' (defaults), response still validates."""
        # Seed 3 games with eval_cp=None on the MG-entry row.
        for _ in range(3):
            await _seed_game_with_mg_eval(
                db_session, full_hash=EVAL_HASH + 1, user_color="white", eval_cp=None
            )

        request = OpeningsRequest(target_hash=EVAL_HASH + 1, match_side="full", color="white")
        response = await analyze(db_session, user_id=1, request=request)

        assert response.stats.total == 3  # WDL still computed
        assert response.stats.eval_n == 0
        assert response.stats.avg_eval_pawns is None
        assert response.stats.eval_ci_low_pawns is None
        assert response.stats.eval_ci_high_pawns is None
        assert response.stats.eval_confidence == "low"
        assert response.stats.eval_p_value is None

    @pytest.mark.asyncio
    async def test_eval_fields_when_target_hash_none(self, db_session: AsyncSession) -> None:
        """target_hash=None skips the eval fetch entirely; defaults preserved."""
        request = OpeningsRequest(target_hash=None, match_side="full", color="black")
        response = await analyze(db_session, user_id=1, request=request)

        assert response.stats.eval_n == 0
        assert response.stats.avg_eval_pawns is None
        assert response.stats.eval_confidence == "low"
        # Black color → -0.25 baseline (EVAL_BASELINE_PAWNS_BLACK).
        assert response.eval_baseline_pawns == pytest.approx(-0.25)

    @pytest.mark.asyncio
    async def test_eval_baseline_white_when_color_none(self, db_session: AsyncSession) -> None:
        """color=None falls back to the white baseline (matches stats_service convention)."""
        request = OpeningsRequest(target_hash=EVAL_HASH + 99, match_side="full", color=None)
        response = await analyze(db_session, user_id=1, request=request)

        assert response.eval_baseline_pawns == pytest.approx(0.25)


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

        # position_stats score / confidence / p_value / CI fields (quick task 260504-ttq)
        ps = response.position_stats
        # W=1, D=0, L=1, N=2 → score = 0.5
        assert ps.score == pytest.approx((1 + 0.5 * 0) / 2)
        assert ps.confidence in {"low", "medium", "high"}
        assert 0.0 <= ps.p_value <= 1.0
        assert 0.0 <= ps.ci_low <= ps.score <= ps.ci_high <= 1.0

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
    async def test_position_stats_score_ci(self, db_session: AsyncSession) -> None:
        """W=8, D=0, L=2, N=10: score=0.8, CI brackets 0.8, bounds in [0,1].

        Verifies quick task 260504-ttq: position_stats includes Wald 95% CI.
        """
        SOURCE_HASH = 98765432
        RESULT_HASH = 98765400

        # 8 wins
        for _ in range(8):
            await _seed_game_with_positions(
                db_session,
                result="1-0",
                user_color="white",
                positions=[
                    {"ply": 0, "full_hash": SOURCE_HASH, "move_san": "e4"},
                    {"ply": 1, "full_hash": RESULT_HASH, "move_san": None},
                ],
            )
        # 2 losses
        for _ in range(2):
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

        ps = response.position_stats
        assert ps.total == 10
        assert ps.wins == 8
        assert ps.losses == 2
        assert ps.score == pytest.approx((8 + 0.5 * 0) / 10)
        assert ps.confidence in {"low", "medium", "high"}
        assert 0.0 <= ps.p_value <= 1.0
        # CI must bracket the score and stay within [0, 1]
        assert 0.0 <= ps.ci_low <= ps.score
        assert ps.score <= ps.ci_high <= 1.0

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

        # Phase 80.1: wins+draws+losses is resulting-position N; game_count is
        # move-played N. When no transposition is seeded (as in this fixture),
        # the two are equal, but compute the helper input from pos_n explicitly
        # to document the new contract.
        pos_n = entry.wins + entry.draws + entry.losses
        expected_confidence, expected_p, _expected_se = compute_confidence_bucket(
            entry.wins, entry.draws, entry.losses, pos_n
        )
        expected_score = (entry.wins + 0.5 * entry.draws) / pos_n
        assert entry.score == pytest.approx(expected_score, abs=1e-9)
        assert entry.confidence == expected_confidence
        assert entry.p_value == pytest.approx(expected_p, abs=1e-9)


# ---------------------------------------------------------------------------
# TestNextMovesTranspositionWdl — Phase 80.1 D-01/D-02
# ---------------------------------------------------------------------------


# Hash range reserved for Phase 80.1 Plan 02 transposition fixtures.
# 0xAA** / 0xBB** are reserved by Plan 80.1-01 (TestQueryTranspositionWdl /
# TestQueryResultingPositionWdl). 0xCC** is the per-test isolation namespace
# for Plan 80.1-02 service-level integration tests.
_TWDL_SOURCE_HASH = 0xCC01
_TWDL_OTHER_SOURCE_HASH = 0xCC02
_TWDL_RESULT_HASH = 0xCC03
_TWDL_SO_SOURCE_HASH = 0xCC04
_TWDL_SO_RESULT_HASH = 0xCC05
_TWDL_FP_SOURCE_HASH = 0xCC06
_TWDL_FP_OTHER_SOURCE_HASH = 0xCC07
_TWDL_FP_RESULT_HASH = 0xCC08


class TestNextMovesTranspositionWdl:
    """Phase 80.1 D-01/D-02: Move Explorer rows show resulting-position WDL.

    game_count stays move-played per D-01; wins+draws+losses reflects all
    games visiting result_hash (transposition-inclusive) per D-02.
    """

    @pytest.mark.asyncio
    async def test_wdl_includes_transposition_games(self, db_session: AsyncSession) -> None:
        """Validation case #1 (canonical convergence): a candidate's resulting
        position is reached by both an e4 game (win) and a d4-transposition
        game (loss). The e4 row's game_count = 1 (only the e4 game played e4
        from SOURCE_HASH), but wins + losses = 2 (both games visit the
        resulting position under the same filters).
        """
        # Game A: played e4 from SOURCE_HASH → RESULT_HASH (win).
        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": _TWDL_SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": _TWDL_RESULT_HASH, "move_san": None},
            ],
        )
        # Game B: reaches RESULT_HASH via OTHER_SOURCE_HASH (transposition,
        # loss). Different entry hash, same resulting hash — Game B never
        # appears as a candidate from SOURCE_HASH but contributes to the
        # resulting-position WDL of Game A's e4 row.
        await _seed_game_with_positions(
            db_session,
            result="0-1",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": _TWDL_OTHER_SOURCE_HASH, "move_san": "d4"},
                {"ply": 1, "full_hash": _TWDL_RESULT_HASH, "move_san": None},
            ],
        )

        request = NextMovesRequest(target_hash=_TWDL_SOURCE_HASH)
        response = await get_next_moves(db_session, user_id=1, request=request)

        assert len(response.moves) == 1
        entry = response.moves[0]
        assert entry.move_san == "e4"
        # game_count is move-played (D-01): only Game A played e4 from SOURCE.
        assert entry.game_count == 1
        # W/D/L are resulting-position (D-02): both games visit RESULT_HASH.
        assert entry.wins == 1
        assert entry.draws == 0
        assert entry.losses == 1
        assert entry.wins + entry.draws + entry.losses == 2
        # Score reflects pos N (1 win + 1 loss out of 2 games visiting
        # RESULT_HASH) = 0.5, not 1.0 (the move-played 1-of-1 win rate).
        assert entry.score == pytest.approx(1.0 / 2.0)

    @pytest.mark.asyncio
    async def test_single_order_game_count_equals_wdl_total(self, db_session: AsyncSession) -> None:
        """Validation case #3: when no transposition exists for a candidate,
        game_count == wins+draws+losses (single-order parity invariant).
        """
        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            positions=[
                {"ply": 0, "full_hash": _TWDL_SO_SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": _TWDL_SO_RESULT_HASH, "move_san": None},
            ],
        )

        request = NextMovesRequest(target_hash=_TWDL_SO_SOURCE_HASH)
        response = await get_next_moves(db_session, user_id=1, request=request)

        assert len(response.moves) == 1
        entry = response.moves[0]
        assert entry.game_count == 1
        assert entry.wins + entry.draws + entry.losses == 1
        assert entry.game_count == entry.wins + entry.draws + entry.losses

    @pytest.mark.asyncio
    async def test_transposition_wdl_filter_parity(self, db_session: AsyncSession) -> None:
        """Validation case #2: a filter applied to query_next_moves and
        query_transposition_wdl must drop the same games from BOTH counts
        (filter parity invariant). Threat T-80.1-05 mitigation.

        Setup: Game A (rated=True) plays e4 from SOURCE → RESULT. Game B
        (rated=False) is a transposition reaching the same RESULT via
        OTHER_SOURCE.

        - rated=True filter: Game B excluded from BOTH game_count AND pos
          WDL → entry.game_count == 1 AND wins+draws+losses == 1.
        - rated=None (no rated filter): Game B included in pos WDL but not
          in game_count (it never played e4 from SOURCE) → entry.game_count
          == 1 AND wins+draws+losses == 2.
        """
        # Game A: rated=True, e4 from SOURCE → RESULT (win)
        await _seed_game_with_positions(
            db_session,
            result="1-0",
            user_color="white",
            rated=True,
            positions=[
                {"ply": 0, "full_hash": _TWDL_FP_SOURCE_HASH, "move_san": "e4"},
                {"ply": 1, "full_hash": _TWDL_FP_RESULT_HASH, "move_san": None},
            ],
        )
        # Game B: rated=False, d4 from OTHER_SOURCE → RESULT (loss, transposition)
        await _seed_game_with_positions(
            db_session,
            result="0-1",
            user_color="white",
            rated=False,
            positions=[
                {
                    "ply": 0,
                    "full_hash": _TWDL_FP_OTHER_SOURCE_HASH,
                    "move_san": "d4",
                },
                {"ply": 1, "full_hash": _TWDL_FP_RESULT_HASH, "move_san": None},
            ],
        )

        # rated=True: Game B dropped from BOTH counts.
        request_rated = NextMovesRequest(target_hash=_TWDL_FP_SOURCE_HASH, rated=True)
        response_rated = await get_next_moves(db_session, user_id=1, request=request_rated)
        assert len(response_rated.moves) == 1
        entry_rated = response_rated.moves[0]
        assert entry_rated.game_count == 1
        assert entry_rated.wins + entry_rated.draws + entry_rated.losses == 1, (
            "filter parity violated: rated=True should drop Game B from pos WDL "
            "as well as from game_count"
        )

        # rated=None: Game B included in pos WDL but not game_count.
        request_all = NextMovesRequest(target_hash=_TWDL_FP_SOURCE_HASH, rated=None)
        response_all = await get_next_moves(db_session, user_id=1, request=request_all)
        assert len(response_all.moves) == 1
        entry_all = response_all.moves[0]
        assert entry_all.game_count == 1  # only Game A played e4 from SOURCE
        assert entry_all.wins + entry_all.draws + entry_all.losses == 2, (
            "rated=None should include Game B in pos WDL"
        )
