---
phase: 139-tactic-mode-overlay-phase-135-subsume
plan: "02"
subsystem: frontend
status: complete
tags: [tactic-mode, entry-points, navigation, analyze-position, phase-135-repoint]
dependency_graph:
  requires:
    - "139-01: TacticModeOverlay + Analysis.tsx tactic wiring"
    - "135: TacticLineExplorer (source being retired)"
  provides:
    - "FlawCard Explore repointed to /analysis?game_id=...&flaw_ply=...&orientation=..."
    - "LibraryGameCard Explore repointed to /analysis tactic mode (desktop + mobile)"
    - "LibraryGameCard D-02 'Analyze position' button (desktop + mobile) → /analysis?fen=..."
  affects:
    - "139-03: TacticLineExplorer deletion (now safe — no remaining callers)"
tech_stack:
  added:
    - "useNavigate (react-router-dom) in FlawCard + LibraryGameCard"
    - "Activity icon (lucide-react) for Analyze position button in LibraryGameCard"
  patterns:
    - "D-01: plain URL params only (game_id/flaw_ply/orientation) — no location.state"
    - "D-02: free-play ?fen= entry from reconstructed scrubbed-ply FEN"
    - "D-04: browser Back for return-to-game — no modal stacking"
    - "CLAUDE.md parity: both desktop + mobile receive the same button additions"
key_files:
  modified:
    - "frontend/src/components/library/FlawCard.tsx"
    - "frontend/src/components/results/LibraryGameCard.tsx"
    - "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx"
decisions:
  - "FlawCard ori = 'missed' when missed_tactic_motif present, else 'allowed'"
  - "LibraryGameCard exploreOri derived from selectedFlaw (parked marker) — same precedence rule"
  - "Activity icon chosen for Analyze position (analysis/charting semantics, not yet used elsewhere in these files)"
  - "MemoryRouter added to LibraryGameCard.test.tsx renders so useNavigate works in jsdom (Rule 1 auto-fix)"
metrics:
  duration: "20min"
  completed: "2026-06-26"
  tasks: 2
  files: 3
---

# Phase 139 Plan 02: Entry-Point Repoint Summary

One-liner: FlawCard and LibraryGameCard Explore buttons repointed to /analysis tactic mode via plain URL params; new desktop+mobile "Analyze position" button deep-links to /analysis?fen= free-play; no modal, no location.state remain.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Repoint FlawCard Explore to /analysis (drop modal) | c8d2e033 | FlawCard.tsx |
| 2 | Repoint LibraryGameCard Explore + add D-02 Analyze position button | 45b1b2fa | LibraryGameCard.tsx, LibraryGameCard.test.tsx |

## What Was Built

### Task 1 — FlawCard.tsx

- Added `useNavigate` from `react-router-dom`.
- Removed `import { TacticLineExplorer }` and the `exploreOpen` state.
- Added `const ori = flaw.missed_tactic_motif != null ? 'missed' : 'allowed'` for orientation derivation.
- Explore button `onClick` now navigates to `/analysis?game_id=${flaw.game_id}&flaw_ply=${flaw.ply}&orientation=${ori}`.
- Removed the `{isTagged && <TacticLineExplorer .../>}` block entirely.
- `data-testid="flaw-btn-explore"`, `variant="brand-outline"`, `aria-label`, and `isTagged` render guard all preserved.
- Two TacticLineExplorer comment references in unrelated JSDoc cleaned up.

### Task 2 — LibraryGameCard.tsx + test fix

**LibraryGameCard.tsx:**
- Added `useNavigate` and `Activity` (lucide-react) imports; removed `TacticLineExplorer` import.
- Removed `exploreOpen` state.
- Added `const exploreOri = selectedFlaw?.missed_tactic_motif != null ? 'missed' : 'allowed'` after `isTaggedFlaw`.
- `renderDesktopExploreButton` restructured into a `flex gap-2` row:
  - Left slot (`flex-1`): Explore button; enabled/disabled with tooltip as before; `onClick` now navigates to `/analysis?game_id=...&flaw_ply=${hoverPly}&orientation=${exploreOri}`.
  - Right slot (`flex-1`): new "Analyze position" button (`data-testid="game-card-btn-analyze-position"`, `aria-label="Analyze this position"`, `variant="brand-outline"`, `Activity` icon); `disabled={boardFen == null}`; `onClick` navigates to `/analysis?fen=${encodeURIComponent(boardFen)}`.
- Mobile Explore block (`md:hidden`) similarly restructured into `flex gap-2`:
  - Same Explore (with navigate) and Analyze position button side-by-side.
  - `data-testid="game-card-btn-analyze-position"` present on both surfaces (acceptance criterion ≥ 2).
- Removed `{isTaggedFlaw && hoverPly != null && <TacticLineExplorer .../>}` block.

**LibraryGameCard.test.tsx (Rule 1 auto-fix):**
- Added `import { MemoryRouter }` from `react-router-dom`.
- Added `renderCard(ui)` helper wrapping children in `MemoryRouter`.
- All 9 test `render(` calls changed to `renderCard(` so `useNavigate` resolves without a real Router.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] LibraryGameCard tests crash with "useNavigate() may be used only in the context of a Router"**
- **Found during:** Task 2 test run
- **Issue:** Adding `useNavigate` to `LibraryGameCard` caused all 9 existing tests in `LibraryGameCard.test.tsx` to throw because jsdom renders have no Router context.
- **Fix:** Added `MemoryRouter` via a `renderCard` helper; replaced all 9 `render(` call sites. No assertion changes needed — the tests verify chip rendering and platform links, neither of which involves navigation.
- **Files modified:** `frontend/src/components/results/__tests__/LibraryGameCard.test.tsx`
- **Commit:** 45b1b2fa

## Test Results

```
Test Files  105 passed (105)
     Tests  1222 passed (1222)
```

All 1222 tests pass, including all 9 LibraryGameCard tests.

## Known Stubs

None. Both Explore buttons navigate to real routes with real params. The Analyze position button uses the already-reconstructed per-ply FEN from `buildPerPly`. No placeholders.

## Threat Flags

T-139-04 (Tampering: ?fen= value): `encodeURIComponent(boardFen)` applied on write. The /analysis reader already FEN-guards via chess.js (T-138-01) — no new exposure.

T-139-05 (Information Disclosure: game_id in URL): accepted per plan — game_id is the user's own library game; the /analysis route is auth-gated (ProtectedLayout).

No new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- `frontend/src/components/library/FlawCard.tsx` modified: FOUND
- `frontend/src/components/results/LibraryGameCard.tsx` modified: FOUND
- `frontend/src/components/results/__tests__/LibraryGameCard.test.tsx` modified: FOUND
- Commit c8d2e033 exists: FOUND
- Commit 45b1b2fa exists: FOUND
- `tsc -b --noEmit` exits 0: PASSED
- `npm run lint` 0 errors (3 warnings in auto-generated coverage files only): PASSED
- All 1222 tests pass: PASSED
