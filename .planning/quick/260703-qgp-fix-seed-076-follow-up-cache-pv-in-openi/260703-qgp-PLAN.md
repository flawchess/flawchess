---
phase: quick-260703-qgp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/opening_position_eval.py
  - alembic/versions/*_add_pv_to_opening_position_eval.py
  - app/services/eval_drain.py
  - app/routers/eval_remote.py
  - tests/test_eval_worker_endpoints.py
  - tests/services/test_eval_drain.py
  - tests/services/test_full_eval_drain.py
autonomous: true
requirements: [SEED-076-FOLLOWUP]
must_haves:
  truths:
    - "An opening flaw in a remote/atomic-analyzed game whose node-0 position was cached retains a real PV walk (not a permanent []-sentinel)."
    - "game_positions.pv at flaw-adjacent opening plies is filled from the cache on the atomic-submit path (no engine call made there)."
    - "opening_position_eval carries a nullable pv column; new cache writes populate it and existing pv-less rows self-heal on next write."
    - "A pv-less cache row does not cause the worker to skip evaluating that opening position (still leased); a pv-bearing row does (omitted from lease)."
  artifacts:
    - "opening_position_eval.pv column + Alembic migration"
    - "4-tuple dedup_map (eval_cp, eval_mate, best_move, pv) threaded through eval_drain.py + eval_remote.py"
    - "Regression tests in tests/test_eval_worker_endpoints.py"
  key_links:
    - "engine_result_map merge in both submit paths runs BEFORE _derive_atomic_sentinel_lines (atomic) / _classify_and_fill_oracle (both)"
    - "_fetch_cached_opening_hashes gates lease omission on pv IS NOT NULL"
---

<objective>
Fix the SEED-076 regression: the cache-aware lease omits cached opening positions so the worker never evaluates them and no PV reaches the row; the submit dedup fill has no pv column to draw from, so opening flaws at those plies get a NULL game_positions.pv and are then permanently []-sentineled by the tier-4 blob backfill (their PV lines + tactic tags lost). ~1 in 10 flaws in remote-analyzed games are affected.

Purpose: cache the pv alongside the eval so dedup transplants carry a walkable PV; merge it into engine_result_map at submit so classify writes it and the sentinel derivation correctly walks it.

Output: nullable `pv` column on opening_position_eval, a 4-tuple dedup_map threaded through both files, cache population + self-heal, both submit paths merging cached pv into engine_result_map, a pv-gated lease omission, and regression coverage. Go-forward fix (main unreleased, nothing broken in prod).
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/seeds/closed/SEED-076-drain-timeout-hole-hardening.md
@app/models/opening_position_eval.py
@app/services/eval_drain.py
@app/routers/eval_remote.py

Key facts (already verified against the code):
- Alembic head is `eb341e836ee9`.
- dedup_map annotation `dict[int, tuple[int | None, int | None, str | None]]` appears at eval_drain.py lines 319, 371, 539, 949, 975, 1045, 1090/1092/1161/1195/1197 (second_best_map shares the 3-tuple shape but is a DIFFERENT map — do NOT widen second_best_map), 2602.
- Unpack sites: eval_drain.py:388 (`_resolve_full_eval`), 967 (`_reconstruct_pos_eval`, uses `_bm`).
- `_upsert_opening_cache` is at eval_drain.py:2376; its INSERT (line 2428) has 4 columns + `ON CONFLICT (full_hash) DO NOTHING` and CAST() param syntax. pv is element [3] of `engine_result_map.get(t.ply, ...)`.
- `_fetch_dedup_evals` (eval_drain.py:316) is the single cache-read fn used by the drain, both remote submit paths, and `_fetch_cached_opening_hashes` (eval_remote.py:168, lease side).
- Atomic submit `_derive_atomic_sentinel_lines` runs at eval_remote.py:1408 (read phase), BEFORE dedup_map is fetched at 1426 inside the write session — the merge must move the fetch earlier.
- `_apply_submit` has NO sentinel derivation; its dedup_map fetch (line 377) + classify (line 405) are both inside one write session — merge there is straightforward.
- Terminal donors (full_hash=0, is_terminal) are excluded everywhere cache-related — do not disturb.
- Lichess games keep `dedup_map = {}` in both submit paths — the merge stays inside the engine-game-only guard.
- Do NOT touch SEED-056 second-pass logic (`_fill_engine_game_flaw_pvs` / `_fill_engine_game_flaw_second_best`) beyond the mechanical tuple-shape update.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add nullable pv column to opening_position_eval (model + migration)</name>
  <files>app/models/opening_position_eval.py, alembic/versions/</files>
  <action>Add a nullable `pv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` column to OpeningPositionEval (import Text from sqlalchemy). Match the semantics of game_positions.pv (full UCI PV string FROM the position; Text, not String(5) — a PV is many moves). Add a docstring line explaining pv is the engine's PV FROM this position, cached so dedup transplants on the engine-free atomic path carry a walkable PV (SEED-076 follow-up). Then generate the migration: `uv run alembic revision --autogenerate -m "add pv to opening_position_eval"`. Open the generated file and VERIFY it contains only `op.add_column('opening_position_eval', sa.Column('pv', sa.Text(), nullable=True))` and the matching `op.drop_column` in downgrade — delete any spurious autogen noise (unrelated index/type diffs). Confirm down_revision is `eb341e836ee9`.</action>
  <verify>
    <automated>uv run alembic upgrade head && uv run ty check app/ 2>&1 | tail -3</automated>
  </verify>
  <done>opening_position_eval has a nullable pv Text column; migration applies cleanly on top of eb341e836ee9 and adds only that column; ty clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Widen dedup_map to a 4-tuple (add pv) and populate + self-heal the cache</name>
  <files>app/services/eval_drain.py, app/routers/eval_remote.py, tests/services/test_eval_drain.py, tests/services/test_full_eval_drain.py, tests/test_eval_worker_endpoints.py</files>
  <behavior>
    - `_fetch_dedup_evals` returns `{full_hash: (eval_cp, eval_mate, best_move, pv)}` (4-tuple), selecting the new pv column.
    - `_upsert_opening_cache` writes pv (element [3] of the engine_result_map entry) and, on conflict, backfills pv onto an existing row ONLY when the existing pv IS NULL (eval columns keep first-write-wins; a non-NULL existing pv is never overwritten).
    - Existing dedup tests updated to the 4-tuple shape; `uv run ty check app/ tests/` passes with zero errors.
  </behavior>
  <action>
1. Change `_fetch_dedup_evals` (eval_drain.py:316) return annotation to `dict[int, tuple[int | None, int | None, str | None, str | None]]`, add `OpeningPositionEval.pv` to the select, and return `{row[0]: (row[1], row[2], row[3], row[4]) ...}`. Update its docstring's returns line.
2. Widen EVERY dedup_map annotation from `tuple[int | None, int | None, str | None]` to `tuple[int | None, int | None, str | None, str | None]` at eval_drain.py lines 371, 539, 949, 975, 1045, 1090, 1195 (the `dedup_map:` params only). Do NOT touch the `second_best_map:` annotations (lines 1092, 1161, 1197, 2602) or the local `second_best_map` — that is a separate 3-tuple map. Grep `dict\[int, tuple\[int \| None, int \| None, str \| None\]\]` after editing to confirm only second_best_map annotations remain.
3. Update the two unpack sites: `_resolve_full_eval` (line 388) `eval_cp, eval_mate, best_move, _pv = dedup_map[target.full_hash]` (keep returning `None` as the pv there — the dedup path's pv is merged into engine_result_map elsewhere, not surfaced through _resolve_full_eval which feeds _apply_full_eval_results eval/best_move writes, NOT pv); and `_reconstruct_pos_eval` (line 967) `cp, mate, _bm, _pv = dedup_map[t.full_hash]`.
4. In `_upsert_opening_cache` (eval_drain.py:2376): pull pv through — `for cp, mate, bm, pv in (engine_result_map.get(t.ply, (None, None, None, None)),)`, include pv in cache_rows, add a `pv_{i}` param + `CAST(:pv_{i} AS text)` in the VALUES (5 columns now: full_hash, eval_cp, eval_mate, best_move, pv). Change the conflict clause to self-heal pv-less rows: `ON CONFLICT (full_hash) DO UPDATE SET pv = EXCLUDED.pv WHERE opening_position_eval.pv IS NULL AND EXCLUDED.pv IS NOT NULL`. Update the docstring: eval/best_move stay first-write-wins; only pv is backfilled when currently NULL. Comment the WHY at the conflict clause (SEED-076: without the backfill, every pre-existing cache row stays pv-less forever and the atomic-path gap persists).
5. Update existing tests that unpack the 3-tuple or seed the cache: tests/services/test_eval_drain.py and tests/services/test_full_eval_drain.py assertions on `_fetch_dedup_evals` results and any `OpeningPositionEval(...)` inserts / direct SQL inserts into opening_position_eval (add the pv column where a full column list is used; leave pv NULL where the test does not care). The helper at tests/test_eval_worker_endpoints.py:4797 (`INSERT ... (full_hash, eval_cp, eval_mate, best_move)`) can stay 4-column for pv-less seeding; Task 3 adds pv-bearing variants.
  </action>
  <verify>
    <automated>uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -n auto tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py -q 2>&1 | tail -5</automated>
  </verify>
  <done>_fetch_dedup_evals returns 4-tuples with pv; _upsert_opening_cache writes pv and self-heals pv-less rows without touching eval columns; all dedup_map annotations widened (second_best_map untouched); ty + ruff clean; the two drain test modules pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Merge cached pv into engine_result_map at submit + gate lease omission on pv + regression tests</name>
  <files>app/routers/eval_remote.py, tests/test_eval_worker_endpoints.py</files>
  <behavior>
    - Cache row WITH pv → opening position omitted from the lease; after atomic submit of a partial (opening-omitted) eval set producing an opening flaw there, game_positions.pv at the flaw-adjacent plies equals the cached pv, the flaw is NOT []-sentineled, and _build_flaw_blob_lease_positions returns lease positions (not sentinel_lines) for it.
    - Cache row WITHOUT pv → opening position is NOT omitted from the lease (worker still asked to evaluate it).
    - The non-atomic _apply_submit path likewise writes the cached pv at flaw-adjacent opening plies.
  </behavior>
  <action>
1. Add a small helper (module-level in eval_remote.py) `_merge_dedup_pv_into_engine_map(targets, dedup_map, engine_result_map) -> None` that, for each non-terminal target with `ply <= DEDUP_MAX_PLY` whose `full_hash in dedup_map` AND whose `ply not in engine_result_map`, inserts `engine_result_map[ply] = dedup_map[full_hash]` (the cached 4-tuple already IS `(cp, mate, best_move, pv)`). Never overrides a ply the worker evaluated fresh. Comment the WHY: SEED-076 — the cache-aware lease omitted these openings so the worker sent no eval/pv for them; merging the cached entry lets _classify_and_fill_oracle write the pv (the crux) and lets _derive_atomic_sentinel_lines walk it instead of []-sentineling the flaw.
2. `_apply_atomic_submit`: move the dedup_map fetch OUT of the write session (line ~1426) to a short read session (or the existing read phase) BEFORE `_derive_atomic_sentinel_lines` at line 1408, keeping the `is_lichess_eval_game -> {}` guard. Call `_merge_dedup_pv_into_engine_map(...)` immediately after fetching and BEFORE line 1408. The cache is insert-only so reading it in a separate earlier session is staleness-safe. Reuse the already-fetched dedup_map inside the write session for `_apply_full_eval_results` (do not re-fetch). Comment that the merge must precede sentinel derivation.
3. `_apply_submit`: after the existing dedup_map fetch (line 377, inside the write session), call `_merge_dedup_pv_into_engine_map(...)` before `_classify_and_fill_oracle` (line 405). No sentinel derivation here, so in-session is fine.
4. `_fetch_cached_opening_hashes` (eval_remote.py:168): only treat a position as server-fillable (omittable from the lease) when its cache row has `pv IS NOT NULL`. Change it to build the set from `_fetch_dedup_evals` entries where the tuple's pv (element [3]) is not None: `frozenset(fh for fh, (_cp, _mate, _bm, pv) in cached.items() if pv is not None)`. Comment the WHY: a pv-less cache row can fill the eval at submit but NOT the pv, so the worker must still evaluate that opening fresh; as the DO UPDATE backfill fills pv over time, omission coverage ramps back up. Leave the submit-side dedup fill (evals) unconditional — it fixes eval holes regardless of pv.
5. Regression tests in tests/test_eval_worker_endpoints.py (extend the existing SEED-076 opening-cache test block near line 4755). Add a pv-bearing cache-seed helper variant (5-column insert). Cases: (a) cache row WITH pv → position omitted from the atomic lease; after atomic-submit of a partial eval set that produces an opening flaw at that ply, game_positions.pv at the flaw-adjacent plies == the cached pv, the flaw's allowed/missed pv_lines are NOT [] (not sentineled), and `_build_flaw_blob_lease_positions` returns lease positions for it; (b) cache row WITHOUT pv → the position is NOT omitted from the lease (appears in the leased positions); (c) `_upsert_opening_cache` backfills pv onto an existing pv-less row without changing its eval_cp/eval_mate/best_move and does NOT overwrite an existing non-NULL pv. Choose fixtures/hashes so the flaw lands at ply <= DEDUP_MAX_PLY. Do NOT gate completion on bin/reset_db.sh — operate against the existing per-run test DB.
  </action>
  <verify>
    <automated>uv run ruff format app/ tests/ && uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -n auto tests/test_eval_worker_endpoints.py tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py -q 2>&1 | tail -6</automated>
  </verify>
  <done>Both submit paths merge cached pv into engine_result_map before classify/sentinel derivation; lease omission is gated on pv presence; new regression tests prove the cached pv reaches game_positions.pv, the opening flaw is not []-sentineled, and pv-less rows are still leased; ruff + ty clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| worker→/atomic-submit | Untrusted worker-supplied evals/PVs cross here; server re-classifies authoritatively (T-147-03) and never trusts worker flaw-ply hints. |
| cache→submit | opening_position_eval is server-owned, insert-only; cached pv is server-computed, not worker-supplied. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qgp-01 | Tampering | cached pv merged into engine_result_map | low | accept | pv originates from the server's own engine pass (drain-written cache), not the worker payload; the merge only fills plies the worker did NOT evaluate, so it cannot override worker-fresh data. |
| T-qgp-02 | Info-disclosure | new pv column | low | accept | pv is a chess PV string, non-sensitive; API responses never expose the cache (return FEN for display per CLAUDE.md). |
| T-qgp-03 | Denial-of-service | DO UPDATE self-heal on conflict | low | accept | one-time pv backfill per row (WHERE pv IS NULL); insert volume is self-limiting as the cache fills. No package installs in this change (T-qgp-SC N/A). |
</threat_model>

<verification>
- `uv run ruff format app/ tests/ && uv run ruff check app/ tests/` clean.
- `uv run ty check app/ tests/` zero errors.
- `uv run pytest -n auto` full backend suite green (run before squash-merge per CLAUDE.md pre-merge gate).
- `uv run alembic upgrade head` applies the new migration cleanly.
- Manual sanity (optional): confirm `grep` finds no remaining `dedup_map: dict[int, tuple[int | None, int | None, str | None]]` (3-tuple) annotation in app/.
</verification>

<success_criteria>
- opening_position_eval has a nullable pv column with a matching Alembic migration on top of eb341e836ee9.
- dedup_map is a 4-tuple `(eval_cp, eval_mate, best_move, pv)` end to end; second_best_map is untouched.
- _upsert_opening_cache writes pv and self-heals pv-less rows (eval columns unchanged).
- Both submit paths merge cached pv into engine_result_map before classify (and before sentinel derivation on the atomic path); a cached opening flaw keeps a real PV walk instead of a permanent [] sentinel.
- Lease omission is gated on pv presence; pv-less cache rows are still leased.
- Regression tests cover: pv-bearing omission + pv-reaches-game_positions + not-sentineled + blob-lease returns positions; pv-less not-omitted; cache pv backfill self-heal without eval overwrite.
- Full backend suite + ruff + ty green.
</success_criteria>

<output>
Create `.planning/quick/260703-qgp-fix-seed-076-follow-up-cache-pv-in-openi/260703-qgp-SUMMARY.md` when done
</output>
