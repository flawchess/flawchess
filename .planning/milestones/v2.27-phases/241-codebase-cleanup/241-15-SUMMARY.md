---
phase: 241-codebase-cleanup
plan: 15
subsystem: backend-services
tags: [cleanup, comments, import, clients, guest, push, email, feedback, store]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "cleanup.py codemod / decision"
provides:
  - "16 services under app/services free of planning tags, with ledgers/241-15.txt covering all 33 INVENTORY rows"
affects: [241-56, 241-66, 241-68]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 297158250c71be5ad8a6dd1953ca3946d662ba21
plan_head_after: 0693ae5726f712c99ad9e08d92624c7ec3a1acd5

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-15.txt
  modified:
    - app/services/import_service.py
    - app/services/normalization.py
    - app/services/chesscom_client.py
    - app/services/chesscom_to_lichess.py
    - app/services/lichess_client.py
    - app/services/guest_service.py
    - app/services/guest_cleanup_service.py
    - app/services/push_send.py
    - app/services/email_service.py
    - app/services/feedback_service.py
    - app/services/feedback_ask_service.py
    - app/services/store_bot_game_service.py
    - app/services/store_paste_game_service.py
    - app/services/bot_game_pgn.py
    - app/services/admin_service.py

key-decisions:
  - "Every SEED pointer in scope (SEED-026, 093, 116, 135, 138, 191, 023) refers to a seed in .planning/seeds/closed/, so none was kept as (see SEED-NNN)"
  - "push_send.py module docstring was rewritten whole as the current prune/TTL contract instead of tag-stripped, keeping the three rules (info-level capture_message only, host never path, no TTL 0)"

patterns-established: []

duration: 55min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 15: Import pipeline, clients, guest, push, email, feedback and store services Summary

**Planning tags are gone from 16 service modules (178 codemod-rewritten comment lines, the rest hand edited), 33 inventory rows are APPLIED, and the non-comment diff against PHASE_BASE is empty.**

## Accomplishments

- Task 1 (import_service.py, normalization.py, 12 rows): the codemod rewrote 92 lines; the remaining ~100 matches were hand edited with exact-string replacements. `_BATCH_SIZE` keeps its "don't move the eval pass back into this lane" rule (INV-L835), `_flush_batch` states the eval pass runs in `run_eval_drain()` and why (INV-L836), and the eval_entry import comment drops the closed SEED-023 pointer (INV-L773). Docstrings now say "active (PENDING, QUEUED or IN_PROGRESS)", retry on `_RETRIABLE_DB_OUTAGE_ERRORS`, and cite `app.services.eval_entry`.
- Task 2 (14 more files, 21 rows): codemod rewrote 86 lines in 12 files, ~110 more hand edited. Guest JWT docs say 365-day (confirmed `_GUEST_JWT_LIFETIME_SECONDS = 31536000`), the clients say `NormalizedGame`, debug-note and PLAN.md pointers are gone, `guest_cleanup_service` documents the Train purge as a rule ("Do NOT add a separate DrillSolve-targeting delete"), and `push_send` keeps "do not restore an error-level capture" and "Do not use a TTL of 0".

## Ledger (ledgers/241-15.txt)

33 rows, all APPLIED: INV-L751, L752, L772, L773, L774, L775, L800, L801, L802, L834, L835, L836 (task 1); INV-L747, L749, L750, L759, L760, L762, L764, L765, L766, L767, L792, L793, L794, L795, L796, L822, L823, L826, L827, L829, L830 (task 2). INV-L773 records that SEED-023 is closed.

## Task Commits

1. **Task 1: import_service.py and normalization.py** - `57234e2f7` (`chore(comments): app/services (import_service, normalization)`)
2. **Task 2: clients, guest, push, email, feedback, store** - `0693ae572` (`chore(comments): app/services (clients, guest, push, email, feedback, store)`)

## Deviations from Plan

### Non-inventoried fixes (all comment/docstring only, Rule 2 style hygiene inside plan scope)

- import_service.py: removed dated-incident/UAT provenance in comments not covered by a row (`UAT 2026-05-20` x3, `code-review 2026-07-02, #1` x2) and rewrote the surrounding sentence in present tense or as a rule.
- chesscom_client.py: the 2026-04-25 "Pre-... conflated both as user not found" narration became "Don't treat both as 'user not found'".
- chesscom_to_lichess.py: the snapshot-provenance comment claimed the constants are "surfaced to user-facing tooltips downstream", but only tests read them; reworded without the claim. The USCF/FIDE accessors now say "No app caller yet (future use)" (grep confirmed only tests call them).
- store_paste_game_service.py: "SC-7 post-commit failure window" (a plan-defined term pointing at 208-03-PLAN.md) became "Post-commit failure window" with the reason already stated inline.
- guest_cleanup_service.py: the welcome copy is quoted exactly (`Welcome.tsx` DELTA_4) instead of the old paraphrase.
- Codemod collapse bug (leading tag into bare punctuation) did not occur in this scope: the grep for `^\s*(#|//|\*)\s*[:;,]\s` on the diff found nothing; two cases of an orphan `;` left by hand edits were fixed before commit.

None of the plan's prohibitions were touched: the dict-shaped test-double fallbacks with `# type: ignore` keep their directive heads, and `game_dict`, `_collect_position_rows`, `bot_elo`, `_import_scope_expanded`, `users_with_zero_pending`, `_apply_eval_results` keep their names in comments.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-15.txt` | exit 0 (16 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-15.txt` | exit 0 (16 selected, 15 changed, no residue) |
| `cleanup.py ledger --scope ... --ledger ledgers/241-15.txt` | exit 0 |
| `ruff check app/services`, `ruff format --check app/services` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline also clean) |
| `source_scan_tests.sh` python half, run SERIALLY without `-n 4` (shared dev Postgres, sibling executors) | 95 passed + 5 passed |
| `source_scan_tests.sh --fe` | 131 passed (9 files); no frontend file changed |

The serial python run is an environmental choice per the parallel-executor instructions, not a plan failure.

## Known Stubs

None.

## Threat Flags

None. No code, request, retry, Sentry message/tag/context-key or log text changed (T-241-28, T-241-29 mitigated by the empty token diff).

## Self-Check: PASSED

- ledgers/241-15.txt found; both task commits (`57234e2f7`, `0693ae572`) are ancestors of HEAD; `git rev-list --count PLAN_HEAD_BEFORE..HEAD` was 2 before this SUMMARY commit; no files deleted by either commit.
