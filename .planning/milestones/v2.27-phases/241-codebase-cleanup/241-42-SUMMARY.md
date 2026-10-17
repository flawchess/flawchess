---
phase: 241-codebase-cleanup
plan: 42
subsystem: frontend-comments
tags: [cleanup, comments, library, results, jsx, token-diff]

requires:
  - phase: 241-04
    provides: "cleanup.py TypeScript/JSX support (scan, codemod, diff, ledger)"
provides:
  - "Library and results components (27 files in scopes/241-42.txt) free of planning tags, with ledgers/241-42.txt"
affects: [241-62, 241-65]

actuals:
  tokens: 33000
  tasks: 2
  commits: 2
plan_head_before: 2b0fd4980a2e07ed386b376c568e993fd15324fb
plan_head_after: 885b4e797909c678db0e2e9097c01e58ccbf592e

tech-stack:
  added: []
  patterns:
    - "Codemod first, then hand edits with exact-string python replacements (assert count == 1) instead of apply-edits JSON"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-42.txt
  modified:
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/TagChip.tsx
    - frontend/src/components/library/TacticMotifChip.tsx
    - frontend/src/components/library/MoveStats.tsx
    - "plus 19 more library/, library/stats/ and results/ components (25 frontend files in total; GameCard.tsx, GameCardList.tsx were already clean and stay untouched)"

key-decisions:
  - "Comments name current identifiers: hoverPly / flawId / passesContext / renderDesktopExploreButton / definition untouched; the INV-L997 comment names no identifier at all, so the later hoverPly rename (241-65) has nothing to update"
  - "INV-L1318 secondary clause is a # comment line in the ledger (the parser accepts only plain INV-L<n> lines), as 241-04 did for INV-L1070"

patterns-established:
  - "Re-verify every inventory claim against code before applying (several rows needed different wording than the inventory proposed, see Deviations)"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

completed: 2026-10-16
status: complete
---

# Phase 241 Plan 42: Library and Results Components Comment Cleanup Summary

**Planning tags and removed-feature narration are gone from the 27 Library/results components (204 scan matches to 0), the token diff against PHASE_BASE is empty, and all 39 INVENTORY rows plus the INV-L1318 secondary clause are in the ledger.**

## Accomplishments

- First scan of scopes/241-42.txt: 204 matches in 27 files. Final `scan --gate`: 0 matches. `diff`: 27 selected, 25 changed, no residue (no code, testid template, Umami attribute, copy or markup token changed).
- Ledger: 19 APPLIED/DEFERRED rows in task 2 (INV-L960 DEFERRED to 241-65), 20 APPLIED rows in task 1, plus the `# INV-L1318 (secondary LibraryGameCard.tsx): APPLIED` comment line. `cleanup.py ledger` exits 0.
- Codemod vs hand edit: the codemod rewrote 29 lines in task 1 (EvalChart, LibraryGameCard) and 58 lines in the other 15 files; the other roughly 120 tagged lines and every inventory row were hand edits (exact-string replacement scripts, each asserting a single match). `git diff -U0` was reviewed after both codemod runs; two bad results (`//. Quick 260620-pza:` and `//. The label doubles` in LibraryGameCard) were fixed by hand, and a few merged lines were re-wrapped.
- Planning provenance the scan regex misses was removed by a broader grep: `UI-SPEC` (SeverityBadge x2, LibraryGameCardList x2, TacticMotifChip), `locked decision 5` (EvalChart), `Pitfall 6/7` (EvalChart), `UAT 179` (MoveStats, ChipColumn, LibraryGameCard), `plan 260610-vru`, `item 4/5`, `DECISION 1`, `IN-03`, `SEED-112 pt.2`, `Plan 02/03`, `QUEUE-08`, `T-118-13`, and a `§5 refresh` reference (now "a benchmark refresh").

## Task Commits

1. **Task 1: LibraryGameCard.tsx and EvalChart.tsx** - `0f17d5e05` (`chore(comments): frontend LibraryGameCard and EvalChart`; also creates the ledger)
2. **Task 2: rest of the Library components, pagination, plan gates** - `885b4e797` (`chore(comments): frontend Library components (rest)`)

`commits: 2` above is measured with `git rev-list --count 2b0fd4980..HEAD` before the SUMMARY commit.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-42.txt` | exit 0 (27 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-42.txt` | exit 0 (27 selected, 25 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-42.txt --ledger ledgers/241-42.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean (baseline clean too) |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed |
| Python half of `source_scan_tests.sh`, run serially (no `-n 4`, same file list) | 95 passed + 5 passed |
| `npm test -- --run src/components/results src/components/library src/components/analysis src/pages/library` | 36 files / 530 tests passed |

The Python half was run without `-n` because sibling executors share the dev Postgres (environmental, not a plan failure).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only, no new packages) before the baseline; no tracked files changed. Baseline lint was clean.

### Inventory wording corrected after re-verification (D-10)

- **INV-L980**: the inventory text said the sticky hover pins the controlled value for a frame; the slider is bound to `sliderPly`, so the comment says the hover is freed so the crosshair and tooltip track the thumb immediately.
- **INV-L982**: the inventory proposed heights from memory; the actual callers pass `h-[104px]` (card desktop), `h-[114px]` (card mobile) and `h-[120px]` (analysis board); the component docblock also stated the stale desktop/mobile pair and now says the default is `h-[116px]`.
- **INV-L994**: `formatTimeControl` is imported, not copied; only `formatDate` is described as copied.
- **INV-L1038**: ledger notes that `Card` still has an `overflowVisible` prop; LibraryGameCard just passes none, so only the comment was deleted.

### Non-inventoried fixes (STYLE-GUIDE 2.2, stale content next to removed tags)

- FlawCard.tsx: "(promotion, self-interference)" became "(self-interference, clearance)" (same stale variant as INV-L1318; promotion now has a family). FlawCard's "Allowed is decision-anchored (+1 vs missed)" is still true there (default `anchored=true`) and was kept without the tag.
- LibraryGameCard.tsx: the `tacticDepthByPly` comment claimed "Allowed is decision-anchored (+1 vs missed)" while the call passes `anchored=false`; that sentence was dropped.
- ChipColumn.tsx and TacticMotifGroup.tsx: the `footer` docs described a desktop Explore button that no longer exists and no caller passes `footer`; ChipColumn's claim that the footer "renders even when the column is empty" was false (`isEmpty` returns null first). Both were rewritten to say only what the prop does. ChipColumn's "md breakpoint matches the game card body switch" (the card switches at lg) became "the md breakpoint is where the label stacks above the chips".
- TacticMotifGroup.tsx: dropped "Replaces the old flat, prefix-per-chip row" history.
- TagChip.tsx / TacticMotifChip.tsx: "Caller is responsible for beta-gating" and "preserves the legacy store-derived ring" history reworded.
- GapPopover.tsx: "(including the D-08 stopgap)" now names the stopgap it meant (blitz/bullet-reads-rapid, confirmed by the Stats test comment).
- MoveStats.tsx: dropped "matches the former collapsed I/M/B badges" and "Replaces the old severity-badge row + Show more button".

No `D-`/Phase tag was kept; no `(see SEED-NNN)` pointer existed in the scope, so no allow-list entry was needed.

## Prohibitions honoured

- No identifier renames (`hoverPly`, `onHoverPlyChange`, `renderDesktopExploreButton`, `passesContext`, `flawId`, `definition`, `analysisCoverageCopy.tsx` all unchanged; INV-L960 DEFERRED to 241-65).
- The MoveStats mobile expand-toggle testid (`move-stats-expand-toggle`, suspected bug) is untouched.
- No `prettier --write`, no test or assertion changes, no STATE.md / ROADMAP.md edits.

## Known Stubs

None.

## Threat Flags

None. Comments only; T-241-59 mitigated by the empty token diff (every testid template, Umami attribute and markup token compared) plus lint, build and tests.

## Notes for downstream plans

- 241-65 (the `flawId` to `gameId` rename) must land INV-L960 in TacticMotifChip.tsx: the doc line reads "The flaw id used to make data-testid unique within a card. Mirrors the gameId param in TagChip."
- 241-35 owns the primary INV-L1318 clause in lib/tacticComparisonMeta.ts; the LibraryGameCard.tsx clause is done here.
- The ledger line for the INV-L1318 secondary clause is a `#` comment (parser limitation), as with 241-04's INV-L1070.

## Self-Check: PASSED

Files verified present: ledgers/241-42.txt and the 25 edited frontend files (git status clean after the second commit). Commits `0f17d5e05` and `885b4e797` verified as ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
