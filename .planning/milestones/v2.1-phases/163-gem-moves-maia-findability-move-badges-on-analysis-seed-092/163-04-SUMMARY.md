---
phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092
plan: 04
subsystem: ui
tags: [react, typescript, vitest, chess, maia, expected-score]

requires:
  - phase: 163-01
    provides: "gemMove.ts — GEM_MAIA_MAX_PROB, classifyGem, summarizeForGem (pure detection module)"
  - phase: 163-02
    provides: "GemIcon/boardMarkers gem variant (SquareMarker.gem, GEM_GLYPH)"
  - phase: 163-03
    provides: "colorForQuality('gem')/UnifiedMovePopover isGem/MaiaMoveQualityBar wiring"
provides:
  - "Two page-level per-FEN retention caches (maiaCurveByFen, gradeSummaryByFen) mirroring engineEvalByFen"
  - "qualityBySanWithGem — current-position chart/bar gem override, fed to both MaiaHumanPanel render sites"
  - "gemActive/gemCandidate — arrival-move classification against the PARENT position's cached data"
  - "gemByNode — sticky per-node cache mirroring liveFlawByNode, reset alongside it"
  - "boardSquareMarkers — live gemCandidate-driven violet board marker"
  - "moveListMarkers gem fold (no mainLineSet exclusion) + VariationTree FlawMarkerEntry.gem/GemIcon wiring"
affects: []

tech-stack:
  added: []
  patterns:
    - "Live-vs-sticky split for a slider-dependent classification: the board (single current node) reads the LIVE memo so ELO changes are reflected instantly; the move list (many historical nodes) reads the STICKY per-node cache since a non-current node has no live memo to re-derive, exactly mirroring the pre-existing liveFlaw (live)/liveFlawByNode (sticky) split"
    - "Two-caches-plus-parent-lookup pattern for cross-navigation data retention (maiaCurveByFen/gradeSummaryByFen keyed by FEN, read back via parentFen once the child is current) — extends the engineEvalByFen precedent to a second, ELO-independent payload shape"

key-files:
  created: []
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "Task 1+2 combined into one commit (interleaved memo chain) — Task 1's two per-FEN caches are unread until Task 2's gemCandidate memo consumes them, so a Task-1-only commit fails its own tsc --noEmit gate under noUnusedLocals, mirroring the 155-04/158-03/162-03 precedent already logged in STATE.md"
  - "moveListMarkers' gem fold has NO mainLineSet exclusion (unlike the pre-existing severity/addLive fold) — gemActive explicitly covers mainline AND free-variation nodes (D-05), and moveListMarkers is the ONLY map VariationTree reads; reusing the severity fold's mainLineSet guard verbatim would have silently dropped every mainline gem badge from the move list, contradicting the phase's own must-have truth"
  - "Rule 1 bug fix: boardSquareMarkers reads the LIVE gemCandidate memo, not the sticky gemByNode cache, for the board's own marker — gemByNode is a one-way latch (only ever inserts true, never removes), so keying the board off it would mean an ELO-slider move could never again hide an already-shown board badge on the SAME still-current node, contradicting RESEARCH.md's explicit D-03 note (\"badges legitimately update when the slider moves\"); found while designing the D-03 integration test, before it was ever wrong in a shipped state"
  - "gemByNode is reset alongside liveFlawByNode at BOTH Reset-button branches (game-mode clearAllSidelines + free-play loadMainLine([], rootFen)) — free-play reset resets nextId to 0 (real collision risk with old node ids), and clearing on the game-mode branch too is harmless (mainline gems instantly re-derive from the still-intact FEN caches on revisit) and keeps the reset semantics uniform with its liveFlawByNode analog"
  - "Task 3 tests drive REAL board interaction (click-to-click via square-{square} testids bubbling through react-chessboard's own onClick) and REAL move-list navigation — useAnalysisBoard is deliberately not mocked in this file, so these are genuine end-to-end proofs of the parent-position cache wiring, not just classifyGem unit coverage (already covered in gemMove.test.ts, Plan 01)"

requirements-completed: [D-03, D-04, D-05, D-06]

coverage:
  - id: D1
    description: "Two per-FEN caches (maiaCurveByFen, gradeSummaryByFen) retain each visited position's Maia curve and grade summary while it is current; gradeSummaryByFen's effect deps are deliberately ELO-free"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Gem moves (Phase 163, SEED-092) — all 5 tests exercise the caches via real navigation"
        status: pass
    human_judgment: false
  - id: D2
    description: "The arrival move into any visited node (mainline or free variation, either color) is classified against the PARENT position's cached data via gemCandidate, and stuck per node in gemByNode"
    requirement: "D-04, D-05"
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#classifies a freely-played WHITE move as a gem; #classifies a freely-played BLACK move as a gem; #classifies a gem on a MAINLINE game node reached via the move list"
        status: pass
    human_judgment: false
  - id: D3
    description: "A gem node paints a violet board marker (live, ELO-reactive) and a GemIcon in the move list (sticky, persists across navigation away and back)"
    requirement: "D-03, D-06"
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#sticky: the move-list gem badge persists after navigating away and back; #re-derives C1 when the ELO slider moves"
        status: pass
    human_judgment: false
  - id: D4
    description: "qualityBySanWithGem recolors the current position's reconciled-best move as 'gem' for both MaiaHumanPanel render sites (desktop + mobile), leaving every other qualityBySan consumer untouched"
    requirement: "D-06"
    verification:
      - kind: static
        ref: "grep -c \"qualityBySan={qualityBySanWithGem}\" frontend/src/pages/Analysis.tsx == 2; grep -c \"qualityBySan={qualityBySan}\" == 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live-browser visual confirmation of the gem badge geometry (violet board-corner marker, move-list GemIcon, violet chart curve, popover copy) on a known gem ply"
    verification: []
    human_judgment: true
    rationale: "jsdom performs no real layout/paint; the DOM-level assertions in this plan's tests (fill-color circle presence) prove the WIRING is correct but not the actual rendered visual appearance. Per 163-VALIDATION.md's own Per-Task Verification Map, this is the designated manual-only UAT row."

duration: 55min
completed: 2026-07-10
status: complete
---

# Phase 163 Plan 04: Gem moves wired into Analysis.tsx Summary

**Two per-FEN retention caches + a parent-position `gemCandidate` memo classify every visited node's arrival move against the PARENT's cached Maia curve and grade summary, surfacing a live ELO-reactive violet board marker plus a sticky move-list `GemIcon`, both proven via real board/move-list navigation in 5 new integration tests.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-07-10T17:39:00Z
- **Completed:** 2026-07-10T18:09:15Z
- **Tasks:** 3 (Tasks 1+2 combined into one commit; Task 3 its own commit)
- **Files modified:** 3 (`frontend/src/pages/Analysis.tsx`, `frontend/src/components/analysis/VariationTree.tsx`, `frontend/src/pages/__tests__/Analysis.test.tsx`)

## Accomplishments
- `maiaCurveByFen`/`gradeSummaryByFen`: two page-level per-FEN caches mirroring `engineEvalByFen` exactly, solving RESEARCH's Pitfall 1 (parent-position data is otherwise unreachable once the user navigates to the child) — `gradeSummaryByFen`'s effect deps are deliberately ELO-free (Pitfall 6)
- `qualityBySanWithGem`: recolors the CURRENT position's reconciled-best candidate as `'gem'` for the chart/bar display sites only (both desktop and mobile `MaiaHumanPanel` render sites), leaving `positionVerdict`/the FlawChess card on the base `qualityBySan`
- `gemActive`/`gemCandidate`: classifies the arrival move into the current node against the parent's cached data, with NO `isGameMode`/`isOnPvLine` exclusion (D-05: covers mainline AND free variations, either color)
- `gemByNode`: sticky per-node cache mirroring `liveFlawByNode`, reset alongside it at both Reset-button branches
- `boardSquareMarkers`: unions in a violet gem `SquareMarker` keyed off the LIVE `gemCandidate` memo (see Deviations — this differs from the plan's literal `gemByNode`-keyed sketch)
- `moveListMarkers`: folds `gemByNode` (sticky, all nodes) + the current node's live `gemCandidate`, deliberately WITHOUT the severity fold's `mainLineSet` exclusion
- `VariationTree.tsx`: `FlawMarkerEntry.gem?: boolean`, `GemIcon` import, and a shared `resolveMarkerIcon()` helper applied at all 3 severity-icon render sites (gem takes precedence, mutually exclusive by construction)
- 5 new integration tests in `Analysis.test.tsx`'s `Gem moves` describe block, driving REAL board clicks (`square-{square}` testids) and REAL move-list navigation to prove the parent-position cache wiring end to end

## Task Commits

Each task was committed atomically:

1. **Task 1+2 (combined): Two per-FEN caches + qualityBySanWithGem, gemActive/gemCandidate/gemByNode, board marker, move-list fold, VariationTree wiring** - `e4ad87e8` (feat)
2. **Task 3: Analysis integration tests (sticky cache, coverage, ELO re-derivation) + board-marker live fix** - `66b12701` (test)

## Files Created/Modified
- `frontend/src/pages/Analysis.tsx` - `maiaCurveByFen`/`gradeSummaryByFen` caches, `qualityBySanWithGem`, `gemActive`/`gemCandidate`/`gemByNode`, `boardSquareMarkers`, `moveListMarkers` gem fold, Reset-button `gemByNode` clears
- `frontend/src/components/analysis/VariationTree.tsx` - `FlawMarkerEntry.gem`, `GemIcon` import, `resolveMarkerIcon()` helper, all 3 render sites updated
- `frontend/src/pages/__tests__/Analysis.test.tsx` - new `Gem moves (Phase 163, SEED-092)` describe block, 5 tests

## Decisions Made
- Task 1+2 combined into one commit (interleaved memo chain, mirrors 155-04/158-03/162-03 precedent) — Task 1's caches are dead code until Task 2 wires them
- `moveListMarkers`'s gem fold has no `mainLineSet` exclusion — gem must cover mainline nodes too (D-05), and this map is VariationTree's only data source
- Rule 1 fix: `boardSquareMarkers` reads the LIVE `gemCandidate`, not the sticky `gemByNode`, for the board's own marker — see Deviations below
- `gemByNode` is reset alongside `liveFlawByNode` at both Reset-button branches, for reset-semantics parity with its structural analog
- Test helper `seedGemGrading` takes a `mover` option that flips the seeded `evalCp` sign, since `evalCp` is always white-POV and a Black gem needs a NEGATIVE cp to read as good for Black

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `boardSquareMarkers` keyed off the sticky `gemByNode` cache instead of the live `gemCandidate` memo**
- **Found during:** Task 3, while designing the D-03 (ELO re-derivation) integration test
- **Issue:** The plan's Task 2 action text (and RESEARCH.md's own Pattern 2/Code Examples sketch) specified reading `gemByNode.has(currentNodeId)` for the board's marker. `gemByNode` is a one-way latch (its effect only ever inserts `true`, mirroring `liveFlawByNode`'s "never overwrite with a negative" contract) — so once a node's arrival move was classified a gem at one ELO rung, the board marker would remain forever, even after moving the ELO slider to a rung that fails C1 on that SAME still-current node. This directly contradicts RESEARCH.md's own D-03 note: "badges legitimately update when the slider moves." It would also have made Task 3's own literally-specified test ("assert that moving `selectedElo`... removes the gem") impossible to satisfy for the board surface.
- **Fix:** Reworked `boardSquareMarkers` to read the LIVE `gemCandidate` memo directly (dropping the `currentNodeId`/`gemByNode` dependency), mirroring exactly how `liveFlaw.squareMarkers` (live), not `liveFlawByNode` (sticky), already drives the board for the pre-existing blunder/mistake markers. `gemByNode` remains the sticky source for `moveListMarkers` (the only surface that needs to remember past, non-current nodes — a past node has no live memo to re-derive since it's no longer the current position).
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** New `Gem moves` D-03 test explicitly asserts the board marker disappears after an ELO change while the move-list badge stays sticky; full test suite green.
- **Committed in:** `66b12701` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — the plan's literal board-marker wiring would have shipped a badge that never updates with the ELO slider, contradicting the phase's own explicit RESEARCH requirement. No scope creep; the sticky move-list behavior (the plan's actual D-06 intent) is unchanged.

## Issues Encountered
- The first draft of the "BLACK move" D-04 test failed: the `seedGemGrading` helper hard-coded a white-POV-favoring `evalCp` sign regardless of mover, so the "gem" move for Black was seeded with a cp that actually favored White — making the OTHER (non-gem) candidate the summary's true best and failing C2. Fixed by adding a `mover` option to the test helper that flips the sign (see Decisions above). Not a product bug — a test-authoring correction, caught and fixed before the final commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 4 plans of Phase 163 are now complete. Gem detection is fully wired: `gemMove.ts` (Plan 01) → visual primitives (Plan 02) → chart/popover surfaces (Plan 03) → live Analysis.tsx wiring + integration tests (this plan).
- Remaining phase-level verification: the live-browser UAT row from `163-VALIDATION.md` (violet board marker, move-list icon, chart curve, popover copy on a real gem ply) is the only item not covered by automated tests — flagged as `human_judgment: true` above, consistent with VALIDATION.md's own manual-only classification.
- No blockers. `tsc -b`, `npm run lint`, `npm run knip`, and the full frontend suite (1732 tests) are all green.

---
*Phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: frontend/src/pages/Analysis.tsx
- FOUND: frontend/src/components/analysis/VariationTree.tsx
- FOUND: frontend/src/pages/__tests__/Analysis.test.tsx
- FOUND commit: e4ad87e8
- FOUND commit: 66b12701
