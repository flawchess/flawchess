# Phase 92: Custom date range filter — Research

**Researched:** 2026-05-21
**Domain:** Frontend (React 19 + shadcn Calendar + Vaul nested drawer) + Backend (FastAPI/Pydantic schema rename + SQL predicate change)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Use the shadcn date range picker pattern — `Calendar` component (`npx shadcn add calendar`) in `mode="range"` with `selected={DateRange}` / `onSelect`. Pulls in `react-day-picker` (~25 KB gz) and `date-fns` (~15 KB gz) as new frontend dependencies. Confirmed against https://ui.shadcn.com/docs/components/radix/date-picker.

**D-02:** No native `<input type="date">` fallback. Range mode + highlighted-span UX is worth the ~40 KB gz dependency cost for this power-user feature, and consistent styling matters more than native pickers.

**D-03:** Two-step trigger pattern. The existing Select stays put with a 9th item labeled "Custom range…" at the bottom. When `onValueChange === 'custom'`, the Select closes and a separate Radix `Popover` opens, anchored to the same trigger element. Popover content is the range Calendar. Picking any non-custom preset clears the custom range and reverts the trigger label.

**D-04:** Trigger label rendering. Once both `from` and `to` are set, the Select trigger displays the resolved range (e.g., `"Mar 1 – Apr 1, 2026"`). Use `date-fns` `format` with a compact format. While the popover is open with only `from` set, the trigger may show `"From Mar 1, 2026…"` placeholder. Final wording TBD by planner.

**D-05:** Popover auto-close behavior. Close automatically when both `from` and `to` are picked. No explicit Apply/Cancel button in the desktop popover.

**D-06:** Mobile = nested Vaul `Drawer` (bottom sheet) layered over the FilterPanel drawer. Single-month Calendar to fit sheet height.

**D-07:** Mobile sheet needs explicit "Apply" CTA button.

**D-08:** Mobile backdrop dismiss = Cancel (no range applied).

**D-09:** Wire param names: `from_date` and `to_date` (snake_case, ISO `YYYY-MM-DD` strings, parsed as `date.date`). `from` is reserved in Python.

**D-10:** Both omitted = no date filter. Apply `WHERE played_at >= :from_date` only when `from_date` is set, and `WHERE played_at < :to_date + interval '1 day'` only when `to_date` is set.

**D-11:** Rename `Recency` in `frontend/src/types/api.ts:38` to `RecencyPreset`. UI-only type with a comment.

**D-12:** Preset → date conversion lives in one shared utility, e.g. `frontend/src/lib/recency.ts`, exporting `presetToDates(preset: RecencyPreset, now?: Date): { from?: Date; to?: Date }`. Memoize on `(preset, today-as-YYYY-MM-DD)`. Round `from` to `00:00` local, `to` to `23:59:59` local.

**D-13:** All six recency-consuming hooks (`useOpenings`, `useEndgames`, `useEndgameInsights`, `useOpeningInsights`, `useStats`, `useNextMoves`) switch to `from_date` / `to_date`. `apply_game_filters()` is single source of truth.

**D-14:** Any URL params currently exposing `recency` switch to `from_date` / `to_date`.

**D-15:** Validation. Backend: if `from_date > to_date`, return 422. Frontend: disable Apply / refuse to close until `from ≤ to`.

**D-16:** Future dates allowed. Very-old dates allowed.

**D-17:** Only-one-bound is allowed and meaningful.

**D-18:** LLM insight prompt scope = OUT. Reports are gated to no-filter; dashboard filter doesn't reach prompt content. Switch internal `insights_service.py:153,164` callsites to `from_date`/`to_date` derived from the fixed `now − 90 days` window.

**D-19:** Drop `recency` from `TimeSeriesRequest` (`frontend/src/types/position_bookmarks.ts:52`), the matching field in `app/schemas/openings.py:153` (time-series request only), and any time-series service/repo callsite. Pre-work, must land first.

### Claude's Discretion

- Calendar layout on desktop popover (one-month vs two-month side-by-side). Two-month is shadcn default. Planner picks based on popover width budget.
- Trigger label format when only `from` is set ("From Mar 1, 2026…" vs "Mar 1, 2026 – ?").
- TanStack Query cache invalidation on deploy. Natural cache miss + refetch — no explicit invalidation unless localStorage filter persistence exists (verified: it doesn't — see §Frontend State Architecture).
- Whether the frontend filter store represents custom range as an adjacent `customRange` field or as a discriminated union under `filters.recency`. Planner chooses based on existing store shape (researched below — recommendation: sibling field).

### Deferred Ideas (OUT OF SCOPE)

- Side-by-side "before vs after" period comparison.
- Quick-shortcut buttons inside the custom popover ("last 30 days", "this year").
- LLM prompt label strategy (revisit if/when the no-filter gate on insight reports is relaxed).
</user_constraints>

<phase_requirements>
## Phase Requirements

No formal `REQ-XX` IDs were defined. Coverage is derived from CONTEXT.md decisions D-01..D-19 and the 7 ROADMAP scope-in items. The planner should use the decision numbers as the requirement keys for the Plan→Requirement mapping.

| Decision | Description | Research Support |
|----------|-------------|------------------|
| D-01/D-02 | Install shadcn Calendar + react-day-picker + date-fns | §Standard Stack confirms registry entry, versions, and verified install command |
| D-03/D-05 | Two-step Select → Popover anchored to same trigger; auto-close on full range | §Architecture Patterns → Pattern 1 confirms Radix Popover `<PopoverAnchor>` is the correct primitive |
| D-06/D-07/D-08 | Nested Vaul drawer on mobile, Apply CTA, backdrop = cancel | §Architecture Patterns → Pattern 2 confirms `Drawer.NestedRoot` exists in vaul 1.1.x and is the documented API |
| D-09/D-10 | Wire `from_date`/`to_date`; predicate semantics | §Backend Wire-Format Change documents the exact `apply_game_filters()` signature change |
| D-11 | Rename `Recency` → `RecencyPreset` | §Recency Call-Site Audit lists every TypeScript site that imports `Recency` |
| D-12 | Shared `presetToDates` utility, memoized on today | §Code Examples → `presetToDates` reference implementation |
| D-13 | Six hooks migrate to `from_date`/`to_date` | §Recency Call-Site Audit → Hooks table, §TanStack Query Key Audit |
| D-14 | URL param migration | §Frontend State Architecture confirms there is NO URL param exposure of `recency` today — D-14 is a no-op (still document the audit) |
| D-15 | 422 on `from_date > to_date` | §Validation Pattern — Pydantic v2 `@model_validator(mode='after')` is project-idiomatic |
| D-18 | LLM internal callsite switch | §Backend Wire-Format Change → `insights_service.py` shows the existing window structure that produces `from_date = now - timedelta(days=90)` |
| D-19 | Drop bookmark time-series recency | §Bookmark Time-Series Pre-Work documents the exact line numbers and the three-of-three audit (only the time-series declaration is removed) |
| ROADMAP-3 | Frontend timezone canonicalization | §Pitfall 1 + §Code Examples → `presetToDates` |
</phase_requirements>

## Summary

This phase replaces a closed `Recency` string union (`week`/`month`/`3months`/`6months`/`year`/`3years`/`5years`/`all`) with two optional ISO date params `from_date` / `to_date` across one backend filter helper (`apply_game_filters`), three Pydantic request schemas, six FE hooks, and one filter UI component. The Calendar UI is a routine shadcn install. The work is shape-of-the-code refactoring with a high ty/ruff blast radius — every `recency_cutoff: datetime | None` keyword arg in 4 repositories and 4 services needs to become two parameters, and every test fixture passes one of them.

The five real risks beyond mechanical rename are: (1) **`insights.py` router uses recency as a gating signal** — `_validate_full_history_filters` blocks the LLM endpoint when `recency != "all_time"`; the equivalent gate for `from_date`/`to_date` is "both omitted" but `FilterContext` itself becomes a different shape; (2) **`FilterContext` in `app/schemas/insights.py:133` is a SEPARATE Literal union** from the `openings.py` ones (uses `"all_time"` not `"all"`); (3) **`app/schemas/stats.py:133` types `recency: str | None`** (not the Literal — looser), and a separate router-level Query param at `app/routers/stats.py:27,52,77` does the same; (4) **the bookmark phase-entry endpoint at `/stats/bookmark-phase-entry-metrics` still accepts `recency` in the request body**, and its FE hook `useBookmarkPhaseEntryMetrics` passes it through — not enumerated in the CONTEXT-listed "six hooks" but is also a consumer; (5) **`recency` appears in 23 backend files and 21 frontend files** — many are test fixtures or service callsites passing the value through, but the ty compiler will surface them all in a single wave.

**Primary recommendation:** Land Wave 0 (D-19 bookmark time-series cleanup) first as a tiny independent change; then a single backend wave that flips `apply_game_filters()` + all 3+1 request schemas + all 4 repository signatures + all 4 services + insights router gating + all backend tests atomically (one PR — ty failures cascade and there is no useful intermediate state); then a frontend wave with the same atomic property (api/client.ts + 6 hooks + FilterPanel UI + shared `recency.ts` utility). The "Calendar component install" is a stand-alone preparatory task that can run in parallel with the backend wave.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Preset label → from/to dates conversion | Browser (FE) | — | D-12 lock: frontend owns "now" + user's local TZ. Backend never sees preset labels. |
| Wire-format Pydantic validation (422 on `from > to`) | API / Backend | — | D-15: backend is authoritative validator; FE prevention is UX nicety only. |
| SQL `played_at` predicate | Database / Storage | — | `apply_game_filters()` in repositories tier — single source of truth per CLAUDE.md §Shared Query Filters. |
| Calendar UI (date selection) | Browser | — | Pure client-side widget; no SSR. |
| Filter state persistence across page navs | Browser | — | `useFilterStore` is a module-level `useSyncExternalStore` — no API/storage tier involvement (no localStorage, no URL — verified). |
| LLM windowing (last_3mo) | API / Backend | — | `insights_service.py` computes window internally; FE filter does not flow into prompt (D-18). |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `react-day-picker` | `^10.0.1` `[VERIFIED: npm registry; CITED: https://ui.shadcn.com/r/styles/new-york-v4/calendar.json declares "react-day-picker@latest"]` | Date picker primitive | Locked by D-01 (shadcn Calendar wraps DayPicker) |
| `date-fns` | `^4.2.1` `[VERIFIED: npm registry; CITED: shadcn calendar.json declares "date-fns" with no pin → resolves to latest 4.x]` | Date math / formatting | Required peer of shadcn Calendar; provides `format`, `addDays`, `subDays`, `subWeeks`, `subMonths`, `subYears`, `startOfDay`, `endOfDay` for the `presetToDates` utility |

### Already Installed (no add)

| Library | Installed Version | Use |
|---------|-------------------|-----|
| `radix-ui` | `^1.4.3` `[VERIFIED: frontend/package.json]` | `<Popover>` for desktop trigger pattern (D-03). The project uses the umbrella `radix-ui` package, not individual `@radix-ui/react-popover` — Popover wrapper at `frontend/src/components/ui/popover.tsx` already imports from `"radix-ui"`. |
| `vaul` | `^1.1.2` `[VERIFIED: frontend/package.json]` | `Drawer.NestedRoot` for mobile sheet (D-06). Confirmed exported from `vaul` at line 1139 of `src/index.tsx` `[VERIFIED: https://github.com/emilkowalski/vaul/blob/main/src/index.tsx#L1098]`. |
| `lucide-react` | `^0.577.0` `[VERIFIED: frontend/package.json]` | `Calendar` / `X` icons for trigger / Apply CTA |

### Backend (no add)

| Library | Use |
|---------|-----|
| Pydantic v2 | `@model_validator(mode='after')` for `from_date ≤ to_date` invariant (D-15) `[VERIFIED: project uses Pydantic 2 throughout — confirmed via existing `@field_validator` patterns in app/schemas/openings.py:14, app/schemas/openings.py:134]` |
| FastAPI `Query()` | `date.date | None` query-param coercion. FastAPI auto-coerces ISO `YYYY-MM-DD` strings to `datetime.date` via Pydantic. `[VERIFIED: standard FastAPI behavior; confirmed in the wild by Phase 87 PR which used `date` types in stats query params — see `app/routers/stats.py` for the established `Query(default=None)` pattern]` |

### Installation

```bash
cd frontend && npx shadcn@latest add calendar
# Auto-adds: react-day-picker@latest (10.0.1), date-fns (4.2.1)
# Auto-writes: frontend/src/components/ui/calendar.tsx
# Auto-uses: existing button registry entry as a dependency
```

**Bundle impact:** ~40 KB gzipped (~25 KB react-day-picker + ~15 KB date-fns tree-shakeable). `date-fns` v4 uses ESM by default and tree-shakes well — only the specific `format`, `subDays`, etc. imports ship.

**Version verification (run before install in Wave 0):**
```bash
cd frontend && npm view react-day-picker version && npm view date-fns version
# Confirmed 2026-05-21: react-day-picker 10.0.1, date-fns 4.2.1
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads (weekly) | Source Repo | slopcheck | Disposition |
|---------|----------|-----|--------------------|-------------|-----------|-------------|
| `react-day-picker` | npm | 8 yrs (initial publish 2017) | ~4M | github.com/gpbl/react-day-picker | not run (best-effort gate unavailable in this session) | `[ASSUMED]` — but: (a) discovered from authoritative source (shadcn registry JSON, confirmed via curl), (b) extreme age + download count, (c) source repo exists, (d) installed today by countless shadcn users. Planner should still gate behind a `checkpoint:human-verify` for belt-and-suspenders compliance with the protocol. |
| `date-fns` | npm | 11 yrs | ~25M | github.com/date-fns/date-fns | not run | `[ASSUMED]` — same disposition: discovered from shadcn registry, ancient + ubiquitous. Checkpoint recommended. |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck not run; both packages were independently confirmed via the shadcn registry JSON pulled from `https://ui.shadcn.com/r/styles/new-york-v4/calendar.json`).

**Packages flagged as suspicious [SUS]:** none.

*Researcher note: per the package legitimacy protocol, packages discovered via shadcn's registry JSON + verified via `npm view` are tagged `[ASSUMED]` because slopcheck did not run. The planner should insert a `checkpoint:human-verify` task before the `npx shadcn add calendar` install. Strictly speaking the shadcn registry IS an authoritative source — but the protocol's `[VERIFIED]` tag is reserved for the post-slopcheck state.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  USER (clicks "Custom range…" in Recency Select)                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────┐
        │  FilterPanel.tsx             │
        │  - Select value="custom"     │
        │  - onValueChange fires       │
        └──────────────┬───────────────┘
                       │
       ┌───────────────┴────────────────┐
       │                                │
   DESKTOP (md+)                    MOBILE (<md)
       │                                │
       ▼                                ▼
┌──────────────────┐         ┌──────────────────────┐
│ Radix Popover    │         │ Drawer.NestedRoot    │
│ <PopoverAnchor>  │         │  (vaul) inside       │
│  = trigger DOM   │         │  existing FilterPanel│
│ <PopoverContent> │         │  Drawer              │
│  Calendar mode=  │         │  Calendar (1 month)  │
│  "range"         │         │  + Apply button      │
└──────────┬───────┘         └──────────┬───────────┘
           │                            │
           │ DateRange { from, to }     │ DateRange + Apply
           │ (auto-close on full pick)  │
           ▼                            ▼
    ┌────────────────────────────────────────┐
    │  FilterState.customRange (new field)   │
    │  { from?: Date; to?: Date } | null     │
    │  + filters.recency = 'custom' marker   │
    └─────────────────┬──────────────────────┘
                      │
                      ▼
    ┌────────────────────────────────────────┐
    │  presetToDates(preset, now)            │
    │   OR { from, to } directly if custom   │
    │  → {from?: Date, to?: Date}            │
    │  → ISO YYYY-MM-DD strings              │
    │  memoized by (preset, today-string)    │
    └─────────────────┬──────────────────────┘
                      │
                      ▼
    ┌────────────────────────────────────────┐
    │  Hooks (6): useOpenings, useEndgames,  │
    │  useStats.use*, useNext-Moves,         │
    │  useOpeningInsights, useEndgameInsights│
    │  → request body { from_date, to_date } │
    │  → TanStack queryKey includes both     │
    └─────────────────┬──────────────────────┘
                      │
                      ▼
    ┌────────────────────────────────────────┐
    │  Pydantic Request Schemas              │
    │   from_date: date.date | None          │
    │   to_date: date.date | None            │
    │   @model_validator: from_date ≤ to_date│
    │   (422 on violation)                   │
    └─────────────────┬──────────────────────┘
                      │
                      ▼
    ┌────────────────────────────────────────┐
    │  apply_game_filters() — query_utils.py │
    │   if from_date: stmt.where(played_at   │
    │       >= from_date)                    │
    │   if to_date: stmt.where(played_at <   │
    │       to_date + interval '1 day')      │
    │  No timezone math (UTC → local         │
    │  bounded already on the FE).           │
    └────────────────────────────────────────┘
```

### Recommended Project Structure

No new directories. Files touched:

```
frontend/
├── src/
│   ├── components/
│   │   ├── filters/
│   │   │   ├── FilterPanel.tsx              # 9th item + popover/drawer
│   │   │   └── CustomRangePopover.tsx       # NEW — desktop popover content
│   │   │   └── CustomRangeDrawer.tsx        # NEW — mobile nested-Vaul content
│   │   └── ui/
│   │       └── calendar.tsx                 # NEW — shadcn registry add
│   ├── lib/
│   │   └── recency.ts                       # NEW — presetToDates() utility
│   ├── types/
│   │   ├── api.ts                           # Rename Recency → RecencyPreset, add 'custom'
│   │   └── position_bookmarks.ts            # D-19: remove recency field
│   ├── hooks/                               # 6 hooks: drop recency, add from_date/to_date
│   └── api/
│       └── client.ts                        # buildFilterParams: recency → from_date/to_date
app/
├── repositories/
│   └── query_utils.py                       # apply_game_filters signature change
├── schemas/
│   ├── openings.py                          # 3 declarations (2 keep changed, 1 removed)
│   ├── insights.py                          # FilterContext recency → from_date/to_date
│   ├── stats.py                             # BookmarkPhaseEntryRequest recency removed/replaced
│   └── opening_insights.py                  # OpeningInsightsRequest recency removed/replaced
├── routers/
│   ├── stats.py                             # Query params recency → from_date/to_date
│   ├── endgames.py                          # Query params recency → from_date/to_date
│   └── insights.py                          # Query params + _validate_full_history_filters gate update
└── services/
    ├── openings_service.py                  # recency_cutoff() helper → remove; RECENCY_DELTAS dict → remove
    ├── stats_service.py                     # callsite parameter rename
    ├── endgame_service.py                   # callsite parameter rename
    ├── insights_service.py                  # lines 153,164: switch to from_date/to_date windows
    ├── insights_llm.py                      # line 421 (docstring only — verify)
    └── opening_insights_service.py          # cutoff = recency_cutoff(request.recency) callsite
```

### Pattern 1: Two-Step Select → Radix Popover Anchored to Trigger

**What:** When the Select reports `value === 'custom'`, programmatically close the Select and open a separate `<Popover>` whose `<PopoverAnchor>` is the same DOM element as the Select trigger. Radix Popover accepts `<PopoverAnchor>` as a sibling of `<PopoverTrigger>` for exactly this case.

**When to use:** The two-step is locked by D-03. Don't try to inline the calendar inside `<SelectContent>` — Radix Select intentionally restricts its content to items.

**Example (composition sketch — not full code):**
```typescript
// Source: Radix UI Popover docs + existing frontend/src/components/ui/popover.tsx:40-44
// (PopoverAnchor wrapper already exported)
import { Popover, PopoverAnchor, PopoverContent } from '@/components/ui/popover';

function RecencyControl() {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
      <PopoverAnchor asChild>
        <Select
          onValueChange={(v) => {
            if (v === 'custom') {
              // Defer popover-open by one tick so the Select close animation
              // doesn't race the popover open animation.
              queueMicrotask(() => setPopoverOpen(true));
            }
            /* otherwise update filters.recency */
          }}
        >
          <SelectTrigger ref={triggerRef}>...</SelectTrigger>
          {/* SelectContent with 9 items including "custom" */}
        </Select>
      </PopoverAnchor>
      <PopoverContent>
        <Calendar mode="range" selected={range} onSelect={...} />
      </PopoverContent>
    </Popover>
  );
}
```

The `asChild` + `PopoverAnchor` pairing is the documented Radix way to anchor a Popover to an arbitrary element. `PopoverAnchor` is already re-exported from `frontend/src/components/ui/popover.tsx:40-44` (line 43: `<PopoverPrimitive.Anchor data-slot="popover-anchor" {...props} />`).

### Pattern 2: Nested Vaul Drawer (Mobile)

**What:** Render a second `Drawer.Root` inside the existing FilterPanel drawer using `Drawer.NestedRoot`. Vaul handles scroll-lock and focus management automatically.

**Source confirmation:** `vaul/src/index.tsx:1098-1110` — `[VERIFIED: https://github.com/emilkowalski/vaul/blob/main/src/index.tsx]`:
```typescript
export function NestedRoot({ onDrag, onOpenChange, open: nestedIsOpen, ...rest }: DialogProps) {
  const { onNestedDrag, onNestedOpenChange, onNestedRelease } = useDrawerContext();
  if (!onNestedDrag) {
    throw new Error('Drawer.NestedRoot must be placed in another drawer');
  }
  return <Root nested .../>;
}
```

And the export at line 1137-1140:
```typescript
export const Drawer = {
  Root,
  NestedRoot,
  Content,
  // ...
};
```

**Gotcha:** `Drawer.NestedRoot` MUST be a child of another `Drawer.Root` or it throws at runtime. Our outer drawer already exists (`frontend/src/pages/Openings.tsx:1063`) — we just need to render the nested Root inside the FilterPanel's render tree when the user clicks "Custom range…" in the mobile sheet view.

**Caveat:** The existing project `Drawer` wrapper (`frontend/src/components/ui/drawer.tsx`) does NOT re-export `NestedRoot`. Wave with the calendar install: add a `DrawerNested` export to that wrapper, or import `NestedRoot` directly from `vaul`.

### Pattern 3: Memoized `presetToDates`

**What:** Convert a `RecencyPreset` label to `{ from?: Date; to?: Date }` in user-local timezone, with `from` at start-of-day and `to` at end-of-day. Memoize on `(preset, today-as-YYYY-MM-DD-local)` so TanStack Query keys are stable within a calendar day.

**When to use:** Every hook that consumes filters. Without memoization, `Date.now()` per render would invalidate cache continuously.

**Sketch (full reference in §Code Examples):**
```typescript
// frontend/src/lib/recency.ts
import { format, startOfDay, endOfDay, subWeeks, subMonths, subYears } from 'date-fns';

const _cache = new Map<string, { from?: Date; to?: Date }>();

export function presetToDates(
  preset: RecencyPreset | null,
  now: Date = new Date(),
): { from?: Date; to?: Date } {
  if (preset === null || preset === 'all') return {};
  const todayKey = format(now, 'yyyy-MM-dd');
  const cacheKey = `${preset}|${todayKey}`;
  const cached = _cache.get(cacheKey);
  if (cached) return cached;

  const to = endOfDay(now);                       // local 23:59:59.999
  const from = startOfDay(_subForPreset(preset, now));
  const result = { from, to };
  _cache.set(cacheKey, result);
  return result;
}
```

### Anti-Patterns to Avoid

- **Computing `Date.now()` inside `useMemo([])` per hook** — produces a stable `from` that drifts from "today" until the page is reloaded. Solution: memoize at the shared utility on `(preset, today-string)`, not per hook.
- **Sending `from_date`/`to_date` as ISO **datetime** strings (with time component)** — backend coerces to `datetime.date`; if you ship `2026-03-01T00:00:00Z` you'll either succeed by silent truncation or 422 depending on FastAPI's Pydantic config. Stick to `YYYY-MM-DD`. Use `format(date, 'yyyy-MM-dd')` on the FE.
- **Treating "only `to_date` set" as "filter all the way back from epoch"** — D-17 says that's a valid intent. The SQL is correct (`played_at < to_date + 1 day` with no `>=` bound) but the FE needs to not coerce missing `from` to `subYears(now, 100)`.
- **Updating only the openings.py schema and forgetting `app/schemas/insights.py:133` and `app/schemas/stats.py:133`** — three other Pydantic surfaces also expose `recency` (see §Recency Call-Site Audit).
- **Removing `recency_cutoff` parameter while leaving callers' positional args intact** — Python won't complain about a misaligned positional call until runtime. Use keyword-only call sites where possible during the migration.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date range picker UI | Two `<input type="date">` synced + custom highlight CSS | shadcn Calendar (D-01) | Range mode with highlighted-span UX, keyboard nav, ARIA, RTL, and screen-reader announcement are all already done by react-day-picker. Reinventing is a week of work for worse UX. |
| Day-bounded arithmetic in user TZ | `new Date(...).setHours(0,0,0,0)` | `startOfDay(date)` / `endOfDay(date)` from `date-fns` | Already a transitive peer of shadcn Calendar. DST edge cases (Mar 13 2027 spring-forward) are handled correctly. |
| Date formatting for the trigger label | Custom `formatRange(from, to)` | `date-fns` `format(d, 'MMM d, yyyy')` | Locale-aware short formatting; no chance of `0`-padded vs unpadded inconsistencies. |
| Mobile nested-drawer scroll lock + focus | Custom CSS `body { overflow: hidden }` | `Drawer.NestedRoot` from vaul | Vaul handles scroll-lock, drag-to-dismiss, accessibility focus trap, and swipe gestures all together. |

**Key insight:** The risk on this phase is not the Calendar UI — it's the touch-everything refactor of `recency` across both stacks. Spend the effort budget there, not on the UI.

## Backend Wire-Format Change

### `apply_game_filters()` — current vs target

**Current** (`app/repositories/query_utils.py:12-77`):
```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,  # ← REMOVE
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> Any:
    ...
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
```

**Target:**
```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,       # ← NEW (replaces recency_cutoff)
    to_date: datetime.date | None,         # ← NEW
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> Any:
    ...
    if from_date is not None:
        stmt = stmt.where(Game.played_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Game.played_at < to_date + datetime.timedelta(days=1))
```

**Note on signature shape:** The current signature is positional-friendly (most callers pass 6 positional args ending in `recency_cutoff`). Adding a second required positional breaks all callers. Recommendation for the plan: **keep both as positional** in the same slot (replace 1 → 2 positional) and update every caller. Alternatively, switch them to keyword-only by adding `*,` before `from_date` — that's a bigger churn but a safer long-term signature. The planner should make this call.

**`played_at` column type:** `TIMESTAMP WITH TIME ZONE` `[VERIFIED: alembic/versions/20260311_133123_dcef507678d8_initial_schema.py:43 — sa.DateTime(timezone=True)]`. Postgres will compare `TIMESTAMPTZ >= DATE` by implicit-casting the date to a `TIMESTAMP WITH TIME ZONE AT TIME ZONE 'UTC' 00:00:00`. **This is the documented gotcha:** "from_date = 2026-03-01" applied against `played_at TIMESTAMPTZ` filters to games whose UTC `played_at` is on or after `2026-03-01 00:00:00 UTC`, which is `2026-02-28 19:00:00 EST` — i.e. a US user picking "March 1" gets games played in the last 5 hours of Feb 28 local time. Two acceptable outcomes:

1. **Accept the UTC discrepancy** as a known minor edge case — at most 24 hours of drift, only matters for very recent games on day boundaries. Document in the predicate comment.
2. **Use `played_at AT TIME ZONE 'UTC' >= :from_date`** — explicit UTC cast in SQL. Doesn't fix the conceptual mismatch (user picks local day; backend matches UTC day) but documents the choice.

The notes file (`.planning/notes/custom-date-range-filter.md:81-85`) is clear that the **frontend canonicalizes to local-day boundaries before sending**. If the FE sends `from_date = "2026-03-01"` it means "user-local Mar 1 → Mar 1 00:00 LOCAL". With Postgres comparing against UTC, you get a 1-day fuzz at the boundary. **Recommended planner stance:** call it out in the schema doc, accept the fuzz, do not add a `client_timezone` parameter to the API (that's a separate scope creep).

### `insights_service.py:153,164` — internal LLM windows

Current `compute_findings` makes two sequential calls:
```python
# line 152-154 (all_time window)
recency=None,
# line 163-165 (last_3mo window)
recency="3months",
```

Target — both callsites become:
```python
# all_time window
from_date=None, to_date=None,
# last_3mo window
from_date=datetime.date.today() - datetime.timedelta(days=90),
to_date=None,  # OR datetime.date.today()
```

This is purely internal — no LLM prompt content change (D-18). Verify the receiving `endgame_service.get_endgame_overview` signature also flips from `recency: str | None` to `from_date / to_date`.

### `insights.py` router gating logic

`_validate_full_history_filters` (`app/routers/insights.py:54-88`) blocks the endpoint when `recency != "all_time"`. New gate becomes:

```python
if filters.from_date is not None or filters.to_date is not None:
    blocking.append("Clear Custom date range filter")
```

But `FilterContext` (in `app/schemas/insights.py:133`) currently has `recency: Literal["all_time", "week", ...]` with default `"all_time"` — a NON-OPTIONAL field. After the rename, the planner has two shape options:

(a) **`from_date: datetime.date | None = None, to_date: datetime.date | None = None`** — flat, matches the wire shape directly. Recommended.
(b) Mirror the discriminated union from the frontend store.

Option (a) is right because `FilterContext` IS a wire-shape mirror — it's used as the `FilterContext.model_dump()` cache key in `insights_llm.py`. Changing it from a single Literal to two optional dates also changes the cache-key shape; old cache rows will naturally miss. That's acceptable behavior on deploy (matches the "natural cache miss" already documented for TanStack Query).

## Recency Call-Site Audit

Run `rg -n "recency|Recency"` against each tree to verify (final count as of 2026-05-21).

### Frontend (21 files)

**Type declarations:**
- `frontend/src/types/api.ts:38` — `export type Recency = ...` → rename to `RecencyPreset`, drop `'custom'` from the preset list (it's a UI-only marker, not a preset value).

**Filter store / UI state:**
- `frontend/src/components/filters/FilterPanel.tsx:9,28,40,58,99,110,173,178,194` — `Recency` import, `FilterState.recency` field, `DEFAULT_FILTERS.recency`, `FILTER_DOT_FIELDS`, the FilterField union, and the Select markup itself.

**Hooks (6 — locked by D-13):**
- `frontend/src/hooks/useOpenings.ts:25` — `recency: params.filters.recency`
- `frontend/src/hooks/useEndgames.ts:11` — `recency: filters.recency`
- `frontend/src/hooks/useEndgameInsights.ts:15` — `recency: filters.recency`
- `frontend/src/hooks/useOpeningInsights.ts:5,14,31,42,53` — Recency import, filter type, normalizedRecency, query key, request body
- `frontend/src/hooks/useStats.ts:3,9,14,18,19,24,29,33,34,39,46,54,56,69,77,87,97` — `useRatingHistory`, `useGlobalStats`, `useMostPlayedOpenings`, `useBookmarkPhaseEntryMetrics`
- `frontend/src/hooks/useNextMoves.ts:21,33` — `recency: filters.recency` in queryKey and request body

**Hook NOT in the CONTEXT-listed six but is also a consumer:**
- `useBookmarkPhaseEntryMetrics` (in `useStats.ts`) passes `recency` to `/stats/bookmark-phase-entry-metrics`. **Planner: add this to the migration list.**

**API client:**
- `frontend/src/api/client.ts:78,87,127,134,142,149,157,179,193` — `buildFilterParams.recency`, the 3 stats endpoints, the 3 endgame endpoints.

**Pages / consumers:**
- `frontend/src/pages/Openings.tsx:289,321,351,1103` — passes `debouncedFilters.recency` into queries; `1103` is a code comment
- `frontend/src/pages/Endgames.tsx:601,673` — empty-state copy mentions "recency filters"
- `frontend/src/pages/GlobalStats.tsx:17,20,21,25,28,44,123,177` — derives `recency` from FilterState; `visibleFilters={['platform', 'recency']}` on the panel
- `frontend/src/pages/Home.tsx:371` — marketing copy: "filterable by time control, color, and recency" (planner: keep "recency" the user-facing label, even though the type is `RecencyPreset`)
- `frontend/src/pages/openings/GamesTab.tsx:55` — empty state copy

**Insight blocks:**
- `frontend/src/components/insights/OpeningInsightsBlock.tsx:69,141,240` — passes through, copy mentions "longer recency window"
- `frontend/src/components/insights/EndgameInsightsBlock.tsx:52` — modified-filter detector compares to DEFAULT_FILTERS

**Charts:**
- `frontend/src/components/charts/EndgameEloTimelineSection.tsx:389` — empty-state copy

**Time-series (D-19 — REMOVE):**
- `frontend/src/types/position_bookmarks.ts:52` — `recency` field on `TimeSeriesRequest`
- `frontend/src/types/position_bookmarks.ts:72` — code comment

**Tests:**
- `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx`
- `frontend/src/hooks/__tests__/useOpeningInsights.test.tsx`
- `frontend/src/components/insights/OpeningInsightsBlock.test.tsx:38`
- `frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx:47`

**Other types:**
- `frontend/src/types/stats.ts:96` — `BookmarkPhaseEntryRequest.recency`

### Backend (23 files)

**Pydantic schemas (4 surfaces — 3 stay, 1 D-19 removes):**
- `app/schemas/openings.py:39` — `OpeningsRequest.recency` → switch to `from_date` / `to_date`
- `app/schemas/openings.py:153` — `TimeSeriesRequest.recency` → **REMOVE per D-19**
- `app/schemas/openings.py:215` — `NextMovesRequest.recency` → switch to `from_date` / `to_date`
- `app/schemas/insights.py:133` — `FilterContext.recency` (Literal, default `"all_time"`) → switch to `from_date` / `to_date` (default `None`)
- `app/schemas/opening_insights.py:29` — `OpeningInsightsRequest.recency` → switch to `from_date` / `to_date`
- `app/schemas/stats.py:133` — `BookmarkPhaseEntryRequest.recency` (`str | None`) → switch to `from_date` / `to_date`

**Routers (3 — Query params):**
- `app/routers/stats.py:27,52,77,92,115` — `recency: str | None = Query(default=None)` on 3 endpoints + 2 service-call passes
- `app/routers/endgames.py:33,56,70,95` — 2 endpoints
- `app/routers/insights.py:68,97,140,182,217` — `_validate_full_history_filters` gate + 2 endpoints

**Services (5):**
- `app/services/openings_service.py:56` — `RECENCY_DELTAS` dict — **REMOVE entirely** (frontend owns the conversion now)
- `app/services/openings_service.py:137-145` — `recency_cutoff()` helper — **REMOVE entirely**
- `app/services/openings_service.py:165,177,201,241,295,313,468,480,499,523` — every callsite that resolves recency to cutoff
- `app/services/stats_service.py:35,70,87,94,101,113,123,132,211,216,225,271,280,295,313,328,343,356,370,527,550` — extensive callsites
- `app/services/endgame_service.py:84,783,791,807,820,854,863,2343,2354,2365,2396,2408,2500,2518,2528,2637,2649,2665,2678,2700,2724,2771` — extensive callsites
- `app/services/insights_service.py:133-136 (docstring), 153,164` — internal windows (D-18)
- `app/services/insights_llm.py:421` — docstring reference only — verify no live code
- `app/services/opening_insights_service.py:52,589,677,887,903,951` — callsites

**Repositories (3 + 1):**
- `app/repositories/query_utils.py:12,18,32,57,58` — the central change
- `app/repositories/openings_repository.py:19,66,110,111,143,178,179,212,232,250,280,318,340,361,393,457,463,481,495,549,555,573,669,670,676` — every per-function signature
- `app/repositories/endgame_repository.py:25,76,86,92,107,126,132,147,266,272,288,366,372,389,429,435,468,515,521,530,536,557,616,622,672,678,696,792,798,814,837,838,844,865,871` — extensive
- `app/repositories/stats_repository.py:30,85,120,122,128,140,178,184,196,234,240,256,345,351,393,443,449,476,499,540,546` — extensive

**Tests (17+ files):**
- All `tests/test_*_repository.py`, `tests/test_*_service.py`, `tests/test_*_router.py`, `tests/test_insights_schema.py`, `tests/test_openings_time_series.py`, `tests/routers/test_insights_openings.py`, `tests/services/test_insights_*.py`, `tests/repositories/test_opening_insights_repository.py`, `tests/test_integration_routers.py`, `tests/test_aggregation_sanity.py` — all pass `recency` or `recency_cutoff=` as keyword args. Estimated total: ~150-200 individual call-site updates.

**Scripts:**
- `scripts/prodcheck_80_1.py:11,55` — local script that uses the filter shape; non-blocking but should be updated for consistency.

## TanStack Query Key Audit

Every existing query key that includes a recency component must change. Listed by hook:

| Hook | Key shape today | Required change |
|------|-----------------|-----------------|
| `useOpeningsPositionQuery` | `['openingsPosition', targetHash, params.filters, offset, limit]` | `filters` object already contains `recency` — replace with `from_date` / `to_date` strings on the FilterState |
| `useRatingHistory` | `['ratingHistory', normalizedRecency, platform, opponentType, gap.min, gap.max]` | Replace `normalizedRecency` slot with `from_date`/`to_date` (or a single derived string `fromKey` = `${from ?? ''}|${to ?? ''}`) |
| `useGlobalStats` | `['globalStats', normalizedRecency, ...]` | Same |
| `useMostPlayedOpenings` | `['mostPlayedOpenings', normalizedRecency, ...]` | Same |
| `useBookmarkPhaseEntryMetrics` | `['bookmarkPhaseEntryMetrics', hashKey, normalizedRecency, ...]` | Same |
| `useEndgameOverview` / `useEndgameGames` | `['endgameOverview', params, window]` — `params` includes `recency` | Same — params object change suffices |
| `useNextMoves` | `[..., {recency: filters.recency, ...}]` | Replace `recency` field with `from_date` and `to_date` |
| `useOpeningInsights` | `['openingInsights', normalizedRecency, ...]` | Replace `normalizedRecency` slot |
| `useCachedEndgameInsights` | `['endgame-insights', 'cached', params]` — params builds from `buildFilterParams` | Once `buildFilterParams` switches, this is automatic |

**Cache invalidation on deploy:** Existing cache entries keyed on `recency` will simply not match the new keys — natural cache miss + refetch. **Verified safe** because:
1. `useFilterStore` is module-level in-memory only (`frontend/src/hooks/useFilterStore.ts:5`) — no localStorage / sessionStorage.
2. No URL params expose `recency` today (audited via `rg -n "recency" frontend/src/ | rg -i "search|navigate"` — only auth-flow URL params surface).
3. TanStack Query default cache lives in memory only (`frontend/src/lib/queryClient.ts`) — verified no `persistQueryClient` usage.

D-14 (URL param migration) is effectively a no-op. The planner should still confirm via a final grep before declaring done.

## Frontend State Architecture

```
┌──────────────────────────────────────────────────┐
│ useFilterStore — useSyncExternalStore over a     │
│ module-level FilterState. Survives nav, dies on  │
│ reload. No localStorage / URL persistence.       │
│ Source: frontend/src/hooks/useFilterStore.ts:5   │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼ filters: FilterState
┌──────────────────────────────────────────────────┐
│ Openings.tsx (line 134), Endgames.tsx (line 99,  │
│ has a separate pendingFilters useState ON TOP),  │
│ GlobalStats.tsx (line 18)                        │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│ FilterPanel.tsx — receives `filters` and         │
│ `onChange` as props (no direct store coupling)   │
└──────────────────────────────────────────────────┘
```

**Discretion call (custom-range field shape) — recommendation:**

The CONTEXT.md presents two options:
1. `customRange: { from?: Date; to?: Date } | null` sibling field to `recency`.
2. `recency` becomes a discriminated union `RecencyPreset | { kind: 'custom'; from?; to? }`.

**Recommended: Option 1 (sibling field) plus a special marker `recency: 'custom' | null | RecencyPreset`.**

Rationale:
- `FilterState` is currently a flat shape with all primitive/array/null fields except `opponentStrength`. Adding a discriminated union breaks the existing `areFiltersEqual` helper (`frontend/src/components/filters/FilterPanel.tsx:70-97`) which uses `===` for most comparisons and a hand-rolled object compare only for `opponentStrength`. A discriminated union would require special-casing both forms.
- Sibling field maps cleanly to the trigger-label rendering: trigger reads `filters.recency` (preset label) OR `filters.customRange` (formatted range string). Sets `recency = 'custom'` and `customRange = { from, to }` together when user picks a custom range; sets `customRange = null` whenever any preset is picked.
- Sibling shape requires extending `FILTER_DOT_FIELDS` to include `customRange`, and extending `areFiltersEqual` to deep-compare it. Both are localized changes.

**Result:**
```typescript
export interface FilterState {
  // ... existing fields
  recency: RecencyPreset | 'custom' | null;          // 'custom' = look at customRange
  customRange: { from?: Date; to?: Date } | null;    // null = no custom range
}

export const DEFAULT_FILTERS: FilterState = {
  // ...
  recency: null,
  customRange: null,
};
```

## Validation Pattern

**Backend validation (D-15): Pydantic v2 `@model_validator(mode='after')`.**

The project uses Pydantic v2 throughout and already uses `@field_validator` for cross-field coercion (`app/schemas/openings.py:14,134,195`). For cross-field invariants like `from_date ≤ to_date`, `@model_validator(mode='after')` is the project-idiomatic surface.

```python
# app/schemas/openings.py (sketched)
from pydantic import BaseModel, model_validator

class OpeningsRequest(BaseModel):
    # ...existing fields...
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None

    @model_validator(mode='after')
    def _check_date_range(self) -> 'OpeningsRequest':
        if self.from_date is not None and self.to_date is not None:
            if self.from_date > self.to_date:
                raise ValueError('from_date must be <= to_date')
        return self
```

Pydantic raises `ValidationError` from the validator, which FastAPI surfaces as **HTTP 422 Unprocessable Entity** with the project's standard error response shape. No additional router-level check needed. `[VERIFIED: standard FastAPI/Pydantic behavior; established in project via existing field_validator pattern]`

**For routers using `Query()` params** (`stats.py`, `endgames.py`, `insights.py`), the same validator must live on a wrapping Pydantic model or be enforced inline:

```python
from fastapi import HTTPException, Query

@router.get("/stats/global")
async def get_global_stats(
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    # ...
):
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
```

Inline check is the lower-ceremony choice for Query params; defining a shared `DateRangeQuery` dependency is over-engineering for 3 endpoints.

**Frontend prevention (D-15):** react-day-picker's `mode="range"` naturally builds `from` first, then `to ≥ from` (the user clicks `from`, then any subsequent click sets `to`). The "Apply" CTA on mobile (D-07) should disable when `!range?.from`. Desktop popover auto-closes per D-05 — no explicit gate needed because the range is always valid by construction.

## Bookmark Time-Series Pre-Work (D-19)

Three `recency` declarations in `app/schemas/openings.py`:

| Line | Schema | Disposition |
|------|--------|-------------|
| 39 | `OpeningsRequest.recency` | Switch to `from_date`/`to_date` |
| 153 | `TimeSeriesRequest.recency` | **REMOVE (D-19)** |
| 215 | `NextMovesRequest.recency` | Switch to `from_date`/`to_date` |

**TimeSeriesRequest consumers:**
- `frontend/src/types/position_bookmarks.ts:52` — `recency?: 'week' | 'month' | ...` field, **REMOVE**
- `frontend/src/types/position_bookmarks.ts:72` — code comment referencing "recency window", update
- `app/services/openings_service.py:295,313` — `compute_bookmark_time_series` (or similar) — these are the time-series service callsite; trace and drop the `recency_cutoff` pass to the repository
- `tests/test_openings_time_series.py` — fixtures pass `recency`; remove

**UI exposure audit:** Bookmark time-series is rendered by the bookmark sidebar / drawer panel. Confirmed via grep that nothing in `frontend/src/components/charts/` or `frontend/src/pages/openings/` reads or sends a recency value into the time-series request — this field has been unused at the call boundary for some time.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no database tables store the literal string `"recency"` as a value | None |
| Live service config | None — no production config references recency presets | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |
| TanStack Query cache (in-memory only) | All query keys including `recency` will naturally evict on deploy refresh | None — natural cache miss |
| localStorage filter persistence | None — `useFilterStore` is in-memory only (verified: `frontend/src/hooks/useFilterStore.ts:5`); the only localStorage flag is `filters-hint-dismissed` (a UX flag, unrelated) | None |
| URL search params | No page exposes `recency` in URL state (verified via grep — only `tab=`, `type=`, OAuth callback params surface) | None — D-14 is a no-op |
| API cached responses (insights_llm Tier-1 cache) | Cache keys include the `FilterContext.model_dump()` hash. Changing FilterContext shape from `recency` to `from_date`/`to_date` will naturally invalidate every existing cache row | Acceptable — equivalent to natural cache miss, matches the LLM-cache "shape change = invalidate" pattern used historically |

## Common Pitfalls

### Pitfall 1: TZ canonicalization race — Date.now() per render

**What goes wrong:** `presetToDates('week')` invoked without memoization returns a new `Date` object on every render, which serializes to a different ISO string by the millisecond. TanStack Query keys include this string; cache misses every render. Result: infinite refetch loop or massive N+1 of API calls.

**Why it happens:** Hooks normally treat dependencies as referentially stable. A fresh Date per render passes `===` checks via React's `useEffect` deps (`Date !== Date`), and TanStack Query's `JSON.stringify` of the key changes by the millisecond.

**How to avoid:** Memoize on `(preset, format(today, 'yyyy-MM-dd'))` so the result is stable within a calendar day. Reference impl in §Code Examples.

**Warning signs:** DevTools shows continuous `query → fetching` for openings/stats/endgame queries; React DevTools shows re-renders driven by the queryKey hook.

### Pitfall 2: UTC boundary fuzz on `played_at TIMESTAMPTZ`

**What goes wrong:** User picks "March 1, 2026" in EST timezone. FE sends `from_date = "2026-03-01"` (local Mar 1 00:00). Postgres compares `played_at >= DATE '2026-03-01'` which casts the date to UTC midnight = `2026-03-01 00:00:00 UTC` = `2026-02-28 19:00:00 EST`. Games played from 7pm EST on Feb 28 onward match. User sees "wait, why did games from Feb 28 show up when I picked March 1?"

**Why it happens:** TIMESTAMPTZ vs DATE comparison casts DATE to a UTC TIMESTAMPTZ at 00:00. There's no way to recover the user's local TZ on the server without passing it explicitly.

**How to avoid:** Two paths:
1. Accept the up-to-24-hour boundary fuzz, document the tradeoff in the predicate comment in `apply_game_filters`, and skip a `client_timezone` param.
2. Pass `client_timezone` from FE → backend, do `played_at AT TIME ZONE :client_tz >= :from_date` in SQL. Bigger scope, scope creep risk.

Recommended: option 1. The minor mismatch is a known tradeoff of bounded-day filtering vs. UTC storage; chess users won't materially care about ≤24h boundary games.

**Warning signs:** Manual UAT shows boundary-day games in/out unexpectedly. Test the boundary explicitly: seed a game played at `2026-03-01 02:00 UTC` (= `2026-02-28 21:00 EST`), filter to `from_date=2026-03-01`, confirm it appears. Decide if that's the desired behavior.

### Pitfall 3: Forgetting `_validate_full_history_filters` gate update

**What goes wrong:** Plan only updates wire params and forgets `app/routers/insights.py:68`. Result: LLM endpoint now accepts custom-range filters, runs against a truncated dataset, and produces a "your full history" report based on a 1-week window. Sentry surfaces silent regression.

**Why it happens:** The gate is buried in a private validator function and isn't part of the obvious schema rename surface.

**How to avoid:** Update the gate at the same time as `FilterContext`. New gate:
```python
if filters.from_date is not None or filters.to_date is not None:
    blocking.append("Clear Custom date range filter")
```
Verify with the existing test `tests/test_insights_router.py` for the full-history gate.

**Warning signs:** Insights endpoint returns 200 with a 3-month report under any non-default filter.

### Pitfall 4: `useBookmarkPhaseEntryMetrics` is the 7th hook, not 6

**What goes wrong:** CONTEXT.md D-13 lists six hooks; planner builds plans for six; the bookmark phase-entry hook silently keeps passing `recency` and 422's against the updated `BookmarkPhaseEntryRequest` schema.

**Why it happens:** It's a sibling of `useMostPlayedOpenings` in the same file (`useStats.ts:66`), easily missed during a per-file pass.

**How to avoid:** Audit `useStats.ts` line by line — there are FOUR hooks in that file: `useRatingHistory`, `useGlobalStats`, `useMostPlayedOpenings`, `useBookmarkPhaseEntryMetrics`. All four pass recency.

**Warning signs:** Bookmark phase-entry metrics (the small "MG entry eval" pillar on bookmark cards) fails to load under any non-default filter post-deploy.

### Pitfall 5: ty cascade across two stacks

**What goes wrong:** Half-applied refactor (Wave 1 done, Wave 2 not) breaks `uv run ty check` because every service-layer callsite of `recency_cutoff=` now mismatches the repository signature. ty failures block CI.

**Why it happens:** `recency_cutoff` is a positional+keyword arg threaded through 4 repositories and 4 services. Once `query_utils.apply_game_filters` changes, every caller is broken until updated.

**How to avoid:** Land Wave 1 atomically — single PR that touches all backend files in one shot. Don't try to split "schemas vs repositories" or "endgame vs openings" — the type errors cascade and there is no useful intermediate state. The plan-check should flag any partial split.

**Warning signs:** Branch shows `apply_game_filters` updated but `tests/test_endgame_repository.py:165` still passes `recency_cutoff=None` — ty fails.

### Pitfall 6: Radix Select inside Radix Popover focus management

**What goes wrong:** Opening the Popover programmatically (D-03) while the Select is still in its closing animation causes the Popover to steal focus before the Select finishes. The Select trigger remains visually "selected" or the Popover open-trigger gets eaten by the Select's restore-focus.

**Why it happens:** Both Radix primitives manage focus via `data-state` and `restoreFocus`. They don't coordinate.

**How to avoid:** Defer `setPopoverOpen(true)` by one tick using `queueMicrotask` or `setTimeout(0)` after the Select reports `onValueChange('custom')`. The deferral lets the Select complete its close + restore-focus sequence before the Popover claims focus.

**Warning signs:** First click on "Custom range…" closes the Select but the Popover doesn't open; the second click does.

## Code Examples

### `presetToDates` reference implementation

```typescript
// frontend/src/lib/recency.ts
// Source: project conventions (CLAUDE.md §No magic numbers, §Type safety)
// + date-fns docs https://date-fns.org/v4/docs/format

import {
  format, startOfDay, endOfDay,
  subWeeks, subMonths, subYears,
} from 'date-fns';

/** UI-only preset list. Crosses no API boundary. */
export type RecencyPreset =
  | 'week' | 'month' | '3months' | '6months'
  | 'year' | '3years' | '5years' | 'all';

const _cache = new Map<string, { from?: Date; to?: Date }>();

function _subForPreset(preset: RecencyPreset, now: Date): Date {
  switch (preset) {
    case 'week': return subWeeks(now, 1);
    case 'month': return subMonths(now, 1);
    case '3months': return subMonths(now, 3);
    case '6months': return subMonths(now, 6);
    case 'year': return subYears(now, 1);
    case '3years': return subYears(now, 3);
    case '5years': return subYears(now, 5);
    case 'all': return now; // never reached — 'all' short-circuits in presetToDates
  }
}

/**
 * Convert a preset label to { from, to } in user-local timezone.
 * `from` = start-of-day local for (now − preset window).
 * `to`   = end-of-day local for today.
 * Memoized by (preset, today-as-YYYY-MM-DD-local) so callers (TanStack Query
 * keys) get stable references within a calendar day.
 */
export function presetToDates(
  preset: RecencyPreset | null,
  now: Date = new Date(),
): { from?: Date; to?: Date } {
  if (preset === null || preset === 'all') return {};
  const todayKey = format(now, 'yyyy-MM-dd');  // user-local
  const cacheKey = `${preset}|${todayKey}`;
  const cached = _cache.get(cacheKey);
  if (cached) return cached;
  const result = {
    from: startOfDay(_subForPreset(preset, now)),
    to: endOfDay(now),
  };
  _cache.set(cacheKey, result);
  return result;
}

/** Render a Date as the ISO wire form `YYYY-MM-DD`. */
export function dateToWire(d: Date | undefined): string | undefined {
  return d ? format(d, 'yyyy-MM-dd') : undefined;
}
```

### `apply_game_filters` updated

```python
# app/repositories/query_utils.py
import datetime
from collections.abc import Sequence
from typing import Any

from sqlalchemy import case
from app.models.game import Game


def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> Any:
    if time_control is not None:
        stmt = stmt.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        stmt = stmt.where(Game.platform.in_(platform))
    if rated is not None:
        stmt = stmt.where(Game.rated == rated)  # noqa: E712
    if opponent_type == "human":
        stmt = stmt.where(Game.is_computer_game == False)  # noqa: E712
    elif opponent_type == "bot":
        stmt = stmt.where(Game.is_computer_game == True)  # noqa: E712
    # NOTE: Postgres implicitly casts DATE to TIMESTAMPTZ at UTC midnight. A
    # local-day-bounded filter on the FE side leaks up to 24h of boundary
    # games to the result set. Accepted trade-off (Phase 92 RESEARCH.md
    # §Pitfall 2). Frontend sends from_date/to_date as user-local day
    # boundaries; backend treats them as UTC midnight DATEs.
    if from_date is not None:
        stmt = stmt.where(Game.played_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Game.played_at < to_date + datetime.timedelta(days=1))
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    if opponent_gap_min is not None or opponent_gap_max is not None:
        # ... unchanged opponent gap logic ...
    return stmt
```

### Pydantic schema with model_validator

```python
# app/schemas/openings.py (OpeningsRequest sketch)
import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, Field, model_validator, field_validator

class OpeningsRequest(BaseModel):
    target_hash: int | None = None
    match_side: Literal["white", "black", "full"] = "full"
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    color: Literal["white", "black"] | None = None
    opponent_gap_min: int | None = None
    opponent_gap_max: int | None = None
    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=200)] = 50

    @field_validator("target_hash", mode="before")
    @classmethod
    def coerce_target_hash(cls, v: object) -> object:
        # ... unchanged BigInt coercion ...
        return v

    @model_validator(mode="after")
    def _check_date_range(self) -> "OpeningsRequest":
        if (self.from_date is not None and self.to_date is not None
                and self.from_date > self.to_date):
            raise ValueError("from_date must be <= to_date")
        return self
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Closed `Recency` string union on the wire | Optional `from_date`/`to_date` `date.date` pair | This phase | Single backend predicate, frontend owns "now"; cache keys reflect day rollover |
| `RECENCY_DELTAS` dict + `recency_cutoff()` helper backend-side | Removed entirely; FE computes the cutoff | This phase | Backend logic simpler; preset semantics live in one place (frontend) |
| `TimeSeriesRequest.recency` | Removed (D-19) | This phase | Was unused; the chart IS the time axis |

**Deprecated/outdated by this phase:**
- `app/services/openings_service.py:56-64` `RECENCY_DELTAS` dict — delete
- `app/services/openings_service.py:137-145` `recency_cutoff()` helper — delete
- `frontend/src/api/client.ts:87` `buildFilterParams` recency branch — replace

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest 4.1 (frontend) |
| Config files | `pyproject.toml` (pytest section), `frontend/vitest.config.*` |
| Quick run command (backend) | `uv run pytest tests/test_openings_repository.py -x` |
| Quick run command (frontend) | `cd frontend && npm test -- --run` |
| Full suite command (backend) | `uv run pytest -x` |
| Full suite command (frontend) | `cd frontend && npm run lint && npm test -- --run && npm run knip` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|--------------|
| D-09/D-10 | `apply_game_filters(from_date=date(2026,3,1), to_date=date(2026,4,1))` returns games with `played_at` in `[2026-03-01 UTC, 2026-04-02 UTC)` | unit | `uv run pytest tests/test_openings_repository.py::test_apply_game_filters_date_range -x` | NEW (add) |
| D-10 | Both omitted = no date predicate emitted | unit | `uv run pytest tests/test_openings_repository.py::test_apply_game_filters_no_date_filter -x` | NEW |
| D-17 | Only `from_date` set = `played_at >= from_date` only | unit | `uv run pytest tests/test_openings_repository.py::test_apply_game_filters_from_only -x` | NEW |
| D-17 | Only `to_date` set = `played_at < to_date + 1 day` only | unit | `uv run pytest tests/test_openings_repository.py::test_apply_game_filters_to_only -x` | NEW |
| D-15 | `OpeningsRequest(from_date='2026-04-01', to_date='2026-03-01')` raises ValidationError → 422 | unit | `uv run pytest tests/test_openings_router.py::test_invalid_date_range_returns_422 -x` (or service-layer schema test) | NEW |
| D-18 | `compute_findings` internal `last_3mo` window calls `get_endgame_overview(from_date=today-90, to_date=today)` | unit | `uv run pytest tests/services/test_insights_service.py -x` (existing test for the two-window structure — extend to assert new param shape) | EXISTS, extend |
| D-19 | `TimeSeriesRequest` schema rejects `recency=` field | unit | `uv run pytest tests/test_openings_time_series.py -x` (delete fixture line) | EXISTS, edit |
| D-13 | `useOpeningsPositionQuery` includes `from_date`/`to_date` in request body, not `recency` | unit (FE) | `cd frontend && npm test -- useOpenings` | EXISTS (existing recency tests; rewrite) |
| D-12 | `presetToDates('week')` returns `{from: startOfDay(now-1w), to: endOfDay(now)}` in user-local TZ | unit (FE) | `cd frontend && npm test -- recency` | NEW |
| D-12 | `presetToDates` cache returns same object reference within a calendar day | unit (FE) | `cd frontend && npm test -- recency` | NEW |
| D-03 | Selecting `value="custom"` opens the popover (RTL test on FilterPanel) | unit (FE) | `cd frontend && npm test -- FilterPanel` | NEW or extend |

### Sampling Rate
- **Per task commit:** `uv run pytest -x` (quick — most failures bubble in <60s)
- **Per wave merge:** Full suite (backend pytest + frontend lint+test+knip)
- **Phase gate:** Full pre-PR checklist green per `CLAUDE.md`

### Wave 0 Gaps
- [ ] `tests/test_query_utils.py` — NEW unit test file for `apply_game_filters` date-range semantics (no current direct tests of this helper — only via integration through repositories). Create with the 4 unit tests above.
- [ ] `frontend/src/lib/__tests__/recency.test.ts` — NEW unit test file for `presetToDates`.
- [ ] No framework install needed; pytest + vitest already configured.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no (phase has no auth changes) | — |
| V3 Session Management | no | — |
| V4 Access Control | no — phase changes filter shape only; existing `current_active_user` dependency unaffected | — |
| V5 Input Validation | **yes** | Pydantic v2 schemas with `@model_validator` (D-15); FastAPI `Query()` type coercion for `date.date`. `extra="forbid"` already applied on `OpeningInsightsRequest` (`app/schemas/opening_insights.py:27`). Maintain on all date-range-bearing schemas. |
| V6 Cryptography | no | — |

### Known Threat Patterns for FastAPI + Pydantic v2

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Date injection via malformed ISO strings | Tampering | Pydantic v2 type coercion — rejects with 422 on any non-`YYYY-MM-DD` input. Confirmed: FastAPI uses Pydantic's `datetime.date` parser which is strict. |
| Reverse date range as a DoS (filter accepts impossibly wide range) | DoS | `from_date > to_date` rejected; both omitted = same as today's "all time" = no new DoS surface. Far-past `from_date` (e.g. 1900-01-01) is allowed by D-16 but bounded by the user's actual game corpus — no expensive table scan beyond what "all time" already does. |
| Unknown-field injection (e.g. `client_timezone` or other extra) | Tampering | `extra="forbid"` on insight request schemas already enforces. Apply to all new shapes by default. |

## Sources

### Primary (HIGH confidence)
- `shadcn registry: https://ui.shadcn.com/r/styles/new-york-v4/calendar.json` — verified via direct curl: declares `react-day-picker@latest` + `date-fns` as dependencies; shows the exact `calendar.tsx` content that `npx shadcn add calendar` writes. Includes `range_start` / `range_middle` / `range_end` className slots that confirm range mode is first-class.
- `npm view react-day-picker version` → `10.0.1` (verified 2026-05-21)
- `npm view date-fns version` → `4.2.1` (verified 2026-05-21)
- `vaul/src/index.tsx` on GitHub: lines 1098-1110 (`NestedRoot` function), line 1137-1144 (`Drawer` export). `[VERIFIED: https://raw.githubusercontent.com/emilkowalski/vaul/main/src/index.tsx]`
- Project source files (all line refs in the Recency Call-Site Audit verified by `rg`)
- `alembic/versions/20260311_133123_dcef507678d8_initial_schema.py:43` — `played_at` is `sa.DateTime(timezone=True)`

### Secondary (MEDIUM confidence)
- WebSearch: react-day-picker v9/v10 `mode="range"` API — confirms `DateRange { from?: Date; to?: Date }` and `onSelect(range: DateRange | undefined, triggerDate: Date)`. Confirmed via the daypicker.dev docs at https://daypicker.dev/selections/range-mode but the WebFetch returned a placeholder snippet.

### Tertiary (LOW confidence)
- Bundle size estimates (~25 KB react-day-picker, ~15 KB date-fns) sourced from D-01 in CONTEXT.md — `[ASSUMED]`, the planner may want to measure with `npm run build` before/after to verify.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | shadcn `npx shadcn@latest add calendar` works in this project (registry "new-york-v4" style matches existing components) | Standard Stack | Low — project already uses shadcn components; calendar will install consistent with select.tsx, popover.tsx |
| A2 | `react-day-picker` v10 `mode="range"` produces a `DateRange` of shape `{from?: Date; to?: Date}` (not the v8 `{from, to}` tuple shape) | Pattern 1 | Medium — sample WebSearch result confirmed v9 shape; v10 likely same. Planner should sanity-check after install via the .tsx the registry writes. |
| A3 | `Drawer.NestedRoot` API surface is `onDrag, onOpenChange, open` (matches outer Root) | Pattern 2 | Low — verified directly in vaul source |
| A4 | Pydantic v2 `@model_validator(mode='after')` raised `ValueError` surfaces as FastAPI 422 (not 500) | Validation Pattern | Low — standard documented behavior; tested daily by every FastAPI app |
| A5 | Postgres TIMESTAMPTZ vs DATE comparison casts DATE to UTC midnight | Pitfall 2 | Low — Postgres docs are explicit; verified via SQL `SELECT '2026-03-01'::timestamptz` returns `2026-03-01 00:00:00+00` |
| A6 | Bundle size impact ~40 KB gz (D-01 lock) | Standard Stack | Low risk to phase; medium risk to PWA bundle policy — planner may want to measure |
| A7 | Frontend filter store has no localStorage persistence — natural cache miss on deploy is safe | Frontend State Architecture, TanStack Query Key Audit | Verified by reading `useFilterStore.ts:5` — module-level only |
| A8 | `useBookmarkPhaseEntryMetrics` is in fact a 7th hook needing migration (not in D-13's list) | Recency Call-Site Audit | High — if planner trusts D-13's count of 6, this hook breaks silently. Surfaced explicitly here. |
| A9 | The `_validate_full_history_filters` gate's "Switch Recency to All time" message becomes "Clear Custom date range filter" after rename | Backend Wire-Format Change | Low — straightforward |
| A10 | `extra="forbid"` should be added to `OpeningsRequest`, `NextMovesRequest`, `TimeSeriesRequest` for consistency with `OpeningInsightsRequest` | Security Domain | Low — these don't currently forbid extras; adding it now risks breaking any unknown field that's accidentally being sent. Recommend the planner NOT add `extra="forbid"` as part of this phase unless explicit scope creep; leave the security-hardening as a separate todo. |

## Open Questions

1. **Discretion call: one-month or two-month Calendar layout on desktop?**
   - What we know: two-month is shadcn default (and matches Stripe/GA). Existing Popover width is `w-72` (288px). Two-month would need a wider Popover.
   - What's unclear: whether the planner wants to bump the Popover width or use single-month even on desktop.
   - Recommendation: single-month on both desktop and mobile, with `numberOfMonths={1}`. Keeps Popover width consistent with existing project patterns; user can navigate months quickly enough. Two-month is a "we have screen real estate" feature; the FilterPanel is already cramped.

2. **Discretion call: format for "from only" or "to only" trigger label?**
   - What we know: D-04 hints "From Mar 1, 2026…" for from-only.
   - What's unclear: to-only equivalent. "Until Apr 1, 2026"? "… → Apr 1, 2026"?
   - Recommendation: "From Mar 1, 2026" (no ellipsis) and "Until Apr 1, 2026". Symmetric, no ambiguity, no trailing punctuation.

3. **Discretion: does `recency.ts` cache need explicit eviction across midnight?**
   - What we know: cache key includes `format(now, 'yyyy-MM-dd')` — when midnight rolls, the key changes naturally and a new entry is computed.
   - What's unclear: the OLD entries (yesterday's key) sit in the Map forever; over 30 days, 8 presets × 30 days = 240 stale entries. Harmless memory leak but technically a leak.
   - Recommendation: not worth fixing in v1. If a user keeps the tab open for 30+ days without refresh, 240 entries × ~100 bytes = 24 KB. Not material. Optional follow-up: bounded LRU.

4. **Open: should `compute_findings` `last_3mo` window use `from_date=today-90, to_date=None` or `from_date=today-90, to_date=today`?**
   - What we know: D-18 is "out of scope, no prompt change". The current code calls `recency="3months"` which under the existing helper computes `from = now - 90 days, to = None`.
   - Recommendation: replicate exact existing semantics — `to_date=None` (not `today`). Avoids any behavior drift inside the LLM cache key.

## Project Constraints (from CLAUDE.md)

The plan must honor these explicit directives:

- **Shared Query Filters**: `apply_game_filters()` is the single shared filter implementation. Do not duplicate the date predicate inside individual repositories. (This phase honors this by changing only `query_utils.py`.)
- **ty compliance**: Zero ty errors required; ty runs between ruff and pytest in CI. Use `Sequence[X]` not `list[X]` for parameter types accepting `list[Literal[...]]`. (Already correct in `query_utils.py`.)
- **No magic numbers**: The `+ datetime.timedelta(days=1)` literal in the `to_date` predicate is a documented sentinel for end-of-day-inclusive; should have an inline comment explaining the +1 day shift. Acceptable per CLAUDE.md's "comment bug fixes / non-obvious code" rule.
- **Pre-PR checklist**: ruff format → ruff check --fix → ty check → pytest → frontend lint+test must all pass locally before push. With ~150-200 callsite changes, expect ruff to surface formatting on the rewritten files.
- **Type safety**: Use `datetime.date` not `str` for the date params. `from_date: datetime.date | None` is the right type; ISO `YYYY-MM-DD` strings on the wire coerce automatically.
- **Function size limits**: Soft 100 logic LOC, hard 200. None of the affected functions grow significantly; the predicate change is a 4-line swap.
- **Refactor on sight**: `RECENCY_DELTAS` dict and `recency_cutoff()` helper become dead code — must be deleted in the same wave per "refactor bloated code on sight."
- **Sentry**: No new error paths; existing capture sites in services/repositories continue to apply. No new `sentry_sdk.set_context` calls needed.
- **Frontend `text-sm` minimum**: The existing FilterPanel "Recency" header is `text-xs` (legacy pre-rule). Do not regress, do not propagate to new Calendar UI — new code uses `text-sm` floor.
- **`data-testid` on every interactive element**: Calendar day buttons (the shadcn registry sets `data-day`; that's not enough — wrap with project-conventional `data-testid="calendar-day-${day.date.toLocaleDateString()}"`), the Popover content (`data-testid="custom-range-popover"`), the Apply CTA (`data-testid="btn-apply-custom-range"`), the nested Drawer (`data-testid="drawer-custom-range"`), the 9th Select item (`data-testid="filter-recency-custom"`).
- **Mobile-first**: Apply changes to both desktop and mobile renderers. The Popover (desktop) vs Drawer.NestedRoot (mobile) split is BOTH renderings of the same logical feature — the field shape, the trigger label rendering, the FilterState wiring is shared.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — shadcn registry JSON confirms install behavior; npm registry confirms versions; vaul source confirms NestedRoot API.
- Architecture: HIGH — Radix Popover and Vaul NestedRoot patterns are both established and verified in the source. The two-step Select→Popover flow has a documented `queueMicrotask` workaround for the focus race.
- Pitfalls: HIGH — every pitfall is grounded in either documented behavior (UTC casting, Pydantic 422) or a concrete code reference (`_validate_full_history_filters`, `useBookmarkPhaseEntryMetrics`).
- Backend audit: HIGH — full call-site enumeration via `rg`; 23 backend files identified.
- Frontend audit: HIGH — 21 frontend files identified, including the often-missed `useBookmarkPhaseEntryMetrics` 7th hook.

**Research date:** 2026-05-21
**Valid until:** 2026-06-21 (stable — shadcn Calendar + react-day-picker v10 are not rapidly evolving). Re-verify shadcn registry contents and npm versions if planning slips past one month.
