---
phase: 79-position-phase-classifier-and-middlegame-eval
plan: "02"
subsystem: import-pipeline
tags:
  - import-pipeline
  - phase-classification
  - middlegame-eval
  - stockfish
  - sentry

dependency_graph:
  requires:
    - "app/services/position_classifier.py (PositionClassification.phase from Plan 79-01)"
    - "app/models/game_position.py (phase SmallInteger column from Plan 79-01)"
    - "app/services/engine.py (evaluate() API from Phase 78)"
  provides:
    - "app/services/zobrist.py: PlyData.phase int field; both ply loops populate it from classification.phase"
    - "app/services/import_service.py: bulk-insert payload writes phase; middlegame entry eval pass (PHASE-IMP-01)"
  affects:
    - "79-03: backfill script extension (reads phase from already-populated rows)"
    - "79-04: dev-DB round (verifies phase non-NULL on every new game row)"

tech_stack:
  added: []
  patterns:
    - "TypedDict extension with bare int field (not Literal for performance in hot loop)"
    - "TDD: RED commit (failing test) + GREEN commit (implementation) per task"
    - "Middlegame entry eval gated by T-78-17 lichess preservation guard"
    - "Bounded Sentry context (game_id + ply only; no pgn/fen/user_id per T-78-18)"
    - "eval_kind tag differentiates middlegame_entry vs endgame_span_entry in Sentry"

key_files:
  created: []
  modified:
    - "app/services/zobrist.py"
    - "app/services/import_service.py"
    - "tests/test_zobrist.py"
    - "tests/services/test_import_service_eval.py"
    - "tests/test_import_service.py"

decisions:
  - "PlyData.phase uses bare 'int' annotation (not Literal[0,1,2]) to avoid ty-check overhead in the hot ply loop — the producer (classify_position) already enforces the Literal"
  - "Middlegame block is inserted BEFORE the existing endgame span-entry loop in the eval pass, per D-79-08 single-contiguous-entry contract"
  - "Existing test mocks updated to include 'phase' key (Rule 1 bug fix: KeyError on pd['phase'] would silently swallow the import job in the outer try/except)"

metrics:
  duration: "18 minutes"
  completed: "2026-05-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 79 Plan 02: Import Pipeline Integration Summary

Wire the Phase 79 `phase` field into the import pipeline: extend `PlyData` TypedDict in `zobrist.py` with `phase: int`, populate it from `classification.phase` in both ply loops, add `"phase": ply_data["phase"]` to the bulk-insert payload in `import_service.py`, and extend the Phase 78 eval pass with a single middlegame-entry Stockfish call per game.

## What Was Built

### Task 1: PlyData phase field (SCHEMA-02)

`app/services/zobrist.py` extended with:

- `PlyData` TypedDict gains `phase: int` field after `endgame_class` with comment: `# 0=opening, 1=middlegame, 2=endgame; lichess Divider.scala (D-79-07)`
- Intermediate-ply loop append: `phase=classification.phase,` added
- Final-position append: `phase=classification.phase,` added

Exactly **2** occurrences of `phase=classification.phase,` in `zobrist.py` (one per loop variant). Runtime introspection check: `PlyData.__annotations__['phase'] is int` prints `OK`.

### Task 2: Bulk-insert payload and middlegame entry eval (PHASE-IMP-01, PHASE-IMP-02)

`app/services/import_service.py` extended with three changes:

**Step 1 — bulk-insert payload:**
`"phase": ply_data["phase"]` added to the row dict inside the ply loop (line ~520), landing on the `game_positions.phase` column from Plan 79-01.

**Step 2 — middlegame entry eval block:**

Inserted at the top of the `for g_id, pgn_text, plies_list in game_eval_data:` loop, **before** the existing per-class endgame span-entry loop:

```python
# Phase 79 PHASE-IMP-01: middlegame entry eval — MIN(ply) where phase == 1.
midgame_entries = [pd for pd in plies_list if pd["phase"] == 1]
if midgame_entries:
    mid_pd = min(midgame_entries, key=lambda p: p["ply"])
    # T-78-17 lichess preservation: skip if lichess %eval already populated the row.
    if mid_pd["eval_cp"] is None and mid_pd["eval_mate"] is None:
        board = _board_at_ply(pgn_text, mid_pd["ply"])
        if board is not None:
            mid_eval_cp, mid_eval_mate = await engine_service.evaluate(board)
            eval_calls_made += 1
            if mid_eval_cp is None and mid_eval_mate is None:
                eval_calls_failed += 1
                sentry_sdk.set_context("eval", {"game_id": g_id, "ply": mid_pd["ply"]})
                sentry_sdk.set_tag("source", "import")
                sentry_sdk.set_tag("eval_kind", "middlegame_entry")
                sentry_sdk.capture_message("import-time engine returned None tuple", level="warning")
            else:
                await session.execute(
                    update(GamePosition)
                    .where(GamePosition.game_id == g_id, GamePosition.ply == mid_pd["ply"])
                    .values(eval_cp=mid_eval_cp, eval_mate=mid_eval_mate)
                )
```

**Step 3 — symmetric Sentry tag on existing endgame path:**
`sentry_sdk.set_tag("eval_kind", "endgame_span_entry")` added alongside the existing `set_tag("source", "import")` call in the endgame span-entry error branch.

**Key constraints verified:**
- `eval_calls_made += 1` appears exactly 2 times (endgame + middlegame paths)
- `eval_calls_failed += 1` appears exactly 2 times (mirrors made counter)
- No `asyncio.gather` introduced
- Sentry context for middlegame eval: only `game_id` and `ply` (no pgn/fen/user_id — T-78-18)
- T-78-17 lichess preservation guard in place

### Imports added

None new. All needed symbols (`update`, `GamePosition`, `_board_at_ply`, `engine_service`, `sentry_sdk`) were already imported from Phase 78 work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing test mocks missing 'phase' key**

- **Found during:** Task 2 GREEN implementation
- **Issue:** After adding `pd["phase"]` to the middlegame block in `import_service.py`, the existing test mocks in `test_import_service.py` and `test_import_service_eval.py` lacked a `"phase"` key. The resulting `KeyError` inside `_flush_batch` was caught by `run_import`'s outer `try/except`, silently marking jobs as FAILED and causing the batch to return 0 positions — `test_position_rows_include_move_san` asserted `len(captured_positions) == 3` but got 0.
- **Fix:** Added `"phase": 0` (for opening/non-endgame plies) or `"phase": 2` (for endgame plies, matching PHASE-INV-01 invariant) to all ply mock dicts in `_make_mock_processing_result`, `_make_endgame_plies`, `_make_two_class_plies`, and three inline ply dicts in `test_position_rows_include_move_san`.
- **Files modified:** `tests/test_import_service.py`, `tests/services/test_import_service_eval.py`

## TDD Gate Compliance

Plan 79-02 is `tdd="true"`. Gate sequence for both tasks:

| Task | RED commit | GREEN commit |
|------|-----------|-------------|
| Task 1 (SCHEMA-02) | `b6fb648` test(79-02): add failing tests for PlyData phase field | `07e6c22` feat(79-02): extend PlyData with phase field |
| Task 2 (PHASE-IMP-01) | `939263b` test(79-02): add failing tests for middlegame entry eval | `8e3f0c2` feat(79-02): bulk-insert payload writes phase, add middlegame entry eval |

Both RED gates failed as expected; both GREEN gates passed all new + existing tests.

## Known Stubs

None. All implementations are complete and non-placeholder.

## Threat Flags

None. This plan modifies the import pipeline to write an additional column and add one Stockfish eval call per game. No new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- `app/services/zobrist.py` — FOUND and modified (Task 1)
- `app/services/import_service.py` — FOUND and modified (Task 2)
- `tests/test_zobrist.py` — FOUND and modified (Task 1 TDD)
- `tests/services/test_import_service_eval.py` — FOUND and modified (Task 2 TDD)
- `tests/test_import_service.py` — FOUND and modified (Rule 1 bug fix)
- Commits: `b6fb648` (RED T1), `07e6c22` (GREEN T1), `939263b` (RED T2), `8e3f0c2` (GREEN T2)
- All 1075 tests pass (6 skipped), ty + ruff green on all modified files
