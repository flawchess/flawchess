---
phase: 243-out-of-the-opening-worse-better-rates
plan: 05
subsystem: frontend
tags: [react, tanstack-query, openings, percentile, popover]

requires:
  - phase: 243-out-of-the-opening-worse-better-rates
    plan: 04
    provides: GET /api/openings/out-of-opening-stats (OutOfOpeningStatsResponse, server-side significant and percentile_favorable)
provides:
  - "Out of the opening" section as the first section of the Openings Stats tab (selected colour, worse primary, better lesser)
  - chart-free popover with per-TC breakdown, 95% footer and percentile-chip disclosures
  - openingsApi.getOutOfOpeningStats, useOutOfOpeningStats (tier2-gated, key ['outOfOpeningStats'])
  - import-completion and delete-all invalidation of the new key
affects: [phase 243 verification, release notes]

actuals:
  tokens: 15000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Copy lives in a non-component module (outOfOpeningCopy.ts); components import it"
    - "Popover testids are fixed literals per side (no colour or TC segment) so Umami gets one popover-open row per explanation"
    - "Endgames components (PercentileBar, RankStatusLine, rankedMetrics helpers) are reused, not forked; CdfMetricId is not widened"

key-files:
  created:
    - frontend/src/types/openingOut.ts
    - frontend/src/hooks/useOutOfOpeningStats.ts
    - frontend/src/components/openings/stats/OutOfOpeningSection.tsx
    - frontend/src/components/openings/stats/OutOfOpeningPopover.tsx
    - frontend/src/components/openings/stats/outOfOpeningCopy.ts
    - frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx
    - frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/pages/openings/StatsTab.tsx
    - frontend/src/pages/__tests__/Openings.render.test.tsx
    - frontend/src/lib/__tests__/analytics.test.ts
    - frontend/src/App.tsx
    - frontend/src/pages/Import.tsx
    - frontend/src/pages/__tests__/Import.endgameOverviewInvalidation.test.ts
    - CHANGELOG.md

key-decisions:
  - "Time controls are re-sorted bullet/blitz/rapid/classical inside the popover rather than trusting API order (a local TC_ORDER const; there is no shared export to reuse)"
  - "The five D-12/D-07 disclosures are shown on every popover (ranked or not); the averaging line is unconditional rather than gated on several ranked TCs"
  - "The eval cut '1.0' in copy is a named constant mirroring OPENING_OUT_THRESHOLD_PAWNS on the backend; the word 'pawn' appears nowhere in the new frontend files (D-03)"

requirements-completed: [D-03, D-09, D-10, D-11, D-12]

coverage:
  - id: F1
    description: "Out of the opening is the first section of the Stats tab, one card for the selected colour, worse row primary (heavier weights) and better row lesser, hints 'Fewer worse games than N% of peers' / 'More better games than N% of peers', no stacked bar"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx#renders the ranked white card with both rows, inverted hints and the bar number"
        status: pass
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx#shows the selected colour only: black is below floor while white stays ranked"
        status: pass
    human_judgment: false
  - id: F2
    description: "Red/green only when the server's significant flag is true; below-floor, pending and unranked states reuse the Endgames RankStatusLine copy; loading, error and tier2-disabled branches"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx#colours the dot only when significant"
        status: pass
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx#shows the analyzing line and keeps the query disabled while tier2 is false"
        status: pass
    human_judgment: false
  - id: F3
    description: "Popover: WHAT sentence in eval units, percentile statement in words, chance line only for out-of-range not-significant, disclosures (not FlawChess users, ranked games only, filters, rating dependence, averaging)"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx#carries the peer, ranked-games, filter, rating and averaging disclosures"
        status: pass
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx#adds the could-be-chance line only for an out-of-range, not significant percentile"
        status: pass
    human_judgment: false
  - id: F4
    description: "Per-TC list in bullet-blitz-rapid-classical order with rate/percentile/games or status; 95% footer 'k of n games · 95% CI a to b · peers typically p25 to p75', never 99%; no chart"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx#lists every time control in fastest-to-slowest order with rate, percentile and games or status"
        status: pass
      - kind: unit
        ref: "frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx#footer shows k of n games, the 95% CI and the peer range, never 99%"
        status: pass
    human_judgment: false
  - id: F5
    description: "Import completion and delete-all invalidate ['outOfOpeningStats']; popover testids map to unchanged Umami targets"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Import.endgameOverviewInvalidation.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/analytics.test.ts#popoverTargetFromTestId(out-of-opening-worse-rate)"
        status: pass
    human_judgment: false
  - id: F6
    description: "Sticky White | Black bar lines up with the 'Out of the opening' heading on desktop, worse row visually stronger than better row, no overlap at 375px"
    requirement: "D-09"
    verification:
      - kind: human
        ref: "Task 1 human-check (rendered page, dev stack with a backfilled user)"
        status: deferred
    human_judgment: true

duration: 25min
completed: 2026-10-31
status: complete
plan_head_before: 79b85b15c6dce94e89a80fc949c18fdf992294bd
plan_head_after: 5c0b0f74ffdbcc314675a277ed6e2d294519ada1
commits: 4
---

# Phase 243 Plan 05: Out-of-the-opening Stats tab section Summary

**The Openings Stats tab now opens with an "Out of the opening" card for the selected colour: the worse rate as the primary row and the better rate as the lesser row, each with an oriented percentile bar, Endgames-style below-floor/pending states, and a chart-free popover with a per-time-control breakdown and a 95% footer.**

## Accomplishments

- Tracer slice end to end: types mirroring `app/schemas/opening_out.py`, `openingsApi.getOutOfOpeningStats` (no filters by design), a tier2-gated `useOutOfOpeningStats` (5 min stale time), `OutOfOpeningSection` wired as the first child of the StatsTab column. The h2 uses `REPERTOIRE_HEADING_CLASS`, so the desktop sticky colour bar overlays it.
- Popover on `MetricInfoPopover`: WHAT sentence with "an eval 1.0 or more below (above) a typical opening position for White (Black)", bold percentile statement, five disclosures, per-TC list, hr, greyed footer with the pooled "k of n games", 95% CI and game-weighted peer band. Fixed-literal testids (`out-of-opening-worse-rate` / `-better-rate`) pinned in the analytics test.
- Import completion (App `handleJobDone`) and both Import.tsx sites (active poll, delete-all) invalidate `['outOfOpeningStats']`; a static-source test guards it. CHANGELOG `### Added` bullet under `[Unreleased]`.

## Task Commits

1. **Task 1 (tracer):** `29b6a7508` feat(243-05): out-of-the-opening card on the Openings Stats tab
2. **Task 2 RED:** `c8a354c50` test(243-05): failing popover tests (module missing)
3. **Task 2 GREEN:** `6b4c54b47` feat(243-05): popover with per-TC list, 95% footer and disclosures
4. **Task 3:** `5c0b0f74f` feat(243-05): refresh the section on import and delete-all

Tracer gate: Task 1 `<verify>` (section + Openings render tests, lint, build, knip) re-run after the commit, passed, so expansion proceeded.

## Deviations from Plan

None - plan executed as written. In-flight fixes only: a lint error in the first section test (unused mock parameter) and two comment rewordings so `grep -ci pawn` on the copy module is 0 as the acceptance criterion requires.

## Known Stubs

None.

## Threat Flags

None. T-243-14 (fixed literal popover testids, analytics test pins the mapping), T-243-15 (all values rendered as React text nodes, no `dangerouslySetInnerHTML`) and T-243-16 (key invalidated on import and delete-all) are implemented as planned.

## Verification

- Full frontend gate from `frontend/`: `npm run lint` clean, `npm run build` (tsc -b + vite) clean, `npm test -- --run` 5702 passed, `npm run knip` clean (two pre-existing configuration hints only).
- Acceptance greps: `OutOfOpeningSection` in StatsTab 2, `out-of-opening-stats` in client.ts 1, new labels in `types/endgames.ts` 0, "pawn" in the new files 0, "99%" in copy and popover 0, "95% CI" in copy 1, "not FlawChess users" 1, `['outOfOpeningStats']` invalidations: App.tsx 1, Import.tsx 2, CHANGELOG match 1.
- Not run: the Task 1 `human-check` (sticky-bar alignment and visual hierarchy on a rendered page with a backfilled dev user, desktop and 375px). Needs the owner or the phase verifier with the dev stack up.

## Rollout notes (owner-run after merge and deploy; not executed here)

1. Before deploy, on prod via flawchess-prod-db: `SELECT metric::text, count(*) FROM user_benchmark_percentiles GROUP BY 1` and the same on `benchmark_cohort_cdf`; expect only the 11 live labels.
2. Deploy with `bin/deploy.sh` (runs migration b7e4c2a9f013).
3. Seed the CDF in the container: `ssh flawchess "cd /opt/flawchess && docker compose exec backend /app/.venv/bin/python -m scripts.seed_cohort_cdf"`.
4. Backfill Stage B after the seed: `uv run python -m scripts.archive.backfill_user_percentiles --target prod --skip-anchors` (tunnel).
5. Spot-check prod user 28 on the Openings Stats tab, both colours.

## Self-Check: PASSED

- FOUND: frontend/src/types/openingOut.ts, frontend/src/hooks/useOutOfOpeningStats.ts, frontend/src/components/openings/stats/OutOfOpeningSection.tsx, OutOfOpeningPopover.tsx, outOfOpeningCopy.ts, both new test files
- FOUND commits: 29b6a7508, c8a354c50, 6b4c54b47, 5c0b0f74f
