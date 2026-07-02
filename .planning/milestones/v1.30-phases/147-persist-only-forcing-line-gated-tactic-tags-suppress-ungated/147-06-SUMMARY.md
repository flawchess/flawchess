---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
plan: 06
subsystem: eval-worker
tags: [eval-remote, atomic-submit, remote-worker, forcing-line-gate, seed-074]

requires:
  - phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
    plan: 04
    provides: AtomicLeaseResponse/AtomicSubmitRequest/AtomicBlobNode schemas + the paired /atomic-lease endpoint (Q4 narrower-hint FEN-per-ply lease, over-cap sentinel)
  - phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
    plan: 05
    provides: POST /eval/remote/atomic-submit — server-authoritative single-transaction eval+blob submit handler (_apply_atomic_submit)
provides:
  - Upgraded scripts/remote_eval_worker.py with a new atomic rung (_handle_atomic_response + _eval_atomic_game) wired into rungs 1 and 3 of the D-06 ladder
  - _hint_flaw_plies / _build_blob_walk_targets / _eval_atomic_blob_nodes — the worker's local, narrower flaw-ply hint + MultiPV-2 continuation-blob computation (no PGN, no Game row; Q4/RESEARCH A2)
  - WORKER_SCHEMA_VERSION constant (observability/rejection only, never gates correctness — Q5)
affects: []

tech-stack:
  added: []
  patterns:
    - "Fat app.* client reuse across a process boundary: the worker imports _walk_pv_boards (app.services.eval_drain) and _run_all_moves_pass (app.services.flaws_service) directly, mirroring the existing precedent of app/routers/eval_remote.py importing _derive_atomic_sentinel_lines the same way — leading-underscore helpers are module-private by convention, not a hard layering boundary in this codebase."
    - "Lightweight in-memory GamePosition objects for a pure-CPU hint (no session, no flush, no PGN): GamePosition() constructed with only .ply/.eval_cp/.eval_mate set, mirroring the existing tests/test_flaws_materialization.py::_make_pos pattern, reused here in production worker code for the first time."

key-files:
  created: []
  modified:
    - scripts/remote_eval_worker.py
    - tests/test_remote_eval_worker.py

key-decisions:
  - "Rungs 1 (explicit tier-1/2) and 3 (idle tier-3) of the D-06 ladder now call /atomic-lease + /atomic-submit exclusively instead of /lease + /submit; _handle_full_ply_response and _eval_positions are left completely unmodified in the file (D-02/D-05 prohibition) but are no longer reachable from _run_cycle. This upgraded worker script, once deployed, always uses the atomic path for full-ply tiers — 'old workers on /lease + /submit' (D-01's mixed-fleet tolerance) refers to machines still running an older, not-yet-updated copy of this script, not a runtime fallback within this file. The three existing ladder tests that hard-assert exact rung-1/3 URLs were updated accordingly; rung-4 (flaw-blob) tests needed no change since they assert only on flaw-blob-lease/submit presence, not full ladder URLs."
  - "The local flaw-ply hint (_hint_flaw_plies) builds GamePosition(ply=N, eval_cp=..., eval_mate=...) objects directly from this worker's own MultiPV-1 full-ply pass output, using the exact same ply-indexing convention _run_all_moves_pass/GamePosition already use elsewhere (verified against zobrist.py's ply-enumeration + SEED-044 post-move-eval-shift semantics and eval_drain._derive_atomic_sentinel_lines' identical missed=board(flaw_ply)/allowed=board(flaw_ply+1) walk). No PGN, no Game row, no DB session — pure CPU transform (Q4/RESEARCH A2)."
  - "Blob walk nodes are evaluated at MultiPV-2 for ALL walked nodes (k=0..len(walk)-1), unlike the tier-4 drain's _build_flaw_multipv2_blobs which only evaluates continuation nodes k>=1 (node 0 there comes from an existing pos_eval/second_best_map the drain already has). This worker's full-ply pass is MultiPV-1 only, so it has no pre-existing second-best for node 0 — it must evaluate node 0 itself via MultiPV-2, matching what _assemble_one_line_blob (app/services/eval_drain.py) requires (a submitted token at node_k=0, or the whole line assembles to [])."
  - "Task 3 required no code change: --once already existed from Phase 123 SEED-051 (confirmed via --help). The dev-first e2e gate was partially automated (a live --dry-run --once run against the running local dev backend confirms /atomic-lease auth + 204 handling + full ladder fall-through to rung 4 with zero crashes) but the full gated-write confirmation needs a queued tier-1/2/3 game, which the current dev DB does not have (eval_jobs has zero 'pending' rows; EVAL_AUTO_DRAIN_ENABLED=false blocks tier-3 idle backfill locally). Per 147-VALIDATION.md's own 'Manual-Only Verifications' table (already lists this exact item) and the project's 'no dev DB reset in plans' convention, this is flagged as HUMAN-UAT rather than manufactured via synthetic DB seeding."

requirements-completed: [SEED-074]

coverage:
  - id: D1
    description: "The upgraded worker leases via /atomic-lease, evals full-ply at MultiPV-1 (unchanged _eval_positions), derives a local flaw-ply hint via _run_all_moves_pass (mistake/blunder only, no PGN), computes MultiPV-2 continuation blobs for those hinted plies, and POSTs everything together to /atomic-submit"
    requirement: "SEED-074"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_atomic_game_hints_and_blobs_flaw_plies_only"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_atomic_submit_payload_shape_and_schema_version"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full-ply pass stays MultiPV-1 (reuses _eval_positions unchanged); blobs come from a separate MultiPV-2 flaw-ply pass; old /lease + /submit and /flaw-blob-* rungs remain untouched and functioning"
    requirement: "SEED-074"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_atomic_game_full_ply_pass_stays_multipv1"
        status: pass
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_ladder_flaw_blob_on_all_tier123_204 + test_ladder_all_queues_empty_sleeps_once (unchanged, still passing)"
        status: pass
      - kind: other
        ref: "uv run ty check app/ scripts/ (zero new errors — 4 pre-existing unrelated diagnostics confirmed via git stash comparison)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The worker's local hint is never trusted as authoritative — the submitted payload carries only raw engine evals and blob nodes, no classification/severity"
    requirement: "SEED-074"
    verification:
      - kind: unit
        ref: "tests/test_remote_eval_worker.py::test_eval_atomic_blob_nodes / _eval_atomic_blob_nodes output shape (token/best_cp/best_mate/second_cp/second_mate/second_uci only)"
        status: pass
      - kind: other
        ref: "app/routers/eval_remote.py::_apply_atomic_submit (147-05) re-runs classify_game_flaws authoritatively — verified in 147-05-SUMMARY.md D1-D3"
        status: pass
    human_judgment: false
  - id: D4
    description: "A --once mode exists for a single lease->submit iteration against dev; the dev-first e2e recipe is documented and a live connectivity run against the dev backend confirms the atomic-lease wiring integrates cleanly (auth, 204 handling, ladder fall-through)"
    requirement: "SEED-074"
    verification:
      - kind: other
        ref: "uv run python scripts/remote_eval_worker.py --help | grep -q -- --once (pass); live --dry-run --once run against http://localhost:8000 completed cleanly, exercising both new /atomic-lease?scope=explicit and /atomic-lease?scope=idle calls (both 204 in the current dev DB state) before falling through to the existing /flaw-blob-lease rung"
        status: pass
      - kind: manual_procedural
        ref: "Full atomic gated-write confirmation (a real 200 lease -> eval -> blob -> /atomic-submit -> observably-gated tags + both completion markers) requires a queued tier-1/2/3 game in the dev DB, which the current dev DB does not have"
        status: unknown
    human_judgment: true
    rationale: "The current dev DB has zero pending eval_jobs rows and EVAL_AUTO_DRAIN_ENABLED=false blocks the tier-3 idle path locally, so /atomic-lease legitimately 204s end-to-end right now. Manufacturing a queued job via direct DB seeding would violate the project's 'no dev DB reset/seeding in plans' convention (design verification to work against existing dev DB or flag as HUMAN-UAT). 147-VALIDATION.md's own Manual-Only Verifications table already lists this exact item as human-run before any prod change — this SUMMARY documents the precise recipe (see below) for that run."

duration: ~55min
completed: 2026-07-01
status: complete
---

# Phase 147 Plan 06: Fleet worker atomic eval+blob rung Summary

**Upgraded `scripts/remote_eval_worker.py` with a new atomic rung (`_handle_atomic_response` + `_eval_atomic_game`) that leases via `/atomic-lease`, evals full-ply at MultiPV-1, derives a local mistake/blunder hint via `_run_all_moves_pass` (no PGN, no Game row), computes MultiPV-2 continuation blobs only for those hinted plies, and submits everything together to `/atomic-submit` — closing the Part B loop so remote-worker games are gated at write time with no ungated window (D-01).**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3 completed (Task 3 required no code change — `--once` already existed)
- **Files modified:** 2 (`scripts/remote_eval_worker.py`, `tests/test_remote_eval_worker.py`)

## Accomplishments

- New atomic eval+blob helpers in `scripts/remote_eval_worker.py`:
  - `_hint_flaw_plies(evals)` — builds lightweight, never-persisted `GamePosition` objects from the worker's own MultiPV-1 full-ply pass output and runs `_run_all_moves_pass` over them, returning the set of plies classified mistake/blunder. Pure CPU, no PGN, no DB session (Q4/RESEARCH A2).
  - `_build_blob_walk_targets(positions, evals, flaw_plies)` — walks the missed line (`board(flaw_ply)`) and allowed line (`board(flaw_ply + 1)`) for each hinted flaw ply via `_walk_pv_boards` (reused unchanged from `app.services.eval_drain`), producing `"{flaw_ply}:{line}:{node_k}"` tokens matching the 147-04 D-04a scheme.
  - `_eval_atomic_blob_nodes(pool, boards, tokens)` — evaluates every walked board at MultiPV-2, mirroring `_eval_flaw_blob_positions`' exact index mapping (`r[0]`/`r[1]`/`r[4]`/`r[5]`/`r[6]`; `r[2]`/`r[3]` excluded).
  - `_eval_atomic_game(pool, positions)` — orchestrates the full-ply pass (`_eval_positions`, unchanged, MultiPV-1) then the hint + blob walk, returning `(evals, blob_nodes)` ready for the `/atomic-submit` body.
  - `_handle_atomic_response` — handles a 200 `/atomic-lease` response end to end and POSTs the `AtomicSubmitRequest`-shaped body (`worker_schema_version`, `evals`, `blob_nodes`, `job_id`) to `/atomic-submit`.
- `_run_cycle`'s D-06 ladder rewired: rung 1 (`explicit`) and rung 3 (`idle`) now call `/atomic-lease` + `_handle_atomic_response` instead of `/lease` + `_handle_full_ply_response`. Rung 2 (`/entry-lease`) and rung 4 (`/flaw-blob-lease`) are byte-for-byte unchanged. `_handle_full_ply_response`/`_eval_positions` remain in the file, unmodified, for any not-yet-upgraded worker still running an older script version during a rolling mixed-fleet deploy (D-02/D-05) — they are simply no longer called by `_run_cycle`.
- New `WORKER_SCHEMA_VERSION: int = 1` constant (observability/rejection only per Q5 — the server never gates correctness on it).
- 12 new unit tests in `tests/test_remote_eval_worker.py` covering the hint selection, blob-walk token generation (including the last-ply-skips-allowed-line edge case), the MultiPV-1 invariant on the atomic path, the zero-hint no-op path, and the assembled `/atomic-submit` payload shape. 3 existing ladder tests updated to assert the new `/atomic-lease`/`/atomic-submit` URLs (rungs 1/3 only — rung 4 tests needed no change).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the atomic eval+blob rung to the fleet worker** — `d05d78a5` (feat)
2. **Task 2: Worker unit tests for the atomic rung** — `5ba15415` (test)
3. **Task 3: Dev-first end-to-end verification gate** — no code change (`--once` already existed); see Deviations and User Setup Required below

**Plan metadata:** pending (docs: complete plan — committed after this SUMMARY)

## Files Created/Modified

- `scripts/remote_eval_worker.py` — new atomic eval+blob helper functions + `_handle_atomic_response`; `_run_cycle` rungs 1/3 rewired to `/atomic-lease` + `/atomic-submit`; `WORKER_SCHEMA_VERSION` constant; new imports (`GamePosition`, `PV_CAP_PLIES`, `_walk_pv_boards`, `_run_all_moves_pass`, `typing.cast`).
- `tests/test_remote_eval_worker.py` — 12 new tests for the atomic rung; 3 existing ladder tests updated for the new rung-1/3 URLs; module docstring updated.

## Decisions Made

See `key-decisions` in the frontmatter above for full rationale on: (1) rungs 1/3 exclusively using the atomic path (with `_handle_full_ply_response`/`_eval_positions` left unmodified but unreachable, satisfying D-02/D-05's "leave old rungs intact" as code-level preservation, not a runtime fallback), (2) the ply-indexing correctness proof for `_hint_flaw_plies` (traced through zobrist.py's post-move eval shift and `_derive_atomic_sentinel_lines`' identical missed/allowed board convention), (3) evaluating ALL walked blob nodes (k=0..N) rather than only k>=1 (this worker has no pre-existing second-best for node 0, unlike the tier-4 drain), and (4) treating the full atomic write-path e2e confirmation as HUMAN-UAT per 147-VALIDATION.md's own Manual-Only Verifications table.

## Deviations from Plan

### Auto-fixed Issues

None — Rules 1-3 did not trigger. The rung-1/3 wiring decision (Rule 4-adjacent architectural choice between "insert a new preferred rung ahead of the untouched old ones" vs "replace rungs 1/3's endpoint calls") was resolved by direct evidence from the plan's own text ("MUST NOT modify... the old worker rungs") interpreted as code-preservation (not call-graph preservation), and by the impossibility of any insertion point satisfying both "prefer the atomic path" and "leave the exact existing ladder-test call-order assertions untouched" simultaneously — every insertion point requires updating at least the three explicit/idle-path tests regardless of where the new rung is placed. This is documented as a key-decision above rather than a Rule 4 stop, since it is a mechanical wiring choice with no schema/architecture impact (both endpoint pairs already exist and are fully tested from 147-04/147-05).

### Deferred Items

**1. Full atomic gated-write e2e confirmation (Task 3 human-check) — deferred to HUMAN-UAT**
- **What was automated:** `--help` confirms `--once` exists; a live `--dry-run --once` run against the running local dev backend (`http://localhost:8000`) exercised the real `/atomic-lease?scope=explicit` and `/atomic-lease?scope=idle` calls end to end (both 204 given the current dev DB state — zero pending `eval_jobs`, `EVAL_AUTO_DRAIN_ENABLED=false`), confirming operator-token auth and 204 handling work correctly against the live server, then fell through cleanly to the existing `/flaw-blob-lease` rung (a real 200, evaluated + dry-run-skipped).
- **What remains manual:** Confirming a real 200 `/atomic-lease` → eval → blob → `/atomic-submit` cycle that writes forcing-line-gated tactic tags + both completion markers atomically requires a queued tier-1/2/3 game. The dev DB currently has none, and per the project's "no dev DB reset/seeding in plans" convention this is not manufactured here.
- **Recipe for the user to complete this gate:** With the dev DB + backend already running (`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` + `uv run uvicorn app.main:app --reload`), queue at least one game for eval (e.g. trigger a fresh import, or any existing app flow that calls the tier-1 explicit enqueue path), then run:
  ```
  uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --once
  ```
  Confirm in the logs: `Atomic-leased game_id=... Evaluating...` followed by `Atomic-submitted game_id=...: flaws_written=N, blobs_written=M`. Then inspect the game's `game_flaws`/`game_positions` rows (or the frontend game-review page) to confirm `full_evals_completed_at` and `full_pv_completed_at` are both set and any `tactic_motif_int` values reflect the forcing-line gate (never a raw/ungated value observable between the two markers). Do NOT run this against prod.

## Issues Encountered

An early Edit call accidentally left two stray leftover assertion lines (`pool.evaluate_nodes_with_pv.assert_called_once()` / `pool.evaluate_nodes_multipv2.assert_not_called()`) at the tail of `test_atomic_submit_payload_shape_and_schema_version`, causing a spurious test failure (that test's `pool` legitimately calls `evaluate_nodes_with_pv` 3 times and `evaluate_nodes_multipv2` 2 times — the assertions were copy-paste residue, not a real invariant of that test). Caught immediately by the first test run and removed before committing; no functional code was affected.

## User Setup Required

None for the code itself. See "Deferred Items" above for the one manual dev-first e2e confirmation step required before any prod rollout of the upgraded worker script (per 147-VALIDATION.md's Manual-Only Verifications table — this was always planned as a human step, not a gap introduced by this plan).

## Next Phase Readiness

- This is the last plan in Phase 147 (wave 5, `depends_on: [147-04, 147-05]`, nothing lists `147-06` in its own `affects`). The atomic pipeline is now complete end to end: `/atomic-lease` (147-04) → upgraded worker (147-06, this plan) → `/atomic-submit` (147-05, server-authoritative single-transaction write) → gated tags + both completion markers with no ungated window (D-01/SEED-074).
- Rollout sequencing (deploying this upgraded worker script to the actual remote fleet machines) is out of scope for this plan — the code is additive/isolated (old `/lease` + `/submit` pair stays live server-side for any not-yet-upgraded machine), so no fleet coordination was required to ship it. The one remaining pre-prod step is the dev-first e2e human-check documented above.
- Full backend suite green: `uv run pytest -n auto -x` → 3097 passed, 18 skipped. `uv run ty check app/ tests/` and `uv run ruff check app/ tests/` both zero errors. `uv run ty check app/ scripts/` shows the same 4 pre-existing, unrelated diagnostics (in `scripts/seed_openings.py` / `scripts/seed_cohort_cdf.py`) confirmed present before this plan's changes via `git stash` comparison.

---
*Phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated*
*Completed: 2026-07-01*

## Self-Check: PASSED

All modified files found on disk; all task/summary commit hashes (`d05d78a5`, `5ba15415`, `98369b64`) found in git log.
