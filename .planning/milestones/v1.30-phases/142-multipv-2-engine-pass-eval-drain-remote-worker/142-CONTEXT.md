# Phase 142: MultiPV=2 Engine Pass + Eval Drain + Remote Worker - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce and persist the per-flaw-node **MultiPV=2** blobs (best + second-best eval cp/mate +
second-best UCI) into the `allowed_pv_lines` / `missed_pv_lines` JSONB columns added in Phase 141,
on every new game analysis, wired through both the local eval drain and the remote-worker contract,
with node-budget ordering reliability validated before merge.

**In scope:**
1. A new `EnginePool._analyse_multipv2()` (board + node limit → `list[InfoDict]` with best + second
   eval cp/mate + second-best UCI per PV node; guarded for single-legal-move positions). (MPV-01)
2. A new eval-drain step `_run_multipv2_pass()` that populates the two JSONB columns for every newly
   analyzed game, fed by the per-ply second-best data already gathered in the whole-game pass. (MPV-02)
3. Additive extension of the remote-worker `SubmitEval` contract so un-upgraded workers keep
   processing full-ply jobs without error. (MPV-02, SC3)
4. A committed margin-histogram validation tool that gates the merge. (MPV-03)

**Out of scope (later phases):** the offline re-tagger CLI that *calls* the gate against stored
blobs (Phase 143), the mate-hierarchy / defender-branch *tests* (143), user-28 A/B validation +
final margin commit (144), and corpus backfill + prod rollout (145). The gate module itself and all
its constants already exist (Phase 141) — this phase does **not** modify `forcing_line_gate.py` or
`tactic_detector.py`.

</domain>

<decisions>
## Implementation Decisions

### Compute location & contract (MPV-02)
- **D-01:** **Extend the existing whole-game per-ply PV pass to `multipv=2`** — do NOT add a separate
  flaw-only second engine pass. The existing `evaluate_nodes_with_pv` (eval_drain Step 3) already runs
  a 1M-node PV search on every ply, parallelized and remote-worker-able. MultiPV=2 is "the increment"
  on that same search (a second PV line at the same node budget, not new positions). Remote workers
  return second-best per ply; the server's `_run_multipv2_pass()` is an **assembly + write** step that
  builds the flaw-line blob arrays from the per-ply second-best data already in `engine_result_map`,
  then writes the JSONB. Rationale: reconciles SC3 (schema extension is load-bearing, not vestigial),
  reuses the remote fleet, marginal engine cost.
- **D-02:** A **new `_analyse_multipv2()` method** on `EnginePool` is required — `_analyse_with_pv`
  returns `InfoDict | None` and cannot be reused for the `list[InfoDict]` multi-line return (per
  MPV-01). Guard for single-legal-move positions (no second line → `su=""`, `s/sm=null`).
- **D-03:** **Inline optional fields on `SubmitEval`** — add `second_cp: int | None = None`,
  `second_mate: int | None = None`, `second_uci: str | None = None` directly to the existing per-ply
  `SubmitEval` row (NOT a parallel `multipv2_evals` list on `SubmitRequest`). Co-located with the ply
  they belong to, simplest, naturally backward-compatible: un-upgraded workers omit the fields → they
  default to `None` and the submit handler treats them as "no second-best".

### Backward-compat semantics (MPV-02 / SC3)
- **D-04:** **Old-worker gap → leave NULL, Phase 145 backfills.** When an un-upgraded worker analyzes a
  whole game it sends no second-best for any ply, so that game's flaw blobs stay NULL; the planned
  `backfill_multipv.py` (Phase 145, `WHERE allowed_pv_lines IS NULL`) fills the tail. New games on
  upgraded workers get blobs immediately. MPV-02's "every newly analyzed game" is therefore
  best-effort-for-upgraded-workers in 142, with the corpus guarantee landing in 145.
- **D-05:** **Eval gap → local SEED-056-style recovery.** Flaw nodes whose eval came from the opening
  dedup cache (Step 2c, ply ≤ DEDUP_MAX_PLY) or from a lichess `%eval` game have no engine second-best
  even on an upgraded worker. For just those flaw nodes, recompute multipv **locally**, mirroring the
  existing `_fill_engine_game_flaw_pvs` PV-recovery pattern (SEED-056). This is a few nodes per game
  (cheap), distinct from the worker-version gap (all nodes → too many → defer to 145).

### Node budget & validation (MPV-03)
- **D-06:** **Keep the existing 1M node budget + 5s timeout** (`_NODES_BUDGET`, `_NODES_TIMEOUT_S`) as
  the starting value for the multipv=2 search. Run the histogram; only raise to 1.5–2M if the SC4 test
  fails (>10% of positions within ±0.05 of the margin). Don't pre-pay cost — the design note frames
  multipv=2 as the increment on the current 1M PV search.
- **D-07:** **Committed `scripts/` + `reports/` validation tool** (benchmarks / db-report style),
  re-runnable on ≥200 dev flaw positions, gating the merge. Must be repeatable because Phases 144
  (A/B) and 145 (rollout) re-tune the margin offline against the same stored evals. NOT a one-off
  pasted into VERIFICATION.md.

### Claude's Discretion
- Exact `_analyse_multipv2()` / `_run_multipv2_pass()` signatures and helper names, the precise
  `scripts/`/`reports/` filenames and CLI flags for the histogram tool, the transaction boundary for
  the blob write (recommend same txn as the oracle-count UPDATE in Step 4b for atomicity), and the
  multipv search timeout tuning — planner/executor decide within the decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source (authoritative spec for this milestone)
- `.planning/notes/tactic-forcing-line-gate.md` §"Storage: persist MultiPV so re-tagging is
  engine-free" (lines 85–119) and §"Open knobs" (lines 135–147) — the blob shape, the
  "multipv=2 is the increment on the 1M PV search" framing, every-node vs solver-only, and the
  node/depth-budget tuning knob. **Respects an AGPL boundary: heuristics/constants/names only — copy
  NO lichess-puzzler source.**
- `.planning/REQUIREMENTS.md` §MPV (MPV-01, MPV-02, MPV-03) — this phase's requirements.
- `.planning/ROADMAP.md` §"Phase 142" — the 4 success criteria this phase is graded on.
- `.planning/phases/141-jsonb-schema-gate-logic/141-CONTEXT.md` — the locked blob shape (D-05),
  every-node storage (D-03), columns location (D-04), JSONB pattern (D-06), and gate constants
  (D-07..D-10) that this phase must fill, not re-decide.
- `.planning/research/SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md` — verified
  python-chess `multipv=2` / SQLAlchemy JSONB / asyncpg patterns and the pitfall list.

### Codebase patterns to follow
- `app/services/engine.py` — `EnginePool` (lines 346–542), `_analyse_with_pv` (486–519),
  `evaluate_nodes_with_pv` (521–542, caps PV at `PV_CAP_PLIES=12`), `_NODES_BUDGET` (1M, line 94),
  `_NODES_TIMEOUT_S` (5.0s), `_read_pool_size()` / `STOCKFISH_POOL_SIZE`. New `_analyse_multipv2()`
  lives here.
- `app/services/eval_drain.py` — orchestration `run_full_eval_drain()` (2080) → `_full_drain_tick()`
  (1812–2077). Insert the new MultiPV step **after Step 4b `_classify_and_fill_oracle()`** (line 2006),
  where flaw plies + their allowed/missed PV lines are known in-memory. Mirror
  `_fill_engine_game_flaw_pvs()` (Step 3b, line 1971, SEED-056) for the eval-gap recovery (D-05) and
  the batched-UPDATE pattern (`_batch_update_pv_rows`, line 443) for the JSONB write.
- `app/schemas/eval_remote.py` — `SubmitEval` (30–35) and `SubmitRequest` (38–45) are the contract to
  extend additively (D-03). `app/routers/eval_remote.py` `/eval/remote/submit` (452–479) →
  `_apply_submit()` (183–328) is the handler to thread second-best through.
- `app/models/game_flaw.py` — `allowed_pv_lines` / `missed_pv_lines` (lines 120–121, `deferred=True`)
  and the D-05 blob-key comment (109–116: `b/bm/s/sm/su`, white-perspective cp).
- `app/services/eval_utils.py` — `LICHESS_K` etc. (read-only here; the gate consumes these, this phase
  only stores raw cp/mate).

### Flaw production (where flaw_ply + the two PV lines come from)
- `app/services/flaws_service.py` — `classify_game_flaws()` (787+), `FlawRecord` (121–150),
  `_detect_tactic_for_flaw()` (401–500): `allowed` = refutation line PV at `flaw_ply+1`, `missed` =
  best-move line PV at `flaw_ply`. The blob arrays are indexed along these two lines.

### Related prior tactic work (context, not to modify)
- `app/services/tactic_detector.py::detect_tactic_motif` — **not modified** in v1.30.
- `reports/tactic-tagger/tactic-tagger-2026-06-23.md` — the "perfect on fixtures" report motivating
  the gate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EnginePool._analyse_with_pv` (engine.py:486) — the closest analog for `_analyse_multipv2()`; new
  method needed because its `InfoDict | None` return can't carry the second PV line.
- `_fill_engine_game_flaw_pvs()` (eval_drain.py:1971, SEED-056) — the exact pattern to mirror for the
  eval-gap multipv recovery (D-05): locally re-evaluate only the flaw-adjacent plies that used
  dedup/lichess evals.
- `_batch_update_pv_rows()` (eval_drain.py:443) — the batched single-UPDATE idiom (FLAWCHESS-6B) to
  follow for writing the JSONB blobs (one round-trip per game).
- The `scripts/` + `reports/` benchmark/db-report convention — the model for the committed,
  re-runnable histogram tool (D-07).

### Established Patterns
- Eval-drain step ordering: eval pass (Step 3) → flaw classification (Step 4b) → PV write. The new
  MultiPV blob write slots in **after** classification because flaw plies aren't known until then.
- Remote contract: lease whole-game positions → worker returns per-ply `SubmitEval` (eval + best_move
  + pv). Additive optional fields keep old workers compatible (the existing `job_id: int | None = None`
  is the precedent for "old worker omits → None").
- `deferred=True` on both JSONB columns (Phase 141 D-02): the blob write must explicitly set the
  attributes; stats reads never load them.

### Integration Points
- `EnginePool` (engine.py) — new `_analyse_multipv2()`.
- `eval_drain.py::_full_drain_tick` — new `_run_multipv2_pass()` after Step 4b (line 2006).
- `eval_remote.py` schema + `/eval/remote/submit` handler — additive second-best fields + threading.
- `game_flaws` JSONB columns — the write target (already migrated, Phase 141).
- No new EnginePool / pool-size change — reuse the module-level singleton (RSS budget).

</code_context>

<specifics>
## Specific Ideas

- **RESEARCH FLAG (PV1 drift):** Switching the *whole-game* pass to `multipv=2` changes how the
  primary line (PV1) is computed for **every** ply, not just flaw nodes — Stockfish's PV1 score under
  MultiPV=2 can drift slightly vs MultiPV=1 (less aggressive pruning), and PV1 feeds `eval_cp`, flaw
  classification, and benchmarks. The MPV-03 histogram validates *second-best ordering*, NOT
  primary-eval drift. The planner/researcher should confirm PV1 eval/best-move quality is preserved
  (e.g. spot-check eval delta vs the current MultiPV=1 pass on the same positions) or guard it.
  Minor non-determinism is already accepted (memory `project_eval_nondeterminism`); a *systematic*
  shift that moves flaw boundaries is the concern.
- The whole value of JSONB-over-Text (Phase 141) is that a future gate rule reads a new blob field
  with **no migration** — this phase must write the full `b/bm/s/sm/su` shape even where a field is
  currently unused (`su` is not read by the current gate but is stored to future-proof).
- The validation must isolate the algorithm from eval noise: the histogram tool runs against stored
  dev MultiPV evals so 144's A/B and 145's rollout re-derive from the same data engine-free.

</specifics>

<deferred>
## Deferred Ideas

- **Solver-only blob storage** (halve MultiPV cost) — explicit later optimization; Phase 141 D-03
  locked every-node storage for now.
- **Server-local MultiPV fallback for old-worker games** — rejected for 142 (D-04); the gap is filled
  by the Phase 145 backfill instead.
- **Offline re-tagger CLI + mate-hierarchy / defender-branch tests + idempotency** — Phase 143.
- **User-28 A/B validation + final `ONLY_MOVE_WIN_PROB_MARGIN` commit** — Phase 144.
- **`backfill_multipv.py --db prod` + corpus rollout + per-motif chip-count monitoring** — Phase 145.
- **Raising `STOCKFISH_POOL_SIZE` to 8** — gated separately on a 24h soak (CLAUDE.md); not touched here.
- None of the above is scope creep — discussion stayed within the MultiPV-pass boundary.

</deferred>

---

*Phase: 142-multipv-2-engine-pass-eval-drain-remote-worker*
*Context gathered: 2026-06-29*
