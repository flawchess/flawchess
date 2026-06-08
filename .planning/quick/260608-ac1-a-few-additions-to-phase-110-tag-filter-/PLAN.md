---
quick_id: 260608-ac1
slug: a-few-additions-to-phase-110-tag-filter-
status: in-progress
date: 2026-06-08
---

# Quick Task 260608-ac1: Phase 110 follow-up — tag chip + eval-chart refinements

Five small frontend additions to the Library Games card (Phase 110). All changes are
frontend-only (`frontend/src`). No backend/API changes — all required data
(`flaw_markers` with per-ply `severity`/`tags`/`is_user`) already exists on `GameFlawCard`.

## Scope (the 5 requested items)

1. **Active-filter ring on Blunder/Mistake severity badges** — apply the same active-filter
   highlight TagChip already has (`ACTIVE_FILTER_RING_CLASS`) to `SeverityBadge`.
2. **Occurrence count on tag chips** — show how many times each tag occurred in the game
   (count-first, like "3 Blunders"), in the Games card only.
3. **Smaller tag chips** — drop tag-chip text one level (`text-sm` → `text-xs`); leave
   `SeverityBadge` (Blunders/Mistakes/Inaccuracies) unchanged.
4. **Rename "Inacc." → "Inaccuracies"** in `SeverityBadge`.
5. **Hover-to-highlight eval-chart markers** — hovering a tag chip OR a Blunder/Mistake
   severity badge in the Games card highlights the matching M/B markers on that card's
   eval chart (dims the rest).

## Decisions

- **D1 (req 1 ring semantics):** Severity default is both M+B selected, so ring only when the
  severity filter is *narrowed to exactly one* (`filter.severity.length === 1 && includes(sev)`).
  Inaccuracy badge never rings (inaccuracy isn't a filterable severity). Ring color = `SEV_COLORS[severity]`.
- **D2 (user-only scope):** `chips`/`severity_counts` are user-only. Scope BOTH the tag count
  (req 2) and the hover-highlight ply set (req 5) to `is_user` markers so the highlighted-dot
  count matches the chip/badge count exactly.
- **D3 (req 3 deviates from CLAUDE.md):** `text-sm` is the documented floor; this intentionally
  uses `text-xs` for tag chips per explicit user request. Flagged in SUMMARY. Not CI-enforced.
- **D4 (req 4 layout):** "Inaccuracies" is much wider than "Inacc."; the desktop severity row
  is `flex-nowrap` in a 1/3-width grid column and will overflow. Switch that row to `flex-wrap`
  so it wraps gracefully instead of clipping.
- **D5 (req 5 emphasis):** highlighted markers get a larger radius + full opacity; non-matching
  markers dim to low opacity. Highlight is transient hover state owned by `LibraryGameCard`,
  passed to `EvalChart` as an optional `highlightedPlies` set (null = normal render). Empty set
  is treated as no-op (never dim everything).

## Tasks

### T1 — SeverityBadge: ring + "Inaccuracies" + optional hover callback
File: `frontend/src/components/library/SeverityBadge.tsx`
- Rename label `inaccuracy: 'Inacc.'` → `'Inaccuracies'`.
- Subscribe to `useFlawFilterStore`; `isActive = (sev==='blunder'||sev==='mistake') && filter.severity.length===1 && filter.severity.includes(sev)`. Apply `ACTIVE_FILTER_RING_CLASS` + `--tw-ring-color: SEV_COLORS[sev]`.
- Add optional `onHover?: (active: boolean) => void`; wire `onMouseEnter/onMouseLeave` (and `onFocus/onBlur` for a11y). Keep stateless otherwise.

### T2 — TagChip: count + smaller font + optional hover callback
File: `frontend/src/components/library/TagChip.tsx`
- Add optional `count?: number`; render count-first before the icon when `count != null && count > 0`.
- Container text `text-sm` → `text-xs`.
- Add optional `onHover?: (active: boolean) => void`; fire alongside the existing popover hover handlers (don't break the definition popover).

### T3 — LibraryGameCard: wire counts + hover highlight
File: `frontend/src/components/results/LibraryGameCard.tsx`
- Memoize `tagCounts: Map<FlawTag, number>` from `is_user` M/B `flaw_markers`.
- `highlight` state: `{kind:'tag', tag} | {kind:'severity', severity} | null`.
- Memoize `highlightedPlies: Set<number> | null` from `highlight` + `is_user` markers (skip inaccuracy).
- Pass `count` + `onHover` to each `TagChip`; pass `onHover` to Blunder/Mistake `SeverityBadge` only.
- Pass `highlightedPlies` to both (desktop + mobile) `EvalChart` instances.
- Switch the severity row from `flex-nowrap` → `flex-wrap` (D4).

### T4 — EvalChart: render highlight
File: `frontend/src/components/library/EvalChart.tsx`
- Add optional prop `highlightedPlies?: ReadonlySet<number> | null`.
- `flawDotElement`: add `opacity` param (default 1).
- `buildDotRenderer(markerMap, highlightedPlies)`: when active (`size>0`), emphasized ply → larger radius + opacity 1; others → opacity dimmed. Inactive → unchanged.

### T5 — Tests + gates
- Update/extend tests: `TagChip.test.tsx` (count render, text-xs), `SeverityBadge` (label + ring), any LibraryGameCard/EvalChart tests touching markers.
- Gates: `npm run lint`, `npm test -- --run`, `npm run knip`, build typecheck.

## Verification
- Visual: counts on chips, smaller chips, "Inaccuracies" label, ring when narrowing severity, hover dims/highlights correct dots.
- Highlighted dot count == chip/badge count (D2 coherence check).
- FlawsTab still renders (optional props omitted there).
