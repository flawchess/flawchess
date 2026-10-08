# Phase 236: Train Phone Grade Record & Instant Server Verdict - Research

**Researched:** 2026-10-08
**Domain:** In-repo Train grading pipeline (FastAPI + SQLAlchemy JSONB column, React solve loop, single-Worker Stockfish WASM grading engine)
**Confidence:** HIGH for the code paths (every claim below was read this session); MEDIUM for the engine-contention magnitude on real phones (not measured)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Owner delegated every gray area to Claude ("you decide", 2026-10-08). Decisions below are Claude's,
grounded in ROADMAP Phase 236, SEED-193 and the Phase 235 decisions.

#### Locked upstream (ROADMAP Phase 236 + SEED-193; do not re-open)
- **D-01:** `phone_grade` record mirrors `SolveRecheck`: `v`, `tier`, `key_es`, `played_es`,
  `key_depth`, `played_depth`, validated with `extra="forbid"`, reusing the `RecheckExpectedScore` /
  `RecheckDepth` value types. Stored in a new nullable JSONB column on `drill_solves`; omit the
  column from the write when absent so it stays SQL NULL (memory
  `project_asyncpg_jsonb_null_vs_sql_null`). A malformed record is dropped to None and never costs
  the solve (same wrap-validator pattern as `recheck`).
  — **Reversibility:** costly — Alembic migration adding a column; dropping it later loses the
  collected accuracy data.
- **D-02:** `move_quality` stays the effective tier after `_resolve_grade`. The override rate is a
  column compare (`phone_grade->>'tier'` vs `move_quality`).
- **D-03:** The server-graded moves go into the pre-attempt `TrainPuzzle` payload and are read only
  after the move, never displayed before the attempt (Phase 235 D-05 rule; the key is already on the
  wire, so nothing new is exposed). Covers fresh and resumed sessions, like Phase 235's key.
  — **Reversibility:** costly — a published API contract field; the instant path is built on it.

#### Record scope and contents
- **D-04:** `phone_grade` always holds the **1.5 s reading** (the first key/played after-move pair
  and the tier it classifies to), never the re-check's 3 s reading. When a re-check ran, the 3 s
  numbers stay in `drill_solves.recheck` (which repeats the 1.5 s pair; that duplication is
  accepted). One meaning per column keeps the audit query simple: phone_grade = what the phone
  concluded at the standard budget.
- **D-05:** Played == key: still write a record, with `tier = "good"` and the played fields equal to
  the key fields (the played move's after-move search IS the think-time after-key search). This
  keeps "every keyed solve has a record" true, so `phone_grade IS NULL` only means legacy/no-key,
  old bundle, or search failure. It also records the think-time key depth for free. Accuracy
  queries must filter `played_move != key` (documented on the model). If the after-key search never
  completed, omit the record.
- **D-06:** Legacy no-key path (Phase 235 D-07, ~0.4% of SR items): no record. Its `esBefore` is a
  root search, a different quantity; mixing it in would pollute the column.
- **D-07:** No device/engine hint in this phase. Search depth reached already measures a slow device
  directly, and `telemetry.client` gives mobile vs desktop. (Deferred.)

#### Payload shape and verdict source
- **D-08:** `TrainPuzzle` carries the server-graded set as a list of `{uci, tier}` entries,
  composed from the same `answer_key_for` / classification path as the key (vetted entries incl.
  the soft "best" entry, the sharp runner-up when present, herring ladder good band). Empty for
  sharp fillers and the no-key path. It is a new field; `runner_up_uci` stays (the re-check trigger
  still reads it).
- **D-09:** The instant verdict renders from the **SolveResponse**, as every verdict does today
  (server truth for `correct_guess`, points and the graded ES pair; POOL-10 stays). The wait drops
  from ~1.5 s + RTT to RTT. The payload tier is NOT rendered; its one job is D-10.
- **D-10:** On the instant path the client asserts `move_quality = <payload tier>` in the solve
  POST (it has no phone tier yet). Normally `_resolve_grade` path 1 overrides it with the live tier
  anyway; if the live classification at solve time no longer contains the move (blob changed between
  composition and solve), path 3 records the composition-time server tier instead of a guess. That
  fallback is why the tier travels with the UCI.
- **D-11:** Server-graded moves are never re-checked. `shouldRecheck` must also exclude every move
  in the D-08 set, not only `su`. Today a soft vetted move the phone rates "inaccuracy" triggers the
  3 s + 3 s re-check (quick 261008-ob1) for a grade the server then discards; that ~6 s wait goes
  away.

#### Late phone reading (instant path)
- **D-12:** The background reading finishes after the instant POST, so for server-graded moves
  `phone_grade` travels on the existing **review route**
  (`POST /train/sessions/{id}/solves/{position}/review`, Phase 233), which already flushes on Next
  and on pagehide via keepalive fetch. It goes as its own validated field next to the telemetry, and
  is written to the `phone_grade` column, never merged into `telemetry` (Phase 233 D-05 keeps
  telemetry out of grading inputs, and this keeps the two concerns separate). Write-once: a later
  flush never overwrites an existing `phone_grade`. If the search has not finished at flush time,
  send nothing for it. Rejected: holding the POST until the search ends (the verdict needs
  server-only `correct_guess`), and a new dedicated endpoint (more surface for the same job).
- **D-13:** Every other keyed solve (phone-graded moves, played == key) sends `phone_grade` on the
  solve POST, frozen with the rest of the payload so `retrySolve` resends it unchanged. The review
  route never writes it for those (write-once also covers that).
  — **Reversibility:** reversible — two write paths for one column, both additive.

#### Reveal while the background search runs
- **D-14:** The reveal shows as soon as the SolveResponse lands. The verdict, score and board badge
  (already derived from `graded_es_before/after` for server-graded moves) need no phone data. The
  "Your move" card shows a compact loading state in place of its line/eval and fills in when the
  search completes. The key line comes from the think-time after-key search; if that is also still
  running when the user moves fast, the solution card uses the same loading treatment.
- **D-15:** If the background search times out or errors: no `phone_grade` record, the "Your move"
  card shows the played move without a line/eval, and there is no engine-error state blocking the
  reveal. The verdict is already server-final.
- **D-16:** Display numbers are unchanged: the played line eval is still clamped to the key line
  (Phase 235 D-09), and the badge follows the server pair as today (Phase 211). No "Checking your
  move…" copy on the instant path.

### Claude's Discretion
- Field names (`server_graded_moves` or similar on `TrainPuzzle`, `phone_grade` column), the
  `PHONE_GRADE_SCHEMA_VERSION` constant, and the exact review-body shape (optional field on the
  review request vs wrapping `ReviewTelemetry`). Keep `ReviewTelemetry`'s own schema and semantics
  intact.
- How write-once is enforced on the review route (e.g. a `phone_grade IS NULL` guard in the
  UPDATE).
- The loading-state visual for the line cards (reuse an existing skeleton or spinner).
- How the background search coexists with reveal-time engine users (free play, eval bar,
  walkthrough): research must check engine contention and whether the background search needs
  priority or a queue slot.
- Stale-bundle behavior: an old client ignores the new `TrainPuzzle` field and sends no
  `phone_grade`; the server accepts both routes without it.

### Deferred Ideas (OUT OF SCOPE)
- Engine/device hint on the record (wasm build, threads, nodes reached). Revisit if depth alone
  cannot separate slow devices from misreads.
- Using the phone-vs-server disagreement on server-graded moves to tune the 1.5 s budget or
  tier-boundary noise handling (needs the data this phase starts collecting).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are registered for Phase 236 (ROADMAP: TBD). CONTEXT decisions D-01..D-16 are the contract; the planner should map plans to them.

| Decision | Research support |
|----------|------------------|
| D-01/D-02 | `SolveRecheck` + `RecheckExpectedScore`/`RecheckDepth` template (§Code Examples 1), JSONB omit-when-absent (§Pattern 4) |
| D-03/D-08 | Composition path `_answer_keys_by_position` + new shared pure function (§Pattern 1); legality filter; herring `mover_color` must be added to the select (Pitfall 3) |
| D-04/D-05/D-06 | `GradeResult` needs a `phoneReading` (keyed path only); depths live in `anchor.depth` and the after-played `RawSearchResult.depth` (§Pattern 3) |
| D-09/D-10 | `_resolve_grade` paths 1 and 3 confirmed (§Open question 4 answered) |
| D-11 | `shouldRecheck` currently excludes only key and `runnerUpUci` (§Pattern 6) |
| D-12/D-13 | Review route body subclass + coalesce write-once (§Pattern 5); claim-UPDATE write for the POST |
| D-14/D-15/D-16 | Every `gradeResult === null` assumption in TrainSolveScreen/TrainReveal enumerated (Pitfall 5); engine preemption hazard (Pitfall 1) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend: ty zero errors (`uv run ty check app/ tests/ scripts/`), explicit return types, `Literal[...]` never bare `str` for fixed sets, `Sequence[...]` for covariant params, `# ty: ignore[rule]` with reason only where unfixable.
- Nesting depth <= 4 per function, gated by `scripts/check_function_size.py app/ --fail-over-depth 4` (backend) and eslint `max-depth` 4 (frontend). Soft target: ~100 logic lines, cognitive complexity <= 15.
- No magic numbers: `PHONE_GRADE_SCHEMA_VERSION` as a named `Final`, mirrored in the frontend as a named const.
- JSONB/enum rules: no native PG ENUM; JSONB columns use `JSONB(none_as_null=True)` and are OMITTED from writes when absent.
- Comment bug fixes at the fix site.
- Sentry: `capture_exception` in non-trivial router/service excepts; never embed variables in messages. Expected conditions (malformed client record) are not captured.
- Never `asyncio.gather` on one `AsyncSession`.
- Frontend: `npm run build` is the only type check; knip fails on unused exports; `data-testid` on interactive elements and major containers; `text-sm` minimum; theme colors from `theme.ts`; no Prettier (ESLint only); `noUncheckedIndexedAccess`.
- Umami: Train guesses/solves are DB-known, so this phase needs **no** new feature event (the instant path is not a new user action).
- Pre-merge gate before squash-merge (ruff format, ruff check, ty x2, function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip). CHANGELOG `## [Unreleased]` bullet required ("faster verdict when the played move is one FlawChess has already graded").
- GSD: no unplanned features; flag scope drift.
- Memory facts: asyncpg writes Python `None` into JSONB as `null::jsonb` (omit the column); `-n auto` green is not serial-CI green; frontend tests need `npm run build` for type safety.

## Summary

Part 1 (record) is a straightforward copy of the Phase 235 `recheck` plumbing: a `PhoneGrade` Pydantic model with the same value types and drop-invalid wrap validator, a new `JSONB(none_as_null=True)` column added by a metadata-only migration on top of head `c5e8a2d7b914`, and a conditional `claim_values["phone_grade"]` entry in `record_solve`'s claim UPDATE (first write wins via the existing `solved_at IS NULL` guard). The frontend already holds every number before the POST except the depths, which are in the hook's anchor (`anchor.depth`) and the after-played search (`afterRaw.depth`) but are not on `GradeResult`; the hook must surface a `phoneReading` that is non-null only on the keyed path, so legacy (D-06) and defensive fallbacks never produce a record.

Part 2 (instant verdict) has three non-obvious hazards that the planner must design around. (1) **Engine preemption:** the grading engine is one Worker whose `search()` sends `stop` and queues the newer request when busy, and the preempted search's promise is dropped without settling (`pendingRef.current = null` on the stop's bestmove). On the instant path the reveal's "Played in game" search (`startGameMoveSearch`, same Worker) will almost always fire while the background played search is still running, killing it: no `phone_grade`, no "Your move" line, and the background promise only rejects at the 8 s timeout. The background search needs a queue slot, not priority: `startGameMoveSearch` must await the in-flight played search before dispatching. (2) **`gradeResult === null` is assumed impossible after a verdict** in at least six places (line boxes, best arrow, Also-fine filter, badge, Analyze cache, game-move coincidence check). (3) **Stale-closure hazard:** `TrainSolveScreen` is not keyed per puzzle, and the background promise now outlives the reveal, so its late `setGradeResult`/error must be guarded by puzzle identity.

Composition parity (D-08) is achievable with one shared pure function in `train_pool.py` called by both `_answer_keys_by_position` (composition, fresh + resume via the single `_attach_answer_keys` funnel) and the three `_classify_*_solve` functions. Composition currently does not load `HerringPool.mover_color`, which the herring good band needs.

**Primary recommendation:** Build Part 1 first (backend schema/column/claim write, then the hook's `phoneReading` and POST field), then Part 2 as: shared `server_graded_moves_for()` + payload field, hook-level serialization of `startGameMoveSearch` behind the in-flight played search, a `playedGradeStatus` state in `TrainSolveScreen` that drives pending/failed line cards, and the review-route `phone_grade` field with a `coalesce` write-once.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Compose the server-graded set (D-08) | API / Backend (`train_pool` pure fn, repository funnel) | — | Server owns the blob/ladder; must be byte-identical to solve-time `classification.graded_moves` |
| Effective tier, `correct_guess` (D-09/D-10) | API / Backend (`_resolve_grade`) | — | Unchanged; payload tier is only a path-3 fallback assertion |
| Phone 1.5 s reading (ES pair, depths, tier) | Browser (grading Worker hook) | — | Only the phone runs this search |
| Instant-path branch decision | Browser (`TrainSolveScreen.gradeAndSolve`) | — | Reads payload after the move, never before |
| `phone_grade` persistence + write-once | Database (claim UPDATE / coalesce UPDATE) | API (schema validation) | Atomic single-statement guards, no read-modify-write |
| Late reading transport | Browser (telemetry hook keepalive flush) | API (review route) | Reuses Phase 233 flush on Next/pagehide |
| Engine scheduling (background vs reveal search) | Browser (grading hook serialization) | — | One Worker, one cancellation authority (`generationRef`) |

## Standard Stack

No new libraries. Everything uses what the repo already ships.

### Core (existing, versions not changed by this phase)
| Library | Purpose in this phase | Evidence |
|---------|----------------------|----------|
| Pydantic v2 | `PhoneGrade`, wire `ServerGradedMove`, wrap validators | `[VERIFIED: app/schemas/train.py:251-293]` |
| SQLAlchemy 2 async + `postgresql.JSONB` | new column, claim UPDATE, coalesce UPDATE | `[VERIFIED: app/models/drill_solve.py:196-208]` |
| Alembic | add-column migration | `[VERIFIED: alembic heads -> c5e8a2d7b914 (head)]` |
| Vitest + Testing Library | frontend tests (FakeWorker / MockWorker harnesses exist) | `[VERIFIED: frontend/package.json "test": "vitest run"]` |

**Installation:** none.

## Package Legitimacy Audit

This phase installs no external packages. **Packages removed due to [SLOP] verdict:** none. **Packages flagged [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
 compose/resume POST /train/sessions
   └─> _attach_answer_keys (single funnel: fresh, resume, IntegrityError-resume)
         └─> _answer_keys_by_position  (blob, best_move, ladder, + herring mover_color NEW)
               ├─> answer_key_for()            -> key / puzzle_type / runner_up
               └─> server_graded_moves_for()   -> [(uci, tier, es...)]  NEW (shared w/ solve)
         └─> legality filter vs served FEN (key null => set [])
   └─> TrainPuzzle {key_move_uci, puzzle_type, runner_up_uci, server_graded_moves NEW}

 think time:  startGrading(fen, key)  ->  Worker: search AFTER key (1.5 s) -> anchor {es, depth, keyLine}

 user moves (handlePieceDrop -> gradeAndSolve)
   ├─ played != key AND played in server_graded_moves?  ── yes ─> INSTANT PATH
   │     ├─ POST /solve {move_quality: payload tier, telemetry}   (no phone_grade; frozen)
   │     │      └─> record_solve -> _resolve_grade path 1 (live tier) | path 3 (payload tier)
   │     │      └─> SolveResponse -> verdict renders, reveal opens, line cards "pending"
   │     └─ background: gradeMove(fen, played) (awaits anchor, after-played 1.5 s search)
   │            ├─ ok   -> setGradeResult (puzzle-guarded) -> cards fill
   │            │         -> telemetry hook stores phone_grade for this (session, position)
   │            └─ fail -> status "failed" -> card shows move, no line (D-15)
   │     reveal: startGameMoveSearch WAITS for the in-flight played search (no stop/preempt)
   │     Next / pagehide flush -> POST /review {...ReviewTelemetry, phone_grade?}
   │            └─> merge_solve_telemetry: telemetry ||= patch ; phone_grade = coalesce(phone_grade, new)
   │
   └─ no ─> TODAY'S PATH: gradeMove (await) -> [recheck?] -> setGradeResult
             -> POST /solve {move_quality: phone tier, recheck?, phone_grade (1.5 s reading) NEW}
             -> claim UPDATE writes phone_grade once
```

### Recommended file touch list
```
app/schemas/train.py                 PhoneGrade, PHONE_GRADE_SCHEMA_VERSION, wire ServerGradedMove,
                                     TrainPuzzle.server_graded_moves, SolveRequest.phone_grade,
                                     ReviewRequest(ReviewTelemetry) + phone_grade; docstrings
app/services/train_pool.py           server_graded_moves_for() (pure, shared); legality filter helper
app/repositories/train_repository.py ComposedPuzzle field, _answer_keys_by_position (+mover_color),
                                     _attach_answer_keys, _classify_*_solve use the shared fn,
                                     record_solve(phone_grade=...), merge_solve_telemetry(phone_grade=...)
app/models/drill_solve.py            phone_grade column (+ docstring: filter played_move != key)
app/routers/train.py                 map TrainPuzzle field; pass phone_grade on solve; ReviewRequest body
alembic/versions/2026100x_..._drill_solves_phone_grade.py
frontend/src/types/train.ts          ServerGradedMove, PhoneGrade, TrainPuzzle/SolveRequest fields, ReviewRequest
frontend/src/lib/trainRecheck.ts     (or new trainPhoneGrade.ts) buildPhoneGradePayload, instant-tier lookup,
                                     shouldRecheck exclusion
frontend/src/hooks/trainGradingSupport.ts  GradeResult.phoneReading
frontend/src/hooks/useTrainGradingEngine.ts phoneReading, startGameMoveSearch serialization, key-line callback
frontend/src/hooks/useTrainPuzzleTelemetry.ts  per-puzzle phone_grade slot added to both flushes
frontend/src/api/client.ts           postReviewKeepalive body type
frontend/src/components/train/TrainSolveScreen.tsx  instant branch, playedGradeStatus, guards, overlay fallbacks
frontend/src/components/train/TrainReveal.tsx       pending/failed your+best boxes, effect deps
```

### Pattern 1: One shared pure function for the D-08 set (composition == solve)

**What:** Today composition (`_answer_keys_by_position`, train_repository.py:2244-2314) derives only `answer_key_for(...)`, while solve time derives `graded_moves` inside `_classify_sr_solve` (2660-2727) and `_classify_herring_solve` (2584-2637). Fillers have no graded moves (`_classify_filler_solve` returns `vetted_moves=[]` and no `graded_moves`, 2640-2657).

Solve-time SR composition (read this session, train_repository.py:2705-2721):
```python
    vetted_moves = (
        vetted_moves_from_pv_node(missed_pv_lines[0], mover_color, best_uci=best_uci)
        if missed_pv_lines
        else []
    )
    graded_moves = graded_moves_from_vetted(vetted_moves)
    if key.puzzle_type == "sharp" and missed_pv_lines:
        runner_up = sharp_runner_up_graded_move(
            missed_pv_lines[0], mover_color, key_uci=key.key_uci
        )
        if runner_up is not None:
            graded_moves.append(runner_up)
```
Herring: `graded_moves=graded_moves_from_vetted(vetted)` with `vetted = vetted_moves_from_ladder(pool_row.ladder, mover)` and `mover = cast(Literal["white", "black"], pool_row.mover_color)` (train_repository.py:2621-2637).

**Do this:** add to `app/services/train_pool.py`:
```python
def server_graded_moves_for(
    *,
    source: int,
    ply: int,
    missed_pv_lines: list[Any] | None,
    best_move: str | None,
    ladder: list[Any] | None,
    herring_mover_color: Literal["white", "black"] | None,
    key_uci: str | None,
    puzzle_type: TrainPuzzleType,
) -> list[ServerGradedMove]:
    """Every move whose grade the server owns, in first-match order (Phase 236 D-08).

    The single derivation shared by composition (pre-attempt payload) and the
    solve path (`_resolve_grade` path 1), so the two lists are identical for the
    same blob/ladder read. Pure, never raises.
    """
    if source == DrillSource.RED_HERRING:
        if herring_mover_color is None:
            return []
        return graded_moves_from_vetted(vetted_moves_from_ladder(ladder, herring_mover_color))
    if source == DrillSource.SHARP_FILLER or not missed_pv_lines:
        return []
    mover = mover_color_for_ply(ply)
    node = missed_pv_lines[0]
    graded = graded_moves_from_vetted(vetted_moves_from_pv_node(node, mover, best_uci=best_move))
    if puzzle_type == "sharp":
        runner_up = sharp_runner_up_graded_move(node, mover, key_uci=key_uci)
        if runner_up is not None:
            graded.append(runner_up)
    return graded
```
Then make `_classify_sr_solve` / `_classify_herring_solve` call it (keeping `vetted_moves` for display), so a refactor regression is caught by the existing `_resolve_grade`/`record_solve` tests. `[VERIFIED: app/services/train_pool.py:576-638, app/repositories/train_repository.py:2584-2727]`

Composition: add `HerringPool.mover_color` to `_answer_keys_by_position`'s select, call `server_graded_moves_for` with the SAME source gating already used for `answer_key_for` (SR columns only for SR, ladder only for herring, train_repository.py:2299-2312), and in `_attach_answer_keys` drop entries that are illegal in the served FEN, and return `[]` whenever the legal key is `None` (D-08 "empty for the no-key path"). `ComposedPuzzle` is `@dataclass(frozen=True)`, so the new field should be a tuple (`server_graded_moves: tuple[ServerGradedMove, ...] = ()`).

**Wire shape:** only `uci` + `tier` cross the wire (the ES values stay server-side, the same rule `VettedMove` follows). Following the Phase 211 precedent of a same-named wire twin (`app.schemas.train.VettedMove` vs `app.services.train_pool.VettedMove`), add `class ServerGradedMove(BaseModel): uci: str; tier: Literal["good", "inaccuracy", "wrong"]` to the schemas module, and `server_graded_moves: list[ServerGradedMove] = Field(default_factory=list)` on `TrainPuzzle`. The `tier` literal matches the domain dataclass verbatim: `tier: Literal["good", "inaccuracy", "wrong"]` `[VERIFIED: app/services/train_pool.py:587-588]`, which is also exactly `SolveRequest.move_quality`'s type, so the client can assert it unchanged (D-10).

What the set contains per source (derived from the code above):
| Puzzle | Set content | Includes key? |
|--------|-------------|---------------|
| SR soft, best_move known | `[best(key) -> "good", su -> "good"/"inaccuracy"]`, or `[best]` alone when `su` fails the band | yes |
| SR soft, best_move unknown | key is None -> no-key path -> `[]` (D-08) | n/a |
| SR sharp | `[su -> tier from b/s gap, in practice "wrong"]` (vetted is empty on sharp nodes) | no |
| Herring | good-band ladder entries; `ladder[0]` is the key | yes |
| Sharp filler | `[]` | no |

### Pattern 2: Instant-path branch (client)

```typescript
// The key is excluded on purpose: played == key keeps today's path and puts its
// D-05 record on the POST (D-13). A null key means the legacy path (no set, D-08).
export function instantServerTier(
  moves: readonly ServerGradedMove[],
  playedUci: string,
  keyUci: string | null,
): TrainMoveTier | null {
  if (keyUci === null || playedUci === keyUci) return null;
  return moves.find((m) => m.uci === playedUci)?.tier ?? null; // first match, like _override_for_key_move
}
```
`gradeAndSolve` branches on it first: instant -> POST now with `move_quality: tier`, `telemetry`, no `phone_grade`, and start `gradeMove` without awaiting it; otherwise today's code plus `phone_grade` built from the 1.5 s reading captured BEFORE `runRecheck` can replace `grade` (D-04).

### Pattern 3: `phoneReading` on `GradeResult` (keyed path only)

`gradeMoveInner` has exactly two keyed exits and three non-record exits:
- played == key (useTrainGradingEngine.ts:669-680): record `{tier: 'good', keyEs: anchor.es, playedEs: anchor.es, keyDepth: anchor.depth, playedDepth: anchor.depth}` (D-05).
- after-played search (689-728): record `{tier: moveTier, keyEs: anchor.es, playedEs: esAfter, keyDepth: anchor.depth, playedDepth: afterRaw.depth}`.
- `phoneReading: null` for: anchor mismatch fallback (652-666, returns a fabricated 0.5 pair), illegal played move fallback (683-695), and any `anchor.legacy === true` anchor (D-06).

Depth convention: `RawSearchResult.depth` is `number | null` (null when no exact line arrived, 0 for a terminal position); `buildRecheckPayload` sends a null depth as 0 (`key_depth: input.keyDepth ?? 0`). Mirror that in `buildPhoneGradePayload`. `[VERIFIED: frontend/src/lib/trainRecheck.ts:79-93, frontend/src/hooks/trainGradingSupport.ts RawSearchResult.depth]`

`GradeResult` is persisted in the Analyze reveal cache (`trainRevealCache.ts:38`, loose shape check at 102-117), so make `phoneReading` optional or tolerate its absence on restore.

### Pattern 4: JSONB omit-when-absent + claim-guarded write-once (POST)

Precedent in `record_solve` (train_repository.py:3355-3375): `claim_values` dict, `if recheck is not None: claim_values["recheck"] = {...}`, then one UPDATE guarded by `DrillSolve.solved_at.is_(None)`. A lost-claim re-submit writes nothing, so first write wins with no extra code. Add `if phone_grade is not None: claim_values["phone_grade"] = phone_grade.model_dump()`. `phone_grade` must NOT be passed into `_resolve_grade` (it is never a grading input; D-02).

### Pattern 5: Review route body and write-once via `coalesce`

Current route (routers/train.py:201-235) takes `body: ReviewTelemetry` and passes `patch=body.model_dump(exclude_none=True)`; the repository does one UPDATE (train_repository.py:3213-3223):
```python
        update(DrillSolve)
        .where(
            DrillSolve.session_id == session_id,
            DrillSolve.position == position,
            DrillSolve.user_id == user_id,
            DrillSolve.solved_at.is_not(None),
        )
        .values(telemetry=_merged_telemetry(patch))
```
and returns `result.rowcount == 1`; the router maps `False` to `404 "Puzzle not found"` (row missing, unsolved or foreign, no existence oracle).

**Body shape (recommended):** a flat subclass, so the wire stays backward compatible and `ReviewTelemetry` itself is untouched:
```python
class ReviewRequest(ReviewTelemetry):
    """Review flush body: the Phase 233 telemetry plus, for a server-graded move,
    the late phone reading (Phase 236 D-12). `phone_grade` is never merged into
    telemetry and never a grading input."""

    phone_grade: PhoneGrade | None = None

    @field_validator("phone_grade", mode="wrap")
    @classmethod
    def _drop_invalid_phone_grade(cls, value: object, handler: ValidatorFunctionWrapHandler) -> PhoneGrade | None:
        try:
            return handler(value)
        except ValidationError:
            return None
```
Pydantic v2 inherits `model_config = ConfigDict(extra="forbid")` from the parent, so unknown keys still 422 (existing `test_review_flush_rejects_bad_body` keeps passing). Router: `patch=body.model_dump(exclude_none=True, exclude={"phone_grade"})`, `phone_grade=body.phone_grade.model_dump() if body.phone_grade is not None else None`. A malformed `phone_grade` drops to None and the telemetry still lands (the drop must not cost the flush, mirroring D-01).

**Write-once:** put it in the SAME UPDATE, only when present:
```python
values: dict[str, Any] = {"telemetry": _merged_telemetry(patch)}
if phone_grade is not None:
    # D-12 write-once: an existing record (POST-time or an earlier flush) wins.
    values["phone_grade"] = func.coalesce(DrillSolve.phone_grade, literal(phone_grade, JSONB))
```
Why `coalesce` and not a `phone_grade IS NULL` WHERE guard: the WHERE guard would make the second flush affect 0 rows, which the route would report as 404 and would also drop that flush's telemetry. `coalesce` keeps one statement, keeps `rowcount == 1` meaning "row found", and is atomic (no read-modify-write). `literal(<dict>, JSONB)` is the same bind pattern `_merged_telemetry` already uses. Because the column is `none_as_null=True` and the expression only runs with a real dict, no JSON null is ever written.

### Pattern 6: `shouldRecheck` exclusion (D-11)

Current rule (trainRecheck.ts:48-56):
```typescript
  const offKey =
    input.keyUci !== null &&
    input.playedUci !== input.keyUci &&
    input.playedUci !== input.runnerUpUci;
```
Add `serverGradedUcis: readonly string[]` to `ShouldRecheckInput` and return false when `playedUci` is in it. In the new flow the instant branch already bypasses `runRecheck`, so this is the pure-rule guarantee (and its test), not the only line of defense. Keep `runnerUpUci` (D-08 says the trigger still reads it).

### Anti-Patterns to Avoid
- **Merging `phone_grade` into `telemetry`:** violates D-12 and Phase 233 D-05. Use `exclude={"phone_grade"}` on the patch dump.
- **Awaiting the background search before the POST:** that is today's path; the point is RTT-only.
- **Computing the D-08 set twice with two code paths:** the payload/solve lists will drift; use the shared function.
- **Rendering the payload tier:** D-09; the verdict renders from `SolveResponse` only.
- **A separate review UPDATE with `phone_grade IS NULL` in WHERE:** turns the second flush into a 404 (see Pattern 5).
- **Adding `phone_grade` to `_resolve_grade`'s inputs:** it is audit data only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Record validation | new clamp/validators | `RecheckExpectedScore`, `RecheckDepth`, wrap validator from `SolveRequest._drop_invalid_recheck` | Already strict (`strict=True`, `allow_inf_nan=False`) and clamp depths to `RECHECK_DEPTH_CAP` |
| Server-graded set | a SQL re-derivation at composition | `vetted_moves_from_pv_node`, `vetted_moves_from_ladder`, `sharp_runner_up_graded_move`, `graded_moves_from_vetted` | Sigmoid/band constants live there; the solve path uses them |
| Legality check | chess.js on the server | `_legal_in(board, uci)` / pattern of `legal_answer_key` (train_pool.py:395-422) | Same parsing and failure semantics as the key |
| Transport for the late reading | new endpoint / beacon | `postReviewKeepalive` + review route | D-12; already handles Next, pagehide, unmount, hidden tab |
| Timeout race | ad-hoc setTimeout | `raceWithTimeout` (trainGradingSupport.ts) | Settles exactly once, aborts the signal |
| Loading visual | new skeleton | the `train-game-line-loading` block (`Loader2` + "Loading…", TrainReveal.tsx:1204-1209) | Same card, same reveal, already styled `text-sm` |

## Common Pitfalls

### Pitfall 1: The reveal's game-move search kills the background grading search
**What goes wrong:** On the instant path the verdict lands after one RTT, `TrainReveal` fetches the reveal GET and calls `startGameMoveSearch` on the SAME grading Worker while the background after-played search (1.5 s) is still running. `search()` then sends `stop` and queues the new dispatch (useTrainGradingEngine.ts:376-387), and the stop's `bestmove` handler discards the in-flight request without settling it (498-517: `pendingRef.current = null;` then dispatches the queued one). The background `gradeMove` promise never resolves; it rejects only when `TRAIN_GRADING_TIMEOUT_MS = 8000` fires. Result: no `phone_grade` (Part 1's best signal lost on exactly these moves) and a failed "Your move" card.
**Why it happens:** Before this phase the reveal could not open until `gradeMove` resolved, so the game search never overlapped grading.
**How to avoid:** Serialize inside the hook. Keep a ref to the in-flight played-search promise (settled-or-not, errors swallowed) set by `gradeMoveInner`, and have `startGameMoveSearch` `await` it before `searchAfterMove`. The game search's own 8 s race still bounds the total (≈1.5 s wait + 1.5 s search). Do not add a priority system: one queue slot is enough because no other caller shares this Worker.
**Warning signs:** In tests with the manually-driven `MockWorker` (useTrainGradingEngine.test.ts:69-86), a `stop` message posted while a played search is in flight.
**Also note:** the free-play engine (`useTrainFreePlay`) and the eval bar (`useStockfishEngine`, TrainSolveScreen.tsx:1332-1336) each own a separate Worker, so they cannot preempt grading; the walkthrough runs no engine. `[VERIFIED: TrainSolveScreen.tsx:826-834 comment "a second, independent engine instance", 1326-1336]`

### Pitfall 2: CPU contention skews the phone reading on the instant path
**What goes wrong:** The eval bar's Worker starts the moment `showResultRow` is true (TrainSolveScreen.tsx:1317-1336) and runs a `movetime 1500` search of the puzzle position, concurrently with the background grading search. Searches are movetime-bounded, so a contended device reaches less depth. The instant-path population is exactly where the server tier is ground truth, so a reading taken under different load than the normal path biases the audit.
**How to avoid (recommended):** gate the eval bar on the background search: `showEvalBar = showResultRow && playedGradeStatus !== 'pending'`. Cost: the bar appears up to ~1.5 s later on ~17% of solves; the verdict is not delayed. The depth recorded on the record still captures residual slowness.
**Confidence:** the contention mechanism is certain; its magnitude on real phones is `[ASSUMED]` (not measured). Planner may accept it instead, but should then say so in the record's docstring.

### Pitfall 3: Composition cannot compute the herring good band without `mover_color`
**What goes wrong:** `_answer_keys_by_position` selects `GameFlaw.missed_pv_lines`, `GamePosition.best_move`, `HerringPool.ladder` but not `HerringPool.mover_color` (train_repository.py:2261-2295). `vetted_moves_from_ladder` requires the STORED mover color, never ply parity (SEED-120 Pitfall 1, train_pool.py:1071-1073).
**How to avoid:** add `HerringPool.mover_color` to the select and pass it only for `RED_HERRING` rows.

### Pitfall 4: Background promise outlives the puzzle (stale closure)
**What goes wrong:** `TrainSolveScreen` is not keyed per puzzle (Train.tsx:241-249 renders one instance with `puzzle={trainSession.currentPuzzle}`), and the puzzle effect only resets state (TrainSolveScreen.tsx:1054-1094). A background `gradeMove` that settles after Next (it will, by the 8 s timeout, since `abortGrading` drops it unsettled) would call `setGradeResult`/set a failed status on the NEXT puzzle, and could stash a `phone_grade` for the wrong position.
**How to avoid:** capture `puzzle.position` (and fen) in the closure and compare against a ref updated by the puzzle effect before any state write; store the late record via a telemetry-hook method that takes `(sessionId, position)` and ignores a mismatch with its own `keyRef`.

### Pitfall 5: Code that assumes a verdict implies `gradeResult !== null`
On the instant path the verdict lands first. Every site below must get a fallback (use `puzzle.key_move_uci` for the best UCI on the keyed path):
| Site | Today | Fix |
|------|-------|-----|
| `buildLineBoxes` (TrainReveal.tsx:268-317) | `your`/`best` roles only when `gradeResult !== null` | add your (played UCI) + best (key) roles with `line: null` and a pending/failed status |
| Line card render (TrainReveal.tsx:1137-1215) | `line === null` means standalone game box | new branch for your/best pending (Loader2 "Loading…") and failed (header only, D-15) |
| Game search effect deps (TrainReveal.tsx:873-904) | depends on the `gradeResult` object | depend on a primitive best UCI; otherwise the game search is re-dispatched when the grade lands |
| `revealOverlay` best arrow + Also-fine filter (TrainSolveScreen.tsx:1383-1399; trainArrows.ts:402 filters `fine.uci !== bestMoveUci`) | `gradeResult?.bestMoveUci ?? null` | fall back to the key, else the key shows as an "Also fine" arrow until the grade lands |
| `playedMoveQuality` (1356-1363) | returns null when `gradeResult === null` | derive from `verdict.graded_es_*` with `isBest = played === key` when present (D-14 badge) |
| `pristineOverlayUcis` (1419-1425) and its comment "A verdict cannot land without a gradeResult" | | include the key; fix the comment |
| `handleAnalyzeClick` (1601-1625) | skips the reveal cache when `gradeResult === null` | accepted residual (Analyze within ~1.5 s also unmounts and kills the search), document it |
| `freePlaySeedEval` (880-892) | null while pending | acceptable: free play searches itself |

### Pitfall 6: Played == key overlaps D-08 and D-13
Soft and herring sets contain the key (soft "best" entry; herring `ladder[0]`). D-13 says played == key sends `phone_grade` on the POST; D-08/D-12 would route a set member to the review flush. Resolve by excluding the key from the instant branch (Pattern 2). Played == key already waits only for the think-time anchor, which has usually settled. See Open Question 1.

### Pitfall 7: "Checking your move…" flashes during the instant POST
`resolveBubbleState` returns `{kind: 'grading'}` whenever `isGrading` is true (trainBubbleState.ts:60-67), which renders `GRADING_COPY`. D-16 forbids that copy on the instant path. Either never set `isGrading` on the instant path (the bubble then keeps the `move` prompt for one RTT), or add an `instant` flag that renders a copy-less spinner. `showResultRow` still works either way because it also requires `verdict !== null || isSolveError`.

### Pitfall 8: A background failure must not trigger the grading-error UI
`gradeAndSolve` sets `gradingError` on a `gradeMove` rejection (TrainSolveScreen.tsx:1131-1140), which hides the result row and shows "your move grading" Retry. On the instant path a rejection is D-15: set the card status to failed only.

### Pitfall 9: The wire key-set contract test
`tests/routers/test_train.py:1145-1155` asserts `set(puzzle.keys()) == {...}` with the current nine keys. Adding the field must update it (do not loosen it to a subset check).

### Pitfall 10: Stale docstrings that now contradict the contract
`app/schemas/train.py` module docstring (lines 1-10) and `VettedMove` ("Never add it to `TrainPuzzle` (P-01)") and `SolveRequest` docstrings describe what is on `TrainPuzzle`. The new wire type is not `VettedMove`, but the docstrings should record D-03 and why it exposes nothing new.

## Code Examples

### 1. `PhoneGrade` (mirrors `SolveRecheck`, values quoted from the source)
Source values: `RECHECK_SCHEMA_VERSION: Final = 1`, `RECHECK_DEPTH_CAP: Final = 255` `[VERIFIED: app/schemas/train.py:175-178]`; `RecheckExpectedScore = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False, strict=True)]` and `RecheckDepth` (`BeforeValidator(_clamp_to(RECHECK_DEPTH_CAP))`, `Field(ge=0, le=RECHECK_DEPTH_CAP, strict=True)`) `[VERIFIED: app/schemas/train.py:251-256]`; `model_config = ConfigDict(extra="forbid")` and `v: Literal[1]` `[VERIFIED: app/schemas/train.py:280-283]`.
```python
# Phase 236 (SEED-193, D-01): schema version stamped on the stored record.
PHONE_GRADE_SCHEMA_VERSION: Final = 1


class PhoneGrade(BaseModel):
    """The phone's 1.5 s grading reading for one keyed solve (Phase 236, D-01/D-04).

    Audit data only: never an input to `_resolve_grade`, scoring or the SR ladder
    (D-02). On a played == key solve the played fields equal the key fields (D-05).
    """

    model_config = ConfigDict(extra="forbid")

    # Must equal PHONE_GRADE_SCHEMA_VERSION (a Literal cannot reference the constant).
    v: Literal[1]
    tier: Literal["good", "inaccuracy", "wrong"]
    key_es: RecheckExpectedScore
    played_es: RecheckExpectedScore
    key_depth: RecheckDepth
    played_depth: RecheckDepth
```
Add `phone_grade: PhoneGrade | None = None` to `SolveRequest` with a `_drop_invalid_phone_grade` wrap validator copied from `_drop_invalid_recheck` (app/schemas/train.py:402-415).

### 2. Model column and migration
Model precedent `[VERIFIED: app/models/drill_solve.py:196-208]`: `mapped_column(JSONB(none_as_null=True), nullable=True, default=None)`.
```python
    # Phase 236 (SEED-193, D-01..D-06): the phone's 1.5 s reading (`PhoneGrade`).
    # Audit data, never a grading input. Accuracy queries must filter
    # played_move != key (D-05 records played == key with equal pairs).
    # Written once: by the solve claim UPDATE, or by the review route via
    # coalesce (D-12). none_as_null: SQL NULL when absent, never JSON null.
    phone_grade: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )
```
Migration precedent `[VERIFIED: alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py:26-39]`: `revision: str = 'c5e8a2d7b914'`, `op.add_column('drill_solves', sa.Column('recheck', postgresql.JSONB(none_as_null=True), nullable=True))`. The new file uses `down_revision = 'c5e8a2d7b914'` (current single head, `[VERIFIED: uv run alembic heads -> c5e8a2d7b914 (head)]`) and `op.add_column('drill_solves', sa.Column('phone_grade', postgresql.JSONB(none_as_null=True), nullable=True))`; downgrade drops it. Nullable, no default: metadata-only, instant on prod. No backfill (go-forward only).

### 3. Frontend payload builder (mirrors `buildRecheckPayload`)
Precedent: `const RECHECK_SCHEMA_VERSION = 1 as const;` `[VERIFIED: frontend/src/lib/trainRecheck.ts:18-19]`.
```typescript
/** Mirrors PHONE_GRADE_SCHEMA_VERSION in app/schemas/train.py (the server accepts only this value). */
const PHONE_GRADE_SCHEMA_VERSION = 1 as const;

export interface PhoneReading {
  tier: TrainMoveTier;
  keyEs: number;
  playedEs: number;
  keyDepth: number | null;
  playedDepth: number | null;
}

/** A null depth is sent as 0, like buildRecheckPayload. */
export function buildPhoneGradePayload(r: PhoneReading): PhoneGrade {
  return {
    v: PHONE_GRADE_SCHEMA_VERSION,
    tier: r.tier,
    key_es: r.keyEs,
    played_es: r.playedEs,
    key_depth: r.keyDepth ?? 0,
    played_depth: r.playedDepth ?? 0,
  };
}
```
If the planner wants a parity guard like `tests/schemas/test_train_telemetry_parity.py`, note that test parses `export const NAME = <digits>;` by regex; `trainRecheck.ts`'s `RECHECK_SCHEMA_VERSION` is not exported and has no parity test, so matching that precedent (no parity test) is acceptable.

### 4. Hook serialization for the reveal search (sketch)
```typescript
/** The in-flight after-played search of the current generation, or a resolved
 * promise. startGameMoveSearch waits on it so it never stops a grading search
 * (Phase 236: on the instant path the reveal opens before grading finishes). */
const playedSearchSettledRef = useRef<Promise<void>>(Promise.resolve());

// in gradeMoveInner, around the after-played search:
const searchPromise = searchAfterMove(afterFen, generation, TRAIN_GRADING_MOVETIME_MS);
playedSearchSettledRef.current = searchPromise.then(() => undefined, () => undefined);
const afterRaw = await searchPromise;

// in startGameMoveSearch's raced work, before dispatch:
await playedSearchSettledRef.current;
if (generation !== generationRef.current) throw new Error('Reveal search superseded by a newer puzzle');
```
Reset the ref in `startGrading`/`abortGrading`. Note the played-search promise also never settles if a NEW puzzle preempts it, which is fine because the generation check rejects the waiting game search.

### 5. Key line before the played search finishes (D-14)
`gradeMoveInner` awaits `anchorReadyRef.current` before the played search. Expose the settled key line to the instant path with an optional callback (`gradeMove(fen, uci, { onKeyLine })`, called right after the anchor await when the anchor is keyed and matches) or a synchronous `peekKeyLine(fen)` ref read. The callback covers both the usual case (anchor already settled at move time) and the fast mover (key card loads until the anchor settles), which is exactly D-14.

## State of the Art

| Old (Phase 235) | New (Phase 236) | Impact |
|-----------------|-----------------|--------|
| Phone tier discarded unless a re-check ran (`recheck` has zero prod rows) | `phone_grade` on every keyed solve | Accuracy becomes a query |
| ~1.5 s wait (+ up to 6 s re-check) on server-graded moves | RTT only, background search fills cards | ~17% of SR + herring solves faster |
| Soft vetted move read as "inaccuracy" triggers 3 s + 3 s re-check | Never re-checked (D-11) | Removes a ~6 s wait whose result the server discarded |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Concurrent eval-bar search measurably lowers grading depth on phones | Pitfall 2 | If negligible, the eval-bar gate is an unnecessary ≤1.5 s delay of the bar (cheap to remove) |
| A2 | Users rarely press Analyze within ~1.5 s of a server-graded move, so skipping the reveal cache there is acceptable | Pitfall 5 | A restored reveal after a fast Analyze returns to the start screen instead of the reveal |
| A3 | Pydantic v2 subclass inherits `extra="forbid"` from `ReviewTelemetry` | Pattern 5 | Unknown review keys would silently pass; the existing `test_review_flush_rejects_bad_body` catches it immediately |
| A4 | `literal(<dict>, JSONB)` inside `func.coalesce` binds correctly under asyncpg (same bind as `_merged_telemetry`) | Pattern 5 | A failing bind shows up in the first router test |

## Open Questions (RESOLVED)

1. **Played == key on soft/herring: instant path or POST path?** RESOLVED (plan 236-05): POST path; `instantServerTier` returns null when played == key, the key stays in the payload list.
   - What we know: the key is in the D-08 set for soft (best entry) and herring (`ladder[0]`); D-13 names played == key as a POST-path record.
   - Recommendation: exclude the key from the instant branch (`instantServerTier` returns null when played == key). Keep the key in the payload list (D-08 says "incl. the soft best entry"; it is harmless and keeps the list equal to `classification.graded_moves`). The wait for played == key stays the think-time anchor, as today.
2. **Bubble during the instant POST RTT (Pitfall 7).** RESOLVED (plan 236-06): copy-less spinner, implemented as a separate `submitting` bubble state (precedence verdict > grading > submitting) rather than an `instant` flag on the grading state. Recommendation: copy-less spinner via an `instant` flag on the grading bubble state, so the user sees the move was taken; planner's call.
3. **Eval-bar gate (Pitfall 2).** RESOLVED (plan 236-06): gated while the background search is pending (`showEvalBar = showResultRow && instantGrade?.status !== 'pending'`), trade-off documented in the code comment. Recommendation: gate it; document the trade-off in the code comment.
4. **Answered: `_resolve_grade` paths (CONTEXT question 4).** Path 1: `graded = _override_for_key_move(played_move, classification.graded_moves)`; when non-null the recorded tier is `effective_quality=graded.tier` with the server ES pair, discarding the client tier. Path 2 requires a `recheck` (`_disagreement_accepted` returns False when `recheck is None`), so it never fires on the instant path. Path 3: `effective_quality=client_tier`, `graded_es_*` None `[VERIFIED: app/repositories/train_repository.py:2855-2877]`. So on the instant path a move still in the live set gets the live tier (path 1) and a move that dropped out gets the payload tier (path 3), exactly D-10. In the path-3 case `graded_es_*` are null, so the badge falls back to the phone grade when it arrives.
5. **Answered: review route when the row is missing.** `merge_solve_telemetry` returns False for a missing, unsolved or foreign row and the router returns 404 `"Puzzle not found"` (routers/train.py:228-231). The client never flushes before a verdict (`reviewRef` is only set when `hasVerdict`, useTrainPuzzleTelemetry.ts:144-148), so on the instant path the row is always already claimed.
6. **Retry semantics.** The instant POST is frozen without `phone_grade` (`setLastSolvePayload(body)`, `retrySolve` resends it, useTrainSession.ts:313-330), so a retried instant solve still gets its reading via the review flush. The normal-path POST freezes `phone_grade` with the rest (D-13).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev DB (Docker) | backend repo/router tests, migration | ✓ | `flawchess-dev-db-1 Up (healthy)` | — |
| uv | backend tooling | ✓ | 0.10.9 | — |
| Node | frontend build/tests | ✓ | v24.19.0 | — |

No missing dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-xdist locally), Vitest (`vitest run`) |
| Config file | `pyproject.toml` / `tests/conftest.py` (per-session cloned DB from migrated template, auto-refresh on new Alembic head); `frontend/vite.config.ts` test block |
| Quick run command | `uv run pytest tests/schemas/test_train_phone_grade_schema.py tests/services/test_train_pool.py -x` ; `cd frontend && npx vitest run src/lib/__tests__/trainRecheck.test.ts` |
| Full suite command | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Phase Requirements -> Test Map
| Decision | Behavior | Type | Automated Command | File Exists? |
|----------|----------|------|-------------------|-------------|
| D-01 | `PhoneGrade` parses; malformed dropped to None on `SolveRequest` and `ReviewRequest` (telemetry kept); depth clamp; unknown key rejected inside the record | unit | `uv run pytest tests/schemas/test_train_phone_grade_schema.py -x` | ❌ Wave 0 (mirror `test_train_recheck_schema.py`) |
| D-01 | Column SQL NULL when absent (`IS NULL` true, `jsonb_typeof` null), stored dict when present | integration | `uv run pytest tests/routers/test_train.py -k phone_grade -x` | ✅ file, ❌ tests (mirror `_recheck_row` helper, test_train.py:3676-3700) |
| D-02 | A phone tier of "wrong" on a vetted move still records the server tier; `phone_grade.tier` stored verbatim | integration | same | ❌ |
| D-03/D-08 | `server_graded_moves` per source (soft best+su, sharp su "wrong", herring band, filler [], no key []), illegal entries dropped | unit + integration | `uv run pytest tests/services/test_train_pool.py -k server_graded -x`; `uv run pytest tests/repositories/test_train_repository.py -k answer_keys -x` | ✅ files (extend `TestAnswerKeyFor`, `test_compose_attaches_answer_keys_for_every_source` 5390) |
| D-08 parity | Composition list == `_classify_and_certify_solve(...).graded_moves` (uci, tier) for the same row, fresh and resumed | integration | `uv run pytest tests/repositories/test_train_repository.py -k graded_parity -x` | ❌ (key test of the phase) |
| D-08 wire | Key-set contract includes the new field | integration | `uv run pytest tests/routers/test_train.py -k pre_attempt -x` | ✅ update 1145-1155 |
| D-10 | Instant POST asserts payload tier; path 1 overrides; path 3 keeps payload tier when graded list is empty | unit | `uv run pytest tests/repositories/test_train_repository.py -k resolve_grade -x` | ✅ extend (5757) |
| D-12 | Review with `phone_grade` writes the column, not into telemetry; second flush with different record does not overwrite; review on a row with a POST record does not overwrite; stale body without it still 204 | integration | `uv run pytest tests/routers/test_train.py -k review -x` | ✅ extend (3484-3660) |
| D-13 | Resubmit keeps first `phone_grade` (claim guard) | integration | same as D-01 | ❌ (mirror `test_recheck_resubmit_keeps_first_record` 3832) |
| D-04/D-05/D-06 | `phoneReading`: keyed off-key = (anchor es/depth, played es/depth, 1.5 s tier); played == key = equal pairs, tier good; legacy and fallbacks = null | unit (MockWorker) | `cd frontend && npx vitest run src/hooks/__tests__/useTrainGradingEngine.test.ts` | ✅ extend |
| D-04 | POST carries the 1.5 s reading even when a re-check replaced the grade | component | `npx vitest run src/components/train/__tests__/TrainSolveScreen.test.tsx` | ✅ extend (near 721-911) |
| D-11 | `shouldRecheck` false for any set member; a soft vetted "inaccuracy" read posts immediately with no re-check | unit + component | `npx vitest run src/lib/__tests__/trainRecheck.test.ts` | ✅ extend |
| D-09/D-14/D-16 | Instant path: POST before engine finishes (FakeWorker that withholds bestmove), payload tier asserted, no `phone_grade`, verdict renders, no `train-grading-indicator`, your/best cards show loading then fill | component | TrainSolveScreen + TrainReveal tests | ✅ extend |
| D-12 (client) | Late record included in Next and pagehide flushes, absent before the search finishes, reset on puzzle change | unit | `npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts` | ✅ extend |
| D-15 | Background rejection: no record, card shows move without line, no `train-grading-error` | component | TrainSolveScreen tests | ❌ |
| Pitfall 1 | `startGameMoveSearch` waits for the in-flight played search (no `stop` posted), both settle | unit (MockWorker) | useTrainGradingEngine tests | ❌ |
| Pitfall 4 | Background settle after Next does not touch the next puzzle's state | component | TrainSolveScreen tests | ❌ |
| D-13 (client) | `retrySolve` resends identical body incl. `phone_grade` | component | extend test at 911 | ✅ extend |

Manual-only: real-phone timing of the instant path and the eval-bar contention (no hardware in CI); verify in browser UAT on desktop Chrome that the verdict appears in RTT and the Your-move card fills ~1.5 s later.

Mutation check (memory `feedback_mutation_test_gap_closures`): prove the D-08 parity test and the Pitfall 1 serialization test by reverting the fix and watching them fail.

### Sampling Rate
- **Per task commit:** the targeted file(s) above (backend single files serially; frontend single test files).
- **Per wave merge:** `uv run pytest -n auto -x` + `cd frontend && npm run build && npm test -- --run`.
- **Phase gate:** full pre-merge gate (CLAUDE.md) green before `/gsd-verify-work`; also one serial `uv run pytest -x` run of the train test files (memory: serial CI hides isolation bugs).

### Wave 0 Gaps
- [ ] `tests/schemas/test_train_phone_grade_schema.py` — D-01 (copy structure of `test_train_recheck_schema.py`)
- [ ] D-08 composition/solve parity test in `tests/repositories/test_train_repository.py`
- [ ] Frontend fixtures: a `TrainPuzzle` builder with `server_graded_moves`, and a FakeWorker variant that holds `bestmove` until released (TrainSolveScreen.test.tsx FakeWorker currently emits on a microtask)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no change | `current_active_user` (Bearer) on both routes; keepalive fetch already sends Bearer |
| V3 Session Management | no | — |
| V4 Access Control | yes | `user_id` from the auth dependency in every WHERE (claim UPDATE, review UPDATE); 404 for foreign rows (no oracle) |
| V5 Input Validation | yes | Pydantic strict types, `extra="forbid"`, bounded ES [0,1], clamped depth, closed `Literal` tier, drop-invalid wrap validators |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Tampered client sends a fabricated `phone_grade` | Tampering | Own row only; audit data, never a grading/scoring input (assert in a test that it does not change `move_quality`/`correct_guess`) |
| Overwriting an earlier record via repeated flushes | Tampering | Claim guard on POST; `coalesce` on review |
| Pre-attempt exposure of the fine moves | Information disclosure | Accepted by owner (Phase 235 D-05, D-03 here); guess UI must not render the set (component test: no set UCI appears before the move) |
| Oversized/malformed review body | DoS / Tampering | Fixed schema with extra="forbid"; a bad record drops to None |

## Sources

### Primary (HIGH confidence, read this session)
- `app/schemas/train.py` (TrainPuzzle 34-73, recheck constants 173-178, value types 251-256, SolveRecheck 259-292, ReviewTelemetry 295-337, SolveRequest 340-415, VettedMove 418-441, SolveResponse 444-498)
- `app/services/train_pool.py` (classify_puzzle_type 268-314, answer_key_for 363-392, legal_answer_key 395-422, vetted moves 425-573, ServerGradedMove 575-638, vetted_moves_from_ladder 1048-1104)
- `app/repositories/train_repository.py` (ComposedPuzzle 184-210, _answer_keys_by_position 2244-2314, _attach_answer_keys 2317-2345, SolveClassification 2563-2581, classifiers 2584-2748, _resolve_grade 2838-2877, merge_solve_telemetry 3173-3223, record_solve 3226-3490)
- `app/routers/train.py` (compose 75-138, solve 141-198, review 201-234)
- `app/models/drill_solve.py` (telemetry/recheck columns 188-208), `alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py`
- `frontend/src/hooks/useTrainGradingEngine.ts` (search/stop queue 340-388, bestmove handler 495-526, startGrading 597-631, abortGrading 633-643, gradeMoveInner 645-736, recheckMove 750-824, startGameMoveSearch 842-893)
- `frontend/src/hooks/trainGradingSupport.ts`, `frontend/src/lib/trainRecheck.ts`, `frontend/src/hooks/useTrainPuzzleTelemetry.ts`, `frontend/src/lib/trainTelemetry.ts`, `frontend/src/api/client.ts:345-369`, `frontend/src/hooks/useTrainSession.ts:300-335`
- `frontend/src/components/train/TrainSolveScreen.tsx` (state 789-848, puzzle effect 1054-1094, runRecheck/gradeAndSolve 1105-1172, showResultRow/eval bar 1317-1336, badge/overlay 1356-1430, Analyze cache 1601-1625), `TrainReveal.tsx` (buildLineBoxes 268-317, game search 864-904, card render 1137-1215), `trainBubbleState.ts:60-67`, `trainArrows.ts:402`, `pages/Train.tsx:231-250`
- Tests: `tests/routers/test_train.py`, `tests/repositories/test_train_repository.py`, `tests/services/test_train_pool.py`, `tests/schemas/test_train_recheck_schema.py`, frontend `TrainSolveScreen.test.tsx`, `useTrainGradingEngine.test.ts`, `TrainReveal.test.tsx`, `trainRecheck.test.ts`, `useTrainPuzzleTelemetry.test.ts`
- `.planning/phases/236-.../236-CONTEXT.md`, `.planning/phases/235-.../235-CONTEXT.md`, `.planning/seeds/SEED-193-...md`

### Secondary / Tertiary
- None. No external documentation was needed; no web sources used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new is introduced.
- Architecture: HIGH, every integration point was read; the D-08 parity design follows the existing single-derivation precedent.
- Pitfalls: HIGH for preemption, stale closure, null-gradeResult sites and the mover_color gap (all read in code); MEDIUM for contention magnitude (A1).

**Research date:** 2026-10-08
**Valid until:** 2026-11-07 (in-repo code; re-check line numbers if Train grading changes first)
