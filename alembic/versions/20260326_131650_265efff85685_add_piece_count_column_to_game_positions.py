"""add piece_count column to game_positions

Adds piece_count (SmallInteger, nullable) to game_positions and backfills
existing rows from material_signature. piece_count counts Q+R+B+N characters
for both sides, excluding K and P. Based on the Lichess endgame definition.

Revision ID: 265efff85685
Revises: 5acd32d13dbb
Create Date: 2026-03-26 13:16:50.420639+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '265efff85685'
down_revision: Union[str, Sequence[str], None] = '5acd32d13dbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('game_positions', sa.Column('piece_count', sa.SmallInteger(), nullable=True))

    # Backfill piece_count from material_signature for existing rows.
    # Counts occurrences of Q, R, B, N characters in the signature string.
    # Kings (K) and pawns (P) are excluded. The underscore separator contains none of these letters.
    # Uses batched updates of 50,000 rows at a time to avoid long locks on production.
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
            WHERE material_signature IS NOT NULL AND piece_count IS NULL;

            IF min_id IS NULL THEN
                RETURN;
            END IF;

            current_min := min_id;
            WHILE current_min <= max_id LOOP
                UPDATE game_positions
                SET piece_count = (
                    LENGTH(material_signature) - LENGTH(REPLACE(material_signature, 'Q', ''))
                    + LENGTH(material_signature) - LENGTH(REPLACE(material_signature, 'R', ''))
                    + LENGTH(material_signature) - LENGTH(REPLACE(material_signature, 'B', ''))
                    + LENGTH(material_signature) - LENGTH(REPLACE(material_signature, 'N', ''))
                )
                WHERE id >= current_min
                  AND id < current_min + batch_size
                  AND material_signature IS NOT NULL
                  AND piece_count IS NULL;

                current_min := current_min + batch_size;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('game_positions', 'piece_count')
