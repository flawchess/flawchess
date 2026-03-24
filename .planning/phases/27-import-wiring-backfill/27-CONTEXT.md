# Phase 27: Import Wiring & Backfill - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire `classify_position()` into the live import pipeline so every newly imported game populates all 7 metadata columns (game_phase, material_signature, material_imbalance, endgame_class, has_bishop_pair_white, has_bishop_pair_black, has_opposite_color_bishops) at import time. Then backfill all existing `game_positions` rows using a standalone script that re-parses stored PGN data — no external API calls needed.

Deliverables: modified import pipeline, standalone backfill script, tests.

</domain>

<decisions>
## Implementation Decisions

### Import Wiring
- **D-01:** Call `classify_position(board)` inside the existing per-ply loop in `import_service.py` where `hashes_for_game` results are processed. Extend each `position_rows` dict with the 7 classifier fields before passing to `bulk_insert_positions`.

### Backfill Strategy
- **D-02:** Backfill from stored PGN — re-parse each game's PGN from the `games` table, replay moves through `chess.Board`, call `classify_position()` at each ply, and UPDATE the 7 columns on existing `game_positions` rows. No external API calls, no re-importing.
- **D-03:** Resumability via NULL `game_phase` query — on each run, find games whose positions still have NULL `game_phase`. Self-healing: if interrupted, re-run and it picks up automatically. No state files or marker tables.
- **D-04:** Batch size = 10 games per DB commit, consistent with the import pipeline OOM constraint (STATE.md critical constraint).
- **D-05:** Script location at `scripts/backfill_positions.py` — standalone Python script, run with `uv run python scripts/backfill_positions.py`. Clear separation from app code for a one-time operation.

### Production Deployment
- **D-06:** Run backfill live while app serves traffic — no maintenance window needed. The 7 metadata columns aren't queried by any frontend yet (Phase 28 adds that), so backfill has zero user-visible impact. New imports already populate columns via wired pipeline.
- **D-07:** Script runs `VACUUM ANALYZE game_positions` automatically after completion. No manual step to forget. Satisfies success criterion #4.

### Error Handling
- **D-08:** Skip and log on per-game classification failure — log game_id and error via Sentry (`sentry_sdk.capture_exception()`), skip the game, continue backfill. Consistent with `import_service.py` pattern which wraps `hashes_for_game` in try/except per game. Sentry provides centralized tracking and alerting for free.
- **D-09:** Stdout progress summary — print progress every N games and a final summary: total games processed, positions updated, errors encountered, VACUUM status. No log files.

### Claude's Discretion
- Import wiring approach (how exactly to integrate classify_position into the hashes_for_game loop or the position_rows assembly)
- Backfill UPDATE strategy (per-game UPDATE vs batch UPDATE)
- Progress reporting frequency (every 10, 50, or 100 games)
- Test structure and coverage approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Position Classifier (Phase 26 output)
- `app/services/position_classifier.py` — `classify_position(board)` returns `PositionClassification` dataclass with 7 fields
- `tests/test_position_classifier.py` — Existing unit tests for classifier

### Import Pipeline
- `app/services/import_service.py` — Lines 392-432: the per-game PGN processing loop where classifier must be wired in
- `app/services/zobrist.py` — `hashes_for_game()` function showing the per-ply iteration pattern
- `app/repositories/game_repository.py` — `bulk_insert_positions()` with chunk_size=2100

### Database Model
- `app/models/game_position.py` — `GamePosition` model with all 7 nullable metadata columns already defined
- `alembic/versions/20260323_213217_38239eef59a8_add_position_metadata_columns.py` — Migration that added the columns

### Project Constraints
- `.planning/REQUIREMENTS.md` — PMETA-05: backfill without requiring user re-import
- `.planning/STATE.md` — Critical constraints: batch_size=10, standalone script (not Alembic), chunk_size=2100

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `position_classifier.py` — Pure function `classify_position(board)` ready to call at each ply
- `hashes_for_game()` — Shows the PGN replay pattern: parse PGN, iterate nodes, push moves on board. Backfill script can reuse this exact pattern.
- `import_service.py` position_rows loop — Lines 401-413 show how to build position row dicts; just need to add 7 more keys from `PositionClassification`

### Established Patterns
- `bulk_insert_positions()` already accepts the 7 metadata keys as optional dict keys (docstring updated in Phase 26)
- Per-game try/except with `logger.warning` for PGN parsing failures (import_service.py lines 397-399)
- Sentry SDK initialized in app startup — backfill script needs its own `sentry_sdk.init()`

### Integration Points
- `import_service.py` line 396: after `hashes_for_game(pgn)` call — need to also replay board and classify each position
- `import_service.py` lines 401-413: position_rows dict assembly — add classifier output fields
- `app/core/database.py` — `async_session_maker` for backfill script DB access

</code_context>

<specifics>
## Specific Ideas

- User initially considered a "delete and re-import" approach (deleting all games and re-running import with the new pipeline) to combine with Phase 29's engine analysis import. Decided against it because backfill from stored PGN is purely local (no API calls, no rate limiting) and simpler. Phase 29 can handle engine analysis separately.

</specifics>

<deferred>
## Deferred Ideas

- **Delete-and-reimport approach for engine analysis** — User noted that Phase 29 (engine analysis import) may need to re-fetch games from APIs to get analysis data. Could potentially combine with a reimport at that point. Deferred to Phase 29 planning.

### Reviewed Todos (not folded)
- **Bitboard storage for partial-position queries** — Different capability (partial-position matching), not related to position metadata backfill. Remains in backlog.

</deferred>

---

*Phase: 27-import-wiring-backfill*
*Context gathered: 2026-03-24*
