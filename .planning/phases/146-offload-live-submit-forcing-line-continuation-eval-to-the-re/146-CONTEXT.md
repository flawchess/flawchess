# Phase 146: Offload live-submit forcing-line continuation eval to the remote worker - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Stop the live `POST /eval/remote/submit` path from running **any** server-side Stockfish.
Phase 142 made every worker submit synchronously evaluate the MultiPV-2 forcing-line
continuation nodes inline (`_apply_submit` → `_build_flaw_multipv2_blobs`, an
`asyncio.gather` over ~22·N continuation-node evals on the server's shared pool) before
responding — surfacing as worker `ReadTimeout`s under load (Sentry FLAWCHESS-7Y) and
contending with tier-3 drain.

Per SEED-071 Option 2 (LOCKED 2026-07-01): the live submit applies full-ply evals,
classifies flaws, fills flaw PVs, and stamps **both** completion markers — leaving
`allowed_pv_lines`/`missed_pv_lines` NULL. The freshly-submitted game then matches the
existing Phase-145 tier-4 predicate and drains through the **existing** flaw-blob
lease/submit + per-game gated D-07 retag path. Server runs zero Stockfish on the live
path; live and backfill paths unify.

**In scope:**
- Remove the server continuation walk from the live submit (`_apply_submit` stops calling
  `_build_flaw_multipv2_blobs`; leaves blobs NULL).
- Live `/submit` payload drops the now-unused per-ply second-best fields.
- **Upgrade the long-running fleet worker (`scripts/remote_eval_worker.py`) to drain
  tier-4** via the Phase-145 `/eval/remote/flaw-blob-lease` + `/flaw-blob-submit` contract.
  This is load-bearing, not optional (see D-04).
- Recency-prioritize tier-4 so freshly-analyzed games get gated promptly (D-01).

**Out of scope (do not expand):** changing the gate logic / `ONLY_MOVE_WIN_PROB_MARGIN`
(consumed, not changed), the blob shape, the tier-4 lease/submit *schema* (Phase 145, reused
as-is), `STOCKFISH_POOL_SIZE`, any new tactic motif, any DB schema/migration. New
capabilities belong in their own phase.

</domain>

<decisions>
## Implementation Decisions

### Tier-4 priority for freshly-analyzed games (the main UX lever)
- **D-01: Recency-order the tier-4 lottery — fresh games win.** Today `_claim_tier4_blob`
  (`eval_queue_service.py` ~459) uses `ORDER BY random() LIMIT 1` across the *entire*
  `allowed_pv_lines IS NULL` backlog, so a just-analyzed live game competes with uniform
  probability against the whole old-corpus backfill and could stay ungated (raw/noisy tags)
  for a long time during the rollout. Change the pick to favor `full_evals_completed_at DESC`
  (recency) so freshly-completed games are selected first and the old corpus drains on the
  tail. No new tier, no new column — recency is the natural fresh-vs-corpus discriminator.
  - **Planner flag:** a *pure* `ORDER BY full_evals_completed_at DESC LIMIT 1` makes every
    idle worker collide on the single newest game (wasteful double-claims; idempotent but
    inefficient). Add a tie-break/jitter — e.g. random pick among the N most-recently-completed
    games, or `ORDER BY full_evals_completed_at DESC, random()` over a recency window — to
    spread picks the way the tier-3 ES lottery does. Exact form is planner/researcher's call.

### Tag display during the NULL-blob window
- **D-02: Show raw (ungated) tactic tags during the window — current behavior, no read-path
  change.** Tags are stored in the `game_flaws` tactic columns and gated at classify-time;
  with blobs NULL the gate is skipped, so the stored columns hold raw tags and display reads
  them directly. A freshly-analyzed game shows its tactic chips immediately; tier-4 retag
  (D-07) silently denoises them shortly after (window is short thanks to D-01). This is
  exactly how every un-blobbed game already behaves today (old corpus pre-backfill). Rejected:
  hiding chips until blobs land — it makes a just-analyzed game look empty/broken and adds new
  blob-presence gating on the read path for no real gain given D-01 shortens the window.

### Live submit payload & completion-marker semantics
- **D-03: Live `/submit` drops per-ply second-best; server unconditionally skips the blob
  build; flaw PVs + both completion markers still stamped live.** The worker stops sending
  `second_cp`/`second_mate`/`second_uci` on `/submit` (honest contract: live submit = full-ply
  evals + flaw PVs). `_apply_submit` always takes the empty-`blob_map` path (it already exists
  as the D-04 old-worker backward-compat branch at `eval_remote.py:275`), so it: applies evals,
  classifies raw flaws, fills flaw PVs, stamps `full_evals_completed_at` **and**
  `full_pv_completed_at`, and leaves `allowed_pv_lines`/`missed_pv_lines` NULL.
  - **Verified safe to drop second-best:** `_build_flaw_blob_lease_positions`
    (`eval_drain.py:1332`) reconstructs both the "missed" (at `flaw_ply`) and "allowed" (at
    `flaw_ply+1`) lines **purely from stored `game_positions.pv` strings** — it has zero
    dependence on per-ply submit second-best. The per-ply second-best fed *only*
    `_build_flaw_multipv2_blobs` (the removed server walk). The gate's blob-node `s/sm` fields
    come from the worker's MultiPV-2 on the *leased continuation FENs* (tier-4), preserved.
  - **Atomicity:** the Phase-142/145 D-07 single-transaction invariant (evals + flaws + blobs +
    completion) is intentionally relaxed on the live path — the game is briefly
    analyzed-but-ungated. This is self-healing: it immediately matches the tier-4 predicate and
    is corrected by the D-07 gated retag at flaw-blob-submit (change-only UPDATE). Acceptable
    per SEED-071 (the live path now behaves like the existing transitional/old-worker path).

### Fleet-worker tier-4 drainer (load-bearing — surfaced during scout, accepted as in-scope)
- **D-04: Phase 146 MUST add a flaw-blob lease/submit drain loop to the long-running fleet
  worker (`scripts/remote_eval_worker.py`).** Scout finding: **no fleet worker speaks the
  flaw-blob contract today** — `remote_eval_worker.py` only calls `/lease` + `/submit`, and
  `scripts/backfill_multipv.py` is observability/kickoff/dev-validate **only** (no EnginePool,
  no continuous drain). So Phase 145's tier-4 endpoints exist but nothing drains them
  continuously. Without this drainer, every deferred live game (and the whole corpus backlog)
  stays NULL-blob forever and tactic tags never get gated — i.e. the offload would *break*
  gating rather than just move it. The worker upgrade is the functional core of this phase.
  - Shape: after exhausting tier-1/2/3 (`/lease`), the worker polls `/flaw-blob-lease`,
    evaluates the leased FENs at MultiPV=2 (it already does MultiPV-2 since Phase 142), and
    echoes token + result to `/flaw-blob-submit`. Worker stays token-opaque (Phase 145 D-04a).
  - **SEED-071 note:** this is "the same 'upgraded worker' client that Phase 145 already
    needs" — Phase 145 built the server endpoints but deferred the fleet-worker client to here.

### Claude's Discretion (planner/researcher decide within the above)
- **Worker full-ply pass likely reducible to MultiPV-1 (optional optimization, research-confirm
  first).** With per-ply second-best dropped (D-03) and verified unused anywhere else, the
  worker's full-ply eval no longer needs MultiPV-2 (Phase 142 raised it solely to feed the now-
  removed server walk; the flaw PV comes from the MultiPV-1 best line). Reverting to MultiPV-1
  speeds the worker. Treat as a *flagged consequence*, not a locked decision — research must
  confirm no remaining consumer before reducing it; if in doubt, leave the full-ply pass at
  MultiPV-2 (harmless).
- Exact recency tie-break/jitter form for D-01; the worker's tier-4 poll cadence, batch size,
  and back-pressure; dev-first end-to-end validation gate (live submit → NULL blobs → tier-4
  drain → gated retag) before any prod change; whether/how to lower `HTTP_TIMEOUT_S` back from
  the 120s SEED-071 stopgap once the server walk is gone.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec & decided approach (authoritative)
- `.planning/seeds/SEED-071-live-submit-continuation-eval-bottleneck.md` — the DECIDED APPROACH
  (Option 2, LOCKED 2026-07-01), the protocol shape, why Option 2 over async-ify, and the three
  open questions resolved in this CONTEXT (priority lane, tag display, worker client).
- `.planning/ROADMAP.md` §"Phase 146" — the phase goal.

### Prior-phase context (locked, do not re-decide)
- `.planning/phases/145-corpus-backfill-rollout/145-CONTEXT.md` — the tier-4 lottery (D-02/D-03),
  the dedicated token-keyed flaw-blob lease/submit schema (D-04/D-04a), per-game gated retag
  (D-07), sentinel `[]` for un-fillable flaws (D-06). Phase 146 **reuses all of this unchanged**;
  it only adds the live-path offload + fleet-worker client + recency ordering.
- `.planning/phases/142-multipv-2-engine-pass-eval-drain-remote-worker/142-CONTEXT.md` — locked
  blob shape (`b/bm/s/sm/su`, white-perspective cp); the D-04 old-worker "leave blobs NULL"
  backward-compat path that Phase 146 makes the default for the live path.
- `.planning/phases/143-offline-re-tagger/143-CONTEXT.md` — `_classify_tactic_gated`, engine-free
  retag from blobs.
- `.planning/notes/tactic-forcing-line-gate.md` — gate design source. **AGPL boundary:
  heuristics/constants/names only — copy NO lichess-puzzler source.**

### Code surfaces (the load-bearing files, verified this session)
- `app/routers/eval_remote.py` — `_apply_submit()` (~195; remove the
  `_build_flaw_multipv2_blobs` call at line 272, force the empty-blob path), the existing
  `/flaw-blob-lease` (~748) + `/flaw-blob-submit` (~936) endpoints the worker must now call.
- `app/services/eval_queue_service.py` — `_claim_tier4_blob()` (~459; change `ORDER BY random()`
  to recency-ordered per D-01) and `claim_eval_job()` (~509, tier dispatcher).
- `app/services/eval_drain.py` — `_build_flaw_multipv2_blobs()` (~the removed server walk; the
  `asyncio.gather` over continuation nodes is the bottleneck), `_build_flaw_blob_lease_positions()`
  (~1332; verified: reconstructs lines from stored `game_positions.pv`, NOT from submit
  second-best — this is why D-03's drop is safe).
- `app/schemas/eval_remote.py` — `SubmitEval` second-best fields (~38-40, 131-135; dropped from
  the live `/submit` per D-03) and the `FlawBlobLease*`/`FlawBlobSubmit*` schemas (reused as-is).
- `scripts/remote_eval_worker.py` — the fleet worker to upgrade (D-04): `_handle_full_ply_response`
  (~266, `/submit`), the lease loop (~234/248), `HTTP_TIMEOUT_S` (~65, the 120s SEED-071 stopgap).
- `scripts/backfill_multipv.py` — observability/kickoff/dev-validate CLI (`--status`/`--dry-run`/
  `--dev-validate`); the drain-progress monitor, NOT a continuous drainer.
- `app/services/flaws_service.py` — `_classify_tactic_gated()` (the D-07 retag path).
- `app/services/forcing_line_gate.py` — `apply_forcing_line_filter()` + `ONLY_MOVE_WIN_PROB_MARGIN`
  (consumed, not changed; tolerate `[]` sentinel).

### Ops
- `bin/prod_db_tunnel.sh` — required for any `--db prod` observability (forwards `localhost:15432`).
- Sentry FLAWCHESS-7Y — the ReadTimeout signal this phase eliminates.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The entire Phase-145 tier-4 server side** — `_claim_tier4_blob`, `/flaw-blob-lease`,
  `/flaw-blob-submit`, `_build_flaw_blob_lease_positions`, `_assemble_flaw_blobs_from_submit`,
  per-game `_classify_tactic_gated` retag — exists and is reused unchanged. Phase 146 adds the
  *client* (fleet worker) + the live-path offload + recency ordering.
- **The empty-`blob_map` branch of `_apply_submit`** (`eval_remote.py:275`) already does exactly
  the deferred-blob behavior (raw classify + stamp complete + NULL blobs). Phase 146 makes it the
  unconditional live path.

### Established Patterns
- Table-less, predicate-driven, idempotent-by-construction tier-4 lottery (`job_id=None`,
  self-dedupes on `allowed_pv_lines IS NULL`). Recency ordering (D-01) keeps this property.
- Worker lease/submit loop with token-opaque evaluation (worker echoes token + MultiPV-2 result).
- Read-session-closed-before-CPU / no `asyncio.gather` on an open `AsyncSession` (CLAUDE.md).

### Integration Points
- `_apply_submit`: delete the `_build_flaw_multipv2_blobs` call + the `_run_multipv2_pass` write
  (both become no-ops when `blob_map` is empty); keep eval apply, raw classify, flaw-PV fill, and
  both completion stamps.
- `_claim_tier4_blob`: swap `ORDER BY random()` for recency-ordered + jitter (D-01).
- `remote_eval_worker.py`: add the tier-4 `/flaw-blob-lease` → MultiPV-2 → `/flaw-blob-submit`
  loop after the tier-1/2/3 `/lease` loop (D-04).
- No new EnginePool, no schema/migration, no `STOCKFISH_POOL_SIZE` change.

### Load-bearing facts (verified against the code this session)
- The live submit's server engine cost is the `asyncio.gather` over continuation nodes inside
  `_build_flaw_multipv2_blobs`; the per-ply submit second-best is only a cheap node-0 overlay.
  Removing the blob build removes all server Stockfish from the live path.
- `_build_flaw_blob_lease_positions` walks lines from stored `game_positions.pv` only → tier-4
  needs the flaw PVs (filled live), NOT the dropped per-ply second-best.
- No fleet worker currently calls `/flaw-blob-lease` (only `backfill_multipv.py` references it,
  and it is observability-only) → the worker drainer (D-04) is mandatory for the offload to work.

</code_context>

<specifics>
## Specific Ideas

- The whole phase follows from SEED-071's root-cause: the *server* waiting on inline continuation
  eval is the bottleneck (not the worker, not the DB, not Stockfish being `SCHED_IDLE`). Moving
  that compute to the fleet removes the load entirely, not just the timeout.
- User's lean (confirmed): freshly-analyzed games should be gated promptly, not "eventually"
  behind the corpus backfill → recency ordering (D-01) rather than a whole new tier.
- Keep the change minimal and honest: drop dead second-best from the wire, reuse the existing
  empty-blob path, reuse the entire Phase-145 tier-4 machinery.

</specifics>

<deferred>
## Deferred Ideas

- **async-ify server-side blob assembly** — the simpler alternative explicitly rejected in
  SEED-071: it unblocks the worker but the server *still* runs the continuation eval (no
  throughput fix vs tier-3 drain) and breaks D-07 atomicity. Not this phase, not a follow-up.
- **Worker full-ply pass MultiPV-2 → MultiPV-1** — a real optimization enabled by D-03, but
  flagged as research-confirm/optional rather than locked (see Claude's Discretion). May land in
  this phase if research confirms no remaining second-best consumer, else its own follow-up.
- **Lowering `HTTP_TIMEOUT_S` back below 120s** — possible once the server walk is gone, but
  gated on observing the new live-submit latency; planner's call.
- None of the above is scope creep — discussion stayed within the offload boundary.

</deferred>

---

*Phase: 146-offload-live-submit-forcing-line-continuation-eval-to-the-re*
*Context gathered: 2026-07-01*
