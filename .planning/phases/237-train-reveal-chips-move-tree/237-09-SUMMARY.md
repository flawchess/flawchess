---
phase: 237-train-reveal-chips-move-tree
plan: 09
subsystem: ui
tags: [react, telemetry, train, reveal-cache, sessionstorage, schema-versioning]
status: complete

requires:
  - phase: 237-01 (review telemetry v2 boundary)
    provides: "REVIEW_TELEMETRY_SCHEMA_VERSION = 2, ReviewTelemetry v: Literal[1, 2], _keys_match_version"
  - phase: 237-02 (reveal move tree)
    provides: "useTrainRevealTree snapshot() / restored / onChipSelect, RevealTreeSnapshot + caps"
  - phase: 237-08 (verdict strip)
    provides: "TrainReveal onStripExpand"
provides:
  - "REVIEW_TELEMETRY_SCHEMA_VERSION = 2 (frontend/src/lib/trainTelemetry.ts) with a parity row; the solve patch keeps TELEMETRY_SCHEMA_VERSION = 1"
  - "v2 ReviewCounters (forked, chipKeys, chipsTotal, stripExpanded), v2 buildReviewTelemetry and v2 ReviewTelemetrySnapshot guard"
  - "useTrainPuzzleTelemetry: onChipSelect, onChipsTotalChange, markStripExpanded, onExploreMove(source, forked); the card/hover machinery is removed"
  - "CachedTrainReveal.revealTree + isRevealTreeSnapshot (malformed field dropped, entry kept)"
  - "Analyze -> Back restores the focused chip, every sideline and the exact node"
affects: [237-10, 237-11]

tech-stack:
  added: []
  patterns:
    - "Per-patch schema version constants mirrored by the parity test"
    - "Optional cache field validated on its own: drop the field, never the entry"
    - "Chip identity stays in a client-side Set; only its size is serialized"

key-files:
  created: []
  modified:
    - frontend/src/lib/trainTelemetry.ts
    - frontend/src/types/train.ts
    - frontend/src/hooks/useTrainPuzzleTelemetry.ts
    - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
    - tests/schemas/test_train_telemetry_parity.py
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/lib/trainRevealCache.ts
    - frontend/src/lib/__tests__/trainRevealCache.test.ts

key-decisions:
  - "The tree hook already fires onChipSelect from selectChip (tap) AND from a line-matching root move, so TrainSolveScreen passes puzzleTelemetry.onChipSelect straight to useTrainRevealTree instead of also calling it in handleChipSelect (the plan listed both; a second call would only be deduped by the Set)"
  - "The default You chip is filtered inside the telemetry hook (key === DEFAULT_ROOT_FOCUS), so the tree hook stays telemetry-agnostic"
  - "Chip count effect lives in TrainSolveScreen (chips.length > 0 -> onChipsTotalChange); the hook keeps the max, so a late game chip raises it and the pre-verdict empty list reports nothing"
  - "Legacy v1 snapshot fields (cardKeys, cardsTotal) in an older cache entry are ignored, not rejected: the entry still seeds the review timer"

requirements-completed: [D-12, D-13]

duration: 8 min
completed: 2026-10-09
actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 6405052bcabcd5d7a863db8d396cdec1f354426d
plan_head_after: 9c620c0df77487706bcd81ca4cd96374808ff5e6
commits: 2

coverage:
  - deliverable: "D-12: every Next/pagehide flush is a v2 body (v 2, review_chips_selected, review_chips_total, review_strip_expanded) with no card keys, carrying a chip tap, a strip expand and a fork"
    verification:
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#tracer: a chip tap, a strip expand and a fork ride the v2 Next flush"
        status: pass
      - kind: test
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#closed set: a flush body has exactly the v2 keys (D-12) and no card keys"
        status: pass
      - kind: test
        ref: "tests/schemas/test_train_telemetry_parity.py#test_telemetry_constant_matches_frontend"
        status: pass
    human_judgment: false
  - deliverable: "D-12: the default You chip is never counted, distinct chips count once, total keeps the max and caps at 10, strip flag is sticky"
    verification:
      - kind: test
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#chips:"
        status: pass
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry (D-12): re-tapping the default You chip and never opening the strip sends zero chips and a closed strip"
        status: pass
    human_judgment: false
  - deliverable: "D-13: review_explored is true only when a sideline was forked; a hand-played known-line move is a board move, not a fork"
    verification:
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry (D-13): a hand-played known-line move counts as a board move, not a fork"
        status: pass
      - kind: test
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#fork (D-13)"
        status: pass
    human_judgment: false
  - deliverable: "Restore guardrail: Analyze -> Back restores the focused chip, every sideline and the exact node; an older entry restores at the puzzle position with You focused; a malformed revealTree is dropped, not the entry"
    verification:
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#TrainSolveScreen — restored reveal tree (Phase 237 plan 09)"
        status: pass
      - kind: test
        ref: "frontend/src/lib/__tests__/trainRevealCache.test.ts#Phase 237: revealTree (T-237-16)"
        status: pass
    human_judgment: false
  - deliverable: "The restored reveal continues the cumulative v2 counters (chips, strip, fork) from the Analyze snapshot"
    verification:
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a restored reveal continues the cumulative v2 counters (chips, strip, fork) into the Next flush"
        status: pass
      - kind: test
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#chips: the Analyze snapshot carries chips, strip and fork, which a restored hook continues"
        status: pass
    human_judgment: false
---

# Phase 237 Plan 09: Telemetry v2 and Restored Reveal Tree Summary

**The Train client now sends review telemetry v2 (chips selected, chips total, strip expanded, fork-only `review_explored`) against the plan 01 boundary, and Analyze -> Back restores the focused chip, every sideline and the exact board node from UCI paths in the reveal cache.**

## Performance

- **Duration:** 8 min
- **Tasks:** 2 (1 tracer, 1 TDD-flagged auto)
- **Files modified:** 9 (frontend 8, backend test 1)

## Accomplishments

- `REVIEW_TELEMETRY_SCHEMA_VERSION = 2` as a plain literal beside the unchanged `TELEMETRY_SCHEMA_VERSION = 1`; the parity test gained its row (the `REVIEW_` prefix cannot match the existing regex, so the rows stay independent).
- `ReviewCounters` swaps the card fields for `forked`, `chipKeys` (Set, only its size leaves the client), `chipsTotal` and `stripExpanded`; `review_explored` is now `counters.forked` (D-13).
- Telemetry hook: `onChipSelect` (skips the default `your` key), `onChipsTotalChange` (max), `markStripExpanded`, `onExploreMove(source, forked)`; the hover timer, `CardEngageKind`, `REVIEW_CARD_HOVER_MIN_MS`, `onCardEngage` and `onCardsTotalChange` are gone (knip clean). The restored-seed merge unions chip keys, maxes the total and ORs the flags.
- `TrainSolveScreen`: tree `onChipSelect` and `restored`, a `chips.length` effect, `onExploreMove(source, forked)`, `onStripExpand`, and `revealTree: revealTree.snapshot()` in the Analyze cache entry.
- `trainRevealCache`: optional `revealTree`, validated by `isRevealTreeSnapshot` (role-key-or-null focus, string arrays, plan 02 path and ply caps). A bad field is removed on read and the rest of the entry restores.

## Task Commits

1. **Task 1 (tracer): v2 review telemetry** - `d0bff64b6` (feat)
2. **Task 2: restored reveal tree** - `9c620c0df` (feat)

Tracer gate: the `<verify>` set (vitest `-t` set, pytest parity and schema tests, lint, build, knip) ran green after the Task 1 commit work, then expansion proceeded.

## Mutation proof

- Removing `onStripExpand` and the tree `onChipSelect` wiring turned the tracer test red (`review_chips_selected` 0 vs 1, `review_strip_expanded` false vs true).
- Removing `restored: restoredSolve?.revealTree` turned the remount test red; removing `revealTree: revealTree.snapshot()` turned the cache-entry test and the remount test red. Files restored from backups.

## Verification

- `uv run pytest tests/schemas/test_train_telemetry_parity.py tests/schemas/test_train_telemetry_schema.py`: 39 passed.
- Full frontend suite 5404 passed; `npm run lint`, `npm run build` (`tsc -b`), `npm run knip` clean.
- Acceptance greps: both version constants, `revealTree?: RevealTreeSnapshot`, `function isRevealTreeSnapshot`, `revealTree: revealTree.snapshot()`, `restored: restoredSolve` match; the card-machinery grep prints 0 for all three files; the parity file mentions `REVIEW_TELEMETRY_SCHEMA_VERSION` twice.

## TDD Gate Compliance

Task 2 was flagged `tdd="true"` but the plan is `type: execute`; tests landed with the implementation in one commit. RED-equivalent evidence is the mutation runs above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Redundancy] `handleChipSelect` does not call `puzzleTelemetry.onChipSelect` itself**
- **Found during:** Task 1
- **Issue:** The plan asked for both `handleChipSelect` calling `onChipSelect` and passing it to `useTrainRevealTree`. The tree hook's `selectChip` already fires the option on a tap, so the double call would only be deduped by the Set.
- **Fix:** Pass it to the hook once; the tracer test proves the tap path still counts.
- **Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`
- **Commit:** `d0bff64b6`

**2. [Rule 3 - Blocking] `_dropped` unused-variable lint error in the cache read**
- **Found during:** Task 2
- **Fix:** copy and `delete stripped.revealTree` instead of rest destructuring.
- **Files modified:** `frontend/src/lib/trainRevealCache.ts`
- **Commit:** `9c620c0df`

**Total deviations:** 2 auto-fixed (1 redundancy, 1 lint). **Impact:** none on behavior or scope.

## Known Stubs

None.

## Threat Flags

None. T-237-16 is mitigated (shape and cap check, field dropped on failure, chess.js-guarded replay, the snapshot never feeds grading or the solve POST); T-237-18 holds (only counts and booleans are serialized, `chipKeys` stays a client-side Set).

## Next Phase Readiness

Plan 10 can move the walkthrough tour and plan 11's browser UAT can confirm v2 rows in the dev DB and the Back restore in a real browser. Old open tabs keep posting v1, which the server still accepts.

## Self-Check: PASSED

- FOUND: frontend/src/lib/trainTelemetry.ts, frontend/src/lib/trainRevealCache.ts, frontend/src/hooks/useTrainPuzzleTelemetry.ts, tests/schemas/test_train_telemetry_parity.py
- FOUND commits: d0bff64b6, 9c620c0df
