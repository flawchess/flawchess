---
phase: quick-261124-ply
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/index.css
  - frontend/src/lib/trainSideLayout.ts
  - frontend/src/lib/__tests__/trainSideLayout.test.ts
  - frontend/src/hooks/useIsDesktop.ts
  - frontend/src/components/train/blunder-check/BlunderCheckStage.tsx
  - frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx
  - frontend/src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx
  - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainMoveTreeList.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/TrainBotBubble.tsx
  - frontend/src/components/train/TrainTourOverlay.tsx
  - frontend/src/components/train/__tests__/TrainBotBubble.test.tsx
  - frontend/src/components/train/__tests__/TrainTourOverlay.test.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
  - frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx
  - frontend/src/components/import/__tests__/ImportBotBubble.test.tsx
  - CHANGELOG.md
autonomous: true
requirements: [quick-261124-ply]

estimate:
  tokens: 110000
  raw_tokens: 110000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Item 3: at 816x616 and 933x704 (landscape, 768px wide and up) blunder check and personalized puzzles show the side-column layout: board column left, height-fitted so it ends above the viewport bottom, bubble / solution / reveal in the right column, game info under the board"
    - "Item 3: below 768px wide, and in portrait below 1024px (616x816, 704x933), the stacked layout with the sticky pinned board is unchanged; at 1024px and up the desktop layout is unchanged (side column still 384px)"
    - "Item 3: the Tailwind trainside variant in index.css and useIsTrainSideLayout read the same media query (TRAIN_SIDE_LAYOUT_QUERY); a test that reads index.css fails if they drift"
    - "Item 3: in the 768-1023 landscape band the settings entry is the desktop nav header cog (nav-settings), so the phone-only progress-row cog stays hidden there with no new control"
    - "Item 1: below 640px every TrainBotBubble without a leading slot shows the persona avatar floated top-left INSIDE the bubble, no name row, no tail, the persona name as the aria-label of a role=group root, and the action row beside the avatar at the bottom right; from 640px up and for the leading (countdown ring) variant the layout is unchanged"
    - "Item 2: Hilda's tour panel on the board shows her avatar floated inside the panel with the step counter in the top-right corner, role=group named after the persona, still pointer-events-none, and the hidden-state corner badge is unchanged"
    - "Item 4: no phone height reserve is implemented; the SUMMARY names where one would go"
  artifacts:
    - path: "frontend/src/lib/trainSideLayout.ts"
      provides: "TRAIN_SIDE_LAYOUT_QUERY (the one media query string) and TRAIN_SIDE_COLUMN_WIDTH_CLASS"
    - path: "frontend/src/index.css"
      provides: "@custom-variant trainside (block form wrapping @media TRAIN_SIDE_LAYOUT_QUERY)"
    - path: "frontend/src/hooks/useIsDesktop.ts"
      provides: "useIsTrainSideLayout, built on TRAIN_SIDE_LAYOUT_QUERY; useIsDesktop and useIsSmUp unchanged"
    - path: "frontend/src/lib/__tests__/trainSideLayout.test.ts"
      provides: "CSS/JS sync test plus the hook's matchMedia contract"
    - path: "frontend/src/components/train/blunder-check/BlunderCheckStage.tsx"
      provides: "blunder-check side layout and height fit keyed on the side-layout gate"
    - path: "frontend/src/components/train/TrainSolveScreen.tsx"
      provides: "personalized-puzzle side layout and height fit keyed on the side-layout gate"
    - path: "frontend/src/components/train/TrainBotBubble.tsx"
      provides: "compact phone branch (floated avatar inside the bubble), mounted via useIsSmUp"
    - path: "frontend/src/components/train/TrainTourOverlay.tsx"
      provides: "compact tour panel with floated avatar"
  key_links:
    - from: "frontend/src/index.css"
      to: "frontend/src/lib/trainSideLayout.ts"
      via: "trainSideLayout.test.ts asserts index.css contains @media TRAIN_SIDE_LAYOUT_QUERY inside @custom-variant trainside"
    - from: "frontend/src/hooks/useIsDesktop.ts"
      to: "frontend/src/lib/trainSideLayout.ts"
      via: "useIsTrainSideLayout passes TRAIN_SIDE_LAYOUT_QUERY to matchMedia"
    - from: "frontend/src/components/train/blunder-check/BlunderCheckStage.tsx"
      to: "frontend/src/hooks/useIsDesktop.ts"
      via: "useIsTrainSideLayout drives useFitBoardToViewport enabled, the game-info slot and bubbleInSide"
    - from: "frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx"
      to: "frontend/src/components/train/blunder-check/BlunderCheckStage.tsx"
      via: "both read useIsTrainSideLayout, so underBoard (game info) and the side-column footer agree"
    - from: "frontend/src/components/train/TrainSolveScreen.tsx"
      to: "frontend/src/components/train/TrainReveal.tsx"
      via: "both read useIsTrainSideLayout (controlsRow / nextButton / showGameFooter vs the verdict card or strip)"
    - from: "frontend/src/components/train/TrainBotBubble.tsx"
      to: "frontend/src/hooks/useIsDesktop.ts"
      via: "useIsSmUp mounts exactly one of the phone or sm+ avatar placements"
---

<objective>
Make the two Train drills (blunder check, personalized puzzles) usable on a Galaxy Z Fold8 in every posture: a side-column layout with a height-fitted board on landscape tablets, and a shorter bot bubble (and tour panel) on phones.

Purpose: on the unfolded landscape screen (816x616, 933x704) the drills fall into the phone stack under the desktop nav header and the 600px board overflows the viewport, with the bubble below the fold. On the cover screen the bubble's avatar + name header row costs about 63px and pushes the Ready button behind the bottom tab bar.
Output: one Tailwind custom variant plus a matching JS hook built on one shared query constant, the drill layouts switched to that gate, a compact phone branch in TrainBotBubble and TrainTourOverlay, tests, and two CHANGELOG bullets.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/CLAUDE.md
@.planning/STATE.md
@frontend/src/hooks/useIsDesktop.ts
@frontend/src/components/train/blunder-check/BlunderCheckStage.tsx
@frontend/src/components/train/TrainBotBubble.tsx
@frontend/src/components/train/TrainTourOverlay.tsx
</context>

<verified_facts>
Checked against the code at planning time (HEAD 209b3cc4f):

- Shell: `NavHeader` (App.tsx ~266) is `hidden sm:block` and renders the settings cog `nav-settings`; `playActive` (Train solve loop) suppresses only the phone `MobileHeader`. So from 640px up, including the new 768-1023 landscape band, settings is reachable from the nav header, and the progress-row cogs (`btn-blunder-check-settings`, `btn-train-settings`, both `sm:hidden`) correctly stay hidden. No settings change is needed.
- Immersive Train page wrapper: `px-4 py-6 md:px-6` (Train.tsx `trainPageClass`), no subnav. At 816px the content width is 768px, at 933px it is 885px.
- Fit math for the band (nav header about 49px, pt 24px, progress row about 22px, two 12px gaps, game-info slot 20px blunder / 44px puzzles, 40px gutter): fitted column about 437px (blunder) / 413px (puzzles) at 816x616 and about 525px / 501px at 933x704. With the 384px desktop side column plus the 32px gap the row overflows by up to 86px; with a 320px band cap it fits or overflows by at most about 21px (blunder at 816x616), which flex-shrink absorbs (both items shrink; ChessBoard sizes from its container width via `computeBoardSize`).
- Tailwind 4.3, compiled through Lightning CSS: `@media (max-height: 559.98px)` builds as `@media (height<=559.98px)`, class selectors escape as `.lg\:flex-row`. `@custom-variant` variants are registered after the built-in breakpoints, so their utilities are emitted AFTER `lg:` utilities: a `trainside:` utility on the same property as an `lg:` utility would win on desktop. Hence the band-only width uses disjoint conditions (`lg:` vs `trainside:max-lg:`).
- The parenthesised `@custom-variant name (...)` shorthand splits its argument on top-level commas (that is how selector lists like `(&:hover, &:focus)` work), so a comma-separated media query list must use the block form with `@slot`.
- Tests: jsdom has no `matchMedia` and `src/vitest.setup.ts` installs none, so `useMinWidth` returns false there (phone branch) in TrainStartScreen.test, EndgameInsightsBlock.test, ImportBotBubble.test and TrainBotBubble.test. TrainSolveScreen.test's stub answers `(min-width: 640px)` with `smUpMatches` (default true) and every other query with `matchMediaMatches`; TrainReveal.test answers every query with `matchMediaMatches`; Train.solveLoop / Train.blunderCheckToday / Train.subnav stubs match only the sm query. All of them keep working with a new query. BlunderCheckSolution.test (line 48) and BlunderCheckTab.test (line 194) mock `@/hooks/useIsDesktop` wholesale with a factory (no importOriginal): a new export used by the drills must be added to both factories, and any non-hook constant must NOT live in that module (vitest throws on a missing export of a factory mock), which is why the shared constants go in `frontend/src/lib/trainSideLayout.ts`.
- The only source reference to the bubble's name-span testid is TrainBotBubble.tsx itself; the six test assertions that read it in jsdom-without-matchMedia files are listed in Task 3. TrainSolveScreen.test's name assertions run with `smUpMatches = true` (sm+ branch) and keep passing.
- TrainTourOverlay's column today holds the avatar and the "1 / 2" step counter; there is no name label in it.
- Remaining `useIsDesktop` consumer after this plan: TrainFlawFixedBanner (thumb size only, not part of the layout split; left on the lg gate on purpose).
- Prerender (`src/prerender.tsx`) renders only Home and Privacy, neither mounts TrainBotBubble, so a JS-gated branch has no SSR hydration concern.
</verified_facts>

<tasks>

<task type="tracer">
  <name>Task 1 (tracer): side-layout gate end to end on blunder check (CSS variant, shared query constant, JS hook, BlunderCheckStage and BlunderCheckSolution)</name>
  <files>frontend/src/index.css, frontend/src/lib/trainSideLayout.ts, frontend/src/lib/__tests__/trainSideLayout.test.ts, frontend/src/hooks/useIsDesktop.ts, frontend/src/components/train/blunder-check/BlunderCheckStage.tsx, frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx, frontend/src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx, frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx</files>
  <read_first>frontend/src/index.css lines 1-37 (the short / deskshort variants and their comment style); frontend/src/hooks/useIsDesktop.ts (whole, 50 lines); frontend/src/components/train/blunder-check/BlunderCheckStage.tsx (whole, 217 lines); frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx lines 270-410; frontend/src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx lines 40-50 and 210-220; frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx line 194; frontend/src/__tests__/pushServiceWorker.test.ts lines 15-21 (readFileSync plus fileURLToPath pattern)</read_first>
  <behavior>
    trainSideLayout.test.ts (jsdom pragma):
    - index.css contains the trainside custom-variant block AND the substring "@media " + TRAIN_SIDE_LAYOUT_QUERY + " {" (fails the moment CSS and TS drift)
    - TRAIN_SIDE_LAYOUT_QUERY equals exactly "(min-width: 1024px), (min-width: 768px) and (orientation: landscape)" (pins the user-approved breakpoints)
    - with a window.matchMedia stub that matches only TRAIN_SIDE_LAYOUT_QUERY, renderHook(useIsTrainSideLayout) returns true and the stub received that exact string; with a stub that matches nothing it returns false; the original matchMedia is restored afterwards
    BlunderCheckSolution.test.tsx:
    - the module mock pins the lg hook to false and drives the new side-layout hook from viewport.desktop, so the existing desktop-path tests (verdict card, side-column footer, game info under the board) pass only when BlunderCheckStage and BlunderCheckSolution key on the side-layout gate; the phone-path tests (viewport.desktop = false) pass unedited
  </behavior>
  <action>
    Per requested change 3 (landscape tablets), blunder-check half. Do NOT change the `useIsDesktop` hook itself (other callers).

    1. Create `frontend/src/lib/trainSideLayout.ts`. Module-private constants: the desktop breakpoint 1024 (Tailwind lg) and the landscape-band floor 768 (Tailwind md), each named and commented. Export `TRAIN_SIDE_LAYOUT_QUERY`, a template string built from those two constants that resolves to exactly "(min-width: 1024px), (min-width: 768px) and (orientation: landscape)". Export `TRAIN_SIDE_COLUMN_WIDTH_CLASS = 'lg:max-w-sm trainside:max-lg:max-w-xs'`: desktop keeps its 384px side column, the 768-1023 landscape band caps it at 320px so the height-fitted board column plus the 32px gap plus the side column fit the 768px / 885px content width at 816 / 933px wide (put the fit numbers from verified_facts in the doc comment). Comment that the two conditions are disjoint on purpose: custom-variant utilities are emitted after the built-in breakpoints, so pairing a plain trainside max-width with an lg one would let the band value override desktop. Module doc: what the side layout is (board column left, bot bubble / solution in a right column, board height-fitted), that index.css's trainside variant MUST read this exact query, and that trainSideLayout.test.ts enforces it. Keeping these constants out of `hooks/useIsDesktop.ts` is deliberate: two test files mock that module wholesale.

    2. `frontend/src/index.css`: after the deskshort variant add a commented `@custom-variant trainside` in the BLOCK form (an `@media` rule with the query text byte-identical to TRAIN_SIDE_LAYOUT_QUERY, wrapping `@slot;`), not the parenthesised shorthand, and say why in the comment (the shorthand splits on top-level commas). The comment names the Fold8 landscape viewports, says it MUST match TRAIN_SIDE_LAYOUT_QUERY in lib/trainSideLayout.ts, and that landscape means width greater than height.

    3. `frontend/src/hooks/useIsDesktop.ts`: generalise the private `useMinWidth` into a private `useMediaQuery(query: string): boolean` with the same body (SSR / missing-matchMedia guard, change listener) and make `useMinWidth` call it. Add exported `useIsTrainSideLayout(): boolean` returning `useMediaQuery(TRAIN_SIDE_LAYOUT_QUERY)`, with a doc comment: the JS twin of the `trainside:` CSS variant, so a drill's JS-mounted branches (height fit, side-column footer, verdict card vs strip) always agree with its CSS split. Update the stale module doc comment (it still names TrainSolveScreen / TrainReveal as lg-gate users; after this plan the lg gate's remaining Train user is TrainFlawFixedBanner).

    4. `frontend/src/components/train/blunder-check/BlunderCheckStage.tsx`: replace the lg hook with `useIsTrainSideLayout` (local name `isSideLayout`) everywhere it gates layout: `useFitBoardToViewport` `enabled`, the game-info slot, and `bubbleInSide`. Add a fix-site comment at the gate: Bug fix (Galaxy Z Fold8 landscape, 816x616 / 933x704): below 1024px the drill fell into the phone stack under the desktop nav header, the width-bound 600px board overflowed the viewport bottom and the bubble sat below the fold; the side column and the height fit now engage on the trainside gate (1024px and up, or 768px and up in landscape). Class changes, each keeping every other token: on the root, every lg-prefixed token becomes trainside-prefixed. On the board column, the phone `display: contents` becomes the BASE class (`contents`) overridden by `trainside:flex` plus trainside-prefixed versions of its w-full / flex-col / items-center / gap-3. On the pinned block, the phone sticky / top-0 / z-10 / bg-background become base classes, reset by `trainside:static trainside:z-auto trainside:bg-transparent` (base-plus-override, so only one custom variant exists and no complement query can drift). `BLUNDER_CHECK_SIDE_CLASS` becomes `flex w-full flex-col gap-4 trainside:mt-[34px] trainside:self-stretch` plus `TRAIN_SIDE_COLUMN_WIDTH_CLASS` (template string at module scope). Rewrite the docstrings and comments that say "from lg up" / "below lg" to name the side-layout gate. `BlunderCheckProgress`'s cog keeps `sm:hidden`; extend its comment with one sentence that from sm up, the landscape band included, the nav header's cog is the settings entry.

    5. `frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx`: replace the lg hook with `useIsTrainSideLayout` for every layout decision (`onDesktop`, the tablet in-flow `actionBar` condition, TrainVerdictCard vs TrainVerdictStrip, and the footer-in-side-column condition). It must use the same gate as BlunderCheckStage: the stage renders `underBoard` (the game info) only in the side layout and the solution drops the footer from the side column there, so a mismatch shows the game info twice or never. Update the comments that say desktop / tablets to say side layout / stacked layout.

    6. Test mocks: in BlunderCheckSolution.test.tsx change the factory to pin the lg hook to false, keep `useIsSmUp: () => true`, and add `useIsTrainSideLayout: () => viewport.desktop`, with a comment that the drill layout must key on the side-layout gate alone. In BlunderCheckTab.test.tsx add `useIsTrainSideLayout: () => true` to the factory.

    7. Write `frontend/src/lib/__tests__/trainSideLayout.test.ts` per the behavior block (read `src/index.css` with readFileSync and `fileURLToPath(new URL('../../index.css', import.meta.url))`; define the matchMedia stub with Object.defineProperty, writable and configurable).
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run trainSideLayout BlunderCheckSolution BlunderCheckTab</automated>
    <automated>npm --prefix frontend run build && grep -lF 'orientation:landscape' frontend/dist/assets/*.css && grep -lF 'trainside\:flex-row' frontend/dist/assets/*.css && grep -lF 'trainside\:max-lg\:max-w-xs' frontend/dist/assets/*.css</automated>
    <automated>grep -c '@custom-variant trainside' frontend/src/index.css</automated> [HEAD=0 EXPECT==1]
    <automated>cat frontend/src/components/train/blunder-check/BlunderCheckStage.tsx frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx | grep -c 'useIsTrainSideLayout'</automated> [HEAD=0 EXPECT>=4]
    <automated>cat frontend/src/components/train/blunder-check/BlunderCheckStage.tsx frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx | grep -cE '\buseIsDesktop\('</automated> [HEAD=2 EXPECT==0]
    <automated>grep -vE '^\s*(//|\*|/\*|\{/\*)' frontend/src/components/train/blunder-check/BlunderCheckStage.tsx | grep -cE '(^|[ "])(max-)?lg:'</automated> [HEAD=4 EXPECT==0]
    <automated>grep -c 'trainside:' frontend/src/components/train/blunder-check/BlunderCheckStage.tsx</automated> [HEAD=0 EXPECT>=4]
    Mutation check (record in SUMMARY): put the lg hook back in BlunderCheckStage and BlunderCheckSolution; the desktop-path BlunderCheckSolution tests fail. Change one character of the query in index.css; trainSideLayout.test fails.
  </verify>
  <done>The trainside variant compiles into the built CSS (media query and both compound utilities present), the hook and the CSS read one constant pinned by a test, blunder check's stage and solution switch layout on the side-layout gate, all listed tests pass, and the mutation checks fail as described.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: expand the side layout to personalized puzzles (TrainSolveScreen, TrainReveal, TrainMoveTreeList)</name>
  <files>frontend/src/components/train/TrainSolveScreen.tsx, frontend/src/components/train/TrainReveal.tsx, frontend/src/components/train/TrainMoveTreeList.tsx, frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx</files>
  <read_first>frontend/src/components/train/TrainSolveScreen.tsx lines 185-262 (layout constants and the width-bound comment), 725-745 (gates), 925-990 (useTrainTour input and useFitBoardToViewport), 1815-2071 (layout JSX); frontend/src/components/train/TrainReveal.tsx lines 195-205 and 340-370; frontend/src/components/train/TrainMoveTreeList.tsx lines 25-100; frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx lines 78-100 (matchMedia stub), 716-800 (renderScreen and beforeEach), 2133-2145 (game-info slot test), 3845-3862 (verdict-card reveal pattern); frontend/src/hooks/useTrainTour.ts lines 200-226 (what isDesktop gates)</read_first>
  <behavior>
    TrainSolveScreen.test.tsx, new test (own describe, flag reset in afterEach):
    - with a module-level `sideLayoutOnly` flag set, the matchMedia stub answers true ONLY for TRAIN_SIDE_LAYOUT_QUERY (sm query still via smUpMatches = true, the lg query and everything else false), modelling 816x616 where the lg gate is off: before the reveal `train-prompt-panel` and `train-game-info-slot` are present (side column and game-info slot); after a guess and a drop the reveal shows `train-verdict-card` and no `train-verdict-strip`
    - every existing TrainSolveScreen / TrainReveal test passes unedited (their stubs answer the new query with matchMediaMatches)
  </behavior>
  <action>
    Per requested change 3, personalized-puzzle half.

    1. `TrainSolveScreen.tsx`: import `useIsTrainSideLayout` (keep `useIsSmUp`) and `TRAIN_SIDE_COLUMN_WIDTH_CLASS`; replace the lg hook with `const isSideLayout = useIsTrainSideLayout()` and rename every use: the `useTrainTour` input (pass `isDesktop: isSideLayout`; the hook's field name stays; in the band the reveal shows the always-open card, so the tour must use the no-tap result copy and skip the phone scroll, which is what that field drives), `useFitBoardToViewport` `enabled`, the tablet in-flow `TrainRevealActionBar` condition, the game-info slot, `promptArea` placement, the `train-prompt-panel` side panel, the `controlsRow` and `nextButton` conditions, and `showGameFooter`. Fix-site comment at the gate, same wording as BlunderCheckStage's (Fold8 landscape bug). Apply the same class conversions as BlunderCheckStage: root lg tokens become trainside tokens; board column base `contents` plus `trainside:flex` and trainside versions of the rest; pinned block sticky / top-0 / z-10 / bg-background as base classes reset by `trainside:static trainside:z-auto trainside:bg-transparent`. `PROMPT_SIDE_CLASS` becomes `flex w-full flex-col items-center gap-4 trainside:mt-8` plus `TRAIN_SIDE_COLUMN_WIDTH_CLASS`. Rewrite the comments that describe the split by `lg` (the block around line 206, the root / column / pinned comments, "tablets (sm up to lg)" near the action bar) to name the side-layout gate. The progress-row cog keeps `sm:hidden` (nav header cog covers sm and up, see verified_facts).

    2. `TrainReveal.tsx`: replace the lg hook with `useIsTrainSideLayout` for the card-vs-strip choice; it must agree with TrainSolveScreen, which hands TrainReveal the side-column controls row and footer under the same gate. Root class becomes `flex w-full flex-col gap-4 trainside:mt-8 trainside:self-stretch` plus `TRAIN_SIDE_COLUMN_WIDTH_CLASS` (via cn); update its offset comment to say side layout.

    3. `TrainMoveTreeList.tsx`: switch both hook reads (the Stockfish row's compact flag and `StockfishRowPlaceholder`) to `useIsTrainSideLayout`. The placeholder exists because the side column's footer (Analyze / Next) sits below the list; in the band that footer is in the side column too, so without it Next jumps when the Stockfish row appears (the Phase 249 UAT bug), and the compact flag must match the placeholder's skeleton height. Update the placeholder's bug-fix comment to say side layout. Leave `TRAIN_MOVE_TREE_HEIGHT_CLASS` on its lg step on purpose: the band is height-constrained (616px / 704px tall), so it keeps the two-row list; add one sentence saying so to that constant's comment.

    4. `TrainSolveScreen.test.tsx`: import TRAIN_SIDE_LAYOUT_QUERY from `@/lib/trainSideLayout`; add the `sideLayoutOnly` flag to the module-scope stub (sm query keeps smUpMatches; when the flag is set, every other query matches only if it equals TRAIN_SIDE_LAYOUT_QUERY; otherwise matchMediaMatches as before); add the test from the behavior block using `renderScreen(makePuzzle())` and the guess-then-drop reveal pattern near line 3850.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run TrainSolveScreen TrainReveal Train.solveLoop BlunderCheckSolution</automated>
    <automated>cat frontend/src/components/train/TrainSolveScreen.tsx frontend/src/components/train/TrainReveal.tsx frontend/src/components/train/TrainMoveTreeList.tsx | grep -cE '\buseIsDesktop\('</automated> [HEAD=4 EXPECT==0]
    <automated>grep -vE '^\s*(//|\*|/\*|\{/\*)' frontend/src/components/train/TrainSolveScreen.tsx | grep -cE '(^|[ "])(max-)?lg:'</automated> [HEAD=4 EXPECT==0]
    <automated>grep -vE '^\s*(//|\*|/\*|\{/\*)' frontend/src/components/train/TrainReveal.tsx | grep -cE '(^|[ "])(max-)?lg:'</automated> [HEAD=1 EXPECT==0]
    <automated>grep -c 'useIsTrainSideLayout' frontend/src/components/train/TrainMoveTreeList.tsx</automated> [HEAD=0 EXPECT>=3] (import plus both reads; the tree height class keeps its lg step, see action)
    <automated>grep -c 'trainside:' frontend/src/components/train/TrainSolveScreen.tsx</automated> [HEAD=0 EXPECT>=4]
    Mutation check (record in SUMMARY): put the lg hook back in TrainSolveScreen; the new side-layout-only test fails.
  </verify>
  <done>Personalized puzzles use the side column and the height fit on the side-layout gate, TrainReveal and TrainMoveTreeList agree with it, the new band test passes and fails with the gate reverted, and every existing solve-screen, reveal and solve-loop test passes unedited.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: compact phone bot bubble and tour panel (floated avatar inside, no name row), plus changelog</name>
  <files>frontend/src/components/train/TrainBotBubble.tsx, frontend/src/components/train/TrainTourOverlay.tsx, frontend/src/components/train/__tests__/TrainBotBubble.test.tsx, frontend/src/components/train/__tests__/TrainTourOverlay.test.tsx, frontend/src/components/train/__tests__/TrainStartScreen.test.tsx, frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx, frontend/src/components/import/__tests__/ImportBotBubble.test.tsx, CHANGELOG.md</files>
  <read_first>frontend/src/components/train/TrainBotBubble.tsx (whole, 169 lines); frontend/src/components/train/TrainVerdictStrip.tsx lines 113-162 (TrainVerdictCard: float-left mr-3 avatar, role=group aria-label, the pattern to copy); frontend/src/components/train/TrainTourOverlay.tsx (whole, 125 lines); frontend/src/components/train/__tests__/TrainBotBubble.test.tsx lines 1-170; frontend/src/components/train/__tests__/TrainStartScreen.test.tsx lines 498-530; frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx lines 95-106; frontend/src/components/import/__tests__/ImportBotBubble.test.tsx lines 120-136; CHANGELOG.md lines 1-35 and the `### Changed` heading of `## [Unreleased]`</read_first>
  <behavior>
    TrainBotBubble.test.tsx (module-scope matchMedia stub: a settable smUp flag answers exactly "(min-width: 640px)", every other query is false so prefers-reduced-motion stays off and the pulse-class tests still hold; default smUp false, reset in afterEach):
    - phone: no visible name span; the root has role=group and aria-label equal to the persona name; train-bot-avatar sits inside the bubble box (the parent of train-bot-copy contains it) and carries float-left; no tail element (no rotate-45 node in the root); the actions row renders inside the bubble
    - phone, avatarSize large: the floated avatar carries size-12 (default carries size-10)
    - sm+ (smUp true): the visible name span's text is the persona name; the avatar is NOT inside the bubble box; the tail is present; the root has no role=group
    - leading on a phone: the leading node renders, no train-bot-avatar, the tail is present
    - the remaining existing tests (img vs emoji, actions, data-state / data-nudge, nudge re-key, stepper) pass
    TrainTourOverlay.test.tsx (new, jsdom, persona PERSONA_REGISTRY['wall-1800']):
    - stepCount 2, step 0: train-tour-overlay has role=group named after the persona, its className contains pointer-events-none, train-bot-avatar inside it carries float-left, train-tour-step-count reads "1 / 2", train-bot-walkthrough shows the copy
    - stepCount 1: no train-tour-step-count
    - hidden: btn-train-tour-reopen renders, a click calls onReopen once, no train-tour-overlay
    Caller tests (run without matchMedia, so the phone branch): the six persona-name assertions listed in the action read the bubble root's aria-label and pass
  </behavior>
  <action>
    Per requested changes 1 and 2.

    1. `TrainBotBubble.tsx`. A CSS-only single node is not clean: on phones the avatar must sit inside the bubble's border, from sm up in a column beside it whose width comes from the name (wider than the 80px avatar) and which sets the row's minimum height; absolute positioning on sm+ would lose both. So mount exactly one placement through `useIsSmUp` (from `@/hooks/useIsDesktop`), the convention the reveal action bar already uses; state that reason in a comment. Compute `compact = leading === undefined && !isSmUp`.
    - Sizes: the column avatar classes become prefix-free, since the column only mounts from sm up: default `size-20` with `text-3xl`, large `size-24` with `text-3xl` (sm+ visuals identical to today). Add a floated-avatar record keyed by `TrainBotAvatarSize`: default `size-10 text-xl` (two text-sm lines, 2 x 20px), large `size-12 text-2xl` (the 96/80 column ratio applied to 40px, about 48px, on the 4px grid). Doc comments on both; no bare numbers in logic.
    - Root: keep data-testid train-bot-bubble, data-state and data-nudge in every branch. Compact: `flex w-full` plus `role="group"` and `aria-label={persona.name}` (TrainVerdictCard pattern). Otherwise `flex w-full flex-row items-start gap-3` (what the sm+ breakpoint computed before, and the leading variant's classes unchanged).
    - Left slot: leading when given; the existing avatar + visible-name column (`flex shrink-0 flex-col items-center gap-1`, name span and its testid unchanged) when not compact; nothing when compact.
    - Bubble box: keep `key={nudgeNonce}` and all its classes; add `flow-root` when compact so it contains the float. Render the tail only when not compact, with the existing left-pointing classes; delete the phone up-pointing tail variant entirely. When compact, the first child of the bubble box is `TrainBotAvatar` with `float-left mr-3` plus the floated size class, then the copy div (a plain block, so its lines wrap around the avatar), then the action row exactly as today. Do NOT clear the float on the action row: it is a flex container, which establishes its own formatting context and is therefore laid out beside the float (narrowed) with `justify-end` putting Ready / actions at the bottom right next to the avatar; it drops below the avatar only when the copy is taller than the avatar or the buttons do not fit beside it. Say that in a comment.
    - Fix-site comment: Bug fix (Galaxy Z Fold8 cover screen): the phone header row (55px avatar plus name above the bubble, with an up-pointing tail) cost about 63px and pushed the blunder-check Ready button behind the bottom tab bar. Rewrite the module docstring and the props docs (`leading`, avatar size) for the two layouts.
    - Callers need no change: none reads the name span or the header row in source (TrainScoreScreen, BlunderCheckDrill, BlunderCheckBetterMove, TrainStartScreen, TrainSolveScreen, EndgameInsightsBubble, FeedbackAskBubble, ImportBotBubble, PersonaGrid); the leading (countdown ring) variant is unchanged on every breakpoint.

    2. `TrainTourOverlay.tsx` (visible state only; the hidden corner badge stays exactly as is). The panel keeps `pointer-events-none`, its absolute inset / z-10 / border / backdrop / padding and testid; add `role="group"` and `aria-label={persona.name}`; replace its `flex items-start gap-3` with `flow-root`. Children in this order: `TrainBotAvatar` with `float-left mr-3 size-10 text-xl` (40px, two text lines, same size as today); `TourStepCount` floated right with a small left margin (give it a className prop or bake the float in; it keeps its testid and still returns null for a one-step part), so the counter takes the top-right corner instead of a row; the copy paragraph as a plain `text-sm` block keeping testid train-bot-walkthrough. Note in the docstring that the old column held the avatar and the counter (there was no name label) and that the compact panel covers less of the board.

    3. Tests per the behavior block. Update TrainBotBubble.test.tsx's header comment (it currently says the file deliberately installs no matchMedia stub). In TrainStartScreen.test.tsx (the three assertions near lines 502, 516, 527), EndgameInsightsBlock.test.tsx (near line 105) and ImportBotBubble.test.tsx (near lines 128 and 134), replace the reads of the name span's textContent with `screen.getByTestId('train-bot-bubble').getAttribute('aria-label')`, keeping each expected value. Create TrainTourOverlay.test.tsx.

    4. CHANGELOG.md, `## [Unreleased]`, `### Changed`, two bullets in plain words, no em-dash: (a) "Train: on landscape tablets and unfolded foldables (768px wide and up), blunder check and personalized puzzles put the board and the bot's bubble side by side, with the board sized to fit the screen height." (b) "Bot speech bubbles on phones show the bot's avatar inside the bubble instead of a name row above it, so the bubble and its buttons take less height (Train, Bots, Endgames, Import, and Hilda's tour on the board)."
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run TrainBotBubble TrainTourOverlay TrainStartScreen EndgameInsightsBlock ImportBotBubble TrainSolveScreen BlunderCheckTab PersonaGrid</automated>
    <automated>grep -c 'useIsSmUp' frontend/src/components/train/TrainBotBubble.tsx</automated> [HEAD=0 EXPECT>=2]
    <automated>grep -vE '^\s*(//|\*|/\*|\{/\*)' frontend/src/components/train/TrainBotBubble.tsx | grep -c 'max-sm:'</automated> [HEAD=1 EXPECT==0]
    <automated>cat frontend/src/components/train/TrainBotBubble.tsx frontend/src/components/train/TrainTourOverlay.tsx | grep -c 'float-left'</automated> [HEAD=0 EXPECT>=2]
    <automated>cat frontend/src/components/train/TrainBotBubble.tsx frontend/src/components/train/TrainTourOverlay.tsx | grep -c 'role="group"'</automated> [HEAD=0 EXPECT>=2]
    Mutation check (record in SUMMARY): restore the phone header row in TrainBotBubble (always render the column); the phone tests in TrainBotBubble.test fail.
  </verify>
  <done>On phones every non-leading bubble shows a floated avatar inside the bubble with no name row and no tail, and the actions beside it; sm+ and the leading variant are unchanged; the tour panel floats Hilda's avatar with the counter top-right and stays pointer-events-none; all listed tests pass; CHANGELOG has both bullets.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| none new | presentational frontend change: no new input, request, storage or route |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ply-01 | Denial of service | drill layout on an unexpected viewport (phone landscape now matches the band) | low | mitigate | board column floors at 240px (`BOARD_MIN_WIDTH_PX` / `TRAIN_BOARD_MIN_WIDTH_PX`) and the page scrolls below that; listed as a browser check in the SUMMARY |
| T-ply-SC | Tampering | npm / pip installs | high | accept | no package is added or updated by this plan |
</threat_model>

<verification>
Full frontend checks once all three tasks are in (from the checkout root):

cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip

Plus: `grep -lF 'orientation:landscape' frontend/dist/assets/*.css` after that build prints the main CSS file. No Prettier (ESLint only); max-depth 4 is gated by lint. No browser checkpoint in this plan: the orchestrator runs the browser UAT afterwards.
</verification>

<success_criteria>
- The drills switch to the side column with a height-fitted board at 816x616 and 933x704 and keep their current layouts at under 768px wide, in portrait under 1024px, and at 1024px and up.
- One query constant feeds both the CSS variant and the JS hook, and a test fails when they differ.
- Phone bubbles and the tour panel lose the avatar header row (about 63px back on the cover screen), sm+ unchanged.
- lint, build, the full vitest run and knip pass.
</success_criteria>

<output>
Create `.planning/quick/261124-ply-foldable-layout-compact-phone-bot-bubble/261124-ply-SUMMARY.md` when done. Besides the standard sections it MUST contain:

1. Mutation checks run and their results (Tasks 1-3).
2. Viewports for the orchestrator's browser UAT (Chrome DevTools sizes, CSS px), each with what to look at:
   - Fold8 cover portrait, about 412 wide (DevTools preset; the real device loses more height to the browser toolbar and Android nav bar): compact bubble, blunder-check Ready button and the puzzle guess buttons above the bottom tab bar.
   - Inner portrait 616x816 (DPR 3): under 640px, so the phone branch (compact bubble, stacked drill).
   - Inner portrait 704x933 (DPR 2.625): sm, stacked layout with the in-flow action bar and the sm+ bubble column.
   - Inner landscape 816x616 and 933x704: side layout, board column ends above the bottom edge, bubble in the side column, Analyze / Next footer on the board's bottom edge, the side column (verdict card, chips, controls row, move list, engine lines) fits its 320px cap without horizontal overflow, settings via the nav header cog, Hilda's tour panel on the board.
   - Regressions: 1280x800 and 1024x768 (desktop, 384px side column), 375x667 phone, 768x1024 portrait tablet (stacked).
   - New consequence to judge: phone landscape (for example 844x390, or the Fold8 cover screen in landscape at about 915x412) now matches the band, so the drill uses the side layout with the board at its 240px floor and a little page scroll, where before it stacked with the board overflowing.
3. Phone height reserve (requested change 4, NOT implemented): below the side-layout gate the board is width-bound; the board column is `display: contents`, so `useFitBoardToViewport` (called with `enabled: isSideLayout` in BlunderCheckStage.tsx and TrainSolveScreen.tsx) cannot measure it there. A follow-up reserve would cap the stacked root's `max-w-[var(--train-col-max)]` in both files with a CSS `min()` of 100% and `100dvh` minus one named reserve constant (progress row, the bubble's minimum height, the 64px bottom tab bar `pb-16` plus the bottom safe area), or add a phone-only fixed `gutterPx` path to the hook that measures the pinned block instead of the column.
</output>
