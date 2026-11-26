---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 06
subsystem: release
tags: [facepalm-score, release, prod-copy, parity, d-11]
requires:
  - phase: 254-03
    provides: "copy_line_material.py (copy, --status, --parity) and backfill --mode pre"
  - phase: 254-16
    provides: "dual-writing Maia hook"
provides:
  - "Release R1 live on prod (production 697ec5fbd): migration a7d2c9e1b254, dual-writing hook, operator tools; readers unchanged"
  - "Prod played_line_material filled from line_loss_* on every row that had line values (copy_pending_rows=0)"
  - "Prod parity: expression equals the stored facepalm_score within 1e-6 on 1,850,930 scored user blunders"
  - "Plan 250-10 closed as superseded by Phase 254 (D-11); Phase 250 complete"
  - "Prod-run worktree .claude/worktrees/phase-254-prod, detached at 697ec5fbd, for plans 07 and 11"
affects: [254-07, 254-08, 254-10, 254-11]
key-files:
  created:
    - .planning/phases/250-facepalm-blunder-selection/250-10-SUMMARY.md
    - reports/maia-flaws-backfill/prod-line-material-copy.md
    - reports/maia-flaws-backfill/copy-line-material-20261114T234043Z.json
    - reports/maia-flaws-backfill/copy-line-material-20261114T234105Z.json
  modified:
    - .planning/ROADMAP.md
    - .planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md
    - CHANGELOG.md
key-decisions:
  - "Owner go-ahead for R1 on 2026-11-14; the release also carried Phase 253 and the library filter changes already on main"
  - "Tasks 1 and 2 ran inline in the orchestrator (long dev DB run, docs plus gate), not in an executor"
  - "The plan's ancestor check for the prod-run worktree cannot pass under squash releases; tree equality with the R1 squash commit was verified instead"
requirements-completed: [D-01, D-09, D-11, D-12, D-17]
---

# Phase 254 Plan 06: Release R1

**R1 is live on prod, the legacy line values are copied into `played_line_material`, and the query-time expression
matches the stored score on every scored user blunder.**

## Task 1: R1 chain rehearsed on dev (all exit 0)

Log: `temp/facepalm-backfill/dev-rehearsal-254-06.log` (gitignored). Dev at Alembic head `a7d2c9e1b254`.

- Copy status before: `copy_pending_rows=5245 copied_rows=0`
- Copy: `total: batches=83 games_scanned=164771 rows_copied=5245 cursor=844366 stopped_early=False dry_run=False`
- Copy status after: `copy_pending_rows=0 copied_rows=5245`
- Parity after the copy: `stored_scored=4557 expression_scored=4557 both_scored=4557 max_abs_diff=5.948233228192379e-08 cut_side_mismatches=0`
- Pre pass, user 28, 2 workers: `games_selected=2880 games_scored=2880 games_stamped=2880 ... pre_scored=5396 pre_null=0 reason_best_move_missing=141`
- Pre pass, second run: `games_selected=0`
- Pre status: `pre_stamped_games=2880 pre_pending_games=0 user_blunders_total=5396 user_blunders_with_best_prob=5255 user_blunders_with_pre_spread=5396`
- Line pass, cutoff `2026-11-14T23:02:07+00:00`: `games_selected=2880 games_scored=2880 games_stamped=2880 ... scores_set=4557 scores_null=839`
- Line status: `line_done_since_cutoff=2880 line_pending_games=0 user_blunders_total=5396 user_blunders_with_score=4557 user_blunders_qualifying=1228`
- Parity after the line pass: `stored_scored=4557 expression_scored=4557 both_scored=4557 max_abs_diff=2.9735861883928294e-08 cut_side_mismatches=0`
- Dev `game_flaws` afterwards: 5245 rows with `played_line_material`, 4629 with `best_line_material`, 5255 with
  `maia_best_prob`, 5396 with `maia_pre_spread`.

## Task 2: D-11 close-out, changelog, pre-merge gate

- `250-10-SUMMARY.md` written (status superseded), ROADMAP Phase 250 shows 11/11 plans closed, `250-CONTEXT.md` D-18
  carries the superseded note, CHANGELOG `[Unreleased]` has the R1 bullet. Commit `15b69def7` on the phase branch.
- Gate, each exit 0: `ruff format` (612 files unchanged), `ruff check . --fix`, `ty check app/ tests/ scripts/`,
  `ty check analysis/`, `check_function_size.py app/ --fail-over-depth 4` (1536 functions, no breaches),
  frontend `lint`, `build`, `test -- --run`, `knip`.
- `uv run pytest -n auto -x`: 6563 passed, 19 skipped, in two clean runs. Three other runs did not finish clean:
  two stopped on `tests/test_eval_worker_endpoints.py::test_lease_lifo` (the claim returned four of the test's own
  five games when asked for three) and one stalled near 98% under machine load and hit a 280 s limit. Earlier in the
  phase `tests/services/test_import_service.py::TestHotLaneCoveredGate::test_stage5c_marks_covered_games` failed
  once. Neither test nor the code under them is changed by this phase, and each passes alone. No formatter fix was
  needed, so there is no `style(254-06)` commit.

## Task 3: R1 shipped, prod copy and parity

Full record: `reports/maia-flaws-backfill/prod-line-material-copy.md` (commit `6e027a88f` on main).

- Owner go-ahead received. R1 cycle closed: squash commit `adbdf856a` on main (tree identical to the gated phase
  branch tip `15b69def7`), phase branch deleted, pushed.
- Release PR #478, CI green, squash-merged to production as `697ec5fbd`, deployed 2026-11-14T23:38Z, server SHA
  verified. Forward-port was skipped by the script (untracked file from another session) and run by hand:
  `2b9c62ce4`.
- S2 `a7d2c9e1b254`, S3 5 columns. Live hook: the first game scored after the deploy has `best_line_material` and
  `maia_pre_spread` on its 4 flaw rows.
- Prod-run worktree at `697ec5fbd`, `uv sync --group maia-inference` done.
- Benchmark DB migrated to `a7d2c9e1b254`; 2515 rows with a score there; the :8001 backend was not restarted.
- S1 before launch: 13 connections. Slice: 23,621 rows in about 5 s.
- Full copy from the prod-run worktree: `rows_copied=2145919`, `EXIT=0`, 1045.5 s.
- Status: `copy_pending_rows=0 copied_rows=2169544`.
- Parity: `stored_scored=1850930 expression_scored=1850930 both_scored=1850930 max_abs_diff=1.003345291294977e-07 cut_side_mismatches=0`, exit 0.

## Deviations

- Tasks 1 and 2 were run inline by the orchestrator instead of an executor.
- The ancestor check in Task 3 step 3 was replaced by a tree-equality check (see key decisions).
- The release carried Phase 253 and two library filter changes in addition to R1.
- The benchmark-lane backend was not restarted after the benchmark migration.

## Self-Check: PASSED
