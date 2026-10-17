"""HerringPool ORM model — globally shared red-herring position pool.

A red herring is a row drawn from a pool sampled across ALL signed-up users'
games, confirmed by a real MultiPV-5 Stockfish search, not "one of the user's
own several-fine-moves plies" (sourcing from `game_best_moves` was structurally
broken). Position-scoped, not user-scoped — mirrors
`GameBestMove`'s "candidacy is a property of the position" convention, one
level further: the position doesn't even have to belong to the SOLVING user.

Identity: a natural `(user_id, game_id, ply)` primary key, mirroring
`game_positions`, is not possible here. The composite FK to `games(id, user_id)`
is `ondelete="SET NULL"` so a pool row survives its source game's deletion, and
a PostgreSQL primary-key column cannot be NULL. So `id` is a surrogate BigInteger
PK — the row's authoritative identity (the key `drill_solves.herring_pool_id`
records) — and the `(user_id, game_id, ply)` triple is a nullable-tolerant
`UniqueConstraint`, doing its remaining job: generation-time dedup and
`ON CONFLICT (user_id, game_id, ply) DO NOTHING` top-up idempotency.

`ladder` element shape is exactly `{"move_uci": str, "cp": int | null, "mate":
int | null}`, five entries, ordered best-first as Stockfish returned them,
with `cp`/`mate` in **white POV** via the house `_score_to_cp_mate` convention
(`app/services/engine.py`) — no new sign convention is introduced.

`mover_color` is the side to move on the board the generator actually
searched. It is stored rather than re-derived because the generator's own
board is authoritative (the `ply - 1` / `flaw_ply + 1` conventions elsewhere
in this codebase do not obviously reconcile). It must always equal
`mover_color_for_ply(ply)`; the generator asserts that at write time, so any
future ply-indexing drift fails loudly at generation instead of silently
serving a wrong-POV ladder.

Never pass `None` for `ladder` — that writes `null::jsonb`, not SQL NULL.
`nullable=False` plus the
`ck_herring_pool_ladder_shape` CHECK below makes this structurally impossible;
this note exists so nobody relaxes either.

`source_played_at` and `fen`/`arriving_move_uci` are deliberate denormalized
copies so the row survives source-game deletion self-sufficiently —
recency ordering must not require a `games` join.

The ladder-shape CHECK is load-bearing, not decoration: it makes "every
stored row has a complete 5-element array" a *write-time* structural
invariant, so the serve-time query (`herring_stmt`) can call
`jsonb_array_elements` with no shape guard of its own. A `jsonb_typeof` guard
AND-ed with an array-length function in a WHERE clause is a live crash in
this codebase (see `app.services.train_pool.answer_key_present`'s
total-operator docstring) — the write-time CHECK is what makes that unsafe
combination unnecessary at read time.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HerringPool(Base):
    """One globally-shared, position-scoped red-herring candidate."""

    __tablename__ = "herring_pool"
    __table_args__ = (
        # SET NULL, deliberately NOT the codebase's dominant CASCADE — a
        # source-game deletion must not silently erode a pool that is
        # computed once (via scripts/gen_red_herring_pool.py) and topped up
        # manually. The FEN/arriving-move/ladder columns below are
        # denormalized precisely so the row is self-sufficient once orphaned.
        ForeignKeyConstraint(
            ["game_id", "user_id"],
            ["games.id", "games.user_id"],
            ondelete="SET NULL",
            name="herring_pool_game_user_fkey",
        ),
        # The (user_id, game_id, ply) identity triple, demoted from PK to a
        # generation-time dedup key (see this model's docstring).
        UniqueConstraint("user_id", "game_id", "ply", name="uq_herring_pool_source"),
        CheckConstraint("phase IN (0, 1, 2)", name="ck_herring_pool_phase"),
        CheckConstraint("mover_color IN ('white', 'black')", name="ck_herring_pool_mover_color"),
        CheckConstraint(
            "jsonb_typeof(ladder) = 'array' AND jsonb_array_length(ladder) = 5",
            name="ck_herring_pool_ladder_shape",
        ),
        # Recency-first, fully deterministic serve ordering (herring_stmt) —
        # source_played_at DESC NULLS LAST, then id ASC — with no games join.
        Index("ix_herring_pool_recency", "source_played_at", "id"),
    )

    # Surrogate PK: the pool row's own identity,
    # independent of whether the source game/user still exists.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Nullable provenance: a source-game deletion SETs these NULL
    # rather than deleting the row. Never an access-control filter, never a
    # serve-time predicate (the pool is identity-blind at serve time).
    user_id: Mapped[int | None] = mapped_column(nullable=True)
    game_id: Mapped[int | None] = mapped_column(nullable=True)

    # A plain column, never part of a foreign key — ply survives
    # the game link nulling out.
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # The side to move on the generator's own board (see docstring). "white" | "black".
    mover_color: Mapped[str] = mapped_column(String(5), nullable=False)

    # Denormalized full FEN + arriving move: the pool row is the SOLE
    # source for a served herring's board — never re-derived from PGN.
    fen: Mapped[str] = mapped_column(String(120), nullable=False)
    arriving_move_uci: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # Lichess Divider.scala phase classification: 0=opening, 1=middlegame, 2=endgame
    # (mirrors GamePosition.phase's convention).
    phase: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Denormalized copy of the source game's played_at, for recency ordering
    # that survives the source game's deletion.
    source_played_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # The raw MultiPV-5 search result: five {"move_uci", "cp", "mate"}
    # dicts, best-first, white POV. `deferred=True` is the structural leak
    # guard (mirrors `GameFlaw.missed_pv_lines`) — never emitted by an
    # implicit select(HerringPool) scan; the only `undefer(HerringPool.ladder)`
    # call site is `herring_stmt`, whose result is consumed server-side.
    ladder: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, deferred=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["HerringPool"]
