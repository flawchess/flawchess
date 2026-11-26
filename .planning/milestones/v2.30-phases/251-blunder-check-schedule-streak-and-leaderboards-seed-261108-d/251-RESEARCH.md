# Phase 251: Blunder-Check Schedule, Streak and Leaderboards - Research

**Researched:** 2026-11-18
**Domain:** In-repo extension: Train streak machine, schedule settings, puzzle/blunder-check session lifecycle, weekly leaderboards and medals, Today page (React)
**Confidence:** HIGH for the code map and constraints (read this session); MEDIUM for the recommended designs of the open discretion areas (reasoned from code, not yet exercised)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-01 to D-17 are owner decisions carried from SEED-261108-dk0 ("Phase 251 decisions", 2026-11-18) and the roadmap.
The seed holds the reasoning; do not re-open them. D-18 to D-25 come from this discussion.

#### Carried forward: schedule and streak
- **D-01: Serve-once.** A window is shown to a user once and never re-served (250-CONTEXT D-17). No review queue,
  no mastered or parked states for blunder check.
- **D-02: Both modes are required for the streak.** On a scheduled day the streak ticks when every mode with a
  session size above 0 is complete. A mode at 0 is not part of the day.
- **D-03: Default blunder-check session size is 6 for all users,** existing ones included, from launch.
  — **Reversibility:** costly — it changes what every existing streak holder must do on launch day; walking it back
  after streaks were lost cannot restore them.
- **D-04: Session size is changeable anytime, per mode, 0 allowed.** The set-to-0-on-a-lazy-day loophole is
  accepted. "Applies from the next scheduled day" was rejected.
- **D-05: Never both modes at 0.** The slider of the last active mode stops at its minimum, with a hint to untick
  days for a break.
- **D-06: Resizing while a blunder-check session is open:**
  - reduced to at or below the windows already done: the session completes now and counts as done;
  - reduced but above the windows already done: the session shortens;
  - increased: the session extends, unless it is already complete for today (then it applies from the next session);
  - set to 0: the session closes, the mode is no longer required today, points already earned stay;
  - a completed session never reopens, so an earned tick cannot be taken back.
- **D-07: Schema.** `train_settings.puzzles_per_session` (CHECK `BETWEEN 1 AND 50`, UI slider 3 to 30) is relaxed to
  allow 0. Blunder check gets its own column and range. The level (D-16) is a nullable column on `train_settings`.
  — **Reversibility:** one-way — a migration relaxes a CHECK and adds columns; once rows hold 0 the old constraint
  cannot be restored without rewriting them.

#### Carried forward: Today page
- **D-08: Layout is sketch 014 variant B.** One Today card with the flame, the freeze meter and a launcher row per
  mode (name, red pending badge, Start / Resume, checkmark when done, "Turn on" when off). The rows are the streak
  checklist. Below: one collapsed row per mode (pitch, "How it works", level picker, session-size slider), then the
  shared schedule row. Desktop: Today card left, settings rows right.
- **D-09: Row states:** pending (badge, Start), in progress (badge with remaining count, Resume), done today
  (checkmark and points earned, no badge), off (muted, one-line pitch, "Turn on").
- **D-10: "How it works" auto-collapses** after the user's first completed session in that mode.
- **D-11: Subnav is Today / Leaderboard / Archive.** The Blunder Check tab is removed.
- **D-12: Score-screen hand-off.** After finishing one mode, the primary button continues with the other mode if
  it is still pending.
- **D-13: Nav badge = sum of both pending counts.** Blunder check has no due queue: its pending count is today's
  configured count minus what is done, and nothing on an unscheduled day.

#### Carried forward: leaderboards, cooldown, guests
- **D-14: Separate boards per mode, no merged Points board.** The leaderboard card gets a Puzzles / Blunder check
  switch, each side with its Points and Score % boards. New `train_weekly_standings.board` keys run through the
  existing finalization and medal code. Thin first-week podiums are accepted.
  — **Reversibility:** one-way — widens the `board` CHECK and writes finalized standings and medals under the new
  keys; published medals cannot be withdrawn.
- **D-15: One medal dialog per week** showing all of a user's medals, not one dialog per board.
- **D-16: Cross-mode cooldown.** A flaw served in either mode is ineligible in the other for
  `CROSS_MODE_COOLDOWN_DAYS`. One filter in each mode's selection.
- **D-17: Guests and users without rated games.** Guests play blunder check on foreign blunders only (the
  no-own-supply path, 250-CONTEXT D-15) and do not appear on leaderboards. A user without rated games picks
  Beginner / Intermediate / Advanced (about 1000 / 1500 / 2000 on the lichess-blitz-normalised scale; labels, not
  numbers; Intermediate preselected). The stored level replaces `DEFAULT_USER_LEVEL_ELO` for that user, is
  changeable later, and is ignored once the user has rated games.

#### Launch and first run (this discussion)
- **D-18: Everyone in one release.** The release that merges this phase removes the beta gate for registered
  users and guests together (backend `current_beta_user` dependency and the frontend tab gate). No beta soak and no
  staged guest launch. The owner chose this over the recommended beta soak, so the streak change reaches all streak
  holders on day one: test the tick rule accordingly (see Specifics).
  — **Reversibility:** costly — re-gating after launch strands open sessions, standings and streak days that
  already depended on blunder check.
- **D-19: Pitch line under the Blunder Check launcher row** until the user's first completed blunder-check
  session, then gone. Blunder Check row only, not the Puzzles row. This settles the open proposal in the seed and
  sketch 014.
- **D-20: The level question is a one-time step after the first Start.** A user without rated games (guests
  included) who taps Start for the first time gets one screen: the level choice with Intermediate preselected and
  the short how-it-works, then the drill. It is shown once. Everyone else, and that user from then on, goes straight
  from Start into the drill. The Phase 249 start screen is retired. The level stays editable in the collapsed
  Blunder Check row (D-08).
- **D-21: Launch notice** on the streak card ("Your streak now includes blunder check. Change the amount on the
  card."): shown to users who had a `train_settings` row before launch. It disappears when the user dismisses it,
  completes a blunder-check session, or changes the blunder-check amount, and at the latest 14 days after launch
  (a named constant). New users and guests never see it. Pair it with the Phase 255 feature-discovery dot.

#### Leaderboard details (this discussion)
- **D-22: Score % board minimum is 18 windows in the week** (three default sessions), a named constant next to
  `ACCURACY_QUALIFY_MIN_PUZZLES`.
- **D-23: Lifetime medal tally is per mode.** A row on a blunder-check board counts blunder-check medals only; a
  row on a puzzle board counts puzzle medals only (today's puzzle tally, which already combines the two puzzle
  boards, is unchanged).
- **D-24: The card opens on the last viewed mode, else Puzzles.** The last choice is remembered in the browser
  only (no server state). The blunder-check score screen links straight to the Blunder check boards.
- **D-25: Guests see the same thing as on the puzzle boards:** the public standings plus their private would-be
  row with the existing sign-up ask. Reuse the guest visibility path unchanged.

### Claude's Discretion
The owner did not select these two areas. The defaults below are orchestrator proposals, not owner decisions; the
planner may adjust them with the reasoning written down, and should surface any that turn out to be one-way.

- **Streak day edge cases:**
  - Puzzles with nothing to serve (`pool_state` `no_material` or `exhausted`) are not required that day, so blunder
    check alone ticks it. Blunder check always has foreign supply, so every user with blunder check on has material
    from their first day; check what that means for `pool_eligible_since` (a user with no puzzle material today
    resolves every day as neutral).
  - An open blunder-check session belongs to a session day and expires with it, like a puzzle session
    (`session_window` / `is_session_expired`). `blunder_check_sessions` has no day or expiry column today.
  - A freeze credit for an off-day or late completion (`credit_only`) follows the same "every required mode done"
    rule as a scheduled day.
  - The reminder fires while any required mode is pending (`has_completed_session_on` becomes "day complete").
  - Days already settled before launch stay as judged; the both-required rule applies from the first day judged
    after launch.
- **Cross-mode cooldown:** `CROSS_MODE_COOLDOWN_DAYS = 7`, keyed on the flaw. Whether a flaw that is active in the
  puzzle spaced-repetition ladder stays out of blunder check for the whole ladder or only for the cooldown after its
  last serve, and whether a blunder-check serve pushes back an already scheduled puzzle review, are open: research
  the puzzle due-date model first.
- Which windows count toward the weekly boards (windows from an unfinished or shortened session), tie-breaks on the
  blunder-check boards (mirror the puzzle rule: count desc, then name), and the layout of the single weekly medal
  dialog.
- Range and slider bounds for the blunder-check session size; the exact new `board` key names.
- Copy for the pitch line, "How it works", the level step and the launch notice (no "your move" on foreign games).

### Deferred Ideas (OUT OF SCOPE)
- Adaptive level from the catch rate (replaces the level question; needs its own tuning).
- Reusing the stored level for the lichess warm-up puzzles in personalized training and for the default bot strength.
- Single-retry spaced repetition (one retry after 3 to 4 weeks, "blind spots fixed" counter); `blunder_check_windows`
  keeps the history needed to backfill it.
- Progress without re-serving: catch-rate trend over the last N sessions, or the facepalm rate in real games
  (SEED-261114-iuv).
- Blunder-check windows in the Archive tab (not raised by the owner; the subnav keeps Archive for puzzles only).
</user_constraints>

<phase_requirements>
## Phase Requirements

No requirement IDs are mapped (TBD). Coverage contract = CONTEXT decisions D-01..D-25 plus the discretion areas.

| Decision | Research support (section) |
|----------|----------------------------|
| D-01 | Serve-once already enforced by `served_for_games` / `_unserved_qualifying_blunder_exists`; D-06 resize must not break it (Pattern 4) |
| D-02, D-03, D-04, D-05 | Streak rule redesign: "complete day" set fed into the unchanged `tick_days` (Pattern 1, 2); migration (Pattern 6) |
| D-06 | BC resize algorithm (Pattern 4) |
| D-07 | Migration shape (Pattern 6) |
| D-08..D-13 | Progress read-model per mode (Pattern 3), frontend map (Frontend Map) |
| D-14, D-15, D-22, D-23, D-24, D-25 | Leaderboard generalisation (Pattern 7) |
| D-16 | Cooldown filters (Pattern 5) |
| D-17, D-20 | Level column and foreign-source fallback (Pattern 8) |
| D-18 | Gate removal checklist (Pattern 9) |
| D-19, D-21 | Progress flags, notice column, feature-route step (Pattern 3, 6, 9) |
</phase_requirements>

## Summary

This phase is entirely in-repo: no new packages, no external services. Everything it extends exists and was read
this session. The load-bearing piece is the streak machine. `tick_days` / `_judge_one_day` in
`app/services/train_scheduler.py` are pure and take a list of "completed session dates"; today that list is
`drill_sessions.session_date` for completed puzzle sessions, and the **eager** tick
(`train_repository._apply_completion_tick`, called from `record_solve`) settles a scheduled day as `fulfilled` the
moment a puzzle session completes. Under D-02 that eager call is now wrong: it must fire only when the **whole day**
becomes complete. The cleanest change keeps `tick_days` and `_judge_one_day` byte-for-byte (the SHIELD_CAP
divergence gate stays green) and changes only what the callers feed them: a set of *complete days* computed from both
session tables and the current per-mode sizes, plus one shared eager entry point called on every event that can
complete a day (puzzle session completes, BC session completes, BC resized at or below done, either mode set to 0).

Blunder-check sessions need a session day: `blunder_check_sessions` has only `started_at`/`completed_at` and
`status IN ('open','completed')`. Add `session_date` and `expires_on` (backfilled), widen status with `'expired'`,
expire stale open sessions exactly like `expire_stale_sessions`, and add a completed-in-window guard so finishing
today's BC session yields the "done today" row instead of composing a new session on the next Start.

Leaderboards generalise with little code: `train_weekly_standings.board` is TEXT + CHECK, finalization writes one
marker per week for all boards, and the claim API is keyed on `(week_start, board)`. Add two board keys, a BC weekly
aggregate over `blunder_check_windows` (ended windows, `points_scored` / `points_possible`), and an entry builder
for Score %. The medal dialog already shows every unclaimed medal in one dialog; D-15 is mostly copy and grouping.

**Primary recommendation:** Keep the pure scheduler untouched, introduce one repository function
`complete_days_for(user, settings)` plus one eager `apply_day_completion(user, day, trigger)` used by both modes and
the settings PUT, and land the migration (two columns + relaxed CHECKs + BC session day columns + notice column +
board CHECK) as the first plan so every later plan builds on it.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Day-complete rule, streak tick, freeze credit | API / Backend (repository + pure scheduler) | — | Streak is server-settled and frozen; the client holds no copy of the arithmetic (TrainStreakCard docstring) |
| Per-mode session size, level, notice state | Database (`train_settings`) | API (`PUT /train/settings`) | Settings rows with CHECKs; never both 0 enforced in DB + Pydantic |
| BC session day, expiry, resize | API / Backend (`blunder_check_service` / repository) | Database | Windows are pre-inserted server-side; resize edits rows |
| Cross-mode cooldown | API / Backend (selection SQL in both modes) | Database (indexes) | One filter per mode's selection, server-side only |
| Per-mode pending counts, row states, nav badge number | API (`GET /train/progress`) | Browser (render only) | Badge visibility is server-computed today (`badge_visible`), no client schedule math |
| Weekly boards, finalization, medals | API / Backend (`train_leaderboard`, `train_medals`) | Database (`train_weekly_standings`) | Lazy finalization already server-side |
| Today card layout, rows, sliders, level step, hand-off | Browser / Client | API | Pure presentation over the progress/settings read models |
| Last viewed leaderboard mode | Browser (localStorage) | — | D-24: no server state |

## Standard Stack

No new libraries. The phase uses what the repo already pins (CLAUDE.md "Tech Stack"): FastAPI, SQLAlchemy 2 async +
asyncpg + Alembic, Pydantic v2, React 19 + TanStack Query + Tailwind, vitest, pytest (+ xdist locally).
`[VERIFIED: CLAUDE.md, frontend/package.json "test": "vitest run"]`

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages. **Packages removed:** none. **Flagged:** none.

## Architecture Patterns

### System Architecture Diagram

```
 Today card (browser)                                           Leaderboard card (browser)
   | Start/Resume puzzles     | Start/Resume BC   | settings PUT        | mode switch (localStorage)
   v                          v                   v                     v
 POST /train/sessions    POST /blunder-check/   PUT /train/settings   GET /train/leaderboard?mode=..
 POST .../solve          sessions, answers,       |                     |
   |                     finish                   | settle-before-mutate|  finalize_due_weeks (lazy,
   | puzzle selection      | BC selection         |  (OLD settings)     |   all 4 boards, one marker)
   |  - cooldown filter    |  - cooldown filter   | apply new sizes     |
   |    (BC served <7d)    |    (puzzle <7d)      | D-06 resize open BC |
   |                       |  - level fallback    |  session            |
   v                       v                      v                     v
 drill_sessions        blunder_check_sessions   train_settings        drill_solves | blunder_check_windows
   completed  ----+----  completed (session_date)    |                    \             /
                  |                                  |               weekly aggregates per board
                  v                                  v
        apply_day_completion(user, day, trigger)  <--+   (eager; fires only on "not complete -> complete")
                  |
                  v
        complete_days_for(user) -> set[date] ----> tick_days (pure, unchanged) -> _judge_one_day
                  ^                                       ^
                  |                                       |
        GET /train/progress (lazy settle, per-mode rows, pending sum, notice)   reminder job (day complete?)
```

### Recommended file touch map

```
app/models/train_settings.py          # new columns + relaxed CHECKs
app/models/blunder_check.py           # session_date, expires_on, status 'expired'
app/models/train_weekly_standing.py   # board CHECK widened
alembic/versions/<new>.py             # one migration, down_revision d1a7b3c5e261
app/services/train_scheduler.py       # new constants only (sizes, cooldown, notice days); tick logic unchanged
app/repositories/train_repository.py  # complete_days_for, apply_day_completion, settings, progress per mode,
                                      # puzzle cooldown filter, size-0 short-circuit
app/repositories/blunder_check_repository.py  # session day/expiry, completed-in-window, resize, cooldown set
app/services/blunder_check_service.py         # compose with count + offset, finish -> day completion
app/services/blunder_check_selection.py       # compose_windows(count, start_position), level fallback, cooldown
app/repositories/train_reminder_repository.py # has_completed_session_on -> day complete
app/services/train_leaderboard.py, train_medals.py, app/repositories/train_leaderboard_repository.py,
app/repositories/train_medals_repository.py   # BC boards
app/routers/blunder_check.py          # drop current_beta_user
app/schemas/train.py, app/schemas/blunder_check.py, app/schemas/feature_route.py
frontend/src/pages/Train.tsx, components/train/TrainSubnav.tsx, TrainStartScreen.tsx, TrainStreakCard.tsx,
TrainScheduleSettings.tsx, TrainLeaderboardCard.tsx, TrainScoreScreen.tsx, blunder-check/BlunderCheckTab.tsx (becomes
a host without its own start screen), medals/*, lib/trainRoute.ts, lib/trainLeaderboard.ts, lib/featureRoute.ts,
lib/analytics.ts, types/train.ts, App.tsx (nav badge)
```

### Pattern 1: Complete-day set feeding the unchanged tick machine (D-02)

**What:** `tick_days(snapshot, completed_session_dates, *, weekday_mask, today, pool_eligible_since)` is pure and
only uses the dates as a set membership test plus the week count and reset notice
`[VERIFIED: app/services/train_scheduler.py:565-649]`:

```python
    completed_set = set(completed_session_dates)
    ...
        elif day in completed_set:
            outcome = "fulfilled"
        else:
            outcome = "missed"
```

and `settle_streak_snapshot` builds the list from puzzle sessions only
`[VERIFIED: app/repositories/train_repository.py:990-995]`:

```python
    dates_result = await session.execute(
        select(DrillSession.session_date).where(
            DrillSession.user_id == user_id, DrillSession.status == "completed"
        )
    )
```

**Recommendation:** Replace that query with `complete_days_for(session, user_id, settings_row)` returning the dates
D on which *every required mode* has a completed session dated D. Pass it as `completed_session_dates` (rename the
parameter to `completed_days` in the docstring only if cheap). `tick_days` and `_judge_one_day` stay unchanged, so
the "exactly one SHIELD_CAP clamp" gate and all existing scheduler unit tests keep passing.

Rule (one pure helper, unit-testable, e.g. `train_scheduler.day_is_complete(puzzles_done, bc_done, *, puzzles_size, bc_size)`):

```python
# Source: recommendation; inputs are plain bools/ints so it lives beside tick_days (pure, no I/O)
def day_is_complete(*, puzzles_done: bool, bc_done: bool, puzzles_size: int, bc_size: int) -> bool:
    puzzles_ok = puzzles_size == 0 or puzzles_done
    bc_ok = bc_size == 0 or bc_done
    return puzzles_ok and bc_ok and (puzzles_done or bc_done)
```

The required set uses the **current** sizes at judging time. That is correct because `upsert_settings` already
settles every elapsed day with the OLD settings before applying new ones
`[VERIFIED: app/repositories/train_repository.py:482-484]`, so a past day is always judged with the sizes that were
in force when its window closed, and today is judged with whatever is in force at its end (the D-04 loophole, which
the owner accepted).

`current_week_completed` and `streak_reset_notice` come out of the same list, so the "N of M this week" caption
automatically counts complete days, not puzzle sessions.

### Pattern 2: One eager day-completion entry point (D-02, D-06, credit_only)

Today the eager path ticks on puzzle completion unconditionally
`[VERIFIED: app/repositories/train_repository.py:3548-3551]`:

```python
    fulfilled = is_scheduled_day(session_date, settings_row.weekday_mask) and (
        settled.settled_through is None or session_date > settled.settled_through
    )
    outcome: DayOutcome = "fulfilled" if fulfilled else "credit_only"
```

**Recommendation:** generalise `_apply_completion_tick` into `apply_day_completion(session, *, user_id, day,
now_utc, was_complete_before: bool)`:

1. `settle_streak_snapshot` first (unchanged order, see its docstring).
2. Compute `complete_now` for `day` via the Pattern 1 rule (both session tables, current sizes).
3. If `not complete_now` or `was_complete_before`: return without writing. **This guard is new and essential**:
   with two modes and resizable sizes, a day can see several completion events (puzzles done, then BC raised from 0
   and completed). Without it the second event hits the existing `credit_only` branch (because `settled_through`
   already equals `day`) and mints a free freeze.
4. Otherwise the existing fulfilled / credit_only choice and the existing compare-and-set writes, unchanged.

Callers:
- `record_solve` after `_mark_session_complete_if_done` returns True (replaces the current `_apply_completion_tick`
  call at train_repository.py:3886).
- BC `finish_session` after `complete_session` changes the row (the repository update must report whether it moved
  the row from `open` to `completed`, so a repeated finish is a no-op; it currently returns None).
- `upsert_settings` after the new sizes are written, for "today" (a mode set to 0, or BC shrunk to at or below done,
  can complete the day). Note: settle-before-mutate stays first; this call comes last.

`was_complete_before` is computed by the caller from the state before its own write (for the settings PUT: evaluate
the rule with the old sizes before the UPSERT; for a session completion: evaluate with that mode's "done" forced to
False unless another completed session of that mode already exists on `day`).

### Pattern 3: Progress read-model per mode (D-08, D-09, D-10, D-13, D-19, D-21)

`GET /train/progress` already commits a lazy settle and is what the nav badge and streak card read
`[VERIFIED: app/routers/train.py:321-356]`. Extend `ProgressSnapshot` / `TrainProgressResponse` with a nested
per-mode object instead of new flat fields (keeps the client typing clean):

```
modes: {
  puzzles:       { size, state: 'pending'|'in_progress'|'done'|'off', remaining, points_today, first_session_done },
  blunder_check: { size, state, remaining, points_today, first_session_done, needs_level, has_rated_games }
}
day_complete: bool
pending_count: int              # D-13: puzzles remaining + BC remaining, 0 on unscheduled days
blunder_check_notice: bool      # D-21
```

- BC `remaining`: open unexpired session -> `window_count - ended windows`; completed session in window -> 0;
  size 0 -> 0; unscheduled day with no open session -> 0; else `blunder_check_per_session` (D-13).
- Keep `waiting_count` and `badge_visible` with their current puzzle meaning so nothing else regresses; the nav
  (`App.tsx useNavIndicators`, which today shows `waiting_count` when `badge_visible`) switches to `pending_count`.
  Note the nav query is gated off for guests (`enabled: navUnlocked && profile != null && !profile.is_guest`), which
  matches today and needs no change.
- `first_session_done` drives D-10 (auto-collapse) and D-19 (pitch line): `EXISTS completed session` per mode, no
  new column.
- `needs_level` = no rated games AND `blunder_check_level IS NULL` (D-20: shown once; choosing writes the level, so it
  is never shown again).

### Pattern 4: BC session day, expiry and the D-06 resize

Current BC session header `[VERIFIED: app/models/blunder_check.py:89-116]`:

```python
        CheckConstraint("status IN ('open', 'completed')", name="ck_blunder_check_sessions_status"),
        CheckConstraint("window_count >= 1", name="ck_blunder_check_sessions_window_count"),
```

Windows are pre-inserted at composition ("One frozen window of a session, pre-inserted at composition time",
`[VERIFIED: app/models/blunder_check.py:119-120]`) and `compose_windows` always composes
`BLUNDER_CHECK_SESSION_WINDOWS` and renumbers from 0 `[VERIFIED: app/services/blunder_check_selection.py:555-590]`.

**Session day:** add `session_date DATE NOT NULL` and `expires_on DATE NOT NULL` (backfilled, see Pattern 6), set at
compose from `local_today(tz, now_utc)` and `session_window(today, mask)` exactly like puzzles. Add `'expired'` to
the status CHECK. At every BC entry point (compose, progress read) expire stale open sessions (`expires_on <= today`)
the same way `expire_stale_sessions` does for puzzles. Recommended extra: when expiring, DELETE the expired session's
windows that were never started (`started_at IS NULL`) so blunders that were never shown return to the pool (D-01
is "shown once"; composition happens only on Start, but an abandoned session's unseen tail would otherwise be burned
forever). Add a completed-in-window guard mirroring `completed_session_in_window` so a second Start on the same
session day returns the done state rather than composing (D-09 "done today").

**Resize algorithm (D-06)**, run inside `upsert_settings` after settle-before-mutate, against the user's open,
unexpired BC session. Let `ended` = windows with `outcome IS NOT NULL`, `n` = new size:

| Case | Action |
|------|--------|
| `n == 0` | status `'expired'` (not `'completed'`: the mode is simply not required today; if the user raises it again the same day a fresh session can be composed). Delete unstarted windows. Points already on ended windows stay. |
| `0 < n <= ended` | delete windows with `outcome IS NULL` and `started_at IS NULL`; set `window_count = ended`... then `complete_session` -> counts as done -> `apply_day_completion` |
| `ended < n < window_count` | delete unstarted windows with `position >= n`; `window_count = n` |
| `n > window_count`, session open | compose `n - window_count` more windows with positions continuing from `window_count` (needs `compose_windows(count=, start_position=)`), `window_count = n`; serve-once holds because `served_for_games` already sees this session's rows |
| session already completed in window | nothing (applies to the next session) |

Edge to decide in the plan: a window that is **started but not ended** (user left mid-window) in the `n <= ended`
case. Recommendation: leave it as is (it was shown, so it stays burned) and complete the session; it never gets an
outcome and is excluded from the boards (Pattern 7). Settings can only be edited from the Today page, never while a
drill is on screen, so this only happens after an abandoned window. `window_count` must stay `>= 1` (CHECK), which
these rules respect because a session at 0 is expired rather than resized.

### Pattern 5: Cross-mode cooldown (D-16)

Puzzle due-date model `[VERIFIED: app/services/train_scheduler.py:48-58, 278-373]`: `CORRECT_RETRY_DAYS: int = 10`,
`FAIL_RETRY_DAYS: int = 4`; due dates are exact offsets from the solve day and "composition serves any item with
`due_date <= today`". A due item skipped by a composition filter keeps its `due_date` and resurfaces first next time
(the per-game cap already relies on this, train_repository.py:1941-1952).

**Recommendation (answers the open discretion items):**
- **Key:** the flaw `(game_id, ply)`. Puzzles join flaws on `GameFlaw.ply == DrillItem.ply` and BC marks served
  blunders by `BlunderCheckWindow.blunder_ply == GameFlaw.ply` (train_repository.py:1885-1891,
  blunder_check_repository.py:216-224), so both modes already use the same ply convention. Only the user's **own**
  blunders can collide (foreign windows are never this user's puzzles; herrings carry no flaw).
- **Window = last serve, both directions, in local days via `session_date`** (`today - CROSS_MODE_COOLDOWN_DAYS`),
  not the whole SR ladder. Reasons: it is what D-16 literally says; a whole-ladder exclusion would remove every
  ACTIVE drill item from BC permanently (most of a heavy user's failed blunders), shrinking own supply for no stated
  goal; and BC is serve-once anyway, so a BC serve can collide with puzzles only once per flaw.
- **"Served" in puzzles** = a `drill_solves` SR row in a `drill_sessions` row with `session_date >= cutoff`
  (composition-time, includes unsolved rows of the open session so the same flaw is never in both open sessions).
  **"Served" in BC** = a `blunder_check_windows` row with `blunder_ply = ply` in a session with
  `session_date >= cutoff`.
- **A BC serve pushes back a scheduled puzzle review implicitly, with no write**: the due item is filtered out of
  composition until the cooldown ends and then resurfaces most-overdue-first. Do not touch `drill_items.due_date`.
- **Implementation shape:** load the user's cooled pair set once per composition (small: at most a week of
  sessions) and apply it in SQL with `tuple_(game_id, ply).notin_(pairs)` (skip the clause when empty), in:
  puzzle `due_stmt` and `pool_stmt` (`_select_candidates`), the two count statements in
  `get_waiting_puzzle_count` (they must mirror composition exactly, per their docstring), and BC's
  `_unserved_qualifying_blunder_exists` (own pick) plus `served_for_games` (so Python-side judging also skips them).
  Do **not** put it inside `pool_entry_stmt`, which also feeds `_material_flags` / eligibility.
- **Index check:** `ix_blunder_check_windows_user_game ("user_id", "game_id")` exists
  `[VERIFIED: app/models/blunder_check.py:153-154]`. `drill_solves` has no `(user_id, ...)` index (only the session
  unique and a partial `solved_at` index, `[VERIFIED: app/models/drill_solve.py:126-138]`), so load the puzzle-side
  set by joining from `drill_sessions` filtered on `user_id` and `session_date`; confirm with EXPLAIN on dev and add
  an index only if the plan shows a seq scan.

Known risk to surface (not a decision to re-open): a BC window built on a blunder the user has seen as a puzzle can
be recognised ("I solved this, so it is a blunder"), the same leak the seed uses to argue against BC repetition. The
7-day cooldown limits only the time overlap, not the recognition. The owner should know; telemetry can compare
catch rates for windows whose blunder has a `drill_items` row against those without.

### Pattern 6: Migration (D-03, D-07, D-14, D-21)

One Alembic revision, `down_revision = "d1a7b3c5e261"` (current head, `uv run alembic heads` this session).

`train_settings` today `[VERIFIED: app/models/train_settings.py:53-80]`:

```python
        CheckConstraint("puzzles_per_session BETWEEN 1 AND 50", name="ck_train_settings_puzzles"),
    ...
    puzzles_per_session: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="6"
    )
```

Changes:
- `ck_train_settings_puzzles` -> `BETWEEN 0 AND 50`.
- `blunder_check_per_session SMALLINT NOT NULL DEFAULT 6` + `CHECK BETWEEN 0 AND <max>` (constant-default ADD COLUMN
  is metadata-only, so every existing row reads 6 instantly: D-03).
- `CHECK (puzzles_per_session > 0 OR blunder_check_per_session > 0)` (D-05 at the DB layer).
- `blunder_check_level TEXT NULL CHECK (blunder_check_level IN ('beginner','intermediate','advanced'))`: TEXT+CHECK per
  CLAUDE.md (low-volume domain column).
- `blunder_check_notice_from TIMESTAMPTZ NULL`; the migration sets it to `now()` only for rows whose user is not a
  guest (`UPDATE train_settings ts SET ... FROM users u WHERE u.id = ts.user_id AND NOT u.is_guest`). The app shows the
  notice while it is non-NULL and `now_utc < notice_from + LAUNCH_NOTICE_DAYS`, and NULLs it on dismiss, on a BC
  completion and on a BC size change. Keeping the 14 in app code (not the migration) honours "a named constant".
- `drill_sessions.ck_drill_sessions_requested_count` stays `1..50`: a size-0 mode never composes (see Pitfall 2).

`blunder_check_sessions`: add `session_date`, `expires_on` (nullable, backfill, then `SET NOT NULL`). Backfill:
`session_date = (started_at AT TIME ZONE COALESCE(ts.timezone, 'UTC'))::date` via LEFT JOIN `train_settings`;
`expires_on = session_date + 1` (beta rows; any still-open one then expires on first touch). Widen status CHECK to
`('open','completed','expired')`. These are beta rows only (`current_beta_user` gate, routers/blunder_check.py:80-87).

`train_weekly_standings` `[VERIFIED: app/models/train_weekly_standing.py:74]`:

```python
        CheckConstraint("board IN ('points', 'accuracy')", name="ck_train_weekly_standings_board"),
```

-> add the two new keys. Recommended names: `'blunder_check_points'` and `'blunder_check_score'` (readable in SQL and
Sentry, no collision with the puzzle keys, and `LeaderboardBoardKind` stays a flat Literal of four).

### Pattern 7: Blunder-check boards (D-14, D-15, D-22..D-25)

Existing pieces `[VERIFIED: app/services/train_leaderboard.py:59, 207-268, 337-360]`,
`[VERIFIED: app/services/train_medals.py:59-112]`:
`ACCURACY_QUALIFY_MIN_PUZZLES: Final = 20`, `_entry_for(kind, aggregate)`, `_tiered_order` (qualified ranked, tentative
after), `final_standings`, `medal_for` (no medal at value 0), `_BOARDS: Final[tuple[LeaderboardBoardKind, ...]] =
("points", "accuracy")` iterated by `finalize_due_weeks`. Finalization writes one marker per week covering all boards,
so adding boards to `_BOARDS` finalizes them from the next due week on; weeks finalized before deploy stay without BC
rows (correct: there were no public BC boards).

Recommendation:
- New aggregate `fetch_week_bc_aggregates(week_start, week_end)` over `blunder_check_windows` joined to `users`,
  `WHERE outcome IS NOT NULL AND ended_at in [week_start, week_end)`, summing `points_scored`, `points_possible` and
  counting windows. Count every ended window regardless of session status (shortened, expired, abandoned sessions
  included): it was played and scored. A started-but-never-ended window is excluded. Add a partial index on
  `blunder_check_windows (ended_at) WHERE ended_at IS NOT NULL` mirroring `ix_drill_solves_solved_at`.
- `BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS: Final = 18` next to `ACCURACY_QUALIFY_MIN_PUZZLES` (D-22).
- Score % = `floor(100 * points_scored / points_possible)` (seed definition; integer like `accuracy_percent`).
- Tie-break: mirror the puzzle rule (`_order_key` = value desc, count desc, name; `_rank_key` for the score board =
  value then windows).
- Generalise `_entry_for` / `build_board` / `final_standings` over a small per-board spec (value function, count
  field, qualify minimum, tentative flag) rather than adding `if kind == ...` branches in five places.
- `GET /train/leaderboard`: return all four boards (two more aggregate queries; tiny) or take a `mode` query param.
  Recommendation: return all four, so switching modes on the card needs no refetch and the rank line can read either.
  `session_id` subtraction (`rank_without_session`) is puzzle-only today; for BC either add a BC session contribution
  or omit the delta on BC boards (simpler; the BC score screen links to the boards, D-24).
- `fetch_unclaimed` orders boards with `case((board == "points", 0), else_=1)` (train_medals_repository.py:187); extend
  to a four-way order. `_BOARD_BY_TEXT` maps exactly two keys and the tally fold initialises
  `{"points": {}, "accuracy": {}}` (train_leaderboard.py:456); both must learn the new keys or a BC medal row raises
  `KeyError` at read time.
- **D-23 vs code (flag to planner):** CONTEXT says today's puzzle tally "already combines the two puzzle boards". The
  code does not: tallies are folded **per board** and `build_board` reads `tallies.get(kind)`
  (train_leaderboard.py:452-470, 562-579), and the info copy says "that player's medals on this board"
  (frontend/src/lib/trainLeaderboard.ts:32-33). Per-board tallies on the two new boards satisfy D-23's intent (a BC
  row never shows puzzle medals). If the owner really wants the puzzle tally combined across Points and Accuracy, that
  is a behaviour change to puzzle boards and must be confirmed.
- D-15: `MedalClaimDialog` already lists every unclaimed medal in one dialog ("listing every unclaimed weekly medal",
  its docstring). Work is: label per board with the mode name, group by week, keep `MEDAL_CLAIM_MAX_ITEMS`.
- D-24: `lib/trainLeaderboard.ts` already remembers the board tab in localStorage
  (`LEADERBOARD_TAB_STORAGE_KEY = 'flawchess_train_leaderboard_tab'`, validated by `parseLeaderboardTab`). Add a
  second key for the mode with the same parse/read/write shape; a stored value outside the union falls back to
  Puzzles.
- D-25: guests: `resolve_viewer_visibility` returns `"guest"`, guests never get standings rows (`is_public` false).
  Reuse unchanged.

### Pattern 8: Level for users without rated games (D-17, D-20)

`user_level_elo(rows)` returns `DEFAULT_USER_LEVEL_ELO` when no row has a pinned Elo, and `_foreign_source` calls it
per session start `[VERIFIED: app/services/blunder_check_selection.py:84, 155-178, 410-436]`:

```python
DEFAULT_USER_LEVEL_ELO: float = 1500.0
...
    level = _median_pinned(chosen)
    return DEFAULT_USER_LEVEL_ELO if level is None else level
```

Recommendation: add `LEVEL_ELO: Final[Mapping[BlunderCheckLevel, float]]` with `"beginner": 1000.0`,
`"intermediate": 1500.0`, `"advanced": 2000.0` (D-17 values; `[ASSUMED]` exact numbers, D-17 says "about") and give
`user_level_elo` a `fallback: float` parameter that `_foreign_source` fills from the stored level (else the
default). Rated games still win (D-17 "ignored once the user has rated games"). `has_rated_games` for the progress
read-model is `recent_rated_games(limit=1)` non-empty. Guests take the same path; they may have imported games, but
the own pick requires `full_evals_completed_at` and guests' games never get the full pipeline
(blunder_check_repository.py:274-276), so they land on foreign windows (D-17).

The level step (D-20) is a frontend screen between the first Start and the drill when `needs_level`; it writes the
level through the settings surface. Recommendation: a small `PUT /train/settings` partial field (see Pitfall 6) or a
dedicated endpoint; either way the first compose must run **after** the level is stored so the first session uses it.

### Pattern 9: Launch: gate removal, routes, discovery dot (D-11, D-18, D-21)

- Backend: `current_beta_user` / `BetaUser` in `app/routers/blunder_check.py:80-87` -> `current_active_user` (guests
  allowed, like every `/train/*` handler). Delete the dependency so knip-style dead code does not linger.
- Frontend: `Train.tsx` redirects `route.tab === 'blunder-check'` for non-beta users and mounts `BlunderCheckTab`;
  `TrainSubnav` takes `showBlunderCheck`. Remove the tab, the `'blunder-check'` entry in `lib/trainRoute.ts`
  (an unknown `/train/*` path already redirects to Today, Train.tsx:140-142), the "Beta" badge, and the Phase 249
  start screen (D-20). The drill host moves under Today and keeps the immersive mechanism (`onImmersiveChange`).
- Discovery dot (D-21 pairs with Phase 255): a new route step needs one entry in `FEATURE_ROUTE`
  (frontend/src/lib/featureRoute.ts) plus one backend Literal member. The backend list is documented as
  "Append-only, in D-06 route order. Step IDs are stored per user and never renamed or removed"
  `[VERIFIED: app/schemas/feature_route.py:18-32]`; a paired list test pins both sides. Use the `used` completion rule
  with a new control slot (e.g. `'train-blunder-check-start'`) on the BC launcher row, mirroring the `train` step.
  Per 255 D-12 there is no queue-jumping: users with earlier open steps reach it later, so the streak-card notice,
  not the dot, is what protects streak holders on launch day.

### Anti-Patterns to Avoid
- **Adding a second shield/count expression** for BC completions: the gate expects exactly one SHIELD_CAP clamp in
  `app/` (`_judge_one_day`). Route everything through `apply_day_completion` -> `_judge_one_day`.
- **Judging "puzzles required" from `pool_state`:** see Pitfall 3.
- **Putting the cooldown inside `pool_entry_stmt`:** it would make material flags and the eligibility watermark
  flicker with the cooldown.
- **A merged board or a shared tally fold keyed on two literals:** every place that enumerates `("points",
  "accuracy")` must be found (grep `"accuracy"` in app/ and `'accuracy'` in frontend/src).
- **Client-side day math:** the badge and row states come from the server, as today (`badge_visible`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Day boundaries | `.date()` on UTC instants | `train_scheduler.local_today` / `session_window` / `is_session_expired` | One conversion site by design; sparse masks break naive `day < today` |
| Streak arithmetic | new shield math for BC | `_judge_one_day` via the shared eager entry point | Divergence gate + frozen-day guarantees |
| Session expiry | ad-hoc BC timestamps | `session_date` + `expires_on` + `expire_stale_sessions` pattern | Matches puzzle semantics the streak walk assumes |
| One-open-session race | app-level locks | existing partial unique index + SAVEPOINT (`insert_session`) | Already handles concurrent Start |
| Ranking, tentative tier, medals | a BC copy of the board code | generalised `_entry_for` / `_tiered_order` / `final_standings` | Finalization equals the live board only if one implementation ranks both |
| Remembered UI choice | server column | `lib/trainLeaderboard.ts` storage helpers pattern | D-24 says browser only |
| Time in endpoints | `datetime.now()` | `dev_now_utc` (`NowUtc`) | CLAUDE.md; dev clock time travel tests streak days |

## Runtime State Inventory (launch-day state)

Not a rename phase, but D-18 launches to everyone at once, so the state that exists at deploy time matters.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Beta `blunder_check_sessions` rows with no session day; possibly an `open` one per beta user | Migration backfill (Pattern 6); open ones expire on first touch |
| Stored data | Every `train_settings` row (registered and guest) | Default BC size 6 via column default (D-03); notice stamp for non-guests only (D-21) |
| Stored data | Streak snapshots settled through yesterday or today | None: settled days are frozen; a user who already completed today's puzzles before deploy keeps today's tick (eager tick already ran) |
| Stored data | `users.prompt_state.feature_route` | New step ID appended; existing users reach it in route order (255 D-12) |
| Live service config | None found (no external config references blunder check) | None |
| OS-registered state | Reminder job runs in-process on a schedule (`train_reminder_service`) | Code change only (day-complete check); verified by reading `_process_candidate` |
| Secrets/env vars | None | None |
| Build artifacts | Installed PWA bundles from before the release will PUT `/train/settings` without the new fields | Make new PUT fields optional (Pitfall 6) |

## Common Pitfalls

### Pitfall 1: Double freeze from repeated completion events
**What goes wrong:** puzzles done (BC at 0) -> day fulfilled; user raises BC and completes it -> eager path sees
`session_date == settled_through` and takes `credit_only` -> +1 freeze for nothing.
**Why:** the existing eager path assumed one completion per day.
**How to avoid:** the `was_complete_before` guard in Pattern 2. **Test:** complete the day, raise BC, complete BC,
assert shield unchanged.

### Pitfall 2: Size-0 puzzles still compose on page mount
**What goes wrong:** `POST /train/sessions` runs on every Today mount as a status read
(routers/train.py:256-268 docstring) and composes with `n = puzzles_per_session`; with 0 it would try to compose an
empty session, and `_discard_if_untouched_and_resized` would discard an untouched open session.
**How to avoid:** short-circuit `compose_and_materialize_session` when the size is 0 (return the empty
`ComposedSession`, write nothing) and expire an open puzzle session when the size becomes 0 (D-06's "set to 0" rule
applied to puzzles; solved puzzles keep their points on the board, which counts by `solved_at`).

### Pitfall 3: `pool_state` is not "nothing to serve"
**What goes wrong:** the orchestrator proposal makes puzzles not required when `pool_state` is `no_material` or
`exhausted`. In code, a puzzle session composes from the static sharp-filler set whenever own material is missing
(`has_material=has_drill_items or has_pool_candidates or sharp_filler_available()`,
train_repository.py:2841-2847), so a `no_material` user still gets a real warm-up session. And `exhausted` is
returned when `waiting_count == 0`, which `get_waiting_puzzle_count` reports right after today's session completed
(branch 2 returns 0 for a completed session in window), so it often means "already done", not "nothing to serve".
**Recommendation (deviation from the proposal, reason written down):** puzzles are required whenever their size is
above 0. The only real "nothing to serve" case is composition returning zero puzzles (`session_id is None`), which
cannot happen while `sharp_filler_available()` is true. If the planner wants a guard anyway, key it on that
composition result for **today**, evaluated in the eager path only.
**Consequence for `pool_eligible_since`:** add "BC size > 0" to `has_material` in both stamping sites. A user who
never had puzzle material and was resolving every day as neutral starts being judged from the first read after
launch. Their streak is 0 anyway (no completed sessions), so nothing is lost, but missed days can show the reset
notice only after they have completed a session (`streak_reset_notice` needs a non-empty completed list).

### Pitfall 4: Sparse-mask session days across modes
**What goes wrong:** under e.g. Mon/Wed/Fri, a Monday visit auto-composes the puzzle session dated Monday (it stays
open until Wednesday); if the user plays BC on Tuesday, a BC session dated "today" is dated Tuesday, so Monday has
puzzles but no BC and is judged missed.
**Recommendation:** date BC sessions with `local_today` like puzzles (consistent with how a fresh puzzle session on
an off day is dated), and accept the edge for sparse masks; the default mask is all 7 days
(`DEFAULT_WEEKDAY_MASK = ALL_WEEKDAYS_MASK`), where `session_window` collapses to the same day. Surface this to the
owner; the alternative (date a new session to the scheduled day whose window covers today) changes puzzle semantics
too.

### Pitfall 5: Everything that enumerates the two board keys
`fold_medal_tallies` initialises `{"points": {}, "accuracy": {}}`; `_BOARD_BY_TEXT` maps two keys;
`fetch_unclaimed` orders with a two-way CASE; `build_leaderboard` / `get_weekly_leaderboard` loop over the two
literals; frontend `LEADERBOARD_TAB_TARGET`, `EMPTY_BOARD_COPY`, `parseLeaderboardTab`, `boardValueLabel` and the
analytics `LeaderboardTabId` union. A missed site raises `KeyError` on the first BC medal or silently drops a board.
**How to avoid:** grep for `"accuracy"` / `'accuracy'` and make each a mapping over the four keys; add a test that
finalizes a week with BC windows and reads unclaimed medals and tallies back.

### Pitfall 6: Full-replace settings PUT vs stale PWA bundles
`TrainSettingsUpdate` is a full-replace body with required fields
`[VERIFIED: app/schemas/train.py:743-765]` (`puzzles_per_session: int = Field(ge=1, le=50)`). Adding
`blunder_check_per_session` / `blunder_check_level` as required would 422 every settings save from an installed
pre-release PWA until it reloads. **Recommendation:** add them as optional (absent = keep the stored value); relax
`puzzles_per_session` to `ge=0`; add a `model_validator` for "not both 0" so the API returns 422 rather than a DB
CHECK violation (which would reach Sentry as a 500).

### Pitfall 7: Launch-day tick rule has no prod rehearsal (D-18)
Days settled before deploy stay frozen; the risk is the first day judged after deploy. **How to avoid:** the
Specifics test list (streak holder on launch day, mode at 0, both resize directions, a day settled before launch, a
user with no puzzle material) as repository tests using the dev clock; plus the reminder test that a user with
puzzles done and BC pending still gets the reminder.

### Pitfall 8: Composition cost and supply at the maximum BC size
`compose_windows` loads at most `MAX_OWN_BATCHES = 3` own batches and `MAX_FOREIGN_BATCHES = 2` foreign batches of 40
games each, with `TABLESAMPLE SYSTEM (2.0)` for foreign picks (blunder_check_selection.py:66-77). Guests are 100%
foreign. Whether 2 foreign batches fill a large session at the rating extremes is unmeasured.
**Recommendation:** BC slider `0, 3..18` step 3 at launch (constant, widen later), DB CHECK `BETWEEN 0 AND 30` for
headroom; a test that a foreign-only user composes the max size on the seeded DB, and a dev/benchmark latency probe
for an 18-window foreign-only compose before shipping.

## Code Examples

### Day-complete query shape (repository)

```python
# Source: recommendation built on settle_streak_snapshot (train_repository.py:990-995)
puzzle_days = select(DrillSession.session_date).where(
    DrillSession.user_id == user_id, DrillSession.status == "completed"
)
bc_days = select(BlunderCheckSession.session_date).where(
    BlunderCheckSession.user_id == user_id, BlunderCheckSession.status == "completed"
)
# Fetch both sets (sequential awaits, never gather), then in Python:
complete = sorted(
    d for d in puzzle_set | bc_set
    if day_is_complete(
        puzzles_done=d in puzzle_set, bc_done=d in bc_set,
        puzzles_size=settings_row.puzzles_per_session,
        bc_size=settings_row.blunder_check_per_session,
    )
)
```

### Cooldown pair set (BC side)

```python
# Source: recommendation; drill_sessions.session_date is the local session day
cutoff = today - datetime.timedelta(days=CROSS_MODE_COOLDOWN_DAYS)
stmt = (
    select(DrillSolve.game_id, DrillSolve.ply)
    .join(DrillSession, DrillSession.id == DrillSolve.session_id)
    .where(
        DrillSession.user_id == user_id,
        DrillSession.session_date >= cutoff,
        DrillSolve.source == int(DrillSource.SR_ITEM),
        DrillSolve.game_id.isnot(None),
    )
)
```

## State of the Art (in-repo)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Weekly streak + required sessions | Per-scheduled-day tick + 0-7 freeze buffer | Phase 193 | The machine this phase feeds |
| Either mode ticks the streak (seed 2026-11-09) | Both required (D-02) | 2026-11-18 | Eager tick must gate on the day, not the session |
| BC spaced repetition planned | Serve-once (250 D-17) | 2026-11-13 | No review queue, no Archive work |
| Own-first BC selection | One-third own / foreign / herring mix | Phase 250 | Guests and no-supply users use the foreign path |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Level Elo values exactly 1000/1500/2000 | Pattern 8 | Slightly off foreign band for no-rated users; constant change |
| A2 | BC slider 0..18 step 3, DB CHECK 0..30 | Pitfall 8 | Users wanting longer sessions; widen via constant |
| A3 | Board keys `blunder_check_points` / `blunder_check_score` | Pattern 6 | One-way once standings are written (D-14); pick before the migration |
| A4 | Set-to-0 marks the BC session `'expired'`, not `'completed'` | Pattern 4 | If owner reads D-06 "closes" as done, raising again the same day would not need a new session |
| A5 | Boards count every ended window regardless of session status; abandoned windows excluded | Pattern 7 | A player can abandon a window after a mid-window timeout forfeit to protect Score %; minor exploit |
| A6 | Puzzles are required whenever size > 0 (deviation from the `pool_state` proposal) | Pitfall 3 | If the owner wants material-less days to need only BC, the warm-up session still exists, so the rule rarely matters |
| A7 | Cooldown by last serve in local days, no due-date write | Pattern 5 | Whole-ladder exclusion would be a different, stricter rule |
| A8 | BC sessions dated `local_today` (sparse-mask edge accepted) | Pitfall 4 | Sparse-mask users can lose a day if they split modes across days |
| A9 | Unstarted windows of expired or shortened sessions are deleted (return to pool) | Pattern 4 | If kept, unseen blunders are burned; supply loss only |

## Open Questions

1. **D-23 wording vs code:** puzzle tallies are per board today, not combined. Keep per-board for all four boards
   (recommended) or combine? Needs owner confirmation only if combining is really intended.
2. **Sparse masks (Pitfall 4):** accept, or date a new session to the covering scheduled day for both modes?
   Recommendation: accept for launch, measure how many users have a mask other than 0 or 127 on prod first (the
   orchestrator can run that SELECT; subagents lack the prod MCP).
3. **Puzzle-recognition leak in BC (Pattern 5):** inform the owner; no design change proposed.
4. **`rank_without_session` on BC boards:** omit (recommended) or add a BC session contribution query?

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (dev, Docker) | tests, migration | ✓ | container `flawchess-dev-db-1` up | — |
| uv / Python | backend | ✓ | uv 0.10.9 | — |
| Node | frontend build/tests | ✓ | v24.19.0 | — |
| Alembic head | migration base | ✓ | `d1a7b3c5e261` | — |

No missing dependencies. Do not gate any plan on `bin/reset_db.sh` (project memory).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-xdist locally), vitest 5 (frontend) |
| Config file | `pyproject.toml` / `tests/conftest.py` (per-worker cloned DB from a migrated template, auto-refreshes on new head); `frontend/vite*.config` |
| Quick run command | `uv run pytest tests/services/test_train_scheduler.py tests/repositories/test_train_repository.py -x` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |

### Phase Requirements -> Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-02 | `day_is_complete` truth table (size 0, both done, one done) | unit | `uv run pytest tests/services/test_train_scheduler.py -x` | ✅ (add cases) |
| D-02 | Streak holder on launch day: puzzles done, BC pending -> no tick; BC done -> tick | repository | `uv run pytest tests/repositories/test_train_repository.py -k day_completion -x` | ✅ (add) |
| D-02/Pitfall 1 | Second completion on an already complete day mints no freeze | repository | same file `-k double_credit` | ❌ new cases |
| D-04/D-06 | Resize: to 0, to <= done, shorten, extend, after completion | repository/router | `uv run pytest tests/routers/test_blunder_check_sessions.py -k resize -x` | ✅ (add) |
| D-05 | Both 0 -> 422, DB CHECK holds | router | `uv run pytest tests/routers/test_train.py -k settings -x` | ✅ (add) |
| Discretion | Day settled before launch stays as judged | repository | `-k settled_before_launch` | ❌ |
| Discretion | No-puzzle-material user: eligibility stamped by BC size | repository | `-k pool_eligible_bc` | ❌ |
| Discretion | Reminder skips only when the day is complete | service | `uv run pytest tests/services/test_train_reminder_service.py -x` | ✅ (add) |
| D-13 | Pending sum, 0 on unscheduled day | repository | `-k pending_count` | ❌ |
| D-16 | Cooldown both directions, due item resurfaces after cooldown, waiting count mirrors composition | repository | `uv run pytest tests/repositories/test_train_repository.py tests/repositories/test_blunder_check_repository.py -k cooldown -x` | ❌ |
| D-17 | Stored level used as fallback; ignored with rated games | unit | `uv run pytest tests/services/test_blunder_check_selection.py -k level -x` | ✅ (add) |
| D-14/D-22 | BC boards rank, 18-window qualify, finalization writes four boards, unclaimed/tally read back | service/repository | `uv run pytest tests/services/test_train_leaderboard.py tests/repositories/test_train_medals_finalization.py -x` | ✅ (add) |
| D-18 | Non-beta and guest users reach every BC route | router | `uv run pytest tests/routers/test_blunder_check_sessions.py -k guest -x` | ✅ (replace 403 tests) |
| D-08..D-12, D-19..D-21, D-24 | Today card rows/states, level step once, notice dismiss, hand-off, mode memory | component | `cd frontend && npx vitest run src/components/train` | ✅ partial |
| Gate | Exactly one SHIELD_CAP clamp in app/ | unit | `uv run pytest tests/services/test_train_scheduler.py -x` | ✅ |

### Sampling Rate
- **Per task commit:** the quick command for the touched module (single files, serial).
- **Per wave merge:** `uv run pytest -n auto -x` plus the frontend block.
- **Phase gate:** full pre-merge gate from CLAUDE.md, including `ty`, the nesting-depth script, and a serial
  `uv run pytest` run before the release (project memory: serial CI hides isolation bugs). Browser UAT of the Today
  card on phone width with the dev clock (D-18 has no prod rehearsal).

### Wave 0 Gaps
- [ ] Shared fixture to create a completed BC session on a given local day (extend `tests/blunder_check_seed.py`)
- [ ] Repository tests for the launch-day cases listed in CONTEXT Specifics
- [ ] Cooldown tests (both modes)
- [ ] Finalization test with BC windows
- [ ] Frontend tests for the new Today card states (replacing `BlunderCheckTab.test.tsx` start-screen cases)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no change | FastAPI-Users (guests included) |
| V3 Session Management | no | — |
| V4 Access Control | yes | Every BC query scoped by `current_active_user.id` (IDOR guard already in repository docstrings); removing the beta gate must not remove the user scoping |
| V5 Input Validation | yes | Pydantic bounds for both sizes, level `Literal`, not-both-0 validator; path bounds already exist for ids/positions |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Guest account churn spamming BC composition (each start ~0.4 s, TABLESAMPLE foreign picks) | DoS | One open session per user (partial unique index) + completed-in-window guard; guest creation path unchanged; watch Sentry/latency after launch |
| Score % gaming by abandoning windows | Tampering (of rankings) | Accepted/flagged (A5); server owns all grading already (D-16/D-18 of 249) |
| Leaking hidden users or guests on BC boards | Information disclosure | Reuse `_rank_board` visibility filter unchanged (D-25) |

## Sources

### Primary (HIGH confidence, read this session)
- `app/services/train_scheduler.py` (tick machine, constants), `app/repositories/train_repository.py` (settings,
  progress, settle, eager tick, waiting count, composition), `app/models/{train_settings,blunder_check,
  train_weekly_standing,drill_session,drill_solve}.py`, `app/services/blunder_check_{service,selection,rules}.py`,
  `app/repositories/blunder_check_repository.py`, `app/routers/{train,blunder_check}.py`,
  `app/services/train_{leaderboard,medals}.py`, `app/repositories/train_{leaderboard,medals}_repository.py`,
  `app/services/train_reminder_service.py`, `app/repositories/train_reminder_repository.py`,
  `app/schemas/{train,feature_route}.py`
- Frontend: `pages/Train.tsx`, `components/train/{TrainSubnav,TrainStreakCard,TrainStartScreen,TrainScheduleSettings,
  TrainLeaderboardCard}.tsx`, `blunder-check/BlunderCheckTab.tsx`, `medals/MedalClaimDialog.tsx`,
  `lib/{trainLeaderboard,featureRoute}.ts`, `App.tsx` (nav badge)
- Planning: 251-CONTEXT, SEED-261108-dk0, sketch 014 README and index.html copy, 249-CONTEXT, 250-CONTEXT,
  255-CONTEXT, ROADMAP Phase 251

### Secondary / Tertiary
- None. No external documentation was needed (no new libraries); the research-plan seam was not used for that
  reason.

## Metadata

**Confidence breakdown:**
- Code map and constraints: HIGH (files read this session, values quoted)
- Streak redesign (Patterns 1-2): HIGH that it preserves existing invariants; MEDIUM on edge semantics (A4, A8)
- Cooldown, boards, resize: MEDIUM (designs reasoned from code; need the listed tests)
- Composition capacity at max size: LOW until probed (Pitfall 8)

**Research date:** 2026-11-18
**Valid until:** 2026-12-18 (in-repo; invalidated earlier by changes to the Train modules)
