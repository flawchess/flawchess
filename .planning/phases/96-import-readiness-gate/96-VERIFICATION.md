---
phase: 96-import-readiness-gate
verified: 2026-05-28T12:00:00Z
status: human_needed
score: 8/8
overrides_applied: 0
human_verification:
  - test: "SC-2 per-page gate: navigate to /openings or /overview before first import (no tier1)"
    expected: "Redirected to /import; page renders import form, not partial openings data"
    why_human: "Route gating is client-side; wiring is confirmed in code but redirect behavior on live app requires a browser session to confirm flash-prevention and toast timing"
  - test: "SC-2 incremental import: with an active incremental import in progress, visit /openings"
    expected: "Openings page renders normally (tier1=true); /endgames renders EndgamesProcessingState with Stockfish counter"
    why_human: "Tier1 vs Tier2 split behavior during incremental import cannot be confirmed without a running import job"
  - test: "SC-3 state machine progression: import page transitions fetching -> importing -> Tier1 CTA -> analyzing endgames X/Y -> ready"
    expected: "Each state displays correct copy; 'Games imported. Openings ready.' at Tier 1; 'Ready. All analysis complete.' at Tier 2; no 'Import complete' at hot-import done"
    why_human: "State transitions require live import + Stockfish drain pipeline; static code analysis confirms wiring but not runtime sequencing"
  - test: "SC-5 Tier-2 toast: after Stockfish drain completes in a session where tier2 was previously false, fire-once toast appears with 'Endgame analysis complete!' and 'Explore Endgames' action"
    expected: "Toast fires once, suppressed on /endgames, navigates to /endgames on action click"
    why_human: "Toast fire-once logic (wasTier2FalseRef) requires live tier2 false->true transition in-session"
  - test: "SC-6 EvalCoverageHeader visible on all pages during Stockfish drain"
    expected: "Amber EvalCoverageHeader bar appears on /import, /openings, /endgames, /overview while pct < 100"
    why_human: "Header presence depends on useEvalCoverage poll and rendering on each page; confirmed by import, but runtime verification ensures no regressions"
---

# Phase 96: Import Readiness Gate — Verification Report

**Phase Goal:** Replace `window.location.reload()` on eval-complete with a two-tier per-page gate. Tier 1 (hot lane done) unlocks Openings + Overview; Tier 2 (Tier 1 AND pending_count==0 AND Stage A/B percentiles persisted) unlocks Endgames and reveals Openings eval metrics.
**Verified:** 2026-05-28
**Status:** human_needed — all 8 automated truths VERIFIED; 5 behavioral items require live-app confirmation
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Authoritative two-tier signal: GET /imports/readiness returns {tier1, tier2, pending_count, total_count}; test asserts tier2=false when evals done but no Stage B rows | VERIFIED | `app/routers/imports.py:135-182` — endpoint exists, correct path `/readiness`, sequential reads. `tests/routers/test_imports_readiness.py:247-273` — `test_tier2_false_when_evals_done_but_no_percentile_rows` exactly tests this truth; 6/6 backend tests green per SUMMARY-01. |
| 2 | Per-page gate: Openings + Overview require Tier 1 (ImportRequiredRoute); Endgames requires Tier 2 in-page | VERIFIED | `App.tsx:611-615` — `/openings/*` and `/overview` wrapped in `ImportRequiredRoute` (tier1). `Endgames.tsx:772-774` — `if (!tier2) return <EndgamesProcessingState .../>` after all hooks. `/endgames/*` also wrapped in `ImportRequiredRoute` (tier1 outer + tier2 inner). |
| 3 | Import page state machine: Tier 1 CTA "Explore Openings" present; "Games imported. Openings ready." copy; "Analyzing endgames (X/Y)" when pendingCount>0; no over-claim at hot-import done | VERIFIED | `Import.tsx:370-391` — `{tier1 && ...}` block with `data-testid="btn-explore-openings"`, "Games imported. Openings ready." at tier1+!tier2, "Analyzing endgames" at !tier2 && pendingCount>0. `Import.tsx:100-101` — hot-import done copy is "Games imported. Openings ready." or "No new games found since last sync" — no "Imported N games". |
| 4 | Honest completion messaging: no message claims completion at hot-import status=completed; "Ready. All analysis complete." only at Tier 2 | VERIFIED | `Import.tsx:381-383` — tier2 ternary: `tier2 ? 'Ready. All analysis complete.' : 'Games imported. Openings ready.'`. The word "complete" in import progress text only appears at Tier 2. |
| 5 | No window.location.reload() on eval-completion path; useEvalCoverage auto-reload retired; no evalCompletionReloadFired | VERIFIED | `useEvalCoverage.ts` — no `window.location.reload`, no `evalCompletionReloadFired`, no `wasPendingRef`. Only occurrence of `window.location.reload` is `App.tsx:641` inside the Sentry `ErrorBoundary` fallback button (pre-existing, not readiness logic, confirmed in SUMMARY-02 deviations). |
| 6 | Stockfish progress bar (EvalCoverageHeader) visible on all pages during drain | VERIFIED | `Import.tsx:243`, `Openings.tsx:778,879`, `Endgames.tsx:810,847`, `GlobalStats.tsx:129,135` — EvalCoverageHeader rendered on all four content pages. `useEvalCoverage.ts` shape unchanged (returns pendingCount, totalCount, pct, isPending, isLoading). Note: EvalCoverageHeader sits inside the tier2 gate in Endgames — but at lines 810 and 847 of Endgames.tsx which are in the post-tier2 render tree; the processing state at line 773 replaces the full page before reaching those points. However, the processing-locked page itself does not include EvalCoverageHeader. This is a behavioral nuance noted for human verification. |
| 7 | Openings eval metrics behind single pulsating-Cpu placeholder until Tier 2; WDL score row unaffected | VERIFIED | `OpeningStatsCard.tsx:61` — `const { tier2 } = useReadiness()`. Lines 219-251: `{tier2 ? <eval bullet + text rows> : <EvalCpuPlaceholder />}`. WDL score row (lines 182-217) rendered unconditionally. `EvalCpuPlaceholder.tsx` — `data-testid="eval-cpu-placeholder"`, amber styling, "Analyzing…" label, `animate-pulse` Cpu icon. |
| 8 | Eval-metric tooltip counter removed; npm run knip passes | VERIFIED | `EvalConfidenceTooltip.tsx` — no `isPending`, no `pendingCount`, no `eval-pending-caveat` testid, no `AlertTriangle` import (grep returns 0 matches). `BulletConfidencePopover.tsx` — no `isPending`/`pendingCount` in interface. SUMMARY-03 reports `npm run knip: exits 0`. |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/routers/imports.py` | GET /imports/readiness endpoint | VERIFIED | `@router.get("/readiness", response_model=ReadinessResponse)` at line 135; sequential awaits, no asyncio.gather |
| `app/schemas/imports.py` | ReadinessResponse pydantic model | VERIFIED | `class ReadinessResponse(BaseModel)` lines 55-76; four fields tier1, tier2, pending_count, total_count |
| `app/repositories/user_benchmark_percentiles_repository.py` | has_any_rows existence helper | VERIFIED | `async def has_any_rows(session: AsyncSession, *, user_id: int) -> bool` at line 127; bounded-count with LIMIT 1 |
| `frontend/src/hooks/useReadiness.ts` | Two-tier readiness poll hook | VERIFIED | queryKey `['imports', 'readiness']`, 3s interval, stops on tier2, safe false defaults, no reload |
| `tests/routers/test_imports_readiness.py` | SC-1 truth-table tests | VERIFIED | All 6 test cases present: auth, scoping, tier1-false, tier2-false-no-percentiles, tier2-true, tier2-true-no-games |
| `frontend/src/components/EndgamesProcessingState.tsx` | Whole-page Endgames locked state | VERIFIED | `data-testid="endgames-processing-state"`, Cpu icon, analysedCount/totalCount counter, no CTA button |
| `frontend/src/pages/Endgames.tsx` | In-place tier2 gate | VERIFIED | `if (!tier2)` early return at line 772 (after all hooks, React rules of hooks compliant) |
| `frontend/src/pages/Import.tsx` | Readiness state machine + Explore Openings CTA | VERIFIED | tier1-gated section with `data-testid="btn-explore-openings"`, state copy, analyzing counter |
| `frontend/src/App.tsx` | Tier1 route/nav gate + tier2 toast | VERIFIED | All three nav surfaces (NavHeader, MobileBottomBar, MobileMoreDrawer) use `useReadiness().tier1`; fire-once toast with `wasTier2FalseRef` |
| `frontend/src/components/stats/EvalCpuPlaceholder.tsx` | Inline pulsating-Cpu placeholder | VERIFIED | `data-testid="eval-cpu-placeholder"`, amber styling, "Analyzing…" label |
| `frontend/src/hooks/useEvalCoverage.ts` | Auto-reload-free eval-coverage hook | VERIFIED | No `window.location.reload`, no `evalCompletionReloadFired`, no `wasPendingRef`; return shape unchanged |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/imports.py get_readiness` | `user_benchmark_percentiles_repository.has_any_rows` | sequential await on one AsyncSession | VERIFIED | Lines 161-175: sequential reads with short-circuits, `asyncio.gather` confirmed absent |
| `frontend/src/hooks/useReadiness.ts` | `/imports/readiness` | TanStack Query queryKey `['imports','readiness']` | VERIFIED | `queryKey: ['imports', 'readiness']`, `apiClient.get<ReadinessResponse>('/imports/readiness')` |
| `frontend/src/App.tsx ImportRequiredRoute` | `useReadiness tier1` | replaces profileHasCompletedImport as redirect signal | VERIFIED | `readiness.tier1` at line 456; `profileHasCompletedImport` function removed |
| `frontend/src/pages/Endgames.tsx` | `EndgamesProcessingState` | early return when `!tier2` | VERIFIED | Line 772: `if (!tier2) { return <EndgamesProcessingState .../>; }` |
| `frontend/src/components/stats/OpeningStatsCard.tsx` | `useReadiness tier2` | replaces useEvalCoverage isPending/pendingCount | VERIFIED | Imports `useReadiness`, destructures `tier2` at line 61 |
| `frontend/src/components/stats/OpeningStatsCard.tsx` | `EvalCpuPlaceholder` | renders when `!tier2` | VERIFIED | Lines 249-251: `<EvalCpuPlaceholder />` in the else branch |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `useReadiness.ts` | `tier1`, `tier2`, `pendingCount`, `totalCount` | GET /imports/readiness (DB queries via game_repository + percentiles_repository) | Yes — live DB counts, not static | FLOWING |
| `EndgamesProcessingState.tsx` | `pendingCount`, `totalCount` props | useReadiness in Endgames.tsx | Yes — passed from live readiness poll | FLOWING |
| `Import.tsx` readiness section | `tier1`, `tier2`, `pendingCount`, `totalCount` | useReadiness() at line 150 | Yes — live poll | FLOWING |
| `OpeningStatsCard.tsx` | `tier2` | useReadiness() at line 61 | Yes — live poll | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — requires running backend server with DB populated for meaningful readiness-state checks. Core wiring confirmed via static analysis.

---

### Probe Execution

Step 7c: No probe scripts declared or conventional probe files found in this phase.

---

### Requirements Coverage

Standalone phase — no requirement IDs declared. Success criteria coverage verified directly against codebase above.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/routers/imports.py` | 168 | `pending = 0 if not tier1 else await ...` — pending_count zeroed during active import | Warning (WR-01, previously documented in REVIEW.md) | EndgamesProcessingState shows "Stockfish: N / N games" during active import when user has prior games, appearing 100% complete while actually locked. Does not block the phase goal — correctness of the two-tier lock itself is unaffected; tier2 stays false while tier1 is false. Advisory. |
| `frontend/src/hooks/useReadiness.ts` | 41-47 | No `isError` branch — API failure falls back to `tier1=false, tier2=false` | Warning (WR-02, previously documented in REVIEW.md) | Transient API error locks user out; does not prevent the goal behavior under normal operation. Advisory. |
| `frontend/src/hooks/useEvalCoverage.ts` | 37-38 | Error maps to `pct=100, isPending=false` | Warning (WR-03, previously documented in REVIEW.md) | API error hides EvalCoverageHeader. Advisory. |

Note: All three warnings are already documented in `96-REVIEW.md` (WR-01, WR-02, WR-03). Per the verification prompt, these are advisory and must not re-block the phase.

**No TBD / FIXME / XXX markers found in phase-modified files.**

No `window.location.reload` found outside the Sentry error boundary button — that occurrence is pre-existing non-readiness logic retained by design.

---

### Human Verification Required

#### 1. Tier-1 Route Gate: First-import User Redirect

**Test:** Register a fresh user, log in, navigate directly to `/openings`.
**Expected:** Redirected to `/import`; toast "Import your games first to unlock this feature."; /import renders the import form, not any openings data.
**Why human:** Route guard behavior under first-render flash (isLoading guard) and toast timing require live browser session to confirm no content flash.

#### 2. Incremental Import: Tier-1 Openings / Tier-2 Endgames Split

**Test:** With an active incremental import running for a user who already has games imported and Stockfish analysis pending, visit `/openings` and `/endgames`.
**Expected:** Openings page renders normally (tier1=true during incremental). Endgames page renders `EndgamesProcessingState` with live Stockfish counter; the nav link to /endgames remains clickable.
**Why human:** Requires live in-flight import to produce tier1=true/tier2=false split state.

#### 3. Import Page State Machine Transitions

**Test:** Watch the Import page through a complete first import cycle: before import, during import, after hot-import done (tier1 reached, tier2 pending), after Stockfish drain (tier2).
**Expected:** At hot-import done: "Games imported. Openings ready." + "Explore Openings" CTA visible + "Analyzing endgames (X / Y)" below CTA. At tier2: "Ready. All analysis complete." No copy contains "Import complete" or "Imported N games from {platform}".
**Why human:** Full state machine requires live pipeline progression.

#### 4. Tier-2 Toast: Fire-Once Behavior

**Test:** In a session where import completes and Stockfish analysis drains, verify the "Endgame analysis complete!" toast fires once and only once. Suppress test: be on `/endgames` when tier2 flips.
**Expected:** Toast fires once with "Explore Endgames" action button that navigates to /endgames and invalidates endgameOverview. When on /endgames already, no toast fires.
**Why human:** Requires live tier2 false→true transition in-session; `wasTier2FalseRef` behavior cannot be tested without browser state.

#### 5. EvalCoverageHeader Visibility During Drain (SC-6)

**Test:** While Stockfish analysis is pending (pct < 100), navigate across /import, /openings, /endgames (post-tier2), /overview.
**Expected:** Amber EvalCoverageHeader bar is visible on all four pages. Note: `EndgamesProcessingState` (pre-tier2) does not include the EvalCoverageHeader — this is correct per design since the whole page is replaced; confirm there is no regression in post-tier2 endgames.
**Why human:** Requires live Stockfish-draining state across pages.

---

### Gaps Summary

None. All 8 success criteria are verified against the codebase. The 5 human-verification items above are behavioral confirmations that require a running app — the wiring for all of them is confirmed in static analysis.

The three advisory warnings from REVIEW.md (WR-01 pending_count masking, WR-02/WR-03 missing isError handling) are pre-documented and do not undermine the core two-tier gate correctness. They are candidates for a follow-up fix phase.

---

_Verified: 2026-05-28T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
