# Phase 145: Corpus Backfill + Rollout - Context

**Gathered:** 2026-06-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Get the forcing-line-gated tactic tags live in production for **all** users' games — existing
and new, across **both** engine-analyzed and lichess %eval sources. Three moving parts:

1. **Backfill the missing MultiPV=2 blobs** across the corpus by leveraging the **remote worker
   fleet** (the bulk of the compute), not a server-local engine pass.
2. **Apply the gated tags** so the noise-reduced tactic tags become live.
3. **Record per-motif tactic chip counts before/after** to confirm the gate's noise reduction
   (SHIP-01, SHIP-02 / SC1–SC4).

**Locked direction (the founding directive for this phase):** the missing MultiPV blobs are
computed by the **remote workers**, not the server. This both honors the "that's where the bulk
of the work lies" intent and satisfies the roadmap's "no second EnginePool / no OOM" goal better
than a server-local pass would (no server engine work for the bulk at all).

**In scope:**
- A new remote-fleet **blob-only backfill job** (narrow: computes only the MultiPV=2 second-best
  for each flaw's PV-line nodes; no full re-eval, no re-classification).
- Backfill coverage spans **engine + lichess %eval** games with flaws missing blobs.
- Per-game gated retag at blob-submit time + a `retag_flaws.py --db prod` sweep for already-blobbed
  stale-tag games.
- Per-motif chip-count before/after monitoring.

**Out of scope (do not expand):** changing the gate logic or `ONLY_MOVE_WIN_PROB_MARGIN` (the final
margin is committed in Phase 144 — this phase consumes it), retuning the detector, raising
`STOCKFISH_POOL_SIZE`, any new tactic motif. New capabilities belong in their own phase.

</domain>

<decisions>
## Implementation Decisions

### Backfill mechanism (SHIP-01 / SC1)
- **D-01: Narrow blob-only remote job, NOT a resweep-style full re-arm.** Reject the
  `resweep_holed_games` re-arm (clearing `full_evals_completed_at` so the fleet re-drains the WHOLE
  game): it re-evaluates every ply, re-classifies flaws, and re-stamps oracle counts just to obtain
  second-best on the flaw plies — redundant compute and it risks shifting the flaw set (PV1 drift,
  142 flag). Instead, a narrow job computes **only** the MultiPV=2 second-best for each flaw's
  PV-line continuation nodes. The server already has each flaw's stored PV (the `game_positions.pv`
  string), so it reconstructs the PV walk and the boards locally — no re-analysis, no re-classify.
- **D-02: New tier-4 lottery, lowest priority.** The backfill is served by a new lease tier that
  fires **only when no tier-1/2/3 work remains**, gated by `EVAL_AUTO_DRAIN_ENABLED` like tier-3.
  Live analysis + the not-yet-analyzed backlog always win; the fleet drains the blob backfill purely
  on spare capacity. Self-pacing, never starves real-time work; finishes "eventually." Modeled on
  the existing tier-3 Efraimidis–Spirakis lottery (`_claim_tier3_derived`, `eval_queue_service.py`),
  which uses **no `eval_jobs` table** — it is a predicate-driven SQL lottery (`job_id=None` on those
  leases), so it self-dedupes by predicate.
- **D-03: Predicate = analyzed game with flaws whose `allowed_pv_lines IS NULL`** (the roadmap
  idempotency guard). Once a game's flaw blobs are written (or sentinel-marked, D-06), it stops
  matching → idempotency-by-construction. Double-claim under contention is acceptable (idempotent
  write — same as tier-3 D-4 residual-duplicate acceptance).

### Lease/submit contract (SHIP-01) — Option 2, dedicated schema
- **D-04: Dedicated token-keyed flaw-line lease/submit schema** (NOT a reuse of the per-game
  whole-game `LeaseResponse`/`SubmitRequest`). Rationale: the positions that need worker compute are
  **continuation nodes along each flaw's stored PV** (`(flaw_ply, "allowed"|"missed", node_k)`, up to
  `PV_CAP_PLIES=12` per line) — they are reached by pushing PV moves, so they are **not game plies**
  and have no `game_positions.ply` row. The existing ply-keyed schema would force overloading `ply`
  as a synthetic node index AND branching the safety-critical live `_apply_submit` handler anyway —
  the "less surface" saving is illusory and it adds blast-radius risk to live eval ingest. The
  dedicated schema carries honest keys (`{token, fen}` out, `{token, multipv2 result}` back; token =
  the server's `(flaw_ply, line, node_k)` reassembly key), isolates blob ingest from live eval
  submit, and mirrors the **Phase 123 entry-ply batch schema precedent** (`EntryLeasePosition`).
- **D-04a: Worker stays token-opaque (near-zero worker change).** The worker just evaluates the
  leased FENs at MultiPV=2 (it already does since Phase 142) and echoes the token + result. It does
  not need to understand flaws/lines/nodes — the server holds the token→blob mapping and reassembles
  on submit.

### Churn / poison-pill safety (SHIP-01 / SC1)
- **D-05: Old/un-upgraded workers are structurally excluded** — the backfill is its own endpoint, so
  an un-upgraded worker never calls it (calling the new endpoint **is** the capability signal). No
  worker-version negotiation needed. (This is why the *old-worker churn* risk from the discussion
  framing mostly dissolves under D-04.)
- **D-06: Sentinel blob write for un-fillable flaws.** When a flaw genuinely cannot produce a blob
  (no stored PV, terminal/unevaluable node), write a **sentinel JSONB value (empty array `[]`)**
  instead of leaving NULL. The lottery predicate is `IS NULL`, so a sentinel-written flaw stops
  matching → no endless re-lease. Self-cleaning, **no new column, no migration**. The gate / retag
  must treat `[]` as "no gate-eligible line" (empty PV → no forced nodes → no suppression). Research
  must confirm the gate handles `[]` gracefully.

### Tag application & sequencing (SHIP-02 / SC2)
- **D-07: Per-game gated retag INSIDE the blob-submit handler.** After the blob-submit writes a
  game's blobs, immediately run the single gated classify path (`_classify_tactic_gated`) for that
  game's flaws so tags update atomically as blobs arrive → **rolling rollout**, each backfilled game
  lands fully done (blobs + gated tags) with no end-of-backfill barrier. The isolation concern (vs
  the assemble-only ideal) is acceptable here because this endpoint is **transitional**: once the
  corpus is backfilled it goes quiet, and new games get blobs + gated tags from the normal full
  analysis (the 143 live gated path) anyway.
- **D-08: `retag_flaws.py --db prod` is still part of rollout (NOT redundant).** D-07 covers freshly
  **backfilled** (old, previously-no-blob) games. The sweep covers games that **already have blobs**
  (post-142 analyses) but were tagged **before** the gate went live in Phase 143 or before the final
  margin — a one-shot engine-free, idempotent, change-only-UPDATE sweep to align them. Order:
  blobs trickle in (fleet) + per-game retag (D-07) → one `retag_flaws.py --db prod` sweep for the
  already-blobbed stale-tag residual → snapshot after.

### Lichess scope (SC4)
- **D-09: The gate (and therefore blob backfill) covers lichess %eval games too.** The backfill
  predicate (D-03) spans **any** analyzed game (engine + lichess) with flaws having NULL blobs.
  Matches SC4's literal "the MultiPV pass is NOT gated on `lichess_evals_at` (second-best is new
  data, not a lichess freebie)." Lichess games need real engine second-best (PV-recovery
  MultiPV=2) — which is exactly the fleet work the lottery distributes. The gate then denoises
  tactic tags **uniformly** across both sources.
- **D-09a: RESEARCH FLAG (feasibility gate for D-09).** `_fill_engine_game_flaw_pvs`
  (`eval_drain.py` ~1009) and the related PV-recovery helper **no-op for lichess games**
  (`if is_lichess_eval_game: return`). So lichess flaws may **not** have stored engine PVs to walk.
  If so, the lichess blob backfill must **compute the flaw PV line first** (an engine PV pass), not
  just MultiPV=2 over existing PV nodes. Research MUST confirm whether lichess games carry stored
  flaw PVs before the lichess scope is planned; if they don't, the lichess job is a PV-pass +
  MultiPV-2 pass (bigger), or lichess coverage drops to a follow-up.

### Claude's Discretion (planner/researcher decide within the above)
- **SC3 monitoring (per-motif chip counts before/after):** the exact script/query, which tag
  columns to count, and the snapshot timing given the rolling rollout. Default intent: snapshot
  **before** any retag (current prod tag counts), then **after** the rollout is substantially
  complete. A committed `reports/` markdown (benchmarks / db-report / retag convention) is the
  natural deliverable.
- **Backfill progress / observability signal** — how to count flaws still `allowed_pv_lines IS NULL`
  (engine + lichess) to know when the backfill is "substantially complete" and when to run the D-08
  sweep + the "after" snapshot.
- Exact tier-4 lease/submit endpoint paths, Pydantic schema names and token encoding, the lottery's
  ES weighting reuse vs a simpler pick, batch size per lease, and prod pacing.
- Dev-first validation (run the lottery + blob job + per-game retag end-to-end on the dev DB / a dev
  user before `--db prod`) is recommended; planner decides the exact gate.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec & requirements (authoritative)
- `.planning/notes/tactic-forcing-line-gate.md` — design source; §"Storage" (engine-free re-tag,
  blob shape) and §"Open knobs". **AGPL boundary: heuristics/constants/names only — copy NO
  lichess-puzzler source.**
- `.planning/REQUIREMENTS.md` §SHIP (SHIP-01, SHIP-02) — this phase's requirements.
- `.planning/ROADMAP.md` §"Phase 145" — the 4 success criteria this phase is graded on.

### Prior-phase context (locked, do not re-decide)
- `.planning/phases/142-multipv-2-engine-pass-eval-drain-remote-worker/142-CONTEXT.md` — locked blob
  shape (`b/bm/s/sm/su`, white-perspective cp), every-node storage, the additive remote-worker
  second-best contract (D-03), and **D-04 (old/un-upgraded worker leaves blobs NULL → THIS phase
  backfills the tail)** + **D-05 (eval-gap local recovery)** — the direct cause of the backlog.
- `.planning/phases/143-offline-re-tagger/143-CONTEXT.md` — the gate is already wired into the
  **live** classify path (`_classify_tactic_gated`), `retag_flaws.py` re-derives tags from blobs
  engine-free, `--margin` is threaded, change-only batched UPDATE + idempotency.
- `.planning/phases/144-user-28-a-b-validation/144-CONTEXT.md` — the **final
  `ONLY_MOVE_WIN_PROB_MARGIN`** is committed there; this phase consumes it (default rule: 0.35 unless
  the hand-check failed). Do NOT retune it here.
- `.planning/phases/141-jsonb-schema-gate-logic/141-CONTEXT.md` — gate constants + mate hierarchy
  (do not re-decide).

### Code surfaces (the load-bearing files)
- `app/services/eval_queue_service.py` — `_claim_tier3_derived()` (~242, the ES lottery to mirror for
  the new tier-4 blob lottery) and `claim_eval_job()` (~457, the tier-1>2>3 dispatcher to extend with
  tier-4). Note the **no-`eval_jobs`-table / `job_id=None`** lottery pattern.
- `app/services/eval_drain.py` — `_build_flaw_multipv2_blobs()` (~1159, the PV-walk + per-node
  MultiPV-2 blob assembly to adapt for the backfill: swap the local `evaluate_nodes_multipv2` gather
  for worker-supplied results), `_batch_update_flaw_pv_lines()` (~1280, the JSONB write),
  `_run_multipv2_pass()` (~1314), `_fill_engine_game_flaw_pvs()` (~1009, **no-ops for lichess** —
  the D-09a feasibility flag), and `resweep_holed_games()` (~2486, the re-arm pattern **rejected** in
  D-01 — kept here as the alternative we did not take).
- `app/routers/eval_remote.py` — `/eval/remote/lease` (~390) + `/eval/remote/submit` (~452) +
  `_apply_submit()` (~183): the live eval-ingest endpoints. The new tier-4 blob lease/submit is a
  **separate** path (D-04 isolation), not a branch of `_apply_submit`.
- `app/schemas/eval_remote.py` — `LeaseResponse` / `SubmitEval` / `SubmitRequest` (the ply-keyed
  schemas NOT reused, D-04) and the **`EntryLeasePosition` / entry-ply batch schemas (~Phase 123)**
  — the precedent template for the new token-keyed blob schema.
- `app/services/flaws_service.py` — `_classify_tactic_gated()` (~525, the single gated classify path
  invoked by the per-game retag in D-07).
- `app/services/forcing_line_gate.py` — `apply_forcing_line_filter()` + `ONLY_MOVE_WIN_PROB_MARGIN`
  (consumed, not changed); must tolerate the `[]` sentinel (D-06).
- `app/models/game_flaw.py` — `allowed_pv_lines` / `missed_pv_lines` (deferred JSONB) + the 8 tactic
  tag columns (the backfill + retag write targets).
- `scripts/retag_flaws.py` — the prod retag sweep (D-08); already `--db prod`, idempotent,
  change-only UPDATE, keyset paging.
- `scripts/backfill_full_evals.py` — the tier-1 enqueue precedent (`--db dev|benchmark|prod`,
  `db_url_for_target`, dry-run, idempotent) — the CLI/DB-target convention for any new backfill
  script (e.g. a kickoff/observability helper).

### Report / ops convention
- `reports/retag/` (or `reports/`) — committed markdown for the per-motif before/after chip counts
  (SC3), benchmarks / db-report / retag convention.
- `bin/prod_db_tunnel.sh` — required for any `--db prod` (forwards `localhost:15432`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_claim_tier3_derived()` (`eval_queue_service.py` ~242) — the ES weighted-random, table-less,
  predicate-driven lottery to clone for tier-4 (swap predicate to `allowed_pv_lines IS NULL`).
- `_build_flaw_multipv2_blobs()` + `_batch_update_flaw_pv_lines()` (`eval_drain.py`) — the PV-walk,
  per-node `(flaw_ply, line, node_k)` keying, blob assembly, and batched JSONB write. The backfill
  reuses this minus the local engine gather (worker supplies the MultiPV-2 results instead).
- `_classify_tactic_gated()` (`flaws_service.py` ~525) — the single gated classify path for the
  per-game retag (D-07) and the prod sweep (D-08).
- entry-ply batch schemas (`eval_remote.py`, Phase 123) — the token/keyed-batch lease/submit template
  for the new blob schema (D-04).

### Established Patterns
- Table-less lottery with `job_id=None`, self-deduping by predicate (tier-3). Tier-4 inherits this:
  idempotency-by-construction, acceptable double-claim, no enqueue step.
- Engine-free re-tag from stored blobs (143): detection replayed from JSONB, change-only UPDATE.
- Committed `reports/` markdown as the monitoring/validation deliverable.
- `--db dev|benchmark|prod` + `db_url_for_target` + dry-run + idempotency for backfill scripts.

### Integration Points
- New tier-4 branch in `claim_eval_job()` (after tier-3, `EVAL_AUTO_DRAIN_ENABLED`-gated).
- New `/eval/remote/...` blob lease + submit endpoints (isolated from `_apply_submit`).
- Blob-submit handler → write JSONB (reuse `_batch_update_flaw_pv_lines`) → per-game
  `_classify_tactic_gated` (D-07).
- Sentinel `[]` write path for un-fillable flaws (D-06); gate/retag tolerate `[]`.
- `retag_flaws.py --db prod` sweep (D-08) + before/after chip-count report (SC3).
- **No new EnginePool, no `STOCKFISH_POOL_SIZE` change** — the bulk compute is the remote fleet.

### Load-bearing facts (verified against the code this session)
- `_run_multipv2_pass` / `_build_flaw_multipv2_blobs` run **unconditionally** in `_full_drain_tick`
  (eval_drain.py ~2305, ~2347) — they don't check `is_lichess_eval_game`. So a lichess game *that is
  processed* gets blobs; the gap is that the tier-3 main predicate (`needs_engine`) almost never
  *selects* lichess games on prod's engine backlog (only the rare residual fallback does). This is
  WHY lichess games lack blobs in practice and motivates D-09's explicit lichess predicate.
- `_fill_engine_game_flaw_pvs` no-ops for lichess games → D-09a feasibility flag (lichess flaws may
  lack stored PVs to walk).

</code_context>

<specifics>
## Specific Ideas

- User's founding directive: **leverage the remote workers** to compute the missing MultiPV blobs —
  "that's where the bulk of the work lies." This phase's whole architecture follows from it.
- User's sharp framing that fixed the design: the tier-3 eval drain **doesn't use the `eval_jobs`
  table** — reuse that table-less **lottery** for the blob-only jobs (→ D-02, D-03).
- User's reasoning for accepting per-game retag in the submit path (D-07): the blob-backfill endpoint
  is **transitional** — once backfill/retag is done it goes quiet, and new games get blobs from the
  normal full analysis anyway, so the isolation tradeoff is low-stakes.
- Keep it engine-free where possible and fast; the backfill self-paces on spare fleet capacity.

</specifics>

<deferred>
## Deferred Ideas

- **resweep-style full re-arm** for blob backfill — explicitly rejected (D-01) in favour of the
  narrow blob-only job; kept as the alternative we did not take.
- **Solver-only blob storage** (halve MultiPV cost) — a 141 D-03 deferral, not this phase.
- **Raising `STOCKFISH_POOL_SIZE` to 8** — gated separately on a 24h soak (CLAUDE.md); untouched.
- **Lichess coverage fallback** — if D-09a research shows lichess flaws lack stored PVs and a full
  PV-pass is too costly, lichess gate coverage drops to a follow-up phase (engine-games-only this
  phase). Decision deferred to research feasibility.
- None of the above is scope creep — discussion stayed within the backfill + rollout boundary.

</deferred>

---

*Phase: 145-corpus-backfill-rollout*
*Context gathered: 2026-06-30*
