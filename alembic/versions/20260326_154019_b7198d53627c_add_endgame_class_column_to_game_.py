"""add endgame_class column to game_positions

Adds endgame_class (SmallInteger, nullable) to game_positions and backfills
existing endgame rows (piece_count <= 6) from material_signature. Also adds
partial index ix_gp_user_endgame_class for endgame query performance.

Endgame class mapping (must match EndgameClassInt in endgame_service.py):
  1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless.

Revision ID: b7198d53627c
Revises: 798b9ccff13f
Create Date: 2026-03-26 15:40:19.393337+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7198d53627c'
down_revision: Union[str, Sequence[str], None] = '798b9ccff13f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('game_positions', sa.Column('endgame_class', sa.SmallInteger(), nullable=True))

    # Backfill endgame_class from material_signature for endgame positions (piece_count <= 6).
    # Uses batched updates of 50,000 rows to avoid long locks on production. Per D-08.
    # Endgame class mapping (must match EndgameClassInt in endgame_service.py):
    # 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless.
    # Mixed detection: 2+ piece families (Q, R, B/N) present — checked FIRST in CASE.
    op.execute(
        """
        DO $$
        DECLARE
            batch_size INT := 50000;
            min_id BIGINT;
            max_id BIGINT;
            current_min BIGINT;
        BEGIN
            SELECT MIN(id), MAX(id) INTO min_id, max_id
            FROM game_positions
            WHERE piece_count IS NOT NULL
              AND piece_count <= 6
              AND endgame_class IS NULL;

            IF min_id IS NULL THEN
                RETURN;
            END IF;

            current_min := min_id;
            WHILE current_min <= max_id LOOP
                UPDATE game_positions
                SET endgame_class = CASE
                    -- Mixed: 2+ piece families present (queen+rook, queen+minor, rook+minor)
                    WHEN (
                        (material_signature ~ '[Q]') AND
                        (material_signature ~ '[RBN]')
                    ) OR (
                        (material_signature ~ '[R]') AND
                        (material_signature ~ '[BN]')
                    ) THEN 5
                    -- Single piece family
                    WHEN material_signature ~ '[Q]' THEN 4
                    WHEN material_signature ~ '[R]' THEN 1
                    WHEN material_signature ~ '[BN]' THEN 2
                    WHEN material_signature ~ '[P]' THEN 3
                    ELSE 6
                END
                WHERE id >= current_min
                  AND id < current_min + batch_size
                  AND piece_count IS NOT NULL
                  AND piece_count <= 6
                  AND endgame_class IS NULL
                  AND material_signature IS NOT NULL;

                current_min := current_min + batch_size;
            END LOOP;
        END $$;
        """
    )

    op.create_index(
        'ix_gp_user_endgame_class',
        'game_positions',
        ['user_id', 'endgame_class'],
        postgresql_where=sa.text('endgame_class IS NOT NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_gp_user_endgame_class', table_name='game_positions', postgresql_where=sa.text('endgame_class IS NOT NULL'))
    op.drop_column('game_positions', 'endgame_class')
