# Phase 230: Weekly Train Leaderboards (SEED-185) - Research

**Researched:** 2026-10-03
**Domain:** FastAPI/SQLAlchemy weekly aggregation + ranking, users-column migration, React/TanStack Query Train UI, settings overlay
**Confidence:** HIGH (all integration points read in this session; no new packages)

## Summary

This phase adds no dependencies. Everything it needs already exists: `drill_solves` carries `correct_guess`, `move_quality`, `source` and `solved_at`; the Train router already injects `now_utc` from `dev_now_utc`; the frontend has `Card`, `ToggleGroup`, `Switch`, `SignupAskActions` and the typed `trackFeature` registry. The work is one aggregation query, a pure-Python ranking module, one `GET /train/leaderboard` endpoint, one `users` column (plus an optional `solved_at` index) in a single migration, a leaderboard card, a score-screen rank line component, a Privacy card in `SettingsPanel`, and one Privacy-page line.

The key design call is **SQL aggregates, Python ranks**. One `GROUP BY user_id` query over the week window returns roughly 100 rows (prod: 77 to 100 trainers a week, about 1.5k solves). A pure function then ranks them. Every viewer-specific variant the locked decisions require falls out of the same function by re-ranking one modified viewer row against an unchanged list of visible others: hidden users' private would-be rank (D-13), the guest ghost row (D-14), and "rank without this session's solves" (D-12). Writing those in SQL would mean several near-duplicate window queries. In Python they are cheap and fully unit-testable without a database. On the dev DB the query compiled and ran in 0.4 ms. No cache is needed.

Six things are easy to get wrong when planning. **(1)** D-12 claims the rank change "can only go up or stay the same". That holds for the Points board but not for Accuracy: a bad session lowers pooled accuracy, so the rank with this session can be worse than without it. The plan needs a rule for that case (recommendation: no delta when the rank got worse; see Open Questions). **(2)** Warm-up sessions are 75% `SHARP_FILLER` (an 8-puzzle warm-up is 2 herrings + 6 sharp). Guests and zero-game users therefore earn only about 2 qualifying puzzles per session, and "20+ puzzles to qualify" copy will confuse anyone who counts their own solves. **(3)** `TrainStartScreen.test.tsx`, `TrainScoreScreen.test.tsx` and `SettingsPanel.test.tsx` render without a `QueryClientProvider` and mock hooks module by module. New query-backed children break them unless those tests mock the new hook or component. **(4)** Leaderboard queries are GLOBAL across users and router tests commit. Backend tests must pin `now_utc` to a unique ISO week per test, or they flake under the shared per-worker DB, the same failure shape as the eval-lottery isolation issue. **(5)** Two docstrings say scoring must never run server-side (`SolvedResult` in `app/schemas/train.py`, `DrillMoveQuality` in `app/models/drill_solve.py`). D-01 now deliberately adds a server-side aggregate pinned by a parity test, so those comments need updating or they will mislead the next reader. **(6)** `TrainScoreScreen` is already at the cognitive-complexity cap and carries a comment saying so. The rank lines must live in their own component.

**Primary recommendation:** Build `app/services/train_leaderboard.py` (pure: week window, points/accuracy metrics, ranking, slicing, pass target, display name, constants) plus `app/repositories/train_leaderboard_repository.py` (two read queries), expose `GET /train/leaderboard?session_id=<optional>`, store the flag as `users.leaderboard_hidden` (written through the existing `PUT /users/me/profile`, read from `GET /users/me/profile`), and render the board with `TrainLeaderboardCard` and `TrainScoreRankLines`, which share one `useTrainLeaderboard` hook.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked upstream (SEED-185 + ROADMAP Phase 230, owner 2026-10-03; do not re-open)
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

#### Layout & placement
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

#### Hidden / anonymous / guest edges
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

### Deferred Ideas (OUT OF SCOPE)
- Medals for the weekly top 3 plus a persisted weekly result snapshot table (already scoped as a follow-up in SEED-185).
- Username verification / display-name blocklist if impersonation abuse appears (SEED-185, explicitly not now).

#### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`: keyword match only (chart axis), unrelated
- `172-deferred-review-findings.md`: keyword match only, unrelated
- `2026-03-11-bitboard-storage-for-partial-position-queries.md`: keyword match only, unrelated
- `2026-08-29-variation-tree-nested-button.md`: keyword match only, unrelated
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs are assigned to this phase. The locked decisions D-01..D-17 serve as the requirement set. Each one is mapped to a test in the Validation Architecture section below.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Server-side points/accuracy + parity test | Aggregate SQL (verified compile + dev-DB run), parity test pattern (`tests/services/test_opening_insights_arrow_consistency.py`) |
| D-02 | ISO-week UTC window on `solved_at`, `dev_now_utc` | `week_window()` pure fn; `NowUtc` alias already in `app/routers/train.py:54` |
| D-03 | Tentative <20 non-filler puzzles, still ranked | `ACCURACY_QUALIFY_MIN_PUZZLES = 20`; non-filler `FILTER` in SQL |
| D-04 | Shared ranks, puzzles-desc within tie, top 5 + ±2, pass target | Pure `rank_board()` + `slice_board()` |
| D-05/D-15 | Display name precedence, "Anonymous" | Pure `display_name()` with blank-string guard |
| D-06/D-13/D-14 | Visibility: registered default, hidden excluded, guests never shown | Visible-set filter + viewer re-insertion |
| D-07..D-10 | One tabbed card, order, localStorage tab, "Accuracy" label | `TrainLeaderboardCard` + `ToggleGroup`; insert after `TrainStreakCard` |
| D-11/D-12/D-17 | Score-screen rank lines | `GET /train/leaderboard?session_id=` returns `rank_without_session` |
| D-16 | Server-persisted opt-out, Privacy card, Privacy page | `users.leaderboard_hidden` + `PUT /users/me/profile` optional field |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Routers are HTTP-only; SQL lives in `app/repositories/`; business logic in `app/services/`. Router convention is `APIRouter(prefix="/train", tags=["train"])` with relative paths (`@router.get("/leaderboard")`).
- No magic numbers: `ACCURACY_QUALIFY_MIN_PUZZLES`, `LEADERBOARD_TOP_N`, `LEADERBOARD_NEIGHBOURS`, `GUESS_POINTS`, `MOVE_TIER_POINTS`, `TRAIN_POINTS_PER_PUZZLE`, `DAYS_PER_WEEK`, the countdown tick interval, and the localStorage key all become named constants.
- `Literal[...]` for fixed sets (`board: Literal["points", "accuracy"]`, `visibility: Literal["public", "hidden", "guest"]`). Explicit return types everywhere. `Sequence[...]` for params that take lists of literals.
- Pydantic at the API boundary, TypedDict or frozen dataclasses internally.
- `ty check` must report zero errors. Suppress only with `# ty: ignore[rule]` plus a reason.
- Nesting depth ≤ 4 (`scripts/check_function_size.py app/ --fail-over-depth 4`; eslint `max-depth`). Cognitive complexity ≤ 15 is soft. `TrainScoreScreen` has no headroom.
- Never `asyncio.gather` on one `AsyncSession`. Run the two leaderboard queries sequentially.
- Time-dependent endpoints take `now_utc` from `dev_now_utc`, never `datetime.now()`.
- DB rules: FK + explicit `ondelete` (no new FK here); no native ENUM; a boolean column is plain `Boolean NOT NULL server_default false`.
- Sentry: `capture_exception` in non-trivial router `except` blocks, with `set_context("train", {...})`. No variables in error messages.
- Frontend: theme colors live in `theme.ts`; `data-testid` on every interactive element and major container; `text-sm` minimum; `isError` branch in every query render chain ("Failed to load …"); no duplicate Sentry captures for TanStack queries; `npm run build` before integrating shared types; knip-clean exports.
- Umami: register every new feature event in `trackFeature`'s registry; a handler whose whole effect is a DB-landing backend write stays un-evented; legacy `settings-*` events keep `trackEvent`.
- Changelog bullet under `## [Unreleased]` when the phase merges. Full pre-merge gate before the squash-merge.
- Do not plan a dev DB reset (`bin/reset_db.sh`); work against the existing dev DB.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Weekly per-user aggregates (points, puzzles, non-filler sums) | Database / Storage | API / Backend (repository) | One `GROUP BY` over an indexed window; ~100 rows out |
| ISO-week window, ranking, ties, slicing, pass target, display name | API / Backend (service, pure) | — | Viewer-specific re-ranking is trivial in Python, awkward in SQL; DB-free unit tests |
| Visibility policy (guest / hidden / public) | API / Backend | — | Must be server-enforced so others' ranks and rows never include hidden or guest users |
| Opt-out flag persistence | Database (`users.leaderboard_hidden`) | API (`PUT /users/me/profile`) | D-16: server-persisted, not localStorage |
| Countdown display | Browser / Client | API supplies `seconds_remaining` | The server owns "now" (dev clock); the client only ticks down from the server value |
| Tab memory | Browser / Client (localStorage) | — | D-09 |
| Score-screen rank change | API (`rank_without_session`) | Browser renders delta copy | Before and after must be computed at the same moment (D-12) |

## Standard Stack

### Core (all already installed, no changes)
| Library | Version (repo) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | `>=2.0.0` (pyproject) | `select()` aggregate with `FILTER` and `CASE` | Project ORM; `func.sum(...).filter(cond)` compiles to `FILTER (WHERE …)` [VERIFIED: compiled this session, see Code Examples] |
| Alembic | `>=1.13.0` | Add `users.leaderboard_hidden` and the `drill_solves` index | Project migration tool; head is `3b7e2f9c41a6` [VERIFIED: `uv run alembic heads`] |
| FastAPI + Pydantic v2 | `>=0.115.0` / `>=2.0.0` | `GET /train/leaderboard` response schema | Project stack |
| @tanstack/react-query | `^5.100.14` | `useTrainLeaderboard` query, invalidation | Project data layer; global `staleTime: 30_000` [VERIFIED: frontend/src/lib/queryClient.ts:68] |
| Python stdlib `datetime` | 3.14.3 | ISO-week bounds (`weekday()` Monday = 0) | [VERIFIED: `date(2026,10,5).weekday() == 0`, `date(2026,10,4).isocalendar().weekday == 7` run this session] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python ranking over SQL aggregates | SQL `RANK() OVER (ORDER BY points DESC)` | SQL needs separate variants for the hidden/guest would-be rank and the "without session" rank. Python handles both with one function and tests without a DB. Population is ~100 rows. |
| `PUT /users/me/profile` optional field | Dedicated `PUT /users/me/leaderboard-visibility` | The dedicated endpoint avoids the profile PUT's `current_strength` recompute (a few extra queries, rare toggle). The profile PUT reuses existing None-filter semantics and its response refreshes the very cache (`['userProfile']`) the Privacy card reads. Either is fine; the profile PUT adds no new route. |
| Adding the flag to `PUT /train/settings` | — | **Reject.** It is a full-replace body: every existing caller would 422 without the new key, and the column lives on `users`, not `train_settings`. |
| `ToggleGroup` for Points/Accuracy | `components/ui/tabs` (Radix Tabs) | CONTEXT names `toggle-group` as the D-07 asset and SettingsPanel already uses it. Tabs give `role=tab` semantics but need pointer events in browser UAT (project memory). Use `ToggleGroup type="single"` with `aria-label`. |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase. Every dependency is already in `pyproject.toml` or `frontend/package.json`.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 Train landing mount ─┐                       Score screen mount (session_id=S) ─┐
                      v                                                          v
        GET /api/train/leaderboard                 GET /api/train/leaderboard?session_id=S
                      │  (current_active_user, now_utc = dev_now_utc)            │
                      └────────────────────────────┬─────────────────────────────┘
                                                   v
                         week_window(now_utc) -> [Mon 00:00 UTC, next Mon 00:00 UTC)
                                                   │
                     ┌─────────────────────────────┴───────────────────────────┐
                     v                                                         v
     repo.fetch_week_aggregates(start, end)                 repo.fetch_session_contribution(
     drill_solves ⋈ users, solved_at in window,                viewer_id, S, start, end)
     GROUP BY user: points, puzzles,                         (only when session_id given;
     nf_points, nf_puzzles, names, is_guest, hidden          scoped to viewer_id → foreign S = 0 rows)
                     │                                                         │
                     └──────────────► service (pure Python) ◄──────────────────┘
                                     │
          split: visible_others = registered ∧ ¬hidden ∧ user≠viewer
                 viewer_entry     = viewer's aggregate (any visibility) or None
                                     │
          for board in (points, accuracy):
             metric(entry)  points: P          accuracy: floor(100·nfP / (3·nfN)), nfN ≥ 1
             rank_with    = 1 + #{others with metric > viewer metric}
             rank_without = same with (viewer − session contribution) [None if no entries left]
             ordered list = others ∪ {viewer row}, sort (metric desc, puzzles desc, name, id)
             slice: top 5 + viewer ±2 (+ gap marker)   pass target: nearest strictly-better row
                                     │
                                     v
           LeaderboardResponse {week_start, week_end, seconds_remaining,
                                points: Board, accuracy: Board}  (no user ids, no emails)
                                     │
               ┌─────────────────────┴──────────────────────┐
               v                                            v
   TrainLeaderboardCard (tabs, countdown,       TrainScoreRankLines ("Points board: #7 (up 3)",
   rows, viewer highlight, guest CTA)            "Accuracy: #4 (tentative)", guest "You'd be #7")

 Settings overlay ── LeaderboardPrivacyCard (Switch) ── PUT /api/users/me/profile {leaderboard_hidden}
                     reads useUserProfile().data       └─ onSuccess: setQueryData(['userProfile']),
                     (hidden for guests)                   invalidate ['train','leaderboard']
```

### Recommended Project Structure
```
app/
├── services/train_leaderboard.py              # NEW pure: constants, week_window, metrics, rank, slice, names
├── repositories/train_leaderboard_repository.py  # NEW: fetch_week_aggregates, fetch_session_contribution
├── routers/train.py                           # + GET /leaderboard
├── schemas/train.py                           # + Leaderboard* response models
├── schemas/users.py                           # + leaderboard_hidden on UserProfileResponse / UserProfileUpdate
├── routers/users.py                           # + pass leaderboard_hidden through GET/PUT profile
├── models/user.py                             # + leaderboard_hidden column
└── models/drill_solve.py                      # + Index ix_drill_solves_solved_at (partial)
alembic/versions/<ts>_<rev>_phase_230_leaderboard.py
tests/services/test_train_leaderboard.py        # NEW pure unit tests (no DB)
tests/services/test_train_score_parity.py       # NEW regex parity vs trainScore.ts
tests/repositories/test_train_leaderboard_repository.py  # NEW (unique ISO week per test)
tests/routers/test_train_leaderboard.py         # NEW HTTP (dependency_overrides[dev_now_utc])
frontend/src/
├── hooks/useTrainLeaderboard.ts                # NEW query hook, key ['train','leaderboard', sessionId?]
├── lib/trainLeaderboard.ts                     # NEW pure: countdown format, tab storage, rank-line copy
├── components/train/TrainLeaderboardCard.tsx   # NEW
├── components/train/TrainScoreRankLines.tsx    # NEW (keeps TrainScoreScreen under its complexity cap)
├── components/settings/LeaderboardPrivacyCard.tsx  # NEW
└── types/train.ts / types/users.ts             # + response types, leaderboard_hidden
```

### Pattern 1: Aggregate in SQL, rank in Python
**What:** One aggregate query returns per-user weekly totals. A pure function computes every rank the UI needs.
**When to use:** Any ranking that needs viewer-specific variants (hidden, guest, without-session) over a small population.
**Ranking rule (D-04):** competition ranking, `rank = 1 + count(others with strictly greater metric)`. Display order within equal metric: `puzzles DESC`, then a deterministic tiebreak (display name, then an internal key). The tiebreak is needed for stable React rendering and deterministic tests. It never changes the rank number.

### Pattern 2: Visible set + viewer re-insertion (D-06/D-13/D-14)
- `others` = entries where `not is_guest and not leaderboard_hidden and user_id != viewer_id`. Every rank on the board is computed against `others` only, so hidden users and guests never move anyone's rank.
- The viewer's own entry (public, hidden or guest) is inserted into `others` to compute their rank and neighbours. A public viewer is simply one of the visible entries. A hidden or guest viewer gets a private would-be row with `visibility` set, so the client labels it "Hidden from others" or "You (guest)".
- Do not return `user_id` for any row. Mark the viewer row with `is_viewer: true`.

### Pattern 3: "Without this session" (D-12)
`viewer_without = viewer_entry − session_contribution`, where the contribution is the sum over `drill_solves WHERE user_id = viewer AND session_id = S AND solved_at in window`. If `viewer_without.puzzles == 0` (Points) or `viewer_without.nf_puzzles == 0` (Accuracy), there is no before-rank and the client shows "#12 this week". Because `others` is unchanged, `rank_without` uses the same function. Scoping the contribution query by `user_id` makes a foreign `session_id` contribute zero rows, so `rank_without == rank` and nothing leaks (IDOR-safe).

### Pattern 4: Accuracy metric as a floored integer percent
Recommendation (discretion): rank on `floor(100 * nf_points / (3 * nf_puzzles))`, computed with integer arithmetic (`(100 * p) // (3 * n)`), the same flooring `displaySessionPercentage` uses on the client. Ranking on the shown number makes ties visible as ties (D-04 "ties share a rank"), puzzles-desc ordering then breaks them meaningfully, and there are no float-equality bugs. Ranking on the exact ratio would show "#3 89%" above "#4 89%", which reads as a bug. Users with `nf_puzzles == 0` have no Accuracy entry. **[ASSUMED: owner preference; low risk, confirm in plan-check]**

### Pattern 5: Countdown from a server-supplied remainder
The response carries `seconds_remaining = int((week_end - now_utc).total_seconds())`. The client stores `dataUpdatedAt` from TanStack and displays `seconds_remaining - (Date.now() - dataUpdatedAt)/1000`, ticking every 60 s (`COUNTDOWN_TICK_MS = 60_000`). Format: `≥1 day: "ends in 1d 4h"`, `≥1 h: "ends in 4h 12m"`, else `"ends in 12m"`. At ≤0 it invalidates `['train','leaderboard']` once. This automatically respects the dev clock and client clock skew, because the client never compares against its own wall clock for the week boundary.

### Pattern 6: Freshness
- Landing: `useTrainLeaderboard()` with key `['train','leaderboard']`, default staleTime. `returnToLanding()` in `Train.tsx` already remounts the landing, but the cached board is younger than 30 s after a session, so **invalidate `['train','leaderboard']` in `returnToLanding`** (or on score-screen mount) to force a refetch.
- Score screen: `useTrainLeaderboard({ sessionId })` with key `['train','leaderboard', sessionId]`, `staleTime: 0`. It fetches once on mount, after the final solve's response has been committed (the score screen only shows after `session_complete` on the solve response, so ordering is safe).
- No refetch after every solve: it would add load to the hot path and nothing on screen shows the board mid-session.
- Do NOT add rank data to `SolveResponse`. The solve endpoint is the hottest, most complex Train path, and Phase 211 pins its key set with an equality test (`test_solve_response_key_set_is_exactly_the_wire_contract`).

### Anti-Patterns to Avoid
- **Ranking on float ratios with `==`:** use integer percent or `fractions.Fraction`.
- **Using `move_quality` as points directly:** it relies on `DrillMoveQuality` member values equalling points, which that enum's docstring calls a readability convenience. Build the SQL `CASE` from the backend `MOVE_TIER_POINTS` mapping so the parity test actually guards the SQL.
- **`select(User)` in the aggregate:** `User.oauth_accounts` is `lazy="joined"`, so selecting the entity drags in a join and needs `.unique()`. Select columns only.
- **Keying the window on `drill_sessions.session_date`:** forbidden by D-02 (user-local day).
- **Hand-rolling "now":** `datetime.now()` in the service breaks dev-clock UAT and tests. Pass `now_utc` down.
- **Putting the Privacy card's state into `engineSettings` or Reset:** it is server state. `resetAllSettings()` must not touch it, and `isAtDefaults` must not include it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Now" for the week window | `datetime.now(UTC)` | `NowUtc` dependency (`app/routers/train.py:54`) | Dev-clock UAT, deterministic tests |
| Profile cache refresh after toggle | Manual refetch | `PUT /users/me/profile` response → `queryClient.setQueryData(['userProfile'], data)` | The response is the full `UserProfileResponse` |
| Guest CTA under the board | New buttons | `SignupAskActions` with a new `source` member `'train-leaderboard'` | Keeps `signup-cta` attribution per surface |
| Percent flooring | New rounding | Same `floor` rule as `displaySessionPercentage` (`trainScore.ts:117-120`) | Shown number never contradicts the ordering |
| Sentry for query errors | `captureException` in the hook | Global `QueryCache.onError` | Frontend CLAUDE.md forbids duplicates |
| Event vocabulary | New event name | Widen `'tab-switch'` target union | Registry test pins exactly 9 event names |

**Key insight:** every "hard" part (window, ties, hidden/guest re-insertion, before/after) is a ten-line pure function once the data is a list of per-user totals. Keep SQL boring.

## Runtime State Inventory

Not a rename/refactor phase. Omitted, except for one note: the new `users.leaderboard_hidden` column defaults to `false` for every existing row, so all registered users with solves this week appear as soon as the release deploys. This is intended (D-06 opt-out model). The Privacy-page line should ship in the same release.

## Common Pitfalls

### Pitfall 1: Accuracy rank change can go DOWN (contradicts D-12's premise)
**What goes wrong:** D-12 says the rank change "can only go up or stay the same". For Points that is true, because removing one's own solves can only lower one's points. For Accuracy, a bad session lowers pooled accuracy, so `rank_without_session` can be better than `rank`.
**How to avoid:** Decide the copy for a worse Accuracy rank. Recommendation: show only an improvement delta ("(up N)"), and otherwise the plain rank, consistent with the unchanged-rank rule and the motivational intent. See Open Question 1.
**Warning signs:** a test fixture with a 100% earlier session and a 33% current session yields `rank_without < rank`.

### Pitfall 2: Warm-up users barely accrue qualifying puzzles
**What goes wrong:** an 8-puzzle warm-up is 2 herrings + 6 sharp fillers (`train_repository.py:1765-1771`, `HERRING_SHARE: float = 0.25` at `train_pool.py:109`). Guests and zero-game registered users therefore gain about 2 non-filler puzzles per session. A user who solved 16 puzzles still reads "18 more puzzles to qualify". A filler-only user (dev user 44: 15 puzzles, 0 non-filler) has no Accuracy entry at all.
**How to avoid:** Copy must not imply "puzzles solved this week". Show the qualifier count as "N more puzzles to qualify" only (D-03 wording), and give the viewer with zero non-filler puzzles a specific line (e.g. "Not on this board yet"). Keep D-10's helper short; do not promise "20 puzzles" without qualification. Flag the effect to the owner in plan-check. It follows from locked D-01/D-03, not a bug.

### Pitfall 3: Global data + committed router tests → flaky ranks
**What goes wrong:** router tests commit through `_test_session_generator` (`tests/conftest.py:409-412`). Any test that writes `drill_solves` in "this week" pollutes every leaderboard assertion in the same worker DB.
**How to avoid:** repository and service tests pass an explicit `now_utc` in a far, unique ISO week per test (e.g. `2031-01-06`, `2031-01-13`, …) and insert `solved_at` inside it. Router tests override the clock with `app.dependency_overrides[dev_now_utc] = lambda: FIXED_NOW` (pop in `finally`), or monkeypatch `settings.ENVIRONMENT = "development"` and send `X-Dev-Clock-Offset-Minutes` (the existing pattern at `tests/routers/test_train.py:1285`). Assert ranks relative to the test's own users, never `entrant_count` totals across the DB. Clean up committed users in `finally`.

### Pitfall 4: Frontend tests without QueryClientProvider
**What goes wrong:** `TrainStartScreen.test.tsx` mocks `useTrainProgress`/`useUserProfile`/`useAuth`, `TrainScoreScreen.test.tsx` mocks `useTrainSettings`/`useTrainOnboarding`/`TrainReminderButton`, and `SettingsPanel.test.tsx` renders `<SettingsPanel />` bare and mocks `@/lib/analytics` as `{ trackEvent }` only (`SettingsPanel.test.tsx:14`). A new child that calls `useQuery`, or imports `trackFeature`, throws.
**How to avoid:** in those three files add `vi.mock('@/hooks/useTrainLeaderboard', …)` (or mock the card or line component). For SettingsPanel, mock `@/components/settings/LeaderboardPrivacyCard`, or wrap in a `QueryClientProvider` and mock `useUserProfile`. Give the new components their own test files with a real `QueryClient` (the `TrainStatsCard.test.tsx` pattern: mock `@/api/client`'s `trainApi` with `vi.importActual`).

### Pitfall 5: TrainScoreScreen complexity cap
**What goes wrong:** the file states its baseline is complexity 13 against a cap of 15 (`TrainScoreScreen.tsx:372-383`). Adding guest/hidden/tentative/delta branches inline breaks the soft gate and the file's own guard pattern.
**How to avoid:** render `<TrainScoreRankLines sessionId={…} isGuest={…} />` as one element under `train-score-total`. All branching lives in that component and a pure copy function (`rankLineCopy()` in `lib/trainLeaderboard.ts`), unit-tested on its own. `Train.tsx` must pass `trainSession.session.session_id` as a new prop.

### Pitfall 6: Stale "never score server-side" comments
**What goes wrong:** `app/schemas/train.py` `SolvedResult` docstring ("porting the formula server-side was considered and rejected") and `DrillMoveQuality`'s docstring ("nothing here should be used to compute a score directly") contradict D-01 once this lands.
**How to avoid:** amend both: the client stays the source of truth for per-session display; the leaderboard aggregate is a deliberate, parity-tested server port (point to the parity test). Also add a one-line note on `trainScore.ts`'s constants that a backend parity test pins them.

### Pitfall 7: Blank usernames
**What goes wrong:** the username columns are nullable `String(100)`. Only None is filtered on profile update (`user_repository.py:63-64`), so `''` or whitespace is possible from older paths. `lichess or chess_com or "Anonymous"` treats `''` correctly in Python, but `'  '` would render blank.
**How to avoid:** `display_name()` uses `.strip()` truthiness, with a unit test for `None`, `''`, `'  '`, lichess-only, chess.com-only and both.

### Pitfall 8: Pass target picks a tied user
**What goes wrong:** if the row directly above the viewer has the same points, "1 point to pass X" is technically true but does not change the viewer's rank number (competition ranking).
**How to avoid:** the target is the nearest row with a strictly greater metric, `N = their_points − viewer_points + 1`. No target at rank 1. Recommendation: Points board only (discretion). The Accuracy board shows the qualifier line instead (an accuracy gap is not actionable).

### Pitfall 9: Week boundary off-by-one
**What goes wrong:** using `<=` on `week_end` double-counts a solve at exactly Monday 00:00:00 UTC. A naive `now_utc.date()` on a non-UTC-aware datetime shifts the week.
**How to avoid:** half-open `[start, end)`, `now_utc.astimezone(datetime.UTC)` before taking `.date()`. Unit tests at Sunday 23:59:59.999999 and Monday 00:00:00 UTC, plus a session spanning the deadline (D-02).

## Code Examples

### Week window (pure)
```python
# app/services/train_leaderboard.py
DAYS_PER_WEEK = 7

def week_window(now_utc: datetime.datetime) -> tuple[datetime.datetime, datetime.datetime]:
    """ISO week [Monday 00:00 UTC, next Monday 00:00 UTC) containing now_utc (D-02)."""
    today = now_utc.astimezone(datetime.UTC).date()
    monday = today - datetime.timedelta(days=today.weekday())  # Monday == 0
    start = datetime.datetime.combine(monday, datetime.time.min, tzinfo=datetime.UTC)
    return start, start + datetime.timedelta(days=DAYS_PER_WEEK)
```

### Aggregate query (verified: compiled with the PostgreSQL dialect and run read-only on the dev DB this session)
```python
# app/repositories/train_leaderboard_repository.py
from sqlalchemy import case, func, select
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.user import User
from app.services.train_leaderboard import GUESS_POINTS, MOVE_TIER_POINTS

_POINTS = case((DrillSolve.correct_guess.is_(True), GUESS_POINTS), else_=0) + case(
    (DrillSolve.move_quality == int(DrillMoveQuality.GOOD), MOVE_TIER_POINTS["good"]),
    (DrillSolve.move_quality == int(DrillMoveQuality.INACCURACY), MOVE_TIER_POINTS["inaccuracy"]),
    else_=MOVE_TIER_POINTS["wrong"],
)
_NON_FILLER = DrillSolve.source != int(DrillSource.SHARP_FILLER)

stmt = (
    select(
        DrillSolve.user_id,
        func.sum(_POINTS).label("points"),
        func.count().label("puzzles"),
        func.coalesce(func.sum(_POINTS).filter(_NON_FILLER), 0).label("nf_points"),
        func.count().filter(_NON_FILLER).label("nf_puzzles"),
        User.lichess_username, User.chess_com_username, User.is_guest, User.leaderboard_hidden,
    )
    .join(User, User.id == DrillSolve.user_id)
    .where(DrillSolve.solved_at >= week_start, DrillSolve.solved_at < week_end)
    .group_by(DrillSolve.user_id, User.id)  # PK functional dependency allows the User columns
)
```
Compiled SQL (with literal binds) was `... sum(CASE WHEN (drill_solves.correct_guess IS true) THEN 1 ELSE 0 END + CASE WHEN (drill_solves.move_quality = 2) THEN 2 WHEN (drill_solves.move_quality = 1) THEN 1 ELSE 0 END) ... FILTER (WHERE drill_solves.source != 2) ... GROUP BY drill_solves.user_id, users.id`. On dev it returned 3 users (incl. one guest, one filler-only) in 0.4 ms. `solved_at IS NOT NULL` is implied by the range predicate. Legacy pre-SEED-119 rows (NULL `move_quality`) fall to `else_` = 0, but they predate every possible current week anyway. Dev data: 0 solved rows with NULL `correct_guess`/`move_quality`. The session-contribution query is the same select, restricted with `DrillSolve.user_id == viewer_id, DrillSolve.session_id == session_id` and without the users join.

### Ranking core (pure, sketch)
```python
@dataclass(frozen=True)
class Entry:
    key: int            # internal only, never serialized
    name: str
    metric: int         # points, or floored accuracy percent
    puzzles: int        # puzzles for points; nf_puzzles for accuracy
    is_viewer: bool

def rank_of(metric: int, others: Sequence[Entry]) -> int:
    return 1 + sum(1 for e in others if e.metric > metric)

def ordered(entries: Sequence[Entry]) -> list[Entry]:
    return sorted(entries, key=lambda e: (-e.metric, -e.puzzles, e.name.casefold(), e.key))
```
`slice_board(ordered_list, viewer_index)`: `top = L[:TOP_N]`. If `viewer_index is None`, return top only. Otherwise `window = L[max(0, v-NEIGHBOURS): v+NEIGHBOURS+1]`. If `window` starts at index ≤ `TOP_N`, return the contiguous `L[:max(TOP_N, v+NEIGHBOURS+1)]`, else `top + gap + window`. Unit-test v = 0, 4, 5, 6, 7, 8, last, and lists shorter than 5.

### Parity test (pattern from `tests/services/test_opening_insights_arrow_consistency.py:38-52`)
```python
_TRAIN_SCORE_TS = Path(__file__).resolve().parents[2] / "frontend/src/lib/trainScore.ts"

def _extract_int(name: str) -> int:
    m = re.search(rf"export\s+const\s+{name}\s*=\s*(\d+)\s*;", _TRAIN_SCORE_TS.read_text())
    assert m, f"could not find export const {name} in trainScore.ts"
    return int(m.group(1))

def _extract_move_tier_points() -> dict[str, int]:
    text = _TRAIN_SCORE_TS.read_text()
    block = re.search(r"MOVE_TIER_POINTS[^=]*=\s*\{(.*?)\}", text, re.S)
    assert block
    return {k: int(v) for k, v in re.findall(r"(\w+)\s*:\s*(\d+)", block.group(1))}

def test_guess_points_match_frontend() -> None:
    assert _extract_int("GUESS_POINTS") == GUESS_POINTS
def test_points_per_puzzle_match_frontend() -> None:
    assert _extract_int("TRAIN_POINTS_PER_PUZZLE") == TRAIN_POINTS_PER_PUZZLE
def test_move_tier_points_match_frontend() -> None:
    assert _extract_move_tier_points() == dict(MOVE_TIER_POINTS)
def test_move_quality_enum_values_match_tier_points() -> None:
    # guards the CASE mapping against an enum renumbering
    assert {DrillMoveQuality.GOOD: 2, DrillMoveQuality.INACCURACY: 1, DrillMoveQuality.WRONG: 0} == {
        DrillMoveQuality.GOOD: MOVE_TIER_POINTS["good"],
        DrillMoveQuality.INACCURACY: MOVE_TIER_POINTS["inaccuracy"],
        DrillMoveQuality.WRONG: MOVE_TIER_POINTS["wrong"],
    }
```
Mutation-prove it (project memory): flip `good: 2` to `good: 3` in a scratch copy, confirm the test fails, revert.

### Migration (mirror `alembic/versions/20260927_140000_3b7e2f9c41a6_drill_sessions_entered_at.py`)
```python
revision = "<new>"
down_revision = "3b7e2f9c41a6"

def upgrade() -> None:
    op.add_column("users", sa.Column("leaderboard_hidden", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_index("ix_drill_solves_solved_at", "drill_solves", ["solved_at"], unique=False,
                    postgresql_where=sa.text("solved_at IS NOT NULL"))

def downgrade() -> None:
    op.drop_index("ix_drill_solves_solved_at", table_name="drill_solves")
    op.drop_column("users", "leaderboard_hidden")
```
Model side: `leaderboard_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)` (same shape as `beta_enabled`, `user.py:320-325`), plus `Index("ix_drill_solves_solved_at", "solved_at", postgresql_where=text("solved_at IS NOT NULL"))` in `DrillSolve.__table_args__`, so autogenerate stays drift-free. The index is a judgement call. Today the table is tiny (dev: 186 rows / 88 kB; prod roughly 1.5k solves/week plus pre-materialized unsolved rows [ASSUMED from SEED-185 counts]), so a sequential scan is milliseconds. But the table grows without bound and the query runs on every Train landing view. The index is one line, and the extra write cost (each solve UPDATE now touches an index) is negligible at this volume.

### Frontend query hook
```ts
export const TRAIN_LEADERBOARD_QUERY_KEY = ['train', 'leaderboard'] as const;

export function useTrainLeaderboard(options?: { sessionId?: number }) {
  const sessionId = options?.sessionId;
  return useQuery<TrainLeaderboardResponse>({
    queryKey: sessionId === undefined ? TRAIN_LEADERBOARD_QUERY_KEY : [...TRAIN_LEADERBOARD_QUERY_KEY, sessionId],
    queryFn: () => trainApi.getLeaderboard(sessionId),
    staleTime: sessionId === undefined ? undefined : 0,
  });
}
```

## Verified In-Repo Values (verbatim)

- `DrillSource` [VERIFIED: app/models/drill_solve.py:86-92]: `SR_ITEM = 0`, `RED_HERRING = 1`, `SHARP_FILLER = 2`. CHECK constraint `"source IN (0, 1, 2)"` (line 123).
- `DrillMoveQuality` [VERIFIED: app/models/drill_solve.py:102-115]: `WRONG = 0`, `INACCURACY = 1`, `GOOD = 2`.
- `drill_solves` columns used [VERIFIED: app/models/drill_solve.py:138, 160, 164, 170, 173-175]: `user_id` (FK `users.id` `ondelete="CASCADE"`), `source: Mapped[int] = mapped_column(SmallInteger, nullable=False)`, `correct_guess: Mapped[bool | None]`, `move_quality: Mapped[int | None]`, `solved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`. Indexes present on dev [VERIFIED: `\d drill_solves`]: only `drill_solves_pkey (session_id, "position")` and `uq_drill_solves_session_puzzle (session_id, game_id, ply)`. No `solved_at` or `user_id` index.
- Frontend scoring [VERIFIED: frontend/src/lib/trainScore.ts:23-27, 46, 58]: `export const MOVE_TIER_POINTS: Record<TrainMoveTier, number> = { good: 2, inaccuracy: 1, wrong: 0, };`, `export const GUESS_POINTS = 1;`, `export const TRAIN_POINTS_PER_PUZZLE = 3;`.
- Users [VERIFIED: app/models/user.py:305-306, 316, 320-325]: `chess_com_username: Mapped[str | None] = mapped_column(String(100), nullable=True)`, `lichess_username: Mapped[str | None] = mapped_column(String(100), nullable=True)`, `is_guest: Mapped[bool] = mapped_column(default=False, server_default=text("false"))`, `beta_enabled` as `Boolean, nullable=False, server_default=text("false"), default=False`.
- Dev clock [VERIFIED: app/core/dev_clock.py:439, 447; app/routers/train.py:54]: `DEV_CLOCK_OFFSET_HEADER = "X-Dev-Clock-Offset-Minutes"`, `def dev_now_utc(request: Request) -> datetime.datetime:`, `NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]`.
- Profile update semantics [VERIFIED: app/schemas/users.py:82-86; app/repositories/user_repository.py:63-64]: `chess_com_username: str | None = None`, `lichess_username: str | None = None`; `updates = {k: v for k, v in data.items() if v is not None}`. Adding `leaderboard_hidden: bool | None = None` is backward compatible (`False` is not `None`, so it is applied). No frontend caller of `PUT /users/me/profile` exists today [VERIFIED: grep `me/profile` in frontend/src: only GET in useUserProfile.ts:9 and Home.tsx:760].
- Alembic head [VERIFIED: `uv run alembic heads`]: `3b7e2f9c41a6 (head)`.
- Analytics registry [VERIFIED: frontend/src/lib/analytics.ts:251, 376, 391-401]: `export const ANALYSIS_TAB_IDS = ['moves', 'eval', 'human', 'flawchess', 'stats'] as const;`, `'tab-switch': { target: AnalysisTabId };`, and exactly 9 names in `FEATURE_EVENT_NAME_SET`. The test `defines exactly 9 well-formed event names` (`analytics.test.ts:231`) and the kebab-slug list test (`:254-269`) must be extended for any new target const.
- `SignupAskSource` [VERIFIED: frontend/src/components/train/SignupAskActions.tsx:28]: `export type SignupAskSource = 'train-score' | 'import-promo' | 'train-landing';`.
- Query keys [VERIFIED: useTrainProgress.ts, useTrainSettings.ts:23, useUserProfile.ts:7]: `['train', 'progress']`, `['train', 'settings']`, `['userProfile']`.
- Warm-up mix [VERIFIED: app/services/train_pool.py:109; app/repositories/train_repository.py:1765-1771]: `HERRING_SHARE: float = 0.25`; "an 8-puzzle all-filler session is now 2 herrings + 6 sharp".

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Scoring only client-side (`trainScore.ts` sole source) | Client for per-session display + server aggregate for the leaderboard, parity-pinned | This phase (D-01) | Update the two docstrings (Pitfall 6) |
| Settings are localStorage-only (Phase 228) | First server-backed setting in the panel | This phase (D-16) | Separate card, outside Reset, hidden for guests |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rank Accuracy on the floored integer percent (visible ties) rather than the exact ratio | Pattern 4 | Low: a different but defensible ordering; easy to swap the metric function |
| A2 | No delta shown when the Accuracy rank got worse | Pitfall 1 / OQ1 | Medium: owner may prefer an honest "(down 2)" |
| A3 | Prod `drill_solves` is small enough that the index is optional; recommended anyway | Migration | Low: index or not, the query stays fast at current volume |
| A4 | The opt-out toggle gets NO Umami event (DB-known per frontend/CLAUDE.md) | Umami | Low: the owner may want toggle history; CONTEXT listed it as discretion |
| A5 | Pass target on the Points board only | Pitfall 8 | Low: discretion item |
| A6 | Leaderboard card also renders in the `exhausted` empty landing branch (after its `TrainStreakCard`) | Integration | Low: CONTEXT names only the completed/default branches; a user with no puzzles left may still be ranked this week |

## Open Questions

> **Resolved by owner 2026-10-03 (see CONTEXT.md D-18, D-19):** Q1 → plain rank with no delta when
> the Accuracy rank is unchanged or worse, never "(down N)". Q3 → qualifier stays non-filler as
> locked; copy must not imply all solves count. Q2 follows the frontend/CLAUDE.md rule (no event for
> the toggle).

1. **Accuracy rank that worsens after a session (D-12 premise does not hold for Accuracy).**
   - What we know: Points `rank_without ≥ rank` always. Accuracy can go either way.
   - Recommendation: show "(up N)" only when it improved; otherwise the plain "#k" (tentative marker still applies). Raise in plan-check as a one-line confirmation.
2. **Umami for the opt-out toggle.**
   - What we know: frontend/CLAUDE.md says a handler whose whole effect is a DB-landing backend write stays un-evented. CONTEXT lists an event as discretion.
   - Recommendation: no event for the toggle. Track tab switches via a widened `'tab-switch'` target (`LEADERBOARD_TAB_IDS = ['leaderboard-points', 'leaderboard-accuracy']`); the tab lives in localStorage, not the URL, so D-02 of Phase 229 allows it.
3. **Qualifier copy given the filler-heavy warm-ups (Pitfall 2).** Recommendation: keep "N more puzzles to qualify" and make D-10's helper not count fillers implicitly ("20+ puzzles to qualify, warm-up puzzles excluded" or similar). UI copy is the planner's or UI-spec's call.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev DB (Docker) | Migration, repo tests | ✓ | postgres:18-alpine (`flawchess-dev-db-1`) | — |
| uv / Python | Backend | ✓ | Python 3.14.3 | — |
| Node | Frontend build/tests | ✓ | v24.19.0 | — |
| Alembic | Migration | ✓ | head `3b7e2f9c41a6` | — |

**Missing dependencies:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend); vitest 5 + Testing Library (frontend) |
| Config file | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block |
| Quick run command | `uv run pytest tests/services/test_train_leaderboard.py tests/services/test_train_score_parity.py -x` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm test -- --run )` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Constants equal trainScore.ts; enum ↔ tier points | unit (regex parity) | `uv run pytest tests/services/test_train_score_parity.py -x` | ❌ Wave 0 |
| D-01 | Points = guess + tier; accuracy excludes SHARP_FILLER; unsolved rows ignored | repo integration (unique week) | `uv run pytest tests/repositories/test_train_leaderboard_repository.py -x` | ❌ Wave 0 |
| D-02 | Monday 00:00 boundary, Sunday 23:59:59.999999, deadline-spanning session splits; `now_utc` from dev clock | unit + router | `uv run pytest tests/services/test_train_leaderboard.py -k window -x`; router test overriding `dev_now_utc` | ❌ Wave 0 |
| D-03 | <20 non-filler = tentative + `puzzles_to_qualify`; still ranked | unit | `... -k qualify` | ❌ Wave 0 |
| D-04 | 1,1,1,4 ranks; puzzles-desc within tie; top 5 + ±2 slicing incl. overlap; pass target = nearest strictly better | unit | `... -k "rank or slice or pass_target"` | ❌ Wave 0 |
| D-05/D-15 | Name precedence; blank/whitespace → "Anonymous" | unit | `... -k display_name` | ❌ Wave 0 |
| D-06/D-13 | Hidden user absent from others' rows and ranks; hidden viewer gets would-be row `visibility="hidden"` | unit + router | `... -k hidden`; `tests/routers/test_train_leaderboard.py -k hidden` | ❌ Wave 0 |
| D-14 | Guest never in others' boards; guest viewer ghost row `visibility="guest"` | unit + router | `... -k guest` | ❌ Wave 0 |
| D-12 | `rank_without_session` correct; foreign session id → no effect (IDOR); first session of week → null | unit + router | `... -k without_session` | ❌ Wave 0 |
| D-16 | `PUT /users/me/profile {leaderboard_hidden}` round-trips; omitted field leaves it unchanged; GET exposes it | router | `uv run pytest tests/test_users_router.py -k leaderboard -x` (extend existing) | ✅ extend |
| D-16 | Migration up/down clean | template auto-refresh on head change | `uv run alembic upgrade head` + full suite | ✅ |
| Security | Response carries no `user_id`/email for any row | router key-set equality test | `tests/routers/test_train_leaderboard.py -k key_set` | ❌ Wave 0 |
| D-07/D-08 | Card after streak card, before stats card, in completed + default branches | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ extend |
| D-09 | Tab persisted; corrupt/throwing localStorage falls back to Points | unit | `npx vitest run src/lib/__tests__/trainLeaderboard.test.ts` | ❌ Wave 0 |
| D-10 | Label "Accuracy" + helper, no "skill" string | component | `npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ❌ Wave 0 |
| D-11/D-12/D-17 | Line copy: "(up 3)", plain rank, "#12 this week", "(tentative)", guest "You'd be #7" | unit (pure copy fn) + component | `npx vitest run src/components/train/__tests__/TrainScoreRankLines.test.tsx` | ❌ Wave 0 |
| D-13/D-14 | "Hidden from others" / "You (guest)" labels; guest `SignupAskActions source="train-leaderboard"` | component | TrainLeaderboardCard test | ❌ Wave 0 |
| D-16 | Privacy card hidden for guests; Reset does not change it; `isAtDefaults` ignores it | component | `npx vitest run src/components/settings/__tests__/` | ✅ extend + ❌ new |
| Umami | `tab-switch` fires on user tab change only (not mount/restore); registry tests updated | component + unit | `npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ extend |
| Countdown | Formatting at 1d4h / 4h12m / 12m / ≤0 triggers one invalidate | unit | `npx vitest run src/lib/__tests__/trainLeaderboard.test.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick command for the touched layer (backend pure tests, or the touched vitest file).
- **Per wave merge:** `uv run pytest tests/services tests/repositories/test_train_leaderboard_repository.py tests/routers/test_train_leaderboard.py -x` + `cd frontend && npm test -- --run src/components/train src/components/settings src/lib`.
- **Phase gate:** the full CLAUDE.md pre-merge gate (ruff format/check, ty ×2, function-size gate, `pytest -n auto -x`, `npm run lint && npm run build && npm test -- --run && npm run knip`). Run the full serial suite once before release (project memory: `-n auto` green ≠ serial CI green).

### Wave 0 Gaps
- [ ] `tests/services/test_train_leaderboard.py`: pure window/rank/slice/name/qualifier/without-session tests
- [ ] `tests/services/test_train_score_parity.py`: regex parity with trainScore.ts
- [ ] `tests/repositories/test_train_leaderboard_repository.py`: unique-ISO-week fixtures (e.g. weeks in 2031), filler exclusion, guest/hidden flags, session contribution scoping
- [ ] `tests/routers/test_train_leaderboard.py`: auth 401, guest 200, `dependency_overrides[dev_now_utc]`, key-set equality, foreign `session_id`
- [ ] `frontend/src/lib/__tests__/trainLeaderboard.test.ts`, `components/train/__tests__/TrainLeaderboardCard.test.tsx`, `TrainScoreRankLines.test.tsx`, `components/settings/__tests__/LeaderboardPrivacyCard.test.tsx`
- [ ] Mocks added to `TrainStartScreen.test.tsx`, `TrainScoreScreen.test.tsx`, `SettingsPanel.test.tsx` (Pitfall 4)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (inherit) | `current_active_user` on `GET /train/leaderboard`; guests are authenticated users |
| V3 Session Management | no | unchanged |
| V4 Access Control | yes | Viewer id only from `current_active_user.id`; `session_id` query param resolved only with `user_id = viewer` (a foreign id contributes 0 rows); flag writable only for self via `/users/me/profile` |
| V5 Input Validation | yes | Pydantic: `session_id: int \| None` query (FastAPI 422 on non-int), `leaderboard_hidden: bool \| None` |
| V6 Cryptography | no | — |
| V8 Data Protection / Privacy | yes | Response exposes only display name, rank, points/percent, puzzle counts; no user ids, emails, guest rows or hidden users to others; opt-out + Privacy page disclosure |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Enumerating internal user ids via board rows | Information disclosure | Never serialize `user_id`; key rows client-side by list index |
| Hidden user leaked through neighbour rows or ranks | Information disclosure | Exclude hidden from `others` before ranking/slicing; test that a hidden user's name never appears for another viewer |
| Guest data shown to others | Information disclosure | `is_guest` excluded from `others`; ghost row only for the guest themself |
| IDOR via `session_id` | Elevation / disclosure | Contribution query filters `user_id = viewer` |
| Impersonation by typed username | Spoofing | ACCEPTED RISK (D-05); do not mitigate |
| Score inflation by client-asserted move tier | Tampering | Pre-existing accepted residual (D-04 of Phase 211: off-key tiers are client-asserted); leaderboard inherits it, no change |
| Board polling load | DoS | Cheap indexed aggregate, TanStack staleTime; no polling interval |

## Sources

### Primary (HIGH confidence)
- Codebase files read this session: `app/models/{drill_solve,drill_session,user}.py`, `app/core/dev_clock.py`, `app/routers/{train,users}.py`, `app/schemas/{train,users,auth}.py`, `app/repositories/{train_repository,user_repository}.py` (relevant ranges), `app/services/train_pool.py:109,1085-1102`, `alembic/versions/20260927_140000_3b7e2f9c41a6_*.py`, `alembic/versions/20260917_172819_feab8324235d_*.py`, `tests/conftest.py:385-600`, `tests/routers/test_train.py` header, `tests/repositories/test_train_repository.py` header, `tests/services/test_opening_insights_arrow_consistency.py`
- Frontend files read: `lib/trainScore.ts`, `lib/analytics.ts`, `lib/__tests__/analytics.test.ts:200-290`, `components/settings/SettingsPanel.tsx`, `components/settings/__tests__/SettingsPanel.test.tsx` header, `components/train/{TrainStartScreen,TrainScoreScreen,TrainStatsCard,TrainStreakCard,SignupAskActions}.tsx`, `pages/{Train,Privacy}.tsx`, `hooks/{useUserProfile,useTrainSettings,useTrainProgress}.ts`, `api/client.ts` trainApi, `types/users.ts`, `frontend/CLAUDE.md`
- Dev DB (read-only): `\d drill_solves`, aggregate run + EXPLAIN ANALYZE (0.4 ms, seq scan, 186 rows)
- SQLAlchemy compile of the proposed statement (PostgreSQL dialect)

### Secondary (MEDIUM confidence)
- `../../seeds/closed/SEED-185-weekly-train-leaderboards.md` prod evidence (population sizes, filler counts): owner-reported, not re-queried (no prod access from this agent)

### Tertiary (LOW confidence)
- Prod `drill_solves` total row count: not observed; inferred from SEED-185 weekly numbers

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new packages; all APIs compiled or run)
- Architecture: HIGH (integration points read; query verified on dev)
- Pitfalls: HIGH for test/complexity/docstring pitfalls (read in code); MEDIUM for the Accuracy rank-direction copy decision (owner input needed)

**Research date:** 2026-10-03
**Valid until:** 2026-11-02 (stable internal codebase; re-check the Alembic head before writing the migration)
