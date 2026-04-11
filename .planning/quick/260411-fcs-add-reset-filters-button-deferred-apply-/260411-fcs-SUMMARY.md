---
quick_id: 260411-fcs
plan: 01
date: 2026-04-11
status: complete
---

# Quick Task 260411-fcs — Summary

**Objective:** Add a Reset Filters button (full panel width) at the bottom of the shared FilterPanel, a "Filter changes apply on closing the filters panel" helper text on deferred-apply instances, and a "modified" indicator dot on the sidebar/mobile filter trigger buttons that pulses once when a deferred commit actually fires.

## Files Modified

- `frontend/src/components/filters/FilterPanel.tsx`
- `frontend/src/lib/theme.ts`
- `frontend/src/pages/Endgames.tsx`
- `frontend/src/pages/Openings.tsx`
- `frontend/src/pages/GlobalStats.tsx`

## Commits

| Hash | Message |
|------|---------|
| `51b5eae` | feat(260411-fcs-01): add Reset button, deferred-apply hint, areFiltersEqual helper to FilterPanel |
| `1af1a68` | feat(260411-fcs-01): wire Endgames page with modified dot + deferred-apply hint |
| `c106fc9` | feat(260411-fcs-01): wire Openings + GlobalStats with modified dot + drawer pulse |

## Key Changes

### Task 1 — FilterPanel + theme
- Added `areFiltersEqual(a, b, fields?)` helper (set-equal on array fields, optional key subset for page-scoped comparison).
- New props: `showDeferredApplyHint?: boolean`, `onReset?: () => void` (escape hatch only — no current consumer uses it).
- Full-width Reset button (`data-testid="btn-reset-filters"`, outline variant) below the last filter section.
- Panel-scoped default `onClick`: resets only the fields listed in `visibleFilters`, preserves all other filter store keys — this is the single source of truth for Reset semantics across all pages.
- Muted helper line `"Filter changes apply on closing the filters panel."` rendered below Reset only when `showDeferredApplyHint` is true.
- `theme.ts` gained `FILTER_MODIFIED_DOT` constant (oklch brand-brown mid).

### Task 2 — Endgames
- `isModified` computed via `areFiltersEqual(appliedFilters, DEFAULT_FILTERS)` — tracks APPLIED, not pending, so the dot describes the state of the query actually firing.
- One-shot pulse (`isPulsing`) gated by `prevAppliedRef` — fires only on real commits (skips initial mount and no-op updates), auto-clears after ~1s via `setTimeout`.
- `bg-brand-brown` modified dot on desktop sidebar strip button (via `SidebarPanelConfig.notificationDot`) and mobile `btn-open-filter-drawer`.
- Both FilterPanel instances (sidebar + drawer) pass `showDeferredApplyHint`.
- Panel-scoped Reset — no `onReset` override. Color/matchSide (not rendered on Endgames) are preserved across Reset.

### Task 3 — Openings + GlobalStats
- **Openings**: `isFiltersModified` on shared `filters`; dot composes with existing onboarding hint (hint takes precedence). Mobile drawer pulse gated via `justCommittedFromDrawerRef` flag set inside `handleFilterSidebarOpenChange` only when `localFilters !== filters` at close time. Desktop does NOT pulse (live apply — pulsing every toggle would be noisy). Mobile drawer FilterPanel passes `showDeferredApplyHint`; desktop does not.
- **GlobalStats**: `isGlobalStatsFiltersModified` restricted to `['platforms', 'recency']` via `areFiltersEqual`'s `fields` param (no cross-page color/matchSide contamination). Non-pulsing dot on both desktop + mobile filter triggers. No `showDeferredApplyHint` anywhere (immediate apply).
- Panel-scoped Reset on both pages — no `onReset` overrides.

## Reset Semantics (Panel-Scoped — No Cross-Page Side Effects)

Reset clicked inside any FilterPanel instance restores ONLY the fields that panel renders (per `visibleFilters`). Fields the panel doesn't render are never touched. This means:

- **Endgames Reset** → preserves Openings' color / matchSide (the Endgames panel doesn't render them).
- **Openings desktop Reset** → preserves the "Played as" / "Piece filter" ToggleGroups (those live outside FilterPanel in `desktopFilterPanelContent`).
- **GlobalStats Reset** → clears platforms + recency only; preserves color / matchSide / timeControls / etc.

Verification step 21 enforced this with a grep check — zero `onReset=` overrides exist on any `<FilterPanel>` instance in the three page files.

## Color Token

`bg-brand-brown` is a registered Tailwind v4 color (defined in `frontend/src/index.css` as `--color-brand-brown: var(--brand-brown)` → `#8B5E3C`). No fallback needed. Same token used consistently across Tasks 2 and 3 dot spans. `FILTER_MODIFIED_DOT` constant added to `theme.ts` for any future JS-side usage.

## Verification

| Check | Result |
|-------|--------|
| `npm run lint` | PASS |
| `npx tsc --noEmit` | PASS |
| `npm run knip` | PASS (no dead exports; `areFiltersEqual` consumed by 3 pages) |
| `npm run build` | PASS (vite + PWA + prerender) |
| `npm test` | PASS (73/73) |

## Deviations

None. The plan anticipated a possible Tailwind fallback for `bg-brand-brown`; verification confirmed the token is registered, so no fallback was used.

## Next Steps (Manual UAT)

Per plan's verification checklist — run `npm run dev` and exercise:
1. Openings desktop — change filter, confirm dot appears live, no pulse. Reset preserves Played-as.
2. Openings mobile drawer — change filter, close drawer, confirm pulse fires once.
3. Endgames — change filter in panel, close, confirm dot + pulse fire on commit (not on pending edit). Confirm hint text is visible inside the panel.
4. GlobalStats — change platform/recency, confirm dot appears live, no hint, no pulse. Navigate to Openings and verify color/matchSide preserved.
5. Cross-check: onboarding "filters hint" ping still takes visual precedence on Openings when active.
