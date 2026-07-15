---
phase: 169-clocked-board-game-loop-usebotgame
plan: 01
subsystem: frontend-lib
tags: [chess-clock, fischer-increment, wall-clock-timing, bot-pacing, vitest]

requires:
  - phase: 168.5-bot-move-pacing-search-budget-seed-096
    provides: "D-01..D-05 locked pacing model (fixed budget, synthetic clock debit, reveal delay, never-flag clamp) this module implements verbatim"
provides:
  - "chessClock.ts: pure timing/pacing primitives (increment, elapsed delta, pause anchor-shift, synthetic debit, D-05 reconciliation, reveal delay, low-time detection/formatting)"
  - "chessClock.test.ts: unit coverage for PLAY-03/04/05 + D-07 with zero DOM"
affects: [169-04-usebotgame-hook, 169-05-clockdisplay-component]

tech-stack:
  added: []
  patterns:
    - "Wall-clock Date.now()-delta timing, never setInterval tick accumulation (mirrors useFlawChessEngine.ts's debounce anchor idiom)"
    - "Pure/sync/React-free module extraction for unit-testability without mounting components (mirrors analysisUrl.ts precedent)"

key-files:
  created:
    - frontend/src/lib/chessClock.ts
    - frontend/src/lib/__tests__/chessClock.test.ts
  modified: []

key-decisions:
  - "Synthetic-debit/reveal-delay/never-flag constants set at Claude's-discretion defaults per CONTEXT.md: REVEAL_DELAY_MIN_MS=500, REVEAL_DELAY_MAX_MS=1500, SYNTHETIC_DEBIT_DIVISOR=20, SYNTHETIC_INCREMENT_SHARE=0.9, NEVER_FLAG_FLOOR_MS=1000, LOW_TIME_THRESHOLD_MS=10000"
  - "Added local unit-conversion constants (MS_PER_SECOND, SECONDS_PER_MINUTE, MS_PER_DECISECOND, DECISECONDS_PER_SECOND, DECISECONDS_PER_MINUTE, CLOCK_LABEL_PAD_WIDTH) inside formatClockLabel so its body stays free of bare numeric literals per CLAUDE.md's no-magic-numbers rule, beyond what the plan's acceptance-criteria grep explicitly checked for"

requirements-completed: []  # PLAY-03/04/05 are shared across Plans 01/04/05 (frontmatter); this plan delivers only the chessClock math primitives. Left [ ] Pending in REQUIREMENTS.md with a partial-delivery note — Plan 04 (useBotGame) actually closes them.

coverage:
  - id: D1
    description: "Fischer increment applied to the mover's remaining time (applyIncrementMs)"
    requirement: "PLAY-03"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts#applyIncrementMs (PLAY-03 Fischer increment)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Elapsed time computed from Date.now() deltas; hidden-tab pause shifts the turn anchor so zero time is charged"
    requirement: "PLAY-04"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts#computeElapsedMs (PLAY-04 wall-clock delta)"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts#visibility pause (PLAY-04)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Bot synthetic clock debit is the larger of real-elapsed and fraction-of-remaining, clamped so the bot never reaches zero"
    requirement: "PLAY-05"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts#computeSyntheticDebitMs (PLAY-05 168.5 D-02 formula)"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts#reconcileBotDebitMs (PLAY-05 D-05 never-flag reconciliation)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Below the low-time threshold the formatter emits tenths (0:09.4); plain m:ss above it"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/chessClock.test.ts#isLowTime / formatClockLabel (D-07 low-time tenths display)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-07-12
status: complete
---

# Phase 169 Plan 01: Clock and Bot-Pacing Math Module Summary

**Pure, React-free `chessClock.ts` module with eight unit-tested timing/pacing helpers (Fischer increment, wall-clock elapsed delta, hidden-tab pause anchor-shift, D-05 synthetic-debit reconciliation, reveal delay, low-time tenths formatting) that `useBotGame` and `ClockDisplay` will compose.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-12T19:07:46Z
- **Completed:** 2026-07-12T19:12:10Z
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments
- `chessClock.ts` exports `applyIncrementMs`, `computeElapsedMs`, `shiftAnchorForPause`, `computeSyntheticDebitMs`, `reconcileBotDebitMs`, `computeRevealDelayMs`, `isLowTime`, `formatClockLabel` plus six named pacing constants, all with explicit return types and zero magic numbers in function bodies.
- `reconcileBotDebitMs` implements the 168.5 D-05 never-flag guarantee by construction: `Math.min(Math.max(realElapsedMs, syntheticMs), botRemainingMs - NEVER_FLAG_FLOOR_MS)` is provably `< botRemainingMs` whenever `NEVER_FLAG_FLOOR_MS > 0`.
- `chessClock.test.ts` covers all four required behaviors (PLAY-03 increment, PLAY-04 wall-clock delta + visibility pause, PLAY-05 synthetic-debit + never-flag reconciliation, D-07 low-time tenths formatting) with 16 passing tests, no DOM/React mounted.

## Task Commits

1. **Task 1: Create chessClock.ts pure timing + pacing helpers** - `830f5790` (feat)
2. **Task 2: Unit-test chessClock — increment, wall-clock delta, visibility pause, D-05 reconciliation, low-time** - `1e16fb6f` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/lib/chessClock.ts` - eight pure timing/pacing helpers + six named constants (REVEAL_DELAY_MIN_MS/_MAX_MS, SYNTHETIC_DEBIT_DIVISOR, SYNTHETIC_INCREMENT_SHARE, NEVER_FLAG_FLOOR_MS, LOW_TIME_THRESHOLD_MS)
- `frontend/src/lib/__tests__/chessClock.test.ts` - 16 unit tests, zero DOM/React, covering all four required behaviors

## Decisions Made
- Constants set to the CONTEXT.md-suggested Claude's-discretion defaults verbatim (no deviation): `REVEAL_DELAY_MIN_MS=500`, `REVEAL_DELAY_MAX_MS=1500`, `SYNTHETIC_DEBIT_DIVISOR=20`, `SYNTHETIC_INCREMENT_SHARE=0.9`, `NEVER_FLAG_FLOOR_MS=1000`, `LOW_TIME_THRESHOLD_MS=10000`.
- Added five local unit-conversion constants (`MS_PER_SECOND`, `SECONDS_PER_MINUTE`, `MS_PER_DECISECOND`, `DECISECONDS_PER_SECOND`, `DECISECONDS_PER_MINUTE`) plus a padding-width constant inside `formatClockLabel` so no bare numeric literal appears in its body — the acceptance-criteria grep only checked for the three specific reconciliation/threshold patterns, but CLAUDE.md's no-magic-numbers rule is stricter, so the extra constants were added proactively (Rule 2-adjacent: not a correctness gap, but keeps the module CLAUDE.md-compliant end to end).

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<behavior>`/`<action>` specs verbatim; no bugs, missing functionality, or blockers encountered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`chessClock.ts` is complete and ready for Plan 04 (`useBotGame`) and Plan 05 (`ClockDisplay`) to import. Both downstream plans can compose these helpers directly — `useBotGame`'s bot-turn orchestration should follow RESEARCH.md Pattern 3 (`Promise.all([selectBotMove(...), setTimeout(resolve, computeRevealDelayMs(rng))])`, never sequential awaits) to avoid double-counting elapsed time against the D-05 reconciliation these helpers implement. No blockers for wave progression.

## Self-Check: PASSED

- `[ -f frontend/src/lib/chessClock.ts ]` → FOUND
- `[ -f frontend/src/lib/__tests__/chessClock.test.ts ]` → FOUND
- `git log --oneline --all | grep -E "830f5790|1e16fb6f"` → both commits FOUND
- Acceptance criteria re-verified: `cd frontend && npx tsc -b` → zero errors; `npx vitest run src/lib/__tests__/chessClock.test.ts` → 16/16 passed; `grep -nE '/ 20|< 10000|- 1000' frontend/src/lib/chessClock.ts` → no in-body magic-number matches; `reconcileBotDebitMs` clamp proven `< botRemainingMs` by the dedicated never-flag test.
- Plan-level verification re-run: `npx tsc -b` clean; `npx vitest run src/lib/__tests__/chessClock.test.ts` green; `npm run lint` clean for both new files (only pre-existing unrelated `coverage/` warnings).

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-12*
