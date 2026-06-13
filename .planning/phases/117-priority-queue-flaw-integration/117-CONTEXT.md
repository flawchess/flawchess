# Phase 117: Priority Queue + Flaw Integration - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the interim LIFO `id`-DESC full-ply drain pick (D-116-09) with a tiered priority
queue served through a lease/report worker contract, capture engine PVs alongside the
all-ply evals, and flow newly-analyzed games automatically into `game_flaws`.

In scope:
- Tiered priority queue: tier 1 (explicit request) > tier 2 (automatic window) > tier 3
  (idle backlog), with round-robin per-user fairness and time-control-weighted ordering
  within a user (QUEUE-01, QUEUE-02).
- Tier-1 whole-pool fan-out of one game's positions (~10s wall-clock, QUEUE-03).
- Lease/report pluggable-worker contract so a future browser worker is additive
  (QUEUE-06, SEED-012 D-8).
- Idle backlog drain so cores never sit idle; full-DB coverage accrues over time
  (QUEUE-05).
- `best_move` (PV[0]) persisted for every evaluated position; full PV persisted only at
  the position after each flawed move (EVAL-04, extended — see D-117-01/02).
- Automatic `classify_game_flaws` on full-analysis completion, with the oracle count
  columns filled for engine-analyzed games (EVAL-06).
- Guest exclusion from all tiers (QUEUE-08; already live via D-116-10).

NOT in this phase (Phase 118): the user-facing "analyze more" button, auto-window
enqueue on import/activity, coverage indicators, in-flight status UX, and guest
account-promotion messaging. Tier-1/tier-2 enqueue *mechanisms* are built here; their
user-facing *triggers* are 118.

Requirements: EVAL-04, EVAL-06, QUEUE-01, QUEUE-02, QUEUE-03, QUEUE-05, QUEUE-06, QUEUE-08.
</domain>

<decisions>
## Implementation Decisions

### PV persistence (EVAL-04 — extends SEED-012 D-7; amends the requirement)
- **D-117-01 — `best_move` (PV[0]) for EVERY evaluated position, stored as UCI.** New
  column on `game_positions`. Enables the engine-best-move step-through display (Phase
  118) and doubles as "the better move you missed" at flaw plies. Storage ≈ +240 MB at
  full coverage on the 44.4M-row table (~+4% of the 5.5 GB data); **zero extra engine
  compute** (PV falls out of the same 1M-node search that produces `eval_cp`). Opening
  region (`ply ≤ DEDUP_MAX_PLY=20`) rides the existing `full_hash` dedup transplant
  exactly like `eval_cp` — `best_move` is a property of the pre-move position, so it is
  safe to transplant cross-game by `full_hash` under the same gate as the eval.
- **D-117-02 — Full PV only at the position AFTER each flawed move.** Stored as
  space-joined UCI, **capped at ~12 plies** (confirm exact cap against SEED-039's
  motif-line depth). This is the SEED-039 refutation line. The flawed move's own
  pre-move PV is NOT stored — "the move you should have played" is already covered by
  D-117-01's `best_move` at the flaw ply.
- **D-117-03 — Format is UCI, not SAN.** `move_san` stays SAN (played move, for move
  lists); `best_move`/`pv` are UCI because: (1) the engine emits UCI natively
  (`Move.uci()`); (2) board-arrow display needs from/to squares, which UCI gives
  directly; (3) SEED-039's classifier (lichess puzzle-cook model) consumes UCI; (4) PV
  serialization is `" ".join(m.uci() …)` with no board replay. Frontend converts UCI→SAN
  on the fly via chess.js when a text label is wanted (it already reconstructs per-ply
  FENs from the 260607 hover feature).

### Within-tier ordering (QUEUE-02 — refines SEED-012 D-4)
- **D-117-04 — Time-control-weighted, longer first, then recency.** Within a user (tiers
  2 and 3), order classical > rapid > blitz > bullet, then most-recent within each TC.
  Refines D-4's flat "most-recent-game-first" (serious games carry more instructive
  flaws and cleaner tactic motifs). All TCs remain eligible — QUEUE-05's full-DB coverage
  is intact; bullet is simply analyzed last. One `CASE` in the `ORDER BY`. Tier-1 is a
  single explicit game, so ordering is moot there.

### 117↔118 enqueue boundary (QUEUE-03)
- **D-117-05 — Mechanism in 117, user triggers in 118.** Phase 117 builds the full queue
  + lease/report contract + all three tier pick mechanisms. Tier-3 (idle backlog) goes
  live on the 117 deploy, replacing the interim LIFO pick. Tier-1 enqueue exists as a
  service function + a minimal internal/admin trigger (NOT a user-facing endpoint) —
  enough to verify QUEUE-03's ~10s fan-out live on the prod pool. Tier-2 pick logic is
  built and tested against synthetic rows. The user-facing "analyze this game" button,
  auto-window-on-import enqueue, and coverage UX are Phase 118.

### Flaw flow-through (EVAL-06)
- **D-117-06 — New `lichess_evals_at` provenance column on `games`** (nullable timestamp),
  set ONLY when lichess %evals are ingested at import. Durable "these evals are lichess
  post-move %evals" signal, decoupled from the count columns. Lightweight pull-forward of
  the `eval_source` provenance column 116-CONTEXT deferred to "if/when client workers
  land."
- **D-117-07 — Repoint D-116-04 and WR-02 off `white_blunders` onto `lichess_evals_at`.**
  D-116-04 (drain preserve-vs-overwrite): preserve when `lichess_evals_at IS NOT NULL`,
  else overwrite legacy depth-15. WR-02 (dedup source gate): a dedup source must have
  `lichess_evals_at IS NULL` (engine-written, pre-move, transplant-safe), replacing
  `white_blunders IS NULL`.
- **D-117-08 — `classify_game_flaws` fills the oracle count columns** (white/black
  inaccuracies/mistakes/blunders) for engine-analyzed games identically to lichess, so
  the count columns always match `game_flaws` rows and the db-report
  "counts match game_flaws" sanity check holds across both platforms.
- **D-117-09 — `is_analyzed` intentionally becomes "has flaw counts (lichess OR engine)".**
  After D-117-08, `white_blunders IS NOT NULL` is true for engine-analyzed games too —
  the correct denominator for the coverage badge and the you-vs-opponent gate (an
  engine-analyzed chess.com game genuinely IS analyzed). `full_evals_completed_at` remains
  the engine-completion / queue marker; `lichess_evals_at` carries the eval-provenance
  distinction.
- **D-117-10 — One-time backfill** in the migration: set `lichess_evals_at` for every
  existing `white_blunders IS NOT NULL` game (today that population is exactly the
  lichess-analyzed set), capturing historical provenance before engine-filled counts blur
  the `white_blunders` signal.
- **D-117-11 — Cache refresh: per-user, debounced.** On game completion, mark that user's
  flaw-dependent caches dirty and actually invalidate at most once per short window / on
  next user request — avoids an invalidation storm at ~8.4k games/day. Builds on the
  260611-fast import-completion invalidation.
- EVAL-06 timing: `classify_game_flaws` runs automatically when a game's
  `full_evals_completed_at` is set (post-drain), progressively after import. The hot
  import lane and its quick entry-ply pass stay untouched.

### best_move/PV backfill policy (operational — post-117 deploy)
- **D-117-12 — Demand-driven + forward; no mass re-enqueue.** `best_move`/`pv` are search
  outputs that were NOT stored pre-117, so they can only be recovered by re-running the
  1M-node search — the stored `eval_cp` does not help. Two pre-117 populations lack them:
  (a) 116-engine-analyzed games (chess.com + un-analyzed lichess, drained since the 116
  deploy), and (b) lichess-analyzed games (we ingested only the eval numbers, never
  best-move/variation). Policy:
  - Forward: every game analyzed from 117 onward captures `best_move` (all plies) + flaw
    `pv`.
  - Pre-117-analyzed games are NOT mass re-enqueued. They acquire `best_move`/`pv` only
    when re-touched — an explicit tier-1 request re-analyzes and captures, and Phase 118's
    auto-window re-touches recent games. Deep history stays eval-only until requested.
  - **A second completion dimension is needed** so a re-touch knows a game is
    "eval-complete but PV-missing" without looking unanalyzed. Add a parallel marker
    (e.g. `full_pv_completed_at` on `games`, mirroring `full_evals_completed_at` /
    D-116-05), or detect NULL `best_move` on non-terminal plies. The queue/triggers
    re-pick on the PV dimension, not by clearing the eval marker.
  - Re-touch eval semantics: for lichess games, preserve the lichess %eval
    (T-78-17 / `lichess_evals_at`) but keep `best_move`/`pv` from the new search; for
    116-engine games the eval is already parity, so the eval rewrite is a harmless no-op.
    Opening-region `best_move` rides the `full_hash` dedup transplant once any game has it.
  - Phase 118 coverage indicators should reflect PV/best_move availability SEPARATELY from
    eval availability (a game can be eval-complete but best_move-missing).

### Claude's Discretion
- Final column types/encodings: `best_move` recommended `varchar(5)` UCI; `pv` a `Text`
  UCI string (or per-flaw rows). `lichess_evals_at` timestamp vs boolean.
- Jobs/lease table schema + lease/report mechanics: lease TTL, status states,
  requeue-on-expiry — constrained by SEED-012 D-8, otherwise planner/researcher territory.
- Job/lease granularity: game-unit per worker for tiers 2/3; tier-1 position-batch
  fan-out across the pool (D-4 addendum). Exact chunking is implementation detail.
- Round-robin fairness state (tracking the longest-waiting user) implementation.
- `classify_game_flaws` idempotency mechanics (delete-then-insert vs upsert) on
  completion — only newly-analyzed games are classified, so reprocessing should not occur,
  but be defensive.
- The internal tier-1 trigger shape (admin endpoint vs management command vs test hook).
- Exact debounce window and the precise set of flaw-dependent caches to invalidate.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source of truth for this milestone
- `.planning/seeds/SEED-012-client-side-stockfish-tactics.md` §"Amendment (2026-06-12)" —
  locked D-1..D-8. This phase implements **D-4** (tiers/fairness/fan-out granularity),
  **D-7** (PV capture, now EXTENDED by D-117-01/02), **D-8** (lease/report pluggable
  worker). D-5/D-6 (storage/budget) already shipped in Phase 116.
- `.planning/seeds/SEED-039-*.md` — the tactic-motif classifier (lichess puzzle-cook
  reimplementation) that consumes EVAL-04's flaw-adjacent PV. Read to confirm the
  ~12-ply PV cap (D-117-02) covers its motif-line depth needs.
- `.planning/REQUIREMENTS.md` — EVAL-04, EVAL-06, QUEUE-01/02/03/05/06/08 + traceability.
  **NOTE: EVAL-04 wording needs amending** to reflect best_move-for-all (D-117-01).
- `.planning/ROADMAP.md` §"Phase 117" — success criteria + the now-locked Criterion #5
  PV-split amendment (best_move-for-all vs full-PV-near-flaws).

### Prior phase context (locked invariants this phase must respect)
- `.planning/phases/116-all-ply-engine-core/116-CONTEXT.md` — D-116-* decisions. Critical:
  **D-116-04** (preserve-vs-overwrite discriminator, repointed by D-117-07), **D-116-08**
  (the full-ply drain is a SECOND coroutine; 117 swaps only its pick + adds the post-game
  hook), and the deferred items (pool-priority scheduling, window cap, `eval_source`
  provenance — D-117-06 pulls a lightweight version forward).

### Spike findings (measured)
- `.planning/spikes/002-sf-1m-node-latency-prod/` — 0.98 s/position, 6 workers linear,
  API latency unaffected.
- `.planning/spikes/003-catchup-queue-sizing/` — backlog ~558k games, ~66-day tier-3
  drain at 6 workers; tier-1 fan-out ≈ 10s; w200 ≈ 0.9 days, w500 ≈ 2.1 days.

### Code being extended
- `app/services/eval_drain.py` — full-ply drain (D-116-08 coroutine). `_fetch_dedup_evals`
  carries the WR-02 gate (repointed by D-117-07) and must also transplant `best_move`
  (D-117-01). The interim LIFO pick is what the queue replaces.
- `app/services/engine.py` — `EnginePool`; `analyse()` returns the PV alongside the score
  (no extra search). Fan-out / lease hook. UCI options centralized here (ENG-03).
- `app/models/game.py` — `is_analyzed` hybrid (`game.py:167-184`), the oracle count
  columns (`white/black_inaccuracies/mistakes/blunders`, `134-139`),
  `full_evals_completed_at` (`158`); `lichess_evals_at` is the NEW column site.
- `app/models/game_position.py` — `eval_cp`/`eval_mate`, the `full_hash` dedup index
  (`ply ≤ 20`); `best_move` + flaw-`pv` are NEW columns.
- `classify_game_flaws` (game-flaws classifier service) — the post-completion hook
  (EVAL-06); must fill oracle columns (D-117-08).
- db-report skill (`reports/db-stats/`) — the "counts match game_flaws" sanity check to
  keep green across platforms after D-117-08.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Full-ply drain skeleton (`eval_drain.py`): pick → load PGNs → collect targets → gather
  outside session → short write tx → mark. 117 swaps the pick for the queue lease and
  adds a post-game classify + PV write.
- `EnginePool.analyse()` already returns the PV — `best_move` and the flaw PV are free.
- `_fetch_dedup_evals` opening-region transplant — extend to carry `best_move`.
- Partial-index marker pattern (`ix_games_user_evals_pending`) for queue pick predicates.
- `classify_game_flaws` — existing classifier; wire as the completion hook.
- 260611-fast cache-invalidation hooks (library-* caches) — extend per D-117-11.

### Established Patterns
- AsyncSession never shared across coroutines; `asyncio.gather` only outside session
  scope (CLAUDE.md hard rule).
- Short write transactions; D-09 failure semantics ((None,None) → NULL row + marker +
  Sentry, no retry).
- T-78-17: lichess %evals never overwritten (now gated on `lichess_evals_at`).
- UCI options live only in `engine.py` (ENG-03).
- Sentry: no variables in messages; context/tags for game_id/ply/source.

### Integration Points
- Drain pick → queue lease/report contract; the post-game hook point (classify + PV +
  cache invalidation) must stay cleanly separable from the pick (116-CONTEXT guidance).
- New `game_positions` columns: `best_move`, flaw `pv`. New `games` column:
  `lichess_evals_at`. Migration + backfill (D-117-10).
- Internal tier-1 trigger wired to exercise fan-out (QUEUE-03) without a user endpoint.
- The new drain coroutine already runs in `app/main.py` lifespan (116); 117 changes its
  pick and post-game hook only.
</code_context>

<specifics>
## Specific Ideas

- Lichess "Request a computer analysis" ~10–30s game-review UX is the tier-1 fan-out
  reference (~10s measured, beats it). Same 1M-node budget so users can cross-check.
- The best_move step-through display is expected to render as a board arrow (from→to) —
  the reason UCI (coordinate) beats SAN for these columns.
- SEED-039 motif tagging follows the lichess puzzle-cook model: the motif is read off the
  refutation line from the position AFTER the blunder — hence full PV only there (D-117-02).
</specifics>

<deferred>
## Deferred Ideas

- User-facing "analyze more" button, auto-window-on-import / on-activity enqueue, coverage
  indicators, in-flight status — **Phase 118** (EVAL/QUEUE demand-UX requirements).
- Guest account-promotion UX (the QUEUE-08 "unlock" messaging) — **Phase 118**.
- Full multi-source `eval_source` provenance column for client/browser workers — SEED-012
  D-8 phase 2; D-117-06 pulls forward only the lichess-vs-engine distinction needed now.
- Pool-priority (tier-aware `EnginePool` scheduling) — only if the gate-between-games
  policy proves too coarse (116-CONTEXT deferred).

### Reviewed Todos (not folded)
- `2026-04-26-phase-70-requirements-roadmap-amendments` — keyword false-positive (planning
  amendments for a different phase); not in 117 scope.
- `2026-03-11-bitboard-storage-for-partial-position-queries` — long-range DB idea;
  unrelated to the queue/flaw work.
- `2026-04-30-benchmark-rebuild-per-tc-selection` / `-benchmark-skill-v2-build` — benchmark
  infra; unrelated.

</deferred>

---

*Phase: 117-Priority Queue + Flaw Integration*
*Context gathered: 2026-06-13*
