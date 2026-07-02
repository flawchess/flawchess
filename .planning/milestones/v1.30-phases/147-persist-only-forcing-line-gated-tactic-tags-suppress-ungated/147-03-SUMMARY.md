---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
plan: 03
subsystem: api
tags: [eval-remote, flaw-blob-lease, dos-guard, tier-4-lottery, seed-073]

requires:
  - phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
    plan: 01
    provides: blobs_pending suppression signal at _apply_submit (unrelated call path, no code dependency, but same file/module family)
provides:
  - Over-cap sentinel branch in flaw_blob_lease — fat games (>MAX_SUBMIT_EVALS walkable flaw-blob positions) sentinel cleanly to 204 instead of 500ing
  - Reusable over-cap sentinel pattern for Part B's atomic-lease endpoint to build on
affects: [147-04, 147-05, 147-06]

tech-stack:
  added: []
  patterns:
    - "Over-cap DoS-guard branch: when a would-be response exceeds a shared max_length cap, sentinel the underlying data (clear the predicate that re-selects it) and return an empty/204 response instead of ever constructing the oversized payload"

key-files:
  created: []
  modified:
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "New elif len(lease_positions) > MAX_SUBMIT_EVALS branch, distinct from the existing `if not lease_positions` all-sentinel branch — over-cap games have a non-empty lease_positions"
  - "The sentinel ply set is derived from a fresh query of the game's NULL-blob flaw rows (GameFlaw.allowed_pv_lines IS NULL), not from sentinel_lines — sentinel_lines only covers un-walkable lines, which under-covers the over-cap case where most lines ARE walkable but the total exceeds the cap"
  - "MAX_SUBMIT_EVALS imported from app.schemas.eval_remote, unchanged — no new constant, no DoS-guard weakening"
  - "Test monkeypatches _build_flaw_blob_lease_positions to return an oversized list (real seeding of >1024 walkable positions is impractical) but queries/asserts against real GameFlaw rows for the write path"

requirements-completed: [SEED-074]

coverage:
  - id: D1
    description: "A game whose total walkable flaw-blob lease positions exceed MAX_SUBMIT_EVALS (1024) no longer 500s on /flaw-blob-lease; it writes [] sentinels for every NULL-blob flaw ply and returns 204 in one pass"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestFlawBlobLeaseEndpoint::test_blob_lease_over_cap_sentinels_all_null_blob_flaws"
        status: pass
    human_judgment: false
  - id: D2
    description: "The over-cap game's existing tactic tags are unchanged — sentinel-ing does not run the gated retag"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestFlawBlobLeaseEndpoint::test_blob_lease_over_cap_sentinels_all_null_blob_flaws"
        status: pass
    human_judgment: false
  - id: D3
    description: "Existing flaw-blob-lease behaviors (empty queue, walkable game, token parsing, all-sentinel, submit isolation) remain unaffected"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestFlawBlobLeaseEndpoint (7 tests) + TestFlawBlobSubmitEndpoint"
        status: pass
      - kind: other
        ref: "uv run ty check app/ tests/ (zero errors) + uv run ruff check app/ tests/ + uv run pytest -n auto (3079 passed, 18 skipped, full backend suite)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-01
status: complete
---

# Phase 147 Plan 03: Over-cap sentinel prerequisite for flaw-blob-lease Summary

**Fat games (>1024 walkable flaw-blob positions) no longer 500 and loop forever in the tier-4 lottery — a new `elif len(lease_positions) > MAX_SUBMIT_EVALS` branch in `flaw_blob_lease` sentinels every NULL-blob flaw ply and returns 204 in one pass, establishing the over-cap pattern Part B's atomic-lease endpoint reuses.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 completed
- **Files modified:** 2 (app/routers/eval_remote.py, tests/test_eval_worker_endpoints.py)

## Accomplishments

- Fixed the real dormant SEED-073 bug: `_build_flaw_blob_lease_positions` returns every walkable node across every NULL-blob flaw's two PV lines with no cap check before `FlawBlobLeaseResponse.positions` (max_length=`MAX_SUBMIT_EVALS`) is constructed. Games with enough flaws × PV length to exceed 1024 walkable positions raised a Pydantic `ValidationError` → 500, and the tier-4 lottery re-picked the same game forever since no blob was ever written (the predicate never cleared).
- New `elif len(lease_positions) > MAX_SUBMIT_EVALS:` branch in `flaw_blob_lease` (app/routers/eval_remote.py), distinct from the existing `if not lease_positions:` all-sentinel branch (over-cap games have a non-empty `lease_positions`, just too many). Queries the game's full NULL-blob flaw-ply set fresh via `GameFlaw.allowed_pv_lines.is_(None)` (mirroring the existing query pattern in `_apply_flaw_blob_submit`'s read phase) — not derived from `sentinel_lines`, which only covers un-walkable lines and would under-sentinel the mostly-walkable over-cap case. Writes `{ply: ([], [])}` for every one of those plies via `_batch_update_flaw_pv_lines` inside its own write session + commit, then returns 204.
- `MAX_SUBMIT_EVALS` imported unchanged from `app.schemas.eval_remote` — no new constant, no DoS-guard weakening (T-147-04 mitigated).
- New integration test `test_blob_lease_over_cap_sentinels_all_null_blob_flaws` seeds two real `GameFlaw` rows (NULL blobs, pre-set tactic tags) and monkeypatches `_build_flaw_blob_lease_positions` to return an oversized (>1024) `lease_positions` list — since seeding that many real walkable positions is impractical. Asserts 204, zero remaining NULL-blob flaws (both `allowed_pv_lines`/`missed_pv_lines` become `[]`), and that `allowed_tactic_motif`/`missed_tactic_motif` are byte-for-byte unchanged (the sentinel write never runs the gated retag).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the over-cap sentinel branch to flaw_blob_lease** — `05b5e6fd` (feat)
2. **Task 2: Router test — over-cap game sentinels to 204, no 500, tags unchanged** — `2f8aefe2` (test)

**Plan metadata:** pending (docs: complete plan — committed after this SUMMARY)

## Files Created/Modified

- `app/routers/eval_remote.py` — new `elif len(lease_positions) > MAX_SUBMIT_EVALS:` branch in `flaw_blob_lease`, plus `MAX_SUBMIT_EVALS` import.
- `tests/test_eval_worker_endpoints.py` — new `test_blob_lease_over_cap_sentinels_all_null_blob_flaws` test in `TestFlawBlobLeaseEndpoint`; docstring updated to list the new test.

## Decisions Made

- The over-cap branch is a `elif`, syntactically and semantically distinct from the `if not lease_positions:` all-sentinel branch — the two conditions (`empty` vs `over-cap`) are mutually exclusive and each writes a sentinel set derived differently (`sentinel_lines`-derived plies for all-sentinel vs a fresh NULL-blob-flaw-ply query for over-cap).
- Deliberately did NOT reuse `sentinel_lines` for the over-cap sentinel set, per the plan's explicit prohibition — `sentinel_lines` only tracks un-walkable lines, and an over-cap game's problem is the opposite (too many walkable lines), so most of its flaw plies would be missed if `sentinel_lines` were the source.
- Test uses a monkeypatched oversized `lease_positions` return rather than real seeding, per the plan's explicit "prefer real seeding if cheap, else patch the builder" guidance — seeding >1024 real walkable PV nodes would require hundreds of flaws with long PVs, disproportionate to the behavior under test. The NULL-blob-flaw-ply query and the DB write are still exercised against real rows, so the actual code path under test (the router's own query + `_batch_update_flaw_pv_lines` write) runs unmocked.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `ruff format`/`ruff check --fix` reformatted long assert lines in the new test after the initial write (line-wrap only, no semantic change) — reran the targeted tests + full suite after to confirm no regressions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The over-cap sentinel pattern is now live and tested at `flaw_blob_lease`; Part B's atomic-lease endpoint (147-04+) can reuse the same "query NULL-blob flaw plies fresh, sentinel via `_batch_update_flaw_pv_lines`, return 204" shape without re-deriving it.
- The ~17 fattest prod games residue (SEED-073) will stop 500ing and stop looping in the tier-4 lottery once this ships — no backfill script needed, they self-heal on their next lease pick.
- Full backend suite (3079 passed, 18 skipped) green after this plan. `uv run ty check app/ tests/` and `uv run ruff check app/ tests/` both pass with zero errors.

---
*Phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated*
*Completed: 2026-07-01*

## Self-Check: PASSED

All modified files found on disk; both task commit hashes (`05b5e6fd`, `2f8aefe2`) found in git log.
