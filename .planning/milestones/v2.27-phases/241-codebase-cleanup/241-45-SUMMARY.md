---
phase: 241-codebase-cleanup
plan: 45
subsystem: frontend-comments
tags: [cleanup, comments, frontend, filters, ui, knip]

requires:
  - phase: 241-04
    provides: "cleanup.py FE support (scan/diff/codemod/ledger for .ts/.tsx)"
provides:
  - "components/filters and the small component folders (admin, auth, feedback, icons, settings, ui, bookmarks, data/trollOpenings) free of planning tags, with ledgers/241-45.txt and allow/241-45.tsv"
affects: [241-51, 241-57, 241-63, 241-68]

actuals:
  tokens: 19000
  tasks: 2
  commits: 2
plan_head_before: 92ed609e756c92c5245d71bbcfaf5a80a2f150f8
plan_head_after: 0e97d2085763b4a50316aa8fe390a93ed128f4fd

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-45.txt
    - .planning/phases/241-codebase-cleanup/allow/241-45.tsv
  modified:
    - frontend/src/components/filters/ (10 files)
    - frontend/src/components/ (EndgamesProcessingState, EvalCoverageHeader)
    - frontend/src/components/admin/, auth/, feedback/, icons/, settings/, ui/, position-bookmarks/ (28 files)
    - frontend/src/data/trollOpenings.ts

key-decisions:
  - "SEED-163 sub-references (2a-2d) in FilterPanel and no-human-rated-games-state were dropped rather than kept as (see SEED-163): they describe shipped behavior, not deferred work"
  - "FlawFilterControl Gem/Great comment rewritten as a rule (do not gate on showTactics) instead of a 'Bug fix (post-verify)' narration"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

completed: 2026-10-16
status: complete
---

# Phase 241 Plan 45: Filter and Small Component Comment Cleanup Summary

**All planning tags are gone from the filter components and the admin, auth, feedback, icon, settings, ui and bookmark components; the 30 INVENTORY rows are applied, and the one `@knipignore` removal (ui/drawer.tsx) is proven harmless by knip.**

## Accomplishments

- First scan: 66 tagged lines in 12 filter files, 48 in the other 66 files (114 total, 39 files with tags; the remaining scope files were already clean and stay untouched). Final `scan --gate` over scopes/241-45.txt: 0 matches.
- Codemod vs hand edits: the codemod rewrote 34 lines in 9 filter files and 18 lines in 15 other files (52 lines). The remaining 62 tagged lines were hand-edited (`temp/241-45/e1..e4.py` replacement scripts; the codemod's own "needs hand edit" list was 33 + 30). Every codemod pair was read before writing and `git diff -U0` reviewed after; no `//: ` punctuation-start artifacts (grep clean).
- Beyond tags, comments follow the code: FlawFilterControl documents the real default (High, `DEPTH_DEFAULT_PRESET`), the real section order (Tactic Depth above Orientation) and that both Library tabs set `showTacticFilter`; FilterPanel/FILTER_DOT_FIELDS call `color` the Openings board color, not "Played-as" (STYLE-GUIDE 3.3 row 65); depth wording uses "depth" not "difficulty" (row 66); the Gem/Great section is no longer called "Best Moves" in rewritten prose (row 67); CustomRangePopover/Drawer describe the pending-range-committed-on-close behavior.
- Comments deleted as provenance only: SentryTestButtons "Moved from GlobalStats.tsx" (INV-L1127), the FilterPanel NativeGamesHint "extracted for complexity gate" rationale (INV-L1085), LibraryFilterPanel "boolean severity toggle is removed" (INV-L1134), FlawFilterControl first tactic-motif comment block (INV-L1093) and the showTactics alias comment (INV-L1092).

## Ledger (ledgers/241-45.txt)

All 30 rows APPLIED (22 in the filters task, 8 in the second): INV-L1051, L1052, L1053, L1080-L1098, L1118, L1126, L1127, L1131-L1134, L1136. The `ledger` command exits 0. Every row was re-verified against the code first (D-10): mounts of EvalCoverageHeader (Import, GlobalStats, Openings, Endgames, not ProtectedLayout), consumers of FeedbackAskBubble and SettingsSheetButton, `DEPTH_DEFAULT_PRESET = 'high'`, render order in FlawFilterControl, `showFlawFilter={false}` at all callers, ImpersonationSelector search cap of 20 rows in app/routers/admin.py. INV-L1131 and INV-L1092 are "M" rows in the inventory and were applied as the suggested wording / deletion.

## Allow list (allow/241-45.tsv)

```
directive  frontend/src/components/ui/drawer.tsx  @knipignore  INVENTORY row INV-L1118: the drawer has consumers now; knip passes without it
```

`cleanup.py diff` prints it as `directive removed or changed: @knipignore (allowed: ...)` and exits 0.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate` (scopes/241-45.txt, 78 files) | exit 0, 0 matches |
| `cleanup.py diff` (same scope, 38 changed) | exit 0, only the allowed `@knipignore` directive line |
| `cleanup.py ledger` | exit 0 |
| `npm --prefix frontend run lint` | clean (baseline clean too) |
| `npm --prefix frontend run knip` | clean without the `@knipignore`; the two "Configuration hints" lines are pre-existing and identical on the untouched tree |
| `npm --prefix frontend run build` (tsc -b + vite) | passes |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed |
| source-scan python half, run serially (no `-n 4`) | 95 passed + 5 passed |

Running the python half serially instead of `-n 4` is environmental (shared dev Postgres with sibling executors), not a plan deviation.

## Task Commits

1. **Task 1: components/filters** - `b727bd6aa` (`chore(comments): frontend filter components`)
2. **Task 2: root, admin, auth, feedback, icons, settings, ui, bookmarks, data** - `0e97d2085` (`chore(comments): frontend components (admin, auth, feedback, icons, settings, ui)`)

`commits: 2` is measured with `git rev-list --count 92ed609e7..HEAD` before this SUMMARY commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` (lockfile install, no new packages). `uv sync --group maia-inference` was not needed: cleanup.py is stdlib-only and no ty run is in this plan's gates; `uv run` created `.venv` on demand. No tracked files changed.

**2. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- FilterPanel: the `pasted` field doc and PastedFilter doc lost "UAT" narration and read as present-tense rules; two inline `(UAT ...)` comments (custom-range focus restore, last-platform deselect) rewritten without the tag; the `FilterState` `rated`/`opponentType` end-of-line comments lost `SEED-163 2a`.
- FlawFilterControl: Gem/Great section comment rewritten as a rule ("Don't gate on showTactics"); header section titles `Best Moves`/`Tactic difficulty` renamed to `Gem / Great toggles`/`Tactic depth filter` per glossary rows 66-67.
- LibraryFilterPanel: component docblock now says the FlawFilterControl is optional (no caller renders it any more).
- PresetRangeFilter: example label "Tactic Difficulty" changed to the actual "Tactic Depth".
- SettingsDialogButton: "Replaced the /settings page (228 UAT)" became "A modal rather than a /settings page" (present tense, reason kept).
- FeedbackButton: "per UI-SPEC ladder" became "ladder"; ImportFilterCard and TacticDepthFilter lost "UI-SPEC"/"Quick" provenance.
- FeedbackAskModalHost / BestMoveIcon / GoodMoveIcon / no-human-rated-games-state: lines the replacements made overlong were re-wrapped.

**Total deviations:** 1 environment prep, 1 group of wording fixes next to removed tags. No code, testid, Umami name, storage key, URL or copy changed (`cleanup.py diff` token comparison, empty apart from the allowed directive).

## Notes for downstream plans

- INV-L1070's ChessBoard.tsx clause and the other components' rows are owned by their own plans; none were touched here.
- Left for the later plans named in the prohibitions: `PRESET_THRESHOLD` (241-68), position-bookmark locals such as `isDirtyRef` (241-63), `remaining` in LeaderboardMedalsDemo (241-57). The dead `showFlawFilter` branch in LibraryFilterPanel stays (INVENTORY 7.1 #36); only its comments changed.
- Seed candidates (not created): none.

## Known Stubs

None.

## Threat Flags

None. Comments only; admin gating code (ImpersonationSelector, SentryTestButtons) has an empty token diff (T-241-62), and the only directive removed is the allow-listed `@knipignore` with knip green (T-241-63).

## Self-Check: PASSED

Files verified present: ledgers/241-45.txt, allow/241-45.tsv. Commits b727bd6aa and 0e97d2085 are ancestors of HEAD.
