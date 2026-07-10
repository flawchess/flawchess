---
phase: 157-flawchess-agreement-verdict-prose-hoverable-moves
plan: 01
subsystem: ui
tags: [typescript, vitest, chess-engine, flawchess-engine, stockfish]

requires:
  - phase: 153-155
    provides: RankedLine/PvLine types (engine/types.ts, uciParser.ts) and the evalToExpectedScore Lichess win% sigmoid (liveFlaw.ts)
provides:
  - "computeFlawChessVerdict — pure classifier comparing FlawChess practical #1 vs Stockfish objective #1 into aligned/safe/sharp tiers, or null on an incomplete snapshot"
  - "SHARP_DROP_THRESHOLD named constant (BLUNDER_DROP alias) for the win%-drop tier split"
affects: [157-02 (Wave-2 component consuming this classifier for prose rendering)]

tech-stack:
  added: []
  patterns:
    - "Pure worker-free/chess.js-free classifier module mirroring positionVerdict.ts's shape (tier union + named-move interface + null-gate contract)"

key-files:
  created:
    - frontend/src/lib/flawChessVerdict.ts
    - frontend/src/lib/flawChessVerdict.test.ts
  modified: []

key-decisions:
  - "D-04 aligned check is UCI-string equality (rootMove === moves[0]), performed BEFORE the drop computation — not derived from drop === 0"
  - "SHARP_DROP_THRESHOLD is the imported BLUNDER_DROP alias from @/generated/flawThresholds, never restated as a literal"
  - "FlawChess-side FlawChessVerdictMove always sets evalMate: null (Pitfall 4 — RankedLine has no mate field)"
  - "drop is clamped to >= 0 defensively via Math.max(0, ...) even though it's always non-negative by construction (D-06)"
  - "Adjusted the Wave-0 test fixture cp values for the D-05 sharp + boundary cases (from the plan's illustrative +210cp/+40cp example, which computed to a 0.147 drop — just under the 0.15 threshold) so the sharp case's win%-drop lands unambiguously above SHARP_DROP_THRESHOLD, and the boundary case ceils the inverse-sigmoid cp so floating-point rounding cannot land the drop just under the threshold"

requirements-completed: []  # REVIEW-02 spans both plans in this phase; the tier-classification core ships here, the prose/UI consumer ships in 157-02 — deferring the checkbox flip to avoid a partial-delivery mark

coverage:
  - id: D1
    description: "computeFlawChessVerdict classifies D-04 aligned (same UCI move on both sides)"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#same UCI move on both sides -> aligned, drop 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "computeFlawChessVerdict classifies D-05 safe/sharp divergence via the win%-drop threshold, including the inclusive >= boundary at SHARP_DROP_THRESHOLD"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#divergent picks with a small win%-drop -> safe"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#divergent picks with a large win%-drop (trap) -> sharp"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#a drop exactly at SHARP_DROP_THRESHOLD maps to sharp (inclusive edge)"
        status: pass
    human_judgment: false
  - id: D3
    description: "computeFlawChessVerdict returns null (never a bogus tier) on any incomplete snapshot: missing FC line, missing SF line, missing FC objective eval, or SF with both evalCp and evalMate null"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#flawChessLine null -> null result"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#stockfishLine null -> null result"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#FC objectiveEvalCp null -> null result"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#SF with both evalCp and evalMate null -> null result"
        status: pass
    human_judgment: false
  - id: D4
    description: "FlawChess side never reads/writes a mate field (RankedLine has none); an SF mate pick still classifies correctly"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#an SF pick expressed as mate still classifies (uses the mate mapping)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Mover POV (black to move) flips the sign so the drop is computed from the mover's POV and remains >= 0"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/flawChessVerdict.test.ts#flips the sign so the drop is computed from the movers POV and remains >= 0"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-07
status: complete
---

# Phase 157 Plan 01: FlawChess Agreement Verdict Classifier Summary

**Pure `computeFlawChessVerdict` classifier module scoring FlawChess's practical #1 pick against Stockfish's objective #1 pick into aligned/safe/sharp tiers via the app-wide win%-drop scale, with a strict null-gate for incomplete snapshots**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-07T07:58:00Z (approx.)
- **Completed:** 2026-07-07T08:02:33Z
- **Tasks:** 2 (TDD RED/GREEN)
- **Files modified:** 2

## Accomplishments
- `frontend/src/lib/flawChessVerdict.ts`: pure, worker-free, chess.js-free module exporting `FlawChessVerdictTier`, `FlawChessVerdictMove`, `FlawChessVerdictResult`, `SHARP_DROP_THRESHOLD`, and `computeFlawChessVerdict(flawChessLine, stockfishLine, mover)`.
- D-04 aligned: same UCI move on both sides classifies as `aligned` with `drop: 0`, checked via string equality before any win%-drop math.
- D-05 safe/sharp: divergent picks classified by the win%-drop sacrificed (`evalToExpectedScore(SF) - evalToExpectedScore(FC)`), split at the imported `SHARP_DROP_THRESHOLD` (`BLUNDER_DROP`, 0.15), inclusive `>=` on the sharp side.
- D-06 null gate: `null` result for any of — missing FlawChess line, missing Stockfish line, missing FC `objectiveEvalCp`, or a Stockfish line with both `evalCp` and `evalMate` null.
- Pitfall 4 respected: the FlawChess-side `FlawChessVerdictMove.evalMate` is always `null` (RankedLine has no mate field); the Stockfish-side pick correctly carries a mate value when the PV is a forced mate, and still classifies (mate maps through the same sigmoid via `MATE_CP_EQUIVALENT`).
- `frontend/src/lib/flawChessVerdict.test.ts`: 10 unit tests covering D-04, D-05 (safe + sharp + inclusive boundary), D-06 (4 null-gate cases), Pitfall 4, and mover POV (black to move).

## Task Commits

Each task was committed atomically:

1. **Task 1: Author the failing tier-classification tests (RED)** - `4dec1578` (test)
2. **Task 2: Implement the pure flawChessVerdict module (GREEN)** - `11f7e5d9` (feat)

**Plan metadata:** commit to follow (docs: complete plan)

_TDD flow: RED (module unresolved) → GREEN (all 10 tests pass) — no REFACTOR needed._

## Files Created/Modified
- `frontend/src/lib/flawChessVerdict.ts` - pure classifier: tier union, verdict-move interface, `SHARP_DROP_THRESHOLD`, `computeFlawChessVerdict`
- `frontend/src/lib/flawChessVerdict.test.ts` - Wave-0 unit tests (D-04/D-05/D-06/Pitfall 4/mover-POV)

## Decisions Made
- D-04's aligned check uses UCI-string equality (`rootMove === moves[0]`), performed before the drop split — not derived from `drop === 0`, since two different UCI moves could coincidentally share the same eval in a flat position.
- `SHARP_DROP_THRESHOLD` is the imported `BLUNDER_DROP` alias from `@/generated/flawThresholds` — no bare `0.15` literal anywhere in the module or its tests (grep-verified).
- `drop` is defensively clamped to `>= 0` via `Math.max(0, ...)` even though it's always non-negative by construction (D-06), guarding against any future floating-point edge case.
- Adjusted the Wave-0 test fixtures for the D-05 sharp and boundary cases: the plan's illustrative example (FC +40cp / SF +210cp) computes to a win%-drop of ~0.147 — just under the 0.15 threshold, which would have made that "sharp" test fail against the real sigmoid. Replaced with FC +40cp / SF +300cp (drop ≈0.214, comfortably sharp). The exact-boundary test derives `sfEvalCp` from the inverse sigmoid and now `Math.ceil`s the result (was `Math.round`, which landed a hair under the threshold at 0.1499 instead of >= 0.15) so the `>=` inclusive-edge assertion is not flaky.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture cp values did not actually exercise the sharp/boundary tiers**
- **Found during:** Task 2 (GREEN verification — `npx vitest run` initially failed 2/10 tests)
- **Issue:** The plan's example fixture (FC objective +40cp, SF objective +210cp) computes a win%-drop of 0.1475 via the real `evalToExpectedScore` sigmoid — below `SHARP_DROP_THRESHOLD` (0.15), so the intended "sharp" test case actually exercised the "safe" branch. Separately, the boundary test's `Math.round`-based inverse-sigmoid cp landed the drop at 0.1499, just under the threshold, making the ">= inclusive edge -> sharp" assertion fail.
- **Fix:** Raised the sharp-case fixture to SF objective +300cp (drop ≈0.214). Switched the boundary case's inverse-sigmoid rounding from `Math.round` to `Math.ceil` so the derived cp value's drop lands at-or-above the threshold rather than fractionally below it.
- **Files modified:** `frontend/src/lib/flawChessVerdict.test.ts`
- **Verification:** `npx vitest run src/lib/flawChessVerdict.test.ts` — all 10 tests pass.
- **Committed in:** `11f7e5d9` (part of the Task 2 GREEN commit, since the fixture fix was needed to reach GREEN)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test fixture bug, not an implementation bug)
**Impact on plan:** The classifier's implementation matches the plan's logic exactly; only the test's own numeric fixtures needed correcting against the real sigmoid math. No scope creep.

## Issues Encountered
None beyond the fixture correction documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `computeFlawChessVerdict`, `SHARP_DROP_THRESHOLD`, and the `FlawChessVerdictTier`/`FlawChessVerdictMove`/`FlawChessVerdictResult` types are ready for Plan 02's `FlawChessAgreementVerdict.tsx` component to consume for prose rendering + hoverable moves.
- No blockers. The module is chess-free, React-free, and passes `npx tsc -b` with zero errors.

---
*Phase: 157-flawchess-agreement-verdict-prose-hoverable-moves*
*Completed: 2026-07-07*

## Self-Check: PASSED

- FOUND: frontend/src/lib/flawChessVerdict.ts
- FOUND: frontend/src/lib/flawChessVerdict.test.ts
- FOUND: .planning/phases/157-flawchess-agreement-verdict-prose-hoverable-moves/157-01-SUMMARY.md
- FOUND: 4dec1578 (test commit)
- FOUND: 11f7e5d9 (feat commit)
- FOUND: f3ecc768 (docs commit)
