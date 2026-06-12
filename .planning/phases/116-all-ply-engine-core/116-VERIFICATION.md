---
phase: 116-all-ply-engine-core
verified: 2026-06-12T21:05:00Z
status: passed
score: 10/10 must-haves verified
re_verification: true
re_verification_note: "Initial verification (2026-06-12T20:30:00Z) found 2 gaps; both closed by the /gsd-code-review --fix pass (CR-01 → 19a375a7, ruff format → 83db4c8a) and confirmed during UAT: fixed backfill predicate re-run on dev marked 9,343 games; ruff format --check clean on all 9 phase files. Gap details below retained for history with status: fixed."
gaps:
  - truth: "Pre-existing games with every non-terminal ply eval-populated are marked full_evals_completed_at by the backfill"
    status: fixed  # commit 19a375a7; live-verified during UAT (9,343 games marked by fixed predicate on dev)
    reason: "The migration backfill SQL lacks a move_san IS NOT NULL exclusion for the terminal row. The import pipeline appends a final-position row to every game with move_san=NULL, eval_cp=NULL, eval_mate=NULL (app/services/zobrist.py:239-248). The NOT EXISTS anti-join finds this row in every real game and marks zero games. The 798ms EXPLAIN was a no-op measurement. Migration tests pass because synthetic fixtures omit the terminal row."
    artifacts:
      - path: "alembic/versions/20260612_120000_add_full_evals_completed_at.py"
        issue: "Lines 83-89: NOT EXISTS clause has no AND gp.move_san IS NOT NULL to exclude the terminal position row"
      - path: "tests/test_migration_116_full_evals.py"
        issue: "Fixtures at lines 270-271 and 301-302 insert only non-terminal rows (ply=0, ply=1) with no terminal row, so they do not catch the CR-01 defect"
    missing:
      - "Add AND gp.move_san IS NOT NULL to the NOT EXISTS subquery in the backfill UPDATE"
      - "Update migration tests to include a terminal row (move_san=NULL, eval_cp=NULL) in each fixture; the covered-game test should mark the game, the uncovered test should not"

  - truth: "Four phase-modified files pass ruff format --check (pre-PR gate per CLAUDE.md)"
    status: fixed  # commit 83db4c8a (WR-03); re-verified: ruff format --check clean on all 9 phase files
    reason: "uv run ruff format --check reports 'Would reformat' for eval_drain.py, tests/services/test_engine_nodes.py, tests/services/test_full_eval_drain.py, tests/test_migration_116_full_evals.py. CLAUDE.md mandates running ruff format before push and calls this the single most common preventable CI failure."
    artifacts:
      - path: "app/services/eval_drain.py"
        issue: "Would reformat (line-length violations at ~890 and over-wrapped lines ~949-951)"
      - path: "tests/services/test_engine_nodes.py"
        issue: "Would reformat"
      - path: "tests/services/test_full_eval_drain.py"
        issue: "Would reformat"
      - path: "tests/test_migration_116_full_evals.py"
        issue: "Would reformat"
    missing:
      - "Run: uv run ruff format app/ tests/ and commit with style(...) prefix"
---

# Phase 116: All-Ply Engine Core Verification Report

**Phase Goal:** The eval drain analyzes every ply of queued games at Lichess-parity depth, storing results directly in `game_positions.eval_cp/eval_mate` with dedup and a distinct full-analysis completion marker, and the worker pool's memory footprint is explicitly bounded before the pool size is raised.
**Verified:** 2026-06-12T21:05:00Z (re-verification; initial 2026-06-12T20:30:00Z)
**Status:** passed
**Re-verification:** Yes — both initial gaps closed by the code-review fix pass and confirmed live during UAT

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | evaluate_nodes() searches at 1,000,000-node budget, returns (eval_cp, eval_mate) in white perspective, (None, None) on timeout/crash | VERIFIED | engine.py:92 `_NODES_BUDGET: int = 1_000_000`; engine.py:386 `chess.engine.Limit(nodes=_NODES_BUDGET)`; 0 multipv references; (None, None) failure path at lines 382-399 |
| 2  | games.full_evals_completed_at column exists, nullable TIMESTAMPTZ, distinct from evals_completed_at | VERIFIED | app/models/game.py:158-160 — Mapped[datetime\|None], sa.DateTime(timezone=True), nullable=True; comment cites EVAL-05/D-116-05 |
| 3  | ix_games_full_evals_pending partial index on games(id) WHERE full_evals_completed_at IS NULL | VERIFIED | migration lines 59-65; not in Game.__table_args__ (Critical Constraint 5 preserved) |
| 4  | ix_gp_full_hash_opening cross-user index on game_positions(full_hash) WHERE ply <= 20 | VERIFIED | app/models/game_position.py:103-107 — Index("ix_gp_full_hash_opening", "full_hash", postgresql_where=text("ply <= 20")); migration lines 67-74 |
| 5  | Pre-existing games with every non-terminal ply eval-populated are marked full_evals_completed_at by the backfill | VERIFIED (re-check) | Fixed in 19a375a7: backfill now excludes the terminal row via `gp.move_san IS NOT NULL`; migration test fixtures include terminal rows. Live-verified during UAT: fixed predicate re-run on dev marked 9,343 games (dev had run the pre-fix migration; prod will run the fixed version). |
| 6  | run_full_eval_drain collects every non-terminal ply, evaluates at 1M nodes, writes eval_cp/eval_mate, marks full_evals_completed_at | VERIFIED | eval_drain.py:801-944 — 4-step session discipline implemented; _collect_full_ply_targets excludes terminal position; marker written unconditionally (D-116-07) |
| 7  | Dedup (ply<=20) reuses parity evals from games with full_evals_completed_at IS NOT NULL | VERIFIED | _fetch_dedup_evals (eval_drain.py:153-179) gated on Game.full_evals_completed_at.isnot(None); tested in test_dedup_hits_parity_source and test_dedup_excludes_depth15_source |
| 8  | asyncio.gather runs outside any AsyncSession scope | VERIFIED | eval_drain.py:887-896 — gather at line 892 is between load_session close (line 885) and write_session open (line 905); AST scan test at test_full_eval_drain.py:499-533 guards this invariant |
| 9  | Real per-worker RSS at 1M-node budget is measured and accounting documented against 4g limit | VERIFIED | engine.py:109-129 — measured table (1w=277MB, 8w=2083MB); conservative prod math 3.24GB / 0.76GB headroom; CLAUDE.md lines 221 updated; docker-compose.yml lines 79-88 updated |
| 10 | Formatter gate passes (ruff format --check) on all four phase-modified files | VERIFIED (re-check) | Fixed in 83db4c8a (WR-03). Re-verified: `ruff format --check` clean on all 9 phase files. |

**Score:** 10/10 truths verified (re-verification; initial score 8/10)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/engine.py` | evaluate_nodes() + _NODES_BUDGET/_NODES_TIMEOUT_S constants | VERIFIED | Constants at lines 92-93; module-level evaluate_nodes at ~line 175; EnginePool.evaluate_nodes at lines 370-401 |
| `app/models/game.py` | full_evals_completed_at column | VERIFIED | Lines 158-160 — nullable TIMESTAMPTZ |
| `app/models/game_position.py` | ix_gp_full_hash_opening dedup index | VERIFIED | Lines 103-107 — ply <= 20 predicate, no user_id |
| `alembic/versions/20260612_120000_add_full_evals_completed_at.py` | column + 2 indexes + backfill | VERIFIED (re-check) | Column and indexes correct; backfill fixed in 19a375a7 (terminal-row exclusion), live-verified marking 9,343 games on dev |
| `app/services/eval_drain.py` | run_full_eval_drain + all helpers + _DEDUP_MAX_PLY | VERIFIED | All 7 symbols present and substantive; ruff format issue is style only |
| `app/main.py` | lifespan wiring of run_full_eval_drain | VERIFIED | Line 80: asyncio.create_task(run_full_eval_drain(), name="full-eval-drain"); cancel/await in finally |
| `tests/services/test_engine_nodes.py` | EVAL-02 test scaffold | VERIFIED | Limit(nodes=) contract test, pool-unset test, real-engine test present |
| `tests/test_migration_116_full_evals.py` | migration tests | VERIFIED (re-check) | Fixtures updated in 19a375a7 to include terminal rows; backfill tests now exercise the real schema shape |
| `tests/services/test_full_eval_drain.py` | EVAL-01/03/05/QUEUE-07 tests | VERIFIED | All 9 required test names present and substantive |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| app/services/engine.py::evaluate_nodes | chess.engine.Limit(nodes=_NODES_BUDGET) | protocol.analyse | WIRED | Line 386: `protocol.analyse(board, chess.engine.Limit(nodes=_NODES_BUDGET))` |
| alembic migration backfill | games.full_evals_completed_at | UPDATE NOT EXISTS anti-join | WIRED (re-check) | Fixed in 19a375a7: anti-join excludes terminal row; live-verified marking 9,343 games on dev |
| app/services/eval_drain.py::run_full_eval_drain | engine_service.evaluate_nodes | asyncio.gather outside session | WIRED | Line 892: gather on evaluate_nodes calls; load_session closed at line 885 before gather |
| app/services/eval_drain.py::_fetch_dedup_evals | Game.full_evals_completed_at | marker-gate join | WIRED | Line 173: Game.full_evals_completed_at.isnot(None) in WHERE clause |
| app/main.py lifespan | run_full_eval_drain | asyncio.create_task | WIRED | Lines 28, 80, 91, 106-110 — import, create, cancel, await |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| run_full_eval_drain write loop | eval_cp/eval_mate per ply | engine_service.evaluate_nodes or dedup_map | Engine calls produce real data; dedup source seeded by fixed backfill (19a375a7) | FLOWING (re-check: UAT observed dedup hits at plies 0-17 on live drain) |
| _fetch_dedup_evals | {full_hash: (eval_cp, eval_mate)} | DB query gated on full_evals_completed_at IS NOT NULL | Source set seeded: 10,577 marked games on dev after fixed backfill | FLOWING (re-check) |

### Behavioral Spot-Checks

Step 7b: Tests run, not the live app.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| evaluate_nodes uses 1M-node Limit | `grep -n "Limit(nodes=_NODES_BUDGET)" app/services/engine.py` | Line 386: match found | PASS |
| gather outside session | `grep -rn "asyncio.gather" app/services/eval_drain.py` | Lines 892 and 736 — both outside async-with blocks | PASS |
| ruff format gate | `uv run ruff format --check app/services/eval_drain.py ...` | Clean on all 9 phase files after 83db4c8a | PASS (re-check) |
| ty check core files | `uv run ty check app/services/engine.py app/services/eval_drain.py ...` | All checks passed | PASS |
| ruff lint | `uv run ruff check app/services/eval_drain.py app/services/engine.py ...` | All checks passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| EVAL-01 | 116-02 | Every ply of a queued game gets eval_cp/eval_mate, terminal excluded | SATISFIED | _collect_full_ply_targets + run_full_eval_drain; test_collect_all_plies_excludes_terminal passes |
| EVAL-02 | 116-01 | 1,000,000-node budget, NNUE, multiPV=1 | SATISFIED | _NODES_BUDGET=1_000_000; 0 multipv references; Limit(nodes=_NODES_BUDGET) |
| EVAL-03 | 116-01, 116-02 | ply<=20 full_hash dedup reuses existing server eval | SATISFIED | Dedup query + ix_gp_full_hash_opening correct; seed restored by fixed backfill (19a375a7); UAT observed live dedup hits at plies 0-17 |
| EVAL-05 | 116-01, 116-02 | Distinct full-analysis completion marker | SATISFIED | full_evals_completed_at column + index; _mark_full_evals_completed writes unconditionally |
| QUEUE-07 | 116-01, 116-02, 116-03 | Memory bounded against 4g; drain coexists with import lane | SATISFIED | engine.py accounting comment; CLAUDE.md Phase 116 paragraph; docker-compose.yml updated; yield gate _any_active_import_or_entry_ply_pending |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| alembic/versions/20260612_120000_add_full_evals_completed_at.py | 83-89 | Backfill NOT EXISTS sub-query missing move_san IS NOT NULL | BLOCKER | Backfill marks zero real games; dedup seeding fails for day-1 deploy |
| alembic/versions/20260612_120000_add_full_evals_completed_at.py | 19 | `Revision ID: <autogenerated>` placeholder never replaced | INFO | Cosmetic; every sibling migration uses the literal revision id |
| app/services/eval_drain.py | 916-923 | Per-ply Sentry capture_message on engine failure (one per NULL hole) | WARNING | Could flood Sentry quota if pool degrades; not a test-blocking issue |
| app/services/eval_drain.py | 890 | ruff format would reformat this line | WARNING | Pre-PR gate failure per CLAUDE.md |
| tests/test_migration_116_full_evals.py | 270-271, 301-302 | Backfill test fixtures omit terminal row | BLOCKER | Tests pass but validate a scenario that never occurs in production |

### Gaps Summary

**Gap 1 — CR-01: Migration backfill marks zero real games (BLOCKER)**

The Plan 01 must-have "Pre-existing games with every non-terminal ply eval-populated are marked full_evals_completed_at by the backfill" is not met. The import pipeline (`app/services/zobrist.py:239-248`) appends a terminal game_positions row with `move_san=NULL`, `eval_cp=NULL`, `eval_mate=NULL` to every imported game. The backfill SQL's `NOT EXISTS (SELECT 1 ... WHERE gp.eval_cp IS NULL AND gp.eval_mate IS NULL)` anti-join finds this terminal row for every game with at least one move and marks nothing.

Downstream consequence: the D-116-06 dedup seeding from the existing corpus does not happen at deploy. The dedup index and query are correct; the source set will populate over time as the drain completes games. But the claim that the backfill "seeds the dedup source set from day one" is false.

Secondary consequence: all fully-analyzed lichess games (`is_analyzed=True`) will be picked by the drain, undergo full 1M-node evaluation for every ply, and then have those results discarded by the `is_analyzed` preservation gate — burning compute for zero written rows (WR-01 in REVIEW.md compounds this).

**Fix required:**

```sql
UPDATE games g
SET full_evals_completed_at = COALESCE(g.imported_at, NOW())
WHERE g.full_evals_completed_at IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM game_positions gp
      WHERE gp.game_id = g.id
        AND gp.move_san IS NOT NULL      -- exclude the terminal row (never evaluated by design)
        AND gp.eval_cp IS NULL
        AND gp.eval_mate IS NULL
  )
```

Both migration tests must gain a terminal row (move_san=NULL, eval_cp=NULL, eval_mate=NULL) in their fixtures, inserted after the non-terminal rows.

**Gap 2 — WR-03: ruff format --check fails on 4 files (BLOCKER per CLAUDE.md pre-PR gate)**

`uv run ruff format --check` reports "Would reformat" for `app/services/eval_drain.py`, `tests/services/test_engine_nodes.py`, `tests/services/test_full_eval_drain.py`, and `tests/test_migration_116_full_evals.py`. CLAUDE.md's pre-PR checklist explicitly states: "Run `uv run ruff format app/ tests/`" and "A CI 'would reformat' failure is always avoidable locally — treat the checklist as part of `git push`". Both `ruff check` (lint) and `ty check` are clean; this is a formatter issue only.

Fix: `uv run ruff format app/ tests/` and commit with a `style(116)` prefix before integration.

---

_Verified: 2026-06-12T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
