# Phase 234: Milestone Feedback Ask (SEED-191) - Pattern Map

**Mapped:** 2026-10-05
**Files analyzed:** 27 (new + modified, incl. tests)
**Analogs found:** 26 / 27

234-RESEARCH.md already cites verified line anchors for most surfaces. This map adds the concrete analogs to copy from and does not repeat the research's SQL (use RESEARCH "Code Examples" verbatim for the three transition statements).

Owner decisions that change patterns: D-01 copy interpolates `active_days` (so `FeedbackAskBubble` needs `active_days` from the profile, or the copy fn takes it as an arg). D-03 the ask replaces ALL non-guest Import variants (`welcome` and `explore`). D-04 Tank intro wins on Train landing (`askActive` only takes effect when `!isIntroHost`). D-05 no UI-SPEC.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/20261005_*_users_prompt_state_feedback_source.py` (NEW) | migration | batch/DDL | `alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py` | exact |
| `app/models/user.py` (+`prompt_state`) | model | CRUD | same file, `first_touch` lines 110-112 | exact |
| `app/models/feedback.py` (+`source` + CheckConstraint) | model | CRUD | same file; CHECK naming `ck_bot_game_settings_rating_source` | exact |
| `app/schemas/feedback_ask.py` (NEW) | model (Pydantic) | transform | `app/schemas/feedback.py` (`FeedbackCreate`) | role-match |
| `app/schemas/feedback.py` (+`source` Literal) | model | request-response | self | exact |
| `app/schemas/users.py` (+`active_days`, `feedback_ask`) | model | request-response | self (`UserProfileResponse`) | exact |
| `app/repositories/feedback_ask_repository.py` (NEW) | repository | CRUD (atomic UPDATE) | `app/repositories/user_repository.py` 140-156 (`first_touch` guarded UPDATE) + `train_repository.py` 2880-2882 (JSONB `||`) | role-match |
| `app/repositories/feedback_repository.py` (+`has_feedback`, `source`) | repository | CRUD | self, `create_feedback` 19-27 | exact |
| `app/services/feedback_ask_service.py` (NEW) | service | request-response + pure fn | `app/services/feedback_service.py` | role-match |
| `app/routers/users.py` (shared builder + POST `/me/feedback-ask`) | controller | request-response | self, `get_profile` 78-114 / `update_profile` 117-152 | exact |
| `tests/test_feedback_ask.py` (NEW) | test | integration | `tests/test_users_first_touch.py`, `tests/routers/test_train_medals.py:100` (dev clock override) | role-match |
| `tests/services/test_feedback_ask_service.py` (NEW) | test | unit | any pure-fn test in `tests/services/` | role-match |
| `tests/test_feedback_router.py` (extend) | test | integration | self | exact |
| `frontend/src/lib/feedbackAsk.ts` (NEW: HILDA_ID, copy fn, placeholder, modal store) | utility/store | event-driven | `frontend/src/lib/playActive.ts` (store) + `frontend/src/lib/trainBotCopy.ts:45` (`TANK_ID`) | exact |
| `frontend/src/hooks/useFeedbackAsk.ts` (NEW) | hook | request-response | `frontend/src/hooks/useUserProfile.ts` `useSetLeaderboardHidden` | exact |
| `frontend/src/components/feedback/FeedbackAskBubble.tsx` (NEW) | component | event-driven | `PersonaGrid.tsx` `BotWelcomeCard` 77-100 + `components/import/ImportBotBubble.tsx` | role-match |
| `frontend/src/components/feedback/FeedbackAskActions.tsx` (NEW, or inline) | component | event-driven | `frontend/src/components/train/SignupAskActions.tsx` | exact |
| `frontend/src/components/feedback/FeedbackAskModalHost.tsx` (NEW) | provider/host | event-driven | `FeedbackButton` mount in `App.tsx:831,854` + `playActive.ts` reader | role-match |
| `frontend/src/components/feedback/FeedbackModal.tsx` (+`placeholder?`, `source?`) | component | request-response | self | exact |
| `frontend/src/hooks/useFeedback.ts` (invalidate profile) | hook | request-response | `useSetLeaderboardHidden` onSuccess | exact |
| `frontend/src/types/users.ts`, `types/feedback.ts` | model | - | self | exact |
| `frontend/src/lib/analytics.ts` (`ACTION_TARGETS`) | config | - | self lines 384-401 | exact |
| `frontend/src/pages/Import.tsx` | page | - | self 143-147, 449 | exact |
| `frontend/src/components/train/TrainStartScreen.tsx` (+ `Train.tsx` prop) | component | - | self 237-245; `isGuest`/`hasGames` prop drilling | exact |
| `frontend/src/components/bots/PersonaGrid.tsx` + `pages/Bots.tsx` | component | - | self 77-100; `Bots.tsx:591` profile read | exact |
| `frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx` (NEW) | test | component | `__tests__/FeedbackButton.test.tsx` (mock pattern) | role-match |
| `CHANGELOG.md` | docs | - | `[Unreleased]` section | n/a |

## Pattern Assignments

### Migration (NEW) — analog `alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py`

Copy the whole file shape (docstring explaining why, revision header, `upgrade`/`downgrade`). Set `down_revision = 'a7c3e9d41f02'`.
```python
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a7c3e9d41f02'
down_revision: Union[str, Sequence[str], None] = 'e3a8c5f17b20'
...
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('drill_solves', sa.Column('telemetry', postgresql.JSONB(none_as_null=True), nullable=True))
```
Deltas (RESEARCH Pitfall 6): `postgresql.JSONB()` (no `none_as_null`), `server_default=sa.text("'{}'::jsonb")`, `nullable=False`; `feedback.source` `sa.Text()` with `server_default=sa.text("'floating_button'")` + `op.create_check_constraint('ck_feedback_source', 'feedback', "source IN ('floating_button', 'milestone_ask')")`. Downgrade: drop constraint, then both columns.

### `app/models/user.py` — analog: same file lines 110-112
```python
first_touch: Mapped[dict[str, str] | None] = mapped_column(
    JSONB(none_as_null=True), nullable=True, default=None
)
```
New: `prompt_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict)`. `text` already imported (see `is_guest` line 31 `server_default=text("false")`).

### `app/repositories/feedback_ask_repository.py` (NEW) — analogs `user_repository.py:146-156`, `train_repository.py:2880-2882`

Guarded single-row UPDATE idiom (user_repository.py 146-156):
```python
result = await session.execute(
    update(User)
    .where(User.id == user_id, User.first_touch.is_(None), User.created_at >= created_after)
    .values(first_touch=first_touch)
)
await session.flush()
return result.rowcount == 1  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
```
JSONB merge (train_repository.py 2880-2882):
```python
return func.coalesce(DrillSolve.telemetry, literal({}, JSONB)).op("||", return_type=JSONB)(literal(patch, JSONB))
```
For this phase use `sqlalchemy.text()` with the verified SQL from RESEARCH "Code Examples" (VIEW / SNOOZE / DONE), every param wrapped in `CAST(:x AS int|text)` (Pitfall 4), constants bound from `feedback_ask_service` (or a shared constants module to avoid a repo->service import), `RETURNING prompt_state->'feedback_v1'`, then `FeedbackAskState.model_validate(row)`; return `None` when no row. Also `count_active_days(session, user_id, today) -> int` (count + today-inclusive +1). No `asyncio.gather`.

### `app/repositories/feedback_repository.py` — self, `create_feedback` lines 19-27
Add `source=data.source` to the `Feedback(...)` constructor; add `has_feedback(session, user_id) -> bool` via `select(exists().where(Feedback.user_id == user_id))`.

### `app/services/feedback_ask_service.py` (NEW) — analog `app/services/feedback_service.py`
Constants at module top (`FEEDBACK_ASK_MIN_ACTIVE_DAYS = 5`, `..._REASK_GAP_DAYS = 10`, `..._MAX_VIEWS = 3`, `..._MAX_ROUNDS = 2`, `FEEDBACK_ASK_ID = "feedback_v1"`). Pure `resolve_feedback_ask` from RESEARCH Pattern 1 verbatim. Sentry: follow `feedback_service.py:123` style but DO NOT reuse the `source="feedback"` tag; on `ValidationError` of stored state do `sentry_sdk.set_context("feedback_ask", {"user_id": ...}); sentry_sdk.capture_exception(exc)` and fail closed (`active=False`).

### `app/routers/users.py` — self lines 78-152
Both routes currently build `UserProfileResponse(...)` independently (GET 97-114, PUT 136-152; PUT passes `impersonation=None`). Extract `_build_profile_response(session, user, profile_row, now_utc, impersonation)` and call from both, adding `active_days` + `feedback_ask`. New route copies GET's dependency signature exactly:
```python
@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    impersonation: Annotated[ImpersonationContext | None, Depends(_get_impersonation_context)],
    now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)],
) -> UserProfileResponse:
```
POST path `"/me/feedback-ask"` (relative; prefix `/users`), `response_model=FeedbackAskView`, thin: delegate to `feedback_ask_service.apply_action(...)`. Note PUT has no impersonation dep today; for the shared builder either add it or pass `None` (current behaviour).

### `app/schemas/feedback_ask.py` (NEW), `schemas/feedback.py`, `schemas/users.py`
Use RESEARCH Pattern 1 `FeedbackAskState` (`ConfigDict(extra="forbid")`, Literal fields). `FeedbackAskView(active: bool, round: Literal[1, 2])`, `FeedbackAskActionRequest(action: Literal["view", "snooze", "done"])`. `FeedbackCreate` gains `source: Literal["floating_button", "milestone_ask"] = "floating_button"` (schemas/feedback.py 39-47).

### Backend tests
- `tests/test_feedback_ask.py`: dev-clock override precedent `tests/routers/test_train_medals.py:100` / `tests/routers/test_train_leaderboard.py:73`:
  ```python
  app.dependency_overrides[dev_now_utc] = lambda: now
  ```
  User/first-touch integration shape from `tests/test_users_first_touch.py`. Seed `user_activity` rows directly (middleware writes with real clock). Every non-guest user insert needs finally-cleanup (memory: lottery isolation). Concurrency test: two separate requests/sessions, never gather on one session.
- `tests/test_feedback_router.py`: extend with `source` default / milestone_ask / 422 cases.

### `frontend/src/lib/feedbackAsk.ts` (NEW) — analogs `lib/playActive.ts`, `lib/trainBotCopy.ts:45`
Module store (copy playActive.ts structure):
```ts
import { useEffect, useSyncExternalStore } from 'react';
let active = false;
const listeners = new Set<() => void>();
function setActive(next: boolean): void {
  if (active === next) return;
  active = next;
  listeners.forEach((listener) => listener());
}
function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
export function usePlayActive(): boolean {
  return useSyncExternalStore(subscribe, () => active);
}
```
-> `openFeedbackAskModal()`, `closeFeedbackAskModal()`, `useFeedbackAskModalOpen()`. Persona id: `export const HILDA_ID: PersonaId = 'wall-1800';` (mirrors `TANK_ID`). Copy fn per D-01: `feedbackAskCopy(activeDays: number): string`. Keep exports minimal (knip).

### `frontend/src/hooks/useFeedbackAsk.ts` (NEW) — analog `useUserProfile.ts` `useSetLeaderboardHidden`
```ts
export function useSetLeaderboardHidden() {
  const queryClient = useQueryClient();
  return useMutation<UserProfile, Error, boolean>({
    mutationFn: async (hidden) => {
      const res = await apiClient.put<UserProfile>('/users/me/profile', { leaderboard_hidden: hidden });
      return res.data;
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(USER_PROFILE_QUERY_KEY, profile);
      ...
```
Deltas: `scope: { id: 'feedback-ask' }`, POST `/users/me/feedback-ask`, `onSuccess` patches `feedback_ask` via `setQueryData(USER_PROFILE_QUERY_KEY, p => p && { ...p, feedback_ask: resp })`; `onMutate` optimistic `active: false` for `snooze`. No Sentry call (global MutationCache.onError reports). No repo precedent for `scope` exists; RESEARCH verified it in query-core 5.102.8.

### `FeedbackAskBubble.tsx` (NEW) — analog `PersonaGrid.tsx` `BotWelcomeCard` 77-100
```tsx
<section data-testid="bots-intro" className="space-y-3 text-sm text-muted-foreground">
  <div data-testid="bots-welcome-bubble">
    <TrainBotBubble persona={host.persona} state="prompt" avatarSize="large">
      <p>{host.copy} ...</p>
```
Swap persona for `PERSONA_REGISTRY[HILDA_ID]`, pass `actions={<FeedbackAskActions surface=... />}`, `useEffect(() => { report('view') }, [report])` (API call, not Umami). Wrapper testid `feedback-ask-${surface}`, copy testid `feedback-ask-copy`. Modal NOT inside the bubble (Pitfall 1).

### `FeedbackAskActions` — analog `components/train/SignupAskActions.tsx` (whole file)
Bare two-`Button` fragment, `brand-outline` secondary first, `default` primary second, `className={TRAIN_BUTTON_CLASS}`, per-surface `source` prop in testids:
```tsx
<Button variant="brand-outline" className={TRAIN_BUTTON_CLASS} onClick={...} data-testid={`btn-signup-why-${source}`}>What changes?</Button>
<Button variant="default" className={TRAIN_BUTTON_CLASS} onClick={...} data-testid={`btn-signup-free-${source}`} ...>Sign up free</Button>
```
-> "Maybe later" / "Sure!", testids `btn-feedback-ask-later-${surface}` / `btn-feedback-ask-sure-${surface}`, `trackFeature('action', { target: 'feedback-ask-later' | 'feedback-ask-sure' })` inside the click handlers (not data-umami attributes, not effects). Surface type: `'import' | 'train-landing' | 'bots'`.

### `FeedbackAskModalHost.tsx` (NEW) + `App.tsx`
Mount once next to `<FeedbackButton />` at `App.tsx:831` and `:854`, but NOT behind `!playActive`. Renders `<FeedbackModal open={open} onOpenChange={(o) => !o && closeFeedbackAskModal()} source="milestone_ask" placeholder={FEEDBACK_ASK_PLACEHOLDER} />`.

### `FeedbackModal.tsx` / `useFeedback.ts` / types
Add optional `placeholder?: string`, `source?: FeedbackSource` (default `'floating_button'`) threaded into the mutate payload; `FeedbackSource` union in `types/feedback.ts`. `useFeedback` onSuccess: `queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY })`. `UserProfile` (types/users.ts 24-50) gains `active_days: number; feedback_ask: { active: boolean; round: 1 | 2 }`.

### Surfaces
- `pages/Import.tsx` line 449 `{profile && <ImportBotBubble variant={importBubbleVariant(profile)} />}` -> ternary on `profile.feedback_ask.active` (D-03: overrides welcome + explore). Leave `EXPLORE_PARTS` untouched.
- `TrainStartScreen.tsx` 237-245: `askActive` prop from `Train.tsx` (like `isGuest`/`hasGames`); `const showAsk = askActive && !isIntroHost` (D-04); reminder ask condition `&& !showAsk`; class `cn('w-full', !isIntroHost && !showAsk && 'max-sm:hidden')`.
- `PersonaGrid.tsx` `BotWelcomeCard` gets `feedbackAskActive: boolean` prop from `Bots.tsx:591` profile; PersonaGrid stays query-free (hooks live only in `FeedbackAskBubble`).

### Frontend tests
`FeedbackAskBubble.test.tsx`: copy the `vi.mock` header style of `__tests__/FeedbackButton.test.tsx` (`// @vitest-environment jsdom`, mock `@/hooks/useFeedback`, mock `react-router` `useLocation`), or wrap in a real `QueryClientProvider` to test the scope/cache patch. Extend existing `FeedbackModal.test.tsx`, `TrainStartScreen.test.tsx`, `PersonaGrid.test.tsx`, Import tests; pre-existing tests must pass untouched (Pitfall 8). No `await import` inside test bodies (memory).

## Shared Patterns

- **Router dependency signature:** `app/routers/users.py:78-84` (session, `current_active_user`, `_get_impersonation_context`, `dev_now_utc`). Apply to POST `/me/feedback-ask`.
- **Guarded atomic UPDATE + `# ty: ignore[unresolved-attribute]` rowcount idiom:** `app/repositories/user_repository.py:146-156`.
- **Sentry:** `set_context` + `capture_exception`, no f-string messages; don't overload `source` tag (`feedback_service.py:123`).
- **Bot bubble:** `TrainBotBubble({ persona, state, children, actions, avatarSize })`; action pair per `SignupAskActions.tsx`.
- **Profile cache writes:** always via `USER_PROFILE_QUERY_KEY` (`useUserProfile.ts:6`).
- **Cross-tree UI state:** module store + `useSyncExternalStore` (`lib/playActive.ts`).
- **Umami:** register targets in `lib/analytics.ts` `ACTION_TARGETS` (384-401), call `trackFeature` only from click handlers.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `useFeedbackAsk.ts` `scope: { id }` usage | hook | serialized mutations | No existing `useMutation` in the repo uses `scope`; rely on RESEARCH (verified in query-core). Raw `text()` SQL with CASTs also has no close repo precedent; use RESEARCH's verified SQL. |

## Metadata

**Analog search scope:** `app/{routers,repositories,services,models,schemas}`, `alembic/versions`, `tests/`, `frontend/src/{lib,hooks,components/{feedback,train,bots,import},pages}`
**Files scanned:** ~20
**Pattern extraction date:** 2026-10-05
