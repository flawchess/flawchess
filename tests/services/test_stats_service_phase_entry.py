"""Service-level integration tests for MG-entry eval + clock-diff fields in
get_most_played_openings (Plan 02, Task 2).

Coverage:
- MG-entry eval fields populated when phase=1 rows exist
- eval_n == 0 when no phase-entry rows have eval
- Clock-diff pct and seconds populated from MG-entry clock data
- Filter consistency: eval_n <= total
- No asyncio.gather in stats_service (CLAUDE.md critical constraint)
- Color-flip symmetry propagates correctly through service
- Outlier trim propagates from repository to response
"""

import datetime
import inspect
import re
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select as _select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.stats_repository import _openings_dedup
from app.services.stats_service import MIN_PLY_WHITE, get_most_played_openings


# ---------------------------------------------------------------------------
# Test user IDs — 700-series to avoid cross-module pollution
# ---------------------------------------------------------------------------

_USER_SS_MG = 701
_USER_SS_EMPTY = 703
_USER_SS_CLOCK = 704
_USER_SS_FILTER = 705
_USER_SS_FLIP = 706
_USER_SS_OUTLIER = 707
_USER_SS_CLOCK_HETERO = 708

_ALL_USER_IDS = [
    _USER_SS_MG,
    _USER_SS_EMPTY,
    _USER_SS_CLOCK,
    _USER_SS_FILTER,
    _USER_SS_FLIP,
    _USER_SS_OUTLIER,
    _USER_SS_CLOCK_HETERO,
]


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure all test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in _ALL_USER_IDS:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _unique_id() -> str:
    return str(uuid.uuid4())


async def _get_white_opening_with_min_ply(
    session: AsyncSession, min_ply: int = 3
) -> tuple[str, str, int] | None:
    """Return (eco, name, full_hash) for a white-defined opening with ply_count >= min_ply."""
    row = (
        await session.execute(
            _select(
                _openings_dedup.c.eco,
                _openings_dedup.c.name,
                _openings_dedup.c.full_hash,
                _openings_dedup.c.ply_count,
            )
            .where(
                _openings_dedup.c.ply_count >= min_ply,
                _openings_dedup.c.ply_count % 2 == 1,
            )
            .order_by(_openings_dedup.c.ply_count, _openings_dedup.c.name)
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    return str(row[0]), str(row[1]), int(row[2])


async def _get_black_opening_with_min_ply(
    session: AsyncSession, min_ply: int = 3
) -> tuple[str, str, int] | None:
    """Return (eco, name, full_hash) for a black-defined opening with ply_count >= min_ply."""
    row = (
        await session.execute(
            _select(
                _openings_dedup.c.eco,
                _openings_dedup.c.name,
                _openings_dedup.c.full_hash,
                _openings_dedup.c.ply_count,
            )
            .where(
                _openings_dedup.c.ply_count >= min_ply,
                _openings_dedup.c.ply_count % 2 == 0,
            )
            .order_by(_openings_dedup.c.ply_count, _openings_dedup.c.name)
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    return str(row[0]), str(row[1]), int(row[2])


async def _seed_game_with_phases(
    session: AsyncSession,
    *,
    user_id: int,
    user_color: str,
    full_hash: int,
    eco: str,
    opening_name: str,
    ply_count: int,
    mg_eval_cp: int | None = None,
    user_clock: float | None = None,
    opp_clock: float | None = None,
    base_time_seconds: int | None = 300,
    time_control_bucket: str = "blitz",
    platform: str = "lichess",
    rated: bool = True,
    played_at: datetime.datetime | None = None,
    result: str = "1-0",
) -> Game:
    """Seed a Game + opening anchor position + MG-entry + opp-clock rows."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_id(),
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="300+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=300,
        base_time_seconds=base_time_seconds,
        rated=rated,
        opening_eco=eco,
        opening_name=opening_name,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()

    # Opening anchor row at the opening's ply_count — ties game to openings_dedup via full_hash
    session.add(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=ply_count,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
            phase=None,
        )
    )

    # MG-entry row (phase=1) — carries eval_cp and user clock
    session.add(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=ply_count + 10,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
            phase=1,
            eval_cp=mg_eval_cp,
            clock_seconds=user_clock,
        )
    )

    # Opponent clock row (ply = MG_ENTRY_PLY + 1)
    if opp_clock is not None:
        session.add(
            GamePosition(
                game_id=game.id,
                user_id=user_id,
                ply=ply_count + 11,
                full_hash=full_hash,
                white_hash=full_hash + 1000,
                black_hash=full_hash + 2000,
                phase=1,
                clock_seconds=opp_clock,
            )
        )

    await session.flush()
    return game


class TestGetMostPlayedOpeningsPhaseEntry:
    """Service-level tests for MG-entry eval + clock-diff fields (Plan 02)."""

    @pytest.mark.asyncio
    async def test_get_most_played_openings_populates_mg_eval_fields(
        self, db_session: AsyncSession
    ) -> None:
        """MG-entry eval fields populated for opening with eval_n_mg > 0."""
        uid = _USER_SS_MG
        opening_info = await _get_white_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if opening_info is None:
            pytest.skip("openings_dedup not seeded")
        eco, opening_name, full_hash = opening_info

        # 12 games with varying MG eval centred around +30 cp (need variance for CI bounds)
        for cp in [20, 25, 25, 28, 30, 30, 30, 32, 35, 35, 38, 42]:
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=full_hash,
                eco=eco,
                opening_name=opening_name,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=cp,
            )
        expected_mean = sum([20, 25, 25, 28, 30, 30, 30, 32, 35, 35, 38, 42]) / 12

        response = await get_most_played_openings(db_session, uid)
        opening = next((o for o in response.white if o.full_hash == str(full_hash)), None)
        assert opening is not None, f"Opening {opening_name} (hash {full_hash}) not in white list"

        assert opening.eval_n == 12
        assert opening.avg_eval_pawns is not None
        assert opening.avg_eval_pawns == pytest.approx(expected_mean / 100.0, rel=0.01)
        assert opening.eval_confidence in ("low", "medium", "high")
        assert opening.eval_p_value is not None
        # With variance in eval, CI bounds should straddle the mean
        assert opening.eval_ci_low_pawns is not None
        assert opening.eval_ci_high_pawns is not None
        assert opening.eval_ci_low_pawns < opening.avg_eval_pawns < opening.eval_ci_high_pawns

    @pytest.mark.asyncio
    async def test_get_most_played_openings_eval_n_zero_when_no_phase_data(
        self, db_session: AsyncSession
    ) -> None:
        """When no phase-entry rows have eval, eval_n == 0 and avg_eval_pawns == None."""
        uid = _USER_SS_EMPTY
        opening_info = await _get_white_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if opening_info is None:
            pytest.skip("openings_dedup not seeded")
        eco, opening_name, full_hash = opening_info

        # Seed games without eval (eval_cp=None)
        for _ in range(3):
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=full_hash,
                eco=eco,
                opening_name=opening_name,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=None,
            )

        response = await get_most_played_openings(db_session, uid)
        opening = next((o for o in response.white if o.full_hash == str(full_hash)), None)
        assert opening is not None

        assert opening.eval_n == 0
        assert opening.avg_eval_pawns is None
        assert opening.eval_confidence == "low"

    @pytest.mark.asyncio
    async def test_get_most_played_openings_clock_diff_pct_signed(
        self, db_session: AsyncSession
    ) -> None:
        """Clock-diff: user 24s ahead on 300s base → avg_clock_diff_seconds=+24, pct≈+8.0."""
        uid = _USER_SS_CLOCK
        opening_info = await _get_white_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if opening_info is None:
            pytest.skip("openings_dedup not seeded")
        eco, opening_name, full_hash = opening_info

        # 5 games: user_clock=204s, opp_clock=180s → diff = +24s; pct = 24/300*100 = 8.0%
        for _ in range(5):
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=full_hash,
                eco=eco,
                opening_name=opening_name,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=50,
                user_clock=204.0,
                opp_clock=180.0,
                base_time_seconds=300,
            )

        response = await get_most_played_openings(db_session, uid)
        opening = next((o for o in response.white if o.full_hash == str(full_hash)), None)
        assert opening is not None

        assert opening.clock_diff_n == 5
        assert opening.avg_clock_diff_seconds == pytest.approx(24.0, rel=0.01)
        assert opening.avg_clock_diff_pct == pytest.approx(8.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_clock_diff_pct_heterogeneous_base_time(
        self, db_session: AsyncSession
    ) -> None:
        """WR-04: avg_clock_diff_pct uses per-game mean, consistent with avg_clock_diff_seconds."""
        uid = _USER_SS_CLOCK_HETERO
        opening_info = await _get_white_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if opening_info is None:
            pytest.skip("openings_dedup not seeded")
        eco, opening_name, full_hash = opening_info

        # 3 bullet games: user behind by 10s, base=180s
        for _ in range(3):
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=full_hash,
                eco=eco,
                opening_name=opening_name,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=50,
                user_clock=100.0,
                opp_clock=110.0,
                base_time_seconds=180,
                time_control_bucket="bullet",
            )

        # 2 blitz games: user ahead by 60s, base=300s
        for _ in range(2):
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=full_hash,
                eco=eco,
                opening_name=opening_name,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=50,
                user_clock=240.0,
                opp_clock=180.0,
                base_time_seconds=300,
                time_control_bucket="blitz",
            )

        response = await get_most_played_openings(db_session, uid)
        opening = next((o for o in response.white if o.full_hash == str(full_hash)), None)
        assert opening is not None
        assert opening.clock_diff_n == 5

        expected_avg_seconds = (3 * (-10.0) + 2 * 60.0) / 5
        assert opening.avg_clock_diff_seconds == pytest.approx(expected_avg_seconds, rel=0.01)

        expected_avg_base = (3 * 180.0 + 2 * 300.0) / 5
        expected_pct = (expected_avg_seconds / expected_avg_base) * 100.0
        assert opening.avg_clock_diff_pct == pytest.approx(expected_pct, rel=0.01)

    @pytest.mark.asyncio
    async def test_filter_threading_eval_n_le_total(self, db_session: AsyncSession) -> None:
        """Filter consistency: eval_n <= total AND clock_diff_n <= total."""
        uid = _USER_SS_FILTER
        opening_info = await _get_white_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if opening_info is None:
            pytest.skip("openings_dedup not seeded")
        eco, opening_name, full_hash = opening_info

        for cp in [30, 60, 90, 120, 150]:
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=full_hash,
                eco=eco,
                opening_name=opening_name,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=cp,
            )

        response = await get_most_played_openings(db_session, uid)
        for opening in response.white + response.black:
            assert opening.eval_n <= opening.total
            assert opening.clock_diff_n <= opening.total

    @pytest.mark.asyncio
    async def test_no_asyncio_gather_in_stats_service(self) -> None:
        """CLAUDE.md critical constraint: no asyncio.gather on the same AsyncSession."""
        import app.services.stats_service as svc

        src = inspect.getsource(svc)
        # Strip comment lines before scanning — avoid false positives in docstrings
        code_only = "\n".join(
            line for line in src.splitlines() if not line.lstrip().startswith("#")
        )
        assert re.search(r"\basyncio\.gather\b", code_only) is None, (
            "asyncio.gather found in stats_service — forbidden per CLAUDE.md "
            "(AsyncSession not safe for concurrent use)"
        )

    @pytest.mark.asyncio
    async def test_color_flip_symmetry_through_service(
        self, db_session: AsyncSession
    ) -> None:
        """Sign convention: same raw eval_cp=+50 → white +0.50, black -0.50 after sign flip."""
        uid = _USER_SS_FLIP

        # White-defined opening for white games
        white_info = await _get_white_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if white_info is None:
            pytest.skip("openings_dedup not seeded")
        eco_w, name_w, hash_w = white_info

        # Black-defined opening for black games (different hash so colors don't collide)
        black_info = await _get_black_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if black_info is None:
            pytest.skip("openings_dedup has no black-defined opening with ply >= 3")
        eco_b, name_b, hash_b = black_info

        # White games: raw eval_cp = +50 → sign = +1 → user_eval = +50
        for _ in range(3):
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=hash_w,
                eco=eco_w,
                opening_name=name_w,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=50,
            )

        # Black games: raw eval_cp = +50 → sign = -1 → user_eval = -50
        for _ in range(3):
            game = Game(
                user_id=uid,
                platform="lichess",
                platform_game_id=_unique_id(),
                pgn="1. e4 e5 *",
                result="1-0",
                user_color="black",
                time_control_str="300+0",
                time_control_bucket="blitz",
                time_control_seconds=300,
                base_time_seconds=300,
                rated=True,
                opening_eco=eco_b,
                opening_name=name_b,
            )
            game.played_at = datetime.datetime.now(tz=datetime.timezone.utc)
            db_session.add(game)
            await db_session.flush()

            db_session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=uid,
                    ply=MIN_PLY_WHITE,
                    full_hash=hash_b,
                    white_hash=hash_b + 1000,
                    black_hash=hash_b + 2000,
                    phase=None,
                )
            )
            db_session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=uid,
                    ply=MIN_PLY_WHITE + 10,
                    full_hash=hash_b,
                    white_hash=hash_b + 1000,
                    black_hash=hash_b + 2000,
                    phase=1,
                    eval_cp=50,
                )
            )
            await db_session.flush()

        response = await get_most_played_openings(db_session, uid)

        # White games: user is white, sign=+1 → positive eval
        opening_w = next((o for o in response.white if o.full_hash == str(hash_w)), None)
        assert opening_w is not None, f"White opening hash {hash_w} not found"
        assert opening_w.avg_eval_pawns == pytest.approx(0.50, rel=0.01)

        # Black games: user is black, sign=-1 → negative eval
        opening_b = next((o for o in response.black if o.full_hash == str(hash_b)), None)
        assert opening_b is not None, f"Black opening hash {hash_b} not found"
        assert opening_b.avg_eval_pawns == pytest.approx(-0.50, rel=0.01)

    @pytest.mark.asyncio
    async def test_outlier_trim_propagates_to_response(self, db_session: AsyncSession) -> None:
        """D-08: outlier eval_cp=+2500 excluded; eval_n=2, avg_eval_pawns=0.75."""
        uid = _USER_SS_OUTLIER
        opening_info = await _get_white_opening_with_min_ply(db_session, MIN_PLY_WHITE)
        if opening_info is None:
            pytest.skip("openings_dedup not seeded")
        eco, opening_name, full_hash = opening_info

        # 3 games: +50, +100 (normal) + 2500 (outlier)
        for cp in [50, 100, 2500]:
            await _seed_game_with_phases(
                db_session,
                user_id=uid,
                user_color="white",
                full_hash=full_hash,
                eco=eco,
                opening_name=opening_name,
                ply_count=MIN_PLY_WHITE,
                mg_eval_cp=cp,
            )

        response = await get_most_played_openings(db_session, uid)
        opening = next((o for o in response.white if o.full_hash == str(full_hash)), None)
        assert opening is not None

        # Only 2 games counted (2500 trimmed)
        assert opening.eval_n == 2
        # Mean of 50+100 = 75 cp = 0.75 pawns
        assert opening.avg_eval_pawns == pytest.approx(0.75, rel=0.01)
