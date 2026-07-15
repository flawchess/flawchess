---
phase: 172-background-gem-sweep-on-analysis-seed-106
verified: 2026-07-15T00:15:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: null
---

# Phase 172: Background Gem Sweep on Analysis (SEED-106) Verification Report

**Phase Goal:** Gems resolve for the whole mainline in the background while the analysis board is open, so badges fill in ahead of the cursor instead of at it.
**Verified:** 2026-07-15
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP SC1–SC7, cross-referenced against CONTEXT.md D-01..D-08)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1/D-04 | Free → cheap → expensive cascade; free prefilter uses `played === best_move` (SAN→UCI converted) AND out-of-book | ✓ VERIFIED | `frontend/src/lib/gemSweep.ts:56-83` `selectSweepCandidates` — book gate `if (i < openingPlyCount) continue` (line 67), strict `sanToUci` equality (line 77-78). `useGemSweep.ts` C1 (Maia) gates C2 (Stockfish): a C1 fail (`maiaProbability > GEM_MAIA_MAX_PROB`) calls `resolveCandidate(..., null)` and returns before ever touching the grading instance (lines 251-256). Unit-tested: `gemSweep.test.ts`, `useGemSweep.test.ts`. |
| SC2/D-05 | Sweep never starves the live engines for the current node — dedicated worker instances, two-point yield gate | ✓ VERIFIED (independently re-proven, not just trusted from SUMMARY) | Dedicated instances: `useGemSweep.ts` calls its own `useMaiaEngine` (line 217) and `useStockfishGradingEngine` (line 231) — each hook has its own `useRef<Worker>` (confirmed in `useMaiaEngine.ts:123`, `useStockfishGradingEngine.ts:143`), so two hook call-sites are structurally two Workers. Two yield points confirmed present in current code: (1) `nextSweepDispatch({ ..., liveBusy, ... })` at `useGemSweep.ts:302-309`, (2) idle-callback ref re-check `if (!liveBusyRef.current && effectiveEnabledRef.current)` at line 330. **I independently reverted both gates and reran the tests**: bypassing both turned `useGemSweep.test.ts`'s LOAD-BEARING case RED (`expected 'fen-0' to be null`); restoring turned it GREEN (11/11). I separately reverted the page-layer wiring (rewired the live `gemGrading` fen to prefer a sweep-in-flight FEN via a temporary `debugInFlightFen` field) and reran `Analysis.test.tsx`'s isolation test: RED (`expected 'ROOT_FEN' not to be 'ROOT_FEN'` — the live instance took the sweep's FEN), then reverted and confirmed GREEN. Working tree confirmed clean (`git status --porcelain` empty) after both experiments. |
| SC3/D-01 | Gem rung pinned to each mover's own rating-at-game-time, not the ELO slider | ✓ VERIFIED | `Analysis.tsx:673-676` `pinnedEloForMover` (uses `deriveRawDefault`/`clampToLadderBounds` from `useMaiaEloDefault.ts`, exported per plan 02) replaces `selectedElo` at all 4 sites: `gemC1` (line 1525), `parentGemCandidateSans` (line 1628), the C2 effect's probability lookup and stamped `GemDetail.elo` (lines 1663-1681). `selectedElo` remains for the Maia chart/WDL bar/FlawChess engine (still used 15+ times elsewhere in the file). `useGemSweep`'s `pinnedEloForPly` option reuses the same `pinnedEloForMover` helper via `Analysis.tsx:1581-1587`, so sweep and live path can never disagree on rung. Test: `useMaiaEloDefault.test.ts` (slider-independence regression), `Analysis.test.tsx` SC3 case. |
| SC4/D-03 | Unanalyzed games stay lazy — no sweep, existing Analyze pill unaffected | ✓ VERIFIED | `sweepCandidates` memo returns `[]` whenever `!evalChartReady \|\| gameData?.moves == null \|\| gameData.eval_series == null` (`Analysis.tsx:1573-1576`). `useGemSweep`'s `enabled` requires `sweepArmedForGame && evalChartReady && gradingEnabled` (line 1605). Test: `Analysis.test.tsx` "renders no pill and no Analyze button when active_eval_status is null... never dispatches sweep work." |
| SC5/D-07 | `GEM_MAIA_MAX_PROB` raised 0.10 → 0.20 | ✓ VERIFIED | `frontend/src/lib/gemMove.ts:35` `export const GEM_MAIA_MAX_PROB = 0.2;`. Behavioral test (0.15 probability + passing C2 now classifies as gem) present in `gemMove.test.ts`. |
| SC6/D-06,D-08 | `opening_ply_count` additive/computed-on-read field; book marker on both surfaces with `severity > gem > book` | ✓ VERIFIED | Backend: `app/services/opening_lookup.py:123-150` `find_opening_ply_count` (parallel to, does not touch, `find_opening`); `app/schemas/library.py:138` `opening_ply_count: int = 0`; `app/services/library_service.py:597,627` computes+passes it in `_build_card` (single construction point for both list and single-game paths); zero Alembic migration created (`git status --porcelain alembic/versions/` empty). TS mirror: `frontend/src/types/library.ts:101`. Precedence: `VariationTree.tsx:73-83` `resolveMarkerIcon` — severity clause first, `flaw?.gem` second, `flaw?.book` last. `boardMarkers.tsx:126,143,163` — gem branch before book branch before severity fallback. Wiring: `Analysis.tsx` `moveListMarkers` sets `book: true` gated on `plyIndex < openingPlyCount` AND no existing severity/gem (lines 1812-1830); `boardSquareMarkers` appends book gated on no existing severity/gem (lines 2301-2316). All confirmed by grep and read; unit tests present at both the component layer (`VariationTree.test.tsx`, `boardMarkers.test.tsx` — severity+book, gem+book, book-only cases) and the opening-lookup layer (`TestFindOpeningPlyCount`, 6 methods, all pass: `uv run pytest tests/test_opening_lookup.py` 72 passed). |
| SC7/D-03 | Bot game opened mid-tier-1-analysis is swept the moment evals land, no reload | ✓ VERIFIED | `evalChartReady` hoisted above the sweep block (`Analysis.tsx:623`). `sweepArmedForGame = gameId != null && (evalChartReady \|\| armedGameId === gameId)` (line 646) reads `evalChartReady` directly on the SAME render it flips true (no ref-flush delay), with `armedGameId` state providing sticky protection against a later flicker (set by an effect keyed on `[evalChartReady, gameId, armedGameId]`, lines 641-646). This is a reactive-state substitute for the plan's originally-suggested `sweptGameIdRef`, not a functional regression — see Deviation Assessment below. Test: `Analysis.test.tsx` SC7 case (eval_series transitions null → populated on an already-mounted page; sweep dispatches only after). |
| D-02 | Scope fence: no gem persistence, no backend gem store, no Library-card/stats surfacing | ✓ VERIFIED | `grep -rn "gem" app/schemas/library.py app/services/library_service.py` shows only a doc-comment reference to "gem sweep" on the `opening_ply_count` field, no gem-storage fields. `grep` for `gem` in `frontend/src/components/library/` and `Library.tsx` found no genuine gem UI (only an unrelated substring match in `EvalChart.tsx`, "engagement"). Maia remains ONNX-only in the browser — no Python Maia dependency introduced. |

**Score:** 8/8 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/opening_lookup.py` | new `find_opening_ply_count` | ✓ VERIFIED | Exists, tested, `find_opening` untouched |
| `app/schemas/library.py` | `GameFlawCard.opening_ply_count: int = 0` | ✓ VERIFIED | Present, default 0 |
| `app/services/library_service.py` | computes+passes field in `_build_card` | ✓ VERIFIED | Unconditional computation, both list/single-game paths |
| `frontend/src/types/library.ts` | `opening_ply_count: number` mirror | ✓ VERIFIED | Non-optional, present |
| `frontend/src/lib/gemMove.ts` | `GEM_MAIA_MAX_PROB = 0.2` | ✓ VERIFIED | Present |
| `frontend/src/hooks/useMaiaEloDefault.ts` | exported `deriveRawDefault`/`clampToLadderBounds` | ✓ VERIFIED | Both exported, consumed by `Analysis.tsx` and `useGemSweep.ts` |
| `frontend/src/lib/gemSweep.ts` | `selectSweepCandidates`, `nextSweepDispatch` | ✓ VERIFIED | Pure, worker-free, zero React/Worker imports |
| `frontend/src/lib/theme.ts` | `BOOK_MARKER_COLOR` | ✓ VERIFIED | `oklch(0.60 0.04 250)`, matches UI-SPEC verbatim |
| `frontend/src/lib/bookGlyph.ts` | `BOOK_GLYPH` | ✓ VERIFIED | One-record-two-consumers, no raw color literal |
| `frontend/src/components/icons/BookIcon.tsx` | `BookIcon` | ✓ VERIFIED | `BookOpen` glyph, "Opening theory" title, no data-testid (glance-only, per UI-SPEC) |
| `frontend/src/components/analysis/VariationTree.tsx` | `resolveMarkerIcon` book clause, `FlawMarkerEntry.book` | ✓ VERIFIED | Precedence chain confirmed by source read |
| `frontend/src/components/board/boardMarkers.tsx` | `SquareMarker.book`, badge branch | ✓ VERIFIED | Ordering confirmed by source read |
| `frontend/src/hooks/useGemSweep.ts` | new hook, dedicated workers | ✓ VERIFIED | Confirmed via source + independent revert test |
| `frontend/src/hooks/useStockfishGradingEngine.ts` | optional `movetimeMs` | ✓ VERIFIED | Defaults to existing cap; sweep passes 1000ms |
| `frontend/src/lib/engine/workerPool.ts` | `isLowPowerDevice()` | ✓ VERIFIED | Extracted, reused by `useGemSweep` |
| `frontend/src/pages/Analysis.tsx` | full wiring (rung pin, sweep call, markers) | ✓ VERIFIED | All sites confirmed by direct source read |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `Analysis.tsx` gem block | `pinnedEloForMover` | Replaces `selectedElo` at 4 sites | ✓ WIRED | Confirmed no `selectedElo` reads remain in the gem-detection region |
| `useGemSweep` | dedicated `useMaiaEngine`/`useStockfishGradingEngine` | Own hook calls, never the live instances | ✓ WIRED | Independently reproduced red-then-green at both hook and page layers |
| `gemSweep.ts` prefilter | `EvalPoint.best_move` (UCI) | `sanToUci(parentFen, playedSan)` conversion before comparison | ✓ WIRED | SAN/UCI trap has a dedicated regression test (`Nf3` vs `g1f3`) |
| `Analysis.tsx` sweep results | `moveListMarkers`/`boardSquareMarkers` | Read-time union, NOT written into `gemByNode`'s FIFO-256 cache | ✓ WIRED | Confirmed: `setGemByNode` appears once in the file (only the live C2 effect writes it); sweep's `gemByPly` is folded in as a second read source |
| `opening_ply_count` | sweep prefilter book gate + book markers | `selectSweepCandidates(..., openingPlyCount, ...)` and `plyIndex < openingPlyCount` checks | ✓ WIRED | Confirmed at both the pure-module level and the two `Analysis.tsx` marker call sites |

### Behavioral Spot-Checks (independently executed, not trusted from SUMMARY)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full targeted test suite for this phase's files | `npm test -- --run` on 7 phase-relevant test files | 138/138 passed | ✓ PASS |
| Backend opening-lookup + library-service tests | `uv run pytest tests/test_opening_lookup.py tests/services/test_library_service.py -q` | 72 passed | ✓ PASS |
| D-05 hook-layer revert proof (independently reproduced) | Bypassed both `liveBusy` gates in `useGemSweep.ts`, ran `useGemSweep.test.ts` | RED (1 failed: `expected 'fen-0' to be null`), then restored → GREEN (11/11) | ✓ PASS |
| D-05 page-layer revert proof (independently reproduced) | Rewired live `gemGrading.fen` to prefer a sweep in-flight FEN (temp `debugInFlightFen`), ran the isolation test | RED (`expected 'ROOT_FEN' not to be 'ROOT_FEN'`), then restored → GREEN (1/1) | ✓ PASS |
| `tsc -b --noEmit` after revert experiments | `npx tsc -b --noEmit` | Zero errors | ✓ PASS |
| Working tree clean after experiments | `git status --porcelain` | Empty | ✓ PASS |

### Requirements Coverage

Phase requirements: none (SEED-106 direct, D-01–D-08 locked). All 8 locked decisions (D-01 through D-08) are individually addressed above and verified against source, not SUMMARY narration.

### Anti-Patterns Found

`grep` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|not yet implemented|coming soon` across all 16 files this phase modified: zero matches. No debt markers, no stub returns, no empty handlers found in the gem-sweep, book-marker, or opening-lookup code paths.

### Deviation Assessment: 172-05's `useState` substitution for the plan's suggested refs

The plan (`172-05-PLAN.md`) suggested `sweptGameIdRef`/`sweepGemByPlyRef` as `useRef`s. The executor substituted `useState` (`armedGameId`, `sweepResolvedPlies`) because this project's ESLint config (`react-hooks/refs`, React Compiler-backed) hard-fails on reading `ref.current` during render, and both values are read during render (`sweepArmedForGame` computation, `needParentGemGrade` computation).

**Judgment: this deviation preserves the intended behavior and is arguably an improvement.**

- `sweepArmedForGame = gameId != null && (evalChartReady || armedGameId === gameId)` reads the reactive `evalChartReady` value directly for the same-render transition — there is no one-render lag risk a stale ref read could introduce; if anything this is *tighter* than a ref would have been, since a ref set inside an effect only becomes visible on the render *after* the effect runs, whereas this reads the live boolean immediately.
- `armedGameId` supplies exactly the "sticky" behavior the plan wanted (protection against `evalChartReady` flickering false again for the same game) via a `useEffect` that sets it once armed and never unsets it for that `gameId`.
- `sweepResolvedPlies`'s one-render-lag design (synced from `sweep.gemByPly` by an effect declared textually after the `useGemSweep` call) correctly breaks what would otherwise be a genuine circular dependency (`needParentGemGrade` feeds the sweep's own `liveBusy` input, so it cannot read the *same-render* `sweep` output) — a ref-based version would have hit the identical lint rule and offered no functional advantage (a ref set in an effect is populated on the same lag a state update would be, but doesn't trigger a re-render when the sweep resolves the ply the user is currently viewing — the state version does).

No regression in the D-03 transition-triggering behavior or the D-05 double-work avoidance was found; the SC7 test (transition case) and the D-05 revert-proofs both pass against this actual implementation, not a hypothetical ref-based one.

### Human Verification Required

None required to determine phase-goal achievement — all locked decisions are independently verifiable via source + tests. Manual UAT items remain outstanding per 172-05-SUMMARY.md's own list (perceived-latency feel, absolute gem frequency judgment, long-game cache-eviction real-world confirmation, visual book-marker confirmation) — these are explicitly non-blocking per VALIDATION.md's "structural blindness" framing (perceived latency and absolute gem frequency are, by design, not unit-testable and were deferred to real-game UAT in the locked decisions themselves, not omitted from this phase's engineering).

### Gaps Summary

None found. All 7 ROADMAP success criteria and all 8 locked decisions (D-01 through D-08) are implemented and verified against the actual codebase, not SUMMARY claims. The two invariants the user specifically flagged for scrutiny — D-05's dual yield gate and D-04's book-ply exclusion — were independently re-proven by reverting the actual code and observing red-then-green, not merely grepped for.

One minor, non-blocking housekeeping note: `.planning/seeds/SEED-106-background-gem-sweep-on-analysis.md` has not been moved to `.planning/seeds/closed/` despite this phase fully implementing it (per CLAUDE.md's seed-lifecycle convention). This does not affect code correctness or phase-goal achievement; flagging for the developer's awareness, not as a gap.

---

_Verified: 2026-07-15_
_Verifier: Claude (gsd-verifier)_
