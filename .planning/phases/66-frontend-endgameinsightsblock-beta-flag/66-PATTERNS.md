# Phase 66: Frontend EndgameInsightsBlock & Beta Flag - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/types/insights.ts` | types | — | `frontend/src/types/users.ts` | role-match |
| `frontend/src/hooks/useEndgameInsights.ts` | hook | mutation (POST) | `frontend/src/hooks/useImport.ts:24-31` | exact |
| `frontend/src/components/insights/EndgameInsightsBlock.tsx` | component | reads profile + mutation result | `frontend/src/components/admin/ImpersonationPill.tsx` (self-gate pattern) + `frontend/src/pages/Endgames.tsx:356-362` (error state pattern) | role-match |
| `frontend/src/types/users.ts` | types | — | self (extend in place) | exact |
| `frontend/src/pages/Endgames.tsx` | page | CRUD read + mutation integration | self (modify in place) | exact |
| `app/models/user.py` | model | — | self (extend in place, `is_guest` column as analog) | exact |
| `app/schemas/users.py` | schema | — | self (extend in place) | exact |
| `app/routers/users.py` | router | request-response | self (extend `get_profile` + `update_profile`) | exact |
| `alembic/versions/{rev}_add_users_beta_enabled.py` | migration | — | `alembic/versions/20260406_065527_68879c51818c_add_is_guest_to_users.py` | exact |
| `.planning/REQUIREMENTS.md` + `.planning/ROADMAP.md` | docs | — | — (text edit only) | — |

---

## Pattern Assignments

### `frontend/src/types/insights.ts` (types)

**Analog:** `frontend/src/types/users.ts` (Literal-typed interface with nullable fields)

**Imports pattern** (`frontend/src/types/users.ts` lines 1-1):
```typescript
import type { ImpersonationContext } from '@/types/admin';
```

**Core pattern** — Literal union types with no `string` fallback (`frontend/src/types/users.ts` lines 3-16):
```typescript
export interface UserProfile {
  email: string;
  is_superuser: boolean;
  is_guest: boolean;
  chess_com_username: string | null;
  lichess_username: string | null;
  // ...
  impersonation: ImpersonationContext | null;
}
```

**Concrete output for `insights.ts`** — mirror the backend `app/schemas/insights.py` Literal types exactly. The status and error fields on `EndgameInsightsResponse` and `InsightsErrorResponse` must be Literal unions, never bare `string`:
```typescript
// frontend/src/types/insights.ts
import type { AxiosError } from 'axios';

export type SectionId = 'overall' | 'metrics_elo' | 'time_pressure' | 'type_breakdown';
export type InsightsStatus = 'fresh' | 'cache_hit' | 'stale_rate_limited';
export type InsightsError = 'rate_limit_exceeded' | 'provider_error' | 'validation_failure' | 'config_error';

export interface SectionInsight {
  section_id: SectionId;
  headline: string;
  bullets: string[];
}

export interface EndgameInsightsReport {
  overview: string;           // empty string = hide per BETA-02 / Phase 65 D-18
  sections: SectionInsight[]; // min 1, max 4
  model_used: string;         // FE does not display; present for debug
  prompt_version: string;     // FE does not display; present for debug
}

export interface EndgameInsightsResponse {
  report: EndgameInsightsReport;
  status: InsightsStatus;
  stale_filters: null;        // FE ignores per D-13; field retained for future use
}

export interface InsightsErrorResponse {
  error: InsightsError;
  retry_after_seconds: number | null; // only for 429
}

export type InsightsAxiosError = AxiosError<InsightsErrorResponse>;
```

**Note:** `noUncheckedIndexedAccess` is enabled. Use `sections.find(s => s.section_id === 'overall')` instead of `sections[0]` when looking up by index.

---

### `frontend/src/hooks/useEndgameInsights.ts` (hook, mutation)

**Analog:** `frontend/src/hooks/useImport.ts:24-31` — `useImportTrigger` is the exact structural template.

**Full analog** (`frontend/src/hooks/useImport.ts` lines 23-31):
```typescript
/** Trigger a new import job. Returns ImportStartedResponse (with job_id). */
export function useImportTrigger() {
  return useMutation<ImportStartedResponse, Error, ImportRequest>({
    mutationFn: async (request: ImportRequest) => {
      const response = await apiClient.post<ImportStartedResponse>('/imports', request);
      return response.data;
    },
  });
}
```

**Filter serialization analog** (`frontend/src/api/client.ts` lines 66-85):
```typescript
function buildFilterParams(params: {
  time_control?: string[] | null;
  platform?: string[] | null;
  recency?: string | null;
  rated?: boolean | null;
  opponent_type?: string;
  opponent_strength?: string;
  window?: number;
}): Record<string, string | string[] | number | boolean> {
  const result: Record<string, string | string[] | number | boolean> = {};
  if (params.time_control) result.time_control = params.time_control;
  if (params.platform) result.platform = params.platform;
  if (params.recency && params.recency !== 'all') result.recency = params.recency;
  if (params.rated !== null && params.rated !== undefined) result.rated = params.rated;
  if (params.opponent_type && params.opponent_type !== 'all') result.opponent_type = params.opponent_type;
  if (params.opponent_strength && params.opponent_strength !== 'any') result.opponent_strength = params.opponent_strength;
  if (params.window) result.window = params.window;
  return result;
}
```

**Concrete output for `useEndgameInsights.ts`:**
```typescript
// frontend/src/hooks/useEndgameInsights.ts
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { buildFilterParams } from '@/api/client';  // must be exported first
import type { FilterState } from '@/components/filters/FilterPanel';
import type { EndgameInsightsResponse, InsightsAxiosError } from '@/types/insights';

export function useEndgameInsights() {
  return useMutation<EndgameInsightsResponse, InsightsAxiosError, FilterState>({
    mutationFn: async (filters: FilterState) => {
      const params = {
        ...buildFilterParams({
          time_control: filters.timeControls,
          platform: filters.platforms,
          recency: filters.recency,
          rated: filters.rated,
          // NO opponent_type — insights router does not accept it (Pitfall 1)
          opponent_strength: filters.opponentStrength,
        }),
        color: filters.color,   // NEW param not in buildFilterParams
      };
      const response = await apiClient.post<EndgameInsightsResponse>(
        '/insights/endgame',
        null,
        { params },
      );
      return response.data;
    },
  });
}
```

**Critical:** `buildFilterParams` is currently private (not exported) in `client.ts`. The planner must export it from `client.ts` before importing here. Do NOT pass `opponent_type` to the insights endpoint (see RESEARCH.md Pitfall 1 — the router does not accept it; only the endgame router does).

**TanStack Query v5:** use `isPending` (not `isLoading`) for mutation in-flight state. `isLoading` does not exist on mutations in v5.

---

### `frontend/src/components/insights/EndgameInsightsBlock.tsx` (component, mutation result + profile gate)

**Self-gate analog:** `frontend/src/components/admin/ImpersonationPill.tsx` — demonstrates reading a profile-derived value from a hook and returning early when the condition is not met (lines 24-26):
```tsx
export function ImpersonationPill({ impersonation, emailMaxWidthClass = 'max-w-[12rem]' }: Props) {
  const { logout } = useAuth();
  // component renders; caller passes impersonation only when truthy
```

For `EndgameInsightsBlock`, the gate lives inside the component, not in the caller (D-17). Pattern to mirror from `frontend/src/hooks/useUserProfile.ts` (lines 5-14) combined with an early return:
```typescript
const { data: profile } = useUserProfile();
if (!profile?.beta_enabled) return null;
// renders null both while loading (profile === undefined) and when beta_enabled === false
```

**Error state typography analog** (`frontend/src/pages/Endgames.tsx` lines 356-362):
```tsx
) : overviewError ? (
  <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
    <p className="mb-2 text-base font-medium text-foreground">Failed to load endgame data</p>
    <p className="text-sm text-muted-foreground">
      Something went wrong. Please try again in a moment.
    </p>
  </div>
```
The block error state uses the same type classes (`text-base font-medium text-foreground` headline + `text-sm text-muted-foreground` body) but renders inside the charcoal card, not full-page.

**theme.ts import for outdated indicator** (`frontend/src/lib/theme.ts` line 66):
```typescript
export const FILTER_MODIFIED_DOT = 'oklch(0.55 0.08 55)'; // brand brown mid
// Tailwind class equivalent: bg-brand-brown (applied via className)
```
The outdated indicator dot uses `className="size-1.5 rounded-full bg-brand-brown"` — no inline style, uses the CSS variable backed Tailwind utility.

**charcoal-texture card pattern** (from `frontend/src/pages/Endgames.tsx` lines 278, 292, etc.):
```tsx
<div className="charcoal-texture rounded-md p-4">
  {/* content */}
</div>
```
The top Insights card uses this exact class string.

**H2 pattern** (from `frontend/src/pages/Endgames.tsx` lines 230, 291, 313, 338):
```tsx
<h2 className="text-lg font-semibold text-foreground mt-2">Endgame Overall Performance</h2>
```
The "Insights" H2 copies this verbatim: `className="text-lg font-semibold text-foreground mt-2"`.

**Skeleton shimmer pattern** (existing Tailwind animate-pulse in project):
```tsx
<div className="animate-pulse">
  <div className="h-4 w-full bg-muted/30 rounded mb-2" />
  <div className="h-4 w-11/12 bg-muted/30 rounded mb-2" />
  <div className="h-4 w-3/4 bg-muted/30 rounded" />
</div>
```

**Button imports** (`frontend/src/components/ui/button.tsx` — existing):
```tsx
import { Button } from '@/components/ui/button';
// variant="default"       → Generate insights / Regenerate (primary CTA)
// variant="brand-outline" → Try again (secondary/error CTA)
```

**Sentry rule:** Do NOT call `Sentry.captureException` anywhere in this component or hook. The global `MutationCache.onError` in `frontend/src/lib/queryClient.ts` (lines 13-20) already captures all mutation errors:
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

---

### `frontend/src/types/users.ts` (types, extend in place)

**Analog:** self (current file lines 1-16):
```typescript
export interface UserProfile {
  email: string;
  is_superuser: boolean;
  is_guest: boolean;
  // ... existing fields ...
  impersonation: ImpersonationContext | null;
}
```

**Change:** append `beta_enabled: boolean` as the last field. Use `boolean` (not `boolean | null`) because the DB column is `NOT NULL DEFAULT false`.

---

### `frontend/src/pages/Endgames.tsx` (page, modify in place)

**Analog:** self (lines 219-383 — the full `statisticsContent` block). Key integration points:

**Mount point for `EndgameInsightsBlock`** — top of `statisticsContent`, before the `{overviewLoading ? ...}` ternary (line 221). The block self-gates to null for non-beta users, so no conditional wrapper needed in this file.

**Per-section slot placement** — inside each H2 group, immediately after the `<h2>` and before the first `<div className="charcoal-texture rounded-md p-4">`:

H2 #1 "Endgame Overall Performance" (line 230) — slot goes after the `</Accordion>` at line 277 and before the charcoal div at line 278:
```tsx
{/* SectionInsight slot for 'overall' */}
{sectionMap.get('overall') && (
  <div data-testid="insights-section-overall" className="mb-3">
    {/* headline + bullets */}
  </div>
)}
<div className="charcoal-texture rounded-md p-4">   {/* existing line 278 */}
```

H2 #2 "Endgame Metrics and ELO" (line 291) — slot after the H2 and before line 292's charcoal div. This H2 is nested inside `{scoreGapData && (<>...`).

H2 #3 "Time Pressure" (line 313) — slot after H2, inside `{(showClockPressure || showTimePressureChart) && (<>...`. SectionInsight dropped when this guard is false (D-05).

H2 #4 "Endgame Type Breakdown" (line 338) — slot after H2, before the charcoal div at line 339.

**Filter equality import** (from `frontend/src/components/filters/FilterPanel.tsx` lines 65-85):
```typescript
import { areFiltersEqual } from '@/components/filters/FilterPanel';
// Use: areFiltersEqual(reportFilters, appliedFilters) with no 3rd argument
// to compare ALL FilterState fields (D-08 — any change lights the indicator)
```

**Hook usage from `frontend/src/hooks/useFilterStore.ts`** (line 204 in Endgames.tsx):
```typescript
const [appliedFilters, setAppliedFilters] = useFilterStore();
```
If the planner lifts mutation state to Endgames.tsx (Option B from RESEARCH.md), the `useEndgameInsights()` hook call goes here alongside the existing `useFilterStore()` call.

---

### `app/models/user.py` (model, extend in place)

**Analog:** `is_guest` column (line 30):
```python
# Guest session flag — True for anonymous users created via POST /auth/guest/create
is_guest: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
```

**Change:** add `beta_enabled` column using the same pattern. Note that `text` is imported from `sqlalchemy` without the `sa.` prefix in this file; either form works, but the migration will use `sa.text()`:
```python
beta_enabled: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    server_default=sa.text("false"),
    default=False,
)
```

**Import change required:** add `Boolean` to the existing `from sqlalchemy import ...` import line (line 7 currently imports `DateTime, String, func, text`).

---

### `app/schemas/users.py` (schema, extend in place)

**Analog:** `impersonation` field (lines 22-24) — demonstrates how the last field added to `UserProfileResponse` looks:
```python
class UserProfileResponse(BaseModel):
    """Response for GET/PUT /users/me/profile."""
    email: str
    is_superuser: bool
    is_guest: bool
    # ... existing fields ...
    impersonation: ImpersonationContext | None = None
```

**Change:** append `beta_enabled: bool` as the last field (no default — it is `NOT NULL` in DB, always present):
```python
beta_enabled: bool
```

---

### `app/routers/users.py` (router, extend in place)

**Analog:** `get_profile` handler (lines 56-83) and `update_profile` handler (lines 86-106):

```python
@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(...) -> UserProfileResponse:
    profile = await user_repository.get_profile(session, user.id)
    counts = await game_repository.count_games_by_platform(session, user.id)
    return UserProfileResponse(
        email=user.email,
        is_superuser=user.is_superuser,
        is_guest=user.is_guest,
        chess_com_username=profile.chess_com_username,
        lichess_username=profile.lichess_username,
        created_at=profile.created_at,
        last_login=profile.last_login,
        chess_com_game_count=counts.get("chess.com", 0),
        lichess_game_count=counts.get("lichess", 0),
        impersonation=impersonation,
    )
```

**Change:** add `beta_enabled=user.beta_enabled` to the `UserProfileResponse(...)` constructor call in **both** `get_profile` (line 72-83) and `update_profile` (lines 95-106). In `update_profile`, the field is `updated.beta_enabled` since the `updated` object is the refreshed User row.

---

### `alembic/versions/{rev}_add_users_beta_enabled.py` (migration)

**Analog:** `alembic/versions/20260406_065527_68879c51818c_add_is_guest_to_users.py` — exact structural pattern for adding a boolean column to `users`.

**Key line from analog** (line 36):
```python
op.add_column('users', sa.Column('is_guest', sa.Boolean(), server_default=sa.text('false'), nullable=False))
```

**Concrete output for the new migration** (autogenerate, then verify):
```python
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("beta_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "beta_enabled")
```

**Workflow:** add `beta_enabled` column to `User` model first, then run `uv run alembic revision --autogenerate -m "add users.beta_enabled"`. Autogenerate will produce the correct `op.add_column` body (no indexes — D-18). Verify the generated file matches the above before applying.

---

## Shared Patterns

### Profile Query (useUserProfile)
**Source:** `frontend/src/hooks/useUserProfile.ts` (lines 1-14)
**Apply to:** `EndgameInsightsBlock.tsx`
```typescript
import { useUserProfile } from '@/hooks/useUserProfile';

// Inside component — gate on beta_enabled:
const { data: profile } = useUserProfile();
if (!profile?.beta_enabled) return null;
```
No changes to the hook itself. The 5-minute `staleTime` is acceptable for beta gating (D-17).

### Filter Equality
**Source:** `frontend/src/components/filters/FilterPanel.tsx` (lines 65-85)
**Apply to:** `EndgameInsightsBlock.tsx` (outdated indicator logic)
```typescript
import { areFiltersEqual } from '@/components/filters/FilterPanel';

// Compare ALL fields — no `fields` argument restriction (D-08):
const isOutdated = rendered !== null
  && reportFilters !== null
  && !areFiltersEqual(reportFilters, appliedFilters);
```

### charcoal-texture Card
**Source:** `frontend/src/pages/Endgames.tsx` (lines 278, 292, 316, 339, etc.)
**Apply to:** `EndgameInsightsBlock.tsx` top card
```tsx
<div className="charcoal-texture rounded-md p-4">
  {/* card content */}
</div>
```

### H2 Visual Pattern
**Source:** `frontend/src/pages/Endgames.tsx` (lines 230, 291, 313, 338)
**Apply to:** `EndgameInsightsBlock.tsx` "Insights" heading
```tsx
<h2 className="text-lg font-semibold text-foreground mt-2">Insights</h2>
```

### Boolean Column Pattern (SQLAlchemy 2.x)
**Source:** `app/models/user.py` line 30
**Apply to:** `app/models/user.py` new `beta_enabled` column
```python
is_guest: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
# New column follows same pattern with Boolean type explicit:
beta_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.text("false"), default=False)
```

### Alembic add_column for Boolean
**Source:** `alembic/versions/20260406_065527_68879c51818c_add_is_guest_to_users.py` line 36
**Apply to:** new migration
```python
op.add_column('users', sa.Column('beta_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False))
```

---

## No Analog Found

No files fall into this category. All files have a close match in the codebase.

| File | Role | Reason |
|------|------|---------|
| `frontend/src/components/insights/EndgameInsightsBlock.tsx` (self-gate aspect) | component | No existing component gates on `beta_enabled` — this establishes the first profile-flag gate. The self-gate pattern is assembled from `useUserProfile()` early-return + `ImpersonationPill.tsx` role-model for theme-import discipline. |

---

## Metadata

**Analog search scope:** `frontend/src/hooks/`, `frontend/src/types/`, `frontend/src/components/`, `frontend/src/pages/Endgames.tsx`, `frontend/src/api/client.ts`, `frontend/src/lib/theme.ts`, `app/models/user.py`, `app/schemas/users.py`, `app/routers/users.py`, `alembic/versions/`
**Files scanned:** 15 source files read directly
**Pattern extraction date:** 2026-04-21
