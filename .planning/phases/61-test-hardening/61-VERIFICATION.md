# Phase 61 — Verification

**Date:** 2026-04-16
**Branch:** `phase-61-test-hardening`
**Worktree:** `/home/aimfeld/Projects/Python/flawchess-tests`

## Success criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `tests/conftest.py` truncates all non-reference tables at session start, keeping `alembic_version` and `openings` intact | VERIFIED | `conftest.py:27-61` — `_TRUNCATE_EXCLUDE = {'alembic_version', 'openings'}` + `_truncate_all_tables` creates a throwaway async engine via `asyncio.run`, runs `SELECT tablename FROM pg_tables WHERE schemaname='public'` and issues `TRUNCATE TABLE ... RESTART IDENTITY CASCADE`. Manually verified: after a pytest run, `openings` retains 3641 rows, `alembic_version` retains 1, all other user-owned tables reset to 0. |
| 2 | Shared module-scoped `seeded_user` fixture in `tests/seed_fixtures.py` | VERIFIED | `seed_fixtures.py` defines `SeededUser` dataclass, `_GAMES_SPEC` (15 games), `EXPECTED` aggregate dict, registers/logins via API, commits portfolio through the patched `async_session_maker`. Registered as a pytest plugin in `conftest.py:21-24`. |
| 3 | `tests/test_aggregation_sanity.py` covers 7 audit gaps | VERIFIED | 12 tests across 6 classes all passing: WDL-black-perspective (4), rolling-window-boundaries (3), filter intersection (1), recency boundary (2), position dedup (1), endgame class transition (1). |
| 4 | `tests/test_material_tally.py` verifies material pure functions | VERIFIED | 10 tests across 3 classes — starting material = 7800 cp, capture reduces count by 100 cp, signed imbalance (+100 white-up-pawn / -500 black-up-rook / 0 starting / 0 both-missing-queen), signature format `KQRRBBNNPPPPPPPP_KQRRBBNNPPPPPPPP`. All passing. |
| 5 | `tests/test_integration_routers.py` hits real routers with exact-integer assertions | VERIFIED | 11 tests across 3 classes: global stats totals + time-control buckets + by-color perspective + platform filters (6 tests), endgame overview distinct total + per-type rook/pawn counts + Phase 59 material-rows invariant (4 tests), openings next-moves 15-game starting-position count (1 test). All passing. |
| 6 | `uv run pytest` remains green; `uv run ty check app/ tests/` is zero-errors; `uv run ruff check .` is zero-errors | VERIFIED | Full suite: **755 passed, 1 skipped** (was 722 before Phase 61 — net +33 tests). `ty`: all checks passed. `ruff check`: all checks passed. `ruff format --check` on all 5 Phase-61 files: clean. |
| 7 | No production code (`app/`) modified | VERIFIED | `git diff main -- app/` is empty. Only `tests/`, `.planning/`, and `.planning/phases/61-test-hardening/` were touched. |

## Test count delta

| File | Tests added | Status |
|------|------------:|--------|
| `tests/test_aggregation_sanity.py` | 12 | all passing |
| `tests/test_material_tally.py` | 10 | all passing |
| `tests/test_integration_routers.py` | 11 | all passing |
| **Total** | **33** | **all passing** |

## Commits

```
cf2101e test(phase-61-03): router integration tests + fixture plugin registration
a71b02f test(phase-61-02): aggregation sanity + material tally tests
2b60de2 test(phase-61-01): truncate flawchess_test at session start + seeded_user fixture
1cbb6c0 plan(phase-61): test suite hardening & DB reset
```

## Notes / follow-ups

- Zero production code (`app/`) changes — this phase purely added test coverage and test infrastructure. No audit-gap turned out to be a real bug; every new assertion passes against current behavior.
- The `seeded_user` fixture is registered once at module scope per consumer (currently just `test_integration_routers.py`). Register+seed cost is ~200 ms once per that module.
- The in-codebase warning about HMAC key length (<32 bytes) already existed and is unrelated to Phase 61.
- `tests/seed_fixtures.py` is intentionally kept as a vanilla test helper module (not under `app/`) so it doesn't ship in the production image.
