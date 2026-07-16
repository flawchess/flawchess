---
phase: 173-anchor-ladder-self-calibration-seed-101
verified: 2026-07-16T05:32:04Z
status: passed
score: 16/16 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 173: Anchor ladder self-calibration (SEED-101) Verification Report

**Phase Goal:** Round-robin the calibration harness's anchors against each other (Maia-argmax rungs 700–2300, SF Skill 0/3/5/8/10, cross-family games included) and fit a logistic/BayesElo-style rating model over the game graph, placing every anchor on one common internal scale with measured spacing (scale fixed arbitrarily, e.g. maia1500 = 1500; explicitly NOT human ELO). Unblocks SEED-102 and answers whether the Maia-3 argmax ladder is compressed like Maia-1's.
**Verified:** 2026-07-16T05:32:04Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

**Roadmap-level (goal-backward, derived from ROADMAP.md goal text — no `success_criteria` array present):**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Anchor-vs-anchor games played among Maia-argmax rungs 700–2300 and SF Skill 0/3/5/8/10, cross-family included | ✓ VERIFIED | `reports/data/anchor-ladder-2026-07-15T20-28-27-398Z.tsv` — 456 real games (216 probe + 240 measure) across all 27 candidate pairs; 10 cross-family (maia×sf) pairs measured at 24 games each |
| 2 | A logistic/BayesElo-style rating model is fit over the resulting game graph | ✓ VERIFIED | `scripts/calibration_anchor_fit.py::fit_bradley_terry` (stdlib Zermelo/MM Bradley-Terry MLE), 7/7 pytest passing, actually executed against the real TSV (commit `c6126878`) |
| 3 | Every anchor placed on one common internal scale with measured spacing, scale fixed arbitrarily (maia1500 = 1500, explicitly NOT human ELO) | ✓ VERIFIED | `scripts/lib/calibration-internal-scale.mjs` — `INTERNAL_RATING` has all 10 anchors, `maia1500: 1500.00` exactly; D-13 "NOT human ELO" caveat in the module docstring, the JSON sibling's `_caveat` field, the pairs-TSV footer, and the findings note |
| 4 | Answers whether the Maia-3 argmax ladder is compressed like Maia-1's | ✓ VERIFIED | `.planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md` Finding 2: explicit verdict — full ladder ≈2.8x compression (36% of nominal 1600pt retained), 1100→1900 sub-range ≈3.2x, directly cross-checked against the independently-measured Maia-1 figure (≈3.3x, 2026-07-13 note) |
| 5 | Unblocks SEED-102 | ✓ VERIFIED | Findings note "What this unblocks" section states the concrete mechanism (internal-rating-based anchor windowing replaces the compressed nominal-Elo `ANCHOR_ELO_WINDOW`); the stable artifact SEED-102 will import (`INTERNAL_RATING`) exists and is committed |

**Plan-level must-haves (173-01 through 173-04 frontmatter):**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | Bot harness plays byte-identical games after game-loop extraction (no behavior change) | ✓ VERIFIED | `scripts/lib/calibration-determinism.check.mjs` re-run live during this verification — PASS, real Maia+Stockfish engines, identical 29-ply `moveUcis` across two seeded runs |
| 7 | A mover-agnostic two-mover game loop exists, drivable by any script with an arbitrary mover per color | ✓ VERIFIED | `scripts/lib/calibration-game-loop.mjs` exports `playTwoMoverGame`; imported by both `calibration-harness.mjs` (bot-vs-anchor wrapper) and `calibration-anchor-ladder.mjs` (anchor-vs-anchor); `calibration-game-loop.check.mjs` re-run live — PASS (checkmate/stalemate/adjudication fixtures) |
| 8 | `parseAnchorSpec` accepts `sf8`/`sf10` without throwing | ✓ VERIFIED | `calibration-anchors.check.mjs` re-run live — PASS; `SF_SKILL_ELO[8]=2600`/`[10]=2800` |
| 9 | Orchestrator plays anchor-vs-anchor games and writes a raw per-game TSV incrementally (crash-durable) | ✓ VERIFIED | Real 456-game run produced the committed ledger; the run was interrupted mid-sweep by the D-04 guard and resumed via `--resume` without losing prior games (STATE.md, 173-04-SUMMARY.md) |
| 10 | Two-pass scheduler probes candidate pairs, then measures only pairs whose probe score sits in [0.2, 0.8] | ✓ VERIFIED | Ledger `pass` column: 216 probe-tagged + 240 measure-tagged rows; per-pair game counts are either exactly 8 (dropped) or exactly 24 (extended, not replayed) for all 27 pairs |
| 11 | The played game graph stays connected with ≥2 informative cross-family links, or the run re-targets/fails loud (D-04) | ✓ VERIFIED (behaviorally, not just by presence) | The real run actually tripped the D-04 guard on the `{maia700, sf0}` island and failed loud; a user-approved band-relaxing rescue (`rescueConnectivity`, commit `a2f96e81`) was added and the resumed run completed with 10 genuine cross-family measured pairs — far above the ≥2 floor |
| 12 | Per-pair aggregate TSV carries the D-13 caveat and `--resume` reconstructs progress from the ledger | ✓ VERIFIED | `anchor-ladder-...-pairs.tsv` footer: `caveat  internal scale — NOT human ELO; downstream fit fixes maia1500 = 1500`; `--resume` was exercised for real during the connectivity-rescue recovery |
| 13 | Python script fits a joint Bradley-Terry/Elo rating for every anchor, draws folded 0.5/0.5 | ✓ VERIFIED | `build_win_counts` folds draws to 0.5/0.5 (unit-tested); real fit output has non-placeholder ratings for all 10 anchors |
| 14 | Fitted scale pinned so `maia1500 == 1500` exactly | ✓ VERIFIED | `apply_scale_fix` assigns the pin directly (not via addition) — `maia1500: 1500.00` in the real output, CI `[1500.0, 1500.0]` |
| 15 | Per-anchor bootstrap CIs and per-pair residuals (cross-family flagged) produced | ✓ VERIFIED | `anchor-ladder-internal-scale.json` — `confidence_intervals` (10 anchors) + `residuals` (27 rows, each with a `cross_family` boolean) |
| 16 | Disconnected/under-cross-linked game graph rejected loudly before fitting (D-04 defensive re-check) | ✓ VERIFIED (after fix) | Code review found this guard was silently defeatable (CR-01: un-canonicalized directional pairs from alternating colors double-counted one bridge as two links). Fixed in commit `0384b52a` — pairs now canonicalized (`sorted()`) before the count, with a mutation-proven regression test (`test_main_single_bridge_both_orientations_fails_connectivity`) asserting the guard now correctly raises on a single real bridge seen in both color orientations. Confirmed the fix is live in the current tree and the regression test passes (`uv run pytest tests/scripts/test_calibration_anchor_fit.py -x` → 7/7 passing). The real run's actual graph has 10 genuine cross-family bridges (well above the pre-fix false-pass threshold), so the pre-fix bug did not corrupt the committed fit output — but the guard itself is now correctly enforced going forward. |

**Score:** 16/16 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/lib/calibration-game-loop.mjs` | Mover-agnostic `playTwoMoverGame` | ✓ VERIFIED | Exists, exported, wired into both harness scripts, structural check green |
| `scripts/lib/calibration-game-loop.check.mjs` | Structural check | ✓ VERIFIED | Re-run live — 3/3 PASS |
| `scripts/lib/calibration-anchors.check.mjs` | Parse/rating check | ✓ VERIFIED | Re-run live — PASS |
| `scripts/lib/calibration-anchor-schedule.mjs` | D-01/D-02/D-04 pure-logic scheduler | ✓ VERIFIED | Exports present, re-run live — PASS (incl. `rescueConnectivity`) |
| `scripts/lib/calibration-anchor-schedule.check.mjs` | Pure-logic check | ✓ VERIFIED | Re-run live — 6/6 PASS |
| `scripts/calibration-anchor-ladder.mjs` | Standalone D-08 orchestrator | ✓ VERIFIED | `node --check` clean; drives `playTwoMoverGame`; used to produce the real 456-game run |
| `scripts/calibration_anchor_fit.py` | Stdlib Bradley-Terry fit CLI | ✓ VERIFIED | ruff + ty clean, 0 numpy/scipy imports, executed for real |
| `tests/scripts/test_calibration_anchor_fit.py` | pytest coverage incl. CR-01 regression | ✓ VERIFIED | 7/7 passing (6 original + 1 CR-01 regression) |
| `scripts/lib/calibration-internal-scale.mjs` | Node-importable internal scale (D-12 #2) | ✓ VERIFIED | Committed, `maia1500===1500`, all 10 anchors numeric, D-13 docstring |
| `reports/data/anchor-ladder-internal-scale.json` | Ratings + CIs + residuals sibling | ✓ VERIFIED | Committed, all fields present |
| `reports/data/anchor-ladder-<ts>.tsv` + `-pairs.tsv` | Raw run output (D-12 #1) | ✓ VERIFIED | Committed, 456 games, clean header, trailing newline (not truncated) |
| `.planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md` | Findings note (D-12 #3) | ✓ VERIFIED | Committed, 5 numbered findings, explicit compression verdict, OQ2 closure, D-13 caveat |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `calibration-harness.mjs` `playGame` | `calibration-game-loop.mjs` `playTwoMoverGame` | delegation | ✓ WIRED | Import at line 76; `playGame` builds mover closures and calls `playTwoMoverGame` (line 460); no inline `for(;;)` loop remains in `playGame` |
| `calibration-anchors.mjs` `SF_SKILL_ELO` | `calibration-harness.mjs` `parseAnchorSpec` | membership gate | ✓ WIRED | `parseAnchorSpec` unmodified (per D-09 "fix at the map"); gate now passes for sf8/sf10 automatically |
| `calibration-anchor-ladder.mjs` | `calibration-game-loop.mjs` `playTwoMoverGame` + anchor movers | direct call | ✓ WIRED | Line 60-61 imports, line 252 `playTwoMoverGame({ ..., moverWhite, moverBlack, ... })` with `maiaArgmaxMove`/`pool.skillMove` closures |
| Per-game TSV header (Node writer) | `load_games` (Python parser) | shared column contract | ✓ WIRED | Both sides declare the identical 10-column header (`pass anchor_white anchor_black result reason plies game_index opening seed git_sha`); the real ledger's header line matches `TSV_HEADER` in `calibration_anchor_fit.py` byte-for-byte |
| `calibration_anchor_fit.py` `main()` | `check_connectivity` | D-04 defensive re-check | ✓ WIRED (fixed) | Runs before any fit call; pairs now canonicalized (commit `0384b52a`) so it genuinely enforces ≥2 distinct cross-family bridges |

### Data-Flow Trace (Level 4)

Not applicable in the conventional sense (no UI/DB-backed component rendering dynamic data). The equivalent trace for this research-tooling phase: raw ledger (real engine games) → `load_games`/`build_win_counts` (real parsing, not static) → `fit_bradley_terry` (real MLE on real win counts, not a stub) → `calibration-internal-scale.mjs`/JSON (real fitted numbers, no placeholder `0`s) → findings note (real numbers quoted from the JSON). Traced end-to-end and confirmed non-hollow at every hop above.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Extracted game loop preserves bot-harness behavior (real engines) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs` | PASS — identical 29-ply game across two seeded runs | ✓ PASS |
| Bot-harness pruning/resume logic unaffected | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-pruning.check.mjs` | PASS (3/3 assertions) | ✓ PASS |
| New game-loop module correctness (synthesized fixtures) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-game-loop.check.mjs` | PASS (checkmate/stalemate/adjudication) | ✓ PASS |
| Scheduler pure-logic (probe/measure/connectivity/rescue) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchor-schedule.check.mjs` | PASS (6/6) | ✓ PASS |
| Anchor parse/rating (sf8/sf10) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchors.check.mjs` | PASS | ✓ PASS |
| Rating-fit pytest suite incl. CR-01 mutation-proven regression | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -x -q` | 7 passed | ✓ PASS |
| ruff/ty on the fit script | `uv run ruff check scripts/calibration_anchor_fit.py tests/scripts/test_calibration_anchor_fit.py && uv run ty check scripts/calibration_anchor_fit.py` | All checks passed | ✓ PASS |
| Orchestrator syntax validity | `node --check scripts/calibration-anchor-ladder.mjs` | SYNTAX-OK | ✓ PASS |
| No numpy/scipy in the fit script | `grep -Ec 'import (numpy|scipy)' scripts/calibration_anchor_fit.py` | 0 | ✓ PASS |
| No stray debt markers in touched files | `grep -E 'TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER'` across all 7 touched calibration files | no matches | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention applies to this phase (Node/Python `.check.mjs`/pytest checks serve the equivalent role and are covered above). Skipped — no probe files declared or discovered.

### Requirements Coverage

No milestone `REQUIREMENTS.md` entries map to Phase 173 (`grep -n "173" .planning/REQUIREMENTS.md` → no matches), consistent with the ROADMAP's own `**Requirements**: TBD (none mapped; plans trace CONTEXT.md decisions D-01–D-13)`. Verified against `173-CONTEXT.md`'s locked decisions instead:

| Decision | Plan(s) | Status | Evidence |
|----------|---------|--------|----------|
| D-01 (two-pass probe→measure) | 173-02 | ✓ SATISFIED | Real run: 8-game probe / 24-game measure split confirmed in ledger |
| D-02 (no full round-robin; adjacent + cross-family only) | 173-02 | ✓ SATISFIED | 27 candidate pairs played, not the 45-pair full round-robin of 10 anchors |
| D-03 (24 games/measured pair, balanced colors) | 173-02 | ✓ SATISFIED | All measure pairs at exactly 24 games |
| D-04 (connectivity guard, ≥2 cross-family links) | 173-02, 173-03 | ✓ SATISFIED | Node guard triggered for real, rescued; Python defensive re-check bug found+fixed (CR-01) |
| D-05 (Python fit, logistic/BT MLE, maia1500=1500 pin) | 173-03 | ✓ SATISFIED | Implemented, tested, executed |
| D-06 (uncertainty + residuals mandatory) | 173-03 | ✓ SATISFIED | Bootstrap CIs + cross-family-flagged residuals present |
| D-07 (stdlib-preferred, no forced scipy) | 173-03 | ✓ SATISFIED | 0 numpy/scipy imports |
| D-08 (standalone script, not a harness mode) | 173-01, 173-02 | ✓ SATISFIED | `calibration-anchor-ladder.mjs` is standalone; extraction avoided duplication |
| D-09 (wire sf8/sf10) | 173-01 | ✓ SATISFIED | `SF_SKILL_ELO[8]/[10]` added |
| D-10 (keep harness conventions, no behavior change) | 173-01, 173-02 | ✓ SATISFIED | Determinism/pruning checks green |
| D-11 (execute the real run) | 173-04 | ✓ SATISFIED | 456-game real sweep completed, human-approved checkpoint |
| D-12 (three deliverable artifacts) | 173-04 | ✓ SATISFIED | Raw+pairs TSV, JS+JSON scale, findings note — all committed |
| D-13 (labeling discipline) | 173-02, 173-03, 173-04 | ✓ SATISFIED | Caveat present in every artifact checked above |

All 13 decisions (D-01–D-13) traced and satisfied; none orphaned.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/calibration-anchor-ladder.mjs` | `validateResumeSeed` (~L573-579) | `--resume` only validates `--seed`, not `--games-per-probe`/`--games-per-measure`/`--anchors` (code-review WR-02) | ℹ️ Info (deferred by design) | Does not affect the completed run (single invocation lineage, consistent args throughout, confirmed via `git log` / STATE.md). Explicitly deferred in 173-REVIEW.md's fix log for SEED-102 if the harness is reused with untrusted resume inputs. Not a phase-goal blocker. |
| `scripts/calibration-anchor-ladder.mjs`, `scripts/calibration-harness.mjs` | `--seed` parsing (~L156-165 / L281-290) | Fractional `--seed` (e.g. `1.5`) silently truncates via `Number.parseInt` rather than rejecting (code-review IN-01) | ℹ️ Info (deferred) | Cosmetic; real run used integer `--seed 1`. Not a phase-goal blocker. |

No debt markers (TBD/FIXME/XXX) found in any of the 7 touched calibration files. No stub returns, no hardcoded-empty-with-no-real-source patterns, no placeholder ratings in the committed internal-scale artifacts.

### Human Verification Required

None outstanding. The phase's one required human checkpoint (Task 1 of Plan 04 — executing the real multi-hour sweep) was already completed and approved during execution (STATE.md: "user-approved" band-relaxing connectivity rescue at commit `a2f96e81`; `173-04-SUMMARY.md` Task 1 marked complete via `checkpoint:human-verify`).

### Gaps Summary

None. All 16 must-have truths (5 roadmap-level + 11 plan-level) verified against the live codebase, not SUMMARY.md claims: every automated check (`.check.mjs` × 4, pytest × 1, ruff/ty × 2) was re-run live during this verification pass rather than trusted from prior reports, the byte-identical-behavior claim was independently re-confirmed against real Maia+Stockfish engines, and the one CRITICAL code-review finding (CR-01, a genuine connectivity-guard bypass) was independently traced to its fix commit and confirmed both structurally (diff review) and behaviorally (mutation-proven regression test passing). The real 456-game sweep's committed data was independently re-derived (pair/game counts, cross-family bridge count) from the raw TSV rather than taken from the findings note's own prose.

---

_Verified: 2026-07-16T05:32:04Z_
_Verifier: Claude (gsd-verifier)_
