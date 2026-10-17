---
phase: 241-codebase-cleanup
plan: 12
subsystem: services
tags: [cleanup, comments, eval-drain, eval-entry]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/diff/ledger and the PHASE_BASE token diff"
  - phase: 241-03
    provides: "extras.py codemod and decision commands"
provides:
  - "app/services/eval_drain.py and eval_entry.py free of planning tags and relocation history"
  - "ledgers/241-12.txt: all 19 INVENTORY rows of the two files APPLIED"
affects: [241-67, 241-68]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: c3b9f7ec01c040dea0df299f0886f90c1bc09306
plan_head_after: 350e444591debbc983e4f66dcd7337d0843382d0

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-12.txt
  modified:
    - app/services/eval_drain.py
    - app/services/eval_entry.py

key-decisions:
  - "The three eval_drain re-export noqa tails (_EvalTarget and the two collectors) now say (tests): re-verified that only tests/services/test_eval_drain.py imports them from eval_drain; import_service.py imports the collectors from eval_entry"
  - "A comment must not contain a literal noqa directive head: the diff gate counts `noqa: F401` text inside comments, so the re-export block comment says 'the names carrying an F401 ignore directive'"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: 55min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 12: eval_drain and eval_entry Comment Cleanup Summary

**Both drain modules now describe what the code does today: the R7 relocation narratives, Phase/SEED/D-NN/WR-NN/Pitfall tags and stale line-number pointers are gone, with an empty token diff against PHASE_BASE.**

## Accomplishments

- eval_drain.py: 172 scan matches before, 0 after. Module docstring, the two re-export block comments, constant banners, the opening-cache write-path docstrings, the tier-4b minimal drain, `_full_drain_tick`, `resweep_holed_games` and the periodic resweep all read in present tense.
- eval_entry.py: 39 matches before, 0 after. The module docstring keeps its "Consumed by" list and the no-AsyncSession rule; the five "Lifted from import_service.py" notes are gone; `_collect_eval_targets_per_game` states the target order directly.
- The import-time lane is called the "entry-ply lane" / "entry-ply drain" (STYLE-GUIDE 3.3 row 33), and "Path-C"/"attempt cap" follows row 30 where a comment was rewritten anyway. Identifiers are unchanged (`_EvalTarget`, `_apply_eval_results`, `_log_path_c_capacity_reached` keep their names for 241-67/68).

## Counts

| | eval_drain.py | eval_entry.py |
|---|---|---|
| Scan matches before | 172 | 39 |
| Lines rewritten by the codemod | 81 | 19 |
| Flagged "needs hand edit" after the codemod | 96 | 20 |
| Hand-edit replacement spans (exact-text batches in `temp/241-12/`) | 94 | 26 |
| Scan matches after | 0 | 0 |

The codemod dry run was read before writing; the `git diff -U0` review found nothing to revert. No comment line started with `:`, `;` or `,` after the codemod. Many codemod outputs (for example `# Quick 26...` heads) needed a follow-up hand edit only where the surviving sentence still carried a tag-shaped reference; those are included in the hand-edit span counts.

## Ledger (ledgers/241-12.txt)

All 19 rows APPLIED after re-verification (D-10): INV-L552..L559, L585, L613..L615 (eval_drain) and INV-L534, L560..L562, L616..L618 (eval_entry). No row was SKIPPED, LEFT, MOVED or DEFERRED. Notes of substance:

- INV-L553: the stated owner of the two collector re-exports (`tests/import_service.py`) was wrong in two places; the only importer from eval_drain is the test module.
- INV-L555: the dedup comment claimed Postgres rejects `ON CONFLICT DO UPDATE` duplicates, but `_insert_cache_candidates` uses `ON CONFLICT DO NOTHING`; the comment now gives the actual reason (one write decision per position).
- INV-L556: re-verification found the `eval_remote.py:1158` best_cp override no longer lives in eval_remote; it is in `eval_apply._apply_bestmove_submit`, and the comment names that symbol.
- INV-L562: `_DRAIN_BATCH_SIZE` is 10 and `ENTRY_LEASE_BATCH_SIZE` is 50 in eval_drain.py; the docstring names both.
- INV-L561: banner reads "Entry-ply lane helpers: claim / mark / collect / classify" (the inventory's "Cold-drain helpers" prefix conflicts with glossary row 33).

## Non-inventoried fixes (STYLE-GUIDE 2.2)

- eval_drain.py: the `_RETRIABLE_DB_OUTAGE_ERRORS` and other untagged comments were left alone. In `_full_drain_tick` the comment on `update_opening_cache` and `blobs_pending` was rewritten from history ("Before this fix ... was being donated") to the invariant; the "Replaces the LIFO id-DESC interim pick" sentence and a "Phase 150 R7 ... is now" narration were rewritten to present tense; the periodic-resweep docstring "what was a manual chore" became "the manual chore".
- eval_entry.py: `_batch_update_entry_eval_rows` "exactly the pre-batch semantics" rewritten as the rule (NULL means no predicate); `_entry_claim_sql` "byte-identical to the pre-212-07 inline literal" became "the plain claim literal".
- FLAWCHESS-NN Sentry short ids were kept where they explain a rule (FLAWCHESS-5Q, 5V, 5A, 6B, 6G, A0); FLAWCHESS-8E was dropped with the stale ON CONFLICT claim.

## Task Commits

1. **Task 1: eval_drain.py + ledger rows** - `313d934d2` (`chore(comments): app/services/eval_drain`)
2. **Task 2: eval_entry.py + remaining ledger rows** - `350e44459` (`chore(comments): app/services/eval_entry`)

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-12.txt` | exit 0 (2 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-12.txt` | exit 0 (2 selected, 2 changed, no residue, noqa heads unchanged) |
| `cleanup.py ledger --scope scopes/241-12.txt --ledger ledgers/241-12.txt` | exit 0 |
| `ruff check` / `ruff format --check` on both files | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| source-scan tests, Python half, run SERIALLY | 95 passed + 5 passed (baseline identical) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` (lockfile only) before the baseline gates; no tracked files changed.

**2. [Plan note] Source-scan tests run serially**
- Per the parallel-executor instructions, the Python half of `source_scan_tests.sh` was run with the same file list but without `-n 4`, to avoid xdist database-name collisions with sibling executors. This is environmental, not a plan failure. The frontend half was not run: this plan touches no frontend file and no test reads these two modules' comment text through vitest.

**3. [Plan note] Diff gate counts `noqa:` text in comments**
- A first draft of the re-export block comment contained the literal text `noqa: F401`; `cleanup.py diff` reported "directive added or changed". The comment was reworded; no directive head in code changed.

**Total deviations:** 1 blocking env prep, 2 plan notes. No behavior change.

## Known Stubs

None.

## Threat Flags

None. Only comments and docstrings changed; the re-export import blocks keep every `# noqa: F401` head; log text, SQL, constants and identifiers are untouched (T-241-24 mitigated by the empty token diff and ty).

## Notes for downstream plans

- Seed candidates: none. Suspected bugs: none found.
- `_tier4b_minimal_drain_tick` is about 150 logic lines, past the soft 100-line guidance (CLAUDE.md); not split here (comment-only plan).

## Self-Check: PASSED

Files present: ledgers/241-12.txt, app/services/eval_drain.py, app/services/eval_entry.py. Commits `313d934d2` and `350e44459` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
