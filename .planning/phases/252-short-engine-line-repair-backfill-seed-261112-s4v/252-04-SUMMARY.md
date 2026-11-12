---
phase: 252-short-engine-line-repair-backfill-seed-261112-s4v
plan: 04
subsystem: line-repair-operator-script
tags: [feeder, tier-4, rewalk, flip-measurement, operator-script, postgres, advisory-lock]

requires:
  - phase: 252-01
    provides: repair subcommand, frozen newest-first work list, repair cursor, D-10 gate constants, GateResult
  - phase: 252-02
    provides: per-line tier-4 NULL semantics (fill-NULL-only writes, per-line lease)
  - phase: 252-03
    provides: blob-only server-pool tick and the tier-4 guard on /atomic-lease
provides:
  - "feed subcommand: just-in-time D-11 tier-4 re-walk feeder with D-10 8-week gate and eval-fingerprint guard"
  - "measure-flips subcommand: D-05 stored-vs-exact classification flip share with a control arm and the 2% gate"
  - "status subcommand: read-only repair and feed progress"
  - "docs/dev-tooling.md inventory entry for scripts/repair_short_lines.py"
affects: [252-06, 252-07, 252-08]

actuals:
  tokens: 22400
  tasks: 3
  commits: 3
plan_head_before: 74dcaf53a7e3d5dd187b4922411528ba3015ff0e
plan_head_after: 6edcfffb93dc2f6c2ae938129c7631971abc5ac1

tech-stack:
  added: []
  patterns:
    - "feeder predicate re-evaluated inside the UPDATE under per-game advisory locks (idempotent), raw SQL NULL literal"
    - "persisted state typed as TypedDict whose only strings are md5 fingerprints"
    - "injectable wall clock plus _after_poll_hook/_max_polls test seams drive the long-running loop deterministically"

key-files:
  created: []
  modified:
    - scripts/repair_short_lines.py
    - tests/scripts/test_repair_short_lines.py
    - docs/dev-tooling.md

key-decisions:
  - "The feeder's clock is wall-clock seconds (time.time), not monotonic, because fed_at is persisted and compared across feeder restarts"
  - "A line is fed only if its node0 pv has at least CACHED_PV_MIN_PLIES plies as well as the D-03 old-shape bound: a `[]` blob under a 1-2 ply pv could only be rebuilt to the same blob"
  - "Fingerprints are taken inside the feed transaction after the per-game locks and before the NULL write, so a worker submit cannot slip between the snapshot and the write"
  - "feed_window locks only games that have a candidate line (not all 500 of the window), keeping the lock count small"
  - "A pilot that has drained is judged at once (min_hours=0); a non-pilot run judges the projection only after FEED_GATE_MIN_HOURS"
  - "A dry-run feed walks windows up to the repair cursor but never polls, waits or persists state, so it cannot hang on a repair that is not running"

patterns-established:
  - "Strictly-above gates reused: evaluate_feed_gates returns GateResult rows like evaluate_repair_gates"

requirements-completed: [D-11, D-04, D-03, D-05, D-10, D-13, D-15]

coverage:
  - id: F1
    description: "A repaired line is NULLed to SQL NULL (not JSON null) and then leased alone by the per-line tier-4 lease; the flaw's other line and its stamp semantics stay intact"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_feed_tracer_repaired_line_leased_alone"
        status: pass
    human_judgment: false
  - id: F2
    description: "Feeder selection rules: D-03 old-shape bound, claimable games only, no guest games, idempotent re-feed, stamp cleared only for games that got a line NULLed"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_feed_d03_bound_skips_node_gap_blobs_and_feeds_empty_sentinels"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_feed_window_is_idempotent_and_keeps_unmatched_games_stamped"
        status: pass
    human_judgment: false
  - id: F3
    description: "Just-in-time windows: low water holds the next window, windows follow the work list and never pass the repair cursor, --batch-games/--low-water size the windows, pilot feeds exactly ceil(1%)"
    requirement: "D-11"
    verification:
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_feed_low_water_holds_the_next_window_until_enough_games_drain"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_feed_pilot_feeds_exactly_the_first_one_percent_and_exits_ok_once_drained"
        status: pass
    human_judgment: false
  - id: F4
    description: "D-10 re-walk gate (projected weeks on the measured drain rate, zero drain after FEED_GATE_MIN_HOURS trips) and the eval/flaw-set fingerprint guard exit 3 with STOP in the report"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_feed_gate_trips_when_nothing_drains_within_the_observation_window"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_feed_fingerprint_guard_trips_when_a_fed_game_eval_changes"
        status: pass
    human_judgment: false
  - id: F5
    description: "measure-flips reuses _run_all_moves_pass, reports stored-vs-exact next to an exact-vs-exact control, gates at 2%, never writes a row, excludes lichess-eval and guest games"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/scripts/test_repair_short_lines.py#test_flips_run_with_a_shifting_searcher_exits_3_and_writes_no_row"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_repair_short_lines.py#test_flips_a_transition_with_a_mate_eval_follows_the_mate_ladder"
        status: pass
    human_judgment: false
  - id: F6
    description: "Dev smoke of the three operator commands: feed --dry-run and status exit 0; measure-flips with real Stockfish (3 games, 2 engines) ran end to end and wrote its report"
    requirement: "D-10"
    verification:
      - kind: other
        ref: "uv run python scripts/repair_short_lines.py measure-flips --db dev --sample-games 3 --engines 2 --report-dir temp/line-repair/smoke"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-11-12
status: complete
---

# Phase 252 Plan 04: Feeder, flip measurement and status Summary

**`scripts/repair_short_lines.py` now has `feed` (a just-in-time, newest-first, single-line tier-4 re-walk feeder that stops itself on the 8-week projection gate or any eval change), `measure-flips` (the D-05 classification flip share with a noise-control arm) and a read-only `status`.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 3 (tracer, feeder loop and gates, measure-flips plus inventory)
- **Files modified:** 3 (no new files; no app code, model or migration touched)

## Accomplishments

- `select_rewalk_lines` and `feed_window`: a line is fed only when its blob has at most `REWALK_MAX_OLD_BLOB_LEN` (3) elements, is shorter than `2*floor(min(plies, 12)/2)+1` for the current node0 pv, and the pv has at least `CACHED_PV_MIN_PLIES` plies. NULLs are a raw SQL literal, taken under per-game advisory locks (ascending id) with the predicate re-evaluated inside the UPDATE; `games.blobs_completed_at` is cleared only for games that got a line NULLed. The tracer proves feed to per-line lease end to end.
- `run_feed`: poll loop with low water (`FEED_LOW_WATER` 150), window size (`FEED_BATCH_GAMES` 500), the fence at the repair cursor, `--pilot`, `--windows`, `--batch-games`, `--low-water`, `--dry-run`, cooperative SIGTERM, Sentry capture of a failed step, persisted `FeedState` that holds only counts and md5 fingerprints.
- `evaluate_feed_gates`: projected weeks (judged only after `FEED_GATE_MIN_HOURS`, zero drain trips, a drained pilot is judged at once) and the eval/flaw-set fingerprint change share against `FEED_MAX_EVAL_CHANGE_SHARE`. The report states the drain rate measured with the fleet as it is and the user-visible NULL window per completed game (p50, p95, max); it prints no fixed throughput expectation (D-15).
- `run_measure_flips`: samples engine-evaluated non-guest games by `md5(id::text)`, re-searches every non-terminal post-move board in two arms (second arm on a freshly started pool), classifies with `flaws_service._run_all_moves_pass`, reports stored-vs-exact next to exact-vs-exact, gates at 2%, SELECTs only.
- `run_status` and the `docs/dev-tooling.md` inventory entry.

## Task Commits

1. **Task 1: Tracer, repaired line fed to SQL NULL and leased alone by tier 4** - `77b625408` (feat)
2. **Task 2: Feeder loop with D-10 re-walk gate, eval-fingerprint guard and status** - `936d6f064` (feat)
3. **Task 3: measure-flips with a control arm and the script inventory entry** - `6edcfffb9` (feat)

## Verification Results

- `uv run pytest tests/scripts/test_repair_short_lines.py -q`: 56 passed (47 before Task 3; the file started this plan at 31). `-k "feed or status"`: 16 passed. `-k flip`: 8 passed.
- Wider: `uv run pytest -n auto tests/scripts tests/services -k "repair or eval or blob or flaw or drain or tier4" -q`: 913 passed, 8 skipped.
- `uv run ty check app/ tests/ scripts/`: all checks passed. `ruff check .` and `ruff format --check`: clean. `check_function_size.py scripts/repair_short_lines.py` and `app/` with `--fail-over-depth 4`: no breaches.
- Mutation checks (guard reverted, run, restored; final tree identical to the committed one): dropping the `REWALK_MAX_OLD_BLOB_LEN` bound failed 3 tests; dropping the `full_evals_completed_at` join, the guest guard, the low-water condition, the repair-cursor fence, the fingerprint comparison, and clearing the stamp for all candidates each failed their dedicated tests (1 to 3 failures each); making the flip counter ignore gained mistakes, and comparing stored against stored, failed the flip tests.
- Dev smoke: `feed --db dev --dry-run --windows 1` exit 0 (work list 9771 games, repair cursor 0 so nothing is in reach, report written); `status --db dev` exit 0 with a `work list size` line; `measure-flips --db dev --sample-games 3 --engines 2` ran 3 min 4 s with real Stockfish and exited 3 (see Observations). All reports under `temp/line-repair/smoke/`, none under `reports/`.
- Acceptance greps: the five FEED constants present (5 lines); `_run_all_moves_pass` used and `MISTAKE_DROP|BLUNDER_DROP` absent from the script (0); `docs/dev-tooling.md` mentions the script (1); `git diff 74dcaf53a..HEAD` touches only the script, its test file and `docs/dev-tooling.md` (claim SQL, models, migrations, `eval_apply.py`, `eval_drain.py`, `eval_remote.py` untouched by this plan).

## Observations for the orchestrator

- **The 2% flip gate is likely to trip on search noise alone.** The 3-game dev smoke gave a stored-vs-exact flip share of 0.333 (4 flips over 12 stored mistakes/blunders) and an exact-vs-exact control share of 0.308 (4 of 13): nearly all flips are mistake<->blunder moves at a band boundary, and two independent exact searches of the same boards already disagree about as much as stored vs exact do. With 200 games the numbers will be tighter, but the control bounds the gate: if control is also well above 2%, the raw 2% gate cannot be met by any re-search and the stop returns to the owner with both numbers (as RESEARCH Pattern 5 anticipated). Consider judging stored-vs-exact against the control (excess flips) or counting only M/B <-> non-M/B flips; this is the owner's call, I did not change the gate definition.
- The feeder needs the repair cursor file to exist. Run order for plans 06/07: start `repair` (which writes the cursor after the first committed batch) and `feed` alongside it, or start `feed` after the repair finished. A dry-run feed before any repair has run reports zero because the fence is at 0.
- `feed` reads the work list written by `repair` (frozen per db/scope); delete `temp/line-repair/<db>-<scope>-worklist.json` only together with the cursor and feed-state files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `measure-flips` crashed at argument parsing**
- **Found during:** Task 3 dev smoke (the pytest suite calls `run_measure_flips` directly, so it did not exercise the CLI)
- **Issue:** `_parse_args` read `args.scope` for every subcommand, but `measure-flips` has no `--scope`.
- **Fix:** read it with `getattr(args, "scope", "all")` and added `test_flips_and_the_other_subcommands_parse_their_documented_flags`.
- **Files modified:** `scripts/repair_short_lines.py`, `tests/scripts/test_repair_short_lines.py`
- **Commit:** `6edcfffb9`

### Plan-form deviations (intent met)

- `run_feed` takes `clock=time.time` instead of `time.monotonic` (persisted `fed_at` must survive a feeder restart) and gained `pilot`, `batch_games`, `low_water`, plus the test seams `_after_poll_hook` and `_max_polls`.
- The Task 1 tracer ends after one wait (`_max_polls=1`) because Task 2 turned `run_feed` into the draining loop; the tracer assertions are unchanged.
- Added a `pv >= CACHED_PV_MIN_PLIES` condition to the feed predicate and an `is_guest` join to the selection and the UPDATE (defence in depth beyond the work list), both noted in key-decisions.
- The plan's low-water example (3 pending, low water 2, one completes) does not cross the threshold as written; the test uses low water 3 with the same shape.
- Task 2 is `tdd="true"`; tests were written together with the implementation, not strictly RED first, and every guard was mutation-checked afterwards (above).

**Total deviations:** 1 auto-fixed bug, 5 plan-form notes. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. T-252-08 mitigated (short-shape blob bound, raw SQL NULL asserted via `jsonb_typeof ... IS NULL`, per-game advisory locks, predicate re-evaluated in the UPDATE, repair-cursor fence, each guard mutation-checked); T-252-09 mitigated (windows bounded by `FEED_LOW_WATER`/`FEED_BATCH_GAMES`, claim SQL and index untouched, 8-week gate); T-252-10 mitigated (reports carry aggregate counts and run stamps only; no user ids, usernames or game ids).

## Next Phase Readiness

Plans 06 to 08 have every operator command: `repair` (plan 01), `feed`, `measure-flips`, `status`. Operator notes: stop the box's worker for the repair (D-08); long runs go under `setsid nohup` with `PYTHONUNBUFFERED=1` from the orchestrator; the feed state file `temp/line-repair/<db>-<scope>-feed-state.json` is the resume point and holds only counts and md5 fingerprints.

## Self-Check: PASSED

- Files: `scripts/repair_short_lines.py`, `tests/scripts/test_repair_short_lines.py`, `docs/dev-tooling.md` modified and present.
- Commits `77b625408`, `936d6f064`, `6edcfffb9` are ancestors of HEAD; `git rev-list --count 74dcaf53a..HEAD` was 3 before the docs commit.
