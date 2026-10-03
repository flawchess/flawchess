# Phase 230: Weekly Train Leaderboards - Pattern Map

**Mapped:** 2026-10-03
**Files analyzed:** 20
**Analogs found:** 18 / 20

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/train_leaderboard.py` (NEW, pure) | service | transform | `frontend/src/lib/trainScore.ts` (points semantics), `app/services/train_scheduler.py` (pure helpers) | role-match |
| `app/repositories/train_leaderboard_repository.py` (NEW) | repository | CRUD read / aggregate | `app/repositories/train_repository.py` `get_progress` (l.768+) | role-match |
| `app/routers/train.py` (+ GET /leaderboard) | router | request-response | same file, `GET /progress` l.237-272 | exact |
| `app/schemas/train.py` (+ Leaderboard*) | schema | - | `TrainProgressResponse` in same file | exact |
| `app/models/user.py` (+ leaderboard_hidden) | model | - | `beta_enabled` l.33-40 | exact |
| `app/models/drill_solve.py` (+ partial index) | model | - | `app/models/import_job.py` l.18-27 | exact |
| `app/schemas/users.py`, `app/routers/users.py` (+ leaderboard_hidden) | schema/router | request-response | `beta_enabled` in `get_profile`/`update_profile` (users.py l.79-147) | exact |
| `alembic/versions/<ts>_<rev>_phase_230_leaderboard.py` | migration | - | `alembic/versions/20260927_140000_3b7e2f9c41a6_drill_sessions_entered_at.py` | exact |
| `tests/services/test_train_leaderboard.py` | test | pure | `tests/services/test_train_scheduler.py` | role-match |
| `tests/services/test_train_score_parity.py` | test | file-I/O regex | `tests/services/test_opening_insights_arrow_consistency.py` l.19-50 | exact |
| `tests/repositories/test_train_leaderboard_repository.py` | test | DB | `tests/repositories/test_train_repository.py` | role-match |
| `tests/routers/test_train_leaderboard.py` | test | HTTP | `tests/routers/test_train.py` (l.1275+ dev clock wiring) | exact |
| `frontend/src/hooks/useTrainLeaderboard.ts` | hook | request-response | `frontend/src/hooks/useTrainProgress.ts` | exact |
| `frontend/src/lib/trainLeaderboard.ts` | utility | transform + localStorage | `frontend/src/lib/botGameSnapshot.ts` (pure localStorage module), `trainScore.ts` | role-match |
| `frontend/src/components/train/TrainLeaderboardCard.tsx` | component | - | `frontend/src/components/train/TrainStatsCard.tsx` | role-match |
| `frontend/src/components/train/TrainScoreRankLines.tsx` | component | - | `TrainScoreScreen.tsx` | role-match |
| `frontend/src/components/settings/LeaderboardPrivacyCard.tsx` | component | mutation | Sound card in `SettingsPanel.tsx` l.141-152 + `useUserProfile.ts` | role-match |
| `frontend/src/types/train.ts`, `types/users.ts` | types | - | existing `TrainProgressResponse`/`UserProfile` | exact |
| `frontend/src/pages/Privacy.tsx` (+1 line) | page | - | itself | exact |
| profile PUT mutation hook | hook | mutation | `frontend/src/hooks/usePositionBookmarks.ts` (useMutation) | partial |

## Pattern Assignments

### `app/routers/train.py` GET /leaderboard (copy `GET /progress`, l.237-272)
Header already has `NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]` (l.54) and `router = APIRouter(prefix="/train", ...)` (l.51). Use relative path `"/leaderboard"`.
```python
@router.get("/progress", response_model=TrainProgressResponse)
async def get_train_progress(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
) -> TrainProgressResponse:
    try:
        progress = await train_repository.get_progress(session, user_id=user.id, now_utc=now_utc)
        await session.commit()
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("train", {"user_id": str(user.id)})
        sentry_sdk.capture_exception()
        raise
    return TrainProgressResponse(...)
```
Leaderboard is read-only: drop the commit/rollback, keep the Sentry capture. `session_id: int | None = None` as query param; scope the contribution query by `user_id` (IDOR-safe, RESEARCH Pattern 3).

### `app/repositories/train_leaderboard_repository.py`
Analog `train_repository.get_progress` (l.768): keyword-only `session, *, user_id, now_utc`, docstring notes "Sequential awaits only, never asyncio.gather". Select columns only (not `select(User)`, oauth_accounts is lazy="joined"). Build the points `CASE` from a backend `MOVE_TIER_POINTS` mapping, not raw `move_quality` (RESEARCH anti-patterns). Return TypedDict/dataclass rows, rank in Python in the service.

### `app/models/user.py` (copy `beta_enabled`, l.35-40)
```python
beta_enabled: Mapped[bool] = mapped_column(
    Boolean, nullable=False, server_default=text("false"), default=False,
)
```

### `app/models/drill_solve.py` partial index
Append to existing `__table_args__` (l.122-130). Pattern from `app/models/import_job.py` l.21-27:
```python
Index("uq_import_jobs_user_platform_active", "user_id", "platform", unique=True,
      postgresql_where=sa.text("status IN ('pending', 'in_progress')"))
```

### Migration (copy `20260927_140000_3b7e2f9c41a6_drill_sessions_entered_at.py`)
Header docstring with Revision/Revises/Create Date + rationale; `down_revision = '3b7e2f9c41a6'` (verify current head). `op.add_column('users', sa.Column('leaderboard_hidden', sa.Boolean(), nullable=False, server_default=sa.text('false')))` + `op.create_index(..., postgresql_where=...)`; downgrade drops both.

### `app/routers/users.py` / `app/schemas/users.py`
Add `leaderboard_hidden=user.leaderboard_hidden` next to `beta_enabled=user.beta_enabled` in `get_profile` (l.111) and `beta_enabled=updated.beta_enabled` in `update_profile` (l.144). `update_profile` uses `user_repository.update_profile(session, user.id, body.model_dump())`, so `UserProfileUpdate` needs `leaderboard_hidden: bool | None = None` and the repository must ignore None (check `user_repository.update_profile` so existing PUTs without the field do not reset it). Schema field sits next to `beta_enabled: bool` (schemas/users.py l.69).

### `tests/services/test_train_score_parity.py` (copy `test_opening_insights_arrow_consistency.py` l.19-50)
```python
_ARROW_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/arrowColor.ts"
m = re.search(rf"export\s+const\s+{name}\s*=\s*(\d+)\s*;", text)
assert m, f"could not find export const {name} in arrowColor.ts"
```
Targets: `GUESS_POINTS = 1` (trainScore.ts l.46), `MOVE_TIER_POINTS: Record<TrainMoveTier, number> = {` object literal (l.23), needs a multi-line key:value regex.

### `tests/routers/test_train_leaderboard.py`
Copy helpers `_register_and_login`, `_seed_game_with_blunder`, httpx `ASGITransport` client and try/finally cleanup from `tests/routers/test_train.py` (l.1275-1300). Pin time via `app.dependency_overrides[dev_now_utc]` (clean up in finally) or the `DEV_CLOCK_OFFSET_HEADER` + `monkeypatch ENVIRONMENT=development` pattern shown there. Use a unique ISO week per test (memory: global data leaks between tests).

### `frontend/src/hooks/useTrainLeaderboard.ts` (copy `useTrainProgress.ts`)
```ts
export const TRAIN_PROGRESS_QUERY_KEY = ['train', 'progress'] as const;
export function useTrainProgress(options?: { enabled?: boolean }) {
  return useQuery<TrainProgressResponse>({
    queryKey: TRAIN_PROGRESS_QUERY_KEY, queryFn: trainApi.getProgress,
    enabled: options?.enabled ?? true,
  });
}
```
Key `['train','leaderboard']` (+ sessionId, `staleTime: 0` for score screen). Add `trainApi.getLeaderboard` in `frontend/src/api/client.ts`.

### `TrainLeaderboardCard.tsx` (analog `TrainStatsCard.tsx`)
`import { Card } from '@/components/ui/card'`; `<Card as="section" className="w-full p-4" data-testid="train-stats-card">` (l.83). Follow `frontend/CLAUDE.md` for testids and `trackFeature` Umami events (tab switch). Guest CTA reuses `SignupAskActions.tsx`.

### `LeaderboardPrivacyCard.tsx` (analog SettingsPanel Sound card, l.141-152)
```tsx
<Card as="section" data-testid="settings-section-sound">
  <CardHeader as="h2" size="compact">Sound</CardHeader>
  <CardBody className="flex items-center gap-2">
    <Switch data-testid="settings-sound-switch" aria-label="Sound effects"
      checked={!muted} onCheckedChange={handleSoundChange} />
    <p className="text-sm text-muted-foreground">Move and game sounds on every board.</p>
  </CardBody>
</Card>
```
State from `useUserProfile()` (key `['userProfile']`, `apiClient.get('/users/me/profile')`); write via `useMutation` PUT `/users/me/profile` then `setQueryData(['userProfile'], ...)`. Must NOT enter `isAtDefaults` (l.122-127) or `handleReset`/`resetAllSettings` (l.134-137). Hide for guests (`profile.is_guest`).

### `frontend/src/lib/trainLeaderboard.ts`
Pure, React-free module like `botGameSnapshot.ts`; wrap localStorage in try/catch with Points fallback (D-09). Named constants (`COUNTDOWN_TICK_MS = 60_000`).

## Shared Patterns
- **Time:** `now_utc` from `dev_now_utc` only, passed down keyword-only; never `datetime.now()`.
- **Sentry:** `sentry_sdk.set_context("train", {...}); sentry_sdk.capture_exception()` in router except blocks, no variables in messages.
- **Types:** `Literal[...]` for visibility/board kinds; explicit return types (ty gate).
- **Nesting depth <= 4** (`scripts/check_function_size.py`); keep TrainScoreScreen under its complexity cap by extracting `TrainScoreRankLines`.

## No Analog Found
| File | Reason |
|---|---|
| ranking logic in `train_leaderboard.py` | no competition-ranking/neighbour-slice code exists; use RESEARCH Patterns 1-4 |
| countdown formatter | no countdown util exists; use RESEARCH Pattern 5 |

## Metadata
**Search scope:** app/routers, app/repositories, app/models, app/schemas, alembic/versions, tests/, frontend/src/{hooks,lib,components/train,components/settings}
**Files scanned:** ~20
