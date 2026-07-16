---
phase: 173-anchor-ladder-self-calibration-seed-101
plan: 01
subsystem: infra
tags: [node, chess.js, stockfish, maia, calibration-harness, esm]

# Dependency graph
requires: []
provides:
  - "scripts/lib/calibration-game-loop.mjs — mover-agnostic playTwoMoverGame({ Chess, pool, moverWhite, moverBlack, startFen, gameRng, onPly, maxPlies }), color-keyed white_win/black_win/draw results"
  - "sf8 (2600) / sf10 (2800) valid --anchors tokens via the extended SF_SKILL_ELO table"
  - "calibration-harness.mjs named exports: requireFlagValue, parsePositiveIntFlag, parseIntList, parseFloatList, deriveGameSeed, SEED_GAME_INDEX_MULTIPLIER, resolveGitSha, buildTimestamp"
affects: [173-02-anchor-ladder-orchestrator, 173-03, 173-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Color-keyed (white_win/black_win/draw) result shape for mover-agnostic game loops, mapped back to caller-relative (win/loss/draw) at the wrapper boundary"
    - "Safe circular ES-module import: game-loop.mjs imports harness.mjs's adjudication constants, referenced only inside function bodies (never at module top-level) so the cycle never hits a TDZ read"

key-files:
  created:
    - scripts/lib/calibration-game-loop.mjs
    - scripts/lib/calibration-game-loop.check.mjs
    - scripts/lib/calibration-anchors.check.mjs
  modified:
    - scripts/calibration-harness.mjs
    - scripts/lib/calibration-anchors.mjs

key-decisions:
  - "sf8/sf10 documented [ASSUMED] labels/ordering-only (never a Bradley-Terry fit input) directly in the SF_SKILL_ELO doc comment, per D-09/Pitfall 3"
  - "playTwoMoverGame's own maxPlies param (game-level PLY_CAP cutoff) is a distinct concept from playGame's maxPlies param (SearchBudget tree-depth cap) — the thin wrapper never forwards the latter into the former, preserving the pre-extraction PLY_CAP default"
  - "playGame's onPly wrapper remaps playTwoMoverGame's color-keyed mover ('white'/'black') back to the bot-relative 'bot'/'anchor' label via (p.mover === 'white') === botIsWhite, keeping the pre-extraction onPly payload byte-identical"

patterns-established:
  - "Mover dispatch by side-to-move (whiteToMove ? moverWhite : moverBlack), not by role (bot vs anchor) — the shape Plan 02's anchor-ladder orchestrator will reuse directly"

requirements-completed: [D-08, D-09, D-10]

coverage:
  - id: D1
    description: "SF_SKILL_ELO extended with sf8=2600/sf10=2800; parseAnchorSpec accepts sf8/sf10 without a parser change"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-anchors.check.mjs (node --import ./scripts/lib/frontend-alias-hook.mjs)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Mover-agnostic playTwoMoverGame extracted into calibration-game-loop.mjs, proven on synthesized checkmate/stalemate/adjudication fixtures"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-game-loop.check.mjs (node --import ./scripts/lib/frontend-alias-hook.mjs)"
        status: pass
    human_judgment: false
  - id: D3
    description: "calibration-harness.mjs's bot-vs-anchor playGame rewritten as a thin wrapper over playTwoMoverGame with NO observable behavior change"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "scripts/lib/calibration-determinism.check.mjs (real Maia+Stockfish engines, node --import ./scripts/lib/frontend-alias-hook.mjs) — same seed reproduced an identical 29-ply blend=1 game"
        status: pass
      - kind: unit
        ref: "scripts/lib/calibration-pruning.check.mjs (node --import ./scripts/lib/frontend-alias-hook.mjs)"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-07-15
status: complete
---

# Phase 173 Plan 01: Anchor Ladder Foundation Summary

**Extracted a color-keyed, mover-agnostic `playTwoMoverGame` game loop out of the bot-vs-anchor harness and wired Stockfish skills 8/10 into the anchor tables, both proven byte-identical / green against existing real-engine checks.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-15T19:51:37Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments
- `scripts/lib/calibration-game-loop.mjs` exports `playTwoMoverGame`, a two-mover game loop dispatched by side-to-move (not bot-vs-anchor role) — the foundation Plan 02's anchor-ladder orchestrator will drive directly.
- `calibration-harness.mjs`'s `playGame` is now a thin wrapper delegating to `playTwoMoverGame`, proven byte-identical via the existing real-engine `calibration-determinism.check.mjs` (same seed → identical 29-ply `moveUcis`) and `calibration-pruning.check.mjs`.
- `SF_SKILL_ELO` gained `8: 2600` / `10: 2800` (documented `[ASSUMED]`, labels/ordering-only); `parseAnchorSpec('sf8'|'sf10')` now works with zero parser changes.
- Eight previously module-local CLI/seed/build helpers (`requireFlagValue`, `parsePositiveIntFlag`, `parseIntList`, `parseFloatList`, `deriveGameSeed`, `SEED_GAME_INDEX_MULTIPLIER`, `resolveGitSha`, `buildTimestamp`) are now named exports, ready for Plan 02 to import instead of duplicate.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire Stockfish skills 8/10 into the anchor tables (D-09) + anchors parse check** - `f4bf2d35` (feat)
2. **Task 2: Extract the mover-agnostic game loop (D-08) + rewire the bot harness as a thin wrapper + export CLI helpers** - `c94b0655` (refactor)

## Files Created/Modified
- `scripts/lib/calibration-game-loop.mjs` - New module: `playTwoMoverGame` + color-keyed `classifyTerminalResultWhitePov`/`evaluateNonTerminalCutoffsWhitePov`/`updateSustainState`/`applyUciMove`, importing the D-10 adjudication constants from `calibration-harness.mjs`
- `scripts/lib/calibration-game-loop.check.mjs` - Structural check: synthesized checkmate/stalemate/adjudication-cutoff fixtures, no real engines
- `scripts/lib/calibration-anchors.check.mjs` - Parse/rating check: `SF_SKILL_ELO[8]/[10]`, `parseAnchorSpec('sf8'|'sf10'|'maia1500')`, `anchorRatingFor`
- `scripts/calibration-harness.mjs` - `playGame` rewritten as a thin wrapper; removed the now-superseded `classifyTerminalResult`/`updateSustainState`/`adjudicatedResult`/`evaluateNonTerminalCutoffs`/`applyUciMove`; 8 CLI/seed/build helpers exported
- `scripts/lib/calibration-anchors.mjs` - `SF_SKILL_ELO` extended with keys `8`/`10`; doc comment updated with the `[ASSUMED]` labels-only caveat

## Decisions Made
- sf8/sf10 documented `[ASSUMED]` labels/ordering-only (never a Bradley-Terry fit input) directly in the `SF_SKILL_ELO` doc comment, per D-09/Pitfall 3.
- `playTwoMoverGame`'s own `maxPlies` param (game-level `PLY_CAP` cutoff) is a distinct concept from `playGame`'s `maxPlies` param (`SearchBudget` tree-depth cap) — the thin wrapper never forwards the latter into the former, preserving the pre-extraction `PLY_CAP` default exactly.
- `playGame`'s `onPly` wrapper remaps `playTwoMoverGame`'s color-keyed mover (`'white'`/`'black'`) back to the bot-relative `'bot'`/`'anchor'` label via `(p.mover === 'white') === botIsWhite`, keeping the pre-extraction `onPly` payload byte-identical.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `calibration-determinism.check.mjs` (real Maia + Stockfish engines) took longer than the initial 180s timeout to complete two full games at the shipped bot budget; re-ran with a 590s timeout and it passed (29-ply `blend=1` game, byte-identical `moveUcis` across both seeded runs). Not a regression — this real-engine check has always run full games end-to-end; no code change needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `playTwoMoverGame` and the sf8/sf10 anchor tokens are ready for Plan 02's anchor-ladder orchestrator to import directly.
- The 8 newly-exported CLI/seed/build helpers let Plan 02 avoid duplicating WR-02 flag validation, seed derivation, git-sha resolution, and timestamp building.

---
*Phase: 173-anchor-ladder-self-calibration-seed-101*
*Completed: 2026-07-15*

## Self-Check: PASSED

All created files and referenced commit hashes verified present on disk / in git log.
