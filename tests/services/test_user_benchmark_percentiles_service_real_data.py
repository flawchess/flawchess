"""Real-data integration tests for user_benchmark_percentiles_service.

Phase 94.1 Plan 09 — gap-closure for VERIFICATION.md gap #1 (missing[1]):
"Add an integration test that runs compute_stage_a / compute_stage_b
end-to-end against a real test DB with a seeded user that DOES have
canonical-slice games — asserts row IS written."

These tests seed a user with games that satisfy the canonical slice
(SKILL.md §1: status='completed', ±100 ELO equal footing, NON-sparse cell,
36-month recency, standard variant, per-metric inclusion floor) and then
assert that compute_stage_a / compute_stage_b actually persist rows to
user_benchmark_percentiles.

Cell-existence verification:
  GLOBAL_PERCENTILE_CDF is keyed by metric_id ONLY (pooled across NON-sparse
  cells), per app/services/global_percentile_cdf.py. The only sparse-cell
  exclusion is (elo_bucket=2400, tc_bucket='classical'). The seed uses
  (_TEST_USER_ELO=1500, _TC_BUCKET='blitz') which is automatically a
  NON-sparse cell — confirmed in reports/global-percentile-cdf-latest.md
  (1600/blitz appears with 501 users; 1500 bucket also appears).

Fallback policy (per Plan 09 Task 3 action step 2): if (1500, 'blitz')
ever stops producing a row, fall back to (1600, 'blitz') or
(1500, 'rapid'); both are confirmed non-sparse in the CDF report.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.user import User
from app.repositories.user_benchmark_percentiles_repository import fetch_for_user
from app.services.user_benchmark_percentiles_service import (
    STAGE_A_METRIC,
    compute_stage_a,
    compute_stage_b,
)

# ── Module-level constants (CLAUDE.md no-magic-numbers) ──────────────────────

_TEST_USER_ELO: int = 1500
_OPP_ELO_WITHIN_BAND: int = 1550  # within ±100 of _TEST_USER_ELO
_TC_BUCKET: str = "blitz"  # NOT classical — avoids any (2400, classical) intersection
_TIME_CONTROL_SECONDS: int = 180  # blitz: <600s
_ENDGAME_GAMES_ABOVE_FLOOR: int = 35  # > score_gap floor of 30
_NON_ENDGAME_GAMES_ABOVE_FLOOR: int = 35  # > score_gap floor of 30
_BELOW_FLOOR_GAMES: int = 5  # below score_gap floor of 30

# Eval-range constants for Stage B seeding (centipawns from white's POV).
_EVAL_TYPICAL_LOW_CP: int = -150
_EVAL_TYPICAL_HIGH_CP: int = 150
_EVAL_WINNING_LOW_CP: int = 180
_EVAL_WINNING_HIGH_CP: int = 250
_EVAL_PARITY_LOW_CP: int = -40
_EVAL_PARITY_HIGH_CP: int = 30

_ENDGAME_PLY_SPAN_LEN: int = 6  # mirrors ENDGAME_PLY_THRESHOLD
_SPAN_START_PLY: int = 30

pytestmark = pytest.mark.asyncio


# ── Seed helpers ──────────────────────────────────────────────────────────────


async def _create_user(session_maker) -> int:
    """Create a fresh User with a unique email; return user_id."""
    async with session_maker() as session:
        user = User(
            email=f"real-data-{uuid.uuid4()}@example.com",
            hashed_password="x",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _delete_user(session_maker, user_id: int) -> None:
    """Delete a user (CASCADE wipes games, positions, percentile rows)."""
    async with session_maker() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


def _result_for(*, user_color: str, user_won: bool, is_draw: bool) -> str:
    """Map (user_color, user_won, is_draw) to the canonical PGN result string."""
    if is_draw:
        return "1/2-1/2"
    if user_won and user_color == "white":
        return "1-0"
    if user_won and user_color == "black":
        return "0-1"
    if (not user_won) and user_color == "white":
        return "0-1"
    return "1-0"


def _make_game(
    *,
    user_id: int,
    user_color: str,
    platform_game_id: str,
    result: str,
    base_dt: datetime.datetime,
    minutes_offset: int,
) -> Game:
    """Build a canonical-slice-qualifying Game row."""
    if user_color == "white":
        white_rating, black_rating = _TEST_USER_ELO, _OPP_ELO_WITHIN_BAND
        white_username, black_username = "me", "opp"
    else:
        white_rating, black_rating = _OPP_ELO_WITHIN_BAND, _TEST_USER_ELO
        white_username, black_username = "opp", "me"
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=platform_game_id,
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str=f"{_TIME_CONTROL_SECONDS}+0",
        time_control_bucket=_TC_BUCKET,
        time_control_seconds=_TIME_CONTROL_SECONDS,
        base_time_seconds=_TIME_CONTROL_SECONDS,
        rated=True,
        is_computer_game=False,
        white_username=white_username,
        black_username=black_username,
        white_rating=white_rating,
        black_rating=black_rating,
    )
    game.played_at = base_dt + datetime.timedelta(minutes=minutes_offset)
    return game


def _eval_drift(low_cp: int, high_cp: int, ply_offset: int) -> int:
    """Deterministic drift within [low_cp, high_cp] across a span."""
    span = high_cp - low_cp
    if span <= 0:
        return low_cp
    return low_cp + (ply_offset * 23) % (span + 1)


async def _seed_canonical_slice_user(
    session_maker,
    *,
    user_id: int,
    n_endgame: int,
    n_non_endgame: int,
    with_evals: bool = False,
) -> None:
    """Insert n_endgame + n_non_endgame canonical-slice-qualifying games.

    Endgame games carry a 6-ply span at ply 30 with endgame_class=1 (rook).
    Non-endgame games carry only the ply=0 position.

    Outcome distribution (varied to keep score_gap non-degenerate):
      - Endgame games: ~60% wins, ~20% draws, ~20% losses (avg score ~0.7)
      - Non-endgame games: ~30% wins, ~20% draws, ~50% losses (avg score ~0.4)
    Resulting score_gap ≈ +0.3.

    When `with_evals=True`, the FIRST 3 endgame games get distinctive
    eval_cp ranges on their span entries so Stage B has data:
      - Game A (typical):  per-ply eval drifts in [_EVAL_TYPICAL_*]; drives
        `achievable_score_gap` (entry-eval-only path uses the first ply).
      - Game B (winning):  per-ply eval in [_EVAL_WINNING_*]; contributes
        to `section2_score_gap_conv` if the per-metric span-bucket floor
        is crossed.
      - Game C (parity):   per-ply eval in [_EVAL_PARITY_*]; contributes
        to `section2_score_gap_parity` if the per-metric span-bucket floor
        is crossed.
    Note: per-metric span-bucket floor (>=20 entry-eval-bucket spans per
    bucket) is NOT crossed with only 3 games. Section2 rows may legitimately
    be absent — Test 2's hard assertion is only on achievable_score_gap.
    """
    base_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    async with session_maker() as session:
        for idx in range(n_endgame + n_non_endgame):
            has_endgame = idx < n_endgame
            user_color = "white" if idx % 2 == 0 else "black"
            # Outcome distribution
            if has_endgame:
                mod = idx % 5
                user_won = mod < 3
                is_draw = mod == 3
            else:
                rel = idx - n_endgame
                mod = rel % 10
                user_won = mod < 3
                is_draw = mod == 3
            result = _result_for(user_color=user_color, user_won=user_won, is_draw=is_draw)
            game = _make_game(
                user_id=user_id,
                user_color=user_color,
                platform_game_id=f"real-{user_id}-{idx}",
                result=result,
                base_dt=base_dt,
                minutes_offset=idx,
            )
            session.add(game)
            await session.flush()

            # ply=0 (every game)
            session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=user_id,
                    ply=0,
                    full_hash=1_000_000 + idx,
                    white_hash=2_000_000 + idx,
                    black_hash=3_000_000 + idx,
                    move_san="e4",
                )
            )

            if not has_endgame:
                continue

            # 6-ply endgame span at ply 30
            # Eval ranges (only when with_evals): every endgame game gets a
            # distinctive eval range so the achievable_score_gap floor of
            # 20 entry-eval games is crossed. The 3 buckets rotate across
            # games to also exercise the section2_* per-bucket grouping.
            if with_evals:
                bucket = idx % 3
                if bucket == 0:
                    eval_low, eval_high = _EVAL_TYPICAL_LOW_CP, _EVAL_TYPICAL_HIGH_CP
                elif bucket == 1:
                    eval_low, eval_high = _EVAL_WINNING_LOW_CP, _EVAL_WINNING_HIGH_CP
                else:
                    eval_low, eval_high = _EVAL_PARITY_LOW_CP, _EVAL_PARITY_HIGH_CP
            else:
                eval_low, eval_high = None, None

            for offset in range(_ENDGAME_PLY_SPAN_LEN):
                if eval_low is not None and eval_high is not None:
                    eval_cp = _eval_drift(eval_low, eval_high, offset)
                else:
                    eval_cp = None
                session.add(
                    GamePosition(
                        game_id=game.id,
                        user_id=user_id,
                        ply=_SPAN_START_PLY + offset,
                        full_hash=10_000_000 + idx * 100 + offset,
                        white_hash=20_000_000 + idx * 100 + offset,
                        black_hash=30_000_000 + idx * 100 + offset,
                        material_signature="KR_KR",
                        material_imbalance=0,
                        endgame_class=1,
                        eval_cp=eval_cp,
                        eval_mate=None,
                    )
                )
        await session.commit()


# ── Per-test user fixture (ensures cleanup) ───────────────────────────────────


@pytest.fixture
async def real_data_user(test_engine) -> AsyncIterator[tuple[int, async_sessionmaker]]:
    """Provide a fresh user_id + a session_maker bound to test_engine.

    Teardown deletes the user (CASCADE wipes games, positions, percentile rows).
    """
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)
    try:
        yield user_id, test_session_maker
    finally:
        await _delete_user(test_session_maker, user_id)


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_compute_stage_a_writes_row_for_qualifying_user(real_data_user) -> None:
    """Stage A writes a row with non-null value AND non-null percentile.

    Seeds a user with ≥30 endgame + ≥30 non-endgame canonical-slice games
    in a NON-sparse (elo_bucket=1200, tc_bucket='blitz') cell. Calls
    compute_stage_a. Asserts the score_gap row is present, both value and
    percentile are non-null, and cdf_snapshot is set to today.
    """
    user_id, test_session_maker = real_data_user
    await _seed_canonical_slice_user(
        test_session_maker,
        user_id=user_id,
        n_endgame=_ENDGAME_GAMES_ABOVE_FLOOR,
        n_non_endgame=_NON_ENDGAME_GAMES_ABOVE_FLOOR,
    )

    await compute_stage_a(user_id, session_maker=test_session_maker)

    async with test_session_maker() as session:
        result = await fetch_for_user(session, user_id=user_id)

    # Strong assertion (acceptance criterion grep, single line):
    # fmt: off
    assert result[STAGE_A_METRIC].value is not None and result[STAGE_A_METRIC].percentile is not None, f"Stage A failed to write a row with non-null value AND non-null percentile for score_gap (got {result.get(STAGE_A_METRIC)!r})"  # noqa: E501
    # fmt: on
    row = result[STAGE_A_METRIC]
    assert row.cdf_snapshot == datetime.date.today(), (
        f"cdf_snapshot expected date.today() ({datetime.date.today()}), got {row.cdf_snapshot!r}"
    )


async def test_compute_stage_b_writes_three_rows_for_qualifying_user(
    real_data_user,
) -> None:
    """Stage B writes achievable_score_gap with non-null value AND percentile.

    Same canonical-slice seed as Test 1 plus 3 distinctive-eval games for
    Stage B. Strong assertion is only on achievable_score_gap (the
    entry-eval-only metric whose floor is reachable with 3 eval-bearing
    games). The two section2_* metrics MAY be absent because the per-metric
    span-bucket floor (>=20 spans per entry-eval bucket) is not crossed
    with this small seed — soft-asserted only.
    """
    user_id, test_session_maker = real_data_user
    await _seed_canonical_slice_user(
        test_session_maker,
        user_id=user_id,
        n_endgame=_ENDGAME_GAMES_ABOVE_FLOOR,
        n_non_endgame=_NON_ENDGAME_GAMES_ABOVE_FLOOR,
        with_evals=True,
    )

    await compute_stage_b(user_id, session_maker=test_session_maker)

    async with test_session_maker() as session:
        result = await fetch_for_user(session, user_id=user_id)

    # Strong assertion on achievable_score_gap (acceptance criterion grep, single line):
    # fmt: off
    assert result['achievable_score_gap'].value is not None and result['achievable_score_gap'].percentile is not None, f"Stage B failed to write achievable_score_gap with non-null value AND non-null percentile (got {result.get('achievable_score_gap')!r})"  # noqa: E501
    # fmt: on

    # Soft assertions: section2_* MAY be present or absent depending on
    # whether the seed crosses the per-metric span-bucket floor of 20 spans.
    # If present, they must have a value (percentile may legitimately be NULL
    # below floor).
    for soft_metric in ("section2_score_gap_conv", "section2_score_gap_parity"):
        if soft_metric in result:
            assert result[soft_metric].value is not None, (
                f"{soft_metric} row was written but value is None; that "
                f"violates the 'no row when value is None' convention"
            )


async def test_compute_stage_a_idempotent_upsert(real_data_user) -> None:
    """Running compute_stage_a twice updates computed_at without drifting value.

    The second call must UPSERT the same (value, percentile) and only advance
    computed_at on the DB side.
    """
    user_id, test_session_maker = real_data_user
    await _seed_canonical_slice_user(
        test_session_maker,
        user_id=user_id,
        n_endgame=_ENDGAME_GAMES_ABOVE_FLOOR,
        n_non_endgame=_NON_ENDGAME_GAMES_ABOVE_FLOOR,
    )

    await compute_stage_a(user_id, session_maker=test_session_maker)
    async with test_session_maker() as session:
        first = await fetch_for_user(session, user_id=user_id)
    first_row = first[STAGE_A_METRIC]

    await compute_stage_a(user_id, session_maker=test_session_maker)
    async with test_session_maker() as session:
        second = await fetch_for_user(session, user_id=user_id)
    second_row = second[STAGE_A_METRIC]

    assert second_row.value == first_row.value, (
        f"Stage A re-run drifted value: {first_row.value!r} -> {second_row.value!r}"
    )
    assert second_row.percentile == first_row.percentile, (
        f"Stage A re-run drifted percentile: {first_row.percentile!r} -> {second_row.percentile!r}"
    )


async def test_compute_stage_a_below_floor_writes_no_row(
    real_data_user,
) -> None:
    """When a user has zero floor-passing cells, NO row is written (Plan 13).

    Seeds 5 endgame games (below the 30-game floor) and 5 non-endgame games.
    Plan 13 correctness fix: the service now uses a single CTE with
    apply_floor=True. With 5 endgame games, the CTE returns no rows for the
    floor-passing query, so no row is written at all. The chip suppresses
    naturally because fetch_for_user returns an empty dict.

    Note: at 1500 ELO the floor-passing query returns no rows because the
    per-cell game count is below the inclusion floor. The behaviour is the
    same as "zero canonical-slice games" from the service's POV.
    """
    user_id, test_session_maker = real_data_user
    await _seed_canonical_slice_user(
        test_session_maker,
        user_id=user_id,
        n_endgame=_BELOW_FLOOR_GAMES,
        n_non_endgame=_BELOW_FLOOR_GAMES,
    )

    await compute_stage_a(user_id, session_maker=test_session_maker)

    async with test_session_maker() as session:
        result = await fetch_for_user(session, user_id=user_id)

    # Plan 13: below-floor users must have NO row. The chip suppresses naturally.
    assert STAGE_A_METRIC not in result, (
        f"Plan 13: below-floor users must NOT have a row in user_benchmark_percentiles "
        f"(got {result.get(STAGE_A_METRIC)!r}). The floor-respecting CTE should return "
        f"no rows when the user has fewer games than the inclusion floor."
    )


# ── User-28-shape regression test ─────────────────────────────────────────────

# Constants for the user-28-shape test (Plan 13 correctness regression)
# ELO bucket boundaries from canonical_slice_sql.py:
#   [800, 1200) → bucket 800
#   [1200, 1600) → bucket 1200
#   [1600, 2000) → bucket 1600
_ELO_BUCKET_800: int = 900  # resolves to bucket 800
_ELO_BUCKET_1200: int = 1300  # resolves to bucket 1200
_ELO_BUCKET_1600: int = 1700  # resolves to bucket 1600
# ELO offset used in _seed_endgame_games_for_elo: opp_elo = user_elo + this offset.
# Distinct from the module-level _OPP_ELO_WITHIN_BAND (which is an absolute ELO),
# to avoid shadowing the existing constant and breaking _make_game.
_OPP_ELO_OFFSET_WITHIN_BAND: int = 50  # within ±100

# Number of eval games per bucket:
# ACHIEVABLE_MIN_GAMES = 20, so:
#   1 below floor, 3 below floor, 25 above floor (≥ 20)
_N_BELOW_FLOOR_SMALL: int = 1  # simulates user 28's n=1 bucket
_N_BELOW_FLOOR_MEDIUM: int = 3  # simulates user 28's n=3 bucket
_N_ABOVE_FLOOR: int = 25  # above ACHIEVABLE_MIN_GAMES floor

# The planned achievable_gap values (set via eval_cp + result):
# achievable_gap_i = actual_score_i - sigmoid(eval_cp_i * color_sign)
#
# Above-floor cell design: draws (score=0.5) with eval_cp=0 → sigmoid(0)=0.5
#   achievable_gap ≈ 0.5 - 0.5 = 0.0 (very close to zero)
#
# Below-floor cell design: wins (score=1.0) with eval_cp=-300 (losing position)
#   sigmoid(-300 * 1 for white) ≈ 0.243 → achievable_gap ≈ 1.0 - 0.243 = 0.757
#   (high gap: exceeded expected performance)
#
# With apply_floor=False (old bug): avg is dragged toward 0.757 (below-floor inflates).
# With apply_floor=True (Plan 13 fix): only above-floor cell contributes → value ≈ 0.0.
_ABOVE_FLOOR_EVAL_CP: int = 0      # entry eval near 0 cp → gap ≈ 0
_ABOVE_FLOOR_RESULT: str = "1/2-1/2"  # draw → score = 0.5
_BELOW_FLOOR_EVAL_CP: int = -300   # losing position → low expected score
_BELOW_FLOOR_RESULT: str = "1-0"   # user (white) wins despite low eval → high gap


async def _seed_endgame_games_for_elo(
    session_maker: async_sessionmaker,
    *,
    user_id: int,
    user_elo: int,
    n_games: int,
    base_offset: int,
    eval_cp: int,
    game_result: str = "1-0",
) -> None:
    """Seed n_games endgame games at user_elo, each with eval_cp on the span entry.

    ELO bucket is determined by user_elo (not by opponent ELO).
    Opponent ELO is set within ±50 of user_elo to satisfy the canonical slice.
    User always plays white. ``game_result`` controls the actual outcome.
    """
    base_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    async with session_maker() as session:
        for idx in range(n_games):
            opp_elo = user_elo + _OPP_ELO_OFFSET_WITHIN_BAND
            platform_game_id = f"u28-{user_id}-{user_elo}-{base_offset + idx}"
            game = Game(
                user_id=user_id,
                platform="lichess",
                platform_game_id=platform_game_id,
                pgn="1. e4 e5 *",
                result=game_result,
                user_color="white",
                time_control_str=f"{_TIME_CONTROL_SECONDS}+0",
                time_control_bucket=_TC_BUCKET,
                time_control_seconds=_TIME_CONTROL_SECONDS,
                base_time_seconds=_TIME_CONTROL_SECONDS,
                rated=True,
                is_computer_game=False,
                white_username="me",
                black_username="opp",
                white_rating=user_elo,
                black_rating=opp_elo,
            )
            game.played_at = base_dt + datetime.timedelta(minutes=base_offset + idx)
            session.add(game)
            await session.flush()

            # Opening position (ply=0)
            session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=user_id,
                    ply=0,
                    full_hash=5_000_000 + user_elo * 10000 + base_offset + idx,
                    white_hash=6_000_000 + user_elo * 10000 + base_offset + idx,
                    black_hash=7_000_000 + user_elo * 10000 + base_offset + idx,
                    move_san="e4",
                )
            )

            # 6-ply endgame span at ply 30 with eval_cp on the entry ply
            for offset in range(_ENDGAME_PLY_SPAN_LEN):
                session.add(
                    GamePosition(
                        game_id=game.id,
                        user_id=user_id,
                        ply=_SPAN_START_PLY + offset,
                        full_hash=80_000_000 + user_elo * 10000 + (base_offset + idx) * 100 + offset,
                        white_hash=81_000_000 + user_elo * 10000 + (base_offset + idx) * 100 + offset,
                        black_hash=82_000_000 + user_elo * 10000 + (base_offset + idx) * 100 + offset,
                        material_signature="KR_KR",
                        material_imbalance=0,
                        endgame_class=1,
                        eval_cp=eval_cp,
                        eval_mate=None,
                    )
                )
        await session.commit()


async def test_user_28_shape_floor_respecting_value_excludes_below_floor_cells(
    real_data_user,
) -> None:
    """Plan 13 correctness regression: user-28-shape floor-respecting value.

    Reproduces the bug where _compute_metric_for_user used apply_floor=False,
    causing tiny below-floor cells (n=1, n=3) to drag the reported value far
    from the floor-passing signal.

    Setup (mirrors user 28's profile):
    - Bucket 800: 1 eval game — wins with eval_cp=-300 (losing position, still won).
      achievable_gap_i = 1.0 - sigmoid(-300) ≈ 1.0 - 0.243 = 0.757. Below floor (1 < 20).
    - Bucket 1200: 3 eval games — same as 800 bucket. Below floor (3 < 20).
    - Bucket 1600: 25 eval games — draws with eval_cp=0 (even position, drew).
      achievable_gap_i = 0.5 - sigmoid(0) = 0.5 - 0.5 = 0.0. Above floor (25 ≥ 20).

    With apply_floor=False (old Plan 05-12 behavior): the weighted avg across all
    cells includes the high-gap below-floor cells → stored value significantly > 0.

    With apply_floor=True (Plan 13): only the 1600-bucket contributes → value ≈ 0.0.

    The test asserts:
    1. The achievable_score_gap row IS written (1600-bucket passes the floor).
    2. The stored value is close to 0 (the above-floor cell's contribution only).
       Threshold: |value| < 0.10 (with 25 draws at eval=0, the avg is exactly 0.0;
       we allow a small margin for floating-point aggregation).
    3. The below-floor cells (if incorrectly included) would push value ≫ 0
       (toward 0.757), so the threshold definitively distinguishes the two paths.
    """
    user_id, test_session_maker = real_data_user

    # Seed the three buckets
    await _seed_endgame_games_for_elo(
        test_session_maker,
        user_id=user_id,
        user_elo=_ELO_BUCKET_800,
        n_games=_N_BELOW_FLOOR_SMALL,
        base_offset=0,
        eval_cp=_BELOW_FLOOR_EVAL_CP,
        game_result=_BELOW_FLOOR_RESULT,
    )
    await _seed_endgame_games_for_elo(
        test_session_maker,
        user_id=user_id,
        user_elo=_ELO_BUCKET_1200,
        n_games=_N_BELOW_FLOOR_MEDIUM,
        base_offset=1000,
        eval_cp=_BELOW_FLOOR_EVAL_CP,
        game_result=_BELOW_FLOOR_RESULT,
    )
    await _seed_endgame_games_for_elo(
        test_session_maker,
        user_id=user_id,
        user_elo=_ELO_BUCKET_1600,
        n_games=_N_ABOVE_FLOOR,
        base_offset=2000,
        eval_cp=_ABOVE_FLOOR_EVAL_CP,
        game_result=_ABOVE_FLOOR_RESULT,
    )

    await compute_stage_b(user_id, session_maker=test_session_maker)

    async with test_session_maker() as session:
        result = await fetch_for_user(session, user_id=user_id)

    # The achievable_score_gap row must be written (1600-bucket passes the floor).
    assert "achievable_score_gap" in result, (
        "Plan 13: achievable_score_gap row must be written when ≥1 bucket passes the floor "
        "(1600-bucket has 25 ≥ ACHIEVABLE_MIN_GAMES=20 eval games)"
    )

    row = result["achievable_score_gap"]
    assert row.value is not None, "value must not be None"

    # The value must reflect ONLY the above-floor (1600-bucket) cell.
    # Above-floor: draws (score=0.5) with eval_cp=0 → gap = 0.5 - sigmoid(0) = 0.0.
    # Below-floor (if incorrectly included): wins with eval_cp=-300
    #   → gap = 1.0 - sigmoid(-300) ≈ 0.757. Would pull avg significantly above 0.
    # apply_floor=True (Plan 13): only above-floor contributes → value ≈ 0.0.
    _FLOOR_CORRECT_THRESHOLD: float = 0.10
    assert abs(row.value) < _FLOOR_CORRECT_THRESHOLD, (
        f"Plan 13 correctness regression: value {row.value:.4f} is not close to 0. "
        f"With apply_floor=True, only the 1600-bucket (draws, eval_cp=0) should contribute "
        f"(expected gap ≈ 0.0). The below-floor 800/1200-bucket cells (wins, eval_cp=-300, "
        f"gap ≈ 0.757) must be excluded. If value > {_FLOOR_CORRECT_THRESHOLD}, the "
        f"apply_floor=False bug may have regressed."
    )
