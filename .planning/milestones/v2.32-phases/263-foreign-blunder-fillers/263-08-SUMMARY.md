---
phase: 263-foreign-blunder-fillers
plan: 08
subsystem: api
tags: [train, legacy-filler, deletion, tests]

requires:
  - phase: 263-foreign-blunder-fillers
    provides: "263-07 composition without the lichess stage; 263-06 reveal server"
provides:
  - "DrillSource.LEGACY_SHARP_FILLER = 2 (renamed; value and 'sharp_filler' wire unchanged)"
  - "Legacy-only handling of source 2 rows: resume skip, completion exclusion, keyless solve classification, reveal not_found"
  - "app/services/sharp_filler.py, the CSV, the generator and their tests are deleted"
affects: [263-09, 263-10]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Retired source kept readable as history: the wire arm and the enum member stay, every serving branch goes"

key-files:
  created:
    - tests/repositories/test_train_legacy_filler.py
  modified:
    - app/models/drill_solve.py
    - app/repositories/train_repository.py
    - app/schemas/train.py
    - app/routers/train.py
    - app/services/train_pool.py
    - app/services/blunder_check_grading.py
    - app/repositories/blunder_check_repository.py
    - app/repositories/train_leaderboard_repository.py
    - app/services/guest_cleanup_service.py
    - tests/routers/test_train.py
    - tests/repositories/test_train_repository.py
    - tests/services/test_train_pool.py
  deleted:
    - app/services/sharp_filler.py
    - app/data/sharp_filler_puzzles.csv
    - scripts/gen_sharp_filler_set.py
    - tests/services/test_sharp_filler.py
    - tests/scripts/test_gen_sharp_filler_set.py

key-decisions:
  - "A legacy filler solve from a stale client is classified 'sharp' with no key and no vetted set, so _resolve_grade records the client's tier (no 404, no misgrade)"
  - "Reveal of a legacy row answers not_found (the set that held its FEN is gone); the router maps it to 404"
  - "PuzzleRevealResponse.motif is deleted; the frontend never read it, so no frontend change was needed"

requirements-completed: [D-03, D-08]

duration: 50min
completed: 2026-11-23
status: complete
plan_head_before: afc03f595853d495bfd27aeea622285dc46bb0fd
plan_head_after: d088760c490506ebb43cc6f3900187940b37232f
commits: 2
---

# Phase 263 Plan 08: Legacy filler rows inert, lichess set deleted Summary

**The ~795 solved source 2 history rows still count and serialize as `sharp_filler`; nothing can serve a lichess filler any more: the CSV, the service and the generator are gone, and unsolved legacy rows are skipped on resume, never pin a session open, and are not revealable.**

## Accomplishments

- Task 1 `17724e19a`: renamed `DrillSource.SHARP_FILLER` to `LEGACY_SHARP_FILLER` (value 2, word-boundary rename across app/tests/scripts) and rewrote the enum and module docstrings. `train_repository`: `load_session_puzzles` skips legacy rows; `_position_answer_key` and `_answer_keys_by_position` lost `sharp_puzzle_id`; `_classify_filler_solve` became `_classify_legacy_filler_solve` (sharp, no vetted moves, no key, fix-site comment on Pitfall 6); `reveal_for_puzzle` returns `not_found` for a legacy row and lost the sharp lookup, the filler FEN arm and `RevealedPuzzle.motif`; `_mark_session_complete_if_done` excludes every unsolved legacy row (fix-site comment on ruling 3); `_wire_source` keeps the `sharp_filler` arm. `PuzzleRevealResponse.motif` and `motif=` in the router are gone. All sharp-set fixtures and autouse patches were removed from the test files.
- Task 2 `d088760c4`: `git rm` of the five files; `answer_key_for` lost `filler_solution_uci` and its filler arm and `server_graded_moves_for` lost the filler condition (every caller updated); docstrings in `train_pool`, `blunder_check_repository`, `guest_cleanup_service`, `train_leaderboard_repository` rewritten. `fixtures/tagger/detector_fixture_*.csv` kept.

## Mutation checks (each reverted afterwards, file restored byte-for-byte)

| Mutation | Result |
| --- | --- |
| Completion clause back to `or_(source != LEGACY_SHARP_FILLER, sharp_puzzle_id IS NOT NULL)` | `test_unsolved_legacy_filler_never_pins_session_open` fails |
| Remove the `not_found` return for a legacy row in `reveal_for_puzzle` | `test_reveal_legacy_filler_not_found` fails |
| `_classify_and_certify_solve` legacy arm replaced by a soft classification | `test_record_solve_on_legacy_filler_records_client_tier` fails |
| Remove the `continue` in `load_session_puzzles` | NOT caught: `test_unsolved_legacy_filler_skipped_on_resume` still passes |

The fourth result is expected rather than a gap in the test: a legacy row always has `game_id` NULL, so the generic `if game is None: continue` below already drops it. The explicit skip is a defensive guard that only matters for a legacy row that (never in prod) carries a game link. Left as is, per the plan.

## Tests

- New module `tests/repositories/test_train_legacy_filler.py` (5): `test_unsolved_legacy_filler_skipped_on_resume`, `test_unsolved_legacy_filler_never_pins_session_open`, `test_resume_serializes_solved_legacy_filler_as_sharp_filler`, `test_record_solve_on_legacy_filler_records_client_tier`, `test_reveal_legacy_filler_not_found`.
- New elsewhere (3): `test_reveal_legacy_filler_returns_404` (routers/test_train.py, replaces the old filler reveal test), `test_answer_key_for_foreign_blunder_takes_the_sr_branch` (2 params), `test_server_graded_moves_for_foreign_blunder_takes_the_sr_branch`.
- Deleted (subject gone):
  - `test_reveal_sharp_filler_reports_sharp_filler_source` (rewritten as the 404 test)
  - `test_record_solve_sharp_filler_returns_empty_vetted_moves` (moved into the new module as the client-tier test)
  - `TestAnswerKeyFor::test_sharp_filler` (2 params) and `TestServerGradedMovesFor::test_sharp_filler_is_empty` in test_train_pool.py
  - Fixtures/helpers: `_TEST_SHARP_PUZZLES`, `_install_sharp_fixture`, `_default_empty_sharp_set` (test_train_repository.py, routers/test_train.py), `_empty_sharp_set` (test_cross_mode_cooldown.py), `_empty_lichess_sharp_set` (repositories and routers test_train_foreign.py), the inline patch in test_imports_router.py
  - `tests/services/test_sharp_filler.py`: test_missing_file_raises_runtime_error, test_header_only_file_raises_runtime_error, test_comment_lines_are_skipped_before_the_header, test_committed_file_loads_successfully, test_ascending_puzzle_id_order, test_user_id_independent_signature, test_excludes_already_served_ids, test_repeats_when_every_id_served, test_limit_larger_than_pool_returns_everything_available, test_served_sharp_ids_stmt_returns_only_this_users_sharp_filler_ids, test_sharp_filler_available_true_for_the_real_committed_set, test_at_least_200_rows, test_puzzle_ids_are_unique, test_exactly_13_motifs_all_drawn_from_motif_labels, test_every_motif_row_count_between_floor_and_cap, test_rating_within_band, test_no_row_carries_a_mate_theme, test_ply_parity_matches_side_to_move_and_fen, test_solution_uci_is_legal_in_its_own_fen, test_first_move_uci_is_consistent_with_the_position_it_arrives_at, test_sharp_filler_data_path_resolves_under_app_data, test_no_app_module_references_the_tagger_fixture_path
  - `tests/scripts/test_gen_sharp_filler_set.py`: test_sharpness_gate_boundary_value_passes, test_sharpness_gate_just_below_boundary_fails, test_sharpness_gate_well_above_boundary_passes, test_sharpness_gate_literal_acceptance_example, test_returns_earlier_target_motif_when_two_present, test_returns_none_for_endgame_only_themes, test_returns_none_when_no_target_motif_present, test_priority_order_matches_first_match_in_target_motifs, test_every_target_motif_is_individually_selectable, test_white_to_move_fullmove_12, test_black_to_move_fullmove_12, test_mate_in_2_row_is_excluded, test_out_of_band_rating_is_excluded, test_non_short_pv_is_excluded, test_endgame_promotion_only_row_is_excluded, test_duplicate_puzzle_id_across_fixtures_is_deduped, test_multi_motif_row_assigned_to_earlier_priority_motif_only, test_groups_are_sorted_ascending_by_puzzle_id
- Kept on purpose: `test_resume_solved_results_*` (solved legacy row serialization in test_train_repository.py) and the leaderboard/progress/medals/activity tests that seed source 2 history rows; only `sharp_puzzle_id=None` keyword arguments were dropped.

## Deviations from Plan

**1. [Judgment] `filler_solution_uci=None` kept at the four train_repository call sites during Task 1.** The parameter is removed in Task 2 as the plan orders it; Task 1 only stopped passing a real value, so each commit is independently green.

**2. [Rule 1] Reworded one docstring in app/schemas/train.py** ("a motif" to "a tactic label") so the plan's `git grep -w motif` acceptance check exits 0; the sentence is about the archive card and is otherwise unchanged.

No other deviations. The wire Literal `DrillSourceWire` is untouched (`'sharp_filler'` kept), and the frontend never read `PuzzleRevealResponse.motif`, so no frontend gate or `gen_*` script was needed.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-263-19 (completion exclusion), T-263-20 (wire arm kept) and T-263-21 (keyless legacy classify) are implemented and covered by the new module.

## Verification observed

- Full backend suite after the last edit: `uv run pytest -n auto -q`: 7062 passed, 9 skipped (was 7098 passed at the start of the plan; the net drop of 36 is the deleted test files and test cases listed above, offset by the new ones).
- Serial runs: `test_train_legacy_filler.py`, `test_train_pool.py`, both `test_train_foreign.py`, `test_imports_router.py`: 213 passed; `test_train_repository.py`, `routers/test_train.py`, `test_cross_mode_cooldown.py`, `test_train_leaderboard_repository.py`: 352 passed.
- Task 1 suites (`tests/repositories tests/routers tests/services` plus the three single files): 3969 passed, 8 skipped.
- `ruff check`, `ruff format` clean, `ty check app/ tests/ scripts/` clean, `check_function_size.py app/ --fail-over-depth 4`: 1700 functions, no breaches.
- Acceptance greps: no `SHARP_FILLER` word, no `SHARP_SET_BY_ID` in app/repositories or tests, no `motif` word in schemas/train.py, routers/train.py, train_repository.py; `LEGACY_SHARP_FILLER` appears 7 times in train_repository.py; the five files are absent; no `filler_solution_uci`, `SHARP_SET`, `_install_sharp_fixture` or sharp_filler import in app/scripts/tests.

## Self-Check: PASSED

- 17724e19a and d088760c4 are ancestors of HEAD; `tests/repositories/test_train_legacy_filler.py` exists; the five deleted files are absent.
