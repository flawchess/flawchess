---
phase: 144-user-28-a-b-validation
plan: "01"
subsystem: tactic-analysis
tags: [tdd, a-b-harness, forcing-line-gate, engine-free, read-only]
dependency_graph:
  requires: [phase-143-forcing-line-gate]
  provides: [scripts/ab_validate_gate.py, tests/scripts/test_ab_validate_gate.py]
  affects: [VALID-01, VALID-02, reports/retag/ab-validation-*.md]
tech_stack:
  added: []
  patterns: [tdd-red-green, session-maker-injection, report-dir-injection, counter-accumulation]
key_files:
  created:
    - scripts/ab_validate_gate.py
    - tests/scripts/test_ab_validate_gate.py
  modified: []
decisions:
  - "Ungated arm wires _detect_tactic_for_flaw directly — not --margin 0, which still applies gate heuristics (already-winning reject, still-winning floor, one-mover discard)"
  - "Both arms read identical stored JSONB blobs, eliminating eval_cp cross-machine non-determinism from the A/B measurement (VALID-01 core guarantee)"
  - "local _PosRow defined independently in the harness to avoid coupling to retag_flaws private symbols"
  - "ty suppress uses # ty: ignore[invalid-argument-type] (not # type: ignore) for the spy wrapper in the test scaffold per CLAUDE.md"
metrics:
  duration: "~45min (cross-session: Wave 0 scaffold in prior session, GREEN implementation in this session)"
  completed: "2026-06-30"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
status: complete
---

# Phase 144 Plan 01: A/B Gate Validation Harness Summary

Engine-free A/B harness (`scripts/ab_validate_gate.py`) + Wave 0 Nyquist scaffold (`tests/scripts/test_ab_validate_gate.py`) — loads user-28 stored MultiPV JSONB blobs once and runs `_detect_tactic_for_flaw` (ungated) vs `_classify_tactic_gated` (gated) over identical inputs to isolate the forcing-line gate's suppression effect.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wave 0 — failing test scaffold | c6097faf | tests/scripts/test_ab_validate_gate.py (+490 lines) |
| 2 | Implement scripts/ab_validate_gate.py to green | 564479d2 | scripts/ab_validate_gate.py (+918 lines), tests/scripts/test_ab_validate_gate.py (+1 line ty-fix) |

## What Was Built

### scripts/ab_validate_gate.py

Read-only, engine-free A/B harness. Key components:

- `lichess_analysis_url(board_fen, ply)`: builds `https://lichess.org/analysis?fen={encoded}` from board_fen() + ply parity (w/b); spaces percent-encoded as `%20` per RFC 3986
- `_load_ab_flaws(session, user_id)`: single non-paginated SELECT on `game_flaws` projecting deferred `allowed_pv_lines`/`missed_pv_lines` explicitly; filters to blob-bearing rows only
- `_load_positions(session, flaws)`: batched SELECT at (ply, ply+1) keys via `tuple_().in_()`, returns `dict[(uid,gid,ply)] -> _PosRow`
- `_run_both_arms(...)`: UNGATED calls `_detect_tactic_for_flaw` directly (gate never invoked); GATED calls `_classify_tactic_gated` at the test margin
- `_process_flaws(...)`: accumulates ungated/suppressed/survived Counters per motif and per orientation; builds per-arm depth distributions (0/1/2/3+ buckets); collects `AbCase` dropped-case list
- `_write_ab_report(...)`: Executive Summary, Per-Motif Allowed/Missed, Depth-Shift Distribution, Dropped Cases + Full PV detail, HUMAN-UAT placeholder sections, A/B Summary
- `run_ab_validation(*, db, user_id, margin, neighbourhood, session_maker, report_dir)`: orchestrates load → process → report; session_maker and report_dir injectable for test isolation
- `AbResult` / `AbCase` dataclasses: public types imported by tests and consumed by Plan 02

### tests/scripts/test_ab_validate_gate.py

Six Nyquist tests with seeded fixture (`_TEST_USER_ID = 144_010`):

1. `test_ungated_arm_bypasses_gate` — monkeypatches `app.services.flaws_service.apply_forcing_line_filter` as a spy; asserts ungated detects but gated suppresses the NON_FORCING_BLOB case, and gate was called at most once (only by gated arm)
2. `test_both_arms_use_same_blobs` — source inspection: "EnginePool", "chess.engine", ".commit()", "bulk_update" all absent from the harness source
3. `test_gated_lte_ungated` — asserts gated counts <= ungated counts per orientation
4. `test_report_output` — asserts report file created with required section headers
5. `test_dropped_case_fields` — asserts each dropped case has orientation, motif_name, depth, pv_line, lichess URL starting with `https://lichess.org/analysis?fen=`
6. `test_lichess_url_encodes_fen` — unit tests the URL helper: spaces are `%20`, side flips by ply parity, different plys produce different URLs

## Verification Results

```
uv run pytest tests/scripts/test_ab_validate_gate.py -x -v
6 passed in 2.79s

uv run pytest -n auto -x
2995 passed, 18 skipped in 26.73s

uv run ruff format --check scripts/ab_validate_gate.py tests/scripts/test_ab_validate_gate.py
passed (clean)

uv run ruff check scripts/ab_validate_gate.py tests/scripts/test_ab_validate_gate.py
passed (0 errors)

uv run ty check app/ tests/
All checks passed!

grep -nE 'EnginePool|chess\.engine|\.commit\(|bulk_update' scripts/ab_validate_gate.py
(no matches — read-only, engine-free confirmed)

grep -n '_detect_tactic_for_flaw' scripts/ab_validate_gate.py
(match found — ungated arm wired)

grep -n '_classify_tactic_gated' scripts/ab_validate_gate.py
(match found — gated arm wired)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docstring contained banned sentinel strings**

- **Found during:** Task 2 (test_both_arms_use_same_blobs), runs 1-3
- **Issue:** The `test_both_arms_use_same_blobs` test does a substring check in the full module source (including docstrings). The initial module docstring contained "EnginePool", "bulk_update", and ".commit()" as negation examples ("does NOT instantiate EnginePool", "no bulk_update", "no session.commit()"), which tripped each check sequentially.
- **Fix:** Rephrased the opening docstring lines to convey the same intent without the banned substrings ("zero Stockfish calls, no chess engine instantiation", "no commits, no UPDATE statements").
- **Files modified:** scripts/ab_validate_gate.py (lines 3-4)
- **Commits:** Fixed inline before task commit 564479d2

**2. [Rule 1 - Bug] type: ignore does not suppress ty errors**

- **Found during:** Task 2, ty check gate
- **Issue:** The Wave 0 test scaffold (Task 1, commit c6097faf) used `# type: ignore[arg-type]` on the spy wrapper's `_real(...)` call. CLAUDE.md mandates `# ty: ignore[rule-name]` for ty suppression; mypy-style comments are ignored by ty, leaving 2 `invalid-argument-type` diagnostics.
- **Fix:** Changed to `# ty: ignore[invalid-argument-type]  # spy wrapper accepts object/str for broad capture`.
- **Files modified:** tests/scripts/test_ab_validate_gate.py (line 280)
- **Commit:** 564479d2 (bundled with Task 2 as a test-file correction)

**3. [Rule 1 - Bug] ruff: unused import `dataclasses.field`**

- **Found during:** Task 2, ruff check gate
- **Issue:** `from dataclasses import dataclass, field` — `field` was imported but never used (all dataclasses use default fields, no `field()` calls needed).
- **Fix:** `uv run ruff check --fix` removed the unused import automatically.
- **Files modified:** scripts/ab_validate_gate.py (line 35)
- **Commit:** 564479d2

## Known Stubs

None. The harness writes a HUMAN-UAT placeholder in the report for "False Negative Count" and "A/B Summary & Margin Justification" — those are intentional placeholders requiring the Plan 02 hand-check, not stubs that block this plan's goal (the measurement machinery itself is complete).

## Threat Flags

None. The harness introduces no new network endpoints, auth paths, or file access patterns beyond the existing `reports/retag/` report convention. T-144-01 (AGPL boundary) confirmed: harness only calls project-internal code, no lichess-puzzler source copied.

## Self-Check: PASSED

- [x] `scripts/ab_validate_gate.py` exists: FOUND
- [x] `tests/scripts/test_ab_validate_gate.py` exists: FOUND
- [x] Commit c6097faf exists: FOUND
- [x] Commit 564479d2 exists: FOUND
- [x] 6 tests GREEN
- [x] 2995 passed full suite
- [x] ty zero errors
- [x] ruff clean
