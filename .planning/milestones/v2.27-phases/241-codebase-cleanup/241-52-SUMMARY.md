---
phase: 241-codebase-cleanup
plan: 52
subsystem: backend-surface, backend-repositories
tags: [naming, refactor, rename]
requires: ["241-02", "241-03", "241-04", "241-07", "241-08", "241-10", "241-24", "241-34"]
provides:
  - "is_allowed(key), promoted_user, worker_evaluated_plies, cache_targets, _matching_server_graded_move, position_hash"
affects: [app/core/ip_rate_limiter.py, app/routers/auth.py, app/routers/eval_remote.py, app/repositories/train_repository.py, app/repositories/stats_repository.py, frontend/src/lib/trainPhoneGrade.ts, tests/test_eval_worker_endpoints.py]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-52.tsv
    - .planning/phases/241-codebase-cleanup/ledgers/241-52.txt
  modified:
    - app/core/ip_rate_limiter.py
    - app/routers/auth.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py
    - app/repositories/train_repository.py
    - frontend/src/lib/trainPhoneGrade.ts
    - app/repositories/stats_repository.py
decisions:
  - "The `_updated_user` row uses absent_paths `-` because the unused binding in promote_guest_email deliberately keeps its name"
metrics:
  duration: ~25m
  completed: 2026-10-16
status: complete
commits: 6
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 03a9165bc59b036ac3ab3ac1fe80f3ae778f25ee
actuals:
  tokens: 4000
  tasks: 3
  commits: 6
---

# Phase 241 Plan 52: backend-surface and backend-repositories renames Summary

Six INVENTORY §5 renames applied, one `refactor(naming)` commit each, with no behavior change.

## Renames

| # | old → new | Commit | Files |
|---|-----------|--------|-------|
| a | `is_allowed(ip)` → `is_allowed(key)` (+ INV-L341) | a8940aef5 | app/core/ip_rate_limiter.py |
| b | `_updated_user` → `promoted_user` | 622c19a0f | app/routers/auth.py |
| c | `_worker_evaluated_plies` → `worker_evaluated_plies` | 0e377029c | app/routers/eval_remote.py, tests/test_eval_worker_endpoints.py (comment) |
| d | `_cache_targets` → `cache_targets` | 61f91035d | app/routers/eval_remote.py, tests/test_eval_worker_endpoints.py (comment) |
| e | `_override_for_key_move` → `_matching_server_graded_move` | ee6bbd739 | app/repositories/train_repository.py, frontend/src/lib/trainPhoneGrade.ts (JSDoc, same commit) |
| f | `full_hash` (dedup CTE label) → `position_hash` | 03a9165bc | app/repositories/stats_repository.py |

No file outside the plan's `files_modified` needed an edit.

## INV-L341

`INV-L341: APPLIED` is recorded in `ledgers/241-52.txt`, landed in commit a8940aef5 together with the rename. Re-verified first: `feedback.py` and `users.py` call `is_allowed` with a user id and an email, so "keyed by IP" was stale. The module docstring line had already changed since INVENTORY, so the replacement text was applied to the current first line.

## Deviations from Plan

**1. [Rule 3 - Blocking] `_updated_user` absent_paths set to `-`**
- **Found during:** Task 1(b)
- **Issue:** The plan's row used absent_paths `app/routers/auth.py`, but the plan itself requires the genuinely unused `_updated_user` binding in `promote_guest_email` (auth.py:632) to keep its name, so `cleanup.py absent` would always report a hit. `cleanup.py diff` passes with the scoped canon_paths row.
- **Fix:** absent_paths `-` for that row; scope still enforced by `canon_paths` and by `diff`.
- **Files modified:** rename-maps/241-52.tsv
- **Commit:** 622c19a0f

**2. [Environment] Targeted tests run serially instead of `-n 4`**
- With ~12 sibling executors sharing one Postgres, `-n 4` runs failed in DB setup; the same tests pass serially. No code issue.

## Verification

- `ty check app/ tests/ scripts/`, `ruff check`, `ruff format --check`: clean at every step.
- Serial tests green: test_ip_rate_limiter, test_guest_auth, test_guest_google_promotion, test_password_policy_and_login_limit, test_eval_worker_endpoints (109), tests/repositories/test_train_repository.py (177), test_stats_repository, test_stats_repository_phase_entry, test_stats_service_phase_entry (42), source_scan_tests.sh --py (5).
- `npm --prefix frontend run lint` and `run build` pass (baseline also green before any change).
- `cleanup.py absent --map` reports 0 hits; `cleanup.py diff --plan 241-52` over all touched files reports no residue.
- stats_repository.py `full_hash` count 20 → 16 (exactly the four label/access/docstring occurrences; the `game_positions.full_hash` column and every other use unchanged).
- No wire field, route path, SQL column or test assertion changed.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

All six commits found in `git log de0c589be..HEAD`; rename-maps/241-52.tsv and ledgers/241-52.txt exist.
