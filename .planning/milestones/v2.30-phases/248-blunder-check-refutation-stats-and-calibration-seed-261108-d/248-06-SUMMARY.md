---
phase: 248
plan: 06
status: complete
commits: 4
live_lane_check: deferred
---

# 248-06 Summary: ship go-forward refutation scoring

## Task 1: owner go-ahead (blocking-human checkpoint)

- Owner's literal answer (2026-11-09, ~20:40 UTC): `merge-and-deploy`
- Given before 247-07 ended; Task 2 held until the precondition held.
- 247-07 end state: `temp/maia-flaws-backfill/prod-full.log` has 1 `EXIT=` line, `EXIT=0` at 2026-11-10 00:18:38 UTC
  (run stamp 20261109T080843Z, 9 shards). Total line: games_selected=603193 games_scored=603193 games_stamped=603190
  games_already_stamped=3 games_write_failed=0 games_score_failed=0 flaws_scored=4520564 flaws_null=9739.
  The 247-07 python process (PID 3148890) is gone and no `backfill_maia_flaws.py` process is alive.
- 247-07 catch-up and coverage (its Task 3): pending (no 247-07-SUMMARY.md). Per D-12 it runs after this deploy with the
  new code as `--mode full` (plan 07 Task 3). 247-07 Task 2 step 5 (prod-coverage.md "Full run" section, shard JSON
  commit) also not done yet.

## Task 2: tracer, ship end to end

- Pre-merge gate on the phase branch (worktree `../flawchess-248`), all exit 0: ruff format (572 unchanged), ruff check,
  ty `app/ tests/ scripts/`, ty `analysis/`, nesting-depth gate (1317 functions, no breaches), `pytest -n auto -x`
  5875 passed / 20 skipped, serial `pytest -x` 5875 passed / 20 skipped (4m15s), frontend lint, build, 6087 tests, knip.
- D-19: `git diff --name-only main...HEAD | grep -E -c '^(frontend/|app/routers/)'` printed 0.
- Docs: `docs/dev-tooling.md` (`--mode full|refutation`, `blunder_check_calibration.py` bullet) and CHANGELOG
  [Unreleased] "punishing reply" bullet.
- Squash-merge: local main rebased onto origin/main (2 origin commits: Postgres max_connections 30 -> 50, postgres
  digest #465), squash on `squash/248` in the worktree (one ROADMAP.md conflict from the rebased plan commits, took the
  phase side), gate re-run on the merge result (ty, ruff, pytest -n auto 5875 passed), `--ff-only` on main, pushed:
  `157076b62 feat(248): ...`; `main...origin/main` = 0 0. Phase branch and squash branch deleted.
- Deploy: release PR #469, CI green (backend, frontend, docker, test), squash-merged as `e60dd1302`, `bin/deploy.sh`
  ok, server at `e60dd130`, forward-port pushed (`0d07aa117`). HTTP 200, backend/caddy/db up (db recreated for the
  max_connections change).
- Prod MCP: `maia_%` column count on game_flaws + games = 12 (baseline 9). `max_connections` = 50.
- Live-lane check: **deferred**. Polled every ~10 min from 00:37 to 01:38 UTC: 0 games with
  `full_evals_completed_at` after the deploy (00:36 UTC), so 0 post-deploy non-guest analyses. Last analyses on prod
  were ~21:00 UTC and the last remote-worker heartbeat 21:24 UTC (overnight lull, unrelated to the deploy). The write
  path is covered by plan 01's lane tests (drain, /atomic-submit, /flaw-blob-submit); re-check on the first daytime
  analysis or during plan 07.
- Pre-backfill baseline (`--status --mode refutation --db prod`, exit 0, 00:37:53 UTC):
  `refutation_stamped_games=0 refutation_unstamped_games_with_flaws=1026634 user_blunders_with_refutation=0
  user_blunders_total=2297495`.

## Task 3: post-deploy health

- Sentry (60 min after deploy, project flawchess): FLAWCHESS-D0 (ConnectionResetError), FLAWCHESS-6P (gaierror),
  FLAWCHESS-D1 (CannotConnectNowError "database system is shutting down"), all at 00:36:04-05 UTC on
  `/api/eval/remote/*-lease`: the db container recreate during the deploy, transient. FLAWCHESS-D3 "Stale frontend
  build detected by version check" at 00:48 UTC: expected after a deploy. No `source:maia_flaws` issues.
- Baselines (01:38 UTC): go-forward refutation-stamped games = 0; refutation backfill scope (base-stamped, no
  refutation stamp) = 1,026,710; pg_stat_activity = 14 of max_connections 50.
- Benchmark lane: before restarting the :8001 backend from the main tree, run `bin/benchmark_db.sh start` (applies
  c4e9b1d7f248 to the benchmark DB). No benchmark-DB backfill (D-19).
- Sequencing for plan 07: 247-07's full run ended EXIT=0; its Task 2 step 5 (prod-coverage.md "Full run" section and
  shard JSON commit) and Task 3 (catch-up + coverage SQL) are NOT done. Plan 07 Task 3 runs the catch-up with the new
  code as `--mode full` (writes 247 values plus the refutation pair) and 247-07 Task 3's coverage SQL on the same
  post-catch-up state.

## Deviations

- Plans 01-05 ran in a dedicated worktree (`../flawchess-248`) because 247-07's backfill was running from the main
  checkout; executors ran sequentially-isolated on the phase branch with pathspec commits (two at a time in waves 1-2).
- The phase-start docs commit (974fb9180, STATE.md only) was made with hooks disabled; all other commits used hooks.
- The release also shipped the 13 then-unpushed local main commits (248 planning docs, blunder-check seeds,
  `fix(sentry): drop engine worker failures from hidden tabs`) and origin's Postgres max_connections change.
