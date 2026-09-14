# Phase 222: Train Bot-Narrated Onboarding & Verdicts - Pattern Map

**Mapped:** 2026-09-13
**Files analyzed:** 22 (5 new, 17 modified)
**Analogs found:** 21 / 22

Every path below was verified git-tracked with `git ls-files`. This document does NOT
re-derive what `222-RESEARCH.md` already proves with file:line evidence (Findings A–L,
Pitfalls 1–14, Code Examples 1–5) — it adds the **analog excerpts** the planner should
tell the executor to copy from, per file.

---

## File Classification

### Backend

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `alembic/versions/<new>_phase_222_train_onboarding_seen.py` (NEW) | migration | schema DDL | `alembic/versions/20260802_174733_6e7e50844af5_phase_203_reminder_intent.py` | exact |
| `app/models/train_settings.py` (MOD) | model | — | same file, `reminder_intent_at` block (`:114-126`) | exact (self) |
| `app/schemas/train.py` (MOD) | schema | request-response | same file, `TrainSettingsResponse` / `SolvedResult` | exact (self) |
| `app/routers/train.py` (MOD, new POST) | router | request-response | same file, `update_train_settings` (`:265-320`) | exact (self) |
| `app/repositories/train_repository.py` (MOD) | repository | CRUD | same file, `get_settings` / `get_or_create_settings` / `_stamp_pool_eligibility` (`:552+`) | exact (self) |
| `app/services/activity_queries.py` (MOD) | service (read-only query) | batch/analytics | same file, `fetch_train` (`:282-299`) + `Payload` TypedDict (`:61-85`) | exact (self) |
| `app/services/activity_stats.py` (MOD, 1 line) | service | batch | same file, `build_payload` (`:70-90`) | exact (self) |
| `scripts/reset_train_state.py` (MOD) | script | CRUD | same file, `_reset` (`:183-200`) | exact (self) |
| `tests/routers/test_train.py` (MOD) | test | request-response | same file, `test_settings_403_guest` (`:2429`), `test_put_settings_*reminder_intent_at` (`:2449-2530`) | exact (self) |
| `tests/test_admin_activity_stats.py` (MOD) | test | batch | same file, helper block (`:38-60`) | exact (self) |
| `tests/scripts/test_reset_train_state.py` (MOD) | test | CRUD | same file (`:68-71`) | exact (self) |

### Frontend

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `frontend/src/components/train/TrainBotBubble.tsx` (NEW) | component (presentational) | request-response (props) | `frontend/src/components/bots/PersonaCard.tsx` (avatar block) + `TrainReveal.tsx`'s `TrainScoreChip` (`:319-333`) | role-match |
| `frontend/src/components/train/TrainBotStepper.tsx` (NEW, optional) | component | event-driven | none close — `TrainLineStepper.tsx` is a **chess-move** stepper (RESEARCH Pitfall 4). Use a plain `useState<number>` | **no analog** |
| `frontend/src/lib/trainBotCopy.ts` (NEW) | utility (pure) | transform | `frontend/src/lib/trainGuessLabels.ts` (copy table + pure resolver, no React) | exact |
| `frontend/src/components/train/trainBubbleState.ts` (NEW) | utility (pure) | transform | `trainGuessLabels.ts`'s `guessFeedbackProse` (guard-clause returns, no nesting) | exact |
| `frontend/src/components/train/TrainSolveScreen.tsx` (MOD) | component | event-driven | self — the five JSX guard blocks at `:1128-1175` and the action row at `:1047-1105` | exact (self) |
| `frontend/src/components/train/TrainReveal.tsx` (MOD) | component | request-response | self — spotlight ring `cn('cursor-pointer', isSpotlit && 'ring-2 ring-brand-brown')` (`:1035`) | exact (self) |
| `frontend/src/components/train/TrainScoreScreen.tsx` (MOD) | component | request-response | self — the `<h1>Session complete</h1>` at `:134` is what the bubble replaces | exact (self) |
| `frontend/src/hooks/useTrainSession.ts` (MOD) | hook | event-driven | self — `sessionMutation.onSuccess` seed (`:170-176`) + `solveMutation.onSuccess` accumulate (`:190-203`) | exact (self) |
| `frontend/src/hooks/useTrainOnboarding.ts` (NEW, or fold into `useTrainSettings`) | hook | request-response | `frontend/src/hooks/useTrainSettings.ts` (`:58-81`, mutation + `setQueryData`) | exact |
| `frontend/src/api/client.ts` (MOD) | api client | request-response | self — `trainApi.updateSettings` (`:286-287`) | exact (self) |
| `frontend/src/types/train.ts` (MOD) | type mirror | — | self — `TrainSettingsResponse` (`:183-190`) | exact (self) |
| `frontend/src/lib/personas/personaRegistry.ts` (MOD) | config/registry | — | self — `Persona` interface (`:74-105`) + any of the 24 entries | exact (self) |
| `frontend/src/lib/trainGuessLabels.ts` (MOD) | utility | transform | self — `GUESS_LABELS` (`:15-18`) | exact (self) |
| `frontend/src/pages/Home.tsx` (MOD, one line) | page copy | — | self — `:68` marketing line (RESEARCH Finding K) | exact (self) |
| `frontend/src/pages/activity/render.js` (MOD) | renderer (imperative) | transform | self — `renderConversionCard` (`:242-258`, the `#conv-big`/`#conv-exp` text pattern) | exact (self) |
| `frontend/src/pages/activity/ActivityPage.tsx` (MOD) | page (DOM-id host) | — | self — the `hero` block at `:402-405` + the Train section at `:469-478` | exact (self) |
| `frontend/src/types/activity.ts` (MOD) | type mirror | — | self — `ActivityStatsPayload` (`:20-40`) | exact (self) |
| frontend tests (`TrainSolveScreen.test.tsx`, `trainBotCopy.test.ts`, …) | test | — | `frontend/src/lib/__tests__/trainScore.test.ts` (pure) + `frontend/src/components/bots/__tests__/SetupScreen.test.tsx:136-148` (`vi.spyOn(Math,'random')`) | exact |

---

## Pattern Assignments

### `alembic/versions/<new>_phase_222_train_onboarding_seen.py` (NEW — migration)

**Analog:** `alembic/versions/20260802_174733_6e7e50844af5_phase_203_reminder_intent.py`
(39 lines end to end). **`down_revision` = `b7d4f5a60002`** (current head, RESEARCH).

Full analog body — copy the shape, including the docstring's "why no backfill" paragraph
(D-13 needs the same statement):

```python
"""phase 203 reminder intent

Revision ID: 6e7e50844af5
Revises: ca8c8fbc2080
Create Date: 2026-08-02 17:47:33.093501+00:00

OFFER-03/OFFER-05 (D-02/D-15): adds `reminder_intent_at`, a client-writable
nullable timestamp on `train_settings`, ...

No backfill, no data migration: every existing row lands on NULL, meaning
"no install intent expressed yet."
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6e7e50844af5'
down_revision: Union[str, Sequence[str], None] = 'ca8c8fbc2080'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "train_settings", sa.Column("reminder_intent_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("train_settings", "reminder_intent_at")
```

Phase 222 = the same two calls, three times each (`intro_seen_at`,
`reveal_walkthrough_seen_at`, `sr_explained_at`).

---

### `app/models/train_settings.py` (model)

**Analog:** the `reminder_intent_at` block in the same file (`:114-126`). Append the three
columns immediately after it, with one comment block explaining the access pattern (this
file's convention is a dense per-column rationale comment, not a bare declaration):

```python
    # Phase 203 (OFFER-03/OFFER-05, D-02/D-15). Opposite access pattern from
    # reminder_last_sent_on directly above: reminder_intent_at IS
    # client-writable and appears in BOTH TrainSettingsUpdate and
    # TrainSettingsResponse. ... an instant, not a calendar watermark, so it
    # uses DateTime(timezone=True) rather than Date (mirrors the codebase's
    # nullable-instant convention ... never a naive DateTime). No backfill:
    # every row that predates this column reads back NULL ...
    reminder_intent_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

**Phase-222 delta to note in the comment:** unlike `reminder_intent_at`, the three new
columns are **Response-only** (D-12) — the closer access-pattern sibling is
`reminder_last_sent_on`, which is absent from `TrainSettingsUpdate`.

---

### `app/schemas/train.py` (schema, request-response)

**Analog A — `TrainSettingsResponse` / `TrainSettingsUpdate` split** (`:273-300`). The
docstring already states the D-12 rule verbatim; extend it, do not restate it elsewhere:

```python
class TrainSettingsResponse(BaseModel):
    """Response for GET/PUT /train/settings.
    ...
    `reminder_last_sent_on` is deliberately absent — it is the reminder job's
    own watermark (D-06), never readable or writable by a client.
    """

    timezone: str
    weekday_mask: int
    puzzles_per_session: int
    reminder_enabled: bool
    reminder_hour: int
    reminder_intent_at: datetime | None
```

Add `intro_seen_at: datetime | None`, `reveal_walkthrough_seen_at: datetime | None`,
`sr_explained_at: datetime | None` here **only**. `TrainSettingsUpdate` is untouched —
note that class's own docstring line "so a PUT body can never smuggle a server-owned
field" is the exact justification.

**Analog B — `SolvedResult` (`:52-77`)** for the D-17 extension. The docstring's
"Not an answer-key leak" paragraph is the pattern to extend field-by-field:

```python
class SolvedResult(BaseModel):
    """...
    Not an answer-key leak: both `correct_guess` and `move_quality` were
    already returned by `SolveResponse` for each of these same positions at
    the moment they were attempted ... Entries here carry no `position`,
    `game_id`, `ply`, or best-move field ...
    """

    correct_guess: bool
    move_quality: Literal["good", "inaccuracy", "wrong"]
```

The three new fields copy `SolveResponse`'s own declarations verbatim (`:219-222`):
`source: Literal["sr_item", "red_herring", "sharp_filler"]`,
`item_status: Literal["active", "mastered", "parked"] | None`, `due_date: date | None`.

---

### `app/routers/train.py` (router, request-response — new POST)

**Analog:** `update_train_settings` (`:265-320`) — the only `/train` handler that is a
write + `NowUtc` + settings-response return, i.e. exactly the new endpoint's shape.

**Module-level pattern to reuse as-is** (`:42-55`):

```python
router = APIRouter(prefix="/train", tags=["train"])

#: The current UTC instant, dev-clock-shiftable. Real clock outside development.
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]


def _reject_guest(user: User) -> None:
    """D-05: explicit gate, not an empty-result inference. ..."""
    if user.is_guest:
        raise HTTPException(status_code=403, detail="Train requires a full account")
```

**Handler shape to copy** (`:265-320`, trimmed):

```python
@router.put("/settings", response_model=TrainSettingsResponse)
async def update_train_settings(
    body: TrainSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
) -> TrainSettingsResponse:
    """..."""
    _reject_guest(user)
    settings_row = await train_repository.upsert_settings(
        session,
        user_id=user.id,
        ...,
        now_utc=now_utc,
    )
    await session.commit()
    return TrainSettingsResponse(
        timezone=settings_row.timezone,
        weekday_mask=settings_row.weekday_mask,
        puzzles_per_session=settings_row.puzzles_per_session,
        reminder_enabled=settings_row.reminder_enabled,
        reminder_hour=settings_row.reminder_hour,
        reminder_intent_at=settings_row.reminder_intent_at,
    )
```

Load-bearing details: `_reject_guest(user)` is the **first statement**; `user.id` comes
from the auth dependency, never the path (V4); the explicit field-by-field
`TrainSettingsResponse(...)` construction (no `**asdict`) is the convention — the three
new fields must be added at **both** return sites in this file (`get_train_settings` at
`:255-263` and `update_train_settings` at `:313-320`), plus the new handler.

The new handler's only deviation: the `Literal` step arrives as a **path parameter**
(`OnboardingStep = Literal["intro", "reveal_walkthrough", "sr_explained"]`), so there is
no body schema at all. FastAPI 422s an unknown step — no hand-rolled validation.

---

### `app/repositories/train_repository.py` (repository, CRUD)

**Analog A — the three mechanical dataclass touch points.** `TrainSettingsRow`
(`:154-164`), `get_settings`'s row→dataclass map (`:258-270`), and
`get_or_create_settings`'s `pg_insert(...).values(...)` **and** its post-insert
`TrainSettingsRow(...)` (`:287-330`). All four lists must gain the three fields; miss one
and `ty` fails. The `get_or_create_settings` new-row half:

```python
    stmt = pg_insert(TrainSettings).values(
        user_id=user_id,
        timezone=DEFAULT_TIMEZONE,
        ...
        # Phase 203 (OFFER-03): a brand-new user has never expressed install
        # intent -- NULL, same create-on-first-touch seam as every other
        # default here.
        reminder_intent_at=None,
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["user_id"])
    await session.execute(stmt)
    return TrainSettingsRow(
        timezone=DEFAULT_TIMEZONE,
        ...
        reminder_intent_at=None,
    )
```

`upsert_settings` (`:333-344`) must **NOT** gain them (D-12).

**Analog B — the stamp function.** `_stamp_pool_eligibility` (`:552-575`) is the existing
"stamp once, never overwrite" precedent and its docstring states that rule outright:

```python
async def _stamp_pool_eligibility(
    session: AsyncSession,
    *,
    user_id: int,
    settings_row: TrainSettingsRow,
    today: datetime.date,
    has_material: bool,
) -> datetime.date | None:
    """D-06: stamp the eligibility watermark once, the first time qualifying
    material is observed; never overwrite an existing one.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
        ...
    """
```

Copy: the keyword-only signature, the `AsyncSession. Caller commits.` arg line, the
`V4: never client-supplied` arg line, and the first-write-wins semantics (RESEARCH
recommends `WHERE <col> IS NULL` / `COALESCE`).

---

### `app/services/activity_queries.py` (service, analytics read)

**Analog:** `fetch_train` (`:282-299`) — same table, same cutoff param, same helpers:

```python
async def fetch_train(conn: AsyncConnection, window_start: datetime.date) -> list[list[Any]]:
    return _table(
        await _rows(
            conn,
            """
            SELECT session_date AS day, count(*) AS sessions,
                   count(DISTINCT user_id) AS users,
                   count(*) FILTER (WHERE status = 'completed') AS completed,
                   ...
            FROM drill_sessions
            WHERE session_date >= CAST(:cutoff AS date)
            GROUP BY 1 ORDER BY 1
            """,
            cutoff=window_start,
        )
    )
```

Rules carried by this excerpt: `text()` bound params via `_rows` (never f-strings — the
V5 control), `_table` for JSON-safe coercion of `date`/`Decimal`, `CAST(:cutoff AS date)`,
explicit `-> list[list[Any]]`. The RESEARCH §Finding J CTE drops straight into this shape.

**Payload key** (`:61-85`) — add `train_funnel: list[list[Any]]` beside `train`:

```python
class Payload(TypedDict):
    """The complete dashboard dataset, as served to the page."""
    ...
    bot: list[list[Any]]
    train: list[list[Any]]
    solves: list[list[Any]]
```

**`app/services/activity_stats.py`** `build_payload` (`:79`) — one line inside the same
`async with`, sequential (never `asyncio.gather`):
`train_funnel=await queries.fetch_train_funnel(conn, window.window_start),`

---

### `frontend/src/pages/activity/render.js` + `ActivityPage.tsx` + `types/activity.ts`

**Analog:** the conversion card end-to-end. This is the big-number/text card pattern that
needs **no** `check:activity-layout` fixture (it uses no chart primitive).

`render.js:242-258` — `renderConversionCard`, the numerator/denominator prose shape D-19
asks for:

```js
function renderConversionCard(){
  const c=C();
  $("#conv-big").textContent=CONV.sessions?(100*CONV.converted/CONV.sessions).toFixed(1)+"%":DASH;
  if(!CONV.sessions){
    $("#conv-exp").textContent="There were no guest sessions in the selected range.";
  } else {
    $("#conv-exp").innerHTML=`<b>${CONV.converted}</b> of <b>${CONV.sessions}</b> guest sessions have since become
      registered accounts.`;
  }
```

`render.js:38` — the payload destructure block the new key joins:

```js
  SIGNUPS=payload.signups; BOT=payload.bot; TRAIN=payload.train; SOLVES=payload.solves;
```

`render.js:360-370` — the render call list; add `renderTrainFunnelCard();` next to
`renderTrainCard();`.

`ActivityPage.tsx:402-405` — the hero markup whose **ids** `render.js` addresses
(rename an id in the JSX and the card silently disappears):

```tsx
              <div className="hero">
                <span className="cap">Guest → registered</span>
                <span className="big" id="conv-big"></span>
                <span className="exp" id="conv-exp"></span>
              </div>
```

Place the new card inside the existing Train section (`:469-478`), which also shows the
`<p className="note">` slot for the right-censoring caveat and the
`data-testid="activity-details-train"` convention:

```tsx
          <div className="card">
            <h3>Sessions per day by outcome</h3>
            <div className="legend" id="tr-legend"></div>
            <div className="chart" id="c-train"></div>
            <details className="data">
              <summary data-testid="activity-details-train">Show the numbers</summary>
              <div className="tblwrap" id="t-train"></div>
            </details>
          </div>
```

`types/activity.ts:20-40` — mirror the Payload key with the same tuple typing:

```ts
export interface ActivityStatsPayload {
  ...
  train: (string | number | null)[][];
  solves: (string | number | null)[][];
```

---

### `frontend/src/components/train/TrainBotBubble.tsx` (NEW — presentational component)

**Analog A — avatar + fallback:** `frontend/src/components/bots/PersonaCard.tsx:107-145`.
Copy the resolver pair and the `<span>`+`<img>` idiom verbatim (RESEARCH Example 5 quotes
the same block); note `aria-hidden="true"`, `alt=""`, `loading="lazy"`, the tint on the
wrapper, and the size passed as a px constant in `style`, not a Tailwind class:

```tsx
export function PersonaCard({ persona, onSelect, winsForPersona }: PersonaCardProps): ReactElement {
  const avatar = placeholderAvatarFor(persona);
  const avatarSrc = resolveAvatarSrc(persona);
  ...
      <span
        aria-hidden="true"
        className="flex shrink-0 items-center justify-center overflow-hidden rounded-full text-2xl"
        style={{
          backgroundColor: avatar.tint,
          width: AVATAR_SIZE_PX,
          height: AVATAR_SIZE_PX,
        }}
      >
        {avatarSrc !== undefined ? (
          <img src={avatarSrc} alt="" loading="lazy" className="h-full w-full object-cover" />
        ) : (
          avatar.emoji
        )}
      </span>
      <span className="text-sm font-medium text-foreground">{persona.name}</span>
```

That last line is also the bot-name-under-the-avatar pattern (`text-sm`, the frontend
floor) the chat row needs.

**Analog B — the inline point pills:** `TrainReveal.tsx:319-333`, `TrainScoreChip`. It is
currently module-private; export it (or move it to its own module) rather than restyling
a new span:

```tsx
function TrainScoreChip({ points, testid }: { points: number; testid: string }): ReactElement {
  return (
    <span
      // rounded-full + slightly wider padding: the same pill shape as the
      // "Points: +N" flash over the board (Phase 200 UAT round 3) ...
      className="shrink-0 rounded-full px-2 py-0.5 text-sm font-semibold text-white"
      style={{ backgroundColor: points > 0 ? TRAIN_VERDICT_CORRECT : TRAIN_VERDICT_INCORRECT }}
      data-testid={testid}
    >
      +{points}
    </span>
  );
}
```

Theme colors come from `lib/theme.ts` constants, never inline hex — the bubble
border/pulse color follows the same rule.

**Analog C — buttons inside the bubble:** `TrainSolveScreen.tsx:1128-1158` (guess pair) and
`:1047-1092` (action row). Move these nodes in **with their testids unchanged**
(`btn-train-guess-critical`, `btn-train-guess-several`, `btn-train-solution`,
`btn-train-analyze`, `btn-train-next`, `train-guess-prompt`, `train-move-prompt`) —
RESEARCH Finding F counts ~140 assertions that stay green if you do:

```tsx
          {guess === null && !moveApplied && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-sm font-semibold" data-testid="train-guess-prompt">
                Before you move with {puzzle.side_to_move}, decide:
              </p>
              <div className="flex gap-2">
                <Button
                  variant="brand-outline"
                  className={TRAIN_BUTTON_CLASS}
                  data-testid="btn-train-guess-critical"
                  onClick={() => setGuess('critical')}
                >
                  {GUESS_LABELS.critical}
                </Button>
```

Note `variant="brand-outline"` for the guess pair and `variant="default"` for Next
(`:1086-1093`) — keep both; that is the frontend/CLAUDE.md primary/secondary rule.

**Analog D — the grading spinner row** (`TrainSolveScreen.tsx:1166-1171`), which becomes
the bubble's `grading` state:

```tsx
          {moveApplied && isGrading && (
            <div className="flex items-center gap-2" data-testid="train-grading-indicator">
              <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
              <p className="text-sm font-semibold text-muted-foreground">Checking your move…</p>
            </div>
          )}
```

---

### `frontend/src/lib/trainBotCopy.ts` + `trainBubbleState.ts` (NEW — pure utilities)

**Analog:** `frontend/src/lib/trainGuessLabels.ts` — the project's existing "shared copy
table + pure resolver, no React import" module, and the closest analog in the tree:

```ts
/**
 * Shared "critical vs several fine moves" guess vocabulary (190.1-03 D-03).
 *
 * Single source of truth for the exact wording so `TrainSolveScreen`'s guess
 * buttons and `TrainReveal`'s verdict row can never drift apart — extracted
 * to its own module (rather than exported from either component) to avoid a
 * parent/child circular import between the two ...
 */
export type Guess = 'critical' | 'several';

export const GUESS_LABELS: Record<Guess, string> = {
  critical: 'One critical move',
  several: 'Several fine moves',
};
```

and the resolver shape (`guessFeedbackProse`, `:57-73`) — **guard-clause returns, no
nesting**, with the "LOCKED wording, never reworded" note in the docstring:

```ts
export function guessFeedbackProse(
  guess: Guess,
  correctGuess: boolean,
  fromOwnBlunder: boolean,
  moveTier: TrainMoveTier,
): string {
  if (guess === 'critical' && correctGuess && moveTier === 'good')
    return 'Right, and you found it: only one move works here.';
  if (guess === 'critical' && correctGuess)
    return "Right, only one move works here, but that wasn't it.";
  ...
```

D-09 edit in this same file: `GUESS_LABELS` becomes `'Only one'` / `'Several'`, plus a
**new** long-form map for the reveal card header. `guessFeedbackProse` is untouched.
`Persona`-typed pools and the injectable `rng` go in `trainBotCopy.ts` per RESEARCH
Examples 2–3; `resolveBubbleState` per Example 1 (same guard-clause style as above).

---

### `frontend/src/lib/personas/personaRegistry.ts` (registry)

**Analog:** the `Persona` interface (`:74-105`) and any of its 24 entries. Field
declarations in this interface always carry a doc comment stating provenance and the rule;
`temperament` needs the same:

```ts
export interface Persona {
  id: PersonaId;
  style: Style;
  rung: Rung;
  /** Honest, tilde-prefixed, round-50 measured/extrapolated display label
   * (D-03/D-06/D-07), read from `PERSONA_CALIBRATION[id].label`. This is
   * what `PersonaCard`/`PersonaDetailSurface` render — never `~${rung}`. */
  calibratedLabel: string;
  ...
  /** Placeholder-avatar glyph (D-18) — species-appropriate emoji rendered on
   * the persona's per-style tint (`personaAvatars.ts`). */
  avatarEmoji: string;
}
```

Entry shape to extend (all 24, e.g. `:447-458` — Hilda, the D-05 fixed teacher, must be
`smart`; `grinder-1600` Tank must be `stern`):

```ts
  'wall-1800': {
    id: personaId('Wall', 1800),
    style: 'Wall',
    rung: 1800,
    botElo: PERSONA_CALIBRATION['wall-1800'].botElo,
    calibratedLabel: PERSONA_CALIBRATION['wall-1800'].label,
    blend: RUNG_BLEND[1800],
    name: 'Hilda the Hippo',
    species: 'Hippo',
    bio: 'Hilda calculates carefully ...',
    avatarEmoji: '🦛',
  },
```

`Record<PersonaId, Persona>` (`:467`) makes the field exhaustive at compile time — a
missing `temperament` is a type error, which is the D-01 guarantee. Lookups use
`personaForId` (`:500-503`), never a raw index.

---

### `frontend/src/hooks/useTrainSettings.ts` / new stamping mutation

**Analog:** the same file's mutation (`:58-81`) — the `setQueryData` idiom RESEARCH
Finding D requires so the stamp response refreshes the shared cache with no refetch:

```ts
export const TRAIN_SETTINGS_QUERY_KEY = ['train', 'settings'] as const;

  const mutation = useMutation({
    mutationFn: ({ weekdayMask, puzzlesPerSession, ... }: TrainSettingsDraft) => {
      const body: TrainSettingsUpdate = {
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        weekday_mask: weekdayMask,
        ...
      };
      return trainApi.updateSettings(body);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data);
      void queryClient.invalidateQueries({ queryKey: TRAIN_PROGRESS_QUERY_KEY });
    },
  });
```

Two rules this excerpt encodes: the mutation body is built **field-by-field**, never
spread from the response (which is why Response-only fields are safe, RESEARCH Pattern 4);
and there is **no** `Sentry.captureException` here — the global `MutationCache.onError`
already captures each mutation error once (module docstring `:13-16`).

**API client analog** (`frontend/src/api/client.ts:284-287`):

```ts
  getSettings: () =>
    apiClient.get<TrainSettingsResponse>('/train/settings').then(r => r.data),
  updateSettings: (data: TrainSettingsUpdate) =>
    apiClient.put<TrainSettingsResponse>('/train/settings', data).then(r => r.data),
```

The stamp call is one more line in this object, typed `<TrainSettingsResponse>`.

**Type mirror** (`frontend/src/types/train.ts:183-190`) — add the three
`… : string | null` fields to `TrainSettingsResponse`, leave `TrainSettingsUpdate` alone.

---

### `frontend/src/hooks/useTrainSession.ts` (hook)

**Analog:** the two `onSuccess` blocks in the same file. Seed (`:161-176`):

```ts
  const sessionMutation = useMutation({
    mutationFn: trainApi.composeOrResumeSession,
    onSuccess: (data) => {
      setSession(data);
      setCurrentIndex(data.puzzles.length > 0 ? 0 : null);
      // 260728-tgc (BUGFIX-TRAIN-SCORE-CROSSDEVICE): seed the score from the
      // server's own solved_results via the shared scorePuzzle/
      // aggregateSessionScore pair ... this is the cross-device fix.
      setSessionScore(
        aggregateSessionScore(
          data.solved_results.map((r) => scorePuzzle(r.correct_guess, r.move_quality)),
        ).total,
      );
```

Accumulate (`:188-202`):

```ts
    onSuccess: (data, variables) => {
      // SEED-119: the single scorePuzzle formula, never re-derived here.
      const points = scorePuzzle(data.correct_guess, data.move_quality);
      setSessionScore((prev) => prev + points);
      setSolvedPositions((prev) => { const next = new Set(prev); next.add(variables.body.position); return next; });
```

`solvedOutcomes` (RESEARCH Finding C / Example 4) is the same seed-then-append pair, one
state slot over. Keep the "never re-derived here" discipline: the bubble copy resolvers
take the outcome array, they do not recompute scoring.

---

### `frontend/src/components/train/TrainReveal.tsx` (spotlight visual)

**Analog:** the same file's spotlight ring, `:1035` and `:1203`. Reuse the **class only** —
never the `spotlightKey`/`onSpotlightChange` channel, which drives board arrows
(RESEARCH Anti-Patterns):

```tsx
    const cardClass = cn('cursor-pointer', isSpotlit && 'ring-2 ring-brand-brown');
```
```tsx
        className={cn(
          showAlsoFine && 'cursor-pointer',
          showAlsoFine && isAlsoFineSpotlit && 'ring-2 ring-brand-brown',
        )}
```

The D-09 reveal-header call site is 13 lines below the second block
(`Guess: {guess !== null ? GUESS_LABELS[guess] : ''}`) and becomes the new long form.

---

### `frontend/src/components/train/TrainScoreScreen.tsx`

**Analog / edit site:** `:132-134` — the heading the bubble replaces, and the
`data-testid="train-score-screen"` root that must survive:

```tsx
    <div className="flex flex-col items-center gap-4 py-12 text-center" data-testid="train-score-screen">
      <h1 className="text-xl font-semibold">Session complete</h1>
```

Reduced-motion precedent in the same file (`:116, 126-130, 137-139`) —
`prefersReducedMotion()` gates the **class**, not the element; copy that for the bubble
nudge/pulse, and see RESEARCH Finding G before asserting on it in tests.

---

### `scripts/reset_train_state.py`

**Analog:** `_reset` in the same file (`:183-200`) — add the three `=None` clears to the
existing `.values(...)` (RESEARCH Finding I; without this, onboarding UAT is one-shot per
dev account):

```python
async def _reset(session: AsyncSession, user_id: int, *, reset_settings: bool) -> None:
    """Delete the user's drill state and clear (or drop) their settings row."""
    await session.execute(delete(DrillSolve).where(DrillSolve.user_id == user_id))
    ...
        await session.execute(
            update(TrainSettings)
            .where(TrainSettings.user_id == user_id)
            .values(
                streak_count=0,
                shield_level=0,
                streak_settled_through=None,
                pool_eligible_since=None,
            )
        )
```

---

### Tests

**Backend router test analog:** `tests/routers/test_train.py:2429-2440` — the guest gate
shape every new `/train` endpoint test copies (unique email per test, register+login
helper, `_set_guest`, assert 403):

```python
async def test_settings_403_guest(test_engine) -> None:
    """A guest account is rejected 403 on both GET and PUT /train/settings."""
    email = f"train-settings-guest-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    await _set_guest(test_engine, user_id)

    get_resp = await _get_settings(token)
    assert get_resp.status_code == 403
```

Round-trip + 422 analog for the stamp endpoint: `:2449-2496`
(`test_put_settings_writes_and_round_trips_reminder_intent_at` shows the
`"2026-08-02T12:34:56Z"` RFC-3339 string-comparison trick and the raw
`httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` call used when the shared
helper cannot express the body). This file's module docstring maintains a per-phase index
of test names — append a Phase 222 block there too; it is a hard convention in this file.

**Backend analytics test analog:** `tests/test_admin_activity_stats.py:38-60` — the
self-contained `unique_email` / `register` / `login` helpers (the docstring states the
project convention that each file duplicates helpers rather than sharing a module).

**Frontend pure-module test analog:** `frontend/src/lib/__tests__/trainScore.test.ts:1-25`
— docstring naming the requirement, `import { describe, expect, it } from 'vitest'`,
named imports through the `@/` alias, one case per behaviour bullet plus boundary cases.
This is the template for `trainBotCopy.test.ts` (the D-15/D-16 truth table).

**Random-cast test analog:** `frontend/src/components/bots/__tests__/SetupScreen.test.tsx:136-148`:

```tsx
describe('SetupScreen — Random resolves to a concrete color at Start (D-12, V-08)', () => {
  it('a Math.random stub < 0.5 resolves to "white"', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.1);
    ...
```

Use the injected `rng` for the pure picker's unit tests and this `vi.spyOn` form for the
rendered cast in component tests (RESEARCH's "do both" recommendation).

---

## Shared Patterns

### Guest gate (every `/train/*` handler)
**Source:** `app/routers/train.py:48-55` (`_reject_guest`)
**Apply to:** the new stamp endpoint — first statement, before any repository call.

### Dev clock
**Source:** `app/routers/train.py:45` — `NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]`
**Apply to:** the stamp endpoint. Never `datetime.now()`.

### IDOR guard
**Source:** `app/routers/train.py:66-68` docstring — "The user id always comes from
`current_active_user.id` — never from a request body or path parameter (V4/IDOR guard)."
**Apply to:** the stamp endpoint and every new repository function (`user_id: int`
keyword-only, documented with the same Args line).

### Explicit response construction
**Source:** `app/routers/train.py:255-263` and `:313-320`
**Apply to:** all three `TrainSettingsResponse(...)` sites — field-by-field, no spread.

### Read/write schema split
**Source:** `app/schemas/train.py` `TrainSettingsResponse` vs `TrainSettingsUpdate` docstrings
**Apply to:** the three seen-timestamps (Response only) and their frontend type mirror.

### Testid stability while relocating nodes
**Source:** RESEARCH Finding F table; nodes at `TrainSolveScreen.tsx:1047-1105, 1128-1175`
**Apply to:** every element moved into the bubble. Only `board-btn-mute` is deleted.

### Pure module, no React import
**Source:** `frontend/src/lib/trainGuessLabels.ts` header; `frontend/src/lib/trainScore.ts:1-6`
**Apply to:** `trainBotCopy.ts`, `trainBubbleState.ts`.

### Activity dashboard four-file seam (id-addressed)
**Source:** `activity_queries.fetch_train` → `activity_stats.build_payload:79` →
`types/activity.ts:20-40` → `render.js:38 + :242-258 + :368` → `ActivityPage.tsx:402-405`
**Apply to:** the funnel card. Renaming a DOM id in the JSX silently drops the card.

### `text-sm` floor + Button variants
**Source:** `PersonaCard.tsx:147-148`; `TrainSolveScreen.tsx:1136-1158` (`brand-outline`)
and `:1086-1093` (`default`)
**Apply to:** all new bubble copy, names, pills, and buttons.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/components/train/TrainBotStepper.tsx` | component | event-driven | No forward-only onboarding stepper exists. `TrainLineStepper.tsx` is a chess-move replayer (`:17-24`) and is explicitly NOT reusable (RESEARCH Pitfall 4). Build a plain `useState<number>` + Next/Got it, with buttons following the `TrainSolveScreen.tsx:1086-1093` Button pattern. |

Partial-analog caveats (analog exists but diverges):
- **Funnel card**: no per-query test exists on the activity dashboard today, so
  `tests/test_admin_activity_stats.py` supplies the harness pattern but not a query-test
  precedent — TRAINBOT-06's test is genuinely new coverage.
- **Stamp endpoint**: `update_train_settings` is the shape analog, but it is a full-replace
  PUT; the new endpoint is a narrow first-write-wins POST with a `Literal` path param and
  no body. Copy the frame, not the upsert semantics.

---

## Metadata

**Analog search scope:** `app/{routers,schemas,models,repositories,services}`,
`alembic/versions`, `scripts/`, `tests/{routers,scripts}`, `tests/test_admin_activity_stats.py`,
`frontend/src/{components/train,components/bots,lib,lib/personas,hooks,pages,pages/activity,types,api}`
**Files read this session:** 24 (all verified tracked via `git ls-files`)
**Pattern extraction date:** 2026-09-13
