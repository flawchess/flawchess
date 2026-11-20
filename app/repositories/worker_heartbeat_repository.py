"""Worker heartbeat repository: upsert-on-submit fleet liveness registry.

Single shared helper called from every live submit handler (entry, flaw-blob,
atomic, bestmove) inside their existing write session — never opens a new
session, never called from a lease endpoint.
"""

from typing import Any

import sentry_sdk
import sqlalchemy as sa
from sqlalchemy import ColumnElement, Double
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worker_heartbeat import WorkerHeartbeat

# Mirror app/models/worker_heartbeat.py column widths so an oversized value
# from a misbehaving/future worker can never hit a DB-level
# StringDataRightTruncation on the heartbeat insert. `last_ip` is
# intentionally excluded: its model column is
# `Text` (unbounded), so there is no width to truncate to.
_WORKER_ID_MAX_LEN = 16  # WorkerHeartbeat.worker_id: String(16)
_SF_VERSION_MAX_LEN = 50  # WorkerHeartbeat.sf_version: String(50)

# Decay time constants (hours) of the two exponentially decayed eval rates.
RATE_TAU_1H_HOURS = 1.0  # current speed while the worker is online
RATE_TAU_24H_HOURS = 24.0  # average contribution including downtime
_SECONDS_PER_HOUR = 3600.0
# Cap on the decay exponent. Postgres raises "value out of range: underflow" for
# exp(-1000::float8) (threshold about 745), so a tau = 1 h worker idle about 31 days
# would make the upsert raise. The SAVEPOINT swallows that error, last_seen never
# advances, and every later submit hits the same error: the row freezes for good.
# exp(-50) is about 1.9e-22, i.e. zero for any rate, so the cap changes no result.
MAX_DECAY_EXPONENT = 50.0
# Decayed terms below this (evals/hour) snap to 0. float8 multiplication also raises
# on underflow (1e-300 * 1e-30), and n_evals = 0 submits are reachable on all four
# lanes, so a run of them could decay a stored rate into that range and freeze the
# row the same way. With the floor, stored rates are 0 or at least min(floor, 1/24),
# so rate * exp(-MAX_DECAY_EXPONENT) never underflows.
_RATE_ZERO_FLOOR = 1e-6


def _decayed_rate(
    rate_col: InstrumentedAttribute[float], excluded_rate: ColumnElement[Any], tau_hours: float
) -> ColumnElement[Any]:
    """SQL for `rate_old * exp(-dt/tau) + excluded_rate`, with the underflow guards.

    WorkerHeartbeat.last_seen here is the PRE-update value: Postgres evaluates every
    ON CONFLICT SET expression against the existing row.

    greatest(dt, 0) covers clock oddities and ordinary concurrency: now() is the
    transaction START time and the heartbeat runs at the end of a possibly long
    submit transaction, so a transaction that started earlier but upserts after a
    later-started one has committed sees last_seen > now().
    """
    # Cast to Double so the whole expression stays float8 rather than numeric.
    dt_hours = (
        sa.cast(sa.extract("epoch", sa.func.now() - WorkerHeartbeat.last_seen), Double)
        / _SECONDS_PER_HOUR
    )
    exponent = sa.func.least(sa.func.greatest(dt_hours, 0.0) / tau_hours, MAX_DECAY_EXPONENT)
    decayed = rate_col * sa.func.exp(-exponent)
    return sa.case((decayed < _RATE_ZERO_FLOOR, 0.0), else_=decayed) + excluded_rate


async def upsert_worker_heartbeat(
    session: AsyncSession,
    *,
    worker_id: str,
    last_ip: str | None,
    sf_version: str | None,
    worker_schema_version: int | None,
    n_evals: int,
    n_holes: int = 0,
    n_plies_leased: int = 0,
) -> None:
    """Upsert one worker_heartbeats row by advisory worker identity.

    Accumulates submit_count/evals_submitted across calls for the same worker_id;
    overwrites last_ip/sf_version/last_seen with the latest values. worker_schema_version
    is coalesced: a lane that omits it (entry-submit, flaw-blob-submit) must never
    clobber the last known atomic-lane value with NULL.

    n_holes/n_plies_leased accumulate exactly like
    submit_count/evals_submitted, but are ATOMIC-LANE-ONLY: the default of 0 is
    load-bearing so the untouched entry and flaw-blob call sites can
    never inflate them, keeping holes_submitted/plies_leased a meaningful per-worker
    hole rate.

    evals_per_hour_1h/_24h are exponentially decayed rates updated atomically in the
    same statement (rate_new = rate_old * exp(-dt/tau) + n_evals/tau, see
    `_decayed_rate`); a first insert stores n_evals/tau. The decay exponent is
    capped and tiny decayed terms snap to 0 so float8 underflow can never make
    this statement raise and freeze the row under the swallowing SAVEPOINT.

    Does NOT commit — the caller's existing write session owns the commit.

    This is passive telemetry only — never a gate — so ANY failure here (a
    still-oversized value, a transient DB error, etc.) is isolated to its own
    SAVEPOINT and swallowed after a Sentry capture. It must never abort the
    caller's surrounding write transaction and discard real, already-computed
    Stockfish eval work.
    """
    worker_id = worker_id[:_WORKER_ID_MAX_LEN]
    if sf_version is not None:
        sf_version = sf_version[:_SF_VERSION_MAX_LEN]

    stmt = pg_insert(WorkerHeartbeat).values(
        worker_id=worker_id,
        last_ip=last_ip,
        sf_version=sf_version,
        worker_schema_version=worker_schema_version,
        last_seen=sa.func.now(),
        submit_count=1,
        evals_submitted=n_evals,
        holes_submitted=n_holes,
        plies_leased=n_plies_leased,
        evals_per_hour_1h=n_evals / RATE_TAU_1H_HOURS,
        evals_per_hour_24h=n_evals / RATE_TAU_24H_HOURS,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["worker_id"],
        set_={
            "last_ip": stmt.excluded.last_ip,
            "sf_version": stmt.excluded.sf_version,
            # worker_schema_version: only overwrite when the new value is non-NULL
            # (entry/flaw-blob lanes never send it — must not clobber the
            # last known atomic-lane value with NULL).
            "worker_schema_version": sa.func.coalesce(
                stmt.excluded.worker_schema_version, WorkerHeartbeat.worker_schema_version
            ),
            "last_seen": stmt.excluded.last_seen,
            "submit_count": WorkerHeartbeat.submit_count + stmt.excluded.submit_count,
            "evals_submitted": WorkerHeartbeat.evals_submitted + stmt.excluded.evals_submitted,
            "holes_submitted": WorkerHeartbeat.holes_submitted + stmt.excluded.holes_submitted,
            "plies_leased": WorkerHeartbeat.plies_leased + stmt.excluded.plies_leased,
            "evals_per_hour_1h": _decayed_rate(
                WorkerHeartbeat.evals_per_hour_1h,
                stmt.excluded.evals_per_hour_1h,
                RATE_TAU_1H_HOURS,
            ),
            "evals_per_hour_24h": _decayed_rate(
                WorkerHeartbeat.evals_per_hour_24h,
                stmt.excluded.evals_per_hour_24h,
                RATE_TAU_24H_HOURS,
            ),
        },
    )
    try:
        async with session.begin_nested():
            await session.execute(stmt)
    except Exception as exc:
        sentry_sdk.set_context("heartbeat", {"worker_id": worker_id})
        sentry_sdk.capture_exception(exc)
