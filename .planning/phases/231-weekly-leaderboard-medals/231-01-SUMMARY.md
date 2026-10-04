---
phase: 231-weekly-leaderboard-medals
plan: 01
subsystem: api
tags: [backend, train, leaderboard, medals, alembic, sqlalchemy, trigger]

requires:
  - phase: 230-weekly-train-leaderboards
    provides: week_window, fetch_week_aggregates, _entry_for, _tiered_order, GET /train/leaderboard
provides:
  - train_weekly_finalizations + train_weekly_standings tables with the deletion-erasure trigger (migration e3a8c5f17b20)
  - lazy idempotent finalize_due_weeks (5 min grace, marker-table claim) called from GET /api/train/leaderboard
  - final_standings / medal_for / build_last_week reusing the live board's ranking code
  - wire shape final for the frontend plans: per-board last_week (podium + viewer_final_rank) and per-row medals
affects: [231-02, 231-03, 231-04, 231-05, 231-06]

actuals:
  tokens: 18000  # chars/4 over the realized diff (71,636 chars)
  tasks: 2
  commits: 3
plan_head_before: 7c6fc22d7f3a84789e146e882c47e5c7bb88add5
plan_head_after: 739a4495065dccad7c6a0a14c0652b0709d3cfba

tech-stack:
  added: []
  patterns:
    - "Marker-table claim (INSERT ON CONFLICT DO NOTHING RETURNING) as the finalization lock and memory"
    - "Read-time masking of stored names; eligibility decided once at finalization"
    - "First DB trigger in the repo (BEFORE UPDATE OF user_id) erasing PII on FK SET NULL"

key-files:
  created:
    - alembic/versions/20261004_120000_e3a8c5f17b20_train_weekly_standings.py
    - app/models/train_weekly_standing.py
    - app/repositories/train_medals_repository.py
    - app/services/train_medals.py
    - tests/routers/test_train_medals.py
    - tests/services/test_train_medals.py
  modified:
    - alembic/env.py
    - app/services/train_leaderboard.py
    - app/schemas/train.py
    - app/routers/train.py
    - tests/routers/test_train_leaderboard.py
    - tests/services/test_train_leaderboard.py

key-decisions:
  - "Finalization marker table instead of an advisory lock: the marker PK insert serializes concurrent finalizers and remembers empty weeks"
  - "MEDALS_FINALIZE_GRACE = 5 minutes after the Sunday deadline, so a solve that started before the deadline and committed just after it is not missed by a permanent snapshot"
  - "Router copies user.id / is_guest / leaderboard_hidden into locals before the finalizer, because a rollback expires every instance in the request-cached session"
  - "Podium shown to guests (public data); viewer_final_rank stays None for them"
  - "D-05 zero-value rule: a 0-point or 0% entry keeps its rank, no medal"

patterns-established:
  - "Router-level finalizer helper that rolls back, reports to Sentry with set_context and never re-raises"
  - "Router medal tests own ISO weeks from Monday 2033-01-03 plus k, monkeypatch MEDALS_START_WEEK, and clear their weeks (marker delete cascades the standings) before and after"

requirements-completed: []

coverage:
  - id: D1
    description: "Migration e3a8c5f17b20 creates the standings and marker tables plus the erase-name trigger, reversible, no alembic drift"
    verification:
      - kind: command
        ref: "uv run alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic check"
        status: pass
    human_judgment: false
  - id: D2
    description: "The first GET after a deadline (plus grace) freezes the public Points and Accuracy boards with explicit medals, one marker, repeat writes nothing, and returns last_week with the viewer's own rank"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_medals.py#test_deadline_finalizes_last_week_and_shows_the_podium"
        status: pass
    human_judgment: false
  - id: D3
    description: "Eligibility, Olympic ties (1,1,3 / 1,2,2 / 1,1,1,4), zero-value rule, due weeks and grace boundary are pinned by DB-free tests"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k 'final_standings or medal_for or last_week or tally'; tests/services/test_train_medals.py -k due_weeks"
        status: pass
    human_judgment: false
  - id: D4
    description: "Podium masking (Anonymous for hidden-now except to self, Deleted user after account deletion with the trigger erasing the stored name) and finalization failure isolation"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_medals.py#test_podium_masks_hidden_now_and_deleted_users, #test_finalization_failure_still_serves_the_board"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-10-04
status: complete
---

# Phase 231 Plan 01: Weekly Leaderboard Medals backend snapshot Summary

**Lazy, idempotent weekly medal snapshot: the first leaderboard GET after a Sunday deadline plus 5 minutes freezes each board's public final standings (explicit Olympic medals, ranks from the live board's own code) and returns last week's podium and the viewer's own non-medal rank, with a DB trigger erasing names on account deletion.**

## Performance

- **Duration:** about 14 min (first commit 07:59, last 08:03 local; start time not recorded, estimated from the plan commit at 07:49)
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files:** 6 created, 6 modified

## Accomplishments

- Migration `e3a8c5f17b20` (down_revision `c4e7a91d2b58`): `train_weekly_finalizations` (week_start PK) and `train_weekly_standings` (FK to the marker ON DELETE CASCADE, FK to users ON DELETE SET NULL, board/medal CHECKs, unique week+board+user), plus `trg_train_weekly_standings_erase_name`. Applied to the dev DB; `downgrade -1` / `upgrade head` round trip ran clean; `alembic check` reports no drift.
- `final_standings(kind, aggregates)` filters to public entries, reuses `_entry_for` and `_tiered_order` (no second ranking implementation, `grep` for `_competition_ranks|_tiered_order` defs in `train_medals.py` is 0), drops tentative Accuracy entries, and attaches `medal_for(rank, value)`. Ties fall out of competition ranks.
- `finalize_due_weeks` (`app/services/train_medals.py`): fetches finalized weeks (one SELECT), claims each due week in ascending order via the marker insert, builds standings from `fetch_week_aggregates` for the closed week, inserts with `ON CONFLICT DO NOTHING`. No commit inside; the router commits.
- Router `_finalize_medal_weeks`: commit on success, rollback + `set_context` + `capture_exception` on failure, never re-raises. `get_train_leaderboard` copies the user's fields into locals first (MissingGreenlet guard) and its docstring no longer claims read-only.
- Wire shape: `LeaderboardRow.medals {gold, silver, bronze}` (zero counts here, Plan 02 fills them) and `LeaderboardBoard.last_week {week_start, podium[{medal, name}], viewer_final_rank}`; `test_response_key_set_has_no_user_ids` pins both new keys and the recursive no-id walk still passes.
- Read-time podium naming: "Deleted user" for NULL user_id, "Anonymous" for a user hidden now except to themselves.

## Task Commits

1. **Task 1 (tracer): migration, model, repository, services, schemas, router, tracer test** - `3f1fcdf10` (feat)
2. **Task 2 RED: tests pinning rules, masking, due weeks, grace, previous-week-only, failure isolation** - `45bda6347` (test)
3. **Task 2 GREEN: `_podium_name` read-time masking** - `739a44950` (feat)

## Verification

- `uv run alembic heads`: `e3a8c5f17b20 (head)`; `alembic check`: "No new upgrade operations detected."
- `uv run pytest tests/routers/test_train_medals.py tests/routers/test_train_leaderboard.py tests/services/test_train_leaderboard.py tests/services/test_train_medals.py`: 112 passed. `tests/routers/test_train_medals.py` run twice consecutively, 5 passed both times.
- Acceptance counts: `-k due_weeks` 6 passed; `-k "final_standings or medal_for"` 13 passed (includes the 1,1,3 / 1,2,2 / 1,1,1,4 tie cases); `-k "last_week or podium or viewer_final_rank"` 8 passed; `-k failure` 1 passed.
- Wave sample `uv run pytest tests/services tests/repositories tests/routers -n auto -k "leaderboard or medal"`: 119 passed, 1 skipped.
- `ruff format --check`, `ruff check`, `ty check app/ tests/ scripts/` all clean; `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Spec-less probe fallback skipped: the phase has no requirement IDs to probe (as recorded in the plan).
- Dev-clock note for UAT: shifting the dev clock past a Sunday deadline finalizes that week permanently; cleanup is `DELETE FROM train_weekly_finalizations WHERE week_start >= '<monday>'` on the dev DB (the FK cascades the standings). Never `bin/reset_db.sh`.

## TDD Gate Compliance

Task 1 is `type="tracer"` (not TDD) and shipped as a single feat commit with its tracer test, so the first `feat(231-01)` commit has no preceding `test(231-01)` commit. Task 2 follows the cycle: RED `45bda6347` (the podium masking tests failed on assertion: `test_last_week_podium_renders_a_deleted_user_row_as_deleted_user`, `test_last_week_podium_masks_a_user_hidden_now_for_other_viewers` and the router `test_podium_masks_hidden_now_and_deleted_users`, each returning the stored name instead of "Deleted user" / "Anonymous"), then GREEN `739a44950`. The `gsd_run check tdd-red-evidence` record was not produced (the verb's record format is not documented in the reference); the failing assertions above are the RED evidence. The eligibility, tie, grace and isolation tests in the RED commit pin behavior Task 1 already shipped, so they passed at RED by design. No refactor commit was needed.

## Deviations from Plan

None - plan executed exactly as written. Two small implementation notes (not deviations): `build_last_week` keeps a redundant `if r.medal is not None` in the podium generator purely for type-checker narrowing, and the `due_weeks` "far after start" test was corrected during RED to the arithmetic of the production rule (2027-01-18 is the open week, so only k=6 is missing).

**Total deviations:** 0.

## Auth Gates

None.

## Known Stubs

None. `LeaderboardRow.medals` is intentionally all-zero until Plan 02 Task 3 adds the grouped tally query (documented in the plan and in the code path: `medal_tallies` is unset in `get_weekly_leaderboard`).

## Threat Flags

None beyond the plan's threat model. The one new trust-boundary change (a global write on a GET) is T-231-04, mitigated by the rollback + Sentry isolation helper and covered by `test_finalization_failure_still_serves_the_board`.

## Self-Check: PASSED

All created files exist on disk; commits `3f1fcdf10`, `45bda6347`, `739a44950` exist; `commits: 3` measured from `git rev-list --count 7c6fc22d7..HEAD`.
