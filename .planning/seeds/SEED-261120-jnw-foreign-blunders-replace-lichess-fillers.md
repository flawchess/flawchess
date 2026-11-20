---
id: SEED-261120-jnw
status: dormant
planted: 2026-11-20
planted_during: /gsd-explore session after the 2026-11-20 release (no active phase)
trigger_when: next time Train session composition, the guest / onboarding first session, or the drill_solves source model is touched; or when planning the next Train milestone
scope: medium, one phase (new foreign-blunder selection, one migration, copy changes, deletion of the lichess filler path)
---

# SEED-261120-jnw: Replace lichess sharp fillers with similarly rated players' blunders

Personalized puzzles (Train) fill a short session with a committed set of lichess puzzles. Blunder
check instead serves blunders from similarly rated players when own supply is short. Use that
approach for personalized puzzles too and delete the lichess filler path entirely.

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

## Decisions (owner, 2026-11-20)

1. **Swap the supply.** Blunders from similarly rated non-guest users replace the lichess fillers.
2. **Pure filler only.** Served only when the user's own supply is short, the same trigger as
   today's `_backfill_sharp_fillers`. Not a permanent share of every session. `HERRING_SHARE`
   is unchanged.
3. **Clean delete.** Retire the existing `source = 2` (`SHARP_FILLER`) `drill_solves` history,
   no read-only legacy path. Drop `app/data/sharp_filler_puzzles.csv`,
   `app/services/sharp_filler.py`, `scripts/gen_sharp_filler_set.py`,
   `drill_solves.sharp_puzzle_id` and the `SHARP_FILLER` source value in one migration.

## Expectation Setting

A quality and consistency win, roughly code-neutral in the backend. A third source arm remains: a
foreign blunder is still "not your game" (no SR state, no `drill_items` row, no open-game link,
different copy, excluded from the Accuracy board). What disappears is the CSV, the generator, the
in-memory lookup and the filler special cases in `answer_key_for` / `server_graded_moves_for`.

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
- **Side effects of retiring history.** 602 of 737 non-guest filler solves sit in `is_warmup`
  sessions that also hold herrings, so deleting rows leaves sessions whose `puzzle_count` no
  longer matches their solves. Points-board totals shift for 167 users. Check frozen
  `train_weekly_standing` snapshots, `pool_eligible_since` / streak accrual for users whose only
  solves were fillers, and the `activity_queries` source breakdown (`frontend/src/types/activity.ts`
  documents source 2).
- **Warm-up semantics and copy.** `is_warmup`, `trainBotCopy` `FILLER_TAIL` and
  `TrainStartScreen` need rewording for "from a similarly rated player's game".
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
