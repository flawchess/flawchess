"""phase 251 blunder check boards

Phase 251 Plan 02: the weekly Train leaderboard gains two blunder-check boards next to the two
puzzle boards (D-14), so the stored board CHECK is widened from two keys to four:
``points``, ``accuracy``, ``blunder_check_points``, ``blunder_check_score``.

The two new names are stored per row in ``train_weekly_standings.board`` and echoed by
GET /train/medals/unclaimed and POST /train/medals/claim, so they are one-way (owner-confirmed at
the plan's decision checkpoint: option-a). Widening is additive: every existing row holds one of
the two old keys, so no row can violate the new CHECK.

Revision ID: ed1ca360aec4
Revises: ccc5e4f91f6d
Create Date: 2026-11-18 21:02:27.331083+00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ed1ca360aec4"
down_revision: Union[str, Sequence[str], None] = "ccc5e4f91f6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BOARD_CHECK = "ck_train_weekly_standings_board"
_BOARDS_BEFORE = "board IN ('points', 'accuracy')"
_BOARDS_AFTER = "board IN ('points', 'accuracy', 'blunder_check_points', 'blunder_check_score')"


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(_BOARD_CHECK, "train_weekly_standings", type_="check")
    op.create_check_constraint(_BOARD_CHECK, "train_weekly_standings", _BOARDS_AFTER)


def downgrade() -> None:
    """Downgrade schema.

    Not data-preserving for blunder-check medals: the two-key CHECK has no value a
    ``blunder_check_*`` row could legally hold, so those rows are deleted before it goes back on.

    Why this is needed and not left to an operator: the migration round-trip suites share one
    database with the router tests in serial CI (see the phase 206 downgrade), so a row written by
    an earlier test would otherwise abort the downgrade with a CheckViolationError.
    """
    op.execute(
        "DELETE FROM train_weekly_standings "
        "WHERE board IN ('blunder_check_points', 'blunder_check_score')"
    )
    op.drop_constraint(_BOARD_CHECK, "train_weekly_standings", type_="check")
    op.create_check_constraint(_BOARD_CHECK, "train_weekly_standings", _BOARDS_BEFORE)
