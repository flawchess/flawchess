---
phase: 178-lichess-compatible-accuracy-acpl-computed-columns
plan: 04
subsystem: database
tags: [chess, stockfish, lichess, accuracy, acpl, backfill, validation, python]

# Dependency graph
requires:
  - phase: 178-01
    provides: "Migration adding *_imported columns, canonical white_accuracy/black_accuracy/white_acpl/black_acpl NULLed and repurposed for the uniform computed formula"
  - phase: 178-02
    provides: "app/services/accuracy_acpl.py — compute_game_accuracy_acpl(positions) shared compute path"
provides:
  - "scripts/backfill_accuracy_acpl.py — streaming (server-side cursor, no N+1), batch-committed, --db-targeted, resumable historical fill calling the shared Plan 02 compute path"
  - "scripts/validate_accuracy_acpl.py — read-mostly computed-vs-*_imported comparison script (PRIMARY ACPL, SECONDARY accuracy, DIVERGENT-BY-DESIGN chess.com) with a summary table"
  - "tests/services/test_backfill_accuracy_acpl.py — dev-DB test proving the backfill fills canonical columns for a complete game and leaves a holed game NULL"
  - "Empirical proof (dev DB, full backfill run): computed ACPL tracks lichess's own *_acpl_imported to mean delta 0.13 (n=9120)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backfill scripts split scaffolding (argparse/--db/session bootstrap, cloned from backfill_full_evals.py) from read path (server-side cursor stream + itertools.groupby, cloned from backfill_best_move_pv.py) — the read-path pattern applies whenever a backfill must join game_positions to games at prod scale without an N+1 per-game query"
    - "Read-mostly validation/report scripts (no --dry-run needed, always exit 0) for comparing a newly-computed column against a preserved *_imported baseline"

key-files:
  created:
    - scripts/backfill_accuracy_acpl.py
    - scripts/validate_accuracy_acpl.py
    - tests/services/test_backfill_accuracy_acpl.py
  modified: []

key-decisions:
  - "--dry-run still streams and computes (cheap, pure Python, no engine calls) and only skips the actual UPDATE — gives a real processed/filled/skipped-none summary instead of a bare COUNT(*), since compute cost here is negligible unlike the engine-bound backfill_best_move_pv.py precedent it borrows scaffolding from."
  - "A compute result of None (interior hole) is NOT written as an explicit NULL UPDATE — the candidate query is already gated on white_accuracy IS NULL, so the row is already NULL; skipping the write avoids a no-op UPDATE and keeps the per-batch write session lean."
  - "--limit caps streamed POSITION rows (not games), mirroring backfill_best_move_pv.py's convention; documented that a limit landing mid-game is expected to trip that one game's Complete-Sequence Gate (skipped_none) as a harmless smoke-test artifact — confirmed empirically (see Issues Encountered)."
  - "Validation script's delta-stats are computed in Python (not SQL percentile_cont) — row counts are in the thousands-per-signal range (not the ~718k backfill scale), so a plain fetch + Python percentile is simpler and fast enough for a manual-inspection tool."

patterns-established:
  - "Coarse-SQL-candidate-filter + authoritative-Python-gate backfills: the candidate SELECT over-includes (white_blunders IS NOT NULL catches chess.com games whose move-quality counts came from chess.com's own game review, not our engine — see Issues Encountered), and the shared compute's own Complete-Sequence Gate is the sole authority on whether a game's result is trustworthy. This is now empirically confirmed, not just documented."

requirements-completed: []

coverage:
  - id: D1
    description: "Backfill streams game_positions ⋈ games via a single server-side cursor (session.stream + itertools.groupby), no per-game N+1 SELECT, gated on white_blunders IS NOT NULL AND white_accuracy IS NULL, calling the exact Plan 02 compute_game_accuracy_acpl per game (single-path guarantee)"
    verification:
      - kind: unit
        ref: "tests/services/test_backfill_accuracy_acpl.py::TestBackfillFillsCompleteGameAndHonorsHoleGate::test_run_backfill"
        status: pass
      - kind: manual_procedural
        ref: "uv run python scripts/backfill_accuracy_acpl.py --db dev (full dev-DB run: 14331 games processed, 11495 filled, 2836 skipped_none)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A compute None result (interior eval hole, or 0-move game) leaves a candidate game's four canonical columns NULL — the backfill never writes a partial/incorrect result"
    verification:
      - kind: unit
        ref: "tests/services/test_backfill_accuracy_acpl.py::TestBackfillFillsCompleteGameAndHonorsHoleGate::test_run_backfill (holed_game assertion)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Validation script reports PRIMARY (computed ACPL vs lichess *_acpl_imported), SECONDARY (computed accuracy vs lichess-provenance *_accuracy_imported), and DIVERGENT-BY-DESIGN (chess.com *_accuracy_imported, reported separately, never a failure); parses and passes ty check; always exits 0"
    verification:
      - kind: manual_procedural
        ref: "uv run python -c \"import ast; ast.parse(open('scripts/validate_accuracy_acpl.py').read())\" && uv run ty check app/"
        status: pass
      - kind: manual_procedural
        ref: "uv run python scripts/validate_accuracy_acpl.py --db dev (PRIMARY n=9120 mean=0.13/median=0.00/p95=1.00; SECONDARY n=9120 mean=0.47/median=0.26; DIVERGENT n=9634 mean=11.07)"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-18
status: complete
---

# Phase 178 Plan 04: Historical Backfill + Correctness Validation Summary

**`scripts/backfill_accuracy_acpl.py` (streaming, no-N+1, --db-targeted) and `scripts/validate_accuracy_acpl.py` fill and empirically confirm lichess-compatible accuracy/ACPL for the existing analyzed-games corpus, verified end-to-end on dev: computed ACPL matches lichess's own `*_acpl_imported` to a mean delta of 0.13 (n=9120, 14331 games processed).**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-18T09:13:45Z (STATE.md handoff from 178-03)
- **Completed:** 2026-07-18T09:25:35Z
- **Tasks:** 3
- **Files modified:** 3 (all created)

## Accomplishments
- `scripts/backfill_accuracy_acpl.py`: a single server-side-cursor stream (`session.stream` + `itertools.groupby`, no N+1) over `game_positions JOIN games`, ordered by `(game_id, ply)` so every game's rows are contiguous, gated by `Game.white_blunders.isnot(None)` (coarse "is_analyzed" candidate filter) plus `Game.white_accuracy.is_(None)` (resumability). Calls the exact Plan 02 `compute_game_accuracy_acpl` per game — zero re-implemented formula logic — and batch-commits `UPDATE games SET white_accuracy=..., ...` per ~100-game batch on a separate write session. `--db {dev,benchmark,prod}` required, `--user-id` optional (default all users), `--dry-run`/`--limit` supported.
- `tests/services/test_backfill_accuracy_acpl.py`: seeds one complete (hole-free) analyzed game and one game with an interior eval hole via an injected `session_maker` (no real engine), invokes `run_backfill`, and asserts the complete game's four columns land the exact pinned values (`white_acpl=2`/`black_acpl=0`, matching the existing `test_accuracy_acpl.py` checkmating-final-move fixture — proving write keying, not just "some non-NULL value") while the holed game's columns stay NULL.
- `scripts/validate_accuracy_acpl.py`: a read-mostly comparison reusing the `--db` scaffolding. Reports PRIMARY (computed ACPL vs lichess `*_acpl_imported`), SECONDARY (computed accuracy vs lichess-provenance `*_accuracy_imported`, gated on `lichess_evals_at IS NOT NULL`), and DIVERGENT-BY-DESIGN (chess.com `*_accuracy_imported`, its own different formula — reported separately, never a failure). Prints mean/median/p95 absolute delta and up to 20 outlier `(game_id, color, delta)` rows for manual triage. Always exits 0 (manual-inspection tool, not a gate).
- **Empirical end-to-end proof on dev DB**: ran the full (unlimited) backfill — 14331 candidate games processed, 11495 filled, 2836 left NULL (holed) — then ran the validation script: PRIMARY ACPL delta mean=0.13/median=0.00/p95=1.00 (n=9120, 99 outliers >2), SECONDARY accuracy delta mean=0.47/median=0.26 (n=9120, 178 outliers >3), DIVERGENT chess.com accuracy delta mean=11.07 (n=9634, 7413 exceeding tolerance — the expected large systematic offset from a different formula). This confirms the whole Phase 178 pipeline (migration + compute + live hook + backfill + validation) is correct on real data, not just unit fixtures.

## Task Commits

Each task was committed atomically:

1. **Task 1: Backfill script — streaming read path, compute+write directly via the shared path** - `e8a78e94` (feat)
2. **Task 2: Backfill dev-DB test (fills columns; honors hole gate)** - `3a8c9f18` (test)
3. **Task 3: Validation script — computed vs *_imported comparison** - `cb7b88c1` (feat)

## Files Created/Modified
- `scripts/backfill_accuracy_acpl.py` - Streaming, batch-committed, `--db`-targeted, resumable backfill calling the shared compute path.
- `scripts/validate_accuracy_acpl.py` - Read-mostly computed-vs-`*_imported` comparison (PRIMARY/SECONDARY/DIVERGENT-BY-DESIGN).
- `tests/services/test_backfill_accuracy_acpl.py` - Dev-DB test: complete game filled, holed game stays NULL.

## Decisions Made
- **`--dry-run` still streams and computes**, only skipping the write — gives a real `processed`/`filled`/`skipped_none` summary rather than a bare candidate count, since the compute is pure Python (no engine calls, unlike `backfill_best_move_pv.py`'s dry-run-is-COUNT-only precedent which exists specifically to avoid starting an engine pool).
- **A `None` compute result is not written as an explicit NULL UPDATE** — the candidate query is already gated on `white_accuracy IS NULL`, so the column is already NULL; skipping the write keeps each batch's write session lean and avoids a no-op statement per holed game.
- **`--limit` caps streamed position rows, not games** (mirrors `backfill_best_move_pv.py`), documented as expected to trip the Complete-Sequence Gate for a game whose rows straddle the limit boundary — confirmed harmless in the smoke tests below.
- **Validation delta stats computed in Python**, not SQL `percentile_cont` — the per-signal row counts (thousands, not the ~718k backfill scale) make a plain fetch-then-`statistics` pass simpler and fast enough for a manual-inspection report.

## Deviations from Plan

None — plan executed exactly as written. No architectural changes, no scope creep.

## Issues Encountered

**Real-data finding, not a bug:** during the full dev-DB backfill run, `skipped_none` for user 2's earliest games was much higher than the RESEARCH.md-cited ~0.5% (222 of 279 games on a `--limit 20000` smoke run). Investigation traced this to older chess.com games whose `white_blunders`/`black_blunders`/etc. oracle counts were populated from chess.com's own game-review data at import time (a documented v1.5 feature, "Engine analysis data import ... from chess.com/lichess") rather than our full-ply Stockfish drain — these games have `full_evals_completed_at IS NULL` and **zero** `game_positions.eval_cp`/`eval_mate` values at any ply, so the compute's Complete-Sequence Gate correctly returns `None` for all of them. This is the coarse-SQL-candidate-filter-over-includes / Python-gate-is-authoritative design working exactly as intended (178-RESEARCH.md Pitfall 6) — no code change was needed, and the full unlimited backfill's aggregate numbers (11495/14331 filled, ~80% overall) confirm the earlier ~20% holed rate was concentrated in this one older user's chess.com-review-only games, not representative of the whole corpus.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 178 (D-01 through D-11, SEED-110) is functionally complete: the migration (Plan 01), the shared compute module (Plan 02), the live-hook wiring (Plan 03), and the historical backfill + validation tooling (this plan) are all in place and empirically cross-checked against real dev data.
- **Running the ~718k-game prod backfill is a separate operator step, NOT gated on phase completion (D-06)** — `bin/prod_db_tunnel.sh` then `uv run python scripts/backfill_accuracy_acpl.py --db prod` (optionally `--user-id` to stage it), followed by `uv run python scripts/validate_accuracy_acpl.py --db prod` to confirm the same tight tracking seen on dev.
- No blockers. `uv run ty check app/ tests/` is zero-error; `uv run pytest tests/services/test_backfill_accuracy_acpl.py -x` passes.
- Surfacing the new computed accuracy/ACPL columns in the API + frontend was explicitly out of scope for this phase (deferred idea in 178-RESEARCH.md) — a future phase would consume `games.white_accuracy`/`black_accuracy`/`white_acpl`/`black_acpl` directly, no further backend plumbing needed.

---
*Phase: 178-lichess-compatible-accuracy-acpl-computed-columns*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: scripts/backfill_accuracy_acpl.py
- FOUND: scripts/validate_accuracy_acpl.py
- FOUND: tests/services/test_backfill_accuracy_acpl.py
- FOUND: .planning/phases/178-lichess-compatible-accuracy-acpl-computed-columns/178-04-SUMMARY.md
- FOUND commit: e8a78e94 (feat)
- FOUND commit: 3a8c9f18 (test)
- FOUND commit: cb7b88c1 (feat)
