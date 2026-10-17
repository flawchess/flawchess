---
phase: 241-codebase-cleanup
plan: 07
subsystem: backend-comments
tags: [cleanup, comments, docstrings, routers, openapi, eval-remote]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "extras.py codemod/absent/decision"
provides:
  - "app/routers (17 files) free of planning tags with an empty non-comment diff against PHASE_BASE"
  - "ledgers/241-07.txt: 24 lines covering 23 INVENTORY rows plus the INV-L354 secondary clause"
affects: [241-52, 241-67, 241-70]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 7dc02e259035727a1f11b80d843ca5d3dcaaedce
plan_head_after: a1cf140c321f8de5a216733448157dd07345a8f7

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-07.txt
  modified:
    - app/routers/admin.py
    - app/routers/auth.py
    - app/routers/bots.py
    - app/routers/endgames.py
    - app/routers/eval_remote.py
    - app/routers/feedback.py
    - app/routers/imports.py
    - app/routers/insights.py
    - app/routers/library.py
    - app/routers/position_bookmarks.py
    - app/routers/push.py
    - app/routers/stats.py
    - app/routers/train.py
    - app/routers/users.py
    - app/users.py

key-decisions:
  - "INV-L376 text adjusted: 'a confirmed row's eval is never overwritten' replaces 'confirmed rows are immutable', because _upsert_opening_cache still lets the pv self-heal touch confirmed rows"
  - "The INV-L354 secondary clause lives in app/users.py:203 (the reset-password call site), not app/routers/users.py; the one-line comment edit was made there"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: ~2h
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 07: app/routers comment cleanup Summary

**All 17 files in app/routers carry no planning tags; eval_remote.py now describes only the current atomic, entry, flaw-blob and tier-4b lanes; every route path, param, response field, Sentry string and log string is unchanged.**

## Performance

- **Tasks:** 2 (eval_remote.py, then the other 16 files plus the plan gates)
- **Files modified:** 15 (14 in app/routers, plus app/users.py for the INV-L354 clause) plus the ledger

## Accomplishments

- Scan of scopes/241-07.txt: 17 files, 0 matches. `cleanup.py diff` over the scope: 14 changed, no residue (the non-comment token stream is identical to PHASE_BASE). `cleanup.py ledger`: exit 0.
- eval_remote.py: module docstring rewritten to the five live lanes plus the flaw-blob pair; the Gen-1 `/lease` + `/submit`, `_apply_submit`, "Phase 149-03 deleted" and "Gen-1 coexistence" narration is gone (none of those handlers exist). Isolation comments now point at the atomic-submit write path (`apply_full_eval`).
- Router docstrings (OpenAPI descriptions) were only corrected or stripped of tags: guest JWT lifetime (365-day), suggestions ply range (2-8, no piece filter), the Google callback redirect_uri explanation, the Train reveal 409 text, the settings PUT settle-before-mutate text.

## Ledger counts (ledgers/241-07.txt)

APPLIED 24, MOVED 0, SKIPPED 0, LEFT 0, DEFERRED 0. 23 INVENTORY rows (INV-L340, 343, 350, 364-374, 375-378, 397, 413, 418, 419, 424) plus the INV-L354 secondary clause. The INV-L354 line is written as `INV-L354: APPLIED (secondary users.py clause)` because the ledger tool only parses `INV-L<n>: STATUS`. INV-L397 covered every listed site; none was already gone.

## Codemod vs hand edits

- `cleanup.py codemod`: 77 lines in eval_remote.py, then 100 lines in 11 other files (177 total). 104 + 80 lines were reported "needs hand edit".
- Hand edits: about 100 span replacements in eval_remote.py and about 85 in the other files (done with exact-match replace scripts that refuse non-unique matches), plus 28 paragraph re-wraps of comments the codemod left with a short first line.
- Codemod output that needed repair: in train.py's module docstring the codemod removed `D-05.` / `D-09.` pointers and left two broken sentences (`reversing Phase 189` / `per Phase 224` dangling); both were rewritten by hand. Hyphen-split words joined by my re-wrap helper (`one-open-session-per- user`, `already- eval'd`, `server- side`) were fixed before committing.

## Non-inventoried fixes

- Stripped untagged-by-scan planning references: single-digit `D-2`/`D-4`/`D-5`, `Q4`/`Q5`, `S-05`/`S-06`, `Pitfall N`, `Open Question #3`, `(260803)`/`260725-da3`-style quick IDs, `tier3-branch-b-one-ply-stamp` debug-session slugs, `T-NNN-NN` threat ids, `ASVS`-adjacent `T-` ids, and `UAT 186`/`IN-02 code review` provenance, wherever they sat in comments or docstrings the codemod touched.
- History narration turned into present tense where the sentence was rewritten anyway: `(it used to be null ...)` on the PUT /me/profile impersonation param, the `in_flight_count removed in Phase 119-03` note (now "There is no in_flight_count: ..."), "lichess-arm game" became "homogenized lichess-eval game" (STYLE-GUIDE 3.3 row 25), "Path-C reporting" became "Attempt-cap reporting" (row 30).
- app/users.py:203 (INV-L354 secondary clause): "from the two existing limiter call sites" became "from the other limiter call sites" (comment-only; `cleanup.py diff app/users.py` clean). This file is outside scopes/241-07.txt (241-03 already cleaned it).
- Kept on purpose: dated bug-fix explanations (FLAWCHESS-8B/8E/A0/CW sentry ids, 2026-xx-xx review dates), `(see SEED-NNN)` pointers (none present in this scope), and INVENTORY 7.1 seed 2 (the coordinated atomic-lane docstring rewrite) untouched beyond the listed rows.

## Task Commits

1. **Task 1: eval_remote.py** - `755c86661` (`chore(comments): app/routers (eval_remote)`)
2. **Task 2: other routers + gates** - `a1cf140c3` (`chore(comments): app/routers (rest)`; also holds the final re-wrap and hyphen fixes for eval_remote.py)

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-07.txt` | 17 files, 0 matches |
| `cleanup.py diff --scope scopes/241-07.txt` | 17 selected, 14 changed, no residue |
| `cleanup.py ledger --scope scopes/241-07.txt --ledger ledgers/241-07.txt` | exit 0 |
| `ruff check app/routers app/users.py`, `ruff format --check` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| `source_scan_tests.sh --py` | 95 + 5 passed |
| `pytest tests/test_imports_router.py tests/test_eval_worker_endpoints.py` | 135 passed |

## Deviations from Plan

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree.** `.venv` was missing; ran `uv sync --group maia-inference` (lockfile only). The first baseline run of the source-scan tests showed two `database "flawchess_test_gw0" does not exist` errors, caused by another wave-3 worktree cloning the shared template database at the same moment; a rerun was clean (95 + 5 passed). Not a code issue.

**2. INV-L354 ledger line format.** The plan asks for `INV-L354 (secondary users.py): STATUS`; `cleanup.py ledger` rejects that shape, so the line is `INV-L354: APPLIED (secondary users.py clause) ...`.

**3. INV-L354 file.** The plan places the clause in `app/routers/users.py ~:203`; the matching comment is in `app/users.py:203` (that file has no such comment in app/routers/users.py). Edited there.

**Total deviations:** 1 environment, 2 plan-text adaptations. No behavior change.

## Known Stubs

None.

## Threat Flags

None. Only comment and docstring text changed; the token-level diff gate confirms route decorators, Query/Header params, response models, Sentry strings and log strings are identical to PHASE_BASE (T-241-14, T-241-15).

## Suspected issues noticed (not touched)

- `app/routers/imports.py` `/eval-coverage` comment mentions `is_analyzed=True` and `app/schemas/imports.py:96` still says `analyzed_count: int  # white_blunders IS NOT NULL (is_analyzed ...)`, while the handler computes `full_evals_completed_at IS NOT NULL`. The schema comment is outside this scope (241-06) and the glossary row 26 covers the term.

## Self-Check: PASSED

Files verified present: ledgers/241-07.txt, this SUMMARY, all 14 router files and app/users.py modified. Commits `755c86661` and `a1cf140c3` are ancestors of HEAD.
