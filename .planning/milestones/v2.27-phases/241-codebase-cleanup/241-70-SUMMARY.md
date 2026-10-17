---
phase: 241-codebase-cleanup
plan: 70
subsystem: codebase-cleanup
tags: [verification, pre-merge-gate, token-diff, ledger-closure]
requires:
  - phase: 241-codebase-cleanup
    provides: plans 241-01..241-69 (comment cleanup, renames, ledgers, rename maps)
provides:
  - phase-wide proof that Phase 241 changed only comments, docstrings, test names and approved renames
  - full pre-merge gate evidence on the phase head (6caf1720d)
  - owner report with readiness and open decisions
affects: [squash-merge of phase 241 to main]
tech-stack:
  added: []
  patterns: [rename-adjusted scope copies for the final token diff]
key-files:
  created: [.planning/phases/241-codebase-cleanup/241-70-SUMMARY.md]
  modified: []
key-decisions:
  - "Final scan/diff ran over rename-adjusted copies of the 49 scope files (temp/241/scopes, gitignored) because ten renamed files made the committed scope lists point at paths that no longer exist"
  - "INV-L354 carries two APPLIED ledger lines (241-02 and 241-07) because the row names two clauses in two files; both are APPLIED, so no conflicting status"
requirements-completed: [D-06, D-08, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17]
status: complete
commits: 0
plan_head_before: 6caf1720d03e175161555b244ebc1670c8b1c76e
plan_head_after: 6caf1720d03e175161555b244ebc1670c8b1c76e
actuals:
  tokens: 0
  tasks: 3
  commits: 0
duration: ~1h
completed: 2026-10-16
---

# Phase 241 Plan 70: Phase-wide verification and pre-merge gate Summary

The union of 69 plans (326 commits, 1,115 files, PHASE_BASE `3bce9acb6` to `6caf1720d`) is proven comment-docstring-test-name-and-rename-only, every INVENTORY section 6 row has a final status, and the full CLAUDE.md pre-merge gate plus a serial pytest run are green. No code or comment commit was needed; this plan adds only this SUMMARY.

## Phase-wide checks

Every check ran on the phase head (HEAD `6caf1720d`, clean tree, `uv sync --group maia-inference` and `npm ci` done in the worktree first).

| # | Check | Result |
|---|-------|--------|
| 1 | `cleanup.py scan --gate --all-allow` over all 49 scopes | exit 0: `scan: 1307 files, 0 matches, 0 blocking` |
| 2 | `cleanup.py diff --all-allow` over all scopes plus 4 `--outside` files | exit 0: `diff: 1311 files selected, 1115 changed`; 13 residue lines, all "(allowed: ...)" (table below) |
| 3 | `cleanup.py outside` | lists exactly 3 paths (see "Files changed outside scope") |
| 4 | Ledger closure | all 36 scopes with section 6 rows pass `cleanup.py ledger`; see "Ledger closure" |
| 5 | `cleanup.py absent` over all 18 rename maps | exit 0: `128 rows checked, 0 hits` |
| 6 | Generated drift: the four `scripts/gen_*.py`, then `git diff --exit-code --stat frontend/src/generated/ reports/data/` | all four generators ran, diff exit 0, no drift, nothing to regenerate or commit |
| 7 | Identifier scans | `scan --identifiers app/`: 177 files, 0 matches. Frontend D-16 grep: only `preSeed119Verdict` (test-local). `scan --identifiers tests/`: 13 matches, all the three known test constants (see "D-16 report") |
| 8 | Spot review | see "Spot review" |

Deviation note for checks 1, 2 and 4: the committed `scopes/*.txt` still list the pre-rename path of ten files that later plans renamed, so `cleanup.py` aborted with `frontend/src/hooks/useWinCelebrationHold.ts does not exist`. I generated rename-adjusted copies (`git diff -M` old to new path, same file names so `allow/241-NN.tsv` still resolves) in the gitignored `temp/241/scopes/` and ran the checks over those. The committed scope files are unchanged. Renamed entries: useWinCelebrationHold.ts to useResultDialogHold.ts, useTrainWalkthrough.ts to useTrainTour.ts, TrainReminderButton.tsx to useTrainReminderSlot.tsx, analysisCoverageCopy.tsx to .ts, BulletConfidencePopover.tsx to EvalConfidencePopover.tsx, WdlConfidenceTooltip.tsx to ScoreConfidenceTooltip.tsx, MiniBoard.tsx to BookmarkMiniBoard.tsx, and the three matching test files.

## Allowed residue

Scan: zero allowed items. Token diff: 13 residue lines, each carrying the toolkit's "(allowed: ...)" reason; none is a behavior change.

| File:line | Residue | Reason (from the allow list) |
|-----------|---------|------------------------------|
| app/repositories/game_flaws_repository.py:169 | `+ ,` | ruff format magic trailing comma after the FLAW_BLOB_COLUMNS rename lengthened the line (241-53) |
| app/repositories/train_leaderboard_repository.py:137 | `+ ,` | ruff format magic trailing comma after the X5 rename lengthened the SolveTotals constructor line (241-66) |
| app/services/endgame_zones.py:18, :848 | `TimeControlBucket` import added, local alias removed | TcBucket alias replaced by the schema import, INVENTORY section 5 M row (241-54) |
| app/services/insights_llm.py:46, :50, :72 | parenthesized import + `TimeControlBucket` | same alias replacement; ruff wrapped the import (241-54) |
| app/services/insights_service.py:55, :76 | `TimeControlBucket` import moved | same alias replacement (241-54) |
| app/services/library_service.py:1690 | `MIN_TACTIC_CHIP_CONFIDENCE: int = MIN_TACTIC_CHIP_CONFIDENCE` removed | X4: alias line removed, one value one name (241-67) |
| frontend/src/components/ui/drawer.tsx:0 | `@knipignore` directive removed | INV-L1118: drawer has consumers now, knip passes without it (241-45) |
| frontend/src/hooks/useTrainRevealTree.ts:466 | `+ : liveEval` | property shorthand `live` expanded to `live: liveEval` so the useTreeMoveGrading option keeps its name (241-60) |
| tests/services/test_train_leaderboard.py:466 | `+ ,` | ruff format magic trailing comma after the X5 rename (241-66) |

No test assertion changed (the diff tool's assertion/test-name rules reported nothing outside the table).

## Files changed outside scope

`cleanup.py outside` printed exactly:

| Path | Plan | Covered by |
|------|------|------------|
| frontend/CLAUDE.md | 241-61 | `--outside` rename-only text check, passed |
| scripts/tactic_tagger_report.py | 241-67 | `--outside` token diff, passed |
| .claude/skills/tactic-tagger-report/SKILL.md | 241-67 | `--outside` rename-only text check, passed |

`scripts/benchmarks/chapter5.py` was passed with `--outside` as well and is unchanged. No path under frontend/src/generated/ or reports/data/ changed (drift check clean). Nothing else is outside the in-scope set, so no wire, DB, testid, storage, Umami, Sentry, URL or env name moved (D-17).

## Ledger closure

- INVENTORY section 6 has 772 rows (`## 6.` to `## 7.`, table rows starting with `| \``); 772 distinct ids have a final status across ledgers: 759 APPLIED, 10 MOVED, 4 LEFT, 0 SKIPPED. Set difference both ways is empty.
- All 5 `DEFERRED to 241-NN` lines (INV-L341 to 241-52, L960 to 241-65, L1298 and L1299 to 241-60, L637 to 241-54) resolve to a final status in the target ledger.
- LEFT with reasons, as required: INV-L490 (241-10, conditional dead-code removal, owner approval), INV-L1281 (241-41, type lacks guest_train, a code change), INV-L1307 (241-33, stale byte constants, a code change), INV-L1336 (241-41, branch likely dead code, INVENTORY section 7.2 #12).
- One literal mismatch with the plan's uniqueness check: INV-L354 has two APPLIED lines (ledgers/241-02.txt for reset_password_rate_limiter.py, ledgers/241-07.txt for the app/users.py clause). The row text names both clauses, so the split is intentional and the statuses agree. The plan's `uniq -d` one-liner would flag it; I read it as satisfied.
- INV-L943 and INV-L1251 do not appear in `cleanup.py rows` output for the final scopes (their INVENTORY path is the pre-rename name, TrainReminderButton / useWinCelebrationHold) but have APPLIED lines in 241-37 and 241-28.

## D-16 report

- Backend (241-66): `scan --identifiers app/` found nothing; no D-16 renames, no cross-layer candidates. Re-run now: 177 files, 0 matches.
- Frontend (241-69): the probe over frontend/src (excluding generated/) returned only test-local `preSeed119Verdict`; no production finds, no D-16 commits. Re-run now: same single name (frontend/src/lib/__tests__/trainRevealCache.test.ts:187, 188, 191).
- Cross-layer candidates: none.
- Tagged test-level names left for the owner (not renamed, reported by 241-66 and 241-69): `_PHASE_169_SHAPED_PGN` (tests/test_bot_pgn_clk_roundtrip.py:27, 47), `_SEED076_PGN` (tests/test_eval_worker_endpoints.py, 9 uses), `PHASE_116_REVISION` (tests/test_migration_116_full_evals.py:37, 301), `preSeed119Verdict` (frontend). 241-25 also reported `_compile_flaw_filter_sql_129` (tests/test_library_repository.py, 9 uses); the final `scan --identifiers tests/` run lists 13 matches, which is the first three names above (the fourth is not tag-shaped to the scanner).

## Spot review

`git diff --word-diff` against PHASE_BASE for ten files; nothing read wrong.

1. app/repositories/game_flaws_repository.py: tag removal, FLAW_BLOB_COLUMNS to FLAW_BLOB_AND_TACTIC_COLUMNS, prose now states the JSON-null-vs-SQL-NULL reason. Good.
2. app/services/library_service.py: provenance dropped, `_TACTIC_CHIP_CONFIDENCE_MIN` to `MIN_TACTIC_CHIP_CONFIDENCE`, docstring rewritten present-tense. Good.
3. app/core/opponent_strength.py: PRESET_THRESHOLD to SIMILAR_THRESHOLD only (rename row X2).
4. frontend/src/hooks/useTrainTour.ts (rename): header rewritten, WALKTHROUGH_* to TOUR_*, types renamed, tags dropped. Good.
5. frontend/src/hooks/useResultDialogHold.ts (rename): hook renamed, narration ("1300ms was a guess") replaced by the invariant. Good.
6. frontend/src/components/insights/ScoreConfidenceTooltip.tsx (rename from WdlConfidenceTooltip): rename plus one dropped "Quick task" line.
7. frontend/src/components/ui/drawer.tsx: `@knipignore` removed, comment trimmed; knip passes.
8. tests/services/test_insights_llm.py: requirement tags (LLM-01, INS-04...) and Phase/D-NN prefixes dropped from docstrings and comments; test bodies untouched. (Remaining lettered shorthand: see Owner report.)
9. tests/test_migration_116_full_evals.py: "Phase 116" becomes "the full_evals_completed_at migration"; the constant `PHASE_116_REVISION` untouched (owner list).
10. frontend/src/components/insights/EvalConfidencePopover.tsx plus ScoreConfidenceTooltip.tsx call sites covered by the frontend build and 5,649 tests below.

Rename plans represented: 241-58 (useResultDialogHold), 241-69 (useTrainTour), 241-61/64 (confidence components), 241-54 and 241-66/67 (aliases and constants).

## Pre-merge gate

Run on the phase head in CLAUDE.md order. ruff format and ruff check were run in check mode first; both were clean, so `--fix` and `format` would have changed nothing and there is no `style(241)` commit. `git status` was clean after the whole gate.

| Command | Result |
|---------|--------|
| `uv run ruff format --check app/ tests/ scripts/ analysis/` | 536 files already formatted |
| `uv run ruff check .` | All checks passed |
| `uv run ty check app/ tests/ scripts/` | All checks passed |
| `uv run --project analysis --with ty ty check analysis/` | All checks passed |
| `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` | OK: 1225 functions scanned, no breaches |
| `npm --prefix frontend run lint` | clean (eslint) |
| `npm --prefix frontend run build` | passes (tsc -b + vite + PWA) |
| `npm --prefix frontend test -- --run` | 333 files / 5649 tests passed |
| `npm --prefix frontend run knip` | clean (two pre-existing configuration hints only: `src/generated/endgameZones.ts` ignore entry and `.css` extension) |
| `uv run pytest -n auto -x -q` (log temp/241/pytest-auto.log) | 5494 passed, 19 skipped, 47 warnings in 90.69s |
| serial `uv run pytest -x -q` (log temp/241/pytest-serial.log) | 5494 passed, 19 skipped, 15 warnings in 294.99s |

Both pytest runs fit in the foreground Bash cap, so nothing was backgrounded from this agent. (`cleanup.py diff` over 1,311 files ran about 12 minutes and was moved to the background by the harness; it completed with exit 0.)

## Owner report

**(a) Readiness.** All gates are green on the phase head. The branch has 326 commits since PHASE_BASE and touches 1,115 files outside .planning/: app 152 files (+6,901/-8,083), tests 225 (+4,646/-5,018), frontend 736 (+11,954/-13,482, includes frontend/CLAUDE.md), scripts 1, .claude 1; net -3,082 lines. Ready for the local squash-merge to main; this plan did not merge, push, deploy or edit CHANGELOG.md. Per the orchestrator note, merge from the main checkout with the usual cherry-pick/squash procedure.

**(b) CHANGELOG.** The phase has no user-facing change, so nothing was added under `## [Unreleased]`. Add an internal line only if you want one.

**(c) Open decisions for the owner.**

1. Tagged test-level names left unrenamed (241-66, 241-69, 241-25): `_PHASE_169_SHAPED_PGN`, `_SEED076_PGN`, `PHASE_116_REVISION`, `_compile_flaw_filter_sql_129`, `preSeed119Verdict`. A rename needs an allow row or rename map for the token diff.
2. INVENTORY section 6 rows LEFT: INV-L490 (PositionBookmarkRepository alias + `import sys as _sys`, dead-code removal, 241-10), INV-L1281 (`guest_train` missing from a type, 241-41), INV-L1307 (stale byte constants, 241-33), INV-L1336 (likely dead branch, section 7.2 #12, 241-41). No row ended SKIPPED.
3. 241-10: `llm_log_repository.get_latest_log_by_hash` has only test callers (section 7 dead-code candidate, not removed).
4. 241-43 INV-L1012 finding: benchmarks-latest.md recommends the cap activates at 14/20 cells, but the `ScoreGapByTimePressureChart.tsx` comment (~line 63) still says "all 20 (TC, quintile) cells cap at +-0.06"; the constants `PRESSURE_SCORE_GAP_NEUTRAL_MIN/MAX` were left alone.
5. 241-68 observation: `app/core/opponent_strength.py` has no importer (only a smoke import was done); dead-code candidate.
6. 241-64 planner interpretation: three drawer props were renamed beyond the INVENTORY list (`onOpenBookmarkSidebar`, `onFilterSidebarOpenChange`, `onBookmarkSidebarOpenChange`, commit f4d83a9ef). 241-61 also edited one file outside its list (`frontend/src/hooks/__tests__/useEvalCoverage.test.tsx`) for the isPending to hasPendingEvals rename.
7. String literals are off-limits by D-15, so assertion messages and f-strings still carry planning tags and closed-seed ids (241-25 list: test_game_flaws_model.py "after Phase 112", test_guest_cleanup_service.py "(D-08)", test_import_service.py "Pitfall 2, 90-RESEARCH.md", test_migration_suppress_ungated_tactic_tags.py "D-06 sentinel", test_library_repository.py "Quick 260717-gmg", plus the many `SEED-079`, `SEED-054`, `SEED-049` mentions in test messages). Decide whether a follow-up string pass is wanted.
8. Lettered planning shorthand the D-11 pattern does not match remains in tests (reported by 241-54): `tests/services/test_insights_llm.py` lines 704-727 ("C6 tail-cap", "C5", "C2 90-day all_time_cutoff"), 1075/1137 ("A2 filter"), 1219 ("A4"), 2269-2363 (C2/C5), plus `tests/services/test_insights_service_series.py:702` (C5), `tests/services/test_canonical_slice_sql.py:967, 985` (A2, A4) and `tests/services/test_best_move_candidates.py:246, 344` (C1/C2). The labels have no definition left in app code. I did not sweep them: they are outside the STYLE-GUIDE tag definition, and editing about 20 lines across four test files is new scope. Flagging per the orchestrator note.
9. Open-seed pointer list: the only seed files in .planning/seeds/ referenced by code pointers are SEED-129, SEED-130 and SEED-189 (all still present). No pointer's seed closed during the phase that I could find; every other `SEED-NNN` mention in app/tests/frontend/src sits inside a string literal (item 7).
10. Several plans added allow/*.tsv rows for ruff-format residue and wrapped imports (6 allow files, 15 lines; all listed above with reasons). 241-51 Task 1 and Task 2 were salvaged from a dead executor and a saved partial patch (commit 0ecfad0c9); both are on the branch and covered by the phase-wide diff.
11. Scope files: the committed `scopes/*.txt` carry pre-rename paths for ten renamed files; anyone re-running the phase-wide check later needs rename-adjusted copies (or a one-line fix of those ten entries).

**(d) Glossary note (D-01).** STYLE-GUIDE section 3.3 binds edited prose and new code only. Comments that this phase did not touch may still use non-canonical words (for example "walkthrough" or "sidebar" in unedited prose); that is expected, not a miss.

## Deviations from Plan

**1. [Rule 3 - Blocking] Stale scope paths.** Found during Task 1, check 1. The committed scope lists named ten files at their pre-rename paths, so `cleanup.py` exited 2. Fix: rename-adjusted copies under gitignored temp/241/scopes/ (see Phase-wide checks). No tracked file changed.

**2. [Plan note] Not run inline.** The plan assumed the orchestrator would run this inline. It ran as a worktree executor; the long runs fit the foreground cap, so the concern did not materialize. Pytest flags `-q -p no:cacheprovider` were added.

**3. [Plan note] INV-L354 double status** (see Ledger closure); satisfied by intent, not by the literal `uniq -d` check.

**Total deviations:** 1 auto-fixed (blocking), 2 plan notes. **Impact:** none on the proof; same files, same checks.

## Known Stubs

None.

## Threat Flags

None. This plan changed no files outside this SUMMARY.

## Self-Check: PASSED

- All 8 required sections present (`grep -c` of the eight headings returns 8).
- SUMMARY.md exists at the plan path; no code commits were produced by this plan, so there are no task hashes to verify (`commits: 0`, `plan_head_before == plan_head_after == 6caf1720d`).
- Gate evidence reproduced above comes from the commands run in this session on an unmodified tree (`git status --short` empty before this file was written).
