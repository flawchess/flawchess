# Phase 234: Milestone Feedback Ask (SEED-191) - Research

**Researched:** 2026-10-05
**Domain:** Full-stack feature (FastAPI + SQLAlchemy JSONB state machine, React bubble integrations on three surfaces)
**Confidence:** HIGH (every load-bearing claim was read in code this session; the atomic SQL and the asyncpg typing pitfall were executed against the dev Postgres 18)

## Summary

Small-medium phase, no new dependencies. The backend needs one migration (`users.prompt_state JSONB NOT NULL DEFAULT '{}'`, `feedback.source TEXT NOT NULL DEFAULT 'floating_button'` + CHECK), two cheap per-profile reads (count of `user_activity` rows, EXISTS on `feedback`), a pure eligibility function, and one POST endpoint whose three actions (`view`, `snooze`, `done`) are each a single guarded `UPDATE users SET prompt_state = prompt_state || jsonb_build_object('feedback_v1', ...) WHERE ... RETURNING`. I ran the full transition set (first view, repeat view, once-per-UTC-day no-op, 3rd view auto-snooze, round-2 start after +10 active days, exhausted, done, unrelated key preserved) against a temp table in the dev DB, and it behaves as specified (see Code Examples).

The frontend work is one shared `FeedbackAskBubble` (Hilda, `wall-1800`, rendered through the existing `TrainBotBubble`) dropped into three surfaces that already own a `useUserProfile()` read: `Import.tsx` (replaces the `ImportBotBubble`), `TrainHeader` (replaces the rotating host and suppresses the reminder ask; removes `max-sm:hidden` while active), and `PersonaGrid`/`BotWelcomeCard` (prop-drilled from `Bots.tsx`, because `PersonaGrid` deliberately never calls `useQuery`). Three traps decide whether this works. (1) `FeedbackModal` must NOT live inside the bubble. The profile refetches (Import polls it every 3s during imports, and `refetchOnWindowFocus` is on), so once "Sure!" marks the ask done, the bubble unmounts and takes a modal-in-progress with it. Mount one app-level modal host instead. (2) `PUT /users/me/profile` builds its own `UserProfileResponse`, and the leaderboard toggle writes that response straight into the profile cache. If the new fields are added only to GET, the ask flickers off. (3) asyncpg cannot infer the type of untyped bind params inside `jsonb_build_object` (verified failure below), so every param in the transition SQL needs a `CAST` or a typed `bindparam`.

The seed's copy, "You've been with FlawChess for 5 days now", is wrong for most users at launch: 98 users are already eligible, many with far more than 5 active days, and every round-2 re-ask lands at 15+ days. This needs an owner decision before UI work (Open Question 1).

**Primary recommendation:** Build the state machine as three guarded single-statement UPDATEs in one repository module, with the eligibility logic as a pure Python function sharing named constants with the SQL. Then build one `FeedbackAskBubble` plus an app-level `FeedbackAskModalHost`, and wire the three surfaces last.

<user_constraints>
## User Constraints (from SEED-191 locked decisions + ROADMAP Phase 234; no CONTEXT.md exists)

### Locked Decisions
(Copied verbatim from `.planning/seeds/SEED-191-milestone-feedback-ask.md` "Locked Decisions (from /gsd-explore 2026-10-05)")

1. **Eligibility:** non-guest users with >= 5 distinct `activity_date` rows in `user_activity`. On 2026-10-05: 98 users eligible, 73 of them active in the last 14 days. Feature-agnostic on purpose, so regulars who never train are covered; no separate Train-session condition needed (training counts as activity).
2. **Surfaces (all three, one shared state; whichever the user hits first):**
   - Import page bot bubble: replaces the usual explore copy ("Analyze your games, try a training session, challenge me to a game, or explore your openings and endgames.", `components/import/importBotBubbleCopy.ts` `EXPLORE_PARTS`).
   - Train landing page host bubble (`TrainStartScreen.tsx` `TrainHeader`): Hilda replaces the daily rotating host while the ask is active.
   - Bots roster page welcome bubble (`components/bots/PersonaGrid.tsx` `BotWelcomeCard`, the `rosterHost` daily rotation): Hilda replaces the standard host greeting while the ask is active. The greeting's inline info popover (how the bots work) is hidden for that stretch, which is acceptable since eligible users have 5+ active days. The welcome bubble renders for guests too, but guests are never eligible.
   - NOT the session score screen.
3. **Mobile exception:** on phones the Train landing bubble is normally hidden for returning users (quick 261004-dta, `max-sm:hidden` in `TrainHeader`). Show it anyway while the ask is active, accepting that it pushes the streak card / Start button down.
4. **Persona + copy:** Hilda the Hippo (`personaRegistry.ts`). "You've been with FlawChess for 5 days now, thanks! Got an idea that would make it better for you?" CTAs: **Maybe later** | **Sure!**
5. **"Sure!"** opens `FeedbackModal` with a concrete placeholder (e.g. "What's one thing you'd change or add?") and marks the ask done forever, even if the modal is closed without submitting.
6. **"Maybe later"** immediately dismisses avatar + bubble and snoozes. Re-ask once after +10 more active days, then never again.
7. **Ignored:** a bubble isn't a modal, so ignoring is normal. After 3 views without a click it counts as "Maybe later". (Refined 2026-10-05 after phase promotion.)
   - **A view = at most one per active day (UTC), across all three surfaces.** On a day the ask is active, Hilda shows on every visit to any surface; only the first render that day increments `views` (server compares a stored `last_view_date` inside the same atomic UPDATE). Per-render counting was rejected: Import -> Train -> Bots would burn all 3 views in one minute.
   - A view is reported only when the bubble actually renders, never on profile fetch.
   - Fully ignored: shows on 3 active days, auto-snoozes, re-asks after +10 active days for 3 more days, then never. Max 6 active days of exposure, spread over >= 13.
8. **State: server-side, one generic JSONB column** (decided over localStorage: no cross-device double-ask, and the funnel is queryable in Postgres). `users.prompt_state JSONB NOT NULL DEFAULT '{}'`, keyed by ask id so future asks (e.g. the deferred NPS ask) add a key, not a migration: `{"feedback_v1": {"status": "snoozed", "views": 2, "last_view_date": "2026-10-05", "snoozed_at_days": 6}}`. Lives on `users`, NOT `train_settings`, since non-trainers must be covered.
   - NOT NULL + default avoids the asyncpg trap where Python `None` writes JSON `null` instead of SQL NULL.
   - Deliberate exception to the CLAUDE.md TEXT + CHECK rule: shape is validated by a Pydantic model per ask (`status: Literal["snoozed", "done"]`) on every read/write instead of a DB CHECK.
   - Updates (view increment, snooze, done) are a single atomic SQL `jsonb_set` / `||` UPDATE, never read-modify-write in Python (two open tabs would lose updates).
   - Profile exposes `active_days` (count from `user_activity`) and the ask state; the server decides eligibility. Also never ask a user who has already submitted feedback from any source.
9. **Measure yield:** tag feedback submissions with a source (e.g. `milestone_ask` vs `floating_button`) so the effect is visible in the `feedback` table.
10. **Priority on Train landing:** above the reminder-install ask (that ask shows indefinitely to anyone without a phone push subscription and would otherwise block this one forever). Guest sign-up and zero-game import asks don't conflict (guests and zero-game users aren't eligible anyway).

ROADMAP adds: "one small POST endpoint for view/snooze/done"; "`feedback.source` column (`milestone_ask` vs `floating_button`)".

### Claude's Discretion
No CONTEXT.md, so no explicit discretion list. Implicitly open (the seed doesn't fix these): exact JSONB field set beyond the example, endpoint path and response shape, today-inclusive `active_days`, round-2 copy, component decomposition, Umami event shape, behavior under impersonation, and interaction with Tank's intro host and the Import `welcome` variant. Recommendations for each are below; the ones that change user-visible behavior are listed under Open Questions.

### Deferred Ideas (OUT OF SCOPE)
- "Recommend FlawChess to a friend" via an NPS-style split: 9-10 get a share CTA, everyone else gets a "what would make it better?" box. Revisit when retention past 14 days improves (on 2026-10-05 only 5 users had 14+ Train days); referrals before retention mostly import churn.
- Re-enabling the floating feedback button on mobile (e.g. as a menu entry instead of a floating button).
</user_constraints>

<phase_requirements>
## Phase Requirements (proposed; no IDs are mapped in REQUIREMENTS.md)

No requirement IDs are mapped ("Requirements: TBD"). This breakdown is a suggestion for the planner to adopt or rename:

| Proposed ID | Description | Research Support |
|----|-------------|------------------|
| FBASK-01 | Migration: `users.prompt_state` JSONB NOT NULL DEFAULT `'{}'`; `feedback.source` TEXT NOT NULL DEFAULT `'floating_button'` + CHECK | Migration section, Pitfall 6 |
| FBASK-02 | Profile (GET **and** PUT) exposes `active_days` and a server-computed `feedback_ask` view (`active`, `round`) | Pattern 2, Pitfall 2 |
| FBASK-03 | Eligibility: non-guest, >= 5 active days, no feedback row from any source, ask state allows it | Pattern 1 (`resolve_feedback_ask`) |
| FBASK-04 | `POST /api/users/me/feedback-ask` with `action: view|snooze|done`, each a single atomic UPDATE; view dedupes per UTC day; 3rd view auto-snoozes; re-ask once after +10 active days | Code Examples (verified SQL) |
| FBASK-05 | `FeedbackCreate.source` Literal, persisted; FeedbackModal accepts placeholder + source | Pattern 4 |
| FBASK-06 | Shared Hilda `FeedbackAskBubble` + app-level modal host; view reported on render | Pattern 3, Pitfall 1 |
| FBASK-07 | Import surface: ask replaces the explore bubble | Surface map |
| FBASK-08 | Train landing: Hilda replaces the rotating host, suppresses the reminder ask, visible on phones | Surface map |
| FBASK-09 | Bots roster: Hilda replaces the welcome greeting, info popover hidden | Surface map |
| FBASK-10 | Umami `action` targets for the Sure / Maybe-later clicks | Umami section |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Router convention `APIRouter(prefix="/users", tags=["users"])` with relative paths. The new route goes on the existing users router as `/me/feedback-ask`.
- HTTP-only routers: business logic in `services/`, SQL in `repositories/` (no SQL in services).
- FK + `ondelete` on every reference (no new FKs in this phase). TEXT + CHECK for the low-volume `feedback.source` domain column. The `prompt_state` JSONB is a **seed-sanctioned exception** validated by Pydantic.
- `Literal[...]` for every fixed value set (`action`, `status`, `source`, `snoozed_by`), never bare `str`. Use `Sequence` rather than `list` for Literal-list params.
- No magic numbers: `FEEDBACK_ASK_MIN_ACTIVE_DAYS = 5`, `FEEDBACK_ASK_REASK_GAP_DAYS = 10`, `FEEDBACK_ASK_MAX_VIEWS = 3`, `FEEDBACK_ASK_MAX_ROUNDS = 2`, `FEEDBACK_ASK_ID = "feedback_v1"`.
- ty clean (`uv run ty check app/ tests/ scripts/`), explicit return annotations, and `# ty: ignore[rule]` with a reason only where unfixable (e.g. `result.rowcount`, the existing idiom).
- Time-dependent endpoints take `now_utc` from `Depends(dev_now_utc)`, never `datetime.now()`.
- Sentry: `capture_exception` in non-trivial excepts in services/routers. No variables in messages; use `set_context`.
- Never `asyncio.gather` on one AsyncSession. (Concurrency tests must use separate requests or sessions.)
- Nesting depth <= 4 (gated by `scripts/check_function_size.py app/` and eslint `max-depth`).
- Frontend: `data-testid` on every interactive element, `text-sm` minimum, `variant="default"` primary / `variant="brand-outline"` secondary, theme colors from `theme.ts`, `isError` branches on queries, knip clean (remove/avoid dead exports), `npm run build` (tsc) before integrating type changes, no Prettier.
- Umami: register feature events in `analytics.ts`, call `trackFeature` only from user-initiated handlers (never from `useEffect`/mount), enumerated literals only, reuse the `action` verb.
- Pre-merge gate (ruff format/check, ty x2, function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip) before squash-merge. CHANGELOG `[Unreleased]` bullet on merge.
- Plans must not gate on `bin/reset_db.sh` (memory: no dev DB reset in plans).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Active-day counting | Database / Storage | API | Rows already written by `LastActivityMiddleware`. The API counts per request. |
| Eligibility + "is the ask active now" | API / Backend | — | Seed: "the server decides eligibility". Needs `is_guest`, feedback existence, active days, JSONB state. |
| State transitions (view/snooze/done) | Database (atomic UPDATE) | API (guards, validation) | Locked: single atomic SQL UPDATE, never read-modify-write. |
| JSONB shape validation | API (Pydantic) | — | Locked exception to DB CHECK. |
| Feedback source attribution | API (schema Literal) + DB CHECK | Browser (which modal sent it) | Browser knows the entry point; DB enforces the domain. |
| Bubble rendering, view reporting, CTA handling | Browser / Client | — | View only counts when actually rendered (locked). |
| Feedback modal lifecycle | Browser (app-level host) | — | Must survive the bubble unmounting (Pitfall 1). |
| Click analytics | Browser (Umami `trackFeature`) | — | Surface/page of the click isn't DB-known. |

## Current-State Map (verified this session)

### `user_activity` (eligibility input)

- Model: `[VERIFIED: app/models/user_activity.py:23-24,33]`
  ```
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
  activity_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
  UniqueConstraint("user_id", "activity_date", name="uq_user_activity_user_date"),
  ```
  Because `(user_id, activity_date)` is unique, `count(*) WHERE user_id = :u` equals `count(DISTINCT activity_date)` and is served by the leading-`user_id` unique index. Dev: 119 rows, 15 users, max 84 rows per user, 0.23 ms `[VERIFIED: dev DB EXPLAIN ANALYZE]`. The table was created by migration `20260626_074415_c4d4588ed2b8_add_user_activity.py` (forward-only from 2026-06-26), so per-user counts top out around 100 rows. Negligible per-profile cost. Prod row counts weren't queried (subagents lack the prod MCP) `[ASSUMED]`.
- Writer: `LastActivityMiddleware` writes **after the response is sent** and with the **real clock**, skipping errors and impersonation `[VERIFIED: app/middleware/last_activity.py:67,77,81,106-108]`:
  ```
  await self.app(scope, receive, send_wrapper)  # ...
  if status_code is None or status_code >= 400 or user_id is None or is_impersonation:
      now = datetime.now(timezone.utc)
      activity_stmt = pg_insert(UserActivity).values(
          user_id=user_id,
          activity_date=now.date(),
  ```
  Consequence: the first profile fetch of a user's 5th day still counts only 4 rows (Pitfall 3). In dev with a clock offset, no rows are written for shifted days, so testing the "+10 days" path needs seeded rows, not the dev clock.

### Profile endpoint + hook

- `GET /users/me/profile` (`[VERIFIED: app/routers/users.py:78]` `@router.get("/me/profile", response_model=UserProfileResponse)`) already takes `now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)]` (line 83) and the dependency-loaded `user: User` (which carries `is_guest` and will carry `prompt_state`).
- `PUT /users/me/profile` (line 117) **builds a second, independent `UserProfileResponse`** (lines 136-152). Both builders must emit the new fields (Pitfall 2).
- `UserProfileResponse` has `is_guest: bool` `[VERIFIED: app/schemas/users.py:56]`. Guests are `users` rows with `is_guest=True` (`[VERIFIED: app/models/user.py:31]` `is_guest: Mapped[bool] = mapped_column(default=False, server_default=text("false"))`).
- Frontend: `[VERIFIED: frontend/src/hooks/useUserProfile.ts:6,15]` `export const USER_PROFILE_QUERY_KEY = ['userProfile'] as const;` and `staleTime: 300_000, // 5 minutes`. `useSetLeaderboardHidden` does `queryClient.setQueryData(USER_PROFILE_QUERY_KEY, profile)` with the PUT response (line 36). Global default `staleTime: 30_000` `[VERIFIED: frontend/src/lib/queryClient.ts:68]`. `refetchOnWindowFocus` is left at the TanStack default (on) `[ASSUMED: TanStack v5 default]`.
- Type: `interface UserProfile` in `frontend/src/types/users.ts:24-50`.
- Repo-wide rule (frontend memory): read `is_guest` from `useUserProfile().data`, never `useAuth().user`.

### Existing JSONB on `users` (precedent)

`[VERIFIED: app/models/user.py:110-112]`
```
first_touch: Mapped[dict[str, str] | None] = mapped_column(
    JSONB(none_as_null=True), nullable=True, default=None
)
```
Its repository write is a blind conditional UPDATE returning `result.rowcount == 1  # ty: ignore[unresolved-attribute]` `[VERIFIED: app/repositories/user_repository.py:146-156]`. Phase 233's merge helper `[VERIFIED: app/repositories/train_repository.py:2880-2882]`:
```
return func.coalesce(DrillSolve.telemetry, literal({}, JSONB)).op("||", return_type=JSONB)(
    literal(patch, JSONB)
)
```
Phase 233's migration added a nullable JSONB (`postgresql.JSONB(none_as_null=True)`). This phase differs because the locked decision is NOT NULL + server default, so the `coalesce` guard is optional but harmless.

### Feedback (model, router, frontend)

- `[VERIFIED: app/models/feedback.py:14-21]` `user_id ... ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True`, `page_url: Mapped[str] = mapped_column(String(500), nullable=False)`, `text`, `rating`, `created_at`. There is no `source` column. The `ix_feedback_user_id` index exists `[VERIFIED: dev DB \d feedback]`, so `EXISTS(SELECT 1 FROM feedback WHERE user_id=:u)` is an index probe.
- Router `[VERIFIED: app/routers/feedback.py:20,23]` `router = APIRouter(prefix="/feedback", tags=["feedback"])`, `@router.post("", response_model=FeedbackResponse, status_code=201)`. Guests may submit. Rate-limited 5/hour/user (`feedback_limiter`). user_id comes from the JWT.
- Schema `[VERIFIED: app/schemas/feedback.py:39-47]` `FeedbackCreate` fields `text`, `rating`, `page_url`. Add `source: Literal["floating_button", "milestone_ask"] = "floating_button"`. The default keeps stale SPA bundles working during deploy.
- Repository `create_feedback` builds `Feedback(user_id=..., page_url=..., text=..., rating=...)` `[VERIFIED: app/repositories/feedback_repository.py:19-27]`. Add `source=data.source`.
- Sentry: `push_sentry_signal` already does `sentry_sdk.set_tag("source", "feedback")` `[VERIFIED: app/services/feedback_service.py:123]`. **Don't overload that tag.** Put the new value in the `feedback` context dict (e.g. `"ask_source": data.source`) or a distinct tag `feedback_source`.
- Frontend: `FeedbackModal({ open, onOpenChange })`, fixed placeholder `"Tell us what you think about FlawChess or this page in particular"`, posts `{ text, rating, page_url }` via `useFeedback()` `[VERIFIED: frontend/src/components/feedback/FeedbackModal.tsx]`. `FeedbackButton` is desktop-only (`'hidden sm:block'`) and mounted in `App.tsx` at lines 831 and 854 `[VERIFIED: frontend/src/App.tsx:831,854]`, hidden when `playActive`. `FeedbackRequest` lives in `frontend/src/types/feedback.ts`.

### The three surfaces

| Surface | File / anchor | Today | Change |
|---|---|---|---|
| Import | `pages/Import.tsx:143-147` `importBubbleVariant(profile)`; line 449 `{profile && <ImportBotBubble variant={importBubbleVariant(profile)} />}` | Random `pickBot('friendly')` persona (memoized), variants `'welcome' \| 'explore' \| 'signup-ask'` `[VERIFIED: components/import/importBotBubbleCopy.ts:6]` | When `profile.feedback_ask.active`, render `<FeedbackAskBubble surface="import" />` instead of `ImportBotBubble`. Leave `EXPLORE_PARTS` untouched. |
| Train landing | `components/train/TrainStartScreen.tsx` `TrainHeader`: line 237 `!isGuest && !showImportAsk && settings?.has_mobile_subscription === false;`, line 243 `const isIntroHost = settings != null && settings.intro_seen_at == null;`, line 245 `<div className={cn('w-full', !isIntroHost && 'max-sm:hidden')} data-testid="train-landing-host">` | Daily rotating host via `landingHost`; reminder ask paragraph; hidden on phones unless Tank's intro | While active: Hilda bubble (`avatarSize="large"`), no tagline/reminder ask, and the `max-sm:hidden` gate becomes `!isIntroHost && !askActive && 'max-sm:hidden'`. Not rendered in the `empty` landing state (TrainHeader isn't mounted there). |
| Bots roster | `components/bots/PersonaGrid.tsx:77-81` `BotWelcomeCard()` (`rosterHost({ today })`), line 86 `<TrainBotBubble persona={host.persona} state="prompt" avatarSize="large">`, line 93 `<InfoPopover ariaLabel="About the bot opponents" testId="bots-intro-info">` | Always renders, guests included | Add a prop (e.g. `feedbackAskActive: boolean`) passed from `Bots.tsx` (which already has `const { data: profile, isLoading, isError } = useUserProfile();`, `pages/Bots.tsx:591`). When true, render `FeedbackAskBubble` (no popover). **PersonaGrid must stay query-free**: its docstring says it "never calls `useQuery` itself ... which would break its existing no-`QueryClientProvider` render tests". |

- Hilda: `[VERIFIED: frontend/src/lib/personas/personaRegistry.ts:488,495]` `'wall-1800': {` ... `name: 'Hilda the Hippo',`. Avatar asset `frontend/src/assets/personas/wall-1800.webp` exists (`ls`). It's resolved automatically by `resolveAvatarSrc` through the `TrainBotBubble` avatar path. Follow the precedent `[VERIFIED: frontend/src/lib/trainBotCopy.ts:45]` `export const TANK_ID: PersonaId = 'grinder-1600';` and add `export const HILDA_ID: PersonaId = 'wall-1800';`.
- Bubble primitive: `TrainBotBubble({ persona, state, children, actions, avatarSize })`. `actions` renders bottom-right inside the bubble. Phones get the avatar header above the bubble.
- Action-pair precedent: `SignupAskActions` (`brand-outline` secondary first, `default` primary second, `TRAIN_BUTTON_CLASS`, a `source` prop for per-surface testids). Mirror it for `FeedbackAskActions` (Maybe later = `brand-outline`, Sure! = `default`).

## Standard Stack

No new packages. Everything uses what's installed:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.x async + asyncpg | repo lockfile | Atomic JSONB UPDATE ... RETURNING | Project ORM. `text()` with CASTs or Core with typed `literal()` |
| Alembic | repo lockfile | Migration (head is `a7c3e9d41f02` `[VERIFIED: uv run alembic heads]`) | Project standard |
| Pydantic v2 | repo lockfile | `FeedbackAskState` stored-shape model, request/response schemas | Locked: validates the JSONB instead of a DB CHECK |
| @tanstack/react-query | 5.102.8 installed `[VERIFIED: node_modules/@tanstack/react-query/package.json]` | Mutation with `scope: { id }` serialization, profile cache patch | Project standard. `scope` is supported (`mutationCache.ts` `scopeFor` → `mutation.options.scope?.id`) `[VERIFIED: query-core src]` |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase, so the audit isn't applicable. **Packages removed:** none. **Flagged:** none.

## Architecture Patterns

### System Architecture Diagram

```
 browser surface mount (Import | Train landing | Bots roster)
        │  reads cached GET /api/users/me/profile ──► { active_days, feedback_ask: {active, round} }
        │                                                   ▲
        │                                     server: count(user_activity) (+today), EXISTS(feedback),
        │                                             is_guest, prompt_state->'feedback_v1'
        │                                             └─► resolve_feedback_ask() (pure fn)
        ▼
  feedback_ask.active ? ──no──► existing bubble (explore / rotating host / roster greeting)
        │yes
        ▼
  <FeedbackAskBubble surface=…>  (Hilda via TrainBotBubble)
        │ on mount (render) ── POST /me/feedback-ask {action:"view"} ──► UPDATE … WHERE last_view_date <> today
        │                                                                   (no-op if already viewed today;
        │                                                                    3rd view => status snoozed, by "views")
        ├─ "Maybe later" click ─► trackFeature(action, feedback-ask-later) ─► POST {action:"snooze"} ─► cache patch: active=false ─► bubble gone
        └─ "Sure!" click ───────► trackFeature(action, feedback-ask-sure) ──► POST {action:"done"}
                                   └─► openFeedbackAskModal()  ─► app-level <FeedbackAskModalHost>
                                                                     └─► <FeedbackModal source="milestone_ask" placeholder=…>
                                                                          └─► POST /api/feedback {…, source} ─► feedback row (source='milestone_ask')
                                                                               └─► invalidate profile
```

### Recommended Project Structure (new/changed files)
```
app/
├── models/user.py                     # + prompt_state JSONB NOT NULL server_default '{}'
├── models/feedback.py                 # + source TEXT NOT NULL default 'floating_button' + CheckConstraint
├── schemas/feedback_ask.py            # NEW: FeedbackAskState (stored), FeedbackAskView (API), FeedbackAskActionRequest
├── schemas/feedback.py                # + source Literal
├── schemas/users.py                   # UserProfileResponse + active_days, feedback_ask
├── repositories/feedback_ask_repository.py  # NEW: count_active_days, apply_view/snooze/done (atomic SQL)
├── repositories/feedback_repository.py      # + has_feedback(user_id), source on create
├── services/feedback_ask_service.py   # NEW: constants, resolve_feedback_ask() pure fn, action orchestration
├── routers/users.py                   # profile GET/PUT via one shared builder; POST /me/feedback-ask
alembic/versions/2026100X_..._users_prompt_state_feedback_source.py
frontend/src/
├── lib/feedbackAsk.ts                 # HILDA_ID, copy, placeholder, modal open store (useSyncExternalStore)
├── hooks/useFeedbackAsk.ts            # mutation (scope 'feedback-ask'), patches USER_PROFILE_QUERY_KEY
├── components/feedback/FeedbackAskBubble.tsx   # Hilda + FeedbackAskActions + view-on-mount
├── components/feedback/FeedbackAskModalHost.tsx # mounted once in App.tsx (both layout branches)
├── components/feedback/FeedbackModal.tsx        # + placeholder?, source? props
├── hooks/useFeedback.ts               # onSuccess: invalidate USER_PROFILE_QUERY_KEY
├── types/users.ts, types/feedback.ts  # new fields
├── lib/analytics.ts                   # ACTION_TARGETS += 'feedback-ask-sure', 'feedback-ask-later'
├── pages/Import.tsx, pages/Bots.tsx, components/train/TrainStartScreen.tsx, components/bots/PersonaGrid.tsx
```

### Pattern 1: Stored shape + pure eligibility (server-decided)

The seed's example `{"status": "snoozed", "views": 2, "last_view_date": ..., "snoozed_at_days": 6}` is illustrative. Implementing "re-ask once, then never", "3 views count as Maybe later", and "still show for the rest of the day the 3rd view happened" needs `round` and `snoozed_by`. Recommended model (status stays exactly `Literal["snoozed", "done"]`; an absent status means "asking"):

```python
# app/schemas/feedback_ask.py
class FeedbackAskState(BaseModel):
    model_config = ConfigDict(extra="forbid")  # catches a typo'd key from the SQL
    status: Literal["snoozed", "done"] | None = None   # None = currently asking
    round: Literal[1, 2] = 1
    views: int = Field(default=0, ge=0)                # views in the current round
    last_view_date: datetime.date | None = None        # UTC day of the last counted view
    snoozed_at_days: int | None = None                 # active_days when snoozed
    snoozed_by: Literal["click", "views"] | None = None
```

Pure function (unit-testable without DB), the single source of the "active" decision:

```python
def resolve_feedback_ask(state: FeedbackAskState | None, *, active_days: int, has_feedback: bool,
                         is_guest: bool, today: datetime.date) -> bool:
    if is_guest or has_feedback or active_days < FEEDBACK_ASK_MIN_ACTIVE_DAYS:
        return False
    if state is None or state.status is None:
        return True                                    # round 1 (or round 2 in progress)
    if state.status == "done":
        return False
    # snoozed
    if state.snoozed_by == "views" and state.last_view_date == today:
        return True                                    # grace: 3rd-view day keeps showing everywhere
    return (state.round < FEEDBACK_ASK_MAX_ROUNDS and state.snoozed_at_days is not None
            and active_days >= state.snoozed_at_days + FEEDBACK_ASK_REASK_GAP_DAYS)
```

The SQL `WHERE` guards in the repository must mirror this. Use the same Python constants as bind params, never literals in the SQL string.

### Pattern 2: One profile builder for GET and PUT

Extract `async def _build_profile_response(session, user, now_utc, impersonation) -> UserProfileResponse` and have both routes call it. It adds:
- `active_days: int`: `count(*)` from `user_activity` for the user, plus 1 when there's no row for `now_utc.date()` yet (the middleware writes after the response; Pitfall 3). Recommended; it's a discretion call.
- `feedback_ask: FeedbackAskView` with `active: bool` and `round: Literal[1, 2]`. `active=False` for guests and under impersonation (recommended: an admin must not burn a user's views or answer for them).

Read `prompt_state` from the dependency-loaded `user` (fresh per request). Validate with `FeedbackAskState.model_validate(user.prompt_state.get(FEEDBACK_ASK_ID))`. On `ValidationError`, `sentry_sdk.capture_exception`, then treat the ask as **not active** (fail closed: never nag on corrupt state).

### Pattern 3: Shared bubble, view on render, app-level modal

```tsx
// FeedbackAskBubble.tsx (sketch)
export function FeedbackAskBubble({ surface, avatarSize }: Props) {
  const { report } = useFeedbackAsk();             // useMutation({ scope: { id: 'feedback-ask' }, ... })
  useEffect(() => { report('view'); }, [report]);  // API call, NOT Umami: allowed in an effect; server dedupes per UTC day
  return (
    <div data-testid={`feedback-ask-${surface}`}>
      <TrainBotBubble persona={PERSONA_REGISTRY[HILDA_ID]} state="prompt" avatarSize={avatarSize}
        actions={<FeedbackAskActions surface={surface} onLater={...} onSure={...} />}>
        <p data-testid="feedback-ask-copy">{FEEDBACK_ASK_COPY}</p>
      </TrainBotBubble>
    </div>
  );
}
```
- `onSure`: `trackFeature('action', { target: 'feedback-ask-sure' })`, `openFeedbackAskModal()` (store), then `report('done')`. The mutation's `onSuccess` patches the cached profile (`setQueryData(USER_PROFILE_QUERY_KEY, p => p && {...p, feedback_ask: resp})`), and the bubble unmounts. The modal survives because it lives in `FeedbackAskModalHost` in `App.tsx`.
- `onLater`: `trackFeature('action', { target: 'feedback-ask-later' })`, then `report('snooze')`. Patch the cache optimistically (`onMutate`) so the bubble disappears **immediately** (locked: "immediately dismisses").
- React 19 StrictMode double-invokes the mount effect in dev. That's harmless because the server no-ops the second view (same `last_view_date`).
- The `scope` serializes view → snooze/done, so a fast click can't overtake the in-flight view.

### Pattern 4: Feedback source
`FeedbackModal` gains `placeholder?: string` and `source?: FeedbackSource` (default `'floating_button'`), threaded into the mutate payload. The host passes `source="milestone_ask"` and placeholder `"What's one thing you'd change or add?"` (seed example). Optionally swap the `DialogDescription` too. `useFeedback` invalidates `USER_PROFILE_QUERY_KEY` on success, so a floating-button submission also ends the ask (eligibility excludes users with any feedback row).

### Anti-Patterns to Avoid
- **Modal inside the bubble:** it gets unmounted by the profile refetch or the done-patch (Pitfall 1).
- **Python read-modify-write of `prompt_state`:** locked out. Two tabs lose updates.
- **`jsonb_set(prompt_state, '{feedback_v1}', <expr>)` where `<expr>` can be SQL NULL:** `jsonb_set` is strict and returns NULL, which violates NOT NULL (verified below). Prefer `prompt_state || jsonb_build_object('feedback_v1', <expr>)` with `coalesce` on every extracted value.
- **Writing Python `None` into JSONB values:** writes JSON `null`; `'null'::jsonb || '{...}'` becomes an array (verified). Never bind None. Always pass concrete ints/strings.
- **`trackFeature` in the mount effect** to record "shown": forbidden (D-03). The DB already records views.
- **Adding `useQuery`/`useMutation` directly in `PersonaGrid`:** breaks its provider-less tests. Prop-drill from `Bots.tsx`. Hooks live only inside `FeedbackAskBubble`, which only renders when the ask is active, so existing tests that never set `feedback_ask` don't need a provider.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Serializing view/snooze/done requests | Manual promise chaining or a "pending" flag | TanStack `useMutation({ scope: { id: 'feedback-ask' } })` | Built-in, verified present in 5.102.8 |
| Concurrency-safe state transition | SELECT then UPDATE in Python | Single guarded `UPDATE ... RETURNING` | Locked decision. Postgres re-evaluates WHERE after the row lock (READ COMMITTED) |
| Shape validation of JSONB | DB CHECK on JSON paths | Pydantic `FeedbackAskState(extra="forbid")` on read + on the RETURNING value | Locked exception |
| Persona avatar for Hilda | New image wiring | `TrainBotBubble` + `PERSONA_REGISTRY['wall-1800']` (asset exists) | Same component as the other three bubbles |
| Dev time travel | `datetime.now()` | `Depends(dev_now_utc)`; tests use `app.dependency_overrides[dev_now_utc] = lambda: now` (precedent `tests/routers/test_train_medals.py:100`) | Project rule |

## Common Pitfalls

### Pitfall 1: FeedbackModal unmounts mid-draft
**What goes wrong:** "Sure!" marks the ask done, the profile patch or refetch flips `active=false`, the surface stops rendering the bubble, and a modal owned by the bubble closes and loses the draft.
**Why:** Import re-renders and refetches the profile on a 3s tick during imports (Import.tsx comment above `importBubbleVariant`). `refetchOnWindowFocus` fires once the 5-minute profile staleTime has passed.
**How to avoid:** Mount one `FeedbackAskModalHost` in `App.tsx`, in both layout branches (and not behind `!playActive`, unlike `FeedbackButton`). Drive it from a tiny module store (`useSyncExternalStore`).
**Warning signs:** a test where the done mutation resolves while the modal is open and the dialog disappears.

### Pitfall 2: PUT /me/profile clobbers the ask
**What goes wrong:** `useSetLeaderboardHidden` writes the PUT response straight into the profile cache. If PUT doesn't compute `feedback_ask`/`active_days`, the ask vanishes (or the type breaks) after toggling the leaderboard opt-out.
**How to avoid:** One shared builder (Pattern 2). Add a backend test asserting GET and PUT return identical `feedback_ask` and `active_days`.

### Pitfall 3: Off-by-one active day on the threshold day
**What goes wrong:** The middleware inserts today's `user_activity` row only after the first authenticated response of the day. The first profile fetch on day 5 sees 4 rows, so no ask appears until the next refetch (up to 5 minutes or a reload). `snoozed_at_days` and the round-2 check have the same off-by-one.
**How to avoid:** `active_days = rows + (0 if today's row exists else 1)`, computed once per request in the service and reused for both profile and transition params. Use `now_utc.date()` from `dev_now_utc`.

### Pitfall 4: asyncpg can't type params inside jsonb_build_object
**What goes wrong:** `IndeterminateDatatypeError: could not determine data type of parameter $1`. **Verified this session** against dev Postgres 18 through SQLAlchemy asyncpg:
```
untyped FAIL: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.IndeterminateDatatypeError'>: could not determine data type of parameter $1
cast OK: {'d': '2026-10-05', 'views': 1}
bindparam_typed OK: {'d': '2026-10-05', 'views': 1}
```
**How to avoid:** `CAST(:today AS text)`, `CAST(:active_days AS int)`, or `text(...).bindparams(bindparam("x", type_=Integer))`. Only integration tests against Postgres catch this; mocks won't.

### Pitfall 5: The "3rd view hides it mid-day" trap
**What goes wrong:** If the 3rd view sets `status='snoozed'` and the profile rule is just "snoozed → inactive", the view response (or the next profile fetch) hides Hilda right after her 3rd appearance. That contradicts "Hilda shows on every surface visit that day".
**How to avoid:** Use `snoozed_by='views'` plus `last_view_date == today` as a grace clause (Pattern 1). An explicit "Maybe later" sets `snoozed_by='click'` and hides immediately. A side benefit: the funnel distinguishes explicit vs ignored snoozes in Postgres.

### Pitfall 6: Migration and model defaults
- Model: `prompt_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict)`. The `default=dict` covers ORM inserts (FastAPI-Users user creation, the test fixtures' `User(...)`). Don't use `none_as_null=True` here: the column is NOT NULL, so a None should fail loudly.
- Migration: `op.add_column('users', sa.Column('prompt_state', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))`. Postgres stores a non-volatile ADD COLUMN default in metadata with **no table rewrite** `[CITED: postgresql.org/docs/current/sql-altertable.html]`, so it's instant and existing rows read `{}`.
- `feedback.source`: `sa.Column('source', sa.Text(), server_default=sa.text("'floating_button'"), nullable=False)` plus `op.create_check_constraint('ck_feedback_source', 'feedback', "source IN ('floating_button', 'milestone_ask')")`. The table holds about 14 rows, so the CHECK validation scan is trivial `[CITED: same page: "Adding a CHECK ... requires scanning the table ... but does not require a table rewrite"]`. All existing rows really did come from the floating button, so the default backfill is truthful. Name follows `ck_<table>_<col>` (`ck_bot_game_settings_rating_source` precedent).
- `down_revision = 'a7c3e9d41f02'`. Downgrade drops the constraint, then the columns.
- `tests/conftest.py` auto-refreshes the template DB when the Alembic head changes, so no manual step is needed.

### Pitfall 7: Impersonation and guests
`LastActivityMiddleware` already skips impersonated requests. The ask must not be answered by an admin: return `active=False` in the profile and make the POST a 204/no-op when the JWT carries `is_impersonation` (reuse `_get_impersonation_context` from `users.py`). Guests: `active=False` always. They can't become eligible until promotion, and promotion is an in-place `UPDATE users`, so a promoted guest's pre-promotion activity days count. That's intended.

### Pitfall 8: Existing frontend tests without providers
`TrainStartScreen.test.tsx` mocks `useUserProfile` as `{ data: { email: 'user@example.com' } }` and renders without a QueryClientProvider. `PersonaGrid.test.tsx` renders provider-less too. Keep every new hook call inside `FeedbackAskBubble` (rendered only when active), and pass ask state into `TrainStartScreen` as a prop from `Train.tsx` (like `isGuest` and `hasGames`). Pre-existing tests then pass untouched, and new tests opt in with a provider or mocks.

### Pitfall 9: Train landing interactions
- `isIntroHost` (Tank, intro stepper never completed) currently keeps the bubble visible on phones. Decide whether Hilda overrides Tank's intro (Open Question 3).
- `TrainMedalDialogHost` can pop a medal dialog on the same visit that counts a view. That's acceptable but worth knowing.
- The guest/import asks can't co-occur (guests and zero-game users are ineligible; a zero-game registered user with 5 active days *is* eligible, though). Decide whether the ask beats the import ask for such users. The recommendation is yes: the seed says it sits "above" the other ask in the bubble. Flag it in UAT.

## Code Examples

### Verified transition SQL (executed against dev Postgres 18 on a TEMP table, rolled back)

Input rows (today `2026-10-05`, active_days 16): `{}`; asking 1 view yesterday; asking 2 views yesterday; asking 1 view today; snoozed round 1 at 6 days by click; snoozed round 2 exhausted; done; unrelated key only. Output: rows 1, 2, 3, 5, 8 changed. Rows 4 (already viewed today), 6 (exhausted), and 7 (done) were untouched:
```
  1 | {"feedback_v1": {"round": 1, "views": 1, "last_view_date": "2026-10-05"}}
  2 | {"feedback_v1": {"round": 1, "views": 2, "last_view_date": "2026-10-05"}}
  3 | {"feedback_v1": {"round": 1, "views": 3, "status": "snoozed", "snoozed_by": "views", "last_view_date": "2026-10-05", "snoozed_at_days": 16}}
  5 | {"feedback_v1": {"round": 2, "views": 1, "last_view_date": "2026-10-05"}}
  8 | {"other_ask": {"status": "done"}, "feedback_v1": {"round": 1, "views": 1, "last_view_date": "2026-10-05"}}
UPDATE 5
```

VIEW (parametrize: `:uid`, `:today` text, `:active_days` int, `:max_views`, `:max_rounds`, `:gap`, all CAST):
```sql
UPDATE users SET prompt_state = prompt_state || jsonb_build_object('feedback_v1',
    CASE WHEN prompt_state->'feedback_v1'->>'status' = 'snoozed'           -- round-2 start (WHERE guarantees eligibility)
         THEN jsonb_build_object('round', 2, 'views', 1, 'last_view_date', CAST(:today AS text))
         ELSE coalesce(prompt_state->'feedback_v1', '{}'::jsonb)
              || jsonb_build_object('round', coalesce((prompt_state->'feedback_v1'->>'round')::int, 1),
                                    'views', coalesce((prompt_state->'feedback_v1'->>'views')::int, 0) + 1,
                                    'last_view_date', CAST(:today AS text))
    END
    || CASE WHEN (CASE WHEN prompt_state->'feedback_v1'->>'status' = 'snoozed' THEN 1
                       ELSE coalesce((prompt_state->'feedback_v1'->>'views')::int, 0) + 1 END) >= CAST(:max_views AS int)
            THEN jsonb_build_object('status', 'snoozed', 'snoozed_at_days', CAST(:active_days AS int), 'snoozed_by', 'views')
            ELSE '{}'::jsonb END)
WHERE id = :uid
  AND coalesce(prompt_state->'feedback_v1'->>'last_view_date', '') <> CAST(:today AS text)
  AND ( prompt_state->'feedback_v1'->>'status' IS NULL
     OR ( prompt_state->'feedback_v1'->>'status' = 'snoozed'
          AND coalesce((prompt_state->'feedback_v1'->>'round')::int, 1) < CAST(:max_rounds AS int)
          AND CAST(:active_days AS int) >= (prompt_state->'feedback_v1'->>'snoozed_at_days')::int + CAST(:gap AS int) ) )
RETURNING prompt_state->'feedback_v1'
```
(A JSON `->>` on a missing key yields SQL NULL, so `{}` and "key absent" both match `status IS NULL`. Verified with row 1.)

SNOOZE (explicit click; allowed while asking or during the 3rd-view grace day):
```sql
UPDATE users SET prompt_state = prompt_state || jsonb_build_object('feedback_v1',
    coalesce(prompt_state->'feedback_v1', '{}'::jsonb)
    || jsonb_build_object('status', 'snoozed', 'snoozed_at_days', CAST(:active_days AS int), 'snoozed_by', 'click'))
WHERE id = :uid
  AND ( prompt_state->'feedback_v1'->>'status' IS NULL
     OR ( prompt_state->'feedback_v1'->>'snoozed_by' = 'views'
          AND prompt_state->'feedback_v1'->>'last_view_date' = CAST(:today AS text) ) )
RETURNING prompt_state->'feedback_v1'
```
Verified output: `{"round": 1, "views": 2, "status": "snoozed", "snoozed_by": "click", "last_view_date": "2026-10-05", "snoozed_at_days": 16}`.

DONE ("Sure!", from any non-done state):
```sql
UPDATE users SET prompt_state = prompt_state || jsonb_build_object('feedback_v1',
    coalesce(prompt_state->'feedback_v1', '{}'::jsonb) || '{"status": "done"}'::jsonb)
WHERE id = :uid AND prompt_state->'feedback_v1'->>'status' IS DISTINCT FROM 'done'
RETURNING prompt_state->'feedback_v1'
```

Strictness probe (verified):
```
 jsonb_set_null_nukes_column | json_null_concat
 t                           | [null, {"a": 1}]
```

Repository contract: each function returns the validated `FeedbackAskState | None` (None means the WHERE didn't match, i.e. an idempotent no-op). After RETURNING, run `FeedbackAskState.model_validate(row)`. A `ValidationError` raised inside the request rolls the transaction back, because `get_async_session` only commits after a clean `yield` `[VERIFIED: app/core/database.py:31-34]`. That makes this the "validate on write" step. The endpoint always returns the recomputed `FeedbackAskView` (re-read via `resolve_feedback_ask` on the RETURNING state, or on the unchanged state for a no-op), so the client can patch its cache.

Optional extra guard: also put `AND NOT is_guest` in each WHERE. The service already checks eligibility, so this is just cheap defense in depth.

### Endpoint shape (recommended)
```python
# app/routers/users.py
@router.post("/me/feedback-ask", response_model=FeedbackAskView)
async def feedback_ask_action(
    body: FeedbackAskActionRequest,           # action: Literal["view", "snooze", "done"]
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    impersonation: Annotated[ImpersonationContext | None, Depends(_get_impersonation_context)],
    now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)],
) -> FeedbackAskView:
    return await feedback_ask_service.apply_action(session, user, body.action,
                                                   now_utc=now_utc, impersonated=impersonation is not None)
```
Full path is `/api/users/me/feedback-ask`, because routers mount under `/api` in `app/main.py`. For ineligible users (guest, has feedback, < 5 days, impersonated), the service skips the UPDATE and returns `active=False`, which is 200 and idempotent. No 4xx means no Sentry noise from a stale tab.

## Umami

- `trackFeature('action', { target: 'feedback-ask-sure' })` and `'feedback-ask-later'`. Register both in `ACTION_TARGETS` `[VERIFIED: frontend/src/lib/analytics.ts:384-401]`. They fall into the bare `{ target: Exclude<ActionTarget, 'reminder-enable'> }` branch of `ActionProps` (lines 483-485), so no new prop types are needed. `trackFeature` adds `page` from the route, which already distinguishes the surfaces: `/library/import` → `library`, `/train` → `train`, `/bots` → `bots` (`PAGE_IDS`, line 245). `lib/__tests__/analytics.test.ts` enforces kebab-case automatically.
- No "shown" event. It would have to fire from an effect (forbidden, D-03), and views are DB-known.
- The submit itself stays un-evented (a DB row, with `source`).
- Rationale per frontend/CLAUDE.md: `prompt_state` is overwritten in place and doesn't record which page the click happened on, so the click event is justified.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Floating feedback button on all viewports | Desktop-only (`hidden sm:block`) | quick 260809-iep (2026-08-09) | Mobile has no feedback entry point. The Train-landing ask on phones (locked mobile exception) becomes the only mobile path for eligible users. |
| Nullable JSONB + `coalesce || patch` (Phase 233 telemetry) | NOT NULL `'{}'` JSONB (this phase) | — | `coalesce` stays as harmless defense |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Prod `user_activity` per-user row counts are small (about 100 max) so the per-profile count is negligible | Current-State Map | Low. Worst case a few hundred index-only rows. |
| A2 | `refetchOnWindowFocus` is on (TanStack default, not overridden in `queryClient.ts`) | Pitfall 1 | Low. The 3s Import refetch alone justifies the app-level host. |
| A3 | Admins impersonating should see no ask and record nothing | Pitfall 7 | Low. It's a product preference; confirm in UAT. |
| A4 | Today-inclusive `active_days` is the desired semantics | Pitfall 3 | Low. It only shifts the ask's first appearance by one fetch. |
| A5 | The ask should beat the zero-game import ask on Train landing for eligible zero-game users | Pitfall 9 | Low/UX |

## Open Questions

1. **Copy says "5 days" but most recipients have more (owner decision, blocks UI copy).**
   - What we know: at launch 98 users are eligible, most with well over 5 active days. Every round-2 ask happens at >= 15 days.
   - Options: (a) interpolate the count: "You've been with FlawChess for {active_days} days now, thanks!" (active days, not calendar tenure); (b) fixed 5-day copy only when `active_days` is in 5-9, a neutral line otherwise ("You've been with FlawChess for a while now, thanks!"); (c) keep the literal copy.
   - Recommendation: (a). The server already returns `active_days`.
2. **Import page `welcome` variant.** The seed says the ask replaces the *explore* copy. A registered user with 5 active days who never completed an import sees `welcome`. Recommendation: the ask overrides any non-guest variant (one shared state, first surface wins). Confirm.
3. **Tank's intro on Train landing.** When the Train intro stepper was never completed (`isIntroHost`), should Hilda replace Tank? Recommendation: no. Keep the onboarding host coherent (Tank opens intro step 1). The ask will reach this user on Import or Bots anyway.
4. **Round-2 copy.** Same sentence, or a gentler "Me again! ..."? Recommendation: same template as Q1(a). That's no extra decision once Q1 is settled.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (docker `flawchess-dev-db-1`) | migration, tests | ✓ | postgres:18-alpine, healthy | — |
| uv / Python 3.14 | backend | ✓ | (ran `uv run alembic heads` OK) | — |
| Node + frontend deps | frontend | ✓ | @tanstack/react-query 5.102.8 | — |

No missing dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend) |
| Config file | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block |
| Quick run command | `uv run pytest tests/test_feedback_ask.py tests/test_feedback_router.py -x` and `cd frontend && npm test -- --run src/components/feedback` |
| Full suite command | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FBASK-01 | Existing users read `prompt_state == {}`; `feedback.source` defaults to `floating_button`; CHECK rejects other values | integration | `uv run pytest tests/test_feedback_ask.py -k migration_defaults -x` | ❌ Wave 0 |
| FBASK-02 | GET and PUT profile both return `active_days` + `feedback_ask`, identical values | integration | `uv run pytest tests/test_feedback_ask.py -k profile -x` | ❌ Wave 0 |
| FBASK-03 | `resolve_feedback_ask` truth table (guest, has_feedback, 4 vs 5 days, done, snoozed by click, grace day, round-2 gap at 15 vs 16 days, exhausted) | unit | `uv run pytest tests/services/test_feedback_ask_service.py -x` | ❌ Wave 0 |
| FBASK-03 | Today-inclusive active_days (no row today → +1) | integration | same file `-k active_days` | ❌ Wave 0 |
| FBASK-04 | view: first, same-day no-op, next day increments, 3rd auto-snoozes with grace, round 2 after +10, never after round 2; snooze; done; unrelated key preserved | integration (real Postgres; Pitfall 4) | `uv run pytest tests/test_feedback_ask.py -k transition -x` | ❌ Wave 0 |
| FBASK-04 | Two concurrent same-day view POSTs → `views == 1` (separate requests, not one session) | integration | `-k concurrent` | ❌ Wave 0 |
| FBASK-04 | 422 on `action: "bogus"`; impersonation → no state change; guest → `active=False`, no write; dev clock override via `app.dependency_overrides[dev_now_utc]` | integration | `-k guards` | ❌ Wave 0 |
| FBASK-05 | POST /feedback with `source=milestone_ask` persists it; omitted → `floating_button`; invalid → 422 | integration | `uv run pytest tests/test_feedback_router.py -x` | ✅ extend |
| FBASK-06 | Bubble renders Hilda + copy + testids; posts `view` once on mount; Later → snooze + bubble gone immediately; Sure → done + modal opens via host and survives bubble unmount; Umami targets fired | component | `npm test -- --run src/components/feedback/__tests__/FeedbackAskBubble.test.tsx` | ❌ Wave 0 |
| FBASK-05 | FeedbackModal uses the placeholder prop and sends `source` | component | `npm test -- --run src/components/feedback/__tests__/FeedbackModal.test.tsx` | ✅ extend |
| FBASK-07 | Import: active → ask bubble instead of `import-bot-bubble`; inactive → unchanged | component | `npm test -- --run src/components/import src/pages/__tests__/Import` | ✅ extend |
| FBASK-08 | TrainStartScreen: active → Hilda, no reminder ask, no `max-sm:hidden` on `train-landing-host` | component | `npm test -- --run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ extend |
| FBASK-09 | PersonaGrid: `feedbackAskActive` → no `bots-intro-info` popover, Hilda shown | component | `npm test -- --run src/components/bots/__tests__/PersonaGrid.test.tsx` | ✅ extend |
| FBASK-10 | New ACTION_TARGETS kebab-case (auto) | unit | `npm test -- --run src/lib/__tests__/analytics.test.ts` | ✅ |

Manual/UAT (browser, run it yourself per project memory): seed a dev user with 5 `user_activity` rows and walk Import → Train → Bots on one day (one view counted, Hilda on all three). Check the phone width on Train landing. Click "Sure!" during an active import poll and confirm the modal persists.

### Sampling Rate
- **Per task commit:** the quick-run command for the touched side.
- **Per wave merge:** the full backend suite plus the frontend lint/build/test.
- **Phase gate:** the full pre-merge gate green before `/gsd-verify-work`.
- **Mutation proof (project memory):** for the once-per-day guard and the round-2 cap, temporarily drop the guard clause and confirm the test fails.

### Wave 0 Gaps
- [ ] `tests/test_feedback_ask.py`: router + repository integration (needs a helper to seed `user_activity` rows for a user, and a cleanup that deletes the user; CASCADE removes activity/feedback).
- [ ] `tests/services/test_feedback_ask_service.py`: pure truth table.
- [ ] `frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx`: QueryClientProvider harness (template: `FeedbackButton.test.tsx`).
- No framework install needed.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (reuses FastAPI-Users JWT) | `current_active_user` |
| V3 Session Management | no | — |
| V4 Access Control | yes | user_id only from the JWT (never body or path); impersonated tokens can't mutate the ask |
| V5 Input Validation | yes | Pydantic `Literal` for `action` and `source`; `extra="forbid"` stored-shape model; DB CHECK on `feedback.source` |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR: mutate another user's ask | Tampering | `WHERE id = :uid` from the JWT only |
| Forged `source=milestone_ask` to skew yield metrics | Repudiation/Tampering | Accept as low-risk (a user can only tag their own feedback; rate limit 5/h already applies). Optionally accept `milestone_ask` only when `feedback_v1.status == 'done'`, but not recommended (over-engineering). |
| Dev clock header in prod | Tampering | `dev_now_utc` honours the header only when `ENVIRONMENT == "development"` `[VERIFIED: app/core/dev_clock.py:68-69]` |
| Admin impersonation answering for the user | Repudiation | Impersonation → no-op + `active=False` |
| Request flooding the POST | DoS | Each call is one indexed single-row UPDATE that no-ops after the first view of the day. No limiter needed. |

## Sources

### Primary (HIGH confidence)
- Codebase files read this session (paths and lines cited inline): `app/models/{user,user_activity,feedback,drill_solve}.py`, `app/middleware/last_activity.py`, `app/core/{dev_clock,database}.py`, `app/routers/{users,feedback}.py`, `app/schemas/{users,feedback}.py`, `app/repositories/{user_repository,feedback_repository,train_repository}.py`, `app/services/feedback_service.py`, Alembic migrations `a7c3e9d41f02`/`c4e7a91d2b58`, `tests/conftest.py`, `tests/test_feedback_router.py`, `tests/test_users_first_touch.py`; frontend `FeedbackButton/FeedbackModal`, `useFeedback`, `useUserProfile`, `types/{users,feedback}.ts`, `ImportBotBubble`, `importBotBubbleCopy.ts`, `pages/Import.tsx`, `TrainStartScreen.tsx`, `TrainBotBubble.tsx`, `SignupAskActions.tsx`, `ImportAskActions.tsx`, `PersonaGrid.tsx`, `pages/Bots.tsx`, `personaRegistry.ts`, `trainBotCopy.ts`, `analytics.ts` (+ test), `App.tsx`, `queryClient.ts`.
- Executed probes: transition SQL on a dev-DB TEMP table (rolled back); asyncpg param-typing probe; `EXPLAIN ANALYZE` per-user count; `\d feedback`; `uv run alembic heads`; TanStack query-core source for `scope`.
- PostgreSQL ALTER TABLE docs (fast default, CHECK scan): https://www.postgresql.org/docs/current/sql-altertable.html

### Secondary (MEDIUM)
- None needed.

### Tertiary (LOW)
- TanStack `refetchOnWindowFocus` default (training knowledge, A2).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new deps; versions verified from installed packages.
- Architecture: HIGH. Every surface, hook and router was read; the transition SQL was executed.
- Pitfalls: HIGH. Pitfalls 1, 2, 3, 4 and 8 were each traced to specific lines or a reproduced failure.

**Research date:** 2026-10-05
**Valid until:** 2026-11-04 (stable internal codebase; re-check if TrainStartScreen/PersonaGrid change before planning)
