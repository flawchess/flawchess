"""reclassify pawnless endgames from mixed

Mixed endgames (class 5) without pawns should be pawnless (class 6).
"Pawnless" now means: no pawns at all — bare kings or multi-family
without pawns (e.g. KRN_KR, KQR_KQ).

Revision ID: fb62990270fd
Revises: befacc0fce23
Create Date: 2026-03-27 12:47:52.279180+00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'fb62990270fd'
down_revision: Union[str, Sequence[str], None] = 'befacc0fce23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# endgame_class int values: 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless
_MIXED = 5
_PAWNLESS = 6


def upgrade() -> None:
    """Reclassify mixed endgames without pawns as pawnless (batched)."""
    op.execute(
        f"""
        DO $$
        DECLARE
            batch_size CONSTANT int := 100000;
            rows_updated int := 1;
        BEGIN
            WHILE rows_updated > 0 LOOP
                UPDATE game_positions
                SET endgame_class = {_PAWNLESS}
                WHERE id IN (
                    SELECT id FROM game_positions
                    WHERE endgame_class = {_MIXED}
                      AND material_signature NOT LIKE '%P%'
                    LIMIT batch_size
                );
                GET DIAGNOSTICS rows_updated = ROW_COUNT;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    """Revert pawnless back to mixed for multi-family positions."""
    op.execute(
        f"""
        DO $$
        DECLARE
            batch_size CONSTANT int := 100000;
            rows_updated int := 1;
        BEGIN
            WHILE rows_updated > 0 LOOP
                UPDATE game_positions
                SET endgame_class = {_MIXED}
                WHERE id IN (
                    SELECT id FROM game_positions
                    WHERE endgame_class = {_PAWNLESS}
                      AND material_signature NOT LIKE '%P%'
                      AND material_signature != 'K_K'
                    LIMIT batch_size
                );
                GET DIAGNOSTICS rows_updated = ROW_COUNT;
            END LOOP;
        END $$;
        """
    )
