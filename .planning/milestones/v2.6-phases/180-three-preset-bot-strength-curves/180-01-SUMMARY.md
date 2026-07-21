---
phase: 180-three-preset-bot-strength-curves
plan: 01
subsystem: testing
tags: [calibration, bot-strength, internal-rating, scheduler, mjs, node-assert]

# Dependency graph
requires:
  - phase: 173-anchor-ladder-self-calibration
    provides: "INTERNAL_RATING measured-scale table (calibration-internal-scale.mjs) + scoreInInformativeBand/bandDistance primitives (calibration-anchor-schedule.mjs)"
provides:
  - "Pure-logic bot-cell two-pass scheduler: internalRatingFor (fail-loud measured-scale accessor), pickLocateAnchors, locateEstimate, selectMeasureBracket (cross-family floor), bracketBeyondLadder"
  - "Engine-free .check.mjs assertion suite (D-02a logic layer) proving the scheduler on fabricated anchor specs"
affects: [180-03-harness, three-preset-bot-strength-curves, G_preset]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Measured-internal-scale anchor selection (never nominal bot_elo) with fail-loud on unmeasured tokens"
    - "One-directional module dependency: harness -> schedule (internalRatingFor defined here, not in the harness, to avoid a circular import)"

key-files:
  created:
    - scripts/lib/calibration-bot-cell-schedule.mjs
    - scripts/lib/calibration-bot-cell-schedule.check.mjs
  modified: []

key-decisions:
  - "internalRatingFor defined+exported in this new module (not the harness, per RESEARCH Pattern 1) so the harness imports it one-directionally — avoids a harness<->schedule circular import"
  - "scoreInInformativeBand + bandDistance are wired into locateEstimate as load-bearing logic (informative-band preference with a nearest-to-band single-anchor fallback), keeping exactly the 5 required exports rather than adding a dead import"

patterns-established:
  - "Fail-loud measured-scale accessor: throw on any anchor token absent from INTERNAL_RATING, never fall back to the nominal anchorRatingFor (Pitfall 1)"
  - "Warn-and-flag (bracketBeyondLadder) for real-but-extreme cells past the ladder edge, never throw (Pitfall 4)"

requirements-completed: []

coverage:
  - id: D1
    description: "internalRatingFor resolves measured INTERNAL_RATING by label and throws fail-loud on any of the non-10-anchor tokens (Pitfall 1, D-07)"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-bot-cell-schedule.check.mjs#internalRatingFor block (measured lookup + assert.throws on maia1300)"
        status: pass
    human_judgment: false
  - id: D2
    description: "pickLocateAnchors returns weakest+strongest by internal rating; locateEstimate excludes out-of-band locate anchors and delegates to combineAnchorEstimates"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-bot-cell-schedule.check.mjs#pickLocateAnchors + locateEstimate blocks"
        status: pass
    human_judgment: false
  - id: D3
    description: "selectMeasureBracket picks the N nearest anchors on internal scale and enforces the >=2-Maia AND >=2-SF cross-family floor even when the raw nearest set is same-family-skewed"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-bot-cell-schedule.check.mjs#selectMeasureBracket block (asserts precondition skew + resulting family counts)"
        status: pass
    human_judgment: false
  - id: D4
    description: "bracketBeyondLadder returns true for an estimate past the sf10 ceiling (all-below bracket), false for an in-range estimate; never throws (Pitfall 4)"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-bot-cell-schedule.check.mjs#bracketBeyondLadder block"
        status: pass
    human_judgment: false

# Metrics
duration: ~10min
completed: 2026-07-19
status: complete
---

# Phase 180 Plan 01: Bot-cell two-pass scheduler module Summary

**Engine-free measured-internal-scale bot-cell scheduler (`internalRatingFor` fail-loud accessor + locate/measure two-pass with a cross-family bracket floor) plus a node-assert D-02a check suite, replacing the Phase-173 nominal-scale anchor-graph logic that clamped the 2026-07-12 run.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-19T15:37Z
- **Completed:** 2026-07-19T15:47Z
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments
- `scripts/lib/calibration-bot-cell-schedule.mjs`: five pure exports (`internalRatingFor`, `pickLocateAnchors`, `locateEstimate`, `selectMeasureBracket`, `bracketBeyondLadder`) + three named constants (`LOCATE_PASS_GAMES`, `DEFAULT_BRACKET_SIZE`, `MIN_BRACKET_PER_FAMILY`), engine/IO-free.
- `internalRatingFor` looks up the measured `INTERNAL_RATING` by label and throws fail-loud on any of the non-10 measured tokens — the exact anti-clamp fix for the 2026-07-12 incident; it never falls back to the nominal `anchorRatingFor` (Pitfall 1).
- `selectMeasureBracket` sorts by `|internalRating − estimate|`, slices to the bracket, then swaps to enforce `>=2` Maia AND `>=2` SF where the ladder allows.
- `bracketBeyondLadder` warn-and-flags cells past the sf10 ceiling / sf0 floor, never throws (Pitfall 4).
- `scripts/lib/calibration-bot-cell-schedule.check.mjs`: one PASS block per exported function on fabricated specs; exits 0.

## Task Commits

1. **Task 1: Bot-cell two-pass scheduler module** - `b3943386` (feat)
2. **Task 2: Engine-free .check.mjs assertion suite** - `8d3c9fa4` (test)

## Files Created/Modified
- `scripts/lib/calibration-bot-cell-schedule.mjs` - Pure-logic two-pass bot-cell scheduler (measured-scale accessor, locate pick + estimate, measure bracket, beyond-ladder flag).
- `scripts/lib/calibration-bot-cell-schedule.check.mjs` - Engine-free node-assert suite (D-02a), fabricated 10-anchor fixtures, PASS-per-function + `process.exit(0)`.

## Decisions Made
- **`internalRatingFor` lives in this module, not the harness.** The plan's own deviation-from-RESEARCH note: defining it here keeps the harness→schedule dependency one-directional and avoids a circular import.
- **Wired `scoreInInformativeBand` + `bandDistance` into `locateEstimate` as real logic** rather than importing them unused. The must_have requires this module to import both from `calibration-anchor-schedule.mjs`; the natural, non-dead-code home is `locateEstimate`, which prefers informative-band locate anchors and, when both are out of band (a likely ladder-edge cell), falls back to the single nearest-to-band anchor (the lopsided other one would otherwise drag the clamp-inflated combination). Both primitives are load-bearing: the fallback changes the returned estimate. The exact 5-function public surface the plan specified is preserved.

## Deviations from Plan

None - plan executed exactly as written. (Both the two design notes above are choices the plan explicitly sanctioned in its `<objective>` planner-decision block and `must_haves`; no auto-fix rules were triggered.)

## Issues Encountered
None. Both automated verifications passed on the first run:
- Task 1: `node --import ./scripts/lib/frontend-alias-hook.mjs -e "…"` → `exports OK`.
- Task 2: check suite → 6 PASS lines, `exit=0`.
- Confirmed the module contains no `anchorRatingFor`/`checkConnectivity`/`buildCandidateGraph`/`rescueConnectivity` call (only doc-comment mentions explaining what does NOT port) and no engine/fs/network call.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 03 (harness) can now import `internalRatingFor`, `pickLocateAnchors`, `locateEstimate`, `selectMeasureBracket`, `bracketBeyondLadder` from this module.
- No blockers.

## Self-Check: PASSED

- FOUND: scripts/lib/calibration-bot-cell-schedule.mjs
- FOUND: scripts/lib/calibration-bot-cell-schedule.check.mjs
- FOUND commit: b3943386 (Task 1)
- FOUND commit: 8d3c9fa4 (Task 2)

---
*Phase: 180-three-preset-bot-strength-curves*
*Completed: 2026-07-19*
