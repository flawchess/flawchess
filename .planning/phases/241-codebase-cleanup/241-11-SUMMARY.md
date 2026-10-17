---
phase: 241-codebase-cleanup
plan: 11
subsystem: backend-comments
tags: [cleanup, comments, eval-pipeline, codemod, ledger]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "extras.py codemod, absent, decision"
provides:
  - "app/services/eval_apply.py free of planning tags, with the 22 INVENTORY section 6 rows applied"
  - "ledgers/241-11.txt covering all 22 rows"
affects: [241-53, 241-67]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: ab92f5162c1577613ff0c7fc4e2f1fdfdd89d5ca
plan_head_after: e70288fbc6cf69bf433dc6ee66a896439c717615

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-11.txt
  modified:
    - app/services/eval_apply.py

key-decisions:
  - "No rewritten comment asserts a single eval_cp ply convention or that no snapshot/restore exists anywhere: the diff/upsert docstring says preservation is a native property of the write and stops there"
  - "apply_full_eval banner placed above _game_row_exists (first helper of that section) rather than directly above commit_unless_game_deleted"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: 55min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 11: eval_apply.py Comment Cleanup Summary

**All 146 planning-tag matches and 22 INVENTORY rows in app/services/eval_apply.py are cleaned up (comments and docstrings only); `cleanup.py diff` against PHASE_BASE shows no code, string or directive change.**

## Accomplishments

- First `cleanup.py scan` listed 146 blocking matches (plus 114 lines the codemod could rewrite on its own); final `scan --gate` lists 0.
- Module docstring now states what the module owns plus the leaf rule (never import eval_drain or eval_remote) and drops the relocation narrative.
- Stale content fixed against the current code: "two of the three attempts" (MAX_EVAL_ATTEMPTS is 5), "4 call sites" (3, all overlay=True), "ALL continuation nodes" (even solver nodes only), `best_move` field docstring (never populated), the "delete-then-insert" wording (it is a diff/upsert), and the "Phase 118 wires cache invalidation" promise for a set nothing reads.
- No planning tags remain; `grep -n "delete-then-insert"` prints only the "not delete-then-insert" clause in the `_classify_and_fill_oracle` step list.

## Codemod vs hand edits

| | Lines |
|---|---|
| Codemod (`cleanup.py codemod`, written after reading the dry-run pairs) | 114 lines changed, 146 flagged "needs hand edit" |
| Hand edits via 4 pair batches (`temp/241-11/e1..e4.py`, scratch, gitignored) | 136 replaced spans covering the 146 flagged lines, the 22 inventory rows and a few neighbouring Sentry-id/quick-task prefixes |

Final diff against the base: 356 insertions, 425 deletions in eval_apply.py. The codemod output was reviewed line by line; none of its rewrites needed reverting.

## Ledger (ledgers/241-11.txt)

22 rows: 21 APPLIED (including the M row INV-L532, applied as written) and 1 MOVED, INV-L546 (paragraph deleted per the verifier, plus a note that `refresh_game_oracle_counts` has one caller, so the deleted "second public consumer" claim was stale). Two rows differ from the verifier text:

- INV-L550: banner moved above `_game_row_exists`, the first helper of the apply_full_eval section, not directly above `commit_unless_game_deleted` (that would have left `_game_row_exists` and `_T` outside their section).
- INV-L584: the verifier's "comment at 1327" (now the PV-line blob write comment in `_diff_upsert_flaw_rows`) also lost its "restore afterward" sentence; the `_classify_and_fill_oracle` docstring's snapshot/restore sentences were reworded as "preservation is a native property of the write". Nothing in the rewrite denies a snapshot/restore elsewhere.

## Gates

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-11.txt` | exit 0, 0 matches |
| `cleanup.py diff --scope scopes/241-11.txt` | exit 0, 1 file changed, no residue |
| `cleanup.py ledger --scope ... --ledger ledgers/241-11.txt` | exit 0 |
| `ruff check` / `ruff format --check` on eval_apply.py | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| source-scan tests, python half, run serially (no `-n`) | 95 + 5 passed (baseline identical) |
| `pytest tests/services/test_eval_apply.py` | 33 passed |

The frontend half of `source_scan_tests.sh` was not run: this plan touches no frontend file.

## Task Commits

1. **Task 1 + Task 2 (code file):** `9c831d34d` `chore(comments): app/services/eval_apply (tags and inventory rows)`
2. **Task 2 (ledger):** `e70288fbc` `chore(comments): app/services/eval_apply (inventory ledger)`

## Deviations from Plan

**1. [Plan note] Tasks 1 and 2 share one code commit.** The tag comments and the row-owned comments are interleaved in the same docstrings (for example `_classify_and_fill_oracle`, `apply_completion_decision`), so a clean split of eval_apply.py into a tags commit and a rows commit was not practical. The ledger is its own commit. The Task 1 acceptance item "scan lists only matches inside Task 2 row comments" is moot: scan lists nothing.

**2. [Environment] Serial source-scan run.** Per the dispatch instructions the python half of `source_scan_tests.sh` was run through a copy with `-n 4` removed (`temp/241-11/ssts_serial.sh`, gitignored), against the shared dev Postgres. Environmental, not a plan failure.

**3. [Rule 3 - Blocking] Fresh worktree setup.** `uv sync --group maia-inference` (lockfile only) so `ty` resolves onnxruntime. No tracked files changed.

**Total deviations:** 1 plan note, 1 environmental, 1 blocking env prep.

## Issues Encountered

- The worktree sandbox rejects heredocs and compound commands, so edit batches were written with the Write tool and applied by a small scratch script (`temp/241-11/ed.py`, exact-match pairs that must occur once).
- Several flagged lines had already been rewritten by the codemod; a few pairs written from the dry-run output matched zero times and were dropped.

## Known Stubs

None.

## Observations for later plans (no action here)

- `FLAW_BLOB_COLUMNS`, `_out_of_book_ply_count`, `refresh_game_oracle_counts`, `on_path_c_capacity_reached`, `stored_eval_predates_engine` and "oracle counts" wording keep their current names (renamed by 241-53 and 241-67).
- Sentry issue ids (FLAWCHESS-6B, -8D, -9F, -8G, -5V, -8W, -A0) in comments are not planning tags under D-11 and were left, except the two removed beside quick-task ids.
- The `# FLAWCHESS-8D: ... not the silent no-op an earlier docstring assumed` comment in `_diff_upsert_flaw_rows` is mild history narration, left unchanged (not inventoried).
- INVENTORY section 7.1 seeds 6 (write-only `_recently_flaw_completed_users`) and 7 (dead `_FullPlyEvalTarget.best_move`) were re-confirmed against the code; the code stays untouched.

## Threat Flags

None. No code, string, directive or schema change.

## Self-Check: PASSED

Files verified present: app/services/eval_apply.py, ledgers/241-11.txt, this SUMMARY. Commits 9c831d34d and e70288fbc are ancestors of HEAD.
