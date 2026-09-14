---
phase: 260914-uer
plan: 01
subsystem: ui
tags: [react, typescript, train, scroll, viewport, tailwind]

# Dependency graph
requires: []
provides:
  - "animateScrollTop (frontend/src/lib/animatedScroll.ts): a tunable-duration rAF scroll tween, the explicit replacement for the browser's native untunable `behavior: 'smooth'`."
  - "useFitPaneToViewport (frontend/src/hooks/useFitPaneToViewport.ts): a viewport-fit hook (sibling of useFitBoardToViewport) that owns its own ref and returns a measured max-height for a scroll pane."
  - "train-feedback-pane: the Train reveal's own bounded scroll container, replacing whole-page scroll on /train during a reveal."
affects: []

# Actuals (#2632)
actuals:
  tokens: 10099
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "rAF scroll tween with an explicit, tunable duration constant (animatedScroll.ts) in place of native `behavior: 'smooth'`, whose timing is UA-owned."
    - "A viewport-fit hook that owns and returns its own ref (useFitPaneToViewport), so a statement-budget-constrained consumer gets ref + measurement from one call site — destructure the hook's return immediately into separate bindings rather than keeping a property-access chain, or eslint's react-hooks/refs rule flags later non-ref property reads on the same object as 'accessing a ref during render'."

key-files:
  created:
    - frontend/src/lib/animatedScroll.ts
    - frontend/src/lib/__tests__/animatedScroll.test.ts
    - frontend/src/hooks/useFitPaneToViewport.ts
    - frontend/src/hooks/__tests__/useFitPaneToViewport.test.ts
  modified:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/components/train/TrainBotBubble.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/hooks/useTrainWalkthrough.ts

key-decisions:
  - "D-A (QUICK-03): no scroll-duration constant existed to bump — the shipped animation was the browser's native `behavior: 'smooth'` (UA-owned duration). Replaced with an explicit rAF tween; WALKTHROUGH_CARD_SCROLL_DURATION_MS = 700 (~2x Chrome's native ~350ms for this delta) is the single knob."
  - "D-B (QUICK-04): the feedback pane is scoped to the reveal state only — the intro stepper, guess prompt, and grading keep today's page-scroll behavior, preserving the Phase 222 locked call that stepper bubbles never scroll internally."
  - "D-C (QUICK-04, desktop): the bot bubble stays under the board on desktop (its Phase 222 D-07 slot, inside the height-fitted left column). On phones the bubble moves into the feedback pane during a reveal."
  - "D-D (QUICK-01): only the tutorial avatar (TRAIN_BOT_AVATAR_CLASS) grew 20% on phones. TRAIN_BOT_AVATAR_LARGE_CLASS (the /train landing Tank) is deliberately untouched — flag in UAT if it should follow."
  - "eslint's react-hooks/refs rule (react-compiler-based) flags ANY later property access on an object returned from a hook once that object also carries a ref field, even for a sibling non-ref value — not just direct ref.current reads. Fixed by destructuring useFitPaneToViewport's return into separate bindings (feedbackPaneRef, feedbackPaneMaxHeightPx) at the call site, matching the existing useBoardStageSize precedent, instead of keeping feedbackPane.paneRef / feedbackPane.maxHeightPx as property-access chains."

patterns-established:
  - "Pattern 1: destructure a hook's {ref, value} return immediately at the call site rather than passing the whole object around — sidesteps a react-hooks/refs false positive and matches useBoardStageSize's existing convention."

requirements-completed: [QUICK-01, QUICK-02, QUICK-03, QUICK-04]

coverage:
  - id: D1
    description: "QUICK-01: the tutorial bot avatar renders 20% larger on phones (46px -> 55px, size-[55px]) and is unchanged at sm+ (80px, size-20); the /train landing 'large' variant (size-14 sm:size-24) is byte-identical."
    requirement: "QUICK-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts, frontend/src/components/train/__tests__/TrainBotBubble.test.tsx — full suite"
        status: pass
      - kind: other
        ref: "grep assertions on TRAIN_BOT_AVATAR_CLASS (size-[55px] sm:size-20) and TRAIN_BOT_AVATAR_LARGE_CLASS (size-14 sm:size-24) in TrainBotBubble.tsx"
        status: pass
    human_judgment: true
    rationale: "Whether 55px 'reads' visibly larger on a real phone and the bubble header row still reads as compact is a visual judgment call the plan explicitly defers to human_uat (item 1) — a class-name assertion proves the CSS changed, not that it looks right."
  - id: D2
    description: "QUICK-02: intro stepper step 1 (Hilda) opens with 'Every puzzle starts with one question:' and keeps the existing 'is there only one good move here, or several?' tail verbatim (84 chars, inside the 145-char STEPPER_COPY_MAX_CHARS budget)."
    requirement: "QUICK-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#'steps 1-2 are hosted by Hilda and define the guess vocabulary' (new assertion added)"
        status: pass
    human_judgment: true
    rationale: "human_uat item 2 asks whether the reworded line 'still fits without the bubble scrolling' on a real phone viewport — a character-budget assertion is a proxy, not the actual rendered layout."
  - id: D3
    description: "QUICK-03: the walkthrough's step-1 scroll-into-view now runs via an explicit rAF tween (animateScrollTop) at WALKTHROUGH_CARD_SCROLL_DURATION_MS = 700ms (0ms under prefers-reduced-motion), replacing the untunable native `behavior: 'smooth'`."
    requirement: "QUICK-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/animatedScroll.test.ts — full suite (6 tests: no-op delta, single-step reduced-motion write, rAF-fallback, multi-tick walk landing exactly on start+delta, past-duration clamp)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#'on a phone, entering the tap step scrolls the feedback pane via animateScrollTop'"
        status: pass
    human_judgment: true
    rationale: "human_uat item 3 and item 5 (reduced motion) ask whether 700ms 'feels' right on a real phone and whether reduced-motion still jumps instantly — that is a subjective speed judgment the plan explicitly reserves for a human, with the single-knob constant named as the adjustment lever if it reads wrong."
  - id: D4
    description: "QUICK-04: during a reveal the feedback (bot bubble on phones + line cards) renders inside train-feedback-pane, a bounded overflow-y-auto container with a visible thin-scrollbar, measured by useFitPaneToViewport; the page/body no longer scrolls on /train during a reveal, and the pane never slides the feedback up behind the pinned board."
    requirement: "QUICK-04"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useFitPaneToViewport.test.ts — full suite (3 tests: measured max-height formula, minPx floor, null before mount)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#'on a phone the reveal feedback pane carries both the bubble and the reveal; on desktop it carries only the reveal (D-C)'"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#'the reveal feedback pane carries thin-scrollbar and overflow-y-auto so its scrollbar stays visible'"
        status: pass
    human_judgment: true
    rationale: "human_uat item 4 (legs a-f) asks for a real-device visual check of the pane's scrollbar visibility, the absence of page-level scroll, the board/eval-bar/action-row staying reachable, desktop's internal reveal-column scroll, and the awkward 700-1000px mid-band — none of that is observable from jsdom rect stubs, only that the measurement formula and the DOM structure are correct."

# Metrics
duration: ~40min (commits span 22:11-22:27 CEST; excludes pre-commit reading/setup time not separately timestamped)
completed: 2026-09-14
status: complete
---

# Phase 260914-uer Plan 01: Train Onboarding Tutorial Tweaks Summary

**Phone-only 20% bigger Train bot avatar, reworded intro line, a tunable 700ms rAF scroll tween replacing the untunable native smooth-scroll, and a bounded `train-feedback-pane` scroll container (measured by a new `useFitPaneToViewport` hook) so the reveal no longer scrolls the whole page behind the pinned board.**

## Performance

- **Duration:** ~40 min (commit span 22:11:31–22:27:20 CEST)
- **Started:** 2026-09-14T22:11:31+02:00 (first task commit; setup/reading preceded this)
- **Completed:** 2026-09-14T22:27:20+02:00
- **Tasks:** 3 / 3
- **Files modified:** 10 (4 created, 6 modified)

## Accomplishments

- QUICK-01: tutorial bot avatar is `size-[55px]` on phones (was `size-[46px]`, a 20% bump), unchanged at `sm+` (`size-20`, 80px). `TRAIN_BOT_AVATAR_LARGE_CLASS` (the `/train` landing Tank) is byte-identical.
- QUICK-02: `INTRO_QUESTION.copy` now reads "Every puzzle starts with one question: is there only one good move here, or several?" (84 chars, well under the 145-char stepper budget).
- QUICK-03: added `frontend/src/lib/animatedScroll.ts` (`animateScrollTop`), an explicit rAF tween with an ease-in-out cubic, used by `useTrainWalkthrough`'s step-1 scroll-to-cards effect at the new `WALKTHROUGH_CARD_SCROLL_DURATION_MS = 700` (0ms under reduced motion).
- QUICK-04: added `frontend/src/hooks/useFitPaneToViewport.ts` (sibling of `useFitBoardToViewport`) and wired it into `TrainSolveScreen.tsx` as `train-feedback-pane` — a bounded, `thin-scrollbar`-visible, `overflow-y-auto` container around the bot bubble (phones only, during a reveal) and `TrainReveal`. The page/body no longer scrolls on `/train` during a reveal; the desktop bubble keeps its Phase 222 slot under the board (D-C).
- `TrainSolveScreen` stays at 99 of 100 statements (feedback pane hook + hoisted `bubbleNode` added, `pinnedRef` removed) — no new `eslint.config.js` baseline entry.

## Task Commits

Each task was committed atomically:

1. **Task 1: Reword the intro question and grow the phone avatar 20%** - `0f33a5dd5` (feat)
2. **Task 2: Add the two leaf modules — a rAF scroll tween and a viewport-fit hook for a pane** - `062f661c3` (feat)
3. **Task 3: Give the reveal feedback its own scroll pane and slow the walkthrough scroll** - `e46d0133c` (feat)

**Plan metadata:** committed separately by the orchestrator (not by this executor).

## Files Created/Modified

- `frontend/src/lib/animatedScroll.ts` - `animateScrollTop(element, deltaPx, durationMs)`, the tunable rAF scroll tween.
- `frontend/src/lib/__tests__/animatedScroll.test.ts` - unit tests for the tween (no-op, single-step, multi-tick, rAF-fallback, past-duration clamp).
- `frontend/src/hooks/useFitPaneToViewport.ts` - viewport-fit hook for a scroll pane; owns its own ref.
- `frontend/src/hooks/__tests__/useFitPaneToViewport.test.ts` - unit tests via `renderHook` + a manually attached DOM node.
- `frontend/src/lib/trainBotCopy.ts` - reworded `INTRO_QUESTION.copy` (QUICK-02).
- `frontend/src/lib/__tests__/trainBotCopy.test.ts` - added an assertion on the new opening clause.
- `frontend/src/components/train/TrainBotBubble.tsx` - `TRAIN_BOT_AVATAR_CLASS` phone step 46px -> 55px (QUICK-01).
- `frontend/src/components/train/TrainSolveScreen.tsx` - `feedbackPane`/`bubbleNode` wiring, `train-feedback-pane` container, bubble-slot split (desktop/pre-reveal vs. phone-reveal).
- `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx` - rewrote the scroll-call assertion against `animateScrollTop`/the pane; added phone/desktop bubble-slot and scrollbar-class coverage.
- `frontend/src/hooks/useTrainWalkthrough.ts` - `pinnedRef` -> `paneRef`, `window.scrollBy` -> `animateScrollTop`, new `WALKTHROUGH_CARD_SCROLL_DURATION_MS`.

## Decisions Made

- D-A (QUICK-03): no scroll-duration constant existed to bump — native `behavior: 'smooth'` has UA-owned timing. Introduced `WALKTHROUGH_CARD_SCROLL_DURATION_MS = 700` (~2x Chrome's native ~350ms for this delta) as the single knob. **Overrule by editing this one constant if UAT says it's still wrong.**
- D-B (QUICK-04): the feedback pane only exists during the reveal. Pre-reveal states (intro stepper, guess prompt, grading) keep today's page-scroll behavior, per Phase 222's locked "stepper bubbles never scroll internally" call.
- D-C (QUICK-04, desktop): the bot bubble stays under the board on desktop in every state; it only moves into the feedback pane on phones during a reveal. Moving the desktop bubble too would be a real desktop redesign, out of scope for this quick task.
- D-D (QUICK-01): only the tutorial avatar moved. The `/train` landing page's `TRAIN_BOT_AVATAR_LARGE_CLASS` Tank is untouched — **flag in UAT if it should also grow.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] eslint `react-hooks/refs` false positive on `useFitPaneToViewport`'s return object**
- **Found during:** Task 3 (running the full `npm run lint` verification leg)
- **Issue:** `useFitPaneToViewport` returns `{ paneRef, maxHeightPx }`. Passing that whole object around and reading `feedbackPane.paneRef` (a ref) and later `feedbackPane.maxHeightPx` (a plain value, same object) tripped eslint's react-compiler-based `react-hooks/refs` rule — it flags ANY property access on an object once that object is known to also carry a ref field, not just direct `.current` reads. This is a real, active rule in `eslint.config.js` (confirmed with and without `--no-inline-config`), not a config quirk.
- **Fix:** Destructured the hook's return into separate bindings at the call site — `const { paneRef: feedbackPaneRef, maxHeightPx: feedbackPaneMaxHeightPx } = useFitPaneToViewport({...})` — and used those names everywhere instead of the property-access chain. Matches the existing `useBoardStageSize` consumer convention (`Analysis.tsx` also destructures immediately). Statement count unaffected (still one `const` declaration).
- **Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`
- **Verification:** `npx eslint src/components/train/TrainSolveScreen.tsx` clean; full `npm run lint` clean; `TrainSolveScreen` statement count unchanged at 99.
- **Committed in:** `e46d0133c` (Task 3 commit)

**2. [Rule 1 - Bug] `useFitPaneToViewport.test.ts`'s JSX harness violated the same `react-hooks` purity rule**
- **Found during:** Task 3 (running `npm run lint` over the whole tree, which caught what the earlier per-file Task 2 verify command — scoped only to the two new test files — had not)
- **Issue:** The original Task 2 test harness was a React component (`Harness`) that mutated a module-scope `latestResult` variable during render to expose the hook's result outside the render tree. eslint's `react-hooks/globals` rule flags reassigning an outer-scope variable during render as an impure side effect, and this rule applies to `.test.ts` files just like production code (no test-file override exists in `eslint.config.js`).
- **Fix:** Rewrote the test using `renderHook` (no JSX component under test, matching the codebase's `useWinCelebrationHold.test.ts` idiom) plus a manually created, detached `<div>` assigned directly to `result.current.paneRef.current` outside of render, then a `fireEvent(window, new Event('resize'))` to drive the hook's own resize listener. This exercises the same re-measurement path a real mount would, without a render-time side effect.
- **Files modified:** `frontend/src/hooks/__tests__/useFitPaneToViewport.test.ts`
- **Verification:** `npm test -- --run src/hooks/__tests__/useFitPaneToViewport.test.ts` (3/3 pass); full `npm run lint` clean.
- **Committed in:** `e46d0133c` (Task 3 commit, alongside the fix that surfaced it — this file was originally committed in Task 2's `062f661c3` and amended here)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — real eslint errors from the project's react-compiler-based `react-hooks` plugin, neither anticipated by the plan). **Impact on plan:** both fixes were required for `npm run lint` (part of the plan's own `<verification>` block) to pass; no scope creep — both are contained to the two files the plan already named for Task 2/3.

## Issues Encountered

None beyond the two deviations above (both surfaced and resolved during Task 3's full verification pass, since the plan's Task 2 verify command ran the two new test files but not the whole-tree `npm run lint`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All four QUICK-01..04 asks are implemented and covered by unit tests where automatable. **Every item in the plan's `<human_uat>` section is still outstanding** — none of it was run against a real dev build in this session:

1. QUICK-01 avatar — visually confirm 55px reads bigger on a 375px viewport without breaking the compact header row, confirm unchanged at 80px on `sm+`, and decide whether the `/train` landing Tank (`large` variant, D-D) should also grow.
2. QUICK-02 copy — confirm the reworded intro line renders without triggering bubble scrolling on a real phone.
3. QUICK-03 scroll speed — judge whether 700ms feels right after pressing Next on "This is your feedback"; the single knob (`WALKTHROUGH_CARD_SCROLL_DURATION_MS`) is ready to retune if not.
4. QUICK-04 pane — all six legs (a-f): visible scrollbar on the pane's right edge, no page-level scroll, feedback never sliding behind the board, board/eval-bar/action-row all reachable, desktop's internal reveal-column scroll with the bubble staying under the board, and the ~700-1000px mid-band.
5. Reduced motion — confirm the step-1 scroll jumps instantly (0ms) instead of tweening when OS "reduce motion" is on.

Resetting the tutorial between UAT runs: the walkthrough re-arms whenever `reveal_walkthrough_seen_at` / the intro stamp are null on the train settings row (dev DB).

---
*Phase: 260914-uer*
*Completed: 2026-09-14*
