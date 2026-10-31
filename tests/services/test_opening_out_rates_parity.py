"""DB-backed edge-case gate for the "out of the opening" worse/better builder (Phase 243).

The seeded user exercises every D-01 / D-02 / D-05 rule through the real shared SQL
(``per_user_cte_opening_out_counts`` / ``per_user_cte_opening_out_rate``): the eval cut
boundaries around the colour baseline, mate scores, the first-middlegame-ply rule, the
early-ending result rule, the canonical slice and the per-colour 30-game floor.

The expected counts come from each spec's ``expected_side`` (the oracle), never from
re-implementing the classification in Python.
"""

from __future__ import annotations

import datetime
from collections.abc import AsyncIterator, Callable
from typing import cast

import pytest
from sqlalchemy import Table, delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.base import Base
from app.models.benchmark_cohort_cdf import BenchmarkCohortCdf
from app.models.benchmark_ingest_checkpoint import BenchmarkIngestCheckpoint
from app.models.benchmark_selected_user import BenchmarkSelectedUser
from app.models.user_benchmark_percentile import UserBenchmarkPercentile
from app.repositories.opening_out_repository import OpeningOutCounts, fetch_opening_out_counts
from app.repositories.user_benchmark_percentiles_repository import fetch_opening_out_rows
from app.schemas.normalization import Color
from app.services.canonical_slice_sql import (
    OPENING_OUT_MIN_GAMES_PER_COLOR,
    per_user_cte_opening_out_rate,
    selected_users_cte,
)
from app.services.global_percentile_cdf import (
    BREAKPOINT_PERCENTILES,
    OPENING_OUT_METRICS,
    CdfTable,
    OpeningOutMetricId,
    interpolate_cohort_percentile,
    round_anchor_to_grid,
)
from app.services.user_benchmark_percentiles_service import (
    STAGE_B_METRIC_FAMILIES,
    compute_anchors_for_user,
    compute_stage_b,
)
from tests.services.opening_out_seed import (
    SEED_TC,
    OpeningSpec,
    create_seed_user,
    delete_users,
    expected_counts,
    main_block_specs,
    out_of_slice_specs,
    seed_opening_specs,
    simple_even_specs,
    with_eval_source,
)

pytestmark = pytest.mark.asyncio

_CYCLES: int = 3
_COLORS: tuple[Color, ...] = ("white", "black")
_ABS_TOL: float = 1e-12


def _main_specs() -> list[OpeningSpec]:
    """Three cycles of both colours' edge-case blocks plus the out-of-slice rows."""
    blocks = [spec for _ in range(_CYCLES) for c in _COLORS for spec in main_block_specs(c)]
    return [*blocks, *out_of_slice_specs()]


@pytest.fixture
async def opening_out_user(
    test_engine,
) -> AsyncIterator[tuple[int, async_sessionmaker, list[OpeningSpec]]]:
    """A seeded user; the user (and by CASCADE every game) is deleted in teardown."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await create_seed_user(session_maker, tag="main")
    specs = _main_specs()
    try:
        await seed_opening_specs(session_maker, user_id, specs, "main")
        yield user_id, session_maker, specs
    finally:
        await delete_users(session_maker, [user_id])


async def _fetch_rate_rows(
    session_maker: async_sessionmaker, user_id: int, metric: OpeningOutMetricId
) -> dict[Color, tuple[float, int]]:
    """Run the floored rate builder for the single_user source; return {colour: (value, n)}."""
    sql = (
        f"WITH {selected_users_cte(source='single_user')},\n"
        f"{per_user_cte_opening_out_rate(SEED_TC, metric=metric, source='single_user')}\n"
        "SELECT user_color, metric_value::float AS value, n_games::int AS n_games\n"
        "FROM per_user_values"
    )
    async with session_maker() as session:
        result = await session.execute(text(sql).bindparams(user_id=user_id))
        return {row.user_color: (row.value, row.n_games) for row in result}


async def test_counts_match_spec_per_color(opening_out_user) -> None:
    """Every edge case lands in the right bucket, per colour, and out-of-slice rows never count."""
    user_id, session_maker, specs = opening_out_user
    async with session_maker() as session:
        counts = await fetch_opening_out_counts(session, user_id=user_id, tc=SEED_TC)
    assert counts == expected_counts(specs)
    # Guard the oracle itself: 11 qualifying games per cycle and colour, 5 worse, 3 better.
    assert counts["white"] == OpeningOutCounts(
        n_games=11 * _CYCLES, worse_n=5 * _CYCLES, better_n=3 * _CYCLES
    )
    assert counts["black"] == counts["white"]


@pytest.mark.parametrize("metric", OPENING_OUT_METRICS)
async def test_rate_builder_matches_counts(opening_out_user, metric: OpeningOutMetricId) -> None:
    """The rate builder's value is exactly count / n, from the same classification body."""
    user_id, session_maker, specs = opening_out_user
    rows = await _fetch_rate_rows(session_maker, user_id, metric)
    for color, counts in expected_counts(specs).items():
        value, n_games = rows[color]
        assert n_games == counts.n_games
        assert value == pytest.approx(counts.count_for(metric) / counts.n_games, abs=_ABS_TOL)


async def test_rate_builder_floor_boundary(test_engine) -> None:
    """30 qualifying games in a colour yield a rate row, 29 do not; the counts builder has no floor."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await create_seed_user(session_maker, tag="floor")
    specs = [
        *simple_even_specs("white", OPENING_OUT_MIN_GAMES_PER_COLOR),
        *simple_even_specs("black", OPENING_OUT_MIN_GAMES_PER_COLOR - 1),
    ]
    try:
        await seed_opening_specs(session_maker, user_id, specs, "floor")
        rows = await _fetch_rate_rows(session_maker, user_id, "opening_worse_rate")
        async with session_maker() as session:
            counts = await fetch_opening_out_counts(session, user_id=user_id, tc=SEED_TC)
    finally:
        await delete_users(session_maker, [user_id])
    assert set(rows) == {"white"}
    assert rows["white"] == (0.0, OPENING_OUT_MIN_GAMES_PER_COLOR)
    assert counts["white"].n_games == OPENING_OUT_MIN_GAMES_PER_COLOR
    assert counts["black"].n_games == OPENING_OUT_MIN_GAMES_PER_COLOR - 1


_EVAL_SOURCES: dict[str, Callable[[list[OpeningSpec]], list[OpeningSpec]]] = {
    "lichess": lambda specs: with_eval_source(
        specs, lichess_evals_at=True, evals_completed_at=True
    ),
    "local_full": lambda specs: with_eval_source(
        specs, full_evals_completed_at=True, evals_completed_at=True
    ),
    "entry_lane": lambda specs: with_eval_source(specs, evals_completed_at=True),
}


async def test_eval_source_flags_do_not_change_classification(test_engine) -> None:
    """Identical games with different eval-source completion flags classify identically.

    Report-only on the real-data side (plan 02 measures the per-source rate gap); here
    the code path is pinned: the builder reads eval_cp / eval_mate and never an
    eval-source column.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    base_specs = [spec for c in _COLORS for spec in main_block_specs(c)]
    user_ids: list[int] = []
    results: dict[str, dict[Color, OpeningOutCounts]] = {}
    try:
        for source, apply_flags in _EVAL_SOURCES.items():
            user_id = await create_seed_user(session_maker, tag=f"src-{source}")
            user_ids.append(user_id)
            await seed_opening_specs(session_maker, user_id, apply_flags(base_specs), source)
            async with session_maker() as session:
                results[source] = await fetch_opening_out_counts(
                    session, user_id=user_id, tc=SEED_TC
                )
    finally:
        await delete_users(session_maker, user_ids)
    expected = expected_counts(base_specs)
    for source, counts in results.items():
        assert counts == expected, f"eval-source flags changed the classification for {source}"


# ── Stage B per-colour rows (plan 03) ────────────────────────────────────────

_SYNTHETIC_SNAPSHOT_MONTH: str = "2026-10"
_SYNTHETIC_N_USERS: int = 200
# Per-metric breakpoint scale: breakpoint p = p / 100 * scale, so the seeded rates
# (worse 5/11, better 3/11) land strictly inside the CDF and differ between metrics.
_CDF_SCALE: dict[OpeningOutMetricId, float] = {
    "opening_worse_rate": 0.9,
    "opening_better_rate": 0.5,
}


def _synthetic_breakpoints(metric: OpeningOutMetricId) -> tuple[float, ...]:
    return tuple(p / 100.0 * _CDF_SCALE[metric] for p in BREAKPOINT_PERCENTILES)


def _synthetic_table(metric: OpeningOutMetricId) -> CdfTable:
    return CdfTable(breakpoints=_synthetic_breakpoints(metric), n_users=_SYNTHETIC_N_USERS)


async def _insert_synthetic_cells(session_maker: async_sessionmaker, anchor: int) -> None:
    """Insert one monotone 99-row CDF cell per opening metric at (anchor, SEED_TC)."""
    async with session_maker() as session:
        # The cells are keyed by the PK; clear any pre-existing cell so the insert is deterministic.
        await _delete_synthetic_cells(session, anchor)
        session.add_all(
            [
                BenchmarkCohortCdf(
                    metric=metric,
                    anchor_elo=anchor,
                    tc=SEED_TC,
                    percentile=int(pct),
                    value=value,
                    n_users=_SYNTHETIC_N_USERS,
                    snapshot_month=_SYNTHETIC_SNAPSHOT_MONTH,
                )
                for metric in OPENING_OUT_METRICS
                for pct, value in zip(BREAKPOINT_PERCENTILES, _synthetic_breakpoints(metric))
            ]
        )
        await session.commit()


async def _delete_synthetic_cells(session, anchor: int) -> None:
    await session.execute(
        delete(BenchmarkCohortCdf).where(
            BenchmarkCohortCdf.metric.in_(OPENING_OUT_METRICS),
            BenchmarkCohortCdf.anchor_elo == anchor,
            BenchmarkCohortCdf.tc == SEED_TC,
        )
    )


async def _remove_synthetic_cells(session_maker: async_sessionmaker, anchor: int) -> None:
    async with session_maker() as session:
        await _delete_synthetic_cells(session, anchor)
        await session.commit()


async def _persist_anchor(session_maker: async_sessionmaker, user_id: int) -> int:
    """Compute and persist the seeded user's blended anchors; return the blitz grid anchor."""
    async with session_maker() as session:
        anchors = await compute_anchors_for_user(session, user_id)
        await session.commit()
    return round_anchor_to_grid(anchors[SEED_TC].anchor_rating)


async def test_stage_b_writes_color_rows(opening_out_user) -> None:
    """Stage B persists 2 metrics x 2 colours for blitz, ranked against one colour-pooled cell."""
    user_id, session_maker, specs = opening_out_user
    anchor = await _persist_anchor(session_maker, user_id)
    await _insert_synthetic_cells(session_maker, anchor)
    try:
        await compute_stage_b(user_id, session_maker=session_maker)
        async with session_maker() as session:
            rows = await fetch_opening_out_rows(session, user_id=user_id)
            all_color_opening = (
                (
                    await session.execute(
                        select(UserBenchmarkPercentile.metric).where(
                            UserBenchmarkPercentile.user_id == user_id,
                            UserBenchmarkPercentile.metric.in_(OPENING_OUT_METRICS),
                            UserBenchmarkPercentile.color == "all",
                        )
                    )
                )
                .scalars()
                .all()
            )
    finally:
        await _remove_synthetic_cells(session_maker, anchor)

    assert set(rows) == {(m, SEED_TC, c) for m in OPENING_OUT_METRICS for c in _COLORS}
    assert all_color_opening == []
    expected = expected_counts(specs)
    for (metric, _tc, color), row in rows.items():
        counts = expected[color]
        assert row.n_games == counts.n_games
        assert row.value == counts.count_for(metric) / counts.n_games
        assert row.percentile == interpolate_cohort_percentile(row.value, _synthetic_table(metric))
        assert row.percentile is not None and 0.0 < row.percentile < 100.0
    # Both colours read the same cell: the mirrored seed gives equal values, so equal percentiles.
    for metric in OPENING_OUT_METRICS:
        assert rows[(metric, SEED_TC, "white")].value == rows[(metric, SEED_TC, "black")].value
        assert (
            rows[(metric, SEED_TC, "white")].percentile
            == rows[(metric, SEED_TC, "black")].percentile
        )


async def test_stage_b_skips_color_below_floor(test_engine) -> None:
    """A colour with 29 qualifying games gets no opening row; the other colour still does."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await create_seed_user(session_maker, tag="stage-b-floor")
    specs = [
        *simple_even_specs("white", OPENING_OUT_MIN_GAMES_PER_COLOR),
        *simple_even_specs("black", OPENING_OUT_MIN_GAMES_PER_COLOR - 1),
    ]
    anchor: int | None = None
    try:
        await seed_opening_specs(session_maker, user_id, specs, "stage-b-floor")
        anchor = await _persist_anchor(session_maker, user_id)
        await _insert_synthetic_cells(session_maker, anchor)
        await compute_stage_b(user_id, session_maker=session_maker)
        async with session_maker() as session:
            rows = await fetch_opening_out_rows(session, user_id=user_id)
    finally:
        if anchor is not None:
            await _remove_synthetic_cells(session_maker, anchor)
        await delete_users(session_maker, [user_id])
    assert set(rows) == {(m, SEED_TC, "white") for m in OPENING_OUT_METRICS}
    assert all(r.n_games == OPENING_OUT_MIN_GAMES_PER_COLOR for r in rows.values())


async def test_stage_b_endgame_families_unchanged() -> None:
    """The opening ids never join the 10 Endgames families (Endgames parity pins them)."""
    assert len(STAGE_B_METRIC_FAMILIES) == 10
    assert not set(STAGE_B_METRIC_FAMILIES) & set(OPENING_OUT_METRICS)


# ── Three-path parity (CDF path vs Stage B vs on-read counts) ────────────────

_BENCHMARK_TABLES: list[Table] = [
    cast(Table, BenchmarkSelectedUser.__table__),
    cast(Table, BenchmarkIngestCheckpoint.__table__),
]
_BENCHMARK_RATING_BUCKET: int = 1200
_BENCHMARK_DUMP_MONTH: str = "2026-10"
_BENCHMARK_ELO: int = 1500
_BENCHMARK_EVAL_GAME_COUNT: int = 100
_BENCHMARK_GAMES_IMPORTED: int = 500


async def _create_benchmark_selection(session_maker: async_sessionmaker, user_id: int) -> None:
    """Create the benchmark-only tables and select the seeded user as a completed peer.

    The tables live only in the benchmark DB (not in the Alembic chain), so the test
    creates and later drops them. The username is read back from the user row so the
    ``lower(lichess_username)`` join in ``selected_users_cte('benchmark')`` matches.
    """
    async with session_maker() as session:
        username = (
            await session.execute(
                text("SELECT lichess_username FROM users WHERE id = :uid").bindparams(uid=user_id)
            )
        ).scalar_one()
        conn = await session.connection()
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=_BENCHMARK_TABLES)
        )
        session.add(
            BenchmarkSelectedUser(
                lichess_username=username,
                rating_bucket=_BENCHMARK_RATING_BUCKET,
                tc_bucket=SEED_TC,
                median_elo=_BENCHMARK_ELO,
                eval_game_count=_BENCHMARK_EVAL_GAME_COUNT,
                dump_month=_BENCHMARK_DUMP_MONTH,
            )
        )
        session.add(
            BenchmarkIngestCheckpoint(
                lichess_username=username,
                rating_bucket=_BENCHMARK_RATING_BUCKET,
                tc_bucket=SEED_TC,
                status="completed",
                games_imported=_BENCHMARK_GAMES_IMPORTED,
            )
        )
        await session.commit()


async def _drop_benchmark_tables(session_maker: async_sessionmaker) -> None:
    """Drop the two benchmark-only tables.

    Raw DDL rather than ``Base.metadata.drop_all(tables=...)``: SQLAlchemy's
    drop_all also tries to drop the shared native ENUM types (``gameresult`` ...),
    which the real ``games`` table still depends on.
    """
    async with session_maker() as session:
        await session.execute(
            text("DROP TABLE IF EXISTS benchmark_ingest_checkpoints, benchmark_selected_users")
        )
        await session.commit()


async def _fetch_cdf_path_rows(
    session_maker: async_sessionmaker, user_id: int, metric: OpeningOutMetricId
) -> dict[Color, tuple[float, int]]:
    """The CDF script's path: benchmark-source selection + the floored rate builder."""
    sql = (
        f"WITH {selected_users_cte(source='benchmark')},\n"
        f"{per_user_cte_opening_out_rate(SEED_TC, metric=metric, source='benchmark', snapshot_date=datetime.date.today())}\n"
        "SELECT user_color, metric_value::float AS value, n_games::int AS n_games\n"
        "FROM per_user_values WHERE user_id = :user_id"
    )
    async with session_maker() as session:
        result = await session.execute(text(sql).bindparams(user_id=user_id))
        return {row.user_color: (row.value, row.n_games) for row in result}


async def test_three_path_parity(opening_out_user) -> None:
    """CDF path, persisted Stage B rows and on-read counts agree exactly per colour x metric.

    The CDF path reads the seeded user through ``benchmark_selected_users`` (so the
    ``source='benchmark'`` prelude is exercised); Stage B persists through the
    single-user chain; ``fetch_opening_out_counts`` is the on-read path. All three
    divide the same integer counts, so the comparison is exact float equality.
    """
    user_id, session_maker, specs = opening_out_user
    anchor = await _persist_anchor(session_maker, user_id)
    await _insert_synthetic_cells(session_maker, anchor)
    await _create_benchmark_selection(session_maker, user_id)
    try:
        cdf_path = {
            m: await _fetch_cdf_path_rows(session_maker, user_id, m) for m in OPENING_OUT_METRICS
        }
        await compute_stage_b(user_id, session_maker=session_maker)
        async with session_maker() as session:
            stage_b = await fetch_opening_out_rows(session, user_id=user_id)
            on_read = await fetch_opening_out_counts(session, user_id=user_id, tc=SEED_TC)
    finally:
        await _drop_benchmark_tables(session_maker)
        await _remove_synthetic_cells(session_maker, anchor)

    assert on_read == expected_counts(specs)
    for metric in OPENING_OUT_METRICS:
        assert set(cdf_path[metric]) == set(_COLORS)
        for color in _COLORS:
            counts = on_read[color]
            cdf_value, cdf_n = cdf_path[metric][color]
            row = stage_b[(metric, SEED_TC, color)]
            assert (cdf_value, cdf_n) == (row.value, row.n_games)
            assert (row.value, row.n_games) == (
                counts.count_for(metric) / counts.n_games,
                counts.n_games,
            )
