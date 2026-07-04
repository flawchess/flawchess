# Game Import & Analysis Pipeline — Architecture Review

**Date:** 2026-07-04
**Scope:** the full game pipeline from `POST /imports` to a fully-analyzed game: import (fetch, normalize, persist), the entry-ply eval drain, the full-ply eval drain (tiers, leasing, classification, tactic blobs), and the remote worker infrastructure (protocol, worker daemon, fleet).
**Method:** first-hand read of `eval_drain.py`, `eval_queue_service.py`, `eval_remote.py`, `engine.py`, `import_service.py`, and the worker script, plus three parallel deep-read agents over the import, drain, and worker subsystems.

**Code surface:** ~12,600 lines across the core files (`eval_drain.py` 2,986; `eval_remote.py` 1,666; `remote_eval_worker.py` 1,161; `import_service.py` 1,000; `flaws_service.py` 1,044; `eval_queue_service.py` 865; `engine.py` 642; clients + normalization ~1,150), backed by ~6,300 lines of worker-endpoint tests.

---

## 1. Executive summary

The pipeline is **architecturally sound but organically accreted**. Its core invariants are consistently enforced and well-tested: short-session discipline (no `asyncio.gather` inside a session), server-authoritative classification (workers are untrusted FEN→eval functions), idempotent writes everywhere, bounded retry with an anti-infinite-loop cap, and a fail-closed auth boundary. Prod is healthy at 686k games.

The cost of ~30 phases of incremental evolution is now visible in four places:

1. **Seven entry points run the same algorithm.** Two in-process drain loops plus five HTTP endpoint pairs all funnel into the same `eval_drain` helpers, with the orchestration around those helpers (read phase, completion decision, job stamping) copy-pasted rather than shared. The Path A/B/C bounded-retry state machine exists **three times verbatim**.
2. **Four protocol generations are live simultaneously.** `/lease`+`/submit` (Gen-1, no longer called by the current worker), `/entry-lease`+`/entry-submit`, `/flaw-blob-lease`+`/flaw-blob-submit`, and `/atomic-lease`+`/atomic-submit` (current). Nothing has ever been retired.
3. **The flaw write is delete-then-insert**, which forced a snapshot/restore compensation layer on the incremental-retry path — the single largest source of recent production bugs (FLAWCHESS-8D StaleDataError, the ungated-tag windows of Phases 146–147).
4. **`classify_game_flaws` plus a full game+positions reload runs up to five times per game per tick** across the helper chain (`_flaw_engine_plies`, `_missing_flaw_pv_targets` ×2, `_build_flaw_multipv2_blobs`, `_classify_and_fill_oracle`), each helper independently re-doing the same "load, overlay evals, classify" preamble.

None of these are correctness emergencies. They are maintenance-cost and bug-surface problems: every new feature (Phase 142 blobs, 145 tier-4, 147 atomic) has had to be threaded through 3+ parallel copies of the same logic, and the recent bug history (8B, 8D, SEED-075/076) traces directly to those seams. The highest-leverage work is **consolidation, not redesign**: the shared building blocks already exist and are already shared; only the orchestration around them is duplicated.

Section 6 gives prioritized recommendations. The top three by value/risk ratio:

- **R1** — extract the completion decision (Path A/B/C + eval_jobs stamp) into one function (3 copies → 1).
- **R2** — retire the Gen-1 `/lease`+`/submit` pair once the fleet is confirmed on atomic, collapsing `eval_remote.py` toward one lease + one submit.
- **R3** — replace the delete-then-insert flaw write with a per-ply diff/upsert, deleting the snapshot/restore layer entirely.

---

## 2. End-to-end data flow

```
                 ┌─────────────────────────────────────────────────────────────┐
                 │                        IMPORT (hot lane)                    │
POST /imports ──►│ create_job (in-mem) → run_import (asyncio task)             │
                 │   bootstrap (DB job row) → platform fetch → normalize       │
                 │   → batch of 30 → _flush_batch:                             │
                 │       games upsert → zobrist walk → positions COPY          │
                 │       → ply_count/result_fen → covered-game gate            │
                 │       → lichess_evals_at stamp                              │
                 └───────────────┬─────────────────────────────────────────────┘
                                 │ games with evals_completed_at IS NULL
                                 ▼
                 ┌─────────────────────────────────────────────────────────────┐
                 │              ENTRY-PLY DRAIN (fast, depth-15)               │
                 │ run_eval_drain loop / remote /entry-lease + /entry-submit   │
                 │   ~1-3 entry plies per game → evals_completed_at stamped    │
                 │   → unlocks endgame stats + percentile Stage B              │
                 └───────────────┬─────────────────────────────────────────────┘
                                 │ games with full_evals_completed_at IS NULL
                                 ▼
                 ┌─────────────────────────────────────────────────────────────┐
                 │            FULL-PLY DRAIN (deep, 1M nodes/ply)              │
                 │ claim_eval_job: tier1 > tier2(dead) > tier3 lottery > tier4 │
                 │ local: _full_drain_tick        remote: /atomic-lease+submit │
                 │   every ply MultiPV-2 → post-move shift → classify flaws    │
                 │   → oracle counts → PVs → forcing-line blobs → tactic tags  │
                 │   → Path A/B/C → full_evals_completed_at + full_pv_...      │
                 └───────────────┬─────────────────────────────────────────────┘
                                 │ analyzed games with NULL-blob flaws
                                 ▼
                 ┌─────────────────────────────────────────────────────────────┐
                 │        TIER-4 BLOB BACKFILL (remote-only, MultiPV-2)        │
                 │ /flaw-blob-lease + /flaw-blob-submit → gated tactic retag   │
                 └─────────────────────────────────────────────────────────────┘
```

Remote workers (`scripts/remote_eval_worker.py`) poll a four-rung ladder each cycle: atomic-lease explicit → entry-lease → atomic-lease idle → flaw-blob-lease, sleeping 1s when all four 204.

---

## 3. Stage documentation

### 3.1 Import

**Entry point.** `POST /imports` (`app/routers/imports.py:46-87`): auth-gated, checks an **in-memory** duplicate guard (`find_active_job`), persists the platform username eagerly, registers an in-memory `JobState` in a module-level dict, and spawns `asyncio.create_task(run_import(job_id))`. The DB `import_jobs` row is created later, inside the background task's bootstrap scope — there is a known window where the job exists only in memory (`_record_failure_with_retry` explicitly handles the "bootstrap never committed" case).

**Orchestrator.** `run_import` (`import_service.py:551-648`) runs under a 3-hour `asyncio.timeout`. Each stage owns its own short `AsyncSession` (bootstrap / per-batch / completion), a deliberate Phase-90 posture after the session-lifetime OOM history. Failures never propagate; they are sanitized (only `ValueError` messages reach the client) and persisted via a bounded-retry failure recorder that survives a Postgres restart window.

**Platform fetch.**
- *chess.com* (`chesscom_client.py`): fetches the archive index, then monthly archives sequentially under a process-wide semaphore(3) with 150ms pacing, 60s backoff on 429, exponential backoff on 5xx. A 404 on the index triggers a three-way disambiguation (user missing vs. archive-index flake), falling back to month-by-month URL enumeration from the account's join date. Transient failures **raise** rather than skip, so `last_synced_at` is never advanced past unfetched games (the silent-data-loss guard).
- *lichess* (`lichess_client.py`): one streaming NDJSON request per import (`aiter_lines`, never buffers the export), semaphore(3) held for the stream duration, same retry envelope via a `_RetryableStatusError` sentinel.

**Normalization** happens inside the client generators (`normalization.py`): variant filtering (Standard only), color/result/termination mapping, TC bucketing, opening lookup, and — lichess only — the embedded `%eval` analysis block. Output is the unified `NormalizedGame` Pydantic model.

**Persistence.** `_flush_batch` (`import_service.py:706-837`), one transaction per 30-game batch:
1. `bulk_insert_games` — upsert with `ON CONFLICT DO NOTHING` on `(user_id, platform, platform_game_id)`; only new IDs proceed (dedup makes re-syncs no-ops).
2. `process_game_pgn` (`zobrist.py:138-267`) — **one mainline walk per game** computing all three Zobrist hashes per ply (white/black/full, signed int64), SAN, clock, clamped `%eval`, endgame class, and phase; per-game parse failures are isolated.
3. `bulk_insert_positions` — asyncpg binary COPY, chunked at 1,700 rows.
4. Bulk `ply_count`/`result_fen` updates via invariant-SQL executemany (the FLAWCHESS-56 prepared-statement-leak fix).
5. **Stage 5c covered-game gate**: games whose entry plies are already covered by lichess `%eval` get `evals_completed_at = NOW()` immediately plus inline flaw classification (so badges don't show 0 while the chart shows flaws).
6. **Stage 5d**: stamps `lichess_evals_at` provenance.

**Completion** advances `last_synced_at` (even on 0-game syncs) and fires percentile Stage A (and conditionally Stage B) as post-commit fire-and-forget tasks.

**Restart behavior.** In-memory registry and the task die with the process; per-batch commits preserve partial data; the orphan reaper (startup + every 5 min with 3h threshold) fails abandoned DB rows; `last_synced_at` not having advanced makes re-sync correct. There is no cancellation endpoint and no durable per-user duplicate guard.

### 3.2 Entry-ply drain (the fast lane)

`run_eval_drain` (`eval_drain.py:2311-2415`), always-on. Purpose: cheap **depth-15** evals of ~1-3 "entry plies" per game (one middlegame entry, one per endgame span) so endgame statistics and percentiles unlock quickly after an import, long before deep analysis completes.

Tick shape: claim 10 games LIFO via `_claim_entry_eval_games` (TTL-leased UPDATE…SKIP LOCKED, `entry_eval_lease_expiry`/`entry_eval_leased_by` columns, TTL 20s — the **one canonical claim** shared with `/entry-lease`) → load PGNs → derive targets from stored position metadata → `asyncio.gather` over the pool with no session open → late write session: apply evals, classify flaws, stamp `evals_completed_at`, commit → fire Stage B for users whose pending count hit zero. Engine failure on a position is terminal for that row (D-09, no retry loop). Remote workers participate via `/entry-lease` (server-gated behind a 300-game backlog threshold) + `/entry-submit` (lease-ownership-filtered).

Known gap (already triaged fix-soon): unlike the full drain, this loop has **no all-fail circuit breaker** — a dead pool would stamp games as evaluated with NULL entries at loop speed.

### 3.3 Full-ply drain (the deep lane)

`run_full_eval_drain` → `_full_drain_tick` (`eval_drain.py:2488-2807`), one game per tick, always yielding to imports and entry-ply backlog (Step-0 gate).

**Scheduling — `claim_eval_job`** (`eval_queue_service.py:641-757`), tier 1 > 2 > 3 > 4:
- **Tier 1 (explicit)**: `eval_jobs` table, `SELECT … FOR UPDATE SKIP LOCKED`, 120s lease, expired-lease sweep at the top of every claim. Race-free.
- **Tier 2 (auto-window)**: **dead lane** — no enqueue source since Phase 118; constant, column, and ordering key retained for a hypothetical future mode.
- **Tier 3 (idle backlog)**: *derived* pick, no queue row. Two-stage Efraimidis–Spirakis lottery: recency-weighted user pick (`exp(-Δt/τ) + floor` on `last_activity`, τ½ = 1d), then TC-weighted × recency-weighted game pick (classical 8× > … > bullet 1×, τ½ = 30d). Plain SELECT, **no locking** — double-claim between the local pool and remote workers is a known accepted race (idempotent, wastes engine cycles).
- **Tier 4 (blob backfill)**: same two-stage lottery over analyzed games with NULL-blob flaws. Reached only by the bundled local scope and the dedicated `/flaw-blob-lease` rung; `scope=idle` deliberately 204s instead (the SEED-072 invariant: the `/submit` path writes no blobs, so serving tier-4 through it would loop forever).

**Per-game algorithm** (identical whether the engine results come from the local pool or a worker POST):
1. Collect one target per ply plus a terminal eval-donor for engine games (`_collect_full_ply_targets`). Lichess `%eval` games keep their evals and only get engine passes at flaw plies (pre-classified from stored evals via `_flaw_engine_plies`).
2. Opening dedup (`ply ≤ 20`): batch lookup in the `opening_position_eval` cache — a PK-indexed, insert-only, cross-user cache of opening evals (the SEED-053 replacement for an 8.4s self-join). Cache hits skip the engine.
3. `asyncio.gather(evaluate_nodes_multipv2)` at 1M nodes over the remaining targets, no session open. All-fail → WR-05 circuit breaker leaves the game pending with one Sentry event.
4. Recovery passes for dedup-transplanted flaw plies (PV + second-best, SEED-056) and the in-memory MultiPV-2 forcing-line blob build (Phase 142, solver-nodes-only per SEED-079).
5. **One write session**: batched eval/best_move UPDATEs with the **post-move shift** (row *k* stores the eval of the position after move *k*; the single `+1` site is `_post_move_eval`) → `_classify_and_fill_oracle` (delete-then-insert `game_flaws`, oracle count columns, flaw PVs at N and N+1, tactic tags gated through the forcing-line filter with `blobs_pending=True` suppression) → blob write → opening-cache upsert → **Path A/B/C**:
   - **A** (0 holes): stamp `full_evals_completed_at` + `full_pv_completed_at`.
   - **B** (holes, under `MAX_EVAL_ATTEMPTS=3`): increment `full_eval_attempts`, leave pending.
   - **C** (holes at cap): stamp anyway (no-infinite-loop invariant); `resweep_holed_games` exists as the manual inverse edge.

### 3.4 Remote worker infrastructure

**Protocol.** All endpoints under `/api/eval/remote`, authenticated by a single fleet-wide `X-Operator-Token` (fail-closed, constant-time compare). `X-Worker-Id` is advisory only. Payloads are strictly bound-validated at the Pydantic layer (SMALLINT ranges, string lengths, list caps) so a corrupt worker can 422 but never 500-loop. Submits are version-gated on `EXPECTED_SF_VERSION`. The server never trusts worker classification: the atomic path re-runs `classify_game_flaws` on its own positions and independently re-derives sentinel lines; token tamper guards reject foreign blob tokens; the owner is derived from the game, never the payload.

**Worker daemon** (`remote_eval_worker.py`): supervisor/child/once process topology with a fixed-3s-restart supervisor, an in-process stall watchdog (600s → `os._exit(1)`), and a file-based heartbeat for the Docker healthcheck (observability only). Each cycle walks the four-rung ladder (§2). The worker runs `--workers N` independent single-threaded Stockfish processes and fans out with `asyncio.gather`. On the atomic path it additionally runs a **local hint classify** (importing the server's own `_run_all_moves_pass`) to decide which plies to blob — the hint is never trusted server-side. Sentry hygiene is careful: transient churn (5xx, 401/404/409/429, transport errors) is ridden out silently and only a 300s streak escalates one event.

**Fleet.** No DB registry, no registration, no per-worker credentials, no server-side liveness. Workers are visible only through `leased_by` values and access-log IPs (consistent with the known topology: one local 4-worker box carrying ~85% of tier-4 throughput plus two small Hetzner workers). Weak-worker damage (position timeouts → holes → Path-C stamps, the FLAWCHESS-8B history) is mitigated by cache-aware + incremental re-leases (`preserve_existing_evals`) but Path-C permanent incompleteness remains by design, and there is no capability-based routing to keep heavy tier-1 games off weak boxes.

### 3.5 Completion-state machine

Four interacting columns on `games` (canonical doc: `.planning/notes/eval-completion-columns.md`):

| Column | Meaning | Writer |
|---|---|---|
| `lichess_evals_at` | provenance: lichess `%eval` ingested | import only |
| `evals_completed_at` | entry-ply lane done (**not** "analyzed") | import 5c + entry drain |
| `full_evals_completed_at` | every ply evaluated (source-agnostic) | full drain / submits |
| `full_pv_completed_at` | best_move/PV written for all plies | same pass |

Plus `full_eval_attempts` (bounded retry) and the entry-lease pair. "Analyzed by our engine" = `full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL`. Note there are effectively **four notions of "analyzed"** in play (the three `Game` hybrids plus `flaws_service`'s ≥90% coverage gate) and they are not complements — this is documented but remains a recurring footgun.

---

## 4. What is genuinely good

Worth stating explicitly, because the recommendations below should not disturb these:

- **Session discipline.** The read → close → gather → late-write choreography is applied uniformly and directly addresses the documented OOM history. The hard rule is repeated at every gather site.
- **Idempotency as the default.** Upserts on natural keys, `WHERE status='leased'` guards on every job stamp, re-stampable completion markers, insert-only opening cache. Duplicate and late deliveries are safe everywhere.
- **Server-authoritative trust model.** Workers can only fill evals; they cannot influence flaw membership, ownership, or completion semantics. The T-145/T-147 tamper guards and bound validation close the practical spoofing/DoS holes for the current threat model.
- **Bounded everything.** Retry caps, lease TTLs, batch chunk sizes, Sentry quota hygiene (aggregate events, not per-ply), the WR-05 circuit breaker, the resweep chunking.
- **The opening dedup cache** is a clean, high-leverage design: position-keyed, insert-only, shared by lease omission, submit fill, and the local drain, so all three agree on what is server-fillable.
- **Import data-loss guards**: raising (not skipping) on transient fetch failures so the sync cursor never advances past unfetched games.
- **Engine pool ergonomics**: `SCHED_IDLE` + `PDEATHSIG` means the pool can saturate cores without starving the API and can never leak orphan processes.

---

## 5. Findings

### 5.1 Duplication (the dominant cost)

| # | Finding | Sites |
|---|---|---|
| D1 | **Path A/B/C completion decision triplicated verbatim** (~35 lines each), plus the guarded `eval_jobs` stamp duplicated at the same three sites | `eval_drain.py:2745-2794`, `eval_remote.py:457-509`, `eval_remote.py:1558-1614` |
| D2 | **`/lease` and `/atomic-lease` are ~95% identical**; `_apply_submit` is a strict subset of `_apply_atomic_submit` | `eval_remote.py:553-645` vs `648-743`; `330-521` vs `1344-1631` |
| D3 | **Classify-preamble repeated 4×**: open session, load game+positions, overlay in-memory post-move evals, `classify_game_flaws`, walk PVs | `_flaw_engine_plies:901`, `_missing_flaw_pv_targets:979`, `_build_flaw_multipv2_blobs:1216`, `_derive_atomic_sentinel_lines:1340` |
| D4 | **Engine acquisition triplicated** in `EnginePool` (`_analyse` / `_analyse_with_pv` / `_analyse_multipv2`) — identical acquire/timeout/restart/release skeleton, with a comment saying the logic "must never diverge" | `engine.py:459-543, 568-606` |
| D5 | **ES lottery duplicated** between tier-3 and tier-4 (near-identical two-stage SQL, separately-seeded constants) | `eval_queue_service.py:278-487, 490-635` |
| D6 | **Five batched-UPDATE helpers** repeat the same `CAST(:p) VALUES` construction | `eval_drain.py:416-540, 1413-1444, 1962-2013` |
| D7 | **Blob assembly index-parity scheme implemented three times** (live build, submit reassembly, lease builder) | `_build_line_blobs:1175`, `_assemble_one_line_blob:1589`, `_build_flaw_blob_lease_positions:1463` |
| D8 | Retry/backoff constants and status handling duplicated between the two platform clients | `chesscom_client.py:32-47`, `lichess_client.py:26-34` |

The practical consequence of D1–D3: `eval_remote.py` imports ~20 underscore-private helpers from `eval_drain.py`. The router and the drain are one component split across a module seam, and every change to the write path must be verified at three orchestration sites.

### 5.2 Fragility (where the bugs have actually come from)

| # | Finding |
|---|---|
| F1 | **Delete-then-insert flaw write** (`_classify_and_fill_oracle:794-814`) forces the snapshot/restore compensation layer (`_snapshot_preserved_flaw_blobs` / `_restore_preserved_flaw_blobs`, `eval_remote.py:1245-1341`) on the incremental-retry path. This seam produced FLAWCHESS-8D (StaleDataError on plies that drop out of flaw status between submits) and is the reason blob preservation logic lives in a router. |
| F2 | **The `blobs_pending` vs `[]`-sentinel distinction** (`flaws_service.py:552-585`): `[]` is FINAL (gate skipped, raw tag stands), absent-with-pending is suppressed to NULL. Getting this backwards re-mints ungated tactic tags (the Phase-147 "strict-zero violation" and the SEED-075 local-drain bug). Three call sites must each pass `blobs_pending=True` correctly. |
| F3 | **SEED-072 tier-4 routing is enforced by convention only** (the `scope="idle"` early return, `eval_queue_service.py:659-690`). A future caller wiring tier-4 through `/lease` re-creates the 5:1 infinite re-serve waste. |
| F4 | **Entry drain lacks the all-fail circuit breaker** the full drain has — a dead pool stamps `evals_completed_at` with NULL evals at loop speed. (Already triaged fix-soon.) |
| F5 | **Import duplicate guard and job registry are in-memory only**; the DB row is created lazily. Restart + re-POST (or a second process) can double-import; wasteful rather than corrupting, thanks to the games upsert. No cancellation endpoint. |
| F6 | **Tier-3/4 double-claim** between local pool and workers (plain SELECT, no lock) — accepted and documented, but it burns full 1M-node game evaluations, the most expensive unit of work in the system. |
| F7 | `_normalize_chesscom_result` falls back to `1/2-1/2` for unrecognized result strings — a decisive game with unmapped strings would be silently recorded as a draw. |
| F8 | `worker_schema_version` is accepted but never gated; a stale worker degrades silently (misses blob coverage) rather than being told to update. |

### 5.3 Performance / memory

| # | Finding |
|---|---|
| P1 | **chess.com buffers whole monthly archives** (`resp.json()`) while lichess streams line-by-line — the one remaining unbounded-ish memory spike in the import hot lane, and an inconsistency between the two paths. |
| P2 | **Redundant classification work per full-drain tick**: the D3 preamble means the same game is loaded and classified up to 5 times (once in `_flaw_engine_plies` for lichess, twice via `_missing_flaw_pv_targets` for the PV and second-best recovery passes, once in `_build_flaw_multipv2_blobs`, once in `_classify_and_fill_oracle`). Pure CPU + repeated position loads; not a prod bottleneck today, but pure waste. |
| P3 | The lost-work window within a lease: a worker that evaluates 100 positions and dies before POST loses all of it. The incremental re-lease only helps *across* attempts. Acceptable at current fleet scale. |

### 5.4 Dead weight

- `_handle_full_ply_response` in the worker (Gen-1 client path, no longer wired into `_run_cycle`).
- Tier-2 lane: constant, column, claim ordering — no enqueue source since Phase 118.
- `hashes_for_game` legacy wrapper (`zobrist.py:270-317`).
- `chesscom_to_lichess.py` Table 3 + four `lookup_*` accessors shipped "for future use" with no caller.
- `Game.needs_engine_full_evals` hybrid documented as caller-less (the SQL predicate is inlined where needed).

### 5.5 Readability

`eval_drain.py` is roughly half comments, most encoding *historical* decision provenance (phase numbers, seed IDs, review-item codes) rather than live invariants. The bug-fix-comment rule (CLAUDE.md) is being followed, but at this density the live invariants (post-move shift, session rule, sentinel semantics) drown in changelog. The module has also outgrown its name: it contains the entry drain, the full drain, the shared write path, the blob machinery, and the remote-lease helpers.

---

## 6. First-principles assessment

Strip the history away and the system has exactly **three jobs**:

1. **Ingest**: platform → normalized game + positions (per-user, incremental, idempotent).
2. **Analyze**: bring a game from imported → fully analyzed. One algorithm: evaluate positions, classify flaws, tag tactics, stamp done. Compute may come from the local pool or a remote worker; that is a *transport* difference, not an algorithmic one.
3. **Schedule**: decide which game to analyze next (explicit request > fresh users > backlog > blob debt).

Measured against that:

- **Ingest is close to its first-principles shape.** One orchestrator, two clients, one normalizer, one flush path. The remaining gaps are operational (durable dedup guard, chess.com buffering, shared retry helper), not structural.
- **The two-lane analyze split (entry vs full) is justified and should stay.** The cost asymmetry is real: ~2-3 depth-15 evals per game versus ~80 MultiPV-2 1M-node evals is a 100-1000× difference, and the entry lane is what makes stats usable minutes after a 10k-game import instead of weeks later. Merging the lanes would be a UX regression dressed up as simplification. The correct target is not fewer lanes but **one write/orchestration path per lane**.
- **The analyze algorithm already exists exactly once** (the eval_drain helpers). What violates first principles is that its *orchestration* exists seven times. The local `_full_drain_tick` and the HTTP `_apply_atomic_submit` are the same function differing only in where `engine_result_map` and the blobs come from. A single `apply_full_eval(game_id, engine_result_map, blob_source, *, preserve_existing)` would serve both, with the drain calling it after a local gather and the router after deserializing a POST.
- **The scheduler is one function already** (`claim_eval_job`) — genuinely shared between local and remote. Good. Its internals just carry a dead lane and a duplicated lottery.
- **The protocol wants to be one lease + one submit.** The four generations exist because retirement was never scheduled, only accretion. The mixed-fleet argument is sound *during* a migration, but the migration completed (the current worker no longer calls Gen-1); what remains is unmeasured backward compatibility for workers that may no longer exist. `worker_schema_version` is already on the wire and can answer that question.
- **The flaw table write is the one place the design fights itself.** Delete-then-insert made sense when a classify pass was total and one-shot. Once incremental retries and deferred blobs existed (Phases 145-147), "delete everything, then compensate for what should have survived" became strictly worse than "compute the desired flaw set, diff against the existing rows, upsert/delete the difference." The snapshot/restore layer, the freshly-blobbed set arithmetic, and FLAWCHESS-8D are all costs of the wrong primitive.

---

## 7. Recommendations

Ordered by value-to-risk ratio. Per the GSD process, these are flagged for planning (seeds/phases), not implemented here. Effort estimates are for implementation plus test adaptation.

### Tier A — high value, low risk (mechanical consolidation)

**R1. Extract the completion decision.** One `apply_completion_decision(session, game_id, failed_ply_count, current_attempts, job_id, *, source_tag) -> bool` housing Path A/B/C plus the guarded `eval_jobs` stamp. Replaces the three verbatim copies (D1). Any future change to retry semantics happens once. *Effort: small. Risk: minimal — the three copies are already line-identical apart from the Sentry tag.*

**R2. Retire the Gen-1 protocol.** Confirm fleet upgrade (log `worker_schema_version` / worker-id on `/submit` hits for a week; the fleet is 3 known boxes), then delete `/lease`+`/submit`, `_apply_submit`, and the worker's dead `_handle_full_ply_response`. `eval_remote.py` collapses toward one full-ply lease + one full-ply submit. *Effort: small-medium (mostly test pruning). Risk: low, gated on the traffic check. Also decide `/flaw-blob-*`'s future: it remains necessary while tier-4 backfill debt exists, but it should be documented as the second candidate for retirement once the blob backlog drains and go-forward games are all atomic.*

**R3. Replace delete-then-insert with a per-ply diff/upsert in `_classify_and_fill_oracle`.** Compute the desired flaw set, then: upsert changed/new plies (preserving blob/tag columns unless the submit carries fresh ones), delete disappeared plies. Deletes `_snapshot_preserved_flaw_blobs`/`_restore_preserved_flaw_blobs` and the whole class of 8D-style bugs. *Effort: medium. Risk: medium — this is the authoritative write; needs the existing endpoint test suite plus a dedicated equivalence test (old vs new final table state across the incremental-retry scenarios). Highest-leverage structural fix in the review.*

**R4. Unify the classify preamble.** One helper: `load_positions_with_overlay(game_id, pos_eval) -> (game, positions)` + classify once per tick and thread the `flaw_result` through the PV-recovery/second-best/blob/sentinel helpers instead of each re-classifying (D3, P2). Cuts up to 4 redundant classify+load rounds per game. *Effort: small-medium. Risk: low; pure refactor with identical inputs.*

**R5. Collapse `EnginePool` acquisition to one generic method** (`_with_worker(fn)` or parameterize by analyse kwargs + result adapter), keeping the four public `evaluate_*` signatures (D4). *Effort: small. Risk: minimal.*

**R6. Parameterize the ES lottery.** One two-stage lottery function taking (user predicate, game predicate, recency column, constants) serving tier-3 and tier-4 (D5). *Effort: small. Risk: low — SQL is already param-bound; keep the existing per-tier constants.*

### Tier B — structural hardening

**R7. Formalize the drain/router boundary.** Move the submit orchestration (`_apply_atomic_submit` body, post-R1/R3/R4) into the service layer — e.g. a new `app/services/eval_apply.py` exposing `apply_full_eval(...)` consumed by both `_full_drain_tick` and the router — so `eval_remote.py` stops importing 20 private helpers and returns to being an HTTP layer per the router convention. Consider splitting `eval_drain.py` (2,986 lines, 5 concerns) along the same seam: entry lane / full lane / shared write path. *Effort: medium (mostly moves). Risk: low.*

**R8. Durable import-job guard.** Create the `import_jobs` row in the request handler (status `pending`) and add a partial unique index on `(user_id, platform) WHERE status IN ('pending','in_progress')`; the in-memory registry stays as the progress cache. Closes the restart/multi-process double-import window (F5) and the "job exists only in memory" window. *Effort: small (one migration + handler reorder). Risk: low.*

**R9. Entry-drain all-fail circuit breaker** — mirror WR-05 (already triaged fix-soon; F4). *Effort: tiny.*

**R10. Stream chess.com archives.** Replace whole-month `resp.json()` with incremental parsing, or at minimum bound the buffer and document the cap; share the retry/backoff envelope between the two clients while in there (P1, D8). *Effort: small-medium. Risk: low.*

**R11. Gate or telemeter `worker_schema_version`.** Minimum: a Sentry/log counter of version per submit so fleet staleness is visible; optionally 426-reject versions below a floor once R2 lands (F8). *Effort: tiny.*

### Tier C — worth deciding, cheap either way

**R12. Delete dead weight**: tier-2 lane (or write down the concrete future mode that justifies keeping it), `hashes_for_game`, the `chesscom_to_lichess` future-use tables, the caller-less hybrid (§5.4). *Effort: tiny.*

**R13. Fix `_normalize_chesscom_result`'s draw fallback** (F7): unknown combinations should log + Sentry and map to a explicit `unknown` result rather than silently becoming draws. *Effort: tiny.*

**R14. Tier-3 double-claim**: cheapest fix is reusing the entry-lease pattern (nullable `full_eval_lease_expiry`/`leased_by` columns + TTL predicate in the lottery WHERE). Only worth it if fleet size grows; at 3 workers the waste is bounded and the code comment already documents the escalation path. *Recommend: defer, keep documented.*

**R15. Minimal fleet visibility**: a `worker_heartbeats` table (worker_id, version, last_seen, counts) updated on each lease is ~30 lines and answers "how many workers are live" without a registry system. Per-worker tokens/rotation only becomes worth it if the volunteer fleet actually grows beyond personally-known operators. *Recommend: the heartbeat table yes, token infrastructure no for now.*

**R16. Comment archaeology**: when touching functions under R1-R7, move phase/seed provenance into the git/PR record or a design note and keep in-code comments to live invariants (post-move shift, session rule, sentinel semantics). Not a standalone task — apply opportunistically.

### Explicitly *not* recommended

- **Merging the entry and full lanes** — the cost asymmetry justifies both (§6).
- **Changing the post-move storage convention** — it permeates everything, matches lichess semantics, and the single-shift-site discipline (`_post_move_eval`) contains it well.
- **A message-queue/broker rewrite** of the scheduling layer — Postgres SKIP LOCKED + derived lotteries is the right tool at this scale and is the best-functioning part of the system.
- **Rewriting the worker protocol as WebSocket/streaming** — polling with a 4-rung ladder at 1s idle sleep is simple, debuggable, and nowhere near a bottleneck.

---

## 8. Suggested sequencing

R1 → R4 → R3 → R7 form a natural dependency chain (each makes the next smaller); R2 can run in parallel after the fleet-traffic check; R8/R9/R13 are independent quick wins. A single milestone-sized effort covering Tier A + R7-R9 would remove roughly a third of `eval_remote.py`, meaningfully shrink `eval_drain.py`, and eliminate the two seams (completion triplication, snapshot/restore) that produced most of the recent production incidents.
