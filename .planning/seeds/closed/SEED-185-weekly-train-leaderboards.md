---
id: SEED-185
status: promoted
promoted_to: Phase 230
promoted: 2026-10-03
planted: 2026-10-03
planted_during: no open milestone (after v2.21), Phase 228 (settings page) ready to execute; /gsd-explore training features
trigger_when: after Phase 228 (settings page) ships, or when planning the next Train / retention work
scope: medium (one phase: weekly aggregation query + leaderboard card on Train start/score screens + guest nudge + opt-out setting + Privacy copy)
---

# SEED-185: Weekly Train leaderboards (points + average session score)

Two weekly leaderboards on Train, shown from the user's very first session:

1. **Points board** (effort): sum of Train points this week. More puzzles per session is
   an intended advantage.
2. **Average session score board** (accuracy/consistency): mean session score this week.

Each board shows the **top 5** plus the **user's own position**.

## Why This Matters

- Train is the only feature with daily return (growth report 2026-10-03). Competition is
  a motivator the owner wants to use from day one, and a small site cannot run
  Duolingo-style leagues, but a single weekly board works at the current population.
- Duolingo reports leagues raised learning time 17% and tripled highly engaged learners
  (https://www.lennysnewsletter.com/p/how-duolingo-reignited-user-growth). Treat those
  numbers as direction only: at our traffic such effects are not measurable.

## Locked decisions (owner, 2026-10-03)

- **Two boards, not one.** Owner overrode the "points only" recommendation. The data
  supports it: the boards measure different things (see Evidence).
- **Visible right after the first session.** The score-board position is shown as
  **tentative until 20 puzzles solved in the current week** ("#4 (tentative), 14 more
  puzzles to qualify"). The points board needs no qualifier. (Round 2: tentative users
  are ranked in the list too, see below.)
- **Display the user's chess.com or lichess username.** These are public.
- **Impersonation is an ACCEPTED RISK, deliberately ignored for now.** FlawChess never
  verifies username ownership (`users.chess_com_username` / `lichess_username` are
  whatever was typed; opponent scouting is a supported use), so anyone can appear as
  e.g. "Hikaru". Owner decision: ignore. If abuse shows up, the options discussed were:
  a display name with a blocklist of top-player usernames (cheapest), a profile-bio code
  check via the public APIs (works for both platforms), or lichess OAuth (lichess only;
  chess.com has no general third-party OAuth). Do not "fix" this unprompted.

## Evidence (prod, week 2026-09-28..10-04, partial)

Points approximated as correct guess (1) + move quality capped at 2, max 3 per puzzle.
The real formula is client-side in `../../../frontend/src/lib/trainScore.ts`.

- 77 users completed a session that week (76-100 per week since the 2026-09-25
  newsletter, 7-15 per week before it). 14 trained on 5+ days.
- **Points ≈ volume:** corr(points, puzzles) = 0.98, corr(points, sessions) = 0.84.
  Top: 87 puzzles at 74%, then 54 at 90%. Median user: 2 sessions, 12 puzzles, 21 points.
- **Score is independent of volume once qualified:** among users with 3+ sessions,
  corr(avg score, puzzles) = 0.18, so the two boards reward different players.
- **A qualifier is mandatory for the score board:** unqualified, the top 8 were all
  one session of 6 puzzles at 100% (likely warm-ups or easy pools). With 3+ sessions,
  29 of 77 qualified and the top was 90% (54 puzzles), 89% (18), 85% (18), 84% (45).
- Caveat: every user's puzzles come from their own games, so difficulty is not
  comparable across users. Label the score board as accuracy/consistency, not skill.

## Locked decisions (owner, 2026-10-03, /gsd-explore refinement)

- **Opt-out visibility.** Every registered user with a username appears by default.
  "Hide me from leaderboards" toggle on the Phase 228 settings page, plus one line on the
  Privacy page (showing usernames next to training results is a new use of listed data).
- **Guests see the board plus a sign-up nudge.** Guests never appear on the board, but
  they see it with "you'd be #N, sign up to claim your spot". 18 of 98 trainers in week
  2026-09-28 were guests, so this doubles as a conversion lever.
- **Display name: lichess username first**, else chess.com, else "Anonymous" (Google
  signup with nothing imported; 6 of 80 registered trainers that week). 37 of 80 had both.
- **Show neighbours.** Top 5, then the user's own row with 2 above and 2 below, and a
  "N points to pass <name>" target.

## Settled by code/data check (2026-10-03)

- **Server-side scoring needs no new column or formula port.** `drill_solves` persists
  `correct_guess` (bool) and `move_quality` (0/1/2), which equal `GUESS_POINTS` and
  `MOVE_TIER_POINTS` from `trainScore.ts`. Puzzle points = `correct_guess::int +
  move_quality`, max 3. Only a parity test pinning the constants is needed. Zero solved
  rows had NULL in either field that week.
- **Score = pooled:** sum(points) / (3 × puzzles solved) over the week, so a long session
  weighs more than a short one.
- **Count solves, not completed sessions.** 87 of 1474 solves that week were in sessions
  never completed (open/expired). Aggregate over `drill_solves.solved_at IS NOT NULL`.
- **Warm-up exclusion goes by puzzle source, not session flag.** Warm-up sessions held
  32 own-pool puzzles and normal sessions held 22 `SHARP_FILLER` puzzles. Rule: points
  board counts every solve; score board excludes `source = SHARP_FILLER` solves, and
  the 20-puzzle qualifier counts only non-filler solves.

## Locked decisions (owner, 2026-10-03, round 2: populated Monday + medals)

- **One weekly window for both boards; no rolling window.** Owner rejected a rolling
  7-day accuracy board.
- **Global deadline: Sunday 24:00 UTC.** Both boards reset Monday 00:00 UTC. Key solves
  on `drill_solves.solved_at` in UTC (ISO week), NOT `drill_sessions.session_date`
  (that is the user's local day and would make the deadline differ per user). A session
  spanning the deadline splits by each solve's timestamp. Show a countdown ("ends in
  1d 4h").
- **Tentative users are ranked on the score board** so it is populated from Monday
  (replay of week 2026-09-28: 43 registered users trained on Monday, 0 qualified; 7
  qualified by Wednesday). Their row is marked tentative with "N more puzzles to
  qualify". Expect Monday's top to be short 100% sessions; accepted.
- **Ties share a rank** (1, 1, 1, 4); within a tie, the user with more puzzles solved is
  listed first.
- **Medals (follow-up, not this phase):** top 3 of each board at the deadline get a
  medal. Score-board medals go to qualified users only (20+ non-filler puzzles), so
  final standings skip tentative users. This phase must not block it: the UTC deadline
  above is the prerequisite. Medals will need a persisted weekly result snapshot
  (opt-outs and account deletions must not rewrite past winners); design that in the
  medals phase.
- **Score integrity (accepted risk in Phase 230, MUST close before medals ship):** Phase
  230 code review WR-01. `record_solve` keeps the client-asserted `move_quality` for any
  off-key move (only vetted key moves get the server tier, Phase 211 D-04), so a direct
  API caller can bank up to 2 of 3 points per puzzle on both public boards. Owner accepted
  this on 2026-10-04 for the leaderboards alone (no prizes, small user base). The medals
  phase must verify or clamp off-key tiers server-side before awarding anything.
  **Superseded 2026-10-04:** owner also accepts WR-01 for medals; see SEED-186.
- **Medals design moved to SEED-186** (`SEED-186-weekly-leaderboard-medals.md`).

## Proposed defaults (confirm in discuss-phase)

- **Placement:** Train start screen (next to the streak) and the session score screen
  ("you moved up 3 places", computed as rank before vs after this session's solves).
- **Out of scope:** medals and their snapshot table, past-week history, notifications,
  league tiers.

## Breadcrumbs

- `../../../frontend/src/lib/trainScore.ts` — scoring constants (GUESS_POINTS, MOVE_TIER_POINTS,
  TRAIN_POINTS_PER_PUZZLE)
- `../../../app/models/drill_session.py`, `app/models/drill_solve.py` — session/solve rows
  (`correct_guess`, `move_quality`, `is_warmup`, `entered_at`)
- `app/models/user.py:20-21` — platform usernames
- `../../../frontend/src/components/train/TrainStartScreen.tsx`, `TrainScoreScreen.tsx`
- `frontend/src/pages/Privacy.tsx:27` — usernames listed as collected data
- `SEED-175-settings-page.md` — Phase 228, home for the opt-out toggle
- `reports/growth/growth-recommendations-2026-10-03.md` — Train retention context
- Related: SEED-184 (conversion/defender trainer), whose results could later feed the
  boards
