---
phase: 116-all-ply-engine-core
plan: "02"
subsystem: backend-service
tags: [stockfish, engine, eval-drain, python-chess, asyncio, postgresql, background-task]

# Dependency graph
requires:
  - phase: 116-all-ply-engine-core
    plan: "01"
    provides: "evaluate_nodes(), Game.full_evals_completed_at column, ix_gp_full_hash_opening"

provides:
  - "run_full_eval_drain() coroutine — all-ply 1M-node analysis with LIFO pick + guest filter + yield gate (EVAL-01/EVAL-03/EVAL-05/QUEUE-07)"
  - "_FullPlyEvalTarget dataclass (game_id, ply, full_hash, board)"
  - "_DEDUP_MAX_PLY = 20 constant (EVAL-03)"
  - "_collect_full_ply_targets(): PGN single-walk collector, terminal exclusion, no is_game_over guard needed"
  - "_fetch_dedup_evals(): marker-gated batch dedup lookup on full_evals_completed_at (Pitfall 4 guard)"
  - "_any_active_import_or_entry_ply_pending(): D-116-11 yield gate predicate"
  - "_mark_full_evals_completed(): single-game unconditional marker write (D-116-07)"
  - "Lifespan wiring in app/main.py as full-eval-drain task"
  - "12-test integration suite covering EVAL-01/03/05 and QUEUE-07"

affects: [116-03-memory-docs, 117-eval-queue]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "4-step session discipline: yield-gate read / pick read / load+dedup read / gather-outside-session / write-late"
    - "D-116-04 is_analyzed gate: white_blunders.isnot(None) column expression used directly in SELECT (hybrid_property not selectable as a column)"
    - "gp_rows list comprehension unwrap: Row[tuple[...]] → tuple[...] via [(r[0], r[1], r[2], r[3]) for r in ...]"
    - "Sentry: set_context + set_tag + capture_message with no f-strings in message body (CLAUDE.md grouping rule)"

key-files:
  created:
    - tests/services/test_full_eval_drain.py
  modified:
    - app/services/eval_drain.py
    - app/main.py

key-decisions:
  - "D-116-04 is_analyzed discriminator: used Game.white_blunders.isnot(None).label('is_analyzed') in the SELECT, not the hybrid property (which is not column-selectable in SQLAlchemy 2.x)"
  - "gp_rows row type: SQLAlchemy Row objects are not assignable to list[tuple[...]] in ty; unpacked via list comprehension"
  - "Scholar's mate has 7 half-moves (plies 0..6), not 8: test updated to expect 7 non-terminal targets"
  - "run_full_eval_drain yield gate uses _any_active_import_or_entry_ply_pending in its own short session before the pick"

patterns-established:
  - "Full-ply drain session discipline: 4 short sessions per tick (yield-gate, pick, load+dedup, write); gather runs between sessions 3 and 4"
  - "Dedup lookup always marker-gated on full_evals_completed_at IS NOT NULL (not evals_completed_at) to exclude depth-15 source rows"

requirements-completed: [EVAL-01, EVAL-03, EVAL-05, QUEUE-07]

# Metrics
duration: 35min
completed: 2026-06-12
---

# Phase 116 Plan 02: Full-Eval Drain Coroutine Summary

**run_full_eval_drain() — all-ply 1M-node drain with yield gate, ply<=20 dedup, is_analyzed preserve gate, and unconditional completion marker; wired into the FastAPI lifespan alongside the untouched entry-ply drain (EVAL-01/03/05/QUEUE-07)**

## Performance

- **Duration:** 35 min
- **Completed:** 2026-06-12
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `_DEDUP_MAX_PLY = 20`, `_FullPlyEvalTarget` dataclass, and four helper functions to `eval_drain.py`
- `_collect_full_ply_targets`: walks PGN mainline once, snapshots `board.copy()` before each push, never adds the terminal position (iterator never visits it — no `is_game_over()` guard needed); returns `[]` on parse failure
- `_fetch_dedup_evals`: batch lookup gated on `Game.full_evals_completed_at IS NOT NULL` (Pitfall 4 guard — excludes depth-15 source rows); returns `{full_hash: (eval_cp, eval_mate)}`
- `_any_active_import_or_entry_ply_pending`: D-116-11 yield gate, two instant indexed predicates
- `_mark_full_evals_completed`: single-game `UPDATE games SET full_evals_completed_at` unconditionally (D-116-07 mark-with-holes)
- `run_full_eval_drain()`: 4-step session discipline (yield-gate / pick / load+dedup / gather-outside-session / write-late); D-116-09 LIFO, D-116-10 guest filter, D-116-04 `is_analyzed` preserve gate evaluated once per game
- `app/main.py`: `full_drain_task = asyncio.create_task(run_full_eval_drain(), name="full-eval-drain")` wired alongside `drain_task` with matching cancel/await/except pattern
- 12-test integration suite covering EVAL-01 (terminal exclusion, PGN failure), EVAL-03 (parity dedup, depth-15 exclusion), EVAL-05 (marker set + holes), QUEUE-07 (AST gather-outside-session scan + two yield-gate predicates)

## Task Commits

1. **Task 1: All-ply collector + dedup lookup + yield gate + marker helpers** — `52018278` (feat)
2. **Task 2: run_full_eval_drain coroutine + lifespan wiring** — `11e44705` (feat)
3. **Task 3: Wave-0 integration test suite** — `cc535170` (feat)

## Verification Results

- `uv run pytest tests/services/test_full_eval_drain.py -x` — 12 passed
- `uv run pytest tests/services/test_eval_drain.py -x` — 13 passed (existing drain untouched, D-116-08)
- `uv run pytest -n auto -x` — 2545 passed, 10 skipped
- `uv run ty check app/ tests/` — zero errors
- `uv run ruff check app/services/eval_drain.py app/main.py tests/services/test_full_eval_drain.py` — clean
- `grep -rn "asyncio.gather" app/services/eval_drain.py` — gather appears only outside session scope (lines 736, 892)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scholar's mate ply count in test**
- **Found during:** Task 3 first pytest run
- **Issue:** `test_collect_all_plies_excludes_terminal` expected 8 targets for Scholar's mate. The PGN `1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6?? 4.Qxf7# 1-0` has 7 half-moves (plies 0..6), not 8; the post-4.Qxf7# board is the terminal checkmate position
- **Fix:** Updated test assertion to expect `expected_ply_count = 7` and document the ply count reasoning in the docstring
- **Files modified:** `tests/services/test_full_eval_drain.py`
- **Commit:** `cc535170`

**2. [Rule 1 - Bug] SQLAlchemy Row type incompatibility in gp_rows**
- **Found during:** Task 2 ty check
- **Issue:** `list(pos_result.all())` returns `list[Row[tuple[...]]]`, not `list[tuple[...]]`, causing a ty type error on the explicit annotation
- **Fix:** Replaced explicit annotation with a list comprehension that unpacks row elements: `gp_rows = [(r[0], r[1], r[2], r[3]) for r in pos_result.all()]`
- **Files modified:** `app/services/eval_drain.py`
- **Commit:** `11e44705`

**3. [Rule 1 - Bug] Hybrid property not column-selectable**
- **Found during:** Task 2 ty check
- **Issue:** `Game.is_analyzed` in a `select()` call emits a ty error — the hybrid property's `_HybridClassLevelAccessor` is not callable as a column expression. `Game._is_analyzed_expression()` is also a classmethod accessor, not callable directly
- **Fix:** Used `Game.white_blunders.isnot(None).label("is_analyzed")` in the SELECT — directly mirrors the hybrid property's implementation in `app/models/game.py`
- **Files modified:** `app/services/eval_drain.py`
- **Commit:** `11e44705`

---

**Total deviations:** 3 auto-fixed (Rule 1 — minor bugs discovered during implementation/type-check)
**Impact on plan:** Necessary correctness fixes, no scope creep.

## Known Stubs

None. All helpers are fully wired and functionally tested.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`:
- T-116-04 (hot-lane starvation) — mitigated: `_any_active_import_or_entry_ply_pending` yield gate implemented and covered by `test_yield_gate_active_import` + `test_yield_gate_entry_ply_pending`
- T-116-05 (lichess %eval overwrite) — mitigated: `is_analyzed` gate preserves existing non-NULL evals for analyzed games (T-78-17), tested implicitly by drain-with-holes test
- T-116-06 (gather inside session) — mitigated: `test_gather_outside_session` AST scan enforces the invariant in CI
- T-116-07 (silent engine failures) — mitigated: `(None, None)` holes captured via `set_context + set_tag + capture_message`

---
*Phase: 116-all-ply-engine-core*
*Completed: 2026-06-12*

## Self-Check: PASSED

Files verified present:
- app/services/eval_drain.py: FOUND
- app/main.py: FOUND
- tests/services/test_full_eval_drain.py: FOUND

Commits verified:
- 52018278: feat(116-02): all-ply collector + dedup lookup + yield gate + marker helpers — FOUND
- 11e44705: feat(116-02): run_full_eval_drain coroutine + lifespan wiring — FOUND
- cc535170: feat(116-02): wave-0 integration test suite for run_full_eval_drain — FOUND
