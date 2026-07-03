---
quick_id: 260703-nux
title: "SEED-076 — cache-aware incremental lease + blob-preserving classify"
status: complete
date: 2026-07-03
---

# SEED-076 — hardened atomic eval lease/submit against weak-worker timeout holes

Implemented the full cache-aware **incremental** lease design (user-approved after two
scope checkpoints that surfaced two correctness gaps in the locked seed).

## What shipped

1. **Submit-side cache fill (the core correctness fix).** `_apply_submit` and
   `_apply_atomic_submit` now build a real `opening_position_eval`-backed `dedup_map`
   (mirroring `_full_drain_tick`) instead of `{}`. Cached opening plies a weak worker
   timed out on are filled server-side **before** `failed_ply_count` is computed, so a
   fillable hole never reaches the Path-C cap and gets permanently stamped (FLAWCHESS-8B).
   Engine-game-guarded so a direct-POST lichess game keeps its %eval best_move.

2. **`preserve_existing_evals` guard** (`_apply_full_eval_results`, new opt-in param). An
   engine-game row that already has a DB eval but resolves to None this submit (its
   position was dropped from the incremental re-lease) is treated as resolved — not
   counted as a hole, not overwritten. Default `False` → the local drain is unchanged.

3. **Incremental + cache-aware lease** (`_build_lease_positions` + new
   `_lease_position_redundant` / `_fetch_cached_opening_hashes`). Omits positions already
   fillable server-side: cached openings, and plies whose DB row (row Q-1, post-move
   shift) already has an eval or is the legit game-over NULL. Terminal donor always kept
   (SEED-044); falls back to the full list if filtering empties the lease (never starve a
   claimed game of the submit that triggers the dedup fill). Wired into both
   `lease_eval_game` and `atomic_lease_eval_game`.

4. **Blob/tag-preserving classify** (`_snapshot_preserved_flaw_blobs` /
   `_restore_preserved_flaw_blobs` in `_apply_atomic_submit`). `_classify_and_fill_oracle`
   does delete-then-insert, so a sparse atomic retry (worker doesn't re-blob an
   already-done midgame flaw) would wipe its `{allowed,missed}_pv_lines` + 8 tactic-tag
   columns. We snapshot those 10 columns before classify and restore them after the blob
   write for flaws NOT re-blobbed this submit. "Freshly blobbed" counts only non-empty
   blobs, so a transient `[]`-sentinel (no PV to walk on a sparse retry) is correctly
   overridden by the preserved real blob. `game_positions.pv` is untouched by a sparse
   retry (classify step 6 only updates plies present in `engine_result_map`), so tier-4
   healing input survives regardless.

## Two design gaps found & fixed during implementation
- The locked seed's "exclude already-eval'd plies" broke `failed_ply_count` for midgame
  plies (resolve path ignores existing DB evals) → fixed by the gated `preserve_existing_evals`.
- The already-eval'd exclusion wiped midgame flaw blobs/tags via delete-then-insert on
  atomic retries → fixed by snapshot/restore, including the `[]`-sentinel override subtlety.

## Tests (tests/test_eval_worker_endpoints.py, +8)
- Lease: omits already-eval'd; omits cached opening; keeps terminal when all rows filled;
  empty-filter falls back to full list.
- Submit: fills cached opening hole server-side → Path A (seed req a); uncached residual
  hole bounded by Path C (seed req b); preserve guard keeps omitted eval'd ply out of the
  hole count → Path A; atomic retry preserves existing flaw blobs + tactic tags.

## Verification
- `ruff format` + `ruff check` + `ty check app/ tests/` → clean.
- Full backend suite `pytest -n auto` → **3151 passed, 18 skipped**.
- Backend-only change; no frontend gate needed.

## Files
- `app/services/eval_drain.py` — `preserve_existing_evals` param + guard.
- `app/routers/eval_remote.py` — dedup_map on both submit paths; incremental/cache-aware
  lease + helpers; snapshot/restore of flaw blobs/tags.
- `tests/test_eval_worker_endpoints.py` — 8 regression tests.
