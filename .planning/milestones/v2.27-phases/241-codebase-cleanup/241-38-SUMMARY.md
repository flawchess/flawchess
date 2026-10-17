---
phase: 241-codebase-cleanup
plan: 38
subsystem: frontend-comments
tags: [cleanup, comments, analysis-components, planning-tags]
requires:
  - phase: 241-04
    provides: "TS/JSX scan and token diff in cleanup.py (fe_support.py)"
provides:
  - "21 analysis components in frontend/src/components/analysis free of planning tags, extraction history and UAT/quick-task provenance, with ledgers/241-38.txt covering all 18 INVENTORY rows"
affects: [241-59, 241-65]
actuals:
  tokens: 23000
  tasks: 2
  commits: 2
plan_head_before: 41ee842f0c77227853d89b94d8df68b15228ce42
plan_head_after: a061ee49e3b5ff10b81d3d3ff4c6b1e08eaa14d2
tech-stack:
  added: []
  patterns:
    - "Comment loop: rows -> codemod (written, then git diff -U0 review) -> hand edits via exact-string pair files in temp/241-38 -> scan --gate / diff / ledger"
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-38.txt
  modified:
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/AnalysisTabs.tsx
    - frontend/src/components/analysis/AnalysisPlayerBar.tsx
    - frontend/src/components/analysis/AnalysisBoardStage.tsx
    - frontend/src/components/analysis/AnalysisDesktopCards.tsx
    - frontend/src/components/analysis/EngineToggleHeader.tsx
    - frontend/src/components/analysis/MovesByRatingChart.tsx
    - frontend/src/components/analysis/EngineLines.tsx
    - frontend/src/components/analysis/FlawChessEngineLines.tsx
    - frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
    - frontend/src/components/analysis/EvalBar.tsx
    - frontend/src/components/analysis/MaiaHumanPanel.tsx
    - frontend/src/components/analysis/MaiaMoveQualityBar.tsx
    - frontend/src/components/analysis/PasteModal.tsx
    - frontend/src/components/analysis/UnifiedMovePopover.tsx
    - frontend/src/components/analysis/AnalysisTagsPanel.tsx
    - frontend/src/components/analysis/EloSelector.tsx
    - frontend/src/components/analysis/EngineUnsupportedNotice.tsx
    - frontend/src/components/analysis/GemMoveBadge.tsx
    - frontend/src/components/analysis/ProseSpan.tsx
    - frontend/src/components/analysis/TemperatureSelector.tsx
key-decisions:
  - "Open-seed pointers (SEED-092, 106, 108, 158, 197 are in .planning/seeds/) were NOT kept: every one in these files was provenance for shipped work, not a pointer to deferred work, so all were dropped"
  - "Bug-fix comments (MaiaMoveQualityBar stablePerElo, EngineLines mobile row height) keep what broke and why; only the tags went"
requirements-completed: [D-01, D-04, D-10, D-11, D-12, D-13, D-15]
duration: 70min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 38: Analysis Components Comment Cleanup Summary

**All 21 analysis components read as the current UI: planning tags, "Extracted from Analysis.tsx (215-06)" paragraphs, UAT and quick-task provenance are gone, 18 of 18 INVENTORY rows are APPLIED, and the token diff against PHASE_BASE is empty (comments only).**

## Performance

- **Tasks:** 2, one commit each
- **Files:** 21 components edited, 1 ledger created
- **Diff:** 22 files changed, 475 insertions, 543 deletions (comment lines only)

## Task Commits

1. **Task 1: tree, tabs, player bar, board stage, desktop cards, toggle header, chart (8 rows)** - `e36b1dc13` (`chore(comments): frontend analysis tree, tabs, board stage`)
2. **Task 2: engine lines, verdict, eval bar, Maia panels, paste modal, popovers, rest (10 rows)** - `a061ee49e` (`chore(comments): frontend analysis engine lines, Maia, popovers`)

`commits: 2` is measured with `git rev-list --count 41ee842f0..HEAD` before this SUMMARY commit.

## Counts

| Item | Count |
|---|---|
| INVENTORY rows | 18 (all APPLIED, each re-verified against the code first, D-10) |
| Codemod rewrites | 43 lines (Task 1 run, 7 files) + 63 lines (Task 2 run, 11 files) = 106 |
| Flagged "needs hand edit" by the codemod | 63 (Task 1) + 104 (Task 2) |
| Scan matches left after the codemod | 40 in Task 1's two big files after hand-editing the others; 166 across the 14 Task 2 files before its codemod run |
| Hand edits | every remaining flagged site, plus untagged provenance next to them (see Deviations 3) |
| Final `scan --gate` | 0 matches over scopes/241-38.txt (21 files) |

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-38.txt` | exit 0, 0 matches |
| `cleanup.py diff --scope scopes/241-38.txt` | exit 0 (21 files selected, 21 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-38.txt --ledger ledgers/241-38.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed (same as the untouched baseline) |
| `source_scan_tests.sh` python half, run serially | 95 passed + 5 passed |
| `vitest run src/components/analysis src/pages/__tests__/Analysis.test.tsx` | 15 files / 323 tests passed |
| Mutation check (EvalBar `'analysis-eval-bar'` -> `'analysis-eval-bar2'`, scratch copy) | `cleanup.py diff` reported the token change; restored, diff exit 0 |

Step 0 baseline on the untouched tree: lint and the fe source-scan tests passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages) before the baseline.

**2. [Environmental] Shared Postgres**
- Per the dispatch instructions the python half of `source_scan_tests.sh` ran serially (no `-n 4`), same file list. Not a plan failure.

**3. [Rule 2 - stale content, STYLE-GUIDE 2.2] Edits beyond the gated tag pattern**
- The scan gate only matches `Phase NNN`, `D-NN`, `SEED-NNN`, quick ids and similar. Neighbouring provenance that carried the same information was cleaned in the same comments: `(164 UAT)`, `(155 UAT)`, `(151.1 UAT)`, `UAT 179`, `Quick w8k item N`, `resolved decision N`, `Task 3`, `Option A/B` labels in MovesByRatingChart, `SC-9`, `PAINT-LIVE`, `Level-1/Level-2` nesting history.
- MaiaHumanPanel: "(iOS gate, no WASM SIMD)" became "(no WASM SIMD)"; the only unsupported reason left in `EngineUnsupportedNotice` is `no-wasm-simd` and the blanket iOS gate no longer exists.
- AnalysisTabs: `movesTab`/`movesCard` helper names in the MoveListHeaderContent comment became `MovesTab`/`MovesCard` (the components that exist now).
- History narration rewritten as a rule rather than deleted: MaiaMoveQualityBar ("Don't add a trailing (eval) parenthetical", "Don't back this with `useState`"), FlawChessAgreementVerdict ("Don't reuse the Turn on Stockfish prompt here"), AnalysisTabs/VariationTree (rules about the absolute-fill scroller and `items-stretch`).

**Total deviations:** 1 blocking env prep, 1 environmental note, 1 content-scope extension. No code, testid, Umami attribute, copy, or identifier changed; DesktopTree/MobileTree, the PlayerBar wrapper and formatScore are untouched (241-59), `definition` in AnalysisTagsPanel untouched (241-65).

## Issues Encountered

- The codemod collapsed `//     (D-08), past which ...` into `//, past which ...` in AnalysisBoardStage.tsx (known bug); fixed by hand and the whole scope grepped for `^\s*(#|//|\*)\s*[:;,]\s` afterwards (clean). It also left `* — callers must treat a null result` in FlawChessAgreementVerdict.tsx and several over-long merged lines; all re-wrapped.
- The worktree sandbox rejects compound shell lines, so commands were issued one at a time.

## Suspected stale text outside this plan's files (not touched)

- `frontend/src/components/bots/PersonaGrid.tsx:117` still says "of Analysis.tsx's FlawChessInfoTooltip"; that helper no longer exists in Analysis.tsx (the live one is the private `FlawChessInfoTooltip` in `AnalysisTabs.tsx`). Whoever owns PersonaGrid.tsx should reword it.
- `frontend/src/components/analysis/__tests__/EngineUnsupportedNotice.test.tsx:4` mentions "the iOS gate" (test file, other plan).
- `VariationTree.tsx` `decorations` prop doc still describes "tactic mode"; left because the prop's current callers were not re-verified here.

## Known Stubs

None.

## Threat Flags

None. Comments only; T-241-55 mitigated by `cleanup.py diff` (token-stream compare of markup, strings and numerics) and lint.

## Self-Check: PASSED

Files verified present: ledgers/241-38.txt and all 21 components. Commits `e36b1dc13` and `a061ee49e` are ancestors of HEAD.
