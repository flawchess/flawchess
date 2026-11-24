---
phase: quick-261124-ply
plan: 01
subsystem: frontend/train
tags: [foldable, responsive, train, blunder-check, bot-bubble]
status: complete
requirements: [quick-261124-ply]
key-files:
  created:
    - frontend/src/lib/trainSideLayout.ts
    - frontend/src/lib/__tests__/trainSideLayout.test.ts
    - frontend/src/components/train/__tests__/TrainTourOverlay.test.tsx
  modified:
    - frontend/src/index.css
    - frontend/src/hooks/useIsDesktop.ts
    - frontend/src/components/train/blunder-check/BlunderCheckStage.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/TrainMoveTreeList.tsx
    - frontend/src/components/train/TrainBotBubble.tsx
    - frontend/src/components/train/TrainTourOverlay.tsx
    - CHANGELOG.md
decisions:
  - "One query constant (TRAIN_SIDE_LAYOUT_QUERY) feeds both the trainside CSS variant and useIsTrainSideLayout; a test reads index.css to fail on drift"
  - "Band width cap uses disjoint conditions (lg:max-w-sm vs trainside:max-lg:max-w-xs) because custom-variant utilities are emitted after built-in breakpoints"
  - "TrainBotBubble mounts exactly one avatar placement through useIsSmUp instead of CSS-hiding a second copy"
actuals:
  tokens: 0
  tasks: 3
  commits: 3
plan_head_before: 209b3cc4fd0f04681908915ac42356cba2ab4eac
plan_head_after: cb97d4cfd168d7b03b76824b42087654ce0a0190
---

# Phase quick-261124-ply Plan 01: Foldable layout and compact phone bot bubble Summary

Train drills (blunder check, personalized puzzles) now use the side-column layout with a height-fitted board from 768px wide in landscape (and 1024px up at any orientation), and phone bot bubbles and Hilda's tour panel float the avatar inside the bubble instead of spending a name-row header.

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (tracer) | a743e20bd | trainside CSS variant, TRAIN_SIDE_LAYOUT_QUERY, useIsTrainSideLayout, blunder check stage and solution on that gate |
| 2 | 0fe61df06 | personalized puzzles (TrainSolveScreen, TrainReveal, TrainMoveTreeList) on the same gate, new band test |
| 3 | cb97d4cfd | compact phone TrainBotBubble and TrainTourOverlay, caller test updates, CHANGELOG |

`actuals.tokens` was not measured with the chars/4 instrument and is left at 0 rather than invented.

## Verification

Run from `frontend/` after the last commit:

- `npm run lint`: clean
- `npm run build` (tsc -b + vite): passes; built CSS contains `@media (width>=1024px),(width>=768px) and (orientation:landscape)`, `trainside\:flex-row` and `trainside\:max-lg\:max-w-xs`
- `npm test -- --run`: 385 files; the one failure of the first full run (FeedbackAskBubble, see Deviations) was fixed and its file re-run green (9/9), everything else passed (6903 + the fixed one)
- `npm run knip`: no issues (two pre-existing configuration hints only)

## Mutation checks

1. Task 1: put `useIsDesktop` back in BlunderCheckStage and BlunderCheckSolution (sed of the hook name): 9 desktop-path BlunderCheckSolution tests failed. Changed `768px` to `760px` in the index.css variant: `trainSideLayout.test` failed (1 test). Both restored; 71/71 pass.
2. Task 2: put the lg hook back in TrainSolveScreen: the new side-layout-only test failed ("uses the side column, the game-info slot and the always-open verdict card"), 191 others passed. Restored.
3. Task 3: always render the avatar + name column (dropped the `!compact` guard) in TrainBotBubble: 5 TrainBotBubble tests failed (phone float / no name row / large size, plus the two img/emoji tests that rely on a single avatar). Restored.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Seventh caller test read the removed name span**
- **Found during:** full vitest run after Task 3
- **Issue:** `FeedbackAskBubble.test.tsx` asserted `getByText('Hilda the Hippo')`, which is the visible name span that no longer renders on the phone layout (jsdom has no matchMedia). The plan listed six such assertions and missed this one.
- **Fix:** read the bubble root's `aria-label` instead, same expected value.
- **Files modified:** `frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx`
- **Commit:** cb97d4cfd

**2. [Rule 3 - Blocking] CSS sync test could not use `import.meta.url`**
- **Issue:** under the jsdom pragma `import.meta.url` is not a file URL, so the planned `fileURLToPath(new URL(...))` threw, and a `?raw` import returned processed (empty) CSS.
- **Fix:** `readFileSync(resolve(process.cwd(), 'src/index.css'))` (vitest runs from the frontend root), with a comment.

**3. [Rule 3 - Blocking] First TrainBotBubble test asserted the visible name on the phone layout**
- The existing "renders the persona name and avatar" test now splits: avatar/copy stays generic, the visible name assertion moved into the new sm+ describe. The test file's matchMedia stub (default phone) replaced the "no stub" header comment as planned.

### Plan-check notes

- A regex rename in TrainSolveScreen briefly clobbered the `useTrainTour` input key (`isDesktop: isSideLayout`); caught by the existing tour test, fixed before the Task 2 commit.
- The Task 3 verify grep `grep -c 'role="group"'` over both files returns 1, not >=2: TrainBotBubble sets the role conditionally (`role={compact ? 'group' : undefined}`), so only the tour panel carries the literal. Behavior is covered by tests.

## Known Stubs

None.

## Threat Flags

None. Presentational change; T-ply-01 (phone landscape matches the band, board floors at 240px and the page scrolls) is listed below for the browser pass.

## Browser UAT list (for the orchestrator, Chrome DevTools CSS px)

- Fold8 cover portrait, about 412 wide: compact bubble (avatar floated inside, no name row, no tail), blunder-check Ready button and the puzzle guess buttons above the bottom tab bar. The real device loses more height to the browser toolbar and Android nav bar than the DevTools preset.
- Inner portrait 616x816 (DPR 3): under 640px, phone branch (compact bubble, stacked drill).
- Inner portrait 704x933 (DPR 2.625): sm, stacked layout with the in-flow action bar and the sm+ bubble column (avatar + name beside the bubble).
- Inner landscape 816x616 and 933x704: side layout; board column ends above the bottom edge, bubble in the side column, Analyze / Next footer on the board's bottom edge, side column (verdict card, chips, controls row, move list, engine lines) fits its 320px cap without horizontal overflow, settings via the nav header cog (`nav-settings`), Hilda's tour panel on the board (avatar floated, counter top-right).
- Regressions: 1280x800 and 1024x768 (desktop, 384px side column), 375x667 phone, 768x1024 portrait tablet (stacked).
- New consequence to judge (T-ply-01): phone landscape (844x390, or Fold8 cover landscape about 915x412) now matches the band, so the drill uses the side layout with the board at its 240px floor and a little page scroll, where before it stacked with the board overflowing.

## Phone height reserve (requested change 4, NOT implemented)

Below the side-layout gate the board is width-bound; the board column is `display: contents`, so `useFitBoardToViewport` (called with `enabled: isSideLayout` in `BlunderCheckStage.tsx` and `TrainSolveScreen.tsx`) cannot measure it there. A follow-up reserve would cap the stacked root's `max-w-[var(--train-col-max)]` in both files with a CSS `min()` of 100% and `100dvh` minus one named reserve constant (progress row, the bubble's minimum height, the 64px bottom tab bar `pb-16` plus the bottom safe area), or add a phone-only fixed `gutterPx` path to the hook that measures the pinned block instead of the column.

## Self-Check: PASSED

- Created files present: trainSideLayout.ts, trainSideLayout.test.ts, TrainTourOverlay.test.tsx
- Commits a743e20bd, 0fe61df06, cb97d4cfd are on `main`; `git rev-list --count` from the recorded base gives 3.

## Orchestrator browser UAT (2026-11-24, same-origin iframe, blunder check ready gate)

| Viewport | Layout | Board | Ready visible |
|---|---|---|---|
| 412x915/840/780/720/680 (cover) | stack, compact bubble (avatar 40px) | 390 | yes, bottom 540 vs tab bar >= 619 |
| 616x816 (inner portrait, DPR 3) | stack | 556 | yes (744 vs bar ~755), page scrolls 30px |
| 704x933 (inner portrait, DPR 2.625) | stack | 572 | yes, no scroll |
| 816x616 (inner landscape) | side column | 401 | yes, no scroll |
| 933x704 (inner landscape) | side column | 489 | yes, no scroll |
| 844x390 / 915x412 (phone landscape) | side column | 212 | yes, no scroll |
| 1280x800 (desktop regression) | side column | 572 | yes |

Change 4 (phone height reserve) not needed: the compact bubble alone keeps Ready ~80px above the tab bar at 680px tall.
Personalized puzzles not exercised live (dev session already done, archive empty); covered by the new 816x616 TrainSolveScreen test.
Full frontend suite re-run after the executor's last fix: 385 files, 6904 tests passed.

## Follow-up (user request after UAT): landscape band polish

- `useIsTrainSideBand` (side layout below lg, i.e. 768-1023px landscape): TrainBotBubble uses the compact floated avatar there too.
- ProtectedLayout hides NavHeader while a Train drill is active (playActive on /train) in the band; the drills' progress-row settings cog shows there (`trainside:max-lg:flex`); the immersive page top padding drops to pt-3.
- Band side column 320 -> 272px and row gap 32 -> 16px (TRAIN_SIDE_COLUMN_WIDTH_CLASS, TRAIN_SIDE_ROW_GAP_CLASS): the band is width-bound, so this is what grows the board.
- useFitBoardToViewport also observes document.body: chrome above the column (the header removed by the drill's effect) changed without resizing the column, leaving a stale fit.
- Browser: 816x616 board 401 -> 452, 933x704 489 -> 542, no scroll, no nav header; 1024x700 and 1280x800 unchanged (header shown, 384px column). Full suite 385 files / 6905 tests pass; band test mutation-checked.

## Follow-up 2 (user request): portrait bottom bar, phone landscape

- Stacked layout at every width (phones, portrait tablets, unfolded foldables) publishes the reveal controls to the fixed bottom bar; the in-flow tablet bar is gone (blunder check solution + puzzles). The board-controls bar no longer hides from `sm` up; `main` keeps pb-16 while one is published. Side effect: bot games at 640-799px now show their Resign bar (it was hidden there).
- Short side layout (`useIsTrainShortSide`: side layout and below 560px tall): 12px fit gutter, pb-2 page padding, progress row and game info move to the side column, the side column scrolls inside a board-tall frame with Analyze/Next sticky at its bottom. Blunder-check panel `mt-4` dropped while immersive.
- Browser matrix (blunder check ready gate + solution, puzzles prompt + reveal) at iPhone 16 393x852 / 852x393, Fold8 cover 412x915 / 915x412, inner 704x933 / 933x704 and 616x816 / 816x616: no hidden action button, no horizontal overflow. iPhone 16 landscape board 228 -> 341 (both drills), cover landscape 278 -> 360; Next on the board's bottom edge in landscape, in the bottom bar in portrait.
- Tests: PublishedRevealBar test stand-in for the shell bar; TrainSolveScreen stub made realistic (below sm is never side layout); new short-side test, mutation-checked. 385 files / 6906 tests pass; lint, build, knip clean.
- Not done: widening the side column in phone landscape (there is spare width at 852px); custom-variant cascade order between `trainside:max-lg:` and `trainside:short:` utilities is unverified, so the band width was left alone.

## Follow-up 3 (user request): portrait foldable header, type scale

- Phone type scale extends to portrait up to 767px (`index.css`); the desktop nav header keeps the desktop scale there.
- `PORTRAIT_FOLDABLE_QUERY` / `foldportrait:` variant / `useIsPortraitFoldable` (640-767px, portrait), sync-tested against index.css. Train drills hide the nav header there (as in the landscape band), show the progress-row cog, drop the top padding; TrainBotBubble is compact there.
- Browser at 704x933: drill and solution with no header, cog at top, 16px copy, board 572, Next in the bottom bar. 744x1133 behaves the same; 768x1024 portrait, landscape and desktop unchanged. 385 files / 6908 tests pass.
