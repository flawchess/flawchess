# Phase 255: Feature Discovery Dot Route - Research

**Researched:** 2026-11-15
**Domain:** Frontend onboarding/announcement state (React 19 + TanStack Query) backed by a server-side per-user JSONB state object (FastAPI + SQLAlchemy async + Postgres)
**Confidence:** HIGH (everything below is grounded in files read this session; no new libraries)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked before the discussion
- **D-01:** Dot only. No "What's New" panel and no static "New" pills (owner, 2026-11-09).
- **D-02:** One route dot at a time (owner, 2026-11-09). The Train count badge is the one exception, see D-17.
- **D-03:** Path problem: one logical step is drawn in two places. The dot shows on the nav item while the user
  is elsewhere, and on the subtab or control once the user is in that section (owner, 2026-11-09).
- **D-04:** Completion is stored server-side and follows the user across devices (owner, 2026-11-15).
  — **Reversibility:** costly — moving back to localStorage would drop every user's stored route state.
- **D-05:** Dots only on important features, to avoid dot fatigue (owner, 2026-11-15). Adding a step is a
  deliberate choice, not a default for every tab.

#### Route contents and order
- **D-06:** The route, in this order:
  0. Import (Library, Import subtab)
  1. Train
  2. Bots
  3. Openings
  4. Played-as control (Openings sidebar)
  5. Filters control (Openings sidebar)
  6. Openings Stats subtab
  7. Endgames
  8. Library Stats subtab
- **D-07:** The Openings sidebar chain is folded into the route: played-as and filters become route steps. The
  bookmarks dot is removed and not replaced.
- **D-08:** Not steps: Library Flaws, Endgames Games, Analysis.
- **D-09:** The Train blunder-check tab is not a step in this phase. It is added when it leaves beta. Adding a
  step later must be a small registry change (one entry: ID, target path, completion rule, position).

#### Ignored steps
- **D-10:** A step the user does not act on auto-skips after 3 active days with the dot on it, then the dot
  moves to the next step. Extract the 3 as a named constant.
- **D-11:** "Active days" should come from `user_activity` (one row per user per active day) where possible,
  so no extra write is needed each time the dot is shown (owner suggestion).
- **D-12:** A new step added later is placed in the route like any other step. There is no queue-jumping for
  new features: a user with earlier open steps reaches the new one after those are done or skipped.

#### Completion and existing users
- **D-13:** A page or subtab step is done when the page or subtab is opened (Import, Bots, Openings,
  Openings Stats, Endgames, Library Stats). A control step is done when the control is used (played-as,
  filters, and Train per D-21).
- **D-21:** The Train step uses the "used" rule (owner, 2026-11-15, during planning). It is done when the user
  clicks the start-training-session button of the personalized puzzle training on Train, Today. Opening Train
  does not complete it. Per D-03 the dot sits on the Train nav item while the user is elsewhere and on the
  start button once the user is on Train, Today. This changes today's behaviour (Train currently clears on
  visit). The same rule shape is the model for a later blunder-check step in Today (D-09): a step inside a page
  the user has already opened needs its own ID and a "used" completion rule.
  *(Owner correction relayed by the coordinator, 2026-11-15: the start button can always be used, because users
  without imported games get a warmup session. The Train step is never a locked target and its 3-day clock
  never pauses.)*
- **D-22:** D-16 must be stored as an explicit set of step IDs per existing user, not as a "whole route done"
  cutoff on `users.created_at`. Otherwise a step added later would already count as done for existing users
  and could never announce a new feature.
- **D-14:** The Import step is done when the Library Import subtab is visited, not when games exist. Some
  users have no chess.com or lichess account and must not be stuck on it. The Import subtab is the landing
  page for an account without games, so this step normally clears on the first session.
- **D-15:** Every completion is recorded from launch on, whether or not the dot is on that step. The dot never
  points at a page the user has already opened since launch.
- **D-16:** Existing users (everyone who signed up before launch, guests included) start with the whole route
  done. The route only walks new signups. Existing users see a dot again only when a new step is added later.
  No migration of the old localStorage flags is needed.

#### Scope edges
- **D-17:** The Train waiting-count badge replaces the dot on Train when both apply, as today. When the route
  is on another step, the badge on Train and the dot elsewhere can both be visible.
- **D-18:** The Library "import your games" dot becomes step 0 of the route, handled by the same arbiter and
  stored server-side like the other steps.
- **D-19:** Guests get the same route. Completion lives on the guest's user row and carries over on
  registration.
- **D-20:** Sticky subnav is out of scope. The subtab dot is visible at the top of the page on arrival.

### Claude's Discretion
- Storage shape. `users.prompt_state` (JSONB, written only by atomic guarded UPDATEs) is the natural
  candidate; a separate table is acceptable if research finds a reason. Completion must be a set of step IDs
  (with done or skipped status), never an index.
- How "the step became current" is timestamped for D-10 and D-11.
- How D-16 identifies existing users (a launch cutoff on `users.created_at`, or a data migration that writes
  the full set). *(Narrowed by D-22: data migration writing the explicit set.)*
- Locked targets. Openings, Endgames and Library Stats need imported games (`isNavLocked`). After D-14, an
  account without games can reach step 3 with a locked target. Suggested handling: no dot on a locked nav
  item, and the 3-day clock does not run while the current step's target is locked. This was not asked
  explicitly; raise it in the plan check if another handling looks better.
- Dot geometry on subtabs and on the sidebar controls, and the mobile path for the played-as and filters
  steps (they sit in a drawer on mobile).
- Whether the old localStorage keys are cleaned up or just left unread.
- Umami events for measuring the effect, if cheap.

### Deferred Ideas (OUT OF SCOPE)
- Blunder-check tab as a route step, when it leaves beta (D-09).
- Sticky subnav, inactive-tab affordance, tab renaming, in-content teaser links, post-import bubble links:
  all remain in SEED-199.
- "What's New" panel and "New" pills: rejected for now (D-01).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs are mapped. The requirement set is D-01..D-22.

| ID | Description (short) | Research Support |
|----|---------------------|------------------|
| D-02/D-03 | One dot, drawn on nav item or on subtab/control | Placement resolver (Pattern 2), slot inventory (Dot slot map) |
| D-04/D-19 | Server-side, guests included, carries over | `users.prompt_state` key, guest promotion is in place (Storage) |
| D-06/D-09/D-21 | Ordered registry, one-entry additions, "used" steps | Registry shape (Pattern 1), Train start button map |
| D-10/D-11 | 3-active-day auto-skip without per-render writes | `current.since_days` stamp + existing `active_days` (Pattern 4) |
| D-12 | No queue-jumping | Arbiter = first unresolved, available step in registry order *(superseded by D-23: the first unresolved step; no dot and no later step while it is locked)* |
| D-13/D-14/D-15 | Visit vs used completion, record always | Recorder in `ProtectedLayout` + control handlers (Pattern 5) |
| D-16/D-22 | Existing users seeded with explicit set | Data migration (Pattern 6) |
| D-17 | Badge replaces Train nav dot | `NavIndicator` precedence kept |
| D-18 | Library import dot becomes step 0 | `import` step replaces `noGames` dot |
| D-20 | No sticky subnav | Subtab dot sits on existing (non-sticky) tab triggers |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend layout: `routers/` HTTP only, `services/` logic, `repositories/` DB access; router `APIRouter(prefix="/users", ...)` with relative paths (the new endpoint goes on the existing users router as `/me/feature-route`).
- Never bare `str` for a fixed set of values: `Literal[...]` in schemas and service/repository params; TS mirrors as string-literal unions.
- No magic numbers: the 3 is `FEATURE_ROUTE_SKIP_ACTIVE_DAYS` (D-10).
- DB rules: FKs mandatory, avoid native ENUM, TEXT+CHECK or SMALLINT+CHECK. `users.prompt_state` is the documented exception (shape validated by Pydantic, not a DB CHECK; see the migration docstring quoted below).
- Time-dependent endpoints take `now_utc` from `dev_now_utc`, never `datetime.now()`.
- Sentry: `capture_exception` in non-trivial `except` blocks in services/routers; no variables in messages; context via `set_context`.
- Never `asyncio.gather` on one `AsyncSession`.
- `ty check` zero errors; explicit return types; `# ty: ignore[rule]` only with reason.
- Nesting depth <= 4 (backend gate script, frontend eslint `max-depth`).
- Frontend: `data-testid` on interactive elements and dots (kebab, component-prefixed), theme constants in `theme.ts`, `text-sm` floor, desktop and mobile changes together, knip must stay clean (delete dead exports), `npm run build` for type changes.
- Umami: `trackFeature` registry only, never from an effect on a value, skip what the URL or DB already says.
- Migrations: `bin/reset_db.sh` must never be in a plan; migrations run at container startup.
- Pre-merge gate (ruff format, ruff check, ty, function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip) before squash-merge; CHANGELOG `[Unreleased]` bullet.
- GSD scope: no unplanned features. Do not propose a What's New panel, pills, sticky subnav or tab renames.

## Summary

Four dot systems exist today and they share nothing: the nav dots in `App.tsx` (`useNavIndicators`, localStorage flags via `useUserFlag`), the Library "no games" dot (pure `noGames` derivation, also duplicated in the More drawer), the Openings sidebar chain (raw unscoped localStorage keys in `useSidebarState`) and the re-minted `train_bots_visited` flag. Every dot is a hand-copied `<span>` pair with `bg-red-500` + `animate-ping` in five files. None of the nav/sidebar dots has a test except the Train and Library dots in `App.test.tsx`.

The backend already has the exact building blocks this phase needs, built for the Phase 234 feedback ask: `users.prompt_state` (NOT NULL JSONB, default `'{}'`, "one JSON object keyed by ask id"), a repository whose every transition is one CAST-typed guarded `UPDATE ... RETURNING`, a Pydantic model validating the stored shape, a today-inclusive `active_days` count from `user_activity` that is already computed on every profile GET and returned as `profile.active_days`, an impersonation no-op convention, and a frontend `useFeedbackAsk` mutation that patches the profile cache. The route copies this pattern almost line for line under a new key `feature_route`, with three actions (`current`, `done`, `skip`) instead of `view`/`snooze`/`done`. The profile already loads `user.prompt_state` with the auth user, so exposing route state on the profile costs zero extra queries, and D-11 is satisfied: the only writes are one per step transition, never per render.

**Primary recommendation:** Store route state in `users.prompt_state["feature_route"]` as `{steps: {<id>: {status, date, with_dot}}, current: {step, since_days}}`; serve it on `GET/PUT /users/me/profile`; write it only through `POST /users/me/feature-route {action, step}`; seed existing users with a data-only Alembic migration that writes the 9 launch IDs; put the ordered registry and a pure placement resolver in `frontend/src/lib/featureRoute.ts`, consumed by a read-only `useRouteDot(slot)` hook at every render site and one recorder component in `ProtectedLayout`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Route order, targets, completion rules (registry) | Browser / Client | — | Placement depends on pathname, lock state (`useReadiness` tier1) and page-local controls, all client concepts; D-09 wants a one-entry change |
| Picking the current step + dot placement (arbiter) | Browser / Client | — | Pure function of registry + stored state + pathname + `navUnlocked`; same answer on every surface (pattern of today's `useNavIndicators`) |
| Persisting done/skipped set and the `current` stamp | API / Backend | Database | D-04; atomic guarded UPDATEs on `users.prompt_state` |
| Active-day count for D-10 | API / Backend | Database (`user_activity`) | Already computed server-side (`profile.active_days`); server re-derives on `skip` so the client cannot fake it |
| Validating step IDs and actions | API / Backend | — | System boundary: `Literal` + `extra="forbid"` |
| Seeding existing users (D-16/D-22) | Database (Alembic data migration) | — | Runs at container start, exactly at deploy time |
| Visit completion recording | Browser / Client (ProtectedLayout effect) | API | Only the client knows the pathname; replaces today's `setUserFlag` effects |
| "Used" completion (played-as, filters, Train start) | Browser / Client (event handlers) | API | The handlers that already dismiss the hints / enter the loop |

## Standard Stack

No new libraries. Everything uses what the repo already has.

### Core (in repo, versions from CLAUDE.md)
| Library | Purpose | Why |
|---------|---------|-----|
| FastAPI 0.141.x + Pydantic v2 | `POST /users/me/feature-route`, schemas | Existing users router |
| SQLAlchemy 2.x async + asyncpg, raw `text()` transitions | Guarded JSONB UPDATEs | Exact precedent in `feedback_ask_repository.py` |
| Alembic | Data-only seed migration | Runs in `deploy/entrypoint.sh` |
| TanStack Query (`useMutation`, `setQueryData`) | Optimistic cache patch of `profile.feature_route` | Precedent `useFeedbackAsk.ts` |
| react-router (`useLocation`) | Pathname for placement and visit completion | Already used by nav |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `users.prompt_state["feature_route"]` | New table `user_route_steps(user_id FK, step_id TEXT CHECK, status TEXT CHECK, ...)` | Relational and analytics-friendly, but every new step needs a migration to widen the CHECK (fights D-09), the `current` stamp needs a second home, and the profile GET needs an extra query. Rejected. |
| Client-driven `current` stamp | Server computes current step on GET and stamps lazily | Server would need the registry order and the client-only lock rule (`tier1` from `/imports/readiness`); writes inside a GET. Rejected. |
| Data migration seed (D-22) | `users.created_at` launch cutoff | Ruled out by D-22. |
| Backend `Literal` step IDs | Pattern-validated free string | Literal follows CLAUDE.md; costs one extra line per new step (see Pitfall 7). |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase. Nothing to audit.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Existing Code Map (what the planner must touch)

### 1. Nav dots, badge and lock in `frontend/src/App.tsx` [VERIFIED: frontend/src/App.tsx, read this session]

| Lines | Symbol | Notes |
|-------|--------|-------|
| 46 | `import { useUserFlag, setUserFlag } from '@/hooks/useUserFlag';` | Goes away |
| 71-76 | `FLAG_OPENINGS_VISITED = 'openings_visited'`, `FLAG_ENDGAMES_VISITED = 'endgames_visited'`, `FLAG_TRAIN_BOTS_VISITED = 'train_bots_visited'` | Remove |
| 107-124 | `NAV_ITEMS` (`'/library'`, `'/train'`, `'/bots'`, `'/openings'`, `'/endgames'`, `'/analysis'`) and `BOTTOM_NAV_ITEMS` (same minus `/analysis`) | Comment at 98-106 forbids unifying them; keep |
| 168 | `const IMPORT_EXEMPT_ROUTES: ReadonlySet<string> = new Set(['/library', '/admin', '/bots', '/analysis', '/activity', '/train']);` | Train and Bots are never locked |
| 170-172 | `function isNavLocked(to: string, navUnlocked: boolean): boolean { return !IMPORT_EXEMPT_ROUTES.has(to) && !navUnlocked; }` | Reuse for route availability |
| 176-184 | `isActive(to, pathname)` (startsWith per section) | Reuse for "in section" |
| 188-236 | `NavIndicators` + `useNavIndicators()`; `const navUnlocked = importedGameCount > 0 && tier1;` (209); `showOpeningsDot`, `showEndgamesDot` (gated on openings visit, 216), Train badge from `useTrainProgress` (221-231), `showTrainDot = navUnlocked && !trainBotsVisited && !showTrainBadge` (234) | Replace flag logic with the arbiter; keep the badge block untouched |
| 238-249 | `NavDot({ testid, mobile, ariaHidden })`: mobile `'absolute top-1.5 right-[30%] flex h-2 w-2'`, desktop `'absolute top-0.5 right-0.5 flex h-2.5 w-2.5'` | Becomes the shared `RouteDot` |
| 251-284 | `TrainBadge` (`train-notification-badge`, `train-notification-badge-mobile`) | Keep as is |
| 288-302 | `NavIndicator`: library dot when `noGames` (aria-hidden), openings/endgames dots, Train: badge first, then dot | Rewrite branches to ask the arbiter; badge precedence stays (D-17) |
| 347, 569 | `<NavIndicator ... mobile={false} />` in `NavHeader`, `<NavIndicator ... mobile />` in `MobileBottomBar` | Call sites |
| 604-609 | `MobileMoreDrawer` re-derives `noGames` and `navUnlocked` ("Same unlock rule as useNavIndicators") | Extract one `useNavUnlocked()` hook; the arbiter needs it too |
| 649-658 | Drawer-only library dot `library-notification-dot-drawer` (hand-copied span) | Replace with route dot for whichever drawer item carries it |
| 750-766 | Three `useEffect`s in `ProtectedLayout` calling `setUserFlag` on `/openings`, `/endgames`, `/train` | Replace with the route recorder (visit completion + `current` stamp) |

### 2. Openings sidebar chain [VERIFIED: files read this session]

- `frontend/src/pages/openings/useSidebarState.ts:30-46`: `localStorage.getItem('played-as-hint-dismissed') === 'true'`, `localStorage.getItem('filters-hint-dismissed') === 'true'`, `dismissPlayedAsHint`, `setFiltersHintDismissed`. Raw keys, not per user. Remove the hint half of this hook (keep panel/drawer state, lines 25-28).
- `frontend/src/pages/Openings.tsx:154-159`:
  ```ts
  const showPlayedAsHint = hasGames && !sidebar.playedAsHintDismissed;
  const showFiltersHint = hasGames && sidebar.playedAsHintDismissed && !sidebar.filtersHintDismissed;
  const showBookmarksHint =
    hasGames && sidebar.playedAsHintDismissed && sidebar.filtersHintDismissed && bookmarks.length === 0;
  ```
  Replace with `useRouteDot('control:openings-played-as')` and `useRouteDot('control:openings-filters')`; delete `showBookmarksHint` (D-07).
- Played-as "used" sites (each calls `sidebar.dismissPlayedAsHint()`): 144 (`handleStatsColorChange`, the Stats colour switch, desktop and mobile), 605 (desktop strip `onToggleColor`), 751 (mobile `onTogglePlayedAs`). These become `recordStep('openings-played-as')`.
- Filters "used" sites (`sidebar.setFiltersHintDismissed(true)`): 263 (`handleDesktopFiltersApply`), 361 (`handleMobileFiltersApply`). Apply counts even without a change (today's behaviour, D-13 "matches today").
- `mobileFiltersDot` at 509-531: red dot wins over the brown "filters modified" dot (`filters-modified-dot-mobile`). Keep that precedence.
- Mobile Stats sticky row 708-724: `OpeningColorSwitch idPrefix="mobile"` (710) and the Filters button `subnav-filter-button` (711-722, already `relative`, renders `{mobileFiltersDot}`).
- `frontend/src/pages/openings/OpeningsDesktopSidebar.tsx`: filters dot 73-89 (`filters-notification-dot`, passed as `notificationDot` to `SidebarLayout`, which renders it inside the strip button at `SidebarLayout.tsx:111-112`), bookmarks dot 91-96 + 190 (remove), played-as dot 220-225 (`played-as-notification-dot` inside `sidebar-strip-btn-color`, button already `relative`). Props `showFiltersHint` (23), `showBookmarksHint` (33), `showPlayedAsHint` (42).
- `frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx`: renders only on Moves/Games (`if (activeTab !== 'explorer' && activeTab !== 'games') return null;`, line 89). Filters slot `{filtersNotificationDot}` at 135 in `subnav-filter-button`; played-as dot 148-156 (`played-as-notification-dot-mobile` in `btn-toggle-played-as`); bookmarks dot 169-177 (`bookmarks-notification-dot-mobile`, remove). Props 37-39.

### 3. Library subtabs [VERIFIED: frontend/src/pages/library/LibraryPage.tsx]

- Default redirect 28-37: `<Navigate to={noGames ? '/library/import' : '/library/games'} replace />` (zero-game accounts land on Import, D-14).
- Desktop `TabsList` 59-76: `tab-import` (60), `tab-games`, `tab-flaws`, `tab-stats` (72). Mobile 109-146: `tab-import-mobile` (114-121), `tab-stats-mobile` (138-145).
- `TabsTrigger` already has `relative` in its base class (`frontend/src/components/ui/tabs.tsx`, the trigger cva starts with `"relative inline-flex h-[calc(100%-1px)] ..."`), so an `absolute` dot child needs no wrapper.
- Library Stats is NOT gated by `isNavLocked` (the `/library` nav is exempt and the subtab is always clickable). The registry needs an explicit `requiresGames` flag for it (CONTEXT treats it as locked without games).

### 4. Openings subtabs [VERIFIED: frontend/src/pages/Openings.tsx]

- Desktop (`lg`+) `TabsTrigger value="stats" data-testid="tab-stats"` at 578-581; mobile `tab-stats-mobile` at 697-700. Note the testid collision with Library's `tab-stats`/`tab-stats-mobile`: dot testids must be section-prefixed (see slot map).
- `activeTab` derivation 89-93; `/openings` redirects to `/openings/explorer` (81, 535-537).

### 5. Train step (D-21) [VERIFIED: files read this session]

- **There is exactly one start button element.** `frontend/src/components/train/TrainStartScreen.tsx:472-481`:
  ```tsx
  <Button
    variant="default"
    className={`${TRAIN_BUTTON_CLASS} w-full`}
    data-testid={state.kind === 'resume' ? 'btn-train-resume' : 'btn-train-start'}
    disabled={isLoading}
    onClick={onEnterLoop}
  >
  ```
  It is rendered as the `action` of `TrainStreakCard` (469-484). Its label (449-452) is `Resume session — X of Y done` or `Start session — N puzzles`.
- **Warmup and regular render the same button.** `LandingState` (115-122) has `'warmup'` and `'fresh'` kinds, and the comment at 123-127 says "'warmup' and 'fresh' (and `resume.isWarmup`) render identically". `resolveLandingState` (145-193) returns `{ kind: 'warmup' }` when `session.is_warmup` (189-191), else `'fresh'`. Both, plus `'resume'`, reach the same `<Button>`; only the testid differs (`btn-train-start` for fresh and warmup, `btn-train-resume` for resume).
- **One click handler funnel.** `onEnterLoop` is passed from `frontend/src/pages/Train.tsx:210` (`onEnterLoop={loop.enterLoop}`), which is `useTrainLoop.ts:217-220`:
  ```ts
  function enterLoop(): void {
    trainSession.markSessionEntered();
    setHasEnteredLoop(true);
  }
  ```
  A repo-wide grep finds no other caller of `enterLoop`/`onEnterLoop`/`markSessionEntered`. So recording `done('train')` in one place covers start, warmup start and resume. Recommended seam: wrap at `Train.tsx:210` (`onEnterLoop={() => { recordStep('train'); loop.enterLoop(); }}`), keeping `useTrainLoop` route-agnostic.
- **Warmup path for zero-game accounts.** `App.tsx:161-162` (IMPORT_EXEMPT_ROUTES doc): "`/train` — every account may train with zero games (composition serves red herrings and filler without game input)". `Train.tsx:127-129`: "No /train/* handler rejects guests, so canTrain only waits for the profile to resolve." `TrainSessionResponse.is_warmup` doc (`app/schemas/train.py`, read this session): "`True` iff the session contains zero surviving SR_ITEM puzzles". Per the owner correction, the Train step is never locked and its clock never pauses; no unavailable state is designed.
- Button-less landing states exist (`loading`, `error`, `empty` = `session_id === null`, `completed` = today's session finished). They need no special route handling: the dot simply has no render site at that moment (the Train nav dot is not shown while the user is on Train, per D-03). For a new user, `completed` implies they already pressed Start (step done).
- **Server-side cross-check already exists:** `POST /train/sessions/{session_id}/enter` stamps `drill_sessions.entered_at` (`app/routers/train.py:256-281`, docstring: "Record that the user pressed Start/Resume on this session"). Useful for measuring the Train step against Postgres; not used as the completion write (one write path for all steps).
- Train subnav: `frontend/src/components/train/TrainSubnav.tsx:56-75`, single `TabsList` for all breakpoints, Today trigger `tab-train-today` (57). Hidden in immersive states (`Train.tsx:175`). Canonical Today path is `TRAIN_TAB_PATHS.today = '/train'` (`frontend/src/lib/trainRoute.ts`), parsed exactly by `parseTrainRoute`.
- Train badge (D-17): stays inside `useNavIndicators` (`App.tsx:221-231`), gated on `navUnlocked && !is_guest`. It only ever replaces the Train **nav** dot. In-section dots (Today subtab, start button) are unaffected by the badge.

### 6. Profile endpoint and types [VERIFIED]

- `app/routers/users.py:81-122` `_build_profile_response` is shared by GET (125-141) and PUT (144-162); its docstring warns "a PUT missing a field would drop it there" (the PUT response replaces the frontend cache). Add `feature_route` here only.
- `app/schemas/users.py:52-86` `UserProfileResponse` ends with `active_days: int` and `feedback_ask: FeedbackAskView`.
- `frontend/src/types/users.ts:33-62` `UserProfile` mirrors it (`active_days: number; feedback_ask: FeedbackAskView;`).
- `frontend/src/hooks/useUserProfile.ts`: `USER_PROFILE_QUERY_KEY = ['userProfile'] as const`, `staleTime: 300_000`, GET `/users/me/profile`. `hasImportedGames(profile)` is "the single definition of the zero-game test".

### 7. Feedback-ask precedent [VERIFIED]

- `app/models/user.py:121-131`:
  ```python
  # One JSON object keyed by ask id (feedback ask = "feedback_v1"). ...
  # Written ONLY by the atomic guarded UPDATEs in
  # app/repositories/feedback_ask_repository.py (never read-modify-write in
  # Python). NOT NULL with a '{}' default, deliberately without none_as_null: a
  # None must fail loudly instead of becoming a JSON null.
  prompt_state: Mapped[dict[str, Any]] = mapped_column(
      JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict
  )
  ```
- Migration docstring `alembic/versions/20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py`: "`users.prompt_state` is one generic JSONB column keyed by ask id ..., so a future ask adds a key, not a migration. ... This is a deliberate exception to the TEXT + CHECK rule: the stored shape is validated per ask by a Pydantic model".
- `app/repositories/feedback_ask_repository.py:1-24` rules to copy verbatim into the new repository: "Every bind is CAST-typed: asyncpg cannot infer the type of an untyped parameter inside `jsonb_build_object` (IndeterminateDatatypeError). Dates travel as ISO strings (`CAST(:today AS text)`)", "Never bind Python `None` into the JSONB (it would write a JSON `null`); every extracted value is wrapped in `coalesce`", "`jsonb_set` is avoided on purpose: it is strict and returns NULL ... `prompt_state || jsonb_build_object` cannot", "Never calls session.commit(); get_async_session commits after a clean request."
- `count_active_days_before(session, *, user_id, today)` at 110-125 counts `user_activity` rows strictly before today; `feedback_ask_service._count_active_days` (93-103) adds 1 for today ("the middleware only writes today's row after the response").
- `feedback_ask_service.build_feedback_ask_snapshot` (110-131) computes `active_days` **before** the guest/impersonation short-circuit (line 115 vs 117), so `profile.active_days` is valid for guests too.
- Impersonation convention: `apply_feedback_ask_action` returns a no-op for `user.is_guest or impersonated` (169-170). The route must keep the impersonation no-op but **must not** copy the guest exclusion (D-19). The feedback SQL guards include `AND NOT is_guest`; do not copy that line.
- `frontend/src/hooks/useFeedbackAsk.ts`: `scope: { id: FEEDBACK_ASK_MUTATION_SCOPE }` serializes calls; `onMutate` cancels in-flight profile queries then patches the cache; `onSuccess` writes the server answer.

### 8. Activity source [VERIFIED: app/middleware/last_activity.py, app/models/user_activity.py]

- `user_activity` has `UniqueConstraint("user_id", "activity_date", name="uq_user_activity_user_date")`. The middleware writes after the response, hour-throttled, with the **real** clock (`now = datetime.now(timezone.utc)`, line 79) and skips impersonated requests and non-2xx (75-76).
- Consequence for dev UAT: the dev clock (`app/core/dev_clock.py:56-78`, honoured only when `ENVIRONMENT == "development"`) shifts `today` but no activity rows are written for shifted days, so time travel alone cannot advance `active_days` by more than 1. Seed `user_activity` rows directly to test the skip (the feedback-ask tests do exactly this, `tests/test_feedback_ask.py:71-74`).

### 9. Guest promotion (D-19) [VERIFIED: app/services/guest_service.py]

Both promotion paths run `sa_update(User).where(User.id == user.id).values(email=..., is_guest=False, ..., promoted_at=func.now())` on the same row (lines 113-131 and the Google twin around 193-197). `prompt_state` is untouched, so route state carries over with no code. `app/routers/auth.py:588`: "The guest is never merged into the existing account" (a guest signing into an existing account keeps that account's own state).

### 10. Old localStorage keys [VERIFIED]

- `frontend/src/hooks/useUserFlag.ts`: `const KEY_PREFIX = 'user_flag:';`, key `` `${KEY_PREFIX}${name}:${email ?? 'anon'}` ``. Only consumer is `App.tsx` (grep). `botGameSnapshot.ts` and `sounds.ts` reference it in comments only.
- Precedent for one-time cleanup: `frontend/src/lib/retiredLocalStorage.ts` (`removeRetiredBookmarkChartKeys`, collects matching keys then removes, swallows storage errors, has a unit test in `src/lib/__tests__/retiredLocalStorage.test.ts`), called from an Openings mount effect (`Openings.tsx:110-114`).

## Architecture Patterns

### System Architecture Diagram

```
                       GET /users/me/profile (existing, staleTime 5 min)
  Postgres users.prompt_state["feature_route"] ──► profile.feature_route + profile.active_days
        ▲                                                   │
        │ guarded UPDATE ... RETURNING                      ▼
  POST /users/me/feature-route            ┌──────── lib/featureRoute.ts (pure) ────────┐
   {action: current|done|skip, step}      │ registry (ordered) + state + ctx           │
        ▲                                 │ ctx = {pathname, navUnlocked, isBeta}      │
        │                                 │  1. candidate = first step not resolved     │
        │                                 │     and available (requiresGames vs lock)  │
        │                                 │  2. expired? active_days - since >= 3      │
        │                                 │  3. slot = nav | subtab | control by path  │
        │                                 └───────────────┬────────────────────────────┘
        │                                                 │ useRouteDot(slotId): boolean
        │                     ┌───────────────┬───────────┼─────────────┬────────────────┐
        │                     ▼               ▼           ▼             ▼                ▼
        │                NavHeader /     Library tabs  Openings tabs  Openings controls  Train Today tab
        │                BottomBar /     (import,      (stats)        (played-as,        + start button
        │                More drawer      stats)                       filters, desktop   (prop into
        │                (badge wins on                                + mobile)          TrainStartScreen)
        │                 Train, D-17)
        │
  FeatureRouteRecorder (in ProtectedLayout) ── visit steps: pathname matches & unresolved ──► done
        │                                   ── candidate != stored current ──► current
        │                                   ── candidate expired ──► skip
  Control handlers (played-as toggle/switch, filters Apply x2, Train enterLoop) ──► done
```

### Recommended file layout

```
app/schemas/feature_route.py               # Literal step IDs, actions, constants, stored-state models
app/repositories/feature_route_repository.py  # 3 guarded UPDATE ... RETURNING statements
app/services/feature_route_service.py      # parse/validate state, route actions, fail closed
app/routers/users.py                       # + POST /me/feature-route, + feature_route in profile
alembic/versions/2026xxxx_..._phase_255_feature_route_seed.py  # data-only seed
frontend/src/types/users.ts                # + FeatureRouteStepId, FeatureRouteState, UserProfile.feature_route
frontend/src/lib/featureRoute.ts           # registry + pure arbiter/placement (unit-tested)
frontend/src/hooks/useFeatureRoute.ts      # useRouteDot(slot) read hook + useNavUnlocked
frontend/src/hooks/useRecordFeatureRoute.ts  # mutation (separate module, see Pitfall 9)
frontend/src/components/featureRoute/RouteDot.tsx  # one dot component, 3 geometries
frontend/src/components/featureRoute/FeatureRouteRecorder.tsx  # effects, mounted in ProtectedLayout
```

### Pattern 1: Registry, one entry per step (D-09, D-21)

**What:** An ordered array; position in the array is the route order. Each entry names its section (nav item), an optional subtab, an optional control slot, how it completes and whether it needs games.

```ts
// frontend/src/lib/featureRoute.ts  (shape; names are recommendations)
export type RouteNav = '/library' | '/train' | '/bots' | '/openings' | '/endgames';
export type RouteControlSlot = 'openings-played-as' | 'openings-filters' | 'train-start';
export type RouteSubtabSlot = 'library-import' | 'library-stats' | 'openings-stats' | 'train-today';

interface RouteStepDef {
  id: FeatureRouteStepId;                 // mirrors the backend Literal
  nav: RouteNav;                          // dot target while outside the section (D-03)
  subtab?: { slot: RouteSubtabSlot; isOn: (pathname: string) => boolean };
  control?: RouteControlSlot;             // "used" steps: dot target on the page
  completion: 'visit' | 'used';           // D-13 / D-21
  visitMatch?: (pathname: string) => boolean;  // required when completion === 'visit'
  requiresGames: boolean;                 // availability (locked-target rule)
}

export const FEATURE_ROUTE: readonly RouteStepDef[] = [
  { id: 'import', nav: '/library', subtab: { slot: 'library-import', isOn: p => p.startsWith('/library/import') },
    completion: 'visit', visitMatch: p => p.startsWith('/library/import'), requiresGames: false },
  { id: 'train', nav: '/train', subtab: { slot: 'train-today', isOn: p => parseTrainRoute(p)?.tab === 'today' },
    control: 'train-start', completion: 'used', requiresGames: false },
  { id: 'bots', nav: '/bots', completion: 'visit', visitMatch: p => p.startsWith('/bots'), requiresGames: false },
  { id: 'openings', nav: '/openings', completion: 'visit', visitMatch: p => p.startsWith('/openings'), requiresGames: true },
  { id: 'openings-played-as', nav: '/openings', control: 'openings-played-as', completion: 'used', requiresGames: true },
  { id: 'openings-filters', nav: '/openings', control: 'openings-filters', completion: 'used', requiresGames: true },
  { id: 'openings-stats', nav: '/openings', subtab: { slot: 'openings-stats', isOn: p => p.startsWith('/openings/stats') },
    completion: 'visit', visitMatch: p => p.startsWith('/openings/stats'), requiresGames: true },
  { id: 'endgames', nav: '/endgames', completion: 'visit', visitMatch: p => p.startsWith('/endgames'), requiresGames: true },
  { id: 'library-stats', nav: '/library', subtab: { slot: 'library-stats', isOn: p => p.startsWith('/library/stats') },
    completion: 'visit', visitMatch: p => p.startsWith('/library/stats'), requiresGames: true },
];
```

Step ID strings above are a recommendation [ASSUMED: naming], kebab-case to match testid and Umami conventions. The future blunder-check step (D-09, D-21) is then one entry, for example `{ id: 'train-blunder-check', nav: '/train', subtab/control: <its slot>, completion: 'used', requiresGames: false }`, plus a `<RouteDot>` at the new control and the new ID in the backend Literal. For a beta-gated target, add an optional `isAvailable?: (ctx) => boolean` field to the entry when that step is added (not needed now; do not build it speculatively). Existing users get the new step automatically: the D-16 seed wrote only the 9 launch IDs, so the new ID is absent and becomes the candidate once their earlier steps are resolved (D-12, D-22).

### Pattern 2: Pure arbiter and placement

```ts
export function resolveRouteDot(state: FeatureRouteState | null, ctx: RouteCtx): RouteDotPlacement | null {
  if (state == null) return null;                       // profile not loaded or corrupt: fail closed, no dot
  const step = FEATURE_ROUTE.find(s => !(s.id in state.steps) && (!s.requiresGames || ctx.navUnlocked));
  if (step == null) return null;
  if (isExpired(step, state, ctx.activeDays)) return null;  // recorder will POST skip; next render moves on
  if (!isInSection(step.nav, ctx.pathname)) return { step: step.id, slot: `nav:${step.nav}` };
  if (step.subtab && !step.subtab.isOn(ctx.pathname)) return { step: step.id, slot: `subtab:${step.subtab.slot}` };
  if (step.control) return { step: step.id, slot: `control:${step.control}` };
  return null;                                           // on a visit step's own page: recorder marks it done
}
```

`isInSection` = today's `isActive(to, pathname)` (move it out of `App.tsx` into the lib so both use one copy). `isExpired` = `state.current?.step === step.id && activeDays - state.current.since_days >= FEATURE_ROUTE_SKIP_ACTIVE_DAYS`. The hook `useRouteDot(slot)` returns `resolveRouteDot(...)?.slot === slot`. Every surface calls the same pure function with the same inputs, which is how `useNavIndicators` already guarantees desktop and mobile agree.

### Pattern 3: Locked targets (discretion item 4)

> **Superseded by D-23 (owner, 2026-11-15): locked steps pause the route.** The candidate is the first unresolved
> step; when its target is locked there is no candidate (no dot, no `current` stamp, no skip) and later steps are not
> considered. The `find` condition in Pattern 2 changes accordingly. The pass-over text below is kept as the record
> of the original recommendation only. How the plans implement the pause, including a step that was already current
> when its target locks again: plan 255-02 (arbiter) and plan 255-04 (clock, assumption A-7).

Original recommendation: the candidate is the first unresolved step **whose target is available**. A locked step (`requiresGames && !navUnlocked`) is passed over without being marked, gets no dot and never gets a `current` stamp, so its clock cannot run. When games arrive, the earlier steps become available again and win by order.

- For the 9 launch steps this is identical to "pause on the locked step": the locked steps (3-8) are contiguous after Bots, and no available step follows them, so a zero-game account simply has no dot after Import/Train/Bots. Train and Bots are import-exempt (`IMPORT_EXEMPT_ROUTES`), and per the owner correction Train is never locked.
- The two rules only diverge for a future step that is available without games and sits after locked ones (for example the blunder-check step). "Pass over" lets a no-games user see it; "pause" never would. This is a D-12 interpretation question: flag it in the plan check. Pass-over needs no extra state; pause would need a stored "locked since" pause interval to stop the clock, which D-11 discourages.
- Edge: if games are deleted (`DELETE /api/games`) the lock returns; a later `current` re-stamp resets that step's clock. Acceptable.

### Pattern 4: The `current` stamp and the 3-active-day skip (D-10, D-11)

- Stored: `current: {step: <id>, since_days: <today-inclusive active_days when it became current>}`.
- The recorder POSTs `current(candidate)` once when the arbiter's candidate differs from `state.current?.step`. Server guard: the step is unresolved and `current.step` differs, so repeated posts (StrictMode, two tabs, two devices) are no-ops and `since_days` never resets by accident.
- Skip rule, shared by client and server: `active_days - since_days >= FEATURE_ROUTE_SKIP_ACTIVE_DAYS` (3). With today-inclusive counting the dot is shown on active days `since`, `since+1`, `since+2`, and moves on the first profile load of the 4th active day. The client uses `profile.active_days` (already served); the server recomputes `active_days` itself in the `skip` transition and enforces the guard in SQL, so a client cannot skip early.
- Writes per user: at most one `current` per step transition, one `done` per step, one `skip` per ignored step. Nothing per render (D-11).
- Why a stamp is unavoidable: deriving "became current" from the previous step's completion date fails for the announcement path, because for existing users the previous steps were resolved by the seed long before the new step shipped, so a new step would auto-skip instantly.

### Pattern 5: Recording completions (D-13, D-15, D-21)

- **Visit steps** (`import`, `bots`, `openings`, `openings-stats`, `endgames`, `library-stats`): one effect in `FeatureRouteRecorder` (mounted in `ProtectedLayout`, replacing `App.tsx:750-766`) posts `done(step)` for every step whose `visitMatch(pathname)` is true and which is not yet in `state.steps`. Independent of the dot (D-15).
- **Used steps:** call `recordStep(id)` from the existing handlers: played-as at `Openings.tsx:144, 605, 751`; filters at `Openings.tsx:263, 361`; Train at the `Train.tsx:210` wrapper. Recording is unconditional on dot visibility (D-15).
- Client guard: skip the POST when the step is already resolved in the cached state, when `profile.feature_route == null`, or when `profile.impersonation != null` (the server also no-ops).
- Mutation (mirror `useFeedbackAsk.ts`): `scope: { id: 'feature-route' }`; `onMutate` cancels profile queries and patches `profile.feature_route` optimistically (done/skip add to `steps`; current sets `{step, since_days: profile.active_days}`); `onSuccess` writes the server's returned state **only if no other feature-route mutation is still pending** (`queryClient.isMutating({ mutationKey: [...] }) <= 1`), otherwise an older response would revert a newer optimistic patch and make the recorder re-post. No Sentry call (global `MutationCache.onError` covers it).

### Pattern 6: Seeding existing users (D-16, D-22)

Data-only Alembic migration (no DDL), the phase's "one small migration":

```python
# Step IDs are hard-coded HERE on purpose: a migration must not import the live registry,
# which will grow later (a later step must stay absent for existing users, D-22).
_LAUNCH_STEP_IDS = ("import", "train", "bots", "openings", "openings-played-as",
                    "openings-filters", "openings-stats", "endgames", "library-stats")

def upgrade() -> None:
    op.execute(sa.text("""
        UPDATE users
        SET prompt_state = prompt_state || jsonb_build_object('feature_route',
            jsonb_build_object('steps', (
                SELECT jsonb_object_agg(step_id, jsonb_build_object(
                    'status', 'done',
                    'date', to_char((now() AT TIME ZONE 'UTC')::date, 'YYYY-MM-DD'),
                    'with_dot', false))
                FROM unnest(CAST(:ids AS text[])) AS step_id)))
        WHERE NOT (prompt_state ? 'feature_route')
    """).bindparams(ids=list(_LAUNCH_STEP_IDS)))

def downgrade() -> None:
    op.execute("UPDATE users SET prompt_state = prompt_state - 'feature_route'")
```

- Covers every row in `users`, guests and superusers included (D-16). No `current` key is written (absent, never JSON null).
- Exactly timed: `deploy/entrypoint.sh:5` runs `alembic upgrade head` at container start, so every account existing at deploy is seeded and every account created afterwards starts with `{}` and walks the route. An account created by the old container during the switchover also walks the route, which is correct (it is a new signup).
- Idempotent (`WHERE NOT (prompt_state ? 'feature_route')`); preserves `feedback_v1` (`||` replaces only the `feature_route` key). Downgrade drops real completions too; document that.
- `op.execute(text(...).bindparams(...))` with an array bind is the planner's choice; a literal `ARRAY['import', ...]` in the SQL string is equally fine and avoids bind typing questions [ASSUMED: alembic offline-mode irrelevant here, migrations run online].
- Row count: the users table is small (prior notes mention ~418 users with games in July plus guests) [ASSUMED: exact prod count not queried this session]; one UPDATE rewriting every row is a sub-second operation at that size.
- A future step that should NOT announce to people who already use the feature (for example blunder-check beta users) gets its own targeted seed migration at that time; not needed now.

### Dot slot map (testids)

| Slot | Desktop render site | Mobile render site | Recommended dot testid |
|------|--------------------|--------------------|------------------------|
| `nav:/library` | `NavHeader` link | `MobileBottomBar` link; More drawer item | `library-notification-dot`, `-mobile`, `-drawer` (existing names) |
| `nav:/train` | same | same | `train-notification-dot`, `-mobile`, `-drawer` (badge wins, D-17) |
| `nav:/bots` | same | same | `bots-notification-dot`, `-mobile`, `-drawer` (new) |
| `nav:/openings` | same | same | `openings-notification-dot`, `-mobile`, `-drawer` (existing) |
| `nav:/endgames` | same | same | `endgames-notification-dot`, `-mobile`, `-drawer` (existing) |
| `subtab:library-import` | `tab-import` trigger | `tab-import-mobile` trigger | `library-import-notification-dot`, `-mobile` |
| `subtab:library-stats` | `tab-stats` (Library) | `tab-stats-mobile` (Library) | `library-stats-notification-dot`, `-mobile` |
| `subtab:openings-stats` | `tab-stats` (Openings) | `tab-stats-mobile` (Openings) | `openings-stats-notification-dot`, `-mobile` |
| `subtab:train-today` | `tab-train-today` (one list for all widths) | same element | `train-today-notification-dot` |
| `control:openings-played-as` | `sidebar-strip-btn-color` | Moves/Games: `btn-toggle-played-as`; Stats: wrap `OpeningColorSwitch idPrefix="mobile"` (`Openings.tsx:710`) in a `relative` span | `played-as-notification-dot`, `-mobile` (existing names) |
| `control:openings-filters` | strip Filters button via `SidebarLayout` `notificationDot` | `subnav-filter-button` (settings column on Moves/Games, sticky row on Stats; one shared `mobileFiltersDot`) | `filters-notification-dot`, `-mobile` (existing names) |
| `control:train-start` | `btn-train-start` / `btn-train-resume` (add `relative`) | same element | `train-start-notification-dot` |

Geometry: one `RouteDot` with three variants copied from today's classes: `nav` (`absolute top-0.5 right-0.5 flex h-2.5 w-2.5`), `nav-mobile` (`absolute top-1.5 right-[30%] flex h-2 w-2`), `inline` for subtabs and controls (same as `nav`, which is what all sidebar dots use today). Desktop header is `overflow-hidden`, so keep the non-negative `top-0.5` offset. Move `bg-red-500` into a `theme.ts` constant (theme.ts already exports class constants, for example `TOUR_SPOTLIGHT_CLASS` at line 670), and mark all route dots `aria-hidden` (decorative; today only the Library dot is).

Mobile played-as on the Stats subtab: today there is no played-as dot there (the mobile board panel returns null on Stats). With the route, step 4 can be current while the user is on Openings Stats (they navigated there themselves), so the dot needs a site there or D-02's "one place" leaves it nowhere. Put it on the `OpeningColorSwitch` wrapper; clicking the other colour calls `handleStatsColorChange`, which already records played-as. Note `OpeningColorSwitch.handleClick` returns early when the clicked colour is already selected (`if (color === selected) return;`), so only a real switch counts, same as today.

### Anti-Patterns to Avoid

- **Re-minting keys** (`train_bots_visited` precedent): a new feature is a new step ID, never a new version of an old ID or of the `feature_route` key. Do not name the key `feature_route_v1`.
- **Read-modify-write of `prompt_state` in Python**: always one guarded `UPDATE ... RETURNING`.
- **Copying the feedback-ask guest guard** (`AND NOT is_guest`): guests walk the route (D-19).
- **Importing the frontend/backend registry into the migration**: hard-code the 9 IDs.
- **Per-render writes**: the recorder posts only on transitions and only when the cached state lacks the step.
- **A second unlock rule**: reuse one `useNavUnlocked()` (today `App.tsx:209` and `604-609` duplicate it).
- **Umami event from the recorder effect**: forbidden by frontend/CLAUDE.md (no `trackFeature` from an effect on a value).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic per-user JSON state | ORM read-modify-write, new table | `feedback_ask_repository` pattern on `users.prompt_state` | Concurrency (two tabs) and the asyncpg JSON-null/typing traps are already solved there |
| Active-day count | New counter column or per-render writes | `count_active_days_before(...) + 1` (and `profile.active_days`) | Existing, indexed by `uq_user_activity_user_date` |
| Optimistic profile patch | Ad-hoc state/context | `useMutation` + `setQueryData(USER_PROFILE_QUERY_KEY, ...)` as in `useFeedbackAsk` | Serialization (`scope`) and stale-refetch handling already designed |
| Retired localStorage cleanup | Inline loops | Extend `lib/retiredLocalStorage.ts` | Tested precedent, swallows storage errors correctly |
| Dot markup | Another hand-copied span pair | One `RouteDot` component | Five copies exist today |

## Runtime State Inventory

This phase migrates dot state from localStorage to the server.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `users.prompt_state` gains key `feature_route` (none exists today; verified by reading all `prompt_state` users: only `feedback_ask_repository.py`, `feedback_ask_service.py`, `models/user.py`) | Data migration seeds the 9 launch IDs for all existing rows (D-16/D-22) |
| Live service config | None. No dot state lives in any external service (Umami only records pageviews/events) | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts / client storage | Browser localStorage on every user device: `user_flag:openings_visited:<email>`, `user_flag:endgames_visited:<email>`, `user_flag:train_bots_visited:<email>` (prefix `user_flag:`), `played-as-hint-dismissed`, `filters-hint-dismissed`. Also cached PWA bundles still running old code until refresh | Recommend one-time cleanup: add `removeRetiredDotKeys()` to `lib/retiredLocalStorage.ts` (prefix `user_flag:` plus the two exact keys), call once from the recorder or `ProtectedLayout` mount, unit-test like the existing one. Delete `useUserFlag.ts` (knip fails otherwise, it would have no importers). Old PWA builds keep writing the old keys harmlessly until they update. |

## Common Pitfalls

### Pitfall 1: asyncpg JSON null and untyped binds
**What goes wrong:** Binding Python `None` writes JSON `null` (not SQL NULL); untyped binds inside `jsonb_build_object` raise `IndeterminateDatatypeError`; `jsonb_set` with a NULL value nulls the whole NOT NULL column.
**How to avoid:** Copy the rules in `feedback_ask_repository.py:8-22` verbatim: `CAST(:x AS text|int)` every bind, `coalesce` every extracted value, `prompt_state || jsonb_build_object(...)` only. Never write a `current: null`; omit the key instead.
**Warning signs:** `IndeterminateDatatypeError` in tests; `prompt_state->'feature_route'->'current'` equals `'null'::jsonb`.

### Pitfall 2: `||` is a shallow merge
**What goes wrong:** `prompt_state || jsonb_build_object('feature_route', jsonb_build_object('steps', {new}))` drops all previously stored steps and `current`.
**How to avoid:** Nest the coalesce chain: `coalesce(prompt_state->'feature_route','{}') || jsonb_build_object('steps', coalesce(prompt_state->'feature_route'->'steps','{}') || jsonb_build_object(CAST(:step AS text), ...))`. Test: done(A) then done(B) keeps A; current(X) keeps steps; any transition keeps `feedback_v1`.

### Pitfall 3: Stale `user.prompt_state` after a raw UPDATE
**What goes wrong:** The handler returns `user.prompt_state` (loaded at auth time) after the UPDATE, so the response lacks the write.
**How to avoid:** Return the value from `RETURNING prompt_state->'feature_route'`; on a no-op (no row matched) re-read with a SELECT, like `feedback_ask_repository.get_state`.

### Pitfall 4: Stored state that no longer validates
**What goes wrong:** A strict `dict[FeatureRouteStepId, ...]` model rejects a stored ID once a step is ever retired from the Literal, and the corrupt-state path then hides every dot forever.
**How to avoid:** Request bodies use the strict `Literal`; the stored-state model keys `steps` as `dict[str, FeatureRouteStepRecord]` (tolerant read, records themselves `extra="forbid"`). Treat the Literal as append-only in practice. A genuinely corrupt state: `sentry_sdk.capture_exception` with `set_context("feature_route", {"user_id": ...})`, return `feature_route = None` on the profile (client shows no dot, fail closed, mirroring `_CorruptAskStateError`), and on the write path roll back like `apply_feedback_ask_action` lines 187-194.

### Pitfall 5: Impersonation completing the user's route
**What goes wrong:** An admin impersonating a user visits pages and silently marks steps done or stamps `current`.
**How to avoid:** Service no-ops when the request carries impersonation (`_get_impersonation_context` dependency as on `/me/feedback-ask`); recorder skips when `profile.impersonation != null`. The middleware already skips activity rows for impersonation.

### Pitfall 6: Visit completion firing before the profile (or with partial mocks)
**What goes wrong:** The recorder posts with `feature_route` undefined (profile loading, or one of the 18 test files that mock `useUserProfile` with partial data) and either crashes or posts garbage.
**How to avoid:** Arbiter and recorder treat `profile?.feature_route == null` as "unknown: no dot, no writes". This also keeps existing page tests inert.

### Pitfall 7: Backend/frontend step-ID drift
**What goes wrong:** A step added to the frontend registry but not to the backend `Literal` gets 422 on every `done`, so the dot never clears.
**How to avoid:** Type the frontend registry `id` as the `FeatureRouteStepId` union in `types/users.ts` (the project hand-mirrors Literals there, e.g. `FeedbackAskAction`), add a vitest asserting every registry ID is unique and that the ordered list equals the expected list, and a pytest asserting `typing.get_args(FeatureRouteStepId)` equals the same list. D-09's "one entry" becomes "one registry entry + one Literal member" (plus a `RouteDot` at a new control). Flag to the planner as the honest cost of CLAUDE.md's Literal rule.

### Pitfall 8: Optimistic patch reverted by an older response
**What goes wrong:** `done(import)` and `current(train)` are queued; `done`'s response (without the new `current`) overwrites the optimistic `current`, so the recorder re-posts.
**How to avoid:** Apply `onSuccess` server state only when this is the last pending feature-route mutation (Pattern 5). Server guards make any re-post a harmless no-op anyway.

### Pitfall 9: Tests without QueryClientProvider
**What goes wrong:** `App.test.tsx` renders `NavHeader`/`MobileBottomBar`/`MobileMoreDrawer` with no `QueryClientProvider` and mocks `@/hooks/useUserProfile` with a factory exporting only `useUserProfile`. `TrainStartScreen.test.tsx` also has no provider (comments at its lines 47, 70, 139 say so deliberately). A nav component that calls `useMutation`/`useQueryClient`, or touches `USER_PROFILE_QUERY_KEY` from the mocked module, throws.
**How to avoid:** Keep render sites read-only (`useRouteDot` uses only `useUserProfile`, `useReadiness` via `useNavUnlocked`, `useLocation`, all already mocked in `App.test.tsx`). Put the mutation in its own module used only by the recorder (in `ProtectedLayout`, not rendered by App.test) and by `Openings.tsx`/`Train.tsx` (their tests have providers). Pass the Train start dot into `TrainStartScreen` as a boolean prop from `Train.tsx` instead of calling the hook inside it.

### Pitfall 10: Dev clock cannot advance active days
**What goes wrong:** UAT of the 3-day skip via the dev clock shows nothing, because the middleware writes `user_activity` with the real clock.
**How to avoid:** In pytest, seed `UserActivity` rows and pin `dev_now_utc` (template: `tests/test_feedback_ask.py:41-74`, which pins NOW before the real date so middleware rows fall outside the count). For manual UAT, insert rows into the dev DB (never `bin/reset_db.sh`).

### Pitfall 11: Alembic head moves under the worktree
**What goes wrong:** Phases 252/254 run in parallel; another migration lands on `main` and the phase-255 migration's `down_revision` creates a second head.
**How to avoid:** Current head on `main` is `a7d2c9e1b254` (phase 254). Re-check `uv run alembic heads` right before the squash-merge and rebase `down_revision` if needed.

### Pitfall 12: Full `UserProfile` fixtures break `npm run build`
**What goes wrong:** Adding a required `feature_route` to `UserProfile` breaks typed full fixtures: `src/lib/impersonation.test.ts:6`, `src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx:18`, and `FeedbackAskBubble.test.tsx`'s `makeProfile`. (Fixtures cast with `as UserProfile`/`Partial<UserProfile>` are unaffected.)
**How to avoid:** Add `feature_route` to those fixtures; run `npm run build` (lint and test do not type-check).

### Pitfall 13: Behaviour changes that tests currently pin
Every existing dot assertion lives in `frontend/src/App.test.tsx`, `describe('Train waiting badge')` (672-892):
- 700-702 `localStorage.clear()` and 802-850 seed `user_flag:*` keys: rewrite to set `profileState.feature_route`.
- 802-817 badge wins over Train dot: still valid (D-17), rewrite setup.
- 822-836 "reworked-Train dot shows ... even with the older visited flags set" and 838-850 "gone once train_bots_visited is set": rewrite against route state (Train clears on start, not visit, D-21).
- 852-859 "reworked-Train dot never shows on a locked (zero-game) account": **inverts**. With the route, a zero-game account with `import` done and `train` open shows the Train dot (Train is import-exempt).
- 880-891 "zero-game profile ... still shows library-notification-dot on both surfaces": now true only while `import` is unresolved (D-14/D-18).
No test asserts `openings-`/`endgames-`/`played-as-`/`filters-`/`bookmarks-notification-dot`, so those behaviours get new tests rather than rewrites.

## Code Examples

### Backend schema (shape)

```python
# app/schemas/feature_route.py
FEATURE_ROUTE_KEY: Final = "feature_route"
# D-10: a step with the dot on it auto-skips after this many active days.
FEATURE_ROUTE_SKIP_ACTIVE_DAYS: Final = 3

FeatureRouteStepId = Literal["import", "train", "bots", "openings", "openings-played-as",
                             "openings-filters", "openings-stats", "endgames", "library-stats"]
FeatureRouteAction = Literal["current", "done", "skip"]

class FeatureRouteStepRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["done", "skipped"]
    date: datetime.date          # UTC day resolved (dev_now_utc)
    with_dot: bool               # the step was `current` when resolved (measurement)

class FeatureRouteCurrent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step: str                    # tolerant read, see Pitfall 4
    since_days: int = Field(ge=1)

class FeatureRouteState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    steps: dict[str, FeatureRouteStepRecord] = Field(default_factory=dict)
    current: FeatureRouteCurrent | None = None

class FeatureRouteActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: FeatureRouteAction
    step: FeatureRouteStepId
```

`UserProfileResponse` gains `feature_route: FeatureRouteState | None` (None = corrupt stored state, client shows no dot).

### Guarded transitions (shape, Postgres 18, following the feedback-ask rules)

```sql
-- DONE: absent or skipped -> done (a later visit upgrades a skip; useful for measurement)
UPDATE users SET prompt_state = prompt_state || jsonb_build_object(CAST(:key AS text),
    coalesce(prompt_state->CAST(:key AS text), '{}'::jsonb)
    || jsonb_build_object('steps',
         coalesce(prompt_state->CAST(:key AS text)->'steps', '{}'::jsonb)
         || jsonb_build_object(CAST(:step AS text), jsonb_build_object(
              'status', 'done',
              'date', CAST(:today AS text),
              'with_dot', coalesce(prompt_state->CAST(:key AS text)->'current'->>'step', '')
                          = CAST(:step AS text)))))
WHERE id = :uid
  AND prompt_state->CAST(:key AS text)->'steps'->CAST(:step AS text)->>'status' IS DISTINCT FROM 'done'
RETURNING prompt_state->CAST(:key AS text);

-- CURRENT: only for an unresolved step that is not already current
--   ... SET ... || jsonb_build_object('current', jsonb_build_object('step', CAST(:step AS text),
--                                                                 'since_days', CAST(:active_days AS int)))
--   WHERE id = :uid
--     AND prompt_state->CAST(:key AS text)->'steps'->CAST(:step AS text) IS NULL
--     AND coalesce(prompt_state->CAST(:key AS text)->'current'->>'step', '') <> CAST(:step AS text)

-- SKIP: only the current step, only once its clock has run out
--   WHERE id = :uid
--     AND prompt_state->CAST(:key AS text)->'current'->>'step' = CAST(:step AS text)
--     AND prompt_state->CAST(:key AS text)->'steps'->CAST(:step AS text) IS NULL
--     AND CAST(:active_days AS int)
--         >= (prompt_state->CAST(:key AS text)->'current'->>'since_days')::int + CAST(:skip_days AS int)
```

Service: `apply_feature_route_action(session, user, action, step, *, now_utc, impersonated) -> FeatureRouteState | None`: impersonated -> return parsed current state with no write; compute `active_days` only for `current`/`skip` (one indexed COUNT); run the transition; on no-op re-read. Router: `@router.post("/me/feature-route", response_model=FeatureRouteState)` taking `current_active_user`, `_get_impersonation_context`, `dev_now_utc` exactly like `feedback_ask_action` (`users.py:249-265`). Always 200, idempotent, so stale tabs never produce 4xx in Sentry.

### Frontend read hook

```ts
// frontend/src/hooks/useFeatureRoute.ts
export function useNavUnlocked(): boolean {
  const { data: profile } = useUserProfile();
  const { tier1 } = useReadiness();
  return hasImportedGames(profile) && tier1;   // one copy of App.tsx:209 / 604-609
}

export function useRouteDot(slot: RouteDotSlot): boolean {
  const { data: profile } = useUserProfile();
  const navUnlocked = useNavUnlocked();
  const { pathname } = useLocation();
  const placement = resolveRouteDot(profile?.feature_route ?? null,
    { pathname, navUnlocked, activeDays: profile?.active_days ?? 0 });
  return placement?.slot === slot;
}
```

## Umami / Measurement (discretion item 7)

Recommendation: **no new Umami events.** Every completion, skip, its UTC date and whether the dot pointed at it (`with_dot`) is in Postgres, and frontend/CLAUDE.md says "Track only what the browser knows and the database cannot". Dot rendering is not a user action, so it may not be tracked from an effect anyway. Measure the effect with:
1. Postgres: per new-signup cohort (`users.created_at >= deploy`), share of each step `done` within 7 days, `with_dot` share, `skipped` share; Train cross-check against `drill_sessions.entered_at`.
2. Umami: re-pull SEED-199's reach table (pageviews joined to `users.id` as `distinct_id`) for the same cohort with a fixed 7-day exposure window, before vs after.

## State of the Art (in this repo)

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Per-device localStorage flags per email (`useUserFlag`) | Server-side set of step IDs on `users.prompt_state` | Follows the user across devices (D-04) |
| Re-minted flag key to re-announce (`train_bots_visited`) | Append a new step ID | Announcements without key versioning |
| Openings dot gated on visit, Endgames gated on Openings | One ordered route, locked steps passed over *(superseded by D-23: a locked step pauses the route)* | Endgames no longer depends on Openings being visited first (SEED-199 complaint) |
| Train dot gated on `navUnlocked` | Train dot shown to zero-game accounts too | Matches Train's import exemption and warmup |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Step ID strings (`openings-played-as`, etc.) | Pattern 1, Code Examples | Cosmetic; pick once, never rename (stored in DB) |
| A2 | Prod `users` row count is small (thousands at most), so the seed UPDATE is sub-second | Pattern 6 | If far larger, still a single UPDATE; worst case a few seconds at container start |
| A3 | "Pass over locked steps" is acceptable under D-12 *(superseded by D-23: the owner chose pause)* | Pattern 3 | Only matters for future steps; owner may prefer pause (needs a pause interval) |
| A4 | A visit to a skipped step upgrades it to `done` | Code Examples (DONE guard) | Analytics nuance only; arbiter treats both as resolved |
| A5 | `with_dot` field is worth storing for measurement | Code Examples | Can be dropped without affecting behaviour |
| A6 | The Train warmup session is always composable (session_id never null in practice) | Existing Code Map 5 | Owner-confirmed; if `empty` ever shows, the dot just has no render site that day and the skip clock handles it |

## Open Questions (RESOLVED)

1. **Locked-step rule for future steps (pass over vs pause).** Identical for the 9 launch steps; matters when a games-free step is appended after locked ones. Recommendation: pass over; raise in plan check.
   **RESOLVED:** pause (owner, D-23). When the first unresolved step's target is locked, no dot is shown, the route does not advance to later steps and that step's clock does not run; the dot appears on it once the target unlocks. Implemented by the arbiter in plan 255-02 and the clock in plan 255-04 (assumption A-7 covers a step that was already current when its target locks again). The earlier pass-over answer (assumption A-1) is withdrawn.
2. **Should the More drawer show the route dot?** Today it shows only the Library dot. Recommendation: render the same nav-level dot there (`-drawer` testid) for consistency; it is the same logical place as the bottom-bar item, so D-02 holds.
   **RESOLVED:** render the nav-level route dot in the More drawer with a `-drawer` testid (plan 255-03 Task 1).
3. **Backend Literal vs D-09 "one entry".** Recommendation: accept one extra Literal line per new step, guarded by the paired list tests (Pitfall 7).
   **RESOLVED:** one frontend registry entry plus one backend `Literal` line per step, guarded by paired list tests (pytest in plan 255-01 Task 1, vitest in plan 255-02 Task 2). A step with a new subtab or control slot also extends the slot union and adds a `RouteDot` at the new site.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | frontend build/tests | ✓ | v24.19.0 | — |
| uv | backend | ✓ | 0.10.9 | — |
| Dev Postgres (Docker `flawchess-dev-db-1`) | pytest, migration tests | ✓ (healthy) | 18 per CLAUDE.md | — |

No missing dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend | pytest with `asyncio_mode = "auto"` (pyproject.toml), per-worker cloned Postgres DB |
| Frontend | vitest (`"test": "vitest run"`), jsdom per file (`// @vitest-environment jsdom`) |
| Quick run (backend) | `uv run pytest tests/test_feature_route.py tests/test_migration_255_feature_route_seed.py -x` |
| Quick run (frontend) | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts src/App.test.tsx` |
| Full suite | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Requirements to Test Map
| Req | Behavior | Type | Command / file | Exists? |
|-----|----------|------|----------------|---------|
| D-04/D-19 | New user and new guest have `{}` route; done/current/skip write; guest writes allowed; promotion keeps state | integration | `tests/test_feature_route.py` (template `tests/test_feedback_ask.py`) | ❌ Wave 0 |
| D-10/D-11 | Skip rejected before 3 active days, accepted at `since+3`; `current` repost does not reset `since_days`; profile GET writes nothing | integration (seed `UserActivity`, pin `dev_now_utc`) | `tests/test_feature_route.py` | ❌ |
| D-15 | `done` recorded for a non-current step with `with_dot=false`; current step `with_dot=true`; skipped then done upgrades | integration | same | ❌ |
| Guards | Impersonation no-op; unknown step/action and extra keys 422; requires auth; `feedback_v1` preserved by every transition; concurrent duplicate posts idempotent; corrupt state fails closed (Sentry, no 500) | integration | same | ❌ |
| D-16/D-22 | Migration seeds exactly the 9 IDs for existing rows incl. guests, preserves `feedback_v1`, idempotent, downgrade removes only `feature_route` | migration | `tests/test_migration_255_feature_route_seed.py` (template `tests/test_migration_240_reveal_tour_stage.py`, pick an unused user-id range) | ❌ |
| D-06/D-12 | Arbiter order, first unresolved wins, no queue-jumping, expired step yields no dot | unit (pure) | `frontend/src/lib/__tests__/featureRoute.test.ts` | ❌ |
| D-03 | Placement: nav outside section, subtab in section, control on page, none on a visit target | unit | same | ❌ |
| Locked rule | `requiresGames` steps passed over when `!navUnlocked` *(superseded by D-23: a locked first unresolved step gives no dot and hides later steps)*; Train/Bots never locked | unit | same | ❌ |
| Registry drift | Ordered ID list equals expected list on both sides | unit | vitest above + pytest `get_args` check | ❌ |
| D-17 | Badge replaces Train nav dot; dot elsewhere coexists with badge | component | `frontend/src/App.test.tsx` (rewrite 802-891) | partial (rewrite) |
| D-18/D-14 | Library dot only while `import` unresolved | component | `App.test.tsx` | partial (rewrite) |
| D-21 | Start/Resume click records `train`; visiting `/train` does not; dot on `tab-train-today` from Leaderboard and on the start button on Today | component | `Train.subnav.test.tsx` / `Train.solveLoop.test.tsx` (have providers) + `TrainStartScreen.test.tsx` (prop only) | ❌ |
| D-07/D-13 | Played-as dot on strip/mobile toggle/mobile Stats switch; filters dot on strip and `subnav-filter-button`; Apply records; bookmarks dot gone | component | `src/pages/__tests__/Openings.render.test.tsx` (has provider) | ❌ |
| Subtab dots | Library import/stats and Openings stats dots on desktop and mobile triggers | component | `LibraryPage.reroute.test.tsx` / new file | ❌ |
| Cleanup | Retired keys removed, storage errors swallowed | unit | `src/lib/__tests__/retiredLocalStorage.test.ts` | extend |

### Sampling Rate
- Per task commit: the quick-run files touched by the task.
- Per wave merge: `uv run pytest -n auto -x` and `npm test -- --run`.
- Phase gate: the full CLAUDE.md pre-merge gate (ruff format/check, ty x2, function-size gate, pytest `-n auto -x`, frontend lint/build/test/knip) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_feature_route.py`
- [ ] `tests/test_migration_255_feature_route_seed.py`
- [ ] `frontend/src/lib/__tests__/featureRoute.test.ts`
- [ ] Profile fixtures updated for the new `feature_route` field (Pitfall 12)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (existing FastAPI-Users) | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | User id only from `current_active_user`; no id in body or path; impersonation is a no-op |
| V5 Input Validation | yes | Pydantic `Literal` action and step, `extra="forbid"`; bounded key set prevents JSONB bloat |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Writing another user's route | Elevation | No user id accepted from the client |
| Stuffing `prompt_state` with arbitrary keys | DoS / Tampering | Step is a `Literal`; key name fixed server-side |
| Admin impersonation altering user state | Repudiation | Server no-op + client skip on impersonation |
| SQL injection via step id | Tampering | Bound parameters only (`CAST(:step AS text)`) |

## Sources

### Primary (HIGH confidence, files read this session)
- `frontend/src/App.tsx` (1-800), `frontend/src/App.test.tsx` (1-310, 672-910)
- `frontend/src/pages/Openings.tsx` (1-819), `frontend/src/pages/openings/{useSidebarState.ts, OpeningsDesktopSidebar.tsx, OpeningsMobileBoardPanel.tsx}`
- `frontend/src/pages/library/LibraryPage.tsx`, `frontend/src/components/ui/tabs.tsx`
- `frontend/src/pages/Train.tsx`, `frontend/src/components/train/{TrainStartScreen.tsx, TrainSubnav.tsx}`, `frontend/src/hooks/useTrainLoop.ts` (1-60, 210-240), `frontend/src/lib/trainRoute.ts`
- `frontend/src/hooks/{useUserFlag.ts, useUserProfile.ts, useFeedbackAsk.ts}`, `frontend/src/lib/retiredLocalStorage.ts`, `frontend/src/types/users.ts`
- `app/models/{user.py, user_activity.py}`, `app/repositories/feedback_ask_repository.py`, `app/schemas/feedback_ask.py`, `app/services/feedback_ask_service.py`, `app/routers/users.py`, `app/schemas/users.py` (52-112), `app/middleware/last_activity.py`, `app/core/dev_clock.py`, `app/services/guest_service.py` (100-135), `app/routers/train.py` (250-281), `app/schemas/train.py` (140-175)
- `alembic/versions/20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py`, `deploy/entrypoint.sh`
- `tests/test_feedback_ask.py` (1-90), `tests/test_migration_240_reveal_tour_stage.py` (1-80)
- `.planning/phases/255-.../255-CONTEXT.md`, `255-DISCUSSION-LOG.md`, seeds SEED-261115-d0t and SEED-199, `CLAUDE.md`, `frontend/CLAUDE.md`

### Secondary / Tertiary
- None. No web or library-doc lookups were needed (no new dependencies; all mechanisms are in-repo).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new dependencies; every mechanism has an in-repo precedent)
- Architecture: HIGH for storage/endpoint/recorder (direct precedent); MEDIUM for the locked-step rule (owner interpretation of D-12)
- Pitfalls: HIGH (each traced to a specific file or test)

**Research date:** 2026-11-15
**Valid until:** 2026-12-15, or earlier if `App.tsx` nav, the Openings sidebar or the Train landing are refactored by another phase
