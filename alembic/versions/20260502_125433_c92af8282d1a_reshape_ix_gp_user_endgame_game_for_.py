"""reshape ix_gp_user_endgame_game for eval columns

Revision ID: c92af8282d1a
Revises: 4be323b0e0fd
Create Date: 2026-05-02 12:54:33.238653+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c92af8282d1a'
down_revision: Union[str, Sequence[str], None] = '4be323b0e0fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop ix_gp_user_endgame_game and recreate with INCLUDE(eval_cp, eval_mate).

    Previously INCLUDE(material_imbalance) — replaced by INCLUDE(eval_cp, eval_mate)
    to enable index-only scans for the eval-based endgame classification queries
    (REFAC-02 / Phase 78-05).
    """
    op.drop_index(
        "ix_gp_user_endgame_game",
        table_name="game_positions",
        postgresql_where="endgame_class IS NOT NULL",
    )
    op.create_index(
        "ix_gp_user_endgame_game",
        "game_positions",
        ["user_id", "game_id", "endgame_class", "ply"],
        postgresql_where="endgame_class IS NOT NULL",
        postgresql_include=["eval_cp", "eval_mate"],
    )


def downgrade() -> None:
    """Restore ix_gp_user_endgame_game with original INCLUDE(material_imbalance)."""
    op.drop_index(
        "ix_gp_user_endgame_game",
        table_name="game_positions",
        postgresql_where="endgame_class IS NOT NULL",
    )
    op.create_index(
        "ix_gp_user_endgame_game",
        "game_positions",
        ["user_id", "game_id", "endgame_class", "ply"],
        postgresql_where="endgame_class IS NOT NULL",
        postgresql_include=["material_imbalance"],
    )
