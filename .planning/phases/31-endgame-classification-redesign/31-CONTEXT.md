# Phase 31: Endgame Classification Redesign - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Redesign endgame analytics from per-game (single transition point) to per-position classification. Add `endgame_class` column to `game_positions`, backfill from existing `material_signature` + `piece_count` data, and rework the endgame repository/service queries to support multi-class per game with a minimum ply threshold. No frontend changes — the Endgames tab UI stays the same, only the backend query logic changes.

</domain>

<decisions>
## Implementation Decisions

### Endgame Analytics Redesign

- **D-01:** Keep the same Endgames tab UI (Statistics + Games sub-tabs, filters, charts). No frontend changes needed. The backend queries become simpler and more accurate.
- **D-02:** A game can count in **multiple endgame classes**. If a game passes through a rook endgame and then a pawn endgame, it counts in both categories — each game outcome (W/D/L) is counted in every endgame class the game participated in.
- **D-03:** **6 plies minimum threshold** — a game only counts in an endgame class if it spent at least 6 plies (3 full moves) in that class. This filters out tactical transitions (piece sacrifices into checkmate, quick class changes) and captures only sustained endgame play.
- **D-04:** Conversion/recovery uses **material_imbalance at the first position** of each endgame class span. Same semantics as today's transition point, applied per-class: "you entered this endgame type up/down material."

### Classifier & Storage

- **D-05:** Do NOT store `game_phase` — it's easily derived from `piece_count <= 6` at query time. Only store `endgame_class`.
- **D-06:** Add `endgame_class` column to `game_positions` — populated only where `piece_count <= 6` (NULL for non-endgame positions). Enables efficient SQL GROUP BY for per-position analytics.
- **D-07:** Endgame class derivation stays as a **separate function** from `classify_position()`. The existing `classify_endgame_class(material_signature)` in `endgame_service.py` is the source of truth. It should be called during import for new games and during backfill for existing rows.
- **D-08:** **Alembic data migration** for backfill — single migration adds the column AND populates it from existing `material_signature` + `piece_count` data. No PGN replay needed.

### Claude's Discretion

- SQL query structure for counting plies per (game_id, endgame_class) and filtering by threshold
- Whether to move `classify_endgame_class()` to position_classifier.py or keep it in endgame_service.py
- Batching strategy for the Alembic data migration UPDATE
- Index strategy for the new endgame_class column (if needed for GROUP BY performance)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current Endgame Implementation
- `app/repositories/endgame_repository.py` — Current per-game transition point queries (to be redesigned)
- `app/services/endgame_service.py` — `classify_endgame_class()` function and aggregation logic (to be updated)
- `app/schemas/endgames.py` — Response schemas (should stay compatible)

### Position Classification
- `app/services/position_classifier.py` — Pure classifier returning raw metrics (NOT being changed to include game_phase/endgame_class)
- `app/models/game_position.py` — GamePosition model (add endgame_class column)

### Import Pipeline
- `app/services/import_service.py` — Wire endgame_class computation into import pipeline
- `app/repositories/game_repository.py` — `bulk_insert_positions()` chunk_size must be updated for wider rows

### Existing Analytics Patterns
- `app/repositories/endgame_repository.py:ENDGAME_PIECE_COUNT_THRESHOLD` — Current threshold constant (6)
- `app/services/analysis_service.py` — `derive_user_result()` and `recency_cutoff()` utilities

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `classify_endgame_class(material_signature)` in endgame_service.py — pure function mapping signature to category. Can be called during import and backfill.
- `_apply_game_filters()` in endgame_repository.py — game filter logic reusable in redesigned queries.
- `ENDGAME_PIECE_COUNT_THRESHOLD = 6` — existing constant for endgame detection.

### Established Patterns
- Alembic data migrations have been done successfully (Phase 27 backfill was standalone, but simpler migrations have used Alembic directly)
- Import pipeline already calls `classify_position()` per position in `_flush_batch()` — adding endgame_class computation is minimal
- `bulk_insert_positions()` chunk_size has been updated multiple times (4000 → 2100 → 2700 → 2300) — needs recalculation for +1 column

### Integration Points
- `GamePosition` model — add `endgame_class` String(12) nullable column
- `_flush_batch()` in import_service.py — compute and store endgame_class alongside existing classifier output
- `endgame_repository.py` — rewrite `query_endgame_entry_rows()` to use per-position grouping with ply count threshold
- `endgame_service.py` — update `_aggregate_endgame_stats()` for multi-class-per-game semantics

</code_context>

<specifics>
## Specific Ideas

- The 6-ply threshold is a named constant, not a magic number — easy to tune later
- Endgame positions are identified by `piece_count <= 6` (Lichess definition, already established)
- The backfill is simple: `UPDATE game_positions SET endgame_class = derive(material_signature) WHERE piece_count <= 6 AND piece_count IS NOT NULL`
- Short tactical transitions (piece sacrifices, quick checkmates) should be filtered out — the threshold ensures only sustained endgame play is counted

</specifics>

<deferred>
## Deferred Ideas

- **Position-level endgame drill-down** — Explore specific endgame positions on a board (like Openings tab for endgames). Builds on stored per-position endgame_class but is a separate feature.
- **MATFLT-01 — Material signature drill-down** — Finer breakdown by specific material configuration (e.g., KRP vs KR within rook endgames). Already tracked in REQUIREMENTS.md.

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-endgame-classification-redesign*
*Context gathered: 2026-03-26*
