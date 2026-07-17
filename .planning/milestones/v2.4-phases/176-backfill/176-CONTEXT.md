# Phase 176: Backfill - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Give the **already-analyzed corpus** `game_best_moves` rows opportunistically, so
historical games gradually become eligible for gem/great markers (Phase 175) and
the has-gem/has-great filter (FILT-01). A new tier-4-style ES weighted lottery
periodically selects an engine-analyzed game that has never been through the
Phase 174 best-move pass and drains it through the existing full multipv=2 + Maia
pipeline. Per-game self-terminating, no operator-run script, no ETA/completion
promise. Coverage grows over time (SC3).

**In scope (Phase 176 only):**
- A new `best_moves_completed_at` completion marker on `games` + migration
  (D-01, D-04).
- A new **backend-only** tier-4b lottery rung `_claim_tier4_bestmove` (D-02).
- A dedicated `BEST_MOVE_BACKFILL_ENABLED` gate (D-05).
- A supporting partial index; routing claimed games through the existing
  `run_one_full_eval_tick`.

**Out of scope:**
- lichess **imported-eval** games (`lichess_evals_at IS NOT NULL`) — already
  drained by Phase **174-07**'s tier-3 residual fallback. 176 must not contend
  for them (D-03).
- Any change to the remote-worker protocol, the `/flaw-blob-lease` path, or the
  go-forward best-move write path beyond adding the completion-marker stamp.
- Gem/great threshold calibration (query-time constants, separate future retune).

</domain>

<decisions>
## Implementation Decisions

All five decisions were made against verified code + a live dev-DB population
count. The target population (dev DB): **6,471 engine games** pv-complete with
zero `game_best_moves` rows — **6,106 of them chess.com (~94%)**.

### Self-termination signal (the crux)
- **D-01:** Add a new **nullable `best_moves_completed_at` timestamp** column on
  `games`. It is stamped by the drain tick whenever a game goes through the
  best-move pass — on **both** the backfill path AND the existing go-forward
  path (otherwise freshly-analyzed games would re-enter the backfill pool
  forever). The self-termination predicate keys off it:
  `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`.
  Rejected: `NOT EXISTS(game_best_moves)` (ambiguous — a game can legitimately
  have zero qualifying plies and would never self-terminate); a temporal cutoff
  on `full_pv_completed_at` (fragile, non-durable).

### Lottery keying (BACK-01 explicitly deferred this to planning)
- **D-02:** Add a **new parallel tier-4b rung** `_claim_tier4_bestmove` — a copy
  of `_claim_tier4_blob`'s two-stage ES weighted (user → game) lottery, same
  plain-SELECT / no-lock shape, with the D-01 predicate — ordered **after**
  `_claim_tier4_blob` in the bundled `scope=None` path of `claim_eval_job`
  (`app/services/eval_queue_service.py`). Blob backfill (which remote workers
  CAN offload) drains first; best-move backfill uses leftover backend capacity.
  - **Rejected: OR-broadening the existing tier-4-blob rung.** That rung doubles
    as the remote-worker `/flaw-blob-lease` source; overloading its predicate
    with the best-move condition risks handing workers games whose only gap is
    best-moves — which workers **cannot** fill (Maia is backend-only, see
    D-02-fact below). Keep the axes orthogonal.
- **D-02-fact (decisive, verified):** Best-move rows require **Maia inference**,
  and `onnxruntime`/`numpy` are deliberately excluded from `Dockerfile.worker`
  (GEMS-06/D-08). Remote workers physically cannot produce `maia_prob`.
  Therefore best-move backfill **must** run on the backend in-process drain
  (`eval_drain.run_one_full_eval_tick`, the sole consumer of the bundled
  `scope=None` tier-4 path) and **requires zero worker changes**. Remote workers
  never reach the bundled tier-4 path — they use `scope=idle` (tier-3, 204 when
  empty) then the dedicated `/flaw-blob-lease`.

### Corpus scope
- **D-03:** **Engine-only** predicate `lichess_evals_at IS NULL`. **CRITICAL
  terminology:** `lichess_evals_at` is the **eval source** (lichess cloud
  %evals), NOT the platform. `lichess_evals_at IS NULL` = "games *we* analyzed
  with our own Stockfish" = **ALL chess.com games** + engine-analyzed lichess/bot
  games. chess.com never provides evals, so every chess.com game is in this
  bucket — they are the **dominant 176 population (~94%)**, not excluded. Do NOT
  misread the predicate as "exclude the lichess platform." Only lichess games
  that arrived WITH imported evals (`lichess_evals_at IS NOT NULL`) are out —
  those are 174-07's job.
- **D-03-locked:** Whole-corpus draining via ES floors + recency weighting
  (every game non-zero draw mass, fresh games dominant) is locked by BACK-01
  ("global + random, no deterministic sweep") and the tier-4 precedent — not
  re-litigated. Guest exclusion (QUEUE-08, `users` JOIN + `NOT is_guest`) is
  inherited from the shared ES building blocks.

### Initial stamp for already-covered games
- **D-04:** In the **same migration** that adds `best_moves_completed_at`, run a
  one-time stamp: set it (to `full_pv_completed_at` or `now()`) `WHERE EXISTS`
  a `game_best_moves` row for the game. Avoids needlessly re-draining the games
  that already have best-move rows (the ~4 go-forward + any 174-07-covered
  games). It won't catch a no-gem go-forward game from the 174→176 window, but
  re-draining those is idempotent (upsert on `(game_id, ply)`) and rare.

### Operational safety
- **D-05:** Add a **dedicated `BEST_MOVE_BACKFILL_ENABLED`** settings bool
  (default `False`). The tier-4b rung checks **both** it AND
  `EVAL_AUTO_DRAIN_ENABLED`. Rationale: best-move backfill load is **backend-only
  and cannot be shed to the remote 4-worker box** (unlike blob backfill, ~85% of
  which the workers carry), so it needs an independent kill-switch to pause it
  under backend CPU/latency pressure without disabling all idle drain. Enable in
  prod **deliberately, after observing backend RSS/CPU** (mirrors 174 D-03b's
  "measure RSS before enabling" posture). RAM risk is negligible (~44 MB Maia
  session already resident; multipv-2 is the same per-ply cost the go-forward
  pass already pays); D-02 preemption (live tier-1/2/3 preempts tier-4) protects
  user-facing analysis latency.

### Claude's Discretion / open research items
- **Backfill re-runs the full pass, not Maia-on-stored-data.** Pre-174 games
  never persisted the per-ply second-best cp margin for non-flaw plies, so the
  claimed game must re-run the multipv=2 Stockfish + Maia pass — exactly what
  `run_one_full_eval_tick` already does for go-forward games and what 174-07
  routes lichess games through. Planner: route the tier-4b claim through the
  same drain tick.
- **Maia-absent stamping guardrail (correctness — verify in research):** the
  drain tick must only stamp `best_moves_completed_at` when Maia **actually ran**
  (onnxruntime present / `score_move` returned data). If a Maia-absent backend
  stamped games "done" with zero rows, it would permanently lock them out of the
  backfill. Confirm both the backfill and go-forward stamping respect this.
- Exact column type (`TIMESTAMPTZ`), index name, and whether to reuse the
  `TIER4_*` half-life/floor constants or introduce `BEST_MOVE_*` ones — planner
  decides (reusing tier-4's is the likely default).
- **SC3 verification approach:** coverage growth is measurable via a snapshot
  diff of `count(DISTINCT game_id)` in `game_best_moves` (or count of stamped
  games) over time — no 100%/ETA promise (per the tier-4 backfill-measurement
  precedent: ES-lottery-driven, opportunistic, no deterministic finish).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source & requirement
- `.planning/ROADMAP.md` §"Phase 176: Backfill" (lines ~112–123) — goal, SC1–SC3,
  the BACK-01 keying deferral.
- `.planning/REQUIREMENTS.md` — **BACK-01** (the sole requirement).
- `.planning/seeds/SEED-108-backend-gem-great-detection.md` — the milestone's
  locked design (best-move storage, gem/great thresholds).

### The precedent this phase mirrors (READ FIRST)
- `app/services/eval_queue_service.py:555–654` — `_claim_tier4_blob`, the
  two-stage ES lottery to copy for `_claim_tier4_bestmove` (D-02). Shared
  building blocks `_es_weighted_user_pick` / `_es_weighted_game_pick` (~291–401).
- `app/services/eval_queue_service.py:660–776` — `claim_eval_job`; the bundled
  `scope=None` ladder (tier-1>2>3>4 blob) where the new tier-4b rung slots in
  after the blob pick. Docstring documents the SEED-072 worker/`/flaw-blob-lease`
  split that makes best-move backfill backend-only.
- `.planning/phases/174-backend-maia-inference-best-move-storage-spike-gated/174-07-SUMMARY.md`
  — the lichess best-move backfill (residual-fallback broadening + partial
  index) that covers the `lichess_evals_at IS NOT NULL` population; 176 is its
  engine-side sibling. Its `ix_games_lichess_pv_backfill_pending` is the partial
  index shape to mirror.

### Where the work happens
- `app/services/eval_drain.py` — `run_one_full_eval_tick` / `_full_drain_tick`
  (the drain the tier-4b claim routes into; `_build_best_move_candidates` at
  ~850); this is where `best_moves_completed_at` gets stamped (both paths).
- `app/services/eval_apply.py:1790–1910` — `_build_best_move_candidates` /
  `score_move` call site; returns `[]` gracefully when Maia absent (the
  Maia-absent guardrail lives here).
- `app/services/maia_engine.py` — `score_move` (backend Maia inference; None
  when onnxruntime absent).
- `app/models/game.py` — add `best_moves_completed_at` column + the partial
  index `Index(...)` declaration (must match the migration to keep
  `alembic check` drift-free — see 174-07's deviation note).
- `app/models/game_best_move.py` (the `game_best_moves` table from 174-03) — the
  rows this phase backfills.
- `app/core/config.py:83` — `EVAL_AUTO_DRAIN_ENABLED`; add
  `BEST_MOVE_BACKFILL_ENABLED` beside it (D-05).

### Consumer that must keep working (don't break)
- Phase 175 FILT-01 has-gem/has-great SQL filter — reads `game_best_moves` rows
  **directly**, NOT the new stamp. So unstamped-but-covered games stay fully
  functional; the stamp governs only the lottery.

### Worker isolation (why backend-only)
- `Dockerfile.worker` vs `Dockerfile` — onnxruntime/numpy in backend image only
  (GEMS-06). `scripts/remote_eval_worker.py` — the worker's lease ladder
  (`/atomic-lease` explicit/idle → `/entry-lease` → `/flaw-blob-lease`); no Maia,
  no best-move lease (by design).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_claim_tier4_blob` + `_es_weighted_user_pick`/`_es_weighted_game_pick`**:
  the tier-4b rung is a near-copy with a different predicate. Reuse the ES
  building blocks directly.
- **`run_one_full_eval_tick` / `_full_drain_tick`**: already writes best-move
  rows for go-forward games and (per 174-07) for routed backlog games — the
  tier-4b claim routes straight into it; no new eval code.
- **174-07's partial-index pattern** (`ix_games_lichess_pv_backfill_pending`):
  template for the engine-side backfill index.

### Established Patterns
- Spare-capacity backfill = table-less, idempotent-by-construction ES lottery
  under `EVAL_AUTO_DRAIN_ENABLED`, preempted by live tier-1/2/3 work (D-02).
- Completion markers are nullable timestamps mirroring `full_pv_completed_at` /
  `full_evals_completed_at`; predicate + partial index keyed off `IS NULL`.
- Broaden/add a rung as a **superset population with clear self-termination** to
  avoid new starvation dynamics (174-07 lesson).

### Integration Points
- New rung: after `_claim_tier4_blob` in `claim_eval_job`'s bundled path.
- New stamp: in the drain tick, on both backfill and go-forward best-move writes.
- New gate: `BEST_MOVE_BACKFILL_ENABLED` checked alongside
  `EVAL_AUTO_DRAIN_ENABLED`.
- New column + one-time stamp + partial index: single Alembic migration.

</code_context>

<specifics>
## Specific Ideas

- The whole phase is a faithful **engine-side mirror of 174-07**: same "give the
  already-analyzed backlog best-move coverage opportunistically" goal, different
  population (our-engine-analyzed / chess.com-dominant, vs 174-07's
  lichess-imported-eval games) and a different self-termination marker
  (`best_moves_completed_at` vs `full_pv_completed_at`).
- Keep the axes orthogonal: blob backfill (`allowed_pv_lines IS NULL`, worker-
  offloadable) and best-move backfill (`best_moves_completed_at IS NULL`,
  backend-only) are separate rungs sharing only the ES machinery.
- Prod rollout is deliberately gated (D-05) and measured (174 D-03b) — do not
  enable best-move backfill in prod as part of the code merge; it's a separate,
  observed flag flip.

</specifics>

<deferred>
## Deferred Ideas

- **Gem/great threshold calibration against real per-game frequency** — query-
  time constants-only retune, milestone Future Requirements (GEMS-07), not 176.
- **Any Maia-on-workers escape hatch** — a worker-protocol change explicitly
  rejected (174 D-02); best-move backfill stays backend-only.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 176-backfill*
*Context gathered: 2026-07-17*
