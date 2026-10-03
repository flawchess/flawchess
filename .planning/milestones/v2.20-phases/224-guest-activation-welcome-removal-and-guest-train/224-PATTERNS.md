# Phase 224: Guest Activation — Welcome Removal & Guest Train - Pattern Map

**Mapped:** 2026-09-17
**Files analyzed:** 24 (6 new, 15 modified, 3 deleted)
**Analogs found:** 21 / 21 new-or-substantially-new units (3 deletions need no analog)

All analog paths below were verified with `git ls-files` (tracked source, no gitignored mirrors).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| NEW `frontend/src/components/train/SignupAskActions.tsx` | component (action pair for `actions` slot) | event-driven (click → nav / promotion) | `frontend/src/components/bots/BotDrawOfferActions.tsx` | **exact** (same slot, same fragment-of-two-Buttons shape) |
| NEW `frontend/src/components/import/ImportGuestPromoBubble.tsx` | component (bubble host) | request-response (profile read) + event | `frontend/src/components/train/TrainScoreScreen.tsx:154-158` (persona memo) + `BotGameDesktopLayout.tsx:99` (bubble+actions composition) | role-match |
| NEW `frontend/src/components/train/__tests__/SignupAskActions.test.tsx` | test | — | `frontend/src/components/bots/__tests__/BotGameBubble.test.tsx` (actions-slot describe block, `:88-110`) | exact |
| NEW `frontend/src/components/import/__tests__/ImportGuestPromoBubble.test.tsx` | test | — | same as above + `frontend/src/components/train/__tests__/TrainBotBubble.test.tsx:70` | exact |
| NEW `frontend/src/pages/__tests__/Home.redirect.test.tsx` | test (redirect assertion) | — | `frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx` | **exact** (same `MemoryRouter` + `LocationDisplay` spy + profile-mock idiom) |
| NEW backend test: guest end-to-end warm-up in `tests/routers/test_train.py` | test | request-response | `tests/routers/test_train.py::test_solve_records_and_advances_streak` (:1303) + `::test_403_guest` (:967) for the guest setup | exact |
| NEW `app/services/activity_queries.py::fetch_guest_train` | service (raw analytics SQL) | CRUD/read | `fetch_conversion` (:631) and `fetch_train` (:284) in the same file | exact |
| NEW `reports/growth/guest-activation-baseline-2026-09-XX.md` | doc | — | `reports/growth/growth-recommendations-2026-09-15.md` | role-match (that file commits no SQL; see note) |
| MOD `frontend/src/pages/Home.tsx` (:777-784) | page | request-response | own file (`hasGames` line stays) | n/a |
| MOD `frontend/src/App.tsx` (`IMPORT_EXEMPT_ROUTES`, `ImportRequiredRoute`, nav) | config/route guard | request-response | existing exempt-route entries in the same array | n/a |
| MOD `frontend/src/pages/Welcome.tsx` | page | static | `frontend/src/components/train/TrainGuestGate.tsx:47` (signup button being deleted — lift its umami attrs) | partial |
| MOD `frontend/src/pages/Import.tsx` (:419-433) | page | request-response | — (branch is *removed*, replaced by the new component) | n/a |
| MOD `frontend/src/components/train/TrainScoreScreen.tsx` (:260) | component | event-driven | Pattern 3 below (`actions` prop, today `undefined`) | n/a |
| MOD `frontend/src/lib/trainBotCopy.ts` (`scoreBubbleCopy`, `INTRO_*`, `WARMUP_TAIL`) | utility (pure copy fn) | transform | `WARMUP_REMINDER_ASK_COPY` (:559-566) — named-constant-per-string shape | exact |
| MOD `frontend/src/components/train/TrainScheduleSettings.tsx` (D-13) | component | request-response | `showReminderBlock` / `showQr` / `showPhoneSection` in the same file (:358, :421-423) | **exact (in-file)** |
| MOD `app/routers/train.py` (`_reject_guest` + 7 sites) | router | request-response | — (deletion) | n/a |
| MOD `app/services/guest_cleanup_service.py` | service | batch delete | existing delete block in `_purge_guest` (the Phase 189 comment being superseded) | exact |
| MOD `app/repositories/train_reminder_repository.py:43-46` | repository docstring | — | n/a | n/a |
| MOD `tests/test_guest_cleanup_service.py::test_purge_guest_cascades_drill_rows` (:418) | test | — | itself (rewrite the docstring + assertions) | n/a |
| MOD `tests/test_admin_activity_stats.py::fake_payload` (:103) | test fixture | — | itself | n/a |
| MOD `app/services/activity_stats.py::build_payload` (:57-92) | service | — | its own per-key `await queries.fetch_*` lines | n/a |
| MOD `frontend/src/pages/activity/render.js::renderTrainCard` (:308-323) + `ActivityPage.tsx:461-478` | view (vanilla JS table) | transform | `renderTrainCard`'s own `table("#t-train", [...])` call | exact |
| DEL `frontend/src/lib/welcomeDismissal.ts` | — | — | importers listed below | n/a |
| DEL `frontend/src/components/train/TrainGuestGate.tsx`, `frontend/src/pages/__tests__/Train.guestGate.test.tsx` | — | — | n/a | n/a |

---

## Pattern Assignments

### `SignupAskActions.tsx` (component, event-driven) — THE key new file

**Analog:** `frontend/src/components/bots/BotDrawOfferActions.tsx` (whole file, 48 LOC). Same
job: a two-`Button` fragment rendered into a bot bubble's `actions` slot. Copy its shape
verbatim — fragment (no wrapper div; the bubble supplies `mt-2 flex flex-wrap justify-end gap-2`),
`variant="default"` + `variant="brand-outline"`, one `data-testid` each.

```tsx
import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { BOT_ACTION_BUTTON_CLASS } from '@/components/bots/chipStyles';

export function BotDrawOfferActions({ offerLive, onAccept, onDecline }: BotDrawOfferActionsProps): ReactElement | null {
  if (!offerLive) return null;
  return (
    <>
      <Button variant="default" className={BOT_ACTION_BUTTON_CLASS} onClick={onAccept} data-testid="btn-accept-bot-draw">
        Accept
      </Button>
      <Button variant="brand-outline" className={BOT_ACTION_BUTTON_CLASS} onClick={onDecline} data-testid="btn-decline-bot-draw">
        Decline
      </Button>
    </>
  );
}
```

Deltas for the new file: (a) `BOT_ACTION_BUTTON_CLASS` is bots-scoped — the Train surface's
equivalent is `TRAIN_BUTTON_CLASS`; use that or no class at all, do NOT import from
`components/bots/chipStyles`. (b) Order is "Why?" (`brand-outline`) then "Sign up free"
(`default`) per S-4, i.e. the *reverse* emphasis order of the analog. (c) Explicit
`ReactElement` return type (CLAUDE.md).

**Promotion handoff excerpt to copy** — `frontend/src/pages/Import.tsx:422-424` (the button
this phase deletes; lift it verbatim):

```tsx
onClick={() => { logoutForPromotion(); window.location.href = '/login?tab=register'; }}
data-umami-event="signup-cta"
data-umami-event-source="import-promo"
```

**Second umami call site to match** — `frontend/src/components/train/TrainGuestGate.tsx:47`
(`data-umami-event="signup-cta"`, being deleted) and `frontend/src/pages/Welcome.tsx:193`
(same attribute, stays). The new score-screen source string is `train-score`.

**Umami rule (frontend/CLAUDE.md:41):** never `data-umami-event` on an internal react-router
`<Link>` — the tracker `preventDefault()`s and assigns `location.href`, downgrading to a full
page reload. The "Why?" control must be a `<Button onClick={() => navigate('/welcome')}>` with
NO umami attribute; `data-umami-event` belongs on `<button>` and outbound `target="_blank"`
links only. The non-attribute alternative in this repo is `trackEvent('signup-cta', { source })`
(`Home.tsx:345`, `:707`; `LoginForm.tsx:154`; `PublicHeader.tsx:31`).

---

### `TrainBotBubble` prop signature (exact, for both new bubbles)

`frontend/src/components/train/TrainBotBubble.tsx:54-78` verbatim:

```tsx
export interface TrainBotBubbleProps {
  persona: Persona;
  /** Drives the `data-state` attribute and the nudge border/pulse styling. */
  state: TrainBubbleState['kind'];
  nudgeNonce?: number;
  /** The bubble's copy for the current state. */
  children: ReactNode;
  /** Optional action row (guess buttons, or Next/Solution/Analyze), rendered
   * as its own row INSIDE the bubble, below `children`. */
  actions?: ReactNode;
  ring?: boolean;
  /** Avatar size step; only the /train landing page uses `'large'`. */
  avatarSize?: TrainBotAvatarSize;
}
```

Render of the slot (`:148-152`) — the caller supplies no layout:

```tsx
{actions !== undefined && (
  <div className="mt-2 flex flex-wrap justify-end gap-2">{actions}</div>
)}
```

Only `persona`, `state`, `children` are required. Existing `actions` callers:
`TrainSolveScreen.tsx:1768` (`actions={bubbleBody.actions}`), `Bots.tsx:428`
(`actions={drawOfferActions}`), `BotGameDesktopLayout.tsx:99`.

**Persona memoisation** — `TrainScoreScreen.tsx:154-158` verbatim, mirror it in the Import bubble:

```tsx
  // D-04: a random smart bot hosts the score bubble regardless of the
  // session's rating band — memoised once per mount so a re-render can never
  // recast mid-read (no deps: pickBot('smart') has no external inputs, so
  // exhaustive-deps raises nothing here).
  const bot = useMemo(() => pickBot('smart'), []);
```

→ Import bubble: `const bot = useMemo(() => pickBot('friendly'), []);` (ImportPage re-renders on
every import-job poll tick, so the memo is load-bearing, not cosmetic).

**Additive `actions` on the score bubble** — current call site `TrainScoreScreen.tsx:260`, which
passes NO `actions` today, so the guest branch cannot alter registered output (SC 3):

```tsx
      <div className="w-full max-w-sm text-left" data-testid="train-score-bubble">
        <TrainBotBubble persona={bot} state="verdict">
```

---

### `ImportGuestPromoBubble.tsx` (component) — what it replaces

**Analog for the composition:** `BotGameDesktopLayout.tsx:99`
(`<BotGameBubble persona={persona} line={botLine} actions={drawOfferActions} />`) — bubble +
actions assembled by the parent, zero logic in the actions component.

**The markup being removed**, `frontend/src/pages/Import.tsx:418-434` verbatim (testids
`import-guest-promo-info` / `import-guest-promo-link` go away with it):

```tsx
      {profile?.is_guest && (
        <Alert variant="info" icon={DoorOpen} data-testid="import-guest-promo-info" className="mb-4">
          <p className="text-sm">
            <button
              onClick={() => { logoutForPromotion(); window.location.href = '/login?tab=register'; }}
              className="font-medium underline underline-offset-2"
              data-testid="import-guest-promo-link"
              data-umami-event="signup-cta"
              data-umami-event-source="import-promo"
            >
              Sign up free
            </button>{' '}
            to use FlawChess on any device and unlock automatic Stockfish analysis of your games.
          </p>
        </Alert>
      )}
```

Note the message text is the D-06 payoff source for the Import bubble's bot-voice rewrite.
After removal, `DoorOpen` (`Import.tsx:3`) and `logoutForPromotion`/`useAuth` (`:26`, `:259`)
become unused **in that file** and must be deleted; `Alert` itself stays (used at `:250`, `:580`).

---

### `TrainScheduleSettings.tsx` guest gating (D-13 / GUESTACT-15)

**Analog is in-file.** The structural-absence idiom, `:358` and `:421-423` verbatim:

```tsx
  const showReminderBlock = capability.isResolved && capability.available;
```
```tsx
  const showQr = !isMobile && !isStandalone;
  const showMobileInstallButton = isMobile && !isStandalone && canInstall;
  const showPhoneSection = showQr || showMobileInstallButton;
```

Render sites `:494` (`{showReminderBlock && <ReminderControls .../>}`) and `:509`
(`{showPhoneSection && ( … <TrainInstallQr testId="qr-handoff-settings" /> … )}`). Add `&& !isGuest`
to both boolean expressions — never a disabled placeholder, never a wrapper conditional around the
JSX (keeps the existing comment block accurate and costs one boolean each).

---

### `trainBotCopy.ts` copy constants (utility, transform)

**Analog for the new constants:** `WARMUP_REMINDER_ASK_COPY` (`:559-566`) — module-level named
constant, `Record<Key, string>` when keyed, plain `const` when single. `WARMUP_TAIL` (`:384`) is
the single-string shape:

```ts
const WARMUP_TAIL = "That one was a warm-up, so it won't come back. Your own positions will.";
```

The warm-up variant to branch (`:681-689`), precedence table unchanged:

```ts
  if (input.isWarmup) {
    return {
      lines: [
        `${sessionOpener(input.band)} Those were warm-ups, nothing to bring back yet. ` +
          'Once your games are analyzed, your own mistakes take over.',
        WARMUP_REMINDER_ASK_COPY[input.reminderAsk],
      ],
    };
  }
```

`scoreBubbleCopy` measures complexity **4** against the cap of 15 — the whole `hasGames` × `isGuest`
branch belongs here, in a pure function, not in the component.

---

### `Home.redirect.test.tsx` (test)

**Analog:** `frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx` — the repo's only
dedicated redirect test, and it already tests the exact `hasGames → /library/games | /library/import`
rule this phase makes unconditional. Copy four things verbatim:

```tsx
// ── Controllable useUserProfile mock ──────────────────────────────────────────
const profileState: { chess_com_game_count: number; lichess_game_count: number } =
  { chess_com_game_count: 0, lichess_game_count: 0 };

vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({ data: { ...profileState } }),
}));

// ── Location spy ──────────────────────────────────────────────────────────────
function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}
```

plus `// @vitest-environment jsdom` on line 1, the heavy-child `vi.mock` stubs, and an
`afterEach(() => { cleanup(); /* reset profileState */ })`. `HomePage` reads its profile through
`useQuery(['userProfile'])` directly (`Home.tsx:755-765`), not `useUserProfile`, so the mock target
is `@/hooks/useAuth` (for `token`) plus a seeded `QueryClient` or an `apiClient` mock — state that
delta explicitly in the plan.

**Auth mock shape** (`Welcome.test.tsx:29-34`, being rewritten — reuse it):

```tsx
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ token: 'test-token', logoutForPromotion: mockLogoutForPromotion }),
}));
```

`Welcome.test.tsx:15` imports `isWelcomeDismissed, setWelcomeDismissed` from
`@/lib/welcomeDismissal` — this import and the localStorage round-trip describe block are deleted
with the module.

**Full `welcomeDismissal.ts` importer list (knip gate):** `Welcome.tsx:8`, `Home.tsx:2`,
`pages/__tests__/Welcome.test.tsx:15`. `lib/botGameSnapshot.ts:5,16` only *mentions* it in comments —
reword, don't delete.

---

### Bubble component tests

**Analog:** `frontend/src/components/bots/__tests__/BotGameBubble.test.tsx`. Two rules from its
docstring the new tests must follow: use a real registry persona, and assert copy against the copy
function's own return, never a hard-coded string.

```tsx
const PERSONA = PERSONA_REGISTRY['attacker-800'];

describe('BotGameBubble — actions slot', () => {
  it('renders the actions slot inside the bubble when supplied', () => {
    render(<BotGameBubble persona={PERSONA} line={null} actions={<button>Accept</button>} />);
    expect(screen.getByRole('button', { name: 'Accept' })).toBeTruthy();
  });

  it('omits the actions row entirely when not supplied', () => {
    render(<BotGameBubble persona={PERSONA} line={null} />);
    expect(screen.queryByRole('button')).toBeNull();
  });
});
```

The `TrainBotBubble` equivalent is `TrainBotBubble.test.tsx:70`.

---

### Backend guest end-to-end warm-up test (`tests/routers/test_train.py`)

**Guest setup analog** — `::test_403_guest` (:967-980), the exact four lines to reuse (the test
itself inverts to 200):

```python
    email = f"train-guest-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    await _set_guest(test_engine, user_id)
```

Fixture/helper names, all module-local in that file: `test_engine` (the only fixture),
`_register_and_login(email) -> (user_id, token)` (:~360), `_set_guest(test_engine, user_id)` (:390),
`_seed_game_with_blunder`, `_seed_drill_item`, `_seed_session`, `_solve`, `_get_drill_item`,
`_delete_games`, `_get_settings`, `_put_settings`, `_stamp_onboarding`. The four tests to invert:
`test_403_guest` (:967), `test_settings_403_guest` (:2551), `test_onboarding_403_guest` (:2580),
`test_progress_403_guest` (:2992).

**Solve-loop analog** — `::test_solve_records_and_advances_streak` (:1303-1327), the shape the new
guest warm-up test copies (note the `try/finally: await _delete_games(...)` — mandatory, the eval
lottery leaks otherwise):

```python
@pytest.mark.asyncio
async def test_solve_records_and_advances_streak(test_engine) -> None:
    """A correct solve advances streak 0 -> 1, stays active, gets a real due_date."""
    email = f"train-solve-adv-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    ...
    try:
        resp = await _solve(token, session_id, 0, guess="critical", move_quality="good")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["streak"] == 1
    finally:
        await _delete_games(test_engine, [game_id])
```

The guest warm-up test seeds NO game (zero-game path), so it needs no `finally` cleanup of games —
but it must still not leak a non-guest Train row (MEMORY `project_eval_lottery_test_isolation`).

**Promotion-preservation analog:** `tests/test_guest_auth.py::test_data_preserved_after_promotion`
(:614-646, proves in-place identity via `created_at`); Google path
`tests/test_guest_google_promotion.py::test_promotion_preserves_user_id` (:169).

**Purge test to rewrite:** `tests/test_guest_cleanup_service.py::test_purge_guest_cascades_drill_rows`
(:418) — its 20-line docstring currently *asserts* "the guest's drill_sessions row survives (D-04)".
Both the docstring and the assertions invert; keep its note that the autouse
`_cleanup_leaked_guest_rows` fixture handles teardown.

---

### `activity_queries.py` guest-cohort query (service, read)

**Analog:** `fetch_conversion` (:631-661) — the closest match by cohort and by return shape
(a `dict[str, Any]` of ints, not a table):

```python
async def fetch_conversion(conn: AsyncConnection, window_start: datetime.date) -> dict[str, Any]:
    """Guest -> registered conversion, from the stamped promoted_at column.
    ...
    """
    row = (
        await _rows(
            conn,
            f"""
            WITH u AS (
              SELECT id, ({_PROMOTED_GUEST}) AS converted
              FROM users u
              WHERE created_at >= CAST(:first AS date) AND {_GUEST_COHORT}),
            ...
            """,
            first=window_start,
        )
    )[0]
    return {
        "sessions": int(row[0]),
        "converted": int(row[1]),
        ...
    }
```

Copy: the f-string + `_GUEST_COHORT` / `_PROMOTED_GUEST` constants, `CAST(:first AS date)` named
params (never f-string interpolation of values), `_rows(conn, sql, **params)`, explicit `-> dict[str, Any]`
return annotation, and `int(row[n])` coercion. `fetch_train` (:284-302, a `_table(...)` returning
`list[list[Any]]`) is the shape to use instead if the guest row becomes table columns; note it has
**no `users` join at all**, so this is a new query, not a filter tweak. `fetch_purged_excluded`
(:504-531) supplies the D-12 footnote.

**Payload key wiring, three coupled sites:**

1. `activity_queries.Payload` TypedDict (:61-86) — add the key, e.g. `guest_train: dict[str, Any]`
   alongside `conversion: dict[str, Any]` and `purged_excluded: dict[str, int]`.
2. `app/services/activity_stats.py::build_payload` (:57-92) — one line in the same
   `await queries.fetch_*(conn, window.window_start)` style:
   ```python
            conversion=await queries.fetch_conversion(conn, window.window_start),
            purged_excluded=await queries.fetch_purged_excluded(conn, window.window_start),
   ```
3. `tests/test_admin_activity_stats.py::fake_payload` (:103-129) — **missing the key fails ~8 tests**:
   ```python
   def fake_payload(range_key: queries.RangeKey = "all") -> queries.Payload:
       """A minimal, schema-complete Payload for tests that monkeypatch build_payload
       and only care about call counts / the echoed range key, not real query data."""
       return queries.Payload(
           ...
           conversion={},
           conversion_compare=[],
           purged_excluded={},
       )
   ```

**Frontend render analog** — `frontend/src/pages/activity/render.js::renderTrainCard` (:308-323):

```js
  table("#t-train",["Date","Sessions","Users","Completed","Expired","Open","Puzzles served"],
    TRAIN.map(r=>[long(r[0]),r[1],r[2],r[3],r[4],r[5],r[6]]).reverse());
```

and the card markup `frontend/src/pages/activity/ActivityPage.tsx:461-478` (`#c-train` chart,
`<summary data-testid="activity-details-train">`, `#t-train` table wrap). **Extend the table or add
a hero pair — do NOT add a chart series**: charts are geometry-validated by
`npm run check:activity-layout` (`frontend/scripts/check-activity-layout.mjs`) at four phone widths.

---

### Baseline note (`reports/growth/…`)

**Analog:** `reports/growth/growth-recommendations-2026-09-15.md` — the only file in that directory.
Copy its front-matter convention (dated filename, a sources line naming "prod DB … Umami DB (both
sites, via SSH read-only), the in-app Activity Pulse dashboard", and the top-of-file dated
correction block idiom). **Deliberate divergence:** that report commits **no SQL**; the new note
must, because its whole purpose is that the after-reading runs the same query. Reuse
`fetch_funnel`'s predicate (`activity_queries.py:471-491`) verbatim for the import-start half.

---

## Shared Patterns

### Guest / games reads
**Source:** `frontend/src/pages/Train.tsx:66-70`
**Apply to:** every new guest branch (SignupAskActions hosts, TrainScheduleSettings, copy fns)

```tsx
  // FLAWCHESS-64: is_guest read from useUserProfile(), never useAuth().user
  // (always null, carries no is_guest — D-02, cf. the Analysis.tsx:789
  // free-play ELO source comment).
  const { data: profile, isError: profileError } = useUserProfile();
  const isGuest = profile?.is_guest === true;
```

`hasGames`, from `frontend/src/pages/Home.tsx:778-779`:

```tsx
    const hasGames =
      (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0) > 0;
```

Both values should be **passed as props** into `TrainScoreScreen` from `Train.tsx` — calling
`useUserProfile()` inside `TrainScoreScreen` and branching costs 2+ complexity and breaches (see
headroom table).

### Button variants
**Source:** `frontend/src/components/bots/BotDrawOfferActions.tsx` + frontend/CLAUDE.md:18
**Apply to:** every new button. Primary = `variant="default"`; secondary = `variant="brand-outline"`
(never `variant="secondary"`, never hand-rolled `bg-*`). `data-testid` kebab-case,
`btn-{action}` prefix, on every interactive element. Minimum font size `text-sm`.

### Structural absence, never a disabled placeholder
**Source:** `frontend/src/components/train/TrainScheduleSettings.tsx:355-358`
**Apply to:** guest suppression of the reminder block, QR block and reminder ask.

### Purge deletes
**Source:** `app/services/guest_cleanup_service.py::_purge_guest`, the existing Phase 189
comment-plus-delete block (the comment that D-08 supersedes begins
`# Phase 189 Plan 02 (POOL-09, D-04/D-05): the Train tables need NO handling here either.`).
Two statements, same transaction; `drill_solves` rides the `drill_sessions` CASCADE:

```python
await session.execute(delete(DrillSession).where(DrillSession.user_id == guest_id))
await session.execute(delete(TrainSettings).where(TrainSettings.user_id == guest_id))
```

### Sentry
`_reject_guest` sits *before* every existing try/except in `app/routers/train.py` — removing it must
not touch those blocks. New backend code uses `set_context`/`set_tag`, never variables in the
message string.

---

## Complexity headroom (measured in RESEARCH.md — planner must EXTRACT, not inline)

| Function | Current | Effective cap | Headroom | Consequence |
|---|---|---|---|---|
| `ImportPage` (`src/pages/Import.tsx:258`) | **29** | 29 (baselined `eslint.config.js:166-172`) | **0** | The guest branch must LEAVE this file (`ImportGuestPromoBubble`), taking it 29 → 28. Any new `&&`/`?:`/`??` inside `ImportPage` fails CI. |
| `TrainScoreScreen` (`TrainScoreScreen.tsx:142`) | **13** | 15 (not baselined) | **2** | Guest logic goes into `scoreBubbleCopy` (pure) + `SignupAskActions`; pass `isGuest`/`hasGames` as props (0 cost). |
| `scoreBubbleCopy` (`trainBotCopy.ts:680`) | 4 | 15 | ample | Home for the whole copy branch. |
| `HomePage` (`Home.tsx:752`) | 12 | 15 | phase removes a branch → 11 | — |
| `TrainPage` (`Train.tsx`) | — | 24 (baselined) | phase only removes a branch | do not refactor |
| `TrainScoreScreen` max-statements | 20 | 100 | ample | — |

A NEW breach must be fixed, not baselined (frontend/CLAUDE.md:10).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `reports/growth/guest-activation-baseline-2026-09-XX.md` | doc | — | The one sibling report commits no SQL; the SQL-bearing structure is new (use RESEARCH Finding I/J drafts). |
| `/welcome` four-delta rewrite | page | static | No existing "delta list" page in the app; `Welcome.tsx`'s current 10-row comparison table is the thing being dropped. Use the `EmptyState`/`Alert` + single primary `Button` idiom. |

## Metadata

**Analog search scope:** `frontend/src/{components,pages,lib,hooks}`, `app/{routers,services,repositories,models}`, `tests/`, `reports/growth/`
**Files scanned:** ~30 read or grepped; 12 read in full or in targeted ranges
**Tracked-source gate:** every analog path confirmed via `git ls-files`
**Pattern extraction date:** 2026-09-17
