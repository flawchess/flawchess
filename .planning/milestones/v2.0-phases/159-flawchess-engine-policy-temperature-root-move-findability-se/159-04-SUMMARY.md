---
phase: 159-flawchess-engine-policy-temperature-root-move-findability-se
plan: 04
subsystem: frontend-analysis-engine-ui
tags: [react, typescript, radix-slider, flawchess-engine, softmax-temperature, ui]

requires:
  - phase: 159-03
    provides: "policyTemperature.ts core (DEFAULT_POLICY_TEMPERATURE, applyPolicyTemperature) and SearchBudget.policyTemperature threaded through both search runners"
  - phase: 159-02
    provides: "computeFindabilityGate + FlawChessAgreementVerdict rawProbBySan/shownSans props, already wired in Analysis.tsx"
provides:
  - "TemperatureSelector.tsx: log-symmetric 0.5-2.0 slider component, exact center at temperature 1.0"
  - "useFlawChessEngine's policyTemperature option, defaulted at the hook's own call site and re-triggering search on change"
  - "Analysis.tsx session-only temperature state rendered once in the shared eloSelector block (mobile + desktop parity)"
affects: []

tech-stack:
  added: []
  patterns:
    - "Component-boundary log-scale mapping: the underlying Radix <Slider> stays linear over [-1, 1]; sliderPositionToTemperature (2 ** x) / temperatureToSliderPosition (Math.log2) convert at the component's own edge, matching bases so position 0 <-> temperature 1 exactly (mirrors EloSelector's ladder-index <-> value mapping pattern)"
    - "Default value imported, not duplicated: TEMPERATURE_DEFAULT = DEFAULT_POLICY_TEMPERATURE (imported from policyTemperature.ts) rather than a coincidentally-matching literal, so the UI default and the search's no-op short-circuit structurally cannot drift apart"

key-files:
  created:
    - frontend/src/components/analysis/TemperatureSelector.tsx
    - frontend/src/components/analysis/__tests__/TemperatureSelector.test.tsx
  modified:
    - frontend/src/hooks/useFlawChessEngine.ts
    - frontend/src/pages/Analysis.tsx

key-decisions:
  - "[Phase 159-04]: TEMPERATURE_DEFAULT imported directly from DEFAULT_POLICY_TEMPERATURE rather than declared as a matching literal — makes the Pitfall 7 / T-159-08 invariant (slider center === search no-op value) structural, not just test-covered"
  - "[Phase 159-04]: TemperatureSelector rendered exactly once, inside the pre-existing shared `eloSelector` JSX const (which both the mobile humanTab and desktop human column already render) — mobile/desktop parity achieved via one render site, not two"
  - "[Phase 159-04]: policyTemperature defaulted (?? DEFAULT_POLICY_TEMPERATURE) at useFlawChessEngine's own SearchBudget-construction call site, not inside a helper — keeps the no-op short-circuit visible at the orchestrator layer per 159-03's established Pitfall 1 discipline"

requirements-completed: []

coverage:
  - id: D1
    description: "TemperatureSelector.tsx exports a log-symmetric slider (TEMPERATURE_MIN=0.5/MAX=2.0/DEFAULT=1.0) with exact-center mapping helpers, plain-language D-09 copy (no 'Temperature'/'T=' jargon), data-testid, aria-label, and a thumbLabels entry"
    requirement: SEED-085
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/TemperatureSelector.test.tsx (13 tests: strict center-exactness both directions, round-trip at min/center/max, constant values, TEMPERATURE_DEFAULT===DEFAULT_POLICY_TEMPERATURE, data-testid/aria-label, jargon-absence, render value formatting)"
        status: pass
      - kind: other
        ref: "grep confirms no text-xs in TemperatureSelector.tsx; cd frontend && npx tsc -b (zero errors)"
        status: pass
    human_judgment: false
  - id: D2
    description: "useFlawChessEngine accepts policyTemperature and threads it into SearchBudget (defaulted at the call site) and the search-trigger effect's dependency array, so changing it re-runs the search"
    requirement: SEED-085
    verification:
      - kind: other
        ref: "grep: 'policyTemperature ?? DEFAULT_POLICY_TEMPERATURE' present in the SearchBudget construction; effect deps array includes policyTemperature; existing useFlawChessEngine.test.ts (2 tests) still pass unchanged"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useFlawChessEngine.test.ts (2 pre-existing tests, unaffected by the additive optional field)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Analysis.tsx holds session-only temperature state (useState(TEMPERATURE_DEFAULT), no persistence) and renders TemperatureSelector once inside the shared eloSelector JSX, visible in both the mobile Human tab and the desktop human column"
    requirement: SEED-085
    verification:
      - kind: other
        ref: "grep: exactly one <TemperatureSelector render site inside eloSelector const, which is itself referenced at both {eloSelector} usages (mobile humanTab, desktop human column)"
        status: pass
      - kind: other
        ref: "cd frontend && npx tsc -b && npm run lint && npm run knip (all zero errors/issues)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Composed live behavior on /analysis: the three D-03 regression cases (Nb5@600 suppressed, Qxf2@600 wins, Qb8@1000 tail-suppressed), slider-driven ranking reshaping while the Maia chart stays raw (D-06), verdict-copy findability-gate non-contradiction (D-10/D-11), and mobile slider parity"
    requirement: SEED-085
    verification: []
    human_judgment: true
    rationale: "Requires live human interaction with real Maia/Stockfish output on /analysis (drag the slider, read the reshaped ranking, compare against the chart) — cannot be proven by unit tests alone. Per the plan's own <verification> section this Task 2 human-check is explicitly harvested into the end-of-phase UAT batch (human_verify_mode=end-of-phase), not blocking this plan's completion."

duration: 20min
completed: 2026-07-07
status: complete
---

# Phase 159 Plan 04: Policy-temperature slider UI + hook wiring Summary

**New `TemperatureSelector.tsx` (log-symmetric 0.5-2.0 slider, exact center at 1.0) threaded through `useFlawChessEngine`'s `SearchBudget.policyTemperature` and rendered once in `Analysis.tsx`'s shared ELO-selector block, giving both the mobile Human tab and the desktop human column a "Play style" (Sharper <-> More human) knob that re-runs the FlawChess search and reshapes its ranking live, while the Maia "Moves by Rating" chart keeps showing raw data.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-07
- **Tasks:** 2
- **Files modified:** 4 (2 new, 2 edited)

## Accomplishments
- Created `TemperatureSelector.tsx` mirroring `EloSelector.tsx`'s structure exactly, but over a continuous log-symmetric domain: the underlying Radix `<Slider>` stays linear over `[-1, 1]`, converting to/from the displayed temperature at the component boundary via `sliderPositionToTemperature` (`2 ** x`) and `temperatureToSliderPosition` (`Math.log2`) — matching bases guarantee position `0` maps to temperature `1` EXACTLY (strict `===`, not `toBeCloseTo`), which is the property that lets `useFlawChessEngine`'s no-op short-circuit fire for every user who never touches the slider (Pitfall 7 / T-159-08).
- `TEMPERATURE_DEFAULT` is imported directly from `policyTemperature.ts`'s `DEFAULT_POLICY_TEMPERATURE` rather than declared as a separately-matching literal, making the "slider center === search no-op value" invariant structural rather than merely test-covered.
- Copy follows D-09 exactly: a "Play style" group label, "Sharper" <-> "More human" endpoint captions, the numeric value shown subtly (`text-sm font-medium tabular-nums`, one decimal), zero "Temperature"/"T=" jargon anywhere in the rendered primary copy (asserted by a dedicated test).
- Threaded `policyTemperature?: number` through `UseFlawChessEngineOptions`, defaulted at the hook's own `SearchBudget`-construction call site (`policyTemperature ?? DEFAULT_POLICY_TEMPERATURE`) — keeping the no-op short-circuit visible at the orchestrator layer, per the discipline 159-03 established at the search-runner layer — and added to the search-trigger effect's dependency array so moving the slider re-runs the search.
- Wired `Analysis.tsx`: a plain `useState(TEMPERATURE_DEFAULT)` session-only state (no persistence, matching the ELO slider's own behavior), passed into `useFlawChessEngine({ ..., policyTemperature: temperature })`, and `<TemperatureSelector>` rendered exactly once inside the pre-existing shared `eloSelector` JSX const — which is itself already referenced at both the mobile `humanTab` and the desktop human-column render sites, achieving mobile/desktop parity from a single insertion point.

## Task Commits

Each task was committed atomically:

1. **Task 1: TemperatureSelector.tsx (log-symmetric slider) + mapping tests** - `30204eaf` (feat)
2. **Task 2: Thread policyTemperature through the hook + render slider in both layouts** - `c3941ba8` (feat)

**Plan metadata:** (this commit, docs)

## Files Created/Modified
- `frontend/src/components/analysis/TemperatureSelector.tsx` - New log-symmetric slider component + TEMPERATURE_MIN/MAX/DEFAULT + mapping helpers
- `frontend/src/components/analysis/__tests__/TemperatureSelector.test.tsx` - 13 tests: mapping helper exactness + round-trips + component render/a11y/copy
- `frontend/src/hooks/useFlawChessEngine.ts` - New `policyTemperature` option, threaded into `SearchBudget`, added to the search effect's deps
- `frontend/src/pages/Analysis.tsx` - New `temperature` session state, passed to `useFlawChessEngine`, `<TemperatureSelector>` rendered once in the shared `eloSelector` block

## Decisions Made
- `TEMPERATURE_DEFAULT` imported from `DEFAULT_POLICY_TEMPERATURE` (not a matching literal) — see key-decisions above.
- Single shared render site (`eloSelector` JSX const) reused for mobile/desktop parity rather than duplicating the `<TemperatureSelector>` JSX at both call sites.
- `policyTemperature` defaulted at `useFlawChessEngine`'s own call site rather than inside a wrapper/helper, consistent with 159-03's Pitfall 1 discipline of keeping the no-op short-circuit visible at each orchestrator layer.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their acceptance criteria without requiring Rule 1/2/3 fixes.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both Thread A (this plan's slider + hook wiring) and Thread B (159-01's findability ranking) plus the verdict-copy gate (159-02) are now fully wired end-to-end on `/analysis` — the phase's three code threads are complete.
- **Outstanding (deferred to end-of-phase UAT, per the plan's own `human_verify_mode=end-of-phase` note):** the Task 2 human-check — live verification of the three D-03 regression cases (Nb5@600, Qxf2@600, Qb8@1000), slider-driven ranking reshaping with the Maia chart staying raw, verdict-copy non-contradiction, and mobile parity — has not yet been run. `P_REF_ANCHORS` (159-01) and `ROOT_CANDIDATE_HARD_CAP=15` (159-03) both remain unvalidated against live Maia distributions until that UAT pass; if any D-03 case fails, `P_REF_ANCHORS`/`FINDABILITY_MARGIN` need recalibration per 159-RESEARCH.md's Pitfall 4/6.
- No REQUIREMENTS.md traceability entry exists for SEED-085 (confirmed — it is not in the milestone's REQ-ID table); `requirements-completed` is intentionally empty per 159-RESEARCH.md's own note that SEED-085 is the sole traceability anchor for this phase.

---
*Phase: 159-flawchess-engine-policy-temperature-root-move-findability-se*
*Completed: 2026-07-07*

## Self-Check: PASSED

- FOUND: frontend/src/components/analysis/TemperatureSelector.tsx
- FOUND: frontend/src/components/analysis/__tests__/TemperatureSelector.test.tsx
- FOUND: frontend/src/hooks/useFlawChessEngine.ts
- FOUND: frontend/src/pages/Analysis.tsx
- FOUND commit `30204eaf` (Task 1: TemperatureSelector.tsx + mapping tests)
- FOUND commit `c3941ba8` (Task 2: policyTemperature hook wiring + Analysis.tsx render)
