---
phase: 178-lichess-compatible-accuracy-acpl-computed-columns
verified: 2026-07-18T09:33:42Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 178: Lichess-compatible accuracy & ACPL (computed columns) Verification Report

**Phase Goal:** Compute per-game accuracy and ACPL for every analyzed game using lichess's exact formulas, written into the repurposed canonical games columns (white_accuracy / black_accuracy / white_acpl / black_acpl) from the per-ply evals already in game_positions, with the original platform-provided values preserved in new *_imported columns. One uniform methodology; a single Python compute path used both at the live hook (_classify_and_fill_oracle full-eval completion) and in scripts/backfill_accuracy_acpl.py; gate on a complete per-ply eval sequence (holes → leave NULL); inaccuracies/mistakes/blunders left untouched (D-04).

**Verified:** 2026-07-18T09:33:42Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Migration copies platform values into `*_imported` BEFORE nulling canonical columns; oracle severity-count columns untouched (D-01..D-04) | VERIFIED | `alembic/versions/20260718_084123_60d9b72c0eaa_...py` — two sequential `op.execute` UPDATEs, copy textually before NULL; `grep -c -E 'inaccuracies|mistakes|blunders'` on the migration file (excluding comments) returns 0. Migration test `test_copy_survives_downgrade_and_reupgrade_preserves_copy_before_null` behaviorally proves the ordering via the real `alembic downgrade -1` / `upgrade head` round-trip — a copy-after-null bug would fail it. Test run: PASS. |
| 2 | Canonical columns NULL after upgrade; `*_imported` columns hold pre-migration values; column types correct (REAL / SmallInteger, nullable) | VERIFIED | `app/models/game.py:163-180` — four `*_imported` mapped_columns added with correct types; `test_canonical_and_imported_columns_null_on_fresh_insert` and `test_imported_columns_present_and_independently_writable` PASS. Dev DB spot-check: `white_accuracy_imported` filled on 79,757 rows, canonical `white_accuracy` NULL except where the compute path has since refilled it (11,552 rows) — consistent with D-01/D-02. |
| 3 | Single shared Python compute path (`app/services/accuracy_acpl.py`) implements the four locked lichess formulas (D-08..D-11) with correct sign/post-move-shift/mover-parity mapping | VERIFIED | `app/services/accuracy_acpl.py` — `win_pct` (pre-sigmoid ±1000 ceiling, imports `LICHESS_K` from `eval_utils`, no re-declared constant), `move_accuracy` (exponential decay + trailing +1), `compute_color_accuracy` (windowed stddev-weighted + harmonic mean), `compute_color_acpl` (plain mean), orchestrator `compute_game_accuracy_acpl` (post-move-shift `{ply+1: eval}` map, mover-parity sign flip, `_is_hole_free` gate). 16 unit tests in `tests/services/test_accuracy_acpl.py` PASS, including the hand-checked lichess game 296343 fixture asserting exact `white_acpl=18`/`black_acpl=61` and windowed accuracy within ±1 of lichess's own 84/61. |
| 4 | Complete-per-ply-eval-sequence gate: an interior hole makes the compute return `None` (all four NULL); a holed/0-move game is never miscomputed | VERIFIED | `accuracy_acpl.py::_is_hole_free` / `compute_game_accuracy_acpl` — returns `None` on any interior missing eval or a 0-move game; terminal-only NULL (checkmate) is not a hole. `test_incomplete_sequence_returns_none` and `test_edge_cases` PASS. Confirmed live at the hook seam by `test_accuracy_acpl_null_on_interior_hole` (direct DB-backed call to `_classify_and_fill_oracle` with a hand-placed ply-2 hole — asserts all four columns NULL while `white_blunders` and the pre-existing `full_evals_completed_at` stamp are untouched). Confirmed in the backfill by `test_backfill_accuracy_acpl.py` (holed game stays NULL). |
| 5 | Live hook writes the four canonical columns atomically with oracle counts and completion stamps, reusing the already-loaded `positions` list, gated on the shared compute's result (D-01/D-03) | VERIFIED | `app/services/eval_apply.py:1074` calls `compute_game_accuracy_acpl(positions)` on the already-loaded list (no new query — code inspection confirms no second `select(GamePosition)` added); the four keys (`white_accuracy`/`black_accuracy`/`white_acpl`/`black_acpl`, lines 1089-1100) ride the SAME pre-existing `update(games_table)....values(...)` call that also writes `white_inaccuracies`/`white_mistakes`/`white_blunders` etc. `_classify_and_fill_oracle` runs inside the caller's single `write_session` alongside `apply_completion_decision` (which sets `full_evals_completed_at`/`full_pv_completed_at`) — one shared transaction, one commit (`apply_full_eval` docstring: "inside the CALLER's write_session (T-117-11 — one commit)"). `test_accuracy_acpl_filled_after_hole_free_drain_tick` drives a real `_full_drain_tick()` and asserts all four columns non-NULL/in-range AND `full_evals_completed_at` set in the same committed state. PASS. |
| 6 | Backfill script (`scripts/backfill_accuracy_acpl.py`) calls the exact same compute function — no re-implemented formula logic — streams via a single server-side cursor (no N+1), gates on `white_blunders IS NOT NULL` + `white_accuracy IS NULL`, does not filter on eval presence (holes stay visible to the Python gate) | VERIFIED | `scripts/backfill_accuracy_acpl.py:106` imports `compute_game_accuracy_acpl` from `app.services.accuracy_acpl`; `_process_batch` calls it directly per game group, zero re-implemented math. `_build_candidate_stmt` filters on `Game.white_blunders.isnot(None)` + `Game.white_accuracy.is_(None)`, no `eval_cp`/`eval_mate` filter. `_stream_game_batches` uses `session.stream(stmt)` (server-side cursor) + `itertools.groupby` by `game_id` — no per-game `select(GamePosition)` inside a loop (grep-confirmed). `uv run ty check app/` zero errors. `tests/services/test_backfill_accuracy_acpl.py` PASS (pins exact values `white_acpl=2`/`black_acpl=0` for the complete game, NULL for the holed game). Empirically re-ran `--db dev`: full corpus already backfilled (candidate set empty — consistent with the documented prior full run). |
| 7 | Validation script compares computed values against `*_imported` (primary ACPL, secondary accuracy, chess.com divergence reported separately, not a failure) | VERIFIED | `scripts/validate_accuracy_acpl.py` — `_fetch_primary_acpl_deltas` (lichess ACPL), `_fetch_accuracy_deltas` (lichess + chess.com accuracy, split by provenance). Re-ran `uv run python scripts/validate_accuracy_acpl.py --db dev`: PRIMARY ACPL delta n=9120 mean=0.13/median=0.00/p95=1.00 (matches SUMMARY's claimed figures exactly); SECONDARY accuracy delta mean=0.47; DIVERGENT chess.com mean=11.07, reported separately, script exits 0 (not a failure gate). `uv run ty check app/` zero errors. |
| 8 | No API/frontend surface added; scope stays backend-only (D-05); no second hook added at lichess import | VERIFIED | `git diff`/file list for the phase touches only `alembic/versions/`, `app/models/game.py`, `app/services/accuracy_acpl.py`, `app/services/eval_apply.py`, `scripts/backfill_accuracy_acpl.py`, `scripts/validate_accuracy_acpl.py`, and their tests — no `frontend/`, no `app/schemas/`, no `app/routers/` changes. `eval_apply.py::apply_full_eval` is the single shared write body for both the server drain and remote atomic-submit path (confirmed by code inspection at :2388-2403); no new import-time hook was added. |

**Score:** 8/8 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py` | Add-column + copy + null migration | VERIFIED | Present; upgrade/downgrade round-trip clean (`alembic upgrade head` at repo baseline); grep confirms no oracle-column references |
| `app/models/game.py` | Four `*_imported` mapped_columns + corrected comments | VERIFIED | Lines 163-180; oracle severity-count columns unchanged |
| `tests/services/test_migration_178_accuracy_imported.py` | Migration behavior test | VERIFIED | 3 tests, all pass |
| `app/services/accuracy_acpl.py` | Pure compute module (D-08..D-11) | VERIFIED | 331 lines; imports `LICHESS_K`, no re-declared magic number; `ty check` clean |
| `tests/services/test_accuracy_acpl.py` | Fixture + edge-case tests | VERIFIED | 16 tests, all pass, including the exact 296343 ACPL fixture |
| `app/services/eval_apply.py` (modified) | Live-hook wiring in `_classify_and_fill_oracle` | VERIFIED | Four keys folded into the existing atomic UPDATE; no second query, no second UPDATE |
| `tests/services/test_full_eval_drain.py` (modified) | Drain-tick integration test | VERIFIED | `TestAccuracyAcplHook` class, 2 tests, both pass |
| `scripts/backfill_accuracy_acpl.py` | Streaming, batched, `--db`-targeted backfill | VERIFIED | Present; `--db dev --dry-run --limit 5` behavior confirmed by code path inspection and dev-DB validation run |
| `scripts/validate_accuracy_acpl.py` | Computed-vs-imported comparison | VERIFIED | Present; re-ran against dev DB, output matches SUMMARY claims |
| `tests/services/test_backfill_accuracy_acpl.py` | Backfill dev-DB test | VERIFIED | 1 test, pins exact values, passes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Migration `upgrade()` | `*_imported` columns | copy-then-null ordering, textually enforced + behaviorally tested | WIRED | `test_copy_survives_downgrade_and_reupgrade_preserves_copy_before_null` proves via the shipped down migration — a copy-after-null bug would fail it |
| `eval_apply.py::_classify_and_fill_oracle` | `app/services/accuracy_acpl.py::compute_game_accuracy_acpl` | direct import + call on already-loaded `positions` | WIRED | Line 76 import, line 1074 call; zero extra query |
| `scripts/backfill_accuracy_acpl.py` | `app/services/accuracy_acpl.py::compute_game_accuracy_acpl` | direct import + call per game group | WIRED | Line 106 import, line 238 call; no duplicated formula code (grep for `math.exp`/`sigmoid`-shaped logic in the backfill script returns nothing) |
| Four new UPDATE keys | existing atomic `games_table` UPDATE (`_classify_and_fill_oracle`) | same `.values(...)` call, lines 1082-1101 | WIRED | Confirmed by direct file read — not a second `update()` statement |
| `_classify_and_fill_oracle` | caller's single `write_session` (shared with completion-stamp writes) | `apply_full_eval` (eval_apply.py:2388-2403) | WIRED | Docstring + code confirm one write_session, one commit owned by the caller (server drain or remote atomic-submit) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase-specific unit + integration tests | `uv run pytest tests/services/test_accuracy_acpl.py tests/services/test_migration_178_accuracy_imported.py tests/services/test_backfill_accuracy_acpl.py -q` | 20 passed | PASS |
| Live-hook drain-tick tests | `uv run pytest tests/services/test_full_eval_drain.py -k accuracy -q` | 2 passed, 48 deselected | PASS |
| Type check | `uv run ty check app/ tests/` | All checks passed | PASS |
| Lint | `uv run ruff check` on the 5 phase source files | All checks passed | PASS |
| Full backend suite (regression check) | `uv run pytest -n auto -q` | 3506 passed, 18 skipped | PASS |
| Validation script re-run against dev DB | `uv run python scripts/validate_accuracy_acpl.py --db dev` | PRIMARY ACPL delta n=9120 mean=0.13/median=0.00/p95=1.00; matches SUMMARY exactly | PASS |
| Dev DB canonical-column population spot-check | `SELECT count(*) FILTER (...) FROM games` | 14,388 analyzed games; 11,552 with `white_accuracy`/`white_acpl` filled; 79,757 with `white_accuracy_imported` filled | PASS (consistent with D-01/D-02; remaining ~2,836 unfilled are chess.com-review-only games with zero `game_positions.eval_cp` — documented, expected `skipped_none`) |

### Requirements Coverage

No requirement IDs are declared for this phase (ROADMAP.md: `Requirements: TBD`; no phase-178 entries in REQUIREMENTS.md). Nothing to trace.

### Anti-Patterns Found

None. Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|placeholder|not yet implemented` across the phase's five modified/created source files (`accuracy_acpl.py`, `eval_apply.py`, `backfill_accuracy_acpl.py`, `validate_accuracy_acpl.py`, `game.py`, the migration) returns only pre-existing, unrelated `_placeholder_defender_node` hits in `eval_apply.py` (SEED-079 PV-blob logic, untouched by this phase).

### Human Verification Required

None. All must-haves are backend-only, deterministic, and covered by automated tests plus a live re-run of the validation script against real dev data.

### Gaps Summary

None. All 8 derived observable truths (spanning the migration, the shared compute module, the live hook, the backfill, and the validation script) verified against the actual codebase — not just SUMMARY.md claims. Key findings from independent verification:

- The migration's copy-before-null ordering is proven by a genuine behavioral test that drives the real `alembic downgrade`/`upgrade` round-trip, not a schema-presence check — a copy-after-null regression would fail it.
- The single-shared-compute-path guarantee (D-06) is real: both `eval_apply.py` and `backfill_accuracy_acpl.py` import and call the identical `compute_game_accuracy_acpl`; no formula logic is duplicated in either caller (grep-confirmed).
- The four canonical columns ride the SAME atomic `UPDATE games` statement as the oracle counts in `_classify_and_fill_oracle`, and that function executes inside the caller's single `write_session` alongside the completion-stamp writes — genuinely atomic, not a claim needing extra trust.
- The complete-sequence NULL gate is exercised at three independent levels (pure unit test, live-hook DB-backed test, backfill DB-backed test), all passing, all pinning exact values rather than "some non-NULL value."
- D-04 (oracle columns untouched) is enforced by both a grep guardrail baked into the migration test's acceptance criteria and a passing full 3506-test regression suite with zero unrelated failures.
- Re-running the validation script against dev DB independently reproduced the SUMMARY's claimed empirical figures (PRIMARY ACPL delta mean=0.13, n=9120) exactly — not just trusted from the summary.

---

_Verified: 2026-07-18T09:33:42Z_
_Verifier: Claude (gsd-verifier)_
