"""convert result user_color termination time_control_bucket to pg enums and drop variant

Revision ID: 3e4018d62102
Revises: 68879c51818c
Create Date: 2026-04-08 15:51:49.111448+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3e4018d62102'
down_revision: Union[str, Sequence[str], None] = '68879c51818c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The three enum types to create
game_result_enum = postgresql.ENUM("1-0", "0-1", "1/2-1/2", name="gameresult", create_type=False)
color_enum = postgresql.ENUM("white", "black", name="color", create_type=False)
termination_enum = postgresql.ENUM(
    "checkmate", "resignation", "timeout", "draw", "abandoned", "unknown",
    name="termination", create_type=False,
)
time_control_bucket_enum = postgresql.ENUM(
    "bullet", "blitz", "rapid", "classical",
    name="timecontrolbucket", create_type=False,
)


def upgrade() -> None:
    """Convert result, user_color, termination, time_control_bucket to PostgreSQL ENUMs and drop variant."""
    # Create enum types in the database
    game_result_enum.create(op.get_bind(), checkfirst=True)
    color_enum.create(op.get_bind(), checkfirst=True)
    termination_enum.create(op.get_bind(), checkfirst=True)
    time_control_bucket_enum.create(op.get_bind(), checkfirst=True)

    # Alter columns to use enums (USING clause casts existing varchar data)
    op.execute("ALTER TABLE games ALTER COLUMN result TYPE gameresult USING result::gameresult")
    op.execute("ALTER TABLE games ALTER COLUMN user_color TYPE color USING user_color::color")
    op.execute("ALTER TABLE games ALTER COLUMN termination TYPE termination USING termination::termination")
    op.execute("ALTER TABLE games ALTER COLUMN time_control_bucket TYPE timecontrolbucket USING time_control_bucket::timecontrolbucket")

    # Drop the variant column (always "Standard", filtered at import time)
    op.drop_column("games", "variant")


def downgrade() -> None:
    """Revert enum columns to varchar and restore variant column."""
    # Re-add variant column
    op.add_column("games", sa.Column("variant", sa.String(50), nullable=False, server_default="Standard"))

    # Revert enum columns to varchar
    op.execute("ALTER TABLE games ALTER COLUMN time_control_bucket TYPE VARCHAR(20) USING time_control_bucket::text")
    op.execute("ALTER TABLE games ALTER COLUMN termination TYPE VARCHAR(20) USING termination::text")
    op.execute("ALTER TABLE games ALTER COLUMN user_color TYPE VARCHAR(5) USING user_color::text")
    op.execute("ALTER TABLE games ALTER COLUMN result TYPE VARCHAR(10) USING result::text")

    # Drop enum types
    time_control_bucket_enum.drop(op.get_bind(), checkfirst=True)
    termination_enum.drop(op.get_bind(), checkfirst=True)
    color_enum.drop(op.get_bind(), checkfirst=True)
    game_result_enum.drop(op.get_bind(), checkfirst=True)
