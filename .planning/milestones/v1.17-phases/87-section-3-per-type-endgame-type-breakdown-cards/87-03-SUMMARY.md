---
phase: 87-section-3-per-type-endgame-type-breakdown-cards
plan: 03
subsystem: frontend
tags: [endgames, react, vitest, orchestrator, info-popover, url-hydration, legacy-removal]

requires:
  - phase: 87-02
    provides: EndgameTypeCard per-class shell + ENDGAME_TYPE_DESCRIPTIONS + ENDGAME_CLASS_TO_SLUG + SHOW_WDL_BAR_IN_TYPE_CARDS exports in lib/endgameMetrics.ts
  - phase: 87-01
    provides: 10 additive ConversionRecoveryStats wire fields (opp_*_pct, opp_*_games, conv_diff_*, recov_diff_*) on the 0-1 scale
  - phase: 86-section-2-endgame-metrics-4-card-layout
    provides: EndgameMetricsSection orchestrator pattern + lib/endgameMetrics.ts shared module
provides:
  - EndgameTypeBreakdownSection orchestrator (~60 LOC) replacing both legacy EndgameWDLChart + EndgameConvRecovChart mounts
  - HIDDEN_ENDGAME_CLASSES lifted into lib/endgameMetrics.ts as a shared export
  - Page-level h2 InfoPopover on "Endgame Type Breakdown" carrying taxonomy + Conv/Recov metric defs + gauge-band explainer + peer-bullet explainer + 5 per-type one-sentence descriptions
  - `?type=<slug>` URL hydration via SLUG_TO_ENDGAME_CLASS reverse map + useSearchParams effect; shareable deep-links pre-seed the type filter
  - 6 vitest cases covering filtering / layout / ordering / empty-state
  - HUMAN-UAT scaffold (11 tests) including the critical 375px real-device density check
  - Legacy EndgameWDLChart.tsx (352 LOC) and EndgameConvRecovChart.tsx (135 LOC) deleted
affects:
  - phase-87 closure (all 6 SEC3 requirements visible on screen and behind testids)
  - v1.17 milestone progress

tech-stack:
  added: []
  patterns:
    - "Orchestrator-card sibling pattern: EndgameTypeBreakdownSection holds the grid + sub-question, EndgameTypeCard holds per-class composition. Matches Phase 86 EndgameMetricsSection + EndgameMetricCard precedent."
    - "URL hydration via useSearchParams + module-scope SLUG_TO_ENDGAME_CLASS reverse map: unknown slugs are silently ignored (T-87-07 mitigation), known slugs pre-seed the local selectedCategory state on mount and on subsequent SPA navigations."
    - "Page-level h2 InfoPopover absorbs both legacy intros (EndgameWDLChart h3 + EndgameConvRecovChart h3) plus a new peer-bullet explainer per D-12, so section-level h3s can be dropped without losing user-facing context."

key-files:
  created:
    - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx (~65 LOC)
    - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx (~230 LOC, 6 tests across 4 describe groups)
    - .planning/milestones/v1.17-phases/87-section-3-per-type-endgame-type-breakdown-cards/deferred-items.md
  modified:
    - frontend/src/lib/endgameMetrics.ts — added HIDDEN_ENDGAME_CLASSES export
    - frontend/src/pages/Endgames.tsx — imports swapped, HIDDEN_ENDGAME_CLASSES imported from lib, SLUG_TO_ENDGAME_CLASS added, useSearchParams effect added, mount swapped to EndgameTypeBreakdownSection, h2 InfoPopover added
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx — vi.mock swapped from EndgameWDLChart + EndgameConvRecovChart to EndgameTypeBreakdownSection
  deleted:
    - frontend/src/components/charts/EndgameWDLChart.tsx (352 LOC)
    - frontend/src/components/charts/EndgameConvRecovChart.tsx (135 LOC)

key-decisions:
  - "HIDDEN_ENDGAME_CLASSES lifted to lib/endgameMetrics.ts (recommended path per Plan 03 §D-03 Action). Both call sites (Endgames.tsx VISIBLE_ENDGAME_CLASS_ENTRIES + EndgameTypeBreakdownSection visibleCategories filter) now consume the shared export. The local definition in Endgames.tsx was removed entirely."
  - "URL hydration approach: a new useEffect was added that reads searchParams.get('type'), maps slug to EndgameClass via the inverse of ENDGAME_CLASS_TO_SLUG, and calls setSelectedCategory + setGamesOffset(0) when a valid mapping exists. The existing handleCategorySelect only sets local React state (no URL navigation), so without the new effect a direct visit to /endgames/games?type=rook would not pre-seed the filter. The effect's dep array is [searchParams] with an eslint-disable for selectedCategory: the effect is a one-way URL->state seed, NOT a two-way sync; including selectedCategory would retrigger on every category change and fight with handleCategorySelect."
  - "totalGames denominator for sharePct: passed `statsData.total_games` (all filtered games matching current filters, including non-endgame). This is the canonical 'population' field for the page. The plan's must-have explicitly forbids the sum-of-per-type-totals alternative (a single game can count toward multiple Endgame Types, inflating the sum)."
  - "h2 InfoPopover absorbs the two legacy h3 popovers verbatim where possible, plus a new peer-bullet explainer for the mirror-metric symmetry. Pawnless is NOT mentioned in the per-type description list because it is filtered out of the section."
  - "Test top-level card regex anchored to `^type-card-(rook|minor-piece|pawn|queen|mixed|pawnless)$`. An unanchored `/^type-card-/` regex picks up sub-element testids (e.g. `type-card-rook-conv-gauge`), which would have made the 5-card-count and ordering assertions ambiguous. The anchored regex deliberately includes `pawnless` so the 'filtered out' assertion is meaningful."
  - "Vitest test wrapper includes both <MemoryRouter> (for Link) and <TooltipProvider> (for the Games-link Tooltip primitive) — identical pattern to the Plan 02 EndgameTypeCard tests."
  - "Endgames.overallPerformance.test.tsx swap: the two legacy vi.mock() stubs were replaced with a single stub for EndgameTypeBreakdownSection. The test only asserted on the surrounding scaffolding (insight slots, overall performance section), so a single mock stub is functionally equivalent to two."

patterns-established:
  - "Anchored top-level testid regex pattern for orchestrators: when both the parent and child components emit testids in the `<prefix>-<key>` and `<prefix>-<key>-<subkey>` shape, anchor the regex to the explicit list of valid `<key>` values to keep card-count assertions unambiguous."
  - "URL-hydration effect is read-only (URL -> state). Two-way sync (state -> URL) requires additional thought about debouncing and history pollution; defer until a phase explicitly asks for it."

requirements-completed: [SEC3-01, SEC3-02, SEC3-05, SEC3-06, SEC3-07]

duration: ~20min
completed: 2026-05-14
---

# Phase 87 Plan 03: Section 3 Orchestrator + Mount Swap + Legacy Removal Summary

**5-card Endgame Type Breakdown grid ships end-to-end via the new EndgameTypeBreakdownSection orchestrator; Endgames.tsx swaps from two legacy mounts (EndgameWDLChart + EndgameConvRecovChart) to a single new mount with a page-level h2 InfoPopover, plus `?type=<slug>` URL hydration; both legacy components are deleted; all frontend gates (tsc, lint, knip, build) green, with one pre-existing unrelated test failure documented as a deferred item.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-14
- **Completed:** 2026-05-14
- **Tasks:** 7 (5 auto + 1 checkpoint surfaced + 1 gate sweep)
- **Files modified:** 6 (3 created, 1 destination-modified, 2 deleted; 1 test mock updated)

## Accomplishments

- Built `EndgameTypeBreakdownSection.tsx` as a thin presentational orchestrator (~65 LOC including header comment). Filters categories via `HIDDEN_ENDGAME_CLASSES.has(c.endgame_class)`, computes `sharePct = totalGames > 0 ? (cat.total / totalGames) * 100 : 0`, maps `tileTestId = type-card-${ENDGAME_CLASS_TO_SLUG[cat.endgame_class]}`, renders one `<EndgameTypeCard>` per surviving class inside the locked `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` container.
- Lifted `HIDDEN_ENDGAME_CLASSES` from `Endgames.tsx:53` into `lib/endgameMetrics.ts` as a shared `ReadonlySet<EndgameClass>` export. `Endgames.tsx` now imports it; the legacy local definition was removed.
- Swapped both legacy mounts (`<EndgameWDLChart>` and `<EndgameConvRecovChart>`) into a single `<EndgameTypeBreakdownSection>` mount inside one `charcoal-texture` tile. The previous `{statsData.categories.length > 0 && ...}` guard around the second tile was dropped because the new orchestrator handles the empty branch internally.
- Added a page-level h2 InfoPopover next to the existing "Endgame Type Breakdown" h2 carrying: (1) taxonomy + composition (lifted from `EndgameWDLChart.tsx:277-285`), (2) Conv + Recov metric definitions (lifted from `EndgameConvRecovChart.tsx:38-44`), (3) gauge-band explainer (lifted from `EndgameConvRecovChart.tsx:45-49`), (4) NEW peer-bullet explainer per D-12, (5) per-type one-sentence descriptions sourced from `ENDGAME_TYPE_DESCRIPTIONS`.
- Wired `?type=<slug>` URL hydration via `useSearchParams` + a new useEffect with `[searchParams]` deps. The effect reads `searchParams.get('type')`, validates via the module-scope `SLUG_TO_ENDGAME_CLASS` reverse map (T-87-07 mitigation: unknown slugs are silently ignored), and calls `setSelectedCategory` + `setGamesOffset(0)` when a valid mapping fires.
- Deleted both legacy components: `EndgameWDLChart.tsx` (352 LOC) + `EndgameConvRecovChart.tsx` (135 LOC). All cross-references in the frontend (`Endgames.overallPerformance.test.tsx` vi.mock entries) were updated to reference the new orchestrator.
- 6 vitest cases on `EndgameTypeBreakdownSection.test.tsx` across 4 describe groups: Filtering (5 cards rendered, pawnless filtered), Layout (sub-question, section testid, locked Tailwind classes), Ordering (preserves backend total-desc sort), Empty state (empty categories renders section + sub-question with no cards).

## Task Commits

Each task was committed atomically on the worktree branch:

1. **Task 1: EndgameTypeBreakdownSection orchestrator + HIDDEN_ENDGAME_CLASSES lift** — `59ef37f0` (feat)
2. **Task 2: Vitest coverage for EndgameTypeBreakdownSection** — `22e8f82a` (test)
3. **Task 3: Mount swap + h2 InfoPopover + ?type= URL hydration in Endgames.tsx** — `dc77146b` (feat)
4. **Task 4: Delete legacy EndgameWDLChart + EndgameConvRecovChart** — `33c5bb13` (refactor)
5. **Task 5: 87-HUMAN-UAT.md scaffold** — committed earlier in `c117f2f6` during planning (the scaffold pre-existed; acceptance criteria all met)
6. **Task 6: Human-verify checkpoint** — surfaced via this SUMMARY for the orchestrator/user; the implementation pass is complete, only the visual / real-device verification remains
7. **Task 7: Full gate sweep + deferred-items doc for the pre-existing test failure** — `36bf21e0` (docs)

## Decisions Made

- **HIDDEN_ENDGAME_CLASSES lift to lib/endgameMetrics.ts (recommended path).** The plan's Task 1 Action offered two options: lift to `lib/endgameMetrics.ts` (recommended) or inline a local copy with a TODO. Lifted because (a) two consumers already exist (Endgames.tsx + EndgameTypeBreakdownSection), (b) the lift matches the same module where Phase 87 Plan 02 added `ENDGAME_TYPE_DESCRIPTIONS` / `SHOW_WDL_BAR_IN_TYPE_CARDS` / `ENDGAME_CLASS_TO_SLUG`, (c) `Endgames.tsx` was already a candidate for de-duplication.
- **URL hydration: new useEffect added (existing logic verified absent).** Inspection of `handleCategorySelect` confirmed it only sets local React state (`setSelectedCategory`, `setGamesOffset`, `window.scrollTo`) and does NOT navigate. The `<Link to="/endgames/games?type=${slug}">` in `EndgameTypeCard` writes the URL on click, but a direct visit to `/endgames/games?type=rook` (refresh, paste, shared URL) would not pre-seed the filter without a new reader. Added a `useEffect` with `[searchParams]` deps that pre-seeds `selectedCategory` from the URL on mount and on subsequent SPA navigations. Used `eslint-disable-next-line react-hooks/exhaustive-deps` on the dep array because `selectedCategory` is intentionally excluded — the effect is one-way (URL -> state), not a bidirectional sync.
- **SLUG_TO_ENDGAME_CLASS reverse map at module scope.** Built once via `Object.fromEntries(Object.entries(ENDGAME_CLASS_TO_SLUG).map(...))`. Module scope keeps it from rebuilding on every render and signals it as a derived constant of `ENDGAME_CLASS_TO_SLUG`. The reverse map naturally validates the slug (T-87-07): unknown slugs produce `undefined` and the effect short-circuits without touching state.
- **totalGames denominator: statsData.total_games (canonical filtered-games count).** Per CONTEXT D-13 the sharePct denominator must be the total filtered-games population, NOT the sum of per-class totals (a single game can count toward multiple Endgame Types). `statsData.total_games` is the existing field that holds that count.
- **h2 InfoPopover content lifted verbatim where possible.** The taxonomy paragraph + the per-type descriptions are sourced from `EndgameWDLChart.tsx:277-285,287-291`. The Conv/Recov metric definitions + gauge-band explainer are sourced from `EndgameConvRecovChart.tsx:38-49`. The peer-bullet explainer is new per CONTEXT D-12 — it covers the mirror-metric symmetry that didn't exist in either legacy component. Per CLAUDE.md, all en-dashes in the lifted text were replaced with commas or parentheses (the original en-dashes were already minimal).
- **Test top-level card regex anchoring.** Initial naive regex `/^type-card-/` picked up sub-element testids (`type-card-rook-conv-gauge`, `type-card-rook-conv-you`, etc.) inflating the 5-card count to 85. Anchored to the explicit class list `/^type-card-(?:rook|minor-piece|pawn|queen|mixed|pawnless)$/`. Including `pawnless` in the regex (even though it should be filtered out) makes the "no pawnless card" assertion explicit instead of implicit.
- **Endgames.overallPerformance.test.tsx single-mock simplification.** The pre-existing test mocked both `EndgameWDLChart` and `EndgameConvRecovChart` with stable testids that were never asserted on. After the legacy deletions, the single new mock for `EndgameTypeBreakdownSection` is functionally equivalent. No assertion text changes needed.

## URL Hydration Approach (key detail)

The URL hydration was a "Claude's Discretion" item per the plan. Pre-existing state: `handleCategorySelect` only updates local React state; navigation to `/endgames/games?type=<slug>` is performed by the `<Link>` inside each `EndgameTypeCard`. A page refresh or a paste-in URL would land on the games tab but with `selectedCategory` defaulting to `'mixed'` (the `DEFAULT_ENDGAME_CLASS`), so the deep-link was incomplete.

The added effect:

```tsx
useEffect(() => {
  const slug = searchParams.get('type');
  if (!slug) return;
  const parsed = SLUG_TO_ENDGAME_CLASS[slug];
  if (parsed && parsed !== selectedCategory) {
    setSelectedCategory(parsed);
    setGamesOffset(0);
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [searchParams]);
```

`SLUG_TO_ENDGAME_CLASS` is built once at module scope from the inverse of `ENDGAME_CLASS_TO_SLUG`. The `selectedCategory` guard prevents re-seeding when the URL and local state are already in sync. The eslint-disable is intentional and documented inline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test bug] Anchored the top-level card testid regex**

- **Found during:** Task 2 (first vitest run)
- **Issue:** The plan's `getAllByTestId(/^type-card-/)` regex picked up all 85 testids emitted by the 5 cards (each card emits its container testid plus 16 sub-element testids), making the card-count assertion fail (85 != 5).
- **Fix:** Anchored the regex to `/^type-card-(?:rook|minor-piece|pawn|queen|mixed|pawnless)$/` so it matches only the 5 (or 6, in the unfiltered build) top-level card containers.
- **Files modified:** `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx`
- **Verification:** All 6 tests pass.
- **Committed in:** `22e8f82a` (Task 2 commit)

**Total deviations:** 1 auto-fixed (Rule 1, test-fixture bug; the implementation matched the plan).

## TDD Gate Compliance

Plan 03 has one `tdd="true"` task (Task 2 — vitest coverage for the orchestrator). The Plan 03 task ordering puts the orchestrator before the test (Task 1: orchestrator, Task 2: tests), so this is presentational-test-after-build rather than strict RED-then-GREEN. This matches the Plan 02 pattern (component first, tests second) and is acceptable for pure presentational components where the wire shape is fully specified upstream.

Plan-level frontmatter is `type: execute`, not `type: tdd`, so the plan-level RED/GREEN gate enforcement does not apply.

## Gate Sweep Results

| Gate | Status | Notes |
|------|--------|-------|
| `uv run ruff check .` | PASS | All checks passed |
| `uv run ruff format --check .` | PRE-EXISTING FAIL | 47 files would be reformatted on the Phase 87 base; not in Plan 03 scope. Confirmed by running on HEAD before any Plan 03 commits. |
| `uv run ty check app/ tests/` | PASS | All checks passed |
| `uv run pytest` | PASS | 1494 passed, 6 skipped |
| `cd frontend && npm test -- --run` | PRE-EXISTING FAIL | 1 unrelated failure in `MetricStatTooltip.test.tsx` (period-vs-colon separator regex). Logged in `deferred-items.md`. Confirmed against base before Plan 03 changes. |
| `cd frontend && npm run lint` | PASS | Zero errors |
| `cd frontend && npm run knip` | PASS | No dead exports / no unused files |
| `cd frontend && npm run build` | PASS | Production bundle built (1.13 MB main chunk, expected for Recharts-heavy app) |

The two pre-existing failures are unrelated to Plan 03 and are documented in `deferred-items.md`. All Plan 03-specific code paths pass every gate.

## SHOW_WDL_BAR_IN_TYPE_CARDS Status

`SHOW_WDL_BAR_IN_TYPE_CARDS` remains at its Plan 02 default of `true`. The real-device 375px density check (HUMAN-UAT Test 4) is the gating decision and is **awaiting human verification**. If the check fires the fallback, Task 6's checkpoint instructions cover the flip + h2 popover copy update + test re-run + new commit.

## HUMAN-UAT Checkpoint Status

The `87-HUMAN-UAT.md` file is in place with all 11 tests (including the critical 375px real-device density check as Test 4). The orchestrator's spawn instructions explicitly directed: "Surface this as a checkpoint return rather than blocking the entire plan; the rest of the plan (orchestrator, mount swap, legacy delete, full gate sweep) MUST complete and be committed." All 7 tasks' implementation work IS committed; the remaining work is purely human visual / real-device verification.

## Self-Check: PASSED

All five Plan 03 commits exist on the worktree branch:

- `59ef37f0` (Task 1, orchestrator + lib lift) — FOUND
- `22e8f82a` (Task 2, vitest) — FOUND
- `dc77146b` (Task 3, mount swap + h2 + URL hydration) — FOUND
- `33c5bb13` (Task 4, legacy deletions) — FOUND
- `36bf21e0` (Task 7 deferred-items doc) — FOUND

All created files verified present on disk:

- `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` — FOUND
- `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` — FOUND
- `.planning/.../deferred-items.md` — FOUND

All deleted files verified absent on disk:

- `frontend/src/components/charts/EndgameWDLChart.tsx` — ABSENT (deleted)
- `frontend/src/components/charts/EndgameConvRecovChart.tsx` — ABSENT (deleted)

Verification commands all green for Plan 03 surfaces:

- `cd frontend && npx tsc --noEmit` — exits 0
- `cd frontend && npm run lint` — exits 0
- `cd frontend && npx vitest run src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` — 6 passed
- `cd frontend && npm run knip` — exits 0
- `cd frontend && npm run build` — exits 0
- `grep -rn "EndgameWDLChart\|EndgameConvRecovChart" frontend/src/` — only acceptable historical references in comments (EndgameTypeBreakdownSection.tsx header, lib/endgameMetrics.ts lift comments, theme.ts unrelated color comment)
- `grep -c "endgame-type-breakdown-info" frontend/src/pages/Endgames.tsx` — 1
- `grep -c "ENDGAME_TYPE_DESCRIPTIONS" frontend/src/pages/Endgames.tsx` — 6 (1 import + 5 popover entries)

## Next Phase Readiness

- **Phase 87 functionally complete.** 5 of the 6 SEC3 requirements are now visible on screen (SEC3-01 grid, SEC3-02 card composition, SEC3-05 mobile fallback flag wired, SEC3-06 EndgameWDLChart removed, SEC3-07 EndgameConvRecovChart absorbed into per-type cards). SEC3-04 was completed by Plan 01 (per-class mirror-metric peer baseline + sig fields on the wire).
- **HUMAN-UAT remaining work** is purely visual / real-device:
  1. Run the 11 tests in `87-HUMAN-UAT.md`.
  2. If Test 4 (375px density) fires the fallback, flip `SHOW_WDL_BAR_IN_TYPE_CARDS` to `false` and update the h2 popover copy per the test's instructions.
  3. Move the status field in `87-HUMAN-UAT.md` from `partial` to `approved`.
- **Two pre-existing CI gate failures** (ruff format on 47 files + MetricStatTooltip test) are documented in `deferred-items.md`. Both are out-of-scope for Plan 03 and exist on the base commit. CI is presumably tolerating them (or they would have blocked Phase 86 / earlier phases too).
- **POLISH-01..POLISH-04 deferred to Phase 88** per CONTEXT §deferred:
  - POLISH-01: cell-specific peer-bullet neutral bands (±0.05 stays for now)
  - POLISH-02: gauge sig gating (gauges stay always-colored)
  - POLISH-03: `data-testid` / ARIA / semantic-HTML audit
  - POLISH-04: 375px parity audit across Sections 1 / 2 / 3
- **v1.17 milestone description amendment:** the description "Frontend-only refactor" was violated by Plan 01 (10 backend wire fields + service-level helper wiring), authorized at discuss-phase. Same caveat as Phase 86 / Phase 85.1. Recommend amending at `/gsd-complete-milestone` time.

## Known Stubs

None. The 5-card section consumes real wire fields end-to-end; there are no hardcoded `[]` / `{}` / `null` placeholders flowing to UI rendering. Empty-state branches (e.g. "Not enough data yet" for zero-game classes) are correct UX, not stubs.

---
*Phase: 87-section-3-per-type-endgame-type-breakdown-cards*
*Plan: 03*
*Completed: 2026-05-14*
