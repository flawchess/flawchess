---
id: SEED-022
status: superseded
superseded_by: SEED-023
superseded_on: 2026-05-20
superseded_reason: First-principles re-read during a /gsd-explore session on 2026-05-20 identified the import-time Stockfish eval pass *inside the per-batch transaction* as the structural OOM driver, making this seed's profile-then-mitigate sequence (Phase 91 profiling → Phase 92α/β tuning → Phase 93 admission control) diagnostic-without-payoff. SEED-023 replaces it with the direct architectural fix (two-lane import). The diagnostic narrative below is retained for history.
planted: 2026-05-20
planted_during: v1.17 (post-Phase-90 stress test + same-day code/config review)
trigger_when: before opening signups to a wider audience (concurrent imports become the norm), OR if a production user with a >15k-game account reports a stuck/failed import, OR before the next deliberate growth push. Also reconsider whenever the import pipeline, Stockfish eval pass, or postgres tuning is touched.
scope: medium-large (likely multi-phase — profiling is small; mitigation phases depend on what the profiling shows)
priority: high (gates concurrent multi-user adoption)
references:
  - logs/import-stress-20k-each-2026-05-20.log   # full per-30s memory trace of the 2026-05-20 stress test
  - .planning/phases/90-import-pipeline-memory-leak-fix-resilience/   # leak fix this seed validates
  - SEED-018                                     # the original leak diagnosis (closed; fix shipped in Phase 90)
  - SEED-017                                     # earlier resilience hardening (closed; superseded by SEED-018)
---

# SEED-022: Import concurrency headroom — survive 2× concurrent 20k-game imports and leave room for more concurrent users

## Goal

Two concurrent 20k-game imports (one chess.com, one lichess) must complete successfully on the current production hardware, and the system must have headroom for additional concurrent importers without OOM-killing Postgres. The 2026-05-20 stress test proved we are not there yet.

## Why This Matters

Phase 90 fixed the per-batch SQL-cache memory leak (SEED-018) and added resilient failure-state recording (the FLAWCHESS-56 carry-forward from SEED-017). Both fixes are real and were validated in production on 2026-05-20. But the post-fix capacity test exposed a *different* limiter: even with a clean backend memory plateau, the combination of two concurrent imports + Postgres working memory + transient batch-time allocations exceeds the box's RAM + swap budget over a long run and OOM-kills Postgres.

The user-stated goal: *"import these games without issues, and have resources for more users importing concurrently."*

## What We Did and What We Saw (2026-05-20 stress test)

**Setup.** Phase 90 deployed to production at 2026-05-20 ~19:55 UTC. A test user (user_id=95, fresh guest account, zero prior games) triggered two concurrent imports from the UI: lichess (target ~20k games) and chess.com (target ~20k games). Memory and job progress were polled every 30 s from a local workstation via SSH (`docker stats` + `pg_stat_activity` + `free -m` + `import_jobs` rows) and written to `logs/import-stress-20k-each-2026-05-20.log` (441 lines, full T+0 → OOM).

**Baseline (before imports).**
- backend RSS: 970 MB
- postgres RSS (cgroup): 2.23 GB (page cache warm from prior workload)
- system avail: 3.5 GB
- swap: 258 MB / 4 GB

**Steady-state during the run (~T+10 min onward).** Backend RSS plateaued at **1.36–1.42 GB** across 11 samples — no creeping growth, occasional shrinkage. This is the Phase 90 leak fix doing exactly what it was meant to do. Postgres oscillated 4.3–5.4 GB (cgroup-attributed; mostly reclaimable page cache, see below) as the kernel and Postgres negotiated cache vs anon, with swap absorbing the slack.

**End of run (T+~28 min, 20:23:32 UTC).** OOM-killer fired. Killed Postgres (PID 650396):
```
oom_kill: Killed process 650396 (postgres)
  total-vm:3.7G  anon-rss:447 MB  shmem-rss:476 MB
  swap:7276 KB   oom_score_adj:0
```
Both import jobs landed in `failed` status with informative SQLAlchemy `InterfaceError: cannot call PreparedStatement.fetch(): the underlying connection is closed` — exactly what Phase 90's failure-recording-with-retry was designed to capture (on 2026-05-16, the same failure mode left jobs stuck `in_progress` forever).

**Where the games landed before the kill:**
- lichess: imported=9058 / fetched=16199 (~45 % of target)
- chess.com: imported=8940 / fetched=8951 (fetcher and processor in lockstep)

**Time-to-OOM:** ~28 min from import start. Swap monotonic climb began at ~T+18 min; kernel held the system together for another ~10 min via aggressive page eviction before exhausting swap.

## What This Test Validated

1. **Phase 90 backend leak fix is solid.** Backend RSS plateau over 22 minutes of dual import — no creeping growth, occasional shrinkage. The per-batch unique-SQL leak diagnosed in SEED-018 is gone.
2. **Phase 90 resilient failure-state recording works end-to-end.** Postgres got OOM-killed mid-transaction, dropped the backend's connections, and the retry-on-DB-recovery path persisted `failed` status + the actual `InterfaceError` to both jobs. On 2026-05-16 this same scenario left jobs stuck `in_progress`. Confirmed fixed in real production fire.
3. **The OOM victim was Postgres, not the backend.** The backend container survived (`Up 36 minutes`); Postgres got the SIGKILL. Postgres also auto-restarted inside its container, so the system as a whole recovered without manual intervention.

## What This Test Did NOT Show (corrections from earlier drafts of this seed)

Two hypotheses I committed to in an earlier draft of this seed (and in the live-chat narration during the test) **did not survive code-and-data scrutiny.** Documenting them here as anti-claims so we don't redo the analysis:

### Anti-claim 1: "7k games piled up in an in-memory producer-consumer queue on lichess." FALSE.

There is **no explicit queue** between the lichess fetcher and the batch consumer. `import_service.py:582` is a plain `async for game_dict in game_iter` and `lichess_client.py:186–188` does `yield normalized` immediately followed by `on_game_fetched()`. Under that pattern the producer is parked at its `yield` whenever the consumer is awaiting `_flush_batch_with_progress`; the gap between `games_fetched` and `games_imported` should never exceed `_BATCH_SIZE` (12 games).

The observed 7,141-game gap (fetched 16199 vs imported 9058) is **almost certainly the lichess stream-retry path double-counting `on_game_fetched`**: the run logged one warning, `Lichess fetch for FaustiOro failed (attempt 1/3), retrying in 5s: peer closed connection without sending complete message body`, and on retry the client restarts the stream. Each restarted game fires `on_game_fetched` again → `games_fetched` over-counts; the unique `(platform, platform_game_id)` constraint dedupes at insert → `games_imported` reflects reality.

**Implication:** a "bounded queue" fix has nothing to bound. The earlier proposal A in this seed (capping a producer-consumer queue) is **withdrawn**. A real adjacent fix here would be: stop double-counting `games_fetched` on stream retry (make `on_game_fetched` idempotent via a seen-id set, or resume with a `since=` checkpoint so the retry doesn't re-yield already-seen games). That's a UX-correctness fix worth ~a `/gsd-fast`, not a memory mitigation.

### Anti-claim 2: "Postgres holds 5.4 GB of irreducible memory and dropping `shared_buffers` will free GBs." FALSE.

Live config check (2026-05-20, post-OOM):
- `shared_buffers = 2 GB` (262,144 × 8 KB, set via command-line at 25 % of 7.6 GB)
- `effective_cache_size = 6 GB` (planner hint only — no real memory cost)
- `work_mem = 8 MB` (per operation per connection; fine at our connection count)
- `maintenance_work_mem = 64 MB`, `wal_buffers = 16 MB`, `temp_buffers = 8 MB` (postgres defaults)
- `max_connections = 100` (high for a 7.6 GB box but irrelevant at current load)
- `huge_pages = try` (THP enabled — see Finding A below)

Per the OOM-kill log, postgres `shmem-rss` at the moment of kill was **476 MB**, not 2 GB. Shared_buffers is a virtual reservation; only touched pages become resident. The ~5.4 GB shown in `docker stats` is dominated by reclaimable page cache that the kernel could not evict fast enough as swap exhausted. **Dropping `shared_buffers` 2 GB → 1 GB would save at best ~240 MB resident under load** — useful but not transformative.

## What the OOM Actually Looked Like (the honest picture)

Total resident at OOM ≈ 7.0 GB out of 7.6 GB RAM; swap 4.0 / 4.0 GB (exhausted). Component breakdown:

| Bucket | Size at OOM | Reducibility |
|---|---|---|
| Backend RSS | 1.48 GB | plateau, no leak (Phase 90 holds) |
| Postgres anon-rss + shmem-rss | ~920 MB | partly tunable (shared_buffers, work_mem) |
| Postgres page cache (cgroup-attributed) | ~4.5 GB | reclaimable, but reclaim couldn't keep up |
| Caddy + umami + other | ~150 MB | mostly idle |
| Swap | 4.0 GB | exhausted |

**Why the OOM-killer fired** is best explained as a *reclaim-vs-allocation race*, not a single bloated process: swap monotonically climbed across the run as the kernel evicted anon pages; eventually swap exhausted; the next anon allocation forced the OOM scorer to pick a victim, and Postgres (largest oom_score under sustained anon pressure) lost. We do **not** currently know which specific allocations were driving the anon-page growth that filled swap — that is exactly what Phase 91 is for.

## New Findings From The Post-OOM Config Audit

### Finding A: Transparent Huge Pages allocating 786 MB

`/proc/meminfo` shows `AnonHugePages: 804864 kB` (~786 MB) currently allocated, with `huge_pages = try` in postgres. On memory-constrained hosts THP is known to hurt reclamation: huge pages must be split before swap-out, and THP can fragment the page-cache eviction path. Disabling THP for postgres (`huge_pages = off`) and possibly at the host level (`echo never > /sys/kernel/mm/transparent_hugepage/enabled`) is a standard recommendation for sub-16 GB Postgres boxes. Possibly meaningful — needs the same controlled test to verify. Listed as a candidate mitigation (D below).

### Finding B: Backend RSS now sits at 1.56 GB at idle, ~590 MB above pre-test baseline

Pre-test cold-start backend was 970 MB; post-OOM-recovery with no imports running it is 1.56 GB. This is almost certainly **CPython's pymalloc holding freed-but-not-returned-to-OS arenas**, not a memory leak (pymalloc only releases arenas when entirely empty, which is rare in long-running async workers). It is not actionable as a "fix," but it is operationally important: **the backend's working baseline after a heavy import is permanently elevated until the container restarts.** If a second heavy workload arrives, the available headroom is ~590 MB smaller than it was on a fresh container. The simplest mitigation is a periodic backend restart cadence (e.g., daily or after N failed imports) — small operational fix, not a code phase.

## What Importing-Without-Issues + Concurrent-User-Headroom Probably Requires

Ranked by **expected leverage** after the corrections above. All non-trivial code items are deferred until Phase 91 produces evidence.

### A. (WITHDRAWN) Bounded producer-consumer queue on lichess

See Anti-claim 1. There is no queue to bound. Replaced by:

### A′. Idempotent `on_game_fetched` / stream-retry resume

UX correctness, not memory: stop the lichess stream-retry from re-counting games in `games_fetched`. Use a per-job seen-id set, or resume the lichess stream with `since=<max(played_at) so far>` so the retry doesn't re-yield previously-seen games. Tiny scope (`/gsd-fast` or `/gsd-quick`). Cleans up the misleading `fetched > imported` discrepancy users see in the import progress UI. Does not move the OOM needle.

### B. Per-batch memory profiling (Phase 91 — see ROADMAP)

The only honest next step. Without `tracemalloc` snapshots at batch boundaries + per-batch RSS deltas + a parallel postgres process-RSS sampler, every mitigation below is a guess. Phase 91 is small (instrumentation only, no behavior change, env-gated) and intentionally produces no fix on its own — it produces a report that says *"here is where memory actually went during a 2× 20k import."* That report selects which of C / D / E / F to do next.

### C. Defer the per-batch Stockfish eval pass out of the import critical path

Today `_flush_batch` Stage 4 fans out Stockfish evals *inside the import transaction* — the import can't commit (and the progress counter can't increment) until all evals for the batch complete. This is what creates multi-minute commit gaps when evals run long. Persist position rows immediately on import; schedule eval as a follow-up background pass (reusing `backfill_eval.py` machinery or a long-lived background task). Eval becomes eventually-consistent; user sees games + WDL stats immediately; eval-dependent endgame metrics fill in within minutes.

Cost: larger refactor (touches `_flush_batch`, adds an `evals_pending` flag or similar, adds a background worker). Likely worth doing *if* Phase 91 confirms that eval-time allocations or eval-induced batch duration is the dominant pressure source. May also let `_BATCH_SIZE` rise back from its post-incident 12.

### D. Postgres tuning sweep

Modest leverage on its own but cheap to try. Candidate changes:
- `shared_buffers` 2 GB → 1 GB (saves up to ~240 MB resident under load; trades some query-cache benefit for kernel page-cache flexibility).
- `huge_pages = off` for postgres + disable THP at host level (better reclamation under memory pressure; see Finding A).
- `max_connections` 100 → 20 (we use ≤5; each connection has ~10 MB overhead; small win at idle, irrelevant at OOM time).

Estimated combined headroom: 300–600 MB. Worth a small phase *after* Phase 91 identifies it as worthwhile.

### E. Hardware ceiling — explicitly rejected by user (2026-05-20)

Listed for completeness only. The Hetzner box could be upgraded to 16 GB RAM trivially (non-disruptive resize, a few euros/month). User explicitly declined this lever and prefers to make the code fit the budget. Honour that constraint in all downstream phases.

### F. Concurrent-import admission control

Gate concurrent active imports at the backend (e.g. "at most K=2 in-flight imports per backend instance, queued FIFO past K"). Turns a hard-OOM failure across multiple users into a graceful queueing experience. Becomes more important as the user base grows. Small phase. Sensible to ship *after* the per-import footprint is well understood from Phase 91 + C/D so we know what K is safe.

### G. Operational: scheduled backend restart cadence

See Finding B. A cron-style restart of the backend container (daily, or after N completed imports) returns the working-set baseline to ~970 MB. Trivial — a one-line addition to a systemd timer or compose-level healthcheck. Useful belt-and-braces regardless of which code mitigations land.

## Acceptance Criteria For The Resulting Phase(s)

- Re-run the same 2× 20k stress test on production and both imports complete with status `completed` and `games_imported` within ~5 % of target (lichess can lose a few to platform-side rate limits).
- During the run, backend RSS plateaus (≤ 1.6 GB sustained), Postgres `anon-rss + shmem-rss` stays below ~1.2 GB sustained, and swap consumption never exceeds 50 % of allocated swap.
- A third concurrent import (e.g. a 5k-game small account) can be triggered mid-run and complete without OOM.
- All operational state (job status, error messages) survives any partial failure — same contract Phase 90 established.
- No RAM upgrade (per user constraint 2026-05-20).

## Suggested Sequence

1. **Phase 91 — Import memory profiling instrumentation** (small; drafted in ROADMAP). Mandatory predecessor. No behavior change. Produces the evidence that selects the next phase.
2. Then **one of** (depending on what Phase 91 shows):
   - **Phase 92-candidate-α — Defer Stockfish eval out of import critical path** (option C — larger phase, biggest single concurrency lever if eval is the spike driver).
   - **Phase 92-candidate-β — Postgres tuning + THP off** (option D — smaller phase if the spike is dominated by postgres anon/shmem behaviour).
3. **Phase 93 — Concurrent-import admission control** (option F — small; the explicit "more concurrent users" half of the goal).
4. **Out-of-band fixes** (each `/gsd-fast` or `/gsd-quick`): A′ (idempotent on_game_fetched), G (backend restart cadence). Can land any time; not on the critical path.

The discuss-phase for Phase 91 should not need to debate scope much — the seed and the Phase 91 ROADMAP entry already lock the goal and the deliverable.
