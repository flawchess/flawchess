---
phase: 166-bot-move-selection-core-selectbotmove
reviewed: 2026-07-11T17:40:08Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - frontend/src/lib/engine/__tests__/botSampling.test.ts
  - frontend/src/lib/engine/__tests__/selectBotMove.test.ts
  - frontend/src/lib/engine/botSampling.ts
  - frontend/src/lib/engine/selectBotMove.ts
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 166: Code Review Report

**Reviewed:** 2026-07-11T17:40:08Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the two new engine modules (`botSampling.ts` pure helpers, `selectBotMove.ts` orchestrator) and their test files against the Phase 166 plan contract (BOT-01..04, D-01..D-14). All verification gates were re-run independently: the 29 tests pass, `tsc -b` is clean, ESLint passes (only pre-existing warnings in generated `coverage/`), and knip reports no dead exports. The chess.js `Move.lan` promotion-suffix concern was checked against the vendored source (`node_modules/chess.js/dist/cjs/chess.js:1345-1347`) — `lan` does append the promotion piece, so `fallbackMove` emits valid UCI on promotion positions.

The regime dispatch, symmetric-ELO budget construction, single-policy-call invariant, and seeded determinism all match the plan. However, the D-13 "degenerate distribution -> null -> fallback" contract has a proven hole: **NaN weights bypass the `total <= 0` guard** in `weightedPick` and silently select the alphabetically-last move instead of triggering the fallback (verified by execution). The same non-finite blind spot exists in `argmaxLine`, and the exported `sampleRankedLines` helper silently returns the *worst* move when called with `tau <= 0` (guarded at the one current call site, but it is a public API per D-09). Additionally, the `BotSettings.budget` type permits a caller to thread `policyTemperature` into the search budget, contradicting the D-02 invariant the module header claims to enforce structurally, and one test assertion for the tau curve is tautological.

No critical/security findings: inputs are caller-trusted per the phase threat model, the RNG is explicitly non-cryptographic by design (T-166-03 accepted), and no injection/eval/secret patterns exist.

## Warnings

### WR-01: NaN weights bypass the degenerate-distribution guard in `weightedPick` — silently picks the last UCI instead of falling back

**File:** `frontend/src/lib/engine/botSampling.ts:33-42`
**Issue:** The D-13 contract (module header, lines 5-9) states degenerate distributions return `null` so the orchestrator falls back to a uniform-random legal move. But the guard `if (total <= 0) return null;` is false when `total` is `NaN` (all NaN comparisons are false), so execution continues: `draw = rng() * NaN = NaN`, `NaN < cumulative` never matches, and the exhausted-loop clamp (intended only for the `rng() === 1` edge case) returns the alphabetically-last sorted UCI. Verified by execution:
- `weightedPick([['a1a2', NaN], ['b1b2', NaN]], rng)` → `'b1b2'` (not `null`)
- `weightedPick([['a1a2', 0.5], ['b1b2', NaN]], () => 0.01)` → `'b1b2'` — a single NaN entry poisons the whole distribution, overriding a 0.5-weight valid entry even at a draw of 0.01.

This is on the live `blend=0` path: `deps.policy` output crosses a Web Worker boundary (T-166-01), and a provider renormalization defect (`p / 0`) yields NaN probabilities. The bot would then deterministically play the alphabetically-last policy key every move rather than the intended random-legal fallback.
**Fix:**
```typescript
// NaN total (e.g. a NaN weight from a defective provider) must count as
// degenerate: `total <= 0` is false for NaN, so use the negated form.
if (!(total > 0)) return null;
```
Optionally also add `Number.isFinite(total)` for an `Infinity` total (an all-`Infinity` policy currently degrades the walk similarly). Add test cases: `samplePolicy({ a1a2: NaN, b1b2: NaN }, rng)` and `samplePolicy({ a1a2: 0.5, b1b2: NaN }, rng)` both return `null`.

### WR-02: `argmaxLine` latches a NaN `practicalScore` as "best" and never replaces it

**File:** `frontend/src/lib/engine/botSampling.ts:87-94`
**Issue:** If the first line scanned has `practicalScore: NaN`, it becomes `best` (via the `best === null` arm). Every subsequent comparison — `line.practicalScore > NaN` and `line.practicalScore === NaN` — is false, so the NaN line wins unconditionally: `argmaxLine([{rootMove:'a1a2', practicalScore: NaN}, {rootMove:'b1b2', practicalScore: 0.9}])` returns `'a1a2'`. This is the live `blend=1` path (BOT-01's deterministic-argmax contract): one non-finite score from a search/backup defect makes the "full-stockfish" bot play an arbitrary array-first move instead of the true argmax, with no fallback signal.
**Fix:**
```typescript
for (const line of lines) {
  // NaN practicalScore never wins (all NaN comparisons are false, so an
  // early NaN `best` would otherwise be unbeatable) — skip non-finite lines.
  if (!Number.isFinite(line.practicalScore)) continue;
  const isBetter = ...
}
```
With all lines non-finite, `best` stays `null` and the orchestrator's existing `?? fallbackMove(...)` handles it. Add a NaN-fixture test.

### WR-03: `sampleRankedLines` has no `tau > 0` precondition — `tau = 0` silently returns the alphabetically-last (possibly worst) move, negative `tau` inverts the softmax

**File:** `frontend/src/lib/engine/botSampling.ts:63-75`
**Issue:** At `tau = 0` the max-score line's weight is `Math.exp((max - max) / 0) = Math.exp(NaN) = NaN` while every other line's weight is `Math.exp(-Infinity) = 0`; the NaN total then rides the WR-01 hole and returns the alphabetically-last sorted UCI regardless of score. Verified by execution: lines `[a1a2: 0.99, z1z2: 0.01]` at `tau = 0` return `'z1z2'` — the *worst* move, when the mathematically correct limit of the softmax is the argmax. A negative `tau` is worse: it flips the exponent sign, concentrating mass on the *lowest* `practicalScore`. The orchestrator's `TAU_EPSILON` short-circuit protects the one current call site, but this helper is a deliberately-exported public API (D-09: "pure, sync, separately-exported helpers") that Phase 168's calibration harness may call directly, and nothing in the signature, docs, or a guard communicates the `tau > 0` precondition.
**Fix:**
```typescript
export function sampleRankedLines(lines, tau, rng): string | null {
  if (lines.length === 0) return null;
  // tau <= 0 is the argmax limit of the softmax; computing it directly
  // avoids exp(NaN)/sign-flip degeneracy for out-of-contract tau values.
  if (tau <= 0) return argmaxLine(lines);
  ...
}
```
(Note: the WR-01 fix alone converts `tau = 0` into a `null` → uniform-random fallback, which is safe but still wrong — the correct limit is argmax.)

### WR-04: `BotSettings.budget` type permits `policyTemperature` pass-through, defeating the D-02 invariant

**File:** `frontend/src/lib/engine/selectBotMove.ts:67,103-108`
**Issue:** `budget: Omit<SearchBudget, 'elo'>` removes only `elo`, so `policyTemperature?: number` (a member of `SearchBudget`, `types.ts:46`) remains a legal field on `settings.budget`. The construction `{ ...settings.budget, elo: {...} }` then spreads a caller-supplied `policyTemperature` straight into the search budget. This contradicts the module's own D-02 header ("the analysis board's `applyPolicyTemperature` transform is NEVER used here") and its inline comment at line 106 ("policyTemperature intentionally omitted"), which the code does not actually enforce — it merely doesn't *set* the field. A Phase 169 call site reusing the analysis board's budget-building helper (which does set `policyTemperature`, per `useFlawChessEngine.ts`) would silently reshape the bot's policy and invalidate Phase 168's calibration curve, exactly the regression the plan's Pitfall 3/D-02 discussion warns about. The existing test (`selectBotMove.test.ts:194-208`) only proves the field is absent when the caller doesn't pass it.
**Fix:**
```typescript
/** Caller-supplied search bounds ... policyTemperature is excluded by type (D-02). */
budget: Omit<SearchBudget, 'elo' | 'policyTemperature'>;
```
This makes the D-02 invariant structural (a compile error at any future call site that tries to thread it) instead of aspirational. Add a test that a budget object cast with `policyTemperature` set does not reach the search stub, or rely on the type-level exclusion plus a `@ts-expect-error` assertion.

### WR-05: Tautological tau assertion — the "tau=0.05 softmax" test never observes the implementation's tau

**File:** `frontend/src/lib/engine/__tests__/selectBotMove.test.ts:174-175`
**Issue:** The test named "calls deps.search once with a real onSnapshot function reference and a tau=0.05 softmax" asserts `expect(TAU_MAX * (1 - settings.blend)).toBeCloseTo(0.05, 10)` — this recomputes the tau formula inside the test, independent of the code under review. It passes even if `selectBotMove` uses `tau = 42` or ignores `blend` entirely; the only behavioral assertion is that the move is one of the two candidates, which any sampling satisfies. The plan's SC1 acceptance criterion ("computes tau = TAU_MAX*(1-0.5)=0.05") is therefore not actually verified, and the D-04/D-05 τ(b) curve — the core of BOT-01's mixed regime — has no regression protection.
**Fix:** Tau is observable through the sampling distribution with a constant rng. With lines `[a1a2: 0.3, b1b2: 0.9]`, the softmax mass on `a1a2` is `exp(-0.6/tau) / (1 + exp(-0.6/tau))`: ~`6.1e-6` at tau=0.05 but ~`2.5e-3` at tau=0.1. A stub `rng: () => 0.001` distinguishes them:
```typescript
// draw = 0.001*total: below a1a2's cumulative mass at tau=0.1 (~2.5e-3)
// but above it at the correct tau=0.05 (~6.1e-6) -> must pick b1b2.
const deps = baseDeps({ search, rng: () => 0.001 });
expect(await selectBotMove(WHITE_FEN, settings, deps)).toBe('b1b2');
// and with rng: () => 1e-7 (below the tau=0.05 mass) -> must pick a1a2.
```

## Info

### IN-01: Module header claims "three `?? fallbackMove(...)` call sites" — there are four

**File:** `frontend/src/lib/engine/selectBotMove.ts:37-39`
**Issue:** The D-09 header paragraph says degeneracy is "handled uniformly at the three `?? fallbackMove(...)` call sites below", but the function has four (lines 99, 118, 124, 127) — the `TAU_EPSILON` short-circuit added a fourth beyond the plan's three. Doc/code drift in a header that downstream phases are told to treat as the invariant record.
**Fix:** Change "three" to "four", or reword to "at every `?? fallbackMove(...)` call site".

### IN-02: `TAU_EPSILON` short-circuit branch has no test coverage

**File:** `frontend/src/lib/engine/selectBotMove.ts:122-125`
**Issue:** The only untested branch in the orchestrator. It is reachable (e.g. `blend = 1 - 1e-9` gives `tau = 1e-10 <= TAU_EPSILON`), and it is the sole guard standing between the orchestrator and WR-03's `sampleRankedLines` degeneracy at near-zero tau.
**Fix:** Add a test with `blend: 1 - 1e-9` asserting the argmax move is returned regardless of rng (mirroring the blend=1 test).

### IN-03: No validation or clamping of `settings.blend` — a NaN blend reaches the softmax path with `tau = NaN`

**File:** `frontend/src/lib/engine/selectBotMove.ts:95,115,121-122`
**Issue:** `blend` is documented as `[0,1]` and `settings` is caller-trusted per the threat model, so this is informational: a `NaN` blend fails all three regime checks (`<= 0`, `>= 1`, `tau <= TAU_EPSILON` are all false for NaN) and flows into `sampleRankedLines(lines, NaN, rng)`, where every weight is `exp(NaN) = NaN` and the WR-01 hole silently selects the alphabetically-last move. The WR-01 fix converts this into the random-legal fallback; a one-line clamp would make it argmax-or-sample as intended.
**Fix:** `const blend = Math.min(1, Math.max(0, settings.blend));` (NaN clamps need `Number.isFinite` first), or document that non-finite blend is a caller precondition bug like D-14.

### IN-04: `picked as string` deviates from the project's `noUncheckedIndexedAccess` narrowing convention

**File:** `frontend/src/lib/engine/botSampling.ts:141`
**Issue:** CLAUDE.md's frontend rules prescribe `!` non-null assertion "when the index is provably in bounds". `picked as string` achieves the same silencing but is a *type* assertion — it would also mask a future type drift of `ucis` (e.g. to `(string | undefined)[]` or a different element type), whereas `ucis[idx]!` only removes the `undefined` arm. The accompanying invariant comment is good; only the mechanism differs from convention.
**Fix:** `return ucis[idx]!;` (keep the comment).

---

_Reviewed: 2026-07-11T17:40:08Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
