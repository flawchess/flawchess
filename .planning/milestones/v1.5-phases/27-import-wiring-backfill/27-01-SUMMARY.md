---
phase: 27-import-wiring-backfill
plan: "01"
subsystem: backend/import
tags: [import, position-classifier, metadata, tdd]
dependency_graph:
  requires:
    - app/services/position_classifier.py (Phase 26-01)
    - app/repositories/game_repository.py (bulk_insert_positions with optional metadata keys)
  provides:
    - classify_position wired into per-ply position_rows assembly in import_service.py
  affects:
    - app/services/import_service.py
    - tests/test_import_service.py
tech_stack:
  added: []
  patterns:
    - Second PGN parse for board state extraction (classify_board/classify_nodes)
    - Graceful degradation via try/except around classify_position per ply
key_files:
  modified:
    - app/services/import_service.py
    - tests/test_import_service.py
decisions:
  - "Second PGN parse is intentional — avoids modifying tested hashes_for_game function; parsing is microseconds per game"
  - "Board advance (classify_board.push) runs regardless of classification success to keep classify_board in sync with hash_tuples index"
  - "Per-ply try/except ensures a single bad position does not abort the whole game's import"
metrics:
  duration: "2 minutes"
  completed_date: "2026-03-24"
  tasks: 1
  files_modified: 2
requirements:
  - PMETA-05
---

# Phase 27 Plan 01: Import Wiring Summary

Wire `classify_position(board)` into the live import pipeline using a second per-game PGN parse, populating all 7 position metadata columns on every newly imported game.

## What Was Built

`import_service._flush_batch()` now calls `classify_position(classify_board)` at each ply before pushing the move, adding game_phase, material_signature, material_imbalance, endgame_class, has_bishop_pair_white, has_bishop_pair_black, and has_opposite_color_bishops to every position_rows dict passed to `bulk_insert_positions`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for classify_position wiring | 4e41812 | tests/test_import_service.py |
| 1 (GREEN) | Wire classify_position into import pipeline | f5360e7 | app/services/import_service.py |

## Key Implementation Details

**Integration point:** `_flush_batch()` in `import_service.py` (lines 392-460)

**Second PGN parse pattern:**
```python
try:
    game_obj_for_classify = chess.pgn.read_game(io.StringIO(pgn))
    classify_nodes = list(game_obj_for_classify.mainline()) if game_obj_for_classify else []
    classify_board = game_obj_for_classify.board() if game_obj_for_classify else None
except Exception:
    classify_board = None
    classify_nodes = []
```

**Per-ply classification (pre-move board state):**
```python
if classify_board is not None:
    try:
        classification = classify_position(classify_board)
        row.update({...7 metadata keys...})
    except Exception:
        logger.warning(...)
    # Advance board regardless of success to stay in sync
    if i < len(classify_nodes):
        classify_board.push(classify_nodes[i].move)
```

## Tests Added

4 new tests in `tests/test_import_service.py::TestRunImport`:
- `test_position_rows_include_game_phase` — all rows have non-null game_phase
- `test_position_rows_include_material_signature` — all rows have non-null material_signature
- `test_starting_position_classified_as_opening` — ply 0 = 'opening', full material signature
- `test_classification_failure_degrades_gracefully` — import completes even when classify_position raises

Total: 25 tests in test_import_service.py (was 21), all passing.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `app/services/import_service.py` exists and imports `classify_position`: confirmed
- `tests/test_import_service.py` contains `game_phase` assertion: confirmed
- Commits 4e41812 and f5360e7: confirmed via `git log --oneline -5`
- All 66 tests pass (25 import + 41 classifier): confirmed
