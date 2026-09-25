# Session length: is there an ideal number of games per sitting?

EDA for a data-story candidate suggested by GM Noël Studer after reviewing the tilt story
(2026-09-20): "Gibt es eine ideale Spiel-Session-Länge, pro Zeitkontrolle? Ich habe immer
6-Partien-Blöcke Blitz gespielt, bei mehr nahm die Qualität ab. Bei Rapid 2–3 Partien, mit
kurzen Pausen."

Script: `analysis/session_length_study/session_length_study.py` (40 s, reads the tilt
study's cached extracts). Tables and charts: `analysis/out/session_length/`.

## Headline

**There is no fatigue signal in bullet or blitz, a clear one in rapid after about the
sixth game, and a (noisier) one in classical after the third.** The number that matters
is the score residual (actual − expected, in percentage points, 1 pp ≈ 7 rating points
at the game level), for all games played at position *k* of a session:

| time control | first game | games 2–5 | late games (def.) | late − early | user-demeaned | share of games that are "late" |
|---|---|---|---|---|---|---|
| bullet | **−1.65** [−1.95, −1.35] | +0.35 | +0.83 (13+) | **+0.48** [+0.09, +0.87] | +0.34 [−0.02, +0.71] | 21% |
| blitz | **−0.49** [−0.74, −0.28] | +0.01 | +0.58 (11+) | **+0.57** [+0.15, +0.97] | +0.53 [+0.16, +0.92] | 14% |
| rapid | −0.08 | +0.20 | −0.54 (7+) | **−0.74** [−1.16, −0.30] | −0.59 [−0.99, −0.16] | 13% |
| classical | +0.46 | −0.28 (games 2–3) | −1.96 (4+) | **−1.68** [−2.79, −0.56] | −1.21 [−2.30, −0.23] | 10% |

(`tbl_phase_tc.csv`, `tbl_late_minus_early.csv`; 95% user-cluster bootstrap CIs; residual
centred per time control so the average over all positions is zero.)

So Noël's rule is half right, and in an interesting way. The **blitz block of six is not
supported**: results in games 7–20+ are, if anything, slightly *better* than in games 2–5
(more on why below), and the within-user blunder rate is flat to game 20 and beyond. The
**rapid rule is supported but the threshold is looser**: games 2–6 are all at or above par,
the drop starts at game 7 (−0.8 pp), i.e. after roughly an hour of play, and 2–3 games
is well inside the safe zone. Classical drops from game 4, but only 10% of classical games
are 4th-or-later games and the estimate is wide.

The **loudest and most robust session effect is the first game**: the warm-up penalty is
−1.65 pp in bullet (−2.3 pp for 800-rated players, −0.8 pp at 2400) and −0.5 pp in blitz,
and there is none in rapid. Second loudest: **pausing inside a session hurts in fast chess**
(3–60 min pause: −0.9 pp blitz, −1.5 pp bullet) but a 1–10 min pause is fine or slightly
positive in rapid; only pauses over 10 min hurt in rapid (−0.7 to −1.0 pp).

## Data and method

Same frame as the tilt story (`analysis/tilt_study/story_data.py`), so the definitions in
`stories/tilt/tilt-report.md` apply unchanged:

- Every rated human game of the 4,487 benchmark users, per (user, time control), ordered
  by start time. Game end = start + clock time used by both sides (reconstructed from the
  first and last `%clk` of each side); a game without a complete clock record gets no end
  time, and an unknown gap starts a new session.
- **Session** = consecutive games with < 60 min between the END of one game and the start
  of the next. Position *k* = the k-th game of the session. 30-min sessions as sensitivity
  (`tbl_curve_position_gap30.csv`, same shapes).
- **Outcome** = residual = score − expected score, expected fitted empirically per
  (time control, 400-pt rating bucket, 25-pt rating-gap bin, colour) on equal-footing,
  hygiene-clean, in-session games. One change from the tilt report: the tilt calibration
  puts the zero point on in-session games only, which leaves first-of-session games with a
  time-control-specific offset (bullet −0.4 pp, classical +0.7 pp, `tbl_tc_offset.csv`).
  Here every position counts, so the residual is **re-centred per time control** over the
  whole scored frame. Shapes and differences are unaffected.
- **Equal footing**: only games with both players within 100 rating points are scored;
  session features are computed over the full history. **Hygiene**: each user's first 100
  imported games in the TC and games > 150 points from the user's long-run median rating
  are dropped. Scored frame: 1,739,714 games, 3,541 users.
- **Selection.** The stopping decision comes *after* a game, so the marginal residual at
  position *k* over all games played at *k* is the honest "how does your k-th game go"
  quantity. What it does not remove is *who* reaches *k* (players who play long sessions
  are different people), handled by a **user-demeaned** residual (each user's mean residual
  in the TC subtracted), and *which sessions* reach *k* (a session that survives to game
  10 survived nine stop decisions, each of which favours continuing after a win), which is
  an upward bias of at most the size of the tilt/hot-hand effect (≈ 0.5–1 pp, from the tilt
  study) and works *against* finding fatigue. Two further cuts are in the tables:
  **continuers** (games followed by another game in the session) and a **fixed cohort**
  (sessions of ≥ N games, positions 1..N−1, so the same sessions sit at every position).
  Continuers are biased *upward* by the quit-on-loss rule, and that bias shrinks with
  depth because the stop-after-loss vs stop-after-win gap shrinks with depth
  (`tbl_stop_hazard.csv`), which fakes a decline; don't read that curve alone.
- **Outcome-free quality metrics**, immune to the stopping rule: blunders and mistakes per
  100 own moves from our engine (618k fully-evaluated games), think time per move relative
  to the user's own mean in the same clock format (removes 3+0 vs 5+3 mix), share of moves
  played in ≤ 1 s, share of games lost on time, lichess-imported ACPL (user-requested
  analysis only, selection-biased). Each also user-demeaned (`_dm`).
- All CIs: 300-rep bootstrap over users (a user's games are correlated); late − early
  differences resample users jointly across the two phases.

## 0. How long are sessions, actually?

| | sessions | mean games | median | p75 | p90 | one-game sessions | median board minutes | p90 board minutes |
|---|---|---|---|---|---|---|---|---|
| bullet | 186,517 | 4.8 | 2 | 5 | 11 | 37% | 4.6 | 22 |
| blitz | 244,547 | 3.5 | 2 | 4 | 8 | 41% | 10.5 | 42 |
| rapid | 308,212 | 2.4 | 1 | 3 | 5 | 50% | 21 | 64 |
| classical | 115,362 | 1.6 | 1 | 2 | 3 | 69% | 46 | 116 |

(`tbl_session_desc.csv`.) Sessions are short and heavy-tailed. Noël's six-game blitz block
is the 80th percentile; a rapid session of 2–3 games is already above the median. Share of
scored games by position (`tbl_pos_share.csv`): 28% of blitz games are first games, 25%
are 7th-or-later, 13.5% 11th-or-later. In rapid 38% are first games and 12.8% are 7th-or-
later. Session length grows with rating in bullet (mean 3.6 games at 800 → 6.3 at 2400)
and shrinks with rating in classical (1.9 → 1.35); blitz and rapid are flat across rating
(`tbl_session_desc_elo.csv`).

Stop hazard (`tbl_stop_hazard.csv`, `stop_hazard.png`): P(session ends after game k) falls
monotonically with k in every TC (blitz: 0.35 after game 1, 0.22 after game 6, 0.15 after
game 12; rapid: 0.47 → 0.28 → 0.19). Nobody stops at a round number; the longer a session
has run, the less likely it is to end after the next game. In bullet and blitz the hazard
after a loss exceeds the hazard after a win at every position up to ~12 (quit-on-loss,
the tilt story's §5), and the gap closes with depth. In rapid the gap is small and
*reverses* from game 8 on (stop after a win more often than after a loss: "quit while
ahead" once the session is long).

## 1. Results by game number (`curve_all.png`, `curve_demeaned.png`, `curve_cohort.png`, `tbl_curve_position.csv`)

Centred residual, all games at position k (pp; cells with n < 1,000 omitted):

| k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13–20 | 21+ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bullet | **−1.6** | +0.3 | +0.2 | +0.4 | +0.5 | +0.3 | −0.3 | +0.1 | −0.1 | +0.6 | +0.2 | +0.8 | +0.2…+1.5 | **+0.9** |
| blitz | **−0.5** | −0.1 | 0.0 | +0.2 | 0.0 | +0.5 | +0.4 | −0.2 | +0.7 | +0.2 | +0.3 | +0.2 | −0.5…+1.4 | **+0.8** |
| rapid | −0.1 | +0.3 | +0.1 | +0.1 | +0.1 | +0.3 | **−0.8** | −0.4 | −0.8 | −0.5 | −0.6 | +0.7 | −3.1…+1.0 | 0.0 |
| classical | +0.5 | −0.4 | +0.1 | −1.0 | **−3.0** | **−2.8** | (n<1k) | | | | | | | |

- **Bullet and blitz: flat after the warm-up game, slightly rising.** No individual cell
  from game 2 to game 20 is significantly negative. Late (13+ / 11+) beats early (2–5) by
  +0.5 pp in both, significant, and the user-demeaned version agrees (+0.34 bullet n.s.,
  +0.53 blitz sig.). The fixed cohort (bullet sessions ≥ 12 games, blitz ≥ 10) shows the
  same: positions 2..N−1 all sit +0.2 to +2 pp, no downward trend.
- **Rapid: at or above par through game 6, then −0.5 to −0.8 pp for games 7–11**, and
  −1 to −3 pp in the thin 14–17 cells. Late (7+) − early (2–5) = −0.74 [−1.16, −0.30],
  user-demeaned −0.59 [−0.99, −0.16]. The fixed cohort (sessions ≥ 6 games, positions 1–5)
  is flat, which is consistent: the decline starts after position 5.
- **Classical: drop from game 4** (−1.0, −3.0, −2.8 pp for games 4–6; 4+ vs 2–3 =
  −1.68 [−2.79, −0.56], demeaned −1.21 [−2.30, −0.23]). Only 10% of classical games are
  4th-or-later, and the effect sits almost entirely in the 1200 bucket (−2.9 pp; 1600
  −0.6 n.s., 2000 +0.9 n.s.), so this is a "probably" rather than a finding.
- The **last game of a session** (`frame = last_game`) runs −6 to −9 pp in bullet and
  −3 to −5 pp in blitz at every position: that is the quit-on-loss rule, not fatigue
  (the tilt story covers it). In rapid the last game turns *positive* from position 8
  (+1 to +3 pp): deep rapid sessions end on a win.

### Why are late bullet/blitz games slightly *better* than early ones?

Three candidates, none of which is "playing more makes you better": (a) session-survival
selection: reaching game 13 means surviving 12 stop decisions that each favour continuing
after a win, so survivors are slightly more often in a good-form state (upper bound ≈ the
tilt study's WW+ effect, +0.5 to +1 pp, which is the size of what we see); (b) opponent
pool: late-night opponents may be more fatigued than the survivor; (c) within-user
composition: a user plays long sessions on days they feel sharp. All three say the same
thing for the story: **no evidence that the 10th or 20th bullet/blitz game is worse than
the 3rd.** Per rating bucket (`tbl_late_minus_early.csv`): late − early is positive or
zero in every bullet and blitz bucket; largest in blitz 1200 (+1.2 pp) and 1600 (+0.9).

## 2. Per rating bucket (`tbl_phase_tc_elo.csv`, `curve_elo_*.png`)

Late − early residual, pp (cells with ≥ 1,000 late games):

| bucket | bullet (13+) | blitz (11+) | rapid (7+) | classical (4+) |
|---|---|---|---|---|
| 800 | +0.2 | −0.1 | **−1.3** [−2.5, −0.4] | −2.7 [−6.1, +0.9] |
| 1200 | +0.9 [0.0, +1.7] | **+1.2** [+0.3, +2.0] | 0.0 | **−2.9** [−5.3, −1.1] |
| 1600 | +0.4 | **+0.9** [+0.1, +1.6] | **−1.2** [−2.1, −0.4] | −0.6 |
| 2000 | **+0.7** [0.0, +1.5] | 0.0 | −0.7 [−1.4, +0.2] | +0.9 (n=525) |
| 2400 | +0.2 | +0.7 | +1.2 [−1.2, +4.2] (n=2.4k) | — |

The rapid decline is present at 800, 1600 and 2000, absent at 1200 (an outlier cell, not
a trend) and untestable at 2400. No rating gradient: fatigue in rapid is not a
"weak players tire faster" story. Bullet's warm-up penalty *does* have a gradient: first
game −2.3 pp at 800, −1.4 at 1200, −2.0 at 1600, −1.3 at 2000, −0.8 at 2400.

## 3. Games or minutes? (`tbl_curve_elapsed.csv`, `tbl_curve_board_minutes.csv`, `tbl_pos_x_elapsed.csv`)

Residual by wall-clock minutes since the session started (games after the first) and by
minutes of clock time already used at the board (excludes pauses):

| | 0–15 | 15–30 | 30–45 | 45–60 | 60–90 | 90–120 | 120–180 | 180–240 | 240+ |
|---|---|---|---|---|---|---|---|---|---|
| bullet, elapsed | +0.6 | +0.2 | +0.4 | +0.5 | +0.5 | +0.3 | +0.1 | +0.2 | +0.5 |
| blitz, elapsed | +0.2 | +0.2 | +0.1 | +0.4 | −0.1 | +0.3 | +0.1 | +0.3 | +0.4 |
| rapid, elapsed | +0.5 | +0.4 | 0.0 | +0.2 | **−0.5** | **−0.7** | −0.4 | +0.7 | −0.4 |
| classical, elapsed | −0.4 | −0.2 | −0.7 | −0.2 | **−1.4** | **−1.7** | +0.5 | −2.8 | −1.7 |

Board minutes tell the same story: bullet and blitz are flat-to-positive out to 2 h+ of
pure clock time (bullet 60–90 board minutes: +1.6 pp!), rapid turns negative at 60–90
board minutes (−0.65 [−1.17, 0.00]), classical at 45+ (noisy). **In rapid the decline
appears at the one-hour mark whichever way you measure it**, which is games 5–8. The
2-D table (position × elapsed) cannot separate "many games" from "many minutes" in rapid:
games 7–10 played within 45–60 min are fine (+0.45, n small), at 60–120 min they are
−1.0 to −1.5 pp. In bullet and blitz, a *low* position with a *long* elapsed time is the
one bad cell (blitz game 2–3 after 15–90 min elapsed: −0.6 to −1.4 pp; bullet −0.9 to
−1.5): that is a pause, not a long session, see §6.

## 4. Quality metrics: blunders, think time, fast moves (`tbl_quality_position.csv`, `quality_*.png`)

**Raw blunder rate falls with position in blitz (5.8 → 5.0 per 100 moves at game 21+) and
bullet (7.4 → 6.7), and that is entirely composition**: stronger players play longer
sessions. Within a rating bucket (`tbl_blunder_phase_tc_elo.csv`) blitz is flat in every
bucket (2400: 3.75 early, 3.72 late); user-demeaned it is flat to game 20+ in bullet and
blitz (late − early: −0.01 and −0.02 per 100 moves). Rapid: +0.09 per 100 moves
[+0.01, +0.17], i.e. +1.5% relative, concentrated in the 1600 bucket (+0.18). Classical:
+0.15 [−0.05, +0.36] (+2.7%). User-demeaned mistakes and ACPL: no trend anywhere. So the
rapid result decline (−0.7 pp) is only weakly mirrored in blunder counts; the quality loss
is small per move and spread out, or it is in the games the engine has not evaluated.

**Everyone speeds up.** Think time per move relative to the user's own mean in the same
clock format, by position:

| k | 1 | 2 | 3 | 5 | 8 | 10 | 12 | 15 | 21+ |
|---|---|---|---|---|---|---|---|---|---|
| bullet | 1.028 | 1.000 | 0.998 | 1.001 | 0.996 | 0.995 | 0.991 | 0.991 | 0.984 |
| blitz | 1.015 | 1.006 | 1.006 | 1.003 | 1.000 | 0.993 | 0.990 | 0.977 | 0.975 |
| rapid | 1.020 | 1.008 | 1.004 | 0.991 | 0.976 | 0.969 | 0.953 | 0.961 | 0.947 |
| classical | 1.025 | 1.008 | 0.979 | 0.973 | 0.982 | 0.902 | | | |

Monotone in every time control, within user, tight CIs (late − early: bullet −1.2%, blitz
−2.4%, rapid −3.7%, classical −2.4%, all significant; the same in every rating bucket).
The share of moves played in ≤ 1 s rises in step: bullet 52% (game 1) → 64% (21+), blitz
27% → 34%, rapid 11% → 13.5%; user-demeaned +0.45 pp bullet/blitz, +0.35 pp rapid.
**Game 1 is played the slowest** in every TC (+2–3% think time), and in bullet it is
also the worst game: warm-up is careful *and* bad. Deeper into the session, players
play faster; in bullet and blitz this costs nothing measurable, in rapid it coincides
with the result decline. Whether faster play *causes* the rapid decline or both are
symptoms of waning attention, the data cannot say. Time-outs, game length (plies), and
the timeout-loss share are flat with position in every TC (bullet game 1 is the exception:
26% of first games are lost on time vs 23–24% afterwards, part of the warm-up penalty).

## 5. Warm-up (first game of a session)

Centred residual of game 1: bullet −1.65 [−1.95, −1.35], blitz −0.49 [−0.74, −0.28],
rapid −0.08 n.s., classical +0.46 [+0.01, +0.95] (classical sessions are mostly one game
and the calibration frame is thin there; treat as zero). This is the tilt story's §4c
finding with the rating gradient added (§2 above). The **first game of a long session is
worse than the average first game** (fixed cohort: −1.4 bullet, −1.4 blitz, −1.6 rapid),
and the marathon-start test (`tbl_marathon_start.csv`) shows why: within user, a lost
first game raises the chance that the session becomes a long one in blitz (+0.16 pp for
≥ 10 games) and rapid (+0.25 pp for ≥ 6 games), lowers it in bullet (−0.16), and the
opposite holds for a session reaching 3+ games (a win makes a third game more likely:
+1.1 pp blitz, +2.3 pp bullet). Small effects, but the direction is the "chasing" one for
long sessions: **marathon rapid and blitz sessions are slightly more likely to have started
with a loss.**

## 6. Pauses inside a session (`tbl_pause.csv`, `tbl_pause_x_depth.csv`, `tbl_pause_x_prev_result.csv`)

Residual by the gap between the end of the previous game and the start of this one
(games 2+, gap < 60 min so still the same session):

| | < 1 min | 1–3 min | 3–10 min | 10–30 min | 30–60 min |
|---|---|---|---|---|---|
| bullet | **+1.05** | −0.20 | **−1.46** | **−1.49** | **−1.27** |
| blitz | **+0.63** | −0.23 | **−0.92** | −0.47 | **−0.75** |
| rapid | +0.06 | +0.38 | **+0.53** | **−0.69** | **−0.97** |
| classical | −1.1 | −1.2 | +0.2 | −1.0 | −0.9 (all n ≤ 9k, none sig.) |

- In **bullet and blitz, any pause over a minute costs**, and 3–60 min pauses cost 1–1.5 pp
  (bullet) and 0.5–0.9 pp (blitz). This holds at every session depth (`tbl_pause_x_depth`:
  bullet games 7+ after a 3–10 min pause −2.1 pp) and **after wins as well as after
  losses** (bullet after a win: 3–10 min −0.6, 10–30 min −1.0; after a loss −2.2/−1.9).
  The tilt story showed the post-loss half of this; the post-win half says it is a
  cooling-down effect, not (only) a tilt one.
- In **rapid, a 1–10 min pause is fine or mildly good** (+0.4/+0.5; after a win +1.0/+1.5,
  after a loss −0.4/−1.1), and the damage starts at 10 min (−0.7) and 30 min (−1.0).
  Noël's "2–3 games with short pauses" is consistent with the data as long as short means
  under ten minutes.
- Caveats: pause length is the player's choice (a 20-minute gap may be a phone call, a
  meal, or a game in a time control that was not imported, see §10), and the "< 1 min"
  cell in bullet/blitz is partly the re-queue of a player who is in flow. Direction is
  robust, size is an upper bound.

## 7. Tilt or fatigue? Position × previous result (`tbl_pos_x_prev_result.csv`, `tbl_streak_x_depth.csv`)

If the late-session decline in rapid were accumulated tilt, the post-loss penalty should
grow with depth. It does not:

| rapid, previous game | pos 2–3 | 4–6 | 7–10 | 11–15 |
|---|---|---|---|---|
| after a loss | −0.75 | −0.86 | −1.48 | −0.73 |
| after a win | +0.94 | +1.21 | 0.00 | −0.61 |

Both lines shift down by ~1 pp from position 7, so the decline hits games after wins as
much as games after losses: **fatigue, not tilt.** In blitz and bullet both lines are flat
(after a loss −0.4 to −0.8 at every depth, after a win +0.3 to +0.9), and the LL+ streak
penalty does not grow with depth either (blitz LL+: −1.5 at pos 2–3, −0.3 to −0.7 deeper;
rapid LL+: −1.4 to −1.9 at every depth).

## 8. Whole sessions and habits (`tbl_session_len_resid.csv`, `tbl_user_habit.csv`)

Mean residual of all games in a session, by session length: one-game sessions are strongly
negative (bullet −5.3, blitz −3.2, rapid −1.1 pp) because a one-game session is mostly
"lost and quit"; 4–12-game sessions are +0.8 to +1.3 pp in bullet/blitz (the same survival
selection); **rapid sessions of 13+ games average −1.1 pp** [−1.8, −0.4], the only
length band in any TC that is negative for a non-selection reason. Users' *typical*
session length is not associated with their overall residual in any useful way
(`tbl_user_habit.csv`: users whose median session is one game score +0.5 to +1.3 pp,
everyone else −0.1 to −0.5; a cross-user comparison confounded by who these people are).

## 9. What Noël's rules look like in the data

| rule | verdict |
|---|---|
| Blitz in blocks of 6, quality drops after | Not seen. Results, within-user blunder rate, mistakes, ACPL are flat from game 2 to game 20+; only think time drops (−2.4% by game 11+). If a strong player feels the drop, the population does not show it, at 2400 either (late − early +0.7 pp, blunders 3.72 vs 3.75). |
| Rapid: 2–3 games | Supported, threshold is generous: games 2–6 are at par, the decline starts at game 7 / after about 60 min at the board (−0.7 pp for 7+, −1 to −3 pp beyond 13). Most players never get there (50% of rapid sessions are one game, p90 is 5). |
| Rapid: short pauses between games | Supported for pauses under 10 min (+0.4 to +0.5 pp, +1.0 to +1.5 after a win); pauses of 10–60 min cost 0.7–1.0 pp. In bullet/blitz any pause over a minute costs. |
| (implicit) warm up | The first bullet game is the worst game of the session (−1.65 pp, −2.3 pp at 800), the first blitz game −0.5 pp. Nothing in rapid. |

## 10. Limits

- **Cross-time-control sittings are invisible.** The benchmark import holds each user's
  main time control (96% of a user's games are in one TC; 79% of users have exactly one),
  so a bullet-blitz-bullet evening looks like two bullet games with a pause, and "fatigue
  carried over from another TC" cannot be tested. This also means some in-session
  "pauses" (§6) were games in another TC.
- **No time of day.** Timestamps are UTC with no user timezone, so "7th rapid game" and
  "late evening" cannot be separated. The rapid decline may partly be a clock-time effect.
- **No counterfactual.** "Stop after 6" removes the observed late games, but the games a
  player would have played instead (next day, fresh) are not observed; the late − early
  gap is the size of the marginal effect, not the gain from a rule.
- Residuals are relative to a calibration that ignores everything but rating gap, bucket,
  TC and colour; a session-position effect on the *opponent* (late-night opponents are
  also tired) is folded in.
- The 2400 rapid and all classical cells beyond position 5 are too thin to say anything.

## 11. Story potential

Enough for a short story, and it pairs naturally with the tilt story's "quit on a loss"
and "don't take a short break in bullet" findings. The honest shape is contrarian on the
blitz half of the question and confirmatory on the rapid half:

1. "Sessions are shorter than you think": median 2 blitz games, 1 rapid game, 41–50%
   one-game sessions; the hazard curve (nobody stops at a round number).
2. "Your first bullet game is your worst" with the rating gradient.
3. "Blitz does not wear out, rapid does after an hour": the position curves, the
   flat within-user blunder rate, the think-time slide.
4. "Pause for coffee in rapid, never in bullet": the pause table by TC.
5. Fatigue vs tilt: the decline hits games after wins too.

Numbers to lead with: −1.65 (bullet first game), −0.74 (rapid 7+ vs 2–5), +0.5 (blitz
11+ vs 2–5, "no fatigue"), −1.5 (bullet 3–60 min pause), +0.5 (rapid 3–10 min pause),
−3.7% think time (rapid late). All small in absolute terms (1 pp ≈ 7 Elo per game), which
the story must say plainly, as the tilt story does.
