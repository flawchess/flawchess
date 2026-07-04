# Phase 150: Consolidate Write Path - Pattern Map

**Mapped:** 2026-07-04
**Files analyzed:** 8 (2 new, 4 modified, 2 new tests/scripts)
**Analogs found:** 8 / 8 (all internal — this is a self-referential refactor: analogs are the very functions being consolidated, plus two cross-domain precedents for the new bits)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/eval_apply.py` (NEW) | service (write-path orchestration) | request-response + CRUD | `app/routers/eval_remote.py::_apply_atomic_submit` (L1060) — the body being moved | exact (source relocation) |
| `app/services/eval_drain.py` (MODIFY: R1/R3/R4/R7) | service (batch/event-driven drain loop) | CRUD + batch | itself, pre-refactor (`_classify_and_fill_oracle` L705, `_full_drain_tick` L2513) | exact (self) |
| `app/routers/eval_remote.py` (MODIFY: R1/R3/R7) | route (HTTP layer) | request-response | itself, pre-refactor; target shape = thin-router convention already used elsewhere in the file (`atomic_submit_eval` L1363 calling out to a service function) | exact (self) |
| `app/services/engine.py` (MODIFY: R5) | service (process/engine wrapper) | request-response | itself — 3 near-identical private methods (`_analyse` L464, `_analyse_with_pv` L515, `_analyse_multipv2` L573) | exact (self) |
| `app/services/eval_queue_service.py` (MODIFY: R6) | service (query/lottery layer) | CRUD (weighted select) | itself — `_claim_tier3_derived` (L277) vs `_claim_tier4_blob` (L489) | exact (self) |
| `tests/services/test_flaw_upsert_equivalence.py` (NEW) | test (golden-snapshot equivalence) | batch/transform | `tests/scripts/test_gen_global_percentile_cdf_unchanged.py` | exact (pattern precedent, different domain) |
| `scripts/gen_write_path_golden.py` (NEW, committed generator) | utility (fixture generator) | batch/transform | `scripts/gen_global_percentile_cdf.py` | exact (pattern precedent, different domain) |
| `FLAW_BLOB_COLUMNS` constant (new, in `game_flaws_repository.py`) | config (single-source column list) | — | `TACTIC_TAG_COLUMNS` (L154-163, same file) | exact (2-line extension of existing pattern) |

## Pattern Assignments

### `app/services/eval_apply.py` (NEW — service, request-response + CRUD)

**Analog:** `app/routers/eval_remote.py::_apply_atomic_submit` (L1060-1334) — this is a **move, not a rewrite**. The function body becomes `apply_full_eval(...)` here.

**Orchestration shape to preserve** (the "read session → CPU work (no session) → write session" sequencing, Phase 147 D-01/D-02 template):
```
1. read_session:  load evals/targets, dedup lookups
2. (no session):  engine calls / classify (CPU-bound, no DB held open)
3. write_session: bulk_insert/update flaws, oracle counts, PV writes,
                  apply_completion_decision(...), upsert_worker_heartbeat(...),
                  commit — ALL inside ONE write_session (T-117-11 atomicity)
```

**Do not wrap the write_session body in try/except** — errors from `bulk_insert_game_flaws` / oracle-count UPDATE must propagate so the transaction aborts and completion markers are never committed (WR-01 fail-closed contract, current docstring at `_classify_and_fill_oracle`). Only the flaw-PV write (`_batch_update_flaw_pv_lines` / `_batch_update_pv_rows`) stays individually fault-tolerant, per current code at `eval_drain.py:886-898`.

**Move (not re-export) these symbols from `eval_drain.py` into this file** to avoid a circular import (`eval_drain.py` must never import from `eval_apply.py` while `eval_apply.py` imports back from it):
`_FullPlyEvalTarget`, `_collect_full_ply_targets`, `_fetch_dedup_evals`, `_resolve_full_eval`, `_post_move_eval`, `_batch_update_best_move_rows`, `_batch_update_pv_rows`, `_batch_update_eval_rows`, `_apply_full_eval_results`, `_mark_full_evals_completed`, `_mark_full_pv_completed`, `_classify_and_fill_oracle` (R3 target — becomes the diff/upsert), the R4-unified preamble helper, `_flaw_engine_plies`, `_build_flaw_multipv2_blobs`, `_derive_atomic_sentinel_lines`, `_batch_update_flaw_pv_lines`, `_run_multipv2_pass`, `_GameColorView`, `_signal_flaw_completion`, `apply_completion_decision` (new, R1), `_parse_token`, `_assemble_flaw_blobs_from_submit`, `_assemble_one_line_blob`.

After the move: `eval_drain.py`'s `_full_drain_tick` imports FROM `eval_apply.py`; `eval_remote.py`'s `atomic_submit_eval` imports FROM `eval_apply.py`. Neither direction reverses.

**`_upsert_opening_cache` scope flag:** `_full_drain_tick` calls it today; `_apply_atomic_submit` does not. `apply_full_eval` must take an explicit `update_opening_cache: bool` parameter (or equivalent) defaulting each caller to its *current* behavior — do not silently unify to "always call it," that is a behavior change forbidden by this phase's no-behavior-change contract (RESEARCH.md Pitfall 4).

---

### `app/services/eval_drain.py` (MODIFY — service, CRUD + batch, R1/R3/R4/R7)

**R1 — `apply_completion_decision` (replaces the inline Path A/B/C block at `_full_drain_tick` L2767-2821):**

Shared shape to extract verbatim (both current copies are line-for-line identical except Sentry `source` tag and warn mechanism):
```python
new_attempts = current_attempts + 1
if failed_ply_count == 0:
    # Path A: no holes — stamp both markers complete.
    mark_full_evals_completed(); mark_full_pv_completed(); stamp_complete = True
elif new_attempts < MAX_EVAL_ATTEMPTS:
    # Path B: holes remain, under cap — increment attempts, leave pending.
    UPDATE games SET full_eval_attempts = new_attempts; stamp_complete = False
else:
    # Path C: holes remain AND cap reached — stamp anyway (D-116-07 no-loop invariant).
    mark_full_evals_completed(); mark_full_pv_completed()
    <emit ONE aggregated warning via warn_fn(...)>; stamp_complete = True

if stamp_complete and job_id is not None:
    UPDATE eval_jobs SET status='completed', completed_at=now()
        WHERE id = :job_id AND status = 'leased'   # guard: late/expired-lease submit is a no-op
```
Signature: `apply_completion_decision(write_session, *, game_id, job_id, failed_ply_count, current_attempts, source: Literal["full_eval_drain", "remote_eval_worker"], on_path_c_capacity_reached) -> bool`. **Do NOT unify the Path-C warning mechanism** — `eval_drain.py` deliberately uses `logger.warning` (FLAWCHESS-5V fix, avoids Sentry quota burn on an expected outcome) while `eval_remote.py` uses `sentry_sdk.capture_message`; thread `on_path_c_capacity_reached` (a callback) or a `warn_fn` param so both call sites keep their existing choice. Keep `upsert_worker_heartbeat(...)` as a sibling call in the caller, not folded into this function (it's PRUNE-06 telemetry, not part of the decision).

**R3 — `_classify_and_fill_oracle` (L705-898) diff/upsert, replacing delete-then-insert:**

Current flow to replace:
```python
# app/services/eval_drain.py:705-898 (current — DELETE-then-INSERT)
delete_flaws_for_game(session, game_id, user_id)          # unconditional full delete
bulk_insert_game_flaws(session, rows)                      # never sets blob/tactic cols → NULL
```

**New 4-way partition** (avoids the JSONB `None`-vs-`null::jsonb` landmine — `project_asyncpg_jsonb_null_vs_sql_null` — do NOT use `ON CONFLICT DO UPDATE ... COALESCE(...)`, a bound Python `None` serializes as real JSON `null`, not SQL NULL, so `COALESCE(EXCLUDED.col, existing.col)` always picks the non-NULL json-null and silently wipes preserved blobs):

1. **Delete** — `existing_ply - desired_ply` (plies no longer flaws). Clean `DELETE ... WHERE ply IN (...)`, never a bulk-update-by-PK (that's the FLAWCHESS-8D StaleDataError trigger).
2. **Insert new** — `desired_ply - existing_ply`, via existing `flaw_record_to_row` + `bulk_insert_game_flaws` (unchanged); omit `FLAW_BLOB_COLUMNS` keys entirely when not freshly-blobbed (→ true NULL via column default).
3. **Update existing, freshly-blobbed** — ORM bulk-update-by-PK, same idiom as today's `_restore_preserved_flaw_blobs`:
```python
# Source: app/routers/eval_remote.py:1050-1057 (current HEAD) — model for update-fresh branch
rows = [
    {"user_id": user_id, "game_id": game_id, "ply": ply, **cols}
    for ply, cols in snapshot.items()
    if ply not in freshly_blobbed and ply in existing_plies
]
if not rows:
    return
await session.execute(update(GameFlaw), rows)
```
4. **Update existing, not freshly-blobbed** — same idiom, but the update dict **excludes `FLAW_BLOB_COLUMNS` entirely** (`{k: v for k, v in row.items() if k not in FLAW_BLOB_COLUMNS}`) so those columns never appear in the SQL `SET` clause — preservation-by-omission, not by NULL-comparison.

Reuse `_batch_update_flaw_pv_lines`'s raw-SQL JSONB pattern for any fresh-blob raw-SQL path (it's safe because `json.dumps()` always produces a real value, never Python `None`):
```python
# Source: app/services/eval_drain.py:1413-1444 (current HEAD)
params[f"allowed_{i}"] = json.dumps(allowed_blobs)
params[f"missed_{i}"] = json.dumps(missed_blobs)
values_parts.append(f"(CAST(:ply_{i} AS smallint), CAST(:allowed_{i} AS jsonb), CAST(:missed_{i} AS jsonb))")
```

**R4 — classify preamble unification (L901, 979, 1216, 1340):** 3 of the 4 sites (`_missing_flaw_pv_targets` L979, `_build_flaw_multipv2_blobs` L1216, `_derive_atomic_sentinel_lines` L1340) share this identical shape:
```python
pos_eval = _reconstruct_pos_eval(targets, dedup_map, engine_result_map)   # pure, in-memory
async with async_session_maker() as session:
    game = await session.scalar(select(Game).where(Game.id == game_id))
    positions = <load GamePosition ordered by ply>
for pos in positions:
    cp, mate = _post_move_eval(pos_eval, pos.ply)   # overwrites pos.eval_cp/eval_mate
    pos.eval_cp, pos.eval_mate = cp, mate
flaw_result = classify_game_flaws(game, positions)
```
`_flaw_engine_plies` (L901) is **structurally different, not a copy-paste target to force-merge** — it runs pre-gather on lichess-eval games where DB-stored `eval_cp`/`eval_mate` are the real %eval and must NOT be overlaid. Design the unified helper as `_classify_with_overlay(game_id, positions_loader, *, overlay: bool, pos_eval=None)`, with `overlay=False` for the `_flaw_engine_plies` call site. Forcing the overlay unconditionally reproduces the exact Phase 117 "0% flaw-PV coverage for lichess games" regression — add a regression test for this specifically, not just "existing tests pass."

**R7 — 3-way split** (entry lane / full lane / shared write path) — see the "R7 Module Split" section of RESEARCH.md for the full symbol inventory; `_full_drain_tick` slims to call `eval_apply.apply_full_eval(...)`.

---

### `app/routers/eval_remote.py` (MODIFY — route, request-response, R1/R3/R7)

**Analog for "thin router" target shape:** the file's own `atomic_submit_eval` (L1363) already demonstrates the convention — thin HTTP wrapper delegating to a service call; extend this same shape so it calls `eval_apply.apply_full_eval(...)` instead of the local private `_apply_atomic_submit`.

**Delete outright (R3):** `_snapshot_preserved_flaw_blobs` (L961) and `_restore_preserved_flaw_blobs` (L1014) — their behavior is now native to the diff/upsert in `eval_apply.py`, not a caller-side compensation layer.

**Remove (R7):** the private-helper import block (L81-107, 21 symbols + 3 constants imported from `eval_drain.py`) — after the move, `eval_remote.py` imports only from `eval_apply.py` (public, non-underscore-prefixed or intentionally-shared names) and stops reaching into `eval_drain.py` internals. This matches the Router Convention in CLAUDE.md ("routers — HTTP layer only, no business logic").

**R1 copy #2** to replace: `_apply_atomic_submit`'s inline Path A/B/C block (L1281-1334) — same shared shape as `eval_drain.py`'s, differing only in Sentry source tag (`"remote_eval_worker"`) and the sentry-capture-message warn path (see R1 pattern above). Note the `upsert_worker_heartbeat(...)` call right before commit here (PRUNE-06) — keep as sibling call in the orchestration function, not folded into `apply_completion_decision`.

---

### `app/services/engine.py` (MODIFY — service/engine wrapper, request-response, R5)

**Analog:** itself — 3 near-identical private methods on `EnginePool` (class starts L370): `_analyse` (L464), `_analyse_with_pv` (L515), `_analyse_multipv2` (L573). All 3 share this 14-line acquire/timeout/restart/release skeleton:
```python
if not self._started: return None  # or (None, None) for _analyse
idx = await self._available.get()
try:
    protocol = self._protocols[idx]
    if protocol is None: return None
    try:
        result = await asyncio.wait_for(protocol.analyse(board, limit[, multipv=2]), timeout=timeout)
    except (asyncio.TimeoutError, chess.engine.EngineError, chess.engine.EngineTerminatedError):
        await self._restart_worker(idx)
        return None
    return result
finally:
    self._available.put_nowait(idx)
```
**Target signature:** one `_acquire_and_analyse(board, limit, timeout, *, multipv: int | None = None) -> chess.engine.InfoDict | list[chess.engine.InfoDict] | None`, parameterized purely on `multipv`. Public methods `evaluate()` (L244), `evaluate_nodes()` (L260), `evaluate_nodes_with_pv()` (L273), `evaluate_nodes_multipv2()` (L294) call it and apply their own post-processing (`_score_to_cp_mate()` at L337 for scalar callers, PV/list extraction for the multipv=2 caller) — no change needed to those post-processing call sites, only to the shared skeleton they call into.

---

### `app/services/eval_queue_service.py` (MODIFY — service/query layer, CRUD weighted-select, R6)

**Analog:** itself — `_claim_tier3_derived` (L277, 3 SQL stages incl. residual fallback) vs `_claim_tier4_blob` (L489, 2 SQL stages, no fallback). Both share the identical TC-multiplier CASE block (`GAME_TC_WEIGHTS`: classical=8/rapid=4/blitz=2/bullet=1/other=0.5) and the same `-ln(random()) / weight` Efraimidis-Spirakis key, differing only in WHERE/EXISTS predicate, which recency column anchors the decay, and which named half-life/floor constants apply.

**Target: two generic building blocks, not one flat function:**
```python
async def _es_weighted_user_pick(session, *, candidate_exists_sql, recency_col_sql, tau_seconds, floor) -> int | None: ...
async def _es_weighted_game_pick(session, *, game_where_sql, recency_col_sql, tau_seconds, game_floor, tc_weights) -> int | None: ...
```
`_claim_tier3_derived` becomes: user-pick → game-pick → (game-pick again, different WHERE, for the residual fallback). `_claim_tier4_blob` becomes: user-pick → game-pick. **Preserve the existing discipline of `sa.text` bound params, never f-string interpolation** — both current functions already enforce this via inline comments; carry it into the shared helpers. This ride-along (D-06) may be deferred to a follow-up if R3 balloons, but must be flagged in the plan/verification if descoped, not silently dropped.

---

### `tests/services/test_flaw_upsert_equivalence.py` (NEW — test, batch/transform)

**Analog:** `tests/scripts/test_gen_global_percentile_cdf_unchanged.py` (existing, CI-enforced "commit the generator + drift-check test" pattern):
```python
# Source: tests/scripts/test_gen_global_percentile_cdf_unchanged.py (current HEAD)
@pytest.mark.parametrize(("metric_id", "tc"), [...])
def test_build_per_user_with_anchor_query_byte_identical_after_refactor(metric_id, tc) -> None:
    expected = _load_golden(metric_id, tc)
    actual = _build_per_user_with_anchor_query(metric_id, tc, snapshot_date=_SNAPSHOT_DATE)
    assert actual == expected, "...regenerate via the snippet in the module docstring..."

def test_fixture_directory_covers_all_in_scope_cells() -> None:
    fixture_names = {p.stem for p in _FIXTURE_DIR.glob("*.sql")}
    in_scope = {f"{m}__{tc}" for m in IN_SCOPE_METRICS for tc in ALL_TIME_CONTROLS}
    assert not (in_scope - fixture_names), "Missing golden fixtures"
```
Adapt for DB-round-trip `game_flaws` row state instead of pure-function SQL strings. Parametrize over 8 scenario fixtures (7 from D-02 + 1 inverse-of-#3 for "flips IN"). **Assert `IS NULL` explicitly for blob columns expected NULL** — a truthy-equality assertion (`assert row.allowed_pv_lines == preserved_value`) would NOT catch the JSONB-null pitfall if it regresses.

**Existing tests to harvest scenario setups from (do not invent new fixtures):**
| Scenario | Existing test | Reusable helpers |
|---|---|---|
| 1. Fresh full submit | `tests/test_eval_worker_endpoints.py::test_atomic_submit_fills_cached_opening_hole_server_side` (~3681) | `_insert_game`, `_insert_game_positions`, `_atomic_request` |
| 2. Residual-hole retry | `test_atomic_retry_preserves_existing_flaw_blobs_and_tags` (3807) | same + manual `UPDATE GameFlaw` |
| 3. Flip OUT of flaw | `test_atomic_retry_snapshotted_ply_no_longer_flaw_does_not_raise` (3895, FLAWCHESS-8D) | `_FLAT_SUBMIT_EVALS_142` vs `_BLUNDER_SUBMIT_EVALS_142` |
| 4. Flip IN to flaw | new — inverse ordering of #3 | same fixtures, swapped order |
| 5. Entry-pass replaced by oracle pass | `tests/services/test_full_eval_drain.py::TestClassifyHook` (~1743) | pre-seeded stale entry-pass `GameFlaw` rows |
| 6. Dedup transplant, no `[]` sentinel taint | `test_atomic_submit_merges_cached_pv_into_flaw_line_not_sentineled` (4012, quick 260703-qgp) | `_insert_opening_cache_with_pv`, `_build_flaw_blob_lease_positions` |
| 7. `blobs_pending=True` suppression | `tests/services/test_full_eval_drain.py::TestLocalDrainBlobsPendingSuppression` (~1851) | `_patch_drain_for_tick_tests` |

---

### `scripts/gen_write_path_golden.py` (NEW committed generator)

**Analog:** `scripts/gen_global_percentile_cdf.py` (structure/docstring convention — regeneration one-liner in the module docstring, not a separate doc file). Generate goldens **before** touching `_classify_and_fill_oracle` (Wave 0 / first task, against pre-refactor code) — the whole point of D-01 is capturing *current, correct* behavior; generating after the diff/upsert lands makes the equivalence proof circular.

---

### `FLAW_BLOB_COLUMNS` constant (new, `app/repositories/game_flaws_repository.py`)

**Analog:** `TACTIC_TAG_COLUMNS` (same file, L154-163) — a 2-line extension:
```python
# Source: app/repositories/game_flaws_repository.py:154-163 (current HEAD)
TACTIC_TAG_COLUMNS: tuple[str, ...] = (
    "allowed_tactic_motif", "allowed_tactic_piece", "allowed_tactic_confidence", "allowed_tactic_depth",
    "missed_tactic_motif", "missed_tactic_piece", "missed_tactic_confidence", "missed_tactic_depth",
)
```
New: `FLAW_BLOB_COLUMNS: tuple[str, ...] = ("allowed_pv_lines", "missed_pv_lines") + TACTIC_TAG_COLUMNS`, defined once here, imported by both `bulk_update_tactic_tags` and the new diff/upsert's partition-3/partition-4 logic in `eval_apply.py`. This satisfies D-04's "future 11th column cannot be silently nulled" goal by construction.

## Shared Patterns

### Single-transaction write session (T-117-11)
**Source:** `app/services/eval_drain.py::_classify_and_fill_oracle` docstring + `app/routers/eval_remote.py::_apply_atomic_submit` (L1060+)
**Apply to:** `eval_apply.py::apply_full_eval` — all writes (flaw diff/upsert, oracle counts, completion decision, heartbeat) commit atomically in one `write_session`. Errors from the flaw write / oracle UPDATE propagate uncaught (fail-closed, WR-01); only the PV write stays best-effort.

### Preservation-by-omission, never by-NULL-comparison
**Source:** `project_asyncpg_jsonb_null_vs_sql_null` (memory), applied in new R3 diff/upsert
**Apply to:** any UPDATE that must leave a JSONB column untouched — omit the key from the row dict passed to `update(Model), rows`; never rely on `COALESCE(EXCLUDED.col, existing.col)` with a Python `None` binding for a JSONB column.

### Single-source-of-truth column tuples
**Source:** `TACTIC_TAG_COLUMNS` (`app/repositories/game_flaws_repository.py:154-163`)
**Apply to:** `FLAW_BLOB_COLUMNS` (new) — both the diff/upsert's partition logic and `retag_flaws.py` import from one place.

### Committed-generator + drift-check test
**Source:** `scripts/gen_global_percentile_cdf.py` + `tests/scripts/test_gen_global_percentile_cdf_unchanged.py`
**Apply to:** `scripts/gen_write_path_golden.py` + `tests/services/test_flaw_upsert_equivalence.py` — regeneration instructions live in the script docstring; a completeness guard test asserts one fixture file per named scenario.

### Thin router → service delegation
**Source:** `app/routers/eval_remote.py::atomic_submit_eval` (L1363) — existing convention in the same file
**Apply to:** the post-R7 `eval_remote.py` — all routes delegate to `eval_apply.py`, no private-helper imports from `eval_drain.py`.

## No Analog Found

None — every touched file has a strong analog, either itself pre-refactor (self-consolidation) or a cross-domain precedent already in the codebase (golden-snapshot generator pattern, single-source column tuple).

## Metadata

**Analog search scope:** `app/services/`, `app/routers/`, `app/repositories/`, `scripts/`, `tests/services/`, `tests/scripts/`, `tests/test_eval_worker_endpoints.py`
**Files scanned:** `app/services/eval_drain.py`, `app/routers/eval_remote.py`, `app/services/engine.py`, `app/services/eval_queue_service.py`, `app/repositories/game_flaws_repository.py`, `scripts/gen_global_percentile_cdf.py`, `tests/scripts/test_gen_global_percentile_cdf_unchanged.py`
**Pattern extraction date:** 2026-07-04
