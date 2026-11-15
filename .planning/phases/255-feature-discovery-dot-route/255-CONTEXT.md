# Phase 255: Feature Discovery Dot Route (SEED-261115-d0t) - Context

**Gathered:** 2026-11-15
**Status:** Ready for planning

<domain>
## Phase Boundary

One strategy for the red pulsating dot. An ordered route of features with the dot in exactly one place at a
time, moving from one unexplored feature to the next. The same mechanism onboards new users and, later,
announces a new feature by adding a step. One arbiter replaces the four dot systems that exist today: the nav
dots, the Openings sidebar hint chain, the re-minted Train flag and the Library "import your games" dot.
Completion is stored server-side.

Not in this phase: a "What's New" panel, "New" pills, sticky subnav work, renaming tabs, in-content teaser
links (the last three stay in SEED-199).

</domain>

<decisions>
## Implementation Decisions

### Locked before the discussion
- **D-01:** Dot only. No "What's New" panel and no static "New" pills (owner, 2026-11-09).
- **D-02:** One route dot at a time (owner, 2026-11-09). The Train count badge is the one exception, see D-17.
- **D-03:** Path problem: one logical step is drawn in two places. The dot shows on the nav item while the user
  is elsewhere, and on the subtab or control once the user is in that section (owner, 2026-11-09).
- **D-04:** Completion is stored server-side and follows the user across devices (owner, 2026-11-15).
  — **Reversibility:** costly — moving back to localStorage would drop every user's stored route state.
- **D-05:** Dots only on important features, to avoid dot fatigue (owner, 2026-11-15). Adding a step is a
  deliberate choice, not a default for every tab.

### Route contents and order
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

### Ignored steps
- **D-10:** A step the user does not act on auto-skips after 3 active days with the dot on it, then the dot
  moves to the next step. Extract the 3 as a named constant.
- **D-11:** "Active days" should come from `user_activity` (one row per user per active day) where possible,
  so no extra write is needed each time the dot is shown (owner suggestion).
- **D-12:** A new step added later is placed in the route like any other step. There is no queue-jumping for
  new features: a user with earlier open steps reaches the new one after those are done or skipped.

### Completion and existing users
- **D-13:** A page or subtab step is done when the page or subtab is opened (Import, Bots, Openings,
  Openings Stats, Endgames, Library Stats). A control step is done when the control is used (played-as,
  filters, and Train per D-21).
- **D-21:** The Train step uses the "used" rule (owner, 2026-11-15, during planning). It is done when the user
  clicks the start-training-session button of the personalized puzzle training on Train, Today. Opening Train
  does not complete it. Per D-03 the dot sits on the Train nav item while the user is elsewhere and on the
  start button once the user is on Train, Today. This changes today's behaviour (Train currently clears on
  visit). The same rule shape is the model for a later blunder-check step in Today (D-09): a step inside a page
  the user has already opened needs its own ID and a "used" completion rule. The start button is always
  usable (users without imported games get a warmup session), so the Train step is never a locked target and
  its 3-day clock never pauses.
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

### Scope edges
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
  the full set).
- Locked targets. Openings, Endgames and Library Stats need imported games (`isNavLocked`). After D-14, an
  account without games can reach step 3 with a locked target. Suggested handling: no dot on a locked nav
  item, and the 3-day clock does not run while the current step's target is locked. This was not asked
  explicitly; raise it in the plan check if another handling looks better.
- Dot geometry on subtabs and on the sidebar controls, and the mobile path for the played-as and filters
  steps (they sit in a drawer on mobile).
- Whether the old localStorage keys are cleaned up or just left unread.
- Umami events for measuring the effect, if cheap.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source seed and prior analysis
- `.planning/seeds/SEED-261115-d0t-feature-discovery-dot-route.md` — the idea, the three existing dot systems,
  the proposed shape (route registry, one arbiter, set of IDs)
- `.planning/seeds/closed/SEED-199-subnav-discoverability.md` — Umami reach per page (the baseline for
  measuring this phase), nav-dot gating notes, sticky subnav and the other ideas that stay out of scope

### Project rules
- `CLAUDE.md` — database design rules, router and repository layout, `dev_now_utc` for time-dependent endpoints
- `frontend/CLAUDE.md` — testids, Umami, styling rules

No external specs. Requirements are fully captured in the decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/App.tsx`: `useNavIndicators` (shared by `NavHeader` and `MobileBottomBar`), `NavDot` (the
  pulsating red dot, desktop and mobile geometry), `NavIndicator`, `TrainBadge`, `isNavLocked`. The arbiter
  replaces the flag logic inside `useNavIndicators`.
- `app/models/user.py` `prompt_state` plus `app/repositories/feedback_ask_repository.py` and
  `app/schemas/feedback_ask.py`: an existing per-user JSONB state object with atomic guarded UPDATEs and a
  Pydantic shape, used by the feedback ask. A model for D-04.
- `app/models/user_activity.py`: one row per user per active day (`uq_user_activity_user_date`), written by
  `app/middleware/last_activity.py`. Source for D-11.
- `frontend/src/hooks/useUserProfile`: the profile query the nav already reads; a candidate carrier for route
  state.

### Established Patterns
- Today's dot state: `frontend/src/hooks/useUserFlag.ts` (localStorage, keyed per email) with
  `FLAG_OPENINGS_VISITED`, `FLAG_ENDGAMES_VISITED`, `FLAG_TRAIN_BOTS_VISITED` set by route effects in
  `App.tsx` (around lines 750 to 765).
- Openings sidebar chain: `frontend/src/pages/openings/useSidebarState.ts` (raw localStorage keys
  `played-as-hint-dismissed`, `filters-hint-dismissed`) and `frontend/src/pages/Openings.tsx` (around lines
  154 to 159, `showPlayedAsHint`, `showFiltersHint`, `showBookmarksHint`).
- Nav order: Library, Train, Bots, Opening, Endgame, Analysis (`NAV_ITEMS`, `BOTTOM_NAV_ITEMS`). Bots is a
  top-level nav item.
- Nav unlock rule: `navUnlocked = importedGameCount > 0 && tier1`; Train and Bots are import-exempt.

### Integration Points
- Subnavs that need a dot slot: Library (`frontend/src/pages/library/LibraryPage.tsx`, Stats and Import tabs)
  and Openings (`frontend/src/pages/Openings.tsx`, Stats tab).
- Existing tests assert the nav dots by testid (`openings-notification-dot`, `endgames-notification-dot`,
  `train-notification-dot`, `library-notification-dot`, with `-mobile` variants).

</code_context>

<specifics>
## Specific Ideas

- The owner's original picture: "a route, where the dot goes from one unexplored feature to the next", with
  the dot "only in one place at the time".
- Engagement first: Train and Bots lead the route, ahead of the analysis sections.
- First real use of the announcement path will be the blunder-check tab leaving beta (D-09).

</specifics>

<deferred>
## Deferred Ideas

- Blunder-check tab as a route step, when it leaves beta (D-09).
- Sticky subnav, inactive-tab affordance, tab renaming, in-content teaser links, post-import bubble links:
  all remain in SEED-199.
- "What's New" panel and "New" pills: rejected for now (D-01).

</deferred>

---

*Phase: 255-Feature Discovery Dot Route (SEED-261115-d0t)*
*Context gathered: 2026-11-15*
