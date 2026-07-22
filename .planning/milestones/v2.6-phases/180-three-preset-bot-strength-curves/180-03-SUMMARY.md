---
phase: 180-three-preset-bot-strength-curves
plan: 03
subsystem: calibration
tags: [calibration, bot-strength, internal-rating, two-pass, near-free-metrics, mjs, node]

# Dependency graph
requires:
  - phase: 180-three-preset-bot-strength-curves
    plan: 01
    provides: "internalRatingFor + pickLocateAnchors/locateEstimate/selectMeasureBracket/bracketBeyondLadder + LOCATE_PASS_GAMES (calibration-bot-cell-schedule.mjs)"
  - phase: 180-three-preset-bot-strength-curves
    plan: 02
    provides: "calibration_anchor_fit.py load_bot_cells (the per-(cell,anchor) TSV consumer)"
provides:
  - "calibration-harness.mjs internal-scale two-pass cell loop (locate->bracket->measure) selecting anchors on the MEASURED internalRatingFor scale, both anchor families, per (bot_elo, bot_blend) cell"
  - "beyond_ladder per-cell flag + six near-free metric columns (draw rate, game length, ACPL, blunder rate, SF-agreement, Maia-agreement) in the per-(cell,anchor) aggregate TSV"
  - "raw per-game ledger + replay-based --resume (variable-length two-pass cells resume byte-identical, Pitfall 5)"
  - "pure engine-free near-free metric accumulator + fabricated-provider .check.mjs"
affects: [180-04 operator sweep, G_preset, SEED-104]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Measured-internal-scale anchor selection in the harness (internalRatingFor), never nominal anchorRatingFor — the 2026-07-12 clamp fix"
    - "Two-tier durable artifacts: raw per-game ledger (resumable) + derived per-(cell,anchor) aggregate (fit input) — mirrors calibration-anchor-ladder.mjs"
    - "Near-free metrics as byproducts: bestmove reuses the adjudication go (0 extra engine calls); Maia-agreement is one cheap policy argmax/bot ply"

key-files:
  created:
    - scripts/lib/calibration-near-free-metrics.check.mjs
  modified:
    - scripts/calibration-harness.mjs
    - scripts/lib/calibration-providers.mjs
    - scripts/lib/stockfish-pool.mjs
    - scripts/lib/calibration-game-loop.mjs

key-decisions:
  - "Extended the SHARED game-loop/providers/pool (beyond Task 3's stated file list) to surface the adjudication eval + bestmove to onPly — the only way to make ACPL/blunder/SF-agreement genuinely near-free (0 extra engine calls). Backward-compatible: a pool without evalPositionWithBest degrades to cp-only, keeping the stub-pool game-loop check green."
  - "Primary durable artifact is now the raw per-game ledger; the per-(cell,anchor) aggregate (Plan 02 fit input) is a derived -cells.tsv sibling written once at end (no metadata footer, since load_bot_cells parses every data line). Supersedes the old per-row-durable aggregate; removed openMainTsvWriter."
  - "Committed in task order 1 -> 3 -> 2 (Task 3 before Task 2) because Task 2's ledger stores per-game near-free sums produced by Task 3's playGame contribution; each commit still passes its own verify."

patterns-established:
  - "onPly now carries { evalCp, bestUci } (post-move) — the near-free hook; fires AFTER the adjudication eval so it rides the same single go"
  - "Ledger replay integrity (T-180-05): a game_index whose recorded opening/color does not match the seed-derived value fail-louds rather than silently corrupting the resumed sweep"

requirements-completed: []

# Metrics
duration: ~22min
completed: 2026-07-19
status: complete
---

# Phase 180 Plan 03: Internal-scale two-pass harness integration Summary

Wired Plan 01's measured-internal-scale two-pass scheduler and Plan 02's TSV contract into `scripts/calibration-harness.mjs`: the cell loop now selects anchors by `internalRatingFor` (fixing the 2026-07-12 clamp), runs a locate→bracket→measure two-pass against both anchor families with the 10 measured labels as the default pool, flags beyond-ladder cells, resumes from a raw per-game ledger, and surfaces six near-free metrics — the whole thing provable engine-free (module load + a fabricated-provider near-free check + the cross-language `load_bot_cells` contract).

## What Was Built

**Task 1 — internal-scale integration (`calibration-harness.mjs`, commit e273bfe6):**
- Imports `internalRatingFor` + the two-pass functions from `calibration-bot-cell-schedule.mjs`.
- `DEFAULT_ANCHOR_TOKENS` restricted to the 10 measured labels (maia700/1100/1500/1900/2300 + sf0/3/5/8/10) — both families fire, every token has a measured `INTERNAL_RATING`.
- `DEFAULT_BOT_BLENDS = [0, 0.05, 0.5]` (the locked presets); `DEFAULT_BOT_ELOS` comment notes the operator passes per-preset `--elo` grids (D-04).
- `summaryRowForCellGroup` inverts the advisory estimate on the INTERNAL axis (`internalRatingFor`), not nominal `anchorRatingFor`.
- D-15 `partitionAnchorsByWindow`/`orderAnchorsForDynamicCutoff`/`ANCHOR_ELO_WINDOW` retired-not-deleted with a superseded comment.

**Task 3 — near-free metrics (harness + providers + pool + game-loop + new check, commit 33ab6db2):**
- `evalPositionCpWithBest` (providers) surfaces the adjudication `bestmove` as a FREE byproduct (the `bestmove` line is already awaited); `pool.evalPositionWithBest`; the game loop passes post-move `{ evalCp, bestUci }` to `onPly` (graceful cp-only fallback keeps the stub-pool `calibration-game-loop.check.mjs` green).
- Pure near-free accumulator (`newNearFreeGameStats`/`recordBotMoveEval`/`recordBotMoveSfAgreement`/`recordBotMoveMaiaAgreement`/`newNearFreeCellStats`/`foldNearFreeGame`/`finalizeNearFreeMetrics`) reusing `classifyLiveSeverity`/`evalToExpectedScore` (liveFlaw) + `maiaArgmaxMove` — no hand-rolled thresholds/argmax.
- `playGame` collects near-free per game (Maia argmax = one cheap policy pass/bot ply on an independent metric RNG); six metric columns added to `mainTsvColumns`/`mainTsvRowLine`.
- `scripts/lib/calibration-near-free-metrics.check.mjs`: fabricated eval/policy fixtures, one PASS per metric, `exit(0)`.

**Task 2 — two-pass cell loop + ledger resume (`calibration-harness.mjs`, commit 8c42d246):**
- Cell loop = `locateCellPass` (top up the two widest anchors to `LOCATE_PASS_GAMES`, then `locateEstimate`) → `selectMeasureBracket` → `measureCellPass` (extend each bracket anchor to `--games-per-cell`, reusing locate games, never replayed).
- `beyond_ladder` column set per cell from `bracketBeyondLadder` (warn-and-flag, never throws — Pitfall 4).
- Raw per-game ledger (`RAW_LEDGER_COLUMNS` incl. per-game near-free sums) + `readPriorLedgerRows`/`applyPriorLedgerRows` replay; `--resume` reconstructs the store and fast-forwards `state.gameIndex` past the last logged game.
- T-180-05 integrity: refuses a changed seed, an anchor/cell outside the current sets, or a `game_index` whose recorded opening/color mismatches the seed-derived value.
- Derived `-cells.tsv` aggregate (the Plan 02 fit input, header + rows only) + `-summary.tsv` advisory; `SKIP_REASON_NOT_BRACKETED` rows for un-played anchors (row-not-silently-absent).

## Gate Results

- **T1 verify** (`node -e` harness module load): OK.
- **T2 verify** (`mainTsvColumns()` includes `beyond_ladder`): OK (31 columns).
- **T3 verify** (`calibration-near-free-metrics.check.mjs`): 6 PASS lines, exit 0.
- **Regression** (engine-free): `calibration-bot-cell-schedule.check.mjs`, `calibration-game-loop.check.mjs`, `calibration-pruning.check.mjs` all green (the pruning check still exercises the retired D-15 `loadPriorSweep`/`SKIP_REASON_*` machinery).
- **Cross-language contract** (key_link): a harness aggregate rendered via `mainTsvColumns`/`mainTsvRowLine` (played maia + sf rows + a games=0 skip row, `beyond_ladder=true`) parses cleanly through Plan 02's `load_bot_cells` — families split correctly, `beyond_ladder` read as `True`, the games=0 row carried through harmlessly.
- **Importers**: `calibration-anchor-ladder.mjs` + `calibration-anchors.mjs` import OK (no removed symbol referenced).

The full 1,440-game real-engine sweep + `--resume` byte-identity is the separate operator/HUMAN-UAT step (D-02(b) pilot), explicitly NOT part of this phase's automated gate (D-01).

## Deviations from Plan

### [Rule 3 - Blocking] Extended the shared game-loop / providers / pool beyond Task 3's stated `<files>`
- **Found during:** Task 3.
- **Issue:** Task 3's `<files>` listed only `calibration-harness.mjs` + the new check, but "reuse the existing per-ply adjudication eval (zero extra engine calls)" and "reuse the existing bestmove byproduct" are impossible without surfacing the game loop's INTERNAL adjudication eval + `bestmove`, which live in `calibration-game-loop.mjs` / `calibration-providers.mjs` / `stockfish-pool.mjs` (all named in Task 3's `read_first`).
- **Fix:** Added `evalPositionCpWithBest` (providers) + `pool.evalPositionWithBest`, and reordered `playTwoMoverGame` to compute the adjudication eval ONCE and pass `{ evalCp, bestUci }` to `onPly`. Backward-compatible: a pool without `evalPositionWithBest` degrades to cp-only (`bestUci: null`), so the stub-pool `calibration-game-loop.check.mjs` keeps passing unchanged. Zero extra engine calls (same single adjudication `go`).
- **Files modified:** scripts/lib/calibration-providers.mjs, scripts/lib/stockfish-pool.mjs, scripts/lib/calibration-game-loop.mjs
- **Commit:** 33ab6db2

### [Design choice] Artifact model + commit ordering
- The primary durable artifact is now the raw per-game ledger (`calibration-harness-<ts>.tsv`); the per-(cell,anchor) aggregate (Plan 02 fit input) is a derived `-cells.tsv` sibling written once at end (no metadata footer, since `load_bot_cells` parses every data line). This supersedes the old per-row-durable aggregate and removed the now-orphaned `openMainTsvWriter`. Consistent with `calibration-anchor-ladder.mjs`'s two-tier model and Pitfall 5's resolution.
- Committed in task order 1 → 3 → 2 (Task 3 before Task 2): Task 2's ledger stores per-game near-free sums produced by Task 3's `playGame` contribution, so committing Task 2 first would reference undefined accumulator functions. Each commit still passes its own verify.

### [Retire-not-delete] D-15 machinery kept because a check exercises it
- `loadPriorSweep`/`readPriorTsvLines`/`parsePriorRow` + `SKIP_REASON_OUT_OF_WINDOW/LOST_CUTOFF/WON_CUTOFF` + `partitionAnchorsByWindow`/`orderAnchorsForDynamicCutoff` are retained (uncalled by the two-pass loop) because `calibration-pruning.check.mjs` imports and asserts them. Only the fully-orphaned `processCellAnchor`/`playCell`/`openMainTsvWriter` were removed.

## Known Stubs

None. The near-free columns populate from real per-ply data in a run; the accumulator is proven engine-free; the aggregate is the real Plan 02 fit input.

## Deferred Issues

- The ledger replay path (`readPriorLedgerRows`/`applyPriorLedgerRows`) has no engine-free automated test — those functions are internal and a resume unit test was not in this phase's gate (the plan gates `--resume` byte-identity via the separate D-02(b) real-engine pilot checkpoint). Mitigated by the T-180-05 fail-loud integrity guards (seed + anchor/cell membership + `game_index` opening/color determinism). A future hardening pass could export + unit-test the replay on a fabricated ledger.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries; the ledger is a local developer-produced file whose replay is now integrity-checked (T-180-05).

## Self-Check: PASSED

- FOUND: scripts/lib/calibration-near-free-metrics.check.mjs
- FOUND: scripts/calibration-harness.mjs (modified)
- FOUND commit: e273bfe6 (Task 1)
- FOUND commit: 33ab6db2 (Task 3)
- FOUND commit: 8c42d246 (Task 2)

---
*Phase: 180-three-preset-bot-strength-curves*
*Completed: 2026-07-19*
