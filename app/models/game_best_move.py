"""GameBestMove ORM model — best-move candidate table for Gem/Great detection (GEMS-01).

Stores one candidate row per out-of-book best-move ply, keyed on the natural
composite (game_id, ply). Unlike game_flaws, candidacy is a property of the
*position*, not the user, so there is no user_id in the key (Claude's discretion
per 174-PATTERNS.md).

Rows are CANDIDATES only (GEMS-01 / D-4): they never carry a stored tier flag or
any classification column. The Gem vs Great tier is decided at query time from
the stored continuous values (GEMS-07), which keeps the margins fully retunable
with zero re-analysis.

Storage is continuous only (D-05): maia_prob (REAL) plus raw Stockfish
centipawns/mate as SmallInteger — never a pre-converted expected-score value.
This mirrors game_positions.eval_cp's raw int-cp convention; the cp->expected-score
conversion stays query-time.
"""

from sqlalchemy import ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GameBestMove(Base):
    """A best-move candidate ply (query-time tier; no stored classification flag)."""

    __tablename__ = "game_best_moves"

    # Natural composite PK: (game_id, ply). Provably unique — one candidate row per
    # game half-move. The composite primary key is the sole uniqueness mechanism; a
    # separate UniqueConstraint would merely duplicate it. No user_id: best-move
    # candidacy is position-scoped, not user-scoped (unlike game_flaws).
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)

    # Maia policy probability the player would have found this best move (0..1).
    maia_prob: Mapped[float] = mapped_column(REAL, nullable=False)

    # Raw Stockfish evals for the best and second-best moves — centipawns/mate as
    # SmallInteger (D-05). Never a pre-converted expected-score value; the cp->ES
    # conversion stays query-time, matching game_positions.eval_cp.
    best_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    best_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    second_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    second_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
