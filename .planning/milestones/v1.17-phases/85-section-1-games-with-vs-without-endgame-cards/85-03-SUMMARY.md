---
phase: 85-section-1-games-with-vs-without-endgame-cards
plan: 03
subsystem: frontend
tags: [react, vitest, endgame, bullet-chart, sig-gating, wilson]

# Dependency graph
requires:
  - phase: 85-01
    provides: non_endgame_score_p_value field on EndgamePerformanceResponse (backend)
  - phase: 85-02
    provides: TS type for non_endgame_score_p_value + extracted EndgameScoreOverTimeChart with SCORE_BAND_CLASS / useIsMobile re-exported
  - phase: 81
    provides: EndgameStartVsEndSection tile shell + sig-gating template + ENDGAME_TILE_SCORE_DOMAIN convention
provides:
  - EndgameGamesWithWithoutSection component (two-card grid + footer Score Gap bullet)
  - Reusable EndgameCard sub-component pattern (WDL bar + sig-gated chess-score row)
  - Vitest coverage for layout, score math, sig gating, empty state, signed gap formatting
affects:
  - phase-85 Plan 04 (will mount this component in Endgames.tsx and delete the legacy EndgamePerformanceSection)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-card sig-gating triple (n >= MIN_GAMES_FOR_RELIABLE_STATS ∧ isConfident(level) ∧ outside neutral band) lifted from EndgameStartVsEndSection
    - Footer Score Gap font color is zone-only (no sig gating, preserves legacy semantics per D-04)
    - Locked ENDGAME_TILE_SCORE_DOMAIN = 0.15 reused (NOT the wider 0.25 default) so the neutral band fills ≈1/3 of the axis

key-files:
  created:
    - frontend/src/components/charts/EndgameGamesWithWithoutSection.tsx
    - frontend/src/components/charts/__tests__/EndgameGamesWithWithoutSection.test.tsx
  modified: []

key-decisions:
  - "Extracted an internal EndgameCard sub-component instead of inlining both tiles — the two cards differ only in title, WDL source, p-value, and testids, so a 5-prop helper keeps nesting depth ≤3 per CLAUDE.md while avoiding 100+ lines of horizontally duplicated JSX"
  - "Locally declared ENDGAME_TILE_SCORE_DOMAIN = 0.15 and SCORE_GAP_DOMAIN = 0.20 rather than importing from the legacy EndgamePerformanceSection.tsx since Plan 04 deletes that file; both constants carry inline comments naming their CONTEXT-locked source-of-truth (D-13, D-05)"
  - "Footer gap and per-card popovers preserve the legacy testIds (perf-section-info, score-gap-difference) so existing Claude-Chrome automation and any sibling tests querying those IDs continue to work after Plan 04's mount-swap"

patterns-established:
  - "Two-card grid + full-width footer tile pattern using grid-cols-1 lg:grid-cols-2 with a separate mt-4 footer div, suitable for future v1.17 sections (86, 87) that need the same shape"

requirements-completed:
  - SEC1-01
  - SEC1-02
  - SEC1-03
  - SEC1-04
  - SEC1-05
  - SEC1-06

# Metrics
duration: ~25min
completed: 2026-05-13
---

# Phase 85 Plan 03: EndgameGamesWithWithoutSection component Summary

**New twin-card Section 1 component replacing the legacy 'Games with vs without Endgame' table: WDL bar + Wilson-CI chess-score bullet per card (anchored at the natural 0.50), full-width footer Score Gap bullet, sig-gated per-card font color, zone-only footer font color, with 7 Vitest assertions covering layout, math, sig gating, and empty state.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-13 (worktree spawn)
- **Completed:** 2026-05-13
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- `EndgameGamesWithWithoutSection.tsx` exports the section component with:
  - Section h3 "Games with vs without Endgame" + sub-tagline + section-level `InfoPopover` (legacy copy verbatim, `testId="perf-section-info"` preserved)
  - Two-card grid (`grid-cols-1 lg:grid-cols-2 gap-4`): "Games without Endgame" left (D-14), "Games with Endgame" right
  - Each card uses an internal `EndgameCard` helper rendering a `MiniWDLBar` row + a chess-score row with `wilsonBounds` CI whiskers, `MiniBulletChart` (`center=0.5`, `domain=0.15`, neutral band ±0.05), and a per-card `InfoPopover` explaining the 0.50 natural anchor
  - Per-card score font color gated on `isConfident(deriveLevel(p, n)) ∧ scoreZoneColor(score) !== ZONE_NEUTRAL`
  - Empty state `"Not enough data yet"` when `wdl.total === 0` (WDL row) or `wdl.total < MIN_GAMES_FOR_RELIABLE_STATS` (score row)
  - Full-width footer tile "Score Gap (Yes − No)" with signed-percentage label (zone-only color from `score_difference` vs `[SCORE_GAP_NEUTRAL_MIN, SCORE_GAP_NEUTRAL_MAX]`, no sig gating per D-04) and `MiniBulletChart` at `center=0`, `domain=0.20`
  - Stable kebab-case data-testids: `endgame-games-with-without-section`, `tile-games-without-endgame`, `tile-games-with-endgame`, `score-value-no`, `score-value-yes`, `score-info-no`, `score-info-yes`, `score-gap-footer`, `score-gap-difference`, `perf-section-info`
- `EndgameGamesWithWithoutSection.test.tsx` with 7 Vitest cases:
  - Section + both tiles + footer h3 render
  - Score math: 10/0/0 → 100%, 5/0/5 → 50%
  - Footer gap: `+7%` for `0.07`, `-12%` for `-0.12`
  - Empty state in left tile when `non_endgame_wdl.total === 0` (right unaffected)
  - Sig gating: `p = 0.20` with n=10 leaves the score value unstyled
  - Sig gating: `total = 5` hides the entire score row (empty-state branch)
  - Sig gating: 9 wins / 1 loss + `p < 0.05` paints the value with `ZONE_SUCCESS`

## Task Commits

1. **Task 1: Create EndgameGamesWithWithoutSection.tsx with two cards + footer Score Gap bullet** — `8abfd8e8` (feat)
2. **Task 2: Component tests for EndgameGamesWithWithoutSection** — `d7beb7ca` (test)

## Files Created/Modified

- **`frontend/src/components/charts/EndgameGamesWithWithoutSection.tsx`** (291 lines, created) — new Section 1 component plus internal `EndgameCard` sub-component
- **`frontend/src/components/charts/__tests__/EndgameGamesWithWithoutSection.test.tsx`** (271 lines, created) — 7 Vitest cases covering the public contract

## Decisions Made

- **`EndgameCard` internal helper instead of inline JSX.** The two cards differ only in 5 inputs (title, tile testid, score-value testid, popover testid, WDL+p-value source). Inlining both would repeat ~50 lines of declarative JSX twice, and the score-derivation block alone (level / zoneHex / scoreShowZoneFontColor / wilsonBounds) is 6 logical lines per card. The helper takes 5 props, has one writer (the section component) and one reader (itself), keeps nesting at depth 3 inside the JSX (`<div className="...tile..."><div className="...flex..."><div className="...grid...">`), and complies with CLAUDE.md's "Don't invent context dataclasses to make signatures fit" rule because the props ARE the natural set of per-card overrides, not a tidy-signature bag.
- **Local declaration of `ENDGAME_TILE_SCORE_DOMAIN = 0.15` and `SCORE_GAP_DOMAIN = 0.20`.** Could have imported from the legacy `EndgamePerformanceSection.tsx`, but Plan 04 deletes that file. Importing now would force Plan 04 to either keep the file around as a constants module or do a tricky in-place rename. A local copy with inline comments naming the CONTEXT-locked source-of-truth (D-13, D-05) is cleaner and matches how `EndgameStartVsEndSection.tsx` declares its own copy of the same constant at line 54.
- **Preserved legacy testIds for section-level popover and gap label.** `perf-section-info` and `score-gap-difference` are the testIds the legacy `EndgamePerformanceSection.tsx` uses today. Per the plan's behavior spec, keeping them avoids Claude-Chrome / future-test fallout when Plan 04 mount-swaps the legacy component for this one.
- **Footer label "Difference:" instead of repeating the h3.** The footer tile carries its own h3 ("Score Gap (Yes − No)"), so the inner row's left-column label is just "Difference:" for visual rhythm parity with the per-card "Score:" label. The signed value still uses `data-testid="score-gap-difference"` per the plan.

## Deviations from Plan

None — plan executed exactly as written. One minor planning-implementation alignment note: the plan's grep acceptance criterion for `data-testid=` ≥ 6 source-line occurrences in the component file. The component has 5 literal `data-testid=` source lines (one of which renders 2 distinct DOM testids via the `EndgameCard` `tileTestId` prop), plus 2 `testId=` prop assignments that the `InfoPopover` internally converts to `data-testid` on the DOM. The rendered DOM exposes 10 distinct testids, satisfying the intent of the criterion (browser-automation coverage of every interactive element + tile container + popover trigger). Documenting here for the orchestrator's verifier.

## Issues Encountered

- **`npm test -- --reporter=basic` not supported.** The plan's verify line specified `--reporter=basic`, but vitest v4 in this repo does not ship the `basic` reporter (no longer aliased; only `default` / `verbose` / `dot` / `json` / etc.). Ran the tests without the flag (`npm test -- --run <path>`) which uses the default reporter and reports pass/fail counts cleanly. Not a deviation in component / test behavior, just in CLI invocation.
- **`node_modules/` absent in the worktree.** Had to run `npm install` once at the start of Task 1 before `tsc` and `eslint` were available. The worktree spawns from a clean tree, so this is expected.

## Verification

- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` — 0 errors
- `cd frontend && npm run lint` — 0 warnings, 0 errors
- `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameGamesWithWithoutSection.test.tsx` — 7 tests passed
- `cd frontend && npm test -- --run` — 363 tests passed (no regressions)
- `cd frontend && npm run knip` — clean (test file's import of the new component prevents the "unused export" flag until Plan 04 mounts it)
- File grep checks:
  - `grep -c "Games without Endgame"` → 3
  - `grep -c "Games with Endgame"` → 3
  - `grep -c "ENDGAME_TILE_SCORE_DOMAIN = 0.15"` → 2 (declaration + usage)
  - `grep -cE "SCORE_GAP_DOMAIN = 0\.20"` → 1
  - `grep -c "wilsonBounds("` → 1 (inside `EndgameCard`, shared by both tiles)
  - `grep -c "isConfident("` → 2 (import + usage)
  - `grep -cE "non_endgame_score_p_value|endgame_score_p_value"` → 2 (both p-values consumed)
  - `grep -c "SCORE_BULLET_DOMAIN"` → 0 (forbidden 0.25 domain is absent)

## Self-Check: PASSED

- File `frontend/src/components/charts/EndgameGamesWithWithoutSection.tsx` — FOUND
- File `frontend/src/components/charts/__tests__/EndgameGamesWithWithoutSection.test.tsx` — FOUND
- Commit `8abfd8e8` (Task 1 feat) — FOUND
- Commit `d7beb7ca` (Task 2 test) — FOUND
- `Endgames.tsx` untouched in this plan — FOUND (no diff)
- `EndgamePerformanceSection.tsx` untouched in this plan — FOUND (no diff)

## Next Phase Readiness

- Plan 04 (mount swap + legacy deletion) can now:
  - Replace `<EndgamePerformanceSection data={...} scoreGap={...} />` in `Endgames.tsx` with `<EndgameGamesWithWithoutSection data={perfData} scoreGap={scoreGapData} />`. Note that `scoreGap` is required in the new component (was optional in the legacy section).
  - Delete `frontend/src/components/charts/EndgamePerformanceSection.tsx` after the swap. The score-over-time chart is already extracted (Plan 02) so the deletion is mechanical.
  - Drop the `EndgamePerformanceSection.test.tsx` legacy-section coverage (the chart-only tests in that file have already moved to `EndgameScoreOverTimeChart.test.tsx` per Plan 02 — verify before deletion).
  - Re-run `npm run knip` after the deletion to confirm SEC1-07 (knip-clean removal).
- No blockers for Plan 04.

---
*Phase: 85-section-1-games-with-vs-without-endgame-cards*
*Completed: 2026-05-13*
