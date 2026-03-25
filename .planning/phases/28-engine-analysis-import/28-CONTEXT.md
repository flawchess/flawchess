# Phase 28: Engine Analysis Import - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Import available engine analysis data from chess.com and lichess during game import. Lichess provides per-move evaluations via `%eval` PGN annotations; chess.com provides game-level accuracy scores via JSON. Store each at its natural granularity. Includes an admin re-import script to backfill existing games by deleting and re-importing from scratch.

Deliverables: Alembic migration (new columns), updated import pipeline (lichess eval extraction + chess.com accuracy extraction), updated normalization + API client, admin re-import script, tests.

</domain>

<decisions>
## Implementation Decisions

### Data Storage Schema
- **D-01:** Per-move evals stored on `game_positions` table — two new nullable columns: `eval_cp` (SmallInteger, centipawns) and `eval_mate` (SmallInteger, mate-in-N moves, signed: positive = white mates, negative = black mates). Both NULL for unanalyzed games or chess.com games.
- **D-02:** Game-level accuracy stored on `games` table — two new nullable Float columns: `white_accuracy` and `black_accuracy`. Both sides stored (not just the user's) to support opponent scouting. Only populated for chess.com games that have accuracy data.
- **D-03:** Split storage matches data granularity: per-move data on positions, game-level data on games. No denormalization.

### Lichess Eval Extraction
- **D-04:** Add `evals=true` to lichess API request params (in `lichess_client.py`). Unanalyzed games simply won't have `%eval` annotations — python-chess `node.eval()` returns `None`. Zero overhead for unanalyzed games.
- **D-05:** Eval representation: centipawns as SmallInteger (e.g., +18 for 0.18 pawns, -112 for -1.12). Mate scores in separate SmallInteger column (e.g., -7 means black mates in 7). python-chess `node.eval()` returns `PovScore` which provides both via `.white().score(mate_score=None)` and `.white().mate()`.
- **D-06:** Extract evals in the same PGN parsing loop where `hashes_for_game` or the per-ply classification runs. `node.eval()` is called per move node, same as `node.clock()`.

### Chess.com Accuracy Import
- **D-07:** Chess.com accuracy lives at the game JSON level: `game["accuracies"]["white"]` and `game["accuracies"]["black"]` (floats, e.g., 83.53). Not all games have this field — only analyzed games.
- **D-08:** Extract accuracy in `normalize_chesscom_game()` — add `white_accuracy` and `black_accuracy` to the normalized game dict. Store both sides for opponent scouting potential.
- **D-09:** Games without `accuracies` key: both columns remain NULL. No error logged — this is normal for unanalyzed games.

### Backfill Strategy
- **D-10:** No automatic backfill of existing games. Only newly imported games (going forward) get eval/accuracy data. Old games retain NULL values.
- **D-11:** Admin re-import script at `scripts/reimport_games.py` — deletes all games + positions for specified user(s), then re-imports from scratch using the updated pipeline. Clean slate approach: `uv run python scripts/reimport_games.py [--user-id N | --all]`.
- **D-12:** Full re-import via UI deferred to a future phase. For now, admin runs the script once after deploying Phase 28.

### Claude's Discretion
- How to extend `hashes_for_game()` or the per-ply loop to extract evals (refactor tuple or add a parallel extraction)
- Re-import script implementation details (batch size, progress reporting, error handling)
- Test structure and coverage approach
- Whether to update stored PGN column with eval-enriched PGN during lichess re-import (the new fetch includes `evals=true` so PGN will have `%eval` annotations)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Import Pipeline
- `app/services/import_service.py` — `_flush_batch()` at lines 343-459: where games are inserted and positions computed. Eval extraction integrates here.
- `app/services/zobrist.py` — `hashes_for_game()` at lines 77-136: PGN parsing loop that already extracts `node.clock()`. `node.eval()` follows the same pattern.
- `app/services/normalization.py` — `normalize_chesscom_game()` at line 141 and `normalize_lichess_game()` at line 233: where accuracy/eval data enters the normalized dict.

### Platform Clients
- `app/services/lichess_client.py` — `fetch_lichess_games()` at line 21: API params need `evals=true` added.
- `app/services/chesscom_client.py` — `fetch_chesscom_games()` at line 53: game JSON already contains `accuracies` field, just needs to be passed through.

### Database Models
- `app/models/game.py` — `Game` model: needs `white_accuracy`, `black_accuracy` Float columns.
- `app/models/game_position.py` — `GamePosition` model: needs `eval_cp` SmallInteger and `eval_mate` SmallInteger columns.
- `app/repositories/game_repository.py` — `bulk_insert_games()` and `bulk_insert_positions()`: must handle new columns.

### Prior Phase Patterns
- `scripts/backfill_positions.py` — Phase 27 backfill script pattern to follow for re-import script structure.
- `app/services/position_classifier.py` — Phase 26/27 pattern of wiring new per-ply computation into import.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `node.eval()` from python-chess: already available on game tree nodes, returns `PovScore` or `None`. Same API as `node.clock()` which is already used.
- `hashes_for_game()`: PGN parsing loop iterates over `game.mainline()` nodes — eval extraction is one extra call per node.
- `normalize_chesscom_game()` / `normalize_lichess_game()`: established pattern for extracting platform-specific fields into normalized dict.
- Phase 27 backfill script (`scripts/backfill_positions.py`): pattern for standalone admin scripts.

### Established Patterns
- Nullable columns added via Alembic migration, populated during import (Phase 26/27 pattern)
- Two PGN parse passes in `_flush_batch()`: one for hashes, one for classification. Eval extraction fits in the classification pass (which already iterates nodes).
- `Float(24)` for REAL (4 bytes) vs DOUBLE PRECISION — used for `clock_seconds`, applicable for accuracy.
- Error handling: try/except per game with `logger.warning()` for non-fatal failures.

### Integration Points
- `lichess_client.py` params dict: add `"evals": True`
- `normalization.py`: add accuracy extraction in chess.com normalizer
- `_flush_batch()` position row assembly: add `eval_cp` and `eval_mate` fields
- `Game` model + migration: add accuracy columns
- `GamePosition` model + migration: add eval columns

</code_context>

<specifics>
## Specific Ideas

- Chess.com public API does NOT provide per-move evals — only game-level accuracy. Verified by fetching actual API response (Hikaru game March 2026): PGN has `%clk` only, accuracy is in top-level `accuracies` JSON field.
- Lichess `%eval` format: `[%eval 0.18]` for centipawns (in pawns), `[%eval #-7]` for mate. python-chess parses these automatically via `node.eval()`.
- The user specifically wants both sides' accuracy stored (white + black) for opponent scouting, not just the user's accuracy.

</specifics>

<deferred>
## Deferred Ideas

- **Full re-import via UI** — user-triggerable re-import button on the Import page. Deferred to future phase.
- **Human-like engine analysis** — Stockfish + Maia Chess pipeline for human-plausible eval scoring. Entirely different scope (v2+ feature, own milestone). Captured in todo: `2026-03-11-human-like-engine-analysis.md`.
- **Derive accuracy for lichess games** — compute game-level accuracy from per-move evals to create unified accuracy metric across platforms. Could be a future enhancement.

</deferred>

---

*Phase: 28-engine-analysis-import*
*Context gathered: 2026-03-25*
