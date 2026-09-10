"""Opening eval cache repair audit tables (Phase 220, CACHEFIX-01).

SEED-164 diagnosed `opening_position_eval` (the position-keyed dedup cache) as
poisoned by the 2026-06-17 `DISTINCT ON` backfill and the first days of the
full-game drain: first-write-wins means a bad early value can never self-heal.
These four tables are the audit trail for `scripts/opening_cache_repair.py`'s
resumable, DB-state-driven repair pipeline (`seed -> calibrate -> screen ->
confirm -> propagate -> rederive -> report`, plus `orphans`/`legacy-sample`).
They are never dropped after the repair completes — they stay as the
permanent record of what was screened, what was found bad, and what was
changed.

Assumption Delta (220-01-PLAN.md, OQ4 resolved): `OpeningCacheAudit.status` is
`Text` + `CheckConstraint`, not `SmallInteger` + a Python `IntEnum`, deviating
from CLAUDE.md's "high-cardinality tables use SMALLINT backed by an IntEnum"
rule at 2.57M rows. Reason: the seed and CACHEFIX-01 both lock `TEXT CHECK`;
the eight status values are operator-facing strings read directly out of
`psql` during a multi-day prod run; the table is not query-hot (one indexed
status lookup per pipeline stage, not a per-request read path); and the
2-byte-per-row saving of SMALLINT is on the order of 5 MB total. Trading that
for readability during a manual, days-long operator run is the right call.

D-01 note: a post-hardening re-audit mode that would set `confirmed` /
`n_sources` on `opening_position_eval` directly from this script is
deliberately NOT built in this phase — hardening (hypothetical Release 2)
ships after the repair, and its migration derives those columns from
`OpeningCacheAudit.status` instead. If the cache is ever re-screened after
hardening ships, a future phase adds that re-audit mode; it is only
documented here, not implemented.

D-02 note: no stage in this phase reads or writes `confirmed` / `n_sources` /
`source_game_id` on `opening_position_eval` — those columns do not exist
until a future two-source-confirmation phase.
"""

from __future__ import annotations

import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OpeningCacheAudit(Base):
    """One row per `opening_position_eval.full_hash` — the repair's per-position ledger.

    No FK on `full_hash` itself (mirrors `OpeningPositionEval`'s own "no FK, no
    cascade" design — the cache row this audits may be deleted independently).
    `status` walks `pending -> screened_clean|flagged|hash_mismatch|orphan`,
    then (for `flagged` rows) `-> confirmed_bad|confirmed_clean`, then (for
    `confirmed_bad` rows once propagated) `-> repaired`.
    """

    __tablename__ = "opening_cache_audit"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','screened_clean','flagged','confirmed_bad',"
            "'confirmed_clean','orphan','hash_mismatch','repaired')",
            name="ck_opening_cache_audit_status",
        ),
        Index("ix_opening_cache_audit_status", "status"),
    )

    # Same key as opening_position_eval.full_hash — the cache row this audits.
    full_hash: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")

    # Snapshot of the cache row's value at `seed` time, so a later stage can
    # tell what changed and the report can show before/after.
    old_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    old_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    old_best_move: Mapped[str | None] = mapped_column(String(5), nullable=True)
    old_pv: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The carrier game/ply `screen` replayed the board from. SET NULL (not
    # CASCADE) — a deleted sample game must not delete the audit row.
    sample_game_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="SET NULL"), nullable=True
    )
    sample_ply: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # `screen` stage result: depth-15 evaluation of the hash-asserted carrier board.
    screen_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    screen_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    screened_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # `confirm` stage result: 1M-node evaluation for rows `screen` flagged.
    full_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    full_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    full_best_move: Mapped[str | None] = mapped_column(String(5), nullable=True)
    full_pv: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Expected-score delta (decision column) and its cp analog (display only).
    delta_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    delta_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Stockfish version string (get_stockfish_version()) at the time this row
    # was last evaluated by the pipeline — e.g. "Stockfish 18".
    engine_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    # D-06 carrier-retry counter: lives in the table (not in memory) so the
    # retry budget survives a kill/resume. Reaches MAX_CARRIERS_PER_HASH before
    # the row is marked hash_mismatch.
    hash_mismatch_attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )

    # `propagate` stamps this once game_positions/repair_rows have been updated.
    repaired_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OpeningCacheRepairRow(Base):
    """One row per `game_positions` cell the `propagate` stage actually rewrote.

    PK mirrors `game_positions`' own natural key (game_id, ply) rather than a
    surrogate — this table exists purely as a per-cell audit trail, one row
    per repaired cell, never queried by anything but the report.
    """

    __tablename__ = "opening_cache_repair_rows"
    __table_args__ = (Index("ix_opening_cache_repair_rows_hash", "full_hash"),)

    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    ply: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    full_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)

    old_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    old_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    new_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    new_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Pitfall 5: pv is written only at flaw-adjacent plies, so its replacement
    # counter must be tracked separately from best_move's — a zero pv_replaced
    # count is normal, not a bug, and the report must be able to tell the two
    # counters apart.
    best_move_replaced: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    pv_replaced: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    repaired_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OpeningCacheRepairGame(Base):
    """One row per game whose `game_positions` rows the repair touched.

    Tracks the `rederive` stage's before/after flaw counts and accuracy/ACPL
    numbers so the report can show the repair's actual effect per game.
    """

    __tablename__ = "opening_cache_repair_games"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','reclassified','failed')",
            name="ck_opening_cache_repair_games_status",
        ),
        Index("ix_opening_cache_repair_games_status", "status"),
    )

    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")

    rows_repaired: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    flaws_before_inacc: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    flaws_before_mist: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    flaws_before_blund: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    flaws_after_inacc: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    flaws_after_mist: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    flaws_after_blund: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    flaws_removed: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    flaws_added: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    drill_items_pruned: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    herrings_touched: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")

    # Matches games.white_accuracy / games.white_acpl column types exactly.
    white_accuracy_before: Mapped[float | None] = mapped_column(REAL, nullable=True)
    white_accuracy_after: Mapped[float | None] = mapped_column(REAL, nullable=True)
    black_accuracy_before: Mapped[float | None] = mapped_column(REAL, nullable=True)
    black_accuracy_after: Mapped[float | None] = mapped_column(REAL, nullable=True)
    white_acpl_before: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    white_acpl_after: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_acpl_before: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_acpl_after: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    reclassified_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class OpeningCacheRepairProgress(Base):
    """Singleton row (id=1) — the pipeline's stage-gate and resume state.

    Every stage's start/finish timestamp lives here so a stage can refuse to
    run before its predecessor finished (`_stage_gate`, CACHEFIX-02) and so a
    killed run can resume: `last_game_id_walked` is the `screen` cursor,
    `screen_floor`/`confirm_floor` are the measured noise floors `calibrate`
    writes and `screen`/`confirm` require to be non-NULL before starting.

    Explicit per-stage columns rather than a JSONB blob: a bound Python `None`
    to JSONB serializes as json `null` rather than SQL NULL
    (`project_asyncpg_jsonb_null_vs_sql_null`), and the report reads these
    columns individually per stage — explicit columns keep that read a plain
    `IS NOT NULL` on a typed column instead of a JSONB path expression.
    """

    __tablename__ = "opening_cache_repair_progress"
    __table_args__ = (CheckConstraint("id = 1", name="ck_opening_cache_repair_progress_singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    last_game_id_walked: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    screen_floor: Mapped[float | None] = mapped_column(REAL, nullable=True)
    confirm_floor: Mapped[float | None] = mapped_column(REAL, nullable=True)
    calibration_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calibrated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    engine_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    seed_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seed_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calibrate_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calibrate_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    screen_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    screen_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirm_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirm_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    propagate_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    propagate_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rederive_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rederive_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    legacy_sample_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    legacy_sample_finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


__all__ = [
    "OpeningCacheAudit",
    "OpeningCacheRepairRow",
    "OpeningCacheRepairGame",
    "OpeningCacheRepairProgress",
]
