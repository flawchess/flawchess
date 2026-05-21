# Phase 91: Two-lane import — defer Stockfish eval to in-process cold drain - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the import pipeline so the hot path (fetch → parse → insert positions → commit) holds no Stockfish work, and a separate in-process `run_eval_drain` coroutine evaluates entry plies in the background. Two concurrent 20k-game imports must complete without OOM-killing Postgres (the 2026-05-20 stress-test failure mode), the user must see opening-explorer / raw endgame WDL / flag-rate / time-per-move stats within seconds of import start, and Stockfish-dependent stats (conversion, recovery, score-gap, time-pressure-vs-performance) must fill in over the following minutes with honest per-metric sample-size labels driven by a `<Cpu />`-iconed header bar + per-metric "based on N of M" caveat.

**In scope:** schema migration + hot-lane refactor (strip stages 3a/4/5 from `_flush_batch`) + cold-lane drain coroutine + `GET /imports/eval-coverage` endpoint + page-level header bar on Endgames + Openings/Stats + `useEvalCoverage()` hook + per-metric pending caveat in `EvalConfidenceTooltip` / `MetricStatPopover` bodies + tests.

**Out of scope:** concurrent-import admission control (SEED-022 option F, deferred), idempotent stream-retry `on_game_fetched` (SEED-022 option A′, `/gsd-fast`), scheduled backend restart cadence (SEED-022 option G, `/gsd-fast`), retroactive re-eval of historical engine-failure rows (operators can run `scripts/backfill_eval.py` manually).

</domain>

<decisions>
## Implementation Decisions

The architecture decisions are locked by **SEED-023** (see `<canonical_refs>` — MUST READ). The four decisions below are the implementation-detail choices delegated to Claude during the discuss session ("I'll let you decide on all points") with reasoning, so the planner can act without re-asking.

### Header Bar — Endpoint + Placement

- **D-01:** New dedicated endpoint `GET /imports/eval-coverage` (authenticated, returns `{pending_count: int, total_count: int, pct_complete: int}` for the authenticated user). NOT extending `GET /imports/active` because (a) that endpoint returns `list[ImportStatusResponse]` — no envelope to attach a sibling field, (b) eval coverage is independent of import job lifecycle (cold lane keeps grinding after the import is `completed`), (c) clean separation makes the polling cadence independent.
- **D-02:** Page-level header rendered at the top of the **Endgames page** and the **Openings → Stats subtab** — the two surfaces where Stockfish-dependent metrics live. Hidden when `pending_count == 0`. NOT in the global topbar (chrome on irrelevant pages like Bookmarks/Library/Import) and NOT on the Import page itself (the existing `ImportProgressBar` already lives there; double-bar is noisy).
- **D-03:** Polling cadence: 10s `staleTime` + 10s `refetchInterval` while `pending_count > 0`. Stops polling at 0 (TanStack Query `refetchInterval: pct === 100 ? false : 10_000`). Same single TanStack Query consumed by both the header bar and the per-metric hook (D-05) so the two surfaces stay in lockstep.
- **D-04:** Copy: `<Cpu /> Stockfish analysis: 87% complete (1,432 games pending)`. Plural-aware on "games". Use the existing `Cpu` lucide icon at `h-3.5 w-3.5` (matches `PositionResultsPanel.tsx:198` and `OpeningFindingCard.tsx:139`).

### Per-Metric Caveat Plumbing

- **D-05:** Centralized hook `useEvalCoverage()` in `frontend/src/hooks/` returning `{pendingCount, totalCount, pct, isPending: pct < 100}`. All Stockfish-dependent components import it. Backed by the same TanStack Query key as the header bar so there's one HTTP call per page regardless of how many metric popovers exist.
- **D-06:** Per-metric caveat is **a one-line addendum inside existing popover bodies** (`EvalConfidenceTooltip`, `MetricStatPopover` call sites with `<Cpu />`). When `isPending` is true: `"Based on currently-evaluated games. {pendingCount} more being analysed — refresh in a few minutes for updated values."` When false: omit the line entirely. NO new popover component family; the caveat is a conditional `<p>` injected into existing bodies.
- **D-07:** Concrete touch sites (planner to enumerate exhaustively from `grep -rn '<Cpu ' frontend/src/`): `EvalConfidenceTooltip.tsx`, `BulletConfidencePopover.tsx`, `PositionResultsPanel.tsx` (Row 3 Eval block), `OpeningFindingCard.tsx`, `EndgameOverallEntryCard.tsx`, `EndgameTimePressureCard.tsx`, `MetricStatPopover` instances with `name` containing "Eval" / "Score Gap" / "Conversion" / "Recovery" / "Achievable Score" / "Endgame Entry Eval". Pending caveat is **always per-user, never per-metric** — it just means "some of your games haven't been Stockfish-analysed yet"; it does not try to per-metric attribute (which would require eval-status flags per ply, not per game — out of scope).

### Migration Backfill Strategy

- **D-08:** Migration sets `evals_completed_at = COALESCE(updated_at, created_at, NOW())` for **all existing rows in `games`**. Assumption: every pre-Phase-91 game has already passed through the in-transaction eval pass, so either (a) its entry plies have populated `eval_cp`/`eval_mate`, or (b) the engine returned `(None, None)` for that entry ply and the row is permanently NULL by design (D-11 path in current `_apply_eval_results`). Re-running case (b) on every backend startup would be unbounded retry against engine errors that won't change without engine config changes — bad pattern.
- **D-09:** Operators who want to retroactively re-eval historical engine-failure rows can run `scripts/backfill_eval.py --db prod` manually (already exists; supports `--db dev|benchmark|prod`). NOT in scope for this phase; ROADMAP scope-out is explicit.
- **D-10:** Backfill timing: the migration runs automatically on backend startup via `deploy/entrypoint.sh`. On prod this means the column is added + backfilled in one transaction during the next deploy. The backfill UPDATE is `UPDATE games SET evals_completed_at = COALESCE(updated_at, created_at, NOW()) WHERE evals_completed_at IS NULL`. At current prod row counts (~150k games estimated) this is a single seq scan + UPDATE — runs in seconds, acceptable.

### Cold-Drain Pick Order

- **D-11:** LIFO ordering: `SELECT id FROM games WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 10`. Reasoning: the user just imported games; those are what they want to see analysed first. With FIFO, a fresh User B import would wait behind any leftover backlog from User A's previous failed import. With LIFO, User B's evals start completing within seconds of their import landing. Same DB cost — B-tree indexes scan in either direction with no penalty. The partial index `WHERE evals_completed_at IS NULL` on `(id)` supports both directions.
- **D-12:** No per-user fairness ordering (e.g., round-robin across users). Acceptable because (a) the cold lane processes ~10 games per ~2-3s wall, so even a 20k-game backlog drains in ~2 hours, (b) once the in-flight imports are caught up, FIFO across remaining users naturally rotates by id, (c) introducing per-user fairness adds query complexity (window functions, distinct-user picks) that earns little until we have >5 concurrent users with pending backlogs — not the current world.
- **D-13:** Cold-drain idle interval `_DRAIN_IDLE_SLEEP_SECONDS = 5`. When `SELECT … LIMIT 10` returns empty, sleep 5s and re-poll. When non-empty, loop immediately. Active drain wakes within 5s of any new pending row — fast enough that the header bar moves visibly even for tiny imports.

### Claude's Discretion (delegated by user)

All four areas above were delegated with "I'll let you decide on all points". Decisions D-01 through D-13 are the locked choices. Planner has flexibility on:
- Exact filename conventions (e.g., `useEvalCoverage.ts` vs `useEvalCoverage/index.ts`) — match existing project convention.
- Exact wording of header-bar copy and per-metric caveat — match project's existing voice (no jargon, no caveats beyond the one functional line per [[popover-copy-minimalism]]).
- Test structure (unit vs integration mix) — match prior import-pipeline phases (Phase 90 used real-DB integration tests for stage 5; same shape applies here).

### Folded Todos
None — todo matches (Phase 70 amendments, recovery popover copy, tailwind axis label) were keyword false positives, not relevant to Phase 91 scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture (the locked design — read first)
- `.planning/seeds/SEED-023-two-lane-import-defer-stockfish.md` — full architectural seed: scope, hot/cold lane shape, schema, UX, acceptance criteria, alternatives rejected.
- `.planning/notes/2026-05-20-import-pipeline-rethink.md` — exploration record: why we pivoted from SEED-022 profiling to direct architectural fix, first-principles reasoning, alternatives considered (Scope B / out-of-process / external queue all rejected with rationale).
- `.planning/seeds/SEED-022-import-concurrency-and-postgres-headroom.md` — superseded but retained: the diagnostic narrative from the 2026-05-20 stress test, anti-claims (no producer-consumer queue, no shared_buffers fix), and OOM mechanism analysis. Useful background for why the rewrite addresses the root cause.
- `.planning/ROADMAP.md` §Phase 91 — scope (in/out), verification criteria, references list.

### Stress test evidence
- `logs/import-stress-20k-each-2026-05-20.log` — 441-line per-30s memory trace of the 2× 20k import that motivated this phase. RSS plateau on backend + monotonic swap climb on host + OOM-kill of Postgres at T+~28min.

### Phase 90 (immediate predecessor)
- `.planning/phases/90-import-pipeline-memory-leak-fix-resilience/` — full directory. Phase 90 established the per-batch session-recycle pattern this phase builds on, plus the resilient failure-recording helper (`_record_failure_with_retry`) and the bound-parameter executemany discipline.

### Project conventions
- `CLAUDE.md` — hard rules: no `asyncio.gather` on same `AsyncSession`, no magic numbers, ty compliance, sentry capture rules, frontend `<Cpu />` icon convention, popover minimum font-size exception, browser automation `data-testid` requirements.
- `.planning/PROJECT.md` — product framing, feature areas, "engines are flawless, humans play FlawChess" tagline (relevant to UX caveat copy honesty).

### User-feedback memories (relevant to UX copy)
- `~/.claude/projects/.../memory/feedback_popover_copy_minimalism.md` — popover prose covers WHAT + sign convention only; trust zone bands for interpretation; no jargon, no caveats beyond what's functional.
- `~/.claude/projects/.../memory/feedback_zone_band_judgement.md` — editorial judgement over IQR for zone bands; not directly applicable here but informs the "no over-engineered statistical disclaimer" instinct for the pending-caveat copy.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`app/services/engine.py` — `EnginePool` + module-level `evaluate()`.** Cold lane reuses the existing module-level pool. No new pool needed. `STOCKFISH_POOL_SIZE=4` on prod (4 vCPUs), `=6` in dev — architecture is pool-size-agnostic. `SCHED_IDLE` preexec already ensures workers yield to live API traffic.
- **`app/services/import_service.py` — `_collect_midgame_eval_targets` + `_collect_endgame_span_eval_targets` + `_split_into_contiguous_islands` + `_island_eval_targets` + `_apply_eval_results` + `_board_at_ply`.** All five helpers extract cleanly into a shared module (suggested: `app/services/eval_drain.py`) consumed by the cold lane. Hot lane no longer calls them.
- **`app/services/import_service.py` — `run_periodic_reaper`.** The pattern for the cold drain. Lifespan-spawned coroutine with `while True: await asyncio.sleep(...); try: ...; except: log+capture` shape. Mirror this for `run_eval_drain`.
- **`app/services/import_service.py` — `_record_failure_with_retry` + `_RETRIABLE_DB_OUTAGE_ERRORS`.** Phase 90 retry-on-DB-recovery helper. Cold drain's UPDATE batch should use the same pattern so a Postgres restart mid-cold-batch doesn't strand work (drain just keeps going; idempotent re-pick handles the rest).
- **`frontend/src/components/insights/EvalConfidenceTooltip.tsx` + `MetricStatPopover.tsx` + `BulletConfidencePopover.tsx`.** Existing popover family. Per-metric caveat slots in as a conditional `<p>` in their bodies.
- **`frontend/src/components/charts/PositionResultsPanel.tsx:198` + `OpeningFindingCard.tsx:139`.** Canonical `<Cpu className="h-3.5 w-3.5" />` icon usage. Header bar matches this sizing.
- **`frontend/src/hooks/useCachedEndgameInsights.ts` (or similar).** Pattern for TanStack Query hooks — `staleTime`, `refetchInterval`, returning typed result. Mirror for `useEvalCoverage`.
- **`scripts/backfill_eval.py`.** Already supports per-ply eval backfill with `--db dev|benchmark|prod`. Reused for D-09 manual operator path.

### Established Patterns

- **Per-batch session lifecycle (Phase 90 / WR-01).** `_flush_batch_with_progress` opens, commits, releases a fresh `AsyncSession` per batch. The cold drain does the same per its 10-game batch.
- **Bound-parameter executemany (Phase 90 / WR-05).** Stage 5 `UPDATE Game` uses `bindparam('b_id')` + `executemany` to avoid unique-SQL leak. Cold lane's bulk `UPDATE GamePosition` for evals + `UPDATE games SET evals_completed_at` should use the same discipline.
- **Cancellation contract (Phase 90 / WR-07).** `_record_failure_with_retry` propagates `asyncio.CancelledError` without retry. Cold drain's main loop must do the same on lifespan shutdown.
- **TanStack Query global error handling.** Per `CLAUDE.md`, `QueryCache.onError` / `MutationCache.onError` in `lib/queryClient.ts` already capture errors to Sentry. The `useEvalCoverage` hook should NOT duplicate this.
- **`data-testid` on every interactive element** + **semantic HTML** (per CLAUDE.md Browser Automation Rules). Header bar needs `data-testid="eval-coverage-header"` and is a `<div role="status">` (live region, screen-reader-friendly for the % updates).
- **Minimum font size `text-sm`** (per CLAUDE.md frontend section) — except hover/tap popover bodies which may use `text-xs`. Header bar uses `text-sm` (primary content); per-metric caveat lines inside popovers may use `text-xs` (popover exception).

### Integration Points

- **`app/main.py` lifespan.** Add `run_eval_drain` task spawn alongside the existing `run_periodic_reaper` spawn. Same cancel-and-await shutdown pattern.
- **Alembic migration.** New `evals_completed_at TIMESTAMPTZ NULL` column + partial index + backfill UPDATE in a single migration revision.
- **`app/routers/imports.py`.** New `GET /imports/eval-coverage` endpoint. Uses existing `current_active_user` dependency + `get_async_session`. Returns a new Pydantic `EvalCoverageResponse` schema.
- **`app/services/import_service.py` `_flush_batch`.** Strip stages 3a (target collection), 4 (`asyncio.gather` over `engine.evaluate`), and the per-target `UPDATE GamePosition` in `_apply_eval_results`. Add per-game evaluation of "are all entry plies already lichess-`%eval`-covered? AND are there any entry plies at all?" — if yes (covered or no entries), set `evals_completed_at = NOW()` in the bulk UPDATE; else leave NULL. The "no entry plies" branch matters for very short games that never reach midgame entry or endgame.
- **Frontend layout.** Header bar mounts at the top of `Endgames.tsx` and the Stats subtab of `Openings.tsx`. Conditional render driven by `useEvalCoverage().pendingCount > 0`.

</code_context>

<specifics>
## Specific Ideas

- **Header copy uses the exact `<Cpu />` icon already established in `PositionResultsPanel.tsx` Row 3 Eval block** so the visual association is immediate ("the same icon I see on the Eval row").
- **User-stated UX expectation (from /gsd-explore):** "We mark every stockfish based metric with a CPU lucide icon. if we have a small header with the same Cpu icon saying 'x% games Stockfish analysis complete' or similar, it should work fine". The header bar copy in D-04 honours this verbatim shape.
- **User-stated parallelism expectation:** "it's important to start in parallel, a short delay is ok". D-13's 5s idle sleep + LIFO ordering (D-11) ensures the header bar moves within seconds of import start, not minutes.
- **Batch-size discipline (from /gsd-explore):** ~10 games per cold-lane transaction is the sweet spot — big enough to amortise commit overhead (~10-15ms fsync), small enough that transactions never approach the 30s held-tx shape that killed the stress test. Constant lives in one place for tuning. Wall-time target per batch: 2-4 seconds total (gather outside session), tx hold time <100ms (UPDATEs only).
- **"Gather outside the session" discipline.** Non-negotiable per the architectural fix. Cold drain pseudocode:
  ```python
  ids = await pick_pending_game_ids(limit=10)        # short tx, then close
  targets = collect_eval_targets(ids)                # no session, CPU only
  results = await asyncio.gather(*[engine.evaluate(t.board) for t in targets])
  async with async_session_maker() as session:       # session opened LATE
      await apply_updates(session, targets, results)
      await session.commit()                          # closed FAST
  ```

</specifics>

<deferred>
## Deferred Ideas

- **Concurrent-import admission control (SEED-022 option F).** Hot-lane batches become I/O-light; this becomes optional. Revisit if production traffic surfaces a separate bottleneck.
- **Scheduled backend restart cadence (SEED-022 option G).** Independent operational hardening; ship via `/gsd-fast` any time.
- **Idempotent `on_game_fetched` for lichess stream-retry (SEED-022 option A′).** UX-correctness fix for the misleading `fetched > imported` discrepancy; ship via `/gsd-fast` any time.
- **Per-user fairness in cold-lane pick order.** Strict id-LIFO is fine at current concurrent-user counts. Introduce round-robin or per-user picks only if real production traffic shows a single user's backlog starving newcomers.
- **Per-ply (not per-game) eval pending state.** Would let us per-metric attribute "X% of conversion-rate-eligible games are evaluated" vs "X% of recovery-rate-eligible games". Adds schema complexity (per-ply flag or per-metric pending count) for marginal UX value. Defer indefinitely unless users complain.
- **Retroactive re-eval of historical engine-failure rows.** Operators can run `scripts/backfill_eval.py` manually if needed. Automated retry-on-failure column would need to track retry counts to avoid unbounded retry against permanently-failing positions — out of scope.

### Reviewed Todos (not folded)
- Phase 70 REQUIREMENTS amendments — keyword false positive (matched on "phase" + "planning" tokens). Not Phase 91 scope.
- Recovery Score Gap popover copy reframe — keyword false positive (matched on "score" + "frontend" + "recovery"). Out of Phase 91 scope.
- WR-01 pt-33 Tailwind axis label — keyword false positive. Unrelated.

</deferred>

---

*Phase: 91-Two-lane import — defer Stockfish eval to in-process cold drain*
*Context gathered: 2026-05-20*
