"""fix material_signature to white_black order

Previously, material_signature stored the stronger side first (regardless of
color). This data migration swaps the two halves for rows where black was
stronger (material_imbalance < 0), so the format becomes {white}_{black}.

Revision ID: 8b6149400d29
Revises: ff7b0ea36116
Create Date: 2026-03-25 17:29:47.965350+00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8b6149400d29'
down_revision: Union[str, Sequence[str], None] = 'ff7b0ea36116'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Swap the two halves of material_signature where black was stronger.
    # Old format: {stronger}_{weaker} — when black was stronger, black pieces
    # came first. New format: always {white}_{black}.
    op.execute(
        """
        UPDATE game_positions
        SET material_signature =
            SPLIT_PART(material_signature, '_', 2)
            || '_' ||
            SPLIT_PART(material_signature, '_', 1)
        WHERE material_imbalance < 0
          AND material_signature IS NOT NULL
        """
    )


def downgrade() -> None:
    # Reverse: swap back to stronger-side-first for rows where black is stronger.
    op.execute(
        """
        UPDATE game_positions
        SET material_signature =
            SPLIT_PART(material_signature, '_', 2)
            || '_' ||
            SPLIT_PART(material_signature, '_', 1)
        WHERE material_imbalance < 0
          AND material_signature IS NOT NULL
        """
    )
