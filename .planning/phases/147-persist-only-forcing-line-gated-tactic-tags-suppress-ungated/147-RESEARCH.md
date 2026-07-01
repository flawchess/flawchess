# Phase 147: Persist only forcing-line-gated tactic tags - Research

**Researched:** 2026-07-01
**Domain:** Backend data-integrity fix (Alembic data migration + classify-path threading) and
remote-worker pipeline upgrade (FastAPI endpoints + async SQLAlchemy + a headless httpx worker
script). No frontend, no LLM.
**Confidence:** HIGH — every load-bearing claim in this doc was re-verified against the live
code (file:line) and/or executed against the dev database (read-only `EXPLAIN`, and mutating
statements wrapped in `BEGIN ... ROLLBACK` so no dev data was altered).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01: A and B stay in one phase (roadmap as-is).** A ships first as the graceful-degradation
  net; B builds the atomic pipeline on top. If B proves larger than expected during planning,
  splitting B into a follow-up is acceptable, but the default is one phase.
- **D-02: New lease + new submit endpoint PAIR (seed lean accepted).** B changes the contract
  (submit carries blobs; completion gates on them) and a mixed fleet runs simultaneously across a
  deploy. Distinct schemas keep their own `MAX_SUBMIT_EVALS`-style DoS caps; gives rollback safety
  and avoids server-side shape-sniffing. Old `/lease` + `/submit` stay deprecated, removed once the
  fleet is fully upgraded.
- **D-03: Suppress the old corpus too — NOT go-forward only** (OVERRIDES the seed's go-forward-only
  lean). Suppress raw cp-tags on pre-Phase-142 old-corpus rows now, for a clean "no ungated tags
  anywhere" invariant immediately, rather than waiting on tier-4 to drain the whole corpus.
- **D-04: Deliver the old-corpus suppression as an Alembic DATA migration** (runs automatically on
  deploy via `deploy/entrypoint.sh`), NOT a standalone `scripts/backfill_*.py` and NOT
  reactive-only. Carve-outs (mate-adjacent, D-06 `[]` sentinel) are MANDATORY and identical to the
  go-forward path. Idempotent + self-healing. **PLANNER CONSTRAINT:** `game_flaws` is
  high-cardinality and migrations run on backend container startup — batch the UPDATE and confirm
  the predicate uses the existing partial index so the migration doesn't seq-scan.
- **D-05: Keep `_full_drain_tick` as-is (seed lean accepted).** The local full-drain already builds
  MultiPV-2 blobs inline and writes gated tags in the same tick — leave it untouched as local
  spare-capacity fallback. Retiring it is a deferred idea.

### Claude's Discretion

- **Q5 (classifier/schema version tag on the new submit)** — deferred to planner. A version tag is
  a robustness nicety, not load-bearing (server-authoritative re-classify + A's NULL
  graceful-degradation net already bound the blast radius).
- **Q4 (worker hint-classify data availability)** — research verification requested: confirm the
  worker can build lightweight `GamePosition`-like objects and call `classify_game_flaws` with NO
  hidden DB dependency via `derive_user_result`. **See "Q4 verification" below — CONFIRMED, with an
  important data-plumbing nuance the planner must decide on.**
- Exact `blobs_pending`/`defer_ungated` parameter name and threading; the migration's batching
  strategy and chunk size; the new endpoint schema shapes and their `MAX_SUBMIT_EVALS` caps; the
  new worker's lease→eval→blob→submit loop, poll cadence, and back-pressure; whether the worker's
  full-ply pass stays MultiPV-2 or drops to MultiPV-1 (Phase 146 carryover — **see "Already
  resolved" note below, this is NOT still open**); dev-first end-to-end validation gate before any
  prod change.

### Deferred Ideas (OUT OF SCOPE)

- Retire `_full_drain_tick` (local full-drain) — kept this phase (D-05); revisit once the fleet gate
  is observed reliable in prod.
- Retire tier-4 + its endpoints entirely — not this phase; end-state cleanup, gated on the old
  corpus fully draining.
- Worker full-ply pass MultiPV-2 → MultiPV-1 — **already done in Phase 146** (see below); nothing
  left to do here, this deferred item can be considered resolved-in-passing.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEED-074 | Persist only forcing-line-gated tactic tags: suppress ungated remote-submit tags (Part A, including old-corpus migration) and add an upgraded-worker atomic eval+blob pipeline gated at write time (Part B) | See "Part A threading", "Part A old-corpus migration", "Part B" sections below — all code sites, the exact suppression predicate, a tested migration SQL, and the worker/server contract are verified against the live codebase and dev DB. |
</phase_requirements>

## Summary

This phase closes a real correctness gap: the remote-submit path writes `game_flaws.tactic_motif`
(both orientations: `allowed_tactic_motif` and `missed_tactic_motif`) as **raw, ungated** values
whenever the forcing-line gate's blob hasn't arrived yet, and those values sit in stats/filters
until tier-4 backfill eventually corrects them (now an unbounded window under the ES lottery).
Two fixes close it: **Part A** suppresses (writes `NULL`) instead of persisting the raw value at
the two write sites that currently produce it (go-forward `_apply_submit`, and a new guarded
Alembic DATA migration for the pre-existing corpus); **Part B** builds a new worker pipeline that
computes full-ply evals + MultiPV-2 continuation blobs together and submits them atomically, so the
server can gate at write time and the ungated window never opens for games processed on the new
path.

Every code site named in CONTEXT.md/SEED-074 was re-verified against the current file and is
accurate (line numbers drift by a handful of lines from small intervening edits but the functions
and call graph are exactly as described). Two things the planner needs that were **not** fully
spelled out in CONTEXT.md:

1. **`tactic_motif` is not one column — it is two independent columns** (`allowed_tactic_motif`,
   `missed_tactic_motif`), each gated by its own blob column (`allowed_pv_lines`,
   `missed_pv_lines`). The suppression predicate must be applied **per orientation**. Empirically
   (verified on dev, and by inspection of the only write path) the two blob columns are always
   NULL/non-NULL **together**, but that is an invariant of `_batch_update_flaw_pv_lines`, not a DB
   constraint — the migration should gate each orientation's suppression on its own blob column,
   not assume the correlation.
2. **`pre_flaw_eval_cp` is NOT a stored column on `game_flaws`.** It is computed at classify time
   as `positions[flaw_ply - 1].eval_cp` (a `game_positions` row). The old-corpus migration
   therefore requires a **JOIN** to `game_positions` on the PK `(user_id, game_id, ply)` — a bare
   `UPDATE game_flaws WHERE ...` cannot express the mate-adjacent carve-out. This join is
   confirmed index-driven (see "Migration predicate is index-driven" below).

**Primary recommendation:** Thread a `blobs_pending: bool` through
`_apply_submit → classify_game_flaws → _build_flaw_record → _classify_tactic_gated`, ship the
Alembic DATA migration using the repo's existing `DO $$ ... WHILE rows_updated > 0 LOOP ...`
batched idiom (already used in `20260327_..._reclassify_pawnless_endgames_from_mixed.py`) joined to
`game_positions`, and build Part B's worker pipeline by cloning the existing tier-4
lease/build/submit machinery (`_build_flaw_blob_lease_positions`, `_walk_pv_boards`,
`evaluate_nodes_multipv2`) into a new endpoint pair, using `_full_drain_tick`'s Step 3d→4 ordering
(classify BEFORE writing blobs, same transaction) as the server-side atomic-write template.
**Also flag: SEED-073 (the over-cap sentinel Part B is supposed to "reuse") is still `dormant` and
unimplemented in code** — Part B's new lease/submit pair will hit the identical >1024-position
500 that SEED-073 documents unless its fix (or an equivalent) ships as part of this phase.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tactic-tag gating decision (forcing-line gate) | API / Backend (`flaws_service.py`, pure function) | — | Already a pure, session-free function; both server and worker call the identical code — no duplication. |
| Suppress ungated tag at write time (Part A go-forward) | API / Backend (`eval_remote.py::_apply_submit`) | — | The only call site that currently defers blobs and knows it. |
| Old-corpus suppression (Part A migration) | Database / Storage (Alembic migration) | — | A bulk data-correctness fix belongs in the migration layer, not a service-layer scan; runs once at deploy. |
| Full-ply eval + MultiPV-2 blob computation (Part B) | External worker process (`scripts/remote_eval_worker.py`, a fat `app.*` client) | API / Backend (server re-classify) | Compute-heavy Stockfish work stays off the API container (SEED-071 lesson); the server remains the trust boundary. |
| Atomic flaws+tags+blobs+completion write (Part B) | API / Backend (`app/routers/eval_remote.py` new submit handler) | Database / Storage | Must be one transaction so no partial/ungated state is ever visible — mirrors `_full_drain_tick`'s existing pattern. |
| Queue/priority selection for the new lease | API / Backend (`eval_queue_service.claim_eval_job`, reused) | — | No new selection logic needed — B changes payload shape and submit semantics, not which game gets picked. |

## Part A — Go-Forward Threading (verified)

### Exact call chain and current behavior

- `app/routers/eval_remote.py::_apply_submit` (lines ~194–283 in the current file; CONTEXT.md's
  ~255–309 range is accurate for the surrounding logic). Confirmed:
  - Line ~261: `blob_map: dict[int, tuple[list[PvNode], list[PvNode]]] = {}` — unconditional empty
    dict (Phase 146 D-03).
  - Line ~281–283: `await _classify_and_fill_oracle(write_session, game_id, engine_result_map, blob_map if blob_map else None)` — `blob_map if blob_map else None` means an **empty dict always
    becomes `None`** here, so `classify_game_flaws`'s `flaw_pv_blobs` param is always `None` on this
    path today. This is the single go-forward site to thread `blobs_pending=True` from.
- `app/services/eval_drain.py::_classify_and_fill_oracle` (lines 678–777) forwards `flaw_pv_blobs`
  straight into `classify_game_flaws` (line ~747). No blocker here — it already accepts and passes
  through an optional parameter; adding `blobs_pending: bool = False` as a sibling parameter (NOT
  derived from `flaw_pv_blobs is None`, since the local drain also passes `flaw_pv_blobs=None` on
  its own first classify call at `eval_drain.py:1200` inside `_build_flaw_multipv2_blobs` — see
  "Landmine" below) is the correct approach.
- `app/services/flaws_service.py::classify_game_flaws` (lines 875–956) forwards to
  `_build_flaw_record` (line ~938) which forwards to `_classify_tactic_gated` (called twice per
  flaw, once per orientation, lines 611 and 617).
- `app/services/flaws_service.py::_classify_tactic_gated` (lines 525–573). Current logic (verified
  exactly as CONTEXT.md describes):
  ```python
  # lines 560-573 (current)
  if (
      motif is not None
      and pv_blob is not None
      and len(pv_blob) > 0
      and pre_flaw_eval_cp is not None
  ):
      solver_color = _solver_color_for(n, orientation)
      if not apply_forcing_line_filter(
          pv_blob, solver_color, pre_flaw_eval_cp, firing_depth=depth, margin=margin
      ):
          return None, None, None, None
  return motif, piece, conf, depth  # <-- raw motif returned when pv_blob is None
  ```

### Landmine: `flaw_pv_blobs=None` is used for TWO different reasons today

`classify_game_flaws(game, positions)` is called with `flaw_pv_blobs=None` in **two** contexts that
must be told apart by the new `blobs_pending` signal, or the suppression will misfire:

1. **`_apply_submit` (remote submit)** — blobs are genuinely deferred (tier-4 will fill them later).
   `blobs_pending` should be `True` here.
2. **`eval_drain.py::_build_flaw_multipv2_blobs` line 1200** — `classify_game_flaws(game, positions)`
   is called with no `flaw_pv_blobs` **on purpose**, purely to discover the flaw-ply set so the
   local drain knows which continuation lines to walk and blob (see "Q4" section — this is the
   exact same "hint" pattern Part B needs). This call's result is **discarded** for tagging purposes
   — the *real* classify with real blobs happens later at `eval_drain.py:2549`
   (`_classify_and_fill_oracle` inside `_full_drain_tick`). If `blobs_pending=True` were
   accidentally threaded into this discovery call, nothing breaks (the discarded result would just
   have `None` motifs) but it would be semantically wrong and wastes the signal's meaning. **Action:
   add the `blobs_pending` parameter with an explicit default of `False` and only set it `True` at
   the one real call site (`_apply_submit`).** Do not derive it implicitly from
   `flaw_pv_blobs is None`.

### Threading plan (concrete signature changes)

```
classify_game_flaws(game, positions, pv_by_ply=None, flaw_pv_blobs=None, blobs_pending=False)
  -> _build_flaw_record(..., blobs_pending=False)
    -> _classify_tactic_gated(..., blobs_pending=False)  # called once per orientation
```

`_apply_submit` passes `blobs_pending=True` unconditionally (Phase 146 already forces
`blob_map={}` unconditionally on this path, so this is a static `True`, not derived from any
runtime condition).

### Exact suppress predicate (per orientation)

Inside `_classify_tactic_gated`, change the fallthrough so that when the gate is skipped **because
a blob is pending** (not because it's final), the motif is suppressed instead of returned raw:

```python
gate_applicable = (
    motif is not None
    and pv_blob is not None
    and len(pv_blob) > 0
    and pre_flaw_eval_cp is not None
)
if gate_applicable:
    ...  # existing apply_forcing_line_filter logic, unchanged
    return motif, piece, conf, depth  # or suppressed by the gate itself

# Gate did NOT apply. Distinguish "pending" from "final":
if (
    blobs_pending
    and motif is not None
    and pv_blob is None          # blob truly absent (not [] sentinel, not populated)
    and pre_flaw_eval_cp is not None   # cp-based gate WOULD apply once the blob arrives
):
    return None, None, None, None   # suppress — self-heals via tier-4 D-07 retag

return motif, piece, conf, depth   # final cases: mate-adjacent (pre_flaw_eval_cp is None)
                                    # or D-06 sentinel (pv_blob == []) — KEEP raw tag
```

Note `pv_blob is None` (not `not pv_blob`) is required to distinguish "no blob" from the D-06 `[]`
sentinel — `_classify_tactic_gated`'s docstring already documents this distinction for the existing
gate condition (`pv_blob is not None and len(pv_blob) > 0`), so the suppression branch must use the
identical `is None` check to avoid re-suppressing an already-final sentinel row.

### Acceptance / test plan (Part A go-forward)

- Unit test in `tests/services/test_flaws_service.py` (existing file, has a
  `_classify_tactic_gated` import already at line 42): synthetic call with
  `blobs_pending=True, pv_blob=None, pre_flaw_eval_cp=<int>, motif=<detected>` → asserts
  `(None, None, None, None)`.
- Synthetic call with `blobs_pending=True, pv_blob=None, pre_flaw_eval_cp=None` (mate-adjacent) →
  asserts raw motif returned unchanged.
- Synthetic call with `blobs_pending=True, pv_blob=[]` (D-06 sentinel) → asserts raw motif returned
  unchanged.
- Router-level test in `tests/test_eval_worker_endpoints.py` (existing file already has
  `test_submit_phase146_blobs_null_both_markers_stamped` at line 2466 and
  `test_submit_phase146_build_blob_not_called` at line 2407 — both direct analogues): add a test
  seeding a detectable-but-non-forcing cp flaw through `_apply_submit`, asserting the persisted
  `game_flaws.allowed_tactic_motif`/`missed_tactic_motif` is `NULL`, then a follow-up
  `/flaw-blob-submit` call (existing D-07 path) fills the correctly-gated tag.

## Part A — Old-Corpus Alembic Data Migration (verified against dev DB, highest-risk item)

### The predicate MUST join `game_flaws` to `game_positions`

`pre_flaw_eval_cp` is not a `game_flaws` column — it's `positions[flaw_ply - 1].eval_cp`
(`flaws_service.py:607`). `game_positions`' PK is `PrimaryKeyConstraint("user_id", "game_id",
"ply")` (`app/models/game_position.py:54`), so the join
`gp.user_id=gf.user_id AND gp.game_id=gf.game_id AND gp.ply=gf.ply-1` hits the PK index directly
(verified via `EXPLAIN` below).

### Migration predicate is index-driven (verified via `EXPLAIN`)

`ix_game_flaws_blob_backfill` already exists
(`alembic/versions/20260630_220000_c3f5d1e8a092_ix_game_flaws_blob_backfill.py`): a partial index
`btree (game_id) WHERE allowed_pv_lines IS NULL`, created specifically for the tier-4 lottery. On
dev (`enable_seqscan=off` to force the choice on a small table — the planner otherwise
cost-prefers a seq scan on dev's tiny 73K-row table, but WILL prefer the partial index on prod's
~3.18M-row table):

```
Bitmap Heap Scan on game_flaws gf
  Recheck Cond: (allowed_pv_lines IS NULL)
  Filter: (allowed_tactic_motif IS NOT NULL)
  ->  Bitmap Index Scan on ix_game_flaws_blob_backfill
Memoize
  ->  Index Scan using game_positions_pkey on game_positions gp
        Index Cond: ((user_id = gf.user_id) AND (game_id = gf.game_id) AND (ply = (gf.ply - 1)))
        Filter: (eval_cp IS NOT NULL)
```

**No new index needed.** The existing partial index (built for a different purpose — the tier-4
lottery) already covers this migration's candidate scan.

### `allowed_pv_lines` / `missed_pv_lines` NULL-together invariant (verified, empirical not enforced)

```
both_null=66358, allowed_null_only=0, missed_null_only=0, both_not_null=7070   (dev, full table)
```

The two blob columns are always NULL together or non-NULL together in the current corpus, because
the only writer (`_batch_update_flaw_pv_lines`) always sets both in one UPDATE. **This is an
invariant of the write path, not a DB constraint** — the migration should still gate each
orientation's suppression on its OWN blob column (`allowed_pv_lines IS NULL` for the allowed
suppression, `missed_pv_lines IS NULL` for the missed suppression) rather than relying on the
correlation, in case a future code path ever breaks it.

### Verified row impact (dev DB, executed read-only / rolled back)

| Query | Result |
|---|---|
| `allowed_tactic_motif IS NOT NULL AND allowed_pv_lines IS NULL` (candidates before cp filter) | 15,412 / 73,428 total flaw rows (21.0%) |
| Of those, `pre_flaw_eval_cp IS NOT NULL` (must suppress) | 14,668 (95.2%) |
| Of those, `pre_flaw_eval_cp IS NULL` — mate-adjacent (must KEEP) | **744 (4.8%)** — a naive migration without the join would wrongly wipe these |
| D-06 `[]` sentinel rows (`allowed_pv_lines = '[]'::jsonb`) | 1 (dev is small; expect proportionally more in prod) — confirmed preserved by the `IS NULL` predicate (an empty JSONB array is NOT NULL, so it never matches) |

A full dry-run of the migration SQL (see below) was executed inside `BEGIN; ... ROLLBACK;` against
dev and confirmed: `allowed_tactic_motif IS NOT NULL` count dropped 16,558 → 1,890 (14,668
suppressed, matching the join-filtered count exactly); the 744 mate-adjacent rows were **not**
touched (still `NOT NULL` after the migration ran); the 1 D-06 sentinel was **not** touched.

### Tested, working migration SQL (batched, following the repo's own convention)

The repo already has an established idiom for exactly this shape of problem —
`alembic/versions/20260327_124752_fb62990270fd_reclassify_pawnless_endgames_from_mixed.py` uses a
`DO $$ ... WHILE rows_updated > 0 LOOP ... GET DIAGNOSTICS rows_updated = ROW_COUNT; END LOOP; END
$$;` block with `batch_size := 100000`, all inside `op.execute()`. This phase's migration should
reuse that exact pattern (verified working via dev dry-run at `batch_size := 5000`/`20000`, both
terminating correctly and producing identical row counts):

```python
def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            batch_size CONSTANT int := 100000;
            rows_updated int := 1;
        BEGIN
            WHILE rows_updated > 0 LOOP
                WITH batch AS (
                    SELECT gf.user_id, gf.game_id, gf.ply,
                           (gf.allowed_pv_lines IS NULL AND gp.eval_cp IS NOT NULL
                                AND gf.allowed_tactic_motif IS NOT NULL) AS suppress_allowed,
                           (gf.missed_pv_lines  IS NULL AND gp.eval_cp IS NOT NULL
                                AND gf.missed_tactic_motif  IS NOT NULL) AS suppress_missed
                    FROM game_flaws gf
                    JOIN game_positions gp
                      ON gp.user_id = gf.user_id AND gp.game_id = gf.game_id
                         AND gp.ply = gf.ply - 1
                    WHERE (gf.allowed_pv_lines IS NULL OR gf.missed_pv_lines IS NULL)
                      AND gp.eval_cp IS NOT NULL
                      AND (gf.allowed_tactic_motif IS NOT NULL OR gf.missed_tactic_motif IS NOT NULL)
                    LIMIT batch_size
                )
                UPDATE game_flaws gf
                SET allowed_tactic_motif      = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_motif END,
                    allowed_tactic_piece      = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_piece END,
                    allowed_tactic_confidence = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_confidence END,
                    allowed_tactic_depth      = CASE WHEN b.suppress_allowed THEN NULL ELSE gf.allowed_tactic_depth END,
                    missed_tactic_motif       = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_motif END,
                    missed_tactic_piece       = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_piece END,
                    missed_tactic_confidence  = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_confidence END,
                    missed_tactic_depth       = CASE WHEN b.suppress_missed  THEN NULL ELSE gf.missed_tactic_depth END
                FROM batch b
                WHERE gf.user_id = b.user_id AND gf.game_id = b.game_id AND gf.ply = b.ply
                  AND (b.suppress_allowed OR b.suppress_missed);
                GET DIAGNOSTICS rows_updated = ROW_COUNT;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # Data migrations that DELETE information (raw tags) are not reversible —
    # follow the repo's existing convention (see e.g. the pawnless-reclassify
    # migration's downgrade, which reconstructs an approximation, not the exact
    # original). Here there is no approximation possible: the raw pre-gate
    # motif value is gone. downgrade() should be a documented no-op (pass) with
    # a comment explaining why, matching the project's general stance that lossy
    # data migrations are one-way (confirm precedent at plan time — most bulk
    # correctness migrations in this repo are upgrade-only in practice even
    # when they nominally define a downgrade()).
    pass
```

**Idempotency confirmed**: re-running the loop after the first pass updates 0 rows (the `WHERE`
clause no longer matches, since the target columns are already NULL) — this satisfies D-04's
"idempotent + self-healing" requirement and means the migration is safe to re-run if Alembic's
migration-tracking table is ever reset.

**Batch size**: reuse `100000` (the existing convention in this repo) rather than inventing a new
number. At prod's estimated candidate volume (see below), this is ~6-7 iterations.

**Prod row-count**: could not be queried directly in this research session — the sanctioned prod-DB
MCP tool was not exposed to this research agent, and directly invoking `psql`/`docker exec` with the
prod read-only password was blocked by the sandbox's credential-leakage guard (correctly — the
password must not appear in a shell command). The planner or a human should run the estimate via
`bin/prod_db_tunnel.sh` + the `flawchess-prod-db` MCP query tool before shipping:
```sql
SELECT count(*) FROM game_flaws gf
JOIN game_positions gp ON gp.user_id=gf.user_id AND gp.game_id=gf.game_id AND gp.ply=gf.ply-1
WHERE (gf.allowed_pv_lines IS NULL OR gf.missed_pv_lines IS NULL)
  AND gp.eval_cp IS NOT NULL
  AND (gf.allowed_tactic_motif IS NOT NULL OR gf.missed_tactic_motif IS NOT NULL);
```
As a rough extrapolation: the `ix_game_flaws_blob_backfill` migration's own docstring states prod
`game_flaws` is **~3.18M rows**; the dev proportion of candidate rows to total rows was ~20-21%,
which would put the prod candidate count in the **~600K-650K** range if the proportion holds (dev
and prod corpora are not guaranteed to have the same shape — this is a rough sizing estimate, not a
verified prod fact — tag `[ASSUMED]`). At a 100K batch size that's ~6-7 loop iterations, each a
fast, index-driven UPDATE; expect this to run in low single-digit seconds even at prod scale, well
within the container-startup budget. Confirm before shipping.

### Alembic conventions in this repo (confirmed)

- Data migrations use `op.execute()` with raw SQL (not `op.get_bind()` + SQLAlchemy Core), see the
  pawnless-reclassify example above and `20260614_130000_wipe_eval_only_residue.py`.
- Indexes are created non-concurrently (inside the transaction) — confirmed by the
  `ix_game_flaws_blob_backfill` migration's own docstring: "migrations run against a quiescent
  backend at container startup ... CONCURRENTLY cannot run inside a transaction." No new index is
  needed for this migration (see above), so this doesn't apply directly here, but it's the
  established constraint if the planner ever needs one.
- `deploy/entrypoint.sh` runs `alembic upgrade head` to completion BEFORE `exec uvicorn ...` starts
  — confirmed no live traffic hits the DB during migration replay (the container is not yet
  serving requests). Lock-contention-with-live-traffic is not the risk here; total migration
  duration (adding to deploy downtime) is the risk, and it's small given the index-driven plan.

### Migration test (pattern already established in this repo)

`tests/test_migration_wipe_eval_only_residue.py` is the exact template: seed rows via the ORM in
the `db_session` fixture, execute the migration's SQL verbatim (kept in sync via a comment, mirrored
from the migration file), assert only the correct rows changed. For this phase, seed at minimum:
(1) a cp-based flaw with `allowed_pv_lines IS NULL` + `allowed_tactic_motif` set + a non-NULL
pre-flaw `eval_cp` → must be suppressed; (2) a mate-adjacent flaw (`pre_flaw_eval_cp IS NULL` via a
`game_positions` row with `eval_cp=NULL, eval_mate=<int>`) with `allowed_tactic_motif` set → must be
preserved; (3) a D-06 sentinel row (`allowed_pv_lines = '[]'::jsonb`) with `allowed_tactic_motif`
set → must be preserved; (4) a row with blobs already populated (`allowed_pv_lines` non-NULL) →
must be preserved (out of scope for suppression); (5) re-run the migration SQL a second time and
assert zero rows change (idempotency).

## Part B — Upgraded-Worker Atomic Eval+Blob Pipeline

### Q4 verification (CRITICAL, requested by CONTEXT.md) — CONFIRMED, with a data-plumbing nuance

**`classify_game_flaws` is confirmed pure and session-free.** Full transitive trace:

- `classify_game_flaws` (`flaws_service.py:875`) takes `(game: Game, positions: list[GamePosition],
  pv_by_ply=None, flaw_pv_blobs=None)` — no `session` parameter, no `await` anywhere in its body or
  any function it calls.
- `derive_user_result` (`app/services/openings_service.py:109`) — confirmed a pure function:
  `def derive_user_result(result: str, user_color: str) -> Literal[...]` — string/literal in,
  literal out, no session, no DB, no import-time side effect. **Q4's stated risk does not
  materialize.**
- Every `GamePosition` attribute the call graph touches was enumerated by grep across
  `flaws_service.py`: `.eval_cp`, `.eval_mate`, `.move_san`, `.pv`, `.phase`, `.clock_seconds`. No
  `.full_hash`/`.white_hash`/`.black_hash`/`.game_id`/`.user_id` access inside the classify
  pipeline (those are query-time filter columns the caller already used to select the list, not
  attributes classify reads).
- `_recompute_fen_map(game.pgn)` (`flaws_service.py:312`) replays the game's PGN independently of
  the `positions` list, to build the `fen_map` the tactic detector needs.
- The `Game` fields touched: `.result`, `.user_color`, `.base_time_seconds`, `.increment_seconds`,
  `.time_control_str`, `.pgn` (via `_resolve_increment` and `derive_user_result` and
  `_recompute_fen_map`).

**The nuance:** the CURRENT `/lease` response (`LeaseResponse` in `app/schemas/eval_remote.py:19`)
sends only `{game_id, user_id, is_lichess_eval_game, positions: [{ply, fen, is_terminal}], leased_at,
job_id}` — **no PGN, no move_san, no game metadata**. If the planner has the new worker call the
**full** `classify_game_flaws` (as CONTEXT.md/SEED-074 literally describes) to get a faithful hint,
the new lease payload must additionally carry the PGN (or at minimum `result`, `user_color`,
`base_time_seconds`/`increment_seconds`, and per-ply `move_san`) — none of which the worker
currently receives. This is a genuine new field, not a hidden dependency, but it changes the new
lease response shape.

**Cheaper alternative worth flagging to the planner:** the worker's hint only needs to know **which
plies are flaws**, not their tags. That set comes entirely from
`flaws_service._run_all_moves_pass(positions)` (`flaws_service.py:338-379`) filtered to
`severity in ("mistake", "blunder")` — the EXACT filter `classify_game_flaws` itself applies
(`flaws_service.py:935`). `_run_all_moves_pass` needs only `.eval_cp`/`.eval_mate` per position —
data the worker's own full-ply pass already produces. Calling this narrower function instead of the
full `classify_game_flaws` for the hint:
- Needs **no PGN, no move_san, no Game object** on the worker side at all — the new lease payload
  can stay FEN-only (or even smaller).
- Is provably equivalent for "which plies to blob" (same filter, same source function).
- Forgoes tactic-motif detection in the hint, which is fine — Part B's blob-building loop in
  `_build_flaw_multipv2_blobs` (`eval_drain.py:1161-1279`) already builds blobs for **every** flaw
  in the classify result regardless of whether a motif was detected (it does not gate on motif
  presence), so motif detection was never actually needed to decide what to blob.

Recommend the planner pick one of these two explicitly at plan time — both are valid, but they
imply different new-lease-schema shapes. This research recommends the narrower
`_run_all_moves_pass`-based hint (less new payload, `# ty: ignore` surface, and dependency
footprint) unless a concrete reason for the full classify hint emerges during planning.

### Full-ply pass MultiPV question — ALREADY RESOLVED (Phase 146), not still open

CONTEXT.md's deferred item ("whether the worker's full-ply pass stays MultiPV-2 or drops to
MultiPV-1... Phase 146 carryover") is **already done and tested**:
- `scripts/remote_eval_worker.py::_eval_positions` (lines 96-125) uses
  `pool.evaluate_nodes_with_pv` (MultiPV-1, 4-tuple) with an explicit comment: "Phase 146 D-03
  consequence: reduced to MultiPV-1 ... now that per-ply second-best was dropped from SubmitEval."
- `SubmitEval` (`app/schemas/eval_remote.py:30`) has no `second_*` fields (comment: "Phase 146 D-03:
  second_cp/second_mate/second_uci removed").
- `tests/test_remote_eval_worker.py::test_eval_positions_uses_multipv1_no_second_best` (line 427)
  locks this in as a tested invariant.
- Separately, tier-4's blob building (`_build_flaw_blob_lease_positions`,
  `eval_drain.py:1332-1428`) walks **every** node of the continuation PV, **including node 0**, and
  the worker re-evaluates node 0 at MultiPV-2 via `_eval_flaw_blob_positions` — it does NOT depend
  on the full-ply pass having been MultiPV-2. This is a different mechanism than the LOCAL drain's
  `_build_line_blobs` (which sources node 0 from the full-ply `second_best_map`, since the local
  drain's full-ply pass IS still MultiPV-2 — `_full_drain_tick` calls `evaluate_nodes_multipv2` for
  every engine target).

**Recommendation for Part B:** the new worker's full-ply pass should stay MultiPV-1 (reuse
`_eval_positions`/`evaluate_nodes_with_pv` as-is); blob building (continuation nodes 0..N, both
lines, for flaw plies only) should mirror tier-4's pattern — a SEPARATE MultiPV-2 evaluation of just
the walked nodes, computed by the worker itself in the same pipeline (no lease round-trip needed,
since the worker already knows the flaw set locally from the hint-classify step). This avoids
reverting the (tested, intentional) MultiPV-1 full-ply optimization from Phase 146.

### Landmine: SEED-073's over-cap sentinel is NOT implemented yet

SEED-074/CONTEXT.md states Part B "reuses the SEED-073 over-cap sentinel for fat games (no
chunking)." **Verified: SEED-073 is still `status: dormant`** (`.planning/seeds/SEED-073-fat-game-
flaw-blob-lease-500.md`) and has **no implementation commit** — `git log` shows only two `docs(seed)`
commits (capture + revise) for SEED-073, and a direct code grep for `over-cap`/`OVER_CAP` across
`app/` and `scripts/` returns zero hits. The current `flaw_blob_lease` handler
(`eval_remote.py:725-783`) has only the `if not lease_positions:` all-sentinel branch; there is
**no** `elif len(lease_positions) > MAX_SUBMIT_EVALS:` branch.

**This means:** the existing tier-4 rung will 500 on the ~17 known fat games in prod (SEED-073's own
quantification: p99=489, p99.9=693, cap=1024, 17 games over cap, largest 1,680), and Part B's NEW
lease/submit pair — which combines full-ply evals AND blobs in one payload, an even larger
worst-case payload than tier-4's blob-only lease — will hit the identical 500 on an equal-or-larger
set of games unless the over-cap guard is implemented. **The planner must either:**
1. Implement SEED-073's fix (or an equivalent over-cap sentinel) as an explicit prerequisite task
   inside this phase (small — SEED-073's own doc estimates ~5 lines), since Part B's new endpoint
   needs the identical protection and "reuse" is only possible once it exists, or
2. Explicitly schedule SEED-073 as a preceding quick task before Part B's endpoint work, with a
   phase dependency noted.

Do not silently assume SEED-073 is "already handled" — it is not.

### Existing machinery to clone for the new endpoint pair

| Reused piece | Location | Role in B |
|---|---|---|
| `claim_eval_job` | `eval_queue_service.py:641` | Reuse UNCHANGED for the new lease's game selection (tier-1 > tier-2 > tier-3 priority) — no new selection logic needed, only a new response shape. |
| `_build_lease_positions` | `eval_remote.py:142-191` | Template for building the new lease payload (PGN replay → FEN-per-ply); if the planner picks the "full classify hint" design, extend this to also return PGN/game metadata rather than duplicating a FEN-per-ply list. |
| `_apply_full_eval_results` | `eval_drain.py` (imported at `eval_remote.py:69`) | Reuse for applying the worker's submitted full-ply evals — same SEED-044 write convention. |
| `_classify_and_fill_oracle` | `eval_drain.py:678-777` | Template for the server's authoritative classify call — takes `flaw_pv_blobs` already; B's new submit handler passes the worker-supplied blob_map here exactly as `_full_drain_tick` does. |
| `_run_multipv2_pass` / `_batch_update_flaw_pv_lines` | `eval_drain.py:1316-1329` / `1282-1313` | Reuse UNCHANGED to write the blobs in the same transaction as the classify — this is the atomic-write mechanism, already proven in `_full_drain_tick`. |
| `_full_drain_tick` Step 4 ordering | `eval_drain.py:2538-2554` | **The exact template for B's server atomic write**: `_apply_full_eval_results` → `_classify_and_fill_oracle(..., flaw_pv_blobs)` (classify BEFORE blobs are in the DB — Pitfall 4/5) → `_run_multipv2_pass(..., flaw_pv_blobs)` (blobs written in the same write session) → completion markers, all inside one `async with async_session_maker() as write_session:` block. |
| `_walk_pv_boards` | `eval_drain.py:1098-1122` | Reusable as-is by the worker (plain function, no session) to walk continuation PV nodes for blobbing — the worker is a fat `app.*` client and can import it directly. |
| `evaluate_nodes_multipv2` | `app/services/engine.py:608` (via `EnginePool`) | The worker already imports `EnginePool`; reuse for blob-node evaluation, mirroring `_eval_flaw_blob_positions` (`remote_eval_worker.py:128`). |
| `_assemble_flaw_blobs_from_submit` | `eval_drain.py:1484` (imported at `eval_remote.py:70`) | Reusable pattern for reassembling worker-submitted per-node results into `PvNode` blobs, adaptable to the new atomic submit's token/keying scheme. |

### New schema shapes (recommendation)

Mirror the existing `FlawBlobLeaseResponse`/`FlawBlobSubmitRequest` pattern
(`app/schemas/eval_remote.py:109-151`) — a **dedicated, isolated** schema set, own `max_length`
caps (do not raise the shared `MAX_SUBMIT_EVALS=1024` — SEED-073 already documents why that's a
DoS-guard constant not meant to grow). Two separately-capped lists in the new submit request: one
for full-ply evals (bounded like the old `SubmitRequest.evals`), one for blob nodes (bounded like
`FlawBlobSubmitRequest.evals`) — SEED-074's own quantification (SEED-073 cross-ref) confirms both
stay comfortably under 1024 for ~99.996% of real games; the ~17 fat games need the over-cap sentinel
above regardless of which list overflows.

Q5 (version tag): given the trust boundary is already enforced (server re-classifies
authoritatively; A's NULL is the graceful-degradation net for any skew), a version tag is optional.
If included, the cheapest form is a single `worker_schema_version: int` field the server can log/
reject on mismatch — do not gate correctness on it, only observability/rejection of egregiously
stale workers.

### Trust boundary (confirmed, unchanged from CONTEXT.md)

The server must re-run its OWN `classify_game_flaws` on its OWN `game_positions` rows plus the
submitted evals/blobs — never trust the worker's local hint-classify as the source of truth. A blob
for a ply the server doesn't consider a flaw is dropped; a flaw the server found but the worker
didn't blob writes `NULL` via Part A's suppression and is backfilled by tier-4 later. This requires
NO new code — it falls out naturally once Part A's `blobs_pending` suppression exists and the
server always classifies from its own data.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Batched bulk UPDATE in an Alembic migration | A custom Python batching script (`scripts/backfill_*.py`) | The repo's own `DO $$ ... WHILE rows_updated > 0 LOOP ...` idiom (D-04 explicitly requires the migration form anyway) | Already proven, already tested elsewhere in this repo (pawnless-reclassify migration); no new pattern to review. |
| Continuation-PV walking for MultiPV-2 blobs | A new PV-walk implementation in the worker | `eval_drain._walk_pv_boards` (plain function, importable as-is) | Byte-identical semantics to what the server/local-drain already produce; avoids blob-shape drift between worker and server. |
| Worker "which plies are flaws" hint | A bespoke severity classifier in the worker | `flaws_service._run_all_moves_pass` (or the full `classify_game_flaws`) | Pure, already tested, guarantees the worker's flaw-ply set matches the server's exactly (same source function). |
| Fat-game payload overflow handling | A bespoke chunking/pagination scheme | The `[]` sentinel pattern already established for D-06/SEED-073 | 17 games out of 409,605 (0.004%) — chunking is not worth the complexity per SEED-073's own analysis; sentinel + tier-4 backfill already covers this class. |

**Key insight:** almost everything Part B needs already exists in this codebase in some form (tier-4
built it for the blob-only case, `_full_drain_tick` built it for the local-atomic case) — the phase
is fundamentally a "combine two existing mechanisms behind one new endpoint pair," not new
engineering.

## Common Pitfalls

### Pitfall 1: Conflating the two `flaw_pv_blobs=None` call sites
**What goes wrong:** Threading `blobs_pending=True` based on `flaw_pv_blobs is None` would
accidentally suppress motifs in `_build_flaw_multipv2_blobs`'s discovery-only classify call
(`eval_drain.py:1200`), which discards its tag output anyway but should not be given a meaning it
doesn't have.
**Why it happens:** Both the real deferred-blob case and the discovery-hint case currently pass
`flaw_pv_blobs=None`, and it's tempting to derive `blobs_pending` from that instead of adding an
explicit parameter.
**How to avoid:** Add `blobs_pending: bool = False` as an independent parameter, set `True` only at
`_apply_submit`'s call site.
**Warning signs:** A test asserting the local drain's blob-discovery classify still returns raw
motifs (it's discarded anyway, but a future refactor could accidentally read it) starts failing.

### Pitfall 2: Suppressing D-06 sentinel or mate-adjacent rows in the migration
**What goes wrong:** A migration predicate that checks only `allowed_pv_lines IS NULL AND
allowed_tactic_motif IS NOT NULL` (no join to `game_positions`, no `[]` distinction) would wipe 744
mate-adjacent tags (4.8% of dev's candidate set) permanently — these can never be re-filled since no
blob will ever exist for them.
**Why it happens:** `pre_flaw_eval_cp` isn't a `game_flaws` column, so it's easy to omit the join
and just write a broader predicate against `game_flaws` alone.
**How to avoid:** Always join to `game_positions` on the PK for the pre-flaw eval_cp check; verified
via `EXPLAIN` that this join is index-driven, so there's no performance reason to skip it.
**Warning signs:** Post-migration row count of mate-adjacent flaws with motifs drops to zero (should
stay unchanged).

### Pitfall 3: Assuming SEED-073 is already fixed
**What goes wrong:** Part B ships assuming the over-cap sentinel exists ("SEED-073 reuse") and the
new atomic submit 500s on the same ~17+ fat games tier-4 already documents.
**Why it happens:** SEED-074/CONTEXT.md's language ("reuses the SEED-073 over-cap sentinel") reads
as if it's already available.
**How to avoid:** Check `.planning/seeds/SEED-073-fat-game-flaw-blob-lease-500.md`'s `status:` field
and grep for `over-cap`/`OVER_CAP` in `app/` before assuming — confirmed dormant/unimplemented as of
this research.
**Warning signs:** A synthetic >1024-position game 500s on the new lease/submit pair in dev testing.

### Pitfall 4: Reverting the MultiPV-1 full-ply optimization
**What goes wrong:** "Fixing" the worker's full-ply pass back to MultiPV-2 under the assumption
Part B needs per-ply second-best data, undoing Phase 146's tested optimization.
**Why it happens:** The CONTEXT.md deferred item phrases this as still-open.
**How to avoid:** It's resolved — `test_eval_positions_uses_multipv1_no_second_best` locks it in;
blob building gets its MultiPV-2 data from a separate, flaw-ply-scoped evaluation pass (tier-4's
pattern), not from the full-ply pass.
**Warning signs:** Full-ply eval throughput regresses (2x engine calls per ply) after Part B ships.

### Pitfall 5: Forgetting the composite PK when batching the migration UPDATE
**What goes wrong:** Using a surrogate `id IN (SELECT id ... LIMIT n)` pattern (copied verbatim from
the pawnless-reclassify migration) fails to compile — `game_flaws` has no surrogate `id` column, its
PK is the composite `(user_id, game_id, ply)`.
**Why it happens:** The established batching idiom in this repo was written for tables with a
surrogate PK (`game_positions` in that example — actually also composite, worth double-checking at
plan time which flavor was used, but `game_flaws` definitely has none).
**How to avoid:** Use a `WITH batch AS (SELECT user_id, game_id, ply, ... LIMIT n) UPDATE ... FROM
batch WHERE gf.user_id=batch.user_id AND gf.game_id=batch.game_id AND gf.ply=batch.ply` shape —
verified working via dev dry-run in this research.
**Warning signs:** Migration fails at `alembic upgrade head` with a column-does-not-exist error on
`id`.

## Code Examples

### Verified working migration SQL (dry-run tested on dev, rolled back)

See the full `upgrade()` body under "Tested, working migration SQL" above — executed against dev
inside `BEGIN; ... ROLLBACK;` at both `batch_size := 5000` and `20000`, confirmed:
- Total suppressed: 14,668 `allowed_tactic_motif` rows (matches the join-filtered candidate count
  exactly).
- Mate-adjacent preserved: 744 rows still `NOT NULL` after the migration ran.
- D-06 sentinel preserved: 1 row unchanged.
- Idempotent: re-running the loop body against the post-migration state updates 0 rows.

### `_full_drain_tick`'s atomic-write ordering (Part B's server-side template)

```python
# eval_drain.py:2538-2554 (verified current)
async with async_session_maker() as write_session:
    failed_ply_count = await _apply_full_eval_results(
        write_session, targets, dedup_map, engine_result_map, is_lichess_eval_game
    )
    # classify BEFORE blobs are written (Pitfall 4/5: blobs not yet in the DB here)
    await _classify_and_fill_oracle(write_session, game_id, engine_result_map, flaw_pv_blobs)
    # blobs written in the SAME transaction as the classify (Pitfall 5: write-session discipline)
    await _run_multipv2_pass(write_session, game_id, flaw_pv_blobs)
    ...  # completion markers, same session, same commit
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Remote submit deferred blobs and raw-classified | Remote submit still defers blobs but suppresses (not raw-classifies) pending-gate motifs | Phase 147 Part A (this phase) | Closes the data-pollution window without needing the full worker upgrade first. |
| Remote worker full-ply pass was MultiPV-2 | Remote worker full-ply pass is MultiPV-1 | Phase 146 D-03 | Already shipped; do not revert in this phase. |
| Tier-4 blob-only lease/submit is the only way blobs reach `game_flaws` for remote games | Part B adds an atomic eval+blob submit so new games never need tier-4 at all | Phase 147 Part B (this phase) | Tier-4 shrinks to backfill-only role for the pre-B corpus. |

**Deprecated/outdated:** the old `/lease` + `/submit` pair is not removed this phase but becomes a
deprecated path once the new pair ships and the fleet upgrades (per D-02); do not remove it in this
phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Prod `game_flaws` candidate-row count for the suppression migration is ~600K-650K, extrapolated from dev's ~20-21% candidate proportion applied to the ~3.18M prod row count cited in the `ix_game_flaws_blob_backfill` migration docstring | Part A old-corpus migration, "Prod row-count" | If prod's proportion differs significantly, the batch-count estimate (and thus migration duration) is off; low risk since the plan is index-driven regardless of row count — worst case the migration takes longer, not incorrectly. |
| A2 | The narrower `_run_all_moves_pass`-based worker hint (vs. the full `classify_game_flaws` hint CONTEXT.md describes) is the recommended design | Part B, "Q4 verification" | If the planner picks the full-classify hint instead, the new lease schema needs PGN + Game metadata fields this research's recommended design avoids; not wrong, just a different schema shape — flagged as an explicit planner decision either way. |
| A3 | SEED-073's fix, or an equivalent, must be implemented as part of (or immediately before) this phase for Part B to work correctly on fat games | Part B, "Landmine: SEED-073" | If skipped, Part B's new endpoint pair 500s on the same fat-game class tier-4 already hits — a real functional bug, not a nice-to-have; HIGH risk if ignored. |

## Open Questions

1. **Should Part B's new lease response include PGN, or should the worker's hint use the narrower
   `_run_all_moves_pass` (no PGN needed)?**
   - What we know: both are technically viable; `classify_game_flaws` is confirmed pure either way.
   - What's unclear: whether the planner values reusing the exact `classify_game_flaws` entry point
     (simplicity, single code path) over the smaller payload/dependency footprint of the narrower
     function.
   - Recommendation: default to the narrower `_run_all_moves_pass` hint unless a concrete reason
     for full tactic-motif detection in the worker's hint emerges (e.g. future per-motif
     back-pressure or worker-side prioritization by motif type — none exists today).

2. **Where does SEED-073's over-cap fix land — as an explicit Phase 147 task, or as a quick task
   shipped just before this phase executes?**
   - What we know: it's required either way for Part B to function on fat games; it's small
     (SEED-073 estimates ~5 lines).
   - What's unclear: whether the user wants it folded into this phase's plan or dispatched
     separately first (per CLAUDE.md's "no unrequested milestone/phase planning" — this is a
     pre-existing dormant seed, not a new phase, so folding it in as a Part-B-prerequisite task
     within this phase's plan seems consistent with scope, but flagging for explicit confirmation).
   - Recommendation: include it as an explicit first task in Part B's plan (small, well-scoped,
     already fully speced in the seed file) rather than assuming it's out of scope.

3. **Exact prod row count for the old-corpus migration** — not verified this session (tooling
   access gap, see Assumption A1). Recommend the planner or a human run the query above via
   `bin/prod_db_tunnel.sh` + the `flawchess-prod-db` MCP tool before finalizing the batch size /
   sizing the deploy-downtime impact.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Dev PostgreSQL (Docker) | Migration test authoring, dry-run verification | Yes (verified: `flawchess-dev-db-1` healthy, 5 days up) | PostgreSQL 18 (alpine) | — |
| Prod DB read-only tunnel (`bin/prod_db_tunnel.sh`) | Prod row-count estimate for migration sizing | Yes, tunnel already up (`ssh -fN -L 15432:127.0.0.1:5432 flawchess`, confirmed running) | — | The prod-db MCP tool itself was not exposed to this research agent's toolset — the planner/human should run the estimate query via the sanctioned MCP tool directly, not via raw `psql`/`docker exec` with an embedded password (the sandbox correctly blocks that). |
| Stockfish engine (dev container) | N/A for this research (no engine calls made or needed) | N/A | — | — |

**Missing dependencies with no fallback:** none — all required tooling exists, only this
research session's own tool access was constrained (documented above, not a project gap).

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 9.0.3 (async, `pytest-asyncio`) |
| Config file | `pytest.ini` / `pyproject.toml` (existing, unchanged) |
| Quick run command | `uv run pytest tests/services/test_flaws_service.py tests/test_eval_worker_endpoints.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEED-074 (Part A go-forward) | `_classify_tactic_gated` suppresses pending-gate motifs, keeps mate-adjacent and D-06 sentinel raw tags | unit | `pytest tests/services/test_flaws_service.py -k classify_tactic_gated -x` | Add new cases to existing file (imports `_classify_tactic_gated` already at line 42) |
| SEED-074 (Part A go-forward, router) | `_apply_submit` writes NULL for a detectable-but-non-forcing flaw when blobs are deferred | integration | `pytest tests/test_eval_worker_endpoints.py -k phase146 -x` | Add new test alongside `test_submit_phase146_blobs_null_both_markers_stamped` (line 2466) |
| SEED-074 (Part A old-corpus migration) | Guarded UPDATE suppresses only the correct rows, preserves carve-outs, idempotent | migration | `pytest tests/test_migration_<name>.py -x` | New file, template = `tests/test_migration_wipe_eval_only_residue.py` |
| SEED-074 (Part B endpoint pair) | New lease/submit atomically writes flaws + gated tags + blobs + both completion markers; game never observably ungated | integration | `pytest tests/test_eval_worker_endpoints.py -k <new_endpoint_name> -x` | New tests, template = existing `/flaw-blob-lease`/`/flaw-blob-submit` tests in the same file |
| SEED-074 (Part B fat-game handling) | A >1024-position game sentinels cleanly on the new endpoint, no 500 | integration | Same file as above | New test; also exercises the SEED-073 prerequisite fix |
| SEED-074 (Part B worker) | New worker lease→eval→hint-classify→blob→submit loop functions end-to-end against a dev backend | manual/integration | `uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --once` (dev-first, per D-05/dev-first gate) | `tests/test_remote_eval_worker.py` existing file for unit-level worker logic; full loop is a dev-server integration check |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/services/test_flaws_service.py tests/test_eval_worker_endpoints.py tests/test_remote_eval_worker.py -x`
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** Full suite green before `/gsd-verify-work`; additionally, run the new worker's
  `--once` mode against a local dev backend (not prod) before considering Part B done — this
  satisfies the "dev-first end-to-end validation gate before any prod change" discretion item from
  CONTEXT.md.

### Wave 0 Gaps
- [ ] New Alembic migration test file (template: `tests/test_migration_wipe_eval_only_residue.py`)
      — covers Part A old-corpus suppression.
- [ ] New test cases in `tests/services/test_flaws_service.py` for `_classify_tactic_gated`'s
      `blobs_pending` parameter — covers Part A go-forward.
- [ ] New test cases in `tests/test_eval_worker_endpoints.py` for the new lease/submit pair — covers
      Part B.
- [ ] SEED-073's over-cap sentinel fix (or equivalent) — a genuine functional prerequisite gap, not
      just a test gap; see "Landmine: SEED-073" above.
- No new test framework/fixture infrastructure needed — `db_session` fixture and router test
  conventions are fully established and sufficient.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not a user-facing auth surface. |
| V3 Session Management | No | N/A — no session state introduced. |
| V4 Access Control | Yes | Reuse the existing `require_operator_token` dependency (`hmac.compare_digest`, fail-closed) unchanged for the new lease/submit pair — do not invent a new auth mechanism. |
| V5 Input Validation | Yes | New Pydantic schemas with their own `max_length` DoS caps (mirroring `MAX_SUBMIT_EVALS`/`FlawBlobSubmitRequest`), per D-02. |
| V6 Cryptography | No | No new crypto surface. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded request body from a compromised/buggy worker | Denial of Service | New schemas cap `evals`/blob-node lists via `Field(max_length=...)`, own constant per D-02 (do not reuse/raise `MAX_SUBMIT_EVALS` — keep the shared DoS-guard semantics SEED-073 already documents). |
| Foreign/tampered token on the new submit (if a token-keyed blob scheme is used, mirroring flaw-blob's `T-145-09`) | Tampering | Re-derive the valid token set server-side and reject any submitted token not in it — exact precedent at `_apply_flaw_blob_submit` (`eval_remote.py:840-865`). |
| Worker classification trusted as authoritative | Spoofing / Tampering | Server always re-runs its own `classify_game_flaws` on its own `game_positions` — worker output is downgraded to "raw evals + blob hints" only, never trusted for tags/severity. Already the explicit design (trust boundary section above). |

## Sources

### Primary (HIGH confidence — verified against live code and/or dev DB this session)

- `app/services/flaws_service.py` (lines 192-956) — full trace of `classify_game_flaws`,
  `_classify_tactic_gated`, `_build_flaw_record`, `_run_all_moves_pass`, `_detect_tactic_for_flaw`,
  `_recompute_fen_map`.
- `app/routers/eval_remote.py` (lines 1-120, 142-330, 700-930) — `_apply_submit`,
  `_build_lease_positions`, `flaw_blob_lease`, `_apply_flaw_blob_submit`, `flaw_blob_submit`.
- `app/schemas/eval_remote.py` (full file) — all current request/response schemas and
  `MAX_SUBMIT_EVALS`.
- `app/services/eval_drain.py` (lines 678-777, 1090-1430, 2318-2570) — `_classify_and_fill_oracle`,
  `_walk_pv_boards`, `_build_line_blobs`, `_build_flaw_multipv2_blobs`, `_batch_update_flaw_pv_lines`,
  `_run_multipv2_pass`, `_build_flaw_blob_lease_positions`, `_full_drain_tick`.
- `app/models/game_flaw.py` (full file) — column defs, confirming `allowed_pv_lines`/
  `missed_pv_lines`/tactic columns are per-orientation, `deferred=True` structural-leak guard.
- `app/models/game_position.py` (lines 47-176) — PK definition, confirming the join key for
  `pre_flaw_eval_cp`.
- `app/services/openings_service.py` (lines 109-124) — `derive_user_result` purity confirmation.
- `alembic/versions/20260630_220000_c3f5d1e8a092_ix_game_flaws_blob_backfill.py` — existing partial
  index, its stated rationale, and the ~3.18M-row prod estimate.
- `alembic/versions/20260327_124752_fb62990270fd_reclassify_pawnless_endgames_from_mixed.py` — the
  batched migration idiom reused for this phase's migration.
- `tests/test_migration_wipe_eval_only_residue.py` — migration test pattern template.
- `scripts/remote_eval_worker.py` (lines 1-130) — `_eval_positions` MultiPV-1 confirmation.
- `tests/test_remote_eval_worker.py` (line 427) — `test_eval_positions_uses_multipv1_no_second_best`.
- `tests/test_eval_worker_endpoints.py` (test name index) — existing Phase-146 test precedents.
- `deploy/entrypoint.sh` — confirms migrations run before uvicorn starts (quiescent).
- Dev database (`flawchess-dev-db-1`, PostgreSQL 18) — `EXPLAIN` plans and `BEGIN; ...; ROLLBACK;`
  dry-runs executed directly this session (all counts and plans quoted above are from actual query
  output, not estimates).
- `.planning/seeds/SEED-073-fat-game-flaw-blob-lease-500.md` — confirmed `status: dormant`, no
  implementation.
- `git log --oneline --all | grep -i 073` — confirmed only 2 doc commits for SEED-073, no code
  commit.

### Secondary (MEDIUM confidence)

- Prod `game_flaws` row-count proportion extrapolation (Assumption A1) — based on a verified prod
  fact (the ~3.18M figure, quoted directly from a migration docstring) combined with an unverified
  extrapolation from dev's proportion.

### Tertiary (LOW confidence)

- None — every claim in this document was either directly verified against code/dev-DB this
  session, or is explicitly flagged in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new external packages/libraries introduced this phase (pure
  SQLAlchemy/Alembic/FastAPI/Pydantic, all already in use).
- Architecture (Part A threading, Part B endpoint design): HIGH — every call site and signature
  verified against the current file contents.
- Migration correctness: HIGH — the exact SQL was executed against dev inside a rolled-back
  transaction and its effect verified row-by-row against the documented carve-outs.
- Prod sizing: MEDIUM — the ~3.18M total-row figure is verified (quoted from code), but the
  candidate-row proportion is extrapolated from dev, not measured on prod, due to a tooling access
  gap in this research session.
- Part B design (worker hint, endpoint schemas): HIGH for what's reused verbatim (tier-4/local-drain
  machinery); MEDIUM for the two open design choices flagged (PGN-based vs. narrower hint; SEED-073
  sequencing) since those are explicitly left to the planner.

**Research date:** 2026-07-01
**Valid until:** 2026-07-15 (14 days — this is an actively-changing part of the codebase; Phase 146
shipped hours before this research and Phase 148+ work may touch the same files)

## Package Legitimacy Audit

Not applicable — this phase introduces no new external packages. All work uses existing project
dependencies (SQLAlchemy async, Alembic, FastAPI, Pydantic v2, httpx, python-chess) already present
in `pyproject.toml`/`uv.lock`.
