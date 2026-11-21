---
phase: 259-facepalm-first-principles-refit
plan: 06
subsystem: release
tags: [facepalm, release, r1, prod-backfill, line-pass, reply-pass]

requires:
  - phase: 259-05
    provides: "reply backfill mode, games.facepalm_reply_completed_at, status counts"
provides:
  - "R1 live on prod: schema at d2a6c8e0f259, hook dual-writes material_loss / material_missed / maia_best_reply_prob"
  - "prod line pass complete: material inputs on 2,207,928 user and 2,210,542 opponent blunders"
  - "prod reply pass running (PID 2012778, launched 2026-11-21T19:01:25Z), completion checked in plan 11"
  - "prod-run worktree .claude/worktrees/phase-259-prod detached at d75996143"
  - "reports/maia-flaws-backfill/prod-facepalm-259-r1.md"
affects: [259-07, 259-11]

actuals:
  tasks: 3
  commits: 2
commits: 2

key-files:
  created:
    - reports/maia-flaws-backfill/prod-facepalm-259-r1.md
  modified:
    - CHANGELOG.md
    - pyproject.toml

key-decisions:
  - "Owner go-ahead for R1 given 2026-11-21; c3ab036e8 (quick 261121-n50) shipped with it on the owner's instruction"
  - "T_DEPLOY, the line-pass cutoff: 2026-11-21T18:10:27+00:00"
  - "Line pass ran with 8 workers on the owner's request (plan: 4); reply pass at 12 as planned"
  - "Owner approved restarting the Phase 252 feeder beside the reply pass (exception to one operator run at a time)"
---

# Phase 259 Plan 06: Release R1 Summary

**R1 is live on prod (server `d7599614`, schema `d2a6c8e0f259`), the prod line pass finished with `line_pending_games=0`, and the 18-hour reply pass is running from the prod-run worktree.**

## Performance

- **Executed by:** an executor for Tasks 1 and 2 (dev rehearsal partly finished by the orchestrator), the orchestrator for Task 3
- **Completed:** 2026-11-21
- **Tasks:** 3/3

## Task 1: dev rehearsal (user 28, nothing committed)

- `uv run alembic upgrade head`: nothing to run, dev already at `d2a6c8e0f259 (head)`.
- Line pass, cutoff `2026-11-21T17:06:41+00:00`, 2 workers, 20 s: `games_selected=5311 games_scored=5311 games_stamped=5311 games_write_failed=0 games_score_failed=0 scores_set=10239 scores_null=20 opponent_scores_set=10906 opponent_scores_null=15`.
- Line status: `line_done_since_cutoff=5311 line_pending_games=0 user_blunders_total=10259 user_blunders_with_score=10239 user_blunders_qualifying=3987 opponent_blunders_total=10921 opponent_blunders_with_line_facts=10914 opponent_blunders_with_score=10906 user_blunders_with_material_inputs=10241 opponent_blunders_with_material_inputs=10906`.
- Reply pass run 1 (executor, stopped cleanly at its time cap): `games_selected=5311 games_scored=2200 games_stamped=2200`, `reason_reply_missing=16`, about 230 games/min on 2 workers.
- Reply pass run 2 (orchestrator, resumed from the stamp): `games_selected=3111 games_scored=3111 games_stamped=3111 games_write_failed=0 games_score_failed=0`.
- Reply pass run 3: `games_selected=0`.
- Reply status: `reply_stamped_games=5311 reply_pending_games=0 blunders_total=21180 blunders_with_reply_prob=21164 reply_residue_losing=0 unscored_pure_miss_no_best=0 blunders_without_material_inputs=33`.
- D-13 row on dev (game 2883555 ply 47): `material_loss` 2.935484, `material_missed` 0, `maia_best_reply_prob` 0.19963053.

## Task 2: changelog and gate

- CHANGELOG bullet under `## [Unreleased]` / `### Changed` (`96eae2240`).
- Exit codes: `ruff format` 0; `ruff check . --fix` 1 at first (7 findings in the committed spike scripts under `.planning/phases/259-.../spike/`), 0 after the exclude below; `ty check app/ tests/ scripts/` 0; analysis `ty check` 0; `check_function_size.py app/ --fail-over-depth 4` 0; `uv run pytest -n auto -x` 0 (7405 passed, 19 skipped); frontend lint 0, build 0, test 0 (6740 tests), knip 0.
- Serial suite `uv run pytest -x` (run by the orchestrator): 0, 7405 passed, 19 skipped in 541.74 s.
- After the squash onto main (which also carries `c3ab036e8`): `uv run pytest -n auto -x` 0 (7124 passed, 8 skipped), `ruff check .` and `ty check` clean.

## Task 3: R1 shipped, prod passes

Full record with every number: `reports/maia-flaws-backfill/prod-facepalm-259-r1.md`.

- Owner go-ahead: "Ship R1", 2026-11-21.
- R1 cycle closed: squash commit `c4cb1e699` on main (one conflict in STATE.md frontmatter, resolved to the phase branch's side), phase branch deleted, main pushed.
- Deploy via the /deploy skill: PR #497 squash-merged as `d75996143`, CI green without fixes, `bin/deploy.sh` exit 0, server at `d7599614`, forward-port pushed. T_DEPLOY `2026-11-21T18:10:27+00:00`.
- S1 11 connections; S2 `d2a6c8e0f259`; S3 4 rows; S4 102 of 119 post-deploy blunders have `material_loss` and 102 have `maia_best_reply_prob`.
- PRODWT `.claude/worktrees/phase-259-prod` detached at `d75996143`, `uv sync --group maia-inference` done.
- Benchmark DB at `d2a6c8e0f259`; no :8001 backend running.
- Line pass: slice 50 games in about 1 s; run A (4 workers) stopped cleanly at 23,700 games; run B (8 workers, about 440 games/s) ended with `EXIT=0`, `games_scored=1031093`, 0 write or score failures. Status: `line_pending_games=0`, `user_blunders_with_material_inputs=2207928`, `opponent_blunders_with_material_inputs=2210542`.
- Reply pass: before the slice `reply_pending_games=1054842`; slice 50 games in 19 s (`reply_probs_set=214`); full run launched 2026-11-21T19:01:25Z, PID 2012778, 12 workers, 30 prod connections, about 16 games/s at the first reading, estimate about 18 hours.

## Task Commits

1. **Task 2: changelog** - `96eae2240` (docs)
2. **Task 2: ruff exclude for spike scripts** - `3e40c3a4e` (style)

Both are inside the R1 squash `c4cb1e699`.

## Deviations from Plan

- **[Rule 3] ruff exclude.** `ruff check .` failed on the phase's committed spike scripts; `.planning/phases/*/spike` was added to `extend-exclude` in `pyproject.toml` (`3e40c3a4e`), following the sketches precedent. The spike scripts are unchanged.
- **Ancestor check replaced.** The plan checks that the R1 squash SHA is an ancestor of PRODWT HEAD; release PRs squash, so it is not. Verified instead that `git diff c4cb1e699 d75996143` is empty.
- **Line pass at 8 workers** instead of 4, on the owner's request; the 4-worker run was stopped cleanly and the 8-worker run resumed from the same cutoff.
- **First reply status read after about 4 minutes**, not 30; plan 11 Task 2 checks the pass again.
- **Feeder beside the reply pass.** The owner stopped the Phase 252 feeder before the line pass and approved restarting it once the reply pass was up.
- The serial suite and the last part of the dev reply rehearsal ran in the orchestrator, not in the executor (long runs die with an executor).
- The release also carried Phase 258 and quick task 261121-n50, both already on main.

## Issues Encountered

- The orchestrator's first stop command for the 4-worker line pass (`pkill -f`) also matched its own shell, so the relaunch needed a second attempt. The pass had stopped cleanly; no data effect.
- A stuck waiter loop left by the executor (a `pgrep -f` that matched itself) was removed.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register; operator connections peaked at 30 in total with the reply pass up.

## Next Phase Readiness

Plan 07 starts on a fresh SW cycle branch off origin/main. The reply pass must be left running; PRODWT must not be re-pointed while it runs.

## Self-Check: PASSED
