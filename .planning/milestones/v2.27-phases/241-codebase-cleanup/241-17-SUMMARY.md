---
phase: 241-codebase-cleanup
plan: 17
subsystem: services
tags: [cleanup, comments, insights, openings, stats]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "extras.py codemod and decision lookup"
provides:
  - "insights_llm.py, insights_service.py, opening_insights_service.py, opening_insights_constants.py, openings_service.py, stats_service.py and opening_lookup.py free of planning tags, with ledgers/241-17.txt"
affects: [241-54, 241-55]

actuals:
  tokens: 38600
  tasks: 2
  commits: 2
plan_head_before: f23d4bc8028fbfc7cf78ce55d95422f0301cb13a
plan_head_after: ca55083b4e2b669ff8042306a8149aa404499a5a

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-17.txt
  modified:
    - app/services/insights_llm.py
    - app/services/insights_service.py
    - app/services/opening_insights_service.py
    - app/services/opening_insights_constants.py
    - app/services/openings_service.py
    - app/services/stats_service.py
    - app/services/opening_lookup.py

key-decisions:
  - "Trailing comments that would push a statement over the formatter width after a tag was stripped were moved to their own line above the statement (_PROMPT_VERSION, _DELTA_WITHIN_NOISE_ELO) instead of letting ruff wrap the statement in parentheses, which would have changed code tokens"
  - "The service-side _TIMELINE_SUBSECTION_IDS stays (INVENTORY section 7 seed: unread); the insights_llm pointer that claimed the two constants must match was dropped as stale"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: ~75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 17: Insights and Openings Services Comment Cleanup Summary

**All planning tags and version/phase narration are gone from the insights and openings services (7 files, about 310 scan matches), prompt text and every non-comment token are unchanged.**

## Accomplishments

- `cleanup.py scan --gate --scope scopes/241-17.txt` exits 0 (7 files, 0 matches); `cleanup.py diff` exits 0 (7 changed, no residue); `cleanup.py ledger` exits 0.
- Ledger `ledgers/241-17.txt` covers all 32 INVENTORY section 6 rows: 31 APPLIED, 1 DEFERRED (INV-L637, the `_apply_a2_filter` docstring, to 241-54 with the `_visible_findings` rename; only its bare "before Phase 214" tag was stripped now). SKIPPED/LEFT: none. One secondary-clause note for INV-L657 (the pointer in insights_llm.py) is recorded as a `#` comment line because the ledger parser rejects non-standard lines.
- Rows were re-verified against the current code before applying (D-10). Two inventoried fixes had to be adapted: INV-L700 named `_trend_tag`, which does not exist (`_trend_info` is the real helper); INV-L704 pointed at `reports/benchmarks-2026-05-04.md`, which does not exist, so the comment now names the benchmark by date.
- Rows whose replacement text asserted a fact were checked: per-class Score Gap bands differ from the global default (L658), `entry_eval_pawns` band is +-0.60 (L659), `non_endgame_elo` comes from `_endgame_elo_logistic` (L661), `per_week_endgame_games` is the per-ISO-week count (L656), `OpeningWDL` rows carry only MG-entry eval fields (L672), `wilson_bounds` lives in `score_confidence` (L703), and the dedupe tie-break matches the sort key (L736).

## Codemod versus hand edits

| Slice | Codemod lines | Hand edits |
|---|---|---|
| insights_llm.py | 52 | 83 flagged lines plus about 16 version-label comments (`v7`, `v12`, ...), via 6 exact-string replacement batches (about 105 replacements) |
| insights_service, opening_insights_service, opening_insights_constants, openings_service, stats_service, opening_lookup | 69 (across 6 files) | 114 flagged lines via 7 replacement batches (about 120 replacements) plus one slice deletion |

`git diff -U0` was reviewed after each codemod run; none of the 121 codemod rewrites had to be reverted. The known codemod punctuation bug did not occur: the `^\s*(#|//|\*)\s*[:;,]\s` grep over the scope found nothing. Hand edits used a throwaway exact-string replacer (`temp/241-17/rep.py`, gitignored) that requires each old string to occur exactly once, so no edit landed on the wrong site.

## Comments deleted as provenance only

- insights_llm.py: skip-set removal note (INV-L702), v21 dispatch-chain paragraph (INV-L733), Phase 68 B4 paragraph (INV-L665), v9/Phase 68 `overall` comment block (INV-L666), WR-06 removal notes, "Phase 88.1 ... re-added" comments, the dangling `.planning/debug/llm-prompt-missing-sections.md` pointers (the file does not exist), and the retired-C4-stage paragraph in `_assemble_user_prompt`.
- insights_service.py: the `_endgame_skill_from_material_rows` deletion note (INV-L732), both removed-helper comment blocks above the endgame-type subsection map (INV-L701), the "Restored from the Phase 87.4 helper name" paragraph (INV-L655).

## Non-inventoried fixes

- insights_llm.py: `_OUTPUT_RETRIES` comment now says what the constant is (structured-output validation retries) instead of citing CONTEXT.md/RESEARCH.md.
- insights_llm.py: 16 prompt-version labels in comments (`v6`, `v7`, `v8`, `v10`, `v11`, `v12`) removed per STYLE-GUIDE 2.2 where they were pure labels. The `v48`/`v49` prompt-version log comments stay: they document when a bump invalidates the cache.
- insights_llm.py: the `v6:` sentence in the `_apply_a2_filter` docstring was left for 241-54 together with INV-L637.
- opening_insights_constants.py, opening_insights_service.py: planning-note and CONTEXT pointers removed (`.planning/notes/...`, `70-CONTEXT.md`).

## Prompt-text safety

- `cleanup.py diff` reports no string-token change in any file, so system and user prompt text, `_PROMPT_VERSION = "endgame_v49"` and the Zone-threshold appendix are byte-identical in token terms.
- tests/services/test_insights_llm.py (128 tests, golden user-prompt comparison included) passes unchanged. No test file was touched.
- insights_service.py comments contain neither the forbidden import phrase nor the banned gather call text; `test_insights_service.py` module_source tests pass.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-17.txt` | exit 0, 7 files, 0 matches |
| `cleanup.py diff --scope scopes/241-17.txt` | exit 0 |
| `cleanup.py ledger --scope scopes/241-17.txt --ledger ledgers/241-17.txt` | exit 0 |
| `ruff check app/services`, `ruff format --check app/services` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| `scripts/check_function_size.py app/ --fail-over-depth 4` | OK, no breaches |
| `tests/services/test_insights_llm.py` | 128 passed |
| insights, opening insights, stats phase-entry, arrow-consistency test files | 260 passed |
| `source_scan_tests.sh --py` commands run serially (no `-n 4`) | 95 passed, then 5 passed |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed |

## Task commits

1. **Task 1: app/services/insights_llm.py** - `457f00eb1`
2. **Task 2: insights_service, opening insights, openings, stats, opening_lookup** - `ca55083b4`

**Plan metadata:** the SUMMARY commit follows these two (`commits: 2` above is measured with `git rev-list --count PLAN_HEAD_BEFORE..HEAD` before the SUMMARY commit).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep and serial pytest in a shared-Postgres worktree**
- **Found during:** Task 1 step 0
- **Issue:** the fresh worktree had no `.venv` (phantom onnxruntime imports in ty) and no `frontend/node_modules`; sibling executors share the dev Postgres, so `-n 4` from `source_scan_tests.sh` and the plan's `pytest -n 4` for test_insights_llm.py would collide on xdist database names.
- **Fix:** `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile only, no new packages); all pytest runs were serial. Environmental, not a plan failure.
- **Files modified:** none tracked.

**2. [Rule 1 - Bug] ruff format wanted to wrap two statements after a trailing comment was shortened**
- **Found during:** Task 1 verification
- **Issue:** `_PROMPT_VERSION = "endgame_v49"  # v49: ...` and `_DELTA_WITHIN_NOISE_ELO ... # ...` are reformatted into parenthesized forms once the tag is removed (the longer original comment kept them under ruff's pragma-comment exemption); that would add code tokens and fail the diff gate.
- **Fix:** the comments moved to their own lines above the statements.
- **Committed in:** 457f00eb1

**3. [Plan adaptation] The INV-L657 secondary note was done in Task 1, not Task 2**
- The pointer sits in insights_llm.py, which Task 1 already edits; the ledger records it as a `#` line (the parser rejects non-standard lines), and the pointer text was dropped rather than reworded because the service constant it named is unread.

**Total deviations:** 1 blocking environment prep, 1 formatter-driven restructure, 1 ordering adaptation.
**Impact on plan:** none on scope; no code token and no string changed.

## Known Stubs

None.

## Threat Flags

None. Only Python comments and docstrings changed (T-241-31 mitigated by the token diff and the golden prompt test; T-241-32 by running the module_source tests).

## Notes for downstream plans

- 241-54 owns INV-L637 (the `_apply_a2_filter` docstring, which still starts "A5 + A2: ..." and carries a "v6:" label) and the `_apply_*_filter` renames; comments in insights_llm.py keep the current function names (`_apply_a2_filter`, `_apply_c2_filter`, `_apply_c3_filter`, `_apply_c5_filter`, `_apply_c6_filter`).
- The `A4`/`C2`/`C5`/`C6` filter-stage labels in insights_llm.py are defined by the `_assemble_user_prompt` docstring itself, so they were left; they are not planning tags.

## Self-Check: PASSED

Files verified present: ledgers/241-17.txt, this SUMMARY. Commits verified as ancestors of HEAD: 457f00eb1, ca55083b4.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
