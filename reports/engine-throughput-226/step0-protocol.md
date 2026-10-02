# Phase 226 step-0 protocol

## 1. Purpose and status

**Committed:** 2026-09-28, before any step-0 run exists under `reports/data/engine-throughput-226/`.

Like `reports/bot-parity-199/accept-rule.md` and `reports/engine-search-fixes-225/accept-rule.md`,
this is a decision contract, not a narrative: every rule below is fixed in advance and is
NOT editable once step-0 data exists. Any deviation is a separate dated override document, in
the shape of `reports/grading-ladder/override-2026-07-31.md`, never an edit to this file. The
accept rule (Plan 226-08) restates every rule here with the measured numbers filled in from
step 0, and its machine-readable twin is `scripts/engine_throughput_226_verdict.py` — every
numeric constant in the accept rule equals a frozen constant there.

This document discharges CONTEXT.md decisions D-09, D-10, D-11, D-13, D-14, D-15, D-16, D-17,
D-19 for the pre-registration step. It does not decide arm ship/hold outcomes — those come from
the accept rule after step-0 and arm data exist.

## 2. Step-0 runs and parameters

**Idle-box rule (mandatory before any wall-clock run in this section):** `/proc/loadavg`'s
first field below 2.0, no `remote_eval_worker` process running, and nothing else heavy (no
test suite, no other sweep, no concurrent wall-clock run from this same list) running at the
same time. Wall-clock runs (throughput, stop rule, profiling) never overlap each other, a
calibration sweep, or a test suite; move quality and calibration are node-deterministic and
may overlap each other only (Pattern 9 sequencing, carried from Phase 225).

The step-0 runs, in the order they are launched:

1. **Profiling (D-16, D-17, Pattern 10).** `profile_search.mjs` at `50 4 4 1` and `400 4 4 0`,
   each config run twice (spread check). Extended with an `isRoot = (f === rootFen)` tag and a
   histogram of grade ms by `(isRoot, grading depth, candidate-count bucket)` — buckets `≤4`,
   `5-8`, `9-12`, `13+` — to decide D-17 (section 5).
2. **Root-split content instrument (D-16, Pattern 2).** Extended `split_root.mjs` in prototype
   mode, over the 16 throughput positions plus the widened move-quality fixture roots (D-14),
   in both Clear-Hash mode (split vs single, absolute since single-vs-single is exactly 0) and
   warm mode (split vs single, and single-vs-single on two differently-warmed engines, to get
   the warm noise floor).
3. **Depth-ab A0 baselines (D-04, Pattern 7).** Four configs: 50 nodes / `--procs 4` / pool 4
   (bot budget, desktop), 400 nodes / `--procs 4` / pool 4 (analysis budget, desktop), 50 nodes
   / `--procs 4` / pool 2 (bot budget, mobile pool-of-2), 400 nodes / `--procs 2` / pool 2
   (analysis budget, mobile pool-of-2, since `computePoolSize()` sets both concurrency and pool
   size to 2 on mobile).
4. **Stop-rule A0 run.** Stop rule ON, `--guard-window 0.09` (`W = 0.09`, carried unchanged from
   Phase 225 `d02-allowance.md`: `ROOT_GUARD_BOOST_ALLOWANCE` A = 0.04, `W` = marginThreshold
   0.05 + A 0.04).
5. **D-03 warm arm.** `calibration-determinism.check.mjs --no-clear-hash --games 4`, on a
   grading-only pool separate from the adjudication/anchor pool (RESEARCH Pattern 5) — measures
   the shipped warm-hash noise floor.
6. **Move-quality fixture build (D-14).** `build-move-quality-fixture.mjs` with its own
   committed constants (SHA-1-of-PuzzleId ordering, rating-band stratification, d20 MultiPV 2
   filter, `MIN_GAP_CP`), landing `fixtures/engine/move-quality-226.tsv` (≥ 50 rows: 12
   `maia-blindness.tsv` rows plus lichess CC0 puzzles from `detector_fixture_test.csv`).
7. **MQ A0a and A0b (D-14 allowance floor).** Two fresh-process `engine-move-quality.mjs` runs
   on the widened fixture, per stop mode (on and off) — the run-to-run flip count `d0` feeds
   the `A = max(1, d0)` allowance in section 4.
8. **cBFTV trace (D-13, Pattern 3).** `engine-search-trace.mjs` at A0 c=1, c=2, c=4, and an
   A2-candidate at c=4 (the gate config), on `cBFTV` and the other 11 `maia-blindness.tsv` rows
   as controls.
9. **Calibration A0a and A0b (D-09, D-10, D-19).** Two in-session A0 sweeps on the five
   Phase 199 cells with their pinned anchors, **50 games per (cell, anchor)**, launched through
   `bin/preset-supervisor.sh` — never the bare harness driver. A0a uses the supervisor's default
   seed (1). A0b uses seed 2 via a new `PRESET_SUPERVISOR_SEED` hook in
   `bin/preset-supervisor.sh` (default 1, so every other caller is unaffected) — same-seed Maia
   games are byte-identical (RESEARCH F-7), so A0a and A0b need different seeds or the Maia
   family's null is degenerate. `PRESET_SUPERVISOR_ANCHORS` is mandatory on every cell — omitting
   it silently re-brackets onto a different anchor pool (runbook §1 "Do NOT omit").

   | Cell | bot_elo | bot_blend | Pinned anchors (`PRESET_SUPERVISOR_ANCHORS`) |
   |---|---|---|---|
   | human1100 (null control) | 1100 | 0.00 | maia700,maia1100,sf0,sf3 |
   | light1300 | 1300 | 0.05 | maia1100,maia1500,sf3,sf5 |
   | light1900 | 1900 | 0.05 | maia1100,maia1500,sf3,sf5 |
   | deep1500 | 1500 | 0.50 | maia1500,maia1900,sf3,sf5 |
   | deep2300 | 2300 | 0.50 | maia1500,maia1900,sf3,sf5 |

   Ledgers land under `reports/data/sweep-226-a0a-{cell}` and `reports/data/sweep-226-a0b-{cell}`
   (gitignored; force-add the `-cells.tsv` aggregates only, Phase 225 precedent).
10. **Drift cross-checks (report-only, D-09).** A0a's own sweep against the committed July-21
    curves (`calibration_parity_verdict.py --old-json reports/data/bot-curves-internal-scale.json`)
    and the Maia-anchor identity check (`maia_anchor_identity`, this plan's Task 2) between A0a's
    ledgers and the committed `sweep-225-a0-*` ledgers, restricted to matching
    `(pass, anchor, game_index)` keys. Neither is a criterion — A0a-vs-A0b is the only in-session
    null the powered thresholds are derived from (D-09: never judge against July-21).

## 3. Calibration rules (D-10)

- **Base thresholds** (carried from Phase 199/225, unchanged): Maia 85 Elo, SF 50 Elo.
- **Null-control thresholds** (carried from Phase 199, unchanged): Maia 165 Elo, SF 149 Elo —
  the validity gate that renders a comparison `void` stays exactly as `calibration_parity_verdict.py`
  computes it.
- **Powered threshold per family** = `max(base_threshold, 1.96 x A0b-vs-A0a pooled se)` — the
  se-multiplier is **1.96** (the 95% normal quantile, matching `NORMAL_95_Z` elsewhere in this
  codebase's calibration tooling).
- **Model check:** if the null's own `|A0b-vs-A0a pooled shift|` exceeds that threshold, the
  threshold inflates to the observed `|shift|` and the run is flagged `model_check_fired` — the
  power model under-predicted the null's own spread.
- **Escalation:** if `|A0b-vs-A0a pooled shift|` exceeds `2 x base_threshold`, the run escalates
  to the user regardless of the inflated threshold — a null drift too large to absorb by
  inflating the threshold at all.
- **Z-based shape guard (replacing the Phase 199 CI-overlap guard, D-10, RESEARCH Pattern 6):**
  a cell fires the guard iff `abs(shift) / se_shift > 1.96` in BOTH families for that cell — not
  the Phase 199 "falls outside the old CI in both families" rule, which fires at a rate
  independent of sample size and does not shrink as N grows.
- **Real (powered) shift, per arm-vs-A0a comparison:** with a valid null control (both
  families' `null_control.within_threshold` true), a real shift exists iff either family's
  `|pooled shift|` exceeds its derived threshold, or the z-based shape guard fires on a cell. A
  void comparison (null control outside its Phase 199 threshold) answers nothing about whether a
  real shift occurred.
- **D-11 refit trigger:** `refit_required` is true iff any SHIPPED item's attribution comparison
  is a real shift. A void comparison on a shipped item escalates to the user — never a silent
  no-refit. A held item's own real shift never triggers a refit (D-11 covers shipped tree-shape
  changes only).

## 4. Move-quality rules (D-14, D-15)

- **Regression margin:** `es(bot_move) - es(correct) <= -0.05` on the `argmaxLine` pick — the
  bot's own selector, judged exactly as Phase 225's `MQ_REGRESSION_MARGIN`.
- **Paired criterion**, per (arm pair, stop mode): the arm HOLDS iff
  `(pass-to-regression flips) - (regression-to-pass flips) <= A`, where `A = max(1, d0)` and
  `d0` is the count of positions whose verdict differs between the MQ A0a and A0b runs in that
  stop mode (step 0, item 7 above). Every counted pass-to-regression flip must be reproduced by
  a fresh-process rerun (RESEARCH Pitfall 8) before it counts against the arm.
- **McNemar's exact one-sided p** on the discordant pairs is computed and reported alongside
  every paired comparison — report-only, never a criterion.
- **Move quality blocks regardless of calibration (D-15).** D-11's conditional refit covers
  persona strength only; an item that fails its move-quality criterion is held even when
  calibration would otherwise ship it.

## 5. D-17: candidate-cap arm activation

The non-root candidate-cap arm exists iff the share of total grade ms spent on non-root grades
with MORE THAN 8 candidates is at least 0.5 (50%) at EITHER judged budget (50-node or 400-node),
taking the mean of the two profile runs per budget from step-0 item 1. If it fires:

- The cap value is **8 candidates on non-root nodes only** (the root grade is never capped —
  root candidates are exactly the legal moves after Maia's `truncateAndRenormalize`, and D-17's
  premise is specifically non-root CPU dominance).
- The arm is **A21SC**, stacking on A21S (D-12's arm chain becomes A0 → A2 → A21 → A21S → A21SC
  when the cap fires; otherwise the chain stops at A21S).

`CANDIDATE_CAP_ARM_ACTIVE` is the boolean design input the verdict CLI's `design-inputs`
subcommand computes from this rule (section 7) — never hand-set.

## 6. D-13 bug signatures

The `cBFTV` trace (step-0 item 8) is scored against two disjoint signatures:

- **Bug signature** — any of: a `TRACE-ANOMALY` line emitted by `engine-search-trace.mjs`; a
  node marked blocked in round `r` (per the A2 underfill fix's `blockedThisRound`) that is STILL
  unselectable in round `r+1`, read from the per-round expansion sets the trace tool records; or
  an A2 root line whose `visits` stop rising across rounds while a selectable leaf still exists
  in the tree. Any of these means item 2 (round underfill) has a bug that must be fixed in
  `mctsSearch.ts` and the arm re-measured before it re-enters the gate.
- **Side-effect signature** — NO bug signature is present, AND the drop of `e4c6`'s value below
  `e2g4`'s across A0-vs-A2 rounds traces to specific expansions whose grades are legitimate
  Stockfish output (a d10-floor grade at a node that misses a forced mating line, consistent
  with the leading hypothesis in RESEARCH Pattern 3). This is recorded as an explained tree-shape
  side effect in `report.md`, not a defect — item 2 proceeds to gate measurement unchanged.

## 7. Design-input derivation rules (D-16)

Each of the following is a FORMULA over step-0 data, computed mechanically by the verdict CLI's
`design-inputs` subcommand (Plan 226-05) — never chosen by eye after looking at the numbers:

- `EXPECTED_MQ_POSITIONS` = the widened fixture's row count (step-0 item 6; ≥ 50 by
  construction).
- `MQ_ALLOWANCE_OFF` / `MQ_ALLOWANCE_ON` = `max(1, d0)` per stop mode, from the MQ A0a-vs-A0b
  run-to-run flip count (step-0 item 7; section 4).
- `CALIBRATION_THRESHOLD_MAIA` / `CALIBRATION_THRESHOLD_SF` = the powered per-family thresholds
  from section 3, computed by `null_check` (this plan's Task 1) over the A0a-vs-A0b calibration
  sweep (step-0 item 9).
- `ROOT_SPLIT_MAX_T50_WALL_RATIO` = `1 - G`, where `G = max(0.03, 0.5 x P)` rounded DOWN to the
  nearest 0.01, and `P` = (sum of single-call root grade ms minus sum of split root grade ms,
  over the 16 throughput positions, Clear-Hash prototype content run from step-0 item 2) divided
  by (sum of A0 T-50 pool-4 ladder wall ms, step-0 item 3). `G` is floored at 0.03 so a
  measured-negligible split gain never produces a near-zero (over-tight) wall-ratio bound.
- `CONTENT_MAX_WARM_MEAN_ABS_DES` = `1.5 x` the warm single-vs-single mean `|Δes|` (step-0 item
  2's warm-mode noise floor).
- `CONTENT_MAX_CLEAR_MEAN_ABS_DES` = `1.0 x` that SAME warm noise floor — the split may not
  change grade content by more than the shipped warm hash already does, even under Clear-Hash
  measurement.
- `STOP_RULE_MAX_WALL_MS` — derived by Phase 225 RESEARCH C-7's rule against the step-0 A0
  idle-box max wall from step-0 item 4 (expected **12,100 ms**, the 5+3 full-clock think
  deadline at the tightest common preset, matching Phase 225's own `STOP_RULE_MAX_WALL_MS`).
- `CANDIDATE_CAP_ARM_ACTIVE` — per section 5.

**Carried-over constants** (unchanged from Phase 225, not re-derived): `THROUGHPUT_MAX_WALL_RATIO`
1.05, `STOP_RULE_MIN_EARLY_STOP_RETENTION` 0.5, guard window 0.09, 16 throughput positions, 16
stop-rule positions.

## 8. What must not happen

- Running any step-0 run, or backgrounding one, from a `gsd-executor` subagent — it dies with
  the agent (Phase 197 wave 2). Every step-0 run is orchestrator-inline (`setsid nohup` +
  Monitor for anything long, under the resume-on-crash supervisor for calibration sweeps).
- Concurrent wall-clock runs (throughput, stop rule, profiling) with each other, a calibration
  sweep, or a test suite.
- Launching a calibration cell without `PRESET_SUPERVISOR_ANCHORS`, or without
  `bin/preset-supervisor.sh` (the crash supervisor is mandatory, never the bare
  `calibration-harness.mjs` driver).
- Pooling A0a and A0b (or any two sweeps) by concatenating `-cells.tsv` files —
  `calibration_anchor_fit.py`'s `load_bot_cells` overwrites per `(cell, anchor)`, so
  concatenation silently drops one run's data (RESEARCH Pattern 6).
- Comparing any arm against the July-21 curves as a CRITERION — A0a vs July-21 is report-only
  (D-09; section 2, item 10). All calibration comparisons that decide anything are against the
  same-session A0a.
- Implementing continuous dispatch or a round-mode flag in this phase — D-01 and D-07 name that
  as Phase 227 scope; the only 227-facing deliverable here is the D-03 no-Clear-Hash arm.
