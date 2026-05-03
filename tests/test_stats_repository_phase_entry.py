"""Integration tests for query_opening_phase_entry_metrics_batch in stats repository.

All tests use a real PostgreSQL database through the db_session fixture,
which wraps each test in a rolled-back transaction for isolation.

Coverage (12 tests):
- MG-entry eval aggregation (sum, sumsq, n)
- EG-entry eval aggregation (parallel pillar in single SQL pass)
- Color-flip sign convention at SQL level for MG entry
- Color-flip sign convention at SQL level for EG entry
- Mate-row exclusion from eval mean for both phases
- Outlier trim |eval_cp| >= 2000 enforced in SQL (D-08)
- Partition invariant: eval_n + mate_n + null_eval_n + outlier_n == phase_entry_total
- Clock-diff at MG entry (user_clock - opp_clock, seconds and base_time_sum)
- Filter consistency: eval_n <= wdl.total for both phases
- Clock-diff excludes games with NULL clock_seconds
- Empty hashes guard returns {}
- Recency filter threads identically to WDL
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.stats_repository import (
    query_opening_phase_entry_metrics_batch,
    query_position_wdl_batch,
)


# ---------------------------------------------------------------------------
# Test user IDs — 600-series to avoid cross-module pollution
# ---------------------------------------------------------------------------

_USER_PHASE_ENTRY = 601
_USER_CROSS_ISO = 602  # cross-user isolation test


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [_USER_PHASE_ENTRY, _USER_CROSS_ISO]:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _unique_game_id() -> str:
    return str(uuid.uuid4())


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = _USER_PHASE_ENTRY,
    platform: str = "lichess",
    result: str = "1-0",
    user_color: str = "white",
    time_control_bucket: str | None = "blitz",
    base_time_seconds: int | None = 300,
    played_at: datetime.datetime | None = None,
    rated: bool = True,
) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)
    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_game_id(),
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="300+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=300,
        base_time_seconds=base_time_seconds,
        rated=rated,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()
    return game


OPENING_PLY = 2  # ply at which the opening hash appears (phase=0)
MG_ENTRY_PLY = 10  # ply at which phase=1 (middlegame entry)
EG_ENTRY_PLY = 30  # ply at which phase=2 (endgame entry)
OPP_CLOCK_PLY = MG_ENTRY_PLY + 1  # opponent's clock is at entry_ply+1


async def _make_game_with_phase_entries(
    session: AsyncSession,
    *,
    user_id: int = _USER_PHASE_ENTRY,
    user_color: str = "white",
    full_hash: int = 111_222_333,
    mg_eval_cp: int | None = None,
    mg_eval_mate: int | None = None,
    eg_eval_cp: int | None = None,
    eg_eval_mate: int | None = None,
    user_clock: float | None = None,
    opp_clock: float | None = None,
    base_time_seconds: int | None = 300,
    platform: str = "lichess",
    time_control_bucket: str | None = "blitz",
    played_at: datetime.datetime | None = None,
    result: str = "1-0",
) -> Game:
    """Create one Game + GamePosition rows (opening + MG-entry + EG-entry + opp-clock row).

    - Opening hash row at ply=2, phase=0 (NULL) — anchors the opening lookup.
    - MG-entry row at ply=10, phase=1 — carries eval_cp / eval_mate.
    - EG-entry row at ply=30, phase=2 — carries eg_eval_cp / eg_eval_mate.
    - Opponent clock row at ply=11, phase=1 — carries opp_clock for clock-diff.
    """
    game = await _seed_game(
        session,
        user_id=user_id,
        user_color=user_color,
        base_time_seconds=base_time_seconds,
        platform=platform,
        time_control_bucket=time_control_bucket,
        played_at=played_at,
        result=result,
    )

    # Opening anchor row (phase = NULL, no eval)
    session.add(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=OPENING_PLY,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
            phase=None,
        )
    )

    # MG-entry row
    session.add(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=MG_ENTRY_PLY,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
            phase=1,
            eval_cp=mg_eval_cp,
            eval_mate=mg_eval_mate,
            clock_seconds=user_clock,
        )
    )

    # Opponent clock row (ply = MG_ENTRY_PLY + 1) — needed for clock-diff computation
    if opp_clock is not None:
        session.add(
            GamePosition(
                game_id=game.id,
                user_id=user_id,
                ply=OPP_CLOCK_PLY,
                full_hash=full_hash,
                white_hash=full_hash + 1000,
                black_hash=full_hash + 2000,
                phase=1,
                eval_cp=mg_eval_cp,
                eval_mate=mg_eval_mate,
                clock_seconds=opp_clock,
            )
        )

    # EG-entry row
    session.add(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=EG_ENTRY_PLY,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
            phase=2,
            eval_cp=eg_eval_cp,
            eval_mate=eg_eval_mate,
        )
    )

    await session.flush()
    return game


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestOpeningPhaseEntryMetrics:
    """Tests for query_opening_phase_entry_metrics_batch."""

    @pytest.mark.asyncio
    async def test_mg_entry_eval_aggregation(self, db_session: AsyncSession) -> None:
        """MG-entry: 3 white games with eval_cp +50, +100, +150 → correct sum/sumsq/n."""
        full_hash = 10_001
        for cp in [50, 100, 150]:
            await _make_game_with_phase_entries(
                db_session, full_hash=full_hash, user_color="white", mg_eval_cp=cp
            )

        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash], color="white"
        )

        assert full_hash in result
        m = result[full_hash]
        assert m.eval_n_mg == 3
        assert m.eval_sum_mg == pytest.approx(300.0, rel=1e-9)
        assert m.eval_sumsq_mg == pytest.approx(50**2 + 100**2 + 150**2, rel=1e-9)
        assert m.mate_n_mg == 0
        assert m.null_eval_n_mg == 0
        assert m.outlier_n_mg == 0

    @pytest.mark.asyncio
    async def test_endgame_entry_eval_aggregation(self, db_session: AsyncSession) -> None:
        """Single SQL pass: MG and EG pillars populated together from phase IN (1, 2)."""
        full_hash = 10_002
        for _ in range(3):
            await _make_game_with_phase_entries(
                db_session,
                full_hash=full_hash,
                user_color="white",
                mg_eval_cp=50,
                eg_eval_cp=200,
            )

        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash], color="white"
        )

        assert full_hash in result
        m = result[full_hash]
        # MG pillar
        assert m.eval_n_mg == 3
        assert m.eval_sum_mg == pytest.approx(150.0, rel=1e-9)
        # EG pillar
        assert m.eval_n_eg == 3
        assert m.eval_sum_eg == pytest.approx(600.0, rel=1e-9)
        assert m.eval_sumsq_eg == pytest.approx(3 * 200**2, rel=1e-9)

    @pytest.mark.asyncio
    async def test_mg_entry_color_flip_symmetry(self, db_session: AsyncSession) -> None:
        """MG sign: white game eval_cp=+100 → +100; black game eval_cp=+100 → -100."""
        full_hash_w = 10_003
        full_hash_b = 10_004
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash_w, user_color="white", mg_eval_cp=100
        )
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash_b, user_color="black", mg_eval_cp=100
        )

        white_result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash_w], color="white"
        )
        black_result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash_b], color="black"
        )

        assert white_result[full_hash_w].eval_sum_mg == pytest.approx(100.0, rel=1e-9)
        assert black_result[full_hash_b].eval_sum_mg == pytest.approx(-100.0, rel=1e-9)

    @pytest.mark.asyncio
    async def test_endgame_entry_color_flip_symmetry(self, db_session: AsyncSession) -> None:
        """EG sign: white game eval_cp=+100 → +100; black game eval_cp=+100 → -100."""
        full_hash_w = 10_005
        full_hash_b = 10_006
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash_w, user_color="white", eg_eval_cp=100
        )
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash_b, user_color="black", eg_eval_cp=100
        )

        white_result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash_w], color="white"
        )
        black_result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash_b], color="black"
        )

        assert white_result[full_hash_w].eval_sum_eg == pytest.approx(100.0, rel=1e-9)
        assert black_result[full_hash_b].eval_sum_eg == pytest.approx(-100.0, rel=1e-9)

    @pytest.mark.asyncio
    async def test_mate_excluded_from_eval_both_phases(self, db_session: AsyncSession) -> None:
        """Mate rows (eval_mate IS NOT NULL) excluded from eval mean; counted as mate_n."""
        full_hash = 10_007
        # 2 games with continuous eval, 1 game with mate
        for cp in [50, 100]:
            await _make_game_with_phase_entries(
                db_session, full_hash=full_hash, mg_eval_cp=cp, eg_eval_cp=cp
            )
        # mate game: eval_cp=NULL, eval_mate=3
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash, mg_eval_cp=None, mg_eval_mate=3,
            eg_eval_cp=None, eg_eval_mate=3
        )

        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash]
        )

        assert full_hash in result
        m = result[full_hash]
        # MG pillar
        assert m.eval_n_mg == 2
        assert m.mate_n_mg == 1
        assert m.null_eval_n_mg == 0
        assert m.outlier_n_mg == 0
        # EG pillar
        assert m.eval_n_eg == 2
        assert m.mate_n_eg == 1
        assert m.null_eval_n_eg == 0
        assert m.outlier_n_eg == 0

    @pytest.mark.asyncio
    async def test_outlier_trim(self, db_session: AsyncSession) -> None:
        """D-08: |eval_cp| >= 2000 trimmed from eval mean; counted as outlier_n not null_eval_n."""
        full_hash_mg = 10_008
        full_hash_eg = 10_009
        # MG: two normal + one outlier (2500 cp)
        for cp in [50, 100]:
            await _make_game_with_phase_entries(
                db_session, full_hash=full_hash_mg, user_color="white", mg_eval_cp=cp
            )
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash_mg, user_color="white", mg_eval_cp=2500
        )

        # EG: two normal + one outlier (-2200 cp)
        for cp in [-50, -100]:
            await _make_game_with_phase_entries(
                db_session, full_hash=full_hash_eg, user_color="white", eg_eval_cp=cp
            )
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash_eg, user_color="white", eg_eval_cp=-2200
        )

        mg_result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash_mg], color="white"
        )
        eg_result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash_eg], color="white"
        )

        m_mg = mg_result[full_hash_mg]
        assert m_mg.eval_n_mg == 2
        assert m_mg.eval_sum_mg == pytest.approx(150.0, rel=1e-9)
        assert m_mg.outlier_n_mg == 1
        assert m_mg.null_eval_n_mg == 0
        assert m_mg.mate_n_mg == 0

        m_eg = eg_result[full_hash_eg]
        assert m_eg.eval_n_eg == 2
        assert m_eg.eval_sum_eg == pytest.approx(-150.0, rel=1e-9)
        assert m_eg.outlier_n_eg == 1
        assert m_eg.null_eval_n_eg == 0
        assert m_eg.mate_n_eg == 0

    @pytest.mark.asyncio
    async def test_partition_invariant_phase_entry_total(self, db_session: AsyncSession) -> None:
        """Invariant: eval_n + mate_n + null_eval_n + outlier_n == phase_entry_row_count per phase."""
        full_hash = 10_010
        # MG: 2 normal, 1 mate, 1 null_eval (cp=NULL, mate=NULL), 1 outlier
        await _make_game_with_phase_entries(db_session, full_hash=full_hash, mg_eval_cp=50)
        await _make_game_with_phase_entries(db_session, full_hash=full_hash, mg_eval_cp=100)
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash, mg_eval_cp=None, mg_eval_mate=3
        )
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash, mg_eval_cp=None, mg_eval_mate=None
        )
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash, mg_eval_cp=2500
        )

        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash]
        )

        assert full_hash in result
        m = result[full_hash]
        # 5 MG-entry rows total
        assert m.eval_n_mg + m.mate_n_mg + m.null_eval_n_mg + m.outlier_n_mg == 5
        # EG: 5 rows (eg_eval_cp=None, eg_eval_mate=None from default)
        assert m.eval_n_eg + m.mate_n_eg + m.null_eval_n_eg + m.outlier_n_eg == 5

    @pytest.mark.asyncio
    async def test_mg_entry_clock_diff(self, db_session: AsyncSession) -> None:
        """Clock-diff: user 180s, opp 200s at MG entry → diff=-20, base_time_sum=300."""
        full_hash = 10_011
        await _make_game_with_phase_entries(
            db_session,
            full_hash=full_hash,
            mg_eval_cp=50,
            user_clock=180.0,
            opp_clock=200.0,
            base_time_seconds=300,
        )

        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash]
        )

        assert full_hash in result
        m = result[full_hash]
        assert m.clock_diff_n == 1
        assert m.clock_diff_sum == pytest.approx(-20.0, rel=1e-6)
        assert m.base_time_sum == pytest.approx(300.0, rel=1e-6)

    @pytest.mark.asyncio
    async def test_filter_consistency_wdl_vs_phase_entry(self, db_session: AsyncSession) -> None:
        """eval_n_mg <= wdl.total AND eval_n_eg <= wdl.total for all openings."""
        full_hash = 10_012
        # Seed 5 games with both MG and EG eval
        for cp in [30, 60, 90, 120, 150]:
            await _make_game_with_phase_entries(
                db_session, full_hash=full_hash, mg_eval_cp=cp, eg_eval_cp=cp
            )

        filter_kwargs = dict(
            time_control=["blitz"],
            platform=["lichess"],
            rated=True,
            opponent_type="human",
            recency_cutoff=None,
        )
        wdl_result = await query_position_wdl_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash], **filter_kwargs
        )
        phase_result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash], **filter_kwargs
        )

        assert full_hash in wdl_result
        assert full_hash in phase_result
        m = phase_result[full_hash]
        total = wdl_result[full_hash].total
        assert m.eval_n_mg <= total
        assert m.eval_n_eg <= total
        assert m.clock_diff_n <= total

    @pytest.mark.asyncio
    async def test_clock_diff_excludes_null_clock_games(self, db_session: AsyncSession) -> None:
        """Games with NULL user clock excluded from clock_diff_n; eval still counted."""
        full_hash = 10_013
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash, mg_eval_cp=100,
            user_clock=None, opp_clock=None
        )

        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash]
        )

        assert full_hash in result
        m = result[full_hash]
        assert m.clock_diff_n == 0
        assert m.eval_n_mg == 1  # eval still counted even without clock

    @pytest.mark.asyncio
    async def test_empty_hashes_returns_empty_dict(self, db_session: AsyncSession) -> None:
        """query_opening_phase_entry_metrics_batch([]) returns {} immediately."""
        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, []
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_recency_filter_threading(self, db_session: AsyncSession) -> None:
        """Recency filter excludes pre-cutoff games from eval_n_mg and eval_n_eg."""
        full_hash = 10_014
        old_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=60)
        recent_date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=5)
        cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)

        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash, mg_eval_cp=50, eg_eval_cp=100, played_at=old_date
        )
        await _make_game_with_phase_entries(
            db_session, full_hash=full_hash, mg_eval_cp=80, eg_eval_cp=160, played_at=recent_date
        )

        result = await query_opening_phase_entry_metrics_batch(
            db_session, _USER_PHASE_ENTRY, [full_hash], recency_cutoff=cutoff
        )

        assert full_hash in result
        m = result[full_hash]
        # Only the recent game should be counted
        assert m.eval_n_mg == 1
        assert m.eval_sum_mg == pytest.approx(80.0, rel=1e-9)
        assert m.eval_n_eg == 1
        assert m.eval_sum_eg == pytest.approx(160.0, rel=1e-9)
