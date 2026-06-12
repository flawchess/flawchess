---
phase: 116-all-ply-engine-core
plan: "03"
subsystem: backend-service
tags: [stockfish, engine, memory-accounting, documentation, queue-07]

# Dependency graph
requires:
  - phase: 116-all-ply-engine-core
    plan: "01"
    provides: "evaluate_nodes() at 1M-node budget, _NODES_BUDGET / _NODES_TIMEOUT_S constants"

provides:
  - "QUEUE-07 / D-116-12: measured per-worker RSS at 1M-node budget (dev box 2026-06-12)"
  - "Memory accounting comment in engine.py: N-workers x footprint + import + Postgres vs 4g math"
  - "D-116-13 deploy-at-6-then-soak plan documented in engine.py, docker-compose.yml, CLAUDE.md"
  - "Corrected stale comments: engine.py 'STOCKFISH_POOL_SIZE=4 to use all 4 vCPUs' (removed), docker-compose.yml 'up to 6' (updated), CLAUDE.md 'pool lowered' (clarified)"

affects: [117-eval-queue]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Memory accounting documented as deploy-time comment (same precedent as _BATCH_SIZE/_HASH_MB in CLAUDE.md)"
    - "RSS measured via /proc/<pid>/status VmRSS after warmup 1M-node searches"

key-files:
  created: []
  modified:
    - app/services/engine.py
    - docker-compose.yml
    - CLAUDE.md

key-decisions:
  - "Measured RSS at 1M-node budget (dev, 2026-06-12): 1w=277MB, 4w=1056MB, 6w=1586MB, 8w=2083MB (260 MB/worker); NNUE page-cache-shared confirmed (sub-linear)"
  - "Prod accounting: conservative 8wx368MB + 0.3GB FastAPI = ~3.24GB under 4g mem_limit, ~0.76GB headroom"
  - "D-116-13 (APPROVED 2026-06-12): ship at STOCKFISH_POOL_SIZE=6, soak ~24h, bump to 8 only if headroom confirmed + latency clean"

requirements-completed: [QUEUE-07]

# Metrics
duration: 25min (Tasks 1-2 in prior session + continuation; Task 3 checkpoint approved)
completed: 2026-06-12
---

# Phase 116 Plan 03: Memory Accounting + Pool-Size Docs Summary

**QUEUE-07 / D-116-12: measured per-worker RSS at 1M-node budget on the dev box, documented N-workers x footprint + import + Postgres accounting against the 4g backend container limit, corrected all three stale pool-size comments across engine.py / docker-compose.yml / CLAUDE.md**

## Performance

- **Duration:** ~25 min (Tasks 1-2 in prior session; Task 3 checkpoint approved by human)
- **Started:** 2026-06-12T18:20:28Z
- **Completed:** 2026-06-12T19:50:00Z
- **Tasks:** 3 of 3 complete
- **Files modified:** 3

## Measured RSS Numbers (QUEUE-07 evidence)

RSS measured by running EnginePool at 1M-node budget on the dev box (2026-06-12),
reading `/proc/<pid>/status VmRSS` after one warmup 1M-node search per worker:

| Workers | Total RSS | Per-Worker RSS |
|---------|-----------|----------------|
| 1       | 277 MB    | 277 MB         |
| 4       | 1056 MB   | 264 MB/worker  |
| 6       | 1586 MB   | 264 MB/worker  |
| 8       | 2083 MB   | 260 MB/worker  |

Sub-linear scaling (8 x 277 = 2216 MB estimated; actual 2083 MB) confirms the 125 MiB
NNUE net is OS page-cache-shared across workers from the same binary (Assumption A3).

## 4g Container Accounting (D-116-12)

Conservative prod accounting uses Phase 91's ~368 MB/worker baseline
(depth-15 import-time evals under full concurrent import load):

| Component | Estimate |
|-----------|----------|
| 8 workers x 368 MB (Phase 91 conservative) | ~2.94 GB |
| FastAPI/Uvicorn + active import pipeline | ~0.30 GB |
| **Total** | **~3.24 GB** |
| `mem_limit: 4g` headroom | **~0.76 GB** |

Dev-measured numbers at 1M-node budget are lower (8w=2083 MB = 2.03 GB), but prod
extrapolation from Phase 91 is used as the conservative bound for the accounting.

Conclusion: 8 workers fits within the 4g backend container limit with ~0.76 GB headroom.
The import-era OOM-kills needed ~3.7+ GB (combined import + oversized pool + no swap limit
before the hotfix). The current architecture has `memswap_limit: 4g` containing any OOM
to the backend container (auto-restarts in ~3s, as observed 2026-05-20 and 2026-05-21).

## Deploy Plan (D-116-13)

The plan documented in engine.py, docker-compose.yml, and CLAUDE.md is:

1. Deploy Phase 116 at `STOCKFISH_POOL_SIZE=6` (current prod value, stable for weeks).
2. Soak: monitor prod API p50/p90 and backend container RSS for ~24h with the full-ply
   drain running.
3. Raise to `STOCKFISH_POOL_SIZE=8` only if:
   (a) The accounting confirms ~0.76 GB headroom holds in practice, AND
   (b) API latency is clean (same check spike 002 performed at 6 workers).
4. If RSS is tighter than projected or latency degrades, stay at 6 permanently.

All Phase 116 throughput benchmarks (5.83 pos/s, ~8.4k games/day) were measured at
6 workers; they remain valid regardless of the 8-worker decision.

## Stale Comments Corrected

| File | Old Text | New Text |
|------|----------|----------|
| `app/services/engine.py` (line ~108) | "Prod sets STOCKFISH_POOL_SIZE=4 to use all 4 vCPUs" | Replaced with QUEUE-07/D-116-12 accounting block; current prod=6, target=8 contingent |
| `app/services/engine.py` (line ~77) | "prod STOCKFISH_POOL_SIZE=4 the pool reserved 4 * 64 = 256MB" | Clarified as "hotfix-era STOCKFISH_POOL_SIZE=4" |
| `docker-compose.yml` (line ~79) | "Sized for the CPX42 host with STOCKFISH_POOL_SIZE up to 6" | Replaced with Phase 116 accounting block: dev RSS, prod math, D-116-13 plan |
| `CLAUDE.md` (OOM-2026-05-16 bullet) | "STOCKFISH_POOL_SIZE lowered" (implied current) | "lowered to 4 (hotfix era only -- prod has since been raised to 6 stably)" |
| `CLAUDE.md` (new bullet) | -- | Added Phase 116 pool accounting paragraph mirroring _BATCH_SIZE/_HASH_MB precedent |

## Task Commits

1. **Task 1: Measure RSS + engine.py accounting comment** -- `ff06e9fb` (docs)
2. **Task 2: docker-compose.yml + CLAUDE.md corrections** -- `ddc90785` (docs)
3. **Task 3: Human go/no-go checkpoint** -- APPROVED 2026-06-12 (no code commit; decision recorded in SUMMARY + STATE.md)

## Accomplishments

- Ran `EnginePool` at 1M-node budget for 1/4/6/8 workers and captured per-worker RSS
  via `/proc/<pid>/status VmRSS` after NNUE warmup
- Added QUEUE-07/D-116-12 comment block above `_POOL_SIZE_ENV`/`_DEFAULT_POOL_SIZE` in
  `engine.py`: measured RSS table, conservative prod accounting, D-116-13 gate plan
- Corrected two stale engine.py comments (pool-size refs to CPX32 era)
- Updated docker-compose.yml backend memory comment with the measured accounting
- Corrected CLAUDE.md: "pool lowered" clarified as hotfix-era only; added Phase 116
  pool-accounting bullet citing measured RSS, prod math, and D-116-13 soak gate

## Deviations from Plan

None -- plan executed exactly as written. Task 3 was a planned blocking checkpoint; user approved the D-116-13 deploy plan on 2026-06-12.

## Known Stubs

None. This plan modifies documentation/comments only -- no data rendering or UI involved.

## Threat Flags

No new threat surface. Updates are documentation-only:
- T-116-09 (stale docs misleading a future deploy) -- mitigated: all three stale comments
  corrected to current prod reality.

---
*Phase: 116-all-ply-engine-core*
*Completed: 2026-06-12*

## Self-Check: PASSED

Files verified present:
- app/services/engine.py: FOUND
- docker-compose.yml: FOUND
- CLAUDE.md: FOUND
- .planning/phases/116-all-ply-engine-core/116-03-SUMMARY.md: FOUND

Commits verified:
- ff06e9fb: docs(116-03): measure RSS at 1M-node budget + update engine.py accounting -- FOUND
- ddc90785: docs(116-03): correct stale pool-size comments in docker-compose.yml + CLAUDE.md -- FOUND
- 3a395f42: docs(116-03): complete plan 03 tasks 1-2 + checkpoint summary -- FOUND (prior session)

Checkpoint approval: D-116-13 approved 2026-06-12 by user ("approved").
