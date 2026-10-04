---
phase: 231-weekly-leaderboard-medals
plan: 02
subsystem: api
tags: [backend, train, leaderboard, medals, api, idor, tally]

requires:
  - phase: 231-weekly-leaderboard-medals
    provides: train_weekly_standings snapshot, finalize_due_weeks, _finalize_medal_weeks, MedalTally/ZERO_TALLY, build_board medal_tallies hook
provides:
  - GET /api/train/medals/unclaimed (lazy finalize, caller-scoped, newest week first, Points before Accuracy, shared flag)
  - POST /api/train/medals/claim (204, shown keys only, caller-scoped, idempotent, validated 1..100 keys)
  - lifetime per-board medal tally on every visible row of GET /api/train/leaderboard from one grouped COUNT
affects: [231-03, 231-04, 231-05, 231-06]

actuals:
  tokens: 13500  # chars/4 over the realized diff (54,296 chars)
  tasks: 3
  commits: 4  # MEASURED: git rev-list --count a566a84e3..HEAD before the SUMMARY commit
plan_head_before: a566a84e32460af4378f7bff77d06a302c035244
plan_head_after: bba48fcc79a89c9432325aa50ff0451a5feeab5f

tech-stack:
  added: []
  patterns:
    - "Claim by natural key: UPDATE scoped by user_id AND posted (week_start, board) pairs, celebrated_at IS NULL guard makes replays no-ops"
    - "_rank_board shared by build_board and visible_keys so the tally lookup cannot drift from the rows shown"

key-files:
  created:
    - tests/repositories/test_train_medals_repository.py
  modified:
    - app/schemas/train.py
    - app/repositories/train_medals_repository.py
    - app/services/train_medals.py
    - app/services/train_leaderboard.py
    - app/routers/train.py
    - tests/routers/test_train_medals.py
    - tests/services/test_train_leaderboard.py

key-decisions:
  - "Unclaimed and claim endpoints take no user parameter and return no ids; a medal is addressed by (week_start, board)"
  - "fold_medal_tallies always returns both board keys (empty dict when a board has no tallies), so consumers never branch on a missing key"
  - "visible_keys is computed for both boards and unioned, so the tally is one grouped query per request, skipped when no row is visible"

patterns-established:
  - "Router medal tests keep the k-table convention: this plan owns weeks k 20-32 (28, 29 unused); repository tests own ids 93720-93739 and k 20-28 from Monday 2034-01-02"

requirements-completed: []

coverage:
  - id: D1
    description: "A medallist lists unclaimed medals (the read finalizes the closed week) and claims exactly the shown keys; the claim persists in the row and affects only the caller"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_medals.py#test_unclaimed_then_claim_round_trip"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-11 order (newest week first, Points before Accuracy), shared flag, D-04 hidden-now viewer, D-10 guest no-op, IDOR scoping, idempotent replay, 422 validation and 401 without token"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_medals.py#test_unclaimed_order_newest_week_first_points_before_accuracy, #test_claim_is_scoped_to_the_caller_and_idempotent, #test_claim_validation_rejects_bad_bodies"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_medals_repository.py -k 'unclaimed or celebrated'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every visible live-board row carries its owner's lifetime medals for that board from one grouped COUNT, surviving an opt-out round trip, no ids on the wire"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_medals.py#test_medal_tally_counts_lifetime_medals_per_board"
        status: pass
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k 'tally or visible_keys'"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_medals_repository.py#test_tally_rows_group_by_board_user_and_medal"
        status: pass
    human_judgment: false
  - id: D4
    description: "No Umami or analytics event for claims (the celebrated_at row is the record)"
    verification: []
    human_judgment: true
    rationale: "Absence of an event is a code-review fact; the claim handler contains no analytics call and the backend has no Umami client"

duration: ~25min
completed: 2026-10-04
status: complete
---

# Phase 231 Plan 02: Medal claim API and live-board tally Summary

**Caller-scoped unclaimed-medals read and shown-keys-only claim POST (idempotent, validated, guest-safe), plus a lifetime per-board medal tally on every visible live-board row from one grouped COUNT.**

## Performance

- **Duration:** about 25 min (start time not recorded; estimated from the plan-01 close-out commit)
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files:** 1 created, 7 modified (production: schemas, repository, two services, router)

## Accomplishments

- `GET /api/train/medals/unclaimed` runs the lazy finalizer first (same `_finalize_medal_weeks`, commit or rollback + Sentry), then returns the caller's `celebrated_at IS NULL` medal rows, newest week first, Points before Accuracy (explicit CASE, alphabetical would invert it), with the final value and a `shared` flag from an aliased EXISTS on the same week, board and medal. Capped at `MEDAL_CLAIM_MAX_ITEMS` (100), the same cap as the claim body.
- `POST /api/train/medals/claim` (204): one UPDATE matching `user_id = caller AND celebrated_at IS NULL AND medal IS NOT NULL AND (week_start, board) IN keys`. Foreign or unknown keys match nothing, a repeat keeps the first stamp, a guest has no rows. `now_utc` comes from `NowUtc` (dev_now_utc). Body is `1..100` keys with date and `Literal` board, so bad input is a 422 before SQL.
- Lifetime tally: `_rank_board` extracted from `build_board` (behavior unchanged, all Phase 230 tests untouched and green); `visible_keys` reuses it, so the grouped `fetch_medal_tallies` runs for exactly the user ids behind the rows shown on either board (including the viewer's own hidden or guest key, never another hidden or guest user's). `fold_medal_tallies` feeds `build_leaderboard(medal_tallies=...)`. Ids stay inside the service; `dataclasses.fields` test now covers BoardRow, PodiumEntry, LastWeek and MedalTally.

## Task Commits

1. **Task 1 (tracer): schemas, repository, service, both endpoints, round-trip test** - `c98b155c3` (feat)
2. **Task 2: claim rules pinned (order, shared, IDOR, replay, D-04, D-10, validation, limit)** - `f78b47021` (test)
3. **Task 3 RED: tally tests plus NotImplementedError stubs** - `dea0d2c3d` (test)
4. **Task 3 GREEN: _rank_board, visible_keys, fold_medal_tallies, fetch_medal_tallies, wiring** - `bba48fcc7` (feat)

## Verification

- Plan-level set (`test_train_medals` router, `test_train_leaderboard` router, services leaderboard + medals, repository medals + leaderboard): 139 passed.
- Wave sample `uv run pytest tests/services tests/repositories tests/routers -n auto -k "leaderboard or medal"`: 139 passed, 1 skipped.
- `ruff format`, `ruff check . --fix`, `ty check app/ tests/ scripts/` (zero errors), `check_function_size.py app/ --fail-over-depth 4` (no breaches) all clean.
- Mutation proof (each reverted and confirmed failing, then restored): dropping the user scope in `mark_celebrated` fails 3 tests; dropping `celebrated_at IS NULL` fails 2; alphabetical board order fails 2; `shared` ignoring the medal fails 3; `visible_keys` returning every key fails 5; tally wiring dropped fails 1; tally ignoring the board fails 1.
- Acceptance greps: both routes present once, no `/train/` prefix in decorators, `now_utc: NowUtc` on both handlers, no `datetime.now`/`utcnow` in code (one match is the pre-existing module docstring in `app/routers/train.py`), one `fetch_medal_tallies(` call, one `def visible_keys`, one `def _rank_board`.
- Spec-less probe fallback skipped: the phase has no requirement IDs to probe (as recorded in Plan 01).

## TDD Gate Compliance

Task 1 is `type="tracer"` (single feat commit with its test). Task 2 is `tdd="true"` but its behavior was already implemented by the Task 1 tracer, so no RED commit exists: the tests passed on first run, and I proved they bite by reverting four guards (see Verification). Task 3 follows the cycle: RED `dea0d2c3d` (router tally test failed on the intended assertion, gold 0 != 2 and silver 0 != 2; service and repository tests failed on `NotImplementedError` from the stubs that exist only so the new symbols import), GREEN `bba48fcc7`. No refactor commit. The `gsd_run check tdd-red-evidence` record was not produced (record format is not documented in the reference), same as Plan 01.

## Deviations from Plan

None - plan executed exactly as written. Notes (not deviations): `fold_medal_tallies` always returns both board keys, which the plan left open; the RED commit carries two stub functions and a dataclass in production files, which the plan implies by listing the new symbols as exports.

**Total deviations:** 0.

## Auth Gates

None.

## Known Stubs

None. The `NotImplementedError` stubs from the RED commit are replaced in the GREEN commit.

## Threat Flags

None beyond the plan's threat model (T-231-09 to T-231-13 are mitigated and test-pinned; T-231-SC accepted, no packages installed).

## Self-Check: PASSED

Created and modified files exist; commits `c98b155c3`, `f78b47021`, `dea0d2c3d`, `bba48fcc7` exist; `commits: 4` measured from `git rev-list --count a566a84e3..HEAD`. STATE.md and ROADMAP.md untouched (the orchestrator owns them this wave).
