/**
 * Opening explorer depth cap (SEED-033).
 *
 * Mirrors backend `app/models/game_position.py` MAX_EXPLORER_PLY.
 *
 * MUST equal the backend value and the partial-index `ply <= N` boundary.
 * There is no codegen mechanism for this one scalar (the endgameZones.ts
 * gen script covers zone registries, not this constant). If the backend cap
 * changes, change this value too and ship both in the same commit.
 *
 * COUPLING INVARIANT: if this value exceeds the index boundary, hash lookups
 * for positions past the cap silently miss the partial index (SEED-033 §3).
 */
export const MAX_EXPLORER_PLY = 28;
