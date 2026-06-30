---
id: SEED-071
status: dormant
planted: 2026-07-01
planted_during: post-v1.30-deploy prod investigation. After deploying the v1.30 Forcing-Line Tactic Gate milestone (phases 141-145), remote eval workers began intermittently failing with ReadTimeout on POST /eval/remote/submit. Root-caused live, on prod, to the synchronous server-side MultiPV-2 continuation eval that Phase 142 added to the live submit path. NOT a Phase 145 bug.
trigger_when: soon — this is an active prod pain point (submit timeouts under any real load, e.g. while a user's imported games are tier-3 draining). Promote as a single backend phase when the v1.30 corpus rollout settles, or sooner if submit timeouts worsen. Stopgap in place: bump worker HTTP_TIMEOUT_S 30 -> 120.
scope: Medium — backend remote-eval submit path only (app/routers/eval_remote.py::_apply_submit, app/services/eval_drain.py::_build_flaw_multipv2_blobs). No DB schema change. Either move blob assembly off the synchronous submit, or offload continuation eval to the worker via the existing Phase-145 lease/submit token machinery.
---

# SEED-071: Live submit path runs forcing-line continuation eval on the server, blocking the response → ReadTimeouts under load

## Why This Matters

Phase 142 (MultiPV-2 foundation, shipped in v1.30) made **every remote-worker submit run
Stockfish on the server, inline, before responding.** On `POST /eval/remote/submit`:

```
_apply_submit (app/routers/eval_remote.py:271)
  -> _build_flaw_multipv2_blobs (app/services/eval_drain.py:1161)
      -> asyncio.gather(engine_service.evaluate_nodes_multipv2(b) for b in gather_boards)   # line 1243-1246
```

For each flaw it walks the *missed* and *allowed* PV lines (up to `PV_CAP_PLIES = 12` nodes each)
and evaluates every continuation node at `_NODES_BUDGET = 1_000_000` nodes on the server's shared
Stockfish pool. A game with N flaws ⇒ ~22·N server-side 1M-node evals **before the submit returns**.

**Observed on prod (2026-07-01, right after the v1.30 deploy):**
- A *single* worker (`remote_eval_worker.py --workers 12 --worker-id ai-slim`, latest `main`)
  intermittently failed with `ReadTimeout` on `/submit` (Sentry FLAWCHESS-7Y). v1.29 — which had
  no server-side continuation eval on submit — had **zero** such failures with 5 workers attached.
- Flaw-light games succeeded fast; flaw-heavy games (e.g. 1552008, 893535) exceeded the worker's
  **30s** `HTTP_TIMEOUT_S` read timeout. Classic per-flaw-count intermittency.
- Server looked deceptively idle the whole time: **DB idle** (no active queries, no lock waits),
  **uvicorn ~11% CPU** (single worker, `uvicorn app.main:app`, no `--workers`). The real work is in
  the **8 `SCHED_IDLE` Stockfish subprocesses** (`CLS=IDL`, ~81% CPU each) — invisible if you only
  look at the API process or the DB. Stockfish being `SCHED_IDLE` is correct (it yields to the API),
  so it is NOT the cause; the cause is that the submit response *waits* on that engine work.
- Made worse by concurrent **tier-3 drain** (a user had imported games): the import drain and the
  submit continuation evals contend for the same 8-engine pool, so submits queue behind the drain.

Why this is a real architectural gap: Phase 145 offloaded the MultiPV-2 continuation compute to the
remote fleet **only for the backfill of old games** (the `/eval/remote/flaw-blob-lease` + `/flaw-blob-submit`
contract). The **live** submit path was never moved off the server — it still does the continuation
analysis synchronously in `_apply_submit`. Under any real prod load that inline engine work is the
bottleneck and surfaces as worker submit timeouts.

## Stopgap (already advised, not a fix)

Bump the worker's `HTTP_TIMEOUT_S` 30 -> 120 so submits complete (the work isn't lost — timed-out
submits retry, and may already be committing past the client timeout). Note `--workers 12` locally
barely helps now: the server pool is the bottleneck, so a lower local worker count is fine.

## Proposed fix (one backend phase)

Pick one (decide during plan-phase):

1. **Async-ify blob assembly on the live path** — return the submit *before* `_build_flaw_multipv2_blobs`,
   and do blob assembly + the gated retag in a background task / the existing drain loop. The submit
   becomes a pure DB write (fast); the gate work happens off the request. Simplest; keeps engine work
   on the server but unblocks the worker.
2. **Offload continuation eval to the worker** — have the live worker compute the continuation nodes
   (reusing the Phase-145 lease/submit token machinery), so the server never runs Stockfish on submit.
   More work, but removes server-side engine load from the live path entirely and unifies live + backfill.

Either way: the submit handler must stop blocking on `asyncio.gather(evaluate_nodes_multipv2(...))`.

## Pointers

- `app/routers/eval_remote.py` — `_apply_submit` (lines ~195-310), call site at 271-274.
- `app/services/eval_drain.py` — `_build_flaw_multipv2_blobs` (1161), `_run_multipv2_pass` (1316),
  `_batch_update_flaw_pv_lines` (1282).
- `app/services/engine.py` — `evaluate_nodes_multipv2` (608), `_NODES_BUDGET`/`PV_CAP_PLIES` (99/104).
- `scripts/remote_eval_worker.py` — `HTTP_TIMEOUT_S = 30.0` (61), submit at `_handle_full_ply_response` (279).
- Sentry: FLAWCHESS-7Y (ReadTimeout on /submit, env=development, worker ai-slim).
