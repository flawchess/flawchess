---
id: SEED-261120-jnw
status: closed
closed: 2026-11-24
closed_reason: shipped to main as Phase 263 (squash-merge b4c91bc60), not yet deployed
promoted_to: Phase 263 (2026-11-23)
planted: 2026-11-20
planted_during: /gsd-explore session after the 2026-11-20 release (no active phase)
trigger_when: next time Train session composition, the guest / onboarding first session, or the drill_solves source model is touched; or when planning the next Train milestone
scope: medium, one phase (new foreign-blunder selection, one small migration, copy changes, deletion of the lichess filler serving path and of the warm-up concept)
---

# SEED-261120-jnw: Replace lichess sharp fillers with similarly rated players' blunders

Personalized puzzles (Train) fill a short session with a committed set of lichess puzzles. Blunder
check instead serves blunders from similarly rated players when own supply is short. Use that
approach for personalized puzzles too and delete the lichess filler path entirely.

**Promoted 2026-11-23 to Phase 263** (`.planning/ROADMAP.md`).

## Why This Matters

Fillers are a thin bridge, a weak case for a separate puzzle type. Prod, 2026-11-20:

| | Value |
|---|---|
| Filler solves, all time | 795 of about 18,950 (4.2%) |
| Users who ever got one | 167 (14 guests) |
| Median fillers per user | 5 (max 71, nobody near the 208 cap) |
| Filler users who later solved an own blunder | 98 of 167 |
| Last 30 days | 138 solves, 30 users |

- Not rating-matched: the set is 208 puzzles rated 1004 to 1399, the same for an 800 and a 2000
  player.
- A different puzzle type from the product: always "sharp", one solution, no vetted alternative
  moves. A new user's first session misrepresents what follows.
- A foreign blunder carries the same answer-key blob as an own puzzle, so it grades on the normal
  path.

## Decisions (owner, 2026-11-20, revised 2026-11-23)

1. **Swap the supply.** Blunders from similarly rated non-guest users replace the lichess fillers.
2. **Pure filler only.** Served only when the user's own supply is short, the same trigger as
   today's `_backfill_sharp_fillers`. Not a permanent share of every session. `HERRING_SHARE`
   is unchanged.
3. **Delete the serving path, keep the history rows** (revised 2026-11-23, replaces the earlier
   "clean delete"). Drop `app/data/sharp_filler_puzzles.csv`, `app/services/sharp_filler.py`,
   `scripts/gen_sharp_filler_set.py` and every composition, grading and reveal branch for a
   filler. The ~795 solved `source = 2` rows stay as inert history, so session `puzzle_count`,
   points-board totals, frozen `train_weekly_standing` snapshots, streaks and
   `pool_eligible_since` are all untouched. See "What keeping the history costs" below.
4. **Retire the warm-up concept entirely** (2026-11-23). A foreign blunder is the same puzzle
   type as the product, so a session with no own puzzles is no longer a different kind of
   session. Remove `drill_sessions.is_warmup`, `TrainSessionResponse.is_warmup` and every
   `isWarmup` branch in the frontend.

## What keeping the history costs (checked against the code, 2026-11-23)

Light. Nothing re-renders an old filler puzzle: the Archive page is `SR_ITEM` only, and the
leaderboard and Activity read only `source`, points and counts. What stays:

- `DrillSource.SHARP_FILLER = 2` (rename to mark it retired) and the `source IN (...)` CHECK.
- `_NON_FILLER` in `train_leaderboard_repository.py` (keeps old fillers off the Accuracy board;
  the new foreign source needs the same exclusion anyway).
- The `"sharp_filler"` arm of `_wire_source`, only if a read path still serializes old rows;
  the Activity source breakdown keeps its source-2 label.

What needs care:

- **Unsolved filler rows in sessions open at deploy.** With the CSV gone they cannot be served.
  `load_session_puzzles` already skips an unresolvable filler; widen the leniency in
  `_mark_session_complete_if_done` from "filler with NULL `sharp_puzzle_id`" to "any filler" so
  such a row cannot pin a session open.
- **`reveal_for_puzzle` on an old filler** returns `not_found`, the same as an orphaned SR row.
  Confirm the frontend handles that for a session completed just before the deploy.
- **`drill_solves.sharp_puzzle_id`**: meaningless without the CSV. Lean: drop the column (the
  set stays in git history). Keeping it is free but dead.

## Expectation Setting

A quality and consistency win, roughly code-neutral in the backend. A third source arm remains: a
foreign blunder is still "not your game" (no SR state, no `drill_items` row, no open-game link,
different copy, excluded from the Accuracy board). What disappears is the CSV, the generator, the
in-memory lookup, the filler special cases in `answer_key_for` / `server_graded_moves_for`, and
the warm-up flag with its copy variants.

## Supply (measured, prod 2026-11-20)

Games with `blobs_completed_at` set on non-guest accounts, by the player's raw rating at game time
(chess.com and lichess mixed, so bands are approximate):

| Rating | Games | Users |
|---|---|---|
| under 800 | ~174k | 216 to 315 per 200-point band |
| 800 to 1600 | ~469k | 369 to 410 per band |
| 1600 to 2200 | ~345k | 138 to 303 per band |
| 2200 to 2400 | ~42k | 63 |
| 2400+ | ~39k | 21 |

Ample in every band. Above 2400 it comes from very few accounts, so use a nearest-first fallback
like blunder check's. This counts games, not servable blunders: the share that clears
`pool_entry_stmt`'s predicates was not measured per band (the August measurement in
`train_pool.py` found about 795k qualifying own-blunder candidates across 266 users overall).

## Reuse

- `blunder_check_selection.user_level_elo` / `level_fallback_elo`: median pinned Elo of recent
  games, else the stored level, else 1500. Solves the rating for a guest with no games.
- `FOREIGN_RATING_BAND`, the TABLESAMPLE prefilter and the nearest-first fallback are the pattern.
- Not reusable: blunder check's window selection itself (game windows, not single blob-backed
  positions).
- `train_pool.pool_entry_stmt`'s predicates (blunder severity, non-empty `missed_pv_lines`,
  winnability floor, dead band, second-best-not-winning) define a servable foreign blunder.

## Open Items for Planning

- **Snapshot vs live join.** A foreign game can be deleted mid-session or later. `herring_pool`
  denormalizes FEN and ladder; blunder check snapshots start FEN plus UCI moves. Pick one so
  session review and Activity survive a deletion.
- **Copy after warm-up is gone.** `is_warmup` did three jobs in `trainBotCopy`: it picked
  `INTRO_WARMUP_WELCOME_COPY`, it suppressed the "won't come back" tail on every reveal, and it
  branched the score screen. Without it: the welcome must still be truthful for a user with no
  own puzzles (derive from the material flags, not a session column), and the per-puzzle tail
  ("from a similarly rated player's game") must not repeat on all puzzles of an all-foreign
  first session. `FILLER_TAIL` and `TrainStartScreen` need the same rewording.
- **First-session ordering.** `_first_session_order` moves the first sharp puzzle to slot 0, and
  lichess fillers were always sharp. Foreign blunders can be soft, so a new user's first session
  may hold no sharp puzzle. Either the filler draw prefers at least one sharp, or onboarding
  tolerates an all-soft session.
- **Pool eligibility.** `_stamp_pool_eligibility` and the session gate OR in
  `sharp_filler_available()`, which is always true. The replacement is "foreign pool non-empty",
  which is false on a fresh dev DB and in tests.
- **Empty database.** The CSV worked with zero games; a foreign pool does not (fresh dev DB,
  tests). Sessions may be short there, as blunder check already accepts.
- **Source exclusions.** Never guests' games, never the user's own.
- **No-repeat and caps.** Per-user no-repeat for foreign fillers (today keyed on
  `sharp_puzzle_id`) and the one-puzzle-per-game session cap.

## Breadcrumbs

- `app/services/sharp_filler.py`, `app/data/sharp_filler_puzzles.csv`,
  `scripts/gen_sharp_filler_set.py`
- `app/repositories/train_repository.py` (`_select_candidates`, `_backfill_sharp_fillers`,
  `is_warmup`)
- `app/services/train_pool.py` (`pool_entry_stmt`, `answer_key_for`, `server_graded_moves_for`)
- `app/services/blunder_check_selection.py` (foreign selection, `user_level_elo`)
- `app/models/drill_solve.py` (`DrillSource`), `app/repositories/train_leaderboard_repository.py`
  (`_NON_FILLER`), `app/services/activity_queries.py`
- `frontend/src/types/train.ts`, `frontend/src/lib/trainBotCopy.ts`,
  `frontend/src/components/train/TrainStartScreen.tsx`
- Phase 206 (SEED-140) introduced the filler: `.planning/PROJECT.md`
- Related: SEED-261118-rh7 (red herring difficulty gap)
