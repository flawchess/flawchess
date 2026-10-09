# Phase 235: Train Grading Anchored to the Server Answer Key (SEED-192) - Research

**Researched:** 2026-10-07
**Domain:** Train grading pipeline (FastAPI/SQLAlchemy backend + React/Stockfish-WASM client), one Alembic column
**Confidence:** HIGH (all claims are from code read this session; one engine measurement run headless this session)

## Summary

This is an internal-plumbing phase: no new libraries, no new services. Every source already has a
server-side "key" reachable with data the repository already owns, but **none of it is loaded at
`TrainPuzzle` construction today**: composition keeps only `(game_id, ply, Game)` for SR items, the
resume path joins `herring_pool` without undeferring `ladder`, and `game_positions.best_move` is read
only at solve time inside `_classify_and_certify_solve`. The cleanest delivery is ONE session-scoped
key query run at the end of `compose_and_materialize_session` (covers the fresh, resume and
IntegrityError-resume paths), feeding a pure per-row derivation function in `train_pool.py` that the
solve path reuses, so composition-time and solve-time keys can never be derived two different ways.

On the client, the change is smaller than it looks if the anchor is generalized rather than forked:
`startGrading(fen, keyUci)` stores an "anchor" (key UCI, key line rooted at the puzzle FEN, anchor ES).
With a key, the anchor comes from an after-key search (D-08); with `null` (D-07), it comes from
today's root search. `gradeMoveInner` then has ONE comparison (`anchor.es` vs after-played ES), and
`GradeResult.bestMoveUci` / `bestLine` / `esBefore` keep their names and meanings for every downstream
consumer (arrows, line boxes, free-play seed, board badge), which therefore start naming the server key
with no further edits. The D-10 re-check is best as a separate imperative `recheckMove` with its own
timeout and node cap, triggered by a pure `shouldRecheck` helper.

A headless SF18 lite WASM probe run this session on the user-28 FEN shows two load-bearing facts: (1)
the current `TRAIN_GRADING_MAX_NODES = 2000000` cap **binds before 3s** (b3 after-move: 2,000,425 nodes
at 2,699 ms), so a 3 s re-check needs a raised node cap or it is not deeper; (2) the sharp runner-up
`su` (d1d5) reads **better than the key** at 1.5 s, so without `su` on the client, playing `su` on a
sharp puzzle would trigger a pointless 6 s re-check that D-02 overrides anyway. The client therefore
needs the runner-up UCI pre-attempt (Open Question 1).

**Primary recommendation:** Add `key_move_uci`, `puzzle_type` and `runner_up_uci` to `TrainPuzzle`
via one post-composition key query + a shared pure `answer_key_for(...)`; generalize the client's mount
search into an "anchor" search; add `recheckMove` (3 s, raised node cap, own timeout); extend the
server override into a `ServerGradedMove` list (vetted + sharp `su`); add a pure `_resolve_grade(...)`
helper for D-14; store the validated re-check in a new `drill_solves.recheck` JSONB omitted when absent.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Derive the key / puzzle type / runner-up per puzzle | API / Backend (`train_pool.py` pure fn + `train_repository.py` query) | Database (game_flaws blob, game_positions.best_move, herring_pool.ladder) | Server owns the answer key (D-06); one derivation shared by compose and solve |
| Deliver key pre-attempt | API / Backend (`TrainPuzzle`) | — | D-05 contract change |
| After-key / after-played searches, re-check | Browser / Client (Stockfish WASM worker) | — | D-01: client engine on both sides, never server evals in one drop |
| Re-check trigger decision | Browser / Client (pure `shouldRecheck`) | — | Must run pre-POST (D-10) |
| Sharp `su` grading (D-02) | API / Backend (`record_solve` override) | — | No client search decides it |
| D-14 guess credit | API / Backend (`_resolve_grade`) | — | `correct_guess` stays server-computed after sanity checks |
| Re-check record (D-17/D-18) | Database (`drill_solves.recheck`) | API (Pydantic validation) | Feeds grading, so separate from telemetry |
| Copy D-12/D-15, unclamped numbers D-16 | Browser / Client | API (`SolveResponse` disagreement flag) | Display follows the server-accepted verdict |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked upstream (ROADMAP Phase 235 + SEED-192, owner 2026-10-07; do not re-open)
- **D-01:** Grade against the server key with the client engine on both sides: played == key ->
  GOOD with no search; otherwise compare the client's after-move search of the played move with its
  after-move search of the key, same budget. Replaces the mixed-horizon root (`esBefore`) vs
  after-move (`esAfter`) drop in `gradeMoveInner`. Never mix server and client evals in one drop.
  Applies to all sources (soft and herring included), not only sharp.
- **D-02:** Server-graded runner-up: on a sharp SR item, played == `su` is graded server-side from
  the blob's `b`/`s` evals (extend `_override_for_key_move`, empty on sharp puzzles today). No client
  search decides it.
- **D-03:** Raising the client movetime globally is rejected (Qh4/b3 swap between depth 19 and 22,
  device- and hash-dependent per SEED-130).
- **D-04:** No sharp-classification hardening or extra server search budget in this phase; a high
  confirmed-disagreement rate becomes a follow-up seed.

#### Key delivery (supersedes P-01 / POOL-10)
- **D-05:** `TrainPuzzle` (pre-attempt) carries the server key move (UCI) AND `puzzle_type`. Owner
  2026-10-07: cheating is not a concern (anyone can run Stockfish in another tab, and `move_quality`
  for off-key moves is already client-asserted). `puzzle_type` is sent because it changes UX: it
  lets the D-10 re-check run before the POST on sharp puzzles only. The guess UI must still never
  DISPLAY the puzzle type or the key before the attempt. Rewrite the `TrainPuzzle` docstring (and
  the `PuzzleRevealResponse` / `SolveRequest` docstrings that cite P-01) to record the new rule and
  why. `source` stays as it is unless the planner finds the client needs it.
  — **Reversibility:** costly — a published API contract change; the frontend grading path is
  rebuilt around the pre-attempt key, so reverting means reinstating mount best-move search and the
  old grading path.
- **D-06:** Key per source: SR item = `game_positions.best_move` at the flaw ply (the existing deep
  answer key); herring = the top entry of the server-certified `herring_pool.ladder`; sharp filler =
  the solution move from `app/data/sharp_filler_puzzles.csv`.
- **D-07:** No key available (~0.4% of SR items have no `game_positions.best_move`): send `null` and
  fall back to today's behavior (client mount best names the solution, today's grading path). No
  pool change.
- **D-08:** Mount search moves from "find the best move at the root" to "evaluate the position after
  the key" during think time, so the wait after the move is unchanged (one after-move search of the
  played move, or none when played == key).

#### Reveal (amends 190.1-03 D-01/D-05)
- **D-09:** The server picks every move shown (key arrow and solution card, soft `su`, herring
  ladder "also fine" moves); the phone supplies every number. The solution line = key + the phone's
  after-key PV and eval. Other displayed lines stay clamped to the key line's eval
  (`clampLineEvalToBest`, now capped by the key line) EXCEPT in a confirmed disagreement (D-15).
  190.1-03's rule that no server number is displayed still holds; only the solution MOVE now comes
  from the server.

#### Disagreement re-check
- **D-10 Trigger:** `puzzle_type == sharp` (SR sharp AND sharp filler), played != key, played !=
  `su` (D-02 owns that), and the phone's 1.5s grade vs the key is **good** (owner picked "good
  only"; an inaccuracy reading is not re-checked).
- **D-11 Budget:** re-run BOTH after-move searches (key and played) at 3s each, sequentially (~6s).
  The re-check's verdict replaces the 1.5s grade whatever it says. `TRAIN_GRADING_TIMEOUT_MS`
  (8000) must be raised for this path (new named constants).
- **D-12 Wait UX:** while the re-check runs, "Checking your move…" switches to an explicit message
  along the lines of "Taking a closer look…".
- **D-13 Outcomes:** re-check still rates the played move good -> **confirmed** disagreement:
  benefit of the doubt, `move_quality = good`. Otherwise -> **resolved**: the re-check's tier is
  recorded as usual.

#### Confirmed disagreement: guess, copy, numbers
- **D-14 Guess (amends P-02):** after a confirmed disagreement the position is treated as ambiguous:
  EITHER guess ("critical" or "several") earns the guess point (`correct_guess = true`). The server
  computes this, accepting the client's disagreement claim after sanity checks (puzzle is sharp,
  played != key and != `su`, claimed tier good). The weekly leaderboard (Phase 230) picks this up
  automatically through `correct_guess`. Owner rationale: crediting the move while marking a
  "several" guess wrong would contradict itself on one screen.
  — **Reversibility:** costly — changes recorded `correct_guess` values (and leaderboard points)
  for affected solves; reverting does not restore past rows.
- **D-15 Copy (owner sign-off on a new branch in LOCKED `guessFeedbackProse`):** one line for both
  guesses: **"Qh4 is the engine's first choice, but your move holds up too."** (Qh4 = key SAN).
  It replaces every "only one move works" branch on this path. The existing six strings stay verbatim.
- **D-16 Numbers:** in a confirmed disagreement the reveal shows the phone's honest evals (no clamp),
  so the played line may read above the key's.

#### Disagreement record
- **D-17:** Record EVERY re-check (outcome `confirmed` and `resolved`), not only confirmed ones, so
  a review can separate phone noise (resolved) from a likely bad answer key (confirmed), per source.
- **D-18:** Storage: a new nullable JSONB column `drill_solves.recheck` (name at planner's
  discretion), NULL when no re-check ran. It travels as its own Pydantic-validated `SolveRequest`
  field (`extra="forbid"`, capped/typed values, a `v` version key), separate from `telemetry`,
  because it feeds grading and Phase 233 D-05 forbids telemetry as a grading input. Omit the column
  from the write when absent so it stays SQL NULL (memory
  `project_asyncpg_jsonb_null_vs_sql_null`).
  — **Reversibility:** costly — Alembic migration adding a column; dropping it later loses the
  collected re-check data.

### Claude's Discretion
- Exact field names (`TrainPuzzle` key/type fields, the re-check column and its keys). Suggested
  payload: outcome, key and played ES at 1.5s and at 3s, depth reached per search, `v: 1`.
- Exact wait-message copy (D-12) within the "Taking a closer look…" intent.
- The new timeout and re-check movetime constants and where they live.
- Server sanity-check details for D-14, and how a re-check claim on a non-sharp puzzle is handled
  (ignore it rather than fail the solve, matching the telemetry drop-invalid pattern).
- Whether the solve POST should carry the 1.5s client ES values even without a re-check (not required).
- How the stale-bundle case degrades (old client ignores the new `TrainPuzzle` fields and grades the
  old way; the server must still accept its solve).

### Deferred Ideas (OUT OF SCOPE)
- A user who guessed "several" and played the key on a mis-classified sharp puzzle (the user-28
  case) still gets "wrong call"; the re-check never runs when played == key. This is answer-key
  quality (ROADMAP step 4): watch the confirmed rate, then a follow-up seed for deeper sharp
  verification before pool entry or a larger runner-up budget.
- A server-side deep re-check queue for puzzles with confirmed disagreements (SEED-192 step 3),
  possibly flipping the stored puzzle type.
- Re-checking a phone "inaccuracy" reading on sharp puzzles (owner chose "good only" for now).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped (ROADMAP: "Requirements: TBD"). The locked decisions are the requirement set.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Grade vs key, client engine both sides | §Client grading flow, Pattern 2 (anchor), Pitfall 3 |
| D-02 | Server-graded sharp `su` | §Server solve path, Pattern 4 (`ServerGradedMove`) |
| D-05 | Key + puzzle_type in `TrainPuzzle` | §Key availability per source, Pattern 1, Open Question 1 |
| D-06 | Key per source | §Key availability per source (file:line for each) |
| D-07 | Null-key fallback | Pattern 2 (legacy anchor = root search) |
| D-08 | Mount search = after-key search | Pattern 2 |
| D-09 | Server picks moves, phone supplies numbers, clamp to key line | §Reveal consumers, Pitfall 4 |
| D-10 | Re-check trigger | Pattern 3 (`shouldRecheck`), Open Question 1 (`su` on client) |
| D-11 | 3s + 3s, new constants | Pattern 3, Pitfall 1 (node cap measured) |
| D-12 | "Taking a closer look…" | §Bubble state |
| D-13 | confirmed / resolved | Pattern 3 |
| D-14 | Either guess earns the point on confirmed | Pattern 5 (`_resolve_grade`), Security |
| D-15 | New `guessFeedbackProse` branch | §Reveal consumers, Open Question 3 |
| D-16 | Unclamped evals on confirmed | Pattern 3 |
| D-17/D-18 | `drill_solves.recheck` JSONB, every re-check | Pattern 6, §Alembic |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Router convention `APIRouter(prefix="/train", ...)`, no business logic in routers; SQL lives in repositories. [VERIFIED: CLAUDE.md]
- `Literal[...]` for every fixed value set (puzzle_type, recheck outcome); never bare `str`. [VERIFIED: CLAUDE.md]
- Pydantic at boundaries, TypedDict/dataclasses internally; ty must pass with zero errors; explicit return types; `# ty: ignore[rule]` only with reason. [VERIFIED: CLAUDE.md]
- No magic numbers: new movetime / node cap / timeout / caps are named constants. [VERIFIED: CLAUDE.md]
- Nesting depth <= 4 gated by `scripts/check_function_size.py app/` and eslint `max-depth`; `record_solve` and `gradeMoveInner` are already long, so new logic goes in helpers. [VERIFIED: CLAUDE.md]
- Never `asyncio.gather` on one `AsyncSession`. [VERIFIED: CLAUDE.md]
- Avoid native PG ENUM; JSONB columns: never write Python `None` (JSON null), omit the column instead. [VERIFIED: CLAUDE.md + memory project_asyncpg_jsonb_null_vs_sql_null]
- Sentry: `capture_exception` in non-trivial except blocks; no variables in messages. Expected validation drops (malformed recheck) are NOT captured (Phase 233 precedent). [VERIFIED: CLAUDE.md]
- Frontend: `data-testid` on interactive elements, `text-sm` floor, theme colors from `theme.ts`, knip must pass (no dead exports), `npm run build` required for shared-type changes. [VERIFIED: frontend/CLAUDE.md]
- Comment bug fixes at the fix site. Pre-merge gate (ruff format/check, ty x2, function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip). [VERIFIED: CLAUDE.md]
- Em-dashes sparingly in UI copy (D-12/D-15 copy has none). [VERIFIED: CLAUDE.md]
- Memory: no plan step may run `bin/reset_db.sh`; the migration runs via `alembic upgrade head` on the existing dev DB. [VERIFIED: MEMORY.md]

## Standard Stack

No new packages. Everything is in the existing stack. [VERIFIED: codebase]

| Component | Version | Role in this phase |
|-----------|---------|--------------------|
| python-chess | 1.11.x (CLAUDE.md) | Legality check of the key UCI against the puzzle FEN at composition (cheap, already imported in `train_repository.py:23`) |
| SQLAlchemy 2.x async + asyncpg | project | One session-scoped key query; JSONB column |
| Alembic | project | One `add_column` migration |
| Pydantic v2 | project | `SolveRecheck` model with wrap-validator drop |
| stockfish (npm, SF18 lite-single WASM) | 18.0.8 [VERIFIED: `require('stockfish/package.json').version`] | Client searches, headless repro |
| chess.js | project | `fenAfterUciMove`, SAN for D-15 copy |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages. **Packages removed:** none. **Packages flagged:** none.

## Key availability per source (planner question 1)

### Today at `TrainPuzzle` construction
`app/routers/train.py:104-113` maps `ComposedPuzzle` field-by-field; `ComposedPuzzle` (`train_repository.py:177-194`) carries only `position, game_id, ply, fen, side_to_move, last_move_uci, herring_pool_id`. [VERIFIED: read]

`TrainPuzzle` today [VERIFIED: app/schemas/train.py:57-62]:
```
    position: int
    game_id: int | None
    ply: int
    fen: str
    side_to_move: Literal["white", "black"]
    last_move_uci: str | None
```

`ComposedPuzzle` is built at TWO sites: fresh composition `_materialize_session_rows` (`train_repository.py:2170-2180`, from `_ReconstructedPuzzle`, which DOES carry `source` and `sharp_puzzle_id`) and resume `load_session_puzzles` (`:1286-1421`, from the `DrillSolve` row). The IntegrityError branch (`:2184-2200`) and `_resolve_existing_session` both route through `_resume_session` -> `load_session_puzzles`. [VERIFIED: read]

| Source | Key (D-06) | Loaded at compose today? | How to get it |
|--------|-----------|--------------------------|---------------|
| SR item | `game_positions.best_move` at the flaw ply | **No.** Only read at solve time, and only when the blob is non-empty (`_classify_and_certify_solve`, `train_repository.py:2531-2540`). The due/pool queries in `_select_candidates` keep `(game_id, ply, Game)` only; the blob is undeferred by `pool_entry_stmt` but the `GameFlaw` entity is discarded. | Join `GamePosition` on PK `(user_id, game_id, ply)` (`game_positions_pkey`, `app/models/game_position.py:54`). |
| SR puzzle_type | `classify_puzzle_type(missed_pv_lines, mover_color_for_ply(ply))` (`train_pool.py:262-309`) | No (blob not carried) | Join `GameFlaw` on PK `(user_id, game_id, ply)`, select `missed_pv_lines`. |
| SR runner-up | `missed_pv_lines[0]["su"]` (blob shape documented at `app/models/game_flaw.py:108-116`) | No | Same blob read. |
| Herring | `ladder[0]["move_uci"]` (`ladder` element shape `{"move_uci": str, "cp": int \| null, "mate": int \| null}`, five entries best-first, white POV: `app/models/herring_pool.py` docstring) | Fresh path: yes (`herring_stmt` undefers `ladder`, `train_pool.py` herring_stmt `.options(undefer(HerringPool.ladder))`), but only `pool_row.fen/arriving_move_uci/mover_color` are copied into `_ReconstructedPuzzle`. Resume path: **no**, `load_session_puzzles` selects `HerringPool` without `undefer`, so touching `.ladder` there raises MissingGreenlet. | Select the `HerringPool.ladder` column explicitly in the key query. puzzle_type is always `"herring"` (`_classify_and_certify_solve:2464-2504`). |
| Sharp filler | `SharpPuzzle.solution_uci` | In memory (`SHARP_SET_BY_ID`, `app/services/sharp_filler.py`), keyed by `drill_solves.sharp_puzzle_id` | No query. puzzle_type always `"sharp"` (`train_repository.py:2505-2510`). No runner-up. |

CSV header [VERIFIED: app/data/sharp_filler_puzzles.csv:7]: `puzzle_id,fen,first_move_uci,solution_uci,ply,side_to_move,motif,rating,themes`. The served `fen` is the position AFTER `first_move_uci` and `solution_uci` is the move to play; `scripts/gen_sharp_filler_set.py:301-316` only accepted rows where its own MultiPV-5 PV0 equals `solution_uci`. [VERIFIED: read]

Mover color: SR uses ply parity `mover_color_for_ply` (`app/services/best_move_candidates.py:65-68`: `return "white" if ply % 2 == 0 else "black"`); herring uses the STORED `HerringPool.mover_color`, never parity (SEED-120 Pitfall 1, comment at `train_repository.py:2485-2495`). [VERIFIED: read]

**Query cost:** one extra query per `POST /train/sessions` (which runs on every Train page mount as a status read), touching at most `puzzles_per_session` (<= 50, `TrainSettingsUpdate` bound) rows through three primary-key/PK-FK lookups. Negligible. [VERIFIED: PK definitions read; cost estimate ASSUMED]

## Architecture Patterns

### System Architecture Diagram

```
POST /train/sessions
  compose_and_materialize_session ──► (fresh | resume | race-resume) ComposedSession
        │
        ▼
  _attach_answer_keys(session_id)  ── ONE query: drill_solves (unsolved, this session, this user)
        │                                ⟕ game_flaws(missed_pv_lines) ⟕ game_positions(best_move)
        │                                ⟕ herring_pool(ladder, mover_color)
        ▼
  answer_key_for(row) [pure, train_pool.py]  ◄── reused by _classify_and_certify_solve at solve time
        │  -> key_move_uci (legality-checked vs fen), puzzle_type, runner_up_uci (sharp SR only)
        ▼
  TrainPuzzle {.., key_move_uci, puzzle_type, runner_up_uci}
        │
        ▼ (client)
  startGrading(fen, key) ── key? ──yes──► after-key search 1.5s  ──► anchor{keyUci, keyLine, es}
        │                   └─no (D-07)─► root search 1.5s (today) ──► anchor{rootBest, rootLine, es}
  user guesses + moves
        ▼
  gradeMove(fen, played): played == anchor.keyUci ? GOOD (no search)
                          : after-played search 1.5s, drop = anchor.es - es(played)
        ▼
  shouldRecheck(puzzle_type, key, runner_up, played, tier)? ─no─► POST
        │yes ("Taking a closer look…")
        ▼
  recheckMove: after-key 3s, then after-played 3s (raised node cap, own timeout)
        │  tier from 3s pair; confirmed iff good; recheck payload {v:1, outcome, es/depth x4}
        ▼
POST /solve {.., move_quality, recheck?}
  record_solve: classification (live blob) ─► graded moves = vetted ∪ sharp-su
        ─► _resolve_grade: override (D-02/Phase 211) | D-14 acceptance | client tier
        ─► claim UPDATE (+ recheck column only when present)
        ▼
SolveResponse {.., disagreement}  ─► reveal: key arrow/line, D-15 copy, D-16 unclamped
```

### Recommended file touch list
```
app/schemas/train.py            # TrainPuzzle fields+docstring, SolveRecheck, SolveRequest.recheck, SolveResponse.disagreement, docstrings
app/services/train_pool.py      # PuzzleAnswerKey + answer_key_for (pure), runner-up grading helper, ServerGradedMove
app/repositories/train_repository.py  # ComposedPuzzle fields, _attach_answer_keys, SolveClassification widen, _resolve_grade, record_solve write
app/routers/train.py            # map new fields; pass recheck dump
app/models/drill_solve.py       # recheck column
alembic/versions/<new>_drill_solves_recheck.py
frontend/src/types/train.ts     # TrainPuzzle (optional fields), SolveRequest.recheck, SolveResponse.disagreement?
frontend/src/hooks/useTrainGradingEngine.ts  # anchor, startGrading(fen,key), recheckMove, node cap param, constants
frontend/src/lib/trainRecheck.ts (new)       # shouldRecheck + payload builder + mirrored constants
frontend/src/components/train/TrainSolveScreen.tsx  # startGrading(fen,key), recheck flow, isRechecking
frontend/src/components/train/trainBubbleState.ts / trainBotCopy.ts  # RECHECK copy
frontend/src/lib/trainGuessLabels.ts + TrainReveal.tsx  # D-15 branch, key SAN
```

### Pattern 1: one session-scoped key query + shared pure derivation
**What:** after `compose_and_materialize_session` resolves a `ComposedSession` with `session_id` not None and non-empty `puzzles`, run one SELECT keyed by `position` and `dataclasses.replace` each frozen `ComposedPuzzle` with `key_move_uci`, `puzzle_type`, `runner_up_uci`.
**Why here:** it is the single funnel for all three return paths (fresh, resume, IntegrityError resume), and the drill_solves rows are flushed before `_materialize_session_rows` returns (`await session.flush()` at `train_repository.py:2181`).
**Sketch (names are discretion, shapes are verified):**
```python
# train_repository.py — joins mirror _classify_and_certify_solve's own scoping
stmt = (
    select(
        DrillSolve.position, DrillSolve.source, DrillSolve.ply, DrillSolve.sharp_puzzle_id,
        GameFlaw.missed_pv_lines, GamePosition.best_move,
        HerringPool.ladder, HerringPool.mover_color,
    )
    .outerjoin(GameFlaw, and_(GameFlaw.user_id == DrillSolve.user_id,
                              GameFlaw.game_id == DrillSolve.game_id, GameFlaw.ply == DrillSolve.ply))
    .outerjoin(GamePosition, and_(GamePosition.user_id == DrillSolve.user_id,
                                  GamePosition.game_id == DrillSolve.game_id, GamePosition.ply == DrillSolve.ply))
    .outerjoin(HerringPool, HerringPool.id == DrillSolve.herring_pool_id)
    .where(DrillSolve.session_id == session_id, DrillSolve.user_id == user_id,
           DrillSolve.solved_at.is_(None))
)
```
Selecting the deferred columns explicitly in `select(...)` bypasses mapper deferral (no `undefer` needed). The SR join must be gated per source in Python (a herring row with a non-null `game_id` can also match a `game_flaws` row of its source user, so only read blob/best_move when `source == DrillSource.SR_ITEM`).

`answer_key_for(...)` lives in `train_pool.py` (pure, unit-testable without DB) and returns a frozen dataclass `PuzzleAnswerKey(key_uci: str | None, puzzle_type: Literal["sharp","soft","herring"], runner_up_uci: str | None)`. Rules:
- SR: `puzzle_type = classify_puzzle_type(blob, mover_color_for_ply(ply))`; `key = best_move` (None if NULL/empty); `runner_up = node["su"]` only when `puzzle_type == "sharp"` and `su` is a non-empty str.
- Herring: `puzzle_type="herring"`, `key = ladder[0]["move_uci"]` when shape-valid.
- Filler: `puzzle_type="sharp"`, `key = SHARP_SET_BY_ID[id].solution_uci`, `runner_up=None`.
- Legality: drop the key (send `null`, D-07 path) unless `chess.Move.from_uci(key) in chess.Board(fen).legal_moves`. One python-chess board per puzzle, FEN already reconstructed.
`_classify_and_certify_solve` must reuse the same function so the solve-time `key`/`runner_up` used by D-02/D-14 sanity checks is derived identically.

### Pattern 2: client "anchor" generalizes the mount search (D-01/D-07/D-08)
**What:** replace `bestSearchRef: BestSearchResult` with an anchor:
```ts
interface GradingAnchor {
  fen: string; generation: number;
  keyUci: string | null;      // server key, or root bestmove in legacy mode
  keyLine: TrainEngineLine;   // rooted at the PUZZLE fen: [keyUci, ...afterKeyPv]
  es: number;                 // mover-POV ES of keyLine's eval
  depth: number;              // rank-1 depth, for the recheck payload
  legacy: boolean;            // true when the key was null/illegal (D-07)
}
```
- `startGrading(fen, keyUci: string | null)`: if `keyUci` is non-null AND `fenAfterUciMove(fen, keyUci)` is non-null, search the after-key FEN (width 1, `TRAIN_GRADING_MOUNT_MOVETIME_MS`) and build `keyLine = [keyUci, ...raw.pv]`. Else run today's root search; `keyLine = bestLineFrom(raw)`, `keyUci = raw.bestMoveUci`.
- `gradeMoveInner`: `played === anchor.keyUci` -> GOOD, no search, `playedLine = keyLine`. Otherwise one after-played search at `TRAIN_GRADING_MOVETIME_MS`; `classifyLiveSeverity(anchor.es, esPlayed)`; `playedLine` clamped to `keyLine`.
- Keep `GradeResult.bestMoveUci = anchor.keyUci`, `bestLine = keyLine`, `esBefore = anchor.es`, `esAfter = esPlayed`. Every consumer (`TrainReveal.tsx:279` `gradeResult?.bestLine.moves[0]`, `TrainSolveScreen.tsx:1288` playedMoveQuality, `:1320` overlay, `:855` free-play seed, `TrainReveal.tsx:886`) then names the key with no code change. [VERIFIED: read]
- Sign: `dispatchNow` already normalizes every search to white POV from the searched FEN's side to move (`whitePovSign`), so an after-key eval is directly comparable to an after-played eval with the PUZZLE mover. [VERIFIED: useTrainGradingEngine.ts dispatchNow]

### Pattern 3: re-check as its own imperative step (D-10..D-13, D-16)
**What:** a pure `shouldRecheck` in a new `frontend/src/lib/trainRecheck.ts`, and a new `recheckMove(fen, playedUci): Promise<RecheckResult>` on `TrainGradingEngine`.
```ts
export function shouldRecheck(p: {
  puzzleType: TrainPuzzleType | null; keyUci: string | null; runnerUpUci: string | null;
  playedUci: string; tier: TrainMoveTier;
}): boolean {
  return p.puzzleType === 'sharp' && p.keyUci !== null && p.playedUci !== p.keyUci
    && p.playedUci !== p.runnerUpUci && p.tier === 'good';
}
```
- `recheckMove`: sequentially `search(afterKeyFen, gen, 1, TRAIN_RECHECK_MOVETIME_MS, TRAIN_RECHECK_MAX_NODES)` then the after-played FEN at the same budget; tier from `classifyLiveSeverity(esKeySlow, esPlayedSlow)`; outcome `'confirmed'` iff tier is good (D-13). Wrapped in the same settle-once timeout shape as `gradeMove` with its own `TRAIN_RECHECK_TIMEOUT_MS`.
- `dispatchNow` hard-codes `nodes ${TRAIN_GRADING_MAX_NODES}` (`useTrainGradingEngine.ts:371`); a `maxNodes` must travel WITH the dispatch like `width`/`movetimeMs` already do (`QueuedDispatch`, readyok drain, stop-queue drain).
- Return a full replacement `GradeResult` (slow `keyLine`, slow `playedLine`, `esBefore/esAfter` = slow pair, `moveTier` from the slow pair) plus the payload. D-16: on `confirmed` do NOT clamp `playedLine` (and skip the game-line clamp in `startGameMoveSearch` for this puzzle); on `resolved` clamp to the slow key line as usual.
- `TrainSolveScreen.gradeAndSolve` (`:1066-1105`): after `gradeMove`, if `shouldRecheck(...)` set `isRechecking`, `await recheckMove`, replace `grade`, attach `recheck` to the POST body. Recommended failure handling (discretion): on re-check timeout/error keep the 1.5 s grade and send no `recheck` (no confirmed claim, so no D-14 credit). `retrySolve` re-sends the frozen payload, so a POST retry never re-runs the re-check. [VERIFIED: useTrainSession lastSolvePayload]

### Pattern 4: server-graded moves list (D-02)
`VettedMove.quality` is `Literal["best", "good", "inaccuracy"]` and the list is DISPLAYED as "Also fine" (`SolveResponse.vetted_moves`), so the sharp `su` (a mistake by construction: `SHARP_GAP_ES: float = MISTAKE_DROP`, `train_pool.py:77`; `MISTAKE_DROP: float = 0.10`, `flaws_service.py:48`) must NOT be appended to `vetted_moves`. [VERIFIED: read]
Recommended: a domain `ServerGradedMove(uci, tier: Literal["good","inaccuracy","wrong"], es_before, es_after)`; `SolveClassification` gains `graded_moves` = vetted entries mapped (`best`->`good`) + for a sharp SR node with non-empty `su` and resolvable `b`/`s`: `tier` from `classify_severity(best_es - second_es)` (`None`->good, `inaccuracy`->inaccuracy, mistake/blunder->wrong; always `wrong` in practice), `es_before=best_es`, `es_after=second_es`. `_override_for_key_move` searches `graded_moves`. Order matters: if `su == best_uci` (data inconsistency already handled in `vetted_moves_from_pv_node`), the key must win (good). `graded_es_before/after` are then non-null for a sharp `su`, so the board badge follows the server numbers (existing Phase 211 seam, `TrainSolveScreen.tsx:1291-1293`).

### Pattern 5: one pure grade resolver (D-14)
Extract the post-classification decision out of `record_solve` (`train_repository.py:3013-3049`) into a pure function (keeps `record_solve` from growing past the depth/size guidance and makes D-14 unit-testable without a DB):
```python
def _resolve_grade(*, guess, played_move, client_tier, classification, recheck) -> ResolvedGrade:
    # 1. server-graded move (Phase 211 vetted + D-02 sharp su) -> server tier + graded ES
    # 2. else D-14: accept iff recheck is not None and recheck.outcome == "confirmed"
    #    and classification.puzzle_type == "sharp" and classification.key_uci is not None
    #    and played_move != classification.key_uci and played_move != classification.runner_up_uci
    #    and client_tier == "good"  -> correct_guess=True, disagreement=True
    # 3. else client tier + _compute_correct_guess(guess, puzzle_type)
```
A claim failing any check is ignored (recorded, but grants nothing), never a 422 (CONTEXT discretion; matches the telemetry drop pattern). Recommended extra check: the payload's 3 s ES pair must itself classify as good (`classify_severity(key_es - played_es) is None`), enforced as a Pydantic `model_validator` so an internally inconsistent claim is dropped at the boundary.

### Pattern 6: the recheck column (D-17/D-18), copy Phase 233
- Model: mirror `telemetry` exactly (`app/models/drill_solve.py:196-197`): `recheck: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True, default=None)`. [VERIFIED: read]
- Schema: a `SolveRecheck(BaseModel)` with `model_config = ConfigDict(extra="forbid")`, `v: Literal[1]`, `outcome: Literal["confirmed", "resolved"]`, four ES floats `Field(ge=0, le=1, allow_inf_nan=False, strict=True)`, four depths `int` capped; on `SolveRequest`: `recheck: SolveRecheck | None = None` with a `mode="wrap"` validator returning None on `ValidationError` (copy `_drop_invalid_telemetry`, `app/schemas/train.py:314-326`). Keep `SolveRequest` itself WITHOUT `extra="forbid"` (stale bundles, see §Stale bundle).
- Router: `recheck=body.recheck.model_dump() if body.recheck is not None else None` (mirror `routers/train.py:164-166`).
- Repository: add `claim_values["recheck"] = recheck` ONLY when present (mirror `train_repository.py:3053-3057`). A plain set, not the `||` merge: one write per solve. Recommended: the server adds an `accepted: bool` key (D-14 outcome) to the stored dict so a later review and the lost-claim re-read both see whether credit was granted without re-deriving it.
- If the TS side mirrors any caps (depth cap, version), add a regex parity test like `tests/schemas/test_train_telemetry_parity.py` (plain-integer `export const NAME = <int>;` literals).

### Anti-Patterns to Avoid
- **Appending sharp `su` to `vetted_moves`:** renders a mistake as "Also fine". Use the separate graded list.
- **Re-using `rankLineForMove(best.lines, gameMoveUci)` after D-08** (`useTrainGradingEngine.ts:832`): the anchor search's `lines` are rooted at the AFTER-KEY FEN, so a game move could falsely match the opponent's reply. Replace with `gameMoveUci === anchor.keyUci ? anchor.keyLine : search`.
- **Mixing server and client numbers in one drop** (D-01): the server's `graded_es_*` only ever pair with each other.
- **Making `TrainPuzzle`'s new TS fields required:** every fixture (`TrainStartScreen.test.tsx:226`, `useTrainSession.test.ts:44`, `TrainSolveScreen.test.tsx:345`, `TrainSolveScreen.restoredGameArrow.test.tsx:153`) and `trainRevealCache` entries written by the previous bundle would break; use optional fields with one nullish default at the consumption site (the established `SolveResponse.vetted_moves?` pattern, `frontend/src/types/train.ts:187-199`).
- **Folding the re-check into `gradeMove`'s 8 s race:** a 1.5 s + 3 s + 3 s path exceeds `TRAIN_GRADING_TIMEOUT_MS = 8000` (`useTrainGradingEngine.ts:109`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ES sigmoid / severity bands | new thresholds | `evalToExpectedScore`, `classifyLiveSeverity` (`liveFlaw.ts`), `classify_severity`, `expected_score_for` (server) | CI drift-checked against `flaws_service.py`; one ladder both sides |
| Puzzle-type classification | a second gap test | `classify_puzzle_type` | composition and solve must agree |
| Malformed JSONB payload handling | try/except in the router | Pydantic wrap validator (`_drop_invalid_telemetry` pattern) | proven Phase 233 shape, no 422 for stale/tampered clients |
| JSONB null-vs-SQL-NULL | `values(recheck=None)` | omit the key from `claim_values` | asyncpg writes `null::jsonb` otherwise |
| Move legality / SAN | string parsing | python-chess (server), chess.js `fenAfterUciMove` / `sanFromPlayedUci` (client) | castling, promotion |
| Search serialization | parallel searches | the hook's existing `search()` stop/queue state machine | single-threaded lite WASM (CONTEXT Established Patterns) |

## Server solve path (planner question 3)

- `SolveRequest` (`app/schemas/train.py:276-326`): `position`, `guess: Literal["critical","several"]`, `played_move` (4-5 chars), `move_quality: Literal["good","inaccuracy","wrong"]`, `telemetry: SolveTelemetry | None = None` + wrap validator. No `model_config` (so unknown keys are ignored, default `extra="ignore"`). [VERIFIED: read]
- `SolveResponse` (`:355-400`): twelve fields incl. `puzzle_type: Literal["sharp", "soft", "herring"]` (`:392`), `vetted_moves`, `graded_es_before/after`. [VERIFIED: read]
- `record_solve` (`train_repository.py:2924-3172`): row lookup scoped by user -> `_classify_and_certify_solve` -> `_compute_correct_guess` (`:3016`) -> `_override_for_key_move` (`:3024`) -> effective tier -> claim UPDATE with `solved_at IS NULL` guard -> SR ladder advance -> completion. Lost claim re-reads stored `correct_guess/correct_move/move_quality` (`:3092-3110`). [VERIFIED: read]
- `_classify_and_certify_solve` (`:2441-2547`): herring -> ladder vetted; filler -> `("sharp", [])`; SR -> live blob + `best_uci` read only `if missed_pv_lines and solve.game_id is not None` (`:2531-2540`). The sharp `su` and `b`/`s` are in `missed_pv_lines[0]` already loaded here, so D-02 adds no query. [VERIFIED: read]
- Plug points: D-02 in the classification result (Pattern 4); D-14 in `_resolve_grade` (Pattern 5); D-18 in `claim_values` beside telemetry (Pattern 6); `RecordedSolve` and `SolveResponse` gain `disagreement: bool` (lost-claim path: read from the stored `recheck["accepted"]`).
- Update `test_solve_response_key_set_is_exactly_the_wire_contract` (`tests/routers/test_train.py:1665-1700`) for the new response field and `test_pre_attempt_payload_shape` (`:1090-1121`) for the new `TrainPuzzle` key set (both are equality tests by design). `test_vetted_move_material_absent_from_request_and_pre_attempt_schemas` (`:1732-1740`) stays valid if the new field names avoid `vetted_moves`/`graded_es_*`.

## Client grading flow (planner question 2)

| Element | Today (file:line) | Change |
|---------|-------------------|--------|
| Constants | `TRAIN_GRADING_MOVETIME_MS = 1500` (:78), `TRAIN_GRADING_MAX_NODES = 2000000` (:79), `TRAIN_GRADING_MULTIPV_WIDTH = 1` (:96), `TRAIN_GRADING_MOUNT_MOVETIME_MS = TRAIN_GRADING_MOVETIME_MS` (:97), `TRAIN_GRADING_TIMEOUT_MS = 8000` (:109) | keep; add `TRAIN_RECHECK_MOVETIME_MS`, `TRAIN_RECHECK_MAX_NODES`, `TRAIN_RECHECK_TIMEOUT_MS` |
| `startGrading(fen)` (:613) | root search width 1 | `startGrading(fen, keyUci)` -> anchor (Pattern 2); callers `TrainSolveScreen.tsx:1059` and `:1136` pass `puzzle.key_move_uci ?? null` |
| `gradeMoveInner` (:662) | root `esBefore` vs after-move `esAfter`; exact match to root bestmove | anchor ES vs after-played ES; exact match to key |
| `clampLineEvalToBest` (:258, used :736, :868) | cap at root best line | cap at `anchor.keyLine`; bypass when confirmed (D-16) |
| `startGameMoveSearch` (:807) | rank lookup in root `lines` (:832) | `gameMoveUci === anchor.keyUci` short-circuit (Anti-pattern above) |
| `gradeAndSolve` (TrainSolveScreen :1066) | grade -> POST `move_quality: grade.moveTier` (:1088) | grade -> maybe recheck -> POST with `recheck` |
| Bubble "grading" (`trainBubbleState.ts:58`, render `TrainSolveScreen.tsx:629-636`, copy `GRADING_COPY = 'Checking your move…'` `trainBotCopy.ts:200`) | one spinner copy | add `RECHECK_COPY` (e.g. `'Taking a closer look…'`) selected by an `isRechecking` flag in the bubble deps (or `{kind:'grading', recheck:boolean}`) |
| Best arrow / solution card (`TrainReveal.tsx:279`, `trainArrows.ts:391-430`) | `gradeResult.bestLine.moves[0]` = phone pick | unchanged code, now the key via `GradeResult` |
| Guess prose (`trainGuessLabels.ts:73-90`, called `TrainReveal.tsx:1027-1035`) | six LOCKED strings | new FIRST guard: when `verdict.disagreement === true` return `` `${keySan} is the engine's first choice, but your move holds up too.` `` (key SAN via `sanFromPlayedUci(puzzle.fen, keyUci)`) |

## Reveal "also fine" mapping (planner question 8)

The "also fine" row and green arrows already come ONLY from the server's `vetted_moves` (soft: `[best, su]` or su-only/best-only; herring: good-band ladder entries; sharp/filler: `[]`), filtered against `bestMoveUci` and the played move before capping (`trainArrows.ts:421-424`). With `bestMoveUci` = key: the soft "best" entry (= `game_positions.best_move` = key) and the herring `ladder[0]` (= key) now dedupe against the blue arrow instead of producing a second "best-looking" arrow when the phone's pick differed. Nothing else names a move. D-09 therefore needs no change to `buildTrainRevealOverlay`. [VERIFIED: read]

## Stale-bundle compatibility (planner question 5)

- **Old client, new server:** extra `TrainPuzzle` JSON keys are ignored by the old bundle, which grades the old way (root vs after-move) and posts the old `SolveRequest` without `recheck` -> `recheck=None` -> today's `_compute_correct_guess`. D-02 still applies server-side to old clients (consistent improvement). Required test: an old-shape body is accepted and graded as today.
- **New client, old server (deploy window / browser with the new bundle against a not-yet-restarted API):** `TrainPuzzle` lacks the new keys -> `undefined ?? null` -> legacy anchor path, no re-check; `SolveRequest.recheck` is silently ignored because `SolveRequest` has no `extra="forbid"`. Hence: never add `extra="forbid"` to `SolveRequest` itself.
- **Restored reveal cache** (`trainRevealCache.ts`): `isCachedTrainReveal` only shallow-checks `puzzle.fen/position`, `verdict.move_quality`, `gradeResult.bestLine` (:96-118), so entries from the previous bundle keep restoring; `verdict.disagreement` must be optional with a single `?? false` default.

## Leaderboard (planner question 6)

`train_leaderboard_repository.py:48-60` scores rows from `DrillSolve.correct_guess.is_(True)` and `DrillSolve.move_quality` via `MOVE_QUALITY_TIER`/`MOVE_TIER_POINTS`; filler excluded from the Accuracy board by `source != SHARP_FILLER`. Medals finalize from the same aggregates. Other `correct_guess` readers: `activity_queries.py:492` (admin count) only. D-14 therefore needs no leaderboard change. [VERIFIED: read] Note: confirmed disagreements on sharp FILLER puzzles add Points-board guess points but not Accuracy (filler excluded), which is consistent with today.

## Common Pitfalls

### Pitfall 1: the 2M node cap makes a "3 s" re-check no deeper than ~2.7 s
**What goes wrong:** `dispatchNow` sends `go movetime ${movetimeMs} nodes ${TRAIN_GRADING_MAX_NODES}`; on a fast device the node cap stops the search first.
**Evidence (this session, headless SF18 lite WASM in Node 24, fresh hash per search, user-28 FEN):**
```
f4h4 movetime=1500 cap=2000000 depth=15 nodes=463608   score(opp POV)=cp -101 wall=1518ms
f4h4 movetime=3000 cap=2000000 depth=17 nodes=1928779  score(opp POV)=cp -381 wall=2863ms
b2b3 movetime=1500 cap=2000000 depth=16 nodes=695607   score(opp POV)=cp -66  wall=1509ms
b2b3 movetime=3000 cap=2000000 depth=20 nodes=2000425  score(opp POV)=cp -266 wall=2699ms
d1d5 movetime=1500 cap=2000000 depth=20 nodes=1181472  score(opp POV)=cp -119 wall=1506ms
d1d5 movetime=3000 cap=100000000 depth=22 nodes=2449718 score(opp POV)=cp -145 wall=3005ms
```
(`nodes` is the last exact PV line's counter, so it under-reports the final total.) The b3 search hit the cap at 2,699 ms in Node; browsers on desktop are likely faster [ASSUMED].
**How to avoid:** a `TRAIN_RECHECK_MAX_NODES` scaled with the movetime (e.g. 2x the grading cap), threaded through the dispatch.

### Pitfall 2: playing the sharp runner-up triggers a pointless 6 s re-check if the client lacks `su`
**Evidence:** at 1.5 s, key Qh4 reads +101 and `su` d1d5 reads +119 (white POV), ES drop `-0.0159` -> "good" -> D-10 would fire; at 3 s it resolves (+381 vs +119, drop 0.1948). D-02 overrides the tier anyway. See Open Question 1.

### Pitfall 3: the user-28 case itself is a played-key solve
The reported contradiction (arrow b3, user played Qh4) disappears through D-01/D-05 alone (played == key -> GOOD, arrow = Qh4). For the hypothetical "played b3" variant, the probe's 3 s pair (Qh4 +381 vs b3 +266, ES drop 0.0756 -> inaccuracy) would record a **resolved** re-check, not confirmed. Fresh hash in the probe vs the browser's warm hash (SEED-130), so treat as one data point, not a rate.

### Pitfall 4: puzzle type can change between composition and solve
`_classify_and_certify_solve` reads the LIVE blob; a reclassification between compose and solve can flip sharp/soft. The client's `puzzle_type` only gates whether it re-checks; the server's live type decides D-14 and the guess grade. A re-check claim on a now-soft puzzle is recorded but grants nothing. Do not "fix" this by snapshotting the type onto `drill_solves` (D-01 of Phase 189: no answer-key snapshot on that table, `drill_solve.py` module docstring).

### Pitfall 5: herring rows can match `game_flaws`
A herring `drill_solves` row may carry a non-null `game_id`/`ply` of a pool source game (possibly the user's own game, D-10 own-game herrings). The SR joins in the key query must be applied only when `source == SR_ITEM`, or a herring could pick up a blob-derived type.

### Pitfall 6: auto-queen underpromotion keys can never be matched
`uciFromDrop` and the solve drop force `promotion: 'q'` (`useTrainFreePlay.ts:489`, `TrainSolveScreen.tsx:1185`). A key like `e7e8n` never equals the played move, so it goes through the search path. Pre-existing limitation; do not add special handling (scope).

### Pitfall 7: displayed played-line eval vs server badge on a sharp `su`
With D-02 the badge follows the server pair (`graded_es_*`), while the "Your move" line shows the phone's after-move eval (clamped to the key line). They can tell slightly different stories (exactly the Phase 211 pattern for soft key moves). Accepted; mention in the plan, do not add server numbers to the line.

### Pitfall 8: knip and the `TrainGradingEngine` interface
Adding `recheckMove` to the interface means every hand-built engine mock (`TrainReveal.test.tsx:148`, `TrainSolveScreen.restoredGameArrow.test.tsx:144`) needs the method for `tsc -b`; new exports in `trainRecheck.ts` must be consumed (knip in the gate).

## Code Examples

### Phase 233 omit-when-absent JSONB write (the template for D-18)
```python
# Source: app/repositories/train_repository.py:3053-3057 (read this session)
    # D-01: add the column ONLY when there is a patch. Omitting it keeps "no
    # telemetry" a true SQL NULL (asyncpg would write Python None as a JSON null
    # VALUE, which `IS NULL` skips and which would break the later `||` merge).
    if telemetry is not None:
        claim_values["telemetry"] = _merged_telemetry(telemetry)
```

### Phase 233 drop-invalid wrap validator (the template for `SolveRequest.recheck`)
```python
# Source: app/schemas/train.py:314-326 (read this session)
    @field_validator("telemetry", mode="wrap")
    @classmethod
    def _drop_invalid_telemetry(
        cls, value: object, handler: ValidatorFunctionWrapHandler
    ) -> SolveTelemetry | None:
        try:
            return handler(value)
        except ValidationError:
            return None
```

### Alembic migration template
```python
# Source: alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py (read this session)
def upgrade() -> None:
    op.add_column('drill_solves', sa.Column('telemetry', postgresql.JSONB(none_as_null=True), nullable=True))
```
New migration: `down_revision = 'f4b9d2c7e815'` (current head [VERIFIED: `uv run alembic heads` -> `f4b9d2c7e815 (head)`; file `20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py:32` `revision: str = 'f4b9d2c7e815'`]), add `recheck` the same way. Metadata-only (nullable, no default), instant on prod.

## Alembic (planner question 4)

- Head: `f4b9d2c7e815` (`users.prompt_state and feedback.source`, Phase 234). [VERIFIED: alembic heads + file read]
- Model on: `20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py` (same table, same column type).
- Model to edit: `app/models/drill_solve.py`, add beside `telemetry` (:196-197). `DrillSource` values [VERIFIED: drill_solve.py:94-96]: `SR_ITEM = 0`, `RED_HERRING = 1`, `SHARP_FILLER = 2`.
- Test isolation: the pytest template DB auto-refreshes when the Alembic head changes (CLAUDE.md), so no manual step. Dev DB: `uv run alembic upgrade head` (no reset).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| P-01: no answer key pre-attempt | key + type (+ runner-up) pre-attempt | this phase (D-05) | rewrite `TrainPuzzle`, `PuzzleRevealResponse`, `SolveRequest` docstrings and the module docstring of `app/schemas/train.py` (:1-9) |
| Phone mount search names the solution | server key names it, phone supplies numbers | this phase (D-09) | `GradeResult` meaning shifts from "phone best" to "key" |
| Root vs after-move drop | after-key vs after-played | this phase (D-01) | apples to apples |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Desktop browsers run SF18 lite at >= the Node nps measured here, so the 2M cap binds within 3 s on many devices | Pitfall 1 | Low: raising the re-check node cap is harmless either way |
| A2 | Adding `runner_up_uci` to `TrainPuzzle` is within D-05/D-10's intent | Open Question 1 | Medium: if the owner refuses, played-`su` solves on sharp puzzles burn a 6 s re-check (server still grades them correctly) |
| A3 | D-15's line belongs in `guessFeedbackProse` (the guess card), not the verdict bubble's `verdictClause` | Open Question 3 | Low-medium: copy placement only |
| A4 | Re-check failure should fall back to the 1.5 s grade without a record | Pattern 3 | Low: alternative is the existing grading-error Retry state |
| A5 | `game_positions.best_move` at the flaw ply is legal in the reconstructed FEN for virtually all rows | Pattern 1 | Low: the legality check maps any bad row to the D-07 path |
| A6 | Key-query cost is negligible | Key availability | Low: PK lookups on <= 50 rows |

## Open Questions

1. **Send the sharp runner-up (`su`) pre-attempt?**
   - What we know: D-10 requires `played != su` for the trigger, decided pre-POST; D-05 lists only key and type. The probe shows `su` can read better than the key at 1.5 s.
   - Recommendation: add `runner_up_uci: str | None` to `TrainPuzzle`, populated only for sharp SR items (null otherwise, so it leaks nothing for soft puzzles that `puzzle_type` does not already reveal). Confirm with the owner as a one-line checkpoint, or treat as implied by D-10.
2. **Should the server also override `played == key` on sharp/filler puzzles?** Today the sharp key is not in `vetted_moves`, so the client's "good" stands. Not required by any decision; the new client asserts good with no search. Recommendation: leave it (scope), but `_resolve_grade` must treat `played == key` as "not a disagreement" for D-14.
3. **D-15 placement:** the phase description calls the line "new bubble copy", D-15 names `guessFeedbackProse` (rendered in the reveal's guess card, `TrainReveal.tsx:1027-1035`). The verdict bubble's clause for a confirmed disagreement is already "Right call [+1], right move [+2]." (`trainBotCopy.ts` `verdictClause`). Recommendation: follow D-15 (guess card), no bubble change.
4. **Carry the 1.5 s ES values on every solve?** Not required (CONTEXT). Recommendation: no; the re-check record carries both budgets when it matters.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | frontend build/tests, headless probe | ✓ | v24.19.0 | — |
| uv | backend | ✓ | 0.10.9 | — |
| Dev Postgres (docker) | backend tests, migration | ✓ | container `flawchess-dev-db-1` running | — |
| stockfish npm (SF18 lite WASM) | `measure-train-movetime.mjs`, probe | ✓ | 18.0.8 | — |

Headless probe script used this session: `temp/phase235/probe_budget.mjs` (gitignored drafts dir) resolves `stockfish`/`chess.js` from `frontend/package.json` via `createRequire`; reusable for a user-28 repro: `node temp/phase235/probe_budget.mjs`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-asyncio, xdist) backend; vitest (jsdom) frontend |
| Config file | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block |
| Quick run command | `uv run pytest tests/services/test_train_pool.py tests/schemas/ -x` ; `cd frontend && npx vitest run src/lib src/hooks/__tests__/useTrainGradingEngine.test.ts` |
| Full suite command | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Decision -> Test Map
| ID | Behavior | Type | Test file (new = Wave 0) | Assertion |
|----|----------|------|--------------------------|-----------|
| D-05/D-06 | `answer_key_for` per source | unit | `tests/services/test_train_pool.py` | SR: key = best_move, type from blob, runner_up only when sharp; herring: key = ladder[0].move_uci, type "herring"; filler: key = solution_uci, type "sharp"; illegal key -> None |
| D-05 | wire key set | router | `tests/routers/test_train.py::test_pre_attempt_payload_shape` (update) | `set(puzzle.keys()) == {six old + key_move_uci, puzzle_type, runner_up_uci}` |
| D-05 | resume path carries keys (incl. herring ladder, deferred column) | repo | `tests/repositories/test_train_repository.py` (new test near `test_resume_serves_herring_with_deleted_source_game`) | resumed `ComposedPuzzle.key_move_uci` equals pool ladder[0] / best_move / solution |
| D-07 | no best_move -> null | repo/router | same files | SR with no `game_positions` row -> `key_move_uci is None`, type still computed |
| D-02 | sharp `su` graded server-side | repo | `test_train_repository.py` (pattern of `test_record_solve_overrides_key_move_grade`) | client asserts "good" on `su` of `_SHARP_PV_LINES` -> recorded `wrong`, `graded_es_*` = (best_es, second_es), `vetted_moves == []` |
| D-14 | confirmed accepted | unit + router | new pure tests for `_resolve_grade`; router test | sharp + off-key + off-su + good + confirmed -> `correct_guess` True for BOTH guesses, `disagreement` True |
| D-14 | sanity rejects | unit | same | soft/herring type, played == key, played == su, tier != good, outcome resolved -> no credit, normal `correct_guess` |
| D-17/D-18 | column write | router | `tests/routers/test_train.py` (copy `_telemetry_row` helper) | no recheck -> `recheck IS NULL` true (SQL NULL); resolved and confirmed both stored as JSON object; resubmit keeps first |
| D-18 | schema | schema | new `tests/schemas/test_train_recheck_schema.py` (pattern `test_train_telemetry_schema.py`) | extra key / bad outcome / ES out of [0,1] / NaN / inconsistent confirmed pair -> dropped to None, solve still 200 |
| Stale bundle | old body | router | `test_train.py` | body without `recheck` -> 200, same grading as before |
| D-01/D-08 | anchor = after-key search; played == key no search | hook | `frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts` (MockWorker) | `startGrading(FEN, key)` posts `position fen <afterKeyFen>`; gradeMove(key) sends no second `go`; off-key compares after-key vs after-played ES |
| D-07 | null key -> root search | hook | same | `startGrading(FEN, null)` posts the root FEN (today's behavior) |
| D-09 | clamp to key line; game move == key shortcut | hook | same ("consistent evals & display clamp" describe) | played line eval capped at key line; game move == key resolves without a search |
| D-10 | trigger | unit | new `frontend/src/lib/__tests__/trainRecheck.test.ts` | true only for sharp + key + off-key + off-su + good |
| D-11/D-13/D-16 | re-check | hook | `useTrainGradingEngine.test.ts` | two `go movetime 3000 nodes <recheck cap>`; confirmed -> unclamped played line; resolved -> slow tier; timeout uses recheck constant |
| D-12 | wait copy | component | `TrainSolveScreen.test.tsx` / `trainBubbleState.test.ts` | re-check in flight shows recheck copy testid, not `GRADING_COPY` |
| D-15 | prose | unit | `TrainReveal.test.tsx` `describe('guessFeedbackProse')` (:1745) | disagreement -> exact "Qh4 is the engine's first choice, but your move holds up too." for both guesses; six existing strings unchanged |
| D-09 | arrow names key | component | `TrainReveal.test.tsx` / `trainArrows.test.ts` | best arrow/box UCI = key when phone search would prefer another move |
| manual | user-28 repro | headless | `node temp/phase235/probe_budget.mjs` or `frontend/scripts/measure-train-movetime.mjs --fens=...` | documents depth/ES at both budgets |

Mutation discipline (memory `feedback_mutation_test_gap_closures`): for D-14 sanity checks and the omit-when-absent write, prove each test by reverting the check and watching it fail.

### Sampling Rate
- **Per task commit:** the touched file's test module (serial, single file).
- **Per wave merge:** `uv run pytest tests/routers/test_train.py tests/repositories/test_train_repository.py tests/services/test_train_pool.py tests/schemas -n auto` + `cd frontend && npm test -- --run`.
- **Phase gate:** full pre-merge gate (CLAUDE.md) green before `/gsd-verify-work`; memory says run the full serial suite once before a release.

### Wave 0 Gaps
- [ ] `tests/schemas/test_train_recheck_schema.py` — D-18 validation
- [ ] `frontend/src/lib/__tests__/trainRecheck.test.ts` — D-10 trigger
- [ ] optional `tests/schemas/test_train_recheck_parity.py` — only if TS mirrors caps

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no change | FastAPI-Users `current_active_user` |
| V4 Access Control | yes | key query and solve stay scoped by `user_id` from `current_active_user` (IDOR guard); herring pool is identity-blind by design |
| V5 Input Validation | yes | `SolveRecheck` Pydantic, `extra="forbid"`, typed/capped, wrap-validator drop |
| V6 Cryptography | no | — |
| V11 Business Logic | yes | D-14 accepts a client claim after server-side sanity checks |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Forged "confirmed" claim to earn the guess point on sharp puzzles | Tampering | Server sanity checks (live sharp type, off-key, off-su, good tier, internally consistent ES pair); every claim stored for audit. Residual accepted by owner (D-05: cheating not a concern; `move_quality` already client-asserted) |
| Key visible pre-attempt in devtools | Information disclosure | Accepted (D-05); UI never renders key/type pre-attempt (verify no pre-attempt render path reads the new fields) |
| Oversized/malformed recheck JSON | DoS / Tampering | bounded fields, extra forbid, drop to None |
| JSON-null write breaking `IS NULL` queries | Integrity | omit the column when absent |

## Sources

### Primary (HIGH confidence, read this session)
- `app/schemas/train.py`, `app/routers/train.py`, `app/repositories/train_repository.py` (composition, resume, solve, override), `app/services/train_pool.py`, `app/services/sharp_filler.py`, `app/data/sharp_filler_puzzles.csv`, `scripts/gen_sharp_filler_set.py`, `app/models/drill_solve.py`, `app/models/herring_pool.py`, `app/models/game_flaw.py`, `app/models/game_position.py`, `app/services/flaws_service.py`, `app/repositories/train_leaderboard_repository.py`, Alembic migrations `a7c3e9d41f02`, `f4b9d2c7e815`
- `frontend/src/hooks/useTrainGradingEngine.ts`, `frontend/src/components/train/TrainSolveScreen.tsx`, `TrainReveal.tsx`, `frontend/src/lib/trainArrows.ts`, `trainGuessLabels.ts`, `trainBotCopy.ts`, `trainRevealCache.ts`, `frontend/src/types/train.ts`, `frontend/src/hooks/useTrainFreePlay.ts`, `frontend/scripts/measure-train-movetime.mjs`
- Tests: `tests/routers/test_train.py`, `tests/repositories/test_train_repository.py`, `tests/schemas/test_train_telemetry_*.py`, `frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts`
- Headless SF18 lite WASM probe run this session (output pasted in Pitfall 1)

### Secondary / Tertiary
- None. No external documentation was needed (no new libraries).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new packages.
- Architecture: HIGH, every seam located by file:line; anchor design keeps downstream consumers unchanged.
- Pitfalls: HIGH for node cap and `su` (measured), MEDIUM for device-speed generalization (A1).

**Research date:** 2026-10-07
**Valid until:** 2026-11-06 (internal code; re-check line numbers if Phase 233/234 follow-ups land first)
