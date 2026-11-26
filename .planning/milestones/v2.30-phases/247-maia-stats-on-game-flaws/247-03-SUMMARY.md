---
phase: 247-maia-stats-on-game-flaws
plan: 03
subsystem: maia-flaw-scoring
tags: [maia, game_flaws, reclassify, eval-apply, operator-scripts]
requires: ["247-02"]
provides:
  - "game_flaws_repository.clear_maia_flaws_completed(session, game_id) -> bool"
  - "eval_apply._classify_and_fill_oracle(...) -> bool (True when it cleared the Maia stamp)"
  - "backfill_flaws.py (default branch + --oracle-gap) and opening_cache_repair.py rederive clear the stamp and print the D-11 reminder"
affects: [247-04, 247-05]
status: complete
commits: 2
plan_head_before: fb60b84fa451f8291499ad63ed7da0a50c46c4d3
plan_head_after: 8ee3b40a949bd3f727a241f8c1622689f5d3a92e
actuals:
  tokens: 6500
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "stamp cleared at the one reclassify choke point (_classify_and_fill_oracle), right after the 4-way diff/upsert, in the same transaction"
    - "survivor preservation by omission: Maia keys never appear in flaw_record_to_row, so neither update bucket names them in its SET clause"
key-files:
  created: []
  modified:
    - app/repositories/game_flaws_repository.py
    - app/services/eval_apply.py
    - scripts/backfill_flaws.py
    - scripts/opening_cache_repair.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/test_backfill_flaws.py
    - tests/scripts/test_opening_cache_repair.py
key-decisions:
  - "Stamp clear lives after _diff_upsert_flaw_rows and before the oracle-count refresh, so the defensive oracle-count early return still reports the clear"
  - "opening_cache_repair clears the stamp on the GameNotAnalyzed branch and commits before writing the failure row, because propagate already rewrote that game's opening best_move rows"
  - "make_game test fixture gained an optional evals mapping (default unchanged) so reclassify tests drive real classification"
requirements-completed: [D-09, D-11]
---

# Phase 247 Plan 03: Reclassify without Maia Summary

Every reclassification that runs without a Maia session now leaves correct Maia data: surviving flaw plies keep their eight values, new plies start NULL, removed plies vanish, and the game's `maia_flaws_completed_at` is cleared so the re-runnable backfill re-scores it. The operator scripts print the D-11 catch-up reminder.

## Accomplishments

- `clear_maia_flaws_completed` (repository): `UPDATE games ... WHERE id = :id AND maia_flaws_completed_at IS NOT NULL RETURNING id`; returns whether a stamp was actually cleared.
- `_classify_and_fill_oracle` now returns `bool`. It returns False for a missing game and for `GameNotAnalyzed` (stamp untouched), and the clear result otherwise (including the defensive oracle-count early return). The Maia keys were deliberately NOT added to `flaw_record_to_row` or `FLAW_BLOB_AND_TACTIC_COLUMNS`.
- A Maia-loaded apply composes with plan 02: classify clears inside the write transaction, the post-commit scorer re-stamps (covered by the existing drain tracer `test_full_drain_tick_maia_flaw_scores_and_stamps`, still green).
- `backfill_flaws.py`: default delete-then-insert branch clears the stamp per rewritten game (dry-run never does) and counts them; `--oracle-gap` threads `(filled, maia_unstamped)` out of `_rederive_oracle_gap_game`, `run_oracle_gap` takes `db`. Both print `format_maia_backfill_reminder` when the count is above zero.
- `opening_cache_repair.py`: `_rederive_reclassify_game` returns a 5-tuple, `_rederive_one_game -> bool`, `_walk_rederive -> (processed, unstamped)`, `run_rederive` prints the reminder. The GameNotAnalyzed branch clears the stamp and commits before writing the failure row.

## Tests

- `tests/services/test_maia_flaw_scoring.py`: `test_reclassify_without_maia_keeps_survivors_nulls_new_unstamps`, `test_reclassify_freshly_blobbed_survivor_keeps_values` (survivor lands in the fresh-blob bucket, `allowed_pv_lines` asserted non-NULL), `test_reclassify_not_analyzed_returns_false_keeps_stamp`, `test_reclassify_unknown_game_returns_false`. Seeds rows at {2, 7}, classification yields {2, 5}: 2 survives with all eight values, 5 is inserted all-NULL, 7 is deleted, stamp NULL, return True. Prior probabilities are exact binary fractions because the columns are REAL (float32).
- `tests/test_backfill_flaws.py::TestMaiaStampHandling`: default-branch unstamp plus one reminder line with count 1, dry-run keeps stamp and prints nothing, `--oracle-gap` unstamps and reminds.
- `tests/scripts/test_opening_cache_repair.py::TestRederive`: `test_rederive_maia_unstamps_and_reminds`, `test_rederive_not_analyzed_maia_clears_stamp` (repair row still ends `failed` with the GameNotAnalyzed error). The existing `test_rederive_failure` wrapper now returns the real classify value, and the lock test's task annotation became `Task[bool]`.

## Mutation proofs

- Replacing `clear_maia_flaws_completed(...)` in `_classify_and_fill_oracle` with `False`: `test_reclassify_without_maia_keeps_survivors_nulls_new_unstamps` and `test_reclassify_freshly_blobbed_survivor_keeps_values` failed on `assert datetime(...) is None` (the stamp survived). The not-analyzed and unknown-game tests passed. Restored: 4 passed.
- Adding `"maia_played_prob": None` to `flaw_record_to_row`'s dict: both survivor tests failed with `survivor must keep its Maia values` (`{'maia_played_prob': None} != {'maia_played_prob': 0.125}`), proving both update buckets are exposed to a Maia key and the omission is what protects them. Restored: 4 passed.
- Replacing the stamp clear in the `backfill_flaws.py` default branch with `if False`: `test_backfill_default_branch_maia_unstamps_and_reminds` failed on `assert datetime(...) is None`. Restored.
- Replacing the None-branch clear in `_rederive_one_game` with `False`: `test_rederive_not_analyzed_maia_clears_stamp` failed on `assert False is True`. Restored.

## Verification

- `uv run pytest -n auto -q`: 5744 passed, 20 skipped. Write-path goldens (`tests/services/test_flaw_upsert_equivalence.py`) unchanged and green. `test_lease_lifo` did not flake.
- `uv run ty check app/ tests/ scripts/`: All checks passed. `uv run ruff check .` clean, `ruff format --check app/ tests/ scripts/ analysis/` clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: `def clear_maia_flaws_completed` 1 hit; `maia_unstamped = await clear_maia_flaws_completed` 1 hit; `format_maia_backfill_reminder(` 2 hits in `backfill_flaws.py`, 1 in `opening_cache_repair.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing tests broken by the new return values**
- **Found during:** Task 2
- **Issue:** `test_rederive_failure`'s monkeypatched wrapper returned None (it did not forward the bool), which would fail `int(...)` in `_walk_rederive`, and `test_rederive_lock` annotated its task as `Task[None]` (ty error).
- **Fix:** wrapper now returns the real classify result; annotation became `Task[bool]`.
- **Files modified:** tests/scripts/test_opening_cache_repair.py
- **Commit:** 8ee3b40a9

Otherwise the plan executed as written. The `make_game` fixture got an optional `evals` argument (default behaviour unchanged) so the reclassify tests drive real classification.

## Follow-up notes

- `scripts/backfill_maia_flaws.py` (named in the reminder) does not exist yet; plan 05 creates it, so the reminder currently points at a future script.
- A MissingGreenlet teardown log (asyncpg connection close) appeared only in the output of runs where a reclassify test failed during development; it is absent on green runs.

## Known Stubs

None.

## Threat Flags

None. T-247-04 (survivor rows) is mitigated by omission and proven by the mutation run above; T-247-05 (stale stamps) by clearing in the same transaction as every rewrite plus the printed reminder.

## Self-Check: PASSED

Files verified present: all seven modified files. Commits 9c0530e81 and 8ee3b40a9 verified on the branch.
