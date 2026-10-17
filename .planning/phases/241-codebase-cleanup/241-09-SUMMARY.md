---
phase: 241-codebase-cleanup
plan: 09
subsystem: backend-repositories
tags: [cleanup, comments, library_repository, query_utils, game_flaws_repository, flaws_repository]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/rows/ledger"
  - phase: 241-03
    provides: "cleanup.py codemod and decision"
provides:
  - "library_repository.py, query_utils.py, game_flaws_repository.py and flaws_repository.py free of planning tags in comments and docstrings, with an empty non-comment diff against PHASE_BASE"
  - "ledgers/241-09.txt covering all 27 INVENTORY rows plus the INV-L505 secondary note"
affects: [241-53, 241-67]

actuals:
  tokens: 26500
  tasks: 2
  commits: 2
plan_head_before: 5b903e1e2d15c50df48b7bd110f747162bb50ac2
plan_head_after: 956a099231bd588352cea4399e82c745dd3c527c

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-09.txt
  modified:
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - app/repositories/game_flaws_repository.py
    - app/repositories/flaws_repository.py

key-decisions:
  - "The ValueError message in flaw_record_to_row still contains '(D-03 ...)': it is a runtime string, so D-15 keeps it untouched (scan does not flag it)"
  - "The INV-L505 secondary note for query_utils.py went into the ledger as a '#' comment line, because the ledger parser rejects non-standard lines"

duration: 70min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 09: Repositories (library, query_utils, game_flaws, flaws) Summary

**The shared flaw/tactic filter repositories now state the current filter rules (neutral "either" orientation default, 19 tactic families, unmapped ints 14 and 15, the user_id requirement) with no quick-task chronology, and the token diff against PHASE_BASE is empty.**

## Performance

- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 4 source files plus the new ledger
- **Scan baseline:** 210 tagged lines in scope; 0 after

## Accomplishments

- library_repository.py (20 rows): module docstring, the tactic-family mapping header, `_depth_in_range`, `_tactic_controls_active`, `_build_tactic_clause`, `build_flaw_filter_clauses`, `query_flaws`, `_analyzed_game_ids_subquery`, `fetch_tactic_comparison` and `fetch_tactic_lines` rewritten as present-tense rules. `FAMILY_TO_MOTIF_INTS` is named 11 times (the test allows 2 to 15).
- query_utils.py, game_flaws_repository.py, flaws_repository.py (7 rows plus the secondary): the `apply_game_filters` docstring now matches the guard that raises without `user_id`, and the default-orientation comments state the neutral-default rule.
- Stale statements corrected, each re-verified against the code first (D-10):
  - the mapping header said "These 10 keys" and "combinations family dropped entirely"; the dict has 19 families and only ints 14 and 15 are unmapped
  - the pin comment claimed pin sits in SUPPRESSED_MOTIFS; it does not (floor 0.92)
  - the trapped_piece "currently suppressed" clause; trapped-piece is no longer suppressed
  - `_depth_ok` named in the mate bullet does not exist anywhere in `app/`
  - `tactic_slot_visible` named `_query_flaws` / `_build_card` as serialization sites; they are `_build_flaw_item` and `library_service._build_tactic_by_ply_entry`
  - `fetch_tactic_comparison`'s docstring mentioned an "allowed-only default"; the default is "either"
  - the game_flaws_repository docstring named `reclassify_positions.py` (does not exist) and an "import hook"; the callers are `eval_entry`, `eval_apply` and `scripts/backfill_flaws.py`

## Ledger counts (ledgers/241-09.txt)

27 INVENTORY rows, all APPLIED, plus 1 secondary note (INV-L505 secondary, `#` comment line):

| Status | Rows |
|---|---|
| APPLIED | 27 |
| MOVED / SKIPPED / LEFT / DEFERRED | 0 |

The two "M" rows (INV-L450, INV-L500) were applied with their changed rewrite text.

## Codemod vs hand edits

| File | Codemod lines changed | Flagged "needs hand edit" |
|---|---|---|
| library_repository.py | 69 | 78 |
| query_utils.py, game_flaws_repository.py, flaws_repository.py | 22 (query_utils 14, game_flaws 8, flaws 0) | 43 |

`git diff -U0` was reviewed after both runs; no codemod rewrite was reverted. The flagged lines plus re-wrapping of comments the codemod left with short first lines were hand edited with exact-match replacement scripts under `temp/241-09/` (gitignored; 10 scripts for library_repository.py, 2 for the rest; each replacement asserted a unique match). About 40 further comment spots that the scan did not list but the codemod's first-line rewrites left awkward ("# Widened to 3-value Literal", "# — the Library's ...") were reworded in the same passes.

## Non-inventoried fixes

- query_utils.py `BUG FIXED (Quick 260621)` became a "Don't emit TWO separate correlated EXISTS" rule (bug-fix why kept, tag gone).
- game_flaws_repository.py `bulk_update_game_flaw_rows`: the pointer to a memory-file name (`project_asyncpg_jsonb_null_vs_sql_null`) became the fact itself (a Python None binds as JSON null, not SQL NULL).
- library_repository.py: dropped `(Option A)`, `(T-bdt-01 ...)`, `(R1/R6)`, `(R2 gate)`, `(R3 gate)` style ids that the scan patterns do not cover.

## Task Commits

1. **Task 1: library_repository.py** - `123ff587d` (`chore(comments): app/repositories/library_repository`)
2. **Task 2: query_utils, game_flaws, flaws** - `956a09923` (`chore(comments): app/repositories (query_utils, game_flaws, flaws)`)

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-09.txt` | exit 0 (4 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-09.txt` | exit 0 (4 files selected, 4 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-09.txt --ledger ledgers/241-09.txt` | exit 0 |
| `ruff check app/repositories`, `ruff format --check app/repositories` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was also clean) |
| `pytest tests/test_library_repository.py -k family_to_motif_ints` | 1 passed |
| `source_scan_tests.sh --py` (run serially, see below) | 95 passed + 5 passed |

The `--fe` half of `source_scan_tests.sh` was not run: this plan edits no frontend file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep and serial test runs in a parallel worktree**
- **Found during:** Task 1 step 0
- **Issue:** fresh worktree had no `.venv`; the runner's first pytest command uses `-n 4`, which collides with sibling executors' xdist database names on the shared dev Postgres.
- **Fix:** `uv sync --group maia-inference` (lockfile only); ran the runner's Python half as two serial pytest commands with the same file lists. Environmental, not a plan failure.
- **Files modified:** none tracked

**Total deviations:** 1 (environmental). No behavior change; no assertion changed.

## Issues Encountered

- The `rows` view lists INV-L450 text as "10 keys"; the dict actually has 19 keys, so the rewrite says "These keys" instead of a count.
- The runtime ValueError string in `flaw_record_to_row` still reads "forbidden (D-03 — game_flaws stores M+B only)". It is a runtime string (D-15) and is not flagged by the scan; a later plan can change it together with its test if the owner wants.

## Known Stubs

None.

## Threat Flags

None. Comments and docstrings only; `cleanup.py diff` shows zero token residue, so T-241-18 is mitigated.

## Self-Check: PASSED

- ledgers/241-09.txt: FOUND
- 123ff587d, 956a09923: FOUND in `git log`
- No change to STATE.md or ROADMAP.md
