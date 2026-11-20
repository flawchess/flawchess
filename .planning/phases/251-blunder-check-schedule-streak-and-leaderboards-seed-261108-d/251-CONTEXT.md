# Phase 251: Blunder-Check Schedule, Streak and Leaderboards (SEED-261108-dk0) - Context

**Gathered:** 2026-11-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the Phase 249 beta MVP into a full Train mode for everyone, guests included. Deliverables:

1. A per-mode session size (blunder check gets its own setting, 0 turns a mode off) on the shared Train schedule and
   reminders.
2. A session streak that needs every mode with a size above 0.
3. The Today page rebuilt as sketch 014 variant B; the Blunder Check tab goes away.
4. A cross-mode cooldown between blunder check and personalized puzzles.
5. Points and Score % leaderboards with medals for blunder check, next to the puzzle boards.
6. Public launch: the beta gate is removed, guests play on foreign blunders, users without rated games pick a level.

Not in this phase: spaced repetition or any re-serving of blunder-check windows (serve-once stands), changes to
selection or the facepalm score (Phases 250, 254, 256), changes to the drill's scoring rules.

</domain>

<decisions>
## Implementation Decisions

D-01 to D-17 are owner decisions carried from SEED-261108-dk0 ("Phase 251 decisions", 2026-11-18) and the roadmap.
The seed holds the reasoning; do not re-open them. D-18 to D-25 come from this discussion.

### Carried forward: schedule and streak
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

### Carried forward: Today page
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

### Carried forward: leaderboards, cooldown, guests
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

### Launch and first run (this discussion)
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

### Leaderboard details (this discussion)
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

### Post-execution owner decisions (2026-11-19, from code review 251-REVIEW.md)

- **Board keys / step ID (plan 02 checkpoint):** `blunder_check_points` / `blunder_check_score`; feature-route step `blunder-check`.
- **D-16 "served" means actually shown (WR-01):** a puzzle counts for the cross-mode cooldown only once it was attempted (not merely composed into a session); a blunder-check window counts only once started (not merely composed).
- **D-06 slider saves on release (WR-03):** the size slider writes the settings draft only on commit (pointer up / keyboard commit), so an intermediate drag position never resizes or completes an open session.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Feature design and owner decisions
- `../../seeds/closed/SEED-261108-dk0-blunder-check-training.md`: "Phase 251 decisions" (streak, Today page,
  leaderboards, cooldown, launch scope), "Spaced repetition revisited" (why serve-once stands), "Interaction and
  scoring" (Score % definition and its false-alarm rule)
- `.planning/ROADMAP.md` §"Phase 251": goal and the three headline decisions

### Layout
- `.planning/sketches/014-train-today-two-modes/README.md`: the question, the three variants, winner B
- `.planning/sketches/014-train-today-two-modes/index.html`: variant B in all four row states, phone and desktop,
  launch notice and level picker toggles (deep link `#desk,p=done,b=progress,norated`)

### What Phase 251 builds on
- `.planning/phases/249-blunder-check-playable-mvp/249-CONTEXT.md`: D-01 beta gate (removed here), D-02 session
  size constant, D-12 to D-18 drill and scoring, D-15 persistence, D-19 no Umami events for DB-held facts
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md`: D-12 to D-16 window mix and user level, D-15 no
  own supply (the guest path), D-17 serve-once
- `.planning/phases/255-feature-discovery-dot-route/255-CONTEXT.md`: the discovery dot the launch notice pairs with

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/train_scheduler.py`: `tick_days`, `_judge_one_day` (the only place shield and count arithmetic
  happens; a divergence gate greps for one occurrence of the `SHIELD_CAP` clamp), `session_window`,
  `is_session_expired`, `is_scheduled_day`, `local_today`
- `app/repositories/train_repository.py`: `settle_streak_snapshot` (single mutation entry point),
  `_stamp_pool_eligibility`, `get_or_create_settings`, `get_progress`
- `app/services/train_leaderboard.py`, `train_medals.py` and their repositories: ranking, visibility
  (`resolve_viewer_visibility` already handles guests and hidden users), `MedalTally`, `finalize_due_weeks`,
  `ACCURACY_QUALIFY_MIN_PUZZLES = 20`
- `app/services/train_reminder_service.py`: `_process_candidate` (settle, then skip if the day is done, then claim)
- `app/services/blunder_check_selection.py` (`DEFAULT_USER_LEVEL_ELO`, user level, foreign band),
  `blunder_check_rules.py` (`BLUNDER_CHECK_SESSION_WINDOWS = 6`, `FOREIGN_RATING_BAND = 150`),
  `blunder_check_service.py`, `app/models/blunder_check.py`
- Frontend: `frontend/src/components/train/` (`TrainStreakCard`, `StreakFlame`, `FreezeMeter`,
  `TrainScheduleSettings`, `TrainLeaderboardCard`, `TrainSubnav`, `TrainScoreScreen`, `TrainStartScreen`,
  `medals/`, `blunder-check/`), nav badge in `frontend/src/App.tsx` (`useNavIndicators`, `TrainBadge`)

### Established Patterns
- Streak settlement is lazy on read and a settled day is frozen forever; `GET /train/progress` commits.
- `tick_days` reads completed days from `drill_sessions.session_date` only; blunder-check sessions carry
  `started_at` / `completed_at` and a fixed `window_count` (CHECK `>= 1`), no session day.
- `train_weekly_standings.board` is TEXT with CHECK `IN ('points', 'accuracy')`.
- Time-dependent endpoints take `now_utc` from `dev_now_utc`.
- Per-viewer UI memory goes in browser storage; beta flag is read from `useUserProfile().data`.

### Integration Points
- `app/routers/blunder_check.py`: every route depends on `current_beta_user` (remove); guests must be allowed as
  in `app/routers/train.py`.
- `GET /train/progress` and `PUT /train/settings`: per-mode counts, pending counts, row states, level, notice state.
- Selection in both modes: the cooldown filter (blunder-check candidates, puzzle pool).

</code_context>

<specifics>
## Specific Ideas

- Launch is not staged (D-18), so the streak rule has no prod rehearsal. Cover the tick rule with tests for: a
  streak holder on launch day, a mode set to 0, both resize directions mid-session, a day settled before launch,
  and a user with no puzzle material.
- Notice copy from the seed: "Your streak now includes blunder check. Change the amount on the card."
- Checklist wording example from the seed: "Puzzles done, Blunder check 4 left".
- Level labels are words, never Elo numbers.
- Project memory that applies: herring and foreign windows are cross-user, so no "your move" copy; run
  `npm run build` for type changes; tweak a constant instead of adding a prop for a one-caller visual change.

</specifics>

<deferred>
## Deferred Ideas

- Adaptive level from the catch rate (replaces the level question; needs its own tuning).
- Reusing the stored level for the lichess warm-up puzzles in personalized training and for the default bot strength.
- Single-retry spaced repetition (one retry after 3 to 4 weeks, "blind spots fixed" counter); `blunder_check_windows`
  keeps the history needed to backfill it.
- Progress without re-serving: catch-rate trend over the last N sessions, or the facepalm rate in real games
  (SEED-261114-iuv).
- Blunder-check windows in the Archive tab (not raised by the owner; the subnav keeps Archive for puzzles only).

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`,
  `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`, `2026-08-29-variation-tree-nested-button.md`:
  keyword-only matches ("phase", "users, games", "score"), unrelated to this phase.

</deferred>

---

*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-dk0*
*Context gathered: 2026-11-18*
