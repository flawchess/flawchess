"""ORM models for the blunder check: sessions, windows and per-move answers.

Phase 249 (D-15 decision: OWN tables, not shared session columns).
`drill_sessions` has schedule-bound NOT NULL `session_date`/`expires_on` (D-02: blunder
check is not tied to the Train schedule) and its `uq_drill_sessions_user_open` index would
stop a user from holding an open puzzle session and an open blunder-check session at the
same time. Phase 251's cross-mode needs (streak across modes, shared schedule, cooldown)
read a UNION over both session tables plus `blunder_check_windows (user_id, game_id,
blunder_ply)`, so MVP rows never need a data migration.

Deletion semantics (LOCKED):
  - `users` delete cascades everything (sessions, windows, answers).
  - A `games` delete only NULLs `blunder_check_windows.game_id` (SET NULL). Windows carry
    their own move snapshot (`start_fen` + `move_ucis`), so a foreign owner deleting a game
    never breaks another user's in-flight session and no VOID outcome is needed. This is
    the same reasoning as `drill_solves.game_id` (a global/foreign pool means a stranger's
    game deletion must never punch a hole in somebody else's session).

Tuning metrics (D-19): no Umami event is needed, the tables carry everything.
  - Sessions started/finished: `blunder_check_sessions.status`, `started_at`, `completed_at`.
  - Window outcomes: `blunder_check_windows.outcome`, `points_scored`, `points_possible`.
  - Abandonment after a forfeit: an open session whose last answered answer row has
    `points_forfeited > 0` and no later answer row.
  - Per-answer timing: `client_elapsed_ms` vs `server_elapsed_ms`.
"""

from __future__ import annotations

import datetime
from enum import IntEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WindowCase(IntEnum):
    """Which kind of judged window this is (stored as SMALLINT)."""

    HERRING = 0  # no blunder in the window: all moves are safe (a red herring)
    ALLOWED = 1  # the window's blunder was allowed by the user's own move
    PURE_MISS = 2  # the blunder is a pure miss
    MIXED = 3


class WindowOutcome(IntEnum):
    """Final result of a window."""

    CLEARED = 0  # herring window, every move correctly passed as safe
    CAUGHT = 1  # blunder window, the user flagged the blunder
    MISSED = 2  # blunder window, the user let the blunder pass
    FALSE_ALARM = 3  # the user flagged a safe move


class WindowArm(IntEnum):
    """Which arm drew a blunder window (Phase 261, stored as SMALLINT)."""

    MAIN = 0  # drawn under the facepalm score cut
    EXPLORATION = 1  # drawn at random, no score cut


class AnswerKind(IntEnum):
    """What the user pressed for one prompted move."""

    SAFE = 0
    BLUNDER = 1
    TIMEOUT = 2


class AnswerResult(IntEnum):
    """Server verdict for one answered move."""

    CORRECT_SAFE = 0
    FALSE_ALARM = 1
    CAUGHT = 2
    MISSED = 3
    TIMEOUT_SAFE = 4
    TIMEOUT_BLUNDER = 5


class BlunderCheckSession(Base):
    """One row per composed blunder-check session (user-scoped header)."""

    __tablename__ = "blunder_check_sessions"
    __table_args__ = (
        # Phase 251: 'expired' joins the set, like drill_sessions (a session past its window).
        CheckConstraint(
            "status IN ('open', 'completed', 'expired')", name="ck_blunder_check_sessions_status"
        ),
        CheckConstraint("window_count >= 1", name="ck_blunder_check_sessions_window_count"),
        # At most one OPEN session per user: partial unique index so completed history
        # rows are unrestricted (precedent: uq_drill_sessions_user_open).
        Index(
            "uq_blunder_check_sessions_user_open",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        # Phase 251: the per-day lookups (completed session on a local day, streak days).
        Index("ix_blunder_check_sessions_user_date", "user_id", "session_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # TEXT + CHECK (low-volume domain column), no native ENUM.
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    # Phase 251: the user's local day the session was composed on and the first local day it is
    # no longer current (`train_scheduler.session_window`), the same window model as drill_sessions.
    session_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    window_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BlunderCheckWindow(Base):
    """One frozen window of a session, pre-inserted at composition time."""

    __tablename__ = "blunder_check_windows"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "position", name="uq_blunder_check_windows_session_position"
        ),
        CheckConstraint(
            "window_length BETWEEN 3 AND 5", name="ck_blunder_check_windows_window_length"
        ),
        CheckConstraint(
            "blunder_position IS NULL OR blunder_position BETWEEN 1 AND window_length",
            name="ck_blunder_check_windows_blunder_position",
        ),
        CheckConstraint(
            "(blunder_position IS NULL) = (blunder_ply IS NULL)",
            name="ck_blunder_check_windows_blunder_ply",
        ),
        CheckConstraint("window_case IN (0, 1, 2, 3)", name="ck_blunder_check_windows_window_case"),
        CheckConstraint(
            "(window_case = 0) = (blunder_ply IS NULL)",
            name="ck_blunder_check_windows_case_herring",
        ),
        CheckConstraint(
            "lead_in_plies BETWEEN 0 AND 4", name="ck_blunder_check_windows_lead_in_plies"
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN (0, 1, 2, 3)", name="ck_blunder_check_windows_outcome"
        ),
        CheckConstraint(
            "better_move_tier IS NULL OR better_move_tier IN (0, 1, 2)",
            name="ck_blunder_check_windows_better_move_tier",
        ),
        # Phase 261 serve-time record: a blunder window carries its arm and a score snapshot, a
        # herring never does, and the record is all-or-nothing.
        CheckConstraint(
            "selection_arm IS NULL OR selection_arm IN (0, 1)",
            name="ck_blunder_check_windows_selection_arm",
        ),
        CheckConstraint(
            "(selection_arm IS NULL) = (arm_probability IS NULL) "
            "AND (arm_probability IS NULL OR (arm_probability > 0 AND arm_probability <= 1))",
            name="ck_blunder_check_windows_arm_probability",
        ),
        CheckConstraint(
            "(selection_arm IS NULL) = (facepalm_score IS NULL)",
            name="ck_blunder_check_windows_arm_snapshot",
        ),
        CheckConstraint(
            "window_case <> 0 OR selection_arm IS NULL",
            name="ck_blunder_check_windows_arm_herring",
        ),
        CheckConstraint(
            "facepalm_score IS NULL OR (facepalm_score >= 0 AND facepalm_score <= 1)",
            name="ck_blunder_check_windows_facepalm_score",
        ),
        # best_prob may be NULL on a scored losing row and reply_prob on a scored row that loses
        # nothing, so neither is required.
        CheckConstraint(
            "facepalm_score IS NULL OR (facepalm_played_prob IS NOT NULL "
            "AND facepalm_loss IS NOT NULL AND facepalm_missed IS NOT NULL)",
            name="ck_blunder_check_windows_snapshot_inputs",
        ),
        CheckConstraint(
            "(facepalm_score IS NULL) = (type_mate IS NULL)",
            name="ck_blunder_check_windows_type_mate",
        ),
        CheckConstraint(
            "type_swing IS NULL OR type_swing >= 0",
            name="ck_blunder_check_windows_type_swing",
        ),
        # D-10 lookups: which plies of a game has this solver already been served.
        Index("ix_blunder_check_windows_user_game", "user_id", "game_id"),
        # Phase 251: feeds the weekly board aggregate (mirrors ix_drill_solves_solved_at).
        Index(
            "ix_blunder_check_windows_ended_at",
            "ended_at",
            postgresql_where=text("ended_at IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("blunder_check_sessions.id", ondelete="CASCADE"), nullable=False
    )
    # 0-based frozen order within the session.
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # The solver (denormalized for D-10 lookups and Phase 251 aggregates).
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Nullable + SET NULL: see module docstring (the snapshot below keeps the window servable).
    game_id: Mapped[int | None] = mapped_column(
        ForeignKey("games.id", ondelete="SET NULL"), nullable=True
    )
    is_own: Mapped[bool] = mapped_column(Boolean, nullable=False)
    window_length: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # 1-based position of the blunder inside the window; NULL for a herring window.
    blunder_position: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    first_ply: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    blunder_ply: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    window_case: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mover_elo: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Self-sufficient snapshot: start FEN plus space-separated UCI moves from the lead-in start.
    start_fen: Mapped[str] = mapped_column(Text, nullable=False)
    move_ucis: Mapped[str] = mapped_column(Text, nullable=False)
    lead_in_plies: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # The game move that led to `start_fen`, shown as the last-move highlight on the Ready gate.
    # NULL when the window starts at the game's first position, and on windows composed before
    # the column existed.
    prior_uci: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # Stockfish best move at the blunder ply (the D-17 key), and the refutation.
    key_uci: Mapped[str | None] = mapped_column(String(5), nullable=True)
    refutation_uci: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # Frozen at composition (D-14).
    points_possible: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    points_scored: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    outcome: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    better_move_uci: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # DrillMoveQuality value (WRONG=0, INACCURACY=1, GOOD=2).
    better_move_tier: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    better_move_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Phase 261 serve-time record (CONTEXT "Claude's Discretion"): the arm, P(arm) at serve time, a
    # snapshot of the facepalm score and its five inputs, and the type-line facts. The score is a
    # query-time expression that moves with every refit and a deleted foreign game NULLs game_id,
    # so the feedback and the calibration read this snapshot. NULL on herring windows and on
    # windows composed before Phase 261, a separate legacy population (no backfill to main).
    selection_arm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    arm_probability: Mapped[float | None] = mapped_column(REAL, nullable=True)
    facepalm_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    facepalm_played_prob: Mapped[float | None] = mapped_column(REAL, nullable=True)
    facepalm_loss: Mapped[float | None] = mapped_column(REAL, nullable=True)
    facepalm_missed: Mapped[float | None] = mapped_column(REAL, nullable=True)
    facepalm_best_prob: Mapped[float | None] = mapped_column(REAL, nullable=True)
    facepalm_reply_prob: Mapped[float | None] = mapped_column(REAL, nullable=True)
    # Deepest settled swing and mate flag on the facepalm-type side (blunder_check_feedback).
    type_swing: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    type_mate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class BlunderCheckAnswer(Base):
    """One row per prompted move of a window (composite PK window_id + move_index)."""

    __tablename__ = "blunder_check_answers"
    __table_args__ = (
        CheckConstraint("move_index BETWEEN 1 AND 5", name="ck_blunder_check_answers_move_index"),
        CheckConstraint(
            "answer IS NULL OR answer IN (0, 1, 2)", name="ck_blunder_check_answers_answer"
        ),
        CheckConstraint(
            "result IS NULL OR result IN (0, 1, 2, 3, 4, 5)",
            name="ck_blunder_check_answers_result",
        ),
        CheckConstraint(
            "(answered_at IS NULL) = (result IS NULL)", name="ck_blunder_check_answers_answered_at"
        ),
    )

    window_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("blunder_check_windows.id", ondelete="CASCADE"),
        primary_key=True,
    )
    move_index: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    prompted_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answer: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    result: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    points_awarded: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    points_forfeited: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    answered_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    client_elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    server_elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


__all__ = [
    "AnswerKind",
    "AnswerResult",
    "BlunderCheckAnswer",
    "BlunderCheckSession",
    "BlunderCheckWindow",
    "WindowArm",
    "WindowCase",
    "WindowOutcome",
]
