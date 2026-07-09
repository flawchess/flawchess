---
phase: 161-analysis-page-viewport-locked-responsive-layout-seed-088
verified: 2026-07-09T18:31:39Z
status: human_needed
score: 3/7 truths verified (structural/logic level)
behavior_unverified: 4
overrides_applied: 0
behavior_unverified_items:
  - truth: "D-01: On desktop (>=1200px wide, >=560px tall) the /analysis frame is locked to 100dvh with no page scroll; the move list (VariationTree) scrolls internally instead."
    test: "Load /analysis (game mode) at 1280x800 and 1366x768 in a real browser."
    expected: "No page-level scrollbar; the whole frame fills the viewport; the move-list/right column scrolls internally."
    why_human: "jsdom performs no real CSS layout; 100dvh resolution and scroll-container behavior can only be observed in a real browser viewport."
  - truth: "D-05: The mobile tree (isMobile true, <640px) and the sub-breakpoint stacked fallback (640-1199px) are visually unchanged."
    test: "Compare /analysis on a <640px viewport and a ~900px viewport before/after this phase."
    expected: "Pixel-equivalent to pre-phase behavior — no visible change."
    why_human: "Visual-parity claims are not verifiable via grep/unit tests; requires side-by-side rendering comparison. (Code diff strongly supports no change — see Artifacts section — but rendering equivalence itself is not code-observable.)"
  - truth: "D-06/D-07: Above ~1200px = full 3-column grid; below ~1200px it hard-stacks to the existing stacked/mobile layout with no intermediate stage; 1280 and 1366 laptops stay in desktop 3-column."
    test: "Resize window width across ~1200px; check 1280px and 1366px widths explicitly."
    expected: "Grid layout applies at and above 1200px with no intermediate/staged collapse; 1280/1366 render as 3-column desktop."
    why_human: "Media-query breakpoint evaluation is not exercised by jsdom; requires real browser resize."
  - truth: "D-09: Below ~560px viewport height the 100dvh lock releases and the whole page scrolls."
    test: "Shrink browser window height below 560px on a desktop-width viewport."
    expected: "100dvh lock releases (short:h-auto), page-level scroll appears."
    why_human: "Height media query (max-height:559.98px) evaluation is not exercised by jsdom."
human_verification:
  - test: "1280x800 and 1366x768 — desktop 3-column grid, frame locked to 100dvh, NO page scroll, eval chart fully visible, move list scrolls internally."
    expected: "Frame fills viewport exactly; no page scrollbar; move list/right column scroll internally; eval chart fully visible (the original SEED-088 bug)."
    why_human: "Real CSS layout/100dvh resolution, not observable via jsdom."
  - test: "Shrink height toward ~560px — board shrinks to its ~420 floor; the board column AND the Human column scroll internally (per the two Rule-2 desk3col:overflow-y-auto additions)."
    expected: "Board visually shrinks, floors at ~420px; board column and Human column each scroll internally instead of overflowing the page."
    why_human: "ResizeObserver-driven live shrink + internal overflow behavior requires a real browser."
  - test: "Height <560px — the 100dvh lock releases and the whole page scrolls."
    expected: "short: variant fires; page-level scroll replaces the locked frame."
    why_human: "Height media query not evaluated in jsdom."
  - test: "Tall window >900px — board still caps at 600px."
    expected: "Board does not exceed 600px width/height even with abundant vertical space."
    why_human: "Requires observing rendered board pixel size in a real browser."
  - test: "~1150px wide — hard-stacks to the existing stacked layout (no intermediate stage)."
    expected: "At ~1150px (below the 1200px desk3col threshold) the layout matches today's stacked/tablet fallback, not a partial 3-column state."
    why_human: "Breakpoint media-query evaluation not exercised in jsdom."
  - test: "<640px mobile tree — visually identical to before this phase."
    expected: "No visible difference in the mobile tab-takeover UI."
    why_human: "Visual parity; code diff supports no change but rendering equivalence requires human eyes."
  - test: "Human/board/engine-card tops still align (the invisible-spacer trick, remapped to desk3col:)."
    expected: "The three desktop columns' top edges align visually."
    why_human: "Visual alignment is a rendering property, not code-observable."
  - test: "Tags panel appears at the bottom of the right column and its hover still highlights the eval chart."
    expected: "AnalysisTagsPanel renders after boardControls in the right column; hovering a tag highlights corresponding plies on the eval chart in the middle column."
    why_human: "The relocation and withHighlight=true wiring are code-confirmed (see Artifacts/Key Links); the actual hover-highlight visual effect requires interactive browser confirmation."
---

# Phase 161: Analysis page viewport-locked responsive layout Verification Report

**Phase Goal:** Convert the `/analysis` desktop (`lg+`) layout from scrolling fixed-pixel columns to a viewport-locked, fluid layout (chess.com/lichess model) so content no longer cuts off at the bottom on small laptop screens. Lock the frame to `100dvh` (no page scroll, inner regions scroll), size the board to `min(width budget, remaining height)` with a ~420px floor, reclaim horizontal space (widen/remove `max-w-7xl`, flex row → CSS grid with fluid middle), and relocate the Tags/badges panel from the middle column into the bottom of the right column. Mobile (`<lg`) stays unchanged.

**Verified:** 2026-07-09T18:31:39Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-01: Desktop frame locked to `100dvh`, no page scroll, move list scrolls internally | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `App.tsx:512` shell class `h-[100dvh] sm:max-desk3col:h-auto ... short:h-auto`; confirmed against pre-phase `git show 72a286f1^:frontend/src/App.tsx` (`h-[100dvh] sm:h-auto sm:block`) — polarity change is real and matches the claimed three-band redesign. CSS compiles (verified `sm\:max-desk3col\:h-auto` present in `dist/assets/*.css`). Real dvh-lock/no-scroll behavior not exercisable in jsdom. |
| 2 | D-02/D-08: Board shrinks with height, floors at 420, caps at 600 | ✓ VERIFIED | `frontend/src/components/board/boardSize.ts` `computeBoardSize()`; `boardSize.test.ts` 7/7 passing incl. CR-01 regression cases (`computeBoardSize(400, Infinity, 400)===400`, `(350, Infinity, 400)===350`, `(300, 500, 600)===300`); ChessBoard.tsx wires `heightRef`→`clientHeight`→`computeBoardSize`. Full clamp/floor/ceiling logic is unit-exercised, not just present. |
| 3 | D-03: 3-column CSS grid `grid-cols-[360px_1fr_360px]`, `max-w-7xl` removed | ✓ VERIFIED | `Analysis.tsx:1997` `desk3col:grid desk3col:grid-cols-[360px_1fr_360px]`; `grep 'max-w-7xl'` on the desktop tree returns nothing (only a removal comment at 1993); `Analysis.test.tsx` asserts the grid class on the row (passing). |
| 4 | D-04: Tags panel at bottom of right column, `withHighlight=true` preserved | ✓ VERIFIED | `Analysis.tsx:2140,2146` — `{boardControls()}` then `{tagsPanel(true)}` inside the right-column div; removed from board column (board column now ends at the eval-chart block, line ~2064). `Analysis.test.tsx` "renders AnalysisTagsPanel in the right column, after the engine card and move list (D-04)" passes. |
| 5 | D-05: Mobile tree and sub-breakpoint stacked fallback visually unchanged | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `useIsMobile`/`MOBILE_BREAKPOINT_PX` (640px) untouched (`Analysis.tsx:109-152`); mobile shell classes (`h-[100dvh]` base, unlocked only at `sm:max-desk3col:`) match pre-phase mobile behavior exactly per diff. Code strongly supports no change; actual visual rendering not confirmed. |
| 6 | D-06/D-07: Hard-stack below ~1200px, no intermediate stage; 1280/1366 stay 3-column | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `index.css:17` `--breakpoint-desk3col: 1200px`; all 6 `lg:` occurrences remapped to `desk3col:` (grep confirms zero live `lg:` classes remain in the desktop tree, only a removal comment). Breakpoint switching itself needs real-browser resize. |
| 7 | D-09: Below ~560px height, `100dvh` lock releases, page scrolls | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `index.css:23` `@custom-variant short (@media (max-height: 559.98px));`; compiled CSS confirmed to contain a real `@media (height<=559.98px)` block (not an empty selector — the CR from RESEARCH Assumption A4 was caught and fixed per SUMMARY, verified via `npm run build` + `grep 559.98px dist/assets/*.css`). Real release-on-short-height behavior needs a real browser. |

**Score:** 3/7 truths verified at code/logic level; 4/7 present + wired but require live-browser confirmation (behavior_unverified).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/board/boardSize.ts` | `computeBoardSize()` + `BOARD_MIN_WIDTH`/`BOARD_MAX_WIDTH` | ✓ VERIFIED | Present, substantive, wired (imported by `ChessBoard.tsx` and `Analysis.tsx`), fixed post-review (CR-01: floor now height-only, `Math.min(widthBudget, ceiling, heightFloored)`). |
| `frontend/src/components/board/__tests__/boardSize.test.ts` | Unit coverage of clamp/zero-guard | ✓ VERIFIED | 7 tests, all passing (`npx vitest run` confirmed live), includes the CR-01 regression cases (WR-01 fix). |
| `frontend/src/components/board/ChessBoard.tsx` | Height-aware `ResizeObserver` via optional `heightRef` | ✓ VERIFIED | `heightRef?: RefObject<HTMLElement \| null>` added to props; single observer instance observes both `containerRef` and optional `heightRef`; `boardWidth>0` gate unchanged; only `Analysis.tsx` passes `heightRef` (grep confirms no other caller regressed). |
| `frontend/src/index.css` | `--breakpoint-desk3col` token + `short` variant | ✓ VERIFIED | `--breakpoint-desk3col: 1200px` (line 17); `@custom-variant short (@media (max-height: 559.98px));` (line 23) — the correct at-rule form (not the broken `&:is()` form from RESEARCH's Assumption A4, per SUMMARY's documented fix); compiled CSS confirmed to contain real media-query wrapping. |
| `frontend/src/App.tsx` | Shell lock/unlock polarity inverted | ✓ VERIFIED | Confirmed via diff against pre-phase commit: base locked (`h-[100dvh]`) unchanged for mobile, `sm:max-desk3col:` unlocks the existing tablet band (640-1199px, unchanged scroll behavior scoped), new `desk3col:` implicit lock at >=1200px (no rule needed — base is already locked), `short:` releases at <560px height. Matches the documented three-band redesign, not a naive `sm:`→`desk3col:` rename. |
| `frontend/src/pages/Analysis.tsx` | Grid conversion, tags relocation, `min-h-0` chain, `lg:`→`desk3col:` remap | ✓ VERIFIED | All present: grid row (1997), tags relocation (2140/2146), `min-h-0` chain intact across inner main (1996) → grid row (1997) → board column (2043) → Human column (2005) → right column (2069); zero live `lg:` occurrences remain. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| App `<main>` | Analysis inner `<main>` → grid row → board column → right column | `min-h-0` chain | ✓ WIRED | Every link in the chain carries `min-h-0` (or `desk3col:min-h-0`) at every level — confirmed by grep across both files; no broken link found. |
| `boardHeightRef` (Analysis.tsx boardRow) | `ChessBoard.tsx` heightRef consumption | `heightRef.current.clientHeight` → `computeBoardSize` | ✓ WIRED | `Analysis.tsx:1490` passes `heightRef={boardHeightRef}`; `ChessBoard.tsx:278-279` reads `clientHeight` and calls `computeBoardSize`, not a `calc()` of magic-number pixels. |
| `tagsPanel(true)` call site | `AnalysisTagsPanel` `withHighlight` prop → eval chart hover wiring | argument preserved across relocation | ✓ WIRED | `Analysis.tsx:2146` still passes `true`; the eval chart remains in the middle column at `Analysis.tsx:2060-2062`. |
| All 6 `lg:` occurrences | `desk3col:` remap | textual remap, `useIsMobile`/`MOBILE_BREAKPOINT_PX` untouched | ✓ WIRED | Grep confirms zero live `lg:` classes remain in the desktop tree; `MOBILE_BREAKPOINT_PX = 640` and `useIsMobile()` byte-identical to pre-phase. |

### Code Review Remediation Verification (161-REVIEW.md cross-check)

| Finding | Claimed Fix | Verified in Code |
|---------|-------------|-------------------|
| CR-01 (BLOCKER): unconditional `Math.max(BOARD_MIN_WIDTH, ...)` floor pinned every width-driven caller (Openings mini-boards, mobile) to 420px, overflowing containers | Reworked to floor the height dimension only: `Math.min(widthBudget, ceiling, Math.max(BOARD_MIN_WIDTH, heightBudget))` | ✓ Confirmed in `boardSize.ts:35-37` and commit `0f802517`. Regression tests added and passing. |
| WR-01: missing width-below-floor regression tests | Added 3 regression tests | ✓ Confirmed in `boardSize.test.ts:22-29`, all passing. |
| WR-02: right column lacks `overflow-y-auto`, relocated tags panel could clip | Added `desk3col:overflow-y-auto` to the right column | ✓ Confirmed at `Analysis.tsx:2069`. |
| IN-01: duplicated `maxWidth={600}` literal | Replaced with imported `BOARD_MAX_WIDTH` | ✓ Confirmed: `Analysis.tsx:70` imports `BOARD_MAX_WIDTH`, `Analysis.tsx:1489` uses it. |
| WR-03: `heightRef` self-referential below `desk3col` | Accepted, no code change (documented rationale: correctness rests on `flex-1`/`min-h-0` decoupling) | Reviewed rationale — reasonable and documented in-line at `Analysis.tsx:1431-1435`. Not a functional gap; acceptable as a documented design tradeoff. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEED-088 | 161-01-PLAN.md | Viewport-locked, fluid `/analysis` desktop layout fixing small-laptop bottom cutoff | ⚠️ NEEDS HUMAN (structural implementation SATISFIED, live behavior confirmation pending) | All D-01…D-09 decisions are implemented and code-verified per the table above; the live-browser dvh-lock/board-shrink/breakpoint-switch confirmation remains outstanding. |

**Note on REQUIREMENTS.md:** `SEED-088` does not appear in `.planning/REQUIREMENTS.md` — that document tracks the v2.0 "FlawChess Engine" milestone's formal `ENGINE-*`/`POOL-*`/`DISPLAY-*`/etc. requirement IDs. SEED-088 is a seed-triggered phase (captured via `/gsd-capture --seed`, planted 2026-07-09), not a milestone requirement, so its absence from REQUIREMENTS.md is expected structure, not an orphaned requirement.

### Anti-Patterns Found

None. Scanned all 7 phase-modified files for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/`placeholder`/`coming soon`/`not yet implemented` — the only matches (`Analysis.tsx:1112`, `1242`, and a test name at `Analysis.test.tsx:298`) are pre-existing, unrelated to this phase's changes (a game-ply placeholder comment, an arrow-timing placeholder comment, and a pre-existing test name containing the word "placeholder").

### Automated Gates (re-run live during this verification)

| Gate | Command | Result |
|------|---------|--------|
| boardSize unit tests | `npx vitest run src/components/board/__tests__/boardSize.test.ts` | ✓ 7/7 pass |
| Analysis unit tests | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ✓ pass (bundled in full run below) |
| Full frontend suite | `npm test -- --run` | ✓ 1690/1690 pass, 137/137 files |
| Type check | `npx tsc -b` | ✓ clean, zero errors |
| Lint | `npm run lint` | ✓ 0 errors (3 pre-existing warnings in `coverage/` generated files, unrelated) |
| Knip | `npm run knip` | ✓ clean, no dead exports |
| Production build | `npm run build` | ✓ builds; compiled CSS inspected and confirmed to contain real `@media (height<=559.98px)` and `@media not all and (width>=1200px)` blocks (not broken/empty selectors) |

All claims in 161-01-SUMMARY.md's automated-gate section are reproduced and confirmed live, not merely trusted.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `computeBoardSize` clamp/floor/ceiling logic (D-02/D-08, incl. CR-01 regression) | `npx vitest run .../boardSize.test.ts` | 7/7 pass | ✓ PASS |
| Real-browser `100dvh` lock / board live-shrink / breakpoint switch / mobile visual parity | N/A — no Playwright/Cypress/Puppeteer in this repo; browser automation tooling (claude-in-chrome) was intentionally not substituted here per the launching agent's explicit classification instruction | — | ? SKIP — routed to Human Verification |

### Probe Execution

No `scripts/*/tests/probe-*.sh` or phase-declared probes found for this phase (not a migration/tooling phase; N/A).

### Human Verification Required

See `human_verification` in frontmatter — this is the harvested Task 3 `<human-check>` (8 items) plus the 4 behavior-unverified truths above (D-01, D-05, D-06/D-07, D-09), which are the same underlying gap: real-browser responsive CSS behavior that jsdom cannot exercise. This was flagged by the plan itself (`161-VALIDATION.md`'s "Manual-Only Verifications" table, sign-off approved 2026-07-09) as a structural limitation, not a shortcut taken by the executor.

### Gaps Summary

No gaps found. All automated gates are green (re-verified live, not merely trusted from SUMMARY.md). The one blocker code-review finding (CR-01) is confirmed fixed in the actual code and covered by new regression tests; the two warnings that needed fixes (WR-01, WR-02) are also confirmed fixed; the info-level nit (IN-01) is confirmed fixed; the remaining warning (WR-03) is a documented, reasonable design tradeoff, not a functional defect.

The phase is structurally and logically complete: every D-01…D-09 decision has a corresponding, verifiable code change, and the pure-logic pieces (`computeBoardSize`) are behaviorally proven via unit tests that exercise the exact clamp/floor/ceiling transitions, including the regression the code review caught. What remains is the live-browser confirmation that these wired CSS classes actually produce the intended `100dvh` lock, height-aware board shrink, and breakpoint hard-stack in a real viewport — this is a `jsdom` limitation acknowledged by the plan's own validation strategy, not a gap in the implementation.

---

_Verified: 2026-07-09T18:31:39Z_
_Verifier: Claude (gsd-verifier)_
