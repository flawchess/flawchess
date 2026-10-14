"""users unique index on lower(email)

FastAPI-Users looks emails up case-insensitively (func.lower) and expects at
most one match, but ix_users_email is case-sensitive. Guest promotion used an
exact-match uniqueness check, so "Victim@x.com" could be created beside
"victim@x.com" and every later lookup of that email raised MultipleResultsFound
(security review 2026-10-14). Prod and dev had zero case-only duplicates when
this was written; if the upgrade fails on a duplicate, resolve it by hand first.

Revision ID: 778c806092fb
Revises: 015d16c15827
Create Date: 2026-10-14 19:28:02.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "778c806092fb"
down_revision: Union[str, Sequence[str], None] = "015d16c15827"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_email_lower", table_name="users")
