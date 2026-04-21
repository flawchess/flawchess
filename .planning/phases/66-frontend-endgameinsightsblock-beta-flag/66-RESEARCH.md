# Phase 66: Frontend EndgameInsightsBlock & Beta Flag — Research

**Researched:** 2026-04-21
**Domain:** React 19 / TanStack Query mutation pattern + SQLAlchemy User model extension + Alembic column migration
**Confidence:** HIGH (all patterns verified from live codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Interleaved per-section architecture. Single API call, single Regenerate button, one findings-hash cache entry. Overview in top card; each `SectionInsight` slotted into its matching H2 (`overall`, `metrics_elo`, `time_pressure`, `type_breakdown`).

**D-02:** Pre-click state: hero card with "Insights" H2 + 1-line blurb + primary "Generate insights" button. No section slots before first click.

**D-03:** Post-click: top card shows overview paragraph + "Regenerate" button. Each SectionInsight renders ABOVE existing chart cards within its H2 group.

**D-04:** Always expanded. No per-section collapse, no dismiss affordance.

**D-05:** Fewer than 4 sections: H2s without a matching section_id render as-is (no placeholder). Suppressed H2s (by existing guards): matching SectionInsight dropped client-side.

**D-06:** Heading label: "Insights" exactly.

**D-07:** Filter change after report rendered: insights STAY VISIBLE with an "outdated" indicator. User manually clicks Regenerate.

**D-08:** FE does not distinguish findings-affecting vs non-affecting filters. Any `appliedFilters` change lights the indicator. Backend cache handles the "color/rated only" case via `status: "cache_hit"`.

**D-09:** Hook shape = `useMutation + local component state`, mirroring `useImportTrigger` (`frontend/src/hooks/useImport.ts:24`).

**D-10:** Button copy: "Generate insights" pre-click, "Regenerate" post-click.

**D-11:** Locked failure copy: "Couldn't generate insights. Please try again in a moment." + `[Try again]` Button (`variant="brand-outline"`). Section insight slots empty on error.

**D-12:** `status: "stale_rate_limited"`: muted banner above overview ("Showing your most recent insights. You've hit the hourly limit; try again in ~{N} min."). Section insights render normally.

**D-13:** `stale_filters` field NOT visualised. FE ignores it.

**D-14:** HTTP 429 with `retry_after_seconds`: static "Try again in ~{N} min." line. `N = max(1, Math.ceil(retry_after_seconds / 60))`. `[Try again]` button always enabled.

**D-15:** Column name `users.beta_enabled` (not `insights_beta_enabled`). REQUIREMENTS.md BETA-01 and ROADMAP.md Phase 66/67 text updated to `beta_enabled` as part of migration commit.

**D-16:** Surface `beta_enabled` via existing `/users/me/profile` endpoint. Extend `UserProfileResponse` + `UserProfile` TS interface.

**D-17:** FE gating inside `EndgameInsightsBlock`: reads `useUserProfile()`, returns `null` when `profile?.beta_enabled !== true`. Also returns `null` while profile is loading. Per-section slots do the same beta check.

**D-18:** Alembic migration: `beta_enabled BOOLEAN NOT NULL DEFAULT false` with `server_default=sa.text("false")`. No index. Rollback: drop column.

**D-19:** Admin impersonation (`ClaimAwareJWTStrategy` from Phase 62) naturally returns impersonated user's `beta_enabled`. No special handling needed.

### Claude's Discretion

- Exact visual treatment of "outdated" indicator (locked in UI-SPEC: 6px brand-brown dot + caption text, static, inline-right of H2).
- Exact 1-line blurb on pre-click hero card (locked in UI-SPEC).
- SectionInsight in-H2 slot styling (locked in UI-SPEC: `text-sm font-semibold` headline, `list-disc text-sm text-muted-foreground` bullets, `mb-3`, no dividers).
- Loading skeleton shape (locked in UI-SPEC: 3-bar overview skeleton + button slot; per-section compact skeleton).
- `data-testid` values (locked in UI-SPEC: 13 testids).
- Whether `EndgameInsightsBlock` exposes per-section insights via render-prop / context / separate hook, or Endgames.tsx calls the mutation hook and passes each SectionInsight to existing chart components.
- Whether to lift mutation state to Endgames.tsx or keep in EndgameInsightsBlock with React context.
- Minute-rounding rule (locked: `max(1, Math.ceil(retry_after_seconds / 60))`).
- Mobile treatment (locked in UI-SPEC: no deviations from existing Endgame tab patterns).

### Deferred Ideas (OUT OF SCOPE)

- LocalStorage / sessionStorage persistence across page reloads.
- Admin UI for flipping `beta_enabled`.
- Per-feature beta columns / `user_beta_features` table.
- Live ticking countdown on 429.
- Filter-diff visualization on `stale_rate_limited`.
- Display of `model_used` / `prompt_version` to regular users.
- Per-section streaming responses.
- Info-popover on the insights block.
- Scroll-into-view anchor after Generate click.
- Typed TS discriminated union helpers ceremony.
- Integration-test coverage with `beta_enabled=True` seeded_user (scope TBD).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INS-01 | User with beta flag enabled sees a "Generate insights" button on the Endgame tab; a user with flag false sees nothing | D-15/D-16/D-17: `beta_enabled` column + `/users/me/profile` surface + self-gating component returning null |
| INS-02 | Generated report renders overview paragraph (≤150 words) above up to 4 Section blocks (≤12-word headline, 0–2 bullets ≤20 words) | D-01/D-02/D-03: interleaved architecture; Phase 65 `EndgameInsightsReport` schema enforces bounds |
| INS-03 | Changing filter context and regenerating produces different insight; color/rated alone does not force new LLM call | D-07/D-08: outdated indicator on any appliedFilters change; backend cache handles non-findings-affecting filter changes via `status:"cache_hit"` |
| BETA-01 | Beta access controlled by boolean flag on `users` table; default false; flip via direct DB op only | D-15/D-18: `users.beta_enabled BOOLEAN NOT NULL DEFAULT false` Alembic migration |
| BETA-02 | Overview paragraph can be independently hidden via backend config; per-section insights still render | Phase 65 D-18: `INSIGHTS_HIDE_OVERVIEW=true` sets `report.overview=""` — FE treats empty string as "hide section" |
</phase_requirements>

---

## Summary

Phase 66 is a largely frontend phase with one small backend migration. The LLM endpoint shipped fully in Phase 65 (verified: 5/5 truths, 1018 tests passing). This phase wires the frontend to consume it and gates the feature behind a `users.beta_enabled` flag.

The backend work is minimal: add one column (`users.beta_enabled BOOLEAN NOT NULL DEFAULT false`) via Alembic autogenerate, extend `UserProfileResponse` with `beta_enabled: bool`, expose it on `/users/me/profile`, and extend the `UserProfile` TypeScript interface. The entire backend delta is about 10 lines of code plus one migration file.

The frontend work is the substantive deliverable: a new `useEndgameInsights` mutation hook, a new `EndgameInsightsBlock` component (self-gating on `beta_enabled`), 4 `SectionInsight` slots interleaved into existing H2 groups in `Endgames.tsx`, and a TS type file for the insights API shapes. The UI-SPEC has locked every visual detail (typography, spacing, skeleton, testids, copy) so the planner has no design decisions left to make.

**Primary recommendation:** Plan the phase as 3 waves — (1) backend column + schema extension + migration, (2) TS types + hook + component skeleton, (3) Endgames.tsx integration + per-section slots + full testid wiring. The backend wave is tiny and can ship in the same plan as the TS types wave.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Beta flag storage | Database / Storage | — | BOOLEAN column on `users` table, enforced at DB level with `NOT NULL DEFAULT false` |
| Beta flag exposure | API / Backend | — | `/users/me/profile` router extends `UserProfileResponse`; no new endpoint |
| Beta flag gating | Browser / Client | — | `EndgameInsightsBlock` reads `useUserProfile()`, returns null when not beta-enabled |
| LLM API call | Browser / Client (via axios) | API / Backend (Phase 65) | `useMutation` POSTs to the already-shipped `/api/insights/endgame` |
| Filter serialization | Browser / Client | — | Extended `buildFilterParams` (in `client.ts`) serializes `FilterState` to query params |
| Outdated indicator | Browser / Client | — | Pure component state: compare `appliedFilters` vs `reportFilters` |
| Error capture | Browser / Client | — | Global `MutationCache.onError` in `queryClient.ts` — do NOT duplicate in component |
| Alembic migration | Database / Storage | — | Standard `op.add_column` on `users`; autogenerate + hand-verify |

---

## Existing Patterns to Mirror

### useMutation Template

**File:** `frontend/src/hooks/useImport.ts`, lines 24–31 [VERIFIED: live codebase]

```typescript
export function useImportTrigger() {
  return useMutation<ImportStartedResponse, Error, ImportRequest>({
    mutationFn: async (request: ImportRequest) => {
      const response = await apiClient.post<ImportStartedResponse>('/imports', request);
      return response.data;
    },
  });
}
```

`useEndgameInsights` mirrors this exactly: `useMutation<EndgameInsightsResponse, AxiosError<InsightsErrorResponse>, FilterState>`. The `mutationFn` calls `apiClient.post('/insights/endgame', null, { params })` where `params` is built via a filter-params builder that includes `color`.

**Important:** `apiClient` (not `endgameApi`) is the right import because this is a POST with query-string params, not a GET. `endgameApi` only wraps GET endpoints.

### Filter Serialization

**File:** `frontend/src/api/client.ts`, lines 66–85 [VERIFIED: live codebase]

`buildFilterParams` is a module-private function in `client.ts`. It is NOT exported. The insights hook cannot import it directly. Two options for the planner:

1. **Export `buildFilterParams` from `client.ts`** and import in `useEndgameInsights.ts`. This is the cleanest approach given Phase 65 D-31 explicitly says the insights endpoint shares this convention.
2. **Duplicate the serialization logic** in `useEndgameInsights.ts`. Less clean.

**Recommendation:** Export `buildFilterParams` from `client.ts` and use it in the insights hook with `color` appended separately.

**VERIFIED query param names** from `app/routers/insights.py` (read directly): [VERIFIED: live codebase]

The insights router uses **the same param names as the endgame endpoint**: `time_control` (singular), `platform` (singular), `rated` (bool). It also accepts `color` (str) which the endgame endpoint does NOT. The router maps them to `FilterContext` internally:

```python
filter_context = FilterContext(
    recency=recency,
    opponent_strength=opponent_strength,
    color=color,
    time_controls=time_control or [],   # singular query param → plural field
    platforms=platform or [],           # singular query param → plural field
    rated_only=bool(rated) if rated is not None else False,  # rated → rated_only
)
```

**Implication for `buildFilterParams`:** The existing function already handles `time_control`, `platform`, `recency`, `rated`, `opponent_type`, `opponent_strength`. The insights hook only needs to append `color` from `FilterState.color`. No new `buildInsightsFilterParams` function is needed — extend the existing call with `{ ...buildFilterParams(filters), color: filters.color }` (or export `buildFilterParams` and compose).

**FilterState field → query param mapping for insights:**
- `FilterState.timeControls` → `time_control` (same as endgame)
- `FilterState.platforms` → `platform` (same as endgame)
- `FilterState.opponentStrength` → `opponent_strength` (same as endgame)
- `FilterState.rated` → `rated` (same as endgame)
- `FilterState.color` → `color` (NEW — not in existing `buildFilterParams`)
- `FilterState.recency` → `recency` (same as endgame)

### useUserProfile

**File:** `frontend/src/hooks/useUserProfile.ts` [VERIFIED: live codebase]

```typescript
export function useUserProfile() {
  return useQuery<UserProfile>({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await apiClient.get<UserProfile>('/users/me/profile');
      return res.data;
    },
    staleTime: 300_000, // 5 minutes
  });
}
```

No changes to this hook. `EndgameInsightsBlock` calls `useUserProfile()` and reads `profile?.beta_enabled`. Since `staleTime` is 5 minutes, the first render after login will have the value; the component should treat `profile === undefined` (loading) as non-beta (return null) per D-17.

### useFilterStore and appliedFilters

**File:** `frontend/src/hooks/useFilterStore.ts` [VERIFIED: live codebase]

`useFilterStore()` returns `[FilterState, setter]` via `useSyncExternalStore`. This is a module-level shared store — the SAME `appliedFilters` object that `useEndgameOverview` keys its query on.

In `Endgames.tsx` line 69: `const [appliedFilters, setAppliedFilters] = useFilterStore();`

`EndgameInsightsBlock` receives `appliedFilters` as a prop (or calls `useFilterStore()` itself). The outdated indicator compares `appliedFilters` (current committed filters) against `reportFilters` (the filter state at time of last Generate click).

`areFiltersEqual` is exported from `FilterPanel.tsx` and accepts an optional `fields` array for partial comparison. For the insights outdated indicator, compare ALL fields in `FilterState` (no field restriction). **CONTEXT.md D-08 says any `appliedFilters` change lights the indicator**, so compare all fields including `color`.

### Endgames.tsx H2 Structure and statisticsContent

**File:** `frontend/src/pages/Endgames.tsx`, lines 219–383 [VERIFIED: live codebase]

```
statisticsContent = (
  <div className="flex flex-col gap-4">
    {overviewLoading ? ... : statsData?.categories.length > 0 ? (
      <>
        {/* H2 #1: Endgame Overall Performance — line 230 */}
        {showPerfSection && (
          <>
            <h2 className="text-lg font-semibold text-foreground mt-2">Endgame Overall Performance</h2>
            <Accordion>...</Accordion>           {/* Concepts explainer — lines 231-277 */}
            <div className="charcoal-texture rounded-md p-4">  {/* first chart card — line 278 */}

        {/* H2 #2: Endgame Metrics and ELO — line 291 */}
        {scoreGapData && (
          <>
            <h2 ...>Endgame Metrics and ELO</h2>

        {/* H2 #3: Time Pressure — line 313 */}
        {(showClockPressure || showTimePressureChart) && (
          <>
            <h2 ...>Time Pressure</h2>

        {/* H2 #4: Endgame Type Breakdown — line 338 */}
        <h2 ...>Endgame Type Breakdown</h2>
      </>
    ) : overviewError ? (
      {/* Error state — lines 357-362 */}
    ) : statsData?.categories.length === 0 ? (
      {/* Empty state — lines 363-370 */}
    ) : (
      {/* No games state — lines 371-381 */}
    )}
  </div>
);
```

**Key integration detail for H2 #1 (overall):** The SectionInsight slot for `overall` must go AFTER the `<Accordion>` (concepts explainer) and BEFORE the first `<div className="charcoal-texture rounded-md p-4">`. The accordion is at lines 231–277. This is what UI-SPEC §"Per-section slot placement" specifies: "Order relative to the existing Accordion concepts panel at :231-277: slot goes BELOW the Accordion (after it closes), above the first chart card."

**H2 #2 (metrics_elo)** is nested inside `{scoreGapData && (<>...`). The SectionInsight slot is conditional on that same guard — only renders when `scoreGapData` exists and the H2 renders.

**H2 #3 (time_pressure)** is inside `{(showClockPressure || showTimePressureChart) && (<>...`). SectionInsight for `time_pressure` drops when this guard is false (D-05).

**H2 #4 (type_breakdown)** is ALWAYS rendered when `statsData?.categories.length > 0`. The section is not guarded by an additional condition.

**Where EndgameInsightsBlock mounts:** At the very top of `statisticsContent`, BEFORE the `{overviewLoading ? ... }` ternary — the block self-gates to null for non-beta users so the surrounding ternary is unaffected.

### Existing Error State Pattern

**File:** `frontend/src/pages/Endgames.tsx`, lines 356–362 [VERIFIED: live codebase]

```tsx
) : overviewError ? (
  <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
    <p className="mb-2 text-base font-medium text-foreground">Failed to load endgame data</p>
    <p className="text-sm text-muted-foreground">
      Something went wrong. Please try again in a moment.
    </p>
  </div>
```

The `EndgameInsightsBlock` error state uses the same typography pattern (`text-base font-medium text-foreground` headline + `text-sm text-muted-foreground` body) but renders inside the top card, not full-page. The locked copy splits into: "Couldn't generate insights." (headline) + "Please try again in a moment." (body) + optional "Try again in ~{N} min." (429 only).

### Global Sentry Mutation Capture

**File:** `frontend/src/lib/queryClient.ts`, lines 13–20 [VERIFIED: live codebase]

```typescript
mutationCache: new MutationCache({
  onError: (error, _variables, _context, mutation) => {
    Sentry.captureException(error, {
      tags: { source: 'tanstack-mutation' },
      extra: { mutationKey: mutation.options.mutationKey },
    });
  },
}),
```

**CRITICAL: DO NOT add `Sentry.captureException` inside `EndgameInsightsBlock` or `useEndgameInsights`.** Every `useMutation` error is captured here automatically. Double-capturing fragments Sentry grouping and creates duplicate issues.

### UserProfileResponse Backend Extension

**File:** `app/schemas/users.py` [VERIFIED: live codebase]

Current `UserProfileResponse` fields: `email`, `is_superuser`, `is_guest`, `chess_com_username`, `lichess_username`, `created_at`, `last_login`, `chess_com_game_count`, `lichess_game_count`, `impersonation`. Add `beta_enabled: bool` as the last field.

**File:** `app/routers/users.py`, lines 70–83 [VERIFIED: live codebase]

The `get_profile` handler returns `UserProfileResponse(email=user.email, is_superuser=user.is_superuser, is_guest=user.is_guest, ...)`. Add `beta_enabled=user.beta_enabled` to the constructor call. The `update_profile` handler at lines 95–106 also constructs a `UserProfileResponse` — add `beta_enabled=updated.beta_enabled` there too.

### User Model Extension

**File:** `app/models/user.py` [VERIFIED: live codebase]

Existing pattern for boolean columns (line 31):
```python
is_guest: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
```

The `beta_enabled` column follows the identical pattern:
```python
beta_enabled: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    server_default=sa.text("false"),
    default=False,
)
```

Note: `is_guest` uses `text("false")` without `sa.`. Both work. Use `sa.text("false")` for consistency with the Alembic migration body.

`Boolean` must be imported from `sqlalchemy` — the existing `String`, `DateTime`, etc. come from `from sqlalchemy import ...` so add `Boolean` to that import.

### Alembic Migration Pattern

**File:** `alembic/versions/20260420_211450_85dfef624a19_create_llm_logs.py` [VERIFIED: live codebase]

The standard pattern for a new column addition (simpler than table creation):

```python
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("beta_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

def downgrade() -> None:
    op.drop_column("users", "beta_enabled")
```

**Autogenerate workflow:**
1. Add `beta_enabled` to `User` model in `app/models/user.py`
2. Run `uv run alembic revision --autogenerate -m "add users.beta_enabled"`
3. Inspect generated file — autogenerate correctly detects new columns with `server_default`
4. Apply with `uv run alembic upgrade head`

No JSONB, no DESC indexes, no complex types: autogenerate will produce a correct migration without hand-editing.

---

## API Contract Summary (from Phase 65)

### Endpoint

`POST /api/insights/endgame` — registered at `app/routers/insights.py` [VERIFIED: live codebase + 65-VERIFICATION.md]

**Query parameters** (verified directly from `app/routers/insights.py`):

| Query param | Type | Default | Notes |
|-------------|------|---------|-------|
| `time_control` | `list[str] \| None` | `None` | Singular — same as endgame endpoint |
| `platform` | `list[str] \| None` | `None` | Singular — same as endgame endpoint |
| `recency` | `str` | `"all_time"` | Same as endgame endpoint |
| `rated` | `bool \| None` | `None` | Same as endgame endpoint |
| `opponent_strength` | `str` | `"any"` | Same as endgame endpoint |
| `color` | `str` | `"all"` | NEW — not in endgame endpoint |

**The existing `buildFilterParams` handles 5 of 6 params already.** Only `color` is missing. The insights hook extends the call: `{ ...buildFilterParams(filters), color: filters.color }`.

**Note on opponent_type:** The insights router does NOT expose `opponent_type` as a query param (unlike the endgame endpoint). The service hardcodes `opponent_type="human"` internally. Do NOT pass `opponent_type` in the insights POST.

### Success Envelope (HTTP 200)

```typescript
interface EndgameInsightsResponse {
  report: EndgameInsightsReport;
  status: "fresh" | "cache_hit" | "stale_rate_limited";
  stale_filters: FilterContext | null;  // only when status=="stale_rate_limited"
}

interface EndgameInsightsReport {
  overview: string;       // always non-empty from LLM; empty string="" when INSIGHTS_HIDE_OVERVIEW=true
  sections: SectionInsight[];  // min 1, max 4
  model_used: string;     // FE ignores/hides from users
  prompt_version: string; // FE ignores/hides from users
}

interface SectionInsight {
  section_id: "overall" | "metrics_elo" | "time_pressure" | "type_breakdown";
  headline: string;   // ≤120 chars (~12 words)
  bullets: string[];  // 0–2 items, each ≤200 chars (~20 words)
}
```

### Error Envelope (HTTP 429 / 502 / 503)

```typescript
interface InsightsErrorResponse {
  error: "rate_limit_exceeded" | "provider_error" | "validation_failure" | "config_error";
  retry_after_seconds: number | null;  // only for 429
}
```

### HTTP Status Mapping

| Status | Condition | Body |
|--------|-----------|------|
| 200 | fresh, cache_hit, or stale_rate_limited | `EndgameInsightsResponse` |
| 429 | Rate limit hit AND no stale fallback | `InsightsErrorResponse(error="rate_limit_exceeded")` |
| 502 | Provider error or structured output validation failure | `InsightsErrorResponse(error="provider_error" or "validation_failure")` |
| 503 | Config error (startup-validated, should not reach prod) | `InsightsErrorResponse(error="config_error")` |

### BETA-02: Overview-Hide Semantics

When `INSIGHTS_HIDE_OVERVIEW=true` (backend env var), the service sets `report.overview = ""` before returning HTTP 200. FE must treat `overview === ""` as "hide section" — render the top card with the H2 + Regenerate button but no overview paragraph. The section slots render normally.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 66 |
|-----------|-------------------|
| `data-testid` on every interactive element | 13 testids locked in UI-SPEC. Also add to `EndgameInsightsBlock`'s container in `Endgames.tsx` mount point if it wraps in a div. |
| `variant="default"` for primary CTAs | Generate + Regenerate buttons |
| `variant="brand-outline"` for secondary/error CTAs | [Try again] button on error state |
| Theme constants in `theme.ts` | Outdated indicator dot reuses `FILTER_MODIFIED_DOT` from `theme.ts` (already exists). No new theme constants needed this phase. |
| `noUncheckedIndexedAccess` | `sections` array access must be narrowed: `const s = sections[i]; if (s) { ... }`. `section_id` lookup on the sections array requires safe access. |
| `Literal[...]` types on status/error fields | TS types must use `"fresh" \| "cache_hit" \| "stale_rate_limited"` not `string` |
| No `Sentry.captureException` in components using `useMutation` | Global `MutationCache.onError` in `queryClient.ts` handles it |
| Always handle `isError` in data-loading ternaries | `EndgameInsightsBlock` mutation error state (D-11) is the `isError` branch |
| Mobile-friendly; apply changes to mobile too | UI-SPEC: no mobile-specific deviations; block inherits existing Endgame tab patterns. No separate mobile section in `Endgames.tsx` for this block. |
| Semantic HTML — `<button>` not `<div onClick>` | Already handled by `Button` component |
| ARIA labels on icon-only buttons | All three buttons (Generate, Regenerate, Try again) have visible text; no `aria-label` needed. Outdated indicator gets `role="status"`. Error container gets `role="alert"`. |
| `ty check` must pass with zero errors | Add return type annotations to all new functions. `beta_enabled: bool` on `UserProfileResponse` uses `bool`, not `Optional[bool]` — it is NOT NULL in the DB. |
| `Knip` runs in CI | All new exports must be imported somewhere. `EndgameInsightsBlock` must be imported in `Endgames.tsx`. `useEndgameInsights` must be imported in `EndgameInsightsBlock`. Any split sub-components must be imported too. |

---

## Standard Stack

No new libraries. Phase 66 uses only existing dependencies.

| Tool | Already in Codebase | Usage |
|------|---------------------|-------|
| `@tanstack/react-query` v5.90 | Yes | `useMutation` for insights POST |
| `axios` v1.15 | Yes | `apiClient.post` in mutationFn |
| `lucide-react` v0.577 | Yes | `Info` icon (stale banner), `Loader2` (pending while re-generating) |
| SQLAlchemy 2.x async | Yes | `Mapped[bool] = mapped_column(Boolean, ...)` |
| Alembic | Yes | `op.add_column` migration |
| Pydantic v2 | Yes | `UserProfileResponse.beta_enabled: bool` |

---

## Architecture Patterns

### Hook + Component State Architecture

The planner must resolve the state-lifting question from "Claude's Discretion". Research supports this pattern:

**Option A: Mutation in `EndgameInsightsBlock`, section insights passed up via prop callback / context.**

`EndgameInsightsBlock` owns the mutation and rendered state. It needs to communicate per-section insights (`SectionInsight[]`) to the 4 H2 locations in `Endgames.tsx`. Options:
- Render prop: `EndgameInsightsBlock` accepts `onReport?: (sections: SectionInsight[]) => void` and calls it after `mutateAsync` resolves. `Endgames.tsx` lifts this into state.
- React context: `EndgameInsightsBlock` wraps in a context provider that section components read.

**Option B: Mutation in `Endgames.tsx`, passed down as props.**

`Endgames.tsx` calls `useEndgameInsights()` at the top level and passes `sections`, `isPending`, `isError`, `handleGenerate` as props to `EndgameInsightsBlock`. Per-section slots get `sections` directly. This requires `Endgames.tsx` to import the hook and adds coupling, but is the simplest data flow.

**Recommendation:** Option B (lift to `Endgames.tsx`) because:
1. `Endgames.tsx` already owns all the existing H2 guards (`showPerfSection`, `showClockPressure`, etc.). It naturally owns the per-section slot visibility too.
2. Avoids a context provider or render-prop indirection.
3. The beta-gating `if (!profile?.beta_enabled) return null` can still live in `EndgameInsightsBlock` (the top-card component). `Endgames.tsx` still calls the hook unconditionally but sections array is null/empty until Generate is clicked.

The planner may choose either option — both are valid. Document the choice in the plan.

### New Files to Create

```
frontend/src/
├── types/
│   └── insights.ts                          # TS interfaces: EndgameInsightsResponse, EndgameInsightsReport,
│                                            #   SectionInsight, InsightsErrorResponse
├── hooks/
│   └── useEndgameInsights.ts               # useMutation wrapping POST /api/insights/endgame
└── components/
    └── insights/
        └── EndgameInsightsBlock.tsx         # Top-card hero → loading → overview/regenerate → error

app/
├── models/user.py                          # +beta_enabled column
├── schemas/users.py                        # +UserProfileResponse.beta_enabled
└── routers/users.py                        # +beta_enabled=user.beta_enabled in both handlers

alembic/versions/
└── YYYYMMDD_HHMMSS_XXXX_add_users_beta_enabled.py
```

---

## Common Pitfalls

### Pitfall 1: Passing `opponent_type` to the Insights Endpoint

**What goes wrong:** The `buildFilterParams` function includes `opponent_type` when it is non-default. The insights router does NOT accept `opponent_type` as a query param (unlike the endgame router). Passing it will cause a FastAPI 422 Unprocessable Entity or silently be ignored depending on FastAPI's `extra = "ignore"` settings.

**Why it happens:** Natural copy of the endgame endpoint call pattern.

**How to avoid:** Do NOT include `opponent_type` in the insights params. The service hardcodes `opponent_type="human"` internally. The insights hook should use `buildFilterParams` with the `opponent_type` field excluded (or build the params object directly without that field).

**Warning signs:** 422 responses when `opponentType` is "human" (the default) — the field is omitted by `buildFilterParams` when it matches default, so this only surfaces with non-default `opponentType`. More specifically, when `opponentType !== "human"`, `buildFilterParams` would add `opponent_type` to the params, causing a 422.

### Pitfall 2: Double Sentry Capture

**What goes wrong:** Developer adds `Sentry.captureException(error)` inside `useEndgameInsights` or `EndgameInsightsBlock` catch block, creating duplicate Sentry issues for every mutation failure.

**Why it happens:** It's a natural instinct to capture errors where they occur. But `MutationCache.onError` in `queryClient.ts` ALREADY captures ALL mutation errors globally.

**How to avoid:** Trust the global handler. The component's `isError` branch renders the failure UI (D-11) without any Sentry call.

### Pitfall 3: noUncheckedIndexedAccess on sections Array

**What goes wrong:** `report.sections[0].section_id` fails TypeScript because `noUncheckedIndexedAccess` makes indexed access return `SectionInsight | undefined`.

**Why it happens:** `tsconfig.json` has `"noUncheckedIndexedAccess": true`. Array index access returns `T | undefined`.

**How to avoid:** Use `report.sections.find(s => s.section_id === "overall")` (safe, returns `undefined` gracefully) instead of index access. Or: `const s = report.sections[0]; if (!s) return null;`.

### Pitfall 4: Beta-Enabled Flash of Content

**What goes wrong:** On initial mount, `useUserProfile()` returns `{ data: undefined, isLoading: true }`. If the component renders anything before the profile query resolves, non-beta users see a flash of the insights block.

**Why it happens:** `useQuery` is async; the first render happens before the profile data arrives.

**How to avoid:** `if (!profile?.beta_enabled) return null;` — this returns null both when `profile` is undefined (loading) and when `profile.beta_enabled` is `false`. D-17 explicitly specifies this behaviour.

### Pitfall 5: appliedFilters Equality for Outdated Detection

**What goes wrong:** The outdated indicator never lights or always lights.

**Why it happens:** `useFilterStore` uses `useSyncExternalStore` with a module-level object. `FilterState` contains arrays (`timeControls`, `platforms`), so reference equality is NOT sufficient for "are these the same filters?" — two objects can have the same array contents but different references.

**How to avoid:** Use `areFiltersEqual(reportFilters, appliedFilters)` (imported from `FilterPanel.tsx`) for equality comparison. Store `reportFilters` as a snapshot of `appliedFilters` at the time of Generate click. `areFiltersEqual` handles array set-equality correctly.

### Pitfall 6: is_guest Users and the Insights Block

**What goes wrong:** Guest users (anonymous accounts) have `beta_enabled: false` (the default). The block correctly shows nothing for them. No action needed; noting for clarity.

**Why it happens:** `users.beta_enabled` defaults to `false` for ALL users including guests.

**How to avoid:** No action needed. The default `false` ensures guests never see the block unless manually enabled via direct DB operation.

### Pitfall 7: Knip Dead Export Detection

**What goes wrong:** CI fails with "unused export" if any export from the new files is not imported elsewhere.

**Why it happens:** `knip` runs in CI and detects unused exports across the project.

**How to avoid:** Every exported symbol from `types/insights.ts`, `hooks/useEndgameInsights.ts`, and `components/insights/EndgameInsightsBlock.tsx` must be imported somewhere in production code. If a type is only used internally, don't export it. The plan should track which exports are consumed.

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio |
| Backend config | `pyproject.toml` [tool.pytest] section + `tests/conftest.py` |
| Backend quick run | `uv run pytest tests/test_users_router.py -x -q` |
| Backend full suite | `uv run pytest -q` |
| Frontend framework | Vitest v4.1 |
| Frontend config | `vite.config.ts` (vitest config embedded) |
| Frontend quick run | `npm test` (runs `vitest run`) |
| Frontend full suite | `npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BETA-01 | `users.beta_enabled` column exists with correct type/default | Backend integration | `uv run pytest tests/test_users_router.py -x -q` | Partially — `/me/profile` tests exist; extend for `beta_enabled` field |
| BETA-01 | `/users/me/profile` returns `beta_enabled: false` by default | Backend integration | `uv run pytest tests/test_users_router.py::test_get_profile_beta_enabled_default -x` | No — Wave 0 gap |
| BETA-02 | `overview=""` when `INSIGHTS_HIDE_OVERVIEW=true`; sections still render | Backend unit | Already covered by Phase 65 `test_insights_llm.py` | Yes (Phase 65) |
| INS-01 | Beta user sees Generate button; non-beta user sees nothing | Frontend unit (Vitest) | `npm test` | No — Wave 0 gap; requires `@testing-library/react` |
| INS-02 | Post-click renders overview + up to 4 section blocks | Frontend unit | `npm test` | No — Wave 0 gap |
| INS-03 | Filter change lights outdated indicator; regenerating produces new report | Frontend unit (state simulation) | `npm test` | No — Wave 0 gap |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_users_router.py -x -q` (backend) + `npm test` (frontend)
- **Per wave merge:** `uv run pytest -q` + `npm test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_users_router.py` — add `test_get_profile_beta_enabled_default` asserting `beta_enabled: False` in the response
- [ ] `tests/test_users_router.py` — add `test_get_profile_beta_enabled_true` using a user with `beta_enabled=True` set in the DB via session update
- [ ] `frontend/src/components/insights/EndgameInsightsBlock.test.tsx` — Vitest render tests (requires `@testing-library/react` — NOT currently installed)
- [ ] `frontend/src/hooks/useEndgameInsights.test.ts` — unit test for query param serialization

**Frontend testing note:** `@testing-library/react` is NOT installed (confirmed by checking `frontend/package.json`). The planner must decide: install `@testing-library/react` + `@testing-library/user-event` to enable FE render tests in this phase, or defer FE render tests to Phase 67. The backend tests (BETA-01 router tests) have no dependency gaps.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Filter equality comparison | Custom deep-equal | `areFiltersEqual` from `FilterPanel.tsx` | Already handles array set-equality; already tested |
| Profile query | New `useQuery` for beta flag | Extend `useUserProfile()` response | No new network request; 5-minute staleTime is fine |
| Shimmer skeleton | Custom CSS animation | Tailwind `animate-pulse` + `bg-muted/30` | Already in codebase; UI-SPEC specifies this pattern |
| Error capture | `Sentry.captureException` in component | `MutationCache.onError` in `queryClient.ts` | Already captures all mutation failures globally |
| Minute rounding | Custom math | `max(1, Math.ceil(retry_after_seconds / 60))` | Locked formula (D-14, UI-SPEC) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `boolean` Pydantic field with `Optional` default | `bool` field with non-null default + `server_default` | SQLAlchemy 2.x / Pydantic v2 | `UserProfileResponse.beta_enabled: bool` (not `bool \| None`) because the column is NOT NULL |
| `useQuery` for mutations | `useMutation` from TanStack Query v5 | TanStack Query v5 | `useMutation` returns `{ mutate, mutateAsync, isPending, isError, data, error }` — no `isLoading` (use `isPending`) |

**TanStack Query v5 naming change:** `isLoading` was renamed to `isPending` for mutations in v5. Do NOT use `mutation.isLoading` — it does not exist. Use `mutation.isPending`. [ASSUMED — consistent with @tanstack/react-query v5.90 installed in the project; this is a well-known v5 breaking change.]

---

## Environment Availability

Phase 66 has no new external dependencies. All required tools are confirmed available:

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| PostgreSQL (Docker) | Alembic migration | Available (Docker Compose) | Run `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` before migration |
| `uv` | Backend dev | Available | Project uses `uv sync` |
| `npm` | Frontend dev | Available | `frontend/package.json` present |
| Phase 65 endpoint | FE hook | Available | Verified shipped: `['/api/insights/endgame']` confirmed in 65-VERIFICATION.md |
| `@testing-library/react` | FE render tests | NOT INSTALLED | Not in `frontend/package.json` devDependencies — planner must decide whether to add |

---

## Risks and Unknowns

### Risk 1: `opponent_type` Param Exclusion (RESOLVED)

**Status:** RESOLVED. The insights router (`app/routers/insights.py`) does NOT accept `opponent_type` as a query param. Confirmed by reading the router. The insights hook must NOT pass `opponent_type`. See Pitfall 1.

### Risk 2: `@testing-library/react` Not Installed (CONFIRMED)

**Status:** CONFIRMED absent. `grep "testing-library" frontend/package.json` returned nothing. Frontend render tests require installing this dependency. Planner decision: add to devDependencies this phase, or defer FE render tests to Phase 67.

### Risk 3: TS `AxiosError<InsightsErrorResponse>` Type

**Status:** LOW risk. `AxiosError` is the error type for axios-backed mutations. When the server returns a 429/502/503 JSON body (`InsightsErrorResponse`), `error.response?.data` contains it. The `error` type parameter in `useMutation<Success, Error, Variables>` should be `AxiosError<InsightsErrorResponse>`. Import: `import type { AxiosError } from 'axios'`. [VERIFIED: axios is `^1.15.0` in package.json; `AxiosError` is exported in all axios v1 versions.]

### Risk 4: State Lifting Architecture Decision

**Status:** LOW risk. The planner must choose between Option A (mutation in component) and Option B (mutation lifted to Endgames.tsx) from the Architecture Patterns section. Both are viable. The decision affects 4+ file integration points in Endgames.tsx. The plan should commit to one architecture and be internally consistent.

### Risk 5: seeded_user `beta_enabled` Variant

**Status:** LOW risk. Backend router tests for `/users/me/profile` returning `beta_enabled: True` need a user row with that flag set. Simplest approach: in the test body, `await session.execute(update(User).where(User.id == seeded_user.user_id).values(beta_enabled=True))` after the seeded_user fixture runs. No fixture modification needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `mutation.isPending` (not `mutation.isLoading`) is the correct TanStack Query v5 API for in-flight mutation state | State of the Art | Component uses wrong property, skeleton/button disabled logic broken |

**A2 (RESOLVED):** The insights router uses `time_control`, `platform`, `rated`, `color` as query param names — verified by reading `app/routers/insights.py` directly. The existing `buildFilterParams` covers 5 of 6; only `color` is new.

**A3 (CONFIRMED):** `@testing-library/react` is NOT installed — confirmed by running `grep "testing-library" frontend/package.json` (returned nothing). Frontend render tests require installing it.

**If this table has only one row (A1):** A2 and A3 were confirmed in-session. Only A1 remains — it concerns TanStack Query v5 API naming which is a well-known, stable change.

---

## Sources

### Primary (HIGH confidence)

All findings verified from live codebase files. No external documentation was required — the API contract comes from the Phase 65 codebase (shipped and verified), and all patterns come from existing source files.

- `frontend/src/hooks/useImport.ts` — `useMutation` template (lines 24–31)
- `frontend/src/hooks/useEndgames.ts` — filter param building pattern
- `frontend/src/hooks/useUserProfile.ts` — profile query pattern
- `frontend/src/pages/Endgames.tsx` — H2 structure, statisticsContent, error patterns
- `frontend/src/types/users.ts` — `UserProfile` interface (current shape)
- `frontend/src/lib/queryClient.ts` — global `MutationCache.onError` Sentry capture
- `frontend/src/lib/theme.ts` — `FILTER_MODIFIED_DOT` constant
- `frontend/src/hooks/useFilterStore.ts` — `appliedFilters` source
- `frontend/src/components/filters/FilterPanel.tsx` — `FilterState`, `areFiltersEqual`, `FILTER_DOT_FIELDS`
- `frontend/src/components/ui/button.tsx` — Button variants (`default`, `brand-outline`)
- `frontend/src/api/client.ts` — `apiClient`, `buildFilterParams` (private function), `paramsSerializer`
- `app/schemas/users.py` — `UserProfileResponse` current shape
- `app/models/user.py` — `User` model current shape
- `app/routers/users.py` — `/users/me/profile` handler (lines 56–83, 95–106)
- `app/routers/insights.py` — exact query param names, `FilterContext` mapping (VERIFIED)
- `app/schemas/insights.py` — `EndgameInsightsResponse`, `InsightsErrorResponse`, `SectionInsight`, `FilterContext` (Phase 65, verified)
- `alembic/versions/20260420_211450_85dfef624a19_create_llm_logs.py` — Alembic migration pattern
- `.planning/phases/65-llm-endpoint-with-pydantic-ai-agent/65-VERIFICATION.md` — Phase 65 confirmed shipped (5/5 truths)
- `.planning/phases/66-frontend-endgameinsightsblock-beta-flag/66-CONTEXT.md` — all 19 locked decisions
- `.planning/phases/66-frontend-endgameinsightsblock-beta-flag/66-UI-SPEC.md` — all visual/copy details

---

## Metadata

**Confidence breakdown:**
- API Contract: HIGH — Phase 65 shipped and verified; router read directly (param names confirmed)
- Backend Extension: HIGH — User model and UserProfileResponse patterns read from live codebase
- Frontend Patterns: HIGH — all hook/component patterns read from live codebase
- Test Architecture: HIGH — vitest installed; `@testing-library/react` absence confirmed
- Filter Serialization: HIGH — router Query() annotations verified directly

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (stable codebase; patterns won't change in 30 days)
