# Phase 92: Custom date range filter - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 92-custom-date-range-filter
**Areas discussed:** Date picker component, Mobile popover behavior. LLM prompt label strategy was selected then dropped (out of scope — LLM reports are gated to no-filter only).

---

## Pre-discuss locks (from `.planning/notes/custom-date-range-filter.md`)

Carried forward without re-asking:

- UX direction = Option A: "Custom range…" as a 9th item in the existing recency Select (not a separate collapsible disclosure).
- API contract = drop the closed `Recency` string union and send two optional `from` / `to` date params; backend `WHERE played_at BETWEEN start AND end`.
- Both omitted = no date filter (no `1970-01-01` sentinel).
- Frontend computes preset → dates locally in user's local timezone; memoize on today's date string.
- Side-by-side "before vs after" comparison is deferred.

The pending todo `2026-05-02-remove-recency-from-bookmark-timeseries.md` was folded into Phase 92 scope as pre-work (Decision D-19).

---

## Date picker component

| Option | Description | Selected |
|--------|-------------|----------|
| Native `<input type="date">` | Zero deps, ~0 KB. Native OS pickers on iOS/Android. Limited Tailwind theming. Recommended in the question. | |
| shadcn Calendar + Popover | `npx shadcn add calendar` → react-day-picker (~25 KB gz) + date-fns (~15 KB gz). Matches the rest of the UI, range mode with highlighted span. | ✓ |
| Two text inputs with ISO parsing | Plain `YYYY-MM-DD` text inputs. Zero deps, worst UX. | |

**User's choice:** Free-text — "We're not on iOS/Android. How about the shadcn date range picker, seems pretty good: https://ui.shadcn.com/docs/components/radix/date-picker". Locks the shadcn pattern over the native fallback I recommended.

**Notes:** Confirmed against the canonical shadcn docs via WebFetch: `Popover` → `Button` trigger → `Calendar mode="range"` with `selected={DateRange}` / `onSelect`. Dependencies: `react-day-picker` + `date-fns`. ~40 KB gz total for the power-user feature.

---

## Trigger pattern (sub-question of Date picker component)

| Option | Description | Selected |
|--------|-------------|----------|
| Two-step: Select item opens a separate popover | Picking "Custom range…" closes the Select and programmatically opens a separate Popover anchored to the same trigger. Matches the notes file. Recommended. | ✓ |
| Replace Select with a single combined popover | Drop the Select entirely; one popover containing both preset list and calendar (Google Analytics / Stripe style). Deviates from the notes file. | |
| Select item with inline calendar swap | Calendar replaces the preset list inside the Select content (no second popover). Uncertain Radix Select support. | |

**User's choice:** Two-step pattern (recommended).

**Notes:** Popover auto-closes when both `from` and `to` are picked (desktop). No explicit Apply/Cancel button on desktop.

---

## Mobile popover behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Nested Vaul bottom sheet over the filter drawer | Second Vaul drawer with a single-month range Calendar. Matches existing mobile pattern. Recommended. | ✓ |
| Inline expansion inside the filter drawer | Calendar appears below the Select row, pushing other rows down. Tall, risks awkward scrolling. | |
| Same Radix Popover as desktop | Radix portals to body, floats over the drawer. Awkward shape the notes already flagged. | |

**User's choice:** Nested Vaul bottom sheet (recommended).

**Notes:** Mobile sheet keeps explicit "Apply" CTA (D-07) — unlike desktop's auto-close on full range pick. Backdrop dismiss = Cancel (no range applied).

---

## LLM prompt label strategy (dropped from scope)

Originally selected by the user during area selection but immediately dropped after my scout:

> "LLM Reports can't be generated when recency and other filters are used. skip"

Confirmed via `app/services/insights_service.py:133-164`: the LLM service explicitly sets `recency=None` / `recency="3months"` per fixed window, independent of `filter_context.recency`. The user-facing report endpoint is gated so dashboard filters do not feed the LLM prompt. Switching the dashboard filter from `recency` to `from_date` / `to_date` has no effect on prompt content. Captured as D-18 (out of scope) and as a deferred idea if the gating relaxes in a future phase.

---

## Claude's Discretion

- Calendar layout on desktop popover (one-month vs two-month side-by-side). Two-month is shadcn default. Planner picks based on popover width.
- Trigger label format when only `from` is set ("From Mar 1, 2026…" vs other wording).
- TanStack Query cache invalidation on deploy. Existing `recency`-keyed entries naturally miss when keys switch to `from_date`/`to_date`. Planner audits for localStorage-persisted filter state.
- Whether the frontend filter store represents custom range as an adjacent `customRange` field or as a discriminated union under `filters.recency`. Planner chooses based on existing store shape.

## Deferred Ideas

- Side-by-side "before vs after" period comparison (carried over from notes file).
- Quick-shortcut buttons inside the custom popover ("last 30 days", "this year") — preset dropdown already covers common cases.
- LLM prompt label strategy if/when the no-filter gate on insight reports is relaxed.
