---
phase: 172-background-gem-sweep-on-analysis-seed-106
plan: 05
subsystem: analysis
tags: [gem-sweep, maia, stockfish, react, typescript, analysis-page, opening-book]

# Dependency graph
requires:
  - phase: 172-01
    provides: "opening_ply_count on GameFlawCard (backend + frontend types)"
  - phase: 172-02
    provides: "gemSweep.ts (selectSweepCandidates, nextSweepDispatch); deriveRawDefault/clampToLadderBounds exported; GEM_MAIA_MAX_PROB raised to 0.2"
  - phase: 172-03
    provides: "BOOK_MARKER_COLOR, bookGlyph.ts, BookIcon; severity > gem > book precedence wired into VariationTree.resolveMarkerIcon and boardMarkers.SquareMarkerBadge"
  - phase: 172-04
    provides: "useGemSweep — dedicated Maia/Stockfish worker instances, the D-04 cascade, the D-05 yield-to-cursor scheduler"
provides:
  - "pinnedEloForMover — Analysis.tsx's D-01 rung-pin helper, reused by both the live gem path and the sweep's pinnedEloForPly"
  - "The gem rung is now a property of the game (mover's rating-at-game-time), never the ELO slider"
  - "opening_ply_count-driven book markers wired end to end on moveListMarkers and boardSquareMarkers"
  - "useGemSweep wired into Analysis.tsx: hoisted evalChartReady, D-04 sweepCandidates, D-03 readiness-transition arming, sweep results folded into both display surfaces"
  - "Page-level D-05/SC2 instance-isolation proof (Analysis.test.tsx), with a manually recorded red-then-green revert"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reactive React state (not a ref) for a value read during render — this project's ESLint config (react-hooks/refs, React Compiler) forbids reading ref.current in the render body; useState + an effect that setStates from the async source is the correct substitute"
    - "Breaking a same-render circular hook dependency (needParentGemGrade feeds the sweep's liveBusy, but also wants to know what the sweep resolved) via a companion state variable synced ONE render late by an effect declared AFTER the producing hook call"

key-files:
  created: []
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "pinnedEloForMover implemented as a useCallback (not module-scope) since it closes over isGameMode/gameData/userProfile — reused identically by gemC1, parentGemCandidateSans, the C2 effect, and pinnedEloForPly"
  - "D-03 'armed' state (sweepArmedForGame) implemented via useState (armedGameId), not the plan's literal sweptGameIdRef suggestion — reading ref.current during render is a hard ESLint failure (react-hooks/refs) in this project; sweepArmedForGame reads evalChartReady directly for the SAME-render transition and armedGameId only for sticky protection against a later flicker"
  - "needParentGemGrade's 'avoid double work' extension (skip re-grading a ply the sweep already resolved) implemented via a companion sweepResolvedPlies useState, synced from sweep.gemByPly by an effect declared AFTER the sweep call — not a ref (same ESLint constraint) and not sweep.gemByPly read directly (would be circular: needParentGemGrade is ALSO the sweep's own liveBusy input)"
  - "sweepCandidates' useMemo deps list `gameData` as a single object dependency instead of gameData?.moves/gameData?.eval_series/gameData?.opening_ply_count — the React Compiler's 'preserve-manual-memoization' check requires the deps array to textually match its own inferred non-optional property accesses inside the callback; optional-chained deps entries triggered a compile-skip lint error"
  - "The live gemGrading (on-demand C2) hook call ended up positioned AFTER useGemSweep in Analysis.tsx (not before, as an initial reading of the plan's file-level artifact table might suggest) — needParentGemGrade must exist before it can be passed to the sweep as liveBusy, and parentGemCandidateSans/gemGrading both depend on needParentGemGrade. Actual instance order per commit: [primary grading, sweep's dedicated grading, live gemGrading] for the Stockfish grading engine, and [live maia, sweep's dedicated maia] for Maia — documented explicitly in Analysis.test.tsx's helper functions after the isolation test caught the reversed assumption"

requirements-completed: []

coverage:
  - id: D1
    description: "The gem rung is pinned to the mover's own rating-at-game-time (pinnedEloForMover) at all four gem-detection sites; the ELO slider no longer changes which moves are gems or their stamped rung, while still driving the Maia chart/WDL bar/FlawChess engine"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#SC3 (Phase 172, SEED-106 D-01): the ELO slider does not change an already-resolved gem's stamped rung"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#gem resolution is a one-way sticky latch across ELO-slider moves"
        status: pass
    human_judgment: false
  - id: D2
    description: "opening_ply_count gates book markers on both moveListMarkers (VariationTree) and boardSquareMarkers (board corner), with severity > gem > book precedence honored at both call sites"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx (39/39 pre-existing Analysis tests green after the D-08 wiring, including WR-05 severity-wins and D-06 sticky-latch cases which exercise the same merged marker maps)"
        status: pass
    human_judgment: true
    rationale: "No dedicated Analysis.test.tsx test exercises a real opening_ply_count > 0 fixture rendering the BookIcon glyph end to end on this page (VariationTree.test.tsx/boardMarkers.test.tsx from plan 03 cover the component-level precedence logic directly) — a human UAT pass on a real analyzed game with known theory plies is the more meaningful proof for the visual outcome."
  - id: D3
    description: "The sweep starts on the analysis-readiness FALSE->TRUE transition (a bot game opened mid-tier-1-analysis gets swept the moment evals land, no reload); an unanalyzed game with no active job never sweeps"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#SC7 (Phase 172, SEED-106 D-03): a bot game opened while tier-1 analysis is still running is swept the moment the evals land — no reload, no remount"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#renders no pill and no Analyze button when active_eval_status is null (unanalyzed, unqueued) — SC4: never dispatches sweep work"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-05 yield-to-cursor invariant proven at the PAGE layer: the live grading/Maia instances are never driven with a sweep candidate FEN, even while the sweep is actively mid-cascade — proven red-then-green via a manual revert"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Instance isolation (Phase 172, SEED-106 D-05 / SC2 — LOAD-BEARING) > the live grading/Maia instances are never driven with a sweep candidate FEN, even while the sweep is actively mid-cascade"
        status: pass
    human_judgment: false

duration: ~2h
completed: 2026-07-14
status: complete
---

# Phase 172 Plan 05: Wire the Background Gem Sweep into Analysis.tsx Summary

**Pinned the gem rung to the mover's own rating (D-01), painted opening-book markers on both surfaces (D-08), wired `useGemSweep` into `Analysis.tsx` on the analysis-readiness transition (D-03/D-04/D-05), and proved the D-05 yield-to-cursor invariant at the page layer with a manually recorded red-then-green revert.**

## Performance

- **Duration:** ~2h
- **Completed:** 2026-07-14
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `pinnedEloForMover` (a `useCallback` reusing plan 02's exported `deriveRawDefault`/`clampToLadderBounds`) replaces `selectedElo` at all four gem-detection sites (`gemC1`, `parentGemCandidateSans`, the C2 confirmation effect's probability lookup, and its stamped `GemDetail.elo`) — the ELO slider no longer moves gems, while still driving the Maia chart/WDL bar/FlawChess engine unchanged. Stale slider-linked doc-comments updated.
- `moveListMarkers` and `boardSquareMarkers` both gained a book-marker pass gated on `plyIndex < gameData.opening_ply_count`, appended at the LOWEST precedence (after severity and gem), mirroring the existing gem-append construction-time-exclusivity guard.
- Hoisted `evalChartReady` above the gem block; added `sweepCandidates` (D-04 free prefilter via plan 02's `selectSweepCandidates` + a new `fenAtPly` helper), `pinnedEloForPly`, and the `useGemSweep` call itself, gated on a readiness-transition-armed state (`sweepArmedForGame`) that fires the SAME render `evalChartReady` flips true — no one-render delay.
- `needParentGemGrade` (the live per-node gate) now also short-circuits once the sweep has already resolved the current mainline ply, via a `sweepResolvedPlies` state synced one render after the sweep's own state — this ordering (not a ref) is what avoids a circular `needParentGemGrade` <-> `sweep.liveBusy` dependency.
- Both display memos fold `sweep.gemByPly` in as a second gem source, strictly by read-time union — never written into `gemByNode`'s shared FIFO-256 cache (Pitfall 4).
- New page-level D-05/SC2 instance-isolation test — the load-bearing proof that the live grading/Maia instances are never driven with a sweep candidate FEN, even while the sweep is mid-cascade — plus new SC7 (readiness-transition), SC4 (lazy-path), and SC3 (slider-independence) tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin the live gem rung to the mover (D-01) and paint the book markers (D-08)** - `89899447` (feat)
2. **Task 2: Wire the sweep — readiness transition, candidates, and the display merge** - `976c3df1` (feat)
3. **Task 3: Page-level proof — instance isolation, the readiness transition, and the lazy path** - `158037b8` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/pages/Analysis.tsx` - D-01 rung pin (`pinnedEloForMover`), D-08 book markers on both marker memos, hoisted `evalChartReady`, D-03 readiness-transition arming, D-04 `sweepCandidates`/`fenAtPly`/`pinnedEloForPly`, the `useGemSweep` call, D-05 `needParentGemGrade` double-work avoidance, sweep-gem display merge on `moveListMarkers`/`boardSquareMarkers`
- `frontend/src/pages/__tests__/Analysis.test.tsx` - `maiaCalls` tracking added to the Maia mock, `isLowPowerDevice` mocked, `lastPrimaryGradingCall`'s index corrected (2 calls/commit -> 3) plus new `lastSweepGradingCall`/`lastLiveGemGradingCall`/`lastSweepMaiaCall`/`lastLiveMaiaCall` helpers, `buildGame()` defaults `opening_ply_count: 0`, four new/extended test cases (SC2 isolation LOAD-BEARING, SC7 transition, SC4 lazy-path extension, SC3 slider-independence)

## Decisions Made

- `pinnedEloForMover` is a `useCallback`, not a module-scope function, because it closes over `isGameMode`/`gameData`/`userProfile` — a stable reference keeps the memos that depend on it from recomputing on every unrelated render.
- D-03's "armed" gate (`sweepArmedForGame`) diverges from the plan's literal `sweptGameIdRef`-only suggestion: this project's ESLint config (`react-hooks/refs`, React Compiler-backed) hard-fails on reading `ref.current` during render, and the armed value is read during render. Implemented as `useState<number | null>` (`armedGameId`) instead — `sweepArmedForGame` reads `evalChartReady` directly for the immediate same-render transition (no ref-flush delay) and `armedGameId` only for sticky protection against a later flicker. The literal string `sweptGameIdRef` no longer appears in the file; documented here since the plan's acceptance criteria specifically grepped for it.
- `needParentGemGrade`'s "avoid double work" extension (documented in the plan's Task 2 action text) is implemented via a companion `sweepResolvedPlies` state, synced from `sweep.gemByPly` by an effect declared textually AFTER the `useGemSweep` call. This breaks what would otherwise be a genuine circular dependency: `needParentGemGrade` is itself fed into the sweep as its `liveBusy` input, so it cannot read the CURRENT render's `sweep` output. A ref-based one-render-lag design was considered first but also hits the `react-hooks/refs` lint rule (a ref read during render), so it was replaced with state — which has the added benefit of actually triggering a re-render when the sweep resolves the ply the user is currently on, rather than silently going stale for a render.
- `sweepCandidates`' `useMemo` dependency array lists `gameData` as a single object, not the three optional-chained sub-paths (`gameData?.moves`, `gameData?.eval_series`, `gameData?.opening_ply_count`) originally written. The React Compiler's "preserve-manual-memoization" ESLint check compares the deps array against its own inferred non-optional property accesses inside the callback body and fails when they don't textually match; `gameData?.x` syntax doesn't match a bare `gameData.x` inference. Depending on the parent object is both type-safe (no risk of accessing a property on `undefined`) and compiler-clean.
- Hook call order ended up `[live maia, sweep's maia]` for `useMaiaEngine` and `[primary grading, sweep's grading, live gemGrading]` for `useStockfishGradingEngine` (not `[..., gemGrading, sweep]` as the test file's first draft assumed) — `useGemSweep` had to be wired in BEFORE `parentGemCandidateSans`/`gemGrading` since `needParentGemGrade` (which both of those depend on) must exist before it can be passed to the sweep's `liveBusy`. The isolation test caught this the first time it ran (both `enabled` values looked inconsistent between polls of the SAME commit) — fixed by correcting the array-index helpers, not by reordering the hooks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed `lastPrimaryGradingCall`'s call-index arithmetic as part of Task 2, not Task 3**
- **Found during:** Task 2 (wiring `useGemSweep` into `Analysis.tsx`)
- **Issue:** Task 2's own `<verify>` step requires `npm test -- --run src/pages/__tests__/Analysis.test.tsx` to stay green, but wiring in `useGemSweep` (which always calls its own dedicated `useStockfishGradingEngine` instance, even when idle) changed the number of grading-hook calls per render commit from 2 to 3 — breaking the existing "Grading run gating" describe block's `lastPrimaryGradingCall()` helper (`gradingCalls[length - 2]`), which assumed exactly 2 calls per commit.
- **Fix:** Updated the index to `length - 3` and the accompanying doc-comment, in the SAME commit as the wiring change (this is the minimal, mechanical portion of the test-file work; Task 2's `<files>` frontmatter only lists `Analysis.tsx`, but the PLAN-level `files_modified` frontmatter authorizes `Analysis.test.tsx` too, and the fix was required to satisfy Task 2's own verify gate).
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Verification:** Full `Analysis.test.tsx` suite green (39/39) before Task 2's commit.
- **Committed in:** `976c3df1` (Task 2 commit)

**2. [Rule 1 - Bug] React Compiler / `react-hooks/refs` violations forced a ref-to-state redesign of the D-03 arming gate and the D-05 double-work guard**
- **Found during:** Task 2, first `npm run lint` pass
- **Issue:** The plan's literal suggestion (`sweptGameIdRef` / `sweepGemByPlyRef`, both `useRef`s read during render) fails this project's ESLint config outright — `react-hooks/refs` treats reading `ref.current` in the render body as a hard error, and a second rule (`react-hooks/preserve-manual-memoization`, the React Compiler) also fired on an unrelated `useMemo` deps mismatch discovered in the same pass.
- **Fix:** Replaced both refs with `useState` (`armedGameId`, `sweepResolvedPlies`), each synced by an effect from the async source. See "Decisions Made" above for the full reasoning (this is a functional improvement, not just a lint appeasement — it also fixes a latent one-render-delay risk the ref design had).
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** `npm run lint` clean; `npx tsc -b --noEmit` clean; full frontend test suite (168 files, 2219 tests) green.
- **Committed in:** `976c3df1` (Task 2 commit)

**3. [Rule 3 - Blocking] Mocked `isLowPowerDevice` in Analysis.test.tsx**
- **Found during:** Task 3, first run of the new SC7/isolation tests
- **Issue:** `useGemSweep.ts`'s device gate (`isLowPowerDevice()`) reads `navigator.hardwareConcurrency`, which jsdom leaves at `0`/`undefined` — every new sweep-dependent test saw the sweep permanently disabled (`enabled: false` always), regardless of eval-data readiness.
- **Fix:** Added `vi.mock('@/lib/engine/workerPool', () => ({ isLowPowerDevice: () => false }))`, mirroring the exact pattern plan 04's own `useGemSweep.test.ts` already established for the hook-layer tests.
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Verification:** SC7/isolation tests pass with the mock in place.
- **Committed in:** `158037b8` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking test-index fix, 1 lint-driven ref-to-state redesign, 1 blocking test-environment mock).
**Impact on plan:** All three were necessary for the plan's own verify gates to pass; none expand scope beyond what the plan already specified. The ref-to-state redesign is the most consequential — it changes the concrete mechanism named in the plan's Artifacts table (`sweptGameIdRef`) but delivers the exact behavior the plan describes (armed on the readiness transition, sticky against flicker, no double work).

## Issues Encountered

- The isolation test's helper functions (`lastLiveGemGradingCall`/`lastSweepGradingCall`) were initially written with the WRONG array indices, based on an assumption about hook call order that turned out to be backwards (see Decisions Made). The test caught this immediately — both `enabled` assertions inside the same `waitFor` poll should have agreed (same commit, same `engineEnabled` variable) but one read true and the other false, which was the tell that two DIFFERENT commits were being compared. Fixed by re-reading the actual file to confirm the real hook order, then swapping the two helpers' indices.

## Revert-Proof Evidence (D-05 yield-to-cursor invariant, page layer)

Per the plan's mandatory Task 3 instructions, the LIVE `gemGrading` hook call was temporarily rewired to prefer a sweep candidate's FEN (`fen: sweep.debugInFlightFen ?? (needParentGemGrade ? parentFen : null)`), with a matching temporary `debugInFlightFen` field added to `useGemSweep`'s return. The isolation test was run to confirm RED, then both temporary edits were reverted and the test re-run to confirm GREEN. Grep/symbol-presence was NOT used as evidence.

**RED (live `gemGrading` bypassed to prefer the sweep's in-flight FEN):**

```
 ❯ src/pages/__tests__/Analysis.test.tsx (42 tests | 1 failed) 1416ms
     × the live grading/Maia instances are never driven with a sweep candidate FEN, even while the sweep is actively mid-cascade

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/pages/__tests__/Analysis.test.tsx > Instance isolation (Phase 172, SEED-106 D-05 / SC2 — LOAD-BEARING) > the live grading/Maia instances are never driven with a sweep candidate FEN, even while the sweep is actively mid-cascade
AssertionError: expected 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RN…' not to be 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RN…' // Object.is equality
 ❯ src/pages/__tests__/Analysis.test.tsx:1488:49
    1486|       // sweep candidate's FEN.
    1487|       expect(lastLiveGemGradingCall()?.fen).not.toBeNull();
    1488|       expect(lastLiveGemGradingCall()?.fen).not.toBe(ROOT_FEN);
       |                                                 ^

 Test Files  1 failed (1)
      Tests  1 failed | 41 skipped (42)
```

(The two FEN strings in the assertion message are literally identical — `expected 'ROOT_FEN' not to be 'ROOT_FEN'` — confirming the live instance's `fen` was contaminated with the sweep's candidate value.)

**GREEN (both temporary edits reverted — `git diff frontend/src/hooks/useGemSweep.ts` confirmed empty, `git diff frontend/src/pages/Analysis.tsx` confirmed no `TEMPORARY`/`debugInFlightFen` residue):**

```
 RUN  v4.1.7 /home/aimfeld/Projects/Python/flawchess/frontend

 Test Files  1 passed (1)
      Tests  42 passed (42)
```

## User Setup Required

None - no external service configuration required.

## Manual UAT (Outstanding — per VALIDATION.md / this plan's `<verification>` section)

The following require a real browser session and are explicitly NOT unit-testable (structural blindness callout applies — `tsc`/`eslint`/`knip`/every automated test pass a sweep that shares an instance with the live path; only the two contention tests, plan 04's at the hook layer and this plan's at the page layer, catch it):

1. Open a real, already-analyzed game; step briskly forward through the mainline. Gem and book badges must already be rendered on plies AHEAD of the cursor, and stepping must not feel slower than today.
2. Play a bot game, open it from the Library while its tier-1 analysis is still running, wait for the evals to land, and confirm the sweep starts with no reload.
3. Judge absolute gem frequency on real games at the raised 0.20 threshold (deliberately not measured pre-ship per D-07 — the Phase 165 TSV is an enriched sample, only its ratios transfer).
4. Open a long game (100+ plies), explore several sidelines, step to the end, scroll back, and confirm an early gem badge is STILL present (the Pitfall-4 eviction check — the sweep's own cache is unbounded/uncapped by design, but this is worth a real-game confirmation).
5. Move the ELO slider on a game with a visible gem: the gem must NOT appear/disappear (D-01 behavior change), while the Maia chart and WDL bar must still respond. (Automated coverage exists for this via SC3/the sticky-latch test; a real-browser pass is still worthwhile given the UI-facing nature of the change.)
6. Visually confirm the muted book-marker badge (`BOOK_MARKER_COLOR`) renders correctly on both the move list and the board corner for a real opening (plan 03's component tests cover the precedence LOGIC, but not a full end-to-end render with real `opening_ply_count` data from the backend).

## Next Phase Readiness

- All seven ROADMAP success criteria for Phase 172 are now observable in the product per this plan's `<success_criteria>` (SC1 cascade, SC2 yield-to-cursor, SC3 rung pin, SC4 lazy path, SC5 raised threshold, SC6 book gate/markers, SC7 transition trigger) — confirmed via the automated test suite; the manual UAT list above remains for a human pass before this phase is considered fully shippable.
- Full frontend gate green: `npm run lint`, `npm run knip`, `npx tsc -b --noEmit`, `npm test -- --run` (168 files, 2219 tests).
- Full backend gate green (phase-wide, since plan 01 touched it): `uv run ruff check app/ tests/`, `uv run ty check app/ tests/`, `uv run pytest -n auto -x` (3287 passed, 18 skipped).
- No blockers. This is the last plan in the phase (wave 3, depends on 172-01..04, all shipped).

---
*Phase: 172-background-gem-sweep-on-analysis-seed-106*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 3 claimed files found on disk; all 4 commit hashes (89899447, 976c3df1, 158037b8, d8f72b88) found in git log.
