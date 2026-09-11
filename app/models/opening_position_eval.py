"""Opening-eval dedup cache — position-keyed, cross-user (SEED-053, Phase 220 CACHEFIX-08).

Design decisions (D-123.1-01, D-123.1-02, D-123.1-03):
  - Keyed by full_hash (BIGINT PK): every distinct opening position maps to at most
    one cached eval row. This collapses the fan-out that makes the self-join slow —
    common opening hashes appear in hundreds/thousands of game_positions rows (ply-0
    dup factor 13,534× on prod), but only once here.
  - Provenance: our-engine full-eval only (full_evals_completed_at IS NOT NULL AND
    lichess_evals_at IS NULL). Lichess %eval entries are excluded — they have no
    best_move/pv, so they cannot let the drain skip the Stockfish pass (D-123.1-03).
  - Column widths match game_positions exactly (SmallInteger eval_cp/eval_mate,
    String(5) best_move for 4-char normal moves + 5-char promotions).

Phase 220 CACHEFIX-08 amendment: the row is NO LONGER immutable. SEED-164 diagnosed
first-write-wins as poisonable by a single misaligned write (the 2026-06-17
OPENING_CACHE_BACKFILL_SQL defect and the first days of the full-game drain), and
Release 2 replaces it with two-source confirmation: a `confirmed=false` candidate
row is replaced wholesale by a disagreeing second source, and only becomes
immutable once `confirmed=true` (two independent games agreed within
OPENING_CACHE_AGREE_MAX_SCORE_DELTA, app/services/eval_drain.py). See
`_upsert_opening_cache`'s candidate/promote/replace algorithm.

Assumption Delta (D-13): `source_game_id` is `BIGINT NULL` with deliberately NO
`ForeignKey`, deviating from CLAUDE.md's FK-mandatory rule. Two reasons: (1) this
table is already deliberately FK-free by design — `full_hash` itself references
nothing, "no FK, no cascade, no invalidation logic" — and (2) a cache row must
survive deletion of the game that happened to source it, because the position eval
it stores remains a valid, reusable fact about that board position independent of
which game first (or last) produced it. A `source_game_id` that CASCADE-deleted
its row on game deletion would silently regress opening dedup coverage every time a
user deleted a game.

D-01 note (from Phase 220's repair plan): `confirmed`/`n_sources` are NOT set by
`scripts/opening_cache_repair.py` — that script predates these columns entirely
(Release 1 ships before Release 2, so the write path stays clean while the repair
runs). The Release-2 migration derives them from `opening_cache_audit.status`
exactly once, at migration time. A post-hardening re-audit mode that would set
these columns from the script directly is deliberately NOT built in this phase;
documented here only, per CONTEXT.md's deferred-ideas list.
"""

from typing import Optional

import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OpeningPositionEval(Base):
    """Denormalized dedup cache of game_positions opening-region our-engine evals.

    One row per distinct full_hash seen in the opening region (ply <=
    DEDUP_MAX_PLY). Populated once by scripts/backfill_opening_eval_cache.py and
    kept current by the eval drain's Step-4 write transaction (plan 02), and — since
    Phase 220 CACHEFIX-08 — governed by two-source confirmation rather than
    first-write-wins (see the class docstring's amendment above).
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

    # Full UCI PV string FROM this position (space-separated moves), Text not
    # String(5) since a PV is many moves. Cached so dedup transplants on the
    # engine-free atomic path carry a walkable PV instead of a permanent []
    # sentinel for opening flaws that land on a cached position (SEED-076 follow-up).
    pv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Phase 220 CACHEFIX-08 provenance columns (D-11, D-12, D-13) ---

    # True once two independent games have agreed on this position's eval within
    # OPENING_CACHE_AGREE_MAX_SCORE_DELTA. Only a confirmed row is transplanted by
    # either read path (eval_apply._fetch_dedup_evals); a candidate is invisible to
    # both dedup transplant and lease-omission.
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # How many independent games' evaluations this row's current value reflects.
    # 1 = candidate (one source so far), 2 = confirmed (a second source agreed).
    # Never exceeds 2 — a confirmed row is immutable to both write lanes.
    n_sources: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")

    # How many times a second source disagreed with this row's candidate value
    # (before it was ever confirmed). D-12: Sentry fires only when this reaches
    # exactly 2 (two consecutive misses on one position), not on every disagreement.
    disagreements: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")

    # Stockfish version string (engine.get_stockfish_version(), e.g. "Stockfish 18")
    # recorded against the row's current value. Recorded but never enforced at read
    # time — see scripts/opening_cache_repair.py's `demote` subcommand docstring for
    # why a routine engine bump does not by itself invalidate confirmed rows.
    engine_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # When this row's current eval/mate/best_move/pv value was last written (insert
    # or replace). NULL for rows that predate this column (Release 1 legacy rows);
    # never read as a freshness gate, informational only.
    written_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # When this row was promoted to confirmed=true. NULL for a candidate.
    confirmed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # The game_id whose engine result produced this row's current value. Deliberately
    # NO ForeignKey (D-13, see the class docstring's "Assumption Delta" above): a
    # result whose game_id equals this column neither promotes nor counts as a
    # disagreement (D-13's self-promotion guard — a re-drained or resubmitted game is
    # the same source, not a second one), and the cache row must outlive the deletion
    # of the game that happened to source it.
    source_game_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
