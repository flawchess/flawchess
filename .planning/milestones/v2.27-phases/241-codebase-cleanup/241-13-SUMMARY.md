---
phase: 241-codebase-cleanup
plan: 13
subsystem: services
tags: [cleanup, comments, eval-queue, engine, eval-utils, score-confidence]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "cleanup.py codemod and decision"
provides:
  - "eval_queue_service.py, engine.py and ten eval/score utility services free of planning tags (scan --gate 0 over scopes/241-13.txt)"
  - "ledgers/241-13.txt: all 36 INVENTORY section 6 rows of this scope APPLIED"
affects: [241-53, 241-67, 241-70]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 297158250c71be5ad8a6dd1953ca3946d662ba21
plan_head_after: 7c77930585c4cc12bc2e40af5563548cd4770952

tech-stack:
  added: []
  patterns:
    - "Comment rewrite states the rule or the current contract; evidence that justifies a rule (prod measurements, observed starvation) stays, provenance (phase, quick, SEED, D-NN ids) goes"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-13.txt
  modified:
    - app/services/engine.py
    - app/services/eval_queue_service.py
    - app/services/accuracy_acpl.py
    - app/services/best_move_candidates.py
    - app/services/eval_confidence.py
    - app/services/eval_utils.py
    - app/services/maia_encoding.py
    - app/services/maia_engine.py
    - app/services/position_classifier.py
    - app/services/score_confidence.py
    - app/services/sharp_filler.py
    - app/services/zobrist.py

key-decisions:
  - "INV-L597: no seed pointer. .planning/seeds/ holds no open seed for the tier-3 derived-pick double-claim, so the note states the limitation (no persisted lease row to lock, SKIP LOCKED alone does not help, a zero-collision pick needs an ephemeral TTL lease) and no seed was created"
  - "INV-L542 names the live writer eval_apply.refresh_game_oracle_counts (its current name); 241-53 must update this mention when it renames the function"
  - "Module docstring of eval_queue_service.py now lists all four tiers (1, 3, 4, 4b) and keeps the observed-on-prod evidence behind the no-residual-fallback rule, with the quick/SEED/plan ids removed"

patterns-established:
  - "Re-verify every inventory row against the code before applying; two rows were wrong as stated and a third needed a wider fix (see Deviations)"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: ~75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 13: Engine, Eval Queue and Eval/Score Utility Services Summary

**The eval queue, Stockfish pool and ten eval/score utility services no longer cite phases, quick tasks, seeds or decision ids, and several comments that had gone stale (guest handling, tier-4b population, caller lists) now describe the code as it is; the non-comment diff against PHASE_BASE is empty.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 2 (eval_queue_service.py + engine.py; ten utility services)
- **Files modified:** 12 services plus the new ledger

## Accomplishments

- `scan --gate --scope scopes/241-13.txt`: 12 files, 0 matches (baseline for the two Task 1 files was 159 matches, for the ten Task 2 files 76 after the codemod).
- `diff --scope scopes/241-13.txt`: exit 0, no residue (12 files changed, comments and docstrings only).
- `ledger`: exit 0, 36 of 36 rows covered, all APPLIED.
- Stale content fixed along the way (STYLE-GUIDE 2.2): see "Stale claims corrected" below.

## Task Commits

1. **Task 1: eval_queue_service.py and engine.py (20 rows)** - `493232191` (`chore(comments): app/services (eval_queue_service, engine)`)
2. **Task 2: the ten utility services (16 rows) and the plan gates** - `7c7793058` (`chore(comments): app/services (eval/score utilities)`)

`commits: 2` above is measured with `git rev-list --count 297158250..HEAD` before the SUMMARY commit.

## Codemod vs hand edits

| Task | Files | Codemod lines changed | Flagged "needs hand edit" | Notes |
|---|---|---|---|---|
| 1 | 2 | 74 | 90 | Most flagged lines sit in multi-paragraph docstrings of `_claim_tier3_derived`, `_claim_tier4_blob` and `claim_eval_job`; rewritten by exact-match replace scripts under `temp/241-13/` (asserting each old text occurs exactly once) |
| 2 | 10 | 62 (9 files) | 76 | Same method |

Every codemod rewrite was reviewed with `git diff -U0`. Hand fixes needed after the codemod: a lowercase sentence start (`# red/green verdicts`), a docstring wrapped line that became a dangling "Phase" fragment in `release_job` (rewritten), and several lines pushed over 100 characters. No `^\s*(#|//|\*)\s*[:;,]\s` residue appeared in the scope.

## Stale claims corrected (verified against the code first, D-10)

- `eval_queue_service.py` module docstring said `enqueue_tier1_game` refuses guests and every claim path filters `NOT users.is_guest`. Code: the tier-1 claim SQL admits guests (`OR ej.tier = 1`), the tier-3 lichess-eval branch (b) and tier-4b admit guests, `enqueue_tier1_game` only returns False for a missing user row. This is the stale comment 241-05 pointed at; the new "Guest handling" section lists the real matrix (INV-L565).
- Tier-4b description said "non-lichess-eval, non-guest" (INV-L564); `_claim_tier4_bestmove` has no `lichess_evals_at` clause and passes `include_guests=True`.
- `engine.py` `_acquire_and_analyse` docstring said "the four public methods"; five public methods call it (INV-L541).
- `eval_queue_service.py` named `eval_drain.run_one_full_eval_tick`, which exists nowhere; the drain entry is `_full_drain_tick` (INV-L588).
- `eval_utils.py` said "the four pre-existing call sites" of `selection_gate_clause` in eval_queue_service.py and "four lanes"; there are three (INV-L571).
- `position_classifier.py` said endgame class is derived at query time; it is derived at import and stored (INV-L576).
- Mentions of a nonexistent tier 2 as a live concept (`tier-2/3`, `tier-1/2`) now say tier-1 / tier-3.
- `scripts/backfill_eval.py` example replaced by `remote_eval_worker.py` / `opening_cache_repair.py` (INV-L582); `eval_confidence.py` caller list now matches the four real callers (INV-L574).

## Ledger (ledgers/241-13.txt)

36 lines, all `APPLIED`: INV-L531, L541, L563-L569, L582, L586-L589, L597, L603, L604, L619-L621 (Task 1) and INV-L535, L542, L570-L576, L590, L622-L627 (Task 2). Details per row are in the ledger. Decisions of note:

- INV-L597: pointer-free limitation note (see key-decisions).
- INV-L620 and INV-L604: deleted outright; INV-L624 and INV-L625: the two tombstone comment blocks in `score_confidence.py` deleted.
- INV-L542: names `refresh_game_oracle_counts`; 241-53 owns the later rename of that function and of every mention.

No `#` comment lines were added to the ledger (no row owned by another plan was touched in these files).

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-13.txt` | exit 0, 12 files, 0 matches |
| `cleanup.py diff --scope scopes/241-13.txt` | exit 0, 12 changed, no residue |
| `cleanup.py ledger --scope scopes/241-13.txt --ledger ledgers/241-13.txt` | exit 0 |
| `ruff check app/services`, `ruff format --check app/services` | clean (61 files already formatted) |
| `ty check app/ tests/ scripts/` | All checks passed (also on the untouched baseline, after `uv sync --group maia-inference`) |
| `source_scan_tests.sh --py`, first pytest command | 95 passed (run serially, without `-n 4`) |
| `source_scan_tests.sh --py`, second pytest command | 5 passed |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed |
| `pytest tests/services/test_eval_queue.py test_engine_nodes.py test_score_confidence.py test_eval_confidence.py` (serial) | 126 passed |

`test_no_bare_lichess_evals_at_derivation_remains` passes (it is AST based, so the rewritten docstrings in `eval_utils.py` cannot trip it).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages). Baseline `ty check` was clean before any edit.

**2. [Environmental] Source-scan tests run serially**
- Per the parallel-execution note, the Python half of `source_scan_tests.sh` ran with the same file list but without `-n 4` because sibling executors share the dev Postgres. This is environmental, not a plan failure; results match the xdist run recorded by 241-02/03.

**3. [Rule 1 - stale comment, STYLE-GUIDE 2.2] Non-inventoried wording fixes next to removed tags**
- `engine.py`: the `PV_CAP_PLIES` comment's "tier-1/2 need 1-2 plies; tier-3 ~3 plies" refers to tactic-motif tiers, not queue tiers; reworded as "tactic-motif tiers 1 and 2 ... tier 3" so the new text cannot be misread against the queue tiers.
- `eval_utils.py`: the 7-derivation history list in `derive_is_lichess_eval_game` and the "tier3-branch-b-one-ply-stamp debug fix" slug and `.planning/debug/` pointer in `derive_raw_lichess_eval_game` replaced by the rule they justify.
- `score_confidence.py`: line-number references to `eval_confidence.py:113/116-119` dropped; `eval_confidence.py` kept as a file reference.
- `accuracy_acpl.py`: a pointer to `.planning/seeds/SEED-110-...` (not an open seed) removed.
- `sharp_filler.py`: "Consumed by plan 03's warm-up-label eligibility check" now names `train_repository`'s pool-eligibility check (the real consumer).
- `eval_queue_service.py`: dropped `RESEARCH-NOTES` / `CONTEXT.md` pointers and the "Doc correction (2026-07-28)" narration (INV-L621), "Add FOR UPDATE SKIP LOCKED" TODO (INV-L597).

**Total deviations:** 1 blocking env prep, 1 environmental serial run, 1 group of stale-wording fixes; none touch code, SQL, constants, runtime strings, testids or tests.

## Issues Encountered

- The worktree sandbox refused several compound shell lines (heredoc plus following commands, `sed` with a computed range, `git` after `||` chains); commands were split into plain calls.
- zsh does not word-split `$U`; a scope file under `temp/241-13/scope2.txt` (the ten utility files) was used with `--scope` instead.

## Known Stubs

None.

## Threat Flags

None. Comments and docstrings only; T-241-25 (claim SQL edited alongside comments) is mitigated by the empty `cleanup.py diff` over the scope and the unchanged SQL strings, and T-241-26 (source-scanning tests) by the green source-scan run.

## Self-Check: PASSED

Files verified present: ledgers/241-13.txt and the 12 edited services. Commits `493232191` and `7c7793058` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
