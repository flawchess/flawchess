---
phase: 259-facepalm-first-principles-refit
plan: 05
subsystem: database
tags: [alembic, backfill, maia, facepalm, postgres, game-stamps]

requires:
  - phase: 259-04
    provides: "FACEPALM_REPLY_COLUMNS, _post_blunder_policy, _reply_prob, refutation_reply_uci, FULL_ROW_COLUMNS"
provides:
  - "migration d2a6c8e0f259: games.facepalm_reply_completed_at (TIMESTAMPTZ NULL), applied to the dev DB"
  - "backfill_maia_flaws.py --mode reply: one post-blunder inference per blunder of either side with a stored played probability, writes only maia_best_reply_prob, stamps only the reply stamp"
  - "full mode sets five stamps; clear_maia_flaws_completed clears five"
  - "--status --mode reply readiness counts and --status --mode line material-input counts"
affects: [259-06, 259-09, reply-backfill, line-pass]

actuals:
  tokens: 12300
  tasks: 2
  commits: 2
plan_head_before: 0e33264a8ba4315348f95404dda56a5532c97cd8
plan_head_after: cad7ef63d156581925f22a675e64431b7b443a0e
commits: 2

tech-stack:
  added: []
  patterns:
    - "reply mode scope = blunders of both sides with stored_played_prob set (the hook's own scorable test), no stamp-independent row predicate"
    - "a mode that writes one column carries its own game stamp; full mode sets every stamp"

key-files:
  created:
    - alembic/versions/20261122_130000_d2a6c8e0f259_phase_259_facepalm_reply_stamp.py
  modified:
    - app/models/game.py
    - app/repositories/game_flaws_repository.py
    - app/services/maia_flaw_scoring.py
    - scripts/backfill_maia_flaws.py
    - tests/scripts/test_backfill_maia_flaws.py
    - tests/services/maia_fakes.py
    - tests/services/test_maia_flaw_scoring.py

key-decisions:
  - "reply_probs_null in the shard report counts user_blunders + opponent_blunders minus reply_probs_set, so it covers blunders that spent no inference (no refutation line) as well as unscorable ones"
  - "Status residues are restricted to rows the hook scored (maia_played_prob set), matching the reply mode's own scope"

patterns-established:
  - "Single-column backfill modes assert in a tracer test that every other column and stamp is unchanged"

requirements-completed: [D-07, D-10, D-11]

coverage:
  - id: D1
    description: "Reply mode fills maia_best_reply_prob for user and opponent blunders with one post-blunder inference each (none without a refutation line), stamps only facepalm_reply_completed_at, changes no other column or stamp, and a second run selects 0 games"
    requirement: "D-07, D-10, D-11"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_reply_mode_fills_both_sides_and_stamps"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full mode sets all five stamps, reply mode only its own, spread/line/pre/opponent never the reply stamp, and the clear helper clears all five"
    requirement: "D-11"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_full_mode_sets_the_reply_stamp"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_reply_mode_sets_only_the_reply_stamp_and_no_other_mode_sets_it"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py#test_clear_helper_clears_five_stamps"
        status: pass
    human_judgment: false
  - id: D3
    description: "--status --mode reply prints stamp counts, both-sides blunder counts and the three readiness residues; --status --mode line also prints the material-input counts of both sides"
    requirement: "D-11"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_reply_status_counts_and_residues"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_line_status_prints_material_input_counts"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dev schema at d2a6c8e0f259 and the dev status command runs SELECT-only against the dev DB"
    verification:
      - kind: other
        ref: "uv run alembic current prints d2a6c8e0f259 (head); uv run python scripts/backfill_maia_flaws.py --db dev --status --mode reply --user-id 28"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-11-21
status: complete
---

# Phase 259 Plan 05: Facepalm reply stamp and reply backfill mode (R1, part two) Summary

**`backfill_maia_flaws.py --mode reply` fills maia_best_reply_prob for blunders of both sides, one post-blunder inference each, behind its own resumable game stamp (migration d2a6c8e0f259), with the status counts the readiness gate reads.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-11-21T16:44:01Z
- **Completed:** 2026-11-21T17:04:00Z
- **Tasks:** 2
- **Files modified:** 8 (1 created)

## Accomplishments

- Instant migration adds `games.facepalm_reply_completed_at`; model column and `mark_facepalm_reply_completed` added; dev DB is at `d2a6c8e0f259`.
- Reply mode: `_reply_row` / `_reply_values` write PK plus `FACEPALM_REPLY_COLUMNS` only; a stored refutation line without a first token spends no inference and counts `reply_missing`. The reply stamp is the checkpoint (`_REPLY_PENDING_CLAUSE`, a constant shared by selector and status), so a relaunch after the prod reboot resumes and a second run selects 0 games.
- Full mode sets the reply stamp with the other four; `clear_maia_flaws_completed` clears five, so a reclassified game is re-scored by every pass.
- Status: `--mode reply` prints `reply_stamped_games`, `reply_pending_games`, `blunders_total`, `blunders_with_reply_prob`, `reply_residue_losing`, `unscored_pure_miss_no_best`, `blunders_without_material_inputs`; `--mode line` appends `user_blunders_with_material_inputs` and `opponent_blunders_with_material_inputs`.
- Module docstring documents the prod commands (12 workers ceiling, no overlapping operator run).

Dev status output (user 28, nothing run on it, only a SELECT):
`reply_stamped_games=0 reply_pending_games=5311 blunders_total=21180 blunders_with_reply_prob=0 reply_residue_losing=0 unscored_pure_miss_no_best=0 blunders_without_material_inputs=21180`

## Task Commits

1. **Task 1: tracer, one seeded game through `--mode reply`** - `6f0ac3f6c` (feat)
2. **Task 2: stamps of every lane, clear helper, status counts** - `cad7ef63d` (feat)

**Plan metadata:** recorded in the follow-up docs commit (SUMMARY, STATE, ROADMAP).

## Files Created/Modified

- `alembic/versions/20261122_130000_d2a6c8e0f259_phase_259_facepalm_reply_stamp.py` - adds the stamp column, downgrade drops it
- `app/models/game.py` - `Game.facepalm_reply_completed_at`
- `app/repositories/game_flaws_repository.py` - `mark_facepalm_reply_completed`, clear helper over five stamps
- `app/services/maia_flaw_scoring.py` - `"reply"` mode, `_reply_row`, `_reply_values`, `GameMaiaScore.reply_probs_set`, reply stamp wiring (also set by full mode)
- `scripts/backfill_maia_flaws.py` - `--mode reply`, `_REPLY_PENDING_CLAUSE`, `_fetch_reply_status`, `_blunder_count_stmt`, material-input counts, report fields `reply_probs_set` / `reply_probs_null`
- `tests/scripts/test_backfill_maia_flaws.py`, `tests/services/test_maia_flaw_scoring.py`, `tests/services/maia_fakes.py` - tracer, stamp, clear-helper and status tests; existing five-stamp pins updated

## Decisions Made

- The shard report's `reply_probs_null` is blunders (both sides) minus those carrying a reply probability, so blunders without a refutation line (no inference) show up in it next to `reasons["reply_missing"]`.
- Status residues are limited to rows with `maia_played_prob` set, the same scope the reply pass uses.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing tests pinned four stamps**
- **Found during:** Task 2
- **Issue:** `test_hook_full_mode_still_stamps` asserted `len(stamps) == 4`, and the clear-helper docstrings and param test named four stamps.
- **Fix:** Updated to five (`_STAMP_COLUMNS` gained the reply stamp; `maia_fakes.assert_maia_lane_state` asserts it too, as the plan said).
- **Files modified:** tests/services/test_maia_flaw_scoring.py, tests/services/maia_fakes.py
- **Committed in:** `cad7ef63d`

**2. [Rule 1 - Bug] Duplicate module constant in the new test block**
- **Found during:** Task 2
- **Issue:** My first draft redefined `_LINE_AFTER_PLY_5`, already defined (identically) earlier in the module.
- **Fix:** Removed the duplicate before committing.
- **Committed in:** `cad7ef63d`

**3. TDD note (Task 2 `tdd="true"`):** the clear-helper and full-mode stamp production code landed in the Task 1 commit (the model and stamp wiring are needed for the tracer to run), so Task 2 has no separate RED commit. The tests were proven by mutation instead: removing the reply stamp from `_mark_stamps` fails the tracer, and removing the reply stamp from the clear helper fails 3 clear-helper tests; both reverted.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug), 1 TDD-order note. **Impact:** none on scope.

## Issues Encountered

The full backend suite (`uv run pytest -n auto -x`) was auto-backgrounded by the harness after 180 s; it finished on its own: 7405 passed, 19 skipped (176 s).

## Known Stubs

None.

## Threat Flags

None: the migration is catalog-only; the mode picks a constant SQL clause and the cutoff stays the only bound parameter (T-259-10); no new endpoint or trust boundary.

## Next Phase Readiness

- Plan 06 can run the reply pass on prod with the documented commands (12 workers max, strictly alone); it needs the dev/prod migration applied first (prod migration happens at the deploy, nothing was done on prod).
- Nothing was backfilled on dev beyond seeded test games; the dev DB has 5311 reply-pending games for user 28.

## Self-Check: PASSED

- Files: migration, SUMMARY and all modified files present on disk.
- Commits `6f0ac3f6c` and `cad7ef63d` are ancestors of HEAD; `plan_head_before..HEAD` = 2 commits.
- Gates: `alembic current` = `d2a6c8e0f259 (head)`, the 154 plan-scope tests then the full suite (7405 passed), `ty check app/ tests/ scripts/`, depth gate (OK, 1698 functions) and `ruff check` clean; dev status prints `reply_pending_games=`.

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-21*
