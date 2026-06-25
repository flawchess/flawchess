---
phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
plan: "01"
subsystem: backend
tags: [tactic-lines, pv-conversion, idor, python-chess, repository, schema]
dependency_graph:
  requires: []
  provides:
    - GET /library/flaws/{game_id}/{ply}/tactic-lines endpoint
    - TacticLinesResponse Pydantic schema
    - fetch_tactic_lines() repository function
    - PAYOFF_MAX_PLIES constant
  affects:
    - app/routers/library.py
    - app/repositories/library_repository.py
    - app/schemas/library.py
tech_stack:
  added: []
  patterns:
    - UCI→SAN conversion via python-chess _parse_pv() reuse
    - Sequential async queries (no asyncio.gather on single AsyncSession)
    - IDOR guard with 404 (not 403) on cross-user/missing flaw
    - board_fen() + ply parity → full FEN reconstruction
key_files:
  created:
    - tests/routers/test_library_tactic_lines.py
    - tests/repositories/test_library_tactic_lines_repo.py
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/routers/library.py
decisions:
  - "Return full FEN (with side-to-move from ply parity) from endpoint so chess.js needs no client-side ply arithmetic"
  - "PAYOFF_MAX_PLIES = 3 (midpoint of 2-4 band from CONTEXT.md)"
  - "allowed_moves[0] is the flaw move itself (prepended); positions[n+1].pv follows"
  - "Raw 0-based depths returned; display offset applied client-side via toDisplayDepthForOrientation()"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-24"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 3
status: complete
---

# Phase 135 Plan 01: Tactic Lines Backend Contract Summary

One-liner: `GET /library/flaws/{game_id}/{ply}/tactic-lines` returning IDOR-guarded display-ready SAN for both PV orientations via python-chess UCI→SAN conversion with payoff truncation.

## What Was Built

New backend endpoint for the Tactic Line Explorer (Phase 135). The endpoint joins `game_flaws` (FEN, tactic depth/motif) with `game_positions` at ply `n` (missed PV) and `n+1` (allowed PV), converts both UCI principal variation strings to SAN using python-chess, and returns a typed `TacticLinesResponse` with display-ready move lists, raw depths, motif strings, and a full FEN.

### New Symbols

- `TacticLinesResponse` (Pydantic model) in `app/schemas/library.py`: fields `missed_moves / missed_depth / missed_tactic_ply_index / missed_motif`, `allowed_moves / allowed_depth / allowed_tactic_ply_index / allowed_motif`, `position_fen`, `flaw_move_san`, `best_move_uci`, `flaw_ply`.
- `PAYOFF_MAX_PLIES: int = 3` named constant in `app/repositories/library_repository.py`.
- `_pv_to_san_list(board, pv)` module-private helper: returns `list[str] | None`.
- `_truncate_pv(sans, tactic_depth_raw)` module-private helper: caps at `tactic_depth + 1 + PAYOFF_MAX_PLIES`.
- `fetch_tactic_lines(session, *, user_id, game_id, ply)` async repository function.
- `GET /flaws/{game_id}/{ply}/tactic-lines` route (`get_tactic_lines`) in `app/routers/library.py`.

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Wave 0 failing tests (RED) — endpoint + repository scaffolds | bcd32186 |
| 2 | TacticLinesResponse schema + fetch_tactic_lines() repository | 2a28cd79 |
| 3 | GET /flaws/{game_id}/{ply}/tactic-lines route with IDOR guard | 46d5e174 |

## Decisions Made

1. **Full FEN from endpoint**: `board.fen()` (with side-to-move) returned rather than `board_fen()` alone; chess.js needs full FEN, and the ply parity computation belongs on the server where it already has the data.
2. **PAYOFF_MAX_PLIES = 3**: midpoint of the 2–4 band from CONTEXT.md (Claude's Discretion). Named constant, not a magic number (CLAUDE.md).
3. **allowed_moves[0] is the flaw move**: `game_positions[n+1].pv` starts AFTER the flaw move; the flaw move SAN is prepended from `game_positions[n].move_san` so the SAN ladder correctly shows "red error move → opponent punishment" starting at index 0 (Pitfall 3).
4. **Raw 0-based depths returned**: No offset applied in the repository. Client applies `toDisplayDepthForOrientation()` (Research Finding 2). `missed_tactic_ply_index == missed_depth` and `allowed_tactic_ply_index == allowed_depth`.
5. **No `capture_exception` on ValueError from `_parse_pv`**: Bad UCI in a stored PV is an expected/graceful case; returns `None` (T-135-04 accept disposition; CLAUDE.md skip expected exceptions).

## Verification Results

All acceptance criteria met:

- `GET /library/flaws/{game_id}/{ply}/tactic-lines` returns 200 with `TacticLinesResponse` fields for owned tagged flaw.
- Requesting another user's flaw returns 404 with `"Flaw not found"` (IDOR; T-135-01).
- Non-integer path params return 422 (FastAPI auto; T-135-02).
- No `white_hash`, `black_hash`, or `full_hash` in any response body (T-135-03).
- Short PVs (length < tactic_depth): no crash, returned as-is.
- NULL PVs: `missed_moves` / `allowed_moves` return `None` gracefully (Pitfall 4).
- Truncation: `missed_moves` length == `tactic_depth + 1 + PAYOFF_MAX_PLIES` for long PVs.

### Test Results

```
tests/routers/test_library_tactic_lines.py::test_200_shape PASSED
tests/routers/test_library_tactic_lines.py::test_404_wrong_user PASSED
tests/routers/test_library_tactic_lines.py::test_404_missing PASSED
tests/routers/test_library_tactic_lines.py::test_401_unauthenticated PASSED
tests/routers/test_library_tactic_lines.py::test_no_hash_leak PASSED
tests/repositories/test_library_tactic_lines_repo.py (5 tests) PASSED
Full backend suite: 2887 passed, 18 skipped
ruff check app/ tests/: clean
ty check app/ tests/: zero errors
```

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All fields are populated from real DB data; no placeholder values.

## Threat Flags

No new threat surface beyond what was planned in the STRIDE register (T-135-01 through T-135-04). All mitigations implemented and covered by tests.

## Self-Check: PASSED

- `app/schemas/library.py`: `class TacticLinesResponse` present (line 425).
- `app/repositories/library_repository.py`: `PAYOFF_MAX_PLIES = 3` present (line 88); `async def fetch_tactic_lines` present.
- `app/routers/library.py`: `/flaws/{game_id}/{ply}/tactic-lines` route present (line 363), no prefix duplication.
- Commits bcd32186, 2a28cd79, 46d5e174 verified in git log.
- All 10 new tests green; full suite green.
