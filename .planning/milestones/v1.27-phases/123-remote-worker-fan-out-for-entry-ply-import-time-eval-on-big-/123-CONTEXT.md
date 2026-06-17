# Phase 123: Remote-worker fan-out for entry-ply (import-time) eval on big first imports - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the existing SEED-048 / Phase 120 headless remote eval worker — which today only drains
**full-ply** tier-1/3 (1M nodes, gated on `full_evals_completed_at`) — to also drain **entry-ply**
(import-time, depth-15, the 2-3 phase-transition positions per game, gated on
`games.evals_completed_at IS NULL`) **in parallel on big first imports**, cutting first-import
latency (time until a brand-new user sees flaws / phase-transition evals populate) by roughly the
worker fan-out factor.

The mechanism is **locked by SEED-051 D-1…D-5** and is NOT re-opened here:
- **D-1** — three-rung priority ladder, checked between full-ply games, no preemption, no reserved
  capacity: tier-1 single-game (top) > entry-ply fresh-import drain (new, batched depth-15) >
  tier-3 idle backlog (bottom).
- **D-2** — server ships FENs (reuses `_collect_eval_targets` / phase-transition selection + all
  SEED-044 storage convention); worker stays a dumb Stockfish-over-HTTP node.
- **D-3** — no new table; one nullable lease column on `games` (`entry_eval_lease_expiry`), claimed
  via `SKIP LOCKED` LIFO (`id DESC`); queue stays the predicate `games.evals_completed_at IS NULL`.
- **D-4** — use a real lease (NOT tier-3's lottery-only model); fresh import is a tiny LIFO hot set
  that N claimers must partition.
- **D-5** — invite workers by **backlog depth at lease time** via a bounded existence probe
  (`… WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 1 OFFSET 299`); gate on game count;
  starting knobs: threshold 300 games, batch 50 games; tail (≲300) falls back to the server pool.

This discussion only resolves the **HOW** forks the seed left open (its "Open/Deferred" list) plus
the worker-loop integration mechanics. Scope is the small delta over the Phase 120 worker.

</domain>

<decisions>
## Implementation Decisions

### Server-pool lease participation (seed Open item — resolved: v1)
- **D-01:** The in-process server drain claims through the new lease column **in v1** — server and
  remote workers **strictly partition** the same import; neither double-evaluates a game.
  - `_pick_pending_game_ids` (`app/services/eval_drain.py`) gains the lease predicate
    `(entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())` and **sets** the lease
    when it picks (same `SKIP LOCKED` LIFO claim shape as the remote endpoint).
  - Lease ends naturally: stamping `evals_completed_at = now()` on completion is the permanent
    release; a crashed server pick is reclaimed by the TTL.
  - This is the natural completion of D-3 and removes the only remaining source of wasted depth-15
    CPU. The lease column has to exist anyway.
- **D-02:** The **D-5 backlog-depth gate stays remote-lease-only.** The server pool always drains
  regardless of backlog depth; the existence-probe gate governs only whether the `/entry-lease`
  endpoint hands a batch to a remote worker.

### Tuning knobs (seed Open item — resolved: constants)
- **D-03:** Threshold (300 games), batch size (50 games), and the entry-ply lease TTL are
  **named module-level constants**, not env vars. (User preference: tweak constants over config
  plumbing; values expected to lock quickly after one live measurement.) Place near the drain /
  endpoint they govern.
- **D-04:** Entry-ply lease **TTL value** is chosen during planning — short, well under the 120s
  full-ply lease TTL, since entry-ply batches are only seconds of work.

### Worker ladder mechanics (worker-loop integration — resolved)
- **D-05:** **Worker orchestrates the ladder** across endpoints; the existing `/eval/remote/lease`
  gains an **optional `scope` param**:
  - **absent** → today's bundled tier-1>2>3 behavior (so **un-updated workers keep working
    unchanged** and simply never drain entry-ply — zero-coordination rollout).
  - `scope=explicit` → tier-1/2 only (`_claim_tier1_2_queued`).
  - `scope=idle` → tier-3 only (`_claim_tier3_derived`).
  - `claim_eval_job` already splits into these internals, so `scope` is a thin param.
- **D-06:** New worker per cycle calls: `scope=explicit` → if 204, `/entry-lease` (gated batch) →
  if empty, `scope=idle`. Up to 3 cheap round-trips, but only on the idle/tier-3 path where the
  worker is already sleeping between polls; busy paths (tier-1, entry-ply) stay at 1-2 calls.
- **D-07:** Endpoints stay single-purpose: separate **batched `/entry-lease`** and **batched
  `/entry-submit`** endpoints (seed scope items 2 & 3) rather than overloading `/lease`'s
  single-game response with a discriminated union (rejected: muddier contract + not
  backward-compatible without a capability negotiation).

### Worker mode activation + observability (resolved)
- **D-08:** Entry-ply is **ON by default** in the upgraded worker binary (no opt-in flag). The D-5
  backlog gate makes always-on safe — `/entry-lease` returns empty unless backlog ≥ threshold, so
  an entry-capable worker costs nothing when there's no big import.
- **D-09:** Add the optional **`entry_eval_leased_by`** column on `games` alongside
  `entry_eval_lease_expiry` (worker-identifier, set at lease time) for prod debuggability.
  Type **`VARCHAR(16)`** — don't waste space; fits both the `"remote-worker"` default (13) and the
  < 10-char worker IDs (D-10) with headroom. Do NOT use `TEXT`.

### Distinctive worker IDs (folded in — makes the leased_by columns useful)
- **D-10:** Each worker self-assigns a **distinctive ID** instead of the current constant
  `_WORKER_ID_REMOTE = "remote-worker"`. Used for **both** `eval_jobs.leased_by` (full-ply path,
  replacing the constant) **and** the new `entry_eval_leased_by`.
  - **Generation:** random per process at startup (e.g. 8-char base36); operator may override with
    a `--worker-id` flag for named boxes (`macbook`, `vps1`), validated **< 10 chars**.
  - **Transport:** sent on lease calls via an **HTTP header** (e.g. `X-Worker-Id`), alongside the
    existing operator-token header. Absent header (old worker) → server falls back to the
    `"remote-worker"` default — same backward-compat story as the `scope` param.
  - Rationale: without distinctive IDs the new `entry_eval_leased_by` column (and existing
    `leased_by`) would always read `"remote-worker"`, defeating the observability purpose D-09 adds.

### Claude's Discretion
- Exact lease-claim SQL shape for the server-side path (mirror the remote endpoint's `SKIP LOCKED`
  LIFO claim); exact module placement of the constants; `X-Worker-Id` exact header name; base36
  length/charset for the random worker ID (must fit `VARCHAR(16)` per D-09); migration index
  strategy for the new lease columns (reuse / extend the existing `ix_games_evals_pending` partial
  index where it helps).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed + roadmap (the locked spec)
- `.planning/seeds/SEED-051-remote-worker-entry-ply-fresh-import-drain.md` — this phase's source;
  D-1…D-5 locked decisions + "What Already Exists" + "Open/Deferred" list.
- `.planning/seeds/SEED-048-headless-remote-eval-worker.md` — parent; the lease/submit protocol,
  operator-token auth, SF-version pinning, and "dumb FEN→eval worker" (D-2) this extends.
- `.planning/ROADMAP.md` § "Phase 123" — scope list (5 work items) + Open/deferred.

### Storage convention (server keeps owning per D-2)
- SEED-044 (storage convention: post-move +1 shift, terminal donor, completion stamp) — referenced
  throughout `eval_drain.py`; the server applies it, the worker never does.

### Code the work plugs into
- `app/services/eval_drain.py` — `run_eval_drain`, `_pick_pending_game_ids` (D-01 server-lease
  change), `_collect_eval_targets_per_game` / `_collect_target_specs` / `_collect_midgame_eval_targets`
  / `_collect_endgame_span_eval_targets` (FEN derivation D-2 reuses), `_mark_evals_completed`.
- `app/routers/eval_remote.py` — `/eval/remote/lease` (gains `scope` param, D-05), `/submit`,
  `_build_lease_positions`, `_apply_submit`, `require_operator_token`, `_WORKER_ID_REMOTE` (D-10
  replaces). New `/entry-lease` + `/entry-submit` go here.
- `app/services/eval_queue_service.py` — `claim_eval_job`, `_claim_tier1_2_queued`,
  `_claim_tier3_derived` (the tier internals `scope` selects between), lease TTL constants.
- `app/services/engine.py` — `EnginePool.evaluate(board)` depth-15 mode (entry-ply engine call).
- `scripts/remote_eval_worker.py` — the worker CLI: add the ladder orchestration (D-05/D-06),
  entry-ply depth-15 mode (default-on, D-08), and the `--worker-id` flag + `X-Worker-Id` header
  (D-10).
- `tests/test_eval_worker_endpoints.py` — existing endpoint test patterns to extend.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `claim_eval_job` already decomposes into `_claim_tier1_2_queued` and `_claim_tier3_derived`, so
  the `scope` param (D-05) is a thin selector, not a rewrite.
- `_collect_eval_targets_*` / `_collect_target_specs` derive entry-ply FENs from PGN + PlyData
  verbatim — the batched `/entry-lease` reuses these (D-2), no new derivation logic.
- `_apply_full_eval_results` / SEED-044 write path: the existing `/submit` already applies the
  post-move shift server-side; `/entry-submit` follows the same ownership split.
- `ix_games_evals_pending` partial index (`WHERE evals_completed_at IS NULL`) backs both the LIFO
  claim and the D-5 existence probe.

### Established Patterns
- Lease-by-TTL + `SKIP LOCKED` is already how `eval_jobs` claims (tier-1/2); the new `games` lease
  column mirrors it (D-3).
- Idempotent submits (ON CONFLICT DO NOTHING for flaws, idempotent oracle UPDATE, completion
  markers) make duplicate/overlapping evals correctness-safe — already relied on in Phase 117/120.
- Backward-compat-by-optional-param: Phase 121's `/lease` already releases mis-claimed lichess
  games; the `scope`-absent default and `X-Worker-Id`-absent default follow the same additive style.

### Integration Points
- `_pick_pending_game_ids` is the single server-side entry-ply claim site → D-01 lease change lands
  there.
- The worker loop (`_run_cycle` / `_run_loop` in `remote_eval_worker.py`) is where the D-05/D-06
  ladder orchestration replaces the single `/lease` call.

</code_context>

<specifics>
## Specific Ideas

- User explicitly wants distinctive worker IDs (current `leased_by` always reads `"remote-worker"`)
  so different workers are distinguishable in prod — random, operator-overridable, < 10 chars
  (D-10).
- User prefers constants over env-var config for the tuning knobs (D-03), consistent with the
  project's "tweak the constant" style.
- Smooth/backward-compatible worker rollout was a stated priority — deploy server first, upgrade
  worker binaries at leisure, mixed fleet must not break (drove D-05's optional `scope` and D-10's
  optional header).

</specifics>

<deferred>
## Deferred Ideas

- **Backlog-gate threshold tuning** — the 300-game starting knob (and 50-game batch / TTL) get
  re-measured against real server-pool throughput once the worker is live (SEED-051 D-5: "measure
  the true value once live"). Not a v1 blocker; v1 ships the constants.
- **macOS background-scheduling caveat** (SEED-048) unchanged — depth-15 spawns at default priority
  on a MacBook worker; no v1 action.

None — discussion otherwise stayed within phase scope.

</deferred>

---

*Phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big*
*Context gathered: 2026-06-16*
