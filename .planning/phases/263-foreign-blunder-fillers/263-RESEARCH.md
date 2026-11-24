# Phase 263: Similarly Rated Players' Blunders Replace the Lichess Fillers - Research

**Researched:** 2026-11-23
**Domain:** Train session composition (SQLAlchemy async / PostgreSQL), DrillSource model + Alembic migration, React reveal/landing copy
**Confidence:** HIGH for the code inventory and integration points (every site read this session); MEDIUM for the draw's prod cost (needs the prod EXPLAIN below); LOW only where tagged `[ASSUMED]`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried in from the seed (owner, 2026-11-20 and 2026-11-23; do not re-open)
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

#### Deleted source game
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

#### What the solver is told
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

#### Which blunders get picked
- **D-14:** Plain random draw among servable blunders within the rating band. No facepalm cut
  and no preference by facepalm score; the phase does not depend on the facepalm work.
- **D-15:** Rating only. The draw does not match or prefer the solver's time control.
- **D-16:** A user's first-ever session is guaranteed at least one sharp puzzle, so the intro
  order (sharp first, then a several-moves puzzle) always works. About 38% of servable foreign
  blunders are sharp, so this is a preference in the draw, not a supply problem.
- **D-17:** A foreign blunder is never served twice to the same user. No exhaustion re-serve.
  The one-puzzle-per-game session cap (`MAX_ITEMS_PER_GAME_PER_SESSION`) applies.

#### Points, streak, Activity
- **D-18:** A solved foreign blunder counts as an old filler did: points on the weekly points
  board, the day's completion and the streak, but not the Accuracy board (own puzzles and
  herrings only). No SR state and no `drill_items` row.
- **D-19:** The admin Activity source breakdown gets a new row for foreign blunders (e.g.
  "Similar player's blunder") and keeps the old row, relabelled as retired (e.g. "Sharp filler
  · lichess (retired)"). The two are never merged.

#### The reveal for a foreign blunder
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

### Deferred Ideas (OUT OF SCOPE)
- **Open a stranger's game in the analysis board, anonymised.** Needs a cross-user read path
  with its own access rules; it would apply to blunder check's foreign windows too. Raised
  while discussing D-21; not captured as a seed yet.
- **Facepalm-weighted filler draw.** Declined for this phase (D-14); the argument for it is
  that a blunder a player at that level should not make has a best move a player at that level
  can find.

#### Reviewed Todos (not folded)
- `todo.match-phase` returned keyword-only matches (e.g. "WR-01 pt-33 is not a valid Tailwind
  class on the Score Y-axis label"); none concern Train session composition, so none were
  folded.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped; the contract is D-01..D-21. Mapping to the research that enables each:

| ID | Description (short) | Research Support |
|----|---------------------|------------------|
| D-01 | non-guest, never solver's own | Draw SQL `users.is_guest IS false`, `g.user_id != :solver` (§ Foreign draw design) |
| D-02 | pure filler, same trigger | Replace `_backfill_sharp_fillers` call at `train_repository.py:2984-2988` (§ Pipeline) |
| D-03 | delete serving path, keep rows | § Touchpoint inventory (delete list), legacy-row handling (§ Schema and migration) |
| D-04 | retire warm-up | § Touchpoint inventory (warm-up list), migration drops `is_warmup` |
| D-05 | rating via blunder check helpers | `user_level_elo` / `level_fallback_elo` reuse, raw prefilter + pinned check (§ Foreign draw design) |
| D-06 | pool_entry_stmt predicates | Predicates reused verbatim across users; compiled SQL in § Prod EXPLAIN request |
| D-07 | live join | Owner-scoped joins (§ Solver-ownership assumptions) |
| D-08 | deleted game dropped, never pins open | `load_session_puzzles` + `_mark_session_complete_if_done` changes; Pitfall 5 (last-puzzle orphan) |
| D-09 | solved outcome kept, reveal not_found | `reveal_for_puzzle` gate extended to foreign |
| D-10 | nothing marks foreign pre-solve | `TrainPuzzle` carries no source; recommend wire `game_id=None` (§ D-21 wire) |
| D-11 | per-puzzle tail | `returnPhrase` in `trainBotCopy.ts:566-580` |
| D-12/D-13 | intro + start-screen copy | Derived `own_puzzle_count` (§ Client derivation) |
| D-14/D-15 | plain random, rating only | Seeded Python pick over SQL candidates |
| D-16 | first-ever session has a sharp | sharp-preferring pick + `_composition_puzzle_types` must read foreign blobs (Pitfall 3) |
| D-17 | per-user no-repeat, per-game cap | served-set query + exclude session game_ids (§ Foreign draw design) |
| D-18 | points/streak yes, Accuracy no | `_NON_FILLER` at `train_leaderboard_repository.py:82` |
| D-19 | Activity rows | `render.js:385-390`, `ActivityPage.tsx:556-564`, `docs/activity-dashboard.md:134-137` |
| D-20 | played move, neutral label | reveal `played_in_game_san` via owner's `game_positions` |
| D-21 | neutral game facts | reuse `GameInfo` / `ForeignGameFooter` (§ Reveal) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend: FastAPI, Python 3.14, SQLAlchemy 2.x async `select()` API, Alembic, asyncpg. PostgreSQL only.
- Routers HTTP only; business logic in services; SQL in repositories (`train_repository.py` already holds Train SQL; `train_pool.py` holds reusable statement builders).
- **Never `asyncio.gather` on one `AsyncSession`** — every await in the draw is sequential.
- DB rules: FK with explicit `ondelete`; `source` stays SMALLINT + Python `IntEnum` + `CHECK (col IN (...))` (no native ENUM).
- No magic numbers: every new limit (candidate games, sample percent if Train-specific) is a named constant.
- `Literal[...]` for every fixed value set (wire `source` Literals in `app/schemas/train.py`, repository dataclasses).
- ty: zero errors, explicit return types, `Sequence[...]` for `list[Literal]` params, `# ty: ignore[rule]` only when unfixable.
- Nesting depth <= 4 (gated by `scripts/check_function_size.py app/ --fail-over-depth 4`, eslint `max-depth`); soft ~100 logic lines, cognitive <= 15. Split along real seams (`_fetch` / `_pick` / `_reconstruct`).
- Sentry: `capture_exception` in non-trivial `except` blocks in services/routers; never variables in error messages.
- Comment every bug fix at the fix site.
- Time-dependent code uses the `dev_now_utc` dependency; composition already receives `now_utc`.
- Pre-merge gate (ruff format/check, ty app/tests/scripts + analysis, depth gate, `pytest -n auto -x`, frontend lint/build/test/knip) before squash-merge; CHANGELOG `## [Unreleased]` bullet when merging.
- Frontend (`frontend/CLAUDE.md`): `data-testid` on interactive elements, `text-sm` floor, knip fails on dead exports (delete exports with the feature), `npm run build` needed to type-check, no `variant="secondary"` for secondary actions.
- Copy: em-dashes sparingly; never "pawns" for eval.
- Memory rules that bite here: every non-guest `Game` insert in a committing test needs finally-cleanup (global draws see other tests' rows); `uv run pytest -n auto` locally, but serial CI must also pass (migration downgrade round-trips have collided with committed rows before, see Phase 206 migration's downgrade bug-fix note); no dev DB reset in plans; worktree has no DB config (run DB-backed tests from a checkout with DB env, or via the dev DB container on the host).

## Summary

The lichess filler is wired through about 25 backend sites in one file (`app/repositories/train_repository.py`), two `train_pool.py` functions (`answer_key_for`, `server_graded_moves_for`), the model/schemas, the leaderboard's `_NON_FILLER`, and ~15 frontend files. Warm-up is a single persisted boolean (`drill_sessions.is_warmup`, frozen at composition from `len(surviving_sr_keys) == 0`) plus its wire field and a set of copy branches (intro welcome, return tail suppression, score-screen branch, a dead `'warmup'` landing kind). Everything is enumerated with file:line below, including ~20 backend test files and ~12 frontend test files that seed or assert filler/warm-up.

The foreign draw should reuse `pool_entry_stmt`'s predicate builders over a TABLESAMPLE game prefilter, in two stages inside one statement: a CTE picks ~200 random sampled games owned by non-guest strangers whose raw owner rating sits in `level ± (FOREIGN_RATING_BAND + FOREIGN_RAW_PREFILTER_MARGIN)`, then the servable owner blunders on those games are read with the exact own-pool predicates. Python then applies the pinned-Elo band (`FOREIGN_RATING_BAND`), the per-user no-repeat set, the session's per-game cap (including herring game ids, which can collide on `uq_drill_solves_session_puzzle`), a seeded random pick with a sharp preference for a first-ever session, and nearest-first fallback; a second wide-sample nearest query runs only for thin rating tails. The exact SQL is in `## Prod EXPLAIN request`.

The biggest correctness risk is not the draw but the many places that join `game_flaws` / `game_positions` on `DrillSolve.user_id` (the solver). A foreign row's flaw belongs to the game's owner, so seven sites must join on the owner instead (`load_session_puzzles`, `_composition_puzzle_types`, `_answer_keys_by_position`, `_classify_sr_solve`, `_mark_session_complete_if_done`, `reveal_for_puzzle`, `_game_move_is_facepalm`). Missing one silently degrades a foreign puzzle to "soft, no key" or pins a session open, with no type error.

**Primary recommendation:** Add `DrillSource.FOREIGN_BLUNDER = 3` (wire `"foreign_blunder"`), rename value 2 to `LEGACY_SHARP_FILLER` keeping wire `"sharp_filler"` for reads of old rows, replace `_backfill_sharp_fillers` with a foreign stage at the same post-reconstruction point, route every SR-style read through an owner-aware join gated on source, derive `own_puzzle_count` per response instead of `is_warmup`, null `game_id` on the wire for foreign puzzles, and stub the foreign draw by default in `tests/conftest.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Foreign candidate SQL (TABLESAMPLE + pool predicates) | Database / Storage | API (statement builder in `train_pool.py`) | Predicates are SQL expressions already living in `train_pool.py`; the draw is one statement |
| Rating level, pinned-Elo band, pick, sharp preference | API / Backend (repository-side Python) | — | Pinned Elo is Python-only (`pinned_elo_for_mover` table interpolation) |
| Owner-aware answer key / grading / reveal | API / Backend | Database | Same `answer_key_for` path as SR; joins must target the game owner |
| Legacy source-2 tolerance (wire, completion leniency) | API / Backend | Database (CHECK keeps 2) | Old rows must still serialize and never pin sessions |
| Schema change (CHECK, drop columns) | Database / Storage | — | Alembic migration |
| "No own puzzles" signal | API / Backend (derived count) | Browser (copy branch) | Client cannot derive it (no per-puzzle source pre-attempt) |
| Tail / intro / start / score copy, neutral footer | Browser / Client | — | Pure copy and existing components |
| Activity source rows | Browser (`render.js`) | API (`fetch_puzzle_difficulty` already groups by source) | New source appears in SQL automatically |

## Standard Stack

No new libraries. Everything uses what the repo already ships.

### Core (in-repo, reused)
| Module / symbol | Location | Purpose | Why |
|---|---|---|---|
| `pool_entry_stmt` predicate builders: `answer_key_present`, `dead_band_admissible`, `second_best_not_winning_admissible`, `expected_score_sql`, `_prior_position_lateral`, `player_only_gate` | `app/services/train_pool.py:708-1051`, `app/repositories/query_utils.py:132-149` | Servable-blunder definition (D-06) | Single source of the own-pool standard; reusing keeps own and foreign identical |
| `answer_key_for`, `server_graded_moves_for`, `classify_puzzle_type`, `legal_answer_key` | `app/services/train_pool.py:275-705` | Key, type, graded set | A non-herring, non-filler source already takes the SR branch |
| `user_level_elo`, `level_fallback_elo`, `USER_LEVEL_SCAN_GAMES`, `FOREIGN_SAMPLE_PERCENT`, `FOREIGN_RAW_PREFILTER_MARGIN`, `FOREIGN_WIDE_SAMPLE_PERCENT`, `FOREIGN_NEAREST_POOL_GAMES` | `app/services/blunder_check_selection.py:96-221` | Solver level and sampling pattern (D-05) | Locked by D-05 |
| `FOREIGN_RATING_BAND` | `app/services/blunder_check_rules.py:164` | Pinned-Elo band | Locked by D-05 |
| `blunder_check_repository.recent_rated_games` | `app/repositories/blunder_check_repository.py:829-858` | Level source rows | Same input blunder check uses |
| `pinned_elo_for_mover`, `is_correspondence_time_control` | `app/services/best_move_candidates.py:79`, `app/services/normalization.py:34` | Candidate mover pinned Elo | Public; `blunder_check_selection._pinned` is private |
| `GameInfo` schema / `ForeignGameFooter` | `app/schemas/blunder_check.py:191-197`, `frontend/src/components/train/blunder-check/BlunderCheckGameFooter.tsx:41-52` | D-21 neutral facts | Same rule as 249 D-09 |

Verbatim values used in this research [VERIFIED: files read this session]:
- `app/services/blunder_check_rules.py:164`: `FOREIGN_RATING_BAND: int = 150`
- `app/services/blunder_check_selection.py:96`: `FOREIGN_SAMPLE_PERCENT: float = 2.0`; `:99`: `FOREIGN_RAW_PREFILTER_MARGIN: int = 500`; `:102`: `FOREIGN_NEAREST_POOL_GAMES: int = 400`; `:105`: `FOREIGN_WIDE_SAMPLE_PERCENT: float = 20.0`; `:107`: `USER_LEVEL_SCAN_GAMES: int = 200`; `:112`: `DEFAULT_USER_LEVEL_ELO: float = 1500.0`; `:115-119`: `"beginner": 1000.0, "intermediate": 1500.0, "advanced": 2000.0`
- `app/services/train_pool.py:73`: `WINNABILITY_FLOOR_ES: float = 0.20`; `:105`: `_SEVERITY_BLUNDER: int = 2`; `:108`: `HERRING_SHARE: float = 0.25`; `:122`: `MAX_ITEMS_PER_GAME_PER_SESSION: int = 1`
- `app/repositories/query_utils.py:57`: `AnalyticsPlatform = Literal["chess.com", "lichess"]`
- `app/repositories/train_repository.py:219`: `blunder_check_level: BlunderCheckLevel | None = None` (on `TrainSettingsRow`)

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages (backend or frontend). **Packages removed due to [SLOP]:** none. **Packages flagged [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
POST /train/sessions (Today mount)
   |
   v
compose_and_materialize_session
   |-- settings, today, expire_stale_sessions, blob_pending
   |-- _resolve_existing_session --(open/completed in window)--> _resume_session
   |        |                                                      |-- load_session_puzzles  [SR | herring | FOREIGN(owner join) | LEGACY(skip)]
   |        |                                                      |-- solved_results via _wire_source (keeps "sharp_filler")
   |        |                                                      '-- own_puzzle_count (derived COUNT of SR rows)
   |        v
   |   _assemble_session_items
   |        |-- _select_candidates  (due SR -> SR pool -> herrings, unchanged)
   |        |-- reconstruct SR + herring FENs
   |        |-- shortfall = n - len(reconstructed)  > 0 ?
   |        |        v
   |        |   _backfill_foreign_blunders  (replaces _backfill_sharp_fillers)
   |        |        |-- level = user_level_elo(recent_rated_games, fallback=level_fallback_elo(settings.blunder_check_level))
   |        |        |-- served = {(game_id, ply)} of solver's FOREIGN rows
   |        |        |-- SQL: TABLESAMPLE games (non-guest, != solver, raw band) -> random 200 -> owner blunders with pool predicates
   |        |        |-- Python: drop served, drop session game_ids, pinned-Elo band, seeded pick (one per game, sharp first if first-ever)
   |        |        |-- short? nearest-first over loaded rows -> short? wide-sample nearest SQL
   |        |        '-- load PGN of picks -> fen_and_last_move_at_ply (drop failures)
   |        '-- shuffle (user_id, today)
   |-- _order_first_ever_session (types must read FOREIGN blobs via owner)
   |-- _materialize_session_rows (no drill_items for FOREIGN; no is_warmup; no sharp_puzzle_id)
   |-- stamp pool_eligible_since if a session row was written (replaces sharp_filler_available())
   '-- _attach_answer_keys -> _answer_keys_by_position (owner-aware joins)
            |
            v
TrainSessionResponse (FOREIGN puzzle: game_id None on wire, no source field)

POST /solve -> record_solve -> _classify_and_certify_solve
      [herring | LEGACY: sharp, no key | SR: solver flaw | FOREIGN: owner flaw]
      -> _resolve_grade -> no drill_items for non-SR -> _mark_session_complete_if_done (owner-aware, legacy excluded)
GET /reveal -> reveal_for_puzzle  [FOREIGN: owner move SAN, owner facepalm, game_info, game_id None; LEGACY: not_found]
```

### Recommended module placement

```
app/services/train_pool.py          # + foreign_candidate_stmt(...) and foreign_nearest_stmt(...) next to pool_entry_stmt
                                    #   (statement builders only; reuse the predicate helpers in place)
app/repositories/train_repository.py
    _backfill_foreign_blunders      # replaces _backfill_sharp_fillers (2604-2663): orchestrates SQL + pick + reconstruct
    _pick_foreign(...)              # PURE function (no I/O): band, served, per-game, sharp-first, seeded; unit-testable
app/models/drill_solve.py           # DrillSource: LEGACY_SHARP_FILLER = 2, FOREIGN_BLUNDER = 3
alembic/versions/2026MMDD_..._phase_263_foreign_blunder_source.py
```
Import check: `train_repository` importing `blunder_check_selection` is cycle-free. `blunder_check_selection` imports only `blunder_check_repository`, `blunder_check_rules`, `blunder_check_candidates`, `blunder_check_feedback`, `facepalm_score`, `best_move_candidates`, `normalization`, `train_scheduler`; none of those import `train_repository` [VERIFIED: grep of `^from app` heads this session]. `blunder_check_service` imports both, which is fine. Do not move `user_level_elo` into a shared module (that is a blunder-check refactor, out of scope).

### Pattern 1: Owner-aware join, gated on source
**What:** A foreign row's `game_flaws` / `game_positions` rows are keyed by the game owner (`game_flaws` PK is `(user_id = game owner, game_id, ply)`, `app/models/game_flaw.py:1-4, 71-82`). Join them through `games.user_id`, and only read them for SR and FOREIGN sources.
**When:** every site in § Solver-ownership assumptions.
**Example (shape, not final code):**
```python
# Source: derived from train_repository._answer_keys_by_position (3226-3260)
ForeignFlaw = aliased(GameFlaw)
ForeignPosition = aliased(GamePosition)
stmt = (
    select(..., GameFlaw.missed_pv_lines, ForeignFlaw.missed_pv_lines, ...)
    .select_from(DrillSolve)
    .outerjoin(Game, Game.id == DrillSolve.game_id)
    # SR join stays byte-identical (solver-scoped)
    .outerjoin(GameFlaw, and_(GameFlaw.user_id == DrillSolve.user_id,
                              GameFlaw.game_id == DrillSolve.game_id, GameFlaw.ply == DrillSolve.ply))
    # FOREIGN join: owner-scoped, only for the foreign source
    .outerjoin(ForeignFlaw, and_(DrillSolve.source == DrillSource.FOREIGN_BLUNDER,
                                 ForeignFlaw.user_id == Game.user_id,
                                 ForeignFlaw.game_id == DrillSolve.game_id, ForeignFlaw.ply == DrillSolve.ply))
    .where(DrillSolve.session_id == session_id, DrillSolve.user_id == user_id, ...)
)
```
Keeping the SR join untouched keeps the existing "a herring row can share (user, game, ply) with an own flaw" discipline intact (`_position_answer_key` docstring, `train_repository.py:3164-3169`).

### Pattern 2: Two-stage TABLESAMPLE draw in one statement
Stage 1 (CTE): `games TABLESAMPLE SYSTEM(p)` joined to `users`, `user_id != solver`, `is_guest IS false`, `platform IN ANALYTICS_INCLUDED_PLATFORMS`, raw owner rating between `level ± (150 + 500)`, `ORDER BY random() LIMIT 200`. Stage 2: join `games` + `game_flaws (user_id = games.user_id)` + the winnability LATERAL and apply the six `pool_entry_stmt` predicates. Pure Python afterwards. See § Foreign draw design and the compiled SQL.

### Pattern 3: Legacy value kept for reads only
`DrillSource(2)` stays a member (renamed) so `_wire_source` can serialize the ~795 solved rows (and any unsolved rows in sessions open at deploy) inside `_resume_session`'s `solved_results` (`train_repository.py:2284-2295`). Every *behaviour* branch is deleted; only "skip / exclude / serialize" remains.

### Anti-Patterns to Avoid
- **A "foreign pool non-empty" EXISTS as the eligibility gate.** A TABLESAMPLE-based check is random per call, so `pool_eligible_since` would stamp nondeterministically. Stamp from the fact that a session row was written instead (§ Eligibility).
- **Copying blunder check's `LIMIT` without `ORDER BY random()`.** See Pitfall 1.
- **Loosening the herring "Played in game" ownership gate** (`reveal_for_puzzle`, `4665-4676`) to serve D-20. Add a separate FOREIGN branch.
- **Reintroducing `is_warmup` as a persisted column under another name.** Derive per response.
- **Reading PGN for every candidate.** Select light columns in the draw, load `Game.pgn` only for the picks.

## Touchpoint Inventory (the delete / change list)

All line numbers read this session in the worktree [VERIFIED: file reads]. "DEL" = delete, "CHG" = change, "KEEP" = intentionally kept.

### Backend: files to delete
| Path | Size | Note |
|---|---|---|
| `app/services/sharp_filler.py` | 164 lines | `SHARP_SET`, `SHARP_SET_BY_ID`, `pick_sharp_fillers`, `served_sharp_ids_stmt`, `sharp_filler_available` |
| `app/data/sharp_filler_puzzles.csv` | 215 lines | Only consumer is `sharp_filler.py:34-36` and the generator |
| `scripts/gen_sharp_filler_set.py` | 536 lines | Reads `fixtures/tagger/detector_fixture_{train,test}.csv` (KEEP those, tagger tests use them) |
| `tests/services/test_sharp_filler.py` | 322 lines | imports the generator too (`:52`) |
| `tests/scripts/test_gen_sharp_filler_set.py` | 197 lines | |

No packaging, Dockerfile, CI or `frontend/src/generated/*` reference to the CSV or the generator [VERIFIED: grep]. No `scripts/gen_*` output depends on fillers. `docs/dev-tooling.md` has no entry for the generator [VERIFIED: grep returned nothing outside `docs/activity-dashboard.md`].

### Backend: `app/models/drill_solve.py`
- CHG `:56-60` module docstring paragraph about `SHARP_FILLER` / `sharp_puzzle_id`.
- CHG `:87-93` enum. Current verbatim: `SR_ITEM = 0`, `RED_HERRING = 1`, `SHARP_FILLER = 2`. Proposed: `LEGACY_SHARP_FILLER = 2` (value unchanged), `FOREIGN_BLUNDER = 3`.
- CHG `:126` verbatim `CheckConstraint("source IN (0, 1, 2)", name="ck_drill_solves_source")` -> `"source IN (0, 1, 2, 3)"`.
- DEL (discretion, recommended) `:161-165` verbatim `sharp_puzzle_id: Mapped[str | None] = mapped_column(Text, nullable=True)`; then drop the now-unused `Text` import if nothing else uses it.

### Backend: `app/models/drill_session.py`
- DEL `:306-310` verbatim `is_warmup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")` and its comment; drop `Boolean` from imports if unused.

### Backend: `app/services/train_pool.py`
- CHG `:199-203` comment "A sharp filler reads "sharp"".
- CHG `:370-399` `answer_key_for`: drop the `filler_solution_uci` parameter and the `SHARP_FILLER` arm (`:395-396`). FOREIGN falls through to the SR branch (correct: mover = owner = ply parity).
- CHG `:645-687` `server_graded_moves_for`: `:678` verbatim `if source == DrillSource.SHARP_FILLER or not missed_pv_lines:` -> `if not missed_pv_lines:`; docstring `:662-666`.
- CHG `:88-95` comment mentions "sharp-filler cross-backfill"; `:1358-1365` `compose_slots` docstring calls herrings "filler" (harmless wording; optional).
- ADD `foreign_candidate_stmt` / `foreign_nearest_stmt` (statement builders).

### Backend: `app/repositories/train_repository.py`
| Lines | Site | Action |
|---|---|---|
| 68-73 | `from app.services.sharp_filler import ...` | DEL |
| 226-255 | `ComposedPuzzle` | KEEP shape; construct FOREIGN with `game_id=None` for the wire (see § D-21 wire) or add an internal flag |
| 267-289 | `ComposedSolvedResult.source` Literal `"sr_item", "red_herring", "sharp_filler"` | CHG add `"foreign_blunder"`, KEEP `"sharp_filler"` |
| 292-332 | `ComposedSession.is_warmup` + docstring | DEL; ADD `own_puzzle_count: int` (derived) |
| 953-997 | `_stamp_pool_eligibility` docstring mentions `sharp_filler_available()` | CHG docstring |
| 2099-2232 | `load_session_puzzles`: SR flaw check `GameFlaw.user_id == user_id` (2163-2168); SHARP_FILLER arm 2172-2190 | CHG: LEGACY rows `continue`; FOREIGN rows need `game is not None`, owner flaw exists, FEN reconstructs |
| 2235-2310 | `_resume_session`: `_wire_source(row.source)` (2288), `is_warmup=drill_session.is_warmup` (2306-2309) | CHG: drop is_warmup; add own_puzzle_count (one COUNT FILTER over the session's rows) |
| 2353-2372 | `_ReconstructedPuzzle.sharp_puzzle_id` | DEL field |
| 2571-2577 | comment "filled by sharp fillers" | CHG |
| 2604-2663 | `_backfill_sharp_fillers` | DEL, replace with `_backfill_foreign_blunders` |
| 2802-2841 | `_composition_puzzle_types`: SR-only blob load, `GameFlaw.user_id == user_id`, `filler_solution_uci=None` | CHG: also load FOREIGN blobs via owner (Pitfall 3) |
| 2844-2865 | `_order_first_ever_session` docstring mentions `is_warmup` | CHG |
| 2868-2886 | `_AssembledSessionItems.is_warmup` | DEL |
| 2889-3016 | `_assemble_session_items`: `sharp_puzzle_id=None` (2954, 2974), sharp stage (2977-2988), `is_warmup` (2991-2994, 3006-3015) | CHG: foreign stage at the same point |
| 3019-3149 | `_materialize_session_rows`: `is_warmup=` (3080, 3148), `sharp_puzzle_id=` (3105) | CHG |
| 3152-3202 | `_position_answer_key(sharp_puzzle_id=...)`, `filler_row` (3171), `filler_solution_uci` (3183-3187), `is_sr` (3172) | CHG: drop filler; `is_sr` -> source in (SR, FOREIGN) |
| 3205-3274 | `_answer_keys_by_position`: selects `DrillSolve.sharp_puzzle_id` (3231); SR joins on `DrillSolve.user_id` (3241, 3249) | CHG: owner-aware FOREIGN joins |
| 3312-3476 | `compose_and_materialize_session`: `is_warmup=False` (3418, 3464), `sharp_filler_available()` (3422-3437), docstring 3350-3370 | CHG (§ Eligibility) |
| 3484-3509 | `_wire_source` | CHG: `LEGACY_SHARP_FILLER -> "sharp_filler"`, `FOREIGN_BLUNDER -> "foreign_blunder"`, keep the raise |
| 3512-3553 | `RecordedSolve.source` Literal | CHG add `"foreign_blunder"` |
| 3577-3640 | `_classify_herring_solve`: `filler_solution_uci=None` (3623) | CHG drop kwarg |
| 3643-3660 | `_classify_filler_solve` | DEL; replace with a 2-line LEGACY arm (`puzzle_type="sharp"`, no key) for clients holding a pre-deploy session (Pitfall 6) |
| 3663-3732 | `_classify_sr_solve`: `GameFlaw.user_id == solve.user_id` (3673), `GamePosition.user_id == solve.user_id` (3695) | CHG: take a `flaw_owner_id`; FOREIGN resolves it from `games.user_id` |
| 3735-3753 | `_classify_and_certify_solve` dispatch | CHG |
| 3950-4057 | `_mark_session_complete_if_done`: GameFlaw join on `DrillSolve.user_id` (4010); SR-only orphan clauses (4019-4029); filler leniency (4041-4047) | CHG: owner-aware join; SR clauses -> source in (SR, FOREIGN); LEGACY: `DrillSolve.source != LEGACY_SHARP_FILLER` (all legacy rows excluded) |
| 4413 | `record_solve` `is_sr = solve_row.source == DrillSource.SR_ITEM` | KEEP (FOREIGN correctly skips drill_items) |
| 4527-4552 | `RevealedPuzzle`: `source` Literal, `motif` field + docstring 4531 | CHG: add `"foreign_blunder"`; DEL `motif`; ADD `game_info: GameInfoRow | None` |
| 4555-4576 | `_game_move_is_facepalm(user_id=...)`, `GameFlaw.user_id == user_id` (4569) | CHG: param is the flaw owner |
| 4579-4759 | `reveal_for_puzzle`: SR orphan gate 4637; sharp_row 4642-4649; ownership gate 4665-4676; FEN branch 4684-4693; type/tactic/motif branch 4705-4744 | CHG (§ Reveal) |

### Backend: other app files
| Path:line | Site | Action |
|---|---|---|
| `app/schemas/train.py:103-104` | comment "a sharp filler reads "sharp"" | CHG |
| `app/schemas/train.py:137-146` | `SolvedResult.source` Literal + docstring | CHG add `"foreign_blunder"`, KEEP `"sharp_filler"` |
| `app/schemas/train.py:172-188` | `TrainSessionResponse.is_warmup` + docstring | DEL; ADD `own_puzzle_count: int` |
| `app/schemas/train.py:590-632` | `SolveResponse` docstring + `source` Literal | CHG |
| `app/schemas/train.py:677-697` | `PuzzleRevealResponse`: `source` Literal (689), `motif` (695-697) | CHG; DEL `motif`; ADD `game_info: GameInfo | None = None` |
| `app/routers/train.py:11, 95` | docstrings mention filler | CHG |
| `app/routers/train.py:110-154` | `TrainPuzzle(game_id=p.game_id ...)`, `is_warmup=composed.is_warmup` (153) | CHG |
| `app/routers/train.py:313-324` | reveal response mapping incl. `motif=result.motif` | CHG |
| `app/repositories/train_leaderboard_repository.py:82` | verbatim `_NON_FILLER: ColumnElement[bool] = DrillSolve.source != int(DrillSource.SHARP_FILLER)` | CHG -> `DrillSolve.source.in_([int(DrillSource.SR_ITEM), int(DrillSource.RED_HERRING)])` (D-18). Field names `non_filler_*` can stay (still true) |
| `app/repositories/train_leaderboard_repository.py:26-31` | docstring "source != SHARP_FILLER" | CHG |
| `app/services/activity_queries.py:679-691` | `fetch_puzzle_difficulty` docstring (SQL groups by `source`, new row appears automatically) | CHG docstring only |
| `app/services/blunder_check_grading.py:256-263` | `answer_key_for(... filler_solution_uci=None)` | CHG drop kwarg |
| `app/repositories/blunder_check_repository.py:385-386` | docstring "Herring and sharp-filler rows carry no own flaw" | CHG (foreign rows are excluded by `source == SR_ITEM` at `:395` already) |
| `app/services/guest_cleanup_service.py:120` | comment "warm-up filler / red-herring rows" | CHG wording |
| `app/models/train_weekly_standing.py:7` | "non-filler solves" | KEEP (still true) |
| `app/services/train_leaderboard.py:11-12, 198-266, 397-398` | "non-filler" wording | KEEP |
| `app/schemas/openings.py:161`, `app/services/openings_service.py:457` | "warm-up" means rolling-window warm-up | KEEP (false positive) |

### Frontend (non-test)
| Path:line | Site | Action |
|---|---|---|
| `src/types/train.ts:42, 73-75, 88-104, 283, 324-346` | `SolvedResult.source`, `TrainSessionResponse.is_warmup`, `SolveResponse.source`, `PuzzleRevealResponse.source` + `motif` | CHG unions add `'foreign_blunder'` (keep `'sharp_filler'` for cached verdicts / old solved_results); DEL `is_warmup`, ADD `own_puzzle_count`; DEL `motif`; ADD `game_info?: GameInfo | null` |
| `src/types/activity.ts:55-60` | source doc "(0 SR item, 1 red herring, 2 sharp filler)" | CHG |
| `src/lib/trainBotCopy.ts:275-347` | intro: `INTRO_WARMUP_WELCOME_COPY` (302-303), `introSteps(sideToMove, isWarmup)` (325-330), `introCopy` (338-347) | CHG to D-12 (noOwnPuzzles param) |
| `src/lib/trainBotCopy.ts:519-580` | `FILLER_TAIL` (531), `ReturnPhraseInput.is_warmup` + `source` union (536-549), `returnPhrase` (566-580) | CHG to D-11: foreign tail always, herring tail always (warm-up suppression goes), `'sharp_filler'` -> `''` |
| `src/lib/trainBotCopy.ts:755-791, 806, 897-989` | `WARMUP_REMINDER_ASK_COPY`, `WARMUP_SCORE_CLAUSE`, `GUEST_SIGNUP_ASK_SCORE` ("instead of warm-ups"), `ScoreBubbleInput.isWarmup`, warm-up branch of `scoreBubbleCopy` | CHG: reword without "warm-up" (Open Question 2) |
| `src/lib/trainBotCopy.ts:442-446` | `positionFact` soft line "just not your game move" | CHG: foreign soft wording ("just not the game move"), keyed on source |
| `src/components/train/TrainStartScreen.tsx:100-106, 130-200, 267, 388-400` | `'warmup'` kind, `resume.isWarmup`, doc comments, `puzzlesLandingFor` | DEL `'warmup'` kind; ADD D-13 sentence |
| `src/components/train/TrainSolveScreen.tsx:438-439, 506, 545-548, 909-914, 1646-1648, 1733, 1740, 2031` | `isWarmup` plumbing; `analyzeOpens` predicate `verdict?.source !== 'red_herring'` | CHG; `analyzeOpens` must be `'game'` only for `sr_item` (or legacy `undefined`) |
| `src/components/train/TrainReveal.tsx:149, 196, 303-357` | `isWarmup` prop, motif, `fromOwnBlunder` | CHG |
| `src/components/train/TrainVerdictDetails.tsx:53, 88-147` | `isWarmup`, `ReturnTail`, motif extras row (`showExtras`) | CHG (motif row goes) |
| `src/components/train/TrainRevealGameFooter.tsx:38-53` | `sr_item` gate | CHG: FOREIGN renders the neutral footer from reveal `game_info` (D-21) |
| `src/components/train/TrainScoreScreen.tsx:41, 106-119, 139, 197-210` | `isWarmup` prop and comments | CHG |
| `src/components/train/ImportAskActions.tsx:10, 14` | comments ("warm-up score bubble", "sharp fillers always") | CHG |
| `src/components/admin/TrainScoreScreenDemo.tsx:92` | `isWarmup: false` | CHG |
| `src/pages/Train.tsx:110, 182` | `isWarmup={trainSession.session.is_warmup}`, comment | CHG |
| `src/pages/Welcome.tsx:14` | verbatim `'Train switches from warm-up puzzles to the mistakes in your own games.'` | CHG wording |
| `src/App.tsx:159-160, 1004-1008` | comments "serves red herrings and (sharp) filler" | CHG |
| `src/pages/activity/render.js:385-390` | verbatim `{source:0,label:"Own flaw · own"},{source:1,label:"Herring · foreign"}, {source:2,label:"Sharp filler · lichess"}` | CHG: relabel 2 "(retired)", ADD `{source:3,label:"Similar player's blunder"}` (D-19) |
| `src/pages/activity/ActivityPage.tsx:556-564` | card note text | CHG |
| `frontend/scripts/check-activity-layout.mjs:447, 483, 494` | layout fixture labels | CHG |
| `src/components/train/blunder-check/BlunderCheckGameFooter.tsx:41-52` | `ForeignGameFooter` not exported, testid `blunder-check-game-footer` | CHG: export or extract a shared neutral footer |
| `src/lib/trainScoreDemoData.ts:39` | `source: 'sr_item'` | KEEP |

False positives (KEEP): engine/Maia "warm-up" in `EngineReadyGate*`, `maiaWorkerHost.ts`, `ortRuntimeSource.ts`, `useBotGame.test.ts`, `maiaWorkerScript.test.ts`, `public/maia/*`, `scripts/*.mjs`; `analysis/*` and `stories/tilt/*` use "filler" in prose only (no reads of the dropped columns) [VERIFIED: grep for `is_warmup|sharp_puzzle|drill_solves` in `analysis/` and `scripts/` found no consumers].

### Docs
- `docs/activity-dashboard.md:134-137` (source rows wording) CHG.
- `CHANGELOG.md` `## [Unreleased]` user-facing bullet (merge-time).

### Tests (backend) — rewrite / delete map
| File | Sites (function, first line) | Action |
|---|---|---|
| `tests/repositories/test_train_repository.py` | imports 69-70; `_TEST_SHARP_PUZZLES` ~370-382; `_install_sharp_fixture` 385; autouse `_default_empty_sharp_set` 404; `test_zero_sr_material_composes_two_herrings_and_six_sharp` 1029; `test_three_sr_candidates_compose_three_sr_two_herring_three_sharp` 1073; `test_zero_sr_composition_sets_is_warmup` 1125; `test_one_sr_item_is_not_warmup` 1162; `test_is_warmup_survives_resume_after_material_arrives` 1199; `test_empty_composition_reports_is_warmup_false` 1255; `test_no_resume_recomputation_mutation_check` 1269; `test_no_sharp_puzzle_id_collides_within_one_session` 1312; `test_composed_session_rows_each_carry_exactly_one_identity_column` 1377; `test_resume_solved_results_include_source_item_status_due_date` 1790; `test_filler_only_session_stamps_pool_eligible_since` 3663; `test_record_solve_sharp_filler_returns_empty_vetted_moves` 4686; `test_compose_attaches_answer_keys_for_every_source` 5535; `test_server_graded_moves_graded_parity_fresh_and_resumed` 5634; `_reconstructed` 6032; `test_first_session_slot_0_is_the_sharp_filler_when_sr_items_are_all_soft` 6299; comments at 539, 1016 | Delete warm-up tests; rewrite sharp-composition tests as foreign; add legacy-row tests |
| `tests/routers/test_train.py` | imports/comments 13, 108, 147-148; `_install_sharp_fixture` 211; autouse `_default_empty_sharp_set` 229; `_delete_sessions` 415; `_seed_session` 572 (`sharp_puzzle_ids` param, 602-632); `test_session_response_exposes_is_warmup` 937; `test_guest_composes_session_200` 1071; `test_guest_zero_game_warmup_end_to_end` 1097; `test_solve_sharp_filler_touches_no_drill_item` 1892; `test_reveal_sharp_filler_reports_sharp_filler_source` 2473 | Rewrite to foreign + legacy |
| `tests/services/test_train_pool.py` | `answer_key_for(... filler_solution_uci=...)` 244-250, 331-365; `test_sharp_filler` 358; 795-803; `test_sharp_filler_is_empty` 878 | Drop kwarg, delete filler tests, add FOREIGN-takes-SR-branch tests |
| `tests/repositories/test_train_leaderboard_repository.py` | `_seed_session` 88; 116; `test_filler_solves_count_on_points_but_not_in_non_filler_totals` 201 | Extend to FOREIGN + LEGACY (both on points, neither on accuracy) |
| `tests/repositories/test_cross_mode_cooldown.py` | import 37; autouse `_empty_sharp_set` 62 | Replace by the conftest stub |
| `tests/routers/test_train_two_mode_streak.py` | imports 35-37; `_SHARP_PUZZLES` 68-81; autouse `_sharp_fixture` 86 ("a user with no games composes a real warm-up session") | Replace with the foreign test fixture (seeded foreign blunders) |
| `tests/repositories/test_train_medals_finalization.py:113`, `tests/routers/test_train_medals.py:158` | `sharp_puzzle_id=None` kwargs | Drop kwarg |
| `tests/routers/test_train_leaderboard.py:63, 143-144` | `SHARP_FILLER` seeds with `sharp_puzzle_id` | Rename member, drop kwarg |
| `tests/repositories/test_train_progress_modes.py:99-100`, `tests/services/test_train_settings_service.py:497-498`, `tests/test_guest_cleanup_service.py:441, 493-494` | gameless puzzle rows seeded as `SHARP_FILLER` | Rename to `LEGACY_SHARP_FILLER`, drop kwarg; re-check semantics (legacy rows are now unservable and excluded from completion) |
| `tests/test_admin_activity_stats.py:1653-1730` | `test_fetch_puzzle_difficulty_splits_by_source` | Add a source-3 row |
| `tests/services/test_sharp_filler.py`, `tests/scripts/test_gen_sharp_filler_set.py` | whole files | DEL |
| `tests/routers/test_blunder_check_points_migration.py` | loads the current head migration by path | KEEP; new migration's `down_revision = "e5c1b7d3a9f2"` |

False positives (KEEP): `test_engine_nodes.py`, `test_facepalm_material.py`, `test_flaws_service.py`, `test_insights_service_series.py`, `test_tactic_detector.py`, `test_imports_router.py`, `test_openings_time_series.py`, `test_stats_service.py`.

### Tests (frontend) — files that reference filler / warm-up
`TrainReveal.test.tsx` (motif rows 723-758, sharp_filler verdict 954-972), `TrainScoreScreen.test.tsx` (warm-up branches 596-735), `TrainSolveScreen.test.tsx` (warm-up intro 3536, sharp_filler tail 3894-3919), `TrainSolveScreen.restoredGameArrow.test.tsx:107`, `TrainStartScreen.test.tsx` (17 `is_warmup` refs; `'warmup'` describe 565-631, route dot 1039), `TrainVerdictStrip.test.tsx:69`, `trainBotCopy.test.ts` (intro 244-317, returnPhrase 440-496, scoreBubbleCopy 694-996), `useTrainSession.test.ts:78`, `useTrainRevealTree.test.ts`, `Train.solveLoop.test.tsx` (6 refs), `Train.subnav.test.tsx:151, 571`, `Train.blunderCheckToday.test.tsx:98`. Most are `is_warmup: false` fixture fields that break `tsc -b` once the field is removed.

## Foreign Draw Design (question 2)

### Inputs
1. **Level** (once per composition): `user_level_elo(await blunder_check_repository.recent_rated_games(session, user_id=user_id, limit=USER_LEVEL_SCAN_GAMES), fallback=level_fallback_elo(settings_row.blunder_check_level))`. Mirrors `_foreign_source` (`blunder_check_selection.py:582-585`) and `blunder_check_service.py:238`. A guest gets the stored level or 1500.
2. **Raw prefilter range:** `level ± (FOREIGN_RATING_BAND + FOREIGN_RAW_PREFILTER_MARGIN)` = `± 650`, as blunder check does (`blunder_check_selection.py:586-594`).
3. **Served set (D-17):** `select(DrillSolve.game_id, DrillSolve.ply).where(DrillSolve.user_id == user_id, DrillSolve.source == DrillSource.FOREIGN_BLUNDER, DrillSolve.game_id.isnot(None))` into a Python set (the `served_sharp_ids_stmt` shape). Any row counts, solved or not, matching `herring_stmt`'s "served = materialized" rule (`train_pool.py:1338-1347`).
4. **Session exclusions:** `exclude_game_ids = {p.game_id for p in reconstructed if p.game_id is not None}` (SR picks are own games so they never collide; herring picks can be a stranger's game, see Pitfall 2).

### SQL (one statement, SQLAlchemy Core)
Stage 1 CTE over `tablesample(Game.__table__, func.system(FOREIGN_SAMPLE_PERCENT), name="g")` joined to `User`: `g.user_id != solver`, `User.is_guest.is_(False)`, `g.platform.in_(ANALYTICS_INCLUDED_PLATFORMS)`, `owner_rating.between(lo, hi)`, `.order_by(func.random()).limit(FOREIGN_FILLER_CANDIDATE_GAMES)` (new constant, proposed 200). Stage 2 joins `Game` (by id) and `GameFlaw` on `(game_id = games.id AND user_id = games.user_id)`, outer-joins the `_prior_position_lateral` on the flaw's own `user_id`, and applies exactly `pool_entry_stmt`'s six predicates (`train_pool.py:1043-1049`). Select only: `game_id, ply, missed_pv_lines, platform, time_control_bucket, time_control_str, owner_rating`. Optionally move the served check into SQL as `NOT EXISTS (drill_solves ... user_id = :solver AND source = 3 AND game_id = f.game_id AND ply = f.ply)`; the EXPLAIN request includes it so the plan shape is known. The full compiled SQL is in `## Prod EXPLAIN request`.

Indexes the plan should hit [VERIFIED: model/migration reads]: `games` sample scan (no index); `users_pkey`; `games_pkey`; `game_flaws` PK `(user_id, game_id, ply)` (`game_flaw.py:73-82`) or `ix_game_flaws_game_id` (`alembic/versions/20260606_151439_a7e0b4796501_add_game_flaws_table.py:62`) or the partial `ix_game_flaws_facepalm_inputs (user_id, game_id) WHERE severity = 2` (`game_flaw.py:38-51`, applicable because the WHERE has `severity = 2`, but it does not INCLUDE `missed_pv_lines`, so heap fetches remain); `game_positions` PK `(user_id, game_id, ply)` through the LATERAL (the LATERAL exists exactly to force that parameterized lookup, `train_pool.py:958-973`). `drill_solves` has no user index: its indexes are PK `(session_id, position)` (`drill_solve.py:140-144`), `uq_drill_solves_session_puzzle (session_id, game_id, ply)` (`:132`) and partial `ix_drill_solves_solved_at` (`:135-137`). The served-set read is a seq scan; `herring_stmt`'s NOT EXISTS has lived with the same scan since Phase 192.

### Python pick (pure, testable)
```
candidates = [c for c in rows if (c.game_id, c.ply) not in served and c.game_id not in exclude_game_ids]
pinned = pinned_elo_for_mover(raw_rating=c.owner_rating, platform=c.platform,
                              time_control_bucket=c.time_control_bucket,
                              is_correspondence=is_correspondence_time_control(c.time_control_str))
distance = abs(pinned - level); in_band = distance <= FOREIGN_RATING_BAND
rng = random.Random(f"train-foreign:{user_id}:{today.isoformat()}")   # namespaced, like pick_one_per_game
order: in-band first (shuffled), then out-of-band by distance (nearest-first, no cap, 251 UAT rule)
one per game_id; if want_sharp and no pick is sharp yet: take the first sharp candidate first
type = classify_puzzle_type(c.missed_pv_lines, mover_color_for_ply(c.ply))
```
If fewer than `shortfall` survive, run the wide nearest query (`FOREIGN_WIDE_SAMPLE_PERCENT`, `ORDER BY abs(owner_rating - level) LIMIT FOREIGN_NEAREST_POOL_GAMES`, then random 200), as `pick_nearest_foreign_game_ids` does (`blunder_check_repository.py:553-604`). Then load `Game.pgn` for the picks only and reconstruct with `fen_and_last_move_at_ply`; drop failures (over-pick by a small margin, e.g. take `shortfall + 2` and trim).

`want_sharp` (D-16): compute `first_ever = await _is_first_ever_session(...)` once in `_assemble_session_items` before the foreign stage (the existing call in `_order_first_ever_session` can reuse it). With the 38% sharp share and ~50+ in-band candidates per draw, a sharp is almost always available; if none is, the session stays as `_first_session_order` already tolerates (`train_repository.py:2763-2765`). Note: D-16's guarantee can only bind when the session has a foreign shortfall or an own sharp; an all-own all-soft first session is unchanged behaviour [ASSUMED interpretation, confirm].

### Eligibility (question 5, second half)
Replace the `sharp_filler_available()` term (`train_repository.py:3421-3437`) with "a session row was written": after `_materialize_session_rows` returns a non-None `session_id`, call `_stamp_pool_eligibility(..., has_material=True)` (it is stamp-if-NULL and returns early when already set, `:985-997`). Keep the pre-composition call with `has_drill_items or has_pool_candidates or blunder_check_per_session > 0`. Same transaction, same `today`. This is exact (the invariant 206 needed is "a completable session exists => a floor exists") and avoids a random TABLESAMPLE EXISTS. On an empty foreign pool (fresh dev DB, tests) a no-material user simply gets no session (or herrings only), which `TrainEmptyBody` already renders (`TrainStartScreen.tsx:332-381`); STATE.md line 35 already notes the related W-06 ("puzzles on with no material still needs a warm-up session for the streak") as a Phase 251 follow-up.

## Solver-Ownership Assumptions (question 3)

| Site | Current assumption (verbatim) | FOREIGN needs |
|---|---|---|
| `load_session_puzzles` 2156-2168, 2208-2231 | flaw keys `GameFlaw.user_id == user_id, GameFlaw.game_id.in_(sr_game_ids)` | owner flaw existence `(game_id, ply)` with `GameFlaw.user_id == games.user_id`; `game is None` -> drop (D-08); LEGACY -> drop |
| `_composition_puzzle_types` 2813-2841 | blobs only for `source == SR_ITEM`, `GameFlaw.user_id == user_id` | load FOREIGN blobs by owner, else every foreign puzzle classifies "soft" and D-16 reorder never finds the sharp |
| `_position_answer_key` 3172-3176 | `is_sr = source == DrillSource.SR_ITEM` gates blob and best move | treat FOREIGN like SR for blob/best gating; ladder stays herring-only |
| `_answer_keys_by_position` 3238-3253 | `GameFlaw.user_id == DrillSolve.user_id`, `GamePosition.user_id == DrillSolve.user_id` | owner-scoped aliased joins gated on source (Pattern 1) |
| `_classify_sr_solve` 3668-3700 | `GameFlaw.user_id == solve.user_id`, `GamePosition.user_id == solve.user_id` | `flaw_owner_id` from `games.user_id`; `game_id` NULL -> degrade like an SR orphan (soft, no key, recorded) |
| `_mark_session_complete_if_done` 4003-4048 | GameFlaw join on `DrillSolve.user_id`; orphan clauses only for `SR_ITEM` | owner-aware join; both orphan clauses for SR and FOREIGN; LEGACY rows always excluded |
| `reveal_for_puzzle` 4637-4744 | SR orphan -> not_found; "Played in game" only `if game is not None and game.user_id == user_id`; flaw read `GameFlaw.user_id == user_id` | FOREIGN with `game is None` -> not_found (D-09); FOREIGN played SAN from `GamePosition.user_id == game.user_id` (D-20, separate branch, herring gate untouched); type/tactic via owner flaw; FEN `full_fen_at_ply(game.pgn, ply)` |
| `_game_move_is_facepalm` 4565-4575 | `GameFlaw.user_id == user_id` | pass the owner id (the "???" badge reflects the blunder's own facepalm score) [ASSUMED: owner wants ??? on foreign too; drop to False if not] |
| tactic-lines endpoint `app/routers/library.py:438-463` | NOT owner-scoped (see § Tactic line) | nothing |
| `_resume_session` solved rows 2263-2283 | LEFT JOIN `drill_items` on solver | none (no match for FOREIGN, item_status/due_date NULL, correct) |
| `record_solve` 4413 | `is_sr` only advances `drill_items` | none (D-18) |

## Schema and Migration (question 4)

**Current head:** `e5c1b7d3a9f2` [VERIFIED: `uv run alembic heads` output `e5c1b7d3a9f2 (head)`], file `alembic/versions/20261201_120000_e5c1b7d3a9f2_quick_261123_lb8_blunder_check_points_rescale.py`.

**Recommended single revision (`down_revision = "e5c1b7d3a9f2"`), upgrade:**
1. `op.drop_constraint("ck_drill_solves_source", "drill_solves", type_="check")` then `op.create_check_constraint("ck_drill_solves_source", "drill_solves", "source IN (0, 1, 2, 3)")` (the Phase 206 shape, `20260807_114022_e5f71b11fa51_phase_206_sharp_filler_source.py:31-33`). Additive, no row can violate it.
2. `op.drop_column("drill_sessions", "is_warmup")` (one-way, D-04).
3. `op.drop_column("drill_solves", "sharp_puzzle_id")` (discretion; recommended: no reader remains, keeping it is dead weight, the IDs stay in git history; it drops the only identity of source-2 rows, which is fine because nothing re-serves them).
4. Data step, recommended: delete untouched open sessions that hold unsolved source-2 rows so they recompose with foreign fillers (mirrors `_discard_if_untouched_and_resized`, `train_repository.py:2313-2350`; cascade deletes their `drill_solves`):
   `DELETE FROM drill_sessions s WHERE s.status = 'open' AND NOT EXISTS (SELECT 1 FROM drill_solves d WHERE d.session_id = s.id AND d.solved_at IS NOT NULL) AND EXISTS (SELECT 1 FROM drill_solves d WHERE d.session_id = s.id AND d.source = 2 AND d.solved_at IS NULL)`.
   Cost: loses `entered_at` on those rows (the activity funnel reads `MIN(entered_at)`), tiny. Touched sessions keep their rows; the widened completion leniency handles them.

**Downgrade:** re-add `is_warmup BOOLEAN NOT NULL server_default false` and `sharp_puzzle_id TEXT NULL`; `DELETE FROM drill_solves WHERE source = 3` BEFORE narrowing the CHECK to `(0, 1, 2)`. The Phase 206 downgrade bug-fix note (`e5f71b11fa51`, downgrade docstring) is exactly this trap: serial CI's migration round-trips share a DB with router tests that commit rows. Downgrade cannot restore the flags (one-way, documented).

**Naming (discretion), recommended:** `DrillSource.LEGACY_SHARP_FILLER = 2` (wire `"sharp_filler"`, unchanged so cached client verdicts and old `solved_results` still parse) and `DrillSource.FOREIGN_BLUNDER = 3` (wire `"foreign_blunder"`; the codebase already says "foreign" for this in blunder check: `SlotOrigin`, `_foreign_source`, `is_own`).

**Sessions open at deploy** (seed "What needs care"):
- Unsolved source-2 rows: `load_session_puzzles` must `continue` past LEGACY rows; `_mark_session_complete_if_done` excludes every LEGACY row (`DrillSolve.source != LEGACY_SHARP_FILLER`), replacing the `sharp_puzzle_id IS NOT NULL` clause.
- A client that loaded the session before deploy can still POST a solve for a filler position: keep a minimal LEGACY arm in `_classify_and_certify_solve` returning `SolveClassification(puzzle_type="sharp", vetted_moves=[])` (the set was always sharp; no key so `_resolve_grade` path 3 records the client tier). Without it the solve would misclassify as "soft" (blob None) or, if rejected with 404, strand the client on "Couldn't save your result" with Next disabled (`TrainReveal.tsx:275-300`).
- The stuck case: an open session whose only unsolved rows are legacy (user stopped right before a filler) never reaches `_mark_session_complete_if_done` again, because completion only runs inside `record_solve` (`train_repository.py:4473`). The landing still renders "completed" (`nothingLeftToServe`, `TrainStartScreen.tsx:181-187`), but the server session stays open until expiry and the day is not credited. See Open Question 1 and Query E in the EXPLAIN request.

## Client Derivation of "No Own Puzzles" (question 5)

The client cannot derive it today: `TrainPuzzle` deliberately carries no `source` (`app/schemas/train.py:73` "`best_move`, `pv` and `source` remain forbidden here"), SR and foreign puzzles both carry sharp/soft types, and `progress.pool_state` / `waiting_count` cannot see it (`waiting_count` adds the herring pool count, `train_repository.py:1987-1992`, so it is almost never 0; `'no_material'` misses the blob-pending first session).

**Recommendation:** a derived, non-persisted `TrainSessionResponse.own_puzzle_count: int` = number of the session's `drill_solves` rows with `source = SR_ITEM` (all positions, solved or not). Fresh composition: `len(items.surviving_sr_keys)`; resume: one `count().filter(source == SR_ITEM)` over the session's rows (extend the existing `solved_rows_stmt` or a sibling COUNT). Rows never change source, so the value is stable across resume, which was the only reason `is_warmup` was persisted (206 D-07). Client: `noOwnPuzzles = session.own_puzzle_count === 0`.
- D-12 intro: `introSteps(sideToMove, noOwnPuzzles)`.
- D-13 start screen: `noOwnPuzzles && established`, where "established" is best read from `progress.modes.puzzles.first_session_done` (`app/schemas/train.py:823-837`) [ASSUMED definition, confirm].
- Score screen: the warm-up branch needs a non-warm-up rewording keyed on the same signal (Open Question 2).
Caveat to surface: Phase 206 D-04 explicitly rejected a `sr_puzzle_count` field to avoid partial-shortfall notices. A count here is used only as `=== 0`; if the owner prefers, the same derivation can ship as a boolean, but that is `is_warmup` inverted. Flag for the planner.

## Reveal for a Foreign Blunder (questions 6 and 7)

**Old filler reveal returning not_found (question 6).** The reveal query is enabled only once a verdict exists in the current loop (`TrainReveal.tsx:207-212`, `enabled: verdict !== null && sessionId !== null`, `staleTime: Infinity`). A completed session never re-fetches reveals on reload (no puzzles left; the score screen reads `solved_results`). The only ways to hit it: a solve that landed on the old backend with the reveal GET on the new one, or a `trainRevealCache` restore after a full reload. Both render `revealQuery.isError` as "Couldn't load the full reveal details." (`TrainReveal.tsx:396-400`) while the verdict and engine chips stay usable. Graceful. One side effect: the global `QueryCache.onError` reports the 404 to Sentry once (`frontend/src/lib/queryClient.ts:78-84`, `retry: 1` at `:96`); expected to be a handful of events right after deploy.

**Tactic line (question 7).** CONTEXT's premise is wrong in a harmless direction: the tactic-lines endpoint is NOT scoped to the signed-in user. `app/routers/library.py:450-455`: "NOT owner-scoped — any authenticated user may expand the tactic lines of any game they inspect on the analysis page (mirrors get_library_game)"; `library_repository.py:2857-2862` filters only `GameFlaw.game_id == game_id, GameFlaw.ply == ply`. Its payload (`app/schemas/library.py:622-670`) is chess content only (SAN lists, depths, motifs, evals, FEN, ply, severity), nothing identifying. More importantly, the Train frontend does not consume `has_tactic_lines` at all: the only `useTacticLines` callers are `pages/Analysis.tsx:524` and `hooks/analysis/useExplainBar.ts:126` [VERIFIED: grep]. The reveal's steppable lines are the client engine's Move / Best / Game chips, which work from the FEN for any source. So a foreign reveal gets the same steppable lines as an own puzzle with no extra exposure. Compute `has_tactic_lines` for FOREIGN exactly as for SR (pointer only) or set False; either exposes nothing.

**D-20 played move.** New FOREIGN branch in `reveal_for_puzzle`: `played_in_game_san` from `GamePosition(user_id=game.user_id, game_id, ply).move_san`, UCI via the existing parse. The chip label is already neutral ("Game", `trainRevealLines.ts:31-35`); the D-20 wording ("Played in that game") belongs where the reveal names the game move. The soft verdict sentence `positionFact` says "just not your game move" for `fromOwnBlunder` (`trainBotCopy.ts:442-446`); FOREIGN needs its own wording.

**D-21 game footer and wire game_id.** Return `game_info` (time control str/bucket, `played_at`, owner rating) for FOREIGN, built from the already-loaded `game` row (same fields as `blunder_check_repository.game_info_for`, `:1282-1299`), typed with `app/schemas/blunder_check.py:191-197` `GameInfo`. Frontend renders it with the neutral `ForeignGameFooter` line "Game: <TC> · player rated <rating> · <date>" (`BlunderCheckGameFooter.tsx:41-52`).
Recommend also sending `game_id = None` for FOREIGN in both `TrainPuzzle` and `PuzzleRevealResponse`: nothing on the client needs it (the footer gate is `sr_item`, `useTacticLines` is not used in Train), and a stale PWA bundle computes `analyzeOpens` as `puzzle.game_id !== null && verdict?.source !== 'red_herring' ? 'game' : 'position'` (`TrainSolveScreen.tsx:913-914`), which for an unknown source would deep-link the stranger's game (D-21 violation). With `game_id` null, old and new bundles open the position only. Note `get_library_game` is public by id by design (`app/routers/library.py:147-155`), so a game id is not secret, but there is no reason to hand it out.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Servable-blunder predicates | A second copy for the foreign query | `answer_key_present`, `dead_band_admissible`, `second_best_not_winning_admissible`, `expected_score_sql`, `_prior_position_lateral`, `player_only_gate` | Total-operator JSONB rules (`train_pool.py:721-735`), LATERAL planner fix (`:958-973`), parity helper (CLAUDE.md "never hand-roll ply % 2") |
| Solver level | New rating logic | `user_level_elo` + `level_fallback_elo` + `recent_rated_games` | Bot-rating echo guard via `apply_game_filters` (`blunder_check_repository.py:832-851`) |
| Pinned Elo | Raw-rating band | `pinned_elo_for_mover` + `is_correspondence_time_control` | chess.com vs lichess scales differ by hundreds |
| Answer key / graded set / type | Foreign-specific grading | `answer_key_for` / `server_graded_moves_for` SR branch | Composition and solve share one derivation (`train_pool.py:325-339`) |
| Neutral game footer | New component | `ForeignGameFooter` + `GameInfo` | Same 249 D-09 rule |
| Session duplicate guard | Python dedupe only | `uq_drill_solves_session_puzzle` (game_id non-NULL at composition) + exclude herring game ids | DB authority |

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | ~795 solved `drill_solves.source = 2` rows (seed, prod 2026-11-20); unsolved source-2 rows in sessions open at deploy (count unknown, Query E); `drill_sessions.is_warmup` values; `drill_solves.sharp_puzzle_id` values; frozen `train_weekly_standing` snapshots | Solved rows: untouched (D-03). Unsolved: code (skip + completion leniency) plus optional migration delete of untouched sessions. Columns: dropped by migration (one-way). Standings: untouched |
| Live service config | None. No Umami event or dashboard keys on warm-up/filler (grep of `frontend/src/lib/analytics.ts` found none). Admin `/activity` reads only `source` ints | Activity labels in code (D-19) |
| OS-registered state | None (no cron/systemd/pm2 job touches fillers) [VERIFIED: grep of scripts/ and bin/ for sharp_filler found only the generator] | None |
| Secrets / env vars | None | None |
| Build artifacts | PWA bundles in browsers and Cloudflare edge: a stale bundle keeps reading `is_warmup` (undefined -> falsy, harmless) and would deep-link a foreign game in Analyze if `game_id` is sent (see § D-21 wire); `trainRevealCache` localStorage entries may carry `source: 'sharp_filler'` | Keep `'sharp_filler'` in client unions; null wire `game_id` for FOREIGN |

## Common Pitfalls

### Pitfall 1: TABLESAMPLE + LIMIT without ORDER BY favours low block numbers
**What goes wrong:** `TABLESAMPLE SYSTEM` reads sampled blocks in physical order; a `LIMIT` that stops early only ever sees the first sampled blocks, i.e. the oldest inserted games (oldest accounts). Blunder check's band pick (`blunder_check_repository.py:530-550`, no ORDER BY) may already have this bias [ASSUMED from PostgreSQL's `tsm_system` block iteration; Query D in the EXPLAIN request checks it on prod]. Out of scope to fix in blunder check; flag only.
**How to avoid:** `ORDER BY random() LIMIT N` in the stage-1 CTE (reads the whole sample, so its cost is what the EXPLAIN must show). If too slow, lower the sample percent rather than drop the ORDER BY.

### Pitfall 2: A foreign pick colliding with a herring on `uq_drill_solves_session_puzzle`
Herring rows carry the source game's `(game_id, ply)` and the herring pool is drawn from all users' games (`train_pool.py:1271-1275`). A soft foreign blunder can be the same position as a herring. Collision raises `IntegrityError` inside the SAVEPOINT, which the materializer treats as a lost open-session race and re-raises when no open session exists (`train_repository.py:3121-3136`) -> 500. Exclude every game id already in `reconstructed`.

### Pitfall 3: Foreign blobs read through the solver's user id
`_composition_puzzle_types`, `_answer_keys_by_position`, `_classify_sr_solve`, `reveal_for_puzzle` and `_mark_session_complete_if_done` all join `game_flaws` on the solver. Applied to a FOREIGN row they return NULL, which silently becomes "soft, no key" (`classify_puzzle_type` returns "soft" for None, `train_pool.py:310-311`), breaks D-16 ordering, sends no key (client falls back to root-search grading) and lets a deleted foreign game pin a session open. No type error, only tests catch it.
**Warning sign:** a foreign puzzle in a test session with `puzzle_type == "soft"` and `key_move_uci is None` despite a sharp blob.

### Pitfall 4: Global draw leaks across tests
Router tests commit rated non-guest games with flaws (e.g. `tests/blunder_check_seed.py:211-253` seeds `white_rating=1500, black_rating=1500`), and the solver's fallback level is 1500. Any composition test in the same xdist worker DB could draw them. **Avoid:** an autouse fixture in `tests/conftest.py` that stubs the foreign draw seam to return no rows, and an opt-in fixture that restores it, sets the sample percents to 100 (blunder check tests do `monkeypatch.setattr(blunder_check_selection, "FOREIGN_SAMPLE_PERCENT", 100.0)`, e.g. `tests/services/test_blunder_check_selection.py:229`) and seeds its own foreign games with finally-cleanup.

### Pitfall 5: The last unsolved puzzle orphaned leaves the session open
Completion is computed only in `record_solve`. If the only unsolved rows are unservable (legacy filler at deploy, a foreign game deleted while the puzzle was not loaded), nothing re-runs `_mark_session_complete_if_done`. The SR orphan path already has this gap. See Open Question 1.

### Pitfall 6: In-flight clients holding a filler puzzle
A browser that composed before deploy still shows a filler and POSTs a solve. Keep the LEGACY classification arm (sharp, no key) and the `"sharp_filler"` wire value; otherwise the solve misgrades or 404s into a stuck Retry state.

### Pitfall 7: `_wire_source` raising on legacy rows
`_resume_session` serializes every solved row of the current window session (`train_repository.py:2284-2295`). If value 2 loses its arm, `_wire_source` raises `ValueError` (`:3509`) and the Today mount 500s for anyone who solved a filler in the current window.

### Pitfall 8: Downgrade with committed source-3 rows
Same trap the Phase 206 downgrade fixed: delete `source = 3` rows before narrowing the CHECK.

### Pitfall 9: ROADMAP vs CONTEXT on the per-puzzle tail
ROADMAP says the "similarly rated player" label "must not repeat on every puzzle of an all-foreign session"; CONTEXT D-11 (later, locked) says it shows on every foreign puzzle including all-foreign sessions. Follow D-11. With warm-up gone, herrings in an all-non-own session also start showing `HERRING_TAIL` (today suppressed by `is_warmup`, `trainBotCopy.ts:567-568`). That follows from D-04 and D-11, but tests asserting "no tail in a warm-up session" (`trainBotCopy.test.ts:444-470`) flip.

## Code Examples

### Foreign stage at the existing filler point
```python
# Source: train_repository._assemble_session_items (2977-2989), adapted
shortfall = n - len(reconstructed)
if shortfall > 0:
    reconstructed.extend(
        await _backfill_foreign_blunders(
            session,
            user_id=user_id,
            settings_row=settings_row,     # needs blunder_check_level for the fallback level
            today=today,
            shortfall=shortfall,
            exclude_game_ids={p.game_id for p in reconstructed if p.game_id is not None},
            want_sharp=first_ever,
        )
    )
```
`_assemble_session_items` does not receive `settings_row` today (signature `:2889-2891`); thread it in or pass `blunder_check_level` only.

### Completion leniency for legacy rows
```python
# Source: train_repository._mark_session_complete_if_done (4041-4047), replaced
# Bug fix (Phase 263): the lichess filler set is gone, so no source-2 row can be served any
# more. Every unsolved one is excluded, not only those with a NULL sharp_puzzle_id.
DrillSolve.source != DrillSource.LEGACY_SHARP_FILLER,
```

### Leaderboard exclusion
```python
# Source: train_leaderboard_repository.py:82, replaced (D-18: own puzzles and herrings only)
_ACCURACY_SOURCES: ColumnElement[bool] = DrillSolve.source.in_(
    [int(DrillSource.SR_ITEM), int(DrillSource.RED_HERRING)]
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Static 208 lichess puzzles (1004-1399) for every shortfall | Rating-matched foreign blunders on the normal grading path | This phase | First session reflects the product; no motif row |
| Persisted `is_warmup` label | Derived `own_puzzle_count`, no "warm-up" wording | This phase | One less frozen column |

**Deprecated:** `motif` on the reveal (filler-only), `filler_solution_uci` parameter, `sharp_filler_available()`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | PostgreSQL `TABLESAMPLE SYSTEM` returns sampled blocks in physical order, so an early LIMIT biases to old rows | Pitfall 1 | Low for Train (ORDER BY random() recommended anyway); informs a blunder-check follow-up |
| A2 | Stage-1 `ORDER BY random()` over a 2% sample is affordable inside a request | Foreign draw | Composition latency / connection hold time; Query A decides |
| A3 | Including `platform IN ('chess.com','lichess')` as a source filter (like guests) does not violate D-06 "no extra predicates" | Foreign draw | Planner/owner may want it dropped; bot/PGN games mostly fail the rating band anyway |
| A4 | "Established user" for D-13 = `modes.puzzles.first_session_done` | Client derivation | Wrong copy on a new user's exhausted day |
| A5 | D-16 binds only when the session has a foreign shortfall (all-own all-soft first sessions stay as today) | Foreign draw | Owner may expect a sharp foreign pick to be forced into every first session |
| A6 | The "???" facepalm badge should show on a foreign game move | Solver-ownership | Cosmetic; switch to False if unwanted |
| A7 | `own_puzzle_count` (a count) is acceptable despite 206 D-04 rejecting `sr_puzzle_count` | Client derivation | Owner may prefer a boolean |
| A8 | Candidate batch of 200 games yields enough in-band blunders (~1 servable per blob-complete game per the seed, ~30% in pinned band) | Foreign draw | Short sessions at band edges; nearest-first covers |

## Open Questions (RESOLVED)

1. **Lazy completion for a session whose remaining rows are all unservable.** RESOLVED: 263-09 Task 1 (lazy completion in `_resume_session`), with the completion leniency in 263-08 Task 1 and the untouched-session delete in migration c4e6a8b0d375 (263-09 Task 3); orchestrator ruling 3.
   - Known: completion runs only in `record_solve`; the landing shows "completed" anyway; the server session stays open and the day is not credited (pre-existing for SR orphans, new exposure for legacy rows at deploy and deleted foreign games).
   - Recommendation: in `_resolve_existing_session`, for an open session with zero servable puzzles and >0 solves, call `_mark_session_complete_if_done` and, if it flips, `apply_day_completion` (same pair `record_solve` uses, `:4473-4498`). One COUNT per resume. Planner decides scope; Query E sizes the deploy-time case.
2. **Score-screen copy for a session with no own puzzles.** RESOLVED: proposed wording in 263-02 Task 1, owner review item in `263-HUMAN-UAT.md` (263-10 Task 2); orchestrator ruling 5. D-11..D-13 do not cover it, D-04 bans "warm-up". The branch also carries `PRACTICE_RATIONALE` and the zero-game/guest variants (`trainBotCopy.ts:963-989`). Recommendation: keep the branch keyed on `own_puzzle_count === 0`, reword in the D-12 voice ("These came from players at your level. Once your games are analyzed, your own mistakes take over."), reword `GUEST_SIGNUP_ASK_SCORE` and `Welcome.tsx:14`. Needs owner sign-off on wording.
3. **Cross-mode repeat.** RESOLVED: out of scope, recorded in 263-10 § Deferred; orchestrator ruling 6. A foreign blunder served in Train can later appear in a blunder-check foreign window for the same user (blunder check's served set is `blunder_check_windows` only). Not covered by D-17. Recommendation: out of scope, note it.
4. **Index on `drill_solves (user_id, source)`.** RESOLVED: not needed; the served set is one 5.7 ms read done in Python (263-01 `_served_foreign_positions`), per § Prod EXPLAIN results item 4 and ruling 1. Not needed if Query C shows a small seq scan; STATE.md already tracks the "revisit near 300k rows" note (Phase 246 WR-01).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python / uv | backend, tests | yes | uv 0.10.9 (venv created in worktree this session) | — |
| PostgreSQL dev DB (Docker) | pytest | container `flawchess-dev-db-1` running on host | 18 (per CLAUDE.md) | — |
| DB config in worktree | pytest / scripts | **no** (memory: "Worktree has no DB config") | — | run DB-backed tests with the main checkout's env, or copy env into the worktree session per project practice (do not touch `.env` files via the agent) |
| Node / npm | frontend | yes | v24.19.0 / 11.17.0 | — |
| `frontend/node_modules` in worktree | vitest, build, knip | **no** | — | `npm ci` in `frontend/` (memory: per-worktree install) |
| uv group `maia-inference` | `ty` on fresh worktree | unknown | — | `uv sync --group maia-inference` (memory: else 3 phantom ty errors) |
| Prod DB access | EXPLAIN | not from this agent | — | orchestrator runs `## Prod EXPLAIN request` |

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest (+ pytest-asyncio, xdist) backend; vitest 5 frontend |
| Config | `pyproject.toml` / `tests/conftest.py` (template DB per xdist worker); `frontend/package.json` `"test": "vitest run"` |
| Quick run | `uv run pytest tests/repositories/test_train_repository.py -x -k foreign` |
| Full suite | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |

### Phase Requirements -> Test Map
| Req | Behavior | Type | Command | Exists? |
|---|---|---|---|---|
| D-01 | never guest, never solver's games | repo integration | `pytest tests/repositories/test_train_foreign.py::test_draw_excludes_guest_and_own_games` | Wave 0 |
| D-02 | foreign only on shortfall, herrings unchanged | repo integration | `...::test_full_own_session_draws_no_foreign` / `::test_shortfall_filled_by_foreign` | Wave 0 |
| D-03 | legacy rows kept, skipped, never pin open, still serialize | repo integration | `...::test_legacy_filler_rows_skipped_and_excluded_from_completion`, `::test_resume_serializes_legacy_source` | Wave 0 |
| D-04 | no is_warmup anywhere | schema/router + grep gate | `pytest tests/routers/test_train.py -k own_puzzle_count`; `git grep -n -i "is_warmup\|isWarmup\|warm-up" -- app frontend/src` returns only false positives | rewrite |
| D-05 | level from user_level_elo with fallback | unit | `...::test_level_uses_stored_level_without_rated_games` | Wave 0 |
| D-06 | same predicates as own pool | repo integration | `...::test_foreign_candidate_rejects_each_pool_predicate` (parametrize: severity, opponent ply, empty blob, dead band, second-best winning, winnability) | Wave 0 |
| D-07/D-08 | live join; deleted game / vanished flaw dropped | repo integration | `...::test_deleted_foreign_game_dropped_and_session_completes` | Wave 0 |
| D-09 | solved outcome kept; reveal not_found | router | `tests/routers/test_train.py::test_reveal_foreign_deleted_game_404` | Wave 0 |
| D-10/D-21 | wire game_id None; neutral game_info only | router | `::test_foreign_puzzle_wire_has_no_game_id`, `::test_reveal_foreign_game_info_has_no_names` | Wave 0 |
| D-11 | tail on every foreign puzzle | vitest | `npm test -- trainBotCopy` (returnPhrase truth table) | rewrite |
| D-12/D-13 | intro and start copy from own_puzzle_count | vitest | `npm test -- TrainStartScreen TrainSolveScreen` | rewrite |
| D-14/D-15/D-17 | random, rating only, one per game, no repeat | unit (pure `_pick_foreign`) | `pytest tests/repositories/test_train_foreign.py -k pick` | Wave 0 |
| D-16 | first-ever session gets a sharp at slot 0 | repo integration | `...::test_first_ever_all_foreign_session_opens_on_sharp` | rewrite of 6299 |
| D-18 | points yes, accuracy no | repo | `pytest tests/repositories/test_train_leaderboard_repository.py -k filler` | rewrite |
| D-19 | Activity row per source | repo + layout script | `pytest tests/test_admin_activity_stats.py -k difficulty`; `node frontend/scripts/check-activity-layout.mjs` | rewrite |
| D-20 | reveal shows the owner's game move | router | `::test_reveal_foreign_reports_owner_game_move` | Wave 0 |
| Migration | upgrade/downgrade round-trip with source-3 rows | migration | new `tests/test_phase_263_migration.py` (pattern of `tests/routers/test_blunder_check_points_migration.py`) | Wave 0 |
| Grading | foreign solve grades on SR path with owner key; legacy solve records | repo | `::test_record_solve_foreign_uses_owner_key`, `::test_record_solve_legacy_filler_records_client_tier` | Wave 0 |

### Sampling Rate
- Per task commit: the touched test file(s) only (serial, single file).
- Per wave merge: `uv run pytest -n auto -x` + frontend `npm test -- --run`.
- Phase gate: full pre-merge gate (CLAUDE.md) plus one serial run of the migration and Train router files (`uv run pytest tests/routers/test_train.py tests/test_phase_263_migration.py`) because serial CI hides isolation bugs (memory).

### Wave 0 Gaps
- [ ] `tests/conftest.py` autouse stub of the foreign draw seam (replaces four per-file sharp fixtures) + opt-in `foreign_pool` fixture (seeds a second non-guest rated user with N qualifying blunders, sample percents patched to 100, finally-cleanup).
- [ ] `tests/repositories/test_train_foreign.py` (draw, pick, ownership joins, legacy handling).
- [ ] `tests/test_phase_263_migration.py`.
- [ ] A seed helper for a foreign qualifying blunder: `_seed_flaw_game` (`tests/repositories/test_train_repository.py:138-216`) sets no `white_rating`/`black_rating`; the foreign helper must set the owner's rating and `full_evals_completed_at` is irrelevant (pool predicates do not read it).

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no (unchanged) | FastAPI-Users |
| V3 Session Management | no | — |
| V4 Access Control | yes | Every read keeps `DrillSolve.user_id == user_id` in the WHERE (IDOR); foreign `(game_id, ply)` is written by composition only, never client-supplied |
| V5 Input Validation | yes (unchanged inputs) | Pydantic `Literal` wire types; add `"foreign_blunder"` |
| V6 Cryptography | no | — |
| V8 Data Protection | yes | D-21: no usernames, user ids, or links of the foreign owner; recommend `game_id=None` on the wire; `game_info` carries only TC, date, owner rating |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---|---|---|
| Owner identity leak via reveal / footer / Analyze link | Information disclosure | Neutral `game_info`; no library-card fetch for FOREIGN; wire `game_id` None |
| Stale PWA bundle deep-linking a stranger's game | Information disclosure | Wire `game_id` None for FOREIGN |
| Owner-scoped join widened to "any user" on SR rows | Tampering / disclosure | Keep SR joins solver-scoped; separate source-gated FOREIGN joins |
| Request holding a scarce prod connection (max 50) during the draw | DoS | Prod EXPLAIN; bounded LIMITs; second (wide) query only on thin tails |

## Prod EXPLAIN request

Run with `EXPLAIN (ANALYZE, BUFFERS)` on prod (read-only). Placeholders: solver user id `28`, solver level `1500` (raw prefilter `1500 ± 650` = `850..2150`); Query B uses level `2600` to exercise a thin tail. `drill_solves.source = 1` is a stand-in for the future `3` so the anti-join has real rows to plan against. Run each twice (cold/warm).

**Query A — main band draw (stage 1 CTE + stage 2 pool predicates + served NOT EXISTS):**
```sql
WITH cand AS 
(SELECT g.id AS game_id 
FROM games AS g TABLESAMPLE system(2.0) JOIN users ON users.id = g.user_id 
WHERE g.user_id != 28 AND users.is_guest IS false AND g.platform IN ('chess.com', 'lichess') AND CASE WHEN (g.user_color = 'white') THEN g.white_rating ELSE g.black_rating END BETWEEN 850 AND 2150 ORDER BY random() 
 LIMIT 200)
 SELECT game_flaws.game_id, game_flaws.ply, game_flaws.missed_pv_lines, games.platform, games.time_control_bucket, games.time_control_str, CASE WHEN (games.user_color = 'white') THEN games.white_rating ELSE games.black_rating END AS owner_rating 
FROM cand JOIN games ON games.id = cand.game_id JOIN game_flaws ON game_flaws.game_id = games.id AND game_flaws.user_id = games.user_id LEFT OUTER JOIN LATERAL (SELECT game_positions.eval_cp AS eval_cp, game_positions.eval_mate AS eval_mate 
FROM game_positions 
WHERE game_positions.user_id = game_flaws.user_id AND game_positions.game_id = game_flaws.game_id AND game_positions.ply = game_flaws.ply - 1 
 LIMIT 1) AS prior ON true 
WHERE game_flaws.severity = 2 AND NOT CASE WHEN (game_flaws.ply % 2 = 0) THEN games.user_color = 'black' ELSE games.user_color = 'white' END AND game_flaws.missed_pv_lines IS NOT NULL AND jsonb_typeof(game_flaws.missed_pv_lines) = 'array' AND game_flaws.missed_pv_lines != CAST('[]' AS JSONB) AND jsonb_typeof(game_flaws.missed_pv_lines[0]) = 'object' AND ((game_flaws.missed_pv_lines[0]) ->> 'su') IS NOT NULL AND ((game_flaws.missed_pv_lines[0]) ->> 'su') != '' AND CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'bm') AS INTEGER) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'bm') AS INTEGER) > 0) THEN 1000.0 ELSE -1000.0 END)) AS FLOAT) WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'b') AS FLOAT) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 'b') AS FLOAT))) AS FLOAT) ELSE NULL END IS NOT NULL AND CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) > 0) THEN 1000.0 ELSE -1000.0 END)) AS FLOAT) WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT))) AS FLOAT) ELSE NULL END IS NOT NULL AND (CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'bm') AS INTEGER) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'bm') AS INTEGER) > 0) THEN 1000.0 ELSE -1000.0 END)) AS FLOAT) WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'b') AS FLOAT) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 'b') AS FLOAT))) AS FLOAT) ELSE NULL END - CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) > 0) THEN 1000.0 ELSE -1000.0 END)) AS FLOAT) WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT))) AS FLOAT) ELSE NULL END >= 0.15 OR CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'bm') AS INTEGER) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'bm') AS INTEGER) > 0) THEN 1000.0 ELSE -1000.0 END)) AS FLOAT) WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'b') AS FLOAT) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 'b') AS FLOAT))) AS FLOAT) ELSE NULL END - CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CASE WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) > 0) THEN 1000.0 ELSE -1000.0 END)) AS FLOAT) WHEN (CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT) IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT))) AS FLOAT) ELSE NULL END < 0.05) AND (((game_flaws.missed_pv_lines[0]) ->> 'su') = '' OR CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) IS NOT NULL AND CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1 ELSE -1 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) < 0 OR CAST(((game_flaws.missed_pv_lines[0]) ->> 'sm') AS INTEGER) IS NULL AND (CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT) IS NULL OR CASE WHEN (CASE WHEN (game_flaws.ply % 2 = 0) THEN 'white' ELSE 'black' END = 'white') THEN 1.0 ELSE -1.0 END * CAST(((game_flaws.missed_pv_lines[0]) ->> 's') AS FLOAT) < 200)) AND CASE WHEN (prior.eval_mate IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (games.user_color = 'white') THEN 1.0 ELSE -1.0 END * CASE WHEN (prior.eval_mate > 0) THEN 1000.0 ELSE -1000.0 END)) AS FLOAT) WHEN (prior.eval_cp IS NOT NULL) THEN 1.0 / CAST((1.0 + exp(-0.00368208 * CASE WHEN (games.user_color = 'white') THEN 1.0 ELSE -1.0 END * prior.eval_cp)) AS FLOAT) ELSE NULL END >= 0.2 AND NOT (EXISTS (SELECT * 
FROM drill_solves 
WHERE drill_solves.user_id = 28 AND drill_solves.source = 1 AND drill_solves.game_id = game_flaws.game_id AND drill_solves.ply = game_flaws.ply));
```
(SQL compiled from the app's own predicate builders with `literal_binds`, `%%` unescaped to `%`.) Also report the row count returned (yield per 200 games). Variant A2: add `AND g.blobs_completed_at IS NOT NULL` to the CTE WHERE and compare yield and time (a yield heuristic only; it is an extra predicate, so D-06 argues against it unless yield is poor).

**Query B — thin-tail nearest fallback (20% sample, level 2600):** replace the `WITH cand AS (...)` block of Query A with the block below; everything from ` SELECT game_flaws.game_id` onward is identical to Query A.
```sql
WITH cand AS 
(SELECT nearest.game_id AS game_id 
FROM (SELECT g.id AS game_id 
FROM games AS g TABLESAMPLE system(20.0) JOIN users ON users.id = g.user_id 
WHERE g.user_id != 28 AND users.is_guest IS false AND g.platform IN ('chess.com', 'lichess') AND CASE WHEN (g.user_color = 'white') THEN g.white_rating ELSE g.black_rating END IS NOT NULL ORDER BY abs(CASE WHEN (g.user_color = 'white') THEN g.white_rating ELSE g.black_rating END - 2600) 
 LIMIT 400) AS nearest ORDER BY random() 
 LIMIT 200)
```

**Query C — served-set read and table sizes:**
```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT game_id, ply FROM drill_solves WHERE user_id = 28 AND source = 1 AND game_id IS NOT NULL;
SELECT relname, reltuples::bigint, relpages, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class WHERE relname IN ('games', 'game_flaws', 'drill_solves', 'drill_sessions', 'users');
```

**Query D — TABLESAMPLE early-LIMIT bias probe (A1), run 3 times:**
```sql
SELECT min(s.id), max(s.id), count(*) FROM (
  SELECT g.id FROM games AS g TABLESAMPLE system(2.0) JOIN users ON users.id = g.user_id
  WHERE g.user_id != 28 AND users.is_guest IS false AND g.full_evals_completed_at IS NOT NULL
    AND g.platform IN ('chess.com', 'lichess')
    AND CASE WHEN (g.user_color = 'white') THEN g.white_rating ELSE g.black_rating END BETWEEN 850 AND 2150
  LIMIT 40) AS s;
SELECT min(id), max(id) FROM games;
```
If the sampled `max(id)` sits far below the table's `max(id)` on every run, the bias is real.

**Query E — sessions open now that hold unsolved source-2 rows (deploy-time exposure):**
```sql
SELECT count(*) AS open_sessions_with_unsolved_fillers,
       count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM drill_solves d2 WHERE d2.session_id = s.id AND d2.solved_at IS NOT NULL)) AS untouched,
       count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM drill_solves d3 WHERE d3.session_id = s.id AND d3.solved_at IS NULL AND d3.source <> 2)) AS only_fillers_left
FROM drill_sessions s
WHERE s.status = 'open'
  AND EXISTS (SELECT 1 FROM drill_solves d WHERE d.session_id = s.id AND d.source = 2 AND d.solved_at IS NULL);
```

## Sources

### Primary (HIGH confidence, read this session)
- `app/repositories/train_repository.py` (composition, serving, grading, completion, reveal; lines cited throughout)
- `app/services/train_pool.py` (predicates, answer key, graded set, herring stmt, pick_one_per_game)
- `app/services/blunder_check_selection.py`, `app/services/blunder_check_rules.py:164`, `app/repositories/blunder_check_repository.py` (level, sampling, foreign picks, game_info_for)
- `app/models/drill_solve.py`, `app/models/drill_session.py`, `app/models/game_flaw.py`, `app/models/game.py`
- `alembic/versions/20260807_114022_e5f71b11fa51_phase_206_sharp_filler_source.py`; `uv run alembic heads`
- `app/schemas/train.py`, `app/schemas/blunder_check.py`, `app/schemas/library.py`, `app/routers/train.py`, `app/routers/library.py`, `app/repositories/library_repository.py`
- `app/repositories/train_leaderboard_repository.py`, `app/services/activity_queries.py`
- Frontend: `trainBotCopy.ts`, `TrainStartScreen.tsx`, `TrainReveal.tsx`, `TrainRevealGameFooter.tsx`, `TrainSolveScreen.tsx`, `TrainVerdictDetails.tsx`, `TrainScoreScreen.tsx`, `BlunderCheckGameFooter.tsx`, `types/train.ts`, `pages/activity/render.js`, `lib/queryClient.ts`, `hooks/useLibrary.ts`
- Tests: `tests/conftest.py`, `tests/repositories/test_train_repository.py`, `tests/routers/test_train.py`, `tests/routers/test_train_two_mode_streak.py`, `tests/repositories/test_cross_mode_cooldown.py`, `tests/blunder_check_seed.py`
- `.planning/phases/263-foreign-blunder-fillers/263-CONTEXT.md`, seed SEED-261120-jnw, ROADMAP § Phase 263, 206/249/250 CONTEXT, STATE.md (selective)

### Tertiary (LOW)
- PostgreSQL TABLESAMPLE SYSTEM block order (training knowledge, A1; Query D verifies)

## Metadata

**Confidence breakdown:**
- Touchpoint inventory: HIGH — every site opened; grep sweeps for all filler/warm-up tokens.
- Architecture / ownership joins: HIGH — derived from the code paths read.
- Draw cost on prod: MEDIUM pending Query A/B/C.
- Copy decisions: LOW by nature (owner wording; Open Question 2).

**Research date:** 2026-11-23
**Valid until:** 2026-12-23 (stable code; re-check line numbers if `train_repository.py` changes before planning)

## Prod EXPLAIN results

Run by the orchestrator on prod, 2026-11-23, through the read-only MCP. These are measurements, not
assumptions, and they override the cost guesses above where they differ.

**Table sizes:** `games` 1.12M rows / 346k pages (4.4 GB), `game_flaws` 7.87M rows (16 GB),
`drill_solves` 24k rows (14 MB), `drill_sessions` 2.7k rows, `users` 1.5k rows (713 non-guest).

| Query | Result |
|---|---|
| A, main band draw, `TABLESAMPLE system(2.0)`, cold | **2433 ms**, 223 servable blunders from 200 games. 1826 ms is the sample scan alone: 6857 page reads to produce 15.4k band-matching games, of which 200 are kept. |
| A's CTE alone at `system(0.1)` | **91 ms**, 344 page reads, 800 band-matching games, 200 kept. |
| A, stage two (200 games to servable blunders) | about 400 ms cold: `games` by id 60 ms, `game_flaws` via `ix_game_flaws_facepalm_inputs` 220 ms, prior `game_positions` by pkey 117 ms. |
| A, `NOT EXISTS` on `drill_solves` | 146 ms and 23,167 buffer hits for 223 probes (about 104 per probe): `uq_drill_solves_session_puzzle` leads with `session_id`, so each probe skip-scans. |
| B, thin-tail nearest fallback, `system(20.0)`, CTE alone, cold | **14,863 ms**, 68k page reads. Not usable inside a request. |
| C, served-set read for one user | 5.7 ms, seq scan of all 1520 pages, 265 rows. |
| D, early LIMIT under TABLESAMPLE | sampled ids 623026 to 3266092 against a table range of 468849 to 3341250. No sign of an old-games bias. The three runs collapsed into one evaluation, so this is a single sample. |
| E, open sessions holding unsolved filler rows | 153 sessions; 122 untouched (no solve yet); 14 with only fillers left unsolved. |

**What this means for the plan:**
1. **Sample percent is the cost.** 2% reads about 6.9k pages to keep 200 games. At 0.1% the band (±650
   raw) still yields 800 candidates, four times what is needed. Use a small sample percent as a named
   constant, sized so the expected candidate count is a small multiple of the games needed, not blunder
   check's value by default.
2. **A filler shortfall needs few puzzles.** 200 games yield about 223 servable blunders before the
   pinned-Elo band; a session needs at most a session's worth. The game LIMIT can be far below 200,
   which also cuts stage two.
3. **The 20% nearest-first fallback cannot ship as written.** It needs another shape for the thin
   tail (2400+): for example escalating the sample percent in steps only on an empty result, or
   widening the raw band on the small sample, with a hard cap and a short session as the accepted
   outcome on an empty pool. The planner must pick one and give it a latency budget.
4. **Do the D-17 exclusion in Python** from the Query C read (5.7 ms), not as a correlated
   `NOT EXISTS`. No new index on `drill_solves` is needed at this table size (open question 4: closed).
5. **Deploy-time exposure is real but small** (open question 1): 122 untouched open sessions can be
   deleted and recomposed; 31 touched ones need the leniency in `_mark_session_complete_if_done`,
   14 of which have only fillers left and would otherwise never complete.
6. Cold numbers are the honest ones for this path: each draw samples different pages, so the cache
   does not warm it the way a repeated query would.
