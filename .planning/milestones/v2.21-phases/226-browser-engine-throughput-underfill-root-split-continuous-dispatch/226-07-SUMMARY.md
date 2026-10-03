---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 07
subsystem: engine-measurement
tags: [step-0, calibration-null, move-quality, cBFTV-trace, D-09, D-10, D-13, D-14, D-16, D-17, D-19]

requires:
  - phase: 226-01..06
    provides: "harness seed hook + warm arm, trace tool, fixture builder, protocol, verdict CLI, content instrument"
provides:
  - "fixtures/engine/move-quality-226.tsv (60 rows, D-14)"
  - "reports/data/engine-throughput-226/step0/ (profiles, content, A0 throughput/stop, warm arm, MQ A0a/A0b, cBFTV traces, calibration nulls, design-inputs.json)"
  - "reports/data/sweep-226-{a0a,a0b}-{human1100,light1300,light1900,deep1500,deep2300}/ ledgers (force-added)"
affects: [226-08, 226-12]

actuals:
  tasks: 3
  commits: 5
  plan_head_before: effcec443260ca674a02c3d4478bf4ef7d433683
  plan_head_after: 40f59bc3e

key-files:
  created:
    - fixtures/engine/move-quality-226.tsv
    - reports/data/engine-throughput-226/step0/design-inputs.json
    - reports/data/engine-throughput-226/step0/calibration/verdict-a0b-vs-a0a.json
  modified:
    - scripts/lib/node-engine-providers.mjs
---

# Phase 226 Plan 07: Step 0 Summary

**Step 0 ran exactly as pre-registered. The calibration null holds with a small pooled se; design-inputs computes every constant with no escalation.**

## Performance

- Started 2026-09-28 11:17 (fixture build), wall-clock driver 12:02-13:53, sweeps 13:55 -> 2026-09-29 02:39.
- Orchestrator-inline throughout (setsid nohup + Monitor / background waiters); no executor subagent ran or backgrounded any step.

## Tooling commits

- Task 1 started from `effcec443`. The fixture was built from `5c2a8deb0`, a diagnostic-only change to the Stockfish child stderr (see Deviations), and committed as `fc3086475`.
- Wall-clock data was measured from T = `27121e329` (fixture + a revert of stray commits; no engine code change vs `fc3086475`).
- Task 3 worktree F = `0f54b1feb`.

## Accomplishments

### Task 1: widened fixture (`fc3086475`)
`FIXTURE-CHECK rows=60 ok`: 12 maia-blindness base rows plus 6 bands x 8 lichess CC0 puzzles.

| band | evaluated | kept | rejected_top_move | rejected_gap | skipped |
|---|---|---|---|---|---|
| 1000-1200 … 2000-2200 (each) | 8 | 8 | 0 | 0 | 0 |

### Task 2: wall-clock step 0 (`0f54b1feb`)
1-min load average before every step, all below 2.0:

| step | load |
|---|---|
| profile 50 run 1 / run 2 | 1.81 / 1.95 |
| profile 400 run 1 / run 2 | 1.98 / 1.86 (run-1 rerun at 13:53: 1.58) |
| content clear / warm | 1.74 / 1.73 |
| t50-p4 / t400-p4 | 1.48 / 1.75 |
| t50-p2 / t400-p2 | 1.87 / 1.99 |
| stop / warm-arm | 1.36 / 1.89 |

- Throughput TSVs: 32 rows each, `root_split_calls` 0, pool_size matches the directory (4/4/2/2).
- **D-17 (grade share of non-root nodes with >8 candidates):** 50 nodes 0.466 / 0.459, 400 nodes 0.359 / 0.359. Below 0.5 at both budgets, so `CANDIDATE_CAP_ARM_ACTIVE=False`.
- **Content, prototype split:**
  - Clear Hash: mean |Δes| 0.0209, p95 0.0785.
  - Warm hash: mean 0.0149, single-vs-single noise floor 0.0168.
- **Stop rule A0:** max wall 8,253 ms.
- **Warm arm:** 4 games, 60 plies, 0 differing.

### Task 3: nulls, traces, design inputs (`40f59bc3e`)

**Calibration.** Ten cells at 50 games per (cell, anchor), 2,000 games in total. Each search cell took one wasm crash-resume after ~8.5h; human cells resumed once. No fast-crash aborts.

| comparison | Maia pooled | SF pooled | null control | verdict |
|---|---|---|---|---|
| A0b vs A0a (criterion basis) | +0.3 ± 26.1 | +11.5 ± 27.3 | Maia +12.3, SF +86.9 (within 165/149) | holds, no shape-guard cell |
| A0a vs July-21 (report-only) | −46.5 ± 36.4 | −17.9 ± 27.4 | SF −177.4 > 149 | void, shape guard at (1500, 0.5) |

**MQ.** All four runs gave 49 pass / 11 regression on both the bot pick and the analysis pick. d0 = 0 in both stop modes, so the allowance is 1 / 1.

**Design inputs** (no `DESIGN-INPUT-ESCALATE`):

| constant | value |
|---|---|
| EXPECTED_MQ_POSITIONS | 60 |
| MQ_ALLOWANCE_OFF / _ON | 1 / 1 |
| CALIBRATION_THRESHOLD_MAIA | 85.0 (se floor 51.2) |
| CALIBRATION_THRESHOLD_SF | 53.54 (se floor, above the 50 base) |
| ROOT_SPLIT_MAX_T50_WALL_RATIO | 0.97 |
| CONTENT_MAX_WARM_MEAN_ABS_DES | 0.0252 |
| CONTENT_MAX_CLEAR_MEAN_ABS_DES | 0.0168 |
| STOP_RULE_MAX_WALL_MS | 12,100 |
| CANDIDATE_CAP_ARM_ACTIVE | False |

## Findings for Plan 226-08

1. **The prototype split already exceeds the Clear-Hash content bound.** Measured 0.0209 against a bound of 0.0168, which is 1.0 x the warm noise floor per protocol section 7. Unless the pool-source split differs materially from the prototype, A21S is likely to fail its content criterion under Clear Hash. It passes comfortably warm (0.0149 vs 0.0252).
2. **`duplicate-expansion` TRACE-ANOMALY lines appear at A0 too.** Counts: c1 16, c2 17, c4 12, A2 candidate c4 14.
   - They cluster on repetition and perpetual positions (WwKKM `g5h5:0;b2c3:#-1`, g687537-p48 `g1h1:0`, I3vZ1), where the same leaf FEN is regraded in a later round.
   - The duplicate-FEN group counts are near-identical across all four traces (11/11/10).
   - This is a pre-existing cycle/transposition effect or a quirk in how the tool keys leaf paths, not a signature introduced by A2. Protocol section 6 still counts any TRACE-ANOMALY as a bug signature, so 226-08 must classify it explicitly (likely an override or a tool-definition fix) before A2 re-enters the gate.
3. **The July-21 drift is not explained by noise, but the comparison is void.** It is report-only per D-09 and changes no criterion.

## Deviations from Plan

1. **[Rule 3, blocking] Fixture build crashed twice with a Stockfish child `exited unexpectedly (code=7)` about 90s in, with no cause on record.**
   - The child's stderr was piped and never read. A standalone repro (216 then 140 positions at d20, same Clear Hash + MultiPV 2 sequence) did not crash, and the children write nothing to stderr.
   - Fix `5c2a8deb0` (diagnostic only): put a bounded stderr tail into the death reason. The rebuild then succeeded.
   - The root cause remains unknown. Both crashes were `setsid nohup` launches; the passing run was in the foreground.
   - The fixture is deterministic (SHA-1 order, first 8 keepers per band), so the retry does not bias selection.
2. **A concurrent session committed two unrelated commits onto this branch.** They were `3fb2ed663 fix(activity)` and `a960ab52f`. With the user's approval they were cherry-picked onto local main (`de7ce598b`, `fcb8fcbf0`, unpushed) and reverted here (`27121e329`).
3. **The first `profile-400-run1` run exited 0 without writing its JSON.** It printed TOTAL, then no histogram and no "Wrote" line. It was rerun alone on an idle box (load 1.58); its histogram matches run 2 within about 1.5% per bucket.
4. **The plan's `cells-to-json --cells-tsv <glob>` command needed one flag per file** (argparse `action="append"`); it was passed that way.

## Issues Encountered

- Monitors expire every 30 min. Overnight waiting used a single background watcher (completion / ABORT / 90-minute stall).

## Next Phase Readiness

- Plan 226-08 can write the accept rule from committed numbers. The two open items are findings 1 and 2 above.

## Self-Check: PASSED

- Task 1 verify: `FIXTURE-CHECK rows=60 ok` and the fixture is tracked.
- Task 2 verify: the python ls-files check passes (all 11 artifact groups present).
- Task 3 verify: design-inputs prints 10 DESIGN-INPUT lines and no ESCALATE; the verdict and design-inputs JSON are tracked.
- `git worktree list` shows only the main checkout.
