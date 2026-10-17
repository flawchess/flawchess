---
phase: 241-codebase-cleanup
plan: 35
subsystem: frontend-lib
tags: [cleanup, comments, typescript, theme, tactics]

requires:
  - phase: 241-04
    provides: "cleanup.py TypeScript support (scan, diff, ledger) and the FE comment loop"
provides:
  - "General frontend libraries (frontend/src/lib/*.ts in scopes/241-35.txt) free of planning tags, token diff against PHASE_BASE empty"
  - "ledgers/241-35.txt covering all 26 INVENTORY section 6 rows of the scope"
affects: [241-42, 241-60, 241-69]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 297158250c71be5ad8a6dd1953ca3946d662ba21
plan_head_after: 9addda407cfa68ac9d8e0cf38f617328d5895eb8

tech-stack:
  added: []
  patterns:
    - "Codemod for the two safe tag shapes, then hand edits through an assert-exactly-once replace helper (temp/241-35/ed.py); a failed pair writes nothing, so a batch is all or nothing"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-35.txt
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/lib/tacticComparisonMeta.ts
    - frontend/src/lib/tacticMotifDefinitions.ts
    - frontend/src/lib/tacticDepth.ts
    - frontend/src/lib/sounds.ts
    - "plus 59 other files under frontend/src/lib (see the second task commit)"

key-decisions:
  - "arrowColor.ts and scoreBulletConfig.ts are untouched: INV-L1298 and INV-L1299 are DEFERRED to 241-60 (DARK_BLUE to NEUTRAL_ARROW_COLOR rename). The ARROW_NEUTRAL block in theme.ts that mentions DARK_BLUE was likewise left for that rename"
  - "Source-pointer comments into .planning (151-MAIA-CONTRACT.md, .planning/notes/*, 57-UI-SPEC.md, CONTEXT.md, 'CONTRACT section a-e' markers) were removed along with the tags even where the scan does not flag them, because a reader of the code cannot open them"
  - "SEED-195 in maiaWorkerErrors.ts was a description tag, not a pointer to deferred work, so it was dropped (no open-seed pointer was needed anywhere in the scope)"

patterns-established:
  - "The scan regex misses tags of the shape 'Quick 260814-b', 'Quick 260814:', '151.1 UAT', '162 UAT', 'CONTRACT section a'; a second grep for UAT|Pitfall|CR-|WR-|SEED-|RESEARCH|CONTEXT.md|Quick|Plan N|sketch|UI-SPEC finds them"

requirements-completed: [D-01, D-04, D-10, D-11, D-12, D-13, D-15]

duration: 95min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 35: General Frontend Libraries Summary

**theme.ts, the tactic metadata modules, sounds.ts and 60 other general libraries now describe the current design (19 tactic families, honest bot clock, graded engine arrows) without planning tags or history, with an empty non-comment diff against PHASE_BASE.**

## Accomplishments

- Task 1 (13 rows): theme.ts, tacticComparisonMeta.ts, tacticMotifDefinitions.ts, tacticDepth.ts, sounds.ts. The 10 to 15 to 17 to 19 family narration is replaced by the current 19 families (counted in the `TacticFamily` union). TAC_CLEARANCE and PHASE_* tombstones deleted. Stale facts fixed while there: the `combinations`/"8 motifs" comment, `Intermediate: 1-6` (now `Medium: 1-6`), Maia accent "red" (now violet), `FLAWCHESS_SECONDARY_LINE` (does not exist), the "Moves by Rating" reference line described as warm brown (it is `'white'`), the Score-timeline fill alpha (comment said 0.18, constants are 0.28).
- Task 2 (13 rows, 2 DEFERRED): 60 further libraries. chessClock.ts lost its Plan/D-nn/CR-nn narration but keeps the honest-clock rule and the calibration caveat. endgameEntryEvalZones.ts no longer claims a 1.5 pawn band. animatedScroll.ts points at `WALKTHROUGH_SCROLL_DURATION_MS` (the constant that exists today; 241-69 renames it). liveFlaw.ts has the `evalToExpectedScore` docblock back above its function.

## Task Commits

1. **Task 1: theme, tactic metadata, tactic depth, sounds** - `b576c04a1` (`chore(comments): frontend lib theme, tactics, sounds`, includes ledgers/241-35.txt with 13 rows)
2. **Task 2: the other general libraries** - `9addda407` (`chore(comments): frontend lib (rest)`, adds the remaining 13 ledger lines)

`commits: 2` is measured with `git rev-list --count 297158250..HEAD` before this SUMMARY commit.

## Ledger (ledgers/241-35.txt): 26 rows

- APPLIED: 24 (INV-L1270, L1271, L1272, L1305, L1314, L1315, L1317, L1318, L1319, L1320, L1321, L1322, L1323, L1339, L1340, L1342, L1343, L1344, L1346, L1347, L1348, L1368, L1369, L1374)
- DEFERRED to 241-60: 2 (INV-L1298, INV-L1299)
- MOVED / SKIPPED / LEFT: 0
- INV-L1318 names a stale variant in components/results/LibraryGameCard.tsx; that clause belongs to 241-42 and was not touched here.

## Codemod vs hand edits

| | Count |
|---|---|
| Codemod (`cleanup.py codemod`) lines rewritten, Task 1 scope (5 files) | 36 |
| Codemod lines rewritten, whole scope run (Task 2, 86 files, 47 changed) | 130 |
| Hand edits left after the codemod, Task 1 | 94 flagged lines (about 50 edit sites, theme.ts and tacticComparisonMeta.ts carry most) |
| Hand edits left after the codemod, Task 2 | 175 flagged lines (about 150 edit sites across 40 files) |
| Reviewed with `git diff -U0` after each codemod run; leading-punctuation grep (`^\s*(#|//|\*)\s*[:;,.]\s`) | 0 hits both times |
| Reverted codemod rewrites | 0 (the first tacticComparisonMeta.ts edit batch was redone from `git checkout --` of that one file because codemod output and hand-edit anchors disagreed; no other file) |

Scan counts: Task 1 scope 128 matches to 0; whole scope 299 matches to 0. A second broader grep found 10 more tag shapes the scan does not match (see patterns-established) and they were fixed too.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-35.txt` | exit 0 (86 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-35.txt` | exit 0 (86 selected, 64 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-35.txt --ledger ledgers/241-35.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean (baseline clean too) |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed (same as baseline) |
| source-scan Python half, run SERIALLY (no `-n 4`, shared dev Postgres) | 95 passed + 5 passed |

## Deviations from Plan

**1. [Environmental] Python source-scan half run serially.** The orchestrator prompt forbids `pytest -n` because sibling executors share the dev Postgres; the same file lists were run without `-n 4`. Not a plan failure.

**2. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags.** Listed so the reviewer can check them against the code:
- theme.ts: `MOVES_BY_RATING_REFERENCE_LINE` comment said "dedicated warm brown", constant is `'white'`; score-timeline comment said fill alpha 0.18, constants use 0.28; "(that token is only used on Library miniboards)" removed (BEST_MOVE_ARROW is also used by analysis and train code); BREAK_LABEL_FONT_SIZE "SC-4 enlarges the prior compact fontSize-11 annotation" rewritten without the history.
- tacticComparisonMeta.ts: TACTIC_FAMILY_FOR_MOTIF now says "self-interference (and the suppressed clearance)" map to no family; filter display order now lists en_passant, under_promotion and promotion (it stopped at sacrifice).
- sounds.ts: SoundEvent docblock rewritten per INV-L1317; the SOUND_FILES comment about `game-win` no longer narrates the 190.1 UAT.
- gemMove.ts: the 0.1 to 0.2 `GEM_MAIA_MAX_PROB` history is kept as the reason for 0.2 ("0.2 (vs 0.1) multiplies gem frequency by about 1.35x ...").
- maiaEncoding.ts, endgameMetrics.ts, signedBandGradient.ts: pointers into `.planning/` (CONTRACT markers, notes, UI-SPEC) removed.
- openingStatsZones.ts and clockFormat.ts named components that no longer exist (MostPlayedOpeningsTable, EndgameClockPressureSection) and now name the current consumers.

**3. [Rule 1 - self-inflicted] Missing comma.** A first edit in materialDiff.ts removed "(D-06)," and left "leading side\n * even when"; fixed in the same task before committing.

**Total deviations:** 1 environmental, 2 notes; none touch code, theme values, zone bounds, Umami helpers or storage keys (the token diff is empty).

## Seed candidates and untouched items (D-04)

- The two iPad detectors (`isIpadOsDesktopUserAgent` in deviceClass.ts vs `isIosWebKit`) and the eval formatters (`formatEval`, `formatSignedEvalPawns`, `formatFlawEvalPart`, `formatPlayerPovEval`) stay separate: no merge. `SCORE_GAP_BUCKET_DISPLAY_SHIFT` (test-only consumers, INVENTORY section 7) is left in place.
- theme.ts still has `ARROW_NEUTRAL` comments naming `DARK_BLUE`; arrowColor.ts keeps its `export const NAME = value;` shape. Both land in 241-60.

## Known Stubs

None.

## Threat Flags

None. Comments only; no new endpoints, auth paths or schema.

## Self-Check: PASSED

Files verified present: ledgers/241-35.txt and the modified libraries. Commits `b576c04a1` and `9addda407` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
