"""Shared fixtures for the benchmark-generator numeric gates (SEED-029 Phase A).

The chapter `*_diff.py` tests are local calibration-source regression checks: they
run the ported queries against the live benchmark DB (localhost:5433) and assert the
results match the committed `benchmarks-latest.md` snapshot. They skip when the
benchmark DB is unreachable (CI, or `bin/benchmark_db.sh` not started).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scripts import gen_benchmarks


@pytest.fixture
async def benchmark_session() -> AsyncGenerator[AsyncSession, None]:
    """Read-only session on the benchmark DB, or skip if unreachable."""
    url = gen_benchmarks._db_url("benchmark")
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment-dependent
        await engine.dispose()
        pytest.skip(
            f"benchmark DB unreachable ({type(exc).__name__}): run bin/benchmark_db.sh start"
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            yield session
    finally:
        await engine.dispose()
