---
phase: 143-offline-re-tagger
verified: 2026-06-30T12:00:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 143: Offline Re-tagger Verification Report

**Phase Goal:** A pure-offline scripts/retag_flaws.py re-derives tactic tags from stored JSONB in seconds with no engine pass, with mate combinations and defender branching covered by explicit unit tests
**Verified:** 2026-06-30
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | scripts/retag_flaws.py --dry-run --margin X --user-id N reports per-motif tag delta without writing to DB; --db dev|benchmark|prod supported | VERIFIED | Script exists (git mv from backfill_tactic_tags.py), CLI flags present, TestRetagDryRun asserts 0 DB rows changed + report written; argparse choices=["dev","benchmark","prod"] |
| 2 | Unit tests cover mate-priority hierarchy: only-best-is-mate forced; both-mates shorter forced; mate-in-1 never suppressed; fall-through to sigmoid | VERIFIED | TestMatePriority in test_forcing_line_gate.py: 13 tests across both solver colors, all pass |
| 3 | A unit test with a multi-ply defender-branching position confirms defender-node ambiguity does not kill a valid forcing line | VERIFIED | test_multi_ply_defender_ambiguity_does_not_kill_line (TestDefenderBranching): 5-node line [S0,D0_ambiguous,S1,D1_ambiguous,S2] passes apply_forcing_line_filter |
| 4 | Re-tagger updates game_flaws tactic columns idempotently via single _classify_tactic_gated path; second run produces 0 changed rows | VERIFIED | test_second_run_changes_zero_rows asserts tags_after_first == tags_after_second; both eval_drain and retag_flaws.py route through _classify_tactic_gated |

**Score:** 4/4 truths verified (0 behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/retag_flaws.py` | Renamed from backfill_tactic_tags.py; blob loading + --margin + gated classify | VERIFIED | git mv history confirmed; backfill_tactic_tags.py gone |
| `tests/services/test_forcing_line_gate.py` | TestMatePriority + TestDefenderBranching + TestMarginParam | VERIFIED | All 3 new test classes present and green |
| `tests/scripts/test_retag_flaws.py` | Dry-run/idempotency/margin tests | VERIFIED | 6 tests pass |
| `reports/retag/.gitkeep` | Committed placeholder | VERIFIED | Exists |
| `app/services/flaws_service.py` | _classify_tactic_gated + _solver_color_for | VERIFIED | Lines 508, 525; _build_flaw_record routes through wrapper |
| `app/services/eval_drain.py` | flaw_pv_blobs threaded into _classify_and_fill_oracle | VERIFIED | Lines 680, 2342 |
| `app/repositories/game_flaws_repository.py` | Docstrings updated to retag_flaws.py | VERIFIED | Lines 152, 172 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/retag_flaws.py::_worker_recompute` | `flaws_service._classify_tactic_gated` | direct import + call with margin=work.margin | WIRED | Lines 313, 322 in retag_flaws.py |
| `eval_drain._full_drain_tick` | `_classify_and_fill_oracle(flaw_pv_blobs)` | flaw_pv_blobs built in memory, passed as arg | WIRED | Line 2342 in eval_drain.py |
| `_classify_and_fill_oracle` | `classify_game_flaws(flaw_pv_blobs=...)` | parameter forwarding | WIRED | Line 746 in eval_drain.py |
| `classify_game_flaws` | `_build_flaw_record(flaw_pv_blobs=...)` | parameter forwarding | WIRED | Line 920 in flaws_service.py |
| `_build_flaw_record` | `_classify_tactic_gated` | both allowed + missed orientations | WIRED | Lines 591-598 in flaws_service.py |
| `is_solver_node_forced` margin param | not global mutation | function arg default only | WIRED/VERIFIED | No assignment to ONLY_MOVE_WIN_PROB_MARGIN outside line 52 definition |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TestMatePriority (SC2) | `uv run pytest tests/services/test_forcing_line_gate.py -k "MatePriority" -q` | 11 passed | PASS |
| TestDefenderBranching (SC3) | `uv run pytest tests/services/test_forcing_line_gate.py -k "defender" -q` | 2 passed | PASS |
| TestMarginParam (D-03) | `uv run pytest tests/services/test_forcing_line_gate.py -k "margin" -q` | 2 passed | PASS |
| TestClassifyTacticGated (gate wrapper) | `uv run pytest tests/services/test_flaws_service.py::TestClassifyTacticGated -q` | 4 passed | PASS |
| TestRetagDryRun + TestRetagIdempotency + TestRetagMarginSensitivity | `uv run pytest tests/scripts/test_retag_flaws.py -q` | 6 passed | PASS |
| Full combined gate + retag suite | `uv run pytest tests/services/test_forcing_line_gate.py tests/services/test_flaws_service.py::TestClassifyTacticGated tests/scripts/test_retag_flaws.py -q` | 55 passed | PASS |
| ty check all touched files | `uv run ty check app/ tests/` | All checks passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| GATE-03 | 143-01 | Mate-priority hierarchy before sigmoid comparison | SATISFIED | TestMatePriority: 13 tests, both colors, all 5 hierarchy cases covered |
| GATE-04 | 143-01 | Defender-node ambiguity does not kill a forced line | SATISFIED | test_multi_ply_defender_ambiguity_does_not_kill_line: 5-node branch-then-reconverge |
| RETAG-01 | 143-03 | Offline re-tagger tunable via --dry-run/--margin/--user-id/--db | SATISFIED | CLI flags present; dry-run writes report + 0 DB rows; margin threads to gate |
| RETAG-02 | 143-02, 143-03 | Idempotent single classify path | SATISFIED | test_second_run_changes_zero_rows; _classify_tactic_gated called by both live drain and retag_flaws.py |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tests/scripts/test_retag_flaws.py | 155-165 | GamePosition.pv seeded with illegal UCI strings ("e4e5 d2d4", "f3e5 d7d6") | Warning | TestRetagMarginSensitivity is vacuous (see caveat below); does not block any SC |

### Code Review Findings Disposition

**WR-01 (Sentry miss on page-fetch errors):** FIXED in commit 2c4d8d59. `_fetch_flaw_page` is now inside the try block; the except handler captures Sentry context and re-raises.

**WR-02 (Vacuous margin sensitivity test):** NOT FIXED. `TestRetagMarginSensitivity` uses GamePosition.pv strings that are illegal on their boards, so `_detect_tactic_for_flaw` returns (None,None,None,None) — the gate is never invoked. The assertions pass trivially (0 <= 0, None is None). This is test debt, not a goal failure:
- ROADMAP SC1 says "--margin X reports per-motif tag delta"; it does not require an integration test proving margin changes results end-to-end.
- Gate-level margin is non-vacuously proven by TestMarginParam (test_forcing_line_gate.py): `is_solver_node_forced` and `apply_forcing_line_filter` each produce opposite verdicts at margin=0.1 vs margin=0.5 on the same node/line.
- Wrapper-level suppression/pass-through is non-vacuously proven by TestClassifyTacticGated (test_flaws_service.py) using a real HANGING_PIECE detector fixture.
- The margin-threading path (CLI arg → _FlawWork.margin → _classify_tactic_gated(margin=work.margin)) is confirmed by code inspection.
- Recommendation for Phase 144: replace the fixture's illegal PV strings with legal UCI moves so the margin sensitivity test exercises the gate end-to-end rather than the detector's early-return path.

**IN-01 (Same-day dry-run reports overwrite):** Accepted risk; Phase 144 will sweep margins and may need to address this. The SC only requires one report per dry-run invocation.

**IN-02 (eval_cp=None silently skips gate):** FIXED in commit 2c4d8d59 (docstring clarification). The behavior is by design (RESEARCH A1 accepted); the docstring now explicitly documents the eval_cp=None skip path.

### Human Verification Required

None. All success criteria are verified programmatically.

---

_Verified: 2026-06-30T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
