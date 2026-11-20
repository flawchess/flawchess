import datetime

from sqlalchemy import BigInteger, Double, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkerHeartbeat(Base):
    """Server-side fleet liveness/version registry, upserted on every live submit.

    No consumer UI is built yet — this is raw telemetry that closes the
    fleet-visibility blind spot of hourly-rotating access logs. `worker_id` is
    self-reported/advisory (the `X-Worker-Id` header, truncated to 16 chars by
    `worker_id_label` in `eval_remote.py`) — it is NEVER used for authz/ownership
    decisions. `last_ip` (from the trusted-proxy `request.client.host`) is the
    more trustworthy cross-check for fleet identity, since worker_id can be
    spoofed or shared across machines.

    `holes_submitted` / `plies_leased` are fed ONLY by the atomic-submit lane, so
    a per-worker hole RATE (holes_submitted / plies_leased) is meaningful — unlike
    `evals_submitted`, which mixes all four submit lanes (entry, flaw-blob, atomic,
    bestmove).

    `evals_per_hour_1h` / `evals_per_hour_24h` are exponentially decayed per-worker
    rates (evals/hour), maintained inside `upsert_worker_heartbeat`'s single
    INSERT ... ON CONFLICT DO UPDATE as
    `rate_new = rate_old * exp(-dt/tau) + n_evals/tau`, with dt = hours since the
    existing row's last_seen. tau = 1 h gives the current speed while the worker is
    online; tau = 24 h gives the average contribution including downtime. Values are
    "as of last_seen": an offline worker stops updating, so readers must decay them
    to now() at read time with these exact expressions:

        evals_per_hour_1h * exp(-least(extract(epoch from now() - last_seen) / 3600.0, 50))
        evals_per_hour_24h * exp(-least(extract(epoch from now() - last_seen) / 86400.0, 50))

    The least(..., 50) cap is required: without it Postgres raises an out-of-range
    (float8 underflow) error once a 1h row has been idle about 31 days. Caveats, not
    solved: the unit is evals, which mix all four lanes and are not CPU work; the
    flaw-blob `nothing_pending` discarded-work path returns before the heartbeat, so
    that work is not counted; worker_id is advisory, so machines sharing an id are
    summed. Existing rows start at 0 and warm up with no backfill; the 24h column
    needs about a day of activity before it means much.

    No ForeignKey: worker_id is a free-form external identity string, not a
    reference to an internal table (CLAUDE.md's FK rule doesn't apply here).
    """

    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    last_ip: Mapped[str | None] = mapped_column(
        Text,
        comment=(
            "Operator-owned worker machine IP (local box + Hetzner), not an "
            "end-user IP — negligible GDPR surface (D-06)."
        ),
    )
    sf_version: Mapped[str | None] = mapped_column(String(50))
    # Nullable — only the atomic-submit lane sends this; entry-, flaw-blob- and
    # bestmove-submit never overwrite it back to NULL (coalesce guard in the
    # upsert helper).
    worker_schema_version: Mapped[int | None]
    last_seen: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.now())
    submit_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    evals_submitted: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    # Atomic-submit lane only — see the class docstring. Accumulating
    # counters, same shape as submit_count/evals_submitted.
    holes_submitted: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    plies_leased: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    evals_per_hour_1h: Mapped[float] = mapped_column(
        Double,
        nullable=False,
        server_default="0",
        comment=(
            "Exponentially decayed evals/hour (tau = 1 h) as of last_seen; "
            "decay to now() at read time, see WorkerHeartbeat docstring"
        ),
    )
    evals_per_hour_24h: Mapped[float] = mapped_column(
        Double,
        nullable=False,
        server_default="0",
        comment=(
            "Exponentially decayed evals/hour (tau = 24 h) as of last_seen; "
            "decay to now() at read time, see WorkerHeartbeat docstring"
        ),
    )
