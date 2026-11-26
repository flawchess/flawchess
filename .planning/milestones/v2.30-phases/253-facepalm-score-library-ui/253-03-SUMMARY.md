---
phase: 253-facepalm-score-library-ui
plan: 03
subsystem: frontend
tags: [library, flaws, facepalm, popover, severity-badge, umami]
requires:
  - phase: 253-01
    provides: "FlawListItem.facepalm_score served by GET /library/flaws"
  - phase: 253-02
    provides: "frontend/src/lib/facepalm.ts domain module"
provides:
  - "Scored Blunder badge on Flaws cards: Blunder, TreePalm icon, floored whole percent"
  - "FacepalmBadgePopover: hover, tap and keyboard popover explaining the score"
  - "toFacepalmPct in lib/facepalm.ts"
  - "CHANGELOG bullet and the full pre-merge gate over the phase"
affects: [library-flaws, severity-badge]
tech-stack:
  added: []
  patterns: ["MetricInfoPopover-style Radix popover with a real button trigger", "pointer-press flag so focus caused by a press is not keyboard focus"]
key-files:
  created:
    - frontend/src/components/library/FacepalmBadgePopover.tsx
    - frontend/src/components/library/__tests__/FacepalmBadgePopover.test.tsx
  modified:
    - frontend/src/types/library.ts
    - frontend/src/lib/facepalm.ts
    - frontend/src/lib/__tests__/facepalm.test.ts
    - frontend/src/components/library/SeverityBadge.tsx
    - frontend/src/components/library/__tests__/SeverityBadge.test.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
    - CHANGELOG.md
key-decisions:
  - "The scored badge span is wrapped in a real <button> popover trigger; the span keeps all severity colors, border and pill shape (D-15), the button adds no styling"
  - "Hover handlers act only for pointerType mouse; touch never arms the hover timers, so a tap cannot double toggle"
  - "pointerDownRef marks a press in progress and is cleared on focus, click and blur, so a stale press can never block a later keyboard focus"
  - "Click calls preventDefault then setOpen(true) so a click or tap opens and never closes (skips the Radix trigger toggle)"
requirements-completed: [D-01, D-02, D-03, D-07, D-14, D-15, D-16, D-17, D-18]
duration: 35 min
completed: 2026-11-14
status: complete
commits: 4
plan_head_before: 3dad0ee92d4c9a4a2f31af692db4e1ac859898af
plan_head_after: 3916f0e06611e2eae6cf08e691b2e62acf846f97
actuals:
  tokens: 9000
  tasks: 3
  commits: 4
---

# Phase 253 Plan 03: Facepalm score in the Blunder badge Summary

Scored blunders on the Flaws tab now read `Blunder <palm> 94%` in the usual blunder colors, and the badge opens a Facepalm popover on hover (100 ms), click or tap, or keyboard focus. Unscored blunders, mistakes, inaccuracies, the Train Archive badge and the Games-card count badges are unchanged.

## Accomplishments

- `FlawListItem.facepalm_score: number | null` mirrors the backend field; `toFacepalmPct` floors and clamps to 0..100 (0.946 to 94, 0.697 to 69, float4 0.70 as served to 69).
- `FacepalmBadgePopover`: Radix popover with a `<button>` trigger (`aria-label` "Blunder, Facepalm 94%"), testids `facepalm-badge-{gameId}-{ply}` and `...-popover`, heading "Facepalm 94%" and the D-18 sentence verbatim. Open and close autofocus are prevented so Radix does not re-fire focus-open or leave a stray ring.
- Open paths: mouse hover after 100 ms with an 80 ms close grace (content hover keeps it open); click or tap opens and never toggles closed; keyboard focus opens at once unless a pointer press caused the focus; Escape, outside press and tabbing away close it (Radix focus-outside dismissal sufficed, no extra `onBlur` close needed).
- `SeverityBadge` gets an optional `facepalm` prop, used only for blunders; the unscored path renders the identical span. `FlawCard` passes it only when `facepalm_score != null`.
- Umami: one `popover-open` per card instance with target `facepalm-badge` (page `library`), nothing on render or reopen.
- `TagChip.tsx` is untouched (no Facepalm entry in the shared Tags legend).
- CHANGELOG bullet added under `[Unreleased]` / Added.

## TDD (Task 2)

- RED (`1de0a69bd`): 17 popover tests plus SeverityBadge D-17 and scored pins. 8 popover tests failed on the planned assertions (6 "expected false to be true", 1 tracking call count 0, 1 popover element not found for the content-hover test); the SeverityBadge pins passed already because Task 1 (the tracer) implemented the scored badge. `semanticAssessment`: failures are the unimplemented hover, focus-open and tracking behavior, not import or syntax faults. The `gsd_run check tdd-red-evidence` classifier was not run (plan is not `type: tdd`).
- GREEN (`14050103a`): hover timers, pointer-type guards, `pointerDownRef` logic. All 17 pass.
- Mutation check (recorded as required): removing the `onBlur` ref clearing fails "keyboard focus after a press that never clicked (drag-off)"; removing the `onClick` ref clearing fails "after a click that never focused the trigger (Safari)". Each guard is individually covered. Source restored afterwards.
- One test-side adjustment: the installed Radix defers a mouse outside press to the following click, so the outside-press test dispatches pointerdown (button 0) then click, after advancing the 0 ms timer that arms Radix's listener.

## Verification (pre-merge gate, all foreground, final tree)

| Step | Result |
| --- | --- |
| `uv run ruff format app/ tests/ scripts/ analysis/` | exit 0, 604 files unchanged |
| `uv run ruff check . --fix` | exit 0, all checks passed |
| `uv run ty check app/ tests/ scripts/` | exit 0 |
| `uv run --project analysis --with ty ty check analysis/` | exit 0 |
| `scripts/check_function_size.py app/ --fail-over-depth 4` | exit 0, 1507 functions, no breaches |
| `uv run pytest -n auto -x` | exit 0, 6346 passed, 19 skipped |
| `npm run lint` | exit 0 |
| `npm run build` (tsc -b + vite) | exit 0 |
| `npm test -- --run` | exit 0, 364 files, 6328 tests passed |
| `npm run knip` | exit 0 (only two pre-existing configuration hints) |
| banned-wording grep (avoidable / chance you / provisional) | no match |

No formatter or autofix changes were produced, so there is no `style(253)` commit. Plan 01's `-k "facepalm and payload"` backend test passes (1 passed).

## HUMAN-UAT (for /gsd-verify-work, not blocking)

- On a real phone, tapping a scored Blunder badge opens the popover once and it stays open until an outside tap (D-16; jsdom only simulates pointer types).
- Visually: the Facepalm section sits under Blunders / Mistakes and above Best Moves / Tactic Depth on both tabs and in the mobile drawer (D-13); the badge reads Blunder, palm icon, percent in blunder colors (D-14, D-15).
- On dev, many blunders are still unscored until Phases 252 and 250-10 finish, so narrowed ranges show small counts (RESEARCH Pitfall 9, by design).

## Deviations from Plan

**1. [Process] Task 1 (tracer) and its tests landed in one feat commit.** Task 1 is a tracer so it was committed as `feat(253-03)`; Task 2 followed the RED then GREEN split.

**2. [Process] `plan_head_before` taken from the dispatch base, not an on-disk ledger.** The sandbox refused writing into the shared git dir, so the base (`3dad0ee92`) from the dispatch is recorded directly; `commits: 4` is measured as `rev-list 3dad0ee92..3916f0e06` before the SUMMARY commit.

**Total deviations:** 2 (both process). **Impact:** none on behavior.

## Known Stubs

None.

## Threat Flags

None. The score is rendered as React text after `toFacepalmPct` (T-253-08); the popover testid carries numeric ids only and normalizes to `facepalm-badge` (T-253-07, covered by the tracking test).

## Self-Check: PASSED

- Files exist: FacepalmBadgePopover.tsx, FacepalmBadgePopover.test.tsx.
- Commits on the branch: feat Task 1, `1de0a69bd` (RED), `14050103a` (GREEN), `3916f0e06` (CHANGELOG).
