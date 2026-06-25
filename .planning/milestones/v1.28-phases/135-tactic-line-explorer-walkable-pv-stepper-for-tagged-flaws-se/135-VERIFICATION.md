---
phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
verified: 2026-06-25T00:30:00Z
status: passed
human_verified: 2026-06-25
human_verified_by: Adrian (attested via /gsd-ship — both browser-only behaviors confirmed working)
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open the Tactic Line Explorer on a tagged flaw on desktop and step through the missed line. Verify the depth counter decrements from the root display depth at each forward step, hits 'Payoff' when past the punchline, and that the SAN ladder highlights the current ply with the punchline colored in missed blue."
    expected: "Depth counter decrements per forward step, floors at 0 (never negative), shows 'Payoff' once past the punchline move. Punchline row in SAN ladder is colored in TAC_MISSED (blue). Current ply row has left-border highlight. Move numbers match real game ply (not restarted at 1)."
    why_human: "Depth counter decrement per ply and 'Payoff' flip are state-transition invariants. vitest covers them in isolation via useTacticLine.test.tsx (all 10 pass), but the integrated rendering path (hook -> TacticLineExplorer -> BoardControls infoSlot -> SanLadder) involves CSS visibility, actual ply walking, and the SanLadder's move-label computation anchored to flawPly — the full interaction requires a real browser or device-level rendering."
  - test: "On mobile (< 768 px viewport), click Explore on a tagged flaw card and also from the eval-chart Explore button on the game card. Confirm the Drawer renders (not Dialog), that closing the explorer from the game card leaves the Game modal open, and that the game-card Explore button shows a tooltip when no tagged flaw is parked."
    expected: "Drawer appears on mobile (D-05). Closing the explorer returns to the Game modal (D-01 stacking). Disabled Explore button on game card shows 'Park the slider on a tactic flaw to explore it' tooltip (D-02)."
    why_human: "D-01 stacking correctness (explorer closes, Game stays open) depends on Radix Dialog/Drawer portal layering and focus management — grep confirms separate exploreOpen state and onOpenChange={setExploreOpen} (not the parent's), but the actual Radix portal z-index stacking and focus-trap return can only be verified in a real browser. Mobile matchMedia breakpoint is mocked in jsdom tests but requires a real device for the Drawer surface."
behavior_unverified_items:
  - truth: "Depth counter decrements per forward ply and floors at 0 (never negative); isPayoff flips true once past the tactic punchline"
    test: "Navigate forward through the PV in TacticLineExplorer on a real tagged flaw and observe the depth readout in BoardControls infoSlot"
    expected: "Readout shows 'Depth: N' decreasing to 'Depth: 0' at the punchline, then 'Payoff' for payoff plies. Never shows a negative depth."
    why_human: "vitest covers this in useTacticLine.test.tsx (test 6: displayDepth decrements per ply, floors at 0; test 7: isPayoff false at/before punchline, true after) and TacticLineExplorer.test.tsx (toggle-reset test checks depth readout shows correct root depth). However the integrated walk — hook state changes reflected in the BoardControls infoSlot span with testid tactic-depth-readout — is a state-transition invariant that fully exercises the hook->component rendering chain only in a browser."
  - truth: "The game-card Explore button (D-03) is always visible, disabled with a tooltip when the parked position is not a tagged user flaw, and opens the explorer stacked over the Game modal returning to it on close (D-01)"
    test: "In the Game modal on LibraryGameCard, park the eval-chart slider at a non-flaw ply, then park it at a tagged flaw ply. Click Explore, walk a few steps, close the explorer."
    expected: "Button always visible. At non-flaw ply: disabled with tooltip visible on hover. At tagged flaw ply: enabled, opens TacticLineExplorer. Closing explorer: Game modal stays open (D-01)."
    why_human: "The disabled-state gate (isTaggedFlaw) and tooltip appearance are conditional rendering paths (ternary wrapping in JSX). The D-01 stacking invariant — that closing TacticLineExplorer does NOT close the Game modal — depends on Radix portal layering at runtime. Code shows separate exploreOpen state and onOpenChange={setExploreOpen} (not the underlying game Dialog's closer), but focus-trap return and z-index behavior require browser verification."
---

# Phase 135: Tactic Line Explorer — Verification Report

**Phase Goal:** Turn each tagged flaw into a walkable lesson. A full-screen Dialog (desktop) / Drawer (mobile) opens a large board + linear SAN ladder + BoardControls preloaded with the stored Stockfish PV, so the user steps through both the missed line (engine PV) and the allowed line (opponent punishment). A depth counter ticks down to the tactic punchline (depth-0 move highlighted), then payoff plies show the landing. Entry points: an Explore secondary button on the flaw card (only when tagged) and on the game card (targets the selected flaw, disabled when not a tagged flaw, stacks over the Game modal and returns to it on close). Sources the two PVs from game_positions.pv (n for missed, n+1 for allowed) via a new tactic-lines endpoint; reuses tacticDepth.ts for the allowed +1 offset.

**Verified:** 2026-06-25T00:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

#### Plan 01 — Backend Contract

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /library/flaws/{game_id}/{ply}/tactic-lines returns 200 with both PVs as display-ready SAN for a tagged flaw the requester owns | VERIFIED | Route at `app/routers/library.py:363`. `test_200_shape` PASSED. `fetch_tactic_lines` converts both PVs via `_parse_pv` -> `_pv_to_san_list`. |
| 2 | Requesting another user's flaw returns 404 (not 403, no existence leak) | VERIFIED | `app/repositories/library_repository.py:2113`: `if flaw is None: return None`; route raises `HTTPException(status_code=404, detail="Flaw not found")`. `test_404_wrong_user` PASSED. |
| 3 | Missed line sourced from game_positions[ply].pv; allowed line from game_positions[ply+1].pv with the flaw move prepended | VERIFIED | `library_repository.py:2136-2155`: missed from `pos_n.pv`, allowed builds board_after_flaw from pos_n+1, prepends `flaw_move_san` at index 0. `test_missed_from_pos_n_allowed_from_pos_n_plus_1` PASSED. |
| 4 | Short PVs (tactic_depth >= PV length) and NULL PVs do not crash; the affected line returns None | VERIFIED | `_truncate_pv` uses Python slice (safe past end). `_pv_to_san_list` returns None on falsy pv. `test_short_pv_no_crash` and `test_null_pv_returns_none` PASSED. |
| 5 | Response exposes only FEN/SAN/depth/motif — never internal Zobrist hashes | VERIFIED | `TacticLinesResponse` schema (lines 425-460) has no hash fields. `test_no_hash_leak` PASSED. No `white_hash`/`black_hash`/`full_hash` in schema grep. |

#### Plan 02 — Frontend Primitives

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | ChessBoard accepts an optional id prop and falls back to 'chessboard' when omitted | VERIFIED | `ChessBoard.tsx:56`: `id?: string`; `ChessBoard.tsx:355`: `id: id ?? 'chessboard'`. `id="tactic-explorer-board"` passed in TacticLineExplorer. |
| 7 | BoardArrow supports optional label + labelColor so the large explorer board can render depth badges on arrow targets | VERIFIED | `ChessBoard.tsx:35,40`: `label?: string; labelColor?: string` on BoardArrow interface. ArrowOverlay renders SVG `<text>` badge when label is set, mirroring MiniBoard.tsx geometry with named constants. |
| 8 | useTacticLine walks a fixed SAN PV from a non-standard root FEN: goForward/goBack/goToMove update position, lastMove, currentPly | VERIFIED | `useTacticLine.ts:82-223`: hook accepts `rootFen`, initializes `new Chess(rootFen)` in replayTo, exports goForward/goBack/goToMove/reset/canGoForward/canGoBack. 10/10 vitest tests PASSED covering all navigation behaviors. |
| 9 | Depth counter decrements per forward ply and floors at 0 (never negative); isPayoff flips true once past the tactic punchline | PRESENT_BEHAVIOR_UNVERIFIED | Code: `displayDepth = Math.max(0, rootDisplayDepth - currentPly)` (line 201); `isPayoff = currentPly > tacticDepthRaw` (line 206). useTacticLine tests 6+7 pass in isolation. Integrated rendering chain (hook -> TacticLineExplorer -> infoSlot) is a state-transition invariant requiring browser verification. |
| 10 | Switching orientation resets the stepper to the root (ply 0); keyboard nav is scoped to the explorer container, not window | VERIFIED | `useTacticLine.ts:136-145`: `useEffect([moves, rootFen, orientation])` resets to ply 0 on orientation change. `useTacticLine.ts:182-194`: keydown listener attached to `containerRef.current`, not window. TacticLineExplorer.test.tsx toggle-reset test verifies depth readout shows root depth after switch. |

#### Plan 03 — Explorer + Entry Points

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 11 | Clicking Explore on a tagged flaw card opens the explorer (Dialog on desktop, Drawer on mobile per D-05) showing the missed line by default with the depth counter at the punchline | VERIFIED | `FlawCard.tsx:216-232`: Explore button (`flaw-btn-explore`) sets `exploreOpen=true`, renders `<TacticLineExplorer>`. TacticLineExplorer defaults to orientation `'missed'` (line 170). Dialog/Drawer switch verified by TacticLineExplorer.test.tsx tests 1+2 (matchMedia mock). |
| 12 | The Missed/Allowed toggle appears only when both lines exist; single-line flaws open the available one with the toggle hidden; switching resets the stepper to root | VERIFIED | `TacticLineExplorer.tsx:174-180`: `showToggle = hasMissed && hasAllowed`; `resolvedOrientation` force-selects the available line when only one exists. Toggle wrapped in `{showToggle && ...}` (line 303). `handleOrientationChange` calls `reset()` (line 259). Tests "hides toggle when only one line" and "toggle switch resets" PASSED. |
| 13 | The SAN ladder labels move numbers from the real game ply (not 1), highlights the current ply, click-jumps, and colors the depth-0 punchline | VERIFIED | `SanLadder.tsx:41-48`: `moveLabel(flawPly, index)` uses `Math.ceil((realPly + 1) / 2)`. Testid `tactic-san-move-{flawPly + i}`. `onClick={() => onGoToMove(i + 1)}`. Punchline colored via TAC_MISSED/TAC_ALLOWED when `i === tacticPlyIndex`. Current ply `border-l-2 border-brand-brown bg-brand-brown/10`. |
| 14 | Flaw cards show a dedicated button row (D-04): Explore+Game for tagged, Game-only for untagged, both brand-outline, on BOTH mobile and desktop | VERIFIED | `FlawCard.tsx:214-265`: `buttonRow` JSX renders `flaw-btn-explore` only when `isTagged`. Rendered in `sm:hidden` (line 445) AND `hidden sm:block` (line 465) wrappers. Tests at lines 517-541 assert Explore+Game for tagged, Game-only for untagged. |
| 15 | The game-card Explore button (D-03) is always visible, disabled with a tooltip when the parked position is not a tagged user flaw, and opens the explorer stacked over the Game modal returning to it on close (D-01) | PRESENT_BEHAVIOR_UNVERIFIED | Code: `LibraryGameCard.tsx:953-979` (mobile) and `1073-1095` (desktop): button always rendered, enabled when `isTaggedFlaw`, disabled+Tooltip otherwise. Separate `exploreOpen` state (line 222); `onOpenChange={setExploreOpen}` does not close parent Game modal. D-01 stacking correctness (Radix portal z-index, focus-trap return) requires browser verification. |

**Score:** 15/15 truths verified (13 VERIFIED, 2 PRESENT_BEHAVIOR_UNVERIFIED — code present and wired, state-transition/stacking invariants not exercised in automation)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/library.py` | TacticLinesResponse Pydantic model | VERIFIED | Line 425: `class TacticLinesResponse(BaseModel)` with all required fields |
| `app/repositories/library_repository.py` | fetch_tactic_lines() + PAYOFF_MAX_PLIES + PV->SAN helpers | VERIFIED | `PAYOFF_MAX_PLIES = 3` at line 88; `_pv_to_san_list` at line 2043; `_truncate_pv` at line 2060; `fetch_tactic_lines` at line 2074 |
| `app/routers/library.py` | GET /flaws/{game_id}/{ply}/tactic-lines route | VERIFIED | Line 363: `@router.get("/flaws/{game_id}/{ply}/tactic-lines", ...)` — relative path, no prefix duplication |
| `tests/routers/test_library_tactic_lines.py` | Endpoint 200/401/404/IDOR coverage | VERIFIED | 5 tests covering all required scenarios, all PASS |
| `tests/repositories/test_library_tactic_lines_repo.py` | PV anchoring, offset, short-PV, NULL-PV unit coverage | VERIFIED | 5 tests covering all required repository behaviors, all PASS |
| `frontend/src/components/board/ChessBoard.tsx` | Optional id prop + label/labelColor on BoardArrow | VERIFIED | `id?: string` at line 56; `label?: string`/`labelColor?: string` at lines 35/40; `id ?? 'chessboard'` at line 355 |
| `frontend/src/hooks/useTacticLine.ts` | useTacticLine hook (PV stepper with depth counter) | VERIFIED | `export function useTacticLine` at line 82; returns full interface including displayDepth, isPayoff, containerRef |
| `frontend/src/hooks/__tests__/useTacticLine.test.tsx` | Navigation + depth-floor + payoff + orientation-reset coverage | VERIFIED | 10 tests, all PASS |
| `frontend/src/components/library/TacticLineExplorer.tsx` | Dialog/Drawer explorer composing ChessBoard + BoardControls + SanLadder + toggle | VERIFIED | Both `tactic-explorer-dialog` and `tactic-explorer-drawer` present; composes all required elements |
| `frontend/src/components/library/SanLadder.tsx` | Linear real-ply-anchored SAN list with highlight + click-jump | VERIFIED | `tactic-san-ladder` testid, `moveLabel` uses real flawPly anchoring |
| `frontend/src/hooks/useLibrary.ts` | useTacticLines TanStack Query hook (lazy, enabled on open) | VERIFIED | Line 228: `enabled: enabled && gameId != null && ply != null` |
| `frontend/src/api/client.ts` | libraryApi.getTacticLines | VERIFIED | Line 377: `getTacticLines: (gameId, ply) =>` |
| `frontend/src/types/library.ts` | TacticLinesResponse TS type | VERIFIED | Line 377: `export interface TacticLinesResponse` mirroring backend schema |
| `frontend/src/components/library/FlawCard.tsx` | D-04 button row (Explore+Game / Game-only) | VERIFIED | `flaw-btn-explore` and `flaw-btn-game` in buttonRow, rendered in both responsive wrappers |
| `frontend/src/components/results/LibraryGameCard.tsx` | D-03 Explore button wired to the selected flaw | VERIFIED | `game-card-btn-explore` with disabled binding tied to `isTaggedFlaw` check |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `app/routers/library.py` | `app/repositories/library_repository.py` | `library_repository.fetch_tactic_lines(session, user_id, game_id, ply)` | VERIFIED | `router.py:385-389`: calls `library_repository.fetch_tactic_lines(session, user_id=user.id, ...)` |
| `app/repositories/library_repository.py` | `app/services/tactic_detector.py` | `_parse_pv` import for UCI walk | VERIFIED | `library_repository.py:43-47`: `from app.services.tactic_detector import _parse_pv`. `tactic_detector.py:241`: `def _parse_pv` exists |
| `frontend/src/components/library/TacticLineExplorer.tsx` | `frontend/src/hooks/useLibrary.ts` (useTacticLines) | `useTacticLines(gameId, ply, open)` lazy fetch | VERIFIED | `TacticLineExplorer.tsx:23,166`: imports and calls `useTacticLines(gameId, ply, open)` |
| `frontend/src/components/library/TacticLineExplorer.tsx` | `frontend/src/hooks/useTacticLine.ts` | `useTacticLine(moves, rootFen, tacticDepthRaw, orientation)` | VERIFIED | `TacticLineExplorer.tsx:24,215-219`: imports and calls `useTacticLine({ moves, rootFen, tacticDepthRaw, orientation })` |
| `frontend/src/components/library/FlawCard.tsx` | `frontend/src/components/library/TacticLineExplorer.tsx` | Explore button opens TacticLineExplorer | VERIFIED | `FlawCard.tsx:27`: imports TacticLineExplorer; `FlawCard.tsx:507-512`: `<TacticLineExplorer open={exploreOpen} ...>` |
| `frontend/src/components/results/LibraryGameCard.tsx` | `frontend/src/components/library/TacticLineExplorer.tsx` | game-card Explore opens TacticLineExplorer stacked over Game modal | VERIFIED | `LibraryGameCard.tsx:35`: imports; `LibraryGameCard.tsx:1111-1118`: `<TacticLineExplorer open={exploreOpen} onOpenChange={setExploreOpen} ...>` separate from parent modal state |
| `frontend/src/hooks/useTacticLine.ts` | `frontend/src/lib/tacticDepth.ts` | `toDisplayDepthForOrientation` for root display depth | VERIFIED | `useTacticLine.ts:19`: `import { toDisplayDepthForOrientation }` from tacticDepth; `useTacticLine.ts:200`: `rootDisplayDepth = toDisplayDepthForOrientation(tacticDepthRaw, orientation)` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `TacticLineExplorer.tsx` | `data` (TacticLinesResponse) | `useTacticLines(gameId, ply, open)` -> `libraryApi.getTacticLines` -> `GET /library/flaws/{gameId}/{ply}/tactic-lines` -> `fetch_tactic_lines()` -> `game_flaws` JOIN `game_positions` | Yes — real DB queries at `library_repository.py:2105-2127`, no static returns | FLOWING |
| `SanLadder.tsx` | `moves`, `flawPly`, `tacticPlyIndex` | Props from TacticLineExplorer, sourced from `data.missed_moves`/`data.allowed_moves` | Yes — populated from PV conversion of real stored Stockfish PVs | FLOWING |
| `useTacticLine.ts` | `position`, `currentPly`, `displayDepth`, `isPayoff` | Internal chess.js replay from `rootFen` (real game_position FEN) walking real SAN moves | Yes — walks server-provided SAN derived from Stockfish PVs | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 10 tactic-lines tests pass | `uv run pytest tests/routers/test_library_tactic_lines.py tests/repositories/test_library_tactic_lines_repo.py -v` | 10 passed | PASS |
| useTacticLine hook: 10 behaviors including depth floor, isPayoff, orientation reset | `cd frontend && npm test -- --run useTacticLine` | 10/10 passed | PASS |
| TacticLineExplorer: Dialog/Drawer switch, toggle visibility, toggle reset, empty/error states | `cd frontend && npm test -- --run TacticLineExplorer` | 7/7 passed | PASS |
| FlawCard D-04: tagged shows Explore+Game, untagged shows Game only | `cd frontend && npm test -- --run FlawCard` | 34/34 passed | PASS |

### Probe Execution

No probes defined for this phase (no probe-*.sh scripts declared in PLAN files). Spot-checks above serve as behavioral evidence.

### Requirements Coverage

No requirement IDs mapped to this phase (requirements: [] in all three PLAN files). No orphaned requirements found in REQUIREMENTS.md for phase 135.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `TacticLineExplorer.tsx` | 42 | `"placeholder"` word in comment | Info | Comment refers to `FALLBACK_FEN` constant used for unconditional hook call (React rules-of-hooks pattern). Not a placeholder feature — the constant is the chess starting position used only while data is absent (loading/error). No user-visible empty data flows through it. |

No TBD/FIXME/XXX debt markers in any phase-modified files. No raw hex literals in components (grep returns 0). No empty return stubs in functional code paths.

### Human Verification Required

#### 1. Integrated depth counter and SAN ladder walk (D-04 flaw card entry point, desktop)

**Test:** Open the Library page on a game that has tagged flaws. Click the Explore button on a tagged flaw card. Step forward through the missed line using the BoardControls forward button or arrow keys.
**Expected:** Depth readout in BoardControls (`tactic-depth-readout`) decrements from the root display depth on each forward step. At the punchline move it shows `Depth: 0`. One step past the punchline it shows `Payoff`. Never shows a negative number. SAN ladder highlights the current ply row with a left brown border. The punchline move (index == tacticPlyIndex) is colored in TAC_MISSED blue. Payoff moves are dimmed in muted-foreground. Move numbers match the real game ply (not starting at 1).
**Why human:** Hook-level depth decrement and isPayoff flip are verified in isolation by useTacticLine vitest (10 tests pass). The full integrated path — hook state change reflected through TacticLineExplorer re-render into the BoardControls `infoSlot` span and the SanLadder row coloring — is a state-transition invariant the jsdom tests exercise only partially (they verify the root depth after a toggle-reset but not a full forward walk). Real browser rendering is required to confirm no CSS/conditional-render gap breaks the chain.

#### 2. Mobile Drawer, D-01 stacking, and D-02 disabled tooltip (game card entry point, mobile)

**Test:** On a mobile device (or DevTools mobile viewport < 768 px), open a game in the Library. Park the eval-chart slider at a non-flaw ply. Observe the Explore button. Park the slider at a tagged flaw ply. Click Explore. Walk a few steps. Close the explorer by tapping outside or the close handle.
**Expected:** At a non-flaw ply: Explore button is visible but disabled; tapping it shows a tooltip "Park the slider on a tactic flaw to explore it". At a tagged flaw ply: Explore button is enabled; tapping opens a Drawer (not Dialog) from the bottom with the board and SAN ladder. Closing the Drawer returns focus to the Game modal which remains open (D-01 stacking — only the explorer closes).
**Why human:** The `isTaggedFlaw` gate and ternary-wrap tooltip render are code-verified. The D-01 stacking invariant — that `onOpenChange={setExploreOpen}` closes only the explorer while the underlying LibraryGameCard Game dialog stays open — depends on Radix Dialog/Drawer portal z-index ordering and focus-trap return behavior, which requires a real browser. The Drawer surface selection at < 768 px is mocked in jsdom tests but requires a real device to confirm the `matchMedia` path works in production.

---

_Verified: 2026-06-25T00:30:00Z_
_Verifier: Claude (gsd-verifier)_
