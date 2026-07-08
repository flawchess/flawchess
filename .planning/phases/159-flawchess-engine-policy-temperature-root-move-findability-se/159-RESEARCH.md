# Phase 159: FlawChess Engine policy temperature + root-move findability - Research

**Researched:** 2026-07-07
**Domain:** Client-side search-ranking algorithm change (TypeScript, pure functions) + a UI slider, on top of the already-shipped Phase 153-158 FlawChess Engine (MCTS/expectimax practical-play search).
**Confidence:** HIGH — this phase is 100% internal codebase modification (no new libraries, no external APIs). Every claim below is `[VERIFIED: codebase]` unless marked otherwise. The one genuinely open unknown is the numeric calibration of `P_ref(ELO)`, which no amount of code-reading can resolve — flagged explicitly in Assumptions Log.

## Summary

This phase modifies exactly one ranking function (`buildRankedLines` in `treeCommon.ts`) to stop discarding the root player's own move-probability, and adds one new pure transform (policy temperature) that reshapes the Maia distribution before it's consumed by both the search and the new ranking. Both threads are algebra + wiring, not new architecture: the search core's node/backup/select machinery (Phase 153, locked) is untouched, and the fix is deliberately scoped to the ranking layer only, per D-01's "the per-move practical score V(X) ... is untouched."

The codebase already contains everything needed to implement Thread B cheaply: every root child (`EngineNode`/`FallbackNode`) already carries `prior`, the exact renormalized Maia probability the ranking currently ignores — `P_you(X)` is not a new signal to compute, it is a field already sitting unused in the sort. The fix is: stop sorting by `child.value` alone; sort by `min(1, child.prior / P_ref(elo)) * child.value` instead, computed only at the root, only for sorting (the stored `practicalScore` on `RankedLine` stays `child.value`, verbatim, per D-04).

Thread A (temperature) is best implemented at the **orchestrator layer** (inside `mctsSearch.ts`'s `dispatchExpansion` and `fallbackExpectimax.ts`'s `expandNode`, immediately after `providers.policy()` resolves and before `truncateAndRenormalize`), not inside `maiaQueue.ts`. This sidesteps the cache-key concern the phase's own CONTEXT.md flags as an open risk: the Maia queue's `(fen, elo)` cache stays a pure raw-Maia oracle cache, completely untouched, because temperature is applied to the *result* after cache lookup, not baked into what gets cached. It also naturally satisfies D-05 (user's-side-only): the orchestrator already knows `rootMover` and each node's `side`, so "is this the user's side to move" is a one-line comparison requiring no new field on `SearchBudget` beyond the temperature value itself.

Both threads compose automatically without extra glue: because temperature is applied before `truncateAndRenormalize` (D-07) and `truncateAndRenormalize`'s output becomes `child.prior`, Thread B's `rankScore` reads the *already temperature-adjusted* prior with zero additional wiring. This is the single most important structural finding of this research — **there is no third code path that needs to "combine" temperature and findability; they compose because they are sequential pure transforms over the same value.**

The verdict-copy gate (D-10/D-11/D-12) is architecturally decoupled from both of the above by construction: `RankedLine` has no `prior` field at all, so the verdict component structurally *cannot* read the temperature-adjusted search-internal probability even by accident. The gate must be wired to read from the same raw-Maia, ELO-keyed data source that already powers the "Moves by Rating" chart (`maia.perElo` + `selectCandidatesByMass`'s output), which Analysis.tsx already computes — this satisfies D-12 (raw Maia, chart-identical) essentially for free.

**Primary recommendation:** Implement Thread B as a new pure module (`findability.ts`) consumed only by `treeCommon.ts`'s `buildRankedLines`; implement Thread A as a new pure module (`policyTemperature.ts`) consumed only by the two orchestrators' `dispatchExpansion`/`expandNode`; thread a new optional `SearchBudget.policyTemperature` field (default 1, short-circuited to a no-op) through both call sites; wire the verdict gate as a new pure function in `flawChessVerdict.ts` fed by primitives the caller (`FlawChessAgreementVerdict.tsx`) already has or can derive from data `Analysis.tsx` already computes.

## User Constraints

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Findability mechanism (Thread B)**
- **D-01 (LOCKED):** Root ranking sorts by `rankScore = min(1, P_you/P_ref) · V(X)` — a saturating linear findability factor. **β is fixed at 1** (no exponent; documented as a future one-liner if calibration ever needs a sharper knee).
  - Rejected raw `P^β·V`: P spans orders of magnitude while V doesn't, so the workable β window is narrow and position-dependent (in the 600-ELO case, β ∈ ~(0.15, 0.25) — outside it the 57% Mistake Rxf2 wins). Every miscalibration fails toward the greedy modal engine.
  - Rejected hard floor: needs an explicit empty-set fallback branch, and moves pop in/out of the ranking discontinuously while dragging the ELO/temperature sliders.
  - The saturation is the load-bearing property: any move at or above `P_ref` gets factor 1, so **the modal move can never be boosted above its own V** — the greedy failure mode is impossible by construction, not calibrated away.
- **D-02:** `P_ref(ELO)` curve (anchors and interpolation shape) is **fully Claude's discretion**. Only the qualitative shape is fixed (aggressive at 600, near-off at master) plus three locked regression cases (see D-03).
- **D-03 (acceptance regression cases, from live observations):**
  - Nb5 (5% @600, currently "Best") must NOT top the ranking.
  - Qxf2 (9% @600, Good) must win at 600 — i.e. the fix must not overshoot into recommending Rxf2 (57%, Mistake).
  - Qb8 (@1000, tail move outside the chart's plotted set) must not top the ranking.
- **D-04:** FC card display unchanged: the badge keeps showing the practical score `V`; ordering silently uses `rankScore`. No new markers/UI for demoted moves. (Divergence between sort order and badge is only possible for below-`P_ref` moves, which rarely reach the shown top lines.) The existing popover copy may mention findability weighting.

**Temperature scope (Thread A)**
- **D-05:** Temperature applies to the **user's side only** (`P_you`); the opponent's policy stays raw Maia at the ELO setting. Rationale: flattening the opponent has the *opposite* effect (a fallible opponent misses refutations, making sharp moves look better) — a both-sides dial would partially cancel itself. Two knobs rejected as more UI than the seed asked for.
- **D-06:** The temperature-adjusted distribution feeds **the MCTS search policy AND the findability `P_you`** (they compose, per SEED-085). The Maia "Moves by Rating" chart keeps showing **raw** Maia data — it is a measurement of real humans, not a model artifact.
- **D-07:** Temperature is applied **BEFORE** the 0.9-mass candidate truncation (`truncateAndRenormalize`): T>1 puts real mass on tail moves so they genuinely enter the searched set. The fixed visit budget spreads thinner; a named hard cap on root candidate count may guard pathological flatness (Claude's discretion).

**Slider UX**
- **D-08:** Range **0.5–2.0, log-symmetric** around the default **1.0** (1.0 at the visual center; halving and doubling are equal steps). Session-only state, default 1.0 on every page load — matches the ELO slider's existing behavior (no localStorage, no URL param). Position: directly below the ELO slider (locked by SEED-085; the ELO slider lives below the Maia card since 155 UAT and drives both engines).
- **D-09:** Plain-language labeling: a label like "Play style" / "Fallibility" with endpoint captions ("Sharper" ↔ "More human"); the numeric T value shown subtly. "Temperature" jargon stays out of the primary copy.

**Verdict copy gating (ride-along)**
- **D-10:** The findability claim ("far easier to find and play") requires BOTH: `P_you(FC pick)` exceeds `P_you(SF best)` by a named margin, AND the pick is inside the chart's plotted candidate set (`selectCandidatesByMass` output) — so the chart visibly backs the words by construction.
- **D-11:** When the gate fails, the safe-tier prose falls back to wording the evals actually support (nearly as good / safer follow-ups) with no findability claim — one extra copy variant, per SEED-085's "say what it can back".
- **D-12:** The gate reads **raw Maia at the selected ELO** — the same distribution the chart displays, so non-contradiction with the chart is exact. Temperature stays a search-internal modeling dial (at T≠1 an adjusted-P gate could contradict the raw chart, reintroducing the original defect).

### Claude's Discretion
- `P_ref(ELO)` anchors and interpolation shape (D-02).
- The temperature transform itself (standard `p^(1/T)` renormalized or equivalent) and where it's implemented in the pipeline (provider vs search layer), subject to D-06/D-07.
- Named hard cap on root candidate count under extreme flattening (D-07).
- Slider styling/step count, following the ELO slider's look; desktop + mobile parity per project rules.
- The named margin in the verdict gate (D-10) and exact fallback wording (D-11), following the popover-copy-minimalism norm.
- Whether `ROOT_PRIOR_FLOOR` / exploration behavior needs any adjustment — not discussed; the fix is ranking-layer, so the floor can stay as-is unless research finds a reason.
- Test strategy, subject to project norms (vitest, pure lib functions preferred; the three D-03 cases become regression tests in whatever form fits).

### Deferred Ideas (OUT OF SCOPE)
- Explicit two-track "findable vs ideal" arrows / teaching surface — rated below the chosen approach in SEED-085; only revive if a distinct teaching surface is wanted.
- Per-side temperature knobs (self + opponent) for time-pressure modeling — SEED-082's original vision; D-05 chose self-only for this phase.
- Played-move vs recommended comparison — already captured as SEED-086.
- "Hard to find" marker on demoted-but-shown FC moves — rejected for this phase (D-04, zero new UI); could revisit if users are confused.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEED-085 | Thread A (policy-temperature slider) + Thread B (root-move findability weighting in the ranking) + verdict-copy findability gate, all committed | See Architecture Patterns (findability + temperature modules), Code Examples, and Common Pitfalls below. No new requirement IDs were minted in REQUIREMENTS.md for this phase — SEED-085 is the sole traceability anchor per CONTEXT.md; the milestone's REQUIREMENTS.md v2.0 table (ENGINE/POOL/DISPLAY/ARROW/REVIEW) is unaffected and should NOT be edited by this phase's plan. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **`ty check` must pass with zero errors** — new functions need explicit return types; `Sequence`/`Literal` rules are backend-only (N/A here), but "no bare `str` for a fixed value set" analog applies: `RankedLine`, `SearchBudget`, `EngineProviders` are all TS interfaces — keep new fields explicitly typed, no `any`.
- **No magic numbers** — every new threshold (`P_ref` anchors, `FINDABILITY_MARGIN`, any root-candidate hard cap, the log-slider's min/max/step) must be a named exported constant, mirroring `ROOT_PRIOR_FLOOR`, `POLICY_MASS_THRESHOLD`, `SHARP_DROP_THRESHOLD`, `NEARLY_SAME_EVAL_CP`.
- **Comment bug fixes** — N/A (this is new capability, not a bug fix), but the *reasoning* behind D-01's saturating-floor choice (vs. the rejected `P^β·V`) should be captured in the new module's header comment, mirroring every other file in `lib/engine/` (each carries a "why this shape, what was rejected" header).
- **Keep functions small/shallow** — `buildRankedLines` currently loops once and sorts once; adding the rankScore computation should stay a single extra `.map()`/inline calculation per child, not a new nesting level. If the temperature/findability logic grows past ~15-20 logic lines inline, extract a named helper (already the plan below).
- **Mobile-first / mobile parity** — the new temperature slider MUST render in both `humanTab` (mobile, Analysis.tsx ~line 1630-1651) and the desktop human column (~line 1796-1829), exactly mirroring how `eloSelector` is placed in both today. Needs a `data-testid`.
- **`data-testid` + ARIA on all new interactive elements** — the new slider needs a `data-testid` (e.g. `analysis-temperature-selector`, mirroring `analysis-elo-selector`), an `aria-label`, and (since it's a Radix `Slider` per-thumb) a `thumbLabels` entry, exactly like `EloSelector.tsx`.
- **`text-sm` floor** — the "Sharper"/"More human" endpoint captions and the subtle numeric T-value label must not drop below `text-sm` (no `text-xs`), same rule that already governs `EloSelector`'s value label.
- **Theme constants in `theme.ts`** — any new color used for the slider (if not reusing `FLAWCHESS_ENGINE_ACCENT`) must be added there, not hard-coded.
- **`noUncheckedIndexedAccess`** — any array/Record indexing in the new `P_ref` anchor lookup or the temperature curve interpolation must narrow before use (mirrors `EloSelector.tsx`'s `ladder[0] ?? value` pattern already in this codebase).
- **Knip** — new exported pure functions (`applyPolicyTemperature`, `pRefForElo`, `rankScore`/`findabilityFactor`, a verdict-gate function) must actually be imported somewhere (they will be, by the orchestrators/verdict component) or knip will flag them as dead exports in CI.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Root-move findability ranking (`rankScore`) | Browser / Client (pure lib, `lib/engine/`) | — | Purely a re-sort of already-computed in-browser search output; no new data source, no server involvement (v2.0 milestone is 100% client-side by design). |
| Policy temperature transform | Browser / Client (pure lib, `lib/engine/`) | — | Reshapes the Maia policy `Record<string, number>` the search already holds in memory; a pure math transform, same tier as `truncateAndRenormalize`. |
| Temperature slider UI | Browser / Client (React component) | — | New Radix-`Slider`-backed control, session-only React state, mirrors `EloSelector`. No backend, no persistence (D-08 explicitly rules out localStorage/URL param). |
| Verdict-copy findability gate | Browser / Client (pure lib `flawChessVerdict.ts` + React `FlawChessAgreementVerdict.tsx`) | — | Reuses data (`maia.perElo`, `shownSans`) already computed client-side in `Analysis.tsx` for the existing Moves-by-Rating chart; no new fetch. |
| Maia raw-policy provider (`maiaQueue.ts`) | Browser / Client (Web Worker) | — | Untouched by this phase — see Architecture Patterns below for why the cache stays pure. |

## Standard Stack

### Core

No new libraries. This phase is pure algorithm/UI work on top of the existing stack:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| (none new) | — | — | The entire v2.0 FlawChess Engine milestone is deliberately zero-new-deps (REQUIREMENTS.md "Out of Scope": "Server-side search... latency-miserable; the engine is client-side everything"). This phase continues that constraint — it is a ranking-algebra + UI-slider change over existing `lib/engine/*.ts` and `components/analysis/*.tsx` files. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `radix-ui` (`Slider` primitive, already a dependency via `@/components/ui/slider`) | already installed | Backs the new temperature slider, identical primitive `EloSelector.tsx` already uses | Reuse `<Slider>` from `@/components/ui/slider` verbatim — do not introduce a second slider implementation. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Saturating linear findability factor (`min(1, P/P_ref)·V`, D-01, locked) | Soft exponent `P^β·V` | Rejected by the user (SEED-085/CONTEXT D-01) — narrow, position-dependent β window; every miscalibration fails toward the rejected greedy modal-move engine. Not re-litigated here; documented for completeness only. |
| Applying temperature at the orchestrator layer (this research's recommendation) | Applying temperature inside `maiaQueue.ts` (provider layer) | Provider-layer application would force the `(fen, elo)` cache key to also carry `T` (and would apply to BOTH sides indiscriminately unless `maiaQueue` also learned about `rootMover`, which it structurally shouldn't — it's a stateless FEN/ELO oracle). Orchestrator-layer application avoids both problems: the cache stays untouched, and `rootMover`/`side` are already local variables at the call site. |
| Continuous (unsnapped) temperature slider | Discrete step-snapped slider (mirroring `EloSelector`'s ladder-snap) | `EloSelector` snaps to `MAIA_ELO_LADDER` because Maia's *model* only has discrete trained rating rungs (snapping is a correctness requirement, not a UX choice). Temperature has no such discrete constraint — it is a continuous multiplier over an already-continuous probability distribution. A continuous (or finely-stepped, e.g. 0.01 in log-space) slider is more appropriate and does not need ladder-style snapping logic. |

**Installation:** None — no `npm install` needed for this phase.

**Version verification:** N/A — no new packages.

## Package Legitimacy Audit

Not applicable. This phase introduces zero new external packages (frontend `package.json` is untouched). No `npm view`/legitimacy check was run because there is nothing to check.

## Architecture Patterns

### System Architecture Diagram

```
                              /analysis page (Analysis.tsx)
                                        │
                    ┌───────────────────┼─────────────────────────┐
                    │                   │                         │
             selectedElo (existing)  NEW: temperature        maia.perElo (existing,
             from useMaiaEloDefault  session state (D-08)    raw Maia @ selectedElo,
                    │              default 1.0, no persist    powers the chart)
                    │                   │                         │
                    └─────────┬─────────┘                         │
                              ▼                                   │
                    useFlawChessEngine({ fen, enabled,             │
                        elo, policyTemperature })  ◄── NEW field   │
                              │                                    │
                              ▼                                    │
                    SearchBudget { maxNodes, elo:{w,b},             │
                        maxPlies, concurrency,                     │
                        policyTemperature? }  ◄── NEW field         │
                              │                                    │
                 ┌────────────┴─────────────┐                      │
                 ▼                          ▼                      │
          mctsSearch.ts              fallbackExpectimax.ts         │
        dispatchExpansion()              expandNode()              │
                 │                          │                      │
     providers.policy(fen, elo, side) ──────┘ (raw Maia,           │
                 │                            maiaQueue.ts          │
                 │                            cache UNCHANGED)      │
                 ▼                                                  │
     NEW: side === rootMover?                                      │
       yes → applyPolicyTemperature(rawPolicy, T)  (Thread A)       │
       no  → rawPolicy unchanged (opponent stays raw Maia, D-05)    │
                 │                                                  │
                 ▼                                                  │
        truncateAndRenormalize()  (existing, D-07: temp BEFORE this)│
                 │                                                  │
                 ▼                                                  │
     child.prior = renormalized (temp-adjusted at root, D-06)       │
                 │                                                  │
                 ▼                                                  │
        backupExpectation / backupRootMax  (UNCHANGED — V(X) math)  │
                 │                                                  │
                 ▼                                                  │
        treeCommon.ts: buildRankedLines(root, rootElo)  ◄── NEW param│
          for each root child:                                     │
            rankScore = min(1, child.prior / pRefForElo(rootElo))   │
                         * child.value        (Thread B)            │
          sort by rankScore desc (was: practicalScore desc)         │
          RankedLine.practicalScore = child.value  (UNCHANGED, D-04)│
                 │                                                  │
                 ▼                                                  │
        EngineSnapshot.rankedLines[]  (order now findability-aware) │
                 │                                                  │
     ┌───────────┼──────────────────────────────┐                  │
     ▼           ▼                              ▼                  │
FlawChessEngineLines   board arrows (top-2)   FlawChessAgreementVerdict
  (badge = V, unchanged)  (ARROW-01, unchanged      │
                            consumer, inherits              NEW: gate reads
                            new order for free)        maia.perElo + shownSans
                                                        (RAW Maia, D-12) ──┘
                                                        via new pure gate fn
                                                        in flawChessVerdict.ts
```

### Recommended Project Structure

No new directories. Two new pure modules alongside the existing `lib/engine/` files, plus targeted edits:

```
frontend/src/lib/engine/
├── findability.ts          # NEW — P_ref(ELO) curve + rankScore (Thread B)
├── policyTemperature.ts    # NEW — applyPolicyTemperature (Thread A)
├── treeCommon.ts           # EDIT — buildRankedLines gains rootElo param, uses findability.ts
├── mctsSearch.ts           # EDIT — dispatchExpansion applies temperature pre-truncation
├── fallbackExpectimax.ts   # EDIT — expandNode applies temperature pre-truncation (parity)
├── types.ts                # EDIT — SearchBudget gains optional policyTemperature field
└── __tests__/
    ├── findability.test.ts        # NEW — pure rankScore/pRefForElo unit tests + D-03 regressions
    └── policyTemperature.test.ts  # NEW — pure applyPolicyTemperature unit tests

frontend/src/lib/
└── flawChessVerdict.ts     # EDIT — new pure gate function + FINDABILITY_MARGIN constant

frontend/src/components/analysis/
├── TemperatureSelector.tsx        # NEW — mirrors EloSelector.tsx exactly
├── FlawChessAgreementVerdict.tsx  # EDIT — wire the new gate, add D-11 fallback prose variant
└── FlawChessEngineLines.tsx       # UNCHANGED (D-04 — badge still shows V)

frontend/src/hooks/
└── useFlawChessEngine.ts   # EDIT — new policyTemperature option, threaded into SearchBudget

frontend/src/pages/
└── Analysis.tsx            # EDIT — new temperature state, render TemperatureSelector in both
                             #        humanTab and desktop human column (mobile parity), pass
                             #        raw-Maia probability data into FlawChessAgreementVerdict
```

### Pattern 1: Layered pure transforms, never conflated (existing codebase convention — extend, don't break)

**What:** `select.ts`'s own header already states the governing convention for this whole file family: `truncateAndRenormalize` and `rootExplorationPriors` are "two DISTINCT functions layered in sequence, never conflated." This phase adds two more layers to the same pipeline (temperature, then findability), and must follow the identical discipline: each transform is a separate, independently-testable pure function; no function silently does two things.

**When to use:** Any time a new derived probability/score is introduced into the search pipeline.

**Example (the resulting full pipeline for one root-side policy() call, Thread A + B composed):**
```typescript
// Source: this phase's design, following the existing select.ts pattern
// (frontend/src/lib/engine/select.ts header comment)

// 1. Provider call (unchanged) — always raw Maia, never temperature-aware itself.
const rawPolicy = await providers.policy(node.fen, budget.elo[node.side], node.side);

// 2. NEW (Thread A): temperature reshapes the distribution, ONLY on the user's side,
//    ONLY before truncation (D-05, D-07). Short-circuits to a no-op at T=1 (ENGINE-07
//    determinism: today's behavior must be bit-identical when the slider is untouched).
const isUsersSide = sideMatchesMover(node.side, rootMover);
const temperature = budget.policyTemperature ?? DEFAULT_POLICY_TEMPERATURE;
const effectivePolicy =
  isUsersSide && temperature !== DEFAULT_POLICY_TEMPERATURE
    ? applyPolicyTemperature(rawPolicy, temperature)
    : rawPolicy;

// 3. Existing, unchanged: 0.9-mass truncation + renormalization.
const candidateMap = truncateAndRenormalize(effectivePolicy);
// candidateMap now feeds child.prior — which is EXACTLY what findability.ts's
// rankScore() will read at the root. No further wiring needed for composition.
```

**Source:** derived from `frontend/src/lib/engine/select.ts` (existing header pattern) + this phase's CONTEXT.md D-05/D-06/D-07.

### Pattern 2: Root-only ranking transform, kept OUT of the value/backup math

**What:** `backup.ts`'s own header states: "nothing in this file ever derives a weight from visits" — the codebase already has a strong convention of keeping the backup/value math (`V(X)`) structurally separate from selection/exploration machinery. D-01 extends this: `rankScore` must be computed **only** in the sort step of `buildRankedLines`, never inside `backupRootMax`/`backupExpectation`. This is what makes D-04 ("badge keeps showing V, ordering silently uses rankScore") trivially true by construction rather than something that needs separate enforcement.

**When to use:** Implementing `buildRankedLines`'s new sort.

**Example:**
```typescript
// Source: this phase's design, following treeCommon.ts's existing buildRankedLines shape
// (frontend/src/lib/engine/treeCommon.ts:144-161)

function buildRankedLines<N extends SearchTreeNode<N>>(root: N, rootElo: number): RankedLine[] {
  const pRef = pRefForElo(rootElo); // findability.ts — pure, O(1) anchor lookup+interpolation
  const lines: (RankedLine & { rankScore: number })[] = [];
  for (const child of root.children.values()) {
    if (child.uci === null) continue;
    lines.push({
      rootMove: child.uci,
      practicalScore: child.value, // UNCHANGED — still V(X), D-04
      objectiveEvalCp: child.objectiveEvalCp,
      modalPath: buildModalPath(child),
      visits: child.visits,
      // rankScore is a SORT-ONLY local field — never assigned onto the public
      // RankedLine the UI consumes. child.prior is already temperature-adjusted
      // if Thread A applied (Pattern 1) — no extra plumbing needed here (D-06).
      rankScore: rankScore(child.prior, pRef, child.value),
    });
  }
  lines.sort((a, b) => {
    if (b.rankScore !== a.rankScore) return b.rankScore - a.rankScore;
    return a.rootMove < b.rootMove ? -1 : a.rootMove > b.rootMove ? 1 : 0; // unchanged tie-break
  });
  // Strip the sort-only field before returning the public shape.
  return lines.map(({ rankScore: _rankScore, ...line }) => line);
}
```

**Source:** derived from `frontend/src/lib/engine/treeCommon.ts:144-161` (existing `buildRankedLines`) + CONTEXT.md D-01/D-04.

### Pattern 3: Verdict gate reads a structurally separate data source (no coupling risk)

**What:** `flawChessVerdict.ts`'s header already states it is "pure, worker-free, chess.js-free." `RankedLine` (the FlawChess side's data) has no `prior` field at all — it is architecturally impossible for the verdict gate to accidentally read the temperature-adjusted internal probability, because that value never leaves the search core. D-12 ("gate reads raw Maia") is therefore satisfiable by construction: wire the gate to the SAME `maia.perElo`/`selectCandidatesByMass` data `Analysis.tsx` already computes for the chart, passed down as new props.

**When to use:** Wiring D-10/D-11/D-12.

**Example:**
```typescript
// Source: this phase's design, following flawChessVerdict.ts's existing pure-function style
// (frontend/src/lib/flawChessVerdict.ts)

/** Findability-claim gate (D-10). Both probabilities MUST be raw Maia at the selected
 *  ELO (D-12) — never the search-internal temperature-adjusted prior, which this module
 *  cannot even see (RankedLine has no prior field). */
export const FINDABILITY_MARGIN = 0.05; // Claude's discretion (D-10) — needs UAT tuning,
// same order of magnitude as INACCURACY_DROP (0.05) in generated/flawThresholds.ts.

export function computeFindabilityGate(
  pYouFc: number | null,
  pYouSf: number | null,
  fcInPlottedSet: boolean,
): boolean {
  if (pYouFc == null || pYouSf == null) return false;
  return fcInPlottedSet && pYouFc > pYouSf + FINDABILITY_MARGIN;
}
```
```tsx
// Caller (FlawChessAgreementVerdict.tsx) resolves SAN + looks up raw probabilities —
// chess.js/SAN conversion stays OUT of flawChessVerdict.ts per its own header constraint.
const rawProbBySan = /* passed down from Analysis.tsx: nearestByElo(maia.perElo, elo)?.moveProbabilities ?? {} */;
const findabilityOk = computeFindabilityGate(
  fcSan ? (rawProbBySan[fcSan] ?? null) : null,
  sfSan ? (rawProbBySan[sfSan] ?? null) : null,
  fcSan ? shownSans.includes(fcSan) : false, // shownSans = selectCandidatesByMass output (D-10)
);
```

**Source:** derived from `frontend/src/lib/flawChessVerdict.ts` + `frontend/src/lib/moveQuality.ts:129-152` (`selectCandidatesByMass`) + `frontend/src/pages/Analysis.tsx:685-688` (`shownSans` already computed there).

### Anti-Patterns to Avoid

- **Applying temperature inside `maiaQueue.ts`:** Forces the `(fen, elo)` cache key to grow a third dimension, and requires the provider (a stateless FEN/ELO oracle) to somehow learn "is this the user's side" — a concept that belongs to the orchestrator (`rootMover`), not the provider. Apply at the orchestrator layer instead (Pattern 1).
- **Storing `rankScore` on `RankedLine`:** Tempts a future UI change to render it, silently violating D-04 ("badge keeps showing V"). Keep it as a sort-local ephemeral value (Pattern 2).
- **Computing `pRefForElo` per-child inside the sort loop from scratch each time:** It only depends on `rootElo`, a single scalar per search — compute once per `buildRankedLines` call, not once per child (cheap either way, but the once-per-call form makes the "one P_ref for the whole ranking" invariant visible in the code).
- **Letting the verdict gate read `flawChessEngine`'s internal state:** The gate must never import anything from `lib/engine/` besides `RankedLine`'s type — it is a chart-consistency check, not a search-internals check (D-12's entire point).
- **A both-sides temperature knob:** Explicitly rejected (D-05) — flattening the opponent's policy makes them *more* fallible, which makes sharp/risky lines look *better* for the player, the opposite of the intended effect. The temperature gate must be strictly `side === rootMover`.
- **Re-deriving the Maia rung lookup independently in two places:** `Analysis.tsx` already calls `nearestByElo(maia.perElo, selectedElo)` (via `moveQuality.ts`) for the chart/`shownSans`. Compute the raw-probability-by-SAN map **once** in `Analysis.tsx` and pass it down, rather than having `FlawChessAgreementVerdict.tsx` call `nearestByElo` a second time — avoids any risk of the gate and the chart disagreeing at an ELO-rung boundary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Temperature-scaling a probability distribution | A custom re-derivation from first principles, or re-deriving Maia's pre-softmax logits | The standard `p_i^(1/T)` renormalized transform (mathematically equivalent to `softmax(logits/T)` when the input `p_i` already came from a softmax, which Maia's policy output does — see `maskAndSoftmax` in `maiaEncoding.ts`) | This is the textbook "softmax temperature" technique used throughout ML/RL (well-known, not project-specific); no library needed, ~5 lines of pure math, but don't invent a different formula — the existing `p^(1/T)` form is the one CONTEXT.md's Claude's-discretion note already names as the expected shape ("standard `p^(1/T)` renormalized or equivalent"). |
| Log-symmetric slider mapping | A bespoke non-linear Radix Slider fork | Keep the underlying `<Slider>` linear (as today), and convert `T = 2^s` / `s = log2(T)` at the component boundary, exactly the way `EloSelector.tsx` already converts ladder index ↔ value | The existing `Slider` primitive only understands a linear numeric range; every log-scale UI slider in existence solves this the same way (map slider position through `2^x`), no new primitive or library needed. |
| Root-candidate hard cap under extreme flattening | A new general-purpose "top-N" utility | A tiny inline `.slice()` after sorting candidates by probability descending, applied ONLY at the root branch of `dispatchExpansion`/`expandNode` (mirrors the existing pattern already in `moveQuality.ts`'s `CANDIDATE_HARD_CAP` / `.slice(0, CANDIDATE_HARD_CAP)`) | `moveQuality.ts` already solved this exact "cap a sorted-by-probability list" problem for the chart; reuse the pattern, not the constant (`select.ts`'s own header explicitly forbids importing `moveQuality.ts`'s `CANDIDATE_HARD_CAP` into the search core — they are deliberately independent tunables for different concerns). |

**Key insight:** Every piece of this phase has a same-file or sibling-file precedent already in the codebase (`select.ts`'s layered-transform discipline, `moveQuality.ts`'s mass-cutoff-then-cap pattern, `EloSelector.tsx`'s slider-value-mapping pattern, `flawChessVerdict.ts`'s pure-gate-function pattern). The main risk in this phase is not "what to build" but "which existing pattern to copy for which piece" — get that mapping right and the implementation is close to mechanical.

## Common Pitfalls

### Pitfall 1: Breaking ENGINE-07 determinism at the default temperature (T=1)

**What goes wrong:** If `applyPolicyTemperature` is called unconditionally even when `temperature === 1`, floating-point round-trip through `p^(1/1)` renormalized could introduce tiny drift vs. the untouched `rawPolicy`, silently changing search output for every user who never touches the slider (i.e., everyone, today).

**Why it happens:** `x ** 1` is mathematically identity but the renormalization division (`p / total`) can still introduce a rounding difference vs. skipping the transform entirely, especially compounded across `POLICY_MASS_THRESHOLD`'s tie-break-sensitive truncation.

**How to avoid:** Short-circuit: `temperature === DEFAULT_POLICY_TEMPERATURE ? rawPolicy : applyPolicyTemperature(rawPolicy, temperature)` at both call sites (Pattern 1's example already does this). This also has a performance benefit (skips work for the overwhelming majority of searches where the slider is untouched).

**Warning signs:** Any existing `mctsSearch.test.ts`/`fallbackExpectimax.test.ts` snapshot fixture that doesn't pass `policyTemperature` starts failing after this phase's changes — that's a signal the short-circuit isn't wired correctly (those tests construct `SearchBudget` without the new field, relying on `?? DEFAULT_POLICY_TEMPERATURE` defaulting AND that default being a true no-op).

### Pitfall 2: Applying temperature to the wrong side (breaking D-05)

**What goes wrong:** `node.side` is `'w'|'b'` (`Side`), `rootMover` is `'white'|'black'` (`MoverColor`) — two different literal-type domains already used side-by-side in this codebase. A naive `node.side === rootMover` comparison is a TypeScript type error (good — it'll be caught), but a hand-rolled string comparison (`node.side === 'w' ? 'white' : 'black') === rootMover`) written slightly wrong (e.g. comparing `node.side` to `fenSide(rootFen)` instead of to `rootMover`, or flipping the ternary) silently applies temperature to the opponent instead of the user, or to both.

**Why it happens:** No existing helper converts between `Side` and `MoverColor` in this codebase (confirmed via search — `fenSide()` and `sideToMoveFromFen()` are both independent FEN parsers, not converters of each other's output).

**How to avoid:** Add one small, explicitly-tested helper (e.g. `sideMatchesMover(side: Side, mover: MoverColor): boolean` in `treeCommon.ts`, alongside `fenSide`) and reuse it at both call sites. Unit-test it directly (`sideMatchesMover('w','white') === true`, `sideMatchesMover('b','white') === false`, etc.) rather than trusting inline logic at two call sites to stay in sync.

**Warning signs:** A regression test where the opponent's move distribution visibly flattens/sharpens when the temperature slider moves (should never happen per D-05) — write an explicit test asserting the opponent-side `policy()` call always receives the pre-temperature `rawPolicy` untouched.

### Pitfall 3: `fallbackExpectimax.ts` drifting from `mctsSearch.ts` (breaking D-06 parity)

**What goes wrong:** Temperature is applied in `mctsSearch.ts`'s `dispatchExpansion` but forgotten in `fallbackExpectimax.ts`'s `expandNode` — the two `SearchRunner` implementations silently diverge, reopening exactly the risk `treeCommon.ts`'s own header warns about ("practicalScore semantics therefore cannot drift between the runners (D-06): both consume this single implementation").

**Why it happens:** `fallbackExpectimax.ts` is the guardrail path, exercised far less in manual testing than the primary `mctsSearch.ts` (it's a drop-in fallback, not the default runner) — it's easy to edit one file, verify visually on `/analysis` (which uses `mctsSearch`), and ship without realizing the second implementation needs the identical change.

**How to avoid:** `fallbackExpectimax.ts`'s `expandNode` already has `rootMover` in scope (unlike `mctsSearch.ts`'s `dispatchExpansion`, which needs a new parameter threaded in) — so the temperature-gating logic is actually *simpler* to add there. Add both edits in the same task/commit, and mirror the D-03 regression tests across both `mctsSearch.test.ts` and `fallbackExpectimax.test.ts` (or better: put the pure temperature/findability logic in its own test file so both orchestrators are proven to call the SAME underlying function, rather than duplicating assertions).

**Warning signs:** `fallbackExpectimax.test.ts` has no temperature-related test after the change lands.

### Pitfall 4: Narrow `P_ref(ELO)` calibration window (same failure shape as the rejected β approach)

**What goes wrong:** D-01's own rationale documents that the sibling `P^β·V` approach was rejected partly because "the workable β window is narrow and position-dependent (in the 600-ELO case, β ∈ ~(0.15, 0.25))." The chosen saturating-floor approach is structurally safer (it cannot boost the modal move above its own V), but `P_ref(600)` still has a real, calculable window: it must be `> P(Nb5)=0.05` (so Nb5's factor is meaningfully `<1`, i.e. genuinely suppressed) and small enough that `P(Qxf2)=0.09`'s factor times `V(Qxf2)` still beats `V(Rxf2)` (Rxf2 isn't suppressed at all if `P(Rxf2)=0.57 > P_ref`, so it relies entirely on its own lower `V` to lose — which it should, since it's classified "Mistake" vs. Qxf2's "Good", but this has NOT been verified numerically in this research session).

**Why it happens:** The actual `V(X)` values for Nb5/Qxf2/Rxf2 at the real 600-ELO position are not available in this research session (no FEN was recovered from the referenced screenshots) — see Open Questions.

**How to avoid:** Do not hard-code a single "obviously correct" `P_ref(600)` value and assume it works. Recover the real FEN(s) behind the three D-03 cases (ask the user, or reconstruct from the SEED-085 doc's move list: 600-ELO position where Nb5/Qxf2/Rxf2 are candidates; 1000-ELO position where Qc7/O-O/Qf6/g5/b5 are the chart's candidates and Qb8 is the tail move) and run the actual search against them during implementation to empirically verify all three D-03 regressions pass with the chosen anchor curve — treat the anchor values as a hypothesis to validate, not a fact to encode.

**Warning signs:** A `findability.test.ts` that only tests `pRefForElo`'s shape (monotonic decrease, endpoints) but never runs the full three-case D-03 regression against real or realistically-reconstructed P/V data.

### Pitfall 5: Verdict gate and chart disagreeing at an ELO-rung boundary

**What goes wrong:** The chart's `shownSans` is computed via `nearestByElo(maia.perElo, selectedElo)` — a snap to the closest 100-ELO rung. If the verdict gate's raw-probability lookup independently re-implements this snap (rather than reusing the exact same resolved rung/map), a boundary case (e.g. `selectedElo = 1050`, equidistant-ish between 1000 and 1100 rungs) could theoretically resolve to different rungs in the two places if the lookups aren't literally sharing one computed value.

**Why it happens:** Two call sites computing "the same" derived value independently is a classic source of drift, and this codebase has a documented precedent for exactly this bug class (Phase 151.1's chart vs. engine-card "best move" self-contradiction bug, referenced in `moveQuality.ts`'s own header: "two independent Stockfish searches broke near-ties differently... yielding a self-contradictory tooltip").

**How to avoid:** Compute the raw-probability-by-SAN map (and `shownSans`) exactly once in `Analysis.tsx`, pass both down as props to `FlawChessAgreementVerdict.tsx` — do not give the verdict component its own `nearestByElo` call.

**Warning signs:** `FlawChessAgreementVerdict.tsx` importing `nearestByElo` or `maia.perElo` directly instead of receiving pre-resolved data as props.

### Pitfall 6: Extreme flattening (high T) blowing up the root candidate set and diluting the fixed visit budget

**What goes wrong:** `truncateAndRenormalize`'s 0.9-mass cutoff currently keeps a small number of moves at T=1 (a few, since Maia's policy is normally peaked). At T=2.0 (max slider value), the flattened distribution could require dozens of moves to reach 90% cumulative mass. `FLAWCHESS_ENGINE_MAX_NODES = 400` then spreads across a much wider root branching factor, degrading every line's search depth/quality — including the eventual winner's.

**Why it happens:** `truncateAndRenormalize`'s mass-based cutoff has no candidate-count ceiling by design (D-11 in `select.ts`'s own docstring: "No hard cap... unlike moveQuality.ts's display-oriented CANDIDATE_HARD_CAP") — this was a deliberate, correct choice for the T=1 case, but T can now push the policy arbitrarily flat.

**How to avoid:** Per CONTEXT.md D-07's own discretion note, add a named hard cap applied ONLY at the root, ONLY after temperature+truncation (not inside `truncateAndRenormalize` itself, which stays general-purpose and untouched — see Anti-Patterns). Pick a cap generous enough not to interfere at T≈1 (e.g. comfortably above the typical T=1 candidate count) but bounded enough to protect the visit budget at T=2.0.

**Warning signs:** A test with a synthetic uniform-ish policy (simulating extreme temperature) producing a root with 20+ children and visibly shallow per-line visit counts in `mctsSearch.test.ts`.

### Pitfall 7: Log-slider center drift (T should be exactly 1.0 at the visual midpoint, not 0.9999...)

**What goes wrong:** Converting slider position `s ∈ [-1, 1]` to `T = 2^s` and back is exact at the endpoints and center in real-number math, but a naive implementation using the wrong min/max/step arithmetic (e.g. deriving the exponent range from `0.5`/`2.0` via `Math.log(...)` with a different base than the inverse `2 ** s`) can leave the visual center a few floating-point ULPs off `1.0`, which then fails the Pitfall 1 short-circuit (`temperature === DEFAULT_POLICY_TEMPERATURE`) at the exact position users are most likely to leave the slider (the default).

**How to avoid:** Use `Math.log2`/`2 **` consistently (matching bases), and consider snapping the slider's own default/reset value to the literal constant `1` (not a computed `2 ** 0`, though that IS exactly 1 in IEEE 754 — verify with a unit test) rather than relying on slider-drag arithmetic to reproduce it after any rounding.

**Warning signs:** A test asserting `temperature === 1` (strict equality, not `toBeCloseTo`) at the slider's default/center position fails.

## Code Examples

### Findability rank score (Thread B core function)

```typescript
// Source: this phase's design (CONTEXT.md D-01), new file frontend/src/lib/engine/findability.ts

/**
 * findability — root-only ranking weight that folds the root player's OWN
 * move-probability (P_you) back into the ranking (D-01), without touching
 * V(X) (the per-move practical score) or the backup/value math at all.
 *
 * `rankScore` is a SATURATING linear factor: any move at or above P_ref gets
 * factor 1 (full V, unmodified) — the modal/highest-prior move can therefore
 * never be boosted above its own V. This is what makes the greedy "rank by
 * P·V" failure mode (rejected in SEED-085) structurally impossible here,
 * rather than merely avoided by careful calibration.
 */

/** Anchor curve for P_ref(ELO): aggressive suppression at low ELO (findability
 *  matters a lot), near-off at the top of the Maia ladder (findability barely
 *  matters — most legal top moves are "findable" to a 2600). ASSUMED starting
 *  point — MUST be validated against the three D-03 regression cases with real
 *  or realistically-reconstructed P/V data before shipping (see Pitfall 4 /
 *  Open Questions — this exact curve was not empirically verified this session). */
const P_REF_ANCHORS: readonly [elo: number, pRef: number][] = [
  [600, 0.12],
  [1000, 0.08],
  [1400, 0.05],
  [1800, 0.03],
  [2200, 0.015],
  [2600, 0.005],
];

/** Linear interpolation between P_REF_ANCHORS, clamped outside the range. */
export function pRefForElo(elo: number): number {
  const first = P_REF_ANCHORS[0];
  const last = P_REF_ANCHORS[P_REF_ANCHORS.length - 1];
  if (!first || !last) return 0; // defensive; P_REF_ANCHORS is a non-empty const
  if (elo <= first[0]) return first[1];
  if (elo >= last[0]) return last[1];
  for (let i = 0; i < P_REF_ANCHORS.length - 1; i += 1) {
    const lo = P_REF_ANCHORS[i];
    const hi = P_REF_ANCHORS[i + 1];
    if (!lo || !hi) continue; // noUncheckedIndexedAccess
    if (elo >= lo[0] && elo <= hi[0]) {
      const t = (elo - lo[0]) / (hi[0] - lo[0]);
      return lo[1] + t * (hi[1] - lo[1]);
    }
  }
  return last[1]; // unreachable given the guards above; defensive
}

/** D-01's saturating findability factor: min(1, P_you/P_ref) · V(X), β=1 (locked). */
export function rankScore(pYou: number, pRef: number, value: number): number {
  if (pRef <= 0) return value; // degenerate guard, mirrors backup.ts's totalPrior===0 convention
  return Math.min(1, pYou / pRef) * value;
}
```

### Policy temperature transform (Thread A core function)

```typescript
// Source: this phase's design (CONTEXT.md D-06/D-07), new file
// frontend/src/lib/engine/policyTemperature.ts. Standard softmax-temperature
// technique (well-known ML/RL method, not sourced from a specific library).

/** T=1 is a true no-op (today's behavior) — callers MUST short-circuit at this
 *  value rather than routing through the transform (Pitfall 1, ENGINE-07). */
export const DEFAULT_POLICY_TEMPERATURE = 1;

/**
 * Reshapes an already-softmaxed probability distribution as if the
 * temperature had been applied before the softmax: p_i^(1/T) renormalized.
 * T>1 flattens (more mass on tail moves — more human fallibility modeled);
 * T<1 sharpens toward the top move (converges toward Stockfish-like play).
 * Valid because Maia's policy() output is itself a softmax over move logits
 * (maskAndSoftmax, @/lib/maiaEncoding) — p_i^(1/T) / Σ p_j^(1/T) is
 * mathematically equivalent to softmax(logits/T) for such inputs.
 */
export function applyPolicyTemperature(
  policy: Record<string, number>,
  temperature: number,
): Record<string, number> {
  const exponent = 1 / temperature;
  const reshaped = Object.entries(policy).map(([uci, p]) => [uci, p ** exponent] as const);
  const total = reshaped.reduce((sum, [, p]) => sum + p, 0);
  const result: Record<string, number> = {};
  for (const [uci, p] of reshaped) {
    result[uci] = total > 0 ? p / total : 0;
  }
  return result;
}
```

### Log-symmetric slider value mapping (D-08)

```typescript
// Source: this phase's design, mirroring frontend/src/components/analysis/EloSelector.tsx's
// value-mapping pattern (ladder index <-> displayed value), adapted for a continuous log scale.

export const TEMPERATURE_MIN = 0.5;
export const TEMPERATURE_MAX = 2.0;
export const TEMPERATURE_DEFAULT = 1.0;

const LOG2_MIN = Math.log2(TEMPERATURE_MIN); // -1
const LOG2_MAX = Math.log2(TEMPERATURE_MAX); // 1

/** Radix Slider stays linear internally; the component converts at its boundary. */
export function sliderPositionToTemperature(position: number): number {
  return 2 ** position;
}
export function temperatureToSliderPosition(temperature: number): number {
  return Math.log2(temperature);
}
```

## Runtime State Inventory

Not applicable — this is not a rename/refactor/migration phase. No stored data, live service config, OS-registered state, secrets, or build artifacts are touched. Confirmed: no database, no persisted settings (D-08 explicitly locks session-only state, no localStorage/URL param), no backend involvement whatsoever (this is a pure frontend TypeScript change).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `P_REF_ANCHORS` starting values (600→0.12, 1000→0.08, ..., 2600→0.005) | Code Examples / Pitfall 4 | If wrong, either Nb5 still tops the 600-ELO ranking (fix doesn't work) or Qxf2 gets suppressed below Rxf2 (overshoot into the rejected greedy-modal failure mode). MUST be validated against real D-03 regression data during implementation, not assumed correct from this research alone. |
| A2 | `FINDABILITY_MARGIN = 0.05` (D-10 gate) | Architecture Patterns Pattern 3 / Code Examples | If too small, the findability claim fires on marginal cases and risks contradicting the chart again (the exact defect this phase fixes); if too large, the "far easier to find and play" claim rarely fires even when true, over-triggering the D-11 fallback. Needs UAT tuning like `SHARP_DROP_THRESHOLD`/`NEARLY_SAME_EVAL_CP` were. |
| A3 | Temperature applied at the orchestrator layer (not `maiaQueue.ts`) is the correct implementation point | Summary / Architecture Patterns Pattern 1 | Low risk — this is a structural/architectural recommendation derived directly from D-05/D-06/D-07's constraints (provider layer cannot know `rootMover`), not a numeric guess. If the planner disagrees, the alternative (provider-layer + cache-key change) is documented as a rejected alternative with reasons, not silently omitted. |
| A4 | Named hard cap value for root candidates under extreme flattening (Pitfall 6) — no specific number recommended | Common Pitfalls Pitfall 6 | Left fully to Claude's discretion per CONTEXT.md; this research did not propose a number because it depends on `FLAWCHESS_ENGINE_MAX_NODES` (400) and desired minimum per-line visit depth, which is a product/perf tradeoff outside this research's scope. |
| A5 | The `p^(1/T)` renormalized formula is the correct temperature-scaling technique for an already-softmaxed distribution | Don't Hand-Roll / Code Examples | Low risk — this is standard, well-documented ML technique (softmax temperature scaling), and CONTEXT.md's own Claude's-discretion note names this exact form as the expected shape ("standard `p^(1/T)` renormalized or equivalent"). |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **What are the exact FENs and real P/V numbers behind the three D-03 regression cases (Nb5/Qxf2/Rxf2 @600; Qb8 @1000)?**
   - What we know: SEED-085's doc names the moves, approximate Maia probabilities (5%, 9%, 57%), and quality labels (Best, Good, Mistake), plus the 1000-ELO chart's plotted candidate set (Qc7/O-O/Qf6/g5/b5).
   - What's unclear: The actual `V(X)` (practical score) values for each candidate, and the exact FEN — these live only in screenshots referenced in the CONTEXT.md/SEED-085 doc, not recoverable from this research session (no image/screenshot access, no FEN string given in any planning artifact read).
   - Recommendation: The planner/executor should ask the user directly for the FEN(s) (or reconstruct them from a live `/analysis` session at the stated ELOs, since the engine is deterministic per ENGINE-07) before finalizing `P_REF_ANCHORS`, and write the three D-03 cases as literal regression tests against that real data — not synthetic stand-ins that only approximate the qualitative relationship.

2. **Should the root candidate hard cap (Pitfall 6 / D-07 discretion) be a fixed count or scale with `budget.maxNodes`?**
   - What we know: `moveQuality.ts` uses a fixed `CANDIDATE_HARD_CAP = 5` for the (unrelated) chart display concern; the search's own `FLAWCHESS_ENGINE_MAX_NODES = 400` is fixed today.
   - What's unclear: Whether a fixed cap (e.g. 15-20) is generous enough across all realistic temperature values, or whether it should be derived from `budget.maxNodes` (e.g. "don't let the root candidate count exceed maxNodes/20" or similar) to stay proportionate if the node budget changes later (per `useFlawChessEngine.ts`'s own comment: "Tunable — revisit after SC4 real-device mobile-memory UAT").
   - Recommendation: Start with a fixed named constant (simpler, matches the existing `moveQuality.ts` precedent); only make it budget-relative if empirical testing at T=2.0 shows visit-depth degradation is unacceptable with a fixed cap.

3. **Does the D-09 "numeric T value shown subtly" language imply a specific display format (e.g. "T=1.4" vs. "1.4x")?**
   - What we know: D-09 says the numeric value should be shown "subtly" (not the primary label — that's "Sharper"/"More human"), mirroring `EloSelector`'s numeric ELO readout pattern (`text-sm font-medium tabular-nums`, right-aligned).
   - What's unclear: Exact copy/format — left as "Claude's discretion" per CONTEXT.md, but not resolved here since it's a pure UX-copy decision with no technical dependency.
   - Recommendation: Follow `EloSelector.tsx`'s exact numeric-label styling (`text-sm font-medium tabular-nums`) for consistency; format as `T.T` to one decimal place (e.g. "0.7", "1.4") since the range 0.5-2.0 doesn't need more precision, and avoid a raw "T=" prefix per D-09's anti-jargon instruction.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest (already configured via `frontend/vite.config.ts`'s `test` field; no separate `vitest.config.ts`) |
| Config file | `frontend/vite.config.ts` |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/__tests__/findability.test.ts src/lib/engine/__tests__/policyTemperature.test.ts` |
| Full suite command | `cd frontend && npm test -- --run` (per CLAUDE.md's pre-merge gate: `npm run lint && npm test -- --run`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEED-085 (Thread B, D-01) | `rankScore` saturates at factor 1 for any `pYou >= pRef`; scales linearly below | unit | `npx vitest run src/lib/engine/__tests__/findability.test.ts` | ❌ Wave 0 |
| SEED-085 (Thread B, D-02/D-03) | The three named regression cases (Nb5 suppressed @600, Qxf2 wins @600, Qb8 suppressed @1000) pass end-to-end through `buildRankedLines` | unit/regression | `npx vitest run src/lib/engine/__tests__/findability.test.ts` (or a dedicated `treeCommon.test.ts` if extracted) | ❌ Wave 0 |
| SEED-085 (Thread B, D-04) | `RankedLine.practicalScore` is unchanged (still `V(X)`) even when sort order changes | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` (extend existing) | ✅ existing file, extend |
| SEED-085 (Thread A, D-05) | Temperature never affects the opponent-side `policy()` call's input | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts` (extend existing) | ✅ existing files, extend |
| SEED-085 (Thread A, D-06) | Temperature-adjusted `child.prior` feeds BOTH the search AND the findability ranking (composition) | integration (within existing mctsSearch/fallbackExpectimax suites) | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` (extend existing) | ✅ existing file, extend |
| SEED-085 (Thread A, D-07) | Temperature applied before `truncateAndRenormalize`; a root hard cap guards extreme flattening | unit | `npx vitest run src/lib/engine/__tests__/policyTemperature.test.ts` + extend `mctsSearch.test.ts` | ❌ Wave 0 (new file) |
| SEED-085 (D-08 slider) | Log-symmetric mapping: position 0 ↔ T=1.0 exactly; position ±1 ↔ T=2.0/0.5 | unit | `npx vitest run src/components/analysis/__tests__/TemperatureSelector.test.tsx` (new, or co-located `.test.tsx`) | ❌ Wave 0 |
| SEED-085 (D-10/D-11/D-12 verdict gate) | Gate fires only when raw-Maia margin exceeded AND pick is in the plotted set; falls back to D-11 prose otherwise; never reads temperature-adjusted data | unit | `npx vitest run src/lib/flawChessVerdict.test.ts` (extend existing) | ✅ existing file, extend |

### Sampling Rate

- **Per task commit:** the scoped quick-run command for whichever file(s) that task touched.
- **Per wave merge:** `cd frontend && npm test -- --run` (full frontend suite) + `npx tsc -b` (per CLAUDE.md's "run tsc -b before integrating frontend" rule — property-access/type changes across `SearchBudget`/`RankedLine` consumers are exactly the class of bug `npm run lint`/`npm test` alone won't catch, since esbuild strips types).
- **Phase gate:** Full pre-merge gate before `/gsd-verify-work` — `uv run ...` backend commands are irrelevant here (frontend-only phase) but `( cd frontend && npm run lint && npm test -- --run )` plus `npx tsc -b` per CLAUDE.md.

### Wave 0 Gaps

- [ ] `frontend/src/lib/engine/__tests__/findability.test.ts` — covers `pRefForElo`, `rankScore`, and the three D-03 regression cases.
- [ ] `frontend/src/lib/engine/__tests__/policyTemperature.test.ts` — covers `applyPolicyTemperature` (flattening/sharpening direction, T=1 identity, renormalization sums to 1).
- [ ] `frontend/src/components/analysis/__tests__/TemperatureSelector.test.tsx` (or co-located) — covers the log-slider position↔temperature mapping, especially the T=1.0-at-center exactness (Pitfall 7).
- [ ] Extend `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` — add cases proving: (a) `budget.policyTemperature` omitted behaves identically to today (regression-proof for existing fixtures), (b) temperature only reaches the root-mover's-side `policy()` input, (c) `buildRankedLines`'s new sort order for a synthetic fixture where a low-prior/high-value child would have won under the old sort but loses under the new one.
- [ ] Extend `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts` — mirror the same temperature/findability cases (Pitfall 3 parity requirement).
- [ ] Extend `frontend/src/lib/flawChessVerdict.test.ts` — add `computeFindabilityGate` cases (both-conditions-true fires; either-condition-false falls back; `null` inputs default to false, never throw).
- [ ] No new test framework install needed — Vitest is already configured and used throughout `frontend/src`.

## Security Domain

Not applicable in the ASVS sense — this phase has no authentication, session, access-control, external input-validation, or cryptography surface. It is a pure client-side ranking-algorithm and UI-slider change with no new data flows crossing a trust boundary (no new fetch, no new user input beyond a slider whose value only affects local in-browser search math). `security_enforcement` need not be separately disabled in config for this phase — there is simply nothing in scope that any ASVS category governs.

## Sources

### Primary (HIGH confidence — direct codebase reads, this session)

- `frontend/src/lib/engine/select.ts` — `POLICY_MASS_THRESHOLD`, `ROOT_PRIOR_FLOOR`, `truncateAndRenormalize`, `rootExplorationPriors`, `selectChild` — the layered-transform convention this phase extends.
- `frontend/src/lib/engine/treeCommon.ts` — `buildRankedLines` (the exact function D-01 modifies), `SearchTreeNode`, `recomputeValue`, `fenSide`.
- `frontend/src/lib/engine/backup.ts` — `backupExpectation`/`backupRootMax` — confirms V(X) math is fully separate from any weighting-by-visits/probability-as-a-selection-criterion concern.
- `frontend/src/lib/engine/types.ts` — `SearchBudget`, `EngineProviders`, `RankedLine`, `EngineSnapshot` — the interfaces this phase extends.
- `frontend/src/lib/engine/mctsSearch.ts` — `dispatchExpansion`, `applyExpansion`, the main search loop — Thread A's primary insertion point.
- `frontend/src/lib/engine/fallbackExpectimax.ts` — `expandNode` — Thread A's parity-required second insertion point.
- `frontend/src/lib/engine/maiaQueue.ts` — confirms the `(fen, elo)` cache shape and why it should stay untouched by this phase.
- `frontend/src/hooks/useFlawChessEngine.ts` — confirms `SearchBudget` construction site, existing `elo` threading pattern to mirror for `policyTemperature`.
- `frontend/src/hooks/useMaiaEloDefault.ts` — the session-only-state pattern D-08 explicitly references (though the new hook needed is simpler — no async re-derivation).
- `frontend/src/components/analysis/EloSelector.tsx` — the exact component shape/styling/testid pattern the new temperature slider must mirror, plus its ladder-value-mapping technique (adapted to log-scale).
- `frontend/src/components/ui/slider.tsx` — the underlying Radix `Slider` primitive (linear only — confirms the log-mapping must happen at the component boundary).
- `frontend/src/lib/moveQuality.ts` — `selectCandidatesByMass`, `nearestByElo`, `CANDIDATE_HARD_CAP`, `CUMULATIVE_MASS_THRESHOLD` — the chart-display precedent for both the "cap after mass-cutoff" pattern (Thread A's root-cap discretion) and D-10's "plotted set" data source.
- `frontend/src/lib/flawChessVerdict.ts` — `computeFlawChessVerdict`, `SHARP_DROP_THRESHOLD`, `NEARLY_SAME_EVAL_CP` — the pure-gate-function convention and constant-naming/scale precedent for `FINDABILITY_MARGIN`.
- `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` — the verdict prose component D-10/D-11 modify; confirms `uciToSan` already lives here (chess.js-in-the-component, not in `flawChessVerdict.ts`).
- `frontend/src/components/analysis/FlawChessEngineLines.tsx` — confirms the badge renders `practicalScore` directly (D-04's "unchanged" claim verified against actual render code).
- `frontend/src/pages/Analysis.tsx` (lines ~480-760, ~1550-1830) — confirms `selectedElo`/`shownSans`/`eloSelector` placement, the desktop/mobile dual-render sites the new slider must mirror, and that `reconciledRankedLines` (Phase 158) is a `.map()` over `flawChessEngine.rankedLines` that preserves order — the single seam proof (sort-order fix alone propagates correctly to arrows/badges/verdict without further changes).
- `frontend/src/generated/flawThresholds.ts` — `INACCURACY_DROP`/`MISTAKE_DROP`/`BLUNDER_DROP` — scale reference for the new `FINDABILITY_MARGIN` constant.
- `frontend/src/lib/maiaEncoding.ts` — `MAIA_ELO_LADDER` (600-2600, step 100) — confirms the ELO domain `pRefForElo` must span.
- `.planning/seeds/SEED-085-engine-policy-temperature-and-low-elo-realism.md` — the full design doc, three-target table, rejected alternatives.
- `.planning/phases/159-.../159-CONTEXT.md` — all locked decisions (D-01 through D-12) and discretion areas.
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — confirms no new v2.0 requirement IDs are minted for this phase; SEED-085 is the sole traceability anchor.
- `frontend/src/lib/engine/__tests__/select.test.ts` — existing test-style precedent (fixture shape, assertion style) for the new `findability.test.ts`/`policyTemperature.test.ts`.
- `frontend/vite.config.ts` — confirms Vitest config location, no separate `vitest.config.ts`.
- `CLAUDE.md` (project root) — coding guidelines, mobile-parity rule, `data-testid` rules, pre-merge gate commands.

### Secondary (MEDIUM confidence)

- `docs/flawchess-engine-explained-2026-07-06.md` (§1-2 read this session) — plain-language framing of the engine's Maia/Stockfish asymmetric-query design; corroborates but does not add new technical constraints beyond what CONTEXT.md/SEED-085 already state.

### Tertiary (LOW confidence — flagged, needs validation)

- The `P_REF_ANCHORS` numeric curve (Code Examples) — `[ASSUMED]`, explicitly flagged in Assumptions Log A1 and Pitfall 4. No external source; a reasoned starting point only.
- `FINDABILITY_MARGIN = 0.05` — `[ASSUMED]`, Assumptions Log A2.
- The softmax-temperature `p^(1/T)` formula — `[ASSUMED]` in the sense that it's training-knowledge ML technique, not verified via Context7/official docs (there is no library involved — it's pure math), but it is standard and uncontroversial; CONTEXT.md's own text independently names the same formula shape.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; entirely a matter of reusing existing in-repo patterns, all read directly this session.
- Architecture: HIGH — every integration point (where temperature applies, why the cache is unaffected, why the verdict gate is structurally decoupled, why the sort-order fix alone propagates to all consumers) was verified by reading the actual call sites and consumer code, not inferred.
- Pitfalls: HIGH for the structural/wiring pitfalls (1-3, 5-7, all derived from directly-observed code and existing codebase precedents for the same bug class); MEDIUM for Pitfall 4 (the calibration risk is real and well-reasoned but inherently unresolvable without the actual position data — flagged, not glossed over).

**Research date:** 2026-07-07
**Valid until:** No expiry concern — this is a closed, internal, zero-external-dependency change; the only thing that could invalidate this research is the phase's own scope changing (e.g. Phase 153-158's frozen search-core files being modified by an unrelated concurrent phase, which GSD's phase-branching model prevents).
