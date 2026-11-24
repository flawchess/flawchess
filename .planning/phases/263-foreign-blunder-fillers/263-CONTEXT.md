# Phase 263: Similarly Rated Players' Blunders Replace the Lichess Fillers - Context

**Gathered:** 2026-11-23
**Status:** Ready for planning

<domain>
## Phase Boundary

When a personalized-puzzle (Train) session is short of the user's own material, fill it with
servable blunders from non-guest players near the solver's rating. Delete the lichess filler
serving path (CSV, service, generator, every filler branch in composition, grading and reveal)
and retire the warm-up concept. The solved lichess filler rows stay as inert history.

Not in this phase: a standing foreign share in every session, any change to the herring pool or
`HERRING_SHARE`, changes to blunder check's own selection, deleting or rewriting old filler
solves, any way to open a stranger's game.

</domain>

<decisions>
## Implementation Decisions

### Carried in from the seed (owner, 2026-11-20 and 2026-11-23; do not re-open)
- **D-01:** Blunders from similarly rated non-guest users replace the lichess fillers. Never a
  guest's game, never the solver's own.
- **D-02:** Pure filler only. Served only when own supply is short, the same trigger as today's
  `_backfill_sharp_fillers` (every SR shortfall, including the exhausted day, per Phase 206
  D-03 / D-05). Not a standing share. `HERRING_SHARE` is unchanged.
- **D-03:** Delete the serving path, keep the history. Drop `app/data/sharp_filler_puzzles.csv`,
  `app/services/sharp_filler.py`, `scripts/gen_sharp_filler_set.py` and every composition,
  grading and reveal branch for a lichess filler. The ~795 solved `source = 2` rows stay
  untouched, so session `puzzle_count`, points-board totals, frozen `train_weekly_standing`
  snapshots, streaks and `pool_eligible_since` do not move.
- **D-04:** Retire the warm-up concept entirely: `drill_sessions.is_warmup`,
  `TrainSessionResponse.is_warmup` and every `isWarmup` branch in the frontend go. No "warm-up"
  wording anywhere. — **Reversibility:** one-way — the migration drops
  `drill_sessions.is_warmup`; the flag is frozen at composition and cannot be recomputed for
  past sessions.
- **D-05:** The solver's rating is blunder check's `user_level_elo` with `level_fallback_elo`
  (median pinned Elo of recent games, else the stored level, else 1500). `FOREIGN_RATING_BAND`,
  the TABLESAMPLE prefilter and the nearest-first fallback are the pattern to follow.
- **D-06:** `train_pool.pool_entry_stmt`'s predicates define a servable foreign blunder
  (blunder severity, the mover is the game's owner, non-empty `missed_pv_lines`, dead band,
  second-best-not-winning, winnability floor). Same predicates as an own puzzle, no extra ones.

### Deleted source game
- **D-07:** Live join, no snapshot. A foreign puzzle is identified by `(game_id, ply)` on
  `drill_solves` and reads its position and answer key from the foreign game's rows at serve
  time. No pool table, no answer-key columns on `drill_solves` (the table keeps its "no
  answer-key snapshot" rule).
- **D-08:** An unsolved foreign puzzle whose game was deleted (or whose `game_flaws` row
  vanished under reclassification) is dropped from the open session, exactly as an orphaned own
  puzzle is today. The session completes one shorter and such a row must never pin a session
  open.
- **D-09:** A solved foreign puzzle whose game is deleted later keeps its outcome (points,
  guess, move quality), so boards, streaks and Activity counts are unchanged. The position is
  not re-openable; a reveal request reports it as not found, as for an orphaned own puzzle.

### What the solver is told
- **D-10:** Nothing marks a foreign puzzle before it is solved.
- **D-11:** After solving, every foreign puzzle shows one neutral line in the return-tail slot
  (where an own puzzle says "Back next session."), e.g. "From a similarly rated player's game,
  so it won't come back." Shown on every foreign puzzle, including in an all-foreign session.
  It replaces `FILLER_TAIL`.
- **D-12:** Two welcome lines in the intro bubble, without the word warm-up. A session with no
  own puzzles uses the owner's wording: "These puzzles come from games of players at your
  level. Once some of your games are imported and analyzed, puzzles will come from your own
  games." Otherwise the existing "puzzles created from your own games" line stays.
- **D-13:** The exhausted day (an established user, none of their own puzzles due) keeps one
  plain start-screen sentence without a session name, e.g. "None of your own mistakes are due
  today. Today's puzzles come from similarly rated players." It replaces the "Warm-up session"
  title and body of Phase 206 D-08 / D-09.

### Which blunders get picked
- **D-14:** Plain random draw among servable blunders within the rating band. No facepalm cut
  and no preference by facepalm score; the phase does not depend on the facepalm work.
- **D-15:** Rating only. The draw does not match or prefer the solver's time control.
- **D-16:** A user's first-ever session is guaranteed at least one sharp puzzle, so the intro
  order (sharp first, then a several-moves puzzle) always works. About 38% of servable foreign
  blunders are sharp, so this is a preference in the draw, not a supply problem.
- **D-17:** A foreign blunder is never served twice to the same user. No exhaustion re-serve.
  The one-puzzle-per-game session cap (`MAX_ITEMS_PER_GAME_PER_SESSION`) applies.

### Points, streak, Activity
- **D-18:** A solved foreign blunder counts as an old filler did: points on the weekly points
  board, the day's completion and the streak, but not the Accuracy board (own puzzles and
  herrings only). No SR state and no `drill_items` row.
- **D-19:** The admin Activity source breakdown gets a new row for foreign blunders (e.g.
  "Similar player's blunder") and keeps the old row, relabelled as retired (e.g. "Sharp filler
  · lichess (retired)"). The two are never merged.

### The reveal for a foreign blunder
- **D-20:** The reveal shows the blunder that was played, with a label that does not claim it
  as the solver's, e.g. "Played in that game: Qxb7 ??". The existing ownership gate on "Played
  in game" stays for herrings.
- **D-21:** The game is shown as neutral facts only, the same as blunder check's foreign footer
  (Phase 249 D-09): time control, the mover's rating, date. No usernames, no user ids, no
  Analyze deep-link, no link to lichess or chess.com. The owner first picked "with game link"
  and withdrew it after the conflict with 249 D-09 was raised.

### Claude's Discretion
- Whether to drop `drill_solves.sharp_puzzle_id` (lean: drop, it means nothing without the CSV;
  the set stays in git history) and how to name the retired and the new `DrillSource` members
  and wire values. The value 2 must keep meaning "lichess sharp filler".
- Exact copy within D-11 to D-13 and D-19 to D-21, following `frontend/CLAUDE.md` and the
  popover-minimalism feedback. Never call the eval unit "pawns".
- How the client learns a session has no own puzzles (D-12, D-13) without a persisted session
  flag: derive it, do not reintroduce `is_warmup` under another name.
- Handling of sessions open at deploy that hold unsolved lichess filler rows: they cannot be
  served any more and must not pin the session open (widen the leniency in
  `_mark_session_complete_if_done` from "filler with NULL `sharp_puzzle_id`" to "any filler").
- Whether a foreign reveal offers the steppable tactic line. The tactic-lines endpoint reads
  `game_flaws` scoped to the signed-in user; only offer it if that can be done without exposing
  anything beyond D-21.
- What replaces `sharp_filler_available()` in `_stamp_pool_eligibility` and the session gate.
  On an empty foreign pool (fresh dev DB, tests) a session may be short or empty, as blunder
  check already accepts.
- Acceptance criteria and test strategy.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-261120-jnw-foreign-blunders-replace-lichess-fillers.md` — owner
  decisions, prod filler usage numbers, the cost of keeping the history, breadcrumbs
- `.planning/ROADMAP.md` § Phase 263 — goal, scope, out of scope

### Prior decisions this phase replaces or mirrors
- `.planning/milestones/v2.13-phases/206-train-warmup-sharp-filler/206-CONTEXT.md` — introduced
  the lichess filler and the warm-up label (D-03 fills every SR shortfall, D-05 exhausted day,
  D-06 to D-09 the warm-up label and copy, D-15 to D-20 the third source and its reveal). This
  phase undoes D-06 to D-14 and replaces D-17 to D-20.
- Phase 249 CONTEXT D-09 (blunder check foreign game footer: neutral facts, no names) and
  Phase 250 CONTEXT D-13, D-14, D-17 (foreign rating band, user level, level fallback). Find
  them with `find .planning -name "249-CONTEXT.md" -o -name "250-CONTEXT.md"`; they may sit
  under `.planning/phases/` or a milestone archive.

### Project rules
- `CLAUDE.md` — DB design rules (SMALLINT + IntEnum + CHECK for `source`), `Literal` types for
  wire values, nesting-depth gate, Sentry rules, no `asyncio.gather` on one session
- `frontend/CLAUDE.md` — copy, testids, styling rules

No external specs beyond these.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/train_pool.py` `pool_entry_stmt`: the servable-blunder predicates. It filters
  on one `user_id`; the foreign draw needs the same predicates over other users within a rating
  band. `answer_key_for`, `server_graded_moves_for`, `classify_puzzle_type` already grade an SR
  blob and work unchanged on a foreign blunder's `missed_pv_lines`.
- `app/services/blunder_check_selection.py`: `user_level_elo`, `level_fallback_elo`,
  `mover_pinned_elo`, `FOREIGN_RATING_BAND`, `FOREIGN_SAMPLE_PERCENT`,
  `FOREIGN_RAW_PREFILTER_MARGIN`, `_foreign_source`, `_load_nearest_foreign`. The rating and
  the sample-then-check-band pattern are reusable; the window selection is not (it picks game
  windows, not single blob-backed positions).
- `frontend/src/components/train/blunder-check/BlunderCheckGameFooter.tsx` `ForeignGameFooter`
  and the `GameInfo` schema in `app/schemas/blunder_check.py`: the neutral game line for D-21.
- `app/repositories/train_repository.py` `_first_session_order`: already tolerates a session
  with no sharp puzzle; D-16 only needs the draw to supply one.

### Established Patterns
- `drill_solves.game_id` is `ON DELETE SET NULL`; an SR row with a vanished game or flaw is
  lazily evicted in `load_session_puzzles` and excluded in `_mark_session_complete_if_done`.
  D-07 to D-09 reuse this for the foreign source. Note the SR path checks the flaw with
  `GameFlaw.user_id == user_id` (the solver); a foreign puzzle's flaw belongs to another user.
- `uq_drill_solves_session_puzzle (session_id, game_id, ply)` stops a duplicate within a
  session. Per-user no-repeat (D-17) is a query over the user's past foreign `drill_solves`.
  `drill_solves` has no user or game index (Phase 246 WR-01), so check the plan of that query.
- The reveal gates "Played in game" on `game.user_id == user_id` (a herring from another
  user's game must not show it). D-20 adds a separate, neutrally labelled field or label for
  the foreign source rather than loosening that gate.
- `_NON_FILLER` in `app/repositories/train_leaderboard_repository.py` keeps fillers off the
  Accuracy board; the foreign source joins that exclusion (D-18).
- A herring row can share `(user, game, ply)` with an own flaw; the source decides which blob
  is read. Keep that discipline for the third source.

### Integration Points
- Composition: `_select_candidates`, `_backfill_sharp_fillers`, `_assemble_session_items`,
  `_materialize_session_rows`, `_order_first_ever_session` in `train_repository.py`.
- Serving and grading: `load_session_puzzles`, `_position_answer_key`,
  `_answer_keys_by_position`, `_classify_and_certify_solve`, `reveal_for_puzzle`,
  `_wire_source`, `_mark_session_complete_if_done`, `_stamp_pool_eligibility`.
- Model and migration: `app/models/drill_solve.py` (`DrillSource`, `ck_drill_solves_source`,
  `sharp_puzzle_id`), `drill_sessions.is_warmup`.
- Schemas and types: `app/schemas/train.py` (three `source` Literals, `is_warmup`),
  `frontend/src/types/train.ts`, `frontend/src/types/activity.ts`.
- Frontend: `frontend/src/lib/trainBotCopy.ts` (`INTRO_WARMUP_WELCOME_COPY`, `FILLER_TAIL`,
  `returnPhrase`, score-screen warm-up branch), `TrainStartScreen.tsx` (`'warmup'` kind),
  `TrainReveal.tsx`, `TrainVerdictDetails.tsx`, `TrainScoreScreen.tsx`, `TrainSolveScreen.tsx`,
  `pages/Train.tsx`, `components/admin/TrainScoreScreenDemo.tsx`,
  `pages/activity/render.js` and `ActivityPage.tsx` (source rows and their explanation).
- `app/services/activity_queries.py` `fetch_puzzle_difficulty` (rows per source).

</code_context>

<specifics>
## Specific Ideas

- **Prod supply, measured 2026-11-23** (5% TABLESAMPLE of `game_flaws`, scaled by 20; blunders
  clearing all `pool_entry_stmt` predicates on non-guest accounts, by the mover's raw rating at
  game time, chess.com and lichess mixed):

  | Rating | Servable blunders | Users in sample | Sharp share |
  |---|---|---|---|
  | under 800 | ~192k | 292 | 41% |
  | 800 to 1199 | ~223k | 330 | 39% |
  | 1200 to 1599 | ~256k | 345 | 38% |
  | 1600 to 1999 | ~243k | 242 | 37% |
  | 2000 to 2199 | ~85k | 102 | 38% |
  | 2200 to 2399 | ~36k | 45 | 38% |
  | 2400+ | ~33k | 13 | 42% |

  Supply is not a constraint in any band. 2400+ is ample in count but comes from few accounts.
  The bands here use the raw platform rating; the app's band uses the pinned Elo.
- The measurement query's full-scan cost is not the serving cost. The serving draw must be
  checked with EXPLAIN on prod (prod `max_connections` is 50; composition runs in a request).
- The owner's exact wording for the no-own-puzzles welcome is in D-12.
- Research should confirm the frontend copes with a reveal that returns not found for an old
  lichess filler in a session completed just before the deploy.

</specifics>

<deferred>
## Deferred Ideas

- **Open a stranger's game in the analysis board, anonymised.** Needs a cross-user read path
  with its own access rules; it would apply to blunder check's foreign windows too. Raised
  while discussing D-21; not captured as a seed yet.
- **Facepalm-weighted filler draw.** Declined for this phase (D-14); the argument for it is
  that a blunder a player at that level should not make has a best move a player at that level
  can find.

### Reviewed Todos (not folded)
- `todo.match-phase` returned keyword-only matches (e.g. "WR-01 pt-33 is not a valid Tailwind
  class on the Score Y-axis label"); none concern Train session composition, so none were
  folded.

</deferred>

---

*Phase: 263-Similarly Rated Players' Blunders Replace the Lichess Fillers*
