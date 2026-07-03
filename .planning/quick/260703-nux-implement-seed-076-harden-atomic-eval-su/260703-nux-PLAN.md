---
quick_id: 260703-nux
title: "SEED-076 — cache-aware incremental lease + blob-preserving classify"
status: in-progress
---

# SEED-076: Harden atomic eval lease/submit against weak-worker timeout holes

Full-incremental design (user-approved after two scope checkpoints). Server-side only.

## Root cause (recap)
Weak remote worker times out (`_NODES_TIMEOUT_S=5s`) on high-branching opening positions,
submits partial evals. The atomic path passes `dedup_map={}` and re-leases the whole game,
so fillable cached-opening holes reach `MAX_EVAL_ATTEMPTS` and get Path-C-stamped permanently.

## Changes

### 1. Submit-side cache-aware fill (the correctness fix)
`app/routers/eval_remote.py` — `_apply_submit` + `_apply_atomic_submit`: replace
`dedup_map = {}` with a real `_fetch_dedup_evals(...)` lookup (mirror `_full_drain_tick`),
built from the game's opening full_hashes. Cached openings the worker timed out on are
filled server-side BEFORE `failed_ply_count` is computed → no permanent stamp of a
fillable hole.

### 2. `preserve_existing_evals` guard (incremental-lease correctness)
`app/services/eval_drain.py` — `_apply_full_eval_results`: new `preserve_existing_evals=False`
param. When True (submit paths only), an engine-game row that already carries a non-NULL DB
eval but resolves to None this submit (its position was omitted from the incremental re-lease)
is treated as resolved — NOT counted as a hole, NOT overwritten. Default False keeps the
local drain unchanged (zero blast radius).

### 3. Incremental + cache-aware lease
`app/routers/eval_remote.py` — `_build_lease_positions(cached_hashes=frozenset())`: omit a
position Q when (a) its opening full_hash is in `opening_position_eval` (cache-aware; submit
dedup fills it), or (b) the DB row it fills (row Q-1, post-move shift) already has an eval or
is a legit game-over NULL (incremental). Terminal donor always kept (SEED-044). Safety net:
if filtering empties the lease, fall back to the unfiltered list (never starve a claimed
game of the submit that triggers the dedup fill). Both `lease_eval_game` and
`atomic_lease_eval_game` fetch `cached_hashes` in their read session and pass it in.

### 4. Blob/tag-preserving classify (atomic path only)
`_classify_and_fill_oracle` does delete-then-insert, so a sparse atomic retry (worker doesn't
re-blob already-done midgame flaws) would wipe `game_flaws.{allowed,missed}_pv_lines` +
8 tactic-tag columns → tier-4 churn + transient quality loss. Fix in `_apply_atomic_submit`:
snapshot those 10 columns (for flaws with `allowed_pv_lines IS NOT NULL`) BEFORE classify,
then restore them AFTER `_run_multipv2_pass` for flaws NOT re-blobbed this submit
(`ply not in flaw_pv_blobs`). `game_positions.pv` is not wiped (step 6 only updates plies
present in engine_result_map), so tier-4 healing input survives regardless.

## Not needed
- Plain `/submit` never carries blobs (deferred to tier-4), so no snapshot/restore there.
- No shared-classify rework: snapshot/restore is localized to `_apply_atomic_submit`.

## Tests (tests/test_eval_worker_endpoints.py)
- Incremental lease omits cached + already-eval'd, keeps terminal + genuine holes.
- Atomic submit fills cached-opening holes server-side without worker round-trip (seed req a).
- preserve guard: omitted already-eval'd ply not counted as hole → Path A.
- Uncached residual hole stays bounded by Path C (seed req b).
- Atomic retry preserves existing flaw blobs/tags (classify fix).
