# Phase 230: Weekly Train Leaderboards (SEED-185) - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Two weekly leaderboards on Train, used as a return motivator from the user's first session: a
**Points** board (effort, sum of Train points this ISO week) and an **Accuracy** board (pooled
average session score this week, labelled as accuracy/consistency, never skill). Each shows the top 5
plus the viewer's own row with neighbours. Delivered as one tabbed card on the Train start screen, a
rank-change line on the session score screen, a server-persisted "Hide me from leaderboards" toggle
in the settings overlay, and one Privacy-page line.

Out of scope: medals and their weekly snapshot table, past-week history, notifications, league tiers.

</domain>

<decisions>
## Implementation Decisions

### Locked upstream (SEED-185 + ROADMAP Phase 230, owner 2026-10-03; do not re-open)
- **D-01 Scoring:** server-side from `drill_solves`: puzzle points = `correct_guess::int +
  move_quality` (max 3). Add a parity test pinning `GUESS_POINTS` / `MOVE_TIER_POINTS` from
  `frontend/src/lib/trainScore.ts`. Accuracy = pooled `sum(points) / (3 × puzzles)`. Count solves
  (`solved_at IS NOT NULL`), not completed sessions. Points board counts every solve; the Accuracy
  board and its qualifier exclude `source = SHARP_FILLER`.
- **D-02 Window:** one ISO week in UTC for both boards, keyed on `drill_solves.solved_at` (NOT
  `drill_sessions.session_date`). Deadline Sunday 24:00 UTC, reset Monday 00:00 UTC, countdown
  shown. No rolling window. A session spanning the deadline splits by each solve's timestamp.
  Time comes from the `dev_now_utc` dependency (`app/core/dev_clock.py`), never `datetime.now()`.
- **D-03 Qualifier:** the Accuracy position is tentative until 20 non-filler puzzles this week.
  Tentative users ARE ranked and listed, marked "N more puzzles to qualify". Points board has no
  qualifier.
- **D-04 Ranking:** ties share a rank (1, 1, 1, 4); within a tie, more puzzles solved is listed
  first. Top 5, then the viewer's row with 2 above and 2 below, plus an "N points to pass <name>"
  target.
- **D-05 Identity:** lichess username, else chess.com username, else "Anonymous". Impersonation is
  an ACCEPTED RISK (no username verification). Do not add verification, blocklists or OAuth.
- **D-06 Visibility:** registered users with a username appear by default. Guests never appear to
  others. Medals are a follow-up phase; nothing here may block them (the UTC deadline is their
  prerequisite).

### Layout & placement
- **D-07:** ONE leaderboard card ("This week") on the Train start screen with a **Points |
  Accuracy** tab toggle and the countdown in the card header. Not two stacked or side-by-side cards.
- **D-08:** Start screen order: bot bubble → `TrainStreakCard` (Start button) → **leaderboard
  card** → `TrainStatsCard` → `TrainScheduleSettings`. The Start button stays above the board.
- **D-09:** The selected tab is **remembered in localStorage** (Points on first visit). Wrap
  reads/writes in try/catch and fall back to Points.
- **D-10:** The score board's tab/label is **"Accuracy"**, with a one-line helper under the tab
  along the lines of "Average session score, 20+ puzzles to qualify". Never call it skill.
- **D-11:** The session score screen shows **only a compact rank-change line per board** (under
  "Points: x/y"), e.g. "Points board: #7 (up 3)" and "Accuracy: #4 (tentative)". No full board
  on the score screen (Done returns to the landing, which has it).
- **D-12:** Rank change = rank with vs without this session's solves, computed at the same moment,
  so it can only go up or stay the same. With no before-rank (the first session of the week), show a
  plain "#12 this week". An unchanged rank shows the plain rank with no delta.

### Hidden / anonymous / guest edges
- **D-13:** An opted-out user is excluded from everyone else's board, and **other users' ranks are
  computed without them**. They still see a **private would-be row** at their would-be rank (with
  neighbours), marked "Hidden from others", so the opt-out keeps their own motivation.
- **D-14:** A guest sees the full tabbed board with a **ghost row** at their would-be rank (with
  neighbours, same shape as D-13), labelled "You (guest)", plus "Sign up to claim your spot" with
  `SignupAskActions` under the board. A guest's solves never affect anyone else's rank.
- **D-15:** Users without a username show as plain **"Anonymous"**. Identical labels are fine
  (6 of 80 registered trainers last week); no numbering, no exclusion.
- **D-16:** The opt-out toggle lives in a new **"Privacy" card** in the Phase 228 `SettingsPanel`
  (Switch + helper line). Unlike the other settings it is **server-persisted** (a new `users`
  column, migration required). Plus one line on `frontend/src/pages/Privacy.tsx`.
  — **Reversibility:** costly — adds a `users` column via Alembic migration and a new API field;
  undoing means a down-migration plus removing the frontend toggle.
- **D-17:** A guest's score-screen line reads **"You'd be #7"** (hypothetical, no delta). No second
  CTA button: the score bubble's existing guest sign-up ask carries it.

### Post-research owner calls (2026-10-03, plan-phase)
- **D-18 Accuracy rank direction:** D-12's "can only go up" holds for the Points board only; on the
  Accuracy board a weak session can leave the rank worse than without it. The score-screen
  Accuracy line shows "(up N)" only when the rank improved; when it is unchanged OR worse, show the
  plain rank with no delta (never "(down N)").
- **D-19 Qualifier stays non-filler:** keep D-01/D-03 as locked: the 20-puzzle qualifier counts
  non-filler solves only, even though warm-up users (guests, zero-game users) earn only ~2
  qualifying puzzles per 8-puzzle session. Copy must never imply all solves count ("N more puzzles
  to qualify" only), and a viewer with zero non-filler solves this week gets a specific
  not-on-this-board line rather than a misleading count.

### Claude's Discretion
- **Row content:** what each row shows (rank, name, points or %, puzzles count), how the viewer's
  row is highlighted, and the tentative marker styling. Keep rows narrow enough for mobile at
  `max-w-2xl`.
- **"N points to pass" on the Accuracy board:** pick a meaningful target (e.g. a percentage-point
  gap, or "N more correct puzzles"), or show the target on the Points board only.
- **Countdown:** format ("ends in 1d 4h") and update cadence.
- **Freshness:** refetch on screen mount and after a session ends vs. after every solve. The score
  screen needs before/after ranks for D-12 (fetched or returned by the solve/complete endpoint).
- **Empty / near-empty week:** the Monday 00:05 state (few or no entries), and a viewer with no
  solves this week (show the board without an own row, or "Solve a puzzle to enter").
- **Privacy card:** position in the panel (it must not be reset by "Reset to defaults", since it is
  a server-persisted privacy choice, not a display preference) and hiding it for guests.
- **Query shape and indexing:** a single windowed aggregation (`RANK()`) vs. per-board queries,
  whether `drill_solves` needs an index on `solved_at` (or user + `solved_at`), and short-TTL
  caching. Population is ~100 trainers/week, ~1.5k solves.
- **Umami:** a `trackFeature` event for tab switches and the opt-out toggle, per the Phase 229
  registry (`frontend/CLAUDE.md` rule).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `../../seeds/closed/SEED-185-weekly-train-leaderboards.md` — full locked decisions, prod evidence
  (points ≈ volume, qualifier rationale, warm-up/filler exclusion), and the medals follow-up constraint
- `.planning/ROADMAP.md` § "Phase 230: Weekly Train Leaderboards (SEED-185)" — phase goal and locked list

### Scoring and data
- `frontend/src/lib/trainScore.ts` — `GUESS_POINTS`, `MOVE_TIER_POINTS` (parity test target)
- `app/models/drill_solve.py` — `correct_guess`, `move_quality`, `source` (`DrillSource.SHARP_FILLER = 2`), `solved_at`
- `app/models/drill_session.py` — session rows (`session_date` is the user-local day, NOT the window key)
- `app/models/user.py:19-31` — `chess_com_username`, `lichess_username`, `is_guest`
- `app/core/dev_clock.py` — `dev_now_utc` dependency for the week window

### Settings and privacy
- `.planning/phases/228-settings-page/228-CONTEXT.md` — D-17 overlay (Dialog/Sheet, no `/settings` route), section-as-Card pattern, localStorage settings model
- `frontend/src/components/settings/SettingsPanel.tsx` — host for the new Privacy card
- `frontend/src/pages/Privacy.tsx:27` — usernames listed as collected data; add the leaderboard line

### Analytics
- `.planning/phases/229-umami-identify-feature-events/229-CONTEXT.md` — typed `trackFeature` registry
- `frontend/CLAUDE.md` — Umami / testid / styling rules

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TrainStreakCard` / `TrainStatsCard` (`frontend/src/components/train/`): `Card as="section" className="w-full"` pattern for the new leaderboard card
- `SignupAskActions` (`components/train/SignupAskActions.tsx`, `source` prop): guest CTA under the board (D-14)
- `components/ui/toggle-group`: segmented control already used by the settings panel (D-07 tabs)
- `components/ui/switch`: opt-out toggle (D-16)
- `TrainScheduleSettings` + `useTrainSettings` (`PUT /train/settings`): an existing server-persisted Train setting round-trip to mirror for the opt-out flag

### Established Patterns
- Routers: `APIRouter(prefix="/train", ...)` in `app/routers/train.py`; SQL lives in `app/repositories/train_repository.py`, not services
- `isGuest` is threaded through `TrainStartScreen` / `TrainScoreScreen` props already
- Landing container: `LANDING_CONTAINER_CLASS` = single column, `max-w-2xl`, `gap-4`
- Phase 228 settings are localStorage + `useSyncExternalStore`; the opt-out is the first server-backed setting in that panel

### Integration Points
- `TrainStartScreen.tsx` (~lines 349-396): insert the card after `TrainStreakCard` in both the in-progress and default landing branches
- `TrainScoreScreen.tsx` (~line 319, under "Points: x/y"): rank-change lines
- `SettingsPanel.tsx`: new Privacy card, guest-hidden, excluded from Reset
- New `users` column + Alembic migration for the opt-out flag

</code_context>

<specifics>
## Specific Ideas

- Score-screen line shape: "Points board: #7 (up 3)" / "Accuracy: #4 (tentative)" / first entry "#12 this week" / guest "You'd be #7".
- Hidden and guest rows share one "would-be row" rendering (private to the viewer).
- Expect Monday's Accuracy top to be short 100% sessions; accepted (SEED-185 round 2).

</specifics>

<deferred>
## Deferred Ideas

- Medals for the weekly top 3 plus a persisted weekly result snapshot table (already scoped as a follow-up in SEED-185).
- Username verification / display-name blocklist if impersonation abuse appears (SEED-185, explicitly not now).

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`: keyword match only (chart axis), unrelated
- `172-deferred-review-findings.md`: keyword match only, unrelated
- `2026-03-11-bitboard-storage-for-partial-position-queries.md`: keyword match only, unrelated
- `2026-08-29-variation-tree-nested-button.md`: keyword match only, unrelated

</deferred>

---

*Phase: 230-weekly-train-leaderboards*
*Context gathered: 2026-10-03*
