# Phase 231: Weekly Leaderboard Medals (SEED-186) - Pattern Map

**Mapped:** 2026-10-04
**Files analyzed:** 30 (new + modified, incl. tests)
**Analogs found:** 28 / 30 (all analogs are git-tracked source)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/2026MMDD_HHMMSS_<rev>_phase_231_train_weekly_standings.py` (new) | migration | DDL | `alembic/versions/20261003_120000_c4e7a91d2b58_users_leaderboard_hidden.py` (header/shape) + `20260725_115348_10335efafdb4_phase_189_train_tables.py` (create_table + CHECK) | role-match; trigger has NO analog (first in repo) |
| `alembic/env.py` (mod) | config | — | itself lines 18-30 | exact |
| `app/models/train_weekly_standing.py` (new) | model | CRUD | `app/models/drill_session.py`, `app/models/drill_solve.py` | exact |
| `app/repositories/train_medals_repository.py` (new) | repository | CRUD (upsert/claim) | `app/repositories/train_leaderboard_repository.py` + `game_repository.py:55-68` + `train_repository.py:330-345, 3004` | exact |
| `app/services/train_leaderboard.py` (mod) | service (pure) | transform | itself (`_entry_for`, `_tiered_order`, `build_board`) | exact |
| `app/services/train_medals.py` (new) | service | batch (lazy finalize) + request-response | `app/services/train_leaderboard.py` (`get_weekly_leaderboard`) | role-match |
| `app/schemas/train.py` (mod) | schema | request-response | itself lines 440-510 | exact |
| `app/routers/train.py` (mod) | router | request-response | itself `get_train_leaderboard` (~281) + progress handler commit/rollback (~260) | exact |
| `tests/services/test_train_leaderboard.py` (mod) | test (unit, DB-free) | — | itself | exact |
| `tests/services/test_train_medals.py` (new) | test (unit) | — | `tests/services/test_train_leaderboard.py` | exact |
| `tests/repositories/test_train_medals_repository.py` (new) | test (DB) | — | `tests/repositories/test_train_leaderboard_repository.py` | exact |
| `tests/repositories/test_train_medals_finalization.py` (new, Plan 06) | test (DB) | — | `tests/repositories/test_train_leaderboard_repository.py` | exact |
| `tests/routers/test_train_medals.py` (new) | test (router) | — | `tests/routers/test_train_leaderboard.py` | exact |
| `tests/routers/test_train_leaderboard.py` (mod) | test | — | itself key-set test (~269-290) | exact |
| trigger existence test (new, e.g. in repo test or `tests/test_migration_only_indexes_exist.py` style) | test | — | `tests/test_migration_only_indexes_exist.py` | exact |
| `frontend/src/types/train.ts` (mod) | types | — | itself (mirror of `app/schemas/train.py`) | exact |
| `frontend/src/api/client.ts` (mod) | api client | request-response | `trainApi.getLeaderboard` (lines 303-310) | exact |
| `frontend/src/hooks/useTrainMedals.ts` (new) | hook | request-response | `hooks/useTrainLeaderboard.ts`, `useSetLeaderboardHidden` in `hooks/useUserProfile.ts:20-40` | exact |
| `frontend/src/lib/trainMedals.ts` (new) | utility (pure copy) | transform | `frontend/src/lib/trainLeaderboard.ts` | exact |
| `frontend/src/lib/theme.ts` (mod) | config | — | itself lines 561-607 (TRAIN_* constants) | exact |
| `frontend/src/index.css` (mod) | styles | — | `.animate-train-score-badge-pop` (lines ~385-398) + reduced-motion block (~535) | exact |
| `frontend/src/components/train/TrainLeaderboardCard.tsx` (mod: container + `TrainLeaderboardCardView`) | component | request-response | itself | exact |
| `components/train/medals/MedalIcon.tsx`, `MedalTally.tsx`, `LastWeekPodium.tsx` (new) | component (presentational) | — | `LeaderboardRowItem` in `TrainLeaderboardCard.tsx:100-128` | role-match |
| `components/train/medals/MedalClaimDialog.tsx` (new) | component (dialog) | event-driven | `components/bots/GameResultDialog.tsx` + `TrainScoreScreen.tsx:258-275` | exact |
| `components/train/medals/TrainMedalDialogHost.tsx` (new) | container | request-response | `TrainLeaderboardCard` container + `useSetLeaderboardHidden` | role-match |
| `components/train/TrainStartScreen.tsx` (mod) | component | — | itself (branches ~346/355/385) | exact |
| `components/admin/LeaderboardMedalsDemo.tsx` + `lib/leaderboardMedalsDemoData.ts` (new) | component (admin) | client-only | `components/admin/TrainReminderTestCard.tsx` | role-match |
| `frontend/src/pages/Admin.tsx` (mod) | page | — | itself lines 30-80 | exact |
| `components/settings/LeaderboardPrivacyCard.tsx`, `pages/Privacy.tsx` (mod) | copy | — | itself (`HIDE_HELPER` line 7-8) | exact |
| Frontend tests: `TrainLeaderboardCard.test.tsx` (mod), `TrainStartScreen.test.tsx` (mod), `pages/__tests__/Train.solveLoop.test.tsx` (mod), new `medals/__tests__/*.test.tsx`, `admin/__tests__/LeaderboardMedalsDemo.test.tsx`, `lib/trainMedals.test.ts` | test | — | `TrainLeaderboardCard.test.tsx`, `bots/__tests__/GameResultDialog.test.tsx`, `TrainScoreScreen.test.tsx` | exact |

## Pattern Assignments

### Migration (new) — analog `alembic/versions/20261003_120000_c4e7a91d2b58_users_leaderboard_hidden.py`

Down-revision = current head `c4e7a91d2b58` (re-check `uv run alembic heads`). Filename template from `alembic.ini:17`: `YYYYMMDD_HHMMSS_<rev>_<slug>.py`.

Header/shape (lines 1-24):
```python
"""users leaderboard_hidden

Revision ID: c4e7a91d2b58
Revises: 3b7e2f9c41a6
Create Date: 2026-10-03 12:00:00+00:00

Phase 230 weekly Train leaderboards: ...
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4e7a91d2b58'
down_revision: Union[str, Sequence[str], None] = '3b7e2f9c41a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
Downgrade mirrors upgrade in reverse (lines 43-50). For `op.create_table` with `sa.CheckConstraint`/`sa.UniqueConstraint`/`sa.ForeignKeyConstraint(..., ondelete='SET NULL')`, copy the shape from `20260725_115348_10335efafdb4_phase_189_train_tables.py`. Generate via `alembic revision --autogenerate`, then hand-append the trigger (no repo analog; use RESEARCH Pattern 4 SQL verbatim):
```python
op.execute("""CREATE FUNCTION train_weekly_standings_erase_name() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN NEW.display_name := 'Deleted user'; RETURN NEW; END $$;""")
op.execute("""CREATE TRIGGER trg_train_weekly_standings_erase_name
BEFORE UPDATE OF user_id ON train_weekly_standings
FOR EACH ROW WHEN (OLD.user_id IS NOT NULL AND NEW.user_id IS NULL)
EXECUTE FUNCTION train_weekly_standings_erase_name();""")
# downgrade: DROP TRIGGER ... ON train_weekly_standings; DROP FUNCTION ...; drop tables
```

### `alembic/env.py` (mod) — lines 25-29
```python
from app.models.drill_solve import DrillSolve  # noqa: F401
from app.models.train_settings import TrainSettings  # noqa: F401
```
Add `from app.models.train_weekly_standing import TrainWeeklyFinalization, TrainWeeklyStanding  # noqa: F401` beside these.

### `app/models/train_weekly_standing.py` (new) — analogs `app/models/drill_session.py`, `app/models/drill_solve.py`

Module docstring documenting deletion semantics (drill_session.py lines 1-17 style) — must document the invisible trigger.

Imports (drill_session.py lines 19-36):
```python
from __future__ import annotations
import datetime
from sqlalchemy import (CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, Text, func, text)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
```
IntEnum + CHECK (drill_solve.py ~103-133):
```python
class DrillMoveQuality(IntEnum):
    """..."""
    WRONG = 0
    INACCURACY = 1
    GOOD = 2

class DrillSolve(Base):
    __tablename__ = "drill_solves"
    __table_args__ = (
        CheckConstraint("move_quality IS NULL OR move_quality IN (0, 1, 2)", name="ck_drill_solves_move_quality"),
        UniqueConstraint("session_id", "game_id", "ply", name="uq_drill_solves_session_puzzle"),
        Index("ix_drill_solves_solved_at", "solved_at", postgresql_where=text("solved_at IS NOT NULL")),
    )
```
TEXT + CHECK (drill_session.py 45-47): `CheckConstraint("status IN ('open', 'completed', 'expired')", name="ck_drill_sessions_status")`.
Nullable SET NULL FK (drill_solve.py ~150): `game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id", ondelete="SET NULL"), nullable=True)` — use the same for `user_id -> users.id`. Full column list: RESEARCH Pattern 3.

### `app/repositories/train_medals_repository.py` (new) — analog `app/repositories/train_leaderboard_repository.py`

Module docstring + imports (lines 1-20): note "Sequential awaits only"; frozen dataclasses for return rows (`SolveTotals`, `WeeklyAggregate` lines 23-42). Select columns only, never `User` entity (oauth_accounts is lazy="joined", line 66-68) — relevant for the LEFT JOIN users podium read.

ON CONFLICT + RETURNING (`app/repositories/game_repository.py:59-68`):
```python
stmt = (
    pg_insert(Game)
    .values(game_rows)
    .on_conflict_do_nothing(constraint="uq_games_user_platform_game_id")
    .returning(Game.id)
)
result = await session.execute(stmt)
```
`index_elements=` form (`train_repository.py:~342`): `stmt = stmt.on_conflict_do_nothing(index_elements=["user_id"])` — use for the marker table PK.

IDOR scoping (train_leaderboard_repository.py `fetch_session_contribution` ~103-125): `.where(DrillSolve.user_id == user_id, ...)` with docstring "Scoping by the caller's user id is the IDOR guard" — copy for unclaimed SELECT and claim UPDATE.

DML rowcount (train_repository.py:3004):
```python
claimed = claim_result.rowcount == 1  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
```

### `app/services/train_leaderboard.py` (mod) — itself

Constants block (lines 46-51) e.g. `ANONYMOUS_DISPLAY_NAME: Final = "Anonymous"` → add `DELETED_USER_DISPLAY_NAME`, `MEDAL_BY_RANK`. Reuse `_entry_for` (149), `_order_key` (169), `_competition_ranks` (178), `_tiered_order` (189), `_slice_indices` (203), `build_board` (270), `get_weekly_leaderboard` (359). Add `final_standings`, `medal_for`, `MedalTally`, `visible_keys`, `build_last_week` per RESEARCH Patterns 1/5/6. Keep `build_board(..., medal_tallies=None)` default so existing DB-free tests pass. Invariant at line 25: `_Entry.key` is never copied onto a response dataclass.

### `app/services/train_medals.py` (new) — analog `get_weekly_leaderboard` in train_leaderboard.py

`Final` module constants (`MEDALS_START_WEEK`, `MEDALS_FINALIZE_GRACE`, `MAX_CLAIM_ITEMS`), pure `due_weeks` + async `finalize_due_weeks` per RESEARCH Pattern 2. Read `MEDALS_START_WEEK` as module global at call time (monkeypatchable). Flat loop with `continue` (nesting gate).

### `app/schemas/train.py` (mod) — itself lines 440-510

```python
LeaderboardBoardKind = Literal["points", "accuracy"]

class LeaderboardRow(BaseModel):
    """... Deliberately carries no user id or email ..."""
    model_config = ConfigDict(from_attributes=True)
    rank: int | None
    ...
class LeaderboardBoard(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rows: list[LeaderboardRow]
    viewer: LeaderboardViewer | None
    pass_target: LeaderboardPassTarget | None
```
Add `MedalKind` Literal, `LeaderboardMedals`, `LeaderboardPodiumEntry`, `LeaderboardLastWeek`, `UnclaimedMedal(s)Response`, `MedalKey`, `ClaimMedalsRequest` (`Field(min_length=1, max_length=MAX_CLAIM_ITEMS)`); extend `__all__` (alphabetical, line ~515).

### `app/routers/train.py` (mod) — itself

Imports/router/NowUtc (lines 24-56):
```python
router = APIRouter(prefix="/train", tags=["train"])
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]
```
Handler shape (`get_train_leaderboard`, ~281-312):
```python
@router.get("/leaderboard", response_model=TrainLeaderboardResponse)
async def get_train_leaderboard(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
    ...
) -> TrainLeaderboardResponse:
    try:
        result = await get_weekly_leaderboard(session, viewer_id=user.id, ..., now_utc=now_utc, ...)
    except Exception:
        sentry_sdk.set_context("train", {"user_id": str(user.id), "session_id": str(session_id)})
        sentry_sdk.capture_exception()
        raise
    return TrainLeaderboardResponse.model_validate(result)
```
Commit/rollback (progress handler ~260-264):
```python
        await session.commit()
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("train", {"user_id": str(user.id)})
        sentry_sdk.capture_exception()
        raise
```
For the finalizer call: same block but do NOT `raise` (must not 500 the board). New routes: `@router.get("/medals/unclaimed", ...)`, `@router.post("/medals/claim", status_code=204)` — relative paths only. Update the leaderboard docstring ("Read-only: no commit") since it now commits.

### Backend tests

**Router tests** (`tests/routers/test_train_leaderboard.py`): copy module docstring k-table convention (lines 1-28), `pin_now` fixture (~69-77), `_register_and_login` (~80-95), `_set_user_fields` (~98-102), `_seed_solves`, `finally` user deletes. Use a new base Monday (e.g. 2033-01-03) and `monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", ...)`; delete the week's marker/standings before seeding and in `finally` (RESEARCH Pitfall 2).
```python
@pytest.fixture
def pin_now() -> Iterator[Callable[[datetime.datetime], None]]:
    def _pin(now: datetime.datetime) -> None:
        app.dependency_overrides[dev_now_utc] = lambda: now
    yield _pin
    app.dependency_overrides.pop(dev_now_utc, None)
```
Key-set test (~269-290) must gain `"last_week"` in board keys and `"medals"` in row keys.

**Repository tests**: `tests/repositories/test_train_leaderboard_repository.py` header (lines 1-24): reserved user-id range + own-week k table on rollback-scoped `db_session`. Pick a fresh unused user-id range.

**Unit tests**: `tests/services/test_train_leaderboard.py` — `_agg(user_id, *, points, puzzles, nf_points, nf_puzzles, ...)` builder (line ~33); test names carry `-k` tokens (`final_standings`, `medal_for`, `tally`, `last_week`, `viewer_final_rank`).

**Trigger existence**: copy `tests/test_migration_only_indexes_exist.py` (lines 16-40), querying `SELECT tgname FROM pg_trigger WHERE tgname = :name` via `test_engine.connect()`.

### `frontend/src/api/client.ts` (mod) — `trainApi.getLeaderboard` lines 303-310
```ts
  /** Phase 230: ... */
  getLeaderboard: (sessionId?: number) =>
    apiClient
      .get<TrainLeaderboardResponse>('/train/leaderboard', { params: ... })
      .then(r => r.data),
```
POST void analog (line 290): `apiClient.post<void>(`/train/sessions/${sessionId}/enter`).then(() => undefined)` → `claimMedals`.

### `frontend/src/hooks/useTrainMedals.ts` (new)
Query: copy `useTrainLeaderboard.ts` (exported `..._QUERY_KEY` const, docstring noting no Sentry, `refetchOnMount: 'always'`, `enabled`). Mutation: copy `useSetLeaderboardHidden` (`hooks/useUserProfile.ts:26-39`):
```ts
export function useSetLeaderboardHidden() {
  const queryClient = useQueryClient();
  return useMutation<UserProfile, Error, boolean>({
    mutationFn: async (hidden) => { ... },
    onSuccess: (profile) => {
      queryClient.setQueryData(USER_PROFILE_QUERY_KEY, profile);
      void queryClient.invalidateQueries({ queryKey: TRAIN_LEADERBOARD_QUERY_KEY });
    },
  });
}
```
Note: do NOT invalidate unclaimed on success in a way that reopens the dialog in the same mount (host keeps per-mount `closed` state).

### `TrainLeaderboardCard.tsx` (mod) + `medals/MedalTally.tsx`, `LastWeekPodium.tsx`
Name block wrap (lines 112-122) — tally goes here as its own nowrap item, like the hidden cue:
```tsx
<span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-1">
  <span className="min-w-0 max-w-full truncate">
    {row.visibility === 'guest' ? GUEST_ROW_LABEL : row.name}
  </span>
  {row.visibility === 'hidden' && (
    <span className="whitespace-nowrap font-normal text-muted-foreground">{HIDDEN_FROM_OTHERS_LABEL}</span>
  )}
</span>
```
Header doc comment (lines 1-14) notes T-230-08: names render as React text children only — keep for podium/dialog. Split: exported `TrainLeaderboardCardView` (props) + thin container keeping `useTrainLeaderboard`/countdown/tab/`trackFeature`. Copy constants live in `lib/trainLeaderboard.ts` → new `lib/trainMedals.ts` same style.

### `medals/MedalClaimDialog.tsx` (new) — analog `components/bots/GameResultDialog.tsx`
Imports (lines 4-10) from `@/components/ui/dialog` (`Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle`). Controlled dismissal (lines 108-117):
```tsx
<Dialog open={open} onOpenChange={(next) => { if (!next) onDismiss(); }}>
  <DialogContent className="top-[30%] sm:top-1/2" data-testid="result-dialog">
    <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
    ...
    <DialogFooter className="sm:flex-col-reverse sm:justify-start"> <Button data-testid="btn-..." /> </DialogFooter>
```
Sound/confetti/reduced-motion (`TrainScoreScreen.tsx:56-57, 262-273`):
```tsx
import { fireWinConfetti, prefersReducedMotion } from '@/lib/confetti';
import { playSound } from '@/lib/sounds';
const reducedMotion = prefersReducedMotion();
playSound(RATING_BAND_SOUND[band]);
if (reducedMotion) return;
if (band === 'green') fireWinConfetti();
```
Here: `muted`/`reducedMotion` arrive as props (demo simulates); Claim handler = `unlockAudio(); if (!muted) playSound('game-win'); if (!reducedMotion) fireWinConfetti(); onClaim(keys)`. Use `showCloseButton={false}` + own close button with testid/aria-label. Test analog: `components/bots/__tests__/GameResultDialog.test.tsx`, `TrainScoreScreen.test.tsx` (mocks of confetti/sounds).

### `index.css` (mod) — lines ~385-398
```css
@keyframes train-score-badge-pop {
  0%   { opacity: 0; transform: scale(0.5); }
  55%  { opacity: 1; transform: scale(1.12); }
  75%  { transform: scale(0.97); }
  100% { opacity: 1; transform: scale(1); }
}
.animate-train-score-badge-pop {
  animation: train-score-badge-pop 0.55s cubic-bezier(0.34, 1.4, 0.64, 1) forwards;
}
```
New `.animate-medal-pop` uses fill mode `both` (delay), omitted by component under reduced motion, plus entry in the `prefers-reduced-motion` block (~535).

### `lib/theme.ts` (mod) — lines 561-607 style
```ts
export const TRAIN_RATING_YELLOW = 'oklch(0.75 0.15 85)'; // amber
export const TRAIN_FREEZE_COLOR = 'oklch(0.82 0.10 230)'; // icy blue
```
Add `MEDAL_GOLD/SILVER/BRONZE` + `MEDAL_COLORS: Record<MedalKind, string>` with trailing descriptive comments.

### `components/admin/LeaderboardMedalsDemo.tsx` (new) — analog `components/admin/TrainReminderTestCard.tsx`
Card shell (lines 29-32): `<div className="charcoal-texture rounded-md p-4 space-y-3" data-testid="admin-...">`, helper `<p className="text-sm text-muted-foreground">`, buttons `variant="brand-outline"` with `data-testid="btn-..."`. Docstring explaining scope (lines 1-18). No hooks/API calls (client-only).

### `pages/Admin.tsx` (mod) — lines 30-80
Section pattern (NOT inside the `import.meta.env.DEV &&` block at ~46-57):
```tsx
<section className="space-y-3" data-testid="admin-section-sentry-test">
  <h2 className="text-lg font-medium">Sentry Error Test</h2>
  <SentryTestButtons />
</section>
```
New: `data-testid="admin-section-leaderboard-medals-demo"`, heading "Leaderboard medals demo". Use `text-sm` (not `text-xs` as the impersonate section does).

### `TrainStartScreen.tsx` (mod) + test
Mount `<TrainMedalDialogHost isGuest={...} />` in the empty/completed/default landing branches. In `TrainStartScreen.test.tsx` mock the host exactly like the card stub (lines ~159-164):
```tsx
vi.mock('@/components/train/TrainLeaderboardCard', () => ({
  TrainLeaderboardCard: ({ isGuest }: { isGuest: boolean }) => (
    <div data-testid="train-leaderboard-card" data-guest={String(isGuest)} />
  ),
}));
```
`useUserProfile` mock (line ~47) returns `{ data: { email } }` — host reads `impersonation`, so the stub must tolerate undefined.

### `LeaderboardPrivacyCard.tsx` (mod) — lines 7-8
```ts
const HIDE_HELPER =
  'Your username and weekly Train results stay off the leaderboards other people see. You still see your own position.';
```
Append one sentence. `Privacy.tsx` ~line 29: one sentence on stored standings + "Deleted user".

### Frontend card test fixtures — `TrainLeaderboardCard.test.tsx` lines 34-58
```ts
const EMPTY_BOARD: LeaderboardBoard = { rows: [], viewer: null, pass_target: null };
function makeRow(overrides: Partial<LeaderboardRow> = {}): LeaderboardRow { return { rank: 1, name: 'magnus', ..., gap_before: false, ...overrides }; }
```
Add `last_week: null` and `medals: { gold: 0, silver: 0, bronze: 0 }` (tests are outside tsc, so drift fails only at runtime). Same for `pages/__tests__/Train.solveLoop.test.tsx` `trainApi` mock (~203-219): add `getUnclaimedMedals`, `claimMedals`.

## Shared Patterns

### Time source
**Source:** `app/routers/train.py` `NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]`. Apply to leaderboard, unclaimed, claim. Tests override via `pin_now`.

### Sentry in routers
**Source:** `app/routers/train.py` ~260-264 / ~305-308. `set_context("train", {...})` + `capture_exception()`, no variables in messages.

### IDOR
**Source:** `fetch_session_contribution` in `train_leaderboard_repository.py`. Caller id only from `current_active_user`; foreign keys match nothing.

### No ids on the wire
**Source:** `LeaderboardRow` docstring (`app/schemas/train.py`), `_Entry.key` invariant (`train_leaderboard.py:25`), key-set router test.

### Frontend query errors
Global `QueryCache/MutationCache.onError` capture; no `Sentry.captureException` in hooks/components (docstrings in `useTrainLeaderboard.ts`, `TrainReminderTestCard.tsx`). `data-testid` on every interactive element; `text-sm` minimum.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Trigger SQL inside the new migration | migration (plpgsql) | event-driven (DB) | No `CREATE TRIGGER` anywhere in `alembic/versions`; use RESEARCH Pattern 4 verbatim |
| Concurrency test (two sessions finalizing) | test | concurrent | No existing two-session race test located; build with two `async_sessionmaker(test_engine)` sessions (as `_set_user_fields` creates) |

## Metadata

**Analog search scope:** `alembic/`, `app/models`, `app/repositories`, `app/services`, `app/schemas`, `app/routers`, `tests/`, `frontend/src/{api,hooks,lib,components,pages}`
**Files scanned:** ~30
**Pattern extraction date:** 2026-10-04
