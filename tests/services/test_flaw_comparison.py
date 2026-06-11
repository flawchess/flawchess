"""Backend tests for Phase 115 flaw-comparison endpoint (FLAWCMP-01/03/04/05).

Wave-0 scaffold: test_registry_has_15_metrics is live; stubs filled in Task 3.

Validation architecture per 115-RESEARCH.md §Validation Architecture:
- test_all_15_bullets            : FLAWCMP-01 / FLAWCMP-03 (15 bullets, zone bounds)
- test_ci_formula                : FLAWCMP-01 (Wald-z math independent of SQL)
- test_filter_plumbing           : FLAWCMP-03 (filter kwargs narrow analyzed set)
- test_severity_filter_zones     : FLAWCMP-03 / D-13 (zones stay with severity filter)
- test_combos                    : FLAWCMP-04 (hasty_miss + low_clock_miss present)
- test_sample_gate               : FLAWCMP-05 / D-09 (20-game gate)
- test_zero_event_bullet         : FLAWCMP-05 / D-11 (zero-event -> delta=None)
- test_registry_has_15_metrics   : pure registry integrity (live now)
"""

import math
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.services.flaw_delta_zones import FLAW_DELTA_ZONES
from app.services.library_service import (
    FLAW_COMPARISON_GATE,
    _compute_mean_ci,
    get_flaw_comparison,
)

# ---------------------------------------------------------------------------
# Expected registry order (15 tags, registry order = family order)
# ---------------------------------------------------------------------------

_EXPECTED_TAGS = [
    "flaw_rate",
    "mistake",
    "blunder",
    "low_clock",
    "hasty",
    "unrushed",
    "opening",
    "middlegame",
    "endgame_phase",
    "miss",
    "lucky",
    "reversed",
    "squandered",
    "hasty_miss",
    "low_clock_miss",
]


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
    time_control_bucket: str = "blitz",
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
    """Seed game_positions with evals so the game is considered analyzed (>=90% coverage)."""
    from app.models.game_position import GamePosition

    ply_count = game.ply_count or 40
    # Seed positions for all plies so coverage = 100%
    for ply in range(ply_count):
        pos = GamePosition(
            game_id=game.id,
            user_id=game.user_id,
            ply=ply,
            full_hash=hash(f"{game.id}-{ply}"),
            white_hash=hash(f"w-{game.id}-{ply}"),
            black_hash=hash(f"b-{game.id}-{ply}"),
            eval_cp=10,  # non-null -> coverage = 100%
            eval_mate=None,
            phase=1,
            piece_count=20,
            material_count=1000,
            material_signature="KR_KR",
            material_imbalance=0,
        )
        session.add(pos)
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


_DEFAULT_FILTER_KWARGS: dict = dict(
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

# User ID reserved for flaw comparison tests (no collision with other test modules)
_TEST_USER = 88888


@pytest_asyncio.fixture(autouse=True)
async def _create_test_user(db_session: AsyncSession) -> None:
    await _ensure_user(db_session, _TEST_USER)


# ---------------------------------------------------------------------------
# Live test: registry integrity (Task 1 assertion)
# ---------------------------------------------------------------------------


def test_registry_has_15_metrics() -> None:
    """FLAW_DELTA_ZONES contains exactly 15 metrics in the correct family order."""
    assert len(FLAW_DELTA_ZONES) == 15
    assert list(FLAW_DELTA_ZONES.keys()) == _EXPECTED_TAGS


# ---------------------------------------------------------------------------
# Task 3: Filled test stubs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_15_bullets(db_session: AsyncSession) -> None:
    """Response has exactly 15 bullets in registry order with embedded zone bounds (FLAWCMP-01/03).

    Seeds 20 analyzed games with player mistakes so analyzed_n >= FLAW_COMPARISON_GATE.
    Verifies:
    - below_gate=False
    - exactly 15 bullets in registry order
    - each bullet's zone_lo/zone_hi/domain matches FLAW_DELTA_ZONES
    - analyzed_n == 20
    - analyzed_gate == FLAW_COMPARISON_GATE
    """
    for _ in range(FLAW_COMPARISON_GATE):
        # white player: even ply = white mover = player flaw
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        # ply=2 (even) + user_color=white -> player flaw (is_opponent_expr returns False)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # mistake

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)

    assert result.below_gate is False
    assert result.analyzed_n == FLAW_COMPARISON_GATE
    assert result.analyzed_gate == FLAW_COMPARISON_GATE
    assert len(result.bullets) == 15
    assert [b.tag for b in result.bullets] == _EXPECTED_TAGS

    for bullet in result.bullets:
        spec = FLAW_DELTA_ZONES[bullet.tag]
        assert bullet.zone_lo == spec.zone_lo, f"zone_lo mismatch for {bullet.tag}"
        assert bullet.zone_hi == spec.zone_hi, f"zone_hi mismatch for {bullet.tag}"
        assert bullet.domain == spec.domain, f"domain mismatch for {bullet.tag}"


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
    mistake = next(b for b in result.bullets if b.tag == "mistake")

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

    # Zero-event bullets keep all the new fields None.
    low_clock_miss = next(b for b in result.bullets if b.tag == "low_clock_miss")
    assert low_clock_miss.player_rate is None
    assert low_clock_miss.opp_rate is None
    assert low_clock_miss.p_value is None


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
    """Filter kwargs narrow the analyzed set; zone bounds present in every bullet (FLAWCMP-03).

    Seeds:
    - 20 blitz games on lichess
    - 20 rapid games on chess.com
    Unfiltered: both sets -> 40 analyzed games.
    Filtered by time_control=["blitz"]: only 20 lichess games included, deltas differ.
    Zone bounds are present regardless of filter.
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
        # No flaw on rapid games -> different delta profile

    # Unfiltered: 40 analyzed games
    result_all = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    assert result_all.analyzed_n == 40
    assert result_all.below_gate is False

    # Filtered to blitz only: 20 analyzed games
    result_blitz = await get_flaw_comparison(
        db_session,
        _TEST_USER,
        time_control=["blitz"],
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
    assert result_blitz.analyzed_n == FLAW_COMPARISON_GATE
    assert result_blitz.below_gate is False

    # Zone bounds present in all bullets regardless of filter
    for bullet in result_all.bullets:
        spec = FLAW_DELTA_ZONES[bullet.tag]
        assert bullet.zone_lo == spec.zone_lo
        assert bullet.zone_hi == spec.zone_hi
        assert bullet.domain == spec.domain

    for bullet in result_blitz.bullets:
        spec = FLAW_DELTA_ZONES[bullet.tag]
        assert bullet.zone_lo == spec.zone_lo
        assert bullet.zone_hi == spec.zone_hi

    # Deltas differ between filtered and unfiltered (only blitz games have mistakes)
    mistake_all = next(b for b in result_all.bullets if b.tag == "mistake")
    mistake_blitz = next(b for b in result_blitz.bullets if b.tag == "mistake")
    # blitz-only: 20/20 games with 1 player mistake each -> positive delta
    # all: 20 games with mistake + 20 without -> smaller mean
    assert mistake_blitz.delta is not None and mistake_blitz.delta > 0
    assert mistake_all.delta is not None
    # Blitz-filtered has higher per-game delta than all (rapid games contribute 0-delta rows)
    assert mistake_blitz.delta > mistake_all.delta


@pytest.mark.asyncio
async def test_severity_filter_zones(db_session: AsyncSession) -> None:
    """flaw_severity=[blunder] returns all 15 bullets WITH zone bounds (D-13).

    Zone bounds must be present even when a severity filter narrows the basis.
    The flaw_rate delta differs between filtered and unfiltered because the severity
    filter changes which games are included (games with mistake-only flaws are
    excluded from the blunder-only filtered set).

    Seeds:
    - 20 games with BOTH player mistake + player blunder -> included under both filters
    - 20 games with player mistake ONLY -> excluded under blunder-only filter

    Unfiltered (40 games): flaw_rate delta = mean of (M+B)/user_moves*100 per game
    Blunder-only filter (20 games): only games that have a blunder are in the set;
    the flaw_rate delta is computed over those 20 games only.
    """
    # 20 games with M+B: each has player mistake (ply=2) + player blunder (ply=4)
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # mistake
        await _seed_flaw(db_session, game=game, ply=4, severity=2)  # blunder

    # 20 games with mistake-only (no blunder) -> excluded from blunder-only filter
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # mistake only

    # Unfiltered: 40 analyzed games
    result_all = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    # Blunder-only filter: only 20 games (those with blunders)
    result_blunder = await get_flaw_comparison(
        db_session,
        _TEST_USER,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="all",
        from_date=None,
        to_date=None,
        flaw_severity=["blunder"],
        opponent_gap_min=None,
        opponent_gap_max=None,
        color=None,
    )

    assert result_blunder.below_gate is False
    assert len(result_blunder.bullets) == 15
    # Blunder filter narrows to 20 games
    assert result_blunder.analyzed_n == FLAW_COMPARISON_GATE

    # All 15 bullets have zone bounds populated (D-13)
    for bullet in result_blunder.bullets:
        spec = FLAW_DELTA_ZONES[bullet.tag]
        assert bullet.zone_lo == spec.zone_lo, (
            f"zone_lo missing on {bullet.tag} under severity filter"
        )
        assert bullet.zone_hi == spec.zone_hi, (
            f"zone_hi missing on {bullet.tag} under severity filter"
        )
        assert bullet.domain == spec.domain

    # flaw_rate delta: unfiltered has 20 games with 2 flaws + 20 games with 1 flaw
    # -> mean < blunder-filtered (20 games with 2 flaws each, so higher flaw_rate mean)
    flaw_rate_all = next(b for b in result_all.bullets if b.tag == "flaw_rate")
    flaw_rate_blunder = next(b for b in result_blunder.bullets if b.tag == "flaw_rate")
    assert flaw_rate_all.delta is not None and flaw_rate_blunder.delta is not None
    # 40 games: 20 with 2 flaws + 20 with 1 flaw -> mean = 1.5 flaws/40moves*100 = 3.75
    # 20 games (blunder filter): 20 with 2 flaws -> mean = 2 flaws/40moves*100 = 5.0
    assert flaw_rate_blunder.delta > flaw_rate_all.delta


@pytest.mark.asyncio
async def test_combos(db_session: AsyncSession) -> None:
    """hasty_miss and low_clock_miss bullets present; zero combo events -> delta=None (FLAWCMP-04).

    - Seeds 20 analyzed games.
    - Adds hasty+miss events (tempo=1 + is_miss=True) on some games.
    - Verifies hasty_miss bullet exists with non-null delta.
    - low_clock_miss has no events -> delta=None (D-12 ships with zero-event fallback).
    """
    # _TEMPO_INT["hasty"] = 1, _TEMPO_INT["low-clock"] = 0
    for i in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        if i < 10:
            # Player hasty+miss: even ply (white mover) + user_color=white = player side
            await _seed_flaw(
                db_session,
                game=game,
                ply=2,
                severity=1,
                tempo=1,  # hasty
                is_miss=True,
            )

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)

    # Both combo tags must be in the response
    tags_in_response = [b.tag for b in result.bullets]
    assert "hasty_miss" in tags_in_response
    assert "low_clock_miss" in tags_in_response

    hasty_miss_b = next(b for b in result.bullets if b.tag == "hasty_miss")
    low_clock_miss_b = next(b for b in result.bullets if b.tag == "low_clock_miss")

    # hasty_miss: 10 games with player events -> non-null delta
    assert hasty_miss_b.delta is not None
    assert hasty_miss_b.player_events > 0

    # low_clock_miss: no low-clock+miss events seeded -> zero-event -> delta=None (D-11)
    assert low_clock_miss_b.delta is None
    assert low_clock_miss_b.ci_low is None
    assert low_clock_miss_b.ci_high is None
    assert low_clock_miss_b.player_events == 0
    assert low_clock_miss_b.opp_events == 0


@pytest.mark.asyncio
async def test_sample_gate(db_session: AsyncSession) -> None:
    """analyzed_n < 20 -> below_gate=True, bullets=[]; >= 20 -> 15 bullets (FLAWCMP-05, D-09).

    Seeds 19 analyzed games first, verifies gate fires. Then adds 1 more to reach 20.
    """
    below_threshold = FLAW_COMPARISON_GATE - 1  # 19

    for _ in range(below_threshold):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)

    # Below gate
    result_below = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    assert result_below.below_gate is True
    assert result_below.bullets == []
    assert result_below.analyzed_n == below_threshold
    assert result_below.analyzed_gate == FLAW_COMPARISON_GATE

    # Add one more game to reach exactly 20
    game_20 = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
    await _seed_analyzed(db_session, game=game_20)

    result_above = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    assert result_above.below_gate is False
    assert result_above.analyzed_n == FLAW_COMPARISON_GATE
    assert len(result_above.bullets) == 15


@pytest.mark.asyncio
async def test_zero_event_bullet(db_session: AsyncSession) -> None:
    """Zero player AND opp events -> delta=None (not 0.0); clean game counts toward analyzed_n.

    Seeds 20 analyzed games with NO game_flaws rows (clean games).
    Verifies:
    - analyzed_n == 20 (clean games ARE counted toward analyzed_n)
    - all 15 bullets have delta=None, ci_low=None, ci_high=None (D-11)
    - delta is None, NOT 0.0 (distinguishes "no events" from "exactly typical")
    """
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        # No flaw rows added -> clean game contributes zero-delta anchor row

    result = await get_flaw_comparison(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)

    assert result.below_gate is False
    assert result.analyzed_n == FLAW_COMPARISON_GATE, (
        f"clean games must count toward analyzed_n; got {result.analyzed_n}"
    )
    assert len(result.bullets) == 15

    for bullet in result.bullets:
        assert bullet.delta is None, (
            f"tag {bullet.tag}: zero-event bullet must have delta=None, not {bullet.delta}"
        )
        assert bullet.ci_low is None, f"tag {bullet.tag}: ci_low should be None for zero-event"
        assert bullet.ci_high is None, f"tag {bullet.tag}: ci_high should be None for zero-event"
        assert bullet.player_events == 0
        assert bullet.opp_events == 0
        # Zone bounds must still be populated (D-13 / D-11)
        spec = FLAW_DELTA_ZONES[bullet.tag]
        assert bullet.zone_lo == spec.zone_lo
        assert bullet.zone_hi == spec.zone_hi
        assert bullet.domain == spec.domain
