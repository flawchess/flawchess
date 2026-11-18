# Phase 251: Blunder-Check Schedule, Streak and Leaderboards - Pattern Map

**Mapped:** 2026-11-18
**Files analyzed:** 30 (from RESEARCH.md "Recommended file touch map" + CONTEXT integration points)
**Analogs found:** 29 / 30

This phase almost entirely extends existing modules, so most "analogs" are the puzzle-side twin of the
blunder-check (BC) code being added. All paths below are git-tracked source.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/<new>_phase_251_*.py` (down_revision `d1a7b3c5e261`) | migration | batch/DDL | `alembic/versions/*_e5f71b11fa51_*` (phase 206 sharp filler: add_column + widen CHECK) | exact |
| `app/models/train_settings.py` | model | CRUD | itself (`ck_train_settings_puzzles`, `puzzles_per_session` col) | exact |
| `app/models/blunder_check.py` (session_date, expires_on, 'expired') | model | CRUD | `app/models/drill_session.py` (session_date/expires_on/status) | exact |
| `app/models/train_weekly_standing.py` (board CHECK) | model | CRUD | itself line 74 | exact |
| `app/services/train_scheduler.py` (constants + pure `day_is_complete`) | utility (pure) | transform | `tick_days` / `_judge_one_day` in same file | exact |
| `app/repositories/train_repository.py` (`complete_days_for`, `apply_day_completion`, settings, progress per mode, cooldown in `_select_candidates`/`get_waiting_puzzle_count`, size-0 short-circuit) | repository | CRUD | `_apply_completion_tick` (3470), `settle_streak_snapshot` (956), `upsert_settings` (406) | exact |
| `app/repositories/blunder_check_repository.py` (expire, completed-in-window, resize, cooldown set, `complete_session` returns bool) | repository | CRUD | `train_repository.expire_stale_sessions` (1139), `completed_session_in_window` (1217) | exact |
| `app/services/blunder_check_service.py` | service | request-response | itself + `train_repository.record_solve` eager-tick call site (~3886) | exact |
| `app/services/blunder_check_selection.py` (`compose_windows(count, start_position)`, level fallback, cooldown) | service | transform | itself (`user_level_elo`, `_foreign_source`, `compose_windows` 555-590) | exact |
| `app/repositories/train_reminder_repository.py` (`has_completed_session_on` -> day complete) | repository | request-response | itself 148-170 | exact |
| `app/services/train_reminder_service.py` | service | batch/event-driven | itself (`_process_candidate`) | exact |
| `app/repositories/train_leaderboard_repository.py` (`fetch_week_bc_aggregates`) | repository | batch/aggregate | `fetch_week_aggregates` (63-105) | exact |
| `app/services/train_leaderboard.py` (per-board spec, BC boards, `BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS`) | service | transform | `_entry_for` (207-224), tally fold (456) | exact |
| `app/services/train_medals.py` (`_BOARDS` widened) | service | batch | itself 65-112 | exact |
| `app/repositories/train_medals_repository.py` (board order CASE) | repository | CRUD | itself 187 | exact |
| `app/routers/blunder_check.py` (drop `current_beta_user`) | controller | request-response | `app/routers/train.py` (`current_active_user`, guests allowed) | exact |
| `app/routers/train.py` (progress/settings/leaderboard extensions) | controller | request-response | itself | exact |
| `app/schemas/train.py` (`TrainSettingsUpdate` optional fields, progress `modes`, boards) | schema | request-response | itself 743-770 | exact |
| `app/schemas/blunder_check.py` | schema | request-response | itself | exact |
| `app/schemas/feature_route.py` (append step ID) | schema/config | config | itself 18-32 | exact |
| `frontend/src/pages/Train.tsx` | page/component | request-response | itself (remove BC tab redirect/mount, lines 137-252) | exact |
| `frontend/src/components/train/TrainSubnav.tsx` | component | — | itself (drop `showBlunderCheck`) | exact |
| `frontend/src/components/train/TrainStreakCard.tsx` (Today card with launcher rows, notice) | component | request-response | itself + `StreakFlame`, `FreezeMeter` | role-match |
| `frontend/src/components/train/TrainScheduleSettings.tsx` (per-mode collapsed rows, sliders, level picker) | component | CRUD (PUT settings) | itself | exact |
| `frontend/src/components/train/TrainLeaderboardCard.tsx` (mode switch) | component | request-response | itself (board tab switch) | exact |
| `frontend/src/components/train/TrainScoreScreen.tsx` + BC score screen (hand-off D-12) | component | — | itself | exact |
| `frontend/src/components/train/blunder-check/BlunderCheckTab.tsx` (host without start screen) + level step | component | request-response | itself; `TrainStartScreen.tsx` for the one-time step | role-match |
| `frontend/src/components/train/medals/*` (one dialog per week) | component | — | `medals/MedalClaimDialog.tsx` | exact |
| `frontend/src/lib/trainLeaderboard.ts` (mode storage key) | utility | file-I/O (localStorage) | `parseLeaderboardTab`/`readLeaderboardTab`/`writeLeaderboardTab` (61-82) | exact |
| `frontend/src/lib/trainRoute.ts`, `lib/featureRoute.ts`, `lib/analytics.ts`, `types/train.ts`, `App.tsx` | utility/config | — | themselves | exact |
| Tests (`tests/services/test_train_scheduler.py`, `tests/repositories/test_train_repository.py`, `tests/routers/test_blunder_check_sessions.py`, `tests/services/test_train_leaderboard.py`, `tests/repositories/test_train_medals_finalization.py`, `tests/services/test_train_reminder_service.py`, `tests/blunder_check_seed.py`) | test | — | existing files of the same names | exact |

## Pattern Assignments

### Migration (`alembic/versions/<new>.py`)

**Analog:** the phase 206 revision `e5f71b11fa51` (grep `revision: str = "e5f71b11fa51"`): add column + drop/recreate CHECK, with a data-aware downgrade.

```python
revision: str = "e5f71b11fa51"
down_revision: Union[str, Sequence[str], None] = "6e7e50844af5"

def upgrade() -> None:
    op.add_column("drill_solves", sa.Column("sharp_puzzle_id", sa.Text(), nullable=True))
    op.drop_constraint("ck_drill_solves_source", "drill_solves", type_="check")
    op.create_check_constraint("ck_drill_solves_source", "drill_solves", "source IN (0, 1, 2)")
    op.add_column(
        "drill_sessions",
        sa.Column("is_warmup", sa.Boolean(), server_default="false", nullable=False),
    )

def downgrade() -> None:
    # Bug fix: DELETE rows the narrower CHECK can't hold BEFORE recreating it,
    # else serial CI (shared DB with router tests) aborts with CheckViolationError.
    op.drop_column("drill_sessions", "is_warmup")
    op.execute("DELETE FROM drill_solves WHERE source = 2")
    op.drop_constraint("ck_drill_solves_source", "drill_solves", type_="check")
    op.create_check_constraint("ck_drill_solves_source", "drill_solves", "source IN (0, 1)")
```

Apply to: `ck_train_settings_puzzles` -> `BETWEEN 0 AND 50`; add `blunder_check_per_session SMALLINT NOT NULL server_default "6"` + CHECK; not-both-0 CHECK; `blunder_check_level TEXT NULL` + CHECK; `blunder_check_notice_from TIMESTAMPTZ` (UPDATE ... FROM users WHERE NOT is_guest); BC sessions `session_date`/`expires_on` (nullable, backfill via LEFT JOIN train_settings timezone, then `alter_column(nullable=False)`), status CHECK widened with `'expired'`; `ck_train_weekly_standings_board` widened with `'blunder_check_points'`, `'blunder_check_score'`; partial index on `blunder_check_windows(ended_at) WHERE ended_at IS NOT NULL`. Downgrade must DELETE/UPDATE rows that violate the narrower CHECKs first (rows at 0, 'expired' sessions, BC standings). Head confirmed: `20261117_210000_d1a7b3c5e261_blunder_check_window_prior_uci.py`.

---

### `app/models/train_settings.py` (model)

**Analog:** itself, lines 53-80:

```python
CheckConstraint("puzzles_per_session BETWEEN 1 AND 50", name="ck_train_settings_puzzles"),
...
# Defaults are 127/6 — see app.services.train_scheduler.DEFAULT_WEEKDAY_MASK/
# DEFAULT_PUZZLES_PER_SESSION ... (single source of truth the app layer applies on first touch;
# these server_defaults exist for direct-INSERT parity).
puzzles_per_session: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="6")
```

Use f-string CHECKs with constants as done for `SHIELD_CAP` / `REMINDER_HOUR_MIN` (same `__table_args__`). New `DEFAULT_BLUNDER_CHECK_PER_SESSION` / `BLUNDER_CHECK_PER_SESSION_MAX` in `train_scheduler.py`.

---

### `app/models/blunder_check.py` (model)

**Analog:** itself lines 89-116 (current header), plus `app/models/drill_session.py` for `session_date`/`expires_on` column types.

```python
CheckConstraint("status IN ('open', 'completed')", name="ck_blunder_check_sessions_status"),
CheckConstraint("window_count >= 1", name="ck_blunder_check_sessions_window_count"),
Index("uq_blunder_check_sessions_user_open", "user_id", unique=True,
      postgresql_where=text("status = 'open'")),
...
# TEXT + CHECK (low-volume domain column), no native ENUM.
status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
```

---

### `app/services/train_scheduler.py` (pure utility)

**Analog:** `tick_days` (565-649) uses `completed_session_dates` only as a set. Add `day_is_complete(*, puzzles_done, bc_done, puzzles_size, bc_size) -> bool` (RESEARCH Pattern 1) and constants (`CROSS_MODE_COOLDOWN_DAYS = 7`, `LAUNCH_NOTICE_DAYS = 14`, BC size default/max/slider). Do NOT touch `_judge_one_day`: a gate test greps for exactly one `SHIELD_CAP` clamp in `app/`.

---

### `app/repositories/train_repository.py` (repository)

**Analog for `apply_day_completion`:** `_apply_completion_tick` (lines 3470-3560). Keep its order and docstring style (IDOR-scoped lookup, `get_or_create_settings`, `local_today`, `settle_streak_snapshot` FIRST, single `_judge_one_day` call, compare-and-set write):

```python
settings_row = await get_or_create_settings(session, user_id=user_id)
today = local_today(settings_row.timezone, now_utc)

view = await settle_streak_snapshot(
    session, user_id=user_id, settings_row=settings_row, today=today
)
settled = view.settled

fulfilled = is_scheduled_day(session_date, settings_row.weekday_mask) and (
    settled.settled_through is None or session_date > settled.settled_through
)
outcome: DayOutcome = "fulfilled" if fulfilled else "credit_only"
judged = _judge_one_day(settled, day=session_date, outcome=outcome)

if outcome == "fulfilled":
    await session.execute(
        update(TrainSettings)
        .where(TrainSettings.user_id == user_id, or_( ... compare-and-set on settled_through ...))
```

New: insert the `complete_now` / `was_complete_before` early return between settle and the outcome choice (Pitfall 1).

**Analog for `complete_days_for`:** `settle_streak_snapshot` (956), which today queries:

```python
dates_result = await session.execute(
    select(DrillSession.session_date).where(
        DrillSession.user_id == user_id, DrillSession.status == "completed"
    )
)
```

Add the twin `BlunderCheckSession.session_date` query (sequential awaits, never `asyncio.gather`), combine via `day_is_complete`. Also stamp `has_material` in `_stamp_pool_eligibility` (826) with "BC size > 0".

**Settings:** `upsert_settings` (406) settles with OLD settings before writing (482-484); D-06 resize and the "today" `apply_day_completion` call go after the write, in that order.

---

### `app/repositories/blunder_check_repository.py` (repository)

**Analog for BC expiry:** `train_repository.expire_stale_sessions` (1139-1165):

```python
await session.execute(
    update(DrillSession)
    .where(
        DrillSession.user_id == user_id,
        DrillSession.status == "open",
        DrillSession.expires_on <= today,
    )
    .values(status="expired")
)
```

Extend with DELETE of `blunder_check_windows` where `started_at IS NULL` for the expired sessions (A9).

**Analog for completed-in-window guard:** `train_repository.completed_session_in_window` (1217): `status == 'completed' AND expires_on > today ORDER BY id DESC`, docstring opens with "Bug fix:" rationale.

**`complete_session` (732-742)** currently returns None; change to return whether the UPDATE moved a row (`result.rowcount == 1`) so a repeated finish does not re-trigger day completion:

```python
await session.execute(
    update(BlunderCheckSession)
    .where(BlunderCheckSession.id == session_id, BlunderCheckSession.status == "open")
    .values(status="completed", completed_at=now_utc)
    .execution_options(synchronize_session=False)
)
```

Cooldown filters: apply in `_unserved_qualifying_blunder_exists` (196) and `served_for_games` (447), with the pair set from RESEARCH "Cooldown pair set" (join `DrillSolve` -> `DrillSession` on `user_id` + `session_date >= cutoff`).

---

### `app/repositories/train_reminder_repository.py`

**Analog:** `has_completed_session_on` (148-170), an `exists()` select on `DrillSession.session_date == day AND completed_at IS NOT NULL`. Replace with "day complete" using the same `day_is_complete` rule and current settings (or call a shared repository helper from `train_repository`, keep it a single definition). Update `__all__`.

---

### `app/repositories/train_leaderboard_repository.py` (aggregate)

**Analog:** `fetch_week_aggregates` (63-105):

```python
stmt = (
    select(
        DrillSolve.user_id,
        func.coalesce(func.sum(_POINTS_EXPR), 0),
        func.count(),
        ...
        User.lichess_username, User.chess_com_username, User.is_guest, User.leaderboard_hidden,
    )
    .join(User, User.id == DrillSolve.user_id)
    .where(DrillSolve.solved_at >= week_start, DrillSolve.solved_at < week_end)
    .group_by(DrillSolve.user_id, User.id)
)
```

`fetch_week_bc_aggregates`: same shape over `BlunderCheckWindow` with `outcome IS NOT NULL` and `ended_at` in `[week_start, week_end)`, summing `points_scored`, `points_possible`, `count()`. Select columns only, never the `User` entity (oauth_accounts is lazy="joined").

---

### `app/services/train_leaderboard.py`

**Analog:** `_entry_for` (207-224) branches on `kind`; generalise to a per-board spec mapping rather than more `if kind ==`:

```python
is_public = not aggregate.is_guest and not aggregate.leaderboard_hidden
if kind == "points":
    return _Entry(aggregate.user_id, name, totals.points, totals.puzzles, False, is_public)
percent = accuracy_percent(totals.non_filler_points, totals.non_filler_puzzles)
...
    totals.non_filler_puzzles < ACCURACY_QUALIFY_MIN_PUZZLES,   # tentative flag
```

Constant at line 59: `ACCURACY_QUALIFY_MIN_PUZZLES: Final = 20` -> add `BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS: Final = 18` beside it. Tally fold at 456 `{"points": {}, "accuracy": {}}` must become a comprehension over all four kinds (else `KeyError`). `_order_key` = `(-value, -count, name.casefold(), key)` mirror for BC.

### `app/services/train_medals.py` / `app/repositories/train_medals_repository.py`

`_BOARDS: Final[tuple[LeaderboardBoardKind, ...]] = ("points", "accuracy")` (line 65) -> four keys; `finalize_due_weeks` (82-112) builds `NewStanding` per `kind in _BOARDS` from `final_standings(kind, aggregates)`: it needs the BC aggregates too (pass both, or let `final_standings` pick by kind). Repository line 187:

```python
# Alphabetical order would put 'accuracy' first; the Points board leads.
board_order = case((TrainWeeklyStanding.board == "points", 0), else_=1)
```

-> four-way `case(...)` (puzzle points, accuracy, bc points, bc score). Also `_BOARD_BY_TEXT`.

---

### `app/routers/blunder_check.py` (controller)

Remove (lines 80-87):

```python
async def current_beta_user(user: Annotated[User, Depends(current_active_user)]) -> User:
    """Authenticated user with beta access, else 403 (D-01: the API refuses too)."""
    if not user.beta_enabled:
        raise HTTPException(status_code=403, detail="Not available")
    return user

BetaUser = Annotated[User, Depends(current_beta_user)]
```

Replace every `BetaUser` with `user: Annotated[User, Depends(current_active_user)]` as in `app/routers/train.py:87` (import `from app.users import current_active_user`, line 63). Time via `NowUtc` / `dev_now_utc`. Keep `SessionIdPath`/`PositionPath` bounds.

---

### `app/schemas/train.py` (`TrainSettingsUpdate`, lines 743-770)

```python
timezone: str
weekday_mask: int = Field(ge=0, le=127)
puzzles_per_session: int = Field(ge=1, le=50)
...
reminder_intent_at: datetime | None
```

Change to `ge=0`; add `blunder_check_per_session: int | None = Field(default=None, ge=0, le=MAX)` and `blunder_check_level: BlunderCheckLevel | None = None` (optional, absent = keep stored, Pitfall 6: stale PWA bundles) and a `model_validator(mode="after")` for not-both-0 (422 instead of DB CHECK 500). Note the docstring's argument against defaulted fields: document why these two are the exception. Level type: `BlunderCheckLevel = Literal["beginner", "intermediate", "advanced"]`.

### `app/schemas/feature_route.py` (lines 18-32)

Append-only `FeatureRouteStepId` Literal; add the new step at the end, mirrored in `frontend/src/types/users.ts` and `FEATURE_ROUTE` (`frontend/src/lib/featureRoute.ts:82`), plus a new `RouteControlSlot` (line 19, e.g. `'train-blunder-check-start'`). A paired list test pins both sides.

---

### Frontend

**`frontend/src/lib/trainLeaderboard.ts`** (analog lines 16, 61-82) for the D-24 mode memory:

```ts
export const LEADERBOARD_TAB_STORAGE_KEY = 'flawchess_train_leaderboard_tab';
export function parseLeaderboardTab(value: string | null): LeaderboardBoardKind {
  return value === 'points' || value === 'accuracy' ? value : DEFAULT_LEADERBOARD_TAB;
}
export function readLeaderboardTab(): LeaderboardBoardKind {
  if (typeof localStorage === 'undefined') return DEFAULT_LEADERBOARD_TAB;
  try { return parseLeaderboardTab(localStorage.getItem(LEADERBOARD_TAB_STORAGE_KEY)); }
  catch { return DEFAULT_LEADERBOARD_TAB; }
}
export function writeLeaderboardTab(tab: LeaderboardBoardKind): void {
  if (typeof localStorage === 'undefined') return;
  try { localStorage.setItem(LEADERBOARD_TAB_STORAGE_KEY, tab); } catch { /* degrade */ }
}
```

Copy as `LEADERBOARD_MODE_STORAGE_KEY` + `parse/read/writeLeaderboardMode` (default `'puzzles'`). Also update `LEADERBOARD_TAB_TARGET`, `EMPTY_BOARD_COPY`, `boardValueLabel` for the new keys.

**`frontend/src/lib/trainRoute.ts`** (17-45): drop `'blunder-check'` from `TrainTab`, the union member, `TRAIN_TAB_PATHS` and the parse branch (unknown paths already redirect to Today, `Train.tsx:140-142`).

**`frontend/src/pages/Train.tsx`**: remove the beta redirect (161), `showBlunderCheck={isBeta}` (192), the BC panel (251-252); keep the immersive mechanism (`pageImmersive`, 137) but key it on the BC drill being active under Today.

**`frontend/src/components/train/TrainSubnav.tsx`**: drop `showBlunderCheck` prop and its conditional classes (34-39, 64-65, 83-84).

**`frontend/src/App.tsx`** (191-200): `trainWaitingCount = trainProgressQuery.data?.waiting_count` / `badge_visible` -> read `pending_count` (D-13); keep the guest gating untouched.

**Today card / settings rows:** extend `TrainStreakCard.tsx` (flame + `FreezeMeter`) with launcher rows per mode; `TrainScheduleSettings.tsx` hosts the per-mode collapsed rows and slider (its existing `puzzles_per_session` slider + PUT mutation is the pattern for the BC slider). Follow `frontend/CLAUDE.md` (theme tokens, `data-testid`, no Prettier, max-depth 4). One-time level step: reuse the layout of `TrainStartScreen.tsx` (being retired) for the level choice + how-it-works screen.

**Medals:** `medals/MedalClaimDialog.tsx` already lists every unclaimed medal in one dialog; add mode label per board and week grouping, keep `MEDAL_CLAIM_MAX_ITEMS`.

## Shared Patterns

### Auth / user scoping
**Source:** `app/routers/train.py:63, 87-92`. All BC and train routes depend on `current_active_user` (guests included); user id always from the dependency, never client input (V4/IDOR). Repository functions take `user_id` kw-only and scope every query by it.

### Time
**Source:** `dev_now_utc` / `NowUtc` dependency (`app/core/dev_clock.py`); day math only via `train_scheduler.local_today`, `session_window`, `is_session_expired`, `is_scheduled_day`.

### Streak mutation discipline
Single eager path through `_judge_one_day`; settle-before-mutate (`settle_streak_snapshot` first); compare-and-set writes on `settled_through`; sequential awaits on one `AsyncSession`.

### Error handling / Sentry
`sentry_sdk.capture_exception()` in non-trivial `except` blocks in services/routers; no variables in messages (use `set_context`). Validation errors are Pydantic 422s (Path bounds, `model_validator`), never DB CHECK 500s.

### Board-key enumeration
Every site that lists `"points"`/`"accuracy"` must become a mapping over four keys: `train_medals._BOARDS`, `_BOARD_BY_TEXT`, tally fold (`train_leaderboard.py:456`), `fetch_unclaimed` CASE (`train_medals_repository.py:187`), frontend `parseLeaderboardTab`, `LEADERBOARD_TAB_TARGET`, `EMPTY_BOARD_COPY`, `boardValueLabel`, analytics `LeaderboardTabId`. Grep `"accuracy"` in `app/` and `'accuracy'` in `frontend/src`.

### Comment bug fixes
Docstrings open with "Bug fix:" and explain what broke (see `completed_session_in_window`, `_pending_better_move_position`, migration downgrade).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| D-06 resize routine (in `blunder_check_repository` / `upsert_settings`) | repository | CRUD | No existing in-place session resize; closest is `_discard_if_untouched_and_resized` in `train_repository.py` (discards rather than resizes). Use RESEARCH Pattern 4 table. |

## Metadata

**Analog search scope:** `app/{models,repositories,services,routers,schemas}`, `alembic/versions`, `frontend/src/{pages,components/train,lib}`, `frontend/src/App.tsx`
**Files scanned:** ~25
**Pattern extraction date:** 2026-11-18
