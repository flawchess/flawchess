"""ORM model for drill_solves — a frozen, pre-materialized per-puzzle row.

One row per puzzle selected at session-composition time, inserted immediately
with `solved_at = NULL` (pre-materialized, not insert-on-attempt). This is what makes the "frozen
list, stable '4 of 12' progress across a resumed mid-window session" cheap:
"remaining" is `WHERE session_id = ? AND solved_at IS NULL`, no re-derivation
of the original composition needed. The solve endpoint becomes an UPDATE, not
an INSERT.

`game_id` is `ON DELETE SET NULL`, NOT `CASCADE` (a one-way door). With a
GLOBAL herring pool, a *foreign* user deleting one of their own
games must never delete a row out of a STRANGER's in-flight session —
`drill_solves` rows ARE the session's frozen puzzle list (PK `(session_id,
position)`), so a CASCADE-delete here would punch a hole in the position
sequence and shift the session-score denominator for a user who did nothing.
Only a global pool (shared across users) can produce this failure mode; a
CASCADE would be correct only when every herring/SR item is necessarily the
solving user's own game.

The row survives its source game's deletion with `game_id` NULL instead
of being deleted. "Still servable" after that means two DIFFERENT things
depending on `source` (see `app.repositories.train_repository`'s
`load_session_puzzles` / `_mark_session_complete_if_done` / `reveal_for_puzzle`
docstrings for the full branch semantics):
- A `RED_HERRING` row stays servable — its FEN/arriving move live on the
  `herring_pool` row, self-sufficient regardless of the game link.
- An `SR_ITEM` row becomes unservable (its answer key was the game's own
  PGN) and is lazily evicted — the same outcome a CASCADE delete would give
  for SR items, via an application-level exclusion instead of a deleted row.

`uq_drill_solves_session_puzzle` (`session_id`, `game_id`, `ply`) no longer
protects a row whose `game_id` has nulled out — PostgreSQL treats NULLs as
distinct in a unique constraint, so two nulled rows in the same session would
not collide on this index. This is acceptable and deliberate: the
constraint's real job is to stop *composition* from inserting the same
position twice, and at composition time every row still has a non-NULL
`game_id` (composition additionally drops an own-game herring colliding with
an SR pick). Do NOT add a partial unique index on
`herring_pool_id` "for safety" — it would forbid the exhaustion fallback
(`herring_stmt(..., exclude_served=False)`) from ever re-serving a pool row
in a later session.

This table stores NO answer-key snapshot: `correct_move`/
`correct_guess`/`played_move` are the RECORDED OUTCOME of an attempt (written
by POST /train/sessions/{id}/solve), never a cached copy of
`best_move`/`pv`/the sharp-soft classification itself.

`herring_pool_id` is the herring's authoritative no-repeat key. Once
`drill_solves.game_id`/`ply` can no longer be trusted as a stable identity for
a herring puzzle (the source game link is nullable), `(game_id, ply)` is no
longer usable for that purpose — the no-repeat exclusion in `herring_stmt` keys
on `herring_pool_id` instead. NULL for every SR row and every row that predates
the global herring pool (a herring's `herring_pool_id` is the only non-NULL
case).

A third `DrillSource` member, `SHARP_FILLER`, backs a static committed CC0
lichess puzzle set (`app.services.sharp_filler`) rather
than a table. `sharp_puzzle_id` is non-None only for a `SHARP_FILLER` row —
`game_id` and `herring_pool_id` both stay NULL for it, mirroring how
`herring_pool_id` is non-None only for a `RED_HERRING` row.
"""

from __future__ import annotations

import datetime
from enum import IntEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DrillSource(IntEnum):
    """Which pool a puzzle was drawn from (75/25 SR/herring mix, plus the static
    sharp-filler set)."""

    SR_ITEM = 0
    RED_HERRING = 1
    SHARP_FILLER = 2


class DrillGuess(IntEnum):
    """The user's pre-attempt "is this critical or several fine" guess."""

    SEVERAL = 0
    CRITICAL = 1


class DrillMoveQuality(IntEnum):
    """Tiered move-quality grade for the played move.

    Members are ordered so the member value equals the move points awarded
    (0/1/2 of the 2 move points in the 1-guess + 2-move = 3 total scoring
    scheme). This is a readability convenience only — the per-session
    scoring formula lives client-side in `frontend/src/lib/trainScore.ts`,
    which stays the single source of truth for display; nothing here should
    be used to compute a score directly. The weekly leaderboard is a deliberate
    server port of the scoring constants in `app.services.train_score`, pinned to
    trainScore.ts by `tests/services/test_train_score_parity.py`.
    """

    WRONG = 0
    INACCURACY = 1
    GOOD = 2


class DrillSolve(Base):
    """One row per puzzle in a frozen session, pre-inserted at composition time."""

    __tablename__ = "drill_solves"
    __table_args__ = (
        CheckConstraint("source IN (0, 1, 2)", name="ck_drill_solves_source"),
        CheckConstraint("guess IS NULL OR guess IN (0, 1)", name="ck_drill_solves_guess"),
        CheckConstraint(
            "move_quality IS NULL OR move_quality IN (0, 1, 2)",
            name="ck_drill_solves_move_quality",
        ),
        UniqueConstraint("session_id", "game_id", "ply", name="uq_drill_solves_session_puzzle"),
        # Read by the weekly Train leaderboard window scan
        # (app.repositories.train_leaderboard_repository.fetch_week_aggregates).
        Index(
            "ix_drill_solves_solved_at", "solved_at", postgresql_where=text("solved_at IS NOT NULL")
        ),
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("drill_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    # 0-based frozen order within the session — the "4 of 12" position.
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Nullable + SET NULL, not NOT NULL + CASCADE — see module docstring for the
    # full rationale (a global pool means a foreign user's game deletion must
    # never delete a row out of another user's session).
    game_id: Mapped[int | None] = mapped_column(
        ForeignKey("games.id", ondelete="SET NULL"), nullable=True
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # The herring's authoritative no-repeat key. NULL for every SR row and
    # every row that predates the global herring pool (see module docstring).
    herring_pool_id: Mapped[int | None] = mapped_column(
        ForeignKey("herring_pool.id", ondelete="SET NULL"), nullable=True
    )

    # The lichess PuzzleId, opaque external identifier
    # (TEXT, not an enumeration -- CLAUDE.md DB rule). No ForeignKey — the
    # referent is a committed data file, not a table. Non-None only for a
    # SHARP_FILLER row; NULL for every SR_ITEM/RED_HERRING row.
    sharp_puzzle_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # The user's raw pre-attempt guess, submitted by the client. NULL until
    # attempted.
    guess: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    correct_guess: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    correct_move: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Tiered move-quality grade: 0=wrong, 1=inaccuracy, 2=good, per
    # DrillMoveQuality. NULL means this row was recorded before the tiered
    # grade existed (no backfill) — `correct_move` above still
    # carries that legacy row's boolean outcome.
    move_quality: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    played_move: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # NULL = not yet attempted. Non-NULL = this puzzle's recorded outcome.
    solved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Client-measured think/review telemetry. Keys are
    # documented by `SolveTelemetry` / `ReviewTelemetry` in app/schemas/train.py.
    # Written only by merging (`coalesce(telemetry, '{}') || patch`), never
    # overwritten. none_as_null: a Python None would be written as a JSON null
    # VALUE, which turns that merge into an array and is skipped by `IS NULL`
    # predicates. A recorded outcome only: never read by grading, scoring, the SR
    # ladder or the leaderboard. Composition inserts never set it, so it
    # stays SQL NULL until a write.
    telemetry: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )
    # The phone's disagreement re-check for this solve.
    # Keys are documented by `SolveRecheck` in app/schemas/train.py plus the
    # server-added `accepted` flag (did the server credit the disagreement).
    # Written once by the claim UPDATE (never merged). Unlike telemetry this IS a
    # grading input. none_as_null: SQL NULL when no re-check ran, never a
    # JSON null value.
    recheck: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )
    # The phone's own grading reading for this keyed solve. Keys are documented by
    # `PhoneGrade` in app/schemas/train.py.
    # Always the phone's 1.5 s reading, never the 3 s re-check reading
    # (that stays in `recheck`). Audit data only: never read by grading, scoring,
    # the SR ladder or the leaderboard. A played == key solve stores equal
    # key/played pairs with tier good, so accuracy queries must filter
    # `played_move != key`. The legacy no-key path stores none. Written
    # once, by the solve claim UPDATE or by the review route via coalesce.
    # none_as_null: "no record" is a true SQL NULL, never a JSON null.
    phone_grade: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )


__all__ = ["DrillGuess", "DrillMoveQuality", "DrillSolve", "DrillSource"]
