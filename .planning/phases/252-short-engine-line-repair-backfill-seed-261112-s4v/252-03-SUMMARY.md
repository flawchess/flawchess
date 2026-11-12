---
phase: 252-short-engine-line-repair-backfill-seed-261112-s4v
plan: 03
subsystem: server-pool-drain-and-mixed-fleet-safety
tags: [eval-drain, tier-4, blob-only, atomic-lease, worker-schema-version, mixed-fleet]

requires:
  - phase: 252-02
    provides: eval_apply.apply_flaw_blob_results, FlawBlobApplyOutcome, stamp_flaw_blob_sentinels, per-line NULL semantics
provides:
  - blob-only server-pool tier-4 tick (_tier4_blob_drain_tick) sharing the /flaw-blob-submit core (D-12)
  - TIER_BLOB_BACKFILL dispatch in _full_drain_tick before any every-ply work
  - tier-4/4b guard on /atomic-lease (D-15)
  - mixed-fleet harmlessness tests for version-2 workers (D-15)
affects: [252-04, 252-07, 252-08]

actuals:
  tokens: 21500
  tasks: 3
  commits: 3
plan_head_before: c283dd38b55dba4723166aa94a33cdc7cb9194f1
plan_head_after: a2153f6907e2e86183a131812109b69c50b11121

tech-stack:
  added: []
  patterns:
    - "in-process drain tick reuses the HTTP lane's apply core; the Maia re-score stays with the caller (import cycle)"
    - "scope-omitted atomic lease 204s the table-less tier-4/4b lottery picks"

key-files:
  created: []
  modified:
    - app/services/eval_drain.py
    - tests/services/test_full_eval_drain.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "Failed searches are dropped (not submitted as holes) in the drain tick, matching the plan; a tick with zero surviving evals writes nothing and returns False"
  - "The tier guard lives in atomic_lease_eval_game, not in claim_eval_job: the bundled tier-4/4b fall-through stays for the in-process drain (D-12 rejected the skip-tier-4 fallback)"
  - "No version bump and no worker release: WORKER_SCHEMA_VERSION_MIN stays 3, scripts/remote_eval_worker.py untouched"

requirements-completed: [D-12, D-15]

coverage:
  - id: C1
    description: "A server-pool tier-4 claim is blob-only: the NULL line is filled, the other line, every eval_cp/eval_mate, the flaw set and game_best_moves are unchanged, apply_full_eval is never reached"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py#TestTier4BlobDrainTick::test_tier4_tick_fills_null_line_and_keeps_evals"
        status: pass
    human_judgment: false
  - id: C2
    description: "Natural tier-4 games, lichess-eval games, zero-leasable, over-cap, all-fail and deleted-game edge cases behave per contract"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py#TestTier4BlobDrainTick"
        status: pass
    human_judgment: false
  - id: C3
    description: "Version-2 workers (version 2 or param omitted) get 204 on /atomic-lease (explicit, idle, omitted scope), /flaw-blob-lease and /bestmove-lease without any claim being attempted; the entry claim never returns a fed game"
    requirement: "D-15"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py#TestMixedFleetRewalkSafety"
        status: pass
    human_judgment: false
  - id: C4
    description: "A scope-omitted /atomic-lease handed a tier-4 or tier-4b claim returns 204; a tier-1 claim still leases"
    requirement: "D-15"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py#TestMixedFleetRewalkSafety::test_atomic_lease_never_serves_tier4_or_tier4b_claims"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-12
status: complete
---

# Phase 252 Plan 03: Blob-only server-pool tick and mixed-fleet safety Summary

**The in-process drain now re-walks a tier-4 claim through `apply_flaw_blob_results` only (evals, flaws and best moves untouched), and `/atomic-lease` refuses to serve tier-4/4b claims, so version-2 workers and scope-less clients can never full-ply re-lease a re-walk game.**

## Accomplishments

- `_tier4_blob_drain_tick(game_id, user_id)` in `app/services/eval_drain.py`: builds the lease with `_build_flaw_blob_lease_positions`, sentinels via `stamp_flaw_blob_sentinels` when nothing is leasable or the lease exceeds `MAX_SUBMIT_EVALS`, runs one `asyncio.gather` of `evaluate_nodes_multipv2` with no session open, maps results with `_evals_from_multipv2_results` (drops the all-None failure tuple), applies through `apply_flaw_blob_results`, then runs `score_game_flaws_after_apply(..., source="full_eval_drain")` when blobs were written.
- `_full_drain_tick` dispatches `TIER_BLOB_BACKFILL` right after the tier-4b dispatch with a bug-fix comment at the site (before Phase 252 a tier-4 claim fell through to the every-ply gather plus `apply_full_eval`).
- `atomic_lease_eval_game` returns 204 for a `TIER_BLOB_BACKFILL` or `TIER_BESTMOVE_BACKFILL` claim (table-less lottery picks, nothing to release). `claim_eval_job` and `WORKER_SCHEMA_VERSION_MIN` are unchanged.

## D-15 audit: every lane a version-2 worker can still call

Line numbers are in `app/routers/eval_remote.py` unless noted. The fed re-walk game is: `full_evals_completed_at` and `evals_completed_at` set, `blobs_completed_at` NULL, one blob line SQL NULL.

| Lane | Gate / claim (file:line) | Claim predicate | Columns written | Why a fed re-walk game is safe |
|---|---|---|---|---|
| `/atomic-lease` scope explicit | version gate :499 before `claim_eval_job` :503 | v2 never reaches it (204). For v3: tier-1 `eval_jobs` rows only | none at lease | gated for v2; explicit scope never falls to tier 3/4 (`eval_queue_service.py` scope == "explicit" returns None) |
| `/atomic-lease` scope idle | same gate :499 | v2 never reaches it. For v3: tier-3 derived (`full_evals_completed_at IS NULL`) | none at lease | gated for v2; a fed game has `full_evals_completed_at` set so tier 3 never picks it |
| `/atomic-lease` scope omitted | same gate :499; tier guard :515 | bundled 1>3>4>4b; tier 4/4b reach a fed game | none at lease | v2 gated at :499; v3+ clients get 204 at :515 for tier 4/4b (the only open path before this plan) |
| `/flaw-blob-lease` | version gate :884 before `_claim_tier4_blob` :889 | tier-4 lottery (the intended re-walk lane) | none at lease | v2 gated; v3 lane is per-line fill-NULL-only (plan 02) |
| `/bestmove-lease` | version gate :1480 before `_claim_tier4_bestmove` :1487 | tier-4b lottery | none at lease | v2 gated; best-move lane never touches eval_cp, pv or blobs |
| `/entry-lease` (no version gate) | `entry_lease_eval_games` :616, claim `_claim_entry_eval_games` (`app/services/eval_entry.py:422`), predicate `_entry_claim_sql` :412 and probe at :597 | `evals_completed_at IS NULL` only | `entry_eval_lease_expiry` of claimed (never fed) games | a fed game has `evals_completed_at` set, so it is never selected; the feeder never clears `evals_completed_at` |
| `/entry-submit` | `entry_submit_eval` :689; writes at :790 (`_apply_entry_eval_results`), :796 (`_classify_and_insert_flaws`), :802 (`_mark_evals_completed`) | only games it leased AND `Game.evals_completed_at IS NULL` | `eval_cp`/`eval_mate` at entry plies, flaw `INSERT ... ON CONFLICT DO NOTHING` (`game_flaws_repository.py:148`), `evals_completed_at` | never writes pv, best_move or a blob column; no full re-evaluation; unreachable for a fed game without a lease |
| `/atomic-submit`, `/flaw-blob-submit`, `/bestmove-submit` | not version-gated by design (an old worker rejected at submit would burn a full game per cycle) | require a prior lease from a gated lease lane | per lane | unreachable for a re-walk game without a lease from a gated lane; `/flaw-blob-submit` additionally rejects tokens outside the re-derived NULL-line lease (422, plan 02) |

## Mutation proofs

- **D-12 dispatch.** Deleting `if tier == TIER_BLOB_BACKFILL: return await _tier4_blob_drain_tick(...)`: `test_tier4_tick_fills_null_line_and_keeps_evals` failed with `AssertionError: a tier-4 tick must never call apply_full_eval` (1 failed). Restored: green.
- **All-fail guard.** Removing `if not evals: return False`: `test_all_searches_failed_writes_nothing` failed (1 failed, 6 passed). Restored.
- **Over-cap branch.** Removing the `MAX_SUBMIT_EVALS` branch: `test_over_cap_sentinels_only_null_lines` failed (1 failed, 6 passed). Restored.
- **D-15 version gate.** Patching `WORKER_SCHEMA_VERSION_MIN` to 2 in `eval_remote.py`: `test_version2_workers_get_204_on_every_gated_lane` failed with `version-2 worker reached a lease lane: [('atomic-lease', {'worker_schema_version': 2}, {'scope': 'explicit'}), ('atomic-lease', ..., {'scope': 'idle'}), ('atomic-lease', ..., {}), ('/api/eval/remote/flaw-blob-lease', ...)]` (the bestmove lane 204s in that mutated run only because the mocked pick builds an empty lease, but its claim mock is asserted not awaited in the real tree). Restored to 3.
- **D-15 tier guard.** Removing the tier guard in `atomic_lease_eval_game`: `test_atomic_lease_never_serves_tier4_or_tier4b_claims` failed with a 200 full lease for tier 4 (`game_id` of the fed game, all plies as positions). Restored.

## Verification run

- `uv run pytest tests/services/test_full_eval_drain.py -n auto -q`: 76 passed.
- `uv run pytest tests/test_eval_worker_endpoints.py -n auto -q`: 134 passed.
- Wider `uv run pytest -n auto tests/ -q -k "eval or blob or flaw or drain or tier4 or maia"`: 1356 passed, 8 skipped.
- `uv run ty check app/ tests/ scripts/`: all checks passed. `uv run ruff check .` clean, `ruff format` clean.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, no breaches.
- `grep -n "^WORKER_SCHEMA_VERSION_MIN: int = 3" app/routers/eval_remote.py` returns line 163; `git diff --name-only $(git merge-base HEAD main) -- scripts/remote_eval_worker.py` prints nothing.

## Task Commits

1. **Task 1: Tracer, blob-only server-pool tick** - `e987b0b67` (feat)
2. **Task 2: Drain-tick edge cases and mutation proofs** - `a69cb899c` (test)
3. **Task 3: Atomic-lease tier guard and mixed-fleet tests** - `a2153f690` (feat)

## Deviations from Plan

### Plan-form notes (intent met)

- Task 1 ran the dispatch mutation proof immediately (the plan placed it in Task 2) so the tracer commit is already proven; Task 2 added the all-fail and over-cap mutation proofs on top.
- The "game deleted after the claim" behavior is tested as deletion between the lease build and the apply (during the engine phase), the real race window. A game already missing before the lease build leaves `_build_flaw_blob_lease_positions` returning an empty lease, so the tick stamps (a no-op on a missing row) and returns True; harmless and not distinguishable from a processed game.
- The v2 test collects every leaking lane into a list before asserting, so a single mutation reports all leaked lanes instead of stopping at the first.

**Total deviations:** none affecting production behavior.

## Known Stubs

None.

## Threat Flags

None. T-252-06 mitigated (dispatch plus eval-preservation test with `apply_full_eval` raising, mutation-proven); T-252-07 mitigated (sentinels on zero/over-cap leases, all-fail returns False without writing); T-252-23 mitigated (version gates proven by test, atomic-lease tier guard, entry lane audited, mutation-checked).

## Self-Check: PASSED

- Files modified and present: `app/services/eval_drain.py`, `tests/services/test_full_eval_drain.py`, `app/routers/eval_remote.py`, `tests/test_eval_worker_endpoints.py`.
- Commits `e987b0b67`, `a69cb899c`, `a2153f690` are ancestors of HEAD; `git rev-list --count c283dd38b..HEAD` = 3.
