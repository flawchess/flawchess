---
phase: 161-analysis-page-viewport-locked-responsive-layout-seed-088
plan: 01
subsystem: ui
tags: [react, tailwindcss-v4, css-grid, flexbox, react-chessboard, responsive-layout]

# Dependency graph
requires: []
provides:
  - "computeBoardSize() pure helper (BOARD_MIN_WIDTH=420 / BOARD_MAX_WIDTH=600) + unit tests"
  - "ChessBoard heightRef prop — opt-in height-aware sizing via the existing ResizeObserver"
  - "Tailwind v4 --breakpoint-desk3col (1200px) token + short (max-height:559.98px) custom variant"
  - "App.tsx analysis-route shell: locked-by-default 100dvh with two scoped unlock bands (tablet range, short-screen)"
  - "Analysis.tsx desktop tree: 100dvh-locked fluid 3-column CSS grid, height-aware board, Tags panel in right column"
affects: [any future /analysis layout work, any future Tailwind custom-breakpoint/custom-variant usage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tailwind v4 CSS-first custom breakpoint (@theme --breakpoint-*) and custom variant (@custom-variant) for non-default responsive thresholds"
    - "Height-aware component sizing via a caller-supplied heightRef observed by the same ResizeObserver as the width container (no second observer, no calc() of magic-number pixel constants)"
    - "Range-scoped Tailwind variant compounding (sm:max-desk3col:) to unlock a CSS lock only within a specific width band, avoiding custom-breakpoint-vs-named-breakpoint cascade-order pitfalls"

key-files:
  created:
    - frontend/src/components/board/boardSize.ts
    - frontend/src/components/board/__tests__/boardSize.test.ts
  modified:
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/index.css
    - frontend/src/App.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "desk3col breakpoint = 1200px; short variant = max-height:559.98px (both as specified in the plan's Claude's-discretion range)"
  - "Named @custom-variant form for `short` DOES compile against tailwindcss ^4.3.0 — but only WITHOUT the &:is() wrapper RESEARCH.md's Assumption A4 used; the exact syntax `@custom-variant short (@media (max-height: 559.98px));` (no &:is()) was required and is now verified via inspecting the compiled CSS"
  - "App.tsx shell polarity deviates from RESEARCH.md's simplified two-tier model (base=unlocked, desk3col:=locks): implemented a three-band model instead (base=locked always; sm:max-desk3col: unlocks only the existing 640-1199px tablet band; short: unlocks below 560px height at any width) because (a) a literal base=unlocked would also unlock true mobile since Tailwind's unprefixed classes apply below the first breakpoint too, breaking D-05, and (b) the custom `desk3col` breakpoint was empirically found to compile to an EARLIER media block than the built-in `sm:` breakpoint in this Tailwind v4.3.0 build, so a naive base-unlocked/desk3col-relocks scheme would lose the cascade to `sm:` at >=1200px width anyway"
  - "Human column (Open Question 1) DOES need its own scroll region: flawChessCard (~300-400px) + MaiaHumanPanel's h-64 chart + quality bar (~420px) sum to ~750-850px minimum, easily exceeding the board column's height budget at the 420px board-floor/short-screen case — added desk3col:overflow-y-auto"
  - "Board column also given desk3col:overflow-y-auto (a Rule 2 addition not spelled out verbatim in the plan's Task 3 action text) — required for D-09's core 'middle column scrolls internally once the board hits its floor' contract; RESEARCH.md's own Pattern 4 note ('the middle column's own internal overflow-y-auto becomes moot [under short:], not absent [otherwise]') implies this region needs the class in the first place"

requirements-completed: [SEED-088]

coverage:
  - id: D1
    description: "computeBoardSize() clamps board size to [420, 600] driven by min(width, height, maxWidth), with a zero-guard that preserves the mount-at-zero-size crash prevention (D-02/D-08)"
    requirement: "SEED-088"
    verification:
      - kind: unit
        ref: "frontend/src/components/board/__tests__/boardSize.test.ts (6 cases: width-driven, ceiling, height-driven, floor, both zero-guards)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ChessBoard gains an opt-in heightRef prop wired into the existing single ResizeObserver; every other caller (Openings miniboards, TrainSketch) is unaffected (heightBudget=Infinity when omitted)"
    requirement: "SEED-088"
    verification:
      - kind: unit
        ref: "npx tsc -b (backward-compatible optional prop, no existing caller breaks)"
        status: pass
      - kind: other
        ref: "grep -rn heightRef frontend/src (only ChessBoard.tsx defines/uses it; Analysis.tsx is the only consumer)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Tailwind v4 --breakpoint-desk3col (1200px) token and short (max-height:559.98px) custom variant compile cleanly"
    requirement: "SEED-088"
    verification:
      - kind: other
        ref: "npm run build (production build); grep -n breakpoint-desk3col frontend/src/index.css; inspected compiled dist CSS for a real @media (height<=559.98px){...} block (not an empty selector)"
        status: pass
    human_judgment: false
  - id: D4
    description: "AnalysisTagsPanel relocated to the bottom of the right column (after boardControls), removed from the board column, withHighlight=true preserved (D-04)"
    requirement: "SEED-088"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx > Analysis desktop layout (Phase 161, SEED-088) > renders AnalysisTagsPanel in the right column, after the engine card and move list (D-04)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Desktop grid row converts to a 1-D CSS grid grid-cols-[360px_1fr_360px]; max-w-7xl removed; all 6 lg: occurrences remapped to desk3col:; useIsMobile/MOBILE_BREAKPOINT_PX untouched (D-03/D-06/D-07)"
    requirement: "SEED-088"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx > Analysis desktop layout (Phase 161, SEED-088) > carries the desk3col 3-column grid-cols class on the grid row (D-03)"
        status: pass
      - kind: other
        ref: "grep -n 'desk3col:grid-cols-\\[360px_1fr_360px\\]' frontend/src/pages/Analysis.tsx; grep -n 'lg:' frontend/src/pages/Analysis.tsx (only a comment mentioning the removed class remains, no live lg: usage)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The 100dvh lock actually holds at real desktop viewport sizes (1280x800/1366x768), releases below ~560px height, hard-stacks below ~1200px width, board sizes correctly between 420-600px, and mobile/stacked-fallback trees are visually unchanged — real browser layout behavior"
    verification: []
    human_judgment: true
    rationale: "jsdom performs no real CSS layout (confirmed in 161-RESEARCH.md's Validation Architecture section); the 100dvh lock, breakpoint switching, and board height-aware sizing are structurally wired and unit-tested at the logic layer (D1-D5 above) but the actual rendered behavior across the 8 viewport scenarios in the plan's Task 3 human-check can only be confirmed in a real browser. Deferred to the orchestrator's UAT pass — see 'Pending HUMAN-UAT' below for the exact checklist."

# Metrics
duration: 40min
completed: 2026-07-09
status: complete
---

# Phase 161 Plan 01: Analysis page viewport-locked responsive layout Summary

**Locked the /analysis desktop frame to `100dvh` with a fluid `grid-cols-[360px_1fr_360px]` 3-column layout, a height-aware `ChessBoard` (`clamp(420, min(width,height), 600)`), and the Tags panel relocated to the right column — fixing the small-laptop eval-chart cutoff (SEED-088).**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-09T18:10:00Z
- **Tasks:** 3 (all `type="auto"`, no checkpoints)
- **Files modified:** 5 modified, 2 created

## Accomplishments
- Extracted `computeBoardSize()` (D-02/D-08: floor 420, ceiling 600, height-aware) into a standalone, unit-tested pure function; wired it into `ChessBoard.tsx` behind an opt-in `heightRef` prop so every other caller (Openings mini-boards, TrainSketch) is byte-for-byte unaffected.
- Added the `desk3col` (1200px) Tailwind breakpoint token and a `short` (max-height 559.98px) custom variant to `index.css` — discovered and fixed a real syntax bug in the process (see Deviations).
- Converted the `/analysis` desktop tree to a `100dvh`-locked, 1-D CSS grid (`grid-cols-[360px_1fr_360px]`), completed the `min-h-0` chain from the App shell down through both flanking columns, relocated `AnalysisTagsPanel` to the bottom of the right column (D-04), and made the board column and Human column each independently scrollable so overflow never reaches the page.
- Redesigned the App.tsx shell's lock/unlock polarity as a three-band model (mobile locked unchanged / tablet band unlocked unchanged / desktop locked new / short-screen unlocked new) after finding the plan's and RESEARCH.md's simpler two-tier polarity would have silently broken mobile and lost a cascade-order race against the built-in `sm:` breakpoint.

## Task Commits

Each task was committed atomically:

1. **Task 1: Height-aware board sizing** — `408312b4` (feat) — `computeBoardSize()` + unit tests + `ChessBoard.tsx` `heightRef` wiring.
2. **Task 2: Tailwind v4 tokens** — `7939980e` (feat) — `--breakpoint-desk3col` + `short` custom variant in `index.css`.
   - **Fix commit** — `a2703b2e` (fix) — corrected the `short` custom-variant syntax after discovering the plan's `&:is(@media (...))` form compiled to a broken, no-op selector.
3. **Task 3: Shell polarity + grid conversion + tags relocation + min-h-0 chain** — `72a286f1` (feat) — `App.tsx`, `Analysis.tsx`, `Analysis.test.tsx`.

**Plan metadata:** (this SUMMARY + STATE/ROADMAP updates — committed separately by the orchestrator, not this executor, per this plan's explicit instruction)

_No TDD RED/GREEN split was needed for Task 1's `tdd="true"` marker in practice — `computeBoardSize()` and its test were authored together and verified GREEN on first run (all 6 behavior cases passed immediately); no failing-first commit was created since the plan's `<behavior>` spec left no ambiguity to falsify against._

## Files Created/Modified
- `frontend/src/components/board/boardSize.ts` — `computeBoardSize()`, `BOARD_MIN_WIDTH`, `BOARD_MAX_WIDTH` (new)
- `frontend/src/components/board/__tests__/boardSize.test.ts` — 6 unit tests covering the clamp/zero-guard logic (new)
- `frontend/src/components/board/ChessBoard.tsx` — optional `heightRef` prop, extended (not duplicated) `ResizeObserver`
- `frontend/src/index.css` — `--breakpoint-desk3col: 1200px`, `@custom-variant short (@media (max-height: 559.98px));`
- `frontend/src/App.tsx` — `isAnalysisRoute` shell: locked-by-default + two scoped unlock bands
- `frontend/src/pages/Analysis.tsx` — desktop grid conversion, tags relocation, `min-h-0`/`overflow-y-auto` chain, `boardHeightRef`
- `frontend/src/pages/__tests__/Analysis.test.tsx` — game-mode fixture (`buildGame`/`libraryGameState`) + 2 new structural assertions; 2 jsdom-gap fixes (`scrollIntoView`, `useFlawFilterStore` default)

## Decisions Made

**Human-column scroll decision (RESEARCH.md Open Question 1):** the Human column (`flawChessCard` + `MaiaHumanPanel`) DOES need its own `overflow-y-auto`. Read `MaiaHumanPanel.tsx`/`MovesByRatingChart.tsx` during implementation: the chart alone defaults to `h-64` (256px), plus the `MaiaMoveQualityBar` below it, plus the `flawChessCard`'s header + `LINES_MIN_HEIGHT` engine lines + agreement verdict + temperature selector + ELO slider — combined content is ~750-850px minimum, which comfortably exceeds the board column's height budget once the board hits its 420px floor on a short screen. Added `desk3col:min-h-0 desk3col:overflow-y-auto` to the Human column div, mirroring `VariationTree`'s established self-scroll pattern.

**desk3col / short exact px:** `desk3col: 1200px` (per the plan's own math: `360 + 420 board floor + 50 eval bars + 360 ≈ 1190`, rounded up slightly, staying below 1280/1366 laptops). `short: 559.98px` max-height (the `.98` avoids an off-by-one at exactly 560px, matching the plan's stated convention).

**Named `@custom-variant` vs inline fallback:** the named form **does** compile against tailwindcss ^4.3.0, but the exact syntax matters. RESEARCH.md's Assumption A4 proposed `@custom-variant short (&:is(@media (max-height: 559.98px)));` (mirroring the `dark` variant's selector-based precedent at line 7) — this compiles WITHOUT ERROR but silently produces a broken, empty `:is()` selector with no media-query wrapping at all (verified by inspecting the built `dist/assets/*.css`: `.short\:block:is(){display:block}` — no `@media` anywhere). The `&:is()` wrapper is for SELECTOR-based custom variants (like `dark`, which wraps a class/attribute selector); AT-RULE-based variants (media features) omit it entirely: `@custom-variant short (@media (max-height: 559.98px));`. This is the form actually shipped; it correctly compiles to `@media (height<=559.98px){.short\:block{display:block}...}`.

**App.tsx polarity — three-band model, not the plan's literal two-tier example.** The plan's Task 3 action text gave an exact illustrative target (`h-auto block desk3col:flex desk3col:flex-col desk3col:h-[100dvh]`) copied verbatim from RESEARCH.md's Pattern 2. Implementing it literally would have:
1. Unlocked true mobile (<640px) — Tailwind's unprefixed/base classes apply below the FIRST breakpoint too, not just "everything below desk3col that isn't mobile." This directly contradicts D-05 ("mobile tree unchanged"), which is both a `must_haves.truths` entry and an explicit human-check item in this same plan.
2. Lost the cascade race to `sm:` even at desktop widths. Verified empirically by building and inspecting the compiled CSS: the custom `--breakpoint-desk3col` (1200px) media block sorts BEFORE the built-in `sm:` (640px) media block in this Tailwind v4.3.0 build's output — the opposite of ascending-breakpoint order. A base-unlocked/desk3col-relocks scheme with both `sm:` and `desk3col:` present would therefore have `sm:h-auto` (textually later) win the cascade at >=1200px, silently keeping desktop unlocked — the exact opposite of D-01.

Fix: kept the shell **locked by default** (unchanged base state, matches mobile today) and used a **compound range variant** `sm:max-desk3col:` to unlock only the existing 640-1199px tablet/stacked-fallback band (today's unchanged scroll behavior, now scoped instead of "everything sm: and up"). `short:` unlocks below 560px height at any width, independent of the range. This sidesteps the cascade-order issue entirely — there's no competing "relock" rule to lose a race against — while satisfying D-01, D-05, D-06, and D-09 simultaneously. Verified via `npm run build` + `python3` inspection of the compiled `dist/assets/*.css` (nested `@media (width>=40rem){ ... @media not all and (width>=1200px){ .sm\:max-desk3col\:block{...} } }` — exactly the 640-1199.98px band).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed the `short` custom-variant compiling to a no-op selector**
- **Found during:** Task 2 (Tailwind v4 tokens)
- **Issue:** RESEARCH.md Assumption A4's proposed syntax `@custom-variant short (&:is(@media (max-height: 559.98px)));` compiles without error but produces `.short\:block:is(){display:block}` — an empty `:is()` with no media-query wrapping, meaning every `short:` utility would apply at ALL viewport heights, not just short ones.
- **Fix:** Removed the `&:is()` wrapper: `@custom-variant short (@media (max-height: 559.98px));`. Rebuilt and confirmed the compiled CSS now correctly wraps in `@media (height<=559.98px){...}`.
- **Files modified:** `frontend/src/index.css`
- **Verification:** `npm run build` + inspected `dist/assets/index-*.css` with a small Python script to confirm the media-query wrapping.
- **Committed in:** `a2703b2e`

**2. [Rule 1 - Bug] Redesigned App.tsx's shell polarity to a three-band model instead of the plan's literal two-tier example**
- **Found during:** Task 3 (App.tsx polarity inversion)
- **Issue:** The plan's exact illustrative target CSS (copied from RESEARCH.md Pattern 2) would have unlocked true mobile (breaking D-05, a hard requirement in the same plan) AND lost the cascade to `sm:` at desktop widths due to `desk3col:`'s custom-breakpoint media block sorting before `sm:`'s in the compiled CSS (verified empirically).
- **Fix:** Kept the base state locked (matches today's mobile behavior); added a compound range variant `sm:max-desk3col:` to unlock only the 640-1199px tablet band (today's unchanged behavior, now scoped); kept `short:` as the unconditional-width safety valve. See "Decisions Made" above for full reasoning and verification.
- **Files modified:** `frontend/src/App.tsx`
- **Verification:** `npm run build` + inspected compiled CSS nesting; `npx tsc -b` clean; full frontend test suite green (1689/1689).
- **Committed in:** `72a286f1`

**3. [Rule 2 - Missing Critical] Added `desk3col:overflow-y-auto` to the board column**
- **Found during:** Task 3 (grid conversion)
- **Issue:** The plan's Task 3 action text for the board column (`Analysis.tsx:2025`) specified only `desk3col:min-h-0 desk3col:h-full`, omitting the explicit `overflow-y-auto` that D-09's "middle column scrolls internally once the board hits its 420px floor" contract actually requires. RESEARCH.md's own Pattern 4 discussion implies this region needs the class (its note that the region's `overflow-y-auto` "becomes moot" under the `short:` fallback only makes sense if the class is present in the first place).
- **Fix:** Added `desk3col:overflow-y-auto` to the board column div alongside `desk3col:min-h-0 desk3col:h-full`.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** `npx tsc -b` clean; full frontend test suite green; documented for the pending browser UAT pass to specifically confirm (viewport check #2 in the checklist below).
- **Committed in:** `72a286f1`

**4. [Rule 2 - Missing Critical] Added `desk3col:overflow-y-auto` to the Human column (resolving Open Question 1)**
- **Found during:** Task 3 (min-h-0 chain)
- **Issue:** RESEARCH.md flagged this as an open question requiring verification during implementation. Read `MaiaHumanPanel.tsx` and `flawChessCard`'s JSX and confirmed the combined content (~750-850px) can exceed the grid row's bounded height at the 420px board-floor case.
- **Fix:** Added `desk3col:min-h-0 desk3col:overflow-y-auto` to the Human column div.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** Same as above; documented for the pending browser UAT pass (viewport check #2).
- **Committed in:** `72a286f1`

**5. [Rule 3 - Blocking] Fixed two jsdom test-environment gaps surfaced by exercising game mode for the first time in Analysis.test.tsx**
- **Found during:** Task 3 (writing the D-04 relocation test)
- **Issue:** (a) jsdom has no `scrollIntoView` implementation, and `HorizontalMoveList`'s active-move effect calls it unconditionally, crashing any game-mode render. (b) `useFlawFilterStore` was mocked to return `[null, vi.fn()]`, and `SeverityBadge` (rendered inside `AnalysisTagsPanel`, now exercised for the first time in this test file) dereferences `flawFilter.severity.length` with no null guard, crashing on render.
- **Fix:** (a) Polyfilled `Element.prototype.scrollIntoView` with a no-op `vi.fn()`. (b) Changed the mock to return a realistic `DEFAULT_FLAW_FILTER`-shaped object instead of `null`.
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Verification:** `npx vitest run src/pages/__tests__/Analysis.test.tsx` — all 16 tests pass (was 15 passing + 1 crashing before the fix).
- **Committed in:** `72a286f1`

---

**Total deviations:** 5 auto-fixed (2 Rule 1 bug fixes, 2 Rule 2 missing-critical additions, 1 Rule 3 blocking fix).
**Impact on plan:** All five were necessary for correctness — two were required for the plan's own explicit hard requirements (D-05 mobile-unchanged, D-09 middle-column-scrolls) to actually hold; two fixed real compile/render bugs discovered while implementing exactly what the plan specified; one fixed test-infra gaps blocking the plan's own required test coverage. No scope creep — no file outside the plan's `files_modified` list was touched, and no feature beyond D-01…D-09 was added.

## Issues Encountered
None beyond the deviations documented above (all were resolved inline via the deviation rules, not left as open issues).

## Known Stubs
None — no hardcoded empty values, placeholder text, or unwired data sources were introduced.

## Threat Flags
None — this phase is a pure client-side CSS/JSX layout refactor with no new trust boundary, matching the plan's own threat model (`T-161-01`, disposition `accept`).

## User Setup Required
None - no external service configuration required.

## Pending HUMAN-UAT

The plan's Task 3 `<human-check>` (real multi-viewport browser verification) was **explicitly out of scope for this executor** per the orchestrator's instructions and is deferred to a human/orchestrator UAT pass. jsdom performs no real CSS layout (confirmed in RESEARCH.md's Validation Architecture section), so none of the following can be automated in this repo (no Playwright/Cypress/Puppeteer present):

1. **1280x800 and 1366x768** — desktop 3-column grid, frame locked to `100dvh`, NO page scroll, eval chart fully visible, move list scrolls internally.
2. **Shrink height toward ~560** — board shrinks to its ~420 floor, then the middle column (board + eval chart) AND the Human column scroll internally (the two Rule 2 additions above — this is the most important check, since it exercises code this executor could not visually verify).
3. **Height <560** — the `100dvh` lock releases and the whole page scrolls.
4. **Tall window >900px** — board still caps at 600px.
5. **~1150px wide** — hard-stacks to the existing stacked layout (no intermediate stage).
6. **<640px mobile** — visually identical to before this phase (the three-band App.tsx polarity redesign specifically targets preserving this).
7. **Human/board/engine-card tops** still align (the invisible-spacer trick, now remapped to `desk3col:`).
8. **Tags panel** appears at the bottom of the right column and its hover still highlights the eval chart.

All automated verification (`tsc -b`, `lint`, `knip`, full frontend test suite — 1689/1689 — and the `grep` check for the grid-cols class) is GREEN; see the `coverage:` block above for the D1-D5 machine-checkable deliverables and D6 for this human-judgment item.

## Next Phase Readiness
- Implementation is complete and all automated gates are green; the phase's success criteria are met pending the browser UAT pass above.
- No blockers for merging once UAT confirms the 8 viewport checks — this was a self-contained, single-plan phase (wave 1, no dependents).

---
*Phase: 161-analysis-page-viewport-locked-responsive-layout-seed-088*
*Completed: 2026-07-09*

## Self-Check: PASSED

All 5 files created/modified verified present on disk; all 4 commit hashes (`408312b4`, `7939980e`, `a2703b2e`, `72a286f1`) verified present in `git log --oneline --all`. No missing items.

## Post-Review Remediation (code review 161-REVIEW.md → commit after `f0412f19`)

Standard-depth code review surfaced 1 critical + 3 warnings + 1 info; the load-bearing one was fixed before phase completion:

- **CR-01 (BLOCKER, fixed):** `computeBoardSize` applied `Math.max(BOARD_MIN_WIDTH, …)` across the whole `min()`, so every width-driven caller with `heightBudget=Infinity` (Openings mini-boards ×2, TrainSketch, mobile analysis — all default `maxWidth=400`) was pinned to a fixed 420px, overflowing a 400px container by 20px and overflowing the viewport on any phone <420px. The floor is a **height** floor (D-08); reworked to `Math.min(widthBudget, min(maxWidth,BOARD_MAX_WIDTH), Math.max(BOARD_MIN_WIDTH, heightBudget))` so width-driven callers size to their container exactly as pre-phase. Verified against all original 6 behavior cases + new regression cases.
- **WR-01 (fixed):** added width-below-floor tests — `computeBoardSize(400, Infinity, 400)===400`, `(350, Infinity, 400)===350`, `(300, 500, 600)===300` — the exact shape that shipped green.
- **WR-02 (fixed):** added `desk3col:overflow-y-auto` to the side-panel (right) column so the D-04-relocated tags panel scrolls instead of clipping in the ~560–700px locked-height band (matches both sibling columns; the `flex-1` move list absorbs space first, so the column only scrolls when fixed siblings alone overflow).
- **IN-01 (fixed):** replaced the duplicated `maxWidth={600}` literal at the analysis call site with the imported `BOARD_MAX_WIDTH` constant.
- **WR-03 (accepted, no change):** `heightRef` pointing at the board's own `boardRow` ancestor is self-referential below `desk3col`, but correctness rests on the documented `flex-1`/`min-h-0` decoupling (the wrapper's height is parent-resolved, not content-resolved). Working as designed; no fix.

Post-fix gates all green: `boardSize.test.ts` 7/7, `Analysis.test.tsx` 16/16, `tsc -b` clean, `lint` 0 errors, `knip` clean, full frontend suite **1690/1690**.
