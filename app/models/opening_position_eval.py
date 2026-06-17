"""Opening-eval dedup cache — position-keyed, cross-user, immutable (SEED-053).

Design decisions (D-123.1-01, D-123.1-02, D-123.1-03):
  - Keyed by full_hash (BIGINT PK): every distinct opening position maps to at most
    one cached eval row. This collapses the fan-out that makes the self-join slow —
    common opening hashes appear in hundreds/thousands of game_positions rows (ply-0
    dup factor 13,534× on prod), but only once here.
  - Immutable: the cached value is a property of the board position, not of any
    game or user. A dangling entry after game/user deletion is still a correct eval.
    No FK, no cascade, no invalidation logic.
  - Provenance: our-engine full-eval only (full_evals_completed_at IS NOT NULL AND
    lichess_evals_at IS NULL). Lichess %eval entries are excluded — they have no
    best_move/pv, so they cannot let the drain skip the Stockfish pass (D-123.1-03).
  - Column widths match game_positions exactly (SmallInteger eval_cp/eval_mate,
    String(5) best_move for 4-char normal moves + 5-char promotions).
"""

from typing import Optional

from sqlalchemy import BigInteger, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OpeningPositionEval(Base):
    """Denormalized dedup cache of game_positions opening-region our-engine evals.

    One row per distinct full_hash seen in the opening region (ply <=
    DEDUP_MAX_PLY). Populated once by scripts/backfill_opening_eval_cache.py and
    kept current by the eval drain's Step-4 write transaction (plan 02).
    """

    __tablename__ = "opening_position_eval"

    # Zobrist hash of the complete board position — explicit BIGINT for 64-bit values,
    # matching game_positions.full_hash (D-123.1-01).
    full_hash: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Centipawn eval from the engine (positive = white advantage). NULL when only a
    # mate score is available. SmallInteger matches game_positions.eval_cp.
    eval_cp: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Mate-in-N score (positive = white mates). NULL when only a cp eval is available.
    # SmallInteger matches game_positions.eval_mate.
    eval_mate: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # PV[0] UCI best move for the position: 4 chars normal (e.g. "e2e4") or 5 chars
    # for promotions (e.g. "e7e8q"). Matches game_positions.best_move (D-117-01).
    best_move: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
