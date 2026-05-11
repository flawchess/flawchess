---
phase: 83
plan: 03
subsystem: frontend/charts (Endgame Start vs End)
tags: [frontend, ui, 2x2-grid, achievable-score, popover, tdd, mini-wdl-bar]
requires:
  - "Plan 83-02 (backend wire format): EndgamePerformanceResponse.entry_expected_score* fields"
  - "Plan 83-04 (zone band calibration): ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX + entryExpectedScoreZoneColor from generated/endgameZones.ts"
provides:
  - "AchievableScorePopover wrapper component (D-10 verbatim body copy)"
  - "EndgameStartVsEndSection 2x2 grid restructure with new achievable-score bullet (tile-1 row 2) and lifted MiniWDLBar (tile-2 row 1)"
  - "TS EndgamePerformanceResponse interface extended with the 5 new entry_expected_score* fields"
affects:
  - "Plan 5 (LLM prompt) consumes the wire-format fields surfaced by Plan 2; the UI in Plan 3 is the visual companion that closes the units mismatch (D-08)"
tech-stack:
  added: []
  patterns:
    - "Thin popover wrapper component (single-purpose, no bodyCopy prop) — mirrors ScoreConfidencePopover scaffolding with hard-coded D-10 copy"
    - "flex flex-col gap-4 2-row stack inside each tile keeps mobile DOM order matching desktop (no flex-col-reverse, no breakpoint-specific reorder)"
    - "Sibling-derived-value triad pattern: achievableLevel/achievableZoneHex/achievableShowZoneFontColor/achievableColor/showAchievableChart mirrors evalLevel/... and scoreLevel/..."
    - "Disambiguation of MiniBulletChart spy by neutralMin: two bullets now share center=0.5, so the legacy tile-2 prop assertion was updated to use the distinct ±0.05 band as the disambiguator"
key-files:
  created:
    - "frontend/src/components/popovers/AchievableScorePopover.tsx"
    - "frontend/src/components/popovers/__tests__/AchievableScorePopover.test.tsx"
  modified:
    - "frontend/src/types/endgames.ts"
    - "frontend/src/components/charts/EndgameStartVsEndSection.tsx"
    - "frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx"
    - "frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx"
decisions:
  - "Wrapper component (not bodyCopy prop) for AchievableScorePopover — preserves ScoreConfidencePopover's signature, avoids coupling churn. Resolved Open Question 1 in 83-RESEARCH.md."
  - "Tile-2 row 1 WDL slot wraps MiniWDLBar with a label-row matching tile-1 conventions ('Win / Draw / Loss:'). Underlying MiniWDLBar already exposes data-testid='mini-wdl-bar'; the outer wrapper carries data-testid='endgame-wdl-bar-row' for scoping."
  - "Existing tile-2 D-16 test (Phase 81 plan 03 case 'passes Tile 2 score-bullet constants') was updated, not duplicated. Adding a second center=0.5 bullet (the new achievable row) made the original `.find(call => center === 0.5)` ambiguous; disambiguating by neutralMin === -0.05 keeps the contract tight without weakening the assertion."
  - "Popover body copy used verbatim D-10 wording from 83-CONTEXT.md (no rewording during implementation). The CLAUDE.md em-dash-sparingly rule applies — body uses commas/periods only, zero em-dashes."
  - "Two test buildPerf factories (charts/__tests__ and pages/__tests__) were both extended with safe-default entry_expected_score* values (n=50, score=0.5, p=1.0, ci=[0.45, 0.55]). Defaults are in-band, non-significant, and sample-size-sufficient so existing tests that don't override these fields stay unaffected."
metrics:
  duration: "~10 minutes"
  completed: 2026-05-11
  tasks_completed: 3
  files_changed: 6 (2 created + 4 modified)
  tests_added: 15  # 6 in AchievableScorePopover + 9 in EndgameStartVsEndSection
---

# Phase 83 Plan 03: Frontend 2x2 grid + Achievable score bullet Summary

Restructured the existing `EndgameStartVsEndSection` twin-tile section from a
single-row-per-tile layout into a 2x2 grid. Tile 1 ("Where you start") now
shows the existing endgame-entry eval on top and a NEW "Achievable score"
bullet on the bottom (W+0.5D axis, [0.45, 0.55] neutral band shared with the
§0 endgame_score zone for visual parity). Tile 2 ("What you do with it")
gains a `MiniWDLBar` on top (lifted from the WDL table below) and keeps the
existing endgame-score bullet on the bottom. The bottom row of both tiles
shares the same W+0.5D axis so the achievable-vs-achieved gap is directly
readable across the two tiles.

The new bullet is gated by `entry_expected_score_n >= 10` (mirrors the
existing Phase 81 entry-eval gate). Tile color rule per D-11 applies:
`(zone != neutral) AND p < 0.05` — borderline-but-significant cases inside
the neutral band stay neutral. `AchievableScorePopover` is a thin wrapper
around radix `PopoverPrimitive` with the D-10 verbatim body copy hard-coded
inside it (no `bodyCopy` prop, per RESEARCH Open Question 1).

## Files Created

### `frontend/src/components/popovers/AchievableScorePopover.tsx` (84 LOC)

Thin wrapper component mirroring `ScoreConfidencePopover` (hover handling,
PopoverPrimitive scaffolding, HelpCircle trigger). Body is a single `<p>`
with the D-10 verbatim copy:

> This is what a 2300+ rated player would score from your endgame-entry
> positions, via the Lichess winning-chances sigmoid. The Lichess curve is
> fitted on 2300+ rapid games, so scoring below this baseline from positive
> evals is normal at lower ratings and is not a flaw. Compare against your
> achieved Endgame score in the other tile.

Default `data-testid="popover-trigger-achievable-score"`, default
`aria-label="What is Achievable score?"`. Body copy verified to NOT contain
"underperformance", "fall short", or "below your potential" (D-10 forbidden
framings). Body contains "2300+" (twice).

### `frontend/src/components/popovers/__tests__/AchievableScorePopover.test.tsx` (90 LOC)

6 RTL tests pinning the wrapper contract:

- `renders trigger with default data-testid` — testid present
- `trigger carries aria-label for screen readers` — non-empty + mentions "achievable score"
- `accepts custom testId prop` — override works
- `opens on click and shows D-10 body copy containing "2300+"` — body wired via portal
- `body copy does NOT contain the forbidden word "underperformance" (D-10)` — also excludes "fall short", "below your potential"
- `body copy mentions the Lichess sigmoid and the achieved-score comparison`

## Files Modified

### `frontend/src/types/endgames.ts`

`EndgamePerformanceResponse` gains 5 new fields mirroring Plan 2's Python
wire format:

```typescript
entry_expected_score: number;
entry_expected_score_n: number;
entry_expected_score_p_value: number | null;
entry_expected_score_ci_low: number | null;
entry_expected_score_ci_high: number | null;
```

Fields are required (not optional) — matches the surrounding `entry_eval_*`
fields. tsc clean.

### `frontend/src/components/charts/EndgameStartVsEndSection.tsx`

- New imports: `AchievableScorePopover`, `MiniWDLBar`, and `entryExpectedScoreZoneColor` + `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX` from the regenerated `@/generated/endgameZones`.
- New derived-value triad: `achievableLevel`, `achievableZoneHex`, `achievableIsInColoredZone`, `achievableShowZoneFontColor`, `achievableColor`, `showAchievableChart`. Reuses the existing `deriveLevel` and `isConfident` helpers.
- Tile-1 body wrapped in `flex flex-col gap-4`; new achievable-score row appended after the existing entry-eval row. The row uses `data-testid="endgame-achievable-score"` (wrapper), `data-testid="achievable-score-value"` (percent text), and `<AchievableScorePopover />` (default testid).
- Tile-2 body wrapped in `flex flex-col gap-4`; new MiniWDLBar row prepended before the existing endgame-score row. The row uses `data-testid="endgame-wdl-bar-row"`; underlying MiniWDLBar already exposes `data-testid="mini-wdl-bar"`.
- Outer `lg:grid-cols-2` grid is UNCHANGED (D-12: only tile interiors change).
- Existing "Games with vs without Endgame" table in `EndgamePerformanceSection.tsx` is NOT modified (D-08 redundancy accepted; `git diff` against that file: zero).

### `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx`

- `buildPerf` factory extended with in-band, non-significant defaults for the 5 new fields so existing tests stay unaffected.
- 9 new RTL cases (see test list below).
- 1 existing tile-2 D-16 case updated: disambiguates the `MiniBulletChart` spy by `neutralMin === -0.05` since the new achievable bullet also uses `center === 0.5`.

### `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx`

`buildPerf` factory extended with the same in-band defaults so the page-level
integration test compiles and continues passing.

## RTL Test Cases Added (9 in EndgameStartVsEndSection)

1. `renders the achievable-score bullet inside tile-1 when entry_expected_score_n >= 10` — testid + 62% rendered
2. `renders "Not enough data yet" inside tile-1 row 2 when entry_expected_score_n < 10` — independent of tile-1 row 1 gate
3. `paints achievable-score value color when zone != neutral AND p < 0.05 (above band)` — ZONE_SUCCESS at 0.62
4. `paints achievable-score value color when zone != neutral AND p < 0.05 (below band)` — ZONE_DANGER at 0.40
5. `does NOT paint achievable-score color when sig but inside neutral band` — D-11 zone-AND-sig rule
6. `renders MiniWDLBar at the top of tile-2 (D-13)` — `data-testid="mini-wdl-bar"` present in tile-2 region
7. `achievable-score popover trigger has data-testid="popover-trigger-achievable-score"` — stable testid
8. `achievable-score popover body does NOT contain the word "underperformance" (D-10)` — open via click, scan document
9. `passes achievable-score W+0.5D constants to MiniBulletChart (D-12 axis parity)` — center=0.5, neutral [0.45, 0.55], domain=0.25

## Verification

| Check | Result |
|-------|--------|
| `npx vitest run src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | 26/26 passed (17 pre-existing + 9 new) |
| `npx vitest run src/components/popovers/__tests__/AchievableScorePopover.test.tsx` | 6/6 passed |
| `npx vitest run src/pages/__tests__/Endgames.startVsEnd.test.tsx` | 6/6 passed (no regression in page-level integration) |
| `npx vitest run` (full frontend suite) | 355/355 passed (30 files) |
| `npx tsc -b --force` | EXIT=0 (clean) |
| `npm run lint` | clean |
| `npm run knip` | clean (no new unused exports — AchievableScorePopover, entryExpectedScoreZoneColor, ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX all imported by EndgameStartVsEndSection.tsx) |
| `grep -c '2300+' frontend/src/components/popovers/AchievableScorePopover.tsx` | 2 |
| `grep -ci 'underperformance\|fall short\|below your potential' frontend/src/components/popovers/AchievableScorePopover.tsx` | 0 |
| `grep -c "AchievableScorePopover" frontend/src/components/charts/EndgameStartVsEndSection.tsx` | 2 (import + JSX) |
| `grep -c "from '@/components/stats/MiniWDLBar'" frontend/src/components/charts/EndgameStartVsEndSection.tsx` | 1 |
| `grep -c "entryExpectedScoreZoneColor" frontend/src/components/charts/EndgameStartVsEndSection.tsx` | 2 (import + call) |
| `grep -c "data-testid=\"achievable-score-value\"" frontend/src/components/charts/EndgameStartVsEndSection.tsx` | 1 |
| `grep -c "data-testid=\"endgame-achievable-score\"" frontend/src/components/charts/EndgameStartVsEndSection.tsx` | 1 |
| `grep -c "flex-col-reverse" frontend/src/components/charts/EndgameStartVsEndSection.tsx` | 0 (mobile DOM order rule) |
| `git diff frontend/src/components/charts/EndgamePerformanceSection.tsx` | empty (D-08 redundancy accepted, existing table unchanged) |

## Mobile/Desktop Parity (CLAUDE.md "Always apply changes to mobile too")

`EndgameStartVsEndSection` has no separate desktop/mobile branches — the
existing component uses `grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)]` and
`grid-cols-1 lg:grid-cols-2` for responsive stacking. The new `flex
flex-col gap-4` 2-row stack inside each tile inherits the same responsive
behavior naturally: top row above bottom row on every viewport (no
breakpoint-specific reorder, no `flex-col-reverse`). The MiniWDLBar uses
`width: 100%` inside its container, so it stretches across mobile width as
expected. No duplicated markup found via `grep` against other endgame
components — the change is single-source.

## Deviations from Plan

**1. [Rule 1 - Bug] Updated existing tile-2 D-16 test to disambiguate the MiniBulletChart spy**

- **Found during:** Task 3 GREEN
- **Issue:** The pre-existing test `passes Tile 2 score-bullet constants to MiniBulletChart (D-16)` finds the tile-2 call via `calls.find(([props]) => props.center === 0.5)`. After the restructure, the new achievable-score bullet ALSO uses `center === 0.5`, so `find` returns the first match (which is the achievable bullet by DOM order). The test then asserted `neutralMin: -0.05` and found `neutralMin: 0.45`.
- **Fix:** Tightened the predicate to `center === 0.5 && neutralMin === -0.05` so the spy disambiguates between the two W+0.5D bullets. The original contract (tile-2 uses the score-bullet ±0.05 band) is preserved — the test is now more specific, not weaker.
- **Files modified:** `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx`
- **Commit:** `56eebbd7` (GREEN of Task 3)

**2. [Rule 3 - Blocker] Updated page-level Endgames.startVsEnd.test.tsx buildPerf**

- **Found during:** Task 1 verify
- **Issue:** `src/pages/__tests__/Endgames.startVsEnd.test.tsx` has its own `buildPerf` factory that returns `EndgamePerformanceResponse` (full type). After Task 1 added 5 required fields, that factory's return literal would be incomplete and the page-level test would fail to compile.
- **Fix:** Added the same in-band, non-significant defaults for the 5 new fields. The page-level test does not target the new bullet, so the defaults are inert.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx`
- **Commit:** `96377591` (RED of Task 3, bundled with the buildPerf extension to keep the build green)

**3. [Style] Em-dash audit on the popover comment block**

- **Found during:** Task 2 verify
- **Issue:** Initial commit had two `—` em-dashes inside the in-file comment that documented D-10 forbidden words. CLAUDE.md "Em-dashes sparingly" is a style preference for human-readable text (not a hard rule for code comments), but the acceptance criterion `grep -ci 'underperformance' = 0` was failing because my comment ALSO listed the forbidden word verbatim.
- **Fix:** Rewrote the comment to reference 83-CONTEXT.md D-10 by name instead of inlining the forbidden words. Em-dashes left intact in comments (one separator dash is fine per CLAUDE.md). Body popover copy has zero em-dashes.
- **Files modified:** `frontend/src/components/popovers/AchievableScorePopover.tsx`
- **Commit:** `23c68c5c` (GREEN of Task 2, fix applied before commit)

No architectural changes were needed (no Rule 4 escalations).

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1 (extend TS type) | (schema-only — gated by Tasks 2/3 behavior tests) | `cc125fd6` — 5 new fields with explicit types | not needed |
| 2 (AchievableScorePopover) | `ca30aea4` — 6 failing tests on a non-existent component | `23c68c5c` — wrapper with D-10 body, all 6 pass | not needed |
| 3 (2x2 restructure) | `96377591` — 9 failing tests + buildPerf factory extension | `56eebbd7` — restructure + tile-2 D-16 spy disambiguation, all 26 pass | not needed |

Task 1 is schema-only, so the failing-then-passing cycle is implicit in
Task 3's RED commit (which would not compile if Task 1's fields were absent).
This is the same pattern used in Plan 2 SUMMARY.md ("Task 2 ships fields
whose behavior is tested by Task 3").

## Known Stubs

None. The new bullet is wired end-to-end from the wire format (Plan 2) and
zone band (Plan 4) through the derived-value triad to the rendered DOM
with stable testids for browser automation. Plan 5 (LLM prompt) consumes
the same fields from the backend, not from this UI.

## Self-Check: PASSED

- `frontend/src/components/popovers/AchievableScorePopover.tsx` — FOUND (created)
- `frontend/src/components/popovers/__tests__/AchievableScorePopover.test.tsx` — FOUND (created)
- `frontend/src/types/endgames.ts` — FOUND (modified)
- `frontend/src/components/charts/EndgameStartVsEndSection.tsx` — FOUND (modified)
- `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — FOUND (modified)
- `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` — FOUND (modified)
- Commit `cc125fd6` (Task 1) — FOUND
- Commit `ca30aea4` (Task 2 RED) — FOUND
- Commit `23c68c5c` (Task 2 GREEN) — FOUND
- Commit `96377591` (Task 3 RED) — FOUND
- Commit `56eebbd7` (Task 3 GREEN) — FOUND
- All verification commands clean (vitest 355/355, tsc clean, eslint clean, knip clean, grep counts as expected)
