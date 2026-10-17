---
phase: 241-codebase-cleanup
plan: 39
subsystem: frontend-comments
tags: [cleanup, comments, bots, jsx]

requires:
  - phase: 241-04
    provides: "FE support in cleanup.py (scan/diff/ledger over .ts/.tsx)"
provides:
  - "18 bot-play components (frontend/src/components/bots) free of planning tags and UAT-round history"
  - "ledgers/241-39.txt covering all 24 INVENTORY rows"
affects: [241-58]

actuals:
  tokens: 6500
  tasks: 2
  commits: 2
plan_head_before: fae6dc0d39bb4e4b43029724116c1bbe1171383b
plan_head_after: ea9573586e9c65bab384990a760d81223e1ce8bc

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-39.txt
  modified:
    - frontend/src/components/bots/BotDrawOfferActions.tsx
    - frontend/src/components/bots/BotGameBubble.tsx
    - frontend/src/components/bots/BotGameDesktopLayout.tsx
    - frontend/src/components/bots/BotGameMobileBar.tsx
    - frontend/src/components/bots/BotGameMobileLayout.tsx
    - frontend/src/components/bots/EngineReadyGate.tsx
    - frontend/src/components/bots/GameControls.tsx
    - frontend/src/components/bots/GameResultDialog.tsx
    - frontend/src/components/bots/MoveListPanel.tsx
    - frontend/src/components/bots/ResumeGate.tsx
    - frontend/src/components/bots/botPlayerRow.ts
    - frontend/src/components/bots/PersonaCard.tsx
    - frontend/src/components/bots/PersonaDetailSurface.tsx
    - frontend/src/components/bots/PersonaEloDisclosurePopover.tsx
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/PlayStyleControl.tsx
    - frontend/src/components/bots/SetupScreen.tsx
    - frontend/src/components/bots/chipStyles.ts

key-decisions:
  - "BotWelcomeCard and botDrawOffer mentions keep their current names (241-58 renames them)"
  - "ResumeGate's `${plyCount} moves` copy (INVENTORY 7.2 #4, suspected bug) left untouched"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: 45min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 39: Bot Components Comment Cleanup Summary

**Planning tags, UAT-round reversals, retired-banner lineage and pinned-complexity-budget notes are gone from the 18 bot-play components; the non-comment token diff against PHASE_BASE is empty.**

## Accomplishments

- First scan: 127 matches in 18 files. Final `scan --gate`: 0.
- Codemod (`--dry-run` read first, then written): 51 lines changed in 15 files, 84 flagged for hand edit. Every codemod pair was read in `git diff -U0`; none had to be reverted. Hand edits: about 70 comment blocks via exact-string replacement scripts (`temp/241-39/e*.py`, gitignored), including re-wrapping of lines the codemod left short or over-long and the `Phase 223:` leftovers it could not strip.
- All 24 INVENTORY rows are APPLIED in `ledgers/241-39.txt`, each re-verified against the code first (D-10): e.g. `FlawChessInfoTooltip` now lives in `AnalysisTabs.tsx`, `GameResultStrip` no longer exists (so the dialog-dismiss comment was rewritten to the real `onDismiss` behavior), the EngineReadyGate mounts are `Bots.tsx:554` and `Analysis.tsx:2519`, `PersonaDetailSurface` mirrors `SetupScreen`'s `buildSettings` (not `handleStart`).
- Testids, Sentry messages and contexts, Umami event names and props, and all copy are unchanged (token diff exit 0).

## Task Commits

1. **Task 1: game layouts, bubble, result dialog, ready gate, controls (14 rows)** - `01ce2d0be` (`chore(comments): frontend bots game layouts and dialogs`)
2. **Task 2: setup screen, persona grid/card/detail, play-style control, chip styles (10 rows)** - `ea9573586` (`chore(comments): frontend bots setup and personas`)

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-39.txt` | exit 0 (18 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-39.txt` | exit 0 (18 selected, 18 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-39.txt --ledger ledgers/241-39.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean (baseline also clean) |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed (same as baseline) |
| Python half of `source_scan_tests.sh`, run serially | 95 passed + 5 passed |
| `npm --prefix frontend test -- --run src/components/bots` | 11 files / 168 tests passed |
| grep `^\s*(#\|//\|\*)\s*[:;,]\s` over components/bots | no codemod-collapsed starts |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile only); baseline lint and FE source-scan tests were green before any edit.

**2. [Plan note] Python source-scan half run serially**
- The `-n 4` pytest command was run without `-n` per the parallel-executor instructions (shared dev Postgres). Environmental, not a plan failure; results identical (95 + 5 passed).

**3. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- EngineReadyGate: `G-213-*` goal tags (not matched by the scan regex) and `FLAWCHESS-A5` provenance removed; the "mount/Sentry" blocks now describe current behavior.
- GameResultDialog, PersonaGrid, PersonaCard, MoveListPanel: `UI-SPEC` / `185-UI-SPEC.md` / `223-CONTEXT` / `Pattern 3` / `locked decision` pointers dropped.
- chipStyles.ts: stale "Human/Engine preset chips" corrected to Human/Light/Deep (matches `PlayStyleControl`); "were the only bot buttons that were comfortably tappable" history rephrased as the rule.
- Present-tense rewrites of "previous"/"now"/"was" history in PersonaCard, PersonaDetailSurface, GameResultDialog and PersonaGrid comments.

**Total deviations:** 1 blocking env prep, 1 plan note, 1 group of wording fixes. None touch code, testids, Umami names, Sentry strings or copy.

## Known Stubs

None.

## Threat Flags

None. Comment-only change; `cleanup.py diff` compared every code token, string and JSX token (T-241-56).

## Notes for downstream plans

- `frontend/src/pages/Bots.tsx:517` still carries `Phase 223 (BOTVOICE-05): replaces the old renderMobileLayout helper` and `GameResultDialog.test.tsx:14` mentions `GameResultStrip.test.tsx`; both belong to the plans that own those files. No secondary-clause ledger lines were needed.
- `BotWelcomeCard` and `botDrawOffer` are still the current names in comments (241-58 renames them).

## Self-Check: PASSED

Files verified present: ledgers/241-39.txt and the 18 bot components. Commits `01ce2d0be` and `ea9573586` are ancestors of HEAD.
