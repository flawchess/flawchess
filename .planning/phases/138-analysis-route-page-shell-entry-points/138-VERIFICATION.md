---
phase: 138-analysis-route-page-shell-entry-points
verified: 2026-06-26T19:25:00Z
status: human_needed
score: 1/4 must-haves verified
behavior_unverified: 3
overrides_applied: 0
deferred:
  - truth: "SC#2 game-review-ply clause: Navigating from a game-review ply pre-loads the board with the correct position and context"
    addressed_in: "Phase 139"
    evidence: "Phase 139 SC#1: 'Opening /analysis?game_id=X&flaw_ply=Y displays the flaw position with the stored PV as the initial mainline'; CONTEXT.md D-03 explicitly descopes game-review-ply from Phase 138 and folds it into Phase 139"
  - truth: "Phase goal 'arriving pre-loaded from tactic cards': tactic-card entry-point repointing"
    addressed_in: "Phase 139"
    evidence: "Phase 139 SC#4: 'TacticLineExplorer.tsx and useTacticLine.ts are deleted; all tactic Explore entry points navigate to /analysis?...'; CONTEXT.md deferred section documents this explicitly"
behavior_unverified_items:
  - truth: "SC#1 — The /analysis page is accessible to authenticated users; network inspection confirms no stockfish WASM/JS fetch on any other route (lazy-load boundary enforced)"
    test: "Navigate to /library, /openings, /endgames with DevTools Network tab open; then navigate to /analysis"
    expected: "No stockfish-18-lite-single.js or .wasm request on /library, /openings, /endgames; engine JS + WASM fetch fires exactly once on /analysis"
    why_human: "React.lazy code-split architecture is statically verified, but the absence of WASM fetch on non-analysis routes is a runtime network observation that grep cannot confirm"
  - truth: "SC#3 — The 'Loading engine...' state is shown in the eval area while the WASM initializes; the board and move stepper remain interactive during this window"
    test: "Load /analysis on a real device (including iOS Safari / low-end Android); observe the eval area immediately after page load, then interact with the board and controls before the engine readies"
    expected: "Eval area shows 'Loading engine...' with spinner; board drag/drop and click-to-click move input work immediately; BoardControls buttons respond; engine eval appears within ~3s"
    why_human: "The code structure (board rendered regardless of isReady) and tests verify the DOM invariant, but actual input interactivity during WASM initialization is a runtime behavioral invariant not exercised by jsdom tests"
  - truth: "SC#4 — window.crossOriginIsolated === false on /analysis; the full Google OAuth login flow completes without error from any page"
    test: "Open /analysis in a browser, run console.log(window.crossOriginIsolated). Then sign out and complete the full Google OAuth sign-in flow from /analysis and one other page (e.g. /openings)"
    expected: "crossOriginIsolated is false; OAuth popup opens, completes, and user is signed in without error"
    why_human: "No COOP/COEP headers are added in this phase (verified by code), but window.crossOriginIsolated and OAuth completion are browser runtime observations that cannot be confirmed by static analysis"
human_verification:
  - test: "SC#1 — Lazy-load boundary: verify no stockfish bundle on other routes"
    expected: "DevTools Network: no stockfish-18-lite-single.js / .wasm on /library, /openings, /endgames; both files fetch exactly once on first /analysis visit"
    why_human: "Network tab is a browser runtime observation; React.lazy architecture is code-verified but the absence of bundle loading elsewhere requires live inspection"
  - test: "SC#3 — On-device interactivity during WASM init (including iOS Safari / low-end Android)"
    expected: "'Loading engine...' spinner appears immediately in the eval area; board drag-drop and click-to-click moves work; BoardControls Back/Forward/Reset/Flip/engine-toggle all respond; EngineLines appear within ~3s"
    why_human: "jsdom test proves the DOM invariant (board rendered while isReady=false) but cannot verify touch/click interactivity or actual WASM init timing on real devices"
  - test: "SC#4 — crossOriginIsolated check and full Google OAuth flow"
    expected: "console.log(window.crossOriginIsolated) returns false on /analysis; complete sign-in via Google OAuth from /analysis and another page without errors"
    why_human: "PLAT-01 CI guard (Phase 136) already verifies no COOP/COEP headers in the response, but window.crossOriginIsolated and OAuth popup completion are observable only in a real browser session"
  - test: "SC#2 — opening-position entry end-to-end: click 'Analyze position' on Openings Explorer (desktop and mobile) from a non-start position"
    expected: "Browser navigates to /analysis?fen=<url-encoded FEN>; the analysis board loads that position (not the start position); URL FEN matches the Explorer position that was showing"
    why_human: "Code and unit tests verify the encoder and button wiring; the end-to-end navigation flow (board actually rendering the correct position after click) benefits from a live smoke test"
---

# Phase 138: `/analysis` Route + Page Shell + Entry Points — Verification Report

**Phase Goal:** Users can navigate to a standalone `/analysis` page lazy-loaded on demand, arriving pre-loaded from tactic cards, game-review plies, and opening positions
**Verified:** 2026-06-26T19:25:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Scope Assessment

The ROADMAP phase goal and SC#2 mention "tactic cards, game-review plies, and opening positions" as entry sources. CONTEXT.md D-03 (locked decision) explicitly descopes both the game-review-ply entry and tactic-card repointing to Phase 139. CONTEXT.md D-04 notes the ROADMAP wording was left untouched intentionally. Phase 139's ROADMAP success criteria explicitly cover `?game_id=X&flaw_ply=Y` (SC#1) and retiring all tactic "Explore" entry points (SC#4). **These are deliberate deferred items, not implementation gaps.**

What Phase 138 delivers: `/analysis` page shell + React.lazy route wiring + opening-position entry point only.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC#1: `/analysis` accessible to authenticated users; no stockfish fetch on other routes (lazy boundary) | PRESENT_BEHAVIOR_UNVERIFIED | Auth gate: `App.tsx:654` inside `<Route element={<ProtectedLayout />}>`, not in `ImportRequiredRoute`. Lazy boundary: `App.tsx:42` `const AnalysisPage = lazy(() => import('./pages/Analysis'))` — app's first `React.lazy`. Architecture sufficient; network-tab confirmation is browser-only |
| 2 | SC#2: Opening position entry pre-loads the analysis board with correct FEN encoded in URL params | VERIFIED | `analysisUrl.ts` exports `buildAnalysisUrl(fen)` using `encodeURIComponent`; `Openings.tsx:566-568` `handleAnalyzePosition` calls `navigate(buildAnalysisUrl(chess.position))`; both desktop (`btn-analyze-position`) and mobile (`btn-analyze-position-mobile`) buttons wired on `activeTab === 'explorer'`; `Analysis.tsx:64-71` FEN-guard reads param and seeds `useAnalysisBoard`; 9/9 automated tests pass |
| 3 | SC#3: "Loading engine..." shown in eval area during WASM init; board and move stepper remain interactive | PRESENT_BEHAVIOR_UNVERIFIED | `Analysis.tsx:105` `engineLoading = engineEnabled && !engine.isReady`; `Analysis.tsx:192-199` conditionally renders `data-testid="analysis-engine-loading"` with "Loading engine..." text; board (`analysis-board`) is always rendered regardless of `isReady`. Test case 4 (jsdom) asserts this DOM invariant and passes. On-device interactivity during actual WASM init requires browser UAT |
| 4 | SC#4: `window.crossOriginIsolated === false` on `/analysis`; Google OAuth flow completes from any page | PRESENT_BEHAVIOR_UNVERIFIED | No COOP/COEP headers added in this phase (verified by code review, threat model T-138-03, and Phase 136 PLAT-01 CI guard). `window.crossOriginIsolated` value and OAuth flow completion are browser runtime observations |

**Score:** 1/4 truths verified (3 present, behavior-unverified — browser runtime observations; 1 confirmed deferred to Phase 139)

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | SC#2 game-review-ply clause: navigating from a game-review ply pre-loads the board | Phase 139 | Phase 139 SC#1: "Opening `/analysis?game_id=X&flaw_ply=Y` displays the flaw position"; CONTEXT.md D-03 locks this descope |
| 2 | Phase goal "tactic cards": tactic-card entry-point repointing | Phase 139 | Phase 139 SC#4: all tactic "Explore" entry points navigate to `/analysis?...`; TacticLineExplorer retired |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/__tests__/Analysis.test.tsx` | Wave-0 test scaffold, 5 cases | VERIFIED | Exists, 5 tests pass (GREEN after Plan 02); mocks `useStockfishEngine`, does not mock `useAnalysisBoard`; jsdom shims present |
| `frontend/src/pages/Analysis.tsx` | Default-exported page shell composing hooks + components | VERIFIED | Exists (226 lines), `export default function Analysis()`, FEN-guard, engine-loading state, all components wired |
| `frontend/src/App.tsx` | First React.lazy boundary, `/analysis` route in ProtectedLayout | VERIFIED | `lazy(() => import('./pages/Analysis'))` at line 42; route at line 654 inside ProtectedLayout; `'/analysis': 'Analysis'` in ROUTE_TITLES; no nav item |
| `frontend/src/lib/analysisUrl.ts` | `buildAnalysisUrl` pure encoder | VERIFIED | Exports `buildAnalysisUrl` using `encodeURIComponent`; named constants `ANALYSIS_PATH`, `FEN_PARAM` |
| `frontend/src/lib/analysisUrl.test.ts` | Unit tests for FEN url-encoding | VERIFIED | 4 tests pass; asserts `%20`, `%2F`, round-trip equality with `encodeURIComponent` |
| `frontend/src/pages/Openings.tsx` | "Analyze position" button on desktop + mobile Explorer | VERIFIED | Both `btn-analyze-position` and `btn-analyze-position-mobile` present; `variant="brand-outline"`, `Microscope` icon, `handleAnalyzePosition` callback, both guarded by `activeTab === 'explorer'` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `App.tsx` | `pages/Analysis.tsx` | `lazy(() => import('./pages/Analysis'))` | WIRED | Line 42; AnalysisPage key'd by fen param (Pitfall 2); Suspense fallback `data-testid="analysis-loading"` |
| `pages/Analysis.tsx` | `hooks/useStockfishEngine.ts` | `useStockfishEngine({ fen: engineEnabled ? position : null, enabled: engineEnabled })` | WIRED | Lines 99-102; unconditional hook call |
| `pages/Analysis.tsx` | `hooks/useAnalysisBoard.ts` | `useAnalysisBoard(guardedFen)` | WIRED | Line 91; FEN-guarded root seed |
| `pages/Openings.tsx` | `lib/analysisUrl.ts` | `navigate(buildAnalysisUrl(chess.position))` | WIRED | Lines 58, 566-568 |
| `Analysis.tsx` (EvalBar) | `engine.evalCp/evalMate/depth` | Props from `useStockfishEngine` return | WIRED | Lines 135-139 |
| `Analysis.tsx` (EngineLines) | `engine.pvLines/depth/isAnalyzing` + `currentPly` | Props from `useStockfishEngine` + `fenToRootPly(position)` (CR-01 fix) | WIRED | Lines 203-209 |
| `Analysis.tsx` (VariationTree) | `nodes/mainLine/currentNodeId/rootPly` from `useAnalysisBoard` | Props destructured from hook return | WIRED | Lines 212-218 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `Analysis.tsx` | `position`, `nodes`, `mainLine` | `useAnalysisBoard(guardedFen)` — in-memory branching tree | Yes (real board state from hook) | FLOWING |
| `Analysis.tsx` | `engine.evalCp`, `engine.pvLines` | `useStockfishEngine({ fen: position, enabled })` — WASM UCI engine | Yes (live engine output in browser) | FLOWING |
| `Openings.tsx` "Analyze position" | `chess.position` | Live Explorer board state from `useChessGame` | Yes (current Explorer FEN) | FLOWING |

---

### Behavioral Spot-Checks

All automated test assertions run via `npm test`:

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Analysis page shell renders with required testids | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | 5/5 pass | PASS |
| `?fen=` seeds the board from a valid opening FEN | Test case 2 in Analysis.test.tsx | PASS | PASS |
| Malformed `?fen=` degrades to start without throwing | Test case 3 in Analysis.test.tsx | PASS | PASS |
| `analysis-engine-loading` shown while `isReady=false`; `analysis-board` present | Test case 4 in Analysis.test.tsx | PASS | PASS |
| Engine ready hides loading chrome | Test case 5 in Analysis.test.tsx | PASS | PASS |
| `buildAnalysisUrl` encodes spaces as `%20`, slashes as `%2F` | `npm test -- --run src/lib/analysisUrl.test.ts` | 4/4 pass | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ROUTE-01 | Plans 02, 03 | Standalone `/analysis` page, lazy-loaded, engine bundle on this route only | SATISFIED | `App.tsx` lazy import + ProtectedLayout route; React.lazy code-split architecture confirmed |
| ROUTE-02 | Plans 02, 03 | Analysis board pre-loaded from tactic card, game-review ply, opening position | PARTIAL (Phase 138 scope: opening position only; remainder deferred to Phase 139 per D-03) | Opening-position entry: fully implemented and tested. Game-review-ply + tactic-card: Phase 139. REQUIREMENTS.md marks ROUTE-02 "Complete" prematurely — this is a documentation artefact (D-04 defers the REQUIREMENTS.md cleanup to milestone close or when Phase 139 absorbs the entry) |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No TBD/FIXME/XXX markers in phase files | — | Clean |

No debt markers, no stubs, no empty handlers, no hardcoded empty data in rendering paths.

**Code review follow-up (fixed before verification):** The 138-REVIEW.md identified CR-01 (EngineLines startPly anchored to static entry FEN, desyncing after navigation) and WR-01 (canGoForward hardcoded true). Both were fixed in commit `a34966ef` before this verification. The current `Analysis.tsx` uses `currentPly = fenToRootPly(position)` for EngineLines and a `useMemo`-derived `canGoForward` from the nodes map. Remaining INFO-level notes (IN-01 misleading comment, IN-02 no chunk-load-error boundary, IN-03 no accessible name on board wrapper, IN-04 bare FEN field indices) are non-blocking and carry no stub/debt markers.

---

### Human Verification Required

#### 1. SC#1 — Lazy-load boundary: no stockfish bundle on other routes

**Test:** Open DevTools Network tab. Visit `/library`, `/openings`, `/endgames`. Then navigate to `/analysis`.
**Expected:** `stockfish-18-lite-single.js` and `stockfish-18-lite-single.wasm` (or equivalent) do not appear in the network log for the non-analysis routes. Both files fetch exactly once on the first `/analysis` visit.
**Why human:** React.lazy architecture guarantees the code-split at build time, but the absence of bundle loading on non-analysis routes is a runtime network observation.

#### 2. SC#3 — On-device interactivity during WASM init (iOS Safari / low-end Android)

**Test:** Load `/analysis` fresh (no cache) on a real mobile device. Immediately after the page appears, attempt to drag a piece on the board, click a square, and click the Back/Forward/Flip buttons before the engine is ready.
**Expected:** "Loading engine..." spinner appears in the eval panel. Board responds to piece moves immediately. All BoardControls buttons are clickable. EngineLines appear within approximately 3 seconds. Text-sm floor visually verified on EvalBar, EngineLines, VariationTree.
**Why human:** jsdom tests confirm the DOM invariant (board rendered while `isReady=false`), but actual touch input interactivity during WASM initialization is not testable in jsdom.

#### 3. SC#4 — crossOriginIsolated check and Google OAuth flow

**Test:** On `/analysis`, run `window.crossOriginIsolated` in the browser console. Then sign out and complete the full Google OAuth login flow from `/analysis` and from `/openings`.
**Expected:** `window.crossOriginIsolated` returns `false`. OAuth popup opens normally, completes, and the user is signed in without errors or blocked popups.
**Why human:** No COOP/COEP headers are added in this phase (code-verified, Phase 136 PLAT-01 CI guard active), but the `window.crossOriginIsolated` value and OAuth popup behavior are browser runtime observations.

#### 4. SC#2 — Opening-position entry end-to-end smoke test

**Test:** On the Openings Explorer tab (desktop and mobile), navigate to a non-start position (e.g. after 1. e4 e5), then click "Analyze position."
**Expected:** URL changes to `/analysis?fen=<url-encoded FEN>`. The analysis board shows the Explorer position (not the start position). The FEN in the URL matches the position that was showing in the Explorer.
**Why human:** Code and unit tests verify the encoder and button wiring; the live end-to-end navigation (board rendering the correct position) benefits from a browser smoke test.

---

### Gaps Summary

No implementation gaps found. All Phase 138 planned deliverables are present, substantive, and wired:
- `Analysis.tsx` (default export, FEN-guard, engine-loading state, all components wired, CR-01/WR-01 fixed)
- `App.tsx` (first React.lazy boundary, route inside ProtectedLayout, key-by-fen remount)
- `analysisUrl.ts` + `analysisUrl.test.ts` (pure encoder, unit-tested)
- `Openings.tsx` (both desktop and mobile "Analyze position" buttons, explorer-tab-gated)

The three unverified truths (SC#1, SC#3, SC#4) are browser runtime observations that the plans explicitly designated as MANUAL UAT items. They are not implementation gaps — the code is wired correctly.

---

_Verified: 2026-06-26T19:25:00Z_
_Verifier: Claude (gsd-verifier)_
