---
phase: 141-jsonb-schema-gate-logic
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, jsonb, postgresql, game_flaws, deferred, pv_lines]

# Dependency graph
requires:
  - phase: 140-full-game-analysis-board
    provides: "stable game_flaws schema with tactic columns (allowed/missed_tactic_*)"
provides:
  - "allowed_pv_lines and missed_pv_lines JSONB columns on game_flaws (nullable, deferred)"
  - "Alembic migration 0b6ac7a4b59a chaining off head c4d4588ed2b8"
  - "TestDeferredBlobLeak regression class in tests/test_game_flaws_model.py"
affects:
  - "141-02 (gate logic reads these columns via undefer())"
  - "142 (engine pass writes blob data into these columns)"
  - "143 (offline re-tagger uses undefer() opt-in path verified here)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "deferred=True on mapped_column() as structural leak guard (first codebase usage)"
    - "sa_inspect(obj).unloaded assertion for deferred-column regression tests"
    - "undefer() opt-in pattern for Phase 143 explicit blob loading"

key-files:
  created:
    - "alembic/versions/20260629_185459_0b6ac7a4b59a_add_pv_lines_blobs_to_game_flaws.py"
  modified:
    - "app/models/game_flaw.py"
    - "tests/test_game_flaws_model.py"

key-decisions:
  - "deferred=True on both JSONB columns is the D-02 structural leak guard — zero stats scan regression by design"
  - "list[Any] | None type for blob columns (D-05 blob is a list of per-node dicts, not a single dict)"
  - "No MutableList wrapper — write-once blobs per D-06 (mirrors llm_log.response_json pattern)"
  - "D-02b: no production repository rewrites — deferred=True alone satisfies STORE-02; 5-site audit confirms"

patterns-established:
  - "deferred=True: new mapper pattern in app/ — apply deliberately on any write-once JSONB blob that must not load on stats scans"
  - "sa_inspect(obj).unloaded: the correct way to assert deferred columns without triggering MissingGreenlet"

requirements-completed: [STORE-01, STORE-02]

coverage:
  - id: D1
    description: "allowed_pv_lines and missed_pv_lines JSONB columns exist on game_flaws via Alembic migration"
    requirement: "STORE-01"
    verification:
      - kind: integration
        ref: "uv run alembic upgrade head && uv run alembic check (no drift)"
        status: pass
      - kind: integration
        ref: "uv run alembic downgrade -1 && uv run alembic upgrade head (round-trip clean)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Deferred blob columns never load on existing stats-style select(GameFlaw) scans (STORE-02)"
    requirement: "STORE-02"
    verification:
      - kind: unit
        ref: "tests/test_game_flaws_model.py::TestDeferredBlobLeak::test_deferred_columns_absent_from_default_select_sql"
        status: pass
      - kind: integration
        ref: "tests/test_game_flaws_model.py::TestDeferredBlobLeak::test_blob_attrs_unloaded_after_stats_select"
        status: pass
    human_judgment: false
  - id: D3
    description: "undefer() round-trip loads both blob attrs (Phase 143 opt-in path works)"
    verification:
      - kind: integration
        ref: "tests/test_game_flaws_model.py::TestDeferredBlobLeak::test_undefer_round_trip_loads_both_blob_attrs"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-06-29
status: complete
---

# Phase 141 Plan 01: JSONB Schema + Deferred Leak Guard Summary

**Nullable JSONB PV-line blobs added to game_flaws with deferred=True structural leak guard, Alembic migration, and regression tests proving zero stats-scan regression and Phase 143 undefer() opt-in path**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-29T18:54:00Z
- **Completed:** 2026-06-29T18:57:18Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `allowed_pv_lines` and `missed_pv_lines` as `Mapped[list[Any] | None]` JSONB columns on `GameFlaw` with `deferred=True` (first deferred mapper usage in the codebase, per D-02)
- Generated and applied Alembic migration `0b6ac7a4b59a` (nullable JSONB adds, no table rewrite, safe on populated game_flaws); downgrade/upgrade round-trip verified clean
- Added `TestDeferredBlobLeak` class with 3 regression tests: compiled-SQL check, unloaded-attribute proof, and undefer() round-trip; all 7 tests in the file pass

## 5-Site Audit: select(GameFlaw) in library_repository.py

Per D-02a, all 5 sites confirmed not to implicitly access the new blob attributes. `deferred=True` makes them structurally safe (an implicit async access would raise `MissingGreenlet`); this audit confirms no site trips it today.

| Line | Function / Context | Assessment |
|------|--------------------|------------|
| 737 | `exists(select(GameFlaw.ply)...)` — correlated EXISTS for Games-tab filter | Column-projected (selects only `ply`); entity never loaded. **Safe.** |
| 1017 | `select(GameFlaw, Game, PositionAt, PositionBefore, PositionTwoBefore)` — `query_flaws` / `_build_flaw_item` | Full entity loaded; `_build_flaw_item` reads only `severity/tempo/phase/is_*/fen/*_tactic_*`. No blob access. **Safe.** |
| 1118 | `select(GameFlaw)` in `fetch_page_game_flaws` — game-card chip builder | Rows appended to dict keyed by `game_id`; callers read `severity/is_*/tactic_*` for chip/count building only. No blob access. **Safe.** |
| 1151 | `select(GameFlaw)` in `fetch_page_game_flaws_both_colors` — eval-chart tactic tooltip | Same shape as 1118; ungated for both movers but reads identical non-blob fields. No blob access. **Safe.** |
| 2255 | `select(GameFlaw).where(user/game/ply)` — tactic-lines single-flaw detail | Reads `flaw.fen`, `flaw.{missed,allowed}_tactic_{motif,confidence,depth}` only. The most likely Phase 143 `undefer()` opt-in site — but in Plan 01 no blob access occurs. **Safe.** |

## Task Commits

Each task was committed atomically:

1. **Task 1: Add two deferred JSONB columns to GameFlaw** - `f3265757` (feat)
2. **Task 2: Generate the Alembic migration for the two columns** - `fc78e6fb` (feat)
3. **Task 3: Audit the 5 select(GameFlaw) sites and add the deferred-leak regression test** - `edcd6853` (test)

## Files Created/Modified

- `app/models/game_flaw.py` — two new `Mapped[list[Any] | None]` JSONB columns with `deferred=True`; added `from typing import Any` and `from sqlalchemy.dialects.postgresql import JSONB`
- `alembic/versions/20260629_185459_0b6ac7a4b59a_add_pv_lines_blobs_to_game_flaws.py` — nullable add_column migration; `down_revision = 'c4d4588ed2b8'`
- `tests/test_game_flaws_model.py` — `TestDeferredBlobLeak` class (3 regression tests); added `sa_inspect` and `undefer` imports

## Decisions Made

- `deferred=True` is the sole STORE-02 mechanism; no production repository rewrites needed (D-02b) — the 5-site audit + `TestDeferredBlobLeak` prove the guard holds
- Used `list[Any] | None` (not `dict | None`) because D-05 blob is a list of per-node dicts matching the JSONB array structure the Phase 142 writer will produce
- Verified `deferred` is a kwarg on `mapped_column()` in SQLAlchemy 2.x (no separate import); the existing `deferred()` function approach is not needed

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 01 complete: storage substrate ready for Phase 141 Plan 02 (gate logic)
- The two JSONB columns are nullable with no writer yet; Phase 142 engine pass will write the blobs; Phase 143 re-tagger reads them via `undefer()`
- `alembic check` confirms no model/DB drift; all tests green

---
*Phase: 141-jsonb-schema-gate-logic*
*Completed: 2026-06-29*
