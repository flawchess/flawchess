---
phase: 184-persona-calibration-strength-honesty
plan: 03
subsystem: ui
tags: [react, typescript, radix-popover, vitest, personas, honesty-surfaces]

requires:
  - phase: 184-02
    provides: "frontend/src/generated/personaCalibration.ts (PERSONA_CALIBRATION Record<PersonaId, {botElo, label}>), committed as a bootstrap/retargeting-only placeholder (labels currently === rung) ahead of Plan 04's real sweep"
provides:
  - personaRegistry.ts sourcing botElo + calibratedLabel per persona from PERSONA_CALIBRATION, replacing the A1 (botElo === rung) placeholder with calibration provenance + D-11 staleness policy
  - A new calibratedLabel field on the Persona interface, exhaustively populated across all 24 Record<PersonaId, Persona> slots
  - PersonaCard.tsx and PersonaDetailSurface.tsx rendering the calibrated label instead of `~${rung}` (card label, card aria-label, detail meta line)
  - PersonaEloDisclosurePopover.tsx — a reusable D-08 measurement-disclosure popover (mirrors MetricStatPopover's hover/tap shell) with a D-06 bottom-rung floor-acknowledgment variant
  - CAL-05 test coverage: ~1800 ceiling, 24-slot completeness, round-50 format, floor-rung label presence, per-style monotonicity spot-check
affects: [184-04-persona-calibration-sweep-execution]

tech-stack:
  added: []
  patterns:
    - "Registry-consumes-generated-file: personaRegistry.ts reads botElo/calibratedLabel per PersonaId key from a generated Record, never hand-transcribing calibration values (mirrors botStrengthCurves.ts consumption elsewhere)"
    - "Supplementary disclosure popover: the D-08 popover is mounted ADJACENT to the visible calibrated label, never replacing it — same pattern as PercentileChip's hover-disclosure precedent"
    - "Synthetic-override test fixture: tests assert calibrated-vs-rung distinctness by spreading a persona object with an overridden calibratedLabel ({ ...PERSONA, calibratedLabel: '~1050' }), matching the existing avatarSrc-override precedent in PersonaCard.test.tsx"

key-files:
  created:
    - frontend/src/components/bots/PersonaEloDisclosurePopover.tsx
  modified:
    - frontend/src/lib/personas/personaRegistry.ts
    - frontend/src/lib/engine/botStyleBundles.ts
    - frontend/src/components/bots/PersonaCard.tsx
    - frontend/src/components/bots/PersonaDetailSurface.tsx
    - frontend/src/lib/personas/__tests__/personaRegistry.test.ts
    - frontend/src/components/bots/__tests__/PersonaCard.test.tsx
    - frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx
    - frontend/knip.json

key-decisions:
  - "requirements-completed left empty: CAL-05 is jointly delivered across Plans 02/03/04 (frontmatter, mirrors Plan 02's own precedent). This plan wires the honesty SURFACES (ceiling clamp, floor-acknowledgment popover, honest labels) and their tests against the committed bootstrap/placeholder calibration data — the real measured values only land once Plan 04 runs the operator sweep. Marking CAL-05 complete here would be a partial-delivery false-positive since today's labels still equal rung under the hood (bootstrap state)."
  - "calibratedLabel placed as a sibling field to botElo in the Persona interface (not a replacement/rename) — rung stays the unchanged structural grid key per the assumption_delta_decision in 184-03-PLAN.md; no primary identity was displaced"
  - "Removed frontend/src/generated/personaCalibration.ts from knip.json's ignore list (Rule 1 — knip flagged the ignore entry as now-redundant): personaRegistry.ts consumes it as of Task 1, so Plan 02's ahead-of-consumer placeholder entry is no longer needed"
  - "personaRegistry.test.ts's pre-existing 'botElo === rung' assertion was rewritten (not deleted) to 'botElo is a member of MAIA_ELO_LADDER' — the retargeting behavior this plan introduces makes the old equality assertion permanently false, but the ladder-membership half of the original assertion is still a real invariant worth keeping"

patterns-established:
  - "Popover hover-content test pattern: vi.useFakeTimers() + fireEvent.mouseEnter + act(() => vi.advanceTimersByTime(200)) + waitFor(() => screen.getByTestId(...)) — copied from EndgameTimePressureCard.test.tsx's openClockGapPopover() precedent for testing the new PersonaEloDisclosurePopover's floor/non-floor body copy"

requirements-completed: []

coverage:
  - id: D1
    description: "personaRegistry.ts sources botElo + calibratedLabel from PERSONA_CALIBRATION for all 24 personas; A1 placeholder prose replaced with calibration provenance + D-11 staleness policy in both personaRegistry.ts and botStyleBundles.ts headers"
    requirement: "CAL-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts (43 tests, includes new CAL-05 describe block: ceiling, completeness, round-50 format, floor-rung label, monotonicity)"
        status: pass
      - kind: unit
        ref: "cd frontend && npx tsc -b — exit 0 (Record<PersonaId> exhaustiveness holds, new field typed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "PersonaCard renders persona.calibratedLabel (not ~${rung}) on both the visible label and aria-label, keeping text-sm text-muted-foreground"
    requirement: "CAL-05"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaCard.test.tsx (7 tests, incl. new 'renders the calibrated label, not the raw rung, when they differ')"
        status: pass
    human_judgment: false
  - id: D3
    description: "PersonaDetailSurface renders the calibrated label in its meta line and mounts a reusable PersonaEloDisclosurePopover (D-08) for every persona, with the D-06 ~900 floor-acknowledgment variant on bottom-rung (800) personas only"
    requirement: "CAL-05"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx (11 tests, incl. new disclosure-trigger-present test and floor-vs-non-floor popover-copy tests)"
        status: pass
      - kind: unit
        ref: "cd frontend && npm run knip — exit 0 (new PersonaEloDisclosurePopover export consumed; personaCalibration.ts ignore entry removed cleanly)"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-07-22
status: complete
---

# Phase 184 Plan 03: Registry + Bots-Page Calibration Wiring Summary

**Wired the generated `PERSONA_CALIBRATION` file into `personaRegistry.ts`, swapped `PersonaCard`/`PersonaDetailSurface`'s provisional `~${rung}` labels for the calibrated `calibratedLabel`, and shipped a reusable `PersonaEloDisclosurePopover` (D-08) with a bottom-rung `~900` floor-acknowledgment variant (D-06).**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-22
- **Tasks:** 3
- **Files modified:** 8 (1 created, 7 modified)

## Accomplishments
- `personaRegistry.ts`: added a `calibratedLabel: string` field to the `Persona` interface; all 24 registry entries now read `botElo`/`calibratedLabel` from `PERSONA_CALIBRATION['<personaId>']` (the generated file from Plan 02) instead of the literal `botElo: <rung>` placeholder. The stale A1 header comment (documenting the pre-calibration `botElo === rung` decision) is replaced with calibration provenance (which scripts produce the file, where the operator runbook lives) plus the D-11 staleness policy. The same D-11 staleness note was added to `botStyleBundles.ts`'s header, since changing its style params invalidates the calibration.
- `PersonaCard.tsx`: swapped `` `~${persona.rung}` `` for `persona.calibratedLabel` on both the visible label and the `aria-label` (so the accessible name matches what's shown), keeping the exact `text-sm text-muted-foreground` classes.
- `PersonaEloDisclosurePopover.tsx` (new): a reusable disclosure popover mirroring `MetricStatPopover.tsx`'s shell verbatim (100ms hover-open delay, Radix `Root`/`Trigger`/`Portal`/`Content`, `side="top" sideOffset={4}`, identical animation classes, `text-xs` body — the documented CLAUDE.md popover exception). Discloses that the ELO is measured in bot-vs-engine games on the internal anchor ladder (approx blitz scale); its `isFloorRung` prop appends a second paragraph acknowledging the `~900` measured floor for bottom-rung (800) personas.
- `PersonaDetailSurface.tsx`: swapped `` `${persona.style} · ~${persona.rung}` `` for `` `${persona.style} · ${persona.calibratedLabel}` ``, and mounted the new popover trigger inline next to that meta text for every persona (`isFloorRung={persona.rung === 800}`) — supplementary disclosure, not a replacement for the visible label.
- Extended all 3 relevant test files with CAL-05 assertions: registry-level ceiling/completeness/format/floor/monotonicity checks, card-level calibrated-label-vs-rung distinctness, and detail-surface-level disclosure-trigger-presence plus floor-vs-non-floor popover body copy (via the `fireEvent.mouseEnter` + fake-timers hover pattern already established in `EndgameTimePressureCard.test.tsx`).
- Removed `frontend/src/generated/personaCalibration.ts` from `knip.json`'s `ignore` list now that it's genuinely consumed (Plan 02 added it there as an ahead-of-consumer placeholder).

## Task Commits

Each task was committed atomically:

1. **Task 1: Source botElo + calibrated label from the generated file; record staleness policy** - `061b70b3` (feat)
2. **Task 2: PersonaCard renders the calibrated label** - `99bebdad` (feat)
3. **Task 3: Detail-surface label swap + reusable measurement-disclosure popover (D-08/D-06)** - `50025713` (feat)

## Files Created/Modified
- `frontend/src/lib/personas/personaRegistry.ts` - `calibratedLabel` field on `Persona`; all 24 entries source `botElo`/`calibratedLabel` from `PERSONA_CALIBRATION`; header replaced with provenance + D-11
- `frontend/src/lib/engine/botStyleBundles.ts` - D-11 staleness note added to the header doc comment
- `frontend/src/components/bots/PersonaCard.tsx` - renders `persona.calibratedLabel` (label + aria-label)
- `frontend/src/components/bots/PersonaEloDisclosurePopover.tsx` (new) - D-08 disclosure popover, D-06 floor variant
- `frontend/src/components/bots/PersonaDetailSurface.tsx` - calibrated label in meta line + mounted disclosure popover
- `frontend/src/lib/personas/__tests__/personaRegistry.test.ts` - CAL-05 assertions; fixed stale botElo-equals-rung test
- `frontend/src/components/bots/__tests__/PersonaCard.test.tsx` - calibrated-label-vs-rung distinctness test
- `frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx` - disclosure-trigger + floor/non-floor popover-copy tests
- `frontend/knip.json` - removed the now-redundant `personaCalibration.ts` ignore entry

## Decisions Made
See `key-decisions` in frontmatter for the full list, notably:
- `requirements-completed` left empty — CAL-05 is jointly delivered across Plans 02/03/04; this plan ships the honesty UI surfaces against Plan 02's bootstrap/placeholder data, not the real measured values (Plan 04's job).
- `calibratedLabel` added as a sibling field, not a rename — `rung` stays the unchanged structural grid key.
- The pre-existing `botElo === rung` test assertion was rewritten to a ladder-membership-only assertion, since retargeting makes the equality permanently false by design.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `act` import in PersonaDetailSurface.test.tsx**
- **Found during:** Task 3 (writing the floor/non-floor popover-copy tests)
- **Issue:** Initially imported `act` from `vitest` (following the pattern of destructuring test utilities from a single module) — `vitest` does not export `act`; it comes from `@testing-library/react`. This produced a `TypeError: act is not a function` at test runtime.
- **Fix:** Moved `act` to the `@testing-library/react` import, matching the exact import shape used by `EndgameTimePressureCard.test.tsx`'s existing hover-popover test pattern.
- **Files modified:** frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx
- **Verification:** `npm test -- --run src/components/bots/__tests__/PersonaDetailSurface.test.tsx` — 11/11 pass.
- **Committed in:** `50025713` (Task 3 commit)

**2. [Rule 3 - Blocking] Removed personaCalibration.ts from knip.json's ignore list**
- **Found during:** post-Task-1 verification (`npm run knip`)
- **Issue:** knip surfaced a "Configuration hints" notice that `src/generated/personaCalibration.ts` should be removed from the ignore list, since `personaRegistry.ts` now genuinely consumes it (Plan 02 added the ignore entry as an ahead-of-consumer placeholder).
- **Fix:** Removed the entry from `knip.json`'s `ignore` array.
- **Files modified:** frontend/knip.json
- **Verification:** `npm run knip` clean (no hints, no errors).
- **Committed in:** `50025713` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking config cleanup)
**Impact on plan:** Both fixes were necessary for the shipped tests/tooling to be genuinely green, not scope creep.

## Issues Encountered
None beyond the two deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 04 can run `bin/run_persona_calibration_sweep.sh` (the operator overnight sweep) and regenerate `personaCalibration.ts` — the registry, card, and detail surface already consume whatever values land there; no further UI wiring is needed once real measurements replace the bootstrap placeholders.
- All CAL-05 honesty surfaces (ceiling clamp, floor-acknowledgment popover, uniform tilde format) are live and tested against the current bootstrap data; they will read correctly the moment Plan 04's real data replaces it, since the plumbing is value-agnostic.
- Full frontend suite (182 files, 2499 tests) passes; `tsc -b`, `knip`, and `lint` are all clean (lint's 3 warnings are pre-existing, unrelated `coverage/` directory noise).
- No blockers.

---
*Phase: 184-persona-calibration-strength-honesty*
*Completed: 2026-07-22*

## Self-Check: PASSED
