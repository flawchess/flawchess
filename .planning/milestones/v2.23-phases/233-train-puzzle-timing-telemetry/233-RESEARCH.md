# Phase 233: Train Per-Puzzle Timing & Engagement Telemetry - Research

**Researched:** 2026-10-05
**Domain:** FastAPI + SQLAlchemy 2.x async JSONB merge write, Pydantic v2 boundary models, React 19 client-side timing/engagement instrumentation, unload-safe fetch
**Confidence:** HIGH (every file:line below was opened with Read/Grep/sed in this session; DB behaviour was probed live against the dev Postgres)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked upstream (SEED-190 + ROADMAP Phase 233, owner 2026-10-05; do not re-open)
- **D-01 Storage:** one nullable `drill_solves.telemetry` JSONB, not individual columns. Validated
  at the API boundary by Pydantic models (`extra="forbid"`, typed and capped int/bool/Literal
  fields, a `v` schema-version key); nothing unvalidated reaches the column. Writes MERGE:
  `telemetry = coalesce(telemetry, '{}'::jsonb) || :patch`, never overwrite. When a request carries
  no telemetry, OMIT the column from the write so "no telemetry" stays SQL `IS NULL` (asyncpg writes
  Python `None` as JSON `null`, see memory `project_asyncpg_jsonb_null_vs_sql_null`). Promote a key
  to a real column only if it becomes product-facing.
  — **Reversibility:** costly — adds a column via Alembic migration; dropping it later loses the
  collected data, which cannot be regenerated.
- **D-02 Think time:** `guess_ms` (board shown -> guess pressed) and `move_ms` (guess pressed ->
  move played), measured client-side, sent as optional telemetry on `POST
  /train/sessions/{id}/solve` (`SolveRequest`). The server cannot measure this (puzzles are
  pre-materialized at composition, P-07). The telemetry part is optional so an old client (stale
  bundle) still solves.
- **D-03 Review time + engagement:** `review_ms` plus engagement counters accumulated in the reveal
  and flushed ONCE per puzzle via a new `POST /train/sessions/{id}/solves/{position}/review`, on
  Next and on `pagehide` (so the last puzzle of a session and abandons are not lost). No per-click
  events.
- **D-04 Data quality:** count only visible time (pause while `document.visibilityState` is
  `hidden`); store `hidden_ms` alongside; cap every stored duration at a named constant (~30 min).
- **D-05 Grading untouched:** telemetry is never an input to `move_quality`, `correct_guess`,
  scoring, SR ladder, or the leaderboard.

#### Correction to the roadmap wording (transport)
- **D-06:** Do NOT use `navigator.sendBeacon` for the unload flush. Auth is FastAPI-Users
  `BearerTransport` (`app/users.py:198`) and sendBeacon cannot set an `Authorization` header, so a
  beacon would 401. Use `fetch(url, { keepalive: true, headers: { Authorization } })` (or axios with
  the fetch adapter + `fetchOptions: { keepalive: true }`) for the `pagehide` flush. Next can use the
  normal `apiClient` call. The roadmap's "sendBeacon" means "a write that survives unload".

#### Owner picks from SEED-190 §4
- **D-07 shown / abandon signal: derive, no extra ping.** The review flush carries
  `exit: "next" | "pagehide"`. "Puzzle N was shown" is derived from puzzle N-1 having `exit = next`
  (position 0: `drill_sessions.entered_at`). No third write per puzzle. Accepted blind spot: a reload
  that resumes mid-session.
- **D-08 Leaderboard exposure: no impression event.** Owner only wants the Points/Accuracy toggle
  tracked, and it already is (`TrainLeaderboardCard.tsx:392`, Umami `tab-switch` with
  `LEADERBOARD_TAB_TARGET`). The plan verifies this (an existing or added test asserting the event
  fires on toggle) and adds nothing else. No IntersectionObserver impression.
- **D-09 Device class: telemetry key per solve.** `client: "mobile" | "desktop"` inside
  `telemetry`, a Pydantic `Literal`. No migration, no `drill_sessions` column, correct when a session
  is resumed on another device. Add one line to `frontend/src/pages/Privacy.tsx`.
- **D-10 No `train-review` Umami mirror.** The DB row is the single source; Umami stays funnels-only.

#### Engagement counter rules
- **D-11 Card "opened":** mobile = a tap that spotlights a card. Desktop = a hover held for at least
  a named constant of 800 ms (drops pointer fly-overs on the way to Next); a desktop card CLICK
  (the board-departed branch that restores the solution and spotlights) counts immediately. Applies
  to line cards and the Also-fine card.
- **D-12 Distinct count:** `review_cards_opened` = distinct cards inspected at least once. Also
  store `review_cards_total` = number of cards shown on that reveal, so coverage is computable.
- **D-13 Walkthrough flag:** store `review_walkthrough: true` when the Phase 222 first-reveal
  walkthrough (`useTrainWalkthrough`) was active on that reveal. Counters are still recorded
  normally; analysis filters on the flag.
- **D-14 Counter set (closed):** `review_cards_opened`, `review_cards_total`, `review_line_steps`
  (prev/next/token, capped), `review_explored` (bool), `review_explore_moves` (capped),
  `review_analyze_opened` (bool), `review_walkthrough` (bool). NO flip counter, NO Solution-return
  counter (the return is already in Umami `train-solution`).

### Claude's Discretion (owner accepted these defaults)
- **Timer interruptions:** a reload/remount mid-puzzle that loses the in-memory timer stores what
  was measured from the restart plus `resumed: true`. The Analyze round-trip (reveal remount via the
  `restoredSolve` cache) keeps ONE review timer across the remount (persist the start/accumulated
  values in the same cache), so `review_ms` covers the whole reveal.
- **Flush semantics:** per-key last write wins via the jsonb `||` merge. Once Next has flushed a
  puzzle, a later `pagehide` for that puzzle is a no-op (client-side "flushed" guard). The review
  endpoint accepts a flush only for a SOLVED row (`solved_at IS NOT NULL`) owned by the caller (user
  id from `current_active_user`, never the body), and DOES accept it after the session is
  completed or expired: it is the user's own row and the last puzzle's flush always lands after
  completion.
- **`review_explored` definition:** true once the user plays at least one free-play move on the
  reveal board (entering exploration happens by moving a piece).
- **Caps / constants:** exact cap values for durations (~30 min) and counters (line steps ~50,
  explore moves similar), each a named constant shared by the Pydantic model and the client.
- **`client` detection:** reuse an existing signal (e.g. the UA check in `useInstallPrompt`) rather
  than inventing a new one; pick whatever is already the project's mobile definition.
- **Schema version:** `v: 1` on both patches.

### Deferred Ideas (OUT OF SCOPE)
- Leaderboard exposure impression (IntersectionObserver, one per visit): declined by owner for now;
  revisit only if the ~2026-10-25 analysis cannot separate exposure from visiting /train.
- Bucketed `train-review` Umami event: declined (D-10).
- Explicit per-puzzle shown ping: declined in favour of deriving from `exit` (D-07).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped to this phase (ROADMAP Phase 233 says `Requirements: TBD`). CONTEXT.md
decisions D-01..D-14 are the contract; the Validation Architecture section maps each one to a test.
</phase_requirements>

## Summary

The backend half is small and fully de-risked. `record_solve` already claims the row with a single
core `update(DrillSolve)` statement (`app/repositories/train_repository.py:2987-3003`) whose WHERE
clause carries `session_id`, `position`, `user_id` and `solved_at IS NULL`. The telemetry merge
belongs in that SAME `.values(...)` call, added only when the request carries telemetry. I compiled
and then executed the merge expression against the live dev Postgres (temp table, rolled back): the
first merge into a SQL-NULL column yields the patch object, a second merge adds keys, an UPDATE that
omits the column leaves it SQL NULL, and `solved_at IS NOT NULL` gates the review flush with
`rowcount` 0/1. The new review route is a copy of `mark_session_entered`
(`app/routers/train.py:186-211`) backed by one UPDATE (no SELECT). The Alembic migration is a
one-liner modelled on the `users.first_touch` migration, which uses `JSONB(none_as_null=True)`.

One live-probe finding matters for the model: if a JSON `null` (not SQL NULL) ever lands in the
column, `coalesce(telemetry, '{}') || patch` does NOT repair it. Postgres returns an ARRAY
(`[None, {'a': 1}]` in the probe), which silently corrupts the row's shape. Declaring the column
`JSONB(none_as_null=True)` (the `users.first_touch` precedent, `app/models/user.py:108-112`) closes
that hole at the type level, in addition to omitting the column when there is no patch.

The frontend half is where the planning effort goes. `TrainSolveScreen.tsx` is 1882 lines and its
component body is already large, so all timing and counter state belongs in one new hook
(`useTrainPuzzleTelemetry`) built on a small pure visible-time stopwatch. The screen itself gets
roughly 6-8 wiring lines. The reveal needs two new optional callback props so the hook can tell a
user action apart from the effects that fire on mount and reset: `onUserStep` on
`TrainLineStepper`, and `onCardEngage` on `TrainReveal`. Without them, `TrainLineStepper`'s
`onStepChange` fires from a mount/reset effect (`TrainLineStepper.tsx:178-197`) and
`onSpotlightChange` cannot distinguish a desktop hover from a desktop click.

**Primary recommendation:** Tracer-first slice: migration + model column + `SolveTelemetry` on
`SolveRequest` merged inside `record_solve`'s claim UPDATE (backend green), then the review route,
then the frontend hook (think timer → review timer + Next flush → pagehide keepalive → counters).
Telemetry must never cost a solve. Wrap `SolveRequest.telemetry` in a Pydantic `mode="wrap"`
validator that drops invalid telemetry to `None` instead of 422-ing the whole solve, and clamp
numeric overflows instead of rejecting them.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Think/review time measurement (visible-only) | Browser / Client | — | Server never knows when a pre-materialized puzzle is shown (P-07); visibility is a browser API |
| Engagement counters (cards, steps, explore, analyze, walkthrough) | Browser / Client | — | Pure UI interactions; accumulated in a hook, flushed once |
| Device class (`client`) | Browser / Client | — | UA check, already the project's mobile definition |
| Unload-safe flush | Browser / Client | API | `pagehide` + `fetch(keepalive)` with Bearer header (D-06) |
| Validation, clamping, schema version | API / Backend | — | Pydantic boundary models (`extra="forbid"`, caps) |
| Ownership + solved gate | API / Backend | Database | `user_id` from `current_active_user` in the UPDATE's WHERE |
| Merge write (`coalesce(...) || patch`) | Database / Storage | API | Atomic in one UPDATE; no read-modify-write race |

## Standard Stack

No new packages. Everything below is already installed.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.52 [VERIFIED: `uv run python` printed `sa.__version__`] | core `update()` with JSONB `||` merge | Already the project ORM; `record_solve` uses core `update()` |
| Pydantic | 2.13.5 [VERIFIED: probe printed `pydantic.VERSION`] | boundary models, clamp/forbid/wrap validators | Project-wide boundary validation |
| asyncpg JSONB codec | (bundled) | dict <-> jsonb | `app/models/game_flaw.py:119` comment: "asyncpg auto-registers the JSONB codec" |
| axios | ^1.16.1 [VERIFIED: frontend/package.json:28] | Next-path flush via `apiClient` | Existing `trainApi` pattern |
| Browser `fetch` keepalive | platform | pagehide flush | sendBeacon cannot send `Authorization` (D-06) |
| vitest | ^5.0.0 [VERIFIED: frontend/package.json:80] | fake timers + visibility tests | Existing test runner |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase. `package-legitimacy check` not applicable.
**Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
 puzzle on screen ──(engine isReady)──► THINK stopwatch starts (visible-only, hidden_ms tracked)
        │                                          │
  guess button (onGuess / onIntroGuess) ──► mark guess_ms
        │                                          │
  graded piece drop (handlePieceDrop) ────► mark move_ms ─► freeze SolveTelemetry snapshot
        │                                                          │
        ▼                                                          ▼
  gradeAndSolve ──► POST /api/train/sessions/{sid}/solve  {..., telemetry?: SolveTelemetry}
                          │  Pydantic: wrap-validator drops invalid telemetry → None (solve never 422s on it)
                          ▼
                    record_solve: ONE claim UPDATE
                      WHERE session_id,position,user_id, solved_at IS NULL
                      SET ..., solved_at=now [, telemetry = coalesce(telemetry,'{}') || :patch]   (only if patch)
                          │
        ◄── SolveResponse (verdict) ──┘
        │
  verdict !== null ──► REVIEW stopwatch starts; counters accumulate:
        │   TrainReveal.onCardEngage (tap/click = open; hover-start/end → 800 ms hold timer)
        │   TrainLineStepper.onUserStep (prev/next/token only, NOT mount/reset effects)
        │   useTrainFreePlay.onUserMove (start / playMove ok / playLine)
        │   handleAnalyzeClick → analyze_opened (+ persist review state in trainRevealCache)
        │   walkthrough.activeStep !== null at any time → walkthrough = true (sticky)
        │   TrainReveal.onCardsTotalChange → cards_total = max seen
        │
        ├── Next (handleNextFromReveal) ──► apiClient POST .../solves/{pos}/review {exit:"next",...}
        │                                     then flushed-guard = true, then handleNext()
        └── window 'pagehide' (not flushed) ─► fetch(/api/.../review, {keepalive, Authorization}) {exit:"pagehide",...}
                          │
                          ▼
              merge_solve_telemetry: ONE UPDATE
                WHERE session_id,position,user_id, solved_at IS NOT NULL   (session status NOT checked)
                SET telemetry = coalesce(telemetry,'{}'::jsonb) || :patch
                rowcount 0 → 404, 1 → 204
```

### Recommended Project Structure (new/changed files)

```
app/
├── models/drill_solve.py            # + telemetry: Mapped[dict[str, Any] | None] JSONB(none_as_null=True)
├── schemas/train.py                 # + caps constants, SolveTelemetry, ReviewTelemetry, SolveRequest.telemetry
├── repositories/train_repository.py # record_solve(+telemetry), merge_solve_telemetry(), _merged_telemetry()
└── routers/train.py                 # + POST /sessions/{session_id}/solves/{position}/review (204)
alembic/versions/2026100X_HHMMSS_<rev>_drill_solves_telemetry.py
tests/
├── routers/test_train.py            # + solve-with-telemetry, review flush, ownership, unsolved, completed-session
└── schemas/test_train_telemetry_parity.py   # caps parity vs frontend/src/lib/trainTelemetry.ts
frontend/src/
├── lib/trainTelemetry.ts            # caps constants (mirrored), payload types, buildSolve/ReviewPatch (pure)
├── lib/visibleStopwatch.ts          # pure visible-time accumulator (injectable clock)
├── lib/deviceClass.ts               # isMobileUserAgent() extracted from useInstallPrompt.ts:190
├── hooks/useTrainPuzzleTelemetry.ts # the one hook TrainSolveScreen calls
├── api/client.ts                    # trainApi.recordReview (axios) + postReviewKeepalive (raw fetch)
├── types/train.ts                   # SolveRequest.telemetry?, SolveTelemetry, ReviewTelemetry
├── lib/trainRevealCache.ts          # + optional review-timer snapshot field
├── components/train/TrainLineStepper.tsx  # + onUserStep?
├── components/train/TrainReveal.tsx       # + onCardEngage?, onLineUserStep?, onCardsTotalChange?
├── hooks/useTrainFreePlay.ts        # + onUserMove? option
└── pages/Privacy.tsx                # + one <li>
```

### Pattern 1: Merge telemetry inside the existing claim UPDATE (single statement)

**What:** `record_solve`'s claim is a core UPDATE, not ORM attribute assignment. Verified at
`app/repositories/train_repository.py:2987-3003`:

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
            guess=guess_int,
            played_move=played_move,
            correct_move=correct_move,
            move_quality=move_quality_int,
            correct_guess=correct_guess,
            solved_at=now_utc,
        )
    )
    claimed = claim_result.rowcount == 1  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
```

Ownership is `DrillSolve.user_id == user_id` directly on the row (the model has its own `user_id`
column, `app/models/drill_solve.py:148`). There is NO subquery on the session's owner. That
discards the "ownership subquery" hypothesis from the earlier run.

**How:** build the values dict, add `telemetry` only when a patch exists:

```python
# Source: verified live against dev Postgres 2026-10-05 (temp table, rolled back)
from sqlalchemy import cast, func, literal
from sqlalchemy.dialects.postgresql import JSONB

def _merged_telemetry(patch: dict[str, object]) -> ColumnElement[Any]:
    """`coalesce(telemetry, '{}'::jsonb) || :patch` — D-01 merge, never overwrite."""
    return func.coalesce(DrillSolve.telemetry, cast(literal("{}"), JSONB)).op(
        "||", return_type=JSONB
    )(literal(patch, JSONB))

values: dict[str, object] = {"guess": guess_int, ..., "solved_at": now_utc}
if telemetry_patch is not None:          # omit the column entirely otherwise (D-01)
    values["telemetry"] = _merged_telemetry(telemetry_patch)
claim_result = await session.execute(update(DrillSolve).where(...).values(**values))
```

Probe output (real, this session):
```
claim rowcount: 1
claim w/o telemetry rowcount: 1
review rowcount: 1
review miss rowcount: 0
[(1, {'v': 1, 'exit': 'next', 'client': 'desktop', 'guess_ms': 1200, 'review_ms': 9000}, False), (2, None, True)]
```
Row 2 (claimed without telemetry) stayed SQL NULL (`IS NULL` = True).

**Merge only on the claimed path.** The lost-claim / re-submit branch (`train_repository.py:3040-3066`)
does not write. That is correct: the first recorded outcome wins (T-189-19) and the first request
already carried the telemetry. `retrySolve` re-sends the identical payload
(`frontend/src/hooks/useTrainSession.ts:325-330`), so the telemetry snapshot must be frozen at
move time and never recomputed.

**`record_solve` signature:** add `telemetry: dict[str, object] | None = None` as a keyword arg.
The router passes `body.telemetry.model_dump(exclude_none=True) if body.telemetry else None`.
`exclude_none=True` is load-bearing: it keeps unmeasured keys out of the patch, so a merge never
writes a JSON null *value* (probe: `{'v': 1, 'guess_ms': 10}`).

### Pattern 2: Review-flush route (mirror `mark_session_entered`)

Template verified at `app/routers/train.py:186-211`: try → repo call → except: rollback +
`sentry_sdk.set_context("train", {"user_id": str(user.id), "session_id": session_id})` +
`capture_exception()` + re-raise; `if not found: rollback; raise HTTPException(404)`; commit.

```python
@router.post("/sessions/{session_id}/solves/{position}/review", status_code=204)
async def record_puzzle_review(
    session_id: Annotated[int, Path(ge=1, le=_SESSION_ID_MAX)],
    position: Annotated[int, Path(ge=0, le=DRILL_POSITION_MAX)],
    body: ReviewTelemetry,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    try:
        found = await train_repository.merge_solve_telemetry(
            session, user_id=user.id, session_id=session_id, position=position,
            patch=body.model_dump(exclude_none=True),
        )
    except Exception:
        await session.rollback()
        sentry_sdk.set_context("train", {"user_id": str(user.id), "session_id": session_id})
        sentry_sdk.capture_exception()
        raise
    if not found:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Puzzle not found")
    await session.commit()
```

- **No `now_utc` dependency**: the route stores client durations only, and the keepalive fetch
  then needs no dev-clock header.
- **Path bounds:** `drill_sessions.id` is int4. `_SESSION_ID_MAX: Final = 2**31 - 1` already exists
  (`app/routers/train.py:66-68`, with the comment "a larger session_id would raise in asyncpg and
  reach Sentry as a 500"). `drill_solves.position` is `SmallInteger` (`drill_solve.py:146`), so
  add `DRILL_POSITION_MAX: Final = 2**15 - 1`. `Path` is not imported yet. The import line is
  currently `from fastapi import APIRouter, Depends, HTTPException, Query` (`train.py:28`).
- **Single UPDATE, single 404:** do not SELECT first to tell "not owned" from "not solved". The
  client never acts on the status, and one statement keeps it atomic. Optional extra: 409 for
  unsolved, mirroring `reveal_puzzle`. Not recommended because it costs a second query for no
  consumer.
- **Session status is not checked.** `reveal_for_puzzle` (`train_repository.py:3183-3194`) also
  filters only by `session_id`/`position`/`user_id`. The new UPDATE never joins `drill_sessions`,
  so completed/expired sessions are accepted, as the discretion section requires.

### Pattern 3: Pydantic boundary models — clamp, never cost a solve

Conventions verified in `app/schemas/train.py`: `Final` constants live in the schema module
(`MEDAL_CLAIM_MAX_ITEMS: Final = 100`, line 549); `Field(ge=, le=)` bounds
(`TrainSettingsUpdate`, lines 355-358). `extra="forbid"` precedent: `app/schemas/opening_insights.py:27`.
The "clip instead of 422 so the record is not lost" precedent: `app/schemas/users.py:119-127`
(`_clip`: "Truncates instead of rejecting ... a 422 would lose the whole record").

**Recommendation (justified):**
1. **Durations/counters CLAMP** to `[0, CAP]` in a `BeforeValidator`, and round floats. The client
   computes ms from clock deltas, and a fractional float like `1234.6` would fail lax `int`
   validation. A 30-min cap is a data-quality cap, not a security bound.
2. **Types and unknown keys still fail validation** (`extra="forbid"`, `strict=True`, D-01).
3. **On `SolveRequest`, a failed telemetry object is DROPPED to `None`** by a `mode="wrap"`
   field validator, so the solve still records (D-02: "optional so an old client still solves").
   On the review route the body IS the telemetry, so it 422s normally.

Probe (real output, Pydantic 2.13.5):
```
{"guess_ms": 1234.6}      -> guess_ms=1235
{"guess_ms": 99_999_999}  -> guess_ms=1800000
{"guess_ms": -5}          -> guess_ms=0
{"bogus": 1}              -> telemetry=None   (solve still valid)
{"guess_ms": True}        -> telemetry=None   (bool is not a duration)
{"guess_ms": "12"}        -> telemetry=None   (strict)
{"resumed": 1}            -> telemetry=None   (strict bool)
standalone ReviewTelemetry {"bogus": 1} -> 422 extra_forbidden
```

```python
# Source: shape verified by local probe (scratchpad), names are proposals [ASSUMED]
TELEMETRY_SCHEMA_VERSION: Final = 1
TELEMETRY_DURATION_CAP_MS: Final = 30 * 60 * 1000       # D-04 "~30 min"
TELEMETRY_LINE_STEPS_CAP: Final = 50                     # discretion "~50"
TELEMETRY_EXPLORE_MOVES_CAP: Final = 50                  # "similar"
TELEMETRY_CARDS_CAP: Final = 10                          # reveal shows <= 4 today

def _clamp(cap: int) -> Callable[[object], object]:
    def _inner(value: object) -> object:
        if isinstance(value, bool):          # bool is an int subclass: let strict int reject it
            return value
        if isinstance(value, (int, float)):
            return max(0, min(cap, round(value)))
        return value
    return _inner

DurationMs = Annotated[int, BeforeValidator(_clamp(TELEMETRY_DURATION_CAP_MS)), Field(ge=0, le=TELEMETRY_DURATION_CAP_MS, strict=True)]

class SolveTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: Literal[1]
    client: Literal["mobile", "desktop"] | None = None
    guess_ms: DurationMs | None = None
    move_ms: DurationMs | None = None
    think_hidden_ms: DurationMs | None = None
    resumed: StrictBool | None = None

class ReviewTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: Literal[1]
    exit: Literal["next", "pagehide"]                     # required: D-07 abandon analysis
    review_ms: DurationMs | None = None
    review_hidden_ms: DurationMs | None = None
    review_cards_opened: CardCount | None = None
    review_cards_total: CardCount | None = None
    review_line_steps: LineSteps | None = None
    review_explored: StrictBool | None = None
    review_explore_moves: ExploreMoves | None = None
    review_analyze_opened: StrictBool | None = None
    review_walkthrough: StrictBool | None = None

class SolveRequest(BaseModel):
    ...existing fields...
    telemetry: SolveTelemetry | None = None

    @field_validator("telemetry", mode="wrap")
    @classmethod
    def _drop_invalid_telemetry(cls, value: object, handler: ValidatorFunctionWrapHandler) -> SolveTelemetry | None:
        """Telemetry is a recorded outcome, never worth losing the solve over (D-02/D-05)."""
        try:
            return handler(value)
        except ValidationError:
            return None
```

**Key-collision decision (planner must adopt):** both patches merge with per-key last-write-wins.
D-04's single `hidden_ms` key would be overwritten by the review patch and the think-phase value
lost. Use `think_hidden_ms` (solve patch) and `review_hidden_ms` (review patch). For the same
reason, `client` and `resumed` go only in the solve patch, and every counter in the review patch
must be a cumulative TOTAL, never a delta, because a pagehide flush followed by a later Next flush
(bfcache return, or Analyze round trip) overwrites per key.

### Pattern 4: Alembic migration (`users.first_touch` precedent)

Head is `e3a8c5f17b20` [VERIFIED: `uv run alembic heads` → `e3a8c5f17b20 (head)`], file
`alembic/versions/20261004_120000_e3a8c5f17b20_train_weekly_standings.py`. Filename template
[VERIFIED: alembic.ini:17] `%%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s`.
Precedent body [VERIFIED: alembic/versions/20260927_120000_d6e4bcc06b45_users_first_touch_attribution.py]:

```python
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('first_touch', postgresql.JSONB(none_as_null=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'first_touch')
```

New migration: `op.add_column('drill_solves', sa.Column('telemetry', postgresql.JSONB(none_as_null=True), nullable=True))`,
`down_revision = 'e3a8c5f17b20'`, no index, no backfill (go-forward only). Docstring: why JSONB
instead of columns, and that NULL means "pre-feature or client sent none". Adding a nullable
column without a default is metadata-only in Postgres, so there is no table rewrite. The table is
~8k rows anyway.

Model line (precedent `app/models/user.py:108-112`, whose comment reads "none_as_null: without it a
Python None is written as JSON null, which an `IS NULL` predicate does not match"):
```python
    telemetry: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )
```
The composition insert (`train_repository.py:2171`, `DrillSolve(...)` constructor) never sets the
attribute, and `none_as_null` makes an accidental `None` safe as well.

### Pattern 5: Visible-time stopwatch (copy of `useBotGameClock` semantics)

Verified pattern in `frontend/src/hooks/useBotGameClock.ts:320-336`: a single `visibilitychange`
listener; on `hidden`, record `pausedAt` idempotently ("a duplicate 'hidden' event (Safari fires
visibilitychange alongside pagehide ...) must not re-baseline"); on visible, shift the anchor by
the paused span. Lines 252-260 add the mount-into-hidden-tab fix: "Seed the pause from the INITIAL
visibility state" (`if (document.visibilityState === 'hidden') pausedAtRef.current = now;`).
It uses `Date.now()`.

Recommend a **pure** accumulator so it is unit-testable without React, plus a thin listener:

```typescript
// frontend/src/lib/visibleStopwatch.ts  [proposal]
export interface VisibleStopwatch {
  visibleMs: number;           // folded visible time
  hiddenMs: number;            // folded hidden time
  segmentStart: number | null; // start of current visible segment (null = paused/hidden/stopped)
  hiddenSince: number | null;  // start of current hidden span
}
export function startStopwatch(now: number, hidden: boolean, seed?: { visibleMs: number; hiddenMs: number }): VisibleStopwatch
export function onVisibility(sw: VisibleStopwatch, hidden: boolean, now: number): VisibleStopwatch  // idempotent per state
export function readStopwatch(sw: VisibleStopwatch, now: number): { visibleMs: number; hiddenMs: number }
export function pauseStopwatch(sw: VisibleStopwatch, now: number): VisibleStopwatch  // fold running segment (unmount/Analyze)
```

Use `Date.now()` (fake-timer friendly, the same clock `useBotGameClock` uses). Persist only the
folded `visibleMs`/`hiddenMs` numbers into `trainRevealCache`. Never persist a running timestamp:
a `performance.now()` origin resets on reload and would turn a persisted value into garbage.

### Pattern 6: `useTrainPuzzleTelemetry` hook (keeps TrainSolveScreen from growing)

One hook, called once in `TrainSolveScreen`, owning all refs/timers. Returned callbacks must be
**referentially stable** (useCallback over refs). Several are fed to effect dependency arrays:
`TrainReveal`'s tap-away effect lists `onSpotlightChange` (`TrainReveal.tsx:884-894`), and the
puzzle-reset effect lists `freePlay.reset`/`walkthrough.reset` (`TrainSolveScreen.tsx:1040`).

Inputs: `{ puzzle, sessionId, isReady, verdict, isRestored, restoredReview, walkthroughActive, isDesktop }`.
Outputs: `markGuess()`, `markMove() → SolveTelemetry` (frozen snapshot), `onCardEngage(key, kind)`,
`onLineUserStep()`, `onExploreMove()`, `onCardsTotal(n)`, `markAnalyze() → reviewSnapshot`,
`flushOnNext()`.

Exact hook points (all verified by Read this session):

| Event | Where | File:line |
|-------|-------|-----------|
| Puzzle transition / reset | the puzzle-keyed reset effect (deps `[puzzle.fen, ...]`) | TrainSolveScreen.tsx:995-1040 |
| Think start ("board shown") | first render where `isReady` is true for this puzzle and `restoredSolve === null` | `isReady` destructured at :960; engine gate at :1794 |
| Guess pressed | `onGuess: setGuess` (prompt and drop-nudge buttons) and `handleIntroGuess` | :1628, :1565-1570, buttons :294-318 |
| Move played (graded) | `handlePieceDrop` graded branch, right before `void gradeAndSolve(guess, playedUci)` | :1165-1169 |
| Telemetry on solve POST | `trainSession.solvePuzzle({...})` body | :1060-1065 |
| Review start | `verdict !== null` (live: `liveVerdict`; restored: `restoredSolve.verdict`) | :818-820 |
| Next | `handleNextFromReveal` (walkthrough.leave(); handleNext()) | :1596-1599 |
| Analyze (both buttons) | `handleAnalyzeClick` (already the single funnel, tracks Umami `analyze`) | :1506-1529 |
| Walkthrough active | `walkthrough.activeStep` | :931-942 |
| Free-play moves | `freePlay.start` / `freePlay.playMove` in handlePieceDrop; `freePlay.playLine` from exploration PV click | :1136-1153; TrainReveal.tsx:476 |
| Line steps | `TrainLineStepper.goTo` (prev :259, token :293, next :307) | TrainLineStepper.tsx:237-242 |
| Card spotlight | `makeCardClickHandler` + per-card pointer/focus handlers | TrainReveal.tsx:142-176, :1000-1018, :1041-1059 |
| Cards total | `lineBoxes` (:949) + `showAlsoFine` (:971) | TrainReveal.tsx |

**Why new callback props instead of reusing existing channels:**
- `TrainLineStepper`'s `onStepChange` fires from an effect keyed on `[index, line]`
  (`TrainLineStepper.tsx:182-197`), and index resets on `[movesKey, startFen, resetNonce]`
  (:178-180). It therefore fires on mount and on every Solution reset, so counting it overcounts.
  Add `onUserStep?: () => void`, called inside `goTo` after the `if (nextIndex === index) return;`
  guard (:238).
- `onSpotlightChange(entry)` receives the same call from a desktop `onPointerEnter` (:1042) and from
  the desktop departed-board click (:166-167), so hover cannot be told apart from click. Add
  `onCardEngage?: (key: string, kind: 'open' | 'hover-start' | 'hover-end') => void`:
  - mobile: `'open'` wherever the spotlight turns ON. That is the toggle-on in
    `makeCardClickHandler` (:174 when `!isSpotlit`), the in-card button branch (:159), and the
    departed branch (:166-167).
  - desktop: `onPointerEnter`/`onFocus` → `'hover-start'`, `onPointerLeave`/`onBlur` →
    `'hover-end'`, departed click branch → `'open'`.
  - Card keys: `box.testid` for line cards, `ALSO_FINE_KEY = 'train-reveal-also-fine'` (:109).
  - The hook holds ONE hover timer (`REVIEW_CARD_HOVER_MIN_MS = 800`, D-11). `hover-start`
    (re)arms it for that key, `hover-end` clears it, and when it fires the key joins a `Set`.
    `review_cards_opened = set.size` (D-12).
- `review_cards_total`: add `onCardsTotalChange?: (n: number) => void`, reported from an effect in
  `TrainReveal` with `n = lineBoxes.length + (showAlsoFine ? 1 : 0)`. The hook keeps the MAX seen,
  because the game box appears late (after the reveal query) and cards are hidden while exploring.
- `useTrainFreePlay` option `onUserMove?: () => void`, fired in `start` (:396-410), in a wrapped
  `playMove` when `makeMove` returns true (currently `playMove: makeMove`, :436), and in `playLine`
  (:438, used by the PV click at TrainReveal.tsx:476). `review_explored = moves > 0`.

**Walkthrough flag (D-13):** set a sticky ref `true` whenever `walkthrough.activeStep !== null`
while the reveal is open. Not "at flush time": `leave()` stamps the watermark and the settings
cache then flips `activeStep` to null (`useTrainWalkthrough.ts:182-186`).

### Pattern 7: Flush transport

- **Next (normal):** `trainApi.recordReview(sessionId, position, body)` via `apiClient.post<void>`,
  driven by a `useMutation` like `markSessionEntered` (`useTrainSession.ts:286-290`). A failure is
  then reported once by the global `MutationCache.onError` Sentry capture (`lib/queryClient.ts:57-59`)
  and must not be captured again (frontend/CLAUDE.md). Fire it synchronously in
  `handleNextFromReveal` BEFORE `handleNext()`: the next puzzle's reset effect then wipes state,
  and on a restored reveal `handleRestoredNext` unmounts the screen (`Train.tsx:142-148`). A
  mutation already started keeps running after its observer unmounts.
- **pagehide:** raw `fetch` with `keepalive: true`. Token source verified at `api/client.ts:71`:
  `const token = localStorage.getItem('auth_token');` with base URL `'/api'` (`client.ts:55`).
  Do not route this through `apiClient`: its 401 interceptor (`client.ts:89-115`) assigns
  `window.location.href = '/login'`, which is wrong during unload. Put a small
  `postReviewKeepalive(sessionId, position, body)` next to `trainApi` in `client.ts` so the
  token-reading convention stays in one file. Sketch:

```typescript
// [proposal] frontend/src/api/client.ts
export function postReviewKeepalive(sessionId: number, position: number, body: ReviewTelemetry): void {
  const token = localStorage.getItem('auth_token');
  if (token === null) return;
  void fetch(`${apiClient.defaults.baseURL}/train/sessions/${sessionId}/solves/${position}/review`, {
    method: 'POST',
    keepalive: true,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  }).catch(() => {
    // Expected during unload/offline; never captured (frontend/CLAUDE.md "skip expected failures").
  });
}
```

- **Listener scope:** register `window.addEventListener('pagehide', ...)` in the hook while the
  reveal is open and unflushed. Read the latest state through refs, since the handler must not
  close over stale React state. `pagehide` already has precedent in `useBotGame.ts:734-743` and
  `instrument.ts:36`. A reload also fires `pagehide`, which covers the "reload during reveal"
  abandon.
- **Flushed guard:** after a Next flush, a later pagehide for that `(sessionId, position)` is a
  no-op. A pagehide flush does NOT set the guard: a bfcache restore or an Analyze return may still
  end in Next, whose cumulative totals then overwrite per key (allowed by "per-key last write wins").
- **Analyze round trip:** both Analyze controls are react-router `<Link>`s
  (`TrainSolveScreen.tsx:535-543`, `TrainReveal.tsx:1382-1394`), so the screen UNMOUNTS. In
  `handleAnalyzeClick`, pause the stopwatch and save `{ visibleMs, hiddenMs, counters, cardKeys }`
  into a new optional field of `CachedTrainReveal` (`lib/trainRevealCache.ts:27-38`, sessionStorage
  `'train_reveal_cache'`). On restored mount, seed from it. Keep the field optional and out of
  `isCachedTrainReveal`'s required checks (:77-97). An older cache entry then still restores, and
  the hook marks the review as resumed or starts fresh.
- **Residual blind spot (accept):** if the user leaves via Analyze and never returns to /train in
  that tab, the component-scoped pagehide listener is gone and no review flush lands. The row keeps
  its solve patch (guess_ms present, review_ms absent), which is itself a distinguishable state.
  Closing this would need a module-level listener outliving the screen. Not recommended (scope).

### Pattern 8: `client` device class

The only UA-based mobile definition is a hook-local const [VERIFIED: `useInstallPrompt.ts:190`]:
```typescript
  const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
```
Its comment (:185-189) says it is "deliberately NOT the project's viewport-based desktop-detection
hook". Calling `useInstallPrompt()` from the solve screen would mount its cooldown and
beforeinstallprompt machinery for one boolean. Extract the regex into `lib/deviceClass.ts`
(`export function isMobileUserAgent(): boolean`) and have `useInstallPrompt` call it (zero
behaviour change). The telemetry hook then uses `isMobileUserAgent() ? 'mobile' : 'desktop'`.
Do not confuse it with `useIsDesktop` (viewport >= 1024 px, `hooks/useIsDesktop.ts`), which governs
hover-vs-tap card semantics in `TrainReveal` (:764). The D-11 counter rule must key on the same
`isDesktop` the reveal uses, not on the UA class.

### Anti-Patterns to Avoid
- **Reading then writing the JSONB in Python** (select row, dict-merge, update): races the two
  writes. Use the SQL `||` merge.
- **Passing `telemetry=None` into `.values()`** when there is no patch: writes SQL NULL over an
  existing patch on the review path, or JSON null on a plain-JSONB column. Omit the key.
- **Counting `onStepChange` / `onSpotlightChange` calls:** both fire for non-user reasons (see Pattern 6).
- **Sending deltas** in the review patch: per-key overwrite turns a second flush into data loss.
- **`sendBeacon`:** cannot set `Authorization` → 401 (D-06).
- **Tracking via `useEffect` on a value for Umami:** irrelevant here (no Umami event added, D-10),
  but do not add one either.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON merge of two writes | Python read-modify-write | Postgres `coalesce(col,'{}'::jsonb) \|\| :patch` in the UPDATE | Atomic, one round trip, verified live |
| JSON null vs SQL NULL | ad-hoc `None` checks | `JSONB(none_as_null=True)` + omit column | Project precedent `users.first_touch` |
| Unload write | sendBeacon / sync XHR | `fetch(..., {keepalive: true})` | Header support; sync XHR is blocked in unload by modern browsers [ASSUMED] |
| Bound validation | manual if/else in router | Pydantic `Annotated[int, BeforeValidator(clamp), Field(ge, le, strict=True)]` | Boundary-validated, OpenAPI documented |
| TS/Python constant drift | codegen script | regex parity test (precedent `tests/services/test_train_score_parity.py`) | No `gen_train_*` script exists; parity test is the established cheap pattern |
| Visibility pause | per-component ad hoc listeners | one pure stopwatch + one listener (useBotGameClock semantics incl. initial-hidden seed) | Two known edge cases already solved there |

**Key insight:** the risky parts are semantic (what counts as a user action, which key wins on
merge), not technical. Every technical primitive needed already exists in the repo.

## Runtime State Inventory

Not a rename/refactor/migration phase (additive column + new route). Section intentionally omitted.

## Common Pitfalls

### Pitfall 1: JSON `null` in the column breaks the merge silently
**What goes wrong:** `coalesce('null'::jsonb, '{}'::jsonb) || jsonb_build_object('a', 1)` returns
`[None, {'a': 1}]`, an array [VERIFIED: live probe on dev Postgres this session].
**Why:** JSON null is a jsonb value, not SQL NULL, so `coalesce` passes it through, and
`null || object` is array concatenation.
**How to avoid:** `JSONB(none_as_null=True)` on model and migration; omit the column when there is
no patch; dump with `exclude_none=True`.
**Warning signs:** `jsonb_typeof(telemetry) = 'array'` in any row. Add it as a test assertion.

### Pitfall 2: Telemetry validation error 422s the solve
**What goes wrong:** a stale or buggy client sends `guess_ms: 1234.5` or an unknown key, and with a
plain `SolveTelemetry | None` field the whole solve 422s, so the puzzle is never recorded.
**How to avoid:** wrap validator drops invalid telemetry; clamp + round numerics (Pattern 3);
`Math.round` on the client as well.
**Warning signs:** 422s on `/train/sessions/*/solve` in logs; solve-error UI in Train.

### Pitfall 3: Counting effect-driven callbacks as user actions
**What goes wrong:** `onStepChange` fires on stepper mount and on every Solution reset;
`onSpotlightChange(null)` fires from the mobile tap-away listener; desktop hover and click arrive
through the same `onSpotlightChange(entry)`.
**How to avoid:** dedicated `onUserStep` / `onCardEngage` props (Pattern 6).
**Warning signs:** `review_line_steps > 0` on reveals where the user never touched a stepper (a
unit test can assert 0 after mount + Solution press).

### Pitfall 4: Stale closures in the pagehide handler
**What goes wrong:** a `pagehide` listener registered in an effect with `[]` deps reads the counters
from the first render.
**How to avoid:** keep all mutable telemetry in refs; the listener reads `ref.current`. Register
once per reveal and remove on cleanup.

### Pitfall 5: Next flush after the puzzle state resets
**What goes wrong:** building the review body inside `handleNext`'s aftermath (or in an effect on
puzzle change) reads the NEXT puzzle's position or reset counters.
**How to avoid:** build and send the body synchronously at the top of `handleNextFromReveal`,
before `walkthrough.leave()` / `handleNext()`; capture `sessionId` and `puzzle.position` from
props at that moment.

### Pitfall 6: Restored reveal's session id
**What goes wrong:** a restored TrainSolveScreen reads `trainSession.session?.session_id`. It equals
`restoredReveal.sessionId` (Train.tsx:122-123 only activates on equality), but during the brief
window before the session loads it is `null`.
**How to avoid:** the flush no-ops when `sessionId == null` (it is never shown before the session
loads anyway); alternatively prefer `restoredSolve.sessionId` for restored reveals.

### Pitfall 7: Test mocks of `trainApi` are explicit object literals
**What goes wrong:** `TrainSolveScreen.test.tsx:190-205` and `Train.solveLoop.test.tsx:208-220`
replace `trainApi` with a hand-listed object. A new `trainApi.recordReview` is `undefined` there.
A direct call in the Next handler then throws inside the click; through `useMutation` it becomes a
mutation error.
**How to avoid:** add `recordReview` to every `trainApi` mock that renders a reveal: the files
listed by `grep -rln trainApi src --include='*.test.tsx'` that mount TrainSolveScreen or Train
(TrainSolveScreen.test.tsx, TrainSolveScreen.restoredGameArrow.test.tsx, Train.solveLoop.test.tsx).
Stub `globalThis.fetch` where pagehide is exercised.
**Existing payload assertions survive:** `Train.solveLoop.test.tsx:387` uses `toMatchObject`
(extra `telemetry` key OK), and `TrainSolveScreen.test.tsx:705-716` asserts the retry body
`toEqual`s the first body. That holds only if the telemetry snapshot is frozen at move time
(Pattern 1), which makes this test a free regression guard.

### Pitfall 8: Think timer start on the first puzzle
**What goes wrong:** on the first puzzle per page load the Stockfish WASM loads ("Loading engine…",
`TrainSolveScreen.tsx:1794-1805`), and the guess UI does not exist until `isReady`. Starting at
mount inflates `guess_ms`.
**How to avoid:** start the think stopwatch when `isReady` first becomes true for the current
puzzle. Accepted residual: on a user's very first puzzle ever, the Phase 222 intro stepper
(`resolveIntroState`) shows before the guess; that reading time lands in `guess_ms`. It can be
excluded in SQL (first session's position 0).

### Pitfall 9: Mobile walkthrough auto-advance and spotlight
`useTrainWalkthrough.handleSpotlightChange` wraps `setSpotlight` (`useTrainWalkthrough.ts:134-141`)
and never spotlights programmatically, so no non-user spotlight exists to filter out
[VERIFIED: full file read]. Still route counting through `onCardEngage`, not through the
walkthrough wrapper.

## Code Examples

See Patterns 1-3 and 7 above (merge expression, route, Pydantic models, keepalive fetch). Each
was either executed in this session (merge SQL, Pydantic clamp/wrap) or copied from a verified
in-repo precedent (route shape, migration, token read). Additional skeletons:

### Repository function for the review flush
```python
# [proposal] app/repositories/train_repository.py
async def merge_solve_telemetry(
    session: AsyncSession, *, user_id: int, session_id: int, position: int, patch: dict[str, object]
) -> bool:
    """Merge a review-telemetry patch into one SOLVED, caller-owned drill_solves row.

    Session status is deliberately not checked: the last puzzle's flush always lands
    after completion (CONTEXT discretion). Returns False -> router 404.
    """
    result = await session.execute(
        update(DrillSolve)
        .where(
            DrillSolve.session_id == session_id,
            DrillSolve.position == position,
            DrillSolve.user_id == user_id,
            DrillSolve.solved_at.is_not(None),
        )
        .values(telemetry=_merged_telemetry(patch))
    )
    return result.rowcount == 1  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
```
(The `ty: ignore` comment form is copied verbatim from `train_repository.py:3004`.)

### Router test skeleton (fixtures verified in tests/routers/test_train.py)
Helpers exist: `_register_and_login` (:237), `_seed_game_with_blunder` (:255), `_seed_session` (:537,
seeds an open session + unsolved rows, telemetry omitted → SQL NULL), `_solve` (:670, posts the
four-field body; extend with an optional `telemetry` kwarg), `_delete_games` (:371). The `/enter`
tests at :3120-3174 use an inline `httpx.AsyncClient(transport=ASGITransport(app=app))`, which is
the shape to copy for `POST .../solves/{position}/review`.

```python
@pytest.mark.asyncio
async def test_review_flush_merges_into_solved_row(test_engine) -> None:
    user_id, token = await _register_and_login(f"train-tel-{uuid.uuid4().hex[:8]}@example.com")
    game_id = await _seed_game_with_blunder(test_engine, user_id, missed_pv_lines=_SHARP_PV_LINES)
    session_id = await _seed_session(test_engine, user_id, [(game_id, _FLAW_PLY_WHITE, int(DrillSource.SR_ITEM))])
    try:
        solve = await _solve(token, session_id, 0, telemetry={"v": 1, "guess_ms": 1200, "client": "mobile"})
        assert solve.status_code == 200
        review = await _review(token, session_id, 0, {"v": 1, "exit": "next", "review_ms": 5000})
        assert review.status_code == 204
        assert await _telemetry(test_engine, session_id, 0) == {
            "v": 1, "guess_ms": 1200, "client": "mobile", "exit": "next", "review_ms": 5000}
    finally:
        await _delete_games(test_engine, [game_id])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `navigator.sendBeacon` for unload analytics | `fetch(..., {keepalive: true})` when headers are needed | keepalive widely supported in evergreen browsers [ASSUMED] | Bearer auth works on unload |
| `unload`/`beforeunload` listeners | `pagehide` (fires on iOS Safari, bfcache-friendly) | project precedent `instrument.ts:32-36` comment: "fires reliably on iOS Safari" | Use pagehide only |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Key names `think_hidden_ms` / `review_hidden_ms` replace D-04's single `hidden_ms` (forced by per-key merge) | Pattern 3 | Low; owner may prefer other names, but one key cannot hold both phases |
| A2 | Cap values: 30 min = 1,800,000 ms; line steps 50; explore moves 50; cards 10 | Pattern 3 | Low; discretion area, values tunable without migration |
| A3 | Think stopwatch starts at engine `isReady`, not at component mount | Pitfall 8 | Medium for position-0 think times; documented definition |
| A4 | A PV-line click in exploration (`freePlay.playLine`) counts as ONE explore move | Pattern 6 | Low; affects `review_explore_moves` scale only |
| A5 | Analyze-then-never-return loses the review flush (accepted residual) | Pattern 7 | Low-medium; identifiable as solve patch without review keys |
| A6 | `fetch` keepalive reliably delivers on pagehide in target browsers; sync XHR is blocked during unload | Pattern 7 / Don't Hand-Roll | Medium; some flushes may be lost on hard kills, which is inherent |
| A7 | iPadOS desktop-mode Safari (UA reports Macintosh) classifies as `desktop` | Pattern 8 | Low; same misclassification the install prompt already accepts |
| A8 | `resumed: true` detection via a sessionStorage marker `(sessionId, position)` set when the think stopwatch starts | Discretion "Timer interruptions" | Low; worst case `resumed` missing on a reloaded think |

## Open Questions

1. **`hidden_ms` key naming (A1).** Recommendation: `think_hidden_ms` + `review_hidden_ms`. A
   single `hidden_ms` cannot survive the second merge. The planner should state it explicitly in
   the plan so the verifier does not flag a D-04 deviation.
2. **Should the solve patch be dropped silently or logged when invalid?** Recommendation: drop
   silently. A Sentry capture per malformed telemetry would be noise from stale bundles during
   deploys. Optional: `logger.warning` without variables in the message.
3. **Abandon via Analyze (A5).** Recommendation: accept. Revisit only if the 2026-10-25 analysis
   shows many solve-only rows with `review_*` missing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (Docker) | migration, router tests | ✓ | container `flawchess-dev-db-1` Up (healthy) [VERIFIED: docker ps] | — |
| uv / Python 3.14 | backend | ✓ | cpython-3.14.3 (path in probe traceback) | — |
| Alembic | migration | ✓ | head `e3a8c5f17b20` | — |
| Node / vitest | frontend tests | ✓ | vitest v5.0.0 ran this session | — |

**Missing dependencies:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest (async, `test_engine` fixture; per-session cloned DB, `tests/conftest.py`) |
| Framework (frontend) | vitest 5 + Testing Library + jsdom |
| Config file | `pyproject.toml` / `frontend/vite.config.ts` `test:` block (:90-94) |
| Quick run (backend) | `uv run pytest tests/routers/test_train.py -k "telemetry or review" -x` |
| Quick run (frontend) | `cd frontend && npx vitest run src/lib/__tests__/visibleStopwatch.test.ts src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts` |
| Full suite | pre-merge gate in CLAUDE.md (`uv run pytest -n auto -x`, ruff, ty, `npm run lint && npm run build && npm test -- --run && npm run knip`) |

### Phase Requirements → Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01 storage/NULL | solve without telemetry leaves `telemetry IS NULL`; with telemetry stores the object; `jsonb_typeof <> 'array'` | integration | `uv run pytest tests/routers/test_train.py -k "solve_without_telemetry_stays_sql_null or solve_with_telemetry_stores_object" -x` | ❌ Wave 0 |
| D-01 merge | review flush adds keys without dropping solve keys; second flush overwrites per key | integration | `uv run pytest tests/routers/test_train.py -k "review_flush_merges or review_flush_last_write_wins" -x` | ❌ Wave 0 |
| D-01 forbid/caps | ReviewTelemetry unknown key → 422; over-cap clamps; float rounds; bool-as-int rejected | unit | `uv run pytest tests/schemas/test_train_telemetry_schema.py -x` | ❌ Wave 0 |
| D-02 optional / never costs solve | solve with invalid telemetry → 200, row solved, telemetry NULL | integration | `uv run pytest tests/routers/test_train.py -k "invalid_telemetry_still_solves" -x` | ❌ Wave 0 |
| D-02 measurement | guess_ms/move_ms measured from isReady → guess → move with fake timers | unit (hook) | `npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts` | ❌ Wave 0 |
| D-03 route | 204 on solved own row; 404 foreign user; 404 unsolved; 204 after session completed/expired; 422 bad body | integration | `uv run pytest tests/routers/test_train.py -k review -x` | ❌ Wave 0 |
| D-03 flush on Next | Next calls `recordReview` once with `exit:"next"` and correct position, before advancing | component | `npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx -t telemetry` | ✅ file, ❌ cases |
| D-03/D-06 pagehide | dispatching `pagehide` calls `fetch` with `keepalive:true` + `Authorization: Bearer <token>` + `exit:"pagehide"`; after Next it is a no-op | unit (hook) | `npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts -t pagehide` | ❌ Wave 0 |
| D-04 visible only | hidden span excluded from ms and added to hidden_ms; mount-into-hidden seeds pause; duplicate hidden idempotent; cap applied | unit | `npx vitest run src/lib/__tests__/visibleStopwatch.test.ts` | ❌ Wave 0 |
| D-04/D-01 parity | Python caps == TS caps | unit | `uv run pytest tests/schemas/test_train_telemetry_parity.py -x` | ❌ Wave 0 |
| D-05 grading untouched | solve response/ladder identical with and without telemetry | integration | `uv run pytest tests/routers/test_train.py -k "telemetry_does_not_change_grading" -x` | ❌ Wave 0 |
| D-07 exit | `exit` required in ReviewTelemetry (missing → 422) | unit | in `test_train_telemetry_schema.py` | ❌ Wave 0 |
| D-08 leaderboard toggle | `tab-switch` fires once on hand switch, never on restore/re-tap | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx -t "tab-switch"` | ✅ EXISTS (ran green this session: 2 passed) |
| D-09 client | `client` = mobile for an iPhone UA, desktop otherwise; useInstallPrompt unchanged | unit | `npx vitest run src/lib/__tests__/deviceClass.test.ts` | ❌ Wave 0 |
| D-09 privacy | Privacy page contains the device-class sentence | component | `npx vitest run src/pages/__tests__/Privacy.test.tsx` (new) or extend an existing render test | ❌ Wave 0 |
| D-11 card open | mobile tap counts immediately; desktop hover < 800 ms does not; >= 800 ms does; desktop departed click counts immediately | component/unit | `npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts -t card` | ❌ Wave 0 |
| D-12 distinct + total | same card twice → 1; total = line boxes + also-fine, max seen | unit | same file `-t distinct` | ❌ Wave 0 |
| D-13 walkthrough | sticky true if activeStep was ever non-null on the reveal | unit | same file `-t walkthrough` | ❌ Wave 0 |
| D-14 counters | line steps only from goTo (0 after mount + Solution reset), capped; explore moves from start/playMove/playLine; analyze flag | component | `npx vitest run src/components/train/__tests__/TrainLineStepper.test.tsx -t onUserStep` + hook file | ✅ stepper file, ❌ cases |
| Discretion: Analyze round trip | review stopwatch state persists through trainRevealCache and resumes on restored mount | unit | `npx vitest run src/lib/__tests__/trainRevealCache.test.ts` | ✅ file, ❌ cases |

**Mutation proof (per memory `feedback_mutation_test_gap_closures`):** for D-01's "omit when absent"
and D-02's wrap validator, the verifier should revert the guard and confirm the test fails.
Presence-of-code checks are not enough.

### Sampling Rate
- **Per task commit:** the quick-run command for the touched side.
- **Per wave merge:** `uv run pytest tests/routers/test_train.py tests/schemas -x` and
  `cd frontend && npx vitest run src/components/train src/hooks src/lib`.
- **Phase gate:** full pre-merge gate (CLAUDE.md), including `npm run build` (tsc: shared types
  change) and `npm run knip` (new exports must be used).

### Wave 0 Gaps
- [ ] `tests/schemas/test_train_telemetry_schema.py` — D-01/D-07 model behaviour
- [ ] `tests/schemas/test_train_telemetry_parity.py` — caps parity (copy `test_train_score_parity.py` regex approach)
- [ ] `tests/routers/test_train.py` — `_solve(..., telemetry=)` kwarg + `_review` + `_telemetry` read helper
- [ ] `frontend/src/lib/__tests__/visibleStopwatch.test.ts`
- [ ] `frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts`
- [ ] `frontend/src/lib/__tests__/deviceClass.test.ts`
- [ ] `recordReview` added to the `trainApi` mocks in TrainSolveScreen.test.tsx, TrainSolveScreen.restoredGameArrow.test.tsx, Train.solveLoop.test.tsx
- Visibility test hygiene: reset `document.visibilityState` via `Object.defineProperty(..., {configurable: true, writable: true})` in `beforeEach` (precedent `useStockfishEngine.test.ts:194-203`, which explains that the override "leaks across tests in this file").

### Tracer-first slice (recommended plan order)
1. **Backend tracer:** migration + model column + `SolveTelemetry` + merge in `record_solve` +
   router passes `model_dump(exclude_none=True)`; tests: NULL-stays-NULL, stored object,
   invalid-telemetry-still-solves. Shippable alone (an old frontend sends nothing).
2. **Review route:** schema + `merge_solve_telemetry` + route + ownership/unsolved/completed tests.
3. **Frontend think time:** `visibleStopwatch`, `deviceClass`, hook (think part), `SolveRequest.telemetry`.
4. **Frontend review + flush:** review stopwatch, Next flush, pagehide keepalive, reveal-cache persistence.
5. **Counters:** `onUserStep`, `onCardEngage` (hover-hold), `onCardsTotalChange`, `onUserMove`,
   analyze, walkthrough flag; Privacy line; D-08 verification (already green).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users `current_active_user` (Bearer JWT, `app/users.py:198`); keepalive fetch sends the same Bearer token |
| V3 Session Management | no | stateless JWT; unchanged |
| V4 Access Control | yes | `user_id` from `current_active_user` only, in the UPDATE WHERE clause (IDOR guard T-189-16 pattern); never from body/path |
| V5 Input Validation | yes | Pydantic `extra="forbid"`, strict types, Literal enums, clamped ints, Path bounds (int4/int2) |
| V6 Cryptography | no | none |
| V8 Data Protection / Privacy | yes | Privacy.tsx line for device class + behavioural timing (D-09); no PII in telemetry (ints/bools/Literals only) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR: write telemetry into another user's row | Tampering | `DrillSolve.user_id == user.id` in the UPDATE; 404 on miss (no existence oracle) |
| Arbitrary JSON stuffing / storage abuse | Tampering / DoS | `extra="forbid"`, closed key set, ints clamped, no strings except Literals |
| Out-of-range path ints → asyncpg overflow → 500/Sentry noise | DoS | `Path(ge=1, le=2**31-1)` / `Path(ge=0, le=2**15-1)` |
| Telemetry influencing scores | Elevation / Repudiation | D-05: never read by grading/leaderboard; test asserts identical SolveResponse with and without telemetry |
| CSRF on keepalive POST | Spoofing | Bearer header (not cookies) required; cross-site page cannot read the token |
| Error-message cardinality in Sentry | Info | constant `HTTPException` detail strings; context via `set_context` (CLAUDE.md) |

## Project Constraints (from CLAUDE.md)

- Router: `APIRouter(prefix="/train")` with relative paths; no business logic in routers; no SQL in services.
- `sentry_sdk.capture_exception()` in non-trivial except blocks of routers; no variables in error messages; context via `set_context`.
- Never `asyncio.gather` on one `AsyncSession` (single UPDATE here anyway).
- No magic numbers: every cap and the 800 ms hover threshold are named constants (both stacks).
- `Literal[...]` instead of bare `str` for fixed sets (`exit`, `client`); explicit return types; ty clean (`uv run ty check app/ tests/ scripts/`); `# ty: ignore[rule]` with reason only where unfixable.
- Pydantic at boundaries, TypedDicts for internal structures.
- DB: avoid native ENUM; JSONB is the owner's explicit choice (D-01). Nullable column, no index.
- Time-dependent endpoints use `dev_now_utc`. The review route is not time-dependent and takes none.
- Nesting depth <= 4 (backend `check_function_size.py --fail-over-depth 4`, frontend eslint `max-depth` 4); ~100 logic lines / cognitive complexity 15 are soft targets, so keep TrainSolveScreen additions to hook wiring.
- Frontend: `data-testid` on new interactive elements (none expected); no `text-xs`; knip-clean exports; run `npm run build` (tsc) because shared types change; no Prettier.
- Frontend Sentry: TanStack mutation errors are already captured globally, so do not double-capture; the keepalive fetch failure is an expected failure and is not captured.
- Umami: no new event (D-10), and no `trackFeature` from effects.
- Comment bug fixes at the fix site; changelog bullet under `## [Unreleased]` at merge.
- Do not run `bin/reset_db.sh`; plans must not depend on a DB reset (memory `feedback_no_dev_db_reset_in_plans`).

## Sources

### Primary (HIGH confidence, read this session)
- `app/repositories/train_repository.py` :895-934 (`stamp_session_entered`), :2870-3100 (`record_solve`), :3140-3208 (`reveal_for_puzzle`)
- `app/routers/train.py` :1-250
- `app/models/drill_solve.py` (full), `app/models/user.py:100-112`, `app/schemas/train.py` (sections), `app/schemas/users.py:105-150`, `app/routers/users.py:210-240`
- `alembic/versions/20260927_120000_d6e4bcc06b45_users_first_touch_attribution.py`, `..._3b7e2f9c41a6_drill_sessions_entered_at.py`, `alembic.ini:17`, `uv run alembic heads`
- `tests/routers/test_train.py` (helpers), `tests/services/test_train_score_parity.py`
- Frontend: `TrainSolveScreen.tsx` :700-1189, :1440-1881; `TrainReveal.tsx` :109-176, :756-1222, :1375-1400; `TrainLineStepper.tsx` :150-249; `useTrainWalkthrough.ts` (full); `useTrainFreePlay.ts` :380-462; `Train.tsx` :60-259; `api/client.ts` :1-140, :286-330; `useBotGameClock.ts` :236-347; `useInstallPrompt.ts` :170-222; `trainRevealCache.ts` (full); `TrainLeaderboardCard.tsx` :55-66, :375-400 + its test :385-401; `Privacy.tsx` :24-64; `useTrainSession.ts` :280-335; `types/train.ts:86-92`
- Live probes: dev Postgres JSONB merge/NULL semantics; Pydantic 2.13.5 clamp/forbid/wrap; vitest leaderboard tab-switch run

### Secondary / Tertiary
- None. No web sources were needed. Browser keepalive/pagehide behaviour is tagged [ASSUMED] (A6).

## Metadata

**Confidence breakdown:**
- Backend write path / route / migration: HIGH (code read + executed SQL probe)
- Pydantic boundary design: HIGH (executed probe)
- Frontend hook points: HIGH (all file:line read); hook API shape: MEDIUM (design proposal)
- Browser unload delivery: MEDIUM/ASSUMED (platform behaviour, not testable in jsdom)

**Research date:** 2026-10-05
**Valid until:** 2026-11-04 (stable internal code; re-check line numbers if TrainSolveScreen/TrainReveal change first)
