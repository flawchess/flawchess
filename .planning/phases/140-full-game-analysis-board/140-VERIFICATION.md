---
phase: 140-full-game-analysis-board
verified: 2026-06-27T13:25:00Z
status: human_needed
score: 2/5
behavior_unverified: 3
overrides_applied: 0
behavior_unverified_items:
  - truth: "Analyze opens /analysis?game_id=X&ply=Y and loads the full game line positioned at the carried ply"
    test: "Open /analysis?game_id=<id>&ply=<n> for an analyzed game; verify board renders game at ply N (pieces + move list highlight) and the EvalChart slider sits at ply N"
    expected: "Board positioned at ply N, move list highlights ply N's move, EvalChart slider at N, game line fully loaded (ply 0→end)"
    why_human: "Board seeding requires a live useLibraryGame response + loadMainLine + goToNode(mainLine[initialPly]) effect chain; no integration test exercises this with real data"
  - truth: "Slider scrubs the main game line (board + move-list sync) and parks dimmed at the fork ply on a sideline; re-enables on return to main line"
    test: "On a loaded game, click a main-line move; verify slider position matches ply, board + move-list update. Then click an inline chip to enter a sideline; verify slider is dimmed (opacity-40) with tooltip 'Return to main game line to scrub'. Return to main line; verify slider re-enables."
    expected: "Three-way sync (board + move list + slider) on main-line clicks; slider visually dimmed + tooltip on sideline; re-enabled on main-line return"
    why_human: "State transitions across three components; slider visual dim + tooltip only observable in a running browser"
  - truth: "Clicking an inline missed/allowed chip fetches its stored PV and unfolds it as a Level-1 sideline; a user move within it creates a Level-2 sub-sideline; TacticModeOverlay activates contextually"
    test: "Load /analysis?game_id=X&ply=Y on a game with a tactic flaw; click the inline Missed/Allowed chip; verify PV unfolds as variation-pv-section, board parks at fork, TacticModeOverlay appears. Within the PV, make a board move; verify a variation-subpv-section appears."
    expected: "PV sideline renders as ml-8 indented block; overlay shows with tactic arrows; level-2 sub-sideline renders when a move is made within the PV"
    why_human: "Requires live chip-click → useTacticLines fetch → insertPvLine effect → re-render → TacticModeOverlay activation chain; no integration test exercises this end-to-end"
human_verification:
  - test: "Open /analysis?game_id=<id>&ply=<n> for an analyzed game and verify full game load + ply positioning"
    expected: "Board at ply N, move list highlights correct move, EvalChart slider at ply N, full game line ply 0→end loaded"
    why_human: "Live board seeding from URL params requires a running app with real game data"
  - test: "Click main-line moves and verify three-way sync (board, move list, slider); then enter a sideline via an inline chip and verify slider dims with tooltip; return to main line and verify slider re-enables"
    expected: "Board + move list + slider all move together on main line; slider shows opacity-40 + 'Return to main game line to scrub' tooltip on sideline; re-enables on main line return"
    why_human: "Visual state transitions (dim, tooltip) only verifiable in a running browser"
  - test: "Click an inline Missed chip on a game with tactic flaws, observe PV unfold + TacticModeOverlay; make a move in the PV sideline and observe level-2 sub-sideline"
    expected: "variation-pv-section renders indented below the chip; TacticModeOverlay shows with arrows; variation-subpv-section renders on user move within the PV"
    why_human: "Multi-component integration (fetch + tree graft + overlay + arrows); no end-to-end automated test"
  - test: "View /analysis at viewport <1024px and verify mobile stack order"
    expected: "Stack order top-to-bottom: Board+EvalBar, EvalChart (game mode), overlay, engine lines, move list, board controls"
    why_human: "Responsive visual layout only verifiable at real mobile viewport size"
  - test: "On the game card page (analyzed game), confirm exactly one Analyze button with Search icon; on flaw card, confirm exactly one Analyze button; confirm no Game modal opens anywhere"
    expected: "One Search-icon Analyze button per analyzed game card (desktop + mobile row); one Analyze button on each flaw card; no Dialog/Drawer opens when clicking any button"
    why_human: "Cross-page navigation and deletion verification requires browsing the live app"
---

# Phase 140: Full-Game Analysis Board — Verification Report

**Phase Goal:** The `/analysis` board loads the whole game on a single unified `Analyze` entry point, with the eval chart relocated below the board and inline missed/allowed tags that expand stored PVs as navigable sidelines.
**Verified:** 2026-06-27T13:25:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Game card and flaw card each expose exactly one `Analyze` button; old pairs and inline Game modal code deleted | VERIFIED | `btn-library-game-analyze` in LibraryGameCard desktop+mobile; `btn-flaw-analyze` in FlawCard; grep confirms `useLibraryGame`/Dialog/Drawer count=0 in FlawCard; no `game-card-btn-explore` or `Activity` import in LibraryGameCard |
| SC-2 | `Analyze` opens `/analysis?game_id=X&ply=Y`, loading full game line positioned at carried ply | PRESENT_BEHAVIOR_UNVERIFIED | `buildGameAnalysisUrl` implemented + unit-tested; Analysis.tsx parses params with NaN-guard; `useLibraryGame` + `loadMainLine` + `goToNode(mainLine[initialPly])` effects wired; actual board seeding at runtime needs human |
| SC-3 | Eval chart below board, move list = board height, controls below move list; slider syncs main line, parks on sideline | PRESENT_BEHAVIOR_UNVERIFIED | Layout code confirmed: EvalChart in left column below board; VariationTree `max-h-[480px] overflow-y-auto` matches board `maxWidth={480}`; BoardControls at bottom of right column; `sliderDisabled={!isOnMainLineForSlider}` with `opacity-40` wired; visual sync and dim behavior needs human |
| SC-4 | Inline missed/allowed chips unfold stored PV sideline; sub-sideline branching (2 levels); contextual TacticModeOverlay | PRESENT_BEHAVIOR_UNVERIFIED | `flaw-inline-tag-missed/allowed-{nodeId}` chips implemented + tested (8 new VariationTree tests); `variation-pv-section` and `variation-subpv-section` in DOM; `insertPvLine` effect grafts PV on `contextualTacticData`; full chip-click → fetch → graft → overlay chain needs human |
| SC-5 | No new backend schema/endpoints (D-4); mobile stacked equivalent; knip/lint/tests pass | VERIFIED | No backend files in phase diff; DOM order is mobile-correct (`flex-col` default); `npm run knip` clean; `npm run lint` 0 errors; `npm test -- --run` 103 files 1206 tests pass; `npx tsc -b` zero errors; mobile visual rendering needs human (flagged separately) |

**Score:** 2/5 truths verified (SC-1, SC-5 fully automated; SC-2, SC-3, SC-4 present + wired, behavior unverified)
**Behavior unverified:** 3 (SC-2, SC-3, SC-4)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/theme.ts` | `TAC_MISSED_BORDER` constant | VERIFIED | Line 153: `oklch(0.70 0.15 258 / 0.30)` |
| `frontend/src/lib/analysisUrl.ts` | `buildGameAnalysisUrl(gameId, ply)` | VERIFIED | Lines 31-32; returns `/analysis?game_id={id}&ply={ply}` |
| `frontend/src/lib/analysisUrl.test.ts` | 2 unit tests for `buildGameAnalysisUrl` | VERIFIED | Tests at lines 33-41 pass |
| `frontend/src/components/library/EvalChart.tsx` | `sliderTestId`, `sliderDisabled` props | VERIFIED | Lines 132, 138; backward-compatible defaults; `opacity-40` + tooltip wired |
| `frontend/src/hooks/useAnalysisBoard.ts` | `pvLine`, `insertPvLine`, `clearPvLine`, `isOnPvLine` | VERIFIED | All four exported; single-setState insert pattern implemented |
| `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` | Behavior 5/6/7 invariant tests | VERIFIED | 3 new tests; behaviors 5 (insert chain), 6 (clear + recovery), 7 (level-2 fork) |
| `frontend/src/components/analysis/VariationTree.tsx` | Two-level nesting, inline chips, severity markers | VERIFIED | `variation-pv-section`, `variation-subpv-section`, `flaw-inline-tag-*`, `BlunderIcon`/`MistakeIcon` present |
| `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` | 8 new Phase 140 test cases | VERIFIED | Tests 7–10 cover level-1/level-2/chip-render/chip-click/error/blunder/inaccuracy |
| `frontend/src/pages/Analysis.tsx` | Game mode: `isGameMode`, `useLibraryGame`, EvalChart below board, slider parking, contextual overlay | VERIFIED | All symbols confirmed; layout structure correct; `handlePvChipClick` + `insertPvLine` effect wired |
| `frontend/src/pages/__tests__/Analysis.test.tsx` | `useLibraryGame` mock added | VERIFIED | Mock returns `{ data: undefined, isError: false }` |
| `frontend/src/components/results/LibraryGameCard.tsx` | Single Search-icon Analyze button (analyzed, desktop + mobile) | VERIFIED | `btn-library-game-analyze` at lines 883 + 958; `isAnalyzed` gate; `buildGameAnalysisUrl` used |
| `frontend/src/components/library/FlawCard.tsx` | Single Analyze button, Game modal deleted | VERIFIED | `btn-flaw-analyze` at line 200; `useLibraryGame` count=0; `Dialog`/`Drawer` count=0 |
| `frontend/src/components/library/__tests__/FlawCard.test.tsx` | 4 new Analyze button tests | VERIFIED | Tests at lines 326+ cover aria-label, href, Search icon |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `LibraryGameCard.tsx` | `/analysis?game_id=X&ply=Y` | `buildGameAnalysisUrl(game.game_id, hoverPly ?? lastEvalPly ?? 0)` | WIRED | Link rendered as `<Link to={buildGameAnalysisUrl(...)}>`; confirmed at lines 882, 957 |
| `FlawCard.tsx` | `/analysis?game_id=X&ply=Y` | `buildGameAnalysisUrl(flaw.game_id, flaw.ply)` | WIRED | Confirmed at line 199 |
| `Analysis.tsx` | `useLibraryGame` | `isGameMode ? gameId : null` | WIRED | Conditional enable via null arg; data used to seed board |
| `Analysis.tsx` | `useTacticLines` (contextual) | `activePvFlaw != null && isGameMode` | WIRED | Dual top-level hook calls; enabled flag gates fetch |
| `Analysis.tsx` | `insertPvLine` effect | `contextualTacticData` + `activePvFlaw` | WIRED | Effect at line 266 grafts PV on data arrival |
| `Analysis.tsx` → `VariationTree.tsx` | PV props | `pvLine`, `flawMarkerByNodeId`, `onPvChipClick`, `activePvNodeId`, `pvFetchPending`, `pvFetchError` | WIRED | All 6 props passed at lines 617-622 |
| `Analysis.tsx` → `EvalChart.tsx` | Slider disable | `sliderDisabled={!isOnMainLineForSlider}` | WIRED | Line 543; `isOnMainLineForSlider = currentNodeId === null || isOnMainLine(currentNodeId)` |
| `Analysis.tsx` → `TacticModeOverlay` | Contextual activation | `showTacticOverlay = (isTacticMode && ...) || (isGameMode && activePvFlaw != null && contextualTacticData != null)` | WIRED | Lines 483-484 |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `buildGameAnalysisUrl` returns correct URL format | `npm test -- --run analysisUrl` | 2 tests pass | PASS |
| `insertPvLine` invariants (chain, mainLine unmutated) | `npm test -- --run useAnalysisBoard` | Behavior 5 passes | PASS |
| `clearPvLine` returns currentNodeId to mainLine | `npm test -- --run useAnalysisBoard` | Behavior 6 passes | PASS |
| Level-2 fork detection | `npm test -- --run useAnalysisBoard` | Behavior 7 passes | PASS |
| VariationTree level-1 pv-section renders | `npm test -- --run VariationTree` | Test (7) passes | PASS |
| VariationTree level-2 subpv-section renders | `npm test -- --run VariationTree` | Test (8) passes | PASS |
| Inline flaw chips render + click callback | `npm test -- --run VariationTree` | Tests (9), (9b), (9c) pass | PASS |
| Blunder icon renders; inaccuracy renders no marker | `npm test -- --run VariationTree` | Tests (10), (11) pass | PASS |
| `btn-flaw-analyze` href matches expected URL | `npm test -- --run FlawCard` | Test passes | PASS |
| Full frontend gate | `npm run lint && npm test -- --run && npx tsc -b && npm run knip` | 0 errors; 103 files / 1206 tests; 0 type errors; knip clean | PASS |

---

### Requirements Coverage

| Requirement | Plans | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| SC-1 | 01, 02, 03 | Single Analyze button entry points; modal deleted | SATISFIED | Code confirms; no old testids/imports remain |
| SC-2 | 01, 02 | URL carries game_id + ply; full game loads | PARTIAL | Code wired; runtime behavior HUMAN-UAT |
| SC-3 | 02 | Layout: EvalChart below board, move list = board height, controls below, slider parks | PARTIAL | DOM structure confirmed; visual behavior HUMAN-UAT |
| SC-4 | 01, 02 | Inline chips → PV → 2-level nesting → contextual overlay | PARTIAL | Code + unit tests; integration HUMAN-UAT |
| SC-5 / D-4 | 01, 02, 03 | No backend changes; mobile stacked; automated gate | SATISFIED | No backend diff; gate passes; mobile visual HUMAN-UAT |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `LibraryGameCard.tsx` | 793, 799, 894 | "placeholder" (UI em-dash lane), "hack" (removed z-30) | Info | Pre-existing comments describing layout patterns and a removed workaround; not stub code |

No BLOCKER anti-patterns found. The "placeholder" occurrences describe a UI column filler (em-dash character), not stub implementations. The "hack" comment references a removed feature.

---

### Human Verification Required

#### 1. Full game load and ply positioning

**Test:** Open `/analysis?game_id=<id>&ply=<n>` for an analyzed game (use any game_id from the library on a game with `analysis_state = 'analyzed'`).
**Expected:** Board renders at ply N with the correct piece positions; move list highlights the move at ply N; EvalChart slider sits at ply N; the full game line (ply 0 through end) is loaded in the move list.
**Why human:** Board seeding requires a live `useLibraryGame` response feeding `loadMainLine` + `goToNode(mainLine[initialPly])` — no integration test exercises this end-to-end.

#### 2. Three-way slider sync (main line) and slider parking (sideline)

**Test:** On a loaded game, click several main-line moves in the move list. Then click an inline Missed or Allowed chip to enter a sideline. Return to the main line.
**Expected:** On main line: board, move-list highlight, and EvalChart slider all update together when a move is clicked. On sideline: slider is visually dimmed (opacity-40) and shows tooltip "Return to main game line to scrub". On return to main line: slider re-enables.
**Why human:** Three-component state sync and visual dim/tooltip are only verifiable in a running browser.

#### 3. Inline chip → PV unfold → Level-2 sub-sideline → contextual TacticModeOverlay

**Test:** Load `/analysis?game_id=X&ply=Y` on a game with tactic flaws. Click an inline Missed or Allowed chip. Within the expanded PV, make a board move (drag or click-to-click).
**Expected:** Clicking the chip: indented `variation-pv-section` block appears, board parks at the fork position, TacticModeOverlay appears with tactic arrows. Making a move within the PV: a `variation-subpv-section` block appears nested inside the Level-1 section.
**Why human:** Requires live `useTacticLines` fetch → `insertPvLine` effect → tree re-render → overlay activation chain; no integration test exercises this end-to-end.

#### 4. Mobile stacked layout

**Test:** Open `/analysis?game_id=X&ply=Y` at a viewport width narrower than 1024px (or mobile device / DevTools mobile simulation).
**Expected:** Components stack top-to-bottom: Board+EvalBar → EvalChart (if game mode) → TacticModeOverlay (if active) → EngineLines → VariationTree (move list) → BoardControls.
**Why human:** Responsive visual layout only verifiable at real mobile viewport size.

#### 5. Single Analyze button on live game and flaw cards; no Game modal

**Test:** Browse the library page showing game cards with `analysis_state = 'analyzed'`. Check both desktop and mobile views. Open the flaw cards view. Attempt to find any remaining Game modal or old Explore / Analyze-position button pairs.
**Expected:** Analyzed game card shows exactly one Analyze button with Search icon per card (desktop card and mobile row). Flaw card shows exactly one Analyze button. No Dialog/Drawer Game modal opens anywhere in the app.
**Why human:** Cross-page navigation and verifying absence of removed UI requires browsing the live app.

---

## Summary

**All automated checks pass.** The 8 phase commits (397f4cb2 through c99b2a6c) are present and verified against their claims. The automated test gate — lint (0 errors), 103 test files / 1206 tests, TypeScript (`tsc -b` zero errors), knip (clean) — is fully green.

**Code-level verification confirms:**
- SC-1 (entry points) and SC-5 (automated gate + no backend changes) are fully satisfied.
- SC-2 (game load from URL), SC-3 (slider sync + layout), and SC-4 (chip → PV → overlay) are all present and wired, with supporting unit tests for the tree invariants and UI rendering. The runtime behavior of the state-transition chains — board seeding from URL params, three-way sync, and the chip-click-to-PV-unfold integration — requires a running browser to confirm. These three success criteria are marked PRESENT_BEHAVIOR_UNVERIFIED per the verification protocol; they match the HUMAN-UAT items the VALIDATION.md already identified.

**No gaps or blockers found.** The 5 human verification items are all in the VALIDATION.md's original manual-only list — they are expected UAT items, not uncovered defects.

---

_Verified: 2026-06-27T13:25:00Z_
_Verifier: Claude (gsd-verifier)_
