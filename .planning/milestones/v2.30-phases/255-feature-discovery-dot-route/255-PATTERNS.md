# Phase 255: Feature Discovery Dot Route - Pattern Map

**Mapped:** 2026-11-15
**Files analyzed:** 24 (new + modified)
**Analogs found:** 22 / 24

All analog paths below are git-tracked source (verified with `git ls-files`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/schemas/feature_route.py` (new) | schema/model | validation | `app/schemas/feedback_ask.py` | exact |
| `app/repositories/feature_route_repository.py` (new) | repository | CRUD (guarded JSONB UPDATE) | `app/repositories/feedback_ask_repository.py` | exact |
| `app/services/feature_route_service.py` (new) | service | request-response | `app/services/feedback_ask_service.py` | exact |
| `app/routers/users.py` (modify: POST `/me/feature-route`, profile field) | router | request-response | same file, `feedback_ask_action` lines 249-265, `_build_profile_response` 81-122 | exact |
| `app/schemas/users.py` (modify: `UserProfileResponse.feature_route`) | schema | request-response | same file, `feedback_ask: FeedbackAskView` field | exact |
| `alembic/versions/20261115_xxxxxx_<rev>_phase_255_feature_route_seed.py` (new, data-only) | migration | batch | `alembic/versions/20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py` (header/docstring style); head is `a7d2c9e1b254` (`20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py`) | role-match |
| `tests/test_feature_route.py` (new) | test | integration | `tests/test_feedback_ask.py` | exact |
| `tests/test_migration_255_feature_route_seed.py` (new) | test | migration | `tests/test_migration_240_reveal_tour_stage.py` | exact |
| `frontend/src/types/users.ts` (modify) | types | - | same file, `FeedbackAskAction`/`FeedbackAskView` mirrors | exact |
| `frontend/src/lib/featureRoute.ts` (new) | utility (pure registry + arbiter) | transform | `App.tsx` `useNavIndicators`/`isActive`/`isNavLocked` (lines 168-236) | role-match |
| `frontend/src/lib/__tests__/featureRoute.test.ts` (new) | test | unit | `frontend/src/lib/__tests__/retiredLocalStorage.test.ts` | role-match |
| `frontend/src/hooks/useFeatureRoute.ts` (new: `useRouteDot`, `useNavUnlocked`) | hook | read | `App.tsx` `useNavIndicators` (188-236), `MobileMoreDrawer` unlock (604-609) | role-match |
| `frontend/src/hooks/useRecordFeatureRoute.ts` (new) | hook | mutation | `frontend/src/hooks/useFeedbackAsk.ts` | exact |
| `frontend/src/components/featureRoute/RouteDot.tsx` (new) | component | render | `App.tsx` `NavDot` (238-249) | exact |
| `frontend/src/components/featureRoute/FeatureRouteRecorder.tsx` (new) | component (effects) | event-driven | `App.tsx` `ProtectedLayout` `setUserFlag` effects (750-766) | exact |
| `frontend/src/lib/retiredLocalStorage.ts` (modify: `removeRetiredDotKeys`) | utility | file-I/O (storage) | same file `removeRetiredBookmarkChartKeys` | exact |
| `frontend/src/lib/theme.ts` (modify: dot color constant) | config | - | `TOUR_SPOTLIGHT_CLASS` (~line 670) | exact |
| `frontend/src/App.tsx` (modify) | component | render | itself | - |
| `frontend/src/App.test.tsx` (rewrite 672-892) | test | component | itself | - |
| `frontend/src/pages/Openings.tsx`, `openings/useSidebarState.ts`, `openings/OpeningsDesktopSidebar.tsx`, `openings/OpeningsMobileBoardPanel.tsx` (modify) | component | event-driven | existing hint dots in those files (see RESEARCH Existing Code Map 2) | exact |
| `frontend/src/pages/library/LibraryPage.tsx` (modify: subtab dots) | component | render | `TabsTrigger` (already `relative`) + `RouteDot` | role-match |
| `frontend/src/pages/Train.tsx`, `components/train/TrainStartScreen.tsx`, `components/train/TrainSubnav.tsx` (modify) | component | event-driven | `Train.tsx:210` `onEnterLoop` seam; dot as boolean prop | role-match |
| `frontend/src/hooks/useUserFlag.ts` (delete) | - | - | - | - |
| Profile fixtures (`src/lib/impersonation.test.ts`, `LeaderboardPrivacyCard.test.tsx`, `FeedbackAskBubble.test.tsx`) | test | - | add `feature_route` field | - |

## Pattern Assignments

### `app/schemas/feature_route.py` (schema)

**Analog:** `app/schemas/feedback_ask.py` (56 lines)

Imports + constants (lines 11-27):
```python
import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

# Key of this ask inside users.prompt_state (a future ask adds another key).
FEEDBACK_ASK_ID: Final = "feedback_v1"
FEEDBACK_ASK_MIN_ACTIVE_DAYS: Final = 5
...
FeedbackAskAction = Literal["view", "snooze", "done"]
```
Stored-state model and request (lines 30-56):
```python
class FeedbackAskState(BaseModel):
    """Stored shape of ``users.prompt_state[FEEDBACK_ASK_ID]``."""
    # Catches a typo'd key written by the transition SQL.
    model_config = ConfigDict(extra="forbid")
    status: Literal["snoozed", "done"] | None = None
    ...
class FeedbackAskActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: FeedbackAskAction
```
Copy: `FEATURE_ROUTE_KEY: Final = "feature_route"`, `FEATURE_ROUTE_SKIP_ACTIVE_DAYS: Final = 3`, `FeatureRouteStepId` Literal (9 IDs), `FeatureRouteAction = Literal["current","done","skip"]`. Deviation (RESEARCH Pitfall 4): stored `steps` keyed `dict[str, FeatureRouteStepRecord]` (tolerant), request `step: FeatureRouteStepId` (strict). Full shape in RESEARCH "Backend schema (shape)".

---

### `app/repositories/feature_route_repository.py` (repository, guarded UPDATE)

**Analog:** `app/repositories/feedback_ask_repository.py` (188 lines)

Module docstring rules to copy nearly verbatim (lines 1-24): one guarded `UPDATE ... RETURNING`, every bind CAST-typed, dates as ISO strings, never bind `None`, `coalesce` every extracted value, no `jsonb_set`, only the own key replaced, never `session.commit()`.

Imports (26-39):
```python
import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
```

Guarded transition shape (`_DONE_SQL`, 98-107):
```python
_DONE_SQL = text(
    """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:ask_id AS text),
    coalesce(prompt_state->CAST(:ask_id AS text), '{}'::jsonb) || '{"status": "done"}'::jsonb)
WHERE id = :uid
  AND NOT is_guest
  AND prompt_state->CAST(:ask_id AS text)->>'status' IS DISTINCT FROM 'done'
RETURNING prompt_state->CAST(:ask_id AS text)
"""
)
```
DO NOT copy `AND NOT is_guest` (D-19). Nest the `steps` merge (Pitfall 2); target SQL for DONE/CURRENT/SKIP is in RESEARCH "Guarded transitions".

Re-read on no-op (`get_state`, 128-137) and transition runner (140-154):
```python
async def _run_transition(
    session: AsyncSession, statement: Any, params: dict[str, object]
) -> FeedbackAskState | None:
    result = await session.execute(statement, {"ask_id": FEEDBACK_ASK_ID, **params})
    row = result.first()
    if row is None:
        return None
    state = FeedbackAskState.model_validate(row[0])
    await session.flush()
    return state
```
Public functions follow `apply_view(session, *, user_id, today, active_days)` keyword-only style (157-188). Reuse `feedback_ask_repository.count_active_days_before` (110-125) rather than duplicating it (or move it to a shared spot, e.g. a `user_activity` repository, if the planner prefers; do not copy it).

---

### `app/services/feature_route_service.py` (service)

**Analog:** `app/services/feedback_ask_service.py` (202 lines)

Imports (13-30): `sentry_sdk`, `pydantic.ValidationError`, `AsyncSession`, `User`, repository module, schema constants.

Corrupt-state fail-closed (42-43, 75-90):
```python
class _CorruptAskStateError(Exception):
    """The stored ask state failed validation; callers fail closed (ask inactive)."""

def _capture_corrupt_state(user_id: int, exc: ValidationError) -> _CorruptAskStateError:
    sentry_sdk.set_context("feedback_ask", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    return _CorruptAskStateError()

def _stored_state(user: User) -> FeedbackAskState | None:
    raw = user.prompt_state.get(FEEDBACK_ASK_ID)
    if raw is None:
        return None
    try:
        return FeedbackAskState.model_validate(raw)
    except ValidationError as exc:
        raise _capture_corrupt_state(user.id, exc) from exc
```
Today-inclusive active days (93-103): `before + 1`.

Action routing via `match` (134-153) and the write path with no-op re-read + rollback on corrupt (156-202):
```python
    if user.is_guest or impersonated:
        return _INACTIVE  # route: keep ONLY `impersonated` (D-19)
    today = now_utc.date()
    active_days = await _count_active_days(session, user.id, today)
    try:
        state = await _transition(...)
        if state is None:
            state = await feedback_ask_repository.get_state(session, user_id=user.id)
    except ValidationError as exc:
        _capture_corrupt_state(user.id, exc)
        await session.rollback()
        return _INACTIVE
```
Profile-side snapshot: parse from `user.prompt_state` (already loaded, zero queries), returning `None` on corrupt; no active_days recompute needed (profile already has `ask.active_days`).

---

### `app/routers/users.py` (modify)

**Analog:** same file.
- Endpoint: copy `feedback_ask_action` (lines 249-265): `body`, `session`, `current_active_user`, `_get_impersonation_context`, `dev_now_utc` deps; `@router.post("/me/feature-route", response_model=FeatureRouteState)`; docstring "Always 200 and idempotent".
- Profile: add `feature_route=...` to `_build_profile_response` (104-122) only; GET and PUT both use it (docstring 89-94 warns about drift).

---

### `alembic/versions/..._phase_255_feature_route_seed.py` (data migration)

**Analog for header:** `alembic/versions/20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py` lines 1-35 (docstring explaining intent, `revision`/`down_revision` typed headers, `from alembic import op`, `import sqlalchemy as sa`). `down_revision = 'a7d2c9e1b254'` (re-check `uv run alembic heads` before merge, Pitfall 11). Body: RESEARCH Pattern 6 (hard-coded `_LAUNCH_STEP_IDS`, `WHERE NOT (prompt_state ? 'feature_route')`, downgrade `prompt_state - 'feature_route'`).

---

### `tests/test_feature_route.py`

**Analog:** `tests/test_feedback_ask.py`
- Module docstring on clock pinning (1-13): pin `dev_now_utc` before the real date so middleware rows fall outside the count; delete users in `finally`.
- Fixtures/helpers to copy (35-86): `NOW`, `TODAY`, `pin_now` fixture (`app.dependency_overrides[dev_now_utc] = lambda: now`), `_client()` via `httpx.ASGITransport`, `_register()` (register + jwt login), `_prior_days`, `_seed_activity` (`UserActivity` rows), `_prompt_state`, `_delete_user`.
- Test shape (89-103): `@pytest.mark.asyncio`, `try: ... finally: await _delete_user(user_id)`.
- Add a guest test (guest start endpoint) since route state must work for guests, and a `typing.get_args(FeatureRouteStepId)` drift test.

### `tests/test_migration_255_feature_route_seed.py`

**Analog:** `tests/test_migration_240_reveal_tour_stage.py`
- Constants (34-49): `TARGET_REVISION = "head"`, `BASE_REVISION = "<down_revision>"`, dedicated user-id range (pick unused, e.g. grep `999_` ranges; 999_5xx and 999_600-602 are taken).
- Alembic driver (54-77): `_make_alembic_cfg()`, `_run_upgrade`/`_run_downgrade` via `asyncio.to_thread(alembic_command.upgrade, cfg, revision)`.
- `_insert_user` raw SQL (107-116) with `ON CONFLICT (id) DO NOTHING`; add `is_guest` variant and a row with existing `feedback_v1` state.
- Always end at head.

---

### `frontend/src/hooks/useRecordFeatureRoute.ts` (mutation)

**Analog:** `frontend/src/hooks/useFeedbackAsk.ts` (54 lines)
```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { USER_PROFILE_QUERY_KEY } from '@/hooks/useUserProfile';

const FEEDBACK_ASK_MUTATION_SCOPE = 'feedback-ask';

function patchFeedbackAsk(queryClient, feedbackAsk): void {
  queryClient.setQueryData<UserProfile>(USER_PROFILE_QUERY_KEY, (profile) =>
    profile ? { ...profile, feedback_ask: feedbackAsk } : profile,
  );
}
export function useFeedbackAsk() {
  const queryClient = useQueryClient();
  return useMutation<FeedbackAskView, Error, FeedbackAskAction>({
    mutationFn: async (action) => (await apiClient.post<FeedbackAskView>('/users/me/feedback-ask', { action })).data,
    scope: { id: FEEDBACK_ASK_MUTATION_SCOPE },
    onMutate: async (action) => {
      await queryClient.cancelQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      patchFeedbackAsk(queryClient, { active: false });
    },
    onSuccess: (view) => patchFeedbackAsk(queryClient, view),
  });
}
```
Deviations: add a `mutationKey` and apply `onSuccess` only when `queryClient.isMutating({ mutationKey }) <= 1` (Pitfall 8); optimistic patch per action (Pattern 5). No Sentry call. Keep in its own module (Pitfall 9: App.test has no QueryClientProvider).

### `frontend/src/components/featureRoute/RouteDot.tsx`

**Analog:** `frontend/src/App.tsx` `NavDot` lines 238-249:
```tsx
function NavDot({ testid, mobile, ariaHidden }: { testid: string; mobile: boolean; ariaHidden?: boolean }) {
  return (
    <span
      className={mobile ? 'absolute top-1.5 right-[30%] flex h-2 w-2' : 'absolute top-0.5 right-0.5 flex h-2.5 w-2.5'}
      data-testid={testid}
      aria-hidden={ariaHidden || undefined}
    >
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
      <span className={cn('relative inline-flex rounded-full bg-red-500', mobile ? 'h-2 w-2' : 'h-2.5 w-2.5')} />
    </span>
  );
}
```
Generalize to `variant: 'nav' | 'nav-mobile' | 'inline'`, always `aria-hidden`, move `bg-red-500` into a `theme.ts` constant next to `TOUR_SPOTLIGHT_CLASS`. Replace the 5 hand-copied span pairs (App.tsx drawer 649-658, OpeningsDesktopSidebar 73-89/220-225, OpeningsMobileBoardPanel 148-156, Openings `mobileFiltersDot` 509-531).

### `frontend/src/components/featureRoute/FeatureRouteRecorder.tsx`

**Analog:** `App.tsx` `ProtectedLayout` lines 750-766 (to be replaced):
```tsx
useEffect(() => {
  if (isOpeningsRoute && profile?.email) {
    setUserFlag(FLAG_OPENINGS_VISITED, profile.email);
  }
}, [isOpeningsRoute, profile?.email]);
```
Same effect shape, but: guard on `profile?.feature_route == null` and `profile.impersonation != null`; post `done` for each unresolved visit step matching pathname, `current` when candidate differs, `skip` when expired. Keep depth <= 4 (loop over registry with early `continue`). No `trackFeature` here.

### `frontend/src/lib/retiredLocalStorage.ts` (extend)

**Analog:** same file lines 13-25 (`removeRetiredBookmarkChartKeys`): collect keys first, then remove; `catch { return 0; }`; `storage: Storage = window.localStorage` param for testing. New `removeRetiredDotKeys` matches prefix `user_flag:` plus exact keys `played-as-hint-dismissed`, `filters-hint-dismissed`. Call site precedent: `Openings.tsx:110-114` mount effect. Extend `src/lib/__tests__/retiredLocalStorage.test.ts`.

### `frontend/src/lib/featureRoute.ts` + `hooks/useFeatureRoute.ts`

No single-file analog; build from `App.tsx`: `IMPORT_EXEMPT_ROUTES`/`isNavLocked` (168-172), `isActive` (176-184, move into the lib), `navUnlocked = importedGameCount > 0 && tier1` (209) and the duplicate in `MobileMoreDrawer` (604-609), collapsing to one `useNavUnlocked()`. Use `hasImportedGames(profile)` from `useUserProfile.ts`. Registry and resolver code: RESEARCH Pattern 1/2 and "Frontend read hook". Read hook must touch only `useUserProfile`, `useReadiness`, `useLocation` (already mocked in App.test).

## Shared Patterns

### Impersonation no-op (server + client)
Source: `app/routers/users.py:51-78` `_get_impersonation_context`; `feedback_ask_service.py:169-170`. Apply to router/service; client recorder skips on `profile.impersonation != null`. Do NOT copy the guest exclusion.

### Time source
`dev_now_utc` dependency (`app/core/dev_clock.py`) in every new endpoint; tests override via `app.dependency_overrides[dev_now_utc]`.

### Sentry
Constant message, `set_context("feature_route", {"user_id": ...})`, `capture_exception` (copy `_capture_corrupt_state`). Frontend: none (global MutationCache).

### Testids
Section-prefixed dot testids per RESEARCH "Dot slot map" (Library and Openings both use `tab-stats`, so dots must be `library-stats-notification-dot` / `openings-stats-notification-dot`).

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `frontend/src/lib/featureRoute.ts` | pure registry/arbiter | No ordered-route concept exists; assemble from App.tsx helpers + RESEARCH Pattern 1/2 |
| `frontend/src/lib/__tests__/featureRoute.test.ts` | unit test | Plain vitest pure-function test; only structural analog is `retiredLocalStorage.test.ts` |

## Metadata

**Analog search scope:** `app/{schemas,repositories,services,routers}`, `alembic/versions`, `tests/`, `frontend/src/{App.tsx,hooks,lib}`
**Files scanned:** ~12
**Pattern extraction date:** 2026-11-15
