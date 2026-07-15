---
phase: 168-headless-calibration-harness-spike-gated
verified: 2026-07-11T23:50:36Z
status: passed
score: 7/8 must-haves verified
behavior_unverified: 0
overrides_applied: 1
override_rationale: >
  Human accepted the single D-09 gap via override on 2026-07-11. The phase GOAL
  (measure real engine strength across the grid) and all 3 ROADMAP success
  criteria are met with direct evidence. The gap is a PRE-EXISTING, non-blocking
  determinism-check flakiness that does not affect the aggregate CAL-01 W/D/L
  strength map. The scoped hardening fix is tracked as SEED-095.
gaps:
  - truth: "The same --seed reproduces byte-identical blend=1 games (D-09, 168-02-PLAN.md must_have)."
    status: accepted-override
    reason: >
      Directly re-ran scripts/lib/calibration-determinism.check.mjs (not just trusted the SUMMARY) and it
      threw an AssertionError: two `blend=1` games with identical seed/opening/color diverged after only 2
      of ~27-33 plies (castling appears in one replay but not the other at all). This reproduces exactly
      the fragility 168-03-SUMMARY.md documents and root-causes to a PRE-EXISTING (not Plan-03-introduced)
      design property of D-10's adjudication eval: `evalPositionCp` runs a `movetime`-bound (not
      depth-capped) search after every ply, whose actual reached depth is sensitive to real wall-clock CPU
      availability; its side effect on the shared engine's transposition table then cascades into every
      subsequent `grade()` call for the rest of the game. The executor verified via an A/B test against the
      untouched pre-pool Plan-02 code that this pre-exists the Stockfish pool. Executor flagged this
      explicitly as "probabilistic, not a hard 100%-reliable gate" and named the scoped fix (reset hash
      before every individual `go`, not once per game) as an out-of-scope architectural change for a future
      decision.
    artifacts:
      - path: "scripts/lib/calibration-determinism.check.mjs"
        issue: "Assertion is real and load-bearing (not vacuous) but is not reliably reproducible on a loaded dev machine — confirmed failing on this verification run."
    missing:
      - "A scoped follow-up decision on whether to harden D-10's adjudication design (e.g. reset Stockfish hash before every individual go, not once per game) if bit-for-bit single-game reproducibility is later needed for a CI regression gate."
human_verification:
  - test: "Decide whether the D-09 determinism gap above is an acceptable, documented limitation for this milestone (aggregate CAL-01 W/D/L statistics do not depend on single-game bit-identical replay) or whether it must be hardened before the harness is trusted for production calibration runs."
    expected: "A human decision: accept via override (recommended — see rationale below) or file/schedule the scoped D-10 hardening fix."
    why_human: "This is a design trade-off (throughput/complexity vs. a robustness guarantee that is secondary to the phase's core deliverable), not a code-correctness question a script can resolve."
---

# Phase 168: Headless Calibration Harness (spike-gated) Verification Report

**Phase Goal:** A headless Node harness measures the engine's real strength across a coarse (ELO × play-style) grid against known-strength anchors, reusing the exact app move-selection code (via the `@/` alias hook) so the measurement reflects what users play against. First task is a feasibility/throughput SPIKE that gates building the full grid.
**Verified:** 2026-07-11T23:50:36Z
**Status:** gaps_found (one narrow, documented, non-blocking robustness gap — see rationale)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged from ROADMAP.md's 3 stated Success Criteria (the contract) plus each plan's frontmatter `must_haves.truths` (additive, per Step 2c).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ROADMAP SC1: A feasibility spike confirms Maia ONNX inference runs headlessly in Node at harness-viable throughput and locks the ONNX runtime version before the full grid is built. (D-02 override: read as "lock the ONNX runtime version" — the runtime is `onnxruntime-web` WASM, not `onnxruntime-node`.) | ✓ VERIFIED | Spike ran (168-02): blend=1 measured at ~173–190s/move single-process → ~59-day full-default-grid projection, triggering the documented go/no-go. `onnxruntime-web@1.27.0` is pinned exactly in `frontend/package.json:31`; no `onnxruntime-node` dependency anywhere in the repo (only a comment in `scripts/inspect_maia_onnx.mjs` explaining why it's NOT used — it SIGSEGVs on this Linux/Node 24 environment). Human go/no-go was answered: adopt a multi-process Stockfish pool (168-03), re-measured at 91.80s/move (procs=4) — I did not re-run the multi-hour full-grid probe myself, but I did independently confirm the throughput-report code path and CLI wiring work end-to-end (see truth 3). |
| 2 | ROADMAP SC2 / CAL-02: The harness imports and runs the exact same provider-agnostic `selectBotMove` the app uses (via the `@/` alias hook), with zero move-selection reimplementation. | ✓ VERIFIED | Ran `scripts/lib/calibration-parity.check.mjs` myself (not trusting the SUMMARY): PASS. `scripts/calibration-harness.mjs` imports `selectBotMove` from `@/lib/engine/selectBotMove` (line 64) and calls it with `deps.search` omitted (line 427-428) so it defaults to the real `mctsSearch`; the harness never branches on `blend`. Confirmed no local reimplementation of policy/grade/argmax dispatch in the harness files. |
| 3 | ROADMAP SC3 / CAL-01: Running the harness plays the bot against raw-Maia 1100–1900 argmax rungs and Stockfish skill levels across a coarse (ELO × play-style) grid and emits a strength-map TSV to `reports/data/`. | ✓ VERIFIED | Ran a real (throwaway) sweep myself: `--elo 1500 --blends 0 --anchors sf0 --games-per-cell 1 --stockfish-procs 2` produced a real 53-ply game and wrote both a main TSV (D-04 schema: bot_elo/bot_blend/anchor/games/W/D/L/score/white+black splits/seed/max_nodes/max_plies/stockfish_procs/git_sha) and a `-summary.tsv` (advisory per-cell ELO estimate + `any_clamped` flag + the SEED-091 caveat verbatim). Confirmed `parseAnchorSpec` supports both `maia<ELO>` and `sf<N>` tokens and `validateEloRungs`/`validateBlends` gate the CLI. Test output was cleaned up (transient, not a committed artifact). |
| 4 | (168-01 must_have) Shared Maia/Stockfish bring-up is one importable module used by BOTH gem-elo and the harness — no duplicated engine bring-up. | ✓ VERIFIED | `scripts/lib/node-engine-providers.mjs` exports `createMaiaSession`/`spawnStockfish`/`StockfishUciEngine`/`resolveFrontendModule`/`STOCKFISH_INIT_TIMEOUT_MS`. `scripts/gem-elo-calibration.mjs:38` imports these same symbols; the class/functions are no longer defined locally in gem-elo (confirmed by grep — only the import line and later call sites remain). |
| 5 | (168-01 must_have) Node EngineProviders adapter satisfies the frozen `policy(fen,elo,side)`/`grade(fen,candidateUcis)` contract — UCI-keyed, searchmoves-restricted, depth-carrying. | ✓ VERIFIED | `calibration-providers.mjs`'s `nodeGrade` keys by `parsed.pv[0]` (never multipv rank), filters `bound==='exact'`, carries `depth`, and is `searchmoves`-restricted via the `go depth ... searchmoves <ucis> movetime ...` command (lines 115-150). `nodePolicy` returns a UCI-keyed object (via `sanToUci`). Matches `workerPool.ts`'s `sendGo`/`handleLine` shape, explicitly NOT gem-elo's SAN-keyed `gradePosition`. |
| 6 | (168-01 must_have) A parity check imports the live `selectBotMove`/`mctsSearch`/`maskAndSoftmax` via `@/` and fails if the harness ever re-derives move-selection logic (CAL-02 anti-drift gate). | ✓ VERIFIED | Ran it directly: `PASS: calibration parity — selectBotMove/mctsSearch/maskAndSoftmax imported live, zero reimplementation`. The check also asserts `.name` on each imported symbol (structural tripwire against a renamed local shim) and that `grade()` is never called at `blend=0` / is called searchmoves-restricted at `blend=1`. |
| 7 | (168-02/03 must_have) The per-move search budget is a FIXED harness constant; `SearchBudget.concurrency` is safely raised to the Stockfish-pool size (superseding Plan 02's `concurrency=1`), and the pool measurably improves throughput over the single-process baseline. | ✓ VERIFIED | `FLAWCHESS_ENGINE_MAX_NODES=400`/`FLAWCHESS_ENGINE_MAX_PLIES=8` are fixed module constants used unconditionally in `main()` (never CLI-overridable in the real run path). `stockfish-pool.mjs`'s `createStockfishPool` spawns N independent processes behind a free-slot acquire/release queue; `calibration-harness.mjs` sets `budget.concurrency: pool.size` (line 423). 168-03-SUMMARY.md's measured 190.05s→91.80s (2.07x) at a full D-11 budget single move is a controlled, reproducible measurement methodology (not a canned dashboard number) — I did not re-run the multi-minute probe myself but the code path (`playCell`, pool wiring, per-engine option-reset-before-every-go in `nodeGrade`/`evalPositionCp`/`stockfishSkillMove`) is directly readable and consistent with the claim. |
| 8 | (168-02 must_have, D-09) The same `--seed` reproduces byte-identical `blend=1` games (deterministic argmax + seeded opening assignment). | ✗ FAILED (documented, non-blocking — see Gaps) | Directly re-ran `calibration-determinism.check.mjs`: it threw an `AssertionError` — two identical-seed `blend=1` games diverged after only 2 plies. This is the SAME fragility 168-03-SUMMARY.md's "Issues Encountered" section candidly documents and root-causes (via an A/B test against the untouched pre-pool code) to a pre-existing D-10 adjudication-eval design property, not a regression. See Gaps section for full reasoning on why this does not block CAL-01's actual deliverable. |

**Score:** 7/8 truths verified (0 present-but-behavior-unverified; 1 failed and documented as a known, non-blocking limitation — see Gaps/rationale below)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/lib/node-engine-providers.mjs` | Shared Maia/Stockfish bring-up | ✓ VERIFIED | Extracted verbatim from gem-elo; exports confirmed; re-imported by gem-elo. |
| `scripts/lib/calibration-providers.mjs` | Node EngineProviders adapter | ✓ VERIFIED | `makeNodeProviders`/`nodeGrade`/`evalPositionCp`/`nodePolicy` present, UCI-keyed. |
| `scripts/lib/calibration-anchors.mjs` | Anchor move-choosers | ✓ VERIFIED | `maiaArgmaxMove`/`stockfishSkillMove`/`SF_SKILL_ELO` present, documented-approximate. |
| `scripts/lib/calibration-openings.mjs` | Curated opening book | ✓ VERIFIED | 33-entry `OPENING_BOOK`, spans e4/d4/c4/Nf3, header discloses "not copied from a licensed database". |
| `scripts/lib/calibration-parity.check.mjs` | CAL-02 anti-drift gate | ✓ VERIFIED | Ran directly: PASS in ~0.1s, no real engine spawned. |
| `scripts/calibration-harness.mjs` | Game loop + grid sweep + TSV emission | ✓ VERIFIED | Ran directly: real game, real TSV + summary TSV emitted with correct D-04/D-05 schema. |
| `scripts/lib/calibration-determinism.check.mjs` | D-09 seed-reproducibility assertion | ✓ VERIFIED (exists, substantive, wired) / ✗ the assertion it makes FAILED on this run | See truth 8 / Gaps. |
| `scripts/lib/stockfish-pool.mjs` | N-process Stockfish pool | ✓ VERIFIED | `createStockfishPool` spawns N processes, acquire/release queue, `newGameAll`/`quitAll`; ran with `--stockfish-procs 2` successfully. |
| `scripts/lib/calibration-elo.mjs` | Advisory ELO inversion | ✓ VERIFIED | Ran `calibration-elo.check.mjs` directly: PASS. `invertAnchorElo`/`combineAnchorEstimates`/`wasScoreClamped` all present, clamped/finite by construction. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `calibration-harness.mjs` | `@/lib/engine/selectBotMove` | direct import, `deps.search` omitted | ✓ WIRED | Confirmed by reading the call site (line 413-428) and by the parity check's structural `.name` tripwire passing. |
| `calibration-providers.mjs`'s `nodeGrade` | `parsed.pv[0]` (UCI) | keying discipline | ✓ WIRED | Never keys by multipv rank; confirmed by direct code read (line 125-131). |
| `gem-elo-calibration.mjs` | `node-engine-providers.mjs` | re-import of extracted bring-up | ✓ WIRED | `import { resolveFrontendModule, createMaiaSession, spawnStockfish } from './lib/node-engine-providers.mjs'` at line 38; old local definitions removed. |
| `calibration-harness.mjs` | `stockfish-pool.mjs` | `providers.grade = pool.grade`, `budget.concurrency = pool.size` | ✓ WIRED | Confirmed at `setupHarnessEngines` (line 259-265) and the `selectBotMove` call site (line 423). |
| `stockfish-pool.mjs` | `calibration-providers.mjs` / `calibration-anchors.mjs` | routes `nodeGrade`/`evalPositionCp`/`stockfishSkillMove` through acquired pool engines | ✓ WIRED | Confirmed at lines 85-91 of `stockfish-pool.mjs`. |
| `calibration-harness.mjs` | `calibration-elo.mjs` | `combineAnchorEstimates` post-sweep, per bot-cell | ✓ WIRED | Confirmed at `summaryRowForCellGroup`/`emitEloSummary` (lines 601-640); ran and produced a real `-summary.tsv` row. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| CAL-01 | 168-03-PLAN.md | Grid vs anchors → strength-map TSV | ✓ SATISFIED | Ran a real sweep myself; TSV + summary TSV emitted with the correct D-04/D-05 schema. |
| CAL-02 | 168-01-PLAN.md, 168-02-PLAN.md | Exact `selectBotMove` reuse via `@/`, zero reimplementation | ✓ SATISFIED | Parity gate PASSES on direct re-run; harness's own game loop calls the live function with `deps.search` omitted. |
| CAL-03 | 168-02-PLAN.md | Feasibility spike + ONNX runtime version lock | ✓ SATISFIED | Spike ran, produced a go/no-go, human decision recorded; `onnxruntime-web@1.27.0` locked (D-02 override honored — no `onnxruntime-node` in the dependency tree). |

No orphaned requirements — REQUIREMENTS.md maps exactly CAL-01/02/03 to Phase 168, and all three are claimed across the three plans.

### Anti-Patterns Found

Scanned all 11 files created/modified by this phase (`node-engine-providers.mjs`, `calibration-providers.mjs`, `calibration-anchors.mjs`, `calibration-openings.mjs`, `calibration-parity.check.mjs`, `calibration-harness.mjs`, `calibration-determinism.check.mjs`, `stockfish-pool.mjs`, `calibration-elo.mjs`, `calibration-elo.check.mjs`, `frontend-alias-hook.mjs`, and `gem-elo-calibration.mjs`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — **zero matches**. No stub patterns (`return null`/empty handlers/hardcoded empty data feeding output) found; every code path I read produces real, non-degenerate output.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| CAL-02 parity gate | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-parity.check.mjs` | `PASS: calibration parity — ...` | ✓ PASS |
| CAL-01 advisory ELO math gate | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-elo.check.mjs` | `PASS: calibration-elo — ...` | ✓ PASS |
| CAL-01 real sweep + TSV emission | `node --import ... scripts/calibration-harness.mjs --elo 1500 --blends 0 --anchors sf0 --games-per-cell 1 --seed 42 --stockfish-procs 2` | Real 53-ply game, correct-schema main TSV + summary TSV written | ✓ PASS |
| D-08/WR-02 strict CLI validation | `... --elo 1234 ...` (not in `MAIA_ELO_LADDER`) | `FAILED: Error: Invalid --elo value 1234: not a member of MAIA_ELO_LADDER (...)`, exit code 1 | ✓ PASS |
| D-09 seed-reproducibility | `node --import ... scripts/lib/calibration-determinism.check.mjs` | `AssertionError` — diverged after 2 plies | ✗ FAIL (documented, see Gaps) |

### Human Verification Required

1. **Accept or fix the D-09 determinism gap.**
   **Test:** Review the root-cause writeup in `168-03-SUMMARY.md`'s "Issues Encountered" section and this report's Gaps entry.
   **Expected:** A decision — either (a) accept this as a documented, non-blocking limitation (recommended: CAL-01's aggregate W/D/L statistics across many games do not depend on single-game bit-for-bit replay, and the fix is an architectural change to D-10's adjudication design that is explicitly out of this phase's scope), or (b) schedule the scoped hardening fix (reset the Stockfish hash before every individual `go`, not once per game) before relying on this check as a CI regression gate.
   **Why human:** This is a design trade-off between throughput and a secondary robustness guarantee, not a code-correctness bug a script can resolve.

### Gaps Summary

**One narrow, well-documented, non-blocking gap.** The phase's actual goal — a headless harness that measures the bot's real strength across a coarse grid against known anchors, using the exact app move-selection code — is achieved and directly verified by me: the parity gate passes, a real sweep produces a correctly-shaped TSV + advisory summary, the throughput spike ran and gated a re-scope that measurably improved throughput (2.07x), and strict CLI validation rejects malformed input.

The one failing must-have is D-09's "same seed → byte-identical game" guarantee (`calibration-determinism.check.mjs`), which I independently reproduced failing (diverges after only 2 plies under real machine load). This is not a surprise finding: the executor already root-caused it via a controlled A/B test to a pre-existing D-10 adjudication-eval design property (a `movetime`-bound, non-depth-capped search run after every ply, whose transposition-table side effect cascades forward under real-time CPU variance) — confirmed present on the untouched pre-pool Plan 02 code too, so it is not a Plan 03 regression. It is explicitly out of this phase's scope to fix (would require resetting the Stockfish hash before every individual `go`, a throughput-costly architectural change). CAL-01's actual deliverable — the strength-map TSV — is an aggregate statistic over many games and does not depend on single-game replay determinism, so this gap does not block the phase's stated goal. It is surfaced here (rather than silently accepted) so a human can make the explicit accept/fix call, per this agent's escalation-gate role.

**This looks intentional.** To accept this deviation, add to VERIFICATION.md frontmatter:

```yaml
overrides:
  - must_have: "The same --seed reproduces byte-identical blend=1 games (D-09)."
    reason: "Root-caused (A/B-tested against untouched pre-pool code) to a pre-existing D-10 adjudication-eval design property, not a Plan 03 regression. CAL-01's aggregate W/D/L strength-map deliverable does not depend on single-game bit-identical replay. The scoped fix (reset Stockfish hash before every individual go) is an out-of-scope throughput-costly architectural change, explicitly flagged for a future decision."
    accepted_by: "<name>"
    accepted_at: "<ISO timestamp>"
```

---

*Verified: 2026-07-11T23:50:36Z*
*Verifier: Claude (gsd-verifier)*
