---
phase: 179-two-sided-move-stats-component-seed-112
plan: 02
subsystem: ui
tags: [react, typescript, frontend, library-service, vitest]

# Dependency graph
requires:
  - phase: 179-01-surface-canonical-per-color-accuracy
    provides: GameFlawCard.white_accuracy/black_accuracy (nullable float, frontend TS mirror)
provides:
  - moverColorAtPly(ply) helper in frontend/src/lib/plyOwnership.ts
  - MoveStatCategory/MoveStatSide types + severityCountsBySide/tierCountsBySide client-side count derivation (frontend/src/lib/moveStatsCounts.ts)
  - MoveStats.tsx shared presentational component (accuracy strip + always-7-row two-sided category table)
  - BestMoveIcon.tsx, GoodMoveIcon.tsx circular category badge icons
affects: [179-03-move-stats-frontend-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-side count derivation via moverColorAtPly (ply parity), never is_user/isUserPly, for surfaces that intentionally show both players (D-08)"
    - "MoveStatsCellRef discriminated union ({ kind: 'category'; category; side }) as the single dispatch unit for onCellActivate/onCellHover"

key-files:
  created:
    - frontend/src/lib/moveStatsCounts.ts
    - frontend/src/lib/__tests__/moveStatsCounts.test.ts
    - frontend/src/components/library/MoveStats.tsx
    - frontend/src/components/library/__tests__/MoveStats.test.tsx
    - frontend/src/components/icons/BestMoveIcon.tsx
    - frontend/src/components/icons/GoodMoveIcon.tsx
  modified:
    - frontend/src/lib/plyOwnership.ts

key-decisions:
  - "moverColorAtPly added as a NEW export alongside isUserPly (not a replacement) — isUserPly answers 'is this the user's move', moverColorAtPly answers 'which literal color moved', and every other gem/great consumption surface still needs the user-scoped isUserPly (memory: project_gem_great_user_scoping)"
  - "Severity glyphs for the 7-row table are rendered via a local SeverityCategoryIcon in MoveStats.tsx (reading SEVERITY_GLYPH directly) rather than importing SeverityGlyphIcon.tsx's BlunderIcon/MistakeIcon — that file deliberately exports no inaccuracy variant (its own move-list call sites omit inaccuracy), but the Move Stats table needs all 3 severities on one shared visual convention"
  - "collapsed prop is threaded through MoveStats (native `hidden` attribute on the table) but not exercised by tests here — full expand/collapse behavior and tests are explicitly Plan 03's job per the plan's action text"
  - "Best/Good icons use a shared checkmark glyph, differentiated only by fill color (MOVE_QUALITY_BEST dark green vs MOVE_QUALITY_GOOD light green) — mirrors chess.com's Best/Good pairing and keeps both icons visually part of the same 'positive tier' family as Gem/Great"

patterns-established:
  - "MoveStatsCellRef ({ kind: 'category'; category: MoveStatCategory; side: MoveStatSide }) is the (category × side) dispatch unit Plan 03 will extend the existing FlawRef unions toward"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-08]

coverage:
  - id: D1
    description: "moverColorAtPly(ply) returns 'white' for even ply, 'black' for odd ply, as a new export alongside isUserPly"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/plyOwnership.test.ts (existing suite, unaffected) + moverColorAtPly exercised transitively via moveStatsCounts.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "severityCountsBySide/tierCountsBySide derive per-side counts purely from flaw_markers/eval_series (never severity_counts), including opponent-side positive tiers (D-08)"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/moveStatsCounts.test.ts (5 tests, all pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "MoveStats renders all 7 category rows always, even when every count is 0; zero cells are muted and inert (not buttons)"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx > 'MoveStats — D-03 all 7 rows always render'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Accuracy strip shows the canonical white_accuracy/black_accuracy value or a muted em-dash when null; never ACPL or an *_imported value"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx > 'MoveStats — D-01/D-02 accuracy strip'"
        status: pass
    human_judgment: false
  - id: D5
    description: "Non-zero cells are semantic buttons dispatching { kind: 'category', category, side } to onCellActivate; inaccuracy count reads from flaw_markers, not severity_counts"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx > 'MoveStats — D-05/D-09 non-zero cell interaction'"
        status: pass
    human_judgment: false
  - id: D6
    description: "Opponent-ply gem/great/best/good counts are surfaced in the opponent's column (D-08, deliberately reversing isUserPly scoping for this surface)"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx > 'MoveStats — D-08 opponent positive tiers surfaced'"
        status: pass
    human_judgment: false
  - id: D7
    description: "Column order flips with game.user_color (player-first) while each cell's background stays the literal board color"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx > 'MoveStats — player-first column order'"
        status: pass
    human_judgment: false
  - id: D8
    description: "Best/Good rows render the new BestMoveIcon/GoodMoveIcon circular badges, colored from theme.ts MOVE_QUALITY_BEST/GOOD"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx > 'MoveStats — Best/Good rows render the new circular icons'"
        status: pass
    human_judgment: false
  - id: D9
    description: "Wiring MoveStats into LibraryGameCard.tsx and AnalysisTagsPanel.tsx (mobile collapse, D-10 filter ring, cycling)"
    verification: []
    human_judgment: true
    rationale: "Explicitly out of scope for this plan (Plan 03's job per the plan objective) — MoveStats.tsx is a self-contained, unit-tested component with no consumer wiring yet, so there is nothing to UAT in the live app until Plan 03 mounts it."

# Metrics
duration: 30min
completed: 2026-07-18
status: complete
---

# Phase 179 Plan 02: Two-sided Move Stats Component Summary

**Shared `MoveStats.tsx` presentational component — accuracy strip + always-7-row Gem/Great/Best/Good/Inaccuracy/Mistake/Blunder two-sided count table — plus the pure client-side `moveStatsCounts.ts` derivation module and two new circular Best/Good badge icons, all unit-tested and ready for Plan 03's consumer wiring.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-18T11:25:00Z
- **Completed:** 2026-07-18T11:55:00Z
- **Tasks:** 2
- **Files modified:** 7 (1 modified, 6 created)

## Accomplishments
- `moverColorAtPly(ply)` added to `frontend/src/lib/plyOwnership.ts` — the literal board-color-of-mover helper (even=white, odd=black), distinct from `isUserPly`'s user-relative check
- `frontend/src/lib/moveStatsCounts.ts` — `MoveStatCategory` (7-valued) + `MoveStatSide` types, `severityCountsBySide`/`tierCountsBySide` folding `flaw_markers`/`eval_series` into per-side counts for BOTH players (D-08), never reading `severity_counts`
- `frontend/src/components/library/MoveStats.tsx` — the shared component: accuracy strip (player-first column order via `game.user_color`, literal-color cell backgrounds from `EVAL_BAR_WHITE`/`BLACK`, canonical value or muted "—") + the always-7-row category table with inert zero cells and semantic `<button>` non-zero cells dispatching `{ kind: 'category', category, side }`
- `BestMoveIcon.tsx`/`GoodMoveIcon.tsx` — new circular checkmark badges colored from `MOVE_QUALITY_BEST`/`MOVE_QUALITY_GOOD`, shape-compatible with `GemIcon`/`GreatMoveIcon`
- 18 new unit tests (5 `moveStatsCounts.test.ts` + 13 `MoveStats.test.tsx`), all passing; full frontend suite (2315 tests, 173 files) green; `npm run lint`, `npx tsc -b`, `npm run knip` all clean

## Task Commits

Each task was committed atomically:

1. **Task 1: moverColorAtPly helper + client-side per-side count derivation (moveStatsCounts.ts)** - `c1ca6819` (feat)
2. **Task 2: MoveStats.tsx shared component (accuracy strip + always-7-row table) + Best/Good icons** - `8142c7df` (feat)

_No TDD-flagged deviation — both tasks carried `tdd="true"` and were implemented test-alongside (behavior + test written together per task, not a separate RED/GREEN commit split), matching this repo's established non-strict-TDD convention for plan-level `type="auto"` tasks. See "Deviations from Plan" below for the explicit note._

## Files Created/Modified
- `frontend/src/lib/plyOwnership.ts` - Added `moverColorAtPly(ply)` export alongside `isUserPly`
- `frontend/src/lib/moveStatsCounts.ts` - NEW — `MoveStatCategory`/`MoveStatSide` types, `severityCountsBySide`, `tierCountsBySide`
- `frontend/src/lib/__tests__/moveStatsCounts.test.ts` - NEW — 5 tests covering empty input, `is_user`-independence, both-side tier counting
- `frontend/src/components/library/MoveStats.tsx` - NEW — the shared two-sided Move Stats component
- `frontend/src/components/library/__tests__/MoveStats.test.tsx` - NEW — 13 tests covering D-01/D-03/D-05/D-08/D-09 and column reorder
- `frontend/src/components/icons/BestMoveIcon.tsx` - NEW — circular "Best" checkmark badge
- `frontend/src/components/icons/GoodMoveIcon.tsx` - NEW — circular "Good" checkmark badge

## Decisions Made
- Kept `isUserPly` untouched and added `moverColorAtPly` as a sibling export — every other gem/great consumption surface (eval-chart dots, board markers, cycling) stays user-scoped per the locked `project_gem_great_user_scoping` convention; only this new surface needs the literal-color variant (D-08 is explicitly scoped to Move Stats, not a global policy change).
- Rendered the 3 severity glyphs (inaccuracy/mistake/blunder) via a local `SeverityCategoryIcon` in `MoveStats.tsx` that reads `SEVERITY_GLYPH` directly, rather than importing `SeverityGlyphIcon.tsx`'s exported `BlunderIcon`/`MistakeIcon` — that file intentionally has no exported inaccuracy component (its own move-list callers omit inaccuracy by design), but the Move Stats table needs all 3 severities under one visual convention. `SeverityGlyphIcon.tsx` itself was left unmodified (out of this plan's `files_modified`).
- `collapsed` prop is accepted and threaded through (native `hidden` attribute on the `<table>`) but not exercised by any test here, per the plan's explicit instruction that full collapse behavior/tests are Plan 03's responsibility.
- Best/Good icons share one checkmark glyph shape, differentiated by fill color only (`MOVE_QUALITY_BEST` dark green vs `MOVE_QUALITY_GOOD` light green) — deliberately mirrors chess.com's Best/Good visual pairing and keeps all 4 positive-tier icons (Gem/Great/Best/Good) reading as one family.
- The white glyph stroke/fill (`#fff`) inside `BestMoveIcon`/`GoodMoveIcon`/the local severity glyph is a literal hex value, matching the exact established precedent in `GemIcon.tsx`, `GreatMoveIcon.tsx`, and `SeverityGlyphIcon.tsx` (all of which hard-code `#fff` for the inner glyph on a themed circle) — confirmed via grep before treating it as compliant with the "no raw color literals" acceptance criterion, since the criterion targets semantic/theme colors (the circle fill, correctly sourced from `theme.ts`), not this pre-existing white-glyph convention.

## Deviations from Plan

None - plan executed exactly as written. Both tasks carried `tdd="true"` in the plan frontmatter; per this repo's established pattern for `type="auto" tdd="true"` plan tasks (see Phase 179 Plan 01 and prior phases), behavior and tests were written together within each task's single commit rather than as separate RED-then-GREEN commits — the plan's own `<behavior>`/`<action>` blocks specify test coverage as part of the single task action, and the acceptance criteria are verified against the final passing state, not an intermediate failing-test gate. This is not a deviation from the plan's actual instructions (the plan does not require separate RED/GREEN commits), just a note on the applicable TDD-gate-enforcement text in the executor workflow (which applies to plans with `type: tdd` at the frontmatter level — this plan is `type: execute`).

## Issues Encountered
None. Full frontend suite (`npm test -- --run`), lint, `npx tsc -b`, and `npm run knip` all passed cleanly on the first attempt after Task 2.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `MoveStats.tsx`, `moveStatsCounts.ts`, `moverColorAtPly`, and the two new icons are all self-contained and unit-tested, ready for Plan 03 to wire into `LibraryGameCard.tsx` and `AnalysisTagsPanel.tsx`.
- Plan 03's remaining work (per the phase's canonical decisions, unchanged by this plan): extend the existing local `FlawRef` unions in both consumer files toward `MoveStatsCellRef`'s `{ kind: 'category'; category; side }` shape (D-09), wire `useFlawFilterStore`'s outline to only the player-side cell (D-10, library-only), implement `collapsed` mobile behavior (D-06 — accuracy strip + user's I/M/B only, tap to expand), gate mounting on `analysis_state === 'analyzed'` (D-07, dropping `AnalysisTagsPanel.tsx`'s current empty-state early return per RESEARCH Pitfall 2), delete the now-fully-superseded `GemGreatBadge.tsx` (+ its test) once both call sites migrate, and resolve the desktop layout arrangement (RESEARCH Open Question 1 / Pitfall 4 — chart vs. Move Stats card vs. board).
- No blockers identified. `severity_counts` and `GemGreatBadge.tsx`/`SeverityBadge.tsx` (library-card/analysis-panel usage only) remain live in the two consumer files until Plan 03 replaces them — `SeverityBadge.tsx` itself must NOT be deleted (still consumed by `FlawCard.tsx`'s Flaws-tab, out of scope, per RESEARCH Pitfall 3).

---
*Phase: 179-two-sided-move-stats-component-seed-112*
*Completed: 2026-07-18*

## Self-Check: PASSED

All 7 modified/created files and both task commit hashes (c1ca6819, 8142c7df) verified present.
