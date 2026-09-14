---
phase: 260914-uer
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/__tests__/trainBotCopy.test.ts
  - frontend/src/components/train/TrainBotBubble.tsx
  - frontend/src/lib/animatedScroll.ts
  - frontend/src/lib/__tests__/animatedScroll.test.ts
  - frontend/src/hooks/useFitPaneToViewport.ts
  - frontend/src/hooks/__tests__/useFitPaneToViewport.test.ts
  - frontend/src/hooks/useTrainWalkthrough.ts
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
autonomous: true
requirements: [QUICK-01, QUICK-02, QUICK-03, QUICK-04]

estimate:
  tokens: 90000
  raw_tokens: 45000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "QUICK-01: the Train bot avatar renders 20% larger on phones (46px -> 55px) and is unchanged at sm+ (80px)."
    - "QUICK-02: intro stepper step 1 opens with 'Every puzzle starts with one question:'."
    - "QUICK-03: the walkthrough's scroll after the 'This is your feedback' step runs for an explicit, named duration constant (double the UA default), honouring prefers-reduced-motion."
    - "QUICK-04: during a reveal the feedback area scrolls inside its own container with a visible thin scrollbar on its right edge; the page/body itself no longer scrolls on /train, and the feedback never slides up behind the pinned board."
  artifacts:
    - frontend/src/lib/animatedScroll.ts
    - frontend/src/hooks/useFitPaneToViewport.ts
    - 'data-testid="train-feedback-pane" wrapper in TrainSolveScreen.tsx'
  key_links:
    - "useTrainWalkthrough's scroll effect scrolls the feedback pane ELEMENT, not window."
    - "TrainSolveScreen threads useFitPaneToViewport's paneRef into both the pane <div> and useTrainWalkthrough."
    - "TrainSolveScreen's max-statements headroom (98 of 100) is not breached."
---

<objective>
Four tweaks to the Phase 222 (SEED-166) Train bot onboarding tutorial:

1. Phone-only 20% bigger bot avatar.
2. Reword the intro "one question" line.
3. Halve the speed of the walkthrough's scroll-into-view animation.
4. Give the reveal feedback area (avatar + speech bubble + line cards) its own
   scroll container with a visible scrollbar, instead of scrolling the whole page
   behind the pinned board.

Purpose: the tutorial currently reads as a page that scrolls under the board with a
hairline full-height page scrollbar, and the scroll jump after the feedback step is
too fast to follow.
Output: two new leaf modules (a rAF scroll tween, a viewport-fit hook for a pane),
a bounded feedback pane in the Train solve screen, and the two copy/size constant bumps.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md

Observed working-tree facts this plan is authorized from (all verified at planning time):

- `frontend/src/lib/trainBotCopy.ts:133-137` — `INTRO_QUESTION.copy`, the string to reword.
  `:363` — walkthrough step 0, `'This is your feedback. One point for a correct call and up to two for the move.'`
  `:112` — `STEPPER_COPY_MAX_CHARS = 145`, the per-step phone copy budget (a test enforces it).
- `frontend/src/components/train/TrainBotBubble.tsx:30` —
  `const TRAIN_BOT_AVATAR_CLASS = 'size-[46px] sm:size-20';` (46px phone / 80px sm+),
  documented at `:18-29`. `:38` holds the separate `TRAIN_BOT_AVATAR_LARGE_CLASS = 'size-14 sm:size-24'`,
  used by exactly one non-tutorial caller (`TrainStartScreen.tsx:191`, the /train landing Tank).
- `frontend/src/hooks/useTrainWalkthrough.ts:141-158` — the ONLY scroll animation in the
  tutorial: entering walkthrough step 1 (`WALKTHROUGH_STEP_TAP_CARD`, i.e. the step right
  after "This is your feedback") runs
  `window.scrollBy({ top: delta, behavior: prefersReducedMotion() ? 'auto' : 'smooth' })`
  with `delta = cardTop - pinnedHeight - WALKTHROUGH_CARD_SCROLL_GAP_PX` (`:30`, = 12).
  **There is no duration constant today** — `behavior: 'smooth'` is UA-controlled
  (~300-400ms in Chrome for this ~400px delta) and not tunable. Phone-only (`isDesktop` returns early).
- `frontend/src/components/train/TrainSolveScreen.tsx` layout today:
  `:1597-1613` root (`flex-col` below `lg`, `lg:flex-row lg:items-start lg:justify-center lg:gap-8`);
  `:1614-1625` `columnRef` (desktop left column, `max-lg:contents`);
  `:1626-1633` the phone-pinned progress+board block (`max-lg:sticky max-lg:top-0`, `ref={pinnedRef}`,
  `data-testid="train-pinned-board"`); `:1760-1770` the `<TrainBotBubble>`;
  `:1787-1800` `{showResultRow && <TrainReveal ... />}` (defined at `:1173-1174`).
  Refs at `:866-869` (`screenRef`, `pinnedRef`); walkthrough hook call `:880-894`;
  `useFitBoardToViewport` call `:895-902` (`enabled: isDesktop` — the height fit is desktop-only).
  `TrainReveal`'s own root is `flex w-full flex-col gap-4 lg:mt-[46px] lg:max-w-sm` (`TrainReveal.tsx:1175-1179`).
- Nothing in the Train tree scrolls internally at page level: `App.tsx:741` renders
  `<main className="pb-16 sm:pb-0">` with no shell height lock (unlike the analysis route at
  `App.tsx:714-719`), so **the body scrolls** — that is the hairline full-height scrollbar.
  `App.tsx:447-448`: the mobile bottom bar is `fixed`, and `main`'s `pb-16` is what reserves its space.
- `frontend/src/index.css:249-274` defines `.thin-scrollbar` (8px thumb, translucent). There is
  **no** `scrollbar-hide` / `scrollbar-width: none` utility anywhere in the Train tree — the
  scrollbar is invisible today only because the scrolling element is the page.
- Complexity gates: `frontend/eslint.config.js:33-35` (`complexity` 15, `max-depth` 4,
  `max-statements` 100 at `error`); `:219-221` baselines `TrainSolveScreen.tsx` at complexity 68.
  Measured now: **`TrainSolveScreen` has 98 statements of the 100 allowed** — only 2 free.
- Existing test coupling: `TrainSolveScreen.test.tsx:2784-2808` asserts
  `scrollBy` was called with `{ top: 388, behavior: 'smooth' }`, mocking `train-pinned-board`
  and `train-line-box-your-move` rects. `lib/__tests__/trainBotCopy.test.ts:113-119` covers
  `introCopy(1, ...)`; `:156-161` enforces `STEPPER_COPY_MAX_CHARS` on every stepper step.
  **No test asserts the old "one question" sentence** (grep-confirmed), so QUICK-02 needs a new assertion.
- `ResizeObserver` is not in jsdom; every suite that renders `TrainSolveScreen` already stubs it
  (`TrainSolveScreen.test.tsx:43-54`, `Train.solveLoop.test.tsx:58-68`,
  `TrainSolveScreen.restoredGameArrow.test.tsx`), so a second RO consumer needs no new stubs.
</context>

<decisions>
Flagged for the developer — these are judgement calls the ask did not settle:

- **D-A (QUICK-03): no scroll-duration constant exists to bump.** The shipped animation is the
  browser's native `behavior: 'smooth'`, whose duration is UA-owned. "Double the duration" therefore
  requires replacing it with an explicit rAF tween. This plan introduces
  `WALKTHROUGH_CARD_SCROLL_DURATION_MS = 700` (~2x Chrome's native ~350ms for this delta) as the
  single knob, per "tweak constants over props". If it still reads wrong in UAT, change that one number.
- **D-B (QUICK-04): the pane is scoped to the reveal state only.** Before the reveal (intro stepper,
  guess prompt, grading) the page keeps today's behavior. This preserves the Phase 222 locked call
  "stepper bubbles never scroll internally" (`trainBotCopy.ts:100-112`, `TrainSolveScreen.tsx:180-184`)
  while giving the *feedback* exactly the container the ask describes.
- **D-C (QUICK-04, desktop): the bubble stays under the board on desktop.** On `lg+` the pane is the
  reveal (line-cards) column; the bot bubble keeps its Phase 222 D-07 slot under the board, inside the
  height-fitted left column, which is already viewport-bounded. Moving the desktop bubble into the same
  scroller would make the right column own the bubble in *every* state (including pre-reveal, where
  there is no right column) — a real desktop redesign, out of scope for a quick task. On phones the
  bubble DOES move into the pane, which is where the ask points.
- **D-D (QUICK-01): only the tutorial avatar size moves.** `TRAIN_BOT_AVATAR_LARGE_CLASS`
  (`TrainBotBubble.tsx:38`, the /train landing Tank) is deliberately untouched; it is not part of the
  tutorial. Say so in UAT if it should follow.
</decisions>

<tasks>

<task type="auto">
  <name>Task 1: Reword the intro question and grow the phone avatar 20%</name>
  <files>frontend/src/lib/trainBotCopy.ts, frontend/src/lib/__tests__/trainBotCopy.test.ts, frontend/src/components/train/TrainBotBubble.tsx</files>
  <action>
Two constant edits plus test coverage (QUICK-01, QUICK-02).

1. `trainBotCopy.ts:133-137` — rewrite `INTRO_QUESTION.copy` so the sentence opens with
   `Every puzzle starts with one question:` and keeps the existing tail
   `is there only one good move here, or several?` verbatim (the closing clause is asserted by
   three existing tests). Result is 84 characters, comfortably inside `STEPPER_COPY_MAX_CHARS` (145),
   so the budget test at `trainBotCopy.test.ts:156-161` stays green. Keep the two-part string
   concatenation style used by its neighbours. Do not touch the surrounding step constants.

2. `trainBotCopy.test.ts:113-119` — in the existing
   `'steps 1-2 are hosted by Hilda and define the guess vocabulary'` case, add one assertion that
   `introCopy(1, 'white', false).copy` contains the new opening clause. No test asserts the previous
   wording, so this assertion is what makes the reword regression-proof (revert the source line and
   this test must fail).

3. `TrainBotBubble.tsx:30` — bump the phone step of `TRAIN_BOT_AVATAR_CLASS` from `size-[46px]` to
   `size-[55px]` (46 x 1.2 = 55.2, rounded down to a whole pixel). Leave `sm:size-20` exactly as is:
   the ask is phone-only. Extend the docstring at `:26-28` with one sentence recording this quick task,
   the 20% factor and that the `sm+` step is deliberately frozen.

4. Do NOT modify `TRAIN_BOT_AVATAR_LARGE_CLASS` (`:38`) or `TrainStartScreen.tsx` (per D-D).

The emoji-fallback type sizes (`text-xl sm:text-3xl` at `TrainBotBubble.tsx:108`) stay unchanged —
real persona art is used in the tutorial, the emoji is a no-art backstop only.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/lib/__tests__/trainBotCopy.test.ts src/components/train/__tests__/TrainBotBubble.test.tsx</automated>
    <automated>cd frontend && test "$(grep -c 'Every puzzle starts with one question' src/lib/trainBotCopy.ts)" = 1 && test "$(grep -c "size-\[55px\] sm:size-20" src/components/train/TrainBotBubble.tsx)" = 1 && test "$(grep -c "size-14 sm:size-24" src/components/train/TrainBotBubble.tsx)" = 1</automated>
  </verify>
  <done>Intro step 1 opens with the new sentence and a test asserts it; the tutorial avatar is 55px on phones and still 80px at sm+; the landing-page `large` variant is byte-identical.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add the two leaf modules — a rAF scroll tween and a viewport-fit hook for a pane</name>
  <files>frontend/src/lib/animatedScroll.ts, frontend/src/lib/__tests__/animatedScroll.test.ts, frontend/src/hooks/useFitPaneToViewport.ts, frontend/src/hooks/__tests__/useFitPaneToViewport.test.ts</files>
  <behavior>
animatedScroll:
- Test 1: a non-positive duration (the reduced-motion path) sets `scrollTop` to `start + delta` in one write, with no rAF scheduled.
- Test 2: a positive duration walks `scrollTop` across successive rAF ticks and lands EXACTLY on `start + delta` on the final tick (no easing residue).
- Test 3: a zero delta is a no-op.

useFitPaneToViewport:
- Test 4: with a stubbed viewport and stubbed pane/body rects, the returned max height is `clientHeight - paneTopDoc - chromeBelow - gutterPx`.
- Test 5: the result never drops below `minPx`.
- Test 6: before the ref is attached (pane not mounted) the hook returns `null` (= "no cap yet").
  </behavior>
  <action>
Both modules are pure leaves — no Train knowledge, no wiring yet (Task 3 consumes them).

**`frontend/src/lib/animatedScroll.ts`** — export
`animateScrollTop(element: HTMLElement, deltaPx: number, durationMs: number): void`.
Explicit return type, no `any`, module docstring explaining WHY it exists: the browser's native
`behavior: 'smooth'` has no duration knob, and the Train walkthrough needs a tunable one (D-A).
Implementation notes:
- `deltaPx === 0` -> return immediately.
- `durationMs <= 0` -> single write `element.scrollTop = element.scrollTop + deltaPx`, return.
  Callers pass `0` for the reduced-motion path, so this module never reads a media query itself.
- Otherwise capture `start = element.scrollTop` and `t0 = performance.now()`, then a
  `requestAnimationFrame` loop with an ease-in-out cubic (or quadratic) on
  `progress = Math.min(1, (now - t0) / durationMs)`, writing `element.scrollTop` each tick and
  assigning the exact `start + deltaPx` when `progress === 1` so rounding never leaves the pane
  a pixel short. Guard `typeof requestAnimationFrame !== 'function'` by falling back to the
  single write (keeps the module safe under any test environment).
- Keep it under the function-size limits: one exported function plus one module-private easing
  helper, nesting depth <= 2.

**`frontend/src/hooks/useFitPaneToViewport.ts`** — a sibling of the existing
`useFitBoardToViewport.ts`; read that file first and mirror its conventions (module docstring
explaining the measurement, `useCallback` measure + `useLayoutEffect` with a `ResizeObserver` and a
`window` resize listener, document-relative arithmetic).

Shape:
```
export interface FitPaneToViewportOptions { gutterPx: number; minPx: number }
export interface FitPaneToViewport { paneRef: RefObject<HTMLDivElement | null>; maxHeightPx: number | null }
export function useFitPaneToViewport(options: FitPaneToViewportOptions): FitPaneToViewport
```
The hook OWNS the ref (`useRef<HTMLDivElement>(null)`) and returns it — that is deliberate: the one
consumer, `TrainSolveScreen`, has only 2 statements of `max-statements` headroom, so it must get
ref + measurement from a single statement.

Measurement (document this reasoning in the docstring, it is the load-bearing part):
```
const rect = pane.getBoundingClientRect();
const paneTop = rect.top + window.scrollY;                                  // document-relative => scroll-invariant
const chromeBelow = document.body.getBoundingClientRect().bottom - rect.bottom; // everything laid out below the pane
const available = document.documentElement.clientHeight - paneTop - chromeBelow - gutterPx;
setMaxHeightPx(Math.round(Math.max(minPx, available)));
```
- `chromeBelow` is MEASURED, not estimated, because the chrome under the pane differs by breakpoint
  (`main`'s `pb-16` reserving the fixed mobile bottom bar below `sm`, the page wrapper's `py-6`
  elsewhere) — the same lesson `useFitBoardToViewport`'s docstring records from the 191 UAT.
- `chromeBelow` is invariant under the cap: capping the pane moves `body`'s bottom and the pane's
  bottom by the same amount. Never use `documentElement.scrollHeight` here — it clamps to the
  viewport once the content fits, which would make the pane shrink by `gutterPx` on every pass.
- Initial state is `null` (no cap) so nothing is clipped before the first layout pass.
- Re-measure on `window` resize and via a `ResizeObserver` on `pane.parentElement ?? pane` (catches
  the board resizing above it). The loop converges: the computed value depends only on the pane's
  TOP, which its own height cannot move, so the second pass sets an identical number and React
  bails out of the re-render.

Tests: `animatedScroll.test.ts` drives a plain `{ scrollTop: 0 } as unknown as HTMLElement` with
`vi.stubGlobal('requestAnimationFrame', ...)` and a stubbed `performance.now` so frames are stepped
deterministically. `useFitPaneToViewport.test.ts` uses `renderHook` (see
`hooks/__tests__/useWinCelebrationHold.test.ts` for the local idiom), stubs `ResizeObserver` the way
`TrainSolveScreen.test.tsx:43-54` does, attaches the ref to a real div and stubs its
`getBoundingClientRect` plus `document.body`'s.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/lib/__tests__/animatedScroll.test.ts src/hooks/__tests__/useFitPaneToViewport.test.ts</automated>
    <automated>cd frontend && npm run build</automated>
  </verify>
  <done>Both modules exist with explicit types, pass their own unit tests, and neither imports anything from the Train tree.</done>
</task>

<task type="auto">
  <name>Task 3: Give the reveal feedback its own scroll pane and slow the walkthrough scroll</name>
  <files>frontend/src/components/train/TrainSolveScreen.tsx, frontend/src/hooks/useTrainWalkthrough.ts, frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx</files>
  <action>
Wire Task 2's modules in (QUICK-03, QUICK-04). Land this as ONE commit so no intermediate state
has a scroll call aimed at an element that no longer scrolls.

**A. `TrainSolveScreen.tsx` — the pane.**

1. Add two module-scope constants next to the existing board constants (`:145-172`), each with a
   docstring in the house style:
   - `TRAIN_FEEDBACK_PANE_GUTTER_PX = 8` — breathing room between the pane's bottom edge and the
     chrome below it (the chrome itself is measured, see the hook).
   - `TRAIN_FEEDBACK_PANE_MIN_HEIGHT_PX = 160` — floor; below it the page is allowed to scroll again
     rather than squeezing the feedback into a slot nobody can read. The phone-pinned board keeps its
     `max-lg:sticky` classes precisely so that fallback still behaves.
2. Replace the `pinnedRef` declaration at `:869` with the pane hook, and delete `ref={pinnedRef}` from
   the pinned block at `:1632` (KEEP `data-testid="train-pinned-board"` and the sticky classes — a
   test and the fallback both depend on them):
   `const feedbackPane = useFitPaneToViewport({ gutterPx: TRAIN_FEEDBACK_PANE_GUTTER_PX, minPx: TRAIN_FEEDBACK_PANE_MIN_HEIGHT_PX });`
   Place it just above the `useTrainWalkthrough` call so the ref is defined before it is passed.
3. Pass `paneRef: feedbackPane.paneRef` to `useTrainWalkthrough` in place of `pinnedRef` (see C).
4. Just above the `return`, next to `bubbleBody`/`bubblePersona` (`:1567-1592`), hoist the bubble into
   a single node so it can be rendered from either slot without duplicating markup:
   `const bubbleNode = bubbleBody === null ? null : <TrainBotBubble ... />;` carrying exactly the
   props the JSX at `:1760-1770` passes today.
5. In the left column, replace the `{bubbleBody !== null && (<TrainBotBubble .../>)}` block with
   `{(isDesktop || !showResultRow) && bubbleNode}` — the bubble stays under the board on desktop and
   in every pre-reveal state (D-B, D-C).
6. Replace `{showResultRow && (<TrainReveal ... />)}` at `:1787-1800` with the pane wrapper, keeping
   every existing `<TrainReveal>` prop untouched:
   ```
   {showResultRow && (
     <div
       ref={feedbackPane.paneRef}
       style={{ maxHeight: feedbackPane.maxHeightPx ?? undefined }}
       className="flex w-full min-w-0 flex-col gap-4 overflow-y-auto overflow-x-hidden thin-scrollbar p-1 lg:max-w-sm"
       data-testid="train-feedback-pane"
     >
       {!isDesktop && bubbleNode}
       <TrainReveal ... />
     </div>
   )}
   ```
   - `thin-scrollbar` (`index.css:254`) is what makes the scrollbar visible on the pane's right edge;
     no `scrollbar-hide`-style utility exists in this tree, so nothing has to be removed.
   - `p-1` keeps the walkthrough's `ring-2` spotlight rings off the clipped edges.
   - `lg:max-w-sm` moves the desktop column cap onto the wrapper (the inner `TrainReveal` keeps its own
     copy; it is now scoped to the wrapper and harmless).
   - `overflow-x-hidden` is explicit: a `overflow-y-auto` box computes `overflow-x` to `auto`, and the
     line stepper already owns its own horizontal scroller.
7. **Statement budget.** `TrainSolveScreen` is at 98 of 100. This task adds 2
   (`feedbackPane`, `bubbleNode`) and removes 1 (`pinnedRef`) = 99. Keep every other new expression
   INSIDE the JSX (the `isDesktop || !showResultRow` test above is deliberately inline, not a
   variable). Verify with
   `npx eslint --no-inline-config --rule 'max-statements: ["error", 1]' src/components/train/TrainSolveScreen.tsx`
   and read the reported count for `TrainSolveScreen`. If it lands above 100, the sanctioned reclaim is
   inlining the `walkthroughTarget` alias (`:894`) at its three JSX use sites — do NOT add an
   `eslint.config.js` baseline entry (`eslint.config.js:69-77`: the override region is a Phase 215
   snapshot, not an escape hatch).

**B. `useTrainWalkthrough.ts` — scroll the pane, on an explicit duration.**

8. Swap the `pinnedRef` input (`:51`, `:100`, `:150-155`) for `paneRef: RefObject<HTMLDivElement | null>`
   — "the bounded feedback pane; the walkthrough scrolls THIS, never the window". Update the interface
   docstring and the module docstring's "phone scroll-to-cards effect" sentence.
9. Add the duration constant beside `WALKTHROUGH_CARD_SCROLL_GAP_PX` (`:28-30`), documenting D-A:
   Phase 222 shipped the UA's native smooth scroll, whose duration is not tunable; this quick task
   asked for half the speed, so the scroll is now an explicit tween and this number is the knob.
   `const WALKTHROUGH_CARD_SCROLL_DURATION_MS = 700;`
10. Rewrite the effect body at `:147-158`:
    ```
    if (activeStep !== WALKTHROUGH_STEP_TAP_CARD || isDesktop) return;
    const card = screenRef.current?.querySelector('[data-testid^="train-line-box-"]');
    const pane = paneRef.current;
    if (!(card instanceof HTMLElement) || pane === null) return;
    const delta = card.getBoundingClientRect().top - pane.getBoundingClientRect().top - WALKTHROUGH_CARD_SCROLL_GAP_PX;
    if (delta <= 0) return;
    animateScrollTop(pane, delta, prefersReducedMotion() ? 0 : WALKTHROUGH_CARD_SCROLL_DURATION_MS);
    ```
    The delta now measures card-top against PANE-top (the pane starts below the board, so the old
    "subtract the pinned block's height" correction is gone with it). Deps become
    `[activeStep, isDesktop, screenRef, paneRef]`.

**C. Tests (`TrainSolveScreen.test.tsx`).**

11. Rewrite the scroll case at `:2784-2808`: `vi.mock('@/lib/animatedScroll', ...)` with an
    `animateScrollTop` spy, then mock `train-feedback-pane`'s rect as `{ top: 300, bottom: 480, height: 180 }`
    and the `train-line-box-your-move` rect as `{ top: 700 }`, and assert the spy was called once with
    `(paneElement, 388, 700)` — same 388 as today (700 - 300 - 12), now against the pane. Keep the
    comment arithmetic line updated. Drop the `vi.stubGlobal('scrollBy', ...)` plumbing.
12. Add a case: with a verdict on screen on a PHONE (`matchMediaMatches = false`), the
    `train-feedback-pane` exists and `within(pane).getByTestId('train-bot-bubble')` and
    `within(pane).getByTestId('train-reveal')` both resolve — and on DESKTOP
    (`matchMediaMatches = true`) `within(pane).queryByTestId('train-bot-bubble')` is null while the
    reveal is still inside. This is the regression that fails if the bubble slot logic is reverted.
13. Add a case asserting the pane element carries `thin-scrollbar` and `overflow-y-auto` in its
    `className` — cheap, but it is the only automated signal that the scrollbar was not styled away.

Run the whole Train surface, not just the edited file: `TrainSolveScreen.test.tsx`,
`TrainSolveScreen.restoredGameArrow.test.tsx`, `Train.solveLoop.test.tsx`, `TrainReveal.test.tsx`.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/components/train/__tests__/TrainSolveScreen.test.tsx src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx src/pages/__tests__/Train.solveLoop.test.tsx src/components/train/__tests__/TrainReveal.test.tsx</automated>
    <automated>cd frontend && npx eslint --no-inline-config --rule 'max-statements: ["error", 100]' src/components/train/TrainSolveScreen.tsx</automated>
    <automated>cd frontend && test "$(grep -c 'train-feedback-pane' src/components/train/TrainSolveScreen.tsx)" = 1 && test "$(grep -v '^ \*' src/hooks/useTrainWalkthrough.ts | grep -c 'animateScrollTop')" = 2</automated>
  </verify>
  <done>During a reveal the feedback renders inside `train-feedback-pane` with a measured max-height, a visible thin scrollbar and no page scroll; the walkthrough's step-1 scroll drives that pane through `animateScrollTop` at 700ms (0ms under reduced motion); `TrainSolveScreen` stays at or under 100 statements with no new eslint baseline.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | Frontend-only copy, CSS utility and layout change. No new input parsing, no network call, no storage, no dependency added. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260914uer-01 | Denial of Service (self-inflicted) | `useFitPaneToViewport` ResizeObserver | low | mitigate | The measured value depends only on the pane's TOP, which its own height cannot move, so the observer converges in one extra pass; the `minPx` floor bounds the worst case. Verified by the hook's unit tests. |
| T-260914uer-02 | Tampering | package manager installs | low | accept | No `npm install` in this plan; `package.json` is not modified, so the package-legitimacy gate does not apply. |
</threat_model>

<verification>
Full local gate before integrating (frontend-only, so the backend legs are skipped):

```
cd frontend
npm run lint
npm test -- --run
npm run build        # tsc -b — Task 2 adds exported interfaces consumed across modules
npm run knip         # Task 2's exports must be reachable from Task 3's imports
```

Never run prettier — this frontend has no Prettier, and `prettier --write` mass-reformats.
</verification>

<human_uat>
None of the four asks can be proven by a unit test. Drive these in the dev build
(`npm run dev` + `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` + backend), using
device emulation at 375x667 for the phone legs, and report each leg pass/fail:

1. **QUICK-01 avatar** — on a 375px-wide viewport, start a Train session as a first-time-tutorial
   user and confirm the bot avatar is visibly larger than before (46 -> 55px) and the bubble header
   row still reads as a compact header. Then at >=640px confirm it is unchanged (80px).
   Also decide whether the /train landing Tank (`large` variant, D-D) should follow.
2. **QUICK-02 copy** — intro step 2 of 5 reads "Every puzzle starts with one question: is there only
   one good move here, or several?" and still fits without the bubble scrolling.
3. **QUICK-03 scroll speed** — on a phone viewport, press Next on "This is your feedback" and judge
   the scroll. If it is still too fast (or now too slow), the single knob is
   `WALKTHROUGH_CARD_SCROLL_DURATION_MS` in `useTrainWalkthrough.ts`.
4. **QUICK-04 pane** — with a reveal open: (a) the feedback area has its OWN scrollbar on its right
   edge, visible as soon as the content overflows; (b) the page/body no longer scrolls (the hairline
   full-height scrollbar is gone); (c) the feedback never slides up behind the board; (d) the board,
   eval bar and action row are all still reachable without page scrolling; (e) repeat on desktop
   (>=1024px), where the reveal column scrolls internally and the bubble stays under the board (D-C);
   (f) check the awkward middle band (~700-1000px wide) too — the mobile stack is used up to 1024px
   but the nav header reappears at 640px, and the pane height is measured, not assumed.
5. **Reduced motion** — with OS "reduce motion" on, the step-1 scroll jumps instantly instead of tweening.

Resetting the tutorial between runs: the walkthrough re-arms whenever
`reveal_walkthrough_seen_at` / the intro stamp are null on the train settings row (dev DB).
</human_uat>

<success_criteria>
- All four asks land, each traceable to QUICK-01..04.
- `npm run lint`, `npm test -- --run`, `npm run build` and `npm run knip` are clean from `frontend/`.
- `TrainSolveScreen` stays within its 100-statement gate with no new `eslint.config.js` baseline entry.
- No backend file, no `package.json`, no Prettier run.
- The four decisions D-A..D-D are surfaced in the summary so the developer can overrule them.
</success_criteria>

<output>
Create `.planning/quick/260914-uer-puzzle-training-onboarding-tutorial-twea/260914-uer-SUMMARY.md` when done,
recording: the measured statement count after Task 3, the final value of
`WALKTHROUGH_CARD_SCROLL_DURATION_MS`, and the HUMAN-UAT legs still outstanding.
</output>
