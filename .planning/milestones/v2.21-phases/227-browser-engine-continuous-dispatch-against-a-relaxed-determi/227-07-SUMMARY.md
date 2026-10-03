---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 07
subsystem: testing
tags: [engine, throughput, interleave, speed-probe, node, stdlib, pytest]

requires:
  - phase: 227-01
    provides: "worker-thread Maia session (probe and gate steps run Maia off the event loop)"
  - phase: 227-03
    provides: "verdict twin manifest column contract (MANIFEST_COLUMNS mirrors _MANIFEST_COLUMNS)"
provides:
  - "scripts/engine-speed-probe.mjs: fixed arm-independent machine-speed workload, one SPEED-PROBE line"
  - "scripts/engine_interleave_227.py: interleave driver (rotated schedule, load gate, per-step probe, crash-safe manifest, resume, dry-run)"
  - "tests/scripts/test_engine_interleave_227.py: 36 tests"
affects: [227-09, 227-11]

plan_head_before: cb82bf558f50333e574f9f646ae446f08257f3a1
plan_head_after: 3376916223191358d7f1b9ead727e81a52fe214f

actuals:
  tokens: 11000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Injectable Deps dataclass (load reader, sleep, clock, command runner, probe runner) so a multi-hour driver is unit-tested without running any engine"
    - "Failed step is recorded, stops the session, and is moved out of manifest.tsv on --resume so the verdict twin only ever reads clean rows"

key-files:
  created:
    - scripts/engine-speed-probe.mjs
    - scripts/engine_interleave_227.py
    - tests/scripts/test_engine_interleave_227.py
  modified: []

key-decisions:
  - "Probe constants frozen at PROBE_SF_NODES=1_800_000 (per each of 5 FENs), PROBE_MAIA_INFERENCES=60, PROBE_MAIA_ELO=1500; measured about 13.1 s of timed work (14.5 s wall) on this box"
  - "A non-zero step rc is recorded in the manifest, then the session stops (exit 1); the operator aborts by SIGTERM of the node PID and relaunches with --resume"
  - "Resume moves failed rows to manifest-failed.tsv (the twin raises InvalidDataError on any rc != 0 row and on duplicates)"
  - "A step's command receives the absolute step output dir (data dir resolved at startup); the manifest records the data-dir-relative path the twin expects"

requirements-completed: []

coverage:
  - id: D1
    description: "Driver runs every config for both arms in one session, alternating arms and rotating configs each round, at least 3 rounds for judged configs"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_interleave_227.py#test_schedule_arms_alternate_between_rounds"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_interleave_227.py#test_rounds_below_minimum_refused_for_judged_configs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Bounded load gate and external machine-speed probe before every step, both recorded in the manifest"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_interleave_227.py#test_load_gate_timeout_returns_last_reading_and_flag"
        status: pass
      - kind: integration
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-speed-probe.mjs (prints SPEED-PROBE sf_ms=7539.8 maia_ms=5540.1 total_ms=13079.9)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Manifest in the verdict twin's exact column contract, appended per step, with resume, dry-run and tooling commit"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_interleave_227.py#test_manifest_header_equals_the_verdict_twin_contract"
        status: pass
      - kind: integration
        ref: "real one-step smoke run (stop-rule, a0, smoke config) wrote one rc 0 manifest row with probe_total_ms 12382.9 and dispatch_mode round"
        status: pass
    human_judgment: false
  - id: D4
    description: "Pinned argv per config and arm (D-04)"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_interleave_227.py#test_build_command_depth_ab_configs_both_arms"
        status: pass
    human_judgment: false
  - id: D5
    description: "Depth-ab argv (`--dispatch-mode`, `--ladder-only`) is accepted by scripts/engine-grading-depth-ab.mjs"
    verification: []
    human_judgment: false
    rationale: "Not verifiable in this plan: those flags are Plan 227-04's (it adds them to depth-ab). This plan pins the argv; Plan 227-04 must land before the first judged session. The stop-rule configs were run for real."

duration: 40min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 07: Interleave driver and machine-speed probe Summary

**Committed, tested D-17 protocol: a speed probe (fixed Stockfish node searches plus fixed Maia inferences, about 13 s) and a stdlib driver that interleaves both arms across rotated configs, gates on load, probes before every step, and writes the manifest the Plan 227-03 verdict twin reads.**

## Accomplishments

- **`scripts/engine-speed-probe.mjs`**: one Stockfish engine at `WORKER_HASH_MB` (imported live from `workerPoolState`, not mirrored) runs `go nodes PROBE_SF_NODES` from each of 5 `PROBE_FENS` (`ucinewgame` + `isready` first); then `PROBE_MAIA_INFERENCES` real `policy()` calls through `makeNodeProviders` on the worker-thread session, `resetMaiaRunMemo()` before each. Both stages have an untimed warm-up. Prints exactly `SPEED-PROBE sf_ms=.. maia_ms=.. total_ms=..`.
- **`scripts/engine_interleave_227.py`**: `build_schedule` (configs rotate left by round - 1, arms reversed on even rounds), `build_command` (the D-04 pinned argv), `parse_probe_line`, `wait_for_load` (polls `/proc/loadavg` every 15 s, gate 2.0 exclusive, 600 s bound, timeout logged and never fatal), `completed_steps`, `main`. Per step: load gate, probe subprocess, pinned command (foreground, log to `logs/r{r}-{config}-{arm}.log`), one flushed manifest row. `--resume`, `--dry-run`, `--rounds` below 3 refused unless smoke is the only config, `run-meta.json` with tooling SHA, start time and schedule. The operator runbook (setsid nohup + Monitor, idle box, SIGTERM the node PID, `--resume`) is in the module docstring.
- **Tests (36)**: schedule size, rotation and arm alternation; exact argv for all configs and both arms; probe parsing (good and 6 malformed shapes); load gate (immediate pass, pass after polls, exclusive boundary, timeout, default bound); a run with injected deps (contract header equals the twin's `_MANIFEST_COLUMNS`, rows readable by the twin's `_read_manifest`, refuse to clobber, resume skips only rc 0 and moves failed rows, failed step stops the session, load-timeout logged and run continues); refusals; dry-run runs nothing.

### Frozen probe values (the accept rule, Plan 227-09, cites these)

| Constant | Value |
|---|---|
| `PROBE_FENS` | 5 positions (opening, two middlegames, a quiet middlegame, a pawn endgame) |
| `PROBE_SF_NODES` | 1,800,000 per FEN (warm-up 20,000) |
| `PROBE_MAIA_INFERENCES` | 60 (one untimed warm-up first) |
| `PROBE_MAIA_ELO` | 1500 |
| Measured | sf 7.54 s + maia 5.54 s = 13.08 s timed; second run 13.21 s (0.99% apart); 14.5 s wall including startup. Under sibling-agent load the smoke run read 12.4 s |

At the initial 120,000 nodes / 40 inferences the probe took only 4.2 s, so both were scaled up to land in the plan's 10-20 s window.

### Full 24-step dry-run schedule (`<DATA>` = the `--data-dir`; each line is `node --import ./scripts/lib/frontend-alias-hook.mjs <script> ...`)

```
step 01 r1 stop-p4 a0 mode=round:      stop-rule --dispatch-mode round --procs 4 --pool-size 4 --openings 12 --maia-fifo --out-dir <DATA>/r1/stop-p4/a0
step 02 r1 stop-p4 a1 mode=continuous: stop-rule --dispatch-mode continuous --procs 4 --pool-size 4 --openings 12 --maia-fifo --out-dir <DATA>/r1/stop-p4/a1
step 03 r1 t400-p4 a0 mode=round:      depth-ab --dispatch-mode round --nodes 400 --ladder-only --procs 4 --pool-size 4 --plies 8 --elo 1500 --openings 12 --maia-fifo --out-dir <DATA>/r1/t400-p4/a0
step 04 r1 t400-p4 a1 mode=continuous: depth-ab --dispatch-mode continuous --nodes 400 --ladder-only --procs 4 --pool-size 4 ... --out-dir <DATA>/r1/t400-p4/a1
step 05 r1 t50-p2 a0 mode=round:       depth-ab --dispatch-mode round --nodes 50 --ladder-only --procs 4 --pool-size 2 ... --out-dir <DATA>/r1/t50-p2/a0
step 06 r1 t50-p2 a1 mode=continuous:  depth-ab --dispatch-mode continuous --nodes 50 --ladder-only --procs 4 --pool-size 2 ... --out-dir <DATA>/r1/t50-p2/a1
step 07 r1 t400-p2 a0 mode=round:      depth-ab --dispatch-mode round --nodes 400 --ladder-only --procs 2 --pool-size 2 ... --out-dir <DATA>/r1/t400-p2/a0
step 08 r1 t400-p2 a1 mode=continuous: depth-ab --dispatch-mode continuous --nodes 400 --ladder-only --procs 2 --pool-size 2 ... --out-dir <DATA>/r1/t400-p2/a1
step 09 r2 t400-p4 a1 mode=continuous: depth-ab ... (as step 04) ... --out-dir <DATA>/r2/t400-p4/a1
step 10 r2 t400-p4 a0 mode=round:      depth-ab ... (as step 03) ... --out-dir <DATA>/r2/t400-p4/a0
step 11 r2 t50-p2 a1 mode=continuous:  depth-ab ... (as step 06) ... --out-dir <DATA>/r2/t50-p2/a1
step 12 r2 t50-p2 a0 mode=round:       depth-ab ... (as step 05) ... --out-dir <DATA>/r2/t50-p2/a0
step 13 r2 t400-p2 a1 mode=continuous: depth-ab ... (as step 08) ... --out-dir <DATA>/r2/t400-p2/a1
step 14 r2 t400-p2 a0 mode=round:      depth-ab ... (as step 07) ... --out-dir <DATA>/r2/t400-p2/a0
step 15 r2 stop-p4 a1 mode=continuous: stop-rule ... (as step 02) ... --out-dir <DATA>/r2/stop-p4/a1
step 16 r2 stop-p4 a0 mode=round:      stop-rule ... (as step 01) ... --out-dir <DATA>/r2/stop-p4/a0
step 17 r3 t50-p2 a0 mode=round:       depth-ab ... (as step 05) ... --out-dir <DATA>/r3/t50-p2/a0
step 18 r3 t50-p2 a1 mode=continuous:  depth-ab ... (as step 06) ... --out-dir <DATA>/r3/t50-p2/a1
step 19 r3 t400-p2 a0 mode=round:      depth-ab ... (as step 07) ... --out-dir <DATA>/r3/t400-p2/a0
step 20 r3 t400-p2 a1 mode=continuous: depth-ab ... (as step 08) ... --out-dir <DATA>/r3/t400-p2/a1
step 21 r3 stop-p4 a0 mode=round:      stop-rule ... (as step 01) ... --out-dir <DATA>/r3/stop-p4/a0
step 22 r3 stop-p4 a1 mode=continuous: stop-rule ... (as step 02) ... --out-dir <DATA>/r3/stop-p4/a1
step 23 r3 t400-p4 a0 mode=round:      depth-ab ... (as step 03) ... --out-dir <DATA>/r3/t400-p4/a0
step 24 r3 t400-p4 a1 mode=continuous: depth-ab ... (as step 04) ... --out-dir <DATA>/r3/t400-p4/a1
```

(`stop-rule` = `scripts/engine-dispatch-stop-rule.mjs`, `depth-ab` = `scripts/engine-grading-depth-ab.mjs`; the full argv per line is printed by `--dry-run`. Each non-smoke line carries the same fixed tail `--plies 8 --elo 1500 --openings 12 --maia-fifo` for depth-ab, as shown on steps 03 to 08.)

## Mutation check (acceptance criterion)

| Mutation | Result |
|---|---|
| `build_schedule`: drop the even-round arm reversal (`arm_order = list(arms)`) | `test_schedule_arms_alternate_between_rounds` FAILED, and `test_dry_run_prints_24_steps_and_runs_nothing` FAILED (34 passed, 2 failed). Reverted; 36 passed. |

## Verification run

- `uv run pytest tests/scripts/test_engine_interleave_227.py -q`: 36 passed.
- `uv run ruff check` and `ruff format --check` on the driver and tests: clean. `uv run ty check scripts/ tests/scripts/`: all checks passed.
- `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-speed-probe.mjs`: well-formed `SPEED-PROBE` line, exit 0.
- Real one-step smoke (`--configs smoke --rounds 1 --arms a0`): exactly one rc 0 row, `config=smoke`, `dispatch_mode=round`, `probe_total_ms=12382.9`, step TSV `engine-dispatch-stop-rule-round-elo1500-stopon-*.tsv` present under `r1/smoke/a0/`.
- Dry-run of the default session prints 24 step lines (25 lines containing `engine-` including the probe header).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `--load-wait-max-s` option added to `run`**
- **Found during:** Task 1 smoke verification
- **Issue:** sibling worktree agents kept the box at load 3 to 4 during this wave, so the plan's smoke command (default 600 s gate) would have sat out the full bound per step and could exceed the 10-minute tool cap.
- **Fix:** `--load-wait-max-s` (default `LOAD_WAIT_MAX_S`, the judged value; recorded in `run-meta.json`). The smoke was run with `--load-wait-max-s 30`; it logged `LOAD-GATE-TIMEOUT (running anyway)` and the manifest recorded `load1=3.02`. The docstring says never to lower it for a judged run. The judged value and gate are unchanged.
- **Files modified:** scripts/engine_interleave_227.py, tests (timeout test)
- **Commit:** 7ee8bad65

**2. [Rule 2 - Missing critical] Failed-step handling and resume hygiene**
- **Issue:** the plan says to append a row per step and `--resume` skips rc 0 rows, but the verdict twin raises `InvalidDataError` on any rc != 0 row and on a duplicate (round, config, arm). A resumed failed step would therefore poison the manifest.
- **Fix:** a non-zero step rc is recorded and stops the session (exit 1); `--resume` moves failed rows to `manifest-failed.tsv` before re-running them. A non-resume run refuses to write into a manifest that already has rows. Covered by tests.
- **Commit:** 7ee8bad65

**3. Operator docstring landed in the Task 2 commit.** The Task 1 commit omitted the OPERATOR NOTES block so Task 2 carries it (commit 337691622); the `--load-wait-max-s` note and a `pgrep -f 'engine-(dispatch|grading)'` pattern (the plain `engine-` pattern would also match the probe) were added there.

**Total deviations:** 2 auto-fixed, none changing the judged protocol.

### Environment notes

- `npm ci` in `frontend/` and `uv sync --group maia-inference` were needed in the fresh worktree (lockfile only, no package added).
- The per-plan commit ledger under the shared `.git/worktrees/` path was not written (sandbox rejects it, as in Plan 227-01); `plan_head_before` is the dispatch base SHA and `commits: 2` is `git rev-list --count base..HEAD` before the docs commit.
- `gsd_run` is not available in this subagent environment, so the protected-branch lookup used the five-name fallback (the worktree branch is `worktree-agent-a48d60e77ebe2190e`, not protected).

## Known Stubs

None.

## Threat Flags

None. T-227-12 (machine drift masquerading as a code effect) is mitigated: interleaved arms with rotation, a logged load gate and an external probe per step, at least 3 rounds enforced, manifest appended per step. T-227-SC: stdlib and existing Node modules only, no package installed or added.

## Notes for downstream plans

- **Plan 227-04 must land before the first judged session.** `scripts/engine-grading-depth-ab.mjs` does not yet accept `--dispatch-mode` or `--ladder-only` at this plan's base; the driver pins them as the plan specifies. The stop-rule path (`stop-p4`, `smoke`) ran for real here. Until 227-04 merges, a dry-run is the only check possible for the three depth-ab configs.
- Plan 227-11 (the orchestrator) launches the judged session per the module docstring, never from an executor subagent. The judged run of this driver was deliberately not performed here.
- The twin expects the manifest at `<data>/gate/throughput/manifest.tsv`, so the data dir to pass is `reports/data/continuous-dispatch-227/gate/throughput`.

## Self-Check: PASSED

- Files exist: scripts/engine-speed-probe.mjs, scripts/engine_interleave_227.py, tests/scripts/test_engine_interleave_227.py.
- Commits exist: 7ee8bad65, 337691622.
