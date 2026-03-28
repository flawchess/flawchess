---
phase: 28-engine-analysis-import
plan: 02
subsystem: backend
tags: [import-pipeline, engine-analysis, lichess, eval-extraction, tdd]
dependency_graph:
  requires: [engine-analysis-schema]
  provides: [lichess-eval-import]
  affects: [import_service, game_positions]
tech_stack:
  added: []
  patterns: [tdd, python-chess-pgn-annotations]
key_files:
  created: []
  modified:
    - app/services/import_service.py
    - tests/test_import_service.py
decisions:
  - "evals list built from classify_nodes (same parse pass used for classification) — no extra PGN parse needed"
  - "eval_cp/eval_mate assignment is outside the classify_board guard — eval extraction works even if classify fails"
  - "Eval semantics: annotation on move node stored on same position row as that move_san (same convention as clock_seconds)"
metrics:
  duration: 10m
  completed: "2026-03-25"
  tasks_completed: 1
  files_changed: 2
---

# Phase 28 Plan 02: Eval Extraction in Import Pipeline Summary

Per-move eval extraction from lichess %eval PGN annotations wired into `_flush_batch`: lichess games with prior computer analysis now store `eval_cp` and `eval_mate` on each position row; chess.com games and unannotated lichess games store NULL.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 (RED) | Failing tests for eval extraction | f9ff4f8 | tests/test_import_service.py |
| 1 (GREEN) | Wire eval extraction into _flush_batch | ae41b67 | app/services/import_service.py |

## What Was Built

### Eval Extraction in _flush_batch (app/services/import_service.py)

After the second PGN parse (which produces `classify_nodes`), a new `evals` list is built:

```python
evals: list[tuple[int | None, int | None]] = []
if classify_nodes:
    for node in classify_nodes:
        pov = node.eval()
        if pov is not None:
            w = pov.white()
            evals.append((w.score(mate_score=None), w.mate()))
        else:
            evals.append((None, None))
```

Then in the position row assembly loop, eval fields are added to each row:

```python
eval_cp: int | None = None
eval_mate: int | None = None
if i < len(evals):
    eval_cp, eval_mate = evals[i]
row["eval_cp"] = eval_cp
row["eval_mate"] = eval_mate
```

**Semantics:** `evals[i]` corresponds to `classify_nodes[i]` — the eval annotation on the move played FROM position `i`. The final position (no move node) and chess.com games always receive `(None, None)`. This matches the existing `clock_seconds` convention.

### Tests (tests/test_import_service.py)

`TestEvalExtraction` class with 5 tests:

- `test_lichess_pgn_with_evals` — centipawn (0.18 → 18) and mate-in extraction
- `test_pgn_without_evals` — absent annotations produce all (None, None)
- `test_mate_negative_for_black` — `[%eval #-7]` → `w.mate() == -7`
- `test_evals_list_shorter_than_hash_tuples` — final position index out of evals range gets (None, None)
- `test_import_service_position_rows_contain_eval_fields` — inline loop simulation verifying eval values per position

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `eval_cp` and `eval_mate` are populated for any lichess game that has `%eval` PGN annotations (games with prior computer analysis). The `evals=True` lichess API param was added in Plan 01 to request these annotations. Chess.com games intentionally store NULL (no per-move eval available from the API).

## Self-Check: PASSED

- [x] `app/services/import_service.py` contains `node.eval()` call inside `_flush_batch`
- [x] `app/services/import_service.py` contains `row["eval_cp"]` assignment
- [x] `app/services/import_service.py` contains `row["eval_mate"]` assignment
- [x] Evals list built from `classify_nodes` (not `hashes_for_game`)
- [x] `tests/test_import_service.py` contains `TestEvalExtraction` class
- [x] Tests verify centipawn extraction (18 from 0.18)
- [x] Tests verify mate extraction (-7 for black mates)
- [x] Tests verify None when no %eval present
- [x] `uv run pytest tests/test_import_service.py -x` exits 0 (30 tests)
- [x] `uv run pytest -x` exits 0 (362 tests)
- [x] `uv run ruff check app/services/import_service.py` — no lint errors
- [x] Commits f9ff4f8 and ae41b67 exist
