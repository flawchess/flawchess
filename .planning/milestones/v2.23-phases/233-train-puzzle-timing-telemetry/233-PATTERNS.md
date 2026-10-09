# Phase 233: Train Per-Puzzle Timing & Engagement Telemetry - Pattern Map

**Mapped:** 2026-10-05
**Files analyzed:** 20 (new + modified)
**Analogs found:** 18 / 20

All analog paths below are git-tracked source (verified `git ls-files`). Excerpts were read this session.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/2026100X_..._drill_solves_telemetry.py` (new) | migration | schema | `alembic/versions/20260927_120000_d6e4bcc06b45_users_first_touch_attribution.py` | exact |
| `app/models/drill_solve.py` (mod) | model | CRUD | `app/models/user.py:104-112` (`first_touch`) | exact |
| `app/schemas/train.py` (mod: caps, SolveTelemetry, ReviewTelemetry, SolveRequest.telemetry) | schema | validation | `app/schemas/users.py:115-128` (`_clip`), `app/schemas/train.py:136` / `:549` | role-match |
| `app/repositories/train_repository.py` (mod: `record_solve` + new `merge_solve_telemetry`) | repository | CRUD (UPDATE) | `record_solve` claim UPDATE `:2987-3004`; `stamp_session_entered` `:905-927` | exact |
| `app/routers/train.py` (mod: new review route) | router | request-response (204 write) | `mark_session_entered` `app/routers/train.py:186-211` | exact |
| `tests/routers/test_train.py` (mod) | test | request-response | `/enter` tests `tests/routers/test_train.py:3120-3160` | exact |
| `tests/schemas/test_train_telemetry_parity.py` (new) | test | parity | `tests/services/test_train_score_parity.py` | exact |
| `frontend/src/lib/trainTelemetry.ts` (new) | utility | transform | `frontend/src/lib/trainScore.ts` (constants mirrored by parity test) | role-match |
| `frontend/src/lib/visibleStopwatch.ts` (new) | utility | event-driven | `frontend/src/hooks/useBotGameClock.ts:250-336` | role-match |
| `frontend/src/lib/deviceClass.ts` (new) | utility | - | `frontend/src/hooks/useInstallPrompt.ts:190` (extract) | exact |
| `frontend/src/hooks/useInstallPrompt.ts` (mod) | hook | - | itself (call `isMobileUserAgent()`) | exact |
| `frontend/src/hooks/useTrainPuzzleTelemetry.ts` (new) | hook | event-driven | `useBotGameClock.ts` (visibility) + `useBotGame.ts:701` (pagehide) | role-match |
| `frontend/src/api/client.ts` (mod: `trainApi.recordReview`, `postReviewKeepalive`) | api client | request-response | `trainApi.markSessionEntered` `client.ts:291-292`; token read `client.ts:70-73` | exact |
| `frontend/src/hooks/useTrainSession.ts` (mod, optional mutation) | hook | request-response | `markSessionEntered` mutation `useTrainSession.ts:286-290` | exact |
| `frontend/src/types/train.ts` (mod) | types | - | existing `SolveRequest` type | exact |
| `frontend/src/lib/trainRevealCache.ts` (mod: optional review snapshot) | utility | storage | `verdictBotId?` optional field `trainRevealCache.ts:27-38` | exact |
| `frontend/src/components/train/TrainSolveScreen.tsx`, `TrainReveal.tsx`, `TrainLineStepper.tsx`, `hooks/useTrainFreePlay.ts` (mod: optional callback props) | component/hook | event-driven | hook points listed in RESEARCH Pattern 6 table | self |
| `frontend/src/pages/Privacy.tsx` (mod: one `<li>`) | page | - | existing `<li>` list in file | self |
| Frontend tests (`TrainSolveScreen.test.tsx`, `Train.solveLoop.test.tsx`, `TrainSolveScreen.restoredGameArrow.test.tsx`) | test | - | existing explicit `trainApi` mocks | self |
| `frontend/src/hooks/useTrainPuzzleTelemetry.test.ts` / `visibleStopwatch.test.ts` (new) | test | - | none specific; use vitest fake timers | no analog |

## Pattern Assignments

### Alembic migration (copy `d6e4bcc06b45` verbatim shape)
Head is `e3a8c5f17b20` (per RESEARCH). Analog body:
```python
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('first_touch', postgresql.JSONB(none_as_null=True), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'first_touch')
```
Docstring style: rationale paragraph + "No backfill: ... stay NULL, which reads as 'never recorded'." Imports: `from alembic import op`, `import sqlalchemy as sa`, `from sqlalchemy.dialects import postgresql`.

### `app/models/drill_solve.py` (analog `app/models/user.py:104-112`)
```python
    # none_as_null: without it a Python None is written as JSON null, which an
    # `IS NULL` predicate does not match (the first-write-wins guard would break).
    first_touch: Mapped[dict[str, str] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )
```
Use `Mapped[dict[str, Any] | None]` and adapt the comment (JSON null breaks the `coalesce || patch` merge into an array, RESEARCH Pitfall 1).

### `app/repositories/train_repository.py`
**Claim UPDATE to extend** (`:2987-3004`):
```python
    claim_result = await session.execute(
        update(DrillSolve)
        .where(
            DrillSolve.session_id == session_id,
            DrillSolve.position == position,
            DrillSolve.user_id == user_id,
            DrillSolve.solved_at.is_(None),
        )
        .values(
            guess=guess_int, played_move=played_move, correct_move=correct_move,
            move_quality=move_quality_int, correct_guess=correct_guess, solved_at=now_utc,
        )
    )
    claimed = claim_result.rowcount == 1  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
```
Change `.values(...)` to `**values` dict; add `values["telemetry"] = _merged_telemetry(patch)` only when patch is not None (omit column otherwise). Merge expression in RESEARCH Pattern 1 (verified live).

**New `merge_solve_telemetry`** docstring/signature shape from `stamp_session_entered` (`:905-921`): keyword-only `session, *, user_id, session_id, ...) -> bool`, Args block ("Caller commits", "never client-supplied"), "Returns: False when ...". Body: single UPDATE with `DrillSolve.solved_at.is_not(None)` in WHERE (no SELECT, no session-status check), return `rowcount == 1` with same ty-ignore.

### `app/routers/train.py` new review route (analog `:186-211`)
```python
@router.post("/sessions/{session_id}/enter", status_code=204)
async def mark_session_entered(
    session_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
) -> None:
    try:
        found = await train_repository.stamp_session_entered(
            session, user_id=user.id, session_id=session_id, now_utc=now_utc
        )
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("train", {"user_id": str(user.id), "session_id": session_id})
        sentry_sdk.capture_exception()
        raise
    if not found:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Session not found")
    await session.commit()
```
Differences: path `"/sessions/{session_id}/solves/{position}/review"`, `Path(ge=..., le=...)` bounds using existing `_SESSION_ID_MAX` (`train.py:66-68`) + new `DRILL_POSITION_MAX: Final = 2**15 - 1`, add `Path` to the fastapi import (`train.py:28`), body `ReviewTelemetry`, no `now_utc`, detail "Puzzle not found". `solve_puzzle` (~:134) passes `body.telemetry.model_dump(exclude_none=True) if body.telemetry else None` to `record_solve`.

### `app/schemas/train.py`
- Constants: `Final` at module level, like `MEDAL_CLAIM_MAX_ITEMS: Final = 100` (`:549`) with a comment explaining the cap.
- Clamp-not-reject precedent `app/schemas/users.py:119-128`:
```python
def _clip(value: object, max_len: int) -> str | None:
    """...Truncates instead of rejecting: ... a 422 would lose the whole record."""
    if not isinstance(value, str):
        return None
```
- `SolveRequest` is at `:136`; add `telemetry: SolveTelemetry | None = None` + `mode="wrap"` drop-to-None validator. Full model sketch: RESEARCH Pattern 3 (probe-verified). Keys: `think_hidden_ms` (solve) vs `review_hidden_ms` (review) to avoid merge collision.

### `tests/routers/test_train.py` (analog `:3120-3160`)
```python
@pytest.mark.asyncio
async def test_enter_session_stamps_once(test_engine) -> None:
    user_id, token = await _register_and_login(f"train-enter-{uuid.uuid4().hex[:8]}@example.com")
    session_id = await _seed_session(test_engine, user_id, [(None, 0, int(DrillSource.RED_HERRING))])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}
        first = await client.post(f"{ENDPOINT}/{session_id}/enter", headers=headers)
        assert first.status_code == 204
```
Plus a DB read helper like `_entered_at` (select via `async_sessionmaker(test_engine)`) for `telemetry` and `telemetry IS NULL` / `jsonb_typeof <> 'array'`. IDOR test mirrors `test_enter_session_rejects_other_users_session`.

### `tests/schemas/test_train_telemetry_parity.py` (analog `tests/services/test_train_score_parity.py:1-30`)
```python
_TRAIN_SCORE_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/trainScore.ts"

def _extract_int(name: str) -> int:
    m = re.search(rf"export\s+const\s+{name}\s*=\s*(\d+)\s*;", _TRAIN_SCORE_TS.read_text())
    assert m, f"could not find export const {name} in trainScore.ts"
    return int(m.group(1))
```
Point at `frontend/src/lib/trainTelemetry.ts`; TS constants must be plain integer literals (e.g. `1800000`, not `30 * 60 * 1000`) or adjust the regex.

### `frontend/src/lib/visibleStopwatch.ts` (analog `useBotGameClock.ts:250-260`, `:320-336`)
```typescript
    if (document.visibilityState === 'hidden') pausedAtRef.current = now;   // seed initial hidden
...
      if (document.visibilityState === 'hidden') {
        // Idempotent: a duplicate 'hidden' event (Safari fires visibilitychange
        // alongside pagehide, and again on bfcache restore) must not re-baseline
        if (pausedAtRef.current === null) pausedAtRef.current = Date.now();
      } else if (pausedAtRef.current !== null) {
        const pausedForMs = Date.now() - pausedAtRef.current;
        ...
        pausedAtRef.current = null;
      }
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
```
Make it pure (state in, state out, injected `now`), `Date.now()` clock. API sketch in RESEARCH Pattern 5.

### `frontend/src/lib/deviceClass.ts` (extract `useInstallPrompt.ts:190`)
```typescript
  const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
```
Keep the preceding comment (deliberately not viewport-based). `useInstallPrompt` calls the new function; zero behaviour change. Do not confuse with `useIsDesktop` (governs D-11 hover semantics).

### `frontend/src/api/client.ts` (analog `:291-292`, token `:70-73`)
```typescript
  markSessionEntered: (sessionId: number) =>
    apiClient.post<void>(`/train/sessions/${sessionId}/enter`).then(() => undefined),
...
  const token = localStorage.getItem('auth_token');
  if (token) { config.headers.Authorization = `Bearer ${token}`; }
```
`recordReview` copies `markSessionEntered`. `postReviewKeepalive` uses raw `fetch(..., {keepalive: true})` with the same token read (bypasses the 401 redirect interceptor), swallowing errors (sketch: RESEARCH Pattern 7). No sendBeacon (D-06).

### `frontend/src/hooks/useTrainSession.ts` (analog `:286-290`)
```typescript
  const { mutate: mutateEntered } = useMutation({ mutationFn: trainApi.markSessionEntered });
  const sessionId = session?.session_id;
  const markSessionEntered = useCallback(() => {
    if (sessionId != null) mutateEntered(sessionId);
  }, [sessionId, mutateEntered]);
```
Global `MutationCache.onError` captures to Sentry; do not capture again.

### `frontend/src/lib/trainRevealCache.ts` (`:27-38`)
Add an optional field like the existing `verdictBotId?: PersonaId;` (comment: "Optional: an entry written before this field existed simply recasts"). Keep it out of `isCachedTrainReveal` required checks. Persist folded numbers only, never a running timestamp.

### `useTrainPuzzleTelemetry.ts` + reveal callback props
Hook-point table (file:line) is in RESEARCH Pattern 6; pagehide precedent `frontend/src/hooks/useBotGame.ts:701` ("Snapshot write on tab-hide/pagehide"). Mutable state in refs; returned callbacks `useCallback`-stable. New optional props: `TrainLineStepper.onUserStep`, `TrainReveal.onCardEngage / onCardsTotalChange`, `useTrainFreePlay` option `onUserMove`.

## Shared Patterns

- **Ownership:** user id only from `current_active_user`; `DrillSolve.user_id == user_id` in the UPDATE WHERE (apply to both repo writes).
- **Sentry in routers:** `set_context("train", {...})` + `capture_exception()` + rollback + re-raise; no variables in messages.
- **JSONB NULL discipline:** `none_as_null=True`, omit column when no patch, `model_dump(exclude_none=True)`.
- **Named constants** shared Python/TS, guarded by regex parity test.
- **Frontend test mocks:** add `recordReview` to explicit `trainApi` mocks; stub `globalThis.fetch` for pagehide tests.

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `useTrainPuzzleTelemetry.test.ts` | test | no existing engagement-counter hook test; use vitest fake timers + `document.visibilityState` stubs |
| D-11 800 ms hover-hold timer | logic | no hover-dwell counter exists; follow RESEARCH Pattern 6 |

## Metadata
**Analog search scope:** app/routers, app/repositories, app/models, app/schemas, alembic/versions, tests/routers, tests/services, frontend/src/{api,hooks,lib}
**Files scanned:** ~14
**Pattern extraction date:** 2026-10-05
