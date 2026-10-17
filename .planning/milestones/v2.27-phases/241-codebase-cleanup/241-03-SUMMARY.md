---
phase: 241-codebase-cleanup
plan: 03
subsystem: tooling
tags: [cleanup, comments, codemod, rename-map, decision-lookup, selftest]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger and the extras.py plugin hook"
provides:
  - "tools/extras.py: codemod, absent and decision commands, registered through register(subparsers) with 9 selftest cases"
  - "app/main.py, app/users.py, app/middleware/last_activity.py free of planning tags, with ledgers/241-03.txt"
affects: [241-05, 241-06, 241-07, 241-52, 241-67, 241-70]

actuals:
  tokens: 13000
  tasks: 2
  commits: 2
plan_head_before: ac91cbb7b07b3282d3dbe4459c01f34db7714098
plan_head_after: 1080f19b6fde43e78e0d64bddfdc2591c87c0e67

tech-stack:
  added: []
  patterns:
    - "Codemod works per prose line from cleanup.py's prose records, then refuses to write a file whose code tokens or lint directives would differ (T-241-05)"
    - "extras.py reaches cleanup.py through sys.modules['cleanup'] so selftest temp repos (set_root) apply to both modules"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/tools/extras.py
    - .planning/phases/241-codebase-cleanup/ledgers/241-03.txt
  modified:
    - app/main.py
    - app/users.py
    - app/middleware/last_activity.py

key-decisions:
  - "The codemod leaves a whole line untouched when any tag on it follows per/see/under/by/from/in/since/after/before/until/of/via/replaces/supersedes, rather than editing the other tags on that line"
  - "Capitalization after a removed leading tag is skipped on continuation lines (previous prose line does not end in . ! ? :), so a mid-sentence wrap never becomes a fake sentence start"
  - "A rewrite that would leave the line starting with punctuation (\"(D-07). Next\" becoming \". Next\") is not applied and is listed for hand edit"

patterns-established:
  - "Fan-out plan loop: rows -> codemod -> git diff -U0 review -> scan -> apply-edits batch (temp/241/*.json) -> scan/diff/ledger -> ruff/ty/source-scan tests -> commit"

requirements-completed: [D-10, D-11, D-12, D-15]

duration: 85min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 03: Toolkit Extras and app/main + app/users + app/middleware Summary

**`extras.py` adds a guarded tag codemod, a rename-map `absent` check and a `decision` lookup to cleanup.py without editing it, and the second backend slice (app/main.py, app/users.py, app/middleware) is clean with an empty token diff against PHASE_BASE.**

## Performance

- **Duration:** ~85 min
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 app files)

## Accomplishments

- `cleanup.py codemod [--dry-run]` rewrites the two safe tag shapes plus a leading group with a sentence-ending period, prints every changed line as a `before:` / `after:` pair, and lists everything it will not touch as `needs hand edit (reason)`. It never deletes a line, only edits text after a comment marker or inside a docstring span, and refuses to write any file whose code tokens or `noqa` / `ty: ignore` style directives would change.
- `cleanup.py absent --map FILE [--map FILE ...]` runs a whole-word `git grep --untracked` of every map row's `old` over that row's `absent_paths`; `-` rows are skipped; exit 1 on any hit.
- `cleanup.py decision PHASE D-NN` finds the CONTEXT.md in `.planning/phases/` or `.planning/milestones/*-phases/` (plain or zero-padded phase, `94.4` style included) and prints the bullet, heading section, table row or paragraph defining the decision; exit 1 with the searched globs otherwise.
- Selftest is now 24/24 (15 from 241-02, 9 new). The new cases cover every behavior bullet of the plan plus continuation lines, idempotence, the code-token guard, the dry-run/write command path, absent whole-word matching and untracked files, and decision lookup in active, archived and padded phases.

## Codemod line counts

| Run | Files | Lines changed by the codemod | Flagged "needs hand edit" |
|---|---|---|---|
| Dry run over scopes/241-05.txt (app/models), nothing written (`git status --porcelain app/models` empty) | 34 | 138 in 25 files | 185 (26 keyword-led, 159 other shapes) |
| Real run over scopes/241-03.txt | 5 | 21 in 3 files (app/main.py 12, app/users.py 8, app/middleware/last_activity.py 1) | 17 |

Hand edits in this slice: 23 `apply-edits` spans across the three files (22 in `temp/241/edits_03.json`, one re-wrap in `edits_03b.json`) covering the 17 flagged lines plus re-wrapping of the comments the codemod left with a short first line. `git diff -U0` was reviewed line by line after the codemod; none of the 21 codemod rewrites needed to be reverted.

Comments deleted as provenance only:

- `app/middleware/last_activity.py` lines 73-74: "CONTEXT.md D-08 ('last_activity isn't written yet') was stale; commit 2beabd3 wired the writes, and phase 62 adds the impersonation skip here." (history of a planning document, not a reason for the code)

History narration rewritten as a rule instead of deleted:

- `last_activity.py` "The tier-2 auto-enqueue that used to fire here was removed in Phase 118" became "Don't auto-enqueue evals from this middleware: the tier-3 ordering above already covers 'active users first'."

"per D-NN" replacements using the `decision` command:

- app/main.py reminder ticker: Phase 201 D-07 became "the claim UPDATE (claim the day first, then send) makes a double send structurally impossible across restarts and any future multi-process case."
- app/users.py: Phase 62 D-04/D-05 became "rejects nested impersonation" and "impersonating a superuser is rejected".

Canonical terms used where a comment was rewritten anyway (STYLE-GUIDE 3.3): "Cold-lane eval drain" became "Entry-ply eval drain" (row 33) and "Path-C-stamped holed games" became "attempt-cap-stamped holed games" (row 30).

## Ledger (ledgers/241-03.txt)

- INV-L351: APPLIED (finally-block comment names "any background task" and "all tasks"; the drain-spawn comment says stop_engine() runs after all background tasks are awaited; six tasks verified in `lifespan()`)
- INV-L352: APPLIED (insights Agent validated before orphan cleanup; verified `get_insights_agent()` precedes `cleanup_orphaned_jobs()`)
- INV-L392: APPLIED (`guest_service.create_guest_user` and `promote_guest_with_google` both still set `hashed_password=""`)

## Task Commits

1. **Task 1: extras.py with codemod, absent and decision (selftested)** - `21023da25` (`chore(241): toolkit extras (codemod, absent, decision)`; the commit lists only `extras.py`)
2. **Task 2: Clean app/main.py, app/users.py, app/__init__.py and app/middleware/** - `1080f19b6` (`chore(comments): app/main, app/users, app/middleware`)

**Plan metadata:** the SUMMARY commit follows these two (`commits: 2` above is measured with `git rev-list --count PLAN_HEAD_BEFORE..HEAD` before the SUMMARY commit).

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py selftest` | 24/24 passed |
| `cleanup.py scan --gate --scope scopes/241-03.txt` | exit 0 (5 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-03.txt` | exit 0 (5 selected, 3 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-03.txt --ledger ledgers/241-03.txt` | exit 0 |
| `ruff check app/`, `ruff check .planning/phases/241-codebase-cleanup/tools`, `ruff format --check` on the three app files | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean before the edits too) |
| `source_scan_tests.sh --py` | 95 + 5 passed |
| `pytest tests/test_main_lifespan.py tests/test_last_activity_middleware.py` | 25 passed |
| `cleanup.py decision 240 D-10`, `decision 94.4 D-13` | exit 0, text printed; `decision 777 D-13` exits 1 naming both searched globs |

app/__init__.py and app/middleware/__init__.py were already clean (scan found nothing), so they stay untouched, as the plan allows.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep for gates in a fresh worktree**
- **Found during:** Task 1 step 0
- **Issue:** `.venv` was missing in the new worktree, so ty would report phantom `onnxruntime` imports.
- **Fix:** `uv sync --group maia-inference` (lockfile only, no new packages); baseline `ruff check app/` and `ty check app/ tests/ scripts/` were clean before any edit.
- **Files modified:** none tracked

### Plan-text adaptations

**2. R1 also accepts a sentence-ending period as the separator.** The plan lists `:`, em dash, en dash and ` - `. Real app/models comments use "Phase 189 Plan 01 (POOL-04, D-06). One settings row per user", which the listed separators leave for hand editing. A `.` followed by whitespace and an uppercase letter is now accepted (selftest case included). It only fires when a tag group starts the prose text.

**3. Open-seed pointers are left unchanged and not listed.** The plan's behavior bullet groups "(see SEED-160) with SEED-160 open" with the "needs hand edit" cases. `scan` deliberately allows that pointer (D-12), so listing it would flag every legitimate pointer in all later plans. The selftest asserts the line is unchanged and that `scan`'s view of it is clean.

**4. Extra guards beyond the plan text.** Hyphenated first words ("per-game", "platform-reported") are capitalized; continuation lines are not capitalized; a result that would start with punctuation is not applied; the write is refused when the code token stream or directive multiset differs. All found by reviewing the 241-05 dry run before the real run.

**Total deviations:** 1 blocking environment prep, 3 plan-text adaptations.
**Impact on plan:** none on scope; no behavior in app/ changed.

## Issues Encountered

- `ruff format` rewrites the `—` escapes in extras.py regexes into literal em dashes; the file keeps them (they are the pattern being matched, not prose).
- The task-2 `rows` command lists the three INVENTORY rows only; INV-L354's other clause (app/users.py:203) belongs to 241-07 per the 241-02 summary and was not touched here.

## Known Stubs

None.

## Threat Flags

None. The codemod only writes comment and docstring text, verified by a token-stream and directive comparison before each write (T-241-05); every changed line is printed for review (T-241-06). No package installs beyond the lockfile sync.

## Notes for downstream plans

- Start each comment plan with `cleanup.py codemod --scope scopes/241-NN.txt --dry-run`, then without `--dry-run`, then `git diff -U0` review, then `scan` for the leftovers. Roughly 40 percent of tagged lines in a model-heavy scope are codemod-fixable; the rest are keyword-led references and labels like "D-06 eligibility watermark" that need a person.
- Flagged lines are never partially edited, so a rerun after hand edits is safe (the codemod is idempotent).
- FE files: the codemod uses generic `//`, `/* */`, `*` head and tail patterns on whatever `fe_support.prose` returns for kind `comment` (kind `test-title` is skipped). It was only exercised on Python here, since fe_support.py lands in 241-04; the first FE plan should run `--dry-run` and read the pairs before writing.
- `absent` expects the rename-map header `old new kind absent_paths ref canon_paths` and comma-separated `absent_paths`.

## Self-Check: PASSED

Files verified present: tools/extras.py, ledgers/241-03.txt, this SUMMARY. Commits verified as ancestors of HEAD: 21023da25, 1080f19b6.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
