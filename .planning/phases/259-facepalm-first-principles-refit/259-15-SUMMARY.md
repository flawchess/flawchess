---
phase: 259-facepalm-first-principles-refit
plan: 15
subsystem: release
tags: [facepalm, release, drop, d-05, d-06, one-way, owner-checkpoint]

requires:
  - phase: 259-12
    provides: "switch release live, D-18 keep"
  - phase: 259-14
    provides: "migration f3a7b9c1e259 and the model without the arrays"
provides:
  - "Drop release live on prod: server 59e1edcb, schema f3a7b9c1e259"
  - "game_flaws without played_line_material / best_line_material; ix_game_flaws_blunder_facts gone"
  - "benchmark DB at f3a7b9c1e259"
affects: []

actuals:
  tasks: 3
  commits: 1
commits: 1

key-files:
  created: []
  modified:
    - CHANGELOG.md

key-decisions:
  - "Owner decision D-06, 2026-11-22: \"drop-now\""
  - "Owner chose to deploy beside the running Phase 252 feeder (\"Deploy beside it\")"
---

# Phase 259 Plan 15: Drop Release Summary

**The old 9-slot material arrays and their covering index are gone from prod and the benchmark DB; the hook keeps writing the scalar inputs on live games.**

## Performance

- **Executed by:** the orchestrator inline (Task 1 is a handful of dev commands and the gate; Tasks 2 and 3 are orchestrator checkpoints)
- **Completed:** 2026-11-22
- **Tasks:** 3/3

## Task 1: dev rehearsal on the dropped schema, changelog, gate

Log: `temp/blunder-check/tracer-259-15.log`.

1. `uv run alembic current`: `f3a7b9c1e259 (head)`.
2. Line pass, cutoff `2026-11-22T12:44:58+00:00`, 2 workers, user 28: `games_selected=5311 games_scored=5311 games_stamped=5311 games_write_failed=0 games_score_failed=0 scores_set=10241 scores_null=18 opponent_scores_set=10906 opponent_scores_null=15`. Status: `line_done_since_cutoff=5311 line_pending_games=0 user_blunders_with_score=10241 user_blunders_qualifying=3109 opponent_blunders_with_material_inputs=10906 opponent_blunders_with_score=10906 user_blunders_with_material_inputs=10241`.
3. Reply status: `reply_stamped_games=5311 reply_pending_games=0 blunders_total=21180 blunders_with_reply_prob=21164 reply_residue_losing=0 unscored_pure_miss_no_best=0 blunders_without_material_inputs=33`.
4. Spread status: `user_blunders_with_score=10241 user_blunders_qualifying=3109`.
5. Calibration on 200 dev games: scored 3106 Good moves (0 not scorable), 47 spot-check windows, exit 0.
6. CHANGELOG note under `[Unreleased]` / `### Changed` (`889185e47`).
7. Gate exit codes: ruff format 0, ruff check 0, ty 0, analysis ty 0, function size 0, frontend lint 0, build 0, test 0 (6740 tests), knip 0. `uv run pytest -n auto -q` 0 (6861 passed, 8 skipped). Serial `uv run pytest -x` 0 (6861 passed, 8 skipped in 500.47 s).

## Task 2: owner decision (D-06, one-way)

Evidence shown:

- Switch live; prod `--status --mode spread` from the DROP branch: `user_blunders_with_score=2209621 user_blunders_qualifying=776783` (identical to plan 12's post-deploy count).
- `ix_game_flaws_facepalm_inputs` valid on prod; the old index was 1,392 MB.
- No-reader gates at 0 over app, scripts and tests (plans 13 and 14); gate and serial suite pass on the dropped schema.
- Seeds and ROADMAP naming the arrays: SEED-261121-tau (this phase), SEED-261114-iuv (Phase 257, shipped), a closed seed and this phase's ROADMAP entry. No open reader.
- Dropping removes the cheap rollback to the pre-switch score about an hour after the switch.

**Option, verbatim:** "drop-now". **Date:** 2026-11-22. The feeder question was answered "Deploy beside it (Recommended)".

## Task 3: drop shipped and verified

- No operator process of the plan's list was running before the deploy; the Phase 252 feeder was (owner-approved).
- DROP cycle closed: squash commit `5904c9a61` on main (tree identical to the phase branch), phase branch deleted, main pushed.
- Deploy via the /deploy flow: PR #499, CI green without fixes, squash-merged as `59e1edcb0`, `bin/deploy.sh` exit 0 at 2026-11-22T13:12Z, server at `59e1edcb`, forward-port pushed (`de39c02f4`).
- Prod: `alembic_version` `f3a7b9c1e259`; the two array columns return no row; `ix_game_flaws_blunder_facts` count 0; `ix_game_flaws_facepalm_inputs` valid; site HTTP 200; backend up with no error lines in its log tail; the feeder kept running.
- Hook after the deploy (games with `maia_flaws_completed_at` after 13:12:30Z, read two minutes later): 489 blunders, 461 with `material_loss`, 462 with `maia_best_reply_prob`.
- Prod `--status --mode spread` after the deploy: `user_blunders_total=2365175 user_blunders_with_score=2209628 user_blunders_qualifying=776785`.
- Benchmark DB: `f3a7b9c1e259`, no array columns; nothing listening on :8001.
- Sentry: checked at the end of the phase (see the phase verification notes).

## Task Commits

1. `889185e47` docs(259-15): changelog note (inside the DROP squash `5904c9a61`)

## Deviations from Plan

- Task 1 ran inline in the orchestrator rather than in an executor.
- The S4 hook check was read two minutes after the deploy instead of 30, with the window bounded to games finished after the deploy; both counts were already well above 0.
- The Phase 252 feeder ran during the deploy on the owner's choice. Its SQL does not name the dropped columns.
- The DROP squash also carries one commit from another session (`24f356735`, a planted seed doc).

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-259-37: blocking decision recorded before the deploy. T-259-38: no listed operator script was running; the feeder is unaffected.

## Next Phase Readiness

All 15 plans are done. The promotion question raised during execution is captured as a separate seed by another session.

## Self-Check: PASSED
