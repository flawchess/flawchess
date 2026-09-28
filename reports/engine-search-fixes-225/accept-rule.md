# Engine search fixes (Phase 225): accept rule

**Committed:** 2026-09-27, before any gate run. Like `reports/bot-parity-199/accept-rule.md`
and `reports/continuous-dispatch/accept-rule.md`, this is a decision contract, not a narrative:
every threshold below is fixed in advance and is not editable once gate data exists. It
discharges CONTEXT.md decisions D-04 (report-only deadline exposure), D-11 (accept rule before
data), D-12 (stacked arms), D-13 amended (per-criterion arms and thresholds), and D-14 (ship
only passing items, never refit).

Its machine-readable twins are `scripts/engine_search_fixes_verdict.py`, whose frozen constants
carry these exact numbers, and `scripts/calibration_parity_verdict.py`, which carries the
Phase 199 calibration thresholds reused verbatim in §4. Once gate data exists under
`reports/data/engine-search-fixes-225/`, this file and those constants are read-only for the
duration of the measurement — any deviation is a separate dated override document, in the shape
of `reports/grading-ladder/override-2026-07-31.md`, never an edit to this file.

## 1. Arms (D-12)

Stacked arms, since item 3 (findability) does not touch bot search trees and is judged
separately:

| Arm | Definition |
|---|---|
| `A0` | The commit that adds this file. Baseline — engine code identical to `main` (only harness tooling from Plans 225-01/225-02 has landed). |
| `A2` | The last commit whose subject carries the `(225-04)` scope and touches `frontend/src/lib/engine` — item 2 (round underfill fix) on top of `A0`. |
| `A21` | The last commit whose subject carries the `(225-05)` scope and touches `frontend/src` — item 2 + item 1 (root comparability guard) on top of `A2`. |
| `FINAL` | The last commit whose subject carries the `(225-06)` scope and touches `frontend/src/lib/engine` — item 3 (findability fallback), report-only item-3 check only, on top of `A21`. |

Item 2 is attributed by A2 vs A0. Item 1 is attributed by A21 vs A2. Item 3 ships
independently of every bot gate (D-14) once its own unit tests are green.

### Content assertions (every arm must pass before any run — Pitfall 3)

- `git diff` between any two arms restricted to `scripts/`, `bin/`, `frontend/package.json`,
  `frontend/package-lock.json` is empty — no arm changes tooling, only engine code.
- `A0`'s `frontend/src/lib/engine` is identical to `git merge-base main {A0}` — A0 is a clean
  tooling-only baseline.
- `A0` to `A2` engine diff is limited to `mctsSearch.ts` and
  `__tests__/mctsSearch.roundFill.test.ts`.
- `A2` to `A21` engine diff is limited to `mctsSearch.ts`, `types.ts`, `botBudget.ts`,
  `__tests__/mctsSearch.test.ts`, and `frontend/src/hooks/useFlawChessEngine.test.tsx`.
- `A21` to `FINAL` leaves `mctsSearch.ts`, `types.ts`, and `botBudget.ts` untouched (item 3
  only touches `findability.ts`/`treeCommon.ts` and their tests).

### Worktree procedure (Pattern 4, Pitfall 7)

Arms run from detached worktrees `../flawchess-225-{arm}` (`git worktree add
../flawchess-225-{arm} <SHA>`), each with its own `( cd frontend && npm ci )` — the harness
alias hook and `node-engine-providers.mjs` resolve their own repo root from
`import.meta.url`, so each worktree measures its own engine code. All harness output is copied
back from the worktree into the main checkout's `reports/data/engine-search-fixes-225/` (and
`sweep-225-*` for calibration) **before** the worktree is removed — harness output left in a
removed worktree is lost. The four arm SHAs (A0, A2, A21, FINAL) are recorded in `report.md`
once each lands.

## 2. Recorded design inputs (D-02)

From `d02-allowance.md` (Plan 225-03, Task 2), measured before this file:

- `ROOT_GUARD_BOOST_ALLOWANCE` **A = 0.04**
- Guard window **W = marginThreshold 0.05 + A 0.04 = 0.09**

`W = 0.09` is the value every stop-rule gate run below passes via `--guard-window`, and the
value Plan 225-05 sets as `FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance`.

## 3. Run parameters (exact command lines, run from each arm worktree root)

All wall-clock runs (stop rule, throughput) run alone on an idle box — never concurrently with
each other, a calibration sweep, or a test suite. Move quality and calibration are
node-deterministic and may overlap each other only.

### Throughput (T-50, T-400) — A0 and A2 only

Judge the `depth = ladder` rows only; flat `d14` rows are informational (per
`reports/continuous-dispatch/accept-rule.md` §1-2). `maia_peak_inflight` must read 1 on every
judged row.

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 50 --depths 14 --ladder --procs 4 --plies 8 --elo 1500 --openings 12 --maia-fifo \
  --out-dir reports/data/engine-search-fixes-225/<arm>
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 400 --depths 14 --ladder --procs 4 --plies 8 --elo 1500 --openings 12 --maia-fifo \
  --out-dir reports/data/engine-search-fixes-225/<arm>
```

**Run order:** a0-50, a2-50, a0-400, a2-400.

### Stop rule (A0 report-only, A2, A21)

`--dispatch-mode` is a required label only, always `round` here.

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs \
  --dispatch-mode round --openings 12 --maia-fifo --root-trace --guard-window 0.09 \
  --out-dir reports/data/engine-search-fixes-225/<arm>
```

### Move quality (a0 off, a2 off, a2 on, a21 on, final off)

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs \
  --arm <arm> --stop-rule <on|off> --out-dir reports/data/engine-search-fixes-225/<arm>
```

Re-runs (RESEARCH Pitfall 8) go into `mq-{mode}-rerun` only for the (arm, mode) pairs the
verdict script's `reruns` subcommand lists (a pass-to-regression flip counts only if a fresh
process reproduces it):

```bash
uv run python scripts/engine_search_fixes_verdict.py reruns \
  --data-dir reports/data/engine-search-fixes-225
```

### Calibration (A21 first)

The five launch blocks of `reports/bot-parity-199/runbook.md` §1, reused verbatim (same
anchors, 24 games per (cell, anchor), `bin/preset-supervisor.sh` mandatory — never the bare
harness driver), with a Phase-225-specific `PRESET_SUPERVISOR_DIR` and supervisor name per
cell: `reports/data/sweep-225-a21-{cell}`, supervisor name `a21-{cell}`, for
`{cell}` in `human1100`, `light1300`, `light1900`, `deep1500`, `deep2300` (matching the
runbook's own cell names). `PRESET_SUPERVISOR_ANCHORS` must be set on every block — omitting it
silently re-brackets onto different anchors (runbook §1 "Do NOT omit").

A21 verdict, against the committed internal-scale curves:

```bash
uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/bot-curves-internal-scale.json \
  --new-cells-tsv reports/data/sweep-225-a21-human1100/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-225-a21-light1300/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-225-a21-light1900/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-225-a21-deep1500/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-225-a21-deep2300/*-cells.tsv \
  --out-json reports/data/engine-search-fixes-225/calibration/verdict-a21-vs-july.json
```

### Branch runs (only if `calibration_branch(primary)` is not `"none"` — §4)

A0 and A2 sweeps use `sweep-225-a0-{cell}` / `sweep-225-a2-{cell}` (same five cells, same
anchors, same 24-games-per-anchor procedure). Each arm's per-cell aggregates are converted to
an `--old-json`-shaped payload via the verdict script's own A0-cells converter:

```bash
uv run python scripts/engine_search_fixes_verdict.py cells-to-json \
  --cells-tsv reports/data/sweep-225-a0-human1100/*-cells.tsv \
  --cells-tsv reports/data/sweep-225-a0-light1300/*-cells.tsv \
  --cells-tsv reports/data/sweep-225-a0-light1900/*-cells.tsv \
  --cells-tsv reports/data/sweep-225-a0-deep1500/*-cells.tsv \
  --cells-tsv reports/data/sweep-225-a0-deep2300/*-cells.tsv \
  --out-json reports/data/engine-search-fixes-225/calibration/a0-cells.json
# repeat for a2-cells.json from the sweep-225-a2-{cell} dirs
```

Then the branch verdicts, each against the A21 sweep's own five `*-cells.tsv`:

```bash
# a0-vs-july: A0's own cells against the committed July-21 curves
uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/bot-curves-internal-scale.json \
  --new-cells-tsv reports/data/sweep-225-a0-*/*-cells.tsv \
  --out-json reports/data/engine-search-fixes-225/calibration/verdict-a0-vs-july.json
# a2-vs-july: A2's own cells against the committed July-21 curves
uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/bot-curves-internal-scale.json \
  --new-cells-tsv reports/data/sweep-225-a2-*/*-cells.tsv \
  --out-json reports/data/engine-search-fixes-225/calibration/verdict-a2-vs-july.json
# a2-vs-a0: attribute item 2's own effect, old side = A0's converted cells
uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/engine-search-fixes-225/calibration/a0-cells.json \
  --new-cells-tsv reports/data/sweep-225-a2-*/*-cells.tsv \
  --out-json reports/data/engine-search-fixes-225/calibration/verdict-a2-vs-a0.json
# a21-vs-a2: attribute item 1's own effect, old side = A2's converted cells
uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/engine-search-fixes-225/calibration/a2-cells.json \
  --new-cells-tsv reports/data/sweep-225-a21-*/*-cells.tsv \
  --out-json reports/data/engine-search-fixes-225/calibration/verdict-a21-vs-a2.json
```

### Data layout

Exactly the layout `scripts/engine_search_fixes_verdict.py` reads, under
`reports/data/engine-search-fixes-225/`:

```
{arm}/stop/                    # engine-dispatch-stop-rule-*.tsv (arm in a0, a2, a21)
{arm}/throughput-50/           # engine-grading-depth-ab-*.tsv (arm in a0, a2)
{arm}/throughput-400/          # engine-grading-depth-ab-*.tsv (arm in a0, a2)
{arm}/mq-off/                  # engine-move-quality-*.tsv (arm in a0, a2, final)
{arm}/mq-on/                   # engine-move-quality-*.tsv (arm in a2, a21)
{arm}/mq-off-rerun/            # only if MQ-2 flips (a2)
{arm}/mq-on-rerun/             # only if MQ-1 flips (a21)
calibration/verdict-a21-vs-july.json    # always required
calibration/verdict-a0-vs-july.json     # conditionally required (calibration_branch != "none")
calibration/verdict-a2-vs-july.json     # conditionally required
calibration/verdict-a2-vs-a0.json       # conditionally required
calibration/verdict-a21-vs-a2.json      # conditionally required
calibration/a0-cells.json               # conditionally required
calibration/a2-cells.json               # conditionally required
```

### Sequencing

Wall-clock runs (stop rule, throughput) run alone on an idle box, never concurrently with each
other, a calibration sweep, or a test suite. Move quality and calibration are node-deterministic
and may overlap each other only.

## 4. Criteria, in evaluation order

Each criterion's twin constant name is given so a threshold in this document can be
grep-verified against `scripts/engine_search_fixes_verdict.py`.

1. **Validity** — content assertions (§1) pass; identical position sets between compared arms
   (`EXPECTED_THROUGHPUT_POSITIONS` = 16, `EXPECTED_STOP_POSITIONS` = 16,
   `EXPECTED_MQ_POSITIONS` = 12); FIFO admissibility (`maia_peak_inflight` = 1 and
   `maia_fifo` = true on every judged throughput row — an inadmissible row is excluded, never
   averaged in).
2. **T-50 and T-400 (throughput, A2 vs A0)** — `A2 ladder wall_ms sum <= THROUGHPUT_MAX_WALL_RATIO
   1.05 x A0 ladder wall_ms sum`, per budget (50 and 400 nodes). Item 2 is a confirmed bug fix
   expected to *lower* wall clock; 1.05 is a no-regression bound with 5% idle-box wall noise, not
   a target.
3. **MQ-2 (move quality, A2 vs A0, stop rule off)** — regression = `es(bot_move) - es(correct)
   <= -MQ_REGRESSION_MARGIN 0.05`. A2 stop-off regression count must not exceed A0 stop-off
   regression count. A pass-to-regression flip counts only if a fresh-process re-run reproduces
   it (RESEARCH Pitfall 8).
4. **S1 (stop rule, A21)** — `A21 max wall_ms <= STOP_RULE_MAX_WALL_MS 12,100 ms`, the 5+3
   full-clock think deadline (`computeThinkDeadlineMs` at the tightest common preset not
   already binding at A0, RESEARCH C-7).
5. **S2 (stop rule, A21 vs A2)** — `A21 early-stop count >= STOP_RULE_MIN_EARLY_STOP_RETENTION
   0.5 x A2 early-stop count`. The guard must not effectively disable the clear-winner branch.
   Trivial-pass when A2 has zero early stops.
6. **MQ-1 (move quality, A21 vs A2, stop rule on)** — same regression definition and re-run rule
   as MQ-2. A21 stop-on regression count must not exceed A2 stop-on regression count.
7. **Calibration (A21 vs July-21, Phase 199 rule verbatim)** — same five cells (including the
   `1100/0.00` null control), the same three criteria and thresholds from
   `reports/bot-parity-199/accept-rule.md` §3/§5 (`NULL_CONTROL_MAX_SHIFT_MAIA_ELO` 165.0,
   `NULL_CONTROL_MAX_SHIFT_SF_ELO` 149.0, `PARITY_POOLED_THRESHOLD_MAIA_ELO` 85.0,
   `PARITY_POOLED_THRESHOLD_SF_ELO` 50.0, shape guard), against
   `reports/data/bot-curves-internal-scale.json`. **Branch rule** (`calibration_branch`,
   operationalizing D-13's "notable shift" via `CALIBRATION_NEAR_MISS_FRACTION` 0.75):
   - primary verdict **fails or void** -> branch **`decision`**: run A0 and A2 against July-21.
     `a0_vs_july` decides `baseline_drift` (not-holds = drift; a missing or void `a0_vs_july`
     counts as **not holds**, i.e. drift). With drift: item2 passes iff `a2_vs_a0` holds, item1
     passes iff item2 passes AND `a21_vs_a2` holds. Without drift: item2 passes iff `a2_vs_july`
     holds; item1 is always held (A21 already failed against July, so item 1's own effect cannot
     be exonerated by a same-July comparison).
   - primary **holds**, and either family's `|pooled shift| > 0.75 x` its own threshold (a near
     miss) -> branch **`report-only`**: both items pass on the primary verdict; `a2_vs_a0` and
     `a21_vs_a2` are recorded as attribution context, and a follow-up seed is recommended if
     either is not-holds.
   - primary **holds**, no near miss -> branch **`none`**: both items pass on the primary verdict
     alone, no further calibration runs needed.

   "Void counts as not holds" everywhere `_verdict_holds` is evaluated — a missing or void
   secondary verdict is never silently treated as a pass.

## 5. Report-only (never decisive)

- Grade CPU ratios and per-position throughput ratios (`grade_cpu_ratio`, `per_position_ratio`,
  `positions_above_one`) alongside T-50/T-400.
- Nodes-at-stop median and p90 per arm (A0, A2, A21) from the stop-rule TSVs.
- D-04 deadline exposure for A2 and A21 — the count and fraction of post-`minNodes` snapshots
  where a non-settled in-window root child exists, per position. Known false-positive caveat: the
  metric cannot see `isClosed` through `RankedLine`, so a terminal root child (value exactly
  1/0/0.5 with `visits` 0) is a known false positive; the 16-position set has none.
- Analysis-selector (`rankedLines[0]`) regressions from the move-quality runner, informational
  only — the judged selector is always `argmaxLine` (the bot's own pick).
- The item-3 table: A2 stop-off `analysis_move` vs FINAL stop-off `analysis_move`, on the same
  12 maia-blindness positions.
- Calibration pooled shifts (A21 vs July-21) placed next to Phase 199's own pooled shifts
  (Maia −57.7, SF −9.9) as incremental-shift context — never averaged together, never used to
  adjust a threshold.

## 6. Item decisions (D-14)

| Item | Ships iff |
|---|---|
| Item 2 (round underfill) | T-50 passes, T-400 passes, MQ-2 passes, and calibration's `item2_pass` is true |
| Item 1 (root comparability guard) | Item 2 ships AND S1 passes, S2 passes, MQ-1 passes, and calibration's `item1_pass` is true (item 1 was never measured without item 2 — A21 always includes item 2) |
| Item 3 (findability fallback) | Ships independently of every bot gate above, once its own unit tests (D-10a/b/c/d) are green |

A held item is reverted from the phase branch and gets a follow-up seed recorded in
`report.md`. **No refit and no 24-persona recalibration under any outcome** — a failed gate is
a first-class phase result, not an invitation to retune thresholds or curves after seeing data.

## 7. What must not happen

- Editing this file or `scripts/engine_search_fixes_verdict.py`'s frozen constants after any
  gate data exists (a deviation is a separate dated override document).
- Running a gate arm (throughput, stop rule, move quality, or a calibration sweep) from a
  gsd-executor subagent, or backgrounding one inside such a subagent — it dies with the agent
  (Phase 197 wave 2).
- Concurrent wall-clock runs (stop rule and/or throughput) with each other, a calibration
  sweep, or a test suite.
- Launching a calibration cell without `PRESET_SUPERVISOR_ANCHORS`, or without
  `bin/preset-supervisor.sh` (the crash supervisor is mandatory — never the bare
  `calibration-harness.mjs` driver).
- Judging a bot arm by `rankedLines[0]` — the judged selector is always `argmaxLine`, the pick
  the bot itself plays.
- Treating an arm checked out from a SHA that fails §1's content assertions as valid gate data.
