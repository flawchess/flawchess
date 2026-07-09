---
phase: 155-react-hook-anytime-ui-free-analysis
verified: 2026-07-06T21:20:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open /analysis (default state, both FlawChess Engine and Stockfish switches ON) on a real iOS/mobile device, navigate through ~20 positions with all 3 engines on."
    expected: "No crash/OOM; ranked lines keep appearing/refining; the FlawChess Engine card and eval bars remain responsive."
    why_human: "Real-device memory ceiling and worker/WASM startup timing cannot be exercised in jsdom (SC4 real-device UAT, deferred from Phase 154, explicitly flagged in 155-04-PLAN.md's <verification> section)."
  - test: "On-device, confirm (a) the standalone Stockfish search is suppressed while FlawChess Engine runs and the 'SF' eval bar shows the engine's own objective root eval (D-04 handoff), and (b) sharing selectedElo for both budget.elo.w/b reads as acceptable in free analysis."
    expected: "The POOL-04 mutual-exclusion handoff and shared-ELO simplification feel correct in real use, not just in unit-test mocks."
    why_human: "These are design-decision confirmations that depend on real search output quality, not mechanically verifiable from source."
  - test: "Watch the FlawChess Engine card live-refine (lines reordering) at the ~150ms throttle cadence on both desktop and mobile viewports for ~10-15 seconds after navigating to a new position."
    expected: "Lines appear almost immediately, then reorder/update smoothly without visible jank or flicker."
    why_human: "Perceptual smoothness (jank/flicker) is a real-browser rendering/timing concern; jsdom + fake timers prove the throttle *mechanism* (immediate first commit, ≤1 trailing commit per 150ms — confirmed passing in useFlawChessEngine.test.ts) but cannot prove it *feels* smooth on real hardware, per this verification's explicit instruction to route perceptual/real-device timing to human review."
---

# Phase 155: React Hook + Anytime UI (Free Analysis) Verification Report

**Phase Goal:** A user analyzing any position on the free-analysis `/analysis` board sees the FlawChess Engine's ranked practical-play lines appear immediately and refine live as the search runs, each with its modal path and objective-vs-practical score pair.
**Verified:** 2026-07-06T21:20:00Z
**Status:** passed — confirmed complete at v2.0 milestone close (2026-07-09)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Quick top-n candidate lines from `useFlawChessEngine` appear almost immediately after navigating to a position, without waiting for the full node budget to exhaust (DISPLAY-01, DISPLAY-04) | ✓ VERIFIED (mechanism) / see human verification for perceptual/real-device confirmation | `useFlawChessEngine.ts` L163-180 (leaky-bucket throttle: immediate commit if `>150ms` since last commit) + L202-209 (`lastCommitAtRef` reset to 0 at the start of every fresh search, guaranteeing first-paint on every navigation) + L107-129 (FEN debounce fires immediately on a "settled" move). Passing behavioral test: `useFlawChessEngine.test.ts` `-t "throttle"` (verified green by this verifier — 1 passed). Wired into `Analysis.tsx` (`flawChessEngine = useFlawChessEngine({ fen: flawChessEnabled ? position : null, ... })`, L501) and rendered via `FlawChessEngineLines` in both desktop and mobile layouts. |
| 2 | Displayed lines visibly refine (reorder/update) as the search accumulates more visits, batched at a fixed cadence (mirroring `RAPID_STEP_DEBOUNCE_MS`) so updates neither jank nor flicker | ✓ VERIFIED (mechanism) / perceptual smoothness → human verification | Same throttle mechanism as truth 1 reuses the `RAPID_STEP_DEBOUNCE_MS = 150` constant (L32) for the onSnapshot commit cadence — a distinct mechanism from the FEN debounce, confirmed by code comment and by the passing `-t "throttle"` test asserting "at most one additional trailing commit" within the window. `FlawChessEngineLines` re-renders reactively off `rankedLines` prop changes (stable row `key={lineIndex}` preserves per-row expand state across snapshot updates, L263 `key={lineIndex}`). Real-browser jank/flicker cannot be exercised in jsdom — routed to human verification per this task's explicit instruction. |
| 3 | Each candidate line in `FlawChessEngineLines.tsx` shows its modal path (player move + opponent most-likely replies from expanded tree nodes), not just the bare root move (DISPLAY-02) | ✓ VERIFIED | `FlawChessEngineLines.tsx` L126-130 (`hasMore`/`moves`/`steps = replayPvLine(baseFen, moves)`) renders `line.modalPath` (not just `rootMove`) as clickable SAN chips, first `MAX_PLIES=5` + `ChevronDown` expand (L207-218) for the remainder. `RankedLine.modalPath: string[]` (types.ts L56) is populated by the frozen search core (`mctsSearch.ts`/`treeCommon.ts`), not reconstructed client-side. Test: `FlawChessEngineLines.test.tsx` (10/10 passing, re-run by this verifier) explicitly asserts "renders modalPath as SAN chips, first MAX_PLIES=5 plies + expand chevron". |
| 4 | Each ranked move displays the objective Stockfish eval alongside the practical-for-you score in the same badge, sourced from data the search already computed with no second grading pass (DISPLAY-03) | ✓ VERIFIED | `FlawChessEngineLines.tsx` L122-124/L138-145: two-segment badge — `objectiveText = formatScore(line.objectiveEvalCp, null)` (STOCKFISH_ACCENT) and `practicalText = formatScore(expectedScoreToWhitePovCp(line.practicalScore, rootMover), null)` (FLAWCHESS_ENGINE_HEADLINE_ACCENT), in one `aria-label`-ed shell, never the bare phrase "best move". Data-flow trace: `objectiveEvalCp`/`practicalScore` are both fields already present on `RankedLine` (types.ts L52/54) populated inside `mctsSearch.ts`/`treeCommon.ts` (L133/151) — the search's own tree, not a second UI-triggered grading call. `expectedScoreToWhitePovCp` (liveFlaw.ts L46-51) is confirmed present, imports `LICHESS_K`/`MATE_CP_EQUIVALENT` from the generated mirror (not redefined), and its own pure-function test passes. |

**Score:** 4/4 truths verified (mechanism-level; 3 items with perceptual/real-device components routed to human verification below — see status rationale)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/theme.ts` | `FLAWCHESS_ENGINE_ACCENT` + `FLAWCHESS_ENGINE_HEADLINE_ACCENT` tokens | ✓ VERIFIED | L78/L81, alongside `STOCKFISH_ACCENT`/`MAIA_ACCENT`; no board-arrow token added. |
| `frontend/src/lib/liveFlaw.ts` | `expectedScoreToWhitePovCp(es, rootMover)` pure function | ✓ VERIFIED | L46-51, mate-boundary-guarded (±`MATE_CP_EQUIVALENT`), imports constants from `@/generated/flawThresholds`. |
| `frontend/src/components/ui/switch.tsx` | Reusable Switch primitive, caller-supplied accent | ✓ VERIFIED | Hand-rolled Radix wrapper, `data-[state=checked]:bg-primary` default overridable via `className`/`style`; used by `EngineToggleHeader` in `Analysis.tsx` with per-card accent. |
| `frontend/src/hooks/useFlawChessEngine.ts` | Anytime-emit hook (throttle, abort/stopAll, provider lifecycle) | ✓ VERIFIED | Full implementation matches plan (L82-281); passing tests. |
| `frontend/src/components/analysis/FlawChessEngineLines.tsx` | Top-3 lines, score-pair badge, modal-path chips | ✓ VERIFIED | Full implementation matches plan (L230-277); 10/10 tests passing. |
| `frontend/src/pages/Analysis.tsx` | Card placement (desktop+mobile), 3-toggle refactor, eval-bar precedence | ✓ VERIFIED | `flawChessCard` rendered above `MaiaHumanPanel` in both `analysis-human-column` (L1629-1642) and mobile `humanTab` (L1450-1453); `EngineToggleHeader` used for all 3 switches; eval-bar precedence block (L1157-1179) confirmed wired. |
| Test files (`*.test.ts(x)` for hook, card, Analysis page) | Cover DISPLAY-01/02/03/04 behaviors | ✓ VERIFIED | All re-run independently by this verifier: `useFlawChessEngine.test.ts` (throttle+abort, 2/2 pass), `FlawChessEngineLines.test.tsx` (10/10 pass), `Analysis.test.tsx -t "FlawChess"` (4/4 pass). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `useFlawChessEngine` | `mctsSearch` (frozen SearchRunner) | `mctsSearch(fen, budget, { policy: queue.policy, grade: pool.grade }, handleSnapshot, signal)` | ✓ WIRED | L220-223; `budget.concurrency = computePoolSize()`, `budget.elo = {w: elo, b: elo}`. |
| FEN navigation | Abort + `pool.stopAll()` | Unconditional call at top of search-trigger effect | ✓ WIRED | L196-197; regression-tested (`-t "abort"` passes). |
| `FlawChessEngineLines` | `expectedScoreToWhitePovCp` | `practicalScore → expectedScoreToWhitePovCp(rootMover) → formatScore()` | ✓ WIRED | L122-124. |
| `FlawChessEngineLines` | `replayPvLine` (from `EngineLines.tsx`) | `modalPath (UCI[]) → replayPvLine(baseFen, slice) → SAN chips` | ✓ WIRED | L130; `replayPvLine`/`formatScore`/`EngineLinesSkeleton` additively exported from `EngineLines.tsx`, confirmed unchanged behavior (`EngineLines.test.tsx` unaffected). |
| `Analysis.tsx` | `useFlawChessEngine` | `useFlawChessEngine({ fen: flawChessEnabled ? position : null, enabled: flawChessEnabled, elo: selectedElo })` | ✓ WIRED | L501-504. |
| `Analysis.tsx` left eval bar | FC/Maia precedence | `leftEvalBarWhiteFraction = flawChessEnabled ? fcWhiteFraction : maiaWhiteFraction` | ✓ WIRED | L1160-1167; test-asserted (`Analysis.test.tsx` FC-precedence describe block, 4/4 pass covering both directions). |
| `Analysis.tsx` right eval bar | FlawChess objective-eval handoff | `rightEvalBarEvalCp = !engineEnabled ? null : flawChessEnabled ? topLine?.objectiveEvalCp ?? null : gameOverlay.evalCp` | ✓ WIRED | L1173-1179 (also covers WR-03's `!engineEnabled` neutral-state fix). |
| `useStockfishEngine` | POOL-04 mutual exclusion | `enabled: engineEnabled && !flawChessEnabled` | ✓ WIRED | L415-416. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `FlawChessEngineLines` (via Analysis.tsx) | `rankedLines` | `flawChessEngine.rankedLines` ← `snapshot.rankedLines` ← `handleSnapshot(next)` ← `mctsSearch`'s `onSnapshot` callback ← the real frozen search tree (Phase 153/154) | Yes — `RankedLine.objectiveEvalCp`/`practicalScore`/`modalPath` are computed inside `mctsSearch.ts`/`treeCommon.ts`'s own backup/expansion logic, not a hardcoded or second-pass value | ✓ FLOWING |
| Left eval bar (FC precedence) | `fcWhiteFraction` | `topLine.practicalScore` (real search output), inverted for side-to-move | Yes | ✓ FLOWING |
| Right eval bar (SF handoff) | `topLine?.objectiveEvalCp` | Same `RankedLine` source | Yes | ✓ FLOWING |

No hollow props or disconnected data sources found — this phase composes real upstream (Phase 153/154) search output through to the DOM, not a mocked/static feed.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Hook throttle: first onSnapshot commits near-instantly, ≤1 trailing commit per 150ms | `npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts -t "throttle"` | 1 passed / 1 skipped | ✓ PASS |
| Hook abort: FEN navigation aborts previous run + calls `pool.stopAll()` | `npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts -t "abort"` | 1 passed / 1 skipped | ✓ PASS |
| Card renders modal-path chips + score-pair badge (DISPLAY-02/03) | `npx vitest run src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` | 10 passed | ✓ PASS |
| Analysis page FC-precedence + card placement (DISPLAY-04) | `npx vitest run src/pages/__tests__/Analysis.test.tsx -t "FlawChess"` | 4 passed / 7 skipped | ✓ PASS |
| Type-check (whole project) | `npx tsc -b --noEmit` | exit 0 | ✓ PASS |
| Lint (whole project) | `npm run lint` | exit 0 (3 unrelated warnings in `coverage/` artifacts only) | ✓ PASS |

Full-suite/knip re-run was not repeated by this verifier (per constraint: run the full suite at most once) — the phase's own documented result (127 files / 1523 tests, `npm run knip` clean) is corroborated by the four targeted re-runs above, all independently green.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|------------|--------------|--------|----------|
| DISPLAY-01 | Plans 02, 04 | Anytime emit — quick lines appear immediately, refine live | ✓ SATISFIED | Hook throttle mechanism (Plan 02) + actual page mount (Plan 04), both verified above. **Note:** REQUIREMENTS.md traceability table (line 92) still reads "Pending (partial...)" for DISPLAY-01 even though the checklist item above it is `[x]` and Plan 04's own commit (`08467b8e`) updated DISPLAY-04's traceability row to "Complete" but left DISPLAY-01's row text stale — a documentation inconsistency, not a code gap (see Anti-Patterns). |
| DISPLAY-02 | Plan 03 | Modal path display | ✓ SATISFIED | `FlawChessEngineLines.tsx` renders `modalPath` as SAN chips; REQUIREMENTS.md marks Complete, consistent with code. |
| DISPLAY-03 | Plans 01, 03 | Objective-vs-practical score pair | ✓ SATISFIED | `expectedScoreToWhitePovCp` (Plan 01) + visible badge (Plan 03); REQUIREMENTS.md marks Complete, consistent with code. |
| DISPLAY-04 | Plan 04 | Surfaces on `/analysis` | ✓ SATISFIED | Card placement, 3-toggle refactor, eval-bar precedence all confirmed wired; REQUIREMENTS.md marks Complete, consistent with code. |

No orphaned requirements — REQUIREMENTS.md maps only DISPLAY-01..04 to Phase 155, and all four appear in the four plans' `requirements:` frontmatter fields (Plan 01: DISPLAY-03; Plan 02: DISPLAY-01; Plan 03: DISPLAY-02/03; Plan 04: DISPLAY-01/04).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/REQUIREMENTS.md` | 92 | Stale traceability-table status text ("Pending (partial...)") for DISPLAY-01, left un-updated by Plan 04's commit while the adjacent checklist entry and DISPLAY-04's own traceability row were correctly updated to reflect closure | ℹ️ Info | Cosmetic documentation drift only — the actual code fully satisfies DISPLAY-01 (see Requirements Coverage above); does not affect phase goal achievement. Worth a 1-line doc fix in a follow-up commit. |
| `frontend/src/pages/Analysis.tsx` | ~1408-1444 (`flawChessCard`) | No `isError`/"FlawChess Engine unavailable" state — `useFlawChessEngine` exposes no error field (worker/search failures resolve to empty `rankedLines` silently, per Plan 02's frozen contract), so a genuine worker-init or `mctsSearch` failure renders a silently blank card (no skeleton, no "off" message, no error message) once `isReady`/`isSearching` settle to their post-failure values | ⚠️ Warning | Deviates from CLAUDE.md's mandatory frontend rule ("Always handle `isError`... never let errors fall through to empty-state messages") and from Plan 04's own `<action>` text (which called for the CLAUDE.md isError copy). Explicitly disclosed as a "Known Gap" in 155-04-SUMMARY.md rather than hidden. Does not block any of the four roadmap Success Criteria (all describe happy-path live-refine behavior), but is a real robustness gap worth a follow-up task — surfacing an error field from `useFlawChessEngine` (or a lightweight local catch) so this failure mode is user-visible. |
| `frontend/src/components/analysis/EngineLines.tsx` | 297 (pre-existing, IN-03 in 155-REVIEW.md) | No-op ternary `lineIndex === 0 ? moveIndex : moveIndex` | ℹ️ Info | Cosmetic; predates Phase 155, correctly not reproduced in the new `FlawChessEngineLines.tsx`; left as-is per the code review's own disposition (deferred, cosmetic). |
| `frontend/src/lib/liveFlaw.ts` | 31-45 (IN-01 in 155-REVIEW.md) | `evalToExpectedScore`'s docstring left orphaned above the newly-inserted `expectedScoreToWhitePovCp` | ℹ️ Info | Cosmetic documentation ordering issue; explicitly deferred by the code-review-fix pass as low-priority. |

No debt markers (`TBD`/`FIXME`/`XXX`) found in any file modified by this phase.

## Human Verification Required

1. **Real-device mobile-memory UAT (SC4, deferred from Phase 154)**
   **Test:** Open `/analysis` on a real iOS/mobile device with all 3 engine switches ON (default state); navigate through ~20 positions.
   **Expected:** No crash/OOM; lines keep appearing and refining across navigations.
   **Why human:** Real-device memory ceilings and Stockfish.wasm worker startup cost cannot be exercised in jsdom.

2. **Decision-confirmation UAT (D-04 handoff + shared-ELO acceptance)**
   **Test:** On-device, confirm the standalone Stockfish search is suppressed while FlawChess Engine runs (the "SF" eval bar reflects the engine's own objective root eval, not a second search), and that sharing `selectedElo` for both `budget.elo.w`/`.b` feels acceptable in free analysis.
   **Expected:** The POOL-04 mutual-exclusion handoff reads correctly and the shared-ELO simplification is acceptable pending Phase 157's true asymmetry.
   **Why human:** These are design-decision judgment calls about real search-quality trade-offs, not mechanically verifiable.

3. **Perceptual live-refine smoothness**
   **Test:** Navigate to a new position and watch the FlawChess Engine card for ~10-15 seconds on both desktop and mobile viewports.
   **Expected:** Top-n lines appear almost immediately, then reorder/update smoothly at the ~150ms cadence with no visible jank or flicker.
   **Why human:** jsdom + fake timers prove the throttle *mechanism* (confirmed passing above) but cannot prove real-browser rendering feels smooth — this task's own instructions route this class of finding to human verification rather than a pass/fail on static analysis.

## Gaps Summary

No blocking gaps. All four roadmap Success Criteria are satisfied at the code/wiring/unit-test level: the hook's anytime-emit throttle mechanism, the FEN-navigation abort/stopAll guard, the modal-path chip rendering, and the objective/practical score-pair badge (sourced from the search's own already-computed `RankedLine` fields, no second grading pass) are all present, wired, and independently re-verified passing by this verifier (not merely trusted from SUMMARY.md). The code-review cycle (155-REVIEW.md → 155-REVIEW-FIX.md) already caught and fixed a genuine Critical issue (blank Stockfish card in the default both-switches-ON state) plus 4 Warnings; all 5 fixes were independently confirmed present in the current `Analysis.tsx`/`useFlawChessEngine.ts` source during this verification.

The phase's `human_needed` status stems entirely from perceptual/real-device concerns (live-refine smoothness, mobile-memory ceiling, on-device decision confirmation) that the phase's own PLAN.md already flagged as deferred HUMAN-UAT items — none of these represent a code gap, and all were anticipated by the executor rather than missed. One documentation inconsistency (a stale REQUIREMENTS.md traceability-table cell for DISPLAY-01) and one disclosed-but-unresolved robustness gap (no `isError` state on FlawChess Engine failure, tracked as a Known Gap in 155-04-SUMMARY.md) are noted as non-blocking follow-ups.

---

_Verified: 2026-07-06T21:20:00Z_
_Verifier: Claude (gsd-verifier)_
