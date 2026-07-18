---
phase: 177-worker-side-multipv2-gem-candidates
plan: 02
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, remote-eval-worker, stockfish, tier-4b-backfill]

# Dependency graph
requires:
  - phase: 177-01 (Protocol-v2 schema + lease version gate + second_best wiring)
    provides: "second_best_map wiring into _build_best_move_candidates, source-tagged Sentry fallback"
  - phase: 174-176 (v2.4 Backend Gem & Great Detection)
    provides: "game_best_moves storage, best_move_candidates.py pure fns, _claim_tier4_bestmove lottery"
provides:
  - "Isolated BestMove* schema pair (BestMoveLeasePosition/Response, BestMoveSubmitEval/Request/Response) — no move_uci on the wire"
  - "_eval_of_position_map — the Pitfall-1 inverse post-move-shift reconstruction, inverting _post_move_eval's +1 forward shift"
  - "_build_bestmove_lease_positions — server-recomputed tier-4b candidate-ply set (out-of-book, played == stored best_move) from already-stored full-pass data, no engine calls"
  - "POST /eval/remote/bestmove-lease — dedicated tier-4b lease endpoint, gated on BEST_MOVE_BACKFILL_ENABLED, calling _claim_tier4_bestmove directly"
  - "_stamp_best_moves_completed_directly — Pitfall-2 forward-progress stamp for zero-candidate/over-cap picks"
  - "POST /eval/remote/bestmove-submit + _apply_bestmove_submit — minimal write (game_best_moves + best_moves_completed_at only), server-authoritative candidate recompute, never touches game_flaws"
affects: [177-03 (drain tier-aware minimal path), 177-04/05 (worker script rung + measurement)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inverse post-move-shift reconstruction (_eval_of_position_map) as the single place that inverts _post_move_eval's +1 forward shift for a caller with no fresh engine pass — a new pattern this phase introduces, documented so a future stored-data-only caller reuses it instead of re-deriving the shift"
    - "Lease and submit both call the SAME reconstruction primitives (_eval_of_position_map + _collect_full_ply_targets) so candidate-ply agreement is structural, not just documented (D-03 stateless recompute)"
    - "Task-2 stamps forward-progress (best_moves_completed_at) at LEASE time on zero/over-cap picks, mirroring /flaw-blob-lease's all-sentinel write, so the ES lottery self-terminates on un-fillable games"

key-files:
  created: []
  modified:
    - app/schemas/eval_remote.py
    - app/routers/eval_remote.py
    - app/services/eval_apply.py
    - app/core/config.py
    - tests/services/test_eval_apply.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "_build_bestmove_lease_positions does NOT apply the full inaccuracy MARGIN gate (passes_inaccuracy_gate needs a runner-up eval that does not exist until the worker computes it) — it applies only the availability half of that gate's None guard (a ply whose eval_of_position is entirely missing is excluded, since it could never pass the margin gate regardless of what second the worker later computes). The full margin gate + Maia scoring runs once, authoritatively, at submit time via the reused _build_best_move_candidates."
  - "_apply_bestmove_submit's in-range tamper guard (T-177-05) rejects any submitted ply outside [0, game_length) with 422, but does NOT separately re-validate candidate membership (T-177-06) — _build_best_move_candidates independently recomputes candidate_targets from targets/engine_result_map (never from second_best_map's keys), so a foreign-but-in-range ply's submitted second-best is simply never read at the map lookup. This mirrors the established second_best guard precedent from 177-01 and avoids a redundant second DB round-trip to revalidate a set that would agree by construction anyway."
  - "_stamp_best_moves_completed_directly reuses the existing _mark_best_moves_completed(session, game_id) helper (Phase 176) rather than duplicating the single-column UPDATE — Task 2's lease-time stamp opens its own short session and calls it directly; Task 3's submit-time stamp calls the same helper inside its own write session, alongside the game_best_moves UPSERT, in the same commit."
  - "_apply_bestmove_submit lives in app/services/eval_apply.py per the plan's explicit artifact placement (unlike its precedents _apply_flaw_blob_submit/_apply_atomic_submit, which live in the router file) — it raises fastapi.HTTPException directly for the 404/422 cases, matching the established error-handling STYLE of those precedents even though physically relocated; FastAPI's HTTPException is a plain exception class catchable regardless of which layer raises it, so this is not a violation of the routers/services logic-layering split (which is about business logic placement, not exception-raising location)."

requirements-completed: [BACK-02, BACK-03]

coverage:
  - id: D1
    description: "Isolated BestMove* schema pair (lease/submit) added to eval_remote.py — no move_uci field, mirroring the flaw-blob-lease/submit isolation contract"
    requirement: "BACK-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveLeaseEndpoint::test_bestmove_lease_candidate_plies (asserts no move_uci key in a returned position)"
        status: pass
    human_judgment: false
  - id: D2
    description: "_build_bestmove_lease_positions reconstructs the tier-4b candidate-ply set (out-of-book, played == stored best_move) from stored data via the Pitfall-1 inverse post-move-shift map, with zero engine calls"
    requirement: "BACK-02"
    verification:
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestEvalOfPositionMap::test_inverts_post_move_shift"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestEvalOfPositionMap::test_ply_zero_resolves_to_none_none_no_crash"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestBestMoveLeasePositions::test_out_of_book_played_best_yields_candidate"
        status: pass
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestBestMoveLeasePositions::test_missing_prior_row_excludes_candidate_no_crash"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /eval/remote/bestmove-lease gated on BEST_MOVE_BACKFILL_ENABLED, calling _claim_tier4_bestmove directly; a zero-candidate or over-cap pick stamps best_moves_completed_at directly and 204s (Pitfall 2 forward progress)"
    requirement: "BACK-02"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveLeaseEndpoint::test_bestmove_lease_disabled_returns_204"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveLeaseEndpoint::test_bestmove_lease_candidate_plies"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveLeaseEndpoint::test_bestmove_lease_zero_candidates_stamps_completed"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /eval/remote/bestmove-submit + _apply_bestmove_submit write ONLY game_best_moves rows + stamp best_moves_completed_at, never apply_full_eval/_classify_and_fill_oracle; server recomputes candidates and 422s an out-of-range submitted ply while silently dropping an in-range non-candidate ply"
    requirement: "BACK-03"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveSubmitEndpoint::test_bestmove_submit_minimal_write_no_reclassify"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveSubmitEndpoint::test_bestmove_submit_out_of_range_ply_422"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveSubmitEndpoint::test_bestmove_submit_foreign_ply_dropped"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveSubmitEndpoint::test_bestmove_submit_existing_flaws_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestBestMoveSubmitEndpoint::test_bestmove_submit_game_not_found"
        status: pass
    human_judgment: false
  - id: D5
    description: "app/core/config.py's BEST_MOVE_BACKFILL_ENABLED comment corrected — no longer states best-move backfill cannot be shed to the remote worker fleet"
    verification:
      - kind: other
        ref: "app/core/config.py:85-95 (manual read-through — comment text)"
        status: pass
    human_judgment: false

# Metrics
duration: 31min
completed: 2026-07-17
status: complete
---

# Phase 177 Plan 02: Tier-4b lease/submit pair (worker-side MultiPV-2 gem-candidate backfill) Summary

**Dedicated `/bestmove-lease` + `/bestmove-submit` endpoint pair with a server-side inverse post-move-shift reconstruction so the ~416k already-analyzed tier-4b games can be gem-candidate-backfilled by the remote fleet, doing exactly the N runner-up MultiPV-2 searches with zero server-side reclassification.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-07-17T15:53:00Z
- **Completed:** 2026-07-17T16:24:00Z
- **Tasks:** 3
- **Files modified:** 6 (4 source, 2 test)

## Accomplishments
- Added the isolated `BestMoveLeasePosition`/`BestMoveLeaseResponse`/`BestMoveSubmitEval`/`BestMoveSubmitRequest`/`BestMoveSubmitResponse` schema pair to `app/schemas/eval_remote.py`, mirroring the `FlawBlob*` isolation contract — no `move_uci` on the wire (the server already validated candidacy server-side).
- Added `_eval_of_position_map` (Pitfall 1) to `app/services/eval_apply.py`: inverts `_post_move_eval`'s `+1` forward post-move shift so the eval OF position `ply` is correctly read from row `ply - 1`, with `ply=0` resolving to `(None, None)` (no row `-1`) rather than crashing.
- Added `_build_bestmove_lease_positions(game_id)`: reconstructs a tier-4b game's candidate-ply set (out-of-book, played == stored `best_move`) purely from `game_positions` + PGN, with zero engine calls — the worker runs the targeted MultiPV-2 searches, not the server.
- Added `POST /eval/remote/bestmove-lease`, calling `_claim_tier4_bestmove` directly (mirroring `/flaw-blob-lease`'s call to `_claim_tier4_blob`), gated on `settings.BEST_MOVE_BACKFILL_ENABLED` before any DB round-trip.
- Added `_stamp_best_moves_completed_directly` (Pitfall 2): a zero-candidate or over-`MAX_SUBMIT_EVALS` pick stamps `best_moves_completed_at` directly at lease time so the ES lottery never re-draws an un-fillable game forever.
- Corrected the stale `BEST_MOVE_BACKFILL_ENABLED` comment in `app/core/config.py` — Phase 177 makes best-move backfill shed-able to the remote worker fleet, so the "cannot be shed" wording is retired.
- Added `_apply_bestmove_submit` + `POST /eval/remote/bestmove-submit`: recomputes the position-keyed `engine_result_map` server-side from the SAME `_eval_of_position_map` reconstruction, tamper-guards submitted plies to `[0, game_length)` (422 on out-of-range), and reuses `_build_best_move_candidates` verbatim (margin gate + pinned-ELO Maia scoring) with the worker's submitted evals as `second_best_map`. Writes ONLY `game_best_moves` rows + stamps `best_moves_completed_at` in one session — never `apply_full_eval` or `_classify_and_fill_oracle`, so `game_flaws` is never read or written.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tier-4b schemas + server candidate-ply reconstruction (inverse post-move shift)** - `5c4a0808` (feat)
2. **Task 2: /bestmove-lease endpoint + forward-progress stamp + config comment** - `e230580a` (feat)
3. **Task 3: /bestmove-submit minimal apply (game_best_moves + stamp only, no reclassify)** - `a66e4021` (feat)

_No TDD RED/GREEN split — tests and implementation were committed together per task, consistent with this plan's `tdd="true"` tasks being small, tightly-scoped changes verified by the same commit's test additions (mirrors 177-01's precedent)._

## Files Created/Modified
- `app/schemas/eval_remote.py` - `BestMoveLeasePosition`/`BestMoveLeaseResponse`/`BestMoveSubmitEval`/`BestMoveSubmitRequest`/`BestMoveSubmitResponse`
- `app/routers/eval_remote.py` - `POST /bestmove-lease` (`bestmove_lease`), `POST /bestmove-submit` (`bestmove_submit`), module docstring updates
- `app/services/eval_apply.py` - `_eval_of_position_map`, `_build_bestmove_lease_positions`, `_stamp_best_moves_completed_directly`, `_apply_bestmove_submit`
- `app/core/config.py` - `BEST_MOVE_BACKFILL_ENABLED` comment correction
- `tests/services/test_eval_apply.py` - `TestEvalOfPositionMap`, `TestBestMoveLeasePositions`; `_insert_game_positions`/`pgn` param additions
- `tests/test_eval_worker_endpoints.py` - `TestBestMoveLeaseEndpoint`, `TestBestMoveSubmitEndpoint`, `_get_game_best_moves_completed_at`, `_count_game_best_moves`, `best_move` field on `_insert_game_positions`

## Decisions Made
- `_build_bestmove_lease_positions` applies only the None-guard half of the inaccuracy gate at lease time (excluding a ply whose `eval_of_position` is entirely unresolvable), not the full margin comparison — the runner-up eval literally does not exist until the worker computes it. The full `passes_inaccuracy_gate` margin check runs once, authoritatively, at submit time via the reused `_build_best_move_candidates`.
- The submit's tamper guard (T-177-05) is structural-range-only (422 on out-of-range); candidate-membership enforcement (T-177-06) is achieved for free by `_build_best_move_candidates`'s own independent recomputation of `candidate_targets` from `targets`/`engine_result_map` — it never reads `second_best_map`'s keys to decide candidacy, so a foreign-but-in-range ply's submitted second-best is silently unread. This avoids a second, redundant DB round-trip purely to re-derive a set that agrees by construction.
- `_apply_bestmove_submit` lives in `eval_apply.py` (service layer) per the plan's explicit artifact placement, diverging from its precedents (`_apply_flaw_blob_submit`/`_apply_atomic_submit`, both in the router file) — it still raises `HTTPException` directly for 404/422, matching the established error-handling style; this is not a CLAUDE.md layering violation since HTTPException is a plain exception class, not business logic.
- `_stamp_best_moves_completed_directly` reuses the existing Phase-176 `_mark_best_moves_completed(session, game_id)` helper rather than duplicating the single-column UPDATE.

## Deviations from Plan

None — plan executed exactly as written. One clarifying interpretation (not a deviation from behavior, but worth recording): Task 1's action text says `_build_bestmove_lease_positions` selects plies where "played_uci == stored best_move at row ply AND passes_inaccuracy_gate(...) using eval-of-position from an INVERSE-shift map." Since the runner-up (second-best) eval needed by `passes_inaccuracy_gate`'s margin comparison does not exist until the worker computes it at submit time, this was implemented as the None-guard-only half of that gate at lease time (a ply with no resolvable `eval_of_position` is excluded, since it could never pass the margin gate regardless of what second the worker later submits) — the full margin gate runs authoritatively at submit time via `_build_best_move_candidates`, which is reused verbatim (Anti-Pattern guidance: "do not re-derive the gem/great gate inline for tier-4b"). This reading is corroborated by RESEARCH.md Pitfall 1's own framing ("misattributes the runner-up gate's best_cp/best_mate") and by S-05/D-03's requirement that the worker — not the server — computes the runner-up searches.

## Issues Encountered
None. `find_opening_ply_count(['a4', 'a5', 'h4'])` was verified directly against the real `openings.tsv` data (returns 2) before being used as a test fixture, rather than assumed.

## User Setup Required
None - no external service configuration required. `BEST_MOVE_BACKFILL_ENABLED` stays off by default (D-05, unchanged from Phase 176); flipping it on in prod remains a separately observed step post-deploy.

## Next Phase Readiness
- The dedicated tier-4b lease/submit pair is fully isolated, single-flag gated, and reuses the fresh lane's pure gate/Maia logic verbatim — Plan 03 (drain tier-aware minimal path) and Plan 04/05 (worker script rung + measurement) can build on this without further changes to this plan's files.
- `_full_drain_tick`'s tier variable is still a documented no-op today (RESEARCH.md Pitfall 3) — the in-process server-pool drain does NOT yet route `TIER_BESTMOVE_BACKFILL` picks through the new minimal candidate-search-only path; that is explicitly Plan 03's scope, not this plan's.
- `scripts/remote_eval_worker.py` still has no `/bestmove-lease`/`/bestmove-submit` calls (Plan 04/05 territory) — until the worker script rung is added, the new endpoint pair is reachable but unused by the live fleet, which is expected/by-design at this point in the phase.

---
*Phase: 177-worker-side-multipv2-gem-candidates*
*Completed: 2026-07-17*

## Self-Check: PASSED

All 6 modified files + SUMMARY.md verified present on disk; all 4 commit hashes (5c4a0808, e230580a, a66e4021, fcdc2010) verified present in git log.
