# Phase 249: Blunder-Check Playable MVP - Pattern Map

**Mapped:** 2026-11-10
**Files analyzed:** 24 (new + modified)
**Analogs found:** 22 / 24

All analog paths below are git-tracked source (no gitignored mirrors).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/models/blunder_check.py` (Session, Window, Answer + IntEnums) | model | CRUD | `app/models/drill_session.py`, `app/models/drill_solve.py` | exact |
| `alembic/versions/<ts>_phase_249_blunder_check_tables.py` | migration | DDL | `alembic/versions/20261109_120000_c4e9b1d7f248_phase_248_maia_refutation.py` (header/revision shape) | role-match |
| `alembic/env.py` (register new models) | config | - | existing `from app.models.drill_session import DrillSession  # noqa: F401` (line 25) | exact |
| `app/services/blunder_check_rules.py` (ported pure fns + constants) | utility (pure) | transform | `scripts/blunder_check/metrics.py`, `scripts/blunder_check/spot_check.py:130-137` | exact (port) |
| `scripts/blunder_check/metrics.py`, `spot_check.py` (re-export app versions) | utility | transform | themselves | modify |
| `app/services/blunder_check_selection.py` (game-first composer) | service | batch/transform | `scripts/blunder_check/spot_check.py` `pick_windows` (230) + `sample.py` loader (425-448, 540-578) | role-match |
| `app/services/blunder_check_service.py` (grade_answer, better-move resolve, points) | service | request-response | `app/repositories/train_repository.py` `_resolve_grade` (3251-3290), `app/services/train_score.py` | role-match |
| `app/repositories/blunder_check_repository.py` | repository | CRUD | `app/repositories/train_repository.py` (compose SAVEPOINT 2485-2575, claim query 1585-1600) | exact |
| `app/schemas/blunder_check.py` | schema | request-response | `app/schemas/train.py` (`ServerGradedMove` 42, `SolveRequest` 473) | exact |
| `app/routers/blunder_check.py` (prefix `/blunder-check`, beta dep) | controller/router | request-response | `app/routers/train.py` (1-80, 84-150) | exact |
| `app/main.py` (include router) | config | - | `app/main.py:34` train_router import + `include_router(..., prefix="/api")` | exact |
| `tests/services/test_blunder_check_rules.py` | test | unit | `tests/scripts/test_blunder_check_metrics.py` | exact |
| `tests/routers/test_blunder_check.py` | test | integration | `tests/routers/test_train.py` (1131 payload shape, 1528 concurrency) | exact |
| `tests/models/test_blunder_check_schema.py` | test | schema | none direct | partial |
| `frontend/src/lib/trainRoute.ts` | utility | routing | itself | modify |
| `frontend/src/components/train/TrainSubnav.tsx` | component | nav | itself | modify |
| `frontend/src/pages/Train.tsx` | page | layout | itself (lines 107-156) | modify |
| `frontend/src/api/client.ts` (`blunderCheckApi`) | api client | request-response | `trainApi` (client.ts:326-345) | exact |
| `frontend/src/types/blunderCheck.ts` | types | - | `frontend/src/types/train.ts` | exact |
| `frontend/src/hooks/useBlunderCheckSession.ts` | hook | request-response | `frontend/src/hooks/useTrainSession.ts` (167-240) | role-match |
| `frontend/src/hooks/useMoveTimer.ts` | hook | event-driven | none (deadline countdown is new) | no analog |
| `frontend/src/lib/blunderCheckDrill.ts` (pure reducer) | utility | state machine | none (Train state lives in hooks) | no analog |
| `frontend/src/components/train/blunder-check/*` (Tab, Start, Drill, Solution, End, PointsFlash) | component | presentation | `TrainSolveScreen.tsx` (sounds 1557-1583), `TrainRevealGameFooter.tsx`, `TrainScoreScreen.tsx`/`TrainScoreBadge.tsx` | role-match |

## Pattern Assignments

### `app/models/blunder_check.py` (model, CRUD)

**Analog A:** `app/models/drill_session.py` (sessions table). Imports and partial unique open index (lines 21-63):
```python
from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, Text, func, text)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

    __table_args__ = (
        CheckConstraint("status IN ('open', 'completed', 'expired')", name="ck_drill_sessions_status"),
        Index("uq_drill_sessions_user_open", "user_id", unique=True,
              postgresql_where=text("status = 'open'")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # TEXT + CHECK per CLAUDE.md DB rules (low-volume domain column)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```
Copy for `blunder_check_sessions` (status `('open','completed')`, `window_count` SmallInteger, no `session_date`/`expires_on`). Keep a module docstring explaining deletion semantics like drill_session.py lines 1-17.

**Analog B:** `app/models/drill_solve.py` (windows + answers). IntEnum + SMALLINT CHECK (lines 87-130) and SET NULL game FK (151):
```python
class DrillMoveQuality(IntEnum):
    WRONG = 0
    INACCURACY = 1
    GOOD = 2
...
        CheckConstraint("source IN (0, 1, 2)", name="ck_drill_solves_source"),
        CheckConstraint("guess IS NULL OR guess IN (0, 1)", name="ck_drill_solves_guess"),
    session_id: Mapped[int] = mapped_column(ForeignKey("drill_sessions.id", ondelete="CASCADE"), primary_key=True)
    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id", ondelete="SET NULL"), nullable=True)
```
New IntEnums: `WindowCase` (HERRING=0, ALLOWED=1, PURE_MISS=2, MIXED=3), `WindowOutcome` (CLEARED..VOID 0-4), `AnswerKind` (SAFE/BLUNDER/TIMEOUT), `AnswerResult` (0-5). Reuse `DrillMoveQuality` for `better_move_tier`. If any JSONB is added, use `JSONB(none_as_null=True)` (drill_solve.py:186-213). Nullable answer columns (`answer`, `result`) use the `IS NULL OR col IN (...)` CHECK form.

---

### `alembic/versions/<ts>_phase_249_blunder_check_tables.py` (migration)

**Analog:** `alembic/versions/20261109_120000_c4e9b1d7f248_phase_248_maia_refutation.py`. Copy docstring layout (phase + decision ids + rationale), and revision header:
```python
revision: str = "<new>"
down_revision: Union[str, Sequence[str], None] = "c4e9b1d7f248"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
Body: `op.create_table` x3 with named CHECKs matching the model, partial unique index via `op.create_index(..., unique=True, postgresql_where=sa.text("status = 'open'"))`, index `(user_id, game_id)` on windows, and (planner's call, per RESEARCH prod probe) partial index `games (user_id, id) WHERE full_evals_completed_at IS NOT NULL`. Downgrade drops in reverse order. Verify with `uv run alembic check` (no autogenerate drift vs models). Register models in `alembic/env.py` next to line 25.

---

### `app/services/blunder_check_rules.py` (pure utility)

**Analog:** `scripts/blunder_check/metrics.py` (lines 1-62 header, functions at 63-254). Import block to copy verbatim:
```python
from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict

from app.repositories.query_utils import mover_is_white_at_ply
# Private import by design: the threshold and the per-ply entry shape must be the classifier's
# own, never re-derived (precedent: scripts/remote_eval_worker.py imports _run_all_moves_pass).
from app.services.flaws_service import INACCURACY_DROP, _MoveEntry  # noqa: PLC2701
from app.services.maia_flaw_stats import RANK_BASE
```
Move: `HAZARD`, `WINDOW_LENGTHS`, `LEAD_IN_PLIES`, `MAX_BLUNDER_POSITION`, `MissCase`, `MoveJudgement` (63), `HazardWeights` (71), `user_move_judgements` (84), `blunder_es` (102), `miss_case` (116), `in_band` (132), `blunder_fits_position` (137), `hazard_position_weights` (156), `FindabilityInputs` (179), `_pair_passes` (202), `findable` (209), `herring_flags` (234), `count_herring_windows` (243); from `spot_check.py`: `WindowShape` (60) and `draw_window_shape` (130-137):
```python
def draw_window_shape(rng: random.Random) -> WindowShape:
    length = rng.choice(WINDOW_LENGTHS)
    for position in range(1, length + 1):
        if rng.random() < HAZARD:
            return WindowShape(length, position)
    return WindowShape(length, None)
```
Do NOT move `MAX_MISS_SHARE`, `capped_blunder_supply`, `elo_bucket`, `auc`, `quartiles`, `flaw_control`, `SupplyRates`, `estimated_user_windows`, `weighted_fit_share` (D-07; report-only). Add new constants `REFUTATION_PROB_MIN = 0.3`, `BEST_PROB_MIN = 0.2`, `ES_BAND_LOW = 0.10`, `ES_BAND_HIGH = 0.90`, `BLUNDER_CHECK_SESSION_WINDOWS = 6`, and `max_fit_position` (RESEARCH Pattern 1). Then in `scripts/blunder_check/metrics.py`/`spot_check.py` replace definitions with `from app.services.blunder_check_rules import ...` re-exports so `tests/scripts/test_blunder_check_metrics.py` stays unchanged.

---

### `app/services/blunder_check_selection.py` (service, batch)

**Analog:** `scripts/blunder_check/spot_check.py` `pick_windows` (230-268, `used` set = one window per game) + `_herring_candidates` (139) + `_blunder_window`/`_herring_window` (204-229); loader logic from `scripts/blunder_check/sample.py` 425-448 (contiguity skip), 540-578 (`_run_all_moves_pass` call). Core judging loop (RESEARCH "Code Examples"):
```python
all_moves = _run_all_moves_pass(positions)
judg = user_move_judgements(all_moves, [p.ply for p in positions if p.move_san], user_is_white)
es_before, es_played, es_ref = blunder_es(all_moves, flaw.ply)
case = miss_case(flaw.is_miss, es_ref, es_played)
```
Inject `rng: random.Random` as a parameter (deterministic tests). No SQL in this module: call repository loaders sequentially (never `asyncio.gather` on one session). Foreign fallback uses `pinned_elo_for_mover` (`app/services/best_move_candidates.py:79`). Full FEN/UCI via `replay_at_ply` (`app/services/train_pool.py:1507`), never `game_flaws.fen`.

---

### `app/services/blunder_check_service.py` (service, grading)

**Analog:** `_resolve_grade` (`app/repositories/train_repository.py:3251-3290`) precedence:
```python
    graded = _matching_server_graded_move(played_move, classification.graded_moves)
    if graded is not None:
        return ResolvedGrade(effective_quality=graded.tier, ...)
    ...
    return ResolvedGrade(effective_quality=client_tier, ...)
```
MVP keeps step 1 and 3 only (no recheck/disagreement). Graded set: `server_graded_moves_for` (train_pool.py:645), `answer_key_for` (370), `legal_server_graded_moves` (690). Points: reuse `MOVE_TIER_POINTS` from `app/services/train_score.py:24-32`. Pure `grade_answer` per RESEARCH Pattern 4; constants `SAFE_POINTS=1`, `BLUNDER_POINTS=3`, `BETTER_MOVE_POINTS=2`, `MOVE_TIMER_SECONDS=15`, `PROMPT_ANIMATION_ALLOWANCE_S`, `NETWORK_GRACE_S`. Return types as frozen dataclasses with `Literal` fields.

---

### `app/repositories/blunder_check_repository.py` (repository, CRUD)

**Analog:** `app/repositories/train_repository.py`.

**SAVEPOINT + IntegrityError resume** (2492-2575):
```python
    try:
        async with session.begin_nested():
            drill_session = DrillSession(user_id=user_id, ..., status="open", ...)
            session.add(drill_session)
            # surface uq_drill_sessions_user_open here if a concurrent request already won
            await session.flush()
            for position, puzzle in enumerate(items.reconstructed):
                session.add(DrillSolve(session_id=drill_session.id, position=position, ..., solved_at=None))
            await session.flush()
    except IntegrityError:
        resumed = await open_session_for_user(session, user_id=user_id)
        if resumed is None:
            raise
        return await _resume_session(...)
```
**User-scoped unclaimed-row query** (1589-1598):
```python
    stmt = (
        select(DrillSolve, Game, HerringPool)
        .outerjoin(Game, Game.id == DrillSolve.game_id)
        .where(DrillSolve.session_id == session_id, DrillSolve.user_id == user_id,
               DrillSolve.solved_at.is_(None))
        .order_by(DrillSolve.position.asc())
    )
```
Answer claim: `update(BlunderCheckAnswer).where(window_id==, move_index==, answered_at.is_(None)).values(...).returning(...)`; 0 rows = double submit. Every query filters by `user_id` (V4). Ply parity via `mover_is_white_at_ply` / `is_opponent_expr` (`app/repositories/query_utils.py:21,61-68`). Candidate pick must gate `full_evals_completed_at IS NOT NULL` and `platform IN ANALYTICS_INCLUDED_PLATFORMS`; foreign batch joins `users` and excludes `is_guest`.

---

### `app/schemas/blunder_check.py` (schema)

**Analog:** `app/schemas/train.py` (`ServerGradedMove` line 42 with "wire twin" docstring; `SolveRequest` 473). Pydantic v2 `BaseModel`, `Literal["safe","blunder","timeout"]`, bounded ints (`Field(ge=1, le=5)` for move_index), UCI regex `^[a-h][1-8][a-h][1-8][qrbn]?$`. Pre-end response models must not contain `game_id`, ply, case, reply-ahead, or remaining count (D-16).

---

### `app/routers/blunder_check.py` (router)

**Analog:** `app/routers/train.py`. Imports + constants (21-80):
```python
import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.dev_clock import dev_now_utc
from app.models.user import User
from app.users import current_active_user

router = APIRouter(prefix="/train", tags=["train"])
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]
_SESSION_ID_MAX: Final = 2**31 - 1
```
Handler shape with commit/rollback + Sentry (84-104):
```python
@router.post("/sessions", response_model=TrainSessionResponse)
async def compose_or_resume_session(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
) -> TrainSessionResponse:
    try:
        composed = await train_repository.compose_and_materialize_session(session, user_id=user.id, now_utc=now_utc)
        await session.commit()
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("train", {"user_id": str(user.id)})
        sentry_sdk.capture_exception()
        raise
```
Use `prefix="/blunder-check", tags=["blunder-check"]`; replace `current_active_user` with a new `current_beta_user` dependency (RESEARCH Pattern 7; `users.beta_enabled` at `app/models/user.py:40-47`; no backend beta dependency exists today). Router maps service dataclasses to schemas field-by-field (train.py 105-150). Register in `app/main.py` like line 34 + `app.include_router(..., prefix="/api")` (285+).

---

### `tests/routers/test_blunder_check.py` (integration test)

**Analog:** `tests/routers/test_train.py`. Payload-shape equality test (1131-1165):
```python
    email = f"train-shape-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    game_id = await _seed_game_with_blunder(test_engine, user_id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(ENDPOINT, headers={"Authorization": f"Bearer {token}"})
        assert set(puzzle.keys()) == {...}   # equality, never membership
    finally:
        await _delete_games(test_engine, [game_id])
```
Concurrency test (1528+): two independent `httpx.AsyncClient`s, assert one open session. Add a beta fixture (register then flip `beta_enabled`), and a `seed_blunder_check_game` helper with contiguous `game_positions`, `full_evals_completed_at`, `best_move` at blunder plies, severity-2 user flaws with Maia pairs; always `finally` cleanup (tier-3 lottery isolation).

### `tests/services/test_blunder_check_rules.py`
**Analog:** `tests/scripts/test_blunder_check_metrics.py` (same fixtures for `_MoveEntry` dicts); add seeded-RNG hazard frequency test and `max_fit_position` monotonicity.

---

### Frontend: `frontend/src/lib/trainRoute.ts` (modify)
Extend (lines 17-43):
```ts
export type TrainTab = 'today' | 'leaderboard' | 'archive';
export const TRAIN_TAB_PATHS: Record<TrainTab, string> = { today: '/train', leaderboard: '/train/leaderboard', archive: '/train/archive' };
export function parseTrainRoute(pathname: string): TrainRoute | null { ... return null; }
```
Add `'blunder-check'` -> `/train/blunder-check` and a beta-aware parse (null for non-beta, which Train.tsx already redirects to Today). Update existing `trainRoute` tests.

### `frontend/src/components/train/TrainSubnav.tsx` (modify)
Add a fourth `TabsTrigger value="blunder-check" data-testid="tab-train-blunder-check"` behind a `showBlunderCheck` prop, same `className="flex-1"` + lucide icon pattern. No Umami tab-switch event (docstring).

### `frontend/src/pages/Train.tsx` (modify)
Beta flag from `useUserProfile()` (line 112 already destructures `profile`; read `profile?.beta_enabled`, never `useAuth().user`). Render `BlunderCheckTab` for the new route without triggering `useTrainLoop`'s Today path; separate immersive flag so `{!immersive && <TrainSubnav .../>}` (line 156) hides during a window.

### `frontend/src/api/client.ts` + `frontend/src/types/blunderCheck.ts`
Copy `trainApi` object style (client.ts:326-345):
```ts
export const trainApi = {
  composeOrResumeSession: () => apiClient.post<TrainSessionResponse>('/train/sessions').then(r => r.data),
  solvePuzzle: (sessionId: number, data: SolveRequest) =>
    apiClient.post<SolveResponse>(`/train/sessions/${sessionId}/solve`, data).then(r => r.data),
```
Types mirror the Pydantic schemas with string-literal unions.

### `frontend/src/hooks/useBlunderCheckSession.ts`
**Analog:** `useTrainSession.ts:167-240`: `useMutation({ mutationFn: trainApi.x, onSuccess })`, seed state from server payload on start, never re-derive points client-side (here: display server `window_points`/`points_awarded` directly, Pitfall 13). Every query needs an `isError` branch.

### `frontend/src/components/train/blunder-check/*`
- Sounds: copy the selection from `TrainSolveScreen.tsx:1572-1583` (`'score-full' | 'score-partial' | 'game-loss'` via `playSound` from `frontend/src/lib/sounds.ts`); forfeit uses `'game-loss'`.
- Board: `ChessBoard` + `BoardArrow`, container `data-testid="chessboard" id="chessboard"`, drag-drop and click-click for the better-move step.
- Better-move grading: `useTrainGradingEngine` (`startGrading(fen, keyUci)`, `gradeMove`).
- Solution: `useTrainRevealTree`, `TrainLineChips`, `TrainMoveTreeList`, `buildTrainPuzzleAnalysisUrl(gameId, ply)` (`frontend/src/lib/analysisUrl.ts:111-123`); game footer: narrow variant of `TrainRevealGameFooter.tsx` (takes `gameId`, `isOwn`) on `useLibraryGame`; copy says "the player" when `!isOwn`.
- End screen: `TrainScoreBadge` for Score %.
- PointsFlash: extract from TrainSolveScreen's `pointsFlash` + `TRAIN_POINTS_FLASH_COLORS` into a small component (colors stay in `theme.ts`).
- Buttons: `Button` variants `default` (primary) / `brand-outline`; `text-sm` minimum; `data-testid` on every interactive element (`blunder-check-btn-safe`, `-btn-blunder`, `-btn-start`).

## Shared Patterns

### Auth / beta gate
**Source:** `app/users.current_active_user` (used throughout `app/routers/train.py`). New `current_beta_user` wraps it and 403s when `not user.beta_enabled`. Apply to every `/blunder-check` route. User id only from the dependency; every repository query filters by `user_id`, 404 on foreign ids.

### Error handling / Sentry
**Source:** `app/routers/train.py:96-103`. try/commit, except: rollback, `sentry_sdk.set_context("blunder_check", {...})`, `capture_exception()`, re-raise. No variables in exception messages.

### Time
**Source:** `NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]` (`train.py:68`). Use for `prompted_at`, `answered_at`, timeout ceiling, `started_at/ended_at`.

### Input bounds
**Source:** `_SESSION_ID_MAX`, `_DRILL_POSITION_MAX` with `Path(ge=..., le=...)` (`train.py:70-75`).

### Concurrency
Partial unique open index + SAVEPOINT + IntegrityError resume (train_repository.py:2492-2575); pre-inserted rows + claiming UPDATE `WHERE answered_at IS NULL`.

### Classifier reuse
`_run_all_moves_pass` (`app/services/flaws_service.py:373`), `INACCURACY_DROP` (47), with `# noqa: PLC2701` private-import precedent (`scripts/blunder_check/metrics.py:23-28`). Never re-derive ES/severity in SQL.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/hooks/useMoveTimer.ts` | hook | event-driven | No deadline countdown exists; use RESEARCH Pattern 6 (fires once, pauses during animations) |
| `frontend/src/lib/blunderCheckDrill.ts` | pure reducer | state machine | Train keeps state in hooks; build pure reducer (vitest-tested) per RESEARCH Q5 state list |
| `tests/models/test_blunder_check_schema.py` | test | schema | Partial: rely on `alembic check` plus CHECK/FK assertions |

## Metadata

**Analog search scope:** `app/models`, `app/routers`, `app/repositories`, `app/services`, `app/schemas`, `alembic/versions`, `scripts/blunder_check`, `tests/routers`, `frontend/src/{lib,hooks,api,components/train,pages}`
**Files scanned:** ~20
**Pattern extraction date:** 2026-11-10
