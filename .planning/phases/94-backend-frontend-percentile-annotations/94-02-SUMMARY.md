---
phase: 94-backend-frontend-percentile-annotations
plan: 02
subsystem: frontend
tags: [frontend, react, percentile, chip, popover, lucide, theme, radix]

# Dependency graph
requires:
  - phase: 94-backend-frontend-percentile-annotations
    plan: 01
    provides: 4 nullable percentile fields on EndgamePerformanceResponse + ScoreGapMaterialResponse
provides:
  - "frontend/src/types/endgames.ts: 4 new nullable `*_percentile: number | null` TS fields mirroring the Pydantic schemas"
  - "frontend/src/components/charts/PercentileChip.tsx: reusable banded-color pill chip with flame tier stack and Radix popover (skill-isolating + improvement-focus flavors)"
  - "PercentileChipFlavor type export for downstream call-site routing"
affects: [94-03-frontend-wire]

# Tech tracking
tech-stack:
  added: []  # no new packages — lucide-react, radix-ui, clsx, tailwind-merge all pre-existing
  patterns:
    - "Chip-as-trigger pattern (Radix Popover Trigger asChild wrapping the colored pill span itself — D-01)"
    - "Theme-driven banded colors: import ZONE_DANGER / GAUGE_NEUTRAL / ZONE_SUCCESS from @/lib/theme; no inline hex/oklch outside CHIP_TEXT_COLOR"
    - "Flame-tier dispatch: cascade `if (p >= TIER_3) return 3` — highest tier only (NOT cumulative)"
    - "Label floor at MIN_TOP_PERCENT=1 — prevents 'Top 0%' at p99.9 (Pitfall 7)"
    - "jsdom oklch-string normalization: tests parse the triplet rather than comparing strings (jsdom strips trailing zeros: `oklch(0.50 ...)` → `oklch(0.5 ...)`)"

key-files:
  created:
    - "frontend/src/components/charts/PercentileChip.tsx (153 LOC — component + types + helpers + popover body)"
    - "frontend/src/components/charts/__tests__/PercentileChip.test.tsx (15 unit tests across 5 behavior groups)"
  modified:
    - "frontend/src/types/endgames.ts (4 new nullable percentile fields with JSDoc gate-clause comments)"

key-decisions:
  - "Chose GAUGE_NEUTRAL (not ZONE_NEUTRAL) for the middle band — matches the page's existing gauge palette for visual consistency (UI-SPEC §Color Assumption A2)."
  - "No knip suppression added: knip exits 0 in Wave-2-only snapshot (likely `ignoreExportsUsedInFile` + test-file usage of the export is enough). Wave 3 will import the chip in the same PR, so no follow-up needed."
  - "CHIP_TEXT_COLOR is the lone hard-coded oklch in the component, documented inline as a chip-internal text-on-fill convention rather than a semantic theme token."
  - "Tests use a parseOklch() helper that compares triplets numerically — jsdom normalizes `oklch(0.50 0.15 25)` to `oklch(0.5 0.15 25)` so string equality fails. Numeric triplet comparison is robust to that normalization and to future theme-constant precision changes."
  - "Popover body avoids em-dashes (per CLAUDE.md style guidance) and the jargon-free copy-minimalism discipline (no 'sigmoid' / 'Wilson' / 'n=' callouts), matching `feedback_popover_copy_minimalism.md`."

patterns-established:
  - "Reusable banded-color chip pattern for percentile-style UI affordances on metric rows"
  - "Component-internal popover-body subcomponent (no separate file) for flavor-routed copy — RESEARCH §A4"

requirements-completed: [PCTL-03, PCTL-04, PCTL-05]

# Metrics
duration: ~18min
completed: 2026-05-23
---

# Phase 94 Plan 02: Frontend PercentileChip + TS field mirror Summary

**Reusable banded-color pill chip with lucide Flame tiers and a Radix popover shell — built standalone, ready for Wave 3 to wire into the 4 ΔES rows. Plus a 4-field manual TS mirror of the Wave 1 Pydantic schema additions.**

## Performance

- **Duration:** ~18 min (including a 5-min initial `npm install` because the worktree had no `node_modules`)
- **Started:** 2026-05-23T08:36Z
- **Completed:** 2026-05-23T08:54Z
- **Tasks:** 2 (Task 1 single-step; Task 2 TDD: RED → GREEN, no REFACTOR needed)
- **Files created:** 2
- **Files modified:** 1

## Accomplishments

- 4 additive nullable TS fields (`achievable_score_gap_percentile`, `score_gap_percentile`, `section2_score_gap_conv_percentile`, `section2_score_gap_parity_percentile`) on the existing endgame response interfaces — non-breaking, mirroring the Wave 1 Pydantic shape, with JSDoc comments documenting each field's reliability gate clause.
- `PercentileChip` standalone component: banded color pill (red / blue / green keyed off p25 / p75), 0..3 lucide Flame icons at the p≥90 / p≥95 / p≥99 tiers (highest tier only), Radix popover shell with hover-open and tap-toggle, two flavor-routed copy bodies (skill-isolating vs improvement-focus).
- 15 unit tests across 5 behavior groups (label formatter, band-color dispatch, flame-tier dispatch, popover flavor routing, accessibility/contract).
- Full frontend test suite remains green: 626/626 passed, no regressions.
- knip clean: the unused export in this wave is not flagged.

## Task Commits

1. **Task 1: Mirror 4 backend percentile fields into TS endgame types** — `dd64eed2` (feat)
2. **Task 2 RED: failing PercentileChip tests** — `5bf9b219` (test)
3. **Task 2 GREEN: implement PercentileChip with banded color, flame stack, popover** — `6fd5ee87` (feat)

_TDD discipline maintained on Task 2: GREEN commit follows a RED commit whose tests fail because `PercentileChip.tsx` does not exist yet._

## Files Created/Modified

- `frontend/src/types/endgames.ts` — added `achievable_score_gap_percentile` on `EndgamePerformanceResponse` (after the existing `achievable_score_gap_ci_high` sibling); added `score_gap_percentile`, `section2_score_gap_conv_percentile`, `section2_score_gap_parity_percentile` on `ScoreGapMaterialResponse`, each placed adjacent to its existing CI/p_value sibling group. Each field has a JSDoc one-liner referencing the gate clause from the backend. NO `section2_score_gap_recov_percentile` — D-12 recovery exclusion mirrored from the backend.
- `frontend/src/components/charts/PercentileChip.tsx` — new file (~153 LOC). Exports `PercentileChip` component + `PercentileChipFlavor` type + `PercentileChipProps` interface. Pure helpers: `deriveBandColor`, `deriveFlameCount`, `formatTopXPercent`. Internal `PercentileChipPopoverBody` subcomponent for flavor-routed copy. Named constants: `HOVER_OPEN_DELAY_MS`, `PERCENTILE_BAND_LOW`, `PERCENTILE_BAND_HIGH`, `FLAME_TIER_1/2/3`, `MIN_TOP_PERCENT`, `FLAME_ICON_SIZE_CLASS`, `CHIP_TEXT_COLOR` (the lone hard-coded color, documented in a comment as a chip-internal text-on-fill convention).
- `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` — new file with 15 `it(...)` blocks across 5 behavior groups; scaffolding inherited verbatim from `EndgameOverallScoreGapRow.test.tsx` (matchMedia + ResizeObserver stubs, `afterEach(cleanup + vi.clearAllMocks)`).

## Decisions Made

- **GAUGE_NEUTRAL chosen for the middle band (not ZONE_NEUTRAL).** Both are blue, but GAUGE_NEUTRAL = `oklch(0.55 0.18 260)` is already the gauge's "typical skill-cohort range" color on the same Stats page — the chip joining that palette reinforces the existing visual language. ZONE_NEUTRAL exists at `oklch(0.50 0.14 260)` but is used on zone-band tile fills, not user-state pills. UI-SPEC §Color Assumption A2 calls this out explicitly.
- **Tests use `parseOklch()` triplet comparison, not string equality.** jsdom's `style.backgroundColor` setter normalizes `oklch(0.50 0.15 25)` → `oklch(0.5 0.15 25)` (drops the trailing zero on the lightness). Comparing the parsed numeric triplet is robust to that and to any future theme-constant precision changes.
- **No knip suppression added.** Wave 2 ends with `PercentileChip` exported and not yet imported by any production code; Wave 3 will wire it in the same PR. Running `npm run knip` exits 0 in the Wave-2-only snapshot, so no `knip-ignore` or `knip.json` change is needed. If CI runs knip on this commit in isolation (it doesn't — CI runs against the merged branch), the test file's import would satisfy knip anyway because the project sets `ignoreExportsUsedInFile`.
- **`CHIP_TEXT_COLOR = 'oklch(0.98 0 0)'` is hard-coded with an inline comment.** This is the chip's near-white text color rendered on top of all three band fills. It is a text-on-fill convention specific to this component, not a semantic theme token (no "danger text" / "success text" semantics apply because it is the same near-white in all three branches). Per the plan's interface contract, this is the documented sole exception to the no-hard-coded-colors rule for this file.
- **Popover bodies avoid em-dashes and jargon.** CLAUDE.md style guidance asks to use em-dashes sparingly in user-facing UI copy; both popover bodies are punctuated with commas and periods only. Both also obey `feedback_popover_copy_minimalism.md` (no methodology jargon, no "n=", no caveats — just WHAT + sign convention).
- **Flame icons get `data-testid="${testId}-flame"`.** Tests need to count flames by querying; using the testId convention rather than a class-based count keeps the test stable against className refactors. Flames remain `aria-hidden="true"` on the wrapping span so screen readers don't read "fire fire fire" — the percentile is in the chip's `aria-label`.

## Deviations from Plan

None — plan executed exactly as written.

The only minor adjustment was during the RED-to-GREEN transition: 2/15 band-color tests initially failed under jsdom because `style.backgroundColor` normalizes `oklch(0.50 ...)` → `oklch(0.5 ...)`. This was fixed by introducing a `parseOklch()` helper inside the test file and comparing triplets numerically. The plan flagged this exact risk in its acceptance criteria ("read `getByTestId(testId).style.backgroundColor` and assert the substring `oklch` is present plus the specific token color string match (or, if jsdom strips oklch, fall back to asserting the inline style includes the exact constant value imported from `theme.ts`)") — the triplet-parse approach is a stricter fallback than the substring-match alternative, so it strengthens the test rather than weakening it.

## Issues Encountered

- **Worktree missing `node_modules`.** The agent's worktree did not have `frontend/node_modules` populated, so `npx tsc` initially failed with "This is not the tsc command you are looking for." Resolved with `npm install --no-audit --no-fund` (~5 sec to add 999 packages from lockfile). Not a Rule 1/2/3 deviation — it's a one-time worktree-setup cost.
- **No `@testing-library/jest-dom` in the project.** The project uses plain Vitest matchers (`toBe` / `toContain` / `toBeTruthy`) rather than jest-dom matchers like `toHaveTextContent`. Initial test file used `toHaveTextContent`; switched to `(textContent ?? '').toContain(...)` after grepping `package.json`. Minor red-herring; resolved before the RED commit.
- **jsdom oklch normalization.** Documented above under Decisions.

## Verification

All plan acceptance criteria green:

- `cd frontend && npx tsc --noEmit` → exits 0.
- `cd frontend && npm test -- --run PercentileChip` → 15/15 passed.
- `cd frontend && npm run lint` → exits 0.
- `cd frontend && npm test -- --run` → 626/626 passed (no regressions in the full suite).
- `cd frontend && npm run knip` → exits 0.
- `grep -c "achievable_score_gap_percentile" frontend/src/types/endgames.ts` → 1.
- `grep -c "score_gap_percentile" frontend/src/types/endgames.ts` → 2 (one on `ScoreGapMaterialResponse`, plus the `achievable_score_gap_percentile` substring match).
- `grep -c "section2_score_gap_recov_percentile" frontend/src/types/endgames.ts` → 0 (recovery exclusion verified).
- `grep -cE "section2_score_gap_conv_percentile|section2_score_gap_parity_percentile" frontend/src/types/endgames.ts` → 2.
- `grep -cE 'ZONE_DANGER|GAUGE_NEUTRAL|ZONE_SUCCESS' frontend/src/components/charts/PercentileChip.tsx` → 4 (import line + 3 derived constants).
- `grep -E 'text-xs|text-sm' frontend/src/components/charts/PercentileChip.tsx` → chip pill is `text-sm` (line 121); popover body inherits `text-xs` from the Content shell (line 150) — the documented CLAUDE.md popover exception.
- `grep -c "section2_score_gap_recov" frontend/src/components/charts/PercentileChip.tsx` → 0 (chip is metric-agnostic; recovery exclusion is at the call-site routing layer).
- Flame test at `percentile=99` asserts exactly 3 Flame icons — proves highest-tier-only dispatch (D-03).
- `formatTopXPercent` floor test at `percentile=99.9` asserts text `Top 1%` (NOT `Top 0%`) — Pitfall 7 mitigation.

## TDD Gate Compliance

Task 2 RED commit (`5bf9b219`, `test:` prefix) was followed by Task 2 GREEN commit (`6fd5ee87`, `feat:` prefix). The RED commit's tests fail (Vite "Failed to resolve import" because `PercentileChip.tsx` does not exist yet); the GREEN commit makes all 15 tests pass. No REFACTOR commit was needed — the GREEN implementation cleared the cognitive-complexity, nesting, and LOC limits on first pass.

## User Setup Required

None — pure additive frontend change, no env vars, no new packages, no DB. Wave 3 will wire the chip into the 4 row sites.

## Next Phase Readiness

- `PercentileChip` is import-ready by `EndgameOverallPerformanceSection.tsx` (Achievable Score Gap + Endgame Score Gap chips) and `EndgameMetricCard.tsx` (Parity + Conversion ΔES chips) per the locked test-id contract in 94-UI-SPEC §Data-TestID Contract.
- The 4 TS percentile fields are typed and accessible from React components as `number | null`.
- Wave 3 callers must gate on `percentile != null` before rendering the chip (matches the plan's locked component contract — no internal null-handling inside the chip).
- No backend or schema work is left for Phase 94; Phase 95 picks up the LLM-payload integration as a separate phase (LLM-05).

## Threat Flags

None — Phase 94 Wave 2 introduces no new trust boundaries. T-94-04 (XSS in popover body) is mitigated because both popover-body branches render static JSX `<p>{string-literal}</p>` with React's auto-escaping; no `dangerouslySetInnerHTML`, no user-controlled content. T-94-05 (info disclosure via aria-label) is accepted — the aria-label echoes the visible chip text. T-94-06 (theme-constant tampering) is mitigated by build-time imports from `theme.ts`; no runtime mutation. No new packages installed (T-94-SC: confirmed against `frontend/package.json` lockfile — `lucide-react`, `radix-ui`, `clsx`, `tailwind-merge` are all pre-existing dependencies).

## Self-Check: PASSED

- SUMMARY.md exists at `.planning/phases/94-backend-frontend-percentile-annotations/94-02-SUMMARY.md`.
- `frontend/src/types/endgames.ts` modified and committed (`dd64eed2`).
- `frontend/src/components/charts/PercentileChip.tsx` created and committed (`6fd5ee87`).
- `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` created and committed (`5bf9b219` RED + `6fd5ee87` GREEN refinement).
- All 3 task commits (`dd64eed2`, `5bf9b219`, `6fd5ee87`) exist on the worktree branch.

---
*Phase: 94-backend-frontend-percentile-annotations*
*Completed: 2026-05-23*
