"""users token_version and unverify password-only accounts

Adds users.token_version (the JWT `tv` claim, see app/users.py) and makes
is_verified mean "email ownership was proven". Guest promotion by email/password
used to set is_verified=True without any proof, so those rows (and any other
password account with no linked Google account) are reset to false. A Google
sign-in that later links to such an account replaces its password, closing the
pre-registration account takeover (security review 2026-10-14).

Revision ID: 015d16c15827
Revises: d3a7f1c9e246
Create Date: 2026-10-14 18:54:57.648973+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "015d16c15827"
down_revision: Union[str, Sequence[str], None] = "d3a7f1c9e246"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.execute(
        """
        UPDATE users u
        SET is_verified = false
        WHERE u.is_verified
          AND NOT u.is_guest
          AND u.hashed_password <> ''
          AND NOT EXISTS (SELECT 1 FROM oauth_account o WHERE o.user_id = u.id)
        """
    )


def downgrade() -> None:
    """Downgrade schema.

    The is_verified backfill is not reversible (the prior unproven values carried
    no information); only the column is dropped.
    """
    op.drop_column("users", "token_version")
