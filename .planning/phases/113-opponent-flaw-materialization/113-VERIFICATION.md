---
phase: 113-opponent-flaw-materialization
verified: 2026-06-10T09:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run benchmark cohort backfill and spot-check opponent rows"
    expected: "Benchmark game_flaws shows rows at both even and odd plies for sampled games (volume roughly doubled vs pre-backfill); prod game_flaws untouched"
    why_human: "Long unattended run against the benchmark DB — explicitly declared HUMAN-UAT phase-114 hand-off per D-09; does not gate phase completion but must be confirmed before phase 114 consumes the benchmark data"
    result: "PASSED 2026-06-10 — backfill: 2,767,158 games processed, 0 errors, 3,805,691 flaw rows across 4,434 users; even/odd ply split 1,903,110/1,902,581 (both sides). Per-game spot-check confirms parity gate (white-user→player on even plies, black-user→player on odd plies). Prod untouched. See 113-UAT.md."
---

# Phase 113: Opponent-Flaw Materialization Verification Report

**Phase Goal:** Persist both sides' M+B flaws in `game_flaws` for every analyzed game (opponent flaws alongside player flaws) at zero added engine cost, with the player/opponent split DERIVED at read time via `is_opponent_expr` (no column, no migration, no index). Every existing `game_flaws` reader is gated player-only so opponent rows do not leak into the self-only Library UI.
**Verified:** 2026-06-10T09:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `is_opponent_expr` is the single source of the ply-parity convention, returns correct boolean for all 4 (ply parity x user_color) combinations | VERIFIED | `query_utils.py` lines 23-51 define `is_opponent_expr` with named constant `_PLY_EVEN_MOVER_WHITE = 0`; `TestIsOpponentExpr` 4 tests pass against real DB |
| 2 | `player_only_gate` convenience wrapper exists for readable D-04 call sites | VERIFIED | `query_utils.py` lines 54-71 define `player_only_gate` as `~is_opponent_expr(...)` |
| 3 | `classify_game_flaws` emits FlawRecords for BOTH movers with per-mover `subject_result` for lucky tag; no `if mover != user_color: continue` filter | VERIFIED | `flaws_service.py` lines 537-568: filter dropped; `derive_user_result(game.result, mover)` called per-mover; code comment at drop site explains D-06/D-05 |
| 4 | `game_flaw.py` ORM model is UNCHANGED (no `is_opponent` column, no migration) | VERIFIED | Model has PK (user_id, game_id, ply) + severity/tempo/phase/bool tag columns only; no is_opponent column; most recent migration `20260609_drop_game_flaws_display_cols.py` predates phase 113 scope; `grep -rl is_opponent alembic/versions/` returns empty |
| 5 | All 5 `game_flaws` readers in `library_repository.py` carry `player_only_gate`; `count_game_severities` is unchanged | VERIFIED | R1 (`flaw_exists_from_table` line 161), R2 (`query_flaws` line 272), R3 (`fetch_page_game_flaws` line 367), R4 (`fetch_stats_aggregates` line 495), R5 (`fetch_stats_trend` line 581) all have `player_only_gate(GameFlaw.ply, Game.user_color)` with D-04 comments; `count_game_severities` still has its own `if mover != user_color: continue` (line 609) |
| 6 | Dev users 28 & 44 backfilled with both sides; ungated ~2x player-only baseline; gated reads equal pre-phase baseline | VERIFIED | SUMMARY 03: pre-backfill 1620 rows; post-backfill 3310 rows (2.04x); gated SQL returns exactly 1620 for both users; idempotency confirmed |

**Score:** 6/6 truths verified

### Deferred Items

None — all truths are verified for this phase.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/repositories/query_utils.py` | `is_opponent_expr` + `player_only_gate` helpers | VERIFIED | Both defined, correct signatures, named constant `_PLY_EVEN_MOVER_WHITE`, docstrings documenting parity convention |
| `app/services/flaws_service.py` | `classify_game_flaws` generalized to both movers | VERIFIED | Player-only filter dropped; per-mover `subject_result`; D-06 comment at change site |
| `app/models/game_flaw.py` | UNCHANGED (no new column) | VERIFIED | No `is_opponent` column; PK unchanged |
| `app/repositories/library_repository.py` | All 5 read sites gated | VERIFIED | R1-R5 all carry `player_only_gate` with Game JOIN for `user_color` access |
| `tests/services/test_flaws_service.py` | `TestIsOpponentExpr`, `TestClassifyBothColors`, `TestOpponentLuckyTag` | VERIFIED | All 3 classes present and substantive; 9 tests pass |
| `tests/test_flaws_materialization.py` | `TestBothSidesMaterialization` | VERIFIED | Class present; 2 integration tests pass |
| `tests/test_library_repository.py` | `TestPlayerOnlyGate`, `TestPageFlawsPlayerOnly`, `TestStatsAggregatesPlayerOnly` | VERIFIED | All 3 classes present; 6 tests pass |
| `tests/test_flaw_predicate.py` | `TestFlawExistsPlayerOnly` | VERIFIED | Class present; 5 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `classify_game_flaws` | `flaw_record_to_row` | `FlawRecord` carrying `side` | VERIFIED | `flaws_service.py` passes all FlawRecords; `flaw_record_to_row` unchanged per D-06 |
| All 5 library_repository read sites | `is_opponent_expr` in `query_utils.py` | `player_only_gate(GameFlaw.ply, Game.user_color)` | VERIFIED | `grep player_only_gate library_repository.py` confirms 5 call sites |
| `apply_game_filters` (R6) | `flaw_exists_from_table` (R1) | Lazy import delegation; gating R1 propagates to R6 | VERIFIED | `query_utils.py` line 181 lazy-imports and calls `flaw_exists_from_table`; R1 carries the gate so R6 is fixed automatically |
| `backfill_flaws.py` | `classify_game_flaws` | D-10 single classify path — no script edit needed | VERIFIED | SUMMARY 03 confirms zero code changes to `backfill_flaws.py`; kernel propagated automatically |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces no new components, pages, or dashboards rendering dynamic data. It writes data to an existing table and gates readers. The data flow correctness is verified structurally by the key link checks and behaviorally by the passing test suite.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `TestIsOpponentExpr` — all 4 parity combinations via real DB | `uv run pytest tests/services/test_flaws_service.py::TestIsOpponentExpr -x -q` | 4 passed | PASS |
| `TestBothSidesMaterialization` — ungated count >= 2x player-only | `uv run pytest tests/test_flaws_materialization.py::TestBothSidesMaterialization -x -q` | 2 passed | PASS |
| `TestStatsAggregatesPlayerOnly` — gated == baseline, ungated > baseline | `uv run pytest tests/test_library_repository.py::TestStatsAggregatesPlayerOnly -x -q` | passes (within 6-test class run) | PASS |
| `TestFlawExistsPlayerOnly` — opponent-only flaw does not flag game | `uv run pytest tests/test_flaw_predicate.py::TestFlawExistsPlayerOnly -x -q` | 5 passed | PASS |
| Full backend suite — no regression | `uv run pytest -n auto -x -q` | 2491 passed, 10 skipped, 1 warning | PASS |

### Probe Execution

No probe scripts declared or applicable for this phase (no `scripts/tests/probe-*.sh`).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FLAWX-01 | 113-01 | `is_opponent` derived at query time via `is_opponent_expr`; both sides queryable per game | SATISFIED | `is_opponent_expr` in `query_utils.py`; all 4 parity combos tested; kernel emits both sides |
| FLAWX-02 | 113-01 | Player-only filter dropped; all classify paths emit both sides at zero engine cost | SATISFIED | Filter dropped in `classify_game_flaws`; D-10 single classify path propagates to eval_drain, reclassify_positions, backfill_flaws |
| FLAWX-03 | Phase 113 | VOIDED — no column, no migration, no index | VOIDED (correct) | No `is_opponent` column in model; no migration file; traceability table shows "Pending" but requirement body is struck through with VOIDED annotation per D-02/D-03. The "Pending" entry is a docs artifact, not a gap — the voiding is authoritatively documented in the requirement text and CONTEXT. |
| FLAWX-04 | 113-03 | `backfill_flaws.py` repopulates opponent flaws; idempotent; prod stays empty | SATISFIED | Dev users 28 & 44 backfilled 1620 → 3310 rows (2.04x); zero code changes to script; prod untouched |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No `TBD`, `FIXME`, or `XXX` markers found in any modified files. No stub implementations. No empty handlers.

### Human Verification Required

The following item is explicitly declared as HUMAN-UAT in Plan 03 (Task 2, `gate=blocking` for phase 114 readiness, but `does NOT gate phase completion` per D-09). It is surfaced here per the standard human_verification workflow.

#### 1. Benchmark Cohort Backfill

**Test:** Run `uv run python scripts/backfill_flaws.py --db benchmark` (optionally `--dry-run` first). Spot-check a sample benchmark game: query `SELECT ply, severity FROM game_flaws WHERE game_id = <id> AND user_id = <uid> ORDER BY ply LIMIT 20` and confirm rows at both even and odd plies.

**Expected:** Row volume roughly doubled vs pre-backfill; both even and odd plies present for each sampled game; prod `game_flaws` untouched.

**Why human:** Long unattended run against the benchmark DB. Must be confirmed before phase 114 consumes the benchmark `game_flaws` for delta-zone computation. Declared non-blocking for phase 113 completion per D-09 (CONTEXT).

### Gaps Summary

No gaps. All 6 must-have truths are verified in the codebase with passing tests and correct implementations. The only open item is the benchmark backfill HUMAN-UAT hand-off to phase 114, which is explicitly non-blocking for phase 113 completion per D-09.

---

_Verified: 2026-06-10T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
