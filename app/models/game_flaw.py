"""GameFlaw ORM model — derived materialization table for M+B flaws.

Stores one row per mistake or blunder by either player in the owner's game,
keyed by (user_id = game owner, game_id, ply).
Inaccuracies are never stored here.

es_before, es_after and move_san are not stored — those display values
are sourced at query time from a game_positions join. The fen column
is retained: game_positions stores only Zobrist hashes (no FEN column), so fen
is the one denormalized display column that cannot be recovered without PGN replay.
"""

from typing import Any, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _material_array_shape(column: str) -> str:
    """CHECK predicate: NULL, or a one-dimensional 9-slot array starting at index 1 (D-09, D-17)."""
    return (
        f"{column} IS NULL OR (cardinality({column}) = 9 "
        f"AND array_lower({column}, 1) = 1 AND array_ndims({column}) = 1)"
    )


class GameFlaw(Base):
    __tablename__ = "game_flaws"
    __table_args__ = (
        # Secondary index for severity scans.
        # Covers: filter by user_id + severity (set-membership) for Games-tab EXISTS
        # and Flaws-tab SELECT queries without a full table scan per user.
        Index("ix_game_flaws_user_severity", "user_id", "severity"),
        # Phase 254 array shape checks, NOT VALID so the migration skips the table scan
        # (metadata matches alembic/versions/..._a7d2c9e1b254_phase_254_facepalm_facts.py).
        CheckConstraint(
            _material_array_shape("played_line_material"),
            name="ck_game_flaws_played_line_material_shape",
            postgresql_not_valid=True,
        ),
        CheckConstraint(
            _material_array_shape("best_line_material"),
            name="ck_game_flaws_best_line_material_shape",
            postgresql_not_valid=True,
        ),
    )

    # Natural composite PK: (user_id, game_id, ply) — mirrors game_positions PK.
    # The key is provably unique (one row per user/game/half-move for M+B only).
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        index=True,
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)

    # Severity: 1=mistake, 2=blunder. Filtered via set-membership (severity IN (...)).
    # 0=inaccuracy is NEVER stored here — game_flaws is M+B only.
    severity: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Tempo family: 0=low-clock, 1=hasty, 2=unrushed; NULL when no clock data.
    tempo: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Phase family: 0=opening, 1=middlegame, 2=endgame (denormalized from game_positions.phase).
    phase: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Opportunity family (boolean typed columns — OR-within-family semantics).
    is_miss: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_lucky: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Impact family
    is_reversed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_squandered: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # fen: board_fen() BEFORE the flawed move — the one denormalized display column
    # that cannot be recovered without PGN replay (game_positions stores only Zobrist
    # hashes, no FEN). Used by the miniboard to render
    # the decision-point position and compute move_san → arrow squares.
    # es_before, es_after, move_san are not stored — sourced from a game_positions
    # join in query_flaws (library_repository.py).
    fen: Mapped[str] = mapped_column(String, nullable=False)

    # Tactic family: all nullable SmallInteger.
    # Two orientations, each a 4-tuple:
    #   allowed_* — the refutation from the flaw_ply+1 PV (the move the *opponent* played
    #               to punish the flaw); pov = board_after_flaw.turn.
    #   missed_*  — the "instead-of" tag from the flaw_ply PV (the engine's best continuation
    #               for the flaw-maker at the decision position); pov = board_before.turn.
    #               NULL on older rows until the missed-pass backfill runs.
    #
    # allowed_tactic_depth is the loop index within the flaw_ply+1 PV;
    # missed_tactic_depth is the loop index within the flaw_ply PV (one ply earlier,
    # at the decision position). Both are detector-loop indices within their own PV —
    # neither is an absolute game ply. The depth slider must treat them
    # consistently (same unit, different PV source).
    #
    # tactic_motif: TacticMotifInt value; NULL = no detector fired.
    # tactic_piece: python-chess PieceType (1=PAWN,2=KNIGHT,3=BISHOP,4=ROOK,5=QUEEN,6=KING)
    #               per-motif semantic; NULL for ambiguous cases.
    # tactic_confidence: winner-confidence 0-100; NULL when tactic_motif is NULL.
    # tactic_depth: loop index within the PV when the motif fires; NULL when tactic_motif is NULL.
    allowed_tactic_motif: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    allowed_tactic_piece: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    allowed_tactic_confidence: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    allowed_tactic_depth: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_motif: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_piece: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_confidence: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_depth: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Maia's probability for the move actually played, at the mover's pinned Elo. Nullable,
    # NULL = not scored (or Maia could not score this row). Still a facepalm input (250 D-11
    # dropped the other per-flaw Maia stats of Phase 247 / 248). Written only by
    # app/services/maia_flaw_scoring.py, never by flaw_record_to_row, so a delete-free
    # diff/upsert preserves it by omission.
    maia_played_prob: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)

    # Phase 250 facepalm-score facts (D-05). Nullable, NULL = not scored. maia_reply_spread (and
    # the Phase 254 maia_best_prob / maia_pre_spread below) are written for blunders of BOTH
    # players since SEED-261114-iuv Part A; line_mate_ply and the three Phase 254 line-fact
    # columns below stay user-side only (opponent rows keep them NULL, so facepalm_expr stays NULL
    # there and the drill and library readers, which have no side gate, keep ignoring opponent
    # rows). Written only by app/services/maia_flaw_scoring.py, never by
    # flaw_record_to_row, so a diff/upsert preserves them by omission. The Phase 250 stored
    # score and the five line-loss snapshot columns were dropped in Phase 254 (D-02, D-19):
    # the score is computed at query time by facepalm_expr and the played_line_material array
    # below replaces the snapshots.
    #   maia_reply_spread = 2 ** entropy (bits) of the full Maia policy one ply after the
    #                       blunder (opponent to move), at the blunderer's (the mover's) pinned Elo.
    #   line_mate_ply     = first line ply after which the blunderer is mated; NULL = no mate.
    maia_reply_spread: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)
    line_mate_ply: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Phase 254 facepalm facts (D-09, D-17). Nullable, NULL = not scored. The facepalm score
    # is computed at query time from these facts (app/services/facepalm_score.py
    # facepalm_expr), so a refit or a new lambda never rewrites rows. Written only by
    # app/services/maia_flaw_scoring.py, never by flaw_record_to_row, so a diff/upsert
    # preserves them by omission.
    #   played_line_material = signed material after N plies of the played (refutation) line,
    #                          slot N = depth N (9 slots, one-based); positive = the blunderer
    #                          is up. Even slots are mid-exchange snapshots and may be NULL.
    #   best_line_material   = the same along the engine's best line from the decision
    #                          position; NULL = the best line is unknown (D-18).
    #   best_line_mate_ply   = ply at which the best line mates the opponent, the best move
    #                          counting as ply 0; NULL = no mate in the stored best line.
    #   maia_best_prob       = Maia's probability for the best move at the blunderer's Elo.
    #   maia_pre_spread      = effective number of replies (2 ** entropy) of the position
    #                          before the blunder.
    # The two array columns carry NOT VALID shape CHECKs (NULL or one-dimensional, 9 slots,
    # lower bound 1), added NOT VALID so the migration stays instant.
    played_line_material: Mapped[Optional[list[int | None]]] = mapped_column(
        ARRAY(SmallInteger), nullable=True
    )
    best_line_material: Mapped[Optional[list[int | None]]] = mapped_column(
        ARRAY(SmallInteger), nullable=True
    )
    best_line_mate_ply: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    maia_best_prob: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)
    maia_pre_spread: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)

    # PV-line blob family: write-once JSONB blobs, nullable.
    # These store the principal-variation nodes for the forcing-line tactic gate.
    # `deferred=True` is the structural leak guard: the columns are never emitted in
    # any `select(GameFlaw)` stats scan; an implicit async access would raise MissingGreenlet.
    # Load explicitly via `.options(undefer(GameFlaw.allowed_pv_lines), ...)`.
    #
    # Two orientations, mirroring the tactic family above:
    #   allowed_pv_lines — the refutation PV starting at flaw_ply+1 (the opponent's punishing
    #                       line); pov = board_after_flaw.turn (same as allowed_tactic_* family).
    #   missed_pv_lines  — the best-move PV starting at flaw_ply (engine's best continuation
    #                       for the flaw-maker at the decision position); pov = board_before.turn.
    #
    # Blob shape: each element is a per-node dict with keys:
    #   b  — best_cp (int | null): best-move eval in centipawns, WHITE-perspective.
    #          Gate converts to side-to-move at read time (matching eval_cp convention).
    #   bm — best_mate (int | null): best-move mate distance (positive = mating, white-pov).
    #   s  — second_cp (int | null): second-best-move eval in centipawns, WHITE-perspective.
    #   sm — second_mate (int | null): second-best-move mate distance, white-pov.
    #   su — second_uci (str): second-best-move UCI string (e.g. "e2e4"),
    #          or "" when there is no legal second move (mirrors the PvNode TypedDict sentinel).
    #
    # No MutableList wrapper needed — write-once blobs (mirror of llm_log.response_json).
    # asyncpg auto-registers the JSONB codec; no manual setup required.
    allowed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
    missed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
