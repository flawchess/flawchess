"""Add ix_game_flaws_blunder_facts: covering partial index for the facepalm aggregates.

Phase 257 D-21. The Flaws Timeline facepalm band and the "Facepalm blunders" comparison score
every blunder of a user's filtered games with facepalm_expr at query time. Without this index
each blunder is a heap fetch of a wide game_flaws row (~1.4 KB, mostly PV-line blobs the score
never reads): on prod the largest account read ~195k buffers (about 9 s cold) for the timeline
counts alone. The index carries exactly the columns the score and the type read, so both
queries become index-only scans (dev: 7,343 -> 128 buffers for the timeline counts, 23k -> 127
for the comparison, zero heap fetches).

Keyed (user_id, game_id) so the per-game probes of both readers (`game_id IN (...)` / nested
loop on the user's games) stay range scans; partial on severity = 2 because only blunders are
scored. maia_pre_spread is included although its coefficient is 0.0 today, so a refit that uses
it stays index-only.

Created non-concurrently, like the project's other game_flaws index migrations: migrations run
against a quiescent backend at container startup (deploy/entrypoint.sh), and CONCURRENTLY
cannot run inside a transaction. Expect one sequential pass over game_flaws at deploy.

Revision ID: b7e4a1c9d257
Revises: ed1ca360aec4
Create Date: 2026-11-20 18:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4a1c9d257"
down_revision: Union[str, None] = "ed1ca360aec4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_game_flaws_blunder_facts",
        "game_flaws",
        ["user_id", "game_id"],
        unique=False,
        postgresql_include=[
            "ply",
            "maia_played_prob",
            "maia_reply_spread",
            "played_line_material",
            "line_mate_ply",
            "best_line_material",
            "best_line_mate_ply",
            "maia_best_prob",
            "maia_pre_spread",
        ],
        postgresql_where=sa.text("severity = 2"),
    )


def downgrade() -> None:
    op.drop_index("ix_game_flaws_blunder_facts", table_name="game_flaws")
