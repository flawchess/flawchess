---
phase: 166-bot-move-selection-core-selectbotmove
fixed_at: 2026-07-11T20:10:30Z
review_path: .planning/phases/166-bot-move-selection-core-selectbotmove/166-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 166: Code Review Fix Report

**Fixed at:** 2026-07-11T20:10:30Z
**Source review:** .planning/phases/166-bot-move-selection-core-selectbotmove/166-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (fix_scope: all — 5 warnings + 4 info)
- Fixed: 9
- Skipped: 0

The 5 warnings were fixed in the first pass (fix_scope: critical_warning); the 4 info findings were fixed in a follow-up pass with fix_scope: all. All results are consolidated here.

## Fixed Issues

### WR-01: NaN weights bypass the degenerate-distribution guard in `weightedPick`

**Files modified:** `frontend/src/lib/engine/botSampling.ts`, `frontend/src/lib/engine/__tests__/botSampling.test.ts`
**Commit:** 814569d8
**Applied fix:** Changed the degenerate guard to `if (!Number.isFinite(total) || total <= 0) return null;` so a NaN or Infinity weight total signals fallback instead of silently returning the alphabetically-last UCI via the exhausted-loop clamp. Added regression tests: all-NaN policy, single-NaN-poisoned policy, and all-Infinity policy all return `null`.

### WR-02: `argmaxLine` latches a NaN `practicalScore` as "best"

**Files modified:** `frontend/src/lib/engine/botSampling.ts`, `frontend/src/lib/engine/__tests__/botSampling.test.ts`
**Commit:** 60a310d2
**Applied fix:** Skip lines with non-finite `practicalScore` in the argmax scan, so an early NaN line can never win via the `best === null` arm; with all lines non-finite, `best` stays `null` and the orchestrator's `?? fallbackMove(...)` handles it. Added NaN-latch and all-non-finite regression tests.

### WR-03: `sampleRankedLines` has no `tau > 0` precondition

**Files modified:** `frontend/src/lib/engine/botSampling.ts`, `frontend/src/lib/engine/__tests__/botSampling.test.ts`
**Commit:** bee22866
**Applied fix:** Added `if (tau <= 0) return argmaxLine(lines);` — the mathematically correct argmax limit of the softmax — instead of `exp(NaN)` degeneracy at `tau = 0` or an inverted softmax at negative tau. Enforced in the public helper itself (D-09 exported API), not only at the orchestrator's `TAU_EPSILON` short-circuit. Added `tau = 0` and negative-tau regression tests.

### WR-04: `BotSettings.budget` type permits `policyTemperature` pass-through

**Files modified:** `frontend/src/lib/engine/selectBotMove.ts`, `frontend/src/lib/engine/__tests__/selectBotMove.test.ts`
**Commit:** 9d7a2579
**Applied fix:** Changed the budget type to `Omit<SearchBudget, 'elo' | 'policyTemperature'>` so the D-02 invariant is structural — a future call site threading the analysis board's temperature into the bot budget is a compile error (enforced by `tsc -b` on src). Updated the test helper's return type and added a `@ts-expect-error` assertion documenting the exclusion. Note: `tsconfig.app.json` excludes `*.test.ts` from the build, so the real CI gate is the `BotSettings` type itself (the test comment states this explicitly).

### WR-05: Tautological tau assertion in the "tau=0.05 softmax" test

**Files modified:** `frontend/src/lib/engine/__tests__/selectBotMove.test.ts`
**Commit:** 0a30ab88
**Applied fix:** Replaced the self-referential `expect(TAU_MAX * (1 - settings.blend)).toBeCloseTo(0.05)` with distribution-observing assertions: with scores {a1a2: 0.3, b1b2: 0.9}, a constant `rng: () => 0.001` draw sits between a1a2's softmax mass at tau=0.05 (~6.1e-6) and tau=0.1 (~2.5e-3), so the test asserts `b1b2` is picked (fails at tau=0.1 or if blend is ignored), and `rng: () => 1e-7` asserts `a1a2` is picked (proves real tau-sized mass on the lower-scored move). `TAU_MAX` is anchored with `expect(TAU_MAX).toBe(0.1)` so a curve change forces fixture recalibration (also keeps the export alive for knip).

### IN-01: Module header claims "three `?? fallbackMove(...)` call sites" — there are four

**Files modified:** `frontend/src/lib/engine/selectBotMove.ts`
**Commit:** 3defe52d
**Applied fix:** Reworded the D-09 header paragraph to the count-proof form "handled uniformly at every `?? fallbackMove(...)` call site below" (the review's suggested alternative), so the invariant record cannot drift again if a future change adds or removes a call site.

### IN-02: `TAU_EPSILON` short-circuit branch has no test coverage

**Files modified:** `frontend/src/lib/engine/__tests__/selectBotMove.test.ts`
**Commit:** ac2a0384
**Applied fix:** Added a test with `blend: 1 - 1e-9` (giving `tau = 1e-10 <= TAU_EPSILON`) asserting the argmax move (`c1c2`) is returned regardless of rng (three constant rng stubs: 0, 0.5, 0.999), mirroring the blend=1 test as the review suggested. The previously-only-untested orchestrator branch is now covered.

### IN-03: No validation or clamping of `settings.blend`

**Files modified:** `frontend/src/lib/engine/selectBotMove.ts`, `frontend/src/lib/engine/__tests__/selectBotMove.test.ts`
**Commit:** ba427d37
**Applied fix:** Adopted the review's preferred clamp option: `const blend = Number.isFinite(settings.blend) ? Math.min(1, Math.max(0, settings.blend)) : 1;` at the top of `selectBotMove`, with all three regime checks and the tau formula now reading the clamped local. NaN (the one value `Math.min`/`Math.max` cannot clamp) maps to 1, the deterministic argmax regime — documented at the clamp site and on the `BotSettings.blend` field doc. Added a regression test: `blend: NaN` returns the argmax move with one search call and zero policy calls.

### IN-04: `picked as string` deviates from the `noUncheckedIndexedAccess` narrowing convention

**Files modified:** `frontend/src/lib/engine/botSampling.ts`
**Commit:** 4b7efa49
**Applied fix:** Replaced `return picked as string;` with `return ucis[idx]!;` per the CLAUDE.md convention (non-null assertion for provably in-bounds indexes). Kept and extended the invariant comment: `!` narrows only the `undefined` arm, so unlike the type assertion it cannot mask a future drift of the `ucis` element type.

## Verification

- Per-fix: targeted vitest runs of the affected engine test files after every change; `npx tsc -b` and `eslint` on all touched files after the type-affecting fixes (IN-03, IN-04) — all clean.
- Test count grew 29 → 39 across the two engine test files (37 after the WR pass, +2 in the info pass: TAU_EPSILON short-circuit, NaN-blend clamp).
- All fixes were applied in an isolated git worktree on a temp branch and fast-forwarded back onto `gsd/phase-166-bot-move-selection-core-selectbotmove` (worktree, temp branch, and recovery sentinel all cleaned up).

---

_Fixed: 2026-07-11T20:10:30Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
