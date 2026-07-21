---
phase: 180-three-preset-bot-strength-curves
plan: 04
subsystem: calibration
tags: [calibration, bot-strength, internal-rating, pilot, human-verify, checkpoint, engine-free-gate]

# Dependency graph
requires:
  - phase: 180-three-preset-bot-strength-curves
    plan: 01
    provides: "calibration-bot-cell-schedule.mjs two-pass scheduler + internalRatingFor"
  - phase: 180-three-preset-bot-strength-curves
    plan: 02
    provides: "calibration_anchor_fit.py fit_bot_cell_rating + g_preset"
  - phase: 180-three-preset-bot-strength-curves
    plan: 03
    provides: "calibration-harness.mjs internal-scale two-pass cell loop + near-free metrics + raw-ledger resume"
provides:
  - "D-02a engine-free logic-layer gate result (green): both calibration .check.mjs + the fitter pytest selection pass with no real engine spawned — the real-engine pilot is authorized"
  - "D-02b real-engine pilot result (APPROVED by operator 2026-07-19): both anchor families fire, --resume byte-identical, fitter emits per-cell rating_vs_maia/rating_vs_sf/g_preset + per-preset G_preset — Phase 180 COMPLETE at the pilot (D-01)"
affects: [180 phase completion (Task 2 pilot), SEED-104]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-layer gate (D-02): (a) engine-free logic layer fully green — automated, done here; (b) small real-engine pilot — blocking human-verify, off this scope"

key-files:
  created:
    - .planning/phases/180-three-preset-bot-strength-curves/180-04-SUMMARY.md
    - reports/data/calibration-harness-2026-07-19T16-41-26-964Z.tsv
    - reports/data/calibration-harness-2026-07-19T16-41-26-964Z-cells.tsv
    - reports/data/calibration-harness-2026-07-19T16-41-26-964Z-summary.tsv
    - reports/data/bot-curves-pilot.json
  modified: []

key-decisions:
  - "Task 1 (D-02a automated gate): green — both calibration .check.mjs + fitter pytest pass, no engine spawned."
  - "Task 2 (D-02b real-engine pilot): RUN and APPROVED by the operator (2026-07-19). Phase 180 COMPLETES here (D-01)."
  - "Task 3 (operator ~1,440-game sweep + findings note): DEFERRED — off the interactive critical path, run when the operator chooses."

requirements-completed: []

# Metrics
duration: ~3min gate + ~75min pilot
completed: 2026-07-19
status: complete
---

# Phase 180 Plan 04: Pilot + operator sweep — gate green, pilot APPROVED, phase complete Summary

Ran the D-02a engine-free logic-layer gate (Task 1, green), then the D-02b real-engine pilot (Task 2), which the operator **approved** on 2026-07-19 — Phase 180 is COMPLETE at the pilot (D-01). Task 3 (the folded-in ~18-22h operator sweep + fitted per-preset curves + findings note) is intentionally **deferred**, off the interactive critical path.

## What Was Built

No source edits — this plan runs and interprets the Plan 01-03 machinery. Task 1 is a pure verification gate.

## Gate Results

### Task 1 — D-02a engine-free logic layer (GREEN, all three commands exit 0)

1. `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-bot-cell-schedule.check.mjs`
   → **PASS** (exit 0). 6 PASS lines: `internalRatingFor`, `pickLocateAnchors`, `locateEstimate`, `selectMeasureBracket`, `bracketBeyondLadder`, `calibration-bot-cell-schedule` two-pass scheduler.
2. `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-near-free-metrics.check.mjs`
   → **PASS** (exit 0). 6 PASS lines: `recordBotMoveEval`, `recordBotMoveSfAgreement`, `recordBotMoveMaiaAgreement`, `finalizeNearFreeMetrics` (aggregate + empty-cell null), `calibration-near-free-metrics` six-metric check.
3. `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k "fit_bot_cell_rating or g_preset" -x`
   → **PASS** (exit 0). 3 passed, 7 deselected.

**No real Maia/Stockfish engine was spawned by Task 1** (logic layer only). Per D-02a → D-02b ordering, the real-engine pilot is now authorized.

## Task 2 — D-02(b) real-engine pilot (PHASE COMPLETION GATE) — RUN & APPROVED

**Status:** COMPLETE. Pilot run `--elo 1500 --blends 0,0.05 --games-per-cell 8 --stockfish-procs 4` (88 games: 32 locate + 56 measure). Operator **approved** 2026-07-19.

**Artifacts:** `calibration-harness-2026-07-19T16-41-26-964Z.tsv` (raw ledger), `-cells.tsv` (aggregate), `-summary.tsv`, `bot-curves-pilot.json` (fit output).

**Acceptance criteria — verdict:**

| Criterion | Result |
|-----------|--------|
| Both anchor families fire (measure pass) | ✅ blend 0 → maia700/maia1100/sf3; blend 0.05 → maia1500/maia1900/sf3/sf5 |
| Near-free metrics populated & differ by preset | ✅ blend 0: 62 plies, 1.58 blund/game, maia-agree 57% · blend 0.05: 74 plies, 1.25 blund/game, maia-agree 37% |
| `--resume` byte-identical | ✅ SHA256 unchanged, empty diff (completed run replays to a no-op) |
| Fitter emits ratings + CIs + g_preset + per-preset G_preset + caveat | ✅ `bot-curves-pilot.json` well-formed (blend 0: 1177/1107, G=+70; blend 0.05: 1518/1455, G=+63) |

**Three flagged signals, adjudicated (approved as benign / low-N artifacts):**

1. **`any_clamped=true` on both cells** — traced to harness `wasScoreClamped(score, games)` (line 840), the **benign shutout continuity clamp** fired by 0/8 vs sf10 and 8/0 vs sf0 (the extreme *locate* anchors, near-guaranteed shutouts). This is NOT the Pitfall-6 nominal-fallback clamp — the scheduler now fails loud, so that bug cannot recur silently. Acceptance criterion conflated the two clamp meanings; the dangerous one is absent.
2. **`beyond_ladder=true` on the blend-0 (Human) cell** — its fit rating (~1177/1107) is mid-ladder, but its measure bracket pulled only ONE SF anchor (sf3), failing the ≥2-SF cross-family floor → correctly flagged as under-bracketed at a sparse spot of the SF ladder. Machinery behaving as designed; a low-N bracketing artifact, not an out-of-range rating.
3. **Human (blend 0) `G_preset = +70`, not ~0 as predicted** — at 8 games/anchor the CIs are enormous and fully overlapping (vs_maia [1006,1276], vs_sf [921,1284]), so +70 is within noise of 0. The full sweep at 24-30 games/anchor will tighten this.

### Task 3 — Folded-in HUMAN-UAT operator sweep + fitted curves + findings note (D-01, OFF critical path, gate=blocking)

**Status:** DEFERRED. Off the interactive critical path — the phase is already complete at Task 2's pilot. Delivers the downstream SEED-104 artifact when the operator chooses to run the ~1,440-game sweep.

**One-command launch:** `bin/run_bot_curves_sweep.sh` runs all three presets in PARALLEL (separate `--out-dir` per preset → no ledger collision), waits, then auto-combines the three `-cells.tsv` aggregates and fits `reports/data/bot-curves-internal-scale.json`. Flags: `--procs N` (SF procs/preset, default 4; drop to 3 if the box is busy), `--games N` (default 24), `--seed N`, `--no-fit`. Auto-resumes any interrupted preset from its own ledger. Parallel is faster than sequential here: Maia is 1-thread wasm + Stockfish `-single` is 1-thread/proc, so on the 16-core box 3×4 SF + 3 Maia ≈ 15 cores (a single preset would idle ~11). Then write the findings note (step 3 below).

**Operator commands:**
1. Full sweep as THREE per-preset invocations (D-03/D-04 per-preset non-uniform grids; cannot be one cross-product — each preset has different `bot_elo` points), each appending to a resumable ledger at 24 games/(cell,anchor) baseline (bump to 30 for any cell whose bracket has fewer than 4 anchors, D-05):
   - Human: `--blends 0    --elo 700,1100,1500,1900,2300`
   - Light: `--blends 0.05 --elo 1100,1300,1500,1700,1900`
   - Deep:  `--blends 0.5  --elo 1100,1500,1900,2300,2600`
   (Deep's 2600 is deliberate extrapolation past sf10's 1907.93 ceiling — expect `beyond_ladder=true` there, not a bug.)
2. Run the fitter over the combined sweep TSV:
   ```
   uv run python scripts/calibration_anchor_fit.py --bot-input <sweep.tsv> --out-bot-curves reports/data/bot-curves-internal-scale.json
   ```
   Confirm the JSON carries per-cell `rating_vs_maia`/`rating_vs_sf`/`g_preset`/CIs/`beyond_ladder` + the per-preset combined `G_preset` and the INTERNAL-SCALE-NOT-human-ELO caveat header.
3. Write `.planning/notes/2026-07-XX-three-preset-bot-strength-curves-findings.md` (rename XX to the run date) mirroring `2026-07-15-anchor-ladder-self-calibration-findings.md`, baking in the caveats: "Deep is a ceiling, not deeper" (blend inside (0,1) is only a softmax temperature dial; the only qualitative cliff is blend 0 vs >0); read any cell leaning on sf0 or maia700 with the Finding-4 style-outlier caveat; non-transitivity means the presets' raw internal rating is search-inflated vs search-less anchors, which is why `G_preset` is SUBTRACTED (not ignored) in SEED-104's offset model.

**Resume-signal:** Type "approved" once the sweep, bot-curves JSON, and findings note exist and read sanely; or "defer" to complete the phase at the pilot and run the sweep later (D-01 allows this — the operator step is off the critical path).

## D-01 Completion Boundary

**The phase COMPLETES at the Task 2 pilot.** The overnight sweep + fitted per-preset curves + `G_preset` + findings note (Task 3) are explicitly HUMAN-UAT, operator-run, and OFF the interactive critical path — this plan is `autonomous: false` for exactly that reason. Task 3 is deferrable ("defer" resume-signal); the `reports/data/bot-curves-internal-scale.json` artifact and the findings note are produced when the operator runs the sweep, not as a blocker to phase completion.

## Deviations from Plan

None for the executed scope. Only Task 1 (the automated D-02a gate) was in scope; it ran exactly as written and passed. Tasks 2 and 3 are blocking human-verify checkpoints intentionally left unrun (no real engines spawned, no self-certification).

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries. The pilot/sweep (when a human runs them) spawn only local engine subprocesses writing to local `reports/data/`; the INTERNAL-SCALE-NOT-human-ELO caveat (T-180-06) is carried in the JSON header + findings note, and `--resume` from the durable ledger (T-180-07) covers a killed sweep.

## Self-Check: PASSED

- FOUND: .planning/phases/180-three-preset-bot-strength-curves/180-04-SUMMARY.md
- Task 1 gate: 3/3 commands exit 0 (verified live this session)
- Task 2 pilot: 88 real-engine games run, both families fired, --resume byte-identical, fitter output well-formed — operator APPROVED
- Task 3: deferred (off critical path)

---
*Phase: 180-three-preset-bot-strength-curves*
*Plan complete: Task 1 gate green + Task 2 pilot approved by operator (phase completes at pilot, D-01). Task 3 operator sweep deferred.*
*Completed: 2026-07-19*
