"""phase 220 opening cache audit

Revision ID: a1c2e3f40001
Revises: e55d2651a373
Create Date: 2026-09-09 12:00:00.000000+00:00

Phase 220 (CACHEFIX-01): the four audit/progress tables for the opening eval
cache repair pipeline (`scripts/opening_cache_repair.py`). SEED-164 diagnosed
the `opening_position_eval` dedup cache (2.57M rows, first-write-wins) as
poisoned by the 2026-06-17 `DISTINCT ON` backfill and the first days of the
full-game drain. These tables ARE the audit trail: every cache row's repair
status lives in `opening_cache_audit`, every propagated `game_positions`
change lives in `opening_cache_repair_rows`, every reclassified game's
before/after numbers live in `opening_cache_repair_games`, and the pipeline's
stage-gate/resume state lives in the singleton `opening_cache_repair_progress`
row. The tables survive the run — they are never dropped after the repair
completes.

Release 1 only (D-01/D-02): this migration does NOT touch
`opening_position_eval` itself. No `confirmed`/`n_sources`/`source_game_id`
provenance columns exist yet — those are Release 2 (a future phase).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1c2e3f40001"
down_revision: Union[str, Sequence[str], None] = "e55d2651a373"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "opening_cache_audit",
        sa.Column("full_hash", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("old_cp", sa.SmallInteger(), nullable=True),
        sa.Column("old_mate", sa.SmallInteger(), nullable=True),
        sa.Column("old_best_move", sa.String(length=5), nullable=True),
        sa.Column("old_pv", sa.Text(), nullable=True),
        sa.Column("sample_game_id", sa.BigInteger(), nullable=True),
        sa.Column("sample_ply", sa.SmallInteger(), nullable=True),
        sa.Column("screen_cp", sa.SmallInteger(), nullable=True),
        sa.Column("screen_mate", sa.SmallInteger(), nullable=True),
        sa.Column("screened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("full_cp", sa.SmallInteger(), nullable=True),
        sa.Column("full_mate", sa.SmallInteger(), nullable=True),
        sa.Column("full_best_move", sa.String(length=5), nullable=True),
        sa.Column("full_pv", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delta_score", sa.REAL(), nullable=True),
        sa.Column("delta_cp", sa.SmallInteger(), nullable=True),
        sa.Column("engine_version", sa.Text(), nullable=True),
        sa.Column(
            "hash_mismatch_attempts", sa.SmallInteger(), server_default="0", nullable=False
        ),
        sa.Column("repaired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','screened_clean','flagged','confirmed_bad',"
            "'confirmed_clean','orphan','hash_mismatch','repaired')",
            name="ck_opening_cache_audit_status",
        ),
        sa.ForeignKeyConstraint(
            ["sample_game_id"], ["games.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("full_hash"),
    )
    op.create_index(
        "ix_opening_cache_audit_status", "opening_cache_audit", ["status"], unique=False
    )

    op.create_table(
        "opening_cache_repair_rows",
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("ply", sa.SmallInteger(), nullable=False),
        sa.Column("full_hash", sa.BigInteger(), nullable=False),
        sa.Column("old_cp", sa.SmallInteger(), nullable=True),
        sa.Column("old_mate", sa.SmallInteger(), nullable=True),
        sa.Column("new_cp", sa.SmallInteger(), nullable=True),
        sa.Column("new_mate", sa.SmallInteger(), nullable=True),
        sa.Column(
            "best_move_replaced", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("pv_replaced", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "repaired_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "ply"),
    )
    op.create_index(
        "ix_opening_cache_repair_rows_hash",
        "opening_cache_repair_rows",
        ["full_hash"],
        unique=False,
    )

    op.create_table(
        "opening_cache_repair_games",
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("rows_repaired", sa.Integer(), server_default="0", nullable=False),
        sa.Column("flaws_before_inacc", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("flaws_before_mist", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("flaws_before_blund", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("flaws_after_inacc", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("flaws_after_mist", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("flaws_after_blund", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("flaws_removed", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("flaws_added", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("drill_items_pruned", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("herrings_touched", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("white_accuracy_before", sa.REAL(), nullable=True),
        sa.Column("white_accuracy_after", sa.REAL(), nullable=True),
        sa.Column("black_accuracy_before", sa.REAL(), nullable=True),
        sa.Column("black_accuracy_after", sa.REAL(), nullable=True),
        sa.Column("white_acpl_before", sa.SmallInteger(), nullable=True),
        sa.Column("white_acpl_after", sa.SmallInteger(), nullable=True),
        sa.Column("black_acpl_before", sa.SmallInteger(), nullable=True),
        sa.Column("black_acpl_after", sa.SmallInteger(), nullable=True),
        sa.Column("reclassified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','reclassified','failed')",
            name="ck_opening_cache_repair_games_status",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id"),
    )
    op.create_index(
        "ix_opening_cache_repair_games_status",
        "opening_cache_repair_games",
        ["status"],
        unique=False,
    )

    op.create_table(
        "opening_cache_repair_progress",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("last_game_id_walked", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("screen_floor", sa.REAL(), nullable=True),
        sa.Column("confirm_floor", sa.REAL(), nullable=True),
        sa.Column("calibration_n", sa.Integer(), nullable=True),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engine_version", sa.Text(), nullable=True),
        sa.Column("seed_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seed_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calibrate_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calibrate_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("screen_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("screen_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirm_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirm_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("propagate_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("propagate_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rederive_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rederive_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legacy_sample_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legacy_sample_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_opening_cache_repair_progress_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("opening_cache_repair_progress")
    op.drop_index(
        "ix_opening_cache_repair_games_status", table_name="opening_cache_repair_games"
    )
    op.drop_table("opening_cache_repair_games")
    op.drop_index(
        "ix_opening_cache_repair_rows_hash", table_name="opening_cache_repair_rows"
    )
    op.drop_table("opening_cache_repair_rows")
    op.drop_index("ix_opening_cache_audit_status", table_name="opening_cache_audit")
    op.drop_table("opening_cache_audit")
