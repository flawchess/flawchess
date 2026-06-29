---
phase: 139-tactic-mode-overlay-phase-135-subsume
verified: 2026-06-26T22:15:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "next/prev-tactic rail present and functional in tactic mode"
    reason: "Cross-flaw rail explicitly descoped by user via D-01 in 139-CONTEXT.md before execution. SCOPE AMENDMENT flagged for milestone close (ROADMAP SC#2 / REQUIREMENTS TACTIC-02 still name the rail; CONTEXT.md instructs do NOT silently edit them). The remaining SC#2 sub-features — motif badge, missed/allowed toggle, depth-to-punchline counter — are all present and verified. SC#3 'tactic-rail state on route re-entry' reinterpreted per D-01 as correct board re-seed + orientation/depth reset (Behavior D, passing)."
    accepted_by: "aimfeld"
    accepted_at: "2026-06-26T22:15:00Z"
---

# Phase 139: Tactic Mode Overlay + Phase 135 Subsume — Verification Report

**Phase Goal:** Tactic mode on the analysis board replicates every Phase 135 TacticLineExplorer behavior at parity; the standalone modal and its hook are retired and all former entry points repointed
**Verified:** 2026-06-26T22:15:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Opening `/analysis?game_id=X&flaw_ply=Y` displays the flaw position with the stored PV as the initial mainline (D-5); the live engine takes over immediately when the user deviates from the stored line | VERIFIED | Analysis.tsx reads `game_id`/`flaw_ply` with NaN guards; `useTacticLines` called; `useEffect` keyed on `[positionFen, resolvedOrientation, isTacticMode]` calls `loadMainLine(moves, positionFen)` + `goToRoot()`; arrow logic gates stored-PV arrows on `onMainLine`; live engine arrows used off-line. Behaviors A–D all pass (4/4 tests). |
| 2 | The motif badge, missed/allowed orientation toggle, depth-to-punchline counter, and next/prev-tactic rail are all present and functional in tactic mode | FAILED | Motif badge (`TacticMotifChip`, `tactic-toggle-missed`/`tactic-toggle-allowed`), missed/allowed toggle (`handleOrientationChange`), and depth counter (`tactic-depth-counter`, `toDisplayDepthForOrientation`) are all present and verified. The **next/prev-tactic rail is absent** — explicitly descoped by user via D-01 in CONTEXT.md. |
| 3 | All four Phase 135 regression behaviors pass before any code deletion: depth-0 highlight (no empty-PV crash), missed/allowed +1 ply offset via `tacticDepth.ts`, real-game-ply move numbering, tactic-rail state on route re-entry | VERIFIED | `Analysis.tactic.test.tsx` — 4/4 tests pass: Behavior A (depth-0 overlay + move list, no crash), Behavior B (allowed display depth 2 for raw 0, `toDisplayDepthForOrientation` confirmed), Behavior C (`moveLabel(42,0)` → "22.", not "1."), Behavior D (orientation toggle re-seeds move list, no stale mainline). "Tactic-rail state" reinterpreted per D-01 as re-seed on change. Deletion in Plan 03 depends_on 01+02, so tests precede deletion. |
| 4 | `TacticLineExplorer.tsx` and `useTacticLine.ts` are deleted; all tactic "Explore" entry points navigate to `/analysis?...`; `npm run knip` passes clean | VERIFIED | `TacticLineExplorer.tsx`, `useTacticLine.ts`, and both their `__tests__` files are gone (confirmed). No production import of either name remains. FlawCard Explore: `navigate('/analysis?game_id=' + flaw.game_id + '&flaw_ply=' + flaw.ply + '&orientation=' + ori)`. LibraryGameCard Explore: navigate on desktop + mobile (two testid instances). `npm run knip` exits 0. |

**Score:** 3/4 truths verified (1 failed — intentional user descope of next/prev-tactic rail)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/analysis/TacticModeOverlay.tsx` | Tactic chrome: motif chips, eval badge, depth counter, arrow-source toggle, HorizontalMoveList + `buildRootArrows`/`buildPvArrow` exports | VERIFIED | 447 lines; exports `isBlackToMove`, `buildRootArrows`, `buildPvArrow`, `TacticModeOverlay`; all testids present; no location.state; uses `toDisplayDepthForOrientation`, `resolveVisibleTactic`, `moveLabel` |
| `frontend/src/pages/Analysis.tsx` | Tactic-mode wiring: param read, useTacticLines, loadMainLine seeding, orientation/arrow-source state, board arrow selection, overlay render | VERIFIED | Reads `game_id`/`flaw_ply`/`orientation` with guards; calls `useTacticLines(gameId, flawPly, isTacticMode)`; D-5 re-seed effect; D-03 arrow logic; `TacticModeOverlay` rendered when `isTacticMode && tacticData != null` |
| `frontend/src/pages/__tests__/Analysis.tactic.test.tsx` | 4 regression behavior tests (A–D) as deletion gate | VERIFIED | 305 lines, 4 tests, all 4 pass; mocks useTacticLines/useStockfishEngine; useAnalysisBoard runs for real; JSDOM shims in place |
| `frontend/src/hooks/useLibrary.ts` (useTacticLines) | Still has live caller after modal deletion | VERIFIED | Called by `Analysis.tsx:146`; knip confirms live; no dead-export penalty |
| `frontend/src/components/library/TacticLineExplorer.tsx` | Deleted | VERIFIED | File does not exist |
| `frontend/src/hooks/useTacticLine.ts` | Deleted | VERIFIED | File does not exist |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/pages/Analysis.tsx` | `frontend/src/hooks/useLibrary.ts` | `useTacticLines(gameId, flawPly, isTacticMode)` | WIRED | Line 146: `const { data: tacticData } = useTacticLines(gameId, flawPly, isTacticMode)` |
| `frontend/src/pages/Analysis.tsx` | `frontend/src/hooks/useAnalysisBoard.ts` | `loadMainLine(activeMoves, positionFen)` seeds stored PV; `goToRoot()` lands at decision position | WIRED | Lines 195–196 in re-seed effect; `goToRoot` added to hook (line 5 in test confirms it) |
| `frontend/src/components/analysis/TacticModeOverlay.tsx` | `frontend/src/lib/tacticDepth.ts` | `toDisplayDepthForOrientation` for depth labels | WIRED | Line 314: `const rootDisplayDepth = toDisplayDepthForOrientation(activeDepthRaw, resolvedOrientation)` |
| `frontend/src/components/library/FlawCard.tsx` | `react-router-dom useNavigate` | `navigate('/analysis?game_id=' + ... '&flaw_ply=' + ... '&orientation=' + ori)` | WIRED | Lines 260–262; no `TacticLineExplorer` import or `exploreOpen` state remains |
| `frontend/src/components/results/LibraryGameCard.tsx` | `react-router-dom useNavigate` | Explore → /analysis tactic params; Analyze position → /analysis?fen=encoded FEN | WIRED | Lines 909–916 (desktop), 1028–1035 (mobile) for Explore; lines 947, 1066 for Analyze position |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `TacticModeOverlay.tsx` | `data: TacticLinesResponse` | `useTacticLines` (TanStack Query, tactic-lines endpoint) via props from `Analysis.tsx` | Yes — real API fetch when `isTacticMode`; enabled guard prevents spurious calls | FLOWING |
| `Analysis.tsx` | `tacticData` | `useTacticLines(gameId, flawPly, isTacticMode)` → real tactic-lines endpoint | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 4 regression behaviors (A–D) | `cd frontend && npm test -- --run Analysis.tactic` | 4 passed, 0 failed | PASS |
| goToRoot unit test | `cd frontend && npm test -- --run useAnalysisBoard` | 7 passed (6 original + 1 goToRoot) | PASS |
| Full frontend suite post-deletion | `cd frontend && npm test -- --run` | 1196 passed, 103 test files | PASS |
| knip (dead exports after deletion) | `cd frontend && npm run knip` | exit 0, no output | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TACTIC-01 | Plan 01 | Board opens at flaw position with stored PV mainline; live engine on deviation | SATISFIED | SC#1 VERIFIED; Behavior A–D tests pass |
| TACTIC-02 | Plan 01 | Motif badge, missed/allowed framing, depth counter, next/prev rail | PARTIALLY SATISFIED | Motif/toggle/depth VERIFIED; rail missing (user-descoped D-01) |
| TACTIC-03 | Plans 02+03 | Modal retired; all entry points repointed; knip clean | SATISFIED | SC#4 VERIFIED; deletions confirmed; knip passes |

### Anti-Patterns Found

No anti-patterns found. No TBD/FIXME/XXX markers in any modified files. No stub patterns (empty returns, placeholder JSX, hardcoded static data in rendering paths). Comment-only references to `TacticLineExplorer` in surviving files are historical JSDoc context per Plan 03 SUMMARY.md decision.

### Human Verification Required

None. All automated checks pass. The one gap (missing rail) is an intentional user-descoped deviation, not a quality or visual-appearance item requiring human testing.

## Gaps Summary

One gap blocks the `passed` verdict:

**SC#2 / TACTIC-02 — next/prev-tactic rail missing**

The ROADMAP SC#2 and REQUIREMENTS TACTIC-02 both specify a "next/prev-tactic rail" enabling cross-flaw navigation. No such rail exists in the codebase. The user explicitly descoped it via **D-01** in `139-CONTEXT.md` before execution began:

> "D-01: No cross-flaw next/prev-tactic rail. Opening Explore passes a SINGLE flaw's data — its missed PV and/or allowed PV, both already returned by the existing tactic-lines response for one game_id+flaw_ply."

The CONTEXT.md documents this as a "SCOPE AMENDMENT (flag at milestone close)" and explicitly says "do NOT silently edit ROADMAP/REQUIREMENTS." This is an intentional deviation with user approval, not an oversight or incomplete implementation.

**This looks intentional.** To formally accept this descoping, add to VERIFICATION.md frontmatter:

```yaml
overrides:
  - must_have: "next/prev-tactic rail present and functional in tactic mode"
    reason: "Cross-flaw rail explicitly descoped by user via D-01 in 139-CONTEXT.md before execution. SCOPE AMENDMENT flagged for milestone close. The missed/allowed toggle within a single flaw satisfies the in-tactic navigation need for v1."
    accepted_by: "aimfeld"
    accepted_at: "2026-06-26T22:15:00Z"
```

With that override applied, all 4 SCs are satisfied and status becomes `passed`.

---

_Verified: 2026-06-26T22:15:00Z_
_Verifier: Claude (gsd-verifier)_
