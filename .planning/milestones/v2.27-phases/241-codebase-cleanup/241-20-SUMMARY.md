---
phase: 241-codebase-cleanup
plan: 20
subsystem: testing
tags: [cleanup, comments, tests, tactic-detector, flaws-service, test-names]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "Planning-tag-free comments, docstrings and test names in the eight tactic and flaw service test files"
affects: [241-56]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2
plan_head_before: d8638e30db9f3936cfca659218c6bce4a80b7e81
plan_head_after: 173a93bca242a048b62da4f0c15ac14800a46c41

tech-stack:
  added: []
  patterns:
    - "Line-addressed edit spec (N<TAB>new text, <DEL> to delete) applied by a scratch script against the original line numbers, so a whole file is edited in one pass without line drift"

key-files:
  created: []
  modified:
    - tests/services/test_tactic_detector.py
    - tests/services/test_forcing_line_gate.py
    - tests/services/test_flaws_service.py
    - tests/services/test_flaw_comparison.py
    - tests/services/test_flaw_delta_zones.py
    - tests/services/test_flaw_upsert_equivalence.py
    - tests/services/test_tactic_comparison_service.py
    - tests/services/test_tactic_delta_zones.py

key-decisions:
  - "Assert messages and other string literals that still carry tags (for example 'D-03: a below-floor allowed fallback eval must suppress') were left as they are: the plan forbids any string change in test code, and scan does not read string literals"
  - "Untagged-by-regex but planning-flavoured test names (test_tagfix02_*) were renamed along with the regex-flagged ones, so no test name keeps a planning pointer"
  - "Comments contradicted by the code were fixed instead of only de-tagged (STYLE-GUIDE 2.2): see Deviations"

patterns-established:
  - "Mechanical regex pass for the repeated fixture annotation 'Reclassified Phase 133:' before hand edits (49 lines in test_tactic_detector.py)"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 95min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 20: Tactic and Flaw Service Test Comment Cleanup Summary

**Planning tags (Phase/Plan/D-NN/quick-task ids/REQ ids/Pitfall/RESEARCH) are gone from comments, docstrings and test names of the eight tactic and flaw service test files, with 452 tests collected before and after, all green, and an empty non-comment token diff.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 2
- **Files modified:** 8 (tests only)

## Accomplishments

- `test_tactic_detector.py` and `test_forcing_line_gate.py`: 0 scan matches (first scan listed 322 lines for the two files; the codemod rewrote 105 + 33 lines, the rest was hand edits).
- The six flaw/tactic comparison files: 0 scan matches (first scan listed 159 lines; codemod fixed 74, the rest was hand edits).
- `cleanup.py scan --gate --scope scopes/241-20.txt` exit 0 (8 files, 0 matches); `cleanup.py diff --scope scopes/241-20.txt` exit 0 (8 selected, 8 changed, no residue).

## Task Commits

1. **Task 1: test_tactic_detector.py and test_forcing_line_gate.py** - `b62b32bae` (`chore(comments): tests/services tactic detector and forcing-line gate`)
2. **Task 2: the six flaw/tactic comparison test files** - `173a93bca` (`chore(comments): tests/services flaw and tactic comparison tests`)

`commits: 2` is measured with `git rev-list --count d8638e30d..HEAD` before the SUMMARY commit.

## Collection counts (before = after)

| Files | Before | After |
|---|---|---|
| test_tactic_detector.py + test_forcing_line_gate.py | 203 | 203 |
| the six flaw/tactic comparison files | 249 | 249 |
| whole scope, run: 445 passed, 7 skipped | 452 | 452 |

## Renamed tests and classes (old -> new)

| Old | New |
|---|---|
| `TestDiscoveredAttackD11PortFixes` | `TestDiscoveredAttackRecaptureAndDepth` |
| `test_deficit_recovered_at_k_plus_3_still_fires_after_d05_retirement` | `test_deficit_recovered_at_k_plus_3_still_fires` |
| `TestSeed044PostMoveConvention` | `TestPostMoveEvalConvention` |
| `test_d03_fallback_allowed_below_floor_suppressed` | `test_fallback_allowed_below_floor_suppressed` |
| `test_d03_fallback_missed_below_floor_suppressed` | `test_fallback_missed_below_floor_suppressed` |
| `test_d03_fallback_allowed_winning_eval_credited` | `test_fallback_allowed_winning_eval_credited` |
| `test_d03_fallback_missed_winning_eval_credited` | `test_fallback_missed_winning_eval_credited` |
| `test_d03_fallback_both_columns_none_credited` | `test_fallback_both_columns_none_credited` |
| `test_d03_sentinel_empty_blob_with_losing_eval_still_credited` | `test_sentinel_empty_blob_with_losing_eval_still_credited` |
| `test_tagfix02_gate_runs_on_none_cp_non_forcing_blob_suppressed` | `test_gate_runs_on_none_cp_non_forcing_blob_suppressed` |
| `test_tagfix02_forced_mate_for_solver_rejects_non_mate_motif_white` | `test_forced_mate_for_solver_rejects_non_mate_motif_white` |
| `test_tagfix02_forced_mate_for_solver_rejects_non_mate_motif_black` | `test_forced_mate_for_solver_rejects_non_mate_motif_black` |
| `test_tagfix02_mate_motif_exempt_via_forced_mate_firing_node` | `test_mate_motif_exempt_via_forced_mate_firing_node` |
| `test_tagfix02_both_pre_flaw_cp_and_mate_none_gate_still_runs` | `test_both_pre_flaw_cp_and_mate_none_gate_still_runs` |
| `test_tagfix02_mate_against_solver_not_an_already_winning_reject` | `test_mate_against_solver_not_an_already_winning_reject` |

`git grep` for every old name outside `.planning` returns no reference to these tests (the three `test_d03_net_*` hits in `tests/scripts/test_engine_dispatch_227_verdict.py` are different tests owned by another plan). No `-k` selector, CI step or doc named any of them. No new name collides with an existing name in its module (`cleanup.py diff` would flag it).

## Codemod versus hand edits

| Step | Lines |
|---|---|
| `cleanup.py codemod` (Task 1 files) | 138 (105 + 33) |
| `cleanup.py codemod` (Task 2 files) | 74 |
| Mechanical regex pass ("Reclassified Phase 13x:" fixture annotations, comment lines only) | 49 |
| Hand-edit spec lines, test_tactic_detector.py | 191 |
| Hand-edit spec lines, test_forcing_line_gate.py | 37 |
| Hand-edit spec lines, six comparison files | 58 + 7 + 2 + 11 + 2 + 12 + 2 + 38 = 132 |
| Single-line `sed` follow-ups after the final broad grep | 16 |

`git diff -U0` was reviewed after the codemod in both tasks. Codemod output that read badly (a lowercase comment start after a removed tag, for example "# the gate no longer skips merely because") was rewritten by hand. The known codemod bug (a comment collapsing to bare punctuation) did not occur: the `^\s*#\s*[:;,]\s` grep over all eight files finds nothing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, STYLE-GUIDE 2.2] Comments contradicted by the code were corrected, not just de-tagged**
- **Found during:** Task 1 and Task 2 hand edits
- **Issue and fix:**
  - `test_forcing_line_gate.py` docstring said the already-winning reject fires at "> 600 cp"; `ALREADY_WINNING_CP_THRESHOLD` is 800 and the test file asserts it. Now "> 800 cp".
  - `test_tactic_detector.py` comment block above `_VALIDATED_FIXTURE_SETS` said attraction "moved from _VALIDATED to _SUPPRESSED" although `"attraction"` is in `_VALIDATED_IDS`; the three stale lines were deleted (the correct rationale sits right above them).
  - `test_tactic_detector.py` trapped-piece header said an empty escape set is "NOT trapped (precision-first deviation from cook)"; the test below it asserts it IS trapped, matching cook. Fixed.
  - `test_flaw_upsert_equivalence.py` docstring said the write path is "delete-then-insert" and a tautology until a later plan swaps in a diff/upsert; `_classify_and_fill_oracle` already is the per-ply diff/upsert (verified in `app/services/eval_apply.py`). Rewritten as present tense.
  - `test_tactic_comparison_service.py` family-mapping docstring narrated five quick-task and phase steps (10 -> 15 -> 17 -> 19 -> 20 -> 19); replaced by the present-tense list of families and the reason clearance is unmapped.
- **Files modified:** the four files above
- **Verification:** tests green; no code token changed (`cleanup.py diff` exit 0)
- **Commits:** b62b32bae, 173a93bca

**2. [Plan note] Planning prose beyond the scan regex was also removed**
- The scan regex misses shapes such as `Quick 260623`, `Plan 128.1`, `Workstream B`, `Bug A/B`, `Task 2`, `T-221-04-02`, `UAT`, `CONTEXT.md`, `project_asyncpg_jsonb_null_vs_sql_null` and `(see 132-02-SUMMARY.md)`. A broad grep over the scope found them in comments and docstrings and they were cleaned too.

### Known leftovers (intentional)

- String literals (assert messages, fixture strings) that still carry tags, because the plan forbids any string change: for example `"D-03: a below-floor allowed fallback eval must suppress"`, `"This fails RED with the voting detector. (Phase 132 D-01)"`, `"(221-D13-SPOTCHECK.md) ..."`, `"Post-move convention must detect the h3 blunder at ply 14 (SEED-044)."`. They are visible only when a test fails. If the owner wants them gone, that is a separate test-text change.
- `test_flaws_service.py` still uses the parameter name `user_result` in the surrounding code (renamed later by 241-56, as the plan notes); only the tag next to it was removed.
- No `allow/241-20.tsv` was needed: no scan match was a false positive, and no `d10`-style domain-vocabulary name part occurred.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-20.txt` | exit 0 (8 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-20.txt` | exit 0 (8 selected, 8 changed, no residue) |
| `ruff check tests/services`, `ruff format --check tests/services` | clean (69 files already formatted) |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean before any edit) |
| `pytest -q -p no:warnings` over the 8 test files, serial | 445 passed, 7 skipped |

Environmental: pytest was run serially (no `-n`), as the parallel-execution notes require for the shared dev Postgres; the plan's `-n 4` form was not used. `uv sync --group maia-inference` was run once for the fresh worktree (lockfile only, no new packages).

## Known Stubs

None.

## Threat Flags

None. Only comments, docstrings and test names changed; T-241-36 is mitigated by the empty token diff, equal collection counts and the passing run above.

## Self-Check: PASSED

Files verified present: the eight test files, this SUMMARY. Commits verified as ancestors of HEAD: b62b32bae, 173a93bca.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
