"""Backend tests for the per-TC flaw-comparison service (Phase 115, Phase 239 plan 02).

Validation architecture:
- test_per_tc_split              : D-02 (one entry per TC, fast to slow, 12 bullets each)
- test_no_analyzed_games         : D-02 (empty tcs, gate echoed)
- test_bullets_and_zone_bounds   : FLAWCMP-01/03 (registry-banded bullets, no domain)
- test_rates_and_pvalue          : UAT (player_rate - opp_rate == delta, p-value)
- test_ci_formula                : FLAWCMP-01 (Wald-z math independent of SQL)
- test_filter_plumbing           : FLAWCMP-03 (filter kwargs narrow the TC list)
- test_severity_filter_zones     : FLAWCMP-03 / D-13 (zones stay with severity filter)
- test_zero_event_bullet         : FLAWCMP-05 / D-11 (zero-event -> delta=None)

The db_session fixture wraps each test in a transaction that is always rolled
back, so seeded users and games never leak into other tests.
"""

import math
import uuid
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.services.flaw_delta_zones import FLAW_DELTA_METRICS, flaw_delta_zone
from app.services.library_service import (
    FLAW_COMPARISON_GATE,
    _compute_mean_ci,
    get_flaw_comparison,
)

# ---------------------------------------------------------------------------
# Seed helpers (mirror tests/test_library_repository.py pattern)
# ---------------------------------------------------------------------------


async def _ensure_user(session: AsyncSession, user_id: int) -> None:
    from sqlalchemy import select

    from app.models.user import User

    existing = (await session.execute(select(User).where(User.id == user_id))).unique()
    if existing.scalar_one_or_none() is None:
        session.add(
            User(id=user_id, email=f"flaw-cmp-test-{user_id}@example.com", hashed_password="x")
        )
        await session.flush()


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int,
    user_color: str = "white",
    ply_count: int = 40,
    platform: str = "lichess",
    time_control_bucket: str | None = "blitz",
    time_control_str: str = "600+0",
) -> Game:
    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color=user_color,
        time_control_str=time_control_str,
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
        ply_count=ply_count,
    )
    session.add(game)
    await session.flush()
    return game


async def _seed_analyzed(session: AsyncSession, *, game: "Game") -> None:  # type: ignore[name-defined]
    """Mark the game analyzed via both gates.

    _analyzed_game_ids_subquery uses the authoritative full_evals_completed_at
    column (quick-task 260617-pu4, replaces per-ply eval-coverage recompute). The
    cheap Game.is_analyzed detector (white_blunders IS NOT NULL) is seeded too, as
    a real Lichess analyzed game satisfies both.
    """
    import datetime

    # Cheap analyzed detector: move-quality counts present (0 = analyzed, no blunders).
    if game.white_blunders is None:
        game.white_blunders = 0

    # Authoritative analyzed gate: full_evals_completed_at IS NOT NULL.
    game.full_evals_completed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    await session.flush()


async def _seed_flaw(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    severity: int = 1,  # 1=mistake
    tempo: int | None = None,
    phase: int = 1,  # 1=middlegame
    is_miss: bool = False,
    is_lucky: bool = False,
    is_reversed: bool = False,
    is_squandered: bool = False,
) -> None:
    from app.repositories.game_flaws_repository import bulk_insert_game_flaws

    await bulk_insert_game_flaws(
        session,
        [
            {
                "user_id": game.user_id,
                "game_id": game.id,
                "ply": ply,
                "severity": severity,
                "tempo": tempo,
                "phase": phase,
                "is_miss": is_miss,
                "is_lucky": is_lucky,
                "is_reversed": is_reversed,
                "is_squandered": is_squandered,
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            }
        ],
    )


_DEFAULT_FILTER_KWARGS: dict[str, Any] = dict(
    time_control=None,
    platform=None,
    rated=None,
    opponent_type="all",
    from_date=None,
    to_date=None,
    flaw_severity=None,
    opponent_gap_min=None,
    opponent_gap_max=None,
    color=None,
)


def _filters(**overrides: Any) -> dict[str, Any]:
    """Default filter kwargs with per-test overrides."""
    return {**_DEFAULT_FILTER_KWARGS, **overrides}


# User ID reserved for flaw comparison tests (no collision with other test modules)
_TEST_USER = 88888


@pytest_asyncio.fixture(autouse=True)
async def _create_test_user(db_session: AsyncSession) -> None:
    await _ensure_user(db_session, _TEST_USER)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_tc_split(db_session: AsyncSession) -> None:
    """25 blitz + 25 rapid analyzed games -> tcs == [blitz, rapid], 12 bullets each (D-02).

    Blitz games carry a player mistake, rapid games do not: pooling the rows would
    blur the two TCs, so the per-TC mistake events must differ.
    """
    for _ in range(25):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="blitz")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, severity=1)  # player mistake
    for _ in range(25):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="rapid")
        await _seed_analyzed(db_session, game=g)

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)

    assert [t.tc for t in result.tcs] == ["blitz", "rapid"]
    for tc_entry in result.tcs:
        assert tc_entry.analyzed_n == 25
        assert tc_entry.below_gate is False
        assert [b.tag for b in tc_entry.bullets] == list(FLAW_DELTA_METRICS)

    blitz_mistake = next(b for b in result.tcs[0].bullets if b.tag == "mistake")
    rapid_mistake = next(b for b in result.tcs[1].bullets if b.tag == "mistake")
    assert blitz_mistake.player_events == 25
    assert rapid_mistake.player_events == 0
    assert blitz_mistake.delta is not None and blitz_mistake.delta > 0
    assert rapid_mistake.delta is None


@pytest.mark.asyncio
async def test_no_analyzed_games(db_session: AsyncSession) -> None:
    """No analyzed games -> tcs == [] and analyzed_gate is the gate constant (D-02)."""
    await _seed_game(db_session, user_id=_TEST_USER)  # not analyzed

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)

    assert result.tcs == []
    assert result.analyzed_gate == FLAW_COMPARISON_GATE


@pytest.mark.asyncio
async def test_bullets_and_zone_bounds(db_session: AsyncSession) -> None:
    """Blitz and rapid hasty bullets carry the rapid band; no bullet has a domain (D-08/D-09)."""
    for bucket in ("blitz", "rapid"):
        for _ in range(FLAW_COMPARISON_GATE):
            g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket=bucket)
            await _seed_analyzed(db_session, game=g)
            await _seed_flaw(db_session, game=g, ply=2, severity=1, tempo=1)  # hasty

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)

    assert [t.tc for t in result.tcs] == ["blitz", "rapid"]
    rapid_band = flaw_delta_zone("hasty", "rapid")
    for tc_entry in result.tcs:
        hasty = next(b for b in tc_entry.bullets if b.tag == "hasty")
        assert hasty.zone_lo == rapid_band.zone_lo
        assert hasty.zone_hi == rapid_band.zone_hi
        assert hasty.has_zone is True
        for bullet in tc_entry.bullets:
            assert "domain" not in type(bullet).model_fields
            band = flaw_delta_zone(bullet.tag, tc_entry.tc)
            assert bullet.zone_lo == band.zone_lo, f"zone_lo mismatch for {bullet.tag}"
            assert bullet.zone_hi == band.zone_hi, f"zone_hi mismatch for {bullet.tag}"


@pytest.mark.asyncio
async def test_rates_and_pvalue(db_session: AsyncSession) -> None:
    """player_rate/opp_rate/p_value populated; player_rate - opp_rate == delta (UAT).

    Seeds 20 analyzed games each with one player mistake (ply=2, white) so the
    mistake bullet has a nonzero, significant positive delta and per-player rates.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # player mistake

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    mistake = next(b for b in result.tcs[0].bullets if b.tag == "mistake")

    # Per-player rates present and consistent with the delta (paired pairing).
    assert mistake.player_rate is not None
    assert mistake.opp_rate is not None
    assert mistake.delta is not None
    assert mistake.player_rate - mistake.opp_rate == pytest.approx(mistake.delta, abs=1e-9)
    # Player committed the only mistakes -> player_rate > opp_rate (== 0).
    assert mistake.player_rate > mistake.opp_rate
    # Identical positive delta across all 20 games -> highly significant.
    assert mistake.p_value is not None
    assert mistake.p_value < 0.05

    # Zero-event bullets keep all the rate fields None.
    low_clock = next(b for b in result.tcs[0].bullets if b.tag == "low_clock")
    assert low_clock.player_rate is None
    assert low_clock.opp_rate is None
    assert low_clock.p_value is None


def test_ci_formula() -> None:
    """_compute_mean_ci: Wald-z CI math verified independently of SQL (FLAWCMP-01).

    Tests:
    - n=0 -> (0, 0, 0)
    - n=1 -> (mean, mean, mean)  [undefined variance]
    - n>=2 -> ci_high - mean == 1.96 * sample_sd / sqrt(n)  within float tolerance
    """
    # n=0 edge case
    mean0, lo0, hi0 = _compute_mean_ci([])
    assert mean0 == 0.0
    assert lo0 == 0.0
    assert hi0 == 0.0

    # n=1 edge case: ci collapses to the single value
    mean1, lo1, hi1 = _compute_mean_ci([3.5])
    assert mean1 == 3.5
    assert lo1 == 3.5
    assert hi1 == 3.5

    # n>=2: verify Wald-z formula explicitly
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    n = len(values)
    expected_mean = sum(values) / n  # 3.0
    sample_var = sum((v - expected_mean) ** 2 for v in values) / (n - 1)  # 2.5
    expected_se = math.sqrt(sample_var / n)
    expected_half = 1.96 * expected_se

    mean_r, lo_r, hi_r = _compute_mean_ci(values)

    assert abs(mean_r - expected_mean) < 1e-10
    assert abs(hi_r - mean_r - expected_half) < 1e-10, (
        f"ci_high - mean should equal 1.96 * se; got {hi_r - mean_r:.6f} vs {expected_half:.6f}"
    )
    assert abs(mean_r - lo_r - expected_half) < 1e-10, (
        f"mean - ci_low should equal 1.96 * se; got {mean_r - lo_r:.6f} vs {expected_half:.6f}"
    )

    # Negative values work correctly
    neg_values = [-2.0, -1.0, 0.0, 1.0]
    mean_n, lo_n, hi_n = _compute_mean_ci(neg_values)
    assert lo_n < mean_n < hi_n


@pytest.mark.asyncio
async def test_filter_plumbing(db_session: AsyncSession) -> None:
    """Filter kwargs narrow the analyzed set and the TC list (FLAWCMP-03, D-02).

    Seeds 20 blitz games on lichess (player mistake each) and 20 rapid games on
    chess.com (no flaws). Unfiltered: two TC entries. time_control=["blitz"]: one.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        g_blitz = await _seed_game(
            db_session,
            user_id=_TEST_USER,
            user_color="white",
            platform="lichess",
            time_control_bucket="blitz",
        )
        await _seed_analyzed(db_session, game=g_blitz)
        await _seed_flaw(db_session, game=g_blitz, ply=2, severity=1)  # player mistake

    for _ in range(FLAW_COMPARISON_GATE):
        g_rapid = await _seed_game(
            db_session,
            user_id=_TEST_USER,
            user_color="white",
            platform="chess.com",
            time_control_bucket="rapid",
        )
        await _seed_analyzed(db_session, game=g_rapid)

    result_all = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    assert [(t.tc, t.analyzed_n) for t in result_all.tcs] == [
        ("blitz", FLAW_COMPARISON_GATE),
        ("rapid", FLAW_COMPARISON_GATE),
    ]

    result_blitz = await get_flaw_comparison(
        db_session,
        _TEST_USER,
        **_filters(time_control=["blitz"]),
    )
    assert [(t.tc, t.analyzed_n) for t in result_blitz.tcs] == [("blitz", FLAW_COMPARISON_GATE)]
    mistake_blitz = next(b for b in result_blitz.tcs[0].bullets if b.tag == "mistake")
    assert mistake_blitz.delta is not None and mistake_blitz.delta > 0


@pytest.mark.asyncio
async def test_severity_filter_zones(db_session: AsyncSession) -> None:
    """flaw_severity=[blunder] keeps all 12 bullets WITH zone bounds (D-13).

    Seeds:
    - 20 games with BOTH player mistake + player blunder -> included under both filters
    - 20 games with player mistake ONLY -> excluded under the blunder-only filter

    The blunder filter narrows the analyzed set, so analyzed_n drops from 40 to 20
    and the blunder delta (blunders only exist in the surviving games) rises.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # mistake
        await _seed_flaw(db_session, game=game, ply=4, severity=2)  # blunder

    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # mistake only

    result_all = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    result_blunder = await get_flaw_comparison(
        db_session,
        _TEST_USER,
        **_filters(flaw_severity=["blunder"]),
    )

    assert result_all.tcs[0].analyzed_n == 2 * FLAW_COMPARISON_GATE
    blunder_tc = result_blunder.tcs[0]
    assert blunder_tc.below_gate is False
    assert blunder_tc.analyzed_n == FLAW_COMPARISON_GATE
    assert len(blunder_tc.bullets) == 12

    for bullet in blunder_tc.bullets:
        band = flaw_delta_zone(bullet.tag, blunder_tc.tc)
        assert bullet.zone_lo == band.zone_lo, f"zone_lo missing on {bullet.tag}"
        assert bullet.zone_hi == band.zone_hi, f"zone_hi missing on {bullet.tag}"

    blunder_all = next(b for b in result_all.tcs[0].bullets if b.tag == "blunder")
    blunder_filtered = next(b for b in blunder_tc.bullets if b.tag == "blunder")
    assert blunder_all.delta is not None and blunder_filtered.delta is not None
    assert blunder_filtered.delta > blunder_all.delta


@pytest.mark.asyncio
async def test_zero_event_bullet(db_session: AsyncSession) -> None:
    """Zero player AND opp events -> delta=None (not 0.0); clean game counts toward analyzed_n.

    Seeds 20 analyzed games with NO game_flaws rows (clean games).
    """
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        # No flaw rows added -> clean game contributes zero-delta anchor row

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)

    tc_entry = result.tcs[0]
    assert tc_entry.below_gate is False
    assert tc_entry.analyzed_n == FLAW_COMPARISON_GATE, (
        f"clean games must count toward analyzed_n; got {tc_entry.analyzed_n}"
    )
    assert len(tc_entry.bullets) == 12

    for bullet in tc_entry.bullets:
        assert bullet.delta is None, (
            f"tag {bullet.tag}: zero-event bullet must have delta=None, not {bullet.delta}"
        )
        assert bullet.ci_low is None, f"tag {bullet.tag}: ci_low should be None for zero-event"
        assert bullet.ci_high is None, f"tag {bullet.tag}: ci_high should be None for zero-event"
        assert bullet.player_events == 0
        assert bullet.opp_events == 0
        band = flaw_delta_zone(bullet.tag, tc_entry.tc)
        assert bullet.zone_lo == band.zone_lo
        assert bullet.zone_hi == band.zone_hi
