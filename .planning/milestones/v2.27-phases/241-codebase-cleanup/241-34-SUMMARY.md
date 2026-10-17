---
phase: 241-codebase-cleanup
plan: 34
subsystem: frontend-lib
tags: [cleanup, comments, train, bot, personas, push]

requires:
  - phase: 241-04
    provides: "cleanup.py FE support (ts_scan.mjs, fe_support.py)"
  - phase: 241-03
    provides: "cleanup.py codemod, decision"
provides:
  - "Train, push, bot and persona libraries (34 files under frontend/src/lib) free of planning tags with an empty token diff against PHASE_BASE"
  - "ledgers/241-34.txt covering all 11 INVENTORY section 6 rows plus the INV-L1288 secondary clause"
affects: [241-40, 241-57, 241-58, 241-52, 241-69]

actuals:
  tokens: 12000
  tasks: 2
  commits: 2
plan_head_before: 297158250c71be5ad8a6dd1953ca3946d662ba21
plan_head_after: f470d0d0ef731e9d23628f1d3f561a739d84caea

tech-stack:
  added: []
  patterns:
    - "Codemod dry run, write, grep for punctuation-led comments, then hand edits through Edit (heredocs and command substitution are blocked in the worktree sandbox)"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-34.txt
  modified:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/trainArrows.ts
    - frontend/src/lib/trainLeaderboard.ts
    - frontend/src/lib/trainRevealLines.ts
    - frontend/src/lib/trainTelemetry.ts
    - frontend/src/lib/trainRecheck.ts
    - frontend/src/lib/trainRevealCache.ts
    - frontend/src/lib/trainPhoneGrade.ts
    - frontend/src/lib/trainScore.ts
    - frontend/src/lib/trainGuessLabels.ts
    - frontend/src/lib/trainMedals.ts
    - frontend/src/lib/trainRevealPreview.ts
    - frontend/src/lib/trainClockContext.ts
    - frontend/src/lib/push.ts
    - frontend/src/lib/reminderSlotState.ts
    - frontend/src/lib/installCooldown.ts
    - frontend/src/lib/handoffMarker.ts
    - frontend/src/lib/streakArrival.ts
    - frontend/src/lib/leaderboardMedalsDemoData.ts
    - frontend/src/lib/feedbackAsk.ts
    - frontend/src/lib/botDrawGate.ts
    - frontend/src/lib/botGameCopy.ts
    - frontend/src/lib/botGameEnd.ts
    - frontend/src/lib/botGamePgn.ts
    - frontend/src/lib/botGameSnapshot.ts
    - frontend/src/lib/botLineTrigger.ts
    - frontend/src/lib/botPendingStore.ts
    - frontend/src/lib/botSetupSettings.ts
    - frontend/src/lib/botTimeControlPresets.ts
    - frontend/src/lib/confetti.ts
    - frontend/src/lib/playStyle.ts
    - frontend/src/lib/personas/botPersonaSetupSettings.ts
    - frontend/src/lib/personas/personaAvatars.ts
    - frontend/src/lib/personas/personaRegistry.ts

key-decisions:
  - "Every SEED reference in scope pointed at a closed seed (119, 193, 191, 197, 098, 104), so all became tags and were removed; no `(see SEED-NNN)` pointer was kept"
  - "Comments that named a stale pointer were corrected rather than just stripped (see Deviations)"

patterns-established: []

requirements-completed: [D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15]

duration: 95min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 34: Train, push, bot and persona libraries Summary

**Comment-only cleanup of 34 frontend lib files: all planning tags gone, every LOCKED copy string, telemetry cap, storage key and code token unchanged (token diff empty), 11 inventory rows plus the INV-L1288 secondary clause logged.**

## Accomplishments

- First dry run over scopes/241-34.txt: 220 tag lines the codemod could rewrite, 253 flagged "needs hand edit" (473 tagged lines in total). The real codemod run changed 220 lines in 32 files; the 253 leftovers were hand edited with the Edit tool, plus a handful of planning pointers `scan` does not match (`UI-SPEC`, `RESEARCH`, `Plan NN`, "Claude's discretion", dated provenance prefixes, `169.5`).
- Final gates: `scan --gate` 34 files 0 matches (also 0 with `--advisory`), `diff` exit 0 (34 selected, 34 changed, no residue, no directive change), `ledger` exit 0.
- `trainTelemetry.ts` `export const NAME = <digits>;` lines are untouched, so the Python parity tests still read them.

## Task Commits

1. **Task 1: Train and push libraries (3 rows)** - `953f8ac6e` (`chore(comments): frontend lib Train and push`; 20 lib files plus the ledger)
2. **Task 2: bot and persona libraries (8 rows + INV-L1288 secondary)** - `f470d0d0e` (`chore(comments): frontend lib bot and personas`; 15 lib files plus the ledger, including one more `trainScore.ts` edit found by a manual grep)

`commits: 2` is measured with `git rev-list --count 297158250..HEAD` before this SUMMARY commit.

## Ledger (ledgers/241-34.txt)

| Row | Status | Note |
|---|---|---|
| INV-L1264 | MOVED | wouldBotResign docblock moved above the function; the "useBotGame.ts owns the counter" pointer was wrong (counter ref is in `useBotGameDrawOffer.ts`), fixed, same for the own-offer cooldown pointers |
| INV-L1265 | MOVED | ROSTER_GREETINGS docblock moved onto its constant |
| INV-L1300 | APPLIED | botDrawGate.ts header rewritten to the current accept/offer/resign rule |
| INV-L1301 | APPLIED | botGameEnd.ts three sites |
| INV-L1302 | APPLIED | BotLineKey doc; the stale "nine keys" count dropped (there are ten) |
| INV-L1303 | APPLIED | resolveBotLine precedence list rewritten to six arms and verified against the code |
| INV-L1316 | APPLIED | Persona.avatarSrc doc |
| INV-L1324 | APPLIED | promptCopy doc |
| INV-L1325 | APPLIED | three wording edits in trainGuessLabels.ts, strings untouched |
| INV-L1345 | APPLIED | personaAvatars.ts docs; draw-banner mentions at personaRegistry.ts removed (no banner component exists) |
| INV-L1349 | APPLIED | both arrow-width pointers now name `useAnalysisBoardArrows.ts` (it lives in `hooks/analysis/`) |
| INV-L1288 (secondary botLineTrigger.ts) | APPLIED, `#` comment line | owned by plan 241-40 (Bots.tsx), listed here as the plan asked |

Counts: 9 APPLIED, 2 MOVED, 0 SKIPPED, 0 LEFT, plus the secondary comment line.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages); baseline lint, `source_scan_tests.sh --fe` (131 tests) and the serial python half (95 + 5 tests) were green before any edit.

**2. [Rule 1 - stale content, STYLE-GUIDE 2.2] Pointers corrected while stripping tags**
- botDrawGate.ts: the draw/resign counters are owned by `useBotGameDrawOffer.ts`, not `useBotGame.ts` (three comments).
- botGameCopy.ts: BotLineKey doc claimed nine keys, there are ten.
- botLineTrigger.ts: the precedence list claimed a "swing in either direction" arm; the code latches regret swings and speaks the settle, so the list now matches `resolveBotLine`.
- personaAvatars.ts: "three call sites (PersonaCard, PersonaDetailSurface, ClockDisplay)" replaced by "every caller" (six components call `resolveAvatarSrc`).
- trainArrows.ts: arrow-width pointers moved from `Analysis.tsx` to `useAnalysisBoardArrows.ts`.
- botGameEnd.ts, botGamePgn.ts, trainScore.ts: references to UI-SPEC / RESEARCH documents removed.

**3. [Plan note] Python half of source_scan_tests.sh run serially**
- Run as the two pytest commands from the script without `-n 4` (shared dev Postgres, no xdist). 95 + 5 passed both before and after. Environmental, not a plan failure.

**4. [Plan note] Codemod fallout**
- The codemod left two punctuation-led comment lines in trainBotCopy.ts (`//, which repeated ...`, `//: the strip ...`) and a dangling "Phase 240" in the scoreBubbleCopy docblock; all three were rewritten by hand. No other `^\s*(#|//|\*)\s*[:;,]` match remained.

**Total deviations:** 1 blocking env prep, 3 notes; no code, copy, testid, Umami name, storage key or wire field changed.

## Non-inventoried fixes

Besides the stale pointers above: the Phase 240 / UAT narration in trainBotCopy.ts tour and score-bubble comments was rewritten from history into present-tense rules ("Don't end a perfect session on the return counts alone ..."), "walkthrough" became "tour" in prose that was rewritten anyway (identifiers `WALKTHROUGH_*` and `WalkthroughContext` untouched, they belong to plan 241-69), and `push.ts` `ensureDeviceSubscribed` lost its code-review narration but keeps the three rules (open the `try` before the permission await, capture to Sentry here, compare the VAPID key before reusing a subscription).

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-34.txt` | exit 0 (34 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-34.txt` | exit 0 |
| `cleanup.py ledger --scope scopes/241-34.txt --ledger ledgers/241-34.txt` | exit 0 |
| `pytest tests/schemas/test_train_telemetry_parity.py tests/services/test_train_score_parity.py` | 12 passed |
| `npm --prefix frontend run lint` | clean |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed |
| python half of `source_scan_tests.sh` (serial) | 95 passed, 5 passed |
| `npx vitest run src/lib` (extra) | 126 files, 2413 tests passed |

## Known Stubs

None.

## Threat Flags

None. Comment text only; T-241-51 mitigated by the empty token diff and the parity tests.

## Self-Check: PASSED

Files verified present: ledgers/241-34.txt and the 34 lib files. Commits `953f8ac6e` and `f470d0d0e` are ancestors of HEAD.
