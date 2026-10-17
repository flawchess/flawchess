---
phase: 241-codebase-cleanup
plan: 06
subsystem: api
tags: [cleanup, comments, pydantic, schemas, planning-tags]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/diff/ledger and the PHASE_BASE token-diff gate"
  - phase: 241-03
    provides: "codemod and decision commands"
  - phase: 241-04
    provides: "toolkit plugin hooks (unused here, schemas are Python only)"
provides:
  - "app/schemas (20 files) free of planning tags; the non-comment diff against PHASE_BASE is empty"
  - "ledgers/241-06.txt with all 16 INVENTORY rows for app/schemas plus the INV-L419 secondary clause"
affects: [241-07, 241-52, 241-67, 241-70]

actuals:
  tokens: 55000
  tasks: 2
  commits: 2
plan_head_before: 7dc02e259035727a1f11b80d843ca5d3dcaaedce
plan_head_after: 9bdb5cf7714b0ede825064b0c165aa12b690b311

tech-stack:
  added: []
  patterns:
    - "Hand edits applied as exact-match (old, new) pairs through a scratchpad helper instead of cleanup.py apply-edits (see Deviations); the diff/ledger gates are unchanged"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-06.txt
  modified:
    - app/schemas/admin.py
    - app/schemas/bots.py
    - app/schemas/endgames.py
    - app/schemas/eval_remote.py
    - app/schemas/feedback.py
    - app/schemas/feedback_ask.py
    - app/schemas/imports.py
    - app/schemas/insights.py
    - app/schemas/library.py
    - app/schemas/llm_log.py
    - app/schemas/normalization.py
    - app/schemas/opening_insights.py
    - app/schemas/openings.py
    - app/schemas/push.py
    - app/schemas/stats.py
    - app/schemas/train.py
    - app/schemas/users.py

key-decisions:
  - "History narration in schema docstrings became present tense or was deleted (for example the Gen-1 'old pair stays deprecated' paragraph, the 'was settled_streak_weeks' asides); only rules that prevent a regression were kept"
  - "Pointers into .planning (notes paths, 189-05-PLAN.md, RESEARCH sections) were removed together with the tags, since the plan's success criterion is 'no pointers into .planning'"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15, D-17]

duration: 75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 06: app/schemas Comment Cleanup Summary

**Every planning tag and `.planning` pointer is gone from the 20 app/schemas files, the SolveRequest/TrainProgressResponse docstrings now describe the current Train contract, and the token diff against PHASE_BASE is empty (no wire name, alias, Literal or string literal moved).**

## Performance

- **Duration:** ~75 min
- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 17 app/schemas files (3 of the 20 scope files were already clean: `__init__.py`, `auth.py`, `position_bookmarks.py`) plus the new ledger

## Accomplishments

- Task 1 (train, eval_remote, imports, library): about 290 tagged lines. The codemod rewrote the mechanical shapes; 101 hand-edit pairs covered the rest (train 34, library 34, eval_remote 26, imports 7).
- Task 2 (13 remaining files): 90 lines were left for hand editing after the codemod; 95 hand-edit pairs cover them plus the INVENTORY rows and neighbouring stale wording.
- All 16 INVENTORY section 6 rows for app/schemas are APPLIED (none moved, skipped or left), each re-verified against the code first; the INV-L419 secondary clause (`schemas/train.py` "before Phase 202 builds any UI") is applied too.
- `scan --gate` on the plan scope reports 0 matches; a wider grep for `Phase N`, `Plan N`, `D-NN`, quick-task IDs, `RESEARCH`, `UAT`, `.planning` finds nothing in app/schemas.

## Task Commits

1. **Task 1: train, eval_remote, imports, library** - `85c07dbb7` (`chore(comments): app/schemas (train, eval_remote, imports, library)`)
2. **Task 2: the remaining app/schemas files** - `9bdb5cf77` (`chore(comments): app/schemas (rest)`)

`commits: 2` above is measured with `git rev-list --count 7dc02e259..HEAD` before the SUMMARY commit.

## Ledger (ledgers/241-06.txt)

All APPLIED: INV-L379, L380, L381, L382, L383, L384, L385, L386, L398, L399, L400, L401, L420, L421, L422 (M), L423. INV-L419 secondary is a `#` comment line because the ledger parser rejects any non-`INV-L<n>: STATUS` line (same workaround as 241-04's INV-L1070); 241-07 writes the real INV-L419 line.

Verifications worth recording:

- L379: `SubmitResponse`, `SubmitEval`, `LeaseResponse` no longer exist anywhere in app/, so the "mirrors SubmitResponse" docstring was stale and was rewritten per the row.
- L381: checked against `get_readiness` in app/routers/imports.py (not-mid-Stage-B clause, settled-empty and below-anchor-floor escapes).
- L400: the row says `_wilson_bounds`; the real function is `score_confidence.wilson_bounds` (no `_wilson_bounds` exists), so the comment names that.
- L420: both tombstone blocks (opponent_* / diff_* fields and score_gap_skill_* / endgame_skill_rate_mean) refer to fields that exist nowhere in app/ code.
- L422: rewritten as the current contract after reading `_resolve_grade` and `_disagreement_accepted` in train_repository.py.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-06.txt` | exit 0, 0 matches |
| `cleanup.py diff --scope scopes/241-06.txt` | exit 0 (20 selected, 17 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-06.txt --ledger ledgers/241-06.txt` | exit 0 |
| `ruff check app/schemas`, `ruff format --check app/schemas` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (also clean on the untouched baseline) |
| `source_scan_tests.sh --py` | 95 passed + 5 passed |

Step 0 baseline (untouched tree, after `uv sync --group maia-inference`): ty and `source_scan_tests.sh --py` both passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages) before the baseline gates; no tracked files changed.

### Plan-text adaptations

**2. Hand edits did not go through `cleanup.py apply-edits`.** The worktree sandbox refuses compound shell lines, and the edits were prose rewrites spanning several lines. I applied them as exact-match old/new pairs (each `old` had to match exactly once, all-or-nothing per batch) with a small helper kept in the session scratchpad, not in the repo. The gates that matter (`diff`, `scan --gate`, `ledger`) are independent of how the text was edited.

**3. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- eval_remote.py: "mirrors SubmitResponse" / "Gen-1 LeaseResponse/SubmitRequest + _apply_submit trio" rewritten (those classes are gone); `D-5 version gate` became "SF-version gate" in three places.
- train.py: "retains its exact prior meaning" / "the new three-way scoring tier" in `SolveResponse` and the "Phase 211 narrows the sentence above" / "Phase 235 amends the above" layering in `SolveRequest` and `PuzzleRevealResponse` were folded into present-tense statements (INVENTORY 7.1 seed #3, a full contract rewrite, was NOT attempted; only tags and the listed rows).
- endgames.py: dropped the history sentence "The old material imbalance + 4-ply persistence proxy is gone", the "Renamed ... design-pivot history" paragraph in `ClockDiffTimelinePoint`, and the "Supersedes the earlier ... FIDE PR mapping" lines.
- insights.py: "Type changed from dict[str, int] to ..." and "replaced the removed time_pressure_cards field" became present-tense descriptions.
- openings.py / users.py / stats.py: "The recency PRESET stays removed", "replacing `lichess_blitz_equivalent_rating` (P-01)" and the `Phase 80 additions` labels rewritten without the history.
- users.py: "(growth report item 16)" removed from the first-touch docstring.

No code token, string literal, Field description, Literal value, alias or directive changed (`diff` exit 0).

**Total deviations:** 1 blocking env prep, 2 plan-text adaptations; none touch behavior.

## Issues Encountered

- `cleanup.py codemod` writes in place when run without `--dry-run`; the plan's step 2 only says `codemod <files>`, so Task 1 ran it for real and reviewed `git diff -U0` afterwards. Several codemod outputs needed follow-up (a lowercase sentence start such as "percentile-first Endgame Stats payload", "Absolute per-side ...", dangling "Phase 109 eval chart models" labels); all were hand-fixed.
- The codemod leaves no `needs hand edit` marker in files, so the second scan was the only way to find the remaining 90 lines in Task 2.

## Known Stubs

None.

## Threat Flags

None. Comments and docstrings only; `cleanup.py diff` compares every name and string token against PHASE_BASE (T-241-12) and Field(description=...) strings are untouched (T-241-13). No package installs beyond the lockfile syncs.

## Self-Check: PASSED

Files verified present: ledgers/241-06.txt, this SUMMARY, all 17 modified app/schemas files. Commits `85c07dbb7` and `9bdb5cf77` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
