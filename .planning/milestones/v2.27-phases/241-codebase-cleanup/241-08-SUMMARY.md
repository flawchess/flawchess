---
phase: 241-codebase-cleanup
plan: 08
subsystem: backend-comments
tags: [cleanup, comments, train, push, feedback, repositories]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/rows/ledger"
  - phase: 241-03
    provides: "extras.py codemod and decision"
provides:
  - "Train, push and feedback repositories (7 files) free of planning tags, with the 13 INVENTORY rows applied"
  - "ledgers/241-08.txt"
affects: [241-52]

actuals:
  tokens: 22000
  tasks: 2
  commits: 2
plan_head_before: 1f4abf6c07a363924ec447adf6c286138656cd3b
plan_head_after: 04d54203bb0574f13dc6956fffca4100d04061d7

tech-stack:
  added: []
  patterns:
    - "Line-range edit batches built from the live file (temp/241/ed.py) so apply-edits never needs hand-typed old text"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-08.txt
  modified:
    - app/repositories/train_repository.py
    - app/repositories/train_reminder_repository.py
    - app/repositories/train_medals_repository.py
    - app/repositories/train_leaderboard_repository.py
    - app/repositories/push_repository.py
    - app/repositories/feedback_repository.py
    - app/repositories/feedback_ask_repository.py

key-decisions:
  - "Rows whose claim was stale in a second place got the same fix there (the '(never backfilled)' parenthetical also sat in the _assemble_session_items docstring)"
  - "Out-of-repo pointers (.planning decision files, RESEARCH files, owner memory notes, stale file:line references) were replaced by the explanation or dropped, not kept as tags"

requirements-completed: [D-01, D-03, D-10, D-11, D-12, D-13, D-15]

duration: ~75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 08: Train, push and feedback repository comments Summary

**Comments and docstrings of the seven Train/push/feedback repositories now describe the current design (SR + herring composition, sharp-filler shortfall fill, reminder claim) with no planning tags, and the token diff against PHASE_BASE is empty.**

## Accomplishments

- `train_repository.py` (the layered 189 -> 192 -> 206 -> 211 file): all bare tags gone. `cleanup.py scan` went from 298+ tagged lines to 0 matches.
- The composition comments no longer describe retired backfill arms: the herring cap comment now says a short SR side is filled by sharp fillers after reconstruction, the `_backfill_sharp_fillers` docstring states what the stage does, and the compose docstring steps 4 and 5 match the code (INV-L469, L521, L522).
- All 13 INVENTORY section 6 rows are APPLIED, each re-verified against the current code first (see ledgers/241-08.txt). None was skipped or left.
- Rewritten Train prose says "puzzle" for an exercise; `drill_*` tables/models and the SR `item` bookkeeping names are untouched.

## Codemod vs hand edits

| File | Codemod-changed lines | Hand-edited spans |
|---|---|---|
| train_repository.py | 156 (before review; the codemod leaves some orphaned sentence fragments, all fixed by hand) | 152 in Task 1 (tags) + 23 in Task 2 (rows and leftovers) |
| train_reminder_repository.py | 6 | 9 |
| train_medals_repository.py | 7 | 0 |
| train_leaderboard_repository.py | 2 | 2 |
| push_repository.py | 3 | 3 |
| feedback_repository.py | 0 | 1 |
| feedback_ask_repository.py | 0 | 3 |

Row-owned comments were left alone in Task 1 (commit 1), as the plan asks; `scan` after Task 1 listed only those (module docstring lines 3-6, ProgressSnapshot, `_resume_session`, `_select_candidates` args plus `_backfill` comment, `_classify_and_certify_solve`), all handled in Task 2.

## Task commits

1. Task 1: `e58ce79bd` `chore(comments): app/repositories/train_repository (tags)`
2. Task 2: `04d54203b` `chore(comments): app/repositories (train, push, feedback)` (six small files, 13 rows, ledger)

`commits: 2` above is `git rev-list --count 1f4abf6c0..HEAD` measured before the SUMMARY commit.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-08.txt` | exit 0 (7 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-08.txt` | exit 0 (7 selected, 7 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-08.txt --ledger ledgers/241-08.txt` | exit 0 |
| `ruff check app/repositories`, `ruff format --check app/repositories` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| `source_scan_tests.sh --py` | 95 + 5 passed |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` (lockfile only) before the baseline gates; no tracked files changed.

**2. [Rule 2 - stale content, STYLE-GUIDE 2.2] Fixes next to inventoried rows or tags that the inventory did not list**
- `_assemble_session_items` docstring had the same stale "(never backfilled - the slot arithmetic already ran)" as the compose docstring (INV-L469); fixed identically, and its mis-indented "Sharp filler fills EVERY residual shortfall" paragraph (a codemod artifact) was re-indented.
- `_select_candidates` args and `_SessionCandidates` docstring carried `D-02` / `Phase 206 e0` tags outside any row; removed.
- Three "memory project_..." pointers (owner notes, not repo files) in `record_solve` and `reveal_for_puzzle` replaced by the explanation or by "see the telemetry comment above".
- `get_waiting_puzzle_count`, `_pool_state`, `completed_session_in_window`, `load_session_puzzles`, `_mark_session_complete_if_done`: history narration ("used to run", "can no longer be an INNER JOIN", "went from NOT NULL + CASCADE", "now excluded") rewritten in present tense.
- `push_repository.MOBILE_USER_AGENT_PATTERN`: the pointer to `useInstallPrompt.isMobile` now names `isMobileUserAgent` in `lib/deviceClass.ts`, which holds the same regex (re-verified).
- `train_reminder_repository`: dropped the pointer to `204-DECISIONS.md`; `D-04` became "the retry semantics the job deliberately avoids" (decision lookup: no retry on transient push failure); the "as of Phase 224" guest-exclusion wording became present tense (Train routes accept guests, verified in app/routers/train.py).
- `feedback_ask_repository`: dropped the `234-RESEARCH.md` pointer, kept the "verified in exactly this shape against Postgres 18" claim.

**3. [Process slip, fixed in-task] Off-by-one in my first rows batch**
- The row batch left seven duplicated tail lines (one per block). Caught by reviewing `git diff -U0`, deleted in the same task before any gate ran; the committed diff has none.

**Total deviations:** 1 blocking env prep, 1 batch of stale-content fixes, 1 self-corrected slip. No code token changed (`diff` exit 0).

## Issues Encountered

- First `source_scan_tests.sh --py` run reported one error (`tests/test_push_send.py::test_send_to_user_fan_out_prunes_only_the_410_not_the_500`, `database "flawchess_test_gw3" does not exist`). The test DB names `flawchess_test_gw0..gw3` are shared by all concurrent wave-3 worktrees on one Postgres, so a sibling executor's session teardown dropped the DB. Rerun passed (95 + 5), nothing in this plan's files was involved.
- The worktree sandbox rejects compound shell lines that mention git; commands were issued one at a time.

## Non-inventoried follow-ups (not done, out of scope)

- `_override_for_key_move` keeps its current name in comments (renamed later by 241-52).
- `_assemble_session_items` docstring step 5 and the following "Sharp filler fills EVERY residual shortfall" paragraph now say nearly the same thing twice; merging them is a rewrite beyond this plan's "only the reason that replaces a tag" rule.

## Known Stubs

None.

## Threat Flags

None. Only comments and docstrings changed; `cleanup.py diff` compared every SQLAlchemy and `text()` token against PHASE_BASE with zero residue (T-241-16). No package installs.

## Self-Check: PASSED

Files verified present: ledgers/241-08.txt and the seven repositories. Commits e58ce79bd and 04d54203b are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
