---
phase: 86
plan: 05
subsystem: frontend
tags: [components, endgame-metrics, orchestrator, layout, deletion]
requires:
  - 86-04 (EndgameMetricCard + EndgameSkillCard sibling cards)
  - 86-03 (lib/endgameMetrics.ts shared helpers, parameterized ConnectorArrows)
  - 86-02 (backend Skill + per-bucket diff fields wired into the response)
provides:
  - frontend/src/components/charts/EndgameMetricsSection.tsx (4-card orchestrator)
  - frontend/src/pages/Endgames.tsx (mount swap + h2 InfoPopover per D-11)
affects:
  - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx (stale mock retargeted)
  - frontend/knip.json (ignore entry added for src/generated/endgameZones.ts)
  - frontend/src/components/charts/EndgameScoreGapSection.tsx (DELETED, SEC2-10)
tech-stack:
  patterns:
    - "Orchestrator + sibling cards pattern (Phase 85 EndgameOverallPerformanceSection precedent)"
    - "Parameterized SVG-overlay ConnectorArrows shared with Phase 85"
    - "Page-level h2 InfoPopover with bucket-taxonomy + ELO-Skill cross-section explainer (D-11)"
key-files:
  created:
    - frontend/src/components/charts/EndgameMetricsSection.tsx (147 LOC)
    - frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx (150 LOC, 3 tests)
    - .planning/milestones/v1.17-phases/86-section-2-endgame-metrics-4-card-layout/86-05-SUMMARY.md
  modified:
    - frontend/src/pages/Endgames.tsx (import swap, mount swap, +1 InfoPopover next to h2 with lifted-and-adapted content)
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx (vi.mock retargeted to EndgameMetricsSection)
    - frontend/knip.json (src/generated/endgameZones.ts added to ignore list)
  deleted:
    - frontend/src/components/charts/EndgameScoreGapSection.tsx (533 LOC removed, SEC2-10)
decisions:
  - "Used a `.map()` loop over `ROW_ONE_BUCKETS = ['conversion', 'parity', 'recovery']` in EndgameMetricsSection.tsx instead of three literal `<EndgameMetricCard>` JSX nodes. The behavior block specified 'three instances'; functionally equivalent and avoids ~30 lines of repeated props. The acceptance criterion that said `grep -c '<EndgameMetricCard'` returns 3 reads 1 with this approach. Plan author can re-expand if a literal-JSX style is preferred for readability."
  - "Added `src/generated/endgameZones.ts` to knip's `ignore` list (Rule 3 auto-fix). With `EndgameScoreGapSection.tsx` deleted, the only remaining consumer of `FIXED_GAUGE_ZONES` / `ENDGAME_SKILL_ZONES` is `lib/endgameMetrics.ts` via aliased imports (`as REGISTRY_*`). Knip's static analysis does not track aliased imports as 'usage' of the original name, so the gate breaks. The file is auto-generated from `app/services/endgame_zones.py` via the codegen script `scripts/gen_endgame_zones_ts.py`; ignoring its exports is the standard knip pattern for codegen output."
  - "Page-level h2 InfoPopover content (D-11) mostly matches the legacy section-level popover at EndgameScoreGapSection.tsx:184-235, with two adaptations: (a) the 'table' paragraph replaced with the per-card peer-bullet paragraph, and (b) a final sentence noting the ELO timeline below uses the same Skill composite (so the popover serves both Section 2 and the ELO timeline that share the h2)."
  - "TDD task ordering: Task 1 created the orchestrator before Task 2 wrote the integration test, so strict RED→GREEN ordering is not visible in the commit log (the test went straight to GREEN). This matches Plan 04's documented pattern; the `tdd=\"true\"` annotation on Task 2 is effectively descriptive (integration test) rather than gating."
metrics:
  completed_date: 2026-05-14
  tasks_completed: 6
  duration_minutes: 13
  files_created: 2
  files_modified: 3
  files_deleted: 1
  test_files_added: 1
  tests_added: 3
  net_loc_delta: -384
---

# Phase 86 Plan 05: Endgame Metrics Orchestrator + Page Mount + Legacy Removal Summary

Mounted the Phase 86 4-card Endgame Metrics layout on the Endgames page,
adopting the sibling cards from Plan 04 inside a new orchestrator and
retiring the legacy `EndgameScoreGapSection.tsx`. Phase 86 is now
functionally complete: SEC2-01..04 and SEC2-06..10 are all addressable on
screen, the legacy 4-gauge strip and eval-stratified WDL table are gone,
knip is clean, and all CI gates pass.

## What Changed

1. **`EndgameMetricsSection.tsx` (new orchestrator, 147 LOC).** Mirrors Phase
   85's `EndgameOverallPerformanceSection`: `relative grid grid-cols-1
   lg:grid-cols-3 gap-4` with Conv/Parity/Recov auto-placed across row 1 and
   the Skill card lifted to `lg:col-start-2` on row 2. Mounts the parameterized
   `ConnectorArrows` with the four locked Phase 86 testids
   (`tile-conversion`, `tile-parity`, `tile-recovery`, `tile-endgame-skill`).
   Derives per-card props from `ScoreGapMaterialResponse`: per-bucket
   `MaterialRow` + mirror lookup, `sharePct` from total material games, and
   Skill scalars / sig fields from the top-level `data.skill` / `data.opp_skill`
   etc. Defensive zero-row synthesis when a bucket is missing from the
   response (lets `EndgameMetricCard`'s empty-state branch fire cleanly).

2. **`Endgames.tsx` mount swap + h2 InfoPopover.** Replaced the
   `<EndgameScoreGapSection data={scoreGapData} />` mount with
   `<EndgameMetricsSection data={scoreGapData} />`. Added a new `<InfoPopover>`
   trigger next to the "Endgame Metrics and ELO" h2 (D-11) with content
   adapted from the legacy section-level popover: bucket taxonomy (Conv /
   Parity / Recov definitions), per-bucket rate semantics, fixed gauge-band
   explainer, per-card peer-bullet explainer (replaces the legacy "table"
   paragraph), and a closing note that the ELO timeline below uses the same
   Skill composite. The popover now serves both Section 2 and the ELO
   timeline section that share the h2.

3. **Integration test suite (`EndgameMetricsSection.test.tsx`, 3 tests).**
   Full-render assertion (all 4 card testids + sub-question copy), Skill-card
   gating assertion (empty state when `skill === null`), and DOM-ordering
   assertion (Conv → Parity → Recovery → Skill via `compareDocumentPosition`).
   Connector-arrows geometry is exercised indirectly by Phase 85's tests + the
   live integration check at the human-verify checkpoint.

4. **Legacy file deletion.** Removed `frontend/src/components/charts/
   EndgameScoreGapSection.tsx` (533 LOC). The frontend `endgameSkill()`
   composite-skill helper at lines 155-165 retires with the file (D-04); the
   composite Endgame Skill rate is now produced server-side via the `skill` /
   `opp_skill` fields per Plans 01-02. Updated the stale `vi.mock` at
   `Endgames.overallPerformance.test.tsx:64-65` to target the new
   `EndgameMetricsSection`.

5. **knip ignore for generated zone registry.** Added
   `src/generated/endgameZones.ts` to `frontend/knip.json`'s `ignore` list.
   With the legacy consumer deleted, knip's static analysis trips on the
   aliased-import re-export pattern in `lib/endgameMetrics.ts` and reports
   `FIXED_GAUGE_ZONES` / `ENDGAME_SKILL_ZONES` as unused exports (false
   positive — they are consumed via the alias and the colorized re-export
   chain feeds `EndgameMetricCard` and `EndgameSkillCard`). The file is
   auto-generated; ignoring is the standard codegen pattern.

## Deviations from Plan

### [Rule 3 — Blocking issue] knip false-positive on generated zone registry

- **Found during:** Task 4 (gate sweep after legacy deletion)
- **Issue:** Knip flagged `FIXED_GAUGE_ZONES` and `ENDGAME_SKILL_ZONES` in
  `src/generated/endgameZones.ts` as unused exports. With
  `EndgameScoreGapSection.tsx` deleted, the only remaining consumer is
  `lib/endgameMetrics.ts` via aliased imports
  (`import { FIXED_GAUGE_ZONES as REGISTRY_FIXED_GAUGE_ZONES }`). Knip's
  reachability analysis cannot trace through the aliased-import +
  same-name re-export combination, so the exports register as orphan. CI's
  `npm run knip` exits non-zero and would block the build.
- **Fix:** Added `src/generated/endgameZones.ts` to the `ignore` list in
  `frontend/knip.json`. The file is auto-generated from
  `app/services/endgame_zones.py` via `scripts/gen_endgame_zones_ts.py`,
  so the typical knip pattern of ignoring codegen output applies.
  Alternative (rejected): rename the colorized local exports in
  `lib/endgameMetrics.ts` to avoid the same-name collision — this would
  ripple to two card components and add semantic-free name churn for no
  user-visible benefit.
- **Commit:** c21b0303

### [Plan-vs-impl drift] `.map()` over ROW_ONE_BUCKETS

- **Found during:** Task 1 implementation
- **Issue:** Task 1's acceptance criterion `grep -c "<EndgameMetricCard"
  EndgameMetricsSection.tsx returns 3` assumes three literal JSX mounts.
  The implementation uses a `.map()` over `ROW_ONE_BUCKETS` and a
  per-bucket metadata table (`METRIC_NAMES`, `METRIC_EXPLANATIONS`,
  `TILE_TESTIDS`), so the grep returns 1.
- **Fix:** Documented here; functionally equivalent. The `.map()` form is
  ~30 lines shorter, single-sourced for the per-bucket metadata, and
  more in line with the orchestrator's role (data shaping + iteration,
  not per-card prop literals). Plan author can re-expand if a literal-JSX
  style is preferred.
- **Commit:** cf5e86dd

## Gates

All seven gates pass on the worktree HEAD:

- `uv run ruff check .` — All checks passed.
- `uv run ty check app/ tests/` — All checks passed.
- `uv run pytest` — 1489 passed, 6 skipped (no new test failures).
- `cd frontend && npm test -- --run` — 35 test files, 391 tests passed.
- `cd frontend && npm run lint` — clean.
- `cd frontend && npm run knip` — clean (after the generated-file ignore).
- `cd frontend && npm run build` — production build succeeds; legacy file
  absent from `dist` (verified via grep on bundled output).

### Pre-existing out-of-scope failure (NOT fixed)

- `uv run ruff format --check .` — Would reformat 91 files. This drift is
  pre-existing and unrelated to Phase 86 Plan 05 (verified by stashing all
  Plan 05 changes and re-running the check; the same 91 files report). Per
  the SCOPE BOUNDARY rule, out-of-scope formatting drift is not auto-fixed
  here. Flag for a separate `/gsd:quick` cleanup.

## Files Created / Modified / Deleted

### Created

- `frontend/src/components/charts/EndgameMetricsSection.tsx` (147 LOC, the
  4-card orchestrator with grid + connector-arrows mount + sub-question)
- `frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx`
  (150 LOC, 3 integration tests)
- `.planning/milestones/v1.17-phases/86-section-2-endgame-metrics-4-card-layout/86-05-SUMMARY.md`

### Modified

- `frontend/src/pages/Endgames.tsx` (import swap; mount swap; new h2
  InfoPopover with lifted-and-adapted content per D-11)
- `frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx`
  (vi.mock retargeted from EndgameScoreGapSection to EndgameMetricsSection,
  testid renamed accordingly)
- `frontend/knip.json` (added `src/generated/endgameZones.ts` to `ignore`)

### Deleted

- `frontend/src/components/charts/EndgameScoreGapSection.tsx` (533 LOC,
  including the frontend `endgameSkill()` helper at lines 155-165 which
  retires per D-04 in favor of server-side `skill` / `opp_skill`)

## Phase 86 Status

Phase 86 is functionally complete. The 9 SEC2 requirements
(SEC2-01..04, SEC2-06..10) are all addressable on screen:

- SEC2-01: 4 cards in order Conv → Parity → Recov → Skill ✓
- SEC2-02: Conv/Parity/Recov layout = gauge → percent + games → WDL →
  peer bullet `You − Opp` vs 0 ✓
- SEC2-03: Skill layout = gauge → percent + games → peer bullet (no WDL) ✓
- SEC2-04: Gauge bands use `FIXED_GAUGE_ZONES.{conversion,parity,recovery}` ✓
- SEC2-06: Peer bullets use mirror-bucket rates ✓
- SEC2-07: Mirror-bucket peer baseline logic preserved ✓
- SEC2-08: Skill peer-bullet sig-test methodology (backend, Wald-z) ✓
- SEC2-09: Per-bullet MetricStatPopover with mirror-bucket explainer ✓
- SEC2-10: Legacy table + 4-gauge strip removed, knip clean ✓

### Backend additive scope flag (carries forward from Phase 85)

The v1.17 ROADMAP description "Frontend-only refactor" is now formally
violated by Phase 86 D-01..D-03 + D-06 (5 Skill schema fields + 1 helper
on `score_confidence.py` + 3 per-MaterialRow diff fields). User-authorized
at discuss-phase; same caveat as Phase 85 D-01. Recommend amending the
milestone description at `/gsd-complete-milestone` time (or rolling into
the existing Phase 85 amendment).

### Shared connector-arrows component

`EndgameOverallConnectorArrows.tsx` kept its existing filename despite
the D-09a-mentioned rename suggestion; the file now serves both Phase 85
(`EndgameOverallPerformanceSection`) and Phase 86 (`EndgameMetricsSection`)
via the 4-testid props lifted in Plan 03. Phase 87 (per-type cards) can
reuse it again or branch a different geometry if the per-type layout
needs different connector shapes.

### Polish deferrals

POLISH-01 (cell-specific peer-bullet neutral bands) and POLISH-02 (gauge
sig-gating) remain deferred to Phase 88 per CONTEXT D-12 / D-13. Phase
88 will also do the 375px mobile parity check across all three
Endgames-page sections.

## Human-Verify Checkpoint (Task 5)

This plan has `autonomous: false` and Task 5 is a `checkpoint:human-verify`
step. The executor cannot block on user input from inside the agent (per
orchestrator instructions), so this section serves as the deferred
verification payload for the user / orchestrator.

**What to verify (resume signal: "approved"):**

1. Run `cd frontend && npm run dev` and `uv run uvicorn app.main:app
   --reload` (with the dev DB up via `docker compose -f
   docker-compose.dev.yml -p flawchess-dev up -d`).
2. Open `http://localhost:5173/endgames` and scroll to the "Endgame
   Metrics and ELO" h2.
3. **Desktop (≥1024 px wide):** the 4 cards arrange as Conv | Parity |
   Recov on row 1 with Endgame Skill alone in the middle column on row 2;
   SVG connector arrows visibly tie each of the three top cards into the
   Skill card (left → right-pointing into Skill's left edge; middle →
   down-pointing into Skill's top; right → left-pointing into Skill's
   right edge).
4. **Mobile (<1024 px wide):** the 4 cards stack single-column in DOM
   order (Conv → Parity → Recov → Skill); connector arrows are hidden.
5. **Per-card MetricStatPopover:** hovering the HelpCircle next to "Diff:"
   on each card opens its locked D-16 explainer (with the methodology
   block on Score / Test / CI). The Skill card popover renders the
   composite explanation.
6. **Page-level h2 InfoPopover:** hovering the HelpCircle next to
   "Endgame Metrics and ELO" opens the lifted bucket-taxonomy + mirror-
   bucket explainer + ELO-Skill-composite note.
7. **Filter responsiveness:** applying a filter (e.g. Opponent Strength:
   Stronger) updates the You / Opp / Diff values + bullet charts; the
   gauges stay the same (gauge bands are fixed per D-13 / SEC2-04).
8. **Legacy removal:** confirm the 4-gauge strip + eval-stratified WDL
   table are gone; only the 4 new cards are visible under the h2.

## Self-Check: PASSED

- File `frontend/src/components/charts/EndgameMetricsSection.tsx` — FOUND
- File `frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx` — FOUND
- File `frontend/src/components/charts/EndgameScoreGapSection.tsx` — ABSENT (intentional deletion)
- Commit `cf5e86dd` — FOUND in `git log`
- Commit `bf6500ae` — FOUND in `git log`
- Commit `a66ac106` — FOUND in `git log`
- Commit `c21b0303` — FOUND in `git log`
