# Phase 226 accept rule (engine throughput: underfill re-land, root guard, root split)

**Committed:** 2026-09-29, as the commit that adds this file — that commit IS arm A0. Like
`reports/bot-parity-199/accept-rule.md`, `reports/continuous-dispatch/accept-rule.md` and
`reports/engine-search-fixes-225/accept-rule.md`, this is a decision contract, not a narrative:
every threshold below is fixed in advance and is **not editable** once any gate data exists
under `reports/data/engine-throughput-226/gate/`. It discharges CONTEXT.md decisions D-04
(mobile pool-of-2), D-09/D-10 (powered calibration, A0a/A0b null), D-11 (conditional shipped-item
refit), D-12 (stacked arms), D-13 (cBFTV — discharged in `design-inputs.md` §4, transcribed here
as arm A0's definition), D-14/D-15 (widened move-quality fixture, blocking), D-16 (root-split
criteria), D-17 (candidate-cap activation), D-19 (A0b seed), D-20 (refit scope).

Its machine-readable twins are `scripts/engine_throughput_226_verdict.py` (every numeric
threshold below equals a frozen constant there — grep-verifiable),
`scripts/engine_throughput_226_calibration.py` (the powered-verdict and refit-decision reducer),
and `scripts/calibration_parity_verdict.py` (the Phase 199 pooled-shift arithmetic, reused
verbatim). Once gate data exists, this file and those constants are **read-only** for the
duration of the measurement — any deviation is a separate dated override document, in the shape
of `reports/grading-ladder/override-2026-07-31.md` and this phase's own
`override-2026-09-29-d13-trace-anomaly.md`, never an edit to this file.

## 1. Arms (D-12)

| Arm | Definition | Engine content vs predecessor |
|---|---|---|
| `A0` | The commit that adds this file. Engine code identical to `git merge-base main HEAD` at that commit — only harness/tooling from Plans 226-01..226-08 has landed. | — |
| `A2` | The last commit whose subject contains the literal string `(arm A2)`, found via `git log -F --grep='(arm A2)'`, restricted to commits touching `frontend/src/lib/engine` — item 2 (round underfill fix, `mctsSearch.ts`'s block-and-restart), plus a D-13 fix inside `mctsSearch.ts` **only if** `design-inputs.md` §4 classified `cBFTV` as a bug. §4 classified it a **side effect** (see the D-13 override document), so A2 carries no D-13 fix beyond the three cherry-picked Phase 225 commits (`a9d5113ef` and its siblings, per RESEARCH Pattern 9). |
| `A21` | The last commit whose subject contains `(arm A21)` (`git log -F --grep='(arm A21)'`), touching `frontend/src` — item 2 + item 1 (root comparability guard) on top of A2. Guard design unchanged from Phase 225 D-01/D-02: boost-aware window, `ROOT_GUARD_BOOST_ALLOWANCE = 0.04`, guard window `W = 0.09`, "settled" = `visits >= 1 \|\| isClosed`. |
| `A21S` | The last commit whose subject contains `(arm A21S)` (`git log -F --grep='(arm A21S)'`) — items 2 + 1 + the root grade split (D-18: the optional `EngineProviders.gradeRoot` field and one routing line in `mctsSearch.ts`'s `dispatchExpansion`; round barrier and apply order untouched) on top of A21. |
| `A21SC` | Only if `CANDIDATE_CAP_ARM_ACTIVE` — the last commit whose subject contains `(arm A21SC)`, adding the non-root candidate cap (8 candidates, non-root nodes only) on top of A21S. **Measured `CANDIDATE_CAP_ARM_ACTIVE = False` (design-inputs.md §5) — this arm does not exist for this phase.** |

Item 2 is attributed by A2 vs A0a (the step-0 A0a calibration sweep, never a fresh A0 sweep —
D-09). Item 1 is attributed by A21 vs A2. The root split is attributed by A21S vs A21. All arm
lookups use `git log -F --grep` (fixed-string match, never a regex) restricted to the relevant
subtree with `-- <path>`.

### Content assertions (every arm must pass before any run)

- `git diff` between any two of A0/A2/A21/A21S(/A21SC) restricted to `scripts/*.mjs`,
  `scripts/lib/`, `bin/`, `frontend/package.json`, `frontend/package-lock.json` is empty — no arm
  changes tooling, only engine code (`frontend/src`).
- `T` (the tooling commit `design-inputs.md` §1 names, `27121e329` or later) to `A0` differs only
  in `reports/`, `.planning/`, `fixtures/engine/move-quality-226.tsv`,
  `scripts/engine_throughput_226_verdict.py` and `tests/scripts/`.
- `A0`'s `frontend/src` is identical to `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src`
  printing nothing — A0 is a clean tooling-only baseline with no engine-code drift from `main`.
- `A0` to `A2` engine diff is limited to `frontend/src/lib/engine/mctsSearch.ts` and
  `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts`.
- `A2` to `A21` engine diff is limited to `mctsSearch.ts`, `types.ts`, `botBudget.ts`,
  `__tests__/mctsSearch.test.ts`, and `frontend/src/hooks/useFlawChessEngine.test.tsx`.
- `A21` to `A21S` engine diff is limited to `rootSplit.ts`, `__tests__/rootSplit.test.ts`,
  `types.ts`, `mctsSearch.ts` (the `dispatchExpansion` provider-selection line and its comments
  only), `__tests__/mctsSearch.test.ts`, `workerPoolDispatch.ts`, `workerPoolState.ts`,
  `workerPool.ts`, `__tests__/workerPool.test.ts`, `hooks/useFlawChessEngine.ts`,
  `hooks/useBotGameEngineDispatch.ts`, and their existing test files.
- `A21S` to `A21SC` (if it exists) is limited to `policyTemperature.ts`, `treeCommon.ts`,
  `mctsSearch.ts`, `fallbackExpectimax.ts`, `__tests__/treeCommon.test.ts` and
  `__tests__/mctsSearch.test.ts`.

Any arm checked out from a SHA that fails these assertions is invalid gate data — do not measure
it, fix the content boundary first.

### Worktree procedure (Phase 225 pattern, reused)

Arms run from detached worktrees `../flawchess-226-{arm}` (`git worktree add
../flawchess-226-{arm} <SHA>`), each with its own `( cd frontend && npm ci )` — the harness alias
hook and `node-engine-providers.mjs` resolve their own repo root from `import.meta.url`, so each
worktree measures its own engine code. All harness output is copied back into the main
checkout's `reports/data/engine-throughput-226/` (`gate/{arm}/...`, `gate/calibration/...`, and
`sweep-226-{arm}-{cell}/` for calibration ledgers) **before** the worktree is removed — output
left in a removed worktree is lost. Record every arm SHA in `report.md` once each lands. No gate
step ever runs from, or is backgrounded inside, a `gsd-executor` subagent (Phase 197 wave 2) —
every wall-clock or calibration run is orchestrator-inline (`setsid nohup` + Monitor, or
`bin/preset-supervisor.sh`'s own resume-on-crash loop for sweeps).

## 2. Recorded design inputs

Every value below is transcribed verbatim from `reports/engine-throughput-226/design-inputs.md`
§2 (itself transcribed from the committed `design-inputs.json`) — see that document for
provenance and derivation.

| Constant | Value |
|---|---|
| `EXPECTED_MQ_POSITIONS` | 60 |
| `MQ_ALLOWANCE_OFF` | 1 |
| `MQ_ALLOWANCE_ON` | 1 |
| `CALIBRATION_THRESHOLD_MAIA` | 85.0 |
| `CALIBRATION_THRESHOLD_SF` | 53.542812708469995 |
| `ROOT_SPLIT_MAX_T50_WALL_RATIO` | 0.97 |
| `CONTENT_MAX_WARM_MEAN_ABS_DES` | 0.02520619090909091 |
| `CONTENT_MAX_CLEAR_MEAN_ABS_DES` | 0.016804127272727273 |
| `STOP_RULE_MAX_WALL_MS` | 12,100.0 |
| `CANDIDATE_CAP_ARM_ACTIVE` | False (no A21SC arm) |

**Carried-over constants** (unchanged from Phase 225, also frozen in the twin):
`THROUGHPUT_MAX_WALL_RATIO` 1.05, `STOP_RULE_MIN_EARLY_STOP_RETENTION` 0.5, `GUARD_WINDOW` 0.09,
`EXPECTED_THROUGHPUT_POSITIONS` 16, `EXPECTED_STOP_POSITIONS` 16, `MQ_REGRESSION_MARGIN` 0.05,
`NULL_MODEL_SE_MULTIPLIER` 1.96, `SHAPE_GUARD_Z` 1.96, `NULL_ESCALATION_FACTOR` 2.0,
`CALIBRATION_BASE_THRESHOLD` {maia: 85.0, sf: 50.0}, `D17_DOMINANCE_SHARE` 0.5,
`D17_CANDIDATE_THRESHOLD` 8, `NON_ROOT_CANDIDATE_CAP` 8, `CANDIDATE_CAP_MIN_T400_GAIN` 0.03,
`GAMES_PER_CELL_ANCHOR` 50, `A0A_SEED` 1, `A0B_SEED` 2, `ARM_SEED` 1 (every gate-arm calibration
cell runs on seed 1, matching A0a — arm-vs-A0a comparisons are paired in the Maia family).

## 3. Run parameters

All wall-clock runs (throughput, stop rule) run alone on an idle box (`/proc/loadavg` first field
< 2.0, no `remote_eval_worker`, nothing else heavy) — never concurrently with each other, a
calibration sweep, or a test suite. Move quality, the root-split content instrument, and
calibration are node-deterministic and may overlap each other only.

### Throughput (T-50-p4, T-400-p4, T-50-p2, T-400-p2) — A2, A21, A21S(, A21SC)

Judge `depth == "ladder"` rows only; `maia_peak_inflight` must read 1 and `maia_fifo` must read
`true` on every judged row (§4 Validity). Underfill's own comparison (A2 vs the step-0 A0
baseline) reuses the step-0 TSVs at `reports/data/engine-throughput-226/step0/throughput/{config}/`
directly — no fresh A0 throughput run.

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 50 --depths 14 --ladder --procs 4 --pool-size 4 --plies 8 --elo 1500 --openings 12 \
  --maia-fifo --out-dir reports/data/engine-throughput-226/gate/<arm>/throughput/t50-p4
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 400 --depths 14 --ladder --procs 4 --pool-size 4 --plies 8 --elo 1500 --openings 12 \
  --maia-fifo --out-dir reports/data/engine-throughput-226/gate/<arm>/throughput/t400-p4
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 50 --depths 14 --ladder --procs 4 --pool-size 2 --plies 8 --elo 1500 --openings 12 \
  --maia-fifo --out-dir reports/data/engine-throughput-226/gate/<arm>/throughput/t50-p2
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 400 --depths 14 --ladder --procs 2 --pool-size 2 --plies 8 --elo 1500 --openings 12 \
  --maia-fifo --out-dir reports/data/engine-throughput-226/gate/<arm>/throughput/t400-p2
```

`<arm>` in `a2`, `a21`, `a21s` (and `a21sc` only if `CANDIDATE_CAP_ARM_ACTIVE`, which measured
false and is skipped entirely). `--pool-size` decouples the Stockfish process pool from
`SearchBudget.concurrency` (D-04): `p4` configs are desktop-shaped (concurrency == pool size 4),
`p2` configs are the mobile pool-of-2 gating measurement (`t50-p2`: concurrency 4 over a
2-worker pool, mirroring `computePoolSize()`'s mobile clamp; `t400-p2`: concurrency AND pool size
both 2, since `computePoolSize()` sets both on mobile). `root_split_calls` must read 0 on every
row for `a2`/`a21` (D-08 tripwire, `validate_root_split_columns`) and `>= 1` with 0
`root_split_premise_violations` for `a21s`/`a21sc`.

**Run order:** wall-clock runs never overlap; within one arm's worktree, `t50-p4`, `t400-p4`,
`t50-p2`, `t400-p2` in that order, one arm fully measured before the next worktree opens.

### Stop rule (A2 report-only baseline; A21 and A21S judged)

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs \
  --dispatch-mode round --pool-size 4 --openings 12 --maia-fifo --root-trace \
  --guard-window 0.09 --out-dir reports/data/engine-throughput-226/gate/<arm>/stop
```

`<arm>` in `a2`, `a21`, `a21s`. S1 (max wall vs `STOP_RULE_MAX_WALL_MS`) is judged at A21 and
A21S; S2 (A21 early-stop retention vs A2) attributes the guard's own effect.

### Move quality (D-14/D-15; A0's own MQ is step-0's `a0a` pass, no fresh A0 MQ run)

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs \
  --arm <arm> --stop-rule <on|off> --pool-size 4 \
  --fixture fixtures/engine/move-quality-226.tsv \
  --out-dir reports/data/engine-throughput-226/gate/<arm>/mq-<on|off>
```

Runs required: `a2 off` (vs step-0 `a0a off`, attributes item 2), `a21 on` (vs `a2 on` — a2's own
`on` pass must also be run, since D-12's guard attribution needs A2-vs-A21 under the stop rule
the guard exists to affect), `a21s off` and `a21s on` (vs `a21 off`/`a21 on` — the split runs
under both stop-rule states to attribute cleanly), and (only if `CANDIDATE_CAP_ARM_ACTIVE`)
`a21sc off`/`a21sc on`. Every arm's `mq-off`/`mq-on` pass that a downstream comparison needs as
its OWN base must exist even when that arm's item is not the one being attributed by that pass
(e.g. `a2 on` exists solely so `a21 on` has a same-arm-chain predecessor).

Re-runs (RESEARCH Pitfall 8) go into `gate/<arm>/mq-<mode>-rerun/` only for the `(arm, mode)`
pairs the verdict script's own `reruns` subcommand lists (a pass-to-regression flip counts only
if a fresh process reproduces it):

```bash
uv run python scripts/engine_throughput_226_verdict.py reruns \
  --data-dir reports/data/engine-throughput-226
```

### Root-split content and determinism (D-16, D-08 — A21S only)

```bash
# Clear-Hash and warm content, real pool implementation (evaluate_content filters split_source == "pool")
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs \
  --split-source pool --hash clear --procs 4 --openings 12 \
  --fixture fixtures/engine/move-quality-226.tsv \
  --out-dir reports/data/engine-throughput-226/gate/a21s/content/clear
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs \
  --split-source pool --hash warm --procs 4 --openings 12 \
  --fixture fixtures/engine/move-quality-226.tsv \
  --out-dir reports/data/engine-throughput-226/gate/a21s/content/warm

# D-08 default (Clear-Hash) determinism check — the PASS-line gate criterion
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs \
  > reports/data/engine-throughput-226/gate/a21s/determinism.txt

# D-03 warm-arm (no-Clear-Hash), report-only, at BOTH a21 and a21s — Phase 227's D-06 input
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs \
  --no-clear-hash --games 4 \
  --out-dir reports/data/engine-throughput-226/gate/<arm>/warm-arm
```

`--split-source pool` exits `EXIT_MODULE_ABSENT` (3) before A21S exists (`rootSplit.ts` absent by
construction at A0/A2/A21) — never run this command against those arms.

### Calibration (D-09/D-10/D-19 — five runbook cells, pinned anchors, per arm)

Reuses `reports/bot-parity-199/runbook.md` §1's five cells and pinned anchors verbatim (same
`PRESET_SUPERVISOR_ANCHORS` — never omit it), at **50 games per (cell, anchor)** (not the
runbook's 24 — D-10's powered sizing), **seed 1** (`ARM_SEED`, matching A0a — never seed 2, which
is A0b-only per D-19), for `<arm>` in `a2`, `a21`, `a21s` (and `a21sc` only if active):

```bash
PRESET_SUPERVISOR_DIR=reports/data/sweep-226-<arm>-human1100 \
PRESET_SUPERVISOR_ANCHORS=maia700,maia1100,sf0,sf3 \
PRESET_SUPERVISOR_GAMES=50 \
nohup bin/preset-supervisor.sh <arm>-human1100 0 1100 \
  >> reports/data/sweep-226-<arm>-human1100/supervisor-launch.log 2>&1 &
disown

PRESET_SUPERVISOR_DIR=reports/data/sweep-226-<arm>-light1300 \
PRESET_SUPERVISOR_ANCHORS=maia1100,maia1500,sf3,sf5 \
PRESET_SUPERVISOR_GAMES=50 \
nohup bin/preset-supervisor.sh <arm>-light1300 0.05 1300 \
  >> reports/data/sweep-226-<arm>-light1300/supervisor-launch.log 2>&1 &
disown

PRESET_SUPERVISOR_DIR=reports/data/sweep-226-<arm>-light1900 \
PRESET_SUPERVISOR_ANCHORS=maia1100,maia1500,sf3,sf5 \
PRESET_SUPERVISOR_GAMES=50 \
nohup bin/preset-supervisor.sh <arm>-light1900 0.05 1900 \
  >> reports/data/sweep-226-<arm>-light1900/supervisor-launch.log 2>&1 &
disown

PRESET_SUPERVISOR_DIR=reports/data/sweep-226-<arm>-deep1500 \
PRESET_SUPERVISOR_ANCHORS=maia1500,maia1900,sf3,sf5 \
PRESET_SUPERVISOR_GAMES=50 \
nohup bin/preset-supervisor.sh <arm>-deep1500 0.5 1500 \
  >> reports/data/sweep-226-<arm>-deep1500/supervisor-launch.log 2>&1 &
disown

PRESET_SUPERVISOR_DIR=reports/data/sweep-226-<arm>-deep2300 \
PRESET_SUPERVISOR_ANCHORS=maia1500,maia1900,sf3,sf5 \
PRESET_SUPERVISOR_GAMES=50 \
nohup bin/preset-supervisor.sh <arm>-deep2300 0.5 2300 \
  >> reports/data/sweep-226-<arm>-deep2300/supervisor-launch.log 2>&1 &
disown
```

Convert each arm's own five `-cells.tsv` aggregates into an `--old-json`-shaped payload (the
"base" side for the NEXT arm's attribution — D-12's stacked chain):

```bash
uv run python scripts/engine_throughput_226_verdict.py cells-to-json \
  --cells-tsv reports/data/sweep-226-<arm>-human1100/*-cells.tsv \
  --cells-tsv reports/data/sweep-226-<arm>-light1300/*-cells.tsv \
  --cells-tsv reports/data/sweep-226-<arm>-light1900/*-cells.tsv \
  --cells-tsv reports/data/sweep-226-<arm>-deep1500/*-cells.tsv \
  --cells-tsv reports/data/sweep-226-<arm>-deep2300/*-cells.tsv \
  --out-json reports/data/engine-throughput-226/gate/calibration/<arm>-cells.json
```

Then the four stacked-attribution verdicts, each new arm's sweep against its immediate
predecessor's converted cells (A2's predecessor is the already-committed
`reports/data/engine-throughput-226/step0/calibration/a0a-cells.json` — never a fresh A0 sweep):

```bash
uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/engine-throughput-226/step0/calibration/a0a-cells.json \
  --new-cells-tsv reports/data/sweep-226-a2-*/*-cells.tsv \
  --out-json reports/data/engine-throughput-226/gate/calibration/verdict-a2-vs-a0a.json

uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/engine-throughput-226/gate/calibration/a2-cells.json \
  --new-cells-tsv reports/data/sweep-226-a21-*/*-cells.tsv \
  --out-json reports/data/engine-throughput-226/gate/calibration/verdict-a21-vs-a2.json

uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/engine-throughput-226/gate/calibration/a21-cells.json \
  --new-cells-tsv reports/data/sweep-226-a21s-*/*-cells.tsv \
  --out-json reports/data/engine-throughput-226/gate/calibration/verdict-a21s-vs-a21.json

# Only if CANDIDATE_CAP_ARM_ACTIVE (measured False — skip):
uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/engine-throughput-226/gate/calibration/a21s-cells.json \
  --new-cells-tsv reports/data/sweep-226-a21sc-*/*-cells.tsv \
  --out-json reports/data/engine-throughput-226/gate/calibration/verdict-a21sc-vs-a21s.json
```

### Data layout

Exactly the layout `scripts/engine_throughput_226_verdict.py` reads, under
`reports/data/engine-throughput-226/`:

```
step0/throughput/{t50-p4,t400-p4,t50-p2,t400-p2}/  # A0 baseline (already committed, 226-07)
step0/calibration/a0a-cells.json                    # A0a converted cells (already committed)
step0/mq/a0a/mq-off/                                # A0a's own MQ off pass (already committed)
gate/{arm}/throughput/{t50-p4,t400-p4,t50-p2,t400-p2}/   # arm in a2, a21, a21s(, a21sc)
gate/{arm}/stop/                                    # arm in a2, a21, a21s
gate/{arm}/mq-off/, gate/{arm}/mq-on/                # per _mq_pair_specs (see Run parameters)
gate/{arm}/mq-{off,on}-rerun/                       # only for flips reruns lists
gate/{arm}/warm-arm/                                # arm in a21, a21s (report-only)
gate/a21s/content/{clear,warm}/                     # split_source=pool rows only
gate/a21s/determinism.txt                           # D-08 PASS-line criterion
gate/calibration/{arm}-cells.json                   # arm in a2, a21, a21s(, a21sc)
gate/calibration/verdict-{a2-vs-a0a,a21-vs-a2,a21s-vs-a21}.json  # (+ a21sc-vs-a21s if active)
```

### Sequencing

Wall-clock runs (throughput, stop rule) run alone on an idle box, never concurrently with each
other, a calibration sweep, or a test suite. Move quality, the content instrument, and
calibration are node-deterministic and may overlap each other only.

## 4. Criteria, in evaluation order

Each criterion's twin constant name is given so a threshold in this document can be
grep-verified against `scripts/engine_throughput_226_verdict.py`. This is `run_gates`'s own
evaluation order.

1. **Validity** — content assertions (§1) pass; `EXPECTED_THROUGHPUT_POSITIONS` = 16 identical
   ladder-position sets between compared arms; `maia_peak_inflight == "1"` and
   `maia_fifo == "true"` on every judged throughput row (an inadmissible row raises, never
   silently excluded — `evaluate_throughput_pair`); `root_split_calls`/
   `root_split_premise_violations` match the D-08 arm expectation on every throughput row
   (`validate_root_split_columns`, `RootSplitDataError` → `EXIT_INVALID`, distinct from a merely
   incomplete run); `EXPECTED_MQ_POSITIONS` = 60 identical id-sets between compared MQ arms;
   `EXPECTED_STOP_POSITIONS` = 16 identical stop-rule row counts, `stop_rule == "on"` on every S1
   row.
2. **Underfill throughput (item 2, A2 vs step-0 A0a)** — for each of the four configs,
   `A2 ladder wall_ms sum <= THROUGHPUT_MAX_WALL_RATIO 1.05 x A0a ladder wall_ms sum`. All four
   configs must pass for `underfill_throughput_passed` to be true.
3. **Underfill MQ (item 2, A2 vs A0a, stop rule off)** — paired criterion (D-14 §4): net =
   (reproduced pass-to-regression flips) − (regression-to-pass flips) ≤
   `MQ_ALLOWANCE_OFF` = 1. A pass-to-regression flip counts only once a fresh-process rerun
   reproduces it (RESEARCH Pitfall 8) — an unrerun flip blocks the whole gate
   (`status: rerun-required`, `EXIT_INCOMPLETE`, never a silent pass or fail).
4. **Guard S1 (stop rule, A21)** — `A21 max wall_ms <= STOP_RULE_MAX_WALL_MS 12,100 ms`.
5. **Guard S2 (stop rule, A21 vs A2)** — `A21 early-stop count >= STOP_RULE_MIN_EARLY_STOP_RETENTION
   0.5 x A2 early-stop count`. Trivially passes when A2 has zero early stops.
6. **Guard MQ (item 1, A21 vs A2, stop rule on)** — same paired definition and rerun rule as
   item 3, allowance `MQ_ALLOWANCE_ON` = 1.
7. **Root-split determinism (D-08, A21S)** — `gate/a21s/determinism.txt` must contain the literal
   line `PASS: calibration determinism` (`evaluate_determinism`).
8. **Root-split T-50 throughput (A21S vs A21)** —
   `A21S t50-p4 ladder wall_ms sum <= ROOT_SPLIT_MAX_T50_WALL_RATIO 0.97 x A21 t50-p4 sum`.
9. **Root-split other throughput configs (A21S vs A21)** — `t400-p4`, `t50-p2`, `t400-p2` each at
   the carried `THROUGHPUT_MAX_WALL_RATIO` 1.05 bound (the split is not expected to help — or
   hurt beyond the no-regression bound — at 400 nodes or on the mobile pool-of-2, where the
   fan-out either has less headroom to help or is capped by pool size).
10. **Root-split Clear-Hash content (A21S)** — candidate-weighted mean `|Δes|` over
    `split_source == "pool"` rows <= `CONTENT_MAX_CLEAR_MEAN_ABS_DES` 0.016804127272727273.
    **design-inputs.md §6 flags that the prototype instrument already measured 0.0209 against
    this exact bound — this criterion is likely to fail unless the real pool implementation
    diverges materially from the prototype.** That is a measured risk recorded in advance, not a
    reason to relax the bound now.
11. **Root-split warm content (A21S)** — same measure, `<= CONTENT_MAX_WARM_MEAN_ABS_DES`
    0.02520619090909091.
12. **Root-split MQ off (A21S vs A21, stop rule off)** — same paired definition, allowance
    `MQ_ALLOWANCE_OFF` = 1. Evaluated regardless of whether the guard (item 1) shipped.
13. **Root-split S1 (A21S) and MQ on (A21S vs A21, stop rule on)** — evaluated the same way as
    items 4 and 6, but only DECISIVE for the root-split ship decision when the guard shipped
    (item 6's own outcome); when the guard is held, these two stay report-only for the split (§6).
14. **Candidate cap (item, only if `CANDIDATE_CAP_ARM_ACTIVE`)** — measured **False**; this arm
    and every one of its criteria are entirely absent from this gate run.
15. **Calibration (D-09/D-10, per shipped item, A0a-anchored powered verdict)** — for each item
    whose §6 stacked rule ships, `powered_verdict` on its own arm-vs-predecessor comparison:
    validity from both families' `null_control.within_threshold` (Phase 199 gate unchanged);
    when valid, `real_shift` is true iff either family's `|pooled shift|` exceeds its powered
    threshold (`CALIBRATION_THRESHOLD_MAIA` 85.0, `CALIBRATION_THRESHOLD_SF` 53.5428) or the
    z-based shape guard fires (`SHAPE_GUARD_Z` 1.96, both families on the same cell). A void
    comparison on a SHIPPED item escalates to the user (never a silent no-refit) — see §6's D-11
    rule.

## 5. Report-only (never decisive)

- McNemar's one-sided exact p-value on every MQ paired comparison's discordant pairs
  (`_mcnemar_one_sided_p`).
- `root_argmax_flip_rate` from both content TSVs (measured 7.9% under the prototype tool,
  identical clear/warm — design-inputs.md §6).
- Grade CPU ratios and per-position throughput ratios alongside every throughput criterion.
- Nodes-at-stop per arm from the stop-rule TSVs.
- The warm-arm (`--no-clear-hash --games 4`) divergence at A21 and A21S — Phase 227's D-06
  round-mode warm-hash noise-floor input (`k x` this number becomes 227's continuous-dispatch
  tolerance; this phase measures and hands off, never sets `k`).
- Pool-2 throughput gains (the `t50-p2`/`t400-p2` ratios themselves, beyond their own
  no-regression bound).
- A real-phone dev-build run of the root split — owner-deferred per D-04 (a Node harness with the
  pool forced to 2 workers is the GATING measurement; the phone run, if it happens, is
  informational only).

## 6. Item decisions (D-12/D-15/D-16/D-17, exactly as `decide_items` implements them)

The stacked rules below are `decide_items`'s own logic, restated for readability — the code is
the single source, this table is not a separate implementation:

| Item | Ships iff |
|---|---|
| Underfill (item 2) | Underfill throughput (all 4 configs) passes AND underfill MQ passes |
| Root guard (item 1) | Underfill ships AND guard S1 passes AND guard S2 passes AND guard MQ passes |
| Root split | Underfill ships AND root-split determinism passes AND T-50 passes AND the other 3 throughput configs pass AND BOTH content bounds pass AND MQ-off passes; **additionally**, IF the guard shipped, root-split S1 AND MQ-on must ALSO pass (the split's own criteria are evaluated independent of the guard's ship status, but become decisive together with it once the guard is live) |
| Candidate cap | Only exists if `CANDIDATE_CAP_ARM_ACTIVE` (measured False — absent from this gate) |

A held item's downstream items automatically hold too (underfill held ⇒ guard and root split both
held, regardless of their own individual criteria — the reason string names this explicitly).
This is stricter than "measure independently": Phase 226 treats a held predecessor as removing
the ground its dependents were measured on, not as a green light to ship a fix layered on a bug.

**D-11 refit rule** (`refit_decision`, run once, only over SHIPPED items' own powered verdicts):
escalate wins over refit, refit wins over no-refit, a held item never contributes regardless of
its own verdict.

- **Escalate** iff any shipped item has no recorded powered verdict, OR any shipped item's
  comparison is void (its null control failed) — a void comparison on a shipped item is never a
  silent no-refit.
- **Refit** iff (no escalation, and) at least one shipped item's comparison shows a real
  (powered) shift.
- **No-refit** iff (no escalation, and) no shipped item shows a real shift.

Refit scope, if triggered (D-20, matching Phase 199): **both** the strength curves (the 10
light/deep calibration cells) AND the blend>0 persona labels — run once, after the verdict, on
the FINAL shipped configuration. Escalate goes to the user, never resolved by re-running or
re-thresholding.

## 7. What must not happen

- Editing this file or `scripts/engine_throughput_226_verdict.py`'s frozen constants after any
  gate data exists under `reports/data/engine-throughput-226/gate/` (a deviation is a separate
  dated override document).
- Running any gate step (throughput, stop rule, move quality, content, determinism, or a
  calibration sweep) from a `gsd-executor` subagent, or backgrounding one inside such a subagent
  — it dies with the agent (Phase 197 wave 2). Every step runs orchestrator-inline.
- Concurrent wall-clock runs (throughput, stop rule) with each other, a calibration sweep, or a
  test suite.
- Launching a calibration cell without `PRESET_SUPERVISOR_ANCHORS`, or without
  `bin/preset-supervisor.sh` (the crash supervisor is mandatory — never the bare
  `calibration-harness.mjs` driver).
- Judging any arm's calibration against the July-21 curves — every calibration criterion above
  compares exclusively against the same-session A0a (D-09).
- Implementing continuous dispatch, a round-mode budget flag, or the D-05 expected-score
  contract in this phase — those are Phase 227 scope (D-01, D-05, D-07); this phase's only
  227-facing deliverable is the D-03 no-Clear-Hash warm-arm measurement, reported not
  implemented.
- Measuring or gating on desktop-WebGPU Maia performance in this phase — Phase 227 prerequisite
  (D-02); the root split is Stockfish-bound and does not depend on it.
- Any refit before the verdict, or a refit scoped to less than both the strength curves and the
  blend>0 persona labels when D-11 triggers (D-20).
- Treating an arm checked out from a SHA that fails §1's content assertions as valid gate data.

---

*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Plan: 226-08*
