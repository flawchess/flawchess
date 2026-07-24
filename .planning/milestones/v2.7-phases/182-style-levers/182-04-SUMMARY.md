---
phase: 182-style-levers
plan: "04"
subsystem: frontend-engine
tags: [flawchess-engine, bot-style, chess.js, opening-book, mcts, style-levers]

# Dependency graph
requires:
  - phase: 182-01
    provides: "RankedLine.childScoreSpread (null-safe variance/sharpness proxy)"
  - phase: 182-03
    provides: "styleLinesFor(style, side) curated per-style SAN-prefix sets (not consumed directly by this plan — consumed by Plan 07's wiring)"
provides:
  - "BotStyleParams (D-01 raw numeric knob data type, no function fields)"
  - "MoveFeatures + classifyMoveFeatures (chess.js move-feature classifier: check/capture/pawn-advance/pawn-storm/exchange/retreat)"
  - "applyStylePriorReweighting(rawPolicy, fen, style) -> unnormalized Record<string, number>"
  - "applyStyleScoreShaping(lines, style) -> RankedLine[] with shaped, clamped practicalScore"
  - "styleBookWeighting(styleLinePrefixes, moveHistorySan, boostMultiplier) -> BookWeightingFn"
affects: ["182-05-botStyleBundles", "182-06-selectBotMove-wiring", "182-07-useBotGame-wiring"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure engine module that deliberately imports chess.js (documented deviation from openingBook.ts's no-chess.js convention) for move-feature classification"
    - "BookWeightingFn composition seam (D-06): styleBookWeighting wraps maiaPolicyWeighting, never replaces it"
    - "Curried-history closure factory (Pitfall 2): moveHistorySan bound at construction time so BookWeightingFn's own 2-arg signature stays unchanged"

key-files:
  created:
    - frontend/src/lib/engine/botStyle.ts
    - frontend/src/lib/engine/__tests__/botStyle.test.ts
  modified:
    - frontend/src/lib/engine/__tests__/openingBook.test.ts

decisions:
  - "BotStyleParams field names fixed as threshold/hysteresisFloor (not resignThreshold) and scoreBonus (singular flat scalar, not a per-feature map) to match the exact field-access shapes already committed in Plan 02's botDrawGate.ts (wouldBotResign's threshold/hysteresisFloor params) and previewed in Plan 05/06/07's prose (settings.style.threshold, settings.style.hysteresisFloor)."
  - "applyStyleScoreShaping takes only (lines, style) — no fen parameter — so its bonus/malus is a flat scalar applied uniformly to every line, not move-feature-conditioned; per-line differentiation for STYLE-04 comes entirely from the childScoreSpread variance term, matching the plan's literal Task 2 action text over a looser reading of D-09's 'contempt feeds score shaping' note (which is deferred to a later wiring plan, not required by this plan's acceptance criteria)."
  - "styleBookWeighting is a 3-arg factory (styleLinePrefixes, moveHistorySan, boostMultiplier) per the plan's <action> text, not the 2-arg shape sketched in the plan's <behavior> summary — the 3-arg form is what Plan 07's prose explicitly calls (styleBookWeighting(styleLinesFor(style, side), moveHistorySan, style.bookBoost)), so it was treated as authoritative."
  - "Committed as 3 separate atomic task commits (type + classifier; the two pure transforms; the book-weighting factory) despite writing all logic in one authoring pass, by staging the file incrementally — mirrors the plan's own 3-task structure and keeps each commit independently tsc/test-green, rather than one combined commit."
metrics:
  duration: "~50 min"
  completed: "2026-07-21"
status: complete
---

# Phase 182 Plan 04: BotStyleParams + Pure Style Transforms Summary

**New `botStyle.ts` module: a raw-numeric-knob `BotStyleParams` type, a color-aware chess.js move-feature classifier, and three pure transforms — unnormalized prior reweighting (STYLE-03), clamped additive score shaping with a null-safe variance term (STYLE-04), and a `maiaPolicyWeighting`-composing opening-book boost factory (STYLE-01) — with a floor-check-before-weighting regression proving the book's raw-policy safety valve survives styling.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3
- **Files created:** 2
- **Files modified:** 1

## Accomplishments

- `frontend/src/lib/engine/botStyle.ts`: `BotStyleParams` (7 fields — `featureMultipliers`, `scoreBonus`, `varianceBonus`, `contempt`, `threshold`, `hysteresisFloor`, `bookBoost` — all plain numbers/nested-number-record, no function fields), `MoveFeatures`/`FeatureMultipliers` interfaces, `PIECE_VALUE`/`EXCHANGE_VALUE_GAP` constants, and `classifyMoveFeatures(move: Move): MoveFeatures` — a pure, color-mirrored classifier reading `.san`/`.flags`/`.piece`/`.captured`/`.from`/`.to` off a chess.js verbose `Move`.
- `applyStylePriorReweighting(rawPolicy, fen, style)`: re-derives `fen`'s legal moves, classifies each `rawPolicy` UCI key's move, and multiplies its raw weight by the product of matched feature multipliers — unmatched or unresolvable UCI keys keep multiplier `1`; output is an unnormalized `Record`, never renormalized.
- `applyStyleScoreShaping(lines, style)`: additively shifts each `RankedLine.practicalScore` by `style.scoreBonus` plus `style.varianceBonus * childScoreSpread` (zero variance term when `childScoreSpread` is `null`), clamped into `[0, 1]`; every other `RankedLine` field is copied unchanged.
- `styleBookWeighting(styleLinePrefixes, moveHistorySan, boostMultiplier)`: a factory returning a `BookWeightingFn` that calls `maiaPolicyWeighting` internally and multiplies a candidate's base weight by `boostMultiplier` iff the FULL joined `[...moveHistorySan, candidate.san].join(' ')` prefix is in `styleLinePrefixes` (Pitfall 2 — never a bare-SAN check) — `openingBook.ts`'s `selectBookMove` RAW-policy floor check runs entirely before any weighting function is invoked, so this factory has no way to rescue an implausible boosted line past `BOOK_POLICY_FLOOR` (Pitfall 1).
- `frontend/src/lib/engine/__tests__/botStyle.test.ts` (21 tests): 7 `classifyMoveFeatures` cases (one real chess.js move per feature, both colors for `isPawnStorm`/`isRetreat`), a `BotStyleParams` no-function-field structural test, 3 `applyStylePriorReweighting` cases (feature-matched scaling + unmatched-unchanged + unnormalized-sum proof, neutral-style no-op, unresolvable-UCI-key fallback), 5 `applyStyleScoreShaping` cases (bonus+variance, null-guard mutation-proof pair, over/under-`[0,1]` clamping with finite assertions, field-preservation regression), and 4 `styleBookWeighting` cases (boost-vs-base, joined-prefix Pitfall-2 mutation-proof pair, absent-candidate skip, empty-set no-op parity with `maiaPolicyWeighting`).
- `frontend/src/lib/engine/__tests__/openingBook.test.ts`: 2 new regression tests using the REAL `styleBookWeighting` (not a hand-rolled stub) proving a 50x-boosted sole book candidate whose RAW policy is below `BOOK_POLICY_FLOOR` still leaves book (`null`), and a companion case confirming a heavily-boosted candidate that clears the floor IS selected across 5 seeds.

## Files Created

- `frontend/src/lib/engine/botStyle.ts` — `BotStyleParams`, `MoveFeatures`, `FeatureMultipliers`, `PIECE_VALUE`, `classifyMoveFeatures`, `applyStylePriorReweighting`, `applyStyleScoreShaping`, `styleBookWeighting`
- `frontend/src/lib/engine/__tests__/botStyle.test.ts` — 21 unit tests covering all exports

## Files Modified

- `frontend/src/lib/engine/__tests__/openingBook.test.ts` — added a `styleBookWeighting` import and a `styled weighting (Phase 182, STYLE-01)` describe block (2 tests)

## Task Commits

1. **Task 1: BotStyleParams type + module header + classifyMoveFeatures** — `dafe04c8` (feat)
2. **Task 2: applyStylePriorReweighting (STYLE-03) + applyStyleScoreShaping (STYLE-04)** — `e14a6dc9` (feat)
3. **Task 3: styleBookWeighting factory (STYLE-01) + openingBook floor-check regression** — `abd39806` (feat)

## Verification

- `cd frontend && npx vitest run src/lib/engine/__tests__/botStyle.test.ts src/lib/engine/__tests__/openingBook.test.ts` — 33/33 passing (21 + 12).
- `cd frontend && npx vitest run src/lib/engine/` — 231/231 passing across all 16 engine test files (no regression in any existing consumer).
- `cd frontend && npx tsc -b` — zero errors.
- `cd frontend && npm run lint` — 0 errors (3 pre-existing unrelated warnings in `coverage/` generated artifacts).
- `git diff --stat frontend/src/lib/engine/botSampling.ts` — empty (STYLE-05 purity: `botSampling.ts` untouched).
- `grep -n "BookWeightingFn = (" frontend/src/lib/engine/openingBook.ts` — still shows the original 2-arg `(candidates, rawPolicy) =>` shape (prohibition: signature not modified).
- Mutation-proof (hand-verified, then reverted): (1) replacing `applyStyleScoreShaping`'s null-guarded variance term with a `childScoreSpread ?? 1` fallback made the "applies NO variance term when null" test fail as expected (0.8 vs expected 0.6); (2) replacing `styleBookWeighting`'s joined-prefix key with a bare `san` check made the Pitfall-2 test fail as expected (0.1 vs expected 0.5 for the matching-history case). Both reverted immediately after; `tsc -b` and the full test run re-confirmed green.

## Decisions Made

- `BotStyleParams` field names (`threshold`, `hysteresisFloor`, `contempt`, `bookBoost`, `scoreBonus`, `varianceBonus`, `featureMultipliers`) were fixed to match the exact access patterns already committed in Plan 02's `botDrawGate.ts` (`wouldBotResign(rootPracticalScore, resignThreshold, consecutiveLowTurns, hysteresisFloor, chess)`) and previewed in Plans 05/06/07's prose (`settings.style.threshold`, `settings.style.hysteresisFloor`, `settings.style?.contempt`, `style.bookBoost`) — cross-checked by reading those plan files before finalizing the shape, since this plan's own type definition is the single source of truth downstream plans depend on.
- `applyStyleScoreShaping` takes only `(lines, style)` — no `fen` parameter, per the plan's literal action text — so its bonus/malus is a flat scalar applied uniformly to every candidate line; per-line differentiation for STYLE-04 comes entirely from the `childScoreSpread` variance term, not from move-feature classification (which `RankedLine.rootMove` alone, without a `fen`, cannot support). CONTEXT.md's D-09 note that contempt "feeds Deep-regime score shaping as a malus/bonus on draw-ish moves" is left for a later wiring plan to interpret at the call site — this plan's Task 2 acceptance criteria only require the flat-bonus + null-gated-variance behavior, which is what was implemented and tested.
- `styleBookWeighting` is a 3-arg factory (`styleLinePrefixes, moveHistorySan, boostMultiplier`) matching the plan's `<action>` text and Plan 07's exact call-site prose, rather than the 2-arg shape sketched in the plan's shorter `<behavior>` summary (which omitted history) — the more detailed `<action>` text and the downstream plan's literal consumption were treated as authoritative.
- Despite authoring all logic for the file in one pass, the three tasks were committed as three separate atomic commits by staging the file incrementally (Task 1's subset, then Task 2's addition, then Task 3's addition), each independently green on `tsc -b` and its own test slice — matching the plan's task boundaries rather than one combined commit.

## Deviations from Plan

None — plan executed as written. All three tasks' acceptance criteria were met literally; the "Decisions Made" section above documents interpretation choices made where the plan's prose left field names/parameter shapes to the executor's judgment (all resolved by cross-referencing the downstream plans 02/05/06/07 that already reference this file's exports).

## Known Stubs

None — `botStyle.ts` ships no bundle data (that is Plan 05's job) and is not yet wired into `selectBotMove`/`useBotGame` (Plans 06/07); this plan's scope is exactly the pure transform module, per its objective.

## Threat Flags

None — this plan's only surface is pure, synchronous, in-memory data transforms (no new network endpoint, auth path, file access, or schema change). The threat model's three registered items (T-182-08 Tampering via function fields, T-182-09 DoS via degenerate distributions, T-182-10 Tampering via boost defeating the book floor) are all mitigated as designed and verified above (no-function-field test, reuse of `weightedPick`'s existing finite guard downstream, and the floor-check-before-weighting regression).

## Issues Encountered

None.

## User Setup Required

None — pure TypeScript module, no external service configuration, no new dependencies.

## Next Phase Readiness

- `BotStyleParams`, `classifyMoveFeatures`, `applyStylePriorReweighting`, `applyStyleScoreShaping`, and `styleBookWeighting` are all ready for Plan 05 to build the 4 named style bundles (`ATTACKER_STYLE`/`TRICKSTER_STYLE`/`GRINDER_STYLE`/`WALL_STYLE`) against this exact field shape, and for Plans 06/07 to wire the pure transforms into `selectBotMove.ts`/`useBotGame.ts`.
- No blockers. `npx tsc -b` (zero errors) and `npx vitest run src/lib/engine/` (231/231) both green.

---
*Phase: 182-style-levers*
*Completed: 2026-07-21*

## Self-Check: PASSED

All claimed files found on disk; all 3 commits (`dafe04c8`, `e14a6dc9`, `abd39806`) found in git log.
