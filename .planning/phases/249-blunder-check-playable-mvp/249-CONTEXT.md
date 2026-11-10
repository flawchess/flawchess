# Phase 249: Blunder-Check Playable MVP (SEED-261108-dk0) - Context

**Gathered:** 2026-11-10 (distilled from SEED-261108-dk0, the Phase 248 calibration report and owner answers in
session; not a discuss-phase run)
**Status:** Ready for planning

<domain>
## Phase Boundary

Blunder check trains the habit of checking your own move before you play it, on stretches of real games, with no
announcement that something critical is about to happen. Phase 248 stored the findability data and calibrated the
selection. This phase makes the drill playable end to end for beta users, so the owner can play it and tune the feel
before Phase 250 builds the schedule, reviews and leaderboards. Deliverables:

1. Window selection service (backend, SQL-first) using the Phase 248 constants.
2. Session and window persistence (every served window and every answer), designed so Phase 250 can add spaced
   repetition, the shared schedule and leaderboards without a data migration of MVP rows.
3. Session API: start a session, fetch the next window, submit answers, finish.
4. Drill UI on a beta-only Train tab: start screen, lead-in replay, arrow prompt, timer, points and forfeits,
   better-move chain, solution screen, session end screen.
5. Umami telemetry for tuning (session start/finish, window outcome, abandon after a forfeit).

</domain>

<decisions>
## Implementation Decisions

### Entry point and audience (owner, 2026-11-10)
- **D-01: Beta-only Train tab.** A 4th tab "Blunder check" on `/train` (beside Today, Leaderboard, Archive), visible
  and reachable only for users with `beta_enabled`. A non-beta user hitting the route or the API gets the normal
  not-found/forbidden behaviour. Start screen with a Start button. No guests in the MVP (guests cannot be beta).
- **D-02: Session size 6 windows**, a named constant (`BLUNDER_CHECK_SESSION_WINDOWS = 6`). Phase 250 turns it into a
  per-mode setting. A session is not tied to the Train schedule, streak or reminders in this phase, and does not
  touch the personalized-puzzle session tables' semantics (see D-14).

### Selection (SEED decisions + Phase 248 calibration, owner 2026-11-10)
- **D-03: Hazard model.** Per window draw the length L uniform over `WINDOW_LENGTHS` = 3..5 user moves and fire the
  blunder at each user move with `HAZARD` = 0.265; the first firing is the blunder position; none within L = herring.
  Then pick a blunder that fits the drawn position, never the other way round (a uniform position leaks, and position
  1 would be over-represented: about a third of misses follow the user's own mistake and only fit position 1).
- **D-04: Good bar.** Every judged user move before the blunder, and every herring move, has an expected-score drop
  below `INACCURACY_DROP` (the flaw pipeline's threshold). Mistakes never count as safe. The lead-in is not checked.
- **D-05: Eval band** [0.10, 0.90] on the pre-move expected score (user's point of view) for every judged user move,
  in blunder windows and herrings. Named constants.
- **D-06: Findability (face-palm test v2), by case** (miss classification from the seed and 248 D-13):
  - allowed (`is_miss` false): `maia_refutation_prob >= R` or `maia_refutation_rank = 1`, R = 0.3;
  - pure miss (`is_miss` and `ES_played >= ES_ref - INACCURACY_DROP`): `maia_best_prob >= X'` or
    `maia_best_rank = 1`, X' = 0.2;
  - mixed (`is_miss` and `ES_played < ES_ref - INACCURACY_DROP`): passes if either test passes.
  No played-probability cap, no top-move-safety rule (face-palm v1 dropped). NULL Maia values do not qualify.
- **D-07: Missed punishments are included with no session cap** (owner, 2026-11-10; replaces `MAX_MISS_SHARE` = 0.30).
  Calibration: pure misses are 19-23% of the usable supply at every rating, so a 30% cap would rarely bind. Keep the
  cap out of the code; reintroduce only if telemetry shows miss windows dominating. Missed-punishment windows use the
  same "Blunder" label, and the window includes the opponent's blunder (as the last lead-in ply when the miss is the
  first judged move).
- **D-08: No low-rating capture/check/mate rule** (owner, 2026-11-10): selection rests on findability alone.
- **D-09: Supply order.** Own games first (user-side blunders and Good moves of the user's own fully evaluated
  games). When the user's unserved own supply cannot fill the drawn window shape, fall back to windows from other
  FlawChess users' games, matched on the mover's rating at game time (band is a named constant; Claude's discretion
  on the value). Own vs foreign is recorded per window. Copy never says "your move" on a foreign game (herring-pool
  precedent).
- **D-10: No repeats in the MVP.** A blunder or herring window already served to the user is not served again, except:
  a blunder window that ended on a false alarm before the blunder was reached returns to the pool as unseen (herring
  false alarms are simply dropped). Re-serving missed blunders is Phase 250's spaced repetition.
- **D-11: Session composition** is whatever the hazard model draws per window (about 30% herrings), no forced mix.

### Drill interaction and scoring (SEED decisions, owner 2026-11-09)
- **D-12: Flow per window.** Replay `LEAD_IN_PLIES` = 3 plies (opponent, user, opponent) at a fixed pace (whatever
  exists near the game start), stop on the first judged user move: the move is shown as an arrow with the piece still
  on its source square, prompt "Safe / Blunder". The answer is asked before the move is played and before the
  opponent's reply appears.
  - Correct "safe": +1 point (`SAFE_POINTS`), small animation and sound (reuse Train's point badges and sounds), play
    the user's move and the opponent's reply, show the next arrow.
  - Correct "blunder": +3 (`BLUNDER_POINTS`), then "find the better move" for +2 (`BETTER_MOVE_POINTS`), graded like
    personalized puzzle training. Then the solution screen.
  - False alarm (flagging a safe move): the window ends.
  - Missed blunder (answering "safe" on the blunder): the window's accumulated safe points are forfeited, shown being
    discarded with a small animation and the 0-points feedback sound; then the solution screen.
  - Herring completed: no extra payoff beyond the per-move points.
- **D-13: Timer** 15 s per judged user move (`MOVE_TIMER_SECONDS`). Timeout on a safe move loses that point and
  forfeits all safe points accumulated in the window (same animation and sound); the window continues and the
  blunder can still be caught. Timeout on the blunder move counts as a missed blunder.
- **D-14: Solution screen.** Reuse the personalized-puzzle solution screen pieces: Best and Game cards, line and
  position exploration, game info, Analyze button (deep link to `/analysis`). Session end screen shows points and
  Score % for the session (Score % = points scored / points possible; possible per window = 1 per judged safe move
  plus `BLUNDER_POINTS` + `BETTER_MOVE_POINTS` when it holds a blunder, including the unreached blunder after a false
  alarm).
- **D-15: Persistence from day one.** Store sessions, served windows (game, plies, shape, case, own/foreign, answer
  key) and per-move answers with timing and outcome, so Phase 250 can compute leaderboards, reviews and the
  cross-mode cooldown from MVP data. Own tables (SMALLINT IntEnum + CHECK for high-volume enum columns, TEXT + CHECK
  for low-volume ones, FKs with `ondelete`), not new columns on the personalized-puzzle tables, unless research shows a
  clean shared-session design; the planner decides with the reasoning written down.
- **D-16: Answer key is server-side.** The client gets the window (positions, lead-in, the judged moves as arrows)
  but not which move is the blunder; answers are graded by the server so the key cannot be read from the payload.

### Claude's Discretion
- Selection mechanics (on-the-fly SQL per session vs a precomputed window pool like `herring_pool`), as long as a
  session starts fast (target well under 1 s server time) and D-03 holds.
- Rating band for the foreign-game fallback; preference for older games where cheap.
- Pacing of the lead-in replay and animation details, within the existing Train look and sound set.
- Exact API shape (one call per answer vs batched), within the D-16 constraint.
- Moving reusable pure functions from `scripts/blunder_check/metrics.py` into `app/services/` (the app must not
  import from `scripts/`); the calibration report then imports the app versions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md`: the full feature design and every owner decision
  (some superseded here: D-07 no miss cap, D-08 no low-rating rule, D-02 session size)
- `reports/blunder-check/blunder-check-calibration-2026-11-10.md`: recommended constants, pass shares by Elo bucket and
  case, window fit and supply per user (median about 927 blunder windows; 43 of 579 users under 50)
- `reports/blunder-check/spot-check-2026-11-10.md`: 120 sample windows drawn the way the feature should draw them
- `.planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-CONTEXT.md` and
  `248-RESEARCH.md`: refutation columns, ply conventions for the refutation move, miss classification, the ES ply
  convention traps
- `.planning/notes/eval-completion-columns.md`: which games count as fully evaluated

</canonical_refs>

<code_context>
## Existing Code Insights

- Selection math to port: `scripts/blunder_check/metrics.py` (`user_move_judgements`, `blunder_es`, `miss_case`,
  `in_band`, `blunder_fits_position`, `hazard_position_weights`, `findable`) and `scripts/blunder_check/spot_check.py`
  (`draw_window_shape`, `pick_windows`: the hazard draw and window assembly already work on prod data).
- ES and per-ply evals: `app/services/train_pool.py` (`expected_score_sql`, `expected_score_for`, `replay_at_ply`,
  `full_fen_at_ply`, `herring_stmt`, `pick_one_per_game`, `_vetted_move`, `server_graded_moves_for` for better-move
  grading), `app/services/flaws_service.py` (`_is_miss`, thresholds).
- Train persistence and API: `app/models/drill_session.py`, `drill_item.py`, `drill_solve.py`, `herring_pool.py`,
  `app/routers/train.py`, `app/services/train_score.py`.
- Maia data: `game_flaws.maia_refutation_prob/rank` (user-side blunders), `maia_best_prob/rank`,
  `games.maia_refutation_completed_at`; `app/services/best_move_candidates.py` `pinned_elo_for_mover`.
- Frontend: `frontend/src/components/train/` (`TrainSubnav.tsx` tabs, `TrainSolveScreen.tsx`, `TrainReveal*`,
  `TrainScoreBadge.tsx`, `TrainScoreScreen.tsx`), `frontend/src/lib/sounds.ts`, `trainArrows.ts`, `trainRoute.ts`,
  `trainTelemetry.ts`, `analysisUrl.ts`; beta flag via `useUserProfile().data.beta_enabled` (not `useAuth().user`).

</code_context>

<specifics>
## Specific Ideas

- Project memory traps that apply: eval_cp has two ply conventions (lichess post-move vs entry-lane aligned); the
  herring pool is cross-user, so ownership-gate any "your move" copy; read `beta_enabled` from the user profile;
  `board.board_fen()` vs full FEN (rebuild exact positions from `games.pgn`); guests excluded from selection.
- The owner reviews the spot-check in parallel; findings may adjust constants but should not change the design.

</specifics>

<deferred>
## Deferred Ideas (Phase 250 or later)

- Shared Train schedule and reminders, per-mode session size with 0 allowed, session streak across both modes.
- Spaced repetition of missed-blunder windows (4 days, re-drawn shape, unlabelled; fallback to the original window
  when a re-draw cannot fit).
- Cross-mode cooldown with personalized puzzles (`CROSS_MODE_COOLDOWN_DAYS`).
- Points and Score % leaderboards with medals and a minimum window count.
- Guests and non-beta launch; replacing the lichess warm-up puzzles with similarly rated users' flaws.
- A `MAX_MISS_SHARE` cap or the low-rating capture/check/mate rule, only if telemetry or the spot-check calls for it.

</deferred>

---

*Phase: 249-blunder-check-playable-mvp*
*Context gathered: 2026-11-10*
