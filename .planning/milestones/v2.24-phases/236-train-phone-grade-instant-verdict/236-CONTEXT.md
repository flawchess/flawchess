# Phase 236: Train Phone Grade Record & Instant Server Verdict - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Two go-forward changes to the Train solve path (SEED-193):

1. **Record the phone's grade on every keyed solve** in a new nullable JSONB column
   `drill_solves.phone_grade`, so grading accuracy (phone vs server tier, phone vs depth-18 spot
   check) becomes a query instead of a Stockfish re-run.
2. **Instant verdict for server-graded moves:** when the played move is one the server grades
   itself (soft vetted entries incl. the "best" entry, herring good band, sharp runner-up `su`),
   skip the ~1.5 s phone wait and POST immediately. The phone's after-move search keeps running in
   the background to fill the "Your move" card and to supply the phone reading for part 1, where
   the server's deep tier is free ground truth.

Not a grading change: no new engine search, no scoring effect, no change to `_resolve_grade`'s
decision order, go-forward only (no backfill).

</domain>

<decisions>
## Implementation Decisions

Owner delegated every gray area to Claude ("you decide", 2026-10-08). Decisions below are Claude's,
grounded in ROADMAP Phase 236, SEED-193 and the Phase 235 decisions.

### Locked upstream (ROADMAP Phase 236 + SEED-193; do not re-open)
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

### Record scope and contents
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

### Payload shape and verdict source
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

### Late phone reading (instant path)
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

### Reveal while the background search runs
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and motivation
- `.planning/ROADMAP.md` § "Phase 236" — goal, steps 1-2, non-goals
- `.planning/seeds/SEED-193-record-phone-grade-on-every-train-solve.md` — evidence (2026-10-08
  audit), prod frequency of server-graded moves, breadcrumbs

### Upstream decisions this phase builds on
- `.planning/phases/235-train-grading-server-answer-key/235-CONTEXT.md` — D-05 (key on the wire,
  no pre-attempt display), D-07 (no-key fallback), D-09 (clamp), D-10/D-11 (re-check), D-17/D-18
  (`recheck` JSONB precedent)
- `.planning/phases/233-train-puzzle-timing-telemetry/` — review route, flush on Next/pagehide,
  D-05 (telemetry is never a grading input)

### Code anchors
- `app/schemas/train.py` — `TrainPuzzle` (~34), `SolveRecheck` (~259) + wrap validator on
  `SolveRequest.recheck` (~402), `ReviewTelemetry` (~295), `VettedMove` (~418)
- `app/repositories/train_repository.py` — `_resolve_grade` (~2838), `_override_for_key_move`,
  `record_solve` claim_values (~3326-3365), `merge_solve_telemetry`
- `app/services/train_pool.py` — `ServerGradedMove` (~576), `answer_key_for`
- `app/models/drill_solve.py` — `recheck` / `telemetry` JSONB column precedent
- `app/routers/train.py` — solve route (~141), review route (~201)
- `frontend/src/components/train/TrainSolveScreen.tsx` — `runRecheck` / `gradeAndSolve`
  (~1105-1170), `playedMoveQuality` (~1355)
- `frontend/src/lib/trainRecheck.ts` — `shouldRecheck`, `buildRecheckPayload` (payload builder to
  mirror)
- `frontend/src/hooks/trainGradingSupport.ts` — `GradeResult`, `LastPlayedSearch` / `GradingAnchor`
- `frontend/src/hooks/useTrainGradingEngine.ts` (~669) — played == key short-circuit

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SolveRecheck` + `RecheckExpectedScore` / `RecheckDepth` types and the drop-invalid wrap
  validator: the template for `PhoneGrade`.
- `buildRecheckPayload` (frontend): the template for a `buildPhoneGradePayload`.
- Review route + keepalive flush (Phase 233): the transport for the late reading (D-12).
- `classification.graded_moves` (server): already the exact D-08 set at solve time; composition
  needs the same list.

### Established Patterns
- JSONB columns omitted from the write when absent (never JSON null).
- Server is the only source of `correct_guess`; verdict renders from `trainSession.lastSolveResponse`.
- Solve payload frozen at move time so Retry resends it unchanged.

### Integration Points
- `gradeAndSolve` branches early: played move in the server-graded set means POST now and grade in
  the background; otherwise today's path plus `phone_grade` on the POST.
- `setGradeResult` currently gates the reveal's line cards; on the instant path it lands after the
  verdict.

</code_context>

<specifics>
## Specific Ideas

- Prod frequency (SEED-193, last 30 days): ~17% of SR + herring solves (701 / 4,016) are non-key
  server-graded and are the instant-path population; herrings are the biggest share (37.2%).
- Follow-up outside this phase: rewrite gitignored `temp/grade-audit/` as a query plus a depth-18
  spot check, and re-run the audit on post-Phase-235 solves around 2026-10-22.
- CHANGELOG bullet: faster verdict when the played move is one FlawChess has already graded.

</specifics>

<deferred>
## Deferred Ideas

- Engine/device hint on the record (wasm build, threads, nodes reached). Revisit if depth alone
  cannot separate slow devices from misreads.
- Using the phone-vs-server disagreement on server-graded moves to tune the 1.5 s budget or
  tier-boundary noise handling (needs the data this phase starts collecting).

</deferred>

---

*Phase: 236-train-phone-grade-instant-verdict*
*Context gathered: 2026-10-08*
