---
phase: 245-analysis-explain-bar
verified: 2026-11-05T11:30:00Z
status: human_needed
score: 11/11 must-haves verified
covered_files:
  - ".planning/phases/245-analysis-explain-bar/245-01-PLAN.md"
  - ".planning/phases/245-analysis-explain-bar/245-01-SUMMARY.md"
  - ".planning/phases/245-analysis-explain-bar/245-02-PLAN.md"
  - ".planning/phases/245-analysis-explain-bar/245-02-SUMMARY.md"
  - "frontend/src/components/analysis/AnalysisBoardStage.tsx"
  - "frontend/src/components/analysis/AnalysisDesktopCards.tsx"
  - "frontend/src/components/analysis/ExplainBar.tsx"
  - "frontend/src/hooks/analysis/useAnalysisBoardArrows.ts"
  - "frontend/src/hooks/analysis/useAnalysisRouteSeeding.ts"
  - "frontend/src/hooks/analysis/useExplainBar.ts"
  - "frontend/src/hooks/useLibrary.ts"
  - "frontend/src/lib/analysisTactics.ts"
  - "frontend/src/lib/analytics.ts"
  - "frontend/src/lib/explainBar.ts"
  - "frontend/src/lib/tacticOrientation.ts"
  - "frontend/src/pages/Analysis.tsx"
covered_digest: "v4:sha256:e003821c782633fb54d47d873e4a8d59630654f35afa299e4eabc3d29db9dfb0"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Desktop (>=1200px): open a game on /analysis, land on an owner mistake/blunder without a tactic motif, click Explain, press Forward/Back, click Got it"
    expected: "Bar sits as a footer row inside the move-list card; Explain grafts the missed line and the board shows missed_moves[0]; Back/Forward step the line; Got it removes the sideline and returns to the flaw move; headline copy and row height do not shift between Explain and Got it"
    why_human: "Visual fit and layout; jsdom has no layout engine"
  - test: "Mobile 360px: same flow"
    expected: "Bar is the row directly above the 5-column footer, nothing overflows or truncates badly, footer still has 5 columns"
    why_human: "360px fit needs a real browser"
  - test: "Mid layout 768-1199px: same flow"
    expected: "Bar is a Card directly under the board controls; exactly one bar; none inside the Moves tab (owner-UAT default from 245-02)"
    why_human: "Placement choice is flagged owner-UAT"
  - test: "Explain on a non-motif flaw and on an opponent flaw; observe board arrow and move-list tint"
    expected: "Plain unlabelled payoff-blue next-move arrow, no teal/crimson tint, no numbered countdown (owner-UAT item 1). Motif chip-opened lines keep the countdown overlay"
    why_human: "Visual overlay judgment"
  - test: "Click Explain / Got it / Forward through the line with sound on, including iOS Safari if available"
    expected: "One move sound per step, no double sound or fork flash on Explain"
    why_human: "Audio and one-frame flash cannot be observed in jsdom"
  - test: "Consecutive flaws P-1 and P (P user's, P-1 opponent's): Explain on P, Back to P-1"
    expected: "Decide whether showing Got it for P at P-1 (code-review WR-01) is acceptable; P-1 Explain is reachable via Got it then Back"
    why_human: "Product call on an accepted-precedence edge"
---

# Phase 245: Analysis Explain Bar Verification Report

**Phase Goal:** Give every flaw on the Analysis page a one-click guided explanation (Explain, then step through the stored PV, then Got it), using PVs FlawChess already stores. Frontend only. Inaccuracies descoped by D-08.
**Verified:** 2026-11-05
**Status:** human_needed (all automated checks pass; remaining items are browser-only)
**Re-verification:** No, initial verification

## Goal Achievement

Verified against code, not SUMMARY claims. Backend diff vs `main` is empty (`git diff --stat main...HEAD -- app tests` shows nothing). The 7 phase-relevant test files (194 tests) pass when run directly in this session.

### Observable Truths (CONTEXT D-01..D-11 plus plan must_haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| D-01 | One button only, no Best/Next | VERIFIED | `ExplainBar.tsx` renders exactly one `<Button>` per state (Explain or Got it); no other buttons; ExplainBar.test covers one-button per placement |
| D-02 | No coach prose / LLM | VERIFIED | Only static label strings in `ExplainBar.tsx` (`SEVERITY_SUFFIX`, `GOT_IT_PREFIX`, etc.); no fetch or LLM call |
| D-03 | Contextual bar: desktop under move list, mobile above footer, mid under controls | VERIFIED (visual: human) | `Analysis.tsx:2693` `footer={<ExplainBar placement="desktop">}` in `MovesCard` (after VariationTreePanel); `:2557` mobile row; `:2109` mid via `DesktopBoardStage` `isMid && explainBar`. Analysis.test "Explain bar placement" asserts one bar per layout |
| D-04 | Direction rule: owner flaw -> missed (fork ply-1), opponent -> allowed (fork at flaw ply) | VERIFIED | `chooseExplainOrientation` in `lib/explainBar.ts`; unit test "prefers missed for the owner and allowed for the opponent"; harness D-05 missed/allowed tests |
| D-05 | Explain grafts and plays first move; allowed lands on refutation, flaw move not grafted | VERIFIED | Graft effect `useAnalysisRouteSeeding.ts`: `pvMoves = allowed_moves.slice(1)`, `if (pendingFlaw.enter) goToNode(rootNodeId)` in the same updater chain as `insertPvLine`; `onExplain` sets `{...flaw, enter:true}` and does not navigate to fork first. Real-board harness tests "D-05 missed" and "D-05 allowed" pass |
| D-06 | Back/Forward step; Got it deletes subtree + openLines entry and returns to flaw move | VERIFIED | `onGotIt`: `deleteSubtree(rootNodeId)`, `setOpenLines` delete, `goToNode(mainLine[line.ply])` for both orientations. Harness tests "D-06 Back/Forward ... Got it" (missed) and "Got it on an allowed line" pass |
| D-07 | Leaving keeps line open; re-entry shows Got it; shared `flawKey` with chips, no duplicates | VERIFIED | `onExplain` checks `openLines.get(flawKey(state.flaw))` and `goToNode(existing.rootNodeId)` without grafting; `findFocusedFlaw` covers fork + subtree. Harness tests "D-07 leaving ... re-enters" and chip-shared-key test pass |
| D-08 | Inaccuracies out of scope; M/B of both sides eligible, with or without motif | VERIFIED | `eligibleExplainMarker` filters `isExplainSeverity`; unit test + Analysis.test "D-08: an inaccuracy ply shows no bar even with usable tactic-line data" |
| D-09 | Fallback to the other line when preferred is null; key uses used orientation | VERIFIED | `usableExplainLines` + `chooseExplainOrientation` fallback; `state.flaw.orientation` is the used one, which is what goes into `pendingFlaw`/`flawKey`. Unit + harness "D-09 fallback" tests pass |
| D-10 | Bar hidden when neither line exists; no disabled button/tooltip | VERIFIED | `resolveExplainBarState` rule 5 returns `hidden`; `ExplainBar` returns `null` for hidden |
| D-11 | Prefetch on landing via `useTacticLines`, same key; no placeholder until resolved | VERIFIED | `useExplainBar.ts` calls `useTacticLines(gameId, eligiblePly, isGameMode && eligiblePly !== null)`, key `['tactic-lines', gameId, ply]`; rule 4 hides while `tacticLines == null`. 404 mapped to `null` in `useLibrary.ts` (hardening, tested in `useLibrary.test.ts`) |
| Plan | Chip clicks and `initialTactic` auto-open unchanged | VERIFIED | `enter` flag is optional; `initialTactic` branch sets `setPendingFlaw(initialTactic)` without it (still parks at fork); harness asserts chips park at fork |
| Plan | Umami via typed registry, only from click handlers | VERIFIED | `BOARD_TOOL_TARGETS` gains `explain-open`/`explain-close`; `trackFeature` called only in `onExplain`/`onGotIt`; harness tracking test asserts nothing on render/navigation; ExplainBar component has no tracking |
| Plan | Bar hidden during fast-forward | VERIFIED | `resolveExplainBarState` rule 1; unit test |
| Plan | Overlay honesty for non-motif lines; 404 -> null; CHANGELOG/README | VERIFIED | `lineHasVisibleMotif` + `focusedLineHasMotif` wired at `Analysis.tsx:1634`; tests in `useAnalysisBoardArrows.test.ts`/`tacticOrientation.test.ts`; CHANGELOG/README changed in the diff |

**Score:** 11/11 decisions verified, 0 PRESENT_BEHAVIOR_UNVERIFIED. The state-transition truths (D-05, D-06, D-07) have behavioral evidence from the real-board harness, not just symbol presence.

### Required Artifacts / Key Links

| Artifact / Link | Status | Details |
|---|---|---|
| `lib/explainBar.ts` (exports eligibleExplainMarker, usableExplainLines, chooseExplainOrientation, resolveExplainBarState, types) | VERIFIED | Substantive pure rules, imported by the hook and tests |
| `hooks/analysis/useExplainBar.ts` | VERIFIED | Called once at `Analysis.tsx:1284`, result spread into three `<ExplainBar>` placements |
| `components/analysis/ExplainBar.tsx` | VERIFIED | Three placements, wired at `:2109`, `:2557`, `:2693` |
| `PendingFlaw.enter` + relocated `findFocusedFlaw` in `analysisTactics.ts` | VERIFIED | Page uses it at `Analysis.tsx:495` |
| Key link: second `useTacticLines` observer, same key | WIRED | `useExplainBar.ts` |
| Key link: `pendingFlaw.enter` -> graft effect -> `goToNode(rootNodeId)` | WIRED | `useAnalysisRouteSeeding.ts` |
| Key link: `footer={<ExplainBar placement="desktop" ...>}` | WIRED | `Analysis.tsx:2693`, `MovesCard` renders `{footer}` |

### Data-Flow (Level 4)

`flawMarkers` come from `gameData.flaw_markers` (live API), tactic lines from `libraryApi.getTacticLines` through `useTacticLines`; no hardcoded or static fallbacks. FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Phase test files | `npx vitest run` on explainBar, useExplainBar, ExplainBar, useLibrary, useAnalysisBoardArrows, tacticOrientation, Analysis tests | 7 files, 194 tests pass | PASS |
| Backend untouched | `git diff --stat main...HEAD -- app tests` | empty | PASS |
| Full gate (lint, `tsc -b`, 345 files / 5797 tests, knip) | Not re-run by me; reported clean by the orchestrator | n/a | Relied on, not independently re-run |

### Requirements Coverage

D-01..D-11 each accounted for above against 245-CONTEXT.md. No REQUIREMENTS.md entries exist for this phase (expected).

### Anti-Patterns

No `TBD`/`FIXME`/`XXX` in files changed by the phase. No stubs: every component renders real state. `git status` clean.

### Review Warnings Assessed (not gaps)

- **WR-01 (got-it precedence at fork ply P-1):** Real, but not a breach of a locked decision. CONTEXT explicitly says to "follow `findFocusedFlaw` semantics" for what the bar shows at a missed line's fork node, and D-07 says re-entering an open line shows Got it. The edge is documented in `explainBar.ts` rule 1b; P-1's Explain is reachable via Got it then Back. D-03's "eligible flaw ply" wording is in mild tension with it. Recorded as a non-blocking warning and listed under human_verification for an owner call.
- **WR-02 (stuck `pendingFlaw` after null/404 or empty-PV fetch hides the bar elsewhere):** Real robustness gap, but not reachable from Explain itself: the bar only offers Explain when `usableExplainLines` confirms the line is graftable (which is why that function exists), so an Explain-originated pending can't get stuck. It requires a chip click or deep-link `initialTactic` on a ply whose `game_flaws` row has drifted or whose PV is empty. The 404-to-null change in 245-02 makes this path silent where it used to set `isError` (the pre-existing stuck-pending behavior on other errors was already there). Rare edge, not a locked-decision violation. Recommend a small follow-up (clear `pendingFlaw` when `contextualTacticData === null` in the graft effect).
- **IN-01 / IN-02:** accepted as info (5-minute cached null; prefetch during Jump animation). Neither affects a must-have.

All four dispositions remain `open` in 245-REVIEW-DISPOSITION.md; the owner should triage them.

## Gaps Summary

No gaps. Every locked decision D-01..D-11 and every plan must-have is implemented, wired into `Analysis.tsx`, and covered by behavioral tests that exercise the real board state transitions. Status is `human_needed` solely because visual fit (360px mobile, mid layout), the plain blue arrow on non-motif lines, sound behavior and the WR-01 product call require a browser. Per the owner's preference, these should be run by Claude via Claude-in-Chrome during `/gsd-verify-work`.

---

_Verified: 2026-11-05_
_Verifier: Claude (gsd-verifier)_
