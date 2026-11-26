---
phase: 250-facepalm-blunder-selection
plan: 05
subsystem: scoring
tags: [maia, facepalm-score, post-apply-hook, fingerprint, advisory-lock, game-flaws]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "plan 01 columns, line_facts, facepalm_score, reply_spread; plan 04 shipped FACEPALM_MODEL"
  - phase: 248-maia-refutation
    provides: "the post-blunder full_policy call and the refutation pair this hook now shares"
provides:
  - "score_game_flaws_after_apply writes maia_reply_spread, line_loss_1/3/5/7/9, line_mate_ply and facepalm_score for user-side blunders in every lane (D-07)"
  - "FacepalmStats / null_facepalm_stats, FACEPALM_COLUMNS, mark_facepalm_spread_completed / mark_facepalm_line_completed"
  - "7-element FlawFingerprint: the stored ply+1 line is part of the inputs fingerprint"
  - "clear_maia_flaws_completed clears all four stamps"
  - "assert_refutation_lane_state proves the facepalm stamps and spread in every lane"
affects: [250-06, 250-07, facepalm backfill, blunder-check selection, Phase 252 pv repair]

actuals:
  tokens: 14178
  tasks: 2
  commits: 2
plan_head_before: 3ed87f7f47437409a2b4a8b63aa6317ea9b6a064
plan_head_after: 5bc1a2d40a380cc2883c8e113da91dfda5ba5ce5

tech-stack:
  added: []
  patterns:
    - "One post-blunder inference feeds both the refutation pair and the reply spread; the spread never waits on the reply guard"
    - "A derived stored line joins the per-game fingerprint so a repair that keeps the first token is still detected"
    - "Full mode emits every derived key for every flaw (None out of scope), so a re-score clears stale values by writing"

key-files:
  created: []
  modified:
    - app/services/maia_flaw_scoring.py
    - app/services/maia_flaw_stats.py
    - app/repositories/game_flaws_repository.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/services/maia_fakes.py

key-decisions:
  - "The refutation-mode (Phase 248 D-10) rows still emit only the pair; the shared _derive_post_blunder drops the spread there, so refutation mode now spends the post-board inference for an unusable reply too"
  - "_flaw_board takes (flaw, boards) instead of the plan's (inputs, flaw, boards): inputs was unused there"
  - "FlawMaiaInput.refutation_pv is a required field (no default) so a caller cannot silently omit the line from the fingerprint"

patterns-established:
  - "_scope_facepalm: the D-06 gate lives in one helper; line facts for a user blunder need only the board and the stored line"
  - "Lane helper asserts a stamped game has all four stamps and a non-NULL spread on every user blunder with a legal reply"

requirements-completed: [D-01, D-05, D-06, D-07]

coverage:
  - id: E1
    description: "A user blunder scored by the post-apply hook carries spread, six line columns and score, and the game holds all four stamps"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_facepalm_tracer_user_blunder_scored_and_four_stamps"
        status: pass
    human_judgment: false
  - id: E2
    description: "D-06 scope: only user-side blunders get values; user mistakes, opponent blunders and a row downgraded from blunder carry NULL in all eight columns"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_facepalm_scope_non_user_rows_null, test_facepalm_full_rescore_clears_row_downgraded_from_blunder"
        status: pass
    human_judgment: false
  - id: E3
    description: "Guard order: the spread is scored with an unusable reply (pair NULL), is NULL for a stalemating blunder, line facts survive a missing rating, a missing line leaves only the score NULL"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_unusable_reply_keeps_pair_null_but_scores_spread, test_facepalm_stalemating_blunder_has_null_spread, test_facepalm_no_rating_keeps_line_facts_only, test_facepalm_missing_line_leaves_score_null, test_refutation_call_count_is_base_plus_scorable_user_blunders"
        status: pass
    human_judgment: false
  - id: E4
    description: "A changed stored line between read and write gives fingerprint_changed and writes nothing (mutation-checked)"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_facepalm_line_change_is_fingerprint_changed"
        status: pass
    human_judgment: false
  - id: E5
    description: "Reclassification keeps survivors' facepalm values, inserts new plies NULL and clears all four stamps; clear helper reports any of the four"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py -k reclassify (10 passed), test_reclassify_clear_helper_clears_all_four_stamps"
        status: pass
    human_judgment: false
  - id: E6
    description: "Every lane (full drain, atomic submit, blob submit) proves both facepalm stamps and the spread through the shared assertion helper"
    requirement: "D-07"
    verification:
      - kind: integration
        ref: "uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -k 'maia or refutation' (12 passed)"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 05: Facepalm Scoring in the Post-Apply Maia Hook Summary

**New games' user blunders now arrive with a Maia reply spread, line material facts and a facepalm score, from the one post-blunder inference the hook already ran, guarded by a line-aware fingerprint and four-stamp reclassification**

## Performance

- **Duration:** 9 min
- **Started:** 2026-11-13T20:09:38Z
- **Completed:** 2026-11-13T20:19:25Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `_derive_post_blunder` replaces `_derive_refutation`: one `full_policy` call on the post-blunder board yields the reply spread (`reply_spread`) and the Phase 248 refutation pair. The spread no longer waits on the reply guard, so a missing, malformed or illegal reply leaves only the pair NULL.
- `_facepalm_values` runs `line_facts` on the replayed pre-board and the stored ply+1 line, then `facepalm_score` with the default `FACEPALM_MODEL`; `_scope_facepalm` applies the D-06 gate. Full mode writes all eight keys for every flaw, so a re-score clears a row downgraded from blunder.
- The stored line (`gp_next.pv`) is the seventh fingerprint element: a line changed between read and write (Phase 252 repair, first token kept, `best_move` still present) is `fingerprint_changed` and nothing is written.
- Full mode stamps `facepalm_spread_completed_at` and `facepalm_line_completed_at` together with the two Maia stamps; `clear_maia_flaws_completed` clears all four and returns True when any was set.
- `assert_refutation_lane_state` now proves the four stamps and the spread on every user blunder with a legal reply, so the full drain, atomic submit and blob submit lanes are all covered without touching their test files.

## Task Commits

1. **Task 1: Tracer, one user blunder scored end to end by score_game_flaws_after_apply** - `318ad9f95` (feat)
2. **Task 2: Guard order, D-06 scope, the line in the fingerprint, reclassification and every lane** - `5bc1a2d40` (test, plus the `clear_maia_flaws_completed` change)

**Plan metadata:** committed separately (docs: complete plan)

Tracer gate: `human_verify_mode` is `end-of-phase` and the tracer's `<verify>` is automated-only, so it was re-run after the Task 1 commit (tracer test and both module suites pass). Tracer verified end-to-end, expanded.

## Files Created/Modified

- `app/services/maia_flaw_scoring.py` - `_derive_post_blunder`, `_facepalm_values`, `_scope_facepalm`, `_flaw_board`, 7-element fingerprint, four-stamp full-mode write, docstrings
- `app/services/maia_flaw_stats.py` - `FacepalmStats`, `null_facepalm_stats`
- `app/repositories/game_flaws_repository.py` - `FACEPALM_COLUMNS`, `mark_facepalm_spread_completed`, `mark_facepalm_line_completed`, four-stamp `clear_maia_flaws_completed`
- `tests/services/test_maia_flaw_scoring.py` - tracer, scope, no-rating, missing-line, stalemate, line-change fingerprint, downgrade, reclassify and clear-helper tests
- `tests/services/maia_fakes.py` - facepalm assertions in `assert_refutation_lane_state`

## Decisions Made

- Refutation mode (D-10) shares `_derive_post_blunder` and keeps writing only the pair. Consequence: an unusable reply in refutation mode now also spends the post-board inference (the spread is computed and dropped). The plan's own function split implies this; the backfill that uses refutation mode is a one-off.
- `_flaw_board(flaw, boards)` drops the unused `inputs` parameter the plan listed.
- `FlawMaiaInput.refutation_pv` has no default so a new construction site cannot forget it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing tests encoded the old "no inference for an unusable reply" rule**
- **Found during:** Task 1 (first run of the module after the hook change)
- **Issue:** `test_refutation_unusable_reply_leaves_null_without_inference` (1 call), `test_refutation_call_count_is_base_plus_scorable_user_blunders` (4 calls) and `test_replay_castling_and_ep_fen` (1 call; its white user blunder at ply 4 now also spends a post-board call) asserted the superseded count.
- **Fix:** Renamed the first to `test_unusable_reply_keeps_pair_null_but_scores_spread` (2 calls, spread set), set the count test to 5 (plies 2 and 8 both spend a post-board call), and made the en-passant replay test use a black user so ply 4 is the opponent's blunder. This is the deliberate update the plan asked for, done in the Task 1 commit because its verify runs the whole module.
- **Files modified:** tests/services/test_maia_flaw_scoring.py
- **Committed in:** 318ad9f95

**2. [Rule 3 - Blocking] `FlawMaiaInput` construction in `test_refutation_target_boards_are_never_mutated`**
- **Found during:** Task 1
- **Issue:** the new required `refutation_pv` field broke the test's constructor call.
- **Fix:** passes the field; Task 2 extended the same test with a real stored line so the line walk runs and asserts `line_loss_1` is set while the boards stay unmutated.
- **Committed in:** 318ad9f95, 5bc1a2d40

---

**Total deviations:** 2 auto-fixed (1 bug in dependent tests, 1 blocking)
**Impact on plan:** Both are consequences of the planned behavior change. No scope creep.

## Issues Encountered

None.

## Verification

- `uv run pytest tests/services/test_maia_flaw_scoring.py tests/services/test_maia_flaw_stats.py -x`: 75 passed.
- `uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -x -k "maia or refutation"`: 12 passed.
- `uv run pytest -n auto -q`: 6281 passed, 19 skipped.
- `uv run ty check app/ tests/ scripts/`: all checks passed. `ruff format --check` and `ruff check .` clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: `_derive_refutation` 0 occurrences, `def _derive_post_blunder` 1, `gp_next.pv` 2, `flaw_record_to_row` source contains no `FACEPALM_COLUMNS` key (exit 0).
- Mutation checks (each restored afterwards):
  - `f.refutation_pv` replaced by `None` in `fingerprint_of`: `test_facepalm_line_change_is_fingerprint_changed` fails.
  - Facepalm stamps removed from the `clear_maia_flaws_completed` UPDATE: 5 reclassify and clear-helper tests fail.
  - Spread forced to `None` in `_derive_post_blunder`: 3 lane tests (drain, atomic submit, blob submit) fail through `assert_refutation_lane_state`.

## Known Stubs

None.

## Threat Flags

None. T-250-13 holds (`line_facts` never raises on bad tokens, the hook keeps its catch-all with `capture_exception` and `set_context`), T-250-14 mitigated and mutation-checked, T-250-15 mitigated (all eight keys for every flaw in full mode, four-stamp clear, reclassify tests).

## Next Phase Readiness

- The backfill (plan 07) can reuse `score_game` full mode and the four stamps unchanged (D-08).
- Blunders whose stored line is shorter than `LINE_DEPTH` plies keep a NULL score by design until the D-18 refit, as carried forward from plan 04; the hook writes their spread and any settled line facts.

## Self-Check: PASSED

Both task commits (`318ad9f95`, `5bc1a2d40`) are ancestors of HEAD (measured count 2 from the ledger base `3ed87f7f4`); all five modified files exist; full suite, ty, ruff and the depth gate are clean.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
