# Phase 174: Backend Maia Inference + Best-Move Storage (spike-gated) - Context

**Gathered:** 2026-07-16
**Status:** Ready for planning

<domain>
## Phase Boundary

During the backend eval-apply pass, run a Python port of Maia-3 inference on
out-of-book best-move plies that clear an inaccuracy floor, and persist
`maia_prob` + best/second Stockfish eval into a new `game_flaws`-sibling table
(`game_best_moves` or similar). Gem/Great classification stays **entirely
query-time** from the stored floats — the table stores candidates, never a
gem/great boolean. The whole phase is **spike-gated**: a fixture-based parity
test proving the Python encoding+inference port matches the client's
onnxruntime-web output gates all further work (mirrors Phase 168's Maia-in-Node
feasibility gate).

**In scope (Phase 174 only):** the parity spike, the new table + migration,
backend Maia inference at eval-apply, the candidate-row gate, uv dependency
isolation, and the query-time reclassification constants.

**Out of scope (later phases):** board/`EvalPoint` consumption + `useGemSweep.ts`
retirement (Phase 175, BOARD-01/02), the Library gem/great game filter (Phase
175, FILT-01), and corpus backfill via the tier-4 lottery (Phase 176, BACK-01).
Do not build those here.

</domain>

<decisions>
## Implementation Decisions

Four SEED-108 "Open Questions" were resolved in this discussion. Everything in
the "Carried forward" section below is already locked by SEED-108's
`/gsd-explore` session and is NOT re-litigated.

### Spike-gate — parity tolerance & fail path (SC1, GEMS-04)
- **D-01:** Parity is defined by **tier-stability + a loose epsilon**, not a
  tight raw-probability match. The gate passes iff every fixture ply lands in
  the **same gem / great / neither tier** on both the Python and client sides,
  with raw `maia_prob` within a loose band (~±0.02 — final number set by the
  researcher from measured drift). Rationale: the tiers are coarse buckets
  (Gem ≤ 0.20, Great (0.20, 0.50]), so tier agreement is what actually protects
  stored classification; benign CPU-vs-WebGPU float drift that never flips a
  tier is acceptable.
- **D-02:** **Fail path** if the port cannot meet the gate: the phase **pauses
  for re-scope**. Falling back to Maia-on-workers (a worker-protocol change)
  stays a *documented escape hatch*, explicitly NOT auto-taken. Do not ship
  mismatched stored data.

### ONNX InferenceSession lifecycle & prod RAM (GEMS-03)
- **D-03:** The Maia `InferenceSession` is **eager-loaded at FastAPI lifespan
  startup**, mirroring the established Stockfish engine lifecycle
  (`start_engine()`/`stop_engine()` at `app/main.py:96,140`). Add a
  `start_maia()`/`stop_maia()` pair called from the same lifespan; one
  process-wide session.
- **D-03a (guardrail):** The eager load must be a **no-op when onnxruntime is
  not installed** — deps are group-isolated (GEMS-06/D-08) and a backend image
  without the inference group must not crash at boot. (Remote workers run
  `scripts/remote_eval_worker.py`, not the FastAPI app, so the lifespan never
  fires there — but keep the guard defensive.)
- **D-03b (guardrail):** The plan MUST measure steady-state backend RSS against
  the documented OOM history before enabling in prod. One ~44 MB session is
  small next to the 6-subprocess Stockfish pool, but the 4 GB backend container
  is OOM-sensitive.

### ELO clamping for out-of-band movers (GEMS-05)
- **D-04:** Clamp the pinned lichess-blitz-equivalent rating to **[600, 2600]**,
  mirroring the frontend `MAIA_ELO_LADDER` bounds / `clampToLadderBounds`
  exactly, so backend-stored `maia_prob` and the live board agree for the same
  position. **Correction to framing:** the "validated 1100–2000 band" cited in
  SEED-108/CLAUDE.md is Maia-3's *validated draw-rate sweep sub-band*, not the
  clamp bounds — the frontend ladder is the full 600–2600 (21 rungs, step 100;
  600–1000 and 2100–2600 are documented extrapolation the model still accepts).
  Backend clamps to the same 600–2600 the board uses. A row is still stored for
  clamped movers (maia_prob is populated at the clamped rung).

### Storage column types (GEMS-01, D-4)
- **D-05:** Persist **raw Stockfish centipawns as ints** (`best_cp`,
  `second_cp`, plus mate flags), exactly as `second_best_map` already holds
  them (`(cp, mate, uci)`) — NOT pre-converted expected-score floats. The
  cp→expected-score conversion (via the existing sigmoid) + mate handling stays
  **query-time in one place**, keeping the C1/C2 margins fully retunable with
  zero re-analysis and matching `game_positions.eval_cp`. `maia_prob` remains a
  float. This is the column set from SEED-108 D-4's own example
  (`… maia_prob, best_cp, second_cp`); GEMS-01's literal "as floats" wording
  means "continuous values, never a boolean flag", satisfied by storing
  `maia_prob` as a float.
- **D-05a:** The `best_es − second_es ≥ INACCURACY_DROP (0.05)` candidate gate
  still computes expected-score **at write time** (to decide whether to store
  the row + run Maia) — storing cp does not remove the write-time ES
  computation; it only keeps the *persisted* value retunable.

### Claude's Discretion
- Exact column names/types of the new table beyond the cp/maia_prob decision
  (e.g. mate representation, whether to denormalize `fen`/`best_move`), the uv
  group name, the parity-fixture corpus source, and the precise eval-apply
  insertion point — the researcher/planner decides these within the locked
  decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source (locked decisions)
- `.planning/seeds/SEED-108-backend-gem-great-detection.md` — the full locked
  design (D-1…D-5), the cost insight, the Open Questions this phase resolves,
  and the breadcrumb line numbers. Primary reference.
- `.planning/ROADMAP.md` §"Phase 174" (lines ~54–64) — goal, success criteria,
  dependency waves.
- `.planning/REQUIREMENTS.md` §"Backend Inference & Storage (GEMS)" —
  GEMS-01…GEMS-07 (the phase's requirement IDs).

### Backend eval pipeline (where inference + storage slot in)
- `app/services/eval_drain.py:761-827` — the per-ply multipv=2 pass;
  `second_best_map` (line ~826) is where the runner-up cp margin already exists
  and is currently dropped for non-flaw plies.
- `app/services/eval_apply.py:1208-1316` — `_build_flaw_multipv2_blobs`;
  flaw-scoped iteration that discards non-flaw second-best. Eval-apply is where
  backend Maia inference slots in (D-3).
- `app/services/engine.py:223-241` + `app/main.py:82-155` — the Stockfish
  `start_engine`/`stop_engine` lifespan pattern to mirror for `start_maia`/
  `stop_maia` (D-03).

### Storage pattern
- `app/models/game_flaw.py` — the sibling-table pattern to mirror for the new
  `game_best_moves` table (FK ondelete=CASCADE, natural composite key).
- `app/models/game_position.py:159-172` — existing per-position eval columns
  (`eval_cp` is int cp; the type convention D-05 matches).

### Client sources to port / stay parity-faithful with
- `frontend/src/lib/maiaEncoding.ts` — the 12-plane board→tensor encoding +
  softmax + `MAIA_ELO_LADDER` (600–2600, `clampToLadderBounds`) to port to
  Python (D-04).
- `frontend/public/maia/maia-worker.js` — the inference glue mirrored in the
  worker.
- `frontend/src/lib/gemMove.ts` — `classifyGem` C1/C2 definition
  (`GEM_MAIA_MAX_PROB` = 0.20, `MISTAKE_DROP` = 0.10) + the cp→expected-score
  conversion to reproduce query-side.
- `frontend/src/hooks/useMaiaEloDefault.ts` — the pinned
  lichess-blitz-equivalent ELO derivation (`*_lichess_blitz ?? raw`,
  `deriveRawDefault`) to reproduce server-side (D-04).
- `frontend/public/maia/maia3_simplified.onnx` (~44 MB, AGPL-3.0) +
  `frontend/public/maia/README.md` (SHA-256/provenance) — the model the backend
  loads.

### uv dependency isolation (GEMS-06)
- `pyproject.toml` — currently `[project.dependencies]` (worker+backend shared)
  + `[dependency-groups].dev`. `onnxruntime`+`numpy` must live in a NEW
  isolated group/extra so the worker image stays lean (D-08). Check how the
  backend vs worker Docker images install groups (`Dockerfile`,
  `Dockerfile.worker`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`second_best_map` (`eval_drain.py:~826`)**: the runner-up cp/mate/uci is
  ALREADY computed at nearly every ply via `evaluate_nodes_multipv2` and
  discarded for non-flaw plies. Persisting it for candidate rows is pure
  plumbing — no extra Stockfish `go` (SEED-108 "Key Cost Insight").
- **Stockfish lifecycle (`engine.py` + `main.py` lifespan)**: the exact
  eager-load-at-startup pattern D-03 mirrors for Maia.
- **`game_flaws` model + JSONB-blob sibling-table pattern**: template for the
  new table.
- **Query-time flaw/tactic filter machinery**: reused later (Phase 175) — out
  of scope here, but the table design should not preclude an `EXISTS`-based
  game filter.

### Established Patterns
- Backend evals store **int centipawns** (`game_positions.eval_cp`), not ES
  floats — D-05 keeps the new table consistent.
- Engines are eager-loaded at lifespan startup, stopped at shutdown (D-03).
- High-cardinality sparse data → **sibling table**, not mostly-NULL columns on
  `game_positions` (SEED-108 D-4).

### Integration Points
- New inference call slots into eval-apply where `second_best_map` already
  lands (`eval_apply.py`), gated on: out-of-book AND played == SF best AND
  `best_es − second_es ≥ 0.05`.
- `start_maia()`/`stop_maia()` hook into the existing `app/main.py` lifespan.

</code_context>

<specifics>
## Specific Ideas

- The parity gate is **classification-first**: what must be reproduced faithfully
  is the tier a ply lands in, not the raw float to 3 decimals. The fixture test
  should assert tier agreement across a corpus of plies + a loose per-ply
  epsilon.
- Mirror the client's ELO clamp exactly (600–2600) so a gem shown live on the
  board and a gem stored in the DB never disagree for the same position/rating.
- Keep the worker image lean — onnxruntime/numpy must not leak into the worker
  dependency set (GEMS-06 is a hard requirement, not a nicety).

</specifics>

<deferred>
## Deferred Ideas

- **Great-ceiling (0.50) + gem-ceiling (0.20) calibration against real per-game
  frequency** — belongs to the milestone's Future Requirements / a post-pipeline
  retune (GEMS-07 makes it a constants-only change; do not calibrate in 174).
- **Board/EvalPoint consumption, `useGemSweep.ts` retirement, Library
  gem/great filter** → Phase 175.
- **Corpus backfill via tier-4 lottery** → Phase 176.

### Reviewed Todos (not folded)
- **`172-deferred-review-findings.md`** — explicitly `resolves_phase: 175`
  (frontend gem-sweep review findings); belongs to Phase 175, not this backend
  phase.
- **`2026-03-11-bitboard-storage-for-partial-position-queries.md`** — unrelated
  database idea (partial-position bitboard queries); a keyword-only fuzzy match,
  out of scope for gem/great detection.

</deferred>

---

*Phase: 174-backend-maia-inference-best-move-storage-spike-gated*
*Context gathered: 2026-07-16*
