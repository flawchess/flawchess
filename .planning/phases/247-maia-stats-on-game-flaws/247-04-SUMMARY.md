---
phase: 247-maia-stats-on-game-flaws
plan: 04
subsystem: maia-flaw-scoring
tags: [maia, eval-remote, atomic-submit, flaw-blob-submit, game_flaws]
requires: ["247-02"]
provides:
  - "app/routers/eval_remote.py: post-commit score_game_flaws_after_apply hooks in _apply_atomic_submit (source=remote_eval_worker) and _apply_flaw_blob_submit (source=flaw_blob_submit, targets=None)"
  - "7 endpoint tests (3 atomic-submit, 4 flaw-blob-submit) in tests/test_eval_worker_endpoints.py"
affects: [247-05]
status: complete
commits: 2
plan_head_before: 8b694a87f182c8de105433223fd1468a0a32fa3d
plan_head_after: 987d35ff42164f1ac5d4e71912a89d27bb7c5b6b
actuals:
  tokens: 7500
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "one-call post-commit hook in the router; the scorer swallows and reports its own failures so the HTTP outcome never depends on Maia"
key-files:
  created: []
  modified:
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py
key-decisions:
  - "Atomic-submit hook sits after the outcome-is-None 404 branch and before the stamp_complete signal, so Path B (incomplete) submits are scored too, same as the drain lane"
  - "Blob-submit hook is guarded by the in-lock survivor-filtered blob_map and sits after the write_session commit; the idempotent early return is untouched"
requirements-completed: [D-08, D-13, D-14]
---

# Phase 247 Plan 04: Remote-worker Maia hooks Summary

The two remote write lanes now run the shared post-commit scorer: a Maia-loaded `/atomic-submit` scores every flaw of the game and stamps it, and a tier-4 `/flaw-blob-submit` that writes blobs re-scores the game so `maia_second_*` is filled on already-stamped games once `missed_pv_lines` arrives late (D-14).

## Accomplishments

- `app/routers/eval_remote.py`: import of `score_game_flaws_after_apply` plus two hook calls (17 lines, no other router logic). Atomic lane passes the in-memory `targets`; blob lane passes `targets=None` so the scorer rebuilds exact boards from `games.pgn` (D-06). The result bool is ignored; response models are unchanged.
- Maia absent: no Maia column written, stamp stays NULL. Scorer exception: submit still 200, evals/flaws committed, game unstamped.
- No new drain or lottery tier (D-11 holds); `/flaw-blob-lease` and the idempotent early return never call the scorer.

## Tests

`tests/test_eval_worker_endpoints.py`, using `tests/services/maia_fakes.fake_full_policy` and a sentinel `maia_engine._session`:

- `TestAtomicSubmitEndpoint`: `test_atomic_submit_maia_flaw_scores_and_stamps` (tracer), `..._absent_leaves_unstamped`, `..._scorer_error_still_200`.
- `TestFlawBlobSubmitEndpoint`: `test_blob_submit_maia_flaw_rescore_fills_second`, `..._second_equals_best_stays_null`, `..._idempotent_no_rescore` (spy on `eval_remote.score_game_flaws_after_apply`, one call for the first submit, none for the repeat, all eight values and the stamp unchanged), `..._absent_noop`.
- The blob tests pre-seed through the real scorer (`targets=None`, source `backfill`) after fixing the placeholder flaw FEN to the true pre-move placement and setting `game_positions.best_move`, so the starting state is a genuinely stamped flaw with `maia_second_*` NULL.
- All new games are deleted in `finally`, so none leak into the tier-3 eval lottery.
- Concurrency edge (D-14): backstop only, covered at scorer level by plan 02 `test_fingerprint_changed_skips_write` and the shared per-game advisory lock.

## Mutation proofs

- Task 1: deleting the atomic-submit hook failed `test_atomic_submit_maia_flaw_scores_and_stamps` on the Maia column assertion (`assert None is not None`); restored, 3 passed.
- Task 2: deleting the blob-submit hook failed `test_blob_submit_maia_flaw_rescore_fills_second` (maia_second_prob assertion) and `test_blob_submit_maia_flaw_idempotent_no_rescore` (`[] == ['flaw_blob_submit']`); restored, 4 passed.
- Extra probe: replacing the `if blob_map:` guard with `if True:` did NOT fail any test. The guard only matters when the in-lock survivor filter empties blob_map (flaws deleted mid-flight) or a sentinel-only write; the all-blobs-written case returns earlier through the idempotent branch, which the idempotent test does cover. That corner is not separately tested.

## Verification

- `uv run pytest tests/test_eval_worker_endpoints.py`: 116 passed.
- `uv run pytest -n auto -q`: 5751 passed, 20 skipped. `test_lease_lifo` did not flake in this run.
- `uv run ty check app/ tests/ scripts/`: All checks passed. ruff format and check clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches (1307 functions).

## Deviations from Plan

**1. [Process] Both hooks landed in the Task 1 commit.** I applied both router edits in one pass, so `d71ff8fee` contains the `flaw_blob_submit` hook as well as the atomic one; the Task 2 commit (`987d35ff4`) is tests only. The behavior is unchanged and each hook is still covered by its own tests and mutation proof. Not rewritten, to keep history linear.

**2. [Cosmetic] Acceptance grep.** `grep -c "score_game_flaws_after_apply(async_session_maker, game_id, targets=targets"` prints 0 because ruff format wraps the call across lines (the single-line form exceeds the line length). The call exists with the intended arguments (`app/routers/eval_remote.py`, atomic hook), mirroring the multi-line call in `eval_drain.py`. The `source="flaw_blob_submit"` grep prints one line as specified.

## Known Stubs

None.

## Threat Flags

None. T-247-06 (worker-supplied su as a key into the server-computed legal policy) is mitigated by the scorer from plan 02; T-247-07 by off-thread inference with no session open and self-contained error handling; T-247-08 by the shared advisory lock plus in-lock fingerprint re-check.

## Self-Check: PASSED

Files present: `app/routers/eval_remote.py`, `tests/test_eval_worker_endpoints.py`. Commits d71ff8fee and 987d35ff4 verified on the branch.
