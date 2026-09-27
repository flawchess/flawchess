---
quick_id: 260927-ajg
mode: quick
description: Fix short-checkmate oracle bug and re-derive affected prod games
---

# Quick 260927-ajg: short checkmate games never get oracle columns

Found by the 2026-09-27 prod sanity check (`reports/db-stats/db-report-prod-2026-09-27.md`, Check E):
1,014 games of 4-9 plies ending in checkmate have `full_evals_completed_at` set but NULL oracle
columns, NULL accuracy and zero `game_flaws`. All 1,014 have a final `move_san` ending in `#` and
miss exactly one eval, on row `ply_count - 1` (the eval of the mated position, which the engine
cannot score). `_compute_eval_coverage` already excludes the terminal row (260615-rb1) but not
this second unevaluable row, so a 7-ply mate scores 6/7 = 0.857 < `EVAL_COVERAGE_MIN`, and both
`classify_game_flaws` and `count_game_severities` return `GameNotAnalyzed`. Games >= 10 plies
lose the same row but still clear 0.90, which is why only short mates are affected.

Runs in an isolated git worktree (`../flawchess-260927-ajg`) because Phase 225 is being worked
on concurrently in the main checkout.

## Task 1: exclude the mated position from the coverage denominator

- files: `app/services/flaws_service.py`, `tests/services/test_flaws_service.py`
- action: in `_compute_eval_coverage`, when the last movable position's `move_san` ends with `#`
  and it carries no eval, drop it from both numerator and denominator (it is structurally
  unevaluable, like the terminal row). Comment the fix site. Update the `EVAL_COVERAGE_MIN`
  comment.
- verify: new unit tests: fully-evaluated 7-ply mate scores 1.0 and `count_game_severities` /
  `classify_game_flaws` no longer return `GameNotAnalyzed`; a sparse mate game stays below the
  gate; a non-mate game with a missing last eval is NOT excused. Revert the fix and confirm the
  new tests fail (mutation check).
- done: `uv run pytest tests/services/test_flaws_service.py` green.

## Task 2: targeted re-derive mode for the oracle gap

- files: `scripts/backfill_flaws.py`, test under `tests/`
- action: add `--oracle-gap` mode selecting games with `full_evals_completed_at IS NOT NULL AND
  white_blunders IS NULL AND ply_count IS NOT NULL`, and reclassifying each through
  `eval_apply._classify_and_fill_oracle` (the drain's diff/upsert classifier, which writes flaws +
  oracle + accuracy) in its own transaction under `pg_advisory_xact_lock(_game_write_lock_key)`.
  Games that are still `GameNotAnalyzed` are skipped and counted. Never uses the script's
  delete-then-insert branch. `--dry-run` counts how many would be fixed.
- verify: DB test seeding a short mate game with NULL oracle, run the mode, assert oracle columns
  and flaw rows written; a still-unanalyzable game untouched.
- done: test green; full pre-merge gate green.

## Task 3: re-derive prod

- Dry run, then real run against prod over the tunnel, from the worktree code.
- Verify with the Check E probe: `full_evals_completed_at IS NOT NULL AND white_blunders IS NULL
  AND ply_count BETWEEN 1 AND 9 AND termination = 'checkmate'` goes to ~0.
- Games completed by the (unfixed) prod drain between the run and the next deploy stay broken;
  rerun `--oracle-gap` once after the next deploy.

Also: amend the db-report skill's Check B with the oracle-gap probe so this class of gap is
visible in future reports.
