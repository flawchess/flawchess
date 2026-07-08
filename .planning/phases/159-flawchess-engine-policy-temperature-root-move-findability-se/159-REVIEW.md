---
phase: 159-flawchess-engine-policy-temperature-root-move-findability-se
reviewed: 2026-07-07T21:00:53Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
  - frontend/src/components/analysis/TemperatureSelector.tsx
  - frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx
  - frontend/src/components/analysis/__tests__/TemperatureSelector.test.tsx
  - frontend/src/hooks/useFlawChessEngine.ts
  - frontend/src/lib/engine/fallbackExpectimax.ts
  - frontend/src/lib/engine/findability.ts
  - frontend/src/lib/engine/mctsSearch.ts
  - frontend/src/lib/engine/policyTemperature.ts
  - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
  - frontend/src/lib/engine/__tests__/findability.test.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
  - frontend/src/lib/engine/__tests__/policyTemperature.test.ts
  - frontend/src/lib/engine/__tests__/treeCommon.test.ts
  - frontend/src/lib/engine/treeCommon.ts
  - frontend/src/lib/engine/types.ts
  - frontend/src/lib/flawChessVerdict.test.ts
  - frontend/src/lib/flawChessVerdict.ts
  - frontend/src/pages/Analysis.tsx
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 159: Code Review Report

**Reviewed:** 2026-07-07T21:00:53Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 159 adds three cohesive features: a policy-temperature transform (`applyPolicyTemperature`) that reshapes the root-mover's Maia policy before search, a root-only findability ranking weight (`rankScore`/`pRefForElo`) folded into `buildRankedLines`, and the `TemperatureSelector` slider + findability-gated verdict prose. The engine plumbing is careful: both `SearchRunner` implementations share `treeCommon.ts` primitives and apply temperature identically (`sideMatchesMover` gate + `DEFAULT_POLICY_TEMPERATURE` short-circuit), the degenerate-input guards mirror each other, and the SAN-keyed findability gate (`computeFindabilityGate`) correctly reads raw Maia probabilities rather than search-internal priors. No security issues (pure client-side chess logic, no secrets, no injection surface).

The material concern is a **contract break introduced by re-sorting `rankedLines` on findability-weighted `rankScore` instead of `practicalScore`**: the frozen `types.ts` contract, the hook's state doc, and the `FlawChessEngineLines` UI all still assume descending-practical-score ordering. The practical-score badges in the ranked-lines list will now render out of numeric order and the "by practical rank" badge shading is mislabeled. A secondary concern is a semantic mismatch between the findability `pRef` anchors (documented against raw Maia probability) and the renormalized prior actually fed to `rankScore`.

## Warnings

### WR-01: `rankedLines` re-sorted on `rankScore` breaks the documented `practicalScore` ordering contract consumed downstream

**File:** `frontend/src/lib/engine/treeCommon.ts:205-209` (sort), with stale contract at `frontend/src/lib/engine/types.ts:50-61` and `frontend/src/hooks/useFlawChessEngine.ts:70-72`

**Issue:** `buildRankedLines` now sorts candidates by `sortRankScore = rankScore(child.prior, pRef, child.value)` descending, not by `practicalScore` (`child.value`). This is intended per D-01, but the public contract and consumers were not updated:

- `types.ts:50` / `RankedLine` and `useFlawChessEngine.ts:71` (`FlawChessEngineState.rankedLines`) both still document "pre-sorted descending by practicalScore." That is now false — `rankedLines[0]` can have a strictly lower `practicalScore` than `rankedLines[1]`.
- `FlawChessEngineLines.tsx:127-133` renders each row's `practicalScore` as a gold badge whose shade is chosen "by practical rank (best/2nd/3rd)" (`FLAWCHESS_ENGINE_BADGE_SHADES[lineIndex]`) and labels rows "Line 1 … practically X for you". With the new sort, the "best" gold shade can sit on a row whose practical cp is numerically lower than the row below it, so the practical badges visibly appear out of descending order and the shade no longer reflects practical rank.

Because `types.ts` is declared a frozen contract, an inaccurate ordering guarantee there is more than a cosmetic doc slip — any consumer that trusts it (or the badge-shade logic that already does) is now wrong.

**Fix:** Update the contract and the consumer semantics to say "sorted descending by findability-weighted rank," and either (a) relabel the `FlawChessEngineLines` badge shading as findability rank rather than practical rank, or (b) if the practical badges must read as a descending list, sort a display copy by `practicalScore` for that component while keeping the findability order for `rankedLines[0]` selection. Minimum viable fix — correct the two doc comments and the `FlawChessEngineLines.tsx:129` "by practical rank" comment/aria wording:

```ts
// types.ts RankedLine — practicalScore field
/** D-06: root-side-to-move expected score, 0-1. NOTE: rankedLines are ordered by
 *  the Phase 159 findability-weighted rankScore, NOT by this field — rankedLines[0]
 *  is the practical (findability-adjusted) pick, which may have a lower practicalScore
 *  than a lower-ranked line. */
```

### WR-02: Findability `pRef` anchors are calibrated against raw Maia probability but `rankScore` is fed the renormalized post-truncation prior

**File:** `frontend/src/lib/engine/treeCommon.ts:202` (call site) and `frontend/src/lib/engine/findability.ts:22-39,73-76`

**Issue:** `findability.ts`'s docstring frames `P_ref` explicitly in raw-probability terms ("a 600-rated player rarely finds a 5%-probability move") and the anchor values (0.12 … 0.005) read as raw Maia move probabilities. But `buildRankedLines` passes `child.prior` as `pYou`, and `child.prior` at the root is the value produced by `applyPolicyTemperature` → `truncateAndRenormalize` → renormalization over the surviving ~90%-mass set (plus the root hard cap). Renormalizing over a truncated set systematically inflates each surviving prior relative to the raw Maia probability the anchors describe. The effect is that `min(1, pYou/pRef)` saturates more readily than the anchor comments imply, so findability suppression is weaker than the documented curve suggests — and it gets weaker still as temperature rises (flatter → more surviving mass → larger renormalization inflation). The code comment at `treeCommon.ts:51-56` asserts `child.prior` "is exactly the P_you the findability ranking reads," which papers over the raw-vs-renormalized distinction the `findability.ts` prose relies on.

This is partly acknowledged (findability.ts:26-30 calls the curve "ASSUMED … live UAT may retune"), so it may be an accepted approximation — but the docstring's raw-probability justification actively contradicts the implementation, which will mislead the UAT retune.

**Fix:** Reconcile the two. Either feed `rankScore` the raw Maia probability (the same distribution `computeFindabilityGate` uses) so the anchors mean what the docstring says, or update the `findability.ts` docstring and `P_REF_ANCHORS` framing to state that `pYou` is the renormalized truncated prior (not raw probability) and that the anchors must be tuned in that space. At minimum, correct the `treeCommon.ts:51-56` comment so it doesn't claim equivalence between the renormalized prior and the raw `P_you` the findability design describes.

## Info

### IN-01: Temperature no-op short-circuit relies on exact float equality with `DEFAULT_POLICY_TEMPERATURE`

**File:** `frontend/src/lib/engine/mctsSearch.ts:304-308`, `frontend/src/lib/engine/fallbackExpectimax.ts:174-178`, `frontend/src/components/analysis/TemperatureSelector.tsx:48-50`

**Issue:** Both runners skip `applyPolicyTemperature` only when `temperature !== DEFAULT_POLICY_TEMPERATURE` (exact `=== 1`). The slider produces temperature via `2 ** position` with `SLIDER_STEP = 0.01` over `[-1, 1]`. Position 0 yields exactly `1`, and the initial/untouched state is the imported constant `1`, so the intended "never perturb default users" guarantee holds. But any slider interaction that lands at a position of, say, `1e-16` instead of exactly `0` yields `2 ** 1e-16 ≈ 1.0000000000000002`, tripping the transform and introducing the exact floating-point renormalization drift the module header warns about. The guarantee is correct for the default path but brittle for a user who drags back toward center.

**Fix:** Consider an epsilon band around the default (`Math.abs(temperature - DEFAULT_POLICY_TEMPERATURE) < 1e-9`) for the short-circuit, or snap the slider's center detent. Low priority — the determinism-critical untouched-user path is already exact.

### IN-02: `extraRootMoves` receive prior 0, forcing `rankScore` to 0 and sorting them below every truncated candidate regardless of objective value

**File:** `frontend/src/lib/engine/mctsSearch.ts:310-315`, `frontend/src/lib/engine/fallbackExpectimax.ts:180-186`, ranked at `frontend/src/lib/engine/treeCommon.ts:202`

**Issue:** Extra root moves merged in after truncation are assigned `prior = 0`. In `buildRankedLines`, `rankScore(0, pRef, value)` = `min(1, 0) * value` = `0` for any `value`, so every extra-root move sorts to the very bottom (tie-broken by UCI), discarding its objective `value` entirely from the ordering. A Stockfish-injected objectively-best move with near-zero Maia probability would therefore never surface as `rankedLines[0]` even if it were the practical pick. This is latent today — `extraRootMoves` is intentionally unset (`useFlawChessEngine.ts:228`) — and is arguably consistent with findability's "unfindable moves are demoted" intent, but the total collapse to a UCI-only tie-break (rather than a small-but-nonzero weight) is a sharper behavior than the saturating factor's stated design and would bite if `extraRootMoves` is ever enabled.

**Fix:** When enabling `extraRootMoves`, decide deliberately whether a 0-prior move should rank strictly last or retain a floor weight (e.g. the D-05 exploration floor already applied elsewhere), and document the choice. No action needed while `extraRootMoves` stays unset.

### IN-03: Redundant "Play style" labeling on the temperature slider container

**File:** `frontend/src/components/analysis/TemperatureSelector.tsx:71-77`

**Issue:** The wrapper `<div>` has both `role="group"` with `aria-label="Play style"` and a visible child `<span>Play style</span>`. Screen readers will announce "Play style" for the group and again read the visible label. Prefer `aria-labelledby` pointing at the visible span (give it an `id`) over a duplicate `aria-label`, or drop one of the two.

**Fix:**
```tsx
<div role="group" aria-labelledby="temp-selector-label" ...>
  <span id="temp-selector-label" className="text-sm text-muted-foreground">Play style</span>
  ...
```

---

_Reviewed: 2026-07-07T21:00:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
