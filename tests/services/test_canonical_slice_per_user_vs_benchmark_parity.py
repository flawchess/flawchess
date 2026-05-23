"""SC-7 property gate: per-user canonical-slice value matches benchmark CDF
aggregation for the same user_id (score_gap only).

Phase 94.1 Plan 09 — gap-closure for VERIFICATION.md gap #2.

This test was scaffolded in Plan 02 and stayed `pytest.skip("implementation
pending Plan 03")` through to verification, which left SC-7 unverified at the
runtime level. Plan 09 lifts the skip and asserts numerical agreement for
`metric_id='score_gap'` against a real test DB seed.

Scope narrowing (per Plan 09 Task 2 action step 2 §"If eval-dependent
metrics cannot be seeded with realistic eval_cp values in this scope..."):
  Only `score_gap` is asserted here. Eval-bearing metrics
  (`achievable_score_gap`, `section2_score_gap_conv`,
  `section2_score_gap_parity`) need realistic per-ply Stockfish eval values
  on `game_positions.eval_cp` that exercise the Lichess sigmoid; that
  surface is covered by the real-data integration tests in
  `tests/services/test_user_benchmark_percentiles_service_real_data.py`.

Per RESEARCH §Open Question 2:
  The per-user pooled value is `avg(metric_value)` across
  `(elo_bucket, tc_bucket)` cells (unweighted), matching the benchmark's
  `percentile_cont` treatment of per-(user, cell) rows. Both paths pool
  across TCs with no per-TC cap (D-09).

Benchmark-only tables (`benchmark_selected_users`,
`benchmark_ingest_checkpoints`) are NOT in the canonical Alembic chain
(INFRA-02). They're created on-demand here via
`Base.metadata.create_all(..., tables=[...])` against the test engine —
the same pattern `scripts/import_benchmark_users.py` uses against the
benchmark engine.
"""

from __future__ import annotations

import datetime
import uuid

from typing import cast

import pytest
from sqlalchemy import Table, delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.benchmark_ingest_checkpoint import BenchmarkIngestCheckpoint
from app.models.benchmark_selected_user import BenchmarkSelectedUser
from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.user import User
from app.services.canonical_slice_sql import per_user_cte_for, selected_users_cte

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_SEED_USER_COUNT: int = 5
_MIN_ENDGAME_GAMES_PER_USER: int = 30
_MIN_NON_ENDGAME_GAMES_PER_USER: int = 30
_FLOAT_EPSILON: float = 1e-9
_TEST_ELO: int = 1500
_OPPONENT_ELO_WITHIN_BAND: int = 1550  # within ±100 ELO of _TEST_ELO
_TC_BUCKET: str = "blitz"
_RATING_BUCKET: int = 1200  # bucket the elo_bucket_expr() maps _TEST_ELO into
_ENDGAME_PLY_SPAN_LEN: int = 6  # mirrors ENDGAME_PLY_THRESHOLD
_SPAN_START_PLY: int = 30

pytestmark = pytest.mark.asyncio


async def _ensure_benchmark_tables(test_engine) -> None:
    """Create benchmark_selected_users + benchmark_ingest_checkpoints in test DB.

    INFRA-02: these tables are not in the Alembic chain. The same pattern
    is used by scripts/import_benchmark_users.py:_ensure_checkpoint_table.
    Idempotent (checkfirst=True).
    """
    selected_table = cast(Table, BenchmarkSelectedUser.__table__)
    checkpoint_table = cast(Table, BenchmarkIngestCheckpoint.__table__)
    async with test_engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: selected_table.create(sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: checkpoint_table.create(sync_conn, checkfirst=True))


async def _seed_user_with_canonical_games(
    session_maker,
    *,
    lichess_username: str,
    user_color: str,
    n_endgame: int,
    n_non_endgame: int,
) -> int:
    """Create a User + n_endgame endgame games + n_non_endgame non-endgame games.

    All games pass the canonical slice:
      - rated=True, is_computer_game=False, variant Standard implied
      - opponent rating within ±100 ELO (equal-footing filter)
      - time_control_bucket='blitz' (NON-sparse cell vs (2400, classical))
      - white_rating and black_rating populated
      - played within last 36 months (recency)

    The endgame games have a 6-ply span at ply 30 with endgame_class=1 (rook).
    Returns the new user_id.
    """
    base_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)

    async with session_maker() as session:
        user = User(
            email=f"parity-{uuid.uuid4()}@example.com",
            hashed_password="x",
            lichess_username=lichess_username,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

        # Determine which side the user plays for rating column assignment.
        if user_color == "white":
            white_rating = _TEST_ELO
            black_rating = _OPPONENT_ELO_WITHIN_BAND
        else:
            white_rating = _OPPONENT_ELO_WITHIN_BAND
            black_rating = _TEST_ELO

        # Distribute outcomes so the avg score per group is distinctive and
        # the gap = avg(endgame) - avg(non-endgame) is non-trivial. Endgame
        # games skew toward wins; non-endgame games skew toward losses, so
        # score_gap is positive and varies per user (we vary the seed to
        # differentiate users).
        for idx in range(n_endgame + n_non_endgame):
            has_endgame = idx < n_endgame
            # Outcome distribution: 60% wins, 20% draws, 20% losses for
            # endgame games; 20% wins, 20% draws, 60% losses for non-endgame.
            if has_endgame:
                if idx % 5 < 3:
                    user_won = True
                    is_draw = False
                elif idx % 5 == 3:
                    user_won = False
                    is_draw = True
                else:
                    user_won = False
                    is_draw = False
            else:
                rel = idx - n_endgame
                if rel % 5 < 1:
                    user_won = True
                    is_draw = False
                elif rel % 5 == 1:
                    user_won = False
                    is_draw = True
                else:
                    user_won = False
                    is_draw = False

            if is_draw:
                result = "1/2-1/2"
            elif user_won and user_color == "white":
                result = "1-0"
            elif user_won and user_color == "black":
                result = "0-1"
            elif (not user_won) and user_color == "white":
                result = "0-1"
            else:
                result = "1-0"

            game = Game(
                user_id=user_id,
                platform="lichess",
                platform_game_id=f"parity-{lichess_username}-{idx}",
                pgn="1. e4 e5 *",
                result=result,
                user_color=user_color,
                time_control_str="180+0",
                time_control_bucket=_TC_BUCKET,
                time_control_seconds=180,
                base_time_seconds=180,
                rated=True,
                is_computer_game=False,
                white_username="me" if user_color == "white" else "opp",
                black_username="opp" if user_color == "white" else "me",
                white_rating=white_rating,
                black_rating=black_rating,
            )
            game.played_at = base_dt + datetime.timedelta(minutes=idx)
            session.add(game)
            await session.flush()

            # ply=0 starting position
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
            # Endgame span: 6 plies starting at ply 30, all with endgame_class=1.
            if has_endgame:
                for offset in range(_ENDGAME_PLY_SPAN_LEN):
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
                        )
                    )
        await session.commit()
    return user_id


async def _seed_benchmark_membership(session_maker, *, lichess_username: str) -> None:
    """Register the seeded user in benchmark_selected_users + completed checkpoint."""
    async with session_maker() as session:
        session.add(
            BenchmarkSelectedUser(
                lichess_username=lichess_username,
                rating_bucket=_RATING_BUCKET,
                tc_bucket=_TC_BUCKET,
                median_elo=_TEST_ELO,
                eval_game_count=999,
                dump_month="2026-02",
            )
        )
        session.add(
            BenchmarkIngestCheckpoint(
                lichess_username=lichess_username,
                rating_bucket=_RATING_BUCKET,
                tc_bucket=_TC_BUCKET,
                status="completed",
                games_imported=999,
            )
        )
        await session.commit()


async def test_score_gap_per_user_matches_benchmark_aggregation(test_engine) -> None:
    """SC-7 numerical parity gate for score_gap.

    Setup: seed 5 distinct users with ≥30 endgame + ≥30 non-endgame
    canonical-slice games on `lichess`, blitz TC, ELO 1500 vs an opponent
    within ±100. Register them in `benchmark_selected_users` +
    `benchmark_ingest_checkpoints` (status='completed').

    Run:
      - per_user_cte_for('score_gap', source='benchmark') → captures
        per-user pooled value via aggregation across all seeded users.
      - per_user_cte_for('score_gap', source='single_user') for each
        user_id → captures the single-user pooled value.

    Assert `abs(benchmark[uid] - single_user[uid]) < 1e-9` for each user.

    Note: this is the Plan 03 executor's green-turn contract. The shared
    module must produce numerically identical values for both consumers
    when given the same underlying game set; only the cohort definition
    (single user vs. cohort) differs.
    """
    await _ensure_benchmark_tables(test_engine)

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    seeded_user_ids: list[int] = []
    seeded_usernames: list[str] = []
    try:
        for i in range(_SEED_USER_COUNT):
            uname = f"parity_user_{uuid.uuid4().hex[:8]}_{i}"
            color = "white" if i % 2 == 0 else "black"
            user_id = await _seed_user_with_canonical_games(
                test_session_maker,
                lichess_username=uname,
                user_color=color,
                n_endgame=_MIN_ENDGAME_GAMES_PER_USER + i,  # vary slightly per user
                n_non_endgame=_MIN_NON_ENDGAME_GAMES_PER_USER + (2 * i),
            )
            seeded_user_ids.append(user_id)
            seeded_usernames.append(uname)
            await _seed_benchmark_membership(test_session_maker, lichess_username=uname)

        # The shared CTE block exposes `per_user_values` (with sparse-cell
        # exclusion applied) but the benchmark-source build does NOT carry
        # `user_id` into that final CTE — it's been projected away ready for
        # the cohort-wide percentile_cont aggregation. To aggregate per user
        # for parity, we read directly from the upstream `per_user` CTE
        # (which still has user_id, elo_bucket, tc_bucket, eg_score,
        # non_eg_score) and re-apply the sparse-cell exclusion inline so the
        # filter matches per_user_values's WHERE clause exactly.
        su_benchmark = selected_users_cte(source="benchmark")
        per_user_benchmark = per_user_cte_for("score_gap", source="benchmark", apply_floor=True)
        benchmark_sql = (
            f"WITH {su_benchmark},\n{per_user_benchmark}\n"
            "SELECT user_id, avg(eg_score - non_eg_score)::float AS value\n"
            "FROM per_user\n"
            "WHERE NOT (elo_bucket = 2400 AND tc_bucket = 'classical')\n"
            "GROUP BY user_id"
        )
        async with test_session_maker() as session:
            bm_result = await session.execute(text(benchmark_sql))
            benchmark_by_uid = {row.user_id: row.value for row in bm_result.fetchall()}

        # Single-user path: run per_user_cte_for for each seeded user.
        su_single = selected_users_cte(source="single_user")
        per_user_single = per_user_cte_for("score_gap", source="single_user", apply_floor=True)
        single_sql = (
            f"WITH {su_single},\n{per_user_single}\n"
            "SELECT avg(metric_value)::float AS value\n"
            "FROM per_user_values"
        )
        single_by_uid: dict[int, float | None] = {}
        async with test_session_maker() as session:
            for uid in seeded_user_ids:
                res = await session.execute(text(single_sql).bindparams(user_id=uid))
                row = res.fetchone()
                single_by_uid[uid] = row.value if row is not None else None

        # Numerical agreement, per user.
        for uid in seeded_user_ids:
            bm_val = benchmark_by_uid.get(uid)
            su_val = single_by_uid.get(uid)
            assert bm_val is not None, (
                f"benchmark path produced no value for user_id={uid} — seed "
                f"did not land in the benchmark cohort"
            )
            assert su_val is not None, f"single_user path produced no value for user_id={uid}"
            assert abs(bm_val - su_val) < _FLOAT_EPSILON, (
                f"score_gap parity violation for user_id={uid}: "
                f"benchmark={bm_val!r}, single_user={su_val!r}"
            )

    finally:
        # Cleanup: delete seeded users (CASCADE removes games / positions)
        # and remove benchmark-membership rows.
        async with test_session_maker() as session:
            for uname in seeded_usernames:
                await session.execute(
                    delete(BenchmarkIngestCheckpoint).where(
                        BenchmarkIngestCheckpoint.lichess_username == uname
                    )
                )
                await session.execute(
                    delete(BenchmarkSelectedUser).where(
                        BenchmarkSelectedUser.lichess_username == uname
                    )
                )
            for uid in seeded_user_ids:
                await session.execute(delete(User).where(User.id == uid))
            await session.commit()
