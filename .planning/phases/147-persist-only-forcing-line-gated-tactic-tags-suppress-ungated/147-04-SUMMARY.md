---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
plan: 04
subsystem: api
tags: [eval-remote, atomic-lease, versioned-endpoint, dos-guard, seed-074]

requires:
  - phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
    plan: 03
    provides: Reusable over-cap sentinel pattern ("never construct an oversized response, sentinel + 204 instead of 500") that this plan's /atomic-lease guard mirrors
provides:
  - New, isolated atomic lease/submit schema pair (AtomicLeaseResponse, AtomicSubmitEval, AtomicBlobNode, AtomicSubmitRequest, AtomicSubmitResponse, MAX_SUBMIT_BLOB_NODES) in app/schemas/eval_remote.py
  - POST /eval/remote/atomic-lease endpoint: claims via claim_eval_job unchanged (tier-1>2>3), returns FEN-per-ply AtomicLeaseResponse, over-cap safe
  - Over-cap sentinel guard on the new lease (positions > MAX_SUBMIT_EVALS -> release job + 204, never 500)
affects: [147-05, 147-06]

tech-stack:
  added: []
  patterns:
    - "New isolated endpoint pair (D-02): a versioned lease/submit contract lives entirely alongside the old pair with its own schemas and DoS caps, letting a mixed fleet (old + upgraded workers) run simultaneously with instant rollback (flip workers back, no server redeploy)"
    - "Lease-side over-cap defense-in-depth: even where a Field(max_length=...) constraint on the response schema was NOT added (unlike FlawBlobLeaseResponse.positions), the endpoint still guards len(positions) > MAX_SUBMIT_EVALS in application code before ever building the response"

key-files:
  created: []
  modified:
    - app/schemas/eval_remote.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "AtomicLeaseResponse.positions has NO Field(max_length=...) constraint (matches the old LeaseResponse.positions exactly, per the plan's 'capped like the old lease' spec) — the over-cap guard is enforced entirely in application code (len() check before constructing the model), not via a Pydantic ValidationError path like FlawBlobLeaseResponse"
  - "The over-cap guard's 'sentinel' action for /atomic-lease is release_job(job_id) (mirroring the existing lichess-eval-game skip already in lease_eval_game), NOT a GameFlaw write — this endpoint selects games needing full-ply evaluation, which have no game_flaws rows yet (flaws are only discoverable after evals exist), so there is nothing analogous to flaw_blob_lease's 'sentinel every NULL-blob flaw ply' to write here"
  - "The over-cap branch is documented as defense-in-depth, not an expected path: MAX_SUBMIT_EVALS=1024 plies (~512 full moves) is essentially unreachable for real chess.com/lichess games, unlike flaw-blob-lease's payload (flaws x PV-line length) which SEED-073 proved 17 real prod games exceed"
  - "worker_schema_version is a required int field on AtomicSubmitRequest (no default) per Q5 (observability/rejection only, never gates correctness) — deferred to 147-05/147-06 where the submit handler is implemented"
  - "AtomicBlobNode mirrors FlawBlobSubmitEval's exact field set (token, best_cp, best_mate, second_cp, second_mate, second_uci) rather than inventing a new shape, keeping the token scheme (D-04a) and None->'' second_uci convention (Pitfall 3) identical across both blob-submitting pairs"

requirements-completed: [SEED-074]

coverage:
  - id: D1
    description: "AtomicLeaseResponse/AtomicSubmitRequest/AtomicSubmitEval/AtomicBlobNode/AtomicSubmitResponse schemas exist with two independently-capped submit lists (evals via MAX_SUBMIT_EVALS, blob_nodes via new MAX_SUBMIT_BLOB_NODES=1024) and a worker_schema_version field"
    requirement: "SEED-074"
    verification:
      - kind: other
        ref: "uv run ty check app/ (zero errors)"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /eval/remote/atomic-lease claims via claim_eval_job unchanged, returns a well-formed AtomicLeaseResponse for an eligible game (FEN-per-ply positions, exactly one is_terminal=True), is operator-token gated, and 204s on an empty queue"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_returns_positions"
        status: pass
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_no_pending_games"
        status: pass
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_requires_operator_token"
        status: pass
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_wrong_operator_token"
        status: pass
    human_judgment: false
  - id: D3
    description: "A fat game whose lease payload exceeds MAX_SUBMIT_EVALS positions hits the over-cap sentinel (204, never 500); the held job is released rather than left stuck 'leased'"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_over_cap_releases_job_and_returns_204"
        status: pass
    human_judgment: false
  - id: D4
    description: "Existing endpoints (/lease, /submit, /flaw-blob-lease, /flaw-blob-submit, /entry-lease, /entry-submit) are untouched"
    requirement: "SEED-074"
    verification:
      - kind: other
        ref: "uv run pytest tests/test_eval_worker_endpoints.py -n auto (75 passed, includes all pre-existing endpoint tests) + uv run pytest -n auto (3084 passed, 18 skipped, full backend suite)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-01
status: complete
---

# Phase 147 Plan 04: Atomic lease/submit schema pair + /atomic-lease endpoint Summary

**A new, isolated schema pair (`AtomicLeaseResponse`/`AtomicSubmitRequest`/`AtomicBlobNode`/etc., with independently-capped `evals`/`blob_nodes` lists) and a new `POST /eval/remote/atomic-lease` endpoint that claims games via the unchanged `claim_eval_job` tier-1>2>3 selector, returns FEN-per-ply positions, and never 500s on an over-cap fat game — laying the lease-side groundwork for Part B's atomic eval+blob worker pipeline (submit side lands in 147-05).**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed
- **Files modified:** 3 (app/schemas/eval_remote.py, app/routers/eval_remote.py, tests/test_eval_worker_endpoints.py)

## Accomplishments

- New `AtomicLeaseResponse` (game_id, user_id, is_lichess_eval_game, positions, leased_at, job_id), `AtomicSubmitEval` (mirrors the old `SubmitEval` full-ply shape), `AtomicBlobNode` (mirrors `FlawBlobSubmitEval`'s token-keyed MultiPV-2 node shape), `AtomicSubmitRequest` (game_id, sf_version, `worker_schema_version: int`, two independently-capped lists `evals`/`blob_nodes`, job_id), and `AtomicSubmitResponse` (game_id, flaws_written, blobs_written) added to `app/schemas/eval_remote.py`. New `MAX_SUBMIT_BLOB_NODES: int = 1024` constant, explicitly distinct from `MAX_SUBMIT_EVALS` per D-02 (no shared/raised cap).
- New `POST /eval/remote/atomic-lease` route in `app/routers/eval_remote.py`, operator-token gated, claiming via `claim_eval_job` completely unchanged (same tier-1>2>3 priority, SKIP LOCKED, stale-lease sweep). Builds FEN-per-ply positions via the existing `_build_lease_positions` helper — no PGN or Game metadata added to the payload, per the plan's Q4 narrower-hint design decision. Mirrors the old `/lease` handler's lichess-eval-game skip (release job + 204) and no-game/no-row 204 paths.
- Over-cap sentinel: when `len(positions) > MAX_SUBMIT_EVALS`, the endpoint releases the held job (if any) and returns 204 instead of ever constructing the response — reusing the 147-03/SEED-073 "never build an oversized payload" pattern. Documented as defense-in-depth rather than an expected path: unlike flaw-blob-lease (17 real prod games proven over cap by SEED-073's own quantification), a real chess.com/lichess game essentially never reaches 1024 plies.
- New `TestAtomicLeaseEndpoint` class (5 tests): missing-token 403, wrong-token 401, no-pending-games 204, a well-formed 200 response (positions non-empty, exactly one `is_terminal=True`, every position has a non-empty FEN), and the over-cap sentinel path (oversized `_build_lease_positions` monkeypatch, asserts 204 + `release_job` called with the held job_id).

## Task Commits

Each task was committed atomically:

1. **Task 1: Define the new atomic lease/submit schema pair** — `b4536332` (feat)
2. **Task 2: Implement the /atomic-lease endpoint with the over-cap sentinel** — `06755817` (feat)

**Plan metadata:** pending (docs: complete plan — committed after this SUMMARY)

## Files Created/Modified

- `app/schemas/eval_remote.py` — new atomic lease/submit schema set (`AtomicLeaseResponse`, `AtomicSubmitEval`, `AtomicBlobNode`, `AtomicSubmitRequest`, `AtomicSubmitResponse`) + `MAX_SUBMIT_BLOB_NODES` constant.
- `app/routers/eval_remote.py` — new `POST /atomic-lease` handler; module docstring updated to document the new endpoint and its 204 causes.
- `tests/test_eval_worker_endpoints.py` — new `TestAtomicLeaseEndpoint` class (5 tests).

## Decisions Made

- `AtomicLeaseResponse.positions` has no `Field(max_length=...)` constraint, exactly matching the old `LeaseResponse.positions` (the plan's spec: "capped like the old lease"). The over-cap protection therefore lives entirely in application code — an explicit `len(positions) > MAX_SUBMIT_EVALS` check before the model is ever constructed — rather than relying on a Pydantic `ValidationError` being caught the way `FlawBlobLeaseResponse`'s `Field(max_length=...)` constraint originally exposed the SEED-073 bug.
- The plan's task text ("sentinel the game's NULL-blob flaws + 204") describes `flaw_blob_lease`'s over-cap mechanism, which writes `[]` to `game_flaws` rows to durably clear the re-pick predicate. That mechanism does not translate structurally to `/atomic-lease`: this endpoint selects games that still need full-ply evaluation, which by definition have no `game_flaws` rows yet (flaws are only discoverable after evals exist and diffs are computed). The closest existing analog already in this same handler family is the lichess-eval-game skip (`release_job` + 204), which was applied here instead. This is flagged explicitly since it's a deliberate interpretation of an ambiguous plan instruction, not a literal implementation of "sentinel NULL-blob flaws."
- The over-cap branch's practical reachability is near-zero for the corpus this pipeline actually serves (chess.com/lichess games), unlike the flaw-blob-lease over-cap case which SEED-073 quantified against 17 real prod games. The guard exists as defense-in-depth consistent with the plan's explicit "never 500s" requirement, and is exercised by a monkeypatch-based test (real seeding of a >1024-ply game is impractical) mirroring 147-03's own test methodology.
- `AtomicBlobNode` and `AtomicSubmitEval` mirror `FlawBlobSubmitEval`/`SubmitEval` field-for-field rather than introducing new naming, keeping the token scheme (`{flaw_ply}:{line}:{node_k}`, D-04a) and `second_uci: None -> ""` wire convention (Pitfall 3) identical across both blob-submitting endpoint pairs for 147-05/147-06 to build on without re-deriving.

## Deviations from Plan

None — plan executed as written, with the interpretation of the ambiguous over-cap "sentinel" language documented above under Decisions Made (not a Rule 1-4 deviation; the plan's own artifacts/acceptance criteria did not mandate a specific sentinel mechanism, only that the endpoint "never 500s").

## Issues Encountered

None. `ruff format` reformatted one long assert-message line in the new test file (line-wrap only, no semantic change) after the initial write; reran targeted tests + full suite after to confirm no regressions.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The new versioned schema pair and `/atomic-lease` endpoint exist, select games with the identical existing queue logic, are operator-token gated, and are fat-game safe — ready for 147-05's `/atomic-submit` handler (worker submits full-ply evals + MultiPV-2 blob nodes together, server runs its own authoritative `classify_game_flaws` and writes flaws + gated tags + completion markers in one transaction).
- `AtomicSubmitRequest`/`AtomicBlobNode`/`AtomicSubmitResponse` schemas are already defined (Task 1 of this plan) so 147-05 can implement the submit handler directly against them without further schema work.
- Full backend suite (3084 passed, 18 skipped) green after this plan. `uv run ty check app/ tests/` and `uv run ruff check app/ tests/` both pass with zero errors.

---
*Phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated*
*Completed: 2026-07-01*

## Self-Check: PASSED

All modified files found on disk; all task/summary commit hashes (`b4536332`, `06755817`, `0e5793cf`) found in git log.
