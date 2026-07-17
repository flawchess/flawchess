---
phase: 175-board-filter-gem-great-consumption
plan: 05
subsystem: ui
tags: [react, typescript, gem-great, analysis-board, useGemSweep, stored-tier]

# Dependency graph
requires:
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-02: EvalPoint.best_move_tier/maia_prob backend read path (the stored data this plan consumes on the board)"
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-03: great-tier frontend primitives (GREAT_ACCENT/GreatMoveIcon/classifyGreat, SquareMarker.great, GemMoveBadge tier prop, UnifiedMovePopover.isGreat, VariationTree great* fields) — every rendering surface this plan wires the stored tier onto"
provides:
  - "Analysis.tsx storedTierByPly (ply -> {tier, maiaProb}) + resolveMarkerFor precedence (stored wins over live gemByNode/sweep fallback) — mainline gem/great rendered from EvalPoint.best_move_tier, no live engine call"
  - "gameHasStoredBestMoveData gate demoting BOTH live gem mechanisms (Phase-163 gemC1/gemGrading/gemByNode AND Phase-172 useGemSweep) to fallback-only (off-mainline / free-play / unanalyzed games)"
  - "WR-06 fix: useGemSweep resolveCandidate wrapped in useCallback([]) + listed in the CR-03 watchdog/fast-fail effect deps"
  - "IN-01 (VariationTree resolveMarkerIcon dead isBook field removed), IN-03 (SweepDispatch idle/done documented no-op), IN-04 (real ply threaded through moveListMarkers, NO_GAME_PLY sentinel)"
affects: [176]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stored-first marker precedence: a per-ply stored-tier lookup consulted BEFORE any live classifier; row-absence on an analyzed game's mainline is authoritative 'not a gem/great' (Pitfall 3), never 'unknown'"
    - "Fallback-only gating: a single 'game has stored best-move data' boolean ANDed into BOTH live gem mechanisms' enable gates, so neither re-derives a verdict the stored path owns (Pitfall 2)"
    - "Demote-not-delete: useGemSweep's dedicated-worker machinery retained intact behind a permanent analyzed-mainline gate as the documented free-play/no-stored-data fallback (SEED-107 superseded)"

key-files:
  created: []
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/components/analysis/MaiaMoveQualityBar.tsx
    - frontend/src/hooks/useGemSweep.ts
    - frontend/src/hooks/__tests__/useGemSweep.test.ts
    - frontend/src/components/analysis/VariationTree.tsx

key-decisions:
  - "gameHasStoredBestMoveData reuses the sticky sweepArmedForGame signal (not the flicker-prone evalChartReady), so the stored-vs-fallback verdict can never transiently flip false mid-poll."
  - "qualityBySanWithGem consults the NEXT mainline move's stored tier (ply mainlinePlyHere+1) with a nextNode.san === reconciledBestSan agreement check — classify_best_move only ever stores a best-move ply, so a stored tier can only match the engine's reconciled-best candidate."
  - "resolveGemFor renamed to resolveMarkerFor and returns a ResolvedMarker ({tier: 'gem'|'great', maiaProbability, elo, byOpponent}) so gem AND great flow through the SAME single precedence site (board badge + move-list fold)."
  - "IN-04: introduced a named NO_GAME_PLY (-1) sentinel and threaded the REAL mainline/sweep ply through the move-list marker fold (markerNodePlies) instead of synthesizing bare -1 literals; the book fold uses the real plyIndex."
  - "The Phase-172 CR-02 (yield-to-cursor wiring) and D-05/SC2 (instance isolation) page-level dispatch proofs are MOOT under demotion (no analyzed-mainline scenario dispatches a sweep candidate through Analysis.tsx's real wiring anymore); rewrote them as the NEW demotion-gate invariant, with the underlying yield/isolation invariants still unit-tested directly in gemSweep.test.ts/useGemSweep.test.ts."

patterns-established:
  - "TDD-mutation self-check: temporarily forced storedTierByPly.get(ply) to return undefined ('no stored data') and confirmed the stored-great page test failed RED (marker vanished), proving the badge is sourced from stored EvalPoint data and not a live path, before reverting clean (diff empty, suite green again)."

requirements-completed: [BOARD-02]

coverage:
  - id: D1
    description: "An analyzed game's mainline renders gem AND great from stored EvalPoint.best_move_tier/maia_prob on the board corner badge, move-list glyph, moves-by-rating chart recolor, and popover — no live Maia/Stockfish call"
    requirement: "BOARD-01/BOARD-02"
    verification:
      - kind: unit
        ref: "Analysis.test.tsx > Stored gem/great consumption (Phase 175, SEED-108 D-01/D-02b/D-03): stored-gem badge, stored-great badge, popover maia_prob + opponent heading (3 of 4 cases)"
        status: pass
      - kind: unit
        ref: "MUTATION self-check — forcing storedTierByPly to return undefined makes the stored-great test fail red (marker sourced from stored data, not a live path)"
        status: pass
      - kind: manual
        ref: "Human-verify checkpoint steps 2-4: badges paint on FIRST paint of the mainline position; DevTools Network+Workers panel shows no Maia/Stockfish worker activity on mainline navigation"
        status: pass
    human_judgment: true
  - id: D2
    description: "A mainline ply with best_move_tier=null renders NO marker and triggers NO live grade — row-absence on an analyzed game's mainline is authoritative (Pitfall 3, BOARD-02 'no background sweep delay')"
    requirement: "BOARD-02"
    verification:
      - kind: unit
        ref: "Analysis.test.tsx > Stored gem/great consumption: 'a mainline ply with best_move_tier=null renders NO marker and never triggers a live grade' (seeds data that WOULD classify a gem if the live path ran — fails loud on regression)"
        status: pass
    human_judgment: false
  - id: D3
    description: "BOTH live gem mechanisms (Phase-163 gemC1/gemGrading/gemByNode AND Phase-172 useGemSweep) fire ONLY for positions with no stored best-move row (off-mainline, free-play, unanalyzed bot games); useGemSweep demoted (not deleted), SEED-107 superseded"
    requirement: "BOARD-02"
    verification:
      - kind: unit
        ref: "Analysis.test.tsx > Sweep demotion (Phase 175, SEED-108 D-01/D-01a): sweep never dispatches for an analyzed game even with an idle live engine + a real D-04 candidate; dedicated instances stay idle while the live per-node instances still resolve an OFF-MAINLINE free move"
        status: pass
      - kind: unit
        ref: "useGemSweep.test.ts: stored-data-disables-sweep (enabled:false -> no dispatch) + unanalyzed-still-runs (enabled:true -> dispatch+resolve preserved)"
        status: pass
      - kind: unit
        ref: "Analysis.test.tsx > 'gem popover heading names the opponent (unanalyzed-game fallback)' + 'classifies a gem on a MAINLINE game node (unanalyzed-game fallback)' — live fallback retained for eval_series:null games"
        status: pass
      - kind: manual
        ref: "Human-verify checkpoint step 5: live fallback still resolves gem/great in user-created variations / fresh unanalyzed bot games (worker activity expected there only)"
        status: pass
    human_judgment: true
  - id: D4
    description: "WR-06 stale-closure trap killed (resolveCandidate useCallback([]) + listed in the CR-03 watchdog/fast-fail effect deps, react-hooks/exhaustive-deps clean with no eslint-disable); IN-01/03/04 cleanups on the retained fallback path; WR-01/03/05 NOT implemented (moot per D-01a)"
    requirement: "BOARD-02"
    verification:
      - kind: unit
        ref: "useGemSweep.test.ts: 'stable-callback (WR-06)' — repeated mid-cascade re-renders with fresh candidate/pinnedElo refs never reset the CR-03 watchdog; the candidate still resolves at (not restarted past) SWEEP_CANDIDATE_TIMEOUT_MS"
        status: pass
      - kind: lint
        ref: "npm run lint (react-hooks/exhaustive-deps + react-hooks/preserve-manual-memoization) clean — 0 errors, no eslint-disable added for resolveCandidate"
        status: pass
    human_judgment: false

# Metrics
duration: ~110min
completed: 2026-07-17
status: complete
---

# Phase 175 Plan 05: Board Stored Gem/Great Consumption + Live-Mechanism Demotion Summary

**An analyzed game's mainline now renders gem AND great markers instantly from the backend-stored `EvalPoint.best_move_tier`/`maia_prob` on every surface (board badge, move-list glyph, moves-by-rating chart recolor, popover), and BOTH client-side live gem mechanisms are demoted to a documented fallback that fires only where no stored row exists — closing BOARD-02's "no background sweep delay" by construction, and resolving the deferred WR-06/IN-01/03/04 findings.**

## Performance

- **Duration:** ~110 min
- **Completed:** 2026-07-17
- **Tasks:** 2 implementation tasks + 1 blocking human-verify checkpoint (approved)
- **Files modified:** 6

## Accomplishments

- **Stored-tier consumption (Task 1).** Added `storedTierByPly` (a `ply -> {tier, maiaProb}` memo derived from `gameData.eval_series`, keeping only non-null `best_move_tier` rows per Pitfall 3) and `gameHasStoredBestMoveData` (the sticky `sweepArmedForGame` readiness signal) to `Analysis.tsx`. Renamed `resolveGemFor -> resolveMarkerFor`, returning a `ResolvedMarker` (`{tier: 'gem'|'great', maiaProbability, elo, byOpponent}`) that consults the stored tier FIRST for any mainline ply of an analyzed game (present or authoritatively null) and only falls through to the live `gemByNode`/`sweep.gemByPly` precedence when there is no stored answer. Routed the board corner badge (`boardSquareMarkers`), the move-list glyph (`moveListMarkers`), the moves-by-rating chart recolor (`qualityBySanWithGem`, which now consults the NEXT mainline move's stored tier with a `nextNode.san === reconciledBestSan` agreement check), and the popover through this one precedence site — great handled everywhere gem is (D-02b).
- **MaiaMoveQualityBar `isGreat` wiring.** Added the matching `isGreat` prop to `ProseMoveSpan` and threaded `qualityBySan.get(m.san)?.quality === 'great'` into `UnifiedMovePopover.isGreat`, so the moves-by-rating chart popover shows great the same way it already shows gem (plan-list omission mirroring the 175-03 `colorForQuality` precedent).
- **Both live mechanisms demoted to fallback-only (Task 2).** `needParentGemGrade` gained a `!currentNodeCoveredByStoredData` clause (the Phase-163 live-at-cursor `gemC1`/`gemGrading`/`gemByNode` path never fires on a stored mainline ply); `useGemSweep`'s `enabled` prop now ANDs `!gameHasStoredBestMoveData` (the Phase-172 sweep never runs over a stored mainline). Both gate on the SAME "no stored tier" signal (Pitfall 2). `useGemSweep.ts` gained a file-header docstring declaring it a demoted free-play-only fallback; SEED-107 closes as superseded.
- **WR-06 fix.** `resolveCandidate` is now a stable `useCallback([])` identity (it touches only stable setState setters), listed explicitly in the CR-03 watchdog + fast-fail effect dependency arrays — the latent stale-closure trap is gone, and `react-hooks/exhaustive-deps` passes with no `eslint-disable`.
- **IN-01/03/04 cleanups.** IN-01: dropped `resolveMarkerIcon`'s unread `isBook` return field (`VariationTree.tsx`). IN-03: documented the scheduler's `idle` vs `done` `SweepDispatch` variants as deliberately-unbranched no-ops (no downstream reader needs the distinction). IN-04: introduced a named `NO_GAME_PLY` (-1) sentinel and threaded the REAL mainline/sweep ply through the move-list marker fold (`markerNodePlies`) and the book fold, instead of synthesizing bare `-1` literals. WR-01/03/05 were deliberately NOT implemented (moot per D-01a — the sweep no longer sweeps a stored mainline at all).

## Task Commits

Each task was committed atomically:

1. **Task 1: Render mainline gem/great from stored EvalPoint.best_move_tier** — `41cb2834` (feat)
2. **Task 2: Demote both live gem mechanisms to fallback-only + WR-06/IN fixes** — `e7e5b0c7` (feat)

## Files Created/Modified

- `frontend/src/pages/Analysis.tsx` — `storedTierByPly`, `gameHasStoredBestMoveData`, `resolveMarkerFor` (renamed from `resolveGemFor`, gem+great), `ResolvedMarker` type, `qualityBySanWithGem` stored-first branch, `needParentGemGrade` + `useGemSweep.enabled` fallback gates, `NO_GAME_PLY` sentinel + real-ply threading, board/move-list `great` rendering.
- `frontend/src/pages/__tests__/Analysis.test.tsx` — new `Stored gem/great consumption` describe (4 cases incl. the mutation-proof null-tier case), new `Sweep demotion` describe (supersedes the Phase-172 CR-02/D-05 dispatch proofs), 3 pre-existing gem tests re-scoped to the unanalyzed-game fallback path.
- `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` — `ProseMoveSpan` `isGreat` prop + `UnifiedMovePopover.isGreat` wiring.
- `frontend/src/hooks/useGemSweep.ts` — demotion docstring, `resolveCandidate` `useCallback([])` (WR-06), IN-03 scheduler no-op documentation.
- `frontend/src/hooks/__tests__/useGemSweep.test.ts` — stored-data-disables-sweep, unanalyzed-still-runs, stable-callback (WR-06) watchdog-timing tests.
- `frontend/src/components/analysis/VariationTree.tsx` — IN-01 dead `isBook` field removed from `resolveMarkerIcon`.

## Human-Verify Checkpoint (Task 3) — APPROVED

The blocking `checkpoint:human-verify` gate was **approved by the user** (2026-07-17). The user manually confirmed:

1. Dev DB + backend + frontend started (steps 1).
2. Opening an already-analyzed game with a gem/great move: the badge appears on the **first paint** of the mainline position — no visible delay, no badge popping in after a beat (steps 2-3).
3. DevTools Network + Workers/Performance panels show **NO Maia/Stockfish worker activity** for mainline navigation — the stored path does no live compute (step 4).
4. Navigating into a user-created variation / loading a fresh unanalyzed bot game: the **live fallback still resolves gem/great** there (worker activity expected in that case only) (step 5).

Step 6 (Library "has gem"/"has great" filter toggles) belongs to Plan 175-04, not this plan; it had a separate bug already fixed independently, and is out of scope for 175-05's gate.

## Deviations from Plan

- **[Rule 1 — Test-scope correction] Three pre-existing Phase-163/172 tests re-scoped to the fallback path.** The demotion legitimately changes behavior these tests asserted: an analyzed game's mainline gem now comes from the stored tier (which the mocks never seed), so `gem popover heading names the opponent`, `classifies a gem on a MAINLINE game node`, and the Phase-172 `D-05 yield-to-cursor wiring` / `Instance isolation` page-level dispatch proofs no longer had a reachable scenario. Re-scoped the first two to the unanalyzed-game (`eval_series: null`) fallback path, and rewrote the latter two as the NEW demotion-gate invariant ("the sweep never dispatches for an analyzed game even with an idle live engine + a real D-04 candidate"). The underlying yield-to-cursor and instance-isolation invariants remain unit-tested directly in `gemSweep.test.ts` / `useGemSweep.test.ts`. This is a test-maintenance consequence of the plan's own demotion decision (D-01a), not a scope change.
- **[Plan-list omission] `MaiaMoveQualityBar.tsx` modified** though not in the plan's `files_modified` frontmatter — the plan's Task 1 action ("Wire the popover ... to the stored maia_prob") and its D-02b truth ("Great appears on ... the eval/moves-by-rating chart") require the chart popover's `isGreat`, which lives in this file (the same category of omission 175-03 documented for `colorForQuality`). Treated as a plan-list omission, not unplanned scope.

## Issues Encountered

- The React Compiler's `react-hooks/preserve-manual-memoization` lint rule rejected an initial `resolveMarkerFor` `useCallback` because it read `gameData?.user_color` inside a nested `return` (inferred dep `gameData` was less specific than the listed `gameData?.user_color`). Fixed by hoisting `const userColor = gameData?.user_color` before use — no behavior change.

## Known Stubs

None — every rendering surface is wired to real stored data (or the retained live fallback); no placeholder/empty-data paths were introduced.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- BOARD-01/BOARD-02 are complete: analyzed-game mainlines render gem/great instantly from stored `EvalPoint` data with no live engine call, both live mechanisms are demoted to a no-stored-row fallback, and the WR-06/IN-01/03/04 deferred findings are resolved. Instant-marker paint + no-mainline-worker-activity confirmed by the approved human-verify checkpoint.
- **Phase 176 (BACK-01) dependency note:** pre-Phase-174/175 analyzed games have zero `game_best_moves` rows, so by this plan's design (Pitfall 3, row-absence is authoritative) they show NO mainline gem/great markers until Phase 176's opportunistic corpus backfill populates their rows. This is expected and correct — the board never invents a marker for a not-yet-backfilled game.

---
*Phase: 175-board-filter-gem-great-consumption*
*Completed: 2026-07-17*

## Self-Check: PASSED

All 6 modified source/test files confirmed present on disk; both task commits
(`41cb2834`, `e7e5b0c7`) confirmed in git history. Full frontend suite
2272/2272 green; `npx tsc -b` + `npm run lint` + `npm run knip` clean.
Human-verify checkpoint approved by the user.
