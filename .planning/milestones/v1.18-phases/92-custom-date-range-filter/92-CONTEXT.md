# Phase 92: Custom date range filter — Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a "Custom range…" 9th item to the existing recency Select in `FilterPanel.tsx` that opens a date-range Calendar in a popover (desktop) / nested Vaul bottom sheet (mobile), and replace the closed `Recency` string union on the API wire with two optional `from`/`to` date params. The backend collapses to a single `WHERE played_at BETWEEN start AND end` shape — no preset translation logic on the server. Frontend owns "now" and converts preset labels to dates in the user's local timezone, memoized to today's date string so TanStack Query keys don't churn per render.

Includes the pre-work to drop `recency` from the bookmark time-series request (`TimeSeriesRequest` + the matching field in `app/schemas/openings.py` ~line 181), which has its own pending todo and must land before the date-range refactor to avoid extending the bookmark time-series endpoint to `from`/`to` for no reason.

</domain>

<decisions>
## Implementation Decisions

### Date input component
- **D-01:** Use the shadcn date range picker pattern — `Calendar` component (`npx shadcn add calendar`) in `mode="range"` with `selected={DateRange}` / `onSelect`. Pulls in `react-day-picker` (~25 KB gz) and `date-fns` (~15 KB gz) as new frontend dependencies. Confirmed against https://ui.shadcn.com/docs/components/radix/date-picker.
- **D-02:** No native `<input type="date">` fallback. Range mode + highlighted-span UX is worth the ~40 KB gz dependency cost for this power-user feature, and consistent styling matters more than native pickers.

### Dropdown ↔ popover integration
- **D-03:** Two-step trigger pattern. The existing Select stays put with a 9th item labeled "Custom range…" at the bottom. When `onValueChange === 'custom'`, the Select closes and a separate Radix `Popover` opens, anchored to the same trigger element. Popover content is the range Calendar. Picking any non-custom preset clears the custom range and reverts the trigger label.
- **D-04:** Trigger label rendering. Once both `from` and `to` are set, the Select trigger displays the resolved range (e.g., `"Mar 1 – Apr 1, 2026"`). Use `date-fns` `format` with a compact format. While the popover is open with only `from` set, the trigger may show `"From Mar 1, 2026…"` placeholder. Final wording TBD by planner.
- **D-05:** Popover auto-close behavior. Close automatically when both `from` and `to` are picked. No explicit Apply/Cancel button in the desktop popover — the Calendar handles range commit internally via `onSelect`.

### Mobile UX
- **D-06:** On mobile (`useBreakpoint('md')` or whatever the existing FilterPanel uses), render the custom-range Calendar inside a nested Vaul `Drawer` (bottom sheet) layered over the FilterPanel drawer. Vaul is already a project dependency (`"vaul": "^1.1.2"`). Single-month Calendar (not two-month side-by-side) to fit the sheet height.
- **D-07:** Mobile sheet needs an explicit "Apply" CTA button. Unlike the desktop popover (auto-closes on full range pick), the mobile sheet keeps the user in control of when to dismiss — tap Apply, sheet closes, FilterPanel drawer is still open with the resolved range showing in the Select trigger.
- **D-08:** Backdrop dismiss is allowed on the mobile sheet but treated as Cancel (no range applied).

### API contract & types
- **D-09:** Wire param names: `from_date` and `to_date` (snake_case, ISO `YYYY-MM-DD` strings on the wire, parsed as `date.date` on the backend via FastAPI's Pydantic coercion). Reason: `from` is a Python reserved keyword and using it as a query param name forces `Query(..., alias="from")` workarounds; `from_date` is project-idiomatic with `played_at`-style naming elsewhere. Planner may revisit if a strong reason emerges.
- **D-10:** Both omitted = no date filter (no `1970-01-01` / `9999-12-31` sentinels). Apply `WHERE played_at >= :from_date` only when `from_date` is set, and `WHERE played_at < :to_date + interval '1 day'` only when `to_date` is set, so semantics are "from start-of-day-from to end-of-day-to" without timezone math on the server.
- **D-11:** `Recency` type rename. Rename `Recency` in `frontend/src/types/api.ts:38` to `RecencyPreset` and keep in the same file. It no longer crosses the API boundary, so a `// UI-only preset, not sent to the API` comment goes on the declaration. Don't move it into FilterPanel-local types — `useStats`, `useEndgames`, etc. still need to know the preset → dates conversion lives somewhere shared.
- **D-12:** Preset → date conversion lives in one shared utility, e.g. `frontend/src/lib/recency.ts`, exporting `presetToDates(preset: RecencyPreset, now?: Date): { from?: Date; to?: Date }`. Memoize callsite results on `(preset, today-as-YYYY-MM-DD)` so TanStack Query keys stay stable within a calendar day. Round `from` to `00:00` local, `to` to `23:59:59` local before sending.

### Hook + URL param migration
- **D-13:** All six recency-consuming hooks (`useOpenings`, `useEndgames`, `useEndgameInsights`, `useOpeningInsights`, `useStats`, `useNextMoves`) switch from passing `recency` to passing `from_date` / `to_date`. The shared `apply_game_filters()` in `app/repositories/query_utils.py` is the single source of truth for the SQL `BETWEEN` predicate.
- **D-14:** Any URL params currently exposing `recency` (e.g. shareable filter URLs) switch to `from_date` / `to_date`. ISO date strings, slightly uglier in the URL but consistent with the API. Planner audits the router to find every consumer.

### Validation & edge cases
- **D-15:** Validation. Backend: if `from_date > to_date`, return 422. Frontend: disable the Apply button (mobile) / refuse to close the popover (desktop) until `from ≤ to`. Calendar in range mode naturally prevents this by the order of clicks, but URL params still need server-side validation.
- **D-16:** Future dates allowed (chess games can have a future scheduled date if PGN headers are weird, and we don't want to special-case). Very-old dates allowed (some users have games back to 2010).
- **D-17:** "Only one bound set" is allowed and meaningful — `from_date` only = "everything since X", `to_date` only = "everything before Y". Frontend Custom popover should support this (e.g. clearing one input), though the default UX hands the user a `from → to` flow.

### LLM insight prompt impact
- **D-18:** Out of scope. LLM endgame/opening insight reports are currently gated to no-filter (recency cannot be applied when generating reports), so changing the dashboard recency filter to `from_date` / `to_date` does not affect prompt content. The prompt's `last_3mo` / `all_time` window structure is independent of dashboard filters (set explicitly in `insights_service.py` lines 153 / 164). If the gating relaxes in a future phase, prompt label strategy becomes a new decision then.

### Bookmark time-series cleanup (folded pre-work)
- **D-19:** Drop `recency` from `TimeSeriesRequest` (`frontend/src/types/position_bookmarks.ts:52`), the matching field in the time-series request schema in `app/schemas/openings.py` (~line 181 — only the time-series one of the three `recency` declarations in that file), and any time-series service / repository call site. Verify no UI surface exposes recency on the bookmark time-series chart — it's been an unused param. Land this first so the date-range refactor doesn't accidentally extend `from`/`to` into a request shape that shouldn't filter at all.

### Claude's Discretion
- Calendar layout on desktop popover (one-month vs two-month side-by-side). Two-month is the shadcn default and matches Stripe/Google Analytics conventions; planner picks based on popover width budget.
- Trigger label format when only `from` is set ("From Mar 1, 2026…" vs "Mar 1, 2026 – ?").
- TanStack Query cache invalidation on deploy. Existing cache entries keyed by `recency` will simply not match new `from_date`/`to_date` keys — natural cache miss + refetch, no explicit invalidation needed unless a localStorage filter persistence layer exists (planner audits `filterStore` or equivalent).

### Folded Todos
- `2026-05-02-remove-recency-from-bookmark-timeseries.md` — folded as D-19. Pre-work for the date-range refactor, must land first to avoid extending `from`/`to` to a request shape that shouldn't filter at all.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design notes
- `.planning/notes/custom-date-range-filter.md` — full pre-discuss design notes covering UX direction (Option A 9th dropdown item), API contract (drop closed union for `from`/`to` dates), implementation gotchas (timezone canonicalization, "all time" = omit both, LLM prompt regression risk), and the related cleanup todo. Locks: 95% preset UX unchanged, single API shape, frontend owns "now".

### Folded pre-work
- `.planning/todos/pending/2026-05-02-remove-recency-from-bookmark-timeseries.md` — bookmark time-series recency removal that must land first (folded into scope as D-19).

### External docs
- https://ui.shadcn.com/docs/components/radix/date-picker — canonical date range picker pattern. Calendar `mode="range"` + Popover + Button trigger. Already confirmed via WebFetch during discuss; pulls in `react-day-picker` + `date-fns`.

### Project conventions
- `CLAUDE.md §Shared Query Filters` — `apply_game_filters()` in `app/repositories/query_utils.py` is the single shared filter implementation. All consumers inherit the wire-shape change for free. Do not duplicate filter logic in individual repositories.
- `CLAUDE.md §Database Design Rules` — use appropriate column types. `played_at` is already a TIMESTAMPTZ; no schema change needed for this phase.
- `CLAUDE.md §Frontend` — minimum font size `text-sm` (existing FilterPanel "Recency" header is `text-xs`, predates the rule; do not regress it but also do not propagate `text-xs` into new Custom Range UI text); `data-testid` on every interactive element (Calendar day buttons, popover, Apply CTA); applies to both desktop and mobile.

### Affected code (verified during scout)
- `frontend/src/types/api.ts:38` — `Recency` closed union. Rename to `RecencyPreset` per D-11.
- `frontend/src/components/filters/FilterPanel.tsx:173-195` — existing recency Select. Add 9th item + wire up popover/sheet trigger.
- `app/repositories/query_utils.py::apply_game_filters()` — single source of truth for `played_at` predicate. Replace recency-cutoff logic with `from_date` / `to_date` BETWEEN.
- `app/schemas/openings.py` ~line 181 — three `recency` declarations; the time-series one is removed in D-19, the other two switch to `from_date` / `to_date`.
- Hooks consuming recency: `useOpenings`, `useEndgames`, `useEndgameInsights`, `useOpeningInsights`, `useStats`, `useNextMoves`.
- `app/services/insights_service.py:153,164` — LLM service sets `recency=None` / `recency="3months"` explicitly per-window, independent of `filter_context.recency`. Switch these internal callsites to `from_date` / `to_date` derived from the same fixed windows (now − 90 days for `last_3mo`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `radix-ui` (already a dep): `Popover` for the desktop trigger; project also has a thin `info-popover.tsx` wrapper.
- `vaul` (already a dep): nested `Drawer` for the mobile bottom sheet.
- `lucide-react` (already a dep): `Calendar` icon for the trigger or Apply CTA.
- `app/repositories/query_utils.py::apply_game_filters()` — single shared filter function. The whole point of this phase's API change is that the new shape lands here once and ripples to every consumer.
- `frontend/src/components/ui/select.tsx` — existing Select wrapper; the 9th item just adds a `SelectItem value="custom"`.

### Established Patterns
- Mobile-first PWA with separate desktop / mobile layouts in FilterPanel. Per CLAUDE.md, when modifying components with separate sections, apply the change to both — for this phase the change IS the two-layout split (popover vs sheet), so it's already accounted for.
- Frontend timezone handling: FlawChess already uses user-local dates for chart axes; treat the custom range as user-local-day-bounded and never UTC.
- `text-sm` minimum (with documented exceptions for hover/tap-activated info tooltips); custom range trigger label and Calendar day labels stay ≥ `text-sm`.

### Integration Points
- Backend wire-format change in `apply_game_filters()` is the central seam. Once that accepts `from_date` / `to_date`, every consumer's request schema updates and the hooks pass the new params.
- Frontend filter store (whatever holds `filters.recency`) gains a `customRange: { from?: Date; to?: Date } | null` adjacent field, OR `filters.recency` becomes a discriminated union of `RecencyPreset | { kind: 'custom'; from?: Date; to?: Date }`. Planner chooses based on existing store shape.
- TanStack Query keys: existing keys including `recency` change to include `from_date`/`to_date`. Old cache entries will naturally miss; no explicit invalidation unless filters persist to localStorage (planner audits).

</code_context>

<specifics>
## Specific Ideas

- shadcn date range picker pattern explicitly cited by the user: https://ui.shadcn.com/docs/components/radix/date-picker.
- Two-step Select → separate Popover (not single combined popover, not inline calendar swap) — keeps the 95% preset case visually unchanged, matches the notes file's locked Option A.
- Nested Vaul bottom sheet on mobile — explicitly chosen over inline expansion or Radix popover-on-drawer.

</specifics>

<deferred>
## Deferred Ideas

- **Side-by-side "before vs after" period comparison** — captured in the notes file as out of scope; revisit if users start asking for "compare last 3 months vs prior 3 months" style analyses.
- **Quick-shortcut buttons inside the custom popover** ("last 30 days", "this year") — the 8 dropdown presets already cover the common cases; the popover is for arbitrary windows only.
- **LLM prompt label strategy** if/when the no-filter gate on insight reports is relaxed — at that point, decide between human label ("past month") derived from span vs absolute dates ("Mar 1 – Apr 1, 2026") vs dropping time framing from the prompt entirely.

</deferred>

---

*Phase: 92-custom-date-range-filter*
*Context gathered: 2026-05-21*
