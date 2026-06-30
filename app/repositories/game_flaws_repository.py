"""Game flaws repository: bulk insert, delete, and FlawRecord→row mapping (Phase 108 Plan 02).

Provides the single FlawRecord→game_flaws row mapping (D-10: one classify path) reused
by the import hook, backfill_flaws.py, and reclassify_positions.py so the materialized
table never drifts from the live classify_game_flaws kernel.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_flaw import GameFlaw
from app.services.flaws_service import FlawRecord

# ---------------------------------------------------------------------------
# Encoding maps — mirrors the FlawTag taxonomy from flaws_service.py
# D-03: severity == "inaccuracy" is NEVER stored in game_flaws (M+B only).
# ---------------------------------------------------------------------------

# Severity: 1=mistake, 2=blunder. Filtering uses set-membership (severity IN (...)),
# so the UI's Blunders/Mistakes toggles select exactly the chosen tiers.
# Inaccuracies are count-only (D-03); flaw_record_to_row raises ValueError on "inaccuracy".
_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}

# Tempo family: 0=low-clock, 1=hasty, 2=unrushed; NULL when no clock data.
_TEMPO_INT: dict[str, int] = {"low-clock": 0, "hasty": 1, "unrushed": 2}

# Phase family: 0=opening, 1=middlegame, 2=endgame (denormalized from game_positions.phase).
_PHASE_INT: dict[str, int] = {"opening": 0, "middlegame": 1, "endgame": 2}

# Tempo tags set for membership scan (at most one per FlawRecord per optional-tempo rule)
_TEMPO_TAGS: frozenset[str] = frozenset(_TEMPO_INT)

# Phase tags set for membership scan (exactly one per FlawRecord)
_PHASE_TAGS: frozenset[str] = frozenset(_PHASE_INT)


def flaw_record_to_row(
    *,
    user_id: int,
    game_id: int,
    flaw: FlawRecord,
) -> dict[str, Any]:
    """Map a FlawRecord (M+B only) + game context to a game_flaws insert dict.

    D-10: this is the single FlawRecord→row mapping reused by all write paths
    (import hook, backfill, reclassify) so the materialized table never drifts.

    Args:
        user_id: The owning user's ID (from game.user_id — no cross-user writes).
        game_id: The parent game's ID.
        flaw: A FlawRecord emitted by classify_game_flaws. Must have severity
              "mistake" or "blunder" (D-03: inaccuracies are never stored).

    Returns:
        A dict suitable for pg_insert(GameFlaw).values([row]).

    Raises:
        ValueError: If flaw["severity"] == "inaccuracy" (programming error — the
                    caller must filter to M+B only before calling this function).
    """
    severity = flaw["severity"]
    if severity == "inaccuracy":
        # Guard: inaccuracies are count-only (D-03). Callers using classify_game_flaws
        # should never see an inaccuracy in the returned FlawRecord list, but an explicit
        # guard here catches any future mis-routing.
        raise ValueError(
            f"flaw_record_to_row: severity='inaccuracy' is forbidden (D-03 — "
            f"game_flaws stores M+B only). ply={flaw['ply']}"
        )

    tags = flaw["tags"]

    # Tempo: at most one tempo tag per FlawRecord (optional-tempo rule: NULL when no clock data)
    tempo_int: int | None = None
    for tag in tags:
        if tag in _TEMPO_TAGS:
            tempo_int = _TEMPO_INT[tag]
            break  # exactly at-most-one tempo tag per the optional-tempo rule

    # Phase: exactly one phase tag per FlawRecord (always present)
    phase_int: int | None = None
    for tag in tags:
        if tag in _PHASE_TAGS:
            phase_int = _PHASE_INT[tag]
            break

    if phase_int is None:
        # Defensive: classify_game_flaws always emits a phase tag, but guard here
        # so a misconfigured record fails loudly rather than writing bad data.
        raise ValueError(
            f"flaw_record_to_row: no phase tag in FlawRecord.tags={tags!r} "
            f"(ply={flaw['ply']}). Tags must include exactly one of {sorted(_PHASE_TAGS)}"
        )

    return {
        "user_id": user_id,
        "game_id": game_id,
        "ply": flaw["ply"],
        "severity": _SEVERITY_INT[severity],
        "tempo": tempo_int,
        "phase": phase_int,
        "is_miss": "miss" in tags,
        "is_lucky": "lucky" in tags,
        "is_reversed": "reversed" in tags,
        "is_squandered": "squandered" in tags,
        # Phase 112 (D-07): es_before, es_after, move_san removed — these were display-only
        # columns now sourced via a game_positions join in query_flaws (D-08).
        # The FlawRecord TypedDict still carries them for internal kernel use; they are
        # intentionally not persisted here (Pitfall 6 in 112-CONTEXT.md).
        "fen": flaw["fen"],
        # Tactic family — both orientations (Phase 124/128 — D-01/D-02/D-06).
        # Use .get() so older construction paths that omit keys map to None (not KeyError).
        # Note the int→motif key-name shift: FlawRecord uses _int suffix for motif int values
        # to distinguish from the DB column name (which stores the raw int directly).
        "allowed_tactic_motif": flaw.get("allowed_tactic_motif_int"),
        "allowed_tactic_piece": flaw.get("allowed_tactic_piece"),
        "allowed_tactic_confidence": flaw.get("allowed_tactic_confidence"),
        "allowed_tactic_depth": flaw.get("allowed_tactic_depth"),
        # missed_* are None until the Phase 128 Plan 02 detector second pass runs.
        "missed_tactic_motif": flaw.get("missed_tactic_motif_int"),
        "missed_tactic_piece": flaw.get("missed_tactic_piece"),
        "missed_tactic_confidence": flaw.get("missed_tactic_confidence"),
        "missed_tactic_depth": flaw.get("missed_tactic_depth"),
    }


async def bulk_insert_game_flaws(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> None:
    """Insert game_flaws rows, skipping conflicts (idempotent for import hook).

    Uses ON CONFLICT DO NOTHING on the PK (user_id, game_id, ply).
    Per RESEARCH §11: small per-game row count (~1-5), pg_insert is appropriate.
    No-op on an empty list.

    Args:
        session: AsyncSession to use for the insert.
        rows: List of dicts from flaw_record_to_row — one dict per FlawRecord.
    """
    if not rows:
        return
    stmt = pg_insert(GameFlaw).values(rows).on_conflict_do_nothing()
    await session.execute(stmt)


# The 8 tactic-tag columns refreshed in isolation by retag_flaws.py.
# Kept as a tuple so the script and bulk_update_tactic_tags share one source of truth.
TACTIC_TAG_COLUMNS: tuple[str, ...] = (
    "allowed_tactic_motif",
    "allowed_tactic_piece",
    "allowed_tactic_confidence",
    "allowed_tactic_depth",
    "missed_tactic_motif",
    "missed_tactic_piece",
    "missed_tactic_confidence",
    "missed_tactic_depth",
)


async def bulk_update_tactic_tags(
    session: AsyncSession,
    updates: list[dict[str, Any]],
) -> None:
    """Update ONLY the 8 tactic-tag columns for existing game_flaws rows.

    Used by retag_flaws.py to refresh tactic tags after a detector change or gate margin change
    without delete-and-reinsert (no FK churn, no recompute of severity/tempo/phase,
    minimal WAL). All non-tactic columns are left untouched.

    Each dict must carry the full PK (``user_id`` / ``game_id`` / ``ply``) plus the 8 tactic
    column values keyed by their column names (see TACTIC_TAG_COLUMNS). SQLAlchemy's ORM
    "bulk UPDATE by primary key" derives the WHERE clause from the PK keys and SETs the rest,
    running the whole list as one executemany.

    No-op on an empty list.
    """
    if not updates:
        return
    await session.execute(update(GameFlaw), updates)


async def delete_flaws_for_game(
    session: AsyncSession,
    *,
    game_id: int,
    user_id: int,
) -> None:
    """Delete all game_flaws rows for one game (used by backfill recompute).

    Scoped to BOTH game_id AND user_id so no cross-user deletion is possible
    (T-108-05 mitigation: user_id derived from game.user_id by the caller).

    Args:
        session: AsyncSession to use for the delete.
        game_id: The parent game's ID.
        user_id: The owning user's ID — restricts the delete to the user's rows.
    """
    await session.execute(
        delete(GameFlaw).where(
            GameFlaw.game_id == game_id,
            GameFlaw.user_id == user_id,
        )
    )
