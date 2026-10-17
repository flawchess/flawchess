# Phase 240: Train First-Session Onboarding Load - Pattern Map

**Mapped:** 2026-10-15
**Files analyzed:** 24 (new + modified, per RESEARCH "Recommended file touch list")
**Analogs found:** 24 / 24 (most files are self-analogs: modify in place following their own existing idiom)

All analog paths below are git-tracked source (no gitignored mirrors).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/2026xxxx_<rev>_phase_240_reveal_tour_stage.py` (NEW, `down_revision='778c806092fb'`) | migration | batch (DDL + backfill) | `alembic/versions/20260728_055940_f2624e60292e_phase_193_session_tick_shield.py` (+ `..._7d6bb75aae54_phase_222_train_onboarding_seen.py` for the column being dropped) | exact |
| `tests/test_migration_240_reveal_tour_stage.py` (NEW) | test | batch | `tests/test_migration_186_user_import_settings.py` | exact |
| `app/models/train_settings.py` | model | CRUD | itself: `shield_level` column + CHECK (lines 49-59, 76) | exact |
| `app/schemas/train.py` (`OnboardingStep` :723, response field :762) | model/schema | request-response | itself | exact |
| `app/repositories/train_repository.py` (`TrainSettingsRow`, 7 sites, new `advance_reveal_tour_stage`) | repository | CRUD | `stamp_onboarding_step` + `_ONBOARDING_COLUMNS` (lines 675-721) | exact |
| `app/repositories/train_repository.py` (first-ever check + `_first_session_order`) | repository/utility | transform | D-09 shuffle (line 2104), EXISTS idiom (line 618), compose flow (2515-2535) | exact |
| `app/routers/train.py` (`_settings_response` :486, endpoint :554-591) | controller | request-response | itself, `stamp_onboarding_step` endpoint | exact |
| `scripts/reset_train_state.py` (:28, :210) | utility | CRUD | itself | exact |
| `tests/routers/test_train.py`, `tests/repositories/test_train_repository.py`, `tests/scripts/test_reset_train_state.py` | test | request-response / CRUD | existing onboarding tests (`test_train.py:2662-2972`, `test_train_repository.py:3923-4012`) | exact |
| `frontend/src/lib/trainBotCopy.ts` | utility (pure copy) | transform | itself (`introSteps` 367-385, `walkthroughCopy` 681-708, `scoreBubbleCopy` 866-953) | exact |
| `frontend/src/hooks/useTrainWalkthrough.ts` | hook | event-driven | itself | exact |
| `frontend/src/hooks/useTrainOnboarding.ts` | hook | request-response | itself (lines 25-35) | exact |
| `frontend/src/types/train.ts` (:379), `frontend/src/api/client.ts` (:347) | model | request-response | itself | exact |
| `TrainSolveScreen.tsx`, `TrainReveal.tsx`, `TrainVerdictStrip.tsx`, `TrainMoveTreeList.tsx`, `TrainRevealActionBar.tsx`, `TrainTourOverlay.tsx`, `trainBubbleState.ts` | component | event-driven | ring sites listed under Shared Pattern "Tour spotlight" | role-match |
| `TrainScoreScreen.tsx` (222-254), `TrainStartScreen.tsx` (:251) | component | request-response | itself | exact |
| `frontend/src/lib/mobileBoardControls.ts`, `frontend/src/App.tsx` | store/provider | pub-sub | itself (payload fields) | exact |
| `frontend/src/index.css` (new `@keyframes tour-spotlight-pulse`) | config (CSS) | n/a | `@keyframes arrow-pulse` / `row-highlight-pulse` (index.css:314-343), reduced-motion block (:529-535) | exact |
| `frontend/src/lib/theme.ts` (glow color constant) | config | n/a | `FLAW_FIXED_GLOW` in `TrainFlawFixedBanner.tsx:27-30` | exact |
| FE tests (`trainBotCopy.test.ts`, `TrainSolveScreen.test.tsx`, `TrainStartScreen.test.tsx`, `TrainScoreScreen.test.tsx`, `TrainReminderButton.test.tsx`, `Train.solveLoop.test.tsx`, `trainBubbleState.test.ts`) | test | n/a | themselves (fixture field rename + count assertions) | exact |
| `CHANGELOG.md` | config/docs | n/a | `## [Unreleased]` (line 9) | exact |

## Pattern Assignments

### Migration (NEW) — analog `alembic/versions/20260728_055940_f2624e60292e_phase_193_session_tick_shield.py`

Copy: module docstring explaining decision + reversibility; hard-coded literal CHECK bound (not imported constant); `op.execute` for data step; downgrade documented as schema-reversible only.

```python
revision: str = 'f2624e60292e'
down_revision: Union[str, Sequence[str], None] = '127c8bd364a6'
...
def upgrade() -> None:
    op.add_column(
        "train_settings",
        sa.Column("shield_level", sa.SmallInteger(), server_default="0", nullable=False),
    )
    # Literal bound, not an f-string off SHIELD_CAP — migrations are frozen
    # artifacts; the model derives the same bound from SHIELD_CAP at import
    # time, but this file must stand on its own forever.
    op.create_check_constraint(
        "ck_train_settings_shield_level", "train_settings", "shield_level BETWEEN 0 AND 7"
    )
    op.execute("UPDATE train_settings SET streak_count = 0, streak_settled_through = NULL")
```

Phase 240 shape (order matters: add, backfill, then drop):
```python
down_revision = '778c806092fb'   # current head (users_unique_index_on_lower_email)
op.add_column("train_settings", sa.Column("reveal_tour_stage", sa.SmallInteger(), server_default="0", nullable=False))
op.create_check_constraint("ck_train_settings_reveal_tour_stage", "train_settings", "reveal_tour_stage BETWEEN 0 AND 3")
op.execute("UPDATE train_settings SET reveal_tour_stage = 3 WHERE reveal_walkthrough_seen_at IS NOT NULL")
op.drop_column("train_settings", "reveal_walkthrough_seen_at")
```
Downgrade: re-add `reveal_walkthrough_seen_at` as in phase 222 (`sa.Column("reveal_walkthrough_seen_at", sa.DateTime(timezone=True), nullable=True)`), optionally `UPDATE ... SET reveal_walkthrough_seen_at = now() WHERE reveal_tour_stage = 3` (data approximate, doc it), drop constraint then column.

---

### `tests/test_migration_240_reveal_tour_stage.py` (NEW) — analog `tests/test_migration_186_user_import_settings.py`

Constants + Alembic-in-thread helpers (lines 20-62):
```python
TARGET_REVISION: str = "head"
BASE_REVISION: str = "411a8de89c4b"  # down_revision of the migration  -> "778c806092fb"
CHECK_CONSTRAINT: str = "ck_user_import_settings_cap"
_TEST_USER_GRANDFATHERED: int = 999_500   # pick a fresh unused 999_xxx range
pytestmark = pytest.mark.asyncio

def _make_alembic_cfg() -> AlembicConfig:
    from app.core.config import settings
    cfg = AlembicConfig("alembic.ini")
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg

async def _run_upgrade(revision: str = TARGET_REVISION) -> None:
    await asyncio.to_thread(alembic_command.upgrade, _make_alembic_cfg(), revision)
async def _run_downgrade(revision: str = BASE_REVISION) -> None:
    await asyncio.to_thread(alembic_command.downgrade, _make_alembic_cfg(), revision)
```
Helpers (`_check_constraint_exists` via `pg_constraint`, `_insert_user` with `ON CONFLICT (id) DO NOTHING`, `_cleanup`) at lines ~105-146. Test shape (line 152): upgrade -> assert -> downgrade -> assert -> always end at head. Tests to write: (1) downgrade to base, insert user + train_settings row with `reveal_walkthrough_seen_at` set and one NULL, upgrade, assert stage 3 / 0 and column gone; (2) CHECK rejects stage 4 with `pytest.raises(IntegrityError)` (line 212 pattern); (3) downgrade/upgrade round trip.

---

### `app/models/train_settings.py` — self-analog

`__table_args__` CHECK (lines 49-59), f-string off a named constant:
```python
CheckConstraint(
    f"shield_level BETWEEN 0 AND {SHIELD_CAP}", name="ck_train_settings_shield_level"
),
```
Add `CheckConstraint(f"reveal_tour_stage BETWEEN 0 AND {REVEAL_TOUR_STAGE_MAX}", name="ck_train_settings_reveal_tour_stage")`. Replace `reveal_walkthrough_seen_at` (lines 144-146) with a `Mapped[int] = mapped_column(SmallInteger, server_default="0", nullable=False)` modeled on `shield_level` (~line 76). Constant lives next to `SHIELD_CAP` (RESEARCH suggests `app/services/train_scheduler.py`).

---

### `app/repositories/train_repository.py` — stage advance; analog lines 675-721

```python
_ONBOARDING_COLUMNS: dict[OnboardingStep, Any] = {
    "intro": TrainSettings.intro_seen_at,
    "reveal_walkthrough": TrainSettings.reveal_walkthrough_seen_at,   # DELETE
    "sr_explained": TrainSettings.sr_explained_at,
}

async def stamp_onboarding_step(session, *, user_id, step, now_utc) -> TrainSettingsRow:
    await get_or_create_settings(session, user_id=user_id)
    column = _ONBOARDING_COLUMNS[step]
    # Guarded on IS NULL: a replayed POST ... can never move an already-stamped timestamp
    await session.execute(
        update(TrainSettings)
        .where(TrainSettings.user_id == user_id, column.is_(None))
        .values({column: now_utc})
    )
    refreshed = await get_settings(session, user_id=user_id)
    assert refreshed is not None  # get_or_create_settings above guarantees the row exists.
    return refreshed
```
New `advance_reveal_tour_stage`: same skeleton, fixed dict `_REVEAL_TOUR_TARGET_STAGE = {"reveal_tour_1": 1, "reveal_tour_2": 2, "reveal_tour_3": 3}`, guard `TrainSettings.reveal_tour_stage == target - 1` (RESEARCH Pattern 1 has full draft). Narrow `_ONBOARDING_COLUMNS` key type to a `TimestampOnboardingStep = Literal["intro", "sr_explained"]`. Also update `TrainSettingsRow` (:180), `get_settings` (:319), `get_or_create_settings` (:367/:388), `upsert_settings` RETURNING (:519/:530/:546), `get_progress` (:850).

### `app/repositories/train_repository.py` — first-ever reorder; analogs

D-09 shuffle (line 2101-2104) — the reorder runs immediately after, with a distinct seed suffix:
```python
# D-09: deterministic (user_id, session_date)-seeded shuffle so a red
# herring's slot is never inferable ...
random.Random(f"{user_id}:{today.isoformat()}").shuffle(reconstructed)
```
EXISTS idiom (line 618):
```python
select(select(DrillItem.user_id).where(DrillItem.user_id == user_id).exists())
```
-> `select(select(DrillSession.id).where(DrillSession.user_id == user_id).exists())`.
Placement in `compose_and_materialize_session` (lines 2522-2528): after `_resolve_existing_session` returns `None` (discard DELETE at :1572 is already executed), before `items = await _assemble_session_items(...)`. Type source: `answer_key_for` / `classify_puzzle_type` in `app/services/train_pool.py:363-392` (herring -> "herring", SHARP_FILLER -> "sharp", SR -> blob). Pure helper `_first_session_order` draft in RESEARCH Pattern 5; keep depth <= 3 with guard clauses; constants `_FIRST_SESSION_SEVERAL_SLOTS = (1, 2)`.

---

### `app/routers/train.py` endpoint (lines 554-591) — self-analog

```python
@router.post("/onboarding/{step}", response_model=TrainSettingsResponse)
async def stamp_onboarding_step(
    step: OnboardingStep,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
) -> TrainSettingsResponse:
    try:
        settings_row = await train_repository.stamp_onboarding_step(
            session, user_id=user.id, step=step, now_utc=now_utc
        )
        await session.commit()
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("train", {"user_id": str(user.id)})
        sentry_sdk.capture_exception()
        raise
    return await _settings_response(session, settings_row, user_id=user.id)
```
Add one guard-clause dispatch inside the `try` (`if is_reveal_tour_step(step): advance_reveal_tour_stage(...) else: stamp_onboarding_step(...)`), TypeGuard helper for ty narrowing. Update the docstring "three names". `_settings_response` (:486) swaps the field.

---

### `frontend/src/hooks/useTrainOnboarding.ts` — self-analog (lines 25-35)

```ts
export type OnboardingStep = 'intro' | 'reveal_walkthrough' | 'sr_explained';
...
mutationFn: trainApi.stampOnboarding,
onSuccess: (data) => { queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data); },
```
New literal: `'intro' | 'sr_explained' | \`reveal_tour_${1 | 2 | 3}\`` mirroring the server exactly.

### `frontend/src/hooks/useTrainWalkthrough.ts` — self-analog

Replace gate at :107 (`settings.reveal_walkthrough_seen_at !== null`), `useState<WalkthroughStep>(0)` (:140), `isLastStep` (:148), `leave()` stamp (:196-199). Latch part per reveal (RESEARCH Pattern 3 draft), clear in `reset()`.

### `frontend/src/lib/trainBotCopy.ts` — self-analog

Intro: `IntroStep` (:282) -> `0 | 1`; delete :310-327, :341-354; `introSteps` (:367-385) / `introStepCount` (:389) / `introCopy` (:399-409) drop `isWarmup`. Tour: replace `WalkthroughStep`/`WALKTHROUGH_STEP_COUNT` (:605-606) and `walkthroughCopy` (:681-708) with `TourStepId`/`TourPart`/`tourPartSteps`/`tourStepCopy` (RESEARCH Pattern 2); keep `WalkthroughTarget` (:616), `TOUR_ICON_TOKEN` (:642-646); add `answerKind` to `WalkthroughContext` (:632-636). Score: `scoreBubbleCopy` (:866-953) per copy-sheet table, delete `returningCountsSentence` and orphan `ScoreBubbleInput` fields / `ScoreBubbleOutcome` (knip).

### `TrainScoreScreen.tsx` (222-254) — self-analog

Widen stamp gate at :248 (`firstExplanation && !isWarmup && missedCount > 0`) to "first-completed variant rendered in any branch" (D-21). Drop `sessionDate`/`expiresOn` props (:132-139) and the feeders in `pages/Train.tsx:260-261` if unused.

### `TrainStartScreen.tsx` :251 — `const onboardingDone = settings?.reveal_walkthrough_seen_at != null;` -> `settings !== undefined && settings.reveal_tour_stage >= REVEAL_TOUR_DONE_STAGE` (named constant, D-22). Same swap at `TrainSolveScreen.tsx:1690` (`tourMaybePending`).

### `TrainTourOverlay.tsx` — `TourStepCount` "n / m" (line 62) fed by part length (D-23); mount at `TrainSolveScreen.tsx:997-1038` passes `stepCount={WALKTHROUGH_STEP_COUNT}` today -> `tourPartSteps(part).length`.

## Shared Patterns

### Tour spotlight (D-20) — source `TrainFlawFixedBanner.tsx:27-30` + `index.css:314-343, 529-535`
```ts
/** Bronze border + halo, identical to the homepage feature-card treatment */
const FLAW_FIXED_GLOW =
  'border border-[rgba(205,127,50,0.85)] shadow-[0_0_24px_rgba(205,127,50,0.35)]';
```
```css
@keyframes arrow-pulse { 0% { opacity: 0.45; } 50% { opacity: 1; } 100% { opacity: 0.75; } }
.animate-arrow-pulse { animation-name: arrow-pulse; animation-timing-function: ease-in-out; animation-fill-mode: forwards; }
...
@media (prefers-reduced-motion: reduce) {
  ...
  .animate-medal-pop { animation: none; }
}
```
New: `@keyframes tour-spotlight-pulse` animating `box-shadow` between two alphas of `rgba(205,127,50,…)`, `infinite` iteration (unlike arrow-pulse's inline-count), class `.tour-spotlight` = static box-shadow ring + animation; append `.tour-spotlight { animation: none; }` to the existing reduced-motion block at :529. Use `box-shadow` only (no border) so no layout shift. Put the color in `theme.ts` (or a CSS var) and have `FLAW_FIXED_GLOW` keep its value. Replace these ring sites with the one shared class:
- `TrainVerdictStrip.tsx:63`, `:152` (`ring && 'ring-2 ring-brand-brown'`)
- `TrainMoveTreeList.tsx:106`
- `TrainReveal.tsx:420-428` (lines box)
- `TrainSolveScreen.tsx:1886` (board, with ring-offset; check `overflow` clipping)
- `TrainBotBubble.tsx:144` (verdict card ring on desktop)
- NEW: chips row container in `TrainReveal.tsx`, action bar (`TrainRevealActionBar.tsx:103-105` comment explains why it was removed; phone bar needs a payload flag through `mobileBoardControls.ts` -> `App.tsx` `MobileBottomBar`).
- Do NOT touch `TrainLineChips.tsx:93` (chip selection ring) or `TrainTourOverlay.tsx:94` (reopen badge).

### Fixed-dict, no-getattr (T-222-02-03)
Source `train_repository.py:675-684` comment + dict. Apply to the stage map.

### Sentry in routers
Source `routers/train.py:581-588` (set_context with user_id, capture_exception, re-raise, no variables in message).

### Named constants
`SHIELD_CAP` used in model CHECK f-string; migration hard-codes the literal. Same for `REVEAL_TOUR_STAGE_MAX = 3`; frontend mirrors with `TOUR_PART_COUNT = 3`.

## No Analog Found

None. The first-session reorder helper is new logic but sits beside the D-09 shuffle; follow RESEARCH Pattern 5 draft.

## Metadata

**Analog search scope:** `alembic/versions/`, `tests/`, `app/models`, `app/repositories`, `app/routers`, `frontend/src/{index.css,components/train,hooks}`
**Files scanned:** ~15
**Pattern extraction date:** 2026-10-15
