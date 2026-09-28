---
id: SEED-172
status: dormant
planted: 2026-09-28
planted_during: v2.19, Phase 225 planned (SEED-170); standalone performance review session
trigger_when: when analysis backlog throughput, worker fleet cost, or API latency during eval submits becomes the priority
scope: small-to-medium (two quick wins, then one phase for engine-call reductions). Re-measure first.
---

# SEED-172: Server analysis pipeline throughput (fewer engine calls, Maia fp32, not a Rust port)

## Why This Matters

Stockfish is ~98-99% of the CPU spent analysing a game (~160-200 engine calls per game at 1M
nodes, ~160 CPU-s per game at prod speed). Post-processing (flaw classification, tactic
tagging, zobrist, position classifier) is 15-35 ms per game. **A Rust/C port of the Python
chess code would save ~0.05 s per game**, so it is not worth it for throughput. The gains are in
making fewer or cheaper engine calls, plus one Maia fix that also removes event-loop blocking
on the API server.

## Measured (2026-09-28, Ryzen 7840HS)

**RE-MEASURE BEFORE ACTING.** The box was under load 14-21 (local 8-engine SCHED_IDLE
`remote_eval_worker`); single-thread SF NPS was ~500-650k vs prod's ~1M nodes/s reference
(engine.py "spike 002" comment). The dev-DB sample query was blocked, so the game sample was
7 club games from `temp/` plus `fixtures/tagger`. Scripts:
`.planning/research/perf-profiling-2026-09-28/`.

| Stage | Cost | |
|---|---|---|
| SF 1M nodes, MultiPV 1/2/5 | 2.08 / 1.98 / 1.68 s per position (loaded box); ~1.0 s on prod | measured / prod ref |
| SF depth 15 (entry lane) | 0.25 s, ~112k nodes | measured |
| Engine calls per game | 163-202 (2.3-2.4 per ply): ~1.0/ply full pass, 31-101 blob-walk nodes, 25-57 second-best re-searches | measured |
| Engine CPU per game | 322 CPU-s loaded box; ~160 CPU-s at prod speed | measured / estimate |
| Worker Python CPU (UCI parse, hint, walk) | 2.2-2.65 s/game; UCI parsing 9-14 ms/call (~1% of engine time) | measured |
| `classify_game_flaws` incl. tactics | 15-20 ms/game (~3-4 flaws); `detect_tactic_motif` 0.73 ms/call | measured |
| `process_game_pgn` (import) | 13.9 ms/game (168 us/ply) | measured |
| Maia `score_move` (fp16, shipped) | 146-168 ms/call, 6-13 calls/game = 1-2 s/game on the API event loop | measured |

Share of engine time: full pass ~45%, blob walks ~20-45%, second-best re-search ~25%.

## Candidate work (decide in discuss-phase)

Quick wins (could be `/gsd-quick`):
1. **Move Maia off the event loop**: `score_move` runs synchronously inside the async submit
   handler (`eval_apply.py` ~2443). Wrap in `asyncio.to_thread` (onnxruntime releases the GIL).
   Pure latency fix, no behavior change.
2. **Maia fp32 on the server: 2.8x at 1 thread, 5.3x at 4 threads.** Native CPU EP has poor fp16
   kernels and fp16 does not scale with threads. Measured 146 -> 52 ms (t=1), 149 -> 28 ms (t=4).
   Played-move probability drift: max 0.0041, mean 0.0009, about the existing ORT parity epsilon
   (0.003844), far below gem/great cut-offs (0.20 / 0.50). **Policy decision needed:**
   `frontend/public/maia/README.md:10` pins the model "unmodified" (MAIA-01, AGPL), the server
   checks its SHA-256 (`_model_bytes_ok`), and D-04 relies on byte-identical bytes client/server.
   Preferred option: upcast fp16 -> fp32 **in memory at load time** (file and SHA untouched);
   alternative: pin a second derived file. Either way re-run the ORT parity check.
3. `position_classifier.py:230` `_compute_mixedness`: `bin().count("1")` -> `int.bit_count()`
   (~5-10% of import CPU). Trivial.

Engine-call reductions (a phase; each changes outputs, so gate on quality):
4. **Cheaper second-best search, ~20% of engine time.** The remote worker re-runs a full 1M-node
   MultiPV-2 search on every ply where played == best (~45 positions/game), but only 6-13 pass
   the gem/great gate. Options: 200k-node runner-up search, a cheap pre-gate, or a sticky
   same-worker re-search with a warm TT. Verify first whether the local drain path (MultiPV-2 on
   every ply already) makes this pass redundant there. Needs a gem/great agreement check.
5. **Cheaper blob walks, ~15-30%.** Consecutive PV positions are searched cold, in parallel, at
   1M nodes each (up to 12 per missed/allowed line). Options: lower node budget for k >= 2,
   shorter `PV_CAP_PLIES`, or sequential walk on one warm engine. Affects tactic-gate
   calibration: re-run the tactic-tagger precision gate.
6. **Worker oversubscription (SMT)**: typically +15-25% throughput, currently blocked by
   wall-clock timeouts. Since the node cap bounds the work, scale the timeout with measured NPS.
   (SF build variant avx2 vs avx512icl/vnni512/bmi2: within ~5% on Zen4, not worth chasing.
   Hash 32 MB is fine at 1M nodes.)
7. **Instrumentation**: `worker_heartbeats` holds only lifetime counters; there is no Sentry
   tracing. Add per-call engine time + nodes per pass type so the call mix above can be tracked
   in prod before and after items 4-6.

Low priority:
8. `process_game_pgn` runs synchronously on the event loop during import
   (`import_service.py` ~1665). Moving it to a process pool matters more for API latency than a
   Rust port. shakmaty via PyO3 would make import ~10-30x faster (14 -> ~1 ms/game) but is high
   effort for a cost that does not dominate.

## Won't help

- Rust/C port of python-chess code, zobrist, classifier, tactic detector: <0.05% of CPU.
- Stockfish build variant switch: <=5-10%.
- Maia batching server-side: batch 16 barely helped fp16 (~130 ms/position).

## Re-measurement plan

1. Idle box (stop local `remote_eval_worker`) or measure on a fleet worker; confirm ~1M nps.
2. Sample 20-50 real games from prod (orchestrator runs the SELECT; subagents lack project MCP).
3. `prof_engine.py` for calls per game by pass type; `maia_fp.py` + `maia_threads.py` for item 2.
4. Better: land item 7 first and read the call mix from prod.

## Breadcrumbs

- `app/services/engine.py:94-109` (Hash 32, Threads 1, `Limit(nodes=1_000_000)`, 5 s timeout)
- `scripts/remote_eval_worker.py:276` (full pass), `:409-481` (blob walk), `:484-552` (second-best), `:555-586`
- `app/routers/eval_remote.py:457` (lease, `DEDUP_MAX_PLY` 20), `app/services/eval_drain.py:1331`
- `app/services/eval_apply.py:2443`, `app/services/maia_engine.py:109`
- `app/services/position_classifier.py:230`, `app/services/zobrist.py:138`, `app/services/import_service.py:1665`
- Browser-side counterpart: SEED-171
