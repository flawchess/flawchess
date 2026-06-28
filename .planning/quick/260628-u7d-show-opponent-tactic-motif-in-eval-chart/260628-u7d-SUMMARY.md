---
phase: quick-260628-u7d
plan: "01"
subsystem: library
tags: [tactic, eval-chart, opponent, library-service, repository]
dependency_graph:
  requires: []
  provides: [opponent-tactic-markers-in-eval-chart]
  affects: [library_service, library_repository, query_utils]
tech_stack:
  added: []
  patterns: [ungated-both-color-fetch, ply-parity-helper, tactic-by-ply-map]
key_files:
  created: []
  modified:
    - app/repositories/query_utils.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - tests/services/test_library_service.py
decisions:
  - "Separate ungated fetch (fetch_page_game_flaws_both_colors) keeps player-gated fetch (fetch_page_game_flaws) unchanged — zero risk of counts/chips/EXISTS leakage"
  - "mover_is_white_at_ply derives from _PLY_EVEN_MOVER_WHITE constant (single source) instead of game.user_color assumption"
  - "tactic_flaw_rows keyword param defaults to None — all existing callers get exact prior behavior with no changes required"
metrics:
  duration_minutes: 25
  completed_at: "2026-06-28T20:00:34Z"
  tasks_completed: 3
  files_changed: 4
status: complete
---

# Phase quick-260628-u7d Plan 01: Opponent Tactic Motif in Eval Chart Summary

Backend change that populates opponent (hollow-square) blunder/mistake markers in the eval-chart tooltip with their tactic motif chips, using an ungated both-color DB fetch while keeping all player-gated surfaces (severity counts, curated chips, Games-tab EXISTS filter, stats) byte-for-byte unchanged.

## What Was Built

### One-liner
Ungated both-color flaw fetch feeds tactic_by_ply for opponent marker tooltips; player-gated fetch still owns all aggregate surfaces.

### Task Breakdown

**Task 1 — query_utils.py + library_repository.py**

- Added `mover_is_white_at_ply(ply: int) -> bool` to `query_utils.py`. Derives from `_PLY_EVEN_MOVER_WHITE = 0` constant (the existing single-source convention) so Python read-path and SQL path agree on ply parity. Docstring notes it mirrors `is_opponent_expr`.

- Added `fetch_page_game_flaws_both_colors(session, user_id, game_ids)` to `library_repository.py` directly below `fetch_page_game_flaws`. Identical shape and IDOR scope (`GameFlaw.user_id == user_id`) but omits the `player_only_gate` and the `Game` JOIN (which existed solely to bring `user_color` into scope for that gate). Loud docstring/warning: this variant is TOOLTIP-ONLY and must not feed counts, chips, filter, or stats.

**Task 2 — library_service.py**

- Added `tactic_flaw_rows: list[GameFlaw] | None = None` keyword-only parameter to `_build_card` (after `max_tactic_depth`). When `None`, the function falls back to `flaw_rows` so all existing callers keep exact prior behavior.

- `tactic_by_ply` construction loop now iterates `tactic_flaw_rows if tactic_flaw_rows is not None else flaw_rows` (i.e., the both-color rows when provided), enabling opponent ply entries to populate the map.

- Fixed `mover_is_white` in `is_decided_lost` call: replaced the assumption `(game.user_color == "white")` with `mover_is_white_at_ply(fr.ply)`. For player rows this equals the old value; for opponent rows it gives the actual mover color, so the decided-lost gate is correct for both.

- `mistake_count`/`blunder_count` sums and `_curate_chips_from_rows` still iterate the player-gated `flaw_rows` parameter (the landmine guard).

- `get_library_game`: sequential fetch of `tactic_flaw_rows` via `fetch_page_game_flaws_both_colors` after existing `flaw_rows` fetch; passed as `tactic_flaw_rows=` to `_build_card`.

- `get_library_games`: batch-fetch `page_tactic_flaws` for the page after `page_flaws`; passed per-game to `_build_card`.

**Task 3 — tests/services/test_library_service.py**

Added `TestOpponentTacticMarker` with two DB-backed tests:

1. `test_opponent_tactic_motif_on_hollow_square_marker` — uses `get_library_game`. Seeds user blunder at ply 2 (even, white) and opponent blunder at ply 3 (odd, black) with confident tactic motifs. Asserts: opponent marker carries `allowed_tactic_motif='fork'`; user marker unchanged; `severity_counts["blunder"] == 1` (landmine guard); `chips == []` (player-gated).

2. `test_opponent_tactic_motif_via_get_library_games` — same setup via `get_library_games` (page-list path) to confirm the `page_tactic_flaws` batch-fetch wiring.

Position sequence: eval rises from `curr_b` back to 0 at ply 3 (black "gave back" the advantage), producing a genuine black blunder via `_run_all_moves_pass`. Uses `_cp_for_white_drop(BLUNDER_DROP)` and named constants (no magic numbers per CLAUDE.md).

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `uv run ty check app/ tests/` — all checks passed
- `uv run ruff check app/ tests/ --fix` — all checks passed
- `uv run ruff format app/ tests/` — 1 test file reformatted (style commit added)
- `uv run pytest -n auto tests/services/test_library_service.py` — 34 passed
- `uv run pytest -n auto -x` — 2918 passed, 18 skipped (full backend suite)
- Frontend: zero files changed — no frontend gate run required

## Known Stubs

None — opponent tactic fields are fully wired from DB to tooltip.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes. Read-only addition of an ungated query variant; IDOR scope (`GameFlaw.user_id == user_id`) preserved.

## Self-Check: PASSED

Files exist:
- app/repositories/query_utils.py — modified (mover_is_white_at_ply)
- app/repositories/library_repository.py — modified (fetch_page_game_flaws_both_colors)
- app/services/library_service.py — modified (_build_card + callers)
- tests/services/test_library_service.py — modified (TestOpponentTacticMarker)

Commits exist:
- 694c67ad: feat(quick-260628-u7d): add ungated both-color flaw fetch + ply-parity helper
- 4850ae5a: feat(quick-260628-u7d): build tactic_by_ply from both-color rows, keep counts/chips player-gated
- 7fb3c3f4: test(quick-260628-u7d): opponent tactic populated + severity-count landmine guard
- 458ece6b: style(quick-260628-u7d): apply ruff format to test file
