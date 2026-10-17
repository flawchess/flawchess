---
phase: 241-codebase-cleanup
plan: 02
subsystem: tooling
tags: [cleanup, comments, python-tokenize, ast, git-diff, selftest]

requires: []
provides:
  - "tools/cleanup.py: scan, apply-edits, diff (incl. --outside), outside, rows, ledger, selftest for Python files, with plugin hooks for fe_support.py (241-04) and extras.py (241-03)"
  - "tools/source_scan_tests.sh: one command that runs every test reading app/ or frontend/src source text"
  - "tools/PHASE_BASE: 3bce9acb621d80e08d0ae296e01efcea0a351049, the commit every phase diff compares against"
  - "app/core/ comment cleanup (29 tagged lines gone) with ledgers/241-02.txt"
affects: [241-03, 241-04, 241-05, 241-52, 241-67, 241-70]

actuals:
  tokens: 17000
  tasks: 2
  commits: 3
plan_head_before: 3bce9acb621d80e08d0ae296e01efcea0a351049
plan_head_after: 974f99e2c90b014ebc8ded617a686313df2060da

tech-stack:
  added: []
  patterns:
    - "Token-stream diff against a pinned base: comments, docstring statements and test function/class names dropped, rename maps applied to both sides"
    - "Commands register with parser.set_defaults(func=fn); plugins imported lazily from tools/"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/tools/cleanup.py
    - .planning/phases/241-codebase-cleanup/tools/source_scan_tests.sh
    - .planning/phases/241-codebase-cleanup/tools/PHASE_BASE
    - .planning/phases/241-codebase-cleanup/ledgers/241-02.txt
  modified:
    - app/core/config.py
    - app/core/database.py
    - app/core/feedback_rate_limiter.py
    - app/core/ip_rate_limiter.py
    - app/core/platform_usernames.py
    - app/core/reset_password_rate_limiter.py

key-decisions:
  - "Prose and token records are plain tuples (Prose = 6-tuple line, col, end_line, end_col, kind, text; token = (kind, text, line)) so FE plugins can return the same shapes without importing cleanup.py"
  - "Relative command-line paths resolve against the cwd when it lies in the checkout, otherwise against the checkout root, so repo-relative paths in scope files, edit batches and ledgers work from any directory and the selftest can run in a temp repo"
  - "diff flags a renamed test that collides with an existing name in the same scope (duplicate definition): pytest would silently shadow one of them, and the test-name normalization alone cannot see it"
  - "FE-suffixed files in a scan or diff selection fail fast with 'FE support is added by 241-04' even when the file is unchanged"

patterns-established:
  - "Tracer loop: scan -> apply-edits batch (temp/241/*.json) -> diff -> rows/ledger -> gates -> commit; proven on app/core"
  - "Gates proven non-vacuous on the committed tree by a live mutation (one code token, one injected tag comment)"

requirements-completed: [D-10, D-11, D-12, D-13, D-14, D-15]

duration: 62min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 02: Cleanup Toolkit and app/core Tracer Summary

**A stdlib-only scan/apply-edits/diff/ledger toolkit for the comment-cleanup fan-out, proven end to end on app/core/ where all 29 planning-tag lines are gone and the token diff against PHASE_BASE is empty.**

## Performance

- **Duration:** ~62 min
- **Started:** 2026-10-16T14:46Z
- **Completed:** 2026-10-16T15:48Z
- **Tasks:** 2 (tracer + hardening)
- **Files modified:** 10 (4 created, 6 app/core files)

## Accomplishments

- `cleanup.py` implements the 241-02 CLI contract: `scan [--gate] [--allow] [--identifiers] [--advisory]`, `apply-edits`, `diff [--base] [--allow] [--outside PATH]`, `outside`, `rows`, `ledger`, `selftest`, plus lazy hooks for `fe_support.py` and `extras.py`.
- app/core/ cleaned by `apply-edits` batch: first scan listed 29 matches (>= 25 required), final `scan --gate` lists 0.
- INVENTORY rows INV-L353, L354 (primary clause), L393, L407 applied after re-verifying each against the current code; INV-L341 DEFERRED to 241-52.
- `source_scan_tests.sh` runs the source-text tests: py part 95 + 5 passed, fe part 9 files / 131 tests passed.
- selftest has 15 cases; a mutation run over the tool itself killed 10 of 11 mutants (the survivor is an equivalent mutant).

## Task Commits

1. **Task 1: Thinnest working toolkit run for real on app/core/** - `7dba18f00` (toolkit + ledger + PHASE_BASE), `b3f77d31e` (`chore(comments): app/core`)
2. **Task 2: Harden the toolkit** - `974f99e2c` (selftest, allow lists, identifiers, plugin hooks, `--outside`, `outside`, source-scan runner)

**Plan metadata:** the SUMMARY commit follows these three (`commits: 3` above is measured with `git rev-list --count PLAN_HEAD_BEFORE..HEAD` before the SUMMARY commit).

## Tool commands and exit codes (final tree)

| Command | Exit |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-02.txt` | 0 (13 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-02.txt` | 0 (13 selected, 6 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-02.txt --ledger ledgers/241-02.txt` | 0 |
| `cleanup.py selftest` | 0 (15/15) |
| `cleanup.py diff --outside scripts/tactic_tagger_report.py --outside .claude/skills/tactic-tagger-report/SKILL.md` | 0 (both unchanged since PHASE_BASE) |
| `cleanup.py diff scripts/tactic_tagger_report.py` | 2 (out-of-scope positional path) |
| `cleanup.py diff frontend/src/main.tsx` | 2, "FE support is added by 241-04" |
| `cleanup.py outside` | 0, prints nothing |
| `cleanup.py scan --identifiers app/` (identifier lines only) | `app/services/stats_service.py:484` and `:572`, `_phase80_item_from_metrics` (definition and use), nothing else |
| `ruff check app/core tools`, `ruff format --check app/core`, `ty check app/ tests/ scripts/` | all clean |

## Mutation checks (not vacuous)

Run on the committed tree, then restored with `git checkout -- app/core/http.py`:

```
$ sed -i 's|^USER_AGENT = \(.*\)$|USER_AGENT = \1 + ""|' app/core/http.py
$ cleanup.py diff --scope scopes/241-02.txt
diff: 13 files selected, 7 changed
app/core/http.py:7: -  / + + ""            (Task 1 preview format; now rendered "- (none) / + + """)
exit 1
(restored)  $ cleanup.py diff --scope ...   -> exit 0

$ echo '# Phase 123 test' >> app/core/http.py
$ cleanup.py scan --gate --scope scopes/241-02.txt
scan: 13 files, 1 matches
app/core/http.py:8:comment: # Phase 123 test
exit 1
(restored)  $ cleanup.py scan --gate --scope ...   -> exit 0, 0 matches
```

The plan suggested a trailing `+ 0` on a numeric constant; http.py holds only the `USER_AGENT` string, so the one-token edit appended `+ ""` instead. Same effect (a code token added), same exit 1.

## Ledger (ledgers/241-02.txt)

- INV-L341: DEFERRED to 241-52 (lands with the `is_allowed` rename; the tag comment at ip_rate_limiter.py:34 was cleaned here)
- INV-L353: APPLIED (config.py EVAL_AUTO_DRAIN_ENABLED comment; re-verified against `claim_eval_job`)
- INV-L354: APPLIED primary clause; the app/users.py:203 clause belongs to 241-07
- INV-L393: APPLIED (backfill_eval now lives under scripts/archive/; reindex_table and gen_benchmarks still call `db_url_for_target`)
- INV-L407: APPLIED (last sentence deleted)

Allow-list entries: none were needed for app/core (no `allow/241-02.tsv`).

## Decisions Made

See `key-decisions` above. Beyond the plan text: the record-shape convention for plugins, cwd-or-root path resolution, the duplicate-test-name residue, and fail-fast FE detection at selection time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep for gates in a fresh worktree**
- **Found during:** Task 1 gates / Task 2 source-scan tests
- **Issue:** `uv run ty check` reported phantom `onnxruntime` unresolved imports and `frontend/node_modules` was missing, so the FE half of `source_scan_tests.sh` could not run.
- **Fix:** `uv sync --group maia-inference` and `npm --prefix frontend ci` (both lockfile-only, no new packages), as the plan's own guidance and the script's message prescribe.
- **Files modified:** none tracked (`.venv`, `frontend/node_modules` are ignored)
- **Verification:** `ty check` "All checks passed!", vitest 131 passed

**2. [Rule 1 - Bug] FE files fail fast at selection time**
- **Found during:** Task 2 acceptance check
- **Issue:** `diff frontend/src/main.tsx` exited 0 because the unchanged file never reached the plugin hook, contradicting the acceptance criterion (exit 2 with the 241-04 message).
- **Fix:** `ensure_plugins(selection)` runs at selection time in `scan` and `diff`.
- **Files modified:** tools/cleanup.py
- **Committed in:** 974f99e2c

**3. [Plan note] Mutation example adapted**
- http.py has no numeric constant, so the code-token mutation used `+ ""` on `USER_AGENT` (see above).

---

**Total deviations:** 2 auto-fixed (1 blocking environment prep, 1 bug), 1 plan-text adaptation
**Impact on plan:** none on scope; no app/ behavior touched.

## Issues Encountered

- The TDD ordering for Task 2 was not strictly red-first: the selftest cases and the features were written together, then the cases passed on the first run. To still prove the cases are meaningful, a mutation harness changed the tool in 11 ways; 10 made selftest fail. The survivor ("unchanged outside file no longer short-circuits") is an equivalent mutant because an unchanged file yields no residue either way.
- `INV-L354` quotes `users.py:203` in the inventory; that clause is out of this plan's file set.

## Known Stubs

None.

## Threat Flags

None. The toolkit reads and writes only files under the in-scope filter (apply-edits refuses everything else), never touches the database, and installs no packages.

## Notes for downstream plans

- `diff`'s directive check compares the multiset of `noqa`, `ty: ignore`, `type: ignore`, `pragma: no cover`, `fmt:`, `pylint: disable=` heads per file; a rewritten comment must keep the directive.
- FE plugin contract (241-04): `fe_support.prose(path, text)` returns 6-tuples `(line, col, end_line, end_col, kind, text)`, `fe_support.tokens(path, text)` returns `(kind, text, line)` tuples (kinds `NAME`/`IDENTIFIER` get name canonicalization, kinds containing `STRING`/`TEMPLATE` get whole-word string canonicalization), `fe_support.directive_heads(records)` returns a multiset; optional `identifiers` is not needed because `--identifiers` reads NAME tokens.
- Extras contract (241-03): `extras.register(subparsers)` plus optional `selftest_cases()` returning `(name, callable)` pairs; `cleanup` is importable as a module even when run as a script (aliased in `sys.modules`).
- Remaining app/core residue outside the tag pass: the ip_rate_limiter docstring/comment wording (INV-L341) lands with 241-52.

## Self-Check: PASSED

Files verified present: tools/cleanup.py, tools/source_scan_tests.sh, tools/PHASE_BASE, ledgers/241-02.txt. Commits verified as ancestors of HEAD: 7dba18f00, b3f77d31e, 974f99e2c.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
