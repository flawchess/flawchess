---
phase: 182-style-levers
plan: "06"
subsystem: frontend-engine
tags: [flawchess-engine, bot-style, style-levers, selectBotMove, wiring]

# Dependency graph
requires:
  - phase: 182-04
    provides: "BotStyleParams shape, applyStylePriorReweighting, applyStyleScoreShaping (botStyle.ts pure transforms)"
provides:
  - "BotSettings.style?: BotStyleParams — the optional, budget-separate style field selectBotMove now accepts"
  - "Two guarded regime hooks in selectBotMove.ts: applyStylePriorReweighting (blend<=0) and applyStyleScoreShaping (search branch)"
  - "A D-03 baseline-invariant regression test proving undefined style is byte-identical to the pre-Phase-182 code path"
affects: ["182-07-useBotGame-wiring", "183-persona-registry"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ternary-guarded optional-field hook pattern: settings.style ? transform(...) : <today's value> at each of two disjoint regime branches, never a shared style-dispatch helper (Pitfall 5)"
    - "Mutation-proof regression via independent recomputation: the undefined-style expectation is derived by calling samplePolicy/argmaxLine directly on the untransformed inputs (not a hardcoded literal alone), so an accidental unconditional reweight/shaping call fails the test even if it happens to still return a plausible-looking move"

key-files:
  created: []
  modified:
    - frontend/src/lib/engine/selectBotMove.ts
    - frontend/src/lib/engine/__tests__/selectBotMove.test.ts

key-decisions:
  - "STYLE-03 left Pending (not marked complete) despite this plan wiring applyStylePriorReweighting into selectBotMove's blend<=0 branch — the requirement text ('Human-rung personas get prior reweighting') describes RUNTIME persona behavior that only exists once Plan 07 threads a resolved BotStyleParams from BotGameSettings.style into selectBotMove's settings.style at the actual play-loop call site. This plan proves the hook fires correctly in isolation (unit tests), not that any real bot game currently sets it. Mirrors 182-05's identical STYLE-01/STYLE-03 partial-delivery reasoning."
  - "STYLE-05 also left Pending — the structural invariant (style params are new bot-only fields, never merged into budget, botSampling.ts stays pure) is proven at THIS seam (BotSettings.style), but botStyle.ts's own forward-pointer comment names BotGameSettings.style (Plan 07) as the second half of the same invariant; leaving it open until Plan 07 lands avoids a premature checkbox flip that Plan 07 would then have to re-verify rather than close."
  - "STYLE-04 was already marked Complete by Plan 04 (pre-existing project state) — left untouched; this plan's search-branch wiring is additional confirmation, not a new completion."
  - "Fixed selectBotMove.test.ts's makeLine helper to include the required childScoreSpread field (defaulted to null) — it was missing since Plan 04 added the field to RankedLine, silently compiling only because *.test.ts is excluded from tsc -b and vitest's esbuild transform doesn't type-check. Left uncaught, any new styled-search test using varianceBonus would have silently produced NaN practicalScore via undefined * varianceBonus."

patterns-established:
  - "Regime-hook wiring: a new optional orchestrator field is threaded through via `settings.style ? transform(input, ...) : input` immediately before the existing consumer call, at each regime branch independently — never a shared entry point across branches operating on structurally different data shapes."

requirements-completed: []  # STYLE-03/05 left Pending (partial delivery, see key-decisions); STYLE-04 was already Complete from Plan 04

coverage:
  - id: D1
    description: "BotSettings gains an optional style?: BotStyleParams field kept separate from budget (not folded into the Omit<> that structurally excludes policyTemperature)"
    requirement: "STYLE-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/selectBotMove.ts — grep 'Omit<SearchBudget' still excludes elo|policyTemperature; style is a sibling field"
        status: pass
    human_judgment: false
  - id: D2
    description: "blend<=0 branch: when style is present, applyStylePriorReweighting runs between deps.policy() and samplePolicy; undefined style samples the raw policy unchanged"
    requirement: "STYLE-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/selectBotMove.test.ts#selectBotMove — styled blend<=0 (STYLE-03 prior reweighting)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Search branch: when style is present, applyStyleScoreShaping runs between search() and argmaxLine/sampleRankedLines; undefined style leaves practicalScore untouched"
    requirement: "STYLE-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/selectBotMove.test.ts#selectBotMove — styled search branch (STYLE-04 score shaping)"
        status: pass
    human_judgment: false
  - id: D4
    description: "With settings.style undefined, selectBotMove is byte-identical to today's code path — no reweight call, no shaping pass"
    requirement: "STYLE-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/selectBotMove.test.ts#selectBotMove — style undefined regression (D-03 baseline invariant)"
        status: pass
    human_judgment: false
  - id: D5
    description: "budget.elo stays symmetric {w:elo,b:elo} regardless of style; botSampling.ts is untouched"
    requirement: "STYLE-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/selectBotMove.test.ts (budget.elo assertion in the styled search-branch test) + git diff --stat frontend/src/lib/engine/botSampling.ts (empty)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-22
status: complete
---

# Phase 182 Plan 06: Wire Style Hooks into selectBotMove Summary

**Adds an optional, budget-separate `BotSettings.style?: BotStyleParams` field and two ternary-guarded hooks (prior reweighting on the `blend<=0` branch, score shaping on the search branch) to `selectBotMove.ts`, proven byte-identical to today's code when `style` is undefined.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 2 (`selectBotMove.ts`, its test file)

## Accomplishments

- `BotSettings.style?: BotStyleParams` added as a new field, explicitly kept out of the `Omit<SearchBudget, 'elo' | 'policyTemperature'>` budget field so the D-02/WR-04 structural exclusion of `policyTemperature` stays intact.
- `blend<=0` branch: `deps.policy()` output now flows through `settings.style ? applyStylePriorReweighting(rawPolicy, fen, settings.style) : rawPolicy` before `samplePolicy`.
- Search branch (shared by `blend>=1` argmax and `0<blend<1` softmax): `snapshot.rankedLines` now flows through `settings.style ? applyStyleScoreShaping(snapshot.rankedLines, settings.style) : snapshot.rankedLines` before `argmaxLine`/`sampleRankedLines`.
- 4 new tests: two D-03 baseline-invariant regressions (one per regime) that derive the expected move independently (via direct `samplePolicy`/`argmaxLine` calls on the untransformed inputs, not a hardcoded literal alone — mutation-proof against an accidental unconditional reweight/shaping call), and two styled-path tests proving a style with a strongly-favoring lever (isPawnAdvance multiplier / varianceBonus) shifts the pick away from the undefined-style baseline.
- Fixed a latent gap in the existing test fixture: `makeLine` was missing `RankedLine`'s required `childScoreSpread` field (added to the type in Plan 04, silently uncaught since `*.test.ts` is outside `tsc -b`'s build and vitest's esbuild transform skips type-checking) — defaulted to `null` so future styled-line fixtures don't accidentally multiply `varianceBonus` by `undefined`.

## Task Commits

1. **Task 1: Add BotSettings.style and the two guarded regime hooks** — `873b3a7b` (feat)
2. **Task 2: Regression + styled-path tests for selectBotMove** — `e1566afa` (test)

## Files Modified

- `frontend/src/lib/engine/selectBotMove.ts` — `BotSettings.style?` field + two guarded hook call sites, imports from `./botStyle`
- `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` — style fixtures (`makeStyle`/`NEUTRAL_FEATURE_MULTIPLIERS`), `childScoreSpread` fix to `makeLine`, 2 new `describe` blocks (4 new tests)

## Verification

- `cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts src/lib/engine/__tests__/botSampling.test.ts` — 43/43 passing.
- `cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts src/lib/engine/__tests__/botSampling.test.ts src/lib/engine/__tests__/botStyle.test.ts` — 64/64 passing (no regression in the sibling pure-transform suite).
- `cd frontend && npx tsc -b` — zero errors.
- `grep -n "Omit<SearchBudget" frontend/src/lib/engine/selectBotMove.ts` — still excludes `'elo' | 'policyTemperature'`.
- `npx eslint src/lib/engine/__tests__/selectBotMove.test.ts src/lib/engine/selectBotMove.ts` — clean.

## Decisions Made

- STYLE-03 and STYLE-05 left `[ ]` Pending rather than marked complete — see key-decisions in frontmatter for the full rationale (this plan proves both hooks fire correctly in isolation; Plan 07's `useBotGame.ts`/`BotGameSettings.style` wiring is what makes an actual bot game session set `settings.style`, mirroring 182-05's established partial-delivery pattern for STYLE-01/STYLE-03).
- STYLE-04 was already Complete from Plan 04 — left as-is, no re-flip.
- Chose `isPawnAdvance` (not `isCapture`/`isCheck`) as the discriminating feature for the blend<=0 styled test — the existing `WHITE_FEN` fixture (king + one pawn, 6 legal moves) has zero legal captures/checks/exchanges/retreats, but two genuine pawn-advance moves (`e2e3`/`e2e4`), making it a real (non-vacuous) discriminator without introducing a new FEN fixture.
- Chose `varianceBonus` (not `scoreBonus`) as the discriminating lever for the search-branch styled test — `scoreBonus` is documented as uniform-additive-only and by design never changes `argmaxLine`'s ranking by itself; `varianceBonus x childScoreSpread` is the only STYLE-04 lever that differentiates between lines.

## Deviations from Plan

None — plan executed exactly as written. The `makeLine` `childScoreSpread` fix is additive test-fixture hygiene within the file this plan already scoped for Task 2, not a deviation from the plan's stated action.

## Issues Encountered

None.

## User Setup Required

None — pure TypeScript module changes, no external service configuration.

## Next Phase Readiness

- `selectBotMove.ts` is ready for Plan 07 to thread a resolved `BotStyleParams` (from `BotGameSettings.style`, resolved via `BOT_STYLE_BUNDLES` keyed by persona) into `settings.style` at the `useBotGame.ts` play-loop call site — no further `selectBotMove.ts` changes should be needed for that wiring.
- The calibration harness (Phase 168-family, if it later measures styled personas) can also pass `settings.style` directly, since the hook lives at the shared orchestrator both the play loop and the harness import.
- No blockers. `npx tsc -b` (zero errors) and the full engine suite subset run in verification are both green.

---
*Phase: 182-style-levers*
*Completed: 2026-07-22*

## Self-Check: PASSED

All claimed files found on disk (`selectBotMove.ts`, `selectBotMove.test.ts`, this SUMMARY.md); all 3 commits (`873b3a7b`, `e1566afa`, `822395b3`) found in git log.
