# Phase 177: Worker-side MultiPV-2 gem-candidate searches, protocol v2 — Research

**Researched:** 2026-07-17
**Domain:** Internal backend architecture refactor (remote-worker eval protocol, priority queue, write-path). No new external libraries.
**Confidence:** HIGH (codebase-verified — every referenced function/line was read directly, not inferred)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Locked upstream by SEED-111 (do not re-litigate)**
- **S-01:** Targeted re-search, NOT a blanket MultiPV-2 full pass. The full-ply pass stays MultiPV-1 (guarded by `test_eval_positions_uses_multipv1_no_second_best`); the worker runs a second targeted `evaluate_nodes_multipv2` only for plies where played == its own best.
- **S-02:** Trust boundary unchanged — the server never trusts worker judgement, only numbers. It re-applies the played==best check, out-of-book gate, and inaccuracy gate itself from submitted evals before running Maia. Submitted entries are ply-keyed and tamper-guarded (in-range check, 422 on garbage).
- **S-03:** Version gating at LEASE, not just submit. `WORKER_SCHEMA_VERSION` → 2; version in the atomic-lease request; v1 workers get 204 (no work) on the atomic lane and idle harmlessly until upgraded. Entry-ply and flaw-blob lanes may stay v1-compatible if convenient.
- **S-04:** Server fallback kept as a rare safety net, instrumented (Sentry tag/metric) so silently re-growing server Stockfish load is visible. Expected steady-state: near zero worker-path fallbacks.
- **S-05:** Tier-4b lease must carry **server-computed candidate plies** (played == stored best_move, out-of-book, from existing best_move/pv columns + book filter) — the SEED-076 incremental filter means a fully-analyzed game leases with no plies for the worker to run a full pass on. Worker compute is exactly the N candidate runner-up searches.
- **S-06:** Tier-4b submits skip reclassification — write `game_best_moves` + stamp `best_moves_completed_at`, touch nothing else (avoids the FLAWCHESS-8D StaleDataError surface churn).
- **S-07:** Worker-side Maia inference rejected (bit-consistency risk across fleet, no throughput win — uvicorn incl. Maia is ~0.5 core).

**Tier-4b worker lane shape**
- **D-01:** Workers reach tier-4b by extending the idle fall-through: `scope=idle` falls through to tier-4b after tier-3 empties — only for v2 workers and only when `BEST_MOVE_BACKFILL_ENABLED`. No new worker-side scheduling; the existing ladder preserves lane priority (fresh work first).
- **D-02:** Tier-4b results return via a dedicated submit endpoint (e.g. `/bestmove-submit`) with its own small schema (game_id + per-ply runner-up evals). The minimal apply path is structural — no worker-supplied discriminator can route a fresh-analysis submit around reclassification. Mirrors the flaw-blob-lease/submit pair pattern.
- **D-03:** Candidate-ply validation is a stateless recompute at apply: the server recomputes the candidate-ply set from its own stored best_move/pv columns + book filter and drops/422s any submitted ply outside it. No lease state persisted; server fully authoritative.
- **D-04:** One flag gates both: `BEST_MOVE_BACKFILL_ENABLED=off` means no tier-4b work leases to anyone (workers or drain). Single switch, consistent with the v2.4 D-05 rollout pattern.

**Drain's role after the shift**
- **D-05:** The in-process server drain stays a tier-4b consumer with a tier-aware minimal path — candidate searches only, minimal write, no reclassify — reusing the same server-side candidate/writer code as the fallback. This also fixes the existing bug where `run_one_full_eval_tick` ignores tier (eval_drain.py:908) and re-evaluates every ply of a tier-4b game at MultiPV-2 and reclassifies from scratch. The freed 8-engine pool (~1/3 of current fleet capacity) keeps contributing to backfill.
- **D-06:** Fallback instrumentation is tagged by source path: drain-local inline candidate computation (expected — locally-drained fresh games have no worker) vs worker-submit fallback (the regression signal, expected ~zero). The regression watch reads only the worker-submit dimension.
- **D-07:** The phase includes an explicit post-deploy before/after measurement step (HUMAN-UAT/verification): re-measure games/h stamped, worker engine busy %, server pool utilization, and fallback counts against the 2026-07-17 baseline recorded in SEED-111.

**Double-claim / TTL leases**
- **D-08:** TTL-lease escalation (D-4) is deferred. The D-07 measurement step also records the double-claim rate; if it stays around ~12% or grows post-shift, TTL leases become their own follow-up (seed/phase). Measure before optimizing.

### Claude's Discretion
- Fresh-lane lease details (area not selected for discussion): follow the seed's lean — include `move_uci` per position in the lease response (simpler than deriving from consecutive positions); out-of-book filtering stays server-side (worker computes second-best for ALL played==best plies, server drops in-book ones). Optionally carry the book-ply count in the lease to trim the superset if cheap.
- Exact endpoint/scope naming, lease/submit Pydantic schema shapes, Sentry tag names, and worker-side retry behavior for failed targeted searches.
- v1→v2 fleet upgrade sequencing (Adrian operates all 4 worker hosts; v1 workers idling on the atomic lane during rollout is acceptable by design).

### Deferred Ideas (OUT OF SCOPE)
- **TTL-lease escalation (D-4)** — double-claim mitigation deferred (D-08); revisit as its own seed/phase if the post-shift measured double-claim rate stays ~12% or grows.
- **uvicorn single-thread bottleneck** (Maia + classify + PGN parse, ~0.5 core today) — next candidate bottleneck at much higher submit rates; measure before optimizing (Maia batch inference / thread offload only if it shows). Per SEED-111 open question #3.
- `172-deferred-review-findings.md` client-side gem-sweep review warnings — frontend, unrelated.
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — unrelated DB feature.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md entries exist for this phase (it is a post-v2.4, seed-driven standalone phase — see STATE.md Roadmap Evolution entry for Phase 177). The seed's Design sketch + Amendment sections (SEED-111) function as the spec. Recommended requirement IDs for the plan to adopt (none exist upstream to conflict with):

| ID (proposed) | Description | Research Support |
|----|-------------|------------------|
| PROTO-01 | `WORKER_SCHEMA_VERSION` bumps to 2; `/atomic-lease` gates v1 workers to 204 | See "Version gating" below |
| PROTO-02 | Worker runs targeted MultiPV-2 re-search for played==best plies after its MultiPV-1 pass; submits second-best evals | See "Fresh-lane worker changes" |
| PROTO-03 | `/atomic-submit` consumes worker-supplied second-best data into `second_best_map`, tamper-guarded | See "Server-side fresh-lane changes" |
| BACK-02 | Dedicated tier-4b lease+submit endpoint pair with server-computed candidate plies | See "Tier-4b worker lane" |
| BACK-03 | Tier-4b submit writes only `game_best_moves` + `best_moves_completed_at`, no reclassify | See "Tier-4b submit apply path" |
| DRAIN-01 | In-process drain gains a tier-aware minimal path for tier-4b games (fixes `_ = tier` no-op) | See "Drain tier-awareness bug" |
| OBS-01 | Fallback instrumentation tagged by source (drain-local vs worker-submit-fallback) | See "Instrumentation" |
| MEAS-01 | Post-deploy before/after measurement against the 2026-07-17 baseline | See "Measurement / D-07" |
</phase_requirements>

## Summary

This phase is a pure internal architecture refactor of FlawChess's remote-eval-worker protocol — no new external libraries, no new dependencies, no frontend changes. All primitives already exist in the codebase and were read directly for this research: `_build_best_move_candidates` (the Pitfall-1 server-side fallback to demote), `_apply_atomic_submit`/`atomic_lease_eval_game` (the fresh-lane lease/submit pair), `claim_eval_job`/`_claim_tier4_bestmove` (the tier ladder, where tier-4b is currently reachable only by the in-process drain), `_full_drain_tick` (which ignores `tier` entirely — the D-05 bug is real and verified at eval_drain.py's `_ = tier` line), and `remote_eval_worker.py`'s `_run_cycle` ladder (currently 4 rungs: atomic-explicit → entry-ply → atomic-idle → flaw-blob).

The core mechanism the plan should exploit: `_build_best_move_candidates` **already accepts** an optional `second_best_map` parameter and already falls back to a server-side `evaluate_nodes_multipv2` call **only for plies missing from that map**. This means shifting the work to workers is primarily a **plumbing** change (thread real worker-computed second-best data through the existing map), not a rewrite of the candidate-detection/gate/Maia logic. The harder, genuinely new work is: (1) the tier-4b dedicated lease/submit pair with server-computed candidate plies and a from-scratch position-keyed `engine_result_map` reconstruction from already-shifted DB storage (a real pitfall — see below), and (2) the drain's tier-aware minimal path, which does not exist today in any form.

**Primary recommendation:** Extend the existing atomic-lease/submit pair and `_build_best_move_candidates` machinery in place (do not rewrite); add a wholly new, isolated tier-4b lease/submit endpoint pair mirroring the flaw-blob-lease/submit precedent exactly; and give the drain tick a real tier branch before touching version gating, since the drain bug is the most likely source of the phase's own regression tests.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MultiPV-1 full-ply eval | Worker (remote fleet) / Server drain | — | Unchanged (Phase 146 D-03 invariant) |
| MultiPV-2 gem-candidate runner-up search (fresh lane) | Worker (remote fleet) | Server (rare fallback, instrumented) | This phase's core shift — was 100% server, becomes worker-computed |
| MultiPV-2 gem-candidate runner-up search (tier-4b backfill) | Worker (remote fleet) | Server drain (tier-aware minimal path) | New lane; server computes candidate plies, worker computes only the runner-up evals |
| Candidate-ply identification (played==best, out-of-book) | API/Backend (server) | — | Trust boundary (S-02/D-03): server recomputes/validates, never trusts worker |
| Maia-3 inference (gem/great scoring) | API/Backend (server) | — | Unchanged; S-07 explicitly rejects worker-side Maia |
| Priority-queue lease/claim logic | API/Backend (server) | — | `eval_queue_service.py` — extended, not replaced |
| game_best_moves / best_moves_completed_at writes | Database / Storage | API/Backend | Same table, two write paths (fresh-lane full apply vs tier-4b minimal apply) |
| Fallback/regression observability | API/Backend (Sentry) | — | D-06 tagging by source path |

## Standard Stack

No new external libraries. This phase extends existing internal modules only:

| Component | Already Used By | Role in This Phase |
|-----------|-----------------|---------------------|
| `httpx.AsyncClient` | `scripts/remote_eval_worker.py` | Worker's HTTP calls to the two new/extended lease-submit round-trips |
| Pydantic v2 (`BaseModel`, `Field`) | `app/schemas/eval_remote.py` | New request/response schemas for the tier-4b pair + extended `AtomicSubmitRequest`/`LeasePosition` |
| SQLAlchemy 2.x async | `app/services/eval_apply.py`, `eval_queue_service.py` | New tier-4b claim/write helpers, mirroring `_claim_tier4_bestmove`/`_upsert_best_move_rows` |
| `chess`/`chess.pgn` | `eval_apply.py`, `eval_remote.py` | PGN replay for candidate-ply move_uci derivation (tier-4b apply path) |
| `sentry_sdk` | throughout | D-06 fallback-source tagging |

**Package Legitimacy Audit:** Not applicable — this phase introduces zero new third-party packages (no `npm install`, no `uv add`). Skip the audit table.

## Architecture Patterns

### System Architecture Diagram (fresh lane, after this phase)

```
Worker (remote fleet)                          Server (FastAPI)
──────────────────────                         ─────────────────
POST /atomic-lease                    ───────▶  worker_schema_version param
  ?scope=explicit|idle                          checked FIRST:
  &worker_schema_version=2                         v1 (or absent) ──▶ 204 (idle
                                                     harmlessly, S-03)
                                                   v2 ──▶ claim_eval_job(scope, ...)
                                                          tier-1/2/3 pick
                                       ◀───────  200: AtomicLeaseResponse
                                                  { positions: [{ply, fen,
                                                    is_terminal, move_uci}] }
                                                  (move_uci NEW field)

1. Eval ALL positions MultiPV-1
   (_eval_positions, UNCHANGED)
2. Hint flaw plies (_hint_flaw_plies,
   UNCHANGED — mistake/blunder only)
3. Walk + eval flaw-blob nodes
   MultiPV-2 (UNCHANGED)
4. NEW: for every ply where
   move_uci(played) == best_move
   (from step 1's own result),
   run evaluate_nodes_multipv2(board)
   → collect {ply: (second_cp,
     second_mate)}

POST /atomic-submit                   ───────▶  _apply_atomic_submit:
  { evals, blob_nodes,                            - tamper-guard blob tokens (unchanged)
    second_best[] }  ◀── NEW field                - NEW: tamper-guard second_best plies
                                                     (0 <= ply < game_length, else 422)
                                                   - build second_best_map from body
                                                     (was: None, hard-coded)
                                                   - _build_best_move_candidates(
                                                       ..., second_best_map)
                                                     → fallback ONLY for gaps
                                                       (instrumented, S-04/D-06)
                                                   - apply_full_eval (UNCHANGED path)
```

### Recommended Project Structure (files touched, no new top-level dirs)
```
app/
├── schemas/eval_remote.py       # +move_uci on LeasePosition; +AtomicSecondBestEval +
│                                 #  second_best[] on AtomicSubmitRequest; new
│                                 #  BestMoveLease*/BestMoveSubmit* schemas (tier-4b)
├── routers/eval_remote.py       # +worker_schema_version param on atomic-lease;
│                                 #  _apply_atomic_submit assembles second_best_map;
│                                 #  new /bestmove-lease + /bestmove-submit endpoints
├── services/
│   ├── eval_apply.py            # _build_lease_positions emits move_uci; new tier-4b
│   │                             #  candidate-ply + minimal-apply helpers (reusing
│   │                             #  _build_best_move_candidates' gate/Maia logic)
│   ├── eval_queue_service.py    # new _claim_tier4_bestmove caller path for the
│   │                             #  dedicated lease endpoint (bypassing claim_eval_job's
│   │                             #  bundled scope=None, which stays drain-only)
│   └── eval_drain.py            # _full_drain_tick gains a real tier branch (D-05);
│                                 #  WORKER_SCHEMA_VERSION-equivalent gate not needed here
│                                 #  (drain is not a "worker", no version to check)
scripts/
└── remote_eval_worker.py        # WORKER_SCHEMA_VERSION 1→2; targeted re-search after
                                  #  MultiPV-1 pass; new ladder rung for /bestmove-lease;
                                  #  worker_schema_version sent on lease, not just submit
tests/
├── test_eval_worker_endpoints.py    # atomic-lease version gating; second_best
│                                     #  tamper-guard; new bestmove-lease/submit tests
├── test_remote_eval_worker.py       # targeted re-search behavior; ladder rung order
├── test_eval_apply.py               # _build_best_move_candidates with a real
│                                     #  second_best_map (not just None fallback)
├── test_eval_queue_service.py       # any new claim helper for the dedicated lease
└── test_eval_drain.py / test_full_eval_drain.py  # tier-aware minimal path (D-05)
```

### Pattern 1: Reuse `_build_best_move_candidates`'s existing `second_best_map` gap-fill, don't rewrite it
**What:** The function already does exactly what S-04 wants: `fallback_targets = [t for t in candidate_targets if t.ply not in second_best_map]` — only plies missing from the map get the server-side `evaluate_nodes_multipv2` call.
**When to use:** Fresh lane (tier-1/2/3). The ONLY change needed on this side is: stop passing `None` at the atomic-submit call site (`app/routers/eval_remote.py:1170`) and instead build a real `second_best_map` from `body.second_best`.
**Example:**
```python
# Source: app/services/eval_apply.py:1823-1966 (already exists, verified)
async def _build_best_move_candidates(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    engine_result_map: dict[int, tuple[...]],
    second_best_map: dict[int, tuple[int | None, int | None, str | None]] | None,
) -> list[dict[str, Any]]:
    ...
    fallback_targets = [t for t in candidate_targets if t.ply not in second_best_map]
    # ^ this line is why the change is additive, not a rewrite.
```

### Pattern 2: Isolated lease/submit pair for tier-4b, mirroring flaw-blob (D-04 precedent)
**What:** `/flaw-blob-lease` + `/flaw-blob-submit` are a fully isolated schema/handler pair that never touches `_apply_atomic_submit` or `_classify_and_fill_oracle`. Phase 145's own docstrings state this isolation was deliberate ("D-04 isolation boundary in the threat model").
**When to use:** Tier-4b (D-02). The new `/bestmove-lease` + `/bestmove-submit` pair should follow the exact same isolation contract: no shared handler code with `_apply_atomic_submit`, dedicated Pydantic schemas, dedicated `_claim_tier4_bestmove`-driven lease builder.
**Example:**
```python
# Source: app/routers/eval_remote.py:723-806 (flaw_blob_lease, the template to mirror)
async def flaw_blob_lease(...) -> Response | FlawBlobLeaseResponse:
    async with async_session_maker() as session:
        blob_pick = await _claim_tier4_blob(session)   # <- swap for _claim_tier4_bestmove
    if blob_pick is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    ...
```

### Pattern 3: Position-keyed vs. decision-keyed vs. post-move-shifted columns (the tier-4b reconstruction pitfall)
**What:** `game_positions` stores THREE different keying conventions in the same row, and the tier-4b apply path is the first place in the codebase that must reconstruct all three from stored data rather than compute them fresh:
- `best_move` at row `k` = the engine's best move **FROM** position `k` (decision-ply-keyed, never shifted).
- `eval_cp`/`eval_mate` at row `k` = the eval **OF the position AFTER** the move at `k`, i.e., the eval **of position `k+1`** (post-move-shifted, SEED-044).
- Therefore: "the eval OF position `k`" (needed as `best_cp`/`best_mate` in `passes_inaccuracy_gate`) lives at **row `k-1`**, not row `k`.
**When to use:** Building `engine_result_map` for the tier-4b minimal-apply path (see Pitfall 1 below — this is the single highest-risk item in the phase).
**Example:**
```python
# Source: app/services/eval_apply.py:329-342 (_post_move_eval, the existing +1-shift site)
def _post_move_eval(pos_eval: dict[int, tuple[int|None,int|None]], ply: int) -> tuple[int|None,int|None]:
    """row `ply`'s STORED eval = eval of position `ply + 1`."""
    return pos_eval.get(ply + 1, (None, None))
# The tier-4b reconstruction needs the INVERSE: eval_of_position(ply) = stored_eval_row[ply - 1]
```

### Anti-Patterns to Avoid
- **Duplicating `_build_best_move_candidates`'s gate/Maia logic for tier-4b:** the candidate-detection loop, `passes_inaccuracy_gate`, `pinned_elo_for_mover`, and `score_move` call are all pure and already extracted into `best_move_candidates.py` — reuse them; do not re-derive the gem/great gate inline in a new tier-4b module.
- **Routing tier-4b submits through `apply_full_eval`:** S-06/D-02 are explicit — tier-4b writes ONLY `game_best_moves` + `best_moves_completed_at`. Calling `apply_full_eval` (which runs `_apply_full_eval_results` + `_classify_and_fill_oracle`) would re-diff/re-upsert flaws for a game whose flaws are already final, reopening the exact FLAWCHESS-8D StaleDataError surface the seed calls out.
- **Gating tier-4b lease reachability through `claim_eval_job(scope=None)`:** that bundled path is drain-only (its only caller is `_full_drain_tick`) and mixes tier-1/2/3/4/4b priority ordering server-side. The new worker-facing `/bestmove-lease` endpoint must call `_claim_tier4_bestmove` directly (mirroring how `/flaw-blob-lease` calls `_claim_tier4_blob` directly, NOT through `claim_eval_job`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Candidate-ply detection (played==best, out-of-book) | A new tier-4b-specific detector | `_contiguous_san_prefix` + `find_opening_ply_count` + the existing loop shape in `_build_best_move_candidates` | Already correct and tested (174-REVIEW CR-01 fixed a real bug here — a fresh reimplementation risks reintroducing it) |
| Inaccuracy/gem/great gating | New threshold logic | `passes_inaccuracy_gate`, `classify_best_move` (`best_move_candidates.py`) | Pure functions, already unit-tested, single retune surface (GEMS-07) |
| Efraimidis-Spirakis weighted lottery pick | A bespoke tier-4b picker | `_es_weighted_user_pick` / `_es_weighted_game_pick` (already generic, already used by `_claim_tier4_bestmove`) | `_claim_tier4_bestmove` already exists (Phase 176) — this phase only needs to make it *reachable* from a worker-facing endpoint, not rewrite it |
| Token tamper-guard pattern for a new lease/submit pair | A novel validation scheme | The `_parse_token`/in-range-ply check pattern from `_apply_atomic_submit`'s blob-node guard, or the `valid_tokens` set-membership check from `_apply_flaw_blob_submit` | Two working precedents already in the file; S-02/D-03 want exactly this shape |

**Key insight:** Nearly every piece this phase needs already exists somewhere in the codebase (fresh-lane candidate logic, tier-4b lottery pick, tamper-guard patterns, isolated-endpoint-pair pattern). The actual net-new code is small: wire-through of `second_best_map` on the fresh lane, one new isolated endpoint pair for tier-4b, one new field on the lease response (`move_uci`), and one new branch in the drain tick.

## Common Pitfalls

### Pitfall 1: Reconstructing `engine_result_map` for tier-4b from already-shifted DB storage
**What goes wrong:** A naive tier-4b apply path reads `game_positions.eval_cp`/`eval_mate` at row `ply` and treats it as "the eval of position `ply`" — but it is actually the eval of position `ply + 1` (post-move shift, SEED-044). This silently misattributes the runner-up gate's `best_cp`/`best_mate` by one ply, producing wrong (but plausible-looking) gem/great classifications on the entire ~416k-game tier-4b backfill.
**Why it happens:** Every other call site in the codebase builds `engine_result_map` from a FRESH engine pass (position-keyed by construction, via `_resolve_full_eval`) — this is the first path that must invert stored, already-shifted data back to position-keyed form.
**How to avoid:** Explicitly build `eval_of_position[ply] = (game_positions.eval_cp, eval_mate) at row (ply - 1)`, with `ply=0` yielding `(None, None)` (no row -1 exists — correctly resolves to "no candidate" via `passes_inaccuracy_gate`'s `None` guard, not a crash). Keep `best_move` un-shifted (row `ply`'s own `best_move` column, matching the existing decision-ply convention). Write a dedicated unit test asserting the shift direction against a small fixture game.
**Warning signs:** Gem/great tier assignments for tier-4b-backfilled games that look "off by one ply" relative to the fresh-lane equivalent for the same position; a code reviewer who reads `_post_move_eval`'s docstring and does NOT see an equivalent inverse-shift comment in the new tier-4b code.

### Pitfall 2: Tier-4b lease returning zero candidate plies stalls the ES lottery pick
**What goes wrong:** `_claim_tier4_bestmove` can pick a game whose stored-best-move-vs-played comparison yields zero out-of-book candidates (e.g., a very short game, or one where every played move differs from stored best). Without a forward-progress guarantee, the game gets picked repeatedly.
**Why it happens:** Unlike `/flaw-blob-lease`'s established `T-145-07` "sentinel write on all-un-walkable" pattern (which writes `[]` blobs so the predicate stops matching), a candidate-ply set of zero has no obvious sentinel column to write — `best_moves_completed_at` IS the natural stamp, but S-06 says "touch nothing else," and normally `best_moves_completed_at` is stamped by `apply_completion_decision` (Path A/C of the FULL apply flow), which the tier-4b minimal path deliberately bypasses.
**How to avoid:** Explicitly decide (and document in the plan) that a zero-candidate tier-4b pick still stamps `best_moves_completed_at` directly (mirroring the flaw-blob all-sentinel 204 branch's forward-progress guarantee) — do not leave the game eligible forever with nothing to submit. This must happen at LEASE time (the candidate-ply set is computed there), not deferred to a submit that will never arrive.
**Warning signs:** `_claim_tier4_bestmove`'s ES lottery repeatedly re-drawing the same handful of games; `best_moves_completed_at` never advancing for a visible subset of the backlog.

### Pitfall 3: `_full_drain_tick`'s tier variable is a documented no-op today — verified
**What goes wrong:** `eval_drain.py`'s `_full_drain_tick` captures `tier: int = claimed.tier` and, at the very end, writes `_ = tier  # tier is available for Phase 118 tier-aware cache logic` — a literal discard. The function unconditionally runs the FULL `evaluate_nodes_multipv2` gather over every non-terminal ply and the full `apply_full_eval` write (including `_classify_and_fill_oracle`), regardless of whether `claimed.tier == TIER_BESTMOVE_BACKFILL`.
**Why it happens:** Tier-4b was added (Phase 176) to `claim_eval_job`'s bundled `scope=None` path specifically so the drain could reach it, but the tier-aware minimal-write branch this phase's D-05 requires was never built — it was out of Phase 176's scope.
**How to avoid:** The plan MUST add an explicit `if tier == TIER_BESTMOVE_BACKFILL:` branch in `_full_drain_tick` before Step 3 (the gather) that routes to the same minimal candidate-search-only logic the new `/bestmove-submit` handler uses server-side (not the full `evaluate_nodes_multipv2`-over-every-ply pass). This is D-05's literal requirement, not an incidental cleanup.
**Warning signs:** A tier-4b game full-evaluated at MultiPV-2 for every ply (visible in Stockfish call counts / timing) and reclassified from scratch when it should have taken the ~N-candidate-only path; the seed's own text calls this "accidentally masked by fallback starvation" — meaning it may not show up until AFTER the fallback frequency drops (i.e., this bug is latent until this very phase's other changes reduce fallback traffic and expose it).

### Pitfall 4: Version gating scope — atomic-lease query param must reach ALL scopes, not just tier-4b
**What goes wrong:** If `worker_schema_version` gating is implemented only inside a new tier-4b code path, existing v1 workers keep leasing tier-1/2/3 via `/atomic-lease` unchanged — which is actually FINE functionally (the server-side fallback still works for them) but defeats S-03's explicit intent ("v1 workers get 204 no-work on that lane" — i.e., the WHOLE atomic lane, not just tier-4b) and therefore defeats the throughput goal, since a mixed fleet with lingering v1 workers keeps generating server-side fallback load on the fresh lanes too.
**Why it happens:** The atomic-lease endpoint currently has NO version parameter at all (only `scope`); `worker_schema_version` today is submit-only and explicitly "accepted but not gated on" (a comment the plan must update, not just add to).
**How to avoid:** Add `worker_schema_version` as a query param to `/atomic-lease` itself (default representing "v1/unknown" for backward-compat with un-updated worker binaries that don't send it — FastAPI's `Query(default=...)` handles the missing-param case). Gate ALL scopes (`explicit` AND `idle`) on `>= 2`, not just the new tier-4b fall-through. Update `remote_eval_worker.py` to send `worker_schema_version=WORKER_SCHEMA_VERSION` (bumped to 2) on the lease call, not just the submit body.
**Warning signs:** Server-side fallback rate (S-04's Sentry metric) staying non-zero post-deploy even after the fleet is nominally upgraded — a sign some worker instance is still landing on the old ungated behavior.

### Pitfall 5: Stale doc comment on `BEST_MOVE_BACKFILL_ENABLED`
**What goes wrong:** `app/core/config.py`'s existing comment on `BEST_MOVE_BACKFILL_ENABLED` reads: "Independent from `EVAL_AUTO_DRAIN_ENABLED` because best-move backfill load is backend-only and **cannot be shed to the remote worker fleet** (unlike blob backfill, ~85% of which the workers carry)." This phase makes that statement FALSE — best-move backfill becomes shed-able to workers, which is the entire point of D-01/D-02.
**Why it happens:** Pre-existing comment written for Phase 176's scope, before this phase existed.
**How to avoid:** Update the comment as part of this phase's changes (small, but a reviewer following the comment trail will otherwise be actively misled about the current architecture).
**Warning signs:** A future contributor reading config.py concludes tier-4b backfill is still backend-CPU-only and makes a wrong capacity-planning decision.

### Pitfall 6: Worker's ladder rung ordering for the new tier-4b lease
**What goes wrong:** Placing the new `/bestmove-lease` rung BEFORE `/flaw-blob-lease` in the worker's `_run_cycle` ladder would let tier-4b (lowest priority, `TIER_BESTMOVE_BACKFILL = 5`) preempt tier-4 blob backfill (`TIER_BLOB_BACKFILL = 4`) on the worker side, inverting the server's own tier ordering that the bundled `claim_eval_job` path already establishes (blob-backfill checked before bestmove-backfill in `claim_eval_job`'s `scope=None` branch).
**Why it happens:** The worker's ladder and the server's tier numbers are two independent priority mechanisms that must be kept in sync by hand — there is no shared enum the worker imports (the worker script only ever sees HTTP status codes, not tier numbers).
**How to avoid:** Place the new rung AFTER the existing rung 4 (`/flaw-blob-lease`), i.e., as rung 5, exactly mirroring `TIER_BLOB_BACKFILL(4) < TIER_BESTMOVE_BACKFILL(5)`.
**Warning signs:** A test asserting ladder rung order (mirroring the existing `_run_cycle` docstring's explicit rung enumeration) failing, or blob-backfill throughput regressing after this phase ships even though blob-backfill code itself is untouched.

## Code Examples

### Existing gap-fill contract (fresh lane) — the mechanism this phase activates
```python
# Source: app/services/eval_apply.py:1879-1893 (verified as-is, no changes needed here)
fallback_targets = [t for t in candidate_targets if t.ply not in second_best_map]
fallback_by_ply: dict[int, tuple[...]] = {}
if fallback_targets:
    results = await asyncio.gather(
        *(engine_service.evaluate_nodes_multipv2(t.board) for t in fallback_targets)
    )
    for t, res in zip(fallback_targets, results, strict=True):
        fallback_by_ply[t.ply] = res
```
This is exactly the S-04 "rare safety net" — it already exists and already only fires for gaps. The plan's job is to make `second_best_map` non-empty for v2-worker submissions, and to add the Sentry instrumentation (D-06) around the `if fallback_targets:` branch so a non-empty fallback list on the worker-submit path is visible and tagged distinctly from the drain-local path.

### Existing all-sentinel forward-progress pattern (tier-4b lease should mirror this)
```python
# Source: app/routers/eval_remote.py:764-775 (flaw_blob_lease, the D-04/T-145-07 precedent)
if not lease_positions:
    if sentinel_lines:
        sentinel_plies = {flaw_ply for flaw_ply, _line in sentinel_lines}
        sentinel_blob_map = {ply: ([], []) for ply in sentinel_plies}
        async with async_session_maker() as write_session:
            await _batch_update_flaw_pv_lines(write_session, game_id, sentinel_blob_map)
            await write_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```
Tier-4b's zero-candidate-plies case (Pitfall 2) should follow the same shape: stamp `best_moves_completed_at` directly at lease time and 204, rather than leaving the game re-eligible.

## State of the Art

| Old Approach | Current Approach (after this phase) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Server computes ALL gem-candidate runner-up evals synchronously inside `/atomic-submit` | Worker computes runner-up evals for plies it already knows are candidates (its own played==best); server only recomputes for gaps | This phase | Server pool load for gem-candidate search drops from 100% to "rare fallback only" |
| Tier-4b (~416k games) reachable ONLY by the in-process server drain (8 engines) | Tier-4b reachable by the full remote worker fleet via a dedicated lease/submit pair | This phase | Near-linear backfill scaling with fleet size instead of an 8-engine ceiling |
| `worker_schema_version` accepted but never gated (submit-only, observability) | Gated at LEASE for the atomic lane; v1 workers idle harmlessly | This phase | Forces clean fleet upgrade instead of allowing indefinite mixed-version server-fallback load |
| `_full_drain_tick` ignores `tier` entirely | Drain branches on `tier == TIER_BESTMOVE_BACKFILL` for a minimal candidate-only path | This phase (D-05) | Fixes a real, currently-latent bug (full MultiPV-2 re-eval + reclassify of already-analyzed tier-4b games) |

**Deprecated/outdated:**
- The `app/core/config.py` comment claiming best-move backfill "cannot be shed to the remote worker fleet" — see Pitfall 5.

## Assumptions Log

No claims in this research are tagged `[ASSUMED]` — every architectural claim above was verified by directly reading the referenced source file and line range in this session (eval_apply.py, eval_remote.py, eval_queue_service.py, remote_eval_worker.py, eval_drain.py, engine.py, best_move_candidates.py, game_position.py, game.py, eval_jobs.py, config.py, schemas/eval_remote.py). No new external package or library claim appears anywhere in this document (there is nothing to verify against a registry).

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (none) | — | — |

**This table is empty** — all claims in this research were verified directly against the codebase this session; no user confirmation needed on factual grounds. (Design DECISIONS — e.g., exact endpoint naming, exact rung ordering choice beyond the tier-number constraint — remain Claude's Discretion per CONTEXT.md, not unverified facts.)

## Open Questions

1. **Does the tier-4b lease need to cap candidate-ply count (a MAX_SUBMIT_EVALS-style over-cap sentinel)?**
   - What we know: `/flaw-blob-lease` has an explicit over-cap branch (SEED-073 precedent) that writes sentinels and 204s rather than ever constructing an oversized response. The fresh-lane `/atomic-lease` has the same pattern for `MAX_SUBMIT_EVALS` positions.
   - What's unclear: whether a single game can realistically produce enough out-of-book played==best candidate plies to approach `MAX_SUBMIT_EVALS` (1024) or a smaller bound — the 174-VERIFICATION data point (8.6 stored rows/game average) suggests very low risk, but a pathological long correspondence game is not ruled out.
   - Recommendation: reuse the existing `MAX_SUBMIT_EVALS`/over-cap-sentinel pattern defensively (cheap insurance, established precedent) rather than skip it; mirror the flaw-blob 204+sentinel-stamp branch from Pitfall 2/2's Code Example.

2. **Exact HTTP query-param vs. request-body placement for `worker_schema_version` on `/atomic-lease`.**
   - What we know: `scope` is currently a `Query()` param on this POST endpoint (unusual for a POST but established in this codebase — `atomic_lease_eval_game`'s existing signature). `worker_schema_version` on submit is a JSON body field (`AtomicSubmitRequest.worker_schema_version`).
   - What's unclear: whether the plan should add it as a second `Query()` param (consistent with `scope`) or introduce a lease request body (a bigger, more invasive schema change, since `/atomic-lease` currently takes no body at all).
   - Recommendation: `Query()` param, consistent with the existing `scope` param on the same endpoint — smallest surface-area change, and the worker script already appends query params to this exact call.

3. **Does the tier-4b lease response need a `move_uci` field, or can it reuse `AtomicLeaseResponse`/`LeasePosition` verbatim?**
   - What we know: D-02 calls for "its own small schema (game_id + per-ply runner-up evals)" — implying a NEW, smaller lease shape, not a reuse of `LeasePosition`. The tier-4b worker does not need `is_terminal` (no terminal donor concept applies — it's not doing a full pass) but DOES need the FEN and (implicitly) enough context to run `evaluate_nodes_multipv2` — it does NOT need `move_uci` on the lease at all, since the server has already validated played==best server-side before selecting the candidate ply (unlike the fresh lane, where the worker itself must compare its own eval's best_move against the played move).
   - What's unclear: whether including `move_uci` anyway (for symmetry/debuggability) is worth the extra field.
   - Recommendation: omit `move_uci` from the tier-4b lease schema — the worker's job there is purely "run MultiPV-2 at these FENs, return second_cp/second_mate," structurally simpler than the fresh lane. Plan should specify the tier-4b lease schema as `{game_id, positions: [{ply, fen}]}` and submit as `{game_id, second_best: [{ply, second_cp, second_mate}]}`.

## Environment Availability

Skipped — this phase has no new external dependencies (no new tools, services, runtimes, or CLIs). All work happens inside the existing FastAPI backend, the existing remote-worker script, and the existing PostgreSQL dev DB. Stockfish and the `EnginePool` are already running dependencies unaffected by this phase's scope.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json` (not absent, not false) — section included per protocol.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio + pytest-xdist (already configured) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing; `addopts` excludes `tests/scripts/benchmarks` and `tests/scripts/tagger`) |
| Quick run command | `uv run pytest tests/test_eval_worker_endpoints.py tests/test_remote_eval_worker.py tests/test_eval_apply.py tests/test_eval_queue_service.py tests/test_eval_drain.py tests/test_full_eval_drain.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROTO-01 | v1 worker (or no version param) gets 204 on `/atomic-lease` for both scopes | unit | `pytest tests/test_eval_worker_endpoints.py::test_atomic_lease_v1_worker_204 -x` | ❌ Wave 0 (new test) |
| PROTO-02 | Worker computes second-best only for played==best plies, not a blanket MultiPV-2 pass | unit | `pytest tests/test_remote_eval_worker.py::test_eval_atomic_game_targeted_second_best_only_played_best -x` | ❌ Wave 0 (new test) — should sit beside the existing `test_eval_atomic_game_full_ply_pass_stays_multipv1` |
| PROTO-03 | `second_best_map` built from submitted data feeds `_build_best_move_candidates`, fallback only fires for gaps | unit | `pytest tests/test_eval_apply.py::test_build_best_move_candidates_uses_submitted_second_best -x` | ❌ Wave 0 (new test) |
| PROTO-03 | Tamper guard: out-of-range submitted `second_best` ply is rejected 422 | unit | `pytest tests/test_eval_worker_endpoints.py::test_atomic_submit_second_best_out_of_range_422 -x` | ❌ Wave 0 (new test) — mirror the existing blob-node tamper-guard test |
| BACK-02 | Tier-4b lease returns server-computed candidate plies only (played==best, out-of-book) | unit | `pytest tests/test_eval_worker_endpoints.py::test_bestmove_lease_candidate_plies -x` | ❌ Wave 0 (new test) |
| BACK-03 | Tier-4b submit writes only `game_best_moves` + `best_moves_completed_at`, no flaw diff/upsert | unit | `pytest tests/test_eval_worker_endpoints.py::test_bestmove_submit_minimal_write_no_reclassify -x` | ❌ Wave 0 (new test) |
| DRAIN-01 | Drain tick on a `TIER_BESTMOVE_BACKFILL` claim runs the minimal path, NOT full MultiPV-2-every-ply + reclassify | unit | `pytest tests/test_full_eval_drain.py::test_full_drain_tick_tier4b_minimal_path -x` | ❌ Wave 0 (new test) |
| OBS-01 | Fallback Sentry tag distinguishes drain-local vs worker-submit-fallback source | unit | `pytest tests/test_eval_apply.py::test_best_move_candidates_fallback_source_tag -x` | ❌ Wave 0 (new test) |
| — (regression guard) | Full-ply pass stays MultiPV-1 (Phase 146 D-03 invariant, must NOT regress) | unit | `pytest tests/test_remote_eval_worker.py::test_eval_positions_uses_multipv1_no_second_best -x` | ✅ (existing, line 460) |
| MEAS-01 | Post-deploy games/h, worker busy %, server pool %, fallback count vs baseline | manual-only (HUMAN-UAT) | N/A — production observation against SEED-111's "Measured baseline (2026-07-17)" table | N/A (D-07 explicit HUMAN-UAT step, not automatable — depends on live prod fleet load) |

### Sampling Rate
- **Per task commit:** the quick-run command above (scoped to the ~7 touched test files)
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** Full suite green before `/gsd-verify-work`, PLUS the D-07 manual before/after measurement against SEED-111's baseline table (games/h, worker busy %, server pool %, fallback counts)

### Wave 0 Gaps
- [ ] All 7 new unit tests listed above (❌ rows) — none exist yet; this phase's plan must create them (mirroring the closest existing precedent test named in each row)
- [ ] No new test file needed — all new tests fit into the 5 existing test files listed in "Recommended Project Structure"
- [ ] Framework install: none — pytest/pytest-asyncio/pytest-xdist already present

## Security Domain

`security_enforcement` is not set to `false` in config — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes (unchanged) | `require_operator_token` (`X-Operator-Token`, `hmac.compare_digest`, fail-closed 403/401) — reused verbatim by any new endpoint |
| V3 Session Management | No | Stateless bearer-token API, no session state (unchanged) |
| V4 Access Control | Yes | Operator-token gate is the sole access boundary for all `/eval/remote/*` endpoints; no per-user authz needed (trusted operator model, unchanged) |
| V5 Input Validation | Yes | New: `second_best[]` ply bounds check (0 <= ply < game_length, else 422 — mirrors existing `blob_nodes` token in-range check); new tier-4b submit schema needs the same `EVAL_CP_MIN/MAX`, `MAX_PLY` field-level Pydantic bounds already established in `app/schemas/eval_remote.py` |
| V6 Cryptography | No new surface | `hmac.compare_digest` reused unchanged; no new secrets introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Worker submits a second-best eval for a ply outside the game's real ply range (garbage/tamper) | Tampering | Structural in-range check `0 <= ply < game_length`, 422 before any write — mirrors the existing `_parse_token`/blob-node guard in `_apply_atomic_submit` (T-147-02 precedent) |
| Worker submits a second-best eval for a ply it was never asked to compute (in-range but not a real candidate) | Tampering | S-02/D-03: server recomputes the candidate-ply set itself and silently drops any submitted ply not in that recomputed set — never trusts which plies the worker chose to send, exactly like the existing blob-node/flaw_ply divergence handling |
| A stale/rogue v1 worker keeps hammering `/atomic-lease` post-deploy, adding load without contributing | Denial of Service (self-inflicted, low severity) | 204 response is cheap (no DB write beyond the existing sweep); worker script's own `idle_sleep` backoff bounds request rate; not a new risk beyond what already exists for an idle-queue 204 |
| Tier-4b lease/submit accidentally shares code with the live `_apply_atomic_submit` reclassify path, creating an unintended write-amplification or StaleDataError surface | Tampering / Denial of Service (data integrity) | Structural isolation (D-02, Pattern 2 above) — a dedicated schema and handler with zero shared write-session code, exactly like the flaw-blob pair's proven isolation |

## Sources

### Primary (HIGH confidence — codebase read directly this session)
- `app/services/eval_apply.py` (full file, 2158 lines) — `_build_best_move_candidates`, `apply_full_eval`, `_classify_and_fill_oracle`, `_FullPlyEvalTarget`, `_post_move_eval`, `_resolve_full_eval`
- `app/routers/eval_remote.py` (full file, 1277 lines) — `atomic_lease_eval_game`, `_apply_atomic_submit`, `atomic_submit_eval`, `flaw_blob_lease`/`_apply_flaw_blob_submit` (the isolation-pattern template), `_build_lease_positions`, `_lease_position_redundant`
- `app/services/eval_queue_service.py` (full file, 995 lines) — `claim_eval_job`, `_claim_tier4_bestmove`, `_claim_tier4_blob`, `_es_weighted_user_pick`/`_es_weighted_game_pick`, tier constants
- `app/services/eval_drain.py` (lines 600-935) — `_full_drain_tick`, the verified `_ = tier` no-op, `_fill_engine_game_flaw_second_best`
- `scripts/remote_eval_worker.py` (full file, 1112 lines) — `_run_cycle` 4-rung ladder, `_eval_atomic_game`, `_hint_flaw_plies`, `WORKER_SCHEMA_VERSION`
- `app/schemas/eval_remote.py` (full file, 222 lines) — `LeasePosition`, `AtomicSubmitRequest`/`AtomicSubmitEval`, `FlawBlobLeasePosition`/`FlawBlobSubmitEval` (the schema-pair template)
- `app/services/best_move_candidates.py` (full file, 293 lines) — `passes_inaccuracy_gate`, `pinned_elo_for_mover`, `classify_best_move`, `mover_color_for_ply`
- `app/services/engine.py` (lines 260-380) — `evaluate_nodes_multipv2`, `evaluate_nodes_with_pv` signatures
- `app/models/game_position.py`, `app/models/game.py`, `app/models/eval_jobs.py`, `app/models/game_best_move.py` — column semantics (post-move shift, tier constants, `game_best_moves` schema)
- `app/core/config.py` (lines 75-109) — `BEST_MOVE_BACKFILL_ENABLED`, `EVAL_AUTO_DRAIN_ENABLED`, `EVAL_OPERATOR_TOKEN`, `EXPECTED_SF_VERSION`
- `.planning/seeds/SEED-111-worker-side-multipv2-gem-candidates.md`, `.planning/phases/177-worker-side-multipv2-gem-candidates/177-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — locked decisions and project history
- `tests/test_eval_worker_endpoints.py`, `tests/test_remote_eval_worker.py` — existing test naming conventions and the `test_eval_positions_uses_multipv1_no_second_best` invariant guard

### Secondary (MEDIUM confidence)
- None — no external documentation or web sources were needed for this phase (pure internal refactor).

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every module cited was read directly this session
- Architecture: HIGH — the fresh-lane gap-fill mechanism, the tier ladder, and the isolation-pair pattern are all verified in the current codebase, not inferred from the seed's prose alone
- Pitfalls: HIGH — Pitfall 3 (drain's `_ = tier` no-op) and the post-move-shift convention (Pitfall 1) were confirmed by reading the exact lines, not assumed from the seed's description

**Research date:** 2026-07-17
**Valid until:** 2026-08-16 (30 days — stable internal codebase, no fast-moving external dependency; re-verify if Phase 176's tier-4b lottery or the atomic-submit write path is touched by an intervening quick/fast task before this phase executes)
