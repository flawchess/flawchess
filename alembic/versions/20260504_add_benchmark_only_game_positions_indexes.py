"""add benchmark-only game_positions indexes

Adds two indexes that materially speed up the /benchmarks skill queries
(see reports/benchmarks-2026-05-04-section-3.md and the index analysis
in the 2026-05-04 conversation):

- ix_gp_game_id_ply (game_id, ply)
  Enables nested-loop lookups for the entry-ply joins in §1, §3, §4, §5,
  §6 of the benchmarks skill (e.g. `JOIN game_positions ep ON ep.game_id =
  fe.game_id AND ep.ply = fe.entry_ply` and the `p1 / p2` clock pairs).
  Drops the §4/§5 clock-diff query from ~57 s to a few seconds by
  replacing two parallel seq scans of the 38 GB table with index probes.

- ix_gp_phase1_game_ply (game_id, ply) WHERE phase = 1
  Enables an index-only scan for the `first_middlegame` CTE in §3, which
  otherwise does a full parallel seq scan filtering on `phase = 1`
  (~9.5 s). The phase=2 case is already covered by
  ix_gp_user_endgame_game thanks to PHASE-INV-01
  (phase=2 ⟺ endgame_class IS NOT NULL).

Both indexes are intentionally NOT applied to prod / dev, because all
production queries on `game_positions` are scoped by `user_id` and the
existing `(user_id, ...)` indexes are sufficient. A bare `(game_id, ply)`
index would waste storage and slow imports on prod with no query benefit.

The benchmark DB is identified by name (`flawchess_benchmark`); the
migration is a no-op on every other database.

Revision ID: 9083c5eedb02
Revises: 1efcc66a7695
Create Date: 2026-05-04

"""
from typing import Sequence, Union

from alembic import op


revision: str = "9083c5eedb02"
down_revision: Union[str, Sequence[str], None] = "1efcc66a7695"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BENCHMARK_DB_NAME = "flawchess_benchmark"


def _is_benchmark_db() -> bool:
    bind = op.get_bind()
    return bind.exec_driver_sql("SELECT current_database()").scalar() == BENCHMARK_DB_NAME


def upgrade() -> None:
    if not _is_benchmark_db():
        return

    op.create_index(
        "ix_gp_game_id_ply",
        "game_positions",
        ["game_id", "ply"],
        unique=False,
    )
    op.create_index(
        "ix_gp_phase1_game_ply",
        "game_positions",
        ["game_id", "ply"],
        unique=False,
        postgresql_where="phase = 1",
    )


def downgrade() -> None:
    if not _is_benchmark_db():
        return

    op.drop_index(
        "ix_gp_phase1_game_ply",
        table_name="game_positions",
        postgresql_where="phase = 1",
    )
    op.drop_index("ix_gp_game_id_ply", table_name="game_positions")
