---
phase: 233-train-puzzle-timing-telemetry
plan: 04
subsystem: ui
tags: [react, typescript, telemetry, engagement, hover, vitest]

requires:
  - phase: 233-train-puzzle-timing-telemetry
    provides: "plan 03 review flush transport (Next via recordReview, every non-Next exit via postReviewKeepalive) and takeReviewSnapshot"
provides:
  - "The closed D-14 engagement summary on every review flush: review_line_steps, review_explored, review_explore_moves, review_analyze_opened, review_walkthrough, review_cards_opened, review_cards_total"
  - "TrainLineStepper.onUserStep (goTo only), useTrainFreePlay onUserMove option, TrainReveal onLineUserStep / onCardEngage / onCardsTotalChange props"
  - "800 ms desktop hover-hold rule (D-11) with hidden-page cancellation, distinct-card counting (D-12)"
  - "Cap parity (TELEMETRY_LINE_STEPS_CAP, TELEMETRY_EXPLORE_MOVES_CAP, TELEMETRY_CARDS_CAP) locked to app/schemas/train.py"
affects: [233-05]

actuals:
  tokens: 11100
  tasks: 2
  commits: 2
plan_head_before: a3e273adc9efd46fa10c65ac5291dc6999caf342
plan_head_after: d14efec4770dbbb945fb0682056317a544f5d9ac

tech-stack:
  added: []
  patterns:
    - "Cumulative counters in one ref, snapshotted by the single takeReviewSnapshot so Analyze, Next and every non-Next flush (and the reveal-cache mirror) carry identical engagement values"
    - "Card identity stays client-side: cardKeys live only in the per-tab reveal cache, the body carries the distinct count"
    - "Child-effect-before-parent-effect ordering: the counters reset skips the very first key so a child's mount-time cards total survives"

key-files:
  created: []
  modified:
    - frontend/src/components/train/TrainLineStepper.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/hooks/useTrainFreePlay.ts
    - frontend/src/hooks/useTrainPuzzleTelemetry.ts
    - frontend/src/lib/trainTelemetry.ts
    - frontend/src/components/train/__tests__/TrainLineStepper.test.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/hooks/__tests__/useTrainFreePlay.test.ts
    - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
    - tests/schemas/test_train_telemetry_parity.py

key-decisions:
  - "Engagement counters are cumulative totals in countersRef; snapshotReviewForAnalyze sets analyzeOpened BEFORE taking the snapshot so the unmount flush after a plain Analyze click carries review_analyze_opened"
  - "The counters reset skips the first key (isFirstKey): TrainReveal's mount effect reports the cards total before the hook's own mount effect runs, and a first-mount reset would wipe it; seed merge unions cardKeys and takes the max total for the same reason"
  - "TrainReveal derives lineBoxes/showAlsoFine above the verdict === null early return (behavior-neutral) so the cards-total effect is a legal hook"
  - "Desktop hover/focus go through startHover/endHover helpers that do the spotlight call AND the telemetry hover-start/hover-end, mobile handlers stay undefined"

patterns-established:
  - "A telemetry callback that must not count effect-driven activity gets its own prop (onUserStep, onUserMove) instead of reusing onStepChange/onSpotlightChange"

requirements-completed: [D-11, D-12, D-13, D-14]

coverage:
  - id: C1
    description: "review_line_steps counts only user prev/next/token clicks (0 on mount, resetNonce bump, equal moves array), capped at 50"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLineStepper.test.tsx#onUserStep (Phase 233 D-14)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#counters: 60 line steps flush review_line_steps capped at 50"
        status: pass
    human_judgment: false
  - id: C2
    description: "review_explored / review_explore_moves count start, legal playMove and playLine only; never reset/goBack/goForward/goToRoot/goToNode or a rejected drop"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainFreePlay.test.ts#useTrainFreePlay — onUserMove counts only user-played moves (Phase 233 D-14)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#counters: 3 explore moves flush review_explored true and review_explore_moves 3"
        status: pass
    human_judgment: false
  - id: C3
    description: "review_analyze_opened rides the Analyze snapshot, the unmount keepalive flush after an Analyze click, the reveal-cache mirror and the restored reveal's later flushes"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#counters: Analyze then unmount sends the keepalive flush with review_analyze_opened and mirrors it"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#counters: the Analyze snapshot carries the counters and a restored hook continues them cumulatively"
        status: pass
    human_judgment: false
  - id: C4
    description: "review_walkthrough is sticky for the puzzle when the first-reveal walkthrough was active at any point; a stepper click and an active walkthrough reach the real Next flush"
    requirement: "D-13"
    verification:
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry: a stepper click and an active walkthrough reach the Next flush"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#counters: markWalkthroughActive makes review_walkthrough true for that puzzle only"
        status: pass
    human_judgment: false
  - id: C5
    description: "Cards: mobile tap and departed-board click count at once, a desktop hover counts only after 800 ms on a visible page, distinct count and max total capped at 10"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#cards: *"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#TrainReveal card engagement (Phase 233)"
        status: pass
    human_judgment: false
  - id: C6
    description: "Flush body is the closed 11-key D-14 set; caps are locked to the server by the parity test"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#closed set: a flush body has exactly the 11 D-14 keys"
        status: pass
      - kind: unit
        ref: "tests/schemas/test_train_telemetry_parity.py#test_telemetry_constant_matches_frontend"
        status: pass
    human_judgment: false
  - id: C7
    description: "The verdict null -> verdict -> null render of one TrainReveal instance raises no hook-order error after the derivation move above the early return"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#TrainReveal refactor: one instance renders verdict null, then a verdict, then null with no hook-order error"
        status: pass
    human_judgment: false
  - id: C8
    description: "Real hover feel on a desktop browser (800 ms threshold) and a real phone tap landing in drill_solves.telemetry"
    requirement: "D-11"
    verification: []
    human_judgment: true
    rationale: "jsdom has no real pointer dwell or touch; the threshold constant and counting rule are unit-tested, the in-browser feel is a dev-build check"

duration: 13min
completed: 2026-10-05
status: complete
---

# Phase 233 Plan 04: Review engagement counters Summary

**The closed D-14 engagement summary (line steps, exploration moves, Analyze, walkthrough, distinct cards opened and shown with an 800 ms desktop hover-hold rule) rides every review flush as capped cumulative counters, including the keepalive flush sent when the user leaves through Analyze.**

## Performance

- **Duration:** ~13 min
- **Completed:** 2026-10-05
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files:** 12 modified, 0 created

## Accomplishments

- Task 1 (tracer): `TrainLineStepper.onUserStep` fires from `goTo` only; `useTrainFreePlay` takes `onUserMove` (ref-held) and wraps `playMove` (fires only on a legal move) and `playLine` (one call per engine-line click). The hook keeps a cumulative `countersRef`, exposes `onLineUserStep`, `onExploreMove`, `markWalkthroughActive`, and `snapshotReviewForAnalyze` sets `analyzeOpened` before snapshotting. `buildReviewTelemetry(totals, counters, exit)` always emits the counter keys, clamped to the mirrored caps; the snapshot/`isUsableReviewSnapshot` accept the new optional fields. TrainSolveScreen wires `onUserMove`, a sticky walkthrough effect and `onLineUserStep`.
- Task 2: `onCardEngage` ('open' | 'hover-start' | 'hover-end') and `onCardsTotalChange` on TrainReveal; one hover timer in the hook armed for `REVIEW_CARD_HOVER_MIN_MS` (800), cleared on key change, unmount, a new hover, a different card, and the page turning hidden. `open` counts immediately. Distinct keys stay client-side (only the count is sent).
- TrainReveal derives `lineBoxes` / `showAlsoFine` above the `verdict === null` early return and adds the cards-total effect there; an explicit render test pins verdict null -> verdict -> null.
- Cap parity now covers all five mirrored constants.
- Full frontend suite green (308 files, 5145 tests); `npm run lint`, `npm run build`, `npm run knip`; backend `tests/schemas` (80), `ruff check`, `ruff format --check`, `ty check` green.

## Mutation proofs

- Stepper: moving `onUserStep?.()` into the `[index, line]` effect turned all three `onUserStep` stepper tests red (not called on mount/reset, once per click, current-token click); reverted.
- Hover threshold: replacing `REVIEW_CARD_HOVER_MIN_MS` with `0` in the hook failed "a hover shorter than 800 ms is not counted", "hover-start on A then B", and "a hover armed, then the page turning hidden"; reverted.
- Early-return move: placing the `onCardsTotalChange` effect below `if (verdict === null)` failed "TrainReveal refactor: one instance renders verdict null..." (plus one pre-existing TrainReveal test, which hits the same hook-order error via its own verdict-null render); reverted.
- First-key guard: removing `isFirstKey` failed "a total reported by a child mount effect ... survives"; reverted.

## Task Commits

1. **Task 1 (tracer): line steps, explore moves, Analyze and walkthrough reach the review flush** - `5fc0b6b5d` (feat)
2. **Task 2: cards opened and cards shown reach the review flush with the 800 ms hover rule** - `d14efec47` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Counters reset would wipe the child's mount-time cards total**
- **Found during:** Task 2 design (child effect order)
- **Issue:** React runs TrainReveal's mount effect (which reports the cards total) before the hook's own mount effect in TrainSolveScreen; resetting counters on the first key change erased it, and a restored reveal's seed overwrote it again.
- **Fix:** the reset skips the very first key (refs are pristine then anyway), and the seed merge unions `cardKeys` and takes the max `cardsTotal`. Covered by a child/parent effect-order test.
- **Files modified:** frontend/src/hooks/useTrainPuzzleTelemetry.ts, its test
- **Commit:** d14efec47

**2. [Rule 3 - Blocking] Existing plan 02/03 hook tests asserted the old flush body/snapshot shape**
- **Found during:** Task 1 and 2
- **Fix:** exact-equality expectations extended with a shared `ZERO_ENGAGEMENT` constant and the new snapshot fields; no behavior asserted away.
- **Files modified:** frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
- **Commit:** 5fc0b6b5d, d14efec47

**3. [Rule 3 - Blocking] react-hooks/globals lint error in a test helper**
- **Found during:** Task 2 lint
- **Fix:** captured the hook result through an effect instead of assigning an outer variable during render.
- **Commit:** d14efec47

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking). **Impact:** none on scope; all inside the plan's files.

## Known Stubs

None.

## Threat Flags

None beyond the plan's `<threat_model>`: only counts and booleans are sent (T-233-16), the client clamps to the mirrored caps and the parity test locks them (T-233-17).

## Accepted residuals

- Manual-only check still open (coverage C8): the 800 ms hover feel and a real phone tap on a dev build.
- Card identity is in the per-tab reveal cache only; the cache entry carries `cardKeys` (opaque testid strings), not content.

## Self-Check: PASSED

- All 12 modified files exist; commits `5fc0b6b5d` and `d14efec47` are ancestors of HEAD; `commits:` measured from the plan ledger (2).
- Acceptance greps: `onUserStep?.()` once in `goTo`; `onUserStep={onLineUserStep}` x2; `onUserMove: puzzleTelemetry.onExploreMove` and `puzzleTelemetry.markWalkthroughActive()` once each; `export const TELEMETRY_LINE_STEPS_CAP = 50;` and `REVIEW_CARD_HOVER_MIN_MS = 800` present and the hook passes the constant to `setTimeout`.
