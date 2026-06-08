"""Game flaws repository: bulk insert, delete, and FlawRecord→row mapping (Phase 108 Plan 02).

Provides the single FlawRecord→game_flaws row mapping (D-10: one classify path) reused
by the import hook, backfill_flaws.py, and reclassify_positions.py so the materialized
table never drifts from the live classify_game_flaws kernel.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete
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
        "es_before": flaw["es_before"],
        "es_after": flaw["es_after"],
        "move_san": flaw["move_san"],
        "fen": flaw["fen"],
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
