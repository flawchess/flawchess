---
id: SEED-185
status: dormant
planted: 2026-10-03
planted_during: no open milestone (after v2.21), Phase 228 (settings page) ready to execute; /gsd-explore training features
trigger_when: after Phase 228 (settings page) ships, or when planning the next Train / retention work
scope: medium (one phase: weekly aggregation query + leaderboard card on Train start/score screens + opt-out setting + Privacy copy)
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
  puzzles to qualify"). The points board needs no qualifier.
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
The real formula is client-side in `frontend/src/lib/trainScore.ts`.

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

## Suggested (not yet decided)

- **Show neighbours** (2 above, 2 below the user) in addition to the top 5. A new user
  lands around #50 of ~77 on points; "12 points to pass <name>" is a reachable target,
  a bare "#50" is not.

## Open questions with proposed defaults

- **Week boundary:** ISO week (Monday) keyed on `drill_sessions.session_date`, which is
  already the user's local day. Resets are then not globally simultaneous; acceptable.
- **Score scope:** do warm-up sessions count toward the score board? Default: points
  yes, score average no (warm-ups are sharp filler, not the user's own pool).
- **Score definition:** mean of per-session percentages vs pooled points/max over all
  puzzles. Default: pooled, so a 30-puzzle session weighs more than a 3-puzzle one.
- **Guests:** excluded (no persistent identity, purged after 30 days inactivity).
- **Users with both usernames:** show lichess first? Or the platform with more games?
  Users with no username (Google signup, nothing imported) appear as "Anonymous".
- **Opt-out:** "Hide me from leaderboards" toggle (fits the Phase 228 settings page) and
  one line on the Privacy page, since showing usernames next to training results is a
  new use of data the Privacy page already lists.
- **Server-side scoring:** the score formula lives only in `trainScore.ts` today.
  The leaderboard needs it server-side: persist the session score on completion, or
  port the formula, with a parity test.
- **Placement:** Train start screen (next to the streak) and the session score screen
  ("you moved up 3 places").

## Breadcrumbs

- `frontend/src/lib/trainScore.ts` — scoring constants (GUESS_POINTS, MOVE_TIER_POINTS,
  TRAIN_POINTS_PER_PUZZLE)
- `app/models/drill_session.py`, `app/models/drill_solve.py` — session/solve rows
  (`correct_guess`, `move_quality`, `is_warmup`, `entered_at`)
- `app/models/user.py:20-21` — platform usernames
- `frontend/src/components/train/TrainStartScreen.tsx`, `TrainScoreScreen.tsx`
- `frontend/src/pages/Privacy.tsx:27` — usernames listed as collected data
- `.planning/seeds/SEED-175-settings-page.md` — Phase 228, home for the opt-out toggle
- `reports/growth/growth-recommendations-2026-10-03.md` — Train retention context
- Related: SEED-184 (conversion/defender trainer), whose results could later feed the
  boards
