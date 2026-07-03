---
phase: quick-260703-qgp
plan: 01
subsystem: database, api
tags: [postgresql, alembic, sqlalchemy, eval-drain, opening-cache, pv]

requires:
  - phase: quick-260703-nux
    provides: cache-aware incremental eval lease + blob-preserving classify (SEED-076)
provides:
  - opening_position_eval.pv nullable Text column + Alembic migration
  - 4-tuple dedup_map (eval_cp, eval_mate, best_move, pv) end to end in eval_drain.py
  - _upsert_opening_cache self-heal (backfills pv onto pv-less rows, first-write-wins otherwise)
  - _merge_dedup_pv_into_engine_map + wiring into both submit paths
  - pv-gated lease omission in _fetch_cached_opening_hashes
affects: [eval-remote-router, eval-drain-service, remote-worker-protocol]

tech-stack:
  added: []
  patterns:
    - "Cache self-heal via ON CONFLICT DO UPDATE ... WHERE col IS NULL AND EXCLUDED.col IS NOT NULL (per-column backfill without touching sibling first-write-wins columns)"
    - "Pre-write-session cache fetch + in-memory merge before a downstream classify/sentinel-derivation call that must see the merged data"

key-files:
  created:
    - alembic/versions/20260703_171134_df8d4f5bc37b_add_pv_to_opening_position_eval.py
  modified:
    - app/models/opening_position_eval.py
    - app/services/eval_drain.py
    - app/routers/eval_remote.py
    - tests/services/test_eval_drain.py
    - tests/services/test_full_eval_drain.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "pv self-heals via DO UPDATE SET pv = EXCLUDED.pv WHERE pv IS NULL; eval_cp/eval_mate/best_move stay first-write-wins (ON CONFLICT DO NOTHING semantics preserved for those columns)"
  - "_apply_atomic_submit's dedup_map fetch moved to its own short read session BEFORE _derive_atomic_sentinel_lines (was inside the write session, after sentinel derivation) so the merged pv is visible to the sentinel walk; write session reuses the fetched dedup_map instead of re-fetching"
  - "Lease omission gated on pv IS NOT NULL, not merely full_hash presence — a pv-less cache row can fill the eval at submit but not the pv, so it must still be leased fresh"
  - "OPENING_CACHE_BACKFILL_SQL (the one-time cold-start backfill script) intentionally left untouched — out of this plan's scope, which targets the incremental _upsert_opening_cache write path"

requirements-completed: [SEED-076-FOLLOWUP]

duration: 25min
completed: 2026-07-03
status: complete
---

# Quick Task 260703-qgp: Cache the pv alongside the eval in opening_position_eval

**Fixed the SEED-076 regression where cache-aware lease omission fed opening flaws a permanent `[]` PV sentinel: `opening_position_eval` now caches the PV alongside the eval, and both submit paths merge the cached PV into `engine_result_map` before classify/sentinel derivation.**

## Performance

- **Duration:** 25min
- **Completed:** 2026-07-03T17:28:00.000Z
- **Tasks:** 3/3 completed
- **Files modified:** 7 (1 new migration, 6 modified)

## Accomplishments

- Added a nullable `pv` Text column to `opening_position_eval` (Alembic migration `df8d4f5bc37b`, on top of `eb341e836ee9`), matching `game_positions.pv` semantics.
- Widened `dedup_map` to a 4-tuple `(eval_cp, eval_mate, best_move, pv)` across every call site in `eval_drain.py` (`second_best_map`, a separate 3-tuple map, deliberately left untouched).
- `_upsert_opening_cache` now writes `pv` on insert and self-heals pv-less existing rows via `ON CONFLICT (full_hash) DO UPDATE SET pv = EXCLUDED.pv WHERE opening_position_eval.pv IS NULL AND EXCLUDED.pv IS NOT NULL` — `eval_cp`/`eval_mate`/`best_move` remain first-write-wins.
- New `_merge_dedup_pv_into_engine_map` helper (`eval_remote.py`) fills a cache-omitted opening ply's `engine_result_map` entry from the cached tuple, never overriding a ply the worker resolved itself. Wired into both `_apply_submit` (before `_classify_and_fill_oracle`) and `_apply_atomic_submit` (before `_derive_atomic_sentinel_lines`, which required moving the dedup_map fetch out of the write session into its own short read session ahead of the sentinel derivation).
- `_fetch_cached_opening_hashes` now gates lease omission on `pv IS NOT NULL`, so a pv-less cache row (e.g. one written before this column existed) is still leased fresh to the worker instead of silently starving that opening ply of a PV forever.
- Net effect: an opening flaw whose node-0 position is cached now retains a real, walkable PV instead of a permanent `[]` sentinel, and as the self-heal backfill runs, previously pv-less cache rows recover their PV over time — closing the ~1-in-10 affected-flaws gap identified in the SEED-076 follow-up seed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add nullable pv column to opening_position_eval (model + migration)** - `38e7ecbb` (feat)
2. **Task 2: Widen dedup_map to a 4-tuple (add pv) and populate + self-heal the cache** - `2db52995` (feat, tdd)
3. **Task 3: Merge cached pv into engine_result_map at submit + gate lease omission on pv + regression tests** - `3a7d936f` (feat, tdd)

_Note: this quick task's plan pre-dispatch commit (`b7ffb0b9`) predates this SUMMARY; the plan itself was already committed at HEAD per the task instructions._

## Files Created/Modified

- `app/models/opening_position_eval.py` - added nullable `pv: Mapped[Optional[str]]` (Text) column with a docstring explaining its SEED-076-follow-up purpose
- `alembic/versions/20260703_171134_df8d4f5bc37b_add_pv_to_opening_position_eval.py` - migration adding only the `pv` column (trimmed spurious autogen drift — an unrelated `game_flaws` index removal)
- `app/services/eval_drain.py` - `_fetch_dedup_evals` returns 4-tuples incl. `pv`; all `dedup_map` annotations widened; `_resolve_full_eval`/`_reconstruct_pos_eval` unpack sites updated; `_upsert_opening_cache` writes + self-heals `pv`
- `app/routers/eval_remote.py` - new `_merge_dedup_pv_into_engine_map` helper; wired into `_apply_submit` and `_apply_atomic_submit`; `_fetch_cached_opening_hashes` gated on `pv IS NOT NULL`; added `collections.abc.Sequence` import
- `tests/services/test_eval_drain.py` - updated `_fetch_dedup_evals` assertions to the 4-tuple shape
- `tests/services/test_full_eval_drain.py` - updated 3-tuple assertions/mocks to 4-tuple shape (parity-source test, refutation-pv-recovery mock)
- `tests/test_eval_worker_endpoints.py` - new `_insert_opening_cache_with_pv` helper; `_get_game_position` now returns `pv`; 3 new regression tests (see below)

## Decisions Made

- pv self-heals via a per-column `DO UPDATE ... WHERE col IS NULL` conflict clause rather than a blanket upsert, preserving first-write-wins for `eval_cp`/`eval_mate`/`best_move` while still letting `pv` recover over time on pre-existing rows.
- `_apply_atomic_submit`'s dedup_map fetch was moved to a short, dedicated read session immediately after building `engine_result_map` and before the token-tamper guard / `_derive_atomic_sentinel_lines` call — the cache is insert-only so this earlier read is staleness-safe, and the write session now reuses the already-fetched `dedup_map` rather than fetching it again.
- `OPENING_CACHE_BACKFILL_SQL` (the one-time cold-start script populating the cache from a `game_positions` self-join) was intentionally left unmodified — it is out of this plan's `files_modified` scope, which targets the incremental `_upsert_opening_cache` write path used by the live drain and both submit endpoints. A cold-started row from that script stays pv-less until `_upsert_opening_cache`'s self-heal backfills it on a later write.

## Deviations from Plan

None — plan executed exactly as written across all three tasks and their `must_haves`.

## New Regression Tests (`tests/test_eval_worker_endpoints.py`)

- `test_fetch_cached_opening_hashes_gates_on_pv_presence` - a pv-bearing cache row is omittable from the lease; a pv-less cache row is not.
- `test_atomic_submit_merges_cached_pv_into_flaw_line_not_sentineled` - a cache-omitted opening flaw ply's pv reaches `game_positions.pv`, the flaw's PV lines are not `[]`-sentineled, and `_build_flaw_blob_lease_positions` returns a real, non-empty lease (not a D-06 sentinel) for both the missed and allowed lines.
- `test_upsert_opening_cache_backfills_pv_without_overwriting_eval_or_existing_pv` - the cache self-heal backfills `pv` onto a pv-less row without touching its `eval_cp`/`eval_mate`/`best_move`, and never overwrites an already-set `pv`.

## Verification Results

- `uv run ruff format app/ tests/` - 269 files unchanged (clean)
- `uv run ruff check app/ tests/` - all checks passed
- `uv run ty check app/ tests/` - all checks passed, zero errors
- `uv run alembic upgrade head` - migration `df8d4f5bc37b` applies cleanly on top of `eb341e836ee9`
- `uv run pytest -n auto` (full backend suite) - **3154 passed, 18 skipped** (0 failures)
- Targeted new-test run: 3/3 new regression tests pass

## Self-Check: PASSED

- `app/models/opening_position_eval.py` - FOUND, contains `pv` column
- `alembic/versions/20260703_171134_df8d4f5bc37b_add_pv_to_opening_position_eval.py` - FOUND
- Commit `38e7ecbb` - FOUND in git log
- Commit `2db52995` - FOUND in git log
- Commit `3a7d936f` - FOUND in git log
- Migration head `df8d4f5bc37b` - confirmed applied via `alembic current`
